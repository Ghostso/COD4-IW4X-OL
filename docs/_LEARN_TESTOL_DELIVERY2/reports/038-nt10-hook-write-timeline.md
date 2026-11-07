# 学习报告 038（重开）— `nt10.py` hook 安装执行与 timeline 线程

**学习范围**：第 1999–2118 行（五路目标解析收尾 + hook 写入 + timeline + 迟到 hook 反推）
**性质**：全实测
**★★★ 本报告收录**hook 写入的完整字节序列**与**从 OpenFileMappingW 反推 TenProxy 基址**

---

## 一、★★★★★ 五路目标解析的**完整优先级链**（第 1999–2012 行）

```python
if nm in _K32:                          # ① kernel32 硬编码 RVA
    ...
elif nm in rvas and ws2:                # ② ws2_32 导出
    tgt = ws2 + rvas[nm]
elif nm in wht_rvas and wht_base:       # ③ winhttp 导出
    tgt = wht_base + wht_rvas[nm]
elif nm in k32_rvas and k32_base:       # ④ kernel32 导出
    tgt = k32_base + k32_rvas[nm]
elif nm in u32_rvas and u32_base:       # ⑤ user32 导出
    tgt = u32_base + u32_rvas[nm]
else:
    log("-- %s 跳过(无导出/无基址)" % nm)
    continue
```

### ★★★★★ 完整的五级优先级

| # | 来源 | 条件 |
|---|---|---|
| **①** | ★ **`_K32` 硬编码** | `nm in _K32` |
| **②** | `ws2_32` 导出 | `nm in rvas and ws2` |
| **③** | `winhttp` 导出 | `nm in wht_rvas and wht_base` |
| **④** | `kernel32` 导出 | `nm in k32_rvas and k32_base` |
| **⑤** | `user32` 导出 | `nm in u32_rvas and u32_base` |

★★★ **⇒ `_K32` 排**第一**（优先于 ws2_32 导出）——**
**因为 `ws2_32` 的导出是**转发**，RVA 可能指向跳转桩而不是真函数。**

---

## 二、★★★★★ hook 写入的**完整字节序列**（第 2013–2028 行）

```python
cave = page + next_slot * 0x400                      # ① 代码洞地址
cnt = page + SLOT * (next_slot + 1)                  # ② 计数器地址
orig = rpm(h, tgt, 16)                               # ③ 读原 16 字节
stolen, n = pick_stolen(orig, tgt)                   # ④ 挑选被覆盖指令
if not stolen:
    log("-- %s 偷指令失败 (%s)" % (nm, orig[:5].hex(" ")))
    continue
code = build_tramp(cnt, cnt + 4, stolen, tgt + n, cave, str_off, mode)   # ⑤ 构建跳板
if not wpm(h, cave, code) or not wpm(h, tgt, b"\xE9" +
                                     struct.pack("<i", cave - (tgt + 5)) +
                                     b"\x90" * (n - 5)):                 # ⑥ 写入
    log("-- %s 写 hook 失败" % nm)
    continue
log("-- hook %-24s @0x%08X 偷%d字节" % (nm, tgt, n))
slots.append((nm, cnt, wide, mode))
next_slot += 1
```

### ★★★★★ 六个步骤的精确分析

| # | 步骤 | 计算 |
|---|---|---|
| **①** | 代码洞地址 | `page + next_slot * 0x400`（★ 每个 hook **1 KB**） |
| **②** | 计数器地址 | `page + SLOT * (next_slot + 1)`（★ 每个 **128 KB** 一段） |
| **③** | 读原字节 | `rpm(h, tgt, 16)` |
| **④** | 挑选 | `pick_stolen`（拒绝跳转，≥5 字节） |
| **⑤** | 构建跳板 | `build_tramp(cnt, cnt+4, stolen, tgt+n, cave, str_off, mode)` |
| **⑥** | 写入 | **两处**：代码洞 + 目标处 |

### ★★★ 内存布局

```
page (VirtualAllocEx 的基址)
  +0x00000  代码洞 0（1 KB）
  +0x00400  代码洞 1
  +0x00800  代码洞 2
  ...
  +0x20000  ★ SLOT = 128 KB 边界
  +0x20000  计数器 0（4 字节）
  +0x20004  计数器 0 的环形缓冲起始（cnt + 4）
  +0x40000  计数器 1
  ...
```

★★★ **⇒ 两部分布局：**
```
前 128 KB（0x20000）：代码洞区，每个 1 KB
之后每 128 KB：一个计数器槽（4 字节计数器 + 73,732 字节环形缓冲）
```

★ **⇒ 而 `build_tramp` 的第 2 个参数是 `cnt + 4`（`arr_addr`）——**
**⇒ 环形缓冲紧跟在 4 字节计数器之后。**

### ★★★★ hook 写入的**精确字节**（第 2021–2023 行）

```python
wpm(h, tgt, b"\xE9" +
    struct.pack("<i", cave - (tgt + 5)) +
    b"\x90" * (n - 5))
```

★★★ **⇒ 完整序列：**
```
偏移 0:  E9                  JMP rel32
偏移 1-4: <cave - (tgt+5)>   相对偏移
偏移 5..n-1: 90 × (n-5)      ★ NOP 填充剩余字节
```

★★★ **⇒ 例如：若 `n = 7`（偷了 7 字节），则：**
```
E9 xx xx xx xx 90 90
```

★ **⇒ `n - 5` 个 NOP 补齐到 `n` 字节（保证指令边界对齐）。**

---

## 三、★★★★ `timeline` 线程（第 2032–2073 行）

### 3.1 ★★★ 每 0.4 秒的完整循环

```python
def timeline():
    last = {}
    while not stop.is_set():
        for i, (nm, cnt, wide, mode) in enumerate(slots):
            d = rpm(h, cnt, BUF_LEN)                 # ★ 读整个缓冲（73,732 字节）
            if len(d) < 4:
                continue
            try:
                with open(snap + ".slot%d" % i, "wb") as sf:
                    sf.write(d)                      # ★ 落盘快照
            except Exception:
                pass
            v = struct.unpack_from("<I", d, 0)[0]    # ★ 读计数器
            if v != last.get(nm, 0):
                ...
                last[nm] = v
        time.sleep(0.4)
```

★★★ **⇒ 四个动作：**
```
① 读 73,732 字节的完整缓冲
② ★ 落盘到 `<snap>.slot<N>`（离线分析用）
③ 读计数器（前 4 字节）
④ 有变化就处理
```

★ **⇒ `snap` 来自 `os.path.splitext(os.path.abspath(a.out))[0]`（报告 032）。**

★★ **⇒ 每个 hook 一个 `.slotN` 文件 ⇒ **完整的命中记录可离线分析**。**

### 3.2 ★★★★★ 字符串类 hook 的**新串提取**（第 2047–2058 行）

```python
# 字符串类 hook: 把域名/映射名整串捞出来, 这是"它到底连谁"的直接答案
if nm in STR_HOOKS and v > last.get(nm, 0):
    strs = []
    for k in range(max(0, v - 6), min(v, RING)):     # ★ 最近 6 条
        rec = 4 + k * REC
        if rec + REC > len(d):
            break
        s = follow_str(h, d, rec, wide)
        if s and s not in strs:
            strs.append(s)
    if strs:
        extra = "  新串=%s" % strs[-4:]              # ★ 只显示最后 4 个
```

★★★ **⇒ 三个要点：**
```
① 只处理 `STR_HOOKS`（9 个）
② ★ 只看**最近 6 条**记录（`v-6` 到 `v`）
③ ★ 只显示**最后 4 个**不同的串
```

★★ **⇒ 注释（第 2047 行，逐字）：**
> **"它到底连谁"的直接答案**

### 3.3 ★★★ socket 类 hook 的**目标地址提取**（第 2059–2067 行）

```python
# connect/sendto/bind: 直接从记录内容区解 IP:端口(入口瞬间数据)
if nm in SOCK_APIS and v > last.get(nm, 0):
    for k in range(max(0, v - 4), min(v, RING)):     # ★ 最近 4 条
        rec = 4 + k * REC
        if rec + REC > len(d):
            break
        sa = describe_sockaddr(d, rec)
        if sa and sa not in extra:
            extra += "  目标=%s" % sa
```

★★ **⇒ 只处理 `SOCK_APIS`（5 个），最近 **4 条**。**

★ **⇒ 注释：**"直接从记录内容区解 IP:端口(**入口瞬间数据**)" ——**
**⇒ 印证了报告 022 的"当场抄 vs 事后读"教训。**

---

## 四、★★★★★ 迟到 hook 的**基址反推**（第 2075–2118 行）

### 4.1 ★★★ docstring（第 2076–2079 行，逐字）

```python
"""迟到 hook: 从 OpenFileMappingW 的命中里认出 CTclsProxy 的调用者,
反推 TenProxy 基址 -> 挂它的取值函数 -> 打"恒成功"补丁。
必须晚做: TenProxy.dll 是 t≈5s 才加载的。
注意: 这会往 TenProxy 的代码里写 JMP, 默认关闭(见 use_late)。"""
```

★★★ **⇒ 三步：**
```
① 从 OpenFileMappingW 的命中里认出 **CTclsProxy 的调用者**
② **反推 TenProxy 基址**
③ 挂它的取值函数 → 打"恒成功"补丁
```

### 4.2 ★★★★★ 反推逻辑（第 2085–2116 行）

```python
base, callers = 0, []
t_w = time.time()
while time.time() - t_w < 15:                        # ★ 最多等 15 秒
    d = rpm(h, ocnt, BUF_LEN)
    if len(d) >= 4:
        c = struct.unpack_from("<I", d, 0)[0]
        for k in range(min(c, RING)):
            rec = 4 + k * REC
            if rec + REC > len(d):
                break
            nm16 = d[rec + 8:rec + 24].decode("utf-16le", "replace")
            # 注意: 每条只抄 16 字节内容, UTF-16LE 的
            # "TCLS_SHAREDMEMEMORY<pid>" 只够到 "TCLS_SHA" —— 别拿全名去比
            if nm16.upper().startswith("TCLS_"):     # ★ 前缀匹配
                cl = struct.unpack_from("<I", d, rec)[0]   # ★ 调用者地址
                if cl not in callers:
                    callers.append(cl)
    for cl in callers:
        cand = cl - 0x61E8                           # ★★★ 关键偏移
        if rpm(h, cand, 2) == b"MZ":                 # ★ 验证
            base = cand
            break
    if base:
        break
    time.sleep(0.5)
```

### ★★★★★ 三个关键点

| # | 要点 | 值 |
|---|---|---|
| 1 | ★★★ **内容只有 16 字节** | UTF-16LE 的 `"TCLS_SHAREDMEMEMORY<pid>"` 只够到 **`"TCLS_SHA"`** ⇒ **别拿全名比** |
| 2 | 匹配方式 | **`startswith("TCLS_")`** |
| 3 | ★★★ **反推公式** | **`TenProxy 基址 = 调用者地址 - 0x61E8`** |

★★★ **⇒ 第 1 条是**重要的实测约束**：**
```
记录内容区只有 16 字节（REC 的布局：+8 到 +24）
        ↓
UTF-16LE 的 "TCLS_SHAREDMEMEMORY<pid>" 每字符 2 字节
        ↓
16 字节 = 8 个 UTF-16 字符
        ↓
★ 只够 "TCLS_SHA"（8 字符）
        ↓
★★★ ⇒ **不能拿全名比较**
```

★★★ **⇒ 第 3 条是**关键的逆向成果**：**
```
CTclsProxy 里的某个函数地址 - 0x61E8 = TenProxy.dll 的基址
        ↓
★ 即：该函数在 TenProxy.dll 中的 **RVA = 0x61E8**
```

★ **⇒ 验证方式：`rpm(h, cand, 2) == b"MZ"`（检查 PE 头）。**

### 4.3 ★★ 失败日志（第 2110–2113 行）

```python
if not base:
    log("-- 迟到 hook: 15s 内没反推出 TenProxy 基址 (TCLS 调用者=%s)"
        % [hex(x) for x in callers[:4]])
    return
```

★★ **⇒ 15 秒内没找到 ⇒ 打印前 4 个调用者地址后返回。**

### 4.4 ★★★ 成功后的转储（第 2118–2128 行）

```python
# 运行时转储 TenProxy 前 0x40000 字节 —— thunk 区(磁盘上是 0)与取值函数体
# (0x6BD0/0x7CA0/0x7EA0/0x8250/0x8510)都在这段里, 用来消除映射猜测。
try:
    tb = bytearray()
    for _o in range(0, 0x40000, 0x1000):
        chunk = rpm(h, base + _o, 0x1000)
        if len(chunk) < 0x1000:
            break
        tb += chunk
    tb = bytes(tb)
```

★★★★★ **⇒ 五个精确的 RVA：**
```
0x6BD0   ← pad LoginInfo（报告 023）
0x7CA0   ← vtable 0x20（2 参 DWORD）
0x7EA0   ← pLen 路径
0x8250   ← vtable[12]（4 参带序号，读 tag7/tag8）
0x8510   ← vtable[14]（要求 tag7 的 len==4）
```

★★★ **⇒ 且注释指出：**"thunk 区（磁盘上是 0）"** ——**
**⇒ 这解释了为什么**磁盘上的 TenProxy 无法静态分析**（thunk 区被清零）。**

---

## 五、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★ 五路优先级 | `_K32` > ws2_32 > winhttp > kernel32 > user32 |
| 2 | ★ 代码洞布局 | `page + next_slot * 0x400`（每个 **1 KB**） |
| 3 | 计数器布局 | `page + SLOT * (next_slot+1)`（每个 **128 KB**） |
| 4 | ★★★ hook 字节 | **`E9 <rel32> 90×(n-5)`** |
| 5 | timeline 间隔 | **0.4 秒** |
| 6 | 缓冲大小 | **`BUF_LEN` = 73,732** |
| 7 | ★★ 落盘 | `<snap>.slot<N>`（每个 hook 一个） |
| 8 | ★ 字符串 hook | 最近 **6 条**，显示最后 **4 个**不同串 |
| 9 | socket hook | 最近 **4 条** |
| 10 | ★★★★★ **16 字节约束** | UTF-16LE 只够 **`"TCLS_SHA"`**（8 字符）⇒ **不能比全名** |
| 11 | ★★★ **反推公式** | **`TenProxy 基址 = 调用者 - 0x61E8`** |
| 12 | 反推验证 | `rpm(cand, 2) == b"MZ"` |
| 13 | 反推等待 | **15 秒**，每 **0.5 秒** |
| 14 | ★★★ 五个 RVA | `0x6BD0` / `0x7CA0` / `0x7EA0` / `0x8250` / `0x8510` |
| 15 | ★★★ thunk 区 | **磁盘上是 0** ⇒ 必须运行时转储 |

---

## 六、结论

### 1. ★★★★★ **`TenProxy 基址 = 调用者 - 0x61E8`** 是一个精确的逆向成果

★ **⇒ 即 `CTclsProxy` 调用的那个函数在 TenProxy.dll 里的 RVA 是 **`0x61E8`**。**

### 2. ★★★★★ **16 字节内容区装不下完整共享内存名**（只够 `TCLS_SHA`）

★ **⇒ 必须用 `startswith("TCLS_")` 而不是全名比较。**

### 3. ★★★ **thunk 区在磁盘上是 0** ⇒ TenProxy 必须运行时转储

### 4. ★★★ 五路目标解析的优先级把 `_K32` 放第一（绕开 ws2_32 转发）

### 5. ★★ hook 字节是 `E9 rel32` + NOP 填充到 `n` 字节

### 6. ★★ 每个 hook 的完整命中缓冲都落盘（`.slotN`），可离线分析

---

## 七、下一步

- `nt10.py` 最后一段（第 2128 行起）—— 迟到 hook 的补丁与主循环
- `fake_auth_tls.py` / `stun_local.py` / `force_display_name.py`
- `bundle\` 五个证书文件
- `payload\` 四个插件 PE + 四个 loader 二进制
