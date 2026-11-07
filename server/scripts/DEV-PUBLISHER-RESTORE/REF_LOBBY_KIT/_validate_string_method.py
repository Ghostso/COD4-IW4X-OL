# -*- coding: utf-8 -*-
"""验证"字符串搜包"方法论是否可靠。"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
IIPS = os.path.abspath(os.path.join(ROOT, "..", "COD OL", "IIPS", "IIPSDownload"))
POS = [b"main/images/pcb_amorphous01_item_icon", b"pcb_amorphous01",
       b"PLAYERCARDS_PCB_AMORPHOUS01_NAME", b"codo.objects",
       b"callsignNameplate", b"marketplace", b"iwi", b"main/images"]


def main():
    pack = os.path.join(IIPS, "lf_init_common_marketplace_1_V49.ifs")
    if not os.path.exists(pack):
        print("缺 %s" % pack)
        return 1
    size = os.path.getsize(pack)
    print("包 %s (%d MB)" % (os.path.basename(pack), size // 1048576))
    b = open(pack, "rb").read()
    print("读入 %d 字节" % len(b))
    print()
    for nd in POS:
        print("  %-44s %d 次" % (nd.decode("latin1"), b.count(nd)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
