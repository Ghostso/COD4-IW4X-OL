import os, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = r'run_codol_001\runs\EARLIEST_20261027_123806'
LO = 0x00010000
img = open(os.path.join(D,'snap_002.bin'),'rb').read()
cov = open(os.path.join(D,'snap_002_cover.bin'),'rb').read()
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
print('=== 谁能创建 MyEventHandler: 找 dwRoomMatch 相关的其它类 ===')
for va in range(0x00E6EF80, 0x00E6F080, 4):
    s=cstr(va,110)
    if s and s.startswith('.?A'):
        print('   0x%08X  %s' % (va,s))
print()
print('=== 关键: 0x63B500 由 vtable 驱动, 那 0x63B500 之前"谁负责注册这个 handler" ===')
print('   dwRoomMatch::Init 是 static void. 找 .text 里所有 55 8B EC 且引用了')
print('   0xDC6D8C (room.match.quick) 的函数, 看是不是 Init')
# 0x63B0F0 引用了 room.match.quick
print()
print('=== 0x63B0F0 (注册命令的那个函数) 的调用者 0x639E16 上下文 ===')
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
md=Cs(CS_ARCH_X86, CS_MODE_32)
c=rd(0x00639DF0,0x60)
for ins in md.disasm(c,0x00639DF0):
    ann=''
    if '0x' in ins.op_str:
        for tok in ins.op_str.replace(',',' ').split():
            if tok.startswith('0x'):
                try: v=int(tok,16)
                except: continue
                if 0x00C00000<=v<=0x01100000:
                    s=cstr(v,60)
                    if s and len(s)>=3: ann='; \"%s\"'%s
    mk='  <<< call 63B0F0' if ins.address==0x00639E16 else ''
    print('  %08X  %-18s %-7s %-26s%s%s' % (ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str,ann,mk))
    if ins.address>0x00639E25: break
