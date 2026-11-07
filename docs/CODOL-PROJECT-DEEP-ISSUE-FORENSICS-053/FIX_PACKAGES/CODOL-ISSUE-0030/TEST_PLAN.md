# 验证实验 B30

## 步骤
1. 在 probe_world_damage 里加'目标在障碍后应打不中'的用例
2. 用 codol_movement_trace 从玩家眼位朝目标方向 trace，fraction<1 则不结算

## 通过判据
有遮挡时伤害为 0

## 失败判据
仍扣血 ⇒ 未接 trace

## 成本
离线 1 小时
