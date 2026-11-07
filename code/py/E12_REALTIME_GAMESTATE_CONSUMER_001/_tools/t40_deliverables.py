# -*- coding: utf-8 -*-
import os
wd=r"D:\BaiduNetdiskDownload\使命召唤OL\E12_REALTIME_GAMESTATE_CONSUMER_001"
F={}
F["01_DEMO_PATH_ATTRIBUTION.md"]=r"""# 01 — `0x350170` 路径归属 / DEMO PATH ATTRIBUTION

> 只读静态分析。未启动游戏/服务端，未注入，未读进程内存，未修改样本。
> 客户端 SHA256 `353754047DBBFE3AFBF6C7D97DE3FACA785B3D5D5E34A9053C820EE78814D6E1`
> 恢复镜像 `codol2697-static-candidate.bin`，ImageBase `0x400000`（VA = RVA + 0x400000）。
> 等级：`PROVEN` / `INFERRED` / `BLOCKED` / `REFUTED`
> 纪律：不因错误字符串或函数名单独裁定路径归属。

---

## 1. 结论摘要

| 主张 | 裁定 |
|---|---|
| `0x350170` 属于 demo/回放处理路径 | **INFERRED（强）**，未达 PROVEN |
| `0x350170` 属于实时网络路径 | **未发现支持证据**（在指定范围内） |
| 可正式从实时网络候选链排除 | **不能**（见 §6） |

**核心证据：** `0x350170` 的两条上游入口最终都由 **demo 控制台命令**驱动，而非网络接收。

## 2. 上游调用链（全量 BFS，DIRECT）

以 `0x350170` 为根做反向调用图 BFS（深度 4），上游**收敛到 9 个函数**：

```
depth 0 : 0x350170
depth 1 : 0x08F1D0, 0x3512A0
depth 2 : 0x09CFE0, 0x34E7C0, 0x3519F0, 0x351A10, 0x356580
depth 3 : 0x1A9060
depth 4 : 0x1A9760
```

## 3. `0x34E7C0` 是 demo 控制台命令回调（DIRECT，决定性）

`0x34DF80` 是注册函数，在 `0x34E1B0` 处注册命令回调：

```asm
34E19B  mov dword [0xDD4BF44], 0x74E7C0    ; ← 回调 = 0x34E7C0
34E1AB  mov esi, 0xCD61EC
34E1B0  call 0x59DCA0                       ; Cmd_AddCommand(name, callback)
```

命令名字符串（`_data/out_t37_names.txt`）：

| VA | 内容 |
|---|---|
| `0xCD61C4` | `cl_demo_timedemo` |
| **`0xCD61D8`** | **`cl_demo_jumptostart`** |
| `0xCD61EC` | `cl_demo_keyboard` |
| `0xCD6200` | `cl_demo_keyboardcomplete` |

**`0x34E7C0` 对应 `cl_demo_jumptostart`（DIRECT）。**

同一注册函数还写入 `cl_demo_play`（`0xCD61B4`）及 cvar `917`–`935`（`0xCD6184`–`0xCD61B0`），整块属于 demo 子系统。

**`0x34E7C0` 的数据指针引用唯一**：`0x34E1A1`（即上述注册表项）——无其他调用者（DIRECT）。

## 4. `0x8F1D0` 的 demo 状态门（DIRECT）

```asm
08F1D3  mov ecx,[0x1BBBCFC]        ; demo/回放状态机
08F1DC  cmp ecx,7
08F1DF  jl  0x48F4B0               ; 状态 < 7 → 直接返回（不调 0x350170）
08F1E5  ...
08F22A  lea edi,[eax+0x1BBBCFC]
08F230  mov eax,[edi]
08F232  cmp eax,7
08F235  jl  0x48F24A
08F237  cmp eax,9
08F23A  jge 0x48F24A
08F23C  mov eax,ebx
08F23E  call 0x750170              ; ← 仅当状态 ∈ [7,9) 才调用
08F24A  call 0x5A96A0
08F251  call 0x750170
08F261  cmp ecx,9
08F264  jne 0x48F4B0               ; 状态 != 9 → 返回
08F26A  ...
08F29F  cmp dword [0x1BBBCFC],0xA
```

**`0x1BBBCFC` 是 demo/回放状态机**（取值范围 0–10，`_data/out_state_var.txt` 共 166 处引用），其写入点集中在 `0x8Fxxx`/`0x9Cxxx`/`0x9Dxxx`（demo 控制簇）。

## 5. `0x8F1D0` 的错误处理引用 demo 错误码（DIRECT）

`0x8F1D0` 的调用者 `0x350170` 越界分支：

```asm
350245  push 0xCD6384
35024A  push 2
35024C  call 0xDDAB8AC
```

字符串 `0xCD6384` = **`EXE_ERR_PROCESS_DEMO_FILE_FAILED`**（`_data/out_t10_batch2`）。

**注意：** 按任务要求，**该字符串单独不足以裁定**；它与 §3、§4 的状态机/命令注册证据**合并**才构成强推断。

## 6. 读取器归属（DIRECT）

`[client+0x89244]` 是**可插拔读取函数指针**，全镜像仅 3 处写入：

| 站点 | 写入值 | 场景 |
|---|---|---|
| `0x35141E` | `0x752570` | 网络读取器（读自 `[+0x8048]` 环形缓冲） |
| `0x3515D9` | `0x74F090` | demo 读取器（失败报 `EXE_ERR_READING_DEMO`） |
| `0x356701` | `0x74F090` | demo 读取器 |

`0x356580`（`0x34E7C0` 调用的 demo 装载函数）在 `0x356701` 安装 demo 读取器后，于 `0x356722` 调用 `0x8F1D0`：

```asm
356701  mov dword [esi+0x89244], 0x74F090
356711  push 0x8020 / push ecx / call edx      ; demo 读取
356722  call 0x48F1D0
```

**这是 demo 链的决定性汇合点（DIRECT）。**

## 7. 未证实的实时网络关联

| 检查 | 范围 | 结果 |
|---|---|---|
| `recv`/`recvfrom` IAT 调用点（9 个函数） | 全 `.text` | 8 层内**未**到达 `0x350170`/`0x3547D0`/`0xA2660` |
| `0x350170` 数据指针引用 | 全镜像 | **0** |
| `0x350170` 上游是否含 socket 句柄/网络缓冲 | 9 个上游函数 | 未发现 |

**说明（按任务纪律）：** 负搜索只记为“在指定范围内未发现”，**不构成 REFUTED**。

## 8. 不能据此下结论的证据

| 证据 | 为何不足 |
|---|---|
| `EXE_ERR_PROCESS_DEMO_FILE_FAILED` 字符串 | 单独可属任何路径；需与状态机/注册证据合并 |
| 函数位于 `0x34xxxx`–`0x35xxxx` 簇 | 地址簇不等于路径归属 |
| `0x352570` 名为“网络读取器” | 命名来自其环形缓冲行为，非路径证明；`0x74F090` 亦写入同一 `+0x89244` |

## 9. 裁定

**`0x350170` 归属 demo/回放路径：INFERRED（强）。**

- 支持：命令回调 `cl_demo_jumptostart`（`0x34E7C0`）+ demo 状态机门（`0x1BBBCFC ∈ [7,9)`）+ demo 读取器安装（`0x74F090`）+ demo 错误码。
- 未排除的替代解释：`0x8F1D0` 可能同时被实时路径以相同状态值调用（未发现证据，但未穷尽间接分派）。
- **因此不能宣称 PROVEN，也不能据此正式排除实时网络候选链。**
"""

F["02_REALTIME_NETWORK_ENTRY_CHAIN.md"]=r"""# 02 — 实时网络入口链 / REALTIME NETWORK ENTRY CHAIN

> 等级：`PROVEN` / `INFERRED` / `BLOCKED`。全部地址为 RVA（模块 `codol2697-static-candidate.bin`，ImageBase `0x400000`）。

---

## 1. 网络 IAT 锚点（PROVEN，PE 导入表）

`_tools/t21_imports.py` 输出：

| 导入 | IAT VA | IAT RVA |
|---|---|---|
| `ws2_32.dll!recv` | `0xBAE490` | `0x7AE490` |
| `ws2_32.dll!send` | `0xBAE4C8` | `0x7AE4C8` |
| `wsock32.dll!recvfrom` | `0xBAE50C` | `0x7AE50C` |
| `wsock32.dll!sendto` | `0xBAE504` | `0x7AE504` |
| `wsock32.dll!select` | `0xBAE4D8` | `0x7AE4D8` |
| `wsock32.dll!ioctlsocket` | `0xBAE4F0` | `0x7AE4F0` |
| `kernel32.dll!ReadFile` | `0xBAE22C` | `0x7AE22C` |
| `kernel32.dll!CreateFileA` | `0xBAE1E4` | `0x7AE1E4` |

**这是“实时网络”与“文件读取”的机器可验证分界锚点（PROVEN）。**

## 2. 收包调用点（PROVEN）

`_data/out_iat_callers.txt`：

| 原语 | 调用点 RVA | 所在函数 |
|---|---|---|
| `recvfrom` | `0x1B0BA1` | `0x1B0430` |
| `recvfrom` | `0x6B4E3C` | `0x6B4DE0` |
| `recvfrom` | `0x775ADE` | `0x775AB0` |
| `recv` | `0x602441` | `0x602430` |
| `recv` | `0x6029BE` | `0x6029A0` |
| `recv` | `0x6052AB` | `0x605220` |
| `recv` | `0x775A6C` | `0x775A50` |
| `recv` | `0x784F7D` | `0x784F60` |
| `recv` | `0x788133` | `0x78772D` |

对应发包：`sendto` 4 处（`0xDFADB`/`0x1B09EF`/`0x6B4C92`/`0x775AA2`）、`send` 5 处。

**结论（PROVEN）：** 实时网络收/发原语调用点已定位；这是网络层的**底锚**。

## 3. 应用层环形缓冲（PROVEN）

客户端在 `[0x743DE9C]` 指向的对象中维护一个 **3 MB 环形缓冲**（基址 `obj+0x8048`）：

| 偏移 | 语义 | 证据 |
|---|---|---|
| `+0x8048` | 环形缓冲基址 | `0x352520`/`0x352551`/`0x35259B`/`0x3525D0` 的 `lea ... +0x8048` |
| `+0x30AF2C` | **写游标** | `0x3524FE`/`0x35252D`/`0x35253B`/`0x352561` |
| `+0x30AF30` | **读游标** | `0x35257E`/`0x3525AD`/`0x3525BB`/`0x3525E1` |

两个原语：

| 函数 | 方向 | 签名 | 关键指令 |
|---|---|---|---|
| `0x3524F0` | **写侧**（src → 环形缓冲） | `(src, len)` | `memcpy(ring+write, src, len)` @`0x352559` |
| `0x352570` | **读侧**（环形缓冲 → dst） | `(dst, len)` | `memcpy(dst, ring+read, len)` @`0x3525D9`，返回 `len` |

两者容量上限 `0x300000`（3 MB），溢出时回绕并把游标清零（`0x35253B`/`0x3525BB`）。

**结论（PROVEN）：** `0x3524F0` 是**接收侧写入器**，`0x352570` 是**消费侧读取器**。

## 4. 读取器安装点（PROVEN）

`[+0x89244]` 为可插拔读取函数指针，全镜像 3 处写入（`_data/out_t27_verify.txt`）：

| 站点 | 值 | 语义 |
|---|---|---|
| `0x35141E` | `0x752570` | 网络读取器 |
| `0x3515D9` | `0x74F090` | demo 读取器 |
| `0x356701` | `0x74F090` | demo 读取器 |

**注意：** `0x352570` 是**读侧**（环形缓冲 → 目标），`0x3524F0` 是**写侧**（源 → 环形缓冲）。二者成对，共享同一环形缓冲。

## 5. 链路状态

| 箭头 | 状态 | 证据 |
|---|---|---|
| `recv/recvfrom` → 收包函数 | **PROVEN** | §2 |
| 收包函数 → 环形缓冲写侧 `0x3524F0` | **BLOCKED** | 8 层内未命中（负搜索，不升级为 REFUTED） |
| 环形缓冲读侧 `0x352570` → `0x3547D0`/`0xA2660` | **PROVEN**（`0x3512A0` 内） | E-11 EV-11-07 |
| 环形缓冲读侧 → `0x350170` | **PROVEN**（`0x8F1D0`/`0x3512A0` 内） | 但路径归属为 demo（见 `01`） |

**链在“收包函数 → 环形缓冲写侧”处中断。** 按任务要求，**停在该层，不补造下游调用关系**。

## 6. 裁定

| 项 | 裁定 |
|---|---|
| 实时网络底锚（IAT） | **PROVEN** |
| 收包调用点清单 | **PROVEN** |
| 应用层环形缓冲与读写原语 | **PROVEN** |
| 收包函数 → 环形缓冲的调用边 | **BLOCKED** |
| 环形缓冲 → Gamestate 业务解析 | **BLOCKED**（与 demo 链共享读取器，归属未定） |
"""

F["03_REALTIME_GAMESTATE_CONSUMER.md"]=r"""# 03 — 实时 Gamestate `0x03` 消费者 / REALTIME GAMESTATE CONSUMER

> 等级：`PROVEN` / `INFERRED` / `BLOCKED`。

---

## 1. 结论

**实时 Gamestate `0x03` 消费者：未定位（BLOCKED）。**

已定位的 `0x03` 处理点属于 **demo/回放路径**（见 `01`），其字段序与服务端 `0xA21B8` 不匹配（见 `04`）。

## 2. 已定位的 `0x03` 处理点（DIRECT）

顶层分派器 `0x350170`（E-11 已证）：

```asm
350150  movzx eax, byte [ebp+0xc]
3501EF  dec eax
3501F5  cmp eax, 3
3501FA  jmp dword [eax*4 + 0x75025C]
```

| wire 值 | 目标 |
|---|---|
| 1 | `0x350040` |
| 2 | `0x34FD80(0)` |
| **3** | **`0x34FD80(1)`** |
| 4 | `0x3547D0` |

**`0x03` → `0x34FD80(arg=1)`（DIRECT）。**

## 3. `0x34FD80` 读取序列（DIRECT）

```asm
34FDB0  call [edi+0x89244]  len=4        ; f0 = dword
34FDC4  cmp byte [ebp+0xc],0
34FDD0  call [edi+0x89244]  len=4        ; f4 = dword（仅 arg=1 分支）
34FE3F  call [edi+0x89244]  len=4        ; f8 = length
34FE81  cmp eax,0x20000                  ; 上限检查
34FE8D  push 0xCD637C                    ; 超限报错
34FEAC  call [edi+0x89244]  len=f8       ; 载荷
34FEB7  cmp [ebp-0x20034],4
34FED4  call 0x1AC1D0       len=4        ; 内嵌 dword
34FF39  ... 写入 [esi+0x4231F8] ...
350024  call 0x751D00
```

**字段序（DIRECT）：** `{i32 f0, i32 f4, u32 len, len bytes}`。

## 4. 与服务端 `0x03` 体的冲突（DIRECT，REFUTED 匹配）

服务端 `_CODOL2697_WriteGamestate` `0xA21B8`：

```asm
0A224C  WriteByte(3)
0A225A  WriteInt32(version)          ; i32
0A2269  WriteLenStr(map)             ; cstring
0A2279  WriteLenStr("mp")            ; cstring
0A2288  WriteInt32(field4)           ; i32
0A22C1  call WriteConfigstrings      ; 0x04 ... 0x06
0A22D9  WriteInt32(fieldC)
0A22E8  WriteInt32(field8)
0A22F8  WriteByte(6)
```

| 位置 | 服务端 | 客户端 `0x34FD80(1)` | 匹配 |
|---|---|---|---|
| 1 | `i32` | `i32` | 宽度同，语义未证 |
| 2 | `cstring` | `i32` | **冲突** |
| 3 | `cstring` | `u32 len` | **冲突** |
| 4 | `i32` | `payload` | **冲突** |

**结论（REFUTED）：** `0x34FD80(1)` **不是** `0xA21B8` 的消费者。两者字段序直接冲突。

## 5. 上游路径归属（DIRECT）

`0x34FD80` 的唯一调用者是 `0x350170`（`0x350204`/`0x350217`），而 `0x350170` 的归属为 demo（`01` §3–§6）。

**因此 `0x03` → `0x34FD80(1)` 属 demo 路径。**

## 6. 实时消费者候选（INFERRED，未证实）

| 候选 | 依据 | 状态 |
|---|---|---|
| 收包函数（§`02`）的下游 | 底锚 PROVEN，但下游边 BLOCKED | BLOCKED |
| `0xA2E50`（reliable payload） | 直接调用者 **0**；数据指针引用 **0** | BLOCKED（历史已记） |
| `0x6D340`/`0x6D5D0` | 读位 + 调 `0xA2480`；上游 `0x6F2F0` | 未证属实时 |
| `0x6E060` | 多次 `MSG_ReadData` | 未证属实时 |

**纪律：** 不使用“用了 `MSG_ReadBits`/`MSG_ReadData`”作为消费者判据。

## 7. 裁定

| 项 | 裁定 |
|---|---|
| 顶层分派器与 `0x03` → `0x34FD80(1)` | **PROVEN** |
| `0x34FD80(1)` 归属 demo | **INFERRED（强）**（经 `0x350170`） |
| 实时 `0x03` 消费者 | **BLOCKED** |
| 实时消费者与服务端字段匹配 | **BLOCKED**（无候选可比） |
"""

F["04_SERVER_CLIENT_FIELD_MATRIX.md"]=r"""# 04 — 服务端/客户端字段矩阵 / FIELD MATRIX

> 基准：服务端 `_CODOL2697_WriteGamestate` RVA `0xA21B8`；客户端候选 `0x34FD80(1)`（demo 路径，唯一已定位的 `0x03` 处理点）。
> 等级：`PROVEN` / `INFERRED` / `BLOCKED` / `REFUTED`

---

## 1. 顶层字段矩阵

| 字段/阶段 | 服务端写入证据 | 客户端读取证据 | 裁定 |
|---|---|---|---|
| 消息类型 `0x03` | `0xA224C WriteByte(3)`（`0x99551`，ECX=1） | `0x3501EF dec eax` + 表项 3 → `0x34FD80(1)` | **PROVEN**（两侧各证；对应关系 DIRECT） |
| 初始整数 | `0xA225A WriteInt32`（4B） | `0x34FDB0` 读 4B → `[edi+0x40148]` | 宽度同；语义 **BLOCKED** |
| 字符串 1 | `0xA2269 WriteLenStr(map)`（cstring） | `0x34FDD0` 读 4B（**非 cstring**） | **REFUTED** |
| 字符串 2 | `0xA2279 WriteLenStr("mp")`（cstring） | `0x34FE3F` 读 4B 长度 | **REFUTED** |
| 字段 4 | `0xA2288 WriteInt32(field4)` | `0x34FEAC` 读 `len` 字节载荷 | **REFUTED** |
| Configstring 子帧 | `0xA22C1 call 0xA0468` → `0xA07F8 WriteByte(4)` … `0xA0997 WriteByte(6)` | 无对应（`0x34FD80` 不解析子帧） | **BLOCKED** |
| `0x06` 标记 | `0xA22F8 WriteByte(6)`（顶层尾） | 无 | **BLOCKED** |
| 结束/游标 | `0xA22FD` 检查 overflow 后返回 | `0x35002C` 返回 | **BLOCKED** |

## 2. 结论：字段序不匹配

**客户端 `0x34FD80(1)` 的字段序 `{i32, i32, u32 len, payload}` 与服务端 `{i32, cstring, cstring, i32, <cfgsub>, i32, i32, 0x06}` 在第 2 个字段即冲突（`i32` vs `cstring`）。**

**裁定（REFUTED）：** 两者不是同一消息格式的读写两端。

## 3. Configstring body 字段矩阵（E-11 已证部分）

| 字段 | 服务端证据 | 客户端证据 | 裁定 |
|---|---|---|---|
| count1 = 2 字节 | `WriteShort` `0xA0807`（`0x99566` ECX=2） | `0x26AF push 2` + `MSG_ReadData` + `movsx word` | **PROVEN** |
| 索引连续性标志 | `0xA0400` WriteIndexDelta（1 bit） | `0x44C8C0` + `MSG_ReadBits(0xD)` | **PROVEN** |
| 13-bit 绝对索引 | 13 bit | `0xA26F4 push 0xD` | **PROVEN** |
| A1 字符串 | `WriteLenStr`（strlen+1 字节） | `0xA25F0` NUL 扫描 | **PROVEN** |
| A2 计数 | 10 bit | `0xA276C push 0xB`（11 bit） | **差异，见 §4** |
| A2 值 | 10 bit | `0xA27D7 push 0xA` | **PROVEN** |
| A3 计数 | 10 bit | `0xA2879 push 0xA` | **PROVEN** |
| A3 记录 | 10/7/4/n×12 | `0xA2480 push 0xA/7/4`，n×12 | **PROVEN** |
| 索引上限 | `0x1DD7` | `cmp edi,0x1DD7` | **PROVEN** |

## 4. A2 计数字宽的潜在差异（按任务要求重新检查）

| 侧 | 证据 | 值 |
|---|---|---|
| 服务端 | E-08 记录 A2 计数为 **10 bit** | 10 |
| 客户端 | `0xA2765 push 0xB` → `MSG_ReadBits(11)` | **11** |

**本轮核对结果：** 客户端 A2 计数读取宽度为 **11 bit**（`0xA2765` 指令级，DIRECT）；服务端 E-08 记录为 **10 bit**（来自 `0x99590` 调用参数，未在本轮重新逐指令确认）。

**裁定：** 该差异**保留为 BLOCKED**。本轮**未获得**服务端 A2 计数的精确位宽指令证据（`0xA0468` 内未定位到对应的 `push`/`WriteBits` 序列），因此**不得**断言两侧一致，也**不得**断言冲突。

**最小验证动作：** 在服务端 `0xA0468` 内逐指令定位 A2 段计数写入的 `push` 位宽。

## 5. 分层纪律声明

- 未把**字节宽度**与**位宽**混同（§1 全部标注宽度类型）。
- 未把**写入一个字节**等同于客户端按同语义消费。
- 未因两个字段**均为 32 位**而认为语义匹配。
- 未把服务端**不同层级**的 `0x06`（`0xA0997` 子帧尾 / `0xA22F8` 顶层尾 / `0xA4CAF` snapshot）合并。

## 6. 裁定

| 项 | 裁定 |
|---|---|
| `0x03` 消息类型对应 | **PROVEN** |
| 初始整数宽度 | PROVEN（4B）；语义 BLOCKED |
| 第 2–4 字段 | **REFUTED**（字段序冲突） |
| Configstring 子帧字段（body 内） | **PROVEN**（count1/索引/A1/A2 值/A3） |
| A2 计数位宽 | **BLOCKED**（服务端未复核） |
| 消息结束与游标 | **BLOCKED** |
"""

F["05_CONFIGSTRING_PATH_CLOSURE.md"]=r"""# 05 — 配置字符串链闭合 / CONFIGSTRING PATH CLOSURE

> 等级：`PROVEN` / `INFERRED` / `BLOCKED` / `REFUTED`

---

## 1. 候选链状态

```
实时 Gamestate 消费者 → 内部子帧循环 → case 6 → 新建 MSG → 0xA2660
```

| 环节 | 裁定 | 依据 |
|---|---|---|
| 实时 Gamestate 消费者 | **BLOCKED** | `03` §7 |
| 内部子帧循环 `0x3547D0` | **PROVEN**（存在），但归属 demo | `01` |
| case 6 `0x354697` | **PROVEN** | E-11 EV-11-05 |
| case 6 → `0x352F80` → `0xA2660` | **PROVEN** | E-11 EV-11-06 |
| 实时链与 demo 链共用底层解析函数 | **INFERRED** | 共享 `0x354100`/`0x352F80`/`0xA2660`，但无实时上游证据 |

**结论：** 该链的**下游**（case 6 → `0xA2660`）已 PROVEN；**上游**（实时消费者）BLOCKED。因此**端到端实时链未闭合**。

## 2. `0x04` 裁定

| 主张 | 证据 | 裁定 |
|---|---|---|
| 服务端写入 `0x04` | `0xA07F8 WriteByte(4)`（`0x99551` ECX=1），唯一调用者 `0xA22C1` | **PROVEN** |
| 客户端值级识别 `0x04` | 四区域扫描无 `cmp == 4` 消息比较 | **未发现**（不升级为 REFUTED） |
| 客户端按游标位置跳过 1 字节 | `0x352FA1 inc eax` / `0x352FA2 mov [esi+0x1C],eax` | **PROVEN** |
| 被跳过字节 = `0x04` | 位置一致 | **INFERRED** |
| `0x04` 读取位宽 | 服务端 1 字节（PROVEN）；客户端跳过 1 字节（PROVEN） | 端到端 **INFERRED** |
| `0x04` 对齐规则 | 服务端 `[msg+0x10]=0` 后整字节写（PROVEN） | 客户端无独立证据 → **BLOCKED** |

**值级识别是否 PROVEN：否。** 仅凭游标位置的识别为 **INFERRED**。

## 3. `0x06` 裁定

| 属性 | 服务端 | 客户端 | 裁定 |
|---|---|---|---|
| 写入/读取 | `0xA0997`（子帧尾）/`0xA22F8`（顶层尾）/`0xA4CAF`（snapshot） | **未定位** | 读取 **BLOCKED** |
| 位宽 | `0x99551` → ECX=1（1 字节） | 未定位 | 服务端 PROVEN；端到端 BLOCKED |
| 对齐 | body 后整字节写（依赖输入） | 未定位 | BLOCKED |
| 终止语义 | 写点位于 body 之后 | 未定位 | BLOCKED |
| 层级 | 三个写入点层级不同 | — | **PROVEN**（禁止合并） |

**纪律：** `0x06` 的值级识别、位宽、对齐、终止**均未在客户端 PROVEN**。

## 4. `0xA2660` 是否为实时 Configstring body reader

| 判据 | 结果 |
|---|---|
| 字段级两侧对应（count1/索引/A1/A2 值/A3） | **PROVEN** |
| 调用者是否为实时路径 | **未证**（3 个调用点：`0x3512A0`、`0x352F80`×2；`0x352F80` 由 case 6 驱动） |
| case 6 上游是否实时 | **BLOCKED** |
| 路径归属对照 | demo 链已由 `01` 建立；实时链未建立 |

**裁定：`0xA2660` 是“Configstring body reader”（PROVEN）；但“**实时** Configstring body reader”这一归属：BLOCKED。**

## 5. 汇合点要求（任务 E12-E）

若实时链与 demo 链最终共用同一底层解析函数，必须给出**可验证的汇合点与上游调用证据**。

本轮发现的汇合点：

| 汇合点 | 证据 | 是否满足 |
|---|---|---|
| `0x354100`（子帧分派器） | 唯一调用者 `0x3547D0`（demo 链） | 仅 demo 上游 |
| `0x352F80` → `0xA2660` | 唯一调用者 `0x354100` | 仅 demo 上游 |
| `0x352570`（读侧原语） | 被 `0x3512A0` 使用（demo 装载） | 未发现实时使用者 |

**结论：** **未找到**实时链与 demo 链的可验证汇合点。按任务要求，**不得**因共用工具函数而认为二者解析同一格式。

## 6. 裁定

| 项 | 裁定 |
|---|---|
| `0x04` 值级识别 | **BLOCKED**（仅 INFERRED 位置） |
| `0x04` 读取位宽 | 服务端 PROVEN / 端到端 INFERRED |
| `0x04` 对齐规则 | **BLOCKED** |
| `0x06` 读取 | **BLOCKED** |
| `0x06` 位宽 | 服务端 PROVEN / 端到端 BLOCKED |
| `0x06` 对齐 | **BLOCKED** |
| `0x06` 终止 | **BLOCKED** |
| `0xA2660` 字段级 | **PROVEN** |
| `0xA2660` 实时归属 | **BLOCKED** |
| 实时↔demo 汇合点 | **未找到** |
"""

F["06_BLOCKER_REGISTER.md"]=r"""# 06 — 阻断登记 / BLOCKER REGISTER

> 每条给出：ID、缺口、已排除项、替代解释、最小下一步。

---

## BLK-12-1：收包函数 → 环形缓冲写侧的调用边

| 项 | 内容 |
|---|---|
| 缺口 | `recv`/`recvfrom` 调用点（9 个函数）到 `0x3524F0`（环形缓冲写侧）之间无已证调用边 |
| 已排除 | 8 层 BFS 内无命中（负搜索，不等于不存在） |
| 替代解释 | ① 经函数指针/虚表间接调用；② 经 `.tvm0` 混淆代码；③ 由独立网络线程写入 |
| 最小下一步 | 在 9 个收包函数内查找对 `[0x743DE9C]` 的访问；或定位写入 `+0x30AF2C` 的其他路径 |
| 范围 | 仅 9 个收包函数及其 3 层下游 |

## BLK-12-2：实时 Gamestate `0x03` 消费者

| 项 | 内容 |
|---|---|
| 缺口 | 未定位实时路径中处理 `0x03` 的函数 |
| 已排除 | `0x34FD80(1)` 字段序与服务端冲突（REFUTED）；`0xA2E50` 调用者 0、数据指针 0 |
| 替代解释 | ① 实时与 demo 共用 `0x350170`（但无实时上游证据）；② 消费者在 `.tvm0`；③ 经间接分派 |
| 最小下一步 | 在 BLK-12-1 解出后，从收包函数下游查找读 `{i32,cstring,cstring,i32}` 的函数 |
| 范围 | 收包函数 3 层下游 |

## BLK-12-3：`0x04` 值级识别

| 项 | 内容 |
|---|---|
| 缺口 | 客户端无 `cmp == 4` 的消息层比较 |
| 已排除 | 四区域（`0x340000-0x360000`/`0xA0000-0xA3000`/`0x60000-0x70000`/`0x1AC000-0x1B0000`）无命中 |
| 替代解释 | ① 由读取层长度前缀隐式跳过；② 由外层状态机处理；③ 值未被校验（仅按位置跳过） |
| 最小下一步 | 定位 case 6 `u32 LEN` 的写入者，检验 `LEN` 是否覆盖子帧边界 |
| 范围 | `0x352F80` 上游 + case 6 `LEN` 数据流 |

## BLK-12-4：`0x06` 读取/位宽/对齐/终止

| 项 | 内容 |
|---|---|
| 缺口 | 客户端 `0x06` 读取点未定位 |
| 已排除 | `0xA2660` 内无读取；子帧循环退出值为 `0x09`/`0x0A`（非 6）；`0x3532F0` 比较的是 `0x81` |
| 替代解释 | ① 由 `LEN` 边界隐式包含；② 由外层状态机跳过；③ 消费者未走此链 |
| 最小下一步 | 在 `0xA2660` 返回后的调用者中搜索读 1 字节并比较 6 的指令；或建立 `LEN` 与 `0xA0997` 的偏移等式 |
| 范围 | `0xA2660` 的 3 个调用点 + case 6 后继 |

## BLK-12-5：A2 计数字宽

| 项 | 内容 |
|---|---|
| 缺口 | 服务端 A2 计数位宽未在本轮逐指令确认（历史记录为 10 bit，客户端实测为 11 bit） |
| 已排除 | 客户端 `0xA2765 push 0xB` 为 DIRECT |
| 替代解释 | ① 服务端记录有误；② 两侧确为不同宽度；③ 段定义不同 |
| 最小下一步 | 在服务端 `0xA0468` 内逐指令定位 A2 段计数写入的 `push` 位宽 |
| 范围 | 服务端 `0xA0468` 内 A2 段 |

## BLK-12-6：`0xA2660` 的实时归属

| 项 | 内容 |
|---|---|
| 缺口 | `0xA2660` 的 3 个调用点均无实时上游证据 |
| 已排除 | 实时链与 demo 链的可验证汇合点未找到 |
| 替代解释 | ① 实时链确实调用 `0xA2660`（未证）；② 实时链使用不同 body reader |
| 最小下一步 | 依赖 BLK-12-1/2 解除 |
| 范围 | `0xA2660` 调用点上游 |

## BLK-12-7：`0x350170` 归属的替代解释

| 项 | 内容 |
|---|---|
| 缺口 | `0x350170` 归属 demo 为 INFERRED，未达 PROVEN |
| 已排除 | 已证 `0x34E7C0` = `cl_demo_jumptostart` 回调；`0x8F1D0` 有 demo 状态门 |
| 替代解释 | `0x8F1D0` 可能同时被实时路径以相同状态值调用（未发现证据，但未穷尽间接分派） |
| 最小下一步 | 枚举 `0x1BBBCFC` 的写入点，确认状态 7/8/9 是否仅由 demo 控制流设置 |
| 范围 | `0x1BBBCFC` 的写入点（`_data/out_state_var.txt`，166 处引用） |
"""

F["07_E12_VERDICT.md"]=r"""# 07 — E-12 总裁定 / VERDICT

> 只读静态分析。未启动游戏/服务端，未注入，未读进程内存，未修改原始样本。

---

## 1. 最终决策问题（任务 §八）

### Q1. `0x350170` 能否正式从实时网络候选链中排除？

**不能（依据不足）。** 裁定为 **INFERRED（强）属 demo**，未达 PROVEN。

依据：
- `0x34E7C0`（`0x350170` 的主要上游）在 `0x34E1B0` 注册为控制台命令 **`cl_demo_jumptostart`** 的回调（`0xCD61D8`，DIRECT）。
- `0x8F1D0` 仅在 demo 状态机 `[0x1BBBCFC] ∈ [7,9)` 时调用 `0x350170`（DIRECT）。
- `0x356580` 在 `0x356701` 安装 demo 读取器 `0x74F090` 后调用 `0x8F1D0`（DIRECT）。
- 越界错误码为 `EXE_ERR_PROCESS_DEMO_FILE_FAILED`（辅助，非单独依据）。

**未排除的替代解释：** `0x8F1D0` 可能同时被实时路径以相同状态值调用（未发现证据，但未穷尽间接分派）。

### Q2. 是否已定位实时 Gamestate `0x03` 消费者？

**否（BLOCKED）。** 已定位的 `0x03` 处理点 `0x34FD80(1)` 经 `0x350170` 归属 demo，且字段序与服务端冲突。

### Q3. 服务端 `_CODOL2697_WriteGamestate` 与客户端实时解析路径是否存在字段级匹配？

**无法比较（BLOCKED）。** 实时消费者未定位。已定位的 demo 消费者 `0x34FD80(1)` 与服务端字段序**冲突（REFUTED）**。

### Q4. `0xA2660` 是否能被认定为实时 Configstring body reader？

**不能（归属 BLOCKED）。** `0xA2660` 作为 “Configstring body reader” 的字段级行为 **PROVEN**；但其“**实时**”归属未证——3 个调用点均无实时上游证据，且实时↔demo 汇合点未找到。

### Q5. 当前证据是否足以开始实现可验证的服务器 Gamestate 编码器？

**不足以实现“可验证”的 Gamestate 编码器。**

- 服务端 `0xA21B8` 的字段序列本身已 PROVEN（可编码）。
- 但**客户端实时消费顺序未证**，因此编码器**无法通过客户端行为验证**。
- Configstring body（count1/索引/A1/A2 值/A3）字段级 PROVEN，可在**离线自测**层面实现。
- 外层框架（`0x03` 消费、`0x04`/`0x06`）BLOCKED。

**结论：** 可实现“服务端自洽 + 离线向量”级别的编码器；**不可宣称**与客户端互操作。

### Q6. 哪些未知项必须在任何互操作性结论之前解决？

| 优先级 | 未知项 | 阻断 |
|---|---|---|
| 1 | 收包函数 → 环形缓冲写侧的调用边（BLK-12-1） | 实时链根 |
| 2 | 实时 `0x03` 消费者（BLK-12-2） | 字段比较 |
| 3 | `0x06` 读取/位宽/对齐/终止（BLK-12-4） | 消息边界 |
| 4 | `0x04` 值级识别（BLK-12-3） | 子帧边界 |
| 5 | `0xA2660` 实时归属（BLK-12-6） | Configstring 闭合 |
| 6 | A2 计数字宽（BLK-12-5） | 字段级一致性 |

## 2. 完成标准逐条裁定

| # | 标准 | 裁定 |
|---|---|---|
| 1 | 实时网络入口有独立证据 | **PROVEN**（IAT 锚点 + 9 个收包函数 + 环形缓冲读写原语） |
| 2 | 网络入口 → 业务分派的调用边 | **BLOCKED**（在“收包函数 → 环形缓冲写侧”中断） |
| 3 | `0x03` 消费者明确证据 | **BLOCKED**（demo 路径已证，实时未定位） |
| 4 | 与 demo 路径归属对照 | **PROVEN**（demo 归属 INFERRED 强，对照完成） |
| 5 | 服务端/客户端字段逐项比较 | **REFUTED（demo 消费者）**；实时 **BLOCKED** |
| 6 | `0x04`/`0x06`/body 层级未混淆 | **满足**（三层分列） |
| 7 | 关键裁定可复核 | **满足**（地址/指令/原始输出齐全） |
| 8 | 原始样本未修改，SHA256 通过 | **满足**（`SHA256SUMS.txt`） |

**实时 Gamestate 消费路径：未定位。** 提交 **BLOCKED** 结论与最小后续范围（`06`）。

## 3. 本轮新增结论

| ID | 结论 | 等级 |
|---|---|---|
| E12-C1 | 网络 IAT 锚点与 9 个收包函数已定位 | PROVEN |
| E12-C2 | 应用层 3 MB 环形缓冲：写侧 `0x3524F0`、读侧 `0x352570` | PROVEN |
| E12-C3 | `[+0x89244]` 读取器指针仅 3 处写入 | PROVEN |
| E12-C4 | `0x34E7C0` = `cl_demo_jumptostart` 命令回调 | PROVEN |
| E12-C5 | `0x8F1D0` 有 demo 状态门（`[0x1BBBCFC] ∈ [7,9)`） | PROVEN |
| E12-C6 | `0x350170` 归属 demo | INFERRED（强） |
| E12-C7 | `0x34FD80(1)` 与服务端 `0xA21B8` 字段序冲突 | REFUTED |
| E12-C8 | 实时 `0x03` 消费者 | BLOCKED |
| E12-C9 | `0xA2660` 实时归属 | BLOCKED |

## 4. 对服务器开发的影响

| 项 | 影响 |
|---|---|
| Configstring body 编码 | 可按 PROVEN 字段实现（离线自测） |
| Gamestate 编码 | 可按服务端序列实现，但**无法客户端验证** |
| 互操作性结论 | **禁止**在 BLK-12-1/2/4 解除前宣称 |
| 分帧/终止 | 必须按“待验证”处理 |

## 5. 纪律声明

- 未把静态推断表述为实机互操作已验证。
- 未因错误字符串或函数名单独裁定路径归属。
- 负搜索结果仅记为“在指定范围内未发现”。
- 未把 demo 文件格式、实时网络消息格式、Gamestate 内部子帧格式混为一谈。
- 未修改任何原始样本。

## 6. 交付物清单

| 文件 | 状态 |
|---|---|
| `01_DEMO_PATH_ATTRIBUTION.md` | ✔ |
| `02_REALTIME_NETWORK_ENTRY_CHAIN.md` | ✔ |
| `03_REALTIME_GAMESTATE_CONSUMER.md` | ✔ |
| `04_SERVER_CLIENT_FIELD_MATRIX.md` | ✔ |
| `05_CONFIGSTRING_PATH_CLOSURE.md` | ✔ |
| `06_BLOCKER_REGISTER.md` | ✔ |
| `07_E12_VERDICT.md` | ✔ |
| `SHA256SUMS.txt` | ✔ |
"""
for n,c in F.items():
    open(os.path.join(wd,n),"w",encoding="utf-8",newline="\n").write(c)
print("wrote",len(F))
