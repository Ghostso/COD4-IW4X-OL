# 02 — Configstring 消费候选 / CONFIGSTRING CONSUMER CANDIDATES

> 只读静态分析。等级：`DIRECT` / `CROSS` / `INFERRED` / `BLOCKED`
> 证据：`_data\out_a16..out_a24.txt`

---

## 1. 主候选：客户端 RVA `0xA2660`

**入口边界：** `0xA2660`（`push ebp; mov ebp,esp; sub esp,0x10C`）→ `0xA2975`（`mov esp,ebp; pop ebp; ret`）。

### 1.1 读取轨迹（与服务器写入**逐字段**对应）

| # | 客户端指令 | RVA | 读取内容 | 服务器对应 |
|---|---|---|---|---|
| 1 | `call 0x1AC1D0` with `push 2` | **0xA26B2** | `MSG_ReadData(esi, &tmp, 2)` → **2 字节** | `WriteShort(count1)` @ 0xA0807 |
| 2 | `movsx eax, word [ebp-0x108]` | 0xA26B7 | 取 count（**有符号 16 位**） | — |
| 3 | `test eax,eax; je 0xA2765` | 0xA26CF | count==0 → 跳过 A1 段 | — |
| 4 | `call 0x44C8C0` | 0xA26E2 | 判索引是否 +1 连续 | `WriteIndexDelta` 的 `newIdx==lastIdx+1` |
| 5 | `push 0xD; call 0x1AC670` | **0xA26F4** | 非连续 → **13-bit 索引** | `WriteBits(newIdx,13)` @ 0xA043F |
| 6 | `cmp edi,0x1DD7` | 0xA2702 | 索引上界 | `cmp esi,0x1DD6` @ 0xA053E |
| 7 | `mov cl,[edi+0x2BD0A40]; cmp cl,0x14; cmp cl,0x12` | **0xA2728–0xA2736** | **索引区间表 + 跳过 0x12** | `cmp eax,0x12 / ...` @ 0xA0576 等 |
| 8 | `call 0x4A25F0` | **0xA2751** | 处理该条目（指针在 `edi`） | `WriteLenStr` + `WriteData` @ 0xA0840 |
| 9 | `push 0xB; call 0x1AC670` | **0xA276C** | **11-bit** count | `WriteBits(count,0xB)` @ 0xA085F |
| 10 | `push 0xD; call 0x1AC670` | **0xA27A8** | 13-bit 索引 | 同上 |
| 11 | `push 0xA; call 0x1AC670` | **0xA27D7** | **10-bit** 值 | `WriteBits(v,0xA)` @ 0xA08A0 |
| 12 | `push 0xA; call 0x1AC670` | **0xA2879** | **10-bit** count | `WriteBits(count,0xA)` @ 0xA08BF |
| 13 | `push 0xD; call 0x1AC670` | **0xA28A9** | 13-bit 索引 | 同上 |
| 14 | `call 0x4A2480` | **0xA28E0** | **A3 记录**（见 §2） | A3 组 @ 0xA090B–0xA0974 |

### 1.2 决定性旁证：字符串邻域

| 字符串 | VA | RVA | 用途 |
|---|---|---|---|
| `"** %i %i"` | 0xCB8334 | 0x8B8334 | 在 `0xA24BE` 被压栈（A3 记录格式化） |
| `"* %i"` | 0xCB8344 | 0x8B8344 | 在 `0xA27E0` 被压栈（10-bit 值格式化） |
| `EXE_CONFIGSTRINGMISMATCH` | 0xCB835C | 0x8B835C | 配置不匹配错误串（本函数字符串组内） |
| `gamestateupdate %d` | 0xCB8378 | 0x8B8378 | 紧随其后的 gamestate 提示 |
| `"151106"` / `"151107"` | 0xCB83E0/8 | — | 紧邻的错误码（既有 E4 已记为 0xA2E50 的报错串） |

> 这组字符串是**本函数所在代码块**的标识：`configstring → gamestate` 相邻。

### 1.3 与 0xA2E50 的关系（重要，不得混淆）

`0xA2E50`（E4/E5 的 reliable-command **payload 形状**候选）位于**同一地址簇**，但：
- `0xA2660` **不调用** `0xA2E50`（本轮调用图未出现该边）；
- `0xA2E50` 的报错串（0xCB83E0/0xCB83E8）与 configstring 组**相邻但不同**。

**裁定：`0xA2660` 是 configstring 消费路径；`0xA2E50` 是另一条（仍 `BLOCKED`）路径。二者不可互证。**

---

## 2. 子过程：客户端 RVA `0xA2480`（A3 定长记录）

```
0xA248C  push 0xA ; call 0x1AC670   -> 10-bit  (field A)
0xA2497  push 7   ; call 0x1AC670   ->  7-bit  (field B)
0xA24A3  push 4   ; call 0x1AC670   ->  4-bit  (n)
0xA24BE  push 0xCB8334 ("** %i %i") ; call 0x23CB10  (snprintf)
0xA24CA  test esi,esi ; jle ...     -> if n>0:
0xA24DE..0xA2533  内联读取 n 组 12-bit
```

**与服务端 A3 组（0xA090B/0xA0922/0xA0939/0xA095B）逐项一致：`10 / 7 / 4 / n×12`。**

## 3. 反汇编方法与一致性自检（回答任务 A 第 4 条）

| 项 | 做法 |
|---|---|
| 重同步线性扫描 | 复用 E-06 `sweep.py`（解码失败前进 1 字节）；本轮客户端 `.text` 得 **2,892,767** 条指令 |
| 字节/位原语 | 来自**指令行为**（`movzx byte` vs `or byte,cl` vs `test byte`），**不依赖函数名** |
| 地址换算 | `pe_helper.py`，VA↔RVA 双向自检通过（0x1AC1D0→0x1AB5D0；0xA2E50→0xA2250） |
| 交叉印证 | 每一字段宽度均**同时**在服务端写入点与客户端读取点出现 |

## 4. 候选链对比表

| 链 | 入口 | 位读调用 | 字段宽度序列 | 与服务器 configstring 匹配 | 等级 |
|---|---|---|---|---|---|
| **A** | **0xA2660** | 6 次 | **2B→13b索引→[11b→13b→10b]→[10b→13b→(10/7/4/n×12)]** | **逐字段一致** | **PROVEN** |
| B | 0x6D5D0 | 3 次 | `10b`+`0xA2480` 或 `11b/10b`+`"* %i"` 格式化 | 分支形似，作用对象不同 | **BLOCKED（候选）** |
| C | 0xAA332 | 9 次 | 未解析 | 无字段级对应 | **BLOCKED（候选）** |
| D | 0xA0D40 / 0xA1290 / 0xA16B0 / 0xA1AE0 | 1–2 次 | 未解析 | 无 | **BLOCKED（候选）** |
| E | 0x1AD3A0…0x1AF4E0（19 个） | 1–24 次 | 未解析（疑 snapshot/状态） | 无 | **BLOCKED（候选）** |

## 5. 结论

| 问题 | 回答 | 等级 |
|---|---|---|
| 客户端 Configstring body 读取器是否定位？ | **是，RVA 0xA2660**（+ 子过程 0xA2480） | **PROVEN** |
| 该读取器与服务端写入是否逐字段一致？ | **是**（count1=2B、13b 索引、11b/10b 计数、10b 值、A3=10/7/4/12b、索引上界 0x1DD7、区间 0..0x13 跳过 0x12） | **CROSS** |
| 是否**只有形状相似**？ | 否 —— 字段宽度、上界、区间检查、格式化串**全部**对应；非"形状匹配" | — |
| 读取 `0x04`/`0x06` 的外层分派器 | **未定位** | **BLOCKED** |
| `0xA2E50`（reliable payload 候选） | **另有其路径**，不与本链互证 | **BLOCKED** |