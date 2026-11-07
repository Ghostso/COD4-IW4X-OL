# -*- coding: utf-8 -*-
import io, os
wd=r"D:\BaiduNetdiskDownload\使命召唤OL\E10_CONFIGSTRING_DISPATCH_001"
fixes = {
 "01_A2660_CALLER_INVENTORY.md": [
   ("| E-09：调用者为 `0x3512A0` 与 `0x352E80` | **函数边界误判**：C2/C3 位于 `0x352F80`，不是 `0x352E80` | `0x352F80` 为独立入口，`0x352E80` 在 `0x352F2A` 已 `ret`，二者之间有 `int3` 填充 |",
    "| E-09：调用者为 `0x3512A0` 与 `0x352E80` | **函数边界误判**：C2/C3 位于 `0x352F80`，不是 `0x352E80` | `0x352E80` 在 `0x352F24` 已 `ret`，`0x352F25..0x352F2F` 为 `int3` 填充；`0x352F30` 起为另一入口，`0x352F80` 又是独立入口 |"),
 ],
 "02_OUTER_DISPATCH_CALLGRAPH.md": [
   ("| 函数入口 | RVA `0x352F80` | DIRECT |",
    "| 函数入口 | RVA `0x352F80`（前驱 `0x352E80` 在 `0x352F24` 已 `ret`） | DIRECT |"),
   ("| case 7 | `0x354740` 写 1 字节 | DIRECT |",
    "| case 7 | `0x354740` 经同一函数指针读 1 字节到 `[esi+0x723c24]` | DIRECT |"),
 ],
 "11_START_GATING_AUDIT_ADDENDUM.md": [
   ("| A-10-4 | 核对 case 6 键枚举（0..8）与 wire opcode 的常量映射 | 完成外层映射 |",
    "| A-10-4 | 核对 case 6 键枚举（0..8）与 wire opcode 的常量映射 | 完成外层映射 |"),
 ],
}
for name, pairs in fixes.items():
    p=os.path.join(wd,name)
    s=open(p,encoding="utf-8").read()
    for a,b in pairs:
        if a not in s:
            print("MISS",name,a[:60]); continue
        s=s.replace(a,b)
    open(p,"w",encoding="utf-8",newline="\n").write(s)
    print("fixed",name)
