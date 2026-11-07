# ICH-045 — Post-Gate UI/Subsystem → Engine Correlation

## 唯一目标

验证 ICH-044 发现的 post-gate 活动（iips DllMain → Text Services/IME → Resource/PicFace/isgpet）是否存在 Engine-side correlation。

## 判定

```text
ICH045_STATUS              = UI_BYPASS_CONFIRMED
ENGINE_CORRELATION         = NOT_OBSERVED
UI_SUBSYSTEM_ROLE          = PLATFORM_UI_BYPASS
NEXT_TARGET                = BASE_VM_CONTINUATION
```

## 证据

### A. 模块加载链

ICH-044 的 post-gate 模块完整链：

```text
t=7.875s (Gate crossed, 0ms)
  iips.dll (IIPS gate trigger)
  MSCTF.dll (Windows Text Services)
  MSVCP80/MSVCR80 (CRT)
  profapi.dll (Profile API)

t=7.955s (+80ms)
  TextShaping.dll (Windows text shaping)
  textinputframework.dll (Windows IME)
  CoreUIComponents.dll / CoreMessaging.dll (Windows Core UI)
  ntmarta.dll / wintypes.dll (Windows security/types)
  SogouTSF.ime / SogouPY.ime / MSIMG32.dll (Sogou IME + GDI+)

t=8.050s (+175ms)
  isgpet_bundle.dll (WeGame IME component, NOT on disk)
  Resource.dll (WeGame UI resource, NOT on disk)
  PicFace.dll (WeGame UI PicFace, NOT on disk)
```

关键事实：**Resource.dll / PicFace.dll / isgpet_bundle.dll 不存在于 COD OL 游戏目录、
components/ 目录、WeGame 目录或磁盘上的任何位置**。它们是运行时从内存/网络
加载的 WeGame NBAPP 平台 UI 组件，与 Engine 无关。

### B. Engine-side correlation

在 post-gate 全程 22 秒的 monitoring 中：

```text
96-entry dispatch table changes = 0
RM vtable calls = 0
IIPS IsPackReady = 0
IIPS RequestPack = 0
loadfastfile = 0
Zone / Asset operations = 0
0x00E83C18 = 0x009B9C00 (stable, no change)
```

**Engine 在 post-gate 后没有执行任何新的 dispatch / RM / IIPS / FF / Zone / Asset 操作。**

### C. Thread correlation

Post-gate 共 16 个新线程（9 @ 0ms, 6 @ 80ms, 1 @ 175ms），全部 basePri=8。
这些线程全部与 iips DllMain、Windows Text Services、WeGame UI 初始化相关。
没有证据显示任何一个线程的 start address 位于 Engine gap 或调用了 dispatch table。

### D. Callback / export correlation

iips.dll 仅有 4 个 export（GetResourceManager / GetResourceManagerII / ReleaseResourceManager(II)），
其中 GetResourceManagerII 已被 Local RM patch 替换。没有发现任何 Engine gap 引用、
dispatch table 引用或 Base.dll 引用。

Resource.dll / PicFace.dll / isgpet_bundle.dll 不在磁盘上，无法进行静态检查。

### E. Window / message correlation

无 window creation / message 事件被捕获（passive observation only）。
但 MSCTF/IME/CoreUI 的加载强烈暗示 Windows Text Services 和 UI 消息循环
在 post-gate 80ms 内激活。这些活动属于 Windows 平台 UI 初始化，
不构成 Engine trigger。

## 判定依据

UI_BYPASS_CONFIRMED 的三个条件全部满足：

1. UI/Resource subsystem 活动明确（18 modules, 16 threads, +175ms 内完成）
2. 其后无新的 Engine execution（dispatch table 0 changes，22s 内无任何 Engine 侧变化）
3. 无 Engine callback / dispatch continuation / 可归因 Engine state transition

这意味着 ICH-044 发现的 post-gate UI/Resource 活动属于 **Platform/UI side initialization**（WeGame/NBAPP 平台层 + Windows IME/UI），**不是 Engine initialization trigger**。

## ICH-044 的 CANDIDATE 修正

ICH-044 将 post-gate UI/Resource 活动标为 TRIGGER_CANDIDATE。
ICH-045 通过深入分析确认：

1. Resource.dll / PicFace.dll / isgpet_bundle.dll 不在磁盘上 → WeGame 平台组件
2. Engine dispatch table 0 changes → Engine 没有响应这些模块加载
3. RM vtable 0 calls → Engine 没有调用 RM
4. 没有 Engine 侧任何状态变化

**结论：ICH-044 的 post-gate UI/Resource 链是 PLATFORM_UI_BYPASS，不是 Engine trigger。**

## Engine 在等什么

综合 ICH-037~045 全部证据，Engine 在 post-gate 后处于一种 stable standby 状态：

- dispatch table 已建立但无进一步调用
- RM 已提供但无 vtable 调用
- Windows UI/IME 子系统已激活但不触发 Engine
- 96 个 Engine function 已注册但未执行
- FF/Zone/Asset 代码已解密但未运行

**Engine 的下一步初始化由 Base VM 的 dispatch continuation 控制，而非任何
post-gate 的 platform/UI 事件触发。**

## 输出文件

- ICH045_MODULE_CHAIN.csv
- ICH045_THREAD_CORRELATION.csv
- ICH045_ENGINE_ACTIVITY.csv
- ICH045_CALLBACK_CANDIDATES.csv
- ICH045_WINDOW_EVENTS.csv
- ICH045_DECISION.md
