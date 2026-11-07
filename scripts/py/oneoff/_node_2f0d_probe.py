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


dis(0x2E80, 0x110, marks=[0x2F0D])

print("\n== prologue before 0x2F0D ==")
raw = off(0x2F0D)
pro = data.rfind(b"\x55\x8b\xec", max(0, raw - 0x300), raw)
if pro >= 0:
    frva = None
    for s in pe.sections:
        if s.PointerToRawData <= pro < s.PointerToRawData + s.SizeOfRawData:
            frva = s.VirtualAddress + pro - s.PointerToRawData
            break
    print("prologue rva", hex(frva) if frva else None)
    if frva:
        dis(frva, 0x160, marks=[0x2F0D])
        hits = []
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
                        hits.append(src - base)
        print("callers", [hex(x) for x in hits[:40]])
        for h in hits[:6]:
            dis(h - 0x50, 0xB0, marks=[h])
