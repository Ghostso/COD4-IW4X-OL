# RUNTIME_VALIDATION_PLAN — 运行验证计划（阶段 C，2026-10-09）

本文件定义从“协议 fixture”到“两个真实客户端 gameplay”的分阶段验收方案。
**本文件只定义方案，不代表任何一步已经通过。** 当前实际推进阶段见 NEXT_STAGE_STATUS.md。

---

## 1. 证据等级（统一使用）

| 等级 | 含义 |
| --- | --- |
| CONFIRMED | 有可复核的一手证据支持 |
| STRONG_CANDIDATE | 较强间接证据，仍缺关键验证 |
| CANDIDATE | 合理候选，尚未充分验证 |
| UNKNOWN | 证据不足 |
| REFUTED | 已被更可靠证据否定 |
| NOT_OBSERVED | 本次观察中没有观察到该事件 |
| INSTRUMENTATION_BLOCKED | 因工具、客户端、资产或采集能力不足，无法完成验证 |

---

## 2. 十级验证阶梯（禁止跨级推导）

每一级必须**独立成立**，并且只有在上一级已成立时才可能成立。**不得把前一项的成功直接推导成后一项成功。**

| # | 验证项 | 判据（必须可机械复核） | 达成标记 |
| --- | --- | --- | --- |
| 1 | 源码中存在对应实现 | 具体 file:line 可指认，且该符号出现在真实调用路径上（非死代码） | （无标记，仅前置） |
| 2 | 协议 fixture 验证字节/解析行为 | 仓库内已提交的捕获字节 fixture 与解析断言一致 | （无标记，仅前置） |
| 3 | 单元测试**实际执行**并通过 | 构建成功 + 测试二进制运行 + 退出码 0 + 测试日志留存 | PROTOCOL_TESTS_PASSED |
| 4 | 服务端成功构建 | 构建退出码 0 + 构建日志 + 产物路径与 SHA-256 | BUILD_CONFIRMED |
| 5 | 客户端成功连接 | 服务端日志出现该客户端 slot 进入 Connected + 客户端 connection_state 证据 | CLIENT_CONNECT_CONFIRMED |
| 6 | 客户端接受 gamestate | 客户端上报 gamestateupdate 6 且 server slot 进入 Active（原始日志，非总结） | GAMESTATE_ACCEPTED_CONFIRMED |
| 7 | 客户端生成游戏世界 | 客户端完成 level-zone load + world 渲染证据（截图 + 日志） | （并入 8） |
| 8 | 可验证的 world spawn | 服务端记录 SV_ClientSpawn 提交 + 客户端 origin/眼高读回，且 generation/sequence 一致 | WORLD_SPAWN_CONFIRMED |
| 9 | 持续发送/接收快照 | 原始 netchan trace 显示 snapshot 持续 + ACK 增长 + parser overflow 为 0 | SNAPSHOT_FLOW_CONFIRMED |
| 10 | 两个真实客户端同局持续交互 | 两个不同 XUID、两个 slot 同时 active、两端快照与交互（移动/开火）均可观测 | TWO_CLIENT_GAMEPLAY_CONFIRMED |

### 前置条件级（必须在 3-4 之前成立）
| 标记 | 判据 |
| --- | --- |
| AUDIT_BASELINE_COMMITTED | 审计包已提交且哈希可复核 |
| CLIENT_HASH_VERIFIED | 客户端 EXE SHA-256 == E3823FD6...（或明确记录为另一构建并记录其哈希） |
| ASSET_SET_VERIFIED | 完整游戏资产集存在，且与目标构建同源、含所需地图 .ff |

---

## 3. 防混淆规则（本计划的重点）

以下等式**全部不成立**，不得作为通过依据:

1. **50 ms snapshot cadence != 20 Hz server frame。** 二者是两个不同的率:
   - 快照发送节拍: sv_client_mp.cpp:1424-1426 hardcode 50 ms，且带 `TODO(CODOL)`，属 [SRC] 非已恢复契约；sv_client_mp.cpp:1418-1421 对 **LAN/loopback peer 直接旁路**该节拍。
   - world frame 间隔: sv_main_mp.cpp:1074 默认 100 ms（10 Hz）。
   - 因此本地 loopback 观察到的快照频率**不能**作为 CODOL 远程客户端速率契约的证据。每次运行必须记录 peer 被判为 LAN 还是 remote。
2. **协议 fixture != 真实 gameplay。** ServerCoreTests.cpp:27314-27391 / :27502-27555 证明字节解释正确，不证明自然对局跑通。
3. **源码存在 != 运行路径已被执行。** 需要独立日志/产物证明该分支确实被执行。
4. **文档记录的快照数量、accepted/rejected 数值及 checksum（如 1201 / 1743 / 0 / 0xF7E89911）在无原始产物时不能认定为已复现。**
5. **测试“设计了” != 测试“执行了”。** 未实际运行测试二进制前，测试只能记为 NOT_OBSERVED / INSTRUMENTATION_BLOCKED。

---

## 4. 运行时证据目录规范

每次运行使用**唯一标识**，建议: `<artifact-root>/runs/<YYYYMMDD_HHMMSS>-<短标签>/`

禁止只保留人工总结。**必须保留原始日志。**

### 4.1 必备内容
| 类别 | 内容 | 来源 |
| --- | --- | --- |
| 身份 | 客户端 EXE 路径/大小/SHA-256；若用 OLfinal 则 out.exe 同样记录；服务端 DLL 各自 SHA-256 | 运行前采集 |
| 构建 | 构建配置 + 构建日志 + 退出码 + 产物路径与 SHA-256 | 构建阶段 |
| 配置 | config/codol-game-dir.txt、OLMOD_* 环境变量全集、启动命令行、PID | 启动前/后采集 |
| 服务端日志 | Ayria/Logs/CodolGameServer.log（原始全文） | 运行中 |
| 客户端日志 | 客户端侧日志与 connection_state 记录 | 运行中 |
| 原始 PCAP | 若条件允许，dedicated UDP 端口与客户端之间的原始抓包 | 运行中 |
| 阶段时间戳 | 每次状态转换的时间戳与前后状态 | 编排器 |
| 原始统计 | 每个统计量的**生成方式**（哪个工具、哪个字段），而非仅数值 | 编排器 |
| summary.json | 运行总结（含 evidence_level） | 编排器 |
| 哈希清单 | 上述**全部文件**的 SHA-256 清单 | 运行后 |

### 4.2 与既有工具的关系
可复用仓库已存在的编排器与其产物名（见 .agents/modules/runtime.md、tools/runtime/CodolNaturalMatchTrace.py:358-377）:
summary.json / netchan_trace.jsonl / server_samples.jsonl / frame_trace.jsonl + frame_trace.summary.json /
dedicated_asset_trace.jsonl / cbuf_commands.jsonl / viewmodel_trace.json / input_scenario.snapshot.json。

**注意**: `.runtime/` 被 .gitignore:4 忽略，历史上导致全部成功声明永久不可核验。运行证据**不得只放在 .runtime 下**，必须复制到受版本管理或独立备份的位置并生成哈希清单。

### 4.3 PCAP
当前仓库**无任何 PCAP 工具**（grep pcap/wireshark/npcap/scapy = 0 命中）。若本轮无法采集，必须在 summary 与 MANIFEST 中显式写 `pcap: NOT_CAPTURED` 并说明原因，**不得留空或省略**。

---

## 5. 运行前置检查清单（每次运行前逐项确认）

1. CLIENT_HASH_VERIFIED 成立（否则 BLOCKED_NO_MATCHING_CLIENT，停止）。
2. ASSET_SET_VERIFIED 成立（否则 BLOCKED_NO_VERIFIED_ASSET_SET，停止）。
3. BUILD_CONFIRMED 成立（否则停止）。
4. PROTOCOL_TESTS_PASSED 成立（否则停止）。
5. 上一轮证据已归档并生成哈希。
6. clean launch（不复用已在局内的进程）。
7. 记录 peer 的 LAN/remote 判定。

---

## 6. 阻塞时的行为

若任一前置未满足:
- **记录阻塞原因**，写明缺失项与判定依据；
- **不得**创建伪造的成功日志或 summary；
- 不得用强制路径（frida-forced / client-native-forced / synthetic protocol client）冒充自然链路；
- 强制运行的产物可以作为附带证据保存，但必须明确标注证据等级，且**不得**用于创建 Golden Copy。

---

## 7. 通过依据的形式要求

每次宣称某级通过时，必须同时给出:
- 该级判据对应的**原始文件路径**；
- 该文件的 **SHA-256**；
- **复现该结论的命令或步骤**；
- 对应**证据等级**。

**不得仅以 Markdown 中写有 PASS 作为通过依据。**
