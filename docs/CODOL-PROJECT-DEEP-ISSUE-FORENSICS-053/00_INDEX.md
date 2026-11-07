# 00 — CODOL 深度问题取证 · 入口

> 任务 `CODOL-PROJECT-DEEP-ISSUE-FORENSICS-053`　日期 2026-10-29
> **覆盖：全部 92 条历史 Issue**（原 7 条 P0 + 本轮补齐 85 条）

## 一、覆盖与完成度

| fix_readiness | 数量 |
|---|---|
| BLOCKED_BY_DEPENDENCY | 11 |
| BLOCKED_BY_EVIDENCE | 7 |
| FIX_READY | 28 |
| INVESTIGATION_READY | 32 |
| OBSOLETE | 11 |
| RESOLVED_VERIFIED | 3 |

| 优先级 | 数量 |
|---|---|
| NONE | 6 |
| P0 | 7 |
| P1 | 29 |
| P2 | 41 |
| P3 | 9 |

## 二、登记数与差异说明

上一轮台账登记 **92** 条；本轮为 **92** 条全部建档。
任务书提到 79 条未完成，其算式为 92 − 7(P0 已做) − 6(已闭合) = 79；
**本轮的 85 = 92 − 7**，即把 6 条已闭合项（1 RESOLVED_VERIFIED + 5 OBSOLETE）也建立了档案。

## 三、文档导航

| 文件 | 内容 |
|---|---|
| `01_EXECUTIVE_TECHNICAL_FINDINGS.md` | 技术结论摘要 |
| `02_FULL_PROJECT_TECHNICAL_HISTORY.md` | 与本批次相关的历史 |
| `03_ROOT_CAUSE_DEPENDENCY_ANALYSIS.md` | 根因与依赖 |
| `04_CRITICAL_PATH_TO_PLAYABLE_BATTLE.md` | 最小可玩关键路径 |
| `05_FIX_READINESS_REPORT.md` | 修复就绪度（全量） |
| `06_MISSING_EVIDENCE_REPORT.md` | 缺失证据 |
| `07_HISTORICAL_REGRESSION_ANALYSIS.md` | 历史回归 |
| `08_FINAL_TECHNICAL_ASSESSMENT.md` | 最终技术评估 |
| `CONNECTION_REGRESSION_DIFFERENTIAL.md` | 10-26 vs 10-29 全差分 |
| `P0_JOINT_ANALYSIS.md` | P0 联合分析 |
| `GAMESTATE_PROTOCOL_FORENSICS.md` / `SNAPSHOT_PROTOCOL_FORENSICS.md` | 协议专项 |
| `UNWIRED_MODULES_FORENSICS.md` | 未接线模块 |
| `NEXT_AGENT_HANDOFF.md` | 可直接接手 |
| `ISSUES/` | 92 份独立档案 |
| `FIX_PACKAGES/` | 28 个 |
| `INVESTIGATION_PACKAGES/` | 50 个 |
| `*.json` / `*.csv` | 6 个机器可读数据库 |
| `verify_forensics.py` | 自检 |
