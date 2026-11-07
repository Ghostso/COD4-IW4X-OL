"""区分房间上行的两类消息:
    A. 02 <sub> ...   容器/子消息
    B. 18 <8B> cf01 ...  另一种（33 种形态，变化在第 10/11/12 字节）

B 类样本:
    18 1c5a98d6145391 cf01 acb50100000000
    18 1c5a98d6145391 cf01 44630000000000

前 9 字节恒定: 18 + 8 字节; 之后 cf01; 之后 4 字节变化; 尾部 2 字节 0

推测: 18 = 某 tag; 8 字节 = 会话/房间标识; cf01 = ?; 4 字节 = 序号/计数
"""
import glob
import os
import re
import struct

ROOT = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs'
ROOM = 0x1122334455667788

logs = glob.glob(os.path.join(ROOT, '**', 'lobby_srv.log'), recursive=True)
b17 = []
b16 = []
for lp in logs:
    txt = open(lp, encoding='utf-8', errors='replace').read()
    for m in re.finditer(r'payload\((\d+)\):\s*((?:[0-9a-f]{2} )+)', txt):
        raw = bytes.fromhex(m.group(2).replace(' ', ''))
        if len(raw) < 16 or raw[0] != 0x0A or raw[9:11] != b'\x13\x08':
            continue
        if int.from_bytes(raw[1:9], 'little') != ROOM:
            continue
        ln = int.from_bytes(raw[11:15], 'little')
        inner = raw[15:15 + ln]
        if len(inner) != ln or len(inner) < 8:
            continue
        body = inner[4:]
        if len(body) == 17:
            b17.append(body)
        elif len(body) == 16:
            b16.append(body)

print('=== 17B 类 (%d 条) ===' % len(b17))
print('恒定前缀: %s' % b17[0][:10].hex())
tail = {}
for b in b17:
    v = struct.unpack_from('<I', b, 10)[0] if len(b) >= 14 else None
    tail.setdefault(tuple(b[10:]), 0)
    tail[tuple(b[10:])] += 1
print('不同的尾部 (%d 种):' % len(tail))
vals = []
for k, c in sorted(tail.items(), key=lambda x: -x[1]):
    raw = bytes(k)
    u32 = struct.unpack_from('<I', raw, 0)[0] if len(raw) >= 4 else None
    vals.append(u32)
    print('    %s  ×%-3d  u32@10=%s' % (raw.hex(), c, u32))
print('  尾部 u32 是否递增: %s' % (vals == sorted(vals)))

print()
print('=== 16B 类 (%d 条) ===' % len(b16))
uniq = []
for b in b16:
    if b not in uniq:
        uniq.append(b)
for u in uniq:
    print('  %s' % u.hex())
    print('    前缀=%s  变化区=%s' % (u[:9].hex(), u[9:12].hex()))
    # +9 和 +10 合并成一个 u16?
    v16 = struct.unpack_from('<H', u, 9)[0]
    print('    u16@9 = %d (0x%X)' % (v16, v16))
