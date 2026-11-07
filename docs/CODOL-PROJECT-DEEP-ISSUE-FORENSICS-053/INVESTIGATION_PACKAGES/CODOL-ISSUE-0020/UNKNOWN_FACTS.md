# 未知事实与假设

## 未知

- 地图与入口路径在全部历史数据里完全共线，无法分离。
- 客户端在哪个函数决定'不建 socket'。
- 沙箱 vs 本体是否也是共因（区间 B 在同一沙箱里就失败了）。
- `task_params.txt` 里 `6c080800000002000000000000000500000000` 是谁写的、什么语义。

## 假设矩阵

| ID | 假设 | 状态 |
|---|---|---|
| H1 | 所选地图不在客户端可加载集合 ⇒ 不连 | `HIGH_UNPROVEN` |
| H2 | 入口路径（PvE 直接开局 vs 房间内开始）决定是否连接 | `HIGH_UNPROVEN` |
| H3 | 102/7 回全 0 | `EXCLUDED` |
| H4 | memberCount | `EXCLUDED` |
| H5 | mmstart 推 StartGame | `EXCLUDED` |
| H6 | 战斗服没起/端口占用 | `EXCLUDED` |
| H7 | 沙箱 vs 本体 | `EXCLUDED_FOR_REGIME_B` |
