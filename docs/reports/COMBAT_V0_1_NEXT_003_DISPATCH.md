# COMBAT_V0_1_NEXT_003_DISPATCH.md

> 任务：COMBAT-V0.1-NEXT-003 步骤 1–2 —— 还原注册表约定、定位真实触发者
> 镜像：`image_best.bin`（基址 0x400000）· **纯静态，未启动/未注入/未附加客户端**
> 前置：[COMBAT_V0_1_NEXT_002_IMPLEMENTATION_GATE.md](COMBAT_V0_1_NEXT_002_IMPLEMENTATION_GATE.md)
> 本次**未修改**任何协议、服务器实现、`SEC_KEY`、`GOLDEN-LOBBY-001`。

---

## 0. 结论先行（回答完成标准 Q1）

> **Q1：`0x7FAA20` 如何分派到 `0x6376F0`？**
>
> **答：它不是"注册到消息表再由消息触发"，而是"随一条出站网络消息被回调"。**
>
> 路径（全部逐指令可复核）：
> ```
> 0x62DDF6 call 0x7F44B0            ; 发送消息 id=0x26，回调 = 0x6376F0
>   -> 0x7F44B0 校验 transport==2（已连接）
>      0x7F4503 call 0xB9B0B0      ; 组装出站缓冲，并调用回调填充
>      -> 0xB9B0B0 内部调用回调 0x6376F0(ctx, buffer)
>      -> 0x6376F0 计算预约槽 = ctx+0x7470+[ctx+0xE360]*0x238
>         -> 0x63770D call 0x637590 ; 把整槽 0x238 字节写进出站缓冲
>      ; 0x7F44B0 随后再走 0x7F456E call 0x7FAA20 做"延迟/补发注册"
> ```
>
> **`0x7FAA20` 是"延迟激活/补发注册器"，`0x7F44B0` 才是"发送器"。**
>
> ★★ **本次追加的决定性证据**：`0xB9B0B0` **只把回调存进消息结构，不调用它**：
> ```
> 00B9B190  mov  esi, [ebp + 0x14]      ; 回调指针
> 00B9B1C6  cmp  dword [ebp - 0x24], 0
> 00B9B1D2  mov  edx, [ebp + 0x1c]
> 00B9B1D5  mov  [ebp - 0x24], edx
> 00B9B1D8  mov  [ebp - 0x1c], esi      ; ★★ 回调被**存入**消息对象，未 call
> ```
> ⇒ **回调是"先登记、后被调用"**（由消息框架在后续时机触发）。
> ⇒ 因此 **`0x6376F0` 既不是"发送时同步填充"，也不是"注册表分派"**，
>    而是**随消息对象一同登记、由框架在稍后调用**的一跳。
>    **该调用点本次仍未定位**（`0xB9B0B0` 全长未见间接 call 该回调）。
> 任务给定的线索 `0x7F4477 mov ecx,0x6376F0 ; 0x7F447C call 0x7FAA20`
> **位于 `0x7F44B0` 的尾部**，即**发送之后的注册步骤**，不是入口。

**这修正了 NEXT-002 的一个判断**：当时把 `0x7FAA20` 当作"要解析的注册表"。
实际 `0x7FAA20` 是**通用延迟激活器**（106 个调用点），
真正需要解析的是 **`0x7F44B0`（只有 2 个调用点）**。

---

## 1. 三层函数的分工（本次新证实）

| 函数 | 调用点数 | 职责 | 证据 |
|---|---|---|---|
| **`0x7F44B0`** | **2** | **出站消息发送器**（本次的真实主角） | `0x7F44BE call 0x803830`（取 transport manager 单例）；`0x7F44CB call 0xB7A670`（get_state）→ `cmp eax,2`（要求 state==2）；`0x7F4503 call 0xB9B0B0`（组装+回调） |
| `0x7FAA20` | 106 | **延迟激活/补发注册器** | 大量压栈后 `0x7FAA56 call 0x7FA800`；`0x7FAA44 test eax,eax` + `0x7FAA63` 判空 |
| `0x7FA800` | 7 | 注册表实现（表基 `0xE69CE0`，条目 0x50 字节，扫描 `0xE56FFE0..0xE5713E0`） | `0x7FA84D mov esi,0xE56FFE0`；`0x7FA84D..0x7FA864` 逐条扫描；`0x7FA83E mov eax,[ecx*8+0xE4E20C]` + `shl eax,4` + `add eax,0xE69CE0` |

### 1.1 `0x7F44B0` 的逐指令证据

```
007F44B0  push ebp / mov ebp,esp / sub esp,8
007F44B7  mov ebx, [ebp+0xc]        ; arg2 = 上下文对象指针
007F44BE  call 0x803830             ; ★ 取 transport manager 懒加载单例
007F44C3  mov edi, eax
007F44C7  je 0x7F44E5               ; 取不到 -> 返回 false
007F44CB  call 0xB7A670             ; get_state
007F44D0  cmp eax, 2                ; ★ 必须 == 2（已连接）
007F44D3  jne 0x7F44E5              ; 否则返回 false（消息不发）
007F44D5  push 0xDAE091             ; 空串 ""
007F44DA  call 0xB7A800             ; 取连接对象
007F44E1  test eax,eax / jne 0x7F44EE
007F44EE  mov ecx, [ebp+0x14]       ; arg5（= 0x62DDF4 的 push 0x26？见 §2）
007F44F1  mov edx, [ebx+0x48]       ; ★ 上下文 +0x48（消息目标/连接句柄）
007F44F4  push ecx
007F44F5  mov ecx, [ebp+0x10]
007F44F8  push ebx
007F44F9  push ecx
007F44FA  push 0
007F44FC  push edx
007F44FD  lea edx, [ebp-4]
007F4500  push edx
007F4501  mov ecx, eax
007F4503  call 0xB9B0B0             ; ★ 组装出站消息（内部会调用回调）
...
007F4551  push 0x7F4330             ; 完成回调
007F4556  push ecx
007F4559  lea edi, [esi+4]
007F455C  push edi
007F455D  mov [eax], esi
007F455F  call [0xca8128]           ; 引用计数 +
007F4565  mov eax, [ebp+8]
007F4568  mov ecx, [ebp+0x18]
007F456B  push eax
007F456C  mov eax, ebx
007F456E  call 0x7FAA20             ; ★★ 发送之后再注册（这就是任务给的线索）
```

⇒ **`0x7FAA20` 的调用发生在 `0xB9B0B0` 之后**，属**发送完成后的登记**。
**因此"注册表"不是触发 `0x6376F0` 的路径**；触发它的是 `0xB9B0B0` 的**回调填充**。

---

## 2. `0x7F44B0` 的**唯一两个调用点**（本次关键新证据）

```
=== callers of 0x7F44B0 ===   count = 2
   0062932F   (in ~006292AF)
   0062DDF6   (in ~0062DD5F)
```

### 2.1 调用点 A：`0x62DDF6` —— 消息 **0x26**，回调 **0x6376F0**

```
0062DDE1  a124142e08      mov  eax, [0x82E1424]
0062DDE6  8b400c          mov  eax, [eax + 0xC]      ; ★ ctx = [ [0x82E1424] + 0xC ]
0062DDE9  68f0766300      push 0x6376F0              ; ★ 回调 = 预约槽填充器入口
0062DDEE  57              push edi                   ; （edi = [ebp+8]）
0062DDEF  8b7d08          mov  edi, [ebp+8]
0062DDF2  50              push eax                   ; ctx
0062DDF3  57              push edi
0062DDF4  6a26            push 0x26                  ; ★★ 消息 ID = 0x26
0062DDF6  e8b5661c00      call 0x7F44B0
```

⇒ **消息 0x26 的填充回调就是 `0x6376F0`。**
按 `0x7F44B0` 的形参约定：`[ebp+8]=0x26`（消息 id）、
`[ebp+0xC]=ctx(=mk)`、`[ebp+0x10]=edi`、`[ebp+0x14]=0x6376F0`。

### 2.2 调用点 B：`0x62932F` —— 消息 **0x27**，数据 = 预约块（**不是**回调）

```
006292F0  8b510c          mov  edx, [ecx + 0xC]
006292F3  81caa0ad92d6    or   edx, 0xD692ADA0        ; ★ 与 0xD692ADAB 只差最低字节
006292F9  33d0            xor  edx, eax
00629301  e82a420000      call 0x62D530              ; 取会话相关值
00629306  33c9            xor  ecx, ecx
00629308  ; 16 次迭代的位掩码循环（0..0xF）
0062931C  8b4508          mov  eax, [ebp + 8]
0062931F  53              push ebx                   ; 完成/失败回调
00629320  81c770740000    add  edi, 0x7470           ; ★ 预约槽数组基址
00629326  57              push edi                   ; 数据指针
00629327  50              push eax
00629328  8d4c241c        lea  ecx, [esp + 0x1C]
0062932C  51              push ecx
0062932D  6a27            push 0x27                  ; ★★ 消息 ID = 0x27
0062932F  e87cb11c00      call 0x7F44B0
```

⇒ **消息 0x27 携带"预约块"（`mk+0x7470`）**。
⇒ **`0x26` 不是"预约块上传"，而是"预约槽被序列化进某条出站消息"**；
`0x27` 才是"把预约块整体发出"。

### 2.3 ★ 任务给出的 `0x26` 的确切含义

**`0x26` = 消息 ID，其填充回调 = `0x6376F0`（预约槽填充器）。**
**不是**任务猜测的"注册表条目号"。

相关常量（本次更正 NEXT-002 的 OCR 误读）：

| 值 | 含义 | 证据 |
|---|---|---|
| `0x26` | 消息 ID（回调型） | `0x62DDF4 push 0x26` |
| `0x27` | 消息 ID（数据型，预约块） | `0x62932D push 0x27` |
| `0xD692ADA0` | 0x6292F3 的 or 掩码 | 立即数编码不在 `68/B8..` 前缀，故先前未命中；本次从反汇编读出 |

> ⚠️ 注意：`0xD692ADA0` 与 NEXT-001 记录的会话记录字段 4
> "`0xD692ADAB`（query criterion）"**只差最低字节**。
> 这是**巧合还是同源**，本次**未证明**，不作断言（列入 §4 未知）。

---

## 3. `0x6376F0` 的数据来源（逐指令）

```
006376F0  push ebp ; mov ebp,esp
006376F3  mov eax, [ebp+0x18]        ; 第六个参数
006376F6  mov ecx, [ebp+0x10]        ; 第四个参数
006376F9  mov edx, [ebp+0xc]         ; 第二个参数
006376FC  push eax
006376FD  mov eax, [ebp+8]           ; 第一个参数 -> 传给 0x637590 的 [ebp+0xc]
00637700  push ecx
00637701  mov ecx, [0x82E13FC]       ; ★★ 全局匹配对象单例
00637707  push edx
00637708  push eax
00637709  mov eax, [ebp+0x14]        ; 第五个参数
0063770C  push ecx                   ; ★ 作为 0x637590 的 ecx（this）
0063770D  call 0x637590             ; ★★ 真正的填充器
00637712  pop ebp / ret
```

**`0x6376F0` = 薄转发器**；真正的填充在 `0x637590`，
而 **`this` 来自全局 `[0x82E13FC]`**（与 accepted handler 的 `0x632717/0x632736` 同源）。

### 3.1 `0x637590`（第一次逐指令确认）

```
00637590  push ebp / mov ebp,esp / sub esp,0x14
0063772D  ...
0063772D  mov esi, ecx               ; ★ this = 匹配对象
00637726  cmp byte [ebp+8], 0
00637735  mov [esi+0x7230], eax      ; 槽计数
0063773B  imul eax, eax, 0x238
00637741  push eax                   ; 长度 = count*0x238
00637742  mov eax, [ebp+0xc]
00637745  push eax                   ; ★ 源指针
00637746  lea ecx, [esi+0x7470]      ; ★ 目的地 = 预约槽数组基址
0063774C  push 0x6EF0                ; 总容量
00637751  push ecx
00637752  call 0xC3C603              ; ★★ memcpy/memmove 型
00637762  cmp eax, ebx               ; ebx=0
0063776A  mov [esi+0xE360], ebx      ; 槽索引 = 0
0063777C  lea edx, [esi+0x75E0]      ; ★ 槽内 +0x170 的绝对地址（= 0x7470+0x170）
```

**★ 方向确认（本次纠正 NEXT-002 的措辞）**：
`0x637590` 是 **`(this, src) -> 写入预约槽`**，
即 **dst = 预约槽数组 `this+0x7470`，src = 调用者传入**。
因此 **预约槽的填充源 = `0x6376F0`/`0x637590` 的 `[ebp+0xc]`/`[ebp+8]`**。

### 3.2 两个填充入口的参数来源对比

| 入口 | 谁调用 | 传入的 src | 结论 |
|---|---|---|---|
| `0x6376F0` | `0xB9B0B0` 的**出站回调**，ctx 由 `[0x82E1424]+0xC` 闭合 | 由出站消息框架提供 | 这是**发送/序列化**路径 |
| `0x637720` | 仅 `0x637930`（薄转发器） | `0x63793A push [ebp+0x18]`、`0x637E3E push [ebp+0xc]` | 由调用者提供 |

```
00637930  push ebp / mov ebp,esp / push ecx
00637934  mov eax, [ebp+0x18]
00637937  mov ecx, [ebp+0xc]
0063793A  push eax                    ; 参数
0063793B  mov eax, [ebp+0x14]
0063793E  push ecx
0063793F  mov ecx, [0x82E13FC]        ; ★ 同样是全局匹配对象
00637945  call 0x637720              ; ★★ 第二个填充器
```

⇒ **两个填充器都以 `[0x82E13FC]` 为 this，都从栈参数取 src。**
**它们是"入槽"和"出槽"两个方向的两个函数**，不是"注册/触发"关系。

---

## 4. 已证实 / 推断 / 未知（本报告范围）

| # | 结论 | 等级 |
|---|---|---|
| D1 | `0x7F44B0` = 出站消息发送器（校验 transport state==2，再组装） | **CONFIRMED** |
| D2 | `0x7F44B0` 全镜像**只有 2 个调用点**（`0x62932F`、`0x62DDF6`） | **CONFIRMED** |
| D3 | `0x7FAA20` = 延迟激活/补发注册器，在**发送之后**被调用（106 调用点） | **CONFIRMED** |
| D4 | 消息 **0x26** 的填充回调 = `0x6376F0`（预约槽填充器入口） | **CONFIRMED** |
| D5 | 消息 **0x27** 的数据 = 预约块 `mk+0x7470` | **CONFIRMED** |
| D6 | `0x6376F0` 是薄转发器，真正填充在 `0x637590`，this = `[0x82E13FC]` | **CONFIRMED** |
| D7 | `0x637590`/`0x637720` 是 **"写入预约槽"**（dst=mk+0x7470, src=参数） | **CONFIRMED** |
| D8 | `0x62CD30` 是 vtable `0xDC72B0` 的 **slot +0x08**；`0x62F840` = +0x00；`0x632680` = +0x100 | **CONFIRMED** |
| D9 | `0x62CD30` 全镜像只有 2 处数据引用（两个 vtable），**无直接调用**；按 slot+0x08 的
 直接调用点检索为 0（该槽经其他间接形式调用，未定位） | **UNKNOWN** |
| D10 | `0xD692ADA0` 与会话记录 criterion `0xD692ADAB` 是否同源 | **UNKNOWN（巧合/同源未证）** |
| D11 | `[0x82E1424]+0xC` 是否等于 `[0x82E13FC]`（同一匹配对象） | **UNKNOWN（强候选，未证）** |
| D12 | 消息 0x26 是**发往服务端**还是**本地/内部** | **UNKNOWN**（`0x7F44B0` 走 transport，倾向网络出站，但未证目标） |

---

## 5. 本次的可复核脚本

| 脚本 | 作用 |
|---|---|
| `_combat_next001/s1_reg.py` | `0x7FAA20` 反汇编 |
| `_combat_next001/s2_disp.py` | `0x7FA800` 注册表实现 + 7 个调用点 |
| `_combat_next001/s3_vtable.py` / `s4_fullvt.py` | vtable `0xDC72B0` 全 112 槽（含 `0x62CD30`@+0x08、`0x632680`@+0x100） |
| `_combat_next001/s7_refs.py` | `0x62CD30`/`0x6376F0` 的全部数据引用 |
| `_combat_next001/s8_dd.py` | `0x62DD5F` 函数（消息 0x26 发送点） |
| `_combat_next001/t1_reg2.py` | `0x7F44B0` 反汇编 + 2 个调用点 |
| `_combat_next001/t2_b9b.py` | `0xB9B0B0` 组件 + `0x62932F`（消息 0x27） |
| `_combat_next001/t4_cb2.py` | `0x637590` 逐指令 + `0x637930` 转发器 |
| `_combat_next001/t5_ada.py` | `0xD692ADA0` 与 criterion 常量检索 |
