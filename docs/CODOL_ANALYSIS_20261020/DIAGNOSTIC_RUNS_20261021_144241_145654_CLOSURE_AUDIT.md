# 2026-10-21 诊断运行封口审计

日期：2026-10-21（Asia/Shanghai）

范围：run_codol_001/runs/ONCE_20261021_144241 与 run_codol_001/runs/DIRECT_20261021_145654。

状态：THIRD_ROUND_STARTED_NON_CONCLUSIVE / DIAGNOSTIC ONLY / P0 0/11 / WIRE AND PLAYABILITY BLOCKED / CLEANUP CONFLICT。

本报告不接受这两段运行作为第三轮正式样本。没有启动客户端、dumpcap、Auth、Lobby、Battle 或任何测试进程。

## 0. 结论摘要

| 项目 | 结论 |
|---|---|
| 第三轮开放审查 | 可启动；只能做非闭合证据分析 |
| P0 | 0/11 |
| 诊断价值 | 预启动抓包、Auth/Lobby 可达、mmbook accepted、28960 监听均可复核 |
| 失败边界 | 无 mmstart、无战斗 UDP、无 map/gamestate/snapshot/ACK/consumer |
| 镜像 | OpenProcess 阻断；未做全页轮询 |
| FF | 仍只有历史 block-0，无 layer-2 世界资产 |
| 2697 | 原始包仍缺失 |
| 清理 | 发现残留 Python 服务进程与端口监听，收口声明与现场不一致 |

## 1. ONCE_20261021_144241：受控抓包顺序诊断

这是先抓包、后启动的受控诊断，不是同 PID 战斗样本。

| 项 | 结果 |
|---|---|
| 抓包 live proof | 2026-10-21T14:42:42+08:00 |
| 客户端创建 | PID 9964，14:42:53 |
| Auth TLS 请求 | 14:43:15 |
| 客户端退出 | 14:46:57 |
| 单次启动 | 是 |
| 自动重启 | 否 |
| 保留游戏流 | 445 帧 TCP/3074，其中 220 帧有载荷 |
| UDP/28960 | 0 帧 |
| gamestate/configstrings | 未捕获 |
| snapshot/游戏 ACK | 未捕获 |
| consumer trace | 未捕获 |
| 镜像 | PID 9964；OpenProcess 错误 5；全页扫描未执行 |

内部哈希清单：

- hashes.sha256 共 414 条；
- 逐项复算 414/414 可读、0 缺失、0 不匹配；
- network/packets.game.pcapng：551,840 B，SHA-256 800CC34A2C1EE7FEA5A5AFF4B90514EC63586633AC4D293366A32DCAC17FFD8。

它证明了抓包可以早于客户端创建，也证明了同一 PID 的 Auth/Lobby TCP 流可以保留。它不能证明战斗通道，因为没有实际进入战斗。R3-A03 仅部分改善；R3-A11 仅到 session-selection；R3-A01 仍为 ACE 后阻断。

## 2. DIRECT_20261021_145654：booking 生效后的诊断

这是 mmbook accepted 所属运行。它没有自带 hashes.sha256，本审计已独立生成：

- DIAGNOSTIC_RUNS_20261021_DIRECT_145654_INVENTORY.csv
- DIAGNOSTIC_RUNS_20261021_DIRECT_145654_INVENTORY.summary.json

独立盘点：434 个文件、112,934,300 B。

### 2.1 booking 与 Lobby

- Lobby 初始为 session=True、booking=False、battle=False；
- 后续出现 20 次 push mmbook accepted(data=20)；
- mmstart 出现次数为 0；
- 客户端仍反复进入 findSessions；
- booking 后 Lobby 连接多次断开并重新建立，伴随新 challenge 和会话密钥；
- 这符合“booking 开关后来生效，但客户端仍停在搜寻服务器”的描述。

该证据只能证明客户端收到了 booking accepted 推送，不能证明客户端消费了战斗端点、准备进入地图、执行 mmstart 或发起战斗 UDP。

### 2.2 战斗服监听与零收包

kit/battle_srv.log：

- 14:57:19 启动 0.0.0.0:28960，PID 15676；
- 明确记录已监听 UDP 0.0.0.0:28960；
- 从 14:57:49 到 15:04:49 连续 16 次收包=0；
- NAT、init、keyex、data、session 全部为 0。

独立解析 network/packets.raw.pcapng：

| 项 | 结果 |
|---|---:|
| 文件字节 | 72,379,752 |
| SHA-256 | 0F01E00D987FAF3C562EC6181A05E412546E850FAE064465010E2297CC076351 |
| pcapng 包数 | 66,120 |
| IPv4 / IPv6 | 66,027 / 11 |
| UDP / TCP | 844 / 64,964 |
| TCP/3074 | 1,980 |
| UDP/28960 | 0 |
| 其他/非 IP | 82 |

战斗服监听是本地实现层事实；客户端没有发送战斗 UDP 是同一时段负证据。两者不能合并成协议兼容。

### 2.3 PID 与同会话边界

该 run 内同时存在两个身份：

- chain.txt：客户端 game pid=1764，记录为第 1 次启动，约 8 秒后退出；
- network/live_capture_meta.json：Pid=14736，ProvenLive=true。

run 中没有对应的第 2 次启动记录、PID 14736 的完整客户端链或连续事件日志。不能把 1764 与 14736 拼成同 PID 会话；用户所述 PID 重启与现场数据一致，但 run 本身没有完整记录重启过程。因此该 run 只能作为诊断性负证据。

## 3. 当前残留进程与端口冲突

在 2026-10-21T15:09:39.154+08:00 做只读核对，发现：

| 进程 | 启动时间 | 端口 |
|---|---|---|
| Python PID 15676 | 14:57:19.416 | UDP 0.0.0.0:28960 |
| Python PID 1624 | 14:57:19.413 | TCP 127.0.0.2:3074 |
| Python PID 17536 | 14:57:19.410 | TCP 127.0.0.1:3074 |
| Python PID 16472 | 更早 | 未发现相关监听 |

命令行为空，不能从 CIM 进一步显示完整启动参数；但 PID 15676 与 DIRECT run 的 battle 日志启动 PID 完全一致，两个 3074 监听也与 Auth/Lobby 启动时间一致。

因此“当前无客户端、dumpcap、Auth/Lobby/Battle 服务或 3074/28960 端口占用”与现场不符：未发现客户端或 dumpcap，但 Auth/Lobby/Battle Python 残留仍在，UDP 28960 仍被占用，TCP 3074 的两个监听仍在。

这会阻止干净的新 run，也可能让下一轮发生端口冲突或把旧服务流量误认成新会话。清理必须由用户明确授权并在受控方式下完成；本审计没有杀进程。

## 4. P0 状态复核

| 项 | 本次诊断贡献 | 状态 |
|---|---|---|
| R3-A01 | 一次 OpenProcess 阻断，无全页扫描 | 仍开放 |
| R3-A02 | 无 payload → dispatcher 结论 | 仍开放 |
| R3-A03 | Auth/Lobby 可达；无战斗 UDP | 仍开放 |
| R3-A04 | 无 gamestate/configstrings | 仍开放 |
| R3-A05 | 无 snapshot/游戏 ACK | 仍开放 |
| R3-A06 | 无 consumer trace | 仍开放 |
| R3-A07 | 无 layer-2 导出 | 仍开放 |
| R3-A08 | 无 Pmove/trace 新证据 | 仍开放 |
| R3-A09 | 无规则链 | 仍开放 |
| R3-A10 | 2697 原始包仍缺失 | 仍开放 |
| R3-A11 | booking accepted 可见；无端点消费/连接 | 仍开放 |

P0 = 0/11。机器门禁 JSON 不需要改写；需要新增的是诊断负证据和清理冲突。

## 5. 为什么仍不能宣布第三轮闭合

第三轮可以继续启动开放证据审查；但即使 booking accepted 和 28960 监听同时存在，要宣布协议或可玩性闭合仍缺少：

1. 同一 PID 从启动前到退出的连续时间线；
2. 实际进入战斗；
3. 双向战斗应用载荷；
4. gamestate/configstrings；
5. 至少两帧 snapshot 与游戏 ACK；
6. consumer trace；
7. 可读镜像；
8. layer-2 世界资产。

第 1、2、3 项决定证据强度，缺失只降低结论置信度，不阻止第三轮分析开始；之后各项也不能从当前日志反推成闭合证据。

## 6. 下一轮操作前置条件

1. 仅使用新的 run 目录，不复用 ONCE_20261021_144241 或 DIRECT_20261021_145654。
2. 在任何新启动前，由用户明确清理或接管残留 Python 进程，并确认 3074/28960 无旧监听。
3. 先启动并证明 dumpcap_live，再单次启动冻结链。
4. 从 PID 创建到退出保持同一 PID；一旦发现 PID 变化，立即停止并把该 run 标为诊断失败。
5. 必须实际进入战斗，并同时取得 gamestate/configstrings、两帧 snapshot、游戏 ACK 和 consumer trace。
6. 镜像先证明可读，再分页采集；ERROR_ACCESS_DENIED 不得重试成全页轮询。
7. booking accepted 只能登记为 Lobby 事件，不能登记为战斗端点已消费。
8. FF layer-2 和世界资产必须独立完成，block-0 不能替代。

## 7. 证据入口

- ONCE_20261021_144241/capture_manifest.json
- ONCE_20261021_144241/RUN_RESULT.md
- ONCE_20261021_144241/hashes.sha256
- DIRECT_20261021_145654/chain.txt
- DIRECT_20261021_145654/kit/lobby_srv.log
- DIRECT_20261021_145654/kit/battle_srv.log
- DIRECT_20261021_145654/network/live_capture_meta.json
- DIRECT_20261021_145654/network/packets.raw.pcapng
- DIAGNOSTIC_RUNS_20261021_DIRECT_145654_INVENTORY.csv
- DIAGNOSTIC_RUNS_20261021_DIRECT_145654_INVENTORY.summary.json
- THIRD_ROUND_BLOCKER_STATUS_20261021.json
- THIRD_ROUND_BLOCKER_STATUS_AUDIT_20261021.md
