import os
import re
import struct

import pefile

IIPS = r"run_codol_001\sandbox_ifs1_20260923\IIPS"
ORIG = r"COD OL\IIPS"


def list_dir(root):
    print("=" * 80)
    print("LIST", root)
    if not os.path.isdir(root):
        print("  (missing)")
        return
    for name in sorted(os.listdir(root)):
        p = os.path.join(root, name)
        kind = "DIR " if os.path.isdir(p) else "FILE"
        size = 0 if os.path.isdir(p) else os.path.getsize(p)
        print(f"  {kind} {name} {size}")


def scan_immediate_985(root):
    print("=" * 80)
    print("0x3D9 (985) little-endian immediates under", root)
    needle = struct.pack("<I", 985)
    needle16 = struct.pack("<H", 985)
    for dp, _, fs in os.walk(root):
        for n in fs:
            if not n.lower().endswith((".dll", ".exe")):
                continue
            p = os.path.join(dp, n)
            try:
                data = open(p, "rb").read()
            except Exception:
                continue
            h32 = [hex(m.start()) for m in re.finditer(re.escape(needle), data)]
            h16 = [hex(m.start()) for m in re.finditer(re.escape(needle16), data)]
            if h32 or h16:
                rel = os.path.relpath(p, root)
                print(f"  {rel}: u32={len(h32)} u16={len(h16)}")
                if h32:
                    print("     u32 first:", h32[:12])


def tenio_ini(path):
    print("=" * 80)
    print("Tenio.ini", path)
    if not os.path.exists(path):
        print("  (missing)")
        return
    print(open(path, "rb").read().decode("utf-8", "replace"))


def tenio_component_exports(root):
    print("=" * 80)
    print("Tenio component exports under", root)
    if not os.path.isdir(root):
        print("  (missing)")
        return
    for n in sorted(os.listdir(root)):
        if not n.lower().endswith(".dll"):
            continue
        p = os.path.join(root, n)
        print("-" * 70)
        print(n, os.path.getsize(p))
        try:
            pe = pefile.PE(p, fast_load=True)
            pe.parse_data_directories(
                directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]]
            )
        except Exception as e:
            print("   pe error:", e)
            continue
        if not hasattr(pe, "DIRECTORY_ENTRY_EXPORT"):
            print("   (no exports)")
            continue
        for e in pe.DIRECTORY_ENTRY_EXPORT.symbols:
            name = e.name.decode("ascii", "replace") if e.name else "(ord %d)" % e.ordinal
            print("   ", e.ordinal, name)


def main():
    list_dir(IIPS)
    list_dir(os.path.join(IIPS, "Tenio"))
    tenio_ini(os.path.join(IIPS, "Tenio.ini"))
    tenio_ini(os.path.join(ORIG, "Tenio.ini"))
    tenio_component_exports(os.path.join(IIPS, "Tenio"))
    scan_immediate_985(IIPS)


if __name__ == "__main__":
    main()
