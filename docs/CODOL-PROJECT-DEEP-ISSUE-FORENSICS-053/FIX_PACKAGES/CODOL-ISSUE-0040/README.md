# CODOL-ISSUE-0040 — 多客户端/重连：per-connection 重置只在 key-exchange 分支发生

> fix_readiness = **FIX_READY**
> 完整档案：[`../../ISSUES/CODOL-ISSUE-0040.md`](../../ISSUES/CODOL-ISSUE-0040.md)

## 下一步

抽出 reset_session_state() 并从 assoc 新建处统一调用。

## 上游依赖

CODOL-ISSUE-0034
