# 验证实验 B22

## 步骤
1. 在 world.c 加断言：map_name 与 clipmap 来源不一致时 WARN
2. 对比 --map coop_train vs --map mp_raid 的 trace 结果

## 通过判据
两种 map 产生不同 trace

## 失败判据
相同 ⇒ 确认无效

## 成本
离线 20 分钟
