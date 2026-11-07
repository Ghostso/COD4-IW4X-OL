import os, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\FIXMC_20261027_140146'
LO = 0x00010000
img=open(os.path.join(D,'snap_004.bin'),'rb').read()
cov=open(os.path.join(D,'snap_004_cover.bin'),'rb').read()
def rd(va,n):
    o=va-LO
    if o<0 or o+n>len(img) or sum(cov[o:o+n])!=n: return None
    return img[o:o+n]
def u32(va):
    b=rd(va,4); return struct.unpack('<I',b)[0] if b and len(b)==4 else None
def u8(va):
    b=rd(va,1); return b[0] if b else None
print('=== 3291 的 flags 是否含 0x8 (NCS 网络分发条件) ===')
h=u32(0x08269818)
print('  句柄 = 0x%08X' % (h or 0))
if h:
    fl=u32(h+4)
    print('  flags = 0x%08X' % (fl or 0))
    print('  flags & 0x8 = %d   -> %s' % ((fl or 0)&8, '会进 NCS 表' if (fl or 0)&8 else '★ 不会进 NCS 表'))
print()
print('=== 对照: dw_autoStartGame / 其他常见 dvar 的 flags ===')
for g,label in ((0x0849B7A4,'dw_autoStartGame'),(0x0849B7C4,'dw_enterRoomCountingDown'),
                (0x0849B7C8,'dw_enterGameNextMapCountingDown')):
    h=u32(g)
    if not h: continue
    fl=u32(h+4)
    print('  %-34s flags=0x%08X  &0x8=%d' % (label, fl or 0, (fl or 0)&8))
print()
print('=== NCS 三张表当前的填充情况 ===')
for addr,cap,arr,label in ((0x077E08D4,0x14,0x077E08E4,'ncs_codinfo_dvar'),
                           (0x077E0DE8,0x15,0x077E0DF8,'ncs_codinfovalue_dvar'),
                           (0x077E0DFC,0x16,0x077E0E0C,'ncs_network_dvar')):
    cnt=u32(addr+4)      # +0x04 是已用量
    print('  %-22s 记录容量=%d 已用=%s' % (label, cap, cnt))
