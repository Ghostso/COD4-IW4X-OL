# 学习报告 060（重开）— `runtime.md` 自动化工具链（第 249–358 行）

**学习范围**：`.agents\modules\runtime.md` 的"匹配自动化"与"Weapon movement 回归"两节
**性质**：全实测（**ol-mod 的自动化验证规范**）
**★★★ 本报告收录**十个运行时工具**与**六个精确的失败签名**

---

## 一、★★★★★ 十个运行时工具清单

| # | 工具 | 职责 |
|---|---|---|
| **1** | `CodolMemoryStrings.py` | 只读 ASCII 证据扫描（16 MiB chunk） |
| **2** | `CodolFridaRuntime.py` | Frida 解包目录管理 |
| **3** | **`CodolMatchFlow.py`** | QuickMatch / ready / allocation 编排 |
| **4** | **`CodolNaturalMatchTrace.py`** | ★★★ **自然匹配验证的统一生命周期入口** |
| **5** | `CodolNetchanTrace.py` | 主 packet log 追踪 |
| **6** | `CodolGameServerControl.py` | server watcher（`--watch-log`） |
| **7** | **`CodolClientInput.py`** | ★★ **真实 binding input 注入** |
| **8** | `CodolHudElemState.py` | 只读 HudElem 差分 |
| **9** | `CodolCaptureEvidence.py` | 原子写入 / framing / 离线校验 |
| **10** | `CodolFrameTrace.py` | ★ 相机与渲染节奏只读回归 |

★★★ **⇒ 十个工具，覆盖**启动 → 匹配 → 输入 → 证据捕获 → 校验**全链。**

---

## 二、★★★★★ `CodolMatchFlow.py` 的三条铁律

### 2.1 ★★★ `--action full` 的顺序（第 253 行，逐字）

```
`CodolMatchFlow.py --action full` 依次执行原生 QuickMatch、等待房间、
调用 room `SetReady(1)`，然后只观察 allocation。默认不直接调用 `0x006E4A20`。
```

★★ **⇒ 四步：QuickMatch → 等房间 → `SetReady(1)` → **只观察** allocation。**

★ **⇒ 且明确："默认**不直接调用** `0x006E4A20`"。**

### 2.2 ★★★★★ 窗口类名的**关键区分**（第 255 行，逐字）

```
开启 `OLMOD_CONSOLE_LOG=1` 时，同一客户端进程同时拥有 `ConsoleWindowClass` 控制台窗口
和类名为 `CODO` 的游戏窗口；`EnumWindows` 顺序受 Z-order 影响，不能取首个可见窗口。
`CodolMatchFlow` 现只选择 `CODO` 的 HWND/thread，缺失时等待并 fail closed。
修复前两客户端会随机有一端只报告 `armed`，因为 native 调用被约束到了控制台线程；
```

★★★★★ **⇒ 一个极其具体的 bug：**
```
OLMOD_CONSOLE_LOG=1
        ↓
同一进程有**两个窗口**：
  ConsoleWindowClass  （控制台）
  CODO                （游戏）
        ↓
EnumWindows 顺序受 Z-order 影响 ⇒ **不能取首个可见窗口**
        ↓
★★★ 修复前：native 调用被约束到**控制台线程**
        ↓
两客户端随机有一端只报告 `armed`
        ↓
★ 修复：**只选 `CODO` 的 HWND/thread**
```

### 2.3 ★★★ 双客户端成功验证（第 255 行）

```
修复后的 clean `mp_crash_tropical/sd` 双客户端运行让两端进入 `Playing`，
分别完成 14 秒 `gameplay_smoke`，随后
`.runtime/two-client-stability/20260816-190102.jsonl` 又持续推进 30 秒。
最终双方 `clientThink failure=none:0`、reliable 全确认、
player/clientInfo mask 均为 `3`，进程保持在线。
```

★★★ **⇒ 四项最终指标：**
```
① clientThink failure=none:0
② reliable 全确认
③ player/clientInfo mask 均为 3
④ 进程保持在线
```

★★ **⇒ 且诚实声明："综合输入只证明所列动作**没有破坏** transport/usercmd/snapshot，
仍不替代逐动作表现与模式完整性验证。"**

---

## 三、★★★★★ `CodolNaturalMatchTrace.py` 的**三重门槛**

### 3.1 ★★★ 完整的 readiness 判定（第 261 行，逐字）

```
`CodolNaturalMatchTrace.py` 是自然匹配验证的统一生命周期入口。
它可以选择 build/install 和 clean launch；对于本轮启动的客户端，
无副作用的 frontend probe 必须同时看到本轮自然 `ClientLoadTime` telemetry，
以及 `QuickMatch` 实际访问的 native objects、vtable slots 与方法地址
全部就绪且连续稳定，才允许继续。
client connection state 只记录为诊断信息，不参与 readiness 判定。
```

### ★★★★★ 三重门槛

```
① 本轮自然 `ClientLoadTime` telemetry
② `QuickMatch` 访问的 native objects / vtable slots / 方法地址
   全部就绪且**连续稳定**
③ （★ 明确排除）client connection state **不参与** readiness 判定
```

★★★ **⇒ 第 ③ 条是**关键的设计决策**：**
```
client connection state  =  0  **不阻碍** QuickMatch
        ↓
（第 297 行明确：2026-08-01 17:38 已在 `connection_state=0` 下
  直接闭环原生 QuickMatch、ready 和 client-native allocation）
        ↓
★ 因此 **PVP UI 导航不是生命周期依赖**
```

### 3.2 ★★★ 后续三个确认（第 261 行）

```
随后要求 `CodolNetchanTrace.py` 的主 packet log 出现脚本 `ready`，
并要求同一 Frida session 的低流量 Cbuf log 同时出现 `ready/attached`，
再以 `CodolGameServerControl.py --watch-log` 的单次持久 Frida session
确认 server watcher armed。
```

★★★ **⇒ 三个后续确认：**
```
① `CodolNetchanTrace.py` 主 packet log 出现 **`ready`**
② 同一 session 的 Cbuf log 出现 **`ready/attached`**
③ `CodolGameServerControl.py --watch-log` 确认 **server watcher armed**
```

### 3.3 ★★★★★ 两条**重要的失败教训**（第 261 行，逐字）

```
不要错误要求忙碌的主 packet log 也保留 Python-side `attached` append；
2026-08-04 实跑中该 marker 因并发落盘缺失，但同一文件已有数千个完整 parser event。

不要为每个 sample 反复 attach/detach；
该旧方式曾在 allocation 后触发 `frida-agent.dll` `0xC0000409` 崩溃。
```

★★★★ **⇒ 两条精确的教训：**

**教训 1：不要要求主 packet log 有 `attached`**
```
2026-08-04 实跑：该 marker 因**并发落盘**缺失
        ↓
但同一文件已有**数千个完整 parser event**
        ↓
★ 所以不能因为缺 `attached` 就判失败
```

**教训 2：不要反复 attach/detach**
```
旧方式：每个 sample 一次 attach/detach
        ↓
★★★ 曾在 allocation 后触发 `frida-agent.dll` **`0xC0000409`** 崩溃
        ↓
★ 必须用**单次持久 session**
```

---

## 四、★★★★★ `CodolClientInput.py` 的 binding input 机制（第 265 行）

### 4.1 ★★★ 为什么不用 `Cbuf_AddText`（第 265 行，逐字）

```
`CodolClientInput.py` 用 CODOL action table 与 `CL_ExecuteBindingAction` 触发真实 binding input，
而不是把没有 console handler 的 `+forward` 交给 `Cbuf_AddText`。
```

★★★ **⇒ 关键区别：**
```
Cbuf_AddText("+forward")   ⇒  ★ 没有 console handler ⇒ 无效
CL_ExecuteBindingAction    ⇒  ★ 真实 binding input
```

### 4.2 ★★★★★ 完整的 action 清单（第 265 行，逐字）

```
当前直接由 CODOL `s_bindingActionNames` 闭合的动作包括
ADS `+speed_throw/-speed_throw`、
冲刺 `+breath_sprint/-breath_sprint`、
专用换弹 `+reload/-reload`、
开火、四向移动、跳跃、蹲伏、匍匐和切枪；
`+usereload` 在实测缺弹状态下没有进入 reload weapon state，
不能代替专用换弹 action。
飞扑不伪造独立 binding，而由 scenario 在前进和冲刺期间组合 prone，
继续交给 native `Pmove` 判定。
```

### ★★★★★ 完整的 action 映射表

| 动作 | binding |
|---|---|
| **ADS** | **`+speed_throw` / `-speed_throw`** |
| **冲刺** | **`+breath_sprint` / `-breath_sprint`** |
| **专用换弹** | **`+reload` / `-reload`** |
| 开火 | （未列具体名） |
| 四向移动 | （未列） |
| 跳跃 / 蹲伏 / 匍匐 / 切枪 | （未列） |

★★★ **⇒ 三个精确的 binding 名（非常反直觉）：**
```
ADS   = +speed_throw     ← ★ 不是 +aim
冲刺  = +breath_sprint   ← ★ 不是 +sprint
换弹  = +reload
```

★★ **⇒ 且明确两个反例：**
```
① `+usereload` 在缺弹状态下**没有**进入 reload weapon state ⇒ 不能代替专用换弹
② 飞扑**不伪造**独立 binding ⇒ 由 scenario 组合 prone，交给 native `Pmove` 判定
```

### 4.3 ★★★ 单 session 的证据捕获（第 265 行）

```
工具在一个 Frida session 内完成 main-thread input timeline、超时 release、parser counters，
以及 server `192`-byte sample、client snapshot/prediction 的 opaque byte capture；
Python/JS 不解码这些状态或实现 movement/weapon/stance heuristics。
```

★★★ **⇒ 四个关键设计：**
```
① **单 session**（不反复 attach）
② ★ **server `192`-byte sample**（精确大小）
③ **opaque byte capture**（不解码）
④ ★★★ **Python/JS 不解码状态、不实现 heuristics**
```

★★ **⇒ 第 ④ 条是**重要的架构原则**：**
```
工具只做**捕获**，不做**解释**
        ↓
★ 避免把"能捕获"当成"理解了语义"
```

### 4.4 ★★★ 同锁复制（第 265 行，逐字）

```
`CODOL_GameServerGetWorldPlayerSampleV1` 仍在同一把 C++ 锁内一次复制
frame、last usercmd、world player 与 weapon scalars，
避免多个 getter 拼接跨帧状态。
```

★★★ **⇒ 一个**重要的并发设计**：**
```
在同一把 C++ 锁内**一次复制**四个量
（frame / last usercmd / world player / weapon scalars）
        ↓
★ 避免多个 getter 拼接**跨帧**状态
```

### 4.5 ★★★ 超时 release 的 RPC（第 265 行）

```
超时 release 必须调用 lowercase RPC `requestrelease`；
scenario 在 `Com_Frame` 完成最后一次 release/sample 后直接发送 terminal，
不再经过独立 capture-finalize RPC。
```

★★ **⇒ `requestrelease` 是**小写**的 RPC 名。**

---

## 五、★★★★★ `gameplay_smoke.json` 的定位（第 267 行，逐字）

```
`tools/runtime/scenarios/gameplay_smoke.json` 是 14 秒综合输入刺激，
覆盖 ADS、短点射、换弹、切枪、前进冲刺和蹲伏/匍匐切换。
它只用于在已有 Playing world 中快速发现 parser、usercmd、snapshot 或原生状态机回归；
多种动作共享同一窗口，不能替代用于归因的单动作 scenario，
也不能把通过结果解释为 gameplay 已完整还原。
```

★★★ **⇒ 14 秒，覆盖 6 类动作：**
```
ADS / 短点射 / 换弹 / 切枪 / 前进冲刺 / 蹲伏-匍匐切换
```

★★★ **⇒ 两条使用限制：**
```
① **不能替代**用于归因的**单动作 scenario**（多动作共享同一窗口）
② **不能把通过结果解释为 gameplay 已完整还原**
```

---

## 六、★★★★ `CodolHudElemState.py` 的定位（第 269 行）

```
`CodolHudElemState.py` 是只读 HudElem 差分工具。
它从活动 snapshot 读取 CODOL 的 `31 current + 31 archival` active prefix，
并按本体 `42` 项 descriptor 返回少量原始字段；不写客户端内存、不推断文字语义。
```

### ★★★★★ 三个精确数字

| # | 项 | 值 |
|---|---|---|
| **1** | active prefix | **`31 current + 31 archival`** |
| **2** | descriptor 项数 | **`42`** |
| **3** | 约束 | **不写内存、不推断文字语义** |

★★ **⇒ 且给出一条**排障方法论**（第 269 行）：**
```
定位"受击后错误出现战地指令完成"时，应在同一局内分别捕获受击前后结果，
先确定新增/变化的数组槽、type 和字段，再沿对应 server HudElem owner
与客户端 consumer 核对；
★ 不得根据屏幕文字直接清零某个未知字段。
```

---

## 七、★★★★★ 证据冻结与校验（第 271–277 行）

### 7.1 ★★★ 冻结流程（第 271 行，逐字）

```
综合 scenario 在父进程只读取和规范化一次，随后以独占创建方式冻结为本轮 run 的
`input_scenario.snapshot.json` 并记录 SHA-256；
子进程只读取该不可变副本并验证 digest。
```

★★★ **⇒ 三步冻结：**
```
① 父进程读取 + 规范化**一次**
② 以**独占创建**方式冻结为 `input_scenario.snapshot.json`
③ 记录 **SHA-256**
        ↓
子进程只读该副本 + 验证 digest
```

### 7.2 ★★★ 双文件输出（第 271 行）

```
指定 `--output` 时，JSON framing 增量写入 `client_input.samples.jsonl`，
Frida binary `_data` 原样写入相邻 `.samples.bin`；
每批 flush/fsync，sequence、segment offset/size/hash 连续校验，
崩溃尾部和 orphan bytes 可诊断恢复。
```

★★★ **⇒ 两个文件：**
```
client_input.samples.jsonl    ← JSON framing（元数据）
client_input.samples.bin      ← ★ Frida binary `_data` 原样
```

★★ **⇒ 且**每批 flush/fsync** + **sequence/offset/size/hash 连续校验**。**

### 7.3 ★★★ 父编排器的复核（第 271 行）

```
纯数据的原子写入、framing 和离线校验集中在 `CodolCaptureEvidence.py`，
父编排器在子进程退出后会重新读取 JSONL/blob、验证每段 hash
并与 scenario 和 child summary 对照，
不接受只保持相同文件大小的替换。
```

★★★ **⇒ 最后一句是**关键的完整性要求**：**
```
★ **不接受只保持相同文件大小的替换**
        ↓
（即：必须验证 hash，不能只比大小）
```

★★ **⇒ 这与交付包的 `deploy.ps1`"只比大小"**形成鲜明对比**（报告 013）。**

---

## 八、★★★★ `--forced-reliable-command` 的格式（第 279 行）

```
`--forced-reliable-command` 中的 menu response 必须使用原生四段格式
`mr <serverId> <menuIndex> <response>`；
`mr custom3` 只会形成畸形 reliable payload，现由入口直接拒绝。
```

★★★ **⇒ 精确的四段格式：**
```
mr <serverId> <menuIndex> <response>
```

★★ **⇒ 且明确：`mr custom3` 只有**三段** ⇒ 畸形 payload ⇒ 入口拒绝。**

### ★★★ 额外的 profile-aware guard（第 279 行）

```
发送 `customN/classN` 前，编排器还会读取当前 prepared character 的
`registered_class_mask`；明确未注册的 class 立即以 `ProtocolFailure` 退出，
不自动替换用户选择，也不把"menu 已解析但 loadout provider 无法提交"
误报为 gameplay 成功。
```

★★★ **⇒ 两个设计原则：**
```
① **不自动替换用户选择**（未注册 ⇒ 直接失败）
② **不把"menu 已解析但 loadout 无法提交"误报为成功**
```

---

## 九、★★★★★ `CodolFrameTrace.py` 的相机回归（第 303–305 行）

### 9.1 ★★★ 七个统计量（第 303 行）

```
`references/client_probe/CodolFrameTrace.py` 是相机与渲染节奏的唯一专用只读回归入口。
它在 `CG_CalcViewValues` 完成点逐帧统计
  两帧往返、角度大跳、viewaxis 正交性、roll 持续比例和 predicted-to-refdef 眼高，
并在 `view_state` 中保留 predicted `ground/view/link entity` 与 `playerSizeScale`。
```

★★★ **⇒ 五个逐帧统计 + 三个保留字段：**
```
统计：两帧往返 / 角度大跳 / viewaxis 正交性 / roll 持续比例 / 眼高
保留：ground entity / view entity / link entity / playerSizeScale
```

### 9.2 ★★★ 抖动判据（第 303 行）

```
prediction 聚合还分别统计 predicted 到 `snap/nextSnap` 的距离、`snap -> nextSnap` 距离、
snapshot 间隔，以及 snapshot 推进边界帧与普通帧的 refdef 位移、加速度和方向反转；
大于 `128` units 的出生/传送 discontinuity 不参与抖动导数。
```

★★★ **⇒ 一个精确阈值：**大于 `128` units 的出生/传送 discontinuity **不参与**抖动导数**。**

### 9.3 ★★★★★ v5 的完整实测（第 305 行，逐字）

```
clean run `.runtime/natural-match/20260810_movement_jitter_trace_v5/match/`
使用 `release -> forward down 4 s -> up`，先清除出生后的 `pm_flags 0x400` release gate，
再完整执行输入；parser `115/115`、accepted `115`、零 reject/overflow/`Com_Error`。
566 个 Playing 帧内 snapshot 固定每 `50 ms` 推进，
边界帧/普通帧平均位移分别为 `0.361/0.349`，平均加速度为 `0.036/0.026`，
两类方向反转均为 `0`，`snapshot_correlated_jitter_detected=false`。
```

### ★★★★★ 完整的实测数据

| 项 | 值 |
|---|---|
| 输入序列 | **`release -> forward down 4 s -> up`** |
| ★ `pm_flags 0x400` | **release gate**（出生后需先清除） |
| parser | **`115/115`** |
| accepted | **`115`** |
| reject / overflow / `Com_Error` | **全零** |
| Playing 帧数 | **566** |
| snapshot 间隔 | **固定每 `50 ms`** |
| ★ 边界帧位移 | **`0.361`** |
| ★ 普通帧位移 | **`0.349`** |
| ★ 边界帧加速度 | **`0.036`** |
| ★ 普通帧加速度 | **`0.026`** |
| 方向反转 | **`0`** |
| ★★★ 结论 | **`snapshot_correlated_jitter_detected=false`** |

★★★ **⇒ 这是一个**极其精确的定量结论**：**
```
边界帧 vs 普通帧：
  位移  0.361 vs 0.349   （差 3.4%）
  加速度 0.036 vs 0.026   （差 38%）
  方向反转 0 vs 0
        ↓
★★★ **没有证据把抖动归因于 20 Hz snapshot 周期性回拉**
```

### 9.4 ★★★ 诚实的边界（第 305 行）

```
因此当前没有证据把移动时第一人称模型的轻微抖动归因于 20 Hz snapshot 周期性回拉；
该 probe 尚未测量 viewmodel 自身的 bob/weapon movement transform，
也没有施加可重复鼠标转向输入，不能用此结果宣称第一人称模型或鼠标响应已经正常。
```

★★ **⇒ 三项未覆盖：**
```
① viewmodel 自身的 bob / weapon movement transform
② 可重复的鼠标转向输入
③ 第一人称模型/鼠标响应是否正常
```

---

## 十、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★ 工具数 | **10 个** |
| 2 | ★★ `CodolMatchFlow --action full` | QuickMatch → 等房间 → `SetReady(1)` → **只观察** allocation |
| 3 | ★ 默认不调用 | **`0x006E4A20`** |
| 4 | ★★★★ **窗口类名** | **`ConsoleWindowClass`** vs **`CODO`**（只选后者） |
| 5 | ★★★ 修复前 bug | native 调用被约束到**控制台线程** ⇒ 随机一端只报 `armed` |
| 6 | ★★ 双客户端成功 | `clientThink failure=none:0` / reliable 全确认 / mask 均为 **`3`** |
| 7 | ★★★★★ **三重门槛** | `ClientLoadTime` telemetry + QuickMatch native 就绪稳定 + **connection state 不参与** |
| 8 | ★★ 三个后续确认 | packet log `ready` / Cbuf `ready/attached` / server watcher armed |
| 9 | ★★★★ **教训 1** | **不要要求主 packet log 有 `attached`**（并发落盘缺失） |
| 10 | ★★★★★ **教训 2** | **不要反复 attach/detach** ⇒ **`frida-agent.dll` `0xC0000409`** |
| 11 | ★★★★★ **binding 名** | ADS=**`+speed_throw`** / 冲刺=**`+breath_sprint`** / 换弹=**`+reload`** |
| 12 | ★★ `+usereload` | **缺弹时无效** ⇒ 不能代替专用换弹 |
| 13 | ★★★ server sample | **`192` 字节** |
| 14 | ★★★★ **架构原则** | **Python/JS 不解码状态、不实现 heuristics** |
| 15 | ★★★ 同锁复制 | frame + last usercmd + world player + weapon scalars **一次复制** |
| 16 | ★ 超时 RPC | **`requestrelease`**（小写） |
| 17 | ★★ `gameplay_smoke` | **14 秒 / 6 类动作** |
| 18 | ★★★ HudElem | **`31 current + 31 archival`** / **`42` 项 descriptor** |
| 19 | ★★★ 证据冻结 | **独占创建 + SHA-256**，**不接受同大小替换** |
| 20 | ★★ menu response 格式 | **`mr <serverId> <menuIndex> <response>`**（四段） |
| 21 | ★★★ 抖动实测 | parser **`115/115`** / 566 帧 / snapshot 每 **`50 ms`** |
| 22 | ★★★★★ **抖动结论** | **`snapshot_correlated_jitter_detected=false`**（位移 0.361 vs 0.349） |
| 23 | ★ discontinuity 阈值 | **`128` units** 不参与抖动导数 |

---

## 十一、结论

### 1. ★★★★★ **两条 Frida 教训极其宝贵**

```
① 不要要求主 packet log 有 `attached`（并发落盘会缺）
② 不要反复 attach/detach ⇒ `frida-agent.dll` `0xC0000409`
```

### 2. ★★★★★ **`ConsoleWindowClass` vs `CODO` 的窗口选择 bug**

★ **⇒ 修复前随机一端只报 `armed`（native 调用被约束到控制台线程）。**

### 3. ★★★★ **binding 名非常反直觉**：ADS=`+speed_throw`，冲刺=`+breath_sprint`

### 4. ★★★★ **"Python/JS 不解码状态、不实现 heuristics"** 是核心架构原则

★ **⇒ 工具只做捕获，不做解释。**

### 5. ★★★ **证据完整性必须验证 hash，不接受同大小替换**

★ **⇒ 与交付包的 `deploy.ps1`"只比大小"**形成鲜明对比**。**

### 6. ★★★ **抖动已定量排除**（`snapshot_correlated_jitter_detected=false`）

---

## 十二、下一步

- `runtime.md` 剩余（第 358 行起，约 640 行）
- `source\.agents\modules\game_server.md`（223 KB）
- `source\docs\devlog\`（中文开发历程）
