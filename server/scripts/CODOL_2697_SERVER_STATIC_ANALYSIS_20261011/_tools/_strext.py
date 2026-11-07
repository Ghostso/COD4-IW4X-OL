import io,sys,pefile,bisect,struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
base=r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\_data"
NEW=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe"
d=open(NEW,"rb").read(); pe=pefile.PE(data=d,fast_load=True); ib=pe.OPTIONAL_HEADER.ImageBase
offs={}
for s in pe.sections:
    nm=s.Name.rstrip(b"\x00").decode("latin1")
    offs[nm]=(s.PointerToRawData,s.VirtualAddress,s.SizeOfRawData,s.Misc_VirtualSize)
def find_str(t):
    b=t.encode()
    r=[]; i=0
    while True:
        j=d.find(b,i)
        if j<0: break
        # map file offset to VA
        nm=off=None
        for name,(ptr,va,rs,vs) in offs.items():
            if ptr<=j<ptr+rs:
                off=ib+va+(j-ptr); nm=name; break
        if off: r.append((nm,off,j))
        i=j+1
    return r
for t in ["CoDOL 2697 gamestate withheld: verified client registration export is required",
          "Read-only verified client registration export for target gamestate publication",
          "CoDOL 2697 publication dry encode=%d bytes=%u actual_client_crc=%d",
          "CoDOL 2697 netconst checksum=%08x seed=%08x"]:
    print("STR",repr(t))
    for nm,va,j in find_str(t): print("    sec=%s va=%#x fileoff=%#x"%(nm,va,j))
