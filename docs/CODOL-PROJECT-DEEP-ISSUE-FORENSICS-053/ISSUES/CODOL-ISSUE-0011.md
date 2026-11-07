# CODOL-ISSUE-0011 — 房间推送的路由信封未定死（route key = roomId 高低 32 位）

> 深度取证档案 · 2026-10-29 · `CODOL-PROJECT-DEEP-ISSUE-FORENSICS-053`

---

## 1. 问题精确定义

0x7E7C90 按 (p1,p2) 遍历表；建房后表项 [+0x10]=roomId_lo、[+0x14]=roomId_hi、[handler]=0x6371F0。0x7E79C0 校验 [obj+8]==key_hi、[obj+0xc]==key_lo。现有三种信封构造都不满足。

## 2. 历史首次发现过程

- **首次发现**：2026-10-28（`docs/ROOM_PUSH_ROUTE_KEY_SLOT_20261028.md`）
- **最近验证**：2026-10-28
- **所属系统**：`lobby`　**优先级**：P1　**登记状态**：`OPEN`　**严重度**：high
- **是否阻塞可玩战斗**：是

## 3. 全部相关历史实验

| 日期 | 实验/事件 | 结果 |
|---|---|---|
| 2026-10-28 第3轮 | 按 (service,task) 读路由表全 0 → 误判'未注册' | 已推翻 |
| 2026-10-28 第5轮 | 改按 roomId 高低 32 位读，命中 0x1122334455667788 | 成立 |
| 2026-10-28 第19轮 | 实机推送仍无效果 | 信封布局未定 |

## 4. 原始证据及 SHA-256

| Evidence ID | 类型 | 路径 | 定位 | 能证明 | 不能证明 |
|---|---|---|---|---|---|
| EV-0011-01 | source | `—` | — | 纯客户端问题 | — |
| EV-0011-02 | location | `docs/ROOM_PUSH_ROUTE_KEY_SLOT_20261028.md` | 全文 | 路由键证据 | — |
| EV-0011-03 | location | `docs/ROOM_OBJECT_LAYOUT_20261028.md` | 全文 | 房间对象布局 | — |

> 完整哈希与存在性见 `EVIDENCE_INDEX.json`；本表只列与该 Issue 直接相关的条目。

## 5. 当前源码位置

`NOT_APPLICABLE` — 该问题不在本仓库源码内（客户端二进制 / 环境 / 文档问题）。

## 6. 关键函数及调用关系

| 文件/地址 | 行/位置 | 作用 |
|---|---|---|
| `docs/ROOM_PUSH_ROUTE_KEY_SLOT_20261028.md` | 全文 | 路由键证据 |
| `docs/ROOM_OBJECT_LAYOUT_20261028.md` | 全文 | 房间对象布局 |

## 7. 客户端逆向证据

本 Issue（CODOL-ISSUE-0011）涉及客户端逆向的部分见 §6；相关专项见 `06_CLIENT_REVERSE_ENGINEERING_GAPS.md` 中 lobby 一节。

证据载体：客户端二进制（3.19 / 1649370），非本仓库源码；具体函数/地址见 §6 表格的 docs/ROOM_PUSH_ROUTE_KEY_SLOT_20261028.md 行。

## 8. 网络协议字段及字节布局

本 Issue 的协议字段与字节布局：见 §6 的 `docs/ROOM_PUSH_ROUTE_KEY_SLOT_20261028.md`，以及 `05_PROTOCOL_GAPS.md` 中 lobby 对应小节。

## 9. 完整数据流

```
服务端构造 push → 加密 → 客户端 dwLobbyEventHandler 槽6(0x7F1060) → 0x7E7C90 查表 → handler 0x6371F0
```

## 10. 第一条未闭合调用边

**槽6 的调用者静态不可定位（call dword ptr [reg+0x18]，全镜像 5421 处）；硬件断点被 ACE 拒绝。**

## 11. 已确认事实

- 路由键 = roomId 高低 32 位（内存表项实测）
- roomId 在客户端内存中一律低 32 位在前（4 处命中，反向 0 处）

## 12. 尚未确认的假设

- 信封中 roomId 的字节位置

## 13. 已排除的假设

- (service,task) 路由（表里放的是 roomId）
- Demonware 位流（上行 10 条样本无一以 tag==3 开头）

## 14. 历史修复尝试

| 时间 | 改动 | 结果 |
|---|---|---|
| 2026-10-28 | 改用 instant_push_body(kind=11) | 共同前缀 23 字节，无效果 |

## 15. 当前代码状态

lobby_server.py 同时存在两套构造器（容器型 build_room_payload 与位流型 _room_body_stream），无单一事实来源。

## 16. 最小复现条件

推一条 room push，在早期窗口转储里读路由表 0xE376C08 的表项，比较 [+0x10]/[+0x14] 与信封内容。

## 17. 最小验证实验

**实验 B11**

| 项 | 内容 |
|---|---|
| 步骤 | 1. 构造一条把 roomId 放在 +8/+0xc 的信封变体<br>2. 与不推、与当前格式三者对照任务数与 11/4 次数 |
| 通过判据 | 三种情况行为互不相同 ⇒ 路由键被采用 |
| 失败判据 | 三者相同 ⇒ 仍被丢弃 |
| 成本 | 3 轮实机 |

## 18. 条件式修复方案

**方案A（条件式）：若 B11 证明信封位置决定成败 → 按 (u32 flag, u32 roomId_hi, u32 roomId_lo, …) 构造。**

**方案B：改用 channel_push_body 并调整 roomId 字段顺序。**

## 19. 修改影响分析

决定房间 UI 能否被服务端驱动；不影响 PvE 直接开局路径。

## 20. 可测量的验收标准

1. 能构造出满足 obj+8/obj+0xc == roomId 的信封，并被客户端接受（行为可观测）。

## 21. 回归测试方案

每次改动后跑一轮，比较任务数/11-4 次数（10-28 已建立该指标）。

## 22. 修复准备度

**INVESTIGATION_READY**

- **下一步**：B11：三种信封对照。
- **上游依赖**：`CODOL-ISSUE-0010`

---