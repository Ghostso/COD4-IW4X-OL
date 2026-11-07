# 学习报告 028（重开）— `nt10.py` 对话框监视 + playerstate 扫描（含误收事故）

**学习范围**：`watch_dialogs`（888–944）+ `scan_playerstate_bases`（950–1002）
**性质**：全实测
**★★★ 本报告收录一次**真实的误收事故**与**双重判据的设计**

---

## 一、★★★ `watch_dialogs`（第 888–944 行）

### 1.1 ★★★ 设计声明（第 889–890 行，逐字）

```python
def watch_dialogs(pid, t_launch, log, stop):
    """盯游戏自己的 #32770 对话框(错误弹窗), 出现就记下【时刻 + 文字】。
    只调 user32 枚举窗口, 不读游戏内存, 零风险。"""
```

★★★ **⇒ **"只调 user32 枚举窗口, 不读游戏内存, 零风险"** ——**
**这是全文件唯一一个**完全不碰游戏内存**的探针。**

★ **⇒ `#32770` 是 Win32 的**标准对话框窗口类名**（`DIALOG`）。**

### 1.2 ★★★ 四个 API 签名（第 893–897 行）

```python
u.GetWindowTextW.argtypes = [W.HWND, W.LPWSTR, ctypes.c_int]
u.GetClassNameW.argtypes = [W.HWND, W.LPWSTR, ctypes.c_int]
u.GetWindowThreadProcessId.argtypes = [W.HWND, ctypes.POINTER(W.DWORD)]
u.EnumWindows.argtypes = [ctypes.c_void_p, W.LPARAM]
u.EnumChildWindows.argtypes = [W.HWND, ctypes.c_void_p, W.LPARAM]
```

★★ **⇒ 五个 API：窗口文本 / 类名 / 进程 ID / 枚举顶层 / 枚举子窗口。**

### 1.3 ★★★ 核心回调（第 910–928 行）

```python
def _cb(h, l):
    wp = W.DWORD(0)
    u.GetWindowThreadProcessId(h, ctypes.byref(wp))
    if wp.value == pid and _cls(h) == "#32770":      # ★ 双条件
        kids = []
        def _ck(k, ll):
            t = _txt(k)
            if t:
                kids.append(t)
            return True
        ck = ctypes.WINFUNCTYPE(ctypes.c_bool, W.HWND, W.LPARAM)(_ck)
        try:
            u.EnumChildWindows(h, ck, 0)
        except Exception:
            pass
        found.append((int(h) if h else 0, _txt(h), kids))
    return True
```

★★★ **⇒ 双条件过滤：**
```
① wp.value == pid      ← 属于目标进程
② _cls(h) == "#32770"  ← 是对话框类
```

★ **⇒ 然后枚举**子控件**的文字（`kids`）—— 弹窗正文往往在子控件里。**

### 1.4 ★★ 去重与轮询（第 931–944 行）

```python
seen = set()
while not stop.is_set():
    del found[:]
    try:
        u.EnumWindows(cb, 0)
    except Exception:
        pass
    for h, t, kids in found:
        if h in seen:
            continue
        seen.add(h)                                  # ★ 按 hwnd 去重
        log("  [dlg] ★ t=%.1fs 弹出 #32770 hwnd=0x%X 标题=%r 子控件=%s"
            % (time.time() - t_launch, h, t, kids[:4]))
    time.sleep(0.4)
```

★★★ **⇒ 三个要点：**
```
① seen 集合按 hwnd 去重（★ 同一个弹窗只记一次）
② 记录 **相对启动时刻**（t = time.time() - t_launch）
③ 只打印**前 4 个子控件**（kids[:4]）
```

★ **⇒ 轮询间隔 **0.4 秒**（与 docstring 的"每 0.4s 落盘"一致）。**

★★ **⇒ `stop` 是 `threading.Event`（外部控制停止）。**

---

## 二、★★★★★ `scan_playerstate_bases`（第 950–1002 行）

### 2.1 ★★★ 锚点定义（第 951–957 行，逐字）

```python
def scan_playerstate_bases(h, maxtime=8.0, cap=64):
    """★ 扫【私有可提交】内存找本地 playerstate（返回基址列表）。

    锚点（来自参考产物 `playerstate-fields.json`，并用 `gameplay-playerstate.bin` 实证）：
        +0xa4 = gravity(800)   +0xb0 = movementSpeed(190)
        +0xc0 = cameraEntity(2047)   +0x1fc = groundEntity(2047)
    主判据 = 「+0xa4 处 800」且「+12 处 190」；备用判据 = 「+0x1c 处 2047 且 +0x158 处 2047」。
    """
```

★★★★★ **⇒ 四个锚点字段（含精确偏移和值）：**

| 偏移 | 字段 | 值 |
|---|---|---|
| **`+0xa4`** | **`gravity`** | **800** |
| **`+0xb0`** | **`movementSpeed`** | **190** |
| **`+0xc0`** | **`cameraEntity`** | **2047** |
| **`+0x1fc`** | **`groundEntity`** | **2047** |

★★★ **⇒ 两个判据：**
```
主判据：+0xa4 == 800  且  +12(0x0C) == 190
备用判据：+0x1c == 2047  且  +0x158 == 2047
```

★★ **⇒ 注意：docstring 说 `+0xb0 = movementSpeed(190)`，但判据写的是 **`+12`** ——**
**这是**相对 `+0xa4` 的偏移**（`0xa4 + 12 = 0xb0`）。**

★★★ **⇒ 即：找到 `gravity=800` 的位置后，检查**它 +12 字节处**是否 == 190。**

★ **⇒ 同理，备用判据的 `+0x1c` / `+0x158` 是**相对某个基址**。**

### 2.2 ★★★ 三个搜索模式（第 958–960 行）

```python
grav = struct.pack("<I", 800)
mspd = struct.pack("<I", 190)
ent = struct.pack("<I", 2047)
```

★★ **⇒ 三个 4 字节模式。**

### 2.3 ★★★ 扫描逻辑（第 984–987 行）

```python
k = d.find(grav)
while k >= 0:
    ok = (d[k + 12:k + 16] == mspd)      # ★ gravity 之后 12 字节 == 190
    if ok:
        ...
```

★★★ **⇒ 先找 `gravity = 800`，再验证 `+12` 处是 `190`。**

### 2.4 ★★★★★ **误收事故**（第 988–994 行，逐字）

```python
# ★ 加严（2026-10-04 事故）：原来只靠 "gravity==800 且 speed==190"，
#   会误收"碰巧也是 800/190"的**别的结构**（实测误收过一批
#   pm_flags=0x18004000、origin=(-303.9,-2471.1,64.86) 的假货，
#   导致探针一整轮 ★=0、镜像全程回落）。
#   这里再用 playerstate 的其它已知字段交叉验证：
#     +0x0c pm_flags 必须是很小的位集   +0x30/0x34/0x38 origin 必须在地图范围内
#     +0xc0 cameraEntity / +0x1fc groundEntity 至少一个是 2047
```

★★★★★ **⇒ 一次**完整的误收事故记录**：**

| 项 | 值 |
|---|---|
| 日期 | **2026-10-04** |
| 原判据 | 只靠 `gravity==800` **且** `speed==190` |
| 误收对象 | **`pm_flags=0x18004000`**、**`origin=(-303.9, -2471.1, 64.86)`** |
| 后果 | ★★★ **"探针一整轮 ★=0、镜像全程回落"** |

★★★ **⇒ 三条**交叉验证**（加严后的判据）：**
```
① +0x0c pm_flags 必须是很小的位集
② +0x30/0x34/0x38 origin 必须在地图范围内
③ +0xc0 cameraEntity / +0x1fc groundEntity 至少一个是 2047
```

★ **⇒ 误收对象的 `pm_flags = 0x18004000` 是个**大值**（不在正常位集内）。**

### 2.5 ★★★ 三条交叉验证的实现（第 995–1002 行）

```python
b = k - 0xA4                                  # ★ 反推基址
if b >= 0 and b + 0x200 <= len(d):
    pmf = struct.unpack_from("<I", d, b + 0x0C)[0]
    ox, oy, oz = struct.unpack_from("<3f", d, b + 0x30)
    cam = struct.unpack_from("<I", d, b + 0xC0)[0]
    gnd = struct.unpack_from("<I", d, b + 0x1FC)[0]
    ok = (pmf < 0x10000
          and abs(ox) < 8192.0 and abs(oy) < 8192.0
```

★★★ **⇒ 四个精确判据：**
```python
pmf < 0x10000                                  # pm_flags 很小
abs(ox) < 8192.0 and abs(oy) < 8192.0          # origin 在地图内（±8192）
cam == 2047 或 gnd == 2047                     # 至少一个是 2047
```

★★ **⇒ `0x10000 = 65536` 是 `pm_flags` 的上限（位集最多 16 位）。**

★★★ **⇒ `±8192` 是**地图坐标范围**（CoD 地图通常是 ±8192 单位）。**

★ **⇒ 而误收对象的 `origin = (-303.9, -2471.1, 64.86)` **在这个范围内** ——**
**所以单靠 origin 判据**不能排除它**，必须靠 `pm_flags` 和 entity 判据。**

★★ **⇒ `b = k - 0xA4` —— 从 `gravity` 的位置**反推基址**。**

★ **⇒ 边界检查 `b >= 0 and b + 0x200 <= len(d)`（确保 `+0x1FC` 可读）。**

---

## 三、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★ `watch_dialogs` 性质 | **不读游戏内存，零风险** |
| 2 | 对话框类名 | **`#32770`** |
| 3 | 双条件 | `pid` 匹配 **且** 类名 == `#32770` |
| 4 | 去重 | 按 **hwnd** |
| 5 | 时间基准 | **相对启动时刻** |
| 6 | 轮询间隔 | **0.4 秒** |
| 7 | ★★★ playerstate 锚点 | `+0xa4`=800 / `+0xb0`=190 / `+0xc0`=2047 / `+0x1fc`=2047 |
| 8 | ★★ 主判据 | `+0xa4==800` **且** `+12==190` |
| 9 | ★★ 备用判据 | `+0x1c==2047` 且 `+0x158==2047` |
| 10 | ★★★★★ **误收事故** | **2026-10-04**，`pm_flags=0x18004000`，`origin=(-303.9,-2471.1,64.86)` |
| 11 | ★★★ 事故后果 | **探针一整轮 ★=0、镜像全程回落** |
| 12 | ★★★ 三条加严 | `pmf < 0x10000` / `abs(ox),abs(oy) < 8192` / `cam`或`gnd`==2047 |
| 13 | ★ 基址反推 | `b = k - 0xA4` |
| 14 | 边界检查 | `b >= 0 and b + 0x200 <= len(d)` |

---

## 四、结论

### 1. ★★★★★ 一次**真实的误收事故**被完整记录

```
只靠 "gravity==800 且 speed==190"
        ↓
误收 pm_flags=0x18004000 的**别的结构**
        ↓
★★★ 探针一整轮 ★=0、镜像全程回落
        ↓
加严：三条交叉验证
```

★★★ **⇒ 教训：**单靠两个数值锚点不足以定位结构，必须多点交叉验证。****

### 2. ★★★ `watch_dialogs` 是**唯一零风险探针**（不碰游戏内存）

★ **⇒ 抓的是**错误弹窗的原文和时刻** —— 直接可读的诊断信息。**

### 3. ★★★ `±8192` 是 CoD 的地图坐标范围

### 4. ★★ `pm_flags < 0x10000` 是位集上限（16 位）

### 5. ★★ 误收对象的 origin **在范围内** ⇒ 单靠 origin 排除不掉

---

## 五、下一步

- `scan_playerstate_bases` 剩余（第 1002–1016 行）
- `read_playerstate`（第 1017–1048 行）
- `_probe_tick_hz` / `_is_predicted` / `_live_score`（第 1049–1117 行）
- `playerstate_probe_thread`（第 1118–1318 行）
- `main()`（第 1319 行起）
