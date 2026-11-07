#!/usr/bin/env python3
"""dwRoomMessage 位流编码器 v3 —— spec 全部来自逆向自动生成（无手抄）。

数据源：
  _byte_papers/msg_spec.py    由 tools/spec_gen.py 自动生成
  TYPE                        由 lobby/94 的 47 号表

用法:
  python -I tools/dwroom_codec3.py list
  python -I tools/dwroom_codec3.py encode MemberList --members 2
  python -I tools/dwroom_codec3.py encode RoomInfo
  python -I tools/dwroom_codec3.py encode P2PInfo --both
  python -I tools/dwroom_codec3.py verify      # 32 条对账
"""
import argparse
import sys

sys.path.insert(0, "_byte_papers")
from msg_spec import SPEC  # noqa: E402

TYPE = {
    "Message": 0, "Manifold": 1, "Text": 2, "StartGame": 3,
    "StartGameFailed": 4, "Join": 5, "JoinRequest": 6, "JoinWithMe": 7,
    "LeaveWithMe": 8, "Leave": 9, "MemberInfoAdd": 10,
    "MemberInfoEXT": 12, "RequestMemberList": 13, "MemberList": 14,
    "RoomInfo": 15, "Ready": 16, "StartCountingDown": 17,
    "AvatarInfo": 18, "P2PInfo": 19, "ChangeTeam": 20,
    "ChangeTeamRequest": 21, "PlaylistWeights": 22, "RoomStateUpdated": 23,
    "Score": 24, "Vote": 26, "SetPilot": 27, "Card": 28,
    "MemberDetails": 29, "MemberDetailsQuery": 30,
    "MemberDetailsNoUpdated": 31, "UpdateDlcLevel": 32,
    "UpdateCreditRating": 33, "UpdateWarGodData": 34,
    "QQMembership": 35, "NetcafePrivileges": 36,
    "JoinMemberInfos": 37, "ClanNameChange": 38,
    "PlayerPrimaryWeaponCountChange": 39, "MyPartyInvitation": 40,
    "dwRoomMessagMyPartyInvitationRejected": 41,
    "SyncPartyPendingToNewMember": 42, "JoinWithParty": 43,
    "MessageText": 44, "InRoomStateChange": 45,
    "DMZLeagueTicketStateChange": 46,
}

# 循环消息：循环体 = spec 的尾部 N 项（从第一个 L 标记起）
LOOP_START = {
    "MemberList": 2,               # spec[2:] 是成员记录
    "JoinMemberInfos": 2,
    "MemberInfoAdd": 1,            # spec[1:] 含记录 + 尾串
    "AvatarInfo": 3,               # spec[3:8] 是 9 环的 5 项（近似）
    "PlaylistWeights": 2,
    "MemberDetails": 2,
    "SyncPartyPendingToNewMember": 3,
    "MyPartyInvitation": 2,
    "Manifold": 3,
}


class BW:
    def __init__(self, lsb=False):
        self.buf = bytearray()
        self.cur = 0
        self.n = 0
        self.lsb = lsb

    def w(self, value, n):
        if n == 0:
            return
        value &= (1 << n) - 1
        bits = range(n) if self.lsb else range(n - 1, -1, -1)
        for i in bits:
            self.cur = (self.cur << 1) | ((value >> i) & 1)
            self.n += 1
            if self.n == 8:
                self.buf.append(self.cur)
                self.cur = 0
                self.n = 0

    def done(self):
        if self.n:
            self.buf.append((self.cur << (8 - self.n)) & 0xFF
                            if not self.lsb else self.cur)
            self.n = 0
        return bytes(self.buf)


def emit(w, spec, name, name_bytes, members, lines):
    total = 0
    first03 = True
    for tag, width in spec:
        w.w(tag, 5)
        total += 5
        if width == "str":
            payload = name_bytes + b"\x00"
            for b in payload:
                w.w(b, 8)
            total += 8 * len(payload)
            lines.append("    0x%02x str(%r)" % (tag, name_bytes))
        elif isinstance(width, tuple) and width[0] == "blob":
            n = width[1]
            w.w(0x08, 5)
            total += 5
            w.w(n, 32)
            total += 32
            for _ in range(n):
                w.w(0, 8)
            total += n * 8
            lines.append("    0x%02x blob(%dB)" % (tag, n))
        else:
            val = 0
            note = ""
            if tag == 0x03 and first03:
                first03 = False
                if name in TYPE:
                    val = TYPE[name]
                    note = "  ← 类型号 %d" % val
            w.w(val, width)
            total += width
            lines.append("    0x%02x %d%s" % (tag, width, note))
    return total


def encode(name, members=1, name_bytes=b"Bob", lsb=False):
    if name not in SPEC:
        raise SystemExit("无 spec: %s" % name)
    spec = SPEC[name]
    w = BW(lsb=lsb)
    lines = []
    # 头（循环外）
    start = LOOP_START.get(name, len(spec))
    head = spec[:start]
    body = spec[start:]
    total = emit(w, head, name, name_bytes, members, lines)
    if body:
        if name == "MemberList" or name == "JoinMemberInfos":
            for _ in range(members):
                total += emit(w, body, None, name_bytes, members, lines)
        else:
            total += emit(w, body, None, name_bytes, members, lines)
    return w.done(), total, lines, len(spec)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["list", "encode", "verify"])
    ap.add_argument("msg", nargs="?")
    ap.add_argument("--members", type=int, default=1)
    ap.add_argument("--name", default="Bob")
    ap.add_argument("--lsb", action="store_true")
    ap.add_argument("--both", action="store_true")
    a = ap.parse_args()

    if a.cmd == "list":
        for k in sorted(SPEC):
            print("%-34s type=%-3s fields=%d" % (
                k, TYPE.get(k, "?"), len(SPEC[k])))
        return

    if a.cmd == "verify":
        print("%-34s %-6s %-6s %s" % ("message", "位", "字节", "首二字节"))
        for k in sorted(SPEC):
            try:
                d, t, _, _ = encode(k)
                print("%-34s %-6d %-6d %s" % (
                    k, t, len(d), d[:2].hex(" ")))
            except SystemExit as e:
                print("%-34s SKIP %s" % (k, e))
        return

    for lsb in ([False, True] if a.both else [a.lsb]):
        d, t, lines, nf = encode(a.msg, a.members, a.name.encode(), lsb)
        print("=== %s %s（%d 字段）===" % (
            a.msg, "LSB" if lsb else "MSB", nf))
        for ln in lines[:10]:
            print(ln)
        if len(lines) > 10:
            print("    ... 共 %d 行" % len(lines))
        print("位长 %d → 字节 %d" % (t, len(d)))
        print("hex: " + d.hex(" "))
        print()


if __name__ == "__main__":
    main()
