# Dedicated 双客户端 SD 验证（2026-08-14）

## 运行条件

- 分支：`v3.3.3.3-dedicated`
- 地图：`mp_crash_tropical`
- 模式：`sd`
- 客户端：两个独立 CODOL 进程，共享同一个 room owner 和 dedicated
- 本轮部署包含：`31e6db0`、`dc66a1f`

## 已确认

两客户端均进入 `Playing`，并通过独立 class 响应提交 loadout：

- slot 0：`changeclass_opfor`，服务器队伍为 SC/防守方
- slot 1：`changeclass_marines`，服务器队伍为 TF/攻击方
- `sd.round.configured=true`
- `sd.round.armed=true`
- `attackers=1`、`defenders=1`，双方 alive 均为 `1`
- 炸弹状态为 `available`
- 攻击方 objectives 数量为 2（A/B）
- 防守方 objectives 数量为 3（A/B + 炸弹相关目标）
- 两个 slot 的 `client_think.failure=none`，`rejected_packets=0`
- dedicated 运行约 76 秒时：`connected_clients=2`、`active_clients=2`、`netchan_packets_dropped=0`

服务端日志出现一次低频状态确认：

```text
sd round armed attackers=1 defenders=1 serverTime=50
```

这证明 SD 的分队、回合 armed 门槛、炸弹可用状态和目标快照已经在同一 authoritative server frame 中成立，不再只是单客户端或截图推断。

## 输入探针边界

`CodolTwoClientMatch.py --exercise-forward` 的 native 输入探针本轮返回失败，但失败来自探针自身对客户端内部 `RaiseException/messageBusRemoveObserver` 和 parser hook 的统计，不是服务端 packet reject：

- 两个 CODOL 进程仍存活且响应正常；
- dedicated 没有丢包、拒绝或 think failure；
- 某次探针后一个客户端停止产生新的 usercmd，但仍在 active timeout 内，不能把它记为完整移动通过。

因此本记录只把网络、分队、SD 状态和目标投影标为已验证；真实双方持续移动、拾取炸弹、安放/拆除和客户端 HUD 仍需单独的输入/人工证据。

## 下一步

1. 保持 class replay 不改变 authoritative team，继续查明客户端输入探针为何停止 usercmd。
2. 用能稳定提交 usercmd 的方式验证攻击方拾取炸弹、A/B plant、SC defuse 和 round completion。
3. SD 证据闭合后切换 `mp_nuked + cha`，验证 CHA 出生、复活、计分和语音/模式 UI。

