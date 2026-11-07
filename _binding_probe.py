import sys
from pathlib import Path
import pefile
import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(r"D:\BaiduNetdiskDownload\使命召唤OL")
P = ROOT / "COD OL" / "codoMP_client_shipRetail.exe"
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


def dis(rva, n, marks=()):
    o = off(rva)
    if o is None:
        print("NO", hex(rva))
        return
    print(f"-- rva {rva:#x} va {base + rva:#x}")
    for ins in md.disasm(data[o : o + n], base + rva):
        tag = " >>" if ins.address - base in marks else ""
        note = ""
        if ins.mnemonic in ("call", "jmp"):
            for op in ins.operands:
                if op.type == 3 and op.mem.base == 0 and op.mem.index == 0:
                    note = f" ; MEM {op.mem.disp:#x} RVA {op.mem.disp - base:#x}"
        print(f"{ins.address:08X}{tag} {ins.bytes.hex():<22} {ins.mnemonic:<8} {ins.op_str}{note}")


def find_pattern(pat, label):
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
    print(label, "hits", [(hex(i), hex(r) if r else None) for i, r in hits])
    return hits


for pat, label in [
    (bytes.fromhex("badc6edc00"), "mov edx,0xDC6EDC"),
    (bytes.fromhex("ff155881ca00"), "call [0xCA8158]"),
    (bytes.fromhex("ff155081ca00"), "call [0xCA8150]"),
    (bytes.fromhex("4850a13800"), "ptr 0x00A13848"),
    (bytes.fromhex("6a50a13800"), "ptr 0x00A1386A"),
]:
    hits = find_pattern(pat, label)
    for raw, rva in hits[:20]:
        if rva:
            dis(max(0, rva - 0x40), 0x120, marks=(rva,))

print("\n== absolute refs to CA8150/CA8158 ==")
for target, name in ((0xCA8150, "CA8150"), (0xCA8158, "CA8158")):
    pat = struct.pack("<I", target)
    hits = find_pattern(pat, name)
    for raw, rva in hits[:30]:
        if rva:
            dis(max(0, rva - 0x30), 0x90, marks=(rva,))

print("\n== RVA refs to 8A8150/8A8158 ==")
for target, name in ((0x8A8150, "8A8150"), (0x8A8158, "8A8158")):
    pat = struct.pack("<I", target)
    hits = find_pattern(pat, name)
    for raw, rva in hits[:30]:
        if rva:
            dis(max(0, rva - 0x30), 0x90, marks=(rva,))

print("\n== callers of binding function ==")
for target in (0x584F5E, 0x184F5E):
    raw_target = off(target)
    if raw_target is None:
        print("no off", hex(target))
        continue
    pro = data.rfind(b"\x55\x8b\xec", max(0, raw_target - 0x500), raw_target)
    frva = None
    if pro >= 0:
        for s in pe.sections:
            if s.PointerToRawData <= pro < s.PointerToRawData + s.SizeOfRawData:
                frva = s.VirtualAddress + pro - s.PointerToRawData
                break
    print("target", hex(target), "prologue rva", hex(frva) if frva else None)
    if frva:
        xs = []
        for s in pe.sections:
            if not (s.Characteristics & 0x20000000):
                continue
            b = data[s.PointerToRawData : s.PointerToRawData + s.SizeOfRawData]
            va = base + s.VirtualAddress
            for i in range(len(b) - 5):
                if b[i] == 0xE8:
                    src = va + i
                    dest = (src + 5 + struct.unpack_from("<i", b, i + 1)[0]) & 0xFFFFFFFF
                    if dest == base + frva:
                        xs.append(src - base)
        print("callers", [hex(x) for x in xs[:30]])
        for x in xs[:10]:
            dis(x - 0x40, 0xB0, marks=(x,))

print("\n== slot contents ==")
for rva in (0x8A8150, 0x8A8158):
    o = off(rva)
    print(hex(rva), "off", hex(o) if o else None, "bytes", data[o : o + 8].hex() if o else None)
