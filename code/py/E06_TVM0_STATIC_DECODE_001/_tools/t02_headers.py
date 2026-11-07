import pefile, struct, zlib
ORIG=r"D:\BaiduNetdiskDownload\CODOL.NET\Game\CODOL_2.6.9.7\codoMP_client_shipRetail.exe"
REC=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
orig=open(ORIG,"rb").read(); po=pefile.PE(ORIG,fast_load=True)
rec=open(REC,"rb").read(); pr=pefile.PE(REC,fast_load=True)
print("=== ORIGINAL section headers (first 24 bytes of each section raw) ===")
for s in po.sections:
    nm=s.Name.rstrip(b"\x00").decode()
    raw=orig[s.PointerToRawData:s.PointerToRawData+24]
    if len(raw)<24: continue
    f0,=struct.unpack_from("<I",raw,0)
    tag=raw[4:8]
    hsz,=struct.unpack_from("<I",raw,8)
    a,=struct.unpack_from("<I",raw,12)
    b,=struct.unpack_from("<I",raw,16)
    c,=struct.unpack_from("<I",raw,20)
    print("  %-8s VA=0x%08X RawSz=0x%08X | +0=0x%08X +4=%r +8=0x%X +12=0x%X(%d) +16=0x%08X +20=0x%X(%d)" % (
        nm,s.VirtualAddress,s.SizeOfRawData,f0,tag,hsz,a,a,b,c,c))
print()
print("=== RECOVERED section sizes (for comparison with +20) ===")
for s in pr.sections:
    nm=s.Name.rstrip(b"\x00").decode()
    print("  %-8s VA=0x%08X RawSz=0x%08X VSize=0x%08X" % (nm,s.VirtualAddress,s.SizeOfRawData,s.Misc_VirtualSize))
print()
print("=== MATCH TEST: does header +20 == recovered section RawSize? ===")
# map by VA
recmap={s.VirtualAddress:s for s in pr.sections}
for s in po.sections:
    nm=s.Name.rstrip(b"\x00").decode()
    raw=orig[s.PointerToRawData:s.PointerToRawData+24]
    if len(raw)<24 or raw[4:8]!=b"AP32": continue
    c,=struct.unpack_from("<I",raw,20)
    r=recmap.get(s.VirtualAddress)
    if r:
        rn=r.Name.rstrip(b"\x00").decode()
        print("  ORIG %-8s VA=0x%08X +20=0x%08X(%d)  == REC %-8s RawSz=0x%08X(%d)  %s" % (
            nm,s.VirtualAddress,c,c,rn,r.SizeOfRawData,r.SizeOfRawData,"MATCH" if c==r.SizeOfRawData else "no"))
    else:
        print("  ORIG %-8s VA=0x%08X +20=0x%08X(%d)  -> no recovered section at same VA" % (nm,s.VirtualAddress,c,c))
print()
print("=== CRC32 hypothesis: is +16 the CRC32 of the recovered (uncompressed) section? ===")
for s in po.sections:
    raw=orig[s.PointerToRawData:s.PointerToRawData+24]
    if len(raw)<24 or raw[4:8]!=b"AP32": continue
    nm=s.Name.rstrip(b"\x00").decode()
    hdr_crc,=struct.unpack_from("<I",raw,16)
    r=recmap.get(s.VirtualAddress)
    if not r: continue
    un=rec[r.PointerToRawData:r.PointerToRawData+ (struct.unpack_from("<I",raw,20)[0])]
    zc=zlib.crc32(un)&0xFFFFFFFF
    print("  %-8s +16=0x%08X  zlib.crc32(uncompressed)=0x%08X  %s" % (nm,hdr_crc,zc,"MATCH" if zc==hdr_crc else "no"))