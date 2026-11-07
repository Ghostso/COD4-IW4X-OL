import pefile, struct
exe = r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe"
pe = pefile.PE(exe, fast_load=True)
base = pe.OPTIONAL_HEADER.ImageBase
TABLE = 0x7C3B40
rva = TABLE - base
off = pe.get_offset_from_rva(rva)
data = pe.__data__
print("table file offset = 0x%X" % off)
print("idx  offset  codec  hint")
print("-" * 40)
for i in range(229):
    p = off + i*6
    field_off, codec, hint = struct.unpack_from("<hbb", data, p)
    print("%3d  0x%04x  %4d  %2d" % (i, field_off & 0xffff, codec, hint))