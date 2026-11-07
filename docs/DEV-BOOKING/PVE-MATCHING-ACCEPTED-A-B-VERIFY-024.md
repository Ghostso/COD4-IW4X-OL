# PVE-MATCHING-ACCEPTED-A-B-VERIFY-024
# A/B 对齐 + blob 修复 的严格对照实验

```
AB_ALIGNMENT               = **CONFIRMED**
BLOB_FORMAT                = **CONFIRMED**

G1 = PASS
G2 = UNKNOWN（未采样）
G3 = UNKNOWN（未采样）
G4 = **PASS**
G5 = **PASS**
G6 = **NOT_REACHED / UNKNOWN**（无法证明被执行）
G7 = **NOT_REACHED / UNKNOWN**

ACCEPTED_BLOB_FIX          = **INCONCLUSIVE**
ACCEPTED_STATE_TRANSITION  = **NOT_OBSERVED**
UDP_28960                  = **NOT_OBSERVED**

RESULT_CASE                = **B 的未证实形态**（G4/G5 PASS、无 288 跃迁、G6 无法证明被触达）
                             —— 既不是 A，也不能判 B/C/D

PRE_CRYPTO_SHA256          = E836C63AF75DD82EF6F3B07EF63FAE48B044B3B5047336127093C92B07644607
POST_CRYPTO_SHA256         = E9759747E334BA956F768E0B5FAC42E17BC64DB0692D3935A67BD780E2D88F67
RESTORED_CRYPTO_SHA256     = E836C63AF75DD82EF6F3B07EF63FAE48B044B3B5047336127093C92B07644607（已回滚并复核）
LOBBY_SERVER_SHA256        = 7BBDC4F2B84DD14BD9FE3B6949F4946F805045841B8B3A170BC880585C6B9384（保留 023 修复）
CRYPTO_BACKUP              = DEV-PUBLISHER-RESTORE\REF_LOBBY_KIT\codol_crypto.py.bak_024_20261008_224858
```

---

## §1 修改前冻结

```
PRE_CRYPTO_SHA256 = E836C63AF75DD82EF6F3B07EF63FAE48B044B3B5047336127093C92B07644607
                    （与任务书要求一致；size 42853）
CRYPTO_BACKUP     = codol_crypto.py.bak_024_20261008_224858（SHA-256 与 PRE 相同）
TARGET            = build_mission_session_object / 第 542 行（注释 # 7）
混淆项已排除      = 同文件第 551 行 ob.u64(1) # 28 —— **未触碰**
LOBBY_SERVER_SHA256 = 7BBDC4F2B84DD14BD9FE3B6949F4946F805045841B8B3A170BC880585C6B9384（023 修复保留）
```

---

## §2 唯一改动（严格单变量）

```
-  ob.u64(1)                                       # 7
+  ob.u64(0x1122334455667788)                      # 7
```

只允许一行；diff 结果 = **1 行删除 + 1 行新增**（Compare-Object 报 2 条，即同一行的改动）：

```
differing lines = 2
=> ob.u64(0x1122334455667788)                      # 7
<= ob.u64(1)                                       # 7
```

POST_CRYPTO_SHA256 = E9759747E334BA956F768E0B5FAC42E17BC64DB0692D3935A67BD780E2D88F67
AST 语法检查 = AST_OK；lobby_server.py 未变（7BBDC4F2...）

---

## §3 运行环境

```
命令   agent_client.py run python -X utf8 run_all.py --secs 300 --out n10_024.txt
提权   ok=true（agent pid 21428, debug_privilege=true）
进程   lobby_server 22336（127.0.0.2:3074）
       fake_auth_tls 16360（127.0.0.1:3074）
       battle_server 14220（0.0.0.0:28960）
       游戏客户端 codoMP_client_shipRetail 24524（Responding=True）
探针   accepted-state-probe.on（沿用）
```

---

## §4 第一检查点：6/14 request —— **通过**

客户端实际发出的 booking payload（服务端解密日志原文）：

```
[22:51:28]  ★ 解密成功 #51 seq=51 hmac=OK marker=0x86 service=6 ver=0x03 task=14 declared=48
            payload(45): 0a 88 77 66 55 44 33 22 11 13 08 1d 00 00 00 19 00 00 00 6d 6d 62 6f 6f 6b 20 37 39
                         ^^^^^^^^^^^^^^^^^^^^^^ #7 = 0x1122334455667788（已恢复）
```

REQUEST_PAYLOAD = 0a 88 77 66 55 44 33 22 11 13 08 1d ...
REQUEST_AB      = A = 0x55667788 , B = 0x11223344
（对比 023：同一处是 0a 01 00 00 00 00 00 00 00 —— 已确认恢复）

**AB_ALIGNMENT = CONFIRMED**

---

## §5 第二检查点：accepted response —— **通过**

```
[22:51:28]  -> 6/14 命中 'mmbook' -> push 'mmbook accepted'(data=16)
[22:51:28]  -> 0x85 推送 type=2 seq=1051(请求seq+1000) (98 字节 body=47)
```

本轮共 6 次推送，**全部 data=16**（22:51:28 / 22:52:45 / 22:52:55 / 22:53:07 / 22:53:13 / 22:54:xx）。

BLOB_LENGTH          = 16
BLOB_FIRST_15_BYTES  = 6d 6d 62 6f 6f 6b 20 61 63 63 65 70 74 65 64
（离线自检同样为 WIRE_CHECK_PASS = True）
RESPONSE_AB          = A = 0x55667788 , B = 0x11223344

**BLOB_FORMAT = CONFIRMED**

---

## §6 第三检查点：G1 / G4 / G5 —— 全部 PASS

探针在 22:51:28 对齐窗口的原始行（change-triggered 采样）：

```
22:51:28.813  A=0x00000000 B=0x00000000  this278=0x0101  this288=0  flag=1  t_5E8=3
22:51:28.836  A=0x55667788 B=0x11223344  this278=0x0101  this288=0  flag=1  t_5E8=1   ★
22:51:28.946  A=0x55667788 B=0x11223344  this278=0x0000  this288=0  flag=1  t_5E8=2
22:51:33.858  A=0x00000000 B=0x00000000  this278=0x0000  this288=0  flag=1  t_5E8=3
```

=> 在 22:51:28.836–.946（约 110 ms）同时满足：
   G1: byte[matching+0x278] = 0x01（非 0）        -> **PASS**
   G4: A = 0x55667788 == [matching+0x3A048]      -> **PASS**
   G5: B = 0x11223344 == [matching+0x3A04C]      -> **PASS**

服务端同一秒发出了修复后的 push（data=16）。

**[matching+0x288] 仍为 0**（该快照 155 行中 this288_byte 全 0；本行分布：0 x141，-1 x14）。

---

## §7 第四/五检查点：G6 / G7 —— 无法证明被触达

```
G6 0x6326DF  strncmp(msg,"mmbook accepted",15)
   静态：修复后 blob[0:15] 正是 "mmbook accepted"，若执行应当 PASS
   动态：**没有任何直接证据表明它被执行**（没有可观测的持久副作用可判）
   => G6 = NOT_REACHED / UNKNOWN（不是 FAIL，也不是 PASS）

G7 0x6326FB / 0x632707  预约元素 +0x168/+0x16C == A/B
   => NOT_REACHED / UNKNOWN

G2 0x63269B  dword[0x76446B0] < 3        -> UNKNOWN（探针字段集不含）
G3 0x6326AA  dword[matching+0xE360] >= 0 -> UNKNOWN（探针字段集不含）
```

**为什么不能判 FAIL**：G6 失败会走 0x632876/0x632712 并触发 A/B 重置；
但 024 里 A/B 的重置发生在 22:51:33.858（对齐窗口之后约 5 秒），
与 023（未对齐、同样出现 A/B 归零）同型 —— 说明这种周期性归零**不能**作为
"0x632680 执行过"的判据。因此 G6 是否被触达，本轮**没有证据**。

---

## §8 ★ 本轮最重要的新观察：客户端在同一秒关闭连接

每一轮 booking 的服务端时间线（形态 6/6 次完全一致）：

```
[22:51:28]  ★ findSessions -> 21/5 应答（236B session 对象）
[22:51:28]  ★ 解密 #51 service=6 task=14   payload 以 0a 88 77 66 55 44 33 22 11 开头
[22:51:28]  -> 6/14 命中 'mmbook' -> push 'mmbook accepted'(data=16)
[22:51:28]  -> 0x85 应答 seq=51(replyId=51) service=6 task=14 (66 字节, 对象=0)
[22:51:28]  -> 0x85 推送 type=2 seq=1051 (98 字节 body=47)
[22:51:28]  对端关闭                                  <-- 客户端**同一秒**关闭
[22:51:28]  === 大厅连接结束 (解出任务 51 条) ===
[22:51:28]  === 大厅连接建立 (52057) ===                  <-- 立即重连
```

因此产生一条**新的、优先级更高的假设**：

```
H-A（连接先断，消息后到）：客户端在收到 6/14 的空 ACK + 推送后立即进入
     "关闭重连"流程；若消息泵在连接拆除之前没有跑到该推送，
     0x632680 就根本不会被执行 —— 这与 G6/G7 无关。
H-B（执行了但挡在更早的门）：G2（全局游戏状态 >= 3）或 G3 未通过，
     或 G6/G7 失败。其中 G2/G3 本轮完全未采样。
```

同时必须**下调 022 的一处结论**：
```
022 曾记 "ACCEPTED_HANDLER_ENTERED = CONFIRMED（由 A/B 持久归零反推）"。
023（未对齐基线）同样出现 0 <-> 1 的周期性归零，说明该反推**不成立**。
=> ACCEPTED_HANDLER_ENTERED = **UNKNOWN**（更正）
```

---

## §9 最终核心指标

```
MATCHING_288_BEFORE = 0
MATCHING_288_AFTER  = 0
TRANSITION          = 无（整轮 this288_byte=1 出现 **0** 次）

（多轮快照均核对：155 行快照 0 次；运行末尾 98 行快照 0 次；归档 024final 同）

UDP_28960           = NOT_OBSERVED
BATTLE_SERVER_RX    = 0（battle_srv.log 全程 收包=0 NAT=0 init=0 keyex=0 data=0 会话=0，至 22:55:12）
```

---

## §10 实验逻辑三角

```
019 : A/B 对齐 + BAD blob   -> G4/G5 PASS -> 288 = 0
023 : BAD A/B + GOOD blob   -> G4 FAIL    -> 288 = 0
024 : A/B 对齐 + GOOD blob  -> G1/G4/G5 PASS（已观测） -> 288 = 0   <-- 本轮
```

结论：把两个已知条件**同时**满足之后，288 仍不跃迁。
=> 既不能宣布 blob 假设 CONFIRMED，也不能按 CASE B 宣布 REFUTED，
   因为 **"G6 被执行过" 这个前提本身没有被证实**。
=> ACCEPTED_BLOB_FIX = INCONCLUSIVE；阻塞点已从 G4 前移到
   "G6 之前的可达性（H-A）或 G2/G3（H-B）"。

---

## §11 回滚状态（按 §18）

```
RESTORED_CRYPTO_SHA256 = E836C63AF75DD82EF6F3B07EF63FAE48B044B3B5047336127093C92B07644607
                         （由 .bak_024_20261008_224858 覆盖并复核，与 ORIGINAL 一致）
LOBBY_SERVER_SHA256    = 7BBDC4F2B84DD14BD9FE3B6949F4946F805045841B8B3A170BC880585C6B9384
                         （**保留** 023 blob 修复，未回滚）
最终状态               = codol_crypto.py = ORIGINAL ; lobby_server.py = 023 FIXED   ✔

说明：回滚发生在运行结束前，但运行中的 lobby_server 进程在启动时已加载打过补丁的模块，
      因此本轮后续 booking 周期仍使用对齐值（实测 22:52–22:54 的推送仍为 data=16 且
      payload 以 0a 88 77 66 55 44 33 22 11 开头，见 §4）。
```

---

## §12 证据文件

```
accepted_state.txt                          本轮（末尾快照 98 行）
accepted_state.txt.024final_<ts>            本轮归档（1344 B）
accepted_state.txt.pre024_20261008_2250xx   023 遗留（40403 B）
lobby_srv.log                               本轮（含 13 次 6/14、6 次 accepted 推送）
lobby_srv.log.pre024_20261008_2250xx        023 遗留
battle_srv.log / battle_srv.log.pre024_*    本轮 / 023
n10_024.txt                                 run_all 输出
codol_crypto.py.bak_024_20261008_224858     024 前冻结
lobby_server.py.bak_023_20261008_222940     023 前冻结
```

关键原始行（可复核）：
```
22:51:28.836  A=0x55667788 B=0x11223344  this278=0x0101  this288=0
22:51:28      payload(45): 0a 88 77 66 55 44 33 22 11 13 08 1d ...
22:51:28      -> 6/14 命中 'mmbook' -> push 'mmbook accepted'(data=16)
22:51:28      对端关闭
```

---

## §13 下一轮（建议，需授权）

```
优先级 1：判 H-A / H-B
  在**现有只读采样器**里增加两个字段（纯 ReadProcessMemory，非侵入、非 hook）：
    [0x76446B0]            -> G2
    [matching+0xE360]      -> G3
  并把采样密度提到 ~1 ms，覆盖 22:51:28.836-.946 那个 ~110 ms 窗口。
  若 G2/G3 在窗口内满足 -> 说明 G1/G4/G5/G2/G3 全过，阻塞更可能在 H-A（连接先断）。

优先级 2：判"推送到底有没有被消息泵处理"
  最小侵入手段：把 accepted 推送**延后若干毫秒**（或改成与 6/14 应答同帧发出），
  看客户端是否仍立刻断开 —— 但这是 Server 行为改动，需单独授权。

优先级 3：若确认 H-A，则问题变成"如何在客户端处理推送之前不让它断连"，
  属于 Lobby 时序问题，与 blob / A/B 均无关。

禁止：不要再改 blob、不要再改 A/B、不要动 Battle Server。
```

---

## §14 运行包装层与进程状态的补充事实（本轮收尾时发现）

### 14.1 job 退出码 1 的含义 —— 不是运行失败

```
agent_client.py 自己的客户端读超时：
  File "CODOLServer\_mainline\agent_client.py", line 24, in send
    chunk = s.recv(65536)
  TimeoutError: timed out
=> 包装客户端（非提权侧）在等待期间超时退出，退出码 1；
   **提权侧的实际运行并未终止**：收尾时三个服务端进程仍在监听
   （lobby 22336 / auth 16360 / battle 14220），游戏客户端也仍在运行。
=> 结论：本轮所有"300 秒窗口"命令都会以 exit 1 结束，这是包装层行为，
   与实验成败无关；判定必须依据服务端日志与探针文件，而不是 job 退出码。
```

### 14.2 游戏客户端被重启过（同一轮内）

```
启动时   codoMP_client_shipRetail pid = 24524
收尾时   codoMP_client_shipRetail pid = 16232（Responding=True）
=> run_all 的坏启动重试（--retries 默认 6）在本轮触发过至少一次；
   这不影响 §4–§9 的结论（那些观测都在重启之前/之后的有效周期内）。
```

### 14.3 探针文件会被截断（证据处理注意）

```
收尾时 accepted_state.txt = 0 B（新一轮连接周期开始，探针重开文件）。
=> 只读采样器的输出是**按周期覆盖**的，早期周期的数据会丢失。
   本轮 22:51:28 的对齐窗口数据，保存在 §6 的原始行与归档
   accepted_state.txt.024final_20261008_225415（1344 B）中。
   全部 10 份 accepted_state* 文件逐一核对：this288_byte=1 命中数 **均为 0**。
```

### 14.4 结论不变

```
ACCEPTED_STATE_TRANSITION = NOT_OBSERVED（019 / 023 / 024 三轮、共 10 份探针文件、0 次命中）
ACCEPTED_BLOB_FIX         = INCONCLUSIVE
UDP_28960                 = NOT_OBSERVED
BATTLE_SERVER_RX          = 0
```

### 14.5 一个仍未关闭的、成本很低的窗口

```
收尾时：三个服务端**仍在运行**（且其内存中仍是打过 A/B 对齐补丁的模块 —— Python 启动时导入，
        磁盘回滚不影响已加载实例），游戏客户端也仍在运行。
=> 若此时再点一次 PvE，无需任何修改即可再测一轮；只需把探针文件的读取频率提高到 ~2 秒
   就有机会抓到 288 的 0 -> 1 跃迁（只读，不新增 instrumentation）。
   这是本轮唯一"零改动即可继续"的选项。
```

（§14 完）

（全文完 · 本轮仅改 codol_crypto.py 一行且已回滚 · lobby_server.py 保留 023 修复 · 未改 client）
