import pefile, struct, hashlib
import aplib
ORIG=r"D:\BaiduNetdiskDownload\CODOL.NET\Game\CODOL_2.6.9.7\codoMP_client_shipRetail.exe"
REC=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
o=open(ORIG,"rb").read(); r=open(REC,"rb").read()
po=pefile.PE(ORIG,fast_load=True); pr=pefile.PE(REC,fast_load=True)
rm={s.VirtualAddress:s for s in pr.sections}

def do(name, srcoff, va):
    hdr=o[srcoff:srcoff+24]
    tag=hdr[4:8]; hsz,=struct.unpack_from("<I",hdr,8); clen,=struct.unpack_from("<I",hdr,12)
    csum,=struct.unpack_from("<I",hdr,16); ulen,=struct.unpack_from("<I",hdr,20)
    print("--- %s @0x%X VA 0x%08X ---" % (name,srcoff,va))
    print("    tag=%r hsz=0x%X clen=0x%X(%d) csum=0x%08X ulen=0x%X(%d)" % (tag,hsz,clen,clen,csum,ulen,ulen))
    comp=o[srcoff+hsz: srcoff+hsz+clen]
    print("    comp bytes=%d  (comp stream spans file 0x%X..0x%X)" % (len(comp),srcoff+hsz,srcoff+hsz+clen))
    out=bytes(aplib.APLib(comp).depack())
    print("    depacked len=%d  claimed=%d  %s" % (len(out),ulen,"LEN-MATCH" if len(out)==ulen else "MISMATCH"))
    print("    sha256(depacked)=%s" % hashlib.sha256(out).hexdigest())
    sr=rm.get(va)
    if sr:
        rec=r[sr.PointerToRawData:sr.PointerToRawData+sr.SizeOfRawData]
        n=min(len(out),len(rec)); same=sum(1 for i in range(n) if out[i]==rec[i])
        print("    vs recovered (0x%X B): common=%d/%d (%.3f%%)  bit-exact=%s" % (
            len(rec),same,n,100.0*same/max(1,n), len(out)==len(rec) and out==rec))
    return out

t=do(".text", 0x400, 0x1000)
print()
v=do(".tvm0", 0x529800, 0xD958000)
print()
# save
open(r"D:\BaiduNetdiskDownload\使命召唤OL\E06_TVM0_STATIC_DECODE_001\_work\depacked_text.bin","wb").write(t)
open(r"D:\BaiduNetdiskDownload\使命召唤OL\E06_TVM0_STATIC_DECODE_001\_work\depacked_tvm0.bin","wb").write(v)
print("saved depacked_text.bin / depacked_tvm0.bin")