# 学习报告 050（重开）— `force_display_name.py` 三种模式与主流程（全文完）

**学习范围**：第 249–389 行（`--tag` 收尾 / `--watch` / `--wait` / 主流程）
**性质**：全实测
**★★★ 本报告收录**三种模式的分工**与**"多次重建"的实测数据**

---

## 一、★★★★★ `--watch` 模式的完整说明（第 253–256 行，逐字）

```python
# ★ --watch：客户端从启动到进大厅会**多次重建**名字结构（实测：132 MB 时 5 处，
#   完全起来后 10 处），写一次不够。这里在给定时限内反复扫描+补写，命中就写，
#   没有就等 2 秒再看；到点退出。不是猜时间——每次都是"扫到才写"。
```

### ★★★★★ 一组精确的实测数据

| 阶段 | 内存 | 命中数 |
|---|---|---|
| 启动中 | **132 MB** | **5 处** |
| 完全起来 | （1,517 MB） | **10 处** |

★★★ **⇒ 两个关键事实：**
```
① 名字结构被**多次重建**（5 → 10 处）
② 内存从 **132 MB** 增长到 **1,517 MB**
        ↓
★★★ 写一次不够 ⇒ 必须**反复补写**
```

★ **⇒ 且明确："**不是猜时间**——每次都是'扫到才写'"。**

★★ **⇒ 这是**正确的事件驱动**设计（不是定时轮询）。**

### ★★ `--watch` 的实现（第 257–300 行）

```python
deadline = time.time() + args.watch
total = 0
while time.time() < deadline:
    pid_now = find_pid()
    if not pid_now:
        time.sleep(2)
        continue
    handle_now = k32.OpenProcess(
        PROCESS_QUERY_INFORMATION | PROCESS_VM_READ | PROCESS_VM_WRITE |
        PROCESS_VM_OPERATION, False, pid_now)
    if not handle_now:
        time.sleep(2)
        continue
    try:
        hits_now, _ = scan(handle_now, args.needle.encode("ascii"))
        if hits_now:
            encoded_now = truncate_encoded(args.apply, args.encoding, len(args.needle))
            payload_now = encoded_now + b"\x00" * (len(args.needle) - len(encoded_now))
            written_now = 0
            for address in hits_now:
                ... (三步写内存)
            total += written_now
            print("  [%s] pid=%d 命中 %d 处，写入 %d 处 -> %r" % ...)
    finally:
        k32.CloseHandle(handle_now)
    time.sleep(2)
print("watch 结束：共写入 %d 处" % total)
return 0
```

★★★ **⇒ 三个要点：**
```
① **每 2 秒**一轮（扫到才写，扫不到就等）
② ★ `truncate_encoded(..., len(args.needle))` —— **以 needle 长度为限**
③ ★★ 只扫 `args.needle`（旧名字）⇒ 写过的位置**下一轮扫不到** ⇒ **幂等**
```

★★ **⇒ 第 ③ 条是关键：**
```
第 1 轮：扫到 5 处旧名字 → 全部改掉
        ↓
第 2 轮：扫旧名字 → 只剩新增的（因为改过的已变成新名字）
        ↓
★ 只补写新增的 ⇒ **不会重复写**
```

---

## 二、★★★★ `--wait` 模式的完整说明（第 302–304 行，逐字）

```python
# ★ --wait：重拉后自动改名。客户端要 ~20-40s 才建出名字结构，所以有界重试。
#   间隔 2s、上限由 --wait 给（默认调用方给 120）。这是"等外部进程到某个状态"，
#   不是猜时间：一旦命中就立刻停。
```

★★★ **⇒ 两个精确数据：**
```
客户端要 **~20-40s** 才建出名字结构
间隔 **2s**，上限由 `--wait` 给（**默认调用方给 120**）
```

### ★★ `--wait` 的两阶段等待（第 305–323 行）

```python
if args.wait > 0:
    deadline = time.time() + args.wait
    # 阶段 1：等进程出现
    while time.time() < deadline:
        if find_pid():
            break
        time.sleep(2)
    # 阶段 2：等名字结构出现
    while time.time() < deadline:
        pid_now = find_pid()
        if pid_now:
            probe = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid_now)
            if probe:
                try:
                    hits, _ = scan(probe, args.needle.encode("ascii"))
                finally:
                    k32.CloseHandle(probe)
                if hits:
                    break
        time.sleep(2)
```

★★★ **⇒ 两个阶段：**
```
① 等**进程出现**（`find_pid()` 非空）
        ↓
② 等**名字结构出现**（`scan` 有命中）
        ↓
★ 一旦命中就 break（不等到 deadline）
```

★★ **⇒ 注意阶段 2 只用 `PROCESS_VM_READ`（不写）—— 因为只是**探测**。**

---

## 三、★★★★ 主流程（第 325–384 行）

### 3.1 ★★★ 定位与打开（第 325–336 行）

```python
pid = find_pid()
if not pid:
    print("客户端没在跑")
    return 1
print("client pid=%d  现役名字=%r" % (pid, args.needle))

handle = k32.OpenProcess(
    PROCESS_QUERY_INFORMATION | PROCESS_VM_READ | PROCESS_VM_WRITE | PROCESS_VM_OPERATION,
    False, pid)
if not handle:
    print("OpenProcess 失败 err=%d" % ctypes.get_last_error())
    return 1
```

★★ **⇒ 四个权限全开（`QUERY_INFORMATION | VM_READ | VM_WRITE | VM_OPERATION`）。**

### 3.2 ★★★ 扫描与列出（第 338–349 行）

```python
needle = args.needle.encode("ascii")
hits, total = scan(handle, needle)
print("扫描可读内存 %.1f MB，命中 %d 处" % (total / 1048576.0, len(hits)))
for address in hits:
    raw = context(handle, address)
    if raw:
        head = " ".join("%02X" % c for c in raw[8:16])
        text = "".join(chr(c) if 32 <= c < 127 else "." for c in raw)
        print("  0x%08X  头[%s]  %s" % (address, head, text))
if not hits or args.list_only or not args.apply:
    k32.CloseHandle(handle)
    return 0
```

★★★ **⇒ 三个提前返回条件：**
```
① `not hits`        —— 没命中
② `args.list_only`  —— 只要列表
③ `not args.apply`  —— 没给目标名
```

★★ **⇒ 三者任一 ⇒ 只报告不修改。**

### 3.3 ★★★★★ 就地覆盖（第 351–378 行）

```python
# 就地覆盖：新名字 + NUL 补齐到原字段长度（原字段是 16 字节定长）
#
# ★ 2026-10-05 18:2x：支持中文。编码用 **GBK**，依据是本客户端自带的 TCLS 通路
#   `nt10.py:406 put(entry | 2, name.encode("gbk", "replace") + b"\x00")`
#   —— 这个客户端写名字就是 GBK。字段 16 字节，中文一个字 2 字节，
#   所以最多 8 个汉字（`无敌暴龙战神` = 12 字节，够）。
encoded = args.apply.encode(args.encoding, "replace")
if len(encoded) > len(needle):
    print("新名字 GBK 后 %d 字节 > 字段 %d 字节，会被截断" % (len(encoded), len(needle)))
replacement = encoded[:len(needle)]
payload = replacement + b"\x00" * (len(needle) - len(replacement))
```

### ★★★★★ 编码选择的依据（逐字）

```python
# 依据是本客户端自带的 TCLS 通路
#   `nt10.py:406 put(entry | 2, name.encode("gbk", "replace") + b"\x00")`
#   —— 这个客户端写名字就是 GBK。
```

★★★ **⇒ 编码选择的**实证依据**：**
```
nt10.py:406 的 TCLS 通路用 **GBK** 写服务器名
        ↓
★ ⇒ "这个客户端写名字就是 GBK"
```

★ **⇒ 但注意：`nt10.py:406` 是**服务器名**（`entry|2`），不是玩家名。**

★★ **⇒ 这是一个**类比推理**（服务器名用 GBK ⇒ 玩家名也用 GBK）。**

★★★ **⇒ 而后来（报告 049）`--encoding` 默认仍是 `gbk`，但 `launch_chain` 传 `utf-8` ——**
**⇒ 说明这个类比后来被**推翻**（榜单是 UTF-8 渲染）。**

### ★★★ 截断处理（第 357–361 行）

```python
encoded = args.apply.encode(args.encoding, "replace")
if len(encoded) > len(needle):
    print("新名字 GBK 后 %d 字节 > 字段 %d 字节，会被截断" % (len(encoded), len(needle)))
replacement = encoded[:len(needle)]        # ★ 直接字节截断（不按字符边界！）
payload = replacement + b"\x00" * (len(needle) - len(replacement))
```

★★★★★ **⇒ 这里有一个**不一致**：**
```
`truncate_encoded()`  →  ★ 按字符边界截断（报告 049）
本处（主流程）          →  ★★ `encoded[:len(needle)]` **直接字节截断**
```

★★★ **⇒ 主流程**没有用** `truncate_encoded`，而是直接 `[:len(needle)]` ——**
**⇒ **可能切出半个 UTF-8 字符**。**

★ **⇒ 这是**一个真实的缺陷**（`truncate_encoded` 只在 `--watch` 和 `--tag` 用，主流程没用）。**

### 3.4 ★★★ 写内存与回读（第 362–382 行）

```python
written = 0
for address in hits:
    old = wintypes.DWORD()
    if not k32.VirtualProtectEx(handle, ctypes.c_void_p(address), len(payload),
                                PAGE_EXECUTE_READWRITE, ctypes.byref(old)):
        print("  0x%08X VirtualProtectEx 失败 err=%d" % (address, ctypes.get_last_error()))
        continue
    done = ctypes.c_size_t()
    ok = k32.WriteProcessMemory(handle, ctypes.c_void_p(address), payload, len(payload),
                                ctypes.byref(done))
    k32.VirtualProtectEx(handle, ctypes.c_void_p(address), len(payload), old,
                         ctypes.byref(wintypes.DWORD()))
    if ok and done.value == len(payload):
        written += 1
    else:
        print("  0x%08X 写失败 err=%d" % (address, ctypes.get_last_error()))
print("已写入 %d/%d 处 -> %r" % (written, len(hits), args.apply))

again, _ = scan(handle, needle)
after, _ = scan(handle, replacement)
print("回读：旧名字剩 %d 处，新名字 %d 处" % (len(again), len(after)))
```

★★★ **⇒ 完整的写-回读验证：**
```
① 三步写内存（改保护 → 写 → 恢复）
② 逐地址报告失败原因（含 err 码）
③ ★★ 回读：扫旧名字（应剩 0）+ 扫新名字（应 == 写入数）
```

★★ **⇒ 第 ③ 条是**自我验证**（与 `nt10.py` 的 `apply_patches` 的"读-写-读"同类）。**

★ **⇒ 但注意：`scan(handle, replacement)` 扫的是**不含 NUL 的新名字**，**
**⇒ 若新名字是 `FF0`，会命中所有含 `FF0` 的地方（**可能多报**）。**

---

## 四、★★★★ 三种模式的完整对比

| 模式 | 触发 | 用途 | 扫描前缀 | 编码处理 |
|---|---|---|---|---|
| **默认**（无 `--watch`/`--wait`/`--tag`） | 立即 | 一次性改名 + 回读验证 | `--needle` | ★ `[:len(needle)]`（**字节截断**） |
| **`--watch N`** | 持续 N 秒 | ★ 反复补写（结构会重建） | `--needle` | ★ `truncate_encoded`（**字符边界**） |
| **`--wait N`** | 最多 N 秒 | 等客户端起来 + 名字结构出现 | `--needle` | （不写，只探测） |
| **`--tag`** | 持续（`--watch` 或 150 秒） | ★ 写唯一标签建映射 | **`b"Lifetime"`** | 固定 ASCII |

★★★ **⇒ 四种模式（含默认），三条不同的扫描前缀/编码策略。**

---

## 五、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★★★ **多次重建实测** | **132 MB 时 5 处** → 完全起来 **10 处** |
| 2 | ★ 设计原则 | **"不是猜时间——每次都是'扫到才写'"** |
| 3 | `--watch` 间隔 | **2 秒** |
| 4 | ★★ `--watch` 幂等 | 只扫旧名字 ⇒ 写过的下轮扫不到 |
| 5 | ★★★ **名字结构出现时间** | **~20-40 秒** |
| 6 | `--wait` 默认（调用方） | **120 秒** |
| 7 | ★★ `--wait` 两阶段 | 等**进程** → 等**名字结构** |
| 8 | ★★★ **编码依据** | `nt10.py:406` 的 TCLS 通路用 **GBK** |
| 9 | ★ 中文容量 | 16 字节 ⇒ 最多 **8 个汉字**（`无敌暴龙战神` = 12 字节） |
| 10 | ★★★★★ **主流程的截断缺陷** | **`encoded[:len(needle)]` 直接字节截断**（未用 `truncate_encoded`） |
| 11 | ★★ 回读验证 | 扫旧名字（应 0）+ 扫新名字 |
| 12 | ★ 回读的局限 | 短名字会**多报**（含子串即命中） |
| 13 | ★ 写内存三步 | 改保护 → 写 → **恢复** |
| 14 | 权限 | `QUERY_INFORMATION \| VM_READ \| VM_WRITE \| VM_OPERATION` |

---

## 六、结论

### 1. ★★★★★ **名字结构会被多次重建**（132 MB 时 5 处 → 10 处）

★ **⇒ 这是 `--watch` 存在的根本原因。**

### 2. ★★★★★ **主流程的字节截断是真实缺陷**

```
truncate_encoded  →  按字符边界（正确）
主流程            →  encoded[:len(needle)]  →  ★ 可能切出半个字符
```

★★ **⇒ 这会导致"进不去服"（报告 049 已说明后果）。**

### 3. ★★★ **编码选择的依据是类比推理**（TCLS 服务器名用 GBK ⇒ 玩家名也用 GBK）

★ **⇒ 后来被推翻（榜单是 UTF-8 渲染）。**

### 4. ★★★ **`--watch` 的幂等设计**（只扫旧名字）

### 5. ★★ **`--wait` 是两阶段等待**（进程 → 名字结构）

### 6. ★★ 回读验证有局限（短名字会多报）

---

## 七、`bundle\` 五个脚本的学习总览

| # | 脚本 | 字节 | 行数 | 报告 | 核心成果 |
|---|---|---|---|---|---|
| 1 | `launch_chain.py` | 25,009 | 445 | 017/018/019 | 五条设计论证 / 三种 role / 七个退出码 |
| 2 | **`nt10.py`** | **146,765** | **2,661** | **020–043（24 份）** | 手写机器码 / TCLS 镜像 / 四补丁 / 密钥链 |
| 3 | `fake_auth_tls.py` | 17,600 | 413 | 044/045/046 | 票据 128B / 三层嵌套 / close-notify |
| 4 | `stun_local.py` | 7,618 | 184 | 047 | DW 私有 STUN 15 字节 |
| 5 | `force_display_name.py` | 19,288 | 389 | 048/049/050 | 五通道失效 / UTF-8 截断 / 标签法 |

★★★ **⇒ 五个脚本共 **216,280 字节 / 4,092 行**，全部逐段学完。**

---

## 八、下一步

- `bundle\` **五个证书文件**逐字节
- `payload\` **四个插件 PE** + **四个 loader 二进制**
- `payload\` **18 个小 map lua** + `cha.lua`/`zm.lua` 剩余
- `source\` 结构与关键文档
