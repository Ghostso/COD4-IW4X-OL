import struct
d=open(r'E:\codol_re\client_image_20261027.bin','rb').read()
BASE=0x400000
def u4(o): return struct.unpack_from('<I',d,o)[0]
def cs(o):
    e=d.find(b'\x00',o,o+300); return d[o:e].decode('latin1','replace')
print('=== COL @0x009F93B0 原始 20 字节 ===')
print(d[0x009F93B0:0x009F93C4].hex(' '))
sig,off,cd,td,chd=struct.unpack_from('<IIIII',d,0x009F93B0)
print(' sig=0x%X offset=0x%X cd=0x%X td=0x%X chd=0x%X' % (sig,off,cd,td,chd))
print()
print('=== 每个 vftable 槽 -4 处的 COL 指针, 对应的类名 ===')
import re
# 找所有 COL: sig==0 at col
cols={}
for o in range(0x1000, len(d)-20, 4):
    if u4(o)==0:
        t=u4(o+12)
        if t and (BASE+0x1000 <= t < BASE+len(d)):
            cols[o]=t
print('COL 总数(以 sig=0 且 td 是合法 VA): %d' % len(cols))
cnt=0
for vt_rva in (0x009C751C,):
    p=vt_rva; i=0
    while p+4<=len(d):
        v=u4(p)
        if not(BASE+0x1000<=v<BASE+len(d)): break
        # v 是槽值; 该槽属于哪个 vftable? 用 p-4 处的值判断
        hdr=u4(p-4)
        cls='?'
        if hdr in cols:
            cls=cs(cols[hdr]+8,200)
        elif (hdr-BASE) in cols:
            cls=cs(cols[hdr-BASE]+8,200)
        if i<40 or cls!='?':
            print('  [%3d] slot=0x%08X  hdr@0x%08X=0x%08X  %s' % (i,v,p-4,hdr,cls))
        p+=4; i+=1
        if i>250: break
