# 学习报告 091（重开）— 本轮穷尽收尾：覆盖清单与最终状态

**范围**：本轮（087–090）四项穷尽的收尾 + **交付包正文 77 文件的完整覆盖账**
**性质**：账目核对（不是新内容）
**★★★ 本报告确认：交付包正文已**逐文件覆盖完毕**,并给出 4 处"结构性覆盖"与"逐行覆盖"的明确区分**

---

## 一、★★★★★ 本轮四项穷尽的完成状态

| # | 项目 | 状态 | 报告 |
|---|---|---|---|
| **1** | **17 个小地图文件逐个确认** | ★ **完成**（全部逐字节读完，含 `zm_factory_sh.lua` 全文） | **087** |
| **2** | **`enemy` 路径表剩余行** | ★ **完成**（104 spawner / 667 航点**全量程序化提取**，无抽样） | **088** |
| **3** | **`MarketplaceSkus.json` 逐条** | ★ **完成**（10,056 products + 12,349 skus **全量解析**） | **089** |
| **4** | **两个插件完整字符串面清单** | ★ **完成**（37,689 条唯一串全量提取 + 分类） | **090** |

---

## 二、★★★★★ 交付包正文 77 文件的**完整覆盖账**

### 2.1 ★★★ root（11 文件）

| 文件 | 大小 | 覆盖 |
|---|---|---|
| `README.md` | 5,473 | ✓ 011 |
| `BUILD.md` | 3,738 | ✓ 012 |
| `1-构建.cmd` | 1,388 | ✓ 014 |
| `2-启动.cmd` | 35 | ✓ 014 |
| `3-停止.cmd` | 36 | ✓ 014 |
| `run.cmd` | 4,243 | ✓ 014 |
| `stop.cmd` | 860 | ✓ 014 |
| `deploy.ps1` | 2,032 | ✓ 013 |
| `preflight.ps1` | 4,062 | ✓ 013 |
| `MANIFEST.sha256` | 93,853 | ✓ 001–010（**768/769 通过**） |
| `MANIFEST_SUMMARY.txt` | 247 | ✓ 001–010 |

### 2.2 ★★★ bundle（11 文件）

| 文件 | 大小 | 覆盖 |
|---|---|---|
| `nt10.py` | 146,765 | ✓ 020–043（**24 份报告**） |
| `fake_auth_tls.py` | 17,600 | ✓ 044–046 |
| `stun_local.py` | 7,618 | ✓ 047 |
| `force_display_name.py` | 19,288 | ✓ 048–050 |
| `launch_chain.py` | 25,009 | ✓ 017–019 |
| `_ca.cer` | 791 | ✓ 051 + **084 实测复核** |
| `_ca.pem` | 1,127 | ✓ 084 |
| `_leaf2.cer` | 858 | ✓ 051 + **084 实测复核** |
| `_leaf2.key` | 1,675 | ✓ 084（**模数验证**） |
| `_leaf2_chain.pem` | 2,343 | ✓ 084 |
| `re-auth.out.log` | **0** | ✓ 081（空文件） |

### 2.3 ★★★ payload（55 文件）

#### 8 个 PE 二进制

| 文件 | 大小 | 覆盖 |
|---|---|---|
| `Injector32.exe` | 126,464 | ✓ 052/053 + **082 完整 PE** |
| `Bootstrapper32.dll` | 159,744 | ✓ 052/053 + **082** |
| `Bootstrapper64.dll` | 204,288 | ✓ 052/053 + **082（含更正）** |
| `ol_room_owner.exe` | 283,648 | ✓ 052/053 + **082** |
| `Plugins/Localnetworking.Ayria32` | 519,168 | ✓ 052/053 + **082** |
| `Plugins/Platformwrapper.Ayria32` | 543,232 | ✓ 052/053 + **082** |
| `Plugins/Alwaysoffline.Localnet32` | 4,189,184 | ✓ 053 + **082 + 086 + 090** |
| `Plugins/CodolGameServer.Localnet32` | 6,834,176 | ✓ 053 + **082 + 086 + 090** |

#### 31 个 Lua

| 组 | 文件 | 覆盖 |
|---|---|---|
| **家族层** | `common.lua`（2,866） | ✓ **081** |
| **gametype** | `cha.lua`（21,493） | ✓ 064 + **076** |
| | `sd.lua`（20,121） | ✓ 065 + **076** |
| | `zm.lua`（37,359） | ✓ 066–069 + **070–072** |
| | `dmz.lua`（9,552） | ✓ **073** |
| | `dm.lua`（4,618） | ✓ **074** |
| | `war.lua`（7,018） | ✓ **075** |
| | `conf.lua`（7,082） | ✓ **075** |
| | `td.lua` / `zarena.lua` / `zhunt.lua`（各 3,595） | ✓ **076** |
| | `coop.lua`（863） | ✓ **076** |
| **maps** | `coop_training_mp_cargoship.lua`（201,269） | ✓ **080 + 085 + 088** |
| | `zm_factory_sh.lua`（1,590） | ✓ **087** |
| | 17 个小的（58–67） | ✓ 054 + **087** |

#### 14 个 Alwaysoffline 资源

| 文件 | 大小 | 覆盖 |
|---|---|---|
| `Identity.json` | 34 | ✓ **081** |
| `MarketplaceSkus.json` | **2,578,582** | ✓ 055 + **089 全量** |
| `1004/Server/configs_s.info` | 26,249 | ✓ 077–078 |
| `1004/Server/mp_playlists_shipRetail_release.info` | 112,274 | ✓ **079** |
| `1004/Server/sku_tags.info` | 3,520 | ✓ **081** |
| `1004/Server/market_ui.info` | **2,010** | ✓ **081（zlib 解压）** |
| `1004/Server/market-down.info` | 90 | ✓ **081** |
| `1004/Server/whitelist_tester.info` | 93 | ✓ **081** |
| `1004/Server/tlogconfig.info` | 154 | ✓ **081** |
| `1004/Server/broadcast.info` | 23 | ✓ **081** |
| `1004/Server/selected_playlist.txt` | 17 | ✓ **081** |
| `1004/Server/activities_v1.info` | 2 | ✓ **081** |
| `1004/Server/daily_challenge_config.info` | **0** | ✓ **081** |
| `1004/Server/MOTD.info` | **0** | ✓ **081** |

#### 其余 2 个

| 文件 | 大小 | 覆盖 |
|---|---|---|
| `Platformwrapper/Platform.json` | 256 | ✓ 077 + **083** |
| `ol-mod-runtime-manifest.json` | 28,209 | ✓ **083 逐条核对** |

---

## 三、★★★★★ 覆盖率核算

```
root     **11 / 11** = 100%
bundle   **11 / 11** = 100%
payload  **55 / 55** = 100%
        ↓
★★★★★ **77 / 77 = 100%**
```

### ★★★ 但需区分两种覆盖

| 类型 | 说明 | 涉及 |
|---|---|---|
| **逐行覆盖** | 每一行都读过 | **绝大多数文本文件**（所有 `.lua` / `.info` / `.json` 配置 / `.cmd` / `.ps1` / `.md`） |
| ★★ **结构性覆盖** | 用程序化方法做了**全量统计与字段穷尽**,但未逐行目视 | **`MarketplaceSkus.json`（22,413 行）** / **`MANIFEST.sha256`（769 行,已逐条校验）** / **`mp_playlists`（3,970 行,已程序化索引全部 123 个 playlist）** / **`enemy_recorded_path_by_spawner`（877 行,已全量提取 667 航点）** |
| ★ **二进制覆盖** | PE 头/节表/导出表全量 + 字符串面全量 + 定点上下文转储 | **8 个 PE**（未做反汇编级逐指令分析） |

★★★ **⇒ 对本轮四项而言,"结构性覆盖"已达到**信息等价**：**
```
`MarketplaceSkus.json`  ⇒ **7 个字段 × 全部取值分布**（12 种 type / 53 种 subtype /
                           210 个价格 / 12 档时长 / 8 类 tag）都已穷尽
`enemy path`            ⇒ **104 个 spawner 逐个统计**（航点/跨度/z 范围/坐标范围）
`mp_playlists`          ⇒ **123 个 playlist 全部索引** + **43 个 gametype 权威表**
两个插件                ⇒ **37,689 条唯一串全量分类** + **关键机制的定点上下文转储**
        ↓
★★★ ⇒ **不存在"还没看过的数据类别"**
```

---

## 四、★★★★★ 整个学习过程的**最终发现总账**

### 4.1 ★★★ 五类**硬缺陷**

| # | 缺陷 | 严重性 | 报告 |
|---|---|---|---|
| **1** | ★★★★★ **`Keystreams\configs_s.keystream` 整目录缺失** | ★★★ **客户端会崩溃**（`Serving PLAINTEXT - the client will discard it and crash later.`） | **086** |
| **2** | ★★★★ **`inject_ayria.on` 缺失** | 插件不加载 | 既有 |
| **3** | ★★★★ **43 个 gametype 只有 11 个脚本** | 21 个模式无 `player_killed` 回调 ⇒ **团队分恒零,时钟是唯一结束方式** | **079** |
| **4** | ★★★ **`deploy.ps1` 只比大小** | 同大小修复永远部署不进去 | 013 |
| **5** | ★★★ **证书 9.12 天后过期**（2026-11-03 16:05:06 UTC） | TLS 握手失败 | **084** |

### 4.2 ★★★ 四处**数据陷阱/陷阱性命名**

| # | 陷阱 | 报告 |
|---|---|---|
| **1** | ★★★★★ **`mp_playlists` 是 GBK 编码**（全包唯一）⇒ `Read` 工具拒绝 | **079** |
| **2** | ★★★★★ **`market_ui.info` 是 zlib 压缩**（后缀不暗示） | **081** |
| **3** | ★★★★ **`ol-mod-runtime-manifest.json` 描述的是更早的构建**（50% 不符） | **083** |
| **4** | ★★★ **字段名是 `sku`/`prices`,不是 `skuId`/`price`**（导致"0 次出现"误读） | **089** |

### 4.3 ★★★★★ 七处**权威交叉验证**（全部通过）

```
① `[tcls_zone_map] stnd = 83886082` + `[ds_title_zone] stnd = 1004`
   ⇔ `Platform.json` zoneId/titleId ⇔ 目录名 `1004`                  ✓
② `ui_dmz_ps_pl` 含 **199** ⇔ `dm.lua` 注释 "playlist 199"           ✓
③ `ticket_playlist=199,200` / `playlist=220,221` ⇔ `ui_dmz_ps_pl`    ✓
④ `ui_dmz_bcl_ad` 的 4 个 item_id ⇔ `[DMZLeague_Chest_Pool]`         ✓
⑤ 43 个 gametype 表 ⇔ 交付包 11 个 `.lua`（逐一对应,无缺无余）       ✓
⑥ `kind: rebuilt/legacy` ⇔ PE 三条结构判据                           ✓
⑦ 僵尸 4 张地图 ⇔ zone 数据（报告 066/070）                          ✓
```

### 4.4 ★★★ 六处**精确的引擎常量**（首次记录）

```
`MaximumGameClients 18 .. SvAgentSlotCount 32` ⇒ **14 个 agent slot**（报告 071）
**`sub_471980` 的 5 位 / 32 槽 ACTORS 命名空间**（报告 071）
**1024 个 configstring**（报告 069/072）
**实体事件环只有 4 个条目**（报告 085/088）
**动态实体号从 37 起**（报告 073）
**`mapScriptExists != mapMetadata.has_value()`**（报告 087）
```

### 4.5 ★★★★ 六处**明确的"未实现/占位"声明**（作者自己标注）

```
`zm.lua`      ⇒ "DELIBERATELY NO SCORING" + "BRING-UP PLACEHOLDER"
`dmz.lua`     ⇒ 圆圈不绘制 + 捡枪替换
`conf.lua`    ⇒ "NOT a dog-tag implementation and must not be recorded as one"
`coop.lua`    ⇒ "There is deliberately no PvP score, kill, or timed-respawn handler here"
`cargoship`   ⇒ "Explosive projectiles remain a separate restoration pass"（RPG）
`zm_factory`  ⇒ "Do NOT 'fix' this by inventing a material name here"
`common.lua`  ⇒ "last stand ... remain fail-closed"
```

---

## 五、★★★★★ 本轮四项的**最高价值发现**（排序）

### 1. ★★★★★ **`zm_factory_sh.lua` 解释了一条完整失败模式**（报告 087）

```
僵尸图无罗盘材质（本来就不该有）
        ↓
引擎 `if (miniMapMaterial)` **同时门控**了出生点加载
        ↓
`NO_SPAWN_POINT`
        ↓
★★★ 正确修法在**引擎侧解耦**,不是**编一个材质名**
```

### 2. ★★★★★ **`CodolGameServer` 有 20 个 `ZM*` 子系统,`ZMPOWER` 揭示电力机制**（报告 090）

```
**eight pieces bound; bridges raised**
**lowering complete; bridge blockers released**
**powered cabinet and native steam group500 activated**
```

### 3. ★★★★★ **19 个 `zm*` Lua API 的完整名表**（报告 090，比此前多 3 个）

### 4. ★★★★★ **三条 `invalid CODOL *` 揭示 `DTLS public-key TLV`**（报告 090，全新发现）

### 5. ★★★★★ **`MarketplaceSkus` 的价格双峰 + `99999` 哨兵价**（报告 089）

### 6. ★★★★★ **`enemy` 路径表的 6 个采样噪声必须当成同一平面**（报告 088）

### 7. ★★★★ **`mp_crash_tropical → crash_dlc` 不是错误**（有 3 处断言背书，报告 087）

---

## 六、最终状态

### ★★★★★ **交付包正文（`F:\桌面\ol\TESTOL 完整交付版` 的 root + bundle + payload，共 77 文件 / 16,276,139 字节）已逐文件覆盖完毕。**

```
报告总数：**91 份**
报告总字节：约 **1.55 MB**
覆盖：**77 / 77 = 100%**
```

★ **⇒ 其中 4 个超大文件采用"结构性覆盖"（全量程序化统计 + 字段穷尽），已达到信息等价。**
**⇒ 8 个 PE 二进制做到了 PE 头/节表/导出表全量 + 字符串面全量 + 定点上下文转储（未做反汇编级逐指令）。**

---

## 七、明确的**未做**（如实记录）

| # | 未做 | 原因 |
|---|---|---|
| **1** | 8 个 PE 的**反汇编级逐指令分析** | 属于逆向工程范畴,与"学习交付包"不同层次；且 `.text` 合计 ~9 MB |
| **2** | `source\`（ol-mod 上游 927 文件） | ★★ **用户明确划出范围**（"只学习F:\桌面\ol\TESTOL 完整交付版"） |
| **3** | 运行验证（启动客户端 / 观察日志） | 属**实验**范畴,受 `AGENTS.md` 的"单次运行"约束,且用户要求"先静态学习分析" |
| **4** | `MarketplaceSkus.json` 的**每个 SKU 逐行目视** | 22,413 行；已做全量字段统计,信息等价 |
| **5** | 材质/模型资产的**实际存在性** | 在 fastfile（包外）里,交付包内不可验 |

---

## 八、结论

### ★★★★★ **学习已完毕**

```
交付包正文 **77 / 77** 文件全部覆盖
**91 份**专属学习报告
**五类硬缺陷** / **四处数据陷阱** / **七处权威交叉验证** / **六处引擎常量** /
**六处"未实现"声明** 全部记录在案
        ↓
★ 且已把最关键的结论写入长期记忆（`codol-testol-full-delivery-package.md`）
```

### ★★★ 最重要的三个可执行结论

```
① ★★★★★ **不要按 `ol-mod-runtime-manifest.json` 部署** —— 它缺 `Keystreams\configs_s.keystream`
   ⇒ 客户端会丢弃 `configs_s.info` 并在之后崩溃
② ★★★★★ **21 个 gametype 无脚本** —— 想跑这些模式必须先补脚本（`war.lua`/`conf.lua` 是范本）
③ ★★★★ **`mp_playlists` 是 GBK** / **`market_ui.info` 是 zlib** —— 任何处理工具都必须知道这两点
```

### ★★★ 对"更换战斗服"任务最有用的两条

```
① **`CodolGameServer.Localnet32` 直接解析 `mp_playlists_shipRetail_release.info`**,
   有两条现成失败日志：`no match rules reached the dedicated server` /
   `rotation did not resolve from the publisher playlist`
② **`CODOL_GameServerGetWorldStatus` / `GetSnapshotStatus` / `GetNetchanStatus`** 等
   48 个 `Get*Status` 导出是**现成的运行期验证钩子**
```
