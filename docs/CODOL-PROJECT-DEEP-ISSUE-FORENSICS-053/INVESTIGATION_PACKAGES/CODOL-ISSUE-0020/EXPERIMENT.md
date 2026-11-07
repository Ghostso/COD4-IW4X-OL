# 最小实验：E1 → E2 → E3

## 步骤

1. E1：完全复刻 10-26 22:08 成功条件（沙箱根 + coop_map.txt=coop_train_mp_firingrange + PvE 直接开局 + 不建房）。
2. E2：同 E1，只把地图换成 coop_training_mp_cargoship。
3. E3：同 E1，只把入口换成 BOT 房间。

## 预期结果

E1 应出现 TX_NAT_REPLY；E2/E3 的结果决定归因。

## 判断标准

| 观察 | 结论 |
|---|---|
| E1 RX, E2 RX, E3 零 | 入口路径是根因 (H2) |
| E1 RX, E2 零, E3 RX | 地图是根因 (H1) |
| E1 RX, E2 零, E3 零 | 两者都必要 |
| E1 RX, E2 RX, E3 RX | 都不是；转查 U4/U5/U6 |
| E1 零 | 成功基线已不可复现，先修环境 |

## 前置条件

- 提权 agent 在线（CODOLServer/logs/elevated_agent.json）
- run_codol_001/run_frozen_chain_once.py --authorize-next-launch
- 沙箱根仍存在，或明确改用本体并在结论中标注 D4 也变成变量
- 用户需在 UI 上走 PvE 剧情入口（不是 BOT 房间）

## 风险/注意

需要启动官方客户端，属于需授权操作；本审计未执行。
