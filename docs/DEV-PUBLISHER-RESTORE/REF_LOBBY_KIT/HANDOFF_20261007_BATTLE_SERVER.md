# 战斗服务器建设 —— 接手手册（2026-10-07）

> 承接 `HANDOFF_20261007_TAKEOVER.md`。本轮**实机验证**了商城 item 分组 SKU 页，
> 并**实测确认**了战斗服收包=0 的根因。结论以本文为准。

---

## 0. 本轮一句话

1. **商城目录页（80/70 等）首次实机通过** —— item 分组 SKU 页发出后，
   `MarketScrollGrid` / `SupplyDrop` 两个 UI 崩溃**双双消失**，商城 UI 不再锁死。
   这解决了 TAKEOVER §5 的 P0「商城空 + 军火箱重叠」。
2. **战斗服收包=0 的根因已实锤**：PvE/剧情任务开局时，客户端**根本不往
   28960 发包**，而是连腾讯外网 `112.132.225.216:10009` + 本地 TenProxy
   `127.0.0.1:10001`。⇒ 缺的是 **dedicated booking / sharedRoomClient 控制面**，
   不是 28960 的握手实现。
3. 剩余 UI 崩溃只剩 **2 条**（首页挑战 #1010 / 公告 #1125）—— 与世界书
   `HANDOFF_20261006_LOBBY_MAP.md` 记录的四条相比少了两条（商城、匹配条已消）。

---

## 1. 商城目录页：从"回空"到"实机通过"

### 1.1 改了什么

`market_skus.build_item_sku_page()`：按 **`item -> [SKU 档]`** 的模型编页
（见 TAKEOVER §15）。只发**含 ground-truth SKU 的 item 组**，当前 5 组：

```
item   122 -> SKU 31774  CP 2280   30 天
item  7110 -> SKU 16096  GP  880   永久
item 22384 -> SKU 39592  GP10880   永久 / 31184 GP 680 7天 / 31759 GP 2580 30天
item 29767 -> SKU 37116  CP10000   永久
item 29892 -> SKU 37251  CP 8000   永久
```

开关：`marketplace-skus-itemgroup.on` + `marketplace-skus-count.txt`
（`enable_itemgroup_sku_test.py [1..5|off]`）。

### 1.2 实机结果（2026-10-07 14:41，`count=1`）

客户端**四个**目录任务全部命中该路径，且**没有锁 UI**：

```
[14:41:25] marketplace 80/70  ★ item 分组 SKU 页: 1 个 item / 1 档 SKU
[14:41:26] marketplace 80/173 ★ item 分组 SKU 页: 1 个 item / 1 档 SKU
[14:41:26] marketplace 80/174 ★ item 分组 SKU 页: 1 个 item / 1 档 SKU
[14:41:43] marketplace 80/232 ★ item 分组 SKU 页: 1 个 item / 1 档 SKU
```

客户端之后**继续正常发** 80/203（库存）、80/230（玩家资产 365755B）、
`71/*` 遥测 —— 说明 marketplace 子系统**没有死**（历史上编错会整块变灰）。

### 1.3 UIException 前后对比（这是"过没过"的唯一判据）

```
基线（itemgroup 生效前，TAKEOVER §15.5）:
  MarketScrollGrid        #1009  还在
  SupplyDrop              #1009  还在
  MatchMakingStripView    #1009  还在
  FilterCategoryButton    #1125  还在
  OnboardingChallenges    #1010  还在

本轮（count=1，实机一轮）:
  MarketScrollGrid        没了   ★
  SupplyDrop              没了   ★
  MatchMakingStripView    没了   ★   ← 上一轮已消（playlist version 796）
  FilterCategoryButton    还在
  MOTDNotificationsPopup  还在
  OnboardingChallenges    还在
```

`_dump_uiexception_bin.py` 现在只剩 **2 条**去重异常：

```
TypeError #1010  OnboardingChallengesChecklistListItem.as:127 -> HomeView
RangeError #1125 FilterCategoryButton.as:215 -> MOTDNotificationsPopup
```

### 1.4 ❌ 更正：「item 分组 SKU 页」是**误判**，已回滚（2026-10-07 15:07）

> **上一节的「通过」结论是错的，已作废。** 下面写清楚为什么判错、以及怎么判。

**症状（用户实测）**：仓库 + 大厅全被锁 —— 正是文档警告过的
"marketplace 子系统解析失败 → STORE/INVENTORY 变灰、本会话不恢复"。

**为什么我先判成了「通过」**：我只看了 `71/7` 里的 UIException 有没有新增
`MarketScrollGrid`/`SupplyDrop`，那两条确实没出现。**但那是无效判据** ——
marketplace 服务一旦解析失败，客户端是**整块停止工作**，根本不会再抛
`MarketScrollGrid`（它连商城页都不构造了）。"异常没新增" 恰恰是崩溃的表现。

**真正有效的判据（事后从日志里补出来的）**：看客户端**还继续不继续要库存**。

```
本轮（itemgroup 开）:  80/* 只出现 task = 70,173,174,230,232
                       ★ 80/203（库存）一次都没有！
对照（itemgroup 关）:  80/203 每次开局都会请求 → 回 7619 件库存
```

客户端收到我们的 SKU 页之后**再也不请求库存**了 —— 这就是
"仓库/大厅被锁"的直接机制。

**处置**：
* 已执行 `python -X utf8 enable_itemgroup_sku_test.py off`；
  `marketplace-skus-itemgroup.on` 与 `marketplace-skus-count.txt` 都已删除
  ⇒ 80/70 等回到**安全空页**（商城仍空，但不会锁 UI）。
* `battle_server.py` 的 game-state 修复**不受影响**（那是另一条路径，
  且已由离线自测覆盖）。

**新的判据纪律（写进 §1.5）**：验商城改动必须同时看**两件事**：
1. `80/203`（库存）在本会话里**出现过**；
2. `71/7` 里没有新增 `MarketScrollGrid`/`SupplyDrop`。
   **只有 (1) 成立，(2) 才有意义。**

### 1.5 把 5 组扩到全目录（真正的"商城可用"）

当前只发 5 组是因为**只有这 5 组有 ground-truth 对照**。
要放量必须先拿到**真实的服务端响应字节**或**字段级的线格式**，
不能靠猜（TAKEOVER §5 的两次打挂教训）。

已有素材（可直接用来扩）：

| 文件 | 内容 |
|---|---|
| `mkt_assets/item_sku_arrays.csv` | 2067 条 / 576 item（多次购买实测可对照） |
| `mkt_assets/sku_table_v2.csv` | 635 条干净记录（含歧义剔除） |
| `CLIENT_OBJECT_SCHEMA.md` 附 1 | `codo.objects.SKUObj` 30 个字段名（exe 0x6af8c0） |

推荐做法（只读 + 单条验证）：

1. 用 `market_skus.build_item_sku_page(limit=N)` 把 N 从 5 逐级抬到
   `len(load_item_groups())`，每级跑一局、用 §1.3 判据；
2. 每一步都把"发出去的 item 集合"落在日志里，出问题时能精确定位到哪一组
   给了客户端解析不了的字段。

> ⚠️ 放量到"多档 SKU 同组"时，注意组内档位**编号量级**要相近
> （`load_item_groups` 已有 `hi//10` 清洗，但那只挡极端噪声）。

---

## 2. ★★ 战斗服务器：收包=0 的根因（本轮实锤）

### 2.1 证据：客户端**从不**往 28960 发包

抓 `sendto` 全量目标（`n10pve_fix3.txt`，PvE 剧情任务一轮）：

```
[t=  2.6s] 122.96.96.225:8081        ← 登录/CDN
[t=  7.6s] 182.50.14.56:8081         ← 登录/CDN
[t=153.9s] 127.0.0.1:10001           ← ★ TenProxy 本地桥
[t=157.9s] 140.206.161.148:8011      ← ★ 腾讯（QoS/平台）
[t=161.7s] 112.132.225.216:10009     ← ★ 腾讯（对战分配，持续心跳）
...
（整轮 240s，28960 一次都没出现）
```

`battle_srv.log` 同轮 `收包=0 NAT=0 init=0 keyex=0 data=0 会话=0`。

### 2.2 这条链的含义

```
大厅 3074:  21/5 findSessions  ✅ 已响应（PvE coop session 对象）
            6/14 mmstart       ✅ 已响应（mmbook accepted）
            11/4 setRoomData   ✅ 已回显 + game start 推送
                ↓
        ★ 客户端随后去连的是「专用对战分配」，不是 28960
                ↓
        sharedRoomClient / DedicatedBookingDispatcher  ← 我们从未实现
                ↓
        分配成功 → 才轮到客户端连战斗服 UDP
```

两个独立参考都印证这点（详见 `F:\桌面\ol\新建文件夹\docs\HANDOFF.md` §13.9）：

* 三方 C# `CodolLocalLobbyServer.cs` 的 `gameStartData` 是**不透明抓包常量**，
  且其 `lsg.log` 里**根本没有 `service=11`** —— 他们自己没验证过房间/剧情路径；
* ol-mod `Servers.cpp:340-365`：`RoomEvent::Ready` → `sharedRoomClient_.setReady(...)`；
  booking → `sharedRoomClient_.setReady(...) + bookingDispatcher_.submit(...)`；
  `sharedRoomClient_.connect(identity, DedicatedControl::configuredClientBridgePort())`
  走的是**另一个端口**，不是 3074，也不是 28960。

### 2.3 结论（写进纪律）

> **不要再往"改 21/5 / 6/14 / 11/4 的推送内容"上投入** ——
> mmstart 推送、game-start 推送、24B/67B 地址块、playlist 对齐，
> 全都已实测不能让客户端连 28960。缺的是**独立的 booking 控制面**。

---

## 3. 战斗服现在的两条路

### 3.1 最短可玩路径：靶场（三方已验证）

靶场那条链**协议层已全通**（TAKEOVER §2「靶场会话 21/5 mission session … ✅」）：

```
session(21/5) → booking(6/14 mmbook accepted) → 客户端连 UDP 28960
  → DTLS init(16B) → cookie(38B) → key exchange(219B→114B)
  → stats 分块 → game state(firingrange-gamestate.bin) → 运动快照
```

`battle_server.py` 已逐条实现且自测全绿；`firingrange-gamestate.bin` 是必须素材
（三方的 `evidence\firingrange-gamestate.bin` 259B **可直接复用**）：

```powershell
Copy-Item "F:\桌面\ol\新建文件夹\evidence\firingrange-gamestate.bin" `
          "D:\BaiduNetdiskDownload\使命召唤OL\REF_LOBBY_KIT\firingrange-gamestate.bin"
```

当前 `battle_srv.log` 每次启动都是 `game state 文件: firingrange-gamestate.bin (缺)`
—— **补上这个文件是靶场路线的第一个必做项**。

### 3.2 完整路径：复刻 dedicated booking 控制面（工作量大）

需要的素材（**不在本机**）：

```
ol-mod  src/game_server/                     整套战斗服（sv_main_mp / sv_snapshot_mp /
                                             sv_collision_mp / NativePmoveBindings …）
        .agents/research/playable_architecture.md
        src/network/DedicatedControl.*        ★ 端口 + 帧格式在这里
```

原包 `E:\handoff2\ol-mod-olfinal.zip` **在本机已不存在**（E: 盘已清理）。
`F:\桌面\ol\新建文件夹\` 只有三方 C# 参考 + 录像证据，**没有 ol-mod 源码**。

⇒ 要推进这条线，需要先拿到 ol-mod 仓库（或其 `src/game_server/` +
`.agents/research/`）。在没有它之前，**不要凭猜实现 booking 帧格式**
（与 SKU 页同类风险：错格式会让整条匹配链死掉且本会话不恢复）。

---

## 4. 建议的接手顺序（更新版）

```
① 靶场可玩（最短、有素材）
   a. 放 firingrange-gamestate.bin（§3.1）        ← 立即可做
   b. 跑一局，看 battle_srv.log 是否出现 RX #1 16B（DTLS init）
   c. 若握手过：核对 stats / game state / 快照是否推进

② 商城目录放量（§1.5）
   count 5 → 全量；每级都用 §1.3 的 UIException 判据

③ 首页挑战（#1010）+ 公告（#1125）
   字段名已在 CLIENT_OBJECT_SCHEMA.md；缺的是 .info 语法
   → 需要 hook 客户端解析器，别再猜键名（TAKEOVER §12.4）

④ dedicated booking 控制面（§3.2）
   前提：先拿到 ol-mod src/game_server/

⑤ 未映射服务 3/* 9/* 10/20 28/* 29/10 102/*（P3）
```

---

## 5. 本轮实机跑法（可复现）

```powershell
# ① 起提权代理（弹 UAC 必须点是）
$py=(Get-Command python).Source
Start-Process -FilePath $py -ArgumentList '-X','utf8',
  'D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\elevated_agent.py' `
  -Verb RunAs -WindowStyle Hidden
python -X utf8 "CODOLServer\_mainline\agent_client.py" ping     # 期望 ok=true

# ② 清残留
python -X utf8 "CODOLServer\_mainline\agent_client.py" run powershell -NoProfile `
  -Command "Stop-Process -Name codoMP_client_shipRetail -Force -EA SilentlyContinue"

# ③ 跑一局
python -X utf8 "CODOLServer\_mainline\agent_client.py" run python -X utf8 `
  "D:\BaiduNetdiskDownload\使命召唤OL\REF_LOBBY_KIT\run_all.py" --secs 240 --out n10_verify.txt

# ④ 判定（只读）
python -X utf8 "REF_LOBBY_KIT\check_run.py"
python -X utf8 "REF_LOBBY_KIT\_dump_uiexception_bin.py"
```

---

## 6. 关键文件速查（本轮相关）

```
REF_LOBBY_KIT\
  market_skus.py                    item 分组 SKU 页（load_item_groups / build_item_sku_page）
  enable_itemgroup_sku_test.py      一键开/关 + count
  check_run.py                      跑局后只读判定
  _dump_uiexception_bin.py          解 71/7 的完整调用链（关键判据）
  mkt_assets/item_sku_arrays.csv    item -> SKU[] 模型来源
  mkt_assets/sku_table_v2.csv       635 条干净 SKU 记录
  CLIENT_OBJECT_SCHEMA.md           客户端对象字段表 + SKUObj/ProductObj 字段
  battle_server.py                  战斗服 UDP（靶场协议已全实现）
  firingrange-gamestate.bin         ★ 缺 —— 靶场路线必补（见 §3.1）
  HANDOFF_20261007_TAKEOVER.md      上一版总入口

F:\桌面\ol\新建文件夹\
  docs\HANDOFF.md                   另一团队工作流水（3700+ 行，靶场全链路）
  evidence\firingrange-gamestate.bin 259B，靶场 game state 素材
  reference\CodolLocalBattleServer.cs 三方战斗服实现
```

---

## 7. 环境快照（2026-10-07 14:45）

* 提权代理：运行中 pid 11012（`debug_privilege=true`）
* 游戏进程：无残留（已清）
* 目录：merged 37834 条启用；库存 7619 件（472KB，在 480KB 安全预算内）
* 开关：`marketplace-skus-itemgroup.on` **开** / `count=5`；
  `mirror_predicted.on` 开；`ready_push.on` 开；
  `firingrange-booking-push.enabled` 开；`playlists-include-pve.on` 开
* 沙箱：`run_codol_001\sandbox_datafix_20260929`

---

## 8. 本轮附带修掉的一个数据事故（值得记住）

`_analyze_item_sku_arrays.py` 是**覆盖写** `mkt_assets/item_sku_arrays.csv` 的。
本轮在一份"**没打开过商城**"的新线性转储
（`mem_linear_20261007_134406`，2218 区 / 1.39GB）上跑了一次，
只解出 **128 个 item**，5 个 ground-truth item **全丢** —— 可信表被写坏。

处置：

1. 用**旧的已验证转储**（`mem_linear\r_259D0000_06400000.bin`，手册要求勿删）
   重跑，恢复成 **572 item / 1609 行**，5/5 ground-truth 全部回来；
2. 给脚本加了**写出护栏**：ground-truth 自检不通过就**拒绝写出**
   （返回码 2，旧表保持原样），并在输出里说明原因和补救办法。
   已实测：对那份弱转储跑 → 5/5 不命中 → 拒绝写出 → 表完好。

> 教训：**任何覆盖写"可信数据表"的脚本都必须先做 ground-truth 自检**。
> 这与 §1.5 的"单条验证"纪律同源 —— 没有对照就不能改数据。
