# E24 `0xA87D50` 缓冲数据流

## 1. 调用点与调用约定

**调用点**：`0x6AB146`（`0x6AAE70` HMAC 校验成功路径）

```asm
6AB140  mov  eax,[ebp-0x220]    ; = span 长度（0x6AAF9A 计算）
6AB146  mov  ecx,[edi+0x5F4]    ; ecx = 协商对象 (this)
6AB14C  mov  edx,[ecx]          ; vptr
6AB14E  mov  edx,[edx+0xC]      ; slot 索引 3
6AB151  push eax                ; arg4 = 长度
6AB152  mov  eax,[ebp-0x210]    ; span 缓冲基址（0x6AAF3D 计算）
6AB158  push eax                ; arg3
6AB159  push eax                ; arg2（与 arg3 同值）
6AB15A  lea  eax,[ebp-0x50]
6AB15D  push eax                ; arg1 = 16 字节临时块
6AB15E  call edx
6AB166  test al,al
6AB168  setne al
```

**被调函数 `0xA87D50`（RVA `0x687D50`）**：

```asm
687D50  push ebp; mov ebp,esp
687D53  mov  eax,[ebp+8]        ; arg1
687D58  lea  esi,[ecx+0xC]      ; this+0xC
687D5B  push esi                ; 第3参 = this+0xC
687D5C  push 0x10               ; 第2参 = 0x10
687D5E  push eax                ; 第1参 = arg1
687D61  call 0xACE180
687D69  test eax,eax; jne fail  ; 非0 => 失败
687D6D  mov  ecx,[ebp+0x14]     ; arg4
687D70  mov  edx,[ebp+0x10]     ; arg3
687D73  mov  eax,[ebp+0xC]      ; arg2
687D76  push esi; push ecx; push edx; push eax
687D7A  call 0xACE1B0
687D82  test eax,eax; jne fail
687D86  mov al,1; ret 0x10
```

**裁定**：`0xA87D50` 为 **thiscall + 4 栈参数 + `ret 0x10`**，返回 `bool`（1=成功，0=失败）。可写为 PROVEN。

## 2. 参数区分（更正 E-23 的表述）

E-23 写 "`(this, buf, buf, len)`"，易被读作 arg2 与 arg3 是同一缓冲。实测：

| 参数 | 来源 | 去向 |
|---|---|---|
| arg1 `[ebp+8]` | `0x6AB15A` `lea eax,[ebp-0x50]` | `0xACE180` 第1参（16 字节临时块） |
| arg2 `[ebp+0xC]` | `0x6AB159` `push eax`（= span 基址） | `0xACE1B0` 第1参 |
| arg3 `[ebp+0x10]` | `0x6AB158` `push eax`（= span 基址） | `0xACE1B0` 第2参 |
| arg4 `[ebp+0x14]` | `0x6AB151` `push eax`（= span 长度） | `0xACE1B0` 第3参 |

即：**arg2 与 arg3 确实同值**（都指向 span），但 arg1 是独立的 16 字节块；两者不混用。E-23 的括号写法在数值上正确，但掩盖了 arg1 ≠ arg2 的事实。

## 3. `0xACE180` 的 16 字节检查（arg1 → this+0x14）

```asm
6CE180  push ebp; mov ebp,esp
6CE183  mov  eax,[ebp+0xC]      ; 第2参 = 0x10
6CE186  mov  ecx,[ebp+0x10]     ; 第3参 = this+0xC
6CE189  cmp  eax,[ecx+4]        ; 比较 this+0x10 处 dword 与 0x10
6CE18C  je   0xACE195
6CE18E  mov  eax,0x10           ; 不相等 -> 返回 0x10（错误码）
6CE193  ret
6CE195  push eax                ; len
6CE196  mov  eax,[ebp+8]        ; 第1参 = arg1
6CE199  push eax
6CE19A  add  ecx,8              ; this+0x14
6CE19D  push ecx
6CE19E  call 0xB4FF60           ; memcpy(this+0x14, arg1, 0x10)
6CE1A6  xor  eax,eax            ; 返回 0 = 成功
6CE1A9  ret
```

- `0xB4FF60` 是 `memcpy`（`rep movsd` + 尾字节分支，见实测反汇编）。
- **比较对象**：`(this+0xC)+4` = `this+0x10` 处的 dword 与常量 `0x10`。
- **写入**：把 arg1 的 0x10 字节拷入 `(this+0xC)+8` = `this+0x14`。
- **失败**：返回 `0x10`。

**裁定**：该检查实际是"**16 字节定长拷入 + 长度守卫**"，不是摘要比对。可写为 PROVEN。

> 未闭合：`this+0x10` 处长度值 `0x10` 的**最初写入点**未定位（构造器 `0x687BA0` 在 `0x687BC4..0x687BDC` 之间以 `push 0x10; call 0xA888A0` 建立基类子对象，但其 `ecx` 与 `this+0xC` 的偏移关系尚未逐指令确认）。该项标 BLOCKED，不影响本节结论。

> 更正 E-23：E-23 描述为 `cmp [ecx], len` 形态，实测为 `cmp 0x10, [ecx+4]`（长度字段在 `this+0x10`，非 `this+0xC`）。

## 4. `0xACE1B0` 的数据流

```asm
6CE1B0  ...
6CE1CB  mov  ecx,[esi]          ; esi = this+0xC -> 描述符索引
6CE1D4  call 0xE00F7FB          ; 索引合法性/查询
6CE1E0  mov  ecx,[esi+4]        ; this+0x10 = 密钥长度
6CE1E3  cmp  ecx,1   jl fail
6CE1EC  cmp  ecx,0x80 jg fail
6CE1F9  mov  edi,[ebp+0x10]     ; arg3 = span 长度
6CE1FE  div  ecx                ; 长度整除检查
6CE206  test cl,3   jne fail    ; 4 对齐
6CE221  mov  ecx,[esi]          ; 索引
6CE223  lea  edx,[ecx+ecx*2]; shl edx,5    ; idx*0x60
6CE229  mov  ecx,[edx+0xD48F64] ; <== cipher 表项
6CE22F  test ecx,ecx
6CE231  je   0xACE25A
6CE233  ... push esi+0x88, esi+8, len, buf, this
6CE244  call ecx                 ; 表驱动函数
```

无表项分支（`0x6CE25A` 起）使用 `[edx+0xD48F48]` 的另一表指针做 XOR 流变换。

**裁定**：`0xACE1B0` 是"**长度校验 + cipher 描述符查表 + 流变换/回调**"，返回 0 表示成功。其核心数据依赖 `.data` 基址 `0xD48F48`/`0xD48F64` 的运行时表。可写为 INFERRED（强）；表的静态内容 BLOCKED。

## 5. 缓冲来源（`0x6AAE70` 内）

| 局部 | 计算点 | 含义 |
|---|---|---|
| `[ebp-0x210]` | `0x6AAF3A` `lea edx,[esi+eax]` | span 基址 = 帧基址 + 偏移 |
| `[ebp-0x220]` | `0x6AAF98` `sub eax,edx` | span 长度 |
| `[ebp-0x50]` | `0x6AAF08` `lea eax,[ebp-0x50]` | 16 字节临时块（供 `0xACE180`） |
| `[ebp-0x224]` | `0x6AAF13` | 消息码/计数器（随后与 `[edi+0x5D0]` 比较） |

`[ebp-0x50]` 在 `0x6AAF06..0x6AAF22` 由第二次 `0xA878A0` 调用填充；其内容源自入站帧（`esi` = arg1 帧缓冲）。

**裁定**：`0xA87D50` 的两个缓冲参数最终都指向**同一入站帧 span**，但用途分离：arg1 → 16 字节长度/密钥透传；arg2/arg3 → span 本体（长度 arg4）。可写为 INFERRED（强）。

## 6. 与帧码的关系

`0x6AAE70` 只在**阶段 3 + msgcode 0x85** 被调用（`0x6AC2D9..0x6AC2F0`），因此：

- `0xA87D50` 的调用**必然**发生在 msgcode == `0x85` 的路径上（PROVEN）。
- `0xA87D50` 与 `0x81/0x83/0x84` **无直接数据流**（那三条走 `0x6AB310` / `0x6AB260` / `0x6A9690`）。

| 帧码 | 是否可达 `0xA87D50` | 依据 |
|---|---|---|
| 0x81 | 否 | 走 `0x6AB310`（阶段 1） |
| 0x83 | 否 | 走 `0x6AB260`（阶段 2） |
| 0x84 | 否 | 走 `0x6A9690`（阶段 2/3） |
| 0x85 | **是** | `0x6AC2DC` → `0x6AC2F0` `call 0x6AAE70` → `0x6AB146` slot+3 |
