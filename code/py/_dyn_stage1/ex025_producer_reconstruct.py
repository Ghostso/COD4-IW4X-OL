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


def dump(data, pe, base, va, size=0x200):
    try:
        off = va2off(pe, base, va)
        blob = data[off:off + size]
    except Exception:
        return []
    return list(Cs(CS_ARCH_X86, CS_MODE_32).disasm(blob, va))


def show(data, pe, base, va, size=0x200, centers=()):
    imp = imports(pe)
    for ins in dump(data, pe, base, va, size):
        ann = ""
        if ins.mnemonic in ("call", "jmp") and "dword ptr [" in ins.op_str:
            try:
                addr = int(ins.op_str.split("[")[-1].split("]")[0], 16)
                dll, name = imp.get(addr, ("", ""))
                ann = " ; " + dll + "!" + name
            except Exception:
                pass
        mark = ">>" if any(abs(ins.address - c) <= 12 for c in centers) else "  "
        print(" ", mark, "%08X %-22s %-8s %s%s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str, ann))


def find_import_calls(data, pe, base, iat_va):
    out = []
    for s in pe.sections:
        if not (s.Characteristics & 0x20000000):
            continue
        b = data[s.PointerToRawData:s.PointerToRawData + s.SizeOfRawData]
        sv = base + s.VirtualAddress
        pat = b"\xff\x15" + struct.pack("<I", iat_va)
        pos = 0
        while True:
            pos = b.find(pat, pos)
            if pos < 0:
                break
            out.append(sv + pos)
            pos += 1
    return out


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


def find_utf16(data, term):
    pat = term.encode("utf-16le")
    out = []
    pos = 0
    while True:
        pos = data.find(pat, pos)
        if pos < 0:
            return out
        out.append(pos)
        pos += 1


print("=" * 100)
print("EX-025 PRODUCER CALL RECONSTRUCTION")
print("=" * 100)

print("\n" + "=" * 100)
print("PART A: COD OL\\TCLS\\Tenio\\TCLS.dll")
print("=" * 100)
rel = r"COD OL\TCLS\Tenio\TCLS.dll"
data = (ROOT / rel).read_bytes()
pe = pefile.PE(data=data, fast_load=False)
base = pe.OPTIONAL_HEADER.ImageBase
imp = imports(pe)
print("IMAGE", hex(base), "entry", hex(pe.OPTIONAL_HEADER.AddressOfEntryPoint))
print("IMPORTS AROUND 0x1043AB60")
for va in sorted(imp):
    if 0x1043AB40 <= va <= 0x1043AC00:
        print(" ", hex(va), imp[va][0], imp[va][1])
print("GetCurrentProcessId CALLERS")
for va, (dll, name) in imp.items():
    if name == "GetCurrentProcessId":
        print("IAT", hex(va))
        for c in find_import_calls(data, pe, base, va):
            print("CALL", hex(c))
            show(data, pe, base, c - 0x60, 0x100, centers=(c,))

print("\nMAPPING FUNCTION FULL 0x100406E0")
show(data, pe, base, 0x100406E0, 0x3C0, centers=(0x10040761, 0x10040822))
print("REF VA 0x100406E0", [hex(x) for x in xrefs32(data, pe, base, 0x100406E0)])
print("REF RVA 0x406E0", [hex(x) for x in xrefs32(data, pe, base, 0x406E0)])
print("E8 CALLERS", [hex(x) for x in e8_callers(data, pe, base, 0x100406E0)])

print("\n%s%%d STRING XREFS")
for off in find_utf16(data, "%s%d"):
    va = off2va(pe, base, off)
    xs = xrefs32(data, pe, base, va) if va else []
    print("STR", hex(off), hex(va) if va else None, "XREFS", [hex(x) for x in xs])

print("\nCreateFileMappingW CALLER ARGS")
for va, (dll, name) in imp.items():
    if name == "CreateFileMappingW":
        for c in find_import_calls(data, pe, base, va):
            print("CALL", hex(c))
            show(data, pe, base, c - 0x80, 0xA0, centers=(c,))

print("\n" + "=" * 100)
print("PART B: WeGame\\tcls\\tcls_core.exe")
print("=" * 100)
rel2 = r"WeGame\tcls\tcls_core.exe"
data2 = (ROOT / rel2).read_bytes()
pe2 = pefile.PE(data=data2, fast_load=False)
base2 = pe2.OPTIONAL_HEADER.ImageBase
imp2 = imports(pe2)
print("IMAGE", hex(base2), "entry", hex(pe2.OPTIONAL_HEADER.AddressOfEntryPoint))
print("EXPORTS")
if hasattr(pe2, "DIRECTORY_ENTRY_EXPORT"):
    for e in pe2.DIRECTORY_ENTRY_EXPORT.symbols:
        print(" ", hex(e.address), e.name.decode(errors="replace") if e.name else "ORD#%d" % e.ordinal)
else:
    print("  none")
print("GetCurrentProcessId CALLERS")
for va, (dll, name) in imp2.items():
    if name == "GetCurrentProcessId":
        print("IAT", hex(va))
        for c in find_import_calls(data2, pe2, base2, va):
            print("CALL", hex(c))
            show(data2, pe2, base2, c - 0x60, 0x100, centers=(c,))

print("\nPRODUCER CONSTRUCTOR 0x4078F0 FULL")
show(data2, pe2, base2, 0x4078F0, 0x2E0, centers=(0x40798F, 0x4079B0))
print("\nMAPPING HELPER 0x407D10 FULL")
show(data2, pe2, base2, 0x407D10, 0x160, centers=(0x407D81, 0x407D9A))
print("REF VA 0x4078F0", [hex(x) for x in xrefs32(data2, pe2, base2, 0x4078F0)])
print("REF RVA 0x1E78F0", [hex(x) for x in xrefs32(data2, pe2, base2, 0x1E78F0)])
print("REF VA 0x407D10", [hex(x) for x in xrefs32(data2, pe2, base2, 0x407D10)])
print("REF RVA 0x1E7D10", [hex(x) for x in xrefs32(data2, pe2, base2, 0x1E7D10)])
print("E8 CALLERS 0x4078F0", [hex(x) for x in e8_callers(data2, pe2, base2, 0x4078F0)])
print("E8 CALLERS 0x407D10", [hex(x) for x in e8_callers(data2, pe2, base2, 0x407D10)])

print("\nFORMAT STRINGS")
for term in ("TCLS_SHAREDMEMEMORY", "%s%lu", "RAIL_TCLS_SHARED", "%s%llu"):
    print(term, [hex(x) for x in find_utf16(data2, term)])

print("\nCreateFileMappingW CALLER ARGS")
for va, (dll, name) in imp2.items():
    if name == "CreateFileMappingW":
        for c in find_import_calls(data2, pe2, base2, va):
            print("CALL", hex(c))
            show(data2, pe2, base2, c - 0x80, 0xA0, centers=(c,))
