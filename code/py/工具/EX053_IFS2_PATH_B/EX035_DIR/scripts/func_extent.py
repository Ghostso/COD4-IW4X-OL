"""确定调用点所在函数的真实入口/范围（只读）。

方法：线性解码整个 .text，收集所有分支目标（E8/E9/EB/7x/0F8x/E3），
对每个调用点，取「上一个 ret 或无条件 jmp 之后」的地址为块起点，
再回退到最近的一个「被其它位置跳入」的地址 = 真入口。
同时收集 call[imm32] 的槽名。
"""
import sys, os, struct, bisect
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pe import Image
import importmap
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
img = Image()
IMAGE_BASE = 0x10000000

md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = False
sec = [s for s in img.sections if s['name'] == '.text'][0]
buf = img.data[sec['raw']:sec['raw']+sec['rawsize']]
base = sec['va']
print('textarea RVA 0x%x size 0x%x' % (base, len(buf)))

targets = set()
calls = []   # (va, slotva)
pos = 0
N = len(buf)
while pos < N:
    m = md.disasm_lite(buf[pos:pos+16], base+pos)
    got = 0
    for (a, size, mn, ops) in m:
        got = a - (base+pos) + size
    if got == 0:
        pos += 1
        continue
    # 重新逐条判分支
    for (a, size, mn, ops) in md.disasm_lite(buf[pos:pos+got], base+pos):
        if mn.startswith('j') and ops.startswith('0x'):
            try: targets.add(int(ops, 16))
            except: pass
        elif mn == 'call':
            if ops.startswith('0x'):
                try: targets.add(int(ops, 16))
                except: pass
            elif ops.startswith('dword ptr [0x'):
                try: calls.append((a, int(ops[13:-1], 16) - IMAGE_BASE))
                except: pass
    pos += got
print('分支目标 %d 个, call[slot] %d 个' % (len(targets), len(calls)))
slots = importmap.build(img)

tgt = sorted(targets)
def enclosing(va, maxback=0x2000):
    """回退到最近的分支目标（且其间无 ret 阻断）作为函数入口候选。"""
    i = bisect.bisect_right(tgt, va) - 1
    cands = []
    while i >= 0 and tgt[i] > va - maxback:
        cands.append(tgt[i]); i -= 1
    return cands

for tag, va in [('A connect', 0x00425802), ('B connect', 0x00650d4e),
                ('A bind+listen', 0x00431460), ('B bind+listen', 0x006747c0),
                ('A getaddrinfo', 0x0044b240), ('B getaddrinfo', 0x0065fca0)]:
    print('== %s 0x%08x  近邻分支目标: %s' % (tag, va, ' '.join('0x%08x'%x for x in enclosing(va,0x400)[:6])))
print()
print('-- 关键槽名 --')
for sv in (0x10b02ac4, 0x10b02b4c, 0x10b02ab0, 0x10b02b38, 0x10b02ab4, 0x10b02b10):
    print('  [0x%08x] = %s' % (sv, slots.get(sv-IMAGE_BASE, '??')))
print()
print('-- A/B connect 的 caller（谁 call 这个槽）--')
for (a, r) in calls:
    if r in (0x10b02ac4-IMAGE_BASE, 0x10b02b4c-IMAGE_BASE):
        print('  0x%08x -> %s' % (a, slots.get(r)))
