# -*- coding: utf-8 -*-
"""discover.py -- 给定 (近似地址, 期望指令文本)，在 ±N 字节窗口内找到真实指令地址。
输出 JSON：{id: {va, insn, exact}}，供生成 tasks.json 用。
用法： python -I discover.py claims.json found.json
"""
import sys, os, json, struct, io
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
HERE = os.path.dirname(os.path.abspath(__file__))
BIN = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\UNPACKED_146\codoMP_unpacked_146.exe'
d = io.open(BIN, 'rb').read()
e = struct.unpack_from('<I', d, 0x3C)[0]
ib = struct.unpack_from('<I', d, e + 0x34)[0]
nsec = struct.unpack_from('<H', d, e + 6)[0]
opt = struct.unpack_from('<H', d, e + 20)[0]
s0 = e + 24 + opt
SECS = []
for k in range(nsec):
    o = s0 + 40 * k
    vs, va, rs, ra = struct.unpack_from('<IIII', d, o + 8)
    ch = struct.unpack_from('<I', d, o + 36)[0]
    SECS.append((ib + va, vs, ra, rs, ch))

def rd(va, n):
    for v, vs, ra, rs, ch in SECS:
        if v <= va < v + max(vs, rs):
            return d[ra + (va - v): ra + (va - v) + n]
    return None

MD = Cs(CS_ARCH_X86, CS_MODE_32)
def ntx(s):
    return ' '.join(s.lower().replace('\t', ' ').split())

def find(near, text, win=32):
    """在 [near-win, near+win] 内找文本匹配的指令（窗口内线性反汇编起点 == 段头? 不，
    用 multiplicity：从 near-win 起线性反汇编，收集所有指令，取文本匹配且地址最接近 near 的。"""
    out = []
    for start in range(near - win, near + win + 1):
        buf = rd(start, 32)
        if not buf:
            continue
        try:
            ins = next(MD.disasm(buf, start))
        except StopIteration:
            continue
        t = ntx(ins.mnemonic + ' ' + ins.op_str)
        if text.lower() in t:
            out.append((abs(start - near), start, t))
    if not out:
        return None
    out.sort()
    return {'va': '0x%08X' % out[0][1], 'insn': out[0][2], 'dist': out[0][0], 'exact': out[0][0] == 0}

def main():
    claims = json.load(io.open(sys.argv[1], encoding='utf-8'))
    res = {}
    for c in claims:
        near = int(c['near'], 16)
        for want in ([c['text']] if isinstance(c['text'], str) else c['text']):
            r = find(near, want)
            key = c['id']
            if isinstance(c['text'], list):
                key = c['id'] + ':seq'
                res.setdefault(key, []).append(r)
            else:
                res[key] = r
        print('%-24s near=%08X want=%-40s -> %s' % (
            c['id'], near, c['text'] if isinstance(c['text'], str) else '|'.join(c['text']),
            json.dumps(res.get(c['id'], res.get(c['id'] + ':seq')), ensure_ascii=False)))
    json.dump(res, io.open(sys.argv[2], 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    print('-> ' + sys.argv[2])

if __name__ == '__main__':
    main()
