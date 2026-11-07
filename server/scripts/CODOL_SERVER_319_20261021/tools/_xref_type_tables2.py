import struct
p=r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin'
d=open(p,'rb').read()
for target in [0xe5ca30,0xe5ca90,0xe5cb10,0xe5c800,0xe5c8c0]:
    needle=struct.pack('<I',target); offs=[]; pos=0
    while len(offs)<40:
        pos=d.find(needle,pos)
        if pos<0: break
        offs.append(pos+0x400000); pos+=1
    print(hex(target),[hex(x) for x in offs])
