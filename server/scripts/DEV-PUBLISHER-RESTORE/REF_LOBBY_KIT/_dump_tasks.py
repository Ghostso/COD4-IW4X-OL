# -*- coding: utf-8 -*-
"""把 lobby_tasks.bin 里每条请求按 service/task 归类, 并 TLV 解码 payload。

用途: 修大厅功能时, 看清每个 service/task 的请求参数到底是什么。
"""
import struct
import sys


def tlv(payload):
    """按类型标签 TLV 解码: 0x01 bool / 0x03 u8 / 0x06 u16 / 0x07 i32 /
    0x08 u32 / 0x09 i64 / 0x0A u64 / 0x10 string / 0x13 blob。"""
    out = []
    i = 0
    n = len(payload)
    while i < n:
        tag = payload[i]
        i += 1
        if tag in (0x01, 0x03):
            if i + 1 > n:
                break
            out.append("u8(%d)" % payload[i])
            i += 1
        elif tag == 0x06:
            if i + 2 > n:
                break
            out.append("u16(%d)" % struct.unpack_from("<H", payload, i)[0])
            i += 2
        elif tag == 0x07:
            if i + 4 > n:
                break
            out.append("i32(%d)" % struct.unpack_from("<i", payload, i)[0])
            i += 4
        elif tag == 0x08:
            if i + 4 > n:
                break
            out.append("u32(%d)" % struct.unpack_from("<I", payload, i)[0])
            i += 4
        elif tag == 0x09:
            if i + 8 > n:
                break
            out.append("i64(%d)" % struct.unpack_from("<q", payload, i)[0])
            i += 8
        elif tag == 0x0A:
            if i + 8 > n:
                break
            out.append("u64(%d)" % struct.unpack_from("<Q", payload, i)[0])
            i += 8
        elif tag == 0x10:
            j = payload.find(b"\x00", i)
            if j < 0:
                out.append("str(%r, unterminated)" % payload[i:i + 32])
                break
            out.append("str(%r)" % payload[i:j].decode("latin1", "replace"))
            i = j + 1
        elif tag == 0x13:
            if i + 5 > n or payload[i] != 0x08:
                out.append("blob?(bad)")
                break
            ln = struct.unpack_from("<I", payload, i + 1)[0]
            out.append("blob(%dB)" % ln)
            i += 5 + ln
        else:
            out.append("?tag(0x%02x)" % tag)
            break
    return out


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "lobby_tasks.bin"
    raw = open(path, "rb").read()
    off = 0
    groups = {}
    while off + 6 <= len(raw):
        svc = raw[off]
        task = raw[off + 1]
        ln = struct.unpack_from("<I", raw, off + 2)[0]
        if off + 6 + ln > len(raw):
            break
        pl = raw[off + 6:off + 6 + ln]
        off += 6 + ln
        groups.setdefault((svc, task), []).append(pl)

    for (svc, task) in sorted(groups):
        pls = groups[(svc, task)]
        print("=== %d/%d  x%d" % (svc, task, len(pls)))
        for pl in pls[:3]:
            print("    %s" % (" | ".join(tlv(pl)) or "(empty)"))


if __name__ == "__main__":
    main()
