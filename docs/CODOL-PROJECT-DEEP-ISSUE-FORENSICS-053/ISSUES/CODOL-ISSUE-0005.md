# CODOL-ISSUE-0005 — 22/22 离线测试未覆盖三个关键探针与任何客户端联调

> 深度取证档案 · 2026-10-29 · `CODOL-PROJECT-DEEP-ISSUE-FORENSICS-053`

---

## 1. 问题精确定义

ctest 注册 22 项，2026-10-26 22:07 全部通过（22 Passed / 0 Failed）。但 probe_snapshot_size.c、probe_world_damage.c、sim_check.c、e2e_client.py 不在 ctest 里。

## 2. 历史首次发现过程

- **首次发现**：2026-10-29（`本次审计：CMakeLists 与 LastTest.log`）
- **最近验证**：2026-10-29
- **所属系统**：`build`　**优先级**：P2　**登记状态**：`PARTIALLY_RESOLVED`　**严重度**：medium
- **是否阻塞可玩战斗**：否

## 3. 全部相关历史实验

| 日期 | 实验/事件 | 结果 |
|---|---|---|
| 2026-10-26 22:07 | LastTest.log：22 Passed / 0 Failed |  |
| 2026-10-29 | 核对 CMakeLists 的 add_test 列表 | 3 个探针 + e2e 未注册 |

## 4. 原始证据及 SHA-256

| Evidence ID | 类型 | 路径 | 定位 | 能证明 | 不能证明 |
|---|---|---|---|---|---|
| EV-0005-01 | source | `CMakeLists.txt` | — | 22 个 add_test | — |
| EV-0005-02 | source | `build/Testing/Temporary/LastTest.log` | — | 全部通过记录 | — |
| EV-0005-03 | location | `tests/probe_world_damage.c` | — | 未注册 | — |
| EV-0005-04 | location | `tests/probe_snapshot_size.c` | — | 未注册 | — |
| EV-0005-05 | location | `tests/sim_check.c` | — | 未注册 | — |
| EV-0005-06 | location | `tests/e2e_client.py` | — | 未注册 | — |

> 完整哈希与存在性见 `EVIDENCE_INDEX.json`；本表只列与该 Issue 直接相关的条目。

## 5. 当前源码位置

| 文件 | 行 | 说明 |
|---|---|---|
| `CMakeLists.txt` | — | 22 个 add_test |
| `build/Testing/Temporary/LastTest.log` | — | 全部通过记录 |

## 6. 关键函数及调用关系

| 文件/地址 | 行/位置 | 作用 |
|---|---|---|
| `tests/probe_world_damage.c` | — | 未注册 |
| `tests/probe_snapshot_size.c` | — | 未注册 |
| `tests/sim_check.c` | — | 未注册 |
| `tests/e2e_client.py` | — | 未注册 |

## 7. 客户端逆向证据

`NOT_APPLICABLE` — 该问题（CODOL-ISSUE-0005，系统 `build`）不涉及客户端逆向。

## 8. 网络协议字段及字节布局

`NOT_APPLICABLE` — 该问题（CODOL-ISSUE-0005，系统 `build`）不涉及线上协议字段与字节布局。

## 9. 完整数据流

```
CMake → ctest → 22 项
```

## 10. 第一条未闭合调用边

**回归套件不含任何'客户端是否接受'的检查（那需要实机）。**

## 11. 已确认事实

- 22/22 在 2026-10-26 22:07 通过（有日志）
- 3 个探针与 e2e 不在 add_test 里

## 12. 尚未确认的假设

- 探针是否有隐藏的回归失败

## 13. 已排除的假设

(本 Issue 尚无已排除假设)

## 14. 历史修复尝试

(无历史修复尝试)

## 15. 当前代码状态

CMakeLists 只注册单元测试。

## 16. 最小复现条件

ctest -N 列出 22 项。

## 17. 最小验证实验

**实验 B5**

| 项 | 内容 |
|---|---|
| 步骤 | 1. 把三个探针注册为 ctest 用例<br>2. 为 e2e_client.py 建一个契约用例 |
| 通过判据 | ctest 项数 22→26 |
| 失败判据 | — |
| 成本 | 离线 1 小时 |

## 18. 条件式修复方案

**方案A：补注册探针；e2e 作为独立契约套件。**

**方案B：保持现状，另建 run 级断言脚本。**

## 19. 修改影响分析

回归套件无法发现世界/伤害/实体层退化。

## 20. 可测量的验收标准

1. ctest 覆盖探针；e2e_client 有可重复的契约用例。

## 21. 回归测试方案

—

## 22. 修复准备度

**FIX_READY**

- **下一步**：在 CMakeLists 增加三个 add_test。
- **上游依赖**：无

---