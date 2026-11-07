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


---

# Appendix A: prior session archive

# CODOL 3.19 C 战斗服 —— 进度存档（2026-10-22 00:22 暂停）

> 本文件只记录**本轮实际验证过的**内容；推断标注 `[推断]`，未完成标注 `[未完成]`。
> 暂停时环境：无客户端/战斗服/注入器进程残留，无 agent 子进程，UDP 28960 空闲。

---

## 0. 一句话现状

**移动/输入/开火状态机已接通；出生点已用地图自己的实体数据修正；
但"落地/穿墙"仍未解决——因为服务端还没有地图碰撞数据。小地图、角色外观、背包武器同样未完成。**

当前构建：`build\Debug\codol_battle_server.exe`
SHA-256 = `F44159EDBB38F8A76016AED0A9683F5FD88F0989D771F9B48DE92933A3DB442D`
单体测试：**15/15 通过**

---

## 1. 本轮最大突破：CODOL 快件（.ff）完整解密

此前多次卡在"读不出地图数据"。本轮把整条链打通，**这是后面所有世界/碰撞工作的前提**。

### 1.1 容器格式（已实测）

```
IWff0100 容器
  0x000  8   "IWff0100"
  0x008  4   version = 461
  0x015  256 RSA-2048 PKCS#1 v1.5 包裹的 key_material(40B)
  0x115  ..  AES-192-CTR 数据体（按 0x2000 分块）
数据体：
  block0(0x2000):  CTR(IV = key_material[24:])  -> "IWffs100" + zone名(300) + level-1 摘要表(336 + i*32)
  之后每 section:   CTR(IV = block0[336+i*32][:16])  -> level-2 表（每 32B 是各数据块的 SHA-256）
  每个数据块(0x2000): CTR(IV = 该块 SHA-256[:16])
  拼接后 zlib.decompress -> zone
```

**关键点：不是连续 CTR 流，而是"每块用自己的 SHA-256 前 16 字节当 IV"。**
这解释了为什么按连续流解永远得不到合法 deflate。

来源：
- 格式与打包器：`_e1_regression\ol-mod-olfinal\tools\reverse\OlfinalFastfile.py`（其 `unpack_zone()` 即规范）
- 密钥：与 **IW4X `Components\Modules\FastFiles.cpp` 的 `ZoneKey`** 同源；IW4X 的
  `AuthLoadInflateDecryptBaseFunc` / `AuthLoadInflateCompare` / `InflateInitDecrypt` 就是这套逐块 CTR + inflate

### 1.2 可复现命令（已固化为工具）

```powershell
# Layer1 + Layer2 一条命令（工具已入库）
cd D:\BaiduNetdiskDownload\使命召唤OL\CODOL_SERVER_319_20261021
python -X utf8 tools\codol_ff_unpack.py ..\_map_extract\coop_train_mp_firingrange.ff ..\_map_extract\coop_train_zone.bin --name coop_train_mp_firingrange

# 分解看：Layer1
cd D:\BaiduNetdiskDownload\使命召唤OL\_PLAINTEXT_PROJECT
# Layer1（CTR 解出 IWffs100 + zone 名）
python -X utf8 tools\codol_ff_decrypt.py ..\_map_extract\coop_train_mp_firingrange.ff --out _l1test --json
# Layer2（逐块 CTR + zlib）见本目录下的 _map_extract\coop_train_zone.bin（已解出，6,291,523 B）
```

### 1.3 本轮产出

| 产物 | 说明 |
|---|---|
| `_map_extract\coop_train_zone.bin` | **解压后的 coop_train_mp_firingrange zone（6.29 MB）** |
| `_map_extract\coop_train_entities.txt` | 从中提取的地图实体串（51,189 B / 381 个实体） |
| `_map_extract\coop_train_spawns.json` | 出生点表 |
| `CODOL_SERVER_319_20261021\tools\codol_ff_unpack.py` | **Layer2 解包工具（新增，可复现）** |

---

## 2. 出生点：已用地图自己的实体数据修正

从解出的 zone 实体串得到的**唯一设计出生点**：

```
info_player_start_so   origin = 48 -572 -116
（worldspawn 0 0 0；其余 379 个是 script_model/script_brushmodel/script_struct/trigger_*）
```

**结论：48 / -572 / -116 本来就是对的。**

`[已修正]` 中途曾照某份 C# 配置把它改成 `-127.018`（比地图出生点**低 11 单位**）→
人物陷进地板 → 表现成"卡住 / 在房顶"。现已改回：

```c
// src/battle/battle_service.c
codol_player_init(&svc->player, 48.0f, -572.0f, -116.0f);
```

---

## 3. 本轮代码改动（CODOL_SERVER_319_20261021）

### 3.1 结构性修复：快照字段的"新值 XOR 基线"

依据 `CoD4x msg.c:1983-2216 MSG_WriteDeltaField`：
```
case -88:  MSG_WriteLong(msg, to ^ from);                       // float
case -87:  MSG_WriteAngle16(msg, to);                           // 角度不异或
default:   if (to) { bit1; write (to ^ from), abs(bits) 位 } else bit0;
```
此协议**每个字段写的是 `to ^ from`**。首帧 `deltaNum=0`（基线全零）时裸值恰等于异或值，
所以看起来"能跑"；**第二帧起客户端拿上一帧做基线，写裸值就全错**。

- 新增 `codol_snap_state_t` 帧基线；`codol_snapshot_build(..., const codol_snap_state_t *from, codol_snap_state_t *cur, ...)`
- 服务层每帧 `snap_from = snap_cur`
- 新测试 `tests/test_snapshot_delta.c`：首帧含裸值 / 同值第二帧写成 0 / 变化帧写异或值

### 3.2 快照字段

| 项 | 之前 | 现在 | 依据 |
|---|---|---|---|
| `command_time` | 写死 1000 | `processed_input_time` | 客户端 usercmd 的确认；写死会导致**指令溢出** |
| 左右武器状态 | 只写 index 17/3/44（**右/副武器**） | 另写 **62/162/107**（左/当前武器） | 3.19 字段表 `LeftWeaponState/Time/Delay` |
| index 61 | 恒 2047 | `on_ground ? 2046 : 2047` | groundEntityNum |
| index 83 | 从未写 | `0`（PM_NORMAL） | pm_type；否则客户端走 spectator/noclip |
| 快照速率 | 20 Hz | **128 Hz**（tick 也 128） | 参考实现实机采样率 |
| 武器 | 写死 1156 | 采信 `usercmd.weapon`（实测该值常为 0，**暂无实效**） | CoD4x/IW4 语义 |

### 3.3 移动模型（`src/world/player.c`）

照 `CODOL-Combat-Server-v0.1\src\Engine\GameWorld.cs:621-638`：
`dir_bias = 0 -2`、`flip_move_y = 1`、`flip_strafe_x = 1`、`WalkSpeed = 190`、`vertical_sim = 0`（不积分 Z）。

### 3.4 装备状态机（`src/battle/equipment.c`，本轮新增）

逐行移植参照的 `_Slot`/`_Equipment`：开火扣弹/射速冷却/换弹转运/空仓换弹/半自动/背包切换。
测试 `tests/test_equipment.c`。

### 3.5 其它

- `/utf-8`（MSVC 源文件编码，消除 C4819）
- `tools/ref_reader.py` + `gen_cases.py` + `cases.txt` + `test_usercmd.c`：C 解析器 vs 参照读取器**差分对账台**
  （600 用例 0 失配；真实客户端 16 条 body 字节 **16/16 一致**）
- `tools/scan_map_entities.py`：从**活客户端内存**抓地图实体串（备用路径，本轮未用上）
- `run_codol_001\runs\make_run_dir.py` + `check_protected_integrity.py`：每轮隔离目录与受保护文件哈希

---

## 4. 已验证 / 未验证（不得混淆）

### 已在真实客户端上验证
- NAT / DTLS init / 密钥交换 / stats / game state / netchan 全链路
- `[world] USERCMD` 出现，`time` 递增、`yaw/pitch` 随转头变化、`F/R` 随按键变化
- 与参照读取器在**真实字节**上 16/16 一致
- 出生点 `48,-572,-116` 与**地图实体数据**一致
- 开镜状态生效（用户实测确认）
- 快照能被客户端接受并进入对局（`RX_GAMESTATE_PROGRESS 1..6`）

### 未验证 / 未完成
- **落地 / 穿墙 / 真实 ground trace** —— 服务端**没有地图碰撞**，`vertical_sim=0` 时不动 Z
- **小地图** —— 本地图 zone 内无 `compass/radar/northyaw` 字符串，需从 `common_mp.ff`（77 MB，已解出）或 configstring 找
- **角色外观 / 背包武器** —— 仍写死；`usercmd.weapon` 实测为 0，此通道不存在
- 快照 index 82（radarFlags，codec -101）/ index 28（eFlags，codec -98）**编码未确定，暂不发**

---

## 5. 下一步（按优先级）

1. **从同一 zone 里定位 clipMap**（planes/nodes/leafs/brushes/leafbrushNodes）→ 移植 CoD4x
   `cm_local.h` / `cm_load_obj.cpp` / `cm_trace.c` / `cm_test.c`，给服务端加 `CM_BoxTrace` / `CM_PointContents`。
   拿到之后：水平位移用 sweep、垂直用 trace 找地面、`groundEntityNum` 用真实接触。
2. **小地图**：用同一套解密流程解 `common_mp.ff`，找 compass/radar 材质与 `northYaw` configstring，
   写进 gamestate 的 minimap configstring。
3. **武器/角色**：`usercmd.weapon` 不可用；需从角色定制/装配来源取，或改为**不下发**这些字段让客户端保留大厅状态。
4. 快照 index 28 / 82 的 codec 编码（-98 / -101）从客户端解析器轨迹
   （`CODOL-BATTLE-SERVER-CLIENT-PARSER-SEMANTICS-046\_extracted\reference\playerstate-*-trace.json`）
   或 CoD4x `MSG_WriteEFlags` 定下来后再发。

---

## 6. 关键路径索引

| 用途 | 路径 |
|---|---|
| C 服工程 | `CODOL_SERVER_319_20261021\` |
| 构建 | `E:\BuildTools\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe --build build --config Debug` |
| 快件解密器(Layer1) | `_PLAINTEXT_PROJECT\tools\codol_ff_decrypt.py` |
| 快件解包工具(Layer1+2) | `CODOL_SERVER_319_20261021\tools\codol_ff_unpack.py` |
| 快件打包/解包规范 | `_e1_regression\ol-mod-olfinal\tools\reverse\OlfinalFastfile.py` |
| IW4X 引擎核心 | `IW4X\iw4x-client\src\Components\Modules\FastFiles.cpp`、`src\Game\Structs.hpp` |
| CoD4x 编码/碰撞 | `CoD4x_Server-21.2\src\msg.c`（MSG_WriteDeltaField）、`cm_local.h`、`cm_load_obj.cpp`、`cm_trace.c` |
| 3.19 字段表 | `CODOL-BATTLE-SERVER-CLIENT-PARSER-SEMANTICS-046\_extracted\reference\playerstate-fields.json` |
| 客户端解析轨迹 | 同目录 `playerstate-*-trace.json` |
| 解出的地图 zone | `_map_extract\coop_train_zone.bin` |
| 本轮运行目录 | `run_codol_001\runs\C_SERVER_FIRST2..13_20261021\`（每轮独立；`kit\` 为链副本） |

## 7. 本轮未启动客户端

用户要求“没修完就不要起”，所以**本轮没有跑任何实机测试**；出生点修正只做了离线实体数据校验与单体测试。
下一次真正要验证的就一件事：**人能否站在地面上且自由移动**。

## 8. 受保护文件状态（AGENTS.md）

`REF_LOBBY_KIT\_golden_hashes.json` 比对：唯一 FAIL 是**先于本会话**的既有漂移
`marketplace_store.py`（实际 50022 B / `E44358F0...`，manifest 期望 46226 B / `28B4A1BE...`，
修改时间 2026-10-16）。本会话**未读写** `REF_LOBBY_KIT` 与 `CODOL_VERIFIED_GOLDEN_20261019` 下任何文件。
可还原来源：`run_codol_001\runs\ONCE_20261021_14*\kit\marketplace_store.py`（46226 B，与 manifest 一致）。

---

# 2026-10-22 续接会话：clipMap 定位 + 最小碰撞层落地

## 0. 一句话

**已完成**：clipMap 关键段定位（自校验工具）、碰撞层 `codol_collision.c` 落地、移动模型改为真实重力+地面/障碍 trace；**全部 18 个单测通过**。
**未完成**：clipMap 的完整精确解析（aabbTrees/cmodels/brushes 数组边界未闭合），当前碰撞是**轴对齐近似**。

## 1. 本轮新增产物

| 文件 | 说明 |
|---|---|
| `tools\clipmap_locate.py` | **新增**。从解包 zone 定位 MapEnts/TriggerModel/TriggerHull/TriggerSlab/cplane/材质名/brushside 指针表，全部带自校验（`SELF-CHECK OK`） |
| `include\codol_collision.h` | **新增**。碰撞 API：`codol_collision_box_trace` / `codol_collision_point_solid` |
| `src\world\collision.c` | **新增**。29 个 script_brushmodel 轴对齐 clip 盒 + 地面平面 z=-116；AABB sweep（slab 法，照 CoD4x cm_tracebox 语义） |
| `include\codol_clipmap_approx.h` | 数据快照（与 collision.c 同源） |
| `tests\test_collision.c` | **新增**。5 组断言：落地、空地移动、clip 阻挡、点实体判定、盒数量 |
| `_map_extract\coop_train_collision_approx.json` | 近似碰撞数据（机器可读） |
| `_map_extract\mp_firingrange_zone.bin` | mp_firingrange 解包 zone（57.9 MB） |

## 2. 已确证的 clipMap 结构（可复算）

`coop_train_zone.bin`，全部偏移经 `tools\clipmap_locate.py` 自校验：

```
0x2327CE..0x23EFC3  entity text (51,189 B)
0x23EFC4..0x23F044  TriggerModel[16]   每项 8B {contents=0x28000001, hullCount, firstHull}
0x23F044..0x23F4C4  TriggerHull[32]    每项 32B {Bounds 24B, contents, slabCount u16, firstSlab u16}
0x23F4C4..0x23F564  TriggerSlab[8]     每项 20B {dir3 单位向量, midPoint, halfSize}
0x23F564..0x23F59C  目录 7 组 (count, cleared-ptr):
                      (27, 4, 27, 144, 30, 30, 30)
0x23F5A4..0x23F7C0  cplane_s[27]       20B/项，单位法线
0x23F7C0..0x23F7F0  ClipMaterial[4]    12B/项 {namePtr=-1, surfaceFlags, contents}
0x23F7F0..0x23F81B  材质名 "clip_player"/"clip_shot_block"/"clip_full"/"clip"
0x23F81B..0x23F8F3  cbrushside_t[27]   8B/项，plane 指针步长恰为 20B（与 plane 数一一对应）
0x23F8F3..0x23F983  brushEdges[144]
0x23F983..           cLeaf/leafbrushNode 记录流（20B stride，未闭合）
```

**自洽点**：27 planes ↔ 27 brushside 指针（步长 20）↔ 目录里的 27；4 材质 ↔ 4 材质名；144 brushEdges ↔ 目录 144。

## 3. 本轮代码改动

- `src\world\player.c`：删除 `vertical_sim=0`（不积分 Z、`on_ground=true` 写死）的旧行为，改为
  - 水平 X/Y 各自独立 sweep（避免斜向穿角）
  - `vz -= gravity*dt` 后向下 trace
  - 命中且 `normal.z > 0.5` → 钳 z、`vz=0`、`on_ground=true`
- `src\world\collision.c`：地面判定用**包含式**比较（`end_z <= ground`），修复"出生点正好在地面上→首帧穿地"的边界 bug
- `CMakeLists.txt`：`collision.c` 加入主目标、`test_player`、`test_session`

## 4. 测试结果

```
test_collision.exe   all checks passed          (落地 / 空地 / 阻挡 / 点实体 / 29 盒)
test_player.exe      ALL PASSED (0)             (出生点 -116、落地、四向移动、斜向归一、开镜)
其余 16 个 test_*    exit=0
test_usercmd.exe     600 cases, 0 mismatch      (需在 tools\ 下运行读 cases.txt)
test_gs_vector.exe   len=263                    (需在 tests\fixtures\ 下运行)
```

## 5. 未完成 / 已知局限

1. **clipMap 精确解析未闭合**：`cLeaf_t` / `cLeafBrushNode_t` / `aabbTrees` / `cmodels` / `brushes` 的数组边界还没定位。zone 里这些数组的落盘顺序与 `clipMap_t` 字段序不同（ZoneBuilder 按 `SaveLogEnter` 顺序写：planes → staticModels → materials → brushsides → brushEdges → nodes → leafs → leafBrushes → leafBrushNodes → borders → partitions → aabbTrees → cmodels → brushes → brushBounds → smodelNodes）。
2. **碰撞是轴对齐近似**：29 个 clip 盒统一按 64×64×64、以实体 origin 为中心。实际 brush 尺寸未取到（实体串不含 size）。**地形/楼梯/斜坡没有碰撞**，只有平地 + 方形障碍。
3. **`codol_static_boxes` 会挡住 spawn 附近移动**：出生点 (48,-572,-116) 距最近 clip 盒 (-75,-434) 约 180 单位，暂不冲突；但若后续加入真实 brush 尺寸需重算。
4. **未实机验证**：按上一轮"没修完不要起"的约定，本轮没启动客户端。

## 6. 下一步（按优先级）

1. 把 `clipMap_t` 各数组边界闭合：以 `0x23F564` 的 7 组目录为起点，用"每个数组的元素尺寸 × count = 下一段偏移"做链式约束求解；`cLeaf_t=40B`、`cLeafBrushNode_t=20B`、`CollisionAabbTree=32B`、`cmodel_t=68B`、`cbrush_t=36B`。
2. 拿到真实 brush 后，用 `cbrush_t.sides → cbrushside_t.plane → cplane_s` 三元组做 `CM_BoxTrace` 的精确面测试，替换 AABB 近似。
3. 之后再处理小地图（common_mp.ff）、武器/外观（usercmd.weapon 恒 0 的替代来源）。

## 7. 受保护文件校验（AGENTS.md）

`REF_LOBBY_KIT\_golden_hashes.json` 9 项：**8 项 OK，1 项既有漂移**
`marketplace_store.py`（实际 50022 B / `E44358F0...`，期望 46226 B / `28B4A1BE...`，mtime 2026-10-16）。
本轮**未读写** `REF_LOBBY_KIT` 与 `CODOL_VERIFIED_GOLDEN_20261019` 任何文件。

---

# 2026-10-22 实机排查断点（clipmap/collision + 快照 + 装备）

## 0. 一句话状态

**服务端已对齐权威快照实现（124B playerstate + clientInfo 段），但客户端仍不采纳：出生卡房顶、背包固定、开火只扣弹、小地图空。**
根因已定位为 **服务端与客户端状态机互相覆写**，非单字段错误。**未修复。**

## 1. 本轮确认的硬事实（全部有日志/字节证据）

### 1.1 `omit_motion` 是唯一有实证支撑的开关

| 轮次 | omit | z 轨迹 | 判定 |
|---|---|---|---|
| `C_SERVER_FIRST3_20261021` | **1** | **-78 ~ -116 起伏（69 个不同值）** | ✅ 客户端自己跑物理 |
| 后续所有轮 | 0 | 恒定 -116 / -127 / -56 | ❌ 客户端直接采用服务端值 |

**注入前 `firingrange-gamestate.bin` 的 z 从未变化（35326 帧全 -116）。**

### 1.2 usercmd 解析器是正确的

- `test_usercmd` 600 自生成用例：0 失配
- **`real_cases.txt`（15 条真实客户端 body）：0 失配**
- 说明 `buttons` / `weapon` 解析无误

### 1.3 真实 usercmd 的按钮分布（本轮 FINAL 轮）

```
btn=0x20000800  18 次   bits=[11,29]   ← ADS + 未知位 29
btn=0x00000000   4 次
btn=0x10000000   1 次   bit28
```
**没有一帧含 bit0（开火）**。而标定轮（KEYMAP_CAL）中：
```
0x2002      bits=[1,13]        ← W+Shift（bit1=SPRINT ✓）
0x200       bits=[9]           ← 单独 Shift
0x20102801  bits=[0,11,13,20,29] ← 鼠标左键（bit0=ATTACK ✓）
```
**结论：按键位定义正确，但客户端在进图后停止上报真实按键（卡在残留值）。**

### 1.4 客户端显示的武器是 1159，不是我们发的 1156

- gamestate 的 `configstring[765] = "1159"`（`firingrange-gamestate.bin` @0x d0）
- `CODOL-DEMONWARE-EVIDENCE-BUNDLE` 与 `living-player-weapons-20260926.md` 均记录 **1159 = M4A1 Tech 典藏版**
- 我们快照 index 39 发 1156 → **客户端忽略**
- 用户确认：显示为 **"M4A1 Tech 典藏版，裸枪，只有一把"**

### 1.5 小地图依赖 `northyaw` / `compass_map_*`

反汇编 `image_t004.76s_100.bin` @`0x4EC170`：
```asm
push 0xdb9754        ; "northyaw"
push 0x32ad060       ; configstring base
call 0x4e88d0        ; Info_GetConfigValue
```
后续写 `[0x32af42c]`（sin/cos）与 `[0x32a73c4]`。
**主 configstring 里没有 `northyaw` → 小地图空。**

### 1.6 clientInfo 字段 0 = 11bit 武器子实体引用（已在本客户端二进制验证）

```
netfield 表 @0x00DA8078: {offset=0x140, width=11}
@0x0054BD7A: mov ecx,[ebx+0x140]; mov [edi+0x398],ecx
```
与 ol-mod `sv_snapshot_mp.cpp` 的 `ClientInfoLivingWeaponField = 0` 完全一致。
**已加入 `snapshot.c`，值恒 0（无 ET6 实体）。**

## 2. 本轮代码改动（全部编译通过）

| 文件 | 改动 | 状态 |
|---|---|---|
| `src/battle/snapshot.c` | 对齐 `CodolMotionSnapshot.cs`：124B；删多余 62/83/107/162；`groundEntityNum` 恒 2047；`ViewHeight` 60 直写；尾部补 clientInfo 段（127B） | 已编译，实机无效 |
| `src/battle/battle_service.c` | `omit_motion` 恢复为 `true`（镜像未命中时） | **未实机验证** |
| `src/battle/equipment.c` | 槽位武器 ID 恒定写自己；`usercmd.weapon` 只接受 1..2047 且命中已知槽位 | 已编译 |
| `src/world/usercmd.c` | 可靠命令文本带出到 `list->reliable[]` | 已编译 |
| `src/world/collision.c` | 新增：29 个 clip 盒 + 地面 z=-116，AABB sweep | 已编译，单测通过 |
| `src/world/player.c` | 真实重力 + 逐轴 sweep；新增 SPRINT(0x2) | 已编译 |

## 3. 测试状态

```
test_snapshot            127 bytes
test_snapshot_delta      ALL PASSED
test_player              ALL PASSED
test_equipment           ALL PASSED
test_collision           ALL PASSED
test_backpack_reliable   ALL PASSED
test_regression_20261022 ALL PASSED
test_usercmd             600 cases 0 mismatch（在 tools/ 下）
test_usercmd real_cases  15 cases 0 mismatch
```

## 4. 硬阻塞（不可绕过）

**ACE-BASE.sys / ACE-GAME.sys 内核驱动**拦截 `ReadProcessMemory`（err=5），
即使持有 `SeDebugPrivilege` 且 `OpenProcess` 成功。

**唯一可行读取方式（已验证）**：`CreateProcess(CREATE_SUSPENDED)` → `OpenProcess` → `ResumeThread`。
脚本：`CODOLServer\_mainline\_dyn100_mem.py`
本轮成功产物：`run_codol_001\runs\SUSPEND_DUMP_20261022\image_best.bin`
（10.39 MB，`nonzero=9354813`，`fails=0`）

**注意**：该脚本不启动 Auth/Lobby，客户端会卡在连接失败，但**解壳代码已在 t≈4.7s 完成**（该时刻 nonzero 从 6.4M 跳到 9.35M）。

## 5. 逆向进展与缺口

**已解出**（来自 `CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\_data\disasm_key2697.txt`，
该文件是 **2.6.9.7 服务端** `codol_dedrun.exe` 的反汇编，**不是 3.19 客户端**）：

```
_CODOL2697_WriteConfigstrings(msg, ctx, cstr, count, cmp, cmpCount):
    WriteByte(4)
    WriteShort(count)                 // ≤ 0x1DD7
    repeat: index_bits(index) + WriteString(value)
    WriteBits(cmpCount, 11)           // ≤ 0x7FF
    repeat: index_bits(index) + WriteBits(value, 10)
    WriteBits(?, 10)
    WriteBits(?, 4)
```

**缺口**：`index_bits()` 的位编码规则（递增索引如何压缩）。
`0x4A0400` 在**客户端**镜像里不是该函数（是 `std::vector::push_back`），
**地址来自 2.6.9.7 服务端，不能直接套用**。

## 6. 下一步（按性价比排序）

1. **实机验证 `omit=1`**（唯一有历史证据的改动）——只看出生点/移动
2. 若 omit=1 有效，再解决背包：需要 gamestate 的 `configstring[765]` 与快照 index39 一致（都用 1159 或都用 1156）
3. 小地图：主 configstring 加 `\northyaw\0`；`compass_map_*` 需真实地图边界
4. `index_bits` 逆向：低优先级，收益不确定

## 7. 受保护文件

`REF_LOBBY_KIT\_golden_hashes.json` 9 项：8 OK，1 既有漂移（`marketplace_store.py` 50022B vs 46226B，mtime 2026-10-16）。
本轮未读写 `REF_LOBBY_KIT` / `CODOL_VERIFIED_GOLDEN_20261019`。


---

## 12. 0x32AD060 曾被成功解析，后被清空

### 12.1 表头与残留

实测 dump：valid=0, count=0, textLen=0。

但 names[]/values[] 里还留着 12 组上次解析成功的指针：

- targetname = lobby_player_pos
- classname = script_origin
- angles = 0 180 0
- origin = -5054 -9 -47
- model = cha_quartermaster
- script_noteworthy = lobby_stand_05

这是大厅出生点实体（cha_quartermaster 军需官模型），说明 0x32AD060 被 0x4E8660 成功解析过至少一次。

### 12.2 为什么现在是空的

0x4E8660 入口三条指令无条件执行：

0x4E867D  mov byte [edi],0        ; valid=0
0x4E8680  mov [edi+4],0           ; count=0
0x4E8683  mov [edi+0x208],0       ; textLen=0

任何一次失败的 parse 都会把上一次的成功结果抹掉（指针数组不清，只清头）。

### 12.3 结论

1. 这张表在大厅阶段被正确填充（lobby_player_pos 实体）。
2. 进图时 0x4EC500 又调了一次 0x4E8660，喂的是 CS[0]。
3. 我们的 CS[0] 以 0x5C 开头，不是 0x7B，parse 失败。
4. 失败路径把 valid/count/textLen 清零，表变空，northyaw 取不到，小地图不初始化。

即：不是表从来没填过，而是被我们的错误 CS[0] 覆盖掉了。
---

## 13. listen server 硬件类型枚举的判定（本轮结论）

### 13.1 枚举本身反推不出服务器

`0x478100` 只有 6 条字符串注册：

```
0xDC5C68  server_hardware_...
0xDC5C80  server_hardware_linux_dedicated
0xDC5CA0  server_hardware_win_dedicated
0xDC5CC0  server_hardware_mac_dedicated
0xDC5CE0  server_hardware_win_listen
0xDC5CFC  server_hardware_mac_listen
```

调用形态是 `push 3 / push <str> / call 0xBD9C00`，即本地化字符串注册，
结果写入 6 个 UI 全局：`0x762EFB8 / BC / C0 / C4 / CC / D0`。

这段代码没有端口、没有包结构、没有握手、没有超时，只是服务器浏览器里 server_hardware 栏的显示文案。

结论：反推不出服务器实现。

### 13.2 但它给出了一个关键协议事实

这 6 个 token 是服务器自己上报的字段取值（IW4 serverinfo 里的 server_hardware）。
客户端承认 dedicated 与 listen 两类，并带 linux / mac 分支，
说明这部分是 IW4 原版引擎代码，不是 CODOL 自研。

由此可定：客户端的服务器发现与连接层是 IW4 原版 netchan，IW4X / CoD4x 的服务端源码即权威参照。

### 13.3 本地客户端真正与对局服务器通信的三处

**1) 游戏自己的 UDP socket，全 exe 唯一**

```
0x77FC11  call [0xCA8548]   socket(AF_INET, SOCK_DGRAM, 0)
0x77FC3F  call [0xCA854C]   ioctlsocket(FIONBIO)
0x77FC8F  call [0xCA8554]   bind(s, {port, 0.0.0.0}, 14)
```

不用 connect()（UDP 走 sendto），所以 connect hook 里看不到它。这解释了此前 hook 到的全是 BugTrace / iips / libcef 的 TCP。

**2) 出站命令队列 0x5C0F50**

```
0x5C0F71  mov esi, [0x331C0C8]
0x5C0F77  xor esi, 0xD362501F       CL 对象（异或解引用）
0x5C0F7F  mov eax, [esi+0x140]      写索引
0x5C0F8E  cmp eax, 0x200            512 条上限
0x5C0FB0  and eax, 0x1FF
0x5C0FB5  shl eax, 0xA              x 0x400
0x5C0FB8  lea edi, [eax+esi+0x148]  命令槽
0x5C0FC1  call 0x675840             写入
```

dump 中 CL 基址 = `0x1C830E14`。
队列布局：`+0x140` 写索引，`+0x144` 读索引，`+0x148` 起 512 x 0x400 字节命令槽。

**3) 入站分发器 0x5C0FD0**，用 `0x7745E0`（strcmp）比对：

```
0xDBFF40  disconnect_ack
0xDBFF50  （第二条，未读全）
0xDBCE80  EXE_SERVER_DISCONNECTED
```

### 13.4 与现有 OOB 命令集对齐

`battle_service.c` 已处理：`stats / getchallenge / connect / heartbeat / gamestateupdate`。
这正是 IW4/CoD4x OOB 的全集。
加上 server_hardware 枚举，可判定：客户端的对局协议 = IW4 原版 netchan，无 CODOL 私有改动。

### 13.5 下一步（待确认）

在 `0x5C0F50` 下断，抓客户端发往 28960 的真实命令序列。
这是唯一能一次拿到客户端意图的入口，优先于继续读字符串枚举。
