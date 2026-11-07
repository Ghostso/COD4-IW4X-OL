import pefile, struct, hashlib, zlib
import aplib
ORIG=r"D:\BaiduNetdiskDownload\CODOL.NET\Game\CODOL_2.6.9.7\codoMP_client_shipRetail.exe"
REC=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
o=open(ORIG,"rb").read(); r=open(REC,"rb").read()
po=pefile.PE(ORIG,fast_load=True); pr=pefile.PE(REC,fast_load=True)
rm={s.VirtualAddress:s for s in pr.sections}
om={s.VirtualAddress:s for s in po.sections}

def depack_block(name, va):
    so=om[va]
    start=so.PointerToRawData
    # locate AP32 within first 64 bytes of the section
    k=o.find(b"AP32", start, start+64)
    assert k>=0, "no AP32 in %s"%name
    H=k
    hdrsize,=struct.unpack_from("<I",o,H+4)
    packed,=struct.unpack_from("<I",o,H+8)
    packed_crc,=struct.unpack_from("<I",o,H+12)
    orig,=struct.unpack_from("<I",o,H+16)
    orig_crc,=struct.unpack_from("<I",o,H+20)
    data_off=H+hdrsize
    comp=o[data_off:data_off+packed]
    print("=== %s (VA 0x%08X) ===" % (name,va))
    print("  AP32 at file 0x%X (within-section offset 0x%X); prefix4=%s" % (H,H-start,o[start:H].hex()))
    print("  hdrsize=0x%X packed=0x%X(%d) packed_crc=0x%08X orig=0x%X(%d) orig_crc=0x%08X" % (hdrsize,packed,packed,packed_crc,orig,orig,orig_crc))
    print("  packed data at file 0x%X .. 0x%X ; section ends at 0x%X" % (data_off,data_off+packed,start+so.SizeOfRawData))
    # crc of the packed stream
    print("  zlib.crc32(packed stream)=0x%08X  %s" % (zlib.crc32(comp)&0xFFFFFFFF, "== header" if (zlib.crc32(comp)&0xFFFFFFFF)==packed_crc else "!= header"))
    out=bytes(aplib.APLib(comp).depack())
    print("  depacked len=%d  claimed=%d  %s" % (len(out),orig,"LEN-MATCH" if len(out)==orig else "LEN-MISMATCH"))
    ocrc=zlib.crc32(out)&0xFFFFFFFF
    print("  zlib.crc32(depacked)=0x%08X  %s" % (ocrc,"== header (VERIFIED)" if ocrc==orig_crc else "!= header"))
    sr=rm.get(va)
    if sr:
        rec=r[sr.PointerToRawData:sr.PointerToRawData+orig]
        same=sum(1 for i in range(min(len(out),len(rec))) if out[i]==rec[i])
        print("  vs recovered(0x%X): common=%d/%d (%.4f%%)  bit-exact=%s" % (len(rec),same,min(len(out),len(rec)),100.0*same/min(len(out),len(rec)), out[:len(rec)]==rec))
    return out

t=depack_block(".text", 0x1000); print()
v=depack_block(".tvm0", 0xD958000); print()
open(r"D:\BaiduNetdiskDownload\使命召唤OL\E06_TVM0_STATIC_DECODE_001\_work\depacked_text.bin","wb").write(t)
open(r"D:\BaiduNetdiskDownload\使命召唤OL\E06_TVM0_STATIC_DECODE_001\_work\depacked_tvm0.bin","wb").write(v)
print("saved.")