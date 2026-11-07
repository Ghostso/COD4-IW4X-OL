# 根因候选

**第一条未闭合边**：没有 bullet trace；codol_movement_trace 已有且有测试，但没接进伤害路径。

## 已确认
- 伤害数值层可用（33 damage, 100→67）
- apply_test_hit 无 trace 调用

## 未确认
- 真实射击在线上到底走哪条消息（开火位 bit0 从未出现）
