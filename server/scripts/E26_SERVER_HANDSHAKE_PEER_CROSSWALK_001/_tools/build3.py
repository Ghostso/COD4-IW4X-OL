# -*- coding: utf-8 -*-
from pathlib import Path
OUT=Path(r"D:\BaiduNetdiskDownload\使命召唤OL\E26_SERVER_HANDSHAKE_PEER_CROSSWALK_001")
files={}

files["E26_OPCODE_DIRECTION_MATRIX.md"]=r'''# E26 消息码方向矩阵

## 1. 客户端侧（E-21..E-25 已证）

客户端会话分派器 `0x6AC0C0` 以 `[esi+0x5CC]`（阶段）与 `[ebp-0xE]`（报文码）二级分派：

| 阶段 `[+0x5CC]` | 报文码 | 处理函数 | 方向证据 |
|---|---|---|---|
| 1 | `0x81` | `0x6AB310`（应答组装 + 入队 + 置阶段 2） | 无直接收发 API 边；`CLIENTCHAL` 字符串线索 |
| 1 | `0x04` | `0x6AAA770`（置 `[+0xC8]=4` 失败） | — |
| 2 | `0x83` | `0x6AB260`（置阶段 3、写 `[+0x5D0]=3`） | 接收计数器被写 |
| 2 | `0x84` | `0x6A9690` | 返回后无条件 `0x6AAA770` |
| 3 | `0x85` | `0x6AAE70`（HMAC + 接收计数器校验） | `Bad recv counter`/`HMAC mismatch` → 偏入站 |
| 3 | `0x84` | `0x6A9690` | 同上 |

E-25 追加：阶段 1 应答经 `0x6AB310 → 0xDAB40 序列化器 → 0x6AA230 入队 → 0x6AA7B0 泵 → 0x783B50 → 0x784E40 → ws2_32!send`（**出站**，PROVEN 五层）。

## 2. 服务端侧（本轮新证）

服务端**客户端→服务端**消息用 **3 位 opcode（0..4）**（`_SV_ExecuteClientMessage` `0x472E77..0x472EB0`）：

| opcode | 处理 | 方向 |
|---|---|---|
| 0 | `_SV_UserMove(...,1)`（`0x473104`） | 入站（客户端移动包） |
| 1 | `_SV_UserMove(...,0)`（`0x47311B`） | 入站 |
| 2 | `_SV_ClientCommand`（`0x473132`） | 入站（客户端命令/字符串） |
| 3 | 无操作返回（`0x47319A`） | — |
| 4 | 拒绝/重读（`0x472E6F`） | — |

服务端**服务端→客户端** servercommand 用：

| 值 | 编码 | 说明 |
|---|---|---|
| `0x01` | `long + string` | legacy serverCommand |
| `0x02` | `long + short(len) + data[len]` | 2697 reliable |
| `0x03` | 2697 gamestate | 2697 通道 |
| `0x04` | 2697 configstring | 2697 通道 |
| `0x05` | legacy EOF | legacy 通道 |
| `0x06` | 2697 EOF/终止 | 2697 通道 |

（来源：本目录 04_PROTOCOL_PATHS / E3 报告；`_SV_WriteReliableCommand` RVA `0x8612E`、`_CODOL2697_WriteGamestate` RVA `0xA21B8`、`_CODOL2697_WriteConfigstrings` RVA `0xA0468`、`_SV_EndClientSnapshot` RVA `0x86F7D`。）

## 3. 两侧对照（判定）

| 维度 | 客户端 | 服务端 | 判定 |
|---|---|---|---|
| 客户端消息 opcode 宽度 | 8 位值（`cmp al,0x81/0x83/0x84/0x85`） | **3 位（0..4）** | **明确冲突** |
| 客户端消息 opcode 取值 | `0x81/0x04/0x83/0x84/0x85` | `0..4` | **明确冲突** |
| 阶段字段 | `[+0x5CC]` = 0/1/2/3 | `_CODOL_HandshakeInit`/`_HandshakeCookie` 用 `[obj+0x238/0x23C/0x50/0x54/0x78]` | **无同构字段** |
| 出站 servercommand | Demonware 对象 slot+3（`0xA87D50`） | `0x01/0x02/0x03/0x04/0x05/0x06` | **无同构** |
| 握手标签 | `CLIENTCHAL`、`BDDATA` | `challengeResponse %d` | **不同族** |
| 共享签名 | `7F 00 00 01`（客户端 2 处） | `7F 00 00 01`（服务端 6 处） | **共享（PROVEN）** |
| 共享标签 | `challengeResponse` | `challengeResponse %d` | **共享（PROVEN）** |

## 4. 方向判定汇总

| 消息 | 方向 | 依据 | 等级 |
|---|---|---|---|
| 客户端 `0x81` 应答 | 出站（客户端→服务端） | E-25 五层链至 `ws2_32!send` | PROVEN |
| 客户端 `0x85` | 入站（服务端→客户端） | `[+0x5D0]` 接收计数器递增 + `Bad recv counter` | INFERRED（强） |
| 服务端 opcode 0/1 | 入站（客户端→服务端） | `_SV_UserMove` 语义 + 3 位读 | PROVEN |
| 服务端 opcode 2 | 入站 | `_SV_ClientCommand` | PROVEN |
| 服务端 `0x02/0x03/0x04` | 出站 | `_SV_WriteReliableCommand`/`_WriteGamestate` | PROVEN |
| 服务端 `challengeResponse` | 出站（服务端响应） | `_CODOL_WriteChallengeResponse` → `0x6DD83` 发送 | PROVEN |

## 5. 禁止的等同

- **`0x81..0x85` ≠ 服务端 `0x01..0x06` servercommand**：前者是客户端 Demonware 对象消息码（8 位），后者是服务端 iD-Tech servercommand（不同方向、不同编码）。
- **`0x81..0x85` ≠ configstring `0x04`/snapshot `0x05/0x06`/demo 子帧**：无论方向还是编码粒度均不同（服务端 `0x04` 是 configstring，客户端 `0x04` 是阶段 1 的失败码）。
- **`0x84` 两侧数值巧合**：客户端 `0x84`（阶段 2/3 处理）与服务端 `0x84` 无语义关联，且服务端 `0x84` 只作为 `cmp eax,0x84` 出现在**非网络**路径（`0xAA5D8` 属浮点/参数解析，`0x165E38`/`0x3416FF` 为日志选择），与协议无关。
'''

files["E26_CLIENT_SERVER_FIELD_CROSSWALK.md"]=r'''# E26 客户端—服务端字段交叉表

## 1. 参考路径（E-25 实际交付，不新增假设）

```text
0x6AB310 (阶段1应答状态机)
  → 0xDAB40 (序列化器，vtable 0xCBBD24；缓冲 [ebx+0xC]、写游标 [ebx+0x10])
  → 0x6AA230 (克隆 0x1C 节点 + 头插 [edi+0xB8])
  → 0x6AA7B0 (会话泵)
  → 0x783B50 (send 包装: send(fd,buf,len))
  → 0x784E40
  → ws2_32!send
```

## 2. 逐项比较（任务书 §C 六问）

| # | 问题 | 服务端证据 | 判定 |
|---|---|---|---|
| C1 | 服务端是否有证据接收此类客户端数据？ | 有接收入口（`recvfrom`→`_SV_ReadPackets`→`_SV_PacketEvent`），但**无** `CLIENTCHAL`/`BDDATA` 标签、**无** Demonware 模块、**无** 8 位 `0x81..0x85` 分支 | **证据不足/不同族** |
| C2 | 服务端从何层级读消息边界与码？ | 帧：`_SV_Netchan_Decode`（`0x855C0`，XOR + `CODOL2697_PROFILE_WIRE`）；消息码：`_MSG_ReadBits(msg,3)`（`0x472E7D`） | **完全不同的分层** |
| C3 | 服务端如何处理字段长度/字符串/二进制？ | `_MSG_ReadByte/Short/Long/Data/String`（`0x2BC61..0x2BEAA`）；`_CODOL_ReadByte/Short/Long`（`0x99394/0x993A6/0x993B8`） | 机制存在，但与 Demonware 序列化器无对应 |
| C4 | 状态条件能否解释客户端阶段转换？ | 服务端状态是 `[obj+0x25C]`/`[+0x64]`/`[+0x68]`/`[+0x10..13]==7F000001`；**无 `[+0x5CC]` 同构** | **无对应** |
| C5 | 服务端响应能否对应客户端 `0x83/0x84/0x85` 分派？ | 服务端下行 `0x01..0x06`；与客户端 `0x83/0x84/0x85` 不同方向、不同编码 | **无对应** |
| C6 | 是否存在字段序/长度/编码/状态冲突？ | 见 E26 冲突报告：首个冲突 = 客户端消息 opcode 位数（8 vs 3） | **明确冲突** |

## 3. 共享点（唯一可交叉验证）

| 项 | 客户端 | 服务端 | 判定 |
|---|---|---|---|
| `challengeResponse` 字符串 | VA `0xCB7AE4`（ref `0x9BFB9`）、`0xCC5EF0`（ref `0x1EC4FE`） | VA `0x7BCCCA`（ref `0x975A4`） | **PROVEN 共享** |
| `7F 00 00 01` 签名 | 2 处 | 6 处（含 `_CODOL_NetworkSessionReady` `0x9A454..0x9A46A`） | **PROVEN 存在**；语义对应 INFERRED（强） |
| 长度常量 `0xBD`（189） | 未找到 | `_CODOL_HandshakeCookie` `0x98611` | 服务端特有 |
| 16 字节 `[1,2,0,0,0,0,≠0,cookie8]` | 未找到 | `_CODOL_HandshakeInit` `0x9830D..0x98377` | 服务端特有 |
| `CLIENTCHAL`/`BDDATA` | 各 1 处 | **0 处** | **客户端特有** |
| HMAC/recv counter | `HMAC mismatch`/`Bad recv counter` | **0 处**（HMAC 仅 mbedTLS 库） | **客户端特有** |

## 4. 结论

- **完全匹配**：`challengeResponse` 字符串、`7F 00 00 01` 签名（iD-Tech 握手族）。
- **部分匹配**：两侧都有可靠命令/快照/配置字符串通道，但编码与 opcode 空间不同（本目录 04/E3 已记录）。
- **明确冲突**：客户端 Demonware 会话握手（`CLIENTCHAL`/`BDDATA`/HMAC/recv counter/`[+0x5CC]` 阶段）在服务端**不存在对应实现**。
- **证据不足**：客户端 `0x81..0x85` 与E-25 那条发送链的服务端消费方，未在本样本中找到（**不等于全局不存在**）。

## 5. 替代解释（必须保留）

1. 客户端 Demonware 会话握手的对端是**独立的 Demonware 大厅/会话服务**（非 `codol_dedrun.exe`），而 2697 专用服务端只承担 iD-Tech 对局流量。
2. 也可能经 `client_room2697.dll`/`client_native_loopback.dll` 桥接后再转发——但这两个 DLL 亦无该族标签（已扫描）。
3. 本轮**不能**断言"协议不兼容"；只能断言"2697 专用服务端样本中未找到该握手族的消费路径"。
'''

files["E26_PROTOCOL_CONFLICTS_AND_BLOCKERS.md"]=r'''# E26 协议冲突与阻塞审计

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
'''

files["E26_NEXT_GATE_DECISION.md"]=r'''# E26 下一门禁决策

## 1. 决策

**维持 CONDITIONAL GO**，并**停止在 `codol_dedrun.exe` 内扩展**。本轮证明该样本是经典 iD-Tech 协议栈，与客户端 Demonware 会话握手不是同族；继续在其内搜索客户端 `0x81..0x85` 的消费者预期不会有收益。

## 2. 本轮获得的确定性收益

1. **服务端接收/分派链按名闭合**（PROVEN）：`recvfrom → _SV_ReadPackets → _SV_PacketEvent → _Netchan_Process → _SV_ExecuteClientMessage`（3 位 opcode 0..4）。
2. **首个结构性冲突定位**（PROVEN）：客户端消息 opcode 8 位 vs 服务端 3 位。
3. **协议族判定**（PROVEN）：服务端为 iD-Tech（`challengeResponse %d`、长度 `0xBD`、`[1,2,...]` 结构、`7F000001`），**无** Demonware 模块与该族字符串。
4. **唯一共享点确认**（PROVEN）：`challengeResponse` 与 `7F 00 00 01` 两侧共有。
5. **多 writer 风险确证**（PROVEN）：legacy 与 2697 双通道共存，由 `CODOL2697_PROFILE_WIRE` 切换。

## 3. 停止条件核对（任务书 §7）

| 停止条件 | 状态 |
|---|---|
| "服务端接收、解析和客户端字段形成可验证对应" | 不适用（字段族不同，无对应） |
| "服务端存在候选处理路径但字段语义不足" | 部分适用 → 已补齐服务端字段证据 |
| "找到明确格式或状态冲突" | **已触发** → C-1（opcode 宽度）及 C-2..C-6 |
| "服务端没有找到候选" | 适用 → 已报告实际覆盖的接收根与闭包边界，**未宣称全局不存在** |

## 4. 剩余最小缺失证据

1. **Demonware 会话服务端模块**：含 `bdCore`/`bds`/`CLIENTCHAL`/`BDDATA` 的二进制；本机 `codol_dedrun.exe`、两个桥接 DLL 均无。
2. **`challengeResponse` 两侧字段序**（客户端 `0x9BFB9` vs 服务端 `0x975A4`）。
3. **客户端 0x81..0x85 的应用层归属**：是 Demonware 服务上的消息，还是另一条独立通道。

## 5. 下一步唯一建议

**在服务端生态中定向寻找 Demonware 会话模块**：以 `bdCore`/`bds`/`demonware`/`CLIENTCHAL`/`BDDATA`/`HMAC mismatch` 为目标字符串，在以下范围内做定向搜索（不做全盘无边界扫描）：

1. `D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\`（含 `scripts\`、`runtime-assets\`、`evidence\`）；
2. `D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\` 下的其他原生模块（非 `codol_dedrun.exe`）；
3. 若存在独立的 Demonware/Demonware-like 大厅进程或服务组件，则对其做 E-21..E-25 同构（`CLIENTCHAL`/`BDDATA`）扫描。

若确认服务端生态**不存在**该模块，则记录"客户端 Demonware 会话握手在 2697 服务端生态中缺失"为首个端到端结构性阻塞，并把实时互操作保持 `NOT-OBSERVED`。

不建议：
- 继续在 `codol_dedrun.exe` 内搜索 `0x81..0x85` 的消费者（已证协议族不同）；
- 把 iD-Tech `challengeResponse` 当作 E-25 那条链的兼容证明；
- 在无服务端对端证据时实现服务器端 Demonware 握手。
'''

for name,content in files.items():
    (OUT/name).write_text(content,encoding="utf-8")
    print("wrote",name,len(content))
