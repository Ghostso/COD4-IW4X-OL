# CODOL 客户端网络协议分析笔记

分析对象：`codoMP_client_shipRetailBase.dll`（60 MB，IW4 谱系，`iw4\game\pc\`）。
本文只记录**可验证的事实**与**已排除的错误结论**，不含任何绕过/会话伪造实现。

---

## 1. PE 结构（已修正）

早期解析失败的原因：`SizeOfOptionalHeader` 读错偏移。
它位于 `PE + 0x14`（20），而非 `PE + 0x0E`（14，那里是 `NumberOfSections`）。
这一处错位导致整个节表错位，并连带产生了一批**错误结论**（见 §5）。

```
PE 偏移           0x00000110        （签名 "PE\0\0"）
Machine           0x014c  (x86)
NumberOfSections  8
SizeOfOptionalHeader 0x00e0
Optional magic    0x010b  (PE32)
ImageBase         0x10000000
SectionAlignment  0x1000
FileAlignment     0x200
AddressOfEntryPoint 0x0000149c
SizeOfImage       0x03991000
```

### 节表（节表起始 `0x00000208`，每项 40 字节）

| # | 名称 | VA | VirtualSize | RawOffset | RawSize | Flags |
|---|------|-----|------|------|------|------|
| 0 | `.text` | `0x00001000` | `0x742000` | `0x00000400` | `0x741c00` | `0x60000020` |
| 1 | `.rdata` | `0x00743000` | `0x26c000` | `0x00742000` | `0x26b200` | `0x40000040` |
| 2 | `.data` | `0x009af000` | `0x153000` | `0x009ad200` | `0x14aa00` | `0xc0000040` |
| 3 | `.idata2` | `0x00b02000` | `0x004eba` | `0x00af7c00` | `0x005000` | `0xc0000020` |
| 4 | `.rsrc2` | `0x00b07000` | `0x002b9c` | `0x00afcc00` | `0x002c00` | `0xc0000020` |
| 5 | `.tls` | `0x00b0a000` | `0xed3000` | `0x00aff800` | `0xed2600` | `0x60000020` |
| 6 | `.tvm0` | `0x019dd000` | `0x1f5e000` | `0x019d1e00` | `0x1f5d600` | `0x60000020` |
| 7 | `.reloc` | `0x0393b000` | `0x056000` | `0x0392f400` | `0x055e00` | `0x42000040` |

节名非标准（`.idata2` / `.rsrc2` 对应常规的 `.idata` / `.rsrc`），是腾讯加固后的产物。
`.tvm0` 即腾讯 TVM 虚拟机保护段（约 31 MB），本体代码被它吞掉。

### 数据目录

| 目录 | RVA | Size | 说明 |
|------|-----|------|------|
| Export | `0x00952d60` | `0x41` | 3 个函数，**0 个具名导出**（匿名导出，配合加固） |
| Import | `0x009f67b8` | `0x3c` | **仅 2 个 DLL**：`kernel32.dll`、`libcef.dll` |
| Resource | `0x00b07000` | `0x2b9c` | |
| Certificate | `0x03985248` | `0x35f0` | |
| BaseReloc | `0x0393b000` | `0x055d4c` | |
| Debug | `0x00746060` | `0x1c` | |
| IAT | `0x00b02000` | `0x000c00` | |

**导入表只有两个 DLL。** `WS2_32.dll` 不在其中——所有网络 API 均为运行时动态解析（见 §2）。

---

## 2. 导入表其实在，只是被搬到了 `.idata2`

PE 头里的 Import 目录（`0x009f67b8`，落在 `.data`）只列 `kernel32.dll` + `libcef.dll`，是**幌子**。
真正的导入表在 `.idata2`，而且**PE 的 IAT 数据目录已被改写为指向它**：

| 项 | 值 |
|---|---|
| IAT 数据目录 | RVA `0x00b02000`，大小 `0x000c00` |
| DLL 数 | 21（与 NULL 分块的槽块数 21 一一对应） |
| 槽总数 | 748 |
| 实际被 `call` 的槽 | 512；`call dword ptr [abs]` 调用点合计 2286 |

DLL 顺序（即槽块顺序）：

```
0 ADVAPI32 1 CRYPT32 2 GDI32 3 IPHLPAPI 4 KERNEL32 5 NETAPI32 6 OLEAUT32
7 PSAPI 8 SETUPAPI 9 SHELL32 10 SHLWAPI 11 USER32 12 VERSION 13 WINMM
14 WINTRUST 15 WLDAP32 16 WS2_32 17 WSOCK32 18 gdiplus 19 ntdll 20 ole32
```

解析器见 [scripts/importmap.py](../scripts/importmap.py)（槽值指向 `[u16 hint][asciz name]`，名字在 `slot_value+2`；序数条目为 `0x80000000|ord`）。

**这 21 个 DLL 全是 CRT / libcurl / OpenSSL 的依赖，没有一个游戏专有组件**（没有 IIPS、TNSDK、反作弊 DLL）。
即：**这张 IAT 属于静态链入的第三方库，不属于游戏网络层。**

### 曾被误判为「运行时解析」的三条证据，全部推翻

1. **`.rdata VA 0x0094f000–0x00953000` 被当作「DLL 名 → 函数名」字符串池。**
   实际 `0x94f000` 一带是**二进制表**（不是字符串）；字符串部分从 `0x951200` 左右才开始，且是 `[u16 hint][asciz name]` 形式的**导入名 blob**——
   `meGetTime` / `WINMM.dll`，然后 `WS2_32.dll` 跟 `WSCEnumProtocols, freeaddrinfo, getnameinfo, getaddrinfo, WSAIoctl`，再 `WLDAP32.dll`……
   这是**延迟加载 / libcurl 的 winsock 动态加载**用表，不是游戏的自建解析器。

2. **`VA 0x0075b890–0x0075b940` 被当作「8 字节步进的紧凑名字数组」。**
   实际是**纯拼接的 NUL 结尾 ASCII 串**：
   `fflush / gethostbyname / getsockname / getsockopt / setsockopt / getnameinfo / getaddrinfo / fread / opendir / WSAStartup / accept / listen / bind / ioctlsocket / socket / getservbyname / connect / fopen`
   「8 字节步进」是把指针表读法硬套到字符串上产生的假象。
   这些串在 `.text` 里**零引用**；唯一引用来自 `.data 0x9b3bdc` 一带的 `{error_code, "name"}` 表——那是 **OpenSSL/CRT 的错误字符串注册表**：
   同表里还有 `"BN lib"`(3) / `"RSA lib"`(4) / `"DH lib"`(5) / `"X509 lib"`(11) 等 `ERR_LIB_*` 编号，
   而紧邻的 `0x9b6000` 块正是 OpenSSL 的 `SYS_str_reasons`（`0x2000007a` = `ERR_PACK(2,0,122)` → `"WSAStartup"`）。
   注意表中写作 `"WSAstartup"`（小写 s），且混着 `"fflush"`、`"opendir"` —— 这些是**错误名标签，不是导入名**。

3. **`LoadLibraryA("WS2_32.DLL")` + `GetProcAddress` 解析器确实存在，但属于 libcurl。**
   位于 `0x430b82`，伴生字符串 `failed to load WS2_32.DLL (%u)`、`WSACreateEvent`、`FreeLibrary(wsock2) failed`。

**修正后的定位方法：** 收发点**可以**直接按 IAT 交叉引用定位（不必再找 `GetProcAddress` 调用点）；
但要注意下面这点——

### 2b. IAT 可见的网络调用点：40 个簇里 38 个是第三方库

把全部 250 个 `ws2_32`/`wsock32` 调用点按间隔 > 0x800 聚成 **40 簇**，用每簇自身的字符串引用做指纹：

| 簇 | 点数 | 归属指纹 |
|---|---|---|
| `0x41eed1–0x426000` | 13+2+27 | **libcurl** 传输核心（multipart/Content-Type、cookie `__Secure-`、`iphlpapi.dll`） |
| `0x428609` / `0x42c9df–0x42dbef` / `0x42f48a` / `0x430042` / `0x430c9e–0x431a4b` / `0x432e27` | 17+4+4+16+1 | **libcurl** POP3/IMAP/TFTP/FTP/DICT/TELNET（`APOP`、`UID FETCH`、`tftp_tx`、`bind() failed`） |
| `0x4438e8`…`0x451b0a` | 17 | **libcurl**（`_netrc`、pkcs11、SASL、NTLM `KGS!@#$%`） |
| `0x64128f`…`0x686c1c` | 109 | **libcurl vtls + OpenSSL**（`..\..\..\..\lib\vtls\openssl.c`、DoH `%s?dns=%s`、SOCKS4、`s3_clnt.c`） |
| `0x2b37a9–0x2b3e3e` / `0x2d9489–0x2d987c` | 10 + 14 | **OpenSSL**（`pk7_doit.c`、`v3_utl.c`） |
| `0x51c8aa–0x51cbf3` | 8 | **libtiff**（`LZWDecode`、`Not enough data at scanline`）—— 第四个静态库，早期未注意到 |
| `0x61603d–0x61606c` | 2 | **腾讯反作弊**（`NtQuerySystemInformation`、`M64Ver102`、`GameGroupId`） |
| **`0x235cc0–0x236100`** | **~10** | **非第三方库**（见下） |
| `0x23112e` / `0x235d4f` 旁串 | — | MSVC STL（`invalid map/set<T> iterator`、`vector<T> too long`）——只是 `.rdata` 邻居，**不是**该簇的指纹 |

**唯一像本体的簇：`0x235cd0`。** 它调用 `WSASocketW` / `WSAEventSelect` / `WSACreateEvent` / `WSAWaitForMultipleEvents` / `WSAEnumProtocolsW`
（libcurl 一律用 `select()`，从不用 `WSAEventSelect`），辅以 `GetTickCount` / `GetCurrentProcessId` / `GetLocalTime`+`SystemTimeToFileTime`，
建 `WSASocketW(AF_INET=2, SOCK_RAW=3, IPPROTO_ICMP=1, NULL, 0, 0)` 原始套接字，再 `malloc(0x30)`+`memset(0,0x30)` 建对象。
形态是 **C++ 类构造**（`[esi]=socket句柄`、`[esi+4]/[esi+8]` 事件、`[esi+0xc]` 0x30 字节缓冲、`[esi+0x10]` 就绪标志、`[esi+0x14]` tick、`[esi+0x18..0x1c]` 64 位 FileTime）。
它**区间内零字符串引用、VA 零 dword 引用**（间接调用），因此无法用字符串判定身份——但原始 ICMP 套接字的形态更像**连通性/延迟探测**，不是游戏 netchan。

### 2c. 一条**看起来完全合理、实际错误**的映射：序数槽的 DLL 前缀

`importmap.build()` 把 DLL 名配给槽块靠的是**块顺序**。对「具名条目」没问题（名字串就写在槽值里，
自证）；但对**全序数的块**，名字区里没有该 DLL 的字符串可校验，块序号错开一格就会整体张冠李戴，
而序数本身仍会被"成功"解析成 `ORD#n`——于是产出一张**自洽但错误**的 API 表。

实际翻车的一例（早前记录里的「COMPLETE ordinal-slot call-site map」）：

| 槽 | 早前判为 | 实为 | 判定依据 |
|---|---|---|---|
| `0xb027f4` | WS2_32 `ORD#12 ioctlsocket` | **OLEAUT32 `VariantChangeType`** | 调用点 `0x238899` 压 4 个参数，含 `VARTYPE=9`(VT_DISPATCH)，返回 HRESULT 用 `jl` 判失败 |
| `0xb027f8` | WS2_32 `ORD#9 htons` | **OLEAUT32 `VariantClear`** | 调用点 `0x236f01`/`0x238855`/`0x238952` 均为 `push ecx; call [slot]; ret` 单参裸 thunk |
| `0xb027fc` | WS2_32 `ORD#8 htonl` | **OLEAUT32 `VariantInit`** | 调用点 `0x2386be` 单参，后接 `_variant_t` 构造 |

佐证链：该段紧接着走 `mov edx,[eax]; mov edx,[edx]; call edx` 的 **IDispatch vtable 调用**；
失败路径上调用**具名**槽 `0x10b02bf4 = ole32.dll!CoUninitialize`。
`VariantInit`/`VariantClear`/`VariantChangeType` 正是 `_variant_t` 的三个支撑函数。
块 6 只有 3 个槽且全是序数，与「只导入这三个」吻合。

**结论：`0x231xxx–0x238xxx` 这一带是 MSVC STL + OLE Automation 胶水代码，不是网络组件。**
早前「htons/htonl/ioctlsocket 的调用点在这里，端口应该就在这里构造」的线索
（曾列为第五目标的突破口）**作废**——那里没有 socket。

真正的 WS2_32 序数槽在 `0xb02a40–0xb02b60`（块 16），其中 `0xb02ab0=ORD#9 htons`、
`0xb02acc=ORD#8 htonl`。块 16 的身份由**具名条目**自证：`WSASocketW`、`WSAEventSelect`、
`WSACreateEvent`、`WSAWaitForMultipleEvents`、`WSAEnumProtocolsW`、`getaddrinfo`… —— HIGH。
块 16 内 72 槽中 56 个是序数，且**每个序数出现两次**（同一描述符的 ILT/IAT 两份），
说明「748 槽 / 250 网络调用点」这类计数**存在重复计数**，仅供量级参考。

块 6 / 15 / 17 是**全序数块**（前缀不可信），`build()` 现已对这类块加 `?` 标记。

---

## 3. 加固 / 反作弊组件（旁证）

字符串池中同时出现一整组**进程内存操作 API**，它们属于保护层自身而非游戏逻辑：

```
NtReadVirtualMemory   NtWriteVirtualMemory   NtProtectVirtualMemory   NtUnmapViewOfSection
ReadProcessMemory     WriteProcessMemory     VirtualProtectEx
LdrLoadDll            LdrLockLoaderLock      AddVectoredExceptionHandler
CreateToolhelp32Snapshot  Process32First/Next(W)  IsDebuggerPresent
```

配套 DLL 名：`TP3DrvDll.dll`、`P3Shell.dll`、`tersafe.dll`、`ace-ats32.dll`、`EMET_CE.dll`、`TenProxy.dll`、`ProtocalHandler.dll`。

`codoMP_client_shipRetail.exe` 另被 TP3 加壳（6 × `.tp3` + 1 × `.tvm0`）。
**这直接决定了离线化的门槛**：客户端跑起来的前提是保护层认为环境合法（见 §4）。

---

## 4. 真正的启动门禁：TCLS

`codoMP_client_shipRetailBase.dll` 硬编码读取以下命名内核对象：

| 对象名 | VA |
|--------|-----|
| `TCLS_SHAREDMEMEMORY` | `0x0088effc` |
| `TCLS_TASMEMORY_` | `0x0088f15c` |
| `TAS-3AAC03A5-7D57-4c80-A175-0E4BEA43EE41-%u` | |
| `PT-81634493-9d70-46be-8157-9e032cc0fd86-%u` | |
| `Global\TenP_TS_%d` | |
| `TP3GameGuardShareMapping` | |

读不到 → 弹 `localization.txt` 的 `WIN_NO_TCLS`（GBK）：
「请使用腾讯游戏登录器(TCLS文件夹内的Client.exe)启动游戏。」

写入方是 `TCLS/ClientBase.dll`（12.7 MB），凭据经命令行 `-q:` / `uid=` / `key=` / `ID=` 传入。
`TCLS/Client.exe`（955 KB）本身**零网络导入**，职责仅是 `CreateProcess` 起 `WeGameLauncher/launcher.exe`。

**即：门禁在客户端本地，不在服务端协议。** 即便协议完全还原，这道检查仍会拦在更前面。

---

## 5. 已排除的错误结论（重要）

以下结论出自节表错位期间的解析，**全部作废**，勿再沿用：

| 错误结论 | 实际情况 |
|----------|----------|
| `0x9abb18` 是「含 84 个函数名的 .text 函数表」 | `0x9abb18` 落在 **`.data`**；内容是成对 dword（`0xFFFFFFFE` / `0xFFFFFFD0` / `0x1071E34E` 之类），**不是名字表**。当时读到的「名字」是节表错位的产物。 |
| `.rdata` 中的 `socket`/`connect`/`send`/`recv` 是网络函数**入口点** | 它们是**字符串常量**。 |
| `0x6B263C` 处 `127.0.0.1` 是客户端回环端点 | 位于 **libcurl 的 URL 解析表**（`pop3./smtp./imap./ldap./dict./ftp./127.0.0.1//localhost/` + `%s://%s…`）。libcurl 被静态链入。 |
| IP 列表 `111.13.35.103`、`183.192.199.244` … | 属 `down.qq.com` 补丁 CDN 故障转移，与游戏协议无关。 |
| 「网络栈走 `LoadLibraryA`+`GetProcAddress` 动态绑定，**无静态 IAT 可交叉引用**」 | **IAT 存在**，在 `.idata2`（21 DLL / 748 槽 / 2286 调用点）。那套 `LoadLibraryA`+`GetProcAddress` 是 **libcurl** 的 winsock 动态加载（`0x430b82`）。 |
| 「`0x75b890–0x75b940` 是 8 字节步进的紧凑名字数组」 | 是**拼接的 NUL 结尾字符串**，「8 字节步进」为读法假象。`.text` 里零引用；唯一引用是 `.data` 的 **OpenSSL/CRT 错误串注册表**。 |
| 「`0x94f000–0x953000` 是 DLL名→函数名 字符串池」 | `0x94f000` 一带是**二进制表**；字符串部分（约 `0x951200` 起）是 `[u16 hint][asciz name]` **导入名 blob**（延迟加载/libcurl）。 |
| 「`0x42c9df` 的 `sendto` 是游戏包组装 / `accept`@`0x43112f` 是游戏内建监听服务器」 | 均为 **libcurl**：前者是 POP3/IMAP/TFTP/FTP 处理器，后者是 FTP active-mode/sockfilt 辅助。 |
| 「块 15 = `WLDAP32.dll` 说明游戏有 LDAP 组件」 | 是 **libcurl 的 LDAP 后端**（`LDAP local: bind via ldap_win_bind %s`）。 |
| 「`0x231xxx–0x236xxx` 是 STL/游戏代码簇（依邻近字符串 `invalid map/set<T> iterator` 判定）」 | 那些 STL 串只是 `.rdata` **邻居**，不是该簇的指纹。该簇实为 `0x235cd0` 的 `WSASocketW`+`WSAEventSelect`+`WSAEnumProtocolsW` 组件，**与 MSVC STL 无关**。 |

### 端口字符串

`8000` 出现在 `VA 0x00978aad / 0x00978db8 / 0x00979298 / 0x00979ac0`；`443` 出现在 `0x00826e02 / 0x00979365 / 0x00979bf0 / 0x0097a89f`。
这些落在配置/JSON 块中，**尚不能断定即游戏协议端口**——早期「IIPS=8000，游戏=8801」的划分来自 `IIPSHostApp.ini` 的 `udp://ctrl.iips.qq.com:8000`，那是 IIPS 补丁通道，与游戏协议是两套东西。

---

## 6. 待办 / 未决

1. ~~定位 `GetProcAddress` 调用点~~ —— **已否**：IAT 可直接交叉引用（见 §2）。
   新的问题变成：**游戏的 netcode 根本不走这张 IAT**。21 个 DLL 全是 CRT/libcurl/OpenSSL，
   40 个网络调用簇里 38 个是 libcurl/OpenSSL/libtiff/反作弊，另一个（`0x235cd0`）是原始 ICMP 探测。
   与「本体代码被 `.tvm0` 吞掉」及「玩法流量走腾讯 TNSDK/IIPS 传送层」的判断一致。
2. 确认消息 524 / 615 的归属（早期在 MD5 数据区和椭圆曲线数据区命中 `"524"` / `"615"`，疑为**假阳性**，需在代码段内按 opcode 重新验证）。
3. 厘清 `.ifs`（974 个，23 GB）在运行时的挂载路径：由 `IIPS/IFS2.dll` + `IIPSVFS.dll` 挂载，**游戏本身未必需要解包**。
4. 协议端口仍未确证。

---

## 附：工具脚本

`scripts/parse_func_table.py` 使用了错位的解析逻辑，其输出不可信。
正确的最小验证片段见本文 §1（节表起始 `0x208`，`<8sIIIIIIHHI` 格式，40 字节/项）。
