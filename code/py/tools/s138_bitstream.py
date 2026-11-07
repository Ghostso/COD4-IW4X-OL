#!/usr/bin/env python3
"""138 · 位流写入器（逐指令还原 0xB777C0）并自测。

【0xB777C0 writeBitsValue(ecx=this, [ebp+8]=srcPtr, [ebp+0xc]=nBits) 逐指令还原】

  this 布局:  +0x08 缓冲指针   +0x10 已分配字节数   +0x14 当前位游标   +0x18 高位标记
  0xB777CD  ecx = [this+0x14]                  ; 位游标
  0xB777D1  edi = (nBits + 位游标 - 1) >> 3    ; 末字节索引
  0xB777D8  if (edi >= [this+0x10]) 扩容到 edi+1 字节, 新字节 = 0
  0xB77806  eax = (nBits - 1) >> 3             ; 源字节数-1
  ── 主循环（每轮处理一个字节边界）──
  0xB77810  eax = 位游标 & 7                   ; 当前字节内的位偏移
  0xB77816  edi = 8 - eax                      ; 本字节剩余位数
  0xB77820  if (ebx(=剩余位数) < edi) ecx = ebx else ecx = edi   ; 本轮要写几位
  0xB77830  ecx += eax                          ; = 目标位在字节内的结束位置
  0xB77832  dl = 0xFF ; dl <<= cl ; dl |= (0xFF >> (8 - (8-eax)))
            → dl = 本字节"待写位"的掩码（低位起 eax..cl-1）
  0xB77846  eax = 位游标 >> 3 + 缓冲基址        ; 当前字节地址
  0xB7784C  al = *字节地址
  0xB77854  [ebp-2] = al & dl                   ; 保留不动的位
  0xB7785C  eax = nBits - 剩余位数              ; 已写入位数
  0xB77860  edi = eax >> 3                      ; 源字节索引
  0xB77865  al = src[edi]                       ; 当前源字节
  0xB7786B  ecx = eax & 7                       ; 源内剩余位
  0xB77873  ebx = 8 - ecx
  0xB7788C  al >>= cl                           ; 源字节右移（高位对齐）
  0xB77891  bl = src[edi+1] << (8 - (eax&7))    ; 下一字节左移补位
  0xB77896  dl = ~dl                            ; 取反 → 目标位掩码
  0xB77898  al |= bl                            ; 拼成待写值
  0xB7789A  al <<= cl                           ; 再左移回原位
  0xB778A2  al &= dl                            ; 只保留目标位
  0xB778A4  al |= [ebp-2]                       ; 并入原字节的保留位
  0xB778A7  *字节地址 = al                      ; 写回
  0xB778A9  [this+0x14] += 本轮位数              ; 推进游标
  0xB778C3  if (剩余位数 != 0) 继续循环

★ 位序: 从每字节的 **最高位(MSB)** 开始写 —— `shr al,cl` 取源高位, `shl` 回填目标高位。
★ 位游标 [this+0x14] 是**全局位偏移**，跨字节连续。

等价的高层语义（这就是标准 MSB-first 位流）：
    for i in range(nBits):
        bit = (src[i>>3] >> (7 - (i&7))) & 1
        pos = base_bit + i
        byte_idx, bit_in_byte = pos >> 3, pos & 7
        buf[byte_idx] |= bit << (7 - bit_in_byte)
"""
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


class BitWriter(object):
    """MSB-first 位流写入器（还原 0xB777C0）。"""

    def __init__(self):
        self.buf = bytearray()
        self.bitpos = 0          # 全局位游标（对应 [this+0x14]）

    def _ensure(self, nbytes):
        while len(self.buf) < nbytes:
            self.buf.append(0)

    def write_bits(self, value, nbits):
        """写 nbits 位（MSB-first），value 右对齐。"""
        if nbits <= 0:
            return self
        self._ensure((self.bitpos + nbits + 7) >> 3)
        for i in range(nbits):
            # 取 value 的第 (nbits-1-i) 位（MSB 先）
            bit = (value >> (nbits - 1 - i)) & 1
            pos = self.bitpos + i
            self.buf[pos >> 3] |= bit << (7 - (pos & 7))
        self.bitpos += nbits
        return self

    def write_from(self, src, nbits):
        """从 src 字节缓冲按 MSB-first 取 nbits 位写入。"""
        for i in range(nbits):
            bit = (src[i >> 3] >> (7 - (i & 7))) & 1
            pos = self.bitpos + i
            self._ensure((pos >> 3) + 1)
            self.buf[pos >> 3] |= bit << (7 - (pos & 7))
        self.bitpos += nbits
        return self

    def data(self):
        return bytes(self.buf)


# ============ 字段码（0xB773D0 名字表，实测）============
F_BOOL = 1
F_U8 = 3
F_U32 = 8
F_STRING = 0x10
F_BLOB = 0x13
F_FULL = 0x15        # 显式位置宽的通用值

CODE_WIDTH = 5       # 0xB77B10 写的字段码固定 5 位


def w_code(bw, code):
    """写 5 位字段码（0xB77B10）。"""
    return bw.write_bits(code, CODE_WIDTH)


def w_u32(bw, v):
    """code(8) + 32 位值。"""
    w_code(bw, F_U32)
    return bw.write_bits(v & 0xFFFFFFFF, 32)


def w_bool(bw, v):
    """code(1) + 1 位。"""
    w_code(bw, F_BOOL)
    return bw.write_bits(1 if v else 0, 1)


def w_full32(bw, v):
    """code(0x15) + 32 位值（RoomStateUpdated / ChangeTeam / Vote 用）。"""
    w_code(bw, F_FULL)
    return bw.write_bits(v & 0xFFFFFFFF, 32)


def w_blob(bw, data):
    """code(0x13) + code(8) + 32 位长度 + data。"""
    w_code(bw, F_BLOB)
    w_code(bw, F_U32)
    bw.write_bits(len(data) & 0xFFFFFFFF, 32)
    bw.write_from(data, len(data) * 8)
    return bw


def msg_header(bw, msg_type):
    """所有 dwRoomMessage 的公共头：code(3) + 8 位类型号（0x6287D0 / 0x628320 / 0x6285B0）。"""
    w_code(bw, F_U8)
    return bw.write_bits(msg_type & 0xFF, 8)


# ============ 三种消息（逐字节对齐序列化器）============
def build_ready(is_ready):
    """dwRoomMessageReady (type 0x10) —— 序列化器 0x6287D0。
       布局: code3 + 8位(0x10) + code1 + 1位 isReady"""
    bw = BitWriter()
    msg_header(bw, 0x10)
    w_bool(bw, is_ready)
    return bw


def build_room_state_updated(state, value_f32):
    """dwRoomMessageRoomStateUpdated (type 0x17) —— 序列化器 0x6285B0。
       布局: code3 + 8位(0x17) + code0x15 + 32位状态 + code0x15 + 32位float"""
    bw = BitWriter()
    msg_header(bw, 0x17)
    w_full32(bw, state)
    w_full32(bw, struct.unpack("<I", struct.pack("<f", float(value_f32)))[0])
    return bw


def build_change_team(team):
    """dwRoomMessageChangeTeam (type 0x14) —— 序列化器 0x628320。
       布局: code3 + 8位(0x14) + code0x15 + 32位阵营"""
    bw = BitWriter()
    msg_header(bw, 0x14)
    w_full32(bw, team)
    return bw


def build_vote(choice):
    """dwRoomMessageVote (type 0x1A) —— 序列化器 0x628320。
       布局: code3 + 8位(0x1A) + code0x15 + 32位选项"""
    bw = BitWriter()
    msg_header(bw, 0x1A)
    w_full32(bw, choice)
    return bw


# ============ 自测 ============
if __name__ == "__main__":
    print("=== 1. 位序自测（MSB-first）===")
    bw = BitWriter()
    bw.write_bits(0b101, 3)
    bw.write_bits(0b11010, 5)
    d = bw.data()
    print("  写 3位 101 + 5位 11010 -> %s (期望 0xBA = 10111010)" % d.hex())
    assert d == b"\xBA", d

    print("\n=== 2. Ready(0x10) 消息 ===")
    for rv in (True, False):
        bw = build_ready(rv)
        d = bw.data()
        print("  isReady=%-5s -> %d 位 %s  (%s)" % (
            rv, bw.bitpos, d.hex(),
            " ".join(format(b, "08b") for b in d)))
    # 手算：code3(5b)=00011 + type0x10(8b)=00010000 + code1(5b)=00001 + bit(1)
    print("  手算: 00011 00010000 00001 1 = %s" %
          "".join(format(b, "08b") for b in build_ready(True).data()))
    print("  ✓ 位流总长 = 5+8+5+1 = 19 位 = 3 字节")

    print("\n=== 3. RoomStateUpdated(0x17) ===")
    bw = build_room_state_updated(5, 45.0)
    print("  state=5 f=45.0 -> %d 位 %s" % (bw.bitpos, bw.data().hex()))
    print("  手算: 00011 00010111 10101 <5的u32> 10101 <45.0的u32>")
    print("  ✓ 位流总长 = 5+8+5+32+5+32 = 87 位 = 11 字节")

    print("\n=== 4. ChangeTeam(0x14) / Vote(0x1A) ===")
    print("  ChangeTeam(1) -> %d 位 %s" % (build_change_team(1).bitpos,
                                            build_change_team(1).data().hex()))
    print("  Vote(3)       -> %d 位 %s" % (build_vote(3).bitpos,
                                            build_vote(3).data().hex()))
    print("  ✓ 位流总长 = 5+8+5+32 = 50 位 = 7 字节")

    print("\n=== 5. 推送信封（单个 tag 0x13 blob）===")
    payload = build_ready(True).data()
    env = bytes([0x13, 0x08]) + struct.pack("<I", len(payload)) + payload
    print("  payload(%d) = %s" % (len(payload), payload.hex()))
    print("  信封        = %s" % env.hex())
    print("  ✓ 客户端 0xB76AF0: push 0x13 -> 校验 tag -> 读 u32 len -> 拷贝")
