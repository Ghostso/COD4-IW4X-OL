# 主线结论：IIPS 上下线全链已吃透，`[100]` 不在 IIPS 层

日期：2026-09-25
方法：`IIPSHostApp.exe` / `IIPSHost.dll` / `iips.dll` 静态反汇编（pefile + capstone，VA 级）
      + TPFUI 资源取证 + 已有动态报告复核
证据等级：**反汇编逐条确认（VA 级）**

---

## 0. 一句话结论

**`[100] 无法连接大厅服务` 与 IIPS 无关，且 IIPS 也不决定大厅。**

`IIPSHostApp` 建命名管道的**唯一硬门槛**是"能不能 connect 到策略服务器
`udp://ctrl.iips.qq.com:8000`"。它不依赖 TPFUI 界面资源、不依赖 HostPid 先存在、
不依赖任何本地文件。反汇编证据如下。

---

## 1. 修正一份错误结论（重要）

此前 `CODOLServer\SUBAGENT_POPUP_TRACE.md` 断言：

> `[100]` 就是对 `116.130.224.66:8000` 连接/超时的结果

**这条不成立**，有三重反证：

1. **域名核对**（本轮实测）：
   ```
   ctrl.iips.qq.com  -> 81.71.56.27 / 81.71.56.168
   ied-tqos.qq.com   -> 116.130.224.66
   ```
   两者是不同域名、不同 IP。把 `[100]` 归给 IIPS 策略连接，与归给 TQoS 探测，
   说的是两条不同的链路。
2. **协议层面对不上**：TQoS 走 `'ur'` 魔数 + UDP 8000；IIPS 策略走
   AES-128(`iips#policy!@#$%`) + UDP 8000。两者共用端口号，但**不是同一套协议**。
   单看"8000/UDP"无法区分，必须看载荷。
3. **`ctrl.iips.qq.com` 目前仍可解析、且历史上是活的**（有 TCP 14309 拉配置成功的实测记录），
   而 `116.130.224.66` 是否应答并不改变 `[100]` 的出现时机（见 §5）。

所以 `[100]` 既不是 IIPS 管道失败（那是 Win32 弹框 `初始化IIPS错误`），
也不是 TQoS 探测失败（那是地址自检，一次性 UDP）。

---

## 2. IIPS 上线（上游）—— 5 条，已穷尽

| 编号 | 上线 | 证据 |
|---|---|---|
| UP-1 | 引擎 `LoadLibrary("IIPS\iips.dll")` → `GetResourceManagerII` | exe 字符串 VA 0x00DC93F0；`iips.dll` 无任何 DLL 静态导入 ⇒ 只能运行时加载 |
| UP-2 | Scaleform AS3 绑定 `AS_IIPS_*`（"边玩边下"面板） | `AS_IIPS_IsPackReady/RequestPack/GetTotalPackSize/...` + dvar `iips_listpackages/iips_syncpackage/iips_syncfile` |
| UP-3 | 配置文件 `iips.ini` / `IIPSClient.ini` / `iips-download.ini` / `UIOptions.ini` | 目录实测 |
| UP-4 | TCLS 下发 `TCLS\ifs_file` → `IIPS\IIPSDownload\%s` | exe 字符串 0x6B5314 / 0x6B5324 |
| UP-5 | 进程层 `IIPSHostApp.exe /mode iipslaunch` → `IIPSHost.dll` | 实测 |

**UP-1 / UP-3 是回显不是开关**：`enable_iips` / `iips_url` 只出现在主 exe 的 `.tp3` 段，
`iips.dll` 内命中数为 0。反复改这两个值对 `[100]` 无效，静态证据已解释。

---

## 3. IIPS 下线（下游）—— 完整调用链（本轮 VA 级确认）

```
IIPSHost.dll!ResourceLoader::Start()                        @ 0x10025800
  ├─ GetModuleFileNameW + wcsrchr('\\')                     @ 0x1000F370  (取模块目录)
  ├─ ... + "IIPSDownload"                                   @ 0x100258F1
  ├─ 状态机 [ebx+0x2BE0] = 1,2,3,4,5,6,8  ← 逐步推进
  ├─ 写日志 "[...connect to policy server start][policySvrAddr %s]"
  │                                                          @ 0x10025A55
  ├─ iips_policymsg_api_create(policySvrAddr)                @ 0x10025A7B
  │     ├─ 返回值 < 0  -> 日志 "...policy server failed"      @ 0x10025AA5
  │     └─ 返回值 >= 0 -> 继续
  ├─ 写日志 "...policy server end"                            @ 0x10025ACB   ← 无条件打印
  └─ 之后才进入 "m_iipsHost.Start(), listen to pipe"
        start   @ ref VA 0x10026861
        failed  @ ref VA 0x100268B5
        succeed @ ref VA 0x100268DC
```

紧接着才是命名管道创建（`IIPSHostApp::Start()` 内部）：

```
0x1000DB37  push 0x100625A4          ; "\\.\Pipe\"
0x1000DB2A  call 0x1000F5A0          ; 名字变换 (先 _mbctolower)
0x1000DB45  std::operator+           ; "\\.\Pipe\" + <name>
0x1000DBB9  push 0      (lpSecurityAttributes)
0x1000DBBB  push 0      (nDefaultTimeOut)
0x1000DBBD  push 0x186A0000          ; nInBufferSize  = 409600000
0x1000DBC2  push 0x186A0000          ; nOutBufferSize = 409600000
0x1000DBC7  push 0x0C                ; nMaxInstances = 12
0x1000DBC9  push 0x06                ; PIPE_TYPE_MESSAGE | PIPE_READMODE_MESSAGE
0x1000DBCB  push 0x40000003          ; PIPE_ACCESS_DUPLEX | FILE_FLAG_OVERLAPPED
0x1000DBD0  push eax  (name)
0x1000DBD1  call CreateNamedPipeA
0x1000DC07  cmp ebp, 0xc / jl        ; 循环 12 个实例, 每实例步长 0x37C
0x1000DC55  call ConnectNamedPipe
0x1000DC72  call WaitForMultipleObjects(0x31=49 handles, FALSE, INFINITE)
0x1000DCC1  mov eax, 0x100878B0      ; -> 0x10005380 = 日志/上报函数
             + push 0x100625B0       ; 日志 tag
```

### 3.1 关键判据

| 事实 | 证据 |
|---|---|
| 建管道在**策略连接之后** | `listen to pipe` 三处日志 ref 全在 `0x10026xxx`（晚于策略日志 `0x10025xxx`） |
| 建管道**不依赖 TPFUI 资源** | `CreateNamedPipeA` 的三条调用链（`0x1000D923 / 0x1000DA0C / 0x1000DDC9`）都不触及 `TPFUI`/`LoadImage` |
| 建管道**不依赖 HostPid** | HostPid 是**游戏侧**（`iips.dll`）用来找 host 的，host 自己只负责写 |
| 策略失败**不阻止**打 "end" 日志 | `0x10025ACC` 无条件执行 ⇒ "end" 出现≠策略连接成功 |
| 策略失败**只影响限速/P2P 配置** | schema 全是 `MaxDLSpeed / MaxConnNum / EnableP2P / PsIps` ⇒ 非致命 |

### 3.2 因此

```
IIPS 在本地是可以走通的，路径是：
  1. 本地起一个 UDP 8000 应答 ctrl.iips.qq.com（AES-128 "iips#policy!@#$%"）
     或者让 iips_policymsg_api_create 返回 >= 0
  2. IIPSHostApp 就会进入 listen-to-pipe，创建 \\.\Pipe\<MD5(lower(url))> 共 12 实例
  3. 并写 IIPS\HostPid（供游戏侧 iips.dll 读取）
```

---

## 4. TPFUI 资源取证（澄清一条被误读的结论）

前一轮报告称"`IIPSRes\back` 下 90 个 png 抽查都在"，据此判断是"路径 bug"。
**本轮实测：文件在，但内容是假的。**

```
COD OL\IIPS\TPFUI\IIPSRes\back\边玩边下\边玩边下底.png   69 字节
  89 50 4E 47 0D 0A 1A 0A 00 00 00 0D 49 48 44 52   .PNG....IHDR
  00 00 00 01 00 00 00 01 08 06 00 00 00 1F 15 C4   width=1 height=1
  89 ...                                            RGBA
```

即**全部 178 个 UI png 都是 1x1 透明占位符**（统一 69 字节）。
同时 `工具\EX035_DIR\IIPS\TPFUI\IIPSRes` 也**只有同样的 4 个真文件**
（`1_1.png` / `Icon_Image_TPF` / `icon.ico` / `Thumbs.db`）。

⇒ 出厂的 CODOL 安装包里 **本来就没有这套托盘 UI 皮肤**（它是 IIPS 下载器的
可选皮肤，停服后不再下发）。所以：

* `LoadImageFromBuffer failed` 是**正常现象**，不是我们破坏的，也不是停服篡改。
* **它不阻止建管道** —— 按 §3.1，管道创建路径不经过 UI 加载。
* 真正卡住 `IIPS\HostPid` 的是**策略服务器连不上**（`ctrl.iips.qq.com` 现已变址/停服）。

---

## 5. `[100]` 的重新定位（最重要）

### 5.1 三层弹框互不替代（已实测）

| 层 | 呈现方式 | 文案 key | 触发条件 |
|---|---|---|---|
| TCLS | Win32 `#32770` | `WIN_NO_TCLS` | 未经登录器启动 |
| IIPS | Win32 `#32770` | `WIN_IIPS_INIT_ERROR` (`0x8189FEC` → "初始化IIPS错误：%x。") | IIPS 管道握手失败 |
| 大厅 | **游戏内 Scaleform 渲染** | `@SF_UI_DW_LIVE_CONNECTING_FAILED` | 大厅层判定失败 |

实拍证据：`CODOLServer\_pop_trace\shots\desktop_game.png`（`[100]无法连接大厅服务!`，
面板右上角还有 `官网` 按钮 ⇒ 游戏内 UI）。

### 5.2 固化启动链**没有**触发 Win32 IIPS 弹框

`_pop_trace\chain1/chain2/chain3\windows.jsonl` 里，走固化链时**没有任何 `#32770`**。
只有直接双击 exe（方式 A）才弹 `初始化IIPS错误`。

⇒ 固化链下 IIPS 层是**过的**（或至少没有进入失败分支），游戏推进到了大厅层。

### 5.3 `[100]` 的真身

```
[100] = 游戏内 UI 面板 + 一个整数
文案 = @SF_UI_DW_LIVE_CONNECTING_FAILED  ("无法连接大厅服务!")
整数 = 100
```

关键点（推翻旧结论）：

* `100` **不是** `BD_LOBBY_PROTOCOL_VERSION_FAILURE`（该枚举值是 17）。
* `100` 与 `116.130.224.66:8000` 的时间吻合是**巧合/旁证不足**：
  该 UDP 探测的应答是**成功**的（客户端收到 73 字节），
  "收到应答"与"画 `[100]`"同时出现，不构成因果。
* `[` `%s` `]` `%s` 格式串位于 exe VA `0x00DE0768`，
  与 key 块相邻 ⇒ 面板文字是 **printf 风格拼装**（token + 本地化串），
  `100` 是被拼进去的第一个参数。
* 真正画 `[100]` 的代码在 `.tp3` 加密段（RVA < 0x594000），
  现有运行期 dump（只覆盖 RVA ≥ 0x594000）**看不到**，这是本项目静态分析的天花板。

### 5.4 大厅连接**从未被发起**

多轮抓包一致：**游戏进程从未对任何地址建立大厅性质的连接**。
它做的全是：CDN 下载（80/443）、QoS 心跳（8081）、SSDP（1900）、TQoS 探测（8000 UDP）。

⇒ `[100]` 是"**客户端判定自己的启动前置条件不满足，于是根本没进大厅阶段**"，
不是"连了大厅但被拒绝"。

---

## 6. 结论与下一步（重排优先级）

### 已结案

| 议题 | 结论 |
|---|---|
| `iips.dll` 是否被官方停服篡改 | **否**，是本项目 9/21 自己打桩（`mov eax,0x12345678; ret; ret` + RTTI 清零），签名被照搬导致 `HashMismatch`；现已回退出厂 `72DDB9D1`（Valid） |
| 改 `enable_iips` / `iips_url` | **无效**，它们是回显不是开关 |
| TPFUI 图片缺失是根因 | **否**，出厂就没有这套皮肤；且管道创建不经 UI |
| `116.130.224.66:8000` 是 `[100]` 成因 | **否**（证据不足且方向上不符） |
| `ctrl.iips.qq.com` 是不是 `116.130.224.66` | **不是**（81.71.56.27/168） |

### 下一步（按投入产出排序）

1. **让 IIPSHostApp 真的建起管道**（最小、可验证）
   本地起 AES-128 策略应答，使 `iips_policymsg_api_create` 返回 ≥ 0。
   一旦 `\\.\Pipe\<MD5(lower(iips_url))>` 出现且 `IIPS\HostPid` 被写，
   IIPS 层就彻底干净，可排除它对后续链路的干扰。

2. **抓 `[100]` 的发起函数**（决定性问题）
   现有运行期 dump 覆盖不到 RVA < 0x594000。
   需要在**更早**的时刻 dump（模块基址 `0x00400000` 全覆盖），
   或在 `[100]` 出现瞬间对进程做全镜像 dump，然后在此 dump 上搜
   `@SF_UI_DW_LIVE_CONNECTING_FAILED` 的 4 字节引用。

3. **拿到"大厅地址从哪来"**
   现有链路里游戏从未见过大厅地址。最可能的下发点是
   `TCLS` 交接块（`TCLS_SHAREDMEMEMORY<pid>`）或 `TQMCenter` 会话。
   建议：挂钩 `OpenFileMapping`/`MapViewOfFile`，或在交接块入手。

4. **不再追**：`116.130.224.66`、`182.50.14.56:8081`、`239.255.255.250:1900`、
   `iips.ini` 的 `enable_iips`、TPFUI 皮肤。

---

## 7. 本轮新增工具

```
CODOLServer\_mainline\_m1_hostapp_conds.py   HostPid/策略/管道字符串 + CreateNamedPipeA 调用点
CODOLServer\_mainline\_m2_hostapp_deps.py    gate 函数 0x1000F370 语义 + 日志串 xref
CODOLServer\_mainline\_m3_resourceloader.py  ResourceLoader::Start 0x10025800 全反汇编
```

## 8. 关键 VA 索引（IIPSHost.dll，基址 0x10000000）

| 事项 | VA |
|---|---|
| `ResourceLoader::Start()` | 0x10025800 |
| 策略日志 start / failed / end | 串 0x10065130 / 0x10065180 / 0x100651D0（ref 0x10025A55 / 0x10025AA5 / 0x10025ACB） |
| `iips_policymsg_api_create` 调用点 | 0x10025A7B |
| 管道日志 start / failed / succeed | ref 0x10026861 / 0x100268B5 / 0x100268DC |
| 管道名前缀 `"\\.\Pipe\"` | 串 0x100625A4（ref 0x1000DB37） |
| `CreateNamedPipeA` 调用点 | 0x1000DBD1（IAT 槽 0x1005D148） |
| `ConnectNamedPipe` 调用点 | 0x1000D923 / 0x1000DA0C / 0x1000DC57 / 0x1000DDC9 |
| `WaitForMultipleObjects` 调用点 | 0x1000DC72 / 0x1000DEB0（49 handles） |
| 12 实例循环 | 0x1000DC07（`cmp ebp,0xC`，步长 0x37C） |
