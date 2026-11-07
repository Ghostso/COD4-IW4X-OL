# BOOKING-CLIENT-CONTRACT-001

> 原 CODOL 客户端**究竟期待什么** Booking 响应？
> 本文只陈述**有客户端侧证据**的结论。无证据一律 `UNKNOWN`。
>
> 分析源：`COD OL\codoMP_client_shipRetail.exe`（7,841,344 B，无壳区）
> 方法：字符串表 + 格式串交叉比对 + 实测帧对照
> 纪律：**未修改 Golden**；静态分析产物置于 `DEV-BOOKING\`

```
GOLDEN-LOBBY-001 = COMPLETE（只读，本次未触碰）
BOOKING_SOURCE   = UNAVAILABLE
分析类型          = 纯静态（第一阶段），未改 Server
```

---

## 0. 一句话结论（先说结论）

**客户端的 `6/14` 是"客户端→服务端"的**预约命令**，
而客户端**自己就带**了期望的响应字符串**：`mmbook accepted`。**

### 证据等级：CONFIRMED

```
0x6B29B0  "mmbook accepted"     ← 客户端 exe 内
0x6B29D4  "mmbook timedout"     ← 客户端 exe 内
0x6B2704  "MM_RESERVE_CMD_REQUEST Accepted"
0x6B2724  "mmbook"
0x6B272C  "%s %d %s %d"
```

**这与我们此前的做法（推 `mmbook accepted`）方向一致**，
但**发送方式**错了 —— 见 §4 的 9/9 失败分析。

---

## 1. 客户端自带的 mmstart 格式串（权威格式表）

在 `0x6B2800` / `0x6B2888` / `0x6B2948` 找到**三个** `mmstart` 格式串，
这是客户端**自己拼装**这些命令的 printf 模板：

### [A] `0x6B2800` —— 剧情/coop 路径（**实测命中**）

```
mmstart sv_resetServer; 2486 %d; 3265 %d; 2489 %d; 2574 0; 2500 %d;
        %s; %s g_difficulty %d; %s; map %s;2654 %s; roomChatChannelID %llu;
```

### [B] `0x6B2888` —— 变体（带 `sv_post_options`）

```
mmstart sv_resetServer; 2486 %d; 3265 %d; 2489 %d; 2574 0; 2500 0;
        %s; %s 2810 %d; sv_post_options %s; map %s;
        roomChatChannelID %llu; %s
```

### [C] `0x6B2948` —— playlist 路径

```
mmstart sv_resetServer; 2486 %d; 3265 %d; 2489 %d; 2574 %d;
        playlist %d; %s %d; roomChatChannelID %llu;
```

### 与实测帧逐字段对照（**CONFIRMED**）

实测（Golden 日志，用户点"剧情"时客户端发出）：

```
mmstart sv_resetServer; 2486 1; 3265 1; 2489 0; 2574 0; 2500 0;
        g_gametype coop;  g_difficulty 0; ;
        map coop_take_mp_fav_tropical;2654 M7-E8S6Client;
        roomChatChannelID 1234605616436508552;
```

| 格式占位 [A] | 实测值 | 语义（推断，标 CANDIDATE） |
|---|---|---|
| `2486 %d` | `1` | UNKNOWN（会话/队伍相关） |
| `3265 %d` | `1` | UNKNOWN |
| `2489 %d` | `0` | UNKNOWN |
| `2500 %d` | `0` | UNKNOWN |
| `%s;` (1) | `g_gametype coop` | gametype |
| `%s` (2) | *(空)* | UNKNOWN（可能为 dvar 前缀） |
| `g_difficulty %d` | `0` | 难度 |
| `%s;` (3) | *(空)* | UNKNOWN |
| `map %s` | `coop_take_mp_fav_tropical` | 地图 |
| `2654 %s` | `M7-E8S6Client` | 客户端标识 |
| `roomChatChannelID %llu` | `1234605616436508552` | 聊天频道 id |

> ⇒ **实测帧 = 格式 [A]**，逐字段吻合。**CONFIRMED**。
> 数字 2486/3265/2489/2500/2654 是**客户端 dvars 编号**，
> 其含义 **UNKNOWN**（不影响响应格式）。

---

## 2. `mmbook` 的完整请求结构（客户端侧证据）

### 2.1 客户端拼装格式

```
0x6B2724  "mmbook"          ← 命令名
0x6B272C  "%s %d %s %d"     ← 参数格式
```

套用后应为：`mmbook <int> <string> <int>`

### 2.2 实测收到的内层 blob（Golden 日志）

```
19 00 00 00 | "mmbook 796 AQAAAAAAAAA= 0"
^^^^^^^^^^^   ^^^^^^ ^^^ ^^^^^^^^^^^^ ^
u32(25)       命令    796  base64     0
```

对照 `%s %d %s %d`：

| 占位 | 实测 | 语义 |
|---|---|---|
| `%s` | `mmbook` | 命令名 |
| `%d` | `796` | **playlist 版本号**（= 我们下发的 `version 796`）**CONFIRMED** |
| `%s` | `AQAAAAAAAAA=` | base64 token（8 字节全 0） |
| `%d` | `0` | UNKNOWN（标志位？） |

### 2.3 外层信封（已实测）

```
0x0A u64      = 1                                 (sender/session id)
0x13 blob(29) = 19 00 00 00 + "mmbook 796 ..."    (内层：裸 u32 长度 + 文本)
```

> 内层是 **typed-mode-disabled** 的裸长度前缀 ——
> 与三方 C# 注释 `0x7F1400 creates its inner stream with typed mode disabled`
> **完全一致**。**CONFIRMED**

---

## 3. ★ 客户端**自己带**了成功/超时标记

这是本轮最重要的发现：

```
0x6B29B0  "mmbook accepted"
0x6B29D4  "mmbook timedout"
0x6B2704  "MM_RESERVE_CMD_REQUEST Accepted"
```

### 含义

客户端在**发起 mmbook 之后**，会进入"等待预约结果"状态，
并**自己认识**两种结果字符串：

| 字符串 | 客户端行为（CANDIDATE） |
|---|---|
| `mmbook accepted` | 停止 retry → 推进到下一阶段 |
| `mmbook timedout` | 报告超时 → 可能重新发起 |

> 也就是说：**服务端不需要发明新格式** ——
> 客户端已经声明它期待 `mmbook accepted` 这个字符串。

### 证据等级

- 字符串**存在** = **CONFIRMED**
- "收到该字符串即停止 retry" = **CANDIDATE**
  （需找到接收侧比较指令才算 CONFIRMED，见 §6 待办）

---

## 4. ★★ 但「字符串对」≠「发送方式对」—— 9/9 失败的真正含义

我们此前已按 `mmbook accepted` 发送，**但 9/9 断连**。
对照本轮静态发现，失败原因**不在字符串本身**，而在：

### 已 REFUTED 的两个假设

| 假设 | 结果 | 证据 |
|---|---|---|
| seq 与客户端号段撞车 | **REFUTED** | 改 `+1000` 偏移后仍 9/9 断连 |
| replyId 需独立计数器 | **REFUTED** | 改独立计数后仍断连（已回退） |

### 仍 UNKNOWN 的关键点

```
① 客户端在**哪个通道**等待 mmbook accepted？
   - 大厅 0x85 push（我们用的）
   - 还是 DedicatedControl / client bridge（另一条链路）
   = UNKNOWN   ← 这是当前最大未知

② 若走 0x85 push，信封的 service 号应为多少？
   我们用了 21（照抄靶场）。PvE 是否为 21 = UNKNOWN

③ "MM_RESERVE_CMD_REQUEST Accepted" 与 "mmbook accepted"
   是同一个东西的两种表述，还是两个不同阶段的标记 = UNKNOWN
```

> 三方 C# 的注释与 `lsg.log` 已证：**它只验证过靶场**，
> 且其日志里**没有 `service=11`** —— 所以 PvE 这条链**没有任何参考**。

---

## 5. 与 28960 的关联（第六阶段目标）

已知（来自 Golden 实测）：

```
6/14 mmbook   ->  我们回 mmbook accepted  ->  客户端断连（9/9）
6/14 mmbook   ->  不回 -> 客户端每 5 秒重试 -> "服务器繁忙"
```

**未观察到**：任何一次 `28960` 收到包。

```
目标链路:
  6/14 response -> session/room -> 28960 endpoint -> NAT 29B -> DTLS

实际观测:
  28960 收包 = 0（全部 31 轮 findSessions / 多次 mmbook 之后）

⇒ "哪个字段把 Booking 与 28960 连接起来" = UNKNOWN
```

**已排除**：session 对象里的地址块**不是**唯一入口 ——
我们已在靶场/PvE session 里都填了 `127.0.0.1:28960`，
客户端**从未**连接它。

---

## 6. 卡点定位（诚实报告）

按指令第九阶段，若找不到 parser 必须明确指出卡在哪里：

```
6/14 SEND CHAIN      = 部分 CONFIRMED
   命令名/参数格式/内层信封/外层信封 均已确认（§2）

6/14 RECEIVE/PARSER  = NOT_LOCATED
   已找到"期望字符串"（mmbook accepted / timedout @0x6B29B0/0x6B29D4）
   但**未定位**比较该字符串的指令，因此：
     · "收到后停止 retry" 仍是 CANDIDATE 而非 CONFIRMED
     · 无法确认客户端在**哪条通道**等待它

RETRY CONDITION      = 部分 CONFIRMED
   实测：不回 -> 每 5 秒重发（已从 Golden 日志量化）

SUCCESS CONDITION    = NOT_LOCATED
   = 卡在"字符串比较指令"这一步

BOOKING → 28960 关联 = UNKNOWN
```

### 具体卡在哪

```
需要定位：引用 0x6B29B0("mmbook accepted") 的代码位置
方法（下一步，仍属静态）：
  1. 在 exe / image_best.bin 里搜 0x006B29B0 的 DWORD 引用
  2. 该引用点即"比较 mmbook accepted"的指令
  3. 顺它往上找调用者 -> 得到"响应由哪条通道进入"
```

---

## 7. 本阶段产物与纪律遵守

```
产物   DEV-BOOKING\BOOKING-CLIENT-CONTRACT-001.md（本文）
       DEV-BOOKING\evidence\（待补：引用点定位结果）

遵守   ✔ 未搜索 ol-mod（已确认不存在）
       ✔ 未修改 Golden（哈希已复核一致）
       ✔ 未猜 booking 帧格式（只陈述客户端自带字符串）
       ✔ 未修改 6/14 response（未动 Server）
       ✔ 未重做 Lobby 工作
       ✔ 未修改 4 个 patch / KDF hook
```

---

## 8. 下一步唯一最短路径（仍静态，不改 Server）

```
① 搜 0x006B29B0 的引用 -> 定位"比较 mmbook accepted"指令
② 顺引用找到响应入口函数 -> 确定它读的是哪条流
   （大厅 0x85 push / DedicatedControl / 其它）
③ 若指向 0x85 push：确认信封 service 号
④ 若指向别的通道：定位该通道的端口与帧格式
⑤ 全部确认后才写 BOOKING_PROTOCOL_SPEC-001.md
⑥ 规格完成且经确认后，才在 DEV-BOOKING 实现

成功标准（唯一）：
  6/14 -> booking accepted -> **客户端停止 retry** -> valid room/session
  -> Battle endpoint -> Battle connection -> handshake
  -> **原 CODOL 客户端进入实际地图** = BATTLE_ENTRY CONFIRMED
```

---

## 9. ★★★ 已定位客户端响应解析器（本卡点解除）

上一节说"卡在字符串比较指令" —— **现已定位并读出**。

### 9.1 定位方法

```
① exe 里 "mmbook accepted" @VA 0x00DC69B0，但**直接引用 0 处**（.tp3 节被加壳）
② 改用**运行期镜像** image_best.bin（VA 0x400000..0xE65000，10,899,456 B）
③ 镜像里搜 0x00DC69B0 的 DWORD 引用 -> 命中 1 处：**VA 0x006326DB**
④ 该处代码**可正常反汇编**（说明运行期已解壳）
```

### 9.2 解析器反汇编（VA 0x006326B6..0x00632736，CONFIRMED）

```asm
006326B6  mov   eax,[ebp+8]
006326B9  cmp   eax,[esi+0x3A048]      ; 比对 字段A
006326BF  jne   0x632916               ; 不等 -> 直接 ret 0x14（拒绝，无副作用）
006326C5  mov   ebx,[ebp+0xC]
006326C8  cmp   ebx,[esi+0x3A04C]      ; 比对 字段B(session/room id)
006326CE  jne   0x632916               ; 不等 -> 拒绝
006326D4  mov   ecx,[ebp+0x14]         ; ecx = 收到的字符串指针
006326D7  push  0xF                    ; 长度 15
006326D9  push  ecx
006326DA  push  0xDC69B0               ; "mmbook accepted"
006326DF  call  0xC3C678               ; ★ 字符串比较（strncmp 语义）
006326E4  add   esp,0xC
006326E7  test  eax,eax
006326E9  jne   0x632876               ; != 0（不相等）-> 走另一分支
006326EF  mov   eax,[esi+0xE360]       ; ★ 相等：读"当前预约索引"
006326F5  imul  eax,eax,0x238          ; 步长 0x238 的数组
006326FB  mov   edx,[eax+esi+0x75D8]   ; 数组项 +0x00
00632702  cmp   edx,[ebp+8]            ; 与 字段A 再比一次
00632705  jne   0x632712
00632707  mov   eax,[eax+esi+0x75DC]   ; 数组项 +0x04
0063270E  cmp   eax,ebx
00632710  je    0x632736               ; ★ 全部命中 -> 成功分支
00632712  call  0x62F6C0               ; 否则走复位/重试
```

### 9.3 成功分支（VA 0x00632736，CONFIRMED）

```asm
00632736  movzx eax,byte [esi+0x105FC]
00632745  mov   dword [esp+0x28],1      ; ★ 状态置 1（"预约成功"）
0063274D  mov   dword [esp+0x24],0xDC74F8   ; 另一个常量字符串
00632761  call  0x771320                ; Scaleform/事件投递
00632770  call  0x631E90
00632776  call  0x632070
0063278B  push  ecx / push eax
0063278F  call  edx                      ; 虚调用（[esi]+0x150）
00632791  call  0x631E50
00632798  je    0x6327C5
006327A1  call  0x811340                 ; 继续推进
```

### 9.4 判据的精确形式（这是最有价值的结论）

> **客户端接受 `mmbook accepted` 的**充分条件**（全部满足）：**

```
① 收到的字符串 == "mmbook accepted"（长度 15，strncmp 语义，0xC3C678）
② 该响应携带的「字段A」 == [esi+0x3A048]
③ 该响应携带的「字段B」 == [esi+0x3A04C]
④ 预约数组 [esi+0xE360] 指向的项，其 +0x00 == 字段A 且 +0x04 == 字段B
   （步长 0x238）
→ 满足则 [esp+0x28]=1（成功），走 0x632736 推进
→ 不满足则跳 0x632876 或 0x632712（复位/重试）
```

### 9.5 证据等级更新

| 项 | 之前 | 现在 |
|---|---|---|
| 期望字符串 | CANDIDATE | **CONFIRMED**（`0xDC69B0`，长度 15，被 `0xC3C678` 比较） |
| 比较指令位置 | NOT_LOCATED | **CONFIRMED：VA 0x006326DF** |
| 成功分支 | UNKNOWN | **CONFIRMED：VA 0x00632736，置 [esp+0x28]=1** |
| 失败分支 | UNKNOWN | **CONFIRMED：VA 0x00632876 / 0x00632712** |
| 是否需匹配 id | UNKNOWN | **CONFIRMED：需 `[esi+0x3A048]` 与 `[esi+0x3A04C]`** |

### 9.6 仍然 UNKNOWN

```
① 该解析器**被谁调用**（= 响应从哪条通道进来）
   - 大厅 0x85 push？
   - DedicatedControl / client bridge？
   = UNKNOWN   ← 下一步要解这里

② 响应里「字段A/字段B」的**取值来源**
   （是客户端自己发出去过的？还是服务端先下发的？）

③ 该比较是**大小写敏感**、是否含结尾 \0（长度给的是 0xF=15，
   而 "mmbook accepted" 恰好 15 字符 —— 说明**不含 \0**）
```

### 9.7 同时定位到的其它引用点（备用证据）

| 字符串 | VA | 引用点 | 备注 |
|---|---|---|---|
| `mmbook accepted` | `0x00DC69B0` | `0x006326DB` | ★ 本节解析器 |
| `mmbook timedout` | `0x00DC69D4` | `0x00632FB2` | 超时分支（待读） |
| `mmbook` | `0x00DC6724` | `0x0062F7E1` `0x007F1540` | 发送侧构造 |
| `MM_RESERVE_CMD_REQUEST Accepted` | `0x00DC6704` | `0x0062EC72` | 另一处状态标记（待读） |

> 下一步最短路径：读 `0x00632690` **函数的入口**（往上找 `push ebp; mov ebp,esp`
> 与 `ret 0x14` 配对），确认参数 3 的语义与调用者 ——
> 调用者即"响应从哪来"的答案。

---

## 10. ★★★ 解析器归属已确定：它是 C++ 虚函数（vtable 槽）

### 10.1 函数入口

```
VA 0x00632680   push ebp / mov ebp,esp / and esp,0xFFFFFFF8
                sub esp,0x24 / push ebx,esi,edi
                mov esi, ecx          ← ★ ecx = this（**thiscall 成员函数**）
                ...
                0x0063291C  ret 0x14  ← 5 个栈参数
```

**参数个数 = 5**（`ret 0x14`），其中：

```
[ebp+8]   = 字段A（与 [esi+0x3A048] 比对）
[ebp+0xC] = 字段B（与 [esi+0x3A04C] 比对）
[ebp+0x14]= 收到的**字符串指针**（与 "mmbook accepted" 比对，长度 0xF）
```

### 10.2 它是虚函数 —— 定位到 vtable 槽位

镜像里搜函数地址 `0x00632680` 的 DWORD 引用，命中 **2 处**：

```
0x00DC73B0
0x00DC7850
```

回溯 vtable 起点 `0x00DC7270`，本函数是 **第 81 槽（+0x140）**。

### 10.3 关键：相邻槽 +0x13C 是**超时**处理

在 `VA 0x00632FB2` 找到 `mmbook timedout` 的引用，其代码为：

```asm
00632FA7  mov  edx,[ebx+0x3A04C]
00632FAD  mov  eax,[ebx]
00632FAF  push 0xF                    ; 长度 15
00632FB1  push 0xDC69D4               ; "mmbook timedout"
00632FB6  lea  ecx,[ebx+0x3A050]
00632FBC  push ecx
00632FBD  mov  ecx,[ebx+0x3A048]
00632FC3  push edx
00632FC4  mov  edx,[eax+0x13C]        ; ★ vtable 槽 +0x13C
00632FCA  push ecx
00632FCB  mov  ecx,ebx
00632FCD  call edx                    ; 调用之
```

**⇒ 结论（CONFIRMED）：这套 vtable 就是"预约/匹配结果通知"接口：**

| vtable 槽 | 函数 | 语义 |
|---|---|---|
| `+0x13C` | （未定位入口） | 收 **`mmbook timedout`** 通知 |
| `+0x140` | **`0x00632680`** | 收 **`mmbook accepted`** 通知（本解析器） |

两者**参数布局相同**（字段A / 字段B / 字符串），说明是同一个接口的两个事件。

### 10.4 对象布局（this 指针偏移，CONFIRMED）

```
esi = this
  +0x0278  byte   守卫（必须 != 0，否则拒绝）
  +0x0E360 dword  当前预约索引（< 0 则拒绝）
  +0x03A048 dword 字段A（期望的 id）
  +0x03A04C dword 字段B（期望的 id）
  +0x03A050 ...   定长缓冲（被 0xC42DE0 清零，push 0x40 = 64 字节）
  +0x03A090 ...   子对象（0xB75D90 析构 / 0xB75DA0 取值）
  +0x03A098 dword  计数
  +0x03A09C dword  计数上限
  +0x03A0A8 dword* 数组指针
  +0x075D8 ...     预约数组（步长 0x238），项 +0x00=字段A, +0x04=字段B
  +0x105D8 ...     某 id（进 mmstart 格式串）
  +0x105FC byte    某标志（进 mmstart 格式串）
```

### 10.5 证据等级更新

| 项 | 等级 |
|---|---|
| 解析器入口 `0x00632680`（thiscall，5 参数，`ret 0x14`） | **CONFIRMED** |
| 它是 vtable 槽 `+0x140` | **CONFIRMED**（2 处 vtable 引用） |
| 相邻槽 `+0x13C` 处理 `mmbook timedout` | **CONFIRMED** |
| 接受条件 = 字符串 + 字段A + 字段B + 数组项匹配 | **CONFIRMED** |
| 成功时置 `[esp+0x28]=1` 并推进 | **CONFIRMED** |

### 10.6 仍 UNKNOWN（下一步）

```
① 该 vtable 属于哪个**接口/对象**（类型名未从 RTTI 取到 —— RTTI 区主要是 CEF）
② 谁**调用** +0x140 槽（= 响应从哪条通道进来）
   - 需要找 `mov edx,[reg+0x140]; call edx` 形式的指令
③ 「字段A / 字段B」的**取值来源**
   （候选人：mmbook 请求里那个 `AQAAAAAAAAA=` 解出的 8 字节？还是别的）
④ 是否**必须先由服务端下发**字段A/字段B，客户端才能对上
   （`[esi+0x3A048]/[0x3A04C]` 何时被写）
```

> **下一步唯一最短路径**：在镜像里搜 `+0x140` 与 `+0x13C` 的
> 虚调用点（`FF 92 40 01 00 00` / `FF 92 3C 01 00 00`），
> 命中处即"响应入口"，从而确定通道与端口。

---

## 11. ★★★ 字段A/字段B 由客户端**自己**产生并外发（关键）

### 11.1 写入点扫描结果（CONFIRMED）

在镜像里搜 `disp32 = 0x3A048`（字段A）与 `0x3A04C`（字段B）的全部访问：

```
0x3A048  共 8 处
    0062C282  清零（复位路径）
    0062F6C5  mov [esi+0x3A048], eax   ← eax=0，清零
    0062F717  mov [esi+0x3A048], ebx   ← ebx=0，清零
    0062F809  mov ecx, [esi+0x3A048]   ← **读**（见 11.2）
    006326BB  （解析器：读，比对）
    006328F7  mov [esi+0x3A048], edi   ← edi=0，清零（拒绝路径）
    00632FBE  （timeout 路径：读）

0x3A04C  同理，全部是"读"或"写 0"
```

**⇒ 在本模块内，字段A/字段B 只被「清零」和「读取」，从未被写入具体值。**

### 11.2 但 `0x62F7E0` 把**它们**塞进了 mmbook 请求（CONFIRMED）

`0x62F780..0x62F81B` 是 **mmbook 请求构造**：

```asm
0062F7C7  mov  dword [esp+0x14], eax
0062F7CB  call 0xB74410                 ; 取某 8 字节（疑为 token）
0062F7E0  push 0xDC6724                 ; "mmbook"
0062F7E5  push 0xDC672C                 ; "%s %d %s %d"
0062F7EA  call 0x774980                 ; ★ sprintf：拼出 "mmbook <d> <s> <d>"
...
0062F7F9  mov  ecx,[esi+0x3A04C]        ; 字段B
0062F801  mov  edx,[edx+0x150]          ; vtable +0x150
0062F808  push ecx
0062F809  mov  ecx,[esi+0x3A048]        ; 字段A
0062F80F  push ecx
0062F810  push eax                      ; 刚拼好的字符串
0062F81B  call edx                      ; ★ 外发（虚调用）
```

### 11.3 由此得到的关键推论

```
字段A / 字段B 是**客户端侧**的标识符：
  · 客户端在**发送 mmbook 之前**就把它们读出来（0x62F7F9/0x62F809）
  · 并**随请求一起发出去**（push 给 vtable+0x150）
  · 解析响应时又要求**响应里带回同样的两个值**（0x6326B9/0x6326C8）

⇒ 这是"**请求-应答配对号（correlation id）**"的典型模式。
   服务端只要**原样回显**客户端发来的这两个值即可通过 ①③ 两项检查。
```

> 注意：本模块只**读**它们，说明其**赋值发生在本模块之外**
> （在发送前的更上游，或另一个模块）。`[esi+0xE360]` 那个"预约索引"
> 同理。**它们的产生者 = UNKNOWN（下一步）**。

### 11.4 客户端契约总表（本阶段最终形态）

| 字段 | 地址/函数 | 类型 | 长度 | 来源 | 用途 | 证据 |
|---|---|---|---|---|---|---|
| 命令名 | `0xDC6724` | ASCIIZ | 6 | 客户端常量 | `mmbook` | CONFIRMED |
| 参数格式 | `0xDC672C` | ASCIIZ | 9 | 客户端常量 | `%s %d %s %d` | CONFIRMED |
| playlist 版本 | 实测帧 | u32→文本 | — | 客户端 | `796` | CONFIRMED |
| token | 实测帧 | base64 | 12 | 客户端（`0xB74410` 产出 8B） | `AQAAAAAAAAA=` | CONFIRMED |
| 第4参数 | 实测帧 | int | — | 客户端 | `0` | CANDIDATE |
| **字段A** | `[this+0x3A048]` | dword | 4 | **客户端内部**（本模块只读） | **请求-应答配对** | CONFIRMED |
| **字段B** | `[this+0x3A04C]` | dword | 4 | **客户端内部**（本模块只读） | **请求-应答配对** | CONFIRMED |
| 期望响应串 | `0xDC69B0` | ASCII | **15** | 客户端常量 | `mmbook accepted` | CONFIRMED |
| 超时串 | `0xDC69D4` | ASCII | 15 | 客户端常量 | `mmbook timedout` | CONFIRMED |
| 接受判定 | `0x6326DF` → `0xC3C678` | strncmp | 15 | 代码 | 响应必须等于期望串 | CONFIRMED |
| 成功副作用 | `0x632745` | dword | 4 | 代码 | `[esp+0x28]=1` | CONFIRMED |
| 拒绝出口 | `0x632916` | — | — | 代码 | `ret 0x14`（无副作用） | CONFIRMED |
| 外发接口 | vtable `+0x150` | 虚函数 | — | 代码 | 把拼好的字符串发出去 | CONFIRMED |
| 响应接口 | vtable `+0x140` / `+0x13C` | 虚函数 | — | 代码 | 收到 accepted / timedout | CONFIRMED |

---

## 12. 仍然未知（精确卡点清单）

```
① 谁的代码**给 [this+0x3A048]/[0x3A04C] 赋非零值**
   （本模块内只有清零；赋值者 = 上游/其它模块）→ UNKNOWN

② vtable+0x140 / +0x13C 的**调用者**
   （= 响应从哪条通道进来）→ UNKNOWN
   方法：搜 `FF 9x 40 01 00 00` 未命中 → 可能是**寄存器间接**
         （`mov edx,[eax+0x140]; call edx` 已被 timeout 路径证实存在）
         下一步搜 `8B 9x 40 01 00 00` / `8B 90 40 01 00 00` 再顺藤摸瓜

③ 外层信封走**哪条连接**：大厅 0x85 push？还是 DedicatedControl？→ UNKNOWN

④ 28960 endpoint 由**哪个字段**携带 → UNKNOWN
   （已确认：session 对象里的地址块**不是**唯一入口）

⑤ 第4参数 `0` 的语义 → CANDIDATE（很可能为 0 即可）
```

### 结论（回答本阶段的核心问题）

> **原始 CODOL 客户端期待的 Booking response 是：**
> 一个**长度恰为 15 的字符串 `mmbook accepted`**，
> 并且**携带客户端在 mmbook 请求里发出去的那两个 id（字段A/字段B）**，
> 使解析器（`0x632680`，vtable `+0x140`）第 ①③ 项检查通过。
>
> **停止 retry 的条件** = 上述两项 + 预约数组项匹配 → `[esp+0x28]=1`。
>
> **无法回答的部分** = 这两项**走哪条通道**送达
> （`vtable+0x140` 的调用者未被定位）。
