# -*- coding: utf-8 -*-
"""扫 ff_init_common_mp_V111.ifs (明文 nifs), 找 callsign 表。

客户端日志显示它加载了 common_mp; exe 字符串表说 callsign 表在
mp/callsignTitle.csv 等路径。这个包是明文 nifs, 可以直接抽。
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
IIPS = os.path.abspath(os.path.join(ROOT, "..", "COD OL", "IIPS", "IIPSDownload"))
PACK = os.path.join(IIPS, "ff_init_common_mp_V111.ifs")
OUT = os.path.join(ROOT, "mkt_assets")

KEY = re.compile(r"callsign|nameplate|badge|emblem|item_cnc|"
                 r"cardicon|cardbackground|cardframe|cardtitle", re.I)


def main():
    if not os.path.exists(PACK):
        print("缺 %s" % PACK)
        return 1
    b = open(PACK, "rb").read()
    print("包 %s: %d 字节, magic=%r" % (os.path.basename(PACK), len(b), b[:4]))

    ss = [s.decode("latin1") for s in re.findall(rb"[ -~]{4,200}", b)]
    print("可打印串 %d 个" % len(ss))

    paths = sorted(set(s for s in ss if s.startswith(("mp/", "main/"))))
    print("mp/ 或 main/ 路径: %d 个" % len(paths))

    hits = sorted(set(s for s in ss if KEY.search(s)))
    print()
    print("== callsign 相关串 %d 个 ==" % len(hits))
    for s in hits[:120]:
        print("  %s" % s)

    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "common_mp_paths.txt"), "w", encoding="utf-8") as f:
        for s in paths:
            f.write(s + "\n")
    with open(os.path.join(OUT, "common_mp_callsign.txt"), "w", encoding="utf-8") as f:
        for s in hits:
            f.write(s + "\n")
    print()
    print("已写出 common_mp_paths.txt / common_mp_callsign.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
