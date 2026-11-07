# CODOL 组件调用 & 服务器通信 · 静态地图

日期：2026-09-29
方法：**纯静态、只读**。反汇编对象 = 运行期解密镜像
`CODOLServer/_mainline/_dyn100_run_20260925_182324/live/image_best.bin`
（base `0x400000`，SHA-256 `17cef6e0a5e7b8d14fb97b5fdd846061187c6a722cfa3c5d432bee37872fd045`）。
未运行游戏、未读写游戏内存、未修改任何既有文件（仅新增本节产出的文件）。

## 0. 本轮静态产物

```text
_arch_scan.py              只读扫描器（modules / imports / endpoints / xref）
arch_modules.csv           顶层 39 个模块：架构/大小/保护壳/SHA-256
arch_imports.csv           689 条导入（来源：运行期已解析 IAT 转储 scratch_iat.txt）
arch_endpoints.csv         813 条端点/协议常量，含明文镜像中的真实引用地址
本文件                    组件调用图 + 服务器通信链（地址级）
```

复现：

```powershell
python -X utf8 _arch_scan.py modules
python -X utf8 _arch_scan.py imports
python -X utf8 _arch_scan.py endpoints
python -X utf8 _arch_scan.py xref 0x81A76A8
```

> 为什么端点的引用地址必须取自明文镜像：磁盘 exe 的 `.tp3` 代码段是密文，
> 对磁盘文件做 xref 扫描永远得到 0 命中（旧 `分析/01_string_anchors.csv`
> 大多数 `ref_count=0` 就是这个原因）。本文件的引用地址全部来自明文镜像。

---

## 1. 组件清单（`arch_modules.csv`，顶层 39 项）

### 1.1 主链

| 模块 | 大小 | 保护壳 | 角色（依据） |
|---|---|---|---|
| `codoMP_client_shipRetail.exe` | 7,841,344 | `.tp3` + `.tvm0` | 游戏主模块。**磁盘代码加密**，唯一入口是一条 VM stub |
| `codoMP_client_shipRetailBase.dll` | 60,327,992 | `.tvm0` | VM 宿主 / 平台 bootstrap。**主 exe 运行期只导入它 1 个函数** |
| `GameDataPlatformServer.dll` | 354,808 | 明文 | GDP（游戏服务器）协议宿主，内嵌 `GDPPkg`/`GDPOpenProtocol.tdr` 引用 |
| `GDPLoader.dll` / `GDPImpl.dll` / `GDPCODOTrail.dll` | 291,832 / 68,088 / 43,600 | `.tvm0` | GDP 加载与实现 |
| `GameRpcs.dll` / `TenRpcs.dll` | 2,488,888 / 17,408,064 | `.tvm0` | RPC 层 |
| `TenProxy.dll` | 167,592 | **无壳** | 平台代理（可静态反汇编） |
| `TenSLX.dll` / `TenSp.dll` | 2,675,768 / 164,920 | `.tvm0` | 平台组件 |
| `TCJ.dll` / `PolicyProbe.dll` / `VSDDrvDll.dll` / `ACE-DRV32.dll` | — | **VMProtect** | 安全/策略组件 |
| `TerSafe.dll` / `ace-ats32.dll` / `tvsd.dll` | — | `.tvm0` / `.tvm40/41` | 安全组件 |
| `BugTrace.dll` | 1,029,624 | **无壳** | 崩溃回传 |
| `GCloudVoice.dll`、`libcef.dll`、`D3DX9_43.dll`、`bink2w32.dll`… | — | 无壳 | 语音 / 内嵌浏览器 / 渲染 / 视频 |

### 1.2 结论

```text
1. 主 exe 的"自己"的代码在磁盘上是密文；运行期才解密 → 一切代码结论只能来自
   运行期镜像（本文件全部遵守）。
2. 主 exe 运行期只导入 1 个函数：Base.dll 的某序号（见 PLAN_A_WORKING_NOTES.md
   的 ordinal-1 @ Base+0x1D6582C）。⇒ exe 的真正 API 面在 Base.dll 侧被 VM 解开。
3. 已解析 IAT 转储（scratch_iat.txt，IAT 基址 0x00B02000，落在第一段 .tp3 内）
   给出**游戏进程实际使用的 Win32 API**，见第 3 节。
```

---

## 2. 进程内调用关系（谁拉起谁）

```text
TCLS\Client.exe (启动器，非本工程分析对象)
  └ CreateProcessW(codoMP_client_shipRetail.exe, "%s" -q %u -i %d -s %d -g %d -u %u -n %s)
      + 共享内存 TCLS_TASMEMORY_<pid> / TCLS_SHELLMEMORY_<pid>
        （布局与算法见 analysis_logs/handoff_recovery.md）
  └ codoMP_client_shipRetail.exe
      ├ 入口 → VM stub（.tvm0）→ 平台 bootstrap
      ├ codoMP_client_shipRetailBase.dll   ← 唯一静态导入；VM 宿主
      ├ IIPS 初始化（enable_iips 闸门）
      │   ├ ifs/iips: 载 iips.dll → ifs2.dll
      │   ├ 命名管道 "\\.\Pipe\" + MD5(lower(iips_url))
      │   └ CreateProcess IIPSHostApp.exe /mode iipslaunch（外部进程）
      ├ 平台组件：TenProxy / TenSLX / TenRpcs / GameRpcs / TCJ / PolicyProbe
      ├ 安全组件：ace-ats32 / ACE-DRV32 / tvsd / TerSafe / GbSpy
      └ DW(Demonware) 层（0x7E9xxx / 0xBBxxxx）→ 大厅
```

**主 exe 内的主要功能区（地址级，全部来自明文镜像反汇编）**

| 区域 | 地址 | 作用 |
|---|---|---|
| DW 状态机 | `0x7F25B0` 取状态 / `0x7F26C0` 泵 / `0x7F28F0` 子状态分派 | 大厅主状态机 |
| DW 配置读取 | `0x50BC70` | 通用 `read(cfgobj, section, key, flag)` |
| DW 配置消费者 | `0x7EDD3A`… | 读 `dw_config` 各键（见 §5.I） |
| 大厅 URL | `0x7F306C` | 构造 `https://%s/` |
| AUTH URL | `0x0B99EA0` 起 | 构造 `https://%s:%d/auth/` |
| tlog 上传 | `0x642830` | 构造 `https://%s:%u/tlog` |
| 大厅帧分发器 | `0x00BA4440` | opcode 分派（0x81/0x83/0x84/0x85/0x87/0x89） |
| 大厅帧处理器 | `0xBA3C70`(0x81) / `0xBA3BA0`(0x83) / `0xBA3590`(0x87) / `0xBA3600`(0x89) | 帧语义 |
| 资源/zone 链 | `0x4FCC00` / `0x4FCCA0` / `0x4FCD50` / `0x49E160` | zone 请求与提交（见 §6） |
| 资产查询 | `0x4A9330` | 查 `mp/marketplace.json` |
| 断线入口 | `0x7EEBC1 → 0x621810 → cppOnDWDisconnected` | 断线路径 |

---

## 3. 通信栈（`arch_imports.csv`：游戏进程实际使用的 Win32 API）

### 3.1 与网络/加密相关的 DLL

| DLL | 导入数 | 说明 |
|---|---|---|
| `WS2_32` | **16** | 唯一网络栈 |
| `CRYPT32` | **15** | 证书/证书存储（`CertFindCertificateInStore` / `CertOpenStore` / `CertCloseStore` / `CertGetNameStringW/A` / `CryptQueryObject` / `CryptMsgGetParam` …） |
| `WINTRUST` | 1 | 签名校验 |
| ADVAPI32 | 79 | `CryptAcquireContextA/W` / `CryptGenRandom` / `CryptDecrypt` / `CryptCreateHash` / `CryptSignHashW` / `CryptExportKey` / 注册表 / 服务 / 事件日志 |
| KERNEL32 / USER32 / GDI32 / ntdll / ole32 / OLEAUT32 / SHLWAPI / SHELL32 / VERSION / SETUPAPI / WINMM / NETAPI32 / gdiplus | — | 常规 Win32 |

**关键否定结论**：**没有 `WININET` / `WINHTTP` / `URLMON` / `DNSAPI` / `SECUR32` / `SCHANNEL`**。
⇒ 客户端的 HTTPS **不是**系统 HTTP 栈做的，而是自己实现。

### 3.2 WS2_32 导入明细（通信原语）

```text
getaddrinfo / getnameinfo          域名解析（不依赖系统 DNS 客户端栈）
WSASocketW                         建 socket
WSAEventSelect / WSAEnumNetworkEvents / WSACreateEvent / WSAWaitForMultipleEvents
                                   WSAEventSelect 异步模型（不是 IOCP）
WSAIoctl / WSAEnumProtocolsW / WSCGetProviderPath / WSACloseEvent
+ 若干 ORD（#1 #6 #7 #13 #19 #112 #151）
```

### 3.3 TLS/HTTP 是"自带库"（字符串证据）

```text
明文镜像内：
  0x00D3AA04  "OpenSSL 0.9.8p 16 Nov 2010"
  0x00D39934  "X.509 part of OpenSSL 0.9.8p 16 Nov 2010"
  0x00D3B1C   "ASN.1 part of OpenSSL 0.9.8p …" 等各子模块版权串
  0x00D36864  "TLSv1.0"
  0x00D368B8  "SSL: SSL_set_fd failed: %s"
  0x00D37050  "SSL_write() return error %d"
  0x00D36680  "vtls\openssl.c"                 ← libcurl 的 OpenSSL 后端
  0x00D33690  "CURLOPT_SSL_VERIFYHOST no longer supports 1 as value!"
```

⇒ **通信栈 = WS2_32(裸 socket) + 静态链接的 OpenSSL 0.9.8p（TLSv1.0）+ 静态链接的 libcurl + CRYPT32（证书存储）**。
这也解释了实测中"把明文 TCP 打到 HTTPS 端口得到 `WRONG_VERSION_NUMBER`"——那是 OpenSSL 的错误码。

### 3.4 HTTP 报文层常量

| 常量 | VA | 引用地址 |
|---|---|---|
| `POST %s HTTP/1.1` | `0x00D5AB10` | — |
| `GET %s HTTP/1.1` | `0x00D5AAD8` | — |
| `Expect: 100-continue` | `0x00D34B7C` | — |
| `Content-Length` | `0x00D34BB8` | — |
| `Content-Length: %I64d` | `0x00D34D5C` | — |
| `X-TransactionID` | `0x00D59E6C` | — |
| `X-TransactionID: %I64u` | `0x00DC9CBC` | — |
| `Expect:` / `Content-Length: %u` | `0x00DC9D28` / `0x00DC9CF0` | — |
| `application/json` | `0x00D5A1E4` | — |

---

## 4. 端点与协议常量（`arch_endpoints.csv`，813 行，节选关键）

| 类别 | 值 | VA | 引用（明文镜像） |
|---|---|---|---|
| config | `dwauth.ini` | `0x00DDBD9C` | push `0x0077EF41` |
| config | `stun.ini` | `0x00DDBDBC` | push `0x0077EFF9` |
| config | `buildconfig.ini` | `0x00DDBDC8` | push `0x0077F093` |
| config | `iips.ini` | `0x00DDBE44` | push `0x0077F25D` |
| config | `cacert.pem` | `0x00DC9CA4` | push `0x0066AF5A` `0x0066B0A0` `0x007F2C33` `0x007F2EB8` `0x007F3036` |
| URL | `https://%s:%d/auth/` | `0x00D5A2CC` | push `0x00B99EBE` `0x00B9AC89` |
| URL | `https://%s/` | `0x00DE09E4` | push `0x007F3071` |
| URL | `https://%s:%u/tlog` | `0x00DC71CC` | push `0x0064283D` |
| URL | `%s://%s:%d/%s/title/%d/queue/%d/member/%llu` | `0x00D5A11C` | （LSG 队列/匹配） |
| host | `ied-tqos.qq.com` | `0x00DD98A0` | push `0x00808668` |
| host | `cod4master.activision.com` | `0x00DBD558` | push `0x004FC4D1` `0x004FC4EC` |
| stun | `stun.us.demonware.net` | `0x00DC6610` | push `0x006213CB` `0x00BAE8E4` |
| stun | `stun.eu.demonware.net` | `0x00D5A9FC` | push `0x00BAE936` |
| stun | `stun.jp.demonware.net` | `0x00D5A9E4` | push `0x00BAE988` |
| stun | `stun.au.demonware.net` | `0x00D5A9CC` | push `0x00BAE9DA` |
| DW 头 | `DW-Server-Ticket` | `0x00D5A194` | push `0x008DF0FD` |
| DW 头 | `DW-Client-Ticket` | `0x00D5A168` | — |
| DW 字段 | `auth_task` | `0x00D5A228` | push `0x008DF6CC` |
| DW 字段 | `lsg_server_ticket` | `0x00D5A0E8` | — |
| DW 字段 | `iv_seed` | `0x00D5A114` | — |
| DW 事件 | `DW_DNS_COMPLETE` | `0x00DE08E8` | — |
| DW 事件 | `DW_ACCOUNT_LOGIN_COMPLETE` | `0x00DE090C` | `0x006831CD` |
| DW 事件 | `DW_LOBBY_CONNECTED` | `0x00DE0938` | — |

> 完整 813 行见 `arch_endpoints.csv`；`kind` 列区分
> url / host / stun / config-file / dw-header/var / dw-event / dw-code / path。

---

## 5. 与服务器通信的完整链路（地址级）

### A. 配置层：4 个 ini 的读取点

| 文件 | 字符串 VA | 读取点 |
|---|---|---|
| `dwauth.ini` | `0x00DDBD9C` | `0x0077EF41` |
| `stun.ini` | `0x00DDBDBC` | `0x0077EFF9` |
| `buildconfig.ini` | `0x00DDBDC8` | `0x0077F093` |
| `iips.ini` | `0x00DDBE44` | `0x0077F25D` |

> 当前磁盘上的 `dwauth.ini` / `iips.ini` **已被本地实验改写**，不能代表历史原值。

### B. 启动闸门

```text
iips.ini  enable_iips=1   <- 唯一闸门（"必须复现 WeGame/TCLS 上下文"已被证伪）
   -> 载入 iips.dll -> ifs2.dll
   -> DW_DNS_COMPLETE
```

### C. AUTH（HTTPS + JSON）

**URL 构造点** `0x00B99EA0`：

```asm
B99EA0  movzx edx, word ptr [esi+0x2170]    ; 端口
B99EB0  push edx
B99EA7  mov  eax, [ebp-0x19d0]              ; 主机（另一来源）
B99EB1  push eax
B99EB8  call 0xBA9EB0                       ; 取主机字符串
B99EBD  push eax
B99EBE  push 0xD5A2CC                       ; "https://%s:%d/auth/"
B99EC9  push 0x200
B99ECE  push ecx                            ; buf
B99ECF  call 0x77B370                       ; snprintf
B99EDB  call 0x8435D0                       ; 发起请求
B99EE3  call 0x6431B0
B99EEA  call 0xB771E0
```

```text
请求   POST /auth/  (HTTP/1.1, TLS)
头     Host / Accept: */* / Content-Type: application/json
       X-TransactionID / Content-Length / Expect: 100-continue
体     {"auth_task":n,"iv_seed":u32,"title_id":"0","identity":"<8hex>",
        "extra_data":"{\"version\":\"0\",\"user_id\":...,\"extended_data\":true}"}
响应   200 + JSON：auth_task / code / iv_seed / client_ticket / server_ticket /
        lsg_server_ticket / lsg_server_ticket_size / next_poll_after /
        estimated_wait_time / member_position
落点   lsg_server_ticket / _size -> 对象 +0x2e8（写点 0xB98577）
```

### D. 队列 / 匹配（LSG）

```text
模板  "%s://%s:%d/%s/title/%d/queue/%d/member/%llu"   @0x00D5A11C
实测  PUT /v1.0/title/<id>/queue/0/member/<id>
      头 DW-Server-Ticket / DW-Server-Ticket-Size:128
         DW-Client-Ticket / DW-Client-Ticket-Size:129 / DW-Ticket-Seed: 0
断线后清理出现 DELETE /queue（是结果，不是原因）
```

### E. 大厅（明文 TCP，非 TLS）

**URL 构造点** `0x007F306C`：

```asm
7F306C  push 0x81A76A8      ; 大厅主机全局（DW 主机名）
7F3071  push 0xDE09E4       ; "https://%s/"
7F3076  call 0x774980       ; 拼接
7F3082  push 0x2712         ; 10002
7F3088  call 0xAC93B0       ; 投递
```

`0x81A76A8`（大厅/DW 主机字符串）的**全部 5 个 push 引用**（`_arch_scan.py xref 0x81A76A8`）：

```text
0x0077EF8A   0x007F2BDD   0x007F2C15   0x007F306C   0x007F3533
abs4 另有：0x00641A11 0x00641AD6 0x00641B5F 0x0077EF8B
           0x007F2BDE 0x007F2C16 0x007F306D 0x007F3534
```

```text
指到 HTTPS 端口会得到 WRONG_VERSION_NUMBER（OpenSSL 错误）-> 证明大厅是明文 TCP
历史根因：0x081A76A8 从未被填充 -> DNS 对象 B 解析出 236.3.0.0
帧：u32 frame_len | u8 type | u8 opcode | body...
    分发器读 opcode 于 reader 缓冲 +30（= body[1]）
```

### F. tlog（日志上传）

```asm
642830  movzx ecx, word ptr [0x81A9EC0]   ; 端口
642837  push ecx
642838  push 0x81A9784                    ; 主机字符串
64283D  push 0xDC71CC                     ; "https://%s:%u/tlog"
642847  push 0xE697B0                     ; buf
64284C  call 0x774900                     ; snprintf(buf,0x410,fmt,host,port)
```

### G. TQoS（网络质量上报）

```text
主机  ied-tqos.qq.com    @0x00DD98A0，push @0x00808668
实测  DNS -> 116.130.224.66:8000（UDP）；无应答
```

### H. STUN / Demonware + 服务器列表主机

```text
stun.us.demonware.net   @0x00DC6610    push @0x006213CB / 0x00BAE8E4
stun.eu.demonware.net   @0x00D5A9FC    push @0x00BAE936
stun.jp.demonware.net   @0x00D5A9E4    push @0x00BAE988
stun.au.demonware.net   @0x00D5A9CC    push @0x00BAE9DA
cod4master.activision.com @0x00DBD558  push @0x004FC4D1 / 0x004FC4EC
```

### I. DW 配置读取（**第一档 ⑤ 的直接卡点**）

统一模式（`0x7EDD3A` 起，共 5 个键）：

```asm
7EDD3A  cmp  byte ptr [0xC7AEAC0], 0     ; "配置已加载"？
7EDD41  je   0x7EE216                    ; 未加载 -> 全部跳过
7EDD47  mov  eax, [0x33E6A00]            ; DW 配置对象
7EDD4C  push 1
7EDD4E  push 0xDE0028                    ; 键名
7EDD53  push 0xDB6EBC                    ; 节名 = "dw_config"
7EDD58  call 0x50BC70                    ; read(cfgobj, section, key, 1)
```

**键 -> 落点表（本轮新读出）**

| 键 | 键名 VA | 落点全局 | 类型 |
|---|---|---|---|
| `STUNPingEnabled` | `0x00DE0028` | `0x084244C4` | bool |
| `STUN_STN` | `0x00DE0038` | `0x084244C8` | char[0x400] |
| `STUN_TUB` | `0x00DE0044` | `0x084248C8` | char[0x400] |
| `STUN_CTG` | `0x00DE0050` | `0x08424CC8` | char[0x400] |
| `STUN_STG` | `0x00DE005C` | `0x084250C8` | char[0x400] |
| 节名 `dw_config` | `0x00DB6EBC` | — | — |

```text
门1  [0xC7AEAC0] = "配置已加载" 标志
门2  [0x33E6A00] = DW 配置对象（容器）
全镜像对这两个全局 705 处引用，没有一处直接写入
=> 由配置模块以计算地址填充；本环境该模块从未生效
=> 所有 dw_config 键读不到 -> DW 跑硬编码默认值 -> 发送链失败 -> +52 s 断线
```

`0x50BC70` 反汇编（配置读取器签名）：

```asm
50BC70  push ebp / mov ebp,esp / mov [ebp-4],0
50BC7B  test eax,eax / je fail          ; eax = 配置对象
50BC83  mov edx,[ebp+8] / test edx,edx / je fail   ; 节名
50BC8E  cmp dword [ebp+0xC],0 / je fail            ; 键名
50BC99  mov ebx,[eax] / mov edi,[eax+4]            ; 内部两张表
50BCAF  cmp byte [ebp+0x10],0                      ; flag
```

### J. GDP（游戏服务器协议）

```text
定义   COD OL\GDPOpenProtocol.tdr   438,856 B  明文 schema
       magic 0x000b02d6；343 命令 / 592 类型
线格式 GDPPkgHead(Version+CmdID+CmdType+headlen+bodylen+SubCmdId)
       CODOL 分支 TGDPCODOLMainCmdHead
宿主   GameDataPlatformServer.dll（内嵌 GDPPkg / GDPOpenProtocol.tdr 引用）
索引   CODOLServer\GDP_PROTOCOL_INDEX.md / GDP_COMMANDS.csv
运行期关系：本阶段 UNKNOWN（未取得 GDP 与大厅的运行时直接引用证据）
```

---

## 6. 资源 / zone 加载链（本轮新增，推翻"必须改 .text"）

```text
0x4FE740  (启动/阶段函数；调用者 0x4FD98B、0x5C0093)
 └ 0x4FE7BE  call 0x4FCD50
    0x4FCD50  (门: test byte [0x1CDAF1C],2)
     ├ 0x4FCD88  call 0x49E410  ; patch_common_marketplace_lite /
     │                             common_marketplace_lite /
     │                             patch_common_marketplace_lite1 /
     │                             common_marketplace_lite1
     ├ 0x4FCD93  call 0x49E4D0  ; patch_common_mp / common_mp /
     │                             patch_localized_common_mp / localized_common_mp
     ├ 追加 patch_ui_mp / ui_mp / patch_localized_ui_mp / localized_ui_mp
     └ 0x4FCE4F  call 0x49E160(arr,count,0)

0x49E160 .. 0x49E3BE call 0x49DE70(arr,count)
0x49DE70  0x49DED4 or dword ptr [0x1CDAF1C], ecx
          注册 {名字,掩码} 进 0x01D06440 (stride 0x44, +0x40 = 掩码)
0x49F280  遍历 0x01D06440 -> call 0x49ED40(name,[rec+0x40])
0x49ED40  0x49ED5A sprintf("%s.ff", name) (fmt @0x00DB617C) -> 找 main\<name>.ff
0x49F180(name) = "该 zone 是否已装载"
          count=[0x01E2ACF4]，slot=[i+0x02F1FD90]，
          名字=[0x029C9DE8 + slot*0xA4 + 8]，字符串比较
```

**磁盘对照（数据层缺口）**

```text
run_codol_001\sandbox_ifs1_20260923\main\   只有 10 个 .ff
   code_post_gfx_default_mp.ff / code_post_gfx_mp.ff / code_pre_gfx_mp.ff
   common_mp_reload.ff / development_mp.ff / localized_code_post_gfx_mp.ff
   localized_code_pre_gfx_mp.ff / localized_ui_mp.ff / mp_playlists.ff / ui_mp.ff

被请求但缺失： common_mp.ff、common_marketplace_lite.ff（及 patch_/localized_ 变体）
它们就在盘上： COD OL\IIPS\IIPSDownload\ff_init_common_marketplace_V95.ifs
   (33,097,234 B；内嵌 3 个 "IWff0100" 块 @0x189 / 0x1C3936E / 0x1F801A3；
    EOF 0x1F90612)
   名称：common_marketplace_lite.ff / common_marketplace_lite1.ff /
        localized_common_marketplace_lite.ff
```

⇒ 与 `RESOURCE_MOUNT_AUDIT_20260929.md` 互证：基础包
`ff_init_common_gfx_V109.ifs` -> `main\` 的 10 个 `.ff` 是 **10/10 精确对应**，
而 marketplace 的 3 个 zone **不在** `main\`。

---

## 7. 仍未确定（UNKNOWN，不自行补全）

```text
1. 大厅建连之后的应用层载荷语义（帧已解，部分字段含义未知）
2. lsg_server_ticket 的字节格式（除前 4 字节 de ad bd ef 外）
3. ticket 的实际校验方式
4. dwauth.ini 字段 2/5/6/7 的业务语义；历史原始 HOST/PORT 取值
5. 0x1CDAF1C 各位的"待装载 / 已装载"极性
6. DW 配置对象 [0x33E6A00] 的创建点（705 处引用中无直接写入）
7. GDP 通道在运行期是否真正被使用
8. auth_task 完整状态枚举；code/result/status 取值表
```

---

## 8. 边界声明

- 本文件与 3 个 CSV 全部由**只读静态分析**产出：未运行游戏、未读写游戏进程内存、
  未修改任何既有文件（`_arch_scan.py`、`arch_*.csv`、本 md 为新增文件）。
- 本文件**不包含**、也不用于：绕过/关闭/隐藏于 ACE 等安全组件，或修改 `.text`
  以规避其检测。第 6 节给出的缺口属**数据层**（缺 `.ff` 资源），与反作弊无关。

## 9. 相关既有文档（交叉引用）

```text
CODOLServer\HANDOFF_20260929_LOBBY_PROTOCOL.md     大厅协议交接（最新）
CODOLServer\RESOURCE_MOUNT_AUDIT_20260929.md       资源挂载审计（与 §6 互证）
CODOLServer\MASTER_CALL_CHAIN.md                   端到端调用链（含 IIPS/TQoS）
CODOLServer\LOCAL_PROTOCOL_INVENTORY.md            本地写死协议 / 组件归属
CODOLServer\GDP_PROTOCOL_INDEX.md                  GDP 命令索引
CODOLServer\IIPS_PIPELINE_FULL_REVERSE.md          IIPS 全链路
CODOLServer\_subagents\tenproxy_container_report.md
CODOLServer\_subagents\cfgblock_semantics.md
CODOL第一阶段证据报告.md                            第一阶段证据与版本基线
```



