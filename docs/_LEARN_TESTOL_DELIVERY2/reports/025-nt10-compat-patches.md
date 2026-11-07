# 学习报告 025（重开）— `nt10.py` 四个兼容补丁（完整逐字节）

**学习范围**：第 546–680 行（4 个补丁的定义 + `compat_patch_once` + `compat_patch_thread` 开头）
**性质**：全实测（**全包最关键的内存补丁**）
**★★★ 本报告逐条收录**四个补丁的精确字节模式**与**latch 机制的由来**

---

## 一、★★★★★ 补丁来源与四个补丁的定义（第 546–558 行）

```python
# ==================== 三方验证过的 4 个兼容补丁 ====================
# 来源: E:\codol\dist\launcher_src\CodolStateReader.cs + Run-Session.ps1
#   补丁1 PatchUnsignedAuthGate   0x00B9A78C 前 16B 起: 84 C0 74 B2 B0 01 -> 74(JE) 改 75(JNE)
#   补丁2 PatchUnsignedClientTicket 0x00B9A7B0 起:     84 C0 75 2A E8    -> 75(JNE) 改 EB(JMP)
#   补丁3 PatchAuthParseFallback  0x00B9A7B0 起: 某 call 改成 E9 跳 0x00B9A7F1
#   补丁4 PatchLocalLsgNonceCheck 0x00BA3C1A: 85 C0 75 44 -> 在 0x00BA3C1C 写 90 90(NOP)
#         (十进制 12205082 = 0xBA3C1A, 12205084 = 0xBA3C1C —— 上次我误算成 0xBA41DA;
#          用运行时转储 n10ao_exe_lobby.bin 核对: 85 C0 75 44 确实在 0xBA3C1A)
# 效果: 客户端走"未签名"离线路径 —— 实测请求里的 auth_task 会从 32 变成 10(三方同款),
#       且不再校验本地 LSG 的 8 字节 challenge。
# ★ 这些字节在磁盘上是加密的(.tp3 段), 必须【运行时解壳后】才匹配得到,
#   所以照 Run-Session.ps1 的做法: 循环重试直到模式出现。
COMPAT_DEADLINE = 90.0
```

### ★★★ 来源（第 547 行）

```
E:\codol\dist\launcher_src\CodolStateReader.cs + Run-Session.ps1
```

★★ **⇒ **两个来源文件**：一个 C# 读取器 + 一个 PowerShell 会话脚本。**
★ **⇒ 路径 `E:\codol\dist\launcher_src\` —— 又一处作者机器路径泄漏。**

### ★★★★ 四个补丁的完整定义

| # | 名称 | 地址 | 原字节 | 改后 | 偏移 |
|---|---|---|---|---|---|
| **1** | `PatchUnsignedAuthGate` | `0x00B9A78C` **前 16B 起** | `84 C0 74 B2 B0 01` | `74` → `75` | `+2` |
| **2** | `PatchUnsignedClientTicket` | `0x00B9A7B0` 起 | `84 C0 75 2A E8` | `75` → `EB` | `+2` |
| **3** | `PatchAuthParseFallback` | `0x00B9A7B0` 起 | 某 `call` | `E8` → `E9` 跳 `0x00B9A7F1` | — |
| **4** | `PatchLocalLsgNonceCheck` | `0x00BA3C1A` | `85 C0 75 44` | `0x00BA3C1C` 写 `90 90` | `+2` |

### ★★★★★ 效果（第 554–555 行，逐字）

```python
# 效果: 客户端走"未签名"离线路径 —— 实测请求里的 auth_task 会从 32 变成 10(三方同款),
#       且不再校验本地 LSG 的 8 字节 challenge。
```

★★★★★ **⇒ 两个可观测的效果指标：**
```
① auth_task: 32 → 10     ★★★ 精确的协议字段变化
② 不再校验本地 LSG 的 8 字节 challenge
```

★ **⇒ "三方同款" —— 说明这个效果在三个独立实现里都一致。**

★★★ **⇒ 而 `auth_task = 32` 正是 `TASK_MAP` 里的 `32→57` 那一项（上一轮报告 011 记录）。**
**⇒ 补丁后变成 `10`（对应 `TASK_MAP` 的 `10→11`）。**

### ★★★★★ `.tp3` 的关键确认（第 556–557 行，逐字）

```python
# ★ 这些字节在磁盘上是加密的(.tp3 段), 必须【运行时解壳后】才匹配得到,
#   所以照 Run-Session.ps1 的做法: 循环重试直到模式出现。
```

★★★★★ **⇒ 这是**第三次独立确认** `.tp3` 加密（上一轮报告 040 已用 5 份转储铁证）：**
```
磁盘上的字节是**加密**的
        ↓
必须**运行时解壳后**才匹配得到
        ↓
所以**循环重试**直到模式出现
```

★ **⇒ `COMPAT_DEADLINE = 90.0` —— 最多重试 **90 秒**。**

---

## 二、★★★ 三个底层工具（第 561–605 行）

### 2.1 `_vm_protect`（第 561–571 行）

```python
def _vm_protect(h, addr, size, prot=0x40):
    try:
        k32.VirtualProtectEx.argtypes = [wintypes.HANDLE, ctypes.c_void_p,
                                         ctypes.c_size_t, wintypes.DWORD,
                                         ctypes.POINTER(wintypes.DWORD)]
        old = wintypes.DWORD(0)
        ok = bool(k32.VirtualProtectEx(h, ctypes.c_void_p(addr), size, prot,
                                       ctypes.byref(old)))
        return ok, old
    except Exception:
        return False, wintypes.DWORD(0)
```

★★ **⇒ `prot=0x40` = `PAGE_EXECUTE_READWRITE`（默认）。**
★ **⇒ 返回 `(ok, old_protect)`。**

### 2.2 ★★★ `_wpm_code`（第 574–591 行）—— **写代码段的标准流程**

```python
def _wpm_code(h, addr, data):
    """写代码段: 先 VirtualProtectEx 开写权限(失败也照样试一次), 写完还原 + 刷 icache。"""
    ok, old = _vm_protect(h, addr, len(data))       # ① 改保护
    wrote = wpm(h, addr, data)                      # ② 写
    if ok:
        try:
            k32.VirtualProtectEx(h, ctypes.c_void_p(addr), len(data), old.value,
                                 ctypes.byref(wintypes.DWORD(0)))    # ③ 还原
        except Exception:
            pass
    if wrote:
        try:
            k32.FlushInstructionCache.argtypes = [wintypes.HANDLE, ctypes.c_void_p,
                                                  ctypes.c_size_t]
            k32.FlushInstructionCache(h, ctypes.c_void_p(addr), len(data))   # ④ 刷 icache
        except Exception:
            pass
    return wrote
```

★★★★★ **⇒ 四步流程（**完整且正确**）：**
```
① VirtualProtectEx → PAGE_EXECUTE_READWRITE
② WriteProcessMemory
③ VirtualProtectEx → 还原原保护
④ ★★★ FlushInstructionCache    ← 关键！否则 CPU 可能执行旧指令
```

★★★ **⇒ 第 ④ 步 `FlushInstructionCache` 是**最容易遗漏的**：**
**x86 上写代码后如果不刷指令缓存，CPU 可能继续执行**旧的已解码指令**。**

★ **⇒ 注释说"失败也照样试一次"（`ok` 为 False 也写）—— 因为有时保护已经是可写的。**

### 2.3 ★★★ `_match_at`（第 594–605 行）—— **支持等价集合的模式匹配**

```python
def _match_at(buf, off, pat):
    """pat 里元素是 int 或 (等价集合)。"""
    for j, p in enumerate(pat):
        if off + j >= len(buf):
            return False
        b = buf[off + j]
        if isinstance(p, (tuple, list, set)):
            if b not in p:
                return False
        elif b != p:
            return False
    return True
```

★★★ **⇒ `pat` 的元素可以是**单个 int** 或**等价集合**（如 `(0x74, 0x75)`）。**

★ **⇒ 这支持"**已经打过补丁**"的检测：**
```python
_match_at(buf, i, (0x84, 0xC0, (0x74, 0x75), 0xB2, 0xB0, 0x01))
#                                  ↑ 0x74=原值, 0x75=补丁后
```

★★★ **⇒ 这样同一段代码**既能匹配原值也能匹配补丁后**，实现幂等。**

---

## 三、★★★★★ `compat_patch_once`（第 608–669 行）—— 四个补丁的逐条实现

### 3.1 ★★★ 补丁 1：AuthGate（第 612–625 行）

```python
# --- 1) AuthGate: 0x00B9A78C-16 起 40 字节内找 84 C0 (74|75) B2 B0 01
base = 0x00B9A78C - 16                  # = 0x00B9A77C
buf = rpm(h, base, 40)
if len(buf) == 40:
    for i in range(0, 40 - 6 + 1):      # 0..34
        if _match_at(buf, i, (0x84, 0xC0, (0x74, 0x75), 0xB2, 0xB0, 0x01)):
            a = base + i + 2            # ★ 跳转指令的位置
            cur = rpm(h, a, 1)
            if cur == b"\x75":
                done.add(1)             # ★ 已是 75 ⇒ 幂等
            elif cur == b"\x74" and _wpm_code(h, a, b"\x75"):
                done.add(1)
                notes.append("补丁1 AuthGate 74->75 @0x%08X" % a)
            break                       # ★ 找到就停
```

★★★ **⇒ 三个要点：**
```
① 搜索窗口：0x00B9A78C - 16 起 40 字节（★ 因为补丁 3 会改变附近的字节）
② 6 字节模式：84 C0 (74|75) B2 B0 01
③ 幂等：若已是 75 ⇒ 直接计入 done
```

★ **⇒ `84 C0` = `test al, al`，`74/75` = `je/jne`，`B2` = `mov dl, imm8`。**

### 3.2 ★★★ 补丁 2：ClientTicket（第 627–640 行）

```python
# --- 2) ClientTicket: 0x00B9A7B0 起 64 字节内找 84 C0 (75|EB) 2A E8
base2 = 0x00B9A7B0
buf2 = rpm(h, base2, 64)
if len(buf2) == 64:
    for i in range(0, 64 - 5 + 1):      # 0..59
        if _match_at(buf2, i, (0x84, 0xC0, (0x75, 0xEB), 0x2A, 0xE8)):
            a = base2 + i + 2
            cur = rpm(h, a, 1)
            if cur == b"\xEB":
                done.add(2)
            elif cur == b"\x75" and _wpm_code(h, a, b"\xEB"):
                done.add(2)
                notes.append("补丁2 ClientTicket 75->EB @0x%08X" % a)
            break
```

★ **⇒ 5 字节模式：`84 C0 (75|EB) 2A E8`。**

★★ **⇒ `75` = `jne rel8`，`EB` = `jmp rel8` —— 从条件跳转改成**无条件跳转**。**

★★★ **⇒ 注意 `2A E8` 是**后续字节**（`sub ch, al` + `call` 的开头），用于定位。**

### 3.3 ★★★★★ 补丁 3：ParseFallback（第 642–658 行）

```python
# --- 3) ParseFallback: 某 call(E8/E9) + 12 字节模式 -> 改成 E9 跳 0x00B9A7F1
pat3 = (0x8D, 0x8D, 0x38, 0xFD, 0xFF, 0xFF, 0xC7, 0x85, 0x68, 0xFD, 0xFF, 0xFF)
if len(buf2) == 64:
    for i in range(0, 64 - 5 - len(pat3) + 1):   # 0..47
        if buf2[i] not in (0xE8, 0xE9):
            continue
        if not _match_at(buf2, i + 5, pat3):
            continue
        a = base2 + i
        if buf2[i] == 0xE9:
            done.add(3)                          # ★ 幂等
        else:
            rel = (0x00B9A7F1 - a - 5) & 0xFFFFFFFF
            if _wpm_code(h, a, b"\xE9" + struct.pack("<I", rel)):
                done.add(3)
                notes.append("补丁3 ParseFallback E8->E9 @0x%08X -> 0x00B9A7F1" % a)
        break
```

★★★ **⇒ 12 字节模式（`pat3`）定位 call 的**后续指令**：**
```
8D 8D 38 FD FF FF     lea ecx, [ebp-0x2C8]
C7 85 68 FD FF FF     mov [ebp-0x298], ...
```

★★ **⇒ 即：`call` 之后紧跟 `lea ecx, [ebp-0x2C8]` + `mov [ebp-0x298], imm32`。**

★★★ **⇒ 相对偏移计算：**
```python
rel = (0x00B9A7F1 - a - 5) & 0xFFFFFFFF
```
**`a` = call 的地址，`+5` = 下一条指令，目标 = `0x00B9A7F1`。**

★ **⇒ 与上一轮 capstone 实测的 `0xB9A7C7` 处 `E8 04 8E CA FF` 完全对应。**

### 3.4 ★★★ 补丁 4：LsgNonceCheck（第 660–667 行）

```python
# --- 4) LsgNonceCheck: 0x00BA3C1A 处 85 C0 75 44 -> 0x00BA3C1C 写 90 90
b4 = rpm(h, 0x00BA3C1A, 4)
if len(b4) == 4:
    if b4 == b"\x85\xC0\x90\x90":
        done.add(4)                          # ★ 幂等
    elif b4 == b"\x85\xC0\x75\x44" and _wpm_code(h, 0x00BA3C1C, b"\x90\x90"):
        done.add(4)
        notes.append("补丁4 LsgNonceCheck NOP @0x00BA3C1C (85 C0 75 44 -> 85 C0 90 90)")
```

★★★ **⇒ 唯一一个**地址固定、不需搜索**的补丁（`0x00BA3C1A`）。**

★ **⇒ 4 字节：`85 C0 75 44` → `85 C0 90 90`（`jne` 变成两个 `nop`）。**

★★★ **⇒ 与上一轮 capstone 实测**完全吻合**（报告 044）。**

---

## 四、★★★★★ `compat_patch_thread` 的 **latch 机制**（第 672–680 行）

```python
def compat_patch_thread(h, log, deadline=COMPAT_DEADLINE):
    """后台线程: 反复尝试 4 个补丁, 直到全部成功或超时。
    ★ 一旦某个补丁成功就【latch】住不再复查 —— 照抄 Run-Session.ps1 的 patched[$i]。
      原因: 补丁3 会把 0xB9A7C7 的 E8 改成 E9, 于是补丁2 的模式(84 C0 .. 2A E8)
      再也匹配不到; 若每轮重新判定, 补丁2 就会"掉出计数"(上一轮日志里 3/4 变 2/4 就是这个)。"""
    done = set()
    t0 = time.time()
    while time.time() - t0 < deadline and len(done) < 4:
```

### ★★★★★ latch 的**完整因果**（逐字）

```
补丁 3 把 0xB9A7C7 的 E8 改成 E9
        ↓
补丁 2 的模式是 (84 C0 .. 2A E8)
        ↓
★★★ E8 变成 E9 ⇒ 补丁 2 的模式**再也匹配不到**
        ↓
若每轮重新判定 ⇒ 补丁 2 会"掉出计数"
        ↓
★ 实测现象：日志里 **3/4 变 2/4**
```

★★★ **⇒ 这是一个**极其精确的观察**：**
**两个补丁的模式**互相干扰**（补丁 3 改了补丁 2 依赖的字节）。**

★ **⇒ 解法：**latch（一旦成功就记住，不再复查）**。**

★★ **⇒ "照抄 `Run-Session.ps1` 的 `patched[$i]`" —— 三方实现都用了这个机制。**

---

## 五、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | 补丁来源 | `E:\codol\dist\launcher_src\CodolStateReader.cs` + `Run-Session.ps1` |
| 2 | ★★★ 补丁 1 | `0xB9A78C-16` 起 40B 内 `84 C0 (74\|75) B2 B0 01` |
| 3 | ★★★ 补丁 2 | `0xB9A7B0` 起 64B 内 `84 C0 (75\|EB) 2A E8` |
| 4 | ★★★★★ 补丁 3 | `E8/E9` + 12B 模式 `8D 8D 38 FD FF FF C7 85 68 FD FF FF` |
| 5 | ★★★ 补丁 4 | **`0xBA3C1A`**：`85 C0 75 44` → `85 C0 90 90` |
| 6 | ★★★ 效果 ① | **`auth_task` 32 → 10** |
| 7 | ★★★ 效果 ② | **不再校验本地 LSG 的 8 字节 challenge** |
| 8 | ★★★★★ `.tp3` 确认 | **磁盘加密，必须运行时解壳后才匹配** |
| 9 | 重试超时 | **`COMPAT_DEADLINE = 90.0`** 秒 |
| 10 | ★★★★ 写代码段四步 | **改保护 → 写 → 还原 → `FlushInstructionCache`** |
| 11 | ★★★ `_match_at` | 支持**等价集合**（`(0x74,0x75)`）⇒ 幂等 |
| 12 | ★★ 补丁 1 窗口 | **前 16 字节起 40 字节**（因补丁 3 会改附近） |
| 13 | ★ 补丁 3 相对偏移 | `(0x00B9A7F1 - a - 5)` |
| 14 | ★★★★★ **latch 原因** | **补丁 3 改 `E8`→`E9` ⇒ 补丁 2 模式失效 ⇒ 3/4 变 2/4** |
| 15 | ★ 地址换算教训 | **十进制 12205082 = `0xBA3C1A`**（上次误算 `0xBA41DA`） |

---

## 六、结论

### 1. ★★★★★ 四个补丁构成**完整的认证绕过链**

```
补丁 1  AuthGate       74→75    反转"签名无效"判定
补丁 2  ClientTicket   75→EB    无条件跳成功
补丁 3  ParseFallback  E8→E9    跳过解析失败处理
补丁 4  LsgNonceCheck  NOP      跳过 LSG challenge 校验
```

★★★ **⇒ 四个缺一不可。**

### 2. ★★★★★ **latch 机制**是补丁**互相干扰**的解决方案

★★★ **⇒ 补丁 3 改 `E8`→`E9` 会破坏补丁 2 的模式（`.. 2A E8`）。**
**⇒ 实测现象："3/4 变 2/4"。**

### 3. ★★★★ 写代码段必须 `FlushInstructionCache`

### 4. ★★★ `.tp3` 加密是**第三次独立确认**（本报告 + 上一轮 5 份转储 + 记忆）

### 5. ★★ 补丁效果有**两个精确指标**（`auth_task` 32→10、不校验 8 字节 challenge）

### 6. ★ 又一次地址手算错误被记录在案（`0xBA41DA` → `0xBA3C1A`）

---

## 七、下一步

- `compat_patch_thread` 剩余（第 680–709 行）
- 会话密钥快照（第 710–804 行）—— **地址链与 XOR 还原**
- `scan_dword` / `probe_auth_object` / `watch_dialogs`（第 815–949 行）
- `playerstate_probe_thread`（第 1118–1318 行）
- `main()`（第 1319 行起）
