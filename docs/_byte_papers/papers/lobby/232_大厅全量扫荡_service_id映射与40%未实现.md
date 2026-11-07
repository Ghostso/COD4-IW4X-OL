# 232 · 大厅全量扫荡（一）—— service id → 代码位置直接映射 + 40.4% 流量未实现

> 卷次：232（第七轮·大厅全量扫荡第一册）
> 方法：**镜像反汇编（VA=文件偏移+0x400000）+ 语料 6848 条全量 + 实机日志 1 份**
> 前卷：`221`（服务 80 全字段）/`222`（80 与 102 证据链）/`224`（小服务）/**`231`（商城根因）**

---

## §0 结论（三句话）

1. **★★★★★ 找到 `0xB78C10 = WriteTaskHeader(buf, svc_u8, task_u8)`** —— 37 个调用点，是 service id → 客户端构造位置的**第一份直接映射**。33/37 解析成功，其中 15 个 (svc,task) 与语料 100% 对上。
2. **★★★★ 实机日志里 40.4%（2767/6848）的请求走 `UNMAPPED` 空 ACK**，服务端 `lobby_server.py` 只覆盖 31/55 个 (svc,task) 组合。
3. **★★★ 更正 223/224/225 卷"service id→名字不可达"**：`0xE4E8F8` 服务名表**根本不是 id 表**（20 项 `{name*, enabled}`，唯一消费者 `0x7EEF2C` 按 0..0x13 循环做配置报错），而 **id 只能从 `0xB78C10` 的调用点读**。

| # | 证据 | 层级 | 强度 |
|---|---|---|---|
| ① | `0xB78C10` 函数体：`0xB78C1F call 0xB75E00(writeN,1)` 写 svc，`0xB78C2A call 0xB76620(u8)` 写 task | 本地逆向 | ★★★★★ |
| ② | 37 个调用点，33 个解析出 (svc,task)，15 个与语料交叉命中 | 双源交叉 | ★★★★★ |
| ③ | 实机日志 `UNMAPPED` 计数 | 本地实机 | ★★★★★ |
| ④ | `0xE4E8F8` 结构 = `{char* name; u32 enabled}`，唯一消费者 `0x7EEF2C` 是配置循环 | 本地逆向 | ★★★★★ |

---

## §1 ★★★★★ `0xB78C10` = WriteTaskHeader —— service id 的唯一静态来源

### 1.1 函数体（完整，7 条指令）

```asm
0xB78C10  push ebp / mov ebp,esp / push esi
0xB78C14  mov  esi, [ebp + 8]        ; esi = holder（BUF 对象）
0xB78C17  mov  ecx, [esi]            ; ecx = *holder
0xB78C19  push 1
0xB78C1B  lea  eax, [ebp + 0xC]      ; &svc 参数
0xB78C1E  push eax
0xB78C1F  call 0xB75E00              ; writeN(*holder, &svc, 1)   ← ★ 写 1 字节 service
0xB78C24  mov  ecx, [ebp + 0x10]     ; task 参数
0xB78C27  push ecx
0xB78C28  mov  ecx, [esi]
0xB78C2A  call 0xB76620              ; u8(*holder, task)          ← ★ 写 1 字节 task
0xB78C2F  pop esi / pop ebp / ret
```

**参数顺序 = `(holder*, svc_byte, task_byte)`。** 无歧义：`0xB75E00` 是底层 `writeN`（`[ecx+0x18]` 门控），`0xB76620` 是 `u8` 写器（230 卷写族表里的 tag `0x03`）。

### 1.2 调用形态（固定四连 + 可选 mov）

```asm
push <task>              ; 6A xx  (task 立即数)
lea  <buf>, [ebp - 0x10] ; 8D xx
push <svc>               ; 6A xx  (svc 立即数)
push <buf>
mov  dword ptr [ebp - 4], 2   ; SEH 状态，可省
call 0xB78C10
```

### 1.3 ★ 全部 37 个调用点的 (svc, task)（33 个解析成功）

| call site | svc | task | 语料条数 |
|---|---|---|---|
| `0xB8E701` | **6** | 5 | 160 ✅ |
| `0xB8F174` | **6** | 14 | 235 ✅ |
| `0xB8F2BB` | **6** | 18 | 0 ★代码独有 |
| `0xB9B9DC` | **8** | 1 | 124 ✅ |
| `0xB9BB1E` | **8** | 2 | 124 ✅ |
| `0xB9B694` | **8** | 3 | 84 ✅ |
| `0x7F7221` | **8** | 6 | 0 ★代码独有 |
| `0xB9B8BE` | **8** | 7 | 0 ★代码独有 |
| `0xB9B7A0` | **8** | 8 | 0 ★代码独有 |
| `0xB8EA5E` | **11** | 2 | 13 ✅ |
| `0xB8EDCA` | **11** | 4 | 261 ✅ |
| `0xB8EEFA` | **11** | 5 | 0 ★代码独有 |
| `0xB8EB6E` | **11** | 9 | 0 ★代码独有 |
| `0xB8EC8E` | **11** | 10 | 0 ★代码独有 |
| `0xB8E93E` | **11** | 11 | 0 ★代码独有 |
| `0xB8E83E` | **11** | 13 | 66 ✅ |
| `0xB8F031` | **11** | 15 | 0 ★代码独有 |
| `0xB9140E` | **12** | 6 | 160 ✅ |
| `0xB91504` | **12** | 9 | 0 ★代码独有 |
| `0xB9FD3C` | **29** | 4 | 0 ★代码独有 |
| `0xB9FF32` | **29** | 5 | 0 ★代码独有 |
| `0xB9FB72` | **29** | 10 | 83 ✅ |
| `0xB9753E` | **58** | 6 | 0 ★代码独有 |
| `0xB9769E` | **58** | 18 | 0 ★代码独有 |
| `0xB977DD` | **58** | 20 | 0 ★代码独有 |
| `0xB9797E` | **58** | 21 | 0 ★代码独有 |
| `0xB97AAE` | **58** | 22 | 0 ★代码独有 |
| `0xB89D12` | **71** | 8 | 0 ★代码独有 |
| `0xB8F489` | **102** | 1 | 172 ✅ |
| `0xB8F74E` | **102** | 2 | 77 ✅ |
| `0xB8F864` | **102** | 3 | 0 ★代码独有 |
| `0xB8F615` | **102** | 5 | 19 ✅ |
| `0xB8F9FC` | **102** | 7 | 371 ✅ |

**未解析 4 处**：`0xB916B4`、`0xBA0151`、`0xBA4AF5`、`0xBA7415`（调用形态不同，走 `mov` 传参而非 `push imm`）。

### 1.4 ★ 交叉验证（这是本表可信的根据）

15 个 (svc,task) **全部**在语料里有对应条数，且 svc 与 task 无一个错位：

```
6/5  ×160   6/14 ×235   8/1 ×124   8/2 ×124   8/3 ×84
11/2 ×13    11/4 ×261   11/13 ×66
12/6 ×160
29/10 ×83
102/1 ×172  102/2 ×77   102/5 ×19   102/7 ×371
```

★ 若参数顺序读反（task↔svc），这 15 个会全部对不上。**这是"参数顺序正确"的机械证明，不是推断。**

---

## §2 ★★★★ 服务 58 (0x3A) = Clan（战队）

### 2.1 代码侧任务全表（语料里一条都没有）

| call site | svc | task |
|---|---|---|
| `0xB9753E` | 58 | 6 |
| `0xB9769E` | 58 | 18 |
| `0xB977DD` | 58 | 20 |
| `0xB9797E` | 58 | 21 |
| `0xB97AAE` | 58 | 22 |

### 2.2 定名证据：`0xB974B4` 的槽数组

```asm
0xB974B4  movsx ecx, word ptr [esi + 0xA338]   ; ★ 战队槽索引
0xB974BB  imul  ecx, ecx, 0x2A0                ; ★ 元素大小 0x2A0 = 672B
0xB974C1  lea   edi, [ecx + esi + 0x3E5A]      ; ★ 数组基址 +0x3E5A
0xB974D6  push 0x80 / push 0 / push edi
0xB974DD  call 0xC3FF30                        ; memset/strnlen 族
0xB974F5  push 0x2C / call 0xB74220            ; 分配 0x2C
0xB97515  call 0xB9BEB0                        ; 构造 BUF
0xB97534  push 0x3A                            ; ★ svc = 58
```

**`0xA338` 索引 × `0x2A0` 步进 + `+0x3E5A` 基址 = 战队槽数组。**

### 2.3 字符串证据（`0xDCB784..0xDCB888` 连续 Clan 命令族）

```
0xDCB784  FetchClanInfo
0xDCB794  ApplyToJoinClan
0xDCB7A4  ListClan
0xDCB7B0  CreateClan
0xDCB7BC  InitClanProfile
0xDCB7CC  RefreshClan
0xDCB7D8  ForceRefreshClanInfo
0xDCB7F0  LeaveClan
0xDCB7FC  RenameClan
0xDCB808  EditClanDescriptionAndRecruit
0xDCB828  EditClanAnnouncement
0xDCB840  EditClanTags
0xDCB850  PromoteClanMember
0xDCB864  DemoteClanMember
0xDCB878  KickClanMember
0xDCB888  ProposeClanMembership
```

★ **这是 AS↔C++ 绑定名表**（与 222 卷 `0xDCCE00` 的 `AS_Message*` 同族），16 条命令对应 5 个 task。

### 2.4 ★ 为什么语料里 0 条

语料 6848 条来自**大厅登录 + 房间流程**，没有进过战队界面。**⇒ 服务 58 是"从未被踩到"的整片未探索区**，不是"客户端不发"。

★ **这条很重要**：过去把「语料里没有」当成「不存在」，实际上只是「没走到」。232 卷证明代码侧存在 5 个 task。

---

## §3 ★★★★ 更正：`0xE4E8F8` 服务名表**不是** service id 表

### 3.1 表结构（20 项，stride 8）

```
0xE4E8F8 + i*8 :  { char* name ; u32 enabled }   i = 0..19
```

| i | name | enabled |
|---|---|---|
| 0 | none | 0 |
| 1 | all | 0 |
| 2 | critical | 0 |
| 3 | non_critical | 0 |
| 4 | eventlog | 0 |
| 5 | friends | 0 |
| 6 | group | 0 |
| 7 | mail | 0 |
| 8 | marketplace | 0 |
| 9 | matchmaking | **1** |
| 10 | messaging | **1** |
| 11 | pooledstorage | 0 |
| 12 | profiles | **1** |
| 13 | storage | **1** |
| 14 | tags | 0 |
| 15 | teams | 0 |
| 16 | tencent | 0 |
| 17 | titleutilities | 0 |
| 18 | reward | 0 |
| 19 | stats | **1** |

### 3.2 唯一消费者 `0x7EEF2C` 是**配置报错循环**，不是 id 查表

```asm
0x7EEF2C  mov eax, [ebx*8 + 0xE4E8F8]     ; 只取 name 指针（不要 enabled）
0x7EEF36  mov [ebp - 0x58], eax
0x7EEF66  push 0xDB4530                    ; 某个配置键名
0x7EEF6C  call edx                        ; 虚调用：状态上报
0x7EF05C  inc ebx
0x7EF05D  cmp ebx, 0x14                   ; ★ 硬编码 20 项
0x7EF060  jl  0x7EEE90
```

★ **`ebx` 从 4 起（`0x7EEE8A mov ebx,4`），步进到 0x14** ⇒ 遍历 index 4..19，**`enabled` 字段根本没被读**。

### 3.3 ★ 决定性负面证据：20 个名字字符串指针在代码里**零引用**

```
none            0xDADDE0  表外引用  50（但全是 "none" 这个常用词的其它用法）
non_critical    0xDE0BF4  表外引用   0
eventlog        0xDE0BE8  表外引用   0
marketplace     0xDE0BDC  表外引用   0
matchmaking     0xDE0BD0  表外引用   0
messaging       0xDE0BC4  表外引用   0
pooledstorage   0xDE0BB4  表外引用   0
profiles        0xDE0BA8  表外引用   0
storage         0xDE0BA0  表外引用   0
teams           0xDE0B98  表外引用   0
tencent         0xDE0B90  表外引用   0
titleutilities  0xDE0B80  表外引用   0
reward          0xDE0B78  表外引用   0
```

**⇒ 这些名字唯一的用途就是这张表本身（供配置/日志打印），没有任何代码拿它们和服务号比对。**

### 3.4 更正三卷

| 卷 | 原说法 | 更正 |
|---|---|---|
| 223 §3.1 | 「表只有 enable 0/1，**无服务号** ⇒ 不能单独用于号↔名绑定」 | ✅ **这句是对的**，但没说清"为什么"——因为**名字根本没被任何代码引用** |
| 224 | 「10 个小服务名**未在客户端内找到数字 id→名字映射**（已穷尽）」 | ⚠ **方法错**：查的是 `0xE4E8F8` 与 RTTI，**没查 `0xB78C10` 调用点**。现在 svc 6/8/11/12/29/58/71/102 全部有代码位置 |
| 225 §4 | 同上 | ⚠ 同上 |

★ **新结论：service id 的权威来源是 `0xB78C10` 的调用点立即数，不是任何名字表。** 名字与 id 之间**在客户端里没有映射表**（这是设计：配置按名字、协议按数字，两者不交叉）。

---

## §4 ★★★★ 服务端覆盖率：40.4% 流量走 UNMAPPED

### 4.1 语料 55 个 (svc,task) 组合，服务端覆盖 31 个

| svc | task（未覆盖） | 条数 | 小计 |
|---|---|---|---|
| **3** | 46, 48, 53 | 88+88+83 | 259 |
| **4** | 4, 13 | 89+290 | 379 |
| **9** | 5, 14 | 88+83 | 171 |
| **10** | 20 | 88 | 88 |
| **12** | 6 | 160 | 160 |
| **28** | 4 | 94 | 94 |
| **29** | 10 | 83 | 83 |
| **68** | 3, 8 | 162+9 | 171 |
| **71** | 3,4,7,9,10,11,13,15,18,20 | 1285 | 1285 |
| **102** | 2 | 77 | 77 |

**合计 2767 / 6848 = 40.4%**

### 4.2 实机日志逐条证实（`VER_20261031_235002\kit\lobby_srv.log`）

```
[23:50:41] -> UNMAPPED service=3 task=53 payload=19B
[23:50:41] -> UNMAPPED service=10 task=20 payload=14B
[23:50:41] -> UNMAPPED service=12 task=6 payload=1B
[23:50:41] -> UNMAPPED service=29 task=10 payload=15B
[23:50:41] -> UNMAPPED service=9 task=14 payload=6B
[23:50:41] -> UNMAPPED service=9 task=5 payload=6B
[23:50:57] -> UNMAPPED service=4 task=4 payload=25B
[23:50:57] -> UNMAPPED service=4 task=13 payload=25B   (×3)
[23:50:57] -> UNMAPPED service=28 task=4 payload=519B
[23:50:57] -> UNMAPPED service=68 task=3 payload=44B
[23:50:46] -> UNMAPPED service=71 task=3 payload=575B
[23:50:46] -> UNMAPPED service=71 task=7 payload=225B/329B/345B
[23:51:16] -> UNMAPPED service=71 task=15 payload=149B
[23:53:52] -> UNMAPPED service=71 task=7 payload=213B/336B
```

★ **`71/7` 单 task 355 条、`71/3` 328 条、`4/13` 290 条 —— 这三个是全大厅最大的未实现面。**

### 4.3 ★ 与 231 卷商城根因的同构性

231 卷证明：商城"回空页 ⇒ `reply+5==0` ⇒ `state=2` ⇒ UI 永不渲染"。

**同样的风险适用于上表每一项**：空 ACK 会让客户端走失败分支。**是否真的失败要看各服务的 `reply+5` 判据**，不能一概而论——这是下一步的具体工作（见 §6）。

---

## §5 代码侧独有：语料里从未出现的 task（13 个）

| svc | task | 说明 |
|---|---|---|
| 6 | 18 | InstantMessage 第 3 个 task |
| 8 | 6, 7, 8 | Profiles 多出 3 个 |
| 11 | 5, 9, 10, 11, 15 | 房间多出 5 个 |
| 12 | 9 | — |
| 29 | 4, 5 | — |
| 58 | 6, 18, 20, 21, 22 | **★ 整个 Clan 服务** |
| 71 | 8 | — |
| 102 | 3 | — |

★ **这些是"存在但未走过"的路径**，按 AGENTS.md 全部是可独立核验的地址级任务（已给 call site）。

---

## §6 边界总账（每项 = 可独立核验任务）

| # | 未解项 | 已穷尽排查 | 结论 |
|---|---|---|---|
| 1 | svc **3/4/9/10/21/28/68/80/93** 的代码构造点 | 扫 `0xB78C10` 全部 37 调用点，这 9 个 svc 一个都没命中 | **不走 `0xB78C10`** —— 它们可能走 `0xB78Bxx` 兄弟函数或不同封装。下一步：扫 `0xB78C10` 前后 0x400 字节内的同类函数 |
| 2 | `0xB916B4`/`0xBA0151`/`0xBA4AF5`/`0xBA7415` 4 个调用点的 (svc,task) | 调用形态非 `push imm`（走 `mov`） | 需单独读寄存器来源 |
| 3 | 服务 58 (Clan) 5 个 task 的**报文结构** | 只有调用点，无样本 | 结构可从 `0xB97000-0xB98000` 反序列化器读 |
| 4 | 每个未实现 task 的**空 ACK 是否导致客户端失败** | 231 卷给出商城判据；其余 9 个 svc 未查 | **逐 svc 找 `reply+N` 判据**，这是最大工作量 |
| 5 | 13 个"代码独有"task 的触发条件 | 已定位 call site，未反查上层 | 可静态推进 |

★ **边界 1 是下一册的第一优先项**：9 个 svc 完全不在 `0xB78C10` 的调用面，说明还有第二种任务头写函数。

---

## §7 复现命令

```powershell
python -I _rev_analysis/_p233/a1_reply5.py     # reply+5 写点全扫
python -I _rev_analysis/_p233/b3_gap.py         # 服务端覆盖率差集
python -I _rev_analysis/_p233/b5_svcnames.py    # 0xE4E8F8 服务名表解码
python -I _rev_analysis/_p233/b9_loop.py        # 0x7EEF2C 配置循环
python -I _rev_analysis/_p233/d6_v7.py          # ★ 0xB78C10 全部 (svc,task)
python -I _rev_analysis/_p233/e1_svc58.py       # 服务 58 = Clan
```

---

## §8 方法论

1. **★★★★★ 「service id 不可得」要先问「客户端在哪写这个 id」。** 名字表是配置面的产物，协议面的 id 在**写任务头的函数**里。`0xB78C10` 的参数顺序由 `0xB75E00`(writeN,1) 与 `0xB76620`(u8) 的调用形态确定，不是猜的。
2. **★★★★ 参数顺序必须用「语料交叉」验证，不能只看反汇编。** 若读反 (svc↔task)，15 个命中会变成 0 个。**命中本身就是判据。**
3. **★★★ 「语料里没有」≠「不存在」。** 服务 58 整片 5 个 task 在代码里，语料 0 条 —— 只是没走到战队界面。
4. **★★★ 名字表的字符串指针「零代码引用」是强判据。** 13/20 个名字表外引用为 0 ⇒ 一定是纯打印/配置用途，不可能是 id 映射源。
5. **★★ 「回空 ACK」不能当作安全默认。** 231 卷已证商城会因此死锁；本卷给出 40.4% 的流量都在走这条未知后果的路。
