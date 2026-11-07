# PVE-ACCEPTED-DISPATCH-026
# service=21 -> 0x7F1400 -> 0x632680 静态闭环与运行时可达性

```
STATIC_ACCEPTED_DISPATCH_PATH = **CONFIRMED**
RUNTIME_632680_EXECUTION      = **UNKNOWN**

G6_STATIC_PATH = **CONFIRMED**     G6_RUNTIME = **UNKNOWN**
G7_STATIC_PATH = **CONFIRMED**     G7_RUNTIME = **UNKNOWN**

SECOND_VTABLE_0xDC7850_STATUS = **STATIC_ONLY**（已定位其宿主对象；无该槽的调用证据）
MESSAGE_PUMP_PATH             = **CONFIRMED**（静态）
CONNECTION_TEARDOWN_PATH      = **CANDIDATE / 部分 UNKNOWN**

H_A = **STRONG_CANDIDATE**
H_B = **REFUTED**（来自 025）

BATTLE_28960 = **NOT_OBSERVED**

RESULT_CASE = 「静态链完整 + runtime 无法用现有非侵入手段确认」
              -> instrumentation boundary reached（按任务书 §十四，不自行升级）
NEXT_TARGET = 「客户端消息泵 / 连接 teardown 的运行时可达性」（不是协议格式，不是 Battle Server）
```

冻结基线（本轮未改动任何文件）：
```
codol_crypto.py   = E836C63AF75DD82EF6F3B07EF63FAE48B044B3B5047336127093C92B07644607（ORIGINAL）
lobby_server.py   = 7BBDC4F2B84DD14BD9FE3B6949F4946F805045841B8B3A170BC880585C6B9384（023 blob 修复保持）
battle_server.py  = 71BB7BEB85E514082B91A4925D18CB09FD07D5E8916FFA7F4FBD4A9750B47274（Golden）
nt10.py           = DEAA33E80AFB8FD99AC3666BF101B2A2450D32ADF0DF1004F94E057A67363145（025 只读采样器）
本轮为纯静态分析：未 hook / 未 breakpoint / 未 debugger / 未注入 / 未写内存 / 未 patch。
```

---

## §1 STATIC_SERVICE21_PATH = CONFIRMED

```
wire: u32 payload_len | marker 0x02 | payload(TLV)
payload TLV: 08 <u32 service=21> | 0A <u64 senderId> | 10 <str "localhost" NUL>
             | 13 08 <u32 blob_len> <blob>

0x007F3800  mov eax,[0x84ABA7C]        <- lobby 状态机
0x007F3805  sub eax,0 ; je 0x7F386B    (state 0 走另一支)
0x007F380B  dec eax ; jne 0x7F3870     <- **只有 state == 1 才继续**
0x007F380E  call 0x803830              <- 取当前传输对象 -> esi
0x007F3815  test esi,esi ; je 0x7F3870
0x007F3819  push 0x81A5570 ; call [0xCA819C]   <- 临界区加锁
0x007F3826  call 0xB838A0              <- **消息泵（持锁调用）**
0x007F382B  push 0x81A5570 ; call [0xCA8190]   <- 解锁
0x007F3838  call 0xB7A670              <- 泵后处理（返回与 4 比较）
         ->
0x00B82A90  service switch（表 0xB83744，index = service-1 = 20，上限 0x4A）
         ->
0x00B8309B
         ->
0x00B7C900
   读 TLV: 0xB761E0(=0x08 u32 service) / 0xB769A0(0x0A u64) /
           0xB76A30(0x10 str, 0x40 buf) / 0xB76AF0(0x13 blob, 0x1000 buf)
   0xB7C9DE  mov ecx,[esi+0x4F0]
   0xB7C9E4  mov eax,[ecx]
   0xB7C9E6  mov eax,[eax+0x68]        <- manager vtable +0x68
   0xB7C9E9  push edx (len) ; push &buf4096 ; push &str40 ; push hi ; push lo
   0xB7CA05  call eax                  <- = 0x7F1400
```

复核（本轮重新执行）：refs 0x7F1400 全镜像只有 **一个** dword 引用 = 0xDE080C
= 0xDE07A4 + 0x68（manager 单例 [0xE39B6E8] 的 vtable）-> 与 020 一致。

## §2 STATIC_MMBOOK_PATH = CONFIRMED

```
0x007F1540..  strncmp(<matching 侧字符串>, "mmbook", 6)    （020 已建立）
0x007F1554    mov ecx,[0x82E13FC]        <- matching 单例
0x007F155A    mov eax,[ecx]              <- 该对象的 vtable
0x007F155C    mov eax,[eax+0x13C]        <- vtable +0x13C
0x007F156F    call eax                   <- **唯一已定位的 0x632680 调用点**
```

## §3 STATIC_632680_CALLER = CONFIRMED

```
0x7F156F  call eax      其中 eax = [[0x82E13FC]] + 0x13C
=> service 21 -> 0xB7C900 -> 0x7F1400 -> 0x7F156F -> [matching+0x13C] -> 0x632680   闭环成立
```

## §4 第二个 vtable 0xDC7850_STATUS = STATIC_ONLY（本轮新解，含关键澄清）

### 4.1 0xDC7850 属于 0xDC7714 这一张表

```
0xDC7714 + 0x13C = 0xDC7850 -> 0x632680        （0xDC7714 的 dword 引用 = 安装点 0x638244）
0xDC7274 + 0x13C = 0xDC73B0 -> 0x632680        （0xDC7274 的安装点 = 0x62C025）
0xDC7274 与 0xDC7714 的前 8 个槽**完全相同**（0x6391E0,0x62CA80,0x62D5D0,0x62D7E0,
0x62DA10,0x62DB50,0x62DC50,0x62DD60）=> 同一类族的基/派生两张表
```

### 4.2 0xDC7714 是"某个 0x3A160 对象在 +0x18 处的子对象"的 vtable

构造函数 0x638210(ebx = 对象)（调用者只有一处：0x639D3D）：

```
0x63821B  [ebx+4]=[ebx+8]=[ebx+0xC]=0
0x638225  [ebx+0x10] = 0xDC7D4C
0x63822C  esi = ebx+0x18
0x638230  [ebx]      = **0xDC73DC**          <- 外层对象 vtable
0x638236  [ebx+0x10] = 0xDC7474
0x63823D  call 0x62C000                      <- 子对象基类构造
0x638242  mov [esi], 0xDC7714                <- **把子对象 [ebx+0x18] 的 vtable 覆盖为 0xDC7714**
0x638248  edi = ebx+0x3A148
0x638254  [edi] = 0xDC787C                   <- 另一个子对象 vtable
0x63826A  mov esi,[0x82E13FC]                <- 读 matching 单例
0x638280  add esi,4 ; 遍历 [matching+4] 链表 -> 把 edi 注册为 listener
```

分配与存放（0x639D00 起）：

```
0x639D03  push 0x3A128 ; operator new ; call 0x62C000 ; **mov [0x82E13FC], eax**   <- matching 单例
0x639D2B  push 0x3A160 ; operator new ; call 0x638210 ; **mov [0x82E1400], eax**   <- 另一个对象
```

结论：
```
- service=21 走的 **[0x82E13FC]** 由 0x62C000 构造（0x3A128 字节）-> vtable 为 0x62C025 安装的那张
  = **0xDC7274** -> +0x13C = **0xDC73B0** = 0x632680   (即"第一处"才是本路径实际生效的槽)
- 0xDC7714 属于 [0x82E1400] 那个 0x3A160 对象在 **+0x18** 处的子对象（0x638210 构造，构造函数内
  还把它自己的一个子对象注册进 matching 的 listener 链表）-> 属于 **另一个(listener/provider)对象**
- 0xDC7714 的 +0x13C（0xDC7850）**有实例化证据**（0x639D3D 分配、0x639D42 存全局），
  但**没有任何运行时证据**表明该槽被调用
=> SECOND_VTABLE_0xDC7850_STATUS = **STATIC_ONLY**，不并入 service=21 路径
```

### 4.3 一个已排查并排除的疑似新入口

```
0x6383A6  mov ecx,[0x82E13FC]
0x6383AE  mov eax,[edx+0x68]        <- matching vtable +0x68
0x6383B1  call eax
经查：0xDC7274 + 0x68 = 0xDC72DC -> **0x62FDC0**（matching 模块内函数），**不是** 0x7F1400。
=> 这**不是**第二个 mmbook 分派入口。已排除。
```

## §5 MESSAGE_PUMP_PATH = CONFIRMED（静态）

```
入口（只有 lobby state == 1）：0x7F3800 -> 0x803830 -> 持锁 0x81A5570 -> 0xB838A0

0x00B838A0(ecx = 传输对象 esi)：
  0xB838C9  lea ecx,[esi+0x5F0] ; call 0xB75DA0 ; fstp [ebp-0x18]   <- 取时间戳(float)
  0xB838D7  cmp byte [esi+0x5E8], 0 ; je 0xB8391A                   <- 首次调用标志
  0xB838E0  fld [0xD599EC] ; fcom ...                               <- 与阈值比较
  0xB83920  mov byte [esi+0x5E8], 1
  0xB8392C  **cmp dword [esi+0x4F4], 0 ; je 0xB83ADE**               <- 连接/套接字对象存在性门
  0xB83939  ... （进入实际的消息处理）
```

静态机制（对 H-A 直接相关）：泵在真正处理消息之前，先要求
[transport+0x4F4] 非 0（活的套接字/连接对象）；一旦该对象被清除，泵会直接跳过，
**队列里尚未处理的消息不会被分派**。并且泵是在临界区 0x81A5570 内被调用的，
所以"拆除"与"泵"之间是串行的 —— 即拆除只要发生在两次泵调用之间，之后的消息就可能永远不被处理。

## §6 CONNECTION_TEARDOWN_PATH = CANDIDATE / 部分 UNKNOWN

```
已确认：泵的存在性门 = [transport+0x4F4]（§5）。
未完成：清除 +0x4F4 / 置 [0x84ABA7C] / 触发 "对端关闭 -> 重连" 的那条路径**尚未完整恢复**。
=> 标 **CANDIDATE**，不写成 CONFIRMED。
=> 因此**不能**断言"teardown 一定导致 pending accepted 被丢弃"（任务书 §十九 要求的升级证据尚未取得）。
```

---

## §7 G6_STATIC_INPUT_SOURCE = CONFIRMED

完整链路（本轮反汇编新证实）：

```
server wire:  13 08 10 00 00 00 | 6d 6d 62 6f 6f 6b 20 61 63 63 65 70 74 65 64 00
              （023 修复后：blob_len = 16，blob[0:15] = "mmbook accepted"）
     |
     v
0x7F1400 自身重新取 blob：
  0x7F1438  call 0xB74220                       <- 取对象
  0x7F144A  call 0x4F3F60(0, len, buf)          <- 用 (buf,len) 得到消息对象 -> edi
  0x7F1463  lea edx,[esp+0x18]                  <- 长度输出
  0x7F1468  lea eax,[esp+0xB4]                  (等效 = 原帧 [esp+0xB0])
  0x7F146F  mov esi,0x800
  0x7F147B  call 0xB76AF0                       <- ★ 读 tag 0x13 blob，**原样**拷入缓冲
  0x7F14DA  mov byte [esp+eax+0xB0], 0          <- NUL 结尾
  0x7F14E2  lea ebx,[esp+0xB0]                  <- ★ ebx = 该缓冲
     |
     v
0x7F1562..0x7F156E  依次 push：len, ebx, edi(str40), [ebp+0xc], [ebp+8]
0x7F156F  call [matching+0x13C] = 0x632680
     |
     v
0x632680  [ebp+0x08]=A  [ebp+0x0C]=B  [ebp+0x10]=str40  [ebp+0x14]=msg(=ebx)  [ebp+0x18]=len
0x6326DF  strncmp(msg, "mmbook accepted", 15)
```

要点：
```
(1) 比较用的缓冲是 **0x7F1400 自己的 [esp+0xB0]**（由它自己的 0xB76AF0 填充）；
    入口处从 0xB7C900 传入的 arg4（[ebp+0x14]）在中途被 0x7F14E2 覆盖。
(2) 0xB76AF0 **原样**拷贝 blob（只吃 tag 0x13 之后的 tag 0x08 u32 长度），不剥内层 u32
    —— 这正是 022 的根因，也是 023 修复后 G6 应当匹配的原因。
(3) 比较长度恰为 15 = "mmbook accepted" 的字节数；blob 为 16 字节（15 + NUL），
    NUL 不参与比较；**不得再有 4 字节内层长度**。
```

=> G6_STATIC_PATH = CONFIRMED（静态：023 修复后的字节确实完整进入 G6 的比较输入）
=> G6_RUNTIME = UNKNOWN（无运行时证据表明执行到 0x6326DF）

## §8 G7_STATIC_INPUT_SOURCE = CONFIRMED（静态）

```
0x6326FB  cmp [eax+esi+0x75D8], [ebp+8]     ; 元素 +0x168 vs A(响应信封 u64 低 32 位)
0x632707  cmp [eax+esi+0x75DC], ebx         ; 元素 +0x16C vs B(高 32 位)
其中 eax = [esi+0xE360] * 0x238（matching+0x7470 预约数组，索引在 +0xE360）
```

=> G7_STATIC_PATH = CONFIRMED ; G7_RUNTIME = UNKNOWN

## §9 运行时侧（只用已有非侵入证据）

```
已有证据（023/024/025 只读探针 + 服务端日志）能给出：
  - 024：G1/G4/G5 在 22:51:28.836-.946 同时成立，push 同秒发出，288 = 0
  - 025：G1 成立窗口内 G2/G3 全部 PASS，288 = 0
  - 024/025：push 后**同一秒**连接结束 + 立即重连（每个周期都如此）

不能给出：
  - 0x632680 / 0x6326DF / 0x632707 中的任一执行证据
  - "0x85 帧是否被消息泵取走" 的任何直接记录

规范判定（严格区分四种等级）：
  STATIC_ACCEPTED_DISPATCH_PATH = CONFIRMED
  RUNTIME_632680_EXECUTION      = UNKNOWN
  RUNTIME_G6                    = UNKNOWN
  RUNTIME_G7                    = UNKNOWN
```

禁止的推断（本轮严格遵守，未使用）：
```
288 == 0                  => handler 没执行        （禁止，未使用）
connection close          => handler 没执行        （禁止，未使用）
server push 成功          => client handler 已执行   （禁止，未使用）
static caller exists      => runtime caller executed（禁止，未使用）
```

## §10 四轮统一视图

```
019 : A/B aligned + bad blob     -> G4/G5 PASS     -> 288=0 ; G6 runtime UNKNOWN
023 : A/B misaligned + good blob -> G4 FAIL        -> G6 NOT_REACHED
024 : A/B aligned + good blob    -> G1/G4/G5 PASS  -> 288=0 ; G6 runtime UNKNOWN
025 : G1/G2/G3 PASS（可读样本）   -> 288=0 ; H-B REFUTED
026 : 静态闭环 CONFIRMED ; SECOND_VTABLE = STATIC_ONLY ; 泵存在 [transport+0x4F4] 门

=> G1-G5 = 目前已证明**不存在**阻塞点
=> G6/G7 runtime 与 0x632680 runtime 执行 = UNKNOWN
=> H_A = STRONG_CANDIDATE（其静态机制已找到：泵的 [transport+0x4F4] 存在性门）
=> H_B = REFUTED
```

## §11 必填字段汇总

```
STATIC_SERVICE21_PATH   = CONFIRMED
STATIC_MMBOOK_PATH      = CONFIRMED
STATIC_632680_CALLER    = CONFIRMED（0x7F156F, eax=[[0x82E13FC]]+0x13C）

0x7F1400                = manager vtable +0x68（唯一 dword 引用 0xDE080C）—— service=21 分派入口
0x7F156F                = 0x632680 的唯一已定位调用点（位于 0x7F1400 内部）
0x632680                = accepted handler（ret 0x14, 5 参数）

SECOND_VTABLE_0xDC7850_STATUS = STATIC_ONLY
  宿主 = 0x638210 构造的 0x3A160 对象（存于 [0x82E1400]）在 +0x18 的子对象
  本路径实际生效槽 = 0xDC7274+0x13C = 0xDC73B0 -> 0x632680

MESSAGE_PUMP_PATH        = CONFIRMED（0x7F3800 state1 -> 0x803830 -> lock -> 0xB838A0 -> unlock -> 0xB7A670）
CONNECTION_TEARDOWN_PATH = CANDIDATE（未完整恢复；泵的门 = [transport+0x4F4]，见 §5/§6）

G6_STATIC_INPUT_SOURCE  = 0xB76AF0(tag 0x13 blob, 原样) -> 0x7F1400 [esp+0xB0] -> ebx -> 0x632680 [ebp+0x14]
G7_STATIC_INPUT_SOURCE  = reservation[[matching+0xE360]].+0x168/+0x16C vs [ebp+8]/[ebp+0x0C]

RUNTIME_632680 = UNKNOWN ; RUNTIME_G6 = UNKNOWN ; RUNTIME_G7 = UNKNOWN

H_A = STRONG_CANDIDATE
H_B = REFUTED

RESULT_CASE = 静态完整 / runtime instrumentation boundary reached
NEXT_TARGET = 客户端消息泵与连接 teardown 的运行时可达性
```

## §12 Hard Stop 说明

```
按任务书 §二十四：静态闭环（service 21 -> 0xB7C900 -> 0x7F1400 -> 0x7F156F -> 0x632680）已完成，
本轮**停止**扩大搜索；runtime 执行无法用现有非侵入式证据证明，故如实记 UNKNOWN，
未引入 hook / debugger / patch，也未做任何 Server timing 实验（§二十）与 Battle 研究（§二十一）。
```

（全文完 · 纯静态 · 未修改任何文件）

