import os, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = r'run_codol_001\runs\MEMDUMP_20261027_v4\mem'
idxs=[]
for line in open(os.path.join(D,'regions.txt'), encoding='utf-8', errors='replace'):
    if line.startswith('#'): continue
    p=line.split()
    if len(p)>=5: idxs.append((int(p[0],16), int(p[1],16), p[4]))
def read_va(va,n):
    for base,size,fn in idxs:
        if base <= va < base+size:
            f=open(os.path.join(D,fn),'rb').read()
            return f[va-base:va-base+n]
    return None
# dw_roomJoin 是 string 类型 (type 6)
b = read_va(0x0810A9F8, 24)
w = struct.unpack('<6I', b)
print('dw_roomJoin  dvar 对象 @0x0810A9F8')
print('  [0] name ptr = 0x%08X' % w[0])
nb = read_va(w[0], 48); print('  name = %r' % nb.split(b'\x00')[0].decode('latin1'))
print('  [1]=0x%08X [2]=type 0x%X [3]=当前值 0x%08X' % (w[1], w[2], w[3]))
vb = read_va(w[3], 96)
print('  string 值指针 0x%08X' % w[3])
if vb:
    print('  内容 = %r' % vb.split(b'\x00')[0].decode('latin1', 'replace'))
print()
# 也看 dw_globalChatRejoinInterval
for nm,addr in (('dw_globalChatRejoinInterval',0x0810B5D8),('dw_channelConnectRetryCount',0x0810B708)):
    b = read_va(addr, 24); w = struct.unpack('<6I', b)
    print('%s @0x%08X type=0x%X value=%d' % (nm, addr, w[2], w[3]))
