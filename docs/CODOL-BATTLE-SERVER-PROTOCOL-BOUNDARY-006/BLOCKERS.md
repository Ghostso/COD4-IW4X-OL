# 阻塞登记

## BLK-006-01 — 3.9.9.7 样本身份缺失

- 结论：工作区没有可归属于 3.9.9.7 的客户端二进制、运行时 dump 或抓包。
- 当前证据：`14_SERVER_KNOWLEDGE_ATLAS_001\00_SAMPLE_MATRIX.md:43-47` 只登记 1.1.1.13、3.3.3.3、2.6.9.7；`3.9.9.7` 仅出现在四份任务报告的“目标版本”行。
- 为什么阻塞：所有目标版本函数地址、包长和字段序都不能归属。
- 最小解除证据：目标客户端 SHA-256、FileVersion/版本资源/manifest，以及该映像的入口/模块信息。
- 优先级：P0。

## BLK-006-02 — 3.9.9.7 客户端到服务器的真实抓包缺失

- 结论：没有目标版本“客户端连接外部服务器并进入战斗”的 pcap、UDP 字节或运行时 socket trace。
- 为什么阻塞：无法判断目标版本是否仍使用 C-3333 的 NAT/INIT/COOKIE/ECDH、booking 或 Demonware 控制面。
- 最小解除证据：至少一条目标版本连接建立、首个有效包、服务器响应和客户端下一包的时间顺序。
- 优先级：P0。

## BLK-006-03 — 实时网络入口到游戏消费者的边未闭合

- 结论：C-2697-Rec 的所有 recv/recvfrom 调用点已被归到非游戏或 Demonware 路径；收包函数到应用层写侧的边未找到。
- 证据：`E17_EXECUTIVE_SUMMARY.md`；`E18_EXECUTIVE_SUMMARY.md`；`E12_REALTIME_NETWORK_ENTRY_CHAIN.md`；`E13_RECV_RINGBUFFER_TRACE_001\07_E13_VERDICT.md`。
- 为什么阻塞：不能从 socket 入口证明任何 gamestate/snapshot 字节进入游戏解析器。
- 最小解除证据：Demonware 上层交付路径，或非 socket 输入通道，最终到达 game opcode 消费者。
- 优先级：P0（辅助版本）；目标版本另有 BLK-006-01。

## BLK-006-04 — 2697 Demonware 服务端对端缺失

- 结论：客户端 Demonware 阶段 1 应答发送链已经静态闭合，但 2697 服务端 `codol_dedrun.exe` 是 iD-Tech 3-bit clc 栈，不含 `CLIENTCHAL`/`BDDATA`/HMAC mismatch。
- 证据：`E25_HANDSHAKE_RESPONSE_SEND_PATH_001`；`E26_SERVER_HANDSHAKE_PEER_CROSSWALK_001`；`E27_DEMONWARE_SERVER_PEER_DISCOVERY_001`。
- 为什么阻塞：无法把客户端 Demonware 应答连接到本机 2697 服务端生态。
- 最小解除证据：含 Demonware 消费者服务端模块，或证明该链走另一独立进程/服务并使用可映射的协议。
- 优先级：P0（辅助版本）。

## BLK-006-05 — gamestate/configstring 实时消费者缺失

- 结论：`0xA2660` 的 body 字段层可证，但实时归属未证；实时顶层 `0x03` 消费者未定位；demo 路径 `0x34FD80(1)` 与服务端字段序冲突。
- 证据：`E08_CONFIGSTRING_BODY_001\07_E08_VERDICT.md`；`E10_CONFIGSTRING_DISPATCH_001\03_OPCODE_04_DISPATCH_VERDICT.md`；`E12_REALTIME_GAMESTATE_CONSUMER_001\07_E12_VERDICT.md`。
- 为什么阻塞：服务器写入顺序不能证明客户端能读取。
- 最小解除证据：实时路径从接收缓冲到 `0xA2660` 或另一个 body reader 的调用边，并证明顶层 `0x03` 的进入分支。
- 优先级：P0。

## BLK-006-06 — 0x06 终止语义缺失

- 结论：服务端有三处 1 字节 `0x06`，但客户端读取、位宽、对齐和所在层没有闭合。
- 证据：`E10_CONFIGSTRING_DISPATCH_001\04_TERMINATOR_06_READ_PATH.md`；`E11_GAMESTATE_SUBFRAME_001\05_OPCODE_06_TERMINATION_VERDICT.md`。
- 为什么阻塞：任何长度/终止计算错误都会让后续 snapshot 帧整体错位。
- 最小解除证据：客户端显式读取/比较 `0x06` 的指令，或外层 LEN 与内部终止偏移的等式。
- 优先级：P0。

## BLK-006-07 — snapshot 完整帧边界缺失

- 结论：S-2697 writer 链和内部 `0x06` 位置已知，但不能证明内部 `0x06`、区域复制或外层 `0x05/0x06` 构成真实线上边界。
- 证据：`14_SERVER_KNOWLEDGE_ATLAS_001\07_GAMESTATE_CONFIGSTRING_SNAPSHOT.md`。
- 为什么阻塞：没有边界就不能实现 2697 snapshot，也不能安全修改 legacy writer。
- 最小解除证据：一条 S-2697/C-2697 对应帧，逐字节标出长度、内部边界与外层 EOF；或客户端 reader 的边界读取序列。
- 优先级：P0。

## BLK-006-08 — delta、baseline、实体索引和增删规则缺失

- 结论：客户端 delta 解码候选 `0x6E060/0x6D340` 未与 writer 或网络入口连接；实体计数、编号、状态编码、删除/新增和首帧基准均未知。
- 证据：`14_SERVER_KNOWLEDGE_ATLAS_001\07_GAMESTATE_CONFIGSTRING_SNAPSHOT.md:101`；`11_OPEN_QUESTIONS.md` BQ-17/BQ-25；`SNAPSHOT_EVIDENCE.md`。
- 为什么阻塞：无法实现可靠增量、实体增删和重连后的 baseline。
- 最小解除证据：客户端解码函数的字段读取顺序、历史快照键、实体表索引和 add/remove 分支。
- 优先级：P0。

## BLK-006-09 — 本地玩家激活与大厅→战斗状态条件缺失

- 结论：当前没有证据表明 gamestate/snapshot 在哪个阶段创建本地玩家、何时从大厅切到战斗或哪个服务器条件使客户端停止等待。
- 证据：`CLIENT_INIT_EVIDENCE.md` 第 4-5 节；`02_BATTLE_ENTRY_AND_INITIALIZATION.md` 步骤 7-8。
- 为什么阻塞：即使包格式正确，也可能停在 `waiting for player data` 或返回大厅。
- 最小解除证据：客户端状态变量写入点、gamestate 完成后的下一状态、地图加载与本地 player 对象创建调用链。
- 优先级：P0。

## BLK-006-10 — C-3333 权威 motion trace 不在工作区

- 结论：29/29 字段序列的原始 JSON 只存在于外部路径 `F:\桌面\ol\新建文件夹\reference\playerstate-motion-trace.json`，当前回归只保留硬编码索引结果。
- 证据：`REF_LOBBY_KIT\snapshot_diff.py:35`；`REF_LOBBY_KIT\battle_selftest.py:450-469`；`_BATTLE_ARCHAEOLOGY_20261005_20261008.md:136,429`。
- 为什么阻塞：无法在当前交付独立复核位宽、值和字段语义。
- 最小解除证据：原始 trace JSON、等值真实帧，或全新目标版本抓包。
- 优先级：P1（辅助版本）；对 3.9.9.7 仍被 BLK-006-01 优先阻断。

## 解除顺序

1. 先解决 **BLK-006-01/02**：确认目标版本并取得真实连接样包。
2. 再用目标客户端定位 **BLK-006-03/05/06/09**：实时入口、gamestate/configstring 消费者、终止和本地玩家激活。
3. 最后才能解决 **BLK-006-07/08**：snapshot 帧边界、实体索引、baseline、delta 和增删。
4. **BLK-006-04/10** 是 2.6.9.7/3.3.3.3 的辅助版本阻塞，可用于提出假设，不能直接产出 3.9.9.7 修订。