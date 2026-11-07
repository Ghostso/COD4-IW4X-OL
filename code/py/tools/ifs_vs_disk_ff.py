#!/usr/bin/env python3
"""对比：磁盘独立 .ff vs .ifs 里内嵌的 .ff。
若两者字节不同，说明 .ifs 内的是"打包后的形态"，磁盘独立的是"解包后"。
若相同，说明 .ifs 只是容器，不解密。
"""
import hashlib
import struct
import sys


def read_ifs_ff_members(path):
    """读 .ifs，返回 [(name, offset, size)] —— 用已知头格式。"""
    b = open(path, "rb").read()
    if b[:4] != b"nifs":
        raise SystemExit("not nifs")
    hdrlen = struct.unpack_from("<I", b, 4)[0]
    tail = struct.unpack_from("<Q", b, 0x4C)[0]
    i = b.find(b"IWff")
    return len(b), i, len(b) - tail, b


def main():
    ifs = sys.argv[1]
    standalone = sys.argv[2] if len(sys.argv) > 2 else None
    size, iwff, tailstart, b = read_ifs_ff_members(ifs)
    print("ifs      = %s" % ifs.rsplit("\\", 1)[-1])
    print("  size   = %d" % size)
    print("  IWff@  = %#x" % iwff)
    print("  tail   = %#x .. %#x" % (tailstart, size))
    print("  ff 长度= %d" % (tailstart - iwff))
    seg = b[iwff:tailstart]
    print("  ff md5 = %s" % hashlib.md5(seg).hexdigest())
    print("  ff head= %r" % seg[:32])

    if standalone:
        s = open(standalone, "rb").read()
        print("\nstandalone = %s" % standalone.rsplit("\\", 1)[-1])
        print("  size   = %d" % len(s))
        print("  md5    = %s" % hashlib.md5(s).hexdigest())
        print("  head   = %r" % s[:32])
        print("\n  完全相同: %s" % (seg == s))
        # 对比 8 个 u64
        if len(seg) > 60 and len(s) > 60:
            print("  ifs   u64[0..3]: %s" % " ".join(
                "%d" % struct.unpack_from("<Q", seg, 12 + k * 8)[0]
                for k in range(4)))
            print("  disk  u64[0..3]: %s" % " ".join(
                "%d" % struct.unpack_from("<Q", s, 12 + k * 8)[0]
                for k in range(4)))


if __name__ == "__main__":
    main()
