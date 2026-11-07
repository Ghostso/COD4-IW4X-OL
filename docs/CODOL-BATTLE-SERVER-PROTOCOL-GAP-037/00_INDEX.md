# CODOL-BATTLE-SERVER-PROTOCOL-GAP-037

**任务编号：** `CODOL-BATTLE-SERVER-PROTOCOL-GAP-037`  
**目标版本：** CODOL 3.19.26.22 / Build 1649370 / 2021-05-07  
**审计日期：** 2026-10-13（Asia/Shanghai）  
**性质：** 只读审计 + 独立目录内可重复验证；不启动游戏，不做真实客户端 E2E。

---

## 0. 结论摘要

1. **现有服务器已经实现了一套完整的“服务端侧协议栈”**：UDP 收发、NAT 探针、DTLS-like cookie/key exchange、数据帧 HMAC/AES 封装、OOB challenge/connect/heartbeat、legacy 13B netchan、2697 netchan、玩家命令解析、权威帧循环、gamestate/configstring 构造、位级 snapshot 编码。见 `CURRENT_SERVER_CAPABILITIES.md`。
2. **目标客户端二进制只直接确认了其中一部分行为**：OOB 状态门与命令字面量、cancelConnect 字面量、gamestateupdate 字面量、增量类型分派表结构，以及 configstring 解析族的存在。见 034 原始证据与 `CLIENT_SERVER_PROTOCOL_MATRIX.tsv`。
3. **从“客户端发起战斗连接”到“客户端收到可解析游戏状态”的关键环节仍缺失**：目标版本的 netchan 真实入口、服务端消息 opcode 分派、gamestate/configstring 的实际消费者入口与字段级格式均未闭合。snapshot 帧边界、delta 基线、实体增删同样为 `UNKNOWN`。
4. **现有服务器的 gamestate 与 snapshot 编码是旧抓包链路/旧协议材料，不是目标版本已确认格式。** 日志确认所有真实启动均为 `connected=0`，客户端从未连入。冻结基线明确不做真实客户端 E2E。
5. **下一任务唯一推荐：闭合目标版本“应用层消息入口与 opcode 证据链”**，即从已定位的 `0x1FF820 → 0x208380 → 0x5F830` 链出发，向上定位调用者 `0x20059B` 所在函数，向下绑定 netchan 重组缓冲与服务端消息 opcode，最终给出可离线验证的消息入口/边界规格；**不在该证据闭合前实现 gamestate、configstring 或 snapshot 编码。** 见 `NEXT_TASK_RECOMMENDATION.md`。

---

## 1. 必读证据入口

### 1.1 034 —— `CODOL-BATTLE-SERVER-TRACE-034`

> 固定基线写的是 `CODOL-BATTLE-STATE-034`；实际目录不存在。  
> 实际存在并已读取的是 `CODOL-BATTLE-SERVER-TRACE-034`。  
> 未找到名为 `CODOL-BATTLE-STATE-034` 的目录或文件。该差异已记入 `UNKNOWN_AND_BLOCKERS.md`。

- `CODOL-BATTLE-SERVER-TRACE-034\00_INDEX.md`
- `CODOL-BATTLE-SERVER-TRACE-034\BATTLE_RX_CALLCHAIN.md`
- `CODOL-BATTLE-SERVER-TRACE-034\GAMESTATE_CONFIGSTRING_TRACE.md`
- `CODOL-BATTLE-SERVER-TRACE-034\SNAPSHOT_FORMAT_AND_DELTA.md`
- `CODOL-BATTLE-SERVER-TRACE-034\CLIENT_STATE_TRANSITIONS.md`
- `CODOL-BATTLE-SERVER-TRACE-034\SERVER_IMPLEMENTATION_GAP.tsv`
- `CODOL-BATTLE-SERVER-TRACE-034\UNKNOWN_AND_BLOCKERS.md`
- `CODOL-BATTLE-SERVER-TRACE-034\OFFLINE_TEST_VECTORS.md`
- 原始输出：`evidence\dis_oob_full.out.txt`、`evidence\dump_typetables.out.txt`、`evidence\delta_chain_context.out.txt`、`evidence\verify_target_image.out.txt`

### 1.2 035 —— `CODOL-BATTLE-OOB-STATE-035`

- `CODOL-BATTLE-OOB-STATE-035\00_INDEX.md`
- `CODOL-BATTLE-OOB-STATE-035\CONFIRMED_VS_UNKNOWN.tsv`
- `CODOL-BATTLE-OOB-STATE-035\SERVER_INTEGRATION_GAP.tsv`
- `CODOL-BATTLE-OOB-STATE-035\UNKNOWN_AND_BLOCKERS.md`
- `CODOL-BATTLE-OOB-STATE-035\src\*.cs` 与 `build\selftest.output.txt`

### 1.3 FREEZE-005 —— `CODOL-BATTLE-SERVER-INTEGRATION-FREEZE-005`

- `FREEZE-005_REPORT.md`
- `attempt_01_20261013_124339\attempt_result.json`
- `attempt_01_20261013_124339\evidence\source_fingerprint_pre.json`
- `attempt_01_20261013_124339\evidence\source_fingerprint_post.json`
- `attempt_01_20261013_124339\evidence\selftest.stdout.log`
- `attempt_01_20261013_124339\evidence\run_maxseconds.stdout.log`
- `attempt_01_20261013_124339\evidence\run_observation.json`

### 1.4 正式服务器源码

- `CODOL-Combat-Server-v0.1\src\Program.cs`
- `CODOL-Combat-Server-v0.1\src\Engine\ServerHost.cs`
- `CODOL-Combat-Server-v0.1\src\Engine\ClientLogic.cs`
- `CODOL-Combat-Server-v0.1\src\Engine\ClientSession.cs`
- `CODOL-Combat-Server-v0.1\src\Net\UdpTransport.cs`
- `CODOL-Combat-Server-v0.1\src\Codol\CodolProtocol.cs`
- `CODOL-Combat-Server-v0.1\src\Codol\Codol2697Protocol.cs`
- `CODOL-Combat-Server-v0.1\src\Codol\MotionSnapshot.cs`
- `CODOL-Combat-Server-v0.1\src\Engine\ServerConfig.cs`
- `CODOL-Combat-Server-v0.1\config\combat_server.cfg`

### 1.5 目标客户端

- EXE：`COD OL\codoMP_client_shipRetail.exe`，SHA256 `36997674b18f2896de5e9d755686f6922af10708f355175714058d0a0172b537`
- DLL：`COD OL\codoMP_client_shipRetailBase.dll`，SHA256 `ef75220de1d6973f34c7069f5bf211b11bd61520c6c0de1882f7359fa5bc6a20`
- 034 使用的运行时镜像：`CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin`，SHA256 `17cef6e0a5e7b8d14fb97b5fdd846061187c6a722cfa3c5d432bee37872fd045`

---

## 2. 状态语义（本任务统一）

| 状态 | 含义 | 本任务使用规则 |
|---|---|---|
| `CLIENT_CONFIRMED` | 目标版本 EXE/DLL/镜像中有直接证据 | 必须有地址、字节或字面量 |
| `SERVER_IMPLEMENTED` | 正式服务器源码中存在实现 | 必须有文件与行号 |
| `TEST_VERIFIED` | 实际执行并通过的测试 | 必须记录命令、退出码、原始输出 |
| `E2E_VERIFIED` | 目标客户端与服务器实际通信验证 | 本任务没有任何 E2E |
| `UNKNOWN` | 证据不足 | 不得用其他版本惯例填补 |

以上状态**可以并存**，不得相互自动升级。

---

## 3. 本任务边界与纪律

- 未修改 FREEZE-005。
- 未修改 `CODOL-Combat-Server-v0.1` 的正式源码、配置或构建脚本。
- 未修改原始游戏 EXE/DLL/镜像/抓包。
- 未启动游戏，未做客户端端到端测试。
- 未将 036 报告作为协议确认依据。
- 未把 legacy/C-3333/2697 格式套用到 3.19.26.22。
- 未制造假 snapshot、假 gamestate 或未经证实的成功响应。
- 所有新增文件均在 `CODOL-BATTLE-SERVER-PROTOCOL-GAP-037` 内。
- 未声称真实客户端兼容性验证通过。

---

## 4. 交付物

| 文件 | 内容 |
|---|---|
| `00_INDEX.md` | 范围、结论摘要、证据入口 |
| `CURRENT_SERVER_CAPABILITIES.md` | 服务器能力清单与真实接线 |
| `CLIENT_SERVER_PROTOCOL_MATRIX.tsv` | 客户端证据 / 服务器实现 / 测试覆盖 / 验证状态矩阵 |
| `CONNECTION_TO_GAMESTATE_GAP.md` | 连接建立到初始游戏状态的完整缺口 |
| `SNAPSHOT_DELTA_GAP.md` | snapshot/delta/实体同步未知项与证据定位 |
| `TRANSPORT_SESSION_GAP.md` | 传输层与会话缺口 |
| `NEXT_TASK_RECOMMENDATION.md` | 唯一推荐下一任务、范围、验收标准 |
| `UNKNOWN_AND_BLOCKERS.md` | 未决问题与最小验证方法 |
| `TEST_AND_BUILD_RESULTS.md` | 实际执行的测试/构建命令、退出码与结果 |
| `FILE_HASH_MANIFEST.tsv` | 本任务新增文件 SHA256 |
| `SHA256SUMS.txt` | 新增交付文件完整性校验值 |

---

## 5. 关键判定

- 现有服务器**能自己运行**：FREEZE-005 已证明构建、251 项自测、指纹、UDP 绑定和停机清理。
- 现有服务器**不能证明与目标客户端互通**：运行日志 `connected=0`，FREEZE-005 明确“未执行真实客户端 E2E”。
- 目标客户端**确实有 OOB 状态机与挑战失败语义**，但这只覆盖连接建立的一部分。
- 目标客户端**确实有解析族与增量类型表结构**，但入口、字段、边界和基线均未闭合。
- 因此下一任务必须优先闭合**应用层消息入口与 opcode 证据链**，而不是继续编码未知格式。
