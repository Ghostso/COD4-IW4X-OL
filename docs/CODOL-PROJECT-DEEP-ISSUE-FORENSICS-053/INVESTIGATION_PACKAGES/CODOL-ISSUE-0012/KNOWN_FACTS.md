# 已证明的事实

- memberCount=0 的那次运行里，vtable 0x00DC78F0 零实例（EARLIEST_20261027_123806）。
- memberCount=1 之后 dwRoomMatchUber（0x00DC795C）确实出现了（EARLIEST2_20261027_132645）。
- 按原因果图，MyEventHandler 缺失本应切断 dwRoomMatchUber 的创建 —— 但后者出现了。
- `0x63E5D6` 有无条件写 `[0x82E1514]`，在分配之前；实测为 0 ⇒ 函数体当时没跑。
