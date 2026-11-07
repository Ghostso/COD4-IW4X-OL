from pathlib import Path
img=Path(r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin")
d=img.read_bytes(); BASE=0x400000
print("=== 0xBA3A00..0xBA3A10 (check for a 5-byte spare) ===")
for insn_addr, ln in [(0xBA3A9D,6),(0xBA3AA3,6),(0xBA3AA9,2)]:
    print("  0x%08X  %s" % (insn_addr, d[insn_addr-BASE:insn_addr-BASE+ln].hex()))
print()
print("方案：把 0xBA3A9D 的 6 字节改成 jmp 到桩（用 5 字节 E9 + 1 字节 NOP）")
print("  桩放 0xBA3FA4（12 字节可用）：")
print("    88 97 D4 06 00 00      mov [edi+0x6D4], dl     (6)")
print("    8A 95 76 FC FF FF      mov dl,[ebp-0x38a]      (6)  原指令")
print("    ... 12 字节刚好用完，但需要 jmp 回来（5 字节）=> 不够")
print()
print("改用 0xBA41A1（15 字节）：")
print("    88 97 D4 06 00 00      (6)  记录 dl")
print("    8A 95 76 FC FF FF      (6)  原指令")
print("    E9 ?? ?? ?? ??         (5)  jmp 回 0xBA3AA3")
print("    合计 17 > 15，仍差 2")
