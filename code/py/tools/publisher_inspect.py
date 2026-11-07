#!/usr/bin/env python3
"""逐个解压 publisher_files 下的 .info，打印头部与结构摘要。"""
import glob
import os
import sys
import zlib


def main():
    d = sys.argv[1] if len(sys.argv) > 1 else \
        r"run_codol_001\runs\ONCE_20261029_173508\kit\publisher_files"
    files = sorted(glob.glob(os.path.join(d, "*.info")))
    for p in files:
        name = os.path.basename(p)
        b = open(p, "rb").read()
        print("=" * 70)
        print("%s  (%d 字节)  head=%s" % (name, len(b), b[:2].hex()))
        try:
            if b[:1] == b"\x78":
                t = zlib.decompress(b)
                kind = "zlib"
            else:
                t = b
                kind = "raw"
            print("  [%s] 解出 %d 字节" % (kind, len(t)))
            s = t[:600].decode("latin1")
            for line in s.split("\n")[:14]:
                print("   |", line[:110])
        except Exception as e:
            print("  解压失败:", e)
            print("   raw:", repr(b[:120]))


if __name__ == "__main__":
    main()
