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
        print("NO OFF", hex(rva))
        return
    print(f"-- rva {rva:#x} va {base + rva:#x}")
    for ins in md.disasm(data[o : o + n], base + rva):
        tag = " >>" if ins.address - base in marks else ""
        note = ""
        if ins.mnemonic in ("call", "jmp"):
            for op in ins.operands:
                if op.type == 3 and op.mem.base == 0 and op.mem.index == 0:
                    note = f" ; MEM {op.mem.disp - base:#x}"
        print(f"{ins.address:08X}{tag} {ins.bytes.hex():<22} {ins.mnemonic:<8} {ins.op_str}{note}")


dis(0x288350, 0x1E0, marks=[0x288499])
dis(0x288BC0, 0x120, marks=[0x288C0F])

print("\n== call xrefs to 0x288C0F / 0x288499 ==")
for target in (0x288353, 0x288C0F, 0x288499):
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
                if dest == base + target:
                    hits.append(src - base)
    print("target", hex(target), "callers", [hex(x) for x in hits[:30]])

print("\n== caller window before 0x288C0A ==")
raw_start = off(0x288C0A)
search_start = max(0, raw_start - 0x500)
prologue = data.rfind(b"\x55\x8b\xec", search_start, raw_start)
if prologue >= 0:
    func_rva = None
    for s in pe.sections:
        if s.PointerToRawData <= prologue < s.PointerToRawData + s.SizeOfRawData:
            func_rva = s.VirtualAddress + prologue - s.PointerToRawData
            break
    print("prologue raw", hex(prologue), "rva", hex(func_rva) if func_rva else None)
    if func_rva:
        dis(func_rva, 0x500, marks=[0x288C0A])
else:
    print("no prologue found")

print("\n== type-info/string windows ==")
for rva in (0x74670C, 0x7467CC, 0x74673C, 0x88D7FC):
    o = off(rva)
    if o is None:
        print("NO", hex(rva))
        continue
    blob = data[o : o + 0x180]
    print("RVA", hex(rva), blob.hex())
    printable = "".join(chr(c) if 32 <= c < 127 else "." for c in blob)
    print(printable)
