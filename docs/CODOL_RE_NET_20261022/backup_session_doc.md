# CODOL 3.19 客户端架构 / 通信链 / 对局断点 —— 2026-10-22 会话存档

> 证据等级：本文所有地址、偏移、字段均来自**运行时内存转储的实际字节**或**实际抓包日志**。
> 推断项标注 `[推断]`，未验证项标注 `[未验证]`。
> 转储文件：`run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin`
> 大小 241,537,024 = `0xE659000`，基址 `0x400000`，**dump 偏移 = VA - 0x400000**（已逐页验证）。
> 抓包：`run_codol_001\runs\OMIT_RETEST_20261022\kit\auth3074.log`、`lobby_srv.log`

---

## 0. 一句话结论

1. **游戏本体在 exe，不在 Base.dll。** Base.dll 是 CEF/平台层；IW4 引擎代码与全部 gamestate/configstring 字符串都在 exe 的 `.tp3` 段里。
2. **socket 层在 exe**，IAT 块 `0xCA8534`–`0xCA855C`，只有 10 个 ws2_32 函数，全部由 `dwauth.ini` 驱动。
3. **`dwauth.ini` 是唯一的目标配置入口**：host/port/title_id 全部由 `0x77EE40` 在启动时读入固定全局。
4. **大厅登录是三段状态机**：DW 状态机 `0x7F26C0`（5 态）× 连接状态机 `0x7F28F0`（10 态）。
5. **`.dll` 独立跑自己的 exe 不可行**：Base.dll 3 个导出全部落在 `.tvm0`（VMProtect），且不含引擎代码。

---

## 1. 客户端二进制结构

### 1.1 exe（`COD OL\codoMP_client_shipRetail.exe`，7,841,344 B）

| 项 | 值 |
|---|---|
| ImageBase | `0x400000` |
| EntryPoint | `0xE5DC690` |
| SizeOfImage | `0xE659000` |
| Import 目录 | **只有 1 个描述符**：`codoMP_client_shipRetailBase.dll`，序号 1 |
| IAT 槽 | `0xE9DC665` |

入口只有一条指令：

```asm
0xE5DC690  ff 15 65 c6 9d 0e    call dword ptr [0x0E9DC665]
0xE5DC696  ...                   （其后全 0）
```

即 **exe 是薄壳，全部工作转交给 Base.dll 导出序号 1**。

段表（RVA / 绝对 VA = 0x400000 + RVA）：

| 段 | RVA | 绝对 VA | VSize | Raw | 熵 | 说明 |
|---|---|---|---|---|---|---|
| .tp3 #0 | `0x001000` | `0x401000` | `0x8A689A` | `0x1000/0x593000` | 7.14 | **加密**，引擎主体 |
| .tp3 #1 | `0x8A8000` | `0xCA8000` | `0x16DA70` | `0x594000/0x16E000` | 5.51 | **明文**，字符串/常量，与文件匹配 99.73% |
| .tp3 #2 | `0xA16000` | `0xE16000` | `0xDBB1CC0` | `0x702000/0x62000` | 4.51 | 虚拟 219.7 MB，磁盘仅 401 KB，运行时展开 |
| .tp3 #3 | `0xE5C8000` | `0x125C8000` | `0x31` | `0x764000/0x1000` | 0 | 100% 匹配 |
| .tp3 #4 | `0xE5C9000` | `0x125C9000` | `0x9228` | `0x765000/0xA000` | 5.71 | 100% 匹配 |
| .tvm0 | `0xE5D3000` | `0x125D3000` | `0x4000` | `0x76F000/0x2000` | 6.29 | VM 入口表 |
| .tp3 #5 | `0xE5D7000` | `0x125D7000` | `0x82000` | `0x771000/0x6000` | 7.34 | 83.33% 匹配 |

**明文段（#1）换算式**：`绝对 VA = 文件偏移 + 0x714000`，反向 `文件偏移 = VA - 0x714000`。

### 1.2 Base.dll（`COD OL\codoMP_client_shipRetailBase.dll`，60,327,992 B）

| 项 | 值 |
|---|---|
| ImageBase | `0x10000000` |
| EntryPoint | `0x149C`（VA `0x1000149C`） |
| SizeOfImage | `0x3991000` |
| 标准导入 | `kernel32.dll`: `LoadLibraryA`, `GetProcAddress`；`libcef.dll`: `cef_string_utf16_clear` —— **共 3 个函数** |
| 导出 | 3 个，**全部落在 `.tvm0`**：RVA `0x1D6582C` / `0x203D4F7` / `0x1AA13B0` |

`.tvm0` 段：RVA `0x19DD000`–`0x393B000`（31 MB），熵 7.02，VMProtect 5.2.3
（字符串 `$VmpVersion: Vmp 5.2.3  Copyright (C) 1998-2014 Tencent. All Rights Reserved.` @ 文件 `0x888331`）。

**决定性否证**：Base.dll 全文件（60 MB）搜索下列引擎符号，**全部 0 命中**：

```
CA_GAMESTATE / gamestateupdate / northyaw / configstring / ConfigString
clc_ / svc_ / netchan / NET_OutOfBand / CL_Parse / CL_Send / usercmd / Com_Printf / Sys_Error
```

⇒ **Base.dll 不含游戏引擎**，只有 CEF/平台代码。

### 1.3 `.local` 目录

存在两份 `codoMP_client_shipRetailBase.dll` 副本（`exe.local\` 与 `Base.dll.local\`），
与主 DLL **逐字节仅差 6 字节**：

```
文件偏移 0x0027D80C:  ff 15 f4 22 b0 10   →  b8 01 00 00 00 90
VA        0x1027E40C:  call [0x10B022F4]  →  mov eax,1
```

`0x10B022F4` 的导入项是 `kernel32!HeapFree`。即 `.local` 版本把一处 `HeapFree` 调用
**强制改成返回 1**（不释放）。历史遗留的兼容补丁副本，与网络无关。

---

## 2. socket 层（在 exe，不在 DLL）

### 2.1 运行时 IAT 块 `0xCA8534`

从 dump 逐 dword 读出，并与 `C:\Windows\SysWOW64\ws2_32.dll` 导出表比对：

| 槽 | 函数 | ws2_32 RVA |
|---|---|---|
| `0xCA8534` | `WSAStartup` | `0x9CC0` |
| `0xCA8538` | `gethostname` | `0x300A0` |
| `0xCA853C` | `WSAGetLastError` | `0x5D50` |
| `0xCA8540` | `inet_addr` | `0x57E0` |
| `0xCA8544` | `closesocket` | `0xEA60` |
| `0xCA8548` | `socket` | `0xC990` |
| `0xCA854C` | `ioctlsocket` | `0x12520` |
| `0xCA8550` | `ntohs` | `0x56E0` |
| `0xCA8554` | `bind` | `0xD890` |
| `0xCA8558` | `setsockopt` | `[推断]` 调用形态为 `(s, 0xFFFF=SOL_SOCKET, ...)` |
| `0xCA855C` | `gethostbyname` | `0x2FF10` |

**全镜像中引用这块 IAT 的调用点极少**，且 `socket` 的创建点唯一。

### 2.2 UDP socket 创建函数 `0x77FBF0`

```asm
0x77FC00  push esi
0x77FC01  push 0x3e8              ; 1000
0x77FC0A  [ebp-0x18] = 1
0x77FC11  call dword ptr [0xCA8548]   ; socket(AF_INET=2, SOCK_DGRAM=2, 0)
0x77FC17  mov esi,eax
0x77FC19  cmp esi,-1
0x77FC3F  call dword ptr [0xCA854C]   ; ioctlsocket(s, FIONBIO=0x8004667E, &1)
0x77FC58  call dword ptr [0xCA8558]   ; setsockopt
0x77FC8F  call dword ptr [0xCA8554]   ; bind(s, &sockaddr{port, 0.0.0.0}, 14)
```

⇒ **这是唯一的 UDP socket 创建/绑定实现**，服务端端口来自函数入参。

### 2.3 上层入口 `0x77FCD0`

```asm
0x77FCD0  push edi
0x77FCD1  push 0xDD8FB8        ; 注册表值名 "Network Port"
0x77FCD6  push 2
0x77FCDD  push 0
0x77FCDF  push 0x7531
0x77FCE4  push 0xDC6634        ; 子键 "1109"
0x77FCE9  call 0x770940        ; 读注册表
0x77FCF4  call 0x77FBF0        ; 建 socket
0x77FCF9  [0x81A9F1C] = eax
```

调用链：`0x77FF38 → 0x77FCD0 → 0x77FBF0`（各只有一个调用者）。

### 2.4 与腾讯组件的边界

| DLL | 网络能力 | 归属 |
|---|---|---|
| `VSDDrvDll.dll` | 30 个 ws2_32 导入（含 `connect/sendto/recvfrom/select/accept/listen`） | 完整 BSD socket 宿主 |
| `TenRpcs.dll` | 13 个 WINHTTP + 11 个 ws2_32 | 腾讯 RPC / HTTP |
| `GameDataPlatformServer.dll` | 导出 `GDP_manager` / `destroy`，导入 `inet_addr/inet_ntoa`，**不导入 socket** | GDP 协议 schema 消费者 |
| `codoMP_client_shipRetailBase.dll` | 标准导入仅 3 个 | **不直接联网** |

⇒ 游戏侧自研 socket 面在 exe；腾讯传输面在 `VSDDrvDll/TenRpcs`，二者独立。
---

## 3. 本地对接文件（唯一配置入口）

### 3.1 `dwauth.ini` 解析函数 `0x77EE40`

逐条指令与字符串常量对应（全部从 dump 读出的实际字节）：

```asm
0x77EE5A  cmp dword ptr [0xE1F80C0], 0xB7      ; 版本门
0x77EE73  push 0xDDBD8C                        ; "使命召唤online"
0x77EE7A  call [0xCA844C]                      ; GetModuleFileNameA
0x77EEA5  call 0x63E750                        ; 载入 TenProxy.dll -> 0x82E1580
0x77EEBE  push 0xDD96B0                        ; "Cross\Apps\VideoEditor\bin\AudioHook.dll"
0x77EEC3  call [0xCA8158]                      ; LoadLibraryA
0x77EF52  call 0xC3D699                        ; fopen("dwauth.ini","r")
0x77EF64  push 0x81A7F34                       ; lsg host 缓冲
0x77EF69  push 0xDDBDA8                        ; "%59s\n"
0x77EF77  push 0x81A9780                       ; lsg port
0x77EF7C  push 0xDDBDB0                        ; "%hu\n"
0x77EF8A  push 0x81A76A8                       ; auth host 缓冲
0x77EF9D  push 0x81A9EC4                       ; 第二端口
0x77EFB0  push 0x81A9EB8                       ; title_id
0x77EFB5  push 0xDDBDB8                        ; "%x\n"
```

### 3.2 全局映射（运行时实测值）

| 全局 | 类型 | dump 实际值 | 含义 |
|---|---|---|---|
| `0x81A76A8` | char[256] | "formal-zone-auth.codol.qq.com" | auth 主机 |
| `0x81A7F34` | char[256] | "formal-zone-lsg.codol.qq.com" | lsg 主机 |
| `0x81A9780` | u16 | 3074 (0x0C02) | lsg 端口 |
| `0x81A9EC4` | u16 | 3074 (0x0C02) | auth 端口 |
| `0x81A9EB8` | u32 | 0x03EA = 1002 | title_id |
| `0x81A56A4` | u32 | 0 | 保留 |
| `0x81A76E4` | u32 | 0 | 保留 |

### 3.3 同函数读取的其它文件

| 文件 | 读取点 | 落地全局 | 结构 |
|---|---|---|---|
| `stun.ini` | `0x77F056` | `0x81A9C50` | **10 条 x 0x3C 字节**数组，末尾 `0x81A9EA8` |
| `iips.ini` | `0x77F08E` | - | `enable_iips` / `iips_url` |
| `buildconfig.ini` | `0x77F098` | `0x81A7F04` / `0x81A9770` / `0x81A7EF4` / `0x81A9C38` | build_version / column / stream / main_version |
| `cacert.pem` | `0x7F2C33` -> `0xB9A100` -> `0xC76600` | 连接对象 `+0x45C` | auth TLS 的 CA |
| `GDPOpenProtocol.tdr` | 由 `GameDataPlatformServer.dll` 消费 | - | 343 命令 / 592 类型 / 39 常量，438,856 B，magic `0x000B02D6` |

### 3.4 `stun.ini` 数组布局（实测）

```
0x81A9C50 + i*0x3C   i = 0..9
每条 60 字节 = 主机名(56) + 端口(4)  [推断]
结束地址 0x81A9EA8 = 0x81A9C50 + 10*0x3C  （完全吻合）
```

循环代码：

```asm
0x77F064  mov esi, 0x81A9C50
0x77F070  push esi / push "%59s\n" / push edi
0x77F07C  add esp,0xC
0x77F083  add esi, 0x3C
0x77F086  cmp esi, 0x81A9EA8
0x77F08C  jl 0x77F070
```
---

## 4. 大厅登录状态机（完整）

### 4.1 DW 状态机 `0x7F26C0`

`[0x84ABA50]` = DW 状态，`[0x84ABA54]` = 上一状态，`[0xE4EA3C]` = 状态字符串指针。

跳转表 `0x7F2850`（state-1 索引，state 1..4）：

| state | 目标 | 动作 |
|---|---|---|
| 1 | `0x7F26E0` | `0x7F3600` DNS 阶段 |
| 2 | `0x7F271B` | `0x7F28F0` 连接阶段 |
| 3 | `0x7F276A` | `0x7F3800` 客户端就绪判定 |
| 4 | `0x7F27B0` | `0x4A6470` 注册 CODOID |
| 5 | `0x7F284E` | 直接返回（终态） |

`0x7F2580` 是通用状态切换器：

```asm
0x7F2583  ecx = [0x84ABA50]        ; 旧状态
0x7F2589  cmp ecx, eax             ; 与目标比较
0x7F258B  je  0x7F25A0             ; 相同则不动
0x7F258D  [0x84ABA50] = eax        ; 新状态
0x7F2595  [0x84ABA54] = ecx        ; 旧状态
0x7F259B  [0xE4EA3C] = 字符串       ; 状态名
```
### 4.2 连接状态机 `0x7F28F0`

`[0x84ABA60]` = 连接状态，跳转表 `0x7F2994`（0..9）：

| state | 目标 | 动作 |
|---|---|---|
| 0 | `0x7F2902` | `push 0` -> `0x7F2B90` 建 **auth** 连接 |
| 1 | `0x7F2913` | `0x7F29C0` 发 auth 请求 |
| 2 | `0x7F291F` | `0x7F2AB0` 轮询；成功 -> `0x7F2B90` |
| 3 | `0x7F2973` | 非法，置 0 |
| 4 | `0x7F298C` | 返回 |
| 5 | `0x7F293E` | `push 1` -> `0x7F2B90` 建 **lsg** 连接 |
| 6 | `0x7F2967` | `0x7F2DB0` 装 cacert / 建 https |
| 7 | `0x7F295B` | `0x7F3100` 证书失败清理 |
| 8 | `0x7F294F` | `0x7F3190` TLS 握手轮询 |
| 9 | `0x7F298C` | 返回（成功态） |

全部 13 个状态写入点（`0x7F2xxx` 段内穷举）：

```
0x7F297F -> 0    0x7F29D7 -> 2    0x7F2AE9 -> 3    0x7F2AFC -> 0
0x7F2BB6 -> 6    0x7F2D8E -> 0    0x7F2ED8 -> 8    0x7F2F60 -> 4
0x7F2FFF -> 7    0x7F30AF -> 4    0x7F31D2 -> 0    0x7F31FA -> 9
0x7F33C3 -> 5
```

### 4.3 `0x7F2B90` = 建连接（唯一入口）

```asm
0x7F2BA8  mov ebx, [0x81A9EB8]           ; title_id = 1002
0x7F2BAF  movzx edi, word [0x81A9EC4]    ; port = 3074
0x7F2BB6  [0x84ABA60] = 6                ; 状态 -> 6（连接中）
0x7F2BCB  push 0x3E60                    ; 分配 0x3E60 = 15968 字节
0x7F2BD0  call 0xB74220                  ; operator new
0x7F2BDC  push edi                       ; port
0x7F2BDD  push 0x81A76A8                 ; "formal-zone-auth.codol.qq.com"
0x7F2BE2  push ebx                       ; title_id
0x7F2BE5  call 0xB88B80                  ; 构造 auth 连接对象
0x7F2BEA  [0x84ABB08] = eax
```

`push 1` 分支（state 5）走 lsg：

```asm
0x7F2C14  push edi / push 0x81A76A8 / push ebx
0x7F2C1D  call 0xB99090                  ; 构造 lsg 连接对象
0x7F2C26  [0x84ABB14] = eax
```

**关键：1002 和 3074 都来自 `dwauth.ini`，不是硬编码。** 改 ini 即改目标。

### 4.4 连接对象结构（`0xB88B80` 构造）

| 偏移 | 初值 | 含义 |
|---|---|---|
| `+0x00` | `0xD59A7C` | vtable（auth 版） |
| `+0x14` | 0 | **auth_task** 字段 |
| `+0x18` | `0xFFFF` | socket 句柄占位 |
| `+0x20` | 0 | 已完成标志 |
| `+0x160` | 0 | SSL/TLS 上下文指针 |
| `+0x31B0` | 0 | - |
| `+0x35F4` | 0 | SSL 对象指针 |
| `+0x35F8` | port | 端口 |
| `+0x360C` | 0x40 字节缓冲 | 主机名（拷贝自 `+0x3658`） |
| `+0x3650` | flag | 模式字节 |
| `+0x3658` | 0x400 字节 | 主机名副本 |
| `+0x3A58` | 0x400 字节 | 第二缓冲 |
| `+0x3E58` | 3 | 状态初值 |

**lsg 版**（`0xB99090`）vtable = `0xD5A1F8`，`+0x31A8 = 3`，`+0x31AC` 是 SSL 上下文。

### 4.5 auth 请求构造 `0xB9A9E0`

字段顺序（全部从 `push imm` 指令读出）：

```asm
0xB9AAAE  mov eax, [esi+0x14]      ; auth_task 当前值
0xB9AAB6  push "auth_task"
0xB9AAD5  push "iv_seed"
0xB9AAF1  push "title_id"
0xB9AB05  push "identity"          ; 常量 0xCC383C
0xB9ABC1  push "extra_data"
0xB9AC89  push "https://%s:%d/auth/"
0xB9AD1A  push "Content-Type" / "application/json"
0xB9AD34  push "X-TransactionID"
```

`auth_task` 的赋值点：

```asm
0xB99328  [esi+0x14] = 0x0A   ; 10（初始）
0xB88F41  [esi+0x14] = 0x20   ; 32
0xB9990E  [esi+0x14] = 0x0C   ; 12
```


### 4.6 auth 请求（实测抓包）

POST /auth/ HTTP/1.1
Host: formal-zone-auth.codol.qq.com:3074
Content-Type: application/json
X-TransactionID: 16165116171768878915
Content-Length: 190
Expect: 100-continue

body = {"auth_task":"10","iv_seed":"3480436955","title_id":"1002","identity":"356c4bc3",
        "extra_data":"{\"version\": \"0\", \"user_id\": \"10995207597479878709\", \"extended_data\": true}"}

响应 200，task 10 -> 11，2239 字节。

### 4.7 证书 / TLS 分支

- 0x7F2C33 push "cacert.pem" -> 0xB9A100 -> 0xC76600（写入 [obj+0x160]+0x45C）
- 0x7F2DB0 装 cacert.pem -> "https://%s/" -> 0x77B370
- 0x7F3100 SSL 错误处理；9/10 号 -> 弹 "@SF_UI_DW_LIVE_CERT_FAILED"
- 0x7F3190 TLS 握手轮询；0x22C4 判成功 -> state 9

0x331C5C0 = auth 模式开关：
- 非 0 -> 0xB88CC0（带 extra_data 的完整 /auth/）
- 为 0 -> 0x7F2D4D（"simplePassword" + 0xB992E0）

### 4.8 四个连接/探测对象

| 全局 | 构造 | vtable | 用途 |
|---|---|---|---|
| 0x84ABB08 | 0xB88B80 | 0xD59A7C | auth (HTTPS /auth/) |
| 0x84ABB14 | 0xB99090 | 0xD5A1F8 | lsg (第二通道, +0x31A8=3) |
| 0x84ABA70 | 0x7F34E0 内 | - | DW DNS 探测 A |
| 0x84ABA74 | 0x7F34E0 内 | - | DW DNS 探测 B |

### 4.9 完整时序

DW 泵 0x7EF0D0 (index 3)
 -> 0x7F2600 置 DW=1 "dwLogonStart"
    -> 0x7F26C0 switch(DW)
       DW=1 -> 0x7F3600 DNS -> 0x7F34E0
       DW=2 -> 0x7F28F0 switch(conn)
         0 -> 0x7F2B90 建 auth + lsg
         1 -> 0x7F29C0 发 auth
         2 -> 0x7F2AB0 轮询
         6 -> 0x7F2DB0 装 cert
         7 -> 0x7F3100 证书清理
         8 -> 0x7F3190 TLS 握手 -> 9
       DW=3 -> 0x7F3800 客户端就绪 -> 2 = DW_LOBBY_CONNECTED
       DW=4 -> 0x7F27B0 注册 CODOID

### 4.10 状态判定

0x7F2AD3 call 0xB9A0D0 取 [obj+0x156C] 错误码
0x7F2ADA cmp eax,0x2BC (700) 成功
0x7F2AE1 cmp eax,0x2C3 (707)
0x7F2AE8 [0x84ABA60]=3
0x7F2AF5 [0x84ABA60]=0
0x7F2B06 [0x84ABA5C]=eax

### 4.11 TLS 成功判据

0x7F31B1 call 0xB983B0
0x7F31B6 cmp eax,0x22C4
0x7F31FA [0x84ABA60]=9
### 4.12 客户端就绪判据（0x7F3800，DW=3）

```asm
0x7F3800  eax = [0x84ABA7C]        ; 子状态
0x7F3805  sub eax,0
0x7F3809  je  0x7F386B              ; 0 -> 0x7F3890 建 LSG 连接
0x7F380B  dec eax
0x7F380C  jne 0x7F3870              ; 非 1 -> 返回
0x7F380E  call 0x803830             ; 取 DW 上下文
0x7F3819  call [0xCA819C]           ; EnterCriticalSection
0x7F3826  call 0xB838A0
0x7F3838  call 0xB7A670             ; 返回码
0x7F383D  cmp eax,4
0x7F3842  jmp [eax*4+0x7F3878]
```

0x7F3890 内部：

```asm
0x7F38B3  movzx eax, word [0x81A9780]   ; lsg 端口 = 3074
0x7F38C0  call 0xB75370                 ; 构造 hosts 字符串
0x7F38EE  call 0xB9A0E0                 ; 取 [obj+0x28]
0x7F3912  call 0xB82070                 ; 建立 LSG 会话
0x7F3919  setne cl
0x7F391E  [0x84ABA7C] = ecx             ; 1 = 成功
```

即：DW=3 时先建 LSG（用 0x81A9780 的端口），成功后才置 1，DW 才会进 2（DW_LOBBY_CONNECTED）。

---

## 5. 客户端消息与配置字符串索引（运行时实测）

### 5.1 exe 明文段的关键字符串（VA = 文件偏移 + 0x714000）

| VA | 内容 | 用途 |
|---|---|---|
| 0xDC0900 | CA_DISCONNECTED | 客户端连接状态枚举 |
| 0xDC0928 | CA_CONNECTING | 同上 |
| 0xDC0954 | CA_CONNECTED | 同上 |
| 0xDC0974 | CA_GAMESTATE | 同上（进入 gamestate 阶段） |
| 0xDB4700 | gamestateupdate %d | gamestate 命令名 |
| 0xDB9754 | northyaw | 指南针/小地图初始化 |
| 0xDD66FF | mp_firingrange | 地图名 |
| 0xDBCD18 | set dw_username | 用户名字段 |
| 0xDBCD2C | connect_lobby | 大厅连接命令 |
| 0xDBFE28 | connect %s "%s" | 连接命令格式 |
| 0xDBFF0C | connectResponse | 连接应答字段 |
| 0xDBFF40 | disconnect_ack | 断连确认 |
| 0xDC2430 | ticket | 票据字段 |
| 0xDC2438 | sessionID | 会话字段 |
| 0xDC7104 | OpenID LoginKey: %s | 登录键 |
| 0xDC9D14 | tencent_ticket: %s | 腾讯票据 |

### 5.2 configstring 索引（firingrange-gamestate.bin 实测）

```
[765] = "1159"    <- 武器选择器（M4A1 Teach 典藏版）
```

### 5.3 RTTI 类名（证明协议栈结构）

```
bdSerializable / bdTaskResult / bdByteBuffer / bdStructBufferSerializable
bdMessagingGroup / bdMatchMakingInfo / bdSessionParams / bdReferencable
dwLobbyEventHandler / dwRoom / dwRoomImp / dwRoomMessageManifold
dwRoomMessageMemberList / dwRoomMessageRoomInfo / dwRoomMessageP2PInfo
MatchMaking_FIND_SERVERS_Query / MatchMaking_FIND_LOBBIES_BY_*
```

存在完整的报文集 + 请求/响应 + 推送 + 状态同步结构；承载者未定位。
---

## 6. 战斗对局部分（当前重点）

### 6.1 工程与构建

| 项 | 路径 / 值 |
|---|---|
| C 战斗服工程 | `CODOL_SERVER_319_20261021\` |
| 构建命令 | `E:\BuildTools\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe --build build --config Debug` |
| 产物 | `build\Debug\codol_battle_server.exe` |
| 端口 | UDP **28960** |
| 源码规模 | `battle_service.c` 567 行 / `snapshot.c` / `equipment.c` / `battle.c` / `world\player.c` / `world\collision.c` / `world\usercmd.c` |

### 6.2 服务端函数清单（`src\battle\battle_service.c`）

```
codol_battle_service_init
codol_battle_service_tick
codol_battle_service_on_packet
send_gamestate        （static）
send_snapshot         （static）
send_frame            （static）
send_oob_text         （static）
handle_stats          （static）
handle_plain          （static）
read_predicted        （static）
```

### 6.3 OOB 命令处理（`0xFF 0xFF 0xFF 0xFF` + 文本 + `00`）

| 客户端命令 | 服务端应答 |
|---|---|
| `stats` | `handle_stats` |
| `getchallenge <n>` | `challengeResponse 1` |
| `connect <...>` | `connectResponse`（不建 netchan 帧） |
| `heartbeat` | `heartbeatresponse` |
| `gamestateupdate <stage>` | **不回包**；`stage==6` 时 `snapshot_due_ms = now + 500ms` |

`gamestateupdate` 收到后置 `svc->gamestate_loading = true`，**停止重发 gamestate**（客户端已切到加载态）。

### 6.4 gamestate 下发

```c
// send_gamestate
读 svc->gamestate_path（默认 "firingrange-gamestate.bin"）
n = 文件字节数，合法范围 16..1100
seq = svc->netchan_seq++
payload = u32(seq) + state[n]
mask = (seq ^ 1) & 0xFF
for (i = 8; i < 4+n; i++) payload[i] ^= mask;   // 前 8 字节不掩码
send_frame(...)
重发策略：失败每 2000ms 重试，最多 5 次
首次触发：收到客户端首个非 OOB 包后 +200ms
```

**当前 gamestate 文件是静态 259 字节模板**（`run_codol_001\runs\...\kit\firingrange-gamestate.bin`），
其中 `configstring[765] = "1159"`。

### 6.5 快照下发

```c
#define CODOL_SNAP_DT_MS 7        // 128 Hz
首次：gamestateupdate stage 6 之后 500ms
每帧：send_snapshot()
       server_time = 1000 + (now - snapshot_epoch_ms)
       位置来源 = read_predicted()（predicted.bin，20ms 刷新，最大 500ms 陈旧）
       镜像未命中 -> omit = true（省略位置）
```

`read_predicted` 读 `predicted.bin`（`<6f I>` = x,y,z,vx,vy,vz,seq，28 字节 LE），
并做三层校验：**NaN**、**±100000 越界**、**文件 mtime 新鲜度**。

镜像命中时加 50ms 速度外推（`PRED_LEAD`），外推量上限 120 单位。

### 6.6 快照字段结构（`src\battle\snapshot.c`）

按 `CodolMotionSnapshot.cs` 对齐：

- `playerstate` 段：**124 字节**
- 尾部 `clientInfo` 段：**127 字节**（`test_snapshot` 输出 127 bytes）
- 已删除多余字段：index 62 / 83 / 107 / 162
- `groundEntityNum`（index 61）：恒 `2047`
- `ViewHeight`（index 38 附近）：直写 **60**（修过 `60^60=0` 的 XOR 归零问题）
- 每帧按 `to ^ from` 写增量（`MSG_WriteDeltaField` 语义），`snap_from = snap_cur`

### 6.7 已知的对局故障（全部有实机证据）

| 现象 | 证据 | 结论 |
|---|---|---|
| 出生在房顶 / 不下落 | z 恒 `-116`，35326 帧无变化 | 服务端 `omit_motion=0` 时客户端直接采用服务端 z，不跑自己的物理 |
| 主武器空、副武器有枪 | 客户端内存 configstring 只有 9 条，唯一武器选择器 `1159` 被绑到副武器槽 | 服务端只下发 1 个武器槽选择器 |
| 开火只扣子弹数 | 真实 usercmd `btn` 从未出现 bit0 | 客户端进图后停止上报真实按键 |
| 小地图全空 | 主 configstring 无 `northyaw`，也无 `compass_map_*` | 缺少 minimap configstring |

### 6.8 usercmd 实测按钮分布

```
FINAL 轮：
  btn=0x20000800  18 次   bits=[11,29]      ADS + 未知 bit29
  btn=0x00000000   4 次
  btn=0x10000000   1 次   bit28
  无任何一帧含 bit0（ATTACK）

KEYMAP_CAL 标定轮（按键正确响应时）：
  btn=0x00002002  bits=[1,13]              W+Shift（bit1 = SPRINT）
  btn=0x00000200  bits=[9]                 单独 Shift
  btn=0x20102801  bits=[0,11,13,20,29]     鼠标左键（bit0 = ATTACK）
```

IW4X `usercmdButtonBits` 权威定义：

```
ATTACK  = 1<<0  = 0x1
SPRINT  = 1<<1  = 0x2
MELEE   = 1<<2  = 0x4
ACTIVATE= 1<<3  = 0x8
RELOAD  = 1<<4  = 0x10
...
ADS     = 1<<11 = 0x800
```

⇒ **按键位定义正确，解析器正确（600 用例 + 15 条真实 body 全 0 失配），
但客户端进图后的 usercmd 内容被冻结在残留值。**

### 6.9 客户端 configstring 实际内容（进图后内存实读）

客户端 configstring 表基址 `0x0C47A48D`，**只有 9 条**：

```
[0] \2482\2\2485\1\2490\214\2491\0\3056\2\g_gametype\coop\g_hardcore\0\mapname\coop_train_mp_firingrange\scr_game_allowkillcam\0\scr_team_fftype\0
[1] (空)
[2] cod
[3] 1
[4] 0 0 0 1
[5] 1159
[6] ** 585 0 0 6690 9930 10545 8738 9321 6747      ← M4A1 + 6 配件
[7] ** 1112 0 0 6690 9930 9321 6747                ← Vector + 4 配件
[8] ** 646 0 0 8738 9321                           ← M9 + 2 配件
```

存储格式：**紧凑 NUL 拼接**（非固定 stride、非指针数组），且**没有任何指针指向该块**
⇒ 是临时缓冲，逐条解析后立即分发，**无法运行时追加**。

⇒ 真实服务器应有**数千条** configstring。小地图、背包、雷达、材质全部依赖它。

### 6.10 gamestate / configstring 生成器缺口

2.6.9.7 服务端（`codol_dedrun.exe`）已解出的写帧算法：

```c
CODOL_WriteConfigstrings(msg, ctx, cstr, count, cmp, cmpCount):
    WriteByte(4);                    // opcode
    WriteShort(count);               // <= 0x1DD7 (7639)
    prev = -1;
    for (i = 0; i < count; i++) {
        index_bits(msg, cstr[i].index, &prev);   // 递增索引编码（未解）
        WriteString(msg, cstr[i].value);
    }
    WriteBits(msg, cmpCount, 11);    // <= 0x7FF (2047)
    prev = -1;
    for (i = 0; i < cmpCount; i++) {
        index_bits(msg, cmp[i].index, &prev);
        WriteBits(msg, cmp[i].value, 10);
    }
    WriteBits(msg, ?, 10);
    WriteBits(msg, ?, 4);
```

**唯一缺口：`index_bits()` 的位编码规则**（递增索引如何压缩）。
`0x4A0400` 在 3.19 客户端镜像里**不是**该函数（是 `std::vector::push_back`），
地址来自 2.6.9.7 服务端，**不能直接套用**。

### 6.11 碰撞 / 出生点

- 出生点 `48, -572, -116` 来自解出的 zone 实体 `info_player_start_so`，是**地图唯一设计出生点**
- `src\world\collision.c`：29 个 clip 盒 + 地面 z = -116，AABB sweep
- `src\world\player.c`：真实重力 + 逐轴 sweep，`CODOL_BTN_SPRINT = 0x2`，`CODOL_SPRINT_SPEED = 320`
- **局限**：clip 盒统一按 64×64×64、以实体 origin 为中心；地形/楼梯/斜坡无碰撞

### 6.12 clipMap 解析进度（`_map_extract\coop_train_zone.bin`）

已定位的区段（绝对偏移）：

```
0x23EFC4..0x23F044  TriggerModel[16]   每项 8B {contents=0x28000001, hullCount, firstHull}
0x23F044..0x23F4C4  TriggerHull[32]    每项 32B {Bounds 24B, contents, slabCount u16, firstSlab u16}
0x23F4C4..0x23F564  TriggerSlab[8]     每项 20B {dir3 单位向量, midPoint, halfSize}
0x23F564..0x23F59C  目录 7 组 (count, cleared-ptr): (27, 4, 27, 144, 30, 30, 30)
0x23F5A4..0x23F7C0  cplane_s[27]       20B/项，单位法线
0x23F7C0..0x23F7F0  ClipMaterial[4]    12B/项 {namePtr=-1, surfaceFlags, contents}
0x23F7F0..0x23F81B  材质名 "clip_player"/"clip_shot_block"/"clip_full"/"clip"
0x23F81B..0x23F8F3  cbrushside_t[27]   8B/项，plane 指针步长恰为 20B
0x23F8F3..0x23F983  brushEdges[144]
0x23F983..          cLeaf / leafbrushNode 记录流（20B stride，未闭合）
```

自洽点：27 planes ↔ 27 brushside 指针（步长 20）↔ 目录里的 27；4 材质 ↔ 4 材质名；144 brushEdges ↔ 目录 144。

**未闭合**：`cLeaf_t`(40B) / `cLeafBrushNode_t`(20B) / `CollisionAabbTree`(32B) / `cmodel_t`(68B) / `cbrush_t`(36B) 的数组边界。

### 6.13 单元测试现状

```
test_snapshot             127 bytes
test_snapshot_delta       ALL PASSED
test_player               ALL PASSED
test_equipment            ALL PASSED
test_collision            ALL PASSED
test_backpack_reliable    ALL PASSED
test_regression_20261022  ALL PASSED
test_usercmd              600 cases 0 mismatch
test_usercmd real_cases   15 cases 0 mismatch
```

### 6.14 战斗侧下一步

1. **configstring 生成器**：补 `index_bits()`，把 9 条扩到完整表（小地图 / 背包 / 雷达都靠它）
2. **背包**：gamestate 的 `configstring[765]` 与快照 index 39 必须一致（都用 `1159`）
3. **clipMap 闭合**：以 `0x23F564` 的 7 组目录为起点做链式约束求解
4. **usercmd 冻结**：确认客户端为何进图后停止上报按键（与 gamestate 完整性相关）

### 6.15 硬阻塞

**ACE-BASE.sys / ACE-GAME.sys 内核驱动**拦截 `ReadProcessMemory`（err=5），
即使持有 `SeDebugPrivilege` 且 `OpenProcess` 成功。

唯一可行读取方式：`CreateProcess(CREATE_SUSPENDED)` → `OpenProcess(PROCESS_VM_READ)` → `ResumeThread`。
脚本：`CODOLServer\_mainline\_dyn100_mem.py`。
---

## 7. 未解项与后续索引

### 7.1 仍未定位

| 项 | 状态 |
|---|---|
| 游戏 netcode 的收发承载者（NET_SendPacket 等价物） | 未定位。Base.dll 无该符号；exe 段 0 已解壳但未找到 netchan 命名空间 |
| MSG_WriteDeltaField 的 configstring index_bits() | 未解（只有 2.6.9.7 服务端算法骨架） |
| compass_map_* / northyaw 的完整取值 | 未找到来源；common_mp.ff（77 MB）已解出，待查 |
| 快照 index 28（eFlags，codec -98）/ index 82（radarFlags，codec -101） | 编码未确定，暂不发 |
| GVoice / QTalk / InChannel 事件通道 | 仅有 RTTI 名，未追 |

### 7.2 关键路径

| 用途 | 路径 |
|---|---|
| 本次内存转储 | run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin（241,537,024 B） |
| auth 抓包日志 | run_codol_001\runs\OMIT_RETEST_20261022\kit\auth3074.log |
| 大厅抓包日志 | run_codol_001\runs\OMIT_RETEST_20261022\kit\lobby_srv.log |
| 单轮链配置 | run_codol_001\runs\OMIT_RETEST_20261022\kit\（副本，受保护原件不动） |
| 解出的地图 zone | _map_extract\coop_train_zone.bin（6,291,523 B） |
| 地图实体串 | _map_extract\coop_train_entities.txt（381 个实体） |
| 出生点表 | _map_extract\coop_train_spawns.json |
| 2.6.9.7 服务端反汇编 | CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\_data\disasm_key2697.txt |
| 快件解包工具 | CODOL_SERVER_319_20261021\tools\codol_ff_unpack.py |
| 内存转存脚本 | CODOLServer\_mainline\_dyn100_mem.py |
| 本轮分析脚本 | CODOL_RE_NET_20261022\（只读分析，未改任何游戏文件） |

### 7.3 本次会话新增分析脚本

| 文件 | 内容 |
|---|---|
| inspect_pe.py | exe / Base.dll 段表、导入、导出、TLS |
| resolve_exe_iat.py | exe 运行时 IAT 与 ws2_32 导出表对齐 |
| all_ws2_slots.py | 全镜像 ws2_32 指针槽扫描（25 处） |
| dump_cfg_region.py | dwauth.ini 解析函数字符串常量 |
| jtables.py | DW / conn 两张跳转表的实际目标 |
| state_writes.py | 连接状态机 13 个写入点穷举 |
| rtti_names.txt | 185 条网络/大厅相关 RTTI 类名 |
| find_transport.py | TenProxy / VSDDrv / GameRpcs 字符串与引用 |

---

## 8. 结论

1. **通信层在 exe 的 .tp3#1 + .tp3#0，不在任何 DLL。** 配置入口唯一：dwauth.ini。
2. **大厅登录已完整还原到指令级**：5 态 DW x 10 态 conn 两条状态机、4 个连接对象、1 个 HTTPS 请求契约。
3. **.dll 自建 exe 不可行**：Base.dll 全部导出在 VMProtect 段内，且不含引擎代码。
4. **战斗对局的瓶颈不在网络层，在 gamestate / configstring 内容。** 客户端只收到 9 条 configstring，而真实服务器有数千条；小地图、背包、武器、雷达全部依赖它。
5. **背包问题的正确解法**：让 configstring[765] 与快照 index 39 使用同一个武器 ID（1159）。
6. **开火只扣弹**：usercmd 的 bit0 在进图后从未出现，先解决 gamestate 完整性再回头看输入。

---
*生成时间：2026-10-22*

---

## 9. 战斗侧新增（2026-10-22 21:xx）

### 9.1 configstring 的真实载体是 InfoString 表，不是字符串数组

- `0xE7B6490`（进图后含 `1159` / `2485\1\...` 的那块）**不是 configstring 数组**。
  它的写入者是 `0x66EF60`：一个 **COM_Parse token 缓冲**，
  逐字符还原 `\` 转义（`0x25` -> `0x2E`），末尾写 `[0xE7B848F]=0`。缓冲区上限 `0x2000`。
- 真正被读的是 **InfoString 键值表**，结构：
  `{ char *buf; int count; struct { char *name; char *value; } entries[]; }`（entry 8 字节）
- 读取函数 `0x4E88D0`：

```asm
0x4E88D6  mov ecx,[ebp+8]      ; table
0x4E88D9  mov eax,[ecx+4]      ; count
0x4E88EB  jle 0x4E8971         ; count<=0 -> 返回 default
0x4E88F1  add ecx,8            ; entries
0x4E88FA  mov eax,[eax]        ; name ptr
; 逐字符、大小写不敏感比较（0x41..0x5A 先 +0x20）
0x4E8941  mov ecx,[ebp+0x14]   ; out
0x4E8946  mov [ecx],eax        ; 命中 -> 写 value
```

签名：`Info_GetConfigValue(table, key, default, out)`。

### 9.2 northyaw 的读取路径（小地图空 = 这里返回 default）

```asm
0x4EC167  lea ecx,[ebp-0x20]        ; out
0x4EC16B  push 0xD AE091            ; default = ""
0x4EC170  push 0xDB9754             ; key = "northyaw"
0x4EC175  push 0x32AD060             ; table
0x4EC17A  call 0x4E88D0
0x4EC182  mov ax,word[0x7AA9CB6]
0x4EC18B  cmp byte ptr [esi],0       ; 若为空 -> 跳到 0x4EC21F，跳过指南针初始化
0x4EC27C  fld1 / fstp [0x32AF42C]    ; 否则 northyaw=1
0x4EC284  fldz / fstp [0x32AF430]
```

同一函数还读 `0x4EC28C` 段的 `0xDB9700`（`spawnflags`）与 `0x4EC33D` 的 `0xDB9760`（`ambient`），
说明 `0x32AD060` 是 **worldspawn 的 InfoString**（解出的 zone 里 `worldspawn` 紧跟其后就是 `northyaw`）。

本 dump 中 `[0x32AD060]=0`、`[0x32AD064]=0` —— **count 为 0，表是空的**，
所以 `northyaw` 取不到，指南针/小地图不初始化。

### 9.3 由此得到的可执行结论

1. 小地图的修复点不是"往 configstring 数组塞 northyaw"，而是**让世界实体的 InfoString 表里存在 `northyaw`**。
2. 解出的 `coop_train_zone.bin` 里 `worldspawn` 之后紧邻 `northyaw`（文件 `0xDB9754` 是字符串常量，
   zone 内实体串也含该键），即**地图自带该键**，只是没进到客户端这张表。
3. 下一步：找 `0x32AD064`（count）的写入点 / `Info_StringToTable` 的调用点，
   确认 CS[0] 是否被解析进这张表。若没解析，说明我们的 CS[0] 格式或触发顺序不对。
---

## 10. 战斗侧：worldspawn / InfoString 链

### 10.1 0x32AD060 是 worldspawn 的 InfoString 表

结构（从 0x4E8660 逐指令读出）：

```c
struct InfoTable {          /* 0x32AD060 */
    char  valid;            /* +0x000 */
    int   count;            /* +0x004   最多 0x40 */
    char *names[64];        /* +0x008 + i*8 */
    char *values[64];       /* +0x00C + i*8 */
    int   textLen;          /* +0x208 */
    char  text[0x800];      /* +0x20C */
};
```

实测 dump：valid=0、count=0，表是空的。

### 10.2 0x4E8660 = Info_ParseString（要求大括号包裹的 key/value）

```asm
0x4E867D  mov byte [edi],0            ; valid=0
0x4E8680  mov [edi+4],0               ; count=0
0x4E8683  mov [edi+0x208],0           ; textLen=0
0x4E868B  call 0x4E85E0               ; Com_Parse
0x4E86DB  cmp byte [ebp-0x404],0x7B   ; 必须是 '{'
0x4E8700  loop:
0x4E8761    call 0x4E85E0             ; 读 key
0x4E87A8    cmp byte [ebp-0x404],0x7D ; '}' 结束
0x4E8837    mov [edi+eax*8+8], ebx    ; names[count]
0x4E8898    mov [edi+eax*8+0xC], ebx  ; values[count]
0x4E889F    inc dword [edi+4]         ; count++
0x4E88B4  mov byte [edi],1            ; valid=1
```

缓冲区上限 0x800（0x4E87F5 / 0x4E8859）。

### 10.3 0x4EC500 = 世界初始化

```asm
0x4EC500  mov edi,0x32AD060
0x4EC506  call 0x4E8660        ; (1) 第一次 parse（worldspawn）
0x4EC50F  push 0xDB97BC        ; 失败日志
0x4EC51E  call 0x4EBFB0        ; (2) 处理 classname
0x4EC528  call 0x4E8660        ; (3) 第二次 parse
0x4EC531  loop: call 0x4EBF30  ; (4) 逐实体处理
0x4EC53B    call 0x4E8660      ; (5) 下一个实体
```

0x4EBF30 读 classname（0xDB971C），0x4EBED0 查实体类表，0x4ED190 -> 0x4EBDF0 分发。

### 10.4 0x4EBFB0 = worldspawn 后处理

```asm
0x4EBFCB  push 0xDB971C          ; "classname"
0x4EBFD0  push 0x32AD060
0x4EBFD5  call 0x4E88D0
0x4EBFE3  mov edx,0xDB9740       ; "worldspawn"
0x4EBFE8  call 0x7745E0          ; strcmp
```

之后依次读：northyaw（0x4EC176）、spawnflags（0x4EC29B）、ambient（0x4EC33E）、sunLight（0x4EC373）、sunColor（0x4EC397）。

表为空则 northyaw / ambient / sunLight 全部取默认值，小地图与光照不初始化。

### 10.5 我们的 gamestate 喂的格式不对

firingrange-gamestate.bin 259 字节布局（实测）：

```
0x00  00 00 00 00                    flags
0x04  03 00 00 00                    count = 3
0x08  "coop_train_mp_firingrange\0"
0x2A  "coop\0"
0x2F  cd cd f0 62 04 06 00 af        8 字节杂项
0x37  "\2482\2\2485\1\2490\214\2491\0\3056\2\g_gametype\coop\g_hardcore\0\mapname\..."  <- CS[0]
0xC2  "cod\0"
0xC6  "1\0"
0xCA  ca 65 "0 0 0 1\0"
0xD3  fd 02 "1159\0"
0xD8  "0\0"
0xDA  cc 5b 92 00 98 88 a6 6c ...    40 字节
```

CS[0] 是 Quake3 的 反斜杠 key/value 形式，但 0x4E8660 只认大括号+双引号形式。
0x4E86DB 检查首字符必须是 0x7B，0x4E874E 检查 0x7D。
我们的串以 0x5C 开头，解析失败，表保持空。

### 10.6 修复方案

CS[0] 改为：

```
{ "classname" "worldspawn" "ambient" "116" "northyaw" "0" "sunLight" "..." "sunColor" "..." }
```

要点：
- 外层必须有花括号
- key/value 用双引号包裹，不是反斜杠分隔
- 同一实体的键值对写在同一花括号内
- 多实体时依次写多个花括号块

这样 0x4E8660 才会把 northyaw 写进 0x32AD060，0x4EC27C 才会执行 [0x32AF42C]=1.0。
---

## 11. 收尾：Com_Parse 输入源

- `0x4E85E0` = Com_Parse：取 cmd 上下文，`imul ecx,0x420` 定位，token 写入上限 `0x3FF` 的缓冲
- 调用链唯一：`0x4EBF30 <- 0x4EC531`，`0x4EBFB0 <- 0x4EC51E`，`0x4EC500 <- 0x61707D`
- dump 中无带引号的 `ambient` / `classname`（0 命中）⇒ 实体串文本未保留，仅留 `0x32AD060` 解析表
- 我们的 CS[0] 首字节 `0x5C` 而非 `0x7B` ⇒ 解析器放弃 ⇒ 表空

### 战斗侧修复清单

| # | 项 | 改动 | 依据 |
|---|---|---|---|
| 1 | CS[0] 格式 | 花括号 + 双引号 key/value | `0x4E86DB` / `0x4E874E` |
| 2 | northyaw | worldspawn 加 `northyaw` | `0x4EC176` |
| 3 | ambient / sunLight / sunColor | 同实体补齐 | `0x4EC33E` / `373` / `397` |
| 4 | 背包 | CS[765] 与快照 index 39 统一 `1159` | 实测 |
| 5 | 出生点 | 48 / -572 / -116 | zone 实体 |
| 6 | 开火 | CS 完整后再查 usercmd bit0 | 实测 |
