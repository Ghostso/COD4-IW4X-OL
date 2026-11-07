# CODOL 复活项目 — 全量成果整理 + 方向决策

日期：2026-09-25
范围：2026-09-19 ~ 2026-09-25 全部实验、结论、资产、待办

---

## 一、时间线（实际做过什么）

| 日期 | 阶段 | 主要内容 | 结果 |
|---|---|---|---|
| 09-19 ~ 09-21 | **ICH001-059** | exe 壳结构、.tp3/.tvm0、引擎区解密、VM 调度表、资源事件 | 摸清壳；**代码加密，磁盘静态反汇编无效** |
| 09-21 | **RESTORE001-005** | 运行时函数 dump、引擎桥接、LocalRM 尝试 | 拿到 14 个运行时函数；写出 LocalRM*.dll |
| 09-22 | **RESTORE_LOCALRM_005/006** | 自研 ResourceManager Provider（替代 IIPS） | LocalRM_v3.dll 通过 LoadLibrary/GetProcAddress/vtable 全套自检 |
| 09-22 | **restore_iips_contract_001/002、restore003/005/006** | IIPS 契约对照实验 | 确认 IIPS 契约面 |
| 09-24 | **抓包 + 服务器启动** | 首次完整抓包、TCLS 分析、GDP 协议、IW4X 可行性 | 拿到 GDP TDR、TCLS 目录协议 |
| 09-25 上午 | **运行时逆向** | 引擎 dump、cfg 加密、平台 AES 扫描 | 确认引擎 gap 映射 |
| 09-25 下午 | **IIPS 深挖** | 管道/共享内存/策略服务器/上线全链 | 契约完整 |
| 09-25 傍晚 | **弹窗取证 + P2P** | 实拍 [100]、p2papp 结案 | [100] 机制钉死 |

---

## 二、已确证事实（按层，全部有 VA/实测证据）

### L0 引擎 / 壳

```
exe = 7,841,344 B，ImageBase 0x00400000，7 个 .tp3 段 + 1 个 .tvm0
导入表只有 1 项：codoMP_client_shipRetailBase.dll!ordinal_1
磁盘代码加密（entry RVA 0x0E5DC690 反汇编为垃圾）
引擎区 0x00994000..0x00CA789A：磁盘为零，运行时由 Base.dll 解出（t≈5s）
换算：exe 字符串 VA = 文件偏移 + 0x714000
     运行期 dump offset = RVA − 0x594000
```

### L1 启动

```
直接双击 exe  -> Win32 #32770「请使用腾讯游戏登录器启动」WIN_NO_TCLS   实测
固化启动链    -> 通过，进游戏                                          唯一入口
TCLS 交接块   -> 共享内存 TCLS_SHAREDMEMEMORY<pid>, size 0x7AC,
                 +0x008/+0x00C 必须为 0（非 0 崩）
```

### L2 IIPS（契约完整）

```
管道名      = \\.\Pipe\ + MD5(lower(iips_url))        [IIPSHost.dll 0x10010870]
管道类型    = MESSAGE，12 实例                        [0x1000DBD1 CreateNamedPipeA]
消息        = 定长 791 字节，cmd=u32@+0x02
cmd 1..21   -> 1=WriteBitmap, 2=show ui,
               10/12/17/18/19/21 -> PostMessage(0x506C/6E/71/74/75/76)
共享内存    = Global\IIPSShareState_MMF_<key> / _Mutex_<key>
前置文件    = IIPS\HostPid（16B UTF-16 PID）
策略服务器  = UDP + CSPolicyMsg schema + AES-128 密钥 "iips#policy!@#$%"
UI 层       = Scaleform GFx（TenTPF.dll = TPFUI）
```

### L3 服务器发现

```
ied-tqos.qq.com        -> 116.130.224.66     [exe 硬编码 VA 0x00DD98A0]
tqos.gamesafe.qq.com   -> 182.50.14.56:8081  [AFD 实测 176 包]
stun1-tub.codol.qq.com -> 121.51.232.95
ctrl.iips.qq.com       -> 81.71.56.168/.27
TQoS 请求: 'ur'+u16(16)+u16(8)+u16(3)+u16(0)+u16(0x0B)+u32(seq)+u32(BusinessID=100)+u16(24)+u16(0)
最小应答(已接受): 'ur'+u16(16)+u16(8)+u16(4)+u16(0)+u16(0)+u32(seq)+u32(100)+u32(0)
AFD 实测: t≈20.3s 连接 116.130.224.66:8000 -> 之后画 [100]
```

### L4 大厅

```
[100]无法连接大厅服务! = 游戏内 Scaleform 渲染面板（实拍确认）
key = @SF_UI_DW_LIVE_CONNECTING_FAILED   exe VA 0x00DE0640
三层失败区分：WIN_NO_TCLS(0x00DDBF80) / WIN_IIPS_INIT_ERROR(0x00DC93A8) / [100](0x00DE0640)
GDP 协议 = GDPOpenProtocol.tdr (438,856 B, 343 命令 + 592 类型)
线格式   = GDPPkgHead(Version+CmdID+CmdType+headlen+bodylen+SubCmdId)
大厅栈   = Demonware Blaze / dwLobby（BD_LOBBY_*, DW_LOBBY_*）
```

### L5 资源 / P2P

```
p2papp.dll = 腾讯通用 P2P 中间件（2013-04-09），非 CODOL 专属
  上报 QQ 号 [p2papi] SetQQ
  占端口 1863 / 28000 做种
  CODOL profile: config/ps2/downloadtpt/stat.gamedl.qq.com
WLDAP32 = libcurl 自带 LDAP 支持（排除后门）
IIPS UI 资源 = 179 个 png 里 178 个是 69 字节 1x1 占位壳（原始目录同样）
IIPSDownload = 975 文件 / 22.14 GB，本地写入（非网络下载）
```

---

## 三、已排除（不要再做，避免重复劳动）

| 项 | 排除理由 |
|---|---|
| 改 enable_iips / iips_url 影响 [100] | 该值只是回显，非行为分支 |
| iips.dll 被官方停服植入 | 849B 改动 = 本项目自己 9/21 打桩（mov eax,0x12345678） |
| iips.dll 双反斜杠路径 bug | **证伪**：\\ 会被 Windows 折叠，且文件确实存在 |
| WLDAP32 是后门 | libcurl 组件 |
| 8081 是腾讯电脑管家、与 [100] 无关 | 错误；tqos.gamesafe.qq.com:8081 是活的 TQoS 通道 |
| .tvm0 与引擎区有关 | 重叠 0 字节 |
| 116.130.224.66 是监控 IP | 它就是 ied-tqos.qq.com 的 DNS 结果，正常 TQoS 端点 |
| 在磁盘上反汇编 .tp3 | 代码加密，无效 |

---

## 四、我们手上的资产（可复用）

| 资产 | 位置 | 价值 |
|---|---|---|
| **IW4X 完整源码** | IW4X\Client核心代码\iw4x-client | ★★★ IW4 血脉，网络/引擎逻辑可参考 |
| **Unlinker.exe / zonebuilder.exe** | E:\IW4X | ★★★ **COD fastfile 解包/重打包工具** |
| 正式 MW2 安装 | G:\SteamLibrary\...\MW2 | ★★ 对照用 |
| 提权常驻代理 | CODOLServer\_mainline\agent_client.py (pid 8788) | ★★★ 免 UAC 全自动 |
| 引擎运行期 dump | run_codol_001\runs\ENGINE_DUMP_*\engine\engine_best.bin | ★★ 明文代码 |
| LocalRM_v3.dll | 根目录 | ★★ 自研 ResourceManager 替代品，已过全套自检 |
| GDP 命令表 | CODOLServer\GDP_COMMANDS.csv / GDP_CMD_MAP.csv | ★★ |
| gdp_server.py / fake_tqos_server.py | CODOLServer\_mainline\ | ★★ 服务器骨架 |
| 实拍 [100] | CODOLServer\_pop_trace\shots\desktop_game.png | ★ 证据 |

---

## 五、方向点评估（6 个）

| # | 方向 | 目标 | 难度 | 依赖 | 价值 | 风险 |
|---|---|---|---|---|---|---|
| **A** | 假 TQoS 闭环 | 让 [100] 消失 | 低 | 主机名改写+本地 UDP8000 | 高 | 低 |
| **B** | 伪造 IIPS host | IIPS 层干净 | 中 | 管道名 MD5 + 791B 消息 | 中 | 低 |
| **C** | 补 IIPS UI 真实资源 | IIPSHostApp 起得来 | 高 | 需原始资源包（已停服） | 低 | 高 |
| **D** | Scaleform 层压制 [100] | 绕过弹窗 | 中 | 需解 ui_mp.ff（有 Unlinker） | 中 | 中 |
| **E** | GDP/Blaze 大厅服务器 | 终极目标 | 极高 | 需先过 A/B | 极高 | 高 |
| **F** | IW4X 引擎复用 | 从引擎层替换联网栈 | 极高 | IW4X 源码 + 引擎知识 | 高 | 极高 |

### 详细说明

**A. 假 TQoS 闭环（推荐先做）**

```
1. suspend_host_redirect.py 把 ied-tqos.qq.com(VA 0x00DD98A0) 原地改写成 127.0.0.1
2. 本地 UDP 8000 起假 TQoS，按已知格式应答
3. 桌面截图看 [100] 是否消失 / 是否进入大厅握手
```

已具备全部要素：改写手法成熟、TQoS 格式已知、最小应答已被客户端接受。

**B. 伪造 IIPS host**

```
1. 建管道 \\.\Pipe\<MD5(lower(iips_url))>  （12 实例，MESSAGE 模式）
2. 写 IIPS\HostPid
3. 建 Global\IIPSShareState_MMF_<key>
4. 按 791B 记录应答 cmd 1..21
```

契约完整，但**不是通往大厅的必经之路**（IIPS 失败时游戏仍能到网络层）。

**C. 补 IIPS UI 资源（不推荐）**

178/179 是 1x1 占位壳，原始资源已随停服消失；补不齐。

**D. Scaleform 层压 [100]**

ui_mp.ff 是压缩 fastfile，但 **E:\IW4X\Unlinker.exe 可能就是解包器**。
若能解出 UI 影片，可定位那个错误面板并考虑压制。

**E. GDP/Blaze 大厅服务器（终极）**

需先 A（让游戏愿意连）+ B（可选）+ 大量 GDP 命令实现。TDR schema 已有。

**F. IW4X 引擎复用**

IW4X 是 IW4 客户端重写，与 CODOL 同血脉；但 CODOL 有 Tencent 专有层（GDP/TCLS/IIPS），
不是直接替换能解决的。

---

## 六、推荐路线

```
第 1 步  方向 A（假 TQoS 闭环）           <- 立刻可做，验证 [100] 是否可消除
第 2 步  若 A 成功 -> 观察游戏下一步动作（是否发起大厅 GDP 连接）
第 3 步  若需要 -> 方向 B（伪造 IIPS host）+ 方向 D（Scaleform 解包佐证）
第 4 步  方向 E（按 GDP 命令码逐个实现大厅）
并行     方向 D 的 Unlinker 解包尝试（独立、有工具）
```

---

## 七、资料索引（按主题）

| 主题 | 文档 |
|---|---|
| 端到端调用链 | CODOLServer\MASTER_CALL_CHAIN.md |
| IIPS 全链路 | CODOLServer\IIPS_PIPELINE_FULL_REVERSE.md |
| IIPS 上线/可疑 | CODOLServer\IIPS_UPSTREAM_AND_SUSPICIOUS.md |
| IIPS 策略协议 | CODOLServer\IIPS_POLICY_PROTOCOL.md |
| IIPS 取证 | CODOLServer\IIPS_TAMPER_FORENSIC.md、IIPS_ROOT_CAUSE.md |
| P2P 链 | CODOLServer\P2P_CHAIN_ANALYSIS.md |
| 弹窗取证 | CODOLServer\SUBAGENT_POPUP_TRACE.md |
| GDP 协议 | CODOLServer\GDP_WIRE_FORMAT.md、GDP_PROTOCOL_INDEX.md |
| TCLS | CODOLServer\TCLS_DIR_PROTOCOL.md、TCLS_SERVERDIR_ANALYSIS.md |
| 共享内存交接 | CODOLServer\SHM_HANDOFF_REVERSE.md |
| IW4X 可行性 | CODOLServer\IW4X_CODOL_FEASIBILITY.md、IW4X_CODOL_REUSE_REPORT.md |
| 操作手册 | CODOLServer\WORKING_HARNESS_NOTES.md |
| 引擎壳逆向历史 | 根目录 ICH001..ICH059_*（28 份决策） |
| LocalRM 历史 | 根目录 RESTORE_LOCALRM_005/006_DECISION.md |
| 无人值守存档 | CODOLServer\UNATTENDED_SESSION_20260925.md |

---

## 八、基础设施现状

```
提权代理      pid 8788，SeDebugPrivilege=True，免 UAC
弹窗监视      CODOLServer\_mainline\_popup_watch.py（窗口枚举）
桌面截图      CODOLServer\_mainline\_pop_desktop_shot.py（唯一能抓游戏内 UI）
固化启动      run_codol_001\capture_elevated_network.ps1 -DurationSeconds 75
             run_codol_001\run_direct_iips1_admin.cmd
运行中子代理  Boole（UI 资产解包）、Avicenna（弹窗产生机制）
```

---

## 九、待补缺口

1. [100] 面板的 GFx 影片名 / AS3 类名（子代理在查）
2. 触发点 VA + 100 的格式串位置（子代理在查）
3. cmd 5/6/8/9/11/13-16/20 的语义（未用到日志串）
4. ui_mp.ff 是否能用 E:\IW4X\Unlinker.exe 解开（**未试**）
5. GDP 命令码的完整实现（343 条）

---

## 十、重要更正：IW4X 与 CODOL 的关系

**IW4X ≠ CODOL。两者只是同引擎（IW4）的不同产品。**

```
IW4 引擎
  +-- IW4X   = 社区对 IW4(MW2 多人) 的客户端重写，去官方化、自建 master/好友列表
  +-- CODOL  = 腾讯基于 IW4 改的独立产品，叠加了整套专有层
```

**同引擎 != 可直接复用。** CODOL 在 IW4 之上叠了 IW4X 完全没有的层：

| 层 | CODOL | IW4X |
|---|---|---|
| 启动器 | TCLS / WeGame 登录器 + 共享内存交接块 | 无（直接跑 exe） |
| 资源系统 | IIPS + IFS2/NIFS + TPFUI(Scaleform) | 原生 fastfile/zone |
| 协议 | **GDP**（GDPOpenProtocol.tdr，343 命令） | 原生 IW4 网络协议 |
| 大厅 | 腾讯自研 + Demonware Blaze 混血 | IW4X 自建 master |
| 反作弊 | ACE / TGProtect | 无 |
| 平台 | QQ 号 / SSO / TQMCenter | Steam 系 |

**IW4X 的正确用途**
1. 作为"同引擎服务器"的参考实现，理解 IW4 引擎结构（zone/fastfile/网络栈）
2. 读它的**源码**来加速定位 CODOL 里对应的引擎函数
3. `E:\IW4X\Unlinker.exe` / `zonebuilder.exe` 是 **IW4 fastfile/zone 通用工具**；
   CODOL 的 `ui_mp.ff` 同属 fastfile 格式，**技术上值得一试**（方向 D），
   但 CODOL 的 .ff 可能被改版/加密，不保证能直接吃

**IW4X 不能的用途**
- 不能直接当 CODOL 服务器：GDP / TCLS / IIPS 三层它一个都没有
- 不能替代 CODOL 的联网栈：平台层（QQ 号/SSO）与 CODOL 完全不同
