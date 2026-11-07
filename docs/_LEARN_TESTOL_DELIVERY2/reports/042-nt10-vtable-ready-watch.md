# 学习报告 042（重开）— `nt10.py` vtable 打印、0x4C 目录偏移兜底、`ready_watch`

**学习范围**：第 2465–2564 行（vtable 打印 + 查找链兜底 + tag 长度回读 + ready_watch）
**性质**：全实测
**★★★ 本报告收录**0x8510/0x8250 的完整查找链**与**`lobby_ready.flag` 的就绪判据**

---

## 一、★★★★ vtable 打印（第 2465–2469 行）

```python
slots_txt = " ".join(
    "槽0x%02X=0x%08X" % (k * 4, v)
    for k, v in enumerate(struct.unpack("<16I", vd)))
got["vt"] = slots_txt
log("  [dump] vtable=0x%08X %s" % (vtp, slots_txt))
```

★★★ **⇒ 打印 16 个槽，格式 `槽0x00=0xXXXXXXXX`（槽偏移是 `k*4`）。**

★ **⇒ `struct.unpack("<16I", vd)` —— 一次解出 16 个 DWORD。**

---

## 二、★★★★★ 0x8510/0x8250 的**完整查找链**（第 2470–2487 行）

### 2.1 ★★★ 查找链的定义（第 2473–2474 行，逐字）

```python
# 0x8510/0x8250 查找链: [base + obj[0x4c] + (len-1)*4] → 目录项 → 条目 → 字段。
# 目录偏移存在 obj+0x4C。若为 0(游戏初始化没读), 从 key20 记录 value 兜底写入。
```

### ★★★★★ 四层查找链

```
① base + obj[0x4C] + (len-1)*4     ← ★ 目录项
② 目录项 → 条目
③ 条目 → 字段
④ 字段 = (len, value)
```

★★★ **⇒ 关键：**目录偏移存在 `obj+0x4C`**。**

★★ **⇒ 若 `obj+0x4C == 0`（游戏初始化时没读）⇒ **查找链断掉**。**

### 2.2 ★★★★★ 兜底写入（第 2475–2487 行）

```python
o4c = struct.unpack_from("<I", od, 0x4C)[0]
if not o4c:
    tbl_ptr = struct.unpack_from("<I", od, 0x18C8)[0]      # ★ table 指针
    if tbl_ptr:
        r20 = rpm(h, tbl_ptr + 19 * 4, 4)                  # ★ 读 table[19]
        v20 = struct.unpack("<I", r20)[0] if len(r20) == 4 else 0
        if v20:
            rr = rpm(h, view + v20 + 4, 4)                 # ★ view + v20 + 4
            dirv = struct.unpack("<I", rr)[0] if len(rr) == 4 else 0
            if dirv:
                wpm(h, obj + 0x4C, struct.pack("<I", dirv))    # ★ 写入 obj+0x4C
                o4c = dirv
                log("  [dump] 兜底写入 obj+0x4C = 0x%08X (目录偏移)" % dirv)
```

### ★★★★★ 兜底逻辑的完整推导

```
obj + 0x18C4  = view（记录基址）
obj + 0x18C8  = tbl_ptr（table 指针）
        ↓
读 tbl_ptr[19]（★ 第 20 项，索引 19）→ v20
        ↓
读 view + v20 + 4 → dirv（★ 跳过 4 字节 = key20 记录的 len 字段）
        ↓
★ 把 dirv 写入 obj + 0x4C（目录偏移）
```

★★★ **⇒ 这与报告 023 的嵌套结构**完全吻合**：**
```
key19 记录 → 存 E1 条目偏移
key20 记录 → len 字段 = E1 偏移
        ↓
tbl_ptr[19] = key19 记录的偏移（索引 19 = tag 19）
        ↓
view + v20 = key19 记录
view + v20 + 4 = ★ **跳过 len 字段，读 value**
```

★★★ **⇒ 但报告 023 说 key20 的 len 字段存 E1 偏移，这里读的是 key19 的 value（+4）。**

★ **⇒ 两种可能的解释：**
```
① 游戏用的是 key19 的 value（存 E1 偏移）
② 或者注释里的 "key20 记录" 与代码的 tbl_ptr[19] 是同一件事（索引混淆）
```

★★ **⇒ 无论哪种，**兜底逻辑是：从 table 的某个槽取出偏移，写进 `obj+0x4C`**。**

### 2.3 ★★ 兜底成功后的验证（第 2488–2495 行）

```python
if o4c and not got.get("o4c"):
    d4v = o4c
    dir_v = view + d4v
    dq = rpm(h, dir_v, 0x20)
    dqword = struct.unpack("<8I", dq) if len(dq) == 0x20 else ()
    got["o4c"] = True
    log("  [dump] obj+0x4C = 0x%08X (目录偏移) 目录@0x%08X 前8项 = %s"
        % (d4v, dir_v, " ".join("%X" % v for v in dqword)))
```

★★ **⇒ 读目录的前 **8 项**（`0x20` = 32 字节）并打印。**

---

## 三、★★★★★ tag 记录长度回读（第 2496–2511 行）

```python
magic = rpm(h, view, 4)                        # ★ 读魔数（应为 0x40）
rows = []
for tag in list(range(1, 32)):                 # ★ tag 1..31
    tb = rpm(h, tbl2 + (tag - 1) * 4, 4)       # ★ table[tag-1]
    if len(tb) < 4:
        break
    off = struct.unpack("<I", tb)[0]
    LB = rpm(h, view + off, 4)                 # ★ view + off = 记录 → 读 len
    rows.append("%d:%s" % (tag, struct.unpack("<I", LB)[0]
                           if len(LB) == 4 else "?"))
line = ("  [dump] obj=0x%08X view=0x%08X table=0x%08X 魔数=%s\n"
        "  [dump] tag:记录长度 = %s"
        % (obj, view, tbl2, magic.hex(" "), " ".join(rows)))
```

### ★★★★★ 完整的验证逻辑

```
① 读 view[0] = 魔数（应为 **0x40**）
② 对 tag = 1..31：
     off = tbl2[tag-1]         ← ★ table 索引是 tag-1（与报告 023 一致）
     len = view[off]           ← ★ 记录的第一个 DWORD 是 len
③ 打印 "tag:len" 列表
```

★★★ **⇒ 这是**验证"我们的镜像在游戏眼里长什么样"的直接方法**（第 2202 行注释）。**

★ **⇒ `range(1, 32)` —— 只查 **tag 1..31**（覆盖全部已知 tag）。**

★★ **⇒ 与报告 023 的镜像布局**完全一致**：**
```
table[tag-1] = 记录偏移
记录 +0 = len
记录 +4 = value
```

---

## 四、★★★★★ `ready_watch`：大厅就绪监视（第 2515–2561 行）

### 4.1 ★★★ 完整的机制说明（第 2516–2519 行，逐字）

```python
# ---- 大厅"就绪"监视 ----
# 客户端分发器(0xBA4440)只有在 [obj+0x5E8]==1 时才受理 0x81; 否则 push 9
# -> 0xBA3420 复位(就是我们看到的 ConnectionReset 10054)。
# 连接对象(开发者手册 §5.1): obj = [[0x08269774] + 0x4F4], 就绪态 = obj+0x5E8 == 1。
# 一旦到 1 就写 lobby_ready.flag, lobby_server.py 据此才发 0x81。
```

### ★★★★★ 五个精确信息

| # | 信息 | 值 |
|---|---|---|
| 1 | **客户端分发器** | **`0xBA4440`** |
| 2 | ★★★ **受理 `0x81` 的条件** | **`[obj+0x5E8] == 1`** |
| 3 | ★★★ **否则** | **push 9 → `0xBA3420` 复位 ⇒ `ConnectionReset 10054`** |
| 4 | 连接对象公式 | **`obj = [[0x08269774] + 0x4F4]`** |
| 5 | ★★★ **就绪态** | **`obj+0x5E8 == 1`** |

★★★ **⇒ 完整的因果链：**
```
客户端分发器 0xBA4440
        ↓
若 [obj+0x5E8] == 1  →  ★ 受理 0x81
若 != 1              →  push 9 → 0xBA3420 复位
                     →  ★★★ **ConnectionReset 10054**
```

★★★ **⇒ 这与上一轮 capstone 实测的 P4 函数（`0xBA3BA0` → `[esi+0x5E8]=3`）**直接相关**：**
```
P4 成功路径写 5E8 = 3
        ↓
但分发器要求 5E8 == 1
        ↓
★ 所以 5E8=3 时**不**受理 0x81？
```

★★ **⇒ 这揭示了一个**状态码的微妙差异**：**
```
5E8 == 1  →  受理 0x81（★ 握手阶段）
5E8 == 3  →  已连接（P4 写）
```

★★★ **⇒ 所以 `ready_watch` 等的 **`5E8 == 1`** 是**握手阶段的就绪**，**
**不是 `5E8 == 3`（已连接）。**

### 4.2 ★★★ `lobby_ready.flag` 的完整语义（第 2520–2522 行）

```python
LOBBY_OBJ_SLOT = 0x08269774
READY_FLAG = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "lobby_ready.flag")
```

★★★ **⇒ `lobby_ready.flag` 是 `nt10.py` 与 `lobby_server.py` 的**跨进程信号**：**
```
nt10.py 检测到 [obj+0x5E8] == 1
        ↓
写 lobby_ready.flag
        ↓
★ lobby_server.py 据此才发 0x81
```

### 4.3 ★★★ 监视循环（第 2524–2559 行）

```python
def ready_watch():
    prev, t_last = None, 0.0
    while not stop.is_set():
        obj, s5e8, sc8, raw = 0, None, None, "ERR"
        try:
            pv = rpm(h, LOBBY_OBJ_SLOT, 4)
            raw = pv.hex(" ") if pv else "ERR"
            base = struct.unpack("<I", pv)[0] if len(pv) == 4 else 0
            if base:
                ov = rpm(h, base + 0x4F4, 4)
                obj = struct.unpack("<I", ov)[0] if len(ov) == 4 else 0
            if obj:
                v1 = rpm(h, obj + 0x5E8, 4)
                v2 = rpm(h, obj + 0xC8, 4)
                if len(v1) == 4:
                    s5e8 = struct.unpack("<I", v1)[0]
                if len(v2) == 4:
                    sc8 = struct.unpack("<I", v2)[0]
        except Exception:
            raw = "EXC"
        cur = (obj, s5e8, sc8, raw)
        now = time.time()
        if cur != prev or now - t_last > 10:
            prev, t_last = cur, now
            log("  [ready] [0x%08X]=%s -> 连接对象=0x%08X 5E8=%s C8=%s"
                % (LOBBY_OBJ_SLOT, raw, obj, s5e8, sc8))
        try:
            if s5e8 == 1:
                with open(READY_FLAG, "w", encoding="ascii") as _rf:
                    _rf.write("obj=0x%08X 5E8=%s C8=%s\n" % (obj, s5e8, sc8))
            elif os.path.exists(READY_FLAG):
                os.remove(READY_FLAG)                    # ★ 不是 1 就删除
        except Exception:
            pass
        time.sleep(0.05)
```

### ★★★ 五个要点

| # | 要点 | 值 |
|---|---|---|
| 1 | 轮询间隔 | **`0.05` 秒**（与 secrets 快照同频） |
| 2 | ★ 链式读取 | `[0x08269774]` → `+0x4F4` → obj |
| 3 | 读两个字段 | **`obj+0x5E8`（state）/ `obj+0xC8`（主状态）** |
| 4 | ★★ 日志节流 | 变化 **或** 每 **10 秒** |
| 5 | ★★★ **标志管理** | **`5E8==1` 写入；否则**删除**** |

★★★ **⇒ 第 5 条是**关键的对称设计**：**
```
5E8 == 1  →  写 lobby_ready.flag
5E8 != 1  →  ★ **删除** lobby_ready.flag（如果存在）
```

★ **⇒ 保证 flag 的存在性**严格等价于** `5E8 == 1`。**

★★ **⇒ 日志格式与上一轮记忆里的 `[ready] [0x08269774]=18 cc 1c 39 -> 连接对象=0x391CE270 5E8=0 C8=1` **完全一致**。**

---

## 五、★★★ 主循环（第 2563–2564 行）

```python
while time.time() - t0 < a.secs:
    time.sleep(2)
```

★★★ **⇒ `a.secs` 默认 **60**（`nt10.py` 的 `--secs`），而 `launch_chain.py` 传 **2400**。**

★ **⇒ 每 2 秒检查一次是否超时。**

---

## 六、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | vtable 打印 | 16 个槽，格式 `槽0x00=0xXXXXXXXX` |
| 2 | ★★★ 查找链 | `[base + obj[0x4C] + (len-1)*4]` → 目录项 → 条目 → 字段 |
| 3 | ★★★ **目录偏移** | **`obj+0x4C`**（为 0 则查找链断） |
| 4 | ★ 兜底来源 | `tbl_ptr[19]` → `view + v20 + 4` |
| 5 | ★★ 兜底写入 | `wpm(obj + 0x4C, dirv)` |
| 6 | 目录验证 | 读前 **8 项**（`0x20` 字节） |
| 7 | ★★★ tag 回读 | `tbl2[tag-1]` → `view[off]` = **len** |
| 8 | tag 范围 | **1..31** |
| 9 | 魔数校验 | `view[0]` 应为 **`0x40`** |
| 10 | ★★★★★ **分发器** | **`0xBA4440`** |
| 11 | ★★★ **受理 0x81 条件** | **`[obj+0x5E8] == 1`** |
| 12 | ★★★ **否则** | push 9 → **`0xBA3420`** 复位 ⇒ **`ConnectionReset 10054`** |
| 13 | 连接对象公式 | **`obj = [[0x08269774] + 0x4F4]`** |
| 14 | ★★★ **`lobby_ready.flag`** | **`5E8==1` 写；否则删** |
| 15 | ready_watch 间隔 | **0.05 秒** |
| 16 | 日志节流 | 变化 **或** 每 **10 秒** |

---

## 七、结论

### 1. ★★★★★ **`[obj+0x5E8] == 1` 是受理 `0x81` 的唯一条件**

★★★ **⇒ 否则 push 9 → `0xBA3420` 复位 → `ConnectionReset 10054`。**

★ **⇒ 这解释了"我们发的 0x81 被客户端 RST"（报告 040）。**

### 2. ★★★★★ **`lobby_ready.flag` 是跨进程的握手信号**

```
nt10.py 检测 5E8==1 → 写 flag → lobby_server.py 据此发 0x81
```

### 3. ★★★ **`5E8 == 1`（握手就绪）与 `5E8 == 3`（已连接）是两个不同状态**

★ **⇒ 分发器只认 `== 1`。**

### 4. ★★★ **`obj+0x4C` 是目录偏移**，为 0 则 0x8510/0x8250 查找链断

★ **⇒ 需要从 `tbl_ptr[19]` 兜底写入。**

### 5. ★★ tag 记录长度回读是验证镜像正确性的**直接方法**

### 6. ★★ `ready_watch` 的 flag 管理是**对称的**（写/删）

---

## 八、下一步

- `nt10.py` 最后几行（第 2564 行起）
- `fake_auth_tls.py` / `stun_local.py` / `force_display_name.py`
- `bundle\` 五个证书文件
- `payload\` 四个插件 PE + 四个 loader 二进制
