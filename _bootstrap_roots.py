import sys
from pathlib import Path
import pefile
import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(r"D:\BaiduNetdiskDownload\使命召唤OL")
COD = ROOT / "COD OL"

md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True


def load(name):
    pe = pefile.PE(str(COD / name), fast_load=False)
    data = (COD / name).read_bytes()
    return pe, data


def rva_to_off(pe, rva):
    for s in pe.sections:
        start = s.VirtualAddress
        end = start + max(s.Misc_VirtualSize, s.SizeOfRawData)
        if start <= rva < end:
            return s.PointerToRawData + rva - start
    return None


def off_to_rva(pe, off):
    for s in pe.sections:
        if s.PointerToRawData <= off < s.PointerToRawData + s.SizeOfRawData:
            return s.VirtualAddress + off - s.PointerToRawData
    return None


def annotated(data, pe, rva, n, base=None, targets=()):
    base = base or pe.OPTIONAL_HEADER.ImageBase
    off = rva_to_off(pe, rva)
    if off is None:
        print("NO_OFFSET", hex(rva))
        return
    print(f"-- dis {rva:#x} va={base + rva:#x} off={off:#x}")
    for ins in md.disasm(data[off : off + n], base + rva):
        note = ""
        if ins.mnemonic in ("call", "jmp"):
            for op in ins.operands:
                if op.type == 2 and op.imm in targets:
                    note = f" ; -> {op.imm - base:#x}"
                elif op.type == 3 and op.mem.base == 0 and op.mem.index == 0:
                    note = f" ; MEM {op.mem.disp - base:#x}"
        print(f"{ins.address:08X} {ins.bytes.hex():<22} {ins.mnemonic:<8} {ins.op_str}{note}")


base_pe, base_data = load("codoMP_client_shipRetailBase.dll")
exe_pe, exe_data = load("codoMP_client_shipRetail.exe")
bb = base_pe.OPTIONAL_HEADER.ImageBase
eb = exe_pe.OPTIONAL_HEADER.ImageBase

print("== EXE RVA 0x4000 bytes ==")
off = rva_to_off(exe_pe, 0x4000)
print("off", hex(off))
if off:
    blob = exe_data[off : off + 0x80]
    print(blob.hex())
    printable = "".join(chr(c) if 32 <= c < 127 else "." for c in blob)
    print(printable)

print("\n== pointer 0x404000 refs ==")
pat = struct.pack("<I", 0x404000)
for label, data, pe, base in (("BASE", base_data, base_pe, bb), ("EXE", exe_data, exe_pe, eb)):
    hits = []
    pos = 0
    while True:
        i = data.find(pat, pos)
        if i < 0:
            break
        rva = off_to_rva(pe, i)
        hits.append((i, rva))
        pos = i + 1
    print(label, "hits", len(hits))
    for i, rva in hits[:40]:
        print("  raw", hex(i), "rva", hex(rva) if rva else None)

print("\n== global refs in BASE ==")
for gname, gva in [("STR_PTR", 0x10A24B84), ("HEAP_STATE", 0x10AC4BFC), ("DONE_FLAG", 0x10AC5C28)]:
    rva = gva - bb
    off = rva_to_off(base_pe, rva)
    print(gname, hex(gva), "rva", hex(rva), "off", hex(off) if off else None)
    if off:
        print("  value", base_data[off : off + 16].hex())
    pat = struct.pack("<I", gva)
    hits = []
    pos = 0
    while True:
        i = base_data.find(pat, pos)
        if i < 0:
            break
        r = off_to_rva(base_pe, i)
        hits.append((i, r))
        pos = i + 1
    print("  refs", len(hits))
    for i, r in hits[:30]:
        if r:
            print("   raw", hex(i), "rva", hex(r))
            annotated(base_data, base_pe, r - 0x18, 0x50, bb)

print("\n== direct callers of Base+0x292800/0x2928A0 ==")
for target in (0x292800, 0x2928A0):
    xs = []
    for s in base_pe.sections:
        if not (s.Characteristics & 0x20000000):
            continue
        b = base_data[s.PointerToRawData : s.PointerToRawData + s.SizeOfRawData]
        va = bb + s.VirtualAddress
        for i in range(len(b) - 5):
            if b[i] == 0xE8:
                src = va + i
                dest = (src + 5 + struct.unpack_from("<i", b, i + 1)[0]) & 0xFFFFFFFF
                if dest == bb + target:
                    xs.append(src)
    print("target", hex(target), "callers", [hex(x - bb) for x in xs])
    for x in xs:
        annotated(base_data, base_pe, x - 0x40, 0x90, bb, targets=(bb + 0x292800, bb + 0x2928A0))

print("\n== TLS callbacks EXE ==")
tls = exe_pe.DIRECTORY_ENTRY_TLS.struct
off = rva_to_off(exe_pe, tls.AddressOfCallBacks - eb)
if off:
    for i in range(8):
        val = struct.unpack_from("<I", exe_data, off + i * 4)[0]
        if not val:
            break
        print(i, hex(val), "rva", hex(val - eb))
