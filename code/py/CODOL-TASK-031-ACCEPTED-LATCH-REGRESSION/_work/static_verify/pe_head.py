import hashlib, struct, sys
p = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d = open(p,'rb').read()
print("size", len(d), "sha256", hashlib.sha256(d).hexdigest())
BASE=0x400000
def off(va): return va-BASE
# check PE header at start
print("MZ", d[:2])
pe = struct.unpack_from("<I", d, 0x3C)[0]
print("e_lfanew", hex(pe), "sig", d[pe:pe+4])
mach, nsec = struct.unpack_from("<HH", d, pe+4)
print("machine", hex(mach), "nsections", nsec)
opt = pe+24
magic = struct.unpack_from("<H", d, opt)[0]
print("optmagic", hex(magic))
imgbase = struct.unpack_from("<I", d, opt+28)[0]
sizeofimg = struct.unpack_from("<I", d, opt+56)[0]
print("ImageBase", hex(imgbase), "SizeOfImage", hex(sizeofimg))
