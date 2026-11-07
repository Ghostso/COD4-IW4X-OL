# CODOL-ISSUE-0007 — iips.ini 的 enable_iips 是隐性环境依赖，未纳入受保护清单

> 深度取证档案 · 2026-10-29 · `CODOL-PROJECT-DEEP-ISSUE-FORENSICS-053`

---

## 1. 问题精确定义

COD OL\iips.ini 的 enable_iips=0 导致本体 6 秒必崩；改为 1 后完整进大厅（模块 83→93、5E8 1→3、Auth 10→11、31 个 service 全部应答）。E1（2026-10-29）在本体上启动成功，说明该项仍为 1。

## 2. 历史首次发现过程

- **首次发现**：2026-10-27（`docs/PVE_BATTLESTART_STATUS_20261027_1220.md §0`）
- **最近验证**：2026-10-29 (E1 launch)
- **所属系统**：`startup`　**优先级**：P1　**登记状态**：`PARTIALLY_RESOLVED`　**严重度**：high
- **是否阻塞可玩战斗**：否

## 3. 全部相关历史实验

| 日期 | 实验/事件 | 结果 |
|---|---|---|
| 2026-10-27 | 定位 enable_iips=0 为 6 秒崩溃根因 | 改 1 后进大厅 |
| 2026-10-27 | 排除 ACE / .local / TAS 三条假设 | 均被实测排除 |
| 2026-10-29 | E1 本体启动成功 | 该值仍有效 |

## 4. 原始证据及 SHA-256

| Evidence ID | 类型 | 路径 | 定位 | 能证明 | 不能证明 |
|---|---|---|---|---|---|
| EV-0007-01 | source | `COD OL/iips.ini` | — | 游戏配置，非源码 | — |
| EV-0007-02 | location | `run_codol_001/run_frozen_chain_once.py` | 86-118 | preflight 目前**不**检查 iips.ini | — |

> 完整哈希与存在性见 `EVIDENCE_INDEX.json`；本表只列与该 Issue 直接相关的条目。

## 5. 当前源码位置

| 文件 | 行 | 说明 |
|---|---|---|
| `COD OL/iips.ini` | — | 游戏配置，非源码 |

## 6. 关键函数及调用关系

| 文件/地址 | 行/位置 | 作用 |
|---|---|---|
| `run_codol_001/run_frozen_chain_once.py` | 86-118 | preflight 目前**不**检查 iips.ini |

## 7. 客户端逆向证据

`NOT_APPLICABLE` — 该问题（CODOL-ISSUE-0007，系统 `startup`）不涉及客户端逆向。

## 8. 网络协议字段及字节布局

`NOT_APPLICABLE` — 该问题（CODOL-ISSUE-0007，系统 `startup`）不涉及线上协议字段与字节布局。

## 9. 完整数据流

```
run_frozen_chain_once.py → preflight → 启动 → iips.ini 被客户端读取
```

## 10. 第一条未闭合调用边

**没有任何清单记录 iips.ini 的期望值。**

## 11. 已确认事实

- enable_iips=1 时客户端可进大厅（两次实机）
- =0 时 6 秒必崩

## 12. 尚未确认的假设

- 除该键外还有哪些 iips.ini 键影响启动

## 13. 已排除的假设

- ACE 驱动杀进程
- `.local` 里补丁的 Base.dll
- TAS 注入

## 14. 历史修复尝试

| 时间 | 改动 | 结果 |
|---|---|---|
| 2026-10-27 | 把 enable_iips 改为 1（手工） | 有效，保留 |

## 15. 当前代码状态

无代码改动；iips.ini 已改为 1 并有 .bak 备份。

## 16. 最小复现条件

在干净副本上把 enable_iips 改回 0，启动客户端 → 6 秒内退出。

## 17. 最小验证实验

**实验 B7**

| 项 | 内容 |
|---|---|
| 步骤 | 1. 在 run preflight 中增加 iips.ini 关键项校验<br>2. 把当前值（1）写成期望值 |
| 通过判据 | preflight 会因 enable_iips≠1 而拒绝启动 |
| 失败判据 | — |
| 成本 | 离线 30 分钟 |

## 18. 条件式修复方案

**方案A：preflight 校验 iips.ini 的 enable_iips，并记录该文件哈希。**

**方案B：把 iips.ini 复制进 kit 并由 launcher 覆盖写入。**

## 19. 修改影响分析

消除'换机器/重装后莫名 6 秒崩'这一类问题。

## 20. 可测量的验收标准

1. preflight 会校验 iips.ini，不一致时拒绝启动并说明。

## 21. 回归测试方案

每次 run 的 preflight.json 记录 iips.ini 的路径与哈希。

## 22. 修复准备度

**FIX_READY**

- **下一步**：在 run_frozen_chain_once.py 的 verify_protected_baseline 之后加一段 iips.ini 校验。
- **上游依赖**：无

---