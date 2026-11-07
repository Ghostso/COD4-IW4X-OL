# 学习报告 020（重开）— `nt10.py` 头部与常量层（第 1–130 行）

**学习范围**：`bundle\nt10.py`（146,765 B）的 docstring + 全部常量 + TRAMP_APIS 表
**性质**：全实测
**★★★ 本报告逐字收录**四条关键设计**与**完整 hook 参数表**

---

## 一、★★★★★ 文件头 docstring（第 1–23 行）—— 四条关键设计

```python
# -*- coding: utf-8 -*-
"""自包含: TAS 注入 + 早期枚举 + PEB 模块链 + 命名/模块:RVA 两种 hook + 磁盘快照

为什么要独立文件: nt8.py 在本机被反复回滚成半成品(改 A 丢 B), 导致关键函数在运行时不存在。

关键设计
  1. 模块枚举必须"早"(t≈0.2s): 晚了会被 ACE 封掉(toolhelp 返回空)。
  2. hook 安装要"晚"(默认 delay 2.5s): 太早会撞上 TP3 在 t≈2s 的 ws2_32 完整性检查 -> 游戏 0xC0000005。
     两者解耦: 枚举在前, 装 hook 在后。
  3. 但 TenProxy.dll 要到 t≈5s 才被加载, 所以它的基址要在那时用"PEB 模块链"现查
     (句柄用 t≈0 打开的那个, 它一直可用)。
  4. 命中缓冲每 0.4s 落盘一次, 游戏提前退出也不丢数据。
```

### ★★★★★ 四条设计的时间线（逐字整理）

| # | 时刻 | 事件 | 约束 |
|---|---|---|---|
| 1 | **t ≈ 0.2 s** | ★★★ **模块枚举** | **晚了会被 ACE 封掉**（`toolhelp` 返回空） |
| 2 | **t ≈ 2 s** | TP3 的 `ws2_32` 完整性检查 | ★ **太早装 hook 会撞上 ⇒ `0xC0000005`** |
| 3 | **默认 2.5 s** | ★★★ **装 hook** | 必须晚于 t≈2s |
| 4 | **t ≈ 5 s** | `TenProxy.dll` 被加载 | ★ 基址要用 **PEB 模块链**现查 |
| 5 | 每 **0.4 s** | 命中缓冲落盘 | 游戏提前退出不丢数据 |

★★★ **⇒ 核心洞察：**枚举与装 hook 必须解耦****
```
枚举在前（t≈0.2s，趁 ACE 还没封）
装 hook 在后（t≈2.5s，避开 TP3 检查）
```

★★★ **⇒ 三个精确时间点：`0.2 s` / `2 s` / `5 s`，以及两个默认值 `2.5 s` / `0.4 s`。**

★★ **⇒ 且揭示了一个**关键的反作弊时序**：**
```
ACE 在 t≈0.2s 后封 toolhelp
TP3 在 t≈2s 做 ws2_32 完整性检查
TenProxy 在 t≈5s 才加载
```

★ **⇒ 这解释了为什么 `launch_chain.py` 用 `--delay 0`（报告 019）**会与默认值 2.5s 冲突** ——**
**`--delay 0` 会让 hook 在 t≈0 装上，**正好撞上 TP3 检查**。**

★★★ **⇒ 这可能就是"坏启动率"的另一个来源（除了 STUN 和 Winsock hook 竞态）。**

### ★★★ "为什么要独立文件"（第 4 行）

> **为什么要独立文件**: `nt8.py` 在本机被反复回滚成半成品(**改 A 丢 B**),
> 导致关键函数在运行时不存在。

★★ **⇒ `nt8.py` 是前身，被"反复回滚成半成品"。**
**⇒ 这是**文件被外部工具/环境回滚**的证据。**

★ **⇒ 第 19–20 行补充：**
> 补丁规格 / TAS 规格 / 迟到 hook 目标 都从同目录的 `patch_spec.txt`、`tas_spec.txt` 读
> (**命令行开关会被环境回滚, 文件不会**)

★★★ **⇒ **命令行开关会被环境回滚，文件不会** —— 这是一个**重要的设计决策依据**。**

★★ **⇒ 但 `patch_spec.txt` / `tas_spec.txt` **不在交付包里**（需验证）。**

---

## 二、★★★ 用法示例（第 14–22 行）

```python
用法:
  python nt10.py --secs 120 --delay 0 --out n10n.txt ^
      --apis OpenFileMappingW,OpenFileMappingA,CreateFileMappingW,CreateFileMappingA,^
MapViewOfFile,connect,sendto,getaddrinfo,GetAddrInfoW,gethostbyname,z1,z2,z3
```

★★ **⇒ 示例里 `--delay 0` —— 与"关键设计 2"的"默认 2.5s"**矛盾**。**
**⇒ 说明示例是**为了尽早观测**，不是生产配置。**

★★ **⇒ 示例的 `--apis` 有 **13 项**（含 3 个占位 `z1`/`z2`/`z3`）。**

### ★★★ 两个机制说明（第 19–22 行）

> 补丁规格 / TAS 规格 / 迟到 hook 目标 都从同目录的 `patch_spec.txt`、`tas_spec.txt` 读
> (命令行开关会被环境回滚, 文件不会)。`--apis` 里的 `zN` 只是占位, 用来把代码洞/计数器槽位
> 预留出来(迟到 hook 用), 不会真的去装 hook。要手动钉某个 tenproxy 函数就写
> `--apis ...,@tenproxy.dll:0x6BD0`

★★★ **⇒ 三种规格文件：**
```
patch_spec.txt        补丁规格
tas_spec.txt          TAS 规格
（迟到 hook 目标）     ← 可能也在某个 spec 文件里
```

★ **⇒ `@tenproxy.dll:0x6BD0` 是**手动钉 hook 地址**的语法。**

---

## 三、★★★ 常量层（第 41–53 行）

```python
PROC_ALL = 0x0008 | 0x0010 | 0x0020 | 0x0400
MEM_COMMIT_RESERVE = 0x3000
PAGE_EXECUTE_READWRITE = 0x40
TH32CS_SNAPMODULE = 0x00000008
TH32CS_SNAPMODULE32 = 0x00000010
JNE_ADDR = 0x0077F6EF

RING = 1024
REC = 72                      # 调用者4 + 参数4 + 内容16 + 调用点机器码48
SLOT = 0x20000
CODE_OFF = 24
CODE_LEN = 48
BUF_LEN = 4 + RING * REC
```

### ★★★ 逐个解析

| 常量 | 值 | 含义 |
|---|---|---|
| `PROC_ALL` | `0x0438` | `PROCESS_VM_OPERATION\|VM_READ\|VM_WRITE\|QUERY_INFORMATION` |
| `MEM_COMMIT_RESERVE` | `0x3000` | `MEM_COMMIT \| MEM_RESERVE` |
| `PAGE_EXECUTE_READWRITE` | `0x40` | 可读写执行 |
| `TH32CS_SNAPMODULE` | `0x08` | 模块快照 |
| `TH32CS_SNAPMODULE32` | `0x10` | 32 位模块快照 |
| **`JNE_ADDR`** | **`0x0077F6EF`** | ★★★ **某个 JNE 指令的地址** |
| `RING` | **`1024`** | 环形缓冲槽数 |
| **`REC`** | **`72`** | ★★★ **每条记录 72 字节** |
| `SLOT` | **`0x20000`** | 每个 API 的代码洞大小（**128 KB**） |
| `CODE_OFF` | **`24`** | 记录内代码偏移 |
| `CODE_LEN` | **`48`** | 记录内代码长度 |
| `BUF_LEN` | **`4 + 1024×72 = 73,732`** | 缓冲区总长 |

### ★★★ `REC = 72` 的分解（逐字注释）

```
调用者4 + 参数4 + 内容16 + 调用点机器码48 = 72
```

★★★ **⇒ 每条命中记录的布局：**
```
+0   4 字节   调用者（返回地址）
+4   4 字节   参数（指针值）
+8  16 字节   内容（前 16 字节）
+24 48 字节   调用点机器码（★ CODE_OFF=24, CODE_LEN=48）
---
    72 字节
```

★★★ **⇒ 记录**调用点 48 字节机器码** —— 这是**反汇编上下文**，用于事后分析。**

★ **⇒ `RING=1024` × `REC=72` + 4 字节头 = **73,732 字节**的共享缓冲。**

---

## 四、★★★★★ `TRAMP_APIS` 表（第 75–105 行）—— **33 个 API 的 hook 参数规范**

```python
TRAMP_APIS = {
    "connect": (8, False, "ptr"), "WSAConnect": (8, False, "ptr"),
    "sendto": (0x14, False, "ptr"), "WSASendTo": (0x18, False, "ptr"),
    "bind": (8, False, "ptr"), "send": (8, False, "ptr"),
    "getaddrinfo": (4, False, "ptr"), "GetAddrInfoW": (4, True, "ptr"),
    "gethostbyname": (4, False, "ptr"),
    "socket": (0, False, "args"), "WSASocketW": (0, False, "args"),
    "recv": (0, False, "args"), "recvfrom": (0, False, "args"),
    "WSARecv": (0, False, "args"), "WSARecvFrom": (0, False, "args"),
    # 共享内存(TAS): 用来确认游戏是否在等 TCLS 递交的票据/服务器地址
    # (E:\1\nt8.py 里的原样三项 + A 版两项, nt10 之前漏了这整块, 导致 "跳过(不支持)")
    "OpenFileMappingW": (0xC, True, "ptr"),
    "CreateFileMappingW": (0x18, True, "ptr"),
    "OpenFileMappingA": (0xC, False, "ptr"),
    "CreateFileMappingA": (0x18, False, "ptr"),
    "MapViewOfFile": (0, False, "args"),
    # kernel32 / user32 (最小改动: 只加常用项, 参数统一用 args 模式)
    "CreateProcessW": (0, False, "args"), "CreateProcessA": (0, False, "args"),
    "WinExec": (0, False, "args"),
    "RegisterWindowMessageW": (4, True, "ptr"), "RegisterWindowMessageA": (4, False, "ptr"),
    "PostMessageW": (0xC, False, "args"), "PostMessageA": (0xC, False, "args"),
    "SendMessageW": (0xC, False, "args"), "SendMessageA": (0xC, False, "args"),
    # WinHttp: 大厅/上报的 HTTP 请求全走这里(ws2_32 的 connect 看不到)。
    #   WinHttpConnect(hSession, pswzServerName[W], nServerPort, dwReserved)
    #   WinHttpOpenRequest(hConn, pwszVerb, pwszObjectName[W], pwszVersion, ...)
    # 记下 (serverName, port) 和 (path) 就能拼出游戏访问的完整 URL。
    "WinHttpConnect": (8, True, "ptr"),
    "WinHttpOpenRequest": (0xC, True, "ptr"),
    "WinHttpSendRequest": (0, False, "args"),
    "WinHttpReceiveResponse": (0, False, "args"),
}
```

### ★★★★★ 三元组的语义

```
(参数偏移, 是否宽字符, 捕获模式)
```

| 字段 | 含义 |
|---|---|
| **参数偏移** | 要记录的参数在栈上的偏移（0 = 用 `args` 模式全存） |
| **是否宽字符** | `True` = `W` 版（UTF-16），`False` = `A` 版（ANSI） |
| **捕获模式** | `"ptr"` = 参数是指针，需跟进去；`"args"` = 直接存参数值 |

### ★★★ 完整分类表（33 个 API）

#### A. 网络连接（`ptr`，记录 sockaddr）

| API | 偏移 | 宽字符 | 说明 |
|---|---|---|---|
| `connect` | `8` | ✗ | sockaddr* 在第 2 参 |
| `WSAConnect` | `8` | ✗ | 同上 |
| **`sendto`** | **`0x14`（20）** | ✗ | ★ 第 5 参是 sockaddr* |
| `WSASendTo` | `0x18`（24） | ✗ | 第 6 参 |
| `bind` | `8` | ✗ | 第 2 参 |
| `send` | `8` | ✗ | （实际 send 第 2 参是 buf，此处按 ptr 记） |

#### B. DNS（`ptr`，记录域名字符串）

| API | 偏移 | 宽字符 |
|---|---|---|
| `getaddrinfo` | `4` | ✗ |
| `GetAddrInfoW` | `4` | ✓ |
| `gethostbyname` | `4` | ✗ |

#### C. 套接字创建/接收（`args`，全存）

```
socket / WSASocketW / recv / recvfrom / WSARecv / WSARecvFrom
```

#### D. ★★★ 共享内存（TAS）—— 5 个

```python
"OpenFileMappingW": (0xC, True, "ptr"),
"CreateFileMappingW": (0x18, True, "ptr"),
"OpenFileMappingA": (0xC, False, "ptr"),
"CreateFileMappingA": (0x18, False, "ptr"),
"MapViewOfFile": (0, False, "args"),
```

★★★ **⇒ 注释揭示了一个**曾经的遗漏**：**
> (E:\1\nt8.py 里的原样三项 + A 版两项, **nt10 之前漏了这整块, 导致 "跳过(不支持)"**)

★★ **⇒ 五项 = W 版 2 个 + A 版 2 个 + `MapViewOfFile` 1 个。**

★ **⇒ 用途注释：**用来确认游戏是否在等 TCLS 递交的票据/服务器地址**。**

★★★ **⇒ 这与记忆里"`OpenFileMapping TCLS_SHAREDMEMEMORY<pid>` 是全流程的钥匙"**完全吻合**。**

#### E. 进程创建（`args`）

```
CreateProcessW / CreateProcessA / WinExec
```

#### F. 窗口消息（`ptr` 或 `args`）

```
RegisterWindowMessageW: (4, True, "ptr")     ← 记录消息名字符串
RegisterWindowMessageA: (4, False, "ptr")
PostMessageW: (0xC, False, "args")           ← 记录消息号
PostMessageA: (0xC, False, "args")
SendMessageW: (0xC, False, "args")
SendMessageA: (0xC, False, "args")
```

#### G. ★★★ WinHttp（`ptr`，记录 URL 组件）

```python
"WinHttpConnect": (8, True, "ptr"),
"WinHttpOpenRequest": (0xC, True, "ptr"),
"WinHttpSendRequest": (0, False, "args"),
"WinHttpReceiveResponse": (0, False, "args"),
```

★★★ **⇒ 注释是关键（逐字）：**
> **WinHttp: 大厅/上报的 HTTP 请求全走这里(ws2_32 的 connect 看不到)。**
> `WinHttpConnect(hSession, pswzServerName[W], nServerPort, dwReserved)`
> `WinHttpOpenRequest(hConn, pwszVerb, pwszObjectName[W], pwszVersion, ...)`
> **记下 (serverName, port) 和 (path) 就能拼出游戏访问的完整 URL。**

★★★★★ **⇒ 这是**最重要的技术洞察之一**：**
```
大厅/上报的 HTTP 请求**不走 ws2_32 的 connect**
        ↓
只 hook connect/sendto **看不到它们**
        ↓
必须 hook WinHttpConnect + WinHttpOpenRequest
        ↓
记录 (serverName, port) + (path) ⇒ 拼出完整 URL
```

---

## 五、★★★ 三个 API 分组集合（第 106–124 行）

```python
K32_APIS = {"CreateProcessW", "CreateProcessA", "WinExec"}
_K32 = {"OpenFileMappingW": 0x221A0, "CreateFileMappingW": 0x20740,
        "OpenFileMappingA": 0x18780, "CreateFileMappingA": 0x116B0,
        "MapViewOfFile": 0x1F830}
U32_APIS = {"RegisterWindowMessageW", "RegisterWindowMessageA",
            "PostMessageW", "PostMessageA", "SendMessageW", "SendMessageA"}
SOCK_APIS = ("connect", "WSAConnect", "sendto", "WSASendTo", "bind")
WHTTP_APIS = ("WinHttpConnect", "WinHttpOpenRequest",
              "WinHttpSendRequest", "WinHttpReceiveResponse")
```

### ★★★★★ `_K32` 表 —— **kernel32 的硬编码 RVA**（关键）

```python
_K32 = {"OpenFileMappingW": 0x221A0, "CreateFileMappingW": 0x20740,
        "OpenFileMappingA": 0x18780, "CreateFileMappingA": 0x116B0,
        "MapViewOfFile": 0x1F830}
```

★★★ **⇒ 五个 kernel32 函数的**硬编码 RVA**：**

| 函数 | RVA |
|---|---|
| `OpenFileMappingW` | **`0x221A0`** |
| `CreateFileMappingW` | **`0x20740`** |
| `OpenFileMappingA` | **`0x18780`** |
| `CreateFileMappingA` | **`0x116B0`** |
| `MapViewOfFile` | **`0x1F830`** |

★★★ **⇒ 注释解释了原因（逐字）：**
> `E:\1\nt8.py` 的做法: 这几个在 kernel32 里是**真函数(不是转发)**,
> 直接用**本机 RVA + kernel32 基址**定位, **不走 ws2_32 导出扫描**
> (那条路在 **delay=0 / 枚举为空时会整个落空**)

★★★ **⇒ 这是一个**关键的健壮性设计**：**
```
ws2_32 的导出是**转发**到 kernel32 的（forwarder）
        ↓
导出扫描在 delay=0 或枚举为空时**整个落空**
        ↓
改用**硬编码 RVA + kernel32 基址**（真函数地址）
```

★ **⇒ 代价：**RVA 是 Windows 版本相关的** —— 换 Windows 版本可能失效。**

★★ **⇒ 又一个 `E:\1\` 路径泄漏（作者的旧工作目录）。**

### ★★★ `STR_HOOKS`（第 121–124 行）—— 需要"跟字符串"的 hook

```python
STR_HOOKS = {"gethostbyname", "getaddrinfo", "GetAddrInfoW",
             "OpenFileMappingW", "OpenFileMappingA",
             "CreateFileMappingW", "CreateFileMappingA",
             "WinHttpConnect", "WinHttpOpenRequest"}
```

★★★ **⇒ 9 个 API 的参数是**字符串指针**，需要额外"跟进去"抄内容。**

★★ **⇒ 注释解释（第 117–120 行）：**
> 这些 hook 的参数是"指向名字/字符串的指针": **记录内容区只有 16 字节,
> 装不下 "stun1-tub.codol.qq.com" 这种域名** —— 所以 timeline 里还要顺着指针去把整串抄回来。

★★★ **⇒ 且注释给出了一个**重要的判断**（第 119–120 行）：**
> (CODOL 的大厅是 Demonware: exe 里有 `DW_DNS_ERROR`/`DW_LOBBY_ERROR`/`DW_LOBBY_CONNECTED`
>  这一整套状态 + `g_dwConfigVersion`, 所以"**无法连接大厅服务!**"很可能卡在**域名解析/连 DW 端点**)

★★ **⇒ 三个 DW 状态串 + 一个 cvar + 一句中文报错。**

---

## 六、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★ 枚举时刻 | **t ≈ 0.2 s**（晚则 ACE 封 `toolhelp`） |
| 2 | ★★★ TP3 检查 | **t ≈ 2 s**（`ws2_32` 完整性 ⇒ 太早 hook 得 `0xC0000005`） |
| 3 | ★★★ 默认 hook 延迟 | **2.5 s** |
| 4 | ★★★ `TenProxy.dll` 加载 | **t ≈ 5 s** |
| 5 | 落盘间隔 | **0.4 s** |
| 6 | ★★ 设计依据 | **命令行开关会被环境回滚，文件不会** |
| 7 | `PROC_ALL` | `0x0438` |
| 8 | `JNE_ADDR` | **`0x0077F6EF`** |
| 9 | `RING` | **1024** |
| 10 | **`REC`** | **72** = 4+4+16+48 |
| 11 | `SLOT` | **`0x20000`**（128 KB） |
| 12 | `BUF_LEN` | **73,732** |
| 13 | ★★★ `TRAMP_APIS` 条目 | **33 个** |
| 14 | ★★★★★ **WinHttp 洞察** | **大厅/上报走 WinHttp，`ws2_32` 的 connect 看不到** |
| 15 | ★★★ 共享内存 5 项 | W/A 版 + `MapViewOfFile`（**曾遗漏**） |
| 16 | ★★★ `_K32` 硬编码 RVA | 5 个（`0x221A0` / `0x20740` / `0x18780` / `0x116B0` / `0x1F830`） |
| 17 | ★★ 为什么用 RVA | `ws2_32` 导出是**转发**，扫描在 `delay=0` 时落空 |
| 18 | ★★★ `STR_HOOKS` | **9 个**（参数是字符串指针） |
| 19 | ★ 记录区限制 | **16 字节**，装不下域名 |
| 20 | ★★★ DW 状态串 | `DW_DNS_ERROR` / `DW_LOBBY_ERROR` / `DW_LOBBY_CONNECTED` / `g_dwConfigVersion` |
| 21 | ★ 中文报错 | **"无法连接大厅服务!"** |
| 22 | ★ 路径泄漏 | `E:\1\nt8.py`（作者旧工作目录） |

---

## 七、结论

### 1. ★★★★★ 三个**精确到秒**的反作弊时序

```
t≈0.2s  ACE 封 toolhelp        ⇒ 枚举必须在此之前
t≈2s    TP3 查 ws2_32 完整性   ⇒ hook 必须在此之后
t≈5s    TenProxy.dll 才加载    ⇒ 基址要现查
```

★★★ **⇒ 而 `launch_chain.py` 传 `--delay 0` ⇒ **直接撞上 t≈2s 的 TP3 检查**。**

★ **⇒ 这是**继 STUN、Winsock hook 竞态之后的第三个不稳定源**。**

### 2. ★★★★★ **WinHttp 是隐藏的大厅通道**

★★★ **⇒ "大厅/上报的 HTTP 请求全走这里（`ws2_32` 的 connect 看不到）"。**
**⇒ 只 hook `connect`/`sendto` 会**完全错过**大厅流量。**

### 3. ★★★ `_K32` 硬编码 RVA 是**健壮性补丁**（导出转发 + 枚举落空）

### 4. ★★★ 共享内存 5 项曾被遗漏，导致"跳过(不支持)"

### 5. ★★ `REC=72` 记录了**调用点 48 字节机器码**（可事后反汇编）

---

## 八、下一步

- `nt10.py` 的函数实现（`build_tramp` / `build_tas_image` / `compat_patch_*` / `snapshot_client` / `playerstate_probe_thread`）
- `fake_auth_tls.py` / `stun_local.py` / `force_display_name.py`
- `bundle\` 五个证书文件
- `payload\` 四个插件 PE + 四个 loader 二进制
