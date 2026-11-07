import os, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = r'run_codol_001\runs\MEMDUMP_20261027_v4\mem'
idxs=[]
for line in open(os.path.join(D,'regions.txt'), encoding='utf-8', errors='replace'):
    if line.startswith('#'): continue
    p=line.split()
    if len(p)>=5: idxs.append((int(p[0],16), int(p[1],16), p[4]))
import re
# 在 EXE 里找 game-start 相关的协议名 / 连接发起标记
keys=[b'NET_OutOfBandPrint', b'CL_Connect', b'CL_ConnectToServer', b'connectToServer',
      b'MSG_WriteConnect', b'net_connect', b'CL_InitDownloads', b'NET_ConnectPacket']
found={}
for base,size,fn in idxs:
    if not (0x400000<=base<0x0EA59000): continue
    try: dd=open(os.path.join(D,fn),'rb').read()
    except: continue
    for k in keys:
        i=dd.find(k)
        if i>=0: found.setdefault(k,[]).append((base+i,fn))
for k in keys:
    v=found.get(k)
    print('%-26s %s' % (k.decode(), ('0x%08X'%v[0][0]) if v else '未见'))
print()
print('=== 客户端是否已经采集过 28960 地址 (search 0x7120=28960 LE u16) ===')
pat=struct.pack('<H',28960)
n=0
for base,size,fn in idxs:
    if not (0x08100000<=base<=0x08200000): continue
    try: dd=open(os.path.join(D,fn),'rb').read()
    except: continue
    i=dd.find(pat)
    while i>=0 and n<15:
        ctx=dd[max(0,i-16):i+20]
        print('   0x%08X  %s' % (base+i, ctx.hex(' ')))
        n+=1; i=dd.find(pat,i+1)
