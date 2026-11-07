# CODOL-ISSUE-0032 — 投射物/爆炸、模式击杀、复活、复制层全部定义但从未被调用

> fix_readiness = **FIX_READY**
> 完整档案：[`../../ISSUES/CODOL-ISSUE-0032.md`](../../ISSUES/CODOL-ISSUE-0032.md)

## 下一步

先在 combat.c 的 killed 处接 mode_player_killed，再跑一次确认日志链。

## 上游依赖

CODOL-ISSUE-0030
