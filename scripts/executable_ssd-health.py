#!/usr/bin/env python3
"""SSD health report for every drive smartctl can see (SATA + NVMe).

Run via `just ssd-health` (needs sudo: smartctl reads drives as root).
Shows, per drive: verdict, health %, wear, data written/read, power-on time,
power cycles, temperature and error counters, in that order.
"""
import json
import os
import subprocess
import sys

TB = 1000**4  # drive makers (and TBW ratings) use decimal terabytes
USE_COLOR = sys.stdout.isatty()


def color(text, code):
    return f"\033[{code}m{text}\033[0m" if USE_COLOR else text


def smartctl(*args):
    cmd = ["smartctl", "-j", *args]
    if os.geteuid() != 0:
        cmd.insert(0, "sudo")
    # smartctl's exit code is a bitmask of warnings, so non-zero is normal.
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return {}


def human_hours(hours):
    if hours is None:
        return "?"
    years, rest = divmod(int(hours), 24 * 365)
    days, hrs = divmod(rest, 24)
    parts = []
    if years:
        parts.append(f"{years}y")
    if years or days:
        parts.append(f"{days}d")
    parts.append(f"{hrs}h")
    return " ".join(parts) + f"  ({int(hours):,} h)"


def tb(n_bytes):
    return "?" if n_bytes is None else f"{n_bytes / TB:,.2f} TB"


def attrs_by_name(data):
    table = data.get("ata_smart_attributes", {}).get("table", [])
    return {a["name"]: a for a in table}


def devstat(data, name):
    """Standard ATA Device Statistics value (same meaning on every vendor)."""
    for page in data.get("ata_device_statistics", {}).get("pages", []):
        for row in page.get("table", []):
            if row.get("name") == name and "value" in row:
                return row["value"]
    return None


def collect(data):
    """Normalise SATA and NVMe output into one dict."""
    d = {
        "model": data.get("model_name", "?"),
        "serial": data.get("serial_number", "?"),
        "firmware": data.get("firmware_version", "?"),
        "capacity": data.get("user_capacity", {}).get("bytes")
        or data.get("nvme_total_capacity"),
        "passed": data.get("smart_status", {}).get("passed"),
        "temp": data.get("temperature", {}).get("current"),
        "hours": data.get("power_on_time", {}).get("hours"),
        "cycles": data.get("power_cycle_count"),
        "health": None,  # percent of life remaining
        "spare": None,
        "written": None,
        "read": None,
        "unsafe": None,
        "errors": {},  # label -> count (only things that matter)
        "warnings": [],
    }

    nvme = data.get("nvme_smart_health_information_log")
    if nvme:
        d["kind"] = "NVMe"
        d["health"] = 100 - nvme.get("percentage_used", 0)
        d["spare"] = (nvme.get("available_spare"), nvme.get("available_spare_threshold"))
        unit = 512_000  # one NVMe "data unit" = 1000 x 512 bytes
        d["written"] = nvme.get("data_units_written", 0) * unit
        d["read"] = nvme.get("data_units_read", 0) * unit
        d["unsafe"] = nvme.get("unsafe_shutdowns")
        d["temp"] = nvme.get("temperature", d["temp"])
        d["errors"] = {
            "Media errors": nvme.get("media_errors"),
            "Error log entries": nvme.get("num_err_log_entries"),
        }
        if nvme.get("critical_warning"):
            d["warnings"].append(f"critical warning flags 0x{nvme['critical_warning']:02x}")
        spare, thresh = d["spare"]
        if spare is not None and thresh is not None and spare <= thresh:
            d["warnings"].append("spare blocks at or below threshold")
        return d

    d["kind"] = "SATA"
    a = attrs_by_name(data)
    sector = data.get("logical_block_size", 512)

    # Health %: standard endurance indicator first, then vendor wear attributes.
    used = devstat(data, "Percentage Used Endurance Indicator")
    if used is not None:
        d["health"] = 100 - used
    else:
        for name in (
            "Media_Wearout_Indicator",  # Intel
            "Wear_Leveling_Count",  # Samsung
            "SSD_Life_Left",
            "Percent_Lifetime_Remain",
            "Remaining_Lifetime_Perc",
        ):
            if name in a:
                d["health"] = a[name]["value"]
                break

    # Data written/read: standard device statistics first, vendor attributes second.
    w = devstat(data, "Logical Sectors Written")
    r = devstat(data, "Logical Sectors Read")
    if w is not None:
        d["written"] = w * sector
    elif "Host_Writes_32MiB" in a:
        d["written"] = a["Host_Writes_32MiB"]["raw"]["value"] * 32 * 1024**2
    elif "Total_LBAs_Written" in a:
        d["written"] = a["Total_LBAs_Written"]["raw"]["value"] * sector
    if r is not None:
        d["read"] = r * sector
    elif "Host_Reads_32MiB" in a:
        d["read"] = a["Host_Reads_32MiB"]["raw"]["value"] * 32 * 1024**2
    elif "Total_LBAs_Read" in a:
        d["read"] = a["Total_LBAs_Read"]["raw"]["value"] * sector

    for label, name in (
        ("Reallocated sectors", "Reallocated_Sector_Ct"),
        ("Pending sectors", "Current_Pending_Sector"),
        ("Uncorrectable (offline)", "Offline_Uncorrectable"),
        ("Reported uncorrectable", "Reported_Uncorrect"),
        ("Program fails", "Program_Fail_Cnt_Total"),
        ("Erase fails", "Erase_Fail_Count"),
        ("Cable/CRC errors", "UDMA_CRC_Error_Count"),
    ):
        if name in a:
            d["errors"][label] = a[name]["raw"]["value"]
    unsafe = a.get("Unexpected_Power_Loss_Ct") or a.get("Power-Off_Retract_Count")
    if unsafe:
        d["unsafe"] = unsafe["raw"]["value"]
    return d


def verdict(d):
    bad = [k for k, v in d["errors"].items() if v]
    if d["passed"] is False:
        return "FAIL", "SMART self-assessment failed"
    if d["warnings"] or bad:
        return "WARN", "; ".join(d["warnings"] + [f"{k}: {d['errors'][k]}" for k in bad])
    if d["health"] is not None and d["health"] < 20:
        return "WARN", "less than 20% life left"
    if d["temp"] is not None and d["temp"] >= 70:
        return "WARN", f"running hot ({d['temp']} C)"
    return "OK", ""


def rows(d):
    """Ordered (section, label, text, color-code) cells for one drive."""
    status, why = verdict(d)
    paint = {"OK": "32", "WARN": "33", "FAIL": "31"}[status]
    out = [
        ("Drive", "Model", d["model"], None),
        ("Drive", "Type / size", f"{d['kind']} / {tb(d['capacity'])}", None),
        ("Drive", "Serial", d["serial"], None),
        ("Drive", "Firmware", d["firmware"], None),
        ("Health", "Verdict", status, paint),
        ("Health", "Notes", why or "-", None),
        ("Health", "SMART self-test", {True: "PASSED", False: "FAILED", None: "unknown"}[d["passed"]], None),
        ("Health", "Life remaining", "?" if d["health"] is None else f"{d['health']}%", None),
    ]
    if d["spare"] and d["spare"][0] is not None:
        out.append(("Health", "Spare blocks (alarm)", f"{d['spare'][0]}% ({d['spare'][1]}%)", None))
    out.append(("Health", "Temperature", "?" if d["temp"] is None else f"{d['temp']} C", None))

    out += [
        ("Wear", "Written (TBW so far)", tb(d["written"]), None),
        ("Wear", "Read", tb(d["read"]), None),
    ]
    if d["written"] and d["read"]:
        out.append(("Wear", "Read : write", f"{d['read'] / d['written']:.1f} : 1", None))
    used = None if d["health"] is None else 100 - d["health"]
    if used and used >= 1 and d["written"]:
        out.append(("Wear", "Est. lifetime TBW (extrapolated)", f"~{tb(d['written'] * 100 / used)}", None))

    out += [
        ("Power", "Powered on", human_hours(d["hours"]), None),
        ("Power", "Power cycles", "?" if d["cycles"] is None else f"{d['cycles']:,}", None),
    ]
    if d["unsafe"] is not None:
        out.append(("Power", "Unsafe shutdowns", f"{d['unsafe']:,}", None))
    for label, value in d["errors"].items():
        out.append(("Errors", label, "?" if value is None else str(value), "33" if value else None))
    return status, out


def render(columns):
    """columns: list of (header, rows). Prints one table, drives side by side."""
    labels = []  # (section, label) in first-seen order
    for _, rs in columns:
        for sec, label, _, _ in rs:
            if (sec, label) not in labels:
                labels.append((sec, label))
    cells = [{(sec, label): (text, code) for sec, label, text, code in rs} for _, rs in columns]

    w0 = max(len(label) for _, label in labels)
    ws = [
        max(len(h), *(len(c[k][0]) for k in labels if k in c))
        for (h, _), c in zip(columns, cells)
    ]
    line = lambda l, m, r: l + "─" * (w0 + 2) + "".join(m + "─" * (w + 2) for w in ws) + r
    print(line("┌", "┬", "┐"))
    print("│ " + " " * w0 + " │" + "│".join(f" {color(h.ljust(w), '1')} " for (h, _), w in zip(columns, ws)) + "│")
    section = None
    for sec, label in labels:
        if sec != section:
            section = sec
            print(line("├", "┼", "┤"))
            print("│ " + color(sec.upper().ljust(w0), "36") + " │" + "│".join(" " * (w + 2) for w in ws) + "│")
        parts = []
        for c, w in zip(cells, ws):
            text, code = c.get((sec, label), ("-", None))
            pad = text.ljust(w)
            parts.append(f" {color(pad, code) if code else pad} ")
        print(f"│ {label.ljust(w0)} │" + "│".join(parts) + "│")
    print(line("└", "┴", "┘"))


def read_drive(dev):
    # Let smartctl auto-detect first: the scan labels the Intel SATA SSD as
    # "-d scsi", which hides its ATA attributes; plain detection finds them.
    data = smartctl("-x", dev["name"])
    if "model_name" not in data and dev.get("type"):
        data = smartctl("-x", dev["name"], "-d", dev["type"])
    return data


def main():
    devices = smartctl("--scan").get("devices", [])
    if not devices:
        sys.exit("No drives found (is smartctl installed and sudo allowed?).")
    columns, failed, worst = [], [], "OK"
    for dev in devices:
        data = read_drive(dev)
        if "model_name" not in data:
            failed.append(dev["name"])
            worst = "FAIL"
            continue
        status, rs = rows(collect(data))
        columns.append((dev["name"], rs))
        worst = max(worst, status, key=["OK", "WARN", "FAIL"].index)
    if columns:
        render(columns)
    for name in failed:
        print(color(f"{name}: could not read SMART data", "31"))
    sys.exit({"OK": 0, "WARN": 1, "FAIL": 2}[worst])


if __name__ == "__main__":
    main()
