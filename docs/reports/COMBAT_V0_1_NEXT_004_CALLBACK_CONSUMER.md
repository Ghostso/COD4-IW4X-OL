# COMBAT_V0_1_NEXT_004_CALLBACK_CONSUMER.md

> 任务：COMBAT-V0.1-NEXT-004 工作一 —— 寻找回调消费点
> 镜像：`image_best.bin`（基址 0x400000）· **纯静态，未启动/未注入/未附加客户端**
> 前置 NEXT-001..003 · 本次**未修改**任何协议、服务器实现、`SEC_KEY`、`GOLDEN-LOBBY-001`

---

## 0. 结论先行（回答问题 1、2）

### 问题 1：`[obj+0x1C]` 的真实消费点在哪里？

**❌ 前提被证伪：`[obj+0x1C]` 不是回调槽。**

`0xBA72C0`（消息对象构造）写的是 **`[esi+0x1C]` = `[ebp+8]` 的低字节**，即一个 **byte 标志**，
不是函数指针：

```
00BA72C0  mov  esi, ecx                  ; esi = 消息对象
00BA72E6  ...
00BA7306  mov  dl, byte ptr [ebp + 8]
00BA7309  mov  byte ptr [esi + 0x1c], dl   ; ★ +0x1C = BYTE（参数低字节）
00BA730C  mov  dl, byte ptr [ebp + 0xc]
00BA7318  mov  byte ptr [esi + 0x1d], dl   ; ★ +0x1D = 另一个 byte
00BA7321  mov  dword ptr [esi + 0x20], eax   ; eax = 0
00BA7324  mov  dword ptr [esi + 0x24], eax   ; eax = 0
00BA7328  mov  dword ptr [esi + 0x28], eax   ; eax = 0
```

**消息对象的真实布局（本次新证实）：**

| 偏移 | 宽度 | 含义 | 证据 |
|---|---|---|---|
| `+0x00` | dword | **vtable = `0xD5A64C`** | `0xBA7312 mov dword [esi], 0xD5A64C` |
| `+0x04` | dword | 上下文/持有者 | `0xBA72F3 mov [esi+4], ecx`（`ecx=[ebp+0x10]`） |
| `+0x08` | dword | 长度/容量 | `0xBA72F6 mov [esi+8], edi`（`edi=[ebp+0x14]`） |
| `+0x0C` | byte | 状态标志 | `0xBA72F9 mov byte [esi+0xC], 1` |
| `+0x10` | dword | 参数指针 | `0xBA72FD mov [esi+0x10], eax`(0) |
| `+0x14` | byte | **已释放/无效标志**（`0xBA74B0` 判它） | `0xBA7300` / `0xBA74B6 cmp byte [esi+0x14],0` |
| `+0x1C` | **byte** | 标志位 A | `0xBA7309` |
| `+0x1D` | **byte** | 标志位 B | `0xBA7318` |
| `+0x20` | dword | 次要指针 | `0xBA7321` |
| `+0x24` | dword | 次要值 | `0xBA7324` |
| `+0x28` | dword | **参数列表/回调指针** | `0xBA7328` 初始化为 0 |

**`+0x28` 是本次唯一可能的"回调槽"，且它在 `0xB9B0B0` 中确实被赋值：**

```
00B9B1C6  cmp  dword ptr [ebp - 0x24], 0
00B9B1CC  cmp  dword ptr [ebp - 0x20], 0
00B9B1D2  mov  edx, dword ptr [ebp + 0x1c]     ; 参数
00B9B1D5  mov  dword ptr [ebp - 0x24], edx     ; ★ 消息对象 +0x20
00B9B1D8  mov  dword ptr [ebp - 0x1c], esi     ; ★ 消息对象 +0x28 = esi
```
（`[ebp-0x44]` = 消息对象基址 ⇒ `[ebp-0x1c]` = `obj+0x28`，`[ebp-0x24]` = `obj+0x20`。）

### 消费点检索结果（`[reg+0x28]`）

| 检索形式 | 命中 | 判定 |
|---|---|---|
| `call dword ptr [reg+0x28]`（disp8/disp32，排除 SIB/ebp） | **2** | `0xC840AF`、`0x658A7E` —— **均为反汇编错位假命中**（逐指令复核为数据/立即数）；`0xC840AF` 实际位于非代码流，`0x658A7E` 在 `0x658A56 ret` 之后 |
| `mov reg,[base+0x28]` 后 48B 内出现间接 `call` | 3358 | 偏移 `0x28` 是极常见字段，**无法据此认定**（任务明确禁止仅凭同偏移认定） |
| 网络/传输区（`0xB7xxxx`–`0xCBxxxx`）内的上述候选 | 54 | 均在 `0x28` 作为**其它对象字段**的上下文；**未发现**与 `0xB9B0B0` 消息对象关联 |

**⇒ 问题 1 的答案：`[obj+0x1C]` 是 byte 标志，不是回调；
真正的回调槽是 `[obj+0x28]`，但它的消费点本次【未定位】。**

---

## 1. 问题 2：`0x6376F0` 与 `0x637930` 的上下文

### 1.1 `0x637930` —— **已定位（3 个调用点，全部确认）**

```
=== every dword ref to 0x637930 ===
   0x632721   (accepted handler 0x632680 的失败分支)
   0x62F94A   (0x62F840 的失败分支)
   0x62FBD0   (0x62FB9F)
```

**三处用法完全同构**（逐指令）：

```
00632720  6830796300   push 0x637930        ; ★ 回调
00632725  52           push edx             ; edx = [[0x82E140C]+0xC]
00632726  8bce         mov  ecx, esi        ; esi = 匹配对象
00632728  e8836bffff   call 0x6292B0        ; ★★ 延迟调度器
```
```
0062F949  6830796300   push 0x637930
0062F94E  52           push edx             ; edx = [[0x82E140C]+0xC]
0062F94F  8bcb         mov  ecx, ebx
0062F951  e85a99ffff   call 0x6292B0
```
```
0062FBCF  6830796300   push 0x637930
0062FBD4  52           push edx             ; edx = [[0x82E140C]+0xC]
0062FBD5  8bce         mov  ecx, esi
0062FBD7  e8d496ffff   call 0x6292B0
```

**`0x6292B0` 就是消费点 —— 它在失败路径上【直接调用】回调：**

```
006292B0  push ebp / mov ebp,esp
006292C5  mov  ebx, dword ptr [ebp + 0xc]    ; ebx = 回调（0x637930）
006292CE  mov  edi, ecx                       ; edi = 匹配对象
006292D5  inc  dword ptr [edi + 0x10780]      ; 计数++
006292F3  or   edx, 0xd692ada0                ; 会话/校验混合常量
006292F9  xor  edx, eax
00629308  ; 16 次位掩码循环 -> [esp+0x18 .. esp+0x54]（16 个 dword）
0062931C  mov  eax, [ebp + 8]
0062931F  push ebx                            ; 完成回调
00629320  add  edi, 0x7470                    ; ★★ 预约槽数组基址
00629326  push edi                            ; ★ 数据 = 预约块
00629327  push eax
0062932D  push 0x27                           ; ★★ 消息 ID = 0x27
0062932F  call 0x7F44B0                       ; 发送
00629337  test al, al
00629339  jne  0x629351                       ; 发送成功 -> 跳过
0062933B  test ebx, ebx / je 0x629351
00629343  push 0 / push 0 / push 0 / push 0
0062934B  push edx
0062934C  call ebx                            ; ★★★ 发送失败 -> 直接调用回调！
```

**⇒ `0x637930` 的执行上下文（CONFIRMED）：**
**它是消息 `0x27` 的完成/失败回调，由 `0x6292B0` 在发送失败时同步调用。**
（发送成功时，回调被交给消息框架，稍后由响应/超时触发 —— 该时点未定位。）

### 1.2 `0x637930` → `0x637720`（预约槽写入器）

```
00637930  push ebp / mov ebp,esp / push ecx
00637934  mov  eax, [ebp + 0x18]
00637937  mov  ecx, [ebp + 0xc]
0063793A  push eax
0063793B  mov  eax, [ebp + 0x14]
0063793E  push ecx
0063793F  mov  ecx, dword ptr [0x82e13fc]     ; ★ this = 匹配对象单例
00637945  call 0x637720                       ; ★★ 真正的槽写入器
```

`0x637720` 的写入（`0x637720` 前 6 条）：

```
00637726  cmp  byte ptr [ebp + 8], 0
00637735  mov  dword ptr [esi + 0x7230], eax   ; 槽计数 = eax
0063773B  imul eax, eax, 0x238
00637741  push eax                             ; 长度
00637742  mov  eax, [ebp + 0xc]                ; ★ 源指针
00637745  push eax
00637746  lea  ecx, [esi + 0x7470]             ; ★ 目的地 = 槽数组
00637752  call 0xC3C603                        ; memcpy/memmove
0063776A  mov  dword ptr [esi + 0xe360], ebx   ; 索引 = 0
0063777C  lea  edx, [esi + 0x75e0]             ; ★ = 槽 0 的 +0x170（名称字段）
```

**⇒ `0x637930` 的语义 = "把入参记录写进预约槽"，this 固定为 `[0x82E13FC]`。**

### 1.3 `0x6376F0` —— 仍未定位消费点

| 事实 | 证据 | 等级 |
|---|---|---|
| 全镜像**只有 2 处** dword 引用 | `0x62DDEA`、`0x7F4478` | CONFIRMED |
| `0x62DDEA` 处把它作为参数压栈（消息 0x26 的发送点） | `0x62DDE9 push 0x6376F0` → `0x62DDF6 call 0x7F44B0` | CONFIRMED |
| `0x7F4478` 处把它作为 `ecx`（处理器）传给注册器 | `0x7F4477 mov ecx,0x6376F0` → `0x7F447C call 0x7FAA20` | CONFIRMED |
| **它被调用的时点** | — | **UNKNOWN** |

**⇒ `0x6376F0` 与 `0x637930` 的关键差异：**
`0x637930` 有 **3 处显式 `push` 到一个已知会调用回调的调度器（`0x6292B0`）**；
`0x6376F0` 只有 **1 处 `push`（给 `0x7F44B0`，其 `0xB9B0B0` 只存不调）**
+ **1 处 `mov ecx`（给延迟注册器 `0x7FAA20`）**。

---

## 2. 入站 / 出站 / 延迟 / 清理 的区分（任务要求）

| 路径 | 函数 | 判据 | 归类 |
|---|---|---|---|
| 消息 **0x27 发送**（携带预约块 `mk+0x7470`） | `0x6292B0` → `0x7F44B0` | `0x629320 add edi,0x7470` + `push 0x27` | **出站** |
| 消息 **0x26 发送**（回调 = `0x6376F0`） | `0x62DD60` → `0x7F44B0` | `0x62DDF4 push 0x26` | **出站** |
| 发送失败的**同步回调** | `0x62934C call ebx` | `test al,al / jne` 后 `test ebx,ebx` | **完成/失败回调** |
| **预约槽写入** | `0x637720`（经 `0x637930`/`0x6376F0`） | `0x637746 lea ecx,[esi+0x7470]` + `call 0xC3C603` | **状态写入** |
| **清理/复位** | `0x62F2CF` 族（`0x62F473 mov word [mk+0x278],0`） | 见 NEXT-002 U1 | **清理** |
| **延迟激活注册** | `0x7FAA20` → `0x7FA800` | 106 调用点；表基 `0xE69CE0` | **延迟** |
| 本地 mmbook 分派 | `0x7F153F`（strncmp "mmbook"）→ `call [vtable+0x13C]` | NEXT-003 §1.1 | **入站分派** |

---

## 3. 已证实 / 未知 分级

| # | 结论 | 等级 |
|---|---|---|
| C1 | 消息对象 vtable = `0xD5A64C`；布局 `+0x14`=字节标志、`+0x1C/+0x1D`=**字节标志**、`+0x20/+0x24/+0x28`=dword | **CONFIRMED** |
| C2 | `0xB9B0B0` 把回调存入 `obj+0x28`、参数存入 `obj+0x20` | **CONFIRMED** |
| C3 | `call dword ptr [reg+0x28]` 的真实命中 = 0（两处为错位假命中） | **CONFIRMED** |
| C4 | `0x637930` 有 3 个调用点，全部 `push 0x637930` → `call 0x6292B0` | **CONFIRMED** |
| C5 | `0x6292B0` = 消息 0x27 发送器；**发送失败时同步调用回调**（`0x62934C call ebx`） | **CONFIRMED** |
| C6 | `0x637930` → `0x637720`，把入参记录 memcpy 进 `mk+0x7470`（槽数组） | **CONFIRMED** |
| C7 | `0x6376F0` → `0x637590`，把入参记录 memcpy 进 `mk+0x7470` | **CONFIRMED** |
| C8 | `[0x82E13FC]` 是匹配对象单例，由 `0x639D00` 用 `0x62C000` 构造（`0x639D19 call 0x62C000`；`0x639D1E mov [0x82E13FC],eax`） | **CONFIRMED** |
| C9 | 匹配对象内部子对象 `+0x10728`（`0x639DA1 add esi,0x38528` 之后的进一步构造） | **CONFIRMED（偏移）** |
| U1 | **`0x6376F0` 的调用时点/调用者** | **UNKNOWN** |
| U2 | **`obj+0x28`（消息回调槽）的框架消费点** | **UNKNOWN** |
| U3 | **`0x6292B0` 传入回调的实参**（参数计数未能唯一配平） | **UNKNOWN** |
| U4 | **A/B 在源记录中的字段偏移** | **UNKNOWN** |

---

## 4. 本次的可复核脚本

| 脚本 | 作用 |
|---|---|
| `_combat_next001/x1_ba74.py` | `0xBA74B0` / `0xBA72C0` 反汇编（消息对象布局） |
| `_combat_next001/x2_cb.py` | `[reg+0x28]` / `[reg+0x20]` 的 call/mov 全量检索 |
| `_combat_next001/x5_msgvt.py` | 消息 vtable `0xD5A64C` 与其 2 处引用 |
| `_combat_next001/x8_recheck.py` | 函数入口校正 + `0x6376F0`/`0x637930` 引用重查 |
| `_combat_next001/x9_637930.py` | **3 处 `push 0x637930` → `call 0x6292B0` 的上下文** |
| `_combat_next001/y1_sched.py` | **`0x6292B0` 反汇编（`0x62934C call ebx` 回调调用点）** |
| `_combat_next001/y2_fwd.py` | `0x637930` 转发器 + `0x637720` 槽写入器 |
| `_combat_next001/y3_source.py` | `[mk+0x10728]` 与 `[0x82E13FC]` 的引用统计 |
| `_combat_next001/y4_singleton.py` | **匹配对象单例的构造点 `0x639D00`** |
