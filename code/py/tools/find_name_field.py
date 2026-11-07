"""在客户端上行里找 'HostUser' / 'loopback' 等标识串, 定位信封的 name 字段。

若客户端上行也带这些串, 就说明信封里确实有一个 name 字段,
且 slot6 的 [ebp+0x18] 就是它。这样能反推信封布局。
"""
import re
import sys

LOG = sys.argv[1]
txt = open(LOG, encoding='utf-8', errors='replace').read()

# 收集所有 payload 明文
pays = []
for m in re.finditer(r'payload\((\d+)\):\s*((?:[0-9a-f]{2} )+)', txt):
    raw = bytes.fromhex(m.group(2).replace(' ', ''))
    pays.append(raw)

print('payload 共 %d 条' % len(pays))
for needle in (b'HostUser', b'loopback', b'Player', b'Server', b'localhost',
               b'BOT', b'mmbook', b'mmstart'):
    hits = [(i, p.find(needle)) for i, p in enumerate(pays) if needle in p]
    print('  %-12s 出现 %d 次' % (needle.decode(), len(hits)))
    for i, off in hits[:4]:
        print('      payload#%d offset %d' % (i, off))

print()
print('=== 含 HostUser 的 payload 原文 ===')
for i, p in enumerate(pays):
    if b'HostUser' in p:
        off = p.find(b'HostUser')
        print('  #%d (%dB) off=%d: %s' % (i, len(p), off, p.hex()))
        print('     前后: %r' % p[max(0, off - 24):off + 40])
