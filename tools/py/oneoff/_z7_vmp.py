"""Decide whether VSDDrvDll's .text is real x86 after unpacking.

Section table says .text has SizeOfRawData == 0 on disk (so it is built at
runtime), while create=0x63BB29A0 sits in .vmp1 and the returned object's
vtable sits in .text at module offset 0x2B80.

If .text holds ordinary compiled code after unpacking, dumping it is enough
and we never have to touch the VM.  If it holds bytecode, we do.
"""
import glob
import io
import os
import re

RUNS = r"run_codol_001\runs"

print("=== VSD_VT samples already captured (from live runs) ===")
seen = {}
for d in sorted(glob.glob(os.path.join(RUNS, "IFS1_*")),
                key=os.path.getmtime)[-40:]:
    f = os.path.join(d, "aboprobe.stdout")
    if not os.path.exists(f):
        continue
    for l in io.open(f, encoding="gbk", errors="replace"):
        if ",VSD_VT," not in l:
            continue
        m = re.search(r"obj=(0x[0-9A-F]+) vt=(0x[0-9A-F]+)", l)
        if m:
            seen.setdefault(m.group(2), set()).add(l.strip()[:220])

print("distinct vtables observed: %d" % len(seen))
for vt, lines in list(seen.items())[:6]:
    print()
    print(" vtable", vt)
    print("   ", list(lines)[0][120:])

print()
print("=== how to read the verdict ===")
print("  slot target starting 55 8b ec / 83 ec / 51 / 56 -> real x86")
print("  slot target starting e9 then scrambled           -> thunk / VM entry")
print("  many slots pointing at the SAME address          -> VM dispatcher")
