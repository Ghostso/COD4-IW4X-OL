# F5 — 最终证据矩阵

> 客户端样本 SHA-256：`353754047dbbfe3afbf6c7d97de3faca785b3d5d5e34a9053c820ee78814d6e1`  
> 静态恢复镜像 SHA-256：`24b4ef2502d3661df178f557192534098c714353cf8c2a00a2ffb26af2bb97e4`  
> ImageBase：`0x400000`；本文 RVA 均为映像 RVA（VA = ImageBase + RVA）。

| 项目 | 服务端证据 | 客户端证据 | 结论 |
|---|---|---|---|
| opcode 0x02 读取点 | E3：`0x8612E` 写 `0x02` | 未定位可复现的消息字节 opcode 读取点 | BLOCKED |
| 0x02 分支 | E3：正返回才写 0x02；0 回退 0x01；负值 Com_Error | 未找到 `cmp ...,2` 或跳转表分支 | BLOCKED |
| 到 0xA2E50 的调用 | 服务端为写侧，无对应客户端调用 | `.text` 0 直接 E8；绝对指针 0；仅 1 条 `.tvm0` 未对齐命中 | BLOCKED |
| 字段布局 | `long + short(length) + data[length]`，length 来自 encoder | `0xA2E50` 读 `long(4) + short(2) + payload`，上限 0x3FC | VERIFIED（字段形状） |
| 消息层级 | 服务端由 `_SV_SendMessageToClient` 进入 Netchan | 客户端未证明 `0xA2E50` 的 `ESI` 对象来自同一内部消息层 | BLOCKED |
| 对照函数 0xA2D90 | 无直接服务端对应 | 与 0xA2E50 同对象布局/读取核心，但后续固定字符串路径 | STATIC-INFERENCE |
| 运行时互通 | 未运行 | 未运行 | NOT-OBSERVED |

## 重要修正

阶段 E 曾把读取核心写成 RVA `0x5AC1D0` 等；本阶段 F4 已确认：

- `0xA2E50`、`0xA2D90` 是 RVA；
- 函数内部 E8 目标 `0x5AC1D0` 是 VA，对应 RVA `0x1AC1D0`；
- 全镜像调用者搜索必须同时按两种形式核对，否则会得到错误的“无调用者/错位入口”结论。

## 最终判定

`opcode 0x02 → 分派 → RVA 0xA2E50 → 字段读取`：**未形成完整静态证据链，标记 BLOCKED。**

可保留的强证据只有：客户端 RVA `0xA2E50` 的字段读取顺序与服务端 `0x02` 的负载字段形状一致。这不足以认定 opcode 一致。
