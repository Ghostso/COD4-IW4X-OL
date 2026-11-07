# 学习报告 021（重开）— `nt10.py` 模块枚举与 trampoline（第 135–249 行）

**学习范围**：`rpm` / `wpm` / `mods_toolhelp` / `mods_peb` / `mods_any` / `export_rva` / `pick_stolen` / `build_tramp` 开头
**性质**：全实测
**★★★ 本报告揭示**PEB 模块链的完整实现**与**trampoline 的三种捕获模式**

---

## 一、★★ 基础读写封装（第 135–146 行）

```python
def rpm(h, addr, size):
    b = ctypes.create_string_buffer(size)
    got = ctypes.c_size_t(0)
    if k32.ReadProcessMemory(h, ctypes.c_void_p(addr), b, size, ctypes.byref(got)):
        return b.raw[:got.value]
    return b""


def wpm(h, addr, data):
    n = ctypes.c_size_t(0)
    return (bool(k32.WriteProcessMemory(h, ctypes.c_void_p(addr), data, len(data),
                                        ctypes.byref(n))) and n.value == len(data))
```

★★★ **⇒ 两个要点：**
```
① rpm 失败返回 b""（空字节串），不抛异常 —— ★ 调用方用 len() 判断
② wpm 双重校验：API 返回 True **且** n.value == len(data)
```

★ **⇒ `wpm` 的双重校验很重要** —— `WriteProcessMemory` 可能部分成功。**

---

## 二、★★★ `mods_toolhelp`（第 149–163 行）

```python
def mods_toolhelp(pid):
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid)
    out = []
    if not snap or snap == -1:
        return out
    me = MODULEENTRY32()
    me.dwSize = ctypes.sizeof(MODULEENTRY32)
    if k32.Module32First(snap, ctypes.byref(me)):
        while True:
            out.append((me.szModule.decode(errors="replace"), me.modBaseAddr or 0,
                        me.modBaseSize))
            if not k32.Module32Next(snap, ctypes.byref(me)):
                break
    k32.CloseHandle(snap)
    return out
```

★★★ **⇒ 三个健壮性措施：**
```
① if not snap or snap == -1   ← 句柄无效（ACE 封掉时的表现）
② errors="replace"            ← 模块名解码不抛异常
③ me.modBaseAddr or 0         ← NULL 转 0
```

★ **⇒ 与 docstring 呼应："晚了会被 ACE 封掉（toolhelp 返回空）"。**

---

## 三、★★★★★ `mods_peb`（第 166–201 行）—— **绕开 ACE 的 PEB 模块链**

```python
def mods_peb(h):
    """直接走 PEB 的模块链(绕开被 ACE 封掉的 toolhelp 枚举)"""
    try:
        ntdll = ctypes.WinDLL("ntdll")
        # 我们是 64 位 Python: 该 API 按【调用方】位宽返回结构, PebBaseAddress 在 +8
        # (目标进程里再去用 32 位的 PEB/链表偏移)
        pbi = (ctypes.c_uint64 * 6)()
        ret = ctypes.c_uint32(0)
        if ntdll.NtQueryInformationProcess(h, 0, ctypes.byref(pbi),
                                           ctypes.sizeof(pbi), ctypes.byref(ret)) != 0:
            return []
        peb = pbi[1]
        if not peb:
            return []
        ldr = struct.unpack("<I", rpm(h, peb + 0x0C, 4))[0]
        if not ldr:
            return []
        head = ldr + 0x0C
        cur = struct.unpack("<I", rpm(h, head, 4))[0]
        out = []
        while cur and cur != head and len(out) < 400:
            b = rpm(h, cur + 0x18, 8)
            if len(b) < 8:
                break
            base, size = struct.unpack("<II", b)
            nm = ""
            nb = rpm(h, cur + 0x2C, 8)
            if len(nb) == 8:
                blen, _mx, bbuf = struct.unpack("<HHI", nb)
                if bbuf and 0 < blen < 520:
                    nm = rpm(h, bbuf, blen).decode("utf-16le", "replace")
            out.append((nm, base, size))
            cur = struct.unpack("<I", rpm(h, cur, 4))[0]
        return out
    except Exception:
        return []
```

### ★★★★★ 完整的 PEB 遍历链（逐偏移）

```
① NtQueryInformationProcess(h, 0, &pbi, sizeof, &ret)
        ↓ ProcessBasicInformation (class 0)
   pbi[1] = PebBaseAddress        ← ★★★ 64 位调用方，结构按 64 位返回
        ↓
② rpm(h, peb + 0x0C, 4)  →  Ldr            ★ PEB->Ldr
        ↓
③ head = ldr + 0x0C                        ★ &Ldr->InLoadOrderModuleList
④ cur = *(head)                            ★ Flink（第一个模块）
        ↓
⑤ 循环（cur != head，最多 400 个）：
     b = rpm(h, cur + 0x18, 8)             ★ LDR_DATA_TABLE_ENTRY
       base = *(cur+0x18)                  ★ DllBase
       size = *(cur+0x1C)                  ★ SizeOfImage
     nb = rpm(h, cur + 0x2C, 8)            ★ BaseDllName (UNICODE_STRING)
       blen = *(cur+0x2C)                  ★ Length (2 字节)
       bbuf = *(cur+0x30)                  ★ Buffer (4 字节)
       nm = rpm(h, bbuf, blen).decode("utf-16le")
     cur = *(cur)                          ★ Flink（下一个）
```

### ★★★ 关键偏移汇总（32 位 LDR_DATA_TABLE_ENTRY）

| 偏移 | 字段 | 值 |
|---|---|---|
| `+0x00` | `InLoadOrderLinks.Flink` | 下一个节点 |
| `+0x0C` | `InLoadOrderLinks` 头（在 `PEB_LDR_DATA` 里） | — |
| **`+0x18`** | **`DllBase`** | 模块基址 |
| **`+0x1C`** | **`SizeOfImage`** | 大小 |
| **`+0x2C`** | **`BaseDllName.Length`** | 名称长度（UTF-16 字节数） |
| **`+0x30`** | **`BaseDllName.Buffer`** | 名称指针 |

★★★ **⇒ 这是**标准的 32 位 PEB 遍历**，偏移全部正确。**

### ★★★★ 一处极重要的注释（第 170–171 行）

```python
# 我们是 64 位 Python: 该 API 按【调用方】位宽返回结构, PebBaseAddress 在 +8
# (目标进程里再去用 32 位的 PEB/链表偏移)
```

★★★★★ **⇒ 这是**64 位 Python 操作 32 位进程的关键陷阱**：**

```
Python 是 64 位（本机）
        ↓
NtQueryInformationProcess 按【调用方】位宽返回 PROCESS_BASIC_INFORMATION
        ↓
64 位布局：ExitStatus(8) + PebBaseAddress(8) + ...
        ↓
★ PebBaseAddress 在 +8（即 pbi[1]，因为 pbi 是 c_uint64 数组）
        ↓
但**目标进程**里的 PEB 是 32 位的
        ↓
★ 所以拿到 peb 之后，必须用**32 位偏移**（0x0C / 0x18 / 0x2C ...）
```

★★★ **⇒ 这个"混合位宽"的处理是**全文件最容易出错的地方**，注释写得非常清楚。**

★ **⇒ `pbi = (ctypes.c_uint64 * 6)()` —— 6 个 uint64 = 48 字节（足够 64 位结构）。**

★ **⇒ `peb = pbi[1]` —— 索引 1 = 偏移 8。**

### ★★ 三个安全措施

```python
except Exception:
    return []
```
★ **任何异常都返回空列表（fail-soft）。**

```python
while cur and cur != head and len(out) < 400:
```
★★ **三重终止条件：**
```
① cur == 0（NULL）
② cur == head（回到链表头）
③ len(out) >= 400（★ 上限保护，防死循环）
```

```python
if bbuf and 0 < blen < 520:
```
★★ **名称长度上限 520 字节（= 260 个 UTF-16 字符 = MAX_PATH）。**

---

## 四、★★★ `mods_any`（第 204–211 行）—— **两条路径的择优**

```python
def mods_any(pid, h):
    ml = mods_toolhelp(pid)
    if any(n.lower().startswith("ws2_32") for n, b, s in ml):
        return ml, "toolhelp"
    ml2 = mods_peb(h)
    if ml2:
        return ml2, "peb"
    return ml, "toolhelp"
```

★★★ **⇒ 判定逻辑：**
```
先试 toolhelp
        ↓
★ 若结果里**有 ws2_32** ⇒ 枚举成功 ⇒ 返回 toolhelp
        ↓
否则试 PEB
        ↓
若 PEB 有结果 ⇒ 返回 peb
        ↓
★ 否则返回空 toolhelp 结果
```

★★★ **⇒ 用 `ws2_32` 是否存在作为"枚举成功"的判据** ——
**因为 `ws2_32` 必定被加载，缺它就说明枚举被 ACE 封了。**

★ **⇒ 这是一个**巧妙的健全性检查**。**

---

## 五、★★★ `export_rva`（第 214–223 行）

```python
def export_rva(dll, names):
    pe = pefile.PE(dll, fast_load=True)
    pe.parse_data_directories(
        directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]])
    want = {n.lower() for n in names}
    got = {}
    for e in pe.DIRECTORY_ENTRY_EXPORT.symbols:
        if e.name and e.name.decode("latin1").lower() in want:
            got[e.name.decode("latin1")] = e.address
    return got
```

★★★ **⇒ 用 `pefile` 解析**磁盘上**的 DLL 导出表，得到 RVA。**

★★ **⇒ 三个要点：**
```
① fast_load=True              ← 只解析必要部分
② 只解析 EXPORT 目录           ← 不解析其他目录（快）
③ 大小写不敏感（.lower()）     ← 因为 Windows 导出名不区分大小写
```

★ **⇒ 返回 `{原始名: RVA}`（键用磁盘上的原名，不是查询时的小写）。**

★★ **⇒ 这解释了 `nt10.py` 依赖 `pefile`（`run.cmd:9` 提到）。**

---

## 六、★★★★★ `pick_stolen`（第 226–237 行）—— **挑选被覆盖的指令**

```python
def pick_stolen(orig, tgt):
    stolen, n = b"", 0
    for ins in MD.disasm(orig, tgt):
        if ins.mnemonic in REL_BAD or ins.mnemonic.startswith("j"):
            return None, 0
        if "eip" in ins.op_str or "rip" in ins.op_str:
            return None, 0
        stolen += orig[n:n + ins.size]
        n += ins.size
        if n >= 5:
            return stolen, n
    return None, 0
```

### ★★★★★ 完整的 trampoline 前置规则

★★★ **⇒ `REL_BAD`（第 73 行）：**
```python
REL_BAD = ("call", "jmp", "ret", "retn", "loop", "loope", "loopne", "loopd")
```

★★★ **⇒ 两条拒绝规则：**

| # | 条件 | 原因 |
|---|---|---|
| 1 | `mnemonic in REL_BAD` **或** `startswith("j")` | ★ **相对跳转无法安全搬移**（rel32 会失效） |
| 2 | `"eip" in op_str` **或** `"rip" in op_str` | ★★ **引用了指令指针**（`call $+5` / `pop eax` 类技巧） |

★★★ **⇒ 累积到 **≥ 5 字节**（`E9 rel32` 需要 5 字节）。**

★ **⇒ 返回 `(stolen_bytes, count)`；失败返回 `(None, 0)`。**

★★ **⇒ `startswith("j")` 覆盖了所有 `jXX` 条件跳转（`je`/`jne`/`jg`/`jl`...），**
**加上 `REL_BAD` 里的 `jmp` ⇒ **所有跳转都被拒绝**。**

★★★ **⇒ 这是**标准的 inline hook 前置检查**，非常严谨。**

---

## 七、★★★★★ `build_tramp` 的三种模式（第 240–249 行开头）

```python
def build_tramp(count_addr, arr_addr, stolen, back_addr, cave_addr, str_off, mode="ptr"):
    """完整保留 EAX/ECX/EDX/ESI(游戏内部函数大量 thiscall, ECX 就是 this)

    mode="args" : 记录 4 个参数(ws2_32 那批, 参数直接压栈)
    mode="ptr"  : 记录 str_off 位置的指针指向的内容(字符串类)
    mode="decl" : 在 "args" 基础上, 额外把 arg2 处的 pLen 指针解引用, 存进记录内容区
                  第 4 个 DWORD(= 记录 +0x14)。用于 3 参数的 blob 取值函数
                  (tag, dst, pLen): 调用方 pLen 初值 = 它自己声明的缓冲区容量,
                  runtime 会把它改成"实际写入长度" —— 抢在函数执行前记下来,
                  就能拿到每个 tag 的真实期望尺寸。dst==0 的那次(查询长度模式)
```

### ★★★★★ 三种捕获模式

| 模式 | 记录内容 | 用途 |
|---|---|---|
| **`"args"`** | **4 个参数**（直接压栈值） | ws2_32 那批 |
| **`"ptr"`** | **`str_off` 位置的指针指向的内容** | 字符串类 |
| **`"decl"`** | `"args"` 基础上，**额外解引用 arg2 的 pLen**，存到**记录 +0x14** | ★ 3 参数的 blob 取值函数 |

### ★★★★ `"decl"` 模式的深度洞察（逐字）

> 用于 3 参数的 blob 取值函数 `(tag, dst, pLen)`:
> **调用方 pLen 初值 = 它自己声明的缓冲区容量**,
> **runtime 会把它改成"实际写入长度"** —— **抢在函数执行前记下来,
> 就能拿到每个 tag 的真实期望尺寸**。`dst==0` 的那次(查询长度模式)

★★★★★ **⇒ 这是一个**极其精巧的观测技巧**：**
```
函数签名：f(tag, dst, pLen)
        ↓
调用方传入的 pLen = 缓冲区**容量**
        ↓
函数执行后，pLen 被改成**实际写入长度**
        ↓
★ 抢在函数执行**前**读 pLen ⇒ 拿到"调用方期望的尺寸"
```

★★ **⇒ 且 `dst==0` 是"查询长度模式"（先问要多大，再分配）。**

★★★ **⇒ 这与 `build_tas_image`（第 366 行）的 tag 机制**直接相关**。**

### ★★★ 寄存器保留的说明（第 241 行）

> **完整保留 EAX/ECX/EDX/ESI**（游戏内部函数大量 **thiscall, ECX 就是 this**）

★★★ **⇒ `thiscall` 约定：`ECX` = `this`，参数在栈上。**
**⇒ 所以 hook 必须完整保留 `ECX`（否则 `this` 被破坏）。**

★ **⇒ 这也解释了为什么 `TRAMP_APIS` 的参数偏移是**从栈上算**的** ——**
**因为 `thiscall` 的参数确实在栈上（`ECX` 除外）。**

### ★★★ 七个参数

```python
build_tramp(count_addr, arr_addr, stolen, back_addr, cave_addr, str_off, mode="ptr")
```

| 参数 | 含义 |
|---|---|
| `count_addr` | 计数器地址（记录当前是第几条） |
| `arr_addr` | 环形缓冲地址 |
| `stolen` | 被覆盖的原始字节 |
| `back_addr` | 跳回地址（原函数 + n） |
| `cave_addr` | 代码洞地址 |
| `str_off` | 字符串参数在栈上的偏移 |
| `mode` | 捕获模式 |

---

## 八、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | `rpm` 失败 | 返回 `b""`（不抛异常） |
| 2 | `wpm` 校验 | API 返回 **且** `n.value == len(data)` |
| 3 | `mods_toolhelp` 健壮性 | `snap == -1` 检测 + `errors="replace"` |
| 4 | ★★★★★ **PEB 混合位宽** | **64 位 Python ⇒ `pbi[1]`（+8）；目标进程用 32 位偏移** |
| 5 | PEB 链偏移 | `+0x0C` Ldr / `+0x18` DllBase / `+0x1C` Size / `+0x2C` Length / `+0x30` Buffer |
| 6 | PEB 循环保护 | `cur != 0` / `cur != head` / `< 400` 个 |
| 7 | 名称长度上限 | **520 字节**（= MAX_PATH 的 UTF-16） |
| 8 | ★★ `mods_any` 判据 | **结果里有 `ws2_32` 才算成功** |
| 9 | `export_rva` | `pefile` + `fast_load` + 只解析 EXPORT |
| 10 | ★★★ `REL_BAD` | **8 种相对跳转** |
| 11 | ★★★ `pick_stolen` 规则 | 拒绝**所有跳转** + **引用 eip/rip** |
| 12 | 最小覆盖 | **≥ 5 字节** |
| 13 | ★★★ 三种模式 | `args` / `ptr` / **`decl`** |
| 14 | ★★★★★ `decl` 洞察 | **抢在函数执行前读 pLen ⇒ 拿到调用方期望尺寸** |
| 15 | ★★ `dst==0` | **查询长度模式** |
| 16 | ★★★ 寄存器保留 | **EAX/ECX/EDX/ESI**（`thiscall` 的 `ECX` = `this`） |

---

## 九、结论

### 1. ★★★★★ **64 位 Python 操作 32 位进程的位宽陷阱**已完整解决

```
NtQueryInformationProcess 按调用方（64 位）位宽返回
        ↓ PebBaseAddress 在 +8
但目标 PEB 是 32 位 ⇒ 后续用 32 位偏移
```

★ **⇒ 这是本文件**最容易出错的一处**，注释写得极清楚。**

### 2. ★★★ `mods_any` 用 `ws2_32` 是否存在作为"枚举成功"判据

★ **⇒ 巧妙的健全性检查。**

### 3. ★★★★★ `build_tramp` 的 `"decl"` 模式是**观测设计的精华**

★★★ **⇒ 抢在函数执行前读 `pLen`，拿到调用方声明的缓冲区容量。**
**这是"在不改代码的前提下观测协议期望值"的经典手法。**

### 4. ★★★ `pick_stolen` 拒绝所有跳转与 eip 引用，最小 5 字节

### 5. ★★ `thiscall` 的 `ECX = this` 决定了必须完整保留寄存器

---

## 十、下一步

- `build_tramp` 的完整实现（第 249–316 行）
- `describe_sockaddr` / `follow_str` / `decode_cmdline`（第 317–365 行）
- `build_tas_image`（第 366–490 行）—— TCLS 共享内存镜像
- `parse_patches` / `apply_patches`（第 494–545 行）
- 四个兼容补丁（第 546–709 行）
- 会话密钥快照（第 710–804 行）
- `playerstate_probe_thread`（第 1118–1318 行）
- `main()`（第 1319 行起）
