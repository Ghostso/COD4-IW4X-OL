import sys
from pathlib import Path
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(r"D:\BaiduNetdiskDownload\使命召唤OL")
COD = ROOT / "COD OL"


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


def disasm(data, pe, rva, n, base=None):
    base = base or pe.OPTIONAL_HEADER.ImageBase
    off = rva_to_off(pe, rva)
    if off is None:
        print("NO_OFFSET", hex(rva))
        return
    print(f"-- disasm rva={rva:#x} va={base + rva:#x} off={off:#x} n={n}")
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True
    for ins in md.disasm(data[off : off + n], base + rva):
        print(f"{ins.address:08X} {ins.bytes.hex():<22} {ins.mnemonic:<8} {ins.op_str}")


def cstr(data, pe, rva, base):
    off = rva_to_off(pe, rva)
    if off is None:
        return None
    blob = data[off : off + 256]
    if b"\x00" not in blob:
        return None
    s = blob.split(b"\x00", 1)[0]
    try:
        return s.decode("ascii")
    except UnicodeDecodeError:
        return None


def annotated(data, pe, rva, n, base=None, extra_targets=()):
    base = base or pe.OPTIONAL_HEADER.ImageBase
    off = rva_to_off(pe, rva)
    if off is None:
        print("NO_OFFSET", hex(rva))
        return
    targets = {base + r: r for r in extra_targets}
    print(f"-- annotated rva={rva:#x} va={base + rva:#x} off={off:#x} n={n}")
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True
    for ins in md.disasm(data[off : off + n], base + rva):
        note = ""
        if ins.mnemonic in ("call", "jmp"):
            for op in ins.operands:
                if op.type == 2 and op.imm in targets:
                    note = f" ; -> RVA {targets[op.imm]:#x}"
                elif op.type == 3 and op.mem.base == 0 and op.mem.index == 0:
                    note = f" ; MEM {op.mem.disp:#x} RVA {op.mem.disp - base:#x}"
        print(f"{ins.address:08X} {ins.bytes.hex():<22} {ins.mnemonic:<8} {ins.op_str}{note}")


def tls_info(pe, data, base, label):
    print(f"== {label} TLS ==")
    tls = getattr(pe, "DIRECTORY_ENTRY_TLS", None)
    if not tls:
        print("no TLS directory")
        return
    s = tls.struct
    print("start", hex(s.StartAddressOfRawData))
    print("end", hex(s.EndAddressOfRawData))
    print("index", hex(s.AddressOfIndex))
    print("callbacks", hex(s.AddressOfCallBacks))
    cbrva = s.AddressOfCallBacks - base
    off = rva_to_off(pe, cbrva)
    print("callback_rva", hex(cbrva), "off", hex(off) if off else None)
    if off:
        for i in range(16):
            val = int.from_bytes(data[off + i * 4 : off + i * 4 + 4], "little")
            if val == 0:
                break
            print("callback", i, hex(val), "rva", hex(val - base))


base_pe, base_data = load("codoMP_client_shipRetailBase.dll")
exe_pe, exe_data = load("codoMP_client_shipRetail.exe")
bb = base_pe.OPTIONAL_HEADER.ImageBase
eb = exe_pe.OPTIONAL_HEADER.ImageBase

print("BASE", hex(bb), "EXE", hex(eb))
print("BASE sections")
for s in base_pe.sections:
    print(s.Name.rstrip(b"\x00").decode("latin1"), "rva", hex(s.VirtualAddress), "raw", hex(s.PointerToRawData), "rawsize", hex(s.SizeOfRawData))
print("EXE sections")
for s in exe_pe.sections:
    print(s.Name.rstrip(b"\x00").decode("latin1"), "rva", hex(s.VirtualAddress), "raw", hex(s.PointerToRawData), "rawsize", hex(s.SizeOfRawData))

tls_info(base_pe, base_data, bb, "BASE")
tls_info(exe_pe, exe_data, eb, "EXE")

annotated(base_data, base_pe, 0x27E290, 0x1C0, bb, extra_targets=[0x27E403, 0x27E40C])
annotated(base_data, base_pe, 0x292800, 0xD0, bb, extra_targets=[0x27E3B0])
annotated(exe_data, exe_pe, 0x584C00, 0x380, eb, extra_targets=[0x184F5E, 0x584F5F])

print("== patch diff ==")
exp = (ROOT / "工具" / "EXPERIMENT_DIR" / "codoMP_client_shipRetailBase.dll").read_bytes()
diffs = [i for i in range(len(base_data)) if base_data[i] != exp[i]]
for off in diffs:
    rva = off_to_rva(base_pe, off)
    print("raw", hex(off), "rva", hex(rva) if rva else None, "orig", base_data[off : off + 16].hex(), "exp", exp[off : off + 16].hex())
    if rva:
        disasm(base_data, base_pe, rva - 0x20, 0x60, bb)
        disasm(exp, base_pe, rva - 0x20, 0x60, bb)
