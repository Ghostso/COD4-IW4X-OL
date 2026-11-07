# TV01_TV06_TEST_RESULTS — 离线测试实际执行结果

**执行对象：** `build\bin\OobStateMachine.exe`（本任务独立构建，19,456 B）
**执行环境：** 本机 Windows，无网络、无游戏、无服务器、无注入
**实际结果：** **`pass=84  fail=0`**，`RESULT: ALL GREEN`，**exit code = 0**
**原始输出：** `build\selftest.output.txt`（4,187 B）
**退出码存档：** `build\selftest.exitcode.txt`
**确定性复核：** 二次运行输出与首次输出 SHA-256 **相同**（`build\selftest.run2.txt`）

> **声明：** 这是**离线自测**。**未**执行任何真实客户端 E2E；
> **不**声称已验证与真实客户端兼容。
> 合成数据只验证**实现内部一致性**。

---

## 1. 逐测试结果

### TV-01 — 状态 3 进入已证实的 `getchallenge` 路径（6 断言，全通过）

| 断言 | 结果 |
|---|---|
| `state 3 selects GetChallenge` | PASS |
| `state 3 gate reason Ok` | PASS |
| `state 3 shouldSend` | PASS |
| `payload equals 'getchallenge 0 "abc123"'` | **PASS**（首次运行为 FAIL，见 §3） |
| `payload has exact prefix/suffix` | PASS |
| `GetChallengeFormat is 19 bytes` | PASS |

**证据锚点：** 分支 `0x1C070E`、格式串 push `0x1C071E`、vsprintf `0x1C0729`。
**边界：** 使用注入种子 `"abc123"`；种子生成逻辑本身**未**建模（`U-10`）。

### TV-02 — 状态 6 进入已证实的 `heartbeat` 路径（5 断言，全通过）

| 断言 | 结果 |
|---|---|
| `state 6 selects Heartbeat` | PASS |
| `state 6 shouldSend` | PASS |
| `heartbeat payload is bare token` | PASS |
| `HeartbeatToken exact` | PASS |
| `HeartbeatToken is 9 bytes` | PASS |

**证据锚点：** 分支 `0x1C0EBB`（`push 0x00DBFE40`）。

### TV-03 — 状态 4/5 不落入未经确认的行为分支（11 断言，全通过）

| 断言 | 结果 |
|---|---|
| `state 4 -> Connect (own branch 0x1C0776)` | PASS |
| `state 5 -> Stats (own branch 0x1C0E07)` | PASS |
| `state 4 payload intentionally NOT modelled` | PASS（返回 `null`） |
| `state 5 payload intentionally NOT modelled` | PASS（返回 `null`） |
| `state -1 / 0 / 1 / 2 / 7 / 8 / 99 rejected (StateNotEligible)` | PASS ×7 |

**说明：** 状态 4/5 的目标分支**确实存在**（因此不是"未知分支"），
但其 **payload 组合未证实**，所以实现显式拒绝构造 payload，
而**不是**用默认成功路径代替。

### TV-04 — `challengeResponse` 与 `connectResponse` 识别与分派互相独立（10 断言，全通过）

| 断言 | 结果 |
|---|---|
| `challengeResponse recognised` | PASS |
| `connectResponse recognised` | PASS |
| `the two tokens classify differently` | PASS |
| `connectReject recognised` | PASS |
| `'connect' alone is NOT 'connectResponse' (no prefix match)` | PASS |
| `heartbeatresponse recognised` | PASS |
| `statResponse recognised` | PASS |
| `disconnect_ack recognised` | PASS |
| `echo recognised` | PASS |
| `uppercase token still recognised (ASCII fold)` | PASS |

**说明：** 第 5 条专门验证**不是前缀匹配**——目标用 `0x7FFFFFFF` bound 比到 NUL。

### TV-05 — 节流边界（28 断言，全通过；**限定为内部一致性**）

| 组 | 断言 | 结果 |
|---|---|---|
| 状态 3 | suppressed@2999 / allowed@3000 / allowed@3001 / suppressed@0 / threshold==3000 | PASS ×5 |
| 状态 4 | 同上（复用 3000 比较） | PASS ×5 |
| 状态 5 | suppressed@99 / allowed@100 / allowed@101 / threshold==100 | PASS ×4 |
| 状态 6 | suppressed@499 / allowed@500 / allowed@501 / threshold==500 | PASS ×4 |
| 重复触发 | first@500 allowed / immediate repeat suppressed / @999 suppressed / @1000 allowed | PASS ×4 |
| 状态 3 记账 | allowed@3000 / `OnAllowed(3)` 刷新 `[ebx+0x30]` 槽 / 立即重复被抑制 | PASS ×3 |
| **槽位独立** | `状态 3 用 3000 槽，不用 100/500 槽` / `状态 5 用自己的槽` / `状态 6 用自己的槽` | PASS ×3 |

**⚠ 语义边界（任务书 §四明确要求）：**
**3000 / 100 / 500 的"作用（业务语义）尚未确认"**，因此本组测试**只**声明：
「计时器与边界处理组件的**内部一致性**」。
**不**声称与目标客户端的**精确时序行为一致**。
具体而言：**未**确认 3000 是"状态驻留"、**未**确认 100 是"重试间隔"、**未**确认 500 是"心跳周期"。

**本轮已确认的是**：数值、适用状态、比较方向（`<` 抑制）、以及 3000 与 100/500 使用**不同计时源**。

### TV-06 — `cancelConnect` 不误清无关会话、不伪造成功（5 断言，全通过）

| 断言 | 结果 |
|---|---|
| `cancel for another session does not close ours` | PASS |
| `own cancel closes session` | PASS |
| `cancel never returns Connected` | PASS |
| `empty session id is a no-op` | PASS |
| `case-different session id does not match` | PASS |

**说明：** 最后一条验证 `Ordinal` 比较（不做大小写折叠）——与目标 OOB 令牌的**折叠**行为刻意相反，
因为会话标识比较属**服务器侧策略**（`U-08`），无目标证据支持折叠。

### ROBUSTNESS — 未知/空/截断/超长/缺终止符/无效状态（19 断言，全通过）

| 类别 | 断言 | 结果 |
|---|---|---|
| 未知令牌 | `unknown token -> Unrecognised` | PASS |
| 空报文 | `empty payload -> Unrecognised`、`null payload -> Unrecognised` | PASS ×2 |
| 缺终止符 | `missing terminator -> Unrecognised (server-side policy)` | PASS |
| 截断 | `truncated token -> Unrecognised` | PASS |
| 超长 | `overlong buffer with valid leading token -> recognised` | PASS |
| 偏移 | `offset-based classification works` | PASS |
| 无效状态 | `-2147483648 / -1 / 0 / 1 / 2 / 7 / 2147483647 -> None` | PASS ×7 |
| 门 2 | `no session -> NoSessionOrBusy`、`busy -> NoSessionOrBusy`、`no session -> shouldSend false` | PASS ×3 |
| 状态空间分离 | `server enum is its own space`、`'Connected' is not client state 3` | PASS ×2 |

**⚠ 拒绝行为定性：** 缺终止符、截断、未知令牌的拒绝是**服务器侧安全策略**，
**不是**目标客户端已确认行为（目标分支体未追踪，见 `U-06`）。

---

## 2. 汇总

| 测试组 | 断言数 | 通过 | 失败 |
|---|---:|---:|---:|
| TV-01 | 6 | 6 | 0 |
| TV-02 | 5 | 5 | 0 |
| TV-03 | 11 | 11 | 0 |
| TV-04 | 10 | 10 | 0 |
| TV-05 | 28 | 28 | 0 |
| TV-06 | 5 | 5 | 0 |
| ROBUSTNESS | 19 | 19 | 0 |
| **合计** | **84** | **84** | **0** |

（`[OK]` 计数实测 84，`[FAIL]` 计数实测 0。）

---

## 3. 测试过程中暴露并修复的实现缺陷（如实记录）

| # | 现象 | 判定 | 处置 |
|---|---|---|---|
| 1 | 首次构建 `CS1026/CS1002/CS1525` @ `SelfTest.cs:22/39/53` | 使用了 C# 7 的 `10_000` 数字分隔符，而 csc 4.0 不支持 | 改为 `10000`；重建通过 |
| 2 | 首次运行 `[FAIL] payload equals 'getchallenge 0 "abc123"'` | 实现用 C# `string.Format("{0}")` 去填目标的 **`%s`** 格式串，产出错误字符串 | 新增 `SprintfSubset.FormatS` 忠实实现 `%s` 替换；重建后全绿 |

> 缺陷 2 说明：**测试是可证伪的**。若不修，模块会把 `getchallenge 0 "abc123"` 错写成
> 含 `%s` 或含 `{0}` 的串，而这类错误只有在**线缆字符串层面**断言才能发现。

---

## 4. 未执行的验证（`NOT_RUN`）

| 项 | 状态 | 原因 |
|---|---|---|
| 真实客户端 E2E | **NOT_RUN** | 任务书 §五.6 与 §一 明确排除 |
| 真实网络收发 | **NOT_RUN** | 同上 |
| 与冻结服务器联调 | **NOT_RUN** | 本轮只交付独立模块 |
| 报文长度/分帧验证 | **NOT_RUN** | 无目标证据（`U-09`） |
