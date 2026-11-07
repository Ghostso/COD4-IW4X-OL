import struct
p=r'D:\BaiduNetdiskDownload\使命召唤OL\_map_extract\coop_train_zone.bin'; d=open(p,'rb').read()
delta=0x30069e8d-0x23f5a4
allhits=[]
for o in range(0x23f800,0x240300):
 v=struct.unpack_from('<I',d,o)[0]
 if 0x30000000<=v<0x31000000:
  raw=v-delta
  if 0x23f81c<=raw<0x23f8f4: allhits.append(o)
print('hits',[hex(x) for x in allhits])
for base in range(0x23fc00,0x23fd00):
 for off in range(0,13):
  good=0
  for h in allhits:
   if h<base: continue
   q=h-base-off
   if q>=0 and q%36==0 and q//36<30: good+=1
  if good>=6: print('base',hex(base),'off',off,'good',good,'res',[((h-base-off)//36 if h>=base and (h-base-off)>=0 and (h-base-off)%36==0 else -1) for h in allhits])
