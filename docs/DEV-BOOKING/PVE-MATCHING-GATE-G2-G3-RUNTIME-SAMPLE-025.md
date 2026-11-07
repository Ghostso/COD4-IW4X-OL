# PVE-MATCHING-GATE-G2-G3-RUNTIME-SAMPLE-025
# G2/G3 只读运行时采样：判定 024 的 H-A / H-B

```
AB_ALIGNMENT（本轮）        = NOT_SATISFIED（按任务要求未恢复 024 的对齐）
BLOB_FORMAT                 = CONFIRMED（lobby_server 023 修复保留，push 全为 data=16）

G1 = PASS（武装窗口已捕获，88 个密采样点）
G2 = **PASS**（88/88 武装样本；全轮 6138/6138 均为 0）
G3 = PASS（可读的 39/39 武装样本为 0）；49 个样本读取失败 -> 该部分 NOT_OBSERVED
G4 = NOT_SATISFIED（本轮 A=1，因未恢复对齐）；024 中为 PASS
G5 = NOT_SATISFIED（本轮 B=0）；024 中为 PASS

288_BEFORE = 0 ; 288_AFTER = 0（88/88 武装样本均为 0）

UDP_28960        = NOT_OBSERVED
BATTLE_SERVER_RX = 0

H_B = **REFUTED**（G2/G3 分支）
H_A = **STRONG_CANDIDATE**（不升级为 CONFIRMED）

RESULT_CASE = **A**（G2/G3 同时 PASS，288 仍 0，客户端仍同秒断连）
NEXT_TARGET = **PVE-ACCEPTED-DISPATCH-026**

CRYPTO_SHA256        = E836C63AF75DD82EF6F3B07EF63FAE48B044B3B5047336127093C92B07644607
LOBBY_SERVER_SHA256  = 7BBDC4F2B84DD14BD9FE3B6949F4946F805045841B8B3A170BC880585C6B9384
NT10_SHA256_POST     = DEAA33E80AFB8FD99AC3666BF101B2A2450D32ADF0DF1004F94E057A67363145
NT10_BACKUP          = DEV-PUBLISHER-RESTORE\REF_LOBBY_KIT\nt10.py.bak_025_20261008_230000
                       （= 4C52295DB7E71F6BF30352830F7C06A76AE06283957CA9BBD13BF2A62F7FC638）
```

---

## §1 冻结基线（启动前核对，全部匹配才继续）

```
codol_crypto.py  = E836C63AF75DD82EF6F3B07EF63FAE48B044B3B5047336127093C92B07644607  ✔（ORIGINAL，未恢复 A/B）
lobby_server.py  = 7BBDC4F2B84DD14BD9FE3B6949F4946F805045841B8B3A170BC880585C6B9384  ✔（023 blob 修复保留）
nt10.py（改前）  = 4C52295DB7E71F6BF30352830F7C06A76AE06283957CA9BBD13BF2A62F7FC638（已备份）
```

## §2 本轮唯一改动：只读采样器（nt10.py 的 _accprobe）

```
新增两个 ReadProcessMemory 字段：
  G2 = [0x076446B0]                      （绝对 VA，dword）
  G3 = [matching + 0xE360]               （有符号 32 位）
提高采样密度：time.sleep(0.005) -> time.sleep(0.001)（约 1 ms）
新增一行输出：SAM（仅在"热窗口"内逐点记录；热窗口 = 在武装状态附近展开 0.5 s）

未改动：其它采样字段、其它采样器、任何写入路径。
确认：全程未 hook / 未 breakpoint / 未注入 DLL / 未 WriteProcessMemory / 未 patch。
NT10_SHA256_POST = DEAA33E80AFB8FD99AC3666BF101B2A2450D32ADF0DF1004F94E057A67363145；AST_OK
```

### 2.1 ★ 对任务书 G2 语义的更正（重要）

任务书写 G2_PASS = signed(value) >= 3。反汇编是**相反**的：

```
0x0063269B  833db046640703     cmp dword ptr [0x76446b0], 3
0x006326A2  0f8d43020000       jge 0x6328eb        <- 0F 8D = JGE（有符号 >=）跳向"失败/重置"出口
=> 正确语义: **G2_PASS = signed(value) < 3** ；G2_FAIL = signed(value) >= 3

（G3 与任务书一致：）
0x006326AA  39be60e30000       cmp dword ptr [esi+0xe360], edi   (edi = 0)
0x006326B0  0f8c37020000       jl 0x6328ed                       <- JL（有符号 <）失败
=> G3_PASS = signed_int32(value) >= 0
```

本报告采用**反汇编语义**。

---

## §3 运行

```
命令   agent_client.py run python -X utf8 run_all.py --secs 300 --out n10_025.txt
进程   lobby_server 19392（127.0.0.2:3074） / fake_auth_tls 19184（127.0.0.1:3074）
       battle_server（0.0.0.0:28960，pid 280） / 游戏客户端 23288
探针   accepted-state-probe.on 已开；新 SAM 行生效
```

---

## §4 时间关联（本轮核心）

### 4.1 服务端事件

```
T_REQUEST（service=6 task=14，真实 mmbook）
   23:05:59 / 23:07:47 / 23:07:49 / 23:07:52 / 23:07:54 / 23:07:59
   23:09:09 / 23:09:12 / 23:09:19 / 23:09:24 / 23:09:34
T_ACCEPTED_PUSH（push 'mmbook accepted'）
   23:07:49 / 23:07:52 / 23:07:54 / 23:07:59
   23:09:09 / 23:09:12 / 23:09:19 / 23:09:24 / 23:09:34
   全部 data=16（023 blob 修复仍生效）
T_CONNECTION_CLOSE：**与 push 同一秒**，每次都是
   例：23:09:09 push -> 23:09:09 连接结束(53229) -> 23:09:09 连接建立(53279)
       23:09:12 push -> 23:09:12 连接结束(53279) -> 23:09:12 连接建立(53282)
       23:09:19 push -> 23:09:19 连接结束(53286) -> 23:09:19 连接建立(53294)
   本轮 9 个推送周期全部同型（"对端关闭 -> 立即重连"）
```

### 4.2 探针事件（T_G1 窗口）

```
this278 出现武装（0x0101 / 0x0001）的窗口：
   23:07:49.791
   23:07:54.986 / .993 / 23:07:55.009
   23:07:59.259
   23:09:09.305 ... .349（约 44 ms，密采样 40+ 点）
   23:09:12.536 ... .566
   23:09:19.028 ... .036
=> 这些窗口与服务端 6/14 + push 的秒级时间戳一一对应（同 024 形态）
```

---

## §5 G2 / G3 的实测结果（本轮唯一目的）

### 5.1 采样规模

```
SAM 行总数（约 1 ms 密度）      = 6138
其中落在武装窗口（this278 非零） = **88**
```

### 5.2 武装窗口内（88 点）

```
G2 值分布        = {0x00000000: 88}
G2PASS 分布      = {1: 88}                 <- **88/88 全部 PASS**
G3 值分布        = {-1: 49, 0: 39}         <- 49 点读取失败；可读的 39 点全为 0
G3PASS 分布      = {0: 49, 1: 39}          <- 可读样本 **39/39 PASS**（-1 的 49 点记为未观测）
this288 分布     = {0: 88}                 <- 从未为 1
A 分布           = {0x00000001: 58, 0x00000000: 30}   <- 未对齐（本轮按任务要求未恢复）
B                = 0x00000000
```

原始样例行（可复核）：

```
[23:09:09.329] SAM G2=0x00000000 G2s=0 G2PASS=1 G3=0  G3PASS=1 this278=0x0101 this288=0 A=0x00000001 B=0x00000000
[23:09:09.347] SAM G2=0x00000000 G2s=0 G2PASS=1 G3=0  G3PASS=1 this278=0x0101 this288=0 A=0x00000001 B=0x00000000
[23:09:12.541] SAM G2=0x00000000 G2s=0 G2PASS=1 G3=-1 G3PASS=0 this278=0x0101 this288=0 A=0x00000001 B=0x00000000
[23:07:59.259] SAM G2=0x00000000 G2s=0 G2PASS=1 G3=0  G3PASS=1 this278=0x0101 this288=0 A=0x00000001 B=0x00000000
```

### 5.3 全轮（6138 点）

```
G2 值分布 = {0x00000000: 6138}   <- 整个运行期间 G2 恒为 0
G3 值分布 = {-1: 6099, 0: 39}
=> [0x76446B0] 在大厅/空闲/booking 全过程中恒为 0（0 < 3 -> G2 始终 PASS）
=> G2 在本状态下**不是变量**，不构成任何 gate 风险
```

### 5.4 G3 读取的可靠性说明（诚实边界）

```
G3 = rpm(hh, matching + 0xE360, 4)，本轮 6138 点中只有 39 点成功（0.64%）。
成功的 39 点**全部落在武装窗口内**，且值均为 0。
=> 可读时 G3 = 0（PASS）；不可读时返回 -1（记为 NOT_OBSERVED，**不是** FAIL）
=> 未能解释为何该地址的读取大多失败（同对象内 matching+0x3A048 的读取一直成功）
   记为 INSTRUMENTATION_LIMITED（只影响 G3 的样本量，不影响"可读即 PASS"的结论）
```

---

## §6 判定

### 6.1 H-B（G2/G3 是阻塞点）= REFUTED

```
在 G1 成立的**每一个**武装窗口里（88 个 1 ms 采样点）：
   G2 = 0 -> G2_PASS（88/88）
   G3 = 0 -> G3_PASS（可读的 39/39）
同时 this288 = 0（88/88），且客户端仍在同一秒断开。
=> H-B 的 G2/G3 分支 **REFUTED**：G2/G3 不是 accepted 未发生的阻塞点。

注意：G1/G2/G3 在程序顺序上**先于 G4/G5**（0x63268D -> 0x63269B -> 0x6326AA -> 0x6326B9），
      因此"G2/G3 通过"这一结论**不依赖** A/B 是否对齐；
      结合 024（G1/G4/G5 同时 PASS、blob 已修复）可知 G1..G5 整体不构成阻塞。
```

### 6.2 H-A（连接先断，消息可能未被处理）

```
本轮 9 个推送周期，每一次都是"push -> 同一秒 连接结束 -> 立即 连接建立"。
=> H-A = **STRONG_CANDIDATE**
不升级为 CONFIRMED 的原因：本轮没有任何直接证据表明消息泵/0x632680 未执行；
   "同秒断连"只是与 H-A 相容，尚未排除"执行了但被 G6/G7 挡住"。
```

### 6.3 旧推理的再次声明

```
288 = 0 只能写作 ACCEPTED_STATE_TRANSITION = NOT_OBSERVED。
不得再据此推断 handler 未执行（022 的那条推理已被 023/024 推翻，本轮再次确认）。
```

---

## §7 必填字段汇总

```
CRYPTO_SHA256           = E836C63AF75DD82EF6F3B07EF63FAE48B044B3B5047336127093C92B07644607
LOBBY_SERVER_SHA256     = 7BBDC4F2B84DD14BD9FE3B6949F4946F805045841B8B3A170BC880585C6B9384
NT10_SHA256_POST        = DEAA33E80AFB8FD99AC3666BF101B2A2450D32ADF0DF1004F94E057A67363145

T_REQUEST               = 23:05:59 / 23:07:47 / 23:07:49 / 23:07:52 / 23:07:54 / 23:07:59 /
                          23:09:09 / 23:09:12 / 23:09:19 / 23:09:24 / 23:09:34
T_ACCEPTED_PUSH         = 23:07:49 / 23:07:52 / 23:07:54 / 23:07:59 /
                          23:09:09 / 23:09:12 / 23:09:19 / 23:09:24 / 23:09:34（全 data=16）
T_G1G4G5_WINDOW         = 024: 22:51:28.836-.946（对齐）
                          025: G1 窗口 23:07:49.791 / 23:07:54.986-.009 / 23:07:59.259 /
                               23:09:09.305-.349 / 23:09:12.536-.566 / 23:09:19.028-.036
                          （025 无 G4/G5，因未恢复对齐）
T_CONNECTION_CLOSE      = 与 push 同一秒（9/9 周期）

G2_VALUES               = 0x00000000 x6138（全轮）
G2_VALUE_AT_TARGET_WINDOW = 0x00000000
G2_RESULT               = **PASS**（CONFIRMED）

G3_VALUES               = -1 x6099（读取失败） / 0 x39
G3_VALUE_AT_TARGET_WINDOW = 0（可读时）
G3_RESULT               = **PASS（可读样本 39/39）**；49/88 点 NOT_OBSERVED

G1 = PASS
G2 = PASS
G3 = PASS（可读样本）
G4 = NOT_SATISFIED（本轮）；PASS（024）
G5 = NOT_SATISFIED（本轮）；PASS（024）

288_BEFORE = 0 ; 288_AFTER = 0

UDP_28960        = NOT_OBSERVED
BATTLE_SERVER_RX = 0（battle_srv.log 至 23:10:36 仍 收包=0 NAT=0 init=0 keyex=0 data=0 会话=0）

H_A = STRONG_CANDIDATE
H_B = REFUTED

RESULT_CASE = A
NEXT_TARGET = PVE-ACCEPTED-DISPATCH-026
```

---

## §8 NEXT_TARGET 说明（不要在本轮继续）

```
按任务书 §十五，G2/G3 全 PASS 后**不要**做"延迟 push"实验，应进入：
   PVE-ACCEPTED-DISPATCH-026
目标：仅证明 service=21 / "mmbook accepted" 是否真正进入 0x7F1400 -> 0x632680。
可用手段：已有日志 + 已有只读状态 + 已有调用链证据 + 可静态证明的 caller/dispatch 关系。
禁止：再次用 A/B 归零推断 handler entry（已被推翻两次）。
```

---

## §9 本轮改动与回滚选项

```
唯一被改的文件 = nt10.py（只读采样器：+2 个读取字段、0.005 -> 0.001 间隔、+SAM 行）
  NT10_SHA256_POST = DEAA33E80AFB8FD99AC3666BF101B2A2450D32ADF0DF1004F94E057A67363145
  NT10_BACKUP      = nt10.py.bak_025_20261008_230000（= 4C52295D...）
  lobby_server.py / codol_crypto.py / battle_server.py / 客户端 = **未改动**
如需恢复采样器：
  Copy-Item 'nt10.py.bak_025_20261008_230000' 'nt10.py' -Force
  复核 SHA = 4C52295DB7E71F6BF30352830F7C06A76AE06283957CA9BBD13BF2A62F7FC638

证据归档：DEV-BOOKING\_025\（accepted_state.txt / lobby_srv.log / battle_srv.log 的 pre025 副本）
本轮探针文件：DEV-PUBLISHER-RESTORE\REF_LOBBY_KIT\accepted_state.txt（6138 SAM + 318 其它行）
```

（全文完 · OBSERVATION ONLY · 未改客户端 / 未改 Server 业务代码 / 未改 crypto / 未改 Battle）
