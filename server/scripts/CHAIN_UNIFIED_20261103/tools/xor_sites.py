"""找出所有 "xor r32, 0xD362501F" 指令点(引擎指针的解码点), 并向后列出间接调用。
   引擎对象 = [0x331C0C8] ^ 0xD362501F; 拿到它之后若走 vtable 就是我们要找的 connect 调用。

用法:
  python -I xor_sites.py                 # 默认钥匙 0xD362501F
  python -I xor_sites.py 0xD362501F --len 0x80
"""
import sys
sys.path.insert(0, __file__.rsplit('\\', 1)[0])
from pe_map import load, va2off
import capstone

P = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\UNPACKED_146\codoMP_unpacked_146.exe'
d, ib, secs = load(P)
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
md.skipdata = True

key = int(sys.argv[1], 0) if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else 0xD362501F
length = 0x80
for i, a in enumerate(sys.argv):
    if a == '--len':
        length = int(sys.argv[i + 1], 0)

kb = key.to_bytes(4, 'little')
# xor eax, imm32 = 35 imm32 ; xor r/m32, imm32 = 81 /6 modrm=11xxx000 → F0..F7
pats = [b'\x35' + kb] + [b'\x81' + bytes([0xF0 + r]) + kb for r in range(8)]

sites = []
for pat in pats:
    for va_, vs, ra, rs in secs:
        n = min(vs, rs)
        if n <= 0 or ra <= 0:
            continue
        blob = d[ra:ra + n]
        i = blob.find(pat)
        while i >= 0:
            sites.append((ib + va_ + i, pat.hex()))
            i = blob.find(pat, i + 1)

sites.sort()
print('xor r32, 0x%08X 命中 %d 处 (真指令形态)\n' % (key, len(sites)))
for va, pat in sites:
    o = va2off(secs, ib, va)
    if o is None:
        continue
    ind = []
    try:
        for ins in md.disasm(d[o:o + length], va):
            if ins.mnemonic == 'call' and ('[' in ins.op_str or ins.op_str.strip() in
                                           ('eax', 'ebx', 'ecx', 'edx', 'esi', 'edi')):
                ind.append('      %08X  call %s' % (ins.address, ins.op_str))
    except Exception:
        pass
    print('--- xor@%08X  (%s) ---' % (va, pat))
    if ind:
        for line in ind:
            print(line)
    else:
        print('      (后方 0x%X 字节内无间接 call)' % length)
    print()
