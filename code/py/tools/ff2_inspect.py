#!/usr/bin/env python3
"""看 F2 小文件（裸 IWff，32KB）内部的结构：找零区边界、条目节奏。"""
import struct
import sys


def main():
    path = sys.argv[1]
    b = open(path, "rb").read()
    i = b.find(b"IWff")
    body = b[i + 24:]
    print("file=%s size=%d iwff=%#x body=%d" % (path.rsplit("\\", 1)[-1],
          len(b), i, len(body)))
    print("ent(head) vs zero-density by 512B:")
    for k in range(0, min(len(body), 8192), 512):
        seg = body[k:k + 512]
        z = seg.count(0)
        print("  %#06x  zeros=%3d/%d  %s" % (
            k, z, len(seg), seg[:24].hex(" ")))


if __name__ == "__main__":
    main()
