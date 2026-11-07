# 08 — Playlist 与模式入口路径

> 对应任务书 §五。按实际观测到的入口分别建立流程，不拼接。

---

## 1. 已观测到的入口

| 入口 | findSessions playlist | 是否建房 | 是否走 mmstart | 战斗连接 |
|---|---|---|---|---|
| **PvE 剧情** | `10`（35 B 请求） | ❌ | ✅ 带 `map` | ✅ 10-26 八轮 |
| **BOT 多人** | `50`（75 B 请求） | ✅ | ✅ 带 `playlist 37`（B1）或 ❌（B2） | ❌ |
| 其它 playlist | 见到 `10` 被复用（`ONCE_20261028_224009` 第二轮） | 视情况 | — | ❌ |

**只观测到这两个 playlist 号**：`10` 与 `50`。

---

## 2. PvE 剧情入口（路径 A）

```
S1 bootstrap(35)
  → 21/5 findSessions 请求 35 B：playlist=10
  → 服务端回 280 B / maxPlayers=4 / map=coop_training_mp_cargoship（注意：回的图 ≠ 客户端要的图）
  → 6/14 mmbook  → 'mmbook accepted'
  → 6/14 mmstart 带 map coop_train_mp_firingrange（客户端自己指定）
  → 服务端仅空应答
  → 客户端连 28960 ✅
```

**特征**
- `roomChatChannelID 0`
- **无 11/13、无 11/4**
- `21/5` 应答的地图（cargoship）与 `mmstart` 的地图（firingrange）**不一致**，
  但**仍然连上了** —— 说明 mmstart 的地图优先。

## 3. BOT 房间入口（路径 B）

```
S1 bootstrap(35)
  → 21/5 findSessions 请求 75 B：playlist=50
  → 服务端回 261–266 B（本地 Host session）
  → 11/13 createRoom → 37 B
  → 11/4 setRoomData ×N（含 16 B ready 批次）
  → 服务端回显频道推送
  → 【B1】21/5 findSessions(10) → mmbook → mmstart(playlist 37)      → 未连
  → 【B2】停在这里                                                    → 未连
```

**特征**
- `roomChatChannelID = roomId`（非 0）
- **有 11/13、有 11/4**
- mmstart 里**没有 map**，只有 `playlist 37` + `start_map_rotate_once N`

---

## 4. 共用 / 不同阶段

| 阶段 | PvE | BOT |
|---|---|---|
| S1 bootstrap 35 请求 | **共用（逐字节同序）** | **共用** |
| 档案确认 | 共用 | 共用 |
| 21/5 findSessions | 共用（**请求尺寸不同：35 vs 75**） | 同左 |
| 11/13 createRoom | **无** | **有** |
| 11/4 setRoomData | **无** | **有** |
| 6/14 mmbook | **有** | **有（仅 B1）** |
| 6/14 mmstart | **有（带 map）** | **有（带 playlist）/ 无（B2）** |
| 战斗连接 | **有** | **无** |

**只在 PvE 出现的**：mmstart 里的 `map`/`g_gametype`/`g_difficulty` 字段。
**只在 BOT 出现的**：`11/13`、`11/4`、`0B/4`、`roomChatChannelID ≠ 0`、`playlist 37`。

---

## 5. 哪些入口能直接触发战斗预约

**两个入口都能触发 `mmbook`**（= 预约）。
PvE 一次就到；BOT 要先建房、发 ready，再 `21/5(10)` → `mmbook`。

⇒ **"必须先创建房间"只对 BOT/多人成立，PvE 不需要。**

---

## 6. 哪些入口由服务器自动开始

**没有。** 全部由客户端主动发 `mmstart`。

---

## 7. playlist 编号的真实语义

| 观察 | 事实 |
|---|---|
| `playlist=10` 出现在 35 B 请求里 | PvE 剧情入口 |
| `playlist=50` 出现在 75 B 请求里 | BOT 多人入口 |
| mmstart 里出现 `playlist 37` | **与 findSessions 的 50 不同号** |
| 官方 `mp_playlists_shipRetail_1.0.0.info` 共 123 条 | 含 123 项 |

**关键矛盾**：`findSessions` 用 50，`mmstart` 用 37。
两者**不是同一个编号空间**，或至少不是同一时刻的同一个值。

三种解释均未证：
1. `37` 是"排序后下标"（`50→148`、`37→123` 的换算曾出现在 10-28 文档）；
2. `37` 是轮换序号；
3. `37` 是另一个 playlist 字段。

---

## 8. 结论

**PvE 与 BOT 的差别不在 bootstrap，而在 S4 分叉之后**：

- PvE：直接 `mmbook → mmstart(map)` → 成功
- BOT：`createRoom → setRoomData×N → mmbook → mmstart(playlist)` → 失败

**唯一有成功证据的入口是 PvE 剧情。**
BOT 入口从未产生过战斗连接（32 个房间 run 全部零 RX）。
