import struct
d = open(r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin','rb').read()
B = 0x400000
for g in [0xE3EC988, 0xE3EC980, 0xE3ECA10]:
    pat=struct.pack('<I',g); h=[];i=0
    while True:
        i=d.find(pat,i)
        if i<0: break
        v=B+i
        if 0x401000<=v<0xE5C8000: h.append(v)
        i+=1
    print('%#010x refs=%d %s' % (g,len(h),[hex(x) for x in h[:12]]))
print()
# dump 0xE3EC980..0xE3EC9A0 raw
o=0xE3EC980-B
for i in range(0,0x40,16):
    b=d[o+i:o+i+16]
    print('%#010x  %s  %s' % (0xE3EC980+i,b.hex(' '),''.join(chr(c) if 32<=c<127 else '.' for c in b)))
