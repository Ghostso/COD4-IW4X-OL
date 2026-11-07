# 152 · 战场语音、手雷爆炸实体、半径伤害、武器摆动

## 一、范围

本报告完整学习 **4 个头文件的前段**：

- `sv_battlechatter_mp.hpp`（前 80 行）
- `sv_grenade_explosion_mp.hpp`（27 行）
- `sv_radius_damage_mp.hpp`（前 80 行）
- `sv_weapon_movement_mp.hpp`（前 80 行）

`server_mp` 进度推进到 **139/154**。

## 二、战场语音：`f1` 从来不是固定前缀

### 2.1 词汇表是 CODOL 的，而且很小

> 每个阵营语音有**十一条** `<voice>_f1_inform_*` 行，与播报员在同一个 CCS 带里，所以**不需要任何 configstring、不需要任何 precache**——客户端已经持有它们。

```text
uk_ 1674..1684
ab_ 947..957
```

IW4 的九条 `bcSounds` 里这里有八条；**`inform_casualty_generic` 不存在**，所以"casualty"触发**没有话说，因此在这里缺席，而不是用一句意思不同的话顶替**。

### 2.2 那段被更正的注释

> 本文件第一版给所有人发 `uk_f1_*`，结果**男性角色被女声回应**。`f1` 不是前缀的一部分：它是**女声 1**。每个阵营四个，随包文件树直接命名：

```text
codo_mp/tf/{f1,f2,m1,m2}/uk_1_inform_*   别名  uk_<gender><n>_inform_*
codo_mp/sc/{f1,f2,m1,m2}/ab_1_inform_*   别名  ab_<gender><n>_inform_*
codo_mp/ancr/tf141  uk_    codo_mp/ancr/scar  ab_    codo_mp/ancr/rbt  rb_
```

结论：

> 所以 `tf` 是 `uk_` 声音、`sc` 是 `ab_` 声音，**这正是本服务器自己的 `SvCharacterFaction::Tf / ::Sc`——这个映射完全不需要发明**。性别来自 `SvCharacterCustomization::female`，服务器一直持有它，只是这个功能从没读过。

**只取两者中的索引 1**：

> 因为 IW4 自己构建前缀时是 `getTeamVoicePrefix(team) + "1_"`，**永远取 voice 1**。在 1 和 2 之间按玩家挑选会是一条零售没有的规则。

### 2.3 十一声道与 52 步长

```text
SvBattleChatterVoiceStride    = 52
SvBattleChatterTfFemaleBase   = 1674
SvBattleChatterScFemaleBase   = 947
male = female + 2 * 52        // f1, f2, m1, m2
```

注释：

> 一个声音的十一条连续且按字母序，同阵营的四个声音相隔 52。两者都在下面**对着从 ncs 表直接读出的参数**做断言，所以一个错误假设会**让构建失败，而不是播错那一行**。

`SvBattleChatterLine` 十一项：AttackFlashbang / AttackGrenade / AttackSmoke / AttackStiel / AttackStun / AttackThwC4 / KillfirmGeneric / KillfirmInfantry / PlantClaymore / ReloadingGeneric / SuppressedGeneric。

## 三、手雷爆炸：十二个闪光弹效果的确切形状

```text
CODREF(out.exe CG_EntityEvent 536467..5365AC): event98 是手雷爆炸消费者
零售 DM 的十二个 Semtex 效果是：
    ET_GENERAL  flags=16  scale=1  eventSequence=1  event[0]={98,5}
    除 number / origin / weapon / surfType 以外所有其它字都是零
外来 flags=32 在这里是错的
```

字段只有四个：origin / weapon / direction / surfaceType。

这是"从实测样本反推出来的精确形状"，而不是"按经验填"。`flags 16` 与 `flags 32` 的差别不会报错，只会让效果不对。

## 四、半径伤害：两个排除、三重可见性

### 4.1 目标视图

```cpp
struct SvPlayerRadiusDamageTarget {
    clientNum, spawnGeneration, origin, eyePosition,
    absoluteBounds, shieldProtection
};
```

注释：

> 帧局部的、已经可受伤的活玩家。**所有者提供保留的眼睛位置与已链接的绝对包围盒**；这些**不是**从站立高度近似重建的。

### 4.2 请求

```text
origin / radius / innerDamage / outerDamage
cone{ angleCos=-1.0f, direction }   // 可选
inflictorEntityNum / ignoreClientNum
contentMask                          // 必须显式给
```

`contentMask` 的注释：

> 直到恢复 OLfinal 的 mask 之前显式给出。Ghosts `G_RadiusDamage` 用 `0x802011`；**这不是默认值。**

### 4.3 可见性：`CanDamage` 的两个排除

```text
CODREF(CanDamage): G_LocationalTracePassed 同时忽略 target 和 inflictor。
不要把第二个排除等同于现有点 trace 模式里的 passOwnerEntityNum——除非核对其原生语义。
```

`SV_TestRadiusDamageVisibility` 的三层：

1. **两个独立的排除也排除它们拥有的实体**；
2. **世界/静态几何在过滤实体窄相之前跑**；
3. `false` = 被遮挡；**`nullopt` = 查询不可用，绝不隐含一条穿过掩体的清空线**。

### 4.4 结果

```text
clientNum / spawnGeneration / distance
unoccludedDamage / exposure / shieldProtection / damage
```

把 `unoccludedDamage`（未遮挡伤害）与 `exposure`（暴露度）与最终 `damage` 三者分列，意味着结果是可以逐项核对的中间量，而不是只给一个最终数字。

## 五、武器摆动：`lastIdleFactor` 与 `weaponIdleTime` 是诊断品的来源

### 5.1 持久状态

```text
damageTime / damagePitch / damageRoll
weaponIdleTime / lastIdleFactor
baseAngles / baseOrigin
recoilAngles / recoilSpeed
swayAngles / swayOrigin / swayViewAngles
```

注释：这是 BO1/Ghosts/BO2 的 `G_BuildWeaponState`/`G_SaveWeaponState` 复制的那批持久 gclient 字段的**语义所有者**，CODOL 已移除的服务端 gclient 布局未知。

### 5.2 诊断结构存在的原因（很具体）

> `lastIdleFactor` 和 `weaponIdleTime` 是原生 idle 阶段的两个输入（`sub_4355D0 0x0355D0`——ABI 注记：`a1[7] lastIdleFactor, 读且写`、`**((int**)a1 + 8) —— weaponIdleTime 被当指针解引用`）。**两者都到不了快照**，所以"狙击镜抖动"假说——"idle 相位每帧从一个不前进的 weaponIdleTime 重建"——**无法从任何现有日志里读出来**。

所以加了 `SvWeaponMovementIdleDiagnostics`，其中 `stageWmTime[9]` 是**每个受限阶段之后采样的 `*weaponIdleTime`**，按调用顺序：

```text
0 damageKick 1 idle 2 viewBob 3 adsBob
4 base 5 viewBob 6 recoil 7 weaponBob 8 setAngles
```

> idle 阶段只**读**这个计数器，所以**不同的那一对就点名了推进它的阶段**。

注释明确：`DIAGNOSTIC ONLY`，没有消费者，不属于任何原生 ABI，与探针一起移除。

### 5.3 一条自我更正的注释

> **已在 out.exe 上确认。上面那些地址是 3.3.3.3 的——本文件此前与那棵树逐字节相同，注释从未重新推导过**——但是……

（后续内容在本组读取范围之外。）

## 六、关键结论

1. **`f1` 是女声 1 不是前缀**，而这个错误的表现是"男性角色被女声回应"——一个只能靠人耳发现的缺陷。
2. **阵营映射不需要发明**：`tf`↔`uk_`、`sc`↔`ab_` 正好就是服务器已有的 `SvCharacterFaction`。
3. **缺席的语音行要缺席**，不要用意思不同的一句顶替（`inform_casualty_generic`）。
4. **手雷爆炸实体的形状是从 12 个实测样本反推的**：`flags 16`、`event[0]={98,5}`，其余字为零；`flags 32` 是错的但不会报错。
5. **`nullopt` 与 `false` 必须分开**：前者是"查不了"，后者是"被挡住"；把前者当后者会给出穿过掩体的清空线。
6. **"读不出来的现象"要加只读探针**，而不是猜一个假说——`stageWmTime[9]` 就是为此存在，且明确标注可随探针一起删。

## 七、未闭合点

- `inform_casualty_generic` 在 CODOL 里不存在，"casualty"触发本组没有对应实现。
- 半径伤害的 `contentMask` 仍需 OLfinal 实测值（当前显式传入）。
- 狙击镜抖动的假说仍未验证，只有探针。
- `viewState_t` 的注释地址仍标为 3.3.3.3 的，本文件后续段落称已在本 build 确认（详见该文件后段）。
