# -*- coding: utf-8 -*-
"""scanstore.py TARGET_VA -- 找出所有以该绝对地址为**目的操作数**的存储指令
（89 xx / C7 05 / A3 等），并反汇编上下文，用于定位隐藏 IAT 的填充点。"""
import sys, io, os, struct
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from verify import P

t = int(sys.argv[1], 16)
need = struct.pack('<I', t)
o = []
hits = []
for va, vs, ra, rs, ch in P.secs:
    if not (ch & 0x20000000):
        continue
    buf = P.d[ra:ra + min(vs, rs)]
    i = 0
    while True:
        j = buf.find(need, i)
        if j < 0:
            break
        hits.append(va + j)
        i = j + 1
o.append('target %08X  exec-hits=%d' % (t, len(hits)))

# 指令起点：moffs 形式 = 命中点 - 1 (A3/A1) 或 - 2 (89 05 / 8B 05 / C7 05)；C7 05 是 -2 且共 10 字节
for h in hits:
    info = []
    for st in range(h - 1, h - 7, -1):
        b = P.rd(st, 16)
        if not b:
            continue
        try:
            ds = list(__import__('capstone').Cs(__import__('capstone').CS_ARCH_X86,
                                                __import__('capstone').CS_MODE_32).disasm(b, st, count=1))
        except Exception:
            continue
        if not ds:
            continue
        ins = ds[0]
        if ins.address + ins.size != h + 4:
            continue
        txt = ins.mnemonic + ' ' + ins.op_str
        if ('[0x%x]' % t) in txt and txt.startswith('mov') and ', ' in txt:
            dst = txt.split(',', 1)[0]
            if '[0x%x]' % t in dst and 'ptr' in dst:
                info.append((st, txt))
    if info:
        st, txt = info[0]
        o.append('  STORE @%08X  %s' % (st, txt))
    else:
        # 报告全部命中点，供人工判别
        o.append('  hit   @%08X  (未识别为存储)' % h)

txt = '\n'.join(o)
io.open(os.path.join(HERE, 'out', 'scanstore.txt'), 'w', encoding='utf-8').write(txt + '\n')
sys.stdout.write(txt.encode('ascii', 'backslashreplace').decode('ascii') + '\n')
