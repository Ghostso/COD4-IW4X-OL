# -*- coding: utf-8 -*-
import os, hashlib
wd=r"D:\BaiduNetdiskDownload\使命召唤OL\E11_GAMESTATE_SUBFRAME_001"
F={}

F["01_GAMSTATE_CONSUMER_CHAIN.md"]=r"""# 01 — Gamestate 消费链 / GAMESTATE CONSUMER CHAIN

> 只读静态分析。未启动游戏/服务端，未注入，未读进程内存，未修改样本。
> 客户端 SHA256 `353754047DBBFE3AFBF6C7D97DE3FACA785B3D5D5E34A9053C820EE78814D6E1`
> 恢复镜像 ImageBase `0x400000`；服务端 ImageBase `0x400000`。
> 等级：`DIRECT` / `CROSS` / `INFERRED` / `BLOCKED`
> **方法学更正：** E-10 的 `t01` 误把 VA 传给 `bytes_rva`，字符串探测全为 None。E-11 统一用 `VA - ImageBase` 换算。

---

## 1. 顶层 opcode 分派器（本轮新定位，DIRECT）

`0x350170` 是顶层消息分派器：

```asm
350170  push ebp / mov ebp,esp / and esp,0xfffffff8
350188  mov edx,[eax+0x89244]        ; 可插拔读取函数指针
35018E  lea ecx,[esp+0x13]
350192  push 1                        ; 读 1 字节
350195  call edx                      ; 读取 opcode
350197  mov al,[esp+0x1b]
35019E  test al,al
3501A0  jne 0x7501EC                  ; al != 0 → 分派
3501EC  movzx eax,al
3501EF  dec eax                       ; value - 1
3501F0  mov esi,1
3501F5  cmp eax,3
3501F8  ja  0x750245                  ; 越界 → EXE_ERR_PROCESS_DEMO_FILE_FAILED
3501FA  jmp dword [eax*4 + 0x75025C]  ; 4 项跳转表
```

**跳转表 `0x75025C`（DIRECT）：**

| wire 值 | 表项 RVA | 目标 | 语义 |
|---|---|---|---|
| 1 | `0x350227` | `0x350040` | 读取 0x40 字节定长记录块 |
| 2 | `0x350201` | `0x34FD80(0)` | 长度前缀 + 载荷 |
| 3 | `0x350214` | `0x34FD80(1)` | 长度前缀 + 载荷 + 额外 4 字节 |
| 4 | `0x350238` | `0x3547D0` | **内部子帧循环** |

**关键（DIRECT）：** 顶层 wire opcode 域为 **1..4**；`0` 走特殊路径，`>4` 走 `EXE_ERR_PROCESS_DEMO_FILE_FAILED`。

## 2. 与既有结论的冲突及更正

| 既有 | 本轮 | 依据 |
|---|---|---|
| E-08/E-10：顶层 `0x03` = Gamestate | **wire opcode 3 是四类顶层消息之一**，但不是唯一；`0x03` 由 `0x34FD80(1)` 处理 | `0x35025C` 表项 |
| E-10：`0x354100` 是外层分派器 | `0x354100` 是 **`0x3547D0` 内部**的子帧分派器；顶层分派器是 `0x350170` | 调用边 `0x350238→0x3547D0→0x354809→0x354100` |
| E-10：case 6 = Configstring | 保持：case 6 进入 `0x352F80→0xA2660`（见 `03`） | DIRECT |

## 3. 读取原语：可插拔函数指针（DIRECT）

`[client+0x89244]` 是**读函数指针**，两处赋值：

| 位置 | 值 | 场景 |
|---|---|---|
| `0x35141E` | `mov [ecx+0x89244], 0x752570` | 网络/实时路径 |
| `0x3515D9` | `mov [eax+0x89244], 0x74F090` | demo/回放路径 |
| `0x356701` | `mov [esi+0x89244], 0x74F090` | demo/回放路径 |

- `0x352570(dst,len,handle)`：把 `len` 字节复制到全局环形缓冲 `[edi+0x8048]`，并把 `[edi+0x30AF30]` 前进 `len`（DIRECT）。
- `0x34F090(dst,len,handle)`：demo 读取，失败时 `push 0xCD6328`（`EXE_ERR_READING_DEMO`）（DIRECT）。

**含义：** 分派器与读取器解耦；同一分派器在实时与回放两种输入下复用。

## 4. `0x34FD80` 逐字段拆解（DIRECT）

```asm
34FDB0  call [edi+0x89244]  len=4   ; f0 = dword
34FDC4  cmp byte [ebp+0xc],0
34FDD0  call [edi+0x89244]  len=4   ; f4 = dword（仅 opcode 3 分支）
34FE3F  call [edi+0x89244]  len=4   ; f8 = length
34FE81  cmp eax,0x20000             ; 长度上限检查
34FE8D  push 0xCD637C               ; 超限报错字符串
34FEAC  call [edi+0x89244]  len=f8  ; 载荷
34FEB7  cmp [ebp-0x20034],4         ; 载荷 ≥ 4 ?
34FED4  call MSG_ReadData   len=4   ; 内嵌 dword
34FF18  mov [edi+0x144], ecx        ; 保存
34FF39  ... 写入 [esi+0x4231F8] 记录 ...
350024  call 0x751D00
```

**结论（DIRECT）：** `0x34FD80` 是**长度前缀的分片消息消费者**（读 4 字节长度 → 读该长度载荷 → 校验 ≤0x20000 → 解析内嵌 4 字节）。它不解析 cstring，也**不**直接处理 Configstring 子帧。

## 5. 服务端对照（DIRECT）

`_CODOL2697_WriteGamestate` `0xA21B8`：

```asm
0A224C  WriteByte(3)              ; 顶层 opcode
0A225A  WriteInt32(version)       ; 4 字节
0A2269  WriteLenStr(map)          ; cstring
0A2279  WriteLenStr("mp")         ; cstring
0A2288  WriteInt32(field4)        ; 4 字节
0A22C1  call WriteConfigstrings   ; 子帧 0x04 ... 0x06
0A22D9  WriteInt32(fieldC)
0A22E8  WriteInt32(field8)
0A22F8  WriteByte(6)              ; 顶层尾
```

`WriteConfigstrings` `0xA0468` 内：`0xA07F8 WriteByte(4)` … `0xA0997 WriteByte(6)`（唯一调用者 `0xA22C1`，DIRECT）。

**两侧对照缺口：** 服务端 `0x03` 的**顶层**消息体是 `{i32, cstring, cstring, i32, <cfgsub>, i32, i32, 0x06}`；客户端 `0x34FD80(1)` 读的是 `{i32, i32, u32 len, payload}`。两者字段序**不一致** → 说明 `0x34FD80` **不是** `0xA21B8` 的对应消费者。

## 6. 裁定

| 项 | 裁定 |
|---|---|
| 顶层分派器已定位 | **PROVEN**：`0x350170` + 表 `0x75025C`（值 1..4） |
| 读取原语可插拔 | **PROVEN**：`[+0x89244]` ∈ {`0x352570`,`0x34F090`} |
| `0x03` 的客户端消费者 | **BLOCKED**：`0x34FD80(1)` 字段序与服务端 `0xA21B8` 不匹配 |
| 是否需继续扩大搜索 | 需在 `.text` 中定位真正的 `{i32,cstring,cstring,i32}` 消费者（见 `07` G-11-1） |
"""

F["02_SUBFRAME_CURSOR_AND_LOOP.md"]=r"""# 02 — 子帧游标与循环 / SUBFRAME CURSOR AND LOOP

> 等级：`DIRECT` / `INFERRED` / `BLOCKED`

---

## 1. 子帧分派器 `0x354100`（DIRECT）

```asm
354100  push ebp / mov ebp,esp
354117  mov eax,[0x7454988]
35411C  mov eax,[eax*4+0x1A65E0C]
354123  xor eax,0x20FD39B9
354150  movzx eax, byte [ebp+0xc]     ; 子帧编号
35415A  cmp eax, 8
35415D  ja  0x75479A                  ; 越界直接返回
354163  jmp dword [eax*4 + 0x7547AC]  ; 9 项跳转表
```

**跳转表 `0x7547AC`（DIRECT）：**

| 编号 | 目标 | 读取 |
|---|---|---|
| 0 | `0x35416A` | 1 字节 → 格式化 |
| 1 | `0x3541C4` | 4 字节 → float |
| 2 | `0x354200` | 1 字节 |
| 3 | `0x354264` | 1 字节 + 分支 |
| 4 | `0x354366` | 1 字节 + 3×float |
| 5 | `0x354468` | 4 字节 + 4 字节 |
| **6** | **`0x354697`** | **u32 len → len 字节载荷 → `0x352F80`** |
| 7 | `0x354740` | 1 字节 → `[esi+0x723C24]` |
| 8 | `0x354766` | 4 字节 |

## 2. 子帧循环 `0x3547D0`（DIRECT）

```asm
3547DF  mov ebx,1
3547ED  mov ecx,[esi+0x89244]
3547F3  push ebx / push eax / call ecx    ; 读 1 字节 → [ebp-4]
3547F7  mov eax,[ebp-4]
3547FD  cmp al,9
3547FF  je  0x75482A                      ; 9 → 退出检查
354801  cmp al,0xA
354803  je  0x75482E                      ; 10 → 返回 0
354805  push 1 / push eax / push edi
354809  call 0x754100                     ; 以该字节为子帧编号分派
35480E  mov eax,[esi+0x89244]
354817  push edi / push 1 / push [ebp-4]
35481E  call eax                          ; 再读 1 字节
354820  mov eax,[ebp-4]
354826  cmp al,9
354828  jne 0x754801                      ; 继续
35482A  cmp al,0xA
35482C  jne 0x754836
35482E  xor eax,eax / pop / ret           ; 返回 0
354836  mov eax,ebx / pop / ret           ; 返回 1
```

**游标关系（DIRECT）：**

| 步骤 | 读取 | 游标推进 |
|---|---|---|
| 入口 | 1 字节 = 子帧编号 | +1 |
| 子帧处理 | 由 case 决定 | 见 `03` |
| 每轮末 | 再读 1 字节 | +1 |
| 退出条件 | 读到 `0x09` 或 `0x0A` | — |

**关键（DIRECT）：** 循环**不是**由 `0x04`/`0x06` 驱动的；退出值是 `0x09`/`0x0A`。子帧编号来自每轮首字节，范围 0..8（越界直接返回）。

## 3. 循环的两条进入路径

| 路径 | 进入点 | 上游 |
|---|---|---|
| A | `0x350238 call 0x3547D0` | `0x350170`（顶层 opcode 4） |
| B | `0x351569 call 0x3547D0` | `0x3512A0`（网络 Gamestate 候选） |

两条路径在 `0x3547D0` 汇合，共用同一 9 项子帧分派器（DIRECT）。

## 4. `0x3512A0` 的游标序列（DIRECT）

```asm
35141E  mov [ecx+0x89244], 0x752570      ; 安装网络读取器
351433  push 4                            ; 读 4 字节
35143C  call 0x752570
351484  push 4                            ; 再读 4 字节
3514A3  call 0x752570
3514B6  call 0x752570                     ; 读长度字节载荷
3514F0  call 0xA2660                      ; Configstring body reader
3514F6  call 0x352FC0
351504  call 0x3530E0
35150D  call 0x3532F0
351516  call 0x3537D0
351561  push 1 / call [edx+0x89244]       ; 再读 1 字节
351569  call 0x3547D0                     ; 子帧循环
```

**`0x3512A0` 与 case 6 的后继完全一致**（`0x352FC0`/`0x3530E0`/`0x3532F0`/`0x3537D0`），说明二者是同一条消息链的两个入口（DIRECT）。

## 5. 裁定

| 项 | 裁定 |
|---|---|
| 子帧分派器与编号范围 | **PROVEN**（`0x354100`，0..8） |
| 子帧循环退出值 | **PROVEN**（`0x09`/`0x0A`） |
| 每轮字段宽度 | **PROVEN**（首字节 1 字节编号；case 内宽度见表） |
| 循环与 `0x04`/`0x06` 的耦合 | **REFUTED**：退出由 `0x09`/`0x0A` 决定 |
"""

F["03_CASE6_CONFIGSTRING_CHAIN.md"]=r"""# 03 — case 6 与 Configstring body 链 / CASE 6 CHAIN

> 等级：`DIRECT` / `CROSS` / `INFERRED` / `BLOCKED`

---

## 1. case 6 完整指令（DIRECT）

```asm
354697  push 0x20000
35469C  lea ecx,[ebp-0x2000C]
3546A2  push 0 / push ecx
3546A5  call 0xB50900                    ; memset 256KB 缓冲
3546AD  lea edx,[ebp-0x2000C]
3546B3  push 0x20000 / push edx
3546B9  lea esi,[ebp-0x20060]
3546BF  call 0x1AC190                    ; MSG_InitReadOnly(buf,0x20000)
3546C4  mov ecx,[edi+0x89244]
3546CB  lea eax,[ebp-0x2004C]
3546D1  push 4                            ; 读 4 字节
3546D4  call ecx                          ; → [ebp-0x2004C] = LEN
3546D6  mov edx,[ebp-0x2004C]             ; edx = LEN
3546DC  mov eax,[ebp-0x20058]             ; eax = msg.buf
3546E2  mov ecx,[edi+0x89244]
3546EB  push ebx / push edx / push eax
3546EE  call ecx                          ; 读 LEN 字节 → msg.buf
3546F3  call 0x352F80                     ; → 0xA2660
```

**语义（DIRECT）：** case 6 = `u32 LEN` + `LEN 字节载荷`，载荷被装入一个新的只读 MSG，然后交给 `0x352F80`。

## 2. `0x352F80` 的 +1 游标（DIRECT）

```asm
352F80  push 0x27760 / push 0 / push 0x1B47EE4
352F8C  call 0xB50900                    ; 清零状态
352F91  mov ecx,[esi+0x18]               ; msg.size
352F94  add ecx,[esi+0x14]               ; + offset
352F97  mov eax,[esi+0x1C]               ; msg.pos
352F9D  cmp eax,ecx
352F9F  jge 0x752FAC
352FA1  inc eax                          ; pos += 1
352FA2  mov [esi+0x1C],eax
352FA5  mov ecx,esi
352FA7  jmp 0xA2660                      ; → body reader
352FAC  mov dword [esi],1                ; 越界标志
352FB2  mov ecx,esi
352FB4  jmp 0xA2660
```

**关键（DIRECT）：** `0x352F80` 无条件把 msg 游标 **+1 字节**后才进入 `0xA2660`；越界分支也进入（只是先置错误标志）。

## 3. `0xA2660` 读取的第一个字段（DIRECT）

```asm
0A2693  mov ecx,[esi+0x18]
0A2696  mov eax,[esi+0x1C]
0A2699  add ecx,[esi+0x14]
0A269C  lea edi,[eax+2]                  ; pos+2
0A26A5  cmp edi,ecx
0A26AF  push 2                           ; 读 2 字节
0A26B2  call 0x1AC1D0                    ; MSG_ReadData
0A26B7  movsx eax,word [ebp-0x108]       ; 有符号 16 位
```

**即 `0xA2660` 进入后立刻读 2 字节 count1**（DIRECT）。

## 4. 与服务端的字段对照（CROSS）

| 步骤 | 服务端 | 客户端 | 一致 |
|---|---|---|---|
| 子帧头 | `WriteByte(4)` @0xA07F8 | `0x352FA1` +1 字节 | 位置一致（值未比较） |
| count1 | `WriteShort(count1)` @0xA0807（2B） | `push 2` + `MSG_ReadData` @0xA26B2 | ✅ |
| A1/A2/A3 | 见 `_CODOL2697_WriteConfigstrings` | `0xA2660` 内 `MSG_ReadBits` | ✅（字段级） |
| 子帧尾 | `WriteByte(6)` @0xA0997 | **未定位** | ❌ |

## 5. 长度前缀 `LEN` 的来源分析

case 6 先读 4 字节 `LEN`，再把 `LEN` 字节装进 MSG。服务端 `0xA22C1` 调用 `WriteConfigstrings` 时**没有**写任何长度前缀（`WriteByte(4)` 紧跟在 `WriteInt32(field4)` 之后）。

| 假设 | 证据 | 裁定 |
|---|---|---|
| `LEN` 是 Configstring 子帧的显式长度 | 服务端无对应写入 | **REFUTED** |
| `LEN` 属于外层分片/缓冲协议（非 `0xA21B8` 内） | case 6 在 `0x354100` 内，`0x354100` 由 `0x350170`/`0x3512A0` 驱动 | **INFERRED** |
| `LEN` 是 Gamestate 的某个 4 字节字段 | 服务端 `0xA2288 WriteInt32(field4)` 位置对应 | **INFERRED（候选）** |

**说明：** 客户端 `0x34FD80` 同样使用“u32 长度 + 载荷”包装，说明该客户端在**读取层**普遍使用长度前缀分片。因此 case 6 的 `LEN` 更可能是**读取层分片长度**，而非 Configstring 自身字段。

## 6. 裁定

| 项 | 裁定 |
|---|---|
| case 6 与 `0xA2660` 的连接 | **PROVEN**（`0x3546F3 → 0x352F80 → 0xA2660`） |
| `0x352F80` 的 +1 字节 | **PROVEN**（指令级） |
| 被跳过字节 = 服务端 `0x04` | **INFERRED**（位置一致，无值比较） |
| case 6 的 4 字节 `LEN` 语义 | **BLOCKED**（服务端无对应写入） |
| Configstring 字段序一致 | **CROSS**（count1/A1/A2/A3） |
| 子帧尾 `0x06` 客户端读取 | **BLOCKED** |
"""

F["04_OPCODE_04_VERDICT.md"]=r"""# 04 — 内部 0x04 裁定 / OPCODE 0x04 VERDICT

---

## 1. 裁定

| 问题 | 裁定 |
|---|---|
| `0x04` 是**显式读取**的标识字节 | **否**（在客户端链中未找到对 0x04 的读取+比较） |
| `0x04` 是**长度字段的一部分** | **REFUTED**（服务端 `WriteByte(4)` 是独立 1 字节写） |
| `0x04` 是**被跳过的上下文数据** | **INFERRED（强）**：`0x352FA1` 固定 +1 字节 |
| `0x04` 子帧识别方式 | **BLOCKED**（未证明确比较） |

## 2. 服务端写入侧（DIRECT）

```asm
0A07E6  mov dword [edi+0x10],0       ; bitpos = 0
0A07ED  mov dword [esp+4],4
0A07F5  mov [esp],edi
0A07F8  call 0x499551                ; WriteByte(msg,4)  —— 1 字节
0A07FD  mov eax,[ebp+0x14]
0A0807  call 0x499566                ; WriteShort(count1) —— 2 字节
```

- `0x99551`：`mov ecx,1` → `0x994FC` → `MSG_WriteData(len=1)`（DIRECT）。
- `WriteConfigstrings` `0xA0468` 的唯一调用者是 `0xA22C1`（DIRECT）。
- 因此 `0x04` 是 **Gamestate 内部子帧的 1 字节头**，位于 `WriteInt32(field4)` 之后、`count1` 之前。

## 3. 客户端侧证据

| 证据 | 位置 | 内容 | 等级 |
|---|---|---|---|
| 游标 +1 | `0x352FA1`–`0x352FA2` | `inc eax; mov [esi+0x1C],eax` | DIRECT |
| 紧接进入 body reader | `0x352FA7` | `jmp 0xA2660` | DIRECT |
| body reader 立刻读 count1 | `0xA26B2` | `push 2` + `MSG_ReadData` | DIRECT |
| 显式 `cmp ... 4` | 四区域扫描 | **命中 0** | DIRECT（否定） |
| 子帧编号与 0x04 的关系 | `0x3547D0` | 编号来自读到的字节，退出值为 `0x09`/`0x0A` | DIRECT |

## 4. "写入 0x04" 与 "客户端比较 0x04" 的区分

| 命题 | 证据 | 裁定 |
|---|---|---|
| 服务端**写入** `0x04` | `0xA07F8` WriteByte(4) | **PROVEN** |
| 客户端**明确比较/分派** `0x04` | 无 `cmp ... 4`、无跳转表以 4 为键 | **未找到（BLOCKED）** |
| 客户端**跳过** 1 字节后进入 body reader | `0x352FA1` | **PROVEN** |
| 被跳过的字节**就是** `0x04` | 仅位置一致 | **INFERRED（强）** |

**纪律：** 按任务 B 第 5 条，保留 `INFERRED`，**不升级为 PROVEN**。

## 5. 可能的识别机制（候选，未证）

| 候选机制 | 支持 | 反对 | 状态 |
|---|---|---|---|
| 调用方按长度前缀切分，子帧头位置隐含 | case 6 有 `u32 LEN` 前缀 | 服务端无长度前缀 | 候选 |
| `0x04` 在读取层被当作分片类型码 | `0x34FD80` 也用长度前缀 | 无 4 的比较 | 候选 |
| `0x04` 通过外层状态机隐式跳过 | `0x352F80` 无条件 +1 | 无条件意味着不校验值 | 候选 |

## 6. 最小新增证据

| ID | 缺口 | 最小证据 | 授权 |
|---|---|---|---|
| G-11-2 | `0x04` 值级识别 | 服务端 `0x04` 对应客户端 1 字节值比较，或 case 6 的 `LEN` 与子帧边界的等式 | 否（静态） |
| G-11-3 | 读取层分片协议 | 找到设置 case 6 `LEN` 的写入者 | 否（静态） |
"""

F["05_OPCODE_06_TERMINATION_VERDICT.md"]=r"""# 05 — 0x06 终止裁定 / OPCODE 0x06 VERDICT

---

## 1. 裁定

| 属性 | 裁定 | 依据 |
|---|---|---|
| 读取 | **BLOCKED** | 未定位客户端读取 `0x06` 的指令 |
| 位宽（8 bit） | **BLOCKED（客户端）**；服务端 **PROVEN** | 服务端 `WriteByte` = `mov ecx,1` |
| 字节对齐 | **BLOCKED** | 客户端读取点未知 |
| 消息层级 | **PROVEN（分层）** | `0xA0997` 子帧尾 vs `0xA22F8` 顶层尾，位置不同 |
| 终止语义 | **BLOCKED** | 无客户端退出分支证据 |

## 2. 服务端 `0x06` 全部写入路径（DIRECT）

全服务端 `WriteByte` 调用点共 43 处，其中值为 6 的有 **3 处**：

| 站点 | 所属函数 | 层级 |
|---|---|---|
| `0xA0997` | `_CODOL2697_WriteConfigstrings` `0xA0468` | **Configstring 子帧尾** |
| `0xA22F8` | `_CODOL2697_WriteGamestate` `0xA21B8` | **Gamestate 顶层尾** |
| `0xA4CAF` | Snapshot 写函数 | Snapshot 内标记（不同层） |

写入原语：`0x99551` → `0x994FC`（`mov ecx,1`）→ `MSG_WriteData(len=1)`，即 **1 字节**。

**纪律：** 三者数值相同但**层级不同**，按任务约束 5 禁止合并语义。

## 3. 客户端读取搜索（本轮）

| 搜索 | 范围 | 结果 |
|---|---|---|
| `0xA2660` 全函数 | `0xA2660..0xA2975` | 读完 A3 后 `ret`，**无 0x06 读取** |
| `cmp/sub == 6` | `0x340000-0x360000` | 命中均与字节流无关（如 `0x34D89C` 是计数比较、`0x34F304` 是数组长度） |
| `cmp/sub == 6` | `0xA0000-0xA3000` | 命中 3 处，均非消息读取 |
| 子帧循环退出 | `0x3547D0` | 退出值为 `0x09`/`0x0A`，**不是 6** |
| case 6 后继链 | `0x352FC0/0x3530E0/0x3532F0/0x3537D0` | `0x3532F0` 读 1 字节但比较的是 `0x81` |

**结论：** 在已追踪链内**未找到** `0x06` 的读取点。按约束 6，**不宣称客户端不存在该逻辑**，保留 BLOCKED。

## 4. 可能由长度边界/外层状态机隐式处理

case 6 的结构是 `u32 LEN + LEN 字节载荷`，载荷整体交给 `0x352F80→0xA2660`。若 `LEN` 精确覆盖 `0x04 + count1 + A1/A2/A3 + 0x06`，则 `0x06` 会落在 MSG 缓冲内但不被 `0xA2660` 消费。

| 假设 | 需要的直接证据 | 状态 |
|---|---|---|
| `0x06` 由 `LEN` 边界隐式包含，不需显式读取 | `LEN` 的写入者与 `0xA0997` 的偏移等式 | **BLOCKED** |
| `0x06` 由外层状态机跳过 | 外层状态机中对该字节的处理 | **BLOCKED** |
| `0x06` 确实被显式比较 | 读取+比较 6 的指令 | **未找到** |

## 5. 每条路径的输入/输出游标关系

| 路径 | 输入游标 | 输出游标 | 依据 |
|---|---|---|---|
| 服务端 `0xA07F8` | bitpos=0 | used+=1 | DIRECT |
| 服务端 `0xA0997` | body 结束 | used+=1 | DIRECT |
| 客户端 `0x352F80` | msg.pos = P | msg.pos = P+1 | DIRECT |
| 客户端 `0xA2660` | msg.pos = P+1 | msg.pos = P+1+consumed | DIRECT |
| 客户端 case 6 载荷 | 外层游标 = Q | Q + 4 + LEN | DIRECT |

## 6. 最小新增证据

| ID | 缺口 | 最小证据 | 授权 |
|---|---|---|---|
| G-11-4 | `0x06` 客户端读取点 | 读取 1 字节并比较 6 的指令，或 `LEN` 与 `0xA0997` 的偏移等式 | 否（静态） |
| G-11-5 | 对齐语义 | 读取原语用 bitpos 还是字节游标 | 否（静态） |
| G-11-6 | 端到端终止 | 原始帧字节 | **是** |
"""

F["06_CURSOR_ACCOUNTING.md"]=r"""# 06 — 游标记账 / CURSOR ACCOUNTING

> 全部为 DIRECT，除标注处。位偏移从服务端 `0x04` 首位起算。

---

## 1. 服务端写入游标（DIRECT）

msg 结构：`[+0]=buf`，`[+4]=used(字节)`，`[+8]=cap`，`[+0x10]=bitpos`，`[+0x14]=overflow`。

| 写入 | 位置 | 字节增量 | bitpos 行为 |
|---|---|---|---|
| bitpos 归零 | `0xA07E6` | — | `[+0x10]=0` |
| `WriteByte(4)` | `0xA07F8` | +1 | 8 bit 写 |
| `WriteShort(count1)` | `0xA0807` | +2 | 16 bit 写 |
| A1 字符串 | `0x99651` | +len+1 | **不更新 bitpos** |
| A2/A3 位字段 | `0x99590` | 视内容 | 位推进，边界重同步 |
| `WriteByte(6)` | `0xA0997` | +1 | 8 bit 写 |

**重同步规则（DIRECT，`0x9960A`）：** `bitpos % 8 == 0` 时 `bitpos = used*8`，随后 `used++` 并追加 0 字节。

**A1 不占位（DIRECT）：** `WriteLenStr` `0x99651` 内无 `[msg+0x10]` 写入（脚本自检结果 `False`）。

## 2. 累计位模型（服务端，count1=16）

| 场景 | 0x06 起始 bitpos | 模 8 |
|---|---|---|
| A1=A2=A3 空 | 44 | 4 |
| A1=[(0,'')] | 53 | 5 |
| A1=[(0,'a')] | 61 | 5 |
| A1=[(0,'a')], A2=[(0,1)] | 72 | 0 |
| 完整示例 | 129 | 1 |

**结论：** `0x06` 起始位置**依输入变化**，不保证字节对齐。

## 3. 客户端读取游标（DIRECT）

| 操作 | 位置 | 游标变化 |
|---|---|---|
| `MSG_InitReadOnly` | `0x1AC190` | `[+0x14]=0`（offset）、`[+0x1C]=0`（pos） |
| `MSG_ReadData(msg,dst,2)` | `0x1AC1D0` | 逐字节读，`pos += len` |
| `MSG_ReadBits(msg,bits)` | `0x1AC670` | 用 `[+0x20]` bitpos；`and 7`/`sar 3` |
| `0x352FA1` | `0x352F80` | `pos += 1`（跳过子帧头） |
| case 6 外层读 | `0x3546D4` | 读 4 字节 `LEN` |
| case 6 载荷读 | `0x3546EE` | 读 `LEN` 字节 |

**`MSG_ReadBits` 结构（DIRECT）：** 使用 `[msg+0x20]` 作 bitpos（不是 `[+0x10]`），说明客户端 MSG 结构与服务端 msg 结构**布局不同**，不能直接套用服务端字段偏移。

## 4. 两侧游标对照（CROSS）

| 阶段 | 服务端字节 | 客户端字节 |
|---|---|---|
| 子帧头 | `0x04` = 1 | `0x352FA1` 跳过 1 |
| count1 | 2 | `MSG_ReadData` 2 |
| A1 | 索引位 + 字符串字节 | `MSG_ReadBits` + NUL 扫描 |
| A2 | 11/13/10 bit | 同 |
| A3 | 10/7/4/n×12 bit | 同 |
| 子帧尾 | `0x06` = 1 | **未定位** |

## 5. 裁定

| 项 | 裁定 |
|---|---|
| 服务端位记账可复算 | **PROVEN** |
| 客户端读取游标推进 | **PROVEN**（除 0x06） |
| 两侧 count1/A1/A2/A3 对齐 | **CROSS** |
| 子帧尾游标 | **BLOCKED** |
| 客户端 MSG 与服务端 msg 同布局 | **REFUTED**（bitpos 偏移 `+0x20` vs `+0x10`） |
"""

F["07_E11_VERDICT.md"]=r"""# 07 — E-11 总裁定 / VERDICT

> 只读静态分析。未启动游戏/服务端，未注入，未读进程内存，未修改样本。

---

## 1. 完成标准逐条裁定

| # | 完成标准 | 裁定 |
|---|---|---|
| 1 | 顶层 Gamestate `0x03` 消费路径 | **BLOCKED**：顶层分派器 `0x350170` 已 PROVEN；`0x03`→`0x34FD80(1)` 字段序与服务端 `0xA21B8` 不匹配 |
| 2 | 内部 `0x04` 子帧识别方式 | **INFERRED（强）**：`0x352FA1` 固定 +1 字节；无值比较 → 按约束保留非 PROVEN |
| 3 | case 6 与 `0xA2660` 的连接 | **PROVEN**：`0x3546F3 → 0x352F80 → 0xA2660` |
| 4 | `0x06` 读取/对齐/终止 | **全部 BLOCKED**（服务端写入侧 PROVEN） |
| 5 | 已证/阻断环节 | 见下表 |

## 2. 环节分级表

| 环节 | 等级 |
|---|---|
| 顶层分派器 `0x350170` + 表 `0x75025C` | **PROVEN** |
| 读取函数指针 `[+0x89244]` ∈ {`0x352570`,`0x34F090`} | **PROVEN** |
| 子帧分派器 `0x354100` + 表 `0x7547AC`（0..8） | **PROVEN** |
| 子帧循环 `0x3547D0`（退出 0x09/0x0A） | **PROVEN** |
| case 6 → `0x352F80` → `0xA2660` | **PROVEN** |
| `0x352F80` +1 字节 | **PROVEN** |
| 被跳过字节 = 服务端 `0x04` | **INFERRED（强）** |
| `0x04` 值级比较 | **BLOCKED** |
| case 6 `LEN` 语义 | **BLOCKED** |
| `0x03` 客户端消费者字段匹配 | **BLOCKED** |
| `0x06` 客户端读取/对齐/终止 | **BLOCKED** |
| Configstring body 字段序 | **CROSS**（count1/A1/A2/A3） |
| 整条消息互操作 | **BLOCKED** |

## 3. 本轮相对 E-10 的更正（追加，不覆盖）

| # | E-10 | E-11 更正 | 依据 |
|---|---|---|---|
| M1 | 字符串探测（`bytes_rva`） | E-10 误传 VA，结果全 None；E-11 用 `VA-ImageBase` | `_data/out_t03_xrefs.txt` |
| M2 | `0x354100` 是外层分派器 | 实为**子帧**分派器；顶层是 `0x350170` | 跳转表 `0x75025C` |
| M3 | `0x04` 是顶层 opcode | 实为 **Gamestate 内部子帧头**；顶层域为 1..4 | `0x3501F5` `cmp eax,3` |
| M4 | case 6 读"4+4 字节" | 实为 `u32 LEN` + `LEN` 字节载荷 | `0x3546D4`/`0x3546EE` |
| M5 | `0x06` 层级 | 三个写入点层级不同，禁止合并（保持 E-10 结论） | 服务端 3 处 |

## 4. 纪律声明

- **未**把位置一致升级为值级识别（`0x04` 保持 INFERRED）。
- **未**跨层合并 `0x06`。
- **未**因搜索无命中宣称客户端不存在对应逻辑（按约束 6）。
- **未**修改任何原始样本。

## 5. 最小新增证据清单

| ID | 缺口 | 最小证据 | 授权 |
|---|---|---|---|
| G-11-1 | `0x03` 客户端消费者 | 定位读 `{i32,cstring,cstring,i32}` 的函数 | 否 |
| G-11-2 | `0x04` 值级识别 | 对 1 字节值 4 的比较，或 case 6 `LEN` 与子帧边界的等式 | 否 |
| G-11-3 | 读取层分片协议 | 设置 case 6 `LEN` 的写入者 | 否 |
| G-11-4 | `0x06` 读取点 | 读 1 字节并比较 6 的指令，或 `LEN` 覆盖到 `0xA0997` 的等式 | 否 |
| G-11-5 | 对齐语义 | 读取原语用 bitpos 还是字节游标 | 否 |
| G-11-6 | 端到端终止 | 原始帧字节 | **是** |

## 6. 交付物清单

| 文件 | 状态 |
|---|---|
| `01_GAMSTATE_CONSUMER_CHAIN.md` | ✔ |
| `02_SUBFRAME_CURSOR_AND_LOOP.md` | ✔ |
| `03_CASE6_CONFIGSTRING_CHAIN.md` | ✔ |
| `04_OPCODE_04_VERDICT.md` | ✔ |
| `05_OPCODE_06_TERMINATION_VERDICT.md` | ✔ |
| `06_CURSOR_ACCOUNTING.md` | ✔ |
| `07_E11_VERDICT.md` | ✔ |
| `SHA256SUMS.txt` | ✔ |
"""

for n,c in F.items():
    open(os.path.join(wd,n),"w",encoding="utf-8",newline="\n").write(c)
print("wrote",len(F))
