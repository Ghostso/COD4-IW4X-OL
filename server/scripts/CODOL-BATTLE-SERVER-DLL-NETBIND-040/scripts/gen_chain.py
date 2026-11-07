# -*- coding: utf-8 -*-
import io, os
ROOT=r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL-BATTLE-SERVER-DLL-NETBIND-040"
def W(n,t): io.open(os.path.join(ROOT,n),"w",encoding="utf-8",newline="").write(t)

W("SOCKET_EVENT_RECEIVE_CHAIN.md", u"""# SOCKET_EVENT_RECEIVE_CHAIN — socket/event → 接收缓冲区

**证据等级: CONFIRMED_DATAFLOW (到栈缓冲区写入) / UNKNOWN (缓冲区 → 解析器)**

本节所有地址: `VA = 0x10000000 + RVA`。RVA→文件偏移按 PE 节区表核算 (`.text`: RVA 0x1000, 文件偏移 0x400, 故 `file_off = RVA - 0xC00`)。

---

## 1. 对象构造: socket + event + 接收缓冲 (RVA 0x235CD0)

函数 `0x235CD0` 构造一个网络对象 (寄存器 `esi` = this):

| 步骤 | 地址 | 机器码 | 语义 | 对象字段 |
|---|---|---|---|---|
| 1 | `0x235CF4` | `ff152422b010` | `call [0x10B02224]` = **GetTickCount** | `[esi+0x14]` = 起始 tick |
| 2 | `0x235D04` | `ff15b423b010` | `call [0x10B023B4]` = **GetLocalTime** | 栈上时间 |
| 3 | `0x235D18` | `ff15bc23b010` | `call [0x10B023BC]` = **SystemTimeToFileTime** | 栈上时间 |
| 4 | `0x235D2A-0x235D33` | `push 0 / push 0x2710 / push eax / push ecx` + `call 0x10291880` | 10000ms (10s) 常量参与时间比较 | `[esi+0x18]`,`[esi+0x1C]` |
| 5 | `0x235D4F` | `ff156c2ab010` | `call [0x10B02A6C]` = **WSACreateEvent** | `[esi+0x04]` = hEvent |
| 6 | `0x235D58` | `ff151c22b010` | `call [0x10B0221C]` = **GetCurrentProcessId** | `[esi+0x08]` = pid |
| 7 | `0x235D5E-0x235D6D` | `push 0; push 0; push 0; push 1; push 3; push 2; call [0x10B02A60]` | **WSASocketW(af=2, type=3, protocol=1, lpProtocolInfo=0, g=0, dwFlags=0)** | `[esi+0x00]` = s |
| 8 | `0x235D75` | `cmp eax, -1` | `s == INVALID_SOCKET` 则跳过注册 | — |
| 9 | `0x235D7D-0x235D81` | `push 1; push [esi+4]; push eax; call [0x10B02A68]` | **WSAEventSelect(s, hEvent, 1=FD_READ)** | — |
| 10 | `0x235D87-0x235D99` | `push 0x30; call malloc; memset(0,0x30)` | 分配 0x30 字节结构 | `[esi+0x0C]` = ptr |
| 11 | `0x235DA1` | `c6461001` | 置有效标志 | `[esi+0x10]` = 1 |

字段布局 (由机器码直接推出):

| 偏移 | 含义 | 证据地址 |
|---|---|---|
| +0x00 | SOCKET | `0x235D73` |
| +0x04 | WSAEVENT | `0x235D55` |
| +0x08 | 进程 id | `0x235D6A` |
| +0x0C | 0x30 字节结构指针 | `0x235D96` |
| +0x10 | 有效标志 (byte) | `0x235DA1` |
| +0x12 | 递增序号 (word) | `0x235E60` `inc word [esi+0x12]` |
| +0x14 | 基准 tick | `0x235D01` |

**注意 (反过度声称):** 步骤 7 的常量 `af=2, type=3, protocol=1` 对应 `AF_INET / SOCK_RAW / 1(IPPROTO_ICMP)`。全 DLL 中 **唯一** 的 `WSASocketW` 调用点就是这里 (`evidence/winsock_callsites.tsv` 中 WSASocketW 仅 1 行)。libcurl/OpenSSL 的 socket 走的是序号导入 `socket`(ord 23) 的其它槽。因此本对象是否为游戏 netchan 通道, 还是网卡/ICMP 诊断通道, **静态证据不足以判定**。

---

## 2. 发起接收操作 (RVA 0x235E00)

函数 `0x235E00` (被 `0x2310E5` 调用) 是接收+校验主体:

| 步骤 | 地址 | 机器码 | 语义 |
|---|---|---|---|
| 1 | `0x235E13` | `mov eax,[ebp+8]` | 入参 (out 结构指针) |
| 2 | `0x235E44-0x235E51` | `mov word [ebp-0x11C],2 ; mov dword [ebp-0x118],edx ; mov dword [ebp-0x124],0x10` | 初始化 `sockaddr_in`(family=2)/`fromlen=0x10` |
| 3 | `0x235E60` | `66ff4612` | `inc word [esi+0x12]` 序号自增 |
| 4 | `0x235EBC-0x235EC9` | `push [ebp-0x124] / lea ecx,[ebp-0x11C]; push ecx / push 0 / push 0x30 / push [esi+0xC] / push [esi]; call [0x10B02A4C]` | **sendto** (序 20): 先发 0x30 字节 |
| 5 | `0x235F17-0x235F23` | `push 1; push 0x64; push 0; lea edi,[esi+4]; push edi; push 1; call [0x10B02A70]` | **WSAWaitForMultipleEvents(1, &hEvent, FALSE, 100ms, FALSE)** |
| 6 | `0x235F29` | `cmp eax, 0xC0` | `WSA_WAIT_TIMEOUT(0x102)` / `0xC0` 分支 |
| 7 | `0x235F4C` | `call [0x10B02A64]` | **WSAEnumNetworkEvents(s, hEvent, &netevents)** |
| 8 | `0x235F52` | `test byte [ebp-0x170],1` | 检查 `lNetworkEvents & FD_READ(1)` |
| 9 | `0x235F5F-0x235F7E` | 见下表 | **recvfrom** |
| 10 | `0x235F86` | `cmp edi,-1` | 返回值校验 |

### 实际接收调用点 (recvfrom)

| 项 | 值 |
|---|---|
| RVA | `0x235F7E` |
| VA | `0x10235F7E` |
| 文件偏移 | `0x23537E` |
| 节区 | `.text` |
| 原始字节 | `ff15482ab010` (= `call dword ptr [0x10B02A48]`) |
| IAT 槽 | RVA `0x00B02A48` / VA `0x10B02A48` / 文件偏移 `0x00AF8648` |
| 槽值 | `0x80000011` = **WS2_32 序号 17 = recvfrom** |

### recvfrom 参数 (由 0x235F5F..0x235F7D 的压栈序列推出)

```
0x235F5F  lea eax,[ebp-0x124]   ; &fromlen
0x235F65  push eax
0x235F66  mov eax,[esi]         ; s           (对象 +0x00)
0x235F68  lea ecx,[ebp-0x11C]   ; &from       (sockaddr_in)
0x235F6E  push ecx
0x235F6F  push 0                ; flags = 0
0x235F71  push 0x100            ; len = 256
0x235F76  lea edx,[ebp-0x10C]   ; buf
0x235F7C  push edx
0x235F7D  push eax              ; s
0x235F7E  call [0x10B02A48]     ; recvfrom
```

- **socket 句柄**: `[esi+0]`, 来自 `WSASocketW` (WC-003)。
- **event**: `[esi+4]`, 由 `WSACreateEvent` 创建, 由 `WSAEventSelect` 绑定, `WSAWaitForMultipleEvents` 等待, `WSAEnumNetworkEvents` 解码。
- **缓冲区**: 函数栈上 `[ebp-0x10C]`, 长度 **0x100 = 256** 字节 (栈局部, 不是堆)。
- **接收长度**: 请求 256; 实际长度 = 返回值 `EAX`, 立即移入 `EDI` (`0x235F84 mov edi,eax`)。
- **返回值/错误**: `0x235F86 cmp edi,-1` (`SOCKET_ERROR`) 分支则放弃本轮。

---

## 3. 接收后的处理 (0x235F8F..0x2360B3)

| 地址 | 机器码 | 语义 |
|---|---|---|
| `0x235F8F` | `e87c010000` | `call 0x10236110` (取时间戳) |
| `0x235F94-0x235FA7` | `mov cl,[ebp-0x10C]` / `and cl,0xF` / 展开为 word | 取 **接收缓冲区第 0 字节的低 4 位** 作为索引 |
| `0x235FAD-0x235FCF` | `mov ebx,[ebp+ecx-0x108]` / `cmp ebx,[esi+8]` / `cmp byte [ecx],0` / `cmp word [ecx+8],bx` | 与 `[esi+8]` (pid/本地标识) 比对 → 源地址/身份校验 |
| `0x236058-0x236079` | `sub eax,[ecx+0xC]` / `movzx ecx,byte [ebp-0x104]` / `mov [esi_out+4],eax` / `sub edi,eax` / `sub edi,0x10` / `mov word [esi_out],bx` / `mov [esi_out+8],edi` / `mov [esi_out+0xC],ecx` | 把长度/身份/时间写入调用方的 out 结构 |

**关键观察**:
- 接收后**第一件事**是读取 `buf[0] & 0x0F` —— 与 "低 4 位类型/opcode" 形态一致, 但**没有**可复核的证据表明它随后驱动一个 opcode→handler 分派表。
- 栈缓冲区 `[ebp-0x10C]` 的内容**未见**被复制到堆/持久缓冲区; out 结构里存的是长度与身份字段, 不是负载拷贝。
- **未定位** netchan 序列/分片重组、消息边界或应用层解析器调用。

---

## 4. 链路状态

```
WSASocketW  (0x235D6D, AF_INET/SOCK_RAW/proto=1)      CONFIRMED_DIRECT
   ↓
WSACreateEvent (0x235D4F)                              CONFIRMED_DIRECT
   ↓
WSAEventSelect (0x235D81, FD_READ)                     CONFIRMED_DIRECT
   ↓
sendto / WSAWaitForMultipleEvents / WSAEnumNetworkEvents  CONFIRMED_DIRECT
   ↓
recvfrom (0x235F7E) -> stack buf [ebp-0x10C], len 0x100   CONFIRMED_DATAFLOW
   ↓
返回值 EAX -> EDI (长度)                                   CONFIRMED_DATAFLOW
   ↓
buf[0]&0xF 索引 + 源身份校验                               CONFIRMED_DATAFLOW (校验)
   ↓
netchan / opcode 解析器                                    UNKNOWN  ← 未闭合
```

**未闭合原因**: 接收后的处理只到"读取 buf[0] 低 4 位 + 源校验 + 写 out 结构", 未发现以该值索引的 handler 表、未发现栈缓冲区向持久缓冲区的拷贝、应用层解析入口不在 `.text` 可达范围 (见 `STATIC_ANALYSIS_BLOCKERS.md`)。

---

## 5. 归属提示 (反过度声称)

`evidence/winsock_callsites.tsv` 显示所有 `recv`/`recvfrom` FF15 调用点中, 绝大多数位于 libcurl/OpenSSL 区段:

| RVA | 归属线索 |
|---|---|
| `0x2D97F3` (`recv`) | OpenSSL `crypto\bio\b_sock2.c` |
| `0x41EED1 / 0x41F394 / ...` (`recv`) | libcurl (Set-Cookie/http 邻接) |
| `0x64BDA1 / 0x64C24F / ...` (`recv`) | libcurl |
| `0x42D97F` (`recvfrom`) | libcurl IMAP (`Got unexpected imap-server response`) |
| `0x670DAF` (`recvfrom`) | libcurl IMAP |
| **`0x235F7E` (`recvfrom`)** | **0x235xxx 独立 socket/event 对象簇; 无第三方库字符串** |

显式 `GetProcAddress("WSACreateEvent"/"WSAEventSelect"/...)` 的解析器位于 `0x430B10`, 其邻接字符串为 libcurl 的 FTP/TELNET 诊断文本 (`.rdata 0x7AE8xx`), 因此该解析器**很可能属于 libcurl 的 Winsock 延迟绑定**, 不能直接等同于游戏 netchan 的绑定。
""")
print("SOCKET_EVENT_RECEIVE_CHAIN.md written")
