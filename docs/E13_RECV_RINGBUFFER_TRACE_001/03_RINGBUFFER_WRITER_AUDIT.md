# 03 — 环形缓冲写侧审计 / RINGBUFFER WRITER AUDIT

> 定向审计，不做全镜像普查。原始输出：`_data/out_writer_audit.txt`、`_data/out_351d00.txt`

---

## 1. `0x3524F0` 函数边界与全部调用者（DIRECT）

**边界：** `0x3524F0..0x35256A`（`0x35256B..0x35256F` 为 `int3` 填充）。

**直接调用者：22 处，全部位于同一函数 `0x351D00`：**

```
0x351DA7 0x351E8C 0x351EA3 0x351F55 0x351F83 0x351F95
0x351FA7 0x351FD9 0x3520C2 0x3520D4 0x3520E6 0x3521B0
0x352293 0x3522A5 0x3522B7 0x3522CE 0x3522FA 0x35232C
0x35235A 0x35236C 0x35237E 0x352395
```

**数据指针引用：2 处**，同样在 `0x351D00` 内（`.text@0x351ED2`、`.text@0x351F02`，作为 `push 0x7524F0` 传给 `0x753A40`/`0x756760`）。

**结论（PROVEN）：** `0x3524F0` 的调用者**唯一**为 `0x351D00`。

## 2. 写入目标地址与回绕（DIRECT）

```asm
3524F8  mov edi,[0x743DE9C]          ; 环形缓冲对象
3524FE  mov eax,[edi+0x30AF2C]       ; write cursor
352504  lea ecx,[eax+ebx]            ; ecx = write + len
352507  cmp ecx,0x300000             ; 3 MB 上限
35250D  jl  0x752546                 ; 未越界 → 单段写
35250F  push esi
352510  mov esi,0x2FFFFF
352515  sub esi,eax                  ; esi = 剩余容量
352519  jle 0x75253B
35251B  mov edx,[ebp+8]              ; src
35251E  push esi / push edx
352520  lea eax,[eax+edi+0x8048]     ; dst = ring + write
352528  call 0xB4FF60                ; memcpy（第一段）
35252D  add [edi+0x30AF2C],esi       ; write += 剩余
352533  add [ebp+8],esi              ; src += 剩余
35253B  mov dword [edi+0x30AF2C],0   ; 回绕：write = 0
352546  mov ecx,[ebp+8]              ; src
352549  mov edx,[edi+0x30AF2C]       ; write（=0 或原值）
35254F  push ebx / push ecx
352551  lea eax,[edx+edi+0x8048]     ; dst = ring + write
352559  call 0xB4FF60                ; memcpy（第二段）
352561  add [edi+0x30AF2C],ebx       ; write += len
```

**要点（DIRECT）：**

| 项 | 值 |
|---|---|
| 目标 | `[0x743DE9C] + 0x8048 + write` |
| 容量 | `0x300000`（3 MB） |
| 回绕 | 越界时先写尾部，游标归 0，再写头部 |
| 数据源 | **调用者栈参数 `[ebp+8]`**（src），长度 `[ebp+0xC]`（len） |
| 返回值 | 无（`void`） |
| 溢出处理 | **无显式错误标志**——只是回绕覆盖 |

**注意：** `0x3524F0` **不读取** `+0x30AF30`（读游标）。它**不检查**读游标，因此**不做背压/满缓冲判断**。

## 3. 唯一调用者 `0x351D00` 的性质（DIRECT）

**边界：** `0x351D00..`（`sub esp,0x40078`，大型函数）。

关键指令：

```asm
351D34  mov eax,[0x743DE9C]
351D39  mov ecx,[eax+0x30AF2C]        ; 读 write 游标
351D60  mov eax,[edi+0x3424]          ; 本地状态
351D82/351D97  计算长度 [ebp-0x4001C]
351DA7  call 0x7524F0                 ; 写 4 字节长度前缀
351DB4  memset(本地缓冲, 0, 0x20000)
351E1D  call 0x74E9F0
351E2D  call 0x753070                 ; 序列化
351E32  call 0x7531B0
351E37  call 0x753400
351E68  memcpy(本地缓冲, [0x743DE9C]+0x4C, 0x7FFC)
351E8C  call 0x7524F0                 ; 写长度
351EA3  call 0x7524F0                 ; 写载荷
351EDF  call 0x753A40                 ; 提交/发送
351F12  call 0x756760                 ; 提交/发送
```

**判读（DIRECT）：** `0x351D00` 先**序列化本地状态**到栈缓冲，再把结果**写入环形缓冲**，最后调用 `0x753A40`/`0x756760` 提交。这是**发送/序列化构造器**，不是接收处理器。

## 4. 调用链归属（DIRECT）

```
0x350170 (demo 顶层分派器)
   └─ 0x350204/0x350217 → 0x34FD80
         └─ 0x350024 → 0x351D00
               └─ 22 处 → 0x3524F0
```

**`0x34FD80` 的唯一调用者是 `0x350170`**（E-12 已证其为 demo 路径）。

**结论（PROVEN）：** `0x3524F0` 的完整已证调用链**完全落在 demo 分派链内**。

## 5. 是否存在第二个写入函数

| 检查 | 结果 |
|---|---|
| `+0x30AF2C` 的写入点（全 `.text`） | 仅 `0x3524F0` 内 4 处 + `0x351D00` 1 处（读）+ `0x356580` 1 处 |
| `0x356580` 的 `+0x30AF2C` 写入 | `0x3565C9 mov [edi+0x30AF2C],eax`——**重置**（demo 装载初始化），非数据写入 |
| `+0x8048` 的写入点 | 仅 `0x3524F0`/`0x352570` 内的 `lea` |

**结论（PROVEN）：** **不存在**第二个向同一环形缓冲写入数据的函数。`0x3524F0` 是唯一写入者。

## 6. 裁定

| 项 | 裁定 |
|---|---|
| `0x3524F0` 边界 | **PROVEN**（`0x3524F0..0x35256A`） |
| 唯一调用者 | **PROVEN**（`0x351D00`，22 处） |
| 数据源 | **PROVEN**（调用者栈参数） |
| 回绕/溢出逻辑 | **PROVEN**（3 MB，无背压） |
| 调用链归属 | **PROVEN**（demo：`0x350170`→`0x34FD80`→`0x351D00`） |
| 是否存在第二写入者 | **REFUTED** |
| 是否可从 9 个收包函数回溯到达 | **REFUTED**（见 `02` §2：闭包内 0 引用） |
