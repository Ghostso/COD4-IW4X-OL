# 06 — 客户端/服务端 Configstring 字段矩阵

> 基准：E-09 已确认的客户端 body reader `0xA2660`；服务端 `_CODOL2697_WriteConfigstrings RVA 0xA0468`。
> 等级：`DIRECT` / `CROSS`（两侧）/ `INFERRED` / `BLOCKED`
> 位偏移从 `0x04` 首位起算（服务端 count1=16 模型）。

---

## 1. 总矩阵

| # | 字段 | 客户端证据 | 服务端证据 | 位偏移 | 字节偏移 | 边界条件 | 结论 |
|---|---|---|---|---|---|---|---|
| F1 | 外层 `0x04` | `0x352FA1 inc [esi+0x1c]` 跳过 1 字节后进入 body（INFERRED） | `WriteByte(4)` @0xA07F8（DIRECT） | 0–7 | 0 | 1 字节整 | **CROSS(INFERRED)**：位置一致，值比较未证 |
| F2 | `count1` = 2 字节 | `push 2 / call MSG_ReadData` @0xA26AF–0xA26B2；`movsx word` @0xA26B7 | `WriteShort(count1)` @0xA0807，`0x99566 ECX=2` | 8–23 | 1–2 | 16 bit little-endian，`movsx` 有符号 | **PROVEN（CROSS）** |
| F3 | 索引连续性标志 | `call 0x44C8C0`（连续则 `lea edi,[ebx+1]`；否则读 13 bit） | `0x400 WriteIndexDelta`（1 bit 连续 / 1+13 bit 绝对） | 24… | — | 首索引 last=-1 | **PROVEN（CROSS）** |
| F4 | 13-bit 绝对索引 | `push 0xD / call MSG_ReadBits` @0xA26F0–0xA26F4 | 13-bit 绝对索引 | 视分支 | — | 上界 `≤0x1DD6`（0x1DD7 跳过） | **PROVEN（CROSS）** |
| F5 | 索引上限 | `cmp edi,0x1DD7; jl` @0xA2702–0xA2708 | `cmp esi,0x1DD6; ja` @0xA053E | — | — | `0x1DD7` 拒绝/跳过 | **PROVEN（CROSS）** |
| F6 | 合法区间 0..0x13 跳过 0x12 | `mov cl,[edi+0x2BD0A40]; cmp 0x14 / cmp 0x12` @0xA2728–0xA2736 | 同表区间校验 | — | — | `>=0x14` 或 `==0x12` 特殊处理 | **PROVEN（CROSS）** |
| F7 | A1 字符串 | `0xA25F0` 按 NUL 扫描（`mov cl,[eax]; test; jne`）@0xA2800；字符串处理 @0xA2751 | `WriteLenStr` @0xA096F（strlen+1 字节） | 24+Δ | 3+ | NUL 终止；长度上限 0x1FFF | **PROVEN（CROSS）** |
| F8 | A2 计数 | `push 0xB / call MSG_ReadBits` @0xA2765–0xA276C | A2 段计数 10 bit | 视 A1 长度 | — | 0 时跳过整段 | **PROVEN（CROSS）** |
| F9 | A2 条目（索引+10 bit） | `push 0xD` 索引 + `push 0xA` 值 @0xA27A4–0xA27D7 | use 10 bit 值 | — | — | 索引同 F4/F5 | **PROVEN（CROSS）** |
| F10 | A3 计数 | `push 0xA / call MSG_ReadBits` @0xA2872–0xA2879 | A3 段计数 10 bit | 视 A1/A2 | — | 0 时跳到函数尾 | **PROVEN（CROSS）** |
| F11 | A3 子过程 `0xA2480` | `call 0xA2480` @0xA28E0 | A3 记录：10+7+4+n×12 | — | — | n≤0xF；A≤0x3FF；B≤0x7F | **PROVEN（CROSS）** |
| F12 | A3 内部位宽 | `MSG_ReadBits(10/7/4/12)` @0xA2490–0xA24A7 | 10/7/4/12 | — | — | — | **PROVEN（CROSS）** |
| F13 | 外层 `0x06` | **无客户端读取证据** | `WriteByte(6)` @0xA0997 | 依输入 44/53/61/72/129… | — | 不保证字节对齐 | **BLOCKED（客户端侧）** |
| F14 | 外层 `0x04` 值比较 | 无 `cmp ...4`（四区域扫描命中 0） | 常量 4（DIRECT） | — | — | — | **BLOCKED** |

## 2. 逐字段分级的强制声明

Configstring body 字段顺序按字段独立裁定。**已 PROVEN 的字段**：F2、F3、F4、F5、F6、F7、F8、F9、F10、F11、F12。**未闭合**：F1（值比较）、F13、F14。

**禁止：** 把 F2–F12 的局部一致上升为“整条消息互操作已证实”。外层框架（F1/F13/F14）未闭合，整体互操作仍为 **BLOCKED**。

## 3. 两侧调用链对照

| 侧 | 路径 |
|---|---|
| 服务端 | `_CODOL2697_WriteGamestate` `0xA21B8` → `call _CODOL2697_WriteConfigstrings` `0xA0468` → `0xA07F8 WriteByte(4)` → `0xA0807 WriteShort(count1)` → 三段 → `0xA0997 WriteByte(6)` |
| 客户端 | `0x3547D0`(读1字节键) → `0x354100`(9项跳转表, case 6) → 读4字节长度+载荷 → `0x352F80`(+1字节) → `0xA2660`(count1 + 三段) → `ret` |

**两侧字段级顺序一致（CROSS）**；外层映射**未证**。

## 4. 层归属更正

0x04 / 0x06(@0xA0997) 属于 Gamestate(0x03) 内部子帧的头/尾；0x06(@0xA22F8) 是 Gamestate 顶层尾，禁止跨层合并。详见 03 第 7 节。
