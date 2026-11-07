# -*- coding: utf-8 -*-
from pathlib import Path
OUT=Path(r"D:\BaiduNetdiskDownload\使命召唤OL\E26_SERVER_HANDSHAKE_PEER_CROSSWALK_001")
files={}

files["E26_EXECUTIVE_SUMMARY.md"]=r'''# E26 执行摘要

## 一句话结论

2697 专用服务端 `codol_dedrun.exe` **有完整、可证实的接收入口与消息分派链**（`WS2_32!recvfrom` → `_SV_ReadPackets` → `_SV_PacketEvent` → `_Netchan_Process` → `_SV_ExecuteClientMessage`，3 位 opcode `0..4` 跳表）；但它是**经典 iD-Tech（CoD）协议栈**，与客户端 E-21..E-25 追踪的 **Demonware 握手对象完全属于两条不同协议族**——服务端**不含** `CLIENTCHAL`、`BDDATA`、`HMAC mismatch`、`Bad recv counter` 任何一个字符串，也**不含** Demonware 模块。因此**客户端 E-25 追踪的阶段 1 应答（0x81..0x85）在服务端没有对应的消费者**；两侧倒是在 iD-Tech 握手族上共享 `challengeResponse` 与 `7F 00 00 01` 标志。

## 关键事实

1. **服务端接收入口可证实**（PROVEN）：
   - `WS2_32.dll!recvfrom`（IAT `0x15CBFA0C` 区域）；`_SV_ReadPackets` RVA `0x6E2D5`；`_SV_PacketEvent` RVA `0x84CA2`。
   - 顶层分派：`_SV_ConnectionlessPacket` RVA `0x8487F`（含 `sub eax,0x4A; cmp al,1` ⇒ 字节 `0x4A`/`0x4B`）。

2. **客户端消息 opcode 空间仅 3 位、0..4**（PROVEN）：
   - `_SV_ExecuteClientMessage` RVA `0x72DBB`：`0x472E6F` 处 `call 0x42bf2d(...,3)` 读 3 位；
   - `0x472EA7 cmp edi,4; ja` 越界拒绝；
   - `0x472EB0 jmp [edi*4+0x7B37A0]`，跳表 5 项（VA `0x473104/47311B/473132/47319A/472E6F`）。
   - `clc[0/1]` → `_SV_UserMove`（`ecx=1/0`），`clc[2]` → `_SV_ClientCommand`，`clc[3]` → 直接返回，`clc[4]` → 拒绝。
   - 与客户端的 `0x81/0x83/0x84/0x85` **量级与形状均不一致**。

3. **服务端握手族是 iD-Tech，不是 Demonware**（PROVEN）：
   - `_CODOL_HandshakeInit` RVA `0x982A3`：校验 16 字节结构 `[1,2,0,0,0,0,非零16位, 8 字节 cookie]`（`0x9830D..0x98377`），再比对 16 字节 challenge/response（`0x98392..0x983AB`）。
   - `_CODOL_HandshakeCookie` RVA `0x9857B`：长度必须是 `0xBD`（`0x98611 cmp [ebp+0x14],0xBD`）。
   - `_CODOL_WriteChallengeResponse` RVA `0x97592`：以格式串 `"challengeResponse %d"`（VA `0x7BCCCA`）构造 0x40 字节响应。
   - `_CODOL_NetworkReceive` RVA `0x9A54C` / `_CODOL_NetworkSend` RVA `0x9A472` / `_CODOL_NetworkSessionReady` RVA `0x9A3FA`：会话就绪签名 `7F 00 00 01`（`0x9A454..0x9A46A`）。
   - 服务端导入表**无**任何 Demonware 模块（仅 ADVAPI32/CRYPT32/GDI32/KERNEL32/msvcrt/SHELL32/USER32/WINMM/WS2_32）。

4. **`CLIENTCHAL`/`BDDATA` 在服务端不存在**（PROVEN，范围内）：
   - 对 `codol_dedrun.exe`、`client_room2697.dll`、`client_native_loopback.dll` 三样本做精确字节扫描，`CLIENTCHAL`/`BDDATA`/`HMAC mismatch`/`Bad recv counter` 命中均为 **0**。
   - 服务端 `HMAC` 仅来自 mbedTLS（`_mbedtls_md_hmac*`、`_hmac_drbg*`），与客户端 Demonware 会话对象无关。

5. **两侧唯一可证实的共享点**（PROVEN）：
   - 字符串 `challengeResponse` 同时存在于服务端（VA `0x7BCCCA`，ref `0x975A4`）与客户端（VA `0xCB7AE4`，ref `0x9BFB9`；另一处 VA `0xCC5EF0`，ref `0x1EC4FE`）。
   - 签名字节 `7F 00 00 01` 两侧均存在（客户端 2 处，服务端 6 处）。

## 判定表（任务书 §四四问）

| 问题 | 回答 | 等级 |
|---|---|---|
| 服务端是否有明确接收入口与消息分派？ | **是**：`recvfrom` → `_SV_ReadPackets` → `_SV_PacketEvent` → `_Netchan_Process` → `_SV_ExecuteClientMessage`（3 位 opcode 0..4） | PROVEN |
| 客户端阶段 1 应答是否有服务端消费路径？ | **否（在本样本范围内未找到）**：服务端无 Demonware 模块、无 `CLIENTCHAL`/`BDDATA`、opcode 空间 0..4 ≠ 0x81..0x85 | PROVEN（缺席）/ 全局不存在 **不宣称** |
| 双侧字段布局/方向/状态是否一致？ | **不一致**：协议族不同（Demonware 对象协议 vs iD-Tech 3位 opcode）；仅 `challengeResponse`/`7F000001` 共享 | PROVEN（差异） |
| 首个可证实冲突点？ | **服务端 `_SV_ExecuteClientMessage` 的 opcode 宽度=3 位、取值 0..4**（`0x472E77`），与客户端 `cmp al,0x81/0x83/0x84/0x85`（8 位值）无法在同一分派器内共存 | PROVEN |

## 被证伪/更正的假设

- **「服务端应与客户端共用 Demonware 握手（`CLIENTCHAL`/`BDDATA`/HMAC/recv counter）」→ REFUTED**：服务端为经典 iD-Tech 栈，无该族任何符号。
- **「E-25 的 0x81 应答会被 2697 专用服务端消费」→ REFUTED（本样本范围内）**：服务端客户端消息 opcode 仅 0..4。
- 保留：客户端与服务端均为相同 CODOL 2697 产品，iD-Tech 层（`challengeResponse`、`7F000001`）共享——**但这不是 E-25 那条 Demonware 链**。

## 剩余阻塞

1. **Demonware 握手对端不在本服务端样本内**：需在 Demonware/`bdCore` 服务端（大厅/会话服务）或另一进程/模块中寻找其消费者；本样本未覆盖。
2. `client_room2697.dll`/`client_native_loopback.dll` 亦无该族标签；是否经加密隧道转交未证实。
3. `challengeResponse` 两侧的**字段序**未逐字段对齐（客户端 `0x9BFB9` vs 服务端 `0x975A4`）。
4. 客户端 0x81..0x85 是否**自身就是**某条应用层 Demonware 服务之上的消息（需 Demonware 服务端才能闭合）。

## 下一步唯一建议

**定位 Demonware 会话服务的对端实现**——即 E-21..E-25 追踪的 `0x6A84E0`/`0x6AB310`/`0x6AA230` 所属会话对象的服务端对应物。它**不在** `codol_dedrun.exe`（已证：无 Demonware 模块/无该族字符串），而应由 Demonware `bdCore`/`bds` 大厅服务或 2697 服务端目录中未被本样本覆盖的模块承载。下一步应在服务端目录与 Demonware 服务组件中做定向搜索（`bdCore`/`bds`/`lobby`/`session`），而非继续在 `codol_dedrun.exe` 内展开。若确认服务端侧不存在该模块，则应记录"客户端 Demonware 会话握手在服务端样本中缺失"为首个结构性阻塞，并停止在该样本内扩展。
'''

for name,content in files.items():
    (OUT/name).write_text(content,encoding="utf-8")
    print("wrote",name,len(content))
