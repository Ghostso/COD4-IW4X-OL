# 修改计划

**方案A**：方案A：preflight 里对 agent 做一次 ping，失败时给出明确处置提示（含重新拉起命令）。

**方案B**：方案B：由 launcher 自己以 RunAs 拉起 agent（需要 UAC，不能完全静默）。

## 影响

减少'环境问题被误判为技术问题'的情况。
