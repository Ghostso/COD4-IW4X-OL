# SNAPSHOT_FORMAT_AND_DELTA — snapshot 核心阻塞调查

**分析对象：** `image_best.bin`，`17cef6e0…`
**地址约定：** `file_offset = RVA = VA - 0x400000`
**方法：** 跳表枚举 + 索引表字节统计 + `E8` 调用链解析 + 序言边界恢复。**无插桩。**

---

## 1. 结论摘要

| 项 | 状态 |
|---|---|
| 增量字段**类型分派器**存在 | **CONFIRMED**（RVA `0x5F830`） |
| 两套类型索引表的**规模与默认项** | **CONFIRMED**（见 §2） |
| 分派器调用链（至 `0x1FF820`） | **CONFIRMED** |
| snapshot **帧起止边界** | **UNKNOWN** |
| **delta 基线**（首帧/历史缓存/指针） | **UNKNOWN** |
| 实体列表**编码与终止条件** | **UNKNOWN** |
| 实体**新增/更新/删除**表示 | **UNKNOWN** |
| entity number ↔ 客户端实体表索引 | **UNKNOWN** |
| 丢失基线 / 无效帧 / 序号异常处理 | **UNKNOWN** |
| 玩家状态与实体状态是否分开解码 | **UNKNOWN** |

> **纪律：** 本轮**不**推测任何字段位宽，**不**用冻结服务器的 legacy 位流冒充目标格式。§2 的表是**唯一**可直接落到目标二进制的编码结构证据，其**字段语义**仍为 `UNKNOWN`。

---

## 2. 增量字段类型分派器（本轮最强的新证据）

### 2.1 函数入口

```
RVA 0005F830  55                 push ebp
RVA 0005F831  8bec               mov  ebp, esp
RVA 0005F833  83ec18             sub  esp, 0x18
RVA 0005F836  8b15583b2c08       mov  edx, [0x82c3b58]          ; 本地客户端索引
RVA 0005F83C  d94520             fld  dword [ebp+0x20]          ; 参数：3 个 float
RVA 0005F83F  8b149588d1c101     mov  edx, [edx*4 + 0x1c1d188]  ; 客户端表
RVA 0005F849  d94524             fld  dword [ebp+0x24]
RVA 0005F84C  8b4554             mov  eax, [ebp+0x54]           ; 参数：类型索引
RVA 0005F84F  8b4d50             mov  ecx, [ebp+0x50]
RVA 0005F855  d94528             fld  dword [ebp+0x28]
RVA 0005F858  81f27ac9b2fb       xor  edx, 0xfbb2c97a           ; 解密客户端对象
RVA 0005F85E  8955fc             mov  [ebp-4], edx
RVA 0005F861  d95df0             fstp dword [ebp-0x10]
RVA 0005F867  d9452c             fld  dword [ebp+0x2c]          ; 参数：第 4 个 float
RVA 0005F86A  8855f8             mov  byte [ebp-8], dl          ; 参数：byte
```

**签名（`INFERRED`）**：`(clientObj, float a, float b, float c, byte d, ..., 0x50/0x54 = 类型索引)`，
`this` 为 `ecx`（客户端对象，由 `[0x82c3b58]` 经 `[+0x1c1d188]` 表 XOR `0xfbb2c97a` 取得）。

> `0x82c3b58` / `[edx*4+0x1c1d188]` / `xor 0xfbb2c97a` 与 `0x6D060` 的函数头部**完全一致**
> ⇒ 两者操作**同一客户端对象**。这是一个**跨函数一致性证据**（`CONFIRMED`）。

### 2.2 两张类型索引表（逐字节统计）

| 表 | 索引表 RVA | 索引范围 | 目标表 RVA | 处理分支数 | **默认项** | 默认项占比 |
|---|---|---|---|---|---:|---:|
| **A** | `0x460550` | `0..0x139`（314） | `0x46040C` | 81（`0x00..0x50`） | **`0x50`** | 223/314 |
| **B** | `0x4606E4` | `0..0x87`（136） | `0x46068C` | 22（`0x00..0x15`） | **`0x15`** | 115/136 |

**表 A 原始字节（节选，完整见 `evidence\dump_typetables.out.txt`）：**
```
+0x000: 00 01 50 50 50 50 50 50 50 50 50 50 50 50 50 02 50 50 ...
+0x050: 50 50 05 06 50 50 50 50 50 50 07 08 09 0a 0b 0c 0d 50 ...
+0x0A0: 30 31 50 32 33 34 34 34 34 34 35 36 50 50 50 50 50 50 ...
+0x110: 45 46 50 50 47 48 38 50 50 50 50 49 50 50 50 50 4a 50 ...
```
**表 B 原始字节（节选）：**
```
+0x000: 00 01 02 03 04 15 05 06 07 08 09 0a 0b 15 15 15 15 15 ...
+0x070: 15 15 15 15 15 15 15 15 0c 0d 0e 15 0f 10 11 12 15 13 15 14
```

**已证**：索引 → 处理分支的映射是**字节表 + 二次跳表**两层结构（`movzx` + `jmp [reg*4+tbl]`），
且表 A 的门是 `cmp idx, 0x139; ja`、表 B 的门是 `cmp idx, 0x87; ja`。
**未证**：这些索引对应哪些逻辑字段、各分支读取多少位、以及索引来自位流的哪种编码。

### 2.3 分派器调用链

```
0x20059B → 0x1FF820 → (0x1FFB88) → 0x208380 → (0x208432) → 0x5F830
0x6010A / 0x207D63 / 0x207EFC → 0x5F730
```

| 调用点 RVA | 所在函数入口 |
|---|---|
| `0x208432` | `0x208380` |
| `0x1FFB88` | `0x1FF820` |
| `0x20059B` | **未定位** |
| `0x6010A` / `0x207D63` / `0x207EFC` | **未定位** |

`0x208380` 头部同样含 `mov edx,[0x82c3b58]; mov eax,[edx*4+0x1c1d188]; xor eax,0xfbb2c97a`
⇒ 与 `0x5F830`、`0x6D060` **同一客户端对象**（`CONFIRMED`）。

`0x1FF820` 头部读取 `[ebx+0xa4]` / `[ebx+0xa0]` / `[ebx+0xf0]` / `[ecx+0xcc]`
⇒ 形态上与"实体/玩家快照字段打包"相符（**`INFERRED`**，未证）。

证据：`evidence\delta_chain_context.out.txt`、`evidence\locate_delta_dispatcher.out.txt`

---

## 3. snapshot 帧边界与 delta 基线 — 仍未闭合

### 3.1 已排除的方向

| 排除项 | 依据 |
|---|---|
| TASK-009 的 `parseSnapshot 0x46D170` | 该 RVA 在本镜像**非函数入口**（`BATTLE_RX_CALLCHAIN.md` §1） |
| TASK-009 的 `parsePacketEntities/Clients/Aux` | 同上，全部非入口 |
| TASK-009 的 `readDeltaField/Entity/Index` | 同上，全部非入口 |
| TASK-009 的 `readBit 0x400C370` | **超出文件范围** |
| 常数整体位移 | 最佳位移仅 7/18 命中（`evidence\delta_hypothesis.out.txt`） |

### 3.2 仍未闭合的具体缺口

| 缺口 | 说明 |
|---|---|
| 帧起点 | 未定位读取"命令字节/帧类型"的分派点（269 个 6 项跳表无一绑定） |
| 帧终点 | 未找到显式终止符比较（`5`/`6` 等）与 packet 语境的绑定 |
| server time | 未定位 `[obj+0x30..0x44]` 之外的 serverTime 字段消费点 |
| 消息序号 | 未定位序号读取与回绕比较 |
| delta 基线来源 | 未定位"上一帧指针/历史缓存"的取用点 |
| 实体列表终止 | 未定位实体计数或哨兵值 |
| 实体增删 | 未定位删除分支或"新实体"分支 |
| entityId → 表索引 | 未定位乘/移位换算与边界检查 |
| 序号异常 | 未定位拒绝分支（丢帧/过期） |
| 玩家状态 vs 实体状态 | 未判定是否两条独立路径 |

**`0x1FF820` 的 `[ebx+0xa0]/[ebx+0xa4]/[ebx+0xf0]` 是当前最有价值的下一步切入点**
（它在 `0x5F830` 的调用链上，且已确认操作同一客户端对象）。

---

## 4. netchan 层 — 候选登记（未绑定）

| 位点 RVA | 含常量 | 说明 |
|---|---|---|
| `0x1AC178` | `[esp+0x44] = 0x20000`（最大分片消息） | 邻近 `0x1AD2D0` 多处调用，形态像缓冲/分片管理 |
| `0x3E5960` | `[esp+0x1154] = 6`，栈帧 `0x1148+` | 大栈帧 + `0xDB4530` 字串引用 |
| `0x3E5A57` | `[esp+0x1154] = ebx`（清零） | 同族 |
| `0x5C2034` | `[esi+0x54] = 0x11` 等结构初始化 | 明显是结构体常量表，**非** netchan |

**判定：`netchanProcess` 真实入口 = `UNKNOWN`。** 上述四处均**未**能通过字符串/调用证据与战斗接收链绑定。

**已登记的 netchan 常量事实（仅作参考，不绑定实现）：**
`0x1FFFFFFF` 序列掩码在镜像中出现 46 次；`1154`（分片尺寸）出现 4 次（上表）；`0x20000`（最大分片消息）出现 7792 次（过于普遍，无区分力）。

---

## 5. 与冻结服务器的差距（只读对照）

| 冻结服务器 | 目标客户端 | 判定 |
|---|---|---|
| `MotionSnapshot.BuildCore`：`ack(u32) + 0x00 + serverTime(u32) + first?{0,8}:{1,4} + 位域 0,1,220` | 目标镜像**无对应证据** | **OLD PROTOCOL**（标注"移植自 REF_LOBBY_KIT / C-3333"） |
| `ExpectedIndexOrder` 29 项硬编码字段序列 | 目标镜像**未证** | **暂缓** |
| `PumpSnapshot`：`u32 netchan_seq + body`，XOR 自 wire offset 8 | 目标镜像**未证** | **暂缓** |
| `s.InputBaselines[seq]` 作为 usercmd 基线 | 本轮目标侧**未定位**基线机制 | **暂缓** |
| `Codol2697Protocol`：`enable_experimental_snapshot2697 = 0`，源码注明"帧边界/delta 基准仍是 BLOCKED" | 本轮**同样未闭合** | **一致（均为 BLOCKED）** |
| `ClientLogic.cs:400` `throw new TruncatedException("Unknown snapshot baseline " + ack)` | 目标镜像**未证** | **暂缓**（但该"未知基线拒绝"语义与目标可能的序号/基线校验方向一致，可作**候选行为**登记） |

**判定：** snapshot 层，冻结服务器的**所有**具体实现均**无本目标证据**。
因此 `SERVER_IMPLEMENTATION_GAP.tsv` 中 snapshot 相关行全部归入"暂缓实现（目标证据不足）"，
唯一例外是"未知基线应拒绝"这一**语义方向**可登记为候选。

---

## 6. 未闭合项汇总（**不得推测**）

| 项 | 状态 |
|---|---|
| snapshot 帧起止边界 | `UNKNOWN` |
| delta 基线 | `UNKNOWN` |
| 实体列表编码与终止 | `UNKNOWN` |
| 实体增删表示 | `UNKNOWN` |
| entityId ↔ 表索引 | `UNKNOWN` |
| 序号/丢包/基线异常处理 | `UNKNOWN` |
| 玩家状态与实体状态是否分离 | `UNKNOWN` |
| 类型表 A/B 各分支的位宽 | `UNKNOWN` |
| 类型表 A/B 索引的逻辑语义 | `UNKNOWN` |
| `netchanProcess` 真实入口 | `UNKNOWN` |
