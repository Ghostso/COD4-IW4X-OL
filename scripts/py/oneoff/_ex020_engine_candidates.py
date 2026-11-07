import sys
import struct
from pathlib import Path
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(r"D:\BaiduNetdiskDownload\使命召唤OL")
P = ROOT / "COD OL" / "codoMP_client_shipRetail.exe"
pe = pefile.PE(str(P), fast_load=False)
data = P.read_bytes()
base = pe.OPTIONAL_HEADER.ImageBase


def off(rva):
    for s in pe.sections:
        if s.VirtualAddress <= rva < s.VirtualAddress + max(s.Misc_VirtualSize, s.SizeOfRawData):
            return s.PointerToRawData + rva - s.VirtualAddress
    return None


def cstr_at(rva, n=80):
    o = off(rva)
    if o is None:
        return None
    raw = data[o : o + n]
    if b"\x00" not in raw:
        return None
    return raw.split(b"\x00", 1)[0].decode("ascii", "replace")


def find_ascii(term):
    b = term.encode("ascii") + b"\x00"
    hits = []
    pos = 0
    while True:
        i = data.find(b, pos)
        if i < 0:
            break
        rva = None
        for s in pe.sections:
            if s.PointerToRawData <= i < s.PointerToRawData + s.SizeOfRawData:
                rva = s.VirtualAddress + i - s.PointerToRawData
                break
        hits.append((i, rva))
        pos = i + 1
    return hits


terms = [
    "Initializing...",
    "codoMP_client_ship.exe",
    "main\\%s",
    "main\\%s_%s",
    "Renderer",
    "RenderPipelineManagement",
    "TextureManager",
    "Engine",
]

print("== TERM RVA / CODE REFS ==")
for term in terms:
    for raw, rva in find_ascii(term):
        if rva is None or rva < 0x1000 or rva >= 0xE5C8000:
            continue
        va = base + rva
        pat = struct.pack("<I", va)
        refs = []
        pos = 0
        while True:
            i = data.find(pat, pos)
            if i < 0:
                break
            xrva = None
            for s in pe.sections:
                if s.PointerToRawData <= i < s.PointerToRawData + s.SizeOfRawData:
                    xrva = s.VirtualAddress + i - s.PointerToRawData
                    break
            if xrva is not None and xrva < 0xE5C8000:
                refs.append((i, xrva))
            pos = i + 1
        print("TERM", repr(term), "raw", hex(raw), "rva", hex(rva) if rva else None, "refs", [(hex(r), hex(x)) for r, x in refs[:20]])


def dis(rva, n, marks=()):
    o = off(rva)
    if o is None:
        print("NO", hex(rva))
        return
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True
    print(f"-- rva {rva:#x} va {base + rva:#x}")
    for ins in md.disasm(data[o : o + n], base + rva):
        tag = " >>" if ins.address - base in marks else ""
        note = ""
        if ins.mnemonic in ("call", "jmp") and ins.operands:
            op = ins.operands[0]
            if op.type == 3 and op.mem.base == 0 and op.mem.index == 0:
                note = f" ; MEM {op.mem.disp - base:#x}"
        print(f"{ins.address:08X}{tag} {ins.bytes.hex():<22} {ins.mnemonic:<8} {ins.op_str}{note}")


print("\n== CANDIDATE FUNCTIONS AROUND REFERENCES ==")
# Initializing.. has known rva 0x???; discover via output. We'll print refs windows.
for term in ["Initializing...", "Renderer", "RenderPipelineManagement", "TextureManager"]:
    for raw, rva in find_ascii(term):
        if rva is None or rva < 0x1000 or rva >= 0xE5C8000:
            continue
        pat = struct.pack("<I", base + rva)
        pos = 0
        while True:
            i = data.find(pat, pos)
            if i < 0:
                break
            xrva = None
            for s in pe.sections:
                if s.PointerToRawData <= i < s.PointerToRawData + s.SizeOfRawData:
                    xrva = s.VirtualAddress + i - s.PointerToRawData
                    break
            if xrva is not None and xrva < 0xE5C8000:
                print("\nREF", term, "raw", hex(i), "rva", hex(xrva))
                # prologue search
                r_off = off(xrva)
                pro = data.rfind(b"\x55\x8b\xec", max(0, r_off - 0x800), r_off)
                if pro >= 0:
                    frva = None
                    for s in pe.sections:
                        if s.PointerToRawData <= pro < s.PointerToRawData + s.SizeOfRawData:
                            frva = s.VirtualAddress + pro - s.PointerToRawData
                            break
                    print("prologue rva", hex(frva) if frva else None)
                    if frva:
                        dis(frva, 0x120)
                else:
                    dis(max(0, xrva - 0x40), 0x100, marks=(xrva,))
            pos = i + 1
