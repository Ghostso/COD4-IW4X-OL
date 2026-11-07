"""解析 GAME_START_PAYLOAD (162B, 靶场抓包常量) 的结构。

目标: 找出哪些字段是地图/gametype 相关的, 以便为 coop 剧情任务生成正确的开局数据。
"""
import struct

PAYLOAD_HEX = (
    "0A011000000000000013088500000081"
    "0000000204000000A4010000181802000000"
    "467D09D8AF02F807F8070000F807F807"
    "0000F807F8070000F807F8070000F807"
    "F8070000F807F8070000F807F8070000"
    "F807F8070000F807F8070000F807F807"
    "00E84BFA9A138B1740000000187A237A"
    "72634B73830000001848107828384800"
    "08485020304068580050000000706100"
    "00000000000000000000080100000000"
)
b = bytes.fromhex(PAYLOAD_HEX)
print('长度 = %d' % len(b))
print()

# protobuf-ish: 0A 01 10 -> field1 varint? 先按 tag 解析
print('=== 按 protobuf tag 尝试解析 ===')
i = 0
depth = 0
while i < len(b):
    tag = b[i]
    field = tag >> 3
    wire = tag & 7
    if wire == 0:      # varint
        j = i + 1
        val = 0; shift = 0
        while j < len(b):
            val |= (b[j] & 0x7F) << shift
            shift += 7
            if not (b[j] & 0x80): j += 1; break
            j += 1
        print('  @%-3d field=%-3d varint=%d' % (i, field, val))
        i = j
    elif wire == 2:    # length-delimited
        j = i + 1
        ln = 0; shift = 0
        while j < len(b):
            ln |= (b[j] & 0x7F) << shift
            shift += 7
            if not (b[j] & 0x80): j += 1; break
            j += 1
        if j + ln > len(b):
            print('  @%-3d field=%-3d len=%d (越界, 停止)' % (i, field, ln))
            break
        data = b[j:j + ln]
        asc = ''.join(chr(c) if 32 <= c <= 126 else '.' for c in data[:40])
        print('  @%-3d field=%-3d len=%-3d %s' % (i, field, ln, data[:24].hex(' ') + (' | ' + asc if asc.strip('.') else '')))
        i = j + ln
    elif wire == 5:    # 32-bit
        if i + 5 > len(b):
            break
        v = struct.unpack_from('<I', b, i + 1)[0]
        print('  @%-3d field=%-3d fixed32=%d (0x%08X)' % (i, field, v, v))
        i += 5
    elif wire == 1:    # 64-bit
        if i + 9 > len(b):
            break
        v = struct.unpack_from('<Q', b, i + 1)[0]
        print('  @%-3d field=%-3d fixed64=%d' % (i, field, v))
        i += 9
    else:
        print('  @%-3d 未知 wire=%d, 停止' % (i, wire))
        break
