# 学习报告 036（重开）— `nt10.py` TAS 注入、三个线程、代码洞与迟到 hook

**学习范围**：第 1751–1870 行（TAS 注入 / 大厅全局 / 线程编排 / 代码洞 / 迟到 hook / patcher）
**性质**：全实测
**★★★ 本报告收录**TAS 共享内存注入**、**线程编排的完整顺序**、**ACE 拒绝 VirtualAllocEx 的时刻**

---

## 一、★★★★★ TAS 注入（第 1750–1775 行）

### 1.1 ★★★ 规格来源与禁用开关（第 1751–1761 行）

```python
tf = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tas_spec.txt")
if os.path.exists(tf):
    try:
        spec = open(tf, encoding="utf-8").read().strip()
    except Exception:
        spec = ""
if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "tas_off.flag")):
    if spec:
        log("★ 跳过 TAS 注入(tas_off.flag 存在) —— 隔离实验用, 原规格 %r" % spec)
    spec = ""
```

★★★ **⇒ 两个文件：**
```
tas_spec.txt    规格（"host:port:name"）
tas_off.flag    禁用开关（★ 隔离实验用）
```

★ **⇒ `tas_off.flag` 存在时**清空 spec** ⇒ 跳过注入。**

### 1.2 ★★★ 规格解析（第 1762–1765 行）

```python
if spec:
    try:
        q = (spec.split(":") + ["", "", ""])[:3]
        host, port, name = q[0] or "127.0.0.1", int(q[1] or 3074), q[2] or "CODOL"
```

★★★ **⇒ 格式：`host:port:name`，默认 `127.0.0.1:3074:CODOL`。**

★ **⇒ `(spec.split(":") + ["", "", ""])[:3]` —— 补齐到 3 项后截取（容错）。**

### 1.3 ★★★★★ 共享内存注入（第 1766–1773 行）

```python
img = build_tas_image(host, port, name)                       # ① 构建 1 MB 镜像
hn = "TCLS_SHAREDMEMEMORY%d" % pid                            # ② 命名
hmap = k32.CreateFileMappingW(wintypes.HANDLE(-1), None, 0x04, 0, len(img), hn)
vp = k32.MapViewOfFile(hmap, 0x000F001F, 0, 0, len(img)) if hmap else None
if vp:
    ctypes.memmove(vp, img, len(img))                          # ③ 拷贝
log("注入 %s host=%s port=%d name=%s -> %s" % (hn, host, port, name,
                                              "成功" if vp else "失败"))
```

★★★ **⇒ 三步：**
```
① build_tas_image(host, port, name)     → 1,081,348 字节镜像
② CreateFileMappingW(HANDLE(-1), ..., 0x04, 0, len, "TCLS_SHAREDMEMEMORY<pid>")
③ MapViewOfFile(hmap, 0x000F001F, ...) → memmove
```

### ★★★★★ 关键 API 参数

| 参数 | 值 | 含义 |
|---|---|---|
| `hFile` | **`HANDLE(-1)`**（`INVALID_HANDLE_VALUE`） | ★ 内存映射（不是文件） |
| `flProtect` | **`0x04`** | `PAGE_READWRITE` |
| `dwMaximumSizeHigh` | `0` | |
| `dwMaximumSizeLow` | `len(img)` | 1,081,348 |
| `lpName` | **`TCLS_SHAREDMEMEMORY<pid>`** | ★★★ 命名共享内存 |
| `MapViewOfFile` `dwDesiredAccess` | **`0x000F001F`** | ★★★ `FILE_MAP_ALL_ACCESS` |

★★★ **⇒ 这正是记忆里"`OpenFileMapping TCLS_SHAREDMEMEMORY<pid>` 是全流程的钥匙"**的直接实现**。**

★★ **⇒ 注意：**这是**创建**（不是打开）—— `nt10.py` 主动创建这个共享内存，供客户端读取。**

★ **⇒ `0x000F001F` = `FILE_MAP_WRITE(0x2) | FILE_MAP_READ(0x4) | FILE_MAP_ALL_ACCESS(0xF001F)`。**

---

## 二、★★★★ 大厅全局的目标（第 1777–1794 行）

```python
# 大厅主机/端口全局的目标(另一位开发者提过填这几个全局可消除"无法连接大厅服务")
# 规格来自同目录 lobby_spec.txt, 形如 "127.0.0.1:3074:3074"
# ★ 2026-10-02: 改版后默认【不写这些全局】—— 三方"能进大厅"的实现完全不碰它们,
#   只靠 hosts + dwauth.ini + 4 个内存补丁。要写的话给 run_all 加 --poke。
LOBBY_HOST, LOBBY_PORT, LOBBY_HTTPS_PORT = "127.0.0.1", 3074, 3074
```

### ★★★★★ 一段**重要的设计决策记录**

```python
# ★ 2026-10-02: 改版后默认【不写这些全局】—— 三方"能进大厅"的实现完全不碰它们,
#   只靠 hosts + dwauth.ini + 4 个内存补丁。
```

★★★ **⇒ **"能进大厅"的充分条件**（三方实现）：**
```
① hosts
② dwauth.ini
③ ★★★ 4 个内存补丁
```

★★ **⇒ **不需要**写大厅全局！**

★ **⇒ 这是一个**重要的简化结论**（避免了一个可能的错误方向）。**

★★ **⇒ `lobby_spec.txt` 存在时才覆盖默认值（`127.0.0.1:3074:3074`）。**

---

## 三、★★★★★ 线程编排的**完整顺序**（第 1796–1860 行）

### 3.1 ★★★ 四个 daemon 线程（按启动顺序）

```python
# ① 兼容补丁
threading.Thread(target=compat_patch_thread, args=(h, log), daemon=True).start()
log("-- [兼容补丁] 后台线程已启动 (最多等 %.0fs 解壳)" % COMPAT_DEADLINE)

# ② 会话密钥快照
threading.Thread(target=secrets_snapshot_thread, args=(h, log, pid), daemon=True).start()

# ③ playerstate 探针（可选）
if getattr(a, 'ps_probe', False):
    ...
    threading.Thread(target=playerstate_probe_thread, args=(h, log, pid), daemon=True).start()

# ④ 弹窗监听
threading.Thread(target=watch_dialogs, args=(pid, t_launch, log, stop), daemon=True).start()

# ⑤ patcher（JNE 监控）
threading.Thread(target=patcher, daemon=True).start()
```

★★★ **⇒ **五个**线程（不是四个）：**

| # | 线程 | 作用 | 条件 |
|---|---|---|---|
| **1** | `compat_patch_thread` | 4 个兼容补丁（等解壳，最多 90 秒） | 总是 |
| **2** | `secrets_snapshot_thread` | 密钥快照 → `secrets.txt` | 总是 |
| **3** | `playerstate_probe_thread` | 出生点探针 | **`--ps-probe`** |
| **4** | `watch_dialogs` | 弹窗监听 | 总是 |
| **5** | `patcher` | JNE 字节监控 | 总是 |

★ **⇒ 全部 `daemon=True`（主线程退出时自动结束）。**

### 3.2 ★★★ tick_hz 的二次读取（第 1802–1812 行）

```python
if getattr(a, 'ps_probe', False):
    _tick = 128.0
    try:
        _tf = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tick_hz.txt')
        _tick = float(io.open(_tf).read().strip()) if os.path.exists(_tf) else 128.0
    except Exception:
        _tick = 128.0
```

★★ **⇒ 这里**又读了一次 `tick_hz.txt`**（与模块级的 `_probe_tick_hz()` 重复）。**

★ **⇒ 可能是**历史遗留的重复代码**。**

---

## 四、★★★★★ 代码洞申请（第 1815–1823 行）

```python
# 早枚举(必须早, 晚了被 ACE 封)
ml, src = mods_any(pid, h)
log("早期模块枚举: %d 个 (来源 %s)" % (len(ml), src))
# 代码洞也在此刻就申请: ACE 之后会拒绝 VirtualAllocEx(实测 t≈2.5s 起 err=5)
# +8 是给"迟到 hook"(tp 的 3 个取值函数)留代码洞 + 计数器槽
page = k32.VirtualAllocEx(h, None, SLOT * (len(apis) + 8),
                          MEM_COMMIT_RESERVE, PAGE_EXECUTE_READWRITE)
log("早期申请代码洞 0x%08X (err=%d)"
    % (page or 0, 0 if page else ctypes.get_last_error()))
```

### ★★★★★ 三条精确数据

| # | 信息 | 值 |
|---|---|---|
| 1 | **模块枚举时机** | **必须早**（晚了被 ACE 封） |
| 2 | ★★★ **`VirtualAllocEx` 被拒时刻** | **`t ≈ 2.5s` 起，`err = 5`**（`ERROR_ACCESS_DENIED`） |
| 3 | **代码洞总量** | **`SLOT × (len(apis) + 8)`** = `0x20000 × (N+8)` |

★★★ **⇒ `t≈2.5s 起 err=5` 是**又一个精确的 ACE 时序**：**
```
t ≈ 0.2s   toolhelp 被 ACE 封
t ≈ 2.5s   VirtualAllocEx 被拒（err=5 = ERROR_ACCESS_DENIED）
```

★★ **⇒ 所以**所有内存分配必须在 t≈2.5s 之前完成**。**

★ **⇒ `+8` 是给"迟到 hook"（TenProxy 的 3 个取值函数）预留的代码洞 + 计数器槽。**

★ **⇒ 若 `len(apis) = 8`（`launch_chain.py` 的 API 列表去掉 zN 后），则总量 = `0x20000 × 16 = 2 MB`。**

---

## 五、★★★★★ 迟到 hook 的**关键否证**（第 1825–1837 行，逐字）

```python
# 迟到 hook 开关(默认关): 它要往 TenProxy.dll 的代码里写 JMP。
# 对比发现: nt8 全程不碰 TenProxy 一个字节 -> 稳定停在"连接中";
#           我们一挂这几个 hook(TenProxy 是 TP3 自己的模块) -> 变成"连接失败"。
# 而 TenProxy 的关键信息现在由 dumper 直接读内存就能拿到(obj/view/table/逐 tag 长度),
# 不必再改它的代码。要开就写 late_spec.txt = "on"。
```

★★★★★ **⇒ 一次**极其重要的对照实验**：**

| 实现 | 对 TenProxy 的处理 | 结果 |
|---|---|---|
| **`nt8`** | **全程不碰一个字节** | ★ **稳定停在「连接中」** |
| **本实现**（挂 hook） | **往 TenProxy 代码写 JMP** | ★★ **变成「连接失败」** |

★★★ **⇒ 结论：**
```
TenProxy 是 **TP3 自己的模块**
        ↓
改它的代码 ⇒ 被检测 ⇒ 「连接失败」
        ↓
★ 而关键信息**直接读内存就能拿到**
（obj / view / table / 逐 tag 长度）
        ↓
★★★ ⇒ **不必再改它的代码**
```

★ **⇒ 这是一个**方向性的否证**：从"hook 探测"改为"纯内存读取"。**

★★ **⇒ 默认**关闭**（`use_late = False`），需要 `late_spec.txt = "on"` 才开。**

---

## 六、★★★★ `patcher()` 线程（第 1846–1860 行）

```python
def patcher():
    last, t0 = None, time.time()
    while not stop.is_set():
        cur = rpm(h, JNE_ADDR, 2)                       # ★ JNE_ADDR = 0x0077F6EF
        if len(cur) == 2:
            if cur != last:
                log("  t=%.1fs 0x%08X 字节变为 %s" % (time.time() - t0, JNE_ADDR,
                                                      cur.hex(" ")))
                last = cur
            if cur[0] == 0x75 and wpm(h, JNE_ADDR, b"\xEB" + cur[1:2]):
                nw[0] += 1
                log("  t=%.1fs 75->EB 已写入 (第 %d 次)" % (time.time() - t0, nw[0]))
        time.sleep(0.2)
```

### ★★★★★ 完整语义

```
每 0.2 秒读 0x0077F6EF 处的 2 字节
        ↓
若首字节 == 0x75（JNE）
        ↓
★ 改成 0xEB（JMP）
        ↓
记录次数
```

★★★ **⇒ 这是**第 5 个补丁**（前 4 个在 `compat_patch_once` 里）：**
```
补丁 1-4  →  compat_patch_thread（等解壳，90 秒）
补丁 5    →  patcher（持续监控，0.2 秒轮询）
```

★★ **⇒ 为什么要**持续监控**：因为 `0x75` 可能会被**反复还原**（TP3 完整性检查）。**

★ **⇒ 每次写入都记 `第 N 次`，可看出被还原的频率。**

★★ **⇒ `JNE_ADDR = 0x0077F6EF`**（模块级常量，报告 020 已记录）。**

---

## 七、★★★ 装 hook 前的等待（第 1862–1870 行）

```python
slots = []
known_bases = {}          # 模块名(小写) -> 运行时基址, 供 apply_patches 用
next_slot = 0             # 下一个可用的代码洞/计数器槽
try:
    log("等待 %.1fs 再装 hook(避开 TP3 在 t≈2s 的完整性检查) ..." % a.delay)
    time.sleep(a.delay)
    # 模块列表: 早期那份优先(ACE 还没封枚举); 但早期枚举经常只拿到十几个模块
    # (进程刚起/还没加载完), ws2_32 很可能不在里面 —— 此时必须继续重试,
    # 直到【ws2_32 出现】或超时。上一轮就是早期只有 11 个 + 不再重试,
```

★★★ **⇒ 三条关键信息：**
```
① `time.sleep(a.delay)` —— 默认 2.5 秒（避开 TP3 的 t≈2s）
② ★ 早期枚举**经常只拿到十几个模块**（进程刚起/还没加载完）
③ ★★ `ws2_32` 很可能**不在**早期枚举里
        ↓
⇒ **必须继续重试，直到 `ws2_32` 出现或超时**
```

★★★ **⇒ 上一轮的失败（第 1870 行截断）：**"早期只有 11 个 + 不再重试"。**

---

## 八、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | TAS 规格 | `tas_spec.txt` = `host:port:name`（默认 `127.0.0.1:3074:CODOL`） |
| 2 | 禁用开关 | `tas_off.flag`（隔离实验用） |
| 3 | ★★★ 共享内存名 | **`TCLS_SHAREDMEMEMORY<pid>`** |
| 4 | `CreateFileMappingW` | `HANDLE(-1)` + **`0x04`（PAGE_READWRITE）** |
| 5 | `MapViewOfFile` | **`0x000F001F`**（`FILE_MAP_ALL_ACCESS`） |
| 6 | ★★★★ **进大厅的充分条件** | **hosts + dwauth.ini + 4 个内存补丁**（**不写大厅全局**） |
| 7 | 线程数 | **5 个**（compat / secrets / ps-probe / dialogs / patcher） |
| 8 | ★★★ **`VirtualAllocEx` 被拒** | **`t ≈ 2.5s` 起，`err = 5`** |
| 9 | 代码洞总量 | `SLOT × (len(apis)+8)` = `0x20000 × (N+8)` |
| 10 | ★★★★ **迟到 hook 否证** | **`nt8` 不碰 TenProxy ⇒ 「连接中」；挂 hook ⇒ 「连接失败」** |
| 11 | ★★★ 结论 | **关键信息直接读内存即可，不必改代码** |
| 12 | ★ 迟到 hook 开关 | `late_spec.txt = "on"`（默认关） |
| 13 | ★★★ **第 5 个补丁** | `0x0077F6EF`：**`75`（JNE）→ `EB`（JMP）**，0.2 秒轮询 |
| 14 | ★★ 装 hook 等待 | `a.delay`（默认 **2.5** 秒） |
| 15 | ★★★ 早期枚举的坑 | **经常只有 11-19 个模块，`ws2_32` 不在里面 ⇒ 必须重试** |

---

## 九、结论

### 1. ★★★★★ **"能进大厅"的充分条件是三个**，不需要大厅全局

```
hosts + dwauth.ini + 4 个内存补丁
```

### 2. ★★★★★ **迟到 hook（改 TenProxy）是错误方向**

★★★ **⇒ `nt8` 不碰 TenProxy ⇒ 「连接中」；改它 ⇒ 「连接失败」。**
**⇒ 关键信息直接读内存即可。**

### 3. ★★★ **`VirtualAllocEx` 在 t≈2.5s 起被拒（err=5）** ⇒ 必须尽早申请代码洞

### 4. ★★★ **第 5 个补丁是持续监控的**（`0x0077F6EF`，可能被反复还原）

### 5. ★★ 早期枚举经常只拿到 11-19 个模块，必须重试等 `ws2_32`

### 6. ★★ TAS 共享内存的注入是**创建**（不是打开）`TCLS_SHAREDMEMEMORY<pid>`

---

## 十、下一步

- `nt10.py` 最后一段（第 1870 行起）—— hook 安装主循环
- `fake_auth_tls.py` / `stun_local.py` / `force_display_name.py`
- `bundle\` 五个证书文件
- `payload\` 四个插件 PE + 四个 loader 二进制
