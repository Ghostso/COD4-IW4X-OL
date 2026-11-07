# 学习报告 029（重开）— `nt10.py` playerstate 完整字段表 + 预测态判据

**学习范围**：`scan_playerstate_bases` 尾部（1002–1014）+ `read_playerstate`（1017–1046）+ 六个辅助函数（1049–1116）
**性质**：全实测
**★★★ 本报告收录 playerstate 的**完整 20 字段偏移表**与**预测态的三重判据**

---

## 一、★★★ `scan_playerstate_bases` 尾部（第 1002–1014 行）

```python
                                      and abs(ox) < 8192.0 and abs(oy) < 8192.0
                                      and abs(oz) < 4096.0            ← ★★★ z 上限不同！
                                      and (cam == 2047 or gnd == 2047))
                            else:
                                ok = False
                        if ok:
                            hits.append(base + off + k - 0xA4)        # ★ 反推基址
                            if len(hits) >= cap:
                                return hits
                        k = d.find(grav, k + 4)
                off += want
        addr = base + size if size else addr + 0x1000
    return hits
```

### ★★★ 三个坐标上限**不同**

```python
abs(ox) < 8192.0
abs(oy) < 8192.0
abs(oz) < 4096.0        ← ★★★ z 只有 x/y 的一半
```

★★★ **⇒ z 轴范围是 ±4096，x/y 是 ±8192。**

★ **⇒ 这符合 CoD 地图的**扁平方形**特征（高度范围小于水平范围）。**

★★ **⇒ `hits.append(base + off + k - 0xA4)` —— 记录的是**基址**（不是 `gravity` 的位置）。**

★ **⇒ `cap = 64`（最多 64 个候选）。**

---

## 二、★★★★★ `read_playerstate` 的**完整字段表**（第 1017–1046 行）

### 2.1 ★★★ docstring 的追加说明（第 1020–1022 行，逐字）

```python
★ 2026-10-04 追加读取"物理/模拟"相关字段，用来判断客户端**是否愿意自己跑 Pmove**：
    +0x04 = pm_type      +0x08 = pm_time      +0x0c = pm_flags
    +0x10 = otherFlags   +0x14 = linkFlags    +0x2c = (idx12, changeHint=3)
```

★★★ **⇒ 六个"物理/模拟"字段，用途是"判断客户端是否愿意自己跑 Pmove"。**

★ **⇒ `Pmove` = CoD 的**玩家移动模拟**（player movement）。**

### 2.2 ★★★★★ 完整的 20 个字段偏移（逐行实测）

```python
w = rpm(h, base, 0x210)                       # ★ 读 0x210（528）字节
if len(w) < 0x210:
    return None
try:
    x, y, z          = struct.unpack_from("<3f", w, 0x30)     # origin
    pitch, yaw, roll = struct.unpack_from("<3f", w, 0x160)    # viewangles
    vx, vy, vz       = struct.unpack_from("<3f", w, 0x3C)     # velocity
    cmdtime          = struct.unpack_from("<I",  w, 0x00)[0]  # commandTime
```

★★★ **⇒ 完整的字段表：**

| 偏移 | 字段 | 类型 | 说明 |
|---|---|---|---|
| **`+0x00`** | `command_time` | u32 | ★ 命令时间戳 |
| **`+0x04`** | `pm_type` | u32 | 移动类型 |
| **`+0x08`** | `pm_time` | u32 | 移动时间 |
| **`+0x0C`** | `pm_flags` | u32 | ★★★ 移动标志（位集） |
| **`+0x10`** | `other_flags` | u32 | 其他标志 |
| **`+0x14`** | `link_flags` | u32 | 链接标志 |
| **`+0x2C`** | `f2c` | u32 | ★★★ 见 §四（"idx12, changeHint=3"） |
| **`+0x30`** | `origin` | 3×float | ★★★ 位置 (x, y, z) |
| **`+0x3C`** | `velocity` | 3×float | ★ 速度 (vx, vy, vz) |
| **`+0xA4`** | `gravity` | u32 | **800**（锚点） |
| **`+0xB0`** | `move_speed` | u32 | **190**（锚点） |
| **`+0xC0`** | `camera_entity` | u32 | **2047**（锚点） |
| **`+0x160`** | `viewangles` | 3×float | ★ pitch, yaw, roll |
| **`+0x1FC`** | `ground_entity` | u32 | **2047**（锚点） |

★★★ **⇒ 14 个字段，跨 `+0x00` 到 `+0x1FC`。**

★★ **⇒ 读取长度 `0x210`（528）字节 —— 覆盖到 `+0x1FC+4 = 0x200`，留 16 字节余量。**

### ★★★ `+0x2C` 的注释（第 1022 行）

```
+0x2c = (idx12, changeHint=3)
```

★★★ **⇒ `+0x2C` 是 `idx12` 字段，`changeHint = 3`。**

★★ **⇒ 这与上一轮记忆里的"实体 delta 编码"相关（`idx12`）。**

★ **⇒ 而 `f2c` 这个变量名 = **`field_to_client`**？**

---

## 三、★★★★ `_probe_tick_hz`（第 1049–1059 行）

```python
def _probe_tick_hz():
    """读 `tick_hz.txt`（与战斗服共用）；默认 **128 tick ≈ 7.8ms**（用户指定）。"""
    try:
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tick_hz.txt")
        if os.path.exists(p):
            v = float(open(p, "r", encoding="utf-8").read().replace(",", " ").split()[0])
            if 1.0 <= v <= 1000.0:
                return v
    except Exception:
        pass
    return 128.0


_PROBE_TICK = _probe_tick_hz()
_PROBE_POLL = 1.0 / _PROBE_TICK
```

★★★ **⇒ 三个要点：**
```
① 从 tick_hz.txt 读（★ 与战斗服共用同一个文件）
② 有效范围 [1.0, 1000.0]
③ ★ 默认 **128 tick**（≈ 7.8 ms）
```

★★ **⇒ `128 tick/s ⇒ 7.8125 ms/tick`。**

★★★ **⇒ "用户指定" —— 说明 128 是**甲方要求的**（不是从游戏推断的）。**

★ **⇒ `_PROBE_POLL = 1/128 ≈ 0.0078 秒`（7.8 ms）。**

---

## 四、★★★★★ `_is_predicted`（第 1066–1077 行）—— 预测态判据

### 4.1 ★★★ docstring 的完整判据（逐字）

```python
def _is_predicted(ps):
    """判"客户端预测态"（2026-10-04 实测修正版）。

    权威态（回声我们快照）：`f2c == 0` 且 `pm_flags ∈ {0, 0x10}`（0x10 = 我方 idx20 的开镜位）。
    预测态：实测 `pm_flags = 0x2020`、`f2c = 4`、并带下落速度。
    ⇒ 判据 = `f2c != 0` 或 `pm_flags ∉ {0, 0x10}`。（前一版只看 `pm_flags != 0` 会误判开镜时的权威态）
    ★ 另加"pm_flags 必须是很小的位集"（`< 0x10000`）：实测误收过一批假结构
      `pm_flags = 0x18004000`（配合 §13.54 的锚点加严一起用）。
    """
    if ps["pm_flags"] >= 0x10000 or ps["f2c"] >= 0x10000:
        return False
    return (ps["f2c"] != 0) or (ps["pm_flags"] not in (0, 0x10))
```

### 4.2 ★★★★★ 两种状态的**精确特征**

| 状态 | `f2c` | `pm_flags` | 其他 |
|---|---|---|---|
| **权威态**（回声我们快照） | **`0`** | **`∈ {0, 0x10}`** | `0x10` = 我方 idx20 的开镜位 |
| **预测态**（客户端自己算） | **`4`** | **`0x2020`** | 并带下落速度 |

★★★ **⇒ 两个精确的观测值：**
```
权威态：f2c=0,    pm_flags ∈ {0, 0x10}
预测态：f2c=4,    pm_flags = 0x2020
```

### 4.3 ★★★ 前一版的**误判**（第 1071 行）

> **前一版只看 `pm_flags != 0` 会误判开镜时的权威态**

★★★ **⇒ 原因：权威态在开镜时 `pm_flags = 0x10`（非 0）。**
**⇒ 只看 `!= 0` 会把它误判为预测态。**

★ **⇒ 修正：判据改成 `f2c != 0 或 pm_flags ∉ {0, 0x10}`。**

### 4.4 ★★★ 假结构的排除（第 1072–1076 行）

```python
if ps["pm_flags"] >= 0x10000 or ps["f2c"] >= 0x10000:
    return False
```

★★★ **⇒ 两个字段都必须 `< 0x10000`（65536）。**

★ **⇒ 与 `scan_playerstate_bases` 的加严一致（误收的 `pm_flags = 0x18004000`）。**

★★★ **⇒ `0x18004000 = 402,669,568` —— 远超 65536。**

---

## 五、★★★ `pred_base.txt` 的持久化（第 1080–1098 行）

```python
def _pred_base_file():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "pred_base.txt")


def _load_pred_base():
    """上一轮学到的预测态地址（exe 基址固定 0x400000，故静态 VA 稳定）。"""
    try:
        with open(_pred_base_file(), "r", encoding="utf-8") as f:
            return int(f.read().strip().split()[0], 0)
    except Exception:
        return None


def _save_pred_base(b):
    try:
        with open(_pred_base_file(), "w", encoding="utf-8") as f:
            f.write("0x%08X\n" % b)
    except Exception:
        pass
```

★★★ **⇒ 关键洞察（第 1085 行，逐字）：**
> **上一轮学到的预测态地址（`exe` 基址固定 `0x400000`，故静态 VA 稳定）**

★★★ **⇒ 因为客户端**不做 ASLR**（基址固定 `0x400000`），**
**所以上次找到的地址**下次仍然有效** ⇒ 可以缓存到文件。**

★ **⇒ 格式：`0x%08X\n`（十六进制，带 `0x` 前缀）。**

★★ **⇒ 这是**跨轮次学习**的机制 —— 上一轮的发现被持久化。**

---

## 六、★★★★ `_is_live_advancing` 与 `_live_score`（第 1101–1115 行）

### 6.1 `_is_live_advancing`（第 1101–1107 行）

```python
def _is_live_advancing(a, b):
    """a/b 为同一地址相隔 ~20ms 的两次读数：commandTime 必须严格推进(=每帧被 usercmd 喂的活结构)。"""
    if not a or not b:
        return False
    if b["command_time"] <= a["command_time"]:
        return False
    return not (b["x"] == 0.0 and b["y"] == 0.0 and b["z"] == 0.0)
```

★★★ **⇒ 两个判据：**
```
① b.command_time > a.command_time      ← 严格推进
② 且 origin 不全是 0                   ← 排除空结构
```

★ **⇒ 采样间隔 **~20 ms**。**

### 6.2 ★★★★★ `_live_score`（第 1110–1115 行）—— **三元组排序键**

```python
def _live_score(ps):
    """判"哪个是预测态"的主判据：commandTime 最新的那个（手册 §13.53.4 建议）。
    预测态每帧被 usercmd 推进，commandTime 必然领先/更新于"回声我们快照"的权威副本。"""
    moving = 1 if (ps["vx"] or ps["vy"] or ps["vz"]) else 0
    extra = 1 if ps["pm_flags"] not in (0, 0x10) else 0
    return (ps["command_time"], moving, extra)
```

★★★ **⇒ 返回三元组（字典序比较）：**
```python
(command_time, moving, extra)
```

| 分量 | 含义 |
|---|---|
| **`command_time`** | ★★★ **主判据**（最大者胜） |
| `moving` | 有速度 ⇒ 1 |
| `extra` | `pm_flags ∉ {0, 0x10}` ⇒ 1 |

★★★ **⇒ 核心逻辑（逐字）：**
> **预测态每帧被 usercmd 推进，commandTime 必然领先/更新于
> "回声我们快照"的权威副本。**

★ **⇒ 所以 `command_time` **最大**的那个就是预测态。**

★ **⇒ 出处：手册 §13.53.4。**

---

## 七、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★ 坐标上限 | **x/y ±8192，z ±4096**（z 只有一半） |
| 2 | 命中上限 | **64** |
| 3 | ★★★ 读取长度 | **`0x210`（528）字节** |
| 4 | ★★★ `command_time` | **`+0x00`** |
| 5 | ★★★ `pm_type/time/flags` | `+0x04` / `+0x08` / **`+0x0C`** |
| 6 | `other_flags` / `link_flags` | `+0x10` / `+0x14` |
| 7 | ★★ `f2c` | **`+0x2C`**（"idx12, changeHint=3"） |
| 8 | ★★★ `origin` | **`+0x30`**（3×float） |
| 9 | ★★ `velocity` | **`+0x3C`**（3×float） |
| 10 | 锚点 | `+0xA4`=800 / `+0xB0`=190 / `+0xC0`=2047 / `+0x1FC`=2047 |
| 11 | ★★★ `viewangles` | **`+0x160`**（pitch/yaw/roll） |
| 12 | ★★★ tick 默认 | **128**（≈ 7.8 ms，**用户指定**） |
| 13 | ★★★★★ 权威态特征 | **`f2c=0` 且 `pm_flags ∈ {0, 0x10}`** |
| 14 | ★★★★★ 预测态特征 | **`f2c=4` 且 `pm_flags=0x2020`** |
| 15 | ★★★ 前一版误判 | **只看 `pm_flags != 0` ⇒ 开镜时 `0x10` 被误判** |
| 16 | ★★★ 假结构 | **`pm_flags=0x18004000`**（≥ `0x10000` 排除） |
| 17 | ★★ 基址稳定性 | **exe 固定 `0x400000`，无 ASLR ⇒ 静态 VA 稳定** |
| 18 | ★ `_is_live_advancing` | `command_time` 严格推进 + origin 非全零 |
| 19 | ★★★★★ `_live_score` | **`(command_time, moving, extra)`** 三元组 |
| 20 | ★ 出处 | 手册 **§13.53.4** / **§13.54** |

---

## 八、结论

### 1. ★★★★★ playerstate 的**完整 14 字段偏移表**已定案

★★ **覆盖 `+0x00`（command_time）到 `+0x1FC`（ground_entity）。**

### 2. ★★★★★ 预测态与权威态的**精确区分**

```
权威态：f2c=0,    pm_flags ∈ {0, 0x10}
预测态：f2c=4,    pm_flags = 0x2020
```

★★★ **⇒ 且前一版"只看 `pm_flags != 0`"会**误判开镜时的权威态**（`0x10`）。**

### 3. ★★★ `command_time` 是**主判据**（预测态必然最新）

★ **⇒ 因为预测态每帧被 usercmd 推进。**

### 4. ★★★ `pred_base.txt` 利用了 **exe 无 ASLR** 的事实

★ **⇒ 上一轮的发现可以持久化复用。**

### 5. ★★ tick 默认 128 是**用户指定**（不是推断）

### 6. ★★ 误收的假结构 `pm_flags=0x18004000` 在两处都被排除

---

## 九、下一步

- `playerstate_probe_thread`（第 1118–1318 行，200 行）
- `main()`（第 1319 行起，约 60 行）
- 然后是 `fake_auth_tls.py` / `stun_local.py` / `force_display_name.py`
- `bundle\` 五个证书文件
- `payload\` 四个插件 PE + 四个 loader 二进制
