# Snapshot 协议证据链

## 1. 结论摘要

**不能为 CODOL 3.9.9.7 建立“服务端 snapshot 构造 ↔ 客户端消费”的闭合对应关系。**

当前存在三条相互分离的证据：

1. **C-3333 / 3.3.3.3 参考链**：Python/C# 实现使用一套 29 个字段索引、index-skip 位流和 4 B netchan 前缀；但权威 trace JSON 不在工作区。
2. **S-2697 / 2.6.9.7 服务端写入链**：`_CODOL2697_WriteSnapshot 0xA4FA0 → _WriteSnapshotReached 0xA4860` 及区域复制常量已定位；客户端消费者未闭合。
3. **C-2697-Rec 客户端候选**：`0x6E060 / 0x6D340` 被列为 delta decode 候选，但没有证明它们消费 S-2697 字节，也没有目标版本 3.9.9.7 样本。

因此当前只能确认“某版本中存在某段实现”，不能确认目标版本端到端兼容。

## 2. 当前正式服务器的 snapshot 发送入口

### 2.1 legacy3333 路径（默认启用）

`src/Engine/ClientLogic.cs`：

- `Update()` 每 tick 调用 `PumpSnapshot`。
- `PumpSnapshot` 入口约在 `ClientLogic.cs:784`。
- 实体保护：若 `s.Player` 不在权威实体表，则跳过下发。
- `MotionSnapshot.Build(...)` 生成 body。
- legacy 外层：`u32 netchan_seq + body`。
- XOR 从 wire offset 8 开始，由 `seq ^ 1` 与客户端可靠命令字节混合。
- 成功后记录 `InputBaselines[seq]`，作为后续 usercmd baseline。

`src/Codol/MotionSnapshot.cs`：

- `Build(...)`：`MotionSnapshot.cs:232`
- `BuildCore(...)`：`MotionSnapshot.cs:252`
- body 初始位置写入：
  - `ack`：u32
  - 一个零字节
  - `serverTime`：u32
  - `first ? 0 : 1`
  - `first ? 8 : 4`
  - 位域 `0,1,220`
- 之后继续写字段索引序列。

**版本归属：** C-3333 的参考实现移植；不是 3.9.9.7 直接证据。

### 2.2 codol2697 路径

`src/Engine/ClientLogic.cs:792-800` 明确拒绝在默认配置下发送 2697 snapshot：

```text
2697 snapshot 帧边界/delta 基准仍是 BLOCKED；
禁止用 legacy 位流冒充目标格式
```

当前 C# 工程没有 2697 snapshot writer。`config/combat_server.cfg` 只有显式实验开关 `enable_experimental_snapshot2697`，默认 0。

因此当前冻结版对 2697 snapshot 采取的是“停止而不伪造”，这是正确的证据纪律。

## 3. S-2697 服务端 snapshot 写入链

证据：`14_SERVER_KNOWLEDGE_ATLAS_001\07_GAMESTATE_CONFIGSTRING_SNAPSHOT.md`。

```text
_CODOL2697_WriteSnapshot            RVA 0xA4FA0
  └─ _CODOL2697_WriteSnapshotReached RVA 0xA4860
       ├─ 初始写 0x00                 RVA 0xA495D
       ├─ 序列 long                   RVA 0xA496E
       ├─ player fields / player arrays
       ├─ animations
       ├─ actors / entities
       ├─ clients
       ├─ glass → 内部 0x06           RVA 0xA4CAF
       ├─ HUD
       ├─ 第二遍 actors / entities
       └─ 区域复制：
            0x728                  RVA 0xA4EBB
            0x2C38                 RVA 0xA4EDF
            count * 0x1F8          RVA 0xA4F3F
            count * 0x13C          RVA 0xA4F61
            count * 0x5C           RVA 0xA4F7D
```

另外：

- `_CODOL2697_PrepareHistory RVA 0xA249D` 是另一调用点。
- 外层终止符由 `_SV_EndClientSnapshot RVA 0x86F7D` 的 `0x87104` 选择：
  - archive inactive → `0x05`
  - archive active → `0x06`
- `A4CAF` 的内部 `0x06` 之后仍继续写 HUD、entities 和区域复制，因此**不能**证明它是整条消息 EOF。

可以确认：

- 服务端写函数和调用链：直接证据（S-2697 指令级）。
- 存在序列 long 和多个区域复制：直接证据。
- `count * 固定大小` 的复制区域：直接证据。
- `count` 是线上实体数量字段：**未证**。
- 区域复制常量与线上字段边界相等：**未证**。
- 内部 `0x06` 是帧边界：**未证**。

## 4. 客户端 snapshot 路径

### 4.1 C-2697-Rec

`14_SERVER_KNOWLEDGE_ATLAS_001\07_GAMESTATE_CONFIGSTRING_SNAPSHOT.md:101`：

- snapshot delta decode：BLOCKED
- 候选函数：`0x6E060`、`0x6D340`
- `0x6D340` 附近有与 `5`、`6` 的比较，但没有把它连接到 S-2697 writer 或实际帧。

`E12_REALTIME_GAMESTATE_CONSUMER_001` 和 `E13/E14` 进一步给出：

- 游戏协议实时消息入口：BLOCKED。
- `0x34FD80(1)` 的 `0x03` 处理属于 demo 路径，字段顺序与服务端 writer 冲突。
- 收包函数到应用层环形缓冲写侧的边未找到。
- 所有独立 `recv/recvfrom` 调用点已经被归到非游戏用途。

因此无法把 `0x6E060/0x6D340` 升格为 snapshot 客户端消费者。

### 4.2 C-3333 参考资料

`REF_LOBBY_KIT\snapshot_diff.py`：

- 索引-skip 解码假设：
  - `0x672067` 读 1 bit：1 = index+1，0 = 后接 4-bit skip 链。
  - `0x672080` 读取 4-bit skip 块。
- 真实字段序列硬编码为：

```text
0, 1, 3, 8, 10, 11, 13, 14, 17, 18, 19, 20,
21, 22, 23, 24, 29, 34, 38, 39, 41, 44, 54, 56,
60, 61, 63, 68, 84
```

- 原始权威 trace 路径：`F:\桌面\ol\新建文件夹\reference\playerstate-motion-trace.json`
- 本工作区 **不存在该 JSON**。
- 现有回归只保存解码后的 29 项索引序列，无法从当前交付独立重放位宽、值和字段语义。

**版本归属：** C-3333。证据等级：交叉印证，不是 3.9.9.7 直接证据。

## 5. 字段级结论（仅对现有参考实现，不是目标版本事实）

| 字段/结构 | 当前实现解释 | 证据来源 | 级别 |
|---|---|---|---|
| netchan 外层 | u32 sequence，后接 body | `MotionSnapshot` + `ClientLogic.PumpSnapshot`；C-3333 参考 | 交叉印证 |
| body ack | u32 | `MotionSnapshot.cs:264` | 交叉印证 |
| body[4] | 固定 `0x00` | `MotionSnapshot.cs:265` | 交叉印证 |
| body[5:9] | serverTime u32 | `MotionSnapshot.cs:266` | 交叉印证 |
| body[9], body[10] | first ? `{0,8}` : `{1,4}` | `MotionSnapshot.cs:267` | 交叉印证 |
| body 位域前缀 | LSB-first，index-skip | C-3333 snapshot_diff；两版 writer | 交叉印证 |
| idx0 | commandTime u32 | C#/Python 实现 | 交叉印证 |
| idx1 | event sequence byte | 实现定义 | 推断 |
| idx3 | weaponTime scalar16 | 实现定义 | 推断 |
| idx8/10/11 | x/z/y float | trace 语义名 + 实现 | 交叉印证 |
| idx13/14 | vy/vx float | trace 语义名 + 实现 | 交叉印证 |
| idx17 | weapon state scalar6 | 实现定义 | 推断 |
| idx18/19/29 | yaw/pitch/roll | trace 语义名 + 实现 | 交叉印证 |
| idx20 | aiming scalar32 | 实现定义 | 推断 |
| idx21-24 | weapon slots present/has/11-bit weapon | 外部 trace 后的修正注释 | 交叉印证，原始 trace 缺失 |
| idx34/38/39/41/44 | movement/weapon parameters | 实现定义 | 推断 |
| idx54/56/60/61/63/68 | constants/flags | 实现定义 | 推断 |
| idx84 | clips/owned/reserve 区段 | 外部 trace 后的修正 | 交叉印证，原始 trace 缺失 |
| idx45/219 | 实验或未知 | 代码和报告 | 未知 |

**不记录为 3.9.9.7 结论：** 上述表中的所有字段宽度、值和索引，因为缺少目标版本文档、函数和抓包。

## 6. 帧边界、实体和 delta

| 项目 | 状态 | 说明 |
|---|---|---|
| 服务端 body 起始头 | C-3333 实现可复核 | 不是 3.9.9.7 直接证据 |
| S-2697 写入调用链 | 直接证据 | 仅服务端二进制 |
| S-2697 帧结束 | BLOCKED | 内部 `0x06` 与外层 `0x05/0x06` 混淆；客户端读取未定位 |
| 实体数量字段 | 未知 | `count*固定大小` 不能证明线上有独立 count 字段 |
| 实体编号 | 未知 | 客户端解码未闭合；当前 C# `EntityId` 只是服务端内部对象字段 |
| 实体状态编码 | 未知 | 只有服务端区域复制和客户端候选函数，没有字段级映射 |
| 基准状态来源 | 未知 | 首帧/历史缓存/PriorSnapshot 的真实指针和字段范围未证 |
| delta 编码 | 未知 | 客户端 delta decode BLOCKED |
| 删除实体 | 未知 | 未找到客户端删除分支或服务端 wire 删除字段 |
| 新增实体 | 未知 | 未找到实体增删边界 |
| 首帧完整状态 | 推断 | 当前 C-3333 参考用 `first` 标志，但目标客户端未确认 |
| 后续增量状态 | 未知/推断 | 代码注释称“省略字段保持旧值”，没有 3.9.9.7 客户端证明 |
| 客户端拒绝条件 | 未知 | 没有找到目标客户端 snapshot 校验分支；不得把 Demonware HMAC/counter 错误套到此层 |

## 7. 服务端与客户端对应表

| 服务端实现 | 对应客户端候选 | 当前对应关系 | 版本归属 | 结论 |
|---|---|---|---|---|
| `MotionSnapshot.Build` legacy | C-3333 外部 motion trace | 29 个索引顺序交叉印证；原始 trace 缺失 | 3.3.3.3 | 不能证明 3.9.9.7 |
| `PumpSnapshot` netchan envelope | 无目标客户端消费者 | 仅实现可复算 | 3.3.3.3 参考 | 不是目标事实 |
| S-2697 `_WriteSnapshot` | C-2697 `0x6E060/0x6D340` | 两条地址链没有直接数据流 | 2.6.9.7 | BLOCKED |
| 当前 C# 2697 实验路径 | 无 | 没有 writer | 当前实现 | 默认禁止发送 |
| 任何 3.9.9.7 实现 | 无 | 无目标样本 | 3.9.9.7 | 不存在 |

## 8. 对六个验收问题的直接回答

1. **3.9.9.7 初始化链最后阶段？** 无已证阶段。
2. **下一阶段缺什么？** 目标版本客户端二进制/运行时身份和目标帧抓包。
3. **snapshot 服务端构造与客户端消费能否建立对应？** 对 3.9.9.7 不能；对 C-3333 只有交叉印证；对 S-2697 与 C-2697 客户端没有建立。
4. **哪些字段已证实？** S-2697 服务端写函数、长序列和区域复制可证；客户端 real-time snapshot 字段、宽度和边界均未知。
5. **是否具备最小协议修改条件？** 不具备。缺少目标版本直接证据，任何改动都可能是版本猜测。
6. **下一项最小工作？** 先取得并验证 3.9.9.7 客户端身份；若没有样本，则停止把其他版本字段写成目标事实。

## 9. 最终裁定

**当前冻结服务器的 snapshot 相关代码只能称为“版本隔离的参考实现”，不能称为“3.9.9.7 snapshot 客户端兼容实现”。**  
尤其是当前默认 legacy snapshot 路径仍来自 3.3.3.3 参考链，2697 路径保持 BLOCKED，3.9.9.7 没有任何直接消费证据。