import pefile, struct, zlib, hashlib, os
import aplib
ORIG=r"D:\BaiduNetdiskDownload\CODOL.NET\Game\CODOL_2.6.9.7\codoMP_client_shipRetail.exe"
d=open(ORIG,"rb").read()
pe=pefile.PE(ORIG,fast_load=True)
S=[(s.Name.rstrip(b"\x00").decode(),s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData) for s in pe.sections]
def which(off):
    for nm,va,vs,rp,rs in S:
        if rp<=off<rp+rs: return "%s(VA 0x%08X)"%(nm,va)
    return "?"
print("=== enumerate ALL AP32 blocks in the original and attempt depack ===")
o=0; idx=0
while True:
    i=d.find(b"AP32",o)
    if i<0: break
    o=i+1
    if i<4: continue
    try:
        hdrsize,=struct.unpack_from("<I",d,i+4)
        packed,=struct.unpack_from("<I",d,i+8)
        packed_crc,=struct.unpack_from("<I",d,i+12)
        orig,=struct.unpack_from("<I",d,i+16)
        orig_crc,=struct.unpack_from("<I",d,i+20)
    except Exception:
        continue
    prefix,=struct.unpack_from("<I",d,i-4)
    # sanity
    ok_shape = (hdrsize==0x18 and 0<packed<20_000_000 and 0<orig<60_000_000)
    res=""
    if ok_shape:
        data=d[i+hdrsize-4: i+hdrsize-4+packed]
        pcrc=zlib.crc32(data)&0xFFFFFFFF
        hdr_ok = (pcrc==packed_crc)
        try:
            out=bytes(aplib.APLib(data).depack())
            ocrc=zlib.crc32(out)&0xFFFFFFFF
            res="depack OK len=%d crc_ok=%s (packed_crc_ok=%s)" % (len(out), ocrc==orig_crc, hdr_ok)
        except Exception as e:
            res="depack FAIL %s (packed_crc_ok=%s)" % (type(e).__name__, hdr_ok)
    else:
        res="not-an-AP32-header (hsz=0x%X packed=0x%X orig=0x%X)"%(hdrsize,packed,orig)
    print("  [%2d] file 0x%08X  section %-22s prefix=0x%08X  %s" % (idx,i,which(i),prefix,res))
    idx+=1