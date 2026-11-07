import pefile, capstone
exe = r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe"
pe = pefile.PE(exe, fast_load=True)
base = pe.OPTIONAL_HEADER.ImageBase
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
va = base + 0x4CE5
rva = 0x4CE5
off = pe.get_offset_from_rva(rva)
print("file offset 0x%X" % off)
data = pe.__data__[off-0x30:off+0x20]
for ins in md.disasm(data, va-0x30):
    mark = "  <<< CRASH" if ins.address == va else ""
    print("0x%06X  %-12s %s%s" % (ins.address, ins.mnemonic, ins.op_str, mark))