# 14 — 协议交叉验证 / PROTOCOL CROSS-VALIDATION

> 本文件的重点是**以实际字节为核心**。
> 标记：`CONFIRMED` / `PARTIAL` / `INFERRED` / `UNKNOWN` / `NOT_APPLICABLE`
> **纪律：** 不能把内部状态标记误判为线上字节；不能因为两边都有某个 `0x06` 就认定语义相同。

---

## 1. 协议对照矩阵（任务书 §5 指定格式）

| 协议类别 | OLD | 2697 | OL-mod | CoD4x | IW4x | 最终版 C-2697 |
|---|---|---|---|---|---|---|
| 连接建立 | `CONFIRMED` EV-Old-Connect | `PARTIAL` EV-2697-Gate | `PARTIAL` EV-R-OlMod | `PARTIAL`（无加密）EV-Netchan-CoD4x | `PARTIAL`（客户端）EV-R-IW4x-A | `UNKNOWN` EV-C-2697-NoRuntime |
| 可靠命令 | `CONFIRMED` EV-Old-Legacy（0x01+string） | `CONFIRMED` EV-2697-RC-Format（0x01/0x02） | `INFERRED` | `NOT_APPLICABLE`（不同实现） | `INFERRED` | `UNKNOWN`（分派 BLOCKED） |
| Gamestate | `CONFIRMED`（0x02，源码） | `CONFIRMED`（0x03，指令级） | `INFERRED` | `PARTIAL`（0x02/0x03 分离） | `PARTIAL` | `UNKNOWN`（`0x03` reader BLOCKED） |
| Configstrings | `CONFIRMED`（0x03） | `PARTIAL`（0x04，body bit 编码 BLOCKED） | `INFERRED` | `PARTIAL` | `PARTIAL` | `UNKNOWN` |
| Snapshot | `PARTIAL`（IW3 serializer） | `PARTIAL`（调用序列确认，帧边界 BLOCKED） | `INFERRED` | `PARTIAL` | `PARTIAL` | `UNKNOWN` |
| 实体状态 | `CONFIRMED`（MSG_WriteDeltaEntity） | `PARTIAL`（`codol_2697_delta.c`） | `INFERRED` | `PARTIAL` | `PARTIAL` | `UNKNOWN` |
| 用户命令 | `CONFIRMED`（clc 3 位分派） | `PARTIAL`（同族） | `INFERRED` | `PARTIAL`（clc） | `PARTIAL` | `UNKNOWN` |
| 断线与错误处理 | `CONFIRMED` | `PARTIAL` | `INFERRED` | `PARTIAL` | `PARTIAL` | `UNKNOWN` |

**解读：** `CoD4x`/`IW4x` 的 `PARTIAL` 指“其自有协议已确认，但它**不是** CODOL 协议”；不能读成“两者协议兼容”。`NOT_APPLICABLE` 表示该类别在对方项目里**不存在对应物**（可靠命令格式不同实现）。

---

## 2. 消息类型对照（含版本陷阱）

### 2.1 旧通道（OLD / 1113 / 2697 共有）

| 流 | opcode | 终止 | 证据 |
|---|---|---|---|
| snapshot | `0x00` | — | EV-2697-MsgTypes |
| serverCommand | `0x01` | — | EV-Old-Legacy |
| gamestate | `0x02` | `0x05` | EV-Old-Legacy |
| configstring | `0x03` | `0x05` | EV-Old-Legacy |
| EOF | `0x05` | — | EV-Netchan-Old |

### 2.2 2697 通道（NEW-only）

| 流 | opcode | 终止 | 证据 |
|---|---|---|---|
| gamestate | **`0x03`** | **`0x06`** | EV-2697-GS-Format |
| configstring | **`0x04`** | **`0x06`** | EV-2697-CS-Format |
| reliable command | **`0x02`**（结构化） | — | EV-2697-RC-Format |
| snapshot 内部标记 | `0x00` + 内部 `0x06` | 外层 `0x05`/`0x06` | EV-2697-Snap-Seq, EV-2697-Snap-Outer |
| EOF | **`0x06`** | — | EV-2697-MsgTypes |

> **版本陷阱（必须保留）：** 2697 gamestate 起始字节 `0x03` 与旧 configstring `0x03` 同值，但是**另一套 2697 上下文**，不可直接等同解释。

---

## 3. 逐字节比较：Reliable Command（本档案最强交叉点）

### 3.1 服务端写入（2697，VERIFIED 指令级）

```
_SV_WriteReliableCommand   RVA 0x8612E
  ret < 0  → Com_Error
  ret == 0 → 0x01 | long | NUL-terminated string
  ret > 0  → 0x02 | long | short(length) | data[length]
```

| 字段 | 写入点 | 宽度 | 端序 |
|---|---|---|---|
| opcode 0x02 | 0x8616B | u8 | — |
| long | 0x8617D | 4 B | LE |
| short(length) | 0x86189 | 2 B | LE |
| data | 0x8619F | length | — |
| opcode 0x01 | 0x861D0 | u8 | — |
| long | 0x861E2 | 4 B | LE |
| string | 0x861EE | NUL 结尾 | — |

边界常量：`0xCCC`、`0x7FFB`、`0xFF`、`0x3FB`、`0x3FC`；长度 1 拒绝；`O → 0x01`、`Z → 0x00`、大写两位 hex 合成字节（小写不接受）。

### 3.2 客户端读取候选（C-2697，VERIFIED 字段形状）

```
RVA 0xA2E50：读取 long(4) + short(2) + payload，并更新槽
             上限 0x3FC
             错误串 0xCB83E0 / 0xCB83E8 仅自引用
```

### 3.3 对照裁定

| 维度 | 服务端 | 客户端 | 裁定 |
|---|---|---|---|
| 字段顺序 | long + short + data | long + short + payload | **形状匹配 CONFIRMED** |
| 长度上限 | 0x3FC | 0x3FC | **一致 CONFIRMED** |
| opcode 0x02 前导 | 写 `0x02` | **未找到 `0x02` 比较/分派** | `BLOCKED` |
| 调用链 | 0x710B7/0x86DE0/0x873E4 → 0x8612E → 0x86B06 → 0x856B6 | 无调用者（E8/E9/指针/跳转表全 0 命中） | `BLOCKED` |
| 运行时字节 | 无抓包 | 无抓包 | `NOT-OBSERVED` |

**最终：字段形状 `CONFIRMED`；opcode 绑定 `INFERRED`；分派 `UNKNOWN`；互通 `NOT-OBSERVED`。**

### 3.4 官方黄金向量（服务端，VERIFIED）

| 向量 | 输入 | 预期输出 |
|---|---|---|
| RC-BIN-001 | seq 0x11223344; payload `10 20 30` | `02 44 33 22 11 03 00 10 20 30` |
| RC-TEXT-001 | seq 0x01020304; text `abc` | `01 04 03 02 01 61 62 63 00` |
| RC-BIN-EMPTY | seq 0; payload 空 | `02 00 00 00 00 00 00` |

来源：E3 RVA；**CONSTRUCTED**（由已确认字段规则构造，非原版抓包）。

---

## 4. 逐字节比较：Gamestate（2697）

| 字段 | 类型 | 证据等级 |
|---|---|---|
| opcode `0x03` | u8 | VERIFIED |
| version | long | VERIFIED（宽度）/ 语义 BLOCKED |
| map | NUL 字符串 | VERIFIED（形状） |
| `"mp"` | NUL 字符串 | VERIFIED |
| field4 | long | VERIFIED（宽度）/ 语义 BLOCKED |
| configstrings（`0x04…0x06`） | 嵌套 | VERIFIED（嵌套位置） |
| fieldC | long | VERIFIED（宽度）/ 语义 BLOCKED |
| field8 | long | VERIFIED（宽度）/ 语义 BLOCKED |
| 终止 `0x06` | u8 | VERIFIED |

GS-001 结构向量：`03 04 03 02 01 6d70_5f63_726f_7373_5f66_6972_65 00 6d70 00 44 33 22 11 <CF-001> 88 77 66 55 cc bb aa 99 06`（字段序 VERIFIED，state 语义 BLOCKED）。

**客户端侧：** 无 `0x03` 网络读取/switch（`gamestateupdate %d` 引用 0x56893/0xA2994；0xA2660 候选）→ `UNKNOWN`。

---

## 5. 逐字节比较：Snapshot 与 `0x06` 的双重身份

| 层 | 位置 | 值 | 语义 | 等级 |
|---|---|---|---|---|
| 内部子记录终止 | RVA 0xA4CAF（glass 之后） | `0x06` | 阶段终止（之后仍继续写 HUD/entities） | STATIC-INFERENCE |
| 外层消息终止 | RVA 0x87104（`_SV_EndClientSnapshot`） | `0x05`/`0x06` | 由 archive 激活选择 | VERIFIED |
| gamestate 尾 | RVA 0xA22F8 | `0x06` | 2697 通道 | VERIFIED |
| configstring 尾 | RVA 0xA0997 | `0x06` | 2697 通道 | VERIFIED |

**强制区分：** 内部 `0x06`（RVA 0xA4CAF）**不是**外层 EOF。它是子记录/阶段标记。任务书明确要求区分“内部状态标记”与“线上字节”，此处正是。

**客户端侧 `0x06`：** 未找到读取/终止判断/长度检查；`UNEXPECTED_EOF` 无直接代码引用 → `NOT-OBSERVED` / `BLOCKED`。

---

## 6. 黄金向量与独立实现交叉测试审计（任务书 §5.2 七问）

| 问 | 回答 |
|---|---|
| 1. 向量来自原始服务端/客户端字节，还是自编？ | **自编（CONSTRUCTED）**。由 E1–E3 字段规则构造，**不是**原版抓包。 |
| 2. 参考实现与被测实现是否独立？ | **不独立**。C# Codec 的字段定义来自同一份 E1–E3 反汇编结论。 |
| 3. 是否存在共用同一错误假设的风险？ | **存在，且高**。若 E3 的字段顺序理解错误，Codec 与服务端结论会**一起错**。 |
| 4. 输入输出是否字节级一致？ | Codec 自检通过；但这只证明“Codec ≡ 自己的字段定义”，不证明“Codec ≡ 真实客户端”。 |
| 5. 错误长度/截断/非法字段/未知命令是否合理？ | Codec 有边界测试（`0x3FC` 等）；**客户端行为未知**。 |
| 6. 解码后状态与编码前状态是否一致？ | 仅对构造向量成立。 |
| 7. 交叉测试只验证格式还是也验证语义？ | **只验证格式**。语义（字段名、状态效果）未验证。 |

**结论：** 现有黄金向量**不能**作为独立验证。它验证了“实现与规范自洽”，**未**验证“规范与真实客户端一致”。这是本档案最需要向读者强调的方法论结论。

---

## 7. 模块交叉点与分离点

### 7.1 真正交叉（有调用链边界）

| 交叉点 | 边界 | 传递 | 终止 |
|---|---|---|---|
| 2697 reliable writer → `_SV_SendMessageToClient` | 服务器发送边界 | 消息字节 | `_SV_Netchan_Transmit 0x856B6` |
| 2697 gamestate writer → `SV_WriteGameState` | 入世流程 | gamestate | 门控（可能 return 0） |
| CODOL_NetworkReceive → `SV_PacketEvent` | 记录层 → 应用层 | Msg | `CODOL_AssociationOpenDetailed` |
| clc 3 位分派 → `SV_UserMove`/`SV_ClientCommand` | 用户输入 | usercmd | 游戏 VM |

### 7.2 无交叉（分离点）

| 分离 | 类型 | 为什么分离 |
|---|---|---|
| 2697 writer ↔ C-2697 `0xA2E50` | **分析链未闭合** | 无分派、无字节、无运行时 |
| CODOL 握手 ↔ CoD4x/IW4x | **设计分层** | 对方没有 cookie+ECDH |
| 平台层（TCLS/IIPS/TenProxy）↔ 游戏通道 | **设计分层** | 平台层是启动/认证，不经游戏 socket |
| OLMOD 插件 ↔ 2697 门控 | **版本差异** | 3.3.3.3 vs 2.6.9.7 |
| REF_LOBBY_KIT ↔ 自研 CODOLServer | **独立实现** | 两个不同大厅服务端 |

### 7.3 模块交叉图

```
[C-2697 socket/recv] --CALL--> [0x602441/0x6029BE/... recv]
        │
        ├─ ? (BLOCKED) ──> [0xA2E50 long+short+payload]  ← 形状匹配
        │                       ▲
        │                       │ 无分派边（UNKNOWN）
        │                       │
[2697 _SV_WriteReliableCommand 0x8612E] --CALL--> [_SV_SendMessageToClient 0x86B06] --CALL--> [_SV_Netchan_Transmit 0x856B6]
                                                                                                   │ PROTO? (NOT-OBSERVED)
                                                                                                   ▼
                                                                                         [UDP 战斗通道]
```

**注：** 图中 `PROTO?` 边是**未闭合**的，不能画成实线。

---

## 8. 协议交叉验证结论

1. **最强交叉点**：reliable command 的**负载形状**（long+short+data，上限 0x3FC）。**服务端 VERIFIED，客户端形状 VERIFIED，绑定 BLOCKED。**
2. **最弱交叉点**：客户端 `0x06`（EOF/EOS）——服务端写入多处以 `0x06`，客户端**零**证据。
3. **必须区分内部/外层 `0x06`**，且必须区分“旧通道 opcode”与“2697 通道 opcode”。
4. **2697 与 Old/1113 是同一家族的消息层升级**：旧通道 opcode 保留，新增 2697 通道。
5. **跨项目协议可比性**：与 CoD4x/IW4x 只在**引擎骨架层**可比；在**握手/记录/加密层决定性不同**（`DISTINCT`）。
6. **独立验证缺口**：现有黄金向量非独立来源，不能增加跨端置信度。
---

# === 追加：第二轮后的矩阵状态（UPDATE-2, 2026-10-12） ===

## 连接建立 / 传输层（服务端侧已闭合）

| 项 | 状态 | 证据 |
|---|---|---|
| 2697 netchan 常量（1162 / 128 / 掩码 / 魔数） | **CONFIRMED** | EV-2697-NetchanConst |
| 2697 reliable `0x02`/`0x01` 选择条件 | **CONFIRMED**（指令级） | EV-2697-RCSelect |
| 2697 reliable 门控（archive + `CODOL2697_PROFILE_WIRE`） | **CONFIRMED**（指令级） | EV-2697-RCGate2 |
| 2697 注册格式链 | **CONFIRMED**（指令级） | EV-2697-RegFmt3 |
| 2697 内部 `0x06` ≠ 外层 EOF | **CONFIRMED** | EV-2697-SnapshotOrder |
| 客户端消费（0x02/0x06/gamestate/configstring/snapshot） | **BLOCKED**（搜索空间不完备） | EV-C2697-DataGap / EV-C2697-Tvm0Noise |

## 逐字节比较矩阵（更新）

| 协议类别 | OLD | 2697 | OL-mod | CoD4x | IW4x | 最终版 C-2697 |
|---|---|---|---|---|---|---|
| 连接建立 | `CONFIRMED` | `CONFIRMED`（常量级） | `PARTIAL` | `PARTIAL` | `PARTIAL` | `UNKNOWN` |
| 可靠命令 | `CONFIRMED` | `CONFIRMED`（选择条件指令级） | `INFERRED` | `NOT_APPLICABLE` | `INFERRED` | `UNKNOWN` |
| Gamestate | `CONFIRMED` | `CONFIRMED`（字段序） | `INFERRED` | `PARTIAL` | `PARTIAL` | `UNKNOWN` |
| Configstrings | `CONFIRMED` | `PARTIAL`（body BLOCKED） | `INFERRED` | `PARTIAL` | `PARTIAL` | `UNKNOWN` |
| Snapshot | `PARTIAL` | `PARTIAL`（帧边界 BLOCKED） | `INFERRED` | `PARTIAL` | `PARTIAL` | `UNKNOWN` |
| 实体状态 | `CONFIRMED` | `PARTIAL` | `INFERRED` | `PARTIAL` | `PARTIAL` | `UNKNOWN` |
| 用户命令 | `CONFIRMED` | `PARTIAL` | `INFERRED` | `PARTIAL` | `PARTIAL` | `UNKNOWN` |
| 断线/错误 | `CONFIRMED` | `PARTIAL` | `INFERRED` | `PARTIAL` | `PARTIAL` | `UNKNOWN` |

**注意：** 客户端列仍全部为 `UNKNOWN`；本轮**未**产生任何客户端侧闭合证据，仅**收窄**了缺失原因（`.data` 99.86% 缺失；`.tvm0` 原始字节扫描无效）。
