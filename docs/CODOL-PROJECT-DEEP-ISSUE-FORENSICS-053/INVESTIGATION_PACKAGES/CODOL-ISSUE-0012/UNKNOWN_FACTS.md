# 未知事实与假设

## 未知

- 当前（memberCount=1）状态下 MyEventHandler 是否存在。
- 若不存在，dwRoomMatchUber 是经由哪条路径创建的。

## 假设矩阵

| ID | 假设 | 状态 |
|---|---|---|
| H0 | memberCount=1 后 MyEventHandler 其实已有实例 | `MUST_TEST_FIRST` |
| H1 | Init 依赖某条大厅应答，该应答未发 | `MEDIUM` |
