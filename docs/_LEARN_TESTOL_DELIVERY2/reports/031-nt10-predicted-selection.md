# 学习报告 031（重开）— `nt10.py` 预测态三级选择 + 原始字节 dump

**学习范围**：第 1222–1318 行（三级选择逻辑 + dump + 日志）
**性质**：全实测
**★★★ 本报告收录**预测态的三级选择策略**（含"z 离群"这个巧妙的判据）

---

## 一、★★★ 第二重过滤（第 1222–1224 行）

```python
if any((v != v or abs(v) > 100000.0)
       for v in (ps["x"], ps["y"], ps["z"], ps["pitch"], ps["yaw"], ps["roll"])):
    continue
good.append((b, ps))
```

★★ **⇒ 检查 **6 个字段**（3 个位置 + 3 个角度）。**

★ **⇒ 比阶段 ① 的检查多了 `pitch`/`yaw`/`roll`。**

---

## 二、★★★★★ 预测态的**三级选择策略**（第 1226–1251 行）

### 2.1 ★★★ 完整说明（第 1226–1231 行，逐字）

```python
# ★ 选"预测态"（2026-10-04 加固；见手册 §13.53.4）：
#   ① 首选 **z 与众数不同** —— 权威副本的 z 恒等于我们下发的常量（当前 -116.00），
#      而预测态的 z 是客户端自己算的（实测 -99.6 / -123.9），天然是离群值；
#   ② 退路一：`_is_predicted()`（f2c != 0 或 pm_flags ∉ {0, 0x10}）；
#   ③ 退路二（本轮新增）：**commandTime 最新** —— 预测态每帧被 usercmd 推进，
#      权威副本只在收到我们快照时更新 ⇒ 上一轮 `★=0` 那种全落空的情况由它兜住。
```

### ★★★★★ 三级策略（完整）

| 级别 | 判据 | 依据 |
|---|---|---|
| **①（首选）** | **z 与众数不同** | 权威副本的 z 恒等于我们下发的常量（**-116.00**），预测态的 z 是客户端自己算的（**-99.6 / -123.9**） |
| **②（退路一）** | `_is_predicted()`（`f2c != 0` 或 `pm_flags ∉ {0, 0x10}`） | 结构特征 |
| **③（退路二，本轮新增）** | **`commandTime` 最新** | 预测态每帧被 usercmd 推进 |

★★★★★ **⇒ 第 ① 级是**最巧妙的设计**：**
```
权威副本的 z = 我们下发的常量（-116.00，恒定）
        ↓
预测态的 z = 客户端自己算的（-99.6 / -123.9，会变）
        ↓
★ **z 的众数 = 权威副本的值**
★ **z 的离群值 = 预测态**
```

★★★ **⇒ 这与记忆里的"`pos_z` 恒为初值 -116"**完全吻合**：**
> 记忆 `codol-spawn-server-authoritative-position`：
> "**从不积分 z**（`:698` 只有 `pos_x/pos_y += vel*dt`），`pos_z` 恒为初值 **-116**"

★ **⇒ 所以权威副本的 z **恒等于 -116.00** ⇒ 众数就是它。**

★★ **⇒ 而预测态的 z 是**客户端自己算的**（`-99.6` / `-123.9`）。**

### 2.2 ★★★ 三级实现（第 1232–1251 行）

```python
_zs = [q["z"] for _b, q in good]
_mode_z = max(set(_zs), key=_zs.count) if _zs else None      # ★ 求众数
_ranked = sorted(good, key=lambda t: _live_score(t[1]), reverse=True)

# ① z 离群
_how = ""
for _b, _ps in good:
    if _mode_z is not None and abs(_ps["z"] - _mode_z) > 1.0:   # ★ 阈值 1.0
        pred_base = _b
        _how = "z 离群 %.2f vs 众数 %.2f" % (_ps["z"], _mode_z)
        break

# ② _is_predicted
if pred_base is None:
    for _b, _ps in good:
        if _is_predicted(_ps):
            pred_base = _b
            _how = "pm_flags=0x%X f2c=%d" % (_ps["pm_flags"], _ps["f2c"])
            break

# ③ commandTime 最新
if pred_base is None and len(_ranked) >= 2 \
        and _ranked[0][1]["command_time"] > _ranked[1][1]["command_time"]:
    pred_base = _ranked[0][0]
    _how = "commandTime 最新 %d > %d" % (_ranked[0][1]["command_time"],
                                        _ranked[1][1]["command_time"])
```

★★★ **⇒ 三个细节：**
```
① 众数用 max(set(_zs), key=_zs.count)     ← 简洁的众数求法
② z 离群阈值 = **1.0**                    ← 超过 1 单位就算离群
③ 第 ③ 级要求 **严格大于**（不是 >=）      ← 避免平局时误判
```

★★ **⇒ 第 ③ 级的 `> ` 很关键：如果两个 `command_time` 相等，**不选**（避免误判）。**

### 2.3 ★★★ 找到后的日志（第 1252–1258 行）

```python
if pred_base is not None:
    _ps = read_playerstate(h, pred_base) or good[0][1]
    log("  [PS] ★ 找到预测态 base=0x%08X (%s) origin=(%.1f, %.1f, %.1f) "
        "vel=(%.1f, %.1f, %.1f) pm_flags=0x%X f2c=%d -> 开始定点轮询"
        % (pred_base, _how, ...))
    _save_pred_base(pred_base)      # ★ 记下来：下一轮直接复用，不再靠猜
```

★★★ **⇒ `_save_pred_base` 把地址写入 `pred_base.txt` ——**下一轮直接复用**。**

---

## 三、★★★★★ 原始字节 dump（第 1259–1290 行）

### 3.1 ★★★ dump 的目的（第 1259–1260 行，逐字）

```python
# ★ 第一轮命中时把原始字节 dump 出来 —— 用来定位"真正的 origin 偏移"
#   （+0x30 读出来全是 0 时，要靠 dump 找真正的坐标三元组）
```

★★★ **⇒ 用途：当 `+0x30` 读出来**全是 0**时，靠 dump 找**真正的坐标偏移**。**

★ **⇒ 这是**偏移不确定时的排查手段**。**

### 3.2 ★★★ dump 的格式（第 1266–1275 行）

```python
with open(hx, "w", encoding="utf-8") as f:
    f.write("# playerstate 原始字节 dump（前 2 个候选，各 0x210 字节）\n")
    for b, ps in good[:2]:
        raw = rpm(h, b, 0x210)
        f.write("\n## base=0x%08X len=%d\n" % (b, len(raw)))
        for i in range(0, len(raw), 16):
            f.write("%04x  %-47s  %s\n" % (
                i,
                " ".join("%02x" % c for c in raw[i:i + 16]),
                "".join(chr(c) if 32 <= c < 127 else "." for c in raw[i:i + 16])))
```

★★★ **⇒ 标准的十六进制 dump 格式：**
```
<偏移:04x>  <16 字节十六进制:47 宽>  <ASCII 侧栏>
```

### 3.3 ★★★★★ **自动扫描"像坐标的 float 三元组"**（第 1276–1287 行）

```python
# 顺便把 0x00..0x200 里所有"像坐标的 float 三元组"列出来，方便肉眼定位
f.write("-- 候选 float 三元组（连续 3 个 |v|<20000 且非全 0 的 float）--\n")
for off in range(0, 0x200, 4):
    if off + 12 > len(raw):
        break
    try:
        a1, a2, a3 = struct.unpack_from("<3f", raw, off)
    except Exception:
        break
    if all(v == v and abs(v) < 20000.0 for v in (a1, a2, a3)) \
            and any(v != 0.0 for v in (a1, a2, a3)):
        f.write("   +0x%03x : %.3f %.3f %.3f\n" % (off, a1, a2, a3))
```

★★★★★ **⇒ 这是**极其聪明的辅助工具**：**
```
从 0x00 到 0x200，每 4 字节取 3 个连续 float
        ↓
过滤：三个都非 NaN 且 |v| < 20000，且**至少一个非零**
        ↓
★ 列出所有"像坐标的三元组"
        ↓
★ 肉眼一看就知道哪个偏移是真 origin
```

★★ **⇒ 阈值 `20000.0`（比地图 ±8192 宽，但排除了垃圾值）。**

★ **⇒ 只 dump **前 2 个候选**（`good[:2]`）。**

---

## 四、★★★ 完整日志落盘（第 1291–1315 行）

### 4.1 ★★★ `player_origin.txt` 的每行格式（第 1293–1303 行）

```python
with open(out, "a", encoding="utf-8") as f:
    for b, ps in good[:24]:
        f.write("t=%.1f base=0x%08X origin=%.2f %.2f %.2f "
                "vel=%.2f %.2f %.2f "
                "angles=%.3f %.3f %.3f commandTime=%d "
                "pm=%d/%d/%d f2c=%d\n"
                % (time.time() - t0, b, ps["x"], ps["y"], ps["z"],
                   ps["vx"], ps["vy"], ps["vz"],
                   ps["pitch"], ps["yaw"], ps["roll"], ps["command_time"],
                   ps["pm_type"], ps["pm_flags"], ps["other_flags"],
                   ps["f2c"]))
```

★★★ **⇒ 完整的行格式（13 个字段）：**
```
t=<秒>  base=0x<addr>  origin=<x> <y> <z>  vel=<vx> <vy> <vz>
angles=<pitch> <yaw> <roll>  commandTime=<n>
pm=<type>/<flags>/<other>  f2c=<n>
```

★ **⇒ 最多写 **24 个候选**（`good[:24]`）。**
★ **⇒ **追加写**（`"a"`）。**

### 4.2 ★★★ 每轮汇总日志（第 1306–1313 行）

```python
p0 = good[0][1]
_ors = {("%.1f,%.1f,%.1f" % (q["x"], q["y"], q["z"])) for _b, q in good}
log("  [PS] 第 %d 轮: %d 个 playerstate（不同 origin %d 种）; "
    "第一个 origin=(%.1f, %.1f, %.1f) vel=(%.1f, %.1f, %.1f) yaw=%.2f "
    "pm_type=%d pm_flags=0x%X"
    % (n, len(good), len(_ors), ...))
```

★★★ **⇒ **"不同 origin N 种"** 是一个关键指标：**
```
若只有 1 种 origin ⇒ 全是同一个（可能是权威副本的多个副本）
若有 2 种以上     ⇒ 有预测态（z 或 x/y 不同）
```

★ **⇒ 用 `%.1f` 精度去重（避免浮点微差）。**

### 4.3 ★★ 未找到时的日志节流（第 1314–1315 行）

```python
elif n <= 3 or n % 10 == 0:
    log("  [PS] 第 %d 轮: 未找到 playerstate" % n)
```

★★ **⇒ 前 3 轮每轮都记，之后**每 10 轮**记一次（避免刷屏）。**

---

## 五、★★★ `main()` 的六个参数（第 1319–1326 行）

```python
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=r"D:\repo\03-live\client\TESTOL")
    ap.add_argument("--exe", default="codoMP_client_shipRetail.exe")
    ap.add_argument("--mutex", default=r"Global\{5BD75B76-601A-4b20-80C8-D2317C94BB30}")
    ap.add_argument("--apis", default="connect,sendto,gethostbyname")
    ap.add_argument("--direct", default="")
    ap.add_argument("--delay", type=float, default=2.5)
```

### ★★★ 六个参数的默认值

| 参数 | 默认值 |
|---|---|
| `--root` | ★★★ **`D:\repo\03-live\client\TESTOL`**（作者机器） |
| `--exe` | `codoMP_client_shipRetail.exe` |
| `--mutex` | ★★ **`Global\{5BD75B76-601A-4b20-80C8-D2317C94BB30}`** |
| `--apis` | `connect,sendto,gethostbyname` |
| `--direct` | `""` |
| `--delay` | **`2.5`** ★（与 docstring 的"默认 delay 2.5s"一致） |

★★★ **⇒ `--delay` 默认 **2.5** —— 正是为了避开 t≈2s 的 TP3 检查（报告 020）。**

★★ **⇒ 而 `launch_chain.py` 传 `--delay 0` ⇒ **覆盖了这个默认值** ⇒ 撞上 TP3。**

★★★ **⇒ `--mutex` 的 `Global\` 前缀 = 跨会话命名空间。**

---

## 六、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | 第二重过滤 | 6 字段（x/y/z + pitch/yaw/roll） |
| 2 | ★★★★★ **三级选择 ①** | **z 与众数不同**（权威 -116.00 vs 预测 -99.6/-123.9） |
| 3 | ★★★ 三级选择 ② | `_is_predicted()`（`f2c != 0` 或 `pm_flags ∉ {0,0x10}`） |
| 4 | ★★★ 三级选择 ③ | **`commandTime` 最新**（严格 `>`） |
| 5 | 众数求法 | `max(set(_zs), key=_zs.count)` |
| 6 | z 离群阈值 | **`1.0`** |
| 7 | ★★★ dump 目的 | 当 `+0x30` 全是 0 时找真正的 origin 偏移 |
| 8 | dump 大小 | **`0x210`** 字节 × 2 个候选 |
| 9 | ★★★★★ **自动三元组扫描** | 0x00–0x200 每 4 字节，`\|v\|<20000` 且非全零 |
| 10 | ★★ `player_origin.txt` | 13 字段，最多 24 个候选，追加写 |
| 11 | ★★ 关键指标 | **"不同 origin N 种"** |
| 12 | 日志节流 | 前 3 轮 + 每 10 轮 |
| 13 | ★★ `--delay` 默认 | **`2.5`**（避开 TP3 的 t≈2s） |
| 14 | ★★★ `--root` 默认 | **`D:\repo\03-live\client\TESTOL`** |
| 15 | ★ `--mutex` | **`Global\{5BD75B76-...}`** |
| 16 | `--apis` 默认 | `connect,sendto,gethostbyname` |

---

## 七、结论

### 1. ★★★★★ "**z 离群**"是**最巧妙**的判据

★★★ **⇒ 利用了"权威副本的 z 恒为 -116"这个**已知常量**：**
```
z 众数   = 权威副本（-116.00，恒定）
z 离群值 = 预测态（客户端自己算的 -99.6 / -123.9）
```

★ **⇒ 这与记忆里"从不积分 z，pos_z 恒为 -116"**完全吻合**。**

### 2. ★★★ 三级策略**逐级兜底**，解决 ★=0

```
① z 离群       （最强，利用已知常量）
② 结构特征     （f2c / pm_flags）
③ commandTime  （兜底，总能区分）
```

### 3. ★★★★★ dump 的**自动三元组扫描**是极好的排查工具

★ **⇒ 不用人工看 hex，直接列出所有"像坐标"的偏移。**

### 4. ★★ `--delay` 默认 2.5 是为了避开 TP3，而 `launch_chain.py` 传 0 破坏了这个保护

### 5. ★★ `"不同 origin N 种"` 是判断"是否有预测态"的关键指标

---

## 八、下一步

- `main()` 剩余（第 1326 行起，约 50 行）
- `fake_auth_tls.py` / `stun_local.py` / `force_display_name.py`
- `bundle\` 五个证书文件
- `payload\` 四个插件 PE + 四个 loader 二进制
