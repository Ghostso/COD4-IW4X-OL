# E21 间接分派审计

## 已确认的虚表

对象构造器 `0x6A84E0` 写入 vtable VA `0xC5B0A4`（RVA `0x85B0A4`，.rdata）。

槽位内容：

| 槽位 | VA | RVA |
|---|---|---|
| 0 | 0xAA8570 | 0x6A8570 |
| 1 | 0xAA85A0 | 0x6A85A0 |
| 2 | 0xAA83C0 | 0x6A83C0 |
| 3 | 0xAA82E0 | 0x6A82E0 |
| 4 | 0xAA88C0 | 0x6A88C0 |
| 5 | 0xAA8720 | 0x6A8720 |

`0x85B0A4+0x18` 起为 `0xFFFFFFFF` 与 `0x474`。随后 `0x85B0EC` 为字符串 `HMAC mismatch`，`0x85B0FC` 为 `HMAC calculation`，`0x85B110` 为 `Bad recv counter`。

## 直接调用者

| 方法 | 直接调用者 |
|---|---|
| 0xAA8570 | 0x6A8570 |
| 0xAA85A0 | 无静态直接调用者 |
| 0xAA83C0 | 无 |
| 0xAA82E0 | 无 |
| 0xAA88C0 | 无 |
| 0xAA8720 | 0x68AC90 |

无调用者的槽位只能由虚表分派调用。这是本轮未闭合的主要间接边界。

## 混淆边界

`0x6AAC80` 附近存在不连续控制流；`0xAAB1C0` 起为 `.tvm0`/VM 混淆代码，线性 capstone 输出不可作为语义证据。

## 裁定

- vtable 布局与槽位：PROVEN
- HMAC 字符串与该对象 vtable 邻近：PROVEN
- 字符串 `HMAC calculation` 等由函数 `0x6AAE70` 直接引用：PROVEN
- vtable 槽位的具体消费者：BLOCKED（间接边界 + .tvm0）
- 对象作为游戏消息消费者的证据：未找到
