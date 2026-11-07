# 靶场 Bring-up 实机验证报告

日期：2026-10-15
范围：只读复核 + 实机遥测分析（未修改任何源码或运行中的服务）
结论等级：`PROVEN`（有可复现命令与日志行号）

---

## 0. 一句话结论

**交接词给出的"致命 Bug"定位不成立；靶场至今从未进图。真正的 blocker 是
快照载荷本身（141 B）无法被客户端解析器接受，客户端因此停在
`cls.state 9` / 加载画面的"等待玩家数据"，从不 ack 任何快照序号。**

---

## 1. 交接词的核心主张：REFUTED

交接词称 `_e1_regression/ol-mod-olfinal/src/game_server/server_mp/sv_snapshot_mp.cpp`
**10290-10335 行**记录了"原生铁律"：

> `deltaMessageDistance > 0` → `frames[deltaNum & 31].valid == 0` → `msg->overflowed = 1` 丢弃

全文（26744 行）检索结果：

| token            | 命中数 |
|------------------|-------:|
| `deltaNum`       | **0** |
| `valid == 0`     | **0** |
| `msg->overflowed`| **0** |

10290-10335 行的真实内容是该文件自己的 OLMOD 注释块，讲的是**反面**：

- 10265-10275：`BIT 0x02 IS THE CLIENT'S TICKET OUT OF CA_PRIMED...`
- 10312-10326：**两个极端都错** ——
  - 每帧 FULL 都带 0x02 → 客户端 `acked once and stopped`，`deltaMessage` 冻结；
  - 只发一次 → `never acked at all`（"the one announcement lands while it is still
    loading the map and there is no second chance"）。
  - 正解：`repeat until it takes, then stop`，判据是 `baseline != nullptr`。

**即：把 0x02 每帧重发，正是该注释点名有害的做法。** 而本次改动
（`ClientEntered` 在 ack 前恒为 false → 每帧 `flags=0x0A`）做的正是这件事。

### 1.1 被删除的 `SnapshotAttempts >= 3` 从来不是拦路虎

旧逻辑日志行 `armed for active 3D rendering` 出现于 `attempts=3`（09:57 运行）
与 `attempts=102`（08:54 运行）。**这两次旧逻辑运行中客户端同样没有 ack 任何快照。**

---

## 2. 决定性测量：ack 从不等于快照序号（全 42 次运行）

`CODOL-Combat-Server-v0.1/logs/firingrange_live.log`，按 `CFG bind=` 切分 42 次运行，
统计每条 `NETCHAN RX ... ack=N`：

| 运行时刻 | GAMESTATE seqs        | 观测到的 ack      | 快照 seq 范围 |
|----------|-----------------------|-------------------|---------------|
| 00:10    | 1, 50, 115, 179       | 0, **179**, 0, **115**, 0, **115** | 2 → 29203 |
| 08:52    | 1, 26, 59, 92         | 0, **92**         | 2 → … |
| 09:36    | 1, 2, 5               | 0, **5**          | 3 → … |
| 09:55    | 1, 2, 13              | 0, **13**         | 3 → … |
| 11:14（含本次修复） | 1, 2, 12, 4  | 0, **12**         | 3 → … |
| 11:35（本轮实机）   | 1, 2, 4      | 0, **4**          | 17 → 12016 |

**`ack` 恒等于最后一条 GAMESTATE 的 netchan seq，从不等于任何快照 seq。**

`★ Client successfully entered world` 在整个日志中出现 **0 次**。

### 2.1 反向佐证

21:47 运行中客户端发出 `messageAck=115`（= gamestate seq），服务端回
`REJECT_USERCMD reason=Unknown snapshot baseline 115` —— 因为服务端 `InputBaselines`
是按**快照** seq 建表的。客户端拿 gamestate 当 usercmd 基线，说明它手上根本没有快照。

---

## 3. 实机截图：是加载画面，不是进图

`_now_state.png`（1920x1080，本轮实机抓取）与 ol-mod 自己带注解的参考图逐字对应：

`_e1_regression/ol-mod-olfinal/docs/devlog/2026-07-31-natural-match-automation.md` §49-51：

> ![loading](assets/2026-07-31-natural-match-loading.png)
>
> "这张图很重要，但也很容易被误读。它证明客户端通过 CCS 校验、解析了当前
> gamestate，并来到原生地图加载画面的'等待玩家数据'；**它不证明已经存在完整的
> authoritative world**。此时 client connection state 仍为 **9**，server 还没有
> 发送真正的 initial snapshot。"

图中靶纸/集装箱/火花是 `mp_firingrange` 的**加载背景美术**，不是活着的 3D 场景。

---

## 4. 自测"全绿"未覆盖失败路径

`CODOLCombatServer.exe --selftest` 实跑：**通过 254 项，失败 0 项**。

但：

1. 自测默认跑在 `protocol_mode=Codol2697`，日志明确写
   `snapshot 发送保持关闭：2697 帧边界/delta 基准仍是 BLOCKED`
   —— **自测根本没走实机失败的那条 legacy 快照路径**。
2. `golden_first_snapshot.hex` 对应的用例在 `SelfTest.cs:532` 强制
   `opt.SnapshotEntryFlag = false`（KAT 基线 `0x08`），黄金向量 `state[10] = 0x08`。
   —— **新的 0x0A entry-flag 行为没有任何测试覆盖。**

---

## 5. 真正的 blocker：快照载荷（本轮新证据）

### 5.1 长度对不上"曾让客户端进图"的那一版

`CODOL-BATTLE-SERVER-CLIENT-PARSER-SEMANTICS-046/_extracted/docs/HANDOFF.md`：

| 行号 | 内容 |
|------|------|
| 1298-1303 | 三方 `TX_SPAWN_EXPERIMENT` bytes 分布 **124×1062**；`_build_motion_snapshot(...)` → **124 字节** ✓ |
| 1337     | 01:53:36 起 `TX_SPAWN_EXPERIMENT seq=2/3/4/… bytes=124` |
| 2583     | `bytes=104`（idx45 实验态）：`RX_USERCMD` **942 条** → 客户端**接受并解析了**我们的快照 |
| 2588-2590| 裸 f32(32位)/裸 short(16位) → **卡在"等待玩家数据"**，ack 恒为 1（解析错位） |

**实机日志里我们的快照长度分布：`141` × 6196 次，全部 141 字节。**
而 `battle_server.py` 当前同样产出 **141 字节 / 1118 bit**。

### 5.2 与第三方参考实现的逐字节对拍

参考实现 `_extracted/reference/CodolMotionSnapshot.cs`
（`battle_server.py` 自述"逐行移植自"它） vs 当前 `battle_server.py`：

```
REFERENCE (CodolMotionSnapshot.cs) : 124 bytes / 984 bits
CURRENT   (battle_server.py)       : 141 bytes / 1118 bits
共同前缀：46 字节；从第 46 字节起分叉，共 65 个字节不同
```

分叉点 = **idx21..24 段**。参考实现写的是**事件数组**
（`equipment.Events[i]`），当前写的是**武器槽**（`slot.weapon` + capacity）。
这正是 2026-10-07 那次"语义更正"改掉的地方 —— 而它**没有经过实机验证**。

### 5.3 写入器与读取器已经不同步（可复现）

`demo_parse.py` 自带的往返自测（声称验证"读取器是 `_BitWriter` 的严格逆"）**现在失败**：

```
$ python -X utf8 demo_parse.py --selftest x
EOFError: 未知索引 48
```

逐字段跟踪断点：

```
#12 idx=21  ...
#13 idx=30   ← 写侧在 idx21 段后直接跳到 30
#14 idx=39
#15 idx=48   ← 读侧无此 codec
```

即：**写侧在 idx21 段写入的位数与读侧期望不一致**，整段从第 46 字节起错位。

---

## 6. 复现命令

```powershell
# 1) 自测（会"全绿"，但不覆盖 legacy 快照路径）
cd D:\BaiduNetdiskDownload\使命召唤OL\CODOL-Combat-Server-v0.1\build\bin
.\CODOLCombatServer.exe --selftest

# 2) 往返自测（会失败 —— 这是关键证据）
cd D:\BaiduNetdiskDownload\使命召唤OL\REF_LOBBY_KIT
python -X utf8 demo_parse.py --selftest x

# 3) 字段序对照（会报 29/29 全对 —— 但那只证明字段序）
python -X utf8 snapshot_diff.py

# 4) 快照长度
python -X utf8 -c "import sys;sys.path.insert(0,r'D:\BaiduNetdiskDownload\使命召唤OL\REF_LOBBY_KIT');import battle_server as bs;eq=bs._Equipment();d,n=bs._build_motion_snapshot(0,1000,1000,True,48.0,-572.0,-116.0,0,0,0,0.0,0.0,0.0,False,eq,omit_motion=False);print(len(d),'bytes /',n,'bits')"
# -> 141 bytes / 1118 bits   （参考实现是 124 / 984）

# 5) ack 证据
Select-String -LiteralPath CODOL-Combat-Server-v0.1\logs\firingrange_live.log `
  -Pattern 'ack=(\d+)' | ForEach-Object { $_.Matches[0].Groups[1].Value } |
  Group-Object | Sort-Object {[int]$_.Name} | Format-Table Count,Name
```

---

## 7. 更正记录（相对上一轮交接词）

| # | 交接词主张 | 实际 | 裁定 |
|---|-----------|------|------|
| 1 | sv_snapshot_mp.cpp:10290-10335 记录"delta>0 必丢包"铁律 | 该 token 全文 0 命中；该段讲的是"每帧重发 0x02 有害" | **REFUTED** |
| 2 | `SnapshotAttempts>=3` 是致命 blocker | 两次旧逻辑运行同样 0 ack | **REFUTED** |
| 3 | 修复后客户端会 ack 快照并进图 | 实机 141B 快照，ack 恒为 gamestate seq，0 次 entered world | **REFUTED** |
| 4 | 截图是实机 3D 出生画面 | 是加载画面（"等待玩家数据"），`cls.state 9` | **更正** |
| 5 | 靶场曾"暂时进图" | 靶场从未进图；只有 demo 进过图 | **更正（用户提供）** |

---

## 8. 建议的下一步（按优先级）

1. **回滚 idx21..24 的"武器槽"改写**，恢复参考实现的**事件数组**写法，
   使首帧长度回到 124 字节 —— 这是唯一有"客户端曾接受并解析"记录的长度。
2. **修复 `demo_parse.py` 的往返自测**（当前失败），让它重新成为可信的
   写入器/读取器互逆判据；否则后续任何字段改动都无法离线验证。
3. **补测试**：把 `SnapshotEntryFlag` 的两种取值都纳入 KAT；
   让自测真正跑一遍 legacy 快照路径（而不是 2697 的 BLOCKED 分支）。
4. **入场门禁改动回滚或收窄**：既然 OLMOD 明确标注"每帧 0x02"有害，
   应恢复"首帧带 0x02、之后 0x08"（参考实现即 `first ? 8 : 4`）。
5. 上述完成后，再用 `launch_game_for_user_test.py` 做实机验证，
   判据是 `ack >= FirstSnapshotSeq` 且 `★ Client successfully entered world` 出现。
