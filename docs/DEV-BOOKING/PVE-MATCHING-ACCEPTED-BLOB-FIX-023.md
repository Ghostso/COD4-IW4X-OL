# PVE-MATCHING-ACCEPTED-BLOB-FIX-023
# mmbook accepted blob 重复长度前缀修复 —— 最小单变量验证

```
ACCEPTED_BLOB_FIX          = **INCONCLUSIVE**（修复本身在 wire 上已证，但 G6 从未被触达）
ACCEPTED_STATE_TRANSITION  = **NOT_OBSERVED**
BATTLE_28960_TRIGGER       = **NOT_OBSERVED**

PRE_FIX_SERVER_SHA256      = 2E32E719AD548E93B66E306D2566E132D34512F69248FC7697815970AFF21DF1
POST_FIX_SERVER_SHA256     = 7BBDC4F2B84DD14BD9FE3B6949F4946F805045841B8B3A170BC880585C6B9384
BACKUP_PATH                = DEV-PUBLISHER-RESTORE\REF_LOBBY_KIT\lobby_server.py.bak_023_20261008_222940
                             （SHA-256 与 PRE_FIX 相同，已验证）

MODIFIED_LINES             = 850 与 908（两处均为同一表达式），见 §2
WIRE_CHECK_PASS            = **True**（离线自检，见 §3）

ROLLBACK_STATUS            = **NO**（blob 修复按授权保留；codol_crypto.py 未被本轮改动）
```

结论一句话：

> **blob 修复在 wire 上已确认生效（data 20 → 16，blob[0:15] == "mmbook accepted"），
> 但本轮实测在 G4 就失败了 —— 因为 019 的 A/B 对齐已被回滚，
> 客户端 matching A/B 回到 (1, 0)，而响应信封仍是 SessionId (0x55667788/0x11223344)。
> 所以 accepted 流程从未走到 G6，blob 假设没有被真正检验。**

---

## §1 实验设计（本轮执行的）

```
唯一变量（相对 022 的诊断）：lobby_server.py 中 mmbook accepted 的 blob 内容
                            去掉多余的 4 字节 u32 长度前缀
保持不变：SessionId / roomId / marker / service / task / senderId / 加密 / 帧格式 /
          序列号 / Publisher / 玩家数据 / Battle Server
未改动：Client EXE、Client DLL、codol_crypto.py（A/B 相关）
```

### 1.1 前置冻结（修改前）

```
PRE_FIX_SERVER_SHA256 = 2E32E719AD548E93B66E306D2566E132D34512F69248FC7697815970AFF21DF1
                         （size 76428，mtime 2026-10-08 14:50:02）
BACKUP                = lobby_server.py.bak_023_20261008_222940
backup SHA-256        = 2E32E719AD548E93B66E306D2566E132D34512F69248FC7697815970AFF21DF1（一致）
工作树状态            = 非 git 仓库；以文件 SHA-256 + mtime 记录
Server 可启动          = 已确认（本轮 run_all 正常起 lobby/auth/battle 三进程）
```

---

## §2 修改内容（严格最小）

定位到 accepted 构造共 **2 处**（不是 3 处；第三处不存在）：

```
lobby_server.py:287   FR_BOOKING_ACCEPTED = b"mmbook accepted" + NUL      （定义，未动）
lobby_server.py:850   accepted = struct.pack("<I", len(FR_BOOKING_ACCEPTED)) + FR_BOOKING_ACCEPTED
lobby_server.py:908   accepted = struct.pack("<I", len(FR_BOOKING_ACCEPTED)) + FR_BOOKING_ACCEPTED
lobby_server.py:911   % len(FR_BOOKING_ACCEPTED)                          （只用于日志，未动）
```

两处**逐字节相同**，一并改为：

```
lobby_server.py:850   accepted = FR_BOOKING_ACCEPTED
lobby_server.py:908   accepted = FR_BOOKING_ACCEPTED
```

验证：
```
POST_FIX_SERVER_SHA256 = 7BBDC4F2B84DD14BD9FE3B6949F4946F805045841B8B3A170BC880585C6B9384
size                   = 76428 -> 76336（-92 字节 = 2 x 46 字节，正好两行）
残留旧表达式           = NONE
python AST 语法检查    = AST_OK
```

**SECOND_SITE_STATUS = ALSO_FIXED**（第 908 处同样是重复长度编码，已同步修改）

---

## §3 离线 wire 自检（未启动游戏之前）

工具：DEV-BOOKING\scripts\_023_wirecheck.py（只读，直接用 kit 的 codol_crypto）

```
=== BEFORE（修复前形态）===
len=51
08 15 00 00 00 | 0a 88 77 66 55 44 33 22 11 | 10 "localhost" 00 | 13 08 14 00 00 00 | 10 00 00 00 6d 6d ... 00
                                                        blob length = 20
                                                        blob[0:15]  = 10 00 00 00 6d 6d 62 6f 6f 6b 20 61 63 63
                                                        == "mmbook accepted"? **False**

=== AFTER（修复后形态）===
len=47
08 15 00 00 00 | 0a 88 77 66 55 44 33 22 11 | 10 "localhost" 00 | 13 08 10 00 00 00 | 6d 6d 62 6f 6f 6b 20 61 63 63 65 70 74 65 64 00
                                                        blob length = 16
                                                        blob[0:15]  = b"mmbook accepted"
                                                        == "mmbook accepted"? **True**

WIRE_CHECK_PASS = True
（且 body 中不再出现 13 08 14 00 00 00 这一 20 长度 blob 头）
```

WIRE_BEFORE = 13 08 14 00 00 00 | 10 00 00 00 | 6d 6d ...（blob len 20，首字节 0x10）
WIRE_AFTER  = 13 08 10 00 00 00 | 6d 6d ...（blob len 16，首字节 0x6D）

---

## §4 真实运行

```
时间      2026-10-08 22:32:20 起，--secs 300（约至 22:37:20）
命令      agent_client.py run python -X utf8
          DEV-PUBLISHER-RESTORE\REF_LOBBY_KIT\run_all.py --secs 300 --out n10_023.txt
提权      ok=true, pid=21428, debug_privilege=true
进程      lobby_server  22644（127.0.0.2:3074, session=True booking=True battle=True）
          fake_auth_tls 14408（127.0.0.1:3074）
          battle_server 18400（0.0.0.0:28960）
          游戏客户端    20132 codoMP_client_shipRetail（Responding=True）
探针      accepted-state-probe.on 已开，accepted_state.txt 共 202 行 / 33025 B
前置清理  run_all 自动结束了上一轮残留（旧 14116/17312/2404 已消失）
```

### 4.1 ACCEPTED_WIRE：**修复确实上线了**

```
[22:33:45]  -> 6/14 命中 'mmbook' -> push 'mmbook accepted'(data=16)
[22:35:16]  -> 6/14 命中 'mmbook' -> push 'mmbook accepted'(data=16)
[22:35:19]  -> 6/14 命中 'mmbook' -> push 'mmbook accepted'(data=16)
[22:35:24]  -> 6/14 命中 'mmbook' -> push 'mmbook accepted'(data=16)
（对比 019：同一行是 data=20）
```

服务端仍在发：service=21、marker=0x02、文本 mmbook accepted —— 符合要求。

---

## §5 ★ 核心结果：本轮停在 G4，没到 G6

### 5.1 观测到的 A/B 是 **017 时代的 (1, 0)**，不是 019 的 (0x55667788, 0x11223344)

accepted_state.txt 分布（202 行）：

```
this288_byte : 0 x188, -1 x14            -> **从未出现 1**
A            : 0x00000001 x22, 0x00000000 x12
B            : 0x00000000 x34
this278      : 0x0000 x27, 0x0101 x7
flag849B61C  : 1 x28, 0 x7
t_5E8        : 3 x12, 0 x10, 1 x7, 2 x3
```

A/B 变化时间线：
```
22:33:45.322  A=0x00000001 B=0x00000000  this278=0x0000  flag=1
22:33:50.290  A=0x00000000 B=0x00000000  this278=0x0000  t_5E8=3
22:35:16.148  A=0x00000000 B=0x00000000  this278=0x0101  t_5E8=3   <- armed
22:35:16.166  A=0x00000001 B=0x00000000  this278=0x0101  t_5E8=3   <- A=1 且 armed
22:35:16.183  A=0x00000001 B=0x00000000  this278=0x0000  t_5E8=0
22:35:19.107  A=0x00000001 B=0x00000000  this278=0x0101  t_5E8=0
22:35:24.900  A=0x00000001 B=0x00000000  this278=0x0101  t_5E8=0
22:35:29.921  A=0x00000000 B=0x00000000  this278=0x0000  t_5E8=3
```

**本轮结论不依赖 022 的"出口鉴别法"**，而依赖一个更简单、无需推断的事实：

```
A 的取值集合 = {0x00000000, 0x00000001}，**从未出现 0x55667788**
响应信封的 A  = 0x55667788
=> G4: cmp A(0x55667788) vs [matching+0x3A048](1) 必然不相等
=> accepted 分支在算术上不可能被走到（与 this288 恒 0 一致）
```

（补充观察：本轮 A 也会在 0 与 1 之间摆动——每次 6/14 周期内为 1、周期外为 0，
与 019 的 0 ↔ 0x55667788 同型。因此"是否发生重置"在本轮**无法**用来区分出口，
022 的鉴别法需要"已对齐"基线才可用。）

### 5.2 根因：019 的 A/B 对齐已被回滚

```
codol_crypto.py SHA-256 = E836C63AF75DD82EF6F3B07EF63FAE48B044B3B5047336127093C92B07644607
                        = **019 之前的原始值**（019 实验用的 30AB0C59... 已不在）
=> 21/5 会话对象 #7 u64 重新变成 1

客户端 6/14 请求实测（本轮）：
  [22:35:16] payload(45): 0a 01 00 00 00 00 00 00 00 13 08 1d ...
                            ^^^^^^^^^^^^^^^^^^^^^^ 客户端回显 #7 = 1
（019 同位置是 0a 88 77 66 55 44 33 22 11）
```

而响应信封的 A/B 仍来自 instant_push_body(SESSION_ID, ...)（010 的修复，一直保留）
=> 响应 A/B = 0x55667788 / 0x11223344
=> 客户端期望 A/B = 1 / 0
=> **G4: cmp A(0x55667788) vs [matching+0x3A048](1) -> 不相等 -> jne 0x632916**

这就是本轮 observed 的直接原因。

### 5.3 门表逐项结果

```
G1  0x63268D  byte[matching+0x278] != 0
    观测：22:35:16.148 / .166、22:35:19.107、22:35:24.900 均为 0x0101 -> **有 armed 窗口**
    结论：PASS（至少在部分采样点成立）

G2  0x63269B  dword[0x76446B0] < 3
    观测：本轮探针字段集不含 0x76446B0 -> **UNKNOWN**（未新增侵入式 instrumentation）

G3  0x6326AA  dword[matching+0xE360] >= 0
    观测：本轮探针字段集不含 0xE360 -> **UNKNOWN**

G4  0x6326B9  A == [matching+0x3A048]
    观测：A=1（客户端侧）/ 响应 A=0x55667788 -> **FAIL（本轮实际失败点）**

G5  0x6326C8  B == [matching+0x3A04C]
    观测：B=0；因 G4 已失败而短路 -> NOT REACHED

G6  0x6326DF  strncmp(msg, "mmbook accepted", 15) == 0
    观测：**NOT REACHED**（本轮的 blob 修复因此**未被检验**）
    离线自检：修复后 blob[0:15] == "mmbook accepted"（WIRE_CHECK_PASS = True）

G7  0x6326FB / 0x632707  预约元素 +0x168/+0x16C == A/B
    观测：NOT REACHED
```

### 5.4 022 出口鉴别法在本轮不适用（更正）

```
019：A 在 0x55667788 与 0 之间摆动   -> 失败在**会重置**的出口（G1/G2/G3/G6/G7）
023：A 在 0x00000001 与 0 之间摆动         -> 失败在**不重置**的出口（G4/G5）
=> 无法用"是否重置"区分本轮出口：022 的鉴别法只在 A/B 已对齐时才有区分力（见 §5.1）
```

---

## §6 必须填写的观测值

```
MATCHING_288_BEFORE  = 0（22:33:14 起全程为 0）
MATCHING_288_AFTER   = 0
TRANSITION           = 无（0 -> 1 未发生）

A_BEFORE             = 0x00000001（本轮基线；不是 019 的 0x55667788）
A_AFTER              = 0x00000001 -> 0x00000000 -> 0x00000001（波动，无"持久归零"）
B_BEFORE             = 0x00000000
B_AFTER              = 0x00000000

E360                 = 未采样（UNKNOWN）
278                  = 0x0000 / 0x0101 交替；6/14 发出时为 0x0101
76446B0              = 未采样（UNKNOWN）

UDP_28960            = NOT_OBSERVED
BATTLE_SERVER_RX     = 0（battle_srv.log 全程 收包=0 NAT=0 init=0 keyex=0 data=0 会话=0）
```

---

## §7 结果分类

```
不落在 CASE A/B/D 中的任何一条，属于 **CASE C 的特例（带混淆变量的未检验）**：

CASE A（根因确认，288 -> 1）        ：未发生
CASE B（G6 过、G7 失败）             ：未发生（G6 都没到）
CASE C（G6 仍失败）                  ：**不适用** —— G6 根本没被执行
CASE D（handler 不执行）             ：不适用 —— 已证明失败的更上游是 G4

严谨表述：
  (1) 修复后的 wire 形态 = CONFIRMED（离线自检 + 服务端 data=16 双证）
  (2) blob 假设是否解除 accepted 阻塞 = **INCONCLUSIVE（未检验）**
  (3) 本轮实际阻塞点 = G4（A/B 未对齐），与 023 的 blob 无关
```

---

## §8 为什么会出现这个混淆变量

```
022 的结论建立在 019 的"已对齐"前提上（A/B 都等于 SessionId 拆半）。
但 019 本身是一次单变量实验，且其**报告 §2.1 明确记录了实验后已回滚**：
  "服务端修改 ROLLED_BACK（我复核当前哈希 codol_crypto.py = E836C63A...）"
本轮开始前未重新施加该对齐，于是在测 blob 之前，G4 就先失败了。
=> 这不是 023 的判断错误，而是**前置状态与 022 假设不一致**导致的混淆。
```

---

## §9 补救实验（需要授权，因为要动第二个变量）

要真正检验 blob 假设，必须具备 019 的对齐前提。建议的**正确单变量对照**：

```
A 组（已有证据，来自 019）：A/B 对齐 + **坏 blob**（带 4 字节前缀）-> 288 = 0
B 组（待做）      ：A/B 对齐 + **好 blob**（023 修复后）      -> 288 = ?

唯一变量：blob 前缀（A/B 对齐在两组中相同）
最小改动（相对现状，仅一行）：
  codol_crypto.py  build_mission_session_object 内
  L542  ob.u64(1)  ->  ob.u64(0x1122334455667788)     # 7
回滚方式：备份 + SHA-256 复核（019 已示范；本轮未动该文件，当前 SHA 仍是 E836C63A...）
```

**本轮按纪律未执行该改动**（第一节禁止修改 A/B）。

若你授权，我会：
1. 备份 codol_crypto.py 并记录 SHA-256；
2. 只改那一行；
3. 重启一轮（300 s），你再点一次 PvE；
4. 观察 this288 是否 0 -> 1。
   若 0 -> 1：ACCEPTED_BLOB_FIX = CONFIRMED，立即冻结成功版本（两份只读备份 + SUCCESS-CANDIDATE）
   若仍为 0：ACCEPTED_BLOB_FIX = REFUTED，转查 G1/G2/G3/G7（本轮未采样的两个量）。

---

## §10 当前状态与回滚

```
BLOB_FIX_CURRENTLY_APPLIED = YES
  lobby_server.py SHA-256 = 7BBDC4F2B84DD14BD9FE3B6949F4946F805045841B8B3A170BC880585C6B9384
  （这是协议正确性的修复，且是 B 组实验的必要条件，故保留）

ROLLBACK_STATUS = NOT_PERFORMED
  codol_crypto.py = E836C63AF75DD82EF6F3B07EF63FAE48B044B3B5047336127093C92B07644607（未动）
  其它文件        = 未动

如需完整回滚 blob 修复：
  Copy-Item 'lobby_server.py.bak_023_20261008_222940' 'lobby_server.py' -Force
  然后用 Get-FileHash 复核应为 2E32E719AD548E93B66E306D2566E132D34512F69248FC7697815970AFF21DF1

证据文件（已归档，未覆盖）：
  accepted_state.txt                          （本轮，202 行 / 33025 B）
  accepted_state.txt.pre023_20261008_223105   （019 遗留，56473 B）
  lobby_srv.log                               （本轮）
  lobby_srv.log.pre023_20261008_223105        （019 遗留，131265 B）
  battle_srv.log / battle_srv.log.pre023_20261008_223105
  n10_019_test2.txt.pre023_20261008_223105
```

（全文完 · 仅修改 lobby_server.py 两行 · 未改 client / 未 hook / 未 patch / 未内存写入）
