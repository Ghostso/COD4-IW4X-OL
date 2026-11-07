# E6 — 阶段 E 之后的下一步静态任务

> 阶段 E · CODOL 2697 · 仅静态分析。本计划不授权启动游戏或服务端。

## 1. 直接回答

### 1. 三条协议路径中，哪一条已形成最完整的双向静态证据链？

当前最完整的是 **reliable command 路径**，但仍不是已验证的完整双向链。

- 服务端 `_SV_WriteReliableCommand` RVA `0x8612E` 直接选择 `0x02` 或 `0x01`；新格式为 `long + short(length) + data[length]`。
- 客户端候选 RVA `0xA2E50` 直接读取 `long + short + payload`，并有 `0x3FC` 上限。
- 缺失环节是客户端 `0x02` opcode 分派和 `0xA2E50` 的调用者。在该调用链闭合前，opcode 绑定只能是 `STATIC-INFERENCE`，不是 `VERIFIED`。
- Gamestate 有强服务端门控，但没有已验证的客户端 `0x03` parser；snapshot 有强服务端编码证据，但客户端 delta/EOF 未闭合。因此 reliable command 只是相对最完整。

### 2. 哪些字段或 opcode 已能确认两端一致，哪些仍然未知？

服务端已确认的编码事实：

- 新 reliable `0x02`：`long(sequence/parameter) + short(length) + payload[length]`。
- 回退 reliable `0x01`：`long(sequence/parameter) + command string`。字段顺序和写入调用为 `VERIFIED`；NUL 终止细节来自 helper 名称，标 `STATIC-INFERENCE`。
- snapshot 内部 `0x06` 写入点 `0xA4CAF`；外层 `0x05/0x06` 选择点 `0x87104`。
- 新 gamestate/configstrings 路径使用 `0x03`、`0x04` 和尾部 `0x06`；legacy writer 使用 `0x02`、`0x03` 和 `0x05`。

客户端已确认的事实：

- 候选 `0xA2E50` 读取 `long + short + payload`，并有 `0x3FC` 边界。
- 它的字段形状与服务端 `0x02` 负载形状匹配。

仍然未知：

- 客户端 `0x02` opcode 分派；没有可验证 `cmp`/switch 或调用者。
- 客户端 `0x06` 的语义，是 EOF、段结束还是其他 token。
- 客户端 `0x03` gamestate parser 和状态转换。
- 客户端 `0x04` configstring consumer。
- snapshot 子记录边界和外层 Msg 分帧。
- 恢复静态客户端镜像与运行时映射的等价性。

### 3. 当前最主要的兼容性障碍是什么？

主要障碍不是已经证明的字节冲突，而是 TenProtect 包装/恢复镜像中的 **客户端分派链未闭合**：

1. 打包客户端无法直接完整反汇编。
2. 恢复镜像是静态恢复，运行时映射等价性为 `NOT-OBSERVED`。
3. 尚未定位客户端 `0x02` opcode 分支、`0x03` gamestate 分支或 `0x06` 终止分支。
4. 服务端新 `0x03/0x04/0x06` 和 `0x02` 路径仅在目标/archive 控制条件下发出，运行时实际激活状态未观测。

因此当前正确状态是 **静态字段形状匹配，但客户端分派未闭合**；不能写成已证实不兼容，也不能写成已证实兼容。

### 4. 下一步最小、最有价值的静态验证任务是什么？

最有价值的下一任务是：**在不运行任何程序的前提下，闭合客户端 RVA `0xA2E50` 的调用者/分派链。**

1. 搜索 `.rdata` 与 `.data` 中所有真实映射到 VA `0x4A2E50` 的函数指针/vtable 引用，排除节相对伪 RVA。
2. 恢复周边对象/vtable 布局，定位在调用 `0xA2E50` 前读取服务端消息 opcode 的方法。
3. 检查该调用者是否比较 `0x02`，以及是否同时存在 `0x01`、`0x03`、`0x04`、`0x05/0x06` 分支。
4. 记录精确文件偏移、RVA、指令上下文和替代解释。
5. 如果仍找不到调用者，将调用链标为 `BLOCKED`；不得把字段形状相似提升为 opcode 一致。

## 2. 按优先级排列的工作队列

| 优先级 | 任务 | 预期价值 | 成本 | 成功条件 |
|---|---|---|---|---|
| P0 | 寻找客户端 `0xA2E50` 的间接/vtable 调用者并恢复 opcode 比较 | 高 | 低-中 | 真实调用者在调用 `long+short+payload` parser 前读取 opcode `0x02`。 |
| P0 | 对客户端 `0xA2D90` 使用同样的间接调用方法 | 高 | 低-中 | 确定它是另一条 reliable sequence 路径还是其他消息路径。 |
| P1 | 在修正映射后的 `.tvm0` 和间接跳转表中搜索 `0x01..0x06` 分派 switch | 高 | 中 | 找到映射正确的可复现 switch/跳转表。 |
| P1 | 围绕 `0xA2660`、`gamestateupdate %d` 引用闭合调用者/状态图 | 中-高 | 中 | 确定它是否为网络 gamestate consumer。 |
| P1 | 围绕 `0x6E060`、`0x6D340` 闭合 delta/snapshot parser 调用者 | 中-高 | 中 | 把 delta parser 连接到内部消息游标，并定位 `0x05/0x06` 处理。 |
| P2 | 检查 `client_room2697.dll`、`client_native_loopback.dll` 的消息/opcode 桥接 | 中 | 中 | 证明直接 opcode 或游标桥接。 |
| P2 | 重建服务端 `_SV_EndClientSnapshot` 的外层 Msg 分帧，仅做形状对照 | 中 | 中 | 证明缓冲区边界，但不宣称运行时兼容。 |

## 3. 停止条件与报告规则

- 在真正观测运行时交互之前，所有端到端兼容结论保持 `NOT-OBSERVED`。
- 不得把 `0x400000 + 节相对伪 RVA` 映射作为证据；必须使用真实节虚拟地址和文件偏移。
- 每项匹配必须记录客户端 SHA-256、精确 RVA/文件偏移、指令上下文和至少一种替代解释。
- 搜索未命中只能写“在所述搜索范围内未找到”，不能写“不存在”。
- 不重复通用文件/字符串扫描，不重生成阶段 A-D 报告。
- 不启动、不注入、不补丁、不编译游戏、服务端或恢复镜像。
