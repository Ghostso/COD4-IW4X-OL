import os
import re
import struct

import pefile

BASE = r"D:\BaiduNetdiskDownload\使命召唤OL"

# Where a Tenio component DLL could plausibly live.
SEARCH_ROOTS = [
    r"COD OL\IIPS",
    r"COD OL\IIPS\Tenio",
    r"COD OL",
    r"run_codol_001\sandbox_ifs1_20260923\IIPS",
    r"run_codol_001\sandbox_ifs1_20260923\IIPS\Tenio",
    r"run_codol_001\sandbox_ifs1_20260923",
]

FACTORY_EXPORTS = {"CreateComponent", "GetComponentIDs", "SetDLLRegistry", "SetFactoryHandle"}


def exports_of(path):
    try:
        pe = pefile.PE(path, fast_load=True)
        pe.parse_data_directories(
            directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]]
        )
    except Exception:
        return set()
    names = set()
    entry = getattr(pe, "DIRECTORY_ENTRY_EXPORT", None)
    if entry is None or isinstance(entry, list):
        return names
    for exp in getattr(entry, "symbols", []):
        if exp.name:
            names.add(exp.name.decode("ascii", "replace"))
    return names


def has_component_factory(path):
    names = exports_of(path)
    return bool(names & FACTORY_EXPORTS), names


def scan_immediate_985(path):
    """Look for 0x3D9 as a 32-bit or 16-bit immediate in code."""
    try:
        data = open(path, "rb").read()
    except Exception:
        return []
    hits = []
    for width, fmt in ((4, "<I"), (2, "<H")):
        needle = struct.pack(fmt, 985)
        start = 0
        while True:
            i = data.find(needle, start)
            if i < 0:
                break
            hits.append((width * 8, i))
            start = i + 1
    return hits


def main():
    print("=" * 100)
    print("Step 1: Tenio component DLLs found anywhere under the project")
    print("=" * 100)

    seen = {}
    for rel_root in SEARCH_ROOTS:
        root = os.path.join(BASE, rel_root)
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d.lower() not in ("vodcache", "iipsdownload")]
            for name in filenames:
                if not name.lower().endswith(".dll"):
                    continue
                path = os.path.join(dirpath, name)
                key = (path.lower(), os.path.getsize(path))
                if key in seen:
                    continue
                seen[key] = True
                is_factory, names = has_component_factory(path)
                if not is_factory:
                    continue
                rel = os.path.relpath(path, BASE)
                print(f"  FACTORY {rel}  size={os.path.getsize(path)}")
                print(f"          factory exports: {sorted(names & FACTORY_EXPORTS)}")
                hits = scan_immediate_985(path)
                if hits:
                    print(f"          immediate-985 hits: {hits[:12]}")
                else:
                    print("          immediate-985 hits: none")

    print()
    print("=" * 100)
    print("Step 2: every DLL under the project that references immediate 985")
    print("=" * 100)

    for dirpath, dirnames, filenames in os.walk(BASE):
        dirnames[:] = [
            d for d in dirnames
            if d.lower() not in (
                "vodcache", "iipsdownload", "__pycache__", "runs",
                "backups", "logs"
            )
        ]
        for name in filenames:
            if not name.lower().endswith((".dll", ".exe")):
                continue
            path = os.path.join(dirpath, name)
            try:
                if os.path.getsize(path) > 120 * 1024 * 1024:
                    continue
            except Exception:
                continue
            hits = scan_immediate_985(path)
            if not hits:
                continue
            rel = os.path.relpath(path, BASE)
            bits = sorted(set(w for w, _ in hits))
            print(f"  {rel}  widths={bits}  count={len(hits)}  first={[hex(o) for _, o in hits[:8]]}")


if __name__ == "__main__":
    main()
