# 08 — 证据登记（E-10 追加）/ EVIDENCE REGISTER ADDENDUM

> 追加修订，不覆盖 `14_SERVER_KNOWLEDGE_ATLAS_001\_EVIDENCE_REGISTER.md`。
> 每条证据给出：ID、类型、定位、原始输出、等级。

---

| EV ID | 类型 | 定位 | 内容 | 原始输出 | 等级 |
|---|---|---|---|---|---|
| EV-10-01 | XREF | 客户端 `.text` 全节 | `0xA2660` 直接调用点 3 个：`0x3514F0`(call)、`0x352FA7`(jmp)、`0x352FB4`(jmp) | `_data/out_t01_xref.txt` | DIRECT |
| EV-10-02 | REFUTE | `E-09 01` | `0x352FA7/0x352FB4` 属 `0x352F80`，不是 `0x352E80` | `_data/out_t01_xref.txt` | DIRECT |
| EV-10-03 | DISPATCH | RVA `0x354100` | 9 项跳转表 `0x7547AC`，键 = `movzx [ebp+0xc]`，`cmp 8` | `_data/out_full_dispatch.txt` | DIRECT |
| EV-10-04 | DISPATCH | RVA `0x3547D0` | 读 1 字节键，排除 `0x09`/`0x0A`，循环调用 `0x354100` | `_output` t18 | DIRECT |
| EV-10-05 | CALLPATH | RVA `0x354697` (case 6) | 初始化 msg → 读 4 字节长度 → 读载荷 → `0x352F80` → `0xA2660` | `_data/out_t36_postconfig.txt` | DIRECT |
| EV-10-06 | CURSOR | RVA `0x352FA1` | `inc eax` / `mov [esi+0x1c],eax`：进 body reader 前 +1 字节 | `_data/out_t10` 系列 | DIRECT |
| EV-10-07 | SERVER | RVA `0xA07F8` | `WriteByte(4)`（`0x99551` → `0x994FC`，len=1） | `_data/out_t19_server_writer.txt` | DIRECT |
| EV-10-08 | SERVER | RVA `0x99551`/`0x99566` | WriteByte = `mov ecx,1`；WriteShort = `mov ecx,2` | `_data/out_t28_final_checks` | DIRECT |
| EV-10-09 | SERVER | RVA `0x9960A..0x99635` | `bitpos%8==0 ⇒ bitpos=used*8` 强制重同步 | `_data/out_c09.txt` | DIRECT |
| EV-10-10 | SERVER | RVA `0x9949B`/`0x99651` | `MSG_WriteData`/`WriteLenStr` 不更新 `[msg+0x10]` | `_data/out_c09.txt` | DIRECT |
| EV-10-11 | REFUTE | RVA `0xA2D91` | `0xA2DC1` 属独立入口 `0xA2D91`，不在 `0xA2660` 内 | `_data/out_full_a2660.txt` | DIRECT |
| EV-10-12 | CLIENT | RVA `0xA2660` | 读 count1(2B)、A1/A2/A3 后 @0xA2975 `ret`，无 0x06 读取 | `_data/out_full_a2660.txt` | DIRECT |
| EV-10-13 | CLIENT | RVA `0xA2480` | `push 0xA / 7 / 4` → 10/7/4 bit；n×12 bit | `_data/out_t35_readprims.txt` | DIRECT |
| EV-10-14 | CLIENT | RVA `0x1AC1D0` | `MSG_ReadData` 纯逐字节，无位逻辑 | `_data/out_t35_readprims.txt` | DIRECT |
| EV-10-15 | CLIENT | RVA `0x1AC670` | `MSG_ReadBits` 使用 `[msg+0x20]` bitpos，`and 7`/`sar 3` | `_data/out_t35_readprims.txt` | DIRECT |
| EV-10-16 | NULL | 四区域扫描 | `0x350000-0x360000`/`0xA2000-0xA3000` 无 `cmp == 4/6` 命中 | `_data/out_t28_final_checks` | DIRECT（否定） |
| EV-10-17 | BOUNDARY | RVA `0x352E80` | `0x352E80` 在 `0x352F2A` 前 `ret`，其后 `int3`；与 `0x352F80` 为不同函数 | `_data/out_t09` 系列 | DIRECT |
