# CODOL-ISSUE-0021 — `mmstart` 不带 map/gametype，playlist 语义未定

> 深度取证档案 · 2026-10-29
> 本档案修正了上一轮对该 Issue 的定位：它不是"独立根因"，而是 ISSUE-0020 的两个共线自变量之一。

---

## 01. 问题基本信息

| 项 | 值 |
|---|---|
| Issue ID | `CODOL-ISSUE-0021` |
| 完整标题 | `mmstart` 命令中不含 `map`/`g_gametype`，且 `playlist` 编号语义（ID / 下标 / 轮换序号）未定 |
| 所属系统 | `lobby`（客户端 → 大厅 6/14） |
| 优先级 | **P0**（本审计上调：它是 ISSUE-0020 的候选自变量之一） |
| 当前状态 | `OPEN` |
| 首次发现 | 2026-10-28 21:26（首次出现 `playlist 37` 形态的轮次） |
| 最近验证 | 2026-10-29 00:21（`ONCE_20261029_002046`） |
| 首次发现任务 | 2026-10-28 BOT 房间实验 |
| 最近调查任务 | 本任务 |
| 客户端版本 | 3.19.26.22 / 1649370 |
| 服务端版本 | 大厅 `lobby_server.py` 工作 kit 88,162 B（SHA `ff473204…`）；失败轮 kit 108,173–109,705 B |
| Git 提交 | UNKNOWN（无 git） |
| 阻塞可玩战斗 | 是（经 ISSUE-0020） |
| 上游依赖 | ISSUE-0012（房间初始化） |
| 下游依赖 | ISSUE-0020 |

**版本区分**：本 Issue 的证据全部来自 3.19 实机日志；未使用 2697 / OLfinal / 2.6.9.7 的任何数据。

---

## 02. 问题的精确定义

**预期行为**
客户端在 `6/14 mmstart` 里明确告诉大厅：这一局打哪张图、什么模式。大厅据此对齐 `findSessions` 应答与战斗服地图。

**实际行为（失败区间 D，2026-10-28 起）**
```
mmstart sv_resetServer; 2486 1; 3265 6; 2489 1; 2574 2; playlist 37;
        start_map_rotate_once 7; roomChatChannelID 1800154382;
```
- **没有 `map`**
- **没有 `g_gametype`**
- 只有 `playlist 37` 与 `start_map_rotate_once N`

对比成功区间（2026-10-26）：
```
mmstart sv_resetServer; 2486 0; 3265 18; 2489 0; 2574 0; 2500 0;
        g_gametype coop;  g_difficulty 1; ; map coop_train_mp_firingrange;2654 ; roomChatChannelID 0;
```

**偏差**
成功轮：客户端知道具体地图（`map coop_train_mp_firingrange`），且 `roomChatChannelID 0`（不在房间里）。
失败轮：客户端只知道一个 `playlist` 编号，且在一个房间频道里。

**失败边界（逐层）**

| 层 | 结论 |
|---|---|
| 请求是否发出 | ✅ 发出 |
| 服务端是否收到 | ✅ 收到 |
| 服务端是否解析出 map | ❌ **`★ mmstart 选择: gametype=? map=?`** |
| 服务端是否据此对齐 findSessions | ❌ 不能（没有 map 可对齐） |
| 客户端是否收到对齐后的 session | ⚠️ 它拿到的仍是 `playlist 50 → mp_raid` |
| 客户端是否连战斗服 | ❌ 见 ISSUE-0020 |

**失败边界一句话**：`mmstart` 里没有地图名，服务端就无法回答"这局打哪张图"。

---

## 03. 历史发现过程

| 日期 | Run | mmstart 形态 | 战斗服 | 结论 |
|---|---|---|---|---|
| 2026-10-26 16:42–22:08（8 轮） | `…_164227` … `_220815` | 带 `map coop_train_mp_firingrange` + `g_gametype coop` | RX | 成功基线 |
| 2026-10-26 23:31–10-27 20:23 | `…_233111` … `_202345` | 带 `map <真实地图>` + `g_gametype coop` | 零 RX | 带 map 也可能失败 |
| 2026-10-28 21:26 起（15 轮） | `…_212642` … `_002046` | **只有 `playlist 37`** | 零 RX | 当前形态 |

**★ 本审计的关键更正**：
上一轮把"mmstart 无 map"当作失败原因。但区间 B/C 的 17 轮**都有 map** 且**都失败**。
因此"有 map 就能连"不成立，"没有 map"也不是唯一充分条件。

---

## 04. 原始证据清单

| Evidence ID | 类型 | 路径 | SHA-256 | 定位 | 能证明 | 不能证明 | 复核 |
|---|---|---|---|---|---|---|---|
| EV-0021-01 | 大厅日志 | `runs\ONCE_20261029_002046\kit\lobby_srv.log` | `c6578c99…` | `00:21:51` | 当前 mmstart 只有 playlist | 客户端为何这样发 | ✅ |
| EV-0021-02 | 大厅日志 | `runs\ONCE_20261026_220815\kit\lobby_srv.log` | `bf650058…` | `22:09:15` | 成功轮 mmstart 带 map + `g_difficulty 1` | — | ✅ |
| EV-0021-03 | 大厅日志 | `runs\ONCE_20261026_233111\kit\lobby_srv.log` | `495b9501…` | `23:32:34` | 带 map 仍失败的第一次 | — | ✅ |
| EV-0021-04 | 全量矩阵 | 34 个 run 的 `lobby_srv.log` | 见 `EVIDENCE_INDEX.json` | 见差分 §1 | 地图与 RX 的共变 | 因果 | ✅ |
| EV-0021-05 | 大厅源码 | `CODOL_VERIFIED_GOLDEN_20261019\lobby_server.py` | `ff473204…` | 行 1090–1143 | mmstart 解析逻辑 | 客户端语义 | ✅ |
| EV-0021-06 | playlist 表 | `kit\publisher_files\mp_playlists_shipRetail_1.0.0.info` | 见索引 | 123 条目 | 官方 playlist 编号集合 | 37 的含义 | ✅ |

**MISSING**：客户端侧 `playlist` 编号的构造代码（RVA UNKNOWN）；10-26 成功轮的 UI 入口截图。

---

## 05. 源码级定位

**文件**：`CODOL_VERIFIED_GOLDEN_20261019/lobby_server.py`
**函数**：`reply_objects()` → `service==6, task` 分支 → mmstart 子分支
**行号**：1090–1150

```python
m = re.search(rb"mmstart[^\x00]{0,512}", body)
if m:
    full_cmd = m.group(0)
    tok = full_cmd.split()
    token = tok[1] if len(tok) > 1 else b""
    fnv = _fnv1a(token)
    _cmd_txt = full_cmd.decode("latin1", "replace")
    _map = re.search(r"\bmap\s+([^;\s]+)", _cmd_txt)
    _gt  = re.search(r"\bg_gametype\s+([^;\s]+)", _cmd_txt)
    log("       ★ mmstart 完整命令: %s" % _cmd_txt)
    log("       ★ mmstart 选择: gametype=%s map=%s"
        % (_gt.group(1) if _gt else "?", _map.group(1) if _map else "?"))
    if _map and _gt:                      # ← ★ 关键：两个都非空才写 coop_map
        ...写 coop_map.txt / active_room.json...
```

| 项 | 值 |
|---|---|
| 输入 | `6/14` payload（含 `mmstart …` 文本） |
| 输出 | `(objects, note, pushes)` |
| 副作用 | 若 `_map and _gt` 同时非空 → 写 `coop_map.txt`、`active_room.json` |
| 失败返回 | 无。`_map` 或 `_gt` 为空时**静默跳过**，只打 `?` |
| 与 Issue 的关系 | 失败区间里 `mmstart` 两个正则都匹配不到 ⇒ `coop_map.txt` **不被更新** ⇒ 下一次 `findSessions` 仍用旧值 |

**关键推论**：由于 `findSessions` 发生在 `mmstart` **之前**，`coop_map.txt` 的自校正
只在**下一轮**才生效。因此单轮内 `findSessions` 回的地图（`mp_raid`）与 `mmstart` 的意图
（`playlist 37`）必然不一致，除非 `coop_map.txt` 事先就写好了。

---

## 06. 客户端逆向定位

| 项 | 值 |
|---|---|
| 映像 | `codoMP_client_shipRetail.exe` 7,841,344 B / `36997674…b537` |
| ImageBase | `0x00400000`，DllCharacteristics `0x8100`（无 ASLR） |
| 构造 `mmstart` 的客户端函数 | **UNKNOWN** —— 未定位 |

**已知**：`mmstart` 是**文本命令**，格式 `mmstart sv_resetServer; <k> <v>; …`。
其中 `2486/3265/2489/2574/2500/2654` 是**编号键**，语义未解。

**陷阱检查**
| 陷阱 | 是否踩到 |
|---|---|
| RVA/VA 混淆 | 否（本 Issue 无地址结论） |
| 跨版本地址混用 | 否 |
| TQOS/TDR 误认 | 否 |
| 静态字符串≈函数执行 | 否 |
| 套用 2697/IW4X/CoD4x | 否（`mmstart` 是 CODOL 家族语法，未用外部结构） |

**FIRST_UNPROVEN_EDGE**：客户端在什么 UI 状态下选择"发 playlist 而不是发 map"。

---

## 07. 网络协议级定位

| Offset | Length | Field | Encoding | 证据 | 等级 |
|---|---|---|---|---|---|
| — | — | `mmstart` 前缀 | ASCII | EV-0021-01/02 | C-bytes |
| — | — | `sv_resetServer;`（token） | ASCII；FNV-1a = `0x0E88C0A4`… 见注 | EV-0021-05 注释 | C-bytes |
| — | — | `<k> <v>;` 编号对 | ASCII | 同上 | C-bytes |
| — | — | `g_gametype <name>;` | ASCII | 成功轮 | C-bytes |
| — | — | `g_difficulty <n>;` | ASCII（成功 `1`，失败 `0`） | 对比 | C-bytes |
| — | — | `map <name>;` | ASCII | 成功/区间 B/C | C-bytes |
| — | — | `2654 <item>;` | ASCII（成功为空，失败为 `M7-E8S6Client`） | 对比 | C-bytes |
| — | — | `playlist <n>;` | ASCII | 区间 D | C-bytes |
| — | — | `start_map_rotate_once <n>;` | ASCII | 区间 D | C-bytes |
| — | — | `roomChatChannelID <u64>;` | ASCII 十进制 | 全部 | C-bytes |

**证据等级说明**：这些全部是**客户端上行字节**，属于最强的一档；但"字段含义"仍是 INFERRED。

---

## 08. 数据流与调用链

```
[UI: 玩家在房间内点开始]
   │                                        UNKNOWN（未定位产生点）
   ▼
[客户端构造 mmstart 文本]
   │  playlist <n> / start_map_rotate_once <m>   PROVEN（日志里有）
   ▼
[6/14 上行 → 大厅]                          PROVEN
   │
   ▼
[lobby_server mmstart 分支]
   ├─ 正则 map / g_gametype                  PROVEN（本 Issue 的观测点）
   ├─ 两个都空 → 跳过写 coop_map              PROVEN（源码 + 日志 `?`）
   └─ 回 ACK                                 PROVEN
   │
   ▼
[下一轮 21/5 findSessions 使用 coop_map 旧值] PROVEN（源码行 789–849）
   │
   ▼
[客户端拿到 session map=mp_raid]
   │                                        UNKNOWN ← FIRST_UNPROVEN_EDGE
   ▼
[客户端是否据此连战斗服]                     CONTRADICTED（零 RX）
```

---

## 09. 根因分析

| Hypothesis | 解释 | 支持 | 反对 | 状态 | 验证 |
|---|---|---|---|---|---|
| **H1** `playlist <n>` 在本 build 中不足以定位地图 | 客户端只知道自己选了"某个 playlist"，具体地图要服务端决定 | 区间 D 全部是此形态 | 区间 B/C 有 map 也失败 | 中可信 | E2/E3 |
| **H2** `37` 不是官方 ID（官方表 123 项里无 37/50） | 客户端用的是"排序后下标" | 10-28 文档已解出 `50→148`、`37→123` | 未在客户端代码中确认 | 中可信 | 需客户端逆向 |
| **H3** 房间内开始 ⇒ 客户端走"等待房间状态"分支，不会直连 | 见 ISSUE-0009/0012 | 成功轮全部不建房 | 无法分离 | 高可信（未证） | E3 |
| **H4** `g_difficulty 0` 与 `2654 M7-E8S6Client` 是"房间实例"标志 | 这两个字段只在房间内出现 | 与建房完全共变 | 无法分离 | 低可信 | 需要更多字段对照 |

---

## 10. 历史修复尝试

| 时间 | 改动 | 结果 |
|---|---|---|
| 2026-10-07 | `coop_map.txt` 自校正 | 使 10-26 成功（但依赖客户端发 map） |
| 2026-10-28 | 删除"固定四图白名单 / 固定 playlist 默认图" | 使 `mmstart` 变成 `playlist 37`；仍零 RX |
| 2026-10-28 | `playlist` 缺失时抛 `PlaylistSelectionError` | 未观察到该异常触发 |

**为什么没解决**：这些改动都在服务端选择逻辑上，没有改变"客户端发什么"。

---

## 11. 当前代码状态

| 检查 | 结论 | 位置 |
|---|---|---|
| 逻辑是否仍在 | ✅ | `lobby_server.py:1090-1143` |
| 是否有死代码 | `_cmd_txt` 解析在 map/gt 都为空时全部白做 | 同上 |
| 硬编码 | `ROOM_ID`、`GAME_IP`、`GAME_PORT` | 文件顶部 |
| 缺异常处理 | `_map`/`_gt` 为空时无告警级日志（只有 `?`） | 行 1105 |

---

## 12. 精准复现方法

同 ISSUE-0020 §12，但**入口必须是 BOT 房间**（不是剧情）。
预期失败输出：
```
★ mmstart 完整命令: mmstart sv_resetServer; … playlist 37; start_map_rotate_once N; roomChatChannelID …;
★ mmstart 选择: gametype=? map=?
```
`_battle_out.txt` 只有 7 行。

---

## 13. 最小验证实验

**E2**（与 ISSUE-0020 共用）：PvE 直接开局，但把地图换成非 firingrange。
**E3**（与 ISSUE-0020 共用）：房间内开始，但地图保持 firingrange。

本 Issue 还需要一个**独立**实验：

**实验 E4（playlist 语义）**
| 项 | 内容 |
|---|---|
| 变量 | 在同一 UI 位置选择**不同**的播放列表项 |
| 观察 | `playlist <n>` 与 `start_map_rotate_once <m>` 如何变化 |
| 通过判据 | 能画出一张"UI 选择 → playlist 编号"的对照表，且编号能与官方 123 项表对上 |
| 成本 | 2–3 轮 |

---

## 14. 修复方案

**条件式。**

**若 E2 证明地图是根因**：让服务端在 `mmstart` 无 map 时**主动从 `findSessions` 的 playlist 回推一张本地可用地图**，并把该地图写进 `active_room.json`（不依赖下一轮）。

**若 E3 证明入口是根因**：本 Issue 降级为 P2，因为它只是症状。

**前置**：E2/E3 结果。

---

## 15. 修复影响分析

| 面 | 影响 |
|---|---|
| 大厅 | 会改变 `findSessions` 的返回 |
| 战斗连接 | 目标 |
| GameState | `active_room.json` 变 ⇒ `_gs_adapt_dynamic` 变 ⇒ gamestate header 变 |
| 历史成功基线 | 若改动 make `mmstart` 无 map 时仍回 firingrange，不影响 PvE 路径 |
| 多客户端 | 无 |

---

## 16. 验收标准

1. `mmstart` 的 `playlist` 编号有**本 build 的**语义定义（不是从 ol-mod 抄的）
2. 服务端在 `mmstart` 之后能确定唯一地图
3. 该地图与客户端请求的地图一致（可通过 `active_room.json` + `lobby_srv.log` 交叉验证）
4. 与 ISSUE-0020 的验收同时满足

---

## 17. 回归测试

| 测试 | 证明 | 不能证明 |
|---|---|---|
| `test_room_selection.py`（5/5，已存在） | playlist 不改写、缺图失败 | 客户端行为 |
| 新增：mmstart 无 map 时的错误分支 | 服务端不会静默继续 | 客户端会连 |
| E1/E2/E3 | 见 ISSUE-0020 | — |

---

## 18. 最终技术结论

**当前状态**：`OPEN`。`mmstart` 在房间入口下不含 map，服务端解析结果为 `?`。

**已经证明的事实**：
1. `mmstart` 的两种形态在磁盘上有完整字节记录（EV-0021-01/02）。
2. 有 map 的 17 轮同样零 RX ⇒ "没有 map"不是充分原因。
3. 服务端在 `_map` 为空时静默跳过 `coop_map.txt` 写入（源码可读）。

**尚未证明的事实**：`playlist 37` 的真实语义；客户端为何在该入口不发 map。

**第一条未闭合证据链**：客户端选择"发 playlist 而非 map"的判定点。

**当前最可信根因**：`playlist` 编号在本 build 中不足以定位地图，而服务端没有把这个缺口报错。

**下一步最小实验**：E2（地图变量）+ E4（playlist 语义表）。

**最小修复条件**：E2 或 E4 给出确定归因。

**完成验收标准**：§16。

**是否可以交给开发 Agent 直接修复：NO**
必须先完成：**E2 与 E4**。

---

## 19. 修改影响分析

见 §15。

## 20. 可测量的验收标准

见 §16。

## 21. 回归测试方案

见 §17。

## 22. 修复准备度

**INVESTIGATION_READY**

- **下一步**：E2（换地图）+ E4（playlist 编号语义表）。
- **上游依赖**：见 §01
