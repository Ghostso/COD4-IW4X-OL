"""对照: 客户端发送缓冲区 vs 我们构造的信封, 逐字段比较。

客户端实测 (0x3AC62E3C 起, snap_003):
    00 00 00 02              加密前的 marker 区(实际是帧头一部分)
    08 0b 00 00 00           service=11
    0a 01 00 00 00 00 00 00 00   senderId=1
    10 "Player" 00           senderName="Player"
    13 08 a6 00 00 00        blob len=166
      0a <u64 roomId>        payload: roomId
      13 08 91 00 00 00      payload: 内层 blob len=145
      8d 00 00 00            内层内层 len=141
      02 04 00 00 00 ...     真正的房间消息
      08 01 00 00 00         尾部

我们构造 (build_room_push):
    08 <kind> 0a <sender> 10 <name> 0a <roomId> 13 08 <len> <payload> 08 0
    ^^^^^^ 注意: 我们多了一个 "0a <roomId>" 字段, 且位置在外层
"""
import importlib.util
import os
import sys

KIT = sys.argv[1] if len(sys.argv) > 1 else r'run_codol_001\kit_roommsg_20261028'
sys.path.insert(0, os.path.abspath(KIT))
spec = importlib.util.spec_from_file_location(
    'lb', os.path.join(KIT, 'lobby_server.py'))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
import codol_crypto as cc

ROOM = mod.ROOM_ID
CLIENT_BUF = bytes.fromhex(
    '080b000000'                     # service=11
    '0a0100000000000000'             # senderId=1
    '10506c6179657200'               # "Player\0"
    '1308a6000000'                   # blob len=166
    '0a8877665544332211'             # roomId
    '130891000000'                   # inner blob len=145
    '8d000000'                       # 141
)
print('客户端发送缓冲区前缀 (%d B):' % len(CLIENT_BUF))
print('  ' + CLIENT_BUF.hex())
print()

payload = mod.build_roomstateupdated_payload(1, 0)
ours_a = mod.build_room_push(1, 'Player', ROOM, payload)
ours_b = cc.instant_push_body(1, 'Player', payload, kind=11)

print('A build_room_push (%d B):' % len(ours_a))
print('  ' + ours_a.hex())
print()
print('B instant_push_body(kind=11) (%d B):' % len(ours_b))
print('  ' + ours_b.hex())
print()

print('=== 与客户端前缀的共同前缀长度 ===')
for name, buf in (('A build_room_push', ours_a), ('B instant_push_body', ours_b)):
    n = 0
    for x, y in zip(buf, CLIENT_BUF):
        if x != y:
            break
        n += 1
    print('  %-22s %d 字节相同' % (name, n))
    if n < len(buf):
        print('      客户端[%d:]=%s' % (n, CLIENT_BUF[n:n + 8].hex()))
        print('      我们  [%d:]=%s' % (n, buf[n:n + 8].hex()))
