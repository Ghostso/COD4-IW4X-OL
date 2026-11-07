# 06 — 客户端静态逆向缺口

> 范围：仍**没有闭合**的调用链、数据流与状态转换。
> 已闭合的部分见 `02_ALL_HISTORICAL_ISSUES.md` 的 C 组，不要在本文找。

---

## 1. 未闭合的链（按"断在哪一环"排序）

### 1.1 socket → 解析器（最小未闭合边）
**ISSUE-0041**

```
socket recv
  → [esi+0xA8]（recv 目的地，已证实）
  → ???                       ← ★ 断在这里
  → [esi+0xB0]（会话对象）
  → 0x7765A0（读取器）
  → 0x81/0x83/0x84/0x85 分支（已证实）
```

原文（`CODOL-BATTLE-SERVER-RECEIVE-LINK-050/00_FINDINGS.md`）：
> "不能把'对象构造'写成'payload 已复制'。"

**为什么它是"最小"**：048→050 三个任务、以及之后的 gamestate/configstring/snapshot/reliable
五项语义（ISSUE-0044）全都悬在这条边上。

### 1.2 五项客户端消费语义
**ISSUE-0044**（解决率 0%）

| 语义 | 已知 | 未知 |
|---|---|---|
| opcode 分发（A-03） | 诊断串 `gamestateupdate %d` @0x54B7B/0x73214 | 表位置、分发规则 |
| gamestate（A-04） | — | 读取/存储路径 |
| configstring（A-05） | `EXE_CONFIGSTRINGMISMATCH` @0x731E1/0xF2833 | 索引→字段映射 |
| snapshot（A-06） | — | delta 基线选择、EOF |
| reliable（A-08） | — | 0x01/0x02 的分发 |

### 1.3 加密节区
**ISSUE-0042**：`.tp3` 第 3 节区缺 ~229.6 MB（VSize 0x0DBB1CC0 vs 实有 0x4F000）。
**ISSUE-0043**：主 DLL `.tvm0`(31.4 MB) / `.tls`(15.5 MB) 未解码。

> 注意：E06 解出的 `.tvm0`（aPLib 块）属于 **2.6.9.7 的恢复映像**，与本 build 主 DLL 的
> `.tvm0` 不是同一个东西。这两条**不得合并**。

### 1.4 房间初始化
**ISSUE-0012**：`dwRoomMatch::Init` 的调用点。函数体在加密节，静态看不到。

已知链路：
```
dwRoomMatch::Init()  [static void, 未执行]
  └─ 局部类 MyEventHandler { vtable 0x00DC78E8, slot[1]=0x63B500 }
       └─ 建房回调 0x63B500 → 0x63E510 → 创建 dwRoomMatchUber
            └─ +0x68 = 0x63C5E0（自动开局状态机，当前停在状态 1）
```

### 1.5 房间信道
**ISSUE-0011**：`0x7E7C90` 的 p1/p2 来自槽6 的 `[ebp+8]/[ebp+0xc]`，
而槽6 是 `call dword ptr [reg+0x18]` 调的（全镜像 5421 处），静态无法唯一定位调用者。

已证实的：
```
dwLobbyEventHandler (vtable 0x00DE07A4)
  槽6 0x7F1060 → 0x7E7C90（按 roomId_hi/roomId_lo 路由）
  槽7 0x7F10C0 → 0x7E79C0（校验 [obj+8]==key_hi, [obj+0xc]==key_lo）
  槽8 0x7F1110 → "是不是我自己"（比对本地玩家 id）
handler 0x6371F0 → 位流 → 0x634870 → 分发表 0x636f3c（type ≤ 0x2E，41 个有效）
```

未定：**信封里 roomId 的字节位置**。

### 1.6 UI
**ISSUE-0046**：163 个 `AS_*` RTTI 类名可枚举，但 TD→COL 引用 0 处；
`ui_mp.ff` 加密；无 `.gfx` 工具。
→ 按钮的回调绑定**静态不可达**。

---

## 2. 状态机

### 2.1 连接状态机（已解出，但无消费者证据）
`0x005C8060` 是"状态值→状态名"映射：

| 值 | 名称 |
|---|---|
| 0 | CA_DISCONNECTED |
| 1 | CA_CINEMATIC |
| 2 | CA_LOGO |
| 3 | CA_CONNECTING |
| 4 | CA_CHALLENGING |
| 5 | CA_LOADING |
| 6 | CA_CONNECTED |
| 7 | CA_SENDINGSTATS |
| 8 | CA_GAMESTATE |
| 9 | CA_PRIMED |
| 10 | CA_ACTIVE |

`call 0x5C8060` 搜不到（两处是数据误报）⇒ 通过 vtable/间接调用。
**缺口**：没有任何一次实机把当前 CA 值读出来。→ 见 ISSUE-0045（ACE 拦读）。

### 2.2 自动开局状态机 `0x63C5E0`
跳表：1→0x63C7F8、2→0x63C85F、3→0x63C89B、4→0x63C8B8、5→0x63C970（自动开局）

当前 `[U+0x20] = 1`；状态 1 在 `0x63C350` 返回假处返回（ISSUE-0013）。

### 2.3 `dwRoomImp` 的闸门（旁支，已作废为主因）
`+0x10614` 由 dvar "3291" 派生，恒 0；`0x62FE80` 读它，为 0 时直接返回。
→ ISSUE-0014（OBSOLETE）：即使打开也不会让 `dwRoomMatchUber` 出现。

---

## 3. 数据流未定

| 数据 | 已知 | 未知 |
|---|---|---|
| 67 字节战斗服地址块 | 11 个连续 IPv4 + 原生小端 u16 端口 + 1 B NAT（`0xB756A0` 证明） | 由谁填入、何时填入 |
| `mmbook accepted` 的 (A,B) | 必须回显客户端的 | 预留槽 `+0x168/+0x16C` 的填充者（ISSUE-0054） |
| `dwRoomMessage*` 的 type 常量 | 41 个构造器只有 2 个能确定类型 | 39 个仍是 `?`（hist_combat #30） |
| 6/5 订阅的 20 个事件编号 | 请求里有 20 | 编号→类名映射（ISSUE-0017） |
| playlist 编号语义 | 官方表 123 项 | 37/50 的真实含义（ISSUE-0021） |

---

## 4. 运行时取证的边界（重要）

| 手段 | 状态 | 出处 |
|---|---|---|
| ReadProcessMemory（活进程） | **不可行**：t+0.01s 起 err=5，ALL_ACCESS 也一样 | `docs/ACE_BLOCKS_EVERYTHING_20261028.md` |
| 硬件写断点 | **不可行**：依赖调试附加，ACE 拒绝 | 同上 |
| 早期句柄 + 立即全量转储 | **有时可行**：10-27 的 `dump_earliest` 读到 1630 MB / 0 失败块 | `docs/GATE_B_INIT_PATH_20261027.md` |
| 与建房事件重叠 | **不可行**：建房在 ~80–100 s，早期窗口在 ~24 s | `docs/PROBE_BLOCKED_BY_ACE_20261028.md` §四 |

> **矛盾未解**：既有记忆称 t+15.39s 可读、t+32.2s 后永久 err=5；
> 10-28 实测 t+0.01s 就失败。两次结果不同，原因未定 → **ISSUE-0045**。

**这是当前所有动态问题（房间按钮、路由键、CA 状态）的共同障碍。**

---

## 5. 已闭合但仍然值得记住的（避免重查）

- `0x63C5E0` 属于 `dwRoomMatchUber`（vtable 0x00DC795C +0x68），不属于 `dwRoomImp`（0x00DC7274）。
- `0x63B500` 是 `MyEventHandler` 的 slot[1]，只在 `0x00DC78F0` 出现一处。
- `room.match.quick/ranked/coop/cancel` 是**控制台命令**，不是自动开局路径。
- `dwRoomMessage*` 的 TypeDescriptor = `name_va - 9`（不是 -8）。
- 位流原语：`0xB77B10` writeBits、`0xB777C0` writeData、`0xB774E0` readBits、`0xB77A70` 核心。
- `StartGame::serialize` @0x00625BE0 已解出首段（3 位 type + 8 位字段 + `0x13`/`8` 的 tag/len 对）。
