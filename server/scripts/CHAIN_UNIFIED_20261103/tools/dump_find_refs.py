"""在 dump 的区域里找"对某地址的调用/取址":
   - E8 rel32 (call) / E9 rel32 (jmp)
   - 绝对立即数 68 <imm32> (push) / B8+r <imm32> (mov reg,imm) / C7 4? <disp> <imm32>
   - FF 15 <imm32> (call [abs])
   region 的 base 用**绝对 VA**, 所以 rel32 的目标按 base+i+5+rel 计算。

用法: python -I dump_find_refs.py <regions.txt> <dump_dir> 0xBB45E0 [0xBB2C40 ...]
"""
import sys, os
sys.path.insert(0, __file__.rsplit('\\', 1)[0])

regf, ddir = sys.argv[1], sys.argv[2]
targets = [int(a, 16) for a in sys.argv[3:]]

regs = []
for ln in open(regf):
    ln = ln.strip()
    if not ln or ln.startswith('#'):
        continue
    p = ln.split()
    regs.append((int(p[0], 16), int(p[1], 16), p[2]))

for t in targets:
    print('### 目标 0x%08X ###' % t)
    n = 0
    for b, s, f in regs:
        fp = os.path.join(ddir, f)
        if not os.path.exists(fp):
            continue
        blob = open(fp, 'rb').read()
        # E8/E9 rel32
        for op, kind in ((0xE8, 'E8 call'), (0xE9, 'E9 jmp')):
            i = 0
            while True:
                i = blob.find(bytes([op]), i)
                if i < 0 or i + 5 > len(blob):
                    break
                va = b + i
                r = int.from_bytes(blob[i + 1:i + 5], 'little', signed=True)
                if (va + 5 + r) & 0xFFFFFFFF == t:
                    print('   %s @ 0x%08X  (区域 0x%08X+0x%X, %s)' % (kind, va, b, s, f))
                    n += 1
                i += 1
        # 绝对立即数
        tb = t.to_bytes(4, 'little')
        for pre in (b'\x68', b'\x15'):      # push imm32 / call [abs] 的 disp 部分
            i = 0
            while True:
                i = blob.find(pre + tb, i)
                if i < 0:
                    break
                va = b + i
                print('   %s@ 0x%08X  (区域 0x%08X+0x%X, %s)'
                      % ('push imm32 ' if pre == b'\x68' else '?abs ',
                         va, b, s, f))
                n += 1
                i += 1
        i = 0
        while True:                          # B8+r imm32
            i = blob.find(b'\xb8' + tb, i)
            if i < 0:
                break
            print('   mov eax,imm32 @ 0x%08X  (区域 0x%08X+0x%X, %s)' % (b + i, b, s, f))
            n += 1
            i += 1
    if n == 0:
        print('   ★ 全 dump 未命中')
    print()
