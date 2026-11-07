import struct, os
p=r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin'; d=open(p,'rb').read(0x1000)
print(d[:64])
if d[:2]==b'MZ':
 pe=struct.unpack_from('<I',d,0x3c)[0]; print('pe',hex(pe), d[pe:pe+4])
 nsec=struct.unpack_from('<H',d,pe+6)[0]; opt=struct.unpack_from('<H',d,pe+20)[0]
 print('nsec',nsec,'optsize',opt)
 off=pe+24+opt
 for i in range(nsec):
  name=d[off+i*40:off+i*40+8].split(b'\0')[0]
  vs,va,rs,ro=struct.unpack_from('<IIII',d,off+i*40+8)
  print(name,hex(va),hex(vs),hex(ro),hex(rs))
