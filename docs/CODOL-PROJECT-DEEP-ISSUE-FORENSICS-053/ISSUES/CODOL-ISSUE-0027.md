# CODOL-ISSUE-0027 — 11 个 playerState 字段仍用 XOR 增量而三份参照都写裸值

> 深度取证档案 · 2026-10-29 · `CODOL-PROJECT-DEEP-ISSUE-FORENSICS-053`

---

## 1. 问题精确定义

离线演示：输入相同、帧 2 差 8 字节；未动的值编码成 0 ⇒ 等于告诉客户端 position=(0,0,0)。2026-10-24 已按结论 1 改为裸值并实机验证'一条成一条坏'——裸值那条成了（用户确认'弹药、换弹正常了''进游戏默认主武器了'），idx61 那条坏了并已回退。

## 2. 历史首次发现过程

- **首次发现**：2026-10-24（`docs/SNAPSHOT_FIELD_DIFF_20261024.md`）
- **最近验证**：2026-10-24 (SNAPSHOT_RAWFIX_20261024_1357)
- **所属系统**：`battle-snapshot`　**优先级**：P1　**登记状态**：`UNVERIFIED`　**严重度**：high
- **是否阻塞可玩战斗**：是

## 3. 全部相关历史实验

| 日期 | 实验/事件 | 结果 |
|---|---|---|
| 2026-10-24 | SNAPSHOT_FIELD_DIFF 列出 11 个 XOR 字段与 idx61 恒 2047 | 确认 |
| 2026-10-24 13:57 | SNAPSHOT_RAWFIX：XOR→裸值 | 用户确认弹药/换弹正常 |
| 2026-10-24 13:57 | 同轮 idx61→动态 2046 | 飞行模式 + 开镜失效，已回退 |
| 2026-10-25 | 离线对拍器 offline_snapshot_crosscheck 22/22 | 全绿 |

## 4. 原始证据及 SHA-256

| Evidence ID | 类型 | 路径 | 定位 | 能证明 | 不能证明 |
|---|---|---|---|---|---|
| EV-0027-01 | source | `battle/snapshot.c` | 330-420 | playerState 字段写入区 | — |
| EV-0027-02 | location | `tools/offline_snapshot_crosscheck.py` | — | 离线对拍器 | — |
| EV-0027-03 | location | `tools/diff_snapshot_impls.py` | — | 131 锚点对照 | — |

> 完整哈希与存在性见 `EVIDENCE_INDEX.json`；本表只列与该 Issue 直接相关的条目。

## 5. 当前源码位置

| 文件 | 行 | 说明 |
|---|---|---|
| `battle/snapshot.c` | 330-420 | playerState 字段写入区 |

## 6. 关键函数及调用关系

| 文件/地址 | 行/位置 | 作用 |
|---|---|---|
| `tools/offline_snapshot_crosscheck.py` | — | 离线对拍器 |
| `tools/diff_snapshot_impls.py` | — | 131 锚点对照 |

## 7. 客户端逆向证据

`NOT_APPLICABLE` — 该问题（CODOL-ISSUE-0027，系统 `battle-snapshot`）不涉及客户端逆向。

## 8. 网络协议字段及字节布局

本 Issue 的协议字段与字节布局：见 §6 的 `tools/offline_snapshot_crosscheck.py`，以及 `05_PROTOCOL_GAPS.md` 中 battle-snapshot 对应小节。

## 9. 完整数据流

```
svc->snap_from / snap_cur → bw_* 写字段
```

## 10. 第一条未闭合调用边

**当前源码里哪些字段仍是 XOR（需逐字段重读）。**

## 11. 已确认事实

- 裸值写法实机有效（弹药/换弹/默认主武器）
- idx61 动态写 2046 会进飞行模式

## 12. 尚未确认的假设

- 11 个字段的当前逐个状态

## 13. 已排除的假设

- 'XOR 是参照的做法'——三份参照都写裸值

## 14. 历史修复尝试

| 时间 | 改动 | 结果 |
|---|---|---|
| 2026-10-24 | XOR→裸值 | 成功一半（位置字段另属 ISSUE-0025） |

## 15. 当前代码状态

已改为裸值；idx61 保持 false(2047)。

## 16. 最小复现条件

跑 tools/offline_snapshot_crosscheck.py；逐字段比对 snap_from/snap_cur 的写入。

## 17. 最小验证实验

**实验 B27**

| 项 | 内容 |
|---|---|
| 步骤 | 1. 逐字段列出当前写入方式（裸值/XOR）<br>2. 对每个字段做一次'改成裸值→实机→回退'的 A/B |
| 通过判据 | 字段与实机表现一一对应 |
| 失败判据 | 某字段改动无差异 ⇒ 该字段未被使用 |
| 成本 | 每字段 1 轮 |

## 18. 条件式修复方案

**方案A：全部改为裸值（已部分完成）。**

**方案B：保持现状，只补文档记录每个字段的依据。**

## 19. 修改影响分析

直接影响 Snapshot 正确性与可玩性（位置/弹药）。

## 20. 可测量的验收标准

1. 所有字段的编码方式与实测对照表一致，且有实机确认。

## 21. 回归测试方案

offline_snapshot_crosscheck 全绿 + 实机 ack 递增。

## 22. 修复准备度

**INVESTIGATION_READY**

- **下一步**：B27：先重读 snapshot.c 逐字段状态。
- **上游依赖**：无

---