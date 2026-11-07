# 学习报告 048（重开）— `force_display_name.py` 头部与内存扫描

**学习范围**：`bundle\force_display_name.py`（19,288 B / 389 行）第 1–120 行
**性质**：全实测
**★★★ 本报告收录**四条服务端通道全部失效的完整证据**与**`AdministraClient` 的构造算法**

---

## 一、★★★★★ docstring：四条通道全部失效（第 4–16 行，逐字）

```python
为什么走内存（`[实测]` 2026-10-05 17:38–17:5x）
  界面显示的是 `AdministraClient`，而且：
    * 服务端能给的三个通道全被客户端忽略 —— 认证应答 ticket `+33`、
      认证应答 `extra_data.username`(base64)、`Identity.json` 的 `displayName`
      （逐条证据见 `01-findings\定因-名字-客户端自己造了AdministraClient-20261005-1745.md`）
    * TCLS 共享内存里的名字客户端**一个字节都不读**（注入 `name=CODOL-LOCAL`，
      在 1,517 MB 内存里命中 **0** 次）
    * `Platformwrapper` 的 Tencent 接口（`Tencent.cpp:35-53`）**没有任何名字槽位**
    * 磁盘上搜不到 `AdministraClient` 这个串 ⇒ 它是运行期用 Windows 账户名
      `Administrator` 拼出来的（`Administra` + `Client` = 16 字节，正好是字段容量）
  ⇒ 与老外文档说法一致：归档插件的做法就是**直接写客户端那个结构**
    （`.agents\research\dw3_feasibility.md:84-90`：把字面量写进
     "the DW authentication account structure"）。
```

### ★★★★★ 四条失效通道 + 一条决定性证据

| # | 通道 | 状态 | 证据 |
|---|---|---|---|
| **1** | 认证应答 **ticket `+33`** | ✗ **被忽略** | 定因文档 |
| **2** | 认证应答 **`extra_data.username`**(b64) | ✗ **被忽略** | 同上 |
| **3** | **`Identity.json` 的 `displayName`** | ✗ **被忽略** | 同上 |
| **4** | **TCLS 共享内存** | ✗ **一个字节都不读** | ★ 注入 `name=CODOL-LOCAL`，**1,517 MB 内存里命中 0 次** |
| **5** | `Platformwrapper` Tencent 接口 | ✗ **无名字槽位** | `Tencent.cpp:35-53` |

★★★ **⇒ 第 4 条是**最强的负面证据**：**
```
向 TCLS 共享内存注入 name = "CODOL-LOCAL"
        ↓
在 **1,517 MB** 内存里搜索该串
        ↓
★★★ **命中 0 次**
        ↓
⇒ 客户端**根本不读** TCLS 里的名字
```

### ★★★★★ `AdministraClient` 的构造算法（第 12–13 行）

```
磁盘上搜不到 `AdministraClient` 这个串
        ↓
⇒ 它是运行期用 Windows 账户名 `Administrator` 拼出来的
        ↓
`Administra` + `Client` = 16 字节
        ↓
★ 正好是字段容量
```

★★★ **⇒ 完整的构造算法：**
```c
// Windows 账户名 = "Administrator"（13 字符）
// 取前 10 个字符 = "Administra"
// 拼接 "Client" = "AdministraClient"（16 字符）
```

★★ **⇒ **"正好是字段容量"** 说明：**
```
取前 10 字符 + "Client" = 16 字符
        ↓
★ 16 是名字字段的定长
        ↓
⇒ 所以取 10（16 - 6 = 10）
```

★★★ **⇒ 这解释了为什么换 Windows 账户名会改变界面名**（报告 014 已记录）。

### ★★ 老外的做法（第 14–16 行）

```
⇒ 与老外文档说法一致：归档插件的做法就是**直接写客户端那个结构**
  （`.agents\research\dw3_feasibility.md:84-90`：把字面量写进
   "the DW authentication account structure"）。
```

★★ **⇒ 老外也是**直接写内存**（不是走服务端通道）。**

★ **⇒ 出处：`.agents\research\dw3_feasibility.md:84-90`。**

---

## 二、★★★ 三种用法（第 18–21 行）

```
用法
    python force_display_name.py                 # 只报告，不改
    python force_display_name.py --apply FF0     # 就地改（可重复执行）
    python force_display_name.py --apply FF0 --list-only
```

★★ **⇒ `--apply FF0` —— 改成一个叫 `FF0` 的名字。**

---

## 三、★★★ 常量与 ctypes 绑定（第 29–57 行）

```python
TARGET = "codoMP_client_shipRetail.exe"
MEM_COMMIT = 0x1000
READABLE = (0x02, 0x04, 0x20, 0x40)
PAGE_EXECUTE_READWRITE = 0x40
PAGE_READWRITE = 0x04

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
PROCESS_VM_OPERATION = 0x0008
```

### ★★★ 完整的权限与页保护常量

| 常量 | 值 | 含义 |
|---|---|---|
| **`READABLE`** | **`(0x02, 0x04, 0x20, 0x40)`** | `PAGE_READONLY` / `READWRITE` / `EXECUTE_READ` / `EXECUTE_READWRITE` |
| `PAGE_EXECUTE_READWRITE` | `0x40` | 可读写执行 |
| `PAGE_READWRITE` | `0x04` | 可读写 |
| `PROCESS_QUERY_INFORMATION` | `0x0400` | 查询信息 |
| `PROCESS_VM_READ` | `0x0010` | 读内存 |
| `PROCESS_VM_WRITE` | `0x0020` | 写内存 |
| `PROCESS_VM_OPERATION` | `0x0008` | 内存操作 |

★★★ **⇒ `READABLE` 包含**四种**页保护（比 `nt10.py` 的 `MEM_PRIVATE` 扫描**范围更广**）：**
```
0x02  PAGE_READONLY
0x04  PAGE_READWRITE
0x20  PAGE_EXECUTE_READ
0x40  PAGE_EXECUTE_READWRITE
```

★★ **⇒ 这与报告 027 的对比：**
```
nt10.py scan_dword       →  只扫 MEM_PRIVATE（堆）
force_display_name.py    →  扫所有 READABLE（含镜像）
```

★ **⇒ 因为名字字段可能在**镜像的只读数据段**里。**

### ★★ `MEMORY_BASIC_INFORMATION`（第 53–57 行）

★ **⇒ 与 `nt10.py` 的 `_MBI` **完全相同**（7 个字段）。**

---

## 四、★★★ `find_pid`（第 60–77 行）

```python
def find_pid():
    class PE32(ctypes.Structure):
        _fields_ = [("dwSize", ...), ..., ("szExeFile", ctypes.c_char * 260)]
    snap = k32.CreateToolhelp32Snapshot(0x00000002, 0)     # ★ TH32CS_SNAPPROCESS
    entry = PE32()
    entry.dwSize = ctypes.sizeof(entry)
    ok = k32.Process32First(snap, ctypes.byref(entry))
    while ok:
        if entry.szExeFile.decode("latin1").lower() == TARGET.lower():
            k32.CloseHandle(snap)
            return entry.th32ProcessID
        ok = k32.Process32Next(snap, ctypes.byref(entry))
    k32.CloseHandle(snap)
    return None
```

★★★ **⇒ `0x00000002` = `TH32CS_SNAPPROCESS`（★ 进程枚举，不是模块枚举）。**

★★ **⇒ 与 `nt10.py` 的 `TH32CS_SNAPMODULE`（`0x08`）**不同**：**
```
nt10.py  用 SNAPMODULE（★ 被 ACE 封）
本文件    用 SNAPPROCESS（★ 未被封）
```

★★★ **⇒ 这是一个**关键的差异**：**
**ACE 封的是**模块枚举**，不是**进程枚举**。**

★ **⇒ `decode("latin1")` —— 避免非 ASCII 崩溃。**

---

## 五、★★★★ `regions` 与 `scan`（第 80–112 行）

### 5.1 `regions`（第 80–92 行）

```python
def regions(handle):
    address = 0
    mbi = MEMORY_BASIC_INFORMATION()
    while address < 0x7FFFFFFF:                    # ★ 32 位上限
        if not k32.VirtualQueryEx(handle, ctypes.c_void_p(address), ctypes.byref(mbi),
                                 ctypes.sizeof(mbi)):
            break
        size = mbi.RegionSize
        if size == 0:
            break
        if mbi.State == MEM_COMMIT and mbi.Protect in READABLE:    # ★ 两个过滤
            yield address, size
        address += size
```

★★★ **⇒ 两个过滤条件：**
```
① `mbi.State == MEM_COMMIT`      （已提交）
② `mbi.Protect in READABLE`      （★ 四种可读保护之一）
```

★ **⇒ **没有**排除 `PAGE_GUARD`（`0x100`）—— 因为 `READABLE` 元组里没有它。**

★★ **⇒ 若遇到 `PAGE_GUARD` 页，`Protect` 会是 `0x100 | base`，**不在 `READABLE` 里** ⇒ 自动排除。**

### 5.2 ★★★ `scan`（第 95–112 行）

```python
def scan(handle, needle):
    hits = []
    total = 0
    for base, size in regions(handle):
        buf = ctypes.create_string_buffer(size)          # ★ 按区大小分配
        read = ctypes.c_size_t()
        if k32.ReadProcessMemory(handle, ctypes.c_void_p(base), buf, size, ctypes.byref(read)) \
                and read.value:
            data = buf.raw[:read.value]
            total += len(data)
            start = 0
            while True:
                index = data.find(needle, start)
                if index < 0:
                    break
                hits.append(base + index)
                start = index + 1                        # ★ +1（允许重叠）
    return hits, total
```

★★★ **⇒ 三个要点：**
```
① **按区大小一次性分配并读取**（不是分块）
② ★ `total` 累加**实际读到的字节数**（用于报告"扫描了多少 MB"）
③ ★★ `start = index + 1`（**允许重叠匹配**）
```

★★ **⇒ 第 ① 条与 `nt10.py` 的**分块读取**（`0x40000`）**不同**：**
```
nt10.py            分块（每次 256 KB）
force_display_name 整区读取
```

★ **⇒ 若某区很大（如 1 GB），整区分配可能失败 —— 这是**潜在风险**。**

★★ **⇒ 但上一轮报告 014 记录实测扫了 **1,517 MB**，说明分区大小可接受。**

---

## 六、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★★★ 失效通道 1 | 认证应答 **ticket `+33`** |
| 2 | 失效通道 2 | **`extra_data.username`**(b64) |
| 3 | 失效通道 3 | **`Identity.json` 的 `displayName`** |
| 4 | ★★★★★ 失效通道 4 | **TCLS 共享内存**（注入 `CODOL-LOCAL`，**1,517 MB 命中 0 次**） |
| 5 | 失效通道 5 | `Platformwrapper` **无名字槽位**（`Tencent.cpp:35-53`） |
| 6 | ★★★★★ **名字构造** | **`"Administrator"[:10] + "Client"` = `"AdministraClient"`（16 字节）** |
| 7 | ★ 关键洞察 | **"正好是字段容量"**（16） |
| 8 | ★ 老外做法 | **直接写内存**（`dw3_feasibility.md:84-90`） |
| 9 | ★★★ `READABLE` | **`(0x02, 0x04, 0x20, 0x40)`** —— 四种页保护 |
| 10 | ★★ 与 `nt10` 对比 | 本文件扫**所有可读区**（含镜像），`nt10` 只扫 `MEM_PRIVATE` |
| 11 | ★★★ 进程枚举 | **`TH32CS_SNAPPROCESS`（`0x02`）**，不被 ACE 封 |
| 12 | ★ 与 `nt10` 对比 | `nt10` 用 `SNAPMODULE`（`0x08`，**被 ACE 封**） |
| 13 | ★ 地址上限 | **`0x7FFFFFFF`** |
| 14 | ★★ 扫描步长 | **`start = index + 1`**（允许重叠） |
| 15 | ★ 统计 | `total` 累加**实际读到的字节数** |

---

## 七、结论

### 1. ★★★★★ **五条通道全部失效**是"只能改内存"的完整论证

★★ **⇒ 尤其第 4 条（TCLS 内存注入，1,517 MB 命中 0 次）是最硬的负面证据。**

### 2. ★★★★★ **`"Administrator"[:10] + "Client"` = 16 字节** 是名字构造算法

★ **⇒ "正好是字段容量"揭示了取 10 字符的原因（16 − 6 = 10）。**

### 3. ★★★ **`TH32CS_SNAPPROCESS` 不被 ACE 封**（与 `SNAPMODULE` 不同）

★ **⇒ 这是 `force_display_name.py` 能工作的前提。**

### 4. ★★ **扫所有 `READABLE` 区**（含镜像），与 `nt10.py` 的 `MEM_PRIVATE` 不同

★ **⇒ 因为名字字段可能在只读数据段。**

### 5. ★★ 整区读取是潜在风险（大区可能分配失败）

---

## 八、下一步

- `force_display_name.py` 剩余（第 120 行起）—— `context` / `truncate_encoded` / `main`
- `bundle\` 五个证书文件
- `payload\` 四个插件 PE + 四个 loader 二进制
