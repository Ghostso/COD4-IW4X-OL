# 01 — Gamestate 消费链 / GAMESTATE CONSUMER CHAIN

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
