# 根因候选

**第一条未闭合边**：本 build 客户端读 memberCount 的代码点。

## 已确认
- memberCount=1 时 dwRoomMatchUber 出现（vtable 0x00DC795C +0x68=0x63C5E0 校验通过）
- memberCount=0 时不出现（10-27 与 10-29 E1 两次）

## 未确认
- 为何是 1 而不是 2/成员数
