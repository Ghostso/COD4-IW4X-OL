import struct
p=r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin'
d=open(p,'rb').read(); BASE=0x400000
def cstr(va,ln=160):
    o=va-BASE
    if o<0 or o>=len(d): return None
    e=d.find(b'\0',o,o+ln)
    if e<0: return None
    b=d[o:e]
    if not b or any(c<32 or c>126 for c in b): return None
    return b.decode()
for target in [0x7AE900,0x9638A8,0x7AECA0,0x963C48,0x9512C0]:
    pat=struct.pack('<I',target); hits=[]; i=0
    while True:
        i=d.find(pat,i)
        if i<0: break
        va=BASE+i
        if 0x401000<=va<0xE5C8000: hits.append(va)
        i+=1
    print('%#x %r refs=%d %s'%(target,cstr(target),len(hits),[hex(x) for x in hits[:20]]))
