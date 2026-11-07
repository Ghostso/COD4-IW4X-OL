import struct
root=r'D:\BaiduNetdiskDownload\使命召唤OL'; d=open(root+r'\_map_extract\coop_train_zone.bin','rb').read()
b=b'clip_player\x00clip_shot_block\x00clip_full\x00clip\x00'; s=d.find(b); print(hex(s),len(b),hex(s+len(b)),hex((s+len(b)+3)&~3))
o=(s+len(b)+3)&~3
for i in range(30):
 p=struct.unpack_from('<I',d,o+i*8)[0]; print(i,hex(o+i*8),hex(p),hex(p-(0x30069e8d-0x23f5a4)))
