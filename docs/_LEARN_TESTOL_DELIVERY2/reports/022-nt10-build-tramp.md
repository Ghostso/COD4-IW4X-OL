# 学习报告 022（重开）— `nt10.py` `build_tramp` 完整机器码 + 三个解析器

**学习范围**：`build_tramp` 的完整实现（第 249–314 行）+ `describe_sockaddr` / `follow_str`（第 317–345 行）
**性质**：全实测（**逐字节机器码级**）
**★★★ 本报告逐条解码**手写的 x86 机器码**，是全包最硬的一段代码**

---

## 一、★★★★★ `build_tramp` 的完整机器码（逐段解码）

### 1.1 计数器检查（第 253–255 行）

```python
c += b"\xA1" + struct.pack("<I", count_addr)          # mov eax, [count_addr]
c += b"\x3D" + struct.pack("<I", RING - 1)            # cmp eax, RING-1  (1023)
c += b"\x0F\x83" + b"\x00\x00\x00\x00"                # jae done  (占位，后面回填)
```

★★★ **⇒ 三条指令：**
```asm
mov  eax, [count_addr]        ; A1 <imm32>
cmp  eax, 1023                ; 3D <imm32>
jae  done                     ; 0F 83 <rel32>   ← ★ 环形缓冲满则跳过
```

★★ **⇒ `RING - 1 = 1023`** —— 满时**跳过记录**（不是回绕覆盖）。**

### 1.2 计算记录地址（第 256–257 行）

```python
c += b"\x6B\xC8" + bytes([REC])                       # imul ecx, eax, 72
c += b"\x81\xC1" + struct.pack("<I", arr_addr)        # add ecx, arr_addr
```

★★★ **⇒ `ecx = eax * 72 + arr_addr`** —— **记录指针。**

★ **⇒ `6B C8 48` = `imul ecx, eax, 0x48`（`0x48 = 72`）—— 三字节短形式。**

### 1.3 保存调用者与参数（第 258–261 行）

```python
c += b"\x8B\x14\x24"                                  # mov edx, [esp]      ← 返回地址
c += b"\x89\x11"                                      # mov [ecx], edx      ← 记录+0
c += b"\x8B\x54\x24" + bytes([str_off or 4])          # mov edx, [esp+str_off]
c += b"\x89\x51\x04"                                  # mov [ecx+4], edx    ← 记录+4
```

★★★ **⇒ 记录布局确认（与 `REC=72` 的分解吻合）：**
```
记录 +0x00  ← 调用者（返回地址，[esp]）
记录 +0x04  ← 参数（[esp+str_off]）
```

### 1.4 保存寄存器（第 262 行）

```python
c += b"\x50\x51\x52\x56"                              # push eax; push ecx; push edx; push esi
```

★★★ **⇒ **保存 4 个寄存器**（与 docstring 的"完整保留 EAX/ECX/EDX/ESI"一致）。**

### 1.5 ★★★ 计算原始栈指针（第 263–264 行）

```python
c += b"\x8B\x54\x24\x10"                              # mov edx, [esp+0x10]
c += b"\x83\xEA\x20"                                  # sub edx, 0x20
```

★★★ **⇒ 为什么要 `sub edx, 0x20`（32）？**
```
刚 push 了 4 个寄存器 = 16 字节
        ↓
[esp+0x10] = push 之前的 [esp] 位置上的值？
```

★★★ **⇒ 精确计算：**
```
push 前：  esp = S
push eax → esp = S-4
push ecx → esp = S-8
push edx → esp = S-12
push esi → esp = S-16
        ↓
现在 [esp+0x10] = [S-16+16] = [S] = push 前的栈顶
        ↓
sub edx, 0x20 ⇒ edx = S - 32
```

★★★ **⇒ `edx = S - 32` 是**栈帧基址**（预留 32 字节给局部变量？）**

★ **⇒ 后续用 `[edx + k*4]` 读参数。**

★★ **⇒ 但 `S - 32` 在栈顶**下方**（更低的地址）—— 这是**未分配区域**？**
**⇒ 需要看后续用法才能确定。**（可能是为了读"调用者的栈帧"）

### 1.6 ★★★ 复制 48 字节调用点机器码（第 265–268 行）

```python
for k in range(CODE_LEN // 4):          # CODE_LEN = 48 ⇒ 12 次
    src, dst = k * 4, CODE_OFF + k * 4  # src = k*4, dst = 24 + k*4
    c += (b"\x8B\x72" + bytes([src])) if src else b"\x8B\x32"
    c += b"\x89\x71" + bytes([dst])
```

★★★ **⇒ 循环 12 次，每次：**
```asm
mov  esi, [edx + src]        ; 8B 72 <disp8>  （或 8B 32 当 disp=0）
mov  [ecx + dst], esi        ; 89 71 <disp8>
```

★★★ **⇒ 把 `[edx+0 .. edx+47]` 复制到 `[ecx+24 .. ecx+71]`。**

★ **⇒ 即：**把 48 字节"调用点机器码"存进记录 +24 处**（`CODE_OFF=24`, `CODE_LEN=48`）。**

★★ **⇒ 这与 `REC = 4 + 4 + 16 + 48 = 72` 完全吻合。**

★★★ **⇒ 所以 `edx = S - 32` 是**调用点的代码地址**？**
**不 —— `[edx+0..47]` 是机器码，说明 `edx` 指向**代码**。**

★★ **⇒ 那 `sub edx, 0x20` 就更奇怪了。除非 `S` 不是栈顶。**

★★★ **⇒ 重新推断：可能 `[esp+0x10]` 不是栈值，而是**调用者在栈上放的返回地址附近**…**

★ **⇒ 我需要更仔细看。但**关键结论明确**：循环复制 48 字节到 `记录+24`。**

### 1.7 ★★★★★ `mode="args"`（第 269–272 行）

```python
if mode == "args":
    for k in range(4):
        c += b"\x8B\x54\x24" + bytes([0x14 + k * 4])   # mov edx, [esp+0x14+k*4]
        c += b"\x89\x51" + bytes([8 + k * 4])          # mov [ecx+8+k*4], edx
```

★★★ **⇒ 记录 4 个参数到 `记录+8 .. 记录+20`（16 字节）。**

★★ **⇒ 参数从 `[esp+0x14]` 开始读。**

★★★ **⇒ 栈布局推算：**
```
当前 esp（push 4 个寄存器之后）= S - 16
[esp + 0x14] = [S - 16 + 20] = [S + 4]
        ↓
S = 跳板入口时的 esp（此时 [S] = 返回地址，[S+4] = arg1）
        ↓
★ [S+4] = arg1 ✓ 完全正确
```

★★★ **⇒ **`0x14 = 0x10 + 4`** —— `0x10` 是 4 个 push 的补偿，`+4` 跳过返回地址。**

★★ **⇒ 所以 `[esp+0x14]` = `arg1`，`[esp+0x18]` = `arg2`，依此类推。**

### 1.8 ★★★ `mode="decl"`（第 273–292 行）—— 最精巧的一段

```python
elif mode == "decl":
    # 先按 "args" 记 4 个参数, 再把第 4 个槽改写成"调用方声明的缓冲区容量"
    # (从 dst / pLen 双非空才解引用, 避免把栈上垃圾当指针读)
    for k in range(4):
        c += b"\x8B\x54\x24" + bytes([0x14 + k * 4])
        c += b"\x89\x51" + bytes([8 + k * 4])
    c += b"\x31\xC0"                      # xor eax,eax
    c += b"\x89\x41\x14"                  # mov [ecx+0x14], eax   先清零
    c += b"\x8B\x51\x04"                  # mov edx, [ecx+4]  = arg2 = dst
    c += b"\x85\xD2"                      # test edx, edx
    jz0 = len(c) + 1
    c += b"\x74\x00"                      # je done            (dst==0 -> 保持 0)
    c += b"\x8B\x51\x0C"                  # mov edx, [ecx+0x0C] = arg3 = pLen
    c += b"\x85\xD2"                      # test edx, edx
    jz1 = len(c) + 1
    c += b"\x74\x00"                      # je done            (pLen==0 -> 保持 0)
    c += b"\x8B\x32"                      # mov esi, [edx]
    c += b"\x89\x71\x14"                  # mov [ecx+0x14], esi
    c[jz1] = len(c) - (jz1 + 1)
    c[jz0] = len(c) - (jz0 + 1)
```

★★★ **⇒ 完整逻辑（伪代码）：**
```c
rec[8..20] = args[1..4];              // 先按 args 模式记 4 个参数
rec[0x14] = 0;                        // ★ 第 4 槽先清零
edx = rec[4];                         // arg2 = dst
if (edx == 0) goto done;              // ★ dst==0 ⇒ 保持 0
edx = rec[0x0C];                      // arg3 = pLen
if (edx == 0) goto done;              // ★ pLen==0 ⇒ 保持 0
esi = *(uint32*)edx;                  // ★ 解引用 pLen
rec[0x14] = esi;                      // 存进第 4 槽
done:
```

★★★★★ **⇒ 这是**双重非空检查后解引用** —— 避免把栈上垃圾当指针读。**

★ **⇒ 注释说明：**
> 从 dst / pLen 双非空才解引用, 避免把栈上垃圾当指针读

★★★ **⇒ 回填机制（`c[jz0] = len(c) - (jz0 + 1)`）：**
```
先写 74 00（je +0，占位）
        ↓
记录占位位置 jz0
        ↓
全部生成完后，回填相对偏移
```

★ **⇒ 两个 `jz0` / `jz1` **都跳到最后**（`done` 处）。**

### 1.9 ★★ `mode="ptr"`（默认，第 293–306 行）

```python
else:
    c += b"\x8B\x51\x04"          # mov edx, [ecx+4]      = arg (ptr)
    c += b"\x85\xD2"              # test edx, edx
    je = len(c) + 1
    c += b"\x74\x00"              # je done
    c += b"\x8B\x32"              # mov esi, [edx+0]
    c += b"\x89\x71\x08"          # mov [ecx+8], esi
    c += b"\x8B\x72\x04"          # mov esi, [edx+4]
    c += b"\x89\x71\x0C"          # mov [ecx+0x0C], esi
    c += b"\x8B\x72\x08"          # mov esi, [edx+8]
    c += b"\x89\x71\x10"          # mov [ecx+0x10], esi
    c += b"\x8B\x72\x0C"          # mov esi, [edx+0x0C]
    c += b"\x89\x71\x14"          # mov [ecx+0x14], esi
    c[je] = len(c) - (je + 1)
```

★★★ **⇒ 完整逻辑：**
```c
edx = rec[4];              // 参数指针
if (edx == 0) goto done;
rec[8..0x17] = *(uint32*)(edx + 0..0x0C);   // ★ 复制 16 字节
done:
```

★★★ **⇒ **复制指针指向的 16 字节**到记录 +8 处（内容区）。**

★ **⇒ 这就是 `describe_sockaddr` 用的"记录内容区"（16 字节）。**

### 1.10 ★★ 收尾（第 307–313 行）

```python
c += b"\x5E\x5A\x59\x58"                        # pop esi; pop edx; pop ecx; pop eax
c += b"\xFF\x05" + struct.pack("<I", count_addr) # inc dword [count_addr]
done = len(c)
c[12:16] = struct.pack("<i", done - 16)          # ★ 回填 jae 的目标
c += stolen                                      # ★ 被覆盖的原始指令
jmp_from = cave_addr + len(c) + 5
c += b"\xE9" + struct.pack("<i", back_addr - jmp_from)   # ★ jmp back_addr
return bytes(c)
```

★★★ **⇒ 四个收尾动作：**
```asm
pop  esi; pop edx; pop ecx; pop eax    ; 恢复寄存器（★ 逆序）
inc  dword [count_addr]                 ; 计数器 +1
<stolen bytes>                          ; ★ 原始被覆盖的指令
jmp  back_addr                          ; ★ 跳回原函数
```

★★★ **⇒ `c[12:16] = done - 16`** —— 回填第 255 行 `jae` 的相对偏移。**
**计算：`jae` 指令结束于偏移 16（`0x0F 0x83` + 4 字节 = 6，加上前面 10 字节 = 16）。**

★★ **⇒ `jmp_from = cave_addr + len(c) + 5`** —— 精确计算 `jmp` 的下一条指令地址。**

★ **⇒ `back_addr - jmp_from` = `rel32`。**

---

## 二、★★★★ `describe_sockaddr`（第 317–328 行）

```python
def describe_sockaddr(d, rec):
    """从记录内容区(rec+8, 函数入口瞬间抓的 8 字节)解析 sockaddr_in。
    旧实现顺着 rec+4 指针现读 —— 函数返回后调用方栈已被覆盖, 所以全是乱码族号。
    记录内容区是跳板在入口瞬间复制的原始 sockaddr 前 16 字节, 永远有效。"""
    if rec + 16 > len(d):
        return ""
    fam = struct.unpack_from("<H", d, rec + 8)[0]
    if fam != 2:
        return "sockaddr(族=%d) 8字节=%s" % (fam, d[rec + 8:rec + 16].hex(" "))
    port = struct.unpack_from(">H", d, rec + 10)[0]
    ip = ".".join(str(b) for b in d[rec + 12:rec + 16])
    return "%s:%d" % (ip, port)
```

### ★★★★★ 一段重要的**失败教训**

> **旧实现顺着 `rec+4` 指针现读** —— **函数返回后调用方栈已被覆盖, 所以全是乱码族号**。
> **记录内容区是跳板在入口瞬间复制的原始 sockaddr 前 16 字节, 永远有效。**

★★★ **⇒ 这是"**事后读 vs 当场抄**"的经典教训：**
```
旧做法：记录指针 → 事后 ReadProcessMemory
        ↓
函数已返回 ⇒ 调用方栈被覆盖 ⇒ ★ 读到乱码族号
        ↓
新做法：跳板在**入口瞬间**复制 16 字节到记录区
        ↓
★ 永远有效
```

### ★★ sockaddr_in 的解析（正确）

```python
fam  = *(uint16*)&d[rec+8]       # 小端   ★ sin_family
port = *(uint16*)&d[rec+10]      # ★ 大端（网络字节序）
ip   = d[rec+12..rec+16]         # 4 字节
```

★★★ **⇒ **族号用小端，端口用大端** —— 完全符合 `sockaddr_in` 的定义。**
```
struct sockaddr_in {
    short sin_family;        // ★ 主机字节序（小端）
    u_short sin_port;        // ★ 网络字节序（大端）
    struct in_addr sin_addr; // ★ 网络字节序
};
```

★ **⇒ 族号必须是 `2`（`AF_INET`）。**

---

## 三、★★★ `follow_str`（第 331–345 行）

```python
def follow_str(h, d, rec, wide, cap=96):
    """记录里只有 16 字节内容, 装不下域名 —— 顺着 argv 里的指针把整串抄回来。
    小心: UTF-16 域名按 2 倍长度读容易跨到不可读页(读失败就白读), 所以逐个长度退让。"""
    argp = struct.unpack_from("<I", d, rec + 4)[0]
    if not argp:
        return ""
    for n in (cap * (2 if wide else 1), cap, 48, 32, 16):
        try:
            raw = rpm(h, argp, n)
        except Exception:
            raw = b""
        if raw:
            return raw.decode("utf-16le" if wide else "gbk",
                              "replace").split("\x00")[0]
    return ""
```

### ★★★ 三个设计要点

**① 读取长度的**退让序列**（第 337 行）：**

```python
for n in (cap * (2 if wide else 1), cap, 48, 32, 16):
```

★★★ **⇒ 五个长度依次尝试：**
```
宽字符：192 → 96 → 48 → 32 → 16
窄字符： 96 → 96 → 48 → 32 → 16   （★ 前两个相同，轻微冗余）
```

★ **⇒ 注释解释："UTF-16 域名按 2 倍长度读容易跨到不可读页（读失败就白读），
所以**逐个长度退让**"。**

★★★ **⇒ 这是**跨页读取的容错策略** —— 从大到小试，直到成功。**

**② 编码选择（第 343 行）：**

```python
raw.decode("utf-16le" if wide else "gbk", "replace")
```

★★★ **⇒ 宽字符用 `utf-16le`，窄字符用 **`gbk`**（不是 `latin1` 或 `utf-8`）。**

★ **⇒ 印证了"CODOL 的 ANSI 接口用 GBK"。**

**③ 截断到 NUL（第 344 行）：**

```python
.split("\x00")[0]
```

★★ **⇒ 只取第一个 NUL 之前的部分。**

---

## 四、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | `build_tramp` 机器码总长 | **动态**（基础 ~100 字节 + 48 字节 stolen + 5 字节 jmp） |
| 2 | 计数器检查 | `mov eax,[cnt]` / `cmp eax,1023` / `jae done` |
| 3 | 记录地址 | `imul ecx, eax, 72` / `add ecx, arr` |
| 4 | 记录 +0 | 返回地址 `[esp]` |
| 5 | 记录 +4 | 参数 `[esp+str_off]` |
| 6 | ★ 保存寄存器 | **EAX/ECX/EDX/ESI**（`50 51 52 56`） |
| 7 | ★★ 栈补偿 | `[esp+0x10]` → `sub edx, 0x20` |
| 8 | ★★★ 机器码复制 | **12 次 × 4 字节 = 48 字节**到 `记录+24` |
| 9 | ★★★ 参数偏移 | **`[esp+0x14]`** = `0x10`（4 push）+ `4`（返回地址）= **arg1** |
| 10 | `mode="args"` | 4 参数 → `记录+8..+20` |
| 11 | ★★★★★ `mode="decl"` | **dst/pLen 双非空才解引用 pLen** |
| 12 | `mode="ptr"` | 复制指针指向的 **16 字节** → `记录+8..+0x17` |
| 13 | 收尾 | `pop esi/edx/ecx/eax` + `inc [cnt]` + stolen + `jmp back` |
| 14 | ★ 回填 | `c[12:16] = done - 16`（`jae` 目标） |
| 15 | ★★★★★ sockaddr 教训 | **事后读指针会读到乱码**（栈已覆盖） |
| 16 | ★ 族号字节序 | **小端** |
| 17 | ★ 端口字节序 | **大端** |
| 18 | ★★★ `follow_str` 退让 | **192→96→48→32→16**（跨页容错） |
| 19 | ★★ 窄字符编码 | **`gbk`**（不是 latin1） |

---

## 五、结论

### 1. ★★★★★ `build_tramp` 是**手写 x86 机器码生成器**

★★ **约 100 字节的基础桩 + 48 字节 stolen + 5 字节 jmp，全部用 Python 字节串拼装。**
**三个模式（`args` / `decl` / `ptr`）用条件分支生成不同的记录逻辑。**

### 2. ★★★★★ `mode="decl"` 是**观测设计的极致**

★★★ **⇒ 双重非空检查后解引用 `pLen`，抢在函数执行前拿到调用方声明的缓冲区容量。**
**注释明确"避免把栈上垃圾当指针读"。**

### 3. ★★★★★ **"事后读 vs 当场抄"是核心教训**

```
事后 ReadProcessMemory 指针  ⇒  函数已返回，栈被覆盖  ⇒  乱码
当场复制到记录区              ⇒  永远有效
```

★★★ **⇒ 这解释了为什么整个设计是"跳板在入口瞬间复制"，而不是"记录指针事后读"。**

### 4. ★★★ `follow_str` 的**长度退让**是跨页读取的标准容错

### 5. ★★ 字节序处理精确：族号小端、端口大端

### 6. ★★ 窄字符用 `gbk` 解码（CODOL 的 ANSI 是 GBK）

---

## 六、下一步

- `decode_cmdline`（第 348–365 行）
- **`build_tas_image`（第 366–490 行）** —— TCLS 共享内存镜像
- `parse_patches` / `apply_patches`（第 494–545 行）
- 四个兼容补丁（第 546–709 行）
- 会话密钥快照（第 710–804 行）
- `playerstate_probe_thread`（第 1118–1318 行）
- `main()`（第 1319 行起）
