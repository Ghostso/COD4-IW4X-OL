# Usercmd 拒绝诊断（2026-08-14）

## 现象

双客户端 Crash/SD 测试可以进入 `Playing`，服务端仍持续发送 snapshot，但运行约十秒后某个客户端的有效包停止，`dropped` 持续增长。旧进程控制接口在附加时已退出，不能把该结果解释为服务端崩溃。

## 现有证据

- `parseClientCommands()` 对同一 packet 内的 commandTime 保持严格递增校验。
- packet 被拒绝时，`Netchan_Process()` 不提交 netchan incoming sequence，也不会把其中的 usercmd 放入服务端队列。
- `SV_PacketEvent()` 的 `defaultUserCmd` 优先取客户端确认的 snapshot history，缺失时才回退到当前 world frame。
- 周期 runtime 日志只显示累计 `packets/dropped/snapshots`，无法判断最后一次拒绝属于旧 command、确认越界还是解码失败。

## 本轮改动

`Appmain.cpp` 新增按 client、按拒绝状态去重的 `client-packet-reject` 日志，包含 sequence、message/reliable acknowledge、decoded command 长度和 reason。该改动是诊断用，不改变接受/拒绝语义；后续应先用新 DLL 重启双客户端，再根据具体 reason 对照 CODOL、BO1 和 Ghosts 的 netchan/usercmd 基线决定正式修复。

## 已确认结论

新 DLL 运行后，失败包反复报告 `rejected_cmd=8100 baseline_cmd=8100`，且两端 ACK 固定、`dropped` 持续增长。相同 commandTime 是客户端 move window 中的重复旧 command，不是回绕或随机解码。COD 的 `SV_UserMove` 语义应先接受并推进 netchan/ACK，再由服务端 command watermark 过滤旧/重复项；拒绝整包会让客户端永久重传同一窗口。

源码现已移除 packet 内严格递增的整包拒绝，保留 `SV_PacketEvent()` 的 `lastQueuedUserCmdTime` 过滤。单测改为验证重复 commandTime 可接受、由 SV 队列水位负责丢弃。

新一轮双客户端 Crash/SD 已观察到：

- 两客户端进入 `Playing`；
- `runtime clients=2 active=2`；
- `packets=4091 dropped=0 snapshots=1848`；
- 两端 message/reliable acknowledge 持续推进；
- 观察窗口内没有新的 `client-packet-reject`。

随后双端分别执行 1 秒 native `+forward/-forward`：两端客户端 parser 都为 `accepted_packet_count>0`、`rejected_packet_count=0`、无 overflow/`Com_Error`，进程保持存活；服务端继续推进到 `packets=14659 dropped=0 snapshots=2972`。这只证明网络和基础前进输入在该窗口内没有重新触发重传闭环，仍不覆盖全部姿态、武器和障碍物行为。

这证明本轮修复解决了已确认的 netchan 重传闭环，但还不等于移动、武器和长时双端 gameplay 已全部通过。

## 下一步判定

1. 继续观察新语义下的双端 commandTime、snapshot、client-think 和进程存活，确认没有新的 native Pmove 或 snapshot 错误。
2. 若 reason 是可靠确认或 packet sequence，先检查客户端是否仍在重传旧 packet，不直接放宽服务端校验。
3. 只有协议证据闭合后才修改行为，并同步更新非递增 command 的单元测试。

当前构建未部署到正在运行的 PID；不能据此宣称移动回滚已修复。
