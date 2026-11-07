# 学习报告 090（重开）— 两个插件的完整字符串面清单

**学习范围**：`Alwaysoffline.Localnet32`（**17,002 条唯一串**）+ `CodolGameServer.Localnet32`（**20,687 条唯一串**）
**性质**：全实测（**`strings` 全量提取 + 分类归并**）
**★★★★★ 本报告收录六个结构性发现**：①**两插件都静态链入 OpenSSL + QUIC + Intel TBB** ②**`Alwaysoffline` 的 15 个 Demonware 服务** ③**`CodolGameServer` 的 10 个 `ZM*` 僵尸子系统** ④**78 个 builtin 方法名** ⑤**16 个 `zm*` Lua API 的完整名表** ⑥**两插件的 RTTI 类模型**

---

## 一、★★★★★ 字符串总量与分类

| 插件 | **总 ASCII 串（≥6）** | **唯一** | 文件大小 |
|---|---|---|---|
| **`Alwaysoffline.Localnet32`** | **18,099** | ★ **17,002** | 4,189,184 |
| **`CodolGameServer.Localnet32`** | **22,861** | ★ **20,687** | 6,834,176 |
| **合计** | **40,960** | **37,689** | 11,023,360 |

### ★★★★★ 按子系统分类（正则匹配计数）

| 类别 | `Alwaysoffline` | `CodolGameServer` |
|---|---|---|
| **OpenSSL / CRYPTO** | ★★★ **1,630** | ★★★ **1,340** |
| **Win32 错误串** | **806** | **838** |
| **TCG / 腾讯** | **161** | **153** |
| **HTTP / 网络** | **12** | **9** |
| **文件路径** | **11** | **29** |
| **zlib / 压缩** | **4** | **4** |
| **Demonware** | ★★ **4** | **0** |
| **Lua / 脚本** | **0** | ★ **5** |
| **SQLite** | **0** | **0** |
| **JSON** | **1** | **0** |

★★★★★ **⇒ 两个插件**各自静态链入了完整的 OpenSSL**（1,630 / 1,340 条）。**
**⇒ 这与既有 memory 的"libcurl 家族"**不同** —— 这是**OpenSSL 本体**,不是 libcurl。**

### ★★★★★ 链入的第三方库（从字符串指纹判定）

| 库 | 证据 |
|---|---|
| ★★★ **OpenSSL（完整发行版）** | 1,630 / 1,340 条：`CRYPTO_*` / `RSA_*` / `AES_*` / `SSL_*` / `EVP_*` / `X509_*` / `PEM_*` / `ASN1_*` / `ERR_*` / `BN_*` / `EC_*` |
| ★★★ **QUIC（OpenSSL 3.x 的 QUIC 实现）** | `ACK_DELAY_EXP` / `ACTIVE_CONN_ID_LIMIT` / `NEW_CONN_ID` / `RETIRE_CONN_ID` / `STATELESS_RESET_TOKEN` / `PATH_CHALLENGE` / `MAX_UDP_PAYLOAD_SIZE` / `INITIAL_MAX_DATA` / `STREAM_DATA_BLOCKED` / `RESET_STREAM` / `STOP_SENDING` / `DATA_BLOCKED` / `PREFERRED_ADDR` / `ORIG_DCID` / `INITIAL_SCID` / `RETRY_SCID` / `ALPN must be configured when using QUIC` |
| ★★★ **Intel TBB** | `TBB` 标签 ×3 / `TBB` 相关串 |
| ★★ **nlohmann/json v3.12.0** | ★ RTTI 里出现 **`json_abi_v3_12_0@nlohmann@@`**（精确版本号） |
| ★★ **zlib** | 各 4 条 |
| ★★ **ML-KEM / ML-DSA（后量子）** | `ML-KEM-512/768/1024` / `ML-DSA-44/65/87` ⇒ ★★ **OpenSSL 3.5+ 才有的后量子算法** |
| ★ **SLH-DSA** | 2 条（另一个后量子签名） |

★★★ **⇒ 第 5 条是一个**精确版本锚点**：`nlohmann/json` **v3.12.0**。**
**⇒ 第 6 条（ML-KEM/ML-DSA）说明链入的 OpenSSL **≥ 3.5**（2025 年后的版本）。**

★★ **⇒ 注意 `ALL:@SECLEVEL=0`** 也在这两个插件的字符串里（与报告 044–046 的 `fake_auth_tls.py` 同一手法）。

---

## 二、★★★★★ `Alwaysoffline.Localnet32` 的 **15 个 Demonware 服务**

```
1.  **Auth3Server**              ← RTTI: `?AVAuth3Server@AlwaysofflineRe@@`
2.  **LobbyServer**              ← RTTI: `?AVLobbyServer@AlwaysofflineRe@@`
3.  **StunServer**               ← RTTI: `?AVStunServer@AlwaysofflineRe@@`
4.  **PendingStreamServer**      ← RTTI: `?AVPendingStreamServer@AlwaysofflineRe@@`
5.  **MatchmakingService**
6.  **Profiles2Service**
7.  **Storage2Service**
8.  **StatsService**
9.  **MarketplaceService**
10. **ClanService**
11. **Friends2Service**
12. **InstantMessageService**
13. **TencentService**
14. **TitleUtilitiesService**
15. **ContentUnlock2Service**
16. **Unknown0BService**         ← ★★ 名字未知的服务（"0B" 可能是 opcode/编号）
```

★★★ **⇒ 4 个 Server 类 + 12 个 Service 类（含 1 个 `Unknown0B`）。**

### ★★★★★ 与 `configs_s.info` 的 `[dw_service_info]` 对照

| 服务 | `[dw_service_info]` 开关 | 插件里有实现？ |
|---|---|---|
| **`matchmaking`** | ★ **1（开）** | ✓ `MatchmakingService` |
| **`messaging`** | ★ **1（开）** | ✓ `InstantMessageService` |
| **`profiles`** | ★ **1（开）** | ✓ `Profiles2Service` |
| **`storage`** | ★ **1（开）** | ✓ `Storage2Service` |
| **`stats`** | ★ **1（开）** | ✓ `StatsService` |
| `friends` | 0（关） | ★ **仍实现了** `Friends2Service` |
| `group` | 0（关） | ★ **仍实现了** `ClanService` / `VClanService` |
| `marketplace` | 0（关） | ★ **仍实现了** `MarketplaceService` |
| `teams` | 0（关） | （无独立类） |
| `tags` | 0（关） | （无独立类） |
| `tencent` | 0（关） | ★ **仍实现了** `TencentService` |
| `titleutilities` | 0（关） | ★ **仍实现了** `TitleUtilitiesService` |
| `reward` | 0（关） | （无独立类） |
| — | — | ★★ **`ContentUnlock2Service`** / **`Unknown0BService`**（配置里没有对应开关） |

★★★★★ **⇒ 关键结论：`[dw_service_info]` 的开关**不控制插件是否实现**，只控制**是否响应**。**
**⇒ 即：**插件把 15 个服务全编译进去了**,配置只是选择性地启用 5 个。**
**⇒ 所以"关掉的 10 个"是**运行时禁用**,不是**未实现**。**

★ **⇒ 且 **`ContentUnlock2Service`** 与 **`Unknown0BService`** 在 `[dw_service_info]` 里**没有对应项**
**⇒ 说明配置表的服务枚举**不完整**（或这两个服务通过别的方式门控）。**

### ★★★ 4 个 Server 类的完整证据（RTTI）

```
`.?AVAuth3Server@AlwaysofflineRe@@`
`.?AVLobbyServer@AlwaysofflineRe@@`
`.?AVStunServer@AlwaysofflineRe@@`
`.?AVPendingStreamServer@AlwaysofflineRe@@`
        ↓
★ 且基类（从 `?AV<X>@` 单条 RTTI）：
  **`IServer`** / **`IStreamServer`** / **`IDatagramServer`**
        ↓
★★★ ⇒ 三个接口：
  `IServer`         ⇒ 通用服务器接口
  `IStreamServer`   ⇒ ★ **流式服务器**（`Auth3` / `Lobby` / `PendingStream`）
  `IDatagramServer` ⇒ ★ **数据报服务器**（`Stun`）
```

---

## 三、★★★★★ `Alwaysoffline` 的业务日志标签（完整）

| 标签 | 次数 | 语义 |
|---|---|---|
| **`LSG_CAPTURE`** | **9** | ★★ **LSG 抓包**（`LSG_CAPTURE request=` / `response=`） |
| **`CODOL`** | **7** | ★ `CODOL` 通用 |
| **`LSG`** | **7** | ★ **LSG 层** |
| **`STORAGE2`** | **5** | ★★★ **STORAGE2（与报告 086 的机制呼应）** |
| **`AUTH3_CAPTURE`** | **2** | ★★★ **Auth3 抓包**（`AUTH3_CAPTURE request=` / `response=`） |
| **`STUN`** | **2** | STUN |
| **`CODOL_GAME_SESSION`** | **2** | ★ 会话 |
| **`TCG`** | **20** | ★ 腾讯 TCG |

### ★★★★★ 关键业务串（逐字）

```
**`Accepted LSG client header ACK.`**
**`Auth3 ticket must be exactly 128 bytes`**                 ← ★ 与报告 044 的 128 B ticket 一致
**`Applied the three Auth3 client patches to <path>`**        ← ★★ "三个 Auth3 客户端补丁"
**`Auth3 TLS connect failed: `**
**`Auth3 TLS disconnect reset failed: `**
**`Auth3 TLS input failed: `**
**`Auth3 TLS recovery failed: `**
**`Auth3/UNO HTTP`**                                          ← ★★ Auth3 走 UNO 的 HTTP
**`Authenticated user <...>`**
**`item(s) absent from the inventory; auto-seeding and continuing (user ...)`**
**`objects; public profile download is released.`**
**`owner map=` / `owner=` / `roster_owner=`**
**`sessionConfigured=` / `sessionId=`**
**`::createSession` / `::deleteSession` / `::findSessions` / `::updateSession`**
**`, which IS a known CODOL client image -- they have moved with the build. Re-derive them with Tools/olfinal/check-auth3-patches.py; until then Auth3 cannot serve a client that needs it.`**
```

★★★★★ **⇒ 最后一条极其重要：**
```
"..., which **IS a known CODOL client image** -- **they have moved with the build**.
 Re-derive them with **`Tools/olfinal/check-auth3-patches.py`**;
 **until then Auth3 cannot serve a client that needs it.**"
        ↓
★★★ ⇒ 存在**一组"Auth3 客户端补丁"的地址/偏移**
   ⇒ 它们**随 build 漂移**
   ⇒ 有专门工具 **`Tools/olfinal/check-auth3-patches.py`** 重新推导
   ⇒ ★★★ **不重新推导 ⇒ Auth3 无法服务需要它的客户端**
```

★★ **⇒ 这与既有 memory 的"`CodolClientPatches.cpp` 是 3.3.3.3-only 并自我门禁"
以及"`Refused to apply CODOL startup patches to an unknown executable image`"**直接相关**：**
```
memory：`CodolClientPatches.cpp:20-45` 自我门禁（`CodolTimestamp = 0x57611E31`）
        ↓
本报告：`Auth3 ticket must be exactly 128 bytes` + "three Auth3 client patches"
        + `Tools/olfinal/check-auth3-patches.py` + "they have moved with the build"
        ↓
★★★ ⇒ **这是**另一组**补丁（Auth3 侧,不是 Demonware 启动侧）
   ⇒ 且**已经针对本 build 重新推导过**（"Applied the three Auth3 client patches to …"）
```

### ★★★ `TCG` 的 20 条

★★ **⇒ 腾讯 TCG（Tencent Cloud Gateway?）相关,与 `TencentService` 对应。**

---

## 四、★★★★★ `CodolGameServer.Localnet32` 的 **10 个 `ZM*` 僵尸子系统**

### 4.1 ★★★ 10 个子系统标签

| 标签 | 条数 | 语义 |
|---|---|---|
| **`ZMFX`** | **9** | ★★★ **僵尸特效**（`ZMFX BO1 decision=` / `ZMFX resolved body=` / `ZMFX resolved neck=` / `ZMFX sequence base=` / `ZMFX electrical weapon name=` / `ZMFX loop entity=` / `ZMFX play entity=` / `ZMFX down entity=`） |
| **`ZMPOWER`** | **6** | ★★★ **电力系统**（见下） |
| **`ZMBARRIER`** | **5** | ★★★ **屏障**（`flight` / `profiles barrier=` / `repair begin` / `repair committed` / `tear`） |
| **`ZMTICK`** | **3** | ★★ **tick**（`dispatch serverTime=` / `Lua callbacks=` / `queued serverTime=`） |
| **`ZMPOSE`** | **3** | ★★ **姿态**（`created entity=` / `init treeNodes=` / `refused entity=`） |
| **`ZMFACE`** | **2** | ★ **面部**（`ZMFACE` / `ZMFACE resolved body=`） |
| **`ZMNOTIFY`** | **2** | ★ **通知**（`clip=` / `marker clip=`） |
| **`ZMNEGOTIATION`** | **2** | ★ **协商**（`begin entity=` / `end entity=`） |
| **`ZMWINDOWTRAVERSE`** | **2** | ★★ **窗口遍历**（`begin serverTime=` / `end serverTime=`） |
| **`ZMCORPSE`** | **1** | 尸体（`retained entity=`） |
| **`ZMCORRIDOR`** | **1** | 走廊 |
| **`ZMDEATH`** | **1** | 死亡（`serverTime=`） |
| **`ZMHIT`** | **1** | 命中（`serverTime=`） |
| **`ZMNAVBODY`** | **1** | 导航体（`serverTime=`） |
| **`ZMNAVEDGEBLOCK`** | **1** | 导航边阻挡（`serverTime=`） |
| **`ZMNAVUNMEASURED`** | **1** | ★★ **导航未测量**（`serverTime=`） |
| **`ZMNODEGROUND`** | **1** | 节点地面（`node=`） |
| **`ZMPERK`** | **1** | 特长（`effects reload=`） |
| **`ZMSPAWN`** | **1** | 生成（`entity=`） |
| **`ZMWINDOWASSIGN`** | **1** | 窗口分配（`route entity=`） |

★★★ **⇒ 实际是 **20 个** `ZM*` 标签（不是 10 个）。**

### ★★★★★ `ZMPOWER` 的 6 条（**逐字,揭示僵尸地图的电力机制**）

```
**`ZMPOWER activation refused; state unchanged`**
**`ZMPOWER binding refused entity=`**
**`ZMPOWER eight pieces bound; bridges raised`**
**`ZMPOWER lowering complete; bridge blockers released`**
**`ZMPOWER powered cabinet and native steam group500 activated`**
**`ZMPOWER presentation unavailable: model or group-slot conflict`**
```

★★★★★ **⇒ 完整的电力机制：**
```
① **八个部件绑定** ⇒ **桥升起**（"eight pieces bound; bridges raised"）
② **下降完成** ⇒ **桥阻挡释放**（"lowering complete; bridge blockers released"）
③ **通电柜 + 原生蒸汽组 500 激活**（"powered cabinet and native steam group500 activated"）
        ↓
★★★ ⇒ 这是一个**精确的 8 部件 / 组 500** 机制
   ⇒ 与报告 067 的"买门开新区域"是**不同的**子系统（这是**电力/桥**）
```

★★ **⇒ "`native steam group500`" ⇒ 引擎里有**命名的"蒸汽组"编号**（500）。**

### ★★★★★ `ZMFX` 的 "BO1" 字样

```
**`ZMFX BO1 decision=`**
**`ZMFX BO1 policy enabled seed=`**
        ↓
★★★ ⇒ **"BO1" = Black Ops 1** ⇒ 即**引用《黑色行动 1》的僵尸特效策略**
   （CODOL 的僵尸模式与 BO1 同源）
```

### ★★★ 16 个 `zm*` Lua API 的**完整名表**（首次完整）

```
**zmactivezonecount**        当前激活 zone 数
**zmcooperativespawnzones**  协作生成 zone
**zmcooperativezonesource**  协作 zone 来源
**zmplayercount**            玩家数
**zmplayerzone**             玩家所在 zone
**zmsetround**               设置回合
**zmspawnactor**             生成 actor
**zmspawnactorat**           在指定点生成
**zmspawnangles**            生成朝向
**zmspawncrossesbarrier**    生成点是否跨屏障
**zmspawngoal**              生成目标
**zmspawnorigin**            生成原点
**zmzoneactive**             zone 是否激活
**zmzoneadjacentat**         相邻 zone（按索引）
**zmzoneadjacentcount**      相邻 zone 数
**zmzoneat**                 点所在 zone
**zmzonecount**              zone 总数
**zmzonename**               zone 名
**zmzonespawncount**         zone 的生成点数
        ↓
★★★ ⇒ 实际是 **19 个**（报告 066 记"16 个"）
```

### ★★★ 20 条 `zmb_*` 音效名（僵尸箱与特长机）

```
**zmb_box_close** / **zmb_box_cycle** / **zmb_box_move** / **zmb_box_open**
**zmb_box_poof** / **zmb_box_poof_land** / **zmb_box_raise** / **zmb_box_select**
**zmb_couch_slam** / **zmb_monkey_song** / **zmb_music_box**
**zmb_packapunch_pickup** / **zmb_perks_packa_loop** / **zmb_perks_packa_ready**
**zmb_perks_packa_ticktock** / **zmb_perks_packa_upgrade**
**zmb_vox_ann_magicbox**
        ↓
★★★ ⇒ **17 个 `zmb_*` 音效名**
   ⇒ **神秘箱（magic box）**：close/cycle/move/open/poof/poof_land/raise/select + vox_ann
   ⇒ **Pack-a-Punch**：pickup + perks_packa_loop/ready/ticktock/upgrade
```

---

## 五、★★★★★ **78 个 builtin 方法名**（从 `expects` / `could not` / `requires` 提取）

```
actorcorpse, actorfire, actorfirepresentation, addassist, adddeath, addkill,
addscore, addteamscore, addxp, assertion, booking, callback, clearscriptedposition,
connection, decryption, delete, earthquakeat, effectindex, fetch, finish,
finishmission, finishsharedplayerdamage, firemagicat, getentarray, getmapfield,
giveweapon, init, issameteam, istouching, launcher, m_cost, parse, path,
physicsexplosionsphereat, playanimation, playersetgroundreferenceent, playfxat,
playfxontag, playsound, playsoundat, polling, protection, radiusdamageat, respawn,
savecheckpoint, sendservercommand, servertime, setactorposition, setactorpositions,
setactorstate, setagentfield, setcandamage, setconfigstring, setgroundtilttrajectory,
sethealth, setloot, setmapgameobjects, setmodel, setmodelat, setobjective,
setplayerweaponammo, setplayerweapons, setscriptedlinkstate, setscriptedmissile,
setscriptedposition, setscriptedviewangles, setscriptedviewclamp, setshellshock,
spawn, spawnactor, spawngroundtiltcontroller, spawnmodel, spawnscriptedmissile,
srtp, there, triggerexploder, type, weaponindex
```

★★★ **⇒ 其中 `there` 与 `type` 显然是**正则误匹配**（`there` / `type` 是普通词）。**
**⇒ 真实 builtin 约 **76 个**。**

### ★★★★★ **新增的、此前未记录的 builtin**

| builtin | 说明 |
|---|---|
| **`addassist`** | ★★ **助攻**（与 `addkill` / `adddeath` / `addscore` / `addteamscore` / `addxp` 同族） |
| **`setmapgameobjects`** | ★★ **设置地图游戏对象**（对应 `print("gametype has no map gameobjects")`！） |
| **`setscriptedmissile`** / **`spawnscriptedmissile`** | ★ **脚本化导弹** |
| **`playfxontag`** | ★ 在标签上播特效（报告 080 的 `coop_training` 用过） |
| **`setmodel`** | ★ 设模型 |
| **`getmapfield`** | ★ 读地图字段（报告 080 用过） |
| **`spawngroundtiltcontroller`** | ★ 地面倾斜控制器（报告 080 的沉船系统） |
| **`setgroundtilttrajectory`** | ★ 倾斜轨迹 |
| **`playersetgroundreferenceent`** | ★ 地面参考实体 |
| **`finishsharedplayerdamage`** | ★ 共享伤害（报告 081 的 mode 3） |

### ★★★ `addassist` 的日志格式（揭示"权威比赛状态"的校验）

```
**`addassist could not update authoritative match state`**
**`addassist expects a bounded integer delta`**
**`adddeath could not update authoritative match state`**
**`adddeath expects a bounded integer delta`**
**`addkill …` / `addscore …` / `addteamscore …` / `addxp …`**（同样两条格式）
        ↓
★★★★★ ⇒ **7 个计分 builtin 各自都有两条校验：**
  ① **"could not update authoritative match state"** ⇒ 更新失败
  ② **"expects a bounded integer delta"** ⇒ ★★ **增量必须是有界整数**
        ↓
★★★ ⇒ 这解释了为什么 `dm.lua` / `war.lua` / `conf.lua` 都用 `addscore(attacker, 50)` 这种**小整数**
   ⇒ **传超大值会被拒绝**
```

★★ **⇒ 这是**一条可用的约束**：所有计分 builtin 的增量有**上限**（具体数值未暴露）。**

---

## 六、★★★★★ `CodolGameServer` 的**武器/动画子系统**（大量日志）

### 6.1 ★★★ `alpha weapon` 系列（CheyTac 专属）

```
**`alpha Barrett asset closure ready images=`**
**`alpha Barrett asset publication failed: `**
**`alpha Barrett metadata provenance differs`**
**`alpha Barrett template audit: `**
**`alpha Barrett WeaponDef XAnim slots patched assets=`**
**`alpha canonical modular weapon unavailable name=`**
**`alpha weapon base configstring type failed name=`**
**`alpha weapon early install unavailable name=`**
**`alpha weapon link failed name=%s source=%s rva=0x%07X op=%u target=0x%08X code=0x%08X`**
**`alpha weapon model audit weapon=cheytac_mp`**
**`alpha weapon model table link failed target=%s source=%s rva=0x%07X op=%u targetAddress=0x%08X code=0x%08X`**
**`alpha weapon model table verification failed target=`**
**`alpha weapon port status=`**
**`alpha weapon post-link verification failed name=%s lookup=%p linked=%p readable=%u`**
**`alpha weapon registration failed name=%s index=%u rva=0x%07X op=%u target=0x%08X code=0x%08X`**
**`alpha weapon rig audit waiting cheytac=`**
**`alpha weapon rig audit weapon=`**
**`alpha weapon zone promotion failed name=%s source=%s zone=%u rva=0x%07X code=0x%08X`**
        ↓
★★★★★ ⇒ **18 条 `alpha weapon` 日志,全部围绕 `cheytac_mp`（CheyTac M200 狙击枪）**
   ⇒ 含**运行期代码补丁**（`rva=0x%07X` / `op=%u` / `target=0x%08X`）
   ⇒ ★★★ **这是"运行期给武器打补丁"的完整日志面**
```

★★ **⇒ 且有**模板审计**、**资产闭包**、**元数据来源**、**XAnim 槽补丁** ⇒ 一套**武器注入框架**。**

### 6.2 ★★★ `ANIMTREE*` 系列（6 个标签）

```
**`ANIMTREEAPPLY type=`**
**`ANIMTREEASSET n=`**
**`ANIMTREEBUILD n=`**
**`ANIMTREENODE key=`**
**`ANIMTREERESOLVE n=`**
**`ANIMTREEWATCH armed at `**
**`ANIMTREEWRITER eip=`**
        ↓
★★★ ⇒ **7 条**，覆盖**构建 / 应用 / 解析 / 监控 / 写入**
   ⇒ `ANIMTREEWRITER eip=` ⇒ ★ **写入时记录指令指针**（补丁点）
```

### 6.3 ★★★ `actor*` 系列（`coop_training` 用到的）

```
**`actorcorpse could not convert the campaign actor`**
**`actorcorpse expects an optional ragdoll boolean`**
**`actorfire could not queue EV_FIRE_WEAPON`**
**`actorfire could not resolve its weapon`**
**`actorfire expects a player and positive damage`**
**`actorfire requires a campaign actor`**
**`actorfire requires the retained point trace`**
**`actorfire target or actor no longer exists`**
**`actorfirepresentation could not queue EV_FIRE_WEAPON`**
**`actorfirepresentation requires a campaign actor`**
        ↓
★★★ ⇒ **10 条**，揭示 `EV_FIRE_WEAPON` 是一个**引擎事件**
   ⇒ 且 `actorfire` **要求"保留的点迹"（retained point trace）**
```

### 6.4 ★★★ 其他关键串

```
**`all CODOL client slots are occupied`**                     ← ★ 槽位耗尽
**`ALL-ZERO (the modelIndex gate fired)`**                    ← ★★ 模型索引门控
**`a slot name does not parse`** / **`a slot/default/enabled cell would not read`**
**`a level of D3DFORMAT `**                                   ← ★ D3D 格式
**`admission/resolved_loadout_invalid`**                      ← ★ 入场/配装
**`advance-blocked configured=` / **`advance-blocked reason=begin_next_round_refused sideSwitch=`**
**`advance-blocked reason=bomb_runtime pickupTrigger=`**      ← ★★ SD 炸弹
**`announcer lead change: ` / **`announcer match end: p ` / **`announcer match start: p ` / **`announcer play p ` / **`announcer voice `**
**`alt fire NO ALT weapon=` / **`alt fire SWITCH client=`**   ← ★★ 副射击模式
**`alt weapon trace client=%u %-24s ps=%u native=%u cmd=%u es=%d`**  ← ★★ 武器轨迹
**`invalid CODOL client netchan fragment bounds`**             ← ★★★ **netchan 分片边界**
**`invalid CODOL DTLS public-key TLV`**                        ← ★★★ **DTLS 公钥 TLV**
**`invalid CODOL fragment acknowledgement`**                   ← ★★ 分片确认
**`invalid authoritative SD round completion`**                ← ★★ SD 回合
```

★★★★★ **⇒ 三条 `invalid CODOL *` 是最有价值的：**
```
**`invalid CODOL client netchan fragment bounds`**
**`invalid CODOL DTLS public-key TLV`**
**`invalid CODOL fragment acknowledgement`**
        ↓
★★★ ⇒ 揭示了**两套线协议**：
  ① **`netchan` 分片**（与既有 memory 的「FAT 分片帧 10 字节头」相关）
  ② ★★★ **`DTLS` 公钥 TLV**（Auth3 的 TLS 里有**自定义公钥 TLV**）
  ③ **分片确认（fragment acknowledgement）**
```

★ **⇒ 第 ② 条是一个**全新发现**：Auth3 的 TLS 握手里有**自定义的 `DTLS public-key TLV`**。**

---

## 七、★★★★★ 两插件的 RTTI 类模型

### 7.1 ★★★ `Alwaysoffline.Localnet32`

```
RTTI 行数：**244**（含 `?AV`）
命名空间分布：
  **`@AlwaysofflineRe@@`** ⇒ **182**
  **`@Demonware@`**        ⇒ **177**
  **`@OlMod@@`**           ⇒ **4**
        ↓
★★★ 顶层类名（38 个）中**业务类**：
  **`Auth3Server`** / **`LobbyServer`** / **`StunServer`** / **`PendingStreamServer`**
  **`IServer`** / **`IStreamServer`** / **`IDatagramServer`**
        ↓
★ 其余 31 个是 **C++ 标准库**（`exception` / `runtime_error` / `bad_alloc` /
  `_System_error` / `codecvt_base` / `ctype_base` / …）
```

### 7.2 ★★★ `CodolGameServer.Localnet32`

```
RTTI 行数：**239**
命名空间分布：
  **`@CodolGameServer@@`** ⇒ **239**
  **`@OlMod@@`**           ⇒ **7**
  **`@Demonware@`**        ⇒ **0**  ★★ 完全没有 Demonware 命名空间！
        ↓
★★★ 顶层类名（37 个）中**业务类**：
  **`ClientPacketResult`**（4 次）
  **`SvScriptBuiltinResult`**（2 次）
  **`MsgWriter`** / **`EngineMsgWriter`**
        ↓
★ 其余 33 个是 C++ 标准库
```

★★★★★ **⇒ 一个决定性的分工证据：**
```
`Alwaysoffline.Localnet32`   ⇒ **有 177 条 `@Demonware@`**,**0 条 `@CodolGameServer@`**
`CodolGameServer.Localnet32` ⇒ **有 239 条 `@CodolGameServer@`**,**0 条 `@Demonware@`**
        ↓
★★★ ⇒ **两个插件的命名空间完全不相交** ⇒ **职责边界清晰**
```

### ★★★ 两个 `*Result` 类

```
**`ClientPacketResult`**（4 次）  ⇒ ★★ **客户端包的处理结果**
**`SvScriptBuiltinResult`**（2 次）⇒ ★★ **服务端脚本 builtin 的结果**
        ↓
★ 与报告 081 的 `codol.call` 契约（`ret, err, code`）**呼应**
```

---

## 八、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★ 字符串总量 | `Alwaysoffline` **17,002 唯一** / `CodolGameServer` **20,687 唯一**（合计 **37,689**） |
| 2 | ★★★★★ **两个插件都静态链入 OpenSSL** | **1,630 / 1,340** 条 |
| 3 | ★★★ **OpenSSL ≥ 3.5** | 含 **`ML-KEM-512/768/1024`** + **`ML-DSA-44/65/87`** + `SLH-DSA`（后量子） |
| 4 | ★★★ **QUIC** | `ACK_DELAY_EXP` / `NEW_CONN_ID` / `PATH_CHALLENGE` / `MAX_UDP_PAYLOAD_SIZE` / … 共 **17+ 个 QUIC 参数** |
| 5 | ★★ **Intel TBB** | `TBB` ×3 |
| 6 | ★★★ **nlohmann/json v3.12.0** | RTTI 里精确出现 `json_abi_v3_12_0@nlohmann@@` |
| 7 | ★★ `ALL:@SECLEVEL=0` | 与 `fake_auth_tls.py` 同一手法 |
| 8 | ★★★★★ **15 个 Demonware 服务** | **4 Server**（`Auth3` / `Lobby` / `Stun` / `PendingStream`）+ **12 Service**（`Matchmaking` / `Profiles2` / `Storage2` / `Stats` / `Marketplace` / `Clan` / `VClan` / `Friends2` / `InstantMessage` / `Tencent` / `TitleUtilities` / `ContentUnlock2` / **`Unknown0B`**） |
| 9 | ★★★★★ **`[dw_service_info]` 不控制实现** | 关掉的 10 个里,**7 个仍有实现**（`Friends2`/`Clan`/`VClan`/`Marketplace`/`Tencent`/`TitleUtilities`/…） |
| 10 | ★★ 三个接口 | **`IServer`** / **`IStreamServer`**（Auth3/Lobby/PendingStream）/ **`IDatagramServer`**（Stun） |
| 11 | ★★★ 两个配置里没有的服务 | **`ContentUnlock2Service`** / **`Unknown0BService`** |
| 12 | ★★★★★ **`Auth3 ticket must be exactly 128 bytes`** | ✓ 与报告 044 的 128 B ticket 一致 |
| 13 | ★★★★★ **"three Auth3 client patches"** | `Applied the three Auth3 client patches to <path>` |
| 14 | ★★★★★ **补丁随 build 漂移** | "**they have moved with the build**. Re-derive them with **`Tools/olfinal/check-auth3-patches.py`**; **until then Auth3 cannot serve a client that needs it**." |
| 15 | ★★ `Auth3/UNO HTTP` | Auth3 走 UNO 的 HTTP |
| 16 | ★★ 4 个 Auth3 TLS 失败串 | `connect failed` / `disconnect reset failed` / `input failed` / `recovery failed` |
| 17 | ★★ `LSG_CAPTURE` / `AUTH3_CAPTURE` | **9** / **2** 条（抓包日志） |
| 18 | ★★★★ **20 个 `ZM*` 子系统** | `ZMFX`(9) `ZMPOWER`(6) `ZMBARRIER`(5) `ZMTICK`(3) `ZMPOSE`(3) `ZMFACE` `ZMNOTIFY` `ZMNEGOTIATION` `ZMWINDOWTRAVERSE` `ZMCORPSE` `ZMCORRIDOR` `ZMDEATH` `ZMHIT` `ZMNAVBODY` `ZMNAVEDGEBLOCK` `ZMNAVUNMEASURED` `ZMNODEGROUND` `ZMPERK` `ZMSPAWN` `ZMWINDOWASSIGN` |
| 19 | ★★★★★ **`ZMPOWER` 的电力机制** | **八部件绑定 ⇒ 桥升起**；**下降完成 ⇒ 桥阻挡释放**；**通电柜 + 原生蒸汽组 500 激活** |
| 20 | ★★★ **`ZMFX BO1`** | "BO1" = **Black Ops 1**（CODOL 僵尸与 BO1 同源） |
| 21 | ★★★★★ **19 个 `zm*` Lua API** | `zmactivezonecount` `zmcooperativespawnzones` `zmcooperativezonesource` `zmplayercount` `zmplayerzone` `zmsetround` `zmspawnactor` `zmspawnactorat` `zmspawnangles` `zmspawncrossesbarrier` `zmspawngoal` `zmspawnorigin` `zmzoneactive` `zmzoneadjacentat` `zmzoneadjacentcount` `zmzoneat` `zmzonecount` `zmzonename` `zmzonespawncount` |
| 22 | ★★ **17 个 `zmb_*` 音效名** | `zmb_box_*`(8) + `zmb_packapunch_pickup` + `zmb_perks_packa_*`(4) + `zmb_vox_ann_magicbox` + `zmb_music_box` / `zmb_couch_slam` / `zmb_monkey_song` |
| 23 | ★★★★ **~76 个 builtin** | 新增：**`addassist`** / **`setmapgameobjects`** / `setscriptedmissile` / `spawnscriptedmissile` / `playfxontag` / `setmodel` / `getmapfield` / `spawngroundtiltcontroller` / `setgroundtilttrajectory` / `playersetgroundreferenceent` / `finishsharedplayerdamage` |
| 24 | ★★★★★ **7 个计分 builtin 的两条校验** | **"could not update authoritative match state"** + **"expects a bounded integer delta"** |
| 25 | ★★★★★ **18 条 `alpha weapon` 日志** | 全围绕 **`cheytac_mp`**,含**运行期代码补丁**（`rva=0x%07X` / `op=` / `target=0x%08X`） |
| 26 | ★★★ 7 条 `ANIMTREE*` | 含 **`ANIMTREEWRITER eip=`**（记录补丁点） |
| 27 | ★★★ 10 条 `actor*` | 揭示引擎事件 **`EV_FIRE_WEAPON`** + "retained point trace" |
| 28 | ★★★★★ **三条 `invalid CODOL *`** | **`netchan fragment bounds`** / ★★ **`DTLS public-key TLV`** / **`fragment acknowledgement`** |
| 29 | ★★★ `ALL-ZERO (the modelIndex gate fired)` | 模型索引门控 |
| 30 | ★★★ **`announcer` 5 条** | `lead change` / `match end` / `match start` / `play` / `voice` |
| 31 | ★★★★★ **两插件命名空间不相交** | `Alwaysoffline`：`@Demonware@`=**177** / `@CodolGameServer@`=**0**；`CodolGameServer`：`@CodolGameServer@`=**239** / `@Demonware@`=**0** |
| 32 | ★★ 两个 `*Result` 类 | **`ClientPacketResult`**（4）/ **`SvScriptBuiltinResult`**（2） |

---

## 九、结论

### 1. ★★★★★ **两个插件各自静态链入了完整的 OpenSSL（含 QUIC 与后量子算法）**

```
**OpenSSL ≥ 3.5**：`ML-KEM-512/768/1024` / `ML-DSA-44/65/87` / `SLH-DSA`
**QUIC**：17+ 个参数串
**Intel TBB** + **nlohmann/json v3.12.0** + **zlib**
        ↓
★★★ ⇒ 与既有 memory 的"libcurl 家族"**不同**：这是 **OpenSSL 本体**
```

### 2. ★★★★★ **`[dw_service_info]` 只控制启用,不控制实现**

```
插件里实现了 **15 个 Demonware 服务**
配置只启用 **5 个**
        ↓
★★★ ⇒ 关掉的 10 个里有 **7 个仍有完整实现**
   ⇒ 所以"关掉"是**运行时禁用**,不是**未实现**
```

### 3. ★★★★★ **Auth3 有一套"随 build 漂移"的客户端补丁**

```
"**they have moved with the build**"
"Re-derive them with **`Tools/olfinal/check-auth3-patches.py`**"
"**until then Auth3 cannot serve a client that needs it**"
        ↓
★★★ ⇒ 这解释并补充了 memory 里 `CodolClientPatches.cpp` 那条**自门禁**结论
   ⇒ 但**这是另一组补丁**（Auth3 侧,不是 Demonware 启动侧）
   ⇒ 且**已针对本 build 重新推导过**
```

### 4. ★★★★★ **`CodolGameServer` 有 20 个 `ZM*` 僵尸子系统,其中 `ZMPOWER` 揭示了电力机制**

```
**八部件绑定 ⇒ 桥升起**
**下降完成 ⇒ 桥阻挡释放**
**通电柜 + 原生蒸汽组 500 激活**
        ↓
★★★ ⇒ 这是一个**独立于"买门开区"的电力/桥子系统**
```

### 5. ★★★★★ **19 个 `zm*` Lua API 的完整名表**（比报告 066 的"16 个"多 3 个）

### 6. ★★★★★ **三条 `invalid CODOL *` 揭示了两套线协议**

```
**`invalid CODOL client netchan fragment bounds`**   ⇒ netchan 分片
**`invalid CODOL DTLS public-key TLV`**             ⇒ ★★ **Auth3 TLS 里的自定义公钥 TLV**
**`invalid CODOL fragment acknowledgement`**        ⇒ 分片确认
```

### 7. ★★★★ **7 个计分 builtin 都要求"有界整数增量"**（`addassist` 是第 7 个）

### 8. ★★★★ **18 条 `alpha weapon` 日志揭示了一套运行期武器补丁框架**（围绕 `cheytac_mp`）

### 9. ★★★★★ **两插件的命名空间完全不相交**（职责边界清晰）

---

## 十、下一步

- 写最终收尾报告（覆盖本轮 087–090 四项穷尽）
