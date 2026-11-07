# E26 下一门禁决策

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
