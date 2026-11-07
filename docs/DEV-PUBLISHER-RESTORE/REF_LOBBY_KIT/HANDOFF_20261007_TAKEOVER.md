# CODOL 离线复活项目 —— 交接手册（2026-10-07）

> 本文是**总入口**。之前 6 篇 `HANDOFF_20261006_*` 是证据底稿，
> 结论以本文 + `HANDOFF_20261006_LOBBY_MAP.md` / `_MERGED_CATALOG.md` 为准。

---

## 0. 项目是什么

把腾讯已停服的《使命召唤 Online》(CODOL, Build 1649370) 跑成**本地离线私服**：
本地假认证 + 假大厅 + 假战斗服，客户端能登录、进大厅、进对局。

现状：**能登录、能进大厅**；大厅里一部分交互可用，其余仍是空的或会崩。

| 路径 | 值 |
|---|---|
| 工作区 | `D:\BaiduNetdiskDownload\使命召唤OL` |
| 服务端套件 | `REF_LOBBY_KIT\`（核心都在这里） |
| 游戏沙箱 | `run_codol_001\sandbox_datafix_20260929\` |
| 完整游戏副本 | `COD OL\`（含 974 个 IIPS `.ifs` 包） |
| 提权代理 | `CODOLServer\_mainline\elevated_agent.py` + `agent_client.py` |

---

## 1. 一分钟接手：怎么跑

```powershell
# ① 起提权代理（会弹 UAC，必须点“是”）
$py=(Get-Command python).Source
Start-Process -FilePath $py -ArgumentList '-X','utf8',
  'D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\elevated_agent.py' `
  -Verb RunAs -WindowStyle Hidden
python -X utf8 "CODOLServer\_mainline\agent_client.py" ping     # 应返回 ok=true

# ② 跑一局（起 auth + 大厅 + 战斗服，再拉起游戏并注入）
python -X utf8 "CODOLServer\_mainline\agent_client.py" run python -X utf8 `
  "D:\BaiduNetdiskDownload\使命召唤OL\REF_LOBBY_KIT\run_all.py" --secs 300 --out n10.txt

# ③ 杀残留游戏（ACE 保护，必须走提权代理）
python -X utf8 "CODOLServer\_mainline\agent_client.py" run powershell -NoProfile `
  -Command 'Stop-Process -Name codoMP_client_shipRetail -Force -EA SilentlyContinue'
```

**服务布局**

| 角色 | 地址 | 文件 |
|---|---|---|
| 假认证 (TLS) | 127.0.0.1:3074 | `fake_auth_tls.py` |
| 假大厅 (明文) | 127.0.0.2:3074 | `lobby_server.py` |
| 战斗服 (UDP) | 0.0.0.0:28960 | `battle_server.py` |

> `run_all.py` 会改 hosts（`formal-zone-auth` / `formal-zone-lsg` → 127.0.0.x）、
> 写 `dwauth.ini`、生成本地证书，然后调 `nt10.py` 注入。

---

## 2. 已经能用的（回归基线）

| 功能 | 走哪条 | 状态 |
|---|---|---|
| 登录 → 进大厅 | 0x81/0x83/0x85 + 4 个内存兼容补丁 | ✅ |
| 玩家档案 | 8/1 public.result、8/2 secure.result、**8/3 上传保存** | ✅ |
| 库存 | 80/203（当前 7614 件，~472KB） | ✅ |
| 玩家资产 | 80/230 | ✅ |
| 余额 | 80/130(CP)、93/1(GP) | ✅ |
| 购买 | 93/131、80/154 | ✅ 武器可买、真实扣款入库 |
| 靶场会话 | 21/5 mission session、21/1 createSession、11/13 createRoom、6/14 mmbook、11/4 setRoomData | ✅ 协议层通 |

购买实测（2026-10-06）：`25324→Item2135 扣2680GP`、`27000→Item2137 扣380GP`，
库存 7611→7612，客户端配装里能看到。

---

## 3. 目录 / 库存 / 开关（当前值）

```
目录
  marketplace-catalog.json          37615  exe 反射(原始)
  marketplace-catalog-client.json   37615  同上(客户端开关版)
  marketplace-catalog-full.json     38424  运行时内存采集版
  marketplace-catalog-merged.json   37793  ← 当前启用(见下)

库存
  marketplace-inventory.json         7614  ← 当前
  .bak_big / .bak_full              17372  全量赠送备份
  .bak_before_allitems_*                7  最早的小仓库

开关(开)
  marketplace-catalog-merged.on      合并目录(优先级最高)
  marketplace-catalog-client.on      客户端目录(被 merged 覆盖)
  marketplace-currency-lenient.on    SKU 货币以客户端请求为准
  mirror_predicted.on                战斗服镜像预测
  ready_push.on                      大厅就绪推送
  sku-live.on                        内存 SKU 采集

开关(关/实验失败已停)
  marketplace-skus.on.rolled_back_20261006
  marketplace-skus-allow-unsafe.on.rolled_back_20261006
  market-sku-probe.on.tested_ok
  provider-dump.on.done
  public-tail-inject.on.rejected_20261006
  market-tables.on.paused_20261006
```

**回滚目录**：删 `marketplace-catalog-merged.on` 即可退回原目录。
**回滚 SKU 实验**：三个 `*.rolled_back/.tested_ok/.rejected` 已经都是关闭态。

---

## 4. 协议与关键机制（接手必读）

### 4.1 大厅帧

```
0x81  服务端 hello ack (26B)
0x82  客户端 stage1 (153B)  -> 取 ticket -> 会话密钥
0x83  挑战 nonce (14B)
0x85  任务/推送帧: seq + IV(16) + AES-CBC 密文 + HMAC-SHA1 前 8B
```

会话密钥来源：`nt10.py` 在客户端 KDF 函数 `0x00BA0D20` 挂 trampoline，
把派生结果写 `secrets_kdf.txt` / `kdf_sessions.txt`；`lobby_server.py` 按 HMAC 试解挑正确那组。

### 4.2 对象编码 = “类型标签 + 值”

```
0x01 bool   0x03 u8    0x06 u16   0x07 i32   0x08 u32
0x09 i64    0x0A u64   0x10 string(0 结尾)   0x13 blob(08 <u32 len> data)
```

★ **客户端逐值检查类型**：该用 i32(0x07) 写成 u32(0x08) 会被拒
（`codol_crypto.py:260-261` 有实证）。编对象必须逐字段对类型，不能“差不多”。

列表应答的封装（80/203 已验证可用）：`08 <count>` + 各对象原始字节。
实现在 `codol_crypto.build_task_reply_objects()`。

### 4.3 已知可用的对象模板

* 钱包：`03 <currency u8> 08 <amount u32>`（7B）
* 库存项：62B，见 `marketplace_store.inventory_object()`
* 玩家资产：`marketplace_player_data()`
* 靶场 session：`codol_crypto.build_mission_session_object()`

---

## 5. 未解决的问题（大修清单）

### ★ P0 商城目录页（80/70,107,119,173,174,232 全部回空）

**后果**：商城空白 + **军火箱页面重叠**（`SupplyDropView` 构造中断）+ 大量商品买不了。

**已知**

* 请求参数（实测）：
  `80/70 = "",1,2000,true,0,0,"1625160"`；`80/107/119/173/174/232` 类似。
* 客户端异常：`MarketScrollGrid.as:145 TypeError #1009`（数据源为 null）。
* 客户端真实数据源是 6 张 coMarketplace CSV + `mp/marketplace.json` 清单
  （version=1625160，MD5 见 `mkt_assets/marketplace.client.json`）。
* **这 6 张表拿不到**：
  - 974 个 `.ifs` / 146 万条 zlib 流按 MD5 扫 → 0/6；
  - 运行时全内存（约 3380 区 / 12.7 万 zlib 流，解压态+压缩态）扫 → 0/6；
  - `common_marketplace_lite.ff` 层二（`IWffs100`）静态不可解；
  - `.tvm0` 不是明文数据段（运行时与磁盘 99.94% 相同）。
  结论：客户端解析 CSV 后不保留原始字节。
* 自己编 SKU 页**已经把整个 marketplace 打挂过两次**（商城/仓库变灰、角色锁死）。

**当前做法/教训**

* 已把 SKU 页开关全部停用（回安全空页）。
* 哨兵探针（`market_sku_probe.py` + `_scan_probe_sentinels.py`）证明：
  客户端**能读到**我们发的值（内存出现 32 处哨兵），但**仍会锁 UI** →
  说明错在 SKU 对象的**字段序列**，不是外层封装、也不只是类型标签。
* 只读 dump 已打通分派链（见 §6），下一步应顺着调用链找到读 SKU 字段的函数。

### ★ P0 剧情任务进不去（战斗服收包=0）

**现象**：PvE 游玩清单里能列出剧情任务 → 点击 → 客户端显示“战斗开始” →
**战斗服一个 UDP 包都没收到**，约 2 分钟后断开重连。

**已排查**

* 大厅侧流程全跑通：`21/5` → `21/1 createSession` → `11/13 createRoom` →
  `6/14 mmbook accepted` → 靶场 booking 推送 → `11/4 setRoomData`。
* session 地址填的是 127.0.0.1:28960（正确），战斗服已改绑 `0.0.0.0`。
* 已把 `21/5` 请求里的第 3 个 u32 回填进 session 的 Playlist 字段，仍无效。
* netstat：游戏进程开了 9 个 UDP 端口，**没有任何一个连向 28960**。

**实测 21/5 请求 payload（剧情任务）**

```
08 01 00 00 00 | 08 00 00 00 00 | 08 0a 00 00 00 |
07 ab ad 92 d6 | 6b 08 04 00 00 00 01 00 00 00 00 00 00 00 00
解析: u32=1, u32=0, u32=10, i32=0xD692ADAB, 然后 tag 0x6B + ...
```

**2026-10-07 接手进展（已实机验证）**

1. **`21/5` 已按所选 PvE 任务回正确 session**
   - 客户端请求实测：`08 01 | 08 00 | 08 0a | 07 <i32>` → `playlist=10`。
   - 客户端随后 `6/14` 的完整 `mmstart` 明文为：

     ```
     mmstart sv_resetServer; 2486 1; 3265 1; 2489 0; 2574 0; 2500 0;
     g_gametype coop; g_difficulty 0; ; map coop_training_mp_cargoship;
     2654 M7-E8S6Client; roomChatChannelID 1234605616436508552;
     ```

   - 修复：`lobby_server.py` 中 `PVE_PLAYLIST_IDS = {10}`，对 `playlist=10`
     改走 `build_mission_session_object(False, playlist=10)`，即
     `map=coop_training_mp_cargoship / GameType=0x1000003 / MaxPlayers=4`
     （不再回 `mp_firingrange / 0x1000007`）。
   - 实机日志确认：`findSessions -> ★ PvE coop mission session 对象`
     （237B，`21/5` 应答 306B）。

2. **`11/4` ready → game start 已接线**
   - 客户端 PvE ready 批次为 21B，`plain[11] == 0x15`，不是旧的 16B
     `ROOM_READY_BATCH`。参考 C# `CodolLocalLobbyServer.cs:1416` 的判据正是
     `pushData[11] == 0x15`。
   - 修复：`has_ready` 同时接受 16B 常量与 `plain[11] == 0x15`。
   - 实机日志确认：`0B/4 setRoomData ... ★就是那条 16B ready 批次 ... 已回显频道推送+game start`，
     并实际发出 `seq=59` 的 `game start` 推送（242B body=190）。

3. **剩余阻塞（尚未解决）**
   - 即使 `game start` 已发出，客户端仍停在“战斗开始”转圈；
   - `battle_srv.log` 仍为 `收包=0`；
   - `n10pve_fix3.txt` 的 `sendto` 记录里**没有** 28960；
   - 客户端网络进程（实际 PID 5480）只有本地 UDP 端口（22011/52840/…），
     没有到 28960 的 connected/remote UDP。

4. **67B 地址块对照实验（已否证）**
   - 假设：PvE 的 24B “normal” 地址块是三方作者的 best-effort，
     客户端 reader `0xB95C50` 可能始终要求 67B。
   - 实现：`pve-address67.on` 开关；开启后 PvE session 变成
     **280B（67B 地址块 + coop map/gametype）**，实测日志：

     ```
     findSessions -> ★ PvE coop mission session 对象
     (单条, 280 字节, map=coop_training_mp_cargoship
      GameType=0x1000003 MaxPlayers=4 playlist=10)
     ```

   - 结果：客户端仍停在“战斗开始”，`battle_srv.log` 仍 `收包=0`，
     `sendto` 仍无 28960。→ **地址块长度不是根因。**

5. **★ 深度剖析结论：大厅本来就不负责“开局”**
   - 参考项目 `F:\桌面\ol\新建文件夹\docs\HANDOFF.md` §13.9 已明确记录：
     - 三方那份 `gameStartData` 是**靶场抓包常量**，且其 `lsg.log` 里
       根本没有 `service=11`，自定义房间/剧情路径**从未被三方验证**；
     - ol-mod 的 `Servers.cpp:340-365` 里，`RoomEvent::Ready` 走
       `sharedRoomClient_.setReady(...)`；
     - `mmbook/mmstart` 走 `sharedRoomClient_.setReady(...)` +
       `bookingDispatcher_.submit(...)`；
     - `sharedRoomClient_.connect(...)` 连的是
       **独立的 DedicatedControl / client bridge 端口**，不是大厅 3074，
       也不是战斗服 28960。
   - 因此当前 PvE 卡点的真正含义是：

     ```
     大厅 3074: 21/5 / 6/14 / 11/4 全部已响应
        ↓
     sharedRoomClient / DedicatedBookingDispatcher: ★ 我们从未实现
        ↓
     分配/启动战斗服 → 客户端进入加载 → 连 UDP 28960
     ```

   - 这也解释了为什么 `mmstart` 推送、`game start` 推送、67B/24B
     session 全部都不能让客户端连 28960：**缺少的是 booking/room 控制面，
     不是大厅里的某一个推送字段。**

**下一步（按优先级）**

1. **复刻 ol-mod 的 DedicatedControl / sharedRoomClient 控制面**：
   从 ol-mod `src/game_server/` 与 `.agents/research/playable_architecture.md`
   找 `configuredClientBridgePort()`、`bookingDispatcher_.submit(...)`、
   `sharedRoomClient_.connect(...)` 的端口和帧格式；
2. 在 `REF_LOBBY_KIT` 新增一个独立的 `booking_server.py`（或把
   `lobby_server.py` 转发到它），负责接收 `mmbook/mmstart`、回
   booking accepted、分配 28960 并通知 `battle_server.py`；
3. 若短期要出可玩结果，优先回到**已验证的 firingrange 路径**
   （270B / 67B / `mp_shootingrange` / `0x1000007`），先把
   battle_server 的 UDP 收包链路稳住，再扩展 PvE。

> 现有 `GAME_START_PAYLOAD` 的触发已确认可用，但 payload 本身仍是不透明
> firingrange 常量；不要把它当成 coop 已验证数据。

### P1 游玩清单（MP 部分）

* 服务端下发 `mp_playlists_shipRetail_1.0.0.info`（zlib 文本，当前 version=796，
  6 个模式、70 条权威地图，字段按 exe 的 playlists 键表补全）。
* 效果：`MatchMakingStripView #1009` 崩溃已消失；但 **MP 条目一条都不显示**。
* PvE 那条剧情任务能显示 → 说明机制本身可用，**MP 条目是内容校验不过**。
* exe 里 playlists 的字段表在 `0x6C5D14` 起（catinfo/rule/teambased/hardcore/
  displayorder/unlockflag/buildversion/levelrestricted/validtime…）。
* 最可疑：我们用的 `gametype` 内部名（war/dm/dom/hp/tag/sr）是**猜的**。
  需要从客户端的 gametype 注册表取真实内部名。

### P1 名片 / 称号无法拥有

* 服务端购买链路没问题（能扣款、能入库、`Priority` 把它们排在 203 应答最前）。
* 客户端仍显示未拥有 → 名片的拥有/装备判定**不走 marketplace inventory**。
* 已试过：把 itemID 注入 `public.result` 尾部 125 个 0x07 槽 → **无效**（已回滚）。
* 客户端对象：`codo.objects.CallSignObj`（cardTitleItemID / cardIconItemID /
  cardBackgroundItemID / cardNameplateItemID…）；接口 `AS_GetMOTDMessages` 系列同类。
* 需要逆 `IsMarketplaceItemOwned` / `WL_FillInInventoryProductItems` 或名片专用表。

### P2 公告 / 挑战（客户端已自报崩溃）

用 `_dump_uiexception_bin.py` 解 71/7 得到的当前异常（2026-10-06/07）：

```
TypeError #1010  OnboardingChallengesChecklistListItem.as:127 → HomeView   (每日挑战)
RangeError #1125 FilterCategoryButton.as:215 → MOTDNotificationsPopup     (公告)
TypeError #1009  MarketScrollGrid.as:145 → MarketplaceView                (商城空)
```

对应服务端下发文件：

| 文件 | 现状 | 影响 |
|---|---|---|
| `daily_challenge_config.info` | zlib 占位注释 | 首页挑战 #1010 |
| `MOTD.info` | text 占位注释 | 公告 #1125 |
| `broadcast.info` | `{}` | 公告 |
| `activities_v1.info` | text 占位注释 | 活动 |
| `whitelist_tester.info` | text 占位注释 | 白名单(可能无害) |

已挖到的键（exe）：
* 挑战：`daily_begin / daily_end / daily_id / daily_once / challenge_version /
  challenges / challenge_%d / daily_reward`，表 `mp/dailyChallengesTable.csv` 等（客户端自带）。
* 配置类：`[%s]`、`%s=%s`、`update / Market / onetimefetch / interval /
  starttime / endtime / userid / Whitelist / Spectator / tags`。

**注意**：`market-down.info`（`[Market] update=0 …`）与 `tlogconfig.info`
（`[TLog] …`）说明这些 `.info` 是 **INI 文本**，写明文再 zlib 压缩即可。

### P3 未映射服务（21 个）

`3/46,48,53`(生涯/结算) `9/5,9/14`(好友) `10/20`(文件) `12/6` `28/1,4` `29/10`
`102/1,5,7`。`68/*`、`71/*` 是遥测/客户端日志，可忽略（也可当“客户端自报故障”用）。

---

## 6. 只读跟踪工具链（本轮新增，可直接复用）

### 6.1 大厅协议矩阵

```
python _lobby_task_matrix.py lobby_srv.log lobby_task_matrix.csv
```
→ 列出客户端发的全部 service/task、次数、payload 长度、我们的应答。
2026-10-06 实测：43 个组合，其中 21 个 UNMAPPED。

### 6.2 数据源审计

```
python _lobby_data_audit.py
```
→ publisher 文件编码/占位状态 + service/task 归属。

### 6.3 客户端异常解码（关键！）

```
python _dump_uiexception_bin.py            # 从 lobby_tasks.bin 解 71/7 的完整调用链
```
日志里的 payload 会被截断，**必须用 `lobby_tasks.bin`**。

### 6.4 只读 provider dump（打通了分派链）

```
New-Item REF_LOBBY_KIT\provider-dump.on     # 打开
# 跑一局；结果在 REF_LOBBY_KIT\provider_dump\
```

链路（实测）：

```
连接对象 obj = [[0x08269774] + 0x4F4]
  [obj+0x608] = provider = 0x39F25CA0 (每次运行不同)
  provider vtable = 0x00D95520
  vtable+0x0C = 0x00C73C10   ← exe 后端的薄封装(转数组/向量读取助手 0xC78360/0xC78390)
```

dump 出 `prov_*` / `vt_*` / `handler_*` 三个文件，`handler_*` 是 144KB 解密后端代码。
**下一跳还没到 SKU 字段级**，需要继续沿调用链往下 dump。

### 6.5 其它现成工具

| 脚本 | 用途 |
|---|---|
| `_scan_probe_sentinels.py` | 扫 80/70 探针哨兵（在线/离线） |
| `market_sku_probe.py` | 生成哨兵 SKU 对象（4 个变体） |
| `market_skus.py` | SKU 页编码（已改为类型正确版） |
| `_build_playlists.py` | 生成 playlists（version 796 + 权威地图） |
| `_build_merged_catalog.py` | 生成合并目录 |
| `_verify_merged_purchase.py` | 临时副本上验证购买 |
| `_scan_market_tables_live.py` | 运行时/离线按 MD5 找 6 张商城表 |
| `_extract_gfx_from_mem.py` | 从内存提 Scaleform SWF（未成功，内存影片不完整） |
| `secrets_kdf.txt` / `kdf_sessions.txt` | 每局会话密钥（大厅/战斗服共用） |

---

## 7. 硬约束与纪律（踩过的坑）

1. **不要猜二进制对象格式。**
   猜 SKU 页 → 商城/仓库全灰、角色锁死，已发生两次（每次只影响当前会话，重启客户端恢复）。
   任何“服务端主动发结构化对象”的实验都必须：开关控制 + 只发 1 条 + 随时回滚。
2. **ACE/TP3 保护**：后开的 `OpenProcess` 的 `VirtualQueryEx` 会被拒（err=5）。
   必须用 `nt10.py` 启动早期拿到的句柄。所以内存扫描要挂在 nt10 里。
3. **提权代理**：所有需要读游戏内存/杀游戏的操作都要走 `agent_client.py`。
   杀进程时注意：用命令行匹配 `run_all.py|nt10.py|...` 会**把 agent_client 自己那条
   命令行也匹配到**（它的 argv 里含脚本名），要按 PID 精确杀。
4. **客户端会话锁**：marketplace 子系统一旦解析失败，本会话不再恢复 → 重启游戏。
5. **共享状态**：`marketplace-inventory.json` / `player-account.json` /
   `player_profiles/*` 是玩家存档，改前先备份；已有多个 `.bak_*`。
6. 用户要求：`mem_marketplace`（9.5GB+ 旧转储）与 `mem_linear` **不要删**。
7. 沙箱游戏根：`run_codol_001\sandbox_datafix_20260929`（`run_all.py` 里的 `GAME_ROOT`）。

---

## 8. 建议的接手顺序

```
① 剧情任务进不去（P0）
   - 抓客户端出站 UDP / connected socket，确认它想连哪里
   - 让 21/5 回与所选任务一致的 map/gametype（当前恒为靶场）
   - 战斗服 battle_server.py 已实现 NAT/DTLS/ECDH/数据帧，先复用

② 游玩清单 MP 条目（P1）
   - 从客户端 gametype 注册表取真实内部名（只读 dump / 内存搜）
   - 用真实名重写 _build_playlists.py 的 gametype，再验证

③ 公告 / 挑战（P1）
   - 按 exe 键表写 MOTD.info / broadcast.info / daily_challenge_config.info
   - 用 _dump_uiexception_bin.py 看 #1125 / #1010 是否消失

④ 商城目录页（P0，最难）
   - 继续只读 provider 调用链 dump，找到读 SKU 字段的函数
   - 或 hook 客户端的类型化读值器，记录字段序列
   - 拿到序列后改 market_skus._sku_obj，先发 1 条验证（带开关+回滚）

⑤ 未映射服务 3/* 9/* 28/* 102/*  （P3）
```

---

## 9. 关键路径速查

```
REF_LOBBY_KIT\
  lobby_server.py          大厅主逻辑(所有 service/task 分支)
  battle_server.py         战斗服 UDP 协议
  codol_crypto.py          帧/加密/对象编码/session 构造
  marketplace_store.py     目录/库存/购买/余额
  market_skus.py           SKU 页编码(实验)
  market_sku_probe.py      哨兵探针
  run_all.py               一键起服务 + 拉起游戏
  nt10.py                  注入/探针/内存转储/hook 基础设施
  publisher_files\         服务端下发的 .info 文件(zlib/文本)
  player_profiles\         public.result / secure.result
  marketplace-*.json       目录与库存
  provider_dump\           只读 dump 的后端代码
  mem_linear\              旧内存全量转储(勿删)
  mem_marketplace\         旧 marketplace 扫描转储(勿删)
  HANDOFF_20261007_TAKEOVER.md   ← 本文
  HANDOFF_20261006_LOBBY_MAP.md  大厅协议/大修方案(详细)
  HANDOFF_20261006_MERGED_CATALOG.md  目录合并与购买修复(详细)
```

---

## 10. 环境快照（2026-10-07 10:38）

* 提权代理：运行中（pid 11012，debug_privilege=true）
* 目录：merged 37793 条启用；库存 7614 件
* 沙箱：`run_codol_001\sandbox_datafix_20260929`
* 注意：可能仍有上一局的 `codoMP_client_shipRetail.exe` 残留，先杀干净再跑

---

## 11. 2026-10-07 续修记录（接手后本轮）

### 11.1 本轮结论（对 §5 P0「剧情任务进不去」的补充）

已确认的事实链（只读证据，全部可复现）：

1. 客户端点「剧情任务」时，`21/5` 请求第 3 个 u32 = **10**，即它把剧情任务解析成
   **`playlist=10`**；随后 `6/14 mmstart` 明确写
   `g_gametype coop; map coop_training_mp_cargoship;`。
2. 客户端**只**取我们下发的 `mp_playlists_shipRetail_1.0.0.info` 这一份游玩清单
   （`10/21`，每次开局都取；没有第二份 coop 清单文件）。
3. 但我们重建的清单里**只有 playlist 1–6（纯 MP），既没有 `gametype coop`，
   也没有 playlist 10**。旧探针版本（`*.bak_before_playlists_20261006_215009`）
   里恰恰有一条 `gametype coop` + `playlist 1`，那次剧情列表可用；
   本次重建把 playlist 1 换成 TDM 时，**顺带把 coop 弄没了**。
4. 客户端不在大厅触发「开局」这点仍成立（§5 的 ol-mod 架构结论），
   但**匹配不到 playlist 这一步在更前面** —— 清单里没有 coop/10，
   客户端的匹配就不会推进到「连战斗服」。这与 battle_server 收包=0 的现象一致。

### 11.2 本轮改动（全部可一键回滚）

| 文件 | 改动 | 回滚 |
|---|---|---|
| `_build_playlists.py` | 新增 `PVE_PLAYLISTS`（playlist 10 / `gametype coop` / coop 任务地图）+ `playlists-include-pve.on` 开关 | 删 `playlists-include-pve.on` 后重跑生成器 |
| `codol_crypto.py` | 新增 `COOP_PLAYLIST_MAP` 与 `build_mission_session_object` 的 map 回填 | 直接 revert 这两处 |
| `publisher_files/mp_playlists_shipRetail_*.info` | 重新生成为 **976 字节**（含 playlist 10），version 仍 796 | 同左；旧文件已 `*.bak_before_playlists_*` 备份 |

* 开关 **开**：`REF_LOBBY_KIT\playlists-include-pve.on`（当前状态：已创建）。
* 自测：`python -X utf8 _build_playlists.py`（关=822B/6 条，开=976B/7 条）；
  `python -X utf8 codol_crypto.py` 全部 OK；session 对象 playlist=10 → map 正确。

### 11.3 下一轮实跑判据

按 §1 起代理 + `run_all.py` 跑一局，点**剧情任务**（例如训练关），观察：

1. `lobby_srv.log`：`findSessions -> ★ PvE coop mission session 对象`（不变），
   但应同时看到 publisher 下发的 `mp_playlists_*.info` 是 **976 字节**；
2. `battle_srv.log`：应出现 **`RX #1 ... 16B`（DTLS init）**——
   这是「客户端终于连 28960」的实锤；若仍 `收包=0`，说明 playlist 对齐不是唯一门槛。
3. 若 battle_srv 开始收包：靶场那条链（§13.10–13.15 已全实现）可直接复用，
   握手 → stats → game state → 快照会依次出现。

### 11.4 仍未解决 / 未验证

* 本轮**未做实机跑**（需要 UAC 弹窗 + 拉起游戏），所以「加回 coop playlist 能否让
  客户端连 28960」**尚未验证**，只是把可复现的缺失项补上。
* 若仍不连：按 §5 的「复刻 ol-mod DedicatedControl / sharedRoomClient 控制面」推进，
  但 ol-mod 源码**不在本机**（只在 `F:\桌面\ol\新建文件夹\docs\HANDOFF.md` 有摘录），
  需要先拿到 ol-mod `src/game_server/` 与 `.agents/research/playable_architecture.md`。
* P1 游玩清单 MP 条目：已从 `mem_linear/r_259D0000_06400000.bin`
  @`0x281ad8b0` 起找到客户端的 mode 注册表
  （`@OBJECTIVES_WAR/DM/DOM/HP/TAG/SR/CHA/PH/DMZ/SPY/TD…`）。
  → 我们用的 `war/dm/dom/hp/tag/sr` **都是真实内部名**，不是猜测问题；
  MP 列表空的原因需另找（可能与 category/catinfo 或 mode→display 映射有关）。

---

## 12. 2026-10-07 续修（第二段：转回大厅，战斗服当黑箱）

用户决定：战斗服当作黑箱，先集中修大厅。下面是这段时间新挖到的**权威事实**，
以及据此调整后的大厅计划。

### 12.1 新产出的可复用资料

* **新增 `CLIENT_OBJECT_SCHEMA.md`** —— 从客户端自身 accessor
  （`mem_linear/r_259D0000_06400000.bin` 里的 `codo.objects::<Class>/<field>`）
  提取的**完整字段表**，覆盖：
  - 挑战：`OnboardingChecklistObj` / `ChallengeObj` / `DailyChallengeObj` / `WeeklyChallengeObj` …
  - 公告：`MOTDMessageObj` / `MOTDCheckinRewardObj` / `ServerMessageObj`
  - 游玩清单：`PlaylistCategoryObj` / `MatchSelectModeObj` / `QuickMatchFilterObj`
  这是客户端**自己声明它要读的字段名**，不是猜的。

### 12.2 两条重要更正（推翻旧结论）

1. **`[%s]` / `%s=%s` / `update` / `userid` / `Whitelist` 不是 `.info` 的解析键。**
   实测这两个格式串紧邻 `crypto\conf\conf_def.c` / `conf_api.c` ——
   属于 **OpenSSL 的 config 解析器**（`codoMP_client_shipRetailBase.dll` @0x77ddc8）。
   `MOTD.info` / `daily_challenge_config.info` 的**真实解析键仍未定位**，
   不要再按旧 HANDOFF §7.2 的「格式已知」去直接重写。
2. **`catinfo` / `displayorder` / `unlockflag` / `levelrestricted` /
   `maxhumanplayersperteam` 这些键，在 `mem_linear` 与 60MB 客户端 DLL 里
   **一处都搜不到**。** `mp_playlists` 解析器不按这些名字读** ——
   重建 `_build_playlists.py` 时沿用的字段名**站不住**。
   `PlaylistCategoryObj` 实际读的是 `name / entries / unlockLevelStart / locked /
   isNewUnlock / isFeatured / cycleTodayIndex`。

### 12.3 更新的**大厅**待办（按可验证性排序）

```
① 游玩清单 MP 条目（P1，目标：MatchMakingStripView #1009 消失 + 出条目）
   - 键名不在 exe/DLL, 在**打包的 Scaleform UI**（IIPS/.ff, 静态难取）
   - 唯一可靠做法: hook 客户端 `PlaylistCategoryObj` 的 setter / `MatchService`
     的 playlist 解析函数, 只读 dump 记录**它逐字段读的键名**
     （与 SKU 页同款: 开关 + 只读 + 单条验证, 严禁再猜）
   - 已做: coop playlist 10 + gametype coop 已补回（见 §11.2, 待实机验证）

② 公告 / 首页挑战（P2，目标：消除 #1125 / #1010）
   - 字段名已知（`MOTDMessageObj` / `OnboardingChecklistObj`, 见 schema 文档）
   - 缺 `.info` 文件语法 → 同样需要「hook 客户端解析器」或找到该 parser
   - 现状文件: MOTD.info = 纯注释占位; daily_challenge_config.info = zlib(纯注释)

③ 商城目录页（P0，最难）
   - 见 §5; 需要 provider 调用链继续下探到 SKU 字段级

④ 未映射服务 3/* 9/* 10/20 12/6 28/* 29/10 102/*（P3）
   - reference C# 也只覆盖了 11/21/28/6-14/80/93/9-14/10-*;
     3/* 9/5 12/6 29/10 102/* 连参考实现都没做过
```

### 12.4 ★ 纪律（本轮再次确认）

`mp_playlists` 的字段名**不是**我们以为的那套。在没有拿到客户端真实键名之前，
**不要再凭猜改 `.info` 的键名** —— 风险与 2026-10-05 那次「猜 SKU 页打挂整个
marketplace」完全相同（猜错会让 `MatchMakingStripView` 崩）。

---

## 13. 2026-10-07 续修：商品购买路径体检（含一次自我纠错）

### 13.1 结论：购买**机制**没问题，问题在**编号体系没打通**

复查链路（§2 说购买"✅", 但 `unknown_skus.txt` 里堆了 155 条失败记录）：

* `marketplace_store.parse_purchase` 已是**结构化解析**（不再逐字节模板匹配），
  各种购买帧形都能取到 SKU/数量;
* `purchase()` 的拒绝只有 4 种：SKU 不存在 / 数量非法 / 非堆叠但 qty!=1 /
  货币不符（后者已被 `marketplace-currency-lenient.on` 放宽）;
* 用**真实 inventory + player_profiles** 在临时副本上跑 `purchase()`：
  catalog 里存在的 SKU（31184 / 37251 / 31181 / 16350 / 990 / 1007 / 12329）
  **全部 OK**; 只有目录里没有的（如 19428）才报
  `Unsupported SKU/currency/quantity`。

→ 代码路径是通的; 真正缺的是**客户端购买帧 SKU → 服务端 Item 的正确映射**。

### 13.2 ★ 自我纠错：低 Item 条目**不能**并入目录（已回滚）

本轮一度把 `_build_merged_catalog.py` 的过滤从 `Item>=1000` 放宽成
`Price<9999999`, 想借此收编 964/980/982/984/986/988/995/998/1005 这 9 个
"用户点过但没有目录条目"的 SKU。**这是错的, 已完整回滚。**

为什么错（依据 `HANDOFF_20261006_CATALOG_LAYOUT.md` §3 的既有硬证据）：

* 内存记录里的 `+0x14` 是**客户端自己的 Item 编号**, 与 exe.Item / 库存 key
  **不是同一套体系** —— 交叉命中率只有 8.7%（随机基线 3.5%）;
* 那批低 Item 值（12/13/28/49/51/54/139/228/6）正是**客户端自有编号**,
  把它们当 exe.Item 写进服务端目录, 会让购买"**假成功、入错物品**";
* `_revert_to_trusted_catalog.py` 早就为此把客户端目录还原成纯 exe 反射版。

回滚动作：

* `_build_merged_catalog.py` 恢复 `Item>=MIN_ITEM(1000)` 过滤（+ 白名单 31774）;
* `marketplace-catalog-merged.json` 重新生成, 与
  `marketplace-catalog-merged.json.bak_before_sane_lowitem_20261007`
  **SHA256 完全一致**（37793 条, 无 964）。

> 教训与 §12.4 同源：**内存里"看起来对"的值, 不一定是同一套编号**。
> 没打通映射前, 宁可让购买失败, 也不能入错物品。
>
> ★ 2026-10-07 追加（见 §14）：后来用 ground-truth 反证法**成功逆出了这批记录的布局**，
> 证明它们确实是客户端真实的 SKU 记录；但**编号体系**确实与 exe 目录冲突（同号不同物）。
> 所以最终做法是：**只并入合并目录里没有的 SKU，已有的绝不覆盖**（§14.4）。
> 也就是说 §13.2 的"不能整批并入"是对的，但原因不是"记录是噪声"，
> 而是"两套编号不能混用"。

### 13.3 真正要解决的事

缺的是这条链的**最后一段**：

```
购买帧 SKU ──(客户端运行时表)──> 客户端 Item 编号 ──?──> 服务端 Item / 库存 key
exe 目录 SKU ──(exe 目录)────> exe Item 编号（= 库存 key）★ 这条已通
```

* 三种来源的 SKU 编号**0 交集**: exe 反射目录的 37615 条里, 用户点过的 105 个
  SKU **一个都不在**（见 CATALOG_LAYOUT §3.A）;
* 所以要么把这套"客户端 SKU→Item"表**完整逆出来**（需要 hook 客户端
  marketplace 解析器 / 拿到 `mp/marketplace.json` + 6 张 coMarketplace CSV）,
  要么接受"只有 exe 目录编号的商品可买"。
* 目录页（80/70）仍回空 → 商城空 + 军火箱重叠（§5 P0）。这与购买**是两件事**,
  但**根因相同**：都是拿不到/对不上客户端那份真实商品数据。

---

## 14. 2026-10-07 续修：★ 客户端 SKU 表**逆出来了**（ground-truth 反证法）

### 14.1 方法（不再用下标硬凑，先用**已知答案**反推布局）

§13.2 否证了"下标"假设后换方向：拿**已实测入库成功**的 5 个 SKU 当 ground truth——

```
37251 -> Item 29892  Price  8000  days 0    (CP)
31184 -> Item 22384  Price   680  days 7    (GP)
37116 -> Item 29767  Price 10000  days 0    (CP)
16096 -> Item  7110  Price   880  days 0    (GP)
31774 -> Item   122  Price  2280  days 30   (CP)
```

（来自 `_verify_merged_purchase.py` / HANDOFF_20261006_MERGED_CATALOG.md 的实测记录，
不是猜的。）在 `mem_linear\r_259D0000_06400000.bin` 里按 SKU 值精确定位这 5 条，
发现 Item **全部固定在 `+0x14`**、价格副本在 `+0x28`。反推出的布局：

```
+0x00 SKU     +0x04 0        +0x08 价格A(或0)   +0x0C 价格B(或0)
+0x10 天数(0=永久, 0xFFFFFFFF=永久)            +0x14 **Item**
+0x28 价格副本（== +0x08 或 +0x0C）
```

### 14.2 用同一布局全库扫（严格自洽校验）

1. `+0x04 == 0`
2. `+0x28 == +0x08` 或 `+0x28 == +0x0C`（价格副本与某一槽一致）
3. `10 <= price <= 10000000`（地板价 10，杀掉 `(item=2, price=1)` 退化命中）
4. `days <= 3650` 或 `days == 0xFFFFFFFF`
5. `1 <= item <= 60000`

同一 SKU 多候选 -> 判歧义，整条丢弃。

### 14.3 结果（`_extract_sku_table_v2.py`）

```
干净记录 635 条, 歧义 23 条
ground truth 自检: 5/5 命中     ← 脚本内置，未过就拒绝写出
输出 mkt_assets/sku_table_v2.csv
```

独立交叉验证（都不是自证）：

* 与旧 `_extract_client_catalog.py`（另一套判据）的 107 条 **完全一致 107/107**；
* 提取出的 Item 里 **216 个本身就是玩家库存 key**（买了才会拥有）；
* 5 个 ground-truth SKU 的数值与 `_verify_merged_purchase.py` 期望值**逐字段相同**。

### 14.4 已落地（开关控制，可回滚）

`_build_merged_catalog.py`：并入 sku_table_v2 里**合并目录还没有**的条目
（已有的编号体系冲突，一律**不覆盖**，仍以 exe/合并目录为准）。

| | 前 | 后 |
|---|---|---|
| merged 条目 | 37793 | **37834** |
| SKU 表补入 | 0 | **41** |

* 开关：`catalog-include-sku-table.on`（当前**开**）
* 关掉后重跑，`marketplace-catalog-merged.json` 与
  `marketplace-catalog-merged.json.bak_trusted_37793_20261007` **SHA256 一致**（已验证）。
* 真实 `purchase()`（临时副本 + 真实库存）：新增抽查
  58/98/102/120/241/242/278/992/993/1000/17280/18048/18076/19428 **全部 OK**，
  入库 Item 与记录一致、重复购买不重复扣款。

### 14.5 还剩什么

* 25 个"点过但找不到"的 SKU，本轮**找回 14 个**
  （58/98/102/120/241/242/278/992/993/1000/17280/18048/18076/19428）；
  仍缺 11 个：`48, 73, 1011, 1981, 15827, 19405, 19621, 31173, 31374, 31819, 41314`。
  多为别的表（套餐/礼包）或本快照没覆盖到的分配 —— 需**重新 dump 一次内存**
  （这次先把商城页翻一遍再 dump）再跑本脚本。
* **目录页（80/70）仍回空** —— 商城空/军火箱重叠的根源是它，不是购买。
  下一步用 `CLIENT_OBJECT_SCHEMA.md` 附 1 的 SKUObj 字段名去拿真实线格式。

---

## 15. 2026-10-07 续修：★★ 客户端 SKU 的真实结构 = **item -> [SKU 档位]**

### 15.1 发现

§14 的布局反推之后，继续沿 stride 0x60 往两边看，发现记录**不是一张大表**，
而是**每个 item 一个小数组**（数组尾用 0xFFFFFFFF 填充）。硬证据：

```
item 22384 (相邻三条, 同一数组):
    sku 39592  GP 10880  永久
    sku 31184  GP   680  7 天     ← ground truth(实测入库过)
    sku 31759  GP  2580  30 天    ← 同一 item 的另一个购买档

item 29892: sku 37251  CP 8000  永久     ← ground truth
item   122: sku 31774  CP 2280  30 天     ← ground truth
            sku    80  CP  281  240 天
```

"同一 item 多个价格/时长档"正是商店的正常形态，与 AS 侧
`itemData.skus / promoSkus / sortedSkus`（见 `_sku_schema_as.py`）完全对应。

→ **结论：客户端运行时目录的模型是 `item -> SKU[]`；目录页 80/70 下发的
  就是这串 SKU 列表。** 这解释了为什么"只补 SKU 数"不够 —— 一个 item 有多个档。

### 15.2 新工具 & 结果

`_analyze_item_sku_arrays.py`（只读，扫现成转储）：

```
记录 2067 条 -> 涉及 item 576 个, 其中多档(>=2 SKU)的 item 398 个
档位分布: 2 档 268 个 / 1 档 178 / 6 档 39 / 3 档 30 / 4 档 18 / 8 档 8 ...
输出 mkt_assets/item_sku_arrays.csv (item,sku,price,days)
```

自检：5 个 ground-truth SKU 全部**逐字段正确**。
覆盖面：手册记录过的 122 个"点过"的 SKU，**覆盖 112 个**（比 §14 的 97 个更多）。

### 15.3 下一步（等新转储）

仍缺 10 个：`48, 1011, 1981, 15827, 19405, 19621, 31173, 31374, 31819, 41314`
—— 用 `collect_after_browsing_store.py` 翻一遍商城页后重新 dump，再跑本脚本。

有了 `item -> SKU[]` 这个模型，80/70 的应答应该按 **每个 item 一组、
组内多档 SKU** 来组织（配合 `_sku_schema_as.SKU_AS_FIELDS` 的字段序），
而不是"一条 item 一个 SKU"。这会直接改写 `market_skus._sku_obj` 的用法。

### 15.4 已实现：item 分组 SKU 页（开关 + 单条验证，默认关）

| 位置 | 改动 |
|---|---|
| `market_skus.py` | 新增 `load_item_groups()` / `build_item_sku_page()`；只取**含 ground-truth SKU 的 item 组**，并剔除组内量级异常的档（如 item 122 里混进的 `sku 80`） |
| `lobby_server.py` | 80/70 分支新增 itemgroup 路径（在哨兵探针之后、旧 SKU 页之前）|
| `enable_itemgroup_sku_test.py` | 一键开/关 + 说明 |

开关：`marketplace-skus-itemgroup.on`（+ `marketplace-skus-count.txt` 控制发几个 item）。

当前可信组（5 个 item / 7 档 SKU，全部有 ground truth 支撑）：

```
item   122 -> SKU 31774  CP 2280   30 天
item  7110 -> SKU 16096  GP  880   永久
item 22384 -> SKU 39592  GP10880   永久
             SKU 31184  GP  680    7 天
             SKU 31759  GP 2580   30 天
item 29767 -> SKU 37116  CP10000   永久
item 29892 -> SKU 37251  CP 8000   永久
```

**当前状态：开关已开，count=1（只发 item 122）** —— 等实机跑一局验证：
1. 商城**不**变灰、角色**不**被锁（历史上编错会这样）；
2. `lobby_srv.log` 出现 `★ item 分组 SKU 页`；
3. 通过后把 `marketplace-skus-count.txt` 从 1 调到 5，再逐步放量。

回滚：`python -X utf8 enable_itemgroup_sku_test.py off`。

> ⚠️ 80/70 的**外层/字段序仍是假设**（无第三方参考）。历史上"自编 SKU 页"
> 打挂过两次整个 marketplace 服务，所以这一步严格"只发 ground-truth 组 + 单条起"。

### 15.5 验证闭环（已备好，等你跑一局）

```
# 1) 起服务 + 拉起游戏（主手册那套），进大厅
# 2) 确认开关（当前已开, count=1 只发 item 122）
python -X utf8 enable_itemgroup_sku_test.py          # 或 5 放量 / off 回滚
# 3) 跑完一局后, 自动判定：
python -X utf8 check_run.py
```

`check_run.py`（只读）会打印：
* 大厅日志里的正向信号（`item 分组 SKU 页` / PvE session / 靶场 session / game start）；
* UIException 里对应崩溃**还在不在**（商城空 MarketScrollGrid / 游玩清单
  MatchMakingStripView / 公告 FilterCategoryButton / 首页挑战 OnboardingChallenges）；
* 战斗服收包数。

**基线（上一局，itemgroup 尚未生效）**：
```
大厅: PvE session OK / game start OK;  item 分组 SKU 页 --（当时没开）
UI  : MarketScrollGrid 还在 / MatchMakingStripView 还在 /
      FilterCategoryButton 还在 / OnboardingChallenges 还在
战斗服: 收包=0
```
→ 跑完这一局后，重点看 `item 分组 SKU 页` 是否变成 `OK`，以及
`MarketScrollGrid` / `SupplyDrop` 有没有**新增**（新增=编错，立刻 off）。

---

## 16. 2026-10-07 续修：provider 调用链**继续下探**的准备

### 16.1 为什么上一轮的 provider dump 断掉了

复核 `provider_dump/handler_00C6FC10_147456.bin`（144KB，从内存 dump）：

* `vtable+0x0C = 0x00C73C10` 确实在这个窗口内；反汇编它发现**只是个薄封装**
  （`call 0xC78360` / `call 0xC78390`，即"转数组/向量读取助手"）；
* 它真正调用的深层函数在 **0xE3F240 / 0xB74240** 等地址 —— **不在** 144KB 窗口里；
* 这些地址在**磁盘 exe 上拿不到**：exe 的 `.tp3` #3 节 VA 巨大(0xE16000 起)
  但 RAW 只有 401KB —— **运行时解壳**才出现，所以只能从内存 dump。

→ 结论：要读 SKU 字段级解析，必须**扩大 dump 覆盖**，沿调用链往下走。

### 16.2 已改进：dump 自动沿**直接 call** 跟随

`nt10.provider_dump_thread` 现在在 dump 完 handler 后：

1. 在 handler 字节里只找 **`E8 rel32`（直接 call）**；
2. 目标必须落在 exe 的两个**真代码区间**内
   （`.tp3`#1 `0x401000..0xCA789A` / `.tp3`#2 `0xCA8000..0xE15A70`）；
3. 每个目标再 dump 一份 16KB 窗口（`provider_dump/callNN_*.bin`）。

自测（对现有 handler 离线跑同一逻辑）：目标从"全字节扫描的 4015 个假候选"
降到 **202 个可信直接调用**，且已知的真目标 `0xB74240` 在列。

用法不变：
```
New-Item REF_LOBBY_KIT\provider-dump.on      # 打开(已 .done, 需重建)
# 跑一局, 结果在 provider_dump/ (含 callNN_*.bin)
```
拿到 `call*.bin` 后，就能在链上找**逐字段读 SKU 的那个函数**，
从而确定 80/70 的 SKUObj 真实线格式（现在这一步仍是假设）。
