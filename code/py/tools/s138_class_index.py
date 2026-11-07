#!/usr/bin/env python3
"""s138_class_index: 验证 "0xDC74F8 起连续的 dwRoomMessage* vtable 数组下标 == 消息 type" 假说。

证据链:
  (a) 数组从 0xDC74F8(dwRoomMessageManifold) 到 0xDC76E4(UpdateWarGodData) 连续 44 项;
  (b) 各 item 的 ctor 由 `mov [ebp-0x40], 0xdcXXXX ; ... ; call <deser>` 内联构造,
      构造点落在 0x636F3C 跳转表的对应 case 区间内(见 s138_type_map.py);
  (c) 已知锚点: 0x02 -> Text(0xDC7504) 下标恰 3 ... 但 type 0x02 的构造点在 0x0063495A 区间,
      且 table[0x02]=0x63495A 调 0x625940, 而 0x625940 写 0xDC7504。若 "下标==type",
      则 0xDC74F8 应为 type 0x00。可 type 0x00 handler=0x636F02(空)。=> 假说不成立。

因此本工具改做**逐条锚定**: 对每个 case, 打印 区间内所有已知 ctor 站点 + 类名。
"""
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)


def cstr0(f):
    e = d.find(b"\x00", f)
    return d[f:e].decode("latin1") if e > 0 else None


def name_of(vt):
    try:
        col = struct.unpack_from("<I", d, vt - VA - 4)[0]
        ti = struct.unpack_from("<I", d, col - VA + 0x0C)[0]
        return cstr0(ti - VA + 8)
    except Exception:
        return None


# 0xDC74F8..0xDC76E4 连续数组
ARR = list(range(0xDC74F8, 0xDC76E8, 12))
print("dwRoomMessage* vtable 连续数组 (0xDC74F8 起, 步长 12, 共 %d 项):" % len(ARR))
for i, vt in enumerate(ARR):
    print("  [%2d] 0x%08X  %s" % (i, vt, name_of(vt)))

# 反查每个 vftable 的 imm32 引用点(用 capstone 正确解出 mov [reg+disp], imm32)
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
import re
md = Cs(CS_ARCH_X86, CS_MODE_32)
MOV = re.compile(r"(?:dword ptr )?\[(.+?)\], (0x[0-9a-f]+)$")
refmap = {}
for va in range(0x400000, 0xD00000, 0x10000):
    f = va - VA
    for ins in md.disasm(d[f:f + 0x10000], va):
        if ins.mnemonic == "mov":
            m = MOV.search(ins.op_str)
            if m:
                imm = int(m.group(2), 16)
                if 0xDC7000 <= imm <= 0xDC7800:
                    refmap.setdefault(imm, []).append(ins.address)

print("\n各项的 mov [reg],imm32 构造点:")
for i, vt in enumerate(ARR):
    refs = refmap.get(vt, [])
    print("  [%2d] 0x%08X  %-48s %s" % (
        i, vt, name_of(vt),
        ", ".join("0x%08X" % r for r in refs) or "(无)"))
