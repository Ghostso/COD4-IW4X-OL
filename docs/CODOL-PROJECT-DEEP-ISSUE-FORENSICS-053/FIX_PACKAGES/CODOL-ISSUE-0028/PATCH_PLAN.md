# 修改计划

**方案A**：方案A：把 jump 分支并入 process_usercmd_dt / move_in_world，并正确维护 walking。

**方案B**：方案B：改用 trace 结果决定 on_ground，再据 on_ground 允许跳跃。

## 影响

垂直移动目前完全依赖客户端预测；服务端永远认为玩家在地面。
