from pathlib import Path
import struct
import sys

import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

ROOT = Path(r"D:\BaiduNetdiskDownload\使命召唤OL")
NEEDLE = "TCLS_SHAREDMEMEMORY".encode("utf-16le")
FMT_LU = "%s%lu".encode("utf-16le")
FMT_LLU = "%s%llu".encode("utf-16le")
FMT_UD = "%s%d".encode("utf-16le")

targets = [
    r"WeGame\tcls\tcls_core.exe",
    r"WeGame\client_launcher.exe",
    r"WeGame\tgp_daemon.exe",
    r"WeGame\wegame.exe",
    r"WeGame\tcls\Tenio\tcls.dll",
    r"WeGame\tcls\client_proxy.dll",
    r"COD OL\TCLS\Client.exe",
    r"COD OL\TCLS\ClientBase.dll",
    r"COD OL\TCLS\TCLSClient.dll",
    r"COD OL\TCLS\Tenio\TCLS.dll",
    r"COD OL\TCLS\TenProtect\Tenio\TCLS.dll",
    r"COD OL\TenProxy.dll",
    r"COD OL\TenSLX.dll",
    r"COD OL\TerSafe.dll",
]


def find_all(hay, needle):
    out = []
    pos = 0
    while True:
        pos = hay.find(needle, pos)
        if pos < 0:
            return out
        out.append(pos)
        pos += 1


def off2va(pe, base, off):
    for s in pe.sections:
        if s.PointerToRawData <= off < s.PointerToRawData + s.SizeOfRawData:
            return base + s.VirtualAddress + (off - s.PointerToRawData)
    return None


def va2off(pe, base, va):
    r = va - base
    for s in pe.sections:
        if s.VirtualAddress <= r < s.VirtualAddress + max(s.Misc_VirtualSize, s.SizeOfRawData):
            return s.PointerToRawData + (r - s.VirtualAddress)
    raise ValueError(hex(va))


def imports(pe, base):
    out = {}
    if not hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
        return out
    for ent in pe.DIRECTORY_ENTRY_IMPORT:
        dll = ent.dll.decode(errors="replace")
        for imp in ent.imports or []:
            name = imp.name.decode(errors="replace") if imp.name else ("ORD#%d" % imp.ordinal)
            # pefile's imp.address is already the image VA in these builds.
            out[imp.address] = (dll, name)
    return out


def dump_around(data, pe, base, va, size=0x140):
    try:
        off = va2off(pe, base, va)
        blob = data[off:off + size]
        md = Cs(CS_ARCH_X86, CS_MODE_32)
        return list(md.disasm(blob, va))
    except Exception:
        return []


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


def xrefs32(data, pe, base, target_va):
    out = []
    pat = struct.pack("<I", target_va)
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


print("=" * 100)
print("EX-024 PRODUCER STATIC SCAN")
print("=" * 100)
for rel in targets:
    p = ROOT / rel
    if not p.exists():
        print("\nMISSING", rel)
        continue
    data = p.read_bytes()
    pe = pefile.PE(data=data, fast_load=False)
    base = pe.OPTIONAL_HEADER.ImageBase
    print("\nFILE", rel, "size", len(data), "base", hex(base), "entry", hex(pe.OPTIONAL_HEADER.AddressOfEntryPoint))
    hits = find_all(data, NEEDLE)
    print("TCLS_SHAREDMEMEMORY utf16 hits", len(hits))
    for off in hits[:10]:
        va = off2va(pe, base, off)
        ctx = data[off - 8:off + 96]
        print("  OFF", hex(off), "VA", hex(va) if va else None, "CTX", ctx.hex())
    for label, pat in [("%s%%lu", FMT_LU), ("%s%%llu", FMT_LLU), ("%s%%d", FMT_UD)]:
        fh = find_all(data, pat)
        if fh:
            print(label, [hex(x) for x in fh[:6]])
    imps = imports(pe, base)
    mapping_imports = [(va, dll, name) for va, (dll, name) in imps.items()
                       if name in ("CreateFileMappingW", "CreateFileMappingA",
                                   "OpenFileMappingW", "OpenFileMappingA",
                                   "MapViewOfFile", "UnmapViewOfFile",
                                   "GetCurrentProcessId")]
    for va, dll, name in mapping_imports:
        calls = find_import_calls(data, pe, base, va)
        print("IMPORT", dll, name, hex(va), "CALLERS", len(calls))
        for c in calls[:12]:
            print("  CALL", hex(c))

print("\n" + "=" * 100)
print("FOCUS tcls_core.exe CreateFileMappingW/OpenFileMappingW callers")
print("=" * 100)
rel = r"WeGame\tcls\tcls_core.exe"
data = (ROOT / rel).read_bytes()
pe = pefile.PE(data=data, fast_load=False)
base = pe.OPTIONAL_HEADER.ImageBase
imps = imports(pe, base)
for name in ("CreateFileMappingW", "CreateFileMappingA", "OpenFileMappingW", "MapViewOfFile"):
    for va, (dll, imp_name) in imps.items():
        if imp_name != name:
            continue
        print("\n###", name, "IAT", hex(va))
        for c in find_import_calls(data, pe, base, va):
            print("CALLER", hex(c))
            for ins in dump_around(data, pe, base, c - 0x60, 0x120):
                mark = ">>" if abs(ins.address - c) <= 12 else "  "
                print(" ", mark, "%08X %-22s %-8s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))

print("\n" + "=" * 100)
print("FOCUS TCLS\\Tenio\\TCLS.dll mapping callers")
print("=" * 100)
rel2 = r"COD OL\TCLS\Tenio\TCLS.dll"
data2 = (ROOT / rel2).read_bytes()
pe2 = pefile.PE(data=data2, fast_load=False)
base2 = pe2.OPTIONAL_HEADER.ImageBase
imps2 = imports(pe2, base2)
for name in ("CreateFileMappingW", "CreateFileMappingA", "OpenFileMappingW", "MapViewOfFile"):
    for va, (dll, imp_name) in imps2.items():
        if imp_name != name:
            continue
        print("\n###", name, "IAT", hex(va))
        for c in find_import_calls(data2, pe2, base2, va):
            print("CALLER", hex(c))
            for ins in dump_around(data2, pe2, base2, c - 0x60, 0x120):
                mark = ">>" if abs(ins.address - c) <= 12 else "  "
                print(" ", mark, "%08X %-22s %-8s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))

print("\n" + "=" * 100)
print("FOCUS tcls_core.exe TCLS_SHAREDMEMEMORY format xrefs")
print("=" * 100)
for target in (0x5822E8, 0x582310, 0x5822B4, 0x5822D8):
    xs = xrefs32(data, pe, base, target)
    print("STR", hex(target), "XREFS", [hex(x) for x in xs])
    for x in xs:
        for ins in dump_around(data, pe, base, x - 0x40, 0x120):
            mark = ">>" if abs(ins.address - x) <= 12 else "  "
            print(" ", mark, "%08X %-22s %-8s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))

print("\n" + "=" * 100)
print("FOCUS tcls_core.exe string decode + producer callers")
print("=" * 100)
for va in (0x5822B4, 0x5822D8, 0x5822E8, 0x582310):
    try:
        off = va2off(pe, base, va)
        raw = data[off:off + 64]
        text = ""
        for i in range(0, min(len(raw), 60), 2):
            ch = raw[i:i + 2]
            if ch == b"\x00\x00":
                break
            text += ch.decode("utf-16le", errors="replace")
        print("STR", hex(va), repr(text), "RAW", raw[:48].hex())
    except Exception as exc:
        print("STRERR", hex(va), exc)


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


for target in (0x4078F0, 0x404020, 0x407D10, 0x407E80):
    print("CALLERS OF", hex(target), [hex(x) for x in e8_callers(data, pe, base, target)])

print("DIS 0x4077F0")
for ins in dump_around(data, pe, base, 0x4077F0, 0x140):
    print(" ", "%08X %-22s %-8s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))

print("\n" + "=" * 100)
print("FOCUS TCLS\\Tenio\\TCLS.dll TCLS_SHAREDMEMEMORY xrefs")
print("=" * 100)
for off in find_all(data2, NEEDLE):
    va = off2va(pe2, base2, off)
    print("STR", hex(off), hex(va), "CTX", data2[off - 16:off + 128].hex())
    if va:
        xs = xrefs32(data2, pe2, base2, va)
        print("XREF32", [hex(x) for x in xs])
        for x in xs:
            for ins in dump_around(data2, pe2, base2, x - 0x40, 0x120):
                mark = ">>" if abs(ins.address - x) <= 12 else "  "
                print(" ", mark, "%08X %-22s %-8s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
