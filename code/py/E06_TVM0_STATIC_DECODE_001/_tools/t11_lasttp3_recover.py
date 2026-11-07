import pefile, struct, zlib, hashlib
import aplib
ORIG=r"D:\BaiduNetdiskDownload\CODOL.NET\Game\CODOL_2.6.9.7\codoMP_client_shipRetail.exe"
d=open(ORIG,"rb").read()
pe=pefile.PE(ORIG,fast_load=True)
S=[(s.Name.rstrip(b"\x00").decode(),s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData) for s in pe.sections]
LAST_VA=0x0DC11000
last=[x for x in S if x[1]==LAST_VA][0]
print("last .tp3: VA=0x%X VSize=0x%X RawPtr=0x%X RawSize=0x%X -> file 0x%X..0x%X" % (
    last[1],last[2],last[3],last[4],last[3],last[3]+last[4]))
print()
print("=== recover all 8 AP32 blocks inside the last .tp3 ===")
o=last[3]; end=last[3]+last[4]
recs=[]
while True:
    i=d.find(b"AP32",o,end)
    if i<0: break
    hsz,=struct.unpack_from("<I",d,i+4); packed,=struct.unpack_from("<I",d,i+8)
    pcrc,=struct.unpack_from("<I",d,i+12); orig,=struct.unpack_from("<I",d,i+16); ocrc,=struct.unpack_from("<I",d,i+20)
    if hsz==0x18 and 0<packed<20_000_000 and 0<orig<60_000_000:
        blk=d[i+hsz:i+hsz+packed]
        if (zlib.crc32(blk)&0xFFFFFFFF)==pcrc:
            try:
                out=bytes(aplib.APLib(blk).depack())
                if len(out)==orig and (zlib.crc32(out)&0xFFFFFFFF)==ocrc:
                    recs.append((i-hsz,out))
                    print("  @file 0x%08X  -> 0x%X bytes (in-image VA if mapped at 0xDC11000: 0x%X)" % (i-hsz,len(out), 0x400000+LAST_VA+(i-hsz-last[3])))
            except Exception as e:
                print("  @0x%X FAIL %s"%(i,e))
    o=i+1
print()
total=sum(len(x[1]) for x in recs)
print("recovered %d blocks, %d bytes total" % (len(recs),total))
allb=b"".join(x[1] for x in sorted(recs))
open(r"D:\BaiduNetdiskDownload\使命召唤OL\E06_TVM0_STATIC_DECODE_001\_work\lasttp3_blocks.bin","wb").write(allb)
print("combined sha256:", hashlib.sha256(allb).hexdigest())
print()
# Does any block look like .data content (pointer tables)?
IB=0x400000
for idx,(off,out) in enumerate(sorted(recs)):
    n_ptr=0
    for j in range(0,len(out)-4,4):
        v=struct.unpack_from("<I",out,j)[0]
        if IB<=v<IB+0x10E25000: n_ptr+=1
    ascii_ratio=sum(1 for b in out[:4096] if 32<=b<127)/min(4096,len(out)) if out else 0
    print("  block %d: off 0x%X len=0x%X in-image VA=0x%X  VA-pointers=%d (%.2f%%)  ascii_head=%.2f" % (
        idx,off,len(out), IB+LAST_VA+(off-last[3]), n_ptr,100.0*n_ptr/max(1,len(out)//4),ascii_ratio))