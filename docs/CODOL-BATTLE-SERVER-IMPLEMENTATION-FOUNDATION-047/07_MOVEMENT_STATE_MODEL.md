# 07 — 内部移动状态模型

## 1. 已实现

| 能力 | 接口 |
|---|---|
| 角度归一化 | `MovementModel.NormalizeDegrees` |
| 最短角差 | `MovementModel.ShortestDeltaDegrees` |
| 前进/横移方向合成 | `MovementModel.GetWorldDirection` |
| 时间步长积分 | `MovementModel.Integrate` |
| 权威/预测分离 | `GameStateModel.GetOrCreateAuthoritative / GetOrCreatePredicted` |
| 状态时间戳与序号 | `PlayerState.StateTimestampMs / StateSequence` |
| 过期与异常检测 | `MovementModel.CheckState` |

## 2. 与 046 移动资料的关系

- 参考 `CODOL_MOVEMENT_PHYSICS_20261004.md` 的方向结论（前进=yaw，横移=yaw±90，后退=yaw+180）。
- **严格区分**：usercmd 编码 / demo 字段 / 网络 snapshot / 客户端 PlayerState 内存布局 / 预测态 / 服务端权威态。
- `mirror_predicted` 仅作为历史实验参考，**不进入**本工程生产架构。

## 3. 明确未完成

- ❌ 地图 BSP/Clip 碰撞。
- ❌ 重力/跳跃的官方语义复刻。
- ❌ 与最终 CODOL 网络字段的映射。
- ❌ 橡皮筋/预测回发的生产实现。

## 4. 证据等级

所有上述模块为 `PROJECT_IMPLEMENTATION_CONFIRMED`（内部模型 + 离线测试），
**不是** `OFFICIAL_CLIENT_CONFIRMED` 的线上协议。
