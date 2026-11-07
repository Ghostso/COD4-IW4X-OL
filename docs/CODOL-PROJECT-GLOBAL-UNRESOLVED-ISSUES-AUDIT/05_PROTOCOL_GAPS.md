# 05 — 协议缺口（UDP / DTLS / ECDH / OOB / GameState / Configstring / Reliable / Snapshot / Usercmd）

> 判定口径：**"服务端能构造" ≠ "客户端收到" ≠ "客户端解析" ≠ "客户端据此改变状态"**。
> 本文件逐层标注每一段协议证据停在哪一层。

证据层级 legend：

- `S-impl` 服务端已实现并可产出字节
- `S-offline` 服务端实现与离线对拍一致
- `S-sim` 仅对模拟客户端（`e2e_client.py`）验证
- `C-bytes` 官方客户端字节被抓到（单向）
- `C-ack` 官方客户端有确认行为
- `C-state` 官方客户端状态因它而改变

---

## 1. 传输层（UDP 28960）

| 段 | 状态 | 证据 | Issue |
|---|---|---|---|
| UDP 绑定/收发 | `S-impl` | `src/transport/transport.c`；日志 `transport initialized on UDP port 28960` | — |
| NAT 探针与 NAT 应答 | `S-impl` + `C-bytes`（10-26 有 8 轮） | `TX_NAT_REPLY %dB` 日志；10-26 八轮成功 | ISSUE-0020 |
| DTLS-like Init / Cookie | `S-impl` + `C-bytes`（同上） | `TX_DTLS_INIT_ACK` | ISSUE-0078 |
| ECDH P-224 密钥交换 | `S-impl` + `C-bytes` | `KEY_EXCHANGE_OK`；`src/crypto/p224.c` | ISSUE-0078 |
| 帧头 `06 02 tag(2) seq(2) hmac(8) len(2) cipher` | `S-impl` + `S-offline` | `test_crypto` / `test_p224` | — |
| 传输密钥派生 `SHA1(ECDH_raw ‖ securityKey16)` | `S-impl`（依据 `battle_server.py` 头部说明） | `HANDOFF_20261025_BINARY_BISECT.md §5` | — |
| 重放保护 / 序号管理 | `S-impl`（部分） | `codol_battle_try_*` 系列 | ISSUE-0040 |
| 会话超时 | `S-impl` | `codol_session_check_timeouts` | ISSUE-0039（时钟） |
| 多客户端隔离 | **不可表达** | 单个 `svc` 里只有一份 player/equip/baselines | ISSUE-0033 |
| 下行分片 | **不存在** | TX 缓冲 512 B | ISSUE-0023 |

**最大缺口**：官方客户端的握手只在 2026-10-26 的 8 轮观测到过，**没有落盘抓包**。
所以传输层的"官方兼容"没有可复用的字节级证据（ISSUE-0078）。

---

## 2. OOB 文本命令

服务端已实现：`getchallenge` / `connect` / `stats` / `heartbeat` / `gamestateupdate` / `cancelConnect`
（`battle_service.c:841-879`）。

| 命令 | 服务端 | 客户端侧证据 | 缺口 |
|---|---|---|---|
| `getchallenge <seed>` | 回 `challengeResponse 1`（**种子恒为 1**） | 有（10-26） | 挑战值是否被校验未知；`getchallenge` 种子生成未追（hist_e #57） |
| `connect <...>` | 回 `connectResponse` | 有（10-26） | userinfo 28 键 → 值/引号规则未解（hist_e #55） |
| `stats` 分块 | 实现 1238 B/块 + `statResponse <missing 位掩码>` | 有 | `stats_total` 上限 32768；chunk 位图是全局非 per-peer（ISSUE-0034） |
| `heartbeat` | 回 `heartbeatresponse` | 有 | — |
| `gamestateupdate <n>` | 只置 `gamestate_loading=true`；stage 6 起 0.5s 后推快照 | 有 | stage 3/4/5 语义未解（hist_e #53） |
| `cancelConnect` | 只打日志 | 未知 | 拆除副作用未解（hist_e #58） |

**缺口**：OOB 的入站信封/长度/分隔规则未完全定死（hist_e #56）；
`0xFF FF FF FF` 前缀若变化会落入 netchan 分支（ISSUE-0035 同类）。

---

## 3. GameState / Configstring

| 段 | 状态 | 证据 |
|---|---|---|
| 259 B gamestate 样本 | 有 | `-046/_extracted/evidence/firingrange-gamestate.bin` |
| 服务端编码（seq + state，`[8:] ^= (seq^1)&0xFF`） | `S-impl` | `battle_service.c:374-409` |
| 动态房间适配（改 map/gametype 首部） | `S-impl`，未实机验证生效 | `battle_service.c:302-372` |
| 尾部 44 字节 | **未解析** | ISSUE-0064 |
| configstring `index_bits()` | **未知** | ISSUE-0064 |
| 客户端消费 | **未证**（0%） | ISSUE-0044 |

**已知的硬约束**：
- `state` 缓冲 1200 B，`n > 1100` 直接拒绝（无日志以外的告警）
- 每会话最多发 5 次（ISSUE-0036）

**为什么客户端仍可能停在 "Setting up game"** — 本审计列出**全部仍可能成立的原因**：

| 候选 | 支持证据 | 反对证据 | 如何验证 |
|---|---|---|---|
| A. 客户端根本没收到 gamestate | 10-26 之后战斗服零收包（连不上就谈不上收） | 10-26 的 8 轮里状态推进到过 gamestateupdate | 先解决 ISSUE-0020，再看 RX_GAMESTATE_PROGRESS |
| B. 收到但解析失败 | 尾部 44 B 未解析、configstring 编码未知 | 10-23 曾有客户端走到 CA_GAMESTATE 被报告过 | 在能连上的配置下抓 `gamestateupdate` 序列 |
| C. 解析成功但地图名/模式不匹配本地资源 | `--map` 与房间选图不一致（ISSUE-0022） | 10-27 文档称换图不改变"是否连 28960" | 让三处地图名一致后跑一轮 |
| D. 解析成功但缺 configstring 项（如 northyaw） | 小地图空白（ISSUE-0058） | 小地图不影响进图 | 补齐 configstring 后观察 |
| E. 解析成功但玩家未被"认作自己" | 服务端位置推不动客户端（ISSUE-0025） | 参照实现无 clientInfo 也能驱动 | 见 ISSUE-0025 |
| F. 状态机被别的条件卡住（房间侧） | `dwRoomMatch::Init` 未调用（ISSUE-0012） | 与战斗服的 gamestate 是两条线 | 先解决房间线 |

**结论**：截至本审计，**没有任何一条候选被排除**，也没有任何一条被证实。
把"卡在 Setting up game"归因于单一原因的表述，目前都**缺乏证据**。

---

## 4. Reliable Command

| 段 | 状态 |
|---|---|
| opcode==2 段的文本命令解析（`mr 1 1 custom1/custom2`） | `S-impl`，实机有日志 |
| 分片（`0xA0000000` RELIABLE 片段） | `S-impl`，**实机从未触发** |
| 客户端 ack | 未观测 |

**缺口**：可靠命令只用来选背包；换枪/其他命令未接（ISSUE-0059）。

---

## 5. Snapshot

| 段 | 状态 | 关键事实 |
|---|---|---|
| 索引 run 编码 | **必须 4 位一组 / 步长 15** | 改 7 位会整条位流错位 |
| 终止符 `0x05` | 正确 | `net_chan_mp.hpp`：54682/54682 demo 快照以它收尾 |
| playerState 字段编码 | 部分（11 个字段曾用 XOR，已修） | ISSUE-0027 |
| idx61 groundEntityNum | 恒 2047（空中） | 2046 会让客户端进飞行模式 + 开镜失效 |
| idx20 pm_flags | `aiming?0x10:0`，但 0x10 可能是 PMF_SPRINTING | ISSUE-0056 |
| 62/83/107/162 / idx219 | 只有我们写，参照无 | 但**是唯一能进图的写法** |
| 位置（omit） | 首帧后不再发 | 服务端推不动客户端 |
| 实体段 | 收得下，不可见 | model_index 恒 0 |
| serverTime | `1000 + elapsed_ms` | 1000 这个基数无出处（ISSUE-0035 同类） |
| ack / 基线 | 精确匹配，缺失即拒绝 | 好设计 |
| 客户端消费 | **`C-ack` 级**（messageAck 持续递增） | 这是全线最强的客户端证据 |

**这一节是全项目唯一有 `C-ack` 级证据的协议段。**

---

## 6. Usercmd

| 段 | 状态 |
|---|---|
| 14 B 结构解析 | `S-impl` + `C-bytes`（19022 条实机） |
| yaw/pitch/roll 变化 | 确认（20 个不同取值） |
| fwd/right 非零 | 确认（518/832） |
| weapon | 恒 1156（`usercmd.weapon` 字段本身恒 0） |
| 开火位 bit0 | **从未出现** |
| 跳跃位 | 定义冲突（0x400 vs 0x2）；且服务端 jump 分支不可达 |
| bit29 | 未解释 |
| 基线语义 | 与参照一致（精确 ack 匹配） |

---

## 7. 协议缺口的优先级排序

| 顺序 | 缺口 | Issue | 理由 |
|---|---|---|---|
| 1 | 客户端不发起连接 | ISSUE-0020 | 一切协议验证的前置 |
| 2 | 房间下行格式与信封 | ISSUE-0010 / 0011 | 房间状态与开局都由它驱动 |
| 3 | 官方握手抓包缺失 | ISSUE-0078 | 传输层唯一可复用证据 |
| 4 | 五项客户端消费语义 0% | ISSUE-0044 | 决定"能不能解释现象" |
| 5 | 开火位 / 按键位表 | ISSUE-0055 / 0060 | 决定战斗输入是否可验证 |
| 6 | 下行分片 | ISSUE-0023 | 决定实体规模 |
| 7 | gamestate 尾部 / configstring 编码 | ISSUE-0064 | 决定地图初始化 |
