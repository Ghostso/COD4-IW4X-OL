# Dedicated 双客户端链路闭环

## 结论

2026-08-14 的本地运行已确认两个真实 CODOL 客户端可以同时进入同一局 dedicated：

- dedicated 日志出现两个独立 client slot，且两端均为 `state=3`、`gamestate_stage=6`、`gameplay=1`。
- 运行状态从 `runtime clients=2 active=0` 过渡到 `runtime clients=2 active=2`。
- `snapshots` 持续增长，说明服务端主动快照、客户端 ACK 和加密 netchan 已形成稳定闭环。
- 两个客户端使用不同的 authenticated XUID 和显示名，未复制首玩家身份。

## 修复边界

本轮修复的是 dedicated 传输和生命周期问题：dedicated 角色绕过客户端 Winsock 重定向、重复配置 session 时保留已有 DTLS peer，并补充了握手和运行状态诊断。它不代表 SD、伤害、武器命中、实体破坏或完整多人玩法已经完成。

## 自动化约束

`tools/runtime/CodolTwoClientMatch.py` 现在把“两个连接建立”和“可用 gameplay 会话”分开判断，只有同时满足 `clients=2`、`active>=2` 且已发送至少一个 snapshot 才报告成功。超时会输出最后观察到的 active 状态，便于区分连接失败和加载阶段尚未完成。

## 2026-08-14 clean 重跑补充

在位置投影工具提交后，重启两次 clean dedicated + 双客户端组合验证多人入口。两次运行都得到相同边界：两个客户端均完成 frontend、QuickMatch 和 ready，`ol-room-owner.log` 均记录两个不同 XUID、两个 bridge、`members=2 ready=2` 并冻结；但 dedicated 只记录一个 `connectionless connected`，随后始终为 `runtime clients=1 active=1`。因此当前证据可以排除 room roster、ready/freeze、端口身份和 dedicated UDP slot 分配是首要原因。

本轮补齐了 `MatchmakingService` 的 session 生命周期广播：`createSession`、`updateSession`、`updatePlayers` 现在都会发布当前会话，`deleteSession` 会发布 terminate；对应 backend 单测和 release 构建均通过并已部署。部署后的两次实跑仍保持上述 `1/2` 边界，说明这是真实缺口但不是非 owner 进入局内的完整修复。

下一步应沿非 owner 客户端的 Matchmaking allocation/find-session 回包继续取证，恢复“房间 owner 只提交一次 booking，已接受的 authoritative session 结果由每个成员各自收到”的正式链路。不要在客户端脚本或 dedicated 端复制 owner 状态、硬编码第二个连接或绕过 roster 条件。

## 后续

以这条稳定的双端快照链为基础，继续补 gameplay owner 和模式状态；出现玩法回滚时优先检查 authoritative player/entity state 与 snapshot 投影，不重新引入客户端 UDP 或房间层特判。
