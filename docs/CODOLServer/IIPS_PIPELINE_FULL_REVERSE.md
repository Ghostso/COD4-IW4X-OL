# IIPS 管线全链路逆向（上线 + 下线，一查到底）

日期：2026-09-25
目标：`COD OL\IIPS\` 全部组件、上下游调用链、管道/共享内存/策略服务器协议、备份件
证据等级：**反汇编逐条确认（VA 级）**

---

## 0. 一句话结论

IIPS 是**资源下载/修补子系统**（不是大厅）。它的形态是：

```
游戏进程                          IIPSHostApp.exe 进程
  iips.dll (ResourceManagerII)  ⇄  命名管道(消息模式, 791B/条)  ⇄  IIPSHost.dll
        │                                                          ├─ Download.dll  (HTTP/HTTPS 下载)
        │                                                          ├─ iips_policymsg.dll (UDP 策略服务器)
        │                                                          └─ IFS2.dll / IIPSVFS.dll (本地归档)
        └─ IIPS\HostPid (文本 PID) + Global\IIPSShareState_MMF_<key> 共享内存
```

`[100]` 与 IIPS 初始化失败**是两件不同的事**（见第 8 节）。

---

## 1. 组件清单（导出表 + 依赖，实测）

| 组件 | 大小 | 导出 | 依赖关键 | 网络 |
|---|---:|---|---|---|
| `iips.dll` | 347704 | `GetResourceManager`, `ReleaseResourceManager`, `GetResourceManagerII`, `ReleaseResourceManagerII` | KERNEL32/USER32/**WS2_32/WSOCK32** | 有 |
| `IIPSHost.dll` | 601656 | `GetIIPSHostApp`, `ReleaseIIPSHostApp` | **Download.dll**, **iips_policymsg.dll**, WS2_32 | 有 |
| `iips_policymsg.dll` | 81464 | `iips_policymsg_api_create/destroy/recv/send` | WS2_32 | **有（UDP 策略服务器）** |
| `IFS2.dll` | 601656 | `CreateIFSLibDll`, `DestoryIFSLibDll`, `IFSDllVerifyApiCompatable` | 仅 KERNEL32 等 | 无 |
| `IIPSVFS.dll` | 216120 | `ICreateBuffer`, `ICreateCoderRWFilter`, `ICreateZlibRWFilter`, `ICreateFileMapper`, `ICreateFileSysMgr`, `ICreateVFileSys`, … 共 9 | 仅 KERNEL32 | 无 |
| `Download.dll` | 1228344 | `TmgrCreate`, `TmgrStartup`, `TmgrNewTask`, `TmgrSetTQOSReportSettings`, `TmgrSetBusinessID`, … 共 46 | WS2_32 + **WLDAP32** | 有 |
| `p2papp.dll` | 2043960 | `IP2PApp`, `IP2PCore`, `IP2PData`, `IHttpFile`, `IP2PDbg` | WS2_32 | 有 |
| `IIPSRepair.dll` | 220728 | `CreateIIPSRepair`, `RealeaseIIPSRepair` | WS2_32 | 有 |
| `IIPSLaunchRestore.dll` | 618040 | `CreateIIPSRepair`, `RealeaseIIPSRepair` | WS2_32 | 有 |
| `IIPSStats.dll` | 273976 | `GetIIPSStats`, `ReleaseIIPSStats` | GDI32（统计窗口 UI） | 无 |
| `iips_policymsg.dll` | 81464 | 见上 | WS2_32 | 有 |
| `IIPSHostApp.exe` | 290360 | —（主程序） | 加载 IIPSHost.dll | — |

**RTTI 对象模型（iips.dll）**：`IIPSWndMsgProcessor`, `CNIFS`, `NIFSFileWrapperImp`, `ResourceManager`, `ResourceManagerII`, `CFilePieceCachedReader`, `CIIPSQosReporter`, `CIFSRepairWatcher`, `IIPSClientListener`

**RTTI 对象模型（IIPSHost.dll）**：`IIPSHostApp`, `ResourceDownloader`, `ResourceLoader`, `NIFSPrePackageMgr`, `GroupFileDownloader`, `IFTFileWrapperTQosReport`, `CIFSFileRestorer`, `ClientQos`, `SpeedCounter`, `CIIPSMixedMetaFileTask`, `CIIPSDownloadMetaFileTask`, `CIIPSDecompressMetaFileTask`, `CIIPSDownloadWholeIFSFileTask`

---

## 2. 上线（上游调用链）：谁调用 IIPS

```
[游戏] codoMP_client_shipRetail.exe
   └─ LoadLibrary("IIPS\iips.dll")                    ← exe 内字符串 VA 0x00DB53F0
      └─ iips.dll!GetResourceManagerII(szUrl)         ← 导出序号 3
         └─ ResourceManagerII::Initialize(szUrl)
```

**游戏侧配置来源**（exe 内字符串，紧邻成簇，是"读 ini → 打日志 → 传下游"，**不是行为分支**）：

```
iips_debug                    @ 0x00DC7E38
iips.ini                      @ 0x00DC7E44
enable_iips=%d                @ 0x00DC7E50
iips_url=%s                   @ 0x00DC7E60
iips_enableOptionalDownloads  @ 0x00DC7E70
```

> 结论：反复改 `enable_iips` / `iips_url` 对 `[100]` 无效，这一点已被静态证据解释。

---

## 3. 下线（下游调用链）：IIPS 调用谁

```
ResourceManagerII::Initialize
  ├─ 本地：IFS.dll(IFS2.dll) + IIPSFileList.ini + IIPSDownload\
  ├─ LaunchIIPSHostApp  →  CreateProcess("IIPSHostApp.exe" "/mode iipslaunch")
  ├─ IIPSClient::Start  →  CreateFile("\\.\Pipe\<name>")   [消息模式]
  └─ InitializeWorkAfterClientConnected
        ├─ IIPShareState.Open("Global\IIPSShareState_MMF_...")
        └─ LoadFileList()

[IIPSHostApp 进程内]
  IIPSHost.dll!GetIIPSHostApp
    ├─ ResourceDownloader / ResourceLoader   → Download.dll (Tmgr*) → HTTP/HTTPS
    ├─ iips_policymsg.dll                    → UDP 策略服务器
    └─ IFS2.dll / IIPSVFS.dll                → 本地归档读写
```

---

## 4. `ResourceManagerII::Initialize()` 逐步失败点（iips.dll 内嵌日志串，按代码顺序）

```
[begin]
  IIPSERR_PARAM                               (szUrl 为 NULL)
  IIPSERR_PARAM,getkey failed
  IIPSERR_GETMODULEPATH                       (取主模块目录)
  SetPrivilege / SetPrivilege failed
  IIPSERR_PRIVILEGE_SE_CREATE_GLOBAL_NAME     ← 需要 SeCreateGlobalPrivilege
  IIPSWndMsgProcessor::Initialize start/end
  IIPSERR_WINMSG_INIT                         (窗口类 _IIPS_WND_CLASS_)
  IIPSERR_GETMAINMODULEPATH                   (configFilePath)
  LoadLibrary IFS.dll → LoadIFS()
  IIPSERR_IFS_LOAD_DLL_ERROR   [NifsInitError %d]
  IIPSERR_IFS_DLL_CANT_FIND_FUNCTION
  IIPSERR_FILELIST_ERROR       (IIPSFileList.ini)
  IIPSTATE_START_REPAIR_IFSFILE [ConnectCount %d]
  IIPSERR_OPEN_HOSTSHAREINFO    [ConnectCount %d]   ← 读 IIPS\HostPid
  LaunchIIPSHostApp start
  LaunchIIPSHostApp failed / IIPSERR_IIPSHOST_INIT
  m_iipsClient connect
  firstime m_iipsClient.Start failed
  synchronous pipe connect failed / IIPSERR_PIPE_INIT   ← “failed to conncet pipe”
  pipe connect succeed(start other action of init)
  ── 之后进入 InitializeWorkAfterClientConnected ──
  m_iipsShareState.Open() failed / IIPSERR_SHARESTATE_INIT
  LoadFileList() failed / IIPSERR_IFS_INIT
  OpenFileMapping() failed
  ResourceManagerII::Initialize() succeed
```

`IIPSClient.ini [ErrMsg]` 的错误码表（7/8/9/38/39）与本链一致。

---

## 5. 管道契约（伪造 host 的核心）

| 项 | 值 | 证据 |
|---|---|---|
| 前缀 | `\\.\Pipe\` | VA 0x10034388，xref VA 0x10003D72 |
| 名字编码 | `MultiByteToWideChar(0xFDE9=CP_UTF8)` | 0x10003D11 / 0x10003D34 |
| 管道类型 | **消息模式** | `SetNamedPipeHandleState(..., lpMode=2)` @ 0x10003E70（2 = PIPE_READMODE_MESSAGE） |
| **每条消息长度** | **0x317 = 791 字节** | `ReadFile(...,0x317,...)` @ 0x10003377/0x10003384；`mov ecx,0xC5; rep movsd; movsw; movsb` @ 0x1001534A 与 0x10003F5C |
| **cmd 字段偏移** | **+0x02（u32）** | `mov eax,[eax+2]` @ 0x10015356；`mov ecx,[eax+2]` @ 0x1001538A；发送侧 `mov eax,[ebx+2]` @ 0x10003C42 |
| 收到后投递 | `SendMessage(hWnd, 0x464, 0, msgPtr)` | 0x1001536F–0x10015376 |
| 有效 cmd | 1 与 2（`sub eax,1 / je` 链） | 0x100153CE–0x100153D9 |
| 监听线程 | `IIPSClientListenThread`，`WaitForMultipleObjects(4 handles)` | 0x100033A0–0x100033A7 |
| 重连 | `ProcessHostAppCrush() → restart IIPSHostApp.exe` | VA 0x10033F60/0x10033FB4 |

**791 字节记录布局（已确认部分）**

```
+0x000  u16   保留 / 长度
+0x002  u32   cmd            ← SendMsg 打印的 msg.cmd
+0x006  ...   payload
共 0x317 = 791 字节
```

**接收后分派路径**
```
IIPSClientListenThread  ReadFile(pipe, buf, 0x317)
  → ResourceManagerII::OnRecvMsg(msg)          @ 0x10015320
      cmd = *(u32*)(msg + 2)                    @ 0x10015356
      SendMessage(hWnd, 0x464, 0, msg)          @ 0x10015376   ← 交给 IIPSWndMsgProcessor
      （无窗口时走 0x100370D0 "[window error][CMD %d][hWnd %d]" 分支）
```

---

## 5A. 版本路径与键派生

```
sprintf_s(buf, 0x64, "IIPS/%hu/%hu/%hu/%hu", v1, v2, v3, v4)   @ 0x100123B3
IIPS Unknown version                                            @ 0x10035EF0
NOT SET UIN                                                     @ 0x10035F08
```

4 个 u16 由 0x10011160 解析得出（版本串分解）。该路径用于拼 IIPS 包 URL / 派生 share key；
`Global\IIPSShareState_MMF_<key>` 与 `<Mutex_<key>` 的 `<key>` 即由此派生。

---

## 6. 共享内存与 HostPid

```
Global\IIPSShareState_MMF_<key>     VA 0x10035E38   xref VA 0x10011B17
Global\IIPSShareState_Mutex_<key>   VA 0x10035E54   xref VA 0x10011C97
IIPS\%hu/%hu/%hu/%hu                VA 0x10035ED8   (版本/键派生格式)
IIPS\HostPid                        文本文件，内容 = IIPSHostApp 的 PID
```

另有互斥体单实例保护：`CreateMutexW` + `GetLastError()==0x514`(ERROR_ALREADY_EXISTS) @ 0x10005130 与 0x100051F0。

---

## 6A. 【核心】管道名派生 = MD5（服务端 IIPSHost.dll 实测）

**服务端才是真正建管道的一方**，在 `IIPSHost.dll`：

```
ResourceLoader::Start()
  → IIPSHostApp::Start()              "[IIPSHostApp::Start()][IIPSHostApp start succeed]"
      → CreateNamedPipeA               @ 0x1000DBD1
      → ConnectNamedPipe               @ 0x1000DC55
  → IIPSHost.ListenThread()            "[IIPSHost.ListenThread()][WaitForMultipleObjects]"
```

**`CreateNamedPipeA` 实参（栈推送顺序，逐条确认）**

```
0x1000DBB9  push 0
0x1000DBBB  push 0
0x1000DBBD  push 0x186A0000          ; nInBufferSize
0x1000DBC2  push 0x186A0000          ; nOutBufferSize
0x1000DBC7  push 0x0C                ; nMaxInstances = 12
0x1000DBC9  push 0x06                ; PIPE_TYPE_MESSAGE|PIPE_READMODE_MESSAGE
0x1000DBCB  push 0x40000003          ; PIPE_ACCESS_DUPLEX | FILE_FLAG_OVERLAPPED
0x1000DBD0  push name
0x1000DBD1  call CreateNamedPipeA
```

随后 `cmp ebp,0xC` 循环 **12 个实例**；每实例记录步长 **0x37C**。

**管道名生成链**

```
0x1000DB37  push 0x100625A4          ; "\\.\Pipe\"
0x1000DB45  std::operator+           ; "\\.\Pipe\" + <name>

<name> 由 0x1000F5A0 生成：
  0x1000F64C  push _mbctolower       ; 输入先转小写
  0x1000F651  call 0x1000F8C0        ; 变换
  0x1000F6B8  call 0x10010870        ; ← MD5 + 输出

0x10010870 = MD5：
  0x10010891  mov [esp+0x18], 0x67452301   ; 标准 MD5 IV
  0x10010899  mov [esp+0x1c], 0xEFCDAB89
  0x100108A1  mov [esp+0x20], 0x98BADCFE
  0x100108A9  mov [esp+0x24], 0x10325476
  0x100108BD  call 0x10010430              ; MD5 block update
  0x100108CB  call 0x10010710              ; MD5 final (+ hex/输出)
```

### 结论

```
管道名 = "\\.\Pipe\" + <MD5 派生串>
输入端 = iips_url（经 lowercase）
```

当前配置对应值（本机算得，供伪造用）：

| iips_url | MD5 |
|---|---|
| `http://127.0.0.1/` | `699fcf4591fc23e79b839d8819904293` |
| `http://127.0.0.1:8080/` | `ee71830d485aca6abfca0ebb34561f72` |
| `http://10.231.2.181/` | `550fef2869b809ae4a23f26a87036f62` |

> 注：`0x1000F8C0` 的具体变换（是否再做 Base32/截断/前缀）未完全展开，
> 需动态抓一次真实管道名做定案（见第 12 节待办 1）。

---

## 7. 策略服务器协议 `ctrl.iips.qq.com:8000`（UDP）

配置来自 `IIPSHostApp.ini`：
```
[IIPSPolicySvrInfo]
Address=udp://ctrl.iips.qq.com:8000
HeartbeatInterval=60
BusinessID=3058
```

**schema（TDR 风格字段表，逐字提取）**

```
cs_policy_msg
  CS_POLICY_MSG_ENCLEN / CS_POLICY_MSG_MAGIC / CS_POLICY_MSG_REQ / CS_POLICY_MSG_RES
  CSPolicyMsg
    Head(CSPolicyMsgHead): Version, Magic, PkgLen, CmdID
    Body(CSPolicyMsgBody)
      Req(CSPolicyMsgReq): BusID, LastImmDLSize, LastImmDLTime,
                           LastPreDLSize, LastPreDLTime, NeedUploadBitmap
      Res(CSPolicyMsgRes): MaxPreDLSpeed, MaxConnNum, MaxDLSpeed, MaxRealTimeULSpeed,
                           MaxPreULSpeed, MaxInGamePreULSpeed, NeedUploadBitmap,
                           ReportIntervalMs, ReportUploadSpeedBytePerSecond,
                           Res1, Res2, Res3
  另有 CSTransMsg: Head(Version, Magic, HeadLen, BodyLen) + Body
```

**加密**：AES-128，**硬编码密钥 `iips#policy!@#$%`**（16 字节）
- `taes_setkey` @ 0x100061C0：`[ks+0xF0] = 0xA`（10 轮，AES-128），字节序翻转 + T 表 `0x10008CF0` / `0x100090F0`
- 调用点 @ 0x1000116E（push key） → 0x10001177
- 会话上下文：`calloc(0x830)`；`socket(AF_INET, ...)`；`[ctx+8]=3`

**注意**：`Download.dll` 还导出 `TmgrSetTQOSReportSettings` / `TmgrSetBusinessID`，说明策略服务器同时承担**下载限速下发**与 **TQoS 上报**两种角色。

---

## 8. `[100]` 与 IIPS 的关系（重要澄清）

两者**不是同一层**：

| 触发路径 | 文案 | localization key |
|---|---|---|
| 直接启动 exe | 致命错误 / 请使用腾讯游戏登录器(TCLS文件夹内的Client.exe)启动游戏。 | `WIN_ERROR` + `WIN_NO_TCLS` |
| IIPS 初始化失败 | 初始化IIPS错误：%x。 | `WIN_IIPS_INIT_ERROR` |
| 大厅连不上（走启动链后） | 无法连接大厅服务! | `@SF_UI_DW_LIVE_CONNECTING_FAILED` |
| 已连过大厅但断开 | 与大厅服务失去连接 | `@SF_UI_DW_LIVE_DISCONNECTED` |

实测（干净启动，不改主机名）：游戏**能**拉起 `IIPSHostApp`、**能**发起外网连接（101.72.248.61:443/80、61.182.140.168:80、116.131.60.72:443，`TQMCenter → 101.226.32.186:7003`），说明 IIPS 失败**不必然阻断**后续网络层。`[100]` 属于大厅层。

---

## 9. IIPSHostApp 实际失败点（TenioLog 实测）

```
[Tenio_Error] Can't find Component(985) Creator From Dll List!
LoadImage LoadImageFromBuffer failed
    file=...\COD OL\IIPS\\TPFUI\IIPSRes\back\<中文>\...png
TPFFile Load file(...\TPFUI\IIPSRes\back\SystemSetting\...png) failed!
```

路径里 `IIPS\\TPFUI` 出现**双反斜杠**，且沙箱 `IIPSRes` 为空 → UI 资源全部加载失败 → 不建管道、不写 `HostPid` → 游戏侧 `IIPSERR_PIPE_INIT`。

---

## 10. 备份件盘点

| 路径 | 内容 | 说明 |
|---|---|---|
| `backups\IIPS_RESTORE_20260925_161510\iips.dll.modified_E2367C48` | 被改动版 iips.dll | 849 字节差异（见第 11 节） |
| `backups\S2_IIPS_RESTORE_20260925_161647\IIPS_iips.dll` | 备份 | 还原点 |
| `backups\S2_IIPS_RESTORE_20260925_161702\IIPS_iips.dll` | 备份 | 还原点 |
| `backups\IIPS_FIX_20260925_155502\` | IIPSClient.ini / IIPSHostApp.ini / iips.ini(原始+沙箱) | 配置对照 |
| `backups\IIPS_SCRIPTMANAGER_20260924_202100\` | Tenio/ScriptManager/Lua51 全套 + SHA256 清单 | 那轮 Tenio 替换实验 |
| `backups\hostpid_orig_20260925_160422.bak` | `IIPS\HostPid`（16B = "20128"） | 原始 PID 文件 |
| `backups\iips_ini_orig_20260925_160422.bak` | `iips.ini` 原始 | 出厂值 |
| `工具\EX035_DIR\IIPS\iips.dll` | **出厂原版** 347704B `72DDB9D1`（签名 Valid） | 唯一可信基线 |

---

## 11. iips.dll 的 849 字节差异（已定性：本项目自伤）

`工具\EX035_DIR\IIPS\iips.dll`（出厂，`72DDB9D1`） vs 曾生效的 `E2367C48`：

| 区域 | 基线 | 被改 |
|---|---|---|
| `.text` RVA 0x1000（7B） | `mov [ecx],0x10033D18; jmp [0x10033298]` | **`mov eax,0x12345678; ret; ret`** |
| `.rdata` RVA 0x33000（98B） | 指针表 `0x3F92A…` | 注入 `"GetResourceManagerII\0ReleaseResourceManagerII\0"` + 名称指针数组 |
| `.data` RVA 0x42000（744B） | MSVC RTTI/异常元数据 | 整体清零 |

节表与导出表**逐字节相同**。改动时间落在此前 9/21 的 LocalRM PE 手术窗口内，`mov eax,0x12345678` 与本项目既有的 LocalRM 桩逐字节一致 ⇒ **不是腾讯停服植入**。当前 `COD OL\IIPS\iips.dll` 已回退为 `72DDB9D1`（Valid）。

---

## 12. 结论与下一步

**已吃透**：组件依赖、上下游调用链、管道契约（名/消息模式/791B/cmd@+2）、共享内存、策略服务器 schema + AES 密钥、初始化逐步失败点、备份件。

**可立即用于写服务器的两个契约**：
1. 伪造 `IIPSHostApp`：建管道 + 写 `HostPid` + 开 `Global\IIPSShareState_MMF_`，按 791B 记录应答（cmd@+2）。
2. 伪造策略服务器：UDP，AES-128(`iips#policy!@#$%`)，`CSPolicyMsg` schema 应答。

**优先级**：
1. 确定管道名派生（`IIPS\%hu/%hu/%hu/%hu` → pipe name）——这是伪造 host 的最后一环。
2. 确定 cmd 1 / cmd 2 的语义与应答（决定 `InitializeWorkAfterClientConnected` 能否通过）。
3. 备选：直接绕过 IIPS（`enable_iips` 非开关，需在 exe 层或退回到"走启动链 + 伪造 TCLS"路线）。
