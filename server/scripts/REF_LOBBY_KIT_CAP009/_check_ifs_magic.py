# -*- coding: utf-8 -*-
"""看 .ifs 文件的头 32 字节, 判断是不是可直读的 nifs 容器。"""
import os
import sys

IIPS = r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\IIPS\IIPSDownload"
TARGETS = [
    "ff_init_common_mp_V111.ifs",
    "lf_init_common_marketplace_1_V49.ifs",
    "lf_hi_init_common_mp_V26.ifs",
    "lf_init_common_mp_1_V35.ifs",
]


def main():
    for n in TARGETS:
        p = os.path.join(IIPS, n)
        if not os.path.exists(p):
            print("缺 %s" % n)
            continue
        with open(p, "rb") as f:
            head = f.read(48)
        print("%-46s %s" % (n, head[:24].hex(" ")))
        print("   ascii: %r" % head[:24])
    return 0


if __name__ == "__main__":
    sys.exit(main())
