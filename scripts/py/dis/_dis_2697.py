import pefile, capstone, struct
exe = r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe"
pe = pefile.PE(exe, fast_load=True)
image_base = pe.OPTIONAL_HEADER.ImageBase
targets = {
    0x4A1D48: "CODOL2697_WritePlayerFields",
    0x4A2840: "CODOL2697_PlayerField",
    0x4A0A9C: "CODOL2697_WriteDeltaValue",
}
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
md.detail = False
for va, name in targets.items():
    rva = va - image_base
    off = pe.get_offset_from_rva(rva)
    size = 0x260
    data = pe.__data__[off:off+size]
    print("=" * 70)
    print("%s  VA=0x%X  file=0x%X" % (name, va, off))
    print("=" * 70)
    for ins in md.disasm(data, va):
        print("0x%06X  %-10s %s" % (ins.address, ins.mnemonic, ins.op_str))
        if ins.mnemonic == "ret":
            break