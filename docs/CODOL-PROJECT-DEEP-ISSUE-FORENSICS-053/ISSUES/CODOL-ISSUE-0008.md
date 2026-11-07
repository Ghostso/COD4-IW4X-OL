# CODOL-ISSUE-0008 — 启动单发令牌与提权 agent 是隐性外部依赖

> 深度取证档案 · 2026-10-29 · `CODOL-PROJECT-DEEP-ISSUE-FORENSICS-053`

---

## 1. 问题精确定义

run_frozen_chain_once.py（行 315-335）要求 CODOLServer/logs/elevated_agent.json 存在、debug_privilege=true 且 PID 存活，否则拒绝启动。2026-10-29 E1 时原 agent(pid 5180) 已死，必须用 Start-Process -Verb RunAs 重新拉起（新 pid 3892 / port 56072）。

## 2. 历史首次发现过程

- **首次发现**：UNKNOWN（`run_codol_001/run_frozen_chain_once.py`）
- **最近验证**：2026-10-29 (E1: agent restarted, pid 3892)
- **所属系统**：`startup`　**优先级**：P1　**登记状态**：`OPEN`　**严重度**：high
- **是否阻塞可玩战斗**：否

## 3. 全部相关历史实验

| 日期 | 实验/事件 | 结果 |
|---|---|---|
| 2026-10-28 | agent pid 5180 写入 elevated_agent.json | 当时可用 |
| 2026-10-29 | E1 开始前检测到 pid 5180 已死 | 必须手工重启 |
| 2026-10-29 | 重启后 pid 3892/debug=True | E1 正常启动 |

## 4. 原始证据及 SHA-256

| Evidence ID | 类型 | 路径 | 定位 | 能证明 | 不能证明 |
|---|---|---|---|---|---|
| EV-0008-01 | source | `run_codol_001/run_frozen_chain_once.py` | 315-335 | agent 检查 | — |
| EV-0008-02 | location | `elevated_agent.json` | — | pid/port/token/debug_privilege | — |
| EV-0008-03 | location | `CODOLServer/_mainline/elevated_agent.py` | 142-153 | 自行写 state 文件并 serve_forever | — |

> 完整哈希与存在性见 `EVIDENCE_INDEX.json`；本表只列与该 Issue 直接相关的条目。

## 5. 当前源码位置

| 文件 | 行 | 说明 |
|---|---|---|
| `run_codol_001/run_frozen_chain_once.py` | 315-335 | agent 检查 |

## 6. 关键函数及调用关系

| 文件/地址 | 行/位置 | 作用 |
|---|---|---|
| `elevated_agent.json` | — | pid/port/token/debug_privilege |
| `CODOLServer/_mainline/elevated_agent.py` | 142-153 | 自行写 state 文件并 serve_forever |

## 7. 客户端逆向证据

`NOT_APPLICABLE` — 该问题（CODOL-ISSUE-0008，系统 `startup`）不涉及客户端逆向。

## 8. 网络协议字段及字节布局

`NOT_APPLICABLE` — 该问题（CODOL-ISSUE-0008，系统 `startup`）不涉及线上协议字段与字节布局。

## 9. 完整数据流

```
人工 UAC → elevated_agent.py → 写 state → launcher 读 state → 远程执行 run_all.py
```

## 10. 第一条未闭合调用边

**agent 的健康检查与自动重启机制不存在。**

## 11. 已确认事实

- agent 死后 launcher 会拒绝启动（10-29 实测）
- 重启后 E1 成功

## 12. 尚未确认的假设

- agent 在什么情况下会退出（当前无日志）

## 13. 已排除的假设

- 'agent 每次 run 都换 token 导致失败'——token 由 agent 写入、launcher 读取，不存在不匹配

## 14. 历史修复尝试

| 时间 | 改动 | 结果 |
|---|---|---|
| 2026-10-29 | 手工 Restart（Start-Process -Verb RunAs） | 有效但不可自动化 |

## 15. 当前代码状态

launcher 的检查逻辑完整；缺的是 agent 生命周期管理。

## 16. 最小复现条件

停掉 agent 进程后跑 launcher → 'refusing launch: elevated agent pid=… is unavailable'。

## 17. 最小验证实验

**实验 B8**

| 项 | 内容 |
|---|---|
| 步骤 | 1. 查看 elevated_agent.py 是否写退出原因日志<br>2. 加一个 ping 健康检查到 preflight |
| 通过判据 | preflight 能区分'agent 不在'与'技术失败' |
| 失败判据 | — |
| 成本 | 离线 30 分钟 |

## 18. 条件式修复方案

**方案A：preflight 里对 agent 做一次 ping，失败时给出明确处置提示（含重新拉起命令）。**

**方案B：由 launcher 自己以 RunAs 拉起 agent（需要 UAC，不能完全静默）。**

## 19. 修改影响分析

减少'环境问题被误判为技术问题'的情况。

## 20. 可测量的验收标准

1. 每个 run 的 preflight.json 记录 agent PID/端口/版本，且失败原因可区分环境与技术。

## 21. 回归测试方案

preflight 断言 agent ping 成功。

## 22. 修复准备度

**FIX_READY**

- **下一步**：在 launcher 的 agent 检查处增加 ping + 明确报错文案。
- **上游依赖**：无

---