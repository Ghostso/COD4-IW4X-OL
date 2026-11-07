# -*- coding: utf-8 -*-
"""
_po_render_hunt.py - final probe: find a DISK-resident, decrypted code region
that references the panel text, and characterise the UI page names.

Why: the shipped EXE's code section is encrypted and the only runtime dump
covers RVA >= 0x594000. Neither yields xrefs to @SF_UI_DW_LIVE_CONNECTING_FAILED,
which is itself the finding. This script checks whether ANY on-disk artifact
(other EXE/DLL/script/config, including the IW4X tree and the sandbox copies)
contains the page/section names or a loadable text form of the popup.

Read-only. No launch, no injection, no network change.
"""
import os
import sys

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"

TERMS = [
    b"popup_connecting",
    b"Live_Frame",
    b"@PLATFORM_POPUP_CONNECTION",
    b"@SF_UI_DW_LIVE_CONNECTING_FAILED",
    b"showPopup",
    b"ShowPopup",
    b"popup_connect",
    b"hud_popup",
]

SKIP_DIRS = {
    "runs", "backups", "_pop_trace", "__pycache__", "logs", "analysis_logs",
    "tools", "toolchain", "IW4X", "WeGameInstaller",
}
SKIP_EXT = {
    ".log", ".etl", ".pcapng", ".pcap", ".jsonl", ".txt", ".md", ".csv",
    ".py", ".js", ".json", ".ini", ".xml", ".bak", ".bin",
}

MAX = 64 * 1024 * 1024


def scan(path):
    try:
        if os.path.getsize(path) > MAX:
            return None
        with open(path, "rb") as fh:
            blob = fh.read()
    except OSError:
        return None
    hits = {}
    for t in TERMS:
        n = blob.count(t)
        if n:
            hits[t.decode()] = n
    return hits or None


def main():
    roots = sys.argv[1:] or [os.path.join(ROOT, "COD OL"),
                             os.path.join(ROOT, "IW4X"),
                             os.path.join(ROOT, "WeGame")]
    total = 0
    for root in roots:
        if not os.path.isdir(root):
            print("skip (missing):", root)
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d.lower() not in SKIP_DIRS]
            for fn in filenames:
                ext = os.path.splitext(fn)[1].lower()
                if ext in SKIP_EXT:
                    continue
                p = os.path.join(dirpath, fn)
                hits = scan(p)
                if hits:
                    total += 1
                    print("%-80s %s" % (p, hits))
                    if total > 200:
                        print("... truncated")
                        return
    print("")
    print("files with hits:", total)


if __name__ == "__main__":
    main()
