# PVE-ACCEPTED-TEARDOWN-RUNTIME-CORRELATION-028
# 自然运行状态下 accepted push 与 Lobby transport teardown 的先后关系

```
CYCLE_COUNT            = **11 个 push 周期**（另有 2 个无 push 的连接作为对照）

ORDERING               = **PUSH_BEFORE_CLOSE**（11/11，按 append-only 日志的写入顺序）
CLOSE_DIRECTION        = **CLIENT_FIN**（11/11 push 周期）
CLIENT_RST_OBSERVED    = 2 次，**均发生在没有 push 的连接上**（对照组）

SERVER_PUSH_SENT       = **CONFIRMED**
CLIENT_RECEIVED        = socket 层 **STRONG_CANDIDATE**；应用层 **UNKNOWN**
CLIENT_CLOSE           = **CONFIRMED**（服务端观测到对端关闭）

4F4_DIRECT_RUNTIME     = **NOT_OBSERVED**（025 采样器未读 4F4；本轮未改采样器）
4F8_DIRECT_RUNTIME     = **OBSERVED**（值 0/1 均出现；唯一 setter 0xB83A88）
TRANSPORT_STATE_RUNTIME= **CORRELATED_WITH_TRANSPORT_TICK**

TICK_ORDER             = **UNKNOWN**（无逐 tick 时间戳）
MESSAGE_PUMP_ORDER     = **CONFIRMED**（027 静态）

H_A                    = **CANDIDATE**（= 任务书 §13 CASE C 的 WEAKENED；§18 枚举里取 CANDIDATE）
STATE2_INERT_TICK      = **CANDIDATE_BLOCKER**（新增候选，见 §6）

RUNTIME_632680 = UNKNOWN ; RUNTIME_G6 = UNKNOWN ; RUNTIME_G7 = UNKNOWN
BATTLE_28960   = NOT_OBSERVED
MODIFIED_FILES = **NONE**（新增 DEV-BOOKING\scripts\_028_*.py 均为只读分析脚本）
```

---

## §1 数据来源（全部为既有数据）

```
1. accepted push 时间 / 连接事件 : DEV-PUBLISHER-RESTORE\REF_LOBBY_KIT\lobby_srv.log（025 运行，1360 行）
2. 保护副本                      : DEV-BOOKING\_025\lobby_srv.log.pre025（024 运行）
3. 客户端只读探针                : DEV-PUBLISHER-RESTORE\REF_LOBBY_KIT\accepted_state.txt（6540 行，1 ms）
4. 关闭侧语义                    : lobby_server.py 的 recv 分支（见 §4）

精确度说明：lobby_srv.log 只有**秒级**时间戳，因此同秒内的先后一律依据
**日志写入顺序**（append-only，写入即事件顺序）；探针文件有**毫秒级**时间戳。
```

## §2 逐周期时间线（11 个 push 周期）

```
| # | conn  | T_REQUEST | T_ACK | T_PUSH(written) | T_CLOSE | T_RECONNECT | CLOSE_DIR | ordering |
|---|-------|-----------|-------|-----------------|---------|-------------|-----------|----------|
| 1 | 53072 | 23:05:59  | 23:05:59 | 23:05:59     | 23:05:59 | 23:05:59   | CLIENT_FIN | PUSH<CLOSE |
| 2 | 53170 | 23:07:47  | 23:07:47 | 23:07:47     | 23:07:47 | 23:07:47   | CLIENT_FIN | PUSH<CLOSE |
| 3 | 53216 | 23:07:49  | 23:07:49 | 23:07:49     | 23:07:49 | 23:07:49   | CLIENT_FIN | PUSH<CLOSE |
| 4 | 53218 | 23:07:52  | 23:07:52 | 23:07:52     | 23:07:52 | 23:07:52   | CLIENT_FIN | PUSH<CLOSE |
| 5 | 53220 | 23:07:54  | 23:07:54 | 23:07:54     | **23:07:55** | 23:07:55 | CLIENT_FIN | PUSH<CLOSE（约 1 s） |
| 6 | 53225 | 23:07:59  | 23:07:59 | 23:07:59     | 23:07:59 | 23:07:59   | CLIENT_FIN | PUSH<CLOSE |
| 7 | 53229 | 23:09:09  | 23:09:09 | 23:09:09     | 23:09:09 | 23:09:09   | CLIENT_FIN | PUSH<CLOSE |
| 8 | 53279 | 23:09:12  | 23:09:12 | 23:09:12     | 23:09:12 | 23:09:12   | CLIENT_FIN | PUSH<CLOSE |
| 9 | 53286 | 23:09:19  | 23:09:19 | 23:09:19     | 23:09:19 | 23:09:19   | CLIENT_FIN | PUSH<CLOSE |
| 10| 53297 | 23:09:24  | 23:09:24 | 23:09:24     | 23:09:24 | 23:09:24   | CLIENT_FIN | PUSH<CLOSE |
| 11| 53302 | 23:09:34  | 23:09:34 | 23:09:34     | 23:09:34 | 23:09:34   | CLIENT_FIN | PUSH<CLOSE |

每次的日志行内顺序（11/11 完全同型）：

```
REQUEST_6_14  ->  PUSH_DECISION  ->  ACK(0x85 应答 service=6 task=14)  ->  PUSH_FRAME(0x85 推送 type=2)
              ->  PEER_CLOSED    ->  CONN_END                       ->  CONN_ESTABLISHED(重连)
```

RECONNECT_LATENCY：10/11 在同一秒内（<=1 s，秒级分辨率下即"立即"）；周期 #5 约 1 s。
两次"对端关闭->连接建立"之间没有任何其它连接的等待，符合 027 恢复的
state=0 -> 0x7F3890 -> 0xB82070 connect 立即重连环。
```

## §3 探针（毫秒级）与周期的对齐

```
| # | 周期秒   | 探针覆盖 | this278 | this288 | A | B | t_C8 | t_644 | t_5E8 | net4F8 |
|---|----------|----------|---------|---------|---|---|------|-------|-------|--------|
| 1 | 23:05:59 | 0 行     | -       | -       | - | - | -    | -     | -     | -      |
| 2 | 23:07:47 | 6 行     | 0x0000  | 0       | 0x00000001 | 0 | 2 | 0 | 1/3 | 0/1 |
| 3 | 23:07:49 | 12 行    | **0x0101** | 0    | 0x00000001 | 0 | 4->2 | 0 | 0->1->3 | 1->0->1 |
| 4 | 23:07:52 | 7 行     | 0x0000  | 0       | 0x00000001 | 0 | 4->2 | 0 | 0/1/2/3 | 1->0->1 |
| 5 | 23:07:54 | 18 行    | **0x0101** | 0    | 0x00000001 | 0 | 2/4 | 0 | 3/0   | 1/0 |
| 6 | 23:07:59 | 11 行    | **0x0101** | 0    | 0x00000001 | 0 | 4/2 | 0 | 0/1   | 1/0 |
| 7 | 23:09:09 | 313 行   | **0x0001->0x0101** | 0 | 0x00000000->0x00000001 | 0 | 2 | 0 | 3 | **1** |
| 8 | 23:09:12 | 318 行   | **0x0001->0x0101** | 0 | 0x00000001 | 0 | 2 | 0 | 3 | **1** |
| 9 | 23:09:19 | 303 行   | **0x0001->0x0101** | 0 | 0x00000000->1 | 0 | 2 | 0 | 3 | **1** |

周期 #1 落在探针启动之前（23:06:10 才开始写），故无数据。

**关键观察**：在 armed 窗口（this278 非 0）内，探针反复记录到
t_644 = 0、t_C8 = 2 或 4、t_5E8 = 3、**net4F8 = 1**，而 this288 恒为 0。
```

## §4 关闭方向（CLOSE_DIRECTION）—— 本轮最有价值的证据

```
服务端日志的两条分支（lobby_server.py）：
  conn.recv(...) 返回 0        -> log "  对端关闭"              <= 对端正常 FIN
  conn.recv(...) 抛异常         -> log "  recv 异常: %r"         <= 对端 RST
    （lobby_server.py 约 1096 行的注释亦写明"最终 ConnectionResetError(10054)"）

统计（19 个连接）：
  收到 push 的连接 11 个 : peer_closed = 1，rst = 0   **全部 FIN**
  未收到 push 的连接 2 个 : conn 53110（23:06:01）、conn 53308（23:11:11） **RST**
  其余 6 个连接无 push 也无异常
```

Windows TCP 语义：closesocket() 时**接收缓冲区仍有未读数据**会导致**中止性关闭（RST）**；
缓冲区已排空才是正常 FIN 关闭。

=> **11 个 push 周期全部 FIN、0 个 RST** ⇒ 客户端关闭时其接收缓冲区**已排空**
   ⇒ 服务端写出的那帧 98 字节 0x85 推送**在 socket 层已被客户端取走**，不是随连接一起被丢弃。
=> 而 RST 机制在同一份日志里**确实出现过 2 次**（且都发生在没有 push 的连接上）
   ⇒ 这构成了一个**天然的对照组**：如果 push 真的被留在缓冲区里，我们应当看到 RST；我们没有。
```

## §5 transport+0x4F8 的运行期证据（本轮新）

```
027 结论：0xB83A88 mov byte [esi+0x4F8], 1 是**唯一 setter**（在消息泵的"socket 已消失"
清理分支里）；清零点在 connect 路径 0xB8201E，另有 0xB7AE82（=0），构造函数 0xB8240A 初始化。

本轮全镜像复核（disp 0x4F8）：
  [W] 0xB81EA9  mov byte [esi+0x4F8], bl     (0xB815E0 基类)
  [W] 0xB8201E  mov byte [ebx+0x4F8], 0      (connect 相关函数)
  [W] 0xB8240A  mov byte [esi+0x4F8], bl     (构造函数 0xB82130)
  [W] 0xB83A88  mov byte [esi+0x4F8], **1**  (消息泵清理分支) <- 唯一置 1
  [W] 0xB7AE82  mov byte [esi+0x4F8], 0
  [R] 0xB7A686  cmp byte [esi+0x4F8], 0      (0xB7A670 的强制分支判断)

=> 运行期观测到 net4F8 = 1，**等价于"消息泵的 socket 消失分支至少执行过一次"**
   ⇒ **transport 的 socket 在 push 窗口附近确实消失过（被拆除）** —— 这是 runtime 观测，不只是静态推断。
```

## §6 新增候选阻塞点：STATE2_INERT_TICK

```
027 恢复的 tick 状态机：
  0x7F3800  eax = [0x84ABA7C]
            state 0 -> 0x7F386B -> 0x7F3890（connect / reconnect）
            state 1 -> 跑消息泵 0xB838A0
            其它    -> 0x7F3870 **直接 ret（什么都不做）**
            state 1 跑完泵后：0xB7A670 -> jmp [eax*4 + 0x7F3878]
               index 2  -> 0x7F385A **state = 2**（停用态）

0xB7A670 的返回：
  [transport+0x4F4] == 0                      -> 0
  否则 0xBA0780(socket) 的返回值
  但若 [transport+0x4F8] != 0（0xB7A686 jne）-> **跳过 "status==2 -> 1" 的强制**，原样返回 2

运行期观测到的组合（§3）：t_644 = 0，t_C8 = 2，t_5E8 = 3
  代入 0xBA0780：cmp [ecx+0x644],0 -> je 0xBA079F；cmp eax,2 -> 相等；
                 cmp [ecx+0x5E8],3 -> 相等；sete al; inc eax  => **返回 2**
  再加上 net4F8 = 1  => **0xB7A670 原样返回 2** => tick 跳表 index 2 => **state = 2**

=> 在 state = 2 下，0x7F3800 不会调用 0xB838A0，
   **队列里尚未分派的 0x85 推送不会被处理**（在没有 4F4=0 的情况下也能发生）。
=> STATE2_INERT_TICK = **CANDIDATE_BLOCKER**
   证据等级：静态状态机 CONFIRMED（027）+ 运行期输入组合 OBSERVED（028）
   限制：4F4 未被直接采样，无法排除"4F4=0 -> 返回 0 -> state=0（重连支）"这条并行解释
```

## §7 严格判定与禁止的推断

```
许可的结论：
  SERVER_PUSH_SENT  = CONFIRMED（11/11 服务端写出推送帧）
  CLIENT_CLOSE      = CONFIRMED（服务端观测到对端关闭）
  CLOSE_DIRECTION   = CLIENT_FIN（11/11 push 周期）
  ORDERING          = PUSH_BEFORE_CLOSE（append-only 日志顺序，11/11）
  RECONNECT_LATENCY = 同秒（<=1 s），符合 027 的 state=0 重连环
  CLIENT_RECEIVED   = socket 层 STRONG_CANDIDATE（FIN 无未读数据）；应用层 UNKNOWN

**未使用**的推断（严格禁止）：
  server push 成功      => client handler 已执行          （未使用）
  connection close      => handler 没执行                （未使用）
  288 == 0              => 0x632680 / G6 未执行           （未使用）
  net4F8 == 1           => 这一次 push 被丢弃              （未使用）
```

## §8 对 H-A 的影响

```
任务书 §7 的三种情况：
  A（push -> 客户端活动 -> close）：本轮观测到 push 之后才 close（11/11），支持"H-A_SUPPORT = STRONG"
  B（close -> push）：**未出现**（11/11 都不是）
  C（同秒）：秒级精度下多为同秒，但**写入顺序**明确给出 push 在前

任务书 §13 的判定：
  CASE C 要求"accepted push 稳定早于 teardown **且**存在客户端已处理该 TCP frame 的证据"
  -> 前者成立；后者（FIN 而无未读数据）是 socket 层的强证据，但仍非应用层处理的直接证据
=> H_A = **CANDIDATE**（相对 027 的 STRONG_CANDIDATE 为**降级**，即任务书所称 WEAKENED）
   理由：如果 push 是"随连接一起被丢弃"的那种 H-A，Windows 关闭时缓冲区有未读数据应当产生 RST；
        11 个 push 周期一个 RST 都没有，而同一日志里 RST 确实出现 2 次（都在无 push 的连接上）。
   保留：应用层是否真的把该帧交给 0x632680，仍然 UNKNOWN。
```

## §9 必填字段汇总

```
CYCLE_COUNT        = 11
（逐周期字段见 §2 与 §3 两张表）

SERVER_PUSH_SENT   = CONFIRMED
CLIENT_RECEIVED    = STRONG_CANDIDATE（socket 层）/ UNKNOWN（应用层）
CLIENT_CLOSE       = CONFIRMED（11/11 为客户端侧 FIN）
RECONNECT_LATENCY  = 10/11 同秒（<=1 s），1/11 约 1 s

4F4_DIRECT_RUNTIME = NOT_OBSERVED
4F8_DIRECT_RUNTIME = OBSERVED（0 与 1 均出现；1 只可能来自 0xB83A88）
TRANSPORT_STATE_RUNTIME = CORRELATED_WITH_TRANSPORT_TICK（t_C8 / t_644 / t_5E8 正是 0xBA0780 的输入）

TICK_ORDER         = UNKNOWN（没有逐 tick 时间戳，未制造）
MESSAGE_PUMP_ORDER = CONFIRMED（027）

H_A                = CANDIDATE
STATE2_INERT_TICK  = CANDIDATE_BLOCKER

RUNTIME_632680     = UNKNOWN
RUNTIME_G6         = UNKNOWN
RUNTIME_G7         = UNKNOWN
BATTLE_28960       = NOT_OBSERVED
MODIFIED_FILES     = NONE
```

## §10 本轮回答的问题

```
问：在自然运行的 024/025 周期中，accepted push 与 Lobby transport teardown 的先后关系是什么？
答：**push 在前，teardown 在后**（11/11，按写入顺序）；且 teardown 是**客户端侧正常 FIN**，
    不是异常断开；同秒完成，随后立即重连。

问：现有证据能否把 H-A 从 STRONG_CANDIDATE 提升，或至少显著削弱？
答：**显著削弱**（H_A 从 STRONG_CANDIDATE 降为 CANDIDATE），
    因为 11/11 的 push 周期都没有出现"关闭时仍有未读数据"应有的 RST，
    而同一份日志里 RST 确实出现过（对照组）。
    同时**新增**一个候选阻塞点 STATE2_INERT_TICK（静态状态机 + 运行期输入组合）。

RUNTIME_632680 仍然 = UNKNOWN —— 诚实结束。
```

（全文完 · 零代码修改 · 使用既有数据 · 未做任何 Server 实验 · Battle 继续冻结）
