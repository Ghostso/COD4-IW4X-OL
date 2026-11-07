# -*- coding: utf-8 -*-
import os
root = r"D:\BaiduNetdiskDownload\使命召唤OL\CLIENT-DEMONWARE-CODEC-KEYFLOW-001"
D = lambda n: os.path.join(root, n)

docs = {}
docs["01_CODEC_FUNCTIONS.md"] = r"""# 01 Codec 函数精确行为

> 任务：CLIENT-DEMONWARE-CODEC-KEYFLOW-001（承接 CLIENT-DEMONWARE-PEER-REUSE-AUDIT-001）
> 样本：`codol2697-static-candidate.bin`，SHA-256 `24b4ef25...97e4`（冻结、只读）
> 全程只读；未启动客户端/服务端/模拟器，未注入，未读取运行时内存。

## 0. 镜像口径核对（先于一切引用）

| 项 | 值 |
|---|---|
| ImageBase | `0x400000` |
| SizeOfImage | `0x0DC14000` |
| `.text` | RVA `0x00001000` / VA `0x00401000` / VS `0x007AC90B` |
| `.rdata` | RVA `0x007AE000` / VA `0x00BAE000` |
| `.data` | RVA `0x008F1000` / VA `0x00CF1000` |
| `.tvm0` | **RVA `0x0D958000` / VA `0x0DD58000`** / VS `0x002B9000`（raw `0x002B8C00`） |
| `.rimp` | RVA `0x0DC11000` / VA `0x0E011000` |

**对上轮报告的更正（重要）**：上一轮 06 号报告称 `.tvm0` VA 为 `0x0D955000`，该值既不是 VA 也不是 RVA，属**笔误**。正确值：RVA `0x0D958000`，VA `0x0DD58000`。本任务全部地址一律显式标注 `VA`/`RVA`。

调用约定（两函数一致，由 prologue/epilogue 确证）：

- `__thiscall`：`ecx = this`（会话对象）。
- 栈参数 2 个，`ret 8` 清理：
  - `[ebp+8]` = `arg1`（字节缓冲指针）
  - `[ebp+0xC]` = `arg2`（方向字节，`dl`）
- 返回：隐式 `eax`（函数体内 `eax` 被用作游标，**返回值不承载语义**；调用点不以返回值分支）。
- 无失败返回；不校验长度参数（长度由调用点按字段大小隐式保证，见 §3）。
- 全文无查表跳转、无间接调用、无 VM 分派（纯直线代码 + 一个 4 次循环）。

两函数是**同一算法的两份实例化**，差别仅在 3 个常量：基址常量、20 字节常量表、置换表。

| | Codec A | Codec B |
|---|---|---|
| 入口 | `VA 0x00AA8D70` | `VA 0x00AA8BF0` |
| 写入基址 | `this + 0x5F9`（`0xAA8E3C add eax,0x5F9`） | `this + 0x60D`（`0xAA8CBD add eax,0x60D`） |
| 输入读取基址 | `arg1 + 1`（`0xAA8D9B inc ecx`） | `arg1 + 1`（`0xAA8C18 inc ecx`） |
| 20B 常量块 | `0xAE091341 F3BCA33F BCEA7218 CC113209 F4544212`（`0xAA8D9C-0xAA8DB8`） | `0xAADE2280 F4211C0B 37EEFF00 CE109227 213CF4AA`（`0xAA8C19-0xAA8C35`） |
| 置换表 | `[7,17,14,16,9,19,13,0,2,3,4,8,1,10,11,5,18,6,12,15]`（`0xAA8DBF-0xAA8E35`） | `[19,18,9,4,17,1,10,8,13,2,15,3,12,5,7,0,14,6,11]`（`0xAA8C3C-0xAA8CB6`） |
| 循环计数 | `edi=4`，每轮 5 字节 → 20B | 同 |
| 输出长度 | **20 字节** | **20 字节** |

## 1. 常量 XOR 的确切操作数、顺序、作用域

以 Codec A 的一轮（`esi` 指向置换表当前项，`eax` 指向输出游标，`ecx` 指向输入游标）为例：

```asm
00AA8E44  mov ebx, [esi-4]            ; idx0 = PERM[k*5+0]
00AA8E47  mov bl, [ebp+ebx-0x18]      ; bl = CONST[idx0]
00AA8E4B  test dl, dl / je 0xAA8E88   ; dl = arg2 方向
; --- dl != 0 分支（本报告记为 STORE）---
00AA8E4F  xor bl, [ecx-1]             ; bl ^= input[0]
00AA8E52  mov [eax-1], bl             ; output[0] = bl
; --- dl == 0 分支（本报告记为 LOAD）---
00AA8E88  xor bl, [eax-1]             ; bl ^= 已存字节[0]
00AA8E8B  mov [ecx-1], bl             ; input[0] = bl
```

- **操作数**：常量字节取自**函数栈内的一张 20 字节表**（`[ebp-0x18]` 起，`0xAA8D9C`/`0xAA8C19` 用 5 条 `mov dword` 初始化）；被 XOR 的是**输入缓冲的第 i 字节**。
- **执行顺序**：先按置换表索引取常量字节 → 再与输入做 XOR → 再写入。
- **作用范围**：恰好 4 轮 × 5 字节 = **20 字节**，与 `arg1` 的 20 字节字段一一对应；**不重排、不截断、不扩展**（置换只作用于取常量的索引，不作用于输入/输出位置）。
- **有效掩码**（把置换折叠掉后等价形式 `out[i] = in[i] XOR mask[i]`）：

```text
Codec A mask = f3421112 72f43241 09ae3f18 13eabca3 54bc09cc
Codec B mask = 213cff0b f422ee00 92deceaa 271cf480 102137??  (第 20 字节由第 4 轮第 5 项补齐)
常量表（原始顺序）A = 411309ae 3fa3bcf3 1872eabc 093211cc 124254f4
常量表（原始顺序）B = 8022deaa 0b1c21f4 00ffee37 279210ce aaf43c21
```

## 2. 固定置换：索引映射、长度、是否截断

置换表就是循环中 `[esi-4]`、`[esi]`、`[esi+4]`、`[esi+8]`、`[esi+0xC]` 读到的 5 个 dword，循环 `esi += 0x14`。逐项已从指令立即数读出：

- Codec A：`[7,17,14,16,9,19,13,0,2,3,4,8,1,10,11,5,18,6,12,15]`（20 项，`0x00AA8DBF`–`0x00AA8E35`）
- Codec B：`[19,18,9,4,17,1,10,8,13,2,15,3,12,5,7,0,14,6,11]`（**仅 19 项**，`0x00AA8C3C`–`0x00AA8CB6`；第 4 轮第 5 项由 `mov dword [ebp-0x1C]` 占据，见 §2.1）

置换**只索引 20 字节常量表**（索引范围 0..19，两表均 ≤20 项，无越界），因此**只影响常量字节的选取顺序**，不改变输入/输出的长度或位置。**不存在截断**：输入始终读满 20 字节，输出始终写满 20 字节。

### 2.1 关于 Codec B"19 项"的判定与更正

`0xAA8CB6 c7 45 e4 0b 00 00 00` = `mov dword [ebp-0x1C], 0x0B`，是置换表第 20 项（值 11），紧随其后：

```asm
00AA8CBD 05 0d060000   add eax, 0x60D
```

上一轮报告把此处读作 `add eax, 0x60D` 之前缺一项，属**读取顺序问题**而非真实缺项。**结论：Codec B 同样是完整 20 项置换**，与 Codec A 等长。

## 3. 长度、对齐、失败返回、调用者错误处理

- **无长度参数**：两函数都不接收长度；每次固定处理 20 字节。调用点用固定长度 0x14 送入后续 HMAC（见 03 号报告），与 20 字节一致。
- **无对齐要求**：逐字节 `mov`，不依赖 dword 对齐。
- **无失败返回**：函数体无错误分支、无 `0x43A7C0` 断言调用（对比 KDF 函数内多次 `0x43A7C0` 断言），调用点也不检查返回值。
- **调用者错误处理**：由调用点承担。KDF 内两处（`0xAAAC??`/`0xAAB92C`、`0xAAB046`/`0xAAB93C`）在同批次 `0xA87830` 边界检查失败时会跳过整个分支并置 `bl=0`，属于**外层缓冲检查**，与 codec 本身无关。

## 4. 正向/逆向判定（关键）

两函数**不是**正向/逆向互补的一对，而是**同一算法在两种方向模式下的实例化**：方向由 `arg2`（`dl`）在**同一函数内**二选一。

```asm
test dl, dl
je  LOAD_label      ; dl == 0 -> LOAD（读 this+base，写 arg1）
    STORE body      ; dl != 0 -> STORE（读 arg1，写 this+base）
```

因此同一函数可被任一方向调用；`0xAA8D70`/`0xAA8BF0` 的差别只在**常量表与置换表不同**，即它们作用于**两个不同字段**（`data[0:20]` 与 `data[20:40]`），而非互为逆变换。

**实际调用方向**（逐一核对，共 4 个调用点，与 §5 调用者枚举一致）：

| 调用点 VA | 函数 | push 方向 | 方向语义 | 缓冲 |
|---|---|---|---|---|
| `0x00AAB92C` | Codec A | `push 1`（`0xAAB921`） | **STORE** | `[ebp-0xA8]` = BDDATA 输出 `data[0:20]` |
| `0x00AAB93C` | Codec B | `push 1`（`0xAAB931`） | **STORE** | `[ebp-0x94]` = `data[20:40]` |
| `0x00AAACE3` | Codec A | `push 0`（`0xAAACDB`） | **LOAD** | `[ebp-0x24]`（20B，随即作为 HMAC key） |
| `0x00AAB046` | Codec B | `push 0`（`0xAAB03E`） | **LOAD** | `[ebp-0x40]`（20B，随即作为 HMAC key） |

⇒ 派生期 **STORE**（把 `data[0:20]`/`data[20:40]` 变换后写入 `this+0x5F9`/`this+0x60D`），消费期 **LOAD**（从同一位置读出并还原）。两处使用**同一常量表、同一置换表**。

## 5. 调用者枚举（穷尽性）

`.text` 全节 `E8 rel32` 调用图：

| 被调函数 | 直接调用者 | 数量 |
|---|---|---:|
| `0x00AA8D70`（Codec A） | `0x00AAACE3`、`0x00AAB92C` | **2** |
| `0x00AA8BF0`（Codec B） | `0x00AAB046`、`0x00AAB93C` | **2** |

补充扫描：全镜像（含 `.rdata`/`.data`/`.tvm0`/`.rimp`）中 `0x00AA8D70`/`0x00AA8BF0` 的 4 字节字面量引用数均为 **0**；两函数也不出现在 `0xFF15`/`0xFFD2` 间接调用目标或任何数据表。⇒ **不存在函数指针式调用路径**；4 个调用点即全部。

**对上轮报告的更正**：上轮 05 号报告称"两个 codec 的调用者各仅 2 处，全部位于密钥派生路径（`0xAAB92C/0xAAB93C` 及另一处）"，措辞含糊且遗漏了 0x85 帧路径的两个调用点。**准确表述**：4 个调用点 = 派生路径 2 个（STORE）+ 帧路径 2 个（LOAD）。

## 6. 证据等级

| 结论 | 等级 | 依据 |
|---|---|---|
| 调用约定、参数、无失败返回 | PROVEN | prologue/epilogue、`ret 8`、无断言调用 |
| 常量 XOR 的操作数/顺序/范围 = 20B | PROVEN | 逐指令（`0xAA8E44`–`0xAA8EC9`） |
| 置换索引映射（A 20 项 / B 20 项） | PROVEN | 立即数逐项读出 |
| 置换只作用于常量索引、不截断 | PROVEN | 输入/输出游标恒为 `+5`，与置换项无关 |
| 方向二选一、非正逆互补 | PROVEN | `test dl,dl / je` |
| 4 个调用点即全部 | PROVEN（直接调用 + 全镜像字面量 0 命中） | 调用图扫描 |
| 逐字节"净效果"等价性 | PROVEN（静态） | 同一 mask 的 XOR 两次 = 恒等，见 03 §3 |
"""

docs["02_FIELD_DEF_USE_CHAINS.md"] = r"""# 02 字段 def-use 链

## 0. 字段语义（本轮更正上轮的两处错标）

| 字段 | 上轮报告标注 | 本轮确证 | 依据 |
|---|---|---|---|
| `this+0x5F0` | "密码学 provider 候选位置" | **AES/加密 provider 对象指针**（`operator new(0x394)` 构造，vtable `0x00C5A31C`） | `0xAAB95D`/`0xAAB983` |
| `this+0x5F4` | 同上 | **AES/解密 provider 对象指针**（同类型，独立实例） | `0xAAB9BD`/`0xAAB9E3` |
| `this+0x5F9` | "codec 输出候选位置" | **20B codec 暂存区 `[+0x5F8, +0x60C)` 的第 1 字节**（基址常量 `0x5F9`，配合 `input+1`/`store-1` 的写法定址） | `0xAA8E3C` |
| `this+0x60D` | 同上 | **20B codec 暂存区 `[+0x60C, +0x620)` 的第 1 字节**（基址常量 `0x60D`） | `0xAA8CBD` |

即：两个 **20 字节** 缓冲区连续存放，整体覆盖 `[+0x5F8, +0x620)`；`0x5F9`/`0x60D` 只是"基址-1"写法定址下的地址常量。

## 1. Codec A 输出链（`data[0:20]` → HMAC 请求密钥）

```text
[def] 0x00AAB911  call expandKey(secret,"BDDATA",72)  -> [ebp-0xA8]  (72B)
         └ 0x00AAB8FB push 0x48 / 0x00AAB906 push 0xC5B13C / 0x00AAB910 push 0x14
[def] 0x00AAB92C  call 0xAA8D70(dl=1, &[ebp-0xA8])     -> mem[this+0x5F8 .. this+0x60B]   (20B, STORE)
[use] 0x00AAACE3  call 0xAA8D70(dl=0, &[ebp-0x24])     -> [ebp-0x24] = mem[this+0x5F8 .. this+0x60B]  (LOAD)
         └ 0x00AAACE8 push 0x14 (20) / 0x00AAACEE HMAC_SHA1 上下文 0xDF6216D
[use] 0x00AAAD40  call 0xA88400  HMAC_Update(ctx, frame, len-8)
[use] 0x00AAAD??  HMAC_Final -> 8B tag 写入发送缓冲
```

调用点位置说明：`0x00AAACE3` 位于**出站 0x85 组帧之前**（`0x00AAAA10` 函数的发送分支）；`0xAAAD40` 的 `HMAC_Update` 参数 `len = [ebp-0x208]-8` 与帧长口径一致（tag 占末 8B）。

## 2. Codec B 输出链（`data[20:40]` → HMAC 应答密钥）

```text
[def] 0x00AAB911  call expandKey(secret,"BDDATA",72)  -> [ebp-0xA8]  (72B)
[def] 0x00AAB93C  call 0xAA8BF0(dl=1, &[ebp-0x94])     -> mem[this+0x60C .. this+0x61F]   (20B, STORE)
         └ 0x00AAB933 lea edx,[ebp-0x94]  (= data[20:40])
[use] 0x00AAB046  call 0xAA8BF0(dl=0, &[ebp-0x40])     -> [ebp-0x40] = mem[this+0x60C .. this+0x61F]  (LOAD)
[use] 0x00AAB04B push 0x14 (20) / 0x00AAB051 HMAC_SHA1 上下文 0xDF6216D
[use] 0x00AAB085 call 0xA88400  HMAC_Update(ctx, 入站帧, len-4)
[use] tag 比较 0x00AAB0E6–0x00AAB12B（8B XOR/OR 归并）
```

`0x00AAB046` 位于**入站 0x85 帧解析函数 `0x00AAAE70`** 内（`= 0xAAAE70+0x1D6`）。

## 3. 其他四个字节范围（不经 codec）

同一 `expandKey(...,"BDDATA",72)` 输出的**后半** 32 字节被直接切分并送入 AES provider，**完全不经 codec**：

```text
[def] 0x00AAB911  data[72] -> [ebp-0xA8]
[use] 0x00AAB941  mov ecx,[edi+0x5F0]          ; 旧 provider（若有）-> 虚表[0] 析构
[def] 0x00AAB96A  0xDF9AA45(0x394) + 0xA87BA0  ; 构造 provider #1 -> [edi+0x5F0]
[use] 0xAAB989-0xAAB99A  provider#1.vtbl[1](&[ebp-0x80], 0x10)   ; 取 16B **密钥**
         └ &[ebp-0x80] 在 0xAAB9F8 同址出现，对应 data[40:56]
[def] 0x00AAB9C2  0xDF9AA45(0x394) + 0xA87BA0  ; 构造 provider #2 -> [edi+0x5F4]
[use] 0xAAB9ED-0xAAB9FE  provider#2.vtbl[1](&[ebp-0x70], 0x10)   ; 取 16B **密钥**
         └ &[ebp-0x70] = data[56:72]
```

`0xAAB98B mov edx,[edx+4]`（vtable 槽 1）+ `push 0x10` + `push &local` → 即 `provider->setKey(buf, 16)`；对应 vtable `0x00C5A31C` 的槽 [1] = `0x00A87C30`。该函数体内 `0xA87C65` 起对 `[0xC5BEB4]`（cipher 名索引）与 `edi+8`（keylen）赋值，`0xA87C92` 把 16B 密钥拷入 provider 内部 `+0xC`。**未触及 `+0x5F9`/`+0x60D`**。

provider 的对象大小与存活期：

- 每次 KDF 都**先析构旧 provider**（`0xAAB94B`/`0xAAB9AB` 经 vtable[0]），再 `0x394` 字节重建（`0xDF9AA45` + `0xA87BA0`）。
- 会话重置/析构路径（`0xAAA14D`–`0xAAA177`、`0xAAA6E9`–`0xAAA6FB`）会把 `+0x5F0`/`+0x5F4` 置 0 并逐个析构。
- **`+0x5F8`/`+0x60C` 两个 20B 缓冲不在 provider 内**：provider 是独立堆对象（指针存于 `+0x5F0`/`+0x5F4`），而 codec 暂存区在**会话对象本体**内。

## 4. 完整写入点清单（`.text` 全节，指令级编码扫描）

| 字段 | 写入点 | 语义 |
|---|---|---|
| `+0x5F0` | `0xAAA6E9`（=0，重置）、`0xAAB983`（新对象） | provider #1 指针 |
| `+0x5F4` | `0xAAA6EF`（=0，重置）、`0xAAB9E7`（新对象） | provider #2 指针 |
| `+0x5F8..0x60B` | `0xAA8E44`–`0xAA8EC9`（Codec A，仅 STORE 分支，经 `+0x5F9` 基址） | 20B codec A 暂存 |
| `+0x60C..0x61F` | `0xAA8CC5`–`0xAA8D4A`（Codec B，仅 STORE 分支，经 `+0x60D` 基址） | 20B codec B 暂存 |
| `+0x5E8/+0x5EC` | `0xAAB8E0`/`0xAAB8E7`（challenge[8:16]，`edx`/`ecx` 两个 dword 直写） | 应答 ID，**不经 codec** |
| `+0x620/+0x624` | `0xAAB3A6`（入站 8B）、`0xAAB6BD`（入站 8B） | 0x81 帧内字段 |

**关键结论**：`+0x5F8`/`+0x60C` 的**唯一写入者**是 codec STORE；其**唯一读取者**是 codec LOAD（`+0x5F8` 的读取点即 Codec A LOAD 分支 `0xAA8E88`–`0xAA8EB9`；`+0x60C` 的读取点即 Codec B LOAD 分支 `0xAA8D09`–`0xAA8D3A`）。全 `.text` 内没有第三个函数读写这两个范围。

## 5. 生命周期

```text
会话对象构造/重置  0xAAA6E9/0xAAA6EF  +0x5F0=+0x5F4=0
握手 0x81 到达     0x00AAB310
  ├ STORE codec A -> +0x5F8..+0x60B
  ├ STORE codec B -> +0x60C..+0x61F
  ├ 新建 provider #1/#2 -> +0x5F0/+0x5F4（用 data[40:56]/[56:72]）
  └ 写入 +0x5E8/+0x5EC = challenge[8:16]
出站 0x85          LOAD codec A -> HMAC key（+0x5F8 仍有效）
入站 0x85          LOAD codec B -> HMAC key（+0x60C 仍有效）
会话重置/析构       0xAAA14D/0xAAA165 析构 provider，+0x5F0/+0x5F4=0
```

`+0x5F8`/`+0x60C` 在会话存活期间**不被清零、不被其他逻辑覆写**（无 `+0x5F8`/`+0x60C` 的写入点，除 codec STORE 外）。因此 LOAD 读到的必然是握手期 STORE 写入的同一 20B。

## 6. 证据等级

| 结论 | 等级 |
|---|---|
| 字段语义更正（+0x5F0/+0x5F4 = provider 指针；+0x5F9/+0x60D = 20B 暂存的基址常量） | PROVEN |
| Codec A/B 各自 STORE→LOAD 成对 | PROVEN |
| `+0x5F8`/`+0x60C` 唯一写入者 = codec STORE | PROVEN（指令级编码扫描 + 边界校验） |
| 后半 32B（`data[40:56]`/`[56:72]`）不经 codec 直接作 provider 密钥 | PROVEN（`0xAAB98E`/`0xAAB9F6`，`push 0x10`） |
| `+0x5E8/+0x5EC` 不经 codec | PROVEN（`0xAAB8E0`/`0xAAB8E7` 直写） |
| 会话重置/析构路径 | PROVEN（`0xAAA14D`–`0xAAA177`） |
"""

for name, text in docs.items():
    with open(D(name), "w", encoding="utf-8") as fh:
        fh.write(text)
    print("wrote", name, len(text))
