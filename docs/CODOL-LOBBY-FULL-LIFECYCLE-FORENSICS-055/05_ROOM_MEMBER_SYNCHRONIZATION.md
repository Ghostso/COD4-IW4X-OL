# 05 — 房间成员同步

> 对应任务书 §四 B。任务书要求建立五条边并逐条给证据。

---

## 1. 任务书要求的链路 vs 实测

任务书给的候选链：

```
服务端成员数据 → 客户端成员数据解析 → 房间成员对象初始化
→ 事件处理器注册 → 房间状态更新 → UI 更新
```

**实测结果：这条链在客户端内部，服务端只提供 `memberCount` 一个标量。**

| 边 | 状态 | 证据 |
|---|---|---|
| 服务端成员数据 | ✅ 只有 **`memberCount`（u32）** | `lobby_server.py:1002` |
| （无）成员列表下行 | ❌ **不存在**：协议清单里没有任何成员列表请求/推送 | 54 个 (svc,task) 全集 |
| 客户端成员数据解析 | ⚠️ 只解析了这一个 u32 | A/B 实测改变它会影响 `dwRoomMatchUber` |
| 房间成员对象初始化 | ⚠️ 被 `memberCount` 门控 | 见 §3 |
| 事件处理器注册 | ❌ **未发生** | `MyEventHandler` 零实例（memberCount=0 时） |
| 房间状态更新 | ⚠️ 停在状态 1 | `[U+0x20]=1` |
| UI 更新 | ❌ 准备按钮无反应 | ISSUE-0009 |

---

## 2. memberCount 的完整证据链

### 2.1 A/B 实验（2026-10-27）

| 快照 | 时刻 | `[0x82E1518]` | `[0x849B61C]` 已请求开局 |
|---|---|---|---|
| snap_001 | t=29 s | `0` | 0 |
| snap_002 | t=61 s | `0` | 0 |
| **snap_003** | t=89 s | **`0x3ACA0CD8`** | **1** |
| snap_004 | t=118 s | `0x3ACA0CD8` | 1 |

对象身份校验：
```
[0x82E1518] = 0x3ACA0CD8
  vtable      = 0x00DC795C   ✓ dwRoomMatchUber
  vtable+0x68 = 0x0063C5E0   ✓ 自动开局状态机
```

### 2.2 2026-10-29 E1 转储的独立复核（memberCount=0）

E1 用的是 10-26 旧 kit（`memberCount=0`），转储 `snap_002`（t=152 s，**晚于建房 73 秒**）：

| 对象 | vtable | 堆内实例 | 结论 |
|---|---|---|---|
| `dwRoomImp` | `0x00DC7274` | **1**（`0x3EAEA240`） | 存在 |
| `dwRoomMatchUber` | `0x00DC795C` | **0** | 不创建 |
| `MyEventHandler` | `0x00DC78F0` | **0** | 不创建 |

⇒ 独立复现了 A/B 的"memberCount=0 ⇒ 不创建"。

---

## 3. ★ 不能由 vtable 存在推断初始化完成

任务书特别要求：**不得因为堆内发现或未发现某个 vtable，就直接认定对象创建或初始化已经完成。**

本审计严格遵守，并给出三条反例：

| 反例 | 事实 |
|---|---|
| `dwRoomMatchUber` 存在 ≠ 可用 | 状态机 `[U+0x20]=1` 停在状态 1；判据 `0x63C350` 返回假 |
| 计时器字段 | `+0x138` / `+0x140` **全 0**，从未启动 |
| `MyEventHandler` 从未被重测 | memberCount=1 后**没有**任何一期转储统计过 `0x00DC78F0` 的实例数 |

⇒ 正确表述是：
**`dwRoomMatchUber` 在 memberCount=1 时被创建；它是否"初始化完成"= UNKNOWN。**

---

## 4. MyEventHandler 与 dwRoomMatch::Init

| 项 | 值 | 来源 |
|---|---|---|
| `MyEventHandler` 的 vtable | `0x00DC78F0` | 常量区唯一引用 |
| RTTI | `.?AVMyEventHandler@?5??Init@dwRoomMatch@@SAXXZ@` | 符号层 |
| 它的 slot[1] | `0x0063B500`（建房回调） | 反汇编 |
| 实例数（memberCount=0） | **0** | 两期转储（10-27、10-29） |
| 实例数（memberCount=1） | **UNKNOWN** | **从未测过** |

**因果矛盾（本审计的独立发现）**：
按原始因果图，`MyEventHandler` 缺失应切断 `0x63B500` → `0x63E510` → `dwRoomMatchUber`。
但 memberCount=1 时 `dwRoomMatchUber` **确实出现了**。

三种解释，均未证：
1. `memberCount=1` 同时也让 `MyEventHandler` 出现了（即 `Init` 被调用）；
2. `dwRoomMatchUber` 由**另一条路径**创建（不经 `0x63B500`）；
3. memberCount=1 的转储里 `MyEventHandler` 其实非零，只是没人去数。

---

## 5. memberCount=0 与 memberCount=1 的完整对照

| 维度 | memberCount=0 | memberCount=1 |
|---|---|---|
| 出现 kit | 10-26（78,206 B）、10-29 E1 | 10-27 起（88,162 B 及以上） |
| `dwRoomImp` | 1 实例 | （未测，假定 1） |
| `dwRoomMatchUber` | **0** | **1** |
| `MyEventHandler` | **0** | **UNKNOWN** |
| 自动开局状态机 | 不存在 | 存在，停在状态 1 |
| `[0x849B61C]` 已请求开局 | 0 | **1** |
| 战斗服连接 | 否 | 否 |
| `11/4` 上行 | 有 | 有 |
| `mmstart` | 有（B1 形态） | 有（B1 形态） |

> ⚠️ 两个 kit 的 **memberCount 与"是否走到 mmstart"无关**：
> 10-26 的 memberCount=0 轮次里客户端也发了 mmstart（`ONCE_20261026_233111`）。

---

## 6. 结论

**房间"成员同步"在本项目里只有 1 个标量（`memberCount`），没有成员列表协议。**

- 链路在"客户端成员数据解析"之后就断了：
  解析了 memberCount，但**事件处理器未注册**（至少 memberCount=0 时未注册）。
- `memberCount=1` 让 `dwRoomMatchUber` 出现，
  但**没有让它初始化完成**（状态机停状态 1、计时器全 0）。
- `MyEventHandler` 在 memberCount=1 下的状态是本专项**最重要的未知项**，
  且只需一次转储即可回答。

**下一步（唯一）**：用 memberCount=1 的 kit 跑一轮 + 转储，统计 `0x00DC78F0` 实例数。
