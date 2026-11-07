# -*- coding: utf-8 -*-
"""peimports.py [VA...] -- 解析 PE 导入目录，把所有 IAT 槽 -> (DLL, 函数名) 打印出来；
给 VA 则只报告命中它的那一项。"""
import sys, io, os, struct
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from verify import P

d = P.d
e = struct.unpack_from('<I', d, 0x3C)[0]
opt = struct.unpack_from('<H', d, e + 20)[0]
opt_off = e + 24
magic = struct.unpack_from('<H', d, opt_off)[0]
dd_off = opt_off + (96 if magic == 0x10B else 112)
imp_rva, imp_sz = struct.unpack_from('<II', d, dd_off + 8 * 1)
print('magic=%X ImageBase=%08X ImportDir RVA=%X size=%X' % (magic, P.ib, imp_rva, imp_sz))

def rva2va(r): return P.ib + r

def rdstr(va, n=128):
    b = P.rd(va, n)
    if b is None: return None
    z = b.find(b'\x00')
    return (b[:z] if z >= 0 else b).decode('latin1')

targets = set()
for a in sys.argv[1:]:
    targets.add(int(a, 16))

out = []
va_desc = rva2va(imp_rva)
i = 0
found = {}
while True:
    raw = P.rd(va_desc + 20 * i, 20)
    if raw is None or len(raw) < 20:
        break
    oft, tds, fc, name_rva, ft = struct.unpack('<IIIII', raw)
    if oft == 0 and name_rva == 0 and ft == 0:
        break
    dll = rdstr(rva2va(name_rva)) or '?'
    out.append('DLL[%d] %-24s OFT=%08X FT=%08X' % (i, dll, rva2va(oft) if oft else 0, rva2va(ft) if ft else 0))
    thunk_src = rva2va(oft) if oft else rva2va(ft)
    ft_va = rva2va(ft)
    j = 0
    while True:
        t = P.u32(thunk_src + 4 * j)
        if t is None or t == 0:
            break
        slot = ft_va + 4 * j
        if t & 0x80000000:
            nm = 'ord#%d' % (t & 0xFFFF)
        else:
            nm_va = rva2va(t) + 2
            nm = rdstr(nm_va, 96) or '?'
        found.setdefault(slot, []).append((dll, nm))
        if slot in targets:
            out.append('  ★ MATCH %08X -> %s!%s' % (slot, dll, nm))
        j += 1
        if j > 20000:
            break
    i += 1
    if i > 500:
        break

out.append('')
out.append('IAT 槽总数 = %d' % len(found))
out.append('槽地址范围 = %08X .. %08X' % (min(found), max(found)) if found else 'none')
for t in sorted(targets):
    if t in found:
        for dll, nm in found[t]:
            out.append('TARGET %08X -> %s!%s' % (t, dll, nm))
    else:
        out.append('TARGET %08X -> <不在导入表>' % t)

txt = '\n'.join(out)
io.open(os.path.join(HERE, 'out', 'imports.txt'), 'w', encoding='utf-8').write(txt + '\n')
sys.stdout.write(txt.encode('ascii', 'backslashreplace').decode('ascii') + '\n')
