# -*- coding: utf-8 -*-
"""按 C# SavePublicProfile 的逐字节规则, 验证 8/3 上传帧与我们的重建结果。

C# 规则(第 700-764 行):
  num = declared + 5
  plain[8]==8, [13]==8, [18]==8, [23]==8, [28]==0x13, [29]==8, [num-1]==0
  num3 = u32@14        版本(0=未压缩, 1=压缩)
  num4 = u32@19        必须 == 1
  num5 = u32@24        CRC
  num6 = i32@30        blob 长度
  num == 35 + num6 + 125*5
  blob = plain[34 : 34+num6]
  raw = blob if num3==0 else InflateProfile(blob)
  raw 长 32768, u32@4==233, u32@8==1248641861, u32@0==num5,
      ProfileCrc(raw,4,32764)==num5
  尾部 125 项都是 tag 07

输出: 重建的 public.result = 32803 + 125*5 = 33428 字节
"""
import os
import struct
import sys
import zlib

ROOT = os.path.dirname(os.path.abspath(__file__))
TASKS = os.path.join(ROOT, "lobby_tasks.bin")
PUB = os.path.join(ROOT, "player_profiles", "public.result")

OWNER = 16701785630074219790


def profile_crc(buf, off, length):
    """照抄 C# ProfileCrc。"""
    num = 0xFFFFFFFF
    for i in range(off, off + length):
        num ^= buf[i] & 0xFF
        for _ in range(8):
            num = (num >> 1) ^ (0xEDB88320 if (num & 1) else 0)
    return (~num) & 0xFFFFFFFF


def inflate(blob):
    return zlib.decompress(blob, 15)


def find_upload():
    raw = open(TASKS, "rb").read()
    off = 0
    while off + 6 <= len(raw):
        svc = raw[off]; task = raw[off + 1]
        ln = struct.unpack_from("<I", raw, off + 2)[0]
        if off + 6 + ln > len(raw):
            break
        pl = raw[off + 6:off + 6 + ln]
        off += 6 + ln
        if (svc, task) == (8, 3):
            # 补 8 字节头(照 C# : frame 含头)
            declared = len(pl) + 3
            return struct.pack("<I", declared) + bytes([0x86, svc, 0x03, task]) + pl
    return None


def main():
    frame = find_upload()
    if frame is None:
        print("lobby_tasks.bin 里没有 8/3")
        return 1
    print("8/3 帧 %d 字节" % len(frame))
    plain = frame
    declared = struct.unpack_from("<I", plain, 0)[0]
    num = declared + 5
    print("declared=%d num=%d plain.len=%d" % (declared, num, len(plain)))
    print("结构标记: [8]=%d [13]=%d [18]=%d [23]=%d [28]=%d [29]=%d [num-1]=%d"
          % (plain[8], plain[13], plain[18], plain[23], plain[28],
             plain[29], plain[num - 1]))
    num3 = struct.unpack_from("<I", plain, 14)[0]
    num4 = struct.unpack_from("<I", plain, 19)[0]
    num5 = struct.unpack_from("<I", plain, 24)[0]
    num6 = struct.unpack_from("<i", plain, 30)[0]
    print("num3(压缩)=%d num4(必须1)=%d num5(CRC)=%d(0x%X) num6=blob长度=%d"
          % (num3, num4, num5, num5, num6))
    print("期望 num = 35 + %d + 125*5 = %d" % (num6, 35 + num6 + 625))
    print()
    blob = plain[34:34 + num6]
    raw = blob if num3 == 0 else inflate(blob)
    print("raw %d 字节" % len(raw))
    print("  u32@0 =%d (期望==%d)" % (struct.unpack_from("<I", raw, 0)[0], num5))
    print("  u32@4 =%d (期望 233)" % struct.unpack_from("<I", raw, 4)[0])
    print("  u32@8 =%d (期望 1248641861)" % struct.unpack_from("<I", raw, 8)[0])
    crc = profile_crc(raw, 4, 32764)
    print("  ProfileCrc(raw,4,32764) = %d (期望 %d)  %s"
          % (crc, num5, "OK" if crc == num5 else "★不符"))
    print()
    # 尾部 125 项
    tail = []
    base = 34 + num6
    for i in range(125):
        if plain[base + i * 5] != 7:
            print("  ★尾项 %d 的 tag != 07" % i)
            break
        tail.append(struct.unpack_from("<i", plain, base + i * 5 + 1)[0])
    print("尾部 %d 项, 非零: %s"
          % (len(tail), [(i, v) for i, v in enumerate(tail) if v]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
