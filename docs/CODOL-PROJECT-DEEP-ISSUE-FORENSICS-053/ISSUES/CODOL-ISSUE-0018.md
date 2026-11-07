# CODOL-ISSUE-0018 — GAME_START_PAYLOAD(162B) 是靶场抓包常量，不是 coop 开局数据

> 深度取证档案 · 2026-10-29 · `CODOL-PROJECT-DEEP-ISSUE-FORENSICS-053`

---

## 1. 问题精确定义

离线解包显示 F807(=2047) 出现 10 次，正是快照'恒在空中'哨兵 ⇒ 确为靶场快照。实机触发+推送都成功但 PvE 仍停'战斗开始'、战斗服 0 收包。

## 2. 历史首次发现过程

- **首次发现**：2026-10-07（`codol_crypto.py:803-826 自述`）
- **最近验证**：2026-10-27
- **所属系统**：`lobby`　**优先级**：P2　**登记状态**：`OPEN`　**严重度**：high
- **是否阻塞可玩战斗**：否

## 3. 全部相关历史实验

| 日期 | 实验/事件 | 结果 |
|---|---|---|
| 2026-10-07 | 抓取 162B 常量 |  |
| 2026-10-26 | 实机推送成功但无效 |  |
| 2026-10-27 | 离线解包确认是靶场快照 |  |

## 4. 原始证据及 SHA-256

| Evidence ID | 类型 | 路径 | 定位 | 能证明 | 不能证明 |
|---|---|---|---|---|---|
| EV-0018-01 | source | `codol_crypto.py` | 803-826 | build_startgame_payload 与警告注释 | — |
| EV-0018-02 | location | `lobby_server.py` | 1147 | build_startgame_payload(_addr67, SESSION_ID, SEC_KEY) | — |

> 完整哈希与存在性见 `EVIDENCE_INDEX.json`；本表只列与该 Issue 直接相关的条目。

## 5. 当前源码位置

| 文件 | 行 | 说明 |
|---|---|---|
| `codol_crypto.py` | 803-826 | build_startgame_payload 与警告注释 |

## 6. 关键函数及调用关系

| 文件/地址 | 行/位置 | 作用 |
|---|---|---|
| `lobby_server.py` | 1147 | build_startgame_payload(_addr67, SESSION_ID, SEC_KEY) |

## 7. 客户端逆向证据

本 Issue（CODOL-ISSUE-0018）涉及客户端逆向的部分见 §6；相关专项见 `06_CLIENT_REVERSE_ENGINEERING_GAPS.md` 中 lobby 一节。

## 8. 网络协议字段及字节布局

本 Issue 的协议字段与字节布局：见 §6 的 `lobby_server.py`，以及 `05_PROTOCOL_GAPS.md` 中 lobby 对应小节。

## 9. 完整数据流

```
11/4 setRoomData(ready) → 推 162B → 客户端无反应
```

## 10. 第一条未闭合调用边

**真实 coop 开局数据；停服前的官方抓包（未见留存）。**

## 11. 已确认事实

- 162B 内含 10 次 F807
- 实机两轮均无效

## 12. 尚未确认的假设

- 真实 coop 开局数据的来源

## 13. 已排除的假设

- '这条是 coop 数据'

## 14. 历史修复尝试

| 时间 | 改动 | 结果 |
|---|---|---|
| 2026-10-26 | 实机推送 | 无效 |

## 15. 当前代码状态

build_startgame_payload 仍在，但区间 D 已不推。

## 16. 最小复现条件

解包 162B 看 F807 出现次数。

## 17. 最小验证实验

**实验 B18**

| 项 | 内容 |
|---|---|
| 步骤 | 1. 搜索 docs/ 与历史 run 是否留有停服前抓包<br>2. 若无，改用 dwRoomMessageStartGame 的 serialize |
| 通过判据 | 找到真实 coop 开局字节 |
| 失败判据 | 无留存 |
| 成本 | 离线 2 小时 |

## 18. 条件式修复方案

**方案A：改由 dwRoomMessageStartGame 承担开局（serialize 首段已解）。**

**方案B：保持现状但记录'不适用于 coop'。**

## 19. 修改影响分析

任何'已推送开局数据'的结论都不成立。

## 20. 可测量的验收标准

1. 开局路径不再依赖 162B 常量。

## 21. 回归测试方案

—

## 22. 修复准备度

**INVESTIGATION_READY**

- **下一步**：B18：搜历史抓包；无则转 StartGame。
- **上游依赖**：`CODOL-ISSUE-0010`

---