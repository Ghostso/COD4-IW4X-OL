# OLMOD-CODOL-BOOKING-BATTLE-BRIDGE-030
# ol-mod 参照 + 当前客户端静态交叉审计：mmbook -> accepted -> mmstart -> Battle

```
OLMOD_REFERENCE_VALUE        = **HIGH**
BOOKING_TO_BATTLE_BRIDGE     = **STRONG_CANDIDATE**（ol-mod 侧为完整实现；本客户端侧确认了 mmstart 构造器与 288 消费者）
MMSTART_CURRENT_CLIENT       = **CONFIRMED**（格式串与构造器都在当前 EXE 内）
SESSIONSTART_CURRENT_CLIENT  = **NOT_OBSERVED**（当前客户端没有 SessionStart 这一层命名；见 §11）
BATTLE_ENDPOINT_BRIDGE       = **CANDIDATE**

RUNTIME_632680               = UNKNOWN
BATTLE_28960                 = NOT_OBSERVED

★ 本轮最重要的发现（与既有结论冲突，必须显式记录）：
   **ACCEPTED_BLOB_FORM_PRE023 = 正确**；**023 的"去掉 4 字节前缀"很可能是 REGRESSION**
   依据：ol-mod 的单元测试断言的是"存档 wire 的精确字节"，
        且该字节为 13 08 13 00 00 00 | 0f 00 00 00 | "mmbook accepted"（带前缀）。

NEXT_TARGET = 用带前缀的 accepted blob（15 字节文本、无 NUL 更贴近存档）+ A/B 对齐
              重跑一次对照实验（= 031 的单变量回归验证）
```

---

## §1 ol-mod 检出信息

```
路径   = F:\桌面\ol\ol-mod-olfinal
branch = OLfinal-live
HEAD   = 3915fa9813be7255d7031c307d31ad12043dfbd4
         "Restore Factory teleporter links and staged return travel"  (Fri Oct 2 09:41:50 2026 -0500)
规模   = 627 files；src/{backend, client_bridge, game_server, localnetworking, platformwrapper, shared}
绑定   = 其文档绑定另一份客户端（044c396c...）；本机客户端为 **36997674...**
=> 一切 ol-mod 的 RVA / offset / class layout / vtable 地址 = **REFERENCE_ONLY**
   只有"当前客户端里独立找到"的才升级。
```

## §2 当前客户端基线（已核验）

```
COD OL\codoMP_client_shipRetail.exe
  SHA-256 = 36997674B18F2896DE5E9D755686F6922AF10708F355175714058D0A0172B537
  大小    = 7,841,344 B
镜像   CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin（10,899,456 B）
  两者在下列字符串上完全一致（命中数相同）
```

## §3 当前客户端确实存在 mmstart 构造器（CONFIRMED）

```
字符串（VA）                                引用点                  说明
"mmstart sv_resetServer; 2486 %d; ..."      0x00632462             匹配模块内的命令构造器
  0xDC6800
"start_map_rotate_once"   0xDC6930          0x006325A6             同一构造器的分支
"2634 1; start_map_rotate" 0xDC6914         0x0063259F             同一构造器的另一分支
"MM_RESERVE_CMD_REQUEST Accepted" 0xDC6704  0x0062EC72             预约命令的"已接受"标记
"mmbook"                  0xDC6724          0x0062F7E1 / 0x007F1540 请求构造 / 0x7F1400 内的 strncmp
"mmbook accepted"         0xDC69B0          0x006326DB             <- 正是 0x632680 内 G6 前的 push
"mmbook timedout"         0xDC69D4          0x00632FB2             <- 超时/拒绝路径
```

0x632462 所在函数 = **0x632070**（fstart 结果），它内部是一个多分支构造器，
用匹配对象字段 [edi+0x105F8] / [edi+0x105FC] / [edi+0x105FE] / [edi+0x10604] / [edi+0x105D8]
填 %d，再 call 0x774980（sprintf 型）生成完整命令串。

=> **MMSTART_CURRENT_CLIENT = CONFIRMED**：当前客户端会构造
   "mmstart sv_resetServer; 2486 <n>; 3265 <n>; 2489 <n>; 2574 0; 2500 <n>; ...; ... g_difficulty..."
   这条命令，以及 "2634 1; start_map_rotate..." / "start_map_rotate_once" 两个变体。
```

## §4 ol-mod 侧的 service/task 映射（与我们完全吻合）

```
InstantMessageService::registerTasks：
  service **0x06** task **5**  = "Messaging::readQueuedMessages"
  service **0x06** task **14** = "Messaging::sendGlobalInstantMessage"     <- 我们的 6/14
  service **0x06** task **18** = "Messaging::sendInstantMessage"

task14 的解析（InstantMessageService.cpp:56-76）：
  readU64(recipient) ; readBlob(message) ; trailing 必须为空或以单个 0x00 结尾
    recipient != 0 且 != localUserId  -> publish(recipient, message, true, true)
    否则                              -> decodeLocalCommand(message) -> publish(localUserId, 回应, true, false)
=> 与我们在 019 抓到的 6/14 payload 形状完全一致：
   0a <u64 SessionId> 13 08 <len 0x1d> <u32 25> "mmbook 796 ..." 00
```

## §5 ★★ accepted 响应的精确字节（ol-mod 的存档回放断言）—— 与 023 冲突

```
tests\backend\DemonwareTests.cpp:1602-1606
  requireDw(... directPushes.front().second == fromHex(
      "08150000000adec0adde0100100110416c776179736f66666c696e6500"
      "1308130000000f0000006d6d626f6f6b206163636570746564"),
    "Messaging task 14 reproduces the **archived** local mmbook event-21 push **exactly**");

逐字节解析：
  08 15000000                       tag 0x08 + u32 21            (service 21)
  0a dec0adde01001001               tag 0x0A + u64 senderId
  10 416c776179736f66666c696e6500   tag 0x10 + "Alwaysoffline" NUL
  13 08 13000000                    tag 0x13 + tag 0x08 + u32 **19**   (blob 长度)
     0f000000                       u32 **15**                          <-- ★ 内层 raw u32 长度前缀
     6d6d626f6f6b206163636570746564 "mmbook accepted" (15 字节)
```

结论（必须显式写明）：
```
(1) ol-mod 的 accepted blob 内容 = **u32(15) + "mmbook accepted"**（共 19 字节），
    **即带 4 字节内层长度前缀** —— 这**正是 023 之前的形态**。
(2) 断言文字是"reproduces the **archived** ... **exactly**"，
    说明这不是 ol-mod 自创，而是**对齐了抓到的真实 wire**。
(3) 因此 **022 的 G6 结论（前缀会让 strncmp 第 0 字节失配）与 ol-mod 存档相矛盾**：
    既然真实 wire 带前缀，客户端必然在某处把内层 raw blob 解开（等价于 ol-mod 的 readBlob），
    而不是把 19 字节原样交给 strncmp。
(4) => **023 去掉前缀很可能是一次 REGRESSION**；024（对齐 + 无前缀）失败与之一致。
```

**差异提示（可作为 031 的单变量细节）**：我们的旧形态是
FR_BOOKING_ACCEPTED = b"mmbook accepted\x00"（16 字节，含 NUL）-> 前缀 16、blob 20；
存档是 15 字节文本（无 NUL）-> 前缀 15、blob 19。二者的**结构相同、长度不同**。
```

---

## §6 ★★ 第二跳：mmstart -> 游戏服（ol-mod 的 bookingSink_）

```
InstantMessageService::decodeLocalCommand（:120-147）：
  input.useDataTypes(false)                     <- 裸模式
  input.readBlob(commandBytes)                  <- 裸 u32 长度 + 数据
  if (bookingSink_ && command.starts_with("mmstart ")) bookingSink_(command);   <- ★ 走 booking
  token = 第一个空格前的单词；FNV-1a(token) 必须 == **0xDEC30B2A**，否则 return nullopt
  回应：response.useDataTypes(false); response.writeBlob("mmbook accepted")

**FNV-1a 实测**：
  "mmbook"  -> **0xDEC30B2A**    <-- 客户端发的就是 mmbook，正好命中该门
  "mmstart" -> 0x6382DCA5       （不命中）=> 该门是给 mmbook 请求用的

同一模式也存在于 src\backend\Demonware\Unknown0BService.cpp:147（service 0x0B）。
```

**测试给出的第二条命令**（DemonwareTests.cpp:1608-1626）：
```
  mmstart = "mmstart sv_resetServer; 2486 1; 3265 12; 2489 0; playlist 26; start_map_rotate_once 0"
  -> bookingCommand == mmstart && directPushes.size() == 1
  -> 断言 "Messaging task 14 routes the client's complete mmstart command to the **game server**"
```

=> ol-mod 的模型：client 的 mmbook -> accepted 回应；client 的 **mmstart 命令 -> 游戏服**。
   而当前客户端构造的 mmstart 串形如：
   "mmstart sv_resetServer; 2486 %d; 3265 %d; 2489 %d; 2574 0; 2500 %d; %s; %s g_difficulty..."
   （比 ol-mod 测试里的还多 2574 / 2500 / g_difficulty 等字段）
```

## §7 DedicatedBookingDispatcher（ol-mod 侧）

```
DedicatedBookingDispatcher.hpp：
  using EntitlementCheck   = bool(u64, span<u32>)
  using RosterProvider     = optional<FrozenRoomRoster>(u64)
  using MatchRulesProvider = optional<DedicatedSession::MatchRules>(BookingSelection)
  using ControlSubmit      = SubmitResult(u32 bridgeIpv4, u16 bridgePort, Message, u32 timeoutMs)
  bool submit(std::string command);
=> submit() 解析 mmstart 命令 -> resolveMatchRules(playlistText, selection) -> 名册冻结/权益检查
   -> 通过 ControlSubmit 把控制消息发给 **bridgeIpv4:bridgePort**。
   hpp 注释明确写道："The address leads because it is the half that used to be missing"
   （为了修一个问题，必须带上地址，而不只是端口）。
```

=> 与我们的实证对照：我们已知客户端有 endpoint 解析器 0x621E50
   （写 {+0x00=4, +0x04=ip, +0x08=port, +0x14=value}，要求 transport [global+0x1F0] 处于 state 1）。
   ol-mod 的 ControlSubmit(bridgeIpv4, bridgePort, ...) 与它语义高度相似，
   但**没有任何 RVA / offset 级别的对应证据** -> BATTLE_ENDPOINT_BRIDGE = CANDIDATE（见 §12）。
```

## §8 current-client：accepted 闩锁与 mmstart 之间缺什么

```
0x632680 的 G6 之后（0x63280B）写 [matching+0x288] = 1（accepted 闩锁）。
本轮把 **[matching+0x288] 的全部访问**逐一列出（匹配模块内）：
  [W] 0x62F47B  mov dword [edi+0x288], ebx         （函数 0x62F370：清零/复位）
  [W] **0x63280B  mov byte [esi+0x288], 1**        （函数 0x632680：accepted 闩锁）
  [R] **0x634402  cmp byte [ebx+0x288], 0**        （函数 0x634340：**唯一读者**）
  [W] 0x634B14  mov dword [ebx+0x288], 0x6FE80000  （函数 0x634870，常量写入）
```

唯一读者 0x634402 的上下文（这是一个与 G2/G3 同族的复合门）：
```
0x6343F9  cmp dword [ebp+0xc], ecx ; jne 0x6346CA
0x634402  cmp byte [ebx+0x288], 0            ; ★ 288
0x634409  mov byte [ebp-0x1E1], 0
0x634410  jne 0x63441B                       ; 288 != 0 -> 跳过下一道检查
0x634412  cmp dword [0x76446B0], 3           ; ★ G2
0x634419  jl  0x634434                       ; < 3 -> 结论保持 0
0x63441B  mov eax,[ebx+0xE360]               ; ★ G3（预约索引）
0x634421  cmp eax, ecx ; jl 0x634434
0x634425  cmp eax, dword [ebx+0x7230]        ; 且索引 < 数组上界
0x63442B  jge 0x634434
0x63442D  mov byte [ebp-0x1E1], 1            ; ★ 结论 = 1
```

=> **[matching+0x288] 参与的是一个"是否可以进入/启动该预约"的判定**，
   而且它与 0x632680 里的 G2/G3 门**是同一族条件**。
   这就是 288 的语义位置：**accepted 闩锁是后续阶段（预约/名册/启动）的前置条件之一**。
=> 注意：accepted 闩锁本身**不是** Battle trigger，也没有直接连到 28960；
   它是"下一阶段准入"的一部分。这与 §3 的 mmstart 构造器（位于匹配模块 0x632070）一致。
```

---

## §9 current-client：0x632680 / 288 / 28960 的关联度

```
0x632680（accepted handler，G6 = strncmp 于 0x6326DF，字面量 0xDC69B0）
  - 本轮再次确证：**"mmbook accepted" 的唯一代码引用点就是 0x6326DB**（G6 前一条 push）。
  - 同模块内另一个字符串 "mmbook timedout"（0xDC69D4）引用点在 0x632FB2 -> 超时/拒绝路径。
  - **没有任何证据**表明 0x632680 直接触发 Battle / 28960 / session start。
    => "0x632680 = Battle start" 这一假定 **REFUTED（静态）**。

[matching+0x288]
  - 写入：0x63280B（=1，accepted 闩锁）；0x62F47B（清零）；0x634B14（常量 0x6FE80000）
  - 唯一读者：**0x634402**（函数 0x634340），与 G2 [0x76446B0] 和 G3 [0xE360] 组成
    "是否准入该预约"的复合判定（见 §8）。
    => 288 的语义 = **后续阶段准入条件**，不是 Battle trigger，也不是 28960 的开关。

28960
  - 字符串 "28960" 在当前客户端镜像中 **0 命中**（端口来自地址/配置，不是字面量）。
  - 021 已确认：端点由 0x621E50 写入 {+0x00=4, +0x04=ip, +0x08=port, +0x14=value}，
    并以 transport [global+0x1F0] 处于 state 1 为前置条件。
  - ol-mod 侧对应的语义是 ControlSubmit(bridgeIpv4, bridgePort, ...)。
    => 两侧语义相近，但**无 RVA/offset 级对应证据** => BATTLE_ENDPOINT_BRIDGE = **CANDIDATE**。
```

## §10 Battle handshake 对照（REFERENCE_ONLY vs 我们的实证）

```
ol-mod（game_server 侧，32 处命中）：
  oob("getchallenge 0 \"01100001deadc0de\"")   （测试里明确使用 OOB 前缀 + getchallenge）
  oob_challenge_reply(OOB_PREFIX + b"getchallenge", <challenge>)
  回复字段：\natType\3\rank\68\challenge\<n>
当前客户端（字符串表证据）：
  "getchallenge 0 \"%s\"" ... natType ... 901 ... 2490 ... checksum ... challenge ... clantag ... xuid
  EXE_KEYWAIT / EXE_KEYCHANGE / EXE_SERVERISFULL / EXE_GAMEISENDING / EXE_MATCHENDED / EXE_DISCONNECTED
  server_hardware_win_dedicated / server_hardware_linux_dedicated
=> **两侧在 getchallenge + natType + challenge 上语义一致**（CANDIDATE 级）。
   客户端侧的 "901"/"2490" 等数字与 ol-mod 的 \natType\3 不是同一编码 -> 细节 **MISMATCH/UNKNOWN**。

与我们 021 的 28960 抓包：
  NAT(29B) -> init(16B) -> cookie(38B) -> 219B(cookie+pubkey) -> ack(114B) -> data 06 02 ...
**ol-mod 使用 OOB 文本命令（getchallenge ...）作为入口；我们抓到的是二进制首字节 13/12 的
握手。两者入口形态不同** -> 不能互换结论：**CODOL 自有证据优先**。
```

## §11 SessionStart 语义（ol-mod 有，客户端无此命名）

```
ol-mod：src\shared\DedicatedSession.hpp:108  struct SessionStart
        DedicatedSession.cpp:13  SessionStartPayloadKind = 2
        encode / decodeSessionStart / valid（含 magic、字符串、map、gametype、拒绝畸形/尾随字节）
        distribution\README.md:32 把流水线写作：
          ready -> client-native allocation -> **mmbook/mmstart** -> **SessionStart** -> world -> snapshot
客户端：SessionStart / sessionstart / Session Start / session_start = **0 命中**
=> SESSIONSTART_CURRENT_CLIENT = **NOT_OBSERVED**
=> 结论：SessionStart 是 **ol-mod（服务器/共享层）的实现概念**，不是原版客户端里的命名。
   客户端侧的对应物应当是 "EXE_KEYWAIT/EXE_KEYCHANGE" 与 "gamestateupdate"，
   但**没有建立命名级对应** -> 保持 UNKNOWN，不强行桥接。
```

## §12 roster / XUID / entitlement 的语义映射

```
ol-mod 命名                     客户端侧证据                                  等级
FrozenRoomRoster / RosterProvider  "roster"/"Roster" = 0 命中                    ol-mod:CONFIRMED / client:UNKNOWN
XUID（getchallenge 0 "<xuid>"）    "xuid" 仅 1 次，出现在 getchallenge 字符串内   CANDIDATE
entitlement_list / 权益检查        "entitlement"/"entitlement_list"/"granted_entitlement_list"
                                  ×9 命中（marketplace 侧）                      CANDIDATE
SessionId（userId）                session record #7 u64 -> A/B（018/019 已实证）  CONFIRMED（客户端侧）
map / gametype / playlist          "playlist" ×27；sv_playlist/handlers           STRONG_CANDIDATE

客户端 session record 语义（018/019 实证，仅做语义映射，**不假定 offset 相同**）：
  #1 Hostaddress(blob(bd_common_addr)) / #2 SessionId(u64) / #3 GameType / #4 MaxPlayers /
  #5 CurrentPlayers / roomId / host uid / map / criterion 0xD692ADAB / 16B securityKey ...
  record+0x168/+0x16C = SessionId 高/低 32 位（= A/B）；#7 u64 直接进 6/14 payload
=> 与 ol-mod 的 XUID/SessionId/roster 存在**语义邻接**，但没有一对一的字段证明。
```

## §13 交叉矩阵（必须项）

```
| 语义 | ol-mod | 当前 CODOL | 证据 |
|---|---|---|---|
| mmbook | task14 首词，FNV1a==0xDEC30B2A 才回包 | 字符串 0xDC6724；请求构造 0x62F7E1；0x7F1540 内 strncmp | **CONFIRMED** 双方 |
| booking accepted | 裸 blob = u32(15)+文本（存档字节断言） | "mmbook accepted" 0xDC69B0 -> 0x6326DF strncmp | **CONFIRMED** 双方 |
| mmstart | bookingSink_ -> DedicatedBookingDispatcher::submit | 格式串 0xDC6800 + 构造器函数 0x632070 | **CONFIRMED** 双方 |
| roster | FrozenRoomRoster / RosterProvider | "roster" 0 命中 | ol-mod CONFIRMED / client UNKNOWN |
| XUID | getchallenge 0 "<xuid>" | "xuid" 1 次（同串内） | CANDIDATE |
| entitlement | EntitlementCheck | entitlement_list ×9 | CANDIDATE |
| SessionId | session snapshot userId | record #7 u64 -> A/B | CONFIRMED（客户端侧） |
| SessionStart | struct + kind=2 + encode/decode | 0 命中 | ol-mod CONFIRMED / client **NOT_OBSERVED** |
| SessionStart v5 | README 流水线中的 SessionStart 阶段 | 0 命中 | client **NOT_OBSERVED** |
| dedicated endpoint | ControlSubmit(bridgeIpv4, bridgePort) | 0x621E50 endpoint writer（transport state==1） | CANDIDATE |
| 28960 | 游戏服端口（配置） | 0x621E50 写入端口；"28960" 0 命中 | CANDIDATE |
| CCS | dedicated CCS | 0 命中 | UNKNOWN |
| gamestate | 流水线阶段 | 仅 "gamestateupdate %d" | NOT_OBSERVED（协议层） |
| netchan | game_server netchan | 0 命中 | REFUTED（作为命名） |
| usercmd | game_server usercmd | 0 命中 | REFUTED（作为命名） |
| ACK | netchan ACK | 大厅层 0x85 ACK 已实证；Battle 层无 | 大厅 CONFIRMED / Battle UNKNOWN |
| battle handshake | OOB getchallenge + challenge reply（+DTLS/netchan） | getchallenge/natType/checksum/EXE_KEYCHANGE + 021 的 28960 二进制握手 | CANDIDATE（入口形态不一致） |
```

## §14 语义等价 / 不一致

```
等价（STRONG 以上）：
  service 0x06 task 14 = "sendGlobalInstantMessage"（ol-mod）  <-> 我们观察到的 6/14 请求
  payload 形状 readU64 + readBlob + 尾随 00（ol-mod）        <-> 019 抓到的 0a u64 / 13 08 len 00
  mmbook 首词 + FNV1a 0xDEC30B2A（ol-mod 门）               <-> FNV1a("mmbook")==0xDEC30B2A（实测）
  mmstart 命令（两处 naming 都用到 "mmstart sv_resetServer..." 家族的 cvar 串）
不一致：
  accepted blob：ol-mod 存档 = 带 u32 前缀；**我们 023 之后 = 不带前缀**（★ 见 §5）
  SessionStart / netchan / usercmd / CCS / roster / XUID：ol-mod 有命名，客户端 0 命中
  Battle 入口：ol-mod 用 OOB 文本 getchallenge；我们抓到的是二进制首字节 13/12 握手
  ol-mod 的 ClientSessionBridge(start(port), process(Capture)) 是 **ol-mod 自己的进程内桥**，
  不属于原版客户端的协议事实 -> 不得当作客户端行为。
```

## §15 未知项（UNKNOWN）
```
U-1 客户端究竟在哪里把 13 08 的内层 raw blob（u32 前缀）解开 —— 022 认为 0xB76AF0 原样拷贝，
    但 ol-mod 存档要求必须解开；两者冲突未解决（见 §5/§16）。
U-2 0x634340（288 的唯一读者）的返回值最终驱动什么（需要继续追它的调用者）。
U-3 mmstart 命令交给服务器之后的**服务端路由**是否真到 28960（客户端侧不可见）。
U-4 [matching+0x7230]（G3 的数组上界）语义。
U-5 客户端 "901"/"2490"/"3265"/"2486"/"2489" 这些数字 cvar 索引的确切含义。
```

## §16 ★ 最可能缺失的那一跳（必须项）

```
候选分类（任务书 §十六）：A..I

本轮证据：
  (e1) 客户端的 mmstart 构造器与格式串**确实存在**（0x632070 / 0xDC6800）-> §3
  (e2) 客户端的 accepted 闩锁 [matching+0x288] 有唯一消费者 0x634402 -> §8
  (e3) 所有历史运行（019/023/024/025/029）中 this288 **从未为 1** -> 闩锁从未完成
  (e4) BATTLE_28960 全部 NOT_OBSERVED；客户端从未出现 Battle 首包 -> 第二跳从未发生
  (e5) ol-mod 的 accepted 存档字节**带 u32 前缀**；我们 023 之后**不带** -> §5
  (e6) 019（对齐 + 带前缀）与 024（对齐 + 不带前缀）**都**得到 288=0
=> 结论：最可能缺失的是 **A（accepted 闩锁未完成）**，并因此 **mmstart 从未被构造/发送**
   （B/C/D 等下游阶段全部未触发）。
   等级 = **STRONG_CANDIDATE**（e1/e2/e3 直接支持 A；e4 自洽）。
   而 **A 的首位候选原因 = accepted blob 形态**（e5），
   但 e6 说明"只改形态"未必足够 -> 需要用 031 的单变量回归实验来判定。
   在 031 完成前，不得把 blob 形态升级为 CONFIRMED。
```

## §17 最终分类与下一步

```
OLMOD_REFERENCE_VALUE        = **HIGH**
BOOKING_TO_BATTLE_BRIDGE     = **STRONG_CANDIDATE**
MMSTART_CURRENT_CLIENT       = **CONFIRMED**
SESSIONSTART_CURRENT_CLIENT  = **NOT_OBSERVED**（ol-mod 独有的实现命名）
BATTLE_ENDPOINT_BRIDGE       = **CANDIDATE**
RUNTIME_632680               = **UNKNOWN**
BATTLE_28960                 = **NOT_OBSERVED**

MOST_LIKELY_MISSING_TRANSITION = A（accepted 闩锁未完成 -> mmstart 从未发送），STRONG_CANDIDATE

NEXT_TARGET = **031：单变量回归实验**
   1) 把 accepted blob 恢复成 ol-mod 存档形态（**精确字节**）：
        13 08 13 00 00 00 | 0f 00 00 00 | 6d6d626f6f6b206163636570746564
      即 FR_BOOKING_ACCEPTED = b"mmbook accepted"（**15 字节，无 NUL**），
      并在其外层写 u32(15) —— 也就是 **回滚 023**。
   2) 同时恢复 019 的 A/B 对齐（codol_crypto L542 = SessionId），使 G4/G5 可通过。
   3) 只此两个变量；观察 this288 是否 0 -> 1、以及客户端是否随后发出 **mmstart**。
   判据：若 288 -> 1 且 lobby 日志出现 mmstart 命令 -> ol-mod 存档形态成立、023 被证伪；
        若仍为 0 -> blob 形态不是唯一原因，回到 §16 的 A 之下继续分叉。
```

## §18 检查过的文件与修改

```
ol-mod 检查（只读）：
  src\backend\Demonware\InstantMessageService.cpp / .hpp
  src\backend\DedicatedBookingDispatcher.cpp / .hpp
  src\backend\Demonware\ByteBuffer.cpp / .hpp
  src\backend\DedicatedBookingDispatcher.hpp
  src\shared\DedicatedSession.hpp / .cpp
  src\client_bridge\ClientSessionBridge.hpp
  src\game_server\DedicatedSessionConsumption.hpp / Appmain.cpp / EngineBindings.*
  tests\backend\DemonwareTests.cpp（存档字节断言） / ServerTests.cpp
  tests\game_server\ServerCoreTests.cpp（OOB getchallenge 断言）
  tests\shared\DedicatedSessionTests.cpp
  distribution\README.md
当前客户端检查（只读）：
  codoMP_client_shipRetail.exe（SHA 见 §2）与 image_best.bin 的字符串 + imm32 xref 扫描
MODIFIED_FILES = **NONE**（新增只读分析脚本：DEV-BOOKING\scripts\_030_strs.py / _030_strs2.py /
                 _030_xref.py / _030_xref2.py）
未修改：客户端 / lobby_server.py / codol_crypto.py / battle_server.py / nt10.py / ol-mod 仓库
未执行：hook / 断点 / 注入 / patch / 计时实验 / 发包重放 / Battle Server 变更
```

（全文完 · 纯只读交叉审计 · 当前客户端证据优先 · ol-mod 仅作参照系）


