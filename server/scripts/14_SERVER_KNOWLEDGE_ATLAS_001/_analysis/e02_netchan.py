import pefile, struct
P=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe"
data=open(P,"rb").read(); pe=pefile.PE(P,fast_load=True); IB=pe.OPTIONAL_HEADER.ImageBase
print("=== E-02: 2697 server netchan constants ===")
for name,val in [("1162 (CODOL_FRAGMENT_SIZE)",1162),("0x20000 (CoD4x MAX_MSGLEN)",0x20000),("0x80000000 (FRAGMENT_BIT)",0x80000000)]:
    pat=struct.pack("<I",val) if val<=0xFFFFFFFF else b""
    c=0;o=0
    while pat and True:
        i=data.find(pat,o)
        if i<0: break
        c+=1;o=i+1
    print("  %-34s u32 occurrences=%d" % (name,c))
# textual
for tok in [b"CODOL_FRAGMENT_SIZE",b"CODOL_MAX_FRAGMENTS",b"codol_fragment",b"FRAGMENT_BIT"]:
    print("  token %-24s occurrences=%d" % (tok.decode(), data.count(tok)))