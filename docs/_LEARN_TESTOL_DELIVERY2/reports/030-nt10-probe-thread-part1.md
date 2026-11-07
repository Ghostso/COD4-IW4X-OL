# 学习报告 030（重开）— `nt10.py` `playerstate_probe_thread`（上）

**学习范围**：第 1118–1222 行（docstring + 三阶段状态机 + 定点轮询）
**性质**：全实测
**★★★ 本报告收录**三阶段状态机**与**"复用缓存地址"的 ★=0 根治方案**

---

## 一、★★★★★ docstring 的**用途说明**（第 1119–1125 行，逐字）

```python
"""★ 出生点/位置探针（2026-10-04）：周期性扫内存里的本地 playerstate，把 origin/角度落盘。

为什么需要它：`spawn_from_map.on` 是让客户端**在地图自带的几十个 mp_tdm_spawn 里自己挑**
出生点，服务端看不到它挑了哪个（挑到几何体里就"卡住走不动"）。读一次内存就能知道
"客户端实际落在哪"，再与地图出生点清单（`loaded-map-entities-19.txt`）对照。
结果写 `player_origin.txt`。
"""
```

★★★★★ **⇒ 完整的问题链：**
```
spawn_from_map.on 开启
        ↓
客户端在**地图自带的几十个 mp_tdm_spawn 里自己挑**出生点
        ↓
★ 服务端看不到它挑了哪个
        ↓
★★★ 挑到几何体里 ⇒ **"卡住走不动"**
        ↓
解法：读一次内存就知道"客户端实际落在哪"
        ↓
再与地图出生点清单（`loaded-map-entities-19.txt`）对照
```

★★★ **⇒ 这与记忆 `codol-spawn-server-authoritative-position` 的记载**完全吻合**：**
> "`omit=1` 语义上 = 参照的 `spawn_from_map.on`，而那份注释写明症状：
> 「客户端在地图自带的几十个 mp_tdm_spawn 里自己挑，**会挑到几何体/屋顶里 → 卡住走不动**」
> ——与实测逐字吻合。"

★ **⇒ 依据文件：`loaded-map-entities-19.txt`（19 张地图的实体清单）。**

---

## 二、★★★★★ 三阶段状态机（第 1163–1222 行）

### 2.1 阶段 ①：已定位 ⇒ 1 秒内 20ms 定点轮询（第 1165–1194 行）

```python
if pred_base is not None:
    t1 = time.time()
    while time.time() - t1 < 1.0 and time.time() - t0 < seconds:
        ps = read_playerstate(h, pred_base)
        # ★ 轮询期间**不再**用 pm_flags/f2c 复判 —— 实测它们在预测态里也会随玩家状态变化
        #   （0x20/0x4000/0x2…），会把稳定命中的地址误判成"失效"。只看读值是否有效。
        _bad = (ps is None)
        if not _bad:
            _vs = (ps["x"], ps["y"], ps["z"], ps["vx"], ps["vy"], ps["vz"])
            _bad = any(v != v or abs(v) > 100000.0 for v in _vs)
            if not _bad and ps["x"] == 0.0 and ps["y"] == 0.0 and ps["z"] == 0.0:
                _bad = True
        if _bad:
            log("  [PS] 预测态 0x%08X 读失败/越界 → 重新扫描" % pred_base)
            pred_base = None
            break
        _write_pred(ps)
        ...
        time.sleep(_PROBE_POLL)      # ★ 1/128 ≈ 7.8 ms
    continue
```

★★★★★ **⇒ 一条**极重要的实测发现**（第 1169–1170 行，逐字）：**
```python
# ★ 轮询期间**不再**用 pm_flags/f2c 复判 —— 实测它们在预测态里也会随玩家状态变化
#   （0x20/0x4000/0x2…），会把稳定命中的地址误判成"失效"。只看读值是否有效。
```

★★★ **⇒ **`pm_flags` 在预测态里会变化**（`0x20` / `0x4000` / `0x2`…）⇒**
**如果每轮都复判 `pm_flags`，会把**稳定命中的地址误判成失效**。**

★ **⇒ 所以轮询期间**只看读值有效性**（不是结构特征）。**

### 2.2 ★★★ 四条有效性判据（第 1171–1176 行）

```python
_bad = (ps is None)                                          # ① 读不到
if not _bad:
    _vs = (ps["x"], ps["y"], ps["z"], ps["vx"], ps["vy"], ps["vz"])
    _bad = any(v != v or abs(v) > 100000.0 for v in _vs)     # ② NaN 或越界
    if not _bad and ps["x"] == 0.0 and ps["y"] == 0.0 and ps["z"] == 0.0:
        _bad = True                                          # ③ origin 全零
```

★★★ **⇒ 三条判据：**
```
① ps is None                          ← 读失败
② v != v（NaN）或 |v| > 100000.0       ← 值非法
③ origin 全零                          ← 空结构
```

★ **⇒ `v != v` 是**检测 NaN 的标准技巧**（NaN != NaN 恒真）。**

★★ **⇒ `abs(v) > 100000.0` 是**越界上限**（远大于地图 ±8192）。**

### 2.3 ★★★ `_write_pred` 的二进制格式（第 1154–1161 行）

```python
def _write_pred(ps):
    try:
        pred_seq[0] = (pred_seq[0] + 1) & 0xFFFFFFFF
        with open(pred_file, "wb") as f:
            f.write(struct.pack("<6fI", ps["x"], ps["y"], ps["z"],
                                ps["vx"], ps["vy"], ps["vz"], pred_seq[0]))
    except Exception:
        pass
```

★★★★ **⇒ `predicted.bin` 的精确格式（28 字节）：**
```
偏移  类型      字段
0x00  float    x
0x04  float    y
0x08  float    z
0x0C  float    vx
0x10  float    vy
0x14  float    vz
0x18  uint32   seq（递增序号，& 0xFFFFFFFF）
---
      28 字节
```

★★★ **⇒ 结构：`<6fI` = 6 个 float + 1 个 uint32。**

★ **⇒ `pred_seq` 是**递增序号**（用于检测"是否新帧"）。**

★★ **⇒ 每次**覆盖写**（`"wb"`），不是追加 ⇒ 永远只有最新一帧。**

### 2.4 ★★★ 高速轨迹 `pred_trace.txt`（第 1182–1192 行）

```python
# ★ 高速轨迹：**每个 tick 都写**（128 tick ⇒ ≈7.8ms 一条），供抖动/穿墙定量分析
trace_n[0] += 1
if trace_fh[0] is not None:
    try:
        trace_fh[0].write("%.4f %.2f %.2f %.3f %.2f %.2f %.2f\n"
                          % (time.time() - t0, ps["x"], ps["y"], ps["z"],
                             ps["vx"], ps["vy"], ps["vz"]))
        if trace_n[0] % 64 == 0:
            trace_fh[0].flush()          # ★ 每 64 条 flush 一次
    except Exception:
        pass
time.sleep(_PROBE_POLL)
```

★★★ **⇒ 格式（7 列，空格分隔）：**
```
t x y z vx vy vz
```

★★ **⇒ 精度不同：`t` 用 `%.4f`，`x/y` 用 `%.2f`，`z` 用 `%.3f`，速度用 `%.2f`。**

★ **⇒ 每 **64 条** flush 一次（≈ 0.5 秒）。**

★★★ **⇒ 用途：**"供抖动/穿墙定量分析"。**

---

## 三、★★★★★ 阶段 ①.5：**复用缓存地址**（第 1195–1206 行）—— ★=0 的根治

```python
# ---------- ①.5 有缓存地址：先验证它还在被逐帧 tick（省掉整轮扫描，根除 ★=0） ----------
if _cached_base is not None:
    _a = read_playerstate(h, _cached_base)
    time.sleep(0.02)                              # ★ 间隔 20 ms
    _b = read_playerstate(h, _cached_base)
    if _is_live_advancing(_a, _b):
        pred_base = _cached_base
        log("  [PS] ★ 复用已学到的预测态 base=0x%08X (commandTime %d -> %d)"
            % (_cached_base, _a["command_time"], _b["command_time"]))
        continue
    log("  [PS] 缓存地址 0x%08X 已失效(commandTime 未推进) -> 重新扫描" % _cached_base)
    _cached_base = None
```

★★★★★ **⇒ 注释揭示了完整的目的（逐字）：**
```
省掉整轮扫描，★ 根除 ★=0
```

★★★ **⇒ "★=0" 是日志里的一个现象**（探针一整轮没有任何命中）。**
**⇒ 上一轮报告 028 的"误收事故"提到"探针一整轮 ★=0"。**

★★★ **⇒ 根治方案：**
```
缓存上一轮学到的地址（pred_base.txt）
        ↓
先**验证**它还在被逐帧 tick（两次读数，间隔 20ms）
        ↓
commandTime 推进 ⇒ 直接复用 ⇒ **省掉整轮扫描**
        ↓
★ 不再因为"扫描误收"而 ★=0
```

★ **⇒ `_is_live_advancing(_a, _b)` 就是报告 029 分析的那个函数。**

---

## 四、★★★ 阶段 ②：未定位 ⇒ 按 interval 扫描（第 1207–1222 行）

```python
# ---------- ② 未定位：按 interval 扫描 ----------
time.sleep(interval)                              # 默认 3.0 秒
n += 1
try:
    bases = scan_playerstate_bases(h, maxtime=6.0, cap=32)
except Exception as e:
    log("  [PS] 第 %d 轮 scan 异常: %r" % (n, e))
    continue
good = []
for b in bases:
    ps = read_playerstate(h, b)
    if ps is None:
        continue
    if not (ps["gravity"] == 800 and ps["move_speed"] == 190):
        continue
    if any((v != v or abs(v) > 100000.0)
```

★★★ **⇒ 三个参数：**
```
interval = 3.0 秒         ← 扫描间隔
maxtime = 6.0 秒          ← 单次扫描时限
cap = 32                  ← 最多 32 个候选
```

★★ **⇒ 三重过滤：**
```
① ps is None            ⇒ 跳过
② gravity != 800 或 move_speed != 190  ⇒ 跳过
③ 任一值 NaN 或 |v| > 100000           ⇒ 跳过
```

---

## 五、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★★★ 探针目的 | `spawn_from_map.on` 让客户端自选出生点，**挑到几何体里就卡住** |
| 2 | ★ 对照清单 | `loaded-map-entities-19.txt` |
| 3 | 输出文件 | `player_origin.txt` |
| 4 | ★★★ 阶段 ① | 已定位 ⇒ **1 秒内 20ms 定点轮询** |
| 5 | ★★★★★ **关键发现** | **轮询期间不能用 `pm_flags`/`f2c` 复判**（会变化） |
| 6 | ★ `pm_flags` 变化值 | `0x20` / `0x4000` / `0x2`… |
| 7 | 三条有效性判据 | `None` / NaN或`>100000` / origin 全零 |
| 8 | ★★ `predicted.bin` 格式 | **`<6fI` = 28 字节**（x,y,z,vx,vy,vz,seq） |
| 9 | ★ 写入方式 | **覆盖写**（永远只有最新一帧） |
| 10 | ★★ `pred_trace.txt` | **7 列**（t x y z vx vy vz），每 tick 一条 |
| 11 | flush 间隔 | **每 64 条** |
| 12 | ★★★★★ **阶段 ①.5** | **复用缓存地址，根除 ★=0** |
| 13 | 验证间隔 | **20 ms** 两次读数 |
| 14 | ★★ 阶段 ② | **interval=3.0s / maxtime=6.0s / cap=32** |

---

## 六、结论

### 1. ★★★★★ 探针的**真实用途**是诊断"卡在几何体里"

★★★ **⇒ `spawn_from_map.on` 让客户端自选出生点，服务端看不到选了哪个。**
**⇒ 读内存就知道"客户端实际落在哪"。**

### 2. ★★★★★ 一条**极重要的实测**：轮询期间不能复判 `pm_flags`

★★★ **⇒ `pm_flags` 在预测态里会随玩家状态变化（`0x20`/`0x4000`/`0x2`…）⇒**
**每轮复判会把稳定地址误判成失效。**

### 3. ★★★★★ **缓存地址 + 20ms 双读验证**根治了 ★=0

★★ **⇒ 省掉整轮扫描，避免扫描误收导致的假阴性。**

### 4. ★★ `predicted.bin` 是 28 字节的二进制格式（6 float + 1 seq）

### 5. ★★ `v != v` 是标准的 NaN 检测技巧

---

## 七、下一步

- `playerstate_probe_thread` 剩余（第 1222–1318 行，约 96 行）
- `main()`（第 1319 行起）
- 然后 `fake_auth_tls.py` / `stun_local.py` / `force_display_name.py`
- `bundle\` 五个证书文件
- `payload\` 四个插件 PE + 四个 loader 二进制
