# PVE-MATCHING-AB-ALIGN-019
# 验证 matching A/B 对齐是否解除 mmbook accepted 第一守卫

> 2026-10-08 执行。**一次最小、可回滚的 Lobby 服务端单变量实验**（用户授权）。
> 未改客户端（EXE/DLL/内存）、未 patch/hook 客户端、未发包、未动
> SessionId / senderId / accepted response / service / task / sequence / opcode /
> endpoint / Lobby TCP / type-2 / listener / UDP-Battle 参数 / ACE / 28960 / retry。
> 实验后已恢复原始服务端并做 SHA-256 校验。

---

## 0. RESULT

```
RESULT_CASE                = B
AB_ALIGNMENT               = CONFIRMED
AB_GUARD_CAUSALITY         = 0x6326B9 = NECESSARY BUT NOT SUFFICIENT
ACCEPTED_HANDLER_EXECUTED  = NO（未观测到 accepted 分支）
NEXT_GATE                  = ADDITIONAL_ACCEPTED_GUARD

一句话：把 findSessions 会话对象的 #7 u64 从 1 改成 SessionId 之后，
客户端侧 matching+0x3A048/+0x3A04C **确实变成了** (0x55667788, 0x11223344)，
与 accepted 信封的 A/B 完全相等（第一守卫在数值上已满足），
但 0x632680 的 accepted 分支**依然没有执行** —— [matching+0x288] 全程为 0。
⇒ A/B 对齐是**必要非充分**条件，后面还卡着另一道门。
```

---

## 1. 实验前 STATIC CHECK（ACTIVE_AB_RECORD）

### 1.1 客户端反序列化器的字段消耗计数

018 已定位：元素类（0x238 B，ctor 0x806B50，vtable 0xDC79F0）的
vtable[0] = **0x00806F20**，是"从网络流读字段写回 this"的反序列化器。
本轮把它的**读取次数**逐条数清：

```
0x00806F20 内部：
  第一次  call 0xB95D70        ; 复合读取
  第二次  call 0xB76A30 (push 0x40, dest = this+0x128)   ; tag 0x10 字符串
  第三次  call 0xB769A0 (dest = this+0x168)              ; ★ tag 0x0A u64
  第四次  call 0xB76A30 (push 0x40, dest = this+0x170)   ; tag 0x10 字符串

0x00B95D70 内部恰好消耗 5 个字段：
  0xB95DB2  call 0xB76AF0   ; tag 0x13 blob -> this+0x18
  0xB95DD6  call 0xB76AF0   ; tag 0x13 blob -> this+0x10 (cap 8)
  0xB95DF7  call 0xB761E0   ; tag 0x08 u32  -> this+0x11C
  0xB95E21  call 0xB761E0   ; tag 0x08 u32  -> this+0x120
  0xB95E44  call 0xB761E0   ; tag 0x08 u32  -> this+0x124
  （0xB761E0 反汇编确认：push 8 → tag 校验；push 4 → 读 4 字节 → [ecx]）

⇒ 合计消耗 **8 个字段**，顺序为：blob, blob, u32, u32, u32, string, **u64**, string
```

### 1.2 与服务端 21/5 会话对象逐一对照（离线 dump）

用 _019_dump_obj.py 直接调用 build_mission_session_object(playlist=10)：

```
#1  off=0x000  tag=0x13 blob len=24   (地址块)
#2  off=0x01E  tag=0x13 blob len=8    data=0100000000000000   <- SessionId blob
#3  off=0x02C  tag=0x08 u32  = 0
#4  off=0x031  tag=0x08 u32  = 0
#5  off=0x036  tag=0x08 u32  = 1      <- Players
#6  off=0x03B  tag=0x10 str  = 'coop_take_mp_fav_tropical'
#7  off=0x056  tag=0x0A u64  = 1      bytes=0a0100000000000000    ★★★
#8  off=0x05F  tag=0x10 str  = 'localhost'
...
#28 off=0x0CA  tag=0x0A u64  = 1      bytes=0a0100000000000000
```

**⇒ ACTIVE_AB_RECORD = #7**（CONFIRMED）
理由：字段**种类序列**与**数量**同时对齐 —— 客户端读 8 个字段
（blob,blob,u32,u32,u32,string,u64,string），服务端 #1..#8 正是
（blob,blob,u32,u32,u32,string,u64,string）；
#28 位于客户端本次读序之外（它在 #9..#27 之后）。

因此本轮**只改 #7**，不碰 #28（遵守"一次只运行一个实验"）。

### 1.3 本轮新增的独立佐证（实验后回看，见 §3.3）

客户端的 mmbook **请求**首字段就是同一个 u64：
baseline = 0a 01 00 00 00 00 00 00 00；测试版 = 0a 88 77 66 55 44 33 22 11。
即客户端把 #7 的值**回显**进 booking 请求 —— 这是对"#7 就是 active record"
的**行为级**证据，强于纯字段序推断。

---

## 2. 实验设置（保护 / 单变量 / 回滚）

### 2.1 备份与哈希

```
备份（实验前）
  DEV-PUBLISHER-RESTORE\REF_LOBBY_KIT\codol_crypto.py.bak_019_20261008_200724   42853 B
  DEV-PUBLISHER-RESTORE\REF_LOBBY_KIT\lobby_server.py.bak_019_20261008_200724   76428 B

SHA-256
  codol_crypto.py  原始 = E836C63AF75DD82EF6F3B07EF63FAE48B044B3B5047336127093C92B07644607
  codol_crypto.py  测试 = 30AB0C5970F396A999405412DEC11071907169B7DEA3050107349BE8EA27EB32
  lobby_server.py       = 2E32E719AD548E93B66E306D2566E132D34512F69248FC7697815970AFF21DF1（从未修改）
```

### 2.2 修改位置（唯一一行）

```
文件  codol_crypto.py   build_mission_session_object()
L542   -    ob.u64(1)                                       # 7
L542   +    ob.u64(0x1122334455667788)                       # 7  [019 test]
（#28 = L551 ob.u64(1) 未动；#2 SessionId blob 未动；lobby_server.py 未动）
diff 行数 = 2（一删一增）
```

### 2.3 变量

```
唯一变量  ACTIVE_AB_RECORD 的 tag-0x0A u64
  原值    0x0000000000000001        -> low32=0x00000001, high32=0x00000000
  测试值  0x1122334455667788        -> LOW32=0x55667788, HIGH32=0x11223344

离线 dump 验证（测试版）
  #7  off=0x056 tag=0x0A value=1234605616436508552 (0x1122334455667788) bytes=8877665544332211
  #2  off=0x01E 仍为 0100000000000000      （未动）
  #5  off=0x036 仍为 1                     （未动）
```

### 2.4 观测手段

```
只读采样线程 _accprobe（017 加入，开关 accepted-state-probe.on 仍在）
  采样间隔约 6~11 ms；变化即记录；对 [matching+0x288] 有 ALERT 闩锁
  关键字段：matching+0x1C / +0x278 / +0x283 / +0x288(word)
            matching+0x3A048 / +0x3A04C (A/B)
            [0x0849B61C] flag；netcore +0x4F4/+0x4F8；transport +0xC8/+0x644/+0x5E8
            [0x084ABA7C] dw state
battle_server.py  收包统计（每 30s 一行）
netstat/Get-NetUDPEndpoint  28960
启动路径  既有提权代理（pid 21428, debug_privilege=true）+ run_all.py
```

---

## 3. 运行记录

### 3.1 BASELINE（原始服务端，20:08-20:13）

```
findSessions response   236 B，单条，map=coop_take_mp_fav_tropical playlist=10
  #7 u64 = 1   (off 0x056)
mmbook request payload  0a 01 00 00 00 00 00 00 00 13 08 1d ...        [20:09:08]
accepted senderId       SessionId 0x1122334455667788
  ⇒ accepted A = 0x55667788   B = 0x11223344

probe（accepted_state.txt.test019_20261008_201410）
  lines=328   this288_byte=1: 0
  A=0x00000001: 11 次     B=0x00000000
  A=0x55667788: 0 次      B=0x11223344: 0 次
  典型事件（20:09:08）：
    [20:09:08.277] this278=0x0001 this1C=0x0E374650 flag=1  A=0 B=0
    [20:09:08.353] this288_word=0x0100 this278=0x0101  A=0x00000001 B=0x00000000 t_C8=4
    [20:09:08.431] 复位
  0x6326B9  0x55667788 != 1      -> FAIL
  0x632680 accepted 分支         -> 未执行
UDP / Battle
  battle_srv.log 收包 = 0（唯一取值）
```

### 3.2 TEST（#7 = SessionId，20:21-20:24）

```
findSessions response   236 B（同上），#7 u64 = 0x1122334455667788
mmbook request payload  0a 88 77 66 55 44 33 22 11 13 08 1d ...        [20:22:27/32/36]
accepted senderId       SessionId 0x1122334455667788（未动）
  ⇒ accepted A = 0x55667788   B = 0x11223344

probe（accepted_state_019test.txt）
  lines=267   this288_byte=1: 0    ALERT: 0
  A=0x55667788: 72 次     B=0x11223344: 72 次      ← ★ 对齐成功
  典型事件（20:22:36，mmbook accepted 推送同一秒）：
    [20:22:36.642] this278=0x0001 this1C=0x0E374650 flag=1 A=0x55667788 B=0x11223344
    [20:22:36.648] this278=0x0101 A=0x55667788 B=0x11223344
    [20:22:36.654] this288_word=0x0100 this278=0x0101 A=0x55667788 B=0x11223344 t_C8=4
    [20:22:36.677] this278=0x0000 this288_word=0x0000 A=0x55667788 B=0x11223344
    （之后 A 才在 20:22:41.665 被清回 0）
  0x6326B9  cmp 0x55667788, 0x55667788 -> 数值上 PASS
  0x632680 accepted 分支            -> 仍未执行（this288 始终 0）
UDP / Battle
  battle_srv.log 收包 = 0（唯一取值）
  Get-NetUDPEndpoint 28960 只有我们自己的监听 0.0.0.0:28960 (pid 2404)
  客户端侧无任何到 28960 的连接
客户端对推送的反应（与 baseline 完全一致）
  [20:22:32] -> 0x85 推送 type=2 seq=1012 ... ; 对端关闭 ; 立即重连
  [20:22:36] -> 0x85 推送 type=2 seq=1022 ... ; 对端关闭 ; 立即重连
```

---

## 4. 必须记录的字段汇总

```
RESULT_CASE                = B
ACTIVE_AB_RECORD           = #7（CONFIRMED；另由 mmbook 请求回显独立佐证）
ORIGINAL_AB                = u64 0x0000000000000001  -> (A,B) = (0x00000001, 0x00000000)
TEST_AB                    = u64 0x1122334455667788  -> (A,B) = (0x55667788, 0x11223344)
MATCHING_AB_AFTER          = A=0x55667788, B=0x11223344（72 个采样点）
RESPONSE_AB                = A=0x55667788, B=0x11223344（envelope senderId = SessionId）
GUARD_6326B9               = 数值上 PASS（0x55667788 == 0x55667788），
                             但无可观测效果（accepted 分支未执行）
ACCEPTED_HANDLER_EXECUTED  = NO（未观测到）
THIS_288_AFTER             = 0（测试全程 267 个采样点，this288_byte=1 命中 0 次；ALERT 未触发）
FLAG_849B61C_AFTER         = 1（⚠ 不是 accepted 判据；017 已证其有多条非 accepted 写入来源）
UDP_SOCKET_ACTIVITY        = NOT_OBSERVED（本轮未做 socket API 级观测）
CLIENT_UDP_28960           = FAILED（无任何到 28960 的连接/发送）
BATTLE_RX_COUNT            = 0
AB_ALIGNMENT               = CONFIRMED
AB_GUARD_CAUSALITY         = 0x6326B9 = NECESSARY BUT NOT SUFFICIENT
NEXT_GATE                  = ADDITIONAL_ACCEPTED_GUARD
```

---

## 5. CASE 判定

对照任务给定分支：

```
CASE A（对齐 + handler 执行 + this288=1）           -> 不成立（this288=0）
CASE B（A/B 对齐，但 handler 不执行）               -> ★ 成立
        ⇒ 0x6326B9 = NECESSARY BUT NOT SUFFICIENT
CASE C（改后 matching 仍为 1/0）                    -> 不成立
        （matching 确实变成了 0x55667788/0x11223344，说明 #7 就是 active record）
CASE D（handler 执行但 this288 不置 1）             -> 无法判定，因无证据表明 handler 被进入
        ※ 说明见下
CASE E（handler 执行 + this288=1 但 UDP=0）         -> 不成立
```

### 5.1 关于 CASE D 的边界（必须写明）

本轮判定"accepted 分支未执行"的依据是 [matching+0x288] 从未置 1。
该字段是 0x63280B 的**唯一**写入点（017 全镜像扫描确认），且紧随其后的
0x62F6C0 不触碰它，因此"执行过就必然可观测"。

但"**0x632680 是否被进入过**"仍然无法区分：
0x632680 有若干**不写 +0x288** 的早退出口 ——
0x632695（byte[+0x278]==0）、0x6326A2（[0x76446B0] >= 3）、
0x6326B0（[+0xE360] < 0）、0x6326BF / 0x6326CE（A/B 不等）、
0x6326E9（strncmp 不等）、0x632705 / 0x632710（预留项二次校验）。
它们都不产生持久可读副作用。
⇒ 严格表述：**accepted 分支未执行**；**函数是否被进入 = UNKNOWN**。
这不影响 CASE B 的结论（A/B 对齐没有带来行为变化）。

---

## 6. 本轮新增的两条硬证据

### 6.1 客户端把 #7 回显进 mmbook 请求（ACTIVE_AB_RECORD 的行为级确认）

```
BASELINE  [20:09:08] payload(45): 0a 01 00 00 00 00 00 00 00 13 08 1d ...
TEST      [20:22:32] payload(45): 0a 88 77 66 55 44 33 22 11 13 08 1d ...
          [20:22:36] payload(45): 0a 88 77 66 55 44 33 22 11 13 08 1d ...
（除该 8 字节外，两次请求逐字节相同）
```

⇒ 客户端拿去 booking 的那个 u64，正是会话记录 #7。
  这同时说明：A/B 不匹配**不是**客户端"没读到我们改的字段"，而是两边**值**不同。
  本轮把值改对之后，客户端的 booking 引用也随之变化 → 修改确实生效到了客户端。

### 6.2 客户端的协议级反应**没有变化**

```
baseline: 推送后 "对端关闭" + 立即重连
test    : 推送后 "对端关闭" + 立即重连   （2/2 事件，与 baseline 逐条同型）
```

⇒ 仅仅让 A/B 数值相等，并未让客户端"接受"这条消息；
  它的反应仍像"收到了一条不该在这个通道出现的帧"。
  这条现象与 018 NEXT_GATE §3 提出的候选一致：
  **accepted 目前是以 marker=0x02 推送发出的**，而调用 0x632680 的
  0x7F1400 任务分派器位于 **marker=0x01（任务应答）** 通道。

---

## 7. NEXT_GATE = ADDITIONAL_ACCEPTED_GUARD

A/B 对齐已排除，下一道门在**更上游**。按可检验性排序：

```
1. 【通道 / marker —— 最高优先】
   现在 accepted 走 build_push()，明文 marker = 0x02（服务端推送）。
   而 0x7F1400（唯一调用 0x632680 的分派器）只出现在函数指针表 0xDE080C 里，
   属于任务应答侧。需静态确认：
     0x02 推送是否也会被派发到 0x7F1400；
   若不会 → 应把 accepted 改成 **6/14 的应答对象**（marker 0x01，replyId = 请求 seq），
   而不是独立推送。这条能同时解释：
     · A/B 对齐后行为毫无变化
     · 客户端每次都在收到推送后立刻断开重连
     · 客户端始终没有后续 setRoomData

2. 【booking-armed 窗口时序】
   实测 byte[matching+0x278]（0x63268D 的守卫）只在请求前后约 20~30 ms 为 1：
     test 20:22:36.642 (=0x0001) -> .648 (=0x0101) -> .677 (=0x0000)
   若应答在 0x278 已被清掉之后才被处理，0x632695 会直接跳到 0x6328EB 退出。
   需要测"应答到达时刻 vs 0x278 置 1 窗口"的先后（只读、不改变量）。

3. 【其它未观测守卫】
   [0x76446B0] < 3   （0x63269B/0x6326A2）
   [matching+0xE360] >= 0 （0x6326AA/0x6326B0）
   这两个字段本轮**没有采样**，属于纯静态待查项。
```

**不要再动 A/B**：AB_ALIGNMENT 已 CONFIRMED，继续改值不会带来新信息。

---

## 8. 恢复与校验（Hard Stop 已执行）

```
1. 恢复    Copy-Item codol_crypto.py.bak_019_20261008_200724 -> codol_crypto.py
2. SHA-256 恢复后 = E836C63AF75DD82EF6F3B07EF63FAE48B044B3B5047336127093C92B07644607
           = 原始值（逐字节一致）                                  ✔
   lobby_server.py 全程未改，SHA-256 = 2E32E719AD548E93B66E306D2566E132D34512F69248FC7697815970AFF21DF1  ✔
3. 标记    源文件中 "[019 test]" 已不存在；ob.u64(1) 出现次数 = 2（#7 与 #28 均已还原） ✔
4. 日志    已归档，见 §10
5. 进程    游戏与 run_all/nt10/lobby_server/battle_server 均已清理（残留计数 = 0）
6. 未做第二种变量实验（CASE B 不构成"第一种实验证明 active record 不是目标记录"）
7. 未宣布 Battle 成功（无任何 Battle 后续证据）
```

---

## 9. 纪律核对

```
客户端 EXE / DLL / 内存            = 未修改
客户端 patch / hook                = 无新增（沿用既有 nt10 注入与只读采样）
发包                               = 无手工发包
SessionId                          = 未修改（0x1122334455667788）
senderId                           = 未修改
accepted response / message        = 未修改
service / task / sequence / opcode = 未修改
endpoint / Lobby TCP               = 未修改
type-2 / listener                  = 未触碰
UDP / Battle 参数 / 28960          = 未修改
ACE / TenProtect                   = 未触碰、未绕过
retry logic                        = 未修改
服务端改动                         = 仅 codol_crypto.py 一行（#7 的值），实验后已还原
"顺手修"其它字段                    = 无
```

---

## 10. 实验产物（全部保留）

```
报告      DEV-BOOKING\PVE-MATCHING-AB-ALIGN-019.md
工具      DEV-BOOKING\scripts\_019_dump_obj.py   （离线 dump 21/5 会话对象字段）

服务端备份
  REF_LOBBY_KIT\codol_crypto.py.bak_019_20261008_200724
  REF_LOBBY_KIT\lobby_server.py.bak_019_20261008_200724

BASELINE 证据（原始服务端）
  REF_LOBBY_KIT\accepted_state.txt.test019_20261008_201410      （328 行）
  REF_LOBBY_KIT\lobby_srv.log.test019_20261008_201410
  REF_LOBBY_KIT\battle_srv.log.baseline019_20261008_200806
  REF_LOBBY_KIT\n10_019_base.txt

TEST 证据（#7 = SessionId）
  REF_LOBBY_KIT\accepted_state_019test.txt                     （267 行）
  REF_LOBBY_KIT\lobby_srv_019test.log
  REF_LOBBY_KIT\battle_srv_019test.log
  REF_LOBBY_KIT\n10_019_test2.txt

过程残留（第一次测试轮未触发 PvE，0 个 booking 事件，保留作记录）
  REF_LOBBY_KIT\accepted_state.txt.test019b_20261008_202115
  REF_LOBBY_KIT\lobby_srv.log.test019b_20261008_202115
```

---

## 11. 结论

```
A/B 对齐（把 findSessions 会话对象 #7 的 u64 从 1 改成 SessionId）：

  (1) 成功让客户端 matching+0x3A048/+0x3A04C = (0x55667788, 0x11223344)
      —— 与 accepted 信封 A/B 完全相等（72 个采样点）
  (2) 并且被客户端**行为级确认**：它把同一个 u64 回显进了 mmbook 请求
  (3) 但 0x632680 的 accepted 分支**依旧没有执行**（[matching+0x288] 全程 0）
  (4) 客户端对 push 的协议级反应与 baseline 一模一样（立即断开 + 重连）
  (5) Battle UDP 依然 0 收包、无 28960 连接

⇒ 第一守卫 0x6326B9 是**必要非充分**条件。
   下一道门最可能是"消息通道"（marker 0x02 推送 vs 0x01 任务应答），
   其次是 booking-armed 窗口（byte[+0x278]）的时序。
   NEXT_GATE = ADDITIONAL_ACCEPTED_GUARD。
```



