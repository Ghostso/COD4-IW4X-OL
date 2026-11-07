from pathlib import Path
import re

import pefile

ROOT = Path(r"D:\BaiduNetdiskDownload\使命召唤OL")
LOG = ROOT / "工具" / "logs" / "ex026_zero_tencent_native_boot_20260917-111137.log"

modules = []
text = LOG.read_bytes().decode("utf-16", errors="replace") if LOG.read_bytes()[:2] == b"\xff\xfe" else LOG.read_text(encoding="utf-8", errors="replace")
for line in text.splitlines():
    m = re.search(r"MODULE_LOAD t=([\d.]+) (.+?) base (0x[0-9a-fA-F]+) size (0x[0-9a-fA-F]+)", line)
    if m:
        path = m.group(2)
        base = int(m.group(3), 16)
        size = int(m.group(4), 16)
        modules.append((base, size, path))

threads = []
for line in text.splitlines():
    m = re.search(r"THREAD t=[\d.]+ TID (\d+) start (0x[0-9a-fA-F]+)", line)
    if m:
        threads.append((int(m.group(1)), int(m.group(2), 16)))


def entry_rva(path):
    try:
        pe = pefile.PE(path, fast_load=True)
        return pe.OPTIONAL_HEADER.AddressOfEntryPoint
    except Exception:
        return None


print("MODULE ENTRY POINTS")
for base, size, path in modules:
    rva = entry_rva(path)
    print(hex(base), hex(rva) if rva is not None else "None", path)

print("\nTHREAD START == MODULE ENTRY")
for tid, start in threads:
    hit = None
    for base, size, path in modules:
        if base <= start < base + size:
            rva = entry_rva(path)
            if rva is not None and start == base + rva:
                hit = (path, rva)
            break
    if hit:
        print("TID", tid, "start", hex(start), "ENTRY", hit[0], "RVA", hex(hit[1]))

print("\nALL THREAD MODULE MAPPING")
for tid, start in threads:
    for base, size, path in modules:
        if base <= start < base + size:
            print("TID", tid, hex(start), path, "RVA", hex(start - base))
            break
    else:
        print("TID", tid, hex(start), "UNKNOWN")
