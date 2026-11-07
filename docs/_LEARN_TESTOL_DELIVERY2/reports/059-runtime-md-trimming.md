# 学习报告 059（重开）— `runtime.md` dedicated 裁剪实验 v26–v51

**学习范围**：`.agents\modules\runtime.md` 第 120–249 行
**性质**：全实测（**极其严谨的实验日志**）
**★★★ 本报告收录**13 个裁剪实验的精确 RVA/字节**与**三次被证伪的方案**

---

## 一、★★★★★ 十三个裁剪实验的完整清单

| 版本 | 裁剪项 | 结果 |
|---|---|---|
| **v26/v28** | Audio startup（`SND_InitDriver` / `SND_Init`） | ★ **两者都退出** ⇒ 不能移植 |
| **v29** | `SND_InitDriver` 的 call | ✓ **成功**（`3 full + 403 delta`） |
| **v30** | Renderer（`CL_InitRenderer`） | ★★★ **失败**（到不了 control listener） |
| **v32** | 撤销 v30 | ✓ **恢复**（`4 full + 412 delta`） |
| **v34** | Window `SetFocus` | ✓ **成功**（`3 full + 409 delta`） |
| **v35** | Accessibility shortcut keys | ✓ **成功**（`3 full + 100 delta`） |
| **v36** | Cursor visibility | ✓ **成功**（`3 full + 80 delta`） |
| **v37** | Input frame（`IN_Frame`） | ✓ **成功**（`3 full + 86 delta`） |
| **v38** | `Com_StartHunkUsers` 完整跳过 | ★★★ **证伪**（`weapon_registry_unavailable`） |
| **v39** | 撤销 v38 | ✓ **恢复**（`4 full + 88 delta`） |
| **v40–v44** | 四个 common zone descriptor 替代 | ★★ **证伪**（`0xC0000005`） |
| **v51** | weapon-group root 只读 probe | ✓ **架构决策边界** |

★★★ **⇒ 13 个版本，**两次完整证伪 + 一次恢复 + 一次只读调查**。**

---

## 二、★★★★★ v29：`SND_InitDriver` 裁剪（成功的第一个）

### 2.1 ★★★ 三方对比（第 123–126 行，逐字）

```
BO1 将 `SND_InitDriver/SND_Init` 都放在 `!com_dedicated` 内，
Ghosts dedicated 也没有 sound startup；
CODOL 对应序列则是 `CL_InitRenderer -> SND_InitDriver -> SND_Init -> cls_soundStarted=1`。
```

### ★★★★★ 三方 dedicated 的 sound 处理

| 引擎 | sound startup |
|---|---|
| **BO1** | **`SND_InitDriver` / `SND_Init` 都在 `!com_dedicated` 内** |
| **Ghosts** | **没有 sound startup** |
| **CODOL** | **`CL_InitRenderer -> SND_InitDriver -> SND_Init -> cls_soundStarted=1`** |

★★★ **⇒ CODOL 的序列是**三连调用 + 一个状态提交**。**

### 2.2 ★★★ v26/v28 的失败（第 126–128 行）

```
v26 只移除两次 sound call 但保留 started 提交，
v28 连同提交一起移除，
两者都在 process patch 成功后、dedicated control port 就绪前退出
        ↓
★★★ 因此完整 guard 不能直接移植。
```

### 2.3 ★★★ v29 的成功（第 127–133 行，逐字）

```
当前只 NOP `Com_Init` RVA `0x19CBEA` 对 `SND_InitDriver 0x00712C10` 的完整 call，
保留 `SND_Init 0x00710C80` 与 `cls_soundStarted 0x078B0A48`。
```

### ★★★★★ 四个精确地址

| # | 项 | 值 |
|---|---|---|
| **1** | 裁剪点（`Com_Init` 内） | **RVA `0x19CBEA`** |
| **2** | 被裁剪的函数 | **`SND_InitDriver 0x00712C10`** |
| **3** | 保留的函数 | **`SND_Init 0x00710C80`** |
| **4** | 保留的状态 | **`cls_soundStarted 0x078B0A48`** |

★★★ **⇒ 只 NOP 掉**驱动初始化**，保留**软件初始化**和**状态提交**。**

★ **⇒ 这是**最小裁剪**（只去掉一个 call）。**

### 2.4 ★★ v29 的完整验证结果（第 130–134 行）

```
`.runtime/natural-match/20260808_dedicated_audio_driver_trim_v29/` 自然闭合
QuickMatch/ready、session/gamestate accepted、world/transport，
并发送 `3 full + 403 delta` snapshot、ack `408`；
client ingress 为 `538 accepted / 1 rejected`，唯一 reject 是连接前的非 CODOL netchan packet，
parser snapshot/playerstate `14/14` 且零 overflow，两个 PID 在捕获后仍响应。
```

★★★ **⇒ 七项指标：**
```
① QuickMatch/ready
② session/gamestate accepted
③ world/transport
④ **3 full + 403 delta** snapshot
⑤ ack **408**
⑥ client ingress **538 accepted / 1 rejected**
⑦ parser snapshot/playerstate **14/14**，零 overflow
```

★★ **⇒ 且明确："**唯一 reject 是连接前的非 CODOL netchan packet**"** ——**
**⇒ 这是**正常的**（不是缺陷）。**

### 2.5 ★★★ 诚实的边界声明（第 133–134 行）

```
window、renderer、剩余 sound 软件状态和 input 初始化仍在执行，
不能把当前状态描述为完整 headless。
```

★★★ **⇒ 明确："**不能把当前状态描述为完整 headless**"。**

---

## 三、★★★★★ v30/v32：Renderer 裁剪的**证伪与撤销**

### 3.1 ★★★ 为什么想裁（第 136–138 行）

```
Renderer 不能沿 BO1/Ghosts 的 dedicated guard 只裁一个 CODOL callsite。
`CL_InitRenderer 0x00467E20` 的注册、viewport、white/console material、font、StatMon
和 console asset 流程虽与 BO1 同构，且 Ghosts dedicated 不调用对应函数，
```

★★ **⇒ BO1/Ghosts 都不做 renderer，所以想裁掉。**

### 3.2 ★★★★★ v30 的精确字节（第 138–140 行）

```
自然实验 v30 只 NOP `Com_Init` RVA `0x19CBE5` 的完整 `E8 36 B2 EC FF` 后，
patch 成功且 dedicated 进程保持存活，却始终不能到达 ol-mod control listener
```

### ★★★★★ 精确的五个字节

```
RVA 0x19CBE5 处的字节：E8 36 B2 EC FF
```

★★★ **⇒ 这是一条 `call rel32` 指令（`E8` + 4 字节相对偏移）。**

★★ **⇒ `rel32 = 0xFFECB236` = **-1,297,866**。**

★ **⇒ 目标 = `0x19CBE5 + 5 - 1,297,866` = `0x19CBEA - 1,297,866` ≈ **`0x00467E20`** ✓**
**⇒ 正好是 `CL_InitRenderer`。**

★★★ **⇒ 所以 v30 裁掉的正是 `Com_Init` 调用 `CL_InitRenderer` 的那一条。**

### 3.3 ★★★ 失败现象（第 139–140 行）

```
patch 成功且 dedicated 进程保持存活，却始终不能到达 ol-mod control listener
        ↓
★★★ 这表明 CODOL 后续初始化仍消费 renderer 状态。
```

### 3.4 ★★★ v32 的撤销与恢复（第 140–145 行）

```
撤销该 patch 后，`.runtime/natural-match/20260808_dedicated_renderer_retained_v32/`
重新自然闭合 `mp_crash_tropical/sd`：
  session/gamestate accepted
  class `31/31`
  character `2`
  dynamic weapon `352`
  world/transport 有效
  稳定窗口 `4 full + 412 delta`
  ack `417`
  client packet `553 accepted / 1 rejected`
  parser snapshot/playerstate `16/16` 且零 overflow
        ↓
★★★ **renderer 必须保留**，直到 CODOL post-init consumer 和 dedicated 分支能作为一个
整体被证明并裁剪。
```

---

## 四、★★★★★ v34–v37：四个成功的裁剪

### 4.1 ★★★ v34：`SetFocus`（第 147–156 行）

```
CODOL WinMain 在 `0x0064272A` 无条件执行 `push HWND; call ds:SetFocus`；
dedicated 会在严格确认 `52 FF 15` opcode 前缀后 NOP 完整 7 bytes，
避免只删 6-byte stdcall call 而把参数留在栈上。
IAT absolute operand 的四字节由 PE loader relocation 所有，不参与固定值比较。
```

### ★★★★★ 三个精确细节

| # | 项 | 值 |
|---|---|---|
| **1** | 裁剪点 | **`0x0064272A`** |
| **2** | opcode 前缀 | **`52 FF 15`**（`push edx; call [IAT]`） |
| **3** | ★★★ **NOP 7 bytes** | **不是 6 bytes**（避免把参数留在栈上） |

★★★ **⇒ 第 3 条是**关键的技术细节**：**
```
`52 FF 15 xx xx xx xx` = push edx（1）+ call [IAT]（6）= **7 字节**
        ↓
若只 NOP 6 字节（call 部分）⇒ **push edx 还在，参数留在栈上**
        ↓
★★★ 必须 NOP **完整 7 字节**
```

★ **⇒ 且注明："**IAT absolute operand 的四字节由 PE loader relocation 所有，不参与固定值比较**"** ——**
**⇒ 因为 IAT 地址会因重定位变化，不能作固定值比对。**

### 4.2 ★★★ v35：Accessibility shortcut keys（第 158–169 行）

```
同一 WinMain 还会先用 `SystemParametersInfoA` 读取 Sticky/Toggle/Filter Keys，
再在功能未启用时临时清除热键标志。Dedicated 保留三次 GET 和退出路径使用的原状态，
只把 RVA `0x242662/0x24267B/0x242692` 的 `75 12/75 10/75 11` 分别改为
`EB 12/EB 10/EB 11`，从而始终跳过三次 SET。
```

### ★★★★★ 三个精确的 RVA + 字节对

| RVA | 原字节 | 改后 |
|---|---|---|
| **`0x242662`** | **`75 12`** | **`EB 12`** |
| **`0x24267B`** | **`75 10`** | **`EB 10`** |
| **`0x242692`** | **`75 11`** | **`EB 11`** |

★★★ **⇒ 三处 `jne` → `jmp`（跳过 SET 调用）。**

★★ **⇒ 且明确："三个 opcode 与位移会作为一个**原子单元**完整校验；**
**原始、部分已 patch 和全部已 patch 均支持，**未知 bytes 在任何写入前拒绝**。"**

★ **⇒ 这是**最严谨的补丁实践**（三态支持 + fail-closed）。**

★★ **⇒ 三方对比（第 162–164 行）：**
```
BO1 dedicated WinMain  **没有**这组逻辑
Ghosts dedicated       显式调用 Sys_RecordAccessibilityShortcutSettings
                       + Sys_AllowAccessibilityShortcutKeys(0)
        ↓
★ 因此该裁剪是 **CODOL dedicated 的宿主副作用隔离**，不冒充三方原生一致
```

### 4.3 ★★★ v36：Cursor visibility（第 171–180 行）

```
CODOL `IN_UpdateSystemCursorVisibility 0x0063DF20` 只按 desired/cached 状态循环调用
`ShowCursor`；BO1 `IN_ShowSystemCursor 0x007D8A00` 具有相同计数同步算法，
Ghosts dedicated 则使用 server console message loop。
runtime 在严格确认 RVA `0x6980F4` 的 `E8 27 5E BA FF` 后 NOP 完整 call，
仍执行 `PeekMessageA/GetMessageA/TranslateMessage/DispatchMessageA`、WndProc、
window handle、renderer 和其余 input 状态。
```

★★★ **⇒ 三个精确地址 + 五个字节：**
```
IN_UpdateSystemCursorVisibility  0x0063DF20
BO1 IN_ShowSystemCursor          0x007D8A00
裁剪点 RVA                       0x6980F4
裁剪字节                         E8 27 5E BA FF
```

★★ **⇒ 且保留**四个消息循环函数**（`PeekMessageA`/`GetMessageA`/`TranslateMessage`/`DispatchMessageA`）。**

### 4.4 ★★★ v37：Input frame（第 182–190 行）

```
CODOL `IN_Frame 0x0063E030` 与 BO1 同名函数的控制流吻合，
负责 click-to-continue、mouse initialized/app active 判断、mouse activate/deactivate 和 movement；
正常每帧 caller 已由第一阶段 frame trim 移除。
runtime 在严格确认 `Com_Init` 尾部 RVA `0x19D0D0` 的 `E8 5B 0F 0A 00` 后 NOP 完整 call，
不删除 `IN_Init`、input globals、设备初始化或 window message pump。
```

★★★ **⇒ 三个精确地址 + 五个字节：**
```
IN_Frame                    0x0063E030
裁剪点（Com_Init 尾部 RVA） 0x19D0D0
裁剪字节                    E8 5B 0F 0A 00
```

---

## 五、★★★★★ v38：`Com_StartHunkUsers` 的**完整证伪**

### 5.1 ★★★ 为什么想跳过（第 192–194 行）

```
完整跳过 `Com_StartHunkUsers 0x0059CFE0` 的方案已被自然运行证伪。
CODOL 函数与 BO1 同名边界逐调用吻合，
但当前 dedicated 仍通过本进程的 client-loaded XAsset registry 解析武器，
尚未拥有 BO1 server 的独立资产注册入口。
```

### 5.2 ★★★★★ v38 的精确操作（第 194–197 行）

```
v38 同时跳过 RVA `0x19D16B` 的启动 call 和 RVA `0x19E0F4` 的 Com_Error recovery call 后，
frontend、ready、自然 allocation、transport、configstrings 和
`154 accepted / 0 rejected` ingress 均继续工作，
但 session 固定停在 `weapon_registry_unavailable`，
resolved class mask `0/31`，没有 gamestate、world 或 snapshot。
```

### ★★★★★ 完整的失败特征

| 项 | 值 |
|---|---|
| 裁剪点 1 | **RVA `0x19D16B`**（启动 call） |
| 裁剪点 2 | **RVA `0x19E0F4`**（Com_Error recovery call） |
| 仍工作的 | frontend / ready / allocation / transport / configstrings / **154 accepted / 0 rejected** |
| ★★★ **失败点** | **`weapon_registry_unavailable`** |
| ★★★ **class mask** | **`0/31`** |
| ★★★ 缺失 | **gamestate / world / snapshot 全无** |

★★★ **⇒ 这是一个**极其精确的失败定位**：**
```
ingress 完全正常（154 accepted / 0 rejected）
        ↓
但 session 停在 `weapon_registry_unavailable`
        ↓
★★★ resolved class mask `0/31`（一个类都解析不出）
        ↓
gamestate / world / snapshot 全无
```

### 5.3 ★★★ v39 的撤销（第 198–205 行）

```
该 patch 已撤销。回退后的 clean run
`.runtime/natural-match/20260808_dedicated_hunk_users_retained_v39/` 恢复
session/gamestate accepted、class `31/31`、character `2`、dynamic weapon `352`、
world/transport、`4 full + 88 delta`、ack `93`、`116 accepted / 1 rejected`；
唯一 reject 是连接前非 CODOL netchan packet，parser snapshot/playerstate `17/17` 且零 overflow。
```

★★★ **⇒ 撤销后**完全恢复**（`class 31/31`）。**

★★ **⇒ 且结论（第 204–205 行，逐字）：**
> **`Com_StartHunkUsers` 必须保留到 dedicated 拥有等价的 native asset-registry bootstrap；
> 不能因 BO1/Ghosts dedicated 省略 frontend startup 就直接搬用完整 guard。**

---

## 六、★★★★ v40–v44：四个 zone descriptor 的**第二次证伪**

### 6.1 ★★★ 尝试的方案（第 207–211 行）

```
v40-v44 对"用四个 common zone descriptor 直接替代该 owner"做了更窄的自然验证。
CODOL `0x0049FD00` 的确构造
  `patch_common_mp/common_mp/patch_localized_common_mp/localized_common_mp`，
`0x0059D730` 也确实在 frame 中轮询 loaded 后执行 weapon registry 序列；
但 dedicated 在原生 post-init gate 未成立、registry 仅 `1 weapon / 2 attachment models` 时
强行执行该序列，会在 `CODOL_Weapon_InitRegistry 0x0042CC50` 触发 `0xC0000005`，
并在 watcher attach 前退出。
```

### ★★★★★ 三个精确地址 + 失败点

| # | 项 | 值 |
|---|---|---|
| **1** | zone descriptor 构造 | **`0x0049FD00`** |
| **2** | 四个 zone 名 | `patch_common_mp` / `common_mp` / `patch_localized_common_mp` / `localized_common_mp` |
| **3** | frame 轮询 | **`0x0059D730`** |
| **4** | ★★★ **崩溃点** | **`CODOL_Weapon_InitRegistry 0x0042CC50`** |
| **5** | 崩溃码 | **`0xC0000005`** |
| **6** | 崩溃前提 | registry 仅 **`1 weapon / 2 attachment models`** |

### 6.2 ★★★★★ v44 的恢复与关键发现（第 212–217 行，逐字）

```
撤销首帧强制初始化并保留完整 Hunk 路径后，v44
`.runtime/natural-match/20260808_dedicated_hunk_users_native_owner_v44/` 中
原生链自行把 registry 推进到 `357 weapons / 151 attachment models`，
并闭合 session/gamestate、class `31/31`、dynamic weapon `352`、world/transport、
`4 full + 78 delta`、ack `84`、`105 accepted / 0 rejected`。
因此 runtime 不再安装完整 Hunk caller patch，也不主动调用该局部 registry 序列；
下一轮必须先闭合 `0x0059DD20/0x0059C180` 内 fastfile 与 post-init 状态的真实所有权。
```

★★★ **⇒ 关键发现：**原生链自行把 registry 推进到 `357 weapons / 151 attachment models`**。**

★★ **⇒ 而强行执行时只有 `1 weapon / 2 attachment models` ⇒ 崩溃。**

★★★ **⇒ 结论：**不要干预，让原生链自己完成**。**

---

## 七、★★★★ v51：只读 probe 达到**架构决策边界**

### 7.1 ★★★ 精确的四个观察点（第 234–239 行）

```
managed asset probe 在 dedicated 上每 100 ms 只读
`0x02DF7D50`、weapon registry count、`uiViewer.show` 与 common-zone observation；
root 从 `0` 变为 `0x33B99E0` 时，registry 已为 `353`、`common_mp=true`、`uiViewer.show=0`。
```

### ★★★★★ 四个观察点 + 关键状态

| # | 观察项 | 值 |
|---|---|---|
| **1** | **weapon-group root** | **`0x02DF7D50`**，从 `0` → **`0x33B99E0`** |
| **2** | registry count | **`353`**（当 root 变非零时） |
| **3** | `common_mp` | **`true`** |
| **4** | `uiViewer.show` | **`0`** |

★★★ **⇒ 关键发现（第 239–240 行，逐字）：**
> **因此该 list 不是 registry 主体或 frontend viewer 的前置条件。**

### 7.2 ★★★ 被删除的 watchpoint 方案（第 240–242 行）

```
v45-v50 试用的 hardware watchpoint 会终止客户端或让 dedicated 长期停在
`configstring_generation_reset`，已删除；不得把这些失败运行当成游戏因果证据。
```

★★★ **⇒ 6 个版本（v45–v50）全部失败**（hardware watchpoint 导致客户端终止）。**

★★ **⇒ 且明确："**不得把这些失败运行当成游戏因果证据**"。**

### 7.3 ★★ 最终决定（第 242–243 行）

```
当前保留完整 `Com_StartHunkUsers` 并暂缓继续细拆 assets，
只读 probe 留作未来部署/资源优化重新开启调查时的状态工具。
```

---

## 八、★★★★ `Frida` 临时目录管理（第 245–249 行）

### 8.1 ★★★ `CodolFridaRuntime.py`（第 247 行）

```
`tools/runtime/CodolFridaRuntime.py` 必须在 import `frida` 前执行，
将解包目录放到仓库的 `.runtime/frida`。默认清理超过 24 小时的目录；
批量清理使用 `CleanupRuntimeTemp.py`，不要再污染用户全局 TEMP 或工作区公共根目录。
```

★★ **⇒ 三个约束：**
```
① 必须在 `import frida` **前**执行
② 解包到 `.runtime/frida`（**不污染 TEMP**）
③ 默认清理 **24 小时**以上的目录
```

### 8.2 ★★★★★ `CodolMemoryStrings.py`（第 249 行）

```
`CodolMemoryStrings.py` 用于对运行客户端做有上限的只读 ASCII 证据扫描。
它不调用游戏函数、不写目标内存，按 16 MiB chunk 扫描 readable ranges，
定期输出进度，并把命中地址、range/module 归属和邻近字符串保存到 `.runtime/memory-strings/`。
不要再为同类任务拼装无进度的单次全内存 `Memory.scanSync`；
同步 RPC 被外部强制终止时可能继续占用目标进程，
必要时应结束该次测试客户端，而不是继续叠 attach。
```

★★★ **⇒ 五个精确参数 + 一条教训：**
```
① **16 MiB chunk**
② 只读 ASCII 扫描
③ 输出：命中地址 + range/module 归属 + 邻近字符串
④ 保存到 `.runtime/memory-strings/`
⑤ ★★★ **不要用无进度的单次全内存 `Memory.scanSync`**
```

★★★ **⇒ 教训（逐字）：**
> **同步 RPC 被外部强制终止时可能继续占用目标进程，
> 必要时应结束该次测试客户端，而不是继续叠 attach。**

★★ **⇒ 这是**Frida 使用的重要经验**（同步 RPC 会卡住目标进程）。**

---

## 九、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★ 实验版本 | **v26–v51（26 个版本）** |
| 2 | ★★★ **v29 成功** | `SND_InitDriver` RVA **`0x19CBEA`** → **`0x00712C10`** |
| 3 | ★ v29 保留 | `SND_Init 0x00710C80` / `cls_soundStarted 0x078B0A48` |
| 4 | ★★★ **v30 证伪** | `CL_InitRenderer 0x00467E20`，裁剪点 **`0x19CBE5`**，字节 **`E8 36 B2 EC FF`** |
| 5 | ★ v32 撤销 | 恢复 `4 full + 412 delta` |
| 6 | ★★★ v34 | `SetFocus` @ **`0x0064272A`**，opcode **`52 FF 15`**，**NOP 7 bytes** |
| 7 | ★★★★ v35 | 三处 **`75 12/75 10/75 11` → `EB 12/EB 10/EB 11`** @ `0x242662/0x24267B/0x242692` |
| 8 | ★ v36 | `IN_UpdateSystemCursorVisibility 0x0063DF20`，裁剪点 **`0x6980F4`**，字节 **`E8 27 5E BA FF`** |
| 9 | ★ v37 | `IN_Frame 0x0063E030`，裁剪点 **`0x19D0D0`**，字节 **`E8 5B 0F 0A 00`** |
| 10 | ★★★★★ **v38 证伪** | `Com_StartHunkUsers 0x0059CFE0`，裁剪 `0x19D16B`/`0x19E0F4` ⇒ **`weapon_registry_unavailable`**，class **`0/31`** |
| 11 | ★★ v39 撤销 | 恢复 class **`31/31`** |
| 12 | ★★★★★ **v40–v44 证伪** | 强行 registry ⇒ **`0xC0000005` @ `0x0042CC50`** |
| 13 | ★★★★ v44 恢复 | 原生链自行推进到 **`357 weapons / 151 attachment models`** |
| 14 | ★★★ v51 probe | weapon-group root **`0x02DF7D50`**：`0` → **`0x33B99E0`**，registry **`353`** |
| 15 | ★ v45–v50 失败 | hardware watchpoint ⇒ 停在 **`configstring_generation_reset`** |
| 16 | ★★ Frida 目录 | **`.runtime/frida`**，清理 **24 小时** |
| 17 | ★★★ `CodolMemoryStrings` | **16 MiB chunk**，只读，**不要单次全内存 scanSync** |

---

## 十、结论

### 1. ★★★★★ **26 个版本的裁剪实验**是极其严谨的工程实践

★★ **⇒ 每次都有：精确 RVA + 字节 + 完整验证指标 + 诚实边界声明。**

### 2. ★★★★★ **两次完整证伪 + 撤销**

```
v30 裁 renderer  ⇒  到不了 control listener  ⇒  v32 撤销
v38 裁 Hunk      ⇒  weapon_registry_unavailable  ⇒  v39 撤销
v40-44 强推 registry  ⇒  0xC0000005  ⇒  v44 撤销
```

### 3. ★★★★★ **"原生链自行推进到 357 weapons / 151 attachment models"** 是关键洞察

★ **⇒ 不要干预，让原生链自己完成。**

### 4. ★★★ **v34 的 "NOP 7 bytes 而非 6"** 是精确的技术细节

```
push edx（1）+ call [IAT]（6）= 7 字节
只 NOP 6 ⇒ 参数留在栈上
```

### 5. ★★★ **v35 的三态补丁校验**（原始/部分/全部 + 未知拒绝）

### 6. ★★ **Frida 同步 RPC 会卡住目标进程**（重要经验）

---

## 十一、下一步

- `runtime.md` 剩余（第 249 行起，约 750 行）
- `source\.agents\modules\game_server.md`（223 KB）
- `source\docs\devlog\`（中文开发历程）
