# 最终修复评估

> 056 任务：大厅业务流程正式修复工程。本文档是任务的最终状态评估。

---

## 一、任务范围回顾

056 的范围明确限定为：**大厅及其战斗连接交接层**。不修改战斗服内部 GameState、Snapshot、移动、碰撞、武器、伤害系统。

## 二、完成的阶段

### R0：保护历史成功基线 ✅ 完成

- 所有关键文件 SHA-256 已计算并记录（[R0_BASELINE_MANIFEST.json](R0_BASELINE_MANIFEST.json)）
- 客户端 3.19 / build 1649370 身份确认
- 历史成功 Kit（10-26）与当前 Kit 差异已逐项比对
- GOLDEN 清单与实际 `lobby_server.py` 不一致已识别并记录
- 无 Git 环境，采用 `PATCHES/baseline` 原件 + 哈希清单 + 独立 Kit 作为回滚机制

### R1：恢复 PvE 大厅启动路径 ⚠️ PENDING_LIVE_VALIDATION（根因已定位，不可在范围内修复）

**五次实机验证结果：**

| Run | 路径 | 结果 |
|---|---|---|
| 114237 | 房间 B1（cargoship） | 战斗服零 RX |
| 120141 | 候选修复，未走到选单 | 零 RX |
| 121002 | GOLDEN，房间 B1 ×2 | 零 RX |
| 121352 | GOLDEN+地图覆盖，房间 B1 ×2 | 零 RX |
| 122010 | 最终日志版，房间 B1 ×2（cargoship + fav_tropical） | 零 RX |

**根因定位（2026-10-29）：**

PvE 剧情路径的断点**不在大厅/战斗服协议**，而在**客户端资产缺失**：

- `COD OL/main/video/` 目录缺少 `coop_train_mp_firingrange_load.bk2` 和 `coop_training_mp_cargoship_load.bk2`
- 审计清单 `CODOL_ANALYSIS_20261020/AUDIT_FIRST_ROUND_CLASSIFIED.csv` 中无任何 firingrange/cargoship 的 `.bk2` 记录
- 目录枚举确认存在的是其他剧情关的 `_load.bk2`（hunted_spring、suburbs、crash_tropical 等）
- 客户端在 `CA_LOADING` 前尝试播放 `<地图名>_load.bk2`，文件缺失 → 停在"战斗开始"
- 与 `docs/PVE_STUCK_INVESTIGATION_20261027.md` 一致：**客户端从不连 28960，对局本身不需要服务器，但进剧情需要本地视频文件**

**阶段日志已实现：**
- `LOBBY_MODE_SELECTED` / `LOBBY_FIND_SESSIONS` / `LOBBY_MMBOOK_RECEIVED` / `LOBBY_MMBOOK_RESPONDED` / `LOBBY_MMSTART_RECEIVED` / `LOBBY_MMSTART_PARSED` / `LOBBY_BATTLE_ENDPOINT_ASSIGNED` 全部接入
- 包含 ISO 时间戳、session、playlist/map/mode、room ID、客户端地址、真实请求 seq
- 不记录敏感令牌或密钥

**候选协议修复（隔离，未固化）：**
- coop GameType `0x1000003`（与历史成功轮一致）
- 显式 coop 地图采用对应 maxPlayers
- 4 项离线单元测试通过（PvE/BOT 路径区分、选单对象、预约/开始日志、房间 ID 清理）
- **未获实机验证，未写入冻结基线**

### R2–R6：未开始 ❌

- R2 房间创建初始化、R3 下行事件、R4 准备/开始、R5 战斗交接、R6 回归均未进入
- 原因：R1 未完成，且 R1 的阻塞根因超出 056 范围

## 三、系统性缺损全景

用户诊断"整套大厅房间战斗部分严重缺损"是准确的。缺损清单：

| 层 | 缺损 | 证据 |
|---|---|---|
| **客户端资产** | firingrange/cargoship 剧情 `_load.bk2` 缺失 | 审计清单 + 目录枚举 |
| **大厅-房间** | 成员列表协议未实现（只回 memberCount 标量） | 055 §05 |
| **大厅-事件** | 20 个 MM 事件推送服务端零推送；自造推送从未证明被客户端解析 | 055 §07 |
| **大厅-准备** | 准备按钮点击无任何网络上行（Flash/Scaleform 层不可达） | 055 §06 |
| **大厅-开始** | mmstart 后客户端不建 UDP socket（路径 B） | 056 R1 五次实机 |
| **战斗交接** | 纯 PvE 路径依赖缺失的视频资产 | 056 R1 根因 |

## 四、可交付物清单

- [R0 基线完整性](R0_BASELINE_INTEGRITY.md) / [R0 清单 JSON](R0_BASELINE_MANIFEST.json)
- [基线清单摘要](02_BASELINE_MANIFEST.md)
- [PvE 修复记录](03_PVE_REPAIR.md)
- [未解决阻塞](09_UNRESOLVED_BLOCKERS.md)
- [离线测试](TESTS/test_lobby_lifecycle.py)（4/4 通过）
- [哈希清单](SHA256SUMS.txt)
- [证据索引](EVIDENCE/R1_LIVE_RUN_INDEX)
- 隔离补丁：`PATCHES/work/lobby_server.py`（未固化）
- 冻结候选 Kit：`run_codol_001/kit_R1_PVE_CANDIDATE_20261029`、`kit_R1_PVE_FINALLOG_20261029`

## 五、结论

056 任务在 R0 完成、R1 根因定位后，**因 PvE 剧情路径依赖的客户端视频资产缺失而无法继续**。该缺失超出 056 任务范围（大厅+战斗交接层），需要客户端资产补全或重新定义 R1 目标。

**建议路径：**
1. **转入 R2-R5（房间路径）**：房间路径已有多次实机证据（createRoom/setRoomData/mmbook/mmstart 全部走通），不依赖 PvE 视频资产。这是 056 范围内可继续推进的唯一路径。
2. **补客户端资产**：从外部来源获取 firingrange/cargoship 的 `_load.bk2` 文件，恢复 PvE 剧情路径。这超出 056 范围，需单独任务。

未获用户指示前，不擅自选择路径。
