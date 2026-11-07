import pefile, capstone
exe = r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe"
pe = pefile.PE(exe, fast_load=True)
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
rva = 0x4CE5
off = pe.get_offset_from_rva(rva)
print("RVA=0x%X file=0x%X" % (rva, off))
data = pe.__data__[off-0x40:off+0x20]
for ins in md.disasm(data, rva-0x40):
    mark = "  <<< CRASH" if ins.address == rva else ""
    print("0x%06X  %-14s %s%s" % (ins.address, ins.mnemonic, ins.op_str, mark))