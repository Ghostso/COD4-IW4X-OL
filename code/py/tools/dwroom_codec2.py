#!/usr/bin/env python3
"""dwRoomMessage 位流编码器 v2 —— 接上类型号表（lobby/94）。

与 v1 的差别：
  * 每条消息的第一个 8 位 = 该类在 lobby/94 表里的类型号（不再是 0）
  * 增加 P2PInfo（840 位定长）
  * 输出同时给 MSB / LSB 两种位序

用法:
  python -I tools/dwroom_codec2.py list
  python -I tools/dwroom_codec2.py encode MemberList --members 2
  python -I tools/dwroom_codec2.py encode RoomInfo
  python -I tools/dwroom_codec2.py encode P2PInfo
  python -I tools/dwroom_codec2.py encode StartGame
"""
import argparse
import sys

TYPE = {
    "dwRoomMessage": 0, "Manifold": 1, "Text": 2, "StartGame": 3,
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
    "MyPartyInvitationRejected": 41, "SyncPartyPendingToNewMember": 42,
    "JoinWithParty": 43, "SpyMessageText": 44, "InRoomStateChange": 45,
    "DMZLeagueTicketStateChange": 46,
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
            self.buf.append(self.cur << (8 - self.n) if not self.lsb
                            else self.cur)
            self.n = 0
        return bytes(self.buf)


def rec725():
    """成员记录 725 位（36 tag），见 lobby/92。"""
    return [
        (0x0a, 64), (0x03, 8), (0x01, 1),
        (0x15, 16), (0x15, 16), (0x15, 8), (0x15, 8), (0x15, 64),
        (0x15, 32), (0x01, 1), (0x15, 8), (0x15, 8),
        (0x15, 16), (0x15, 16), (0x15, 16), (0x15, 16), (0x15, 16),
        (0x15, 8), (0x15, 16), (0x15, 8),
        (0x15, 32), (0x15, 32), (0x15, 8), (0x15, 32), (0x15, 32),
        (0x15, 8),
        (0x01, 1), (0x01, 1), (0x01, 1), (0x01, 1), (0x01, 1), (0x01, 1),
        (0x15, 32), (0x03, 8), (0x03, 8), (0x01, 1),
    ]


SPEC = {
    "Manifold": [(0x03, 8), (0x08, 32), (0x01, 1), (0x15, 64)],
    "Text": [(0x03, 8), (0x10, "str"), (0x15, 64), (0x02, 8)],
    "StartGameFailed": [(0x03, 8), (0x15, 32)],
    "JoinRequest": [(0x03, 8), (0x10, "str"), (0x15, 32)],
    "LeaveWithMe": [(0x03, 8)],
    "Leave": [(0x03, 8), (0x15, 64)],
    "MemberInfoEXT": [(0x03, 8), (0x15, 64), (0x10, "str"), (0x15, 32),
                      (0x03, 8), (0x03, 8), (0x01, 1)],
    "RequestMemberList": [(0x03, 8)],
    "RoomInfo": [(0x03, 8)],
    "Ready": [(0x03, 8), (0x01, 1)],
    "StartCountingDown": [(0x03, 8), (0x15, 32)],
    "AvatarInfo": [(0x03, 8), (0x03, 8), (0x03, 8), (0x06, 16), (0x05, 16),
                   (0x06, 16), (0x06, 16), (0x06, 16)],
    "P2PInfo": [(0x03, 8), (0x15, 32), (0x13, ("blob", 67)),
                (0x13, ("blob", 8)), (0x15, 32), (0x15, 64)],
    "ChangeTeam": [(0x03, 8), (0x15, 32), (0x15, 8), (0x15, 32), (0x15, 64)],
    "ChangeTeamRequest": [(0x03, 8), (0x15, 32), (0x03, 8)],
    "PlaylistWeights": [(0x03, 8), (0x15, 32), (0x15, 32)],
    "RoomStateUpdated": [(0x03, 8), (0x15, 32), (0x15, 32)],
    "Score": [(0x03, 8)] + [(0x15, 32)] * 4,
    "Vote": [(0x03, 8), (0x15, 32), (0x03, 8)],
    "SetPilot": [(0x03, 8), (0x15, 8)],
    "Card": [(0x03, 8)] + [(0x15, 16)] * 5,
    "MemberDetailsQuery": [(0x03, 8), (0x15, 32)],
    "MemberDetailsNoUpdated": [(0x03, 8)],
    "UpdateDlcLevel": [(0x03, 8), (0x03, 8)],
    "UpdateCreditRating": [(0x03, 8), (0x01, 1)],
    "UpdateWarGodData": [(0x03, 8), (0x03, 8), (0x08, 32), (0x08, 32)],
    "QQMembership": [(0x03, 8), (0x15, 32)],
    "NetcafePrivileges": [(0x03, 8), (0x15, 32)],
    "JoinMemberInfos": [(0x03, 8), (0x15, 8)] + rec725(),
    "ClanNameChange": [(0x03, 8), (0x10, "str")],
    "PlayerPrimaryWeaponCountChange": [(0x03, 8), (0x01, 1)],
    "MyPartyInvitation": [(0x03, 8), (0x07, 32), (0x0a, 64), (0x10, "str")],
    "MyPartyInvitationRejected": [(0x03, 8), (0x0a, 64)],
    "JoinWithParty": [(0x03, 8), (0x15, 64), (0x15, 8), (0x15, 8)],
    "SpyMessageText": [(0x03, 8), (0x10, "str"), (0x15, 64), (0x02, 8),
                       (0x01, 1)],
    "InRoomStateChange": [(0x03, 8), (0x01, 1)],
    "DMZLeagueTicketStateChange": [(0x03, 8), (0x01, 1)],
}


def encode(name, lsb=False, name_bytes=b"Bob", members=1):
    if name == "MemberList":
        spec = [(0x03, 8), (0x15, 32, members)] + rec725() * members
    elif name == "MemberInfoAdd":
        spec = [(0x03, 8)] + rec725() + [(0x10, "str")]
    elif name == "dwRoomMessage":
        spec = [(0x03, 8)]
    else:
        spec = SPEC.get(name)
        if spec is None:
            raise SystemExit("未知消息: %s" % name)
    w = BW(lsb=lsb)
    total = 0
    lines = []
    for item in spec:
        tag, width = item[0], item[1]
        forced = item[2] if len(item) > 2 else None
        w.w(tag, 5)
        total += 5
        if width == "str":
            payload = name_bytes + b"\x00"
            for b in payload:
                w.w(b, 8)
            total += 8 * len(payload)
            lines.append("  0x%02x str(%r)" % (tag, name_bytes))
        elif isinstance(width, tuple) and width[0] == "blob":
            n = width[1]
            w.w(0x08, 5)
            total += 5
            w.w(n, 32)
            total += 32
            for _ in range(n):
                w.w(0, 8)
            total += n * 8
            lines.append("  0x%02x blob(%d B)" % (tag, n))
        else:
            # 第一个 0x03 字段写类型号；带 forced 的写指定值
            if forced is not None:
                val = forced
            elif tag == 0x03 and not lines and name in TYPE:
                val = TYPE[name]
            else:
                val = 0
            w.w(val, width)
            total += width
            note = ""
            if tag == 0x03 and not lines and name in TYPE:
                note = "  ← 类型号 %d" % val
            elif forced is not None:
                note = "  ← 值 %d" % val
            lines.append("  0x%02x %d 位%s" % (tag, width, note))
    return w.done(), total, lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["list", "encode"])
    ap.add_argument("msg", nargs="?")
    ap.add_argument("--members", type=int, default=1)
    ap.add_argument("--name", default="Bob")
    ap.add_argument("--lsb", action="store_true")
    ap.add_argument("--both", action="store_true")
    a = ap.parse_args()

    if a.cmd == "list":
        for k in sorted(TYPE, key=lambda x: TYPE[x]):
            print("%2d 0x%02x  %s" % (TYPE[k], TYPE[k], k))
        return

    for lsb in ([False, True] if a.both else [a.lsb]):
        data, total, lines = encode(
            a.msg, lsb=lsb, name_bytes=a.name.encode(), members=a.members)
        print("=== %s  %s ===" % (a.msg, "LSB" if lsb else "MSB"))
        for ln in lines[:12]:
            print(ln)
        if len(lines) > 12:
            print("  ...（共 %d 个字段）" % len(lines))
        print("位长 %d → 字节 %d" % (total, len(data)))
        print("hex: " + data.hex(" "))
        print()


if __name__ == "__main__":
    main()
