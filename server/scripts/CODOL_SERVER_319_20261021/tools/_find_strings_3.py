import struct
p=r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin'; d=open(p,'rb').read()
for pat in [b'weaponattach',b'common_mp',b'IWffs100',b'IWffu100']:
    print('\nPAT',pat)
    pos=0
    for n in range(30):
        pos=d.find(pat,pos)
        if pos<0: break
        print(hex(pos+0x400000),end=' '); pos+=1
    print()
