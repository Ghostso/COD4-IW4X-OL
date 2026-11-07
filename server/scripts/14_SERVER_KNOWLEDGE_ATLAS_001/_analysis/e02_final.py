import pefile, struct
from capstone import *
P=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe"
data=open(P,"rb").read(); pe=pefile.PE(P,fast_load=True); IB=pe.OPTIONAL_HEADER.ImageBase
print("=== E-02 FINAL: netchan constants in 2697 server binary ===")
print("ImageBase 0x%X  SizeOfImage 0x%X" % (IB,pe.OPTIONAL_HEADER.SizeOfImage))
rows=[
 ("CODOL_FRAGMENT_SIZE-1 = 1161", 0x489),
 ("mask 0x1fffffff (CODOL seq mask)", 0x1fffffff),
 ("CODOL_MAX_MESSAGE = 1162*128 = 148736", 0x24500),
 ("magic ceil(2^37/1162)", 0x70CC729),
]
for label,val in rows:
    pat=struct.pack("<I",val); c=0;o=0
    while True:
        i=data.find(pat,o)
        if i<0: break
        c+=1;o=i+1
    print("  %-40s value=0x%-10X occurrences=%d" % (label,val,c))
print()
print("derivation check: 1162*128=0x%X ; ceil(2^37/1162)=0x%X" % (1162*128, -(-(2**37)//1162)))