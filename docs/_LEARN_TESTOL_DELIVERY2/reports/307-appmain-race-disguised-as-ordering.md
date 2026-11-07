# 307 · **"一个竞态伪装成顺序"**、**"一个崩溃的 CODOL 客户端什么都不留"**、`AC130` 的边界声明

## 一、范围

本报告学习 `Appmain.cpp` 8080–8300 行。

## 二、**TCLS 映射的"竞态伪装成顺序"**（本组最重要的一段）

### 2.1 那段完整的论证

```php
// FIRST, BEFORE ANYTHING THAT DEPENDS ON THE ENGINE OR THE RENDERER.
//
// TenProxy asks for TCLS_SHAREDMEMEMORY<pid> during this process's own startup, and
// publishing it used to sit in installClientInputPatches -- which runs only after the
// engine bindings resolve AND installFrameHook succeeds. That is deep into startup and
// rendering-adjacent, so it is a RACE against TenProxy dressed up as an ordering.
//
// Measured 2026-09-05: on Wine's d3d9 it won -- the client authenticated as Skeet and
// the lobby served his profile -- and under DXVK it lost, and the same [100] came back.
// The player then had a choice between a client that logs in and crashes at the intro
// (d3d9) and one that survives the intro and cannot log in (DXVK). Nothing about the
// mapping should depend on which renderer is in use.
```

### 2.2 八层

```text
1. **TenProxy 在这个进程自己的启动期间请求 `TCLS_SHAREDMEMEMORY<pid>`**
2. 而发布它**过去坐在 `installClientInputPatches` 里**
3. ⇒ 那个函数**只在引擎绑定解析之后且 `installFrameHook` 成功之后**才跑
4. ⇒ 那是**启动的深处且与渲染相邻**
5. ⇒ **所以它是一个对着 TenProxy 的【竞态】，却伪装成一个【顺序】**
6. **实测 2026-09-05**：在 Wine 的 d3d9 上**它赢了**（客户端验证为 Skeet 且大厅服务了他的 profile）
7. 而在 **DXVK 下它输了**，`[100]` 又回来了
8. ⇒ 玩家于是有一个选择：**一个能登录但在开场崩溃**（d3d9）与**一个能挺过开场但不能登录**（DXVK）
9. ⇒ **关于那个映射的任何东西都不应该取决于用哪个渲染器**
```

### 2.3 **"一个竞态伪装成一个顺序"**

**⇒ 这是整个文件里最重要的一句方法论。**

**⇒ 与 §265 的"竞争会让两个 loader 看到同一个 null"、§282 的"在这里等就绪 = 死锁"同族**（第三次"顺序/竞态的混淆"）。

### 2.4 而**两种渲染器两种失败**

```text
d3d9  ⇒ 能登录，开场崩溃
DXVK  ⇒ 能挺过开场，不能登录
```

**✅ 一个完美的"两个选择都不可接受"的展示。**

**⇒ 而根因是**时序**而不是**渲染器**。**

### 2.5 而**修法**

```php
// onStartup/onInitialized are the plugin's own entry points, so this is as early as
// this code can run. It is idempotent -- the handle is held for the process lifetime
// and a second call returns immediately -- and the later call site is left in place as
// a backstop for a path that reaches the frame hook without coming through here.
if (role != Dedicated)
{
    const auto tclsMapping = publishTclsMapping();
    if (tclsMapping != NotRequested)
        logGameServer("tcls mapping " + name + " (early)");
}
```

### 2.6 四层

```text
1. `onStartup`/`onInitialized` 是插件的**自己入口点** ⇒ 这是这段代码能跑的**最早时刻**
2. 它**幂等** —— 句柄持有到进程生命周期结束，**第二次调用立即返回**
3. ⇒ **后面的调用点留在原地作为后备**
4. ⇒ 用于"一条到达帧钩子而不经过这里的路径"

**⇒ 所以**两处都发布**，第一处优先。**

### 2.7 而 `" (early)"` 后缀区分

**⇒ 所以日志能看出是**哪一处**发布的。**

**✅ 与 §275 的"`ALREADY VISIBLE`"配合 —— 三种结果 + 一个 `(early)` 标记。**

## 三、**"一个崩溃的 CODOL 客户端什么都不留"**（本组第二重要）

### 3.1 那段

```php
// A CODOL CLIENT THAT CRASHES LEAVES NOTHING. It installs its own
// TopLevelExceptionFilter, so there is no dump and no WER event -- only
// a ClientException posted to the lobby, whose stack starts at the
// reporter and carries no registers. A vectored handler runs BEFORE
// that filter, so it is the only place the faulting context can be read.
//
// Free until something faults, which is why this is armed here and not
// implemented as a hook: the functions involved in section 152w's crash
// are per-frame, and a per-frame client hook killed three clients at once.
CodolGameServer::armNativeFaultWitness(GetModuleHandleW(nullptr));
```

### 3.2 七层

```text
1. **一个崩溃的 CODOL 客户端什么都不留**
2. 它装了自己的 `TopLevelExceptionFilter`
3. ⇒ 所以**没有 dump 也没有 WER 事件**
4. ⇒ 只有**一个 `ClientException` 投到大厅**，其栈**从报告者开始且不带寄存器**
5. ⇒ **一个向量化处理器（VEH）在那个过滤器【之前】运行**
6. ⇒ 所以它是**唯一能读到故障上下文的**地方
7. ⇒ **未故障时免费** ⇒ 这就是为什么它**在这里装而不是实现成钩子**
8. 因为 §152w 崩溃涉及的函数是**每帧的**，而**一个每帧客户端钩子一次杀死了三个客户端**
```

### 3.3 **VEH 在 `TopLevelExceptionFilter` 之前 ⇒ 唯一能读到上下文**

**✅ 一个精确的机制论证。**

**⇒ 与 §162 的 `DisconnectWitness` hook 的是**写**而不是函数入口**同族**（都是"从能拿到证据的地方取"）。**

### 3.4 而"**一个每帧客户端钩子一次杀死了三个客户端**"

**⇒ 三层**：

```text
1. §152w 崩溃涉及的函数是**每帧的**
2. 而钩一个每帧客户端函数
3. ⇒ **一次杀死了三个客户端**
```

**✅ 这是一个**惨痛的实测** —— 与 §306 的"暂缓"同族。**

**⇒ 第五次"钩每帧函数 = 灾难"。**

## 四、`characterInfo` 的**1 Hz 独立线程**

```php
// AND A ONE-HERTZ READ OF THE CLIENT'S OWN characterInfo. The bridge tick
// was the wrong place for this: it fires while the client is still at the
// menu, where cgame is not initialised and the array pointer is null, so
// the probe only ever reported BASE NULL and never sampled a match at all.
//
// Its own thread, one second apart, READ ONLY and bounds-checked, logged
// only when the answer CHANGES -- so a healthy match prints one line and an
// invisible player prints the moment it goes wrong. Deliberately not a hook:
// this project's rule is never to hook a per-frame client function.
std::thread([] {
    std::string last;
    for (;;)
    {
        std::this_thread::sleep_for(std::chrono::seconds(1));
        auto report = Bindings.reportClientCharacterInfo();
        if (report.empty() || report == last) continue;
        last = std::move(report);
        logGameServer(last);
    }
}).detach();
```

### 4.1 五层

```text
1. **1 Hz 读客户端自己的 `characterInfo`**
2. 桥的 tick 是**错误的地方**：它在客户端**还在菜单**时触发，那时 cgame 未初始化而**数组指针是 null**
3. ⇒ 所以探针**只报过 BASE NULL 而从未采样到一场比赛**
4. **自己的线程、一秒一次、只读且边界检查、只在答案【变化】时记录**
5. ⇒ **刻意不做钩子：这个项目的规则是绝不钩一个每帧客户端函数**
```

### 4.2 **"桥的 tick 在客户端还在菜单时触发"**

**⇒ 与 §304 的"两个来源，一个沉默"同族 —— 又一次"探针在错误的时刻"（第三次）。**

### 4.3 而"只在答案变化时记录"

**⇒ 与 §304 的四个静态字符串同族（第八次"变化触发"）。**

### 4.4 ⚠ **而它 `continue` 而**不**清空 `last`**

```cpp
if (report.empty() || report == last) continue;
```

**⇒ 所以"从有值变成空"⇒ **不打印**且**保留旧值**。**

**⇒ 下一次有值且与旧值相同时 ⇒ **也不打印**。**

**⚠ 这可能漏掉"变空再变回"的情况。**

**⇒ 而 §304 的 `reportClientCharacterInfo` 在 `base == nullptr` 时返回空。**

## 五、`configuredClientInstance` 的**两项**

```cpp
const auto instance = configuredClientInstance();
if (!instance || (*instance > 1 && !installClientInstanceSingleInstancePatch(*instance)))
{
    logGameServer("client instance mutex patch failed");
    return;
}
```

### 5.1 三层

```text
`instance` 无值 ⇒ 失败
`*instance > 1` 且补丁失败 ⇒ 失败
`*instance <= 1` ⇒ 通过（【不需要】补丁）
```

**⇒ 所以实例 1 不需要单实例补丁。**

**✓ 因为**第一个实例**本来就能拿到互斥量。**

### 5.2 ⚠ **而 `!instance` 与"补丁失败"用**同一条日志**

**⇒ "client instance mutex patch failed"。**

**⚠ 两个不同的原因一个消息** —— 与 §244 的"八个出口一个返回类型"同族。

## 六、`Bindings.bind()` 的**单点**

```cpp
if (!Bindings.bind())
{
    logGameServer("engine binding failed");
    return;
}
```

**⇒ 一个单点。**

**⇒ 而 §306 说 `bind()` 报 "native entity binding prefix mismatch function=SV_LinkEntity"** —— 那是**未解包**的症状。**

**✓ 所以这个单点在解包后才有意义。**

## 七、**`OLMOD_ALPHA_WEAPONS` 的 gamestate 补丁**

```cpp
if (role == Client)
{
    const auto *const alphaWeapons = std::getenv("OLMOD_ALPHA_WEAPONS");
    if (alphaWeapons && std::string_view(alphaWeapons) == "1")
    {
        const auto alphaGamestatePatch = installClientAlphaWeaponGamestatePatch(
            prepareClientAlphaWeaponsForGamestate);
        logGameServer("client alpha gamestate patch " + name);
    }
}
```

### 7.1 而 `prepareClientAlphaWeaponsForGamestate` 是**回调**

```cpp
void prepareClientAlphaWeaponsForGamestate()
{
    const auto status = Bindings.installAlphaWeaponPorts();
    logGameServer("client gamestate alpha weapon restore status=" + alphaWeaponPortStatusName(status));
}
```

**⇒ 所以"gamestate 补丁在发布 gamestate 之前调用这个回调"。**

**✅ 与 §249 的"安装完整的 alpha 基础对【在链接 WeaponDef 之前】"配合。**

### 7.2 而 §304 的 `markFramePhase(2)` 里也调 `installAlphaWeaponPorts()`

```cpp
Bindings.auditXModelSurfaces();
const auto alphaWeaponPortStatus = Bindings.installAlphaWeaponPorts();
```

**⇒ 所以**两处**调用 `installAlphaWeaponPorts`。**

**⇒ 而它是七态机（§246）⇒ 所以两处都安全（幂等）。**

**✓ 但 `installAlphaWeaponPorts` 可能阻塞 15 秒（§249）⇒ 在帧线程上！**

**⚠ 一处潜在的性能问题。**

## 八、`installFrameHook` 的**两条路径**

```cpp
if (!OlMod::runsGameServer(role))
{
    Installed = installFrameHook(Bindings, onServerFrame);
    if (Installed)
        installClientInputPatches(role);
    logGameServer("client frame hook " + (Installed ? "installed" : "failed"));
    return;
}
// （专用服路径）
```

### 8.1 三层

```text
不是跑游戏服务器的角色 ⇒ 只装帧钩子 + 输入补丁 ⇒ 返回
是 ⇒ 继续装所有服务端 provider
```

### 8.2 而 `installClientInputPatches(role)` **只在帧钩子成功后才调**

**⇒ 所以如果 `installFrameHook` 失败 ⇒ **所有客户端补丁都不装**。**

**⚠ 这解释了 §307 开头"发布 TCLS 过去坐在 `installClientInputPatches` 里"**为什么危险**。**

**✅ 因果闭合。**

## 九、`Server.setLoadoutProvider` 的**空手枪回退**

```cpp
Server.setLoadoutProvider([](uint64 xuid, string_view selectedLoadout)
    -> optional<SvResolvedLoadout> {
    optional<SvResolvedLoadout> loadout;
    { const lock_guard lock(LoadoutMutex); loadout = RegisteredSessionAssets.loadout(xuid, selectedLoadout); }
    if (!loadout || loadout->secondary.weaponAssetIndex != 0) return loadout;

    // An empty pistol slot is a legal class state. The client-side
    // weapon table identifies the retail fallback as
    // `chicken_melee_mp` (asset 1154), not weapon 0. Resolve it through
    // the current registry so the native movement and damage paths see
    // the same complete SvResolvedWeapon as any other held weapon.
    const auto knife = Bindings.resolveWeaponConfigStringIndex("chicken_melee_mp");
    if (!knife || !*knife) return loadout;
    ClientWeaponSelection selection{};
    if (!Bindings.readWeaponSelection(*knife, selection) || !selection.weaponAssetIndex) return loadout;
    loadout->secondary = toResolvedWeapon(selection);
    return loadout;
});
```

### 9.1 三层

```text
① 取注册的 loadout
② 若副武器非 0 ⇒ 【直接返回】
③ 若为 0 ⇒ 解析 `chicken_melee_mp`（1154）并【替换】
```

### 9.2 而"**客户端侧的武器表把零售回退识别为 `chicken_melee_mp`（资产 1154），不是武器 0**"

**⇒ 与 §285 的"`chicken_melee_mp` 必须留在基址 1154"**完全一致** ✓**

**⇒ 与 §290 的"空手枪槽回退到刀"**同一个 1154 ✓

**✅ 三处确认 1154。**

### 9.3 而"**让原生移动与伤害路径看到与其他持有武器相同的完整 `SvResolvedWeapon`**"

**⇒ 三层**：

```text
1. 通过**当前注册表**解析
2. ⇒ 让原生移动与伤害路径看到**同样完整的**结构
3. ⇒ 而不是一个空的副武器
```

**✅ 与 §253 的"空槽不是把 0 当刀"一致。**

## 十、**`AC130_TEST_GRANT` 的边界声明**（本组第三重要）

### 10.1 那段中文

```php
// ★★ 28100 刀W（台账 ④ 连杀 · AC130 授予链）——
//   我方"连杀达标 → 授予 → 使用"的整条机制是**通用**的：
//     · 达标/充能：`SvUavEarningState::observe`（`sv_main_mp.cpp:3716`，按 spawnGeneration 每命只领一次）
//     · 授予：`world_.grantPlayerUav(clientNum, weapon)`（`:3788`，原子提交 + 原生 overlay）
//     · 使用：`world_.consumePlayerUavAction(clientNum, asset)`（`:3757`，校验后消费 key4 action）
//   唯一的"写死"点是这个 provider **固定返回 UAV**。本刀加一个**显式开关**：
//   置 `OLMOD_AC130_TEST_GRANT=1` 时改为返回 AC130 的连杀物品（`killstreak_ac130_mp`，
//   刀U 已按名解析并回读校验），于是**连杀达标后玩家拿到的就是 AC130**，
//   从而验证"asset 可授予 + 充能/使用键链通"。
//   ⚠ 使用时的**副作用仍是 UAV 的（开雷达）** —— AC130 的炮艇视角/炮塔/计时 HUD 未实现，
//     那是独立课题（见 findings 的边界）；本刀只做授予面，不假装炮艇已可用。
//   ⚠ 默认不开 ⇒ 未设环境变量时行为与之前**逐字节一致**。
```

### 10.2 五层

```text
1. **"连杀达标 → 授予 → 使用"的整条机制是通用的**
2. 三个函数：`observe`（充能）/ `grantPlayerUav`（授予）/ `consumePlayerUavAction`（使用）
3. ⇒ **唯一的"写死"点**是这个 provider **固定返回 UAV**
4. ⇒ 加一个显式开关返回 AC130 ⇒ **验证"asset 可授予 + 充能/使用键链通"**
5. ⚠ **使用时的副作用仍是 UAV 的（开雷达）** —— **AC130 的炮艇视角/炮塔/计时 HUD 未实现**
6. ⚠ **默认不开 ⇒ 未设环境变量时行为与之前逐字节一致**
```

### 10.3 **"本刀只做授予面，不假装炮艇已可用"**

**✅ 这是整个文件里最诚实的边界声明之一。**

**⇒ 与 §288 的"留空是有意的"、§292 的"没有任何东西被发明"同族**（第十四次"明确边界"）。

### 10.4 而三个函数的位置

```text
sv_main_mp.cpp:3716    SvUavEarningState::observe
sv_main_mp.cpp:3788    world_.grantPlayerUav
sv_main_mp.cpp:3757    world_.consumePlayerUavAction
```

**⇒ 三个具体行号。**

**✅ 与 §151 的"UAV earning (once per life, `owned` survives death)"配合。**

### 10.5 而 `v[0] == '1' && v[1] == '\0'` 是**严格单字符**

**⇒ 与 §279 的 `size == 1 && value[0] == '1'` 等价，但这里是 `getenv` + 两字符检查。**

**⇒ 第十三种解析。**

## 十一、`KNIFEU-KS` 的**六个名字探测**

```cpp
for (const char *name : {"killstreak_uav_mp", "killstreak_pro_uav_mp",
                         "killstreak_ac130_mp", "killstreak_pro_ac130_mp",
                         "killstreak_sentry_mp", "killstreak_nuke_mp"})
{
    if (const auto w = resolveKillstreakWeapon(name))
        write("KNIFEU-KS|resolved name=" + name + " asset=" + w->weaponAssetIndex +
            " ammo=" + w->ammoIndex + " clip=" + w->clipIndex + " capacity=" + w->clipCapacity);
    else
        write("KNIFEU-KS|unresolved name=" + name);
}
```

### 11.1 六个名字

```text
killstreak_uav_mp
killstreak_pro_uav_mp
killstreak_ac130_mp
killstreak_pro_ac130_mp
killstreak_sentry_mp
killstreak_nuke_mp
```

### 11.2 而四个字段

```text
asset / ammo / clip / capacity
```

**⇒ 与 §243 的 `SvRewardWeapon` 五字段（含 ADS/overlay）不同 —— 这里只打四个。**

**⚠ 而 `resolveKillstreakWeapon` 返回五字段。**

### 11.3 而"只在首次调用时打"

```cpp
static const bool killstreakProbed = [] { ...; return true; }();
(void)killstreakProbed;
```

**⇒ 用一个**立即执行的静态 lambda** + `(void)` 来触发副作用。**

**⚠ 一个**反模式** —— 应该用 `std::call_once` 或一个显式的 `if`。**

**⇒ 与 §242/§239 的 `call_once` 相比这是**手写的更差版本**。**

## 十二、关键结论

1. **"一个竞态伪装成一个顺序"** —— TCLS 发布过去在 `installClientInputPatches` 里，那是启动深处。
2. **两种渲染器两种失败**（d3d9 能登录开场崩 / DXVK 能挺过不能登录）。
3. **"关于那个映射的任何东西都不应该取决于用哪个渲染器"**。
4. **修法是在插件最早的入口点发布**（幂等 + 后面留后备）。
5. **"一个崩溃的 CODOL 客户端什么都不留"** —— 它装了自己的 `TopLevelExceptionFilter`。
6. **VEH 在 `TopLevelExceptionFilter` 之前 ⇒ 唯一能读到故障上下文的地方**。
7. **"一个每帧客户端钩子一次杀死了三个客户端"** —— 第五次"钩每帧函数 = 灾难"。
8. **`characterInfo` 的 1 Hz 独立线程** —— 因为桥的 tick 在客户端还在菜单时触发。
9. **⚠ 那个线程在"变空"时不打印且保留旧值** ⇒ 可能漏掉"变空再变回"。
10. **`configuredClientInstance` 的两项用同一条日志** —— 两个原因一个消息。
11. **`installClientInputPatches` 只在帧钩子成功后才调** ⇒ 解释为什么 TCLS 放在那里危险。
12. **空手枪回退到 `chicken_melee_mp`（1154）** —— 与 §285/§290 **三处确认 1154**。
13. **"让原生移动与伤害路径看到与其他持有武器相同的完整 `SvResolvedWeapon`"**。
14. **`AC130_TEST_GRANT` 的边界声明**："本刀只做授予面，不假装炮艇已可用"。
15. **三个连杀函数的具体行号**（`sv_main_mp.cpp:3716/3788/3757`）。
16. **`KNIFEU-KS` 的六个名字探测**，但只打四个字段（`resolveKillstreakWeapon` 返回五个）。
17. **⚠ 用一个立即执行的静态 lambda + `(void)` 触发副作用** —— 一个反模式。

## 十三、未闭合点

- `installAlphaWeaponPorts` 在帧线程上可能阻塞 15 秒。
- `characterInfo` 线程的"变空"漏报。
- `resolvedCommandBaselineTime` 与 packet-omit 基线。
- `Appmain.cpp` 8300 行之后未读取。
