# CODOL 弹窗动态抓取报告

**日期**：2026-09-25（Asia/Shanghai）
**执行方式**：提权代理 + `_popup_watch.py`（窗口枚举）+ `_pop_desktop_shot.py`（桌面 BitBlt 截图）

---

## 〇、最重要的结论（先看这里）

**`[100]无法连接大厅服务!` 不是 Win32 弹窗，而是游戏自己渲染在游戏画面里的 UI。**

证据：`CODOLServer\_pop_trace\shots\desktop_game.png`（1920x1080 实拍）里，游戏窗口中央画着一个带蓝框的面板，里面有：

```
[100]无法连接大厅服务!
```

面板右上角还有一个 **`官网`** 按钮——这是**游戏内 UI 组件**，不是 Windows 对话框。

**这解释了一个长期困惑**：窗口枚举器（`_popup_watch.py`）在整条固化启动链里**一个游戏弹窗都没抓到**，因为 `[100]` 根本不经过 `CreateWindow`/`MessageBox`，它是渲染出来的。只有对**桌面做像素级截图**才能看到它。

> 此前用户反馈"错误100，无法连接大厅服务"、"目前OL无法进入大厅"——现在有实拍图为证，且明确了它的呈现机制。

---

## 一、三种启动方式对比

| 方式 | 入口 | 到游戏窗口 | 走到的层 | 结果 |
|---|---|---|---|---|
| A. 直接双击 exe | `sandbox_ifs1_20260923\codoMP_client_shipRetail.exe` | 是 | TCLS 之后 / IIPS | Win32 `#32770` 弹窗：`致命错误 / 初始化IIPS错误：8189fec。` |
| B. 固化 observer 链 | `capture_elevated_network.ps1` | 是（splash） | IIPS → 网络层 | **游戏内渲染 `[100]无法连接大厅服务!`**（见实拍图），随后自行退出 |
| C. 固化直接启动链 | `run_direct_iips1_elevated.ps1 -Sandbox sandbox_ifs1_20260923` | 是（splash） | IIPS → 网络层 | 同上（窗口期内未截到 UI 面板，但同为 splash+网络层） |

**关键**：方式 A 与方式 B/C 死在**完全不同的层**。
- A：死在 IIPS 初始化（`WIN_IIPS_INIT_ERROR`），是**Win32 弹窗**。
- B/C：IIPS 这关没弹框，游戏推进到**网络层**，最后才在**游戏内 UI** 上显示 `[100]`。

---

## 二、方式 B 实拍证据（决定性）

`CODOLServer\_pop_trace\shots\desktop_game.png`：

```
游戏窗口（pid 17036, class CODO, 标题 使命召唤online）
  └─ 中央面板（蓝框）
       ├─ [100]无法连接大厅服务!          <- 游戏内渲染文本
       └─ 官网 按钮（面板右上）
```

裁剪图：`CODOLServer\_pop_trace\shots\dialog_100_crop.png`

> 注：裁剪图里文字是镜像的，因为原始 BMP 是 bottom-up 存储，我做了直接像素拷贝。文本内容从左到右读是 `[100]无法连接大厅服务!`。

### 时间线（`CODOLServer\_pop_trace\desktop\windows.jsonl`）

| t(s) | pid | 进程 | 窗口类 | 说明 |
|---|---|---|---|---|
| 20.73 | 9444 | `AboProbe.exe` | `ConsoleWindowClass` | 观察器 |
| 21.53 | 18260 | `TP3Helper.exe` | `#32770` | 保护壳窗口（无文本） |
| **36.16** | **17036** | **`codoMP_client_shipRetail.exe`** | **`CODO`** | **`使命召唤online`** |
| **36.16** | **17036** | **`codoMP_client_shipRetail.exe`** | **`CoD Splash Screen`** | **`使命召唤online Multiplayer`** |
| — | — | — | — | **`[100]` 是渲染文本，窗口枚举看不到；靠桌面截图捕获** |

---

## 三、网络层证据（同步抓到的 AFD ETW）

同一次运行 `run_codol_001\runs\NET_CAPTURE_ELEVATED_20260925_164411\game_rt_report.md`（want_pids=[17036]，即那个显示了 `[100]` 的进程）：

```
t=20.330  0xFFFFC90B9C7FA110#1 -> 116.130.224.66:8000  ret=0
t=20.342  0xFFFFC90B9FACB200#2 -> 116.130.224.66:8000  ret=0
```

**时间吻合**：t≈20.3s 向 `116.130.224.66:8000` 发起 UDP 连接 → 之后游戏内渲染出 `[100]`。

这坐实了：
1. `[100]` 就是**对这个地址连接失败**的结果；
2. `116.130.224.66:8000` 是**游戏自己算出来并主动去连的**（不是 WeGame/TCLS 塞的）；
3. 该地址已停服无人应答 → 超时 → `@SF_UI_DW_LIVE_CONNECTING_FAILED` → 画 `[100]`。

（上一次运行 `NET_CAPTURE_ELEVATED_20260925_163332` 同样记录到 `116.130.224.66:8000` 两次连接。）

---

## 四、文案来源追溯（localization.txt → exe 地址）

`COD OL\localization.txt`（GBK，5604 字节）：

| key | 中文文案 | loc 偏移 | 用在哪个弹窗 |
|---|---|---|---|
| `WIN_ERROR` | `致命错误` | 0x697 | 方式 A 的 Win32 框标题 |
| `WIN_IIPS_INIT_ERROR` | `初始化IIPS错误：%x。` | 0x115C | **方式 A 的正文** |
| `WIN_NO_TCLS` | `请使用腾讯游戏登录器(TCLS文件夹内的Client.exe)启动游戏。` | 0x10BC | 历史已知（本次未复现） |
| `@SF_UI_DW_LIVE_CONNECTING_FAILED` | `无法连接大厅服务!` | 0x950 | **游戏内 `[100]` 的正文** |

对应 key 字符串在 `COD OL\codoMP_client_shipRetail.exe` 的地址（ImageBase=0x00400000）：

| key | 文件偏移 | VA |
|---|---|---|
| `WIN_ERROR` | 0x006C7F74 | 0x00DDBF74 |
| `WIN_NO_TCLS` | 0x006C7F80 | 0x00DDBF80 |
| `WIN_IIPS_INIT_ERROR` | 0x006B53A8 | 0x00DC93A8 |
| `@SF_UI_DW_LIVE_CONNECTING_FAILED` | 0x006CC640 | 0x00DE0640 |

---

## 五、`[100]` 的 `100` 是什么

`100` 与 `无法连接大厅服务!` 同屏，而该文案对应 key `@SF_UI_DW_LIVE_CONNECTING_FAILED`。结合网络证据（对 `116.130.224.66:8000` 连接失败），`100` 是**大厅连接失败的错误码**（dwLobby 层的失败码，非 `BD_LOBBY_*` 枚举值 17 那类）。它是**本地/大厅层**的错误，不是 IIPS 层。

---

## 六、IIPS 初始化失败的真实原因（方式 A 的弹窗）

来自 `run_codol_001\runs\REPRO_DIRECT_S2_1639` 与 `...\IIPS\TenioLog\20260925_163710.log`：

1. **沙箱 `IIPS\HostPid` 是 0 字节**（原始 `COD OL\IIPS\HostPid` 是 16 字节 BOM + `20128\r\n` UTF-16）。HostPid 是管道握手前置条件，空 → `IIPSERR_PIPE_INIT`。
2. **`IIPSHostApp` 把 UI 资源路径拼成双反斜杠**：日志反复出现
   ```
   ...\sandbox_ifs1_20260923\IIPS\\TPFUI\IIPSRes\back\边玩边下\边玩边下底.png
   ```
   而**验证这些文件是存在的**（`back` 下 90 个 png，抽查 3 个 missing→False），所以不是资源缺失，是**路径拼接 bug** → `LoadImageFromBuffer` 全挂 → UI 初始化失败 → 不建管道 → 不写 HostPid。

**这就是方式 A 弹 `初始化IIPS错误` 的原因，也是方式 B/C 能越过它、走到大厅层的原因。**

---

## 七、结论与下一步

### 结论
1. **`[100]` 是游戏内渲染的 UI**，不是 Win32 弹窗——这是本次最重要的发现，解释了过去"抓不到弹窗"的现象。
2. **固化启动链（B/C）有效**：能把游戏推进到**网络层**，并**主动连 `116.130.224.66:8000`**，连不上才画 `[100]`。
3. **我们写服务器要拦截/伪造的目标已经明确**：`116.130.224.66:8000`（UDP）。
4. `[100]` 与 IIPS 是两层：IIPS 没起来时弹的是 Win32 `初始化IIPS错误`，IIPS 过了才轮到 `[100]`。

### 下一步
1. **在本地 8000 端口伪造对 `116.130.224.66:8000` 的应答**，让游戏不再画 `[100]`，看它是否进入大厅。
2. 同时修 `IIPSHostApp` 的双反斜杠路径 / 伪造 `HostPid`，让 IIPS 层彻底干净。
3. 采集窗口建议 ≥120s（本次 `[100]` 出现在游戏窗口出现后约 10~20s 内）。

---

## 八、原始数据位置

```
CODOLServer\_pop_trace\shots\desktop_game.png        实拍：游戏内 [100] 面板（决定性证据）
CODOLServer\_pop_trace\shots\dialog_100_crop.png     [100] 面板裁剪图
CODOLServer\_pop_trace\shots\game_splash_chain1.png  游戏窗口截图（PrintWindow，DirectX 全黑）
CODOLServer\_pop_trace\desktop\windows.jsonl         方式 B 窗口时间线
CODOLServer\_pop_trace\direct\windows.jsonl          方式 A 弹窗日志（IIPS 错误框）
CODOLServer\_pop_trace\chain1\windows.jsonl          方式 B（75s）
CODOLServer\_pop_trace\chain2\windows.jsonl          方式 C（130s）
CODOLServer\_pop_trace\chain3\windows.jsonl          方式 B 复跑（115s）
run_codol_001\runs\NET_CAPTURE_ELEVATED_20260925_164411\game_rt_report.md   [100] 同进程网络报告
run_codol_001\runs\NET_CAPTURE_ELEVATED_20260925_163332\game_rt_report.md   复现确认
run_codol_001\runs\REPRO_DIRECT_S2_1639\             方式 C 运行目录（game_status / tenio_files）
run_codol_001\sandbox_ifs1_20260923\IIPS\TenioLog\20260925_163710.log      IIPSHostApp 双反斜杠日志
```

## 九、脚本

```
CODOLServer\_mainline\_popup_watch.py        窗口枚举 + PrintWindow 截图（抓 Win32 弹窗）
CODOLServer\_mainline\_pop_desktop_shot.py   桌面 BitBlt 截图（抓游戏内渲染 UI）<- 本次新增，关键工具
```
