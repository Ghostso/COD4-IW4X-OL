import os, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
D = r'run_codol_001\runs\MEMDUMP_20261027_v4\mem'
def read_va(va, n):
    for line in open(os.path.join(D,'regions.txt'), encoding='utf-8', errors='replace'):
        if line.startswith('#'): continue
        p = line.split()
        if len(p) < 5: continue
        base, size = int(p[0],16), int(p[1],16)
        if base <= va < base+size:
            f = open(os.path.join(D,p[4]),'rb').read()
            return f[va-base:va-base+n]
    return None
def cstr(va, n=64):
    b = read_va(va,n)
    if not b: return None
    e=b.find(b'\x00')
    return b[:e].decode('latin1') if e>=0 else None
print('=== 名字指针表 0x007E8700..0x007E87A0 ===')
blk = read_va(0x007E8700, 0xA0)
for k in range(0,0xA0,4):
    v = struct.unpack_from('<I', blk, k)[0]
    s = cstr(v) if 0x00D00000 <= v <= 0x01000000 else None
    if s and len(s)>=3:
        print('   0x%08X -> 0x%08X "%s"' % (0x007E8700+k, v, s))
print()
print('=== 反汇编 0x007E86C0..0x007E87B0 ===')
code = read_va(0x007E86C0, 0xF0)
md = Cs(CS_ARCH_X86, CS_MODE_32)
for ins in md.disasm(code, 0x007E86C0):
    ann = ''
    if '0x' in ins.op_str:
        for tok in ins.op_str.replace(',',' ').split():
            if tok.startswith('0x'):
                try: va=int(tok,16)
                except: continue
                if 0x00D00000 <= va <= 0x01000000:
                    s=cstr(va)
                    if s and len(s)>=3 and all(32<=ord(c)<127 for c in s): ann='; "%s"'%s
    print('  %08X  %-24s %-7s %-30s%s' % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str, ann))
