# PVE-MATCHING-ACCEPTED-DISPATCH-020
# marker=0x02 push 能否到达 0x7F1400 → 0x632680 —— 纯静态结论

```
RESULT_CASE                    = **A**（存在完整静态路径）
MARKER_01_DISPATCH             = 任务应答侧（本条路径未涉及；见 §4.6 的结构性判别）
MARKER_02_DISPATCH             = 服务端推送 → 服务号分派（service = 首个 TLV tag 0x08 的 u32）
MARKER_02_TO_7F1400            = **CONFIRMED**
7F1400_CALLERS                 = 唯一一处间接调用：0xB7CA05 call eax，eax = [manager]+0x68
632680_CALLERS                 = 调用点唯一：0x7F156F call eax（eax = [matching]+0x13C）；指针另存于 0xDC73B0 与 0xDC7850 两个 vtable 槽
632680_UNIQUE_ENTRY            = CONFIRMED（唯一已定位调用点 = 0x7F1400 内；第二槽未定位调用者，见 §4.4）
REQUEST_6_14_DISPATCH          = 出站请求：service=6 / task=14（与入站即时消息不是同一 message class）
ACCEPTED_RESPONSE_DISPATCH     = 入站即时消息：service=21 → mm* 文本分派 → matching mmbook handler
PUSH_AND_TASK_RESPONSE_SAME_PATH = YES（在**消息分派层**同一条服务号分派路径；差异由首个 TLV 的 tag 决定）
NEXT_GATE                      = **0x63268D / additional accepted guard**（CASE A，故按规则进入下一轮）
```

纪律核对（本轮）：
```
未启动游戏 · 未改 server · 未改 client · 未 patch · 未 hook · 未发包
未改 marker / senderId / SessionId / A/B / sequence / service / task
未碰 listener · 未碰 UDP · 未碰 28960 · 未碰 Battle · 未绕过 ACE
全部分析为只读：image_best.bin（base 0x400000，10,899,456 B）
新增只读工具：DEV-BOOKING\scripts\_020_dispatch.py
```

---

## §0 一句话结论

**不存在任何 marker 门。** 客户端在 Lobby TCP 上收到 0x85 帧后，解密得到
`u32 payload_len | marker | payload`；但**分派键不是 marker，而是 payload 的首个 TLV（tag 0x08 = u32 = service）**。
服务号 21 命中跳表第 20 项（0xB83744），进入即时消息处理链：

```
0x7F3800 (大厅 tick) → 0x803830 (netcore) → 0xB838A0 (消息泵)
   → 0xB82A90 (service 跳表) --service=21--> 0xB8309B
      → 0xB7C900 (读 0A u64 / 10 string / 13 blob)
         → [manager]+0x68 = 0x7F1400 (mm* 文本分派)
            → strncmp(msg,"mmbook",6)==0
               → [matching]+0x13C = 0x632680 (统一 mmbook handler)
```

服务端 accepted 用的正是 instant_push_body(..., kind=21)，其信封首字段就是 tag 0x08 + u32 21
—— 与跳表第 20 项**逐字段对上**。

---

## §1 marker 到底是什么（先把线格式钉死）

依据本项目**已被行为验证**的实现（codol_crypto.py，逐字段照抄第三方 C#）：

```
线格式（两端一致）：
    u32 total_len | 0xAB | 0x85 | u32 seq | iv[16] | cipher[n] | hmac8[8]
                    ^^^^                                     ^^^
                    byte[4]                                  byte[5]

明文（解密后）：
    服务端→客户端:  u32 payload_len | marker(byte[4]) | payload      ← marker 在这里
                     marker: 0x01 = 任务应答, 0x02 = 服务端推送
    客户端→服务端:  u32 declared | 0x86 | service | 0x03 | task | payload
```

**结论**：marker 是**解密后明文的第 4 字节**（不是线格式里的 0xAB）。
本轮在全镜像做了穷举搜索，证实客户端**没有任何**形如
`cmp byte ptr [reg+4], 0x01 / 0x02 / 0xAB / 0x85 / 0x86` 的指令（7 种 ModRM 变体全部 0 命中）。
即：marker 可能只被传输层用于「这条消息要不要带 replyId 语义」，
而**真正的业务分派键是 payload 首字段（service）**。

---

## §2 关键对象与 vtable 身份（本轮新确证）

### 2.1 即时消息管理器（manager）
```
0x7F097F   mov dword ptr [0xE39B6E8], 0xDE07A4     ← 安装 vtable
0x7F09EB   mov eax, 0xE39B6E8 ; ret                ← 单例 getter（构造函数尾部返回实例）
0x7F09A3   循环 0x13 次 call 0xB97F20，esi += 0xF8 ← 19 个子对象，每个 0xF8 字节
⇒ 全局单例地址 = 0xE39B6E8；vtable = 0xDE07A4（0xDE07A0 是前置 RTTI/调整指针）
```

校验方法：用已知 vtable 0xDC7274（matching，ctor 0x62C025 安装）做对照，
find_dword(0xDC7274) = 0x62C025 ✔ 方法有效；而 find_dword(0xDE07A0) = 空，
故表的真实基址是 **0xDE07A4**（此前只知「0x7F1400 存于 0xDE080C」）。

### 2.2 manager 注册进 netcore
```
0x803830   netcore 单例 getter（得到 [0x8269774]）
0x80385A   push 0xE39B6E8 ; mov ecx,eax ; call 0xB7A400
0xB7A400   mov dword ptr [ecx+0x4F0], eax          ← ★ netcore+0x4F0 = manager 指针
```

### 2.3 0x7F1400 的槽位
```
0xDE080C - 0xDE07A4 = 0x68  ⇒  **manager vtable +0x68 = 0x7F1400**
（该槽之前的 +0x50/+0x54/+0x5C 都是 0x4F7590「ret 8」空实现）
```

---

## §3 完整数据流（本轮实证）

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ Lobby TCP 0x85 帧到达                                                         │
│   u32 len | AB | 85 | seq | iv[16] | cipher | hmac8                          │
└───────────────────────────────┬──────────────────────────────────────────────┘
                                │  HMAC-SHA1[:8] 校验 + AES-128-CBC 解密
                                ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ 明文  u32 payload_len | marker | payload                                     │
│   marker: 0x01 = 任务应答    0x02 = 服务端推送                                │
│   （本轮穷举：全镜像无 cmp byte [reg+4], {1,2,AB,85,86}，marker 不参与业务分派）│
└───────────────────────────────┬──────────────────────────────────────────────┘
                                │  构造「消息对象」(ByteBuffer 语义)
                                ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ 0x7F3800  大厅 tick / 状态机（状态 [0x84ABA7C]）                              │
│   state 0 → call 0x7F3890                                                    │
│   state 1 → call 0x803830 (netcore)                                          │
│             call [0xCA819C] (加锁)                                            │
│             mov ecx,esi ; call 0xB838A0   ← ★ 消息泵，无 marker 判断           │
│             call [0xCA8190] (解锁)                                            │
│             call 0xB7A670 (归一化 type) → 按 0..4 再跳表 0x7F3878             │
└───────────────────────────────┬──────────────────────────────────────────────┘
                                ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ 0xB838A0 / 0xB829A0 / 0xB82A90   netcore 消息分派                             │
│   0xB82AD4  call 0xB761E0(ecx=消息对象, &v)                                   │
│             └─ 0xB761E0: push 8 ; call 0xB76310(期望 tag 0x08)                │
│                           push 4 ; call 0xB75E80(读 u32)                      │
│             ⇒ **v = payload 首个 TLV 的 u32（tag 必须为 0x08）= service**      │
│   0xB82B23  mov [netcore+0x5C8], v                                            │
│   0xB82B80  mov ecx,[netcore+0x4F0] ; mov edx,[ecx] ; mov edx,[edx+0xF8]      │
│   0xB82B92  call edx            ← manager+0xF8 = 0x7F20E0( v )   （通知）      │
│   0xB82B97  cmp eax, 0x14 → je (service==20 特例)                             │
│   0xB82CCA  call 0xB80D30(netcore+0x20, &v, &obj)  （已注册服务查表）          │
│               └ 命中 → obj->vtable+8(v) ; 未命中 → 落到下面的内建跳表          │
│   0xB82D2C  cmp eax,0x3E9 (1001) / 0xB82D42 dec eax / 0xB82D43 cmp eax,0x4A    │
│   0xB82D4C  jmp dword ptr [eax*4 + 0xB83744]      ← ★ 内建 service 跳表        │
└───────────────────────────────┬──────────────────────────────────────────────┘
                                │  index = service - 1
                                │  service = 21 (0x15) → index 20
                                ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ 0xB8309B  即时消息 case（跳表第 20 项，0xB83744 + 20*4 = 0xB83794）           │
│   0xB830B5  call 0xB7C900                                                     │
└───────────────────────────────┬──────────────────────────────────────────────┘
                                ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ 0xB7C900  即时消息解析（ecx = netcore，arg1 = 消息对象）                       │
│   0xB7C958  call 0xB769A0  → 读 **tag 0x0A u64** → [ebp-0x105C]/[ebp-0x1058]  │
│   0xB7C980  call 0xB76A30  → 读 **tag 0x10 string** → 0x40 字节缓冲            │
│   0xB7C9CF  call 0xB76AF0  → 读 **tag 0x13 blob**   → 0x1000 字节缓冲 + len   │
│   0xB7C9DE  mov ecx,[esi+0x4F0]        ; manager                              │
│   0xB7C9E4  mov eax,[ecx]              ; vtable 0xDE07A4                      │
│   0xB7C9E6  mov eax,[eax+0x68]         ; ★ 0x7F1400                           │
│   0xB7C9E9..0xB7CA02  压 5 参: len, buf4096, str40, u64hi, u64lo             │
│   0xB7CA05  call eax                   ; ★ 唯一调用点                          │
└───────────────────────────────┬──────────────────────────────────────────────┘
                                ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ 0x7F1400  mm* 文本分派器（ret 0x14；ecx=manager；5 参数）                      │
│   0x7F153C  push 6 | push ebx | push "mmbook" | call 0xC3C678  (strncmp)      │
│   0x7F1554  mov ecx,[0x82E13FC]        ; matching 单例                         │
│   0x7F155C  mov eax,[eax+0x13C]        ; ★ 0x632680                            │
│   0x7F156F  call eax   --(A=u64lo, B=u64hi, ptr=str40, msg=buf4096, 15)-->     │
│   其它分支: "mmrsv"(→matching+0x140) / "mminvite"(→[0x82E1404]+0xC) /          │
│             "mmrespondinvitecmd"(→+0x10) / "mmwhisper"                        │
└───────────────────────────────┬──────────────────────────────────────────────┘
                                ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ 0x632680  统一 mmbook handler（ret 0x14）                                     │
│   0x6326B9  cmp A, [matching+0x3A048]   ← 第一守卫（019 已证明必要非充分）     │
│   0x6326C8  cmp B, [matching+0x3A04C]                                         │
│   0x6326DF  strncmp(msg,"mmbook accepted",15)                                 │
│   0x63280B  mov byte [matching+0x288], 1  ← accepted 分支唯一副作用           │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## §4 逐任务结果

### 4.1 任务一：定位 marker（穷举结果）
```
FOUND（语义）: marker = 解密明文 byte[4]；0x01 = 任务应答，0x02 = 服务端推送
NOT FOUND     : 全镜像无 cmp byte ptr [reg+disp], {0x01,0x02,0xAB,0x85,0x86}（disp=4 与 5 的 7 种 ModRM 全 0）
NOT FOUND     : 0xAB / 0x85 也不以立即数形式在固定小位移上与内存比较
解释          : 分派不是「先看 marker 再选处理器」，而是「直接读 payload 首字段（service）」
```

### 4.2 任务二：重建 Lobby message dispatcher
```
入口  0x7F3800（大厅 tick，状态 [0x84ABA7C]）
      state 1 分支里 **无条件** 调 0xB838A0（加锁/解锁包裹），调用点前无任何 marker 判断
分派  0xB82A90 内 jmp dword ptr [eax*4 + 0xB83744]，index = service - 1
      范围：1 .. 0x4B（1..75）；0x3E9(1001) 另有分支；service==0x14(20) 特例
      跳表 0xB83744 共 75 项，逐项对应一个入站服务处理器
      **service=21 → index=20 → 0xB8309B（即时消息）**
      其余示例：6→0xB82DDD、8→0xB82E29、11→0xB82DB3、15→0xB82E9F、16→0xB82EC5、
                17→0xB82F11、18→0xB82F37、19→0xB82F45、22→0xB82F6B
```

### 4.3 任务三：追 0x7F1400
```
真实语义   manager（0xE39B6E8，vtable 0xDE07A4）的虚方法 **+0x68**；
           输入 = (u64低, u64高, 0x40 字符串, 4096 文本缓冲, 长度)；
           行为 = 对文本做 **strncmp 前缀链**（"mmbook"/"mmrsv"/"mminvite"/
           "mmrespondinvitecmd"/"mmwhisper"），命中 "mmbook" 后调 matching 的
           vtable+0x13C = 0x632680，并把 (A,B,str,buf,15) 传下去
调用者     **唯一**：0xB7C9E6 取指针 → 0xB7CA05 call eax（间接，disp=+0x68）
           direct_callers(0x7F1400) = 空；find_dword(0x7F1400) = 仅 0xDE080C（vtable 槽本身）
marker 条件 **无**（0x7F1400 的入参里没有 marker，调用点也没有 marker 判断）
```

### 4.4 任务四：追 0x632680
```
指针存储   dword 引用仅两处：**0xDC73B0**（= 0xDC7274 + 0x13C，matching 类）与
           **0xDC7850**（= 0xDC7714 + 0x13C，**另一个类**的同类槽）
直接调用   direct_callers(0x632680) = 空
已定位调用点 **唯一一处**：0x7F156F（在 0x7F1400 内），经 [matching]+0x13C 间接调用，
           压 5 参 = (A=u64lo, B=u64hi, str40, buf4096, 15) —— 与 018 的 A/B 结论完全一致
⇒ ACCEPTED_HANDLER_UNIQUE_ENTRY = **CONFIRMED（唯一已定位调用者 = 0x7F1400）**
   保留项：第二槽 0xDC7850（vtable 0xDC7714）也装着同一指针，本轮**未定位**其调用者，
   因此严格表述为「唯一已定位调用点」，不是「全镜像唯一可调用点」。
```

### 4.5 任务五：marker=0x02 → 0x7F1400（判定）
```
CASE A 成立。理由三条：
 ① 从 0x7F3800（tick）到 0xB82A90（service 跳表）**全程没有任何 marker 读取或比较**；
 ② 该路径的入口条件只依赖 **payload 首个 TLV 必须带 tag 0x08**（0xB761E0 内部 push 8 并校验）；
 ③ 服务端 accepted 的 instant_push_body(..., kind=21) 首字段恰好是 tag 0x08 + u32 21
    （codol_crypto.py:762-777 明确：08 <u32 service> | 0A <u64 senderId> | 10 <name>0 | 13 08 <len> <data>），
    且后续字段 0A/10/13 与 0xB7C900 的三个读取器（0xB769A0 / 0xB76A30 / 0xB76AF0）**一一对应**。
⇒ PUSH_TO_ACCEPTED_HANDLER = **CONFIRMED**；本轮**不修改 server**。
```

### 4.6 任务六：6/14 request 与 accepted response 是否同一 message class
```
request  客户端→服务端，service=6 / task=14，走「(service,task) 请求」语义（出站）
response 服务端→客户端，marker=0x02 推送，service=21（即时消息），走「service 分派」语义
⇒ **不是同一个 message class**；但二者在**消息分派层同一条路径**上：
   入站消息统一进 0xB82A90 的 service 跳表，差别由 **首个 TLV 的 tag** 体现——
   推送首字段 = tag 0x08（service）；任务应答首字段 = tag 0x0A（replyId）。
   0xB761E0 **只接受 tag 0x08**，因此本跳表天然只处理推送/通知类，
   任务应答由 replyId→在途任务 的另一条路走。
⇒ PUSH_AND_TASK_RESPONSE_SAME_PATH = YES（同一分派层）/ 语义上分属不同 class
```

---

## §5 统计与遗漏

### 5.1 本轮新增工具
```
DEV-BOOKING\scripts\_020_dispatch.py
   refs <addr...>      绝对 dword / E8 / E9 引用
   absrefs <lo> <hi>   值落在 [lo,hi) 的全部 dword 及其所在指令
   idxrefs <lo> <hi>   带比例变址的 [disp+reg*4] 分派
   indd <a> <b>        区间内全部 call [reg+disp] 的位移直方图
   lb <a> <b> <disp>   [reg+disp] 的字节读取
   fstart <addr>       反查函数入口
   sweep <a> <b>       容错线性反汇编（跳过不可解码字节）
   dump / vt / pat / patr / region
```

### 5.2 关键地址表
```
0x7F1400  mm* 文本分派器            = manager vtable +0x68
0x7F20E0  manager vtable +0xF8      = 消息通知（0xB82B92 调用）
0x7F3800  大厅 tick / 状态机
0x7F3890  state 0 子流程
0x803830  netcore 单例 getter
0xB7A400  netcore 注册 manager → [netcore+0x4F0]
0xB7C900  即时消息解析（唯一 caller 0xB830B5）
0xB8309B  service==21 的 case 体
0xB83744  service 跳表（75 项，index = service-1）
0xB838A0  消息泵（由 0x7F3826 调用）
0xB82A90  消息分派主体
0xC3C678  strncmp
0xDC7274  matching vtable 基址；+0x13C = 0x632680；+0x140 = 0x62E9F0
0xDE07A4  manager vtable 基址；+0x68 = 0x7F1400
0xE39B6E8 manager 单例；netcore+0x4F0 指向它
0xE39B6F8 manager 的 19 个子对象数组（每个 0xF8）
```

### 5.3 未做（诚实边界）
```
- **传输层（解密 → 消息对象构造）未逐步追踪**：即 marker 是否在构造消息对象时被用于
  「带/不带 replyId」的选择，本轮未逐指令确认。但**分派层已确认无 marker 门**。
- 第二 vtable 槽 0xDC7850（基址 0xDC7714）的调用者未定位。
- service 跳表的全部 75 项未逐项命名（本轮只展开了必要项与若干示例）。
- 0xB80D30（已注册服务查表）内部未展开。
```

---

## §6 NEXT_GATE（按 CASE A 规则）

```
PUSH_TO_ACCEPTED_HANDLER = CONFIRMED
⇒ 允许进入下一轮：**additional accepted guard**
   候选（按 019 §7 与本案新增证据重排）：
     G1  0x63268D 起、第一守卫之后的指令序列（本轮未展开）
     G2  0x6326DF strncmp("mmbook accepted",15) 之前的前置条件
     G3  [0x76446B0] < 3（0x63269B/0x6326A2）
     G4  [matching+0xE360] >= 0（0x6326AA/0x6326B0）
     G5  调用前 manager+0xF8(0x7F20E0) 的副作用是否改变匹配状态
     G6  0xB80D30 已注册服务查表是否**抢先命中**（命中就不走内建跳表）——
         这是本轮新发现的一条**可能的分流点**，值得优先排除
```

（全文完 · STATIC ONLY · 未做任何修改）
