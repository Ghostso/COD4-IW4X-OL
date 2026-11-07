# 216 · 三个 `requiredBytes`、动画块 install/restore 的 CAS、`serverCharacterInfo` 的单一缓冲

## 一、范围

本报告学习 `EngineBindings.cpp` 4311–4510 行。

## 二、三个"传多远"的常量

三个从 `WeaponDefinitionsRva` 取定义的函数，`requiredBytes` 各不相同：

```cpp
resolveGrenadeLaunchParameters:  3838  // final confirmed bool +3837
resolveLauncherProjectileParameters: 0x7A0  // through +79C
resolveGrenadeBlastParameters:   3834  // Checkpoint50: effect-up +3833
```

### 2.1 三个数

```text
3834 = 0xEFA    blast：最后读 +3833（effect-up）
3838 = 0xEFE    launch：最后读 +3837（bool）
1952 = 0x7A0    launcher：最后读 +79C
```

**blast 与 launch 只差 4 字节** —— 因为 blast 读 `+3833`，launch 读 `+3837`。

**launcher 完全不同** —— `+79C` 在 **1980 附近**，而不是 3800 附近。

### 2.2 为什么 launcher 差这么多

**因为启动器参数在 WeaponDef 的不同区域** —— §`sv_launcher_launch_mp.hpp` 里记的偏移是 `794/798/79c`，与这里 `through +79C` 一致。

**而手雷参数在 `1416/1436/2284/2616/2620/3811/3837`** 一带（§141）。

**所以 `requiredBytes` 是"这个函数用到的最远偏移 + 1"**，而不是"结构总大小"。

### 2.3 三个统一的四步

```cpp
1. if (!bindingCommitted_ || !module_ || !weapon || weapon > MaximumWeaponAssetIndex)
       return nullopt;
2. address = module_ + WeaponDefinitionsRva + weapon * sizeof(void*);
   if (!readableSpan(address, sizeof(void*))) return nullopt;
3. definition = *(const uint8_t* const*)address;
   if (!readableSpan(definition, requiredBytes)) return nullopt;
4. return SV_Read...Parameters(weapon, {definition, requiredBytes});
```

**三次 `readableSpan`**（`address`、`definition`）—— **两级间接各校验一次**。

**这防止"定义指针是野指针"** —— 而 §182 里 `DB_FindXAssetHeader` 的 `allowDefault` 问题正是这个风险的来源。

## 三、`evaluateTrajectory`：**又一次每次调用校验前缀**

```cpp
constexpr std::size_t EvaluateTrajectoryRva = 0x10BD0;
constexpr array<uint8_t,16> prefix{
    0x55,0x8B,0xEC,0x83,0xE4,0xF8,0x83,0xEC,0x18,0x53,0x56,0x8B,0xF1,0x8B,0x0E,0x83 };
```

### 3.1 十六字节解码

```text
55 8B EC          push ebp / mov ebp,esp
83 E4 F8          and esp,-8
83 EC 18          sub esp,18h
53                push ebx
56                push esi
8B F1             mov esi,ecx        ← ECX 是参数
8B 0E             mov ecx,[esi]
83 ...            （后续）
```

**`8B F1` = `mov esi,ecx`** —— 而 §194 里 `invokeEvaluateTrajectory` 的注释是 `EAX=time, ECX=plain trajectory, EDI=out`。

**所以 ECX 是轨迹指针，`mov esi,ecx` 把它存进 ESI 备用，然后 `mov ecx,[esi]` 读第一个字段（`type`）**。

**这完全印证了 §151 的 `SvNativeTrajectory` 布局**：

```text
+0  int32 type      ← `mov ecx,[esi]` 读它
```

### 3.2 与 §215 的 `directionToAngles` 同一模式

**两个函数都是"内联常量 + 每次调用校验 + `NativeStageScope`"**：

```cpp
directionToAngles:  rva 0x364C10, 16 字节前缀, stage "vectoangles"
evaluateTrajectory: rva 0x10BD0,  16 字节前缀, stage "BG_EvaluateTrajectory"
```

**这两个 RVA 都不在 `EngineBindings.hpp` 的 RVA 表里**，所以不走 `bind()` 统一校验。

**这是 §215 指出的不一致的第二个例子** —— 现在有 2 个了。

### 3.3 lambda 包住原生调用

```cpp
return SV_EvaluateTrajectory(trajectory, atTime,
    [&](const auto& input, auto time, auto& point) {
        return invokeEvaluateTrajectory(module_ + EvaluateTrajectoryRva,
            &input, time, point.data());
    });
```

**`SV_EvaluateTrajectory` 接受一个 `SvTrajectoryEvaluator`**（§151），所以这里用 lambda 把原生调用包起来。

**这样 `SV_EvaluateTrajectory` 的校验逻辑（拒绝 `Com_Error` 分支与零时长除法）在调用前就生效**。

## 四、`clientLoadoutBindingsAvailable()`

```cpp
return weaponSlotReadStaged_ != 0 && currentCharacterGet_ != nullptr;
```

注释：

> **与 `valid()` 分开是故意的。这两个驱动 `captureClientLoadoutRequest`，而那是【客户端报告自己 loadout】的路径 —— 所以它们的缺失恰好降级那条路径，而绝不能读成"引擎未绑定"。**

**两个指针**：

```text
weaponSlotReadStaged_   在 bind() 里显式置 0（§214）
currentCharacterGet_    已绑定（§214）
```

**所以这个函数在 OLfinal 上恒返回 `false`**（因为 `weaponSlotReadStaged_ == 0`）。

**这与 §214 里"`valid()` 的注释仍说它无地址"是同一处滞后的另一面。**

## 五、`observeGameThread()`：CAS 记录第一个线程

```cpp
const auto currentThread = GetCurrentThreadId();
auto expected = std::uint32_t{};
if (gameThreadId_.compare_exchange_strong(expected, currentThread,
        memory_order_acq_rel, memory_order_acquire))
    return true;
return expected == currentThread;
```

### 5.1 逻辑

```text
expected 初始为 0
CAS(0 → currentThread) 成功 ⇒ 这是第一个观察到的线程，记录下来，返回 true
CAS 失败 ⇒ expected 被写成当前值
return expected == currentThread
```

**所以**：

- 第一次调用：记录并返回 true；
- 后续同一线程：CAS 失败但 `expected == currentThread` ⇒ true；
- 不同线程：`expected != currentThread` ⇒ **false**。

### 5.2 两种内存序

```text
成功序  memory_order_acq_rel
失败序  memory_order_acquire
```

**成功用 acq_rel**（既是写也是读），**失败用 acquire**（只读）—— 这是 CAS 的标准配对。

**而 `EngineBindings.hpp` 里 `gameThreadId_` 是 `std::atomic<uint32_t>`，初值 0** —— 所以 0 是"未设置"哨兵。

## 六、`nativeServerEntityBindingsAvailable()`

```cpp
return valid() && gEntities_ && serverGameEntitiesPointer_ &&
    serverGameEntityCount_ && svLinkEntity_ && svUnlinkEntity_ && svTrace_ &&
    writableBytes(serverGameEntitiesPointer_, sizeof(*serverGameEntitiesPointer_)) &&
    writableBytes(serverGameEntityCount_, sizeof(*serverGameEntityCount_));
```

**七个非空 + 两个可写**。

**注意 `valid()` 已经检查了其中五个**（`gEntities_`/`svLinkEntity_`/`svUnlinkEntity_`/`svTrace_`/…），所以这里有冗余。

**但那两个 `writableBytes` 是 `valid()` 不检查的** —— 因为它们是**要写的槽**（§215 的 `runtime_slots` 只检查了另外三个）。

## 七、`serverCharacterInfo`：**一份缓冲，两个消费者**

这是本组最重要的一段。

### 7.1 问题

```cpp
// CODREF(bg_update_player_dobj): one buffer, two consumers.
// BG_UpdatePlayerDObj 0x0040B700 is HANDED this pointer, but
// sub_AA94C0 (VA 0x004094C0) DERIVES it from the anim-condition base
// while PM_Footsteps runs inside PmoveSingle.
```

**两个消费者**：

```text
BG_UpdatePlayerDObj   收到这个指针（显式传参）
sub_AA94C0            【自己从 anim-condition 基址推导】
```

### 7.2 私有分配的后果

```text
Handing the DObj path a private allocation left the derived one reading zeroes,
so sub_AA91C0 returned null, no legs animation was ever selected,
and every player stayed on animation record 0
    - a crouched pose that put the whole locational hit skeleton
      ~20 units below the drawn body.
```

**四步因果**：

```text
1. 私有分配 ⇒ 推导路径读到零
2. sub_AA91C0 返回 null
3. 从未选中腿部动画 ⇒ 每个玩家停在动画记录 0
4. 那是一个蹲姿，把整个命中骨架放在绘制身体下方约 20 单位
```

**节点 3→4 尤其重要**：

> **"每一个玩家停在动画记录 0 —— 一个蹲姿，把整个定位命中骨架放在绘制身体下方约 20 单位"**

**"蹲姿"是记录 0** —— 所以骨架矮了 20 单位，**而这正是"打不到头"的机制**。

**与 §198 里"共享动画时钟冻结"是两个不同的原因，但症状相同**（骨架错位）。

### 7.3 唯一的解决办法：放在推导的位置

```cpp
return std::span<std::byte, SvNativeCharacterInfoSize>(
    serverAnimConditionStorage_.data() +
        ServerCharacterInfoBaseOffset +        // 0xAF350
        entityNum * SvNativeCharacterInfoSize, // 0x450
    SvNativeCharacterInfoSize);
```

**所以 `serverCharacterInfo` 不分配，而是返回 `serverAnimConditionStorage_` 里那块** —— 正是引擎会推导的位置。

**`0xAF350 + entityNum * 0x450`** —— 与 §184 的 `ServerCharacterInfoBaseOffset` 与 `SvNativeCharacterInfoSize` 一致。

## 八、`installServerAnimConditionStorage`：CAS 交换 + 写时钟

### 8.1 两段 CAS

```cpp
auto* slot = (void* volatile*)animConditionBasePointer_;
previousBase = (std::byte*)InterlockedCompareExchangePointer(slot, nullptr, nullptr);
if (InterlockedCompareExchangePointer(slot, storage_.data(), previousBase) != previousBase)
    return false;
```

**第一段：`CAS(slot, nullptr, nullptr)` = 纯读**（比较交换成同一个值，等于原子读）。

**第二段：`CAS(slot, previousBase → storage_.data())`** —— 只有当前值仍是 `previousBase` 才写。

**所以是"读-改-写"但不是原子的整体** —— 如果两次之间有别人改了，第二段会失败并返回 false。

### 8.2 写两个时钟

```cpp
*(uint32*)(context + AnimFrameTimeOffset)    = serverAnimationTimeMilliseconds_;  // 0xAF308
*(uint32*)(context + AnimSnapshotTimeOffset) = serverAnimationTimeMilliseconds_;  // 0xAF30C
```

**两个时钟写同一个值** —— 注释解释了：

> **两个词携带同一个服务器时间：CODOL 把本地帧时间与快照服务器时间分开，因为客户端两者都有，而 dedicated 服务器只有它自己的。**

**"客户端两者都有，dedicated 只有自己的"** —— 所以两个槽填同一个值。

### 8.3 为什么在 install 里写

> **它属于这里而不是调用点，因为【每一个】原生动画、DObj 与定位 trace 调用都通过这个 install 到达那个块，而一个对其中一个正确、对下一个陈旧的时钟会在更窄的窗口里复现同一个冻结动画故障。**

**"同一个故障会在更窄的窗口里复现"** —— 这是**把不变量放在唯一入口**的理由。

## 九、`restoreServerAnimConditionStorage`：**带条件的恢复**

```cpp
return InterlockedCompareExchangePointer(
    (void* volatile*)animConditionBasePointer_,
    previousBase,                     // 新值
    serverAnimConditionStorage_.data() // 【只有当前是这个才换】
) == serverAnimConditionStorage_.data();
```

**第三参数是"比较值"** —— **只有当前仍是我们的存储时才恢复**。

**所以如果中途别人改了，恢复失败并返回 false** —— 而不是覆盖别人的值。

**这与 §196 里 `serverDObjFreeAdapter` 的空 `__except` 形成对照**：那里失败就算了，这里失败要报告。

## 十、`MSG_Init`：ESI + 两个栈参数

```asm
push esi
mov esi, messagePointer
push bufferLength
push bufferData
call function
add esp, 8
pop esi
```

**`msg_t*` 在 ESI、`data` 与 `length` 在栈**。

**`push esi`/`pop esi`** 包住 —— 因为 ESI 既是参数又是被调用者保存寄存器。

**压栈顺序 `bufferLength` 先、`bufferData` 后** ⇒ `bufferData` 在 `[esp+0]`（第一个栈参）✓

## 十一、关键结论

1. **`requiredBytes` 是"用到的最远偏移 + 1"**，而不是结构总大小（3834/3838/1952 三个数各不同）。
2. **两次 `readableSpan` 校验两级间接** —— 防止野定义指针。
3. **`directionToAngles` 与 `evaluateTrajectory` 都内联 RVA + 每次校验** —— 与 `bind()` 统一校验不一致。
4. **`clientLoadoutBindingsAvailable()` 在 OLfinal 上恒 false**。
5. **`observeGameThread()` 用 CAS 记录第一个线程**，0 是未设置哨兵。
6. **一份缓冲两个消费者**：`BG_UpdatePlayerDObj` 收指针而 `sub_AA94C0` 自己推导 ⇒ 必须放在推导的位置。
7. **私有分配导致"每个玩家停在动画记录 0（蹲姿），命中骨架在绘制身体下方约 20 单位"** —— 这是"打不到头"的机制之一。
8. **`restore` 用带条件的 CAS** —— 只有仍是我们的时候才换回。

## 十二、未闭合点

- `serverAnimationTimeMilliseconds_` 由谁更新未在本组。
- `EngineBindings.cpp` 4510 行之后未读取。
