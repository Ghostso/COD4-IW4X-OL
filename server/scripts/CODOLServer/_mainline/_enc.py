from pathlib import Path
from capstone import CS_ARCH_X86, CS_MODE_32, Cs
# verify the encodings
md=Cs(CS_ARCH_X86,CS_MODE_32)
for b in (bytes.fromhex("fe87e0050000"),):
    for i in md.disasm(b, 0xBA3A18):
        print("0x%08X  %s  %s  (len=%d)" % (i.address, i.mnemonic, i.op_str, len(i.bytes)))
print()
print("原指令 0xBA3A18: 89 8D 70 FC FF FF   mov [ebp-0x390], ecx   (6 字节)")
print("替换为        : FE 87 E0 05 00 00   inc dword [edi+0x5E0]  (6 字节)")
print("副作用：不再更新游标 [ebp-0x390] —— 但游标在 0xBA3A07 已由 ecx 载入，")
print("        而 0xBA3A18 的写入本就是把它存回，去掉后游标保持 0xBA3A07 的值。")
print("        => 可能影响后续读取；先用它做【到达性探测】，不追求行为正确。")
