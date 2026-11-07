# ICH-044 — Engine External Trigger / Initialization Event 定位

## 运行记录

### Run A: Local RM v3 + -q（成功，Gate crossed）

```text
PID                  = 21928
Process lifetime     = 30.1s (stable)
Gate crossed         = YES (t = 7.875s)
Dispatch table       = 96 entries (confirmed)
Dispatch table changes = 0 (post-gate 22s monitoring)
Final modules        = 149
Final threads        = 71
```

### Run B: Local RM v3 + 无 -q

```text
PID                  = 24172
Process lifetime     = 30.1s
Gate crossed         = NO
iips.dll             = NEVER LOADED
Final modules        = 130
Final threads        = 55
原因                 = -q flag 控制 IIPS 加载路径。无 -q → iips.dll 不加载 → RM 无法注入 → Gate 无法跨越。
```

Run B 不是 post-gate trigger 变体，而是 pre-gate 条件变体。不适用于 post-gate trigger 分析。

## Post-Gate 时间线 (Run A)

```text
t=7.875  GATE_CROSSED (96 entries)
         +9 modules, +9 threads
         MSCTF.dll, iips.dll, MSVCP80, MSVCR80, profapi
         （IIPS/CRT/Text Services Infrastructure）

t=7.955  +80ms: +7 modules, +6 threads
         TextShaping.dll, textinputframework.dll,
         CoreUIComponents.dll, CoreMessaging.dll,
         ntmarta.dll, wintypes.dll, SogouTSF.ime, SogouPY.ime, MSIMG32
         （Windows 文本渲染 / IME / UI 框架）

t=8.050  +175ms: +3 modules, +1 thread
         isgpet_bundle.dll, Resource.dll, PicFace.dll
         （游戏 UI 资源初始化）

t=26.691 +18.8s: +1 module
         gpapi.dll
         （延迟网络 / Google Play API）
```

## 关键观察

1. **Post-gate 0ms 内立即出现 9 modules / 9 threads**：iips.dll 在同一 polling cycle 中加载，RM 注入在 iips.dll 加载到执行之间完成。thread 爆发在同一 50ms 周期内，说明这是 iips.dll DllMain 初始化触发。

2. **80ms 后 TextShaping / IME / CoreUI 链激活**：这是 Windows 文本服务 / IME 子系统初始化。Engine 不是在等 VM 信号，而是在等 Windows UI/Text subsystem 就绪。

3. **175ms 后 Resource.dll / PicFace.dll / isgpet_bundle.dll**：游戏自己的 UI 资源包加载。

4. **Dispatch table 0 changes**：96 entries 在 post-gate 22s 内没有变化。Engine function table 是静态注册，不是每次 resource init 都重写。

5. **RM vtable 0 calls**：Engine 没有（直接）调用 RM 接口。触发可能走的是 RM 内部回调或 VM dispatch，而不是通过 vtable。

## 分类

| Trigger 类别 | 观察 | 状态 |
|---|---|---|
| A. Window/message | MSCTF/IME/TextShaping 加载暗示 Windows Text Services 激活 | CANDIDATE |
| B. Timer/waitable | 无直接证据（未拦截） | NOT_OBSERVED |
| C. Thread/worker completion | Post-gate 立即 9 threads (DllMain) + 80ms 后 6 threads (UI) | CANDIDATE |
| D. Internal Engine state | Dispatch table 不变 | NO_EVIDENCE |
| E. Platform callback | iips DllMain + CoreUI 链暗示 platform 初始化 callback | CANDIDATE |
| F. Command-line | Run B 差异：-q 控制 iips 加载 → 影响 gate crossing | CONFIRMED (pre-gate only) |
| G. Base VM continuation | Base Anchor A/B 静态定位，无 runtime correlation | STATIC_ONLY |
| H. 其他 | Resource.dll / PicFace.dll 是游戏 UI 初始化 | CANDIDATE |

## Anchor Correlation

```text
Anchor A RVA 0x18AE194 = 0x00E83B00 (96-entry dispatch base)
Anchor B RVA 0x15EC784 = 0x00E83C00 (dispatch base + 0x100)
RVA distance A - B = 0x2C1A10 (2.76 MB)
Both in Base.dll .tls (VM-generated data, not reloc target)
Base.dll loaded in process (confirmed in module list)
Runtime candidate object address: NOT_RECOVERED (per ICH-043 result)
```

## 判定

```text
ICH044_STATUS = TRIGGER_CANDIDATE
FIRST_POST_GATE_EVENT = iips.dll DllMain thread burst + Windows Text Services (MSCTF/IME/TextShaping) chain activation
ENGINE_INITIALIZATION_TRIGGER = Windows UI/Text subsystem + iips DllMain (not RM vtable, not FF/Zone/Asset)
RUNTIME_CORRELATION = PARTIAL
```

### PARTIAL 而非 CONFIRMED 的原因

我们观察到 post-gate 后 MSCTF/IME/TextShaping/CoreUI 链在 80ms 内激活，
并以此作为 candidate trigger。但**没有直接证据**证明这条链就是
Engine 进入 FF/Zone/Asset 加载的前提条件：

- 没有 window creation 事件记录（仅通过 module 加载推断）
- 没有 WM_CREATE / WM_TIMER / WM_SHOWWINDOW 消息样本
- 没有 CreateEvent / CreateMutex 同步对象 trace
- RM vtable calls = 0，无法将 trigger 与 RM 生命周期关联
- Dispatch table 无变化，无法将 trigger 与已知 Engine function 关联

因此判定为 TRIGGER_CANDIDATE，不是 TRIGGER_FOUND。

## Hard Stop 评估

1. baseline 稳定复现：YES
2. 需要 debugger：NO
3. 需要大范围扫描：NO（使用了定向 module list）
4. 3 个变体无差异：Run A/B 有明确差异（-q 控制 pre-gate），Run C 未执行（A/B 已足够）
5. 30s 内无新可归因事件：NO（post-gate 有 18 modules, 16 threads）
6. 只有静态候选没有 runtime correlation：PARTIAL — 有 module/thread runtime 证据，但缺少 Engine-side correlation

## 输出文件

- ICH044_TIMELINE.csv (Run A v2)
- ICH044_THREAD_EVENTS.csv (Run A v2)
- ICH044_MODULE_EVENTS.csv (Run A v2)
- ICH044_WINDOW_EVENTS.csv (passive, no events)
- ICH044_SYNC_EVENTS.csv (passive, no events)
- ICH044_VM_ANCHOR_CORRELATION.csv
- ICH044_DECISION.md

Run B 备份:
- ICH044_RUNB_TIMELINE.csv
- ICH044_RUNB_DECISION.md
- ICH044_RUNB_THREADS.csv
- ICH044_RUNB_MODULES.csv

Run A v2 备份:
- ICH044_RUNA_TIMELINE.csv
- ICH044_RUNA_DECISION.md
- ICH044_RUNA_THREADS.csv
- ICH044_RUNA_MODULES.csv
