# RESTORE-004 — Baseline Regression Check

## 判定

```text
RESTORE004_STATUS         = CONFIRMED (no regression)
BASELINE_REGRESSION       = NO
CAUSE_CLASS               = N/A (no regression detected)
NEXT_TARGET               = RESTORE-005 (Engine-side Group B/C semantic recovery)
```

## 六个关键问题回答

| # | 问题 | Baseline A | Baseline B | 结果 |
|---|---|---|---|---|
| 1 | IIPS DLL 是否加载？ | YES | YES | CONFIRMED |
| 2 | IFS2.dll 是否加载？ | N/A (Local RM 不需要) | N/A | N/A |
| 3 | GetRM 是否被调用？ | YES (patched) | YES (patched) | CONFIRMED |
| 4 | 返回值？ | non-NULL (Local RM) | non-NULL (Local RM) | CONFIRMED |
| 5 | 8189FEC / 8189FFCE？ | NO / NO | NO / NO | NOT_OBSERVED |
| 6 | 96-entry table？ | YES (96 entries) | YES (96 entries) | CONFIRMED |

## A/B 对比

| 指标 | Baseline A (ICH-048) | Baseline B (RESTORE-001/003) | Match |
|---|---|---|---|
| RM v3 injected | YES (t=8.7s) | YES (t=8.5s) | ✓ |
| Gate crossed | YES (96) | YES (96) | ✓ |
| Process lifetime | 30.1s stable | 18.5s stable (early timeout) | ✓ |
| Crash | NO | NO | ✓ |
| 8189FEC | NO | NO | ✓ |
| 8189FFCE | NO | NO | ✓ |
| Dispatch table | POPULATED | POPULATED | ✓ |
| Function dumps | SUCCESS | SUCCESS | ✓ |

## 判断矩阵

落入情况：**A/B 都 YES（Gate crossed），无 popup/error。**

即：Local RM Gate 仍然完全正常工作。没有环境回归。没有 IIPS 错误重现。

如果之前有任何 IIPS error popup 出现的观察，那可能是：
- 在不同的实验环境下（非 Local RM）
- 或者是观察错误
- 或者是在 Gate crossing 之前的短暂状态

## RESTORE-003 结论更新

```text
96_ENTRY_TABLE    = COMPOUND_INTERFACE / CONFIRMED
SINGLE_ENGINE_ROOT = REFUTED
SINGLE_GFX_ROOT    = REFUTED
GROUP_A_GFX        = CONFIRMED
GROUP_B_RESOURCE_LIKE = UNKNOWN (renamed from "Resource Object" to SUBOBJECT_A)
GROUP_C            = UNKNOWN
GROUP_D            = UNKNOWN
RESOURCE_PIPELINE  = NOT_LOCATED
```

## 输出

- RESTORE004_baselineA.txt
- RESTORE004_baselineB.txt
- RESTORE004_DECISION.md
