# -*- coding: utf-8 -*-
import struct, sys
sys.path.insert(0, "DEV-BOOKING/scripts")
BASE = 0x400000
IMG = r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d = open(IMG, "rb").read()
def find_va(needle):
    i = d.find(needle)
    return (BASE + i) if i >= 0 else None
for needle in (b"mmstart sv_resetServer", b"MM_RESERVE_CMD_REQUEST Accepted",
               b"mmbook accepted", b"mmbook timedout", b"start_map_rotate_once"):
    va = find_va(needle)
    print("%-34s -> VA 0x%08X" % (needle.decode(), va if va else 0))
    if not va:
        continue
    pat = struct.pack("<I", va)
    refs = []
    start = 0
    while True:
        j = d.find(pat, start)
        if j < 0:
            break
        if j % 4 == 0:
            refs.append(BASE + j)
        start = j + 1
    full = [hex(va)] if False else refs
    # also search for a two-dword pair (begin/end pointers) used by std::string_view
    print("   imm32 refs (%d): %s" % (len(refs), ", ".join("0x%08X" % r for r in refs[:12])))
    pat2 = struct.pack("<II", va, va + len(needle))
    j = d.find(pat2)
    print("   ptr+len pair: %s" % (("0x%08X" % (BASE + j)) if j >= 0 else "none"))
