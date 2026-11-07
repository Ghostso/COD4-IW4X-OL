# PVE-ACCEPTED-DISPATCH-RUNTIME-SPLIT-029
# 分流实验：4F4 teardown starvation vs state=2 inert tick

```
TEARDOWN_STARVATION (Path A) = **REFUTED**（本轮样本内可判定）
STATE2_INERT_TICK   (Path B) = **STRONG_CANDIDATE**（存在性）；作为本次 push 的 blocker = **CANDIDATE**（见 §8 反证）

RUNTIME_632680 = **UNKNOWN** ; G6_RUNTIME = UNKNOWN ; G7_RUNTIME = UNKNOWN
BATTLE_28960   = **NOT_OBSERVED**

MODIFIED_FILES = **nt10.py（只读采样器，唯一改动，+2 个字段）**
  nt10 BEFORE = DEAA33E80AFB8FD99AC3666BF101B2A2450D32ADF0DF1004F94E057A67363145
  nt10 AFTER  = 4A9628F747A8FDD47D41D9C9FB2F9BD37FA649CDB649672A68A8DA87E5CC2328
  backup      = DEV-PUBLISHER-RESTORE\REF_LOBBY_KIT\nt10.py.bak_029
  codol_crypto.py = E836C63A...（未动） / lobby_server.py = 7BBDC4F2...（未动）
  battle_server.py = 71BB7BEB...（未动）
未 hook / 未 patch / 未注入 / 未断点 / 未改 Server / 未改 timing / 未重排或重复 push。
```

---

## §1 采样方法

```
宿主：现有只读探针 _accprobe（nt10.py），纯 ReadProcessMemory。
本轮只新增 2 个读取（其余字段沿用 024/025）：
  transport_4F4 = [transport+0x4F4]   —— 与现有 nblk 同一次读取，未增加 RPM 调用
  lobby_tick_state = [0x084ABA7C]     —— 1 次额外 ru32
保留：transport_4F8 / socket+0x5E8 / socket+0xC8 / socket+0x644 / this278 / this288 / A / B / G2 / G3
采样间隔：1 ms（time.sleep(0.001)）
输出：SAM 行只在"热窗口"内写（窗口 = armed 或 (state,4F4,4F8) 发生变化后 0.3 s），
      以便在状态跃迁附近拿到密集点而不产生巨量输出。

可选计数器搜索（任务书 §五，OPTIONAL）：在 0xB83920..0xB83A00（消息泵内）扫描
inc/add dword 型自增，**未发现**现成的 processed-message/queue-depth 计数器
-> OPTIONAL_COUNTER = NOT_FOUND，未新造任何计数器。
```

## §2 运行与周期

```
命令：agent_client.py run python -X utf8 run_all.py --secs 600 --out n10_029.txt
进程：lobby_server 14544（127.0.0.2:3074） / fake_auth_tls 24804（127.0.0.1:3074）
      游戏客户端 18060
探针：accepted-state-probe.on；采样文件 accepted_state.txt（按周期会被截断，故每轮快照）
快照：DEV-BOOKING\_029\snap_234042.txt（5828 SAM 行）、snap_234211.txt（5464 SAM 行）

**本轮 A/B 未对齐是刻意的**：按任务书 §一"不改变 AB 对齐值"，codol_crypto.py 保持 ORIGINAL
（实测 A = 0x00000000 / 0x00000001）。
=> 因此即使消息被成功分派，**G4 也必然失败**，this288 在本轮**不可能**变成 1。
   本轮目的只是分流 A/B 两条 starvation 路径，288 不作为成功判据。
```

### 2.1 服务端 push 周期（本轮共 5 次 accepted push）

```
=== cycle #1 (line 217) ===
   line 5      [23:37:58]  CONN_ESTABLISHED
   line 215    [23:38:55]  REQUEST_6_14
   line 217    [23:38:55]  PUSH_DECISION
   line 218    [23:38:55]  REQUEST_6_14
   line 219    [23:38:55]  PUSH_FRAME_WRITTEN
   line 220    [23:38:55]  PEER_CLOSED
   line 221    [23:38:55]  CONN_END
   line 222    [23:38:55]  CONN_ESTABLISHED
=== cycle #2 (line 275) ===
   line 222    [23:38:55]  CONN_ESTABLISHED
   line 273    [23:38:57]  REQUEST_6_14
   line 275    [23:38:57]  PUSH_DECISION
   line 276    [23:38:57]  REQUEST_6_14
   line 277    [23:38:57]  PUSH_FRAME_WRITTEN
   line 278    [23:38:57]  PEER_CLOSED
   line 279    [23:38:57]  CONN_END
   line 280    [23:38:58]  CONN_ESTABLISHED
=== cycle #3 (line 506) ===
   line 290    [23:39:28]  CONN_ESTABLISHED
   line 504    [23:40:31]  REQUEST_6_14
   line 506    [23:40:31]  PUSH_DECISION
   line 507    [23:40:31]  REQUEST_6_14
   line 508    [23:40:31]  PUSH_FRAME_WRITTEN
   line 509    [23:40:31]  PEER_CLOSED
   line 510    [23:40:31]  CONN_END
   line 511    [23:40:31]  CONN_ESTABLISHED
=== cycle #4 (line 736) ===
   line 521    [23:41:00]  CONN_ESTABLISHED
   line 734    [23:41:34]  REQUEST_6_14
   line 736    [23:41:34]  PUSH_DECISION
   line 737    [23:41:34]  REQUEST_6_14
   line 738    [23:41:34]  PUSH_FRAME_WRITTEN
   line 739    [23:41:34]  PEER_CLOSED
   line 740    [23:41:34]  CONN_END
   line 741    [23:41:34]  CONN_ESTABLISHED
=== cycle #5 (line 826) ===
   line 741    [23:41:34]  CONN_ESTABLISHED
   line 824    [23:42:10]  REQUEST_6_14
   line 826    [23:42:10]  PUSH_DECISION
   line 827    [23:42:10]  REQUEST_6_14
   line 828    [23:42:10]  PUSH_FRAME_WRITTEN
   line 829    [23:42:10]  PEER_CLOSED
   line 830    [23:42:10]  CONN_END
```

T1（push 发出）时刻：23:38:55 / 23:38:57 / 23:40:31 / 23:41:34 / 23:42:10
其中 **3 次（23:40:31、23:41:34、23:42:10）落在探针覆盖窗口内**，用于本轮的时序对齐。

## §3 4F4 时间序列（Path A 的关键字段）

```
快照 snap_234042（23:39:10 → 23:40:35）：
   4F4 = 0xFFFFFFFF（读不到/无对象）  23:39:10.051 起
   4F4 = 0x00000000（被清零）         23:39:26.714 → 23:39:27.190  **仅 0.476 s**（169 点）
   4F4 = 0x3DD212C8（socket 存活）    23:39:28.161 起
快照 snap_234211（23:40:43 → 23:42:10）：
   4F4 = 0xFFFFFFFF                   23:40:43.436 → 23:40:59.456
   4F4 = 0x00000000                   23:40:59.456 → 23:41:00.581  **1.125 s**（171 点）
   4F4 = 0x3D5F9F38（存活）           23:41:00.888 起（含全部 3 个 push 时刻）

**关键**：两次 4F4: 非零 -> 0 的跃迁，**都发生在 state == 0 期间**（见 §5），
即当时消息泵本来就因为 state != 1 而不会被调用；清零本身并没有造成"泵被 4F4 门跳过"。
```

## §4 4F8 时间序列

```
snap_234042：4F8=1 共 1 段 0.298 s（23:39:28.427→28.725）；4F8=0 共 2 段 2.029 s
snap_234211：4F8=1 共 2 段 **69.120 s**
               23:41:01.122 → 23:41:34.442（33.320 s）
               23:41:34.579 → 23:42:10.379（35.800 s）
             4F8=0 共 3 段 1.950 s

=> 4F8=1 的两段与 state=2 的两段**逐段对应**（33.320/35.800 对 33.169/35.251）。
=> 结合 027 的结论（0xB83A88 是 4F8 的唯一置 1 点，位于泵的"socket 消失"清理分支），
   说明**泵确实在每次进入 state=1 的窗口里跑过**并看到了 socket 变化。
```

## §5 state（[0x84ABA7C]）时间序列 —— 最重要的结果

```
snap_234042（窗口 85 s）：
   state=0 : 23:39:10.051 → 23:39:27.190（17.139 s，5413 点）
   state=1 : 23:39:28.161 → 23:39:28.425（**0.264 s**，142 点）   <- 唯一会调用泵的状态
   state=2 : 23:39:28.427 → 23:40:31.255（**62.828 s**，226 点）
   state=1 : 23:40:31.441（1 点）
   state=0 : 23:40:31.537 → 23:40:33.829（2.292 s）

snap_234211（窗口 87 s）：
   state=0 : 23:40:43.436 → 23:41:00.581（17.145 s）
   state=1 : 23:41:00.888 → 23:41:01.120（**0.232 s**）
   state=2 : 23:41:01.122 → 23:41:34.291（**33.169 s**）
   state=1 : 23:41:34.488（1 点）
   state=2 : 23:41:34.579 → 23:42:09.830（**35.251 s**）
   state=1 : 23:42:10.404（1 点）
   state=0 : 23:42:10.262/.468 → 23:42:10.881

**量化**：
   state=1（泵可运行）总时长 ≈ 0.232～0.264 s / 85～87 s 窗口 ≈ **0.27%～0.31% 的墙钟时间**
   state=2（泵不会被调用）单段 33～63 s
=> 消息泵的"可运行窗口"极短且稀疏；其余时间 tick 要么在 state=0（重连支）要么在 state=2（停用支）。
```

## §6 5E8 / C8 / 644（用于解释 0xBA0780 -> 0xB7A670）

```
本轮 armed 窗口内实测：t_644 = 0，t_C8 = 2 或 4，t_5E8 = 0/1/2/3。
代入 027 恢复的静态链：
  0xBA0780：cmp [socket+0x644],0 -> je；cmp [socket+0xC8],2 -> 相等；
            cmp [socket+0x5E8],3 -> 相等；sete al; inc eax  => 返回 2
  0xB7A670：若 [transport+0x4F8] != 0 -> 跳过 "2 -> 1" 的强制 -> 原样返回 2
  0x7F3800 跳表 index 2 -> 0x7F385A state = 2
=> 与 §4/§5 观测到的 "4F8=1 与 state=2 逐段对应" 完全一致。
```

## §7 两条路径的形态判别（核心）

```
Path A 形态（泵被 4F4 门跳过）= **[4F4 == 0] 且 [state == 1 或本次 tick 会调用泵]**：
   snap_234042：**0 行**
   snap_234211：**0 行**
   并且 §3 的两次 4F4: 1->0 全部发生在 state == 0 期间。
=> **Path A 形态在采样中从未出现** ⇒ TEARDOWN_STARVATION = **REFUTED**（样本内）

Path B 形态（state=2 停用）= [4F4 != 0] 且 [state == 2]：
   snap_234042：**164 行**
   snap_234211：**179 行**
   单段 33～63 s，socket 全程存活。
=> **Path B 形态反复出现且占据绝大部分墙钟时间** ⇒ STATE2_INERT_TICK = **STRONG_CANDIDATE**（存在性）
```

## §8 关键反证（任务书 §十二）

```
三次有探针覆盖的 accepted push，全部**恰好落在 state=2 -> state=1 的边界上**：
   23:40:31 : state=2 段结束 23:40:31.255 -> state=1 @31.441 -> state=0 @31.537
   23:41:34 : state=2 段结束 23:41:34.291 -> state=1 @34.488 -> state=2 @34.579
   23:42:10 : state=2 段结束 23:42:09.830 -> state=1 @10.404 -> state=0 @10.468
并且三次的 4F4 都 **!= 0**（socket 存活，值 0x3D5F9F38）。

=> 即在 push 附近，tick **确实进入过 state=1**，消息泵**有**运行机会。
=> 因此 A / B 两条 starvation **都不足以单独解释"没有形成可观测的 0x632680 执行"**。
=> 按任务书 §十二：TEARDOWN_STARVATION = WEAKENED（本轮进一步为 REFUTED 形态）、
   STATE2_INERT_TICK = WEAKENED（作为本次 push 的 blocker）-> 枚举取 **CANDIDATE**。
=> 下一阶段应回到 **message object / service dispatch / indirect call**，而不是继续围绕连接与队列。
```

## §9 message pump starvation 是否观测到

```
观察到 **state=2 长时间运行（33～63 s/段，占墙钟 99.6% 以上）**，
即"泵几乎不被调用"这一现象**确实存在**。
但**没有**观察到"本次 accepted push 因此被饿死"的证据：
三次 push 都伴随一次 state=1 窗口（§8）。
=> MESSAGE_PUMP_STARVATION_OBSERVED = YES（现象层面）
   PUSH_STARVED_BY_IT = NO_OBSERVED（本轮）
```

## §10 其它必填项

```
CLIENT_RECEIVED       = SOCKET_LAYER_STRONG_CANDIDATE（沿用 028 的 FIN/RST 判据） / APPLICATION_RECEIVED = UNKNOWN
28960 / BATTLE RX     = NOT_OBSERVED（battle_srv.log 23:42:30 仍 收包=0 NAT=0 init=0 keyex=0 data=0 会话=0）
state=2 duration      = 62.828 s（snap1 单段）; 33.169 s + 35.251 s（snap2）
4F4->0 duration       = 0.476 s（snap1）; 1.125 s（snap2）
4F8=1 duration        = 0.298 s（snap1）; 33.320 s + 35.800 s（snap2）
TICK_ORDER            = 与 push 的毫秒级先后 **UNKNOWN**（服务端日志只有秒级；探针 1 ms 但 push 的 ms 不可知）
MODIFIED_FILES        = nt10.py（采样器，见卷首 SHA）；其余未改
```

## §11 最终证据等级

```
TEARDOWN_STARVATION = **REFUTED**（样本内 Path A 形态 0 行；两次 4F4: 1->0 均在 state=0 期间）
STATE2_INERT_TICK   = **STRONG_CANDIDATE**（存在性）/ 作为本次 push 的 blocker = **CANDIDATE**（§8）
RUNTIME_632680      = **UNKNOWN**
G6_RUNTIME          = **UNKNOWN**
G7_RUNTIME          = **UNKNOWN**
BATTLE_28960        = **NOT_OBSERVED**
```

## §12 本轮回答的问题

```
问：accepted push 到底是否因为 transport teardown 或 state=2 而无法被 message pump 消费？
答：**两者都不是充分的解释。**
    - Path A（4F4->0 导致泵跳过）在本轮采样中**完全没出现过**（0 行）；
      两次 4F4 清零都发生在 tick 已经处于 state=0 的时候。
    - Path B（state=2 停用）**确实长期存在**（单段 33～63 s，占墙钟 >99.6%），
      但三次 accepted push **都恰好伴随一个 state=1 窗口**（4F4 存活），
      即消息泵在 push 附近**有**运行机会。

因此当前 blocker 的位置已经从"连接/队列"移回 **dispatch 内部**：
  0x85 帧 -> message object -> service dispatch -> 0xB7C900 -> 0x7F1400 -> 0x632680。
这一段的运行时可观测性 **INSTRUMENTATION_BLOCKED**（在不引入 hook/断点的前提下无法直接观察）。

按任务书 §十六 STOP-4：A/B 两条 starvation 都已被显著削弱，
故本轮以 **RUNTIME_DISPATCH_BOUNDARY = INSTRUMENTATION_BLOCKED** 结束，
不继续无限静态追踪，不启动 Battle Server，不做绕过。
```

---

## §13 终局快照（运行结束后补测，证据等级不变）

快照 snap_234737（窗口 23:40:43 → 23:47:37，约 407 s）：

```
state=2 : 3 段，合计 **392.736 s**
            23:42:12.939 -> 23:47:37.255  **324.316 s**（到最后一条记录仍在 state=2）
            23:41:34.579 -> 23:42:09.830   35.251 s
            23:41:01.122 -> 23:41:34.291   33.169 s
state=1 : 4 段，合计 **0.403 s**
            23:41:00.888 -> 23:41:01.120   0.232 s
            23:42:12.748 -> 23:42:12.919   0.171 s
            23:41:34.488 / 23:42:10.404   各 1 点
state=0 : 4 段，合计 18.741 s
4F4=0   : 1 段，合计 1.125 s（23:40:59.456 -> 23:41:00.581，仍在 state=0 期间）
```

**量化（终局）**：在 407 s 的窗口里，**唯一会调用消息泵的 state=1 只占 0.403 s ≈ 0.10%**；
最长的一段 state=2 达 **324 s**，且在记录结束时仍未离开。

两种解读（必须并列，不能只取其一）：

```
解读 A（starvation）：state=2 = 停用态 -> 泵不被调用 -> 入站帧排队不被处理。
解读 B（idle-by-design）：state=2 = 空闲态；state=1 只在有活动时短暂出现，
                        泵是"事件驱动"而非轮询 —— 那么 state=2 本身不是缺陷。
```

**两种解读下结论相同**：三次有覆盖的 accepted push（23:40:31 / 23:41:34 / 23:42:10）
**都恰好落在 state=2 -> state=1 的窗口上**，且 4F4 全部 != 0。
即无论 state=2 是"停用"还是"空闲"，**push 到达时泵都有运行机会** ——
这与 §8 的反证一致：A/B 两条 starvation 都不足以解释未形成可观测的 0x632680 执行。

终局其它核对：

```
this288 / this288_byte = **从未为 1**（0 命中）—— 本轮 A/B 未对齐，G4 必然失败，符合预期
总 accepted push = 5
BATTLE RX = 0（battle_srv.log 23:47:30 仍 收包=0 NAT=0 init=0 keyex=0 data=0 会话=0）
文件终态：codol_crypto.py = E836C63A...（未动） / lobby_server.py = 7BBDC4F2...（未动）
          battle_server.py = 71BB7BEB...（未动） / nt10.py = 4A9628F7...（本轮唯一改动：采样器 +2 字段）
快照留存：DEV-BOOKING\_029\snap_234042.txt / snap_234211.txt / snap_234737.txt
```

（§13 完 · 证据等级与 §11 一致，未升级）

（全文完 · 唯一改动为只读采样器 nt10.py · 未 hook / 未 patch / 未改 Server / 未改客户端）
