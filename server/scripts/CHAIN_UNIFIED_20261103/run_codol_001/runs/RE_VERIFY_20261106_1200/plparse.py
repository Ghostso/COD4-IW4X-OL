# -*- coding: utf-8 -*-
"""plparse.py <info> [out] -- 解压 playlist .info，列出每个 playlist 的 rule 1011/3265"""
import sys, io, zlib, re, os
HERE = os.path.dirname(os.path.abspath(__file__))
p = sys.argv[1]
t = zlib.decompress(open(p, 'rb').read()).decode('latin1')
blocks = re.split(r'(?m)^name\s+', t)
o = ['file: %s  (decompressed %d B)' % (os.path.basename(p), len(t))]
gate_fail = []
for b in blocks[1:]:
    nm = b.split('\n', 1)[0].strip().strip('"')
    kv = dict(re.findall(r'(?m)^rule\s+(1011|3265)\s+(\S+)', b))
    v2 = int(kv.get('3265', '0') or 0)
    tag = '  <== 3265<=1 : 闸2 不过(设计上不连战斗服)' if v2 <= 1 else ''
    if v2 <= 1:
        gate_fail.append(nm)
    o.append('%-36s 1011=%-5s 3265=%-5s%s' % (nm, kv.get('1011', '-'), kv.get('3265', '-'), tag))
o.append('')
o.append('共 %d 个 playlist，其中 %d 个 3265<=1：%s' % (len(blocks) - 1, len(gate_fail), ', '.join(gate_fail)))
txt = '\n'.join(o)
dst = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, 'out', 'playlists.txt')
io.open(dst, 'w', encoding='utf-8').write(txt + '\n')
sys.stdout.write(txt.encode('ascii', 'backslashreplace').decode('ascii') + '\n')
