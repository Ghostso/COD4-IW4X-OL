from pathlib import Path
import struct

import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

ROOT = Path(r"D:\BaiduNetdiskDownload\使命召唤OL")


def va2off(pe, base, va):
    r = va - base
    for s in pe.sections:
        if s.VirtualAddress <= r < s.VirtualAddress + max(s.Misc_VirtualSize, s.SizeOfRawData):
            return s.PointerToRawData + (r - s.VirtualAddress)
    raise ValueError(hex(va))


def off2va(pe, base, off):
    for s in pe.sections:
        if s.PointerToRawData <= off < s.PointerToRawData + s.SizeOfRawData:
            return base + s.VirtualAddress + (off - s.PointerToRawData)
    return None


def imports(pe):
    out = {}
    if not hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
        return out
    for ent in pe.DIRECTORY_ENTRY_IMPORT:
        for imp in ent.imports or []:
            name = imp.name.decode(errors="replace") if imp.name else ("ORD#%d" % imp.ordinal)
            out[imp.address] = (ent.dll.decode(errors="replace"), name)
    return out


def xrefs32(data, pe, base, target):
    pat = struct.pack("<I", target)
    out = []
    for s in pe.sections:
        b = data[s.PointerToRawData:s.PointerToRawData + s.SizeOfRawData]
        sv = base + s.VirtualAddress
        pos = 0
        while True:
            pos = b.find(pat, pos)
            if pos < 0:
                break
            out.append(sv + pos)
            pos += 1
    return out


def dump(data, pe, base, va, size=0x160):
    try:
        off = va2off(pe, base, va)
        blob = data[off:off + size]
    except Exception:
        return []
    return list(Cs(CS_ARCH_X86, CS_MODE_32).disasm(blob, va))


def show_dump(data, pe, base, va, size=0x160, centers=()):
    for ins in dump(data, pe, base, va, size):
        mark = ">>" if any(abs(ins.address - c) <= 12 for c in centers) else "  "
        print(" ", mark, "%08X %-22s %-8s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))


print("=" * 100)
print("FOCUS ClientBase.dll TCLS_SHAREDMEMEMORY references")
print("=" * 100)
rel = r"COD OL\TCLS\ClientBase.dll"
data = (ROOT / rel).read_bytes()
pe = pefile.PE(data=data, fast_load=False)
base = pe.OPTIONAL_HEADER.ImageBase
print("SECTIONS")
for s in pe.sections:
    print(" ", s.Name.rstrip(b"\0").decode(errors="replace"), hex(base + s.VirtualAddress),
          hex(s.Misc_VirtualSize), hex(s.Characteristics))
print("IMPORTS", imports(pe))
str_va = off2va(pe, base, 0x1D3C8C)
print("STRING VA", hex(str_va))
print("XREF32 VA", [hex(x) for x in xrefs32(data, pe, base, str_va)])
print("XREF32 RVA", [hex(x) for x in xrefs32(data, pe, base, 0x1D508C)])
# Look for push imm32 of the VA or RVA and any mov reg, imm32 in executable sections.
patterns = [struct.pack("<I", str_va), struct.pack("<I", 0x1D508C)]
for s in pe.sections:
    if not (s.Characteristics & 0x20000000):
        continue
    b = data[s.PointerToRawData:s.PointerToRawData + s.SizeOfRawData]
    sv = base + s.VirtualAddress
    for pat in patterns:
        pos = 0
        while True:
            pos = b.find(pat, pos)
            if pos < 0:
                break
            print("IMM", pat.hex(), "AT", hex(sv + pos))
            pos += 1

print("\n" + "=" * 100)
print("FOCUS Tenio TCLS.dll name-building helpers")
print("=" * 100)
rel2 = r"COD OL\TCLS\Tenio\TCLS.dll"
data2 = (ROOT / rel2).read_bytes()
pe2 = pefile.PE(data=data2, fast_load=False)
base2 = pe2.OPTIONAL_HEADER.ImageBase
for fn in (0x10005727, 0x10004F39, 0x10005A8D, 0x10002469):
    print("FUNC", hex(fn))
    show_dump(data2, pe2, base2, fn, 0x100)

print("\nCREATE CALLER 0x10040822")
show_dump(data2, pe2, base2, 0x10040700, 0x180, centers=(0x10040761, 0x10040822))

print("\nSTRING CONTEXT")
for off in (0x3C3268, 0x3C05F4, 0x3DD190):
    va = off2va(pe2, base2, off)
    raw = data2[off:off + 64]
    text = ""
    for i in range(0, min(len(raw), 60), 2):
        ch = raw[i:i + 2]
        if ch == b"\x00\x00":
            break
        text += ch.decode("utf-16le", errors="replace")
    print(hex(off), hex(va) if va else None, repr(text), raw[:48].hex())

print("\n" + "=" * 100)
print("EXTRA tcls_core VA/RVA refs for producer constructors")
print("=" * 100)
rel3 = r"WeGame\tcls\tcls_core.exe"
data3 = (ROOT / rel3).read_bytes()
pe3 = pefile.PE(data=data3, fast_load=False)
base3 = pe3.OPTIONAL_HEADER.ImageBase
for target in (0x4078F0, 0x404020, 0x407D10, 0x407E80):
    for val, typ in ((target, "VA"), (target - base3, "RVA")):
        xs = xrefs32(data3, pe3, base3, val)
        print("TARGET", hex(target), typ, [hex(x) for x in xs])
print("STRING TERMS")
for term in ("GameLauncher4TCLS", "CLauncher4TCLS", "CLauncher", "SaveGameInfo", "AddGame"):
    hits = []
    pat = term.encode("utf-16le")
    pos = 0
    while True:
        pos = data3.find(pat, pos)
        if pos < 0:
            break
        hits.append(pos)
        pos += 1
    print(term, [hex(x) for x in hits])
print("CALLER 0x4743A7 context")
show_dump(data3, pe3, base3, 0x474100, 0x1A0, centers=(0x4743A7,))

print("\n" + "=" * 100)
print("EXTRA Tenio TCLS.dll format-string xrefs and mapping caller")
print("=" * 100)
for target in (0x103C05F4, 0x103DD190):
    print("TARGET", hex(target), "XREF32", [hex(x) for x in xrefs32(data2, pe2, base2, target)])
for term in ("%s%lu", "%s%llu", "%s%d", "TCLS_SHAREDMEMEMORY"):
    pat = term.encode("utf-16le")
    hits = []
    pos = 0
    while True:
        pos = data2.find(pat, pos)
        if pos < 0:
            break
        hits.append(pos)
        pos += 1
    print("TERM", term, [hex(x) for x in hits])
for fn in (0x100534A0, 0x10047730, 0x100477B0, 0x100475B0):
    print("REALFUNC", hex(fn))
    show_dump(data2, pe2, base2, fn, 0xC0)

# Find function start before 0x10040822 and direct callers.
start = 0x10040822
for x in range(start - 1, 0x10040000, -1):
    try:
        b = data2[va2off(pe2, base2, x):va2off(pe2, base2, x) + 3]
    except Exception:
        break
    if b == b"\x55\x8b\xec":
        start = x
        break
print("MAPPING_FUNC_START", hex(start))


def e8_callers(data, pe, base, target):
    out = []
    for s in pe.sections:
        if not (s.Characteristics & 0x20000000):
            continue
        b = data[s.PointerToRawData:s.PointerToRawData + s.SizeOfRawData]
        sv = base + s.VirtualAddress
        for pos in range(len(b) - 5):
            if b[pos] != 0xE8:
                continue
            src = sv + pos
            dst = (src + 5 + struct.unpack_from("<i", b, pos + 1)[0]) & 0xFFFFFFFF
            if dst == target:
                out.append(src)
    return out


print("MAPPING_FUNC_CALLERS", [hex(x) for x in e8_callers(data2, pe2, base2, start)])
for c in e8_callers(data2, pe2, base2, start):
    show_dump(data2, pe2, base2, c - 0x40, 0x120, centers=(c,))

print("\n" + "=" * 100)
print("EXTRA TenProxy.dll signature/message xrefs")
print("=" * 100)
rel4 = r"COD OL\TenProxy.dll"
data4 = (ROOT / rel4).read_bytes()
pe4 = pefile.PE(data=data4, fast_load=False)
base4 = pe4.OPTIONAL_HEADER.ImageBase
for target in (0x10020C4A, 0x10020BCE, 0x10021E5A, 0x10021EFE, 0x10021956, 0x100219E2, 0x10020F70):
    print("TARGET", hex(target), "XREF32", [hex(x) for x in xrefs32(data4, pe4, base4, target)])
    for x in xrefs32(data4, pe4, base4, target):
        show_dump(data4, pe4, base4, x - 0x50, 0x120, centers=(x,))
