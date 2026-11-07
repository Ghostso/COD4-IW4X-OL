# 02 — 真实大厅状态机（按证据重建）

> 由 64 个 run 的 `kit/lobby_srv.log` 按行重建，**不是**把任务书里的候选流程当真。
> 凡任务书候选与实际不符之处，逐条注明「实测更正」。

---

## 1. 总流程（唯一共同主干）

以下 20 个请求（含 10\`/21 ×10）构成**恒定前缀**：这 20 个 (svc,task) 组成的**集合**
在 **56/56 个 run 里完全相同**（顺序在各 run 间有轻微差异，但集合不变）。

```
S0  连接建立
      <- 客户端 hello (28 B) = c8 00 00 00 | c8 00 00 00 | d2 00 00 00 | dc 00 00 00 | 00 00 08 00 | 0f 8c 91 3c 8b d8 80 c1
      -> 0x81 (26 B) 服务端应答
      <- 0x82 stage1 (153 B)
      -> 0x83 (14 B) challenge
      ★ KDF 试解命中（aes_out / challenge）

S1  会话 bootstrap（前 20 个恒定；其余 15 个在位置 30 之后按 run 变化）
      71/4  71/10  10/12  80/70  12/6  6/5  8/1  8/2
      10/21 ×10（10 个 publisher 文件）
      10/12  80/107  9/14  3/53  29/10  71/13  10/20  80/230  93/1
      80/119  80/174  80/173  8/3  71/7  71/3  68/3  28/4  4/13  71/18
      102/7  102/1  3/46  3/48  80/232  9/5  4/4

S2  档案/身份确认
      102/1  80/130  93/1  4/13  71/3
      （8/3 上传档案也在这一段）

S3  选单查询
      21/5 findSessions        ← 客户端带 playlist 号来问"有哪些 session"
      102/5

S4  ★ 分叉点：进入哪条游玩路径
```

**S1 的 20 个恒定请求是硬证**：无论后续成功还是失败、无论 PvE 还是 BOT，
这个**集合**完全一致。**"启动阶段有问题"的说法与此矛盾。**

⚠️ 更正：位置 30 之后的请求**并不恒定**——
只有 32/56 个 run 按同一顺序包含全部 35 个；12 个 run 的排列不同。
所以本文件只对"前 20 个的集合"作强断言。

---

## 2. S4 分叉：两条互斥路径

### 2.1 路径 A —— PvE 剧情直接开局（**唯一有过战斗连接成功的路径**）

```
21/5 findSessions(playlist=10)
      ↓  服务端回 mission session（280 B, maxPlayers=4）
6/14 mmbook        ← 客户端"预约"
      ↓  服务端 push 'mmbook accepted'(20 B)
6/14 mmstart       ← 客户端给出完整开局命令
      ↓  ★ 本路径下服务端只回空应答（10-26 成功轮的形态）
【客户端自行连 UDP 28960】
```

实机证据（`ONCE_20261026_220815` @22:09:15）：
```
★ mmstart 完整命令: mmstart sv_resetServer; 2486 0; 3265 18; 2489 0; 2574 0; 2500 0;
   g_gametype coop;  g_difficulty 1; ; map coop_train_mp_firingrange;2654 ; roomChatChannelID 0;
★ mmstart 选择: gametype=coop map=coop_train_mp_firingrange
★ 已记住剧情地图 -> coop_map.txt = coop_train_mp_firingrange
-> 6/14 命中 'mmstart' … -> 仅空应答
-> 6/14 空应答(payload=28)
```
战斗服侧同轮收到 `TX_NAT_REPLY 29B`（详见 `11_HISTORICAL_SUCCESS_FAILURE_TIMELINES.md`）。

**本路径的关键特征**：
- `roomChatChannelID 0`（**不在任何房间里**）
- 全程**没有** `11/13 createRoom`、**没有** `11/4`
- 请求序列只有 3 条结束时事件：`21/5 → 6/14(mmbook) → 6/14(mmstart)`

### 2.2 路径 B —— 房间内开始对局（BOT / 多人）

```
21/5 findSessions(playlist=50 或其它)
      ↓  服务端回本地 Host session
11/13 createRoom   ← 客户端建房
      ↓  服务端回 roomId + memberCount
11/4 setRoomData ×N ← 客户端把房间状态写进频道（ready 批次在其中）
      ↓  服务端回显频道推送（+ 可选 game start）
【随后分成 B1 / B2】
```

**B1 —— 房间内点"开始"**（10-27 202345 / 10-29 002046 实测）：
```
… 11/4 ×N …
21/5 findSessions(playlist=10)
6/14 mmbook
6/14 mmstart   ← 这一次 mmstart 带的是 playlist 37，没有 map
```
注意：这条路径**同样会走到 mmstart**，只是 mmstart 的内容不同。

**B2 —— 房间内没走到"开始"**（10-29 E1 实测）：
```
… 11/4 ×11 …
【再无 21/5、无 6/14】→ 33 秒后客户端退出
```

### 2.3 关键更正（与任务书候选流程的差异）

| 任务书候选 | 实测 | 依据 |
|---|---|---|
| "准备状态 → 开始请求 → 匹配/预约" | 房间路径里 **`11/4` 的 16 B 批次本身就是 ready**，不是独立协议 | 日志 `★ 11/4 ready -> 发 Ready + RoomStateUpdated(countdown)` |
| "mmstart 或正式开始机制" | **mmstart 是两条路径共同的开局命令**，只是内容不同 | 两条路径都有 `★ mmstart 完整命令` |
| "客户端获得战斗服地址 → 自主连接" | **地址在 bootstrap 期（1/5 之外）就给了**；mmstart 之后才连 | 见 §4 |
| "创建房间 → 房间初始化 → 成员同步 → UI 更新 → 准备" 是必经链 | **PvE 路径完全没有房间**，直接 mmbook→mmstart | `roomChatChannelID 0` |

---

## 3. 各路径的阶段对比表

| 阶段 | PvE(路径A) | 房间内开始(B1) | 房间内未开始(B2) |
|---|---|---|---|
| S1 bootstrap 35 请求 | ✅ | ✅ | ✅ |
| 21/5 findSessions | ✅ playlist=10 | ✅ playlist=50 | ✅ playlist=50 |
| 11/13 createRoom | ❌ | ✅ | ✅ |
| 11/4 setRoomData | ❌ | ✅ | ✅ |
| 房间 ready 批次(16 B) | ❌ | ✅ | ✅ |
| 6/14 mmbook | ✅ | ✅ | ❌ |
| 6/14 mmstart | ✅ 带 map | ✅ 带 playlist 37 | ❌ |
| 战斗服首包 | ✅（10-26 八轮） | ❌ | ❌ |

**这张表是本任务最重要的产出**：
**B1 与路径 A 都走到了 mmstart，但只有路径 A 产生了战斗连接。**
所以"有没有 mmstart"不是判据；**mmstart 的内容**才是。

---

## 4. 战斗服地址到底在哪一步给到客户端

任务书候选把"客户端获得战斗服地址"放在 mmstart 之后。实测不支持这个顺序：

- `21/5 findSessions` 的应答对象里就带 67 B 地址块
  （`cc.build_mission_session_object(..., address67=True)`，`lobby_server.py:840-844`；
  对象大小 280 B = session 记录 + 地址块）。
- 成功轮与失败轮的 `21/5` 应答**都是 280 B**（`11_...TIMELINES.md` 有对照）。
- 也就是说 **地址在 mmstart 之前就到了客户端**。

⇒ 客户端"拿到地址却不连"是**确实发生过**的事实，不是地址没给。

这让 ISSUE-0020 的候选解释进一步收窄：不是"地址缺失"，而是"拿到地址后不发起连接"。

---

## 5. 服务端主动推送在流程中的位置

实测到的大厅下行推送只有三类：

| 推送 | 触发时机 | 协议 | 证据 |
|---|---|---|---|
| `mmbook accepted` (20 B) | 收到 `6/14 mmbook` 后 | 6/14 应答 + push | 全部含 mmbook 的 run |
| 频道回显（`0B/4` 后） | 收到 `11/4` 后 | 11/4 → 频道 | 房间路径全部 run |
| `dwRoomMessageStartGame` (109 B) | `mmstart` 后（部分 kit 版本） | 6/14 push | 10-28/10-29 的 kit |

**没有任何一条"服务端主动发起"的推送**（例如服务端先推 roomInfo 让客户端建房）。
建房永远是**客户端先发 `11/13`**。

> 这一点很重要：任务书问"是客户端主动请求还是服务端推送决定开始"——
> 实测答案是**客户端主动**：`11/13`、`11/4`、`21/5`、`6/14` 全部由客户端发起。

---

## 6. 被遗漏/不存在的阶段

| 任务书阶段 | 实测结论 |
|---|---|
| "房间成员同步" | 客户端**从不单独请求**成员列表；成员信息随 `11/4` 批次与房间推送走 |
| "房间 UI 状态更新（客户端主动拉取）" | 无拉取；纯靠 `11/4` 回显与推送 |
| "匹配/预约"（独立于 mmbook） | **不存在独立阶段**；`mmbook` 就是预约 |
| "开始对局条件满足"作为客户端本地判定 | 无法从日志证明；但从 B1/B2 看，进不进入 `mmstart` 由**用户是否点了开始**决定 |

---

## 7. 结论

真实大厅流程是：

```
S1 bootstrap（35 请求，恒定）
  → S2 档案确认
  → S3 21/5 findSessions（带 playlist）
  → S4 分叉
       ├─ A: mmbook → mmstart(map)          → 客户端连战斗服   ✅ 10-26 八轮
       └─ B: createRoom → setRoomData×N
               ├─ B1: (→ mmbook → mmstart(playlist37))  → 未观测到连接
               └─ B2: 停在房间                     → 未观测到连接
```

**唯一的成功路径是 A，且 A 的特征是 `roomChatChannelID 0` + mmstart 里带具体 map。**
