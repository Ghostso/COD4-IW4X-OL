# 03 — 握手模块实现

**分支:** 047 工程 `049/connectionless-handshake`(基线 `8f3e331` → 提交 `64f5095`)。
**约束:** 在 047 已通过测试的基础设施上**新增**,不重写既有模块。

---

## 1. 文件与职责

| 文件 | 职责 | 证据等级 |
|---|---|---|
| `Protocol\Handshake\HandshakeEvidence.cs` | 证据分级枚举、`[TestOnly]`、`UnprovenHandshakeSurface` | `Unknown`(未证实面登记) |
| `Protocol\Handshake\ConnectionlessHandshake.cs` | 解析/边界、词表、请求模型、响应接口、重复检测、结构化日志 | `OfficialClientObserved` |
| `Sessions\HandshakeStateMachine.cs` | 状态机(见 `04`) | `ProjectImplementationConfirmed` |

## 2. `ConnectionlessHandshake` 能力(工作包 A 逐条)

| 需求 | 实现 | 关键常量/行为 |
|---|---|---|
| 1. 报文解析与命令边界检查 | `Parse(span, direction)` | token ≤ 32B、参数 ≤ 256B、帧 ≤ 512B;空格分隔;越界/非可打印拒绝 |
| 2. 已证实命令词表显式注册 | `RegisteredCommands` → `ConnectionlessCommands.All` | 14 条,每条带 RVA + 方向 |
| 3. `getchallenge` 请求数据模型 | `GetChallengeRequest` + `ParseGetChallenge` | 按字面形状 `getchallenge 0 "%s"` 切分 `Flag`/`Value`;值按**不透明数据**处理 |
| 4. `challengeResponse` 处理接口 | `IChallengeResponseHandler` | 接口;无内置"成功"语义 |
| 5. `connect` 请求数据模型 | `ConnectRequest` + `ParseConnect` | 按字面形状 `connect %s "%s"` 切分 `Field1`/`Field2`,**不合并**为猜测会话 id |
| 6. `connectResponse`/`connectReject` 接口 | `IConnectResponseHandler` / `IConnectRejectHandler` | 接口;格式未证实 |
| 7. challenge/会话/超时分离 | `ConnectionlessHandshake`(无状态解析) vs `HandshakeStateMachine`(有状态/时钟) | 见 `04` |
| 8. 非法/未知/截断/超长/重复拒绝 | `HandshakeRejectReason`(11 值) + `RegisterClientRequest` | 每类有独立 reason 与测试 |
| 9. 结构化日志与诊断 | 注入 `IDiagnosticsSink`,事件名固定 | `frame-accepted` / `frame-rejected` / `duplicate-request` / `getchallenge-received` / `connect-received` |

## 3. 拒绝原因枚举(稳定、可测)

`None / EmptyInput / TruncatedInput / OversizedInput / NonPrintableInput / UnknownCommand /
WrongDirection / MissingArgument / MalformedArgument / DuplicateRequest / UnexpectedCommand`

## 4. 证据隔离的代码级手段

1. **`UnprovenHandshakeSurface`**:8 项未证实面以常量登记,测试断言其完整。
2. **`HandshakeEvidenceClass`**:`ClientEvidenceConfirmed` / `ProjectModel` / `TestOnlySimulated`。
   请求模型只标 `ClientEvidenceConfirmed`(词法形状);响应接口不标任何 wire 兼容。
3. **`[TestOnly]` + `TEST_ONLY_` 前缀**:所有模拟值可被静态/测试识别。
4. **`Connected` 唯一入口**是 `HandshakeStateMachine.AcceptConnectResponse(evidenceId)`,
   且要求 `evidenceId` 非空、已存在已验证 challenge 值。任何"仅 token 匹配"的 `connectResponse`
   都**不会**建立会话(见 `04` §3)。

## 5. 与 2697 的隔离

- 握手模块位于 `Protocol\Handshake`,**不引用** `Protocol\Versions\Local2697*`。
- 既有 `ProtocolCodecRegistry` 仍**不默认注册** 2697;`FinalCodolGameDecoder` 仍显式拒绝。
- 2697 **不能**作为最终 CODOL 的回退路径(本模块无任何回退分支)。

## 6. 未实现/未声称

- 未实现与官方服务端**兼容的响应生成**;
- 未实现 challenge 算法 / nonce / 鉴权 / 连接序号 / OOB 前缀 / 响应封装;
- 未声称端到端握手完成。本模块只覆盖**连接无关明文命令层**的识别、边界与状态。
