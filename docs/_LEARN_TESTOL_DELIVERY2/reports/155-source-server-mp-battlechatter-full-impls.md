# 155 · 战场语音（续）与三处实现：断言的写法、爆炸实体的自证、使用对象的顺序

## 一、范围

本报告学习 **4 处**：

- `sv_battlechatter_mp.hpp` 后段（80–247 行）
- `sv_grenade_explosion_mp.cpp`（42 行，完整）
- `sv_use_object_mp.cpp` 前段（120 行）
- `sv_splash_mp.cpp`（15 行，完整）

`server_mp` 进度推进到 **149/154**。

## 二、断言查的是**公式**，不是复述结论

```cpp
static_assert(SvBattleChatterParameter(Tf, true,  ReloadingGeneric) == 1683, "uk_f1_inform_reloading_generic");
static_assert(SvBattleChatterParameter(Tf, false, ReloadingGeneric) == 1787, "uk_m1_inform_reloading_generic");
static_assert(SvBattleChatterParameter(Sc, true,  ReloadingGeneric) == 956,  "ab_f1_inform_reloading_generic");
static_assert(SvBattleChatterParameter(Sc, false, ReloadingGeneric) == 1060, "ab_m1_inform_reloading_generic");
static_assert(SvBattleChatterParameter(Tf, true,  KillfirmInfantry) == 1681, "uk_f1_inform_killfirm_infantry");
static_assert(SvBattleChatterParameter(Tf, true,  AttackFlashbang)   == 1674, "uk_f1_inform_attack_flashbang");
```

注释：

> **实测的，直接来自 `localized_common_mp` 的 `ncs_snd` 表。** 每一个都在上面的算术写出来之前，由 `name-announcers.py` 按名字打印过，所以这些断言**检查的是公式而不是复述它**。

六条断言用了**两个阵营 × 两个性别 × 三条不同行**的交叉组合，而不是重复同一点六次——这样 `base`、`stride`、`gender offset`、`line index` 四个自由度各自被约束。

验算：`Tf female = 1674`，`ReloadingGeneric = 9` ⇒ 1683 ✓；`male = 1674 + 104 = 1778`，+9 ⇒ 1787 ✓；`Sc female = 947`，+9 ⇒ 956 ✓；`male = 947+104 = 1051`，+9 ⇒ 1060 ✓。

## 三、`SvEventReloadStartNotify = 0x1D` 的一次实战失败

注释记录了一次"名字表说它是什么意思，不等于这个 build 的 Pmove 真的发它"：

> `sv_client_events_mp.cpp` 把 `EventReloadStartNotify = 0x1D` 写在 `EventReloadAddAmmo = 0x1E` 旁边，并注明："四个中的每一个都被两弹匣那次的活体环印证：0x1E 和 0x1D 在换弹前后出现"。**那是本 build 的一次测量，来自 2026-08-21 一个把两个弹匣打空的人。**
>
> 本文件第一版用了名字表上的 **27**（`EV_RELOAD_START`），结果**换弹台词在一整场里一次都没响**，而击杀台词正常——**名字表说的是一个 id 意味着什么，不是这个 build 的 Pmove 发哪个 id。**

语义侧也支持 29：

> IW4 的触发是 `waittill("reload_start")`，而 GSC notify 由 **NOTIFY 事件**驱动，不是状态变化。

## 四、三个语音常量的来源各不相同

| 常量 | 值 | 来源 |
|---|---:|---|
| `AudibleRadius` | 1400.0 | **读游戏自己的 alias 记录** |
| `SuppressionRadius` | 1000.0 | `_battlechatter_mp.gsc` 的 `distSq = 1000*1000` |
| `SpeakerHoldMs` | 2000 | `_battlechatter_mp.gsc` 的 `waittill(2.0)` |

`AudibleRadius` 的取证方式很细：

> `uk_f1_inform_reloading_generic` 的声音资产是 **988 字节 = 九个 108 字节的备选录音**，每一个都带 `mindist 7.0, maxdist 1400.0`。对比之下播报员的 `uk_1mc_timesup` 带 360/600——**这就是为什么一个是世界音，另一个几乎是 UI 音**。

`SpeakerHoldMs` 的注释揭示了它是**绕过缺陷**：

> `timeHack`：`wait(2.0)`，在那里注释为"给一个永远不来的 soundalias notify 的绕行方案"。**说话者占着话筒两秒，不管片段真实长度是多少。**

## 五、听众策略：一次被明确命名的产品决定

这一段是本项目里少见的"把偏离写清楚"的例子。

### 5.1 零售为什么不发

> IW4 用 `playSoundToTeam(alias, team, self)` 投递：说话者的**队伍**，排除说话者。自由混战里没人有队伍，所以它**谁都到不了**——这就是零售 dm demo 里零条战场语音的原因。**不是 demo 里漏了，是那个模式下结构性地静音**，而且很可能是故意的：敌人喊"换弹"就是暴露位置。

### 5.2 本项目的选择

> 它在 **Everyone** 上出厂是为了测试，**而玩家留下了它**——然后更进一步，连**自己的**呼号也留着，因为在一场实打实的比赛里听到了：
>
> > "it works the way you say it. Let's keep self audition, it's pretty cool. Can come back at a later time later in dev to change it."
>
> 所以下面的默认是 `EveryoneIncludingSpeaker`，它是**一个有署名的产品决定**，不是 bug 也不是遗留调试开关。**在该决定被重审之前不要重审。**

忠实路径仍然只差一个谓词：`OLMOD_BATTLECHATTER_TEAM=1`，功能其余部分不变。

### 5.3 为什么投递必须是"每客户端 `p`"而不是世界音实体

> **这正是投递用每客户端 `p` 而不是世界音实体的全部原因**：实体是有位置的，但**到达每一个客户端**，因为 `shouldArchiveWorldEntity` 没有逐客户端可见性阶段（`sv_snapshot_mp.cpp`，它自己的 TODO 说 dedicated 那版从未恢复）。**只发队伍那就会变成一个未构建的子系统而不是一个谓词**，而"假设队伍能用"就是假设未测代码。

### 5.4 代价被写下来了

> **代价，明确说：**`p` 是**本地**音，所以它没有方向也没有衰减——全音量或什么都没有。上面的半径是在服务端施加的，用来**顶替客户端本来会做的衰减**。

## 六、性别：模型名，因为角色定义里的标志不工作

### 6.1 活体实测的反例

> 一场活体比赛里测的：两名玩家，一个 `fpa_raider_sc_m`、一个 `fpa_pingoles_sc_f`，**两个都解析成男声**——`SvCharacterCustomization::female` 对女性角色是 false。

推断：

> `presentation.female = characterDefinition[2] != 0` 显然读的不是性别，而**修正那个不在本范围**：`female` 会写进 clientInfo 而客户端可能据此选身体，**为一个声音去改渲染路径**不值得。

### 6.2 模型名的统计

> 名字无歧义地携带它。对随包 zone 里**每一个** `fpa_` 身体模型（**456 个**）检查过，取**最后一个裸 `m` 或 `f` 分量**：**279 男 / 173 女 / 4 个无法解析**，而那四个是 `fpa_tightjeans_*`——**裤子被错槽成身体**。

命名规则：`<slot>_<name>_<faction>_<gender>[_variant...]`，变体后缀（`_ter`、`_basic`、`_red`、`_a`、`_00_hrt`）**正是为什么要在任意位置找这个 token 而不是只看结尾**。

`std::optional<bool>` 返回：空 = "**名字没说**"，不是"男"——调用方决定。

## 七、手雷爆炸实体：用"重建后相等"自证

```cpp
SV_ProjectGrenadeExplosionEntity:
    entityNum ∈ [FirstDynamicServerEntityNum, EntityNumWorld)
    weapon ∈ [1, MaximumWeaponAssetIndex]
    direction < 162
    surfaceType <= 31
    origin 每个分量 finite 且 == trunc(自己)      ← 必须已经是整数
```

然后：

```text
entity = wireZeroBaseline()
number / eType=0 / eFlags=16
origin / weaponAssetIndex / impactSurfaceType
modelScale=1.0f / eventSequence=1
events[0] = {98, direction}
```

`SV_IsGrenadeExplosionEntityValid` 的做法很漂亮：

```cpp
if (entity.events[0].parameter >= 162) return false;
const auto expected = SV_ProjectGrenadeExplosionEntity({...从 entity 反解...}, entity.number);
return expected && *expected == entity;
```

**用"把实体拆回事件、再重新投影、要求逐字段相等"来校验**——任何多写或漏写的字段都会被这个往返抓住，不需要另写一份字段清单。

`direction < 162` 这个上界在投影和校验里各出现一次；162 应该是方向编码的合法值域上限（与 `DirToByte` 的表长一致）。

`origin` 必须是**整数**，因为错误码 98 使用整数化临时实体原点（与之前报告里 `std::trunc` 的处理一致）——这里把它提前成准入条件，比事后截断更严格。

## 八、使用对象：定义准入与队伍关系

`validDefinition`：

- `objectId` 必须非零；
- `Any` 关系直接通过；
- 其它关系要求 `ownerTeam ∈ {Tf, Sc}`（**不能是 None**）。

`teamAllowed`：

```text
Any      → team ∈ {Tf, Sc}          （观察者/无队玩家不算）
Friendly → team == ownerTeam
Enemy    → team ∈ {Tf, Sc} && team != ownerTeam
```

`configure` 用 `unordered_set` 拒绝**重复 objectId**，空定义表也拒绝。

## 九、`eligibleDefinition`：候选顺序就是空间策略

```cpp
if (!command.playing || !command.alive || !(command.buttons & UserCmdButtonActivate))
    return nullptr;
```

然后**按调用方给的候选顺序**遍历：

```cpp
if (!candidate.insideTrigger) continue;
find(definition by objectId)  失败 → continue
!teamAllowed                   → continue
requiresKeyObject && !hasKeyObject → continue
→ 返回第一个通过的
```

注释：

> **调用方拥有原生触发器排序。保持候选顺序防止这个通用进度所有者发明空间策略。**

这与之前报告里"多个可提示触发器重叠时取体积最小者"是分层设计：**空间优先级在调用方，通用所有者只认顺序**。

## 十、`cancelProgress` 与 `cancelClient`

`cancelProgress` 产生事件后**同时**做两件事：

```text
objectClaimants_.erase(progress->second.objectId);
clientProgress_.erase(progress);
```

`elapsedMilliseconds = lastCommandTime - startCommandTime`——**用最后一条命令的时间，不是当前时间**，这样取消的时长与"最后一次真的按着"的那一刻一致。

`cancelClient` 里有一道时间守卫：

```cpp
if (previousCommandTime != end && commandTime < previousCommandTime->second)
```

即**命令时间倒退时不做取消**（乱序/回退的 usercmd 不能取消一个更新的进度）。这与 antilag、zombie injury 等处的时间处理是同一套纪律。

## 十一、`SV_BuildSplashCommand`

```cpp
"w " + slot + " " + row + " " + points
```

注释：

> 三个参数，按 `sub_C1C860` 读它们的顺序：它把 `argv(3)` 当分数、`argv(2)` 当行，并自己钳槽位。

即**字符串里的顺序与消费方读 argv 的下标**是对齐的（argv(1)=slot），而槽位钳制交给客户端。

## 十二、关键结论

1. **断言要交叉约束多个自由度**，六条 static_assert 覆盖两个阵营 × 两个性别 × 三条行，而不是同一点重复六次。
2. **名字表说 id 什么意思，不等于这个 build 发哪个 id**——用 27 换弹台词整场不响，用 0x1D 才对。
3. **偏离必须署名**：`EveryoneIncludingSpeaker` 是有署名的产品决定，附原始引语与回退开关。
4. **"假设未构建的子系统能用"是陷阱**：世界音实体没有逐客户端可见性，所以队伍投递会变成未构建子系统。
5. **自证式校验**（拆回→重建→逐字段比对）比自己再写一份字段清单更可靠。
6. **候选顺序就是空间策略的归属边界**：通用所有者不发明优先级。

## 十三、未闭合点

- `SvCharacterCustomization::female` 读到的东西不是性别，未修正（有意，避免动渲染路径）。
- `fpa_tightjeans_*` 四个模型名无法判定性别（裤子错槽）。
- `p` 是无方向无衰减的本地音，半径是服务端顶替。
- 玻璃 touch 与具体原生处理器仍是 `TODO(CODOL)`。
