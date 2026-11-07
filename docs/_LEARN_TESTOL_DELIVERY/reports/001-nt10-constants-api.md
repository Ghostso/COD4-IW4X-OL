# 学习报告 001 — nt10.py 常量表与 API 契约（第 24-98 字节区）

**文件**：`F:\桌面\ol\TESTOL 完整交付版\bundle\nt10.py`
**学习范围**：行 24-98（imports / 常量 / ctypes 签名 / TRAMP_APIS 表）
**字节区间**：约 24-98 行对应的源码文本

---

## 一、这一块是什么

`nt10.py` 的**基座声明区**。它不执行任何逻辑，但定义了后面所有代码依赖的
Windows API 契约、内存布局常量和 hook 参数表。**理解错了这里，后面全错。**

---

## 二、逐项拆解

### 1. 依赖（行 24-37）

```python
import argparse, io, ctypes, os, re, struct, subprocess, sys, threading, time
from ctypes import wintypes
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
```

| 依赖 | 用途 |
|---|---|
| `ctypes` + `wintypes` | 全部 Win32 调用 |
| `pefile` | 解析 ws2_32.dll / kernel32.dll 的**导出表**，取 RVA |
| `capstone` | **x86-32 反汇编器**，用于 `pick_stolen` 判断哪几条指令能安全搬运 |

★ 注意 `CS_MODE_32` —— 目标是 32 位进程，尽管跑 `nt10.py` 的 Python 是 64 位。

### 2. 内存权限常量（行 41-45）

```python
PROC_ALL = 0x0008 | 0x0010 | 0x0020 | 0x0400
```

四个权限位合成 `OpenProcess` 的访问掩码：

| 位 | 名称 | 为什么需要 |
|---|---|---|
| `0x0008` | `PROCESS_VM_OPERATION` | 要 `VirtualAllocEx` / `VirtualProtectEx` |
| `0x0010` | `PROCESS_VM_READ` | 要 `ReadProcessMemory` 读密钥 |
| `0x0020` | `PROCESS_VM_WRITE` | 要 `WriteProcessMemory` 打补丁 |
| `0x0400` | `PROCESS_QUERY_INFORMATION` | 要查进程信息 |

**没有 `PROCESS_CREATE_THREAD` (0x0002)** —— 说明这套代码**不用 `CreateRemoteThread`**，
所有执行都是靠**劫持目标已有的调用路径**（inline hook），不是注入新线程。

```python
MEM_COMMIT_RESERVE = 0x3000    # 同时 Commit + Reserve
PAGE_EXECUTE_READWRITE = 0x40  # 代码洞必须可执行
TH32CS_SNAPMODULE32 = 0x00000010  # 从 64 位进程枚举 32 位模块，必须带这一位
```

### 3. `JNE_ADDR = 0x0077F6EF`（行 46）

一个**硬编码的绝对地址**。后面 `patcher()` 线程会每 0.2 秒读这里 2 字节，
发现是 `75 xx`（JNE）就改成 `EB xx`（JMP）。

**这是绕过某个条件跳转的补丁点**，绑定这一个 build（`0x6096930A`）。

### 4. 环形缓冲布局（行 48-53）

```python
RING   = 1024        # 最多 1024 条记录
REC    = 72          # 每条 72 字节
SLOT   = 0x20000     # 每个 hook 占 128 KB 代码洞
CODE_OFF = 24        # 记录内偏移 24 = 调用点机器码
CODE_LEN = 48        # 抄 48 字节原始指令
BUF_LEN  = 4 + 1024*72 = 73,732
```

**记录 72 字节的精确分配**（注释写明）：

```
+0   4B  调用者返回地址
+4   4B  参数（或指针）
+8  16B  内容区（sockaddr 前 16 字节 / 4 个 DWORD）
+24 48B  调用点的 48 字节原始机器码
```

★ **为什么抄 48 字节机器码**：事后可以反汇编调用点，看**是哪个 API、哪个调用者**
在做事。这是"抓现场"而不是"抓结果"。

### 5. ctypes 签名（行 55-70）

关键点：**`restype` 必须显式设为 `HANDLE`/`c_void_p`**。

```python
k32.OpenProcess.restype = wintypes.HANDLE
k32.VirtualAllocEx.restype = ctypes.c_void_p
k32.MapViewOfFile.restype = ctypes.c_void_p
```

**不设 `restype` 的后果**：ctypes 默认按 `c_int`（32 位有符号）返回，
64 位下句柄/地址被截断成负数 → 后续所有调用失败。这是 ctypes 最常见的坑。

`CreateFileMappingW` 的签名里 `hFile = HANDLE(-1)` 对应 `INVALID_HANDLE_VALUE`，
用于创建**页文件支持的**共享内存（TCLS 镜像要用）。

### 6. `REL_BAD`（行 73）

```python
REL_BAD = ("call", "jmp", "ret", "retn", "loop", "loope", "loopne", "loopd")
```

`pick_stolen` 用它判断"这几条指令能不能搬到跳板里"。

**逻辑**：如果被偷的指令里有相对跳转，搬到别处后**相对偏移全错**，
所以整条放弃。`ret` 类会让跳板提前返回，也放弃。

### 7. `TRAMP_APIS`（行 75-124）

每个 hook 目标的参数描述：`(str_off, wide, mode)`

| 字段 | 含义 |
|---|---|
| `str_off` | 参数在栈上的偏移（`esp+N`） |
| `wide` | 是否宽字符（UTF-16） |
| `mode` | `ptr`（解引用读内容）/ `args`（直接记 4 个参数） |

**按类别分**：

| 类别 | API | 关键点 |
|---|---|---|
| ws2_32 网络 | `connect` `sendto` `bind` `send` | `str_off=8/0x14`，`ptr` 解引用 sockaddr |
| 域名解析 | `getaddrinfo` `gethostbyname` | `str_off=4`，`ptr` 顺着指针读域名 |
| 共享内存 | `OpenFileMappingW` `CreateFileMappingW` | **`wide=True`** —— 名字是 W 版宽字符 |
| 进程创建 | `CreateProcessW` `WinExec` | `args` 模式，记 4 个参数 |
| 窗口消息 | `PostMessageW` `SendMessageW` | `args` 模式 |
| **WinHttp** | `WinHttpConnect` `WinHttpOpenRequest` | **`wide=True`** |

★★ **最重要的一条注释（行 97）**：

> WinHttp：大厅/上报的 HTTP 请求**全走这里**（ws2_32 的 connect 看不到）。

这解释了为什么只 hook ws2_32 会漏掉大厅流量——大厅用的是 WinHTTP 栈，
不是 Winsock。

---

## 三、这一块的关键结论

1. **不使用远程线程注入** —— 权限掩码里没有 `0x0002`，全靠 inline hook。
2. **记录是 72 字节定长**，含 48 字节调用点机器码 —— 为事后反汇编留证据。
3. **`wide` 标志区分 A/W 版** —— `OpenFileMappingW`/`WinHttpConnect` 是宽字符，
   读错会用 GBK 解码 UTF-16 得到乱码。
4. **大厅流量必须 hook WinHTTP**，ws2_32 看不到。
5. **`JNE_ADDR` 是硬编码**，换 build 就失效。

---

## 四、待验证

- [ ] `TRAMP_APIS` 里每个 `str_off` 是否与该 API 的调用约定一致（逐个核 stdcall 参数序）
- [ ] `JNE_ADDR = 0x0077F6EF` 在本 build 的实际字节与语义
- [ ] 48 字节机器码是否够覆盖最长的调用点（有些 `call [xxx]` 前面有长 prologue）
