import struct
p=r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin'; d=open(p,'rb').read()
# xrefs to the type-name pointer for weaponattach at db5cf0
needle=struct.pack('<I',0xdb5cf0); pos=0; refs=[]
while len(refs)<50:
 pos=d.find(needle,pos)
 if pos<0:break
 refs.append(pos+0x400000);pos+=1
print('weaponattach-name refs',[hex(x) for x in refs])
# xrefs to type 43 numeric patterns in every executable region (byte scan, print context)
for pat in [b'\x84\x00',b'\x7f\x2b']:
 print('pattern',pat.hex(),'count',d.count(pat))
