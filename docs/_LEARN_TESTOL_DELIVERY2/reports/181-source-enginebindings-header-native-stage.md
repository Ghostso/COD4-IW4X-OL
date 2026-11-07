# 181 · EngineBindings 头文件（前段）：原生阶段的故障归因

## 一、范围

本报告学习 `EngineBindings.hpp` 前 200 行。

## 二、`NativeStageScope`：给 SEH 加一个"当前在调谁"的标签

### 2.1 问题

```cpp
// THE NAME OF THE NATIVE STAGE CURRENTLY EXECUTING, for the vectored fault witness.
// Every clientThink stage calls into the same shared BG code, so a faulting RVA on its
// own cannot say which of ol-mod's calls arrived there.
```

**同一个 RVA 可能来自多个调用者**，所以单看崩溃地址说不清是谁调进来的。

### 2.2 解法

```cpp
const char *SV_CurrentNativeStage();
void SV_SetCurrentNativeStage(const char *stage);

struct NativeStageScope {
    explicit NativeStageScope(const char *stage) { SV_SetCurrentNativeStage(stage); }
    ~NativeStageScope() { SV_SetCurrentNativeStage("none"); }
    // 不可拷贝不可赋值
};
```

**RAII + 字符串字面量**：不分配、不持锁、恢复值固定为 `"none"`。

用例（前面报告里见过）：

```cpp
const NativeStageScope stage{ "playerstate_to_entitystate" };
return invokePlayerStateToEntityState(...);
```

所以崩溃日志可以说"当时正在 `playerstate_to_entitystate` 阶段"。

### 2.3 RAII 的代价

`SV_SetCurrentNativeStage` 若用 `thread_local` 指针，则：**跨线程无效**（另一个线程崩了看不到本线程的标签）。这解释了为什么 `NativeStageScope` 不能做成普通成员——它是**线程局部**的。

而 `""none""` 这个恢复值是**硬编码**而不是保存旧值——因为 `NativeStageScope` **不可嵌套**（注释没写，但从"不可拷贝"与固定恢复值可以推出设计意图是扁平使用）。

## 三、`NativeExceptionDetails`：十四个字段

```text
code / address / accessType / faultAddress
eax ebx ecx edx esi edi ebp esp eip
```

**全部六个通用寄存器 + ebp/esp/eip**。

`accessType` 来自 `EXCEPTION_RECORD::ExceptionInformation[0]`（读/写/执行），`faultAddress` 来自 `[1]`——这两个字段在 `EXCEPTION_ACCESS_VIOLATION` 里有意义，其它异常码下无意义。

**保留 `address` 与 `faultAddress` 两个**：前者是异常记录里的地址，后者是被访问的地址，二者不同（一个是"在某处发生了"，一个是"试图访问某处"）。

## 四、四套失败分类法，各管一段

### 4.1 `ClientLoadoutResolveFailure`（16 项）

```text
None / StagedSlot / NativeResolverUnavailable / ItemName
BaseWeaponLookup / BaseWeaponResolver / DefaultAttachments
EquippedAttachmentName / EquippedAttachmentSlot / AttachmentMerge
AttachmentLookup / AttachmentCapacity / ModularWeaponResolver
WeaponDefinition / ModularWeaponDependency / AttachmentModelResolution
```

**沿装配流程排布**：从槽位 → 名字 → 基础武器 → 默认附件 → 装备附件 → 合并 → 查找 → 容量 → 模块化 → 定义 → 依赖 → 模型。

这与之前报告里"附件问题必须只损失一个附件"对应——`AttachmentMerge` 是其中一环。

### 4.2 `WeaponRegistryInitializationStatus`（3 项）

```text
Ready / CommonAssetsUnavailable / InitializationFailed
```

只有三项，因为它是**初始化**而不是**装配**。

### 4.3 `AlphaWeaponPortStatus`（9 项）

```text
Disabled / WaitingForCommonAssets / WaitingForWeaponRegistry
WrongThread / SourceAssetMissing / InvalidDefinition
LinkFailed / RegistrationFailed / Ready
```

**两个 `WaitingFor*` 与 `WrongThread`** —— 说明这是一个有前置依赖、有线程要求的过程。

### 4.4 `ServerAnimationInitializationStatus`（14 项）

```text
NotInitialized / Ready / InvalidBinding / WrongThread / ContextBusy
BeginLoadAnimTreesFailed / LoadAnimTreesFailed
AnimationScriptAssetsUnavailable / FindAnimsFailed / ParseAnimScriptFailed
PrecacheAnimTreesFailed / FindAnimTreesFailed / EndLoadAnimTreesFailed
FinalizePlayerAnimsFailed / InvalidOutput
```

**这一段最有价值**：它把动画初始化拆成**九个具名步骤**：

```text
BeginLoadAnimTrees
LoadAnimTrees
AnimationScriptAssets
FindAnims
ParseAnimScript
PrecacheAnimTrees
FindAnimTrees
EndLoadAnimTrees
FinalizePlayerAnims
```

而 `InvalidOutput` 是第九步之后的检查。

这与之前报告里"519 vs 123 的 animtree 差异"直接相关——**这九个步骤里任何一步失败都有具名状态**。

### 4.5 `ClientCharacterPresentationResolveFailure`（9 项）

```text
None / InvalidRequest / ItemName / Selection
BaseItemDefinition / CharacterDefinitionTable / CharacterDefinition
ViewmodelConfigString / ConstantConfigStrings
```

`ClientCharacterPresentationResolveStatus` 带三个附加字段：

```cpp
failure / recordIndex(0xFFFFFFFF 哨兵) / itemId
```

`recordIndex` 是**哪一条角色记录失败**，`itemId` 是**哪个物品**——两个维度。

## 五、颜色选择器的那个置换

```cpp
CODOL_CharacterCustomization_BuildLocalModelList 0x00569C50
    把 +3 处的次级角色定义字节映射成颜色名
CODOL_CharacterCustomization_ColorNameToSelector 0x0040C4C0
    把颜色名映射成模型变体选择子

constexpr std::array<uint8_t,4> SelectorByDefinitionValue{ 0, 3, 1, 2 };
```

注释给了完整的推导：

> `BuildLocalModelList 0x00569CFA..0x00569D20` 把 **0/1/2/3 映射到 wht/cau/yel/blk**。**原生选择子表 `0x0040C4C0` 是 wht/yel/blk/cau**，**因此这个精确的置换**。

即：

```text
定义值 → 颜色名 → 选择子
0 → wht → 0
1 → cau → 3
2 → yel → 1
3 → blk → 2
```

**两张表的顺序不同**，所以置换是 `{0,3,1,2}` 而不是恒等。这是一个"两个有序表取复合"的干净例子。

越界返回 `nullopt`。

### 5.1 为什么这是 CODOL 特有

> **这是一个 CODOL 商城层；BO1/Ghosts 在没有这个枚举的情况下生成它们的服务端角色模型。**

即：颜色选择器属于商城外观系统，不是基础角色系统。

## 六、`XAssetHeader`

```cpp
struct XAssetHeader { void *data{}; };
```

注释：

> **CODOL 的 XAssetHeader 在这个 x86 构建里是一个单指针 union**；只有通用数据视图穿过这个头文件。

即：`XAssetHeader` 在各版本里是 union，但这里只暴露通用指针——**不假装知道具体类型**。

这与之前 `SV_ForgeFindXAsset` 返回 `void*` 是同一策略。

## 七、关键结论

1. **共享代码段里的崩溃需要"当前阶段"标签**，而 RVA 本身说不清是谁调进来的。
2. **`NativeStageScope` 用 RAII + 字面量**，零分配零锁，但恢复值是硬编码的 `"none"`（不可嵌套）。
3. **`address` 与 `faultAddress` 是两回事**：一个说"在哪发生了"，一个说"试图访问哪"。
4. **四套失败分类法按流程排布**，其中动画初始化拆成九个具名步骤。
5. **两个有序表复合产生置换**（`{0,3,1,2}`），而不是恒等——因为它跨了两张顺序不同的表。
6. **`XAssetHeader` 只暴露通用指针**，不假装知道 union 的具体成员。

## 八、未闭合点

- `ServerAnimationInitializationStatus` 的九个步骤各自失败的具体条件未在本组。
- `EngineBindings.hpp` 200 行之后的大量绑定声明未读取。
- 519 vs 123 的归因结论仍未出现。
