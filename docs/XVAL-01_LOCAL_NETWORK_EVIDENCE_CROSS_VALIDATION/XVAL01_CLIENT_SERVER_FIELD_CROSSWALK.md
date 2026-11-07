# XVAL01_CLIENT_SERVER_FIELD_CROSSWALK — 客户端/服务端字段对照

> 对象：目标服务端 = 2697 `codol_dedrun.exe`（`80816711…`，无源码，指令级）；目标客户端 = 2.6.9.7 `codoMP_client_shipRetail.exe`（`35375404…`）/ 恢复镜像 `codol24b4ef25…`。
> 纪律：**服务端能写 ≠ 客户端能读**。每一行分别标注两侧证据等级；只有两侧**都有指令级证据**才可标 `PROVEN(两侧)`。
> 地址口径 RVA（VA = RVA + 0x400000）。`✔`=本任务活体复核（见 `_data\INDEPENDENT_VERIFICATION_LOG.md`）。

---

## 0. 分层总表（先看这张）

| 协议项 | 服务端 writer 证据 | 客户端 reader 证据 | 字段级裁定 | 绑定/分派 |
|---|---|---|---|---|
| Reliable 0x01/0x02 载荷 | 指令级 `PROVEN`（0x8612E） | 指令级**形状** `PROVEN`（0xA2E50） | **一致**（长+短+载荷，上限 0x3FC） | **BLOCKED**（无 0x02→0xA2E50） |
| Gamestate 顶层 0x03 | 指令级 `PROVEN`（0xA21B8） | 仅 demo 消费者，**冲突** | **REFUTED（demo）**；实时 `BLOCKED` | BLOCKED |
| Configstring 0x04 body | 指令级 `PROVEN`（0xA0468） | 指令级 `PROVEN`（0xA2660） | **逐字段一致** ✔ | 外层 0x04 值级 `BLOCKED` |
| Configstring 终止 0x06 | 指令级 `PROVEN`（0xA0997） | **无** | 服务端单侧 | BLOCKED |
| Snapshot | 调用序列 `PROVEN`（0xA4860） | **无** | 服务端单侧 | BLOCKED |
| Snapshot 外层 0x05/0x06 | 指令级 `PROVEN`（0x87104） | **无** | 服务端单侧 | BLOCKED |

**一句话：** 唯一"两侧字段级一致"的是 **configstring body 的内部布局**；其余全部停在服务端单侧或更深处的分派绑定。

---

## 1. Reliable Command（0x01 / 0x02）

服务端 `_SV_WriteReliableCommand` RVA `0x8612E`（`2697_SA 04 §2.3`、`E-14`）：

```
ret < 0   → Com_Error
ret == 0  → [0x01][long seq][NUL-terminated string]
ret > 0   → [0x02][long seq][short length][data[length]]
```

| 字段 | 服务端写入点 | 宽度/端序 | 客户端读取点 | 宽度/端序 | 裁定 |
|---|---|---|---|---|---|
| opcode | 0x8616B(0x02) / 0x861D0(0x01) | u8 | **未定位** | — | **BLOCKED** |
| seq | 0x8617D / 0x861E2 | long, LE | 0xA2E50 族 读 4B | long, LE | 形状一致 |
| length | 0x86189 | short, LE | 读 2B（0x3FC 上限） | short, LE | **一致** |
| data | 0x8619F | length B | payload | length B | 形状一致 |

- **已证明：** 载荷形状（long+short+data）与上限 `0x3FC`。边界常量 `0xCCC/0x7FFB/0xFF/0x3FB/0x3FC`；`O`→0x01、`Z`→0x00、大写两位 hex 合成字节（小写不接受）。
- **未证明：** opcode `0x02` 的**客户端读取点**与**到 0xA2E50 的分派**。E-06/E-13/E-14/E-19 的 E8/绝对 VA/裸 RVA/跳转表搜索**全部 0 命中**，且搜索空间结构不完备（见 §6）。
- **不得升级：** 不可写"客户端已支持 0x02"。

## 2. Gamestate（0x03）

服务端 `_CODOL2697_WriteGamestate` RVA `0xA21B8`：

```
0x03 | long state[0] | map\0 | "mp"\0 | long state+8 | [configstrings 0x04..] | long state+0xC | long state+0x8 | 0x06
```

| 字段 | 服务端 | 客户端 | 裁定 |
|---|---|---|---|
| opcode 0x03 | 0xA224C `WriteByte(3)` | 0x350170 表项 3 → 0x34FD80(1)（**demo**） | 冲突 |
| 版本/序号(long) | 0xA225A | demo 读 4B（对齐） | 形状似但路径无关 |
| 地图名(cstring) | 0xA2269 | demo 读到的是 4B 载荷 → **不匹配** | **REFUTED** |
| "mp"(cstring) | 0xA2279 | 无对应 | REFUTED |
| field4(long) | 0xA2288 | 无对应 | 差异 |
| configstrings 子帧 | 0xA22C1 call 0xA0468 | 无 | BLOCKED |
| fieldC / field8 (long×2) | 0xA22F8 前 | 无 | BLOCKED |
| 终止 0x06 | 0xA22F8 | 无 | BLOCKED |

- 字段**语义**（state[0]/+4/+8/+0xC 的含义）全部 BLOCKED；服务端字段**宽度与顺序** PROVEN。
- 已定位的 0x03 消费者**只属于 demo 路径**（`0x8F1D0` 有 demo 状态门 `[0x1BBBCFC]∈[7,9)`，上行 `0x34E7C0`=`cl_demo_jumptostart`）；**实时消费者未定位**。

## 3. Configstring（0x04 … 0x06）——唯一两侧闭合区

服务端 `_CODOL2697_WriteConfigstrings` RVA `0xA0468`；客户端 consumer RVA `0xA2660`（入口）→ `0xA2975`（`ret`）。

| 字段 | 服务端（写入） | 客户端（读取） | 位宽/端序 | 裁定 |
|---|---|---|---|---|
| opcode `0x04` | 0xA07F8 `WriteByte(4)` | 外层 `0x352FA1` +1 字节（**无值比较**） | 8 bit | 位置 INFERRED；值级 **BLOCKED** |
| `count1` | 0xA0807 `WriteShort` | 0xA26AF `push 2` → 0x1AC1D0 → `movsx word` ✔ | **2 B / 16 bit LE** | **PROVEN（两侧）** ✔ |
| 索引增量 | 0xA0400 `WriteIndexDelta` | 0xA26E2 call 0x44C8C0；否则 0xA26F4 `push 0xD` ✔ | 连续=1 bit；否则 1+13 bit | **PROVEN（两侧）** ✔ |
| A1 字符串 | 0x99651 `strlen+1` WriteData | 0xA25F0 NUL 扫描 | strlen+1 字节（含 NUL） | **PROVEN（两侧）** |
| A1 长度上限 | cmp 0x1FFF | （读侧隐含） | 8191 | PROVEN（服务端） |
| A1 黑名单 | 0x25 / 0x92 | — | — | PROVEN（服务端） |
| A2 段计数 | 0xA084D `mov [esp+8],0xB` ✔ | 0xA2765 `push 0xB` ✔ | **11 bit** | **PROVEN（两侧）** ✔（E-08 旧记 10 bit 已更正） |
| A2 条目值 | 0xA088A `mov [esp+8],0xA` ✔ | 0xA27D7 `push 0xA` ✔ | **10 bit** | **PROVEN（两侧）** ✔ |
| A3 段计数 | 0xA08AD `mov [esp+8],0xA` ✔ | 0xA2879 `push 0xA` | 10 bit | **PROVEN（两侧）** |
| A3 字段 | 0x090B(10)/0x922(7)/0x939(4)/0x950(n×12) ✔ | 子过程 0xA2480 `push 10/7/4` | 10/7/4 + n×12 | **PROVEN（两侧）** |
| 索引上限 | cmp `0x1DD6` / sentinel 0x1DD7 | 0xA2702 `cmp edi,0x1DD7` ✔ | — | **PROVEN（两侧）** ✔ |
| 合法索引区间 | 0..0x13 跳过 0x12 | 0xA2728 `cmp cl,0x14`/`cmp cl,0x12` ✔ | — | **PROVEN（两侧）** ✔ |
| 终止 `0x06` | 0xA0997 `WriteByte(6)` | **0xA2660 循环结束即 ret，无读取** | 8 bit | 服务端 PROVEN；客户端 **BLOCKED** |
| 字节对齐 | `MSG_WriteBits` 重同步 bitpos=used*8（0x9960A） | 读取端无等价队列语义 | — | 服务端 PROVEN；客户端 BLOCKED |

**关键更正（本任务独立复核）：** A2 段计数 **两侧均为 11 bit**。E-08 `04` 曾记服务端为 10 bit，`E-14 04 §3` 已修订；本任务直接反汇编两侧（服务端 0x0A084D=0xB、客户端 0xA2765=0xB）确认。**历史错误保留在 E-08 原文，不删除。**

## 4. Snapshot

服务端 `_CODOL2697_WriteSnapshot` RVA `0xA4FA0` → `_CODOL2697_WriteSnapshotReached` RVA `0xA4860`：`entities → clients → glass(内部 0x06 @0xA4CAF) → HUD → 第二遍 → 区域复制(0x728/0x2C38/count×0x1F8/count×0x13C/count×0x5C)`。

| 项 | 服务端 | 客户端 | 裁定 |
|---|---|---|---|
| 调用序列 | PROVEN（0xA4860） | 无 | 服务端单侧 |
| 内部 0x06（glass 后） | PROVEN（0xA4CAF，其后继续写） | 无 | **不是** EOF（服务端结构证据） |
| 外层终止 0x05/0x06 | PROVEN（0x87104 依 archives 选择） | 无 | 服务端单侧 |
| delta 基准/实体字段 | 部分（0x728 等区域尺寸） | 候选 0x6E060/0x6D340 未闭合 | **BLOCKED** |
| 客户端 delta 解码 | — | 未闭合 | **BLOCKED** |

## 5. 会话/Demonware（平台层 vs 游戏层）

| 项 | 证据 | 层 | 裁定 |
|---|---|---|---|
| 平台/预订帧（service 21/5、6/14） | `_combat_next011` 44 帧，HMAC OK，`accepted_present=false` | **平台** | PROVEN（分层） |
| Demonware 帧读取器 0x6ABBC0（4B 长度前缀） | E-19（单源） | 平台/后端 | 形状 PROVEN（单源） |
| 类型码 1/2 → 游戏 opcode | E-19 §2 | — | **REFUTED（不属同一编码空间）** |
| 04 字段板载通道认证 | REF_LOBBY_KIT（进大厅） | 大厅 | PROVEN（仅大厅） |
| 认证成功 ⇒ 进战斗 | `BATTLE_RX=0` | — | **REFUTED** |

## 6. 为何大量客户端字段停在 BLOCKED（结构原因，非工具缺陷）

| 限制 | 量化 | 后果 |
|---|---|---|
| `.data` 未恢复 | VSize 218 MB vs RawSize 300,544 B = **99.86% 缺失**（✔ V-02） | 候选 vtable/分派表可能落在缺失区 |
| 末节 `.tp3` 未恢复 | 打包客户端末节 VSize ≈ 52.5 MB | 不能作强否定 |
| `.tvm0` 未解码 | E8 可靠性 0.0%（29,474 字节中 0 落入函数入口） | 原始字节扫描无效，须先解码 |
| 无运行时 dump | 全盘不存在 | 恢复镜像 ≡ 运行时映射无法证明 |

**结论：** 客户端项的 `BLOCKED` 是"搜索空间不完备"，不是"搜索了没有"。

---

## 7. 逐字段结论汇总（供实现方直接引用）

| 可立即按已证字段实现（服务端自洽 / 离线向量） | 必须等客户端证据 |
|---|---|
| Reliable `0x01`/`0x02` 编码（字段序 + 0x3FC 上限） | `0x02`→客户端分派 |
| Gamestate 顶层字段序与宽度 | 客户端实时 `0x03` 消费者与字段语义 |
| Configstring `0x04` body（count1/索引/A1/A2/A3 全部位宽） | 外层 `0x04` 值级识别、`0x06` 读取/对齐 |
| Snapshot 服务端调用序列与内部 0x06 语义 | 客户端 snapshot delta 解码与帧边界 |

> **不得**把"可编码"当作"可互操作"。互通验收仍取决于 `XVAL01_REMAINING_BLOCKERS.md` 中的最小证据。
