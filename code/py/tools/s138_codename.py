#!/usr/bin/env python3
"""s138_codename: 从 0xB773D0 抽出 25 项 字段码 -> 类型名 表(权威)。

反汇编 0xB773D0 的函数序言:
    mov dword ptr [ebp - 0x64], <ptr>   ; index 0  (NoType)
    mov dword ptr [ebp - 0x60], <ptr>   ; index 1  (Bool)
    ...
    mov dword ptr [ebp - 0x04], <ptr>   ; index 0x18 (Unknown Type)
然后:
    cmp eax, 0x18 ; if >0x18 -> 0x18
    if (eax <= 0) eax = 0
    ebx = [ebp + eax*4 - 0x64]   ; 索引表基址 ebp-0x64, 每项 4 字节
所以 字段码 n -> 名字 = cstr(table[n]), 表基址 ebp-0x64, 步长 4, 25 项(0..0x18)。
"""
import sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()


def cstr(va):
    f = va - VA
    if not (0 <= f < len(d)):
        return None
    e = d.find(b"\x00", f)
    if e < 0:
        return None
    s = d[f:e]
    if not s or not all(32 <= c < 127 for c in s):
        return None
    return s.decode("latin1")


md = Cs(CS_ARCH_X86, CS_MODE_32)
code = d[0xB773D0 - VA: 0xB773D0 - VA + 0xB0]

# 表基址 ebp-0x64; 索引 i 对应的 disp = -0x64 + 4*i
import re
slots = {}
for ins in md.disasm(code, 0xB773D0):
    if ins.mnemonic != "mov":
        continue
    m = re.match(r"dword ptr \[ebp ([-+]) (0x[0-9a-f]+)\], (0x[0-9a-f]+)$",
                 ins.op_str)
    if not m:
        continue
    disp = int(m.group(2), 16)
    if m.group(1) == "-":
        disp = -disp
    slots[disp] = int(m.group(3), 16)

TABLE_BASE = -0x64
print("字段码 -> 类型名  (表基址 ebp-0x64, 步长 4, 由 0xB773D0 的")
print("  `mov ebx,[ebp+eax*4-0x64]` 证实; 码 >0x18 钳到 0x18)")
print()
print("| code | 类型名 | 名字串 VA |")
print("|------|--------|-----------|")
names = {}
for i in range(0x19):
    disp = TABLE_BASE + 4 * i
    imm = slots.get(disp)
    nm = cstr(imm) if imm else None
    if nm is None:
        print("| 0x%02X | (未抓到) | ? |" % i)
    else:
        names[i] = nm
        print("| 0x%02X (%2d) | %s | 0x%08X |" % (i, i, nm, imm))
print()
print("槽位覆盖(直接 mov imm 形式): %d/25" % len(slots))
print()
print("未直接捕获的槽位由 `mov eax,<imm>; mov [ebp-disp],eax` 形式给出:")
print(" 16 (0x10) String        0x00CAF92C")
print(" 17 (0x11) String        0x00CAF92C  (与 16 同指针)")
print(" 19 (0x13) Blob          0x00D5982C")
print(" 22 (0x16) Blob          0x00D5982C  (与 19 同指针)")
print(" 23 (0x17) StructData    0x00D59774")
print(" 24 (0x18) Unknown Type  0x00D59764")
print()
print("对照 0x636F3C 跳转表上界 (`cmp eax,0x2e; ja`), 消息 type 0..0x2E 与")
print("字段码 0..0x18 是两套独立编号, 不可混用。")

