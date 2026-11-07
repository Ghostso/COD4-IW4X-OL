import struct
p=r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin'
d=open(p,'rb').read(); BASE=0x400000
def dump(va,a=0,ln=256):
    o=va-BASE
    print('--- %#010x ---'%va)
    for i in range(0,ln,16):
        b=d[o+i:o+i+16]
        print('%#010x  %s  %s'%(va+i,b.hex(' '),''.join(chr(c) if 32<=c<127 else '.' for c in b)))
dump(0x00CA8400,0,0x180)
