# 150 · 奖章横幅、使用对象、脚本源加载、alpha 武器端口

## 一、范围

本报告完整学习 **4 个文件**：

- `sv_splash_mp.hpp`（150 行）
- `sv_use_object_mp.hpp`（109 行）
- `sv_script_source_mp.hpp`（61 行）
- `sv_alpha_weapon_port_mp.hpp`（前 98 行）

`server_mp` 进度推进到 **131/154**。

## 二、奖章横幅：一次"行号用错 build"的活故障

### 2.1 命令格式

```text
w <slot> <row> <points>
```

`CG_ServerCommand` 的 `'w'` 走到 `sub_C1C860`，按**行**索引 `mp/splashTable.csv`，从**第 4 列**读显示时长、**第 11 列**读图标，存进五个同时显示槽之一。

### 2.2 那段被更正的注释

> 下面的行号**每一行都是本 build 的**。它们从 OLfinal 自己的随包 `mp/splashTable.csv` 读出——**619 行 × 14 列**，放在 `re/demo-re/splashtable-olfinal/`，解析在旁边的 .txt 里——从 `code_post_gfx_mp.ff` 提取（它既不在 `common_mp.ff` 也不在 `common_gametype_mp.ff`）。
>
> **这些行号以前是 3.3.3.3 的，那是一个活 bug。** 本头文件此前携带 3.3.3.3 的编号，并注释断言它是"本 build 的"。**在 OLfinal 上第 32 行是 `SPLASHES_MULTIKILL`，所以本项目打过的每一场比赛里的每一次 first blood 都显示 MULTIKILL 横幅。** 什么都抓不到它：线形良好、横幅也画出来了。

### 2.3 "横幅是奖章，不是击杀"

零售 dm demo 十分钟发 20 个，而对 28 次击杀——**每一个都命名一枚奖章**：

| 命令 | 名字 | 次数 |
|---|---|---:|
| `w 0 12 0` | round_start | 1（2.6 s 处） |
| `w 0 16 50` | SPLASHES_HEADSHOT | 4 |
| `w 0 18 0` | SPLASHES_LONGSHOT | 2 |
| `w 0 29 50` | SPLASHES_REVENGE | 5 |
| `w 0 34 100` | SPLASHES_BUZZKILL | 4 |
| `w 0 38 0` | SPLASHES_FIRST_PLACE_KILL | 3 |
| `w 0 406 0` | destroyed_uav | 1 |

> 把 `w 0 <row> 50` 读成"一次击杀"正是让击杀音看起来错的原因：28 次 `mp_hit_kill` 播放对"8 个击杀横幅"是 28 次击杀对 **9 枚奖章**，两个数字从来不可比。

### 2.4 槽位

- 槽 0 = 玩家自己的横幅（默认）；
- 槽 2 = 播报/呼叫行，**不是**玩家横幅。demo 发 `w 2 4 0`（announcer_line）、`w 2 368 0`（used_strike_helicopter）、`w 2 392 0`、`w 2 393 0`——全是全场比赛事件，全 0 分。`sub_C1C860` 把槽钳到 0..4。
- 行 4 `announcer_line` 在表里**每一列都是空的**——无文字、无图标、无声音。它是播报员在下面说话时的横幅，**不是播报员本身**：demo 把全部十四次 `w 2 4 0` 与同一帧的高带 `p` 配对，而没有横幅的三次正是连杀呼叫。

### 2.5 已接线的四枚 + 一个诚实的例外

| 常量 | 行 | 分数 |
|---|---:|---:|
| SvSplashHeadshot | 16 | 50 |
| SvSplashRevenge | 29 | 50 |
| SvSplashFirstBlood | 33 | **0** |
| SvSplashFirstPlaceKill | 38 | 0 |

first blood 的 0 是唯一**没有测量支撑**的值：

> demo 里没有出现 first blood——录制者没拿到——所以它的分值是没有测量支撑的那一个。0 与 demo 发的其它每一枚无加成奖章一致，且**是记分板上不可能出错的值**。

### 2.6 队列：每 1500 ms 一枚

`sub_C1C860` 每个显示槽只存一个横幅，所以同帧发两个 ⇒ 第二个在第一个画出前就覆盖它。

实测：dm demo 里两个槽 0 横幅之间的最小间隔**正好 1500 ms**，出现四次，从不更小——而且**三次连发是同一次击杀的几枚奖章**，间隔正好是它：

```text
t=143000 REVENGE(50) -> t=144500 BUZZKILL(100) -> t=146000 FIRSTPLACE(0)
t=236400 BUZZKILL    -> t=237900 FIRSTPLACE
t=513400 BUZZKILL    -> t=514900 LONGSHOT
```

> 所以零售服务器不决定显示哪枚奖章——它**全部显示、按顺序**，而队列才是让这件事可见的东西。

`SvSplashQueueLimit = 8`，注释："超过这个就丢弃**并说出来**——静默截断的队列读起来像一枚从未被授予的奖章。"

### 2.7 分数是横幅的不是记分板的

> 零售既显示也授予加成；本服务器显示它，而 dm.lua 不加，所以爆头在横幅里读 "+50" 而记分板只动了击杀的 50。**发 0 会是更小的谎、更大的偏离**，所以发 demo 的值，并在这里点名接缝：加成属于 dm.lua，计分住在那里。

### 2.8 未接线的六项，每一项都写明了缺什么

```text
30 DOUBLEKILL / 31 TRIPLEKILL / 32 MULTIKILL —— 需要"多杀窗口"
```

这里的注释是一次**反驳而不是取值**：

> 实测：零售 dm 比赛里**零**个多杀横幅，而它唯一一对间隔小于四秒的击杀——t=240600 与 t=242800，2200 ms——只产生了 REVENGE，别无他物。所以**本 build 不用 IW 系列已知的 4000 ms 窗口；它小于 2200 ms，或者根本不是纯时间窗口。** 因为是 CoD 惯例就搬 4 秒会是错的，而 build 里没有任何东西会说出来。

其余五项：18 LONGSHOT（距离阈值）、34 BUZZKILL（连杀长度）、20 AVENGER / 22 DEFENDER（时间窗内的成对伤害史）、406 与槽 2 呼叫（本服务器还不生成的连杀实体）。

### 2.9 命中部位：两次"settled"，一次记录在案的异常

**已钉死（§51g）**：名字表 19 项——none/helmet/head/neck/torso_upper/torso_lower/arm、hand、leg、foot 各对/gun——out.exe（`0x00E4FB30`、`0x00E5AFB0`）与 3.3.3.3（`0x00CD83B8`、`0x00CDF3C8`）内容与顺序相同。旧注释说这块"没有 head 条目所以选一个就是猜"，**那是把原始字符串块当表读**，正是 §51g 要记录的陷阱。

**也已钉死（活体实测）**：`SvPlayerDamagePayload::hitLocation` 是 trace 的 part group，而 §51h 留了个问题：partGroup 是不是名字索引（`BulletShieldPartGroup = 19`，恰好在 19 个名字之后一格）。一场实打实的比赛回答了它：

```text
17 次击杀，part group 2(×11)、5(×3)、4(×2)、6(×1)
每次都和同一根骨头配对，且玩家报告 HEADSHOT 奖章正确触发
⇒ partGroup 2 就是 head，名字表的顺序就是 part-group 顺序
```

**仍然奇怪且不属于本常量**：

> 17 次击杀里 11 次读作 head，对两个拿步枪的玩家来说是高比率。这里**记录它而不是解释它**——见关于缩放 broadphase 的 gentity 短字的 locational-hitbox 注释。它不影响奖章，奖章是对的。

## 三、使用对象：严格大于的去重与事件顺序

```text
UserCmdButtonActivate = 0x00000008
```

四种定义：

- `ownerTeam` + `allowedRelation`（Any/Friendly/Enemy）；
- `useDurationMilliseconds`；
- `requiresKeyObject`。

候选 `SvUseObjectCandidate{ objectId, insideTrigger, hasKeyObject }`。

事件三态 `Begin / Cancel / Complete`，带 `commandTime` 与 `elapsedMilliseconds`。

`SvUseObjectSystem` 四个内部表：

- `definitions_`；
- `clientProgress_`（每客户端一个进行中的对象）；
- `objectClaimants_`（每对象一个占用者）；
- `lastCommandTimes_`（去重用）。

`claimantForObject(objectId)` 暴露给外部判断"这个目标被谁占着"。

## 四、脚本源加载：三级回退与四类错误

```text
InvalidSelection / NoSource / ReadFailed / SourceTooLarge
```

`SV_LoadGameplaySource(scriptRoot, mapName, gameType, maxBytes=1 MiB)` 产出 `SvGameplaySource{ sourceName, source, files[] }`。

`SV_IsValidGameplaySourceSelection(value)` 先校验选择字符串本身。

`SvMapScriptMetadata{ miniMapMaterial }` 独立加载，注释解释了为什么它的字节上限与 gameplay 源相同（1 MiB）：

> 元数据执行有独立的分配器与指令上限，但**战役地图块还携带实测的运动表**。让字节上限与 gameplay 源一致，这样那些地图能到达它们的早期元数据返回，而不是在文件大小预检上失败。

## 五、alpha 武器端口

`SvAlphaWeaponTuning` 携带 21 个字段，注释强调准入门：

> 只包含**alpha 偏移有具名 C1 消费者**（或明确加括号的 penetrate 字段）**且** OLfinal 目标已被独立恢复的字段。带指针的模型、材质、动画和声音**不穿过这个结构**。

`HitLocationCount = 21`（与前一份报告一致，仍标注未定）。

`SvAlphaWeaponLineage` 四类：

```text
MeasuredDescendant        实测后代
CompatibilityAlias        兼容别名
ConvertedPresentation     转换后的表现
MissingModelFamily        缺失模型族
```

`OlfinalWeaponDefSize = 0x101C`：`DB_SizeofXAsset<WeaponDef> 0x4834B0` 返回该值，`DB_LinkXAssetEntry 0x49DA10` 通过 type-28 尺寸分派**精确拷这么多字节**。

`AlphaWeaponNetworkBaseIndex = 1224`：

> OLfinal 随包的普通武器表止于 1223。客户端 alpha 安装器在解析第一个模块化武器**之前按声明顺序**追加这个目录，所以这些是可能过线的基索引。**一个专用的地图重置按不同顺序重建它自己的私有注册表；调用方必须把匹配的 alpha 名翻回这个索引，而不是把那个进程局部槽暴露给客户端。**

`SV_StringTableHash`（`0x76B7C0`）：StringTable 单元格在文本指针旁边缓存这个小写多项式哈希——**别名模型表必须同时更新第零列的两半**。

`SV_PatchAlphaWeaponDefinition(definition, persistentNameAddress, tuning)`：

> 已从 OLfinal WeaponDef 拷过来的克隆字节**原地**打补丁。`persistentNameAddress` 必须指向在结果 DB 条目存续期间活着的存储；保留链接器复制结构但**刻意保持其带指针成员浅层**。

## 六、关键结论

1. **表行号也是"按 build 变的常量"**，和 MOD 表、configstring 一样。行号用错不会报错——横幅照样画，只是画错的那个。
2. **"多杀窗口"是一次实测反驳**：零售本 build 里零个多杀横幅，唯一一对 2200 ms 相邻击杀只出了 REVENGE ⇒ 窗口 < 2200 ms 或根本不是纯时间窗。**不搬 CoD 惯例的 4 秒**。
3. **队列是让"一次击杀几枚奖章"可见的机制**，不是去重机制；1500 ms 是实测最小间隔。
4. **0 分是最不可能在记分板上出错的值**，用于无测量支撑的情况。
5. **alpha 武器的网络索引是 1224 起的连续段**，而进程内注册表顺序不同 ⇒ 必须双向翻译，不能直接暴露。

## 七、未闭合点

- 多杀窗口的真实判据未知（只知道 < 2200 ms 或非线性）。
- LONGSHOT 距离阈值、BUZZKILL 连杀长度、AVENGER/DEFENDER 的成对伤害窗口全部未取。
- 17 次击杀里 11 次判为 head 的比率偏高，记录而未解释。
- `HitLocationCount = 21` 仍待从原生 WeaponDef 数组真长确认。
