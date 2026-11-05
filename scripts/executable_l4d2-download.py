#!/usr/bin/env python3
"""
Download a Left 4 Dead 2 custom map/campaign from Steam Workshop,
save it to the local game addons directory.
"""

from html.parser import HTMLParser
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request

DEFAULT_ADDONS_DIR = "/var/u01/SteamLibrary/steamapps/common/Left 4 Dead 2/left4dead2/addons"
MAX_DEPTH = 5

# HTTP proxy for ISP-filtered Steam hosts. Direct first; curl retries through
# the local Homebrew dpi-proxy service only on failure.
PROXY_URL = os.getenv("DPI_PROXY_URL", "http://127.0.0.1:18118")


def fetch_bytes(url, data=None, headers=None, timeout=10):
    """GET/POST bytes, direct first, via the HTTP proxy on failure."""
    req = urllib.request.Request(url, data=data, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read(), dict(resp.headers)
    except Exception as direct_err:
        cmd = [
            "curl", "-sS", "--fail-with-body", "--noproxy", "", "--proxy", PROXY_URL,
            "--suppress-connect-headers", "--max-time", str(timeout), "-D", "-", "-o", "-",
        ]
        for k, v in (headers or {}).items():
            cmd += ["-H", f"{k}: {v}"]
        if data is not None:
            cmd += ["--data-binary", "@-"]
        cmd.append(url)
        try:
            proc = subprocess.run(cmd, input=data, capture_output=True, timeout=timeout + 5)
        except Exception as e:
            raise direct_err from e
        if proc.returncode != 0:
            raise direct_err
        head, _, body = proc.stdout.partition(b"\r\n\r\n")
        hdrs = {}
        for line in head.decode("latin-1").splitlines()[1:]:
            if ":" in line:
                k, v = line.split(":", 1)
                hdrs[k] = v.strip()
        return body, hdrs


def fetch_json(url, data=None, headers=None, timeout=10):
    """fetch_bytes + JSON decode."""
    body, _ = fetch_bytes(url, data=data, headers=headers, timeout=timeout)
    return json.loads(body.decode("utf-8"))


def extract_workshop_ids(input_str):
    """Extract one or more workshop IDs from a URL, string, or collection."""
    matches = re.findall(r"(?:id=)?(\b\d{8,12}\b)", input_str)
    if not matches:
        return []
    seen = set()
    unique = []
    for m in matches:
        if m not in seen:
            seen.add(m)
            unique.append(m)
    return unique


def check_collection(workshop_id):
    """Check if workshop_id is a collection and return its child items."""
    data = urllib.parse.urlencode({
        "collectioncount": "1",
        "publishedfileids[0]": str(workshop_id),
    }).encode("utf-8")
    try:
        payload = fetch_json(
            "https://api.steampowered.com/ISteamRemoteStorage/GetCollectionDetails/v1/",
            data=data,
            headers={"User-Agent": "L4D2-Downloader/1.0"},
            timeout=5,
        )
        details = payload.get("response", {}).get("collectiondetails", [{}])[0]
        children = details.get("children", [])
        out = []
        for c in children:
            if "publishedfileid" in c:
                out.append({
                    "id": str(c["publishedfileid"]),
                    "filetype": int(c.get("filetype", 0)),
                })
        return out
    except Exception:
        return []


def expand_items(ids, depth=0, seen=None):
    """Recursively expand workshop collections up to MAX_DEPTH."""
    if seen is None:
        seen = set(ids)
    out = []
    for wid in ids:
        children = check_collection(wid)
        if not children:
            out.append(wid)
            continue
        print(f"📁 Workshop ID {wid} is a Collection containing {len(children)} items.")
        for child in children:
            cid = child["id"]
            ftype = child.get("filetype", 0)
            if ftype == 2 and depth < MAX_DEPTH and cid not in seen:
                seen.add(cid)
                out.extend(expand_items([cid], depth + 1, seen))
            elif cid not in seen:
                seen.add(cid)
                out.append(cid)
    return out


def extract_linked_workshop_ids(text):
    """Find Steam Workshop IDs embedded in description URLs."""
    pattern = r"steamcommunity\.com/(?:sharedfiles/filedetails|workshop/filedetails)/\?id=(\d{8,12})"
    seen = set()
    unique = []
    for m in re.finditer(pattern, text):
        wid = m.group(1)
        if wid not in seen:
            seen.add(wid)
            unique.append(wid)
    return unique


class RequiredItemsParser(HTMLParser):
    """Read links only from Steam's Required Items panel."""

    def __init__(self):
        super().__init__()
        self.depth = 0
        self.ids = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "div":
            if self.depth:
                self.depth += 1
            elif attrs.get("id") == "RequiredItems":
                self.depth = 1
        elif tag == "a" and self.depth:
            self.ids.extend(extract_linked_workshop_ids(attrs.get("href", "")))

    def handle_endtag(self, tag):
        if tag == "div" and self.depth:
            self.depth -= 1


def expand_required_items(details_list):
    """Include required items recursively, along with linked multipart descriptions."""
    seen = {str(d["publishedfileid"]) for d in details_list}
    index = 0
    while index < len(details_list):
        details = details_list[index]
        index += 1
        wid = str(details["publishedfileid"])
        page, _ = fetch_bytes(
            f"https://steamcommunity.com/sharedfiles/filedetails/?id={wid}",
            headers={"User-Agent": "L4D2-Downloader/1.0"},
            timeout=15,
        )
        parser = RequiredItemsParser()
        parser.feed(page.decode("utf-8", "replace"))
        linked = parser.ids
        if re.search(r"part\s*\d+\s*/\s*\d+", str(details.get("title") or ""), re.IGNORECASE):
            text = f"{details.get('short_description') or ''}\n{details.get('description') or ''}"
            linked += extract_linked_workshop_ids(text)
        new_ids = [item for item in expand_items(list(dict.fromkeys(linked))) if item not in seen]
        if new_ids:
            print(f"🔗 Found {len(new_ids)} required or linked item(s): {', '.join(new_ids)}")
            extra = get_published_file_details(new_ids)
            if {str(d.get("publishedfileid")) for d in extra} != set(new_ids):
                raise RuntimeError("Steam did not return details for all required items")
            seen.update(new_ids)
            details_list.extend(extra)
    return details_list


def is_preview_url(url):
    """Check if URL points to Steam's image preview host rather than a downloadable file."""
    try:
        parsed = urllib.parse.urlparse(url)
        return "images.steamusercontent.com" in (parsed.hostname or "")
    except Exception:
        return False


def get_published_file_details(item_ids):
    """Fetch metadata for a list of workshop items from Steam Web API."""
    if not item_ids:
        return []
    post_data = {"itemcount": str(len(item_ids))}
    for i, wid in enumerate(item_ids):
        post_data[f"publishedfileids[{i}]"] = wid
    data = urllib.parse.urlencode(post_data).encode("utf-8")
    try:
        payload = fetch_json(
            "https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/",
            data=data,
            headers={"User-Agent": "L4D2-Downloader/1.0"},
            timeout=10,
        )
        return payload.get("response", {}).get("publishedfiledetails", [])
    except Exception as e:
        print(f"Error querying Steam API: {e}", file=sys.stderr)
        return []


def human_size(bytes_val):
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_val < 1024.0:
            return f"{bytes_val:.1f} {unit}" if unit in ["MB", "GB"] else f"{int(bytes_val)} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f} TB"


def report_progress(downloaded, total_size, start_time, last_print):
    """Print the download progress bar; returns the new last-print time."""
    now = time.time()
    if now - last_print > 0.3 or downloaded == total_size:
        last_print = now
        elapsed = max(now - start_time, 0.001)
        pct = (downloaded / total_size * 100) if total_size > 0 else 0
        speed_str = f"{human_size(downloaded / elapsed)}/s"
        bar_len = 25
        filled = int(bar_len * pct / 100)
        bar = "=" * filled + "-" * (bar_len - filled)
        print(
            f"\r  ⬇ [{bar}] {pct:5.1f}% ({human_size(downloaded)}/{human_size(total_size)}) @ {speed_str:<10}",
            end="",
            flush=True,
        )
    return last_print


def download_direct(url, tmp_path, expected_size):
    """Stream the URL direct; returns bytes written or raises."""
    req = urllib.request.Request(url, headers={"User-Agent": "Valve/Steam"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        total_size = int(resp.headers.get("Content-Length", expected_size))
        return stream_response(resp, tmp_path, total_size)


def stream_response(resp, tmp_path, total_size):
    """Stream an open response to tmp_path with progress; returns bytes."""
    downloaded = 0
    start_time = time.time()
    last_print = 0
    with open(tmp_path, "wb") as f:
        while True:
            chunk = resp.read(64 * 1024)
            if not chunk:
                break
            f.write(chunk)
            downloaded += len(chunk)
            last_print = report_progress(downloaded, total_size, start_time, last_print)
    print()
    return downloaded


def download_via_proxy(url, tmp_path, expected_size, timeout=600):
    """Stream the URL through the HTTP proxy with curl; returns bytes or raises."""
    proc = subprocess.Popen(
        ["curl", "-sS", "--fail-with-body", "--noproxy", "", "--proxy", PROXY_URL,
         "--max-time", str(timeout), "-H", "User-Agent: Valve/Steam", url],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    total_size = expected_size
    downloaded = 0
    start_time = time.time()
    last_print = 0
    with open(tmp_path, "wb") as f:
        while True:
            chunk = proc.stdout.read(64 * 1024)
            if not chunk:
                break
            f.write(chunk)
            downloaded += len(chunk)
            last_print = report_progress(downloaded, total_size, start_time, last_print)
    _, err = proc.communicate(timeout=30)
    print()
    if proc.returncode != 0:
        raise RuntimeError(err.decode("utf-8", "replace").strip() or f"curl exit {proc.returncode}")
    return downloaded


def download_file(url, target_path, expected_size=0):
    """Download a file with a progress bar, writing to .tmp before renaming."""
    tmp_path = target_path + ".tmp"
    try:
        try:
            download_direct(url, tmp_path, expected_size)
        except Exception:
            print("  ↩️ Direct blocked, retrying via proxy...", flush=True)
            download_via_proxy(url, tmp_path, expected_size)
        os.replace(tmp_path, target_path)
        try:
            os.chmod(target_path, 0o644)
        except Exception:
            pass
        return True
    except Exception as e:
        if os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
        print(f"\n  ❌ Failed to download: {e}", file=sys.stderr)
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: l4d2-download.py <steam_workshop_url_or_id> [url_or_id ...]", file=sys.stderr)
        print(
            "Example: l4d2-download.py https://steamcommunity.com/sharedfiles/filedetails/?id=3079158071",
            file=sys.stderr,
        )
        sys.exit(1)

    input_arg = " ".join(sys.argv[1:])
    addons_dir = os.getenv("L4D2_ADDONS_DIR", DEFAULT_ADDONS_DIR)
    os.makedirs(addons_dir, exist_ok=True)

    extracted_ids = extract_workshop_ids(input_arg)
    if not extracted_ids:
        print(f"Error: Could not parse any Steam Workshop ID from: '{input_arg}'", file=sys.stderr)
        sys.exit(1)

    final_ids = expand_items(extracted_ids)
    if not final_ids:
        print(f"Error: Could not parse any Steam Workshop ID from: '{input_arg}'", file=sys.stderr)
        sys.exit(1)

    print(f"🔍 Querying Steam Workshop API for {len(final_ids)} item(s)...")
    details_list = get_published_file_details(final_ids)
    if not details_list:
        print("Error: No workshop items found or Steam API unreachable.", file=sys.stderr)
        sys.exit(1)

    try:
        details_list = expand_required_items(details_list)
    except Exception as e:
        print(f"Error checking required Workshop items: {e}", file=sys.stderr)
        sys.exit(1)

    for details in details_list:
        wid = str(details.get("publishedfileid"))
        result = int(details.get("result", 0))
        title = details.get("title") or f"Workshop item {wid}"
        file_url = details.get("file_url")
        file_size = int(details.get("file_size", 0))
        preview_url = details.get("preview_url")

        print(f"\n📦 [{wid}] {title}")

        if result != 1 or not file_url:
            print(f"  ⚠️ Cannot download: file URL unavailable from Steam (result code: {result}).")
            continue

        if is_preview_url(file_url):
            print(f"  ⚠️ Skipping '{title}': collection link/preview only, no game file URL.")
            continue

        target_vpk = os.path.join(addons_dir, f"{wid}.vpk")
        target_preview = os.path.join(addons_dir, f"{wid}.jpg")

        if os.path.isfile(target_vpk) and os.path.getsize(target_vpk) == file_size:
            print(f"  ℹ️ File already exists with exact size ({human_size(file_size)}): {wid}.vpk")
        else:
            print(f"  Size: {human_size(file_size)}")
            success = download_file(file_url, target_vpk, expected_size=file_size)
            if success:
                print(f"  ✅ Saved: {wid}.vpk")

        if preview_url and not os.path.isfile(target_preview):
            try:
                body, _ = fetch_bytes(
                    preview_url, headers={"User-Agent": "Valve/Steam"}, timeout=15
                )
                with open(target_preview, "wb") as pf:
                    pf.write(body)
                try:
                    os.chmod(target_preview, 0o644)
                except Exception:
                    pass
            except Exception:
                pass



if __name__ == "__main__":
    main()
