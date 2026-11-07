# -*- coding: utf-8 -*-
"""快照字段级对照 —— 把我们的 snapshot.c 与三份参照实现逐字段比一遍（纯离线，不起客户端）。

比对的四份实现：
  OUR  src/battle/snapshot.c :: codol_snapshot_build
  PY   REF_LOBBY_KIT/battle_server.py :: _build_motion_snapshot   （这行代码的源头）
  CSV  CODOL-Combat-Server-v0.1/src/Codol/MotionSnapshot.cs :: BuildVerifiedMotionSnapshot
       （能玩的 C# 配置 firingrange_live.cfg 里 verified_entry_snapshot=1 -> 走的就是这个）
  CSC  ... :: BuildCore
       （另一个 builder；它自己的注释与 CSV 互相矛盾，见报告）

方法：把每份实现的"字段写入序列"规范成一张表；每项带
  · 源码锚点字符串 —— 脚本会在源码里**实际定位**它，找不到就报 MISSING；
  · 一个**归一化 key** —— 只有 key 不同才算真的"写法不一致"，
    避免被我自己写的说明文字（"裸值/常量/此 builder 恒用"）误导。

用法：  python -X utf8 tools/diff_snapshot_impls.py [--write-report]
"""
from __future__ import annotations
import argparse, io
from pathlib import Path

ROOT = Path(r"D:\BaiduNetdiskDownload\使命召唤OL")
OURS = ROOT / "CODOL_SERVER_319_20261021" / "src" / "battle" / "snapshot.c"
PYF = ROOT / "REF_LOBBY_KIT" / "battle_server.py"
CSF = ROOT / "CODOL-Combat-Server-v0.1" / "src" / "Codol" / "MotionSnapshot.cs"
REPORT = ROOT / "CODOL_SERVER_319_20261021" / "docs" / "SNAPSHOT_FIELD_DIFF_20261024.md"

# 条目 = (tag, idx, 显示文字, 源码锚点, 归一化 key)
# tag: hdr=头 | fld=字段 | const=常量位段 | mark=index 标记 | list=列表段 | tail=尾

OUR = [
    ("hdr", None, "u32 ack | u8 0 | u32 server_time | u8(first?0:1) | u8(first?8:4)", "put_u8(&w, first ? 8 : 4)", "hdr"),
    ("hdr", None, "bits(0,1) 基线 | bits(1,1) has_fields | bits(220,8) num_fields", "bw_bits(&w, 220, 8)", "numfields=220"),
    ("fld", 0,  "presence1 + u32 command_time",  "bw_index(&w, 0, &prev, 7)",  "u32"),
    ("fld", 1,  "presence0 + u8 event_sequence", "bw_index(&w, 1, &prev, 7)",  "u8"),
    ("fld", 3,  "scalar_XOR(weapon_time,16)",    "bw_index(&w, 3, &prev, 7)",  "scalar16.xor"),
    ("fld", 8,  "f32_XOR(x)",                    "bw_index(&w, 8,  &prev, 7)", "f32.xor"),
    ("fld", 10, "f32_XOR(z)",                    "bw_index(&w, 10, &prev, 7)", "f32.xor"),
    ("fld", 11, "f32_XOR(y)",                    "bw_index(&w, 11, &prev, 7)", "f32.xor"),
    ("fld", 13, "f32_XOR(vy)",                   "bw_index(&w, 13, &prev, 7)", "f32.xor"),
    ("fld", 14, "f32_XOR(vx)",                   "bw_index(&w, 14, &prev, 7)", "f32.xor"),
    ("fld", 17, "scalar_XOR(weapon_state,6)",    "bw_index(&w, 17, &prev, 7)", "scalar6.xor"),
    ("fld", 18, "u16 yaw（无条件写）",             "bw_index(&w, 18, &prev, 7)", "u16"),
    ("fld", 19, "u16 pitch（无条件写）",           "bw_index(&w, 19, &prev, 7)", "u16"),
    ("fld", 20, "scalar_XOR(aiming?0x10:0,32)",  "bw_index(&w, 20, &prev, 7)", "scalar32.xor"),
    ("fld", "21-24", "**旧式事件数组**：bits(1)+u8 事件号 [+bits(1)+11bit 武器]", "bw_index(&w, 21 + i, &prev, 7)", "legacy-events"),
    ("fld", 29, "u16 roll（无条件写）",            "bw_index(&w, 29, &prev, 7)", "u16"),
    ("fld", 34, "f32 60.0（裸写）",                "bw_index(&w, 34, &prev, 7)", "f32"),
    ("fld", 38, "scalar(60,8)",                  "bw_index(&w, 38, &prev, 7)", "scalar8=60"),
    ("fld", 39, "scalar_XOR(weapon,11)",         "bw_index(&w, 39, &prev, 7)", "scalar11.xor"),
    ("fld", 41, "f32_XOR(aim_fraction)",         "bw_index(&w, 41, &prev, 7)", "f32.xor"),
    ("fld", 44, "scalar_XOR(weapon_delay,16)",   "bw_index(&w, 44, &prev, 7)", "scalar16.xor"),
    ("fld", 54, "bits(1)+bits(0x1000,31)",       "bw_index(&w, 54, &prev, 7)", "otherflags=0x1000"),
    ("fld", 56, "scalar(139,10)",                "bw_index(&w, 56, &prev, 7)", "scalar10=139"),
    ("fld", 60, "scalar(190,16)",                "bw_index(&w, 60, &prev, 7)", "scalar16=190"),
    ("fld", 61, "**常量 scalar(2047,16)**",        "bw_index(&w, 61, &prev, 7)", "scalar16=2047const"),
    ("fld", 62, "scalar(0,6)  ★参照三份都没有",    "bw_index(&w, 62, &prev, 7)", "scalar6=0"),
    ("fld", 63, "scalar(800,16)",                "bw_index(&w, 63, &prev, 7)", "scalar16=800"),
    ("fld", 68, "scalar(2047,11)",               "bw_index(&w, 68, &prev, 7)", "scalar11=2047"),
    ("fld", 83, "写 scalar(0,1)（=1 位 0）",       "bw_index(&w, 83, &prev, 7)", "pmtype-bit-written"),
    ("fld", 107, "scalar(0,16) ★参照三份都没有",   "bw_index(&w, 107, &prev, 7)", "scalar16=0"),
    ("fld", 162, "scalar(0,16) ★参照三份都没有",   "bw_index(&w, 162, &prev, 7)", "scalar16=0"),
    ("fld", 219, "无条件写 bits(1)+bits(1)",      "bw_index(&w, 219, &prev, 7)", "219-written"),
    ("const", None, "f32 1.0 | bits(0,8) | bits(1,1) | bits(5,17) | u16 100 | u16 100", "put_f32(&w, 1.0f)", "constblock"),
    ("mark", 84, "**没有 index(84) 标记**",        "guns = eq->slot_count", "no-84-marker"),
    ("list", None, "clips / owned15 / reserve 三个列表", "bw_bits(&w, 1, 1);                       /* 15 个已拥有槽位 */", "lists"),
    ("tail", None, "bits(0,13) | 第1~5段 | 0x05",  "bw_bits(&w, 0, 13)", "tail"),
]

PYT = [
    ("hdr", None, "u32 ack | u8 0 | u32 server_time | [first?0:1] | [first?8:4]", 'w.bytes_(bytes([0 if first else 1, 8 if first else 4]))', "hdr"),
    ("hdr", None, "bits(0,1) | bits(1,1) | bits(220,8) num_fields", "w.bits(220, 8)", "numfields=220"),
    ("fld", 0,  "bits(1)+u32 command_time",  'w.index(0, prev); w.bits(1, 1); w.bytes_(struct.pack("<I", command_time))', "u32"),
    ("fld", 1,  "bits(0)+u8 event_sequence", "w.index(1, prev); w.bits(0, 1); w.bytes_([eq.event_sequence & 0xFF])", "u8"),
    ("fld", 3,  "scalar(weapon_time,16) 裸值",  'w.index(3, prev); w.scalar(eq.weapon_time, 16)', "scalar16"),
    ("fld", 8,  "f32 x 裸值",                 'w.index(8, prev); w.bytes_(struct.pack("<f", x))', "f32"),
    ("fld", 10, "f32 z 裸值",                 'w.index(10, prev); w.bytes_(struct.pack("<f", z))', "f32"),
    ("fld", 11, "f32 y 裸值",                 'w.index(11, prev); w.bytes_(struct.pack("<f", y))', "f32"),
    ("fld", 13, "f32 vy 裸值",                'w.index(13, prev); w.bytes_(struct.pack("<f", vy))', "f32"),
    ("fld", 14, "f32 vx 裸值",                'w.index(14, prev); w.bytes_(struct.pack("<f", vx))', "f32"),
    ("fld", 17, "scalar(weapon_state,6) 裸值", 'w.index(17, prev); w.scalar(eq.weapon_state, 6)', "scalar6"),
    ("fld", 18, "u16 yaw（受 omit_viewangles 开关）", 'w.index(18, prev); w.bytes_(struct.pack("<H", yaw & 0xFFFF))', "u16"),
    ("fld", 19, "u16 pitch（受 omit_viewangles 开关）", 'w.index(19, prev); w.bytes_(struct.pack("<H", pitch & 0xFFFF))', "u16"),
    ("fld", 20, "scalar(aiming?0x10:0,32) 裸值", 'w.index(20, prev); w.scalar(0x10 if aiming else 0, 32)', "scalar32"),
    ("fld", "21-24", "**武器槽式（默认）**：bits(1)+[bits(1)+11bit weapon | bits(0)]；旧式可由 slot_events_legacy.on 回退", "w.bits(1 if has else 1, 1)", "slot-form"),
    ("fld", 29, "u16 roll（受 omit_viewangles 开关）", 'w.index(29, prev); w.bytes_(struct.pack("<H", roll & 0xFFFF))', "u16"),
    ("fld", 34, "f32 60.0",                  'w.index(34, prev); w.bytes_(struct.pack("<f", 60.0))', "f32"),
    ("fld", 38, "scalar(60,8)",              'w.index(38, prev); w.scalar(60, 8)', "scalar8=60"),
    ("fld", 39, "scalar(sel.weapon,11) 裸值", 'w.index(39, prev); w.scalar(sel.weapon, 11)', "scalar11"),
    ("fld", 41, "f32 aim_fraction 裸值",      'w.index(41, prev); w.bytes_(struct.pack("<f", aim_fraction))', "f32"),
    ("fld", 44, "scalar(weapon_delay,16) 裸值", 'w.index(44, prev); w.scalar(eq.weapon_delay, 16)', "scalar16"),
    ("fld", 54, "bits(1)+bits(0x1000,31)",   'w.index(54, prev); w.bits(1, 1); w.bits(0x1000, 31)', "otherflags=0x1000"),
    ("fld", 56, "scalar(139,10)",            'w.index(56, prev); w.scalar(139, 10)', "scalar10=139"),
    ("fld", 60, "scalar(190,16)",            'w.index(60, prev); w.scalar(190, 16)', "scalar16=190"),
    ("fld", 61, "**常量 scalar(2047,16)**",    'w.index(61, prev); w.scalar(2047, 16)', "scalar16=2047const"),
    ("fld", 63, "scalar(800,16)",            'w.index(63, prev); w.scalar(800, 16)', "scalar16=800"),
    ("fld", 68, "scalar(2047,11)",           'w.index(68, prev); w.scalar(2047, 11)', "scalar11=2047"),
    ("fld", 219, "仅 idx219.on 时写（默认关→不写）", 'w.index(219, prev); w.bits(1, 1); w.bits(1, 1)', "219-optional"),
    ("const", None, "f32 1.0 | bits(0,8) | bits(1,1) | bits(5,17) | u16 100 | u16 100", 'w.bytes_(struct.pack("<f", 1.0))', "constblock"),
    ("mark", 84, "**有 index(84) 标记**",      "w.index(84, prev)", "84-marker"),
    ("list", None, "clips / owned15 / reserve", "w.bits(clip_count, 17)", "lists"),
    ("tail", None, "bits(0,13) | 第1~5段 | 0x05", "w.bits(0, 1); w.bits(0, 1); w.bits(0, 1); w.bits(1, 1); w.bits(2047, 11)", "tail"),
]

CSV_ = [
    ("hdr", None, "bits(220,8) num_fields",     "w.Bits(220, 8);", "numfields=220"),
    ("fld", 0,  "bits(1)+u32 command_time",     "w.Index(0, prev); w.Bits(1, 1); w.Bytes(BitConverter.GetBytes(commandTime))", "u32"),
    ("fld", 1,  "bits(0)+u8 event_sequence",    "w.Index(1, prev); w.Bits(0, 1); w.Bytes(new byte[] { (byte)(eq.EventSequence & 0xFF) })", "u8"),
    ("fld", 3,  "scalar(weapon_time,16) 裸值",   "w.Index(3, prev); w.Scalar((uint)eq.WeaponTime, 16)", "scalar16"),
    ("fld", 8,  "f32 x 裸值",                    "w.Index(8, prev); w.Bytes(BitConverter.GetBytes((float)x))", "f32"),
    ("fld", 10, "f32 z 裸值",                    "w.Index(10, prev); w.Bytes(BitConverter.GetBytes((float)z))", "f32"),
    ("fld", 11, "f32 y 裸值",                    "w.Index(11, prev); w.Bytes(BitConverter.GetBytes((float)y))", "f32"),
    ("fld", 13, "f32 vy 裸值",                   "w.Index(13, prev); w.Bytes(BitConverter.GetBytes((float)vy))", "f32"),
    ("fld", 14, "f32 vx 裸值",                   "w.Index(14, prev); w.Bytes(BitConverter.GetBytes((float)vx))", "f32"),
    ("fld", 17, "scalar(weapon_state,6) 裸值",   "w.Index(17, prev); w.Scalar((uint)eq.WeaponState, 6)", "scalar6"),
    ("fld", 18, "u16 yaw（仅首帧可省）",           "w.Index(18, prev); w.Bytes(BitConverter.GetBytes((ushort)(yaw & 0xFFFF)))", "u16"),
    ("fld", 19, "u16 pitch（仅首帧可省）",         "w.Index(19, prev); w.Bytes(BitConverter.GetBytes((ushort)(pitch & 0xFFFF)))", "u16"),
    ("fld", 20, "scalar(aiming?0x10:0,32) 裸值",  "w.Index(20, prev); w.Scalar(aiming ? 0x10u : 0u, 32)", "scalar32"),
    ("fld", "21-24", "**旧式事件数组（此 builder 恒用）**", "w.Index(21 + i, prev);", "legacy-events"),
    ("fld", 29, "u16 roll（仅首帧可省）",          "w.Index(29, prev); w.Bytes(BitConverter.GetBytes((ushort)(roll & 0xFFFF)))", "u16"),
    ("fld", 34, "f32 60.0",                      "w.Index(34, prev); w.Bytes(BitConverter.GetBytes(60.0f))", "f32"),
    ("fld", 38, "scalar(60,8)",                  "w.Index(38, prev); w.Scalar(60, 8)", "scalar8=60"),
    ("fld", 39, "scalar(sel.Weapon,11) 裸值",     "w.Index(39, prev); w.Scalar((uint)eq.Selected.Weapon, 11)", "scalar11"),
    ("fld", 41, "f32 aimFraction 裸值",           "w.Index(41, prev); w.Bytes(BitConverter.GetBytes((float)aimFraction))", "f32"),
    ("fld", 44, "scalar(weapon_delay,16) 裸值",   "w.Index(44, prev); w.Scalar((uint)eq.WeaponDelay, 16)", "scalar16"),
    ("fld", 54, "bits(1)+bits(0x1000,31)",       "w.Index(54, prev); w.Bits(1, 1); w.Bits(0x1000, 31)", "otherflags=0x1000"),
    ("fld", 56, "scalar(139,10)",                "w.Index(56, prev); w.Scalar(139, 10)", "scalar10=139"),
    ("fld", 60, "scalar(190,16)",                "w.Index(60, prev); w.Scalar(190, 16)", "scalar16=190"),
    ("fld", 61, "**按 opt.OnGround 动态写 2046/2047**", "w.Index(61, prev); w.Scalar((uint)(opt != null && opt.OnGround ? 2046 : 2047), 16)", "scalar16=onground-cfg"),
    ("fld", 63, "scalar(800,16)",                "w.Index(63, prev); w.Scalar(800, 16)", "scalar16=800"),
    ("fld", 68, "scalar(2047,11)",               "w.Index(68, prev); w.Scalar(2047, 11)", "scalar11=2047"),
    ("fld", 83, "写 bits(0,1)（=1 位 0）",          "w.Index(83, prev); w.Bits(0, 1)", "pmtype-bit-written"),
    ("fld", 219, "无条件写：bits(1)+bits(1)，并把 1.0/100,100 常量块并入其中", "w.Index(219, prev); w.Bits(1, 1); w.Bits(1, 1)", "219-written"),
    ("const", None, "f32 1.0 | bits(0,8) | bits(1,1) | bits(5,17) | u16 100 | u16 100", "w.Bytes(BitConverter.GetBytes(1.0f)); w.Bits(0, 8)", "constblock"),
    ("mark", 84, "**没有 index(84) 标记**",        "int guns = eq.Slots.Count - ((eq.Slots[eq.Slots.Count - 1].Capacity == 0) ? 1 : 0);", "no-84-marker"),
    ("list", None, "clips / owned15 / reserve",  "w.Bits(clipCount, 17)", "lists"),
    ("tail", None, "bits(0,13) | 第1~5段 | 0x05", "w.Bits(0, 13);", "tail"),
]

CSC = [
    ("hdr", None, "bits(85,8) num_fields  ★与其他三份都不同", "w.Bits(85, 8)", "numfields=85"),
    ("fld", 0,  "bits(1)+u32 command_time",      "w.Index(0, prev); fieldOrder.Add(0); w.Bits(1, 1); w.Bytes(BitConverter.GetBytes(commandTime))", "u32"),
    ("fld", 1,  "bits(0)+u8 event_sequence",     "w.Index(1, prev); fieldOrder.Add(1); w.Bits(0, 1); w.Byte((byte)(eq.EventSequence & 0xFF))", "u8"),
    ("fld", 3,  "scalar(weapon_time,16) 裸值",    "w.Index(3, prev); fieldOrder.Add(3); w.Scalar(eq.WeaponTime, 16)", "scalar16"),
    ("fld", 8,  "f32 x 裸值",                    "w.Index(8, prev); fieldOrder.Add(8); w.Bytes(BitConverter.GetBytes((float)x))", "f32"),
    ("fld", 10, "f32 z 裸值",                    "w.Index(10, prev); fieldOrder.Add(10); w.Bytes(BitConverter.GetBytes((float)z))", "f32"),
    ("fld", 11, "f32 y 裸值",                    "w.Index(11, prev); fieldOrder.Add(11); w.Bytes(BitConverter.GetBytes((float)y))", "f32"),
    ("fld", 13, "f32 vy 裸值",                   "w.Index(13, prev); fieldOrder.Add(13); w.Bytes(BitConverter.GetBytes((float)vy))", "f32"),
    ("fld", 14, "f32 vx 裸值",                   "w.Index(14, prev); fieldOrder.Add(14); w.Bytes(BitConverter.GetBytes((float)vx))", "f32"),
    ("fld", 17, "scalar(weapon_state,6) 裸值",    "w.Index(17, prev); fieldOrder.Add(17); w.Scalar(eq.WeaponState, 6)", "scalar6"),
    ("fld", 18, "u16 yaw（受 OmitViewAngles 开关）", "w.Index(18, prev); fieldOrder.Add(18); w.Bytes(BitConverter.GetBytes((ushort)(yaw & 0xFFFF)))", "u16"),
    ("fld", 19, "u16 pitch（受 OmitViewAngles 开关）", "w.Index(19, prev); fieldOrder.Add(19); w.Bytes(BitConverter.GetBytes((ushort)(pitch & 0xFFFF)))", "u16"),
    ("fld", 20, "scalar(aiming?0x10:0,32) 裸值",  "w.Index(20, prev); fieldOrder.Add(20); w.Scalar(aiming ? 0x10 : 0, 32)", "scalar32"),
    ("fld", "21-24", "可由 LegacySlotEvents 在**旧式事件数组**与**武器槽式**之间切换", "w.Index(21 + i, prev); fieldOrder.Add(21 + i);", "slot-or-legacy"),
    ("fld", 29, "u16 roll（受 OmitViewAngles 开关）", "w.Index(29, prev); fieldOrder.Add(29); w.Bytes(BitConverter.GetBytes((ushort)(roll & 0xFFFF)))", "u16"),
    ("fld", 34, "f32 60.0",                      "w.Index(34, prev); fieldOrder.Add(34); w.Bytes(BitConverter.GetBytes(60.0f))", "f32"),
    ("fld", 38, "scalar(60,8)",                  "w.Index(38, prev); fieldOrder.Add(38); w.Scalar(60, 8)", "scalar8=60"),
    ("fld", 39, "scalar(sel.Weapon,11) 裸值",     "w.Index(39, prev); fieldOrder.Add(39); w.Scalar(sel.Weapon, 11)", "scalar11"),
    ("fld", 41, "f32 aimFraction 裸值",           "w.Index(41, prev); fieldOrder.Add(41); w.Bytes(BitConverter.GetBytes((float)aimFraction))", "f32"),
    ("fld", 44, "scalar(weapon_delay,16) 裸值",   "w.Index(44, prev); fieldOrder.Add(44); w.Scalar(eq.WeaponDelay, 16)", "scalar16"),
    ("fld", 54, "bits(1)+bits(0x1000,31)",       "w.Index(54, prev); fieldOrder.Add(54); w.Bits(1, 1); w.Bits(0x1000, 31)", "otherflags=0x1000"),
    ("fld", 56, "scalar(139,10)",                "w.Index(56, prev); fieldOrder.Add(56); w.Scalar(139, 10)", "scalar10=139"),
    ("fld", 60, "scalar(190,16)",                "w.Index(60, prev); fieldOrder.Add(60); w.Scalar(190, 16)", "scalar16=190"),
    ("fld", 61, "**按 OnGround 动态写 2046/2047**", "w.Index(61, prev); fieldOrder.Add(61); w.Scalar(opt != null && opt.OnGround ? 2046 : 2047, 16)", "scalar16=onground-cfg"),
    ("fld", 63, "scalar(800,16)",                "w.Index(63, prev); fieldOrder.Add(63); w.Scalar(800, 16)", "scalar16=800"),
    ("fld", 68, "scalar(2047,11)",               "w.Index(68, prev); fieldOrder.Add(68); w.Scalar(2047, 11)", "scalar11=2047"),
    ("fld", 219, "仅 EmitIdx219 时写（默认关→不写）", "w.Index(219, prev); fieldOrder.Add(219); w.Bits(1, 1); w.Bits(1, 1)", "219-optional"),
    ("const", None, "f32 1.0 | bits(0,8) | bits(1,1) | bits(5,17) | u16 100 | u16 100", "w.Bytes(BitConverter.GetBytes(1.0f)); w.Bits(0, 8);", "constblock"),
    ("mark", 84, "**有 index(84) 标记**",          "w.Index(84, prev); fieldOrder.Add(84);", "84-marker"),
    ("list", None, "clips / owned15 / reserve",  "w.Bits(clipCount, 17);", "lists"),
    ("tail", None, "bits(0,13) | 第1~5段 | 0x05", "for (int i = 0; i < 13; i++) w.Bits(0, 1);", "tail"),
]

SRCS = [("OUR", OURS, OUR), ("PY", PYF, PYT), ("CSV", CSF, CSV_), ("CSC", CSF, CSC)]
NAMES = ("OUR", "PY", "CSV", "CSC")


def locate(path: Path, anchor: str):
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    for i, line in enumerate(lines, 1):
        if anchor in line:
            return i
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write-report", action="store_true")
    a = ap.parse_args()
    buf = io.StringIO()

    def out(s=""):
        print(s)
        buf.write(s + "\n")

    locs, keys, disp = {}, {}, {}
    out("# 快照字段级对照（离线，由 tools/diff_snapshot_impls.py 生成）\n")
    out("> 本文件 §0–§4 由脚本生成；重跑脚本会覆盖。§5 起是人工分析。\n")
    out("## 0. 锚点定位（脚本在源码里**实际找到**的行号）\n")
    out("| 实现 | 文件 | 锚点数 | 未找到 |")
    out("|---|---|---|---|")
    for name, path, table in SRCS:
        L, K, D, miss = {}, {}, {}, []
        for tag, idx, d, anchor, key in table:
            ln = locate(path, anchor)
            L[(tag, idx)] = ln
            K[(tag, idx)] = key
            D[(tag, idx)] = d
            if ln is None:
                miss.append((tag, idx, anchor))
        locs[name], keys[name], disp[name] = L, K, D
        out("| %s | `%s` | %d | %s |" % (name, path.name, len(table),
                                         ("**%d**" % len(miss)) if miss else "0"))
        for tag, idx, anchor in miss:
            out("|   ↳ MISSING | %s idx=%s | `%s` | |" % (tag, idx, anchor[:70]))
    out("")
    for name in NAMES:
        L = locs[name]
        out("- %s 行号：" % name + "、".join(
            "%s=%s" % (i, L[(t, i)]) for (t, i) in L if t in ("fld", "mark")))

    allidx, seen = [], set()
    for name in NAMES:
        for (tag, idx) in locs[name]:
            if tag == "fld" and idx not in seen:
                seen.add(idx)
                allidx.append(idx)
    allidx.sort(key=lambda i: (0, i) if isinstance(i, int) else (1, str(i)))
    K = {(n, i): keys[n][("fld", i)] for n in NAMES for i in allidx if ("fld", i) in keys[n]}

    out("\n## 1. 字段索引集合差异\n")
    out("| 字段 | OUR | PY | CSV | CSC |")
    out("|---|---|---|---|---|")
    for i in allidx:
        out("| %s | %s |" % (i, " | ".join("有" if (n, i) in K else "**—**" for n in NAMES)))
    out("")
    part = [i for i in allidx if not all((n, i) in K for n in NAMES)]
    out("**只被部分实现写出的字段**：" + ("、".join(str(i) for i in part) or "无"))

    out("\n## 2. 同一字段的编码写法差异（只列出**归一化 key 真的不同**的）\n")
    out("| 字段 | OUR | PY | CSV | CSC |")
    out("|---|---|---|---|---|")
    real = []
    for i in allidx:
        ks = [K.get((n, i)) for n in NAMES]
        if len({k for k in ks if k}) > 1 or any(k is None for k in ks):
            ds = [disp[n][("fld", i)] if (n, i) in K else "—" for n in NAMES]
            real.append(i)
            out("| %s | %s |" % (i, " | ".join(d.replace("|", "/") for d in ds)))
    out("")
    out("**真的不一致的字段**：" + ("、".join(str(i) for i in real) or "无"))
    same = [i for i in allidx if i not in real]
    out("\n**写法完全一致的字段**：" + ("、".join(str(i) for i in same) or "无"))

    out("\n## 3. 同一字段的值不同（写法相同、常量不同）\n")
    val = [i for i in allidx
           if i in real and len({K.get((n, i)) for n in NAMES if K.get((n, i))}) == 1]
    out("写法一致但值/常量不同的字段：" + ("、".join(str(i) for i in val) or "无"))

    out("\n## 4. 结构性差异（头部 / index 标记 / 可选字段）\n")
    out("| 项 | OUR | PY | CSV | CSC |")
    out("|---|---|---|---|---|")
    for tag, idx in (("hdr", None), ("const", None), ("mark", 84), ("list", None), ("tail", None)):
        row = []
        for n in NAMES:
            if (tag, idx) in disp[n]:
                d = disp[n][(tag, idx)]
                if tag == "hdr":
                    other = [disp[m][(tag, idx)] for m in NAMES if (tag, idx) in disp[m]]
                    d = d if d == other[0] else d
                row.append(d.replace("|", "/"))
            else:
                row.append("—")
        out("| %s%s | %s |" % (tag, ("#%s" % idx) if idx is not None else "", " | ".join(row)))
    out("")
    for n in NAMES:
        has84 = disp[n].get(("mark", 84), "—")
        out("- **%s 的 index(84) 标记**：%s（源码行 %s）" % (n, has84, locs[n].get(("mark", 84))))
    out("")
    for n in NAMES:
        if ("fld", 219) in disp[n]:
            out("- **%s 的 idx219**：%s" % (n, disp[n][("fld", 219)]))
    out("")
    for n in NAMES:
        if ("fld", 83) in disp[n]:
            out("- **%s 的 idx83**：%s" % (n, disp[n][("fld", 83)]))
        else:
            out("- **%s 的 idx83**：不写" % n)

    if a.write_report:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(buf.getvalue(), encoding="utf-8")
        print("\n[written] %s" % REPORT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
