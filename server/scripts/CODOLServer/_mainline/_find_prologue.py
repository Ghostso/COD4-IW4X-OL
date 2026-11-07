import pefile
p=r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\Cross\ProtocalHandler.dll'
pe=pefile.PE(p,fast_load=True); data=open(p,'rb').read()
anchor=0x7A44F
print('candidate prologues within 0x3000 before anchor:')
for i in range(anchor, max(0,anchor-0x3000), -1):
    if data[i:i+3] in (b'\x55\x8b\xec', b'\x55\x8b\x6c', b'\x55\x8b\xe5'):
        print('  off=%X bytes=%s'%(i,data[i:i+16].hex(' ')))
print('CC padding before anchor:')
for i in range(anchor, max(0,anchor-0x200), -1):
    if data[i:i+8] == b'\xcc'*8:
        print('  CC8 at off=%X'%i); break
