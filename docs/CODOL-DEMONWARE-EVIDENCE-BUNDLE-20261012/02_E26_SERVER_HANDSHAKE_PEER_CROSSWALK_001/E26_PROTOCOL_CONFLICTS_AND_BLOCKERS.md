# E26 协议冲突与阻塞审计

## 1. 首个可证实的冲突点

**冲突 C-1（opcode 宽度/取值）**

| 侧 | 地址 | 指令 | 取值 |
|---|---|---|---|
| 客户端 | `0x6AC186/0x6AC1CA/0x6AC240/0x6AC2DC` | `cmp al,0x81 / 0x83 / 0x84 / 0x85` | 8 位，≥0x81 |
| 服务端 | `0x472E7D` + `0x472EA7` + `0x472EB0` | `_MSG_ReadBits(msg,3)`；`cmp edi,4`；`jmp [edi*4+0x7B37A0]` | 3 位，0..4 |

**影响**：同一个分派器不可能同时承载 `0x81`（需 ≥7 位）与 0..4（3 位）。这是两侧消息语义层不可调和的第一个结构性差异。

## 2. 冲突清单

| ID | 冲突 | 证据 | 等级 |
|---|---|---|---|
| C-1 | 客户端消息 opcode 位数 8 vs 3 | `0x6AC186` vs `0x472E7D` | PROVEN |
| C-2 | 握手标签族不同：`CLIENTCHAL`/`BDDATA` vs `challengeResponse %d` | 三服务端样本 0 命中 vs 客户端各 1 命中 | PROVEN |
| C-3 | 阶段字段无同构：客户端 `[+0x5CC]`(0..3) vs 服务端 `[+0x238/0x23C/0x50/0x54/0x78]` | 两侧反汇编 | PROVEN |
| C-4 | 下行编码不同：客户端 Demonware 对象 slot+3 vs 服务端 `0x01..0x06` | E-25 vs `_SV_WriteReliableCommand` | PROVEN |
| C-5 | HMAC/接收计数器仅客户端存在 | `HMAC mismatch`/`Bad recv counter` 服务端 0 命中 | PROVEN |
| C-6 | 传输边界不同：客户端 `[+0xB8]` 队列 + `0xDAB40` 序列化器 vs 服务端 iD-Tech netchan + `_MSG_*` | 两侧 | PROVEN |

## 3. 需重点审计的已知风险（任务书 §D）

| 风险 | 本轮结论 |
|---|---|
| 2697 同时保留 legacy writer 与 2697 writer | **确证存在**（`0x01/0x03/0x05` legacy vs `0x02/0x03/0x04/0x06` 2697）；由 `CODOL2697_PROFILE_WIRE`（VA `0x7B9812`）与`_CODOL_Target2697ArchivesActive` 控制 |
| reliable command `0x02 | long | short(len) | data` 的 opcode 绑定未获客户端独立确认 | 维持 BLOCKED（本目录 E3/E5 已记；本轮未新增客户端证据） |
| 快照/配置字符串有不同 writer/reader | **确证**（服务端多 writer；客户端对应 reader 未闭合） |
| `0x81..0x85` 不得等同 configstring `0x04`/snapshot `0x05/0x06`/demo 子帧 | **已在 E26_OPCODE_DIRECTION_MATRIX §5 明确禁止** |
| 双侧外层封装/传输边界可能不同 | **确证不同**（C-6） |

## 4. 未闭环的结构性阻塞

| ID | 阻塞 | 最小缺失证据 |
|---|---|---|
| B-1 | 客户端 Demonware 握手的服务端对端 | 一个**含** Demonware `bdCore`/`bds` 会话模块的服务端二进制或模块 |
| B-2 | `challengeResponse` 两侧字段序对齐 | 两侧该字段的逐字段读取序列 |
| B-3 | 客户端 0x81 应答的服务端消费者 | 服务端存在 8 位 opcode ≥0x81 的客户端消息分派 |
| B-4 | `client_room2697.dll`/`client_native_loopback.dll` 是否有加密隧道转交 | 两 DLL 的导出/导入与调用方 |

## 5. 不得声明的结论

- 不得声明"协议不兼容"——只声明"2697 专用服务端样本中未找到该握手族消费路径"。
- 不得声明"`0x81..0x85` 是某已知协议阶段"——服务端无对应，客户端仅有字符串线索。
- 不得把 `challengeResponse`/`7F000001` 的共享当作 E-25 那条链的兼容证明。
- 不得把认知完备率当作互操作完成率。
