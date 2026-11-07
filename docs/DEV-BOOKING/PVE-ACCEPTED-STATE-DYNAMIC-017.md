# PVE-ACCEPTED-STATE-DYNAMIC-017
# 动态确认 0x632680 的 mmbook accepted 分支是否执行，以及 accepted 后状态变化

> 2026-10-08 执行。**动态 + 静态**。未修改 client 指令、未新增 hook、未 patch、
> 未伪造 UDP/DTLS、未手工发包、未做 ACE/TenProtect bypass。
> 未修改 senderId / SessionId / service / type / sequence / message / endpoint / 28960。
> 未重新设计 Booking response。
>
> 唯一新增：经用户显式批准，在 nt10.py 里加了一个**只读**采样线程
> （仅 ReadProcessMemory；不写内存、不装 hook、不改指令），开关文件
> `accepted-state-probe.on`。启动客户端走既有合法提权代理 + `run_all.py`。

---

## 0. 结论先行

```
ACCEPTED_WIRE              = CONFIRMED（9 次 'mmbook accepted' 实际发出）
ACCEPTED_HANDLER_EXECUTED  = NO   ← mmbook accepted 分支（0x63280B）从未执行
ACCEPTED_STATE_TRANSITION  = FAILED
THIS_288_BEFORE            = 0x0000 (byte@+0x288 = 0)
THIS_288_AFTER             = 0x0000 (byte@+0x288 = 0)   ← 唯一标记从未置 1
FLAG_849B61C_BEFORE        = 0
FLAG_849B61C_AFTER         = 1   ← 但该写入**不是** accepted 分支（见 §8.2）
UDP_SOCKET_ACTIVITY        = NOT_OBSERVED
CLIENT_UDP_28960_SEEN      = FAILED
BATTLE_RX_COUNT            = 0
RESULT_CASE                = C
```

**一句话**：客户端确实收到了 `mmbook accepted`，但 `0x632680` 的 accepted
分支**没有执行**。机制已定位到**第一道 A/B 守卫**：客户端内存里
`[matching+0x3A048]` = **0x00000001**、`[+0x3A04C]` = **0x00000000**，
而响应信封的 senderId 拆成 A=0x55667788 / B=0x11223344（013/012 已确认 wire 值），
`0x6326B9 cmp eax,[esi+0x3A048]` 直接 `jne 0x632916` 退出 →
accepted 分支在**构造上不可达**。故不存在 accepted state transition，
也就没有 accepted → Battle 触发，`battle_srv` 全程 收包=0。

---

## 1. FACT_BASELINE

### 1.1 承接（未重查，未推翻）

```
senderId / A-B（wire）        = SessionId 0x1122334455667788，LOW/HIGH 拆分（013）  已关闭
listener [matching+4]         = 7/7 NOT_BATTLE（015）                              已关闭
[0x0849B61C] 的 consumer      = 0x7CB1E2 / 0x7CFA87，UI/telemetry（014/015）        已关闭
type-2 network object         = Demonware lobby TCP 连接（016，TYPE2_TO_UDP REFUTED）已关闭
Lobby socket 0xB81EF0/0xBA4080= Lobby 主连接，非 Battle（015/016）                   已关闭
0x77FBF0                      = IPX LAN broadcast，非 Battle                         已关闭
```

### 1.2 本轮新增（静态，用于给出动态判据）

**(a) accepted 分支的唯一标记**

```asm
0x00632680  accepted handler 入口（__thiscall, this = [0x082E13FC], ret 0x14）
0x0063268D  cmp byte [esi+0x278], 0
0x00632695  je  0x6328EB                 ; 未 armed -> 直接清 A/B 返回
0x0063269B  cmp dword [0x76446B0], 3
0x006326A2  jge 0x6328EB
0x006326B6  mov eax, [ebp+8]             ; A（信封 senderId 低 32 位）
0x006326B9  cmp eax, [esi+0x3A048]       ; ★★ A 守卫
0x006326BF  jne 0x632916                 ; ★ 不匹配 -> 退出，且**不清 A/B**
0x006326C5  mov ebx, [ebp+0xC]           ; B
0x006326C8  cmp ebx, [esi+0x3A04C]       ; ★★ B 守卫
0x006326CE  jne 0x632916
0x006326DA  push 0xDC69B0 "mmbook accepted"
0x006326DF  call 0xC3C678                ; strncmp(..., 0xF)
0x006326E9  jne 0x632876
0x006326EF  eax = [esi+0xE360]           ; 预留项索引
0x006326FB  edx = [esi+eax*0x238+0x75D8]
0x00632702  cmp edx, [ebp+8]  / jne 0x632712
0x00632707  eax = [esi+eax*0x238+0x75DC]
0x0063270E  cmp eax, ebx      / je  0x632736   ; ★★ 全部通过 -> accepted 成功路径
0x00632712  call 0x62F6C0                ; 超时/内层不匹配：清 A/B
...
0x00632809  call edx                     ; [esi.vt+0x148] 状态迁移
0x0063280B  c6868802000001  mov byte [esi+0x288], 1   ; ★★★ accepted 分支唯一标记
0x00632812  call 0x62F6C0                ; 清 A/B
0x0063281E  call edx                     ; [esi.vt+0x5C] = 0x62FDE0 type-2 门控
0x00632827  c6051cb6490801  mov byte [0x849B61C], 1
```

**全镜像扫描（确定性）**：所有 `mov byte [reg+disp32], imm8` 共 2462 条，
其中 disp=0x288 且 imm=1 的 **只有 0x0063280B 一处**。
另一处触碰该字段的是 `0x0062F47A  mov word [edi+0x288], bx`（bx=0，清零）。

⇒ `byte[[0x082E13FC]+0x288] == 1  ⟺  accepted 分支执行过`。
  该判据**唯一且持久**：`0x62F6C0（紧随其后的调用）经复核**不触碰 +0x288**
  （只清 [esi+0x3A048]/[+0x3A04C]/[+0x3A050]/[+0x3A090]）。
  一旦置 1 会保持到下一次 booking 复位（0x62F460 族 或 0x634B13 的 word 清零）。

**(b) A/B 的写者全表（用于排除误判）**

```
[matching+0x3A048] 全部引用：
  0x62C280  mov [ebx+0x3A048], edi    ; 复位族（edi=0）
  0x62F6C5  mov [esi+0x3A048], eax    ; 在 0x62F6C0 内，清零（仅 0x632680 调用）
  0x62F717  mov [esi+0x3A048], ebx    ; 在 0x62F6F0 内，先清零
  0x62F73C  mov [esi+0x3A048], ecx    ; 在 0x62F6F0 内，ecx = [edi+0x168]（★ 唯一赋值）
  0x6328F7  mov [esi+0x3A048], edi    ; 在 0x632680 内（edi=0），清零
  0x6326B9  cmp eax, [esi+0x3A048]    ; ★ 守卫读
0x62F6C0 的直调者：0x632712 / 0x632812 / 0x63288C —— 全部在 0x632680 内
0x632916（A/B 不匹配出口）经反汇编确认只是 pop/ret 0x14，**不清 A/B**
```

---

## 2. 动态环境与手段

```
提权代理        CODOLServer\_mainline\elevated_agent.py
                pid=21428 port=54901 debug_privilege=true（UAC 人工批准）
启动            agent_client.py run python run_all.py --secs 420
Run1            n10_017.txt / n10_017_a3.txt（420.9s，正常退出 rc=0）
Run2            n10_017b.txt（retry 后成功；18:11:59 有一次重启，会覆盖 accepted_state.txt）
服务            auth 127.0.0.1:3074 TLS / lobby 127.0.0.2:3074 明文 / battle 0.0.0.0:28960 UDP
开关            firingrange-booking-push.enabled 存在（既有，本轮未增删）
观测通道        nt10 早期句柄 + 只读采样线程（见 §2.2）
```

### 2.1 ACE 阻断外部观测（再次确认，写进接力手册）

用提权代理跑独立 python 进程尝试读游戏内存：

```
game pid = 21716
OpenProcess -> 304 err 0
[global] [0x082E13FC] matching = READ-FAIL
[global] [0x0849B61C] flag     = READ-FAIL
[global] [0x08269774] netcore  = READ-FAIL
[global] [0x084ABA7C] dwstate  = READ-FAIL
```

⇒ **OpenProcess 成功，但 ReadProcessMemory 全失败**（HANDOFF §7.2 说的"后开的
  OpenProcess 会被拒"，实际被拒的是读）。
  ⇒ 唯一可用的内存通道 = nt10 启动早期拿到的句柄。这是硬约束。

### 2.2 本轮新增的只读采样（用户批准）

```
文件    DEV-PUBLISHER-RESTORE\REF_LOBBY_KIT\nt10.py     函数 _accprobe
开关    accepted-state-probe.on
输出    accepted_state.txt（变化即记 + 1s 心跳 + ALERT 闩锁）
采样    每 5ms 一次（实测有效 ≈ 6~11ms/次），13 个字段：
        exe_base = 0x00400000（实测确认，静态 VA 直接可用）
        [0x082E13FC] matching            matching+0x1C / +0x278 / +0x283 / +0x288(word)
        matching+0x3A048 / +0x3A04C (A/B) [0x0849B61C] flag
        [0x08269774] netcore / +0x4F8     [netcore+0x4F4] transport
        transport+0xC8 / +0x644 / +0x5E8  [0x084ABA7C] dw state
写入    仅写本地日志文件；对目标进程**只有 ReadProcessMemory**
回滚    删 accepted-state-probe.on（或还原 nt10.py 的 _accprobe 段）
```

---

## 3. Test 1：wire accepted（ACCEPTED_WIRE）

**Run1**（lobby_srv_run1.log）——4 次实际推送：

```
[18:03:41] 6/14 命中 'mmbook' -> push 'mmbook accepted'(data=20)
[18:03:41] -> 0x85 推送 type=2 seq=1051(请求seq+1000, 避开客户端号段) (98 字节 body=51)
[18:03:41] 对端关闭
[18:04:07] 6/14 命中 'mmbook' -> push 'mmbook accepted'(data=20)
[18:04:07] -> 0x85 推送 type=2 seq=1020 (...) (98 字节 body=51)
[18:04:07] 对端关闭
[18:04:37] 6/14 命中 'mmbook' -> push 'mmbook accepted'(data=20)
[18:04:37] -> 0x85 推送 type=2 seq=1020 (...) (98 字节 body=51)
[18:04:37] 对端关闭
（共 4 次）
```

**Run2**（lobby_srv.log）——5 次：18:11:24 / 18:11:32 / 18:11:42 / 18:11:47 / 18:12:48。

**合计 9 次 `mmbook accepted` 实际写出**（日志在 conn.sendall(pf) 之后）。

每次请求侧链路一致：

```
11/13 createRoom -> roomId=0x1122334455667788
28/1  任务参数
21/5  findSessions payload 35B -> 解析值=[1, 0, 10, -695030357] -> PvE coop session 对象 236B
6/14  mmbook -> push 'mmbook accepted'（marker=2 推送, seq=请求seq+1000）
       对端关闭（客户端立即 FIN，随后立刻重连）
```

### 3.1 ACCEPTED_WIRE

```
ACCEPTED_WIRE = CONFIRMED
  6/14 的空 ACK（seq=请求seq）与 type=2 推送（seq=请求seq+1000）都已实际发出；
  9/9 次客户端随后立刻关闭大厅连接并重连。
```

---

## 4. Test 2：accepted 分支执行（ACCEPTED_HANDLER_EXECUTED）

判据见 §1.2(a)：`byte[matching+0x288]` 是 accepted 分支的唯一写入点（0x63280B），
且 0x62F6C0 不触碰它 ⇒ 一旦执行，该字节保持 1。

### 4.2 实测结果

```
Run1（40ms 采样，accepted_state_run1.txt）
  probe 行数                     281
  this288_byte = 1 的采样数      0
  this288_word 取值分布          0x0000 x22 / 0x0100 x3 / 0xFFFF(初始不可读) x1
  ALERT                          0
  所有 CHG 行 this288_byte 均为 0（含 3 个 booking 事件窗口）

Run2（≈6~11ms 采样，accepted_state.txt）
  probe 行数                     433
  this288_byte = 1 的采样数      0
  ALERT                          0
  A=0x00000001 的采样数          8（全部落在 booking armed 窗口内）
```

★ 关键：Run2 的采样是**变化即记录**（tuple 内含 m288），
   所以"变成 1"本身必然触发一条 CHG；只有 <6ms 内被复位才会漏。
   而 0x63280B 与任何复位点之间隔着 ~0x27 字节 handler 代码，
   **不存在**能在一个采样周期内把 +0x288 置 1 又清掉的路径。
   ⇒ 否定是**构造上稳健**的，不只是"没抽到"。

### 4.3 机制定位（为什么没执行）

Run2 在 18:12:48 的 booking 事件被完整捕获（与 lobby 日志时间精确对齐）：

```
[18:12:48.296] CHG ... this288_byte=0 this288_word=0x0000 this278=0x0000 this1C=0 flag849B61C=1
[18:12:48.338] CHG ... this288_byte=0 this288_word=0x0100 this278=0x0101 this1C=0x0E374650
                      trans=0x3DC17FD0 t_C8=2 t_5E8=3 dw=0x02 **A=0x00000001 B=0x00000000**
[18:12:48.348] CHG ... 同上，t_C8=4            A=0x00000001 B=0x00000000
[18:12:48.389] CHG ... this288_word=0x0000 this278=0x0000 this1C=0   A=0x00000001 B=0x00000000
[18:12:53.338] CHG ...                        A=0x00000000 B=0x00000000
```

结论链：

```
(1) 客户端 [matching+0x3A048] = 0x00000001，[+0x3A04C] = 0x00000000
    （0x62F6F0 从预留项 [edi+0x168]/[edi+0x16C] 拷来；
     与 012 实测 "findSessions 解析值=[1, 0, 10, -695030357]" 的前两个 u32 一致）
(2) 响应信封 senderId = SESSION_ID = 0x1122334455667788
    （lobby_server.py L458 / L851 / L909，本轮复核）
    ⇒ 由 0x7F1400 拆成 A=0x55667788 / B=0x11223344（013）
(3) 0x6326B9: cmp 0x55667788, 1   -> jne 0x632916   ★ 第一道守卫即退出
    0x632916 路径不清 A/B、不写 [this+0x288]、不写 [0x849B61C]
(4) ⇒ accepted 分支（0x63280B 之后的一切）**不可达**
```

这既解释了 §4.2 的否定结果，也是**独立于采样**的机制性证据。

### 4.4 必须说明的边界

```
ACCEPTED_HANDLER_EXECUTED（= accepted 分支）            = NO        CONFIRMED
0x632680 是否被"进入"过（走到 0x6328EB / 0x632916）     = UNKNOWN
```

理由：进入/退出这些出口**不产生持久可读副作用**（不清 A/B、不写新字段），
在没有断点/hook 的前提下无法区分"从未进入"与"进入但被守卫拦下"。
**这不影响本轮结论**：无论是否进入，A/B 守卫都使 accepted 分支不可达。

---

## 5. Test 3：accepted 状态前后

```
THIS_288_BEFORE        = 0x0000   (byte@+0x288 = 0)
                        沿整个观测窗口，byte@+0x288 恒为 0
THIS_288_AFTER         = 0x0000   (byte@+0x288 = 0)
                        ★ 从未出现 1，也从未出现 word=0x0101
                        booking armed 期间观察到 word = 0x0100
                        = byte@+0x288=0, byte@+0x289=1

FLAG_849B61C_BEFORE    = 0
FLAG_849B61C_AFTER     = 1        （Run1 首次 booking 事件后置 1 并保持；
                                   Run2 在 18:12:48.296 置 1）
                        ⚠ 该 1 **不是** accepted 分支写的 —— 见 §8.2
```

对照：同一个 booking armed 窗口内（Run1 18:03:41.527）还观察到

```
this278  = 0x0101   (byte@+0x278 = 1，即 booking armed；0x63268D 守卫会通过)
this283  = 0
this1C   = 0x0E374650  （非 0，即 0x62FDE0 的 GATE-A 条件成立）
t_C8 / t_644 / t_5E8 / net4F8 / dw = 4或2 / 0 / 0或3 / 0或1 / 0x00或0x02
```

---

## 6. Test 4：accepted 之后的网络行为

从每条 accepted timestamp 起观察 0 ~ 10s：

```
battle_srv.log（Run1 + Run2 全程）
  [stat] 收包=0 NAT=0 init=0 keyex=0 data=0 会话=0   （每 30s 一行，两轮全部为 0）
  收包取值集合 = {0}
nt10 [net] / netstat
  只有 127.0.0.1:3074 [ESTABLISHED]（大厅）；
  无任何到 28960 的 UDP 连接或发送记录
客户端反应
  9/9 次：收到 mmbook accepted 推送后**立刻关闭大厅连接**并重连
  （"对端关闭" 后立即出现新的 "=== 大厅连接建立 ==="；优雅 FIN，非 RST）
```

```
UDP_SOCKET_ACTIVITY   = NOT_OBSERVED
CLIENT_UDP_28960_SEEN = FAILED
BATTLE_RX_COUNT       = 0
```

说明：本轮**没有**做 socket/bind/sendto/recvfrom 的 API 级观测（那需要额外 hook 或
连接级抓包，超出本轮授权），所以记 NOT_OBSERVED 而非 "CONFIRMED absent"；
但"没有发生"由 battle 收包=0 + 无 28960 连接双重支撑。

---

## 7. 附带收获：016 的 type-2 / DW 模型被动态证实

Run1 18:03:11 捕获到完整的 DW 连接建立序列（016 静态模型的独立动态验证）：

```
[18:03:05]     matching=0x3DB5ADE0（matching 单例创建）
[18:03:09.819] net=0x3DBDFEF8（网络核单例）            net4F8=0
[18:03:11.169] trans=0x3DBFA210  t_C8=1  t_644=0  t_5E8=0  dw=0x01
[18:03:11.211] trans=0x3DBFA210  t_C8=2  t_644=0  t_5E8=1  dw=0x01
[18:03:11.297] trans=0x3DBFA210  t_C8=2  t_644=0  t_5E8=2  dw=0x01
[18:03:11.642] trans=0x3DBFA210  t_C8=2  t_644=0  t_5E8=3  net4F8=1  dw=0x02
[18:03:44.190] （重连后同样收敛到 t_C8=2 / t_5E8=3 / net4F8=1 / dw=0x02）
```

逐字段对上 016：

```
0xBA40A0 [t+0xC8]=1 -> 0xBA4127 [t+0xC8]=2                ✔ 实测 t_C8 1->2
0xBA40AA [t+0x5E8]=0，状态机随后推进                        ✔ 实测 0->1->2->3
0xB83A88 kind=4 报文置 [sing+0x4F8]=1                      ✔ 实测 net4F8 0->1
0x7F385A type==2 -> [0x84ABA7C]=2（"DW_LOBBY_CONNECTED"）  ✔ 实测 dw 0x01->0x02
0xBA0780 [t+0x644]==0 && [t+0xC8]==2 && [t+0x5E8]==3 -> type 2
0xB7A670 [sing+0x4F8]!=0 -> 归一化 type 2                   ✔ 两者同时成立
```

⇒ 016 的 `type-2 = Demonware lobby TCP 连接 / DW_LOBBY_CONNECTED` 得到实测确认。
  推论：若 accepted 分支真的执行，其 0x63281E 调用的 0x62FDE0 会返回 1（type-2 存在）
  → 跳过 listener 广播。与 015/016 的预测一致，只是本轮 accepted 分支没走到那一步。

---

## 8. 与既有结论的关系（含两处更正）

### 8.1 与 013 的关系（不是重开 A/B 端序问题）

013 关闭的是**字节序 / 拆分方向**：wire senderId 的 LE u64 → LOW32/HIGH32。
本轮**没有**触碰这个结论，也没有重新推导它。

本轮新增的是一个**字段身份（field identity）**事实：

```
013 的推理链：item+0x168 = SessionId 低 32 位 = 0x55667788   ← 这一步是**假设**
             0x62F73C: [matching+0x3A048] = [item+0x168]
             ⇒ 推断 [matching+0x3A048] = 0x55667788
本轮实测：   [matching+0x3A048] = 0x00000001，[+0x3A04C] = 0x00000000
```

即：**客户端在 0x62F6F0 处取的 item+0x168 并不是 SessionId 低 32 位，而是 1**。
这与 012 自己的实测 `findSessions 解析值=[1, 0, 10, -695030357]` 的前两个值吻合。

⇒ 这是"客户端把会话对象的**哪个** u32 放进 item+0x168"的问题，
   不是"低 32 位放前还是放后"的问题。按本轮纪律**不修改 senderId**，
   仅作事实记录并写入 NEXT_GATE。

### 8.2 更正：[0x0849B61C] 不是 accepted 的可靠标记

014/015/016 把 [0x0849B61C]=1 当作 accepted 状态之一。本轮实测证明它**不可用作判据**：

```
写入点（matching 模块内，mov byte [0x849B61C],1）：
  0x632827  ← accepted 分支（唯一"真"accepted 点）
  0x634BEC  ← matching 其它路径
  0x6398AD  ← matching 其它路径
  0x639A79  ← matching 其它路径
  0x63C9C1  ← matching 其它路径
另有 UI 侧 0x7CB1E4 / 0x7CB1FB / 0x7CB236 / 0x7CF7F9 / 0x7CFA89 / 0x7CFADD / 0x7CFAEC

动态反证：Run1 [18:03:41.527] / [18:04:07.767]、Run2 [18:12:48.338]
          **同一采样行**内 flag849B61C=1 而 this288_byte=0。
          若该 1 来自 0x632827，则 0x63280B 必已执行 ⇒ this288_byte 必为 1。
          实测为 0 ⇒ 该 1 来自非 accepted 路径。
```

⇒ 后续接力：**不要再用 [0x0849B61C]==1 推断 accepted**。

### 8.3 未受影响

```
LISTENER_PATH_CLOSED = YES（未重开）
SENDERID_PATH_CLOSED = YES（未重开；§8.1 是字段身份事实，不是端序重开）
TYPE2_TO_UDP         = REFUTED（§7 反向加强）
LOBBY_PATH_EXCLUDED  = YES
```

---

## 9. 要求的字段汇总

```
FACT_BASELINE              = §1（承接项 + 本轮新增判据 + 唯一标记扫描结论）
ACCEPTED_WIRE              = CONFIRMED（9 次实际发出；§3）
ACCEPTED_HANDLER_EXECUTED  = NO（accepted 分支；0x63280B 唯一标记从未置 1；
                               A/B 守卫使其构造上不可达；§4）
ACCEPTED_STATE_TRANSITION  = FAILED
THIS_288_BEFORE            = 0x0000（byte@+0x288 = 0）
THIS_288_AFTER             = 0x0000（byte@+0x288 = 0）
FLAG_849B61C_BEFORE        = 0
FLAG_849B61C_AFTER         = 1（但非 accepted 分支写入；§8.2）
UDP_SOCKET_ACTIVITY        = NOT_OBSERVED
CLIENT_UDP_28960_SEEN      = FAILED
BATTLE_RX_COUNT            = 0
RESULT_CASE                = C
```

### 9.1 RESULT_CASE 判定依据（对照任务 §13~§16）

```
CASE A: accepted = EXECUTED, accepted state = CONFIRMED, UDP = YES  -> 不成立
CASE B: accepted = EXECUTED, accepted state = CONFIRMED, UDP = 0    -> 不成立
        （accepted state 未发生：[this+0x288] 从未置 1）
CASE C: wire accepted = YES, accepted 分支 = NOT_EXECUTED           -> ★ 成立
CASE D: wire accepted = YES, 0x632680 = UNKNOWN, UDP = 0            -> 部分相关
        （函数是否被"进入"确为 UNKNOWN，但 accepted **分支**已被证否，
          且 A/B 守卫给出机制性证明，故取 C 而非 D）
```

### 9.2 Hard Stop 核对（任务 §19）

```
UDP RX #1 是否出现              = 否（battle 收包恒为 0）
accepted executed 但 UDP=0      = 不成立（accepted 根本没执行）
⇒ 不进入 PVE-BATTLE-DTLS；
⇒ 走 CASE C 分支：回到 service=21/type=2 -> dispatcher -> 0x632680 这条线，
   本轮已把它推进到"守卫层"，见 NEXT_GATE。
```

---

## 10. NEXT_GATE

**唯一待解问题变成：如何让 [matching+0x3A048] / [+0x3A04C] 与响应信封的 A/B 相等。**

按优先级：

```
1. 【字段身份，最高优先，纯静态可做】
   0x62F6F0 的 ecx = [edi+0x168]、edx = [edi+0x16C]。必须先确定：
     (a) edi 指向的"预留项"是哪个对象、由谁分配/填充；
     (b) 客户端从我们下发的 findSessions / session 对象里，**把哪两个 u32**
         写进 [item+0x168] / [item+0x16C]（实测值 1 / 0）；
     (c) 0x62CCCD / 0x62FBBB（置 byte[+0x278]=1）与这条链的先后关系。
   判据：实测 A=1/B=0 与 012 的 findSessions 解析首两值 [1, 0] 完全一致 ——
         优先验证"session 对象的第 1/2 个 u32 被当成 A/B"。
   ※ 这是字段身份问题，**不要**回到 013 的端序结论去改 senderId/SessionId。
     下一轮若需实验，必须单独开变量、可回滚，且需新的授权范围。

2. 【服务端会话对象整形，若 1 证实】
   让 session 对象经客户端解析后落到 [item+0x168]/[item+0x16C] 的值
   等于响应信封的 A/B（= senderId 的低/高 32 位）。在此之前，
   任何 mmbook accepted 推送都注定被 0x6326B9 拦下。

3. 【渠道核查（与本轮结论并列，尚未验证）】
   accepted 当前以 **marker=0x02 推送** 发送（build_push），
   而 0x7F1400 任务分派器位于 **marker=0x01（任务应答）** 通道
   （codol_crypto.py L20 / L737 / L924；0x7F1400 只出现在函数指针表 0xDE080C 里）。
   需静态确认 0x02 推送能否到达 0x7F1400；若不能，
   还应把 accepted 改成 6/14 的**应答对象**而不是独立推送。

4. 【不要做】
   不要再查 listener / senderId 端序 / type-2 lobby object / Lobby TCP；
   不要再把 [0x0849B61C]==1 当 accepted 判据；
   不要在 A/B 相等之前重跑动态（9 次已足够，结论稳定）。
```

---

## 11. 纪律核对

```
修改 client 指令 / patch 指令        = 无
新增 hook                            = 无
内存写入（对游戏进程）               = 无（_accprobe 只用 ReadProcessMemory）
伪造 UDP / 伪造 DTLS                 = 无
手工发包                             = 无
ACE / TenProtect bypass / 禁用 ACE   = 无
修改 senderId / SessionId            = 无
修改 service / type / sequence / message = 无
修改 endpoint / 28960                = 无
重新设计 Booking response            = 无
重新研究 listener / 已关闭路线        = 无
UAC                                  = 由人工批准（未绕过）
```

新增 / 改动文件：

```
新增  DEV-BOOKING\PVE-ACCEPTED-STATE-DYNAMIC-017.md
新增  DEV-BOOKING\scripts\_017_spot.py        （只读抽查；ACE 阻断后仅留作记录）
新增  DEV-BOOKING\scripts\_017_scan_c686.py   （静态：唯一标记扫描）
改动  DEV-PUBLISHER-RESTORE\REF_LOBBY_KIT\nt10.py  （+_accprobe 只读采样线程）
新增开关 DEV-PUBLISHER-RESTORE\REF_LOBBY_KIT\accepted-state-probe.on
证据  REF_LOBBY_KIT\accepted_state.txt / accepted_state_run1.txt
      REF_LOBBY_KIT\lobby_srv.log / lobby_srv_run1.log
      REF_LOBBY_KIT\battle_srv.log / battle_srv_run1.log
      REF_LOBBY_KIT\n10_017*.txt / n10_017b.txt
```

---

## 12. 复现命令（供接力）

```
# 1) 起提权代理（UAC 需人工批准）
$py=(Get-Command python).Source
Start-Process -FilePath $py -ArgumentList '-X','utf8',
  'D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\elevated_agent.py' -Verb RunAs -WindowStyle Hidden
python -X utf8 "CODOLServer\_mainline\agent_client.py" ping

# 2) 确认开关
#    accepted-state-probe.on            <- 本轮新增（只读采样）
#    firingrange-booking-push.enabled   <- 既有（推送 mmbook accepted）

# 3) 跑一局（游戏内需手动点一次 PvE 剧情任务触发 matchmaking）
python -X utf8 "CODOLServer\_mainline\agent_client.py" run python -X utf8 "DEV-PUBLISHER-RESTORE\REF_LOBBY_KIT\run_all.py" --secs 420 --out n10_017b.txt

# 4) 判定
#    看 accepted_state.txt 是否出现 this288_byte=1 或 ALERT
#    看 battle_srv.log 的 收包= 是否非 0
```

---

## 13. 最终问题的直接回答

> **客户端到底有没有真正执行 0x632680 的 mmbook accepted 分支？执行以后状态发生了什么？**

**没有执行。**

- 服务端确实把 "mmbook accepted" 发出了 9 次（marker=2 推送，seq=请求seq+1000），wire 侧无问题。
- 但 accepted 分支的唯一标记 byte[[0x082E13FC]+0x288]（写入点 0x63280B，全镜像唯一）
  在 **40ms 与约 6ms 两档采样、两轮、9 个事件窗口**里**从未置 1**，
  且该标记不会被紧随其后的 0x62F6C0 清除 —— 所以这不是"没抽到"，是"没发生"。
- 机制已定位：0x632680 的第一道守卫
  `0x6326B9 cmp A_frame, [matching+0x3A048]`
  拿 A_frame=0x55667788 比 [matching+0x3A048]=0x00000001（实测），
  **立刻 jne 0x632916 退出**；该出口不清 A/B、不写 [this+0x288]、不写 [0x0849B61C]。
  accepted 分支在构造上不可达。
- 因此**没有 accepted state transition**：[this+0x288] 保持 0；
  进不了 0x63281E 的 type-2 门控，也到不了 0x632827。
- 客户端每次**优雅关闭大厅连接并重连**，battle_srv 全程 **收包=0**，
  没有任何到 28960 的 UDP。BATTLE = NOT_REACHED，RESULT_CASE = C。

⇒ 下一步（唯一缺口）：查清客户端 [item+0x168] / [item+0x16C] 到底取自会话对象的哪两个 u32
（实测为 1 和 0），使 A/B 守卫能通过。详见 §10。




