# 151 · 预约语法、UAV 奖励、导弹事务、轨迹原语

## 一、范围

本报告完整学习 **4 个文件**：

- `sv_playlist_mp.hpp`（106 行）
- `sv_rewards_mp.hpp`（109 行）
- `sv_missile_mp.hpp`（139 行）
- `sv_trajectory_mp.hpp`（38 行）

`server_mp` 进度推进到 **135/154**。

## 二、预约：两套语法，本 build 不用 3.3.3.3 那套

### 2.1 逐字对照

```text
3.3.3.3  mmstart sv_resetServer; 2486 1; 3265 12; 2489 0;
         playlist 26; start_map_rotate_once 0

CODOL    mmstart 2486 1; 2481 18; 2489 1; 2500 0;
         g_gametype war; 2483 1; map mp_bloc
```

### 2.2 为什么第二个更强

> 第二个是**实测的、不是推断的**：它是 `re/alpha0022/dw-capture-*.log` 里的字面即时消息动词，多个会话，其中 **2481 在变**（12、18）而其余保持不变。

关键结论：

> 它**不带 playlist id 也不带 rotation index**——它直接命名地图和模式，**这比一个还要去查表的 rotation 索引是严格更好的证据。**

所以 `SvBookingCommand` 里 `playlistId`/`rotationIndex` 是**可选**的，配 `hasPlaylistId`/`hasRotationIndex` 两个布尔：

> **消费者必须问它们在不在，而不是比较一个被默认成零的值。**

零是合法值（一个真实存在的 playlist 0），所以不能当哨兵。

### 2.3 模式名双向映射

```text
ffa -> dm
tdm -> war
kc  -> conf
```

未列出的原样返回。`SV_EngineGameType(bookingToken)` 与 `SV_BookingTokenForGameType(gameType)` 是两个方向。

### 2.4 `SvPendingBooking`：两代 configstring 的区分

```cpp
assign(rotation, initialChecksum,
       generationRequirement = NewGeneration);
observeConfigStrings(initialized, checksum, allowReady = true);
commit(ready);
cancel();
```

`SvConfigStringGenerationRequirement` 两态：

- `NewGeneration`：必须看到**新的** generation 才 ready；
- `CurrentGeneration`：当前代也接受。

`SvReadyBooking{ rotation, configStringChecksum }`——ready 时携带的是**那一刻的校验和**，不是 initial 的那个。

## 三、UAV 奖励：一次生命只能赚一次，但 owned 跨命保留

```cpp
struct SvUavEarningState {
    std::uint32_t owned{};
    std::optional<std::uint8_t> life;
    std::optional<std::uint8_t> grantedLife;
    bool earnedThisLife{};
    void observe(generation, alive, eligible, streak, threshold);
};
```

`observe` 的三段逻辑：

1. `!alive` ⇒ `life/grantedLife` 清空、`earnedThisLife=false`（**死亡即重置赚取权，但不碰 owned**）；
2. `life != generation` ⇒ 记新代际、清 granted、清 earned（**重生**）；
3. `eligible && !earnedThisLife && streak >= threshold && owned != UINT32_MAX` ⇒ `++owned`、`earnedThisLife=true`。

`owned` 用 `!= UINT32_MAX` 保护溢出，而不是 `+=` 后检查。

派生的两段注释：

> IW4 `_killstreaks.gsc`：`lastEarnedStreak` 守护每条命；**owned 列表跨死亡保留**。库存发布是单独的重试。

`SV_GrantUavWeapon(state, weapon)`：

> 一次充能的显式授予。赚取所有者必须防止重复授予。**把持有的武器、弹匣、储备和 key4 动作作为一次源变更发布。**

`SvRewardWeapon{ weaponAssetIndex, ammoIndex, clipIndex, clipCapacity, aimDownSight, hasOverlayReticle }`。

### 3.1 奖励槽目标：8 位 ID + 5 位目标

`SvRewardSlot{ id, target }`。

`SV_EquippedRewardTargets(rewards, shift)`：

- `shift` 必须有限、是整数、在 -100..100；
- 每个槽若 `runtimeId` 为零则跳过（= 空槽）；
- `cost = persistentCosts ? persistentCost : normalCost`；
- `target = cost + shift`，用 **double** 算；
- 若 `runtimeId > 255` 或 `target < 0` 或 `target > 31` ⇒ **整体返回 nullopt**。

注释：

> 只解析选择。角色/特权修正以及授予/花费状态与这两列实测的原生表代价分开。

### 3.2 失败查找绝不能变成"零代价奖励"

```cpp
if (!reward || !reward->runtimeId || reward->runtimeId > 255 ||
    reward->normalCost > 31 || reward->persistentCost > 31)
    return std::nullopt;
```

> 运行时字段是 8 位 ID 和 5 位目标。**一次失败的查找绝不能通过 `atoi("")` 变成一个有效的零代价奖励。**

`items[slot] > 65535` 也直接拒绝（profile 整数域上限）。

## 四、导弹：计算与发布严格分离

### 4.1 四个结构的角色

```text
SvMissileNetworkState  —— 源拥有的呈现状态，不进 WorldClientState
SvMissileSpawnRequest  —— 命令候选在分配实体号之前提请求（initial.number 必须为 0）
SvServerMissile        —— 世界侧存储，永不嵌入客户端/原生镜像
SvMissileFrameUpdate   —— 完成后的模拟结果
```

`SvMissileNetworkState` 字段来源注释：`ET_MISSILE` 表 `0xDA7A20`；零售 dm 实体 482 / 第 2 条命。

`surfaceType` 的注释：

> `CG_EntityEvent 5362B0/5363BB` 用 `cent+392`（`es+94`）选**按表面**的手雷声/效果。

### 4.2 三个变体的结果

```cpp
using SvMissileFrameResult = std::variant<
    SvMissileFrameUpdate,     // 继续飞
    SvMissileRetirement,      // 退役
    SvMissileDetonation>;     // 引爆
```

`SvMissileDetonation` 的四项：

```cpp
std::optional<SvGrenadeExplosionEvent> effect;   // 水下抑制可省略表现但保留伤害
std::vector<SvMissilePlayerDamage> playerDamage;
std::string weaponName;
std::optional<SvFactorySpecialImpact> factoryImpact;
```

注释：

> **不可变结果，不是内联效果。** 世界只在导弹移除与原生帧镜像都提交时才分配视觉事件并记账脚本伤害。

### 4.3 `SV_ComputeMissileFlightStep` 的契约

> **计算而不发布。** 撞击解析先于引信处理；所有者必须在这个步进提交前完成那些后续。

还有一个容易搞错的点：

> **自由飞行保留原始网络轨迹/时间/基。** 运行时 origin/angles 与保留的网络轨迹基是**不同的东西**——自由飞行移动前者而不重定基后者。

### 4.4 粘附

`SV_StickMissileToWorld(missile, step, timedDetonation, encodeDirection)`：

> 解析一个**已被准入的** `WEAPSTICKINESS_ALL` 接触。玩家/移动平台附着与特殊表面后续是分开的。**不跑 think、不发外部效果、不改变输入导弹。**

### 4.5 投射到实体状态

```cpp
SV_ProjectMissileEntity(networkState) -> optional<SvEntityState>
SV_IsMissileEntityValid(entity)
```

> **只准入已恢复的手雷字段；无关的 union 载荷绝不能静默穿过序列化边界。**

`SvEntityTypeMissile = 4`。

## 五、轨迹：36 字节，两个求值入口

```cpp
struct SvNativeTrajectory {
    std::int32_t type, time, duration;
    std::array<float,3> base, delta;
};
static_assert(sizeof == 36);
static_assert(offsetof(base) == 12);
static_assert(offsetof(delta) == 24);
```

注释指出了**两个**求值入口：

> `BG_EvaluateTrajectory 0x410BD0` 读一个朴素的 36 字节轨迹：type/time/duration、base、delta。`0x410EA0` 则接受一个**地址混淆**的 base。源拥有的轨迹用朴素入口。

`SV_IsTrajectoryValid(trajectory, atTime)` 的职责：

> 在进入前拒绝原生的 `Com_Error`/default 分支和零时长除法分支。**一次缺失/失败/部分成功的原生调用绝不发布一个点。**

`SV_EvaluateTrajectory` 返回 `optional<array<float,3>>`——失败就是不发布，而不是发布零。

## 六、关键结论

1. **两套预约语法都必须支持，且必须区分"零"与"缺"**。CODOL 那套直接给地图+模式，比索引更强；用零当哨兵会静默错配。
2. **生命边界有三层**：死亡重置赚取权、重生重置 earned 与 granted、**owned 跨死亡保留**。
3. **一次失败的查表绝不能退化成"零代价奖励"**——`atoi("")` 会给你 0，而 0 是合法代价。
4. **导弹的"计算"与"发布"是硬分离**：`Compute` 不发效果、不改输入；`Detonation` 是不可变结果，世界在两侧都提交后才发视觉与记账。
5. **轨迹有两个原生入口**，一个朴素一个地址混淆；源侧只用朴素那个，且失败绝不发布点。

## 七、未闭合点

- `WEAPSTICKINESS_ALL` 之外的粘附类型、玩家/移动平台附着与特殊表面后续都未恢复。
- 导弹撞击后的穿透 continuation 不在本组。
- 预约里 `2481` 等数字字段的语义未解读（只知道它在变）。
