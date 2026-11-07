import struct
p=r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin'
d=open(p,'rb').read(); BASE=0x400000
def find(s):
    b=s.encode(); out=[]; i=0
    while True:
        i=d.find(b,i)
        if i<0: break
        out.append(BASE+i); i+=1
    return out
for s in ['dwauth.ini','GDPOpenProtocol.tdr','formal-zone-auth.codol.qq.com','formal-zone-lsg.codol.qq.com','stun1-tub.codol.qq.com','iips.ini','stun.ini','3074']:
    print('%-36s %s'%(s,[hex(x) for x in find(s)][:8]))
# xrefs to dwauth.ini string
for s in ['dwauth.ini','GDPOpenProtocol.tdr']:
    for va in find(s):
        pat=struct.pack('<I',va); hits=[]; i=0
        while True:
            i=d.find(pat,i)
            if i<0: break
            if 0x401000<=BASE+i<0xE5C8000: hits.append(BASE+i)
            i+=1
        print('xrefs to %s @%#x: %s'%(s,va,[hex(x) for x in hits[:12]]))
