#!/usr/bin/env python3
"""132 卷工具: 枚举 AS_* 对象虚表.

判据(三条同时成立):
  1) vftable[-1] 是合法 MSVC COL:  +00/+04/+08 全零, +0C -> type_info, type_info+08 -> ".?A..."
  2) vftable[0] == 0x00693DD0            (共享标量删除析构 shim)
  3) vftable[1] 落在 .tp3 代码段 0x401000..0xCA789A

★ 全部输入输出一律 VA;(内部减 0x400000 换算文件偏移)
★ 不要用步进扫表 —— 步进是假设不是发现(132 探讨 §一)

输出: tools/as_objs_true.json  [[vtable_va, col_name, handler_va], ...]
"""
import json
import re
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

IMAGE = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
DTOR_THUNK = 0x00693DD0
CODE_LO, CODE_HI = 0x401000, 0xCA789A

d = open(IMAGE, "rb").read()
N = len(d)


def u32(va, off=0):
    return struct.unpack_from("<I", d, va - VA + off)[0]


def cstr(va, lim=160):
    f = va - VA
    if not (0 <= f < N):
        return None
    e = d.find(b"\x00", f)
    if e < 0 or e - f > lim:
        return None
    return d[f:e].decode("latin1", errors="replace")


def col_name(col):
    """合法 COL -> 类名; 否则 None。"""
    if not (VA + 20 <= col <= VA + N - 20):
        return None
    if struct.unpack_from("<III", d, col - VA) != (0, 0, 0):
        return None
    td = u32(col, 0x0C)
    if not (VA <= td < VA + N):
        return None
    nm = cstr(td + 8)
    return nm if nm and nm.startswith(".?A") else None


def main():
    objs = []
    for vt in range(VA + 0x1000, VA + N - 0x40, 4):
        nm = col_name(u32(vt, -4))
        if not nm:
            continue
        if u32(vt) != DTOR_THUNK:
            continue
        h = u32(vt, 4)
        if not (CODE_LO <= h < CODE_HI):
            continue
        objs.append([vt, nm, h])

    print("真·AS 对象虚表: %d 个" % len(objs))
    from collections import Counter
    dup = Counter(o[2] for o in objs)
    print("handler 复用度 top5:", ["0x%08X x%d" % (k, v) for k, v in dup.most_common(5)])
    out = r"D:\BaiduNetdiskDownload\使命召唤OL\tools\as_objs_true.json"
    json.dump(objs, open(out, "w"), indent=0)
    print("-> " + out)


if __name__ == "__main__":
    main()
