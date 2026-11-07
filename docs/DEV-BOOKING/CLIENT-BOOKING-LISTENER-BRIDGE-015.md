# CLIENT-BOOKING-LISTENER-BRIDGE-015
# accepted handler 的 listener 广播 → 注册源 / vtable / callback 的静态闭合

> 2026-10-08 执行。**纯静态**。未修改 client / server / senderId / booking response /
> SessionId / 28960 / Battle server。未 hook、未 patch、未伪造 UDP/DTLS。未运行动态实验。
>
> 分析源：`CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin`
> （运行期已解壳镜像，10,899,456 B，**VA = 0x00400000 + 文件偏移**，可读范围
> `0x00400000 .. 0x00E65000`）。超出该范围的全局只能看到"引用它的指令"，看不到内容。
>
> 补充数据源（本轮新用）：`COD OL\codoMP_client_shipRetail.exe` 的 **section[2] (.tp3) raw 区**
> （RVA 0xA16000..0xA78000，文件偏移 0x702000..0x764000，**明文未加密**）。
> 用于读出 0xE69xxx 静态 listener 对象的 vtable 指针（镜像 dump 里读不到）。

---

## 0. 结论先行

```
ACCEPTED_HANDLER            = 0x00632680（base matching 对象 vtable+0x13C）
ACCEPTED_BROADCAST_SITE     = 0x00632824..0x00632844（成功）/ 0x0063289E..0x006328B3（失败）
ACCEPTED_BROADCAST_ABI      = listener->vtable+0x24(arg1, arg2)
                              成功 = (1, 0)；失败 = (0, 2)；callee 清 8 字节栈

ACCEPTED_LISTENER_LIST      = CONFIRMED，位于 [0x082E13FC]+0x04
LISTENER_CONTAINER_LAYOUT   = { head@+0, tail@+4, count@+8 }
LISTENER_NODE_LAYOUT        = { value@+0, next@+4, prev@+8 }（12 字节，0xC）
LISTENER_REGISTRATION_SITE  = CONFIRMED  ← 本轮最大突破（见 §4）
LISTENER_VTABLE             = CONFIRMED（7 个注册点，vtable 全部锁定）
LISTENER_CALLBACK           = CONFIRMED（7 个 +0x24 目标全部锁定）

其中 5/7 个 listener 的 +0x24 = 0x004F7590（`ret 8` 空实现，NOT_BATTLE_LISTENER）
另外 2/7 个是真实回调：
  0x00738E70 = wargod 排位天梯数据刷新（UI/战绩，非 Battle）
  0x007CAF30 = UI / CEF 内嵌网页 + 事件投递（非 Battle）

=> LISTENER → BATTLE = REFUTED（7/7，无 UNKNOWN 残留）
   BATTLE_TRIGGER_PATH = UNRESOLVED（accepted 的 listener 广播不产生任何 Battle 行为）
   LOBBY_PATH_EXCLUDED = YES
   SENDERID_PATH_CLOSED = YES
```

**一句话**：accepted 分支确实会遍历 `[matching+4]` 的观察者链表并逐个调用
`listener->vtable+0x24`，但链表中**没有任何一个 listener 的 +0x24 会进入 Battle /
session / socket**；其中 5 个是空实现，2 个是战绩/UI。因此「accepted →
listener → Battle」这条假说本轮被**证伪**（而不是"未找到"）。

---

## 1. FACT_BASELINE（承接 003/006/012/013/014，全部复核）

```
image_best.bin VA 映射        = 0x00400000 + fileoffset（VA 0x400000..0xE65000 可读）CONFIRMED
客户端 EXE imagebase          = 0x00400000，SizeOfImage = 0x0E659000          CONFIRMED
  section[0] .tp3 RVA 0x1000    VS 0x8A689A  RAW 0x1000    RS 0x593000
  section[1] .tp3 RVA 0x8A8000  VS 0x16DA70  RAW 0x594000  RS 0x16E000
  section[2] .tp3 RVA 0xA16000  VS 0xDBB1CC0 RAW 0x702000  RS 0x00062000（明文）
matching 单例                 = [0x082E13FC]，vtable 0x00DC7274，ctor 0x0062C000
derived matching（booking UI）= [0x082E1400]，vtable 0x00DC73DC，ctor 0x00638210
  其 base 子对象在 +0x18，vtable 被改写为 0x00DC7714
6/14 mmbook 响应通道          = Lobby TCP（127.0.0.1:eph -> 127.0.0.2:3074），已排除重查
senderId / A-B                = LOW32/HIGH32 MATCH，已关闭，未重查
[0x0849B61C]                  = UI flag，已知 2 个 reader 0x7CB1E2 / 0x7CFA87，未重查
```

---

## 2. ACCEPTED_HANDLER（0x00632680，逐条复核 014）

```
0x0063268B  mov esi, ecx                 ; esi = matching([0x082E13FC])
0x0063268D  cmp byte [esi+0x278], 0      ; booking pending 守卫
0x006326B9  cmp eax, [esi+0x3a048]       ; A 比对
0x006326C8  cmp ebx, [esi+0x3a04c]       ; B 比对
0x006326DA  push 0xdc69b0 "mmbook accepted"
0x006326DF  call 0xc3c678 (strncmp)      ; == 0 走 accepted
--- accepted 成功路径 ---
0x00632736  movzx eax,[esi+0x105fc]
0x00632761  call 0x771320                ; 遥测/日志（事件描述符 0xdc74f8）
0x0063278F  call [esi.vt+0x150]          ; 0x6297A0：strlen thunk -> vt+0x14C
0x006327C3  call [esi.vt+0x14C]          ; 0x629730：序列化 + 入队 [esi+0x3a0b0]
0x00632809  call [esi.vt+0x148]          ; 0x62C580：状态迁移
0x0063280B  mov byte [esi+0x288], 1      ; 对象级 accepted 状态
0x00632812  call 0x62F6C0                ; 复位 A/B
0x0063281E  call [esi.vt+0x5C]           ; 0x62FDE0：网络对象存在性守卫
0x00632822  jne 0x632864                 ; ★ 非零（存在有效 net 对象）则【跳过】listener 广播
0x00632824  mov edi,[esi+4]              ; ★★ listener 链表 head
0x00632827  mov byte [0x0849B61C], 1     ; 全局 UI flag
0x00632832  mov ecx,[edi]                ; node->value
0x00632834  mov eax,[ecx]                ; value->vtable
0x00632836  mov edx,[eax+0x24]           ; ★ listener 回调槽
0x00632839  mov edi,[edi+4]              ; next
0x0063283C  push 0
0x0063283E  push 1
0x00632840  call edx                     ; this=ecx, arg1=1, arg2=0
0x00632842  jne 0x632832                 ; 循环
0x00632846  mov eax,[esi+0xe360]         ; reservation index
0x00632859  push esi / call 0x6293B0     ; 构造/提交会话记录（见 §7）
0x0063285F  call 0x629F80                ; 状态门控（见 §7）
0x00632864  call 0x655930                ; 清理
--- 失败/超时路径 ---
0x0063289E  mov edi,[esi+4]
0x006328A5  mov ecx,[edi] / mov eax,[ecx] / mov edx,[eax+0x24]
0x006328AF  push 2
0x006328B1  push 0
0x006328B3  call edx                     ; arg1=0, arg2=2
```

**关键新事实**：`0x00632822 jne 0x632864` — listener 广播**不是无条件执行**；
它只在 `matching->vt[+0x5C]`（`0x0062FDE0`）返回 **0** 时执行。

`0x0062FDE0` 的行为（CONFIRMED）：

```
0x0062FDFC  call 0x803830        ; 取全局网络对象
0x0062FE09  call 0xb7a670        ; 取对象"类型"
0x0062FE0E  cmp eax, 2           ; 类型 != 2 -> 返回 0
0x0062FE15  call 0xb7a770        ; 取对象子字段
0x0062FE1E  mov eax, 1           ; 都成立 -> 返回 1（跳过广播）
```

即：**只有当"不存在类型 2 的有效网络对象"时才广播 listener**。

---

## 3. ACCEPTED_LISTENER_LIST / LISTENER_OBJECT_LAYOUT（CONFIRMED）

### 3.1 容器

`[matching + 0x04]` 是一个手写双向链表容器，**不是** std::list：

```
container ptr = [0x082E13FC] + 4
  +0x00  head
  +0x04  tail
  +0x08  count
```

证据（唯一写入者 = 插入 helper `0x00724EB0`）：

```asm
0x00724EB3  push 0xc                  ; ★ 节点 12 字节
0x00724EB5  call 0xb74220             ; 分配
0x00724EC1  mov ecx,[ebp+8]           ; 参数 = &value
0x00724EC4  mov edx,[ecx]
0x00724EC6  mov [eax], edx            ; node->value = value
0x00724EF9  mov edx,[esi]             ; 空表分支
0x00724EFB  mov [eax+4], edx          ; node->next = head
0x00724EFE  mov [eax+8], 0            ; node->prev = 0
0x00724F0B  mov [ecx+8], eax          ; head->prev = node
0x00724F0E  inc dword [esi+8]         ; count++
0x00724F11  mov [esi], eax            ; head = node
0x00724F17  inc dword [esi+8]
0x00724F1A  mov [esi+4], eax          ; tail = node
0x00724F1D  mov [esi], eax            ; head = node
```

### 3.2 节点

```
node = { value@+0x00, next@+0x04, prev@+0x08 }   // 0x00C 字节
value = 指向多态对象的指针；*(value) = 该对象的 vtable
```

与广播循环 `0x632832..0x632844` 完全一致（`[edi]` 取 value，`[edi+4]` 取 next）。

### 3.3 匹配对象上共有 4 条同类容器

| 容器 | 谁插入 | 谁遍历 |
|---|---|---|
| `matching+0x04` | 7 处（见 §4） | `0x632824`（vt+0x24）/ `0x62DDB6`（vt+0x10） |
| `matching+0x10` | `0x6C2E66` | 未在可读代码中发现遍历者 |
| `derived([0x82E1400])+0x04` | `0x724E44` | 未发现 |
| `derived_base(+0x1C)` | `0x6382D9` | 未发现 |

### 3.4 同一链表的第二个（非 accepted）消费者

`0x62DD60`（= matching 对象 vtable+0x1C）也遍历 `[matching+4]`：

```asm
0x0062DD9B  mov eax,[0x82e13fc]
0x0062DDA9  mov ebx,eax
0x0062DDB6  mov esi,[ebx+4]           ; head
0x0062DDC7  mov ecx,[esi]             ; value
0x0062DDC9  mov eax,[ecx]             ; vtable
0x0062DDCB  mov edx,[eax+0x10]        ; ★ 另一个槽（+0x10）
0x0062DDCE  mov esi,[esi+4]
0x0062DDD1  push 0
0x0062DDD3  push ebx                  ; matching+0x340
0x0062DDD4  push 0x1c
0x0062DDD6  push 0
0x0062DDD8  push edi                  ; arg1->0x48
0x0062DDD9  call edx                  ; 5 参数
```

⇒ **同一个 listener 链表被两种不同事件复用**（+0x24 和 +0x10）。
accepted 用的是 **+0x24**。

---

## 4. LISTENER_REGISTRATION_SITE（CONFIRMED，本轮核心）

### 4.1 插入 / 删除 helper 家族

```
0x00724EB0  insert(container in ESI, position node in EDI, &value)   ret 4   ← 主插入
0x00623430  insert into (EAX+4) 头插
0x00623460  remove(container in ESI, value in ECX)                            ← 反注册
0x00724E50  remove（同一家族）
0x00724F30  append（节点 0x58 字节，另一容器族）
0x007CBD10  insert（0x0C 节点，0x7CBxxx 家族自备一份）
```

> 说明：这是 MSVC 内联容器助手，调用约定为 **container 放 ESI、位置节点放 EDI、
> 值取 `&local` 单栈参**，因此 `call 0x724EB0` 之前一定能看到
> `mov esi,[容器基址]` / `add esi,偏移` / `mov edi,[esi]` 三件套。

### 4.2 写入 `[0x082E13FC]+0x04`（accepted 广播目标）的全部注册点

| # | 注册点 | value（listener 对象） | vtable |
|---|---|---|---|
| 1 | `0x006382B3`（derived ctor `0x638210`） | `&[0x082E1400] + 0x3A148` | `0x00DC787C` |
| 2 | `0x006C0E43` | `[0x08425504]` | `0x00DCECEC` |
| 3 | `0x00736CD5` | `0x00E69C34`（静态对象） | `0x00DD7194` |
| 4 | `0x007C5154` | `[0x0849B60C]` | `0x00DDCBDC` |
| 5 | `0x007CBCF6` | `0x00E69CB0`（静态对象） | `0x00DDCF2C` |
| 6 | `0x0063B097`（ctor `0x63B020`） | `this`（vtable `0x00DC7E6C`） | `0x00DC7E6C` |
| 7 | `0x0063B4E7` | `0x0E60CAF8`（静态对象） | UNRESOLVED（见 §5.3） |

反注册对照：`0x623460` 被 `0x5ED5A8`、`0x5ED90A`、`0x63830B`、`0x63B0C3`、
`0x63C09B`、`0x736D0D`、`0x7C50D1`、`0x7EF486` 调用（各自成对 ADD/REMOVE）。

`matching+0x10` 的注册点：`0x006C2E66` → value `0x00E69BE0`（vtable `0x00DCF39C`）。

### 4.3 注册点 1 的关键反汇编（derived ctor 0x638210）

```asm
0x0063826A  mov esi,[0x82e13fc]        ; 单例
0x00638248  lea edi,[ebx+0x3a148]
0x00638254  mov [edi], 0xdc787c        ; ★ listener 子对象 vtable
0x00638280  add esi, 4                 ; ★ container = matching+4
0x00638299  mov eax,[esi]              ; 查重（node->value == edi ?）
0x006382A2  cmp [eax], edi
0x006382A6  mov eax,[eax+4]
0x006382AD  mov edi,[esi]
0x006382B3  call 0x724eb0              ; ★ 注册到 matching+4
```

### 4.4 注册点 4 的反汇编（`0x7C5120`）

```asm
0x007C5124  mov ecx,[0x849b60c]        ; listener 对象
0x007C512F  mov esi,[0x82e13fc]
0x007C5135  mov eax,[esi+4]
0x007C5138  add esi,4                  ; container = matching+4
0x007C5142  cmp [eax], ecx             ; 查重
0x007C5154  call 0x724eb0
```

`[0x0849B60C]` 由 `0x7C5000` 创建：`push 4 / call 0xc3e9f5 / mov [eax],0xddcbdc /
mov [0x849b60c],eax` ⇒ 4 字节纯 vtable 适配器对象。

---

## 5. LISTENER_VTABLE / LISTENER_CALLBACK（全部锁定）

### 5.1 方法

`*(listener) = vtable`（对象首 dword）。回调 = `vtable + 0x24`。

### 5.2 完整表

| # | listener value | vtable | **vtable+0x24** | 判定 |
|---|---|---|---|---|
| 1 | `&[0x82E1400]+0x3A148` | `0x00DC787C` | `0x004F7590`（`ret 8`） | NOT_BATTLE（空实现） |
| 2 | `[0x08425504]` | `0x00DCECEC` | `0x004F7590` | NOT_BATTLE（空实现） |
| 3 | `0x00E69C34` | `0x00DD7194` | **`0x00738E70`** | NOT_BATTLE（wargod 排位） |
| 4 | `[0x0849B60C]` | `0x00DDCBDC` | `0x004F7590` | NOT_BATTLE（空实现） |
| 5 | `0x00E69CB0` | `0x00DDCF2C` | **`0x007CAF30`** | NOT_BATTLE（UI / CEF） |
| 6 | `this`（`0x63B020` ctor） | `0x00DC7E6C` | `0x004F7590` | NOT_BATTLE（空实现） |
| 7 | `0x0E60CAF8` | `0x00DC78EC` | `0x004F7590`（`ret 8`） | NOT_BATTLE（空实现） |
| (B) | `0x00E69BE0`（在 matching+**0x10**，非 +4） | `0x00DCF39C` | `0x008435D0`（`ret`） | 空实现 |

**⇒ 7/7 个 listener 的 +0x24 全部锁定，无一进入 Battle。**

vtable 读取证据（例，`0x00DD7194`）：

```
0xE69C34 处 dword = 0x00DD7194        ← 来自 EXE section[2] 明文数据
0xDD7194+0x24 = 0xDD71B8 处 dword = 0x00738E70
```

`0x004F7590` = `c2 08 00`（`ret 8`），`0x008435D0` = `c3`（`ret`）：
均为**共享默认空实现**，被 listener #1/#2/#4/#6/#7 五个不同 class 的 vtable
共同引用（各自 `vtable+0x24` 处均为 `0x004F7590`）。
⇒ 说明 `+0x24` 是这个大接口里"绝大多数类都不重写"的槽位。

### 5.3 listener #7（`0x0E60CAF8`）的 vtable 来源

镜像 dump 只覆盖到 RVA 0xA65000，而 `0x0E60CAF8` 的 RVA = 0xA20CAF8，看不到内容；
EXE section[2] 的文件映射部分也只到 RVA 0xA78000。**但 vtable 是代码内联写入的**：

```asm
0x0063B49C  test byte [0x0E9C668C], 1        ; 一次性初始化守卫
0x0063B4A3  mov  [0x082E1578], eax
0x0063B4AA  or   dword [0x0E9C668C], 1
0x0063B4B1  mov  dword [0x0E60CAF8], 0x00DC78EC   ; ★ listener #7 的 vtable
0x0063B4BB  mov  esi,[0x082E13FC]
0x0063B4C4  add  esi,4                             ; container = matching+4
0x0063B4C7  mov  [ebp-4], 0x0E60CAF8
0x0063B4E7  call 0x00724EB0                        ; 注册
```

`0x00DC78EC + 0x24 = 0x00DC7910` → dword = **`0x004F7590`**（`ret 8`，空实现）。

此外，dump 资源 `_cleanout\dump_low/zone/wide/big/devmap/map.bin` 经内容检索
（`"mmbook accepted"` / `"mmbook timedout"` 零命中）确认**不含该模块映射**，
无法用来补读 RVA 0xA20CAF8；本条不再是残留 UNKNOWN。

⇒ **7 个 listener 的 +0x24 全部落定，无 UNKNOWN 残留。**

---

## 6. CALLBACK_DOWNSTREAM（逐个追，均不进入 Battle）

### 6.1 `0x00738E70`（listener #3）

```asm
0x00738E70  mov al, byte [0x08425990]
0x00738E75  mov byte [0x0842558B], al
0x00738E7A  test al,al
0x00738E7C  je   0x738e8d
0x00738E7E  call 0x738BF0
0x00738E83  call 0x738D00
0x00738E88  call 0x737430
0x00738E8D  ret 8
```

下游全是 wargod（排位天梯）数据刷新，字符串证据：

```
0x00DD6EA4 "wargodLadderArray"                0x00DD7110 "wargodMatchState"
0x00DD7140 "currentSeasonID"                  0x00DD7124 "wargodMatchStateUpdateTime"
0x00738C14 call 0x7f9090 / call 0x50f410       （属性/配置读写）
0x00738D63 call 0x801320 / [0x84ABB08]         （赛季对象）
```

无 socket、无 endpoint、无 DTLS。**NOT_BATTLE_LISTENER（CONFIRMED）**

### 6.2 `0x007CAF30`（listener #5）

```asm
0x007CAF36  mov ecx,[0x82e13fc] / call [ecx.vt+0x5C]     ; 同一网络对象守卫
0x007CAF55  cmp byte [ebp+8], 0                          ; arg1
0x007CAF82  call 0x730280                                ; ★ UI 事件投递，事件 id = 6
0x007CAFBE  call [matching.vt+0x5C] / call [matching.vt+0x54]
0x007CB005  call 0x730280                                ; 事件 id = 0x65
0x007CB043  mov esi,0xddce94 "cppWebCloseCurrentPage"    ; ★ CEF 内嵌网页
0x007CB048  call 0x4f7150 / 0x730490                     ; CEF 调用
```

`0x730280` = UI 事件分派器（构造含 `"Object"` / `"id"` 字段的事件对象，
再 `call [vt+0x14]`）⇒ **UI 层**。无 socket。**NOT_BATTLE_LISTENER（CONFIRMED）**

### 6.3 `0x004F7590`（listener #1/#2/#4/#6）

`ret 8`。调用后 `eax` 未被检查（`0x632841` 之后直接 `test edi,edi`）⇒
对 accepted/失败通知**完全无副作用**。**NOT_BATTLE_LISTENER（CONFIRMED）**

### 6.4 旁证：这些 listener 真正重写的槽位都不是 +0x24

| vtable | 覆盖槽位 |
|---|---|
| `0x00DC787C` | +0x00 `0x6380A0`、+0x04 `0x638130` |
| `0x00DCECEC` | +0x18 `0x6C04E0`、+0x1C `0x6C0490` |
| `0x00DDCBDC` | +0x00 `0x7C45E0`、+0x04 `0x7C4650`、+0x10 `0x7C4760` |
| `0x00DDCF2C` | +0x04 `0x7CB330`、+0x08 `0x7CB350`、+0x20 `0x7CBAB0`、+0x24 `0x7CAF30` 等 |

其中 `0x7C4760`（= listener #4 的 `+0x10`，由 §3.4 的 `0x62DD60` 广播触发）为：

```asm
0x007C4760  cmp dword [ebp+8], 5      ; arg1 == 5
0x007C4767  jne 0x7c4779
0x007C4771  call 0x7C4CE0             ; (arg4, arg5)
0x007C477A  ret 0x14
```

---

## 7. ACCEPTED 分支的非 listener 出口（复核 014，非 Battle）

```
0x771320  遥测/日志发射（事件描述符 0x00DC74F8）
0x6297A0  = vt+0x150，strlen thunk -> vt+0x14C（0x629730）
0x629730  序列化（call 0x769710）+ 入队 [esi+0x3a0b0]（call 0x6568F0）
0x62C580  = vt+0x148，状态迁移
0x62F6C0  复位 A/B
0x62FDE0  = vt+0x5C，网络对象守卫（见 §2）
0x6293B0  由 reservation item 构造会话记录；内部 call 0x801960 / 0xb95c50 / 0xb74bc0
0x629F80  门控 [esi+0x281] / [esi+0x105d8] / [esi+0x245]；
          -> 0x629860（搬运 [ebx+0x190] 名字、[ebx+0x188/0x18c] 字段）
          -> 0x7F49A0（call 0x803830 → 0xb7a670 == 2 → 0xb7a800），仅查询/比较，不建 socket
0x655930  清理
```

`0x804A82` 端口候选表 / `0x818DE0` 状态机 / `0x803830` 传输类型查询属于**下游**，
不在 accepted 分支的直接调用面内；不因出现 28960 就认定 Battle（遵守任务 §11）。

---

## 8. BATTLE_MODULE_ENTRY / UDP_SOCKET（本轮静态结果）

```
BATTLE_MODULE（DTLS/ECDH/secp224）字符串区 = 0xD3D628 / 0xD55DB0 / 0xD5611C（确认存在）
  但它们是 **OpenSSL 0.9.8p 的 ERR reason 字符串表 + 密码套件名表**，
  不是 Battle code 入口；对它们的 dword 引用全部落在数据表内，无代码 xref 可达。

UDP_SOCKET_CREATE       = 已定位 4 处（见 §12），但**无法证明哪一处属于 Battle**
UDP_SOCKET_CALLER_CHAIN = PARTIAL（见 §12.3，向上只追到 0xA0542B / 0xA2F953 / 0x9FDC68）
GAME_IP_STORAGE         = socket 对象 +0x08（网络序，CONFIRMED）；
                          session 侧候选 +0x18（CANDIDATE）
GAME_PORT_STORAGE       = socket 对象 +0x06（网络序，CONFIRMED）；
                          session 侧候选 +0x1C（HOST 序，CANDIDATE）
```

本轮**没有**声称任何 accepted → listener → socket 的链路；
accepted 分支的直接调用面内不存在任何 socket API 调用。

---

## 9. ACCEPTED_TO_BATTLE_PATH

```
0x00632680 accepted
  ├─ [this+0x288]=1 / [0x0849B61C]=1                （状态，UI）
  ├─ vt+0x150 → vt+0x14C → 序列化入队 [this+0x3a0b0] （消息队列；006/014 已证非 Battle 直连）
  ├─ vt+0x148 状态迁移
  ├─ vt+0x5C 守卫（存在类型 2 网络对象则跳过广播）
  ├─ listener 广播 +0x24
  │     ├─ 5/7 → 0x004F7590（空实现）                ✗
  │     ├─ 1/7 → 0x00738E70（wargod 排位数据刷新）    ✗
  │     └─ 1/7 → 0x007CAF30（UI / CEF 内嵌网页）      ✗
  └─ 0x6293B0 / 0x629F80 / 0x655930（会话记录 + 状态门控 + 清理）
```

整条链上**没有**任何 socket()/WSASocket()/sendto()/recvfrom()/bind()、
没有任何 DTLS/ECDH 调用、没有 28960 常量或 IP:port 消费点。

---

## 10. BATTLE_TRIGGER_PATH 判定

```
BATTLE_TRIGGER_PATH = UNRESOLVED

其中「accepted → listener → Battle」这一具体假说 = REFUTED
（7 个 listener 的 +0x24 全部锁定：5 个空实现 + 2 个排位/UI，无一进入 Battle。）

LISTENER → BATTLE =
  listener #1 (0xDC787C) : REFUTED（+0x24 = ret 8 空实现）
  listener #2 (0xDCECEC) : REFUTED（+0x24 = ret 8 空实现）
  listener #3 (0xDD7194) : REFUTED（wargod 排位模块 0x73xxxx）
  listener #4 (0xDDCBDC) : REFUTED（+0x24 = ret 8 空实现）
  listener #5 (0xDDCF2C) : REFUTED（UI / CEF 模块 0x7Cxxxx）
  listener #6 (0xDC7E6C) : REFUTED（+0x24 = ret 8 空实现）
  listener #7 (0xDC78EC) : REFUTED（+0x24 = ret 8 空实现）
⇒ 7/7 REFUTED，无 CANDIDATE 残留
```

---

## 11. 证据等级表

| 项 | 地址 | 等级 |
|---|---|---|
| accepted 广播 site / ABI | `0x632824`..`0x632844`（1,0）/ `0x6328A5`..`0x6328B3`（0,2） | CONFIRMED |
| 广播被 `vt+0x5C` 门控 | `0x63281E` / `0x632822` / `0x62FDE0` | CONFIRMED |
| listener 容器 = `[0x82E13FC]+4`，head/tail/count | `0x632824` / `0x724EB0` | CONFIRMED |
| node = {value,next,prev}，0xC 字节 | `0x724EB3` / `0x724EC6` / `0x724EFB` / `0x724EFE` | CONFIRMED |
| 插入 helper | `0x00724EB0` | CONFIRMED |
| 删除 helper | `0x00623460` | CONFIRMED |
| 7 个注册点 | §4.2 表 | CONFIRMED |
| listener #1 vtable / +0x24 | `0xDC787C` / `0x4F7590` | CONFIRMED |
| listener #2 vtable / +0x24 | `0xDCECEC` / `0x4F7590` | CONFIRMED |
| listener #3 vtable / +0x24 | `0xDD7194` / `0x738E70` | CONFIRMED |
| listener #4 vtable / +0x24 | `0xDDCBDC` / `0x4F7590` | CONFIRMED |
| listener #5 vtable / +0x24 | `0xDDCF2C` / `0x7CAF30` | CONFIRMED |
| listener #6 vtable / +0x24 | `0xDC7E6C` / `0x4F7590` | CONFIRMED |
| listener #7 vtable / +0x24 | `0xDC78EC`（写入点 `0x63B4B1`）/ `0x4F7590` | CONFIRMED |
| `0x738E70` = wargod 排位刷新 | `0x738E70`→`0x738BF0/0x738D00/0x737430` + 字符串 | CONFIRMED |
| `0x7CAF30` = UI/CEF | `0x7CAF30` + `"cppWebCloseCurrentPage"` + `0x730280` | CONFIRMED |
| `0x4F7590` = `ret 8` 空实现 | `0x4F7590` | CONFIRMED |
| accepted → listener → Battle | — | **REFUTED（7/7）** |
| accepted 直接 connect 28960 | — | REFUTED（承接 006/014） |
| Lobby 路径 `0xB81EF0→0xBA4080` | — | 排除，未重走 |
| senderId / A-B | — | 已关闭，未重走 |
| `_cleanout\dump_*.bin` 含本模块映射 | — | REFUTED（内容检索零命中） |
| ws2_32 IAT 槽位（socket/htons/inet_addr/…） | `0xCA84D4..0xCA855C` | CONFIRMED（§12.1） |
| UDP socket 创建点 ×4 | `0xC65410` / `0xBB18B0` / `0xC7BB00` /（TCP 族）`0xC7BAF0` | CONFIRMED（§12.2） |
| socket 对象布局 + setter/bind | `0xD8E3A8` 类；`0xC65650/0xC65690/0xC656D0/0xC65440` | CONFIRMED（§12.4） |
| 28960 非客户端常量 | `0x00007120` 仅在 `0xD9453A`/`0xD94597`（OpenSSL 数据） | REFUTED（§12.6） |
| `0x77FBF0` 非 Battle（IPX LAN 广播） | `socket(6,2,1000)` @`0x77FBF0` | REFUTED（§12.6） |
| bdAddress ip/port 候选 | session `+0x18` / `+0x1C`，读点 `0x77DC69` | CANDIDATE（§12.5） |
| 4 个 socket 点到 matching / Battle 的向上链 | `0xA0542B` / `0xA2F953` / `0x9FDC68` / `0xC73E60` | UNRESOLVED |

---

## 12. OUT-OF-BAND：UDP / Battle socket 侧（并行静态核查，已并入）

> 本节由一次**并行的静态子任务**产出，方法论与主报告一致（纯静态、只读、指令级证据）。
> 所有 VA 均为镜像 VA（base 0x400000）。它**没有**建立 accepted→socket 的链路。

### 12.1 IAT 槽位识别（ws2_32，CONFIRMED）

PE 导入目录被剥掉（`DataDirectory[1].Size = 0`，节名 `.tp3`），
但 ws2_32 的槽位由壳在运行期填好，位于 `0xCA84D4..0xCA855C`：

```
0xCA8534 WSAStartup   0xCA8538 gethostname  0xCA853C WSAGetLastError  0xCA855C gethostbyname
0xCA8548 socket       0xCA8554 bind         0xCA8558 setsockopt        0xCA854C ioctlsocket
0xCA8550 htons        0xCA8540 inet_addr    0xCA8504 htonl             0xCA851C sendto
0xCA84E0 send         0xCA84E4 recv         0xCA84E8 select             0xCA8500 accept
0xCA84D4 ntohs        0xCA8544 closesocket
```

证据：`0xC65414 push 0x11 / push 2 / push 2 / call [0xCA8548]`（UDP socket）；
`0xC656F1 call [0xCA8550]` → `mov word [esi+6], ax`（htons→sin_port）；
`0xC656FF call [0xCA8540]` → `mov [esi+8], eax`（inet_addr→sin_addr）；
`0x621B2C push 0x81A9F70 / push 0x101 / call [0xCA8534]`（WSAStartup）。

### 12.2 UDP_SOCKET_CREATE = 4 处（无一处可证属于 Battle）

| VA | 指令 | 说明 |
|---|---|---|
| `0x00C65410` | `push 0x11 / push 2 / push 2 / call [0xCA8548]` | socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP)；fd → `[esi+0x14]`（arg==0 时另存 `[esi+0x18]`）。__thiscall，属 vtable `0xD8E3A8` 的 **+0x08** 槽；同族 `0xC653D0`（+0x04）= `push 6 / push 1 / push 2` 为 TCP。对象 0x24 字节，工厂 `0xC65D70`。**CONFIRMED** |
| `0x00BB18B0` | `push 0x11 / push 2 / push 2 / call [0xCA8548]` | 随后 `call 0xBB12A0(arg1,arg2,sock)`，返回 fd。**CONFIRMED** |
| `0x00C7BB00` | `push 0 / push 2 / push 2 / call [0xCA8548]` | socket(AF_INET, SOCK_DGRAM, 0) 裸helper。**CONFIRMED** |
| `0x00C7BAF0` / `0x00C7BB10` | `push 0/push 1/push 2`；`push 0/push eax/push 1` | TCP / AF_* helper。**CONFIRMED** |

### 12.3 UDP_SOCKET_CALLER_CHAIN（仅指令级可证的跳）

```
(socket) 0xBB18B0  ← 0xC73E77（函数 0xC73E60：cmp [esi+4],-1；成功 mov [esi+4],eax）
                   （类 vtable 0xD95538，由 0xC73E30 安装）           CONFIRMED
(socket) 0xC65410  ← 工厂 0xC65D70（push 0x24; call [eax+0x28]; mov [eax],0xD8E3A8）
                   ← 类名注册项 0xE495E4 = {0xD8E334, 0x505, 0xD8E468="socket", ...}
                     0xD8E338 处 dword = 0xC65D70                     CONFIRMED
                   ← 描述符由 0xC65340（mov eax,0xE495E4; ret）取出
                   ← 被 0xA2F953 调用（虚分派，无 E8 直调）            CANDIDATE
bdSocket::connect 0xC65220（日志 "Socket connection established on port %d"
                   @0xD8E2BC / "Could not create socket. Error %d" @0xD8E310）
                   ← 0xA0542B（兄弟 0xC65190 ← 0x9FDC68）             CANDIDATE
向上到 0x818DE0 / 0x6334xx / 0x62xxxx                              UNRESOLVED
```

### 12.4 socket 对象布局（类 vtable `0xD8E3A8`，CONFIRMED）

```
+0x00 vtable           +0x04 sockaddr_in: word[+4]=AF_INET, word[+6]=htons(port),
                                        dword[+8]=inet_addr(ip), +0xC..+0x13 = 0
+0x14 fd               +0x18 fd2         +0x1C / +0x20 misc
setter: 0xC65650(+0x2C) SetPort       0xC65690(+0x30) SetBroadcastAddr(INADDR_BROADCAST)
        0xC656D0(+0x34) SetAddr(port,ipstr)   0xC65710(+0x3C) FIONBIO
        0xC65740(+0x38) SO_BROADCAST    0xC655E0 sendto / 0xC65560 send / 0xC655B0 recv
bind:   0xC65440 push 0x10 / lea eax,[ecx+4] / push eax / push [ecx+0x18] / call [0xCA8554]
        0xC65480 同上但用 [ecx+0x14]
```

### 12.5 GAME_IP_STORAGE / GAME_PORT_STORAGE

```
socket 对象内：IP @ +0x08，PORT @ +0x06，均为网络序                    CONFIRMED
session 侧候选：0x77DC69..0x77DC91 读 movzx [ebx+0x18..0x1B] + movzx word [ebx+0x1C]，
    用 "%u.%u.%u.%u:%u (BD_NULL)"（@0xDDBAB8）格式化
    ⇒ 4 字节 IP @ +0x18，2 字节 PORT @ +0x1C（HOST 序）                CANDIDATE
    （未观察到该结构被拷进 sockaddr）
本地 endpoint 构造器 0x621B00（← 0x621587）：WSAStartup → gethostname/gethostbyname
    → 写 mov word [ebx+2], ax/dx（0x621C63/0x621C6E），127.0.0.1 兜底
    ⇒ 这是 **LOCAL/loopback**，不是比赛服                          CONFIRMED
```

### 12.6 本节 REFUTED

```
REFUTED: 0x77FBF0 是 Battle socket
   push 0x3E8 / push 2 / push 6 / call [0xCA8548] = socket(AF_IPX=6, SOCK_DGRAM, NSPROTO_IPX=1000)
   + setsockopt(SO_BROADCAST)@0x77FC58 + ioctlsocket(FIONBIO)@0x77FC3F
   + bind(len=0xE) on mov word [ebp-0x14],6 → 14 字节 sockaddr_ipx；
   端口来自配置键 "Network Port"/"1109"（0x77FCD5-0x77FCE4）→ 结果存 [0x81A9F1C]
   ⇒ LAN/system-link 广播 socket
REFUTED: 28960 是客户端常量
   dword 0x00007120 仅出现在 0xD9453A / 0xD94597（OpenSSL 数据内），无代码上下文；
   亦无 8300-8316 / 8400 / 8600 的代码常量
REFUTED: 存在 ws2_32 动态名表
   字符串 "WSASocketA/W" / "sendto" / "recvfrom" / "WS2_32.dll" / "ws2_32" 在镜像内不存在；
   "WSAStartup"@0xD90B14 / "WSASTARTUP"@0xD90D40 / "WSAstartup"@0xD950EC /
   "ioctlsocket"@0xD95100 都是 OpenSSL 0.9.8p 的 error/reason 字符串数组
REFUTED: \dpnet.dll@0xDD9834 / \dplayx.dll@0xDD9874 / wpcap.dll@0xDE1658 是 socket 导入
   分别是 DirectPlay/DirectShow DLL 名表，以及 "ClientOffline*" 记录器用的
   pcap 名称表（pcap_findalldevs/open_live/setnonblock/compile/setfilter/next_ex）
REFUTED: 0xC5D2C4 / 0xC5D2D0 是 socket 创建点（只是 jmp [0xCA8528] / jmp [0xCA84E0] 裸 thunk）
UNKNOWN : "dgram"@0xD9E830 属 OpenSSL BIO method 名表；未穷尽排除 BIO_new_dgram/SSL_set_bio
```

### 12.7 本节 BATTLE_MODULE_ENTRY = UNRESOLVED

最外层的 UDP 侧函数只到 `0xC73E60 → 0xBB18B0 → socket()` 与
`0xC65D70 / 类 0xD8E3A8 → 0xC65410 → socket()`；
**没有任何指令级证据把其中任一接到 Battle endpoint**。

> 方法论警告（留给接力者）：capstone 的 `disasm()` 遇到首个非法字节即停止，
> 因此 `_015_lib.dis()/show()` 在起点落在指令中间或数据上时会**静默返回空**；
> 请改用子任务新增的 `_015_dis2.py`（resync）。`_015_glob.py` 对数据 xref
> 可能选中假指令（已在 0xD8E3A8 上验证过一次假阴性）。

---

## 13. NEXT_GATE

```
1. listener 侧已完全收口（7/7 REFUTED，无 UNKNOWN 残留）：
   **不要再去 [matching+4] 找 Battle**，这条轴已死。
   唯一注意：`0x632824` 的广播还被 `matching->vt+0x5C`（`0x62FDE0`）门控，
   运行期"没有类型 2 网络对象"时才广播；这与 012 观察到的 RX=0 无矛盾关系。

2. accepted → Battle 的断点不在 listener，需换轴（两条独立轴并行）：
   a) 【UI/net 对象轴】0x629F80 → 0x7F49A0 → 0x803830 / 0xb7a670 / 0xb7a800，
      查清 0xb7xxxx 里的"类型 2 对象"到底代表哪种 transport（TCP/UDP/IPC）。
   b) 【socket 轴，§12 已给锚点】从已确认的 UDP 创建点反向找 caller：
      0xA0542B（→ bdSocket::connect 0xC65220）
      0xA2F953（→ 类描述符 0xC65340 / 0xE495E4 "socket"）
      0x9FDC68（→ 0xC65190）
      0xC73E60 的 caller（→ 0xBB18B0 → socket）
      0x481AD0（"matchqual,me %s,host %u.%u.%u.%u,ping %i,..." @0xDB5B80）
      目标：把上述任一接到 0x6334xx / 0x818DE0 / 0x62xxxx（matching）或
      0x77DC69 的 BD_NULL ip:port 结构（+0x18 / +0x1C）。
   c) 独立轴：确认 game server socket 是否属于 IW-engine netcode
      （与 Demonware bdSocket 0xD8E3A8 类并存）。

3. 明确**不要**因为 §12 找到 socket 就宣布 Battle —— 4 个创建点没有一个是
   Battle 的证明；必须由 caller 链 + endpoint 数据流双向证成。

4. 下一阶段建议命名：
   PVE-BATTLE-UDP-DYNAMIC-016（动态）
   CLIENT-BATTLE-TRANSPORT-STATIC-016（静态：0xA0542B / 0xA2F953 / 0xC73E60 / 0x481AD0）
```

---

## 14. 纪律核对

```
client 修改 / server 修改 / senderId 修改 / booking response 修改 = 无
SessionId 修改 / 28960 修改 / Battle server 修改              = 无
hook / patch / fake UDP / fake DTLS / ACE-TenProtect bypass   = 无
动态实验 / 启动游戏 / 发包                                     = 无
新增文件：仅 DEV-BOOKING\scripts\_015_*.py（只读分析脚本）与本报告
只读访问了 COD OL\codoMP_client_shipRetail.exe（PE 节表 + section[2] 只读）
并行子任务同样为纯静态只读，未修改任何目标文件
```

---

## 15. 本轮新增工具（只读，供后续接力）

```
DEV-BOOKING\scripts\_015_lib.py       镜像加载 / dis / refs / vtable / disp 扫描
DEV-BOOKING\scripts\_015_sweep.py     resync 线性反汇编，定位 [reg+disp] 访问
DEV-BOOKING\scripts\_015_ctx.py       对任意 VA 输出对齐后的指令窗口
DEV-BOOKING\scripts\_015_func.py      回溯函数起点（int3 填充定位）
DEV-BOOKING\scripts\_015_str.py       字符串 + VA
DEV-BOOKING\scripts\_015_hex.py       dword + ascii 转储
DEV-BOOKING\scripts\_015_glob.py      全局变量引用分类（读/写）
DEV-BOOKING\scripts\_015_col.py       RTTI COL -> 类名
DEV-BOOKING\scripts\_015_exe.py       读原版 EXE（含 section[2] 明文数据区）
DEV-BOOKING\scripts\_015_vtables.py   vtable 枚举
DEV-BOOKING\scripts\_015_walk.py      链式虚调用遍历点扫描
DEV-BOOKING\scripts\_015_vcall_singleton.py  单例上的虚调用点
--- 并行 UDP/Battle socket 静态核查新增（同目录，均只读）---
DEV-BOOKING\scripts\_015_index.py     全局对齐指令索引 -> _015_idx.pkl（约 404 万条）
DEV-BOOKING\scripts\_015_dis2.py      resync 反汇编（推荐，规避 disasm 提前中止）
DEV-BOOKING\scripts\_015_iatxref.py   IAT 槽位引用
DEV-BOOKING\scripts\_015_wordwrite.py word 写入点
DEV-BOOKING\scripts\_015_storeimm.py  立即数存储点
DEV-BOOKING\scripts\_015_dw.py / _015_refrange.py / _015_bytes.py / _015_sockaddr.py
DEV-BOOKING\scripts\_015_probe_dumps*.py  大 dump 是否含本模块（结论：不含）
```
