# 05 — 传输栈归属裁定 / TRANSPORT STACK ATTRIBUTION

> 等级：PROVEN / INFERRED / BLOCKED / REFUTED

---

## 1. 候选路径归类表

| 路径 | 核心原语 | 归类 | 裁定 |
|---|---|---|---|
| 0x1B0430 | IcmpCreateFile/SendEcho2/ParseReplies + getaddrinfo + select/recvfrom | 服务器延迟测量（ping） | PROVEN |
| 0x605220 / 0x6104D0 / 0x672460 | OpenSSL + libcurl + HTTP 串 + down-update.qq.com | HTTP 更新/下载 | PROVEN |
| 0x6029A0 | recv + 错误日志（Recv failure） | 通用 socket 错误处理 | PROVEN |
| 0x775A50 / 0x775AB0 | recv/recvfrom 虚表槽位 | 通用 socket 抽象 | INFERRED |
| 0x78772D | GetSystemTimeAsFileTime | 时间戳工具 | PROVEN |

## 2. 是否存在游戏会话入站数据路径

| 检查 | 结果 |
|---|---|
| 0x1B0430 入站数据 | ICMP echo 回复（非游戏） |
| 0x605220 链入站数据 | HTTP 响应（更新模块） |
| 0x6029A0 入站数据 | 错误路径（仅 -1 时记录） |
| 剩余未归属的 recv/recvfrom 调用点 | 0x6B4DE0、0x784F60 等 |

裁定（BLOCKED，限定范围）：在 E-13 的 9 收包函数与 E-14/E-15 追踪的路径内，未发现游戏会话入站数据路径。

## 3. 关键排除（本轮新增）

| 路径 | 此前归属 | 本轮更正 |
|---|---|---|
| 0x1B0430 | 通用 socket 事件（E-13） | ICMP ping / 延迟测量（PROVEN） |
| 0x78772D | 含 .tvm0 调用（E-13） | 时间戳换算；.tvm0 定性为 REFUTED |

## 4. 传输栈清单（当前已知）

| 栈 | 证据 | 是否游戏协议 |
|---|---|---|
| ICMP ping | Icmp* API | 否（延迟测量） |
| HTTP/HTTPS (libcurl+OpenSSL) | libcurl/HTTP 串/down-update.qq.com | 否（更新） |
| 明文 UDP socket 抽象 | recv/recvfrom 虚表 | 未定（未找到游戏消息特征） |

## 5. 裁定

| 项 | 裁定 |
|---|---|
| 0x1B0430 归类 | PROVEN（ping/延迟测量） |
| 0x605220 链归类 | PROVEN（HTTP 更新） |
| 0x78772D 归类 | PROVEN（时间戳工具） |
| 游戏会话入站路径 | BLOCKED（未定位） |
| 是否可合并 HTTP/ping 与游戏模块 | REFUTED（不同用途） |