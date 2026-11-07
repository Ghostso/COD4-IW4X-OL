# 07 — E-10 总裁定 / VERDICT

> 只读静态分析。未启动游戏、未注入、未读进程内存、未修改样本。

---

## 1. 五项完成标准逐条裁定

| # | 完成标准 | 裁定 | 依据 |
|---|---|---|---|
| 1 | 外层 `0x04` 分派 | **BLOCKED** | 无客户端 `cmp 4`；仅有“进入 body 前 +1 字节”强 INFERRED（`03`） |
| 2 | `0x06` 读取路径 | **BLOCKED** | 客户端读取点未定位（`04`） |
| 3 | `0x06` 位宽（8 bit） | **BLOCKED** | 服务端 `WriteByte` 为 1 字节（DIRECT）；客户端无读取证据 |
| 4 | `0x06` 字节对齐 | **BLOCKED** | 起始 bitpos 输入相关（44/53/61/72/129…）；客户端对齐行为未知 |
| 5 | `0x06` 终止语义 | **BLOCKED** | 服务端写点位于 body 之后；客户端未见退出/终止分支 |
| 6 | Configstring body 字段顺序 | **按字段独立裁定** | F2–F12 PROVEN；F1/F13/F14 BLOCKED（`06`） |

## 2. 任务 A：调用链闭合

- `0xA2660` 直接调用点 **3 个**（全量复核）：`0x3514F0`（调用）、`0x352FA7`、`0x352FB4`（尾跳转）。
- 分布：`0x3512A0` ×1、`0x352F80` ×2。
- **更正 E-09：** 后两处在 `0x352F80`，不是 `0x352E80`。
- 找到客户端 9 项跳转表 `0x354100`（case 0..8）与选择器 `0x3547D0`。
- Configstring body 走 **case 6**（4 字节长度 + 载荷 + 跳过 1 字节），**不是 case 4**。
- 外层 `0x04` 的值级分派：**BLOCKED**。
- `.tvm0`：不在本链任何 `call/jmp` 边上，按停止条件不深入。

## 3. 任务 B：0x06 终止语义

- 服务端 Configstring 尾 `WriteByte(6)` @ `0xA0997`：**DIRECT**。
- 客户端 `0xA2660` 内**没有**读取 `0x06` 的指令。
- 四类 `0x06` 上下文（Configstring / Gamestate / Snapshot 内 / 外层选择器）分别登记，**未跨层合并**。
- 服务端位记账：`bitpos%8==0 ⇒ bitpos=used*8`；`WriteData`/`WriteLenStr` 不更新 bitpos。
- 累计位模型：`0x06` 起始可为 44/53/61/72/129…，**不保证字节对齐**。
- 读取端行为：**BLOCKED**。

## 4. 任务 C：字段级一致性

| 字段 | 裁定 |
|---|---|
| count1 2 字节 | PROVEN |
| 索引连续性标志 + 13-bit 绝对索引 | PROVEN |
| A1 字符串 | PROVEN |
| A2 计数与条目 | PROVEN |
| A3 计数与子过程 `0xA2480` | PROVEN |
| 索引上限及跳过规则 | PROVEN |
| 外层 `0x04` | BLOCKED（位置 CROSS-INFERRED，值比较未证） |
| 候选 `0x06` | BLOCKED |

## 5. 全局纪律声明

- **未**把局部字段一致升级为整条消息互操作已证实。
- **未**用构造向量冒充 Golden。
- **未**跨消息层合并 `0x06` 候选。
- **未**在 `.tvm0` 混淆区扩大搜索。

## 6. 停止条件与最小证据缺口

| ID | 缺口 | 最小新增证据 | 授权 |
|---|---|---|---|
| G-04-1 | 外层 `0x04` 分派 | `0x3547D0` 键的生产者/取值域，或 case 6 键的常量比较 | 否 |
| G-04-2 | 跳过字节内容 | `0x352F80` 入口前该字节的写入者 | 否 |
| G-06-1 | `0x06` 客户端读取点 | `0xA2660` 返回后调用者的 1 字节常量比较 | 否 |
| G-06-2/3 | 对齐与终止 | 读取原语的 bitpos/字节游标使用与退出分支 | 否 |
| G-06-4 | 端到端兼容 | 原始帧字节 | **是** |

## 7. 交付物清单

| 文件 | 状态 |
|---|---|
| `01_A2660_CALLER_INVENTORY.md` | ✔ |
| `02_OUTER_DISPATCH_CALLGRAPH.md` | ✔ |
| `03_OPCODE_04_DISPATCH_VERDICT.md` | ✔ |
| `04_TERMINATOR_06_READ_PATH.md` | ✔ |
| `05_BIT_ALIGNMENT_RECONSTRUCTION.md` | ✔ |
| `06_CLIENT_SERVER_CONFIGSTRING_MATRIX.md` | ✔ |
| `07_E10_VERDICT.md` | ✔ |
| `SHA256SUMS.txt` | ✔ |
