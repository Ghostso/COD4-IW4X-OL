"""解码客户端 setRoomData 批次里的容器结构（dwRoomMessageManifold 线格式）。

已知样本(全部来自 ONCE_20261028_202928 的真实客户端上行):
  10 00 00 00 | 02 | 02 00 00 00 | 18 00 00 00 | d0 00 00 00 | 00 00 00
  11 00 00 00 | 18 1c 5a 98 d6 14 53 91 | cf 01 6c 58 01 00 00 00 00
  0c 00 00 00 | 02 02 00 00 00 | 08 00 00 00 | 80 08 00
  3b 00 00 00 | 02 | 06 00 00 00 | 30 00 00 00 | e0 68 ab 5b ab 63 ab 03 ...

第一条: u32 总长=16, 然后 02(类型) 02 00 00 00(?) 18 00 00 00(d0=208?)
本脚本只做结构统计与假设检验, 不改任何东西。
"""
import re
import sys

LOG = sys.argv[1] if len(sys.argv) > 1 else \
    r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\ONCE_20261028_202928\runtime_kit\lobby_srv.log'

txt = open(LOG, encoding='utf-8', errors='replace').read()
batches = []
for m in re.finditer(r'payload\((\d+)\):\s*((?:[0-9a-f]{2} )+)', txt):
    raw = bytes.fromhex(m.group(2).replace(' ', ''))
    i = raw.find(b'\x13\x08')
    if i < 0:
        continue
    ln = int.from_bytes(raw[i + 2:i + 6], 'little')
    b = raw[i + 6:i + 6 + ln]
    if len(b) == ln and ln >= 8:
        batches.append(b)

print('共 %d 条房间批次' % len(batches))
print()
for b in batches:
    total = int.from_bytes(b[:4], 'little')
    print('总长字段=%3d  实际=%3d  %s' % (total, len(b), b.hex()))
    off = 4
    parts = []
    # 假设: 总长之后是 [type u8] 然后若干 [u32 len][payload]
    if off < len(b):
        parts.append('type=%02x' % b[off])
        off += 1
    while off + 4 <= len(b):
        sub = int.from_bytes(b[off:off + 4], 'little')
        parts.append('u32=%d' % sub)
        off += 4
        if sub == 0:
            break
    print('   →', ' | '.join(parts))
    print()
