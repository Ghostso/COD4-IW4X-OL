"""按 protobuf 解析客户端上行的 0x02 类 body。

protobuf wire format:
    tag byte = (field_number << 3) | wire_type
    wire_type: 0=varint, 1=64bit, 2=length-delimited, 5=32bit

样本:
    02 02 0000 0008 000000 800800
      ^ tag=0x02 -> field 0, wire_type 2 (length-delimited)
      下一字节 0x02 -> 长度 2
      "0000" -> 2 字节数据
      然后 08 -> tag field=1 wire=0 (varint)
      ...
"""
import struct

samples = [
    '020200000008000000800800',
    '020200000018000000d0000000000000',
    '020200000018000000d0100000000000',
    '020400000018000000a808000000003000000050110000000000',
    '020600000030000000e068ab5bab63ab030000000050000000703100000000000000003001000080220000000020000000c0a185694d3115f91c00',
    '181c5a98d6145391cf01acb50100000000',
]


def parse_pb(b, indent=0):
    i = 0
    out = []
    while i < len(b):
        tag = b[i]
        field = tag >> 3
        wire = tag & 7
        pad = '  ' * indent
        if wire == 0:      # varint
            j = i + 1
            shift = 0
            v = 0
            while j < len(b):
                c = b[j]
                v |= (c & 0x7F) << shift
                j += 1
                shift += 7
                if not (c & 0x80):
                    break
            out.append('%stag@%d f=%d wt=0 varint=%d' % (pad, i, field, v))
            i = j
        elif wire == 2:    # length-delimited
            if i + 1 >= len(b):
                break
            ln = b[i + 1]
            if i + 2 + ln > len(b):
                out.append('%stag@%d f=%d wt=2 len=%d ★越界(剩余%d)'
                           % (pad, i, field, ln, len(b) - i - 2))
                break
            data = b[i + 2:i + 2 + ln]
            out.append('%stag@%d f=%d wt=2 len=%d data=%s'
                       % (pad, i, field, ln, data.hex()))
            i += 2 + ln
        elif wire == 5:
            if i + 5 > len(b):
                break
            v = struct.unpack_from('<I', b, i + 1)[0]
            out.append('%stag@%d f=%d wt=5 u32=%d' % (pad, i, field, v))
            i += 5
        elif wire == 1:
            if i + 9 > len(b):
                break
            v = struct.unpack_from('<Q', b, i + 1)[0]
            out.append('%stag@%d f=%d wt=1 u64=%d' % (pad, i, field, v))
            i += 9
        else:
            out.append('%stag@%d f=%d wt=%d ★未知' % (pad, i, field, wire))
            break
    return out


for s in samples:
    b = bytes.fromhex(s)
    print('=== %s (%d B) ===' % (s[:48], len(b)))
    for line in parse_pb(b):
        print('  ' + line)
    print()
