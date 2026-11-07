# PVE-MATCHING-AB-FIELD-IDENTITY-018
# matching+0x3A048 / +0x3A04C 的字段身份与来源链（纯静态）

> 2026-10-08 执行。**严格 STATIC ONLY**。
> 未启动游戏、未改 EXE/DLL、未 patch、未 hook、未发包、未改用调试器、
> 未改 senderId/SessionId/server/Lobby protocol/accepted response、
> 未重跑 017、未碰 listener / type-2 / UDP-28960 / endian / ACE bypass。
> 只读：原始 EXE、运行时镜像反汇编、strings、xref、构造/调用链、已有报告。

---

## 0. RESULT

```
RESULT = 已完整定位。

matching+0x3A048 / +0x3A04C 不是 SessionId，也不是 response envelope 的 A/B。
它们是 **21/5 findSessions 会话对象里那个 tag=0x0A 的 u64 字段（字段序 #7）**
经客户端反序列化器写进"会话记录"对象 +0x168/+0x16C，再被 0x62F6F0 搬到 matching 的。

而我们的服务端把该 u64 **硬编码成 1**（codol_crypto.py: ob.u64(1)  # 7），
envelope 的 senderId 却是 SessionId 0x1122334455667788 →
两边是**两套不同字段**，因此在 0x6326B9 必然不相等。

  RESPONSE_AB (0x55667788, 0x11223344)  !=  MATCHING_AB (1, 0)
  ⇒ RESPONSE_AB != MATCHING_AB   （CONFIRMED）
```

---

## 1. FACT_BASELINE

### 1.1 承接（未重查）

```
accepted handler 0x632680；0x6326B9 cmp eax,[esi+0x3A048] / jne 0x632916      （013/017）
0x7F1400 分派器：ecx=[0x082E13FC]，A/B = 信封 senderId 的 LOW/HIGH32          （013）
wire senderId = SessionId 0x1122334455667788（lobby_server.py L458/L851/L909） （012/017）
017 实测：[matching+0x3A048]=1，[matching+0x3A04C]=0                          （017）
endian 结论保持（本轮不重开）                                                  （013）
```

### 1.2 本轮新增（全部指令级）

```
0x62F6F0(matching=esi, item=edi)：
  0x62F717   mov [esi+0x3A048], 0        ; 先清零
  0x62F71D   mov [esi+0x3A04C], 0
  0x62F736   mov ecx, [edi+0x168]        ; ★ A = item+0x168
  0x62F73C   mov [esi+0x3A048], ecx
  0x62F742   mov edx, [edi+0x16C]        ; ★ B = item+0x16C
  0x62F748   mov [esi+0x3A04C], edx
  0x62F74E   lea edx, [edi+0x170]        ; ★ item+0x170 = C 字符串（inline）
  0x62F760.. strlen
  0x62F78D   call 0xC427F0               ; strncpy([esi+0x3A050], edx, min(len,0x3F))
```

⇒ item 的布局 = { ..., u32 @+0x168, u32 @+0x16C, char[] @+0x170 }。

---

## 2. edi 是什么对象（caller / ctor / 归谁）

### 2.1 0x62F6F0 的三个调用点，edi 全部由同一公式算出

```
caller A  0x62F917   （函数 0x62F836，= matching vt+0x3C）
  0x62F902   mov [ebx+0xE360], eax            ; ebx = matching，eax = 索引
  0x62F908   imul eax, eax, 0x238
  0x62F90E   lea edi, [eax+ebx+0x7470]        ; ★ edi = matching + 0x7470 + idx*0x238
  0x62F915   mov esi, ebx                     ; esi = matching
  0x62F917   call 0x62F6F0

caller B  0x63789D
  0x637896   lea edi, [edx+esi+0x7470]        ; 同公式（esi = matching）

caller C  0x6378BE
  0x6378AB   mov [esi+0xE360], ebx            ; idx = 0
  0x6378B1   imul ebx, ebx, 0x238
  0x6378B7   lea edi, [ebx+esi+0x7470]        ; 同公式
```

### 2.2 该数组

```
构造  matching ctor 0x62C000：
  0x62C0C7   lea esi, [ebx+0x7470]           ; 数组基址 = matching+0x7470
  0x62C0CD   mov [ebp+0xC], 0x31             ; ★ 0x31+1 = 50 个元素
  0x62C0D8   call 0x806B50                   ; 逐元素构造
  0x62C0DD   add esi, 0x238                  ; ★ stride = 0x238
  0x62C0E8   mov [ebx+0xE360], -1            ; 选中索引 = -1
  数组范围 = 50 * 0x238 = 0x6EF0 字节（0x62CD66 的 memcpy 大小正是 0x6EF0）

另有"暂存对象" matching+0x7238（同类、0x238 字节）：
  0x62C0B6   lea ecx, [ebx+0x7238] / call 0x806B50   ; ctor
  0x637D55   mov dword [ebx+0x7238], 0xDC79F0        ; 直接装 vtable（复用/重置）
```

### 2.3 元素类（0x238 字节）

```
元素 ctor = 0x00806B50
  0x806B55   xor ebx, ebx                    ; ebx = 0
  0x806B89   mov dword [esi], 0xDC79F0       ; ★ vtable = 0xDC79F0
  0x806B8F   mov dword [esi+8], 0xDC79FC
  0x806B99   mov dword [ecx+esi+4], 0xDC7A08
  0x806BA1   lea ecx, [esi+0x1CC]
  0x806BA7   mov dword [esi+0x168], ebx      ; ★ +0x168 = 0（构造初始化）
  0x806BAD   mov dword [esi+0x16C], ebx      ; ★ +0x16C = 0
  0x806BB3   mov dword [esi+0x1B0], ebx
  ...
ctor 调用点（全镜像仅 6 处）：
  0x62C02C / 0x62C0A4 / 0x62C0C2 / 0x62C0D8   matching ctor（数组 + 暂存）
  0x7C10EB   栈上实例，随后注册名字 "serv" / "partySession" / "searchSession"
  0xC956C7   静态实例 @0x0E3ECA98（网络/地址区）
RTTI 已被剥离（COL 0xDF84AC 解析失败）→ 类名不可恢复。
```

⇒ 该 0x238 字节类是 Demonware 的**会话/地址描述符**（0x7C10EB 把它注册为
  serv / partySession / searchSession）。matching+0x7470 是它的一份 **50 槽副本数组**。

---

## 3. 真正的写入者：会话记录的反序列化器 0x00806F20

0x806F20 是**元素类 vtable[0]**（唯一引用 = vtable 0xDC79F0 的第 0 项），
它是一个"从网络流读字段写回 this"的**反序列化器**：

```asm
0x00806F20  push ebp / mov ebp,esp / push ecx / push ebx / push esi / push ecx
0x00806F27  mov  esi, ecx                 ; esi = this（会话记录）
0x00806F29  mov  ecx, [ebp+8]             ; ecx = 输入流对象
0x00806F3B  call [0xCA8128]               ; addref(stream)
0x00806F43  call 0xB95D70                 ; ★ 批量读：blob + 3 个标量
0x00806F50  mov  ecx, [ebp+8]
0x00806F53  push 0x40
0x00806F55  lea  edx, [esi+0x128]         ; 目标 = this+0x128
0x00806F5C  call 0xB76A30                 ; ★ 读 tag=0x10 字符串（cap 0x40）
0x00806F69  mov  ecx, [ebp+8]
0x00806F6C  lea  eax, [esi+0x168]         ; ★★★ 目标 = this+0x168
0x00806F73  call 0xB769A0                 ; ★★★ 读 tag=0x0A u64（8 字节）
0x00806F80  push 0x40
0x00806F82  lea  ecx, [esi+0x170]         ; 目标 = this+0x170
0x00806F8C  call 0xB76A30                 ; ★ 读 tag=0x10 字符串（cap 0x40）
```

**0xB769A0 = u64 读取器（决定性）**

```asm
0x00B769A0  push ebp / mov ebp,esp / sub esp,8 / push esi
0x00B769A7  push 0x0A                    ; ★ 要求 tag == 0x0A（u64）
0x00B769AB  call 0xB76310                ; 校验 tag
0x00B769B0  test al,al / je fail
0x00B769B4  push 8                       ; ★ 8 字节
0x00B769B6  lea  eax, [ebp-8]
0x00B769B9  push eax
0x00B769BA  mov  ecx, esi
0x00B769BC  call 0xB75E80                ; 读 8 字节
0x00B769C5  mov  eax, [ebp+8]            ; eax = 目标指针
0x00B769C8  mov  ecx, [ebp-8]            ; 低 32 位
0x00B769CB  mov  edx, [ebp-4]            ; 高 32 位
0x00B769CE  mov  [eax], ecx              ; ★ +0x168 = u64 低 32 位
0x00B769D0  mov  [eax+4], edx            ; ★ +0x16C = u64 高 32 位
0x00B769D3  mov  al,1 / ret 4
```

⇒ **item+0x168 = u64 低 32 位；item+0x16C = u64 高 32 位。**
  写入用的是 [eax]/[eax+4]（指针间接），所以按 disp=0x168 的静态扫描**看不到这个写点**，
  这正是"全镜像搜 +0x168 写入点"只看到 ctor / copy 的原因。

同理 0xB76A30 读 **tag=0x10 字符串**（逐字节读到 NUL，cap 由参数给）→ 写 +0x128 / +0x170。

---

## 4. 字段序对齐：证明用的就是 21/5 会话对象

0xB95D70（0x806F20 的第一步）把若干标量写进 this：

```asm
0x00B95DA1..0xB95DB2  call 0xB76AF0      ; tag=0x13 blob -> [esi+0x18] 等
0x00B95DBA  mov [esi+0x118], edx
0x00B95DCB..0xB95DD6  call 0xB76AF0      ; 第二个 blob -> [esi+0x10]（cap 8）
0x00B95DF3..0xB95DF7  call 0xB761E0 -> [esi+0x11C]
0x00B95E20..0xB95E21  call 0xB761E0 -> [esi+0x120]
0x00B95E44..0xB95E49  call 0xB761E0 -> [esi+0x124]   ; ★ 关键
```

而本任务里 build_mission_session_object 的字段序（codol_crypto.py 文档 + L542/L551 代码）：

```
#1 地址 blob        19 08 <len> ...
#2 SessionId blob   19 08 08 <8B>            ← SessionId 走 **blob**
#3 u32 0            08 00000000
#4 u32 0            08 00000000
#5 u32 1 (Players)  08 01000000
#6 map 字符串       10 <ASCII> 00
#7 u64 1            0A 01 00 00 00 00 00 00 00   ← ★★★ ob.u64(1)  # 7
#8 hostname         10 "localhost" 00
...
#28 u64 1           0A 01 00 00 00 00 00 00 00   ← ob.u64(1)  # 28
```

**一一对应（CONFIRMED）**：

```
服务端字段                  → 客户端会话记录
#1 addr blob                → rec+0x18
#2 SessionId blob           → rec+0x10        （8 字节，tag 0x19 blob）
#3 u32 0                    → rec+0x11C
#4 u32 0                    → rec+0x120
#5 u32 1 (Players)          → rec+0x124        ★ 过滤器字段
#6 map 字符串               → rec+0x128
#7 u64 1                    → rec+0x168 / +0x16C     ★★★ A/B 的真正来源
#8 hostname 字符串          → rec+0x170
```

**闭环证据（不是数值巧合）**：客户端"会话列表复制器" 0x637950 用 **rec+0x124** 做过滤：

```asm
0x00637950  ...（filter + copy）
0x00637975  cmp dword ptr [eax+0x124], edx    ; edx = 1
0x0063797B  ja  0x63799F                      ; > 1 -> 跳过
0x00637989  lea edi, [ecx+ebx+0x7470]         ; 目标 = arr[idx]
0x00637990  mov ecx, 0x8E                     ; ★ 0x8E dwords = 0x238 字节
0x00637997  rep movsd
0x00637999  add dword ptr [ebx+0x7230], edx   ; count++
0x0063799F  add eax, 0x238                    ; 源指针步进 = 0x238
```

服务端 #5 = u32 **1**，客户端过滤器是 **rec+0x124 <= 1** —— 数值与位置双双吻合，
把"哪个源字段进哪个 rec 偏移"从 CANDIDATE 抬到 **CONFIRMED**。
（另外 0x637950 的 stride 0x238 与元素类大小一致。）

---

## 5. +0x168 / +0x16C 的所有写入点（全镜像分类）

按 disp32 常量扫描（脚本 _018_dispw.py，模式匹配 + 局部解码，跳过 esp/ebp 基址）共 **119** 处
（0x168 共 67 处、0x16C 共 52 处）。0x168/0x16C 是极常见的结构偏移，绝大多数属于**别的类**。
分类如下：

### 5.1 属于本会话记录类（0x238 / vtable 0xDC79F0）—— 只有三类

```
类别                      RVA                                   说明
构造初始化(0)             0x00806BA7 / 0x00806BAD                元素 ctor 0x806B50，ebx=0
网络反序列化(★生产者)     0x00806F6C/0x00806F73 -> 0xB769A0      写入用 [eax]/[eax+4]，
                                                                故不在常量偏移扫描结果里
拷贝/传播                0xBACEB0..0xBACEC2（0x16C 等）         结构整体赋值（copy）
                         0xBAD0EB..0xBAD0FD（0x168+0x16C）      结构整体赋值（copy）
```

0xBACE80 / 0xBACF50 两段是**逐字段结构拷贝**（rep movsd + 逐 dword 搬），
把源对象的 +0x168/+0x16C 原样搬到目标对象 —— 属于 **copy/move chain**，不是原始生产者。

### 5.2 明显无关（unrelated object reuse / 别的类）

```
- 浮点字段：0x41C204、0x461CD0、0x464122、0x464E54、0x464E83、0x470E23、0x4E83AD、
            0x544FB5、0x5452A2、0x548D37、0x600289、0x6002A1、0x6722AA、0x84B8BF、
            0x84DED4、0x8DAD2D、0x8DB075、0x8DB0D8、0x8DB5E2、0x909131、0x909535 …
            （fst/fstp dword，说明这些类的 +0x168 是 float）
- 位域操作：0x849035 (and 0xFFFFFFFC)、0x84907A (and 0xFFFFFFDF)、0xA3560A
- 其它类的整型写：0x5408CB、0x6EC935、0x6E9A54、0x9E335B、0xA18BD2/A18BD8、
            0xA35358/A3535E、0xA35395、0xA35614、0xA6B656、0xA6B735、0xB9A246、
            0xBAD0F1（见上，属 copy）、0x7C4343、0xC2E057、0xAD0B89、0xBACEC2
- lea 取子对象地址：0x63BD78、0x63CBF4、0x63D064、0x63D0AA、0xBAE8B2、0xBB2CF0、
            0x84A264、0xBB4D5A/0xBB4DC3/0xBB4E32、0x6E53CF
```

**结论**：本类唯一**非零**生产者就是 0x806F20 → 0xB769A0；其余非零写点都是"别的类"
或"结构拷贝"。这与 017 实测 (1,0) 有唯一解释相符。

---

## 6. 完整数据流图

```
  服务端 21/5 findSessions 应答
    build_mission_session_object()      codol_crypto.py
      #7  ob.u64(1)   ->  0A 01 00 00 00 00 00 00 00
      (#28 同值；#2 SessionId 走 19 08 08 <8B> blob)
            |
            v  (Lobby TCP -> 客户端会话对象流)
  客户端 会话记录反序列化器  0x00806F20   [元素类 vtable[0]]
      0xB95D70            blob #1 -> rec+0x18 ;  blob #2 -> rec+0x10
                          0xB761E0 -> rec+0x11C / +0x120 / +0x124   (#3/#4/#5)
      0xB76A30 (tag 0x10) #6 map 字符串      -> rec+0x128
      0xB769A0 (tag 0x0A) #7 u64 = 1         -> rec+0x168(低) / rec+0x16C(高)   ★★★
      0xB76A30 (tag 0x10) #8 hostname        -> rec+0x170
            |
            v
  会话记录副本数组  matching+0x7470   [50 × 0x238，ctor 0x62C000 分配]
      写入路径三条（互为替代/补充）：
        0x00637950  filter [src+0x124]<=1, rep movsd 0x8E dwords, count++
                    （唯一直调者 0x6379E0 <- matching vt+0x1C）
        0x00637720  memcpy_s(arr, 0x6EF0, src, n*0x238)   （直调者 0x637930）
        0x0062CD30  matching vt+0x44: memcpy_s(arr[0], 0x6EF0, matching+0x7238, 0x238)
                    并置 [matching+0x7230]=1、[matching+0xE360]=0
      选中索引 [matching+0xE360] = 0
            |
            v
  0x0062F6F0(matching=esi, item=edi=&arr[0])
      matching+0x3A048 = arr[0]+0x168 = 1      (u64 低 32 位)
      matching+0x3A04C = arr[0]+0x16C = 0      (u64 高 32 位)
      matching+0x3A050 = str(arr[0]+0x170)     (hostname)
            |
            v
  0x00632680 accepted 分支判定
      0x6326B9  cmp A_frame, [matching+0x3A048]   A_frame = 0x55667788
      0x6326BF  jne 0x632916                      ★ 不相等 -> 直接退出
      0x6326FB  mov edx, [esi+idx*0x238+0x75D8]   （= arr[idx]+0x168，二次校验）
      0x632702  cmp edx, A_frame / jne 0x632712
```

两套字段的分岔点（本轮核心）：

```
response envelope  0A <u64 senderId>            <- 我们发 SessionId 0x1122334455667788
                      |  客户端帧解析 -> 0x7F1400 拆 LOW/HIGH32 -> A_frame/B_frame
                      v
                  0x6326B9，与下面比较
                      ^
session 对象       0A <u64 #7 = 1>               <- 我们硬编码 1
                      |  0x806F20 -> rec+0x168/+0x16C -> 0x62F6F0 -> matching+0x3A048/+0x3A04C
```

⇒ 两者都是 tag 0x0A 的 u64，但**来自两个不同的对象/字段实例**：
  envelope 的 senderId 与 会话对象的 #7。客户端要求它们**相等**。

---

## 7. 必须回答的问题

### 7.1 (1,0) 的真实语义（对照任务给的 A–G）

```
答案是 B + C/D 的组合，并明确**排除 F**：

MATCHING_A_SOURCE = 21/5 会话对象 字段 #7（tag 0x0A 的 u64）的**低 32 位**
MATCHING_B_SOURCE = 同一 u64 的**高 32 位**

ITEM_168_SEMANTICS = u64 的 bit[31:0] —— 会话/身份引用（session reference / host uid 类）
ITEM_16C_SEMANTICS = u64 的 bit[63:32]

A. 默认初始化值        —— 部分成立：ctor 确实把它清 0（0x806BA7/0x806BAD），
                          但运行时的 1 不是初值，而是被反序列化器覆盖的
B. findSessions 返回数据 —— ★ 成立（来自 21/5 session 对象 #7）
C. session/room ID 低/高字段 —— ★ 成立（它就是一个 u64 引用的高低半）
D. player/session identity —— 与 C 同源；客户端把同一 u64 回显在 mmbook 请求首字段
                          （payload 开头 0A 01 00 00 00 00 00 00 00），
                          说明它是客户端认得的**会话引用**，但**不是**玩家 SessionId
E. playlist/server/region/shard —— 排除：playlist 是 #10（i32），在客户端读序之外
F. response envelope A/B 的另一种字段 —— **明确排除**：两者虽同为 tag 0x0A u64，
                          但生产者不同（信封 senderId vs 会话对象 #7），
                          本轮的错配正说明它们不是同一字段实例
G. 完全不同的状态字段   —— 排除（有完整数据流）
```

### 7.2 findSessions 解析链（任务 §4）

```
response field (#7 u64)
    -> parser / 反序列化器 0x806F20 （tag 0x0A，读 8 字节）
    -> 目标指针 &rec+0x168（0xB769A0 内 mov [eax]/[eax+4]）
    -> item 字段 rec+0x168 / rec+0x16C
    -> 复制进 matching+0x7470 数组（0x637950 / 0x637720 / 0x62CD30）
    -> 0x62F6F0 搬运
    -> matching+0x3A048 / +0x3A04C
```

FINDSESSIONS_RELATION = **CONFIRMED**
理由不是数值吻合，而是四点独立证据同时成立：
  (1) 读取器 0xB769A0 硬编码 tag == 0x0A 且读 8 字节（只能由 u64 字段喂）；
  (2) 读序 blob→blob→u32×3→string→u64→string 与 build_mission_session_object 的
      #1..#8 完全一致；
  (3) 过滤器字段 rec+0x124 与我们的 #5 "u32 1 (Players)" 数值+位置同时吻合，
      且客户端过滤条件是 <=1；
  (4) 全镜像中值为 1 的 tag-0x0A u64 只有 build_mission_session_object 的 #7/#28
      （ROOM_HOST_UID=1000001、envelope senderId=SESSION_ID 都不是 1）。

### 7.3 RESPONSE_AB_RELATION

```
RESPONSE_AB_RELATION = 与 MATCHING_AB **不同源**

  envelope  A = 0x55667788 / B = 0x11223344
    来自 senderId = SESSION_ID = 0x1122334455667788（lobby_server.py L458）
  MATCHING  A = 1 / B = 0
    来自 21/5 会话对象 #7 u64 = 1（codol_crypto.py L542）

  0x6326B9 cmp 0x55667788, 1 -> jne 0x632916      即 017 实测的拒绝路径
```

### 7.4 0x62F6F0 的语义（任务 §5）

```
0x62F6F0 不是 "A/B -> matching"，也不是 "room metadata -> matching"，而是：

  会话记录(rec) -> matching 的"**当前预约/选中会话的关联快照**"

它一次搬三样东西，且都是"当前选中会话记录的第 idx 项"：
  rec+0x168/0x16C（u64 引用） -> matching+0x3A048/0x3A04C
  rec+0x170（hostname 串）    -> matching+0x3A050（0x40 字节）
并先清空 matching+0x3A048/0x3A04C 与 [matching+0x3A050]。
调用它的两个上层（0x62F836 = matching vt+0x3C、0x637930 包装）都在
"选中某个会话 / 提交 booking"的语境里。

注意：0x62F6F0 **没有**调用 0x62F8CB（那是 byte [+0x289]=1，017 实测的"booking 已提交"标记），
两者是同一流程里的相邻但不同的两个标记位。
```

---

## 8. 证据等级

```
CONFIRMED
  0x62F6F0 读 [edi+0x168]/[edi+0x16C] 并与 edi+0x170 字符串成组
  edi = matching + 0x7470 + idx*0x238，idx = [matching+0xE360]
  数组 = 50 × 0x238 = 0x6EF0，ctor 循环 0x62C0CD..0x62C0E6（0x31+1 次）
  元素类 ctor 0x806B50，size 0x238，vtable 0xDC79F0，+0x168/+0x16C 初值 0
  反序列化器 0x806F20 把 rec+0x168 交给 0xB769A0
  0xB769A0 硬编码 tag 0x0A + 8 字节，写 [eax] / [eax+4]（低/高 32 位）
  0xB76A30 硬编码 tag 0x10（字符串）
  客户端过滤器用 rec+0x124，条件 <=1，stride 0x238 的 rep movsd（0x637950）
  服务端 #5 = u32 1；#7 = u64 1；#2 SessionId 走 tag 0x19 blob
  RESPONSE_AB != MATCHING_AB

STRONG_CANDIDATE
  该 rec 流**具体**来自 21/5 findSessions 应答（而非 room / 其它对象）：
  由 (1)~(4) 四点推定，但未逐帧证明"由 21/5 应答直接喂给 0x806F20"

CANDIDATE
  u64 #7 的业务名（host uid / demonwareID / session reference 三者之一）；
  C# 参考未给 #7 命名

UNKNOWN
  类名（RTTI 已剥离，COL 0xDF84AC 解析失败）
  0x7C10EB 注册的三个会话（serv / partySession / searchSession）与 21/5 rec 的对应关系

REFUTED
  "matching+0x3A048 来自 SessionId 低 32 位"（013 的中间假设）
      —— 反证：SessionId 在 #2 走 tag 0x19 blob，写到 rec+0x10；
              A/B 走 tag 0x0A u64，写到 rec+0x168。两者 tag 与目标偏移都不同。
  "matching+0x3A048 来自 response envelope A/B 的同一字段"
      —— 反证：见 §7.3。
```

---

## 9. 最终报告字段汇总

```
RESULT                        = CONFIRMED（完整数据流已建立，§3~§7）

MATCHING_A_SOURCE             = 21/5 会话对象字段 #7（tag 0x0A u64）的低 32 位
                                = 0x00000001
MATCHING_B_SOURCE             = 同一 u64 的高 32 位
                                = 0x00000000

ITEM_168_SEMANTICS            = u64 bit[31:0] —— 会话/身份引用（session reference）
ITEM_16C_SEMANTICS            = u64 bit[63:32]

MATCHING_AB_SOURCE_CHAIN      = build_mission_session_object #7 (0A <u64=1>)
                                  -> 0x806F20 反序列化 (tag 0x0A)
                                  -> 0xB769A0: rec+0x168=低 / rec+0x16C=高
                                  -> matching+0x7470[idx] (0x637950/0x637720/0x62CD30)
                                  -> 0x62F6F0
                                  -> matching+0x3A048 / +0x3A04C
                                （idx = [matching+0xE360] = 0）

FINDSESSIONS_RELATION         = CONFIRMED（§7.2 四点独立证据）

RESPONSE_AB_RELATION          = 不同源：envelope senderId = SESSION_ID
                                (0x55667788 / 0x11223344)
                                vs 会话对象 #7 u64 = 1 (1 / 0)

FIELD_IDENTITY_STATUS         = CONFIRMED
  matching+0x3A048/+0x3A04C ← 会话记录 +0x168/+0x16C ← tag 0x0A u64 ← 21/5 #7
  且 +0x168/+0x16C **不是** SessionId（SessionId 走 tag 0x19 blob → rec+0x10）

A_B_EQUALITY_STATUS           = NOT_EQUAL（CONFIRMED）

NEXT_GATE                     = 见 §10
```

---

## 10. NEXT_GATE（唯一缺口）

按 Hard Stop：已确认 **+0x168/+0x16C ≠ response A/B**，故本报告明确给出

```
RESPONSE_AB != MATCHING_AB
```

并且不再猜 senderId / endian。真正的缺口变成了**服务端两个字段没有对齐**：

```
缺 口  21/5 会话对象 #7 的 u64 值  vs  envelope 的 senderId 值 不一致。

下一步（需要新一轮授权，本轮禁止改 server / accepted response / senderId）：
  1. 决定"以哪一边为准"。两种自洽方案：
     (a) 让 21/5 会话对象的 #7（以及 #28）u64 与 envelope senderId 取同一个值；
     (b) 或让 envelope senderId 取会话对象 #7 的值（=1）。
     建议先做 (a)：只动 findSessions 应答里的两个常量，不动 senderId / SessionId，
     变量最少、可一键回滚。
  2. 静态先确认 #7 与 #28 哪一个才是客户端实际读到的那个 u64
     （客户端读序只取到 #8 附近；若只读一个 u64，#28 在本次读序之外，
      则只需改 #7；这需要再静态展开 0x806F20 后续的读取序列）。
  3. 因 (a) 会改 findSessions 应答，属于"新一轮单变量实验"，必须新开授权与回滚开关；
     本轮不执行。
```

---

## 11. 纪律核对

```
STATIC ONLY                        = 是（未启动游戏 / 未注入 / 未调试）
未改 EXE / DLL                     = 是（只读 EXE 与运行时镜像）
patch / hook / 调试器               = 无
发包 / 改 server / 改 accepted 应答  = 无
改 senderId / SessionId             = 无
改 Lobby protocol                   = 无
重跑 017                            = 否
listener / type-2 / UDP-28960 / endian = 未触碰
ACE / TenProtect bypass             = 无
```

本轮新增只读脚本：

```
DEV-BOOKING\scripts\_018_dispw.py    全镜像 disp 写入点扫描（模式匹配 + 局部解码）
DEV-BOOKING\scripts\_018_schema.py   schema 猜测验证（结论：否定，保留作记录）
```

---

## 12. 成功标准自检

> 问题一：为什么 matching+0x3A048/+0x3A04C 当前是 (1,0)？

```
因为它们是 21/5 会话对象 #7 那个 u64 的两个 32 位半，而我们的
build_mission_session_object 把 #7 硬编码成 1（codol_crypto.py L542: ob.u64(1)  # 7）。
用 u64 = 1 拆半 → A=低32=1、B=高32=0，正是 017 实测的 (1,0)。CONFIRMED。
```

> 问题二：它们与 mmbook accepted response A/B 是否属于同一字段体系？

```
不属于。
  会话对象 #7：tag 0x0A u64，写 rec+0x168/+0x16C，值 1
  envelope 的 A/B：同样最终是 tag 0x0A u64，但那是**信封层的 senderId**，
                  由帧解析器读出，值 = SESSION_ID = 0x1122334455667788
两者只在"都是 u64"这一点上同型，**生产者与载体都不同**，
所以只要服务端不把它们设成同一个值，0x6326B9 就永远不相等。
```

⇒ 本任务完成：FIELD_IDENTITY_STATUS = CONFIRMED；A_B_EQUALITY_STATUS = NOT_EQUAL。




