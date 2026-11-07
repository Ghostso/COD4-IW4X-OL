# 验证实验 B32

## 步骤
1. 在 codol_damage_apply 返回 killed 后调用 codol_mode_player_killed
2. 在 tick 里轮询 codol_mode_respawn_due

## 通过判据
一次对局内出现 spawn→kill→score 日志链

## 失败判据
无变化 ⇒ 接线位置不对

## 成本
离线 2 小时
