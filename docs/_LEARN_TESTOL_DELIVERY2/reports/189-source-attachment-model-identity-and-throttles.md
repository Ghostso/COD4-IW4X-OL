# 189 · 附件翻译的模型索引身份、`__usercall`、缓冲区的 alignas

## 一、范围

本报告学习 `EngineBindings.hpp` 1893–2152 行。

## 二、附件的跨武器身份是**模型索引**

这是本组最重要的一段。

### 2.1 问题

```text
profile 为一个瞄具存【一个】附件物品，并把它挂在好几把不同的武器上
    —— 物品 25703 出现在三个职业的 ordinal 23 上，而这三个职业的主武器是两把不同的枪
但模块化串里的 id 是【每武器】的：
    6206  是 red_rmrtmp
    14268 是 red_rmrm9
而零售把它们各发布在自己的武器上
```

### 2.2 解法

> **把它们绑在一起的是【模型索引】**。两个 RMR 都解析到模型 17，两个扩容弹匣都到 10，`mag_fast*` 到 11，`mag_fmj*` 到 12。
>
> **所以模型索引是附件的武器无关身份**，而翻译就是：**找到这个物品在任何地方命名的模型，然后在【目标武器】的表里找携带同一模型的条目。**

### 2.3 失败即诚实

> **当目标武器没有该模型的条目时返回空**，**这是"一把不吃红点的枪"的诚实答案**。

### 2.4 翻译后的 id 必须带自己的名字

```cpp
// dword_1978640[id] -- the string an interned attachment id stands for. The
// merged list is keyed by NAME downstream, so a translated id has to carry its
// own name with it or the merge re-looks-up the one we just replaced.
```

**这是"下游按名字键控"的直接后果**：翻译只换 id 不换名字，会让合并重新查回被替换掉的那个。

## 三、`attachmentSupportedByWeapon`：表存在性就是支持性

### 3.1 那次真实的崩溃

```text
attachmentModelResolutionAvailable 回答"用哪个模型"，
而 out.exe 自己的查找 sub_42F9B0 在附件不在武器的表里时返回 NONE 模型
    —— 一个【合法】答案，意思是"这把武器没有它的模型"。
把它读成"可用"，就是把一个红点装上了 MSR，
并在出生时让客户端以 `1073 tag_reticle_red_dot ..._vmchar` fault 掉（§187）。
```

### 3.2 注册侧给出答案

```text
sub_42F910 把 (attachment, model) 对追加到 word_198C0A0[128 * weapon]，
并在模型是 none model 时【完全跳过追加】
所以表里正好持有武器真的拥有模型的那些附件
⇒ 【表内的存在性】才是支持测试，而那是注册不变量而不是推断
```

**"注册不变量而不是推断"** —— 这句话把"怎么判断"从"试验"提升到"从产生方式推出"。

## 四、`OwnershipResolver` 是 `__usercall`

```cpp
// sub_5E3760, the ownership resolver behind 94 call sites.
// int __usercall(int itemId@<eax>, void *outRecord@<edi>) -> eax;
// the record's +4 is a u16 set to 1 when the item is owned.
```

**`@<eax>` / `@<edi>` 是 MSVC 的 `__usercall` 语法**标注 —— 两个参数都在寄存器里，返回值在 EAX。

**94 个调用点** —— 这是一条被广泛使用的函数。

`outRecord + 4` 是 `u16`，拥有时为 1。

## 五、`traceServerLocationalEntities` 的存在理由

```cpp
// CODREF(sv_trace): what 3.3.3.3's SV_PointTraceToEntity 0x005FB510
// does per entity, in this project, because 1649370 does not contain
// that function at all (section 73). Bones are posed in MODEL space, so
// the ray is carried into it by the entity's own origin and angles and
// the hit normal is carried back out.
```

**本 build 完全没有这个函数** ⇒ 必须在本项目里重实现。

关键几何：

```text
骨骼在【模型空间】摆姿
所以射线要用实体自己的 origin 与 angles 带进模型空间
命中法线再带出来
```

`priorityMap` 参数与之前的 `SV_GetLocationalPriorityMap` 直接衔接。

## 六、`NativeServerEntityMirrorSlot` 的四个字段

```cpp
struct NativeServerEntityMirrorSlot {
    SvCollisionEntity source;          // 源
    SvNativeServerEntity baseline;     // 基线
    SvNativeServerEntity sourceProjection;  // 投影
    SvNativeServerEntity linkedImage;       // 链接后
};
```

**四个阶段各一份**，所以每一次发布都可以回滚到前一阶段。

## 七、五个计数器：`Count` / `Mismatch` / `Unavailable` / `Mask` / `Failure`

```cpp
mutable std::uint64_t nativeTraceComparisonCount_;
mutable std::uint64_t nativeTraceMismatchCount_;
mutable std::uint64_t nativeTraceUnavailableCount_;
mutable std::uint32_t nativeTraceLoggedDifferenceMask_;
mutable std::string nativeTraceComparisonFailure_;
mutable bool nativeTraceComparisonObservedSuccess_;
```

**三态计数**：比较过（Count）／不一致（Mismatch）／查不了（Unavailable）。

**`LoggedDifferenceMask` 是位掩码** —— 每种差异类型只记一次（与 `SvTraceComparisonDifference` 枚举对应）。

**`ObservedSuccess_` 是布尔** —— "曾经成功过一次"，用于区分"一直失败"与"还没跑过"。

## 八、`ActorHitPoseOwner` 与"树头复用"

```cpp
struct ActorHitPoseOwner {
    alignas(8) std::array<std::uint32_t, 2> tree{};
    SvActorHitPose source{};
    void *dobj{};
    std::uint32_t updatedTime{};
    bool failed{};
};
mutable std::array<ActorHitPoseOwner, 2048> actorHitPoseOwners_{};
```

注释：

> **稳定的有界所有者；原生 XAnim 节点在移除/代际变化时被释放。树头被【复用】，绝不每次重生都从关卡 hunk 重新分配。**

`alignas(8)` 在树头上 —— 因为它是原生结构，需要对齐。

**2048 项**与 `MaximumGameEntities` 一致。

## 九、两处 `alignas(16)` 的静态缓冲

```cpp
alignas(16) mutable std::array<std::byte, ServerAnimConditionStorageSize> serverAnimConditionStorage_;   // 0x100000
alignas(16) mutable std::array<std::byte, ServerLoadAnimStorageSize>      serverLoadAnimStorage_;        // 0x12000
```

**两个缓冲都是 `alignas(16)`** —— 因为它们会被原生代码当作结构化数据访问（含 SSE 对齐要求）。

### 9.1 总静态占用

```text
serverAnimConditionStorage_    1,048,576
serverLoadAnimStorage_            73,728
nativeServerCharacterInfo_   18 × 0x450 = 27,864
nativeServerDObjSkelArena_   18 × 256 × 32 = 147,456
actorHitPoseOwners_          2048 × ~40 ≈ 82,000
```

**约 1.38 MB 的静态数组在 `EngineBindings` 里** —— 这是它作为单例被持有时的固定成本。

## 十、`nativeServerDObjSkelArena` 的尺寸推导

```cpp
static constexpr std::size_t NativeServerDObjSkelArenaSize = 18 * 256 * 32;
```

```text
18 = 客户端槽数
256 = 每个 DObj 的骨骼上限（推测，需核）
32 = 每根骨骼的姿势字节数（DObjAnimMat 是 32 字节）
```

`used_` 与 `skelEpoch_` 说明这是**一个线性分配的 arena**，按代际回收。

## 十一、日志节流的**八种不同机制**

在这一段里能看到至少八种：

```text
1. 计数器封顶        nativeServerDObjSkeletonLogCounter_
2. 位掩码只记一次    nativeTraceLoggedDifferenceMask_
3. 边沿触发          lastLoadoutRefusal_（指针比较做身份测试）
4. 字符串去重        lastDefaultAttachmentRefusal_ / lastBlankEnabledNote_
5. 哨兵初始值        lastCharacterIndexRefusal_{-2}（-2 = 无拒绝记录）
6. 状态数组          playerDObjReportedState_[64]
7. 字符串数组        nativeServerAnimationReport_[64]
8. 布尔"曾成功"      nativeServerEntityMirrorObservedSuccess_
```

**每一种针对不同的"重复模式"**：

- 纯计数（每秒几十条）；
- 类型有限（差异种类）；
- 字面量身份（指针）；
- 内容身份（字符串）；
- 有意义的哨兵值；
- 每实体状态机；
- 每实体一行；
- 全局一次性。

## 十二、`lastLoadoutRefusal_` 是 `const char*` 而不是 `std::string`

```cpp
// Edge-trigger for the capture-refusal line. A literal each time, so pointer
// comparison is the identity test and no allocation happens on the hot path.
mutable const char *lastLoadoutRefusal_{};
```

**每次都是字面量 ⇒ 指针比较即身份测试 ⇒ 热路径零分配**。

这是一个很干净的模式：`const char*` + 字面量 + 指针比较。

## 十三、关键结论

1. **附件的跨武器身份是模型索引**，不是物品 id，也不是名字。
2. **表内存在性 = 支持性**（注册时跳过 none model ⇒ 这是不变量）。
3. **`__usercall` 的 94 个调用点**说明它是核心函数。
4. **本 build 缺 `SV_PointTraceToEntity`，必须自己实现**，且骨骼在模型空间。
5. **三态计数（比较/不一致/查不了）+ 位掩码 + 曾成功布尔**是差异报告的完整形态。
6. **字面量指针比较做边沿触发**是热路径零分配的标准做法。
7. **八种日志节流机制各有针对性**。

## 十四、未闭合点

- `NativeServerDObjSkelArenaSize = 18*256*32` 里 256 的来源未在本组确认。
- `EngineBindings.hpp` 2152 行之后未读取。
