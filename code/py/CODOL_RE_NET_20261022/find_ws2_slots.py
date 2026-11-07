import struct, collections, os
p=r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin'
d=open(p,'rb').read()
BASE=0x400000
print('size',len(d),hex(len(d)))
# sections from exe
secs=[('.tp3#0',0x1000,0x8a689a,0x1000,0x593000),('.tp3#1',0x8a8000,0x16da70,0x594000,0x16e000),('.tp3#2',0xa16000,0xdbb1cc0,0x702000,0x62000),('.tp3#3',0xe5c8000,0x31,0x764000,0x1000),('.tp3#4',0xe5c9000,0x9228,0x765000,0xa000),('.tvm0',0xe5d3000,0x4000,0x76f000,0x2000),('.tp3#5',0xe5d7000,0x82000,0x771000,0x6000)]
def rva2off(va):
    rva=va-BASE
    for nm,sva,vsz,raw,rsz in secs:
        if sva<=rva<sva+max(vsz,rsz): return raw+(rva-sva)
    return None
ws2=0x779A0000
lo,hi=ws2, ws2+0x40000
hits=[]
for off in range(0,len(d)-4,4):
    v=struct.unpack_from('<I',d,off)[0]
    if lo<=v<hi:
        hits.append((BASE+off,v))
print('dword hits in ws2 range:',len(hits))
for va,v in hits[:200]:
    print('  slot VA=%#010x -> %#010x (rva %#x)'%(va,v,v-ws2))
open(r'CODOL_RE_NET_20261022\ws2_slots.txt','w',encoding='utf8').write('\n'.join('%#010x -> %#010x rva %#x'%(a,b,b-ws2) for a,b in hits))
