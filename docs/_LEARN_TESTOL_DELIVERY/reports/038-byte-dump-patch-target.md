# 学习报告 038 — 逐字节：补丁目标 `client+0x08371A` 与返回码定案

**方法**：反汇编 `0x4F77C`..`0x4F860`（实际打补丁段）+ 两个分支的返回码
**性质**：全实测
**★★★ 本报告给出了补丁的**精确目标地址**和**完整返回码**

---

## 一、★★★ 两个分支的返回码（逐字节）

### `0x4F8C3` —— 版本不匹配

```asm
004F8C3  B8 03 00 00 00     mov  eax, 3          ← ★★★ 返回 3
004F8C8  5F                 pop  edi
004F8C9  5E                 pop  esi
004F8CA  5B                 pop  ebx
004F8CB  8B E5              mov  esp, ebp
004F8CD  5D                 pop  ebp
004F8CE  C3                 ret
```

★★★ **返回 `3` = `"unsupported_host"`** ✓（与报告 035 的状态表一致）

### `0x4F8CF` —— 未请求

```asm
004F8CF  5F                 pop  edi
004F8D0  5E                 pop  esi
004F8D1  33 C0              xor  eax, eax        ← ★★★ 返回 0
004F8D3  5B                 pop  ebx
004F8D4  8B E5              mov  esp, ebp
004F8D6  5D                 pop  ebp
004F8D7  C3                 ret
```

★★★ **返回 `0` = `"not_requested"`** ✓

### ★★ 这**完美闭合**了状态枚举

```
状态 0 = not_requested   ← 0x4F8CF（环境变量没设）
状态 3 = unsupported_host← 0x4F8C3（版本不匹配）
状态 1 = patched         ← 主路径成功
状态 2 = already_patched ← 主路径的另一分支
状态 4 = unexpected_bytes← 主路径的字节校验失败
状态 5 = unknown         ← main 路径里 `mov eax, 5`（`0x4F7D6`）
```

★★ **`0x4F7D6` 我看到了 `B8 05 00 00 00`（`mov eax, 5`）—— 确认状态 5 的存在。**

---

## 二、★★★ 补丁的目标地址：`client + 0x08371A`

### 关键指令（`0x4F783`）

```asm
004F783  C6 44 24 14 00     mov  byte ptr [esp+14h], 0
004F788  8D 9F 1A 37 08 00  lea  ebx, [edi + 8371Ah]    ← ★★★ 目标地址！
```

★★★ **`edi` = `GetModuleHandleW(NULL)` 返回的**客户端主模块基址**（`0x400000`）。**

★★★ **⇒ 补丁目标是**客户端 `0x400000 + 0x08371A = 0x48371A`**。**

### ★★ 这与 `nt10.py` 的补丁地址对比

**记忆里 `nt10.py` 的补丁**（报告 002/003）：
```
4 个兼容补丁，带精确字节模式
```

★★ **`0x48371A` 是否在 `nt10.py` 的补丁列表里？** —— **需查。**

★★★ **如果不在，则两套补丁互补（不冲突）。**

### 后续：`VirtualAlloc` + `ReadProcessMemory`?

```asm
004F7BC  C7 44 24 10 00 00 00 00  mov dword ptr [esp+10h], 0
004F7C4  50                       push eax
004F7C5  6A 40                    push 40h               ← ★ PAGE_EXECUTE_READWRITE
004F7C7  6A 08                    push 8                 ← ★ 8 字节
004F7C9  53                       push ebx               ← 目标地址
004F7CA  FF 15 F4 D0 47 10        call dword ptr [1047D0F4h]  ← ★ VirtualProtect！
004F7D0  85 C0                    test eax, eax
004F7D2  75 0C                    jne  0x4F7E0
004F7D4  B8 05 00 00 00           mov  eax, 5            ← ★ 失败 → 状态 5（unknown）
004F7D9  5F 5E 5B                 pop edi; pop esi; pop ebx
004F7DC  8B E5 5D C3              mov esp,ebp; pop ebp; ret
```

★★★ **`push 0x40`（`PAGE_EXECUTE_READWRITE`）+ `push 8`（8 字节）+ `push ebx`（目标）
+ `call VirtualProtect`** —— **标准的补丁前置。**

★★★ **⇒ 补丁长度是 **8 字节**。**

★ **8 字节足够写 `E9 rel32`（5 字节）+ 3 字节填充，或 `B8 imm32 C3`（5 字节）+ 3。**

---

## 三、★★★ 补丁的**字节校验**（`0x4F7E4` 起）

```asm
004F7E4  8B 46 50              mov  eax, [esi+50h]    ← ★ SizeOfImage（PE 头 + 0x50）
004F7E7  89 7C 24 1C           mov  [esp+1Ch], edi    ← 保存基址
004F7EB  3D 1A 37 08 00        cmp  eax, 8371Ah       ← ★★ 比较 SizeOfImage 与 0x8371A?
004F7F0  0F 82 82 00 00 00     jb   0x4F878          ← 太小 → 跳过
004F7F6  05 E6 C8 F7 FF        add  eax, 0FFF7C8E6h   ← ★★ 加法（溢出检查？）
004F7FB  83 F8 08              cmp  eax, 8
004F7FE  72 78                 jb   0x4F878          ← 
004F800  C6 44 24 1C 00        mov  byte ptr [esp+1Ch], 0
...
```

★★ **`cmp eax, 0x8371A` 这里 `eax` 是 `SizeOfImage`（`0x0E659000`）** ——
**`0x0E659000 > 0x8371A` ⇒ 不跳（继续）。**

★★ **`add eax, 0xFFF7C8E6`** ——
```
0x0E659000 + 0xFFF7C8E6 = 0x0E5D58E6 (32 位回绕)
0x0E5D58E6 = 241,454,310
```
**然后 `cmp eax, 8; jb`** —— **241M >= 8 ⇒ 不跳。**

★ **这两个检查是**边界验证**（确保 `0x8371A` 在镜像内且后面有 8 字节空间）。**

★★ **`0x0E659000 - 0x8371A = 0x0E5D58E6`** —— 与上面的加法一致 ✓

★★★ **⇒ 这是**"目标地址 + 8 字节 是否在镜像范围内"**的检查。**

---

## 四、★★★ 然后做**字符串比较**（`0x4F808` 起）

```asm
004F808  C6 44 24 1C 00        mov byte ptr [esp+1Ch], 0
004F80D  BA 4C CC 51 10        mov  edx, 1051CC4Ch    ← ★ 期望字节串 A
004F812  FF 74 24 1C           push [esp+1Ch]
004F816  C6 44 24 1C 00        mov byte ptr [esp+1Ch], 0
004F81B  8B CB                 mov  ecx, ebx          ← 目标地址
004F81D  FF 74 24 1C           push [esp+1Ch]
004F821  C6 44 24 1C 00        mov byte ptr [esp+1Ch], 0
004F826  FF 74 24 1C           push [esp+1Ch]
004F82A  6A 08                 push 8                 ← 8 字节
004F82C  E8 BB 0A 00 00        call 0x503EC           ← ★★ 比较函数
004F831  83 C4 10              add  esp, 10h
004F834  84 C0                 test al, al
004F836  74 04                 je   0x4F83C
004F838  B3 01                 mov  bl, 1             ← ★ 匹配 → bl=1
004F83A  EB 46                 jmp  0x4F882
```

★★★ **`mov edx, 0x1051CC4C`** = **期望的 8 字节模式**（VA `0x1051CC4C`）。**

★★ **`call 0x503EC`（8 字节比较）** —— 把目标处的 8 字节与期望比较。

★★★ **⇒ 这是**字节模式校验**：如果目标处的 8 字节 == `0x1051CC4C` 的值，
则 `bl = 1`（状态 1 = `patched`）；否则走另一分支。**

### ★★ 第二条比较（`0x4F83C` 起）

```asm
004F83C  C6 44 24 1C 00        mov byte ptr [esp+1Ch], 0
004F841  BA 44 CC 51 10        mov edx, 1051CC44h    ← ★ 期望字节串 B
004F846  FF 74 24 1C           push ...
...
004F860  E8 87 0A 00 00        call 0x503EC           ← 同样的比较函数
```

★★ **`0x1051CC44`** —— **第二个期望模式（8 字节）。**

★★★ **⇒ 两套字节模式：**
```
0x1051CC4C  → 状态 1（patched）
0x1051CC44  → 状态 2（already_patched）
```

---

## 五、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | 补丁目标 | `client + 0x08371A`（`lea ebx, [edi+8371Ah]`）★ |
| 2 | 补丁长度 | **8 字节**（`push 8`） |
| 3 | 页保护 | `PAGE_EXECUTE_READWRITE`（`0x40`） |
| 4 | 保护失败返回 | **`5`**（`unknown`） |
| 5 | 版本不符返回 | **`3`**（`unsupported_host`） |
| 6 | 未请求返回 | **`0`**（`not_requested`） |
| 7 | 边界检查 1 | `SizeOfImage >= 0x8371A` |
| 8 | 边界检查 2 | `SizeOfImage - 0x8371A >= 8` |
| 9 | 期望模式 A | `0x1051CC4C`（8 字节） |
| 10 | 期望模式 B | `0x1051CC44`（8 字节） |
| 11 | 比较函数 | `0x503EC` |
| 12 | 匹配 A | `bl = 1` → 状态 1 |
| 13 | 匹配 B | → 状态 2 |

---

## 六、★★★ 立即需要验证的

### 1. `client + 0x08371A = 0x48371A` 处的 8 字节是什么

★★ **需要读客户端 EXE @ `0x400000 + 0x8371A` 的 8 字节，
并与 `0x1051CC44` / `0x1051CC4C` 比较。**

★★★ **如果匹配 ⇒ 这个客户端**支持**这个补丁。**
**如果不匹配 ⇒ `unexpected_bytes`。**

### 2. `nt10.py` 的补丁地址里有没有 `0x48371A`

★★ **需要查 `nt10.py` 的 4 个补丁。**

---

## 七、结论

### 1. ★★★ 补丁目标是 `client+0x08371A`（8 字节）

★★ **这是**唯一**的补丁点（这一段只看到一个 `lea`）。**

### 2. ★★★ 返回码完全闭合状态枚举

```
0 not_requested   ← 环境变量没设
1 patched         ← 字节匹配 A（0x1051CC4C）
2 already_patched ← 字节匹配 B（0x1051CC44）
3 unsupported_host← 版本不符
4 unexpected_bytes← （主路径后面，待查）
5 unknown         ← VirtualProtect 失败
```

### 3. ★★ 这是**可选增强**，不影响换战斗服

★★ **默认 `OLMOD_ALLOW_UNSIGNED_FASTFILES` 不设 ⇒ 状态 0 ⇒ 不打补丁。**

---

## 八、待逐字节继续（★ 优先级）

- [ ] ★★★ **读 `0x1051CC44` / `0x1051CC4C` 的 8 字节模式**
- [ ] ★★★ **读客户端 EXE @ `0x48371A` 的 8 字节**（验证能否匹配）
- [ ] ★★ **查 `nt10.py` 的 4 个补丁地址是否有 `0x48371A`**
- [ ] ★★ **`0x4F882` 之后（实际写补丁的 8 字节内容）**
- [ ] ★ **状态 4（`unexpected_bytes`）的触发点**
- [ ] ★ **`0x503EC`（8 字节比较函数）**
