"""从内存转储自动提取所有 dwRoomMessage* 的 serialize/deserialize 规格。

原理: 每条消息 vtable[0]=serialize, vtable[1]=deserialize。函数体固定套路:
    call 0xB77B10 (writeBits)  arg = push 的 5 位标签常量
    call 0xB777C0 (writeData)  args = (ptr, nbits), nbits 在倒数第二个 push
少数路径用 `mov dword [esp], imm` 代替 push, 一并识别。

用法: python -I tools/room_msg_spec.py <out.md>
只读转储, 不写任何受保护路径。
"""
import json
import os
import sys

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

D = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\MEMDUMP_20261027_v4\mem'
FIX = r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_SERVER_319_20261021\fixtures\dwroommsg_vtables_20261027.json'
OUT = sys.argv[1] if len(sys.argv) > 1 else 'room_msg_spec.md'

regions = []
for line in open(os.path.join(D, 'regions.txt'), encoding='utf-8'):
    if line.startswith('#'):
        continue
    p = line.split()
    if len(p) >= 5:
        regions.append((int(p[0], 16), int(p[1], 16), p[4], int(p[2], 16)))

CACHE = {}


def blob(fn):
    if fn not in CACHE:
        CACHE[fn] = open(os.path.join(D, fn), 'rb').read()
    return CACHE[fn]


def read_at(va, n):
    for base, size, fn, _p in regions:
        if base <= va < base + size and va + n <= base + size:
            return blob(fn)[va - base:va - base + n]
    return None


WRITE_BITS, WRITE_DATA = 0x00B77B10, 0x00B777C0
READ_BITS, READ_DATA = 0x00B774E0, 0x00B772E0
KNOWN = {WRITE_BITS: 'B', WRITE_DATA: 'D', READ_BITS: 'R', READ_DATA: 'r'}
md = Cs(CS_ARCH_X86, CS_MODE_32)


def decode(va, max_insns=140):
    code = read_at(va, 0x400)
    if not code:
        return []
    insns = list(md.disasm(code, va))[:max_insns]
    ops = []
    pushes = []
    for ins in insns:
        m, o = ins.mnemonic, ins.op_str
        if m == 'push':
            if o.startswith('0x'):
                pushes.append(int(o, 16))
            elif o.lstrip('-').isdigit():
                pushes.append(int(o))
            else:
                pushes.append(None)
            pushes = pushes[-4:]
        elif m == 'mov' and o.startswith('dword ptr [esp'):
            # mov dword ptr [esp], imm  —— 等价于 push imm
            v = o.rsplit(',', 1)[-1].strip()
            pushes.append(int(v, 16) if v.startswith('0x') else
                          (int(v) if v.lstrip('-').isdigit() else None))
            pushes = pushes[-4:]
        elif m == 'call':
            tgt = int(o, 16) if o.startswith('0x') else None
            kind = KNOWN.get(tgt)
            if kind:
                vals = [v for v in pushes if v is not None]
                if kind in ('B', 'R'):
                    ops.append((kind, vals[-1] if vals else None))
                else:
                    # writeData(ptr, nbits): nbits 先压栈 -> 第一个常立即数
                    ops.append((kind, vals[0] if vals else None))
            pushes = []
        elif m.startswith('j'):
            pushes = []
        elif m == 'ret':
            break
    return ops


entries = json.load(open(FIX, encoding='utf-8'))
rows = []
for e in entries:
    name = e['name']
    if not name.startswith('?AVdwRoomMessage'):
        continue
    vf = [v for v in (e.get('vfuncs_clean') or []) if v]
    if not vf:
        continue
    ser = decode(vf[0])
    rows.append((name, e['vtable_va'], vf[0], vf[1] if len(vf) > 1 else 0, ser))

lines = ['# dwRoomMessage* 位流规格（自动提取）', '',
         '来源: `MEMDUMP_20261027_v4` 运行时内存转储（VA 直接可读）。',
         '记法: `B(tag)` = writeBits(5 位常量)；`D(bits)` = writeData(bits 位)。',
         '每条消息 = 头部 `B(0x3)` + type 字节(D 8) + 字段序列。', '']
kept = 0
for name, vt, sv, dv, ser in rows:
    short = name.replace('?AV', '').replace('@@', '')
    if not ser:
        continue
    kept += 1
    txt = ' '.join(('B(0x%X)' % v) if k == 'B' else ('D(%s)' % (v if v else '?'))
                   for k, v in ser)
    lines.append('## %s' % short)
    lines.append('')
    lines.append('`serialize=0x%08X`  vtable=`0x%08X`' % (sv, vt))
    lines.append('')
    lines.append('    %s' % txt)
    lines.append('')

open(OUT, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
print(OUT, kept, 'messages')
