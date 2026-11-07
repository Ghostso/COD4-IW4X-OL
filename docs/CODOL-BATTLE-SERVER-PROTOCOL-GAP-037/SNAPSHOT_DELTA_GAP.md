# SNAPSHOT_DELTA_GAP — 快照、增量与实体同步

**目标：** CODOL 3.19.26.22 / Build 1649370  
**主要证据：** 034 `SNAPSHOT_FORMAT_AND_DELTA.md` 与原始输出。  
**纪律：** 未找到目标版本直接证据的字段一律 `UNKNOWN`。

---

## 1. 当前确定的只有“结构存在”

| 项 | 证据 | 状态 |
|---|---|---|
| 增量字段类型分派器 `0x5F830` | 034 序言 + 反汇编 | `CLIENT_CONFIRMED` |
| 类型表 A：索引 `0x460550`，314 项 | 034 字节统计 | `CLIENT_CONFIRMED` |
| 类型表 A：目标表 `0x46040C`，81 分支，默认 `0x50` | 034 字节统计 | `CLIENT_CONFIRMED` |
| 类型表 B：索引 `0x4606E4`，136 项 | 034 字节统计 | `CLIENT_CONFIRMED` |
| 类型表 B：目标表 `0x46068C`，22 分支，默认 `0x15` | 034 字节统计 | `CLIENT_CONFIRMED` |
| 调用链 `0x5F830 ← 0x208380 ← 0x1FF820 ← 0x20059B` | 034 调用解析 | `CLIENT_CONFIRMED`（结构） |
| `0x1FF820` 读取 `[ebx+0xa0]/[ebx+0xa4]/[ebx+0xf0]` | 034 反汇编 | `CLIENT_CONFIRMED`（读取事实） |

**注意：** 表规模、默认项、分支数只证明“存在映射结构”，不证明字段语义或位宽。

---

## 2. 仍然 UNKNOWN 的核心项

| 缺口 | 状态 | 为什么不能推断 |
|---|---|---|
| snapshot 帧起点 | `UNKNOWN` | 未定位 frame type / 命令字分派 |
| snapshot 帧终点 | `UNKNOWN` | 未找到终止符/长度绑定 |
| 序列号读取与回绕 | `UNKNOWN` | 未定位序号消费点 |
| delta 基线 | `UNKNOWN` | 未定位上一帧指针/历史缓存 |
| first 语义 | `UNKNOWN` | 只在旧协议实现中出现 |
| 实体列表编码与终止 | `UNKNOWN` | 未定位实体计数/哨兵 |
| 实体新增 | `UNKNOWN` | 未定位新实体分支 |
| 实体更新 | `UNKNOWN` | 类型分派分支语义未知 |
| 实体删除 | `UNKNOWN` | 未定位删除分支 |
| entityId ↔ 表索引 | `UNKNOWN` | 未定位乘/移位换算与边界检查 |
| 字段位宽 | `UNKNOWN` | 类型表只给分支索引，不给读位数 |
| 字段默认值 | `UNKNOWN` | 未定位默认路径 |
| 字段位序 | `UNKNOWN` | 未定位位流读取器 |
| 丢包/乱序/重复 | `UNKNOWN` | 未定位序号异常拒绝分支 |
| 基线失效 | `UNKNOWN` | 未定位拒绝语义 |
| 玩家状态 vs 实体状态 | `UNKNOWN` | 未判定是否两条独立路径 |

---

## 3. 已排除的错误方向

034 明确否定了以下 TASK-009 地址可用于目标版本：

- `parseSnapshot 0x46D170`：非函数入口。
- `parsePacketEntities/Clients/Aux`：非入口。
- `readDeltaField/Entity/Index`：非入口。
- `readBit 0x400C370`：超出文件范围。
- 整体位移假设：最佳位移仅 7/18 命中。

**结论：** 不得沿用 TASK-009 的 snapshot 函数名或 RVA。

---

## 4. 现有服务器实现与目标证据的对照

| 服务器实现 | 目标证据 | 判定 |
|---|---|---|
| `MotionSnapshot.BuildCore`：`ack(u32)+0x00+serverTime(u32)+first?{0,8}:{1,4}+位域` | 无对应目标证据 | 旧协议；不得称目标格式 |
| `ExpectedIndexOrder` 29 项硬编码 | 无对应目标证据 | 暂缓 |
| `PumpSnapshot`：`u32 netchan_seq + body`，XOR 自 wire offset 8 | 无对应目标证据 | 暂缓 |
| `InputBaselines[seq]` 作为 usercmd 基线 | 目标侧未定位 | 暂缓 |
| 2697 snapshot 默认禁用 | 034 同样未闭合 | 一致；保持禁用 |

---

## 5. 最有价值的下一步静态切入点

034 已给出明确线索：

1. `0x1FF820` 的 `[ebx+0xa0]`、`[ebx+0xa4]`、`[ebx+0xf0]`。
2. 调用链上的 `0x20059B` 所在函数尚未定位。
3. `0x5F830` 的类型表和默认项已经可用。

**建议：** 不要先从 snapshot 位流入口“猜”；应先从 `0x1FF820` 向上定位调用者，再向下绑定消息类型与帧边界。该工作与 `NEXT_TASK_RECOMMENDATION.md` 推荐一致。

---

## 6. 离线测试边界

034 的 `OFFLINE_TEST_VECTORS.md` 已给出可做的结构级测试：

- TV-08：表 A 边界 `> 0x139` 拒绝，遍历断言 223 项默认。
- TV-09：表 B 边界 `> 0x87` 拒绝，遍历断言 115 项默认。
- 任何“字段位宽”“delta 正确性”“实体编码正确性”测试**当前都不能做**，因为没有目标证据。

**不得**用合成数据证明兼容性。
