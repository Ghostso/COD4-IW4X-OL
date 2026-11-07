import struct
ORIG=r"D:\BaiduNetdiskDownload\CODOL.NET\Game\CODOL_2.6.9.7\codoMP_client_shipRetail.exe"
d=open(ORIG,"rb").read()
c=0;o=0;locs=[]
while True:
    i=d.find(b"AP32",o)
    if i<0: break
    locs.append(i); c+=1; o=i+1
print("AP32 occurrences:",c)
for i in locs[:20]:
    print("  off 0x%X  ctx=%r" % (i, d[max(0,i-8):i+28]))