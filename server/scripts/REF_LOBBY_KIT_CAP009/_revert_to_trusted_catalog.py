# -*- coding: utf-8 -*-
"""回到唯一可信的目录: exe 反射提取的 marketplace-catalog.json。

理由(本轮实测):
  - exe 目录(37615 条)是从 exe 里**反射提取**的, Item/Category/Currency 都权威
  - 我后来从内存扒的 101 条, item 值集中在个位数(12/13/28/49...), 是噪声
  - 两者 SKU 编号 0 交集 -> 不是同一套体系, 不能混

做法: 把 marketplace-catalog-client.json 恢复成 exe 目录的完整拷贝,
      **不再合并**任何内存推断出来的条目。
"""
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "marketplace-catalog.json")
DST = os.path.join(ROOT, "marketplace-catalog-client.json")
BAK = os.path.join(ROOT, "marketplace-catalog-client.json.bak_inferred")


def main():
    exe = json.load(open(SRC, "r", encoding="utf-8"))
    print("exe 目录 %d 条" % len(exe))
    if os.path.exists(DST):
        shutil.copy(DST, BAK)
        print("已备份当前客户端目录 -> %s" % os.path.basename(BAK))
    with open(DST, "w", encoding="utf-8") as f:
        json.dump(exe, f, ensure_ascii=False, separators=(",", ":"))
    print("已恢复为 exe 目录的完整拷贝: %d 条" % len(exe))
    return 0


if __name__ == "__main__":
    sys.exit(main())
