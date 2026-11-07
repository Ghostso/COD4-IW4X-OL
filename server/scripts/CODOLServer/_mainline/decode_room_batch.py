"""解码客户端自己发出的 11/4 setRoomData 批次, 判定房间消息的容器格式。

从 lobby_srv.log 里抽出 batch 十六进制, 按两种假设解码:
  A. 裸位流 (B(3) 头 + type 字节 + 字段)
  B. protobuf/bdByteBuffer 风格 (tag/len)
把两种假设的结果都打出来对照。
"""
import re
import sys

LOG = sys.argv[1] if len(sys.argv) > 1 else \
    r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\ONCE_20261028_202928\runtime_kit\lobby_srv.log'

txt = open(LOG, encoding='utf-8', errors='replace').read()
# payload(<n>): <hex>
for m in re.finditer(r'payload\((\d+)\):\s*((?:[0-9a-f]{2} )+)', txt):
    n = int(m.group(1))
    raw = bytes.fromhex(m.group(2).replace(' ', ''))
    if n < 30 or n > 400:
        continue
    # 找 0A <u64> 13 08 <len> 的 setRoomData 结构
    i = raw.find(b'\x13\x08')
    if i < 0:
        continue
    ln = int.from_bytes(raw[i + 2:i + 6], 'little')
    batch = raw[i + 6:i + 6 + ln]
    if len(batch) != ln:
        continue
    print('=== setRoomData  batch=%d  payload=%d ===' % (ln, n))
    print('  roomId =', raw[1:9].hex() if raw[:1] == b'\x0a' else '?')
    print('  batch  =', batch.hex())
    print('  head   =', ' '.join('%02x' % b for b in batch[:24]))
    print()
