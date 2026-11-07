# 03 — 明文分帧与分派 / PLAINTEXT FRAMING AND DISPATCH

> 等级：PROVEN / INFERRED / BLOCKED / REFUTED

---

## 1. 前提

按任务要求，只有在明文数据流有证据支持后才能寻找分帧/分派。

01/02 已裁定：本链（0x605220 / 0x6104D0）不产生可用的应用层明文数据流（REFUTED）。因此本节只考察"若该栈确有分帧，其形态为何"，以确认它属 HTTP 而非游戏协议。

## 2. 该网络栈的分帧形态（PROVEN）

| 证据 | 内容 |
|---|---|
| 请求构造 | "GET %s HTTP/1.1 Connection: close Host: %s"（0xC5B440） |
| 响应解析 | "Content-Length"（4 处）、"HTTP/1.0" / "HTTP/1.1" |
| 连接管理 | "HTTP/1.0 connection set to keep alive!" |
| 库标识 | "libcurl"、"libcurl error"、"libcurl! Edit at your own risk." |
| 目标主机 | "http://down-update.qq.com/" |

裁定（PROVEN）：该栈的分帧是 HTTP/1.x 报文分帧（请求行 + 头 + Content-Length），不是 CODOL 游戏消息分帧。

## 3. 游戏协议分帧器：是否在本链内

| 目标 | 是否出现在 0x605220 六层闭包 | 证据 |
|---|---|---|
| 0xA2660（Configstring body reader） | 否 | 闭包查询返回 False |
| 0x3547D0（子帧循环） | 否 | 同上 |
| 0x350170（demo 顶层分派器） | 否 | 同上 |
| 0x34FD80（长度前缀消费者） | 否 | 同上 |
| 0xA2E50（reliable payload） | 否 | 同上 |

裁定（PROVEN 负）：0x605220 路径在六层内不接触任何已知游戏协议解析器。

## 4. 是否存在消息类型比较或跳转表

| 检查 | 结果 |
|---|---|
| HTTP 分支 | 有（HTTP/1.0 vs 1.1、POST vs GET） |
| 游戏消息 opcode 比较（1..4 表） | 无 |
| 游戏子帧编号比较（0..8 表） | 无 |

## 5. 分帧不完整时的行为

| 层 | 行为 | 证据 |
|---|---|---|
| HTTP | 由 libcurl 的 Content-Length / chunked 处理 | 字符串 |
| 连接就绪 | 0x605220 超时检查 + 1 字节探测 + recv 2 字节探测 | 01 第5节 |
| 游戏协议 | 不在本链内 | 第3节 |

## 6. 裁定

| 项 | 裁定 |
|---|---|
| 本链分帧类型 | HTTP/1.x（PROVEN） |
| 存在游戏消息类型分派 | REFUTED |
| 存在游戏子帧分派 | REFUTED |
| 消息边界类型 | HTTP Content-Length（PROVEN） |
| 游标推进 | libcurl 内部（未逐指令追踪，超出本轮范围） |

说明：本轮未寻找"应用层消息分派器"，因为前提（明文数据流）已被 REFUTED。按停止条件第 1 类（已证明数据指向其他用途），该路径结束。