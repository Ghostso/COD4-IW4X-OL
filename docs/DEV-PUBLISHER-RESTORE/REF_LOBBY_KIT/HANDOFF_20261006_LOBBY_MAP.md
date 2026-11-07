# 大厅协议专项排查 —— 2026-10-06

> 方向变更: 不再逐个追商品, 改为**系统排查大厅协议**。
> 工具: `_lobby_task_matrix.py`(全量矩阵) + `lobby_task_matrix.csv`。

## 0. 一句话

大厅里客户端一共发了 **43 个 service/task 组合**, 其中 **21 个我们完全没映射**。
"商城空 / 军火箱页面重叠 / 游玩清单空 / 背包副武器近战买不了" 不是孤立 bug,
而是几个**根因应答缺失**的连锁反应。首恶是 **80/70 目录页回空**。

## 1. 大厅请求矩阵(2026-10-06 实机一轮)

### 1.1 商城 / 目录 —— ★ 最大根因

| service/task | 次数 | 我们的应答 | 说明 |
|---|---|---|---|
| 80/70  | 1 | **空页** | 目录主页(页1/2000/version=1625160) |
| 80/107 | 1 | **空页** | 目录另一视图 |
| 80/119 | 1 | **空页** | 带筛选 id 0x6CA62CD7 |
| 80/173 | 2 | **空页** | 小查询 |
| 80/174 | 1 | **空页** | 单页查询 |
| 80/232 | 2 | **空页** | 无参查询 |
| 80/203 | 1 | 库存 7612 件 | OK |
| 80/230 | 2 | 玩家资产 365419B | OK |
| 80/130, 93/1 | 4 | 余额 | OK |
| 80/131, 80/154 | 1 | 购买 | OK(但有货币/Item 编号问题) |

请求参数已逐个解出:

| task | payload(TLV 解码) |
|---|---|
| 70  | `"", 1, 2000, true, 0, 0, "1625160"` |
| 107 | `"", 1, 2000, "1625160"` |
| 119 | `"", 1, 1000, 0x6CA62CD7, 0` |
| 174 | `"", 1, 700` |
| 173 | `"", u16(700)` |
| 232 | `""` |

**影响链**: 空目录页 -> `MarketScrollGrid.as:145` 数据源为 null ->
`TypeError #1009` -> 商城空白; `SupplyDropView.as:202`(军火箱)构造中断 ->
页面栈没正常收尾 -> **退出页面与大厅重叠**。

### 1.2 玩家档案 / 库存

| service/task | 应答 | 说明 |
|---|---|---|
| 8/1 | public.result 33428B | OK |
| 8/2 | secure.result 32983B | OK |
| 8/3 | 保存上传档案 33428B | OK(本轮新增) |

### 1.3 游玩清单 / 房间

| service/task | 应答 | 说明 |
|---|---|---|
| 10/21 | publisher `mp_playlists_shipRetail_1.0.0.info` | 内容只有 1 条占位 |
| 10/12 | user_file `the.json` | OK |
| 10/20 | **UNMAPPED** | 用户文件列表? |
| 11/4 | setRoomData 空应答 | 靶场用 |
| 11/13 | createRoom roomId | OK |
| 21/5 | findSessions 靶场 session | OK |

### 1.4 未映射(21 个)

| 分组 | service/task | 推断功能 |
|---|---|---|
| 生涯/结算 | 3/46, 3/48, 3/53 | 战后结算、生涯数据 |
| 好友/社交 | 9/5, 9/14 | 好友列表、在线状态 |
| 用户文件 | 10/20 | 文件列表 |
| 房间 | 12/6 | 房间附加 |
| 任务参数 | 28/1, 28/4 | 任务参数 |
| ? | 29/10 | ? |
| 遥测 | 68/3, 68/8 | 埋点(可忽略) |
| 客户端日志 | 71/3,4,7,10,13,18 | UIException/ClientLogin 上报(可忽略) |
| ? | 102/1,5,7 | ? |
| 未解密 | 49/83 | 密钥未对上 |

## 2. 排查优先级(按影响面)

```
P0  80/70 目录页格式      -> 商城空 + 军火箱重叠 + 大部分买不了
P1  4/5 背包 / 副武器 / 近战 -> 购买链路 + 档案/解锁位
P2  10/21 游玩清单真实数据 -> 游玩清单
P3  9/* 好友, 3/* 生涯, 28/* 等未映射 -> 功能性补全
P4  71/* UIException     -> 反过来当"客户端自报故障"用
```

## 3. P0 的难点与正确做法

### 3.1 为什么不能靠猜

2026-10-05 曾自编 3 条 SKU 发 80/70: 客户端整个 marketplace 服务死掉
(仓库/商城全红叹号、角色被锁)。结论: **字段集/顺序/外层封装任一错都会死**。

### 3.2 已知的"客户端字段表"(来自内存 AS3 元数据)

`_sku_schema_as.py` 给出 SKUObj 的字段与 pos:

```
name(130) id(156) promoSkuId(177) cp(206) cc(238) duration(269)
stackable(296) productId(329) requirementLevel(357) requirementPrestige(392)
requirementUnlockFlag(430) purchasable(474) originalPrice(516) price(548)
currency(572) couponEnable(602) ignoreEntitlement(637) indexInProduct(678)
ignoreDiscount(713)
```

但 `pos` 是 AS3 槽位号, **不是线格式字段号**。线格式是
"类型标签 + 值"序列(0x08 u32 / 0x10 string / 0x13 blob …)。

### 3.3 唯一稳妥路径

**逆客户端对 80/70 应答的解析器**, 而不是继续猜:

1. 定位 service=80 task=70 的**原生 handler**(大厅处理器段
   `n10*_exe_lobby.bin` @0x00BA2000 或 TenProxy 反推点)。
2. 看它按什么顺序读哪些 tag、构造哪个对象。
3. 用已知能工作的对象(`inventory_object` / `balance_object`)做编码参照,
   先只发 **1 条最小 SKU**, 准备好随时回滚。

> 备选: hook 客户端 Scaleform 侧的 `MarketScrollGrid` 数据 setter
> (AS3), 直接看它期望的对象形状。但原生 handler 更直接。

## 4. 本轮新增文件

| 文件 | 说明 |
|---|---|
| `_lobby_task_matrix.py` | 大厅 service/task 全量统计 |
| `lobby_task_matrix.csv` | 上表的 CSV 版 |
| `HANDOFF_20261006_LOBBY_MAP.md` | 本文 |

## 5. 下一步动作

先做 P0: 找 80/70 的原生解析器。具体从
`n10buy6_exe_lobby.bin` / `tp_runtime.bin` 的 handler 表入手,
对照已能工作的 80/203(库存) 与 80/130(余额) 的解析路径,
反推 80/70 期望的字段序列。

## 6. ★ 客户端自己报的故障图(71/7 UIException 解码)

`lobby_tasks.bin` 里 71/7 的正文是 **base64**, 解出来就是大厅各界面的
崩溃调用链。2026-10-06 晚一轮得到 4 条(去重后):

| 异常 | 调用链 | 对应功能 | 缺的服务端数据 |
|---|---|---|---|
| `TypeError #1009` | `MarketScrollGrid.as:145` -> MarketplaceView / SupplyDropView | 商城空白 + **军火箱页面重叠** | 80/70 目录页 |
| `TypeError #1009` | `MatchMakingStripView.as:343` -> `MatchMakingStripView.as:152` -> `DataManager.as:296/333/218` -> `LobbyController.as:1236/1262` | **游玩清单空 / 匹配条** | 10/21 游玩清单 |
| `TypeError #1010` | `OnboardingChallengesChecklistListItem.as:127` -> `OnboardingChallengeChecklist.as:91` -> `HomeView.as:271/101` | 首页挑战清单 | 挑战数据(未定位) |
| `RangeError #1125` | `FilterCategoryButton.as:215/247` -> `MOTDNotificationsPopup.as:464/131` | 公告/筛选弹层 | MOTD / broadcast 数据 |

### 解码脚本

日志里的 payload 会被截断, **必须用 `lobby_tasks.bin`**(全量):

```python
# 记录格式: svc(1B) task(1B) len(u32 LE) payload(len)
# 71/7 的 payload 里含 base64 文本, base64 解码后即异常的完整调用链
```

已写入 `_dump_uiexception_bin.py`(见下节)。

### 由此得到的"大厅功能 -> 数据源"对照

```
商城 / 军火箱重叠   <- 80/70,107,119,173,174,232 目录页
游玩清单 / 匹配条   <- 10/21 publisher mp_playlists_*.info
首页挑战清单        <- 挑战数据(待定位 service/task)
公告 / 筛选弹层     <- MOTD / broadcast
4/5 背包 / 副武器 / 近战 <- 购买(93/131,80/154) + 档案/解锁
```

## 7. ★★ 大厅大修方案(取代逐个打补丁)

### 7.1 审计结果(`_lobby_data_audit.py`)

```
publisher 文件 10 个, 其中占位/缺失 4 个:
  daily_challenge_config.info  zlib 60B  占位  -> 首页挑战 #1010
  MOTD.info                    text 29B  占位  -> 公告弹层 #1125
  activities_v1.info           text 30B  占位  -> 活动
  whitelist_tester.info        text 30B  占位  -> 白名单(可能无害)

商城目录页 80/70,107,119,173,174,232  空应答
  -> 商城空白 + 军火箱页面重叠 + 大量买不了 (最恶)

未映射服务 21 个:
  3/46,48,53(生涯) 9/5,9/14(好友) 10/20(文件)
  28/1,4 29/10(任务参数) 102/1,5,7(未知)
  68/*,71/*(遥测/日志, 可忽略)
```

### 7.2 ★ `.info` 是 INI 格式 —— 解析器键已从 exe 取出

`codoMP_client_shipRetail.exe @0x6A9E00` 附近是这些配置文件的解析键表:

```
[%s]            <- section
%s=%s           <- key=value
update / Market / onetimefetch / interval
starttime / endtime / userid / Whitelist / Spectator / tags
num / timestamps / ids / pinnedChallenges
uiclickcount / TLog / uiclick / uipage / uipage_limit / uilastpages
```

已验证的同类文件:

```
market-down.info  = [Market] update=0 onetimefetch=0 interval=0
tlogconfig.info   = [TLog] uiclickcount=0 ...
```

=> **MOTD / broadcast / activities / configs_s 都是 INI 文本**, 可以
按这些键直接编写, 不用逆二进制。

### 7.3 三层数据模型(大修顺序)

```
第 1 层 文本/INI (.info)          <- 格式已知, 直接重写
    mp_playlists(mp_playlists_*.info)   已重建 version=796 + 6 模式
    MOTD.info / broadcast.info          待按 INI schema 编写
    daily_challenge_config.info         待按 INI schema 编写
    activities_v1.info / configs_s.info 待补

第 2 层 结构化二进制(商城目录)     <- 必须逆客户端解析器
    80/70,107,119,173,174,232 -> SKUObj 列表
    已有线索: SKUObj 字段表(_sku_schema_as.py, 19 个字段)
    正确做法: 逆 80/70 的原生 handler, 别猜(猜错过一次, 打挂整个商城)

第 3 层 未映射服务                 <- 逐个体检
    3/*(生涯/结算) 9/*(好友) 28/*,29/*(任务) 102/*
```

### 7.4 关键结论: 为什么之前"一处一处修"没用

* 商城目录空 -> 商城 + 军火箱 两处崩; 目录页格式错 -> 整个 marketplace
  服务死(2026-10-05 实测)。
* 游玩清单文件 version 错 -> MatchMakingStripView 崩; version 796 后
  崩溃消失, 但模式名/地图名不对 -> 列表仍空。
* 挑战/公告数据空 -> HomeView / MOTD 弹层各自崩。
* 这些**互相独立**, 只修一处当然不行 —— 必须按上面的三层一起补齐。

### 7.5 立即要做的三件事

1. 按 exe 键表重写 `MOTD.info` / `broadcast.info` /
   `daily_challenge_config.info` / `activities_v1.info`, 消除 #1125/#1010。
2. 用内存注册表的权威地图名 + `OBJECTIVES_*` 模式名, 继续校准
   `mp_playlists`, 让游玩清单真正出条目。
3. 逆 80/70 原生 handler, 拿到 SKUObj 的线格式, 一次修好商城+军火箱+购买。

## 8. 第 2 层实测结果(2026-10-06 深夜)

### 8.1 哨兵探针

实现 `market_sku_probe.py` + `_scan_probe_sentinels.py`:
往 80/70 应答里填唯一值(name="PROBE0" id=0x11111111 productId=0x22222222
price=0x44444444 currency=0x55), 客户端解析后扫内存找这些值。

* 变体 1(类型正确: String=10 int=07 Boolean=01 currency=u8=03)发出后,
  内存里出现 32 处哨兵(id/productId/price/originalPrice)。
* **但用户实机: 商城/仓库变灰、角色被锁** —— 正是文档警告的灾难性失败。
* 协议层没死: 客户端之后仍正常发 80/203/80/230/93/131, 甚至完成购买、
  拿到 7614 件库存。说明锁是 **marketplace UI 子系统的解析死锁**,
  不是网络层。

**结论**: 哨兵出现在内存 ≠ 解析成功(很可能是原始帧缓冲拷贝)。
"类型标签对了就够了"是错的。外层封装大概率没问题(否则协议层会断),
错在 **SKU 对象的字段序列**。

**已回滚**: `marketplace-skus.on` / `marketplace-skus-allow-unsafe.on` /
`market-sku-probe.on` 全部停用, 恢复安全空页。重启游戏即恢复。

### 8.2 分派链(静态)

```
exe 0xBA3710   0x85 帧处理器: 读 4B 长度 + 16B IV, 解密后处理
exe 0xBA3A05   call [[edi+0x608]] + 0x0C   <- provider vtable 分派
TenProxy vtable 0x128305D0 槽 0x0C = 0x1281137F -> jmp 0x12817980
0x12817980     TenProxy 包装函数, 再走 [edx+0x18] 虚调用
```

**真正的 service/task 解析器在 TenProxy 之后的游戏后端模块里**,
不在已 dump 的 `tp_runtime.bin`(167936B) 覆盖范围内。

### 8.3 下一步(只读, 不再发可疑数据)

1. 运行时读 provider 对象 `[conn+0x608]` 及其 vtable/被调地址
   (用 nt10 早期句柄, 只读)。
2. dump 被调函数所在的模块区间, 找到 service=80 的解析器。
3. 从解析器读出 SKUObj 的字段读取序列, 再编码。
