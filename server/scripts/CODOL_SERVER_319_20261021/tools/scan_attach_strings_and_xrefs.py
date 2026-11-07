from pathlib import Path
import struct
p=Path(r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin')
d=p.read_bytes(); base=0x400000
for s in [0xdb5cf0,0xdb2f0c]:
    i=0; refs=[]
    needle=struct.pack('<I',s)
    while True:
        off=d.find(needle,i)
        if off<0: break
        refs.append(off+base); i=off+1
    print(hex(s),'n',len(refs),[hex(x) for x in refs[:40]])
# find all NUL strings in memory that mention attachment-like tokens and report around type43 tables
for n in [b'attach',b'weaponattach']:
    hits=[]; pos=0
    while True:
        i=d.find(n,pos)
        if i<0: break
        start=d.rfind(b'\0',max(0,i-80),i)+1
        end=d.find(b'\0',i)
        if 0<=start<end and end-i<200: hits.append((start+base,d[start:end].decode('latin1')))
        pos=i+1
        if len(hits)>100: break
    print(n, len(hits))
    for a,s2 in hits[:30]: print(hex(a),repr(s2))
