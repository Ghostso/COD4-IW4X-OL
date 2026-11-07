import os, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\EARLIEST2_20261027_132645'
LO = 0x00010000
img=open(os.path.join(D,'snap_003.bin'),'rb').read()
cov=open(os.path.join(D,'snap_003_cover.bin'),'rb').read()
def rd(va,n):
    o=va-LO
    if o<0 or o+n>len(img) or sum(cov[o:o+n])!=n: return None
    return img[o:o+n]
def u32(va):
    b=rd(va,4)
    return struct.unpack('<I',b)[0] if b and len(b)==4 else None
U = 0x3ACA0CD8
print('=== 验证 0x%08X 是 dwRoomMatchUber 实例 ===' % U)
vt=u32(U)
print('  vtable = 0x%08X  (期望 0x00DC795C)' % vt if vt else '  vtable 读不到')
if vt:
    # 校验 vtable[0x68] == 0x63C5E0
    s68=u32(vt+0x68)
    print('  vtable+0x68 = 0x%08X  (期望 0x0063C5E0 = 自动开局状态机)' % s68 if s68 else '')
    s64=u32(vt+0x64)
    print('  vtable+0x64 = 0x%08X' % s64 if s64 else '')
# RTTI 校验
col=u32(vt-8) if vt else None
if col:
    b=rd(col,20)
    if b:
        sig,off,cd,pTD,pCD=struct.unpack('<IIIII',b)
        if sig==0 and pTD:
            nm=rd(pTD+8,110)
            if nm:
                e=nm.find(b'\x00')
                print('  RTTI = %s' % nm[:e].decode('latin1'))
print()
print('=== 该对象的 +0x20 状态字段 ===')
for off in (0x20,0x24,0x28,0x2C,0x10614):
    v=u32(U+off)
    print('  +0x%05X = %s' % (off, ('0x%08X (%d)'%(v,v)) if v is not None else '未覆盖'))
print()
print('=== MyEventHandler (vtable 0x00DC78F0) 这次有实例了吗 ===')
pat=struct.pack('<I',0x00DC78F0)
i=img.find(pat,0); n=0
while i>=0:
    if all(cov[i+k]==1 for k in range(4)):
        va=LO+i
        if not (0x00DC7800<=va<=0x00DC7A00):
            print('   实例候选 0x%08X' % va); n+=1
    i=img.find(pat,i+1)
print('   共 %d 个' % n)
print()
print('=== [0x849B61C] 已请求开局标志 ===')
b=rd(0x0849B61C,4)
print('  首个字节 = %d  (0=未请求, 1=已请求)' % b[0] if b else '未覆盖')
