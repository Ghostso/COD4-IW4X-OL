# GAMESTATE_CONFIGSTRING_TRACE — gamestate / configstring 解析族

**分析对象：** `image_best.bin`，`17cef6e0…`
**地址约定：** `file_offset = RVA = VA - 0x400000`
**方法：** `int3` 填充序言恢复 + `E8 rel32` 调用解析 + 字符串/常量扫描。**无插桩。**

---

## 1. 结论摘要

| 问题 | 状态 |
|---|---|
| 目标镜像中存在 gamestate/configstring 解析族 | **CONFIRMED**（函数边界 + 相互调用） |
| 该族与 TASK-009 标签（`parseGameState` / `parseConfigStrings`）一一对应 | **UNKNOWN** |
| 读取顺序、字段宽度 | **UNKNOWN**（族内未见可直接命名的字段常量） |
| "先 gamestate → 再 configstring → 再 snapshot" | **UNKNOWN**（未定位驱动该顺序的分派器） |
| 冻结服务器的 `0x25`/`0x92` 禁用字节规则在本目标成立 | **不存在**（见 §3） |

> **纪律：** 本轮**不**把冻结服务器 2697 写入器的字段顺序当作目标客户端事实。任务书 §3 明确要求"未从目标二进制或可靠目标版本数据中确认的字段一律标记 UNKNOWN，不得照搬其他版本"。

---

## 2. 目标解析族 — 函数边界与调用关系

`0x6D000..0x6E100` 区间经 `int3` 填充恢复，共 11 个真实函数入口：

```
6D060  6D360  6D6E0  6D870  6D960  6D9D0  6DA30  6DAE0  6DCF0  6E030  6E0A0
```

**各入口的直接调用关系（`E8 rel32` 解析，仅列函数内调用）：**

| 入口 RVA | 直接调用 |
|---|---|
| `0x6D060` | `0x4340` ×3 |
| `0x6D360` | `0x1AB9A0`、`0x1ABA00`、`0x6CFA0`、`0x6C9D0`、**`0x6D060`**、`0x6D1B0`、`0x83C20F`(栈检查) ×3 |
| `0x6D6E0` | `0x42C0` ×3、`0x42E0`、`0x83C20F` |
| `0x6D870` | `0x83C20F` |
| `0x6D960` | `0x73C60`、`0x3854F0`、`0x63A20`、`0x3847A0` |
| `0x6D9D0` | **`0x6D8F0`** |
| `0x6DA30` | **`0x6D870`**、`0x3EC90`、**`0x6D6E0`**、`0x3EC90`、`0x3EB70` |
| `0x6DAE0` | **`0x6D6E0`**、`0x2695A0`、`0x268470`、`0x268560`、`0x83C20F` |
| `0x6DCF0` | **`0x6DAE0`**、`0x42C0` |
| `0x6E030` | **`0x6DCF0`**、`0x83C20F` |
| `0x6E0A0` | `0x6D8F0`、`0x3833E0`、`0x383410`、**`0x6D870`**、`0x2695A0` |

**已读出的最小调用骨架（`CONFIRMED`）：**
```
0x6E030 -> 0x6DCF0 -> 0x6DAE0 -> 0x6D6E0
0x6DA30 -> {0x6D870, 0x6D6E0}
0x6E0A0 -> {0x6D8F0, 0x6D870}
0x6D360 -> {0x6D060, 0x6D1B0}
```
即存在一条 `0x6E030 → 0x6DCF0 → 0x6DAE0 → 0x6D6E0` 的**逐层收敛**调用链，形态上符合"消息级 → 块级 → 项级"的解析分层，但**分层语义未证**。

证据：`evidence\characterize_parse_family.out.txt`

---

## 3. 禁用字节规则交叉核对（新增证据）

冻结服务器 2697 写入器含一条硬校验：

```
Codol2697Protocol.cs:512
  if (b == 0x25 || b == 0x92) throw new ArgumentException("forbidden configstring byte");
```

**本轮在目标镜像中被测区间的独立扫描结果：**

| 扫描范围 | `cmp …, 0x25` | `cmp …, 0x92` |
|---|---:|---:|
| 全 `.text`（`0x1000..0x8A6000`） | 101 处 | 20 处 |
| **configstring 解析族 `0x6D870..0x6E100`** | **0** | **0** |

**判定：**
- 该禁用字节规则**不能**在目标客户端对应区间得到印证 ⇒ 它是**冻结服务器侧的编码约束**，不是目标客户端行为。
- 因此 `SERVER_IMPLEMENTATION_GAP.tsv` 中该规则归类为 **"仅适用于旧协议模式 / 无目标证据"**，**不得**升格为目标协议约束。
- 全 `.text` 中的 121 处命中分属其他模块（字符串/JS/路径处理等），**与 configstring 无关**，不作推断。

证据：`evidence\check_forbidden_bytes.out.txt`

---

## 4. 服务端消息 opcode（0..5）分派表 — 未定位

按任务要求，本轮对"opcode 0..5 分派"做了系统性搜索：

- 扫描策略：全 `.text` 内 `jmp dword ptr [reg*4 + disp32]` 且 `disp32` 指向**6 个**合法 `.text` 目标的形式。
- 命中总数：**269** 处 6 项跳表。
- 逐项检查**邻近函数**是否属于解析族（`0x6C000..0x70000`）或含 `getchallenge`/`gamestateupdate` 等字面量：**无一命中**。

**结论：`UNKNOWN`。** 本目标的服务端消息 opcode 分派**未定位**。
（TASK-009 声称 `parseServerMessage 0x46E6A0` 为分派入口，该地址在本镜像中**不是函数入口**，见 `BATTLE_RX_CALLCHAIN.md` §1。）

**候选（**仅登记，不作结论**）：** `0x5D92B`（表 `0x5DB58`）、`0x39634`（表 `0x39700`）等 6 项跳表位于 `.text` 低区，形态与"消息类型分派"相似，但**没有任何字符串/调用证据**把它们与 gamestate/configstring 绑定。

---

## 5. configstring 数据流（已达成的部分）

以下为**仅凭本目标自身**能够确定的环节：

| 环节 | 证据 | 等级 |
|---|---|---|
| configstring 类解析函数存在于 `0x6DAE0` / `0x6DCF0` / `0x6E030` | 序言边界 + 相互调用 | **CONFIRMED**（存在性） |
| 其中 `0x6DAE0` 调用 `0x268470` / `0x268560` / `0x2695A0` | `E8` 解析 | **CONFIRMED** |
| 这些被调用函数是"字符串表/哈希"语义 | — | **UNKNOWN** |
| 索引宽度、索引上界、是否稀疏 | — | **UNKNOWN** |
| 禁用字节（`0x25`/`0x92`） | §3 | 目标内**不存在** |

**未达成的环节（不得推测）：** 位流起点、索引编码（是否 index-skip）、表容量、非法索引的拒绝分支、与 snapshot 的先后关系。

---

## 6. 与冻结服务器的对照（只读）

| 冻结服务器 | 目标客户端 | 判定 |
|---|---|---|
| `Codol2697ConfigStringWriter.Build` 使用 index-skip（`WriteIndex`：相邻则 1 bit，否则 1 bit + 13 bit） | 目标镜像该规则**未证** | **暂缓**（无目标证据） |
| 索引上界 `0x1DD6`（`ValidateIndex`） | 目标镜像**未证** | **暂缓** |
| 禁用字节 `0x25`/`0x92` | 目标镜像**未出现该规则** | **不适用**（仅服务器侧约束） |
| `BuildGameState(version, map, field4, fieldC, field8, …)`（来源标注：服务端 RVA `0xA21B8`/`0xA0468`，属 **2697 服务端**） | 目标为 **3.19.26.22**，非 2697 | **OLD PROTOCOL**（不得套用） |
| `protocol_mode = legacy3333`（默认） | 目标为 3.19.26.22 | **OLD PROTOCOL**（C-3333 抓包链） |
| `enable_experimental_snapshot2697 = 0` | — | **暂缓**（实为正确处置） |

**判定：** 冻结服务器在 gamestate/configstring 上**没有任何一项**可被本轮升格为"目标协议已确认"。
最小差异因此落在 **OOB 层**（见 `00_INDEX.md` §4 第 4 问 与 `SERVER_IMPLEMENTATION_GAP.tsv` 的 `GAP-001`），而**不是** gamestate/configstring 层。

---

## 7. 未闭合项

| 项 | 状态 |
|---|---|
| `0x6D360` 是否即 `parseGameState` | `UNKNOWN` |
| `0x6DAE0`/`0x6DCF0` 是否即 `parseConfigStrings` | `UNKNOWN` |
| `0x6D060`（唯一命中序言者）语义 | `UNKNOWN` |
| gamestate → configstring → snapshot 顺序 | `UNKNOWN` |
| 服务端消息 opcode 分派表位置 | `UNKNOWN` |
| configstring 索引编码与上界 | `UNKNOWN` |
