# 312 · **发射器的第四条路**、**"手雷/烟雾丢不出去"的缺口**、`100 × 10 ms` 的稳定性断言 —— **`Appmain.cpp` 全文读完**

## 一、范围

本报告学习 `Appmain.cpp` 9174–9393 行（文件末尾），并对整个文件做总账。

## 二、`SV_HandleClientEventsDetailed` 的**六个回调 + 一个设备**

```cpp
SV_HandleClientEventsDetailed(
    playerState, entity, currentAimSpreadScale, resolvedLoadout, events,
    // ① fire basis 构造
    [&](weapon) { return Bindings.buildServerWeaponFireBasis(nativePlayerState, weaponAimState, weapon, serverTime); },
    // ② 开火
    [&](playerState, entity, weapon, basis, spread, event) { ... },
    // ③ 近战
    [&](playerState, entity, weapon, basis) { return executeServerMeleeAttack(...); },
    // ④ 装备
    Server.playerEquipment(playerState.clientNum, playerState.spawnGeneration),
    // ⑤ 投掷物
    [&](ps, entity, weapon) { ... },
    // ⑥ UAV
    uavWeapon ? &*uavWeapon : nullptr);
```

**⇒ 五个 lambda + 一个设备 + 一个可选指针。**

## 三、**发射器的第四条路**（本组最重要的一段）

### 3.1 那段中文定因

```php
// ★★★ OLMOD(launcher-fire, 20261016-2000) -- 清单 #6：**发射器开火路径**。
//
// 定因（-38000.md）：发射器三条路全落空 —— Factory 特殊（MP 下恒
// nullopt）、offhand 投掷物（头注释明确排除非"丢出去"类）、子弹
// （SV_BuildBulletFirePlan 要求 weaponType == WeaponTypeBullet(0)）。
// 活体实测（-1930.md，1,136 把武器）：**rpg_mp / javelin_mp / stinger_mp /
// at4_mp / crossbow_mp / sparrow_mp 的 weaponType 全 = 2** ⇒ 子弹那道门
// 在这里 return std::nullopt ⇒ Failed ⇒ 扣扳机什么都不发生。
//
// 本分支 = 第四条路：**weaponType == 2 且不是 factory 特殊**（那是另一条
// 已有分支）⇒ 读 C1 契约的 7 个字段、算初速度、构造 SvMissileSpawnRequest，
// 交给既有的 sv_missile_* 三件（投影/步进/落地贴附，手雷已在用）。
//
// ⚠ 纪律（-38000.md §5）：**不动手雷那两条生产者路径**
// （sv_grenade_launch_mp / sv_zm_special_mp），也不改 sv_missile_* 本体。
```

### 3.2 八层

```text
1. **发射器的三条路全落空**：
     · Factory 特殊（MP 下恒 nullopt）
     · offhand 投掷物（头注释明确排除非"丢出去"类）
     · 子弹（`SV_BuildBulletFirePlan` 要求 `weaponType == WeaponTypeBullet(0)`）
2. **活体实测（1,136 把武器）**：`rpg_mp`/`javelin_mp`/`stinger_mp`/`at4_mp`/`crossbow_mp`/`sparrow_mp` 的 **`weaponType` 全 = 2**
3. ⇒ 子弹那道门在这里 `return nullopt` ⇒ `Failed` ⇒ **扣扳机什么都不发生**
4. ⇒ **本分支 = 第四条路**：`weaponType == 2` 且**不是** factory 特殊
5. ⇒ 读 **C1 契约的 7 个字段**、算初速度、构造 `SvMissileSpawnRequest`
6. ⇒ 交给既有的 `sv_missile_*` 三件（**投影 / 步进 / 落地贴附**，手雷已在用）
7. ⚠ **纪律：不动手雷那两条生产者路径，也不改 `sv_missile_*` 本体**
```

### 3.3 而**六个发射器的 `weaponType` 全 = 2**

```text
rpg_mp / javelin_mp / stinger_mp / at4_mp / crossbow_mp / sparrow_mp
```

**⇒ 六个，而 1,136 把武器里还有多少是 type 2 未知。**

**⇒ 与 §298 的"`weaponType == 2` 是第三种类型（特殊武器）"**完全一致** ✓**

**✅ 而 §298 是**从 `FactoryReconstructedBoxPool` 的角度**看到的 type 2。**

**⇒ 这里是**从发射器角度** —— 同一个类型。**

### 3.4 而**七个字段**

```cpp
const auto parameters = Bindings.resolveLauncherProjectileParameters(weapon.weaponAssetIndex);
const auto velocity = SV_ComputeLauncherVelocity(*parameters, basis);
const auto angles = Bindings.directionToAngles(*velocity);
```

### 3.5 **"C1 契约的 7 个字段"**

**⇒ 而日志打了五个**：

```text
speed / speedUp / speedForward / radius / inner / outer     ← 六个
```

**⚠ 注释说 7 个而日志打 6 个（`parameters->speed`, `speedUp`, `speedForward`, `explosionRadius`, `explosionInnerDamage`, `explosionOuterDamage`）。**

**⇒ 第七个可能是 `weaponAssetIndex` 之外的字段。**

### 3.6 而 `SvMissileSpawnRequest` 的**十项**

```cpp
SvMissileSpawnRequest launch{};
auto &network = launch.initial;
network.weapon      = weapon.weaponAssetIndex;
network.owner       = (uint16)playerState.clientNum;
network.ground      = EntityNumNone;
network.position    = { 5, (int32)serverTime, 0, basis.muzzleTrace, {} };
network.angles.base = *angles;
for (i = 0; i < 3; ++i) network.position.delta[i] = std::trunc((*velocity)[i]);
network.launchTime  = serverTime;
launch.fuseDeadline = serverTime + 30000u;
```

### 3.7 十项

```text
weapon / owner / ground
position（含一个 5 与 serverTime 与 0 与 muzzleTrace 与空 delta）
angles.base
position.delta[3]（速度截断）
launchTime
fuseDeadline
```

**⚠ 而 `position = { 5, (int32)serverTime, 0, basis.muzzleTrace, {} }` 的五项**

**⇒ 一个**位置结构的五个字段**，其中 `5` 与 `serverTime` 显然是**不同的东西**（一个是 entityNum？一个是时间？）。**

**⇒ 待读 `SvMissileSpawnRequest` 的定义。**

### 3.8 而 `std::trunc((*velocity)[i])`

**⇒ 所以速度被**截断成整数**。**

**⇒ 因为 `delta` 是整数类型。**

**⚠ 精度丢失** —— 但可能是协议的线格式。

### 3.9 而**引信是 30 秒**

```php
// 引信：发射器不是定时器而是撞击/距离引爆，这里只给一个
// 保守的清理上限（与手雷的非定时分支同值 30 s）。
launch.fuseDeadline = serverTime + 30000u;
```

**⇒ 三层**：

```text
1. 发射器不是定时器而是**撞击/距离引爆**
2. ⇒ 这里只给一个**保守的清理上限**
3. ⇒ 与手雷的**非定时分支同值 30 s**
```

**✅ 与记忆里"`SvSplashReleaseIntervalMilliseconds = 1500`"**不同的量。**

### 3.10 而**"明确失败，不静默落进子弹分支"**

```php
// 读不到参数 ⇒ **明确失败**，不静默落进子弹分支（那里必然再 nullopt，
// 会把"为什么没反应"藏起来）。
return CodolGameServer::SvFireWeaponResult::Failed;
```

**⇒ 三层**：

```text
1. 读不到参数 ⇒ **明确失败**
2. **不静默落进子弹分支**
3. ⇒ 因为那里**必然再 nullopt** ⇒ **会把"为什么没反应"藏起来**
```

**✅ 与 §285 的"两层失败"、§311 的"不猜"同族**（第九次"拒绝要明确"）。

## 四、**"手雷/烟雾丢不出去"的缺口**（本组第二重要）

### 4.1 那段中文

```php
// OLMOD(multiplayer_offhand_projectile): Factory 池优先（只在 opt-in 时
// 有效），未命中再走 MP 普通投掷物。旧写法在多人模式下恒 nullopt 并
// 静默返回 DeferredImpact —— 这就是"手雷/烟雾丢不出去"的缺口。
const auto kind = Server.offhandWeaponKind(weapon.weaponAssetIndex);
if (!kind) return CodolGameServer::SvFireWeaponResult::DeferredImpact;
```

### 4.2 四层

```text
1. **Factory 池优先**（只在 opt-in 时有效）
2. 未命中再走 **MP 普通投掷物**
3. 旧写法在**多人模式下恒 nullopt** 并**静默返回 `DeferredImpact`**
4. ⇒ **这就是"手雷/烟雾丢不出去"的缺口**
```

### 4.3 而 `DeferredImpact` 的**语义**

**⇒ "延后的撞击"** —— 所以玩家看到的是"没反应"而不是"失败"。

**⚠ 一个**让失败看起来像成功**的返回值。**

**✅ 与 §272 的"合取式里静默丢项"同族（第十次"静默的失败"）。**

### 4.4 而**投掷物的十项参数**

```cpp
const auto basis = Bindings.buildServerOffhandFireBasis(nativePlayerState, weaponAimState, weapon, serverTime);
if (!basis) return Failed;
const auto parameters = Bindings.resolveGrenadeLaunchParameters(weapon.weaponAssetIndex);
if (!parameters) return Failed;
const auto offhand = SV_ReadNativeOffhandState(nativePlayerState);
const auto launch = SV_ComputeGrenadeLaunch({
    .parameters = *parameters,
    .basis = *basis,
    .playerVelocity = ps.velocity,
    .angularVelocity = {120, 75, 0},
    .time = serverTime,
    .owner = (uint16)ps.clientNum,
    .heldFuseMilliseconds = std::max(0, offhand.grenadeTimeLeft),
    .rotate = !(*kind >= FireTrap && *kind <= Monkey),
}, [](v, out) { ... });
```

### 4.5 十项

```text
parameters / basis / playerVelocity
angularVelocity {120, 75, 0}
time / owner
heldFuseMilliseconds = max(0, offhand.grenadeTimeLeft)
rotate = !(FireTrap ≤ kind ≤ Monkey)
```

### 4.6 而"**原版开火/缩小 demo：静止角速度贯穿飞行**"

```php
// Original fire/shrink demos: stationary angular trajectory
// throughout flight. Monkey also needs upright presentation.
.rotate=!(*kind>=SvFactorySpecialKind::FireTrap && *kind<=SvFactorySpecialKind::Monkey)
```

**⇒ 三层**：

```text
1. 原版的**火/缩小** demo：**静止**角速度贯穿飞行
2. ⇒ 所以 `FireTrap`..`Monkey` 这个范围内的 kind **不旋转**
3. ⇒ **猴子也需要直立表现**
```

**✅ 一个**范围检查**而不是枚举**。**

**⇒ 而 `FireTrap ≤ kind ≤ Monkey` 意味着枚举顺序有语义。**

## 五、`SV_ClearNativeGrenadeTimer` 与 `ps.grenadeTimeLeft = 0`

```cpp
entity.pendingEntitySpawns.push_back(*launch);
CodolGameServer::SV_ClearNativeGrenadeTimer(nativePlayerState);
ps.grenadeTimeLeft = 0;
```

### 5.1 三层

```text
① 排队生成
② **清原生手雷计时器**
③ **清镜像的 grenadeTimeLeft**
```

**⇒ 两层状态都要清** —— 因为一个是**原生**一个是**我们的镜像**。

**✅ 与 §266 的"两个来源要同步"同族。**

## 六、三个 `reports` 上限

```cpp
static unsigned launcherReports{};    if (launcherReports++ < 32)
static unsigned launcherRefused{};    if (launcherRefused++ < 16)
static unsigned mpOffhandReports{};   if (mpOffhandReports++ < 64)
static unsigned offhandReports{};     if (offhandReports++ < 64)
```

**⇒ 四个上限：32 / 16 / 64 / 64。**

**⚠ 四个不同的值。**

**✅ 与 §273 的"96/48/128/12"同族（上限各不相同）。**

## 七、`ensureInstalled` 与**延迟启动的稳定性断言**（本组第三重要）

### 7.1 `ensureInstalled`

```cpp
bool ensureInstalled()
{
    initialize();
    return Installed;
}
```

**⇒ 两项。**

### 7.2 `scheduleDeferredInitialize` 的**那段**

```php
// LOCAL OVERRIDE (olmod-local, 2026-10-03). One worker, started once. It
// polls the readiness predicate every 10 ms (the unpack lands between 2068
// and 4065 ms, and the dedicated role must rewrite the single-instance guard
// BEFORE the game's own WinMain check runs, so the poll is deliberately
// tight) and then calls initialize() exactly once -- no retry loop, so a
// later unrelated failure cannot re-run startup repeatedly.
void scheduleDeferredInitialize()
{
    static bool scheduled = false;
    if (scheduled) return;
    scheduled = true;
    std::thread([] {
        // Stability margin: the predicate must hold for 100 consecutive
        // 10 ms polls (1 s). One flipped page is not proof the packer is
        // done -- see the 13:37 / 13:27 comparison in the header comment.
        int stable = 0;
        for (int attempt = 0; attempt != 6000; ++attempt)
        {
            std::this_thread::sleep_for(std::chrono::milliseconds(10));
            if (!startupImageUnpacked()) { stable = 0; continue; }
            if (++stable < 100) continue;
            logGameServer("deferred startup: .tp3 image unpacked and stable after " + (attempt * 10) + " ms");
            initialize();
            return;
        }
        logGameServer("deferred startup gave up: .tp3 image never unpacked in 60 s");
    }).detach();
}
```

### 7.3 七层

```text
1. **一个工作线程，启动一次**
2. **每 10 ms 轮询就绪谓词**
3. 而"解包落在 **2068 到 4065 ms** 之间"（§306 的采样）
4. ⇒ 而**专用服角色必须在游戏自己的 `WinMain` 检查之前重写单实例守卫**
5. ⇒ **所以轮询是刻意紧的**
6. ⇒ 然后**精确地调用 `initialize()` 一次** —— **没有重试循环**
7. ⇒ 所以**一个后来的无关失败不能反复重跑启动**
```

### 7.4 而**稳定性边际**

```text
1. 谓词必须**连续 100 次 10 ms 轮询（1 秒）**成立
2. ⇒ **一个翻转的页不是打包器完成的证据**
3. ⇒ 见头注释里 **13:37 / 13:27 的对比**
```

**✅ 一个**极其谨慎**的判据。**

**⇒ 与 §306 的"五个采样点 567/1055/2068/4065/8060"配合 —— 而这里是"1 秒连续"。**

### 7.5 而 `attempt != 6000` ⇒ **60 秒上限**

**⇒ `6000 × 10 ms = 60 秒`。**

**⇒ 而日志明说"never unpacked in 60 s"。**

### 7.6 ⚠ **`scheduled` 是普通 `bool` 而可能被多线程访问**

**⇒ 如果 `initialize()` 从多个线程被调 ⇒ 竞态。**

**⚠ 但从调用点看 `initialize()` 在 `StartupMutex` 下（§306）而 `scheduleDeferredInitialize` 在锁**内**被调。**

**⇒ 所以 `scheduled` 在 `StartupMutex` 下 ⇒ 安全。** ✓

### 7.7 而 `initialize()` 里 `Installed` 在延迟路径上不置真

**⇒ 但 `scheduled` 保证只调度一次，而调度后的线程只调 `initialize()` 一次。**

**⇒ 所以"`Installed` 不置真"是**安全的**。**

**✅ §306 的疑问解决。**

## 八、**`Appmain.cpp` 的总账**

### 8.1 体量

```text
565,999 字节
9,393 行
```

### 8.2 学过的分段

| 行段 | 报告 | 主题 |
|---|---|---|
| 1–180 | 270 | `gameTypeIsTeamless`、校验和错配、两个 64 KB |
| 178–380 | 271 | `SNAPHEX` 预言机、八个线程队列 |
| 380–600 | 272 | "命中不是伤害"、自伤探针 |
| 599–820 | 273 | `client_events_rejected` 三症状、`axisDist` |
| 816–1040 | 274 | `EV_MELEE_HIT` 36 次/0 次、五种 env 解析 |
| 1040–1260 | 275 | TCLS 命名空间、17 个补丁 |
| 1263–1480 | 276 | `0x0043204F` 的 `edx=0`、抢修与"引擎是否抢先" |
| 1479–1700 | 277 | "我瞄的正是那堵墙"、15 个 loadout 失败名 |
| 1704–1920 | 278 | Frida 三次两次杀服、62 字段状态 |
| 1928–2140 | 279 | 17 个诊断、`fps-set-<n>` 泛化 |
| 2134–2360 | 280 | §187o 钉 dm 被取消、8 个控制消息 |
| 2353–2575 | 281 | `SendRawCommand` 默认关、换角色工作流 |
| 2575–2795 | 282 | 会话 12 阶段、`CharacterSelectionResolve` 缺席 |
| 2795–3020 | 283 | **`>=` 把真人判成人机** |
| 3020–3240 | 284 | 坏职业跳过、`CodolWorldPlayerSample` 192/352 |
| 3240–3460 | 285 | **Wetwork 51 条动态武器串** |
| 3460–3680 | 286 | **`181 ** 646 0 0 1243 1242`** |
| 3677–3900 | 287 | **`sub_514540` 配置串校验器**、dmz 战利品带 |
| 3896–4120 | 288 | **75 个全试过无奖章音** |
| 4115–4340 | 289 | **"指南针与出生列表无关"** |
| 4340–4560 | 290 | **"客户端显示 Barrett 而服务器执行一把刀"** |
| 4560–4780 | 291 | `BotsCreated` 从不重置 |
| 4779–5000 | 292 | **操作者禁令"严禁自己造人机"** |
| 5000–5220 | 293 | **V1.203 第 2 刀删克隆档案** |
| 5220–5440 | 294 | **`<map>_const.ff` 才是实体编号真源** |
| 5440–5660 | 295 | zm 区域四张预测表、`?N` 与 `cmodel` 两套 |
| 5659–5880 | 296 | **28 屏障/168 板/28 翻越** |
| 5880–6100 | 297 | **骨骼索引一致性规则** |
| 6099–6320 | 298 | **神秘箱七层过滤** |
| 6320–6540 | 299 | **`36 = 2 × 18` 模型槽** |
| 6540–6760 | 300 | **"发布到 gamestate 而不是 live"** |
| 6760–6980 | 301 | **出生点"丢点而不是整图失败"** |
| 6980–7200 | 302 | **"完全不发布 brush model"** |
| 7200–7420 | 303 | **"一个线程的挂起无法自己报告"** |
| 7420–7640 | 304 | 看门狗九阶段、"两个来源一个沉默" |
| 7640–7860 | 305 | **"`commitSessionRoster` 从未被调用"是假的** |
| 7780–8080 | 306 | **`.tp3` 未解包 ⇒ t~0 读密文** |
| 8080–8300 | 307 | **"一个竞态伪装成顺序"** |
| 8300–8520 | 308 | **`错误 1073 tag_weapon defaultvehicle`** |
| 8518–8740 | 309 | **"玩家模型索引不是模型配置串索引"** |
| 8737–8960 | 310 | **标签块在 5896、三次推理反转** |
| 8961–9180 | 311 | **alt-fire 四次失败** |
| 9174–9393 | 312 | 发射器第四条路、投掷物缺口 |

### 8.3 **本文件的五个最重要发现**

#### ① **"一个竞态伪装成顺序"**（§307）

**TCLS 发布在 `installClientInputPatches` 里 ⇒ d3d9 赢而 DXVK 输 ⇒ 两种渲染器两种失败。**

#### ② **`grep` 的盲区让"从未被调用"成为假结论**（§305）

**`commitSessionRoster` 是非限定的类内调用而 `grep` 匹配不到 ⇒ 而"接受杀死它；失败饶它"定死了因果。**

#### ③ **"看起来同构但实际不同"的两个索引**（§309）

**`modelIndex` 是四位命名空间 `{0,6,7,8}` 而 `viewmodelIndex` 是十位的模型带索引 ⇒ 混淆它就是一个隐形玩家。**

#### ④ **`>=` 的数据边界方向错误**（§283）

**真人 xuid ≈ 1.67e19 是 bot base 的 21 倍 ⇒ `>=` 恒真 ⇒ 11 个装饰被抹掉。**

#### ⑤ **"标签块在 `5896`，三次推理反转"**（§310）

**发 tag 0 → 零售线上反驳 → **通道认错了**（不是服装通道而是收纳武器通道）。**

### 8.4 本文件的**五个"操作者指令"**

```text
§292  "严禁自己造人机。追求官方原生人机进房间再进图"
§292  "如果你的人机移动全是自己编的，取消，我们要走官方 bot，不是让你自己造"
§283  "谁让你复制我的了"
§295  "新构建先把热日志修复掉"
§293  "我进图人物装饰还是没有"（三条症状报告）
```

### 8.5 本文件的**五种"静默的失败"**

```text
§272  "命中不是伤害"（hitEntity=none）
§281  "手雷/烟雾丢不出去"（DeferredImpact）
§295  "actor 停在 spawner 上"（空图）
§305  "`commitSessionRoster` 从未被调用"
§309  "隐形玩家"（`+0x18` 空）
§272  "合取式里静默丢项"
```

## 九、关键结论

1. **发射器的六把武器 `weaponType` 全 = 2** ⇒ 三条路全落空 ⇒ 第四条路。
2. **"C1 契约的 7 个字段"** 而日志打 6 个。
3. **"不动手雷那两条生产者路径，也不改 `sv_missile_*` 本体"** —— 一个纪律声明。
4. **投掷物缺口是"恒 nullopt + 静默 `DeferredImpact`"** —— 一个让失败看起来像成功的返回值。
5. **`FireTrap ≤ kind ≤ Monkey` 不旋转** —— 一个范围检查而不是枚举。
6. **两层状态都要清**（原生计时器 + 我们的镜像）。
7. **四个 `reports` 上限各不相同**（32/16/64/64）。
8. **延迟启动每 10 ms 轮询、连续 100 次（1 秒）才认**，60 秒上限。
9. **"专用服必须在 `WinMain` 检查之前重写单实例守卫 ⇒ 轮询刻意紧"**。
10. **"一个翻转的页不是打包器完成的证据"**。
11. **`scheduled` 在 `StartupMutex` 下 ⇒ 安全**，且解决 §306 的 `Installed` 疑问。
12. **`Appmain.cpp` 565,999 字节 / 9,393 行全部读完**，由报告 270–312 覆盖。
13. **五个最重要发现**：竞态伪装成顺序、`grep` 盲区、两个同构索引、`>=` 边界方向、标签块三次反转。
14. **五个操作者指令**、**五种静默的失败**。

## 十、下一步

按用户既有范围顺序：

```text
sv_snapshot_mp.cpp   1,466,951 B   ← 【下一个，最大的文件】
sv_main_mp.cpp         657,426 B
localnetworking（6 个）
platformwrapper（7 个）
client_bridge（2 个）
backend/（Demonware 52 + 若干）
shared/
source\ 的非 src（docs 75 / tools 148 / assets 55 / tests 24 / distribution 7 / .agents 59 / references 12 / 根 14）
```
