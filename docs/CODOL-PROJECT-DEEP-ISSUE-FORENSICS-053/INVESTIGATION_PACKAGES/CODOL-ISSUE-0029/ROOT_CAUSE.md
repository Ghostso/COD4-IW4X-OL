# 根因候选

**第一条未闭合边**：mp_firingrange 的 cbrush_t(36B)/brushBounds(24B)/brushContents(4B) 表位置。

## 已确认
- -116 是常数不是算出来的（18404 帧 z 恒 -116）
- coop 层零地板面
- mp_firingrange 有 1104 朝上平面

## 未确认
- mp_firingrange brush 表布局
