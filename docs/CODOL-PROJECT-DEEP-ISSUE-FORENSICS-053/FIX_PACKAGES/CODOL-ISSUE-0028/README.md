# CODOL-ISSUE-0028 — 跳跃在 usercmd 网络路径上不可能触发（walking 从不被刷新）

> fix_readiness = **FIX_READY**
> 完整档案：[`../../ISSUES/CODOL-ISSUE-0028.md`](../../ISSUES/CODOL-ISSUE-0028.md)

## 下一步

在 codol_movement_process_usercmd_dt 里按 cmd->buttons 的跳位设置 vz，并用 trace 维护 on_ground。

## 上游依赖

无
