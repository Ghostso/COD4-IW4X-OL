"""把协议库套到所有历史上行样本上，验证通用性并找出字段变化规律。

数据源: 各 run 的 lobby_srv.log 里 payload() 明文。
只取 11/4 的（payload 以 0a <roomId> 开头且含 13 08）。
"""
import glob
import importlib.util
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('rp', os.path.join(HERE, 'room_protocol.py'))
rp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rp)

ROOT = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs'
logs = glob.glob(os.path.join(ROOT, '**', 'lobby_srv.log'), recursive=True)
print('日志 %d 份' % len(logs))

samples = []
for lp in logs:
    txt = open(lp, encoding='utf-8', errors='replace').read()
    for m in re.finditer(r'payload\((\d+)\):\s*((?:[0-9a-f]{2} )+)', txt):
        raw = bytes.fromhex(m.group(2).replace(' ', ''))
        # 11/4 的明文形如: 0a <u64> 13 08 ... 08 <u32>
        if len(raw) < 16 or raw[0] != 0x0A:
            continue
        if raw[9:11] != b'\x13\x08':
            continue
        rid = int.from_bytes(raw[1:9], 'little')
        if rid == 0:
            continue
        ln = int.from_bytes(raw[11:15], 'little')
        inner = raw[15:15 + ln]
        if len(inner) != ln or len(inner) < 8:
            continue
        decl = int.from_bytes(inner[0:4], 'little')
        samples.append({
            'log': os.path.basename(os.path.dirname(lp)),
            'payload_len': len(raw),
            'room': rid,
            'inner_len': ln,
            'declared': decl,
            'ok': decl == len(inner) - 4,
            'body': inner[4:],
        })

print('候选 11/4 样本 %d 条' % len(samples))
print()
print('%-22s %5s %18s %6s %6s %5s'
      % ('run', 'plen', 'roomId', 'ilen', 'decl', 'ok'))
for s in samples:
    print('%-22s %5d 0x%016X %6d %6d %5s'
          % (s['log'][:22], s['payload_len'], s['room'], s['inner_len'],
             s['declared'], s['ok']))

print()
print('=== 按 body 长度分组（同一类操作应有相同长度）===')
by_len = {}
for s in samples:
    by_len.setdefault(len(s['body']), []).append(s)
for ln in sorted(by_len):
    grp = by_len[ln]
    print('  body=%3d B  ×%d' % (ln, len(grp)))
    # 找不同位置的差异
    if len(grp) > 1:
        base = grp[0]['body']
        diff = set()
        for s in grp[1:]:
            for i in range(min(len(base), len(s['body']))):
                if base[i] != s['body'][i]:
                    diff.add(i)
        if diff:
            print('       变化字节位置: %s' % sorted(diff)[:20])
        else:
            print('       所有样本完全相同')
