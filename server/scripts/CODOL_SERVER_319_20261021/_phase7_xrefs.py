import struct
p=r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin'; d=open(p,'rb').read()
targets=[0x4EC500,0x4EC000,0x4E88D0,0x5AD350,0x5ADD76,0x5AD300]
for t in targets:
 refs=[]
 for o in range(0x1000,0xa79000-5):
  if d[o]==0xe8:
   rel=struct.unpack_from('<i',d,o+1)[0]
   dst=(o+0x400000)+5+rel
   if dst==t: refs.append(o+0x400000)
 print(hex(t),[hex(x) for x in refs[:80]],'count',len(refs))
