#!/usr/bin/env python3
"""dwRoomMessage 位流编码器（MSB-first）—— 依据 lobby/89..92 逆向结论。

★ 重要：位序（MSB-first / LSB-first）**尚未实测确认**。
   本文件默认 MSB-first（与 0xB777C0 writeDataCore 的 msb_index 用法一致），
   并提供 --lsb 开关以便实机对拍。

用法:
  python -I tools/dwroom_codec.py list
  python -I tools/dwroom_codec.py encode MemberList --members 2 --name Bob
  python -I tools/dwroom_codec.py encode ChangeTeam --team 1 --slot 3
  python -I tools/dwroom_codec.py encode MemberList --members 1 --name Bob --lsb

产物：hex 字符串 + 字节数 + 逐字段注释（stdout）。
"""
import argparse
import sys


class BitWriter:
    """MSB-first 位写入器。"""

    def __init__(self, lsb=False):
        self.buf = bytearray()
        self.cur = 0
        self.nbits = 0
        self.lsb = lsb

    def write(self, value, n):
        """写 n 位。MSB-first：先写高位。"""
        if n == 0:
            return
        value &= (1 << n) - 1
        if self.lsb:
            # LSB-first：低位移到当前字节的低位
            for i in range(n):
                bit = (value >> i) & 1
                self._push_bit(bit)
            return
        for i in range(n - 1, -1, -1):
            bit = (value >> i) & 1
            self._push_bit(bit)

    def _push_bit(self, bit):
        if self.nbits == 0:
            self.cur = 0
        self.cur = (self.cur << 1) | bit
        self.nbits += 1
        if self.nbits == 8:
            self.buf.append(self.cur)
            self.cur = 0
            self.nbits = 0

    def finish(self):
        if self.nbits:
            self.cur <<= (8 - self.nbits)
            self.buf.append(self.cur)
            self.nbits = 0
        return bytes(self.buf)


# ---------- 消息定义（顺序 = 逆向得到的 tag 序列）----------
# 每项: (tag, 位宽 或 特殊标记)
#   位宽 int          => writeData(N)
#   "str"             => 0x10 字符串：(len+1)*8
#   ("blob", bytes)   => 0x13 0x08 u32(len) len*8

def msg_member_list(n_members, name):
    """MemberList = 50 位头 + N × (725 位 + 名字串)"""
    out = []
    out.append((0x03, 8))        # 消息类型号（值待实测）
    out.append((0x15, 32))       # 成员数
    for i in range(n_members):
        # ---- 成员记录 725 位（36 个 tag） ----
        rec = [
            (0x0a, 64),   # 账号 ID
            (0x03, 8),    # 槽位
            (0x01, 1),
            (0x15, 16),
            (0x15, 16),
            (0x15, 8),
            (0x15, 8),
            (0x15, 64),
            (0x15, 32),
            (0x01, 1),
            (0x15, 8),
            (0x15, 8),
            (0x15, 16),
            (0x15, 16),
            (0x15, 16),
            (0x15, 16),
            (0x15, 16),
            (0x15, 8),
            (0x15, 16),
            (0x15, 8),
            (0x15, 32),
            (0x15, 32),
            (0x15, 8),
            (0x15, 32),
            (0x15, 32),
            (0x15, 8),
            (0x01, 1),
            (0x01, 1),
            (0x01, 1),
            (0x01, 1),
            (0x01, 1),
            (0x01, 1),
            (0x15, 32),
            (0x03, 8),
            (0x03, 8),
            (0x01, 1),
        ]
        out.extend(rec)
    return out


def msg_change_team(team, slot, v32, v64_a, v8):
    return [(0x03, 8), (0x15, 32), (0x15, 8), (0x15, 32), (0x15, 64)]


def msg_set_pilot(slot):
    return [(0x03, 8), (0x15, 8)]


def msg_request_member_list():
    return [(0x03, 8)]


def msg_leave():
    return [(0x03, 8), (0x15, 64)]


def msg_score(a, b, c, d):
    return [(0x03, 8), (0x15, 32), (0x15, 32), (0x15, 32), (0x15, 32)]


def msg_card(x):
    return [(0x03, 8)] + [(0x15, 16)] * 5


def msg_update_war_god(a, b, c, d):
    return [(0x03, 8), (0x03, 8), (0x08, 32), (0x08, 32)]


def msg_update_dlc(a, b):
    return [(0x03, 8), (0x03, 8)]


def _member_record():
    """725 位成员记录（36 个 tag）—— 与 msg_member_list 内部同一份。"""
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


def msg_member_info_add(name_bytes):
    """MemberInfoAdd = 0x03:8 + 完整 725 位记录 + 0x10 名字串
    （记录本身已含首个 0x0a:64 账号 ID）"""
    out = [(0x03, 8)]
    out.extend(_member_record())
    out.append((0x10, "str"))
    return out


REGISTRY = {
    "MemberInfoAdd": (msg_member_info_add, None),
    "MemberList": (msg_member_list, 50),
    "ChangeTeam": (msg_change_team, 169),
    "SetPilot": (msg_set_pilot, 26),
    "RequestMemberList": (msg_request_member_list, 13),
    "Leave": (msg_leave, 82),
    "Score": (msg_score, 161),
    "Card": (msg_card, 118),
    "UpdateWarGodData": (msg_update_war_god, 100),
    "UpdateDlcLevel": (msg_update_dlc, 26),
}


def encode(name, args, lsb=False, name_bytes=b"Bob"):
    fn, expect = REGISTRY[name]
    if name == "MemberList":
        spec = fn(args.members, name_bytes)
    elif name == "MemberInfoAdd":
        spec = fn(name_bytes)
    elif name == "ChangeTeam":
        spec = fn(args.team, args.slot, 0, 0, 0)
    elif name == "SetPilot":
        spec = fn(args.slot)
    elif name == "Score":
        spec = fn(0, 0, 0, 0)
    elif name == "Card":
        spec = fn(0)
    elif name == "UpdateWarGodData":
        spec = fn(0, 0, 0, 0)
    elif name == "UpdateDlcLevel":
        spec = fn(0, 0)
    else:
        spec = fn()

    w = BitWriter(lsb=lsb)
    lines = []
    total = 0
    for tag, width in spec:
        w.write(tag, 5)
        total += 5
        if width == "str":
            # 写侧等价于 writeData(str, (len+1)*8)：名字字节 + 1 个 NUL
            payload = name_bytes + b"\x00"
            for b in payload:
                w.write(b, 8)
            total += 8 * len(payload)
            lines.append("  0x%02x  str(%r)" % (tag, name_bytes))
        elif isinstance(width, int):
            w.write(0, width)
            total += width
            lines.append("  0x%02x  %d 位" % (tag, width))
        else:
            lines.append("  0x%02x  ?" % tag)
    data = w.finish()
    return data, total, lines, expect


class Args:
    members = 1
    name = "Bob"
    team = 0
    slot = 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["list", "encode"])
    ap.add_argument("msg", nargs="?")
    ap.add_argument("--members", type=int, default=1)
    ap.add_argument("--name", default="Bob")
    ap.add_argument("--team", type=int, default=0)
    ap.add_argument("--slot", type=int, default=0)
    ap.add_argument("--lsb", action="store_true")
    a = ap.parse_args()

    if a.cmd == "list":
        for k, (_, bits) in sorted(REGISTRY.items()):
            print("%-20s 定长 %d 位" % (k, bits))
        return

    if a.msg not in REGISTRY:
        print("未知消息: %s" % a.msg)
        return
    data, total, lines, expect = encode(
        a.msg, a, lsb=a.lsb, name_bytes=a.name.encode())
    print("=== %s ===" % a.msg)
    for ln in lines:
        print(ln)
    print("总位长 %d (期望 %s)  字节 %d" % (
        total, expect if a.msg != "MemberList" else "50+725N+str",
        len(data)))
    print("hex: " + data.hex(" "))
    if a.lsb:
        print("(LSB-first 模式)")


if __name__ == "__main__":
    main()
