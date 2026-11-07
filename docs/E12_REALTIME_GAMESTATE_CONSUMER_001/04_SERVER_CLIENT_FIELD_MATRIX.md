# 04 — 服务端/客户端字段矩阵 / FIELD MATRIX

> 基准：服务端 `_CODOL2697_WriteGamestate` RVA `0xA21B8`；客户端候选 `0x34FD80(1)`（demo 路径，唯一已定位的 `0x03` 处理点）。
> 等级：`PROVEN` / `INFERRED` / `BLOCKED` / `REFUTED`

---

## 1. 顶层字段矩阵

| 字段/阶段 | 服务端写入证据 | 客户端读取证据 | 裁定 |
|---|---|---|---|
| 消息类型 `0x03` | `0xA224C WriteByte(3)`（`0x99551`，ECX=1） | `0x3501EF dec eax` + 表项 3 → `0x34FD80(1)` | **PROVEN**（两侧各证；对应关系 DIRECT） |
| 初始整数 | `0xA225A WriteInt32`（4B） | `0x34FDB0` 读 4B → `[edi+0x40148]` | 宽度同；语义 **BLOCKED** |
| 字符串 1 | `0xA2269 WriteLenStr(map)`（cstring） | `0x34FDD0` 读 4B（**非 cstring**） | **REFUTED** |
| 字符串 2 | `0xA2279 WriteLenStr("mp")`（cstring） | `0x34FE3F` 读 4B 长度 | **REFUTED** |
| 字段 4 | `0xA2288 WriteInt32(field4)` | `0x34FEAC` 读 `len` 字节载荷 | **REFUTED** |
| Configstring 子帧 | `0xA22C1 call 0xA0468` → `0xA07F8 WriteByte(4)` … `0xA0997 WriteByte(6)` | 无对应（`0x34FD80` 不解析子帧） | **BLOCKED** |
| `0x06` 标记 | `0xA22F8 WriteByte(6)`（顶层尾） | 无 | **BLOCKED** |
| 结束/游标 | `0xA22FD` 检查 overflow 后返回 | `0x35002C` 返回 | **BLOCKED** |

## 2. 结论：字段序不匹配

**客户端 `0x34FD80(1)` 的字段序 `{i32, i32, u32 len, payload}` 与服务端 `{i32, cstring, cstring, i32, <cfgsub>, i32, i32, 0x06}` 在第 2 个字段即冲突（`i32` vs `cstring`）。**

**裁定（REFUTED）：** 两者不是同一消息格式的读写两端。

## 3. Configstring body 字段矩阵（E-11 已证部分）

| 字段 | 服务端证据 | 客户端证据 | 裁定 |
|---|---|---|---|
| count1 = 2 字节 | `WriteShort` `0xA0807`（`0x99566` ECX=2） | `0x26AF push 2` + `MSG_ReadData` + `movsx word` | **PROVEN** |
| 索引连续性标志 | `0xA0400` WriteIndexDelta（1 bit） | `0x44C8C0` + `MSG_ReadBits(0xD)` | **PROVEN** |
| 13-bit 绝对索引 | 13 bit | `0xA26F4 push 0xD` | **PROVEN** |
| A1 字符串 | `WriteLenStr`（strlen+1 字节） | `0xA25F0` NUL 扫描 | **PROVEN** |
| A2 计数 | 10 bit | `0xA276C push 0xB`（11 bit） | **差异，见 §4** |
| A2 值 | 10 bit | `0xA27D7 push 0xA` | **PROVEN** |
| A3 计数 | 10 bit | `0xA2879 push 0xA` | **PROVEN** |
| A3 记录 | 10/7/4/n×12 | `0xA2480 push 0xA/7/4`，n×12 | **PROVEN** |
| 索引上限 | `0x1DD7` | `cmp edi,0x1DD7` | **PROVEN** |

## 4. A2 计数字宽的潜在差异（按任务要求重新检查）

| 侧 | 证据 | 值 |
|---|---|---|
| 服务端 | E-08 记录 A2 计数为 **10 bit** | 10 |
| 客户端 | `0xA2765 push 0xB` → `MSG_ReadBits(11)` | **11** |

**本轮核对结果：** 客户端 A2 计数读取宽度为 **11 bit**（`0xA2765` 指令级，DIRECT）；服务端 E-08 记录为 **10 bit**（来自 `0x99590` 调用参数，未在本轮重新逐指令确认）。

**裁定：** 该差异**保留为 BLOCKED**。本轮**未获得**服务端 A2 计数的精确位宽指令证据（`0xA0468` 内未定位到对应的 `push`/`WriteBits` 序列），因此**不得**断言两侧一致，也**不得**断言冲突。

**最小验证动作：** 在服务端 `0xA0468` 内逐指令定位 A2 段计数写入的 `push` 位宽。

## 5. 分层纪律声明

- 未把**字节宽度**与**位宽**混同（§1 全部标注宽度类型）。
- 未把**写入一个字节**等同于客户端按同语义消费。
- 未因两个字段**均为 32 位**而认为语义匹配。
- 未把服务端**不同层级**的 `0x06`（`0xA0997` 子帧尾 / `0xA22F8` 顶层尾 / `0xA4CAF` snapshot）合并。

## 6. 裁定

| 项 | 裁定 |
|---|---|
| `0x03` 消息类型对应 | **PROVEN** |
| 初始整数宽度 | PROVEN（4B）；语义 BLOCKED |
| 第 2–4 字段 | **REFUTED**（字段序冲突） |
| Configstring 子帧字段（body 内） | **PROVEN**（count1/索引/A1/A2 值/A3） |
| A2 计数位宽 | **BLOCKED**（服务端未复核） |
| 消息结束与游标 | **BLOCKED** |
