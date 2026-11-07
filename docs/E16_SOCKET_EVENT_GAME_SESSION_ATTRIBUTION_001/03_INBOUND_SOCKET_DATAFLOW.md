# 03 — 入站 socket 数据流 / INBOUND SOCKET DATAFLOW

> 等级：PROVEN / INFERRED / BLOCKED / REFUTED

---

## 1. 唯一的入站接收点（PROVEN）

在 0x1B0430..0x1B0F30 内，唯一的入站网络调用是 recvfrom（0xBAE50C），位于 0x1B0BA1。全部调用点：

| IAT | 调用点 | 说明 |
|---|---|---|
| recvfrom 0xBAE50C | 0x1B0BA1 | 仅此一处 |
| sendto 0xBAE504 | 0x1B09EF | 出站（ICMP echo） |

## 2. 入站数据流（完整，DIRECT）

    1B0ADF  mov al,[edi+ecx+0x655C]     ; DNS 已完成？
    1B0AE8  je 0x5B0CA4
    1B0AEE  mov ecx,[0x7474EAC]
    1B0AF4  mov dl,[edi+ecx+0x655D]
    1B0AFD  jne 0x5B0CA4
    1B0B44  call [0xBAE4D8]             ; select
    1B0B4A  cmp eax,1 / jne 0x5B0CA4
    1B0B53  mov ecx,[0x7474EAC]
    1B0B59  mov edx,[edi+ecx+0x5C30]    ; socket 句柄
    1B0B60  lea eax,[esp+0x50]          ; 收包缓冲 = 栈上
    1B0B64  push eax / push edx
    1B0B66  call [0xBAE4E0]             ; __WSAFDIsSet
    ...
    1B0BA1  call [0xBAE50C]             ; recvfrom

收包缓冲：[esp+0x50]（栈上临时缓冲，随函数返回失效）。

## 3. 是否为 ICMP 回复的独立证据（PROVEN）

| 证据 | 内容 |
|---|---|
| ICMP 句柄创建 | IcmpCreateFile（0xBAE098）@0x1B0580 |
| ICMP echo 发送 | IcmpSendEcho2（0xBAE09C）@0x1B0957 |
| ICMP 回复解析 | IcmpParseReplies（0xBAE094）@0x1B0A72 |
| ICMP 句柄关闭 | IcmpCloseHandle（0xBAE090）@0x1B0808/0x1B0826 |
| socket 创建 | socket（0xBAE508）@0x1B05C9 |
| 目标端口 | htons @0x1B09BB（写入 sockaddr） |

裁定：recvfrom 收到的是 ICMP echo 回复（由 IcmpParseReplies 解析），不是游戏协议报文。

## 4. 是否存在分帧、解包、队列或应用层分派

| 检查 | 结果 |
|---|---|
| 长度字段提取 | 无 |
| 消息边界 | 无 |
| 类型字段分派 | 无 |
| 队列提交 | 无 |
| 复制到对象字段 | 无（数据交 IcmpParseReplies 后丢弃） |
| 应用层函数调用 | 无（该函数内部自闭合） |

裁定（REFUTED，限定范围）：0x1B0430 内不存在游戏协议分帧/队列/应用层分派。

## 5. 结果如何被使用（PROVEN）

ICMP 往返时间（RTT）写入 [obj+ebx+0x934]（0x1B097A: mov [ebx+ecx+0x934],eax）。这是服务器延迟测量，供服务器列表/选择 UI 使用，与游戏会话数据无关。

## 6. 裁定

| 项 | 裁定 |
|---|---|
| 入站接收点 | PROVEN（0x1B0BA1 recvfrom，唯一） |
| 收包缓冲 | PROVEN（栈上 [esp+0x50]） |
| 数据性质 | PROVEN（ICMP echo 回复） |
| 分帧/队列/分派 | REFUTED（不存在） |
| 结果用途 | PROVEN（RTT 写入 [obj+ebx+0x934]） |
| 游戏入站数据路径 | REFUTED |