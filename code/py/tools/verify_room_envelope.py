"""对拍: 服务端构造的房间推送 vs 客户端真实发送缓冲区。

客户端真实缓冲区 (snap_003 @ 0x3AC62E40):
    08 0b 00 00 00 | 0a 01 00000000000000 | 10 "Player" 00
    | 13 08 a6 00 00 00 | 0a <roomId> 13 08 <91 00 00 00> 8d 00 00 00 <141B> 08 01 00 00 00

注意：客户端那份的 body 是它自己的房间状态（141B），我们造不出同样的内容；
本脚本只验证**外层与封装层**（L1 + L2 的骨架 + L3 的 declared 规则）。
"""
import importlib.util
import os
import struct
import sys

KIT = sys.argv[1] if len(sys.argv) > 1 else r'run_codol_001\kit_roommsg_20261028'
sys.path.insert(0, os.path.abspath(KIT))
spec = importlib.util.spec_from_file_location(
    'lb', os.path.join(KIT, 'lobby_server.py'))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

ROOM = 0x1122334455667788

# 客户端真实缓冲区（截到 payload 开头部分，body 用占位）
CLIENT_HEAD = bytes.fromhex(
    '080b000000'                    # L1: service=11
    '0a0100000000000000'            # L1: senderId=1
    '10506c6179657200'              # L1: "Player\0"
    '13')                           # L1: blob tag
CLIENT_INNER_HEAD = bytes.fromhex(
    '0a8877665544332211'            # L2: roomId
    '1308')                         # L2: blob tag


def check(name, cond, detail=''):
    print('  %s %-46s %s' % ('PASS' if cond else 'FAIL', name, detail))
    return cond


ok = True
body = b'\x02\x02\x00\x00\x00\x18\x00\x00\x00\xd0\x00\x00\x00\x00\x00\x00'
payload = mod.build_room_payload(ROOM, body)
push = mod.build_room_push(1, 'Player', ROOM, payload)

print('=== 服务端构造 ===')
print('  payload (%d B): %s' % (len(payload), payload.hex()))
print('  push    (%d B): %s' % (len(push), push.hex()))
print()

print('=== 与客户端缓冲区对拍 ===')
ok &= check('L1 第1字节 = 0x08', push[0] == 0x08, '0x%02X' % push[0])
ok &= check('L1 service = 11', struct.unpack_from('<I', push, 1)[0] == 11,
            str(struct.unpack_from('<I', push, 1)[0]))

i = 5
ok &= check('L1 tag 0a', push[i] == 0x0A)
sid = struct.unpack_from('<Q', push, i + 1)[0]
ok &= check('L1 senderId 位置与值', sid == 1, str(sid))
i += 9
ok &= check('L1 tag 10', push[i] == 0x10)
e = push.find(b'\x00', i + 1)
name = push[i + 1:e]
ok &= check('L1 senderName', name == b'Player', repr(name))
i = e + 1
ok &= check('L1 tag 13 08', push[i:i + 2] == b'\x13\x08', push[i:i + 2].hex())

l1_len = struct.unpack_from('<I', push, i + 2)[0]
ok &= check('L1 payload 长度字段 == 实际', l1_len == len(payload),
            '%d vs %d' % (l1_len, len(payload)))
l2 = push[i + 6:]
ok &= check('L2 起点 = 0x0a', l2[0] == 0x0A, '0x%02X' % l2[0])
rid = struct.unpack_from('<Q', l2, 1)[0]
ok &= check('L2 roomId', rid == ROOM, '0x%016X' % rid)
ok &= check('L2 tag 13 08', l2[9:11] == b'\x13\x08', l2[9:11].hex())

inner_len = struct.unpack_from('<I', l2, 11)[0]
declared = struct.unpack_from('<I', l2, 15)[0]
ok &= check('L3 declared == innerLen-4', declared == inner_len - 4,
            '%d vs %d' % (declared, inner_len - 4))
body_out = l2[19:19 + declared]
ok &= check('L3 body 往返一致', body_out == body,
            '%d B' % len(body_out))
tail = l2[19 + declared:]
ok &= check('L3 尾部 08 01000000', tail == b'\x08\x01\x00\x00\x00', tail.hex())

print()
print('=== 共同前缀（与客户端前 24 字节） ===')
n = 0
for a, b in zip(push, CLIENT_HEAD + CLIENT_INNER_HEAD):
    if a != b:
        break
    n += 1
print('  %d 字节相同' % n)

print()
print('结果: %s' % ('全部通过' if ok else '有失败项'))
sys.exit(0 if ok else 1)
