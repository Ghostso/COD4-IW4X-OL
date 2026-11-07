# 验证实验 B29

## 步骤
1. 用已解出的 plane/brushside 表 + 反推的 brush 边界，生成完整 clipmap
2. 替换 codol_clipmap_coop_train.inc，重跑 probe_world_damage

## 通过判据
trace 落在真实 brush 面上而非 -116

## 失败判据
仍落到 -116 ⇒ brush 表仍不对

## 成本
离线数小时
