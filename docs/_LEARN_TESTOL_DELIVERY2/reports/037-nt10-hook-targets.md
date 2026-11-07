# 学习报告 037（重开）— `nt10.py` hook 安装主循环（模块等待与目标解析）

**学习范围**：第 1870–1999 行（模块等待 + 导出解析 + `@` 直接地址 + kernel32 硬编码）
**性质**：全实测
**★★★ 本报告收录**三重模块等待条件**、**四条目标解析路径**

---

## 一、★★★★ `need_more` 的**三重等待条件**（第 1872–1888 行）

```python
# 直到【ws2_32 出现】或超时。上一轮就是早期只有 11 个 + 不再重试,
# 导致 ws2_32=0, connect/sendto/getaddrinfo/GetAddrInfoW/gethostbyname 全部跳过。
need_sock = any(nm in apis and nm not in _K32 and nm not in U32_APIS
                and not nm.startswith("@") for nm in apis)
need_whtt = any(nm in WHTTP_APIS for nm in apis)
early_n = len(ml)

def has_ws2(lst):
    return any(n.lower().startswith("ws2_32") for n, b, s in lst)

def need_more(lst):
    if not lst:
        return True
    if need_sock and not has_ws2(lst):
        return True
    if need_whtt and not any(n.lower().startswith("winhttp") for n, b, s in lst):
        return True
    return not any(n.lower().startswith("kernel32") for n, b, s in lst)
```

### ★★★★★ 三个精确的失败后果（第 1871 行）

```python
# 导致 ws2_32=0, connect/sendto/getaddrinfo/GetAddrInfoW/gethostbyname 全部跳过。
```

★★★ **⇒ 五个 API 会**全部跳过**：**
```
connect / sendto / getaddrinfo / GetAddrInfoW / gethostbyname
```

### ★★★ `need_more` 的完整判定逻辑

```python
if not lst:                    → True   （列表为空）
if need_sock and not has_ws2   → True   （需要 socket 但没 ws2_32）
if need_whtt and not winhttp   → True   （需要 winhttp 但没加载）
return not kernel32            → True   （★ 连 kernel32 都没有）
```

★★★ **⇒ 四个等待条件（按优先级）：**
```
① 列表为空
② 需要 socket 但无 ws2_32
③ 需要 WinHttp 但无 winhttp
④ ★ 无 kernel32（最基本的）
```

★ **⇒ `need_sock` 的判定排除了三类：**
```python
nm not in _K32        ← kernel32 硬编码那 5 个
nm not in U32_APIS    ← user32 那 6 个
not nm.startswith("@") ← 直接地址
```
**⇒ 只有**真正需要 ws2_32 的**才算 `need_sock`。**

---

## 二、★★★ 有界等待（第 1890–1911 行）

```python
t_ml, tries = time.time(), 0
while need_more(ml) and time.time() - t_ml < 60.0:      # ★ 最多 60 秒
    try:
        ml2 = mods_any(pid, h)[0]
    except Exception:
        ml2 = []
    if not ml2:
        try:
            ml2 = mods_peb(h)
        except Exception:
            ml2 = []
    if ml2 and len(ml2) >= len(ml):                     # ★ 只接受"更多"的结果
        ml = ml2
    tries += 1
    if tries % 10 == 0:
        log("  ...等 ws2_32 出现: 已重试 %d 次, 当前 %d 个模块, ws2_32=%s"
            % (tries, len(ml), "有" if has_ws2(ml) else "无"))
    time.sleep(0.3)
log("模块数=%d (早期枚举 %d, ws2_32 %s)"
    % (len(ml), early_n, "有" if has_ws2(ml) else "!! 仍然没有"))
if not ml:
    log("!! 模块列表为空 —— 典型症状: 不是管理员窗口。请用【管理员 PowerShell】重跑。")
```

★★★ **⇒ 五个要点：**
```
① 最多等 **60 秒**，每 **0.3 秒**重试
② 先试 mods_any，失败/空则试 mods_peb
③ ★ 只接受 len 更大的结果（避免退化）
④ 每 10 次打一次进度
⑤ ★★★ 空列表 ⇒ **"不是管理员窗口"** ⇒ 提示用管理员 PowerShell
```

★★ **⇒ 第 ⑤ 条是**重要的诊断**：空模块列表的典型原因是**权限不足**。**

---

## 三、★★★ 导出解析（第 1912–1925 行）

```python
sysdir = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "SysWOW64")
rvas = export_rva(os.path.join(sysdir, "ws2_32.dll"), apis)
ws2 = next((b for n, b, s in ml if n.lower().startswith("ws2_32")), 0)
log("ws2_32=0x%08X 导出=%s" % (ws2, {k: hex(v) for k, v in rvas.items()}))
```

★★★ **⇒ 两个要点：**
```
① 从 **SysWOW64** 读 ws2_32.dll（★ 32 位版本）
② 用 export_rva 解析导出表拿 RVA
```

★★★ **⇒ `SysWOW64` 是**关键的**：**
```
64 位 Windows 上：
  C:\Windows\System32  →  64 位 DLL
  C:\Windows\SysWOW64  →  ★ 32 位 DLL
        ↓
CODOL 是 32 位 ⇒ 必须读 **SysWOW64**
```

★ **⇒ 若读错目录，RVA 会**完全不同**（64 位 ws2_32 的导出偏移与 32 位不同）。**

### ★★ WinHttp 的独立处理（第 1916–1925 行）

```python
# WinHttp(大厅 HTTP 层): WINHTTP.dll 导出是真函数(不走转发), 用导出表+基址定位
need_whtt = any(nm in WHTTP_APIS for nm in apis)
wht_base, wht_rvas = 0, {}
if need_whtt:
    wht_rvas = export_rva(os.path.join(sysdir, "winhttp.dll"),
                          [nm for nm in apis if nm in WHTTP_APIS])
    wht_base = next((b for n, b, s in ml if n.lower().startswith("winhttp")), 0)
```

★★★ **⇒ 注释（第 1916 行，逐字）：**
> **WinHttp(大厅 HTTP 层): WINHTTP.dll 导出是真函数(不走转发), 用导出表+基址定位**

★★ **⇒ 对比 `_K32` 的注释："这几个在 kernel32 里是**真函数(不是转发)**" ——**
**⇒ 说明 `ws2_32` 的导出**是转发**（所以要用 `_K32` 硬编码），**
**而 `winhttp` 和 `kernel32` 的导出**是真函数**。**

★★★ **⇒ 三层 API 的定位策略：**

| 模块 | 导出性质 | 定位方式 |
|---|---|---|
| **`ws2_32`** | ★ **转发** | 导出表（RVA 有效，但函数会转到 kernel32） |
| **`winhttp`** | **真函数** | 导出表 + 基址 |
| **`kernel32`** | **真函数** | ★ `_K32` 硬编码 RVA |

---

## 四、★★★ 代码洞的二次申请（第 1926–1932 行）

```python
if not page:
    page = k32.VirtualAllocEx(h, None, SLOT * (len(apis) + 8),
                              MEM_COMMIT_RESERVE, PAGE_EXECUTE_READWRITE)
if not page:
    log("VirtualAllocEx 失败 err=%d" % ctypes.get_last_error())
    return
log("代码洞 0x%08X" % page)
```

★★★ **⇒ 二次申请（第 1820 行已申请过一次）——**如果第一次失败，这里再试一次**。**

★ **⇒ 但注意：第一次在 t≈0 附近，第二次在 `a.delay`（2.5 秒）之后 ⇒**
**★★★ 第二次很可能**失败**（因为 ACE 在 t≈2.5s 起拒绝）。**

---

## 五、★★★★★ 四条目标解析路径（第 1951–1999 行）

### 5.1 ★★★ 路径 1：`@模块名:RVA`（第 1953–1973 行）

```python
if nm.startswith("@"):
    spec2 = nm[1:]
    if ":" in spec2 and not spec2.startswith("0x"):
        mname, _, mrva = spec2.partition(":")
        mb, t_w = 0, time.time()
        while time.time() - t_w < 30:               # ★ 最多等 30 秒
            ml2 = mods_peb(h) or ml
            mb = next((b for n, b, s in ml2
                       if n.lower() == mname.lower()
                       or n.lower().startswith(mname.lower())), 0)
            if mb:
                break
            time.sleep(0.3)
        if not mb:
            log("-- %s 30 秒内没看到模块 %s" % (nm, mname))
            continue
        known_bases[mname.lower()] = mb
        tgt = mb + int(mrva, 0)
        # 用 "tp+0xRVA" 命名, 这样导出段会按 tag/dst/pLen 解释参数
        nm = "tp+%s" % mrva if mname.lower().startswith("tenproxy") else nm
        log("-- %s -> %s 基址 0x%08X + %s = 0x%08X" % (nm, mname, mb, mrva, tgt))
```

★★★ **⇒ 三个要点：**
```
① 模块名匹配支持 **精确 或 前缀**（`==` 或 `startswith`）
② 最多等 **30 秒**
③ ★★ tenproxy 的 hook 命名为 **`tp+0xRVA`** —— 这样"导出段会按 tag/dst/pLen 解释参数"
```

★★★ **⇒ 第 ③ 条揭示了**命名的语义作用**：**
```
nm = "tp+0x7CAF"  ⇒  导出段识别为 tenproxy 的函数
                  ⇒  ★ 按 **tag / dst / pLen** 解释参数（decl 模式）
```

★ **⇒ 与报告 022 的 `mode="decl"` 直接呼应。**

### 5.2 ★★★ 路径 2：`@绝对地址`（第 1974–1975 行）

```python
else:
    tgt = int(spec2, 0)
```

★ **⇒ 直接用绝对地址（无模块查找）。**

### 5.3 ★★★ 两条路径的共同校验（第 1976–1985 行）

```python
t_w = time.time()
ok = False
while time.time() - t_w < 30:
    if rpm(h, tgt, 3) == b"\x55\x8b\xec":        # ★ push ebp; mov ebp, esp
        ok = True
        break
    time.sleep(0.3)
if not ok:
    log("-- %s 30 秒内没等到 55 8b ec, 跳过: %s" % (nm, rpm(h, tgt, 5).hex(" ")))
    continue
```

★★★★ **⇒ **极其严谨的校验**：**
```
每 0.3 秒检查目标地址的前 3 字节是否 == `55 8b ec`
        ↓
（`push ebp; mov ebp, esp` = ★ 标准的函数序言）
        ↓
最多等 **30 秒**
        ↓
★ 等不到 ⇒ **跳过这个 hook**
```

★★★ **⇒ 为什么需要等：**因为 `.tp3` 段要**运行时解壳**，解壳前目标处不是 `55 8b ec`。**

★ **⇒ 失败时打印前 5 字节（`rpm(h, tgt, 5).hex(" ")`）—— 便于诊断。**

### 5.4 ★★★ 路径 3：`TRAMP_APIS` 表（第 1986–1990 行）

```python
else:
    if nm not in TRAMP_APIS:
        log("-- %s 跳过(不支持)" % nm)
        continue
    str_off, wide, mode = TRAMP_APIS[nm]
```

★★ **⇒ 从 `TRAMP_APIS` 取 `(参数偏移, 宽字符, 模式)` 三元组。**

### 5.5 ★★★★★ 路径 4：`_K32` 硬编码（第 1991–1999 行）

```python
if nm in _K32:
    # 本机 RVA + kernel32 基址 (E:\1\nt8.py 的路子, 不依赖 ws2_32 导出扫描)
    mb = next((b for n, b, s in ml if n.lower().startswith("kernel32")), 0)
    if not mb:
        log("-- %s 找不到 kernel32 基址" % nm)
        continue
    known_bases["kernel32.dll"] = mb
    tgt = mb + _K32[nm]
    log("-- %s 本机 RVA 0x%X -> 0x%08X (kernel32 基址 0x%08X)"
```

★★★ **⇒ 注释（逐字）：**"本机 RVA + kernel32 基址 (`E:\1\nt8.py` 的路子,
**不依赖 ws2_32 导出扫描**)"**

★★ **⇒ 这是**绕开"ws2_32 导出是转发"问题**的方案。**

★ **⇒ 代价：**RVA 是 Windows 版本相关的**（换版本可能失效）。**

---

## 六、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★ 无 ws2_32 的后果 | **5 个 API 全跳过**（connect/sendto/getaddrinfo/GetAddrInfoW/gethostbyname） |
| 2 | `need_more` 四条件 | 空 / 无 ws2_32 / 无 winhttp / **无 kernel32** |
| 3 | `need_sock` 排除 | `_K32` + `U32_APIS` + `@` |
| 4 | 模块等待 | **60 秒**，每 **0.3 秒** |
| 5 | ★★ 只接受更大结果 | `len(ml2) >= len(ml)` |
| 6 | ★★★ 空列表诊断 | **"不是管理员窗口"** |
| 7 | ★★★ `SysWOW64` | **32 位 DLL 所在目录**（System32 是 64 位） |
| 8 | ★★★ 三层定位策略 | `ws2_32`（转发→导出表）/ `winhttp`（真函数→导出表）/ `kernel32`（**`_K32` 硬编码**） |
| 9 | ★ 代码洞二次申请 | 第一次 t≈0，第二次 2.5s 后（★ 很可能失败） |
| 10 | ★★★ 四条解析路径 | `@模块:RVA` / `@绝对地址` / `TRAMP_APIS` / **`_K32`** |
| 11 | ★★ `@` 路径等待 | **30 秒** |
| 12 | ★★★ tenproxy 命名 | **`tp+0xRVA`** ⇒ 按 **tag/dst/pLen** 解释 |
| 13 | ★★★★★ **函数序言校验** | **`55 8b ec`**（`push ebp; mov ebp, esp`），等 **30 秒** |
| 14 | 校验失败 | 打印前 5 字节后跳过 |

---

## 七、结论

### 1. ★★★★★ **三层 API 定位策略**是核心架构

```
ws2_32   导出是**转发**  →  用导出表（但要防"转发导致的 RVA 失效"）
winhttp  导出是**真函数** →  导出表 + 基址
kernel32 导出是**真函数** →  ★ _K32 硬编码（绕开 ws2_32 转发问题）
```

### 2. ★★★★★ **`55 8b ec` 函数序言校验**是"等解壳"的判据

★★ **⇒ 每 0.3 秒检查一次，最多 30 秒 ⇒ 等不到就跳过。**

### 3. ★★★ **`SysWOW64` 是 32 位 DLL 的目录**（不是 System32）

### 4. ★★★ **无 ws2_32 ⇒ 5 个关键 API 全跳过**（上一轮的失败）

### 5. ★★ 空模块列表的诊断是"不是管理员窗口"

### 6. ★★ `tp+0xRVA` 的命名让导出段按 `decl` 模式解释参数

---

## 八、下一步

- `nt10.py` 最后一段（第 1999 行起）—— hook 安装与主循环
- `fake_auth_tls.py` / `stun_local.py` / `force_display_name.py`
- `bundle\` 五个证书文件
- `payload\` 四个插件 PE + 四个 loader 二进制
