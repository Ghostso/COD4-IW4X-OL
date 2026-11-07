# CODOL-ISSUE-0054 — mmbook accepted 必须回显客户端自己的 (A,B)，预留槽填充者未定位

> 深度取证档案 · 2026-10-29 · `CODOL-PROJECT-DEEP-ISSUE-FORENSICS-053`

---

## 1. 问题精确定义

八个连续的 COMBAT_V0_1_NEXT_00x 实现门禁都收敛到同一个点：[+0x168]/[+0x16C] 由谁填、填什么，始终未定位。

## 2. 历史首次发现过程

- **首次发现**：2026-10-16（`COMBAT_V0_1_NEXT_001_BLOCKER.md §2.5`）
- **最近验证**：2026-10-29
- **所属系统**：`lobby`　**优先级**：P1　**登记状态**：`OPEN`　**严重度**：high
- **是否阻塞可玩战斗**：是

## 3. 全部相关历史实验

| 日期 | 实验/事件 | 结果 |
|---|---|---|
| 2026-10-16..22 | COMBAT_V0_1_NEXT_001..011 八轮 | 未闭合 |
| 2026-10-26 | mmbook accepted 后客户端确实发了 mmstart | 那时成立 |
| 2026-10-29 | E1 未走到 mmbook（无 mmstart） | 无新增信息 |

## 4. 原始证据及 SHA-256

| Evidence ID | 类型 | 路径 | 定位 | 能证明 | 不能证明 |
|---|---|---|---|---|---|
| EV-0054-01 | source | `lobby_server.py` | 1085-1090 | mmbook 分支 | — |
| EV-0054-02 | location | `lobby_server.py` | 1085 | `6/14 命中 'mmbook' -> push 'mmbook accepted'` | — |

> 完整哈希与存在性见 `EVIDENCE_INDEX.json`；本表只列与该 Issue 直接相关的条目。

## 5. 当前源码位置

| 文件 | 行 | 说明 |
|---|---|---|
| `lobby_server.py` | 1085-1090 | mmbook 分支 |

## 6. 关键函数及调用关系

| 文件/地址 | 行/位置 | 作用 |
|---|---|---|
| `lobby_server.py` | 1085 | `6/14 命中 'mmbook' -> push 'mmbook accepted'` |

## 7. 客户端逆向证据

本 Issue（CODOL-ISSUE-0054）涉及客户端逆向的部分见 §6；相关专项见 `06_CLIENT_REVERSE_ENGINEERING_GAPS.md` 中 lobby 一节。

## 8. 网络协议字段及字节布局

本 Issue 的协议字段与字节布局：见 §6 的 `lobby_server.py`，以及 `05_PROTOCOL_GAPS.md` 中 lobby 对应小节。

## 9. 完整数据流

```
客户端 6/14 mmbook → 服务端 push 'mmbook accepted'(20B) → 客户端发 mmstart
```

## 10. 第一条未闭合调用边

**[+0x168]/[+0x16C] 的写入点。**

## 11. 已确认事实

- 10-26 成功轮里 mmbook accepted 后客户端立即发 mmstart
- 10-29 E1 里客户端未发 mmstart（更上游就停了）

## 12. 尚未确认的假设

- 回显值的来源

## 13. 已排除的假设

- 'mmbook accepted 没发'——10-26/10-29 日志都显示已发

## 14. 历史修复尝试

(无历史修复尝试)

## 15. 当前代码状态

lobby_server.py 回固定的 'mmbook accepted' 文本。

## 16. 最小复现条件

看 lobby 日志的 mmbook 行与其后是否有 mmstart。

## 17. 最小验证实验

**实验 B54**

| 项 | 内容 |
|---|---|
| 步骤 | 1. 在 E1 型成功会话里，比较客户端 mmbook 请求里的 (A,B) 与服务端回显值 |
| 通过判据 | 两者一致 |
| 失败判据 | 不一致 ⇒ 需改回显 |
| 成本 | 1 轮（依赖 0020） |

## 18. 条件式修复方案

**方案A（条件式）：若 B54 不一致 → 回显客户端请求里的原值。**

**方案B：保持现状（10-26 已证明够用）。**

## 19. 修改影响分析

预约放行信号。

## 20. 可测量的验收标准

1. 能证明回显值与客户端写入值一致。

## 21. 回归测试方案

记录 mmbook 请求与回显的字节。

## 22. 修复准备度

**BLOCKED_BY_DEPENDENCY**

- **下一步**：依赖 ISSUE-0020。
- **上游依赖**：`CODOL-ISSUE-0020`

---