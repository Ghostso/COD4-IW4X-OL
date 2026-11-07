# A/B 实验：11/13 createRoom 的 memberCount 0 → 1

**日期**：2026-10-27 13:21
**run**：`run_codol_001/runs/ONCE_20261027_132124`
**实验 kit**：`run_codol_001/kit_membercount1_20261027`（源 kit 副本，只改 1 处）

## 实验设计

- 原值：`lobby_server.py:874` `ob.u64(ROOM_ID); ob.u32(0); ob.u32(18); ...`
- 改为：`ob.u32(1)`（memberCount 0 → 1）
- 假设：客户端若按成员数判断房间是否成立，0 会导致它从不初始化房间子系统
- 判据：`[0x82E1518]`（dwRoomMatchUber 指针）是否变非零

## 执行结果：**实验未触发，无效**

### 1. 本轮客户端没有进入剧情流程

`11/13 createRoom` **一次都没出现**。与上一轮对比：

| service | 上一轮 `122904` | 本轮 `132124` |
|---|---|---|
| 6/5 订阅 | 2 | 2 |
| 21/5 findSessions | 1 | **0** |
| 11/13 createRoom | 1 | **0** |
| 11/4 setRoomData | 2 | **0** |
| 6/14 mmbook/mmstart | 3 | **0** |

客户端在 `13:22:01` 完成订阅后就停在大厅，只发 keepalive，直到固化链 200 秒到点退出。
⇒ **`memberCount` 的改动从未被客户端读到过，实验没有验证任何东西。**

### 2. 活进程读字段再次被 ACE 拦死

```
本会话直连:  OpenProcess -> handle=None  err=5
经提权 agent: handle=280 err=0
              [0x082E1518] READ-FAIL err=299 (ERROR_PARTIAL_COPY)
              连 sanity 0x400000 都读不到
```

⇒ 与 [[codol-ace-blocks-debug-and-read]] 记录一致：**后期句柄结构性不可读**。
要拿 `[0x82E1518]` 只能等下一次"启动后立刻抢句柄 + 立即全量转储"。

### 3. 一个可复现的前置障碍

本轮 `13:22:51` 出现：

```
71/3  payload(120): 10 43 68 61 6e 6e 65 6c 53 75 62 73 63 72 69 70 74 69 6f 6e ...
         = "ChannelSubscriptionFail|${TIMESTAMP_OFFSET(-5)}|..."
     -> UNMAPPED -> 空 ACK
```

`ChannelSubscriptionFail` 是客户端 TLog 里的事件名（`0x00DB4C00`），
说明**频道订阅失败被记录并上报了**。它与 `6/5` 订阅 20 个事件只拿到空应答
是同一件事的两面。

## 结论

- **memberCount 假设：未验证**（实验没触发）。不能据此说它是/不是原因。
- 本轮与上一轮的差别不在 kit，而在**客户端有没有走进剧情流程**——
  这一步本身就有随机性（上一轮进了、这一轮没进）。
- 要重新做这个实验，必须先确保客户端真的走到 `11/13`，
  否则改了也白改。**判据应先看日志里有没有 `createRoom`，再谈 `[0x82E1518]`。**

## 下一步（按可行度）

1. **重跑**，先确认日志出现 `11/13 createRoom`；同时用
   `live_fullmem.py` 的"抢早期句柄 → 立即转储"路径（而不是后期读），
   在 t≈80s 做一次全量快照，从转储里读 `[0x82E1518]`。
2. 或者先处理更上游的 `ChannelSubscriptionFail` —— `6/5` 订阅 20 个事件
   却拿到空应答，这个失败可能正是"客户端认为房间没建立"的直接原因。
   **这条比 memberCount 更靠前，优先级应更高。**

相关：[[codol-myhandler-never-created-root-cause]]、[[codol-ace-blocks-debug-and-read]]
