# NEXT_AGENT_HANDOFF — 可直接接手

> 2026-10-29 · 053 全量交付（92 条 Issue 全部建档）

## 0. 先读这三个数字

- 92 条历史 Issue 全部有独立档案（`ISSUES/`）
- **28 条 `FIX_READY`** —— 服务端内部/工程化改动，可以立刻动手
- **32 条 `INVESTIGATION_READY`** —— 各有一条明确实验，跑完即可推进

关键入口：`FIX_READINESS_MATRIX.csv`（谁可以修、下一步是什么）

---

> 你不需要读任何聊天记录。读完这一页就能开始工作。

---

## 1. 项目真实状态（一句话）

客户端能进大厅、能建房、能解析 usercmd；**但当前不向战斗服发起 UDP 连接**，
所以"进图"这个历史成绩当前无法复现。

---

## 2. 当前最早的阻塞点

**`CODOL-ISSUE-0020`** — 战斗服零收包，客户端从不 connect。

不要从别的地方开始。0025（位置）、0024（实体）、0030（射击）全部在它后面。

---

## 3. 已确认的成功基线

| 基线 | 日期 | 产物 | 关键条件 |
|---|---|---|---|
| 进大厅 | 2026-10-27 | 日志 | `COD OL\iips.ini` 的 `enable_iips=1`；走 `run_frozen_chain_once.py` |
| 战斗连接 | **2026-10-26** | **8 轮日志在盘上** | 见下 |

**10-26 成功轮的完整条件（这是最重要的资产）**：

```
启动根目录 : run_codol_001\sandbox_ifs1_20260923
mmstart    : mmstart sv_resetServer; 2486 0; 3265 18; 2489 0; 2574 0; 2500 0;
             g_gametype coop;  g_difficulty 1; ; map coop_train_mp_firingrange;2654 ;
             roomChatChannelID 0;
房间       : 不创建（11/13 createRoom 计数 = 0）
入口       : PvE 剧情直接开局
```

---

## 4. 当前失败基线

```
mmstart : mmstart sv_resetServer; 2486 1; 3265 6; 2489 1; 2574 2; playlist 37;
          start_map_rotate_once 7; roomChatChannelID 1800154382;
房间     : 创建（自造 room push）
入口     : BOT 房间
结果     : _battle_out.txt 只有 7 行初始化，零 RX
```

---

## 5. 第一个最小实验（就做这个）

**E1：完全复刻 10-26 的成功条件。**

```bash
python -I run_codol_001/run_frozen_chain_once.py --authorize-next-launch
python -I run_codol_001/run_frozen_chain_once.py \
  --game-root "D:/BaiduNetdiskDownload/使命召唤OL/run_codol_001/sandbox_ifs1_20260923" \
  --kit <一份复制的 10-26 成功轮 kit> --seconds 240 --out chain_e1.txt
```

前置：
- 提权 agent 在线：`CODOLServer/logs/elevated_agent.json` 里的 PID 存活
- `kit/coop_map.txt` = `coop_train_mp_firingrange`
- 用户在 UI 上走 **PvE 剧情入口**（不是 BOT 房间）

### 成功判据
`runs/<RUN>/kit/_battle_out.txt` 出现：
```
[battle] TX_NAT_REPLY 29B
```

### 失败判据
240 秒后仍只有 7 行初始化（无任何 `TX_` / `RX_`）。

### 成功后立刻做（不要等）
1. 抓包（`dumpcap` / `pktmon`），保存到 run 目录
2. 用 `CODOLServer/_mainline/dump_earliest.py <outdir> 200 6` 抢转储

这两份产物是本项目**从未有过**的东西，能一次解锁 0012、0041、0078。

---

## 6. 然后做 E2 / E3

| 实验 | 只改 | 若零 RX 说明 |
|---|---|---|
| E2 | 地图换成 `coop_training_mp_cargoship` | **地图是根因** |
| E3 | 入口换成 BOT 房间 | 入口是根因 |

判据表见 `CONNECTION_REGRESSION_DIFFERENTIAL.md §6`。

---

## 7. 关键源码入口

| 文件 | 行 | 作用 |
|---|---|---|
| `CODOL_VERIFIED_GOLDEN_20261019/lobby_server.py` | 1090–1150 | mmstart 解析 + coop_map 自校正 |
| 同上 | 789–849 | findSessions 选图 |
| 同上 | 1002–1010 | 11/13 createRoom（memberCount） |
| 同上 | 1181–1226 | 102/7（val 恒 0） |
| `CODOL_SERVER_319_20261021/src/battle/battle_service.c` | 1061–1140 | UDP 唯一入口 |
| 同上 | 421–591 | send_snapshot |
| 同上 | 374–409 | send_gamestate |
| `CODOL_SERVER_319_20261021/src/main.c` | 157–175 | 主循环 |

---

## 8. 关键客户端地址（3.19 / 1649370，ImageBase 0x400000，无 ASLR）

| 语义 | VA | RVA |
|---|---|---|
| CA 状态 值→名 映射 | `0x005C8060` | `0x1C8060` |
| `MyEventHandler` vtable | `0x00DC78F0` | `0x9C78F0` |
| 建房回调 | `0x0063B500` | `0x23B500` |
| `dwRoomMatchUber` vtable | `0x00DC795C` | `0x9C795C` |
| 自动开局状态机 | `0x0063C5E0` | `0x23C5E0` |
| `dwRoomImp` vtable | `0x00DC7274` | `0x9C7274` |
| 创建 dwRoomMatchUber | `0x0063E510` | `0x23E510` |
| 房间信道 handler | `0x006371F0` | `0x2371F0` |
| 房间消息分发表 | `0x00636f3c` | `0x236f3c` |
| 位流 writeBits | `0xB77B10` | `0x777B10` |
| 位流 readBits | `0xB774E0` | `0x7774E0` |

⚠️ 所有地址只对 **3.19 主 EXE** 有效；主 DLL 的地址未在此列出。

---

## 9. 关键日志位置

```
run_codol_001/runs/<RUN_ID>/kit/lobby_srv.log     ← 大厅全部交互（最重要）
run_codol_001/runs/<RUN_ID>/kit/_battle_out.txt   ← 战斗服 RX/TX
run_codol_001/runs/<RUN_ID>/chain_*.txt           ← 客户端启动过程（第 1 行有 --root）
run_codol_001/runs/<RUN_ID>/preflight.json        ← 受保护基线哈希
```

**最好的一份参考日志**：`runs/ONCE_20261026_220815/kit/_battle_out.txt`（成功全链路）。

---

## 10. 最高优先级 Issue

1. `CODOL-ISSUE-0020` — 零收包（唯一总开关）
2. `CODOL-ISSUE-0021` — mmstart 地图（0020 的自变量）
3. `CODOL-ISSUE-0010` — 房间下行（若走房间入口必需）

---

## 11. 不得破坏的历史成果

| 项 | 原因 |
|---|---|
| `REF_LOBBY_KIT/**` | AGENTS.md 规定的受保护原件，只读 |
| `CODOL_VERIFIED_GOLDEN_20261019/**` | 工作基线，改动需记录 |
| `run_codol_001/run_frozen_chain_once.py` | 唯一启动入口 |
| **快照索引编码 = 4 位 / 步长 15** | 改 7 位立即卡死（历史事故） |
| **idx61 = 2047** | 改 2046 立即飞行模式 |
| **不按参照重写编码器** | 已实测会卡住（`REFENCODER_*`） |
| `omit = snapshot_sent` | 改成就每帧发位置已验证无效且会拉扯 |
| 10-26 的 8 个成功 run 目录 | **唯一的成功物证**（不要清理） |

---

## 12. 执行顺序（照做）

1. 读 `CONNECTION_REGRESSION_DIFFERENTIAL.md`（10 分钟）
2. 跑 E1
3. E1 成功 → **立刻**转储 + 抓包 → 再跑 E2
4. E1 成功 → 记录一条 `TX_NAT_REPLY` 的时间戳与客户端 PID
5. E2 若零 RX → 地图是根因 → 读 `INVESTIGATION_PACKAGES/CODOL-ISSUE-0021/`
6. E2 若有 RX → 跑 E3 → 入口是根因 → 读 `INVESTIGATION_PACKAGES/CODOL-ISSUE-0009/`

**不要**在拿到 E1/E2 结果之前修改 `lobby_server.py` 的任何地图相关逻辑。

---

## 13. 如果 E1 就失败

那说明**连历史成功都复现不了**，此时：
1. 不要做 E2/E3
2. 对比 E1 与 `ONCE_20261026_220815` 的每一项（§3 的 6 个条件）
3. 优先怀疑：沙箱是否还在、`iips.ini` 是否被改回、提权 agent 是否换了
4. 把差异写进新的 run 目录的 `RESULT.md`

在这种情况下，"地图 vs 入口"的归因实验必须暂停，先修环境。
