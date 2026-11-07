# G3 状态复核与协调（001）

> 任务：`CODOL-KEYFLOW-LENGTH-COMPATIBILITY-001`
> 性质：只读复核；不覆盖原始 G3 测试矩阵、CSV、差异报告或决策文件。
> 实时互通：**NOT-OBSERVED**。

## 1. 原 G3 状态

原 `CODOL_G3_DECISION_001.md` 记录：

| 项 | 原值 |
|---|---|
| G3 | `PARTIAL PASS / CONDITIONAL` |
| TC-16…TC-32 | 16 PASS / 0 FAIL / 1 BLOCKED / 0 NOT-EXECUTED |
| 原阻塞 | TC-27 `BLOCKED-INSUFFICIENT-SPEC` |
| 主要限制 | 序列号模型只有反汇编级证据，原版失败处置未验证，参考 parser 上限差异未分层 |

## 2. 本任务复核后的增量事实

### 2.1 TC-27

Counter-boundary 静态审计确认：

```text
old expected = 0xFFFFFFFF
received seq = 0
store (old+1) = 0
compare 0 with old 0xFFFFFFFF -> reject
failure path sets object state 4
```

因此：

| 项 | 复核后状态 |
|---|---|
| 回绕比较行为 | `CONFIRMED-STATIC` |
| expected 回写值 | `CONFIRMED-STATIC`：0 |
| 原“expected unchanged”模型 | `CONFLICTING-EVIDENCE`，已被修正 |
| 同一连接后续行为 | `UNRESOLVED` |
| 原版运行时行为 | `NOT-OBSERVED` |

### 2.2 长度限制

Counter-boundary 与长度兼容性复核确认：

- 本地 parser：外层 `ln > 0x100000` 时拒绝/保留余量。
- 冻结客户端：密文长度 `ct_len >= 0xFFFFFF` 时走长度/帧错误路径，且要求 16B 对齐。
- 客户端静态等价的最大外层长度：`0x100000E`。
- 本地 parser 下最大对齐外层长度：`0xFFFFE`。
- 首个客户端静态合法但本地 parser 拒绝的对齐外层值：`0x10000E`。
- 这是独立兼容性缺口，不自动推翻 G3 小帧结论。

## 3. 建议的 G3 状态登记

以下仅为本任务的协调建议；原文件保持只读。

| 用例 | 原状态 | 复核后建议 | 备注 |
|---|---|---|---|
| TC-16…TC-24 | PASS | PASS，不变 | 小帧固定向量与 MAC/布局结果不受影响 |
| TC-25 | PASS | PASS（结果不变，状态注记修正） | “重复拒绝”不变；失败后 expected 会先推进 |
| TC-26 | PASS | PASS（结果不变，状态注记修正） | “跳号拒绝”不变；失败后 expected 会先推进 |
| TC-27 | BLOCKED-INSUFFICIENT-SPEC | **PASS (STATIC BEHAVIOR RECORDED)** | 仅表示静态行为已记录；运行时 `UNRESOLVED` |
| TC-28 | PASS | PASS，不变 | keepalive 分支不变 |
| TC-29 | PASS | PASS（范围注记修正） | 原测试不能代表完整大帧兼容性；外层长度和密文长度分层 |
| TC-30…TC-32 | PASS | PASS，不变 | 截断/短帧/对齐拒绝结果不变 |
| G3 总状态 | PARTIAL PASS / CONDITIONAL | **PARTIAL PASS / CONDITIONAL（不变）** | 新的模型更正和大帧缺口意味着不能无条件升级 |

## 4. 建议登记到统一问题台账

```text
Q-LEN-01:
  本地 parser 外层 ln 上限 0x100000
  vs 冻结客户端密文 ct_len < 0xFFFFFF
  客户端等价最大外层 ln = 0x100000E
  状态: CONFIRMED-STATIC（差异）
  运行影响: UNRESOLVED
  决策: 不扩大 parser；记录适用范围；若目标要求大帧，另立变更

Q-TC27-01:
  TC-27 回绕边界
  状态: CONFIRMED-STATIC
  运行时: NOT-OBSERVED
  原 G3 阻塞状态可由静态行为记录替代，但不得标记为运行时验证
```

## 5. 决策规则复核

| 条件 | 当前处理 |
|---|---|
| 目标使用场景不需要超过 `0x100000` 的帧 | 保持 parser 不变，记录适用范围；不需要追求数值一致 |
| 目标实际要求更大帧 | 先确认完整帧格式、长度公式和安全边界，再提出独立变更和回归测试 |
| 需要运行时兼容结论 | 进入授权隔离环境，另行采集运行时证据；本任务不执行 |
| 需要升级 G3 | 本任务不自动升级；TC-27 static pass、序列状态修正和大帧缺口必须分别登记 |

## 6. 最终协调结论

```text
G3 = PARTIAL PASS / CONDITIONAL
TC-27 = PASS (STATIC BEHAVIOR RECORDED)
Sequence failure-state model = CORRECTED
Large-frame parser compatibility = OPEN/UNRESOLVED
Runtime interoperability = NOT-OBSERVED
```

本复核**不覆盖**原 G3 测试矩阵，不修改历史哈希，不提升 G4/G5，也不改变实时互通状态。