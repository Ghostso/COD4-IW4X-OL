# CODOL-ISSUE-0088 — 固化链的参考实现本身带 6 次重试与共享 GAME_ROOT

> 深度取证档案 · 2026-10-29 · `CODOL-PROJECT-DEEP-ISSUE-FORENSICS-053`

---

## 1. 问题精确定义

受保护的 run_all.py 默认 6 次重试、共享 GAME_ROOT，与'单发'纪律冲突。靠 run_frozen_chain_once.py 在副本上改写（换成 range(1,2)、替换 GAME_ROOT）来满足。

## 2. 历史首次发现过程

- **首次发现**：2026-10-21（`NEXT_RUN_BASELINE_DECISION_20261021.md`）
- **最近验证**：2026-10-29
- **所属系统**：`startup`　**优先级**：P2　**登记状态**：`PARTIALLY_RESOLVED`　**严重度**：medium
- **是否阻塞可玩战斗**：否

## 3. 全部相关历史实验

| 日期 | 实验/事件 | 结果 |
|---|---|---|
| 2026-10-21 | NEXT_RUN_BASELINE_DECISION 记录 |  |
| 2026-10-29 | E1 实测：launcher 的两处改写正常生效 |  |

## 4. 原始证据及 SHA-256

| Evidence ID | 类型 | 路径 | 定位 | 能证明 | 不能证明 |
|---|---|---|---|---|---|
| EV-0088-01 | source | `run_codol_001/run_frozen_chain_once.py` | 207-227 | GAME_ROOT 改写 | — |
| EV-0088-02 | source | `run_codol_001/run_frozen_chain_once.py` | 299-306 | retry 循环改写 | — |
| EV-0088-03 | location | `run_all.py（受保护）` | — | 6 次重试 + 共享 GAME_ROOT | — |

> 完整哈希与存在性见 `EVIDENCE_INDEX.json`；本表只列与该 Issue 直接相关的条目。

## 5. 当前源码位置

| 文件 | 行 | 说明 |
|---|---|---|
| `run_codol_001/run_frozen_chain_once.py` | 207-227 | GAME_ROOT 改写 |
| `run_codol_001/run_frozen_chain_once.py` | 299-306 | retry 循环改写 |

## 6. 关键函数及调用关系

| 文件/地址 | 行/位置 | 作用 |
|---|---|---|
| `run_all.py（受保护）` | — | 6 次重试 + 共享 GAME_ROOT |

## 7. 客户端逆向证据

`NOT_APPLICABLE` — 该问题（CODOL-ISSUE-0088，系统 `startup`）不涉及客户端逆向。

## 8. 网络协议字段及字节布局

`NOT_APPLICABLE` — 该问题（CODOL-ISSUE-0088，系统 `startup`）不涉及线上协议字段与字节布局。

## 9. 完整数据流

```
受保护 run_all.py → 副本改写 → 单发
```

## 10. 第一条未闭合调用边

**—**

## 11. 已确认事实

- 两处改写存在且有效（E1）

## 12. 尚未确认的假设

- —

## 13. 已排除的假设

(本 Issue 尚无已排除假设)

## 14. 历史修复尝试

| 时间 | 改动 | 结果 |
|---|---|---|
| 2026-10-19.. | 由 launcher 补齐 | 有效 |

## 15. 当前代码状态

launcher 已补齐。

## 16. 最小复现条件

直接跑受保护 run_all.py 应出现 6 次重试。

## 17. 最小验证实验

**实验 B88**

| 项 | 内容 |
|---|---|
| 步骤 | 1. 文档说明 launcher 的两处改写及其理由 |
| 通过判据 | 文档可查 |
| 失败判据 | — |
| 成本 | 离线 10 分钟 |

## 18. 条件式修复方案

**方案A：保持现状并文档化。**

**方案B：—**

## 19. 修改影响分析

纪律靠补丁维持，不是靠基线。

## 20. 可测量的验收标准

1. 文档说明 launcher 的两处改写及其理由。

## 21. 回归测试方案

—

## 22. 修复准备度

**FIX_READY**

- **下一步**：在 HANDOFF 里写明这两处改写。
- **上游依赖**：无

---