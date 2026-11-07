# PVE-MATCHING-ACCEPTED-GATE-CLOSURE-022
# mmbook accepted 门 —— 从 0x632680 到 [matching+0x288]=1 的全部必要条件，以及 017/019 为什么没发生

```
RESULT                        = **GATE CLOSED（根因确定，单点）**
ACCEPTED_GATE_COUNT           = 7 道门（0x632680 内），此前只识别出 2 道
FAILING_GATE                  = **G6 = 0x6326DF strncmp(msg, "mmbook accepted", 15)**
ROOT_CAUSE                    = 服务端推送的 blob 里多了一个 4 字节 u32 长度前缀
                                （lobby_server.py:850），客户端把 blob **原样**读进缓冲
                                （0xB76AF0 不会剥掉内层 u32），于是 strncmp 在第 1 个字节就失败
EVIDENCE_DYNAMIC_MATCH        = 019 日志中 A/B 先对齐(0x55667788/0x11223344)后变 0x00000000，
                                且 [matching+0x288] 全程为 0 —— 与 G6 失败路径的副作用**逐条吻合**
SERVER_FIX_REQUIRED           = 1 行（把 blob 内容改成**裸文本**），**本轮未改**（禁止修改）
020_CONCLUSION                = 仍然成立：wire 分派链 CONFIRMED；失败点在 handler **内部**
```

纪律：未改 client / server / 配置 / 数据；未 patch / hook / 发包。
本轮为纯静态 + 只读证据复核。新增只读工具：DEV-BOOKING\scripts\_022_gate.py。

---

## §0 一句话结论

**wire 到了、分派到了、函数进了、A/B 也对了 —— 死在字符串比较上。**

服务端发的 blob 内容是 10 00 00 00 + "mmbook accepted" + NUL（u32(16) 前缀 + 16 字节文本），
而客户端做的是 strncmp(缓冲, "mmbook accepted", 15)，比较对象是**从第 0 字节开始**的原始字节：

```
缓冲前 15 字节: 10 00 00 00 6d 6d 62 6f 6f 6b 20 61 63 63
字面量        : 6d 6d 62 6f 6f 6b 20 61 63 63 65 70 74 65 64
=> 第 0 字节 0x10 不等于 0x6D  => 比较失败 (jne 0x632876)
```

---

## §1 0x632680 的完整门图（本轮硬结果）

入口签名（cdecl，5 个栈参数 + this）：
```
[ebp+0x08] = A            （u64 低 32 位，来自 21/5 会话对象 tag-0x0A u64）
[ebp+0x0C] = B            （u64 高 32 位）
[ebp+0x10] = str40        （0x40 字节缓冲区 = tag-0x10 字符串，实测 "localhost"）
[ebp+0x14] = msg          （0x1000 字节缓冲区 = tag-0x13 blob，**G6 的比较对象**）
[ebp+0x18] = len          （tag-0x13 blob 的长度）
ecx = matching 单例 [0x082E13FC]
```

| 门 | 地址 | 条件 | 失败跳转 | 失败是否重置 A/B |
|---|---|---|---|---|
| **G1** | 0x63268D | byte[matching+0x278] 非 0（booking armed） | 0x6328EB | **是** |
| **G2** | 0x63269B | dword[0x76446B0] < 3（全局游戏状态） | 0x6328EB | **是** |
| **G3** | 0x6326AA | dword[matching+0xE360] >= 0（预约索引） | 0x6328ED | **是** |
| **G4** | 0x6326B9 | A == dword[matching+0x3A048] | 0x632916 | 否 |
| **G5** | 0x6326C8 | B == dword[matching+0x3A04C] | 0x632916 | 否 |
| **G6** | 0x6326DF | strncmp(msg, "mmbook accepted", 15) == 0 | 0x632876 | **是**（经 0x632712 或 0x63288C） |
| **G7** | 0x6326FB / 0x632707 | 预约数组元素[idx].+0x168==A 且 +0x16C==B | 0x632712 | **是** |

全部通过后进入 **ACCEPTED PATH**（0x632736 起）：

```
0x632736  读 byte[esi+0x105FC]；构造局部结构 {type=1, name=0xdc74F8 " Ub", 0,0,0}
0x632761  call 0x771320
0x632770  call 0x631E90 -> call 0x632070
0x63277E  edx = [esi].vt+0x150 ; push 0,0,B,A,eax ; call edx     <- 入队
0x632791  call 0x631E50 ; test al
          al != 0 -> push 1 ; call 0x811340 ; push ... ; vt+0x14C ; call edx
0x6327C5  ecx = 元素[idx] 地址（matching+0x7470+idx*0x238）
          构造局部 {0xdc751C, 3, 元素指针} ; call 0x62ABF0
0x6327FA  edx = [esi].vt+0x148 ; push 局部 ; call edx
0x63280B  ★ mov byte [esi+0x288], 1                              <- ACCEPTED 标记
0x632812  call 0x62F6C0                                          <- 注意：成功后也会重置
0x632817  call [esi].vt+0x5C ; test al
          al == 0 -> 广播：edi=[esi+4] 链表，逐个 [listener.vt+0x24](0,1)
0x632827  mov byte [0x849B61C], 1
0x632846  call 0x6293B0 ; call 0x629F80
0x632864  call 0x655930 ; epilogue ; ret 0x14
```

**关键理解**：0x63280B 之前有 **一串副作用**（vt+0x150 入队、0x631E50、0x811340、vt+0x14C、0x62ABF0、vt+0x148）。
017/019 观察到 this288 恒 0 => **这一整串都没有发生**，不是"只差最后一步"。

---

## §2 两个失败出口的差别（本轮关键鉴别点）

```
出口甲  0x632916（= G4/G5 失败，直接跳）
        仅 pop/ret，**不动 A/B**
出口乙  0x6328EB / 0x6328ED（= G1/G2/G3 失败）
        0x6328F7  mov dword [esi+0x3A048], 0     <- A 归零
        0x6328FD  mov dword [esi+0x3A04C], 0     <- B 归零
        0x632903  call 0xC42DE0(memset(&[esi+0x3A050], 0, 0x40))
        0x63290B  call 0xB75D90(&[esi+0x3A090])  <- 清字符串对象
        然后落到 0x632916
出口丙  0x632712（= G7 失败，也来自 G6 失败的分支）
        0x632712  call 0x62F6C0                  <- 同一个"重置"函数
        然后 [0x82E140C].vt+0xC 与 0x6292B0，再 ret
出口丁  0x632876 ->（若 byte[esi+0x280]==0 且 dword[esi+0x10780]<=0xA）-> 0x632712
        否则 0x63288C：call 0x62F6C0；vt+0x5C；广播 [vt+0x24](0,2)；
        再 vt+0x148 传 {0xdc7528, 4, 2}；ret
```

**0x62F6C0 是什么**（本轮确证）：

```
0x62F6C0  xor eax,eax ; push 0x40 ; push 0
          mov [esi+0x3A048],eax ; mov [esi+0x3A04C],eax
          lea eax,[esi+0x3A050] ; call memset
          lea ecx,[esi+0x3A090] ; jmp 0xB75D90
=> 一个纯粹的"重置关联状态"函数
其**全部 3 个调用者都在 0x632680 内**：0x632712、0x632812、0x63288C
```

**0x62F6F0**（A/B 安装器，018 结论的落地处）：
```
0x62F6F0(esi=matching, edi=元素)
   先做与 0x62F6C0 相同的重置（A/B=0），再：
   0x62F736  ecx = [edi+0x168] ; 0x62F73C  [esi+0x3A048] = ecx
   0x62F742  edx = [edi+0x16C] ; 0x62F748  [esi+0x3A04C] = edx
   0x62F74E  再拷贝 [edi+0x170] 的字符串到 +0x3A050
调用者：0x62F917、0x63789D、0x6378BE（会话对象解析 / 本地选择路径）
```

### 2.1 由此得到一条可判别的动态判据

```
"matching+0x3A048 由非零变为 0 且**保持** 0"
  => 只可能来自 0x62F6C0（3 个调用者全在 0x632680 内）或 0x6328F7（同在 0x632680 内）
  => **证明 0x632680 被进入过，并且走了某个"重置出口"**
  （0x62F6F0 的前置重置是瞬时的——同函数内几步之后就把 A 写回元素值，
    采样间隔 6~11ms 不可能稳定抓到；而实测 A=0 持续超过 0.7 秒）
```

---

## §3 用 019 的真实证据做闭合（本轮决定性一步）

### 3.1 服务端：accepted 确实发出去了，而且带了长度前缀

lobby_srv_019test.log（20:22:32 那一轮，逐行）：

```
[20:22:32]  ★ findSessions -> 21/5 应答（PvE coop mission session 对象, 236 字节）
[20:22:32]  ★ 解密 #12 seq=12 service=6 task=14
             payload(45): 0a 88 77 66 55 44 33 22 11 13 08 1d 00 00 00 19 00 00 00 6d 6d 62 6f 6f 6b ...
             （客户端 mmbook 请求里回显了 #7 = 0x1122334455667788）
[20:22:32]  -> 6/14 命中 'mmbook' -> push 'mmbook accepted'(data=20)
[20:22:32]  -> 0x85 应答 seq=22(replyId=22) service=6 task=14 对象=0 (66 字节)
[20:22:32]  -> 0x85 推送 type=2 seq=1022(请求seq+1000) (98 字节 body=51)
[20:22:32]  对端关闭                                  （客户端立刻关闭连接）
```

data=20 正是 lobby_server.py:850 的产物：
```
FR_BOOKING_ACCEPTED = b"mmbook accepted" + NUL          # 16 字节
accepted = struct.pack("<I", len(FR_BOOKING_ACCEPTED)) + FR_BOOKING_ACCEPTED   # 4+16 = 20 字节
pushes = [(2, cc.instant_push_body(SESSION_ID, "localhost", accepted))]
=> blob 内容 = 10 00 00 00 | 6d 6d 62 6f 6f 6b 20 61 63 63 65 70 74 65 64 00
```

### 3.2 客户端：blob 读取器原样拷贝，不剥内层 u32

```
0xB76AF0(ecx=消息对象, [ebp+8]=缓冲区, [ebp+0xC]=容量指针)
  0xB76AF5  push 0x13  ; call 0xB76310   -> 期望 tag 0x13
  0xB76B11  call 0xB761E0                -> 读 tag 0x08 的 u32 = blob 长度 -> esi
  0xB76B31  push eax(长度) / push ecx(缓冲区)
  0xB76B35  call 0xB75E80                -> ★ 把 blob 的 esi 个字节原样读入缓冲区
  0xB76B52  [容量指针] = esi
=> 缓冲 = blob 的原始内容（含那 4 字节前缀），**没有任何剥离**
```

### 3.3 客户端探针：A/B 先对齐、后被清零；this288 从未为 1

accepted_state_019test.txt（265 行，只读解析）：

```
this288_byte : 0 x251, -1 x14             -> 从未出现 1
A            : 0x55667788 x72, 0x00000000 x20
B            : 0x11223344 x72, 0x00000000 x20
this278      : 0x0000 x56, 0x0101 x29, 0x0001 x7
flag849B61C  : 1 x85, 0 x8
t_5E8        : 3 x42, 0 x29, 1 x11, 2 x8

时间线（A/B/this278/this288 变化点）：
  20:22:27.686  this278=0x0001 , t_5E8=3
  20:22:27.692  this278=0x0101 , flag=1
  20:22:27.709  A=0x55667788 B=0x11223344          <- 对齐成立（G4/G5 满足）
  20:22:27.727  this278=0x0000 , t_5E8=0            <- 武装窗口 ~41ms 后关闭
  20:22:32.216/.222/.251  再次武装 -> 关闭（~35ms）
  20:22:36.642/.648/.677  再次武装 -> 关闭（~35ms）
  20:22:41.665  A=0x00000000 B=0x00000000 , this278=0 , t_5E8=3
  20:23:33.082+ A 仍为 0
```

逐条吻合 G6 失败路径：
```
(1) G4/G5 满足（A/B 对齐） => 失败不可能是 0x632916 那条出口（它不动 A/B）
(2) A/B 后来变成 0 并保持    => 走了"重置出口"：0x62F6C0 或 0x6328F7
(3) this288 恒 0             => 没走 0x632812（成功路径也调 0x62F6C0，但会先把 0x288 置 1）
(4) 服务端每次 6/14 都推了 accepted（data=20） => wire 侧确实到了
(5) push 与武装窗口同秒（20:22:27/32/36）     => 时间不是主因，内容才是
```

=> **唯一自洽解释：0x632680 进入后，G1/G2/G3 通过、G4/G5 通过，在 G6 处失败。**
   （G7 在 G6 之后，不可能先失败。）

---

## §4 为什么 017 那次也失败（且方式不同）

017（baseline，未对齐）：A = 1（会话对象 #7 = 1），响应信封 A = 0x55667788

```
=> G4 在 0x6326BF 就失败 -> jne 0x632916（**不重置**）
=> 与 017 观测一致：A 保持 1、B 保持 0，this288 = 0
=> 017 的失败点是 G4；019 把 G4/G5 修好之后，失败点前移到 G6
```

**所以 019 并没有白做**：它把失败点从 G4 推进到 G6，从而暴露出真正的根因。

---

## §5 修复点（本轮不实施，仅记录）

lobby_server.py 的 6/14 推送分支（约 847-853 行）与另一分支（约 904-909 行）：

```
现状（错）: accepted = struct.pack("<I", len(FR_BOOKING_ACCEPTED)) + FR_BOOKING_ACCEPTED
             pushes = [(2, cc.instant_push_body(SESSION_ID, "localhost", accepted))]
正确（应）: pushes = [(2, cc.instant_push_body(SESSION_ID, "localhost", FR_BOOKING_ACCEPTED))]
理由      : instant_push_body 内部的 ob.blob() 已经写了 13 08 + u32 长度，
            客户端 0xB76AF0 读到的就是这块"裸内容"；
            再套一层 u32 前缀会让 strncmp 从第 0 字节即失配
参照      : 同文件 898 行那条分支用的就是裸文本 b"mmbook accepted"（无前缀）
```

注意：FR_BOOKING_ACCEPTED 目前是 16 字节（含 NUL）。裸发 16 字节没问题
（strncmp 只比 15 字节）；若要更贴近，可发 15 字节无 NUL 版，但不是必须。

---

## §6 仍未确定的部分（诚实边界）

```
U-1 **G2 的运行时取值未知**：0x76446B0 不是计数器，而是一个**全局游戏状态枚举**
    （全镜像 230 处访问，比较值覆盖 0/1/3/4/5/6/7/8/9/0xA；写入点设过 0、3、4、7）。
    G2 要求 < 3。它在大厅里的实际取值本轮未采样 -> UNKNOWN。
    但即使 G2 通过与否未知，也不影响结论：G6 的输入（带前缀的 blob）已被静态证实**必然失配**，
    所以只要函数被进入，G6 就一定会失败。
U-2 G6 失败后走 0x632712 还是 0x63288C，取决于 byte[matching+0x280] 与 dword[matching+0x10780]，
    两者本轮未被采样 -> UNKNOWN（两条路都会重置 A/B，不影响结论）。
U-3 G1 的 armed 语义（0x278 的两个写点 0x62CCCD / 0x62FBBB 分别对应"开始预约 / 清理"）
    已由 BOOKING_STATE-001 建立，但"窗口为何只有 20~35ms"未解 -> UNKNOWN。
U-4 0x632812 之后 vt+0x5C 的语义（016 已确认为"门控广播"）本轮未再展开。
U-5 0x631E50（0x632791 调用）的门控（要求传输 state==1）是否也会成为后续阻塞 -> 未评估。
```

---

## §7 硬结论

```
ACCEPTED_GATE_COUNT        = 7（G1..G7），此前记录为 2
FAILING_GATE               = G6（0x6326DF，strncmp(msg, "mmbook accepted", 15)）
ROOT_CAUSE                 = blob 内多 4 字节 u32 前缀（服务端 lobby_server.py:850 / 908）
ROOT_CAUSE_LEVEL           = CONFIRMED
                             静态：写入端 + 读取端 + 比较端三方对齐
                             动态：019 的 A/B 归零路径与 this288 恒 0 逐条吻合
ACCEPTED_HANDLER_ENTERED   = CONFIRMED（由 A/B 持久归零反推）
ACCEPTED_BRANCH_EXECUTED   = REFUTED（0x63280B 从未执行）
PUSH_TO_ACCEPTED_HANDLER   = 维持 020 的 CONFIRMED（分派层成立）
BATTLE_RELEVANCE           = 无关：本门未通过，客户端根本走不到取端点 / 拨 28960
                             （与 021 的 BATTLE_SERVER_REQUIRED = REFUTED 一致）
NEXT_STEP                  = 由"改 server"这一步决定；本轮按纪律**未改**
                             若授权，最小改动 = 去掉那 4 字节前缀（1 行 x2 处），
                             然后重测 this288 是否变为 1
                             若变为 1，再进入 020 遗留的 additional guard / 端点链路评估
```

（全文完 · STATIC ONLY · 未修改任何文件）


