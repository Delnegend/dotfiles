#!/usr/bin/env python3
"""
Pixel-perfect sync for Zed themes from microsoft/vscode:
  - cfg-app/zed/themes/vscode_dark_modern.jsonc  <- theme-defaults/dark_modern.json
  - cfg-app/zed/themes/vscode_dark_2026.jsonc   <- theme-defaults/2026-dark.json
    (2026-dark includes dark_modern -> dark_plus -> dark_vs)

Usage:
  python scripts/sync-zed-vscode-theme.py          # check both
  python scripts/sync-zed-vscode-theme.py --write  # update both in place
  python scripts/sync-zed-vscode-theme.py --check  # exit 1 if drift

Mapping is explicit (VSCode color -> Zed style) derived from kevcamel/vscode_dark_modern.zed
and semantic naming. Zed-only keys (accents, players, scrollbar thumb, etc.) are preserved.
"""
import argparse
import json
import sys
import urllib.request
from pathlib import Path

try:
    import json5
except ImportError:
    print("Installing json5...", file=sys.stderr)
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "json5", "--quiet"])
    import json5

REPO_ROOT = Path(__file__).resolve().parents[1]
VS_BASE = "https://raw.githubusercontent.com/microsoft/vscode/main/extensions/theme-defaults/themes"

# --- Explicit mapping: Zed style key -> VSCode color key (flat) ---
STYLE_MAP = {
    "border": "sideBar.border",
    "border.variant": "menu.border",
    "border.focused": "focusBorder",
    "border.selected": "sideBar.border",
    "border.transparent": "sideBar.border",
    "border.disabled": "sideBar.border",
    "elevated_surface.background": "editorWidget.background",
    "background": "editor.background",
    "element.background": "surface.border",
    "text": "editor.foreground",
    "text.muted": "editor.foreground",
    "text.disabled": "editor.foreground",
    "status_bar.background": "statusBar.background",
    "title_bar.background": "titleBar.activeBackground",
    "title_bar.inactive_background": "titleBar.inactiveBackground",
    "toolbar.background": "titleBar.inactiveBackground",
    "tab_bar.background": "editorGroupHeader.tabsBackground",
    "tab.inactive_background": "tab.inactiveBackground",
    "tab.active_background": "tab.activeBackground",
    "panel.background": "panel.background",
    "panel.focused_border": "focusBorder",
    "pane_group.border": "editorGroup.border",
    "scrollbar.track.border": "editorOverviewRuler.border",
    "editor.foreground": "editor.foreground",
    "editor.background": "editor.background",
    "editor.gutter.background": "editor.background",
    "editor.line_number": "editorLineNumber.foreground",
    "editor.active_line_number": "editorLineNumber.activeForeground",
    "editor.wrap_guide": "sideBar.border",
    "editor.active_wrap_guide": "sideBar.border",
    "editor.indent_guide": "editorIndentGuide.background1",
    "editor.indent_guide_active": "editorIndentGuide.activeBackground1",
    "editor.document_highlight.read_background": "editor.selectionHighlightBackground",
    "editor.document_highlight.bracket_background": "editor.selectionHighlightBackground",
    "terminal.background": "panel.background",
    "terminal.foreground": "terminal.foreground",
    "link_text.hover": "textLink.foreground",
    "version_control.added": "editorGutter.addedBackground",
    "version_control.deleted": "editorGutter.deletedBackground",
    "version_control.modified": "editorGutter.modifiedBackground",
    "error.background": "editorWidget.background",
    "error.border": "menu.border",
    "hidden": "descriptionForeground",
    "hint.background": "badge.background",
    "info.border": "menu.border",
    "modified": "chat.editedFileForeground",
    "unreachable.background": "editorWidget.background",
    "unreachable.border": "menu.border",
    "warning.background": "editorWidget.background",
    "warning.border": "menu.border",
}

ALPHA_MAP = {
    "text.disabled": ("editor.foreground", "80"),
    "hint.background": ("badge.background", "1A"),
    "error.background": ("editorWidget.background", None),
    "unreachable.background": ("editorWidget.background", None),
    "warning.background": ("editorWidget.background", None),
}

# Syntax maps
SYNTAX_MAP_MODERN = {
    "attribute": "#9CDCFE",
    "boolean": "#569CD6",
    "comment": "#6A9955",
    "comment.doc": "#6A9955",
    "constant": "#4FC1FF",
    "constructor": "#569CD6",
    "embedded": "#D4D4D4",
    "emphasis.strong": "#569CD6",
    "function": "#DCDCAA",
    "keyword": "#569CD6",
    "keyword.declaration": "#569CD6",
    "keyword.control": "#C586C0",
    "keyword.import": "#C586C0",
    "number": "#B5CEA8",
    "operator": "#D4D4D4",
    "preproc": "#569CD6",
    "property": "#9CDCFE",
    "punctuation": "#CCCCCC",
    "punctuation.bracket": "#CCCCCC",
    "punctuation.delimiter": "#CCCCCC",
    "punctuation.list_marker": "#CCCCCC",
    "punctuation.special": "#CCCCCC",
    "string": "#CE9178",
    "string.escape": "#D7BA7D",
    "string.regex": "#D16969",
    "string.special": "#D16969",
    "string.special.symbol": "#D16969",
    "tag": "#569CD6",
    "tag.component.jsx": "#4EC9B0",
    "text.literal": "#CE9178",
    "type": "#4EC9B0",
    "type.builtin": "#569CD6",
    "variable": "#9CDCFE",
    "variable.special": "#569CD6",
}

SYNTAX_MAP_2026 = {
    "attribute": "#79c0ff",
    "boolean": "#79c0ff",
    "comment": "#8b949e",
    "comment.doc": "#8b949e",
    "constant": "#79c0ff",
    "constructor": "#d2a8ff",
    "embedded": "#c9d1d9",
    "emphasis.strong": "#ff7b72",
    "function": "#d2a8ff",
    "keyword": "#ff7b72",
    "keyword.declaration": "#ff7b72",
    "keyword.control": "#ff7b72",
    "keyword.import": "#ff7b72",
    "number": "#79c0ff",
    "operator": "#c9d1d9",
    "preproc": "#ff7b72",
    "property": "#79c0ff",
    "punctuation": "#c9d1d9",
    "punctuation.bracket": "#c9d1d9",
    "punctuation.delimiter": "#c9d1d9",
    "punctuation.list_marker": "#c9d1d9",
    "punctuation.special": "#c9d1d9",
    "string": "#a5d6ff",
    "string.escape": "#7ee787",
    "string.regex": "#a5d6ff",
    "string.special": "#a5d6ff",
    "string.special.symbol": "#a5d6ff",
    "tag": "#7ee787",
    "tag.component.jsx": "#7ee787",
    "text.literal": "#a5d6ff",
    "type": "#79c0ff",
    "type.builtin": "#ff7b72",
    "variable": "#ffa657",
    "variable.special": "#ff7b72",
}

THEMES = [
    {
        "path": REPO_ROOT / "cfg-app" / "zed" / "themes" / "vscode_dark_modern.jsonc",
        "name": "VSCode Dark Modern",
        "flat_chain": ["dark_vs.json", "dark_plus.json", "dark_modern.json"],
        "syntax_map": SYNTAX_MAP_MODERN,
    },
    {
        "path": REPO_ROOT / "cfg-app" / "zed" / "themes" / "vscode_dark_2026.jsonc",
        "name": "VSCode Dark 2026",
        "flat_chain": ["dark_vs.json", "dark_plus.json", "dark_modern.json", "2026-dark.json"],
        "syntax_map": SYNTAX_MAP_2026,
    },
]


def fetch_vscode(chain):
    def fetch(p):
        url = f"{VS_BASE}/{p}"
        data = urllib.request.urlopen(url).read().decode("utf-8")
        return json5.loads(data)
    flat = {}
    raws = {}
    for name in chain:
        j = fetch(name)
        raws[name] = j
        if "colors" in j:
            flat.update(j["colors"])
    # return flat and the last raw that has tokenColors
    return flat, raws[chain[-1]], raws


def sync_one(cfg, do_write=False):
    flat, last_raw, all_raw = fetch_vscode(cfg["flat_chain"])
    print(f"\n[{cfg['name']}] Fetched flat colors: {len(flat)} keys (chain {cfg['flat_chain']})")
    modern = {k: v for k, v in flat.items() if "modern" in k.lower()}
    if modern:
        print(f"  Modern keys: {modern}")

    with open(cfg["path"], encoding="utf-8") as f:
        try:
            zed = json.load(f)
        except:
            zed = json5.load(open(cfg["path"], encoding="utf-8"))
    style = zed["themes"][0]["style"]
    syntax = style.get("syntax", {})
    drift = []

    for zed_key, vs_key in STYLE_MAP.items():
        vs_val = flat.get(vs_key)
        if vs_val is None:
            print(f"WARN: VSCode key {vs_key} not in flat (for Zed {zed_key})", file=sys.stderr)
            continue
        zed_val = style.get(zed_key)
        if zed_val is None:
            continue
        if zed_key in ALPHA_MAP:
            base, suffix = ALPHA_MAP[zed_key]
            expected = vs_val
            if suffix:
                if len(vs_val) == 7 and suffix:
                    expected = vs_val + suffix
                elif vs_val.lower().endswith(suffix.lower()):
                    expected = vs_val
            if isinstance(zed_val, str) and zed_val.lower() != expected.lower():
                drift.append((zed_key, zed_val, expected, vs_key))
        else:
            if isinstance(zed_val, str) and zed_val.lower() != vs_val.lower():
                drift.append((zed_key, zed_val, vs_val, vs_key))

    for zed_syn_key, expected_hex in cfg["syntax_map"].items():
        zed_syn_val = syntax.get(zed_syn_key, {}).get("color") if isinstance(syntax.get(zed_syn_key), dict) else None
        if zed_syn_val and zed_syn_val.lower() != expected_hex.lower():
            drift.append((f"syntax.{zed_syn_key}", zed_syn_val, expected_hex, "token"))

    if drift:
        print(f"Drift detected for {cfg['name']} ({len(drift)}):")
        for zed_k, cur, exp, vs_k in drift:
            print(f"  {zed_k:35} current {cur:12} -> upstream {exp:12} (via {vs_k})")
    else:
        print(f"No drift — {cfg['name']} is pixel-perfect with current vscode/main.")

    if do_write and drift:
        for zed_k, cur, exp, vs_k in drift:
            if zed_k.startswith("syntax."):
                syn_key = zed_k[len("syntax."):]
                if syn_key in syntax and isinstance(syntax[syn_key], dict):
                    syntax[syn_key]["color"] = exp
                    print(f"Updated syntax.{syn_key} -> {exp}")
            else:
                style[zed_k] = exp
                print(f"Updated style.{zed_k} -> {exp}")
        with open(cfg["path"], "w", encoding="utf-8") as f:
            json.dump(zed, f, indent=2)
            f.write("\n")
        print(f"Wrote updated theme to {cfg['path']}")
    return drift


def main():
    parser = argparse.ArgumentParser(description="Sync Zed themes from VSCode")
    parser.add_argument("--write", action="store_true", help="Write updated themes in place")
    parser.add_argument("--check", action="store_true", help="Exit 1 if drift detected")
    args = parser.parse_args()

    all_drift = []
    for cfg in THEMES:
        if not cfg["path"].exists():
            print(f"Skipping {cfg['name']}: {cfg['path']} not found")
            continue
        drift = sync_one(cfg, do_write=args.write)
        all_drift.extend(drift)

    if args.check and all_drift:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
