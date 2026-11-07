# E21 假设台账

| ID | 假设 | 支持证据 | 反证/替代 | 状态 |
|---|---|---|---|---|
| H-E21-01 | 0x6A84E0 是 HMAC/加密载荷对象构造器 | vtable 0xC5B0A4，槽位方法 0xAA8270 明确写该 vtable；字符串引用集中在 0x6AAE70 | 字符串邻近不能单独证明 vtable 方法承担 HMAC 语义 | STRONG_INFERENCE |
| H-E21-02 | 0x6AAE70 是 HMAC 校验/计算函数 | HMAC calculation/HMAC mismatch/Bad recv counter/Bad frame/payload size 四个字符串直接由该函数引用 | 下游 0xA85AD0 进入 .tvm0 边界 | STRONG_INFERENCE |
| H-E21-03 | 类型 1 与类型 2 进入同一路径 | 0x6A9978 汇合，均 mov ebx,9 | 无 | PROVEN |
| H-E21-04 | 该对象属于 Demonware 会话/加密边界 | 与 0x6ABBC0/0x6ABE80 状态机直接相连；字符串含 HMAC/recv counter；无游戏解析候选 | 仍可能有下游游戏消费者经间接分派 | STRONG_INFERENCE |
| H-E21-05 | 该对象直接通向 CODOL 实时游戏解析器 | 无直接证据 | 5 层闭包无候选；vtable 槽位 1-4 无直接调用者 | REFUTED（限定范围） |
| H-E21-06 | 类型码 1/2 的具体协议语义已解 | 无 | 仍为 BLOCKED | BLOCKED |
| H-E21-07 | 0x6A84E0 是单一游戏消息分支 | 34 个静态调用者 | 与单分支假设冲突 | REFUTED |
