#!/usr/bin/env python3
"""134 卷工具: 逐字节重验 AS_* 注册器 (修正 133 的 838 成分错误).

判据(四条同时成立; ★ 不检查函数头形态 — MSVC 叶子函数没有 push ebp):
  1) 函数入口前两字节 == cc cc            (int3 对齐)
  2) 体内前 0x300 字节有 mov [reg], <vtable>
  3) <vtable> 属于 as_objs_true.json (829 个)
  4) 写入点距函数入口 <= 0x400            (排除数据区误撞)

★ 为什么不能用 "函数头必须是 55 8b ec":
  0x6AEBD0 头是 57 8b f8 (push edi; mov edi,eax)
  0x728350 头是 53 bb 01 00 00 00 (push ebx; mov ebx,1)
  两者都是合法注册器 —— 叶子函数省略帧指针建立。

输出: tools/as_regfns_v2.json  (838 条, 覆盖 829/829)
"""
import json
import re
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

IMG = r"E:\codol_re\client_image_20261027.bin"
OUT = r"D:\BaiduNetdiskDownload\使命召唤OL\tools"
VA = 0x400000
# c7 /0 = mov r/m32, imm32 —— ModRM 的低 3 位是 /0，reg 字段编码目标寄存器
MOV_MODRM = (0x00, 0x40, 0x41, 0x42, 0x43, 0x45, 0x46, 0x47)

d = open(IMG, "rb").read()
N = len(d)


def fnstart(va):
    """向上找最近的 cc cc 对齐点 —— 只在双向验证后可信(见 §四)。"""
    f = va - VA
    for back in range(0, 0x900):
        if f - back - 2 >= 0 and d[f - back - 1] == 0xCC and d[f - back - 2] == 0xCC:
            return VA + f - back
    return None


def main():
    objs = json.load(open(OUT + r"\as_objs_true.json"))
    vtset = {o[0] for o in objs}
    reg = {}
    for vt in vtset:
        pat = struct.pack("<I", vt)
        pos = 0
        while True:
            i = d.find(pat, pos)
            if i < 0:
                break
            pos = i + 1
            va = VA + i
            fs = fnstart(va)
            if not fs or va - fs > 0x400:
                continue
            f = fs - VA
            ok = False
            for j in range(f, min(f + 0x300, N - 5)):
                if d[j] == 0xC7 and d[j + 1] in MOV_MODRM:
                    if struct.unpack_from("<I", d, j + 2)[0] == vt:
                        ok = True
                        break
            if ok:
                reg.setdefault(fs, set()).add(vt)

    cov = set()
    for s in reg.values():
        cov |= s
    print("真注册器 %d 个, 覆盖 %d / %d" % (len(reg), len(cov), len(objs)))
    unc = [o for o in objs if o[0] not in cov]
    print("未覆盖:", [(hex(o[0]), o[1]) for o in unc] if unc else "无")
    json.dump(sorted(reg), open(OUT + r"\as_regfns_v2.json", "w"))
    print("-> as_regfns_v2.json")


if __name__ == "__main__":
    main()
