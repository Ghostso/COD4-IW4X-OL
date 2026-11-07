import pefile, struct, hashlib, zlib
import aplib
ORIG=r"D:\BaiduNetdiskDownload\CODOL.NET\Game\CODOL_2.6.9.7\codoMP_client_shipRetail.exe"
REC=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
o=open(ORIG,"rb").read(); r=open(REC,"rb").read()
po=pefile.PE(ORIG,fast_load=True); pr=pefile.PE(REC,fast_load=True)
rm={s.VirtualAddress:s for s in pr.sections}
mom={s.VirtualAddress:s for s in po.sections}

def try_block(name, va, hdr_off):
    hdr=o[hdr_off:hdr_off+24]
    tag=hdr[4:8]
    hsz,=struct.unpack_from("<I",hdr,8)
    clen,=struct.unpack_from("<I",hdr,12)
    csum,=struct.unpack_from("<I",hdr,16)
    ulen,=struct.unpack_from("<I",hdr,20)
    print("--- %s @fileoff 0x%X (VA 0x%08X) ---" % (name,hdr_off,va))
    print("    hdr: tag=%r hdr_size=0x%X comp_len=0x%X (%d) csum=0x%08X uncomp_len=0x%X (%d)" % (tag,hsz,clen,clen,csum,ulen,ulen))
    comp=o[hdr_off+hsz: hdr_off+hsz+clen]
    print("    compressed bytes available: %d" % len(comp))
    try:
        out=aplib.decompress(comp)
    except Exception as e:
        print("    aplib.decompress FAILED: %r" % (e,)); return
    print("    aplib output length = %d (header claims %d)  %s" % (len(out),ulen,"LEN-MATCH" if len(out)==ulen else "len-mismatch"))
    sr=rm.get(va)
    if sr:
        rec=r[sr.PointerToRawData:sr.PointerToRawData+sr.SizeOfRawData]
        n=min(len(out),len(rec))
        same=sum(1 for i in range(n) if out[i]==rec[i])
        print("    vs recovered raw (0x%X bytes): common=%d/%d (%.2f%%)" % (len(rec),same,n,100.0*same/max(1,n)))
        print("    bit-exact: %s" % (len(out)==len(rec) and out==rec))
    print("    sha256(depacked) =", hashlib.sha256(out).hexdigest())
    return out

# .text
try_block(".text", 0x1000, 0x400)
print()
# .tvm0
out_tvm0=try_block(".tvm0", 0xD958000, 0x529804)