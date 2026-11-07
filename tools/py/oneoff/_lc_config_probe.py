import sys
from pathlib import Path
import pefile
import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(r"D:\BaiduNetdiskDownload\使命召唤OL")
P = ROOT / "COD OL" / "codoMP_client_shipRetailBase.dll"
pe = pefile.PE(str(P), fast_load=False)
data = P.read_bytes()
base = pe.OPTIONAL_HEADER.ImageBase
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True


def off(rva):
    for s in pe.sections:
        if s.VirtualAddress <= rva < s.VirtualAddress + max(s.Misc_VirtualSize, s.SizeOfRawData):
            return s.PointerToRawData + rva - s.VirtualAddress
    return None


def cstr_at(rva, n=160):
    o = off(rva)
    if o is None:
        return None
    blob = data[o : o + n]
    if b"\x00" not in blob:
        return None
    raw = blob.split(b"\x00", 1)[0]
    try:
        return raw.decode("ascii")
    except UnicodeDecodeError:
        return None


def dis(rva, n, marks=()):
    o = off(rva)
    if o is None:
        print("NO", hex(rva))
        return
    print(f"-- rva {rva:#x}")
    for ins in md.disasm(data[o : o + n], base + rva):
        tag = " >>" if ins.address - base in marks else ""
        note = ""
        if ins.mnemonic in ("call", "jmp"):
            for op in ins.operands:
                if op.type == 3 and op.mem.base == 0 and op.mem.index == 0:
                    note = f" ; MEM {op.mem.disp - base:#x}"
        print(f"{ins.address:08X}{tag} {ins.bytes.hex():<22} {ins.mnemonic:<8} {ins.op_str}{note}")


print("== LC table 0x1074670C ==")
o = off(0x74670C)
for i in range(6):
    ent = data[o + i * 0xC : o + i * 0xC + 0xC]
    vals = struct.unpack("<III", ent)
    print("entry", i, [hex(v) for v in vals])
    for v in vals:
        if 0x10000000 <= v < 0x14000000:
            s = cstr_at(v - base)
            if s:
                print("   str", hex(v), repr(s))

print("\n== LC_ strings ==")
for pat in (b"LC_", b"lc_"):
    hits = []
    pos = 0
    while True:
        i = data.find(pat, pos)
        if i < 0:
            break
        rva = None
        for s in pe.sections:
            if s.PointerToRawData <= i < s.PointerToRawData + s.SizeOfRawData:
                rva = s.VirtualAddress + i - s.PointerToRawData
                break
        hits.append((i, rva))
        pos = i + 1
    print(pat, "hits", len(hits))
    for i, rva in hits[:30]:
        s = cstr_at(rva, 120)
        print("  raw", hex(i), "rva", hex(rva) if rva else None, "str", repr(s))

print("\n== caller region 0xB7800-0xB7F80 ==")
dis(0xB7800, 0x780, marks=(0xB7B07, 0xB7B45, 0xB7E67, 0xB7E9A))
