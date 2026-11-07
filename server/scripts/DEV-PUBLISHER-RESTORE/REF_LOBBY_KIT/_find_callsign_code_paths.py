# -*- coding: utf-8 -*-
"""在内存里找"客户端读名片表"的代码路径 —— 为挂钩定位。

已知 CallSignObj 的字段名和 ActionScript 元数据都在
r_259D0000_06400000.bin 里。找它们附近的**函数名字符串**,
那些就是客户端真正调用的函数(可以下断)。
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(ROOT, "mem_linear", "r_259D0000_06400000.bin")


def main():
    b = open(P, "rb").read()
    # 找 Callsign_* 函数名
    fns = sorted(set(m.group(0).decode("latin1")
                     for m in re.finditer(rb"Callsign_[A-Za-z_]{4,60}", b)))
    print("Callsign_* 函数 %d 个:" % len(fns))
    for f in fns:
        print("  %s" % f)
    print()
    # 找 codo.objects::CallSignObj/ 的字段访问器
    fields = sorted(set(m.group(0).decode("latin1")
                        for m in re.finditer(
                            rb"codo\.objects::CallSignObj/[A-Za-z_]{3,60}", b)))
    print("CallSignObj 字段访问器 %d 个:" % len(fields))
    for f in fields:
        print("  %s" % f)
    print()
    # 找 card* 字段名(可能的 getter/setter)
    getters = sorted(set(m.group(0).decode("latin1")
                         for m in re.finditer(
                             rb"(?:get|set)[A-Z][A-Za-z]{3,40}", b)))
    cand = [g for g in getters if re.search(
        r"(card|call|title|icon|background|nameplate|frame|badge)", g, re.I)]
    print("card/callsign 相关 getter/setter %d 个:" % len(cand))
    for g in cand[:60]:
        print("  %s" % g)
    return 0


if __name__ == "__main__":
    sys.exit(main())
