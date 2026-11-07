# IIPS 全部上线（上游）+ 可疑目标重点分析

日期：2026-09-25
方法：静态导入表扫描 + 磁盘字符串 + 运行期 dump（`dump_off = RVA − 0x594000`）+ 配置核对

---

## 一、上线（上游）：谁调用 IIPS —— 共 5 条

### UP-1 引擎 C++（主上线）

```
codoMP_client_shipRetail.exe
  LoadLibrary("IIPS\iips.dll")        ← exe 字符串，文件偏移 0x6B53F0，VA 0x00DC93F0
  GetProcAddress("GetResourceManagerII")
  → ResourceManagerII::Initialize(url)
```

**注意**：`iips.dll` **没有被任何 DLL 静态导入**（我对 `COD OL`、`TCLS`、`tqm`、`Cross`、
`components`、`TenProtect` 全目录扫了 PE 导入表，只发现 `IIPSHost.dll → iips_policymsg.dll` 一条）。
⇒ iips.dll 只能由引擎**运行时 LoadLibrary** 加载。

### UP-2 Scaleform UI（AS3 绑定）—— 之前漏掉的一条

```
exe 内 ActionScript 绑定（`AS_` 前缀 = Scaleform AS）：
  AS_IIPS_IsPackReady
  AS_IIPS_RequestPack
  AS_IIPS_GetTotalPackSize
  AS_IIPS_GetDownloadedPackSize
  AS_IIPS_GetPackDownloadProgress
  RTTI: .?AVAS_IIPS_Response@@  .?AVAS_IIPS_GetPackDownloadProgress@@  ...

配套 dvar：
  iips_listpackages / iips_syncpackage / iips_syncfile
```

⇒ UI（"边玩边下"面板）会**直接通过 AS 调 IIPS** 请求/查询资源包。

### UP-3 配置文件

| 文件 | 关键项 |
|---|---|
| `IIPS\iips.ini`（游戏根目录 `iips.ini`） | `enable_iips` / `iips_url` / `iips_enableOptionalDownloads`（**回显，非开关**） |
| `IIPS\IIPSClient.ini` | `[TQOS] ReportInterval=1`、`LastReport=0`（每次运行都上报 TQoS） |
| `IIPS\iips-download.ini` | 最大任务/连接/限速、`DEFAULT_MAXTIMEOUT_DEADACTIVITY=30000` |
| `IIPS\UIOptions.ini` | `DownloadingWhilePlayGame=1`、`PrePackage=..\PreDownloadPkgs`、`VfsPath=..\..\data.vfs:;..\..\res.vfs:Res` |
| `IIPS\IIPSVersion.ini` | `V1.2.1.13` |

### UP-4 TCLS 下发

```
exe 字符串： TCLS\ifs_file        （文件偏移 0x6B5314）
           -ifs_file             （0x6B52E0）
           IIPS\IIPSDownload\%s  （0x6B5324/0x6B5340）
           IIPS: %d:%d:%s-%u:%s:%s:%lld:%lld:%d  （0x6B5358，上报格式）
```

⇒ TCLS 通过 `ifs_file` 把资源清单交给游戏，游戏再交给 IIPS。

### UP-5 进程/模块层

```
IIPSHostApp.exe (/mode iipslaunch)
   └─ IIPSHost.dll  (GetIIPSHostApp)
        ├─ iips_policymsg.dll   (策略服务器, UDP)
        ├─ Download.dll         (下载引擎)
        └─ IFS2.dll / IIPSVFS.dll
```

---

## 二、下线（下游）：IIPS 调用谁

```
ResourceManagerII
  → 命名管道 \\.\Pipe\<MD5(lower(url))>   （791 字节/条，cmd@+2）
  → IIPSHostApp.exe 进程
       ├─ Download.dll      → HTTP/HTTPS + P2P
       ├─ p2papp.dll        → P2P 上传/下载
       ├─ iips_policymsg.dll→ UDP 策略服务器（AES-128, key "iips#policy!@#$%"）
       └─ IFS2.dll/IIPSVFS  → 本地归档
```

---

## 三、可疑目标重点分析

### SUS-1 `p2papp.dll` —— **最可疑**

| 证据 | 含义 |
|---|---|
| `CP2PAppEx`, `CP2PCore`, `IP2PData`, `P2PNetwork`, `P2PTaskRunner`, `P2PDownloadCallback` | 完整 P2P 栈 |
| `[p2papi] SetQQ %u` | **把玩家 QQ 号塞进 P2P 模块**（身份/统计） |
| `[CP2PAppEx::NotifyQueryP2pShare] GetAdapterMaybe3G true/false` | 探测网络类型（3G/宽带） |
| `CP2PAppEx::ReportStatisticAtUnit GetDataMgr()->GetStatistic()` | 定时上报统计 |
| `http://127.0.0.1` | 与本机 P2P 核心通信 |
| `CISDDownload::SetSpeedLimit(... uP2PUploadSpeed ...)` | 有**上传**通道 |

⇒ 具备"上传带宽 + 身份标识 + 定时上报"三要素，是**隐私/资源占用**重点关注对象。

### SUS-2 `Download.dll` 的远端端点

```
http://rtstat.iips.qq.com:443/data/webpkg        ← IIPS 统计上报端点（实测字符串）
udp://%s:%d
LDAP local: ldap_simple_bind_s %s                ← 来自内嵌 libcurl（非恶意）
http://curl.haxx.se/rfc/cookie_spec.html         ← 证实内嵌 libcurl
WLDAP32.dll 16 个序号导入                        ← libcurl 的 LDAP 支持
```

⇒ `WLDAP32` 不是后门，是 **libcurl 自带 LDAP 支持**。但 `rtstat.iips.qq.com` 是真实上报端点。

### SUS-3 `iips_policymsg.dll` —— 弱加密

```
AES-128，密钥硬编码 "iips#policy!@#$%"（明文就在 .rdata）
taes_setkey @ 0x100061C0，轮数 10
```

⇒ 该协议的加密**可被我们完全复现**（写服务器时可直接用）。

### SUS-4 运行期新增/改动目录

| 路径 | 说明 |
|---|---|
| `IIPS\Snapshot`、`IIPS\vodcache`、`IIPS\Tenio`、`IIPS\TenioLog` | 运行期生成 |
| `IIPS\Progress.ini` | 运行期改写（`[DownloadInfo] Percent= / Stop=`） |
| `IIPS\IIPSDownload\` | 975 文件 / 22.14 GB，其中 974 个 mtime 落在 09-25 16:42（**本地写入**，非网络下载） |
| `IIPS\HostPid` | 空 ⇒ `IIPSERR_PIPE_INIT`（方式 A 弹框的根因） |

### SUS-5 `iips.dll` 自身 849 字节改动

已定性：**本项目自己 9/21 打桩**（`mov eax,0x12345678; ret; ret` + RTTI 清零），
非官方停服植入。现已回退出厂 `72DDB9D1`（签名 Valid）。

---

## 四、结论

1. **上线共 5 条**：引擎 LoadLibrary（主）、Scaleform AS3 绑定、配置文件、TCLS 下发、HostApp 进程。
   之前只盯住了第 1 条，**UP-2（AS3 绑定）是新发现的**。
2. **最可疑 = `p2papp.dll`**（QQ 号 + 上传通道 + 定时上报）；
   其次 `Download.dll` 的 `rtstat.iips.qq.com:443`。
3. `WLDAP32` 是 libcurl 组件，**排除**。
4. IIPS 协议（管道 791B + 策略服务器 AES）**契约完整**，可用来写服务器。
