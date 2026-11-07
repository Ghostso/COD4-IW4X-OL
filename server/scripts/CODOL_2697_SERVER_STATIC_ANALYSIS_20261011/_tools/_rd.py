import io,sys,pefile
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
NEW=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe"
d=open(NEW,"rb").read(); pe=pefile.PE(data=d,fast_load=True); ib=pe.OPTIONAL_HEADER.ImageBase
def rd(va):
    off=pe.get_offset_from_rva(va-ib); end=d.index(b"\x00",off)
    return d[off:end].decode("latin1")
for va in [0x7c4e20,0x7c4e23,0x7c4e28]:
    print(hex(va),repr(rd(va)))
