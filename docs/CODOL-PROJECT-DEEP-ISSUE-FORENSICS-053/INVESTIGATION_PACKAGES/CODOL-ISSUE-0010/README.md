# CODOL-ISSUE-0010 — INVESTIGATION PACKAGE（不是修复任务包）

> 本包的 `FIX_READINESS_MATRIX.csv` 判定为 `can_fix_now = false`，
> 因此**不生成 FIX_PACKAGE**。这里给出的是取证任务，不是补丁任务。

## 标题
房间下行：先证明客户端到底有没有在读

## 完整档案
[`../../ISSUES/CODOL-ISSUE-0010.md`](../../ISSUES/CODOL-ISSUE-0010.md)

## 本包包含
- `KNOWN_FACTS.md` — 已证明的事实（每条带出处）
- `UNKNOWN_FACTS.md` — 未知事实与假设矩阵
- `TARGET_SOURCE.md` — 需要检查的精确源码位置
- `EXPERIMENT.md` — 最小实验、预期结果、判断标准

## 交付给下一个 Agent 时的一句话
先读 `EXPERIMENT.md`；在拿到实验结果之前不要写任何补丁。
