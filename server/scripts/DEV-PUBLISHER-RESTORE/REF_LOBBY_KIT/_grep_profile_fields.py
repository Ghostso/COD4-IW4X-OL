# -*- coding: utf-8 -*-
"""在 C# 参考实现里找 public.result 的 125 个字段是什么。

C# 日志: RAW_PROFILE_RESULT kind=public source=disk bytes=33428 fields=125
我们实测: public.result 尾部正好 125 个 07 <i32>。
=> 这 125 个字段就是玩家档案的数据, 应该在 C# 代码里有定义/用法。
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(ROOT, "_ref", "CodolLocalLobbyServer.cs")


def main():
    lines = open(P, "r", encoding="utf-8", errors="replace").read().splitlines()
    print("文件 %d 行" % len(lines))
    for kw in ("fields", "125", "PublicProfile", "public.result",
               "ReadProfile", "ProfileFields", "PlayerProfile"):
        idx = [i for i, l in enumerate(lines) if kw in l]
        print()
        print("== %s: %d 行 ==" % (kw, len(idx)))
        for i in idx[:15]:
            print("%5d| %s" % (i + 1, lines[i].strip()[:150]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
