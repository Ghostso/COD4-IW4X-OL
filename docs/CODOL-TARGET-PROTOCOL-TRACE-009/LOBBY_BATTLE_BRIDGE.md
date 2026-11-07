# LOBBY_BATTLE_BRIDGE — C 层：大厅与战斗交接协议及状态关联

**目标版本：** CODOL 3.19.26.22 / Build 1649370
**分析对象：** `COD OL\codoMP_client_shipRetail.exe`（`36997674…`）
**性质：** 只读静态追踪。
**独立建账声明：** 本节**既不并入 A 层，也不并入 B 层**。它只描述「大厅输出如何变成战斗输入」。

---

## 1. 交接链总览（跨协议图）

```
┌─────────────── A 层（大厅 / Demonware 控制面）───────────────┐
│ 匹配对象 matching                                            │
│   [this+0x278] = BOOKING_PENDING                             │
│   reservation array @ this+0x75D8 (stride 0x238)             │
│   index @ this+0xE360 ; A/B @ this+0x3A048 / 0x3A04C         │
│   构造器 0x0062F7E0  ->  "mmbook <A> <B> ..."                │
└───────────────────────────┬──────────────────────────────────┘
                            │ service 0x06 / task 14
┌───────────────────────────▼──────────────────────────────────┐
│ 服务端预约应答  accepted blob                                │
│   13 08 | 13 00 00 00 | 0f 00 00 00 | "mmbook accepted"      │
│   (外层 u32(15) 前缀 + 15B 文本, 无 NUL)                     │
└───────────────────────────┬──────────────────────────────────┘
                            │ 通道 = UNKNOWN（见 §4）
┌───────────────────────────▼──────────────────────────────────┐
│ 客户端 accepted 解析器 0x00632680 (ret 0x14)                 │
│   守卫: [esi+0x278] != 0                                     │
│   回显: [ebp+8]==A, [ebp+0xC]==B                             │
│   成功: 0x00632745 写 [esp+0x28] = 1                         │
│                  ↓                                           │
│        [matching+0x288]  预约闩锁                            │
│        unique consumer 0x00634402                            │
│                  ↓                                           │
│        mmstart 构造器 0x00632070                             │
│        "mmstart sv_resetServer; 2486 ..."                    │
└───────────────────────────┬──────────────────────────────────┘
                            │ mmstart 命令（发送 = NOT_OBSERVED）
┌───────────────────────────▼──────────────────────────────────┐
│ B 层（战斗 / UDP + netchan）                                 │
│   getchallenge -> connect -> stats -> heartbeat              │
│   netchanProcess 0x005A5960 -> parseServerMessage 0x0046E6A0 │
│   BATTLE_28960 = NOT_OBSERVED                                │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. 交接候选字段（逐项证据链）

对每个候选交接字段，按任务要求建立五段链：
`大厅生产位置 → 序列化/传递位置 → 客户端保存或转换位置 → 战斗连接消费位置 → 服务端实际校验位置`

### F-01 预约配对号 A / B

| 环节 | 位置 | 等级 |
|---|---|---|
| 生产 | `0x0062F6F0`：`A=[edi+0x168]`→`[esi+0x3A048]`；`B=[edi+0x16C]`→`[esi+0x3A04C]` | CONFIRMED |
| 序列化/传递 | `0x0062F7E0` 的 mmbook 请求；读取 `0x0062F7F9` / `0x0062F809` | CONFIRMED |
| 客户端保存 | `[matching+0x3A048]` / `[matching+0x3A04C]` | CONFIRMED |
| 战斗连接消费 | **UNKNOWN**（未找到 A/B 出现在战斗连接路径） | UNKNOWN |
| 服务端校验 | **UNKNOWN**（无服务端对端实现可复核 1649370 校验） | UNKNOWN |

> **判定：** A/B 是**大厅内部预约配对**，已被证明「必须被 accepted 回显」，但**没有证据**表明它进入战斗连接。⇒ **不得**把 A/B 标为战斗凭据。

### F-02 战斗端点（服务器地址 + 端口）

| 环节 | 位置 | 等级 |
|---|---|---|
| 生产 | `UNKNOWN`（未在目标 EXE 定位到端点写入点；文档明确 `Booking → 28960 linkage = UNKNOWN`） | UNKNOWN |
| 序列化/传递 | `UNKNOWN` | UNKNOWN |
| 客户端保存 | 候选 `[matching+0x278]` / reservation item `+0x168`/`+0x16C`（仅结构，非端点） | UNKNOWN |
| 战斗连接消费 | `UNKNOWN`（`BATTLE_28960 = NOT_OBSERVED`） | UNKNOWN |
| 服务端校验 | `UNKNOWN` | UNKNOWN |

> **判定：** 端点是交接链**首要缺口**。**不得**把「`mmstart` 中出现的数字」直接当作地址/端口。

### F-03 会话 ID / 玩家身份（XUID）

| 环节 | 位置 | 等级 |
|---|---|---|
| 生产 | Demonware `AuthIdentity{titleId=1004, userId}`（REFERENCE） | REFERENCE |
| 序列化 | mmbook payload 含 `u64 SessionId`（`0a <u64>`） | CONFIRMED（形状） |
| 客户端保存 | `UNKNOWN` | UNKNOWN |
| 战斗连接消费 | `UNKNOWN` | UNKNOWN |
| 服务端校验 | `UNKNOWN` | UNKNOWN |

### F-04 安全材料（securityKey / 会话密钥）

| 环节 | 位置 | 等级 |
|---|---|---|
| 生产 | Demonware 描述符提供 16B `securityKey`（`DtlsSessionConfig::SecurityKeySize = 16`） | REFERENCE |
| 序列化 | DTLS INIT / COOKIE_ECHO 携带 `securityId`(8B) | REFERENCE |
| 客户端保存 | per-peer `securityKey`（`DtlsPeerSystem::PeerSession`） | REFERENCE |
| 战斗连接消费 | 参与 `DtlsSessionKeys::derive` → aesKey/hmacKey/iv | REFERENCE |
| 服务端校验 | HMAC `authenticator` 校验 | REFERENCE |

> **判定：** securityKey 是**战斗 DTLS 的密钥输入**，来源可追溯到 Demonware 描述符。但「描述符由谁下发、何时刷新」在目标 EXE 中仅 `UNKNOWN`。**不得**把「地址/端口传递」等同于「凭据验证完成」。

---

## 3. `accepted` 字节形态（★ 与既有 023 结论冲突）

| 来源 | 形态 | 说明 |
|---|---|---|
| ol-mod 存档断言（`DemonwareTests.cpp:1602-1606`） | `13 08 \| 13 00 00 00 \| 0f 00 00 00 \| "mmbook accepted"`（**带 u32 前缀**） | 逐字节单测 |
| 本项目 023 之后实现 | **去掉 4 字节前缀** | 疑似 REGRESSION |

**冲突未裁定：** `OLMOD-CODOL-BOOKING-BATTLE-BRIDGE-030.md` 明确将此标记为
`ACCEPTED_BLOB_FORM_PRE023 = 正确`、`023 的"去掉 4 字节前缀"很可能是 REGRESSION`，
并要求用单变量实验判定。

> **纪律：** 在该实验完成前，**不得**把任一形态升级为 CONFIRMED。

---

## 4. 传输通道（accepted → 客户端）—— UNKNOWN

| 已排除 | 依据 |
|---|---|
| 直接 `call 0x632680` | 未找到匹配虚调用 |
| 普通 `mov reg,[obj+0x140]; call reg` | 未命中 |
| Base.dll 处理 mmbook | 全限定字符串扫描 0 命中（`base_caller = UNKNOWN`） |

| 未证实 | 说明 |
|---|---|
| `0x85` push 通道 | 属 2.6.9.7 证据，**不得**套用 |
| DedicatedControl | ol-mod 自建桥，非原版客户端事实 |
| ClientSessionBridge | ol-mod 进程内桥，**不属于客户端协议事实** |
| TCP / UDP / IPC / 共享内存 | 四者均未证实 |

> **判定：** `accepted` 的传输通道 = `UNKNOWN`。**不得**据 ol-mod 的桥实现反推客户端通道。

---

## 5. 匹配/预约状态机（客户端侧）

| 锚点 | RVA | 等级 |
|---|---|---|
| 状态码处理 | `0x00634080`（比较 `8` / `0x2A` / `0x1E` / `0x26`） | CONFIRMED |
| 回调桥 | `0x00634240`（`mov ecx,[eax+0x25C8]` 取匹配对象） | CONFIRMED |
| 回调注册 | `0x00633FE0`（引用 `0x7E7E8D` / `0x7E7F46`；直接调用 `0x62CCFA` / `0x62DF95`） | CONFIRMED |
| 网络抽象对象 | `0x00803830`（返回对象，校验 `类型==2`） | CONFIRMED（地址）/ 传输类型 UNKNOWN |
| 预约闩锁 | `[matching+0x288]`，唯一消费者 `0x00634402` | CONFIRMED |

**结论：** 客户端确实通过一个**网络抽象对象**接收匹配/预约状态；但该对象的**底层传输类型未确认**。

---

## 6. 连接生命周期（跨层）

| 阶段 | 大厅侧 | 战斗侧 | 证据 |
|---|---|---|---|
| 登录 | LobbyProtocol → established | — | REFERENCE |
| 匹配 | matching 创建 / BOOKING_PENDING | — | CONFIRMED |
| 预约 | mmbook → accepted | — | CONFIRMED（形状） |
| 闩锁 | `[matching+0x288]` | — | 未置 1（全部历史运行） |
| 发送 | mmstart | — | NOT_OBSERVED |
| 连接 | （大厅连接保留 / 关闭 = UNKNOWN） | 带外 getchallenge/connect；DTLS；netchan | REFERENCE |
| 进图 | — | Connected → ClientLoading → Active | CONFIRMED（服务端模型） |

**未确认：**
- 战斗连接建立期间，大厅连接是**保留 / 关闭 / 复用 / 异步**：`UNKNOWN`。
- 连接失败 / 取消匹配 / 返回大厅 / 战斗断线的状态回退：部分锚点存在（`disconnectCommand 0x1AA610`、`demoDisconnectCommand 0x1AAD70`、`disconnectKeepSession 0x204390`、`completeDisconnect 0x1C0FD0`），但**转移条件**未闭合。

---

## 7. 中间模块与平台组件（不得当作网络协议）

| 组件 | 作用 | 判定 |
|---|---|---|
| TCLS（`TCLS\ClientBase.dll`） | 写共享内存凭据、启动门禁 | **本地平台层**，非游戏协议 |
| TenProxy（`TenProxy.dll`） | 代理/隧道组件 | **中间层 API**，未见其承载游戏协议的直接证据 |
| IIPS（`IIPS\*`） | 补丁/资源下载（974 个 `.ifs`，23 GB） | **补丁通道**，与战斗协议是两套 |
| ACE / TGuard / TP3 | 反作弊 | **安全层**，非游戏协议 |
| WKNet（`0x1022axxx` 簇） | Tencent WeGame 选路（端口 13003/13004/13005，`wukong.gamesafe.qq.com`） | **平台选路**，非游戏 netcode（`docs/network-9goals.md` §13.2） |

> **纪律：** 上述组件即使有 `socket/connect/send`，也不得直接据此认定其为大厅或战斗协议的承载者。目标 EXE 的 netcode 本体代码被 `.tvm0`（约 31 MB）吞掉，静态明文面无法直接定位 —— 这是**有证据支撑的否定结论**（`docs/network-9goals.md` §13.2.4）。

---

## 8. C 层结论

- **交接链唯一已定位的缺失跳变：** `[matching+0x288]` 从未为 1 ⇒ `mmstart` 从未构造/发送 ⇒ 战斗首包从未出现。等级 `STRONG_CANDIDATE`（e1–e5 直接支持）。
- **A/B 配对号**：已证「必须被 accepted 回显」；**未证**进入战斗连接。
- **战斗端点**：来源 `UNKNOWN`（首要缺口）。
- **accepted 传输通道**：`UNKNOWN`。
- **大厅连接在战斗期间的去留**：`UNKNOWN`。
- **不得声称**：地址/端口传递 = 完整大厅—战斗认证链。
