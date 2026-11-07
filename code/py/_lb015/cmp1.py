import os
D = r"D:\BaiduNetdiskDownload\使命召唤OL\DEV-PUBLISHER-RESTORE\REF_LOBBY_KIT\mem_linear_20261007_134406"
fresh = os.path.join(D, "r_00401000_008A7000.bin")
fb = open(fresh,"rb").read()
ib = open(r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin","rb").read()
# image_best offset for VA x: x-0x400000 ; fresh offset: x-0x401000
def ib_at(va): 
    o = va-0x400000
    return ib[o:o+16]
def fb_at(va):
    o = va-0x401000
    return fb[o:o+16]
for va in (0x401000, 0x500000, 0x632680, 0x7CB1E2, 0x8A0000, 0xA00000, 0xB00000, 0xC00000, 0xC50000):
    print("%08X  ib=%s  fb=%s  %s" % (va, ib_at(va).hex(), fb_at(va).hex(), ib_at(va)==fb_at(va)))
# overall match ratio over section1
n = min(len(fb), 0x8A7000)
same = sum(1 for i in range(0, n, 4096) if ib[0x1000+i:0x1000+i+4096]==fb[i:i+4096])
print("page-equal count (4K) over %d pages: %d" % (n//4096, same))
# raw file compare
raw = open(r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe","rb").read()
def raw_at(va):
    o = va-0x400000  # first section raw==va
    return raw[o:o+16]
eqrb=sum(1 for i in range(0,n,4096) if raw[0x1000+i:0x1000+i+4096]==fb[i:i+4096] and i+0x1000+4096<=len(raw))
print("raw-vs-fresh equal pages:", eqrb)
print("raw len", hex(len(raw)))
