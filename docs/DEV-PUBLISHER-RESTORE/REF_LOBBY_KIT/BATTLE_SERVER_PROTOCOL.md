# 战斗服务器协议规格 + 离线自测（2026-10-07）

> 这轮的目标是"推进真正的战斗服务器实现"。做法不是再猜，而是：
> 从**实机抓包里把整条链的每一个字节解出来**，固化成规格，并配一个
> **不需要游戏**的离线自测（`battle_selftest.py`），让后续每一步改动都能秒级回归。

---

## 0. 本轮最重要的两个结论

1. **真实客户端确实走完了整条战斗服握手**（有抓包为证）——
   NAT → DTLS init → ECDH 密钥交换 → `getchallenge`/`connect`/`stats`/`heartbeat`
   → 开始发 usercmd。也就是说战斗服的**协议层本来就是通的**。
2. **卡点在"首个 game state 的下发时机"**：抓包里
   **`TX_GAMESTATE` 出现过 0 次**、`RX_GAMESTATE_PROGRESS` 也 0 次。
   客户端连上后一直发 14B 空命令包等我们推 game state，我们却在等它先发
   `gamestateupdate` —— **双方互等，永远停在"等待连接"**。

`battle_server.py` 已修：`connect` 应答发出后**立即安排**首个 game state
（`assoc["connect_done"]`），不再要求先解析出一条完整 usercmd。

### ★★ 0.1 同一类 bug 的第二处：**快照也从来不发**（本轮一并修掉）

修完 game state 之后，自测第 ⑨ 步仍然只看到"OOB 应答"，**一条快照都没有**。
根因与上面**完全一样**：

```python
# 旧代码
elif cmd.startswith("gamestateupdate "):
    ...
    if stage == 6 and not snapshot_due:
        snapshot_due = time.time() + 0.5      # ← 只有收到这条命令才启动快照
```

而真实客户端**从不发 `gamestateupdate`**（抓包实录：
`gamestateupdate` 0 次、`TX_SPAWN` 0 次）。所以快照永远不开始，
客户端会停在"**等待玩家数据**"。

**修法**：下发 game state 的**同一时刻**就启动 `snapshot_due`
（`pump_gamestate` 里加一段），不再依赖任何客户端命令。

**修完后**（离线自测实录）：

```
[OK] ⑧ game state seq=2 len=263
TX_SPAWN_EXPERIMENT seq=2  serverTime=1000 bytes=124 (第 1 帧, pos=48.0,-572.0,-116.0 yaw=0)
TX_SPAWN_EXPERIMENT seq=41 serverTime=1691 bytes=124 (第 40 帧, ...)
...
[OK] ⑪ 快照自动开始，共 276 条
```

124 字节运动快照按 `snap_hz`（默认 = tick 128 Hz）稳定下发。
这是战斗服**第一次真正开始推快照**。

> **规律（值得记住）**：这两处 bug 是同一个模式 ——
> **服务端在等客户端发一条它永远不会发的命令**。
> 凡是"等客户端先说话"的 gate，都要拿抓包核实那条命令到底出现过没有
> （`gamestateupdate` → 0 次，就是反例）。

---

## 1. 抓包证据（`battle_srv.log` 21:28:19~21:28:24，一次完整真实会话）

| # | 方向 | 长度 | 内容 |
|---|---|---|---|
| 1,2 | C→S | 29B | NAT 遍历探针，`0d 02 ... 7f 00 00 01 20 71`（尾 6B = 127.0.0.1:8305） |
| 3 | C→S | 16B | DTLS init：`01 02 0000 0000 <clientTag:2> 01 00×7`，实测 clientTag=`d2 41`=16850 |
| — | S→C | 38B | cookie（首字节改 `02 02`），[14:16]=serverTag，[24:30]=本地 IP/端口 |
| 4 | C→S | 219B | `03 02 <serverTag> | cookie(38B) | …(67B) | u64 1 | 客户端公钥(100B)` |
| — | S→C | 114B | key-exchange ack：`04 02 <tag> | 0000 | 服务端公钥(100B)@[6:106] | 01 @106` |
| 5 | C→S | 54B 数据帧 | 解出 `FF FF FF FF getchallenge 0 "e7c8a98a6b4c2d0e"\0` |
| — | S→C | 数据帧 | `FF FF FF FF challengeResponse 1\0` |
| 6 | C→S | 463B 数据帧 | 解出 `... connect e7c8a98a6b4c2d0e "\name\TTctRThTNkNsaWVudA==\xuid\…"` |
| — | S→C | 数据帧 | `FF FF FF FF connectResponse\0` |
| 7 | C→S | 855B 数据帧 | 解出 `FF FF FF FF stats\0 <index:1> <total:u16=826> <826B>` |
| — | S→C | 数据帧 | `FF FF FF FF statResponse 0\0` |
| 8+ | C→S | 30B 数据帧 | `FF FF FF FF heartbeat\0`（每 1s 一次） |
| — | S→C | 数据帧 | `FF FF FF FF heartbeatresponse\0` |
| 17+ | C→S | 30B 数据帧 | **usercmd**，明文 14B（见下） |

### 数据帧封装（逐字节确认）

```
06 02 <serverTag:2> <seq:2> <hmac8> <len:2> <cipher(len)>
```

* `seq` 是客户端自增序号，从 **0** 开始（握手期 OOB 也占号）。
* **`<serverTag>` 取自 cookie[14:16]**，不是 clientTag ——
  这一点两边都按 cookie[14]/[15] 校验，写错了会**静默丢包**（本轮自测踩过）。
* AES 流密钥 = `SHA1(ECDH共享x(28B大端) ‖ securityKey(16B))` → 24B（末 4B 补 0）；
  `securityKey` = **16 个 0x01**。
* 流加密计数器 = `SHA1(seed)`，`seed = seq(2) | 00 00 | serverTag(2)`，逐块 +1。
* `hmac8 = HMAC-SHA1(key24, [0:6] ‖ [14:])[:8]`。

### 客户端 usercmd 明文（14B，实录解出）

```
01 00 00 00 | 00 00 00 00 | 00 00 00 00 | 00 02
  head=1       ack[5:9]      …              terminator
```

`head & 0xE0000000 == 0` → 走 netchan 分支；`body = plain[13:]=0x02`，
`read_reliable`/`read_input` 都正常返回空（不抛异常）。

> ⚠️ 注意：**别用全零 14B 当"空命令"样本** —— 它会触发
> `REJECT_USERCMD reason=Truncated bytes`，但那不是客户端的真实行为。
> 自测里用的是上面这条实录字节。

---

## 2. 离线自测：`battle_selftest.py`

不需要游戏，几秒跑完，逐步断言：

```powershell
cd "D:\BaiduNetdiskDownload\使命召唤OL\REF_LOBBY_KIT"
python -X utf8 battle_selftest.py        # 全流程
python -X utf8 battle_selftest.py -v     # 打印每步字节
```

10 步（全绿 = 退出码 0）：

```
① NAT 遍历（29B，首字节 0d->0c）
② DTLS init -> 38B cookie
③ cookie+公钥 -> 114B key ack（客户端侧独立互推传输密钥，必须等于服务端）
④ OOB getchallenge -> challengeResponse
⑤ OOB connect -> connectResponse
⑥ stats 分块 -> statResponse
⑦ heartbeat x2 -> heartbeatresponse
⑧ 服务端**主动**下发 game state（263B，含 g_gametype/mapname/coop）
⑨ 客户端 usercmd 后服务端继续发数据帧
⑩ 真实 14B usercmd 必须被解析器接受（回归护栏）
⑪ 快照必须**自动**开始（不能等客户端的 gamestateupdate）—— 回归护栏
```

它把"改一次跑一局游戏（3~5 分钟）"压缩成"改一次跑 13 秒"，
而且失败会直接告诉你**是哪一步**。

### 本轮它抓到的东西

第一次跑就在 ④ 之前失败，暴露了自测客户端的一个真错误
（数据帧 `[2:4]` 填了 clientTag 而不是 serverTag）。修好后又暴露
**⑧ game state 从未下发** —— 这正是真实客户端卡住的原因。
两个问题都不是靠读代码发现的，是靠复放真实字节发现的。

---

## 3. 改动清单（本轮）

| 文件 | 改动 |
|---|---|
| `snapshot_diff.py` | **新增**：把 `_build_motion_snapshot` 的 idx 序列和真实 trace 逐字段对照（★ 见 §7，基准已换成**完整**的 motion-trace） |
| `battle_server.py` | ① `connect` 分支置 `connect_done` 并**立即安排 game state**；② `pump_gamestate` 触发条件由 `ready` 放宽为 `ready or connect_done`；③ assoc 增加 `connect_done` 初值；④ 下发 game state 的**同时启动 `snapshot_due`**（快照不再等 `gamestateupdate`） |
| `battle_selftest.py` | **新增**：离线复放真实抓包的自测（**11** 步断言，含两条回归护栏） |
| `check_run.py` | **新增有效判据**：`80/203 库存请求` —— 见 §1.4，防"仓库/大厅被锁"再次被漏判 |
| `firingrange-gamestate.bin` | 从 `F:\桌面\ol\新建文件夹\evidence\` 取回（259B），此前一直缺 |

回滚：`battle_server.py` 的三处都在 `connect_done` 上，删掉即可回到旧行为
（旧行为 = 客户端永远等不到 game state）。

---

## 4. 下一步（战斗服真正要做完的）

按"能离线验证"的顺序：

```
① 快照内容**正确性**（下一步的重点）
   - 现在的 ⑪ 只断言"快照开始发了"，还没断言**客户端能接受**。
   - 我们发的是 **124B** 快照；而实录里客户端真正读的那份
     `demo-player-fields-trace.json` 只有 **140 bit**（≈18B）——
     说明**真实快照比我们的瘦得多**，我们的字段集/宽度大概率是错的。
   - 权威素材（都已在本机，可直接用来对齐）：
       F:\桌面\ol\新建文件夹\reference\demo-player-fields-trace.json
           → 75 次字段读、140 bit 全量序列（含每段的位宽与值）
       F:\桌面\ol\新建文件夹\reference\playerstate-motion-trace.json
       ...-posture- / -spawn- / -equipment- / -health- / -zero- trace.json
   - 做法：把 demo 的字段读序列做成"期望位流"，和 `_build_motion_snapshot`
     的输出逐位 diff；差异处就是错的地方。**先做这个，再上真机。**

② 出生点 / 位置 / 朝向
   - 已有开关：spawn_at.txt / static_spawn.on / spawn_from_map.on /
     omit_viewangles.on / mirror_predicted.on（+ --ps-probe 探针）
   - 判据见 HANDOFF §13.35~13.53，别再重跑那些已否证的组合

③ 武器 / 装备
   - _Equipment 默认 M4A1；实录有 CodolRangeEquipment 的字段表

④ 把自测扩成"回归套件"
   - 每次改 battle_server 先跑 battle_selftest.py，
     再起游戏做一轮端到端
```

---

## 6. 真机一轮的观察（2026-10-07 15:26~15:31）

战斗服侧无异常：正常启动、`game state 文件: firingrange-gamestate.bin (259 字节)`
已加载、快照已 armed。这轮**客户端没走到战斗服**——它在大厅阶段
（`hmac=BAD` 反复重解密钥那一段）就 `ConnectionResetError(10054)` 掉了。

> 这跟战斗服的改动无关（那轮 `收包=0`，客户端压根没连 28960）。
> 大厅偶发握手失败是**另一条线**的问题，需要单独看；
> 但它会挡住"战斗服端到端验证"，所以复现时要先把大厅这一关跑稳。

### 6.1 ✅ 大厅断连已修（2026-10-07 15:39，实机验证）

**症状**：一轮里连续断连 3 次，每次都停在
`★ 解密成功 #1 seq=2 hmac=BAD marker=0x4F service=133 ver=0x48 declared=79273349`。
`marker=0x4F` / `service=133` / `declared=79273349` 全是**不可能的值**
（正常帧永远是 `marker=0x86 / ver=0x03 / declared 几十`）——
说明 AES 用的是**错的密钥**，解出来是乱码。

**根因**（`lobby_server.py` `handle_lobby` 的密钥选取分支）：

```python
sec = conn_keys if conn_keys.get("_ok") else (keys_of(derived) or read_secrets())
```

客户端每次重连，nt10 都会**追加一组新的派生密钥**到 `kdf_sessions.txt`
（实测同一会话密钥 `96149686…` 累积到 2/3/4 组）。
当 `pick_keyset`（按 HMAC 试解）**没命中**时，这行就回落到"猜的一组"硬解，
于是 hmac=BAD；紧接着 `pending = []` 把请求丢掉、**永不回应** →
客户端超时重连 → 又追加一组 → 再失败 → 死循环 → `ConnectionResetError(10054)`。

**修法**：**候选密钥组没过 HMAC 就什么都不做** ——
`sec = None`，帧**保留在 `pending`**，等 nt10 写入正确的那组后下一轮自然命中。
（客户端重连会让 nt10 重新派生，那正是我们要等的那一组。）

**实测对照**：

```
修之前：hmac=BAD marker=0x4F service=133 declared=79273349   ← 乱码
        15:29~15:30 连续断连 3 次

修之后：hmac=OK  marker=0x86 service=71  declared=84          ← 干净
        一整轮 88 个 hmac=OK / 0 个 hmac=BAD / **连接全程未断**
        正常跑满 40 个 service/task（含 80/70,107,119,173,174,232 目录页、
        11/4 房间、21/1 会话）
```

**判据（以后看这个）**：`lobby_srv.log` 里
`[keys] ★ 试解命中:` 出现 + 首帧 `hmac=OK marker=0x86`。
若出现 `hmac=BAD` 或"候选密钥组 N 组都未通过 HMAC"，
就是这条链又坏了。

---

## 5. 一句话交接

**战斗服的协议层是通的（有完整真实抓包），卡的是"连上之后不推首个
game state"。** 本轮修好了那一处，并把整条链固化成一个 13 秒的离线自测。
接下来每一步都应该先加进 `battle_selftest.py`，再上真机。

---

## 7. ★★ 快照字段语义对齐（2026-10-07，含一次自我纠错）

### 7.1 纠错：基准用错了

上一版我拿 `reference/demo-player-fields-trace.json` 当基准，得出：

> "真实快照只有 140 bit / 32 字段，我们 984 bit，序列差很多。"

**这个结论是错的。** 那份文件自己写着：

```
scope  = offline position branch trace; ... not live packet validation
error  = RuntimeError('Unclassified call 0xc42d81')     <- 解到一半就抛了
```

它**残缺**。正确基准是同一目录下的：

```
playerstate-motion-trace.json
  completed = True          <- 完整
  totalBits = 497
  reads     = 173
  带完整语义 origin / viewAngles / velocity / clips / reserve / owned /
             events / weaponTime / weaponState / weaponDelay / gravity / ...
```

### 7.2 换成正确基准后的真实结论

把 trace 的 `reads` 按 index-skip 位流解出来（`snapshot_diff.py` 的
`decode_index_sequence`），真实字段序列是：

```
[0, 1, 3, 8, 10, 11, 13, 14, 17, 18, 19, 20,
 21, 22, 23, 24, 29, 34, 38, 39, 41, 44, 54, 56, 60, 61, 63, 68, 84]
```

我方（修好 idx21..24 之后）：

```
[0, 1, 3, 8, 10, 11, 13, 14, 17, 18, 19, 20,
 21, 22, 23, 24, 29, 34, 38, 39, 41, 44, 45, 54, 56, 60, 61, 63, 68, 219]
```

**28 / 29 个字段完全对上，且顺序一致。** 我们的快照结构基本是对的 ——
之前"差很多"是**基准残缺**造成的误判。

唯一真缺口是 **idx 84**（武器/弹药表尾部，见 §7.4）；
另有两个多余项 `45`（默认关）与 `219`（待确认）。

### 7.3 唯一的真缺陷：idx 21..24 语义错位（已修）

实录解码 idx 21..24 的读值：

```
idx=21  (1,1)(1,1)(11, 1157)   <- 槽0: 武器 1157
idx=22  (1,1)                  <- 槽1: 无
idx=23  (1,1)(1,1)(11, 0)
idx=24  (1,1)(1,1)(11, 0)(1,0)
```

与 metadata 完全吻合：`clips=[[1157,35,0],[1158,15,0],[0,0,0]]`、
`owned=[1157,1158,317]`、`weapon=1157`。

=> 这四个字段是**武器槽**。而旧代码往这里写的是 `eq.events[i]`（事件号），
客户端会把**事件号当成武器 id** 解释 —— 语义错位。

**已改**（`battle_server.py` `_build_motion_snapshot`）：idx 21..24 改写成
"present 位 + 有值位 + 11 bit 武器 id"，形状逐位取自实录。
回退开关：`slot_events_legacy.on`（存在时回到旧的事件数组写法）。

### 7.4 idx 84 = 武器/弹药表的完整规格

`idx=84` 解出来是一整段结构化数据，与 metadata 对得上：

```
(4,15)x8 ...                       <- 已拥有武器表尾部填充
(17, 5)                            <- clips 计数 = 5
per-slot: (4,i)(11,weapon)(1,1)(9,clip)(1,0) ...
per-slot: (4,i)(11,ammo_key)(12,reserve) ...
```

这正是我方 `_build_motion_snapshot` 末尾 `guns` 循环的对应物。

### 7.5 当前状态

* `battle_selftest.py` **12 步全绿**，新增第 ⑫ 步作为语义回归护栏
  （已用"注入回归 -> 必须报 FAIL"验证过它真的会抓）。
* `snapshot_diff.py` 基准已换成 motion-trace，并打印差异清单：
  现在报 **28/29 对齐**，缺 `idx 84`，多 `45`（默认关）/`219`。
  （两个工具都修了"只认字面量 `w.index(N)`、漏掉 `w.index(21 + i)` 循环形式"
   这个 bug —— 否则会把已写好的字段误报成缺失。）

### 7.6 下一步

```
✅ ① idx 219 —— 已确认真实序列没有 → 默认**不发**（回退开关 `idx219.on`）
✅ ② idx 45  —— 保持默认关
✅ ③ idx 84  —— 已逐位实现（见 §7.7）
✅ ④ 真机验证 —— 见 §7.8
```

### 7.7 ✅ idx 84 已实现 —— 快照字段序列 **29/29 全对齐**

把实录 idx84 段 97 条读数全部解出来后（工具 `_idx84_decode.py`），
结构是：

```
9 个 4bit 块 = 15×9 + 0                      <- 稀疏表头
10 个 1bit   = 1,1,0×8
1bit=1 + 17bit=<clips 计数>                  <- 实录 = 5
clips 项: 1bit=1 + 4bit=slot + 11bit=weapon
                 + 1bit=1 + 9bit=clip + 1bit=0
1bit=1 ; 1bit=1                              <- owned 列表
owned 项: 1bit=1 + 1bit=1 + 11bit=weapon + 5×1bit + 12bit
1bit=1                                       <- reserve 列表
reserve 项: 4bit=slot + 11bit=ammoKey + 12bit=reserve + 1bit(继续?)
尾部 13 个 1bit=0
```

**最关键的一处**：这段内容在实录里是 **idx 84** —— 序列里 `68` 的下一个
直接就是 `84`（编码 = `1bit(0) + 4bit(15)` → index 68+16=84）。
旧代码**只写了内容、漏了 `w.index(84, prev)` 这个索引标记**，
客户端会把这一整段当成"仍属于上一个字段"→ **整段错位**。

修完后 `snapshot_diff.py` 报：

```
双方都有  : 29 个
我们缺的  : []
我们多发的: []
```

### 7.8 真机一轮（2026-10-07 16:49，300s）

```
大厅 : hmac=OK 69 / hmac=BAD 0 / 断连 0        ← 健康
      [keys] ★ 试解命中: 密钥组 src=kdf-session
战斗服: game state 文件 259B 已加载；快照发到 141 字节/帧
        收包=0 —— 客户端仍停在大厅，需**手动点进对局**才会连 28960
```

快照帧从 124B 涨到 **141B**，正是新增 idx84 那一段的量。
到这一步，"协议 + 字段序列"已经没有已知缺口；剩下的验证只能靠
**在游戏里手动点进靶场**。

### 7.9 开关清单（本轮新增）

| 开关 | 默认 | 作用 |
|---|---|---|
| `idx219.on` | 关 | 发旧代码的 idx219（实录没有，仅回退用） |
| `slot_events_legacy.on` | 关 | idx21..24 回到旧的事件数组写法（仅回退用） |
| `idx45.on` | 关 | 发 idx45（实测会让视角乱转，保持关） |
| `coop_map.txt` | （无） | 覆盖剧情 session 的 map 名（写一行） |

---

## 8. ★★★ 剧情任务实测（2026-10-07 17:02，用户手动点击）

用户手动进剧情任务，抓到了**决定性证据**。

### 8.1 大厅侧全链路都跑通了

```
[17:02:56] findSessions 解析值=[1, 0, 10, -695030357] -> 回填 playlist=10
[17:02:56] findSessions -> ★ PvE coop mission session 对象
[17:02:56] 6/14 命中 'mmbook' -> push 'mmbook accepted'
[17:02:56] ★ mmstart 完整命令:
           mmstart sv_resetServer; 2486 1; 3265 1; 2489 0; 2574 0; 2500 0;
           g_gametype coop; g_difficulty 0; ;
           map coop_take_mp_fav_tropical;
           2654 M7-E8S6Client; roomChatChannelID 1234605616436508552;
[17:02:57] 0B/4 setRoomData ... 已回显频道推送+game start
11/13 createRoom, 21/5 findSessions, 6/14 ×3, 11/4 ×2 全部命中
```

### 8.2 ★ 但客户端**要的地图**和我们**回的**不是同一张

```
客户端明说:  map coop_take_mp_fav_tropical     (来自 mmstart)
我们回的  :  map coop_training_mp_cargoship    (来自 COOP_PLAYLIST_MAP[10])

⇒ 两张不同的图。客户端拿到的"要去哪"与"要下哪"对不上
  ⇒ battle_srv.log 收包=0（它根本没去连 28960）
```

**素材侧确认客户端要的那张图存在**（就在沙箱里）：

```
ff_init_coop_take_mp_fav_tropical_V53.ifs        29,997,445 B
lf_init_coop_take_mp_fav_tropical_V4.ifs         24,945,937 B
lf_hi_init_coop_take_mp_fav_tropical_V3.ifs      41,773,363 B
```

### 8.3 已修

`codol_crypto.COOP_PLAYLIST_MAP[10]` 改为实测值
`coop_take_mp_fav_tropical`；并加 `coop_map.txt` 覆盖口（写一行地图名）。
靶场分支不受影响（自测确认仍是 `mp_firingrange`）。

> ⚠ 注意：`lobby_server.py` 是**常驻进程**，改完必须**重启**才会生效。
> 本轮 17:05:44 的重试仍回旧地图，就是因为进程还是旧代码。

### 8.4 下一步判据（重启后再点一次剧情）

同一位置观察：

```
① lobby_srv.log 应出现 map=coop_take_mp_fav_tropical
② battle_srv.log 应出现 RX #1 16B（DTLS init）← 客户端终于连 28960 的实锤
③ 若 ② 成立：握手 → stats → game state → 快照 会依次出现
```

### 8.5 ★★ 第三轮实测（17:16）：确认"地图是每次现选的"

```
[17:16:04] findSessions -> ★ PvE coop mission session
           map=coop_take_mp_fav_tropical          ← 我们回的（上一轮记住的）
[17:16:04] ★ mmstart 选择: gametype=coop map=coop_evasion_mp_con_spring
                                                     ← 客户端这次选的是**另一关**
[17:16:04] ★ 已记住剧情地图 -> coop_map.txt = coop_evasion_mp_con_spring
```

**三条硬结论**：

1. **剧情任务是"每次现选"的** —— 三轮分别是
   `coop_take_mp_fav_tropical` / `coop_chopper_mp_suburbs` /
   `coop_evasion_mp_con_spring`。写死一张图**永远追不上**。
2. **时序是**：`21/5 findSessions` → 我们回 session（含地图）
   → 客户端发 `6/14 mmstart`（这才告诉我们它选了哪关）。
   即"我们回答在地图确定**之前**"。
3. 三张图**素材都在**（沙盒 IIPS 里有对应 `.ifs`）：
   ```
   ff_init_coop_take_mp_fav_tropical_V53.ifs        29,997,445 B
   ff_init_coop_evasion_mp_con_spring_V13.ifs       13,071,613 B
   （coop_chopper_mp_suburbs 同理）
   ```

### 8.6 已实现"自校正闭环"

`lobby_server.py` 在收到 `mmstart` 时把地图**记到 `coop_map.txt`**；
`codol_crypto` 下一次 `build_mission_session_object` 就用它。
于是：**玩家选哪一关，下一轮 session 就回哪一关**（一轮收敛）。

实测已生效：
```
[17:16:04] ★ 已记住剧情地图 -> coop_map.txt = coop_evasion_mp_con_spring
$ coop_map.txt 内容 = coop_evasion_mp_con_spring
```

> 局限：因为时序上 findSessions 在前，**改选关卡后需要再点一次**才能对齐。
> 若要一次就中，需要更早拿到"玩家选了哪关"（例如 28/1 任务参数或
> 剧情列表的 10/21 下发内容里带的选择），见 §8.7。

### 8.7 下一步（两条都值得做）

```
① 再点一次剧情 —— 验证"自校正闭环"能否让 map 对齐
   判据：battle_srv.log 出现 RX #1 16B（DTLS init）

② 若仍不连：找"更早的地图来源"
   候选：28/1（任务参数，客户端每次开局都会发）、
        10/21 下发的剧情列表里是否带关卡 id、
        21/5 请求里那个 i32（实测 0xD692ADAB 之类）是否就是"关卡选择"
```

### 8.7.1 ❌ 已否证：`28/1` 不含关卡选择（2026-10-07 17:23）

两次点击选了**不同的关卡**，但 `28/1` 的 payload **逐字节相同**：

```
关卡 coop_evasion_mp_con_spring   28/1 = 6c 08 08 00 00 00 02 00 00 00 00 00 00 00 05 00 00 00 00
关卡 coop_take_mp_fav_tropical    28/1 = 6c 08 08 00 00 00 02 00 00 00 00 00 00 00 05 00 00 00 00
                                        ^^^^^^^^^^^^^^^^^^^ 完全一致
```

⇒ **`28/1` 与选了哪一关无关**，不能用来提前确定地图。`28/*` 这条线到此为止。

### 8.7.2 请求时序（实测固定顺序）

```
11/13 createRoom   ->  28/1 任务参数  ->  21/5 findSessions  ->  6/14 mmstart
                                          ↑ 我们在这里必须给出地图
                                                                    ↑ 到这里才知道选哪关
```

`28/1` 已否证；那么"我们回答在地图确定之前"就是**当前架构的硬约束**。
可行的收敛办法只剩两条：

```
a) 自校正闭环（已实现）：上一轮记住 → 这一轮对上。选同一关点两次即收敛。
b) 让 session 里的地图**不参与**客户端的"去哪张图"判定
   （即地图不是它连战斗服的前置条件）—— 需要确认它到底卡在哪一步。
```

### 8.7.3 待确认

地图不一致时，客户端**仍然**没连 28960。但也可能"地图"根本不是
它不连的原因 —— 需要一次"地图已对齐"的对照：

```
做法：让 coop_map.txt 固定成某一关，然后**连点同一关两次**。
      若第二次仍不连 28960，则地图不是根因，要转查别的门槛。
```

### 8.9 ★★★ 关键否证：客户端把对战地址送到**外部腾讯服务器**（不是我们）

把整轮 `sendto` 目标去重（`n10_pve3_20261007_a2.txt`，600s）：

```
101.67.36.18:10035      ← ★ 外部腾讯地址，全程高频（gcloudvoice.dll 发出）
116.162.186.61:443
122.96.96.225:8081
127.0.0.1:10001         ← TenProxy 本地桥
127.0.0.1:64654 / :64656
140.206.161.148:8011
182.50.14.56:8081
61.241.53.221:80
```

**整个 600 秒日志里 `28960` 出现 0 次。**

而 `101.67.36.18:10035` 的发送方是 **`gcloudvoice.dll`**（腾讯语音/中继组件），
不是我们的战斗服，也不是大厅。

**这解释了"收包=0"的完整含义**：

```
我们 session 里给的地址 = 127.0.0.1:28960   （没错，格式也对）
客户端却把对战流量送去了 101.67.36.18:10035  （它自己另找的地方）
```

⇒ 客户端**没有采用**我们 session 里那个地址去连"对局"。
它另有来源决定"对局流量往哪走"（最可能是平台/语音中继的下发），
而我们的 28960 只被期望用于**DTLS 握手那一层**（三方靶场就是那么走的）。

### 8.10 由此得到的两条路线

```
路线 A（继续攻 PvE）：找出"101.67.36.18:10035 这个地址是谁下发的"，
        把它重定向到本机，看客户端会不会改用我们的地址。
        —— 需要追 gcloudvoice.dll 的地址来源（可能是平台 QoS/中继下发）。

路线 B（回到靶场）：三方唯一验证过的路径是**靶场**
        （session + booking + 28960 的 DTLS）。
        靶场那条链不经过 gcloudvoice，直接连 28960。
        ⇒ 用靶场做端到端，是**确定性更高**的一条路。
```

> 本轮结论：PvE 剧情任务的对局流量走的**不是** 28960，
> 因此拿它验证战斗服是错的选择。**应该用靶场验证战斗服。**

### 8.11 靶场路径已就绪（推荐用它做端到端验证）

路由实测（`lobby_server.reply_objects` 的 21/5 分支）：

```
playlist != 10  ->  build_mission_session_object(firing_range=True)
                    len=268, map=mp_firingrange, GameType=0x1000007,
                    MaxPlayers=1, 地址块 = 127.0.0.1:28960   ← 直接指向我们
playlist == 10  ->  PvE coop 分支（地图随关卡变）
```

需要的开关**全部已开**：

| 项 | 状态 |
|---|---|
| `firingrange-session.enabled`（21/5 回靶场 session） | ON |
| `firingrange-booking-push.enabled`（6/14 回 booking accepted） | ON |
| `firingrange-battle.enabled` | ON |
| `firingrange-gamestate.bin`（259B） | 有 |
| 战斗服 28960 快照字段序列 29/29 对齐实录 | 有 |

> 为什么靶场更可信：三方参考**唯一验证过**的就是靶场那条链，
> 且它**不经过 gcloudvoice**，是直接连 28960 的。PvE 那条走外部地址。

### 8.12 下一轮判据（点靶场）

```
① lobby_srv.log: findSessions -> ★ 靶场 mission session 对象（268 字节）
② battle_srv.log: RX #1 16B  ← 客户端连上 28960 的实锤
③ 之后依次应看到：TX_DTLS_INIT_ACK(38B) -> TX_DTLS_KEY_EXCHANGE_ACK(114B)
   -> RX_OOB getchallenge/connect -> RX_STATS -> TX_GAMESTATE -> TX_SPAWN_EXPERIMENT
```

如果在 ② 就断了（`收包=0`），则说明连靶场也不走 28960，
那就得回头查"客户端到底从哪里拿对战地址"（见 §8.9 路线 A）。

---

## 9. ★★★ 找到闪退的直接原因：我们推的 `mmbook accepted` 把客户端打崩了

### 9.1 现象（用户实测："点击进入靶场游戏就闪退"）

三次点击，三次闪退，**每次都在我们推送 `mmbook accepted` 之后 1~2 秒**：

```
[17:45:05] 6/14 命中 'mmbook' -> push 'mmbook accepted'(data=20)
[17:45:05] -> 0x85 推送 type=2 seq=50 (98 字节 body=51)
[17:45:07] ★ 解密成功 #50 service=71 task=7 declared=469   <- ClientException!
[17:45:07] 对端关闭                                         <- 客户端自己蹦了

[17:45:54] push 'mmbook accepted'  -> [17:45:55] 对端关闭
[17:48:02] push 'mmbook accepted'  -> [17:48:03] 对端关闭
```

**三次全部**：推 `mmbook accepted` → 客户端发 `ClientException` → 断连。
而且本会话里 **`mmstart` 一次都没到过** —— 客户端在推送到来后就崩了。

### 9.2 关键点：那条推送是**靶场专用信封**，却用在了 **PvE** 上

客户端的 `mmbook` 原文是：

```
0a 01 00..00 | 13 08 1d 00 00 00 | 19 00 00 00 | "mmbook 796 AQAAAAAAAAA= 0" 00
                                      ^^ 长度 25
```

即 `mmbook 796 ...`（**playlist 796**，是剧情/PvE 的 booking），
不是靶场。而我们回的是照抄 C# 的**靶场** booking 信封：

```python
FR_BOOKING_ACCEPTED = b"mmbook accepted\x00"
accepted = struct.pack("<I", len(FR_BOOKING_ACCEPTED)) + FR_BOOKING_ACCEPTED
pushes = [(2, cc.instant_push_body(1, "localhost", accepted))]
```

—— `senderId=1` / `"localhost"` / service 21，这套是三方**只在靶场**用过的。
在 PvE booking 上回靶场信封，客户端解不了 → `ClientException` → 闪退。

### 9.3 处置：先关掉这条推送（可一键恢复）

```
mv firingrange-booking-push.enabled firingrange-booking-push.enabled.OFF_TEST
```

关掉后 `6/14 mmbook` 只回**裸 ACK**，不再推送：

```python
return ack("6/%d 命中 'mmbook' (booking 开关未开, 仅空应答)" % task)[:2] + ([],)
```

**判据**：再点一次，
* 若客户端**不再闪退** → 确认是这条推送打崩的；
* 若仍闪退 → 是别的推送/字段，继续按同样方法二分。

恢复：把 `firingrange-booking-push.enabled.OFF_TEST` 改回
`firingrange-booking-push.enabled`。

### 9.4 教训（第三次同类）

**不要把一个场景验证过的信封用到另一个场景。**
三方只验证过"靶场 + booking 推送"；我们把它也发给了 PvE，
结果直接把客户端打崩。这与商城 SKU 页、快照 idx21..24 是同一类错误：
**拿一处对的信息去套另一处**。

新纪律：**任何服务端主动推送，必须先确认"这个场景下客户端期望它"** ——
用开关隔离 + 单次验证 + 随时回滚。

### 9.5 关掉 booking 推送后的第一轮（17:50~17:53）

```
[17:50:17] 靶场开关: session=True booking=False battle=True   ← 推送已关
[17:50:42] 大厅连接建立 + 试解命中                            ← 握手正常
[17:52:40~17:53:02] 客户端退出并重连（对端关闭 x2，17:53:09 重新起进程）
战斗服: 收包=0（客户端没走到对局）
```

这一轮 `n10_nobooking_20261007` 的 sendto 只到 8 次就结束 —— **客户端这一轮
根本没走到商城/booking 那一步**，所以还没能验证"关掉推送是否不闪退"。
需要再点一次（这一轮启动后客户端只走到大厅就退了）。

**下一步**：在 `booking=False` 下再点一次，只看一件事 ——
`mmbook accepted` 推送是否还会导致 `ClientException`。

### 9.6 ★★ 二分实验结果（17:57，关掉推送后）

用户点击后：**不再闪退**，但游戏提示 **"服务器繁忙"**。

日志显示客户端进入**5 秒一次的轮询**：

```
[17:57:09] 21/5 findSessions  -> 6/14 命中 'mmbook' (仅空应答)
[17:57:14] 21/5 findSessions  -> 6/14 命中 'mmbook' (仅空应答)
[17:57:19] ... 每 5 秒重复，一直到 17:57:35 之后转为 keepalive
```

`mmbook` 原文始终是（逐字节相同）：

```
0a 01 00 00 00 00 00 00 00 | 13 08 1d 00 00 00 | 19 00 00 00
| "mmbook 796 AQAAAAAAAAA= 0" 00
```

**结论（两条都成立）**：

1. `mmbook accepted` 推送**确实是闪退的原因**（关掉就不崩了）。
2. 但它同时**是推进的必要条件** —— 不推 → 客户端拿不到 booking 回执 →
   无限重试 → 显示"服务器繁忙"。

⇒ 所以不能简单关掉，得**发一条客户端能接受的 booking 应答**。

### 9.7 与三方参考的差异（下一步要做的）

三方参考（`_ref/CodolLocalLobbyServer.cs:1436-1449`）在 `6/14` 上是：

```csharp
// ① 先回 ACK（generic ack, replyId = ++num9）
byte[] ack2 = BuildTaskReply(localSecrets, b4, num8++, ++num9, resultObj2);
stream.Write(ack2, ...);
// ② 再推（仅当开关存在 且 body 含 "mmbook "）
byte[] push = BuildPushFrameWithSender(..., 21u, accepted, 1, "localhost");
```

**注意参考用的是两个独立计数器**：`num8++` 做帧 seq、`++num9` 做 replyId。
我方目前用**请求的 seq 回显**当 replyId（`lobby_server.py:1148-1149`）。
在 1:1 情况下两者同值，但**一旦中间插入推送，就会错位**。

三条待验证的假设（按可能性）：

```
a) replyId 语义：应改成"服务端自己的递增计数器"，而不是回显请求 seq。
   （参考用 ++num9；我方回显 r["seq"]。1:1 时同值，插入推送后错位）
b) 那条推送可能**只该给靶场**（playlist 1），PvE（796）不该收到。
   但本客户端发的是 796，我们却按靶场处理 —— 需要按 playlist 分流。
c) 推送的 service 号（我方 21）或 sender 名可能需要跟着 booking 类型变。

验证方式：一次只改一条，用"是否还闪退 / 是否还繁忙"做判据。
```

### 9.8 当前状态

```
• firingrange-booking-push.enabled 已改名为 .OFF_TEST（推送关闭）
• 客户端不再闪退，但停在"服务器繁忙"（booking 一直重试）
• 战斗服 收包=0（客户端没到连 28960 那一步）
• 现象可复现，判据明确
```

**恢复推送**：把 `.OFF_TEST` 后缀去掉。

### 9.9 ★★★ 找到真正的崩溃机制：**推送抢了客户端的帧序号**（18:06 实录）

replyId 改动**没解决问题**（客户端仍闪退）→ 已回退。
但那一轮留下了**逐帧对照**，直接暴露了机制：

```
#13 客户端请求  seq=13  → 我方应答 seq=13 (replyId=13)   OK
#14 客户端 mmbook seq=14 → 我方应答 seq=14 (replyId=14)   OK
                        → 我方推送 seq=15   ★ 占掉了 15
#15 客户端发 ClientException，用的就是 **seq=15**        ← 撞车！
对端关闭
```

**机制**：客户端按**自己**的序号递增发请求（13、14、15、16…）。
我们的推送从**同一个计数器**取号，正好抢在它前面占了 `15`。
客户端看到 `15` 已被占（它认为那是自己的号）→ 判定异常 → 崩。

而参考实现（C#）用的也正是同一个 `num8++` —— 但**它的 `lsg.log` 里
从未出现过 `service=11`**，即三方**从未验证过这条推送路径**。
所以这不是"我们抄错了"，而是**参考实现本身这条路径就是坏的**。

### 9.10 处置：把推送放到客户端不会用的号段

```
推送 seq = 客户端当前请求 seq + push_seq_offset(默认 1000)
```

```
客户端 seq=13 -> 应答 seq=13, 推送 seq=1013
客户端 seq=14 -> 应答 seq=14, 推送 seq=1014
客户端 seq=15 -> 应答 seq=15, 推送 seq=1015
```

开关：`push_seq_offset.txt`（写偏移值，默认 1000）。

> 注意：`2026-10-04` 曾试过"独立号段 push_seq=1000"并记录为**失败** ——
> 但当时同时还有别的 bug（replyId/seq +1），不能据此判死。
> 这次是在 replyId 已确认无关、且序列逐帧对齐之后重做的，条件不同。

### 9.11 本轮已改/待验

| 改动 | 状态 |
|---|---|
| replyId 改独立计数器 | ❌ 无效，**已回退**成回显请求 seq |
| 推送 seq 改 `请求seq + 1000` | ✅ 已实现，待实机验证 |
| `firingrange-booking-push.enabled` | ✅ 已恢复（推送是推进必需） |

### 9.12 ★★★ 定论：这条推送**本身**就会打断连接（seq 号段不是根因）

把 seq 挪到 `请求seq+1000` 之后重测，客户端**仍然**断，只是症状换了
（从"秒闪退"变成"**大厅连接中断**"）。逐条统计本轮日志：

```
0x85 推送 type=2 出现 9 次
其中 9 次后面**紧跟着就是** "对端关闭"
       —— 9/9，无一例外
```

```
[18:13:39] -> 0x85 推送 type=2 seq=1008(请求seq+1000, 避开客户端号段)
[18:13:39] 对端关闭                      ← 推完立刻断
[18:13:44] -> 0x85 推送 ... seq=1011
[18:13:44] 对端关闭
... 共 9 次，模式完全一致
```

**结论**：改 seq 号段**没有解决问题** → 号段不是根因。
这条 `mmbook accepted` 推送**无论用什么 seq 都会打断连接**。

### 9.13 为什么：这是**靶场专用**信封，却发给了 **PvE**

客户端 `mmbook` 的完整解码（TAG 结构）：

```
0x0A u64          = 1                             (sender/会话 id)
0x13 blob len=29  = 19 00 00 00 "mmbook 796 AQAAAAAAAAA= 0"
                    ^^^^^^^^^^^ u32(25) = 内层消息长度
                                                     ^^^ playlist = 796
```

`796` 是**剧情/PvE** 的 playlist。而我们的 `mmbook accepted` 是照抄三方的
**靶场**回复（`senderId=1` / `"localhost"` / service 21）——
三方**只验证过靶场**，它的 `lsg.log` 里连 `service=11` 都没有。

⇒ 用靶场信封回 PvE 预约，客户端解不了 → 直接断线。

### 9.14 处置与下一步

```
已做：firingrange-booking-push.enabled
        -> .OFF_CONFIRMED_CRASH（推送关闭，避免继续打断连接）

关掉后客户端会回到"服务器繁忙"（无限重试 mmbook），
但**不会再断连** —— 那是个更可用的基线（至少大厅稳定）。
```

两条路（下一步二选一，建议先 1）：

```
1) 走**靶场**而不是 PvE：靶场才是三方验证过的那条链。
   需要让客户端进入靶场入口（playlist=1），而不是剧情(796)。
   判据：lobby_srv.log 里 findSessions 回的应是
        268 字节 / map=mp_firingrange / GameType=0x1000007。

2) 继续攻 PvE：需要知道 PvE 的 booking 应答该长什么样。
   我方没有任何 PvE booking 的成功样本 —— 三方的 lsg.log 里也没有。
   只能靠"猜 + 单次验证"，风险高（已经崩了 9 次）。
```

### 9.15 ★ 重要澄清：**没有独立的"靶场"入口**

本地下发的游玩清单（`mp_playlists_shipRetail_1.0.0.info`，version 796）里：

```
playlist 条目 = [1, 2, 3, 4, 5, 6, 10]     ← 注意：**没有单独的靶场 playlist**
gametype      = [coop, dm, dom, hp, sr, tag, war]

playlist 10 = "Coop Mission"（剧情/合作），它的地图表里含：
    coop_training_mp_cargoship coop 1
    coop_train_mp_firingrange  coop 1     ← ★ 靶场是**这个列表里的一张图**
    coop_survival_mp_cross_fire coop 1
    ...
```

⇒ **靶场不是独立入口，而是"剧情任务"列表里的一个关卡**
（`coop_train_mp_firingrange`）。

### 9.16 ★ 但客户端的选择**没有传到 21/5**

实测：无论点哪一关，`21/5 findSessions` 的 payload **逐字节相同**：

```
08 01 00 00 00 | 08 00 00 00 00 | 08 0a 00 00 00 | 07 ab ad 92 d6 ...
解析值 = [1, 0, 10, -695030357]      ← 恒为 playlist=10，i32 也恒定
```

也就是说：**"玩家选了哪一关"这个信息，在 findSessions 阶段完全拿不到**。
它只在**之后的 `6/14 mmstart`** 里才出现（`map coop_xxx`）。

这与 §8.5 的结论一致，并解释了为什么写死地图永远对不上。

### 9.17 当前可用基线（建议保持）

```
firingrange-booking-push.enabled -> .OFF_CONFIRMED_CRASH   （推送关闭）

效果：客户端**不再断连**（大厅稳定），但会 5 秒一次重试 mmbook，
      界面显示"正在搜寻服务器 / 服务器繁忙"。
```

**这是一个稳定但不完整的基线** —— 比"点了就崩"好，且可复现。

### 9.18 下一步的真正抉择（需要用户拍板）

我们卡在一个**没有参考答案**的点上：

```
PvE booking 的成功应答应该长什么样？
  · 三方的 lsg.log 里没有 service=11 / 没有 PvE booking 样本
  · ol-mod 源码不在本机（它可能有）
  · 我方手上只有"靶场 booking"这一种信封，而它发给 PvE 必然断连

可选路线：
A) 拿到 ol-mod 的 src/game_server/（它有完整的 booking 子系统）
   —— 这是唯一有"标准答案"的路
B) 继续盲试 PvE booking 应答格式
   —— 每次错都会断连/闪退，效率低且消耗用户耐心
C) 换目标：不去"进对局"，先把**不依赖 booking 的能力**做扎实
   （商城、公告、挑战、好友等大厅功能）
   —— 这些有明确判据，且不涉及未知协议
```

### 8.8 本轮日志文案修正

`PvE coop mission session 对象 ... map=` 旧代码打印的是**常量**
`MISSION_MAP_NORMAL`，与**实际发出去的**地图可能不一致 —— 会误导排查。
已改为打印真正发出去的值（`cc.coop_map_for(playlist)`）。

> **教训（第二次同类）**：素材要**先看 `completed` / `error` / `scope` 再当基准**。
> 残缺的 trace 会给出**看起来很像**但完全错误的差异清单。
