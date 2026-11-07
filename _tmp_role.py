import os, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
D = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\EARLIEST2_20261027_132645'
LO = 0x00010000
img=open(os.path.join(D,'snap_004.bin'),'rb').read()
cov=open(os.path.join(D,'snap_004_cover.bin'),'rb').read()
def rd(va,n):
    o=va-LO
    if o<0 or o+n>len(img) or sum(cov[o:o+n])!=n: return None
    return img[o:o+n]
def cstr(va,n=120):
    b=rd(va,n)
    if b is None or len(b)<2: return None
    e=b.find(b'\x00')
    if e<1: return None
    t=b[:e].decode('latin1')
    return t if all(32<=ord(c)<127 for c in t) else None
print('=== 命令行 vs 脚本绑定: 看 0xDC0Dxx 这片字符串是怎么被用的 ===')
print('  0x644E20 里: push "setdvar" -> 再 push 到 call [edx+0x14]')
print('  这是"按名字查某个值"的取值器形态, 不是命令注册')
print()
print('=== 对照: 真正的控制台命令注册长什么样 (room.match.* 那次) ===')
print('  0x63B0F0: mov esi,"room.match.quick" / call 0x4F37A0 / 返回非0表示已存在')
print('            mov [0xE9C66B8], esi / mov [0xE9C66BC], 0x63A720')
print('            => 把"名字 + 函数指针"填进一个链表节点')
print()
print('=== 所以 setdvar 在本 build 里的角色 ===')
# 检查 0xDC0DBC 附近是不是一个"脚本内置函数名表"
print('  同片字符串: setdvar / ForceCollectGarbage / Dvar_GetBool / Dvar_GetInt')
print('             Dvar_GetFloat / Dvar_GetString / Dvar_GetEnumLength / execnow')
print('  => 这是 ENGINE 暴露给脚本层的内置函数名表')
print()
print('=== 关键: 这些名字是否被 Cmd_AddCommand 类函数注册? ===')
# 0x4F37A0 是命令查找; 找 call 0x4F37A0 且 push setdvar 的
pat=struct.pack('<I',0x00DC0DBC)
i=img.find(pat,0)
while i>=0:
    va=LO+i
    if 0x400000<=va<0x0EA59000 and all(cov[i+k]==1 for k in range(4)):
        # 看前 12 字节有没有 call 到 0x4F37A0 附近
        pre=img[i-16:i]
        print('   引用 0x%08X, 前16字节: %s' % (va, pre.hex(' ')))
    i=img.find(pat,i+1)
