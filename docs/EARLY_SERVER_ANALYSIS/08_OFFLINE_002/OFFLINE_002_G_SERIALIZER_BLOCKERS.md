# OFFLINE_002 — G：战斗序列化器阻塞项

> 任务：`EARLY-SERVER-OFFLINE-VALIDATION-002` §5/§6/§7。
> 输入：只读。派生脚本/证据仅写 `08_OFFLINE_002\`；不启动服务端/客户端，不执行 `.cmd`，不修改样本/既有报告。
> 状态词：CONFIRMED / STRONG_CANDIDATE / CANDIDATE / UNKNOWN / REFUTED / NOT_OBSERVED / INSTRUMENTATION_BLOCKED。
> 说明：每条阻塞项给出**证据定位**与**最小闭合任务**；不猜测、不用篇幅代替验证。

---

## G.0 一句话结论

- 服务端 CoDOL 序列化器**源码级完整**（gamestate/configstrings/snapshot 三段，`codol\` 专用实现），但**客户端可解析性未验证**。
- 最大阻塞**不是**序列化器缺失，而是：① **无带完整载荷的下行抓包**（客户端/服务端双向）；② **客户端 VMProtect 加壳**导致解码路径语义不可静态确证；③ **线值 opcode 与 `svc_ops_e` 枚举两套编号系**，客户端实际使用哪套未知。
- 上述三项均**不能**用推测填补，故序列化器"可直接复用"最多到 **STRONG_CANDIDATE/CANDIDATE**，不能升级为 CONFIRMED。

---

## G.1 阻塞项清单

### BLK-1 无游戏层载荷抓包（最高优先级）
- **证据**：4 份 `wiretap-*.jsonl` 共 11,878 事件，`kind ∈ {task,push,auth_frame,udp,stun_reply,counter,write,handler_exception,undecodable,refused,udp_unhandled}`，`layer ∈ {lobby,seckey,stun}`，**0 个事件携带报文载荷字节**；`lobby\docs\wiretap_report.md:185`："No game-layer events in this capture"。
- **影响**：无法对服务端序列化器产出做逐字节比对；无法确认客户端解码器接受的格式。
- **等级**：**REFUTED**（"现有捕获可裁决序列化器"这一前提被证伪）。
- **最小闭合任务**：采集**一份含完整 gamestate/snapshot 载荷**的抓包（非 `pkt[:128]` 截断），或对早期服务端做**受控单会话**下行记录（需另行授权，本轮不做）。

### BLK-2 客户端 VMProtect 加壳（静态分析盲区）
- **证据**：客户端 PE 段表——`.vmp0`（`va 0x9610000`, vsize `0xc668`）+ 所有代码段改名 `nsn`；导入表仅 `Kernel33.dll`（`_evidence\client_xrefs.json` 的 `sections`）。
- **影响**：服务端注释引用的客户端 VA（`0x49dd7e`/`0x49d9ce`/`0x5a0510`/`0x465f57` 等）虽存在且反汇编可读，但其**运行时语义不可静态确证**；关键字符串（`Received gamestate`、`begin parse`、`bad command byte`）xref 为空（间接引用）。
- **等级**：**INSTRUMENTATION_BLOCKED**。
- **最小闭合任务**：动态调试（需授权）或在**未加壳**的对应客户端版本上做静态分析；**不得**用传统 CoD 架构相似性替代。

### BLK-3 线值 opcode 与 `svc_ops_e` 两套编号系
- **证据**：服务端线值——gamestate `0x02`（`codol_configstrings.c:298`）、configstring 子流 `0x03`（`:276`）、snapshot `0x00`（`codol_snapshot.c:23`）、serverCommand `0x01`（`sv_snapshot.c:61`）、终止 `0x05`（`codol_configstrings.c:284/306`、`codol_snapshot.c:41`、`sv_snapshot.c:62/849`）。对比 `net_game_conf.h:64-78 svc_ops_e`：gamestate=1、configstring=2、serverCommand=4、download=5、snapshot=6、EOF=7。
- **影响**：CODOL 线值是**自定义 opcode 空间**（用 `#define` 而非枚举值）；客户端实际按哪套解析 **UNKNOWN**。
- **等级**：两套编号系并存 = **CONFIRMED**；客户端所用编号 = **UNKNOWN**。
- **最小闭合任务**：从客户端反汇编中定位 svc 分派表/比较常量（受 BLK-2 约束），或从带载荷抓包中实测首字节。

### BLK-4 客户端解码入口未闭合
- **证据**：客户端字符串存在（`0x849358` begin parse、`0x849388` bad command byte、`0x8493b0` bad clientNum、`0x849210` configStrings、`0x846370` CL_GetSnapshot trunc、`0x848f70` non-baseline discard、`0x74e784` baseline），但**引用点为空或落在加壳区**；`CS_PRIMED` 状态转换点无字符串。
- **影响**：无法给出客户端"gamestate 解码入口/快照解码入口/状态机"的确切 RVA。
- **等级**：字符串存在 = **CONFIRMED**；解码入口 = **UNKNOWN/INSTRUMENTATION_BLOCKED**。
- **最小闭合任务**：带载荷抓包 + 动态跟踪；或未加壳版本静态分析。

### BLK-5 现有 C# 参考不是早期原生服务端
- **证据**：`CODOL-Combat-Server-v0.1\src\Codol\MotionSnapshot.cs:3` 自述"逐行移植自 `REF_LOBBY_KIT/battle_server.py::_BitWriter / _build_motion_snapshot`"；`ClientLogic.cs:408/432` 的 `PumpGameState`/`PumpSnapshot` 是重写实现；`SelfTest.cs:1067` 期望 game state == 263B。
- **影响**：C# 的 `MotionSnapshot` 字段序（`ExpectedIndexOrder`：`0,1,3,8,10,11,13,14,17,18,19,20,21,22,23,24,29,34,38,39,41,44,54,56,60,61,63,68,84`，`MotionSnapshot.cs:222-227`）与**早期原生 CoDOL 序列化器**（`codol_snapshot.c` 的 6 段布局）**不是同一实现**，两者**未证明互通**。
- **等级**：C#≠原生 = **CONFIRMED**；C# 与客户端互通 = **NOT_OBSERVED**。
- **最小闭合任务**：**不得**用 C# 参考替代原生序列化器的验证；若采用 C# 路线，需独立与客户端联调。

### BLK-6 地址块形态 / 密钥一致性（承 OFFLINE_001）
- **证据**：258B 记录内嵌 **37B 短地址**（`session_record_258.bin` field#0 = Blob[37]），观测 COOKIE_ECHO 携带 **67B 长地址**（`battle_srv.log:2324`）；本机 258B 的 securityKey 为 16×`0x01`，而 `lobby\securitykey.bin` 为另一份 16B 值（`_evidence\offline_002_evidence.json`）。
- **影响**：若目标运行时 securityKey 未唯一确定，传输密钥分叉 → 静默丢包（见 A 报告）。
- **等级**：**NOT_OBSERVED**（两形态对应关系未闭合）。
- **最小闭合任务**：确认目标运行时唯一 16B securityKey；闭合 37B/67B 地址形态与实机对应。

### BLK-7 真实会话 MAC 逐字节复算（承 OFFLINE_001 A）
- **证据**：`battle_srv.log:2325` 仅记录 `transport=22d0fa6843b44afe0bedd2777d22f7c1`（32 hex = **16B**，即 24B key 的前 16B）；ECDH 私钥每轮随机、不落盘。
- **影响**：无法逐字节复算该会话 8B MAC 与 keystream。
- **等级**：**INSTRUMENTATION_BLOCKED**。
- **最小闭合任务**：受控单会话记录**完整 24B transport key**（绑定 seq）或**同期 ECDH 私钥/共享 X(28B)**；复算后仅记录结论与哈希，不落盘密钥。

---

## G.2 阻塞项优先级

| 优先级 | 阻塞项 | 理由 |
|---|---|---|
| P0 | BLK-1（无载荷抓包） | 阻塞所有逐字节验证；前置条件明确、零风险（离线分析已有数据） |
| P0 | BLK-3（opcode 编号系） | 直接决定客户端能否解析 gamestate/snapshot 首字节 |
| P1 | BLK-4（解码入口未闭合） | 决定能否给出双端映射的客户端侧确切 RVA |
| P1 | BLK-2（VMProtect） | 与 BLK-4 同源；需动态调试或未加壳版本 |
| P2 | BLK-5（C#≠原生） | 影响路线选择（见 H 报告） |
| P2 | BLK-6 / BLK-7 | 承 OFFLINE_001，独立于序列化器 |

---

## G.3 证据等级汇总

| 断言 | 等级 | 依据 |
|---|---|---|
| 现有捕获无游戏层载荷，不能裁决序列化器 | **REFUTED**（前提） | 11,878 事件 0 载荷；`wiretap_report.md:185` |
| 客户端为 VMProtect 加壳 | **CONFIRMED** | `.vmp0` + `nsn` 段表 |
| 客户端解码器语义不可静态确证 | **INSTRUMENTATION_BLOCKED** | 加壳 + 间接引用 |
| CODOL 线值与 `svc_ops_e` 为两套编号系 | **CONFIRMED** | 写点 vs `net_game_conf.h:64-78` |
| 客户端使用哪套 opcode | **UNKNOWN** | 无客户端分派表证据 |
| 客户端解码入口/`CS_PRIMED` 转换点 | **UNKNOWN** | 无引用点 |
| C# 参考≠早期原生序列化器 | **CONFIRMED** | `MotionSnapshot.cs:3` 自述 + 布局差异 |
| 37B/67B 地址形态对应 | **NOT_OBSERVED** | 无实机对应证据 |
| 真实会话 MAC 逐字节复算 | **INSTRUMENTATION_BLOCKED** | 仅 16/24B key |

---

## G.4 停止条件核对（§7）

| §7 停止条件 | 是否触发 | 处理 |
|---|---|---|
| 关键源文件缺失 | 否 | 服务端 `codol\` 源文件齐全（D 报告） |
| 客户端对应路径无法定位 | **是** | 已标 **UNKNOWN/INSTRUMENTATION_BLOCKED**（E 报告），列出最小后续任务 |
| 字段编号无法从真实解析逻辑确定 | 否 | 已从 `SessionDescriptor.cs:131-159` + 字节解析确定（C 报告） |
| 序列化器编码格式仍然未知 | 部分 | 服务端格式**已确认**；客户端可解析性 **UNKNOWN** → 未用推测填补 |
| 证据相互冲突且无法解释 | 部分 | opcode 两套编号系已解释为自定义空间；客户端所用编号保留 UNKNOWN |

**结论**：触发"客户端对应路径无法定位"与"序列化器（客户端侧）仍未知"两项 → 已按要求**保留 UNKNOWN 并列出最小后续任务**，未用推测填补。
