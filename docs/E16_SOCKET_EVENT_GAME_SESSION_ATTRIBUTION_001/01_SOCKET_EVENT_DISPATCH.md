# 01 — Socket 事件分派 / SOCKET EVENT DISPATCH

> 只读静态分析。冻结基线（本轮开工复核，全部一致）：
> 客户端 353754047dbbfe3afbf6c7d97de3faca785b3d5d5e34a9053c820ee78814d6e1
> 恢复镜像 24b4ef2502d3661df178f557192534098c714353cf8c2a00a2ffb26af2bb97e4
> 服务端 80816711946a5392abab81a625a516f24fb4d649e9b8008fc5a4e506be750ea1
> 地址为 RVA（VA = RVA + 0x400000）。等级：PROVEN / INFERRED / BLOCKED / REFUTED

---

## 1. 函数边界

| 项 | 值 |
|---|---|
| 入口 | 0x1B0430 |
| 结尾 | 0x1B0E2C 附近（回跳式轮询） |
| 大小 | 约 0xB00 字节（691 条指令） |
| 被引用方式 | 数据指针 .text@0x1B007F（非直接 call） |

## 2. 该函数使用的全部网络/系统 API（PROVEN，决定性）

按导入表（_tools/t02_iat.py）统计 0x1B0430..0x1B0F30 范围内的 IAT 引用：

| IAT VA | DLL | API | 出现 |
|---|---|---|---|
| 0xBAE098 | iphlpapi.dll | IcmpCreateFile | 1 |
| 0xBAE09C | iphlpapi.dll | IcmpSendEcho2 | 1 |
| 0xBAE094 | iphlpapi.dll | IcmpParseReplies | 1 |
| 0xBAE090 | iphlpapi.dll | IcmpCloseHandle | 2 |
| 0xBAE484 | ws2_32.dll | getaddrinfo | 1 |
| 0xBAE494 | ws2_32.dll | freeaddrinfo | 1 |
| 0xBAE508 | wsock32.dll | socket | 1 |
| 0xBAE4D8 | wsock32.dll | select | 1 |
| 0xBAE4E0 | wsock32.dll | __WSAFDIsSet | 1 |
| 0xBAE4DC | wsock32.dll | WSAGetLastError | 1 |
| 0xBAE500 | wsock32.dll | htons | 2 |
| 0xBAE504 | wsock32.dll | sendto | 1 |
| 0xBAE50C | wsock32.dll | recvfrom | 1 |
| 0xBAE170 | kernel32.dll | CreateEventA | 1 |
| 0xBAE168 | kernel32.dll | WaitForSingleObject | 1 |
| 0xBAE184 | kernel32.dll | Sleep | 2 |
| 0xBAE178 | kernel32.dll | GetTickCount | 5 |
| 0xBAE138 | kernel32.dll | GetLastError | 3 |
| 0xBAE140 | kernel32.dll | CloseHandle | 2 |

关键（PROVEN）：该函数的核心网络原语是 ICMP（IcmpCreateFile / IcmpSendEcho2 / IcmpParseReplies / IcmpCloseHandle），配合 DNS 解析与原始 socket。

## 3. 函数开头的语义（PROVEN）

    1B044D  push 0xB9EC / call 0xB4A135     ; operator new(0xB9EC)
    1B0480  mov byte [eax+0xB83C],0
    1B048E  mov [0x7474EAC],eax             ; 全局单例指针
    1B0493  mov eax,[0x7474EB0]             ; 服务器条目数
    1B04A2  mov esi,0x2CCA3C8               ; 服务器表基址
    1B04CF  call [0xBAE484]                 ; getaddrinfo
    1B04F2  cmp dword [eax+4],2             ; AF_INET 检查
    1B0536  call [0xBAE494]                 ; freeaddrinfo

0x1B0430 首先在 0x2CCA3C8 的服务器表上做 DNS 解析，并缓存 IPv4 地址到 [obj+0xB840] 数组。

## 4. 事件分派结构

函数不是"socket 事件状态机"，而是周期性轮询循环 + 每服务器状态标志分派：

| 状态标志 | 偏移 | 分派点 | 语义 |
|---|---|---|---|
| 主机解析完成 | [obj+0xB83C] | 0x1B0558 | 数据块级循环入口门 |
| 每服务器 ICMP 阶段 A | [obj+ebx+0x930] | 0x1B08C0 / 0x1B0A25 | ping 已发出 |
| 每服务器 ICMP 阶段 B | [obj+ebx+0x931] | 0x1B08FD | echo 已回复 |
| 每服务器解析状态 | [obj+ebx+0x655C] | 0x1B08DA / 0x1B0ADF | DNS 已完成 |
| 每服务器解析结果 | [obj+ebx+0x655D] | 0x1B0991 / 0x1B0AF4 | DNS 成功 |

外层循环（0x1B0550 至 0x1B0E2C）以 Sleep(1) + GetTickCount 节流，遍历 0x64（100）个服务器槽位。

## 5. 四个"事件分支"的实际含义（本轮更正 E-13 用词）

E-13 称其为"四个事件分支"（0x1B086D / 0x1B0991 / 0x1B0A25 / 0x1B0ADF）。本轮更正：这四者不是并列的 socket 事件类型，而是 ICMP ping 流程的四个顺序阶段。

| E-13 标注 | 实际语义 | 裁定 |
|---|---|---|
| 0x1B086D | 计时基准重置（GetTickCount） | PROVEN |
| 0x1B0991 | 构造 ICMP echo 请求（htons + type） | PROVEN |
| 0x1B0A25 | 检查 ping 是否已发出/已回复 | PROVEN |
| 0x1B0ADF | 检查 DNS 解析状态并进入 select/recvfrom 收包 | PROVEN |

四个分支全部属于同一 ICMP ping 子系统，不存在"游戏会话入站数据分支"。

## 6. 裁定

| 项 | 裁定 |
|---|---|
| 函数边界 | PROVEN（0x1B0430 起） |
| 引用方式 | PROVEN（数据指针，非直接 call） |
| 核心网络原语 | PROVEN（ICMP + DNS + 原始 socket 探测） |
| "四个事件分支"性质 | PROVEN（ICMP 四阶段，非并列事件类型） |
| 是否游戏会话事件机 | REFUTED |