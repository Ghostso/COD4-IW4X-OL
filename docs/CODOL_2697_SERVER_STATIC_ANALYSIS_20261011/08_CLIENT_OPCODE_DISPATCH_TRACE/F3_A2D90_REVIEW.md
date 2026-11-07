# F3 — 对照函数 RVA 0xA2D90 复核

> 客户端样本 SHA-256：`353754047dbbfe3afbf6c7d97de3faca785b3d5d5e34a9053c820ee78814d6e1`  
> 静态恢复镜像 SHA-256：`24b4ef2502d3661df178f557192534098c714353cf8c2a00a2ffb26af2bb97e4`  
> ImageBase：`0x400000`；本文地址基准：`0xA2E50`/`0xA2D90` 为映像 RVA，函数内部 E8 目标为 VA（VA - ImageBase = RVA）。

> RVA `0xA2D90`；VA `0x4A2D90`；文件偏移 `0xA2190`。

## 1. 函数边界

RVA `0xA2D90`–`0xA2E42`，下一函数入口为 `0xA2E50`。入口同样为 `55 8B EC 81 EC 08 04 00 00`，并有相同的 `__security_cookie` 结构。

## 2. 与 0xA2E50 的关系

| 项目 | 0xA2D90 | 0xA2E50 |
|---|---|---|
| 消息对象布局 | `[esi+0x14/+0x18/+0x1c]` | 相同 |
| 缓冲区边界检查 | 相同模式 | 相同模式 |
| 读取核心 | `0x5AC1D0`（VA）→ RVA `0x1AC1D0` | 相同 |
| 字段 | 先读 4 字节 `EBX` | 先读 4 字节 `EBX` |
| 后续 | 固定 `0x400` 字节字符串路径，调用 `0xDE5D3F6` 和 `0xB4A600` | 读 short length（≤0x3FC），调用 `0x5ACB00` 复制 payload |
| 全局槽 | `[0x1A89500] xor 0x2B90AC87`，`+0x4014C` / `+0x40154 + (idx<<10)` | 相同 |
| 错误/报错 | 没有 len+payload 上限路径 | `0xCB83E0/0xCB83E8` 报错字符串 |

**结论：两者属于同一“消息 4 字节索引 + 全局槽”家族，读序和对象布局同族是 VERIFIED；但这不代表它们承担同一协议职责。** 0xA2D90 的固定字符串路径与 0xA2E50 的 short-length payload 路径不同，不能因地址相邻就认定同义。

## 3. 调用者

与 0xA2E50 相同：全镜像绝对指针 0 命中；`.text` 内 E8/E9 0 命中；只有一条 `.tvm0` 未对齐字节命中（RVA `0xD97BF7E`），不能作为调用者。

**F3：0xA2D90 不能为 opcode 0x02 提供独立证据。其代码形状与 0xA2E50 同族为 STATIC-INFERENCE，调用者链为 BLOCKED。**
