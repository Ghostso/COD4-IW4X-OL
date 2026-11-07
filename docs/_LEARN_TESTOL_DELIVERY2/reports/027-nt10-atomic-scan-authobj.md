# 学习报告 027（重开）— `nt10.py` 原子写 + 内存扫描 + auth 对象探针

**学习范围**：`secrets_snapshot_thread` 剩余（779–802）+ `_MBI` / `scan_dword` / `probe_auth_object`（805–885）
**性质**：全实测
**★★★ 本报告收录**secrets.txt 的确切格式**、**MEM_PRIVATE 扫描策略**、**auth 对象的关键字段偏移**

---

## 一、★★★★★ `secrets.txt` 的**确切格式**（第 786–801 行）

### 1.1 写入条件（第 786–789 行）

```python
# state>=2 就有 challenge；state==3 才有 aes/hmac。任一有内容就写。
cur = (s.get("challenge", b""), s.get("aes_out", b""), s.get("hmac_out", b""))
if any(cur) and cur != last:
    last = cur
```

★★★ **⇒ 两个条件：**
```
① any(cur)      —— challenge / aes_out / hmac_out **任一非空**
② cur != last   —— **内容有变化**（避免重复写）
```

★ **⇒ `cur` 是三元组，只用于**变化检测**。**

### 1.2 ★★★★★ 文件格式（第 790–793 行，逐字节）

```python
lines = ["pid %d" % pid, "state %d" % s.get("state", 0)]
for n in ("challenge", "aes_out", "aes_in", "hmac_out", "hmac_in"):
    if s.get(n):
        lines.append("%s %s" % (n, s[n].hex()))
```

★★★ **⇒ `secrets.txt` 的完整格式：**
```
pid <PID>
state <N>
challenge <hex>
aes_out <hex>
aes_in <hex>
hmac_out <hex>
hmac_in <hex>
```

★★★ **⇒ 空格分隔，每行一个键值对。**

★ **⇒ 顺序固定：`pid` / `state` / `challenge` / `aes_out` / `aes_in` / `hmac_out` / `hmac_in`。**

★★ **⇒ **`pid` 在第一行** —— 正是报告 026 说的"判据"。**

### 1.3 ★★★★ 原子写（第 794–797 行）

```python
tmp = SECRETS_PATH + ".tmp"
with open(tmp, "w") as f:
    f.write("\n".join(lines) + "\n")
os.replace(tmp, SECRETS_PATH)
```

★★★ **⇒ 标准的三步原子写：**
```
① 写临时文件  secrets.txt.tmp
② 关闭（with 块退出）
③ ★★ os.replace(tmp, SECRETS_PATH)   ← 原子替换（Windows 上也是原子的）
```

★★ **⇒ `os.replace` 在 Windows 上映射到 `MoveFileEx(MOVEFILE_REPLACE_EXISTING)`，是**原子的**。**
**⇒ 保证读端永远看到**完整文件**，不会读到半个。**

### 1.4 ★★★ 日志（第 798–801 行）

```python
log("[secrets] 快照已写 state=%s challenge=%s"
    % (s.get("state"), (s.get("challenge") or b"").hex()))
log("[secrets]   aes_out=%s" % (s.get("aes_out") or b"").hex())
log("[secrets]   hmac_out=%s" % (s.get("hmac_out") or b"").hex())
```

★★ **⇒ 三行日志：`state`+`challenge` / `aes_out` / `hmac_out`。**

### 1.5 ★★★ 0.05 秒轮询（第 802 行）

```python
time.sleep(0.05)
```

★★★ **⇒ 与报告 026 的"0.5s → 0.05s"一致。**

---

## 二、★★★★ `_MBI` 与 `scan_dword`（第 805–850 行）

### 2.1 `_MBI` 结构（第 805–812 行）

```python
class _MBI(ctypes.Structure):
    _fields_ = [("BaseAddress", ctypes.c_void_p),
                ("AllocationBase", ctypes.c_void_p),
                ("AllocationProtect", wintypes.DWORD),
                ("RegionSize", ctypes.c_size_t),
                ("State", wintypes.DWORD),
                ("Protect", wintypes.DWORD),
                ("Type", wintypes.DWORD)]
```

★★ **⇒ `MEMORY_BASIC_INFORMATION` 的完整定义（7 个字段）。**

### 2.2 ★★★★★ 扫描策略（第 816–817 行，逐字）

```python
def scan_dword(h, value, maxtime=60.0, cap=8):
    """在【私有可提交】内存里找 4 字节值(小端)。只扫 MEM_PRIVATE(堆), 不扫镜像,
    这样规模可控。返回命中地址列表。"""
```

★★★★★ **⇒ 核心设计决策：**
```
只扫 MEM_PRIVATE（堆）
不扫镜像（.text/.rdata 等）
        ↓
★ 规模可控
```

★★★ **⇒ 这与上一轮 `force_display_name.py` 的"扫所有可读区"**不同**：**
```
force_display_name.py   扫 READABLE（含镜像）
nt10.py scan_dword      只扫 MEM_PRIVATE（只扫堆）
```

★ **⇒ 因为要找的是**运行期创建的对象**（在堆上），不是静态数据。**

### 2.3 ★★★ 五个常量（第 825–826 行）

```python
MEM_COMMIT, MEM_PRIVATE = 0x1000, 0x20000
PAGE_GUARD, PAGE_NOACCESS = 0x100, 0x01
```

★★ **⇒ 四个标志位。**

### 2.4 ★★★ 完整遍历逻辑（第 827–850 行）

```python
while addr < 0x7FFF0000 and time.time() - t0 < maxtime:
    mbi = _MBI()
    if k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi),
                          ctypes.sizeof(mbi)) == 0:
        addr += 0x1000
        continue
    base = mbi.BaseAddress or 0
    size = mbi.RegionSize or 0
    if (mbi.State == MEM_COMMIT and mbi.Type == MEM_PRIVATE
            and not (mbi.Protect & (PAGE_GUARD | PAGE_NOACCESS))):
        off = 0
        while off < size:
            want = int(min(0x40000, size - off))     # ★ 每次最多 256 KB
            d = rpm(h, base + off, want)
            if d:
                k = d.find(pat)
                while k >= 0:
                    hits.append(base + off + k)
                    if len(hits) >= cap:              # ★ cap=8
                        return hits
                    k = d.find(pat, k + 4)            # ★ +4 而非 +1
            off += want
    addr = base + size if size else addr + 0x1000
```

★★★ **⇒ 六个设计要点：**

| # | 要点 | 值 |
|---|---|---|
| 1 | 地址上限 | **`0x7FFF0000`**（32 位用户态上限） |
| 2 | 时间上限 | **`maxtime = 60.0`** 秒 |
| 3 | 三个过滤条件 | `MEM_COMMIT` **且** `MEM_PRIVATE` **且** 非 `GUARD`/`NOACCESS` |
| 4 | 分块读取 | **每次最多 `0x40000`（256 KB）** |
| 5 | 命中上限 | **`cap = 8`** |
| 6 | ★ 搜索步长 | **`k + 4`**（不是 `+1`，因为找的是 4 字节值） |

★★ **⇒ 第 6 点是正确的优化：DWORD 不会重叠。**
**（对比 `force_display_name.py` 用 `+1`，因为找的是字符串）**

★★★ **⇒ `VirtualQueryEx` 失败时 `addr += 0x1000` —— 跳一页继续。**

---

## 三、★★★★★ `probe_auth_object`（第 853–885 行）—— auth 对象的关键字段

### 3.1 ★★★ docstring 的完整判据（第 854–858 行，逐字）

```python
def probe_auth_object(h, log):
    """按 vtable 0xD5A2EC 找出客户端的 auth 对象, 打印关键字段。
    判据参考反汇编:
      [obj+0x18]  = 早期从应答里取的第一个值(0xB9A5CE)
      [obj+0xD8]  = 逐位解析 client_ticket 后的首个 dword, 必须 == DE AD BD EF(0xB9A809)
      [obj+0xCC]/[obj+0xC8]/[obj+0xD0] = 后续一步写入(0xB9A863/0xB9A877/0xB9A888)
    """
```

★★★★★ **⇒ 三个关键字段 + 四处反汇编地址：**

| 字段 | 含义 | 反汇编地址 |
|---|---|---|
| **`+0x18`** | 早期从应答里取的第一个值 | **`0xB9A5CE`** |
| **`+0xD8`** | ★★★ **逐位解析 `client_ticket` 后的首个 dword** | **`0xB9A809`** |
| `+0xCC` / `+0xC8` / `+0xD0` | 后续一步写入 | `0xB9A863` / `0xB9A877` / `0xB9A888` |

★★★ **⇒ **`[obj+0xD8]` 必须 == `0xEFBDADDE`（= `DE AD BD EF` 小端）**。**

★★★★★ **⇒ 这正是**票据魔数**（上一轮报告 012 已确认）：**
```
ticket[0..3] = DE AD BD EF
        ↓ 小端读作 DWORD
0xEFBDADDE
```

★ **⇒ 所以 `[obj+0xD8]` 是"票据是否被正确解析"的**验证点**。**

### 3.2 ★★★ vtable 地址 `0xD5A2EC`

```python
hits = scan_dword(h, 0xD5A2EC)
```

★★ **⇒ 用 `scan_dword` 找 `0xD5A2EC` 这个 vtable 指针值。**

★★★ **⇒ 而上一轮 capstone 实测的 svc vtable 是 **`0xD5A5E0`**（报告 051）——**
**`0xD5A2EC` 与它相差 `0x2F4`（756 字节）。**

★ **⇒ 说明这是**另一个类**的 vtable（`auth` 对象 vs `svc` 对象）。**

### 3.3 ★★★ 扫描的 13 个字段（第 871–872 行）

```python
for off in (0x18, 0x28, 0x2C, 0xC8, 0xCC, 0xD0, 0xD8, 0xE0, 0xF8, 0xFC,
            0x160, 0x164, 0x168):
```

★★★ **⇒ 13 个偏移：**
```
0x18, 0x28, 0x2C, 0xC8, 0xCC, 0xD0, 0xD8, 0xE0, 0xF8, 0xFC, 0x160, 0x164, 0x168
```

★ **⇒ 但日志只打印 **12 个**（漏了 `0x168`）。**

★★ **⇒ 日志格式串（第 875–878 行）明确标注：**
```python
"+D8=0x%X(票据魔数应为0xEFBDADDE) +E0=0x%X +F8=0x%X +FC=0x%X +160=0x%X +164=0x%X"
```

★★★ **⇒ `+D8` 的期望值是 **`0xEFBDADDE`**（票据魔数）。**

### 3.4 ★★★ 内存转储（第 879–883 行）

```python
try:
    open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "_authobj_%08X.bin" % a), "wb").write(rpm(h, a, 0x2400))
except Exception:
    pass
```

★★★ **⇒ 把 auth 对象的前 **`0x2400`（9216）字节**转储到 `_authobj_<addr>.bin`。**

★ **⇒ 这是**离线分析的原始材料**（`auth` 对象的完整结构）。**

### 3.5 ★★ 最多处理 4 个命中

```python
for a in hits[:4]:
```

★ **⇒ `scan_dword` 的 `cap=8`，这里只取前 **4** 个。**

---

## 四、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★ 写入条件 | `any(challenge/aes_out/hmac_out)` **且** 有变化 |
| 2 | ★★★★★ **`secrets.txt` 格式** | `pid` / `state` / `challenge` / `aes_out` / `aes_in` / `hmac_out` / `hmac_in` |
| 3 | ★★★ 原子写 | 写 `.tmp` → **`os.replace`** |
| 4 | ★★★ 轮询间隔 | **`0.05`** 秒 |
| 5 | ★★★★★ 扫描策略 | **只扫 `MEM_PRIVATE`（堆），不扫镜像** |
| 6 | 地址上限 | `0x7FFF0000` |
| 7 | 时间上限 | **`60.0`** 秒 |
| 8 | 分块大小 | **`0x40000`（256 KB）** |
| 9 | 命中上限 | **`cap = 8`** |
| 10 | ★ 搜索步长 | **`k + 4`**（DWORD 不重叠） |
| 11 | ★★★ auth vtable | **`0xD5A2EC`**（≠ svc 的 `0xD5A5E0`） |
| 12 | ★★★ `[obj+0x18]` | 早期应答首值（`0xB9A5CE`） |
| 13 | ★★★★★ `[obj+0xD8]` | **票据首 DWORD，必须 == `0xEFBDADDE`**（`0xB9A809`） |
| 14 | `[obj+0xC8/CC/D0]` | 后续写入（`0xB9A863/877/888`） |
| 15 | 扫描字段数 | **13 个**（日志只打印 12 个，漏 `0x168`） |
| 16 | 转储大小 | **`0x2400`（9216）字节** |

---

## 五、结论

### 1. ★★★★★ `secrets.txt` 的**七行格式**已完全定案

```
pid <PID>          ← ★ 判据（必须等于当前客户端 pid）
state <N>
challenge <hex>
aes_out <hex>
aes_in <hex>
hmac_out <hex>
hmac_in <hex>
```

### 2. ★★★ `os.replace` 原子写保证读端不读半文件

### 3. ★★★★★ `scan_dword` 只扫 `MEM_PRIVATE` 是**关键的规模控制**

★ **⇒ 与 `force_display_name.py` 的"扫所有可读区"形成对比（不同目的）。**

### 4. ★★★★★ `[obj+0xD8] == 0xEFBDADDE` 是**票据解析的验证点**

★★ **⇒ 与 `DE AD BD EF` 魔数直接对应。**

### 5. ★★ `auth` 对象的 vtable（`0xD5A2EC`）与 `svc`（`0xD5A5E0`）是**两个不同的类**

---

## 六、下一步

- `watch_dialogs`（第 888–949 行）
- `scan_playerstate_bases` / `read_playerstate`（第 950–1048 行）
- `_probe_tick_hz` / `_is_predicted` / `_live_score`（第 1049–1117 行）
- `playerstate_probe_thread`（第 1118–1318 行）
- `main()`（第 1319 行起）
