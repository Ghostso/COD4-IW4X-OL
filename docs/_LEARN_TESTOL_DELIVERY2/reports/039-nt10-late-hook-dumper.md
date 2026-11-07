# 学习报告 039（重开）— `nt10.py` 迟到 hook 执行与 dumper 线程

**学习范围**：第 2128–2247 行（TenProxy 转储 + thunk 解析 + 迟到 hook 计划 + dumper）
**性质**：全实测
**★★★ 本报告收录**迟到 hook 的两个精确 RVA**与**六个 thunk 地址**

---

## 一、★★★★ TenProxy 运行时转储（第 2128–2133 行）

```python
if len(tb) >= 0x1000:
    tp_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "tp_runtime.bin")
    open(tp_path, "wb").write(tb)
    log("  [dump] TenProxy 运行时镜像 %.0fKB -> tp_runtime.bin"
        % (len(tb) / 1024.0))
```

★★ **⇒ 转储前 `0x40000`（256 KB）到 `tp_runtime.bin`。**

★★★ **⇒ 这是**唯一能拿到 TenProxy 真实代码的方式**（磁盘上 thunk 区是 0）。**

---

## 二、★★★★★ 六个 thunk 地址的解析（第 2134–2150 行）

```python
# thunk 区直接解出 每条 jmp 目标, 打印 RVA 对照
md3 = None
try:
    import capstone as _cs
    md3 = _cs.Cs(_cs.CS_ARCH_X86, _cs.CS_MODE_32)
except Exception as _e2:
    log("  [thunk] capstone 不可用: %s" % _e2)
for th in (0x119A, 0x107D, 0x1078, 0x1451, 0x13ED, 0x1226):
    if md3 is None:
        break
    for ins in md3.disasm(tb[th:th + 8], base + th):
        if ins.mnemonic in ("jmp", "ret"):
            log("  [thunk] RVA 0x%X -> %s %s" % (th, ins.mnemonic, ins.op_str))
            break
```

### ★★★★★ 六个 thunk RVA（精确）

```
0x119A / 0x107D / 0x1078 / 0x1451 / 0x13ED / 0x1226
```

★★★ **⇒ 这六个是**thunk 区的入口**，每个是一条 `jmp`（转到真实函数）。**

★★ **⇒ 用 capstone 反汇编前 8 字节，找到 `jmp` 或 `ret` 就打印。**

★ **⇒ 用途：**"打印 RVA 对照"** —— 建立 thunk → 真实函数的映射表。**

★★★ **⇒ 这解释了为什么 `nt10.py` 依赖 `capstone`（`run.cmd:9` 提到）。**

---

## 三、★★★★★ 迟到 hook 的两个精确 RVA（第 2158–2168 行）

### 3.1 ★★★ 完整的推理链（第 2158–2167 行，逐字）

```python
# 0x7DA0(槽0x24, DWORD 2 参) / 0x7EA0(槽0x28, blob 3 参) 是 pad LoginInfo
# 和 0x6310 那段共用的取值函数; 0x7EA0 的第 2 个参数 dst 可以为 0
# (查询长度模式), 这正是"期望尺寸"的最直接来源, 所以给它挂 decl 模式。
# 0x6BD0 = CTclsProxy::GetLoginInfo(__EH_prolog, 头 3 字节 55 8b ec),
# 挂上它就能看到服务器列表循环到底跑没跑。
# 注意 0x7ED0 是 0x7EA0 函数体内部(cmp [ebp+0x10],0), 不是入口, 不能挂。
# 槽 0x2c(读 tag 14/15/16/19)指向的是另一个函数, 它的 RVA 只能从运行时
# vtable 里读 —— 由下面的 dumper 打印出来。
# 2026-10-01: 只挂读 tag7/tag8 的两个真函数(0x8250=vtable[12], 0x8510=vtable[14]),
# 用 decl 记录 (tag,dst,pLen,seq) + *pLen, 看游戏到底怎么读 —— 这是当前唯一卡点。
```

### ★★★★★ 完整的 RVA 对照表

| RVA | 槽/角色 | 签名 | 说明 |
|---|---|---|---|
| **`0x7DA0`** | 槽 **`0x24`** | **DWORD 2 参** | pad LoginInfo |
| **`0x7EA0`** | 槽 **`0x28`** | **blob 3 参** | ★ `dst` 可为 0（**查询长度模式**） |
| **`0x6BD0`** | — | **`CTclsProxy::GetLoginInfo`** | `__EH_prolog`，头 3 字节 **`55 8b ec`** |
| **`0x7ED0`** | ✗ | — | ★★★ **是 `0x7EA0` 函数体内部**（`cmp [ebp+0x10],0`），**不是入口，不能挂** |
| **`0x8250`** | **`vtable[12]`** | 4 参带序号 | ★ 读 **tag7/tag8** |
| **`0x8510`** | **`vtable[14]`** | 4 参带序号 | ★ 读 **tag7**（要求 len==4） |

★★★ **⇒ 三条关键洞察：**

**① `0x7EA0` 的 `dst` 可为 0（查询长度模式）**
```
这是"期望尺寸"的最直接来源
        ↓
所以给它挂 decl 模式
```

**② `0x7ED0` 不是入口（是 `0x7EA0` 内部）**
```
0x7ED0 = 0x7EA0 函数体内部的 cmp [ebp+0x10], 0
        ↓
★★★ **不能挂**（会破坏函数中间）
```

**③ `0x6BD0 = CTclsProxy::GetLoginInfo`，头 3 字节 `55 8b ec`**
★ **⇒ 与 `pick_stolen` 的校验一致。**

### 3.2 ★★★ 最终只挂两个（第 2168 行）

```python
plans = ((0x8250, 4, "decl"), (0x8510, 4, "decl"))
```

★★★ **⇒ 只挂 `0x8250` 和 `0x8510` 两个，都用 `decl` 模式，`str_off = 4`。**

★★ **⇒ 注释（第 2167 行，逐字）：**
> **"这是当前唯一卡点"**

★ **⇒ 说明：读 tag7/tag8 的机制是**当时未解决的核心问题**。**

### 3.3 ★★★ 迟到 hook 的执行（第 2169–2188 行）

```python
for rva, soff, md2 in plans:
    tgt = base + rva
    orig = rpm(h, tgt, 16)
    stolen, n = pick_stolen(orig, tgt)
    if not stolen:
        log("-- tp+0x%X 偷指令失败 (%s)" % (rva, orig[:5].hex(" ")))
        continue
    s = next_slot
    cave = page + s * 0x400
    ccnt = page + SLOT * (s + 1)
    code = build_tramp(ccnt, ccnt + 4, stolen, tgt + n, cave, soff, md2)
    if not wpm(h, cave, code) or not wpm(h, tgt, b"\xE9" +
                                         struct.pack("<i", cave - (tgt + 5)) +
                                         b"\x90" * (n - 5)):
        log("-- tp+0x%X 写 hook 失败" % rva)
        continue
    log("-- 迟到 hook tp+0x%X @0x%08X 偷%d字节 (槽 %d, 模式 %s)"
        % (rva, tgt, n, s, md2))
    slots.append(("tp+0x%X" % rva, ccnt, False, md2))
    next_slot += 1
```

★★ **⇒ 与普通 hook 的流程**完全相同**（报告 038），只是目标地址来自 `plans`。**

★ **⇒ `slots.append(("tp+0x%X" % rva, ccnt, False, md2))` ——**
**⇒ 命名 `tp+0x8250`，`wide=False`，`mode="decl"`。**

### 3.4 ★★ 额外补丁（第 2190–2194 行）

```python
if PS:
    try:
        apply_patches(h, known_bases, ml, PS, log)
    except Exception as e:
        log("-- patch 异常: %r" % (e,))
```

★★ **⇒ `PS` 来自 `patch_spec.txt`（默认空）⇒ **通常不执行**。**

---

## 四、★★★★ dumper 线程（第 2198–2247 行）

### 4.1 ★★★ 三个取证目标（第 2198–2202 行，逐字）

```python
# ---- 运行时取证: 把"游戏自己看到的东西"抄回来 ----
#  1) exe 的登录读取段(0x241300 起): 磁盘上是加壳态, 只有运行时才是真码
#  2) exe 全局 [0x82E1580] 指向的 CTclsProxy 对象(它内部 +0x18C4/+0x18C8
#     就是 TAS 镜像的 记录基址 / table 指针)
#  3) 逐 tag 打印"记录长度": 直接验证我们的镜像在游戏眼里长什么样
TAS_OBJ_PTR = 0x82E1580
```

### ★★★★★ 三个精确地址

| # | 项 | 地址 |
|---|---|---|
| **1** | exe 登录读取段 | **`0x241300`** 起（★ 磁盘上是加壳态） |
| **2** | ★★★ **CTclsProxy 对象指针** | **`0x82E1580`** |
| **2a** | ★★★ 内部偏移 | **`+0x18C4`（记录基址）/ `+0x18C8`（table 指针）** |
| **3** | 逐 tag 记录长度 | （通过上面的对象） |

★★★ **⇒ `+0x18C4` / `+0x18C8` 正是 TAS 镜像的**记录基址 / table 指针**。**

★★ **⇒ 这印证了报告 023 的镜像布局（`table` 在 `+4`，`rec` 在 `0x100004`）——**
**游戏把它们记在对象里。**

### 4.2 ★★★ exe 模块范围校验（第 2206–2215 行）

```python
def dumper():
    exe_base = next((b2 for n2, b2, s2 in ml
                     if n2.lower().startswith("codomp_client")), 0)
    exe_size = next((s2 for n2, b2, s2 in ml
                     if n2.lower().startswith("codomp_client")), 0)
    if exe_base:
        log("  [mod] exe base=0x%08X size=0x%X (末=0x%08X) 场景全局0x%08X %s"
            % (exe_base, exe_size, exe_base + exe_size, 0x08269774,
               "在范围内" if exe_base <= 0x08269774 < exe_base + exe_size
               else "★超出模块范围"))
```

★★★ **⇒ 校验 `0x08269774`（svc 槽）是否在 exe 模块范围内。**

★★ **⇒ 若"超出模块范围" ⇒ 说明基址不是 `0x400000`（ASLR 或重定位）。**

★ **⇒ 这是一个**重要的自检**。**

### 4.3 ★★★ 40 轮 × 3 秒的循环（第 2216–2222 行）

```python
for _it in range(40):
    if stop.is_set():
        return
    time.sleep(3)
    # 在 /auth/ 之后按 vtable 找出客户端 auth 对象, 看应答被接受到哪一步
    if _it in (24, 31, 37):
        probe_auth_object(h, log)
```

★★★ **⇒ 40 轮 × 3 秒 = **120 秒** 总时长。**

★★ **⇒ 在第 **24 / 31 / 37** 轮（即 t ≈ 72 / 93 / 111 秒）调 `probe_auth_object`。**

★ **⇒ 注释："在 `/auth/` 之后按 vtable 找出客户端 auth 对象, 看应答被接受到哪一步"。**

### 4.4 ★★★ `netstat` 旁证（第 2223–2240 行）

```python
# 旁证: 直接读游戏的 TCP 连接表(不依赖任何 hook) —— 若 connect 的
# sockaddr 被解码成垃圾, 这里能看到真实的外连目标与状态(SYN_SENT 等)
try:
    import subprocess as _sp
    _out = _sp.check_output(["netstat", "-ano"], encoding="latin1",
                            errors="replace", timeout=12)
except Exception:
    _out = ""
if _out:
    _conns = set()
    for _ln in _out.splitlines():
        _p = _ln.split()
        if len(_p) >= 5 and _p[0].upper() == "TCP" and _p[4] == str(pid):
            _conns.add("%s [%s]" % (_p[2], _p[3]))
    _key = "|".join(sorted(_conns))
    if _key and _key != got.get("conns"):
        got["conns"] = _key
        log("  [net] 游戏 TCP 连接 = %s" % " ; ".join(sorted(_conns)))
```

★★★★ **⇒ 这是一个**绝妙的独立旁证**：**
```
不依赖任何 hook
        ↓
直接 `netstat -ano` 读系统 TCP 表
        ↓
过滤出 pid == 目标进程的行
        ↓
★ 显示**真实的外连目标与状态**（如 SYN_SENT）
```

★★★ **⇒ 注释说明用途：**"若 connect 的 sockaddr 被解码成垃圾,
这里能看到真实的外连目标与状态"。**

★ **⇒ 即：**当 hook 的解码不可信时，用系统表交叉验证**。**

★★ **⇒ 格式：`%s [%s]` = `远端地址:端口 [状态]`。**

★ **⇒ 只在**变化时**打印（`_key != got.get("conns")`）。**

---

## 五、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | TenProxy 转储 | 前 **`0x40000`（256 KB）** → `tp_runtime.bin` |
| 2 | ★★★ 六个 thunk RVA | **`0x119A` / `0x107D` / `0x1078` / `0x1451` / `0x13ED` / `0x1226`** |
| 3 | ★ 槽 `0x24` | RVA **`0x7DA0`**（DWORD 2 参） |
| 4 | ★★ 槽 `0x28` | RVA **`0x7EA0`**（blob 3 参，`dst` 可为 0） |
| 5 | ★ `GetLoginInfo` | RVA **`0x6BD0`**，头 **`55 8b ec`** |
| 6 | ★★★ **不能挂** | **`0x7ED0`**（是 `0x7EA0` 内部） |
| 7 | ★★★ **实际挂两个** | **`0x8250`（vtable[12]）/ `0x8510`（vtable[14]）** |
| 8 | 模式 | 都是 **`decl`**，`str_off = 4` |
| 9 | ★★★ 注释 | **"这是当前唯一卡点"** |
| 10 | ★★★ exe 登录段 | **`0x241300`** 起（磁盘加壳） |
| 11 | ★★★ **CTclsProxy 指针** | **`0x82E1580`** |
| 12 | ★★★ 内部偏移 | **`+0x18C4`（记录基址）/ `+0x18C8`（table 指针）** |
| 13 | ★ 模块范围校验 | `0x08269774` 是否在 exe 范围内 |
| 14 | dumper 循环 | **40 轮 × 3 秒 = 120 秒** |
| 15 | auth 探针时刻 | 第 **24 / 31 / 37** 轮（t ≈ 72 / 93 / 111 秒） |
| 16 | ★★★★ **netstat 旁证** | 不依赖 hook，直接读系统 TCP 表 |

---

## 六、结论

### 1. ★★★★★ **`0x82E1580` 是 CTclsProxy 对象指针**，内部 `+0x18C4/+0x18C8` 是 TAS 镜像的基址

★ **⇒ 这是"我们的镜像在游戏眼里长什么样"的**直接验证点**。**

### 2. ★★★★★ **`0x7ED0` 不是入口，不能挂**（是 `0x7EA0` 的内部）

★ **⇒ 这是一个**避免踩坑的关键区分**。**

### 3. ★★★ **实际只挂 `0x8250` / `0x8510`**（读 tag7/tag8），且注释说"这是当前唯一卡点"

### 4. ★★★★ **`netstat` 旁证**是当 hook 不可信时的独立验证手段

### 5. ★★★ **thunk 区磁盘上是 0** ⇒ 必须运行时转储 + capstone 解析

### 6. ★★ dumper 的 120 秒循环覆盖整个启动窗口

---

## 七、下一步

- `nt10.py` 最后一段（第 2247 行起）—— dumper 剩余与主循环
- `fake_auth_tls.py` / `stun_local.py` / `force_display_name.py`
- `bundle\` 五个证书文件
- `payload\` 四个插件 PE + 四个 loader 二进制
