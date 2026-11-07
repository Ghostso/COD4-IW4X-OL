# CODOL-ISSUE-0015 — memberCount 修复已落地但语义来自 ol-mod（非本 build）

> 深度取证档案 · 2026-10-29 · `CODOL-PROJECT-DEEP-ISSUE-FORENSICS-053`

---

## 1. 问题精确定义

11/13 createRoom 应答 [u64 roomId][u32 memberCount][u32 18][u64 secondId]… 中 memberCount 原为 0，改 1 后 dwRoomMatchUber 首次出现。结构注明来自 ol-mod Unknown0BService（3.3.3.3），不能直接采信。

## 2. 历史首次发现过程

- **首次发现**：2026-10-27（`docs/LOBBY_TRAFFIC_GAP_20261027.md`）
- **最近验证**：2026-10-27
- **所属系统**：`lobby`　**优先级**：P2　**登记状态**：`PARTIALLY_RESOLVED`　**严重度**：medium
- **是否阻塞可玩战斗**：否

## 3. 全部相关历史实验

| 日期 | 实验/事件 | 结果 |
|---|---|---|
| 2026-10-27 13:27 | A/B：memberCount 0 vs 1 | 1 生效 |
| 2026-10-27 14:04 | 正式 kit 复跑 | 同样生效 |

## 4. 原始证据及 SHA-256

| Evidence ID | 类型 | 路径 | 定位 | 能证明 | 不能证明 |
|---|---|---|---|---|---|
| EV-0015-01 | source | `lobby_server.py` | 1002 | ob.u64(ROOM_ID); ob.u32(1); ob.u32(1)… | — |
| EV-0015-02 | location | `docs/AB_MEMBERCOUNT_RESULT_20261027.md` | — | A/B 证据 | — |

> 完整哈希与存在性见 `EVIDENCE_INDEX.json`；本表只列与该 Issue 直接相关的条目。

## 5. 当前源码位置

| 文件 | 行 | 说明 |
|---|---|---|
| `lobby_server.py` | 1002 | ob.u64(ROOM_ID); ob.u32(1); ob.u32(1)… |

## 6. 关键函数及调用关系

| 文件/地址 | 行/位置 | 作用 |
|---|---|---|
| `docs/AB_MEMBERCOUNT_RESULT_20261027.md` | — | A/B 证据 |

## 7. 客户端逆向证据

本 Issue（CODOL-ISSUE-0015）涉及客户端逆向的部分见 §6；相关专项见 `06_CLIENT_REVERSE_ENGINEERING_GAPS.md` 中 lobby 一节。

## 8. 网络协议字段及字节布局

本 Issue 的协议字段与字节布局：见 §6 的 `docs/AB_MEMBERCOUNT_RESULT_20261027.md`，以及 `05_PROTOCOL_GAPS.md` 中 lobby 对应小节。

## 9. 完整数据流

```
11/13 请求 → 服务端应答(memberCount) → 客户端创建 dwRoomMatchUber
```

## 10. 第一条未闭合调用边

**本 build 客户端读 memberCount 的代码点。**

## 11. 已确认事实

- memberCount=1 时 dwRoomMatchUber 出现（vtable 0x00DC795C +0x68=0x63C5E0 校验通过）
- memberCount=0 时不出现（10-27 与 10-29 E1 两次）

## 12. 尚未确认的假设

- 为何是 1 而不是 2/成员数

## 13. 已排除的假设

(本 Issue 尚无已排除假设)

## 14. 历史修复尝试

| 时间 | 改动 | 结果 |
|---|---|---|
| 2026-10-27 | 0→1 | 生效，保留 |

## 15. 当前代码状态

lobby_server.py:1002 固定回 1。

## 16. 最小复现条件

改回 0 跑一轮，读 [0x82E1518]。

## 17. 最小验证实验

**实验 B15**

| 项 | 内容 |
|---|---|
| 步骤 | 1. 试 memberCount=2<br>2. 对比 dwRoomMatchUber 与状态机是否更前进 |
| 通过判据 | 2 与 1 行为相同 ⇒ 1 是布尔语义 |
| 失败判据 | 2 有更好进展 ⇒ 语义是计数 |
| 成本 | 1 轮 |

## 18. 条件式修复方案

**方案A：以行为为准，保留 1，并在注释里标注出处是 ol-mod。**

**方案B：若 B15 显示计数语义 → 改为按房间成员数。**

## 19. 修改影响分析

房间初始化。

## 20. 可测量的验收标准

1. 本 build 中该字段的读取点被静态定位，或 A/B 证明 1 是唯一有效值。

## 21. 回归测试方案

每次 run 记录 dwRoomMatchUber 指针。

## 22. 修复准备度

**INVESTIGATION_READY**

- **下一步**：B15：memberCount=2 对照。
- **上游依赖**：无

---