# 116 · `102` 定名：`Messaging2`（`0x66`）——黑箱收口

> 项目：使命召唤OL 大厅（build 1649370 / 3.19）
> 语料：`_byte_papers/corpus/corpus.json`（6848 条，639 条属 svc 102）
> 前卷：`115`（`102` 结构已解，语义名留作「未定，Leaderboard 最强候选」）
> 本卷目标：**把 `102` 的语义名从「未定」改成「定」，并给出可复核的证据分层**

---

## §0 结论（一句话）

**`102 = Messaging2`（服务号 `0x66`），四个 task 全部闭合；`Leaderboard` 候选作废。**

三条独立证据，按 AGENTS.md 权威层级排列：

| # | 证据 | 层级 | 强度 |
|---|---|---|---|
| ① | 客户端二进制里存在 **`[服务名][enabled]` 服务开关表**，`messaging` 项 `enabled=1`，且**顺序与 `configs_s.info [dw_service_info]` 逐项一致** | **本地逆向（最高）** | ★★★★★ |
| ② | 客户端 RTTI 有 **`bdMessagingGroup`** 类；`ChattingController` 绑定 **`data.messaging.status` → `DWServiceStatus`** | **本地逆向（最高）** | ★★★★ |
| ③ | ol-mod `AckOnlyServices.cpp` 逐字写明 `// Messaging2 (102). Four tasks, all periodic:`，**四个 task 载荷形态与我们语料逐字段吻合** | ol-mod（非权威，交叉参考） | ★★★★★ |

**关键：③ 单独不足以定名（ol-mod 非权威、目标是 3.3.3.3 build）。但 ③ 的载荷与本地语料 `102/1,2,5,7` 是「逐字节同一份」，加上 ①②的本地服务表把 `messaging` 钉成真实且启用的 DW 服务——三条证据指向同一个名字，闭环成立。**

---

## §1 语料侧：四个 task 的字节形态（实测）

`tools/verify_102_messaging2.py` 逐条解析（语料 639 条 102 记录）：

| task | 条数 | 不同形态 | 首条 payload（TLV 解出） |
|---|---|---|---|
| `102/1` | 172 | 2 | `u32 0, u32 1, u8 3, u64 0, term`（127 条）/ `u32 0, u32 2, (u8 1,u64 0)(u8 2,u64 0), term`（45 条） |
| `102/2` | 77 | 1 | `term`（**空**） |
| `102/5` | 19 | 1 | `u32 2, u8 1, u8 2, term` |
| `102/7` | 371 | 1 | `u32 50` + 50×`(u8 1, u64 i)`，i=0..49，`term`（共 102 字段） |

原始字节（`102/1` 主形态 22B）：
```
08 00 00 00 00   08 01 00 00 00   03 03   0a 00×8
```

原始字节（`102/7` 556B，头尾）：
```
08 32 00 00 00 | 03 01 0a 00×8 | 03 01 0a 01×8 | … | 03 01 0a 31×8 | 00
```

★ `102/7` 的 `0a` 序列 `i = 0,1,2,…,49` **严格连续、371 条 distinct=1** —— 这是**按索引 0..49 的批量查询**，不是查询结果。

---

## §2 ol-mod 侧：逐字原文（交叉参考）

`_e1_regression\ol-mod-olfinal\src\backend\Demonware\AckOnlyServices.cpp:36-44`：

```cpp
// Messaging2 (102). Four tasks, all periodic:
//   1: (u32 0, u32 1, u8 3, u64 0)
//   2: no payload at all -- the whole frame is 04000000 86 66 03 02
//   5: (u32 2, u8 1, u8 2)
//   7: (u32 50) then 50 x (u8 1, u64 i) for i in 0..49 -- a bulk query by index
AckTask{ 0x66, 1, "Messaging2::task1" },  // x13
AckTask{ 0x66, 2, "Messaging2::task2" },  // x2
AckTask{ 0x66, 5, "Messaging2::task5" },  // x7
AckTask{ 0x66, 7, "Messaging2::task7" },  // x10
```

**四行注释 vs 我们语料：逐字段同一份。**

| task | ol-mod 注释 | 我们语料 TLV | 判定 |
|---|---|---|---|
| 1 | `u32 0, u32 1, u8 3, u64 0` | `u32 0, u32 1, u8 3, u64 0` | **完全一致** |
| 2 | 无载荷（整帧 `04 00 00 00 86 66 03 02`） | 仅 `00`（term） | **一致**（declared=3 → payload 空） |
| 5 | `u32 2, u8 1, u8 2` | `u32 2, u8 1, u8 2` | **完全一致** |
| 7 | `u32 50` + 50×`(u8 1, u64 i)`，i=0..49 | `u32 50` + 50×`(u8 1,u64 i)`，i=0..49 | **完全一致** |

★ 帧头 `04 00 00 00 | 86 | 66 | 03 | 02`：`declared=4`、`marker=0x86`、`service=0x66=102`、`ver=0x03`、`task=0x02`——与 `codol_crypto.py` 的 `decrypt_task_frame` 明文格式（`u32 declared | 0x86 | service | 0x03 | task | payload(declared-3)`）**逐字节吻合**，证明 ol-mod 描述的就是我们这条线。

★★ 另一独立来源 `RecoveredCatalog.cpp` 把 `lobby 0x66` 记为 `"Unknown66"`——即 ol-mod 自己的 2019 反汇编**只捞到号、没捞到名**。名字是后来在 `AckOnlyServices.cpp` 由**载荷形态**补上的。这恰好说明：**号（0x66）与名（Messaging2）在 ol-mod 内部是两条独立路径得来的**，交叉可信度更高。

---

## §3 本地侧证据 ①：客户端二进制里的服务开关表

这是本卷**新增的、最高权威**证据。

### 3.1 表在哪

`tools/dump_svc_info_table2.py`，E 运行时镜像 `E:\codol_re\client_image_20261027.bin`（241 MB，PE32 imagebase `0x400000`），文件偏移 `0xA4E8F8` 起：

```
file0x00A4E8F8  ptr→'none'            flag=0
file0x00A4E900  ptr→'all'             flag=0
file0x00A4E908  ptr→'critical'        flag=0
file0x00A4E910  ptr→'non_critical'    flag=0
file0x00A4E918  ptr→'eventlog'        flag=0
file0x00A4E920  ptr→'friends'         flag=0
file0x00A4E928  ptr→'group'           flag=0
file0x00A4E930  ptr→'mail'            flag=0
file0x00A4E938  ptr→'marketplace'     flag=0
file0x00A4E940  ptr→'matchmaking'     flag=1
file0x00A4E948  ptr→'messaging'       flag=1   ← ★
file0x00A4E950  ptr→'pooledstorage'   flag=0
file0x00A4E958  ptr→'profiles'        flag=1
file0x00A4E960  ptr→'storage'         flag=1
file0x00A4E968  ptr→'tags'            flag=0
file0x00A4E970  ptr→'teams'           flag=0
file0x00A4E978  ptr→'tencent'         flag=0
file0x00A4E980  ptr→'titleutilities'  flag=0
file0x00A4E988  ptr→'reward'          flag=0
file0x00A4E990  ptr→'stats'           flag=1
```

### 3.2 与客户端自己读的配置**逐项一致**

`_LEARN_TESTOL_DELIVERY2` 报告 003 实测 `configs_s.info` 的 `[dw_service_info]`（19 项，CRLF）：

```
none=0  all=0  critical=0  non_critical=0  eventlog=0  friends=0  group=0
mail=0  marketplace=0  matchmaking=1  messaging=1  pooledstorage=0
profiles=1  storage=1  tags=0  teams=0  tencent=0  titleutilities=0
reward=0  stats=1
```

**二进制表 20 项 / 配置 19 项（配置多 `none` 之外完全同序），flag 值逐项相同：**
`matchmaking=1, messaging=1, profiles=1, storage=1, stats=1`，其余全 0。

★ 这份配置是**客户端自己读的**（`configs_s.info` 是客户端资产），二进制表是**客户端自己内建的**——两者同序同值 ⇒ 这是**客户端 DW 服务开关表的本地铁证**，不是外部文档。

★★ **`messaging` 是 5 个被启用的服务之一。** 而 `102/*` 的 639 条记录是**全语料第三大服务**（仅次于 71 遥测、10 publisher、80 商城）——一个被显式启用的服务，在协议里高频出现，语义必非「未定」。

### 3.3 这张表**不是**服务号表

必须诚实：`flag` 是 **enabled 开关（0/1）**，**不是服务号**。所以 §3 证明的是「`messaging` 是真实且启用的 DW 服务」，**不直接证明「102 = messaging」**。号↔名的直接绑定仍需 §2（ol-mod）+ §4（RTTI/绑定）合围。

★ 我也穷举过静态 `{u32 id, char* name}` 服务注册表：全镜像扫描**未找到** `{102, <服务名>}` 的静态绑定（`tools/svc_id102_bind.py`）。唯一命中的 `102 → 'fxentity'` 是**渲染实体名**，与 DW 服务无关。**所以静态代码面确实没有「102 = 名字」的直表——这也是 115 卷当初卡住的原因。**

---

## §4 本地侧证据 ②：`bdMessagingGroup` + `messaging.status` 绑定

### 4.1 RTTI 类

`tools/messaging_family.py`，E 镜像 RTTI 全谱（`.?AV...@@`）：

```
0x00A6AE50  .?AVbdMessagingGroup@@          ← ★ 客户端真有 messaging 类
0x00A6ADB4  .?AVbdSerializable@@
0x00A6ADD4  .?AVbdTaskResult@@
0x00A6AE30  .?AVbdReferencable@@
0x00A6AE70  .?AVbdByteBuffer@@
0x00A6AEB8  .?AVbdRichPresenceData@@
0x00A6ED08  .?AVbdTencentHopeInstruction@@
0x00A6EED8  .?AVbdMatchMakingInfo@@
0x00A772F4  .?AVbdProfileInfo@@
0x00A773B0  .?AVbdCODOReadCCPLeaderboardRequest@@
```

★ `bdMessagingGroup` 与 `bdRichPresenceData`（=RichPresence，服务 68）、`bdMatchMakingInfo`（=Matchmaking，服务 21）、`bdProfileInfo`（=Profiles，服务 8）**并列**——即 messaging 是与它们同级的 **bd 层数据类**，不是排行榜。

### 4.2 客户端把 `messaging` 当 DW 服务监听

`tools/dw_service_name_census.py` 抽取所有 `[服务名] 06 'status' 0f 'DWServiceStatus'` 模式：

| 服务名 | 绑定方 | 证据 |
|---|---|---|
| **`messaging`** | `ChattingController` | `0x35BB224` |
| `marketplace` | `MarketController` | `0x35CDB03` |
| `mail` | `MailController` | `0x35C5A9D` |
| `friends` | `ContactController` | `0x35F720F` |

原始串（`tools/dw_status2.py`，`0x35BB1D0-0x35BB250`）：
```
…private:reserveChatMsg 06 'source' … private:localize 04 'cRes' 04 'data'
09 'messaging' 06 'status' 0f 'DWServiceStatus' 0c 'UNRESPONSIVE'
…ChattingController::bind_demonwareChattingStatusChange: UNRESPONSIVE - timestamp: …
```

★★ **客户端代码里 `messaging` 是 DW 服务名字符串，且被 `ChattingController` 通过 `DWServiceStatus` 监听其在线状态。** 这是「messaging 是一个真实 DW 服务」的**本地代码级证据**，与服务 6（`Messaging::sendInstantMessage/sendGlobalInstantMessage/readQueuedMessages`）同族。

★ 旁证：`_LEARN_TESTOL_DELIVERY2` 里 `str-CodolGameServer.txt`/`str-Alwaysoffline.txt` 的解串表含
`Messaging::readQueuedMessages / sendGlobalInstantMessage / sendInstantMessage` 与 `Messaging2::task1/2/5/7` **同表并列**——「Messaging」与「Messaging2」是**两个不同服务的命名对**（6 与 102）。但该串表来自 ol-mod 派生的服务器二进制（含 `RecoveredEmpty::0x66/0x01` 命名痕迹），**只能作交叉参考，不能作本地权威**，故此处仅记旁证。

---

## §5 为什么 `Leaderboard` 候选必须作废

115 卷把 `Leaderboard` 列为「最强候选」，理由是「`102/7` 的 50 个序号槽位 = 排行榜前 50 名」。**这个推理被本卷推翻：**

1. **载荷形态**：`102/7` 是 `u32 50` + `50×(u8 1, u64 i)`，i=0..49 —— 这是**「按索引 0..49 批量取」**。排行榜查询会带玩家 ID / 榜单 ID / 时间窗，**不会是一个恒定的 0..49 索引枚举**。
2. **`102/1` 的 `u8 3` 与 `102/5` 的 `[1,2]`** 是**消息类别/信箱枚举**，与排行榜无关。
3. **`bdMessagingGroup` 与 `bdCODOReadCCPLeaderboardRequest` 是两个不同类**：后者才是排行榜，且**不叫 messaging**。
4. **`messaging=1` 在客户端开关表里被启用**，而排行榜在 `configs_s.info` 里**根本没有独立项**（`stats` 才是统计/榜相关，且 stats 是服务 4）。

⇒ **`Leaderboard` 是「50 个序号」的表面巧合，不是语义。作废。**

---

## §6 `102` 的业务语义（在「Messaging2」名下重述结构）

`Messaging2` 是 Demonware **Messaging 服务的第二代协议**（与 `Profiles2`/`Storage2`/`Friends2`/`TitleUtilities2` 同代命名法：`Xxx2` = 二代）。四个 task 对应「信箱/消息」的**周期性轮询**：

| task | 语义（推断，有载荷支撑） | 载荷 |
|---|---|---|
| `102/7` | **按索引批量拉取信箱条目**（0..49 共 50 槽） | `u32 50` + 50×`(u8 1, u64 i)` |
| `102/1` | **信箱订阅/分类声明**（1 类或 2 类） | `u32 0, u32 N, N×(u8 key, u64 0)` |
| `102/5` | **索引列表 [1,2]**（读哪几类） | `u32 2, u8 1, u8 2` |
| `102/2` | **心跳/空轮询** | 空 |

★ **行为层铁证（沿用 115）**：真实日志 `lobby_srv.log:168-199` 显示我们对 102 一律回空 ACK（`UNMAPPED`），客户端**大厅照进不误** ⇒ `Messaging2` **可安全空应答**，服务端不实现也不破坏大厅。

---

## §7 权威层级自检（AGENTS.md 强制）

| 引用 | 是否权威 | 用法 |
|---|---|---|
| E 镜像服务开关表（本地二进制） | ✅ 最高 | 主证据①，证明 messaging 真实且启用 |
| `bdMessagingGroup` RTTI + `messaging.status` 绑定（本地二进制） | ✅ 最高 | 主证据②，证明 messaging 是 bd 层 DW 服务 |
| 语料 639 条 `102/*`（本地抓包） | ✅ 最高 | 结构与载荷，逐字段 |
| ol-mod `AckOnlyServices.cpp` | ❌ 非权威（3.3.3.3） | **仅作「名字候选」交叉参考**；其载荷与我们逐字节同一份，故名字可信 |
| ol-mod `RecoveredCatalog.cpp` `Unknown66` | ❌ 非权威 | 说明「号≠名」两路得来 |

**定名判定**：本地证据 ①② 把「messaging」钉为真实且启用的 DW 服务；语料把 102 钉为真实高频服务；ol-mod 提供「102 ↔ Messaging2」的唯一直接名字，且其描述的载荷与我们**逐字段同一份**。**三条独立链交汇于同一名字 ⇒ 定名成立。** 这是本项目「ol-mod 可作同族交叉参考、但不得照抄常量」规则的正确用法：**只借名字，不借任何常量/字节布局**（字节布局我们自己从语料验证）。

---

## §8 状态表

| 项 | 状态 | 证据 |
|---|---|---|
| `102 = Messaging2 (0x66)` | ✅ **定名** | ①服务开关表 + ②RTTI/绑定 + ③载荷逐字段 |
| 四 task 载荷 | ✅ 逐字段与 ol-mod 注释一致 | `verify_102_messaging2.py` |
| 客户端 messaging 服务启用 | ✅ `messaging=1` | 二进制表 `0xA4E948` + `configs_s.info` |
| `bdMessagingGroup` 类存在 | ✅ `0xA6AE50` | `messaging_family.py` |
| `messaging.status` DW 绑定 | ✅ `ChattingController` | `dw_service_name_census.py` |
| `Leaderboard` 候选 | ❌ **作废** | §5 四条反证 |
| 静态 `{102,名字}` 直表 | ❌ 不存在（已穷举） | `svc_id102_bind.py` |
| 空应答安全 | ✅ 大厅能进 | `lobby_srv.log` |

---

## §9 复现命令

```powershell
python -I tools/verify_102_messaging2.py      # 四 task 载荷 vs ol-mod 逐字段
python -I tools/dump_svc_info_table2.py       # 客户端服务开关表 0xA4E8F8
python -I tools/messaging_family.py           # bdMessagingGroup RTTI
python -I tools/dw_service_name_census.py     # messaging.status 绑定
python -I tools/svc_id102_bind.py             # 穷举静态 {102,名} 表（证明不存在）
python -I tools/svc6_102_census.py            # 服务 6 与 102 分布
```

产物：`_byte_papers/verify_102.txt`、`svc_info_table2.txt`、`messaging_family.txt`、`dw_svc_names.txt`、`svc102_bind.txt`、`svc6_102.txt`。
