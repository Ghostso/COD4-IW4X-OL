#!/usr/bin/env python3
"""s138_store_scan: find store instructions writing a given disp32 offset,
e.g. obj2 fields. Scans for modrm forms with mod=10 (disp32) or mod=01 (disp8).
Usage: python -I tools/s138_store_scan.py 0xF8 0xFC
"""
import struct, sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)
md = Cs(CS_ARCH_X86, CS_MODE_32)

# text range: find .text by PE header
pe = struct.unpack_from("<I", d, 0x3C)[0]
nsec = struct.unpack_from("<H", d, pe + 6)[0]
opt = pe + 24
sects = []
so = opt + struct.unpack_from("<H", d, pe + 20)[0]
for i in range(nsec):
    o = so + i * 40
    name = d[o:o + 8].rstrip(b"\x00").decode("latin1", "replace")
    vsz, vaddr, rsz, raddr = struct.unpack_from("<IIII", d, o + 8)
    sects.append((name, vaddr, rsz, raddr))
for s in sects:
    print("sec %-8s va=0x%08X rawsz=0x%X" % (s[0], s[1] + VA, s[2]))

disp = int(sys.argv[1], 0) if len(sys.argv) > 1 else 0xF8
# find 4-byte disp in text, back up 1-8 bytes, try disasm
text = [s for s in sects if s[0] == ".tp3"][0]
_, tva, tsz, traw = text
needle = struct.pack("<I", disp)
hits = []
i = traw
end = traw + tsz
while True:
    i = d.find(needle, i, end)
    if i < 0:
        break
    hits.append(i)
    i += 1
print("disp 0x%X: %d raw hits" % (disp, len(hits)))
seen = 0
for h in hits:
    for back in range(2, 9):
        st = h - back
        code = d[st:st + back + 10]
        ok = None
        for ins in md.disasm(code, VA + st):
            if ins.address == VA + h - 0 or ins.address <= VA + h < ins.address + ins.size:
                # instruction containing the disp
                txt = ins.mnemonic + " " + ins.op_str
                if ins.mnemonic in ("mov", "movzx", "movsx", "lea", "add", "sub", "or", "and", "xor", "inc", "dec", "cmp", "test"):
                    # must reference +disp exactly
                    if ("0x%x]" % disp) in txt:
                        ok = (ins.address, txt, ins.bytes.hex)
                break
        if ok:
            print("  0x%08X  %-40s  %s" % (ok[0], ok[1], ok[2]))
            seen += 1
            break
    if seen > 400:
        break
