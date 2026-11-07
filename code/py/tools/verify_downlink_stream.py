"""按客户端**下行** deserialize 的读序，回读服务端构造的房间消息 body。

客户端 deserialize 实测读序（以 RoomInfo 0x627EE0 为例）：
    readBits(3)  -> 5 位，必须 == 3
    readData(8)  -> 8 位，type
    ...后续字段...

本脚本独立实现位读器（不复用服务端写器），验证服务端输出可被正确回读。
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


class BitReader:
    def __init__(self, data):
        self.d = data
        self.pos = 0

    def read_bits(self):
        v = 0
        for i in range(5):
            b, k = self.pos // 8, self.pos % 8
            if b >= len(self.d):
                raise EOFError('read_bits @%d' % self.pos)
            if (self.d[b] >> k) & 1:
                v |= 1 << i
            self.pos += 1
        return v

    def read_data(self, nbits):
        v = 0
        for i in range(nbits):
            b, k = self.pos // 8, self.pos % 8
            if b >= len(self.d):
                raise EOFError('read_data(%d) @%d' % (nbits, self.pos))
            if (self.d[b] >> k) & 1:
                v |= 1 << i
            self.pos += 1
        return v


def check(name, cond, detail=''):
    print('  %s %-40s %s' % ('PASS' if cond else 'FAIL', name, detail))
    return cond


ok = True
print('=== RoomInfo(0x0F) ===')
ri = mod.build_roominfo_payload(mod.ROOM_ID, room_name=b'BOTMatch')
r = BitReader(ri)
ok &= check('header tag == 3', r.read_bits() == 3)
t = r.read_data(8)
ok &= check('type == 0x0F', t == 0x0F, '0x%02X' % t)
ok &= check('body 长度合理', 4 <= len(ri) <= 512, '%d B' % len(ri))

print()
print('=== RoomStateUpdated(0x17) ===')
rs = mod.build_roomstateupdated_payload(1, 0)
r = BitReader(rs)
ok &= check('header tag == 3', r.read_bits() == 3)
t = r.read_data(8)
ok &= check('type == 0x17', t == 0x17, '0x%02X' % t)
ok &= check('field1 tag 0x15', r.read_bits() == 0x15)
ok &= check('field1 value == 1', r.read_data(32) == 1)
ok &= check('field2 tag 0x15', r.read_bits() == 0x15)
ok &= check('field2 value == 0', r.read_data(32) == 0)
ok &= check('无多余位', r.pos <= len(rs) * 8, '%d/%d' % (r.pos, len(rs) * 8))

print()
print('=== MemberDetails(0x1D) ===')
md = mod.build_memberdetails_payload(mod.PLAYER_UID, flags=1, team=0, ready=1,
                                     name=b'Player')
r = BitReader(md)
ok &= check('header tag == 3', r.read_bits() == 3)
t = r.read_data(8)
ok &= check('type == 0x1D', t == 0x1D, '0x%02X' % t)
ok &= check('uid tag 0x15', r.read_bits() == 0x15)
uid = r.read_data(32)
ok &= check('uid 低32', uid == (mod.PLAYER_UID & 0xFFFFFFFF), '0x%X' % uid)
slots = []
for _ in range(15):
    if r.read_bits() != 0x02:
        break
    slots.append(r.read_data(8))
ok &= check('15 个槽位', len(slots) == 15, str(slots[:3]))

print()
print('=== 完整推送（外层 + L2） ===')
push = mod.build_room_push(1, 'Player', mod.ROOM_ID, rs)
ok &= check('push[0] == 0x08', push[0] == 0x08)
ok &= check('service == 11', struct.unpack_from('<I', push, 1)[0] == 11)
ok &= check('push 内含 roomId',
            struct.pack('<Q', mod.ROOM_ID) in push)

print()
print('结果: %s' % ('全部通过' if ok else '有失败项'))
sys.exit(0 if ok else 1)
