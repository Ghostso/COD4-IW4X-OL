# 148 · 实体池/尸体环、const baseline 表、Lua 运行时、出生配置、脚本内建、触碰

## 一、范围

本报告完整学习 **7 个文件**：

- `sv_entity_mp.hpp`（297 行，实体池与尸体环）
- `sv_const_baselines_mp.hpp`（228 行，const baseline 全表结构）
- `sv_script_lua_mp.hpp`（89 行）
- `sv_client_spawn_mp.hpp`（63 行）
- `sv_script_builtin_mp.hpp`（前 160 行）
- `sv_client_impacts_mp.hpp`（97 行）

`server_mp` 进度推进到 **123/154**。

## 二、尸体环：8 → 18，以及一条 compile-time 不变量

### 2.1 四个数字

```text
EntityNumWorld                 = 2046
EntityNumNone                  = 2047
FirstPlayerCorpseEntityNum     = 19
PlayerCorpseRingSize           = 18
FirstDynamicServerEntityNum    = 37
```

静态断言钉死：

```cpp
static_assert(FirstPlayerCorpseEntityNum + PlayerCorpseRingSize ==
              FirstDynamicServerEntityNum);
```

注释解释了为什么用 `==` 而不是 `<=`：

> 钉住环到间隙，而不是给它上界。`<=` 对任何小于等于真实环的值都会通过，**而这正是继承常量出错的方向**。

### 2.2 为什么尸体号必须是 19..36

`CG` 的访问器 `sub_BB9EE0` 做 `globals + 952 * entityState->number + 639904`——**没有减法、没有边界检查**（IW3 减 64 并断言，而零售构建把断言编译掉了）。

> 从动态 FIFO 分配尸体产生了实体 396，它在该数组后写了 396*952 字节并让客户端崩溃。

### 2.3 18 是本 build 的实测值，不是 3.3.3.3 的 8

```text
MEASURED 本 build 自己的零售流量，离线，6160/6160 快照全解码无失步：
    ET_PLAYER          1..8      那场比赛的八名玩家
    ET_PLAYER_CORPSE   19..36    连续，18 个不同号
    其它一切           37..750   其中最低的正好是 37
```

复用 3.3.3.3 的 8 的代价写在注释里：

> 本服务器会把动态实体号 27..36 交出去，**而客户端会把它当尸体存**——`sub_BB9EE0` 按实体号索引 corpseinfo，无减法无边界检查——而且它会在八具尸体之后回收槽位，而零售用十八个。

18 也正好是本 build 的客户端槽数（`ServerCharacterInfoSlotCount`、`0xAF350 + 18*0x450` 里的 18、大厅上报的房间容量）。

注释还明确降级了 3.3.3.3 的四条推导：

> 上面那四条是 3.3.3.3 的、从未在这里重跑：out.exe 的 `0x004E8460` 是 dvar 注册不是 `G_RunCorpseAnimate`，所以 corpseinfo 边界、池步长和 `es.number < 19` 字面量在本 build 上都是未校验的。**demo 一条都不需要。**

## 三、尸体的四个标志与两个轨迹类型

| 常量 | 值 | 含义 |
|---|---:|---|
| `SvCorpseReinitialiseFlag` | **0x80000** | eFlags 里=需要重建 |
| `SvCorpseSpawnFlags` | **0xA0000** | 生成时 |
| `SvDeadPlayerHiddenFlag` | **0x20000** | 玩家实体上=跳过整个 per-client 动画状态初始化 |
| `SvCorpseSpawnTrajectoryType` | 1 | 生成时 trType |
| `SvCorpseRagdollTrajectoryType` | **9** | 本 build 的 ragdoll |
| `SvCorpseRagdollAngleTrajectoryType` | 10 | apos 用 |
| `SvCorpseRagdollDelayMilliseconds` | 1000 | 沉降→ragdoll |

### 3.1 代码里自己更正了两个此前的结论

> **门是 0x80000，不是 0x200000。** 这个标志没有两位移位。ida `0x00BB86BD` 处的 0x200000 测试是 `sub_BB8050` 里一个无关标志，把它读成尸体位是一次误归因——**这也意味着 dm demo 的 0xA0206 一直是对的，而"修正"成 0x280000 弄坏了一个能工作的值。**
>
> **populator 确实存在**：`sub_BB9F70`。它被漏掉是因为它在基址 1455144 写 corpseinfo，而访问器 `sub_BB9EE0` 用的是 639904——**同一个结构在第二个数组里**——所以扫一个基址就得出"从没有人填充它"，这是假的。

### 3.2 `SvDeadPlayerHiddenFlag (0x20000)` 的作用

实测：活玩家 eFlags 是 2 或 0，死亡是 `0x20002`，在归档的三秒里恒定。

客户端 `sub_BB89E0` 在该位设置时**跳过整个 per-client 动画状态初始化**（XAnim 设置、lerp 重置、两个 0x40 memset）：

```text
v5 = 952 * centity[99] + base + 1433256;   // per-client anim state
if ( (centity[62] & 0x20000) == 0 )        // centity+0xF8 = es.eFlags
{ ...initialise... }
```

> 这是 IW 的 `EF_DEAD` 行为：客户端停止呈现玩家实体，因为**尸体应该接手**，所以在玩家实体上留着这一位意味着玩家实体本身不再被画——**如果没有尸体接手，这就是"敌人凭空消失"的症状**。

这一位留在 playerState 里（pmove 需要它），**只从上线走的 entityState 里遮蔽掉，且只在死亡动画被保持期间**。

### 3.3 ragdoll 值 13 在本 build 不存在

```text
demo 的 ragdoll 值是 13，而那个值在本 build 里不存在。
CODRED(bg_evaluate_trajectory) sub_AB29C0 对 trType 分支只处理 0..12；
其它一切落到 Com_Error(2, "90 %i", trType)
—— 这就是发 13 之后第一次击杀时活客户端弹出的错误对话框。
```

> 把 demo 常量直接跨 build 搬过来正是本项目反复踩的坑：**demo 给对的是形状，给错的是数字**。
>
> 9 是本 build 的 ragdoll 类型。它的 switch 把 case 9 与 0、1、12 归为"保持位置"，这正是客户端模拟 ragdoll 需要服务端做的；而 IW3 把 9 命名为 `TR_RAGDOLL`/`TR_FIRST_RAGDOLL`，10 是 `TR_RAGDOLL_GRAVITY`——也就是 demo 与它配对的 apos 值，**而且本 build 的 switch 确实接受它**，这就是为什么 aprType 10 从未报错。

### 3.4 沉降与重生**必须**错开——一条只能在编译期守的不变量

五步链条（全部从客户端镜像证明）：

1. `respawnTime = serverTime + max(deathAnimMs,1)`；`clearReinitTime = serverTime + max(deathAnimMs,50)`——**表达式相同 ⇒ 同一服务端帧触发**；
2. 那一帧客户端更新重生玩家的 clientInfo：`CG_UpdateCharacterModelsFromClientInfo 0x0051BC80` 在 modelIndex 为零时**清除全部十个角色模型槽**；
3. 尸体的 eFlags 在同一帧变化，重新触发 `CG_ResetEntity sub_BBAD90 case 2`，它调 `CG_CopyCorpseInfo sub_BB9F70` 把**刚被清空的 clientinfo 拷进 corpseinfo**；
4. `BG_UpdatePlayerDObj 0x0040B700` 开头是 `if (!*(_DWORD*)a5 || !**(_BYTE**)(a5+24))`（`!valid || !model[0]`），在这个分支上**释放 DObj**；
5. 之后没有任何东西再拷 corpseinfo——该数组在整个镜像里只有三处代码引用且全是读/拷路径——**所以尸体再也不回来**。

> 零售从不撞上这个。它的沉降在**尸体生成后** 1.4..2.9 s（约 18 条 dm demo 尸体生命实测），而重生是另一个 gametype 计时器，所以两者永不同帧——这就是零售尸体熬过其主人的重生、活到约 80 s 直到槽位被复用的原因。

`SvCorpseSettleRespawnSeparationMs = 250`，且附一条 static_assert，注释说：

> **没有任何服务端测试能抓到这里的回归**：伤害发生在客户端，它在拷贝了被清空的 clientinfo 后释放尸体 DObj，而服务端自己的快照里仍有一具完全有效的尸体。所以这条不变量改在编译期强制——把分离量归零会静默恢复"身体一沉降就消失"。

## 四、实体池：reserve 存在的理由

```cpp
bool reserve(std::uint32_t entityNum);
```

注释：

> 零售的静态地图实体**不占连续区间**：factory 的是 37, 42..46, 48, 53, 55, 56, 59..——而客户端**按号**解析 `cl.entityBaselines`（快照标志 0x10）。一个动态实体如果拿到 42，就会继承那个槽的 origin、model 和 solid，**所以地图 const-baseline 表点名的每一个号都必须从 `spawn()` 的可及范围里抽走，无论那个号上是否真的发布了静态实体。**
>
> 保留槽只能通过 `spawnAt` 访问，永不进入空闲链表。在第一次 spawn 前调用；`reset()` 清除全部保留。

`spawnAt` 只接受"已保留且未使用"的槽——"拿一个任意号会让静态实体落到顺序分配已经许给别人的槽上"。

`rollbackFree(handle, previousLifetime)`：只在非保留的 FIFO 槽上可用。

## 五、const baseline：编号就是身份

### 5.1 来源

每个地图在 `<map>.ff` 旁边带一个 `<map>_const.ff`，内含一个 rawfile：`mp/constbaselines/bl_pc_<map>_<gametype>.bin`。它是**完整的 280 字节 entityState_t 记录数组**——客户端在地图加载时读（`sub_515340 → sub_6613E0`），按实体号索引进 `dword_77CE488`，并对任何带快照标志 0x10 到达的实体解析它（`sub_470F60`）。

> **所以实体号就是身份**：把门发布到错误的号上，客户端会给它一个无关实体的 origin、model 和 solid。本项目花了很久试图通过遍历地图实体串来复现编号，**卡在 288/397**——因为间隙编码了哪些实体占槽，这从实体列表本身是不可恢复的。

### 5.2 记录字段（为什么连轨迹都要带）

```text
entityNum / eType / brushModelIndex (`*N`) / xmodelIndex
solid / eFlags
originBits[3] / anglesBits[3] / scaleBits    ← 浮点存原始位模式
field0058 / field00E4 / field0098 / field0070
positionTrajectoryType / angleTrajectoryType
positionTrajectoryTime / Duration / DeltaBits[3]
angleTrajectoryTime / Duration / DeltaBits[3]
surfType
```

浮点用位模式而不是十进制字面量的原因：

> 这些要与服务端自己的地图解析做**精确相等**比较来决定某个字段到底发不发，而有损地穿过十进制字面量会把一个安静实体变成一个话痨实体。

**轨迹那一段是"未建模字段开始有害"的地方**：

> 发布在表号上的实体会继承服务端不覆盖的每一个字段，而服务端只能覆盖它**建模**的东西。漏掉这些意味着一个道具可能从它的行里拿到一个速度（`pos.trDelta`）和一个角速度（`apos.trDelta`）并悄悄漂移旋转。**factory 的 script-model 行里有六条正是这样——实体 475..480，电击臂，trType 1，delta 像 (-141,0,-79) 和一个 -180 自旋。**

### 5.3 表按 (地图, 模式) 成对键

> 一张 zm 地图只有一个模式，所以地图单独就是唯一键，这里原先只收一个地图。**mp_nuked 有十三张表，`dd` 排在第一个**，所以只按地图查会给一个死亡竞赛服务器**支配模式**的实体编号——而编号就是身份：发布在错号上的门在客户端变成另一个实体的 origin、model 和 solid。**当配对未知时回退到该地图的第一张表**，这正是单模式地图想要的。

### 5.4 slot 0 不可达，且这是客户端的性质

```text
索引数组 dword_77CE488 是零填充的，sub_470F60 的守卫是 v2 > 0
⇒ "槽 0" 与 "不在表里" 在那里是同一个答案，实体回退到零结构
factory 的槽 0 是实体 37——retail demo 也确实显示它以 eType 0 到达，而文件写的是 6
在这里返回真实记录会让本服务器成为两边中唯一使用它的那个
```

所以 `SV_ConstBaselineEntityState` 从 slot 1 开始扫。

### 5.5 script_model 的键是**原点**

brush model 有 `*N` 可键；script_model 没有，所以键是原点——两边从同一个地图实体串解析出来，所以 float32 **逐位相同**而不只是接近。

> factory 的 134 条可达 script-model 行里有 126 条单凭原点就唯一。其余 8 条是**同位置对**，只差 xmodel（391/392 与 389/390——处于同一位置的道具），所以 `xmodelIndex` 在**本服务器的模型 configstring 带与零售一致时**能打破平局。它可能不一致，这就是为什么平局失败返回空而不是猜：**放到错号上的实体会继承陌生人的基线，而顺序编号只是多花线字节。**

`SV_ConstBaselineScriptModelRowByOrigin` 的用途注释写得很妙：

> 用于**测量**本服务器的模型 configstring 带与零售的差异：一个只有一个候选行的道具不需要破平局，所以两个 modelIndex 就构成两个带之间偏移的一次干净观测。

## 六、Lua 运行时：限额与所有权

```text
maximumMemoryBytes          8 MiB
maximumInstructionsPerRun   1,000,000
instructionHookInterval     1,000
maximumSourceBytes          1 MiB
maximumScheduledThreads     256
maximumThreadResumesPerFrame 64
```

`SvLuaRuntime` 不可拷贝不可移动（`unique_ptr<Impl>`），四个入口：`reload` / `dispatchWorldEvents` / `dispatchTouchNotifications` / `advance`。

日志分四级：`Info/Error` × `Print/CompileError/RuntimeError/HostError`，带 `generation`、`sourceName`、`message`、`traceback`。

## 七、出生配置：为什么 unarmed 是 flag 不是空 loadout

```cpp
bool unarmed{};
std::uint16_t unarmedWeaponAssetIndex{};
```

> 大逃杀什么都不给你——零售 BattleCity 影像显示空 HUD 和光手直到第一个箱子——所以解析出的 loadout 照常校验，然后**刻意不装备**。
>
> **它是出生标志而不是空 loadout**，因为准入（`SV_ClientSpawn`）和装备（`equipResolvedLoadout`）都会先跑 `SV_IsResolvedLoadoutValid`：没有武器的 loadout 在它能表达任何意思之前就被拒绝，**而这个拒绝读起来像一个坏了的职业选择**。

`unarmedWeaponAssetIndex`：

> 武器索引 0 没有视模型，所以无武器出生**根本不画手臂**——第一个 unarmed 构建看起来就是那样，而这不是零售的做法：BattleCity 影像显示光着的戴手套的手。客户端把"什么都没装"建模成一把真武器 `dmz_empty_mp`，这个字段携带它的索引。**零保留"无视模型"行为，所以一个未解析的名字是降级而不是失败。**

默认值：gravity 800、speed 190、moveSpeedScaleMultiplier 1.0、maxHealth 100。

`failureReason` 参数的理由：

> 四个返回**曾**都是不带限定的 `return false` 进一个没有 else 分支的调用方，所以"不能发生的出生"与"没人请求的出生"无法区分——**对玩家来说，选职业就是什么都不发生。**

## 八、脚本内建注册表

`SvScriptValue` 是 variant：`monostate / bool / int64 / double / string / SvScriptVector / SvScriptObjectRef / SvScriptObjectArray`。

`SvScriptBuiltinErrorCode` 十四项：UnknownBuiltin、InvalidArgumentCount/Type/Value、MissingSelf、InvalidSelf、ObjectNotFound、InvalidObjectState、WeaponNotOwned、InvalidAmmoState、WorldMutationFailed、DeathTransitionUnavailable、MatchStateUnavailable。

`MatchScoreCallbacks` 里有三个值得单说的：

1. **`addKillForClient`** 与 `addClientScore` 分开："无队模式的得分限制读的计数器，与显示分保持距离，理由与 cha 把队伍分与之分开相同：**它们在不同单位里。**"
2. **`addDeathForClient` / `addAssistForClient`**（刀AB）：
   > `deaths`/`assists` 在计分板里**本来就有位置**（`FieldDeaths=70`、`FieldAssists=67`），底层 `addClientDeaths`/`addClientAssists` **也早已实现**——**唯独没暴露给 gametype 脚本**，所以 cha/sd/spy 的这两列一直是 0。
3. **`playSoundForClient`**（刀BP）：专属击杀音只能在 Lua 里按 `event.weapon_name` 判定，因为 C++ 播 `p` 的 `projectClientHudElems` 拿不到武器名。
4. **`isBotClient`**：击杀特效表按**击杀武器**键控，所以 bot 击杀会播玩家的装饰性死亡效果——操作员要求 bot 不触发武器专属击杀效果。

`MissionCallbacks` 三个：`sendServerCommand` / `setConfigString` / `finishMission`。注释：

> 保留这个所有权边界，而不是让 world 学会网络客户端或比赛编排。

## 九、触碰（client impacts）

- `SvClientImpactBatch`：32 项 `targetEntityNums` + `unresolvedEntityCount`；
- `SvClientImpactCallbackBatch`：**64** 个（每个 touch 两次回调）；
- `SvClientImpactScriptNotificationBatch`：**64** 个。

回调顺序：

> BO1/Ghosts 先 target 后 source，而 BO2 先 source 后 target。CODOL 保留 32-touch 的 pmove 输入布局，但**不保留服务端回调所有者**，所以顺序保持显式。`TODO(CODOL)`：一旦恢复 CODOL 服务端回调顺序证据或等价权威脚本契约就删掉这个策略选择。

## 十、关键结论

1. **尸体号不是可自由选的**：客户端按实体号索引 corpseinfo，无减法无检查 ⇒ 19..36 是硬约束，且必须恰好填满到 37。
2. **沉降/重生同帧会在客户端永久毁掉尸体**，而服务端快照里一切正常 ⇒ 只能用编译期不变量守。
3. **跨 build 搬 demo 常量的正确姿势**：形状可以照搬，数字必须按本 build 的 switch 重验（ragdoll 13 → 9）。
4. **const baseline 让编号成为身份**：错号 = 继承别人的 origin/model/solid；表必须带轨迹字段，否则道具会漂移自旋。
5. **空 loadout 表达不了"光手"**，因为它先被 loadout 校验拒绝；必须用独立 flag + `dmz_empty_mp`。
6. **"字段存在、底层实现了、就是没接出来"** 在 `deaths`/`assists` 上又出现了一次。

## 十一、未闭合点

- 3.3.3.3 的四条尸体推导在本 build 上未复跑（`0x004E8460` 是 dvar 注册）。
- 尸体路径在运行时是否**被到达**仍由 TODO 跟踪。
- 没有 `_const.ff` 提取表的地图只能顺序编号（9/13 张 nuked 表、未解析的 .ifs）。
- `SvClientImpactCallbackOrder` 是策略选择而非测得的 CODOL 行为。
- script_model 的 xmodel 破平局依赖本服务器模型带与零售一致，而这一点尚未确立。
