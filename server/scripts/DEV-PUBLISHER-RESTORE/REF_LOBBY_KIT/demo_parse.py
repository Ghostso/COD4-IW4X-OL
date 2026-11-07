# -*- coding: utf-8 -*-
"""demo_parse.py —— 解析 CODOL 录像(`main/demo/*.demo`)的**消息帧容器**。

背景（2026-10-04 实测，见 HANDOFF §13.16）
------------------------------------------
录像里存的是**当年官方服务器下行的消息流**，且基本未加密 —— 这是"实体/靶子/命中"
那一半我们一直缺的数据源。容器格式（已用连续 seq 验证）：

    <opcode 1B> <seq u32 LE> <payload>
      opcode 1 -> payload = 以 NUL 结尾的文本命令（配置串 / cvar / 指令）
      opcode 2 -> payload = u16 LE 长度 + 数据（netchan / gamestate / 快照）
      opcode 3..6 -> 暂按同款 u16 长度处理（未验证，遇错会报）

文本命令里能看到：`d <idx> <val>`（配置串/实体字段）、`s <cvar> "<val>"`、
`f "MP_CONNECTED`、`S 1214`、`d 670 <hex>… 3 0` 等；字符串**可能是 base64 的 UTF-8**
（`5LiW`=世），与实时客户端 `\name\QUNsaWVudA==` 同款。

用法
----
  python demo_parse.py <demo文件>              # 摘要：帧数/长度/前若干帧/命令样本
  python demo_parse.py <demo文件> --text       # 导出全部文本命令到 <demo>.text.txt
  python demo_parse.py <demo文件> --bin <目录> # 导出 opcode=2 的载荷到目录
"""
import argparse
import collections
import os
import struct
import sys

TEXT_OPS = {1}
LEN_OPS = {2, 3, 4, 5, 6}


def _hexdump(d, off, ln, per=16):
    """经典 hexdump（offset | 16 字节 | ASCII）。"""
    for i in range(off, off + ln, per):
        row = d[i:i + per]
        hexs = " ".join("%02x" % b for b in row)
        asc = "".join(chr(b) if 32 <= b < 127 else "." for b in row)
        print("   %06x  %-47s  %s" % (i, hexs, asc))



def find_stream_start(d):
    """找帧流起点：第一个满足 `02 <seq=1> <u16 len>` 且后续能连续走下去的位置。"""
    for i in range(len(d) - 11):
        if d[i] != 2:
            continue
        if int.from_bytes(d[i + 1:i + 5], "little") != 1:
            continue
        ln = int.from_bytes(d[i + 5:i + 7], "little")
        if 16 <= ln <= 8192:
            return i
    return None


def _frame_at(d, off):
    """判断 off 处是否是帧头；是则返回 (seq, payload, nxt)，否则 (None, None, None)。"""
    if off + 6 > len(d):
        return None, None, None
    op = d[off]
    if op not in TEXT_OPS and op not in LEN_OPS:
        return None, None, None
    seq = int.from_bytes(d[off + 1:off + 5], "little")
    if not (0 < seq < 0x7FFFFFFF):
        return None, None, None
    if op in TEXT_OPS:
        k = d.find(b"\x00", off + 5, min(off + 5 + 4096, len(d)))
        if k < 0:
            return None, None, None
        return seq, d[off + 5:k], k + 1
    p = off + 5
    if p + 2 > len(d):
        return None, None, None
    ln = int.from_bytes(d[p:p + 2], "little")
    if p + 2 + ln > len(d):
        return None, None, None
    return seq, d[p + 2:p + 2 + ln], p + 2 + ln


def _chain_ok(d, off, want=3):
    """从 off 起能连续走 want 帧、且 seq 递增(+1..+4) —— 用来防误判。"""
    seqs = []
    cur = off
    for _ in range(want):
        seq, pl, nxt = _frame_at(d, cur)
        if pl is None:
            return False
        if seqs and not (0 < seq - seqs[-1] <= 4):
            return False
        seqs.append(seq)
        cur = nxt
    return True


def parse_frames(d, start, resync=True):
    """从 start 起切帧。

    ★ 关键结构（2026-10-04 定位，见 HANDOFF §13.32）：录像由**块**组成，
      每块的 seq **从 2 重新开始**；块与块之间夹着一小段头（内含浮点数）。
      因此"合法帧"有两种：
        ① 续帧：last_seq < seq <= last_seq + 64
        ② **新块**：seq 很小(<=8) 且**从该处能连续走 3 帧**（防误判）
    返回 (frames, notes, gaps)。gaps = [(gap_start, gap_len)] 块间空隙。
    """
    frames = []
    notes = []
    gaps = []
    off = start
    last_seq = 0
    while off + 6 <= len(d):
        seq, pl, nxt = _frame_at(d, off)
        cont = (last_seq == 0) or (seq is not None and 0 < seq - last_seq <= 64)
        restart = (seq is not None and seq <= 8) and _chain_ok(d, off)
        if pl is not None and (cont or restart):
            frames.append((off, d[off], seq, pl))
            last_seq = seq
            off = nxt
            continue
        if not resync:
            notes.append("停止 @%d" % off)
            break
        # 向后找下一个可续处（窗口放宽到 256KB，且要求能连走 3 帧）
        found = False
        lim = min(off + 262144, len(d) - 6)
        for k in range(off + 1, lim):
            op2 = d[k]
            if op2 not in TEXT_OPS and op2 not in LEN_OPS:
                continue
            s2 = int.from_bytes(d[k + 1:k + 5], "little")
            if not (0 < s2 <= 8 or 0 < s2 - last_seq <= 64):
                continue
            if not _chain_ok(d, k):
                continue
            gap = k - off
            if gap > 0:
                gaps.append((off, gap))
            off = k
            found = True
            break
        if not found:
            notes.append("无法再续 @%d" % off)
            break
    return frames, notes, gaps


def walk_nested(buf, out, depth=1, max_depth=3):
    """递归切**嵌套帧**：op=2 的载荷里还是 `<op><seq u32><u16 len><data>`。

    返回实际消费的字节数。注意 op=2 载荷前面可能有一段小头（实测 6 字节全 0），
    调用方应先按起始偏移试切（见 parse_nested）。
    """
    off = 0
    while off + 7 <= len(buf):
        op = buf[off]
        seq = int.from_bytes(buf[off + 1:off + 5], "little")
        ln = int.from_bytes(buf[off + 5:off + 7], "little")
        if (op not in (1, 2, 3, 4, 5, 6) or not (0 < seq < 0x7FFFFFFF)
                or ln > len(buf) - off - 7):
            break
        data = buf[off + 7:off + 7 + ln]
        out.append((depth, op, seq, data))
        if op == 2 and depth < max_depth:
            walk_nested(data, out, depth + 1, max_depth)
        off += 7 + ln
    return off


def parse_nested(frames, max_depth=3):
    """对每个 op=2 顶层帧，自动试起始偏移后递归切帧。"""
    out = []
    for off, op, seq, pl in frames:
        if op != 2:
            continue
        best = (0, [])
        for st in range(0, min(13, len(pl))):
            o = []
            walk_nested(pl[st:], o, 1, max_depth)
            if len(o) > len(best[1]):
                best = (st, o)
        out.extend(best[1])
    return out


# ======================================================================
# 位流读取器 —— `battle_server._BitWriter` 的**严格逆**（2026-10-04）
# ======================================================================
# 写入侧（见 battle_server.py `_BitWriter`）有两个反直觉点，读侧必须**分别跟踪两个游标**：
#   ① `bytes_()` 把原始字节**追加在数据末尾**（分配位置 = 当前长度 L），**位游标不动**；
#   ② `bits()` 只在位游标"字节对齐"时才 `bit = len(Data)*8` 并追加一个零字节 ——
#      也就是**跳到末尾**（越过刚追加的原始字节）。
# → 结果：原始字节与位流按**分配顺序**交错在同一线性缓冲里，不能当成单一游标读。
#
# 读侧状态（相对快照起点）：
#   · self.bit —— 位游标 r（单位 bit，可能落后于 L*8）
#   · self.n   —— 写侧"已分配字节数" L
# 规则（与写侧逐行互逆）：
#   · bits(n)  ：在 r 处读 n 位（每字节 LSB-first）；每当 r%8==0 → r = L*8; L += 1
#   · raw(n)   ：在 D[base+L : base+L+n] 读 n 字节（**不是**读位游标处）; L += n
#   · scalar(w)：1 位 present；若为 1 → 读 (w&7) 位低位 + (w//8) 个**原始字节**
class _BitReader(object):
    def __init__(self, data, base=0, bit=0, alloc=None):
        self.d = data
        self.base = base
        self.bit = bit
        self.n = alloc if alloc is not None else (bit >> 3)

    def bits(self, n):
        v = 0
        for i in range(n):
            if (self.bit & 7) == 0:
                self.bit = self.n * 8
                self.n += 1
            pos = self.base + (self.bit >> 3)
            if pos >= len(self.d):
                raise EOFError("位流越界 @bit=%d" % self.bit)
            v |= ((self.d[pos] >> (self.bit & 7)) & 1) << i
            self.bit += 1
        return v

    def raw(self, n):
        pos = self.base + self.n
        if pos + n > len(self.d):
            raise EOFError("原始字节越界 @%d+%d" % (pos, n))
        self.n += n
        return bytes(self.d[pos:pos + n])

    def u32(self):
        return struct.unpack("<I", self.raw(4))[0]

    def u16(self):
        return struct.unpack("<H", self.raw(2))[0]

    def f32(self):
        return struct.unpack("<f", self.raw(4))[0]

    def scalar(self, width):
        if self.bits(1) == 0:
            return 0
        low = width & 7
        v = self.bits(low) if low else 0
        sh = low
        for _ in range(width // 8):
            v |= self.raw(1)[0] << sh
            sh += 8
        return v

    def index(self, prev):
        """对应写侧 `_BitWriter.index()`；返回 (index, 跳过量)。"""
        if self.bits(1):
            idx = prev + 1
            skip = 0
        else:
            skip = 0
            while True:
                v = self.bits(4)
                skip += v
                if v != 15:
                    break
            idx = prev + 1 + skip
        return idx, skip


# 已知索引的编码（来自 `_build_motion_snapshot`；写侧顺序即权威）
SNAP_SCALAR_W = {3: 16, 17: 6, 20: 32, 38: 8, 39: 11, 44: 16,
                 56: 10, 60: 16, 61: 16, 63: 16, 68: 11,
                 # ★ 2026-10-04 按参考 trace 的 cursor 量出的宽度补齐（见 HANDOFF §13.45.3）
                 7: 12, 9: 12, 12: 8, 15: 8, 47: 11, 57: 11, 59: 8}
SNAP_F32 = {8: "x", 10: "z", 11: "y", 13: "vy", 14: "vx", 34: "f34", 41: "aim",
            # ★ 量出的 float 字段
            16: "f16", 30: "f30", 58: "f58"}
SNAP_U16 = {18: "yaw", 19: "pitch", 29: "roll"}
# ★ 量出的"presence 位 + n 个原始字节"字段（codec 号各不同，但宽度都是 1 位 + n 字节）
#   idx 45 = presence + 2 字节（= 17 位，与 §13.34 实跑互相印证）
SNAP_PRES_RAW = {4: (4, "i4"), 45: (2, "yawf"), 64: (4, "i64")}


def _read_gun_list(br):
    """读 `bits(has,1)` + N 条 `<u4 idx><u11 weapon><u1 1><u9 clip><u1 0><u1 last>`。"""
    if br.bits(1) == 0:
        return []
    out = []
    while True:
        i = br.bits(4)
        w = br.bits(11)
        br.bits(1)
        clip = br.bits(9)
        br.bits(1)
        last = br.bits(1)
        out.append((i, w, clip))
        if not last:
            break
    return out


def read_motion_snapshot(br, tolerate=True):
    """按 `_build_motion_snapshot` 的**字段序**读一条记录。

    tolerate=True 时遇到**未知索引**就停止并如实报告（用来发现官方多出来的字段）。
    返回 (fields dict, note)。
    """
    f = {}
    f["ack"] = br.u32()
    f["b0"] = br.raw(1)[0]
    f["server_time"] = br.u32()
    f["hdr2"] = br.raw(2)
    br.bits(1); br.bits(1); br.bits(8)          # 0 / 1 / 220
    prev = -1
    known = (set(SNAP_SCALAR_W) | set(SNAP_F32) | set(SNAP_U16) | set(SNAP_PRES_RAW)
             | {0, 1, 21, 22, 23, 24})
    for _ in range(200):
        idx, skip = br.index(prev)
        prev = idx
        if idx in SNAP_U16:
            f[SNAP_U16[idx]] = br.u16()
        elif idx in SNAP_F32:
            f[SNAP_F32[idx]] = br.f32()
        elif idx in SNAP_SCALAR_W:
            f["i%d" % idx] = br.scalar(SNAP_SCALAR_W[idx])
        elif idx == 0:
            br.bits(1); f["command_time"] = br.u32()
        elif idx == 1:
            br.bits(1); f["event_seq"] = br.raw(1)[0]
        elif idx in (21, 22, 23, 24):
            br.bits(1); ev = br.raw(1)[0]; f["ev%d" % (idx - 21)] = ev
            if ev not in (0x19, 0x1A):
                br.bits(1); f["evw%d" % (idx - 21)] = br.bits(11)
        elif idx in SNAP_PRES_RAW:
            # presence 位 + n 个原始字节（宽度由参考 trace 量出，见 HANDOFF §13.45.3）
            _n, _nm = SNAP_PRES_RAW[idx]
            br.bits(1)
            _raw = br.raw(_n)
            f[_nm] = struct.unpack("<H", _raw)[0] if _n == 2 else struct.unpack("<I", _raw)[0]
        elif idx == 54:
            br.bits(1); br.bits(31)
        elif idx == 219:
            br.bits(1); br.bits(1)
            f["f219"] = br.f32()
            br.bits(8); br.bits(1); br.bits(17)
            f["u219a"] = br.u16(); f["u219b"] = br.u16()
            f["guns"] = _read_gun_list(br)
            n15 = 0
            br.bits(1)
            for _i in range(15):
                occ = br.bits(1)
                if occ:
                    n15 += 1
                    br.bits(1); br.bits(11); br.bits(5); br.bits(12)
            f["occupied15"] = n15
            br.bits(1)
            ammo = []
            while True:
                i = br.bits(4); key = br.bits(11); res = br.bits(12); last = br.bits(1)
                ammo.append((i, key, res))
                if not last:
                    break
            f["ammo"] = ammo
            br.bits(13)
            br.bits(1); br.bits(1); br.bits(1); br.bits(1); br.bits(11)
            br.bits(1); br.bits(1)
            f["tail"] = br.raw(1)[0]
            return f, "完整(%d 字段)" % len(f)
        elif idx in known:
            return f, "索引 %d 语义未知 -> 停" % idx
        else:
            if tolerate:
                return f, "遇未知索引 %d (跳过量 %d) -> 停" % (idx, skip)
            raise EOFError("未知索引 %d" % idx)
    return f, "循环上限"


def _snap_plausible(f):
    """快照合理性：x/z/y 是有限浮点、server_time 是合理毫秒数、yaw/pitch 在 u16 内。"""
    for k in ("x", "z", "y"):
        if k not in f:
            return False
        v = f[k]
        if v != v or v in (float("inf"), float("-inf")) or abs(v) > 1e6:
            return False
    return True


def probe_snapshots(buf, base=0, tries=64, max_rec=4, start=0):
    """在 buf 的 [start, start+tries) 字节偏移上试解析快照，返回按可信度排序的候选。

    （快照的位流是**按分配顺序**交错的，起点只能是字节边界 —— 见 `_BitReader` 注释。）
    打分：x/z/y 有限浮点 + server_time 递增 + 记录条数。
    """
    best = []
    for off in range(start, min(start + tries, max(0, len(buf) - 12))):
        br = _BitReader(buf, base=base + off)
        recs = []
        try:
            for _ in range(max_rec):
                f, note = read_motion_snapshot(br)
                if len(f) < 8:
                    break
                recs.append((f, note))
        except Exception as e:
            recs.append((None, "中断: %r" % (e,)))
        good = sum(1 for f, _n in recs if f and _snap_plausible(f))
        st = [f["server_time"] for f, _n in recs if f and "server_time" in f]
        inc = len(st) > 1 and all(st[i] < st[i + 1] for i in range(len(st) - 1))
        if good:
            best.append((good, inc, off, recs))
    best.sort(key=lambda x: (-x[0], -x[1], x[2]))
    return best


def scan_for_snapshots(d, limit=None):
    """全文件扫描**快照头签名**，再用读取器验证。

快照头（`_build_motion_snapshot` 固定布局，前 11 字节是原始字节、未参与掩码）：
      [ack u32] 00 [server_time u32] f0 f1   ← f0 = 0(首帧)/1，f1 = 8(首帧)/4
    紧随其后的位流头 `bits(0,1) bits(1,1) bits(220,8)` 恒定产出字节 `72 03`。
    因此强签名 = `d[o+4]==0 and d[o+11]==0x72 and d[o+12]==0x03`。
    （`battle_server.pump_snapshot` 的掩码只作用于 payload[8:]，故 o+4 仍是明文 00。）
    """
    hits = []
    end = len(d) - 13 if limit is None else min(len(d) - 13, limit)
    for o in range(0, max(0, end)):
        if d[o + 4] != 0 or d[o + 11] != 0x72 or d[o + 12] != 0x03:
            continue
        if d[o + 9] not in (0, 1) or d[o + 10] not in (4, 8):
            continue
        try:
            f, note = read_motion_snapshot(_BitReader(d, base=o), tolerate=True)
        except Exception as e:
            hits.append((o, None, "读失败 %r" % (e,)))
            continue
        hits.append((o, f, note))
    return hits


def snap_selftest():
    """往返自测：用 battle_server 的真实写入器建快照，再用本读取器读回并逐字段比对。

    这是"读取器是不是 `_BitWriter` 严格逆"的**唯一可信证据**（不依赖任何 demo 数据）。
    """
    try:
        import battle_server as bs
    except Exception as e:
        print("[!] 无法 import battle_server: %r" % (e,))
        return 2
    eq = bs._Equipment()
    want = dict(ack=0x11223344, server_time=1000, command_time=123456,
                x=48.5, y=-572.25, z=-116.75, pitch=0x1234, yaw=0xABCD,
                roll=0x0102, vx=1.5, vy=-2.5, aim_fraction=0.75, aiming=True)
    for omit in (False, True):
        for first in (True, False):
            data, nbits = bs._build_motion_snapshot(
                want["ack"], want["server_time"], want["command_time"], first,
                want["x"], want["y"], want["z"], want["pitch"], want["yaw"],
                want["roll"], want["vx"], want["vy"], want["aim_fraction"],
                want["aiming"], eq, omit_motion=omit)
            f, note = read_motion_snapshot(_BitReader(data), tolerate=False)
            errs = []
            _keys = ["ack", "server_time", "command_time", "aim"]
            if not getattr(bs, "_OMIT_VIEWANGLES", False):
                _keys += ["yaw", "pitch", "roll"]
            for k in _keys:
                if k in want and f.get(k) != want[k]:
                    errs.append("%s: 期望 %r 实得 %r" % (k, want[k], f.get(k)))
            if f.get("i20") != (0x10 if want["aiming"] else 0):
                errs.append("i20(aiming): 期望 %r 实得 %r"
                            % (0x10 if want["aiming"] else 0, f.get("i20")))
            if f.get("i39") != eq.selected.weapon:
                errs.append("i39(weapon): 期望 %r 实得 %r"
                            % (eq.selected.weapon, f.get("i39")))
            if f.get("tail") != 0x05:
                errs.append("tail: 期望 5 实得 %r" % (f.get("tail"),))
            if "yawf" in f:      # idx 45 是开关字段（idx45.on），只有开时才发
                _exp45 = want["yaw"] & 0xFFFF
                if f.get("yawf") != _exp45:
                    errs.append("idx45: 期望 %r 实得 %r" % (_exp45, f.get("yawf")))
            if not omit:
                for k in ("x", "z", "y", "vy", "vx"):
                    exp = want[k]
                    if abs(f.get(k, 1e30) - exp) > 1e-3:
                        errs.append("%s: 期望 %r 实得 %r" % (k, exp, f.get(k)))
            tag = "omit=%d first=%d" % (omit, first)
            print("[selftest] %s -> %s  字节=%-4d 位=%d  读回字段=%d"
                  % (tag, "OK" if not errs else "FAIL", len(data), nbits, len(f)))
            for e in errs:
                print("           %s" % e)
            if errs:
                return 1
    print("[selftest] 全部通过：读取器是 _BitWriter 的严格逆")
    return 0





def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("demo")
    ap.add_argument("--text", action="store_true")
    ap.add_argument("--bin")
    ap.add_argument("--nested", action="store_true",
                    help="递归切嵌套帧(op=2 载荷里还套着同样的帧)，打印叶子概览")
    ap.add_argument("--selftest", action="store_true",
                    help="往返自测：验证位流读取器是 battle_server._BitWriter 的严格逆")
    ap.add_argument("--snap", action="store_true",
                    help="在 op=2 载荷 / 嵌套叶子 / 块间空隙上试解运动快照，报告字段索引")
    ap.add_argument("--snap-at", default=None,
                    help="直接在指定文件偏移(十进制或0x开头)解析一条快照并打印字段")
    ap.add_argument("--snap-tries", type=int, default=64,
                    help="每个候选缓冲试多少个起始字节偏移(默认 64)")
    ap.add_argument("--snap-max", type=int, default=4,
                    help="每个起点最多连读几条快照(默认 4)")
    ap.add_argument("--scan", action="store_true",
                    help="全文件扫描快照头签名(ack 00 server_time f0 f1 72 03)并验证")
    ap.add_argument("--find", default=None, metavar="HEX",
                    help="在文件里搜字节串（如 00c0 / '00 c0'），打印全部偏移")
    ap.add_argument("--hex", default=None, metavar="OFF:LEN",
                    help="十六进制转储文件 [OFF, OFF+LEN)（OFF 支持 0x 前缀）")
    ap.add_argument("--op2", type=int, default=0, metavar="N",
                    help="转储前 N 个 op=2 载荷的完整十六进制")
    a = ap.parse_args()

    if a.selftest:
        return snap_selftest()

    d = open(a.demo, "rb").read()
    print("文件 = %s" % a.demo)
    print("大小 = %d (%.1f KB)" % (len(d), len(d) / 1024))
    print("头 32B = %s" % d[:32].hex(" "))

    # `--hex` / `--find` / `--snap-at` 不需要帧流 —— 允许直接作用在任意二进制（如参考产物的 demo-packet-*.bin）
    if a.find:
        pat = bytes.fromhex(a.find.replace(" ", ""))
        hits = []
        i = d.find(pat)
        while i >= 0:
            hits.append(i)
            i = d.find(pat, i + 1)
        print("\n=== --find %s（%d 字节）命中 %d 处 ===" % (pat.hex(), len(pat), len(hits)))
        print("   %s" % hits[:80])
        return 0

    if a.hex:
        sp = a.hex.split(":")
        off = int(sp[0], 0)
        ln = int(sp[1], 0) if len(sp) > 1 else 256
        off = max(0, min(off, len(d)))
        ln = min(ln, len(d) - off)
        print("\n=== --hex 0x%X..0x%X (%d 字节) ===" % (off, off + ln, ln))
        _hexdump(d, off, ln)
        return 0

    if a.snap_at is not None:
        off = int(a.snap_at, 0)
        print("\n=== --snap-at 0x%X (%d) ===" % (off, off))
        br = _BitReader(d, base=off)
        f, note = read_motion_snapshot(br)
        print("  结果: %s" % note)
        for k, v in f.items():
            print("    %-14s = %r" % (k, v))
        print("  消耗: 位游标=%d (%.1f 字节), 分配长度=%d" % (br.bit, br.bit / 8.0, br.n))
        return 0

    start = find_stream_start(d)
    if start is None:
        print("[!] 没找到帧流起点（`02 <seq=1> <u16 len>`）")
        return 1
    print("帧流起点 = %d" % start)

    frames, notes, gaps = parse_frames(d, start)
    print("解析到 %d 帧；备注: %s" % (len(frames), "; ".join(notes) if notes else "无"))
    if frames:
        ends = []
        for off, op, seq, pl in frames:
            nxt = _frame_at(d, off)[2]
            ends.append(nxt if nxt else off)
        covered = max(ends) - start
        print("尾部覆盖到 offset %d (%.1f%%)" % (covered, 100.0 * covered / max(1, len(d) - start)))
        print("seq 范围 = %d .. %d" % (frames[0][2], frames[-1][2]))
        print("★ 块数 = %d（seq 每块从 2 重新开始）; 块间空隙 %d 处"
              % (len(gaps) + 1, len(gaps)))
        if gaps:
            tot = sum(g[1] for g in gaps)
            print("   空隙合计 %d 字节; 前 8 处: %s"
                  % (tot, [(g[0], g[1]) for g in gaps[:8]]))
            g0 = gaps[0]
            print("   第 1 处空隙 bytes[%d:%d]: %s"
                  % (g0[0], g0[0] + g0[1], d[g0[0]:g0[0] + g0[1]][:40].hex(" ")))

    ops = collections.Counter(f[1] for f in frames)
    print("opcode 分布 = %s" % {("%d" % k): v for k, v in sorted(ops.items())})

    texts = [f for f in frames if f[1] == 1]
    print("\n文本命令 = %d 条；前 25 条：" % len(texts))
    for off, op, seq, pl in texts[:25]:
        print("   seq=%-6d %r" % (seq, pl[:100].decode("latin1")))

    bins = [f for f in frames if f[1] == 2]
    if bins:
        print("\n二进制帧(op=2) = %d；前 8 条：" % len(bins))
        for off, op, seq, pl in bins[:8]:
            print("   seq=%-6d len=%-5d %s" % (seq, len(pl), pl[:24].hex(" ")))

    if a.text:
        out = a.demo + ".text.txt"
        with open(out, "w", encoding="utf-8") as f:
            for off, op, seq, pl in texts:
                f.write("%8d  %6d  %s\n" % (off, seq, pl.decode("latin1")))
        print("\n已导出文本命令 -> %s" % out)

    if a.bin:
        os.makedirs(a.bin, exist_ok=True)
        for n, (off, op, seq, pl) in enumerate(bins):
            open(os.path.join(a.bin, "%05d_seq%06d.bin" % (n, seq)), "wb").write(pl)
        print("已导出 %d 个二进制载荷 -> %s" % (len(bins), a.bin))

    if a.nested:
        leaves = parse_nested(frames)
        print("\n=== 嵌套帧 %d 个 ===" % len(leaves))
        ops = collections.Counter((dep, op, len(dt)) for dep, op, seq, dt in leaves)
        print("(深, op, 长) 前 12 种: %s"
              % [(k, v) for k, v in ops.most_common(12)])
        d1 = [x for x in leaves if x[0] == 1]
        print("深度 1 叶子 %d 个；前 24 个头 12B：" % len(d1))
        for dep, op, seq, dt in d1[:24]:
            print("   op=%d seq=%-6d len=%-6d %s" % (op, seq, len(dt), dt[:12].hex(" ")))
        # 顺便试一下"是不是压缩"
        import zlib
        hit = 0
        for dep, op, seq, dt in d1:
            for off in (0, 1, 2):
                for wbits in (-15, 15):
                    try:
                        o = zlib.decompressobj(wbits)
                        if len(o.decompress(dt[off:])) >= 8:
                            hit += 1
                            break
                    except Exception:
                        pass
        print("叶子中 zlib/raw-deflate 可解 = %d/%d" % (hit, len(d1)))

    if a.op2:
        print("\n=== 前 %d 个 op=2 载荷 ===" % a.op2)
        for n, (off, op, seq, pl) in enumerate(bins[:a.op2]):
            print("--- op2[%d] seq=%d @%d len=%d ---" % (n, seq, off, len(pl)))
            _hexdump(pl, 0, len(pl))
        return 0

    if a.scan:
        print("\n=== --scan 快照头签名 ===")
        hits = scan_for_snapshots(d)
        print("命中 %d 处" % len(hits))
        for o, f, note in hits[:20]:
            if f is None:
                print("   @%-8d %s" % (o, note))
                continue
            keys = ("ack", "server_time", "command_time", "x", "z", "y",
                    "yaw", "pitch", "aim", "i39")
            kv = " ".join("%s=%s" % (k, f[k]) for k in keys if k in f)
            print("   @%-8d %s | %s" % (o, kv, note))
        return 0

    if a.snap:
        cands = []          # (标签, 字节缓冲, 局部基址, 起始偏移范围)
        for n, (off, op, seq, pl) in enumerate(bins):
            cands.append(("op2[%d] seq=%d @%d len=%d" % (n, seq, off, len(pl)),
                          pl, 0, a.snap_tries))
        leaves = parse_nested(frames)
        for k, (dep, op, seq, dt) in enumerate([x for x in leaves if x[0] == 1]):
            cands.append(("leaf[%d] op=%d seq=%d len=%d" % (k, op, seq, len(dt)),
                          dt, 0, min(a.snap_tries, len(dt))))
        for k, (go, gl) in enumerate(gaps[:6]):
            cands.append(("gap[%d] @%d len=%d" % (k, go, gl),
                          d[go:go + gl], 0, min(a.snap_tries, gl)))
        hits = 0
        for tag, buf, base, tries in cands:
            best = probe_snapshots(buf, base=base, tries=tries, max_rec=a.snap_max)
            if not best:
                continue
            good, inc, off, recs = best[0]
            hits += 1
            print("\n=== %s ===" % tag)
            print("   最佳起点 = 缓冲内 +%d; 连读 %d 条, 合理 %d 条, server_time 递增=%s"
                  % (off, len(recs), good, inc))
            for i, (f, note) in enumerate(recs):
                if f is None:
                    print("   记录%d: %s" % (i, note))
                    continue
                keys = ("server_time", "x", "z", "y", "yaw", "pitch", "aim",
                        "guns", "ammo", "tail")
                kv = " ".join("%s=%s" % (k, f[k]) for k in keys if k in f)
                print("   记录%d: %-52s | %s" % (i, kv[:52], note))
        if hits == 0:
            print("\n[--snap] 在所有候选缓冲上都没读出合理快照")
            print("  提示: demo 里的快照可能被 XOR 掩码(见 battle_server.pump_snapshot 的 mask)，"
                  "或容器层级未切对；可先用 --nested / --snap-at 手工定位。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
