# 02_IMPORT_IDENTITY_HYPOTHESES — `0x87BE00` API 身份判定

**镜像:** S-IMG `17cef6e0a5e7b8d14fb97b5fdd846061187c6a722cfa3c5d432bee37872fd045`
**地址约定:** ImageBase `0x400000`;`file_offset = RVA = VA - 0x400000`。
**注意:** `0x87BE00`、`0x87BA50`、`0x0CA84E8` 等在不同文献中混用 RVA/VA;本文一律**显式标注**。

---

## 0. 结论(TL;DR)

| 假设 | 内容 | 裁定 |
|---|---|---|
| H1 | `0x87BE00` 是 socket/网络接收路径 | **CONFIRMED** |
| H2 | `0x87BE00` 是 `ReadFile`/重叠文件读取路径 | **REJECTED** |
| H3 | 属于其他 I/O 或封装层 | 部分成立(它是 select+recv 的**封装**),但封装对象是**套接字**,非"其他 I/O" |
| H4 | 现有证据不足以确定 | **不成立**(证据已足) |

`0x87BE00` = **`select()` 超时门控 + `recv()` 读取** 的封装原语;
错误经 **`WSAGetLastError()`** 判 `WSAEINTR(10004)` 与 `WSAEWOULDBLOCK(10035)`。

## 1. 决定性证据 A:槽表序号身份(静态、可复核)

指令里的 `call dword ptr [0x0CA84E8]` 使用**绝对 VA**;正确 file_offset = `0x008A84E8`。
该位置位于 S-IMG 第 2 节区(`.tp3` VA `0x8A8000`,Raw `0x8A8000`,RSize `0x16E000`)内,**可读**。

S-IMG 运行期值 vs 磁盘 EXE 未重定位值(同一 RVA):

| 槽 VA | 槽 RVA | 磁盘 EXE dword(未绑定) | 序号 | 运行期镜像值 | 名称 |
|---|---|---|---|---|---|
| `0x00CA84E0` | `0x008A84E0` | `0x80000013` | 19 | `0x116CF5CD` | **send** |
| `0x00CA84E4` | `0x008A84E4` | `0x80000010` | 16 | `0x116CE13A` | **recv** |
| `0x00CA84E8` | `0x008A84E8` | `0x80000012` | 18 | `0x116CF641` | **select** |
| `0x00CA84EC` | `0x008A84EC` | `0x80000005` | 5 | `0x116CF2CC` | **getpeername** |
| `0x00CA84F0` | `0x008A84F0` | `0x80000004` | 4 | `0x116CFFEE` | **connect** |
| `0x00CA84FC` | `0x008A84FC` | `0x8000000D` | 13 | `0x116CD32D` | **listen** |
| `0x00CA8500` | `0x008A8500` | `0x80000001` | 1 | `0x116CF9F6` | **accept** |
| `0x00CA8510` | `0x008A8510` | `0x80000016` | 22 | `0x116CFA98` | **shutdown** |
| `0x00CA8518` | `0x008A8518` | `0x80000014` | 20 | `0x116CDF36` | **sendto** |
| `0x00CA851C` | `0x008A851C` | `0x80000011` | 17 | `0x116CD717` | **recvfrom** |
| `0x00CA8520` | `0x008A8520` | `0x80000074` | 116 | `0x116CF4F9` | **WSACleanup** |
| `0x00CA8524` | `0x008A8524` | `0x80000070` | 112 | `0x116CFE8A` | **WSASetLastError** |
| `0x00CA8528` | `0x008A8528` | `0x80000097` | 151 | `0x116CFA30` | **__WSAFDIsSet** |
| `0x00CA8534` | `0x008A8534` | `0x80000073` | 115 | `0x751C9CC0` | **WSAStartup** |
| `0x00CA8538` | `0x008A8538` | `0x80000039` | 57 | `0x751F00A0` | **gethostname** |
| `0x00CA853C` | `0x008A853C` | `0x8000006F` | 111 | `0x751C5D50` | **WSAGetLastError** |
| `0x00CA8540` | `0x008A8540` | `0x8000000A` | 10 | `0x751C57E0` | **ioctlsocket** |
| `0x00CA8544` | `0x008A8544` | `0x80000003` | 3 | `0x751CEA60` | **closesocket** |
| `0x00CA8548` | `0x008A8548` | `0x80000017` | 23 | `0x751CC990` | **socket** |
| `0x00CA8550` | `0x008A8550` | `0x80000009` | 9 | `0x751C56E0` | **htons** |
| `0x00CA8554` | `0x008A8554` | `0x80000002` | 2 | `0x751CD890` | **bind** |
| `0x00CA855C` | `0x008A855C` | `0x80000034` | 52 | `0x751EFF10` | **gethostbyname** |

> 序号→名称映射取自本机 `C:\Windows\SysWOW64\ws2_32.dll` 的导出表(序号 16=recv、18=select、19=send、111=WSAGetLastError、115=WSAStartup、116=WSACleanup、151=__WSAFDIsSet)。
> 该序号编号是 Winsock 的标准编号;`wsock32.dll` 对同一子集使用**相同序号**。

### 1.1 独立交叉验证(两种证据源一致)

`0x008A8534` 之后的槽在**运行期镜像**里已被绑定为**真实函数地址**:

| 槽 | 运行期值 | 减去 ws2_32 基址 `0x751C0000` | 与 ws2_32 导出 RVA 比对 |
|---|---|---|---|
| `0xCA8534` | `0x751C9CC0` | `0x9CC0` | `WSAStartup` RVA `0x9CC0` **完全一致** |
| `0xCA853C` | `0x751C5D50` | `0x5D50` | `WSAGetLastError` RVA `0x5D50` **完全一致** |
| `0xCA8544` | `0x751CEA60` | `0xEA60` | `closesocket` RVA `0xEA60` **完全一致** |
| `0xCA8548` | `0x751CC990` | `0xC990` | `socket` RVA `0xC990` **完全一致** |
| `0xCA8550` | `0x751C56E0` | `0x56E0` | `htons` RVA `0x56E0` **完全一致** |
| `0xCA8554` | `0x751CD890` | `0xD890` | `bind` RVA `0xD890` **完全一致** |
| `0xCA855C` | `0x751EFF10` | `0x2FF10` | `gethostbyname` RVA `0x2FF10` **完全一致** |

8/11 槽在同一基址 `0x751C0000` 下与 ws2_32 导出 RVA 精确吻合 → **运行期槽绑定 = ws2_32 导出**。
这独立复现了磁盘序号表的"Winsock"身份(两条证据路径互不依赖)。证据:`evidence/c04_resolve.txt`、`evidence/c05_base.txt`、`evidence/k01_modid.txt`。

## 2. 决定性证据 B:参数布局与调用约定(机器码)

`0x87BE00`(RVA)完整反汇编见 `evidence/z01_identity_and_pe.txt`。

```
0087be00  sub  esp, 0x110
0087be15  mov  ebx, [esp+0x11C]      ; arg2
0087be1d  mov  esi, [esp+0x11C]      ; arg1 (socket)
0087be25  mov  edi, [esp+0x12C]      ; arg4 (timeout_ms / flags)
0087be2c  test edi, edi
0087be4d  mov  eax, 0x10624DD3       ; 有符号除 1000(ms -> tv_sec)
0087be52  imul edi / sar edx,6 / ...
0087be62  imul eax,eax,0x3e8 / sub edx,eax / imul edx,edx,0x3e8   ; tv_usec

0087be76  push ecx                 ; 5th: timeout (const timeval*)
0087be77  push 0                   ; 4th: exceptfds = NULL
0087be79  push 0                   ; 3rd: writefds  = NULL
0087be7b  lea  eax,[esp+0x20] / push eax   ; 2nd: readfds (FD_SET 栈缓冲)
0087be80  lea  ecx,[esi+1] / push ecx     ; 1st: nfds = socket+1
0087be84  call dword ptr [0xCA84E8]  --> select

0087beb7  mov  edx,[esp+0x128]      ; arg3 (len)
0087bebe  push 0                   ; flags = 0
0087bec0  push edx                 ; len
0087bec1  push ebx                 ; buf
0087bec2  push esi                 ; s (socket)
0087bec3  call dword ptr [0xCA84E4]  --> recv

0087becd  mov  esi,[0xCA853C] / call esi     ; WSAGetLastError
0087bed5  cmp  eax, 0x2733          ; 10035 = WSAEWOULDBLOCK
0087be8e  call dword ptr [0xCA853C]
0087be94  sub  eax, 0x2714          ; 10004 = WSAEINTR
```

**参数布局与 Winsock 完全吻合:**

- `select(int nfds, fd_set *readfds, fd_set *writefds, fd_set *exceptfds, const struct timeval *timeout)`
  — 代码恰好压入 5 个参数:timeout、exceptfds=NULL、writefds=NULL、readfds=&栈缓冲、nfds=socket+1。
- `recv(SOCKET s, char *buf, int len, int flags)` — 代码恰好压入 4 个参数:flags=0、len=arg3、buf=arg2、s=arg1。
- `timeout` 使用 `mov eax,0x10624DD3; imul edi; sar edx,6` 的标准**有符号除 1000** 魔数,
  并把 `tv_sec=ms/1000`、`tv_usec=(ms%1000)*1000` 写入栈上的 `timeval`。
- 失败路径调用 `WSAGetLastError`(而非 `GetLastError`),并与 **WSA 错误码** `10004/10035` 比较。

> **调用约定:** 32 位 stdcall/cdecl 参数**从右到左**压栈,`call dword ptr [slot]` 经 IAT;
> 读完 `add esp,0x10` 平衡 4 个参数。数据流:返回值(recv 字节数)成为后续解码长度 `esi`(见 `03`)。

## 3. H2(`ReadFile` / 重叠文件读)为何被**证否**

044 在 `09_CORRECTION_LOG.md` C4 提出"更像 ReadFile/ReadFileEx 类重叠读",支持证据两条。两条均被本轮推翻:

| 044 的支持证据 | 045 复核 | 裁定 |
|---|---|---|
| `mov eax,0x10624DD3; imul; sar 6` 是 `ms/1000` 与 `ms%1000`,结果压入 **`OVERLAPPED`** | 同一魔数是 `select` 的 **`struct timeval`** 构造(`tv_sec`/`tv_usec`);`select` 的第 5 参数正是 `timeval*` | **改判:不是 OVERLAPPED** |
| 失败码 `0x2714`/`0x2733` 属 Win32 等待错误族(非 WSAGetLastError 族) | `0x2714=10004=WSAEINTR`、`0x2733=10035=WSAEWOULDBLOCK`,是**WSA 错误域**;且前一条指令明确 `call [0xCA853C]` = `WSAGetLastError` | **改判:是 WSA 域** |
| "两阶段调用(主+降级)在 ReadFile/RecvFile 与 WSARecv 间共享" | 两阶段是 **select(就绪等待)→recv(实际读)**;真正的两阶段读(ReadFile 失败→另一 API)语义不同(此处第二次调用是**同一套接字**的 recv,而非文件降级) | **证据不成立** |
| (无) | 文件读不需要 `select` + `timeout` + `fd_set`;文件读也不会用 `WSAGetLastError` | **决定性反证** |

> 044 的 `0x87BE00` 字节扫描**结论(0 个直接调用者、经 thunk 到达)仍然成立**,只是 API 语义判错。

## 4. 调用者与调用关系(回答任务书"`0x87BE00`、`0x87BA50` 与其调用者的实际关系")

| 关系 | 证据(VA-空间校正扫描) |
|---|---|
| `0x87BE00`(RVA)的**直接调用者** | **0 个**(节区 #1 全量 E8 扫描) |
| `0x87BA50`(RVA)= 1 条 `jmp 0x87BE00`(E9 rel32) | **跳板/别名** |
| `0x87BA50` 的**调用者** | `0x85D96E`、`0x85E71A`(共 2 处,E8) |
| `0x87C110` 的调用者 | `0x85D49D`(1 处) |
| `0x87D5A0` 的调用者 | `0x85D3DB`、`0x85D418`、`0x85D9B5`、`0x85D9F7`(4 处) |

**接收→解码路径(同一函数 `0x85Dxxx` 内,机器码连续):**

```
00C5D95E  push 0
00C5D960  push 0x4EBC                      ; 长度上限 0x4EBC
00C5D965  lea  eax,[esp+0x5000]            ; 栈上接收缓冲(~19.8KB)
00C5D96C  push eax                         ; buf
00C5D96D  push edi                         ; socket
00C5D96E  call 0xC7BA50                    ; -> jmp 0x87BE00 (select+recv)
00C5D973  mov  esi,eax                     ; 返回长度
00C5D97A  jle  out                         ; <=0 退出
00C5D980  mov  eax,[ebx]
00C5D9B5  call 0xC7D5A0                    ; 解码器 #2(用长度 esi)
00C5D9F7  call 0xC7D5A0                    ; 第二段解码
```

**这闭合了 042–044 从未闭合的边:** `socket → select+recv(0x87BE00) → 长度(esi) → 解码器 0x87D5A0`。
证据:`evidence/m01_callers.txt`、`evidence/q01_receive_to_decode.txt`、`evidence/n01_callers_ctx.txt`。

## 5. 剩余 UNKNOWN(不影响 H1 判定)

| 项 | 状态 | 说明 |
|---|---|---|
| 提供方 DLL 的**名称字符串** | `UNKNOWN` | S-IMG/磁盘 EXE 第 2 节区的 hint/name 串(`RVA 0xA149xx`)被清零;导入描述符 size=0。**名称串缺失**,但**序号身份与参数布局已足以定 API**。 |
| 运行期块 A 指针的宿主模块 | `UNKNOWN` | 块 A 运行期值(`0x116Cxxxx`)与块 B(`0x751Cxxxx`)不同;本机 ws2_32 RVA 布局无法解释块 A。可能为 ws2_32 兼容封装/不同构建的 ws2_32。**不影响**序号→API 名称判定。 |
| `0x85D96E` 调用者的业务归属 | `UNKNOWN` | 该函数属 `0x85Dxxx` 簇(与 042 的 TQOS `0x85E6F0` 邻近但**不同函数**);其在游戏层/平台层的归属未在本任务闭合。 |

## 6. 是否需要补充证据

**不需要。** 任务书要求"若现有 PE 导入表足以解决问题,不再申请其他材料"。本轮证明:

1. 041/044 设想的"最小补充证据 = 覆盖 `RVA 0x0CA8400..0x0CA8700` 的只读快照"——**其实已在本机 S-IMG 内**(只需正确做 VA→RVA 换算)。
2. 该段解析后即得出 `select`/`recv`/`WSAGetLastError`,并解开 BE-01/BE-02/BE-04。

043/044 的"必须申请新证据"建议**据此撤回**;`08_NEXT_ACTION_DECISION.md` 给出修正后的决策。
