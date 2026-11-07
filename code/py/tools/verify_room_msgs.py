"""按客户端的**读取顺序**回读服务端编出的房间消息, 验证位宽对齐。

客户端读法(全部来自内存转储 MEMDUMP_20261027_v4):
    readBits(3)   -> 5 位, 必须 == 3            (0xB774E0 校验)
    readData(8)   -> 8 位消息类型
    然后按各自 deserialize 的 readBits/readData 序读字段。

本脚本独立实现一个 LSB-first 位读器, 不复用 lobby_server 的写器,
避免"自己验自己"。用法:
    python -I tools/verify_room_msgs.py <kit_dir>
"""
import importlib.util
import os
import sys

KIT = sys.argv[1] if len(sys.argv) > 1 else r'run_codol_001\kit_roommsg_20261028'


class BitReader:
    def __init__(self, data):
        self.d = data
        self.pos = 0

    def read_bits(self):
        """readBits(expected): 读 5 位并返回。"""
        v = 0
        for i in range(5):
            byte = self.pos // 8
            bit = self.pos % 8
            if byte >= len(self.d):
                raise EOFError('read_bits past end at bit %d' % self.pos)
            if (self.d[byte] >> bit) & 1:
                v |= (1 << i)
            self.pos += 1
        return v

    def read_data(self, nbits):
        v = 0
        for i in range(nbits):
            byte = self.pos // 8
            bit = self.pos % 8
            if byte >= len(self.d):
                raise EOFError('read_data(%d) past end at bit %d' % (nbits, self.pos))
            if (self.d[byte] >> bit) & 1:
                v |= (1 << i)
            self.pos += 1
        return v


def load_lobby():
    path = os.path.join(KIT, 'lobby_server.py')
    sys.path.insert(0, os.path.abspath(KIT))
    spec = importlib.util.spec_from_file_location('lobby_under_test', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def expect_header(r, want_type):
    got = r.read_bits()
    assert got == 3, 'header tag 应为 3, 实得 %d' % got
    t = r.read_data(8)
    assert t == want_type, 'type 应为 0x%02X, 实得 0x%02X' % (want_type, t)
    return t


def verify(mod):
    checks = []

    def case(name, payload, want_type, reader):
        r = BitReader(payload)
        try:
            expect_header(r, want_type)
            reader(r)
            checks.append((name, True, '%d B, 用 %d 位' % (len(payload), r.pos)))
        except Exception as e:
            checks.append((name, False, repr(e)))

    # RoomStateUpdated: 0x15+32, 0x15+32
    def rs(r):
        assert r.read_bits() == 0x15, 'field1 tag'
        a = r.read_data(32)
        assert r.read_bits() == 0x15, 'field2 tag'
        b = r.read_data(32)
        assert (a, b) == (1, 0), 'values %r' % ((a, b),)

    case('RoomStateUpdated(1,0)',
         mod.build_roomstateupdated_payload(1, 0),
         mod.ROOM_MSG_TYPE['roomstateupdated'], rs)

    # Ready: 0x01 + 1 位 (+ 0x01 + 8 位)
    def rd(r):
        assert r.read_bits() == 0x01, 'ready tag'
        v = r.read_data(1)
        assert v == 1, 'ready 值 %d' % v
        assert r.read_bits() == 0x01, 'tail tag'
        assert r.read_data(8) == 0xFF, 'tail 值'

    case('Ready(1)', mod.build_ready_payload(1),
         mod.ROOM_MSG_TYPE['ready'], rd)

    # StartCountingDown: 0x15 + 32
    def scd(r):
        assert r.read_bits() == 0x15
        assert r.read_data(32) == 0

    case('StartCountingDown(0)', mod.build_startcountingdown_payload(0),
         mod.ROOM_MSG_TYPE['startcountingdown'], scd)

    # MemberDetails: 0x15+32, 15×(0x02+8), 0x08+8, 0x15+32, 4×(0x08+32) ...
    # 客户端 0x6261F7 push 0x20 —— uid 只写**低 32 位**，这里按同一位宽比对。
    UID32 = mod.PLAYER_UID & 0xFFFFFFFF

    def md(r):
        assert r.read_bits() == 0x15
        uid = r.read_data(32)
        assert uid == UID32, 'uid 0x%X != 0x%X' % (uid, UID32)
        slots = []
        for _ in range(15):
            assert r.read_bits() == 0x02, 'slot tag'
            slots.append(r.read_data(8))
        assert r.read_bits() == 0x08
        assert r.read_data(8) == 0
        assert r.read_bits() == 0x15
        assert r.read_data(32) == UID32
        for _ in range(4):
            assert r.read_bits() == 0x08
            r.read_data(32)
        for _ in range(2):
            assert r.read_bits() == 0x08
            r.read_data(32)
        for _ in range(3):
            assert r.read_bits() == 0x06
            r.read_data(16)
        for _ in range(3):
            assert r.read_bits() == 0x08
            r.read_data(32)
        assert slots[:3] == [1, 0, 1], 'slots %r' % (slots[:3],)

    case('MemberDetails', mod.build_memberdetails_payload(
        mod.PLAYER_UID, flags=1, team=0, ready=1),
        mod.ROOM_MSG_TYPE['memberdetails'], md)

    # ChangeTeam: 0x15+32, 0x15+8, 0x15+32, 0x15+64
    def ct(r):
        assert r.read_bits() == 0x15 and r.read_data(32) == UID32
        assert r.read_bits() == 0x15 and r.read_data(8) == 1
        assert r.read_bits() == 0x15 and r.read_data(32) == UID32
        assert r.read_bits() == 0x15 and r.read_data(64) == 0

    case('ChangeTeam(1)', mod.build_changeteam_payload(1, mod.PLAYER_UID),
         mod.ROOM_MSG_TYPE['changeteam'], ct)

    ok = sum(1 for c in checks if c[1])
    print('=== 房间消息位宽对拍: %d/%d 通过 ===' % (ok, len(checks)))
    for n, good, detail in checks:
        print('  %s %-22s %s' % ('PASS' if good else 'FAIL', n, detail))
    return ok == len(checks)


if __name__ == '__main__':
    sys.exit(0 if verify(load_lobby()) else 1)
