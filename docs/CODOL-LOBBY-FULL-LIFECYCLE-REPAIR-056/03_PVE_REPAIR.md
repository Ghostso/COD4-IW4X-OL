# R1 PvE 路径恢复

状态：**★ 2026-10-29 突破——目标路径已确认为"训练"入口；大厅→战斗交接可用。**
（训练地图的碰撞问题属战斗服内部，按 056 边界另行处理。）

## ★ 结论（2026-10-29，实机 + 逆向双证）

**"客户端从不连 28960"只发生在房间路径与 PvE 面板（队伍玩法）上；从"训练"入口进，客户端能正常进入对局。**

证据链（全部本地逆向，见 [16_W35_UI_TO_BACKEND_CHAIN.md](16_W35_UI_TO_BACKEND_CHAIN.md)）：

1. 根模式分派器 `0x0073F8C0` 的 7 项跳表 + 面板建立代码 `0x0073DFCA` 给出映射：
   **0=pvpPanel、1=pvePanel、2=battleCity、3=warGod、4=roomPanel、5=（无面板，训练）、6=theatre**。
2. `OnRootModeClick` 里 `cmp eax,5` 的**唯一分支**就是调 UI 的 `CPP_OnTraining`
   （`CPP_OnTraining` 串全镜像只有这一处引用，0x0073FA2F）。
3. 10-26 八轮成功的 mmstart 是 `map coop_train_mp_firingrange`（`train`=训练）、`roomChatChannelID 0`。
4. 客户端内存里有三条 mmstart 模板：`0x00DC6800`（带 map+难度=**成功形态**）、
   `0x00DC6888`（带 post_options）、`0x00DC6948`（带 playlist=房间形态）。
5. PvE 面板对应的 playlist 10 是 `Survival Normal`，定义 `minparty 1 / maxparty 6` ⇒ **队伍玩法，
   客户端为它建房是预期行为**——这就是"选剧情任务却建房"的原因，不是缺陷。

⇒ **要进入对局，走"训练"入口（根模式 5）；PvE 剧情/生存列表是队伍玩法。**

## 剩余（不属 056 范围）

训练地图**碰撞不对**（穿地/悬空/撞不到墙）：战斗服 `CODOL_SERVER_319_20261021` 的碰撞表
由 `tools/export_clipmap_zone.py` 从 `coop_train_zone.bin` 生成（29 个 box，见
`src/world/collision.c:25-29`），需与客户端实际所用地图的几何对齐。属战斗服内部，
056 边界外。

---

## 历史记录（R1 早期五次实机，结论仍有效）

状态：**PENDING_LIVE_VALIDATION**（当时未复现纯 PvE A 路径）。

## 本轮实际测试

| Run | Kit / 唯一变化 | 实际客户端路径 | 战斗服 UDP |
|---|---|---|---|
| `run_codol_001/runs/ONCE_20261029_114237` | 当前 GOLDEN 复制件；预置 `coop_train_mp_firingrange` | `createRoom → findSessions(10,cargoship) → mmbook → mmstart(cargoship, roomId≠0)` | 仅 7 行初始化，零 RX |
| `run_codol_001/runs/ONCE_20261029_120141` | 候选日志 + coop GameType 修复 + firingrange 地图覆盖 | Bootstrap 后出现 `ChannelSubscriptionFail`；无 findSessions；随后客户端重连 | 零 RX |
| `run_codol_001/runs/ONCE_20261029_121002` | 当前 GOLDEN；无地图覆盖 | 两次 `createRoom → findSessions(10,cargoship) → mmbook → mmstart(cargoship, roomId≠0)` | 零 RX |
| `run_codol_001/runs/ONCE_20261029_121352` | GOLDEN + 仅 `coop_map.txt=firingrange` | 客户端仍选 cargoship；两轮 mmstart；房间 ID 非零 | 零 RX |
| `run_codol_001/runs/ONCE_20261029_122010` | 最终阶段日志 + coop GameType 修复 | 两轮 `createRoom → findSessions(10,cargoship) → mmbook → mmstart`；请求 58–60 / 67–69 | 零 RX |

五次启动均通过既有冻结链、每次一个客户端、每个独立 Run ID。启动前使用独立清单，REF `verify-only` 最后通过。两次启动器因前一轮残留 3074 拒绝时，没有创建客户端；已按 PID 经提权 Agent 清理本轮 Auth/Lobby/Battle 服务。

## 关键结论

1. 2026-10-29 E1 是 BOT/B2，无 mmbook/mmstart，不能用来证明 PvE 回归。
2. 本轮 UI 操作产生的是 B1 房间路径，不是成功轮 A 路径。与历史 A 路径相比，存在 `createRoom`、`roomChatChannelID≠0`、cargoship、编号字段等多处共线差异。
3. 10-26 成功轮的 `findSessions` 回 cargoship，但客户端 mmstart 自选 firingrange 且成功。这直接否定“findSessions 回包地图必须与 mmstart 相同才能连接”的旧推断。
4. `mmbook accepted` 后继续 mmstart 在本轮仍成立。断点在 mmstart 接收/解析之后、客户端 UDP 首包之前，尚不能归因于单个服务端字段。
5. 候选轮未走到选单，不能验证 coop GameType 修复，也不能将其列为通过或回滚依据。
6. 后续最终日志版本已走到两轮 mmstart，仍未产生 UDP；故 coop GameType 修复**未能修复该 B1 房间路径**，保持未验收，未写入冻结基线。

## 已实施（隔离工作区，未固化）

- `PATCHES/work/lobby_server.py`：阶段日志（ISO 时间、session、playlist/map/mode、room ID、客户端地址、请求 seq）及按连接的轻量业务元数据；不记录 booking 文本、密钥或票据。
- 候选协议变化：coop 使用 GameType `0x1000003`，显式 coop 地图采用对应 maxPlayers；**未获实机验证，不作为完成修复**。
- 已冻结候选：`run_codol_001/kit_R1_PVE_CANDIDATE_20261029`，SHA 以 Run `120141` 的 postflight 为准。后续工作副本增加真实请求序号，与该冻结候选不是同一版本。
- `TESTS/test_lobby_lifecycle.py`：4 项 unittest 全通过，覆盖真实 PvE 请求对象、BOT 路径不继承 PvE 地图、预约/开始日志、房间 ID 清理。该结果只是离线单元/序列化测试，不是官方客户端验收。

## 未闭合与下一步

必须先通过正常 UI 进入成功轮对应的 firingrange PvE 剧情任务（mmstart `map=coop_train_mp_firingrange`、roomChatChannelID=0），否则不能对 PvE A 路径做单变量判断。服务端日志不能决定 UI 入口；禁止硬编码伪造该客户端状态。

在正确 A 路径出现后，才分别验证 GameType、MaxPlayers、mmstart 应答和战斗 UDP 首包。R2–R6 尚未开始；不得把本轮 B1 结果冒充完整大厅回归。
