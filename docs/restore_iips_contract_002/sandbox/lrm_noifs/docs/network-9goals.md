# 网络层九目标 —— 12 节答复

对象：`codoMP_client_shipRetailBase.dll`（60 MB，IW4 谱系）。
结论一律标注 **HIGH / MEDIUM / LOW**；无证据处标 **UNKNOWN**，不填空、不推断填充。
端口相关结论遵守既定约束：**不从字符串池反推端口，必须从实际运行时参数确认**；
**不假设函数名一定以明文形式出现**；**不因端口"看起来像"就认定**。

> 总纲：本次分析推翻了此前支撑整个分析框架的一个前提。
> 该 DLL 的 IAT 确实存在（在 `.idata2`），但**它是静态链入的第三方库的 IAT，不是游戏网络层的 IAT**。
> 因此下面九问中，凡涉及「游戏的 socket / connect / send / recv / 端口」的部分，
> 诚实答案是 **UNKNOWN**，而不是某个看起来合理的猜测。

---

## 1. 【WS2_32 加载点】

| 结论 | 置信度 |
|---|---|
| PE 头 Import 目录（`0x009f67b8`，落在 `.data`）只列 `kernel32.dll` + `libcef.dll` | HIGH |
| `WS2_32.dll` **不在这张表里** | HIGH |
| 真导入表在 `.idata2`，IAT 数据目录被改写为指向它（RVA `0xb02000`，size `0xc00`） | HIGH |
| 该表被 **21 个 DNS/槽块** 描述，其中含 `WS2_32.dll`、`WSOCK32.dll` | HIGH |

**关键新证据（决定第 1 节性质的）：** 那张幌子导入表的描述符 `FirstThunk` 指向
`0x009f6800`(kernel32) / `0x009f6841`(libcef)，**落在 `.data`，不在 `.idata2`**。
即：**OS 加载器即便处理这张表，也只会往 `.data` 写 2 个 DLL 的指针，永远不会填 `.idata2` 的 748 个槽。**

同时，全 `.text` 对表基址 `0x10b02000` 只有 **1 处**引用（RVA `0x2f6fd9`），
反汇编为 `FF 15 00 20 B0 10` = `call dword ptr [0x10b02000]` —— 那是**对 0 号槽的普通调用**，
**不是**遍历表的重定位器。

**推论**：填 `.idata2` 的既不是 OS 加载器，也不是 `.text` 里的代码。
最可能是腾讯 TVM 保护壳的加载桩（入口 `0x149c` 或 `.tvm0` 段内）在做自建导入解析。
**置信度 MEDIUM**——因为 `.tvm0`（31 MB，占文件一半）未分析，此处是推理而非直读。

**`WS2_32` 块（块 16）身份**：由**具名条目自证**——`WSASocketW`、`WSAEventSelect`、
`WSACreateEvent`、`WSAWaitForMultipleEvents`、`WSAEnumProtocolsW`、`WSCEnumProtocols`、
`getaddrinfo`、`getnameinfo`、`freeaddrinfo`。**HIGH**（名字串就写在槽值里，不依赖块顺序）。

---

## 2. 【GetProcAddress 调用点】

| 结论 | 置信度 |
|---|---|
| 找到 **1 处** `LoadLibraryA("WS2_32.DLL")` + `GetProcAddress` winsock 动态解析器，位于 `0x430b82` | HIGH |
| 该解析器**属于 libcurl**（伴生串 `failed to load WS2_32.DLL (%u)`、`FreeLibrary(wsock2) failed`、`WSACreateEvent`） | HIGH |
| **未找到游戏本体的 winsock 运行时解析点** | MEDIUM |
| 但「没找到」≠「不存在」：`.rdata @0x88e900` 存在 TVM **加密字符串字母表**（`ABCDEFGHIJKLMNOPQRSTUVWXYZ` 紧跟 `tersafe.dll|DllEntry8`），明文关键词扫描会**系统性漏计** | HIGH |

第 3 条给 MEDIUM 而非 HIGH，正是因为第 4 条：在加固文件中，
「明文扫描未命中」不足以证明「不存在」。**这正是「不要假设函数名一定以明文形式出现」的具体后果。**

---

## 3. 【API → 函数指针映射】

映射重建器：`scripts/importmap.py`（`build()` 返回 `{槽RVA: 'dll!api'}`）。

| 结论 | 置信度 |
|---|---|
| 21 个 DLL / 748 槽（含重复计数，见下） | MEDIUM |
| **具名条目**的 `dll!api` 映射（名字在 `slot_value+2`，`[u16 hint][asciz name]` 形式） | HIGH |
| **序数条目**的 `dll!` 前缀（靠块顺序推断） | **不可信** |
| 序数块的「归属 DLL」若错一格会产出自洽但错误的表 | HIGH（已实证） |

**本次修正的一处实证错误：** 早前记录的「COMPLETE ordinal-slot call-site map」把
`0xb027f4` / `0xb027f8` / `0xb027fc` 判为 WS2_32 的 `ioctlsocket` / `htons` / `htonl`。
**错误。** 它们实为 **OLEAUT32 的 `VariantChangeType` / `VariantClear` / `VariantInit`**：

- `0x238899`：`push 9`(VARTYPE=9, VT_DISPATCH) `push 0` `push &dest` `push &src` → **4 个参数**，
  返回 HRESULT 用 `jl` 判失败，随后 `mov edx,[eax]; mov edx,[edx]; call edx` 走 **IDispatch vtable**。
  **`ioctlsocket` 只取 3 个参数，此调用不可能是它。**
- `0x236f01` / `0x238855` / `0x238952`：均为 `push ecx; call [slot]; ret` 之类的**单参裸 thunk**。
- 同函数失败路径调用**具名**槽 `0x10b02bf4 = ole32.dll!CoUninitialize`。
- `VariantInit`/`VariantClear`/`VariantChangeType` 恰是 `_variant_t` 的三个支撑函数；
  块 6 只有 3 个槽且全为序数，与「只导入这三个」吻合。

**根因**：`build()` 按块顺序配 DLL 名。具名条目可自证，**全序数块不行**——名字区里没有该 DLL
的字符串可校验，块序号错开一格就整体张冠李戴，而序数本身仍被"成功"解析成 `ORD#n`。
`build()` 现已对全序数块加 `?` 标记（`OLEAUT32.dll?!ORD#12`）。

**真正的 WS2_32 序数槽在块 16（`0xb02a40–0xb02b60`）**，例如：

```
0xb02ab0  ORD#9  htons        0xb02acc  ORD#8  htonl
0xb02a50  WSAIoctl            0xb02aa0  ORD#23 socket
0xb02aa4  ORD#2  bind         0xb02ac4  ORD#4  connect
```

块 16 共 72 槽中 56 个是序数，且**每个序数出现两次**（同一描述符的 ILT/IAT 两份拷贝）。
故「748 槽 / 250 个网络调用点 / 40 簇」这类计数**含重复计数**，只作量级参考。

---

## 4. 【socket 调用链】

| 结论 | 置信度 |
|---|---|
| `0x235cd0`：C++ 类构造，调用 `WSASocketW(AF_INET=2, SOCK_RAW=3, IPPROTO_ICMP=1, NULL, 0, 0)` | HIGH |
| 同函数 `WSACreateEvent` → `WSAEventSelect(sock, event, 1)` → `malloc(0x30)` + `memset(0, 0x30)` | HIGH |
| 对象布局：`[+0]`socket `[+4]`event `[+8]`pid `[+0xc]`0x30 缓冲 `[+0x10]`就绪标志 `[+0x14]`tick `[+0x18..0x1c]`FileTime | HIGH |
| 该函数**区间内零字符串引用、VA `0x10235cd0` 零 dword 引用**（间接调用），无法用字符串定身份 | HIGH |
| 其形态是**原始 ICMP 连通性/延迟探测**（或环境指纹采集），**不是游戏 netchan** | MEDIUM |

补充本次新读到的细节：它还做 `GetTickCount` + `GetLocalTime`→`SystemTimeToFileTime`，
再 `push 0 / push 0x2710` 调 `0x291880` 做 **64 位除以 10000**——即 **FILETIME(100ns) → 毫秒**，
是「开机以来毫秒数」；并且取 `GetCurrentProcessId`、准备一个 `0x101` 字节缓冲（疑似路径）。
结合原始 ICMP 套接字，更像**反作弊/环境侧信道**而非游戏网络层。

**其余 `socket()` 调用点**：全部落在 libcurl / OpenSSL / libtiff / 腾讯反作弊簇内（见 §9）。
**未发现游戏 netchan 的 socket 创建点。UNKNOWN。**

---

## 5. 【connect 调用链】

| 结论 | 置信度 |
|---|---|
| `connect` 出现在 IAT（`0xb02ac4 = ORD#4`）与 libcurl 簇中 | HIGH |
| libcurl 的 `connect` 调用链（含 `bind() failed`、SOCKS4、`getaddrinfo` 前置） | HIGH |
| **游戏本体的 `connect` 调用链** | **UNKNOWN** |

**没有任何一条从游戏逻辑出发、经 `sockaddr` 到达 `connect` 的链路被确证。**
早前设想的突破口（「`htons`/`htonl` 在 `0x236xxx` 构造端口」）**已作废**——那里是 OLE Automation（§3）。

---

## 6. 【send / recv 调用链】

| 结论 | 置信度 |
|---|---|
| `send`/`recv`/`sendto`/`recvfrom`/`WSASend`/`WSARecv` 调用点存在于 IAT | HIGH |
| 其中 `0x42c9df` 的 `sendto`、`0x43112f` 的 `accept` 属于 **libcurl**（POP3/IMAP/TFTP/FTP 处理器、FTP active-mode 辅助） | HIGH |
| **游戏本体的收发包链路** | **UNKNOWN** |

CEF（`libcef.dll` 为**导入**依赖，非静态链入）会自带自己的 HTTP/WS 收发，
其调用点在 `libcef.dll` 内，**不在本 DLL 的 `.text` 中**，因此按 IAT 交叉引用**看不见**。

---

## 7. 【实际目标地址 / 端口】

**UNKNOWN。没有任何一个游戏协议端口由实际运行时参数确证。**

必须明确记录与约束相关的边界：

- `8000` 出现在 `.rdata` `0x978aad / 0x978db8 / 0x979298 / 0x979ac0`；
  `443` 出现在 `0x826e02 / 0x937965 / 0x979bf0 / 0x97a89f`。
  **这些是字符串常量，按约束不得据此断定即游戏端口。** 它们落在配置/JSON 块中。
- 早前「IIPS=8000」的划分来自 `IIPSHostApp.ini` 的 `udp://ctrl.iips.qq.com:8000`——
  那是 **IIPS 补丁通道**，与游戏协议是两套东西。**MEDIUM**（配置文件为实，但不等于游戏端口）。
- 「游戏=8801」**无来源**，作废。
- `111.13.35.103` 等 IP 属 `down.qq.com` **补丁 CDN 故障转移**，与游戏协议无关。**HIGH**。
- `127.0.0.1` 位于 **libcurl 的 URL 解析表**（`pop3./smtp./imap./ldap./dict./ftp.` 邻居），
  不是客户端回环端点。**HIGH**。

**唯一一条已确证的 socket 目标参数**是 §4 的
`WSASocketW(2, 3, 1, ...)` = `AF_INET / SOCK_RAW / IPPROTO_ICMP`，**无端口、无地址**
（`connect` 不在同一函数内）。它**不能**回答第五目标。

---

## 8. 【TCP / UDP】

| 结论 | 置信度 |
|---|---|
| `0x235cd0` 建的是**原始 ICMP** 套接字（`SOCK_RAW` + `IPPROTO_ICMP`） | HIGH |
| libcurl 簇使用 TCP（HTTP/HTTPS/FTP/POP3/IMAP…） | HIGH |
| **游戏协议是 TCP 还是 UDP** | **UNKNOWN** |
| 「IW4 谱系用 UDP」是**先验常识**，不是本文件读出的证据，**不得作为结论** | — |

---

## 9. 【网络用途分类】

按簇指纹可确证的归属：

| 用途 | 载体 | 端侧归属 | 置信度 |
|---|---|---|---|
| HTTP/HTTPS、FTP、POP3、IMAP、TFTP、DICT、TELNET、SOCKS | 静态 **libcurl** | 本 DLL `.text` | HIGH |
| TLS/加密（含 DoH `%s?dns=%s`） | 静态 **OpenSSL 1.1.1** + libcurl vtls | 本 DLL `.text` | HIGH |
| 图像解码（`LZWDecode`） | 静态 **libtiff** | 本 DLL `.text` | HIGH |
| 补丁 CDN 故障转移 | `down.qq.com` | 配置数据 | HIGH |
| IIPS 补丁通道 | `udp://ctrl.iips.qq.com:8000`（`IIPSHostApp.ini`） | 配置文件 | MEDIUM |
| 环境侧信道 / 探测 | `0x235cd0`（原始 ICMP + pid + 开机毫秒） | 本 DLL `.text` | MEDIUM |
| 反作弊遥测 | TP3 / ACE / Tersafe（`tersafe.dll` 被 `.text` `push` 于 `0x5f753e`） | 本 DLL + 外部 DLL | MEDIUM |
| **登录 / 大厅 / 对战（GAME_PROTOCOL）** | **未定位** | **UNKNOWN** | **UNKNOWN** |

**重要负结论（HIGH）**：`.text` 里 `push` 到的 DLL 名只有
`user32.dll`(4)、`ws2_32.dll`(2)、`kernel32.dll`(2)、`ntdll.dll`(2)、`iphlpapi.dll`(1)、
`normaliz.dll`(1)、`tersafe.dll`(1)、`advapi32.dll`(1)、`netapi32.dll`(1)。
**没有 IIPS、没有 TNSDK。** 两者都是腾讯的网络/传送层组件；它们不在此 DLL 的明文引用中。
这与「玩法流量走 TNSDK/IIPS 传送层、且该层不在本文件的明文可见范围内」一致——但请注意，
这是**「未见其人」而非「查无此人」**（TVM 加密串的存在使明文扫描不完备）。

---

## 10. 【524 / 615 所属连接】

**UNKNOWN —— 且当前不具备回答条件。**

- 早前在 MD5 数据区与椭圆曲线数据区命中 `"524"` / `"615"`，**疑为假阳性**（HIGH 疑）。
  这两个常数（`0x20C` / `0x267`）与哈希/曲线常量重合概率高，必须按 opcode 在代码段重验。
- 第九目标要求先**确认真正的游戏 socket**，再回答六问（哪条连接 / TCP 还是 UDP / 哪个阶段 /
  前置客户端请求 / 客户端为何继续或停止 / 下一条预期消息）。
  **§4–§8 已表明：真正的游戏 socket 尚未定位。** 因此在找到它之前，
  任何「524 属于哪条连接」的答案都只能是编造。**此处留空，不填。**

---

## 11. 【仍未知的问题】

1. **填 `.idata2` 的是谁** —— 推测是 TVM 加载桩，需要分析 `.tvm0`（31 MB）或入口 `0x149c` 才能证实。
2. **游戏 netcode 在哪** —— 不在明文 `.text` 的 IAT 可见范围内。可能去向：
   `.tvm0` 内被保护的本体代码；或 TNSDK/IIPS 传送层（由外部 DLL 提供，明文无引用）。
3. **协议端口** —— 无运行时参数，无结论。**这是第五目标的核心，仍未达成。**
4. **524 / 615 语义** —— 依赖第 2、3 项。
5. **`.ifs`（974 个 / ~23 GB）运行时挂载** —— 由 `IIPS/IFS2.dll` + `IIPSVFS.dll` 挂载；
   **游戏本身未必需要解包**（此点若成立，可直接省掉整条解包路线）。
6. **启动门禁** —— `TCLS_SHAREDMEMEMORY` 等命名内核对象读不到即弹 `WIN_NO_TCLS`。
   **这道门禁在客户端本地，不在服务端协议**：即便协议完全还原，它也拦在前面。

---

## 12. 【下一步】

按「先确证、后推断」排序，且**第八目标（动态验证）现在是唯一能回答端口问题的路径**：

1. **静态侧到此为止的部分要说清楚。** 静态分析对本 DLL 的**游戏协议**已接近极限：
   明文扫描在 TVM 加密串面前不完备，`.tvm0` 未分析，而 IAT 可见网络栈已确证属第三方库。
   继续在 `.text` 明文里找游戏端口，**预期回报为零**。
2. **第八目标：动态验证。** 这本来就是既定目标，且是打破僵局的唯一手段。
   在合法启动客户端的条件下，记录 `connect` / `send` / `recv` 的
   时间、线程、API、socket 句柄、**目标 IP、目标端口、协议、返回值**。
   端口必须由此确证——**符合「必须从实际运行时参数确认」的约束**。
3. **定位 `.tvm0` 的本体还原范围。** 先做静态度量：`.tvm0` 中是否存在
   `sockaddr_in` 构造模式（`66 C7 00 xx xx` 写 `sin_port`、`C7 00 02 00 00 00` 写 `sin_family=2`）。
   这是**在受保护段内找证据**，而非从字符串池猜端口。
4. **重新验证 524 / 615**：按 opcode 在代码段内定位，排除 MD5/曲线常量假阳性。
5. **厘清 `.ifs` 挂载**：确认 `IIPSVFS` 是否在运行时按需挂载、游戏是否可直接读——
   这可能让 23 GB 的解包工作变成不必要。
6. **门禁问题单独处理**（与协议无关）：TCLS 命名共享内存是本地检查，
   它决定的是「能否启动」，而非「能否联网」，两条战线应分开评估。

> 会话中形成的、必须随结论一起传递的元判断：
> **本 DLL 里那张 IAT 不是游戏的网络层。** 任何基于「从 IAT 找游戏 socket」的后续推断都会失败。
> 下一步必须换阵地——要么进 `.tvm0`，要么上动态验证。

---

## 13. 【后续补证 —— 家族 A/B 与 WKNet 簇】

> 本节为后续静态取证追加。完整交付见 `docs/net-familyAB-report.md`。

### 13.1 家族 A / B 的身份（推翻「两个游戏网络家族」的前提）

| | 家族 A | 家族 B |
|---|---|---|
| 身份 | 静态 **libcurl 7.65.1** | 静态 **libcurl 7.63.0** |
| 版本串 | `0x107ac794`（唯一引用 `0x1041f84d`） | `0x1095dd7c`（唯一引用 `0x1064116d`） |
| 栈 | 仅 IPv4 | IPv4 + IPv6 双栈 |
| 用途 | 第三方库，**非游戏网络** | 第三方库，**非游戏网络** |

**置信度 HIGH。** §5–§6 中「未确证游戏 connect/send 链路」由此得到解释：**任务 1 所列六个 A 侧地址与六个 B 侧地址全部是 libcurl 内部函数**（`lib/connect.c`、`lib/tftp.c`、`lib/ftp.c`）。A/B 不是「两种游戏网络模式」，而是**同一第三方库的两个版本被静态链入同一映像**。

- 4 字节帧 = **curl TFTP 的 `opcode(2B)+block(2B)`**，**非**游戏 netcode 帧格式。HIGH
- `0x1044b240` = curl **HTTP Digest 认证**（**不是** getaddrinfo 包装器）；`0x1065fca0` = printf/整数格式化族。HIGH
- 真正的 getaddrinfo 调用点：`0x2b3cd0`(OpenSSL)、`0x44b267`(A)、`0x65fcc8`(B)。

### 13.2 WKNet 簇 —— 唯一非库网络代码

地址范围 `0x1022axxx` / `0x1022exxx` / `0x10231xxx` / `0x10232xxx` / `0x10235xxx` / `0x1023axxx`。**腾讯 WeGame「悟空」选路 / 接入模块**，非游戏 netcode。置信度 HIGH。

**13.2.1 主机名来源已确定（§7 中此前为 UNKNOWN 的一项）**

`0x1022e7a0`（WKNet 加载器，`ret 0xc`）**在栈上逐字节构造四个主机名**，由配置对象标志 `[cfg+0x64]`（经 `0x1022a840` 取得）二选一：

| `[cfg+0x64]` | 主 | 备用 |
|---|---|---|
| `!= 0` | `wukong.gamesafe.wegamex.com.hk` | `wukong1.gamesafe.wegamex.com.hk` |
| `== 0` | `wukong.gamesafe.qq.com` | `wukong1.gamesafe.qq.com` |

四个指针经 `eax` 传给 VM 解析函数 `0x1022edc0`，每个域名调用两次（主 + `1` 前缀备用）。**这解释了「`.rdata` 找不到主机名」——它们根本不在 `.rdata`。** HIGH

**13.2.2 硬编码兜底 IP 与端口的实际使用点**

- 九条 IP 串 `0x109235b0`–`0x10923630`（三组各三条）→ 循环 `0x1022ea71`：`rand()%3 + {0,3,6}` 每组取一 → **`inet_addr`（桩 `0x1045311e`）** → `push_back` 进 `vector<in_addr> @ [edi+0x04]`（`0x10088fdb`）。**当且仅当 `[edi+0x10]` 处 vector 项数 ≥3 时整套跳过**（`0x1022ea6a cmp edx,3 / jae`）。
- 端口常量 `0x32cb` / `0x32cc` / `0x32cd` = **13003 / 13004 / 13005**（写于 `0x1022eaa9`/`0x1022eab0`/`0x1022eab7`）→ `push_back` 进 `vector<u_short> @ [edi+0x1c]`（`0x100890db`，循环 3 次）。
  **★ 这三个端口是从常量指令直接读出，不是从字符串池反推** —— 满足约束的形式要求。但**它们仍未在运行时被观测**，故**不满足「必须从实际运行时参数确认」**，只作静态证据列出。

**13.2.3 `sin_addr` 的第二条线（与 §4 的 ICMP 探测同源）**

```
0x102310d7  mov edx,[eax+0x34]          ; eax = 0x1022a670() 的 68 字节单例
0x102310e3  mov [esi],edx
0x102310e5  call 0x10235e00
0x10235e44  mov word  [ebp-0x11c],2     ; sin_family = AF_INET
0x10235e4b  mov dword [ebp-0x118],edx   ; ★ sockaddr_in.sin_addr
0x10235ec9  call dword ptr [0x10b02a4c] ; = sendto
```

`0x10b02a4c` = **`sendto`**，WS2_32 **ordinal 20**（`0x80000014`），**由目标 DLL 导出表 ordinal → 名字反查证实**，非签名推断。同理 `0x10b02a58` = `WSASetLastError`(ord 112)、`0x10b02a54` = `__WSAFDIsSet`(ord 151)。

**★ 序号导入铁律：IAT 槽值高位若为 1（`IMAGE_ORDINAL_FLAG`），必须走 `IMAGE_EXPORT_DIRECTORY` 反查，不能 `cstr`。**

**13.2.4 未解缺口 —— 已从「未找」升级为「已证明不在明文内」**

**`WKNet_singleton + 0x34` 在全 `.text` 中没有任何明文写入者。** 扫描覆盖 opcode ∈ {`89`,`88`,`8b`,`8a`,`c7`,`c6`} × modrm ∈ {`40`–`47`}（含 `disp8` 与 `disp32` 全形式）：簇内**唯一**命中是 `0x102310d7` 的 **load**，**零 store**；最近的写入落在 `0x10238994` 之后。

同时 `0x1022edc0`（唯一同时接收「容器 + 主机名指针」的明文入口）**首指令 `jmp 0x134f2d50`，而 `0x134f2d50` 与 `0x134da308` 均已由节表确认落在 `.tvm0`**（`va=0x19dd000`，起始 32 字节 `fa5b42c6e749f11a…` 高熵）。
⇒ **该字段的写入落在虚拟化保护内，静态不可解码。这是有证据支撑的否定结论，不是猜测。** 置信度 HIGH。

**13.2.5 68 字节单例的已证布局**（由 `0x1022e7a0` 逐指令得出）

```
[+0x00] byte     初始化标志（0x1022eb36 置 1；0x1022e7fe 清 0）
[+0x04] vector   vector<in_addr> — 兜底 IP
[+0x10] vector   （加载器在 0x1022ea6a 检查项数是否 >=3）
[+0x1c] vector   vector<u_short> — 端口 13003/13004/13005
[+0x40] dword    加载器 arg1（本函数最高写入偏移）
```

**注意：`[edi+0x34]` 从未被 `0x1022e7a0` 写入。**

### 13.3 必须随结论传递的元判断（追加）

- **「明文函数体零静态调用者」是虚拟化调用图的结构性属性**（`0x22e610` / `0x22e740` 等 TVM 派发器入口），不是死代码判据。**必须停止对 `0x1022exxx` 簇使用「无调用者 = 未使用」。**
- **在反汇编文本里 grep `+0x34` 会命中栈操作数**：`1022ee63 mov eax,[esp+0x34]`、`10227178 mov [ebp+0x34],edx`、`10232138 mov eax,[ebp+0x34]`、以及主机名构造段中的 `mov byte ptr [ebp-0x34], 0x73`。**不得当作对象字段写入的证据。**
- **`GAME_NETWORK_CONFIRMED` 未达到。** 条件「拿到真实端点」未满足：`.text` 内不存在游戏 netcode，无运行时观测，任务 8（动态验证）仍受阻（`工具` 目录为空）。

---

*本文只记录可验证事实与否证结论，不含任何绕过 / 会话伪造实现。*
