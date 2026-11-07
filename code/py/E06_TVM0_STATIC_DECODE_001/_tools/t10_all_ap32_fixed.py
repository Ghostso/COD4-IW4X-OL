import pefile, struct, zlib, hashlib
import aplib
ORIG=r"D:\BaiduNetdiskDownload\CODOL.NET\Game\CODOL_2.6.9.7\codoMP_client_shipRetail.exe"
d=open(ORIG,"rb").read()
pe=pefile.PE(ORIG,fast_load=True)
S=[(s.Name.rstrip(b"\x00").decode(),s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData) for s in pe.sections]
def which(off):
    for nm,va,vs,rp,rs in S:
        if rp<=off<rp+rs: return "%s(VA 0x%08X)"%(nm,va)
    return "?"
print("AP32 header layout (relative to signature S):")
print("  S+0x00 'AP32'  S+0x04 hdr_size=0x18  S+0x08 packed_len  S+0x0C packed_crc32  S+0x10 orig_len  S+0x14 orig_crc32  S+0x18 packed data")
print()
print("=== enumerate ALL AP32 blocks ===")
o=0; idx=0; good=0
while True:
    i=d.find(b"AP32",o)
    if i<0: break
    o=i+1
    try:
        hsz,=struct.unpack_from("<I",d,i+4)
        packed,=struct.unpack_from("<I",d,i+8)
        pcrc,=struct.unpack_from("<I",d,i+12)
        orig,=struct.unpack_from("<I",d,i+16)
        ocrc,=struct.unpack_from("<I",d,i+20)
    except Exception: continue
    prefix,=struct.unpack_from("<I",d,i-4)
    shape = (hsz==0x18 and 0<packed<20_000_000 and 0<orig<60_000_000)
    if not shape:
        print("  [%2d] 0x%08X %-22s prefix=0x%08X  NOT-A-HEADER hsz=0x%X" % (idx,i,which(i),prefix,hsz)); idx+=1; continue
    data=d[i+hsz:i+hsz+packed]
    ok_crc = (zlib.crc32(data)&0xFFFFFFFF)==pcrc
    try:
        out=bytes(aplib.APLib(data).depack())
        oc=zlib.crc32(out)&0xFFFFFFFF
        verdict="depack OK len=%d origcrc_ok=%s packedcrc_ok=%s" % (len(out), oc==ocrc, ok_crc)
        if oc==ocrc and len(out)==orig: good+=1
    except Exception as e:
        verdict="depack FAIL %s packedcrc_ok=%s" % (type(e).__name__,ok_crc)
    print("  [%2d] 0x%08X %-22s prefix=0x%08X hsz=0x%X packed=0x%X(%d) orig=0x%X(%d) %s" % (
        idx,i,which(i),prefix,hsz,packed,packed,orig,orig,verdict))
    idx+=1
print()
print("FULLY VERIFIED blocks: %d / %d" % (good,idx))