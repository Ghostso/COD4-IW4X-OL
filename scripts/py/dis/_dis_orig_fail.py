# -*- coding: utf-8 -*-
import capstone
p_bak = r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929\Ayria\Plugins\CodolGameServer.Localnet32.bak"
with open(p_bak, "rb") as f: d = f.read()

md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
target_off = 0x1EE735
chunk = d[target_off - 14 : target_off + 40]
for ins in md.disasm(chunk, 0x101EF335 - 14):
    print("  0x%08X: %-10s %s" % (ins.address, ins.mnemonic, ins.op_str))