# 根因候选

**第一条未闭合边**：move_in_world 里是否有等价 jump 逻辑（需读 world/player.c）——即便有，walking 也不会被维护。

## 已确认
- codol_pmove_single 在 src/ 内零调用者、零取地址
- process_usercmd_dt 里 on_ground 恒 true

## 未确认
- 客户端跳跃时服务端的实际表现（无实机）
