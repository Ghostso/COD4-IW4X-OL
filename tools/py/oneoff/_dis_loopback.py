import pefile, capstone

dll_path = r'D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\client_native_loopback.dll'
pe = pefile.PE(dll_path)
base = pe.OPTIONAL_HEADER.ImageBase
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)

rva = 0x1500
off = pe.get_offset_from_rva(rva)
data = pe.__data__[off:off+0x550]

for ins in md.disasm(data, base + rva):
    extra = ""
    # annotate calls or jmps
    print("0x%08X: %-10s %-30s %s" % (ins.address, ins.mnemonic, ins.op_str, extra))
