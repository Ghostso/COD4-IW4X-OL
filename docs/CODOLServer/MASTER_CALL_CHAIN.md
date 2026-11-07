# CODOL 端到端调用链（主文档）

日期：2026-09-25
目的：把"游戏怎么启动 → 怎么走到大厅 → 为什么画 `[100]`"一次性钉死
证据等级：**实拍图 + AFD/ETW 实测 + 反汇编 VA 级**

---

## 0. 一图总览

```
[启动层]  直接双击 exe            -> Win32 #32770 "请使用腾讯游戏登录器..." (WIN_NO_TCLS)
          固化启动链 / WeGame     -> 通过 TCLS 检查，进入游戏
                     │
[本地层]  TCLS 交接 (共享内存 TCLS_SHAREDMEMEMORY<pid>)
              │
          IIPS 初始化 (ResourceManagerII::Initialize)
              ├─ 载 IFS.dll + IIPSFileList.ini
              ├─ 读 IIPS\HostPid
              ├─ CreateProcess IIPSHostApp.exe /mode iipslaunch
              └─ CreateFile("\\.\Pipe\" + MD5(lower(iips_url)))   ← 失败则 Win32 "初始化IIPS错误"
                     │
[发现层]  TQoS  (UDP) -> ied-tqos.qq.com 解析 -> 116.130.224.66:8000
                     │        （无应答）
[大厅层]  GDP / Blaze dwLobby   ← 【当前断点】
                     │
[呈现层]  游戏内渲染 UI： "[100]无法连接大厅服务!"   ← 不是对话框，是渲染文本
```

---

## 1. 启动层

| 入口 | 结果 | 证据 |
|---|---|---|
| 直接双击 `sandbox_ifs1_20260923\codoMP_client_shipRetail.exe` | Win32 `#32770`：`致命错误 / 初始化IIPS错误：8189fec。` | `_pop_trace\direct\windows.jsonl` t=20.0 |
| 固化 observer 链 `capture_elevated_network.ps1` | 过 IIPS，进网络层，画 `[100]` | `_pop_trace\chain1\windows.jsonl` |
| 固化直接链 `run_direct_iips1_elevated.ps1` | 同上 | `_pop_trace\chain2/chain3` |

固化链才是**唯一能走到网络层**的入口。

---

## 2. 本地层：IIPS 初始化（细节见 `IIPS_PIPELINE_FULL_REVERSE.md`）

关键契约：

```
管道名    = "\\.\Pipe\" + MD5( lowercase(iips_url) )      ← IIPSHost.dll 0x10010870 标准 MD5
管道类型  = MESSAGE（CreateNamedPipeA dwPipeMode=6, 12 实例）
消息      = 定长 791 字节，cmd 在 +0x02
共享内存  = Global\IIPSShareState_MMF_<key> / _Mutex_<key>
前置文件  = IIPS\HostPid（UTF-16，内容 = IIPSHostApp 的 PID）
```

失败表现（方式 A）：`IIPSHostApp` 把 UI 路径拼成 `IIPS\\TPFUI\IIPSRes\...`（双反斜杠），
`LoadImageFromBuffer` 全挂 → 不建管道 → 不写 HostPid → 游戏 `IIPSERR_PIPE_INIT`
→ Win32 弹 `初始化IIPS错误：8189fec`。

---

## 3. 发现层：TQoS

**端点来源（已实测解析）**

```
ied-tqos.qq.com  --DNS-->  116.130.224.66
```

`ied-tqos.qq.com` 是 exe 内**硬编码字符串**（`COD OL\codoMP_client_shipRetail.exe`，
文件偏移 0x6C58A0，**VA 0x00DD98A0**，紧邻 `tqos` 等串）。
`116.130.224.66` 在 exe 里**零命中** ⇒ 它是**运行时 DNS 解析**产物，不是硬编码。

**⇒ 拦截点 = `ied-tqos.qq.com` 字符串本身**：
启动时原地改写成 `127.0.0.1`（等长覆盖，`suspend_host_redirect.py` 已在用此手法），
游戏即连 `127.0.0.1:8000`，由本地假 TQoS 应答。

其它实测解析（供对照）：

```
tqos.gamesafe.qq.com  -> 122.96.96.225 / 182.50.14.56   （AFD 抓到游戏往 182.50.14.56:8081 发 176 包）
stun1-tub.codol.qq.com-> 121.51.232.95
ctrl.iips.qq.com      -> 81.71.56.168 / 81.71.56.27      （IIPS 策略服务器）
```

**实测（AFD/ETW，want_pids = 显示 `[100]` 的那个游戏进程）**

```
t=20.330  0xFFFFC90B9C7FA110#1 -> 116.130.224.66:8000  ret=0
t=20.342  0xFFFFC90B9FACB200#2 -> 116.130.224.66:8000  ret=0
```

（另一次运行 `NET_CAPTURE_ELEVATED_20260925_163332` 同样记录到两次连接。）

随后约 10~20s 内，游戏内渲染出 `[100]无法连接大厅服务!`。

⇒ **`[100]` 就是对 `116.130.224.66:8000` 连接/超时的结果。**

---

## 4. 大厅层：GDP / Blaze

- 协议定义：`COD OL\GDPOpenProtocol.tdr`（438,856 B，343 命令 + 592 类型）
- 线格式：`GDPPkgHead(Version+CmdID+CmdType+headlen+bodylen+SubCmdId)`；CODOL 分支 `TGDPCODOLMainCmdHead`
- 命令码：`REQ_ENTERCHANNEL=0x0289`, `NOTIFY_LOGIN=0x030E`, `NOTIFY_SERVER_ENTERED=0x0278` …
- 大厅事件：`DW_LOBBY_CONNECTED` / `DW_LOBBY_ERROR` / `cppOnDWConnected / Disconnected`
- `无法连接大厅服务!` = key `@SF_UI_DW_LIVE_CONNECTING_FAILED`
  - localization.txt 偏移 0x950；exe 字符串 VA **0x00DE0640**

---

## 5. 呈现层：[100] 是"画"出来的，不是"弹"出来的

| 现象 | 机制 |
|---|---|
| 窗口枚举器抓不到 `[100]` | 它不走 `CreateWindow`/`MessageBox`，是游戏内 UI |
| `PrintWindow` 截游戏窗口全黑 | DirectX 后台缓冲，`PrintWindow` 拿不到 |
| 唯一有效手段 | **桌面 BitBlt 截图**（`_pop_desktop_shot.py`） |

实拍：`CODOLServer\_pop_trace\shots\desktop_game.png`
面板内容：`[100]无法连接大厅服务!`（右上角还有 `官网` 按钮 → 游戏内 UI 组件）

---

## 6. 文案 key ↔ exe 地址对照

| key | 中文 | loc 偏移 | exe VA |
|---|---|---|---|
| `WIN_ERROR` | 致命错误 | 0x697 | 0x00DDBF74 |
| `WIN_NO_TCLS` | 请使用腾讯游戏登录器(TCLS文件夹内的Client.exe)启动游戏。 | 0x10BC | 0x00DDBF80 |
| `WIN_IIPS_INIT_ERROR` | 初始化IIPS错误：%x。 | 0x115C | 0x00DC93A8 |
| `@SF_UI_DW_LIVE_CONNECTING_FAILED` | 无法连接大厅服务! | 0x950 | 0x00DE0640 |
| `@SF_UI_DW_LIVE_DISCONNECTED` | 与大厅服务失去连接 | 0x93C | — |

---

## 7. 三层失败要分清（历史混淆点）

| 层 | 表现 | key | 触发条件 |
|---|---|---|---|
| TCLS | Win32 框 | `WIN_NO_TCLS` | 未经登录器启动 |
| IIPS | Win32 框 | `WIN_IIPS_INIT_ERROR` | HostPid 空 / 管道没起来 |
| 大厅 | **游戏内渲染** | `@SF_UI_DW_LIVE_CONNECTING_FAILED` | `116.130.224.66:8000` 无应答 |

**三者互不替代**：IIPS 过了才会看到 `[100]`；这就是为什么"修 IIPS"和"连大厅"是两件事。

---

## 8. 写服务器的最小动作（结论）

1. **拦/答 `116.130.224.66:8000`（UDP）** —— 让游戏不再画 `[100]`，看它是否进入大厅握手。
   - 不可改系统网络（用户硬约束）。
   - 可行手段：启动时把 `ied-tqos.qq.com`（exe VA 0x00DD98A0）等主机名原地改写成 `127.0.0.1`，
     再本地起 UDP/8000 应答（沿用 `suspend_host_redirect.py` 的成熟手法）。
2. TQoS 最小应答（已被客户端接受）：
   ```
   'ur' + u16(16) + u16(8) + u16(4) + u16(0) + u16(0) + u32(seq) + u32(100) + u32(0)
   ```
3. 之后才轮到大厅 GDP / Blaze（`GDPOpenProtocol.tdr` + `gdp_server.py` 骨架）。

---

## 9. 相关文档

| 文件 | 内容 |
|---|---|
| `CODOLServer\IIPS_PIPELINE_FULL_REVERSE.md` | IIPS 全链路（组件/管道/策略服务器/备份） |
| `CODOLServer\SUBAGENT_POPUP_TRACE.md` | 弹窗动态抓取（本次决定性证据） |
| `CODOLServer\GDP_WIRE_FORMAT.md` | GDP 线格式 |
| `CODOLServer\GDP_COMMANDS.csv` / `GDP_CMD_MAP.csv` | 命令码表 |
| `CODOLServer\SHM_HANDOFF_REVERSE.md` | TCLS 交接块逆向 |
| `CODOLServer\WORKING_HARNESS_NOTES.md` | 可复现操作手册 |
