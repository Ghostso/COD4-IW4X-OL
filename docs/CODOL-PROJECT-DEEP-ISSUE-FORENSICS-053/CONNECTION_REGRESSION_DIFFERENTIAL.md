# 10-26 成功 → 10-29 失败：连接回归全差分

> 这是本任务要求的那份"完整差异表"和"最早发生变化的那一个输入"的答案。
> 所有结论均由**本审计直接读取磁盘上的原始 run 目录**重新计算，不引用上一轮报告的结论。

---

## 0. 结论先行（三句话）

1. **"10-26 成功 → 10-29 失败"这个二分是错的。** 磁盘上存在 **跨越 3 天的 8 次成功**和 **3 个彼此不同的失败区间**，
   失败不是一次退化，而是三次独立的入口/配置切换。
2. **唯一能把 8 次成功与 26+ 次失败完全分开的变量是 `mmstart` 里的地图名：**
   成功的全部是 `coop_train_mp_firingrange`，失败的无一例外落在其它地图上。**分离度 34/34，零反例。**
3. 该变量同时与两个共变量完全共线：**是否创建房间**（成功=无房间）与 **游戏根目录**（成功=沙箱）。
   因此纪律上不能宣布"地图就是根因"；但它是最廉价、且能一次区分三种解释的单变量。

---

## 1. 全量运行矩阵（本审计重算）

数据来源：`run_codol_001/runs/<RUN>/kit/lobby_srv.log` 与 `kit/_battle_out.txt`，
逐 run 正则提取 `mmstart 完整命令`、`createRoom`、`RX_CLIENT_GAME_HEADER`。

| Run | mmstart map | 创建房间 | roomChatChannelID | 战斗服 RX |
|---|---|---|---|---|
| ONCE_20261026_164227 | `coop_train_mp_firingrange` | 否 | `0` | **RX** |
| ONCE_20261026_172646 | `coop_train_mp_firingrange` | 否 | `0` | **RX** |
| ONCE_20261026_193429 | `coop_train_mp_firingrange` | 否 | `0` | **RX** |
| ONCE_20261026_211944 | `coop_train_mp_firingrange` | 否 | `0` | **RX** |
| ONCE_20261026_212253 | `coop_train_mp_firingrange` | 否 | `0` | **RX** |
| ONCE_20261026_215228 | `coop_train_mp_firingrange` | 否 | `0` | **RX** |
| ONCE_20261026_215943 | `coop_train_mp_firingrange` | 否 | `0` | **RX** |
| ONCE_20261026_220815 | `coop_train_mp_firingrange` | 否 | `0` | **RX** |
| ONCE_20261026_233111 | `coop_training_mp_cargoship` | **是** | `1234605616436508552` | — |
| ONCE_20261027_005433 | `coop_training_mp_cargoship` | 是 | 同上 | — |
| ONCE_20261027_010057 | `coop_training_mp_cargoship` | 是 | 同上 | — |
| ONCE_20261027_011512 | `coop_training_mp_cargoship` | 是 | 同上 | — |
| ONCE_20261027_012246 | `coop_training_mp_cargoship` | 是 | 同上 | — |
| ONCE_20261027_012519 | `coop_training_mp_cargoship` | 是 | 同上 | — |
| ONCE_20261027_120832 | `coop_training_mp_cargoship` | 是 | 同上 | — |
| ONCE_20261027_122904 | `coop_training_mp_cargoship` | 是 | 同上 | — |
| ONCE_20261027_123505 | `coop_training_mp_cargoship` | 是 | 同上 | — |
| ONCE_20261027_123823 | `coop_training_mp_cargoship` | 是 | 同上 | — |
| ONCE_20261027_132700 | `coop_training_mp_cargoship` | 是 | 同上 | — |
| ONCE_20261027_140400 | `coop_training_mp_cargoship` | 是 | 同上 | — |
| ONCE_20261027_171707 | `coop_chopper_mp_suburbs` | 是 | 同上 | — |
| ONCE_20261027_174747 | `coop_training_mp_cargoship` | 是 | 同上 | — |
| ONCE_20261027_192605 | `coop_training_mp_cargoship` | 是 | 同上 | — |
| ONCE_20261027_193644 | `coop_escape_mp_storm_spring` | 是 | 同上 | — |
| ONCE_20261027_202345 | `coop_training_mp_cargoship` | 是 | 同上 | — |
| ONCE_20261028_*（12 轮） | 无 `map`，只有 `playlist 37` + `start_map_rotate_once N` | 是 | 同上 | — |
| ONCE_20261029_*（3 轮） | 同上 | 是 | 同上 | — |

**统计**：8 次 RX 全部满足 `map == coop_train_mp_firingrange` 且 `创建房间 == 否`；
26 次零 RX 全部不满足。**该判据在全部 34 次带 mmstart 的运行上 100% 分离。**

---

## 2. 三个失败区间（不是一次退化）

### 区间 B — 2026-10-26 23:31 → 10-27 07:53

| 维度 | 成功（22:08:15） | 区间 B（23:31:17） |
|---|---|---|
| 启动根目录 | `run_codol_001\sandbox_ifs1_20260923` | **同一沙箱** |
| `coop_map.txt` | `coop_train_mp_firingrange` | **`coop_training_mp_cargoship`** |
| `mmstart` map | `coop_train_mp_firingrange` | **`coop_training_mp_cargoship`** |
| `mmstart` 序号段 | `2486 0; 3265 18; 2489 0;` | **`2486 1; 3265 1; 2489 0;`** |
| `g_difficulty` | `1` | **`0`** |
| `roomChatChannelID` | `0` | **`1234605616436508552`** |
| 是否创建房间（11/13） | **无** | **有** |
| 0B/4 setRoomData | 无 | **有（含 "16B ready 批次"）** |
| `11/4` 上行 | 无 | 有 |
| `102/7` | **0 次** | **0 次** |
| findSessions 应答对象 | 280 B | 280 B（**完全相同**） |
| 客户端上行 0x81/0x83 握手 | 有 | 有 |
| 战斗服 RX | **有** | 无 |

**区间 B 的关键**：`102/7` 一次都没出现，说明"102/7 导致零 RX"在这段**不成立**。

### 区间 C — 2026-10-27 17:17 → 20:23

| 维度 | 成功 | 区间 C |
|---|---|---|
| 启动根目录 | 沙箱 | **`COD OL`（完整本体，3095 文件）** |
| map | firingrange | cargoship / suburbs / storm_spring |
| `102/7` | 0 次 | **每次 5 秒重发，回显 50/50 全 0（555B）** |
| `memberCount`（11/13） | `0`（无 11/13） | **`1`**（`ob.u32(1); ob.u32(1)`） |
| 房间 | 无 | 有 |
| RX | **有** | 无 |

### 区间 D — 2026-10-28 → 10-29

| 维度 | 成功 | 区间 D |
|---|---|---|
| 启动根目录 | 沙箱 | `COD OL` |
| map | firingrange | **无 map，只有 `playlist 37`** |
| `coop_map.txt` | 存在 | **不存在** |
| 房间推送 | 无 | 有（自造 room envelope，122/146/70 B） |
| `102/7` | 0 次 | **不处理**（"对齐 10-26 成功轮"） |
| `memberCount` | — | `1` |
| RX | **有** | 无 |

**区间 D 里 `102/7` 已被改回"不处理"，与成功轮一致，但依然零 RX。**
⇒ `102/7` 不是区间 D 的原因。而区间 D 与成功轮的唯一 map 级差异是 `mmstart` 没有 map。

---

## 3. 已确认差异 / 未验证差异 / 无法复核

### 3.1 已确认差异（本审计直接读原始文件确认）

| # | 差异 | 证据 |
|---|---|---|
| D1 | 成功的 mmstart 带 `map coop_train_mp_firingrange`；失败的不带或带别的图 | 34/34 run 的 `lobby_srv.log` |
| D2 | 成功从不发 `11/13 createRoom`（0 次）；失败全部发 | `Select-String -Pattern 'createRoom'` 计数 |
| D3 | 成功的 `roomChatChannelID 0`；失败为 `1234605616436508552` | mmstart 原文 |
| D4 | 成功根目录为沙箱；10-27 12:00 之后为本体 `COD OL` | `chain*.txt` 第一行 `--root` |
| D5 | 区间 C 起 `102/7` 出现并被回显全 0 | 区间 C 日志 |
| D6 | 区间 B/C 起 `memberCount` 由 0 改为 1 | `lobby_server.py` 内 `ob.u32(1)` |
| D7 | findSessions 应答体在成功与失败**相同**（280 B） | 日志 `(对象 280 字节, maxPlayers=4)` 两侧一致 |
| D8 | 两侧都完成 0x81/0x83 Demonware 握手与 `mmbook accepted` | 两侧日志 |
| D9 | 战斗服二进制的启动参数一致（`--bind 0.0.0.0 --port 28960`） | 两侧 `_battle_out.txt` 头部 |

> ★ D7/D9 很重要：它排除了"findSessions 应答不同""战斗服没起"这两类解释。

### 3.2 尚未验证的差异

| # | 差异 | 为什么没验证 |
|---|---|---|
| U1 | 地图 → 客户端内部资源解析是否导致不发 connect | 需要实机单变量试验（本次审计禁止启动客户端） |
| U2 | 是否建房 → 是否让客户端走"房间内准备"分支而非直连 | 同上 |
| U3 | 沙箱 vs 本体 → IIPS/资源层差异是否影响连接 | 同上 |
| U4 | `task_params.txt`（区间 B 起出现，内容 `6c080800000002000000000000000500000000`）是谁写的、什么语义 | 未定位写入点 |
| U5 | `2486/3265/2489/2574/2500` 这组编号在 mmstart 里的语义 | 客户端内无对应表被解出 |
| U6 | `roomChatChannelID` 从 0 变为 0x1122334455667788 是否影响开局 | 未做单变量 |

### 3.3 无法复核的历史条件

| # | 条件 | 原因 |
|---|---|---|
| M1 | 10-26 成功轮的客户端内存转储 | 该轮无转储；最近的转储是 10-27 |
| M2 | 10-26 成功轮的网络抓包 | 从未采集（`THIRD_ROUND_PREREQUISITES R3-A03` 至今未做） |
| M3 | 用户在每轮实际点击的 UI 入口 | 无屏幕录制；只能从 mmstart 形态反推 |

---

## 4. 对原 P0 假设的裁决

| 原假设（上一轮登记） | 本审计裁决 | 依据 |
|---|---|---|
| H1：`mmstart` 无 map ⇒ 客户端不连 | **成立但不完整**。区间 B/C **有** map 仍失败 | 表 §1 |
| H2：`102/7` 回全 0 ⇒ 客户端不连 | **被否证为普遍原因**。区间 B 完全没有 102/7 仍失败；区间 D 已不处理仍失败 | §2 区间 B、D |
| H3：`mmstart` 推 StartGame 打断连接 | **被否证**。区间 B 未推 StartGame（"仅空应答"）仍失败 | 区间 B 日志 |
| H4：`memberCount` 影响连接 | **已被否证**（10-27 文档已记） | 区间 B 已是 1 仍失败 |
| H5：战斗服没启动/端口占用 | **被否证** | D9：两侧日志头一致 |

---

## 5. 最早发生变化的那一个输入

按时间顺序，紧邻最后一次成功（10-26 22:08:15）的下一次运行（10-26 23:31:17）
在下列输入上发生了变化：

```
coop_map.txt           coop_train_mp_firingrange  →  coop_training_mp_cargoship
mmstart map            coop_train_mp_firingrange  →  coop_training_mp_cargoship
mmstart 序号段         2486 0; 3265 18; ...       →  2486 1; 3265 1; ...
g_difficulty           1                          →  0
roomChatChannelID      0                          →  1234605616436508552
是否创建房间            否                          →  是
```

**这些不是六个独立变量。** 从 `lobby_server.py` 的行为看，
`roomChatChannelID` 与"是否创建房间"是同一件事的两面（频道号 = 返回的 roomId）；
`mmstart` 的其余字段是客户端根据"进入了房间"这件事自己带出来的。

因此**真正的自变量只有两个**：

- **A：选中的地图**（`coop_map.txt` / `playlist` 决定）
- **B：进入路径**（PvE 直接开局 vs 房间内开始）

而 A 与 B 在现有全部 34 次运行里**完全共线**，无法从历史数据中分离。

**结论：不能宣布 `mmstart` 或 `102/7` 是根因。** 上一轮的 H1/H2/H3 都已被数据部分否证。

---

## 6. 最小差分实验矩阵（必须做的单变量序列）

要分离 A（地图）与 B（入口路径），只需三次运行。每次只动一个变量。

| 实验 | 入口 | map | 其余 | 若 RX 出现 | 若仍零 RX |
|---|---|---|---|---|---|
| **E1** | PvE 直接开局（成功形态） | **`coop_train_mp_firingrange`** | 与 220815 逐字节相同（`g_difficulty 1`、`roomChatChannelID 0`、不建房） | 复现基线成功 → 进入 E2 | 说明"成功"已不可复现（环境退化），先修环境 |
| **E2** | PvE 直接开局 | **换成 `coop_training_mp_cargoship`** | 其余同 E1（仍不建房） | **地图不是原因**，问题在入口 | **地图就是原因**（这是关键判据） |
| **E3** | 房间内开始 | `coop_train_mp_firingrange` | 其余同 E1 | **入口不是原因** | 入口是关键（与 E2 合起来定位） |

**判据表**：

| E1 | E2 | E3 | 结论 |
|---|---|---|---|
| RX | RX | 零 | 入口路径是根因 |
| RX | 零 | RX | **地图是根因** |
| RX | 零 | 零 | 地图+入口都必要（需进一步二分） |
| RX | RX | RX | 两者都不是；差异在别处（回 §3.2 的 U4/U5/U6） |
| 零 | — | — | 基线不可复现，先解决环境（见 `07_HISTORICAL_REGRESSION_ANALYSIS.md`） |

**E1 必须先做**，因为它同时校验"沙箱 + firingrange + 无房间"这套历史成功条件是否仍然成立。

---

## 7. 复现 E1 的精确命令（不得由本审计执行）

```bash
python -I run_codol_001/run_frozen_chain_once.py --authorize-next-launch
python -I run_codol_001/run_frozen_chain_once.py \
  --game-root "D:/BaiduNetdiskDownload/使命召唤OL/run_codol_001/sandbox_ifs1_20260923" \
  --kit <复制的成功轮 kit> --seconds 240 --out chain_e1.txt
```

前置条件：
- 提权 agent 在线（`CODOLServer/logs/elevated_agent.json`）
- `kit/coop_map.txt` 内容为 `coop_train_mp_firingrange`
- 用户在 UI 里走**剧情/PvE 直接开局**入口（不是 BOT 房间）
- 判据：`kit/_battle_out.txt` 出现 `TX_NAT_REPLY` 或 `KEY_EXCHANGE_OK`

> ⚠️ 若沙箱已被 10-27 的决定废弃（"不得使用沙箱"），E1 需改用 `COD OL` 本体 +
> 同一套 mmstart 形态。这会把 D4（根目录）也变成变量，需在结论里注明。

---

## 8. 证据索引

| Evidence ID | 文件 | 证明的事实 |
|---|---|---|
| EV-REG-01 | `runs/ONCE_20261026_220815/kit/lobby_srv.log` | 最后一次成功的 mmstart 原文 |
| EV-REG-02 | `runs/ONCE_20261026_220815/kit/_battle_out.txt` | 成功轮战斗服完整 RX 序列 |
| EV-REG-03 | `runs/ONCE_20261026_233111/kit/lobby_srv.log` | 第一次失败的 mmstart 原文 |
| EV-REG-04 | `runs/ONCE_20261026_233111/kit/_battle_out.txt` | 失败轮战斗服只有 7 行初始化 |
| EV-REG-05 | `runs/ONCE_20261026_220815/chain_pos.txt` 第 1 行 | 成功轮根目录 = 沙箱 |
| EV-REG-06 | `runs/ONCE_20261027_120832/chain*.txt` 第 1 行 | 10-27 12:00 起根目录 = 本体 |
| EV-REG-07 | 34 个 run 的 `lobby_srv.log` | 全量分离矩阵（§1） |
