# 06 — 准备与开始流程

> 对应任务书 §四 C（准备按钮）与 §四 E（开始对局）。

---

## 1. 准备按钮（ISSUE-0009）

### 1.1 问题陈述

点击"准备"后：**无任何网络上行，本地"已准备"状态也不变**。

实测（`ONCE_20261028_225645`，该轮 11/4 只有 4 条）：无一条是准备。

### 1.2 调用链——已定位到什么程度

| 环节 | 状态 | 证据 |
|---|---|---|
| Flash 按钮 → Scaleform 回调 | **UNKNOWN** | `.gfx` 在加密的 `ui_mp.ff` 内（熵 7.95–8.00） |
| Scaleform → `AS_SetReadyState` | **UNKNOWN** | 该类名存在（`rtti_full.md`），但 TD→COL 引用 0 处 |
| AS 类 → C++ 后端 | **UNKNOWN** | 同上 |
| C++ → 房间事件系统 | **UNKNOWN** | `MyEventHandler` 状态未定（见 §05） |
| 本地 UI 状态置 Ready | **未发生** | 用户观察 |
| 发上行（`11/4` 的 16 B 批次） | **未发生** | 该轮日志 |

⇒ **调用链在第 1 环就断了**，无法再往里指。

### 1.3 "AS_* 未实现"这个结论必须降级

`READY_BUTTON_NO_IMPL_20261028` 曾判"`AS_SetReadyState` 未实现"。但：

- RTTI 名字存在（163 个 AS_* 类名，`RE_FULL_20261029/rtti_full.md`）；
- TD→COL 引用 0 处**只能证明静态层找不到注册证据**；
- Scaleform 注册完全可能用**哈希/ID** 而非名字串。

原作者在 `READY_BUTTON_ROOT_CAUSE_CLOSED` 第 21 轮已承认这一点。
**本审计维持该降级：该结论是 LOW credibility。**

### 1.4 准备状态应通过哪个协议更新

实测：**`11/4 setRoomData` 里的 16 B 批次**就是 ready 批次。

日志原文（区间 D 的 kit 自己标注）：
```
-> 0B/4 setRoomData 空应答(channel=0x…, type=1, batch=21 ★就是那条 16B ready 批次 …)
★ 11/4 ready -> 发 Ready + RoomStateUpdated(countdown)
```

⇒ 客户端把"准备"编码进 `11/4` 的一个 batch，而不是单独协议。

### 1.5 服务端应返回什么

当前实现只做两件事：
1. 回显该 `11/4`（"三方同款"）；
2. 若 `ready_push.on` 存在，额外推 `01 <len> Ready` 与 `RoomStateUpdated(countdown)`。

**从未证明客户端消费了这两条推送**（见 `07_ROOM_EVENT_DISPATCH.md`）。

---

## 2. 开始对局（谁决定开始）

任务书要求明确：客户端主动 / 房主 / 匹配服务 / 房间服务推送？

### 2.1 实测答案：**客户端主动**

| 证据 | 内容 |
|---|---|
| `11/13 createRoom` | 客户端先发，服务端从不主动推 roomInfo |
| `11/4` | 客户端主动写房间状态 |
| `21/5` | 客户端主动查询 |
| `6/14 mmbook` | 客户端主动预约 |
| `6/14 mmstart` | **客户端主动给出开局命令** |

**没有任何一条服务端发起的"开始"消息。**

### 2.2 房主权限 / 成员数量 / 准备条件

| 条件 | 证据 | 结论 |
|---|---|---|
| 房主权限 | 无任何协议字段体现 | **UNKNOWN**（本机单人，无法验证） |
| 成员数量 | `memberCount` 只影响 `dwRoomMatchUber` 创建 | 与"能否开始"关系未证 |
| 准备条件 | 16 B ready 批次发过之后才有 `21/5→mmbook→mmstart`（B1） | **相关**，非因果 |

### 2.3 mmbook 与 mmstart 的准确位置

任务书要求明确这两者在大厅流程中的位置。实测：

```
路径 A（PvE）： 21/5(playlist=10) → 6/14 mmbook → 6/14 mmstart → 连战斗服
路径 B1（房间）：…11/4 ready… → 21/5(playlist=10) → 6/14 mmbook → 6/14 mmstart → 未连
```

| 命令 | 位置 | 内容 |
|---|---|---|
| **`mmbook`** | `findSessions` **之后**、`mmstart` **之前** | `mmbook 796 …`（预约），服务端回 `mmbook accepted`(20 B) |
| **`mmstart`** | `mmbook` **之后** | 路径 A：带 `map <具体图>`；路径 B：带 `playlist 37` + `start_map_rotate_once N` |

**§六 E 的答案**：
**mmbook = 预约；mmstart = 客户端对服务端下的"开局指令"**。
两者都由客户端主动发出。`mmbook` 不是"匹配服务"，是**预约战斗服实例**。

### 2.4 mmstart 的完整命令格式

路径 A（成功轮 `ONCE_20261026_220815`）：
```
mmstart sv_resetServer; 2486 0; 3265 18; 2489 0; 2574 0; 2500 0;
        g_gametype coop;  g_difficulty 1; ;
        map coop_train_mp_firingrange;2654 ; roomChatChannelID 0;
```

路径 B1（`ONCE_20261028_224009`）：
```
mmstart sv_resetServer; 2486 1; 3265 6; 2489 1; 2574 2;
        playlist 37; start_map_rotate_once 4; roomChatChannelID 1234605616436508552;
```

**差异归纳**：

| 字段 | 路径 A | 路径 B1 |
|---|---|---|
| `map <name>` | **有** | **无** |
| `g_gametype` | **有** | **无** |
| `g_difficulty` | 有 | 无 |
| `playlist <n>` | 无 | **有** |
| `start_map_rotate_once <n>` | 无 | **有** |
| `roomChatChannelID` | `0` | 非 0（= roomId） |
| `2486/3265/2489/2574/2500` | `0/18/0/0/0` | `1/6/1/2/0` 等 |

---

## 3. 服务端在 mmstart 后应该做什么

| kit 版本 | 行为 | 结果 |
|---|---|---|
| **10-26 成功轮（78,206 B）** | **仅空应答** | ✅ 客户端连上战斗服 |
| 10-27 起（88,162 B） | 仅空应答 | ❌ 未连 |
| 10-28 起（≥102 KB） | 额外推 `dwRoomMessageStartGame`(109 B) | ❌ 未连 |

⇒ **"推 StartGame"与"连上"没有正相关**（10-26 不推却连上了）。

---

## 4. 结论

| 问题 | 答案 |
|---|---|
| 准备按钮的 UI 回调在哪 | **UNKNOWN**（停在 Flash/Scaleform 层） |
| 点击后调用哪个函数 | **UNKNOWN** |
| 哪个条件决定是否发请求 | **UNKNOWN** |
| 准备状态走哪个协议 | **`11/4` 的 16 B 批次** |
| 服务端应返回什么 | 回显 + 可选 `Ready`/`RoomStateUpdated` 推送（**未被证明被消费**） |
| 谁决定开始战斗 | **客户端**（先 `mmbook` 再 `mmstart`） |
| 房主/人数/准备是否是前置 | **未证**；本机单人无法区分 |

**本专项的最大缺口**：准备按钮的 UI 侧完全不可达，
而它是"房间路径能否走通"的第一块多米诺。
