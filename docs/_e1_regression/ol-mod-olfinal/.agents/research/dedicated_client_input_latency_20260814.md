# Dedicated 双客户端输入延迟与掉线记录

## 现象

2026-08-14 的双客户端 Crash/SD 实机运行中，用户观察到操作指令至少有约 5 秒延迟，其中一个客户端弹错并掉线。

## 已确认时间线

- client instance 1：PID `42736`，userId `01100001DEADC0DE`，server slot `1`，XUID `76561201696194782`。
- client instance 2：PID `50436`，userId `01100001DEADC0DF`，server slot `0`，XUID `76561201696194783`。
- `08:54:45`：backend 的 `AlwaysofflineRe.Localnet32.log` 出现 slot 1 对应的 `service 71/task 7 clientDisconnect`。
- 在此之前 dedicated 日志一直是 `clients=2 active=2`，`netchan_packets_dropped=0`，`socketError=0`，并持续发送 snapshot。
- `08:58:39`：dedicated 才因 slot 1 的 `last_packet` 超过 active timeout 而清理它；不是服务器主动拒绝或 socket 错误。
- slot 1 清理后 slot 0 仍持续收到 snapshot，直到它也因没有上行包在 `09:02:39` 超时。

因此当前证据更支持：客户端先进入 backend/session disconnect 或异常状态，随后停止发送 game packet/usercmd；dedicated 只是按正常超时策略清理。不能把这次现象归因于 snapshot writer、packet drop 或 server think reject。

## 重要干扰源

本轮使用了 `CodolTwoClientMatch.py --exercise-forward`。旧版 `CodolClientInput.py` 在每个 `Com_Frame` 中执行高频 native 内存采样，并同时挂载 `parseSnapshot`、`parsePlayerState`、`CL_ParseServerMessage` 和 packet-event 钩子。采样还会持续向 Frida 宿主发送大块 opaque playerstate 数据并周期性落盘。该路径运行在客户端主线程附近，足以造成输入延迟、消息队列积压或客户端自身进入异常状态。

这不是 gameplay server 的正式实现路径，不能用它的 parser 统计直接判定真实游戏协议失败。

## 已做的低干扰修正

- `CodolClientInput.py` 增加 `--no-parser-trace`；默认工具行为仍保留解析钩子，便于专门的协议证据采集。
- `CodolTwoClientMatch.py --exercise-forward` 改为低干扰模式：不挂 parser/packet 钩子，采样周期默认 `0.25s`，并把是否挂钩写入 `parser_trace` 字段。
- 只有显式启用 parser trace 时，双客户端工具才把 accepted/rejected/overflow 计数作为通过条件。

## 下一次验证边界

1. 重新启动两个客户端和 dedicated，不使用 `--exercise-forward`，先观察至少 5 分钟：两端上行包、`last_packet`、message/reliable ack 是否持续增长。
2. 再用新的低干扰 `--exercise-forward` 做短时 forward，比较是否仍出现约 5 秒延迟或停止上行。
3. 若不使用探针仍掉线，继续查 backend `clientDisconnect` 与客户端网络/会话状态；若只在旧探针出现，则问题属于测试工具干扰，不应修改 server timeout 或伪造快照。

## 未解决

- 错误弹窗中的 `9025` 尚未建立到确定的客户端错误枚举映射。
- 尚无一次不挂任何 Frida probe、双客户端连续 5 分钟的自然输入证据。
- 在上述证据闭合前，不调整 active timeout，也不把掉线当作 gameplay 协议失败。

## 后续实机中发现的协议缺口

无探针自然运行约 7 分钟后，日志首次出现高位序号，例如
`sequence=0x80001f28`，并同时出现 `client reliable acknowledge exceeds the
server sequence`。这不是普通 ACK 过大，而是 COD netchan 的 bit31 分片标志
被旧解析器当成普通 13-byte client header，导致 fragment offset/length 被误读
成 `messageAcknowledge` 和 `reliableAcknowledge`。Kisak/BO 的原生链路会先按
`sequence|0x80000000 + fragmentStart + fragmentLength` 重组，再解析普通包。

当前源码已加入每客户端 fragment buffer、连续 offset 校验和 `FragmentPending`
状态；完整包才会推进 ACK、usercmd 和 snapshot 状态，分片期间只刷新活动时间。
这部分已通过固定 fragment 回归测试，尚未完成部署后的长时实机复验。
