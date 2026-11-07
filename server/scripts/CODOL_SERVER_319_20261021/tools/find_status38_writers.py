# -*- coding: utf-8 -*-
"""追 [obj+0x38] 的写入点 —— 状态码从哪来。

已知:
  0x4AA6CC  mov esi, [ebx+0x28]     ; esi = 某个对象
  0x4AA6D0  mov ecx, esi
  0x4AA6D2  call 0x927100           ; 返回 [ecx+0x38]
  0x4AA6D8  mov eax, [ebx+0x40]
  0x4AA6DC  mov ecx, esi
  0x4AA6DE  call 0xb83d70

要找: 谁写 [X+0x38]。32 位下典型机器码:
  mov dword [reg+0x38], eax   -> 89 4x 38  (modrm: mod=01 rm=reg, reg=eax)
  mov dword [reg+0x38], imm32 -> C7 4x 38 xx xx xx xx
  也扫 mov dword [reg+disp32], eax -> 89 8x 38 00 00 00

做法: 扫全 .text 里所有 "?? 38" 形态太宽; 改用**限定位移 0x38 且 base 为常见寄存器**,
      再反汇编确认是不是写 +0x38。
"""
import struct
from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

DUMP = Path(r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\LIVE_FULLMEM_20261022\mem\mem_000.bin")
BASE = 0x400000


def main():
    b = DUMP.read_bytes()
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True

    # 候选机器码前缀(mod=01, disp=0x38, reg=eax/ecx/edx/ebx):
    #   89 40 38  mov [eax+0x38], eax
    #   89 48 38  mov [eax+0x38], ecx
    #   89 50 38  mov [eax+0x38], edx
    #   89 58 38  mov [eax+0x38], ebx
    #   (rm 换成 ecx/edx/ebx/esi/edi/ebp 时 modrm 低 3 位变化)
    pats = []
    for reg in range(8):          # source reg
        for rm in range(8):       # base reg
            modrm = 0x40 | (reg << 3) | rm
            pats.append(bytes([0x89, modrm, 0x38]))

    found = []
    for p in pats:
        i = 0
        while True:
            j = b.find(p, i)
            if j < 0:
                break
            va = j + BASE
            if 0x401000 <= va <= 0xC00000:
                found.append((va, p))
            i = j + 1
    found.sort()
    print("找到 %d 处可能的 `mov [reg+0x38], reg`" % len(found))

    # 只看 0x4A0000-0x4B0000 这段(订阅逻辑所在区)
    near = [x for x in found if 0x4A0000 <= x[0] <= 0x4B0000]
    print("其中在 0x4A0000-0x4B0000 区间的 %d 处:" % len(near))
    for va, p in near[:20]:
        start = max(0, (va - BASE) - 6)
        code = b[start:(va - BASE) + 10]
        insns = list(md.disasm(code, start + BASE))
        txt = " | ".join("%s %s" % (x.mnemonic, x.op_str) for x in insns)
        print("  0x%08X  [%s]  %s" % (va, p.hex(), txt[:110]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
