# 05 — 测试与构建(实际执行结果)

> **重要声明:** 本轮握手测试的报文全部为**合成/模拟**夹具,标记为
> **`SIMULATED_HANDSHAKE_TEST_ONLY`**。测试通过**不**代表最终 CODOL 客户端兼容性通过。

---

## 1. 工具链与环境

| 项 | 值 |
|---|---|
| SDK | .NET SDK **8.0.420** |
| 目标框架 | net8.0 |
| OS | Windows(执行主机) |
| 分析 Python | 3.11.9;pefile 2024.8.26;capstone 5.0.7 |
| 确定性构建 | `<Deterministic>true</Deterministic>` + `<ContinuousIntegrationBuild>true</ContinuousIntegrationBuild>` |

## 2. 构建命令与结果

```powershell
cd D:\BaiduNetdiskDownload\使命召唤OL\CODOL-BATTLE-SERVER-IMPLEMENTATION-FOUNDATION-047
powershell -NoProfile -ExecutionPolicy Bypass -File build\build-and-test.ps1 -Configuration Release
```

| 项 | 结果 |
|---|---|
| 构建 | **成功**,**0 warning / 0 error** |
| 测试 | **65 passed / 0 failed / 65 total**,`RESULT=PASS` |
| 日志 | `build\logs\build_20261014_132023.log`、`build\test-results\tests_20261014_132023.log` |

**测试增量:** 基线 39 → 本轮 **65**(新增 26)。

## 3. 产物哈希(Release)

| 产物 | SHA-256 |
|---|---|
| `src\Codol.BattleServer\bin\Release\net8.0\Codol.BattleServer.dll` | `3FBA29FDB02F54AE46D2331484F560D1AA2AC118075B87934D91272CC4D73932` |
| `tests\Codol.BattleServer.Tests\bin\Release\net8.0\Codol.BattleServer.Tests.dll` | `575B0845752852975FFA34E13FC3EFF8E126939E2A39DD7729EB8AC2550A87AF` |

**确定性验证:** 连续两次 `dotnet build --no-incremental` 产物 SHA-256 完全一致(`3FBA29FD…3932`)→ 逐字节可重复。

## 4. 新增测试清单(26 项,逐项有确定输入与预期)

| 测试 | 输入 | 预期 |
|---|---|---|
| `handshake/known-commands-recognized` | `connectResponse TEST_ONLY_value` | 接受;token RVA 0x9BFF0C |
| `handshake/unknown-command-rejected` | `totallyNotACommand x` | `UnknownCommand` |
| `handshake/empty-input-rejected` | 0 字节 | `EmptyInput` |
| `handshake/truncated-input-rejected` | `" getchallenge"` / `"getchallenge"` | `TruncatedInput` / 接受且空参数 |
| `handshake/oversized-input-rejected` | > 512B 帧 / > 256B 参数 | `OversizedInput` |
| `handshake/argument-boundary` | `echo hello world` | 参数原样保留 `hello world` |
| `handshake/wrong-direction-rejected` | 服务端 token 当客户端帧(及反向) | `WrongDirection` |
| `handshake/non-printable-rejected` | 含 0x01 的帧 | `NonPrintableInput` |
| `handshake/parse-getchallenge` | `getchallenge 0 "TEST_ONLY_challenge"` | `Flag=0`,`Value` 捕获 |
| `handshake/parse-connect` | `connect TEST_ONLY_field1 "TEST_ONLY_field2"` | 两字段分别捕获 |
| `handshake/getchallenge-malformed` | `getchallenge 0 noquotes` / `heartbeat` | `MalformedArgument` / 非 getchallenge |
| `handshake/duplicate-request-detected` | 同 peer 同字节两次 | 第二次判重(计数 2) |
| `handshake/unproven-surface-isolated` | — | 8 项未证实面齐全 |
| `session/handshake-legal-transitions` | 6 条合法转移 | 全部 `true` |
| `session/handshake-illegal-transitions` | 7 条非法转移 | 全部 `false` |
| `session/challenge-cannot-connect-directly` | getchallenge → challengeResponse | 停在 `ChallengeValidated` |
| `session/connect-requires-validated-challenge` | 直接 connect | 拒绝,状态不变 |
| `session/challenge-timeout` | 时钟推进超限 | `TimedOut`,`Challenge` 阶段 |
| `session/connect-timeout` | connect 阶段推进超限 | `TimedOut`,`Connect` 阶段 |
| `session/connect-reject` | `connectReject TEST_ONLY_reason` | `Rejected`,detail 捕获 |
| `session/unknown-response-does-not-connect` | 未知响应 + 错阶段响应 | 状态不变,不建会话 |
| `session/duplicate-getchallenge-refused` | 重复 getchallenge | 拒绝 |
| `session/connect-response-needs-evidence` | 空 evidence 拒绝;带 id 接受 | 仅显式证据可 `Connected` |
| `session/challenge-connect-correlation` | 全流程 | challenge 值跨阶段保留 |
| `session/state-machine-clock-separated` | 注入时钟 | 相位耗时随注入时钟 |
| `protocol/test-only-fixtures-are-marked` | 夹具类型 | 带 `[TestOnly]`,`TEST_ONLY_` 前缀 |

> 所有模拟报文均来自 `HandshakeTestFixtures`,该类带 `[TestOnly]` 且每个字面量以 `TEST_ONLY_` 开头。

## 5. 历史不可变性与基线保护

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\verify-history-immutability.ps1
```

结果:`checked=547 failures=0` → **`HISTORY_IMMUTABLE_OK`**。
040–046 历史产物与原始客户端基线**未修改**。

## 6. 已知失败项

- **无测试失败项。**
- **未验证(显式阻塞,非失败):** 最终 CODOL 客户端兼容性、真实服务端握手、challenge 算法、
  端到端连接、in-match 收包链。
- 本轮唯一测试失败(开发期)是 `session/connect-timeout` 暴露的 `TimeoutPhase` 计算 bug,
  已修复后全绿;该失败/修复过程记录于此,未隐藏。
