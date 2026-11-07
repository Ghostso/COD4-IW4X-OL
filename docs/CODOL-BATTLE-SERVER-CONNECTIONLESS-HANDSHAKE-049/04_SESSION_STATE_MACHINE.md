# 04 — 连接/会话状态机

**实现:** `src\Codol.BattleServer\Sessions\HandshakeStateMachine.cs`(独立于 `ClientSession` 的传输生命周期模型)。
**目的:** 让握手业务逻辑在无 socket 的情况下可推理、可测试,并保证未验证的 challenge 不能进入 `Connected`。

---

## 1. 状态

| 状态 | 语义 |
|---|---|
| `Disconnected` | 初始/复位 |
| `ChallengePending` | 已收到合法 `getchallenge` |
| `ChallengeValidated` | 已收到 `challengeResponse` 并捕获其值(算法未校验,仅结构) |
| `ConnectPending` | 已收到合法 `connect` |
| `Connected` | 仅由显式、带证据 id 的响应接受进入 |
| `Rejected` | 服务端 `connectReject` |
| `TimedOut` | 阶段超时 |

## 2. 合法转移(完整表,代码 `IsAllowed` 与此一致)

| From | To | 触发 |
|---|---|---|
| Disconnected | ChallengePending | 接受 `getchallenge`(非重复) |
| ChallengePending | ChallengeValidated | 接受非空 `challengeResponse` |
| ChallengePending | Rejected / TimedOut | 显式拒绝 / challenge 超时 |
| ChallengeValidated | ConnectPending | 接受 `connect`(非重复) |
| ChallengeValidated | Rejected / TimedOut | 显式拒绝 / challenge 超时 |
| ConnectPending | Connected | `AcceptConnectResponse(evidenceId)` |
| ConnectPending | Rejected | 接受 `connectReject` |
| ConnectPending | TimedOut | connect 超时 |
| Connected | Disconnected / TimedOut | 断开 / 超时 |
| Rejected / TimedOut | Disconnected | `Reset()` |

**除上表外一律非法**,`Transition` 抛 `HandshakeStateException`。

## 3. 强制不变量(验收要求逐条)

| 要求 | 实现手段 | 测试 |
|---|---|---|
| 未验证 challenge 不得转 `Connected` | `IsAllowed(ChallengePending, Connected) == false`;`challengeResponse` 只到 `ChallengeValidated` | `session/challenge-cannot-connect-directly` |
| 未证实响应不得当作成功连接 | `connectResponse` 仅返回提示,状态**不变**;`Connected` 只经 `AcceptConnectResponse(evidenceId)` | `session/connect-response-needs-evidence` |
| challenge 与 connect 上下文关联 | `ChallengeValue` 在 `ChallengeValidated` 捕获,延续到 connect 阶段 | `session/challenge-connect-correlation` |
| 超时/重复/无效/拒绝有测试 | 见 `05` | `session/challenge-timeout`、`session/connect-timeout`、`session/duplicate-getchallenge-refused`、`session/connect-reject` |
| 网络接收层与业务解耦 | 状态机只吃 `HandshakeFrame`;时钟 `IHandshakeClock` 可注入 | `session/state-machine-clock-separated` |
| 2697 不得作默认回退 | 状态机不引用 2697 | `protocol/registry-separates-versions`(既有) |

## 4. 超时模型(与 challenge/connect 分离)

- 两个独立上限:`ChallengeTimeoutMs`(默认 5000)、`ConnectTimeoutMs`(默认 5000);
- 进入新状态时重置 `PhaseStartedUnixMs`;
- `ExpireIfNeeded()` 按当前阶段选用上限;到期转 `TimedOut` 并记录 `TimeoutPhase`;
- `TimeoutPhase` 在 `TimedOut` 后仍报告**实际超时阶段**(修复自测试发现的 bug)。

## 5. 重复请求

- `RegisterClientRequest(peer, bytes)` 以 `peer|hex(bytes)` 为键;
- 首次返回 `true`;重复返回 `false` 并计数;
- 状态机在 `Disconnected` 阶段的重复 `getchallenge` → `DuplicateRequest`;
  在错误阶段的任何请求 → `UnexpectedCommand`。

## 6. 重置

`Reset()` 仅允许从 `Rejected`/`TimedOut`/`Disconnected`;清空 challenge/connect 上下文与重复计数。

## 7. 明确边界

- 状态机的"已验证"指**结构已捕获**,不是**算法已验证**;因此 `ChallengeValidated` 不是
  "challenge 正确"的断言。真正的算法校验是 `UnprovenHandshakeSurface.ChallengeValidation`。
- `Connected` 需要调用方提供**证据 id**,这是把"接口完整"与"官方兼容"分开的强制手段。
