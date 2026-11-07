# TCLS 启动链取证报告（逆向子代理 A）

日期：2026-09-26 ／ 工作目录：`D:\BaiduNetdiskDownload\使命召唤OL`
镜像：`CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin`（基址 `0x400000`）

方法约束（**全程遵守**）：纯静态反汇编 + 只读文件/注册表。
未运行游戏，未写注册表，未改文件，未用 `netsh`/路由/DNS/防火墙/网卡命令，
未用 `sc` 命令，未删除文件，未下载安装。

## 0. 证据分级

本报告严格区分三类，不混用：

```text
[实测]     本次在本机文件/镜像上实际执行的只读读取结果（含哈希、字节、命令输出）
[反汇编]   本次在指定镜像/PE 上实际反汇编得到的指令
[既有证据] 仓库里其它会话留下的日志/报告（引用，未由本轮复核）
[推断]     由上述证据外推的结论，明确标注
```

---

## 1. 输入清单与哈希（实测）

| 文件 | 大小 | SHA-256 |
|---|---|---|
| `image_best.bin` | 10899456 | `17cef6e0a5e7b8d14fb97b5fdd846061187c6a722cfa3c5d432bee37872fd045` |
| `COD OL\TenProxy.dll` | 167592 | `a5ee7ede762c473f58a87b214213097f6dda8950ac537b0a959389aef31348cb` |
| `WeGame\tcls\tcls_core.exe` | 1971248 | `bb48629ebe7cda9ce8ef20298d45b10db2a5959946b61afb3c28dcbaa37b7eae` |
| `COD OL\TCLS\Client.exe` | 955592 | `4c19a7db7c217af342963b343487fe5679538ab99f76766f7376d2bbafb48dce` |
| `COD OL\TCLS\Tenio\TCLS.dll` | 4704616 | `32e5874e7869fc8416cb8f8775406aba06bfa71c3d5e711960aef81535825362` |
| `COD OL\codoMP_client_shipRetail.exe` | 7841344 | `36997674b18f2896de5e9d755686f6922af10708f355175714058d0a0172b537` |

镜像 PE 头（实测，`pefile`）：

```text
ImageBase 0x00400000   SizeOfImage 0x0E659000   SizeOfHeaders 0x1000
段（全部名为 .tp3，运行期已解密）：
  .tp3      VA 0x00001000  VS 0x008A689A  RAW 0x001000  RS 0x008A7000
  .tp3 a    VA 0x008A8000  VS 0x0016DA70  RAW 0x8A8000  RS 0x0016E000
  .tp3      VA 0x00A16000  VS 0xDBB1CC0   RAW 0xA16000  RS 0x00062000
  .tp3      VA 0x0E5C8000  VS 0x00000031  RAW 0xA78000  RS 0x00001000
  .tp3      VA 0x0E5C9000  VS 0x00009228  RAW 0xA79000  RS 0x0000A000
  .tp3      VA 0x0E5D3000  VS 0x00004000  RAW 0xA83000  RS 0x00004000
  .tp3      VA 0x0E5D7000  VS 0x00082000  RAW 0x771000  RS 0x00006000
```

**[实测] 重要限制**：镜像大小 `0xA65000` 远小于 `SizeOfImage 0xE659000`。
`0x331C5C0 - 0x400000 = 0x2F1C5C0 > 0xA65000`，因此
**配置块 `0x331C5C0` 所在的数据段不在镜像里**（`static bytes present: False`）。
本轮只能分析代码，不能从镜像读配置块的初值。

---

## 2. 复跑命令

```powershell
cd D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_subagents

# 镜像侧
python _tcls_shm_scan.py find TCLS_SHAREDMEMEMORY TenProxy.dll Invoke WIN_NO_TCLS
python _tcls_shm_scan.py layout
python _tcls_shm_scan.py xrefs 0x331C5C0 0x331C5D8 0x331C65C
python _tcls_shm_scan.py disasm 0x641600 0x641C00
python _tcls_shm_scan.py disasm 0x7F2B90 0x7F2E00
python _tcls_shm_scan.py disasm 0x8014C0 0x801570
python _tcls_shm_scan.py strings 0xDC6EDC 0xDC6EEC 0xDC70F8 0xDC7104

# TenProxy.dll 侧（基址 0x10000000）
python _tcls_tenproxy.py vtable --count 14
python _tcls_tenproxy.py disasm 0x100060D0 0x10006370
python _tcls_tenproxy.py disasm 0x10006360 0x10006830
python _tcls_tenproxy.py disasm 0x10007DA0 0x10007E62
python _tcls_tenproxy.py disasm 0x10008250 0x10008365
python _tcls_tenproxy.py disasm 0x10008510 0x100085F3
python _tcls_tenproxy.py layout

# 布局模型 / 样本块
python _tcls_shm_layout.py layout --out tcls_shm_layout.json
python _tcls_shm_layout.py build --host 127.0.0.1 --port 443 --field 1004 --out _tcls_shm_sample.bin

# 显式创建映射（本报告未执行，见 6.3）
python _tcls_shm_layout.py create --pid <game_pid> --host 127.0.0.1 --port 443 --field 1004 --keep 300
```

脚本与产物（纯 ASCII，`py_compile` 通过，实测）：

```text
CODOLServer\_subagents\_tcls_shm_scan.py             镜像扫描（find/xrefs/disasm/layout/strings）
CODOLServer\_subagents\_tcls_tenproxy.py            TenProxy.dll vtable / 槽函数 / 容器布局
CODOLServer\_subagents\_tcls_shm_layout.py          共享内存布局模型 + 样本生成 + create
CODOLServer\_subagents\_tcls_evidence.txt           49 KB 镜像侧全量反汇编
CODOLServer\_subagents\_tcls_evidence_tenproxy.txt  67 KB TenProxy 侧全量反汇编
CODOLServer\_subagents\_tcls_find.json               字符串命中
CODOLServer\_subagents\tcls_shm_layout.json          布局模型（机器可读）
CODOLServer\_subagents\_tcls_shm_sample.bin          样本块（0x80000 字节，76 字节非 0）
```

---

## 3. 任务 1：TCLS 启动路径盘点

### 3.1 项目里 TCLS 相关文件（实测）

**A) `COD OL\TCLS\`（游戏自带的旧 TCLS 客户端目录）**

```text
Client.exe                955592   TCLS 客户端 GUI（登录 / 更新 / 启动游戏）
ClientBase.dll           12714952  客户端主逻辑
TCLSClient.dll              65128
TPSvc.exe                  373648  TCLS 常驻服务
tpsvcBase.dll            12699984
Assistant.exe              372400
BackgroundDownloader.exe   782016
bugreport.exe              290408
Lua51.dll / sqlite3.dll / tinyxml.dll / ver_30.dll / sound.dll / SSO*.dll
DirInfo3_3.dll / tacc_2_1.dll
Tenio\   TCLS.dll 4704616 / TenBase.dll 6009592 / Dir.dll / June.dll /
         ProtocalHandler.dll / TenTPF.dll / p2papp.dll / iigw_client_api.dll /
         log.dll / TenFact.dll / MemoryAlloctor.dll / TinyXml.dll /
         TenioDL\{TenioDL.exe, TenioDL.dll, QQDownload.dll, TNProxy.dll}
TenProtect\ TASLogin.exe 7223352 / TASLoginBase.dll 12723840 /
            TasBridge.dll / TASJIT.dll / TenSafe.exe / TenSafe_1.exe /
            SecureCheck.dll / BugTrack.dll / TenHotFix.dll /
            TP\{TPApp.dll, TPDownload.dll, TPHelper.Installer.exe,
                TPHelper\TPHelper.exe, TPHelperBase.dll 14391416,
                        TenSLX.dll, libcef.dll, TPWeb.exe}
config\  见 3.2
plugins\ QmTCLSPlugin.dll 607424 / QmTCLSPatch.dll 279744 / QMCommon.dll /
         QMIpc.dll / QMNetworkMgr.dll / dr.dll / QQPCfix.dll /
         QQPCDetector.dll / GameCooperation.zip
ui\ res\ patchs\ music\ tlog\ ALog\

COD OL\components\tclsqmfix\
  TclsQmFix.exe 750912 / TclsQmFix.dat / TclsQmFix.rdb / TclsQmFixCfg.etf
  QMGreenPacket.dll / ExtractQmPacketFiles.dll / arkGraphic.dll /
  xGraphic32.dll / TSSysKitProxy.dll / Common.dll / GF.dll ...
```

**B) `WeGame\tcls\`（WeGame 的 TCLS host）**

```text
tcls_core.exe            1971248   ★ TCLS 核心 / 游戏启动器
TCLSCoreConfig.ini           992
Tenio.ini                    450
tinydl.ini / tinydl_tcls.ini / VFSConfig.ini / perfix.ini
ProtocolCenter.dll       2089520
GameDiffer.dll / TSG.dll / client_proxy.dll / adapt_for_imports.dll
UpdateInstaller.exe       488608
config\  commonconfig.cfg 7792 / updateconfig.cfg 10776 /
         VersionServerConfig.xml 456 / VersionServerConfigdynamic.ini 61 /
         CacheConfig.xml 0 / __commonconfig.cfg.tmp
Tenio\   tcls.dll 638512 / tenbase.dll 3003952 / TenioTPF.dll 4439600 /
         June.dll / log.dll / MemoryAlloctor.dll / TenFact.dll / TinyXml.dll /
         ScriptManager.dll / VFS.dll / TPFCustom.dll / TPFAdapter.dll /
         TenBaseForCross.dll / xRender.dll / GdiPlus.dll / TenioDL\
UIShellRes\ DMLQ1\TCLS  QQSPEED\TCLS  QQXJ\TCLS
```

**C) 其它 TCLS 相关文件（实测，仅列关键）**

```text
WeGame\tgp_daemon.exe               1223208   TGP 守护进程
WeGame\apps\Rail\rail.exe          15386160   Rail 启动器
WeGame\apps\Rail\rail4tcls.dll      6221864   ★ Rail -> TCLS 桥
WeGame\apps\Rail\rail_api64.dll    17313384
WeGame\apps\{agent,ca,df,nrc,Pallas}\TCLS\   （各游戏自带 TCLS 副本）
run_codol_001\tcls_redirect_run.ps1
CODOLServer\tcls_dir_server.py
CODOLServer\_tcls_serverdir_static.py
CODOLServer\_read_tcls_shm.py
COD OL\scripts\codol_launch.py
COD OL\scripts\tas_crypt.py
```

`CODOLServer\_mainline\` 里名字含 tcls 的文件（实测）：

```text
_tcls_net_report.py  _tcls_nodes.txt  _tcls_blocks.txt
_tcls_payload.txt    _tcls_serverdir_static.py
TCLS_DIR_PROTOCOL.md TCLS_SERVERDIR_ANALYSIS.md TCLS_REDIRECT_RESULT.md
frida_tcls_dir_redirect.js
```

### 3.2 `COD OL\TCLS\config\*.ini` 全部键值（实测）

```ini
; ---- config\dirserverdynamic.ini (56 B) ----
[DirServer]
successfulserverid=1
successfulport=5223

; ---- config\versionserverconfigdynamic.ini (61 B) ----
[versionserver]
successfulserverid=10
successfulport=8002

; ---- config\check.ini (59 B) ----
[check]
backupfile=data.vfs
noticerepair=
checktoolname=

; ---- config\CacheConfig.xml (17 B) ----
<filelist />

; ---- tinydl.ini (18 B) ----
[main]
switch=1

; ---- version.ini (134 B, UTF-16LE) ----
[LiveUpdateVersion]
version=2020070700
[TCLS]
version=2020070700
```

```ini
; ---- Tenio.ini (488 B) ----
[Log]
OutputDebugString=VTE
WriteToLogFile=VTE
logFileCount=20
[DefaultValue]
DllPath="Tenio"
Dlls=TCLS.dll,TenBase.dll,Dir.dll,TenTPF.dll,MemoryAlloctor.dll,June.dll,log.dll
[361]
Dll=TenFact.dll
[1121]
DLL=TinyXml.dll
```

```xml
<!-- config\dirserver.xml (714 B) -->
<Server>
  <DirServer count="5" SuccessfulServerID="1" SuccessfulPort="8080">
    <Server1 Catalog="" host="tcls.qq.com" />
    <Server2 Catalog="" host="123.151.176.103" />
    <Server3 Catalog="" host="119.84.150.46" />
    <Server4 Catalog="" host="183.61.224.121" />
    <Server5 Catalog="" host="101.91.63.192" />
    <portlist count="3" port1="8080" port2="5223" port3="10009">0</portlist>
  </DirServer>
  <RoleServer count="1" SuccessfulServerID="1" SuccessfulPort="">
    <Server1 Catalog="" host="" />
    <portlist count="1" port1=""></portlist>
  </RoleServer>
</Server>

<!-- config\VersionServerConfig.xml (824 B) -->
<Server>
  <versionserver version="1" count="13" SuccessfulServerID="1"
                 SectionTimeOut="5000" TotalTimeOut="600000"
                 SuccessfulPort="8001;9001;10001;8002;9002;10002">
    <Server1  host="tcls.rail.qq.com"/>   <Server2  host="223.167.104.26"/>
    <Server3  host="220.249.243.189"/>    <Server4  host="183.194.234.198"/>
    <Server5  host="183.192.199.25"/>     <Server6  host="180.163.25.22"/>
    <Server7  host="14.215.138.14"/>      <Server8  host="123.151.72.67"/>
    <Server9  host="123.126.122.65"/>     <Server10 host="120.241.190.12"/>
    <Server11 host="116.128.163.239"/>    <Server12 host="111.13.34.177"/>
    <Server13 host="101.89.38.73"/>
    <portlist port1="8001" port2="9001" port3="10001"
              port4="8002" port5="9002" port6="10002" count="6"/>
  </versionserver>
</Server>
```

### 3.3 WeGame 侧 TCLS 配置（实测）

```ini
; ---- WeGame\tcls\TCLSCoreConfig.ini (992 B) ----
[Log]   Level=ET
[QOS]   Enable=1
; 按 game_id 分节；CODOL 的 game_id=29 【没有条目】
; 存在的节：1=dnf 2=cf 10=x5 11=x5_2 13=xycq 16=xgame 17=qqspeed
;            21=yxd 23=ava 24=dmlq 26=lol 28=xxz 30=tgame 31=nba2k
;            32=cof 38=qqxj 48=bns 57=hon 99=BN client 512=lcu
[21]
TCLSPath=TCLS
TCLSClientFileName=Client.exe
UsesTCLSLoginOnly=1

; ---- WeGame\tcls\Tenio.ini (450 B) ----
[Log] OutputDebugString=E / WriteToLogFile=E / logFileCount=5
[DefaultValue] DllPath="Tenio"
              Dlls=TCLS.dll,TenBase.dll,log.dll,MemoryAlloctor.dll,June.dll,TenioTPF.dll
[361] Dll=TenFact.dll
[1121] DLL=TinyXml.dll

; ---- WeGame\tcls\config\VersionServerConfigdynamic.ini (61 B) ----
[versionserver]
successfulserverid=1
successfulport=19080

; ---- WeGame\version.ini ----
[LiveUpdateVersion] version=2012102401
[TCLS]              version=2012102401
```

`WeGame\tcls\config\VersionServerConfig.xml` 指向 `dir-update.wegame.com.cn:19080`
（+3 个 IP 备用），与 CODOL 自己的 `tcls.qq.com` / `tcls.rail.qq.com` 是两套更新源。

### 3.4 TCLS 进程是哪个 exe？谁拉起？

**[既有证据 + 实测]** `WeGame\tcls\tcls_core.exe` 是真正的 TCLS host
（TCLSHostApp / TCLS_Launcher / GameLauncher4TCLS_1_0；含
`"TCLS_SHAREDMEMEMORY"` + `"%s%lu"` 与 `CreateFileMappingW` 调用点）。
`COD OL\TCLS\Client.exe` 是旧 GUI 前端；`COD OL\TCLS\Tenio\TCLS.dll`
里也有同族 `CreateFileMappingW`（EX-025）。注意 `WeGame\tcls\Tenio\tcls.dll`
只有 638512 字节，与 CODOL 的 `TCLS.dll`（4704616 字节）是不同构建（实测大小）。

**[既有证据] 拉起链**：`run_codol_001\tcls_redirect_run.ps1` 实测路径为
`WeGame\tgp_daemon.exe` → `tcls_core.exe` → `TCLSHost` → 游戏进程。
但**哪个进程 CreateProcess 了 tcls_core.exe，本仓库内无模块含明文
`CreateProcess*` + `"tcls_core.exe"` 参数对**（EX-065 全树扫描结论，本轮未复跑）。

**[既有证据] 命令行模板**：tcls_core 给游戏的命令行是 `'"%s" -q %u'`；
完整形式来自 `TCLS.dll 0x103C53CC`：

```text
"<game exe>" -q %u -i %d -s %d -g %d -u %u -n %s [ -m --1 ]
```

### 3.5 它往共享内存里写什么

**[反汇编] 它写的是一个「tag 容器」，不是平面结构体**（见第 5 节）。

**[反汇编] 关键否定结论**：tcls_core **从不写入 `0x331C5C0`**。
配置块只能由游戏自己的 `0x641600 ApplySettings` 写，而它只能通过
`TenProxy.dll!Invoke(0x566)` 的 `CTclsProxy` 对象读值。链条是：

```text
tcls_core -> TCLS_SHAREDMEMEMORY<游戏PID> -> TenProxy.dll -> 0x331C5C0
```

---

## 4. 任务 2：共享内存写入方定位

### 4.1 镜像内字符串搜索（实测）

```text
python _tcls_shm_scan.py find TCLS_SHAREDMEMEMORY TenProxy.dll Invoke WIN_NO_TCLS tcls_core.exe TCLS_TASMEMORY_

HIT TCLS_SHAREDMEMEMORY   ascii  count=0
HIT TCLS_SHAREDMEMEMORY   utf16  count=0
HIT TenProxy.dll          ascii  count=1
HIT Invoke                ascii  count=5
HIT WIN_NO_TCLS           ascii  count=1
HIT tcls_core.exe         ascii  count=0
HIT TCLS_TASMEMORY_       ascii  count=0
HIT TCLS_TASMEMORY_       utf16  count=0
```

**[实测] 结论**：游戏 EXE 的运行期代码里**没有任何** `TCLS_SHAREDMEMEMORY`
字面量。游戏侧不构造这个名字，只由 `TenProxy.dll` 构造。

对应字符串（实测 `strings`）：

```text
0x00DC6EDC  "TenProxy.dll"
0x00DC6EEC  "Invoke"
0x00DDBF80  "WIN_NO_TCLS"
0x00DC70F8  "%d.%d.%d.%d"
0x00DC7104  "OpenID LoginKey: %s"
0x00DE09A8  "simplePassword"
0x00DE09B8  "297 %s %d"
0x00DC9CA0  "PEM"
0x00DC9CA4  "cacert.pem"
```

### 4.2 全树二进制扫描（实测）

```text
COD OL\codoMP_client_shipRetailBase.dll  TCLS_SHAREDMEMEMORY (ascii+utf16), TCLS_TASMEMORY_ (ascii+utf16)
COD OL\TenProxy.dll                      TCLS_SHAREDMEMEMORY (utf16)
COD OL\TerSafe.dll                       TCLS_SHAREDMEMEMORY (ascii)
```

`WeGame\tcls\tcls_core.exe` 在本轮 ASCII/UTF-16 扫描中 **0 命中**。
EX-024/EX-065 报过 utf16 命中，本轮**既不推翻也不确认**，只如实记录本轮结果。

### 4.3 是 TCLS 创建，还是游戏创建后等 TCLS 填？

**[反汇编] 结论：TCLS 侧创建；游戏侧只 Open + Map。**

```asm
; COD OL\TenProxy.dll  CTclsProxy::Initialize  真身 0x10005E40
100060EF  call dword ptr [0x100263A0]   ; KERNEL32!GetCurrentProcessId
10006101  push 0x10020FA0               ; "[CTclsProxy::Initialize] GetCurrentProcessId = %d"
10006176  push 0x10020F70               ; L"TCLS_SHAREDMEMEMORY"
100061B4  call 0x100014CE               ; 拼前缀
100061C7  call 0x10001212               ; 追加十进制 pid
100061CE  call dword ptr [0x1002639C]   ; KERNEL32!SetLastError(0)
100061DD  push 0x000F001F               ; FILE_MAP_ALL_ACCESS
100061DB  push 0
100061E2  call dword ptr [0x10026398]   ; KERNEL32!OpenFileMappingW   ★ 只 Open
100061EB  mov [ecx+0x18D4], eax
100061F4  cmp dword ptr [edx+0x18D4], 0
100061FB  jne 0x1000621F
100061FD  call dword ptr [0x10026388]   ; KERNEL32!GetLastError
1000620B  push 0x10020EA0               ; "...TCLS_SHAREDMEMEMORY+%d fail!Error code = %d"
10006273  call dword ptr [0x10026394]   ; KERNEL32!MapViewOfFile
100062E9  mov eax, [edx]                ; 读 mapped+0x00
100062F4  cmp dword ptr [ecx+0x18D0], 0x40
100062FB  jae 0x10006326                ; >= 0x40 接受
10006315  call 0x1000142E               ; "TCLS<..>%d<..>Proxy%d" 兼容性告警
1000631D  mov [ebp-0x34], 0             ; ★ 失败：初始化结果 = 0
```

`TenProxy.dll` 导入表（实测）只有 `CRYPT32 / MSVCP60 / KERNEL32 / USER32 /
ADVAPI32 / MSVCRT`，**没有任何注册表 API**；`TCLS_SHAREDMEMEMORY` 是 UTF-16 字面量。

**[反汇编] 三条结论**：

1. `TenProxy.dll` 只调用 `OpenFileMappingW`，**从不调用 `CreateFileMappingW`**。
2. 共享内存**必须由外部进程创建**（TCLS 侧或我们自己的进程）。
3. 游戏侧用自己进程的 `GetCurrentProcessId()` 拼名字，所以**必须由游戏自己去打开**；
   但外部可以在游戏启动前/启动瞬间**创建**这个名字的映射。

### 4.4 镜像内 `Invoke(0x566)` 与 vtable（反汇编，本轮复核）

```asm
; WinMain 内
0077EEA0  call 0x4FCE80              ; 前置初始化
0077EEA5  call 0x63E750              ; ★ 创建 CTclsProxy
0077EEAC  mov [0x82E1580], eax       ; ★ 存全局
0077EEB1  cmp eax, ebx / je 0x77EEBE
0077EEB5  mov edx,[eax] / mov ecx,eax / mov eax,[edx+4]
0077EEBC  call eax                   ; ★ 立刻调 vtable+0x04 = CTclsProxy::Initialize

; 0x63E750 CreateTclsProxy
0063E754  mov eax,[0x82E157C]        ; 缓存 HMODULE
0063E79A  push 0xDC6EDC              ; "TenProxy.dll"
0063E79F  call [0xCA8158]            ; KERNEL32!LoadLibraryA
0063E7AA  push 0xDC6EEC              ; "Invoke"
0063E7B0  call [0xCA8150]            ; KERNEL32!GetProcAddress
0063E7BE  push 0x566
0063E7C3  call eax                   ; Invoke(0x566, &out)
0063E7C8  mov eax,[ebp-4] / ret
```

`TenProxy.dll`（反汇编，本轮复核）：

```asm
export 1  0x100013E3  "Invoke"              ; 跳转存根
10001D8E  cmp dword ptr [ebp+8], 0x566
10001D95  jne 0x10001DDD                    ; 其它 id：out 不变
10001D97  push 0x18E4                       ; new 6372 字节
10001D9C  call 0x1000D0DE                   ; operator new
10001DB7  call 0x100013A2                   ; -> 0x10005510 CTclsProxy::CTclsProxy()
10001DDB  mov [ecx], edx                    ; *out = 对象
```

主 vtable（反汇编，实测）：

```text
primary vtable VA 0x100205D0
  +0x00 0x100205D0 -> 0x10006BD0
  +0x04 0x100205D4 -> 0x10005E40   ★ CTclsProxy::Initialize
  +0x08 0x100205D8 -> 0x100075F0
  +0x0C 0x100205DC -> 0x10007980
  +0x10 0x100205E0 -> 0x10007A60
  +0x14 0x100205E4 -> 0x10007AB0
  +0x18 0x100205E8 -> 0x10007B00
  +0x1C 0x100205EC -> 0x10006B20
  +0x20 0x100205F0 -> 0x10007CA0
  +0x24 0x100205F4 -> 0x10007DA0   ★ GetDWORD（索引读）
  +0x28 0x100205F8 -> 0x10007EA0   ★ GetBytes（索引读 + 拷贝）
  +0x2C 0x100205FC -> 0x10008140   ★ GetBlock（索引读，长度走 lenptr）
  +0x30 0x10020600 -> 0x10008250   ★ 通道表 GetBlock
  +0x34 0x10020604 -> 0x100083B0
  +0x38 0x10020608 -> 0x10008510   ★ 通道内 DWORD
```

### 4.5 镜像侧 `ApplySettings` 逐项取值（反汇编，本轮复核）

```asm
00641616  push 0xD40 / push 0 / push 0x331C5C0 / call 0xC42DE0   ; memset 0xD40
00641628  mov ecx,[0x82E1580]                                    ; ★ CTclsProxy*
0064163D  mov eax,[ecx] / mov eax,[eax+0x24]                     ; slot +0x24
00641642  push edx(&len) / push 1 / call eax                     ; tag 1 -> [0x331C5D4]
0064165C  mov edx,[ecx] / mov eax,[edx+0x28]                     ; slot +0x28
00641661  push 0x331C5D4 / push 0x331C5C4 / push 0x16 / call eax ; tag 0x16 -> block+0x04
00641680  push 0x331C658 / mov [0x331C658],0x80                  ; 长度槽 0x80
00641694  push 0x331C5D8 / push 0x18 / call eax                  ; tag 0x18 -> block+0x18
006416B9  mov [0x331C66C],0x10                                   ; 长度槽 0x10
006416C4  push 0x331C65C / push 0x19 / call eax                  ; tag 0x19 -> block+0x9C
0064170D  push 0x331C65C / push 0x11 / call 0xC3C603             ; 组 "OpenID LoginKey: %s"
0064173F  push 0x331CA70 / push 0 / push 7 / call eax            ; tag 7 长度 -> block+0x4B0
00641763  cmp dword [0x331CA70],0x400 / jle ...                  ; 截到 0x400
00641787  push 0x331CA70 / push 0x331C670 / push 7 / call eax    ; tag 7 -> block+0x0B0
006417B1  push 0x331CAF4 / push 0 / push 0x1B / call eax         ; tag 0x1B 长度 -> block+0x534
006417D5  cmp dword [0x331CAF4],0x80 / jle ...                   ; 截到 0x80
006417F9  push 0x331CAF4 / push 0x331CA74 / push 0x1B / call eax ; tag 0x1B -> block+0x4B4
0064182F  push eax / push 0x12 / call [edx+0x24]                 ; tag 0x12 -> [ebp-0x420] 通道号
0064185A  push 0x331CAF8 / push 5 / call [eax+0x38]              ; 通道 tag 5 -> block+0x538
00641894  push 0 / push 7 / call [edx+0x38]                      ; 通道 tag 7（长度校验）
006418F8  push 0 / push 8 / call [edx+0x30]                      ; 通道 tag 8 -> [ebp-0x418]
0064191E  cmp [ebp-0x428], eax / je ...                          ; tag7值 == tag8长度 ?
006419C3  cmp al, 0x3B (';') / cmp al, 0x3A (':')                ; ★ 字段分隔符
00641A07  cmp edx,9 / 00641ACC cmp edx,7 / 00641B59 cmp edx,5    ; 字段数分支
00641BC8  mov [0x331C5C0], eax                                   ; ★ 唯一写入点
```

**`block+0x04` 与 `block+0x98` 是 tag 0x16 / tag 0x18，两者都在
`cmp eax,edi / je 0x641678` 的成功分支之下**，即只有 `OpenFileMappingW`
成功、`Initialize` 走到 tag 读取阶段，才会被写。

---

## 5. 共享内存布局（反汇编解出）

机器可读版本：`CODOLServer\_subagents\tcls_shm_layout.json`。

### 5.1 容器结构

```text
Name   : "TCLS_SHAREDMEMEMORY" + 十进制(游戏进程 PID)   （无 '+'，无下划线）
Size   : 0x80000 (512 KiB)
Protect: PAGE_READWRITE   Access: FILE_MAP_ALL_ACCESS (0x000F001F)

映射布局
  mapped + 0x000   DWORD       版本头；必须 >= 0x40        [0x100062F4]
  mapped + 0x004   DWORD[64]   TABLE A（标签偏移表）
  mapped + 0x104               TABLE A 结束 = 条目区起点

标签寻址（1-based）
  off   = mapped[0x04 + 4*(tag-1)]        ; 绝对偏移
  entry = mapped + off
  entry + 0x000   DWORD  载荷字节长度（== 4 表示这是个 DWORD）
  entry + 0x004   bytes  载荷

通道（channel）模型
  tag 0x12 -> DWORD  通道号 channel（1-based）
  raw    = mapped[0x04 + 4*(0x13-1)] = mapped[0x4C]   ; 槽 +0x2C 以 tag=5 直读该 dword
  sub    = mapped[ raw + 4*(channel-1) ]              ; 通道子表偏移
  t_off  = mapped[ sub + 4*(tag-1) ]
  entry  = mapped + t_off
  entry + 0x000 DWORD 长度 / entry + 0x004 载荷
```

### 5.2 TABLE A 标签（由 `CTclsProxy::Initialize` + `ApplySettings` 反汇编得到）

| tag | 调用方 / 槽 | 目标 | 含义 |
|---|---|---|---|
| 0x01 | Init `+0x24` | `this+0x8AC` | DWORD 标志 |
| 0x02 | Init `+0x24` | `this+0x8AC` | DWORD（失败则为 0） |
| 0x03 | Init `+0x28` | `this+0x10C0` | 1 字节，>0 触发某分支 |
| 0x04 | Init `+0x28` | `this+0x8B0` | **GameSignature**，上限 0x80 |
| 0x05 | Init `+0x28` | `this+0x1038` | **LoginKey**，上限 0x10，一次性 |
| 0x07 | ApplySettings `+0x28` | `block+0x0B0`（长度 `block+0x4B0`） | 字符串/数据，≤ 0x400 |
| 0x0E | Init `+0x2C` | `this+0x8C` | 块，上限 0x410 |
| 0x0F | Init `+0x2C` | `this+0x49C` | TCLS core 窗口名（供 `FindWindowW`） |
| 0x10 | Init `+0x2C` | `this+0x11DC` | 块，上限 0x28 |
| 0x12 | ApplySettings `+0x24` | 栈 | **通道号** |
| 0x13 | Init `+0x2C`（tag=5 直读） | `this+0x18CC` | **通道表偏移**，须写在 `mapped+0x4C` |
| 0x16 | ApplySettings `+0x28` | `block+0x04`（长度 `block+0x14`） | 块，≤ 0x10 |
| 0x18 | ApplySettings `+0x28` | `block+0x18`（长度 `block+0x98` = 0x80） | 块，≤ 0x80 |
| 0x19 | ApplySettings `+0x28` | `block+0x9C`（长度 `block+0xAC` = 0x10） | 块，≤ 0x10 |
| 0x1A | Init `+0x28` | `this+0x1144` | 1 字节，>0 触发某分支 |
| 0x1B | ApplySettings `+0x28` | `block+0x4B4`（长度 `block+0x534` ≤ 0x80） | **JumpSignature**，上限 0x70 |

### 5.3 通道子表标签

| tag | 调用方 / 槽 | 目标 | 含义 |
|---|---|---|---|
| 0x05 | ApplySettings `+0x38` | `block+0x538` | DWORD |
| 0x07 | ApplySettings `+0x38` | 栈 | DWORD，**必须等于 tag 8 载荷长度** |
| 0x08 | ApplySettings `+0x30` | `[ebp-0x418]` | **数据串**，按 `;` / `:` 切字段 |

### 5.4 tag 8 数据串的字段映射（字段数 == 9 / 7 / 5 三分支）

| 段号 | N=9 目标 | N=7 目标 | N=5 目标 |
|---|---|---|---|
| 1 | `0x81A76A8` HOST | 同 | 同 |
| 2 | `0x81A9EC4` (word) PORT | 同 | 同 |
| 3 | `0xE51184` | 同 | `0x81A7F34` |
| 4 | `0xE513D4` (word) | 同 | `0x81A9780` (word) |
| 5 | `0x81A7F34` | 同 | `0x81A9EB8`（经 `0xC40233`） |
| 6 | `0x81A9780` (word) | 同 | — |
| 7 | `0x81A9784` | `0x81A9EB8` | — |
| 8 | `0x81A9EC0` (word) | — | — |
| 9 | `0x81A9EB8` | — | — |

**[反汇编] N 不等于 9/7/5 时**（`0x641BBB`）只写 `block+0x000`，
**HOST/PORT 完全不动**。所以**至少要有 5 段**，HOST 与 PORT 才会被写入游戏全局。

`0x6415C0` 把 `block+0x538` 的 4 字节格式化成点分四段（`%d.%d.%d.%d` @ `0xDC70F8`）；
`0x641560` 把二进制按 16 进制展开（查表 `0xDB6CA8`）。

### 5.5 游戏侧消费点（含降级路径）

**主路径（`[0x331C5C0] != 0`，`0x7F2B90`）**：

```asm
007F2BA0  cmp dword ptr [0x331C5C0], 0
007F2C64  cmp dword ptr [0x331C5C0], 0        ; 二次判定
007F2C6B  je 0x7F2D4D                          ; ==0 -> auth 降级路径
007F2CC1  mov ecx,[0x331CAF8]                  ; 通道 tag5 -> block+0x538
007F2CC8  movzx edx, word ptr [0x331C658]      ; block+0x98 长度
007F2CD0  push 0x331C670                       ; block+0x0B0
007F2CDC  push 0x331C5C4                       ; block+0x04
007F2D20  push 0x331C5D8                       ; block+0x18
007F2D25  push 0x331C65C                       ; block+0x9C
007F2D2A  call 0xB88CC0                        ; ★ objA：真正发起连接
007F2D7E  jne 0x7F2DA0                         ; 成功
007F2D8E  mov dword ptr [0x84ABA60], 0          ; 失败 -> sub_state=0
```

**降级路径（`0x7F2D4D`）不走 `0xB88CC0`**，改为 `0xB992E0`，
push 常量 `0xDE09A8` = `"simplePassword"`。

**[反汇编，本轮新发现] 但降级路径同样消费配置块**：

```asm
0080153F  mov edi, [0x331C5D4]                 ; ★ 配置块 +0x14 长度槽
00801545  push 0x331C5C4                       ; ★ 配置块 +0x04
0080154A  mov ecx, 0x40
0080154F  mov esi, 0x8269728
00801554  call 0x641560                        ; 十六进制展开，上限 0x40
0080155C  test eax, eax / setg al
00801561  mov byte ptr [0x84ABAD6], al
```

`0x641560` 要求 `ecx >= 2*edi + 1`，否则直接返回 0。
**[推断]** 若配置块全 0，`edi = 0`、`ecx = 0x40 >= 1` 成立，
函数走成功分支但只写一个 `'\0'`，返回 1 —— 即降级路径**不因配置块为 0 而崩**。

---

## 6. 任务 3：结论与可执行方案

### 6.1 三个选项的判定

#### 选项 a：启动 TCLS / Client.exe 组件 —— 不推荐（不可行）

1. `tcls_core.exe` 只有在它**自己 CreateProcess 游戏**时才知道游戏 PID；
   单独启动它**不会**为已存在的游戏进程创建映射。
2. `COD OL\TCLS\Client.exe` 是旧 GUI，需要登录票据 / CrossSvrID / 服务器列表
   （EX-065、`TCLS_SERVERDIR_ANALYSIS.md`），停服状态走不到"启动游戏"。
3. `tcls_core.exe` 写 tag 容器前会先 `LoadLibraryW(IIPSLaunchRestore.dll)` +
   `CreateIIPSRepair`（EX-065：`0x8D353/0x8D38A/0x8D39F`），需要腾讯侧服务。
4. **实测**：`WeGame\tcls\TCLSCoreConfig.ini` 里 **CODOL 的 game_id=29 没有条目**，
   这份 WeGame 的 TCLS 配置不包含 CODOL。

若仍要走 a，正确入口（**实测参数模板**来自 `run_codol_001\tcls_redirect_run.ps1`）：

```text
exe   : D:\BaiduNetdiskDownload\使命召唤OL\WeGame\tgp_daemon.exe
参数  : -launcher=<JSON> StartFor=29 AddPath="<sandbox>"
cwd   : D:\BaiduNetdiskDownload\使命召唤OL\WeGame
```

并且还需要 `CODOLServer\tcls_dir_server.py` 提供 `/ DIRTREERESP` 才可能走通目录查询。
但**即使走通，也不解决"共享内存里要有合法 tag 值"**。

#### 选项 c：证明不可行 —— 部分成立

**不可行部分（[反汇编]，确定）**：无法从本机任何静态文件恢复**真实的** tag 值
（uId / OpenID / LoginKey / GameSignature / 真实 HOST+PORT）。
既有证据 `settings_source_report.md`：全盘 `dwauth.ini` 搜索 **0 命中**；
注册表中 CODOL 相关 host/port 值 **0 条**。`TCLS_SHAREDMEMEMORY` 是运行期对象，
本机既无活动 TCLS 进程也无历史完整转储。

**可行部分**：布局已完全解出，可以被我们自己的进程填成**自洽**值；
只要自洽，`0x641600` 就会成功写入 `0x331C5C0`。

#### 选项 b：自己创建同名共享内存并按布局填值 —— ★ 采纳

### 6.2 采纳方案：选项 b（自建映射）

1. `TenProxy.dll` 只 `Open` 不 `Create`（[反汇编] 4.3），**我们创建 = 游戏能打开**，
   语义上等价于 TCLS 的写入。
2. 布局已 100% 静态解出（第 5 节），可构造自洽块。
3. 唯一硬前置是**版本头 `mapped+0x000 >= 0x40`**（`0x100062F4`）。
4. `Initialize` 按 tag 号索引，缺 tag 只让对应项失败，不会崩。

### 6.3 可执行步骤（精确）

**共享内存名**：`TCLS_SHAREDMEMEMORY<十进制 PID>`，`<PID>` = 游戏进程 PID。
**大小**：`0x80000`。**保护**：`PAGE_READWRITE`。

**必须写在固定位置的三个值**：

| 偏移 | 宽 | 值 | 作用 |
|---|---|---|---|
| `0x000` | 4 | `0x00000040` | 版本头（`>= 0x40` 才被接受）。同时充当 tag 4 的 payload 长度字段（`4 == DWORD`），使 GameSignature 读取成功 |
| `0x04 + 4*(tag-1)` | 4 | 该 tag 条目相对映射基址的偏移 | TABLE A 索引 |
| `0x04 + 4*(0x13-1)` = `0x4C` | 4 | 通道表 payload 的偏移 | 槽 `+0x2C`（tag=5）**直接读**，不经过长度字段 |

**最小 tag 集合（让 `0x641600` 成功写出 HOST/PORT）**：

```text
tag 0x12 (DWORD)  = 1              ; 通道号
tag 0x13          -> 通道表         ; 见上表 0x4C
通道表[channel-1] -> 通道子表
通道子表[0x08-1]  -> tag8 数据串     ; 至少 5 段
通道子表[0x07-1]  -> DWORD == tag8 串长度
通道子表[0x05-1]  -> DWORD
tag 0x16          -> 块 <= 0x10      ; 写 block+0x04（长度 block+0x14）
tag 0x18          -> 块 <= 0x80      ; 写 block+0x18（长度 block+0x98）
tag 0x19          -> 块 <= 0x10      ; 写 block+0x9C（长度 block+0xAC）
tag 0x1B          -> 块 <= 0x70      ; 写 block+0x4B4（长度 block+0x534）
tag 0x0F          -> TCLS core 窗口名（可选）
tag 0x04 / 0x05 / 0x0E / 0x10 / 0x1A / 0x01 / 0x02 / 0x03（可选）
```

**tag 8 数据串格式**（[反汇编] 5.4）：

```text
"HOST:PORT:字段3:字段4:字段5"   或   "HOST;PORT;字段3;字段4;字段5"
```

字段数必须 == 9 / 7 / 5；推荐 **5 段**（最少且能填 HOST/PORT）。

样本（已生成 `_tcls_shm_sample.bin`，实测 0x80000 字节、76 字节非 0）：

```text
tag 8 串 = "127.0.0.1;443;1004\0"    (长度 0x13 = 19)
tag 7    = 0x13 (== 上面长度)
tag 0x12 = 1
通道表[0]        -> 0x334（通道子表偏移）
通道子表[0x05-1] -> {00 00 00 00}, 长度 4
通道子表[0x07-1] -> {13 00 00 00}, 长度 4
通道子表[0x08-1] -> "127.0.0.1;443;1004\0", 长度 0x13
```

**操作顺序（关键）**：

1. **先创建映射，再让游戏进程进入 `Initialize`**。`WinMain 0x77EEAA` 把
   `Invoke(0x566)` 的结果存进 `[0x82E1580]` 后**立刻**调
   `[vtable+0x04]`（`0x77EEB5..0x77EEBC`）。映射必须在那一刻存在。
2. 游戏每次启动 PID 不同，必须用**本次**的 PID。
3. 实践做法：`CreateProcess(CREATE_SUSPENDED)` → 读 `pi.dwProcessId` →
   `CreateFileMappingW("TCLS_SHAREDMEMEMORY"+pid)` → `ResumeThread`。
   这正是 `COD OL\scripts\codol_launch.py` 已实现的做法。
4. 写完后**保持映射句柄不关闭**，否则对象销毁，后来者 `OpenFileMappingW` 失败。
5. **[推断]** 启动后改映射内容仍然有效：`Initialize` 保存的是块地址
   （`[this+0x18C4]`），`GetDWORD/GetBytes` 从该共享视图现读，不是拷贝。
   （对比：`ApplySettings` 每几秒重跑并先 `memset` 配置块，所以 poke 会被清回 0，
   既有证据 `SESSION_RECORD_20260926_C5C0_SWITCH.md`。）

**脚本**：

```powershell
cd D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_subagents

python _tcls_shm_layout.py layout --out tcls_shm_layout.json
python _tcls_shm_layout.py build  --host 127.0.0.1 --port 443 --field 1004 --out _tcls_shm_sample.bin
python _tcls_shm_layout.py create --pid <game_pid> --host 127.0.0.1 --port 443 --field 1004 --keep 300
```

### 6.4 不要做的事

* 不要为了"让配置块有值"而 `poke [0x331C5C0]`：既有运行期实验
  （`_poke_c5c0.py`）显示它只换来路径切换、会被周期重跑清零，且拖慢时间线约 18 s。
* 不要改游戏二进制。
* 不要写 `dwauth.ini`：既有证据表明它与 TCLS 路径写**同一组全局**，
  是并列覆盖关系，不是"默认值 vs 覆盖值"。

---

## 7. 未能查明 / 未做的事（如实列出）

1. **真实的 tag 值本机无来源**（HOST / PORT / uId / OpenID / LoginKey /
   GameSignature / JumpSignature）。本轮**未复跑**注册表查询与全盘 ini 搜索，
   引用的是既有证据 `settings_source_report.md` 的结论。
2. `WeGame\tcls\tcls_core.exe` 里 `TCLS_SHAREDMEMEMORY` 字面量**本轮扫描 0 命中**。
   EX-024/EX-065 报有 utf16 命中。本轮既不推翻也不确认。
3. **谁 CreateProcess 了 `tcls_core.exe`** —— 未解出（EX-065 全树扫描结论，本轮未复跑）。
4. **字段数 == 9 / == 7 分支的字段语义未解出**（只解出目标全局地址）。
   `-i/-s/-g/-u/-n` 与 `0x81A7F34 / 0x81A9780 / 0x81A9784 / 0x81A9EC0 /
   0x81A9EB8` 的对应关系未建立。
5. **`block+0x98` 的 `word` 低位没有静态写入点**：`0x7F2CCB` 用
   `movzx word ptr [0x331C658]` 读，但 `ApplySettings` 只在 `0x641685`
   写了 dword 常量 `0x80`（低位 0x80、高位 0）。**[推断]** 低位被认为是
   producer 侧写入的长度；**未解出**。
6. **vtable 其余槽的语义未展开**：`0x10006BD0`(v+0x00)、`0x100075F0`、`0x10007980`、
   `0x10007A60`、`0x10007AB0`、`0x10007B00`、`0x10006B20`、`0x10007CA0`、`0x100083B0`。
7. **镜像里没有 `0x331C5C0` 的静态初值**（数据段不在镜像内，实测），
   当前运行期的实际块内容本轮无从读取。
8. **本轮未做任何运行期验证**：没有创建过 `TCLS_SHAREDMEMEMORY<pid>`，
   没有启动游戏，没有 attach 任何进程。6.3 是**基于反汇编的推荐序列，未经实测**。

---

## 8. 最终结论

```text
TCLS_SHARED_MEMORY_OBJECT      = "TCLS_SHAREDMEMEMORY" + 十进制(游戏 PID)
TCLS_SHARED_MEMORY_SIZE        = 0x80000
PRODUCER_REQUIRED              = 外部进程（tcls_core.exe 或我们自己的进程）
CONSUMER                       = 游戏内 TenProxy.dll CTclsProxy::Initialize
CONSUMER_ONLY_OPEN             = 是（只有 OpenFileMappingW，无 Create）      [反汇编]
GAME_EXE_HAS_NAME_LITERAL      = 否（镜像内 0 命中）                          [实测]
CONTAINER_MODEL                = 版本头 + 64 项偏移表 + [len][payload] 条目
CHANNEL_MODEL                  = tag 0x12 选通道 -> 通道表 -> 子表 -> 条目
TAG8_REQUIRED_MIN_FIELDS       = 5（HOST;PORT;f3;f4;f5）                      [反汇编]
CONFIG_BLOCK_WRITER            = 0x641600，唯一调用者 0x642739                [反汇编]
CONFIG_BLOCK_ONLY_ON_SHM_OK    = 是（0x64164C..0x641671 是成功分支）          [反汇编]
DOWNGRADE_PATH_ALSO_USES_BLOCK = 是（0x801546 读 block+0x14 / block+0x04）    [反汇编]
RECOVERABLE_REAL_TAG_VALUES    = 否（本机无来源）                             [既有证据]
CHOSEN_OPTION                  = b（自建同名共享内存并按布局填自洽值）
```

**最小可行动作序列（3 步）**：

```text
1. CreateProcess(CREATE_SUSPENDED) 启动
   "COD OL\codoMP_client_shipRetail.exe"，cwd = "COD OL"
   命令行至少含 -q（否则 0x77F6E8 的 WIN_NO_TCLS 判定会弹致命框）

2. 立刻用返回的 dwProcessId 创建并映射
   CreateFileMappingW(INVALID_HANDLE_VALUE, NULL, PAGE_READWRITE,
                      0, 0x80000, "TCLS_SHAREDMEMEMORY<pid>")
   MapViewOfFile(..., FILE_MAP_ALL_ACCESS, ...)
   写入：
     +0x000 = 0x00000040
     +0x04 + 4*(tag-1)   = 各 tag 条目偏移          （TABLE A）
     +0x04 + 4*(0x13-1)  = 通道表 payload 偏移       （即 mapped+0x4C）
     tag 0x12 = 1                                    （通道号）
     通道表[0]           -> 通道子表
     通道子表[0x05-1]    -> DWORD（len 4）
     通道子表[0x07-1]    -> DWORD == len(tag8)
     通道子表[0x08-1]    -> "HOST;PORT;f3;f4;f5\0"   （>= 5 段）
     另填 tag 0x04（GameSignature 前缀）/ 0x16 / 0x18 / 0x19 / 0x1B 空块

3. ResumeThread；保持句柄不关闭。
   预期：TenProxy::Initialize 通过版本检查 -> ApplySettings 解析 tag8
         5/7/9 段成功 -> [0x331C5C0] = 1 -> 0x7F2B64 不再跳 0x7F2D4D。
   （该路径切换已被既有 poke 实验间接验证；本轮未实测。）
```
