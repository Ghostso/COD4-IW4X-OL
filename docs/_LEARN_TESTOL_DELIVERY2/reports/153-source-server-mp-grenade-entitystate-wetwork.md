# 153 · 手雷发射/引爆、原生 entityState、Wetwork 场景

## 一、范围

本报告完整学习 **4 个头文件**：

- `sv_grenade_launch_mp.hpp`（47 行）
- `sv_grenade_detonation_mp.hpp`（61 行）
- `sv_native_entitystate_mp.hpp`（前 90 行）
- `sv_wetwork_scene_mp.hpp`（18 行）

`server_mp` 进度推进到 **143/154**。

## 二、手雷发射：只计算，不消耗

```cpp
struct SvGrenadeLaunchParameters {
    weapon;
    speed; speedUp;
    fuseMilliseconds;
    bool cookOffHold;
    bool timedDetonation;
};
```

注释：这是恢复的**发射字段，不是替换的 WeaponDef**。其它投射物属性（接触、激活、旋转策略）是**各自独立的所有者**。

`SvGrenadeLaunchRequest`：

```text
parameters / basis / playerVelocity
angularVelocity            // 调用方拥有旋转策略与随机性
time / owner / heldFuseMilliseconds
rotate
```

`angularVelocity` 的注释很关键：

> 调用方拥有旋转策略/随机性。**把它的种子随命令候选一起复制；一次失败的发射绝不能推进一个全局 RNG。**

`SV_ComputeGrenadeLaunch(request, toAngles)` 的边界：

> 普通玩家投掷（**没有**额外的水平/相对向上速度，**没有**距离激活）。负的持有计时器属于单独的 in-hand/throwback 事件路径。**这个函数计算一个生成请求，而不消耗弹药或引信。**

即：`Compute` 是纯的，扣弹药/扣引信在事务提交侧。

## 三、手雷引爆：只处理"普通干手雷"

### 3.1 爆炸参数

```text
weapon / radius / innerDamage / outerDamage
coneAngleDegrees = 180.0f
traceAlongContact / forceNormalUp
```

准入门：

> **只处理普通手雷爆炸。**闪光/烟雾/重型/刀需要它们各自的后续，**绝不能静默变成普通溅射伤害**。

`coneAngleDegrees` 默认 180.0 与之前报告里"cone 必须恰是 180.0f"一致——即锥形默认对全向爆炸是退化的。

### 3.2 请求与三个前置

```text
parameters / time / weaponName
surfaceTraceMask / radiusTraceMask     // 显式
ignoreClientNum
```

`surfaceTraceMask` 的注释：

> **调用方必须先确立爆炸在水外。**掩码保持显式，直到生产 trace 策略被选中。

### 3.3 `SV_ComputeDryGrenadeDetonation` 的六条外部依赖

```text
targets                帧局部可伤害目标
evaluate               原生轨迹求值
surfaceTrace           表面 trace
encodeDirection        方向编码
anglesToForward        角度→前向
visibility             半径伤害可见性
```

返回 `optional<SvMissileDetonation>`，注释：

> 完成一个**已准入的干普通手雷**的到期引信。提供者只查询保留原语；返回的引爆走既有帧事务。**盾反馈/flags 与水是独立后续，所以受盾保护的目标不会被静默派发。**

"受盾保护的目标不会被静默派发"——即宁可跳过，也不按普通溅射处理。

## 四、原生 entityState：0x118 与两个被更正的常量

### 4.1 尺寸

```text
CODDIFF(1649370): 0x110 是 3.3.3.3 的 entityState_s。
本 build 拷 0x118 —— 这里的八处是 `mov ecx, 70; rep movsd`，
3.3.3.3 的六处是 `mov ecx, 68` —— 正好是 netfield 对齐在尾部预测的 +8。
```

### 4.2 `SvEntityEventCount = 170` 的真正含义

```text
CODDIFF(1649370): 170，原 162。
这是事件参数宽度表 dword_DA9410 的长度——即有声明参数宽度的事件数量，
因此也是事件实体类型（ET_EVENTS + event）的范围。
```

**它不是一个实体事件环里 event id 的边界**：

> **codec -94 把那个 id 写成裸字节**，而客户端自己的解码器对表内或表外的 id 都给零参数宽度，而不是拒绝快照。

⇒ `SvMaximumEntityEventId = 0xFF` 才是 id 的边界。

这两个常量的区分很重要：**表长 ≠ id 域**。混用会让超过 170 的合法事件被误拒。

### 4.3 `unk00A0` 是 28 位不是 13 位

```text
CODOL ET_PLAYER field 35 / entityState_s +0xA0
原生转换拥有它的值；确切的玩法语义仍未知
```

```text
CODDIFF(1649370): 二十八位，不是 3.3.3.3 的十三位。
codec -55 的四组 present-bit 到达第 27 位
    (2<<0, 4<<2, 11<<6, 5<<17, 然后 22..27 的单比特)
所以值需要 32 位来容纳，0x0FFFFFFF 来界定。
```

注释自我说明：

> **codec、字段索引 37 和偏移 0xA4 都被移植了；类型和它的边界被留在 3.3.3.3 的两组 13 位形状。**

这是一条典型的"局部移植"缺陷记录：偏移改了、类型没改。

### 4.4 `+0xD2` 是第三人称呈现选择器

> `BG_PlayerToEntity_SetMisc` 通常拷当前武器，但它的 **WeaponDef-type-3 分支**从 `playerState +0x344` 取值。

### 4.5 address-bound 元数据不在原生 ABI 内

```cpp
std::array<std::byte, Size> bytes{};
bool secureOriginAddressBound{};    // 源侧元数据，不属于 CODOL 的 0x110 字节 ABI
```

注释里仍写 0x110——一处遗留笔误（实际 Size 已是 0x118）。

`SvNativeEntityState` 有显式的拷贝/移动构造与赋值（因为 `secureOriginAddressBound` 需要随字节一起同步），且 `static_assert(alignof == alignof(uint32_t))`。

## 五、Wetwork 场景：const 收尾之后的 180 个全状态 mover

```text
Wetwork 把 mission 拥有的 mover 叠在 mp_cargoship 的 const 场景上。
const fastfile 止于实体 823；零售准入快照还携带 180 个全状态 mover。
它们的布局与 SvConstBaselineEntry 已表示的同一子集相同，
但它们是【传输状态】而不是客户端侧的 delta 基线。
```

这句"是传输状态不是基线"是关键区别：

- const baseline 表是 **delta 的参照物**（客户端拿去和自己算的比）；
- Wetwork 这 180 个是**实际要发的完整状态**（因为它们的 origin/model 不在地图 const 里）。

`using SvWetworkSceneEntry = SvConstBaselineEntry;` —— **借用同一结构体**，因为字段子集恰好够。

## 六、关键结论

1. **`Compute` 与"消耗"必须分开**：发射不扣弹药/引信，引爆不派发受盾目标。
2. **失败的发射不能推进全局 RNG**——种子必须随命令候选复制。
3. **表长 ≠ id 域**：`SvEntityEventCount=170` 是参数宽度表长，event id 边界是 0xFF。
4. **局部移植是最隐蔽的缺陷**：`unk00A0` 的 codec/索引/偏移都改了，唯独类型与边界留着 13 位。
5. **const baseline 与"传输状态"是两种东西**，虽然结构可以共用。

## 七、未闭合点

- `unk00A0` 的确切玩法语义未知（值域已纠正到 28 位）。
- 盾反馈/flags 与水是独立后续，本组未实现。
- flash/smoke/heavy/knife 的爆炸后续全部未接，且明确禁止退化为普通溅射。
- 手雷引爆的 trace 策略（surfaceTraceMask / radiusTraceMask）仍未选定。
