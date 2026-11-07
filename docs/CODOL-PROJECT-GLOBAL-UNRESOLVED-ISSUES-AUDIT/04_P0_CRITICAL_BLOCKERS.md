# 04 — P0 阻塞项（阻止进入可玩战斗）

共 **7** 项。判定标准：该问题不解决，就无法出现'可操控的游戏画面'。

> ★ 关于 'Setting up game / 等待玩家数据'：2026-10-24 已证明它有两个独立成因，
> 一个是快照索引 run 编码（已修复，见 CODOL-ISSUE-0027 的历史），
> 另一个是服务端位置推不动客户端（CODOL-ISSUE-0025，未解决）。
> 但截至 2026-10-29，更前置的问题是**客户端根本不连战斗服**（CODOL-ISSUE-0020），
> 所以本轮 P0 的根节点不是快照，而是'连接不被发起'。

## 根阻塞集合

| Issue ID | 标题 |
|---|---|
| CODOL-ISSUE-0009 | 准备按钮点击不产生任何客户端上行，根因未定 |
| CODOL-ISSUE-0010 | 房间下行推送格式在'位流 / 容器'之间反复，最终未定死 |
| CODOL-ISSUE-0012 | dwRoomMatch::Init 从未被调用（MyEventHandler 零实例） |
| CODOL-ISSUE-0020 | BOT 房间场景下战斗服零收包（客户端从不 connect） |
| CODOL-ISSUE-0021 | mmstart 中的 playlist 编号在本轮解析为 37 而 findSessions 为 50，且均非官方 ID |
| CODOL-ISSUE-0041 | recv 缓冲 → 0x7765A0 读取器的边未闭合（最小未闭合边） |
| CODOL-ISSUE-0074 | 102/7 playerdata 批量读回全 0 会清空玩家选图/选模式 |


---

### CODOL-ISSUE-0009 — 准备按钮点击不产生任何客户端上行，根因未定

- **系统**: `lobby`
- **状态**: `BLOCKED`  **优先级**: `P0`  **严重度**: critical
- **阻塞可玩战斗**: 是
- **首次发现**: 2026-10-28（docs/READY_BUTTON_NO_RESPONSE_20261028.md）
- **证据等级**: E0-runtime-observed + E1-static

**问题现象**：用户按'准备'完全无反应；该轮 11/4 上行只有 4 条（房间初始化/成员状态/房间状态/mmbook），没有任何一条是'准备'。本地'已准备'状态也不变。

**预期行为**：点击应产生一条上行并把本地状态置为已准备。

**实际行为**：零上行、零本地状态变化。

**触发条件**：进入 BOT 房间 UI 后点击准备。

**影响范围**：BOT 房间入口无法走通；只能依赖 PvE 剧情入口（该入口从不使用此按钮）。

**历史调查过程**：先判为'AS_SetReadyState 未实现'（RTTI 无 COL、零引用）；后被修正为'dwRoomMatch::Init 未调用 ⇒ MyEventHandler 零实例'。两条解释并存，未判定哪条是根因。

**当前最可信判断**：现象确定；根因未定

**尚缺证据**：无法读活进程内存（ACE），无法反编译 ui_mp.ff（加密），无 .gfx 工具。

**最小验证方法**：在被明确批准的一次实验里，只改一个变量：让服务端在 createRoom 后推送 RoomInfo + RoomStateUpdated（已离线对拍通过的位流），观察按钮是否变为可点。

**推荐修复方向**：先确定'按钮禁用条件'的数据来源：房间状态对象是否因缺少服务端推送而未进入可准备态。

**证据来源**：

- `docs/READY_BUTTON_NO_RESPONSE_20261028.md`
- `docs/READY_BUTTON_NO_IMPL_20261028.md`
- `docs/AS_CLASSES_INVENTORY_20261028.md`
- `docs/UI_FF_ENCRYPTED_20261028.md`
- `docs/READY_BUTTON_ROOT_CAUSE_CLOSED_20261028.md`

**依赖**：`CODOL-ISSUE-0010`, `CODOL-ISSUE-0012`

**完成验收标准**：点击准备后，lobby_srv.log 出现一条可识别的准备上行，且本地 UI 状态改变。

**复杂度**：L　**推荐处理顺序**：P0-1

---

### CODOL-ISSUE-0010 — 房间下行推送格式在'位流 / 容器'之间反复，最终未定死

- **系统**: `lobby`
- **状态**: `CONTRADICTORY_EVIDENCE`  **优先级**: `P0`  **严重度**: critical
- **阻塞可玩战斗**: 是
- **首次发现**: 2026-10-28（docs/ROOM_DIRECTION_SPLIT_20261028.md / TYPE02_IS_TEXT_20261028.md）
- **证据等级**: E0-runtime-behaviour-diff + E1-static

**问题现象**：上行 body 首字节只出现 0x02 与 0x18（87 条样本），且穷举 160 bit 偏移无 readBits==3 ⇒ 上行不是位流；下行由各 RoomMessage::deserialize 读位流（0x637000 以 (ptr, len*8) 直接建流）。据此重编后，实机首次出现可观测差异（任务数 85→71、11/4 由 6 次降为 4 次），但战斗服仍零收包，UI 是否点亮未确认。

**预期行为**：服务端能构造出被客户端接受并无错误地改变房间状态的下行消息。

**实际行为**：消息被处理（有行为差异）但未达成目标；无法确认是否被正确解析。

**触发条件**：createRoom 后的三条推送。

**影响范围**：房间状态机无法由服务端驱动。

**历史调查过程**：10-28 内至少经历四轮反转：位流 → 容器 → 上下行不同 → type02 是文本。每次反转都伴随一次实机无效。

**当前最可信判断**：两套格式都被部分证伪；最终形态未定

**尚缺证据**：无法确认客户端是否解析成功（无日志、无法读内存）。

**最小验证方法**：对同一条消息做'故意畸形'对照：若客户端 ack/行为对该消息敏感，说明确被解析；否则说明被忽略。

**推荐修复方向**：先用畸形对照建立'客户端确实在读这段'的证据，再谈内容正确性。

**证据来源**：

- `docs/ROOM_DIRECTION_SPLIT_20261028.md`
- `docs/TYPE02_IS_TEXT_20261028.md`
- `docs/DOWNLINK_STREAM_RUN_20261028.md`
- `docs/ROOM_MSG_NOT_BITSTREAM_20261028.md`
- `docs/ROOM_PROTOCOL_COMPLETE_20261028.md`
- `docs/ROOM_PUSH_SPEC_FIX_RUN_20261028.md`

**完成验收标准**：有一条消息能被证明被客户端解析（畸形对照产生可测差异）。

**复杂度**：L　**推荐处理顺序**：P0-2

---

### CODOL-ISSUE-0012 — dwRoomMatch::Init 从未被调用（MyEventHandler 零实例）

- **系统**: `lobby`
- **状态**: `OPEN`  **优先级**: `P0`  **严重度**: critical
- **阻塞可玩战斗**: 是
- **首次发现**: 2026-10-27（docs/GATE_B_INIT_PATH_20261027.md §'完整因果链闭合'）
- **证据等级**: E0-memdump

**问题现象**：整份 1478 MB 转储里搜 vtable 0x00DC78F0 的实例，一个都没有。

**预期行为**：Init 执行时应创建 MyEventHandler，其 slot[1]=0x63B500 是建房回调。

**实际行为**：零实例 ⇒ 0x63B500 永不被调用 ⇒ 0x63E510 不执行 ⇒ dwRoomMatchUber 不创建。

**触发条件**：进入大厅/房间阶段。

**影响范围**：整条自动开局链的上游断点。

**历史调查过程**：2026-10-27 由'三个包装函数是控制台命令'上溯到控制台注册表，再从 0x63B500 的 vtable 反推。2026-10-28 从符号层独立确认 MyEventHandler 是 dwRoomMatch::Init 的局部类。

**当前最可信判断**：实例数为 0：确定；Init 未调用的原因：未知

**尚缺证据**：Init 的调用点。函数体在加密节 .tp3（VSize 219 MB / RawSize 401 KB），静态看不到。

**最小验证方法**：行为二分：按 BISECT_EXPERIMENT_PLAN 逐组关闭大厅应答，看按钮是否变为可点。需用户逐轮反馈。

**推荐修复方向**：找到 Init 的调用条件；最可能是某条大厅应答前置数据。

**证据来源**：

- `docs/GATE_B_INIT_PATH_20261027.md`
- `docs/READY_BUTTON_ROOT_CAUSE_CLOSED_20261028.md`
- `docs/BISECT_EXPERIMENT_PLAN_20261028.md`

**依赖**：`CODOL-ISSUE-0009`

**完成验收标准**：转储中出现 MyEventHandler 实例（vtable 0x00DC78F0），且 0x63B500 被调用。

**复杂度**：L　**推荐处理顺序**：P0-4

---

### CODOL-ISSUE-0020 — BOT 房间场景下战斗服零收包（客户端从不 connect）

- **系统**: `battle-network`
- **状态**: `OPEN`  **优先级**: `P0`  **严重度**: critical
- **阻塞可玩战斗**: 是
- **首次发现**: 2026-10-26（docs/PVE_STARTGAME_BLOCKER_20261026.md）
- **证据等级**: E0-runtime-verified

**问题现象**：客户端进程打开的 UDP 端口（22011/50095/…）没有一个连向 28960；战斗服日志 TX_NAT_REPLY=0 KEY_EXCHANGE_OK=0 RX_CLIENT_GAME_HEADER=0。

**预期行为**：客户端应发起 NAT/DTLS/getchallenge/connect。

**实际行为**：零收包。10-29 最新一轮仍然如此：_battle_out.txt 只有 7 行初始化。

**触发条件**：从 BOT 房间入口点开始/准备。

**影响范围**：任何战斗功能都无从验证。

**历史调查过程**：10-26 PvE 入口的 8 轮曾成功连上（mmstart 携带 map + g_gametype）。10-27 之后即使同样形态也全灭。10-28 提出三个候选：mmstart 无 map、102/7 回全 0、mmstart 推 StartGame。

**当前最可信判断**：现象确定；根因多候选未二分

**尚缺证据**：没有做过单变量二分（10-28 列出了计划但未见执行记录）。

**最小验证方法**：按 BATTLE_CONNECT_DIVERGENCE §五：mmstart 不推 StartGame、102/7 恢复不处理、memberCount 保留 1，跑一轮。

**推荐修复方向**：先做上述单变量回归，确认是否回到 10-26 行为。

**证据来源**：

- `docs/PVE_STARTGAME_BLOCKER_20261026.md`
- `docs/BATTLE_ZERO_RX_ROOT_CAUSE_20261028.md`
- `docs/BATTLE_CONNECT_DIVERGENCE_20261028.md`
- `docs/DOWNLINK_STREAM_RUN_20261028.md`
- `run_codol_001/runs/ONCE_20261029_002046/kit/_battle_out.txt`
- `run_codol_001/runs/ONCE_20261029_002046/kit/lobby_srv.log`

**依赖**：`CODOL-ISSUE-0009`, `CODOL-ISSUE-0010`

**完成验收标准**：战斗服日志出现 TX_NAT_REPLY 或 KEY_EXCHANGE_OK 或 RX_CLIENT_GAME_HEADER 之一。

**复杂度**：M　**推荐处理顺序**：P0-0（最高）

---

### CODOL-ISSUE-0021 — mmstart 中的 playlist 编号在本轮解析为 37 而 findSessions 为 50，且均非官方 ID

- **系统**: `lobby`
- **状态**: `OPEN`  **优先级**: `P0`  **严重度**: high
- **阻塞可玩战斗**: 是
- **首次发现**: 2026-10-28（docs/BATTLE_ZERO_RX_ROOT_CAUSE_20261028.md）
- **证据等级**: E0-runtime-log

**问题现象**：10-29 最新一轮：findSessions playlist=50 → 命中本地 mp_raid；mmstart 带 playlist 37 + start_map_rotate_once 7；lobby 日志打印 'mmstart 选择: gametype=? map=?'。

**预期行为**：房间最终地图/模式应唯一且本地可用。

**实际行为**：两个编号语义不同（ID / 下标 / 轮换序号三解未定），且 mmstart 未带 map。

**触发条件**：从 BOT 房间点开始。

**影响范围**：客户端拿不到目标地图 ⇒ 推断不发起 connect。

**历史调查过程**：10-28 已统计全 57 轮：A 形态（带 g_gametype）25 轮有 8 轮成功，B 形态（playlist 37）8 轮 0 成功。

**当前最可信判断**：相关性确定；因果未证

**尚缺证据**：playlist 编号的真实语义（官方表 123 项中无 37/50）。

**最小验证方法**：让 mmstart 也带 `map <本地图>; g_gametype coop`（复制 10-26 成功形态）跑一轮。

**推荐修复方向**：统一 findSessions 与 mmstart 指向同一张本地可用图。

**证据来源**：

- `docs/BATTLE_ZERO_RX_ROOT_CAUSE_20261028.md`
- `run_codol_001/runs/ONCE_20261029_002046/kit/lobby_srv.log`

**完成验收标准**：mmstart 携带的 map==findSessions 回的地图，且战斗服收到连接。

**复杂度**：S　**推荐处理顺序**：P0-1

---

### CODOL-ISSUE-0041 — recv 缓冲 → 0x7765A0 读取器的边未闭合（最小未闭合边）

- **系统**: `client-re`
- **状态**: `OPEN`  **优先级**: `P0`  **严重度**: critical
- **阻塞可玩战斗**: 是
- **首次发现**: 2026-10-14（CODOL-BATTLE-SERVER-RECEIVE-LINK-050/00_FINDINGS.md）
- **证据等级**: E1-static

**问题现象**：可证两端使用同一会话对象、同一长度/类型控制链；不能证 0x7765A0 读的字节就是 recv 的 payload。

**预期行为**：从 socket 到解析器的完整数据流。

**实际行为**：'对象构造'≠'payload 已复制'。

**触发条件**：任何'客户端会解析我们的包'的推断。

**影响范围**：所有上层协议结论都悬在这条边上。

**历史调查过程**：048→050 三个任务收敛到这一条边。

**当前最可信判断**：确定（未闭合）

**尚缺证据**：运行时 socket 数据指针与首个消费者的对应关系。

**最小验证方法**：在早期转储窗口内捕获 [esi+0xA8] 与 [esi+0xB0] 的指针关系。

**推荐修复方向**：用早期窗口内的高频转储对比缓冲区内容与 recv 目标。

**证据来源**：

- `CODOL-BATTLE-SERVER-RECEIVE-LINK-050/00_FINDINGS.md`
- `CODOL-BATTLE-SERVER-RECVBUFFER-TO-PARSER-041/`

**完成验收标准**：同一份字节可在 recv 目标与读取器输入两处被指认。

**复杂度**：L　**推荐处理顺序**：P0-6

---

### CODOL-ISSUE-0074 — 102/7 playerdata 批量读回全 0 会清空玩家选图/选模式

- **系统**: `lobby`
- **状态**: `OPEN`  **优先级**: `P0`  **严重度**: critical
- **阻塞可玩战斗**: 是
- **首次发现**: 2026-10-28（docs/BATTLE_CONNECT_DIVERGENCE_20261028.md §3（hist_combat #20））
- **证据等级**: E0-runtime-correlation

**问题现象**：字段表索引 [44..49] = PVEDifficulty/PVEMap/PVEMode/PVPMatch/PVPMode/RootIndex。曾回 50 个字段全 0，等于告诉客户端'你什么都没选'。

**预期行为**：回显客户端真实选择。

**实际行为**：当前最新一轮已改为'保持不处理（对齐 10-26 成功轮）'，但未验证是否能恢复连接。

**触发条件**：大厅初始化 102/7。

**影响范围**：与 CODOL-ISSUE-0020 同为战斗服零收包的候选根因。

**历史调查过程**：10-27 两轮回显均失败（客户端每 5 秒重发）；10-28 起改回不处理。

**当前最可信判断**：候选根因，未二分

**尚缺证据**：单变量二分结果。

**最小验证方法**：BATTLE_CONNECT_DIVERGENCE §五 的三步回归。

**推荐修复方向**：先做单变量回归，再逐个放开。

**证据来源**：

- `docs/BATTLE_CONNECT_DIVERGENCE_20261028.md`
- `run_codol_001/runs/ONCE_20261029_002046/kit/lobby_srv.log`
- `docs/PVE_STUCK_INVESTIGATION_20261027.md §3`

**依赖**：`CODOL-ISSUE-0020`

**完成验收标准**：战斗服收到连接，且 102/7 行为与地图选择一致。

**复杂度**：S　**推荐处理顺序**：P0-1

---
