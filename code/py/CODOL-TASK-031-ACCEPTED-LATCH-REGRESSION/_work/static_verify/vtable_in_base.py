import struct,os
BASE=0x400000
files = {
 "image_best": r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin",
 "Base.dll": r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetailBase.dll",
}
for name,p in files.items():
    d=open(p,'rb').read()
    for a in (0xDC73A0,0xDC7840):
        tb=struct.pack("<I",a)
        n=0; first=[]
        s=0
        while True:
            i=d.find(tb,s)
            if i<0: break
            n+=1
            if len(first)<6: first.append(i)
            s=i+1
        print("%-12s %08X  count=%d  first=%s" % (name,a,n,["%X"%x for x in first]))
