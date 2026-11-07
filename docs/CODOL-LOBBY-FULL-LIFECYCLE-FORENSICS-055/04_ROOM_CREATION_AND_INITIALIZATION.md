# 04 — 房间创建与初始化

> 对应任务书 §四 A。全部结论来自原始日志 + `lobby_server.py` 源码。

---

## A1. 谁触发 createRoom

**客户端。** 服务端从不主动建房。

实测依据：全部 32 个出现 `11/13` 的 run 里，`11/13` 之前必先有
`21/5 findSessions(playlist=50)`（BOT 多选单）。PvE 路径（`playlist=10`）**从不**出现 `11/13`。

```
21/5 findSessions(playlist=50)   ← 先查询有哪些 session
11/13 createRoom                 ← 客户端决定建房
```

服务端侧没有任何"主动推 roomInfo 让客户端建房"的推送（见 `02_..._STATE_MACHINE.md §5`）。

## A2. 客户端建房前处于什么状态

- 已完成 S1 bootstrap（35 请求）与档案确认
- 已拿到 `21/5` 的 session 对象（含 67 B 战斗服地址块）
- `102/1` 频道订阅已成功（客户端 `0x00B8F495` 强校验 ≥1 对象）

## A3. 请求字段

`11/13` 的 declared 长度在 **全部 32 个 run 里都是 4 字节**（`_lobby_protocols.json`：
`11/13 runs=32 sizes=[4]`）。

⇒ **createRoom 请求本身几乎无参**（4 B）。
源码注释也写明：`if task == 13: # createRoom(请求无参)`（`lobby_server.py:989`）。

## A4. 服务端返回字段

```python
# lobby_server.py:1002-1010（工作基线 88,162 B）
ob.u64(ROOM_ID)        # 0x1122334455667788（固定）
ob.u32(1)              # memberCount  ← 2026-10-27 由 0 改为 1
ob.u32(1)              # 旧版是 18，改 memberCount 时一并改成 1
ob.u64(ROOM_SECOND_ID) # 0x42706516032933CB（固定）
ob.bool_(False)
ob.bool_(False)
ob.u32(1)
```
总长 **37 字节**（日志 `createRoom -> roomId=0x… secondId=0x… (37 字节)`）。

**注意版本差异**（同一字段三种取值，都存在过）：

| kit 版本 | memberCount | 第 3 个 u32 |
|---|---|---|
| 10-26 成功轮（78,206 B） | **0** | **18** |
| 10-27 修复后 | **1** | **1** |
| 区间 C（87,080 B） | 1 | 1 |

## A5. Room ID 编码

- `ROOM_ID = 0x1122334455667788` 固定。
- 客户端内存中一律 **低 32 位在前**（`docs/ROOM_OBJECT_LAYOUT_20261028.md`：4 处命中，反向 0 处）。
- 路由表项 `+0x10=0x55667788`（lo）、`+0x14=0x11223344`（hi）。
- 唯一例外：`ONCE_20261029_002046` 的 roomId 是 `0x6B4C2D0E`（那轮 kit 用了不同常量）。

## A6. 房间对象如何初始化

客户端侧（`docs/ROOM_OBJECT_LAYOUT_20261028.md`，来自转储）：

```
0x08425C08
  +000  7E9FCCB8   疑似 vtable（RTTI 解不出）
  +008  55667788   roomId 低 32
  +00C  11223344   roomId 高 32
  +014  01010000   两个 flag 字节
  +018  00000001
  +01C  0000056E   (1390)
  +020  0000041A   (1050)
  +030  6B4C2D0E E7C8A98A   8 字节标识
  +038  "M7-E8S6Clie…"      客户端实例名
```

出现时间线（同一进程 4 次快照）：`snap_001` 全 0 → `snap_002` 仅 `+0xC=1` → **`snap_003` roomId 写入** → `snap_004` 不变。

## A7. 成员列表如何建立

**关键结论：客户端从不单独请求成员列表。**

- 协议清单里**没有**任何"getMembers / listMembers"类请求。
- 成员信息只随 `11/4` 的 blob 批次与（我们自造的）房间推送走。
- 服务端回 `memberCount` 后，客户端据此决定是否往下走（2026-10-27 的 A/B）。

`memberCount` 的 A/B 实测：

| memberCount | `[0x82E1518]` dwRoomMatchUber | `MyEventHandler` | 结果 |
|---|---|---|---|
| **0** | `0` | 0 实例 | 从不建房 |
| **1** | `0x3ACA0CD8`（vtable 0x00DC795C +0x68=0x63C5E0 校验通过） | **未重测** | 对象出现，状态机启动 |

⚠️ **不能**由"堆里出现了 dwRoomMatchUber"推断"初始化完成"：
状态机停在状态 1（`[U+0x20]=1`），计时器 `+0x138/+0x140` 全 0。

## A8. 创建成功后客户端预期收到什么

实测（32 个房间 run 全部一致）：

1. `11/13` 应答（37 B）
2. 随后**客户端自己**发 `11/4 setRoomData`（不是等服务端推）
3. 服务端对 `11/4` 回显频道推送（kit 版本不同时还会附 `dwRoomMessageStartGame`）

**没有任何一条"服务端主动"的房间初始化消息。**

## A9. 当前服务端是否遗漏下行事件

- **6/5 订阅的 20 个事件：服务端一个都没推**（`LOBBY_TRAFFIC_GAP_20261027`）。
  这是最明确的一处"遗漏"。
- 房间推送（`11/4` 回显、自造 room push）确实发了，但**从未证明被客户端解析**。

## A10. 是否存在客户端等待但服务端没有提供的状态

| 候选 | 证据 | 状态 |
|---|---|---|
| 房间成员列表 | 无拉取请求；成员走 blob | UNKNOWN |
| RoomInfo/RoomStateUpdated 事件 | 6/5 订阅了但零推送 | **是**（最可能） |
| 准备回执 | 客户端发 16 B ready 批次后，服务端只回显 | UNKNOWN |
| 倒计时 StartCountingDown | 订阅项之一，从未推送 | 是 |

---

## 结论

**createRoom 链路本身是通的**（客户端发 → 服务端回 → 客户端继续）。
断点不在建房，而在**建房之后的房间状态同步**（见 `05_ROOM_MEMBER_SYNCHRONIZATION.md`）。
