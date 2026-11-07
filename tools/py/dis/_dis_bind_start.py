# -*- coding: utf-8 -*-
import pefile, capstone

p = r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929\Ayria\Plugins\CodolGameServer.Localnet32"
with open(p, "rb") as f: d = f.read()

pe = pefile.PE(data=d)
base = pe.OPTIONAL_HEADER.ImageBase
target_va = 0x1020AB20
target_off = pe.get_offset_from_rva(target_va - base)

print(f"EngineBindings::bind at VA 0x{target_va:X}, file offset 0x{target_off:X}")

md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
for insn in md.disasm(d[target_off:target_off+160], target_va):
    print("  0x%08X: %-10s %s" % (insn.address, insn.mnemonic, insn.op_str))