# CODOL 配置块字段语义 + 连接函数 `0xB88CC0` 逆向（子代理 B）

日期：2026-09-26
镜像：`CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin`（10,899,456 B）
加载基址：`0x400000`，`offset = VA - 0x400000`
方法：**纯静态、只读**反汇编（capstone 5.0.7 / pefile）。未运行游戏、未改内存、未改网络、未删除文件。
脚本（全部纯 ASCII，`py_compile` 通过）：

- `CODOLServer\_subagents\_cfg_dis.py`：区间反汇编 / 调用者 / 立即数引用 / 数据 dump
- `CODOLServer\_subagents\_cfg_scan_fields.py`：全镜像扫描落在配置块区间内的绝对引用
- `CODOLServer\_subagents\_cfg_tenproxy_tags.py`：`TenProxy.dll` tag 处理函数提取
- `CODOLServer\_subagents\_cfg_build_report.py`：生成字段 JSON

---

## 0. 三个必须先更正的前提（重要）

任务书里的三处描述经反汇编核对后**需要修正**，否则会推导出错误结论：

### 更正 1：`+0x98` 不是端口，而是 `+0x18` 缓冲区的长度

```
0064167A  mov ecx,[0x82e1580]
00641680  push 0x331c658          ; ← 出参：长度
00641685  mov dword [0x331c658],0x80   ; 先置默认 0x80
0064168F  mov edx,[ecx]
00641691  mov eax,[edx+0x28]
00641694  push 0x331c5d8          ; ← 入参：缓冲区本体
00641699  push 0x18               ; tag 0x18
0064169B  call eax                ; GetInt(tag=0x18, dst=+0x18, size=&+0x98)
```

`+0x98` 在 `0x7F2CC8` 被 `movzx edx, word [0x331c658]` 取出，然后压栈成为 `0xB88CC0` 的第 3 个栈参数（见下）。它配合 `+0x18` 使用，语义是**长度/容量**，不是端口。

### 更正 2：真正的端口在**另一个全局** `0x81A9EC4`，它不进 `0xB88CC0`

```
007F2BA8  mov ebx, dword [0x81A9EB8]     ; 参数
007F2BAF  movzx edi, word [0x81A9EC4]    ; ★ 端口
007F2BDC  push edi                       ; port
007F2BDD  push 0x81a76a8                 ; host
007F2BE2  push ebx
007F2BE3  mov ecx, eax
007F2BE5  call 0xB88B80                  ; objA 构造（host/port 在这里进入）
```

`host = 0x81A76A8`、`port = 0x81A9EC4`（**word / 16 位**，与“端口”相符）由 `0x641600` 的 **tag 0x07 前两个字段**填充。也就是说：**端口确实存在且是 16 位，但不是配置块 `+0x98`，而是独立全局 `0x81A9EC4`。**

### 更正 3：`0x331C5C0` 首 dword 在整个镜像里**没有任何一处被写入非 0 常量**

全镜像扫描（`_cfg_scan_fields.py 0x331C5C0 0x4`）结果：

```
OFFSET +0x000  VA 0x0331C5C0
   0064161E  68c0c53103        push 0x331c5c0        ; memset dst
   00641BC8  a3c0c53103        mov [0x331c5c0],eax   ; ★ 唯一写入点 = ApplySettings 返回值
   006BBD25  3905c0c53103      cmp [0x331c5c0],eax
   006BBD86  3935c0c53103      cmp [0x331c5c0],esi
   006BBE05  3935c0c53103      cmp [0x331c5c0],esi
   006C195D  833dc0c5310301    cmp [0x331c5c0],1
```

结论：这个“开关”**只由 `0x641600` 的返回值写入**。运行期手工改成 1 能改变分支走向，但**不会补上其余字段**——这正是“改了首 dword 仍失败”的直接原因。

---

## 1. 完整反汇编 `0xB88CC0`（连接函数）

### 1.1 函数签名（由 `ret 0x28` 推出）

`ret 0x28` = 10 个参数 = `thiscall`（`ecx` = objA）+ 返回 `bool`。

调用点 `0x7F2D2A` 的压栈顺序（右到左）对应参数编号：

| 参数 | 来源 | 说明 |
|---|---|---|
| arg1 | `0x331C65C` | 配置块 +0x9C（16 字节，取首字节当模式） |
| arg2 | `0x331C5D8` | 配置块 +0x18（字符串，后续写入流） |
| arg3 | `0x331C658` | 配置块 +0x98（长度字，`movzx word`） |
| arg4 | `0x331C5C4` | 配置块 +0x04（4 字节） |
| arg5 | `0x331CAF8` | 配置块 +0x538（4 字节，tag 5 数据） |
| arg6 | `0` 或 `ebp-0x4C` | 0x40 字节临时缓冲（`0x7F2B30` 生成） |
| arg7 | `0` | 固定为 0 |
| arg8 | `0x331C670` | 配置块 +0xB0（字符串） |
| arg9 | `0` 或 `0xE3EC578` | 会话/票据指针 |
| arg10 | `0` 或 `0x80` | 模式标志（由 `0x849B501` 决定） |

另有 `ecx = objA = [0x84ABB08]`，这是 `thiscall` 的 `this`，不计入 10 个栈参数。

### 1.2 逐段行为

```
00B88CE7  cmp dword [esi+0x20], 0        ; ★ 出口 A：已在连接中 → 直接 return 0
00B88CEB  jne 0xB88F22                   ;     xor al,al ; ret 0x28

00B88CF1  mov ebx,[ebp+0x1C]             ; arg6 字符串
00B88CF4..00B88D0C  strlen 预检；若字节 >= 0x80（非 ASCII）→
00B88DA7  call 0x8435D0 / mov [esi+0x156c],0x73 / mov al,1  ; ★ 特殊返回 1

00B88D0E  mov eax,[ebp+8]                ; arg1(+0x9C) → 复制 16 字节到 [esi+0x3190..0x319C]
00B88D33  lea edi,[esi+0x35FC]           ; 0x85C 字节缓冲，先 memset
00B88D47  mov eax,[ebp+0x18]             ; arg5(+0x538) → [esi+0x364C]
00B88D50  mov eax,[ebp+0x14]             ; arg4(+0x04) → 复制 16 字节到 [esi+0x35FC]

00B88D70  arg6 字符串 → [esi+0x360C]，截断 0x3F，strncpy
00B88DDF  arg8 字符串 → [esi+0x3658]，截断 0x3FF
00B88E3F  arg9 字符串 → [esi+0x3A58]，截断 0x3FF
00B88E90  mov cl,[ebp+0x2C]              ; arg10 字节 → [esi+0x3650] 模式标志

00B88E93  push 0x1C / call 0xB74220      ; 分配 0x1C 字节 → 存入 [ebp+0x2C]
00B88EA6  mov bx, word [ebp+0x10]        ; ★ arg3 = 0x331C658 的长度字
00B88EAC  mov [ebp-4], 0
00B88EB3  movzx edx,bx / push edi(0) / push edx
00B88EBA  call 0x4AA4A0                  ; 构造底层 socket/流对象
00B88EBF  mov edi,eax                    ; 新对象

00B88EC1..00B88EF0  释放旧 [esi+0x35F4]（虚析构）
00B88EF2  mov [esi+0x35F4],edi
00B88EF8..00B88F00  edi+4 交给 [0xCA8128]（引用计数/AddRef）

00B88F06  mov edx,[ebp+0xC]              ; arg2 = 0x331C5D8 缓冲区指针
00B88F09  mov ecx,[esi+0x35F4]
00B88F0F  movzx eax,bx                  ; ★ arg3 长度字
00B88F12  push eax / push edx
00B88F14  call 0xB75E00                  ; ★ 写入/校验
00B88F19  test al,al
00B88F1B  jne 0xB88F38                   ; 成功
00B88F1D  call 0x8435D0
00B88F22  xor al,al ; ret 0x28           ; ★ 出口 B：return 0

00B88F38  mov word [esi+0x35F8], bx      ; 记录长度
00B88F41  mov dword [esi+0x14], 0x20     ; 状态 0x20
00B88F48  call 0xB9A9E0                  ; ★ 进入 TLS/握手阶段，返回值即 al
```

### 1.3 `0xB88CC0` 对参数的校验与返回值语义

**只有两个显式返回 0 的出口**，且都不涉及“端口合法性”：

| 出口 | 条件 | 返回值 |
|---|---|---|
| A `0xB88CEB` | `[objA+0x20] != 0`，即对象已在连接中 | `0` |
| B `0xB88F1D` | `0xB75E00`（把 arg2 缓冲区写入流）返回 0 | `0` |
| 特殊 `0xB88DA7` | arg6 字符串含非 ASCII（`>=0x80`） | `1`（但置 `[+0x156C]=0x73` 错误码） |
| 正常 `0xB88F48` | `call 0xB9A9E0` 的返回值原样返回 | `0/1` |

关键点：**`0xB88CC0` 本身不做 host/port 解析，也不发起 DNS/TCP**。它把参数拷进成员、构造一个 0x1C 字节的流对象，然后调用 `0xB9A9E0` 做 TLS/握手。真正“连接”的动作在更下层。

`0xB75E00` 的关键分支如下：

```
00B75E07  mov edx,[esi+0xC]       ; 流对象容量成员
00B75E0C  test edx,edx
00B75E0E  jne 0xB75E1E            ; 非 0 才进入真正的容量检查
00B75E10  mov eax,[ebp+0xC]       ; 本次写入长度
00B75E13  add [esi+8],eax
00B75E16  pop esi
00B75E17  mov al,1
00B75E19  ret 8                   ; ★ 容量为 0 时，长度为 0 也直接成功
```

`0x4AA4A0` 新建该流对象时把 `[obj+0xC]` 置 0，所以这次调用里的 `0xB75E00` **正常不会失败**。因此观测到的 `0xB88CC0` 返回 0，静态上应归于最后的 `0xB9A9E0`，而不是 `+0x98` 的“长度校验失败”。

### 1.4 因此“`0xB88CC0` 返回 0”有三种可能（按证据强度）

1. **`[objA+0x20] != 0`**（对象已在忙）——静态可排除：`0xB88B80` 构造末尾显式置 `[esi+0x20]=0`（`0xB9A2C0`）。
2. **`0xB75E00` 失败**——需要流对象已有非 0 容量且长度超出该容量才可能失败；本次对象是刚构造的，`[obj+0xC]=0`，故正常路径下基本可排除。
3. **`0xB9A9E0` 内部连接/TLS/证书阶段失败**——它读取 `cacert.pem`（`0xB9A100` → `0xC76600`），并把错误码写入 `[esi+0x156C]`（如 `0x2E7` / `0x2DE` / `5`）。在 `+0x98=0` 时 `0xB75E00` 仍返回 1，因此当前最可靠的归因是这里（推断）。

> 事实：`+0x98` 为 0 时，`0xB75E00` 的入参长度为 0，但容量成员 `[obj+0xC]` 也为 0，函数仍返回 1。
> 推断：`+0x98` 不必为“返回 0”负责；真正失败点在 `0xB9A9E0`。

---

## 2. `0x641600`（ApplySettings）→ 配置块写入映射

`0x641600` 开头即 `memset(0x331C5C0, 0, 0xD40)`（`0x641616`），随后按 TCLS tag 逐槽填充。Vtable 槽位：`+0x24` = 取 DWORD，`+0x28` = 取字符串/长度，`+0x30`/`+0x38` = 数据块读取（见 `TenProxy.dll` 侧证据）。

### 2.1 写入表（偏移 → 来源 tag → 写入点）

| 偏移 | VA | 类型 | 来源 tag / 槽 | 写入指令 |
|---|---|---|---|---|
| `+0x000` | `0x0331C5C0` | dword | 函数返回值 | `00641BC8 mov [0x331c5c0],eax` |
| `+0x004` | `0x0331C5C4` | 4 B 缓冲 | tag `0x16`，`[vtable+0x28]` | `00641667 push 0x331c5c4` |
| `+0x014` | `0x0331C5D4` | dword | 常量 `0x10` | `0064164C mov [0x331c5d4],0x10` |
| `+0x018` | `0x0331C5D8` | 字符串缓冲 | tag `0x18` | `00641694 push 0x331c5d8` |
| `+0x098` | `0x0331C658` | dword（长度） | 常量 `0x80` + tag `0x18` 出参 | `00641685 mov [0x331c658],0x80` |
| `+0x09C` | `0x0331C65C` | 16 B 缓冲 | tag `0x19` | `006416C4 push 0x331c65c` |
| `+0x0AC` | `0x0331C66C` | dword | 常量 `0x10` | `006416B9 mov [0x331c66c],0x10` |
| `+0x0B0` | `0x0331C670` | 字符串缓冲 | tag `0x07` 第 2 字段 | `0064178C push 0x331c670` |
| `+0x4B0` | `0x0331CA70` | dword（长度） | tag `0x07`，clamp `0x400` | `00641772 mov [0x331ca70],0x400` |
| `+0x4B4` | `0x0331CA74` | 缓冲 | tag `0x1B` | `006417FE push 0x331ca74` |
| `+0x534` | `0x0331CAF4` | dword（长度） | tag `0x1B`，clamp `0x80` | `006417E4 mov [0x331caf4],0x80` |
| `+0x538` | `0x0331CAF8` | dword | tag `0x05` 数据块 | `0064185B push 0x331caf8` |
| `+0x53C..+0xD3F` | — | — | **无任何引用** | 全镜像扫描为 0 |

### 2.2 Tag 编号语义

`TenProxy.dll` 的 `+0x24` / `+0x28` 真身是 `0x10007DA0` / `0x10007EA0`：tag 作为**共享内存偏移表索引**使用（`tag*4` 取偏移，再加块基址），不是硬编码 switch。

| Tag | 用途（本地图证据） | 语义判定 |
|---|---|---|
| `0x05` | 数据块 → `+0x538` | 未知（TLS/指纹相关，`0x6415C0` 把它格式化成 `a.b.c.d` 字符串） |
| `0x07` | 字段1 → `0x81A9EC4`（port, word）；字段2 → `+0x0B0`；字段3 起 → `0x81A7F34` 等 | **HOST/PORT 组（事实）** |
| `0x12` | 仅取长度 `[ebp-0x420]` | 未知（大小查询） |
| `0x16` | → `+0x004` | 未知 |
| `0x18` | → `+0x018`，长度出参 `+0x098` | 未知（字符串，进 objA 成员 +0x3190 区） |
| `0x19` | → `+0x09C` | 未知（首字节作模式标志） |
| `0x1B` | → `+0x4B4`，长度 `+0x534` | 未知 |

另外 `TenProxy.dll` 内部有 tag **4 = QQSignature、5 = LoginKey** 的一次性凭证语义（取过即清零）。这里的 `0x05` 是**配置 tag**，与“LoginKey 一次性 tag=5”**不是同一编号空间**，不可混用（事实：两处编号来源不同）。

### 2.3 缺失 TCLS 时的默认值（全 0 之外的例外）

有 5 个偏移在无 TCLS 时会被初始化为非 0 容量，其余全 0：

| 偏移 | 默认值 |
|---|---|
| `+0x014` | `0x10` |
| `+0x098` | `0x80`（随后可能被 tag 0x18 的真实长度覆盖；无 TCLS 时保持 `0x80`） |
| `+0x4B0` | `0x400` |
| `+0x0AC` | `0x10` |
| `+0x534` | `0x80` |

> 注意：`+0x98` 被 `0x641685` 显式写成 `0x80`，**即使没有 TCLS 也不是 0**。但实测“全 0”是因为整块 `memset` 之后 `mov [0x331c658],0x80` 仍会执行，所以 `+0x98` 理论上应为 `0x80`——若实测读到 0，说明读取发生在 `0x641600` 执行之前，或该版本走了不同分支。**这一点标为待实测确认。**

---

## 3. 最小可填值集合

### 3.1 `0xB88CC0` 的“最小可填值”

首先给出严格结论：**配置块单独无法保证 `0xB88CC0` 返回非 0。** 该函数的最终返回值来自 `0xB9A9E0`，后者需要可用的 host/port、证书环境和握手对端。配置块只决定把它送进哪条分支、以及送给下层什么数据。

分两类如下：

**第一步：走真连接分支（objA）**

| 字段 | 值 | 理由 |
|---|---|---|
| `+0x000` | `1` | `0x7F2BA0` / `0x7F2C64` 两处开关 |
| `0x81A76A8` | host 字符串（如 `"127.0.0.1"`） | 进 objA 构造，非空才有目标 |
| `0x81A9EC4` | port（如 `443`） | objA 构造第 2 参数 |

**第二步：让它走到 `0xB9A9E0` 的调用点**

| 字段 | 建议值 | 理由 |
|---|---|---|
| `+0x098` | `0x80` | 它是 `0xB75E00` 的写入长度参数；0 也会成功，但 `0x80` 更接近正常 TCLS 形态 |
| `+0x018` | 任意 ASCII 字符串 | arg2，作为写入流的缓冲区 |
| `+0x004` | 任意 4 字节 | arg4，复制进 objA 的 16 字节槽 |
| `+0x0B0` | 任意 ASCII 字符串 | arg8 |
| `+0x538` | 任意 dword | arg5 |
| `+0x09C[0]` | 任意字节 | arg1 的首字节，也是后续对象 16 字节槽 |
| arg6 (`ebp-0x4C`) | 由 `0x7F2B30` 生成 | 非 ASCII（`>=0x80`）会走 `0x73` 错误路径；false 分支传 0 |

上述配置能让函数完成对象赋值、构造和 `0xB75E00` 调用，但**不能绕过 `0xB9A9E0`**。

### 3.2 本机联调可直接使用的值

```
0x331C5C0  dword   = 1                      ; 开真连接分支
0x81A76A8  cstr    = "127.0.0.1"            ; HOST
0x81A9EC4  word    = 443                    ; PORT（host 侧用 TLS 时）
0x331C658  dword   = 0x80                   ; +0x98 长度；0 也不是已证实的失败原因
0x331C5D8   cstr   = "codol"                ; +0x18，纯 ASCII 即可
0x331C5C4  dword   = 0x00000001             ; +0x04，任意非 0
0x331C670   cstr   = "codol"                ; +0xB0
0x331CAF8  dword   = 0x00000000             ; +0x538，可保持 0（仅作指纹格式串）
0x331C65C  byte[0]= 0x00                    ; +0x9C 模式标志
```

> 注意：`0x81A76A8` 是**全局 char 缓冲**（`tag 0x07` 字段1，最大 `0x400`），不是指针。直接写字符串即可。

### 3.3 可直接验证的 Python 骨架（不执行，仅示意）

```python
# 需要已提权的进程写内存句柄；本文件不包含实际写入代码
plan = [
    (0x331C5C0, b"\x01\x00\x00\x00"),
    (0x331C658, b"\x80\x00\x00\x00"),
    (0x331C5C4, b"\x01\x00\x00\x00"),
    (0x331C5D8, b"codol\x00"),
    (0x331C670, b"codol\x00"),
    (0x81A76A8, b"127.0.0.1\x00"),
    (0x81A9EC4, b"\xbb\x01"),            # 443 little-endian
]
```

---

## 4. 结论（严格区分事实与推断）

**事实**

1. `0xB88CC0` 是 `thiscall + ret 0x28`（10 参数），全镜像唯一调用者是 `0x7F2D2A`；它不解析 host/port，也不发起 DNS/TCP。
2. `0xB88CC0` 只有两个返回 0 的静态出口：`[objA+0x20]!=0`，以及 `0xB75E00` 返回 0。
3. 配置块 `0x331C5C0` 中，`0x641600` 实际只写 12 个偏移；`+0x53C..+0xD3F` 在整个镜像里**零引用**。
4. 配置块首 dword 在整个镜像里**没有任何地方写入常量 1**，只有 `0x641BC8` 从 `ApplySettings` 返回值写入。
5. `+0x98` 是 `+0x18` 缓冲区的长度出参（默认 `0x80`），**不是端口**；端口是独立全局 `0x81A9EC4`（word）。
6. `0x641600` 的配置来源是 TCLS 命名共享内存（`TCLS_SHAREDMEMEMORY<pid>`），非注册表。

**推断（未证实）**

1. 运行期把首 dword 改成 1 后仍失败，最可能是 `0xB9A9E0` 的连接/TLS/握手阶段返回 0；具体是 host/port 无效、证书路径或服务端协议失败，当前静态证据不足以区分。
2. `+0x98=0` 不是已证实的失败原因；`0xB75E00` 的零容量分支会直接返回 1。

**未解**

1. Tag `0x05/0x16/0x18/0x19/0x1B` 的**业务语义**未解——`TenProxy.dll` 的 tag 表是运行期共享内存，镜像内无静态映射。
2. `+0x53C..+0xD3F` 这 2 KB 区域的用途未解（静态零引用不等于运行期不用，可能存在寄存器间接寻址）。
3. `0xB9A9E0` 内部对 `cacert.pem` 的读取路径与各连接失败的精确判定未完全展开。

---

## 5. 复现命令

```text
python -X utf8 CODOLServer\_subagents\_cfg_dis.py disasm 0xB88CC0 0xB88F70
python -X utf8 CODOLServer\_subagents\_cfg_dis.py disasm 0x641600 0x641C00
python -X utf8 CODOLServer\_subagents\_cfg_scan_fields.py 0x331C5C0 0xD40
python -X utf8 CODOLServer\_subagents\_cfg_tenproxy_tags.py
python -X utf8 CODOLServer\_subagents\_cfg_build_report.py
```
