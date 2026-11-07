# 182 · EngineBindings 头文件（中段）：少一个参数的后果

## 一、范围

本报告学习 `EngineBindings.hpp` 200–419 行。

## 二、`ClientWeaponSelection`：一条武器在源侧的完整投影

35 个字段，可以分五组：

```text
身份    itemId / baseWeaponAssetIndex / weaponAssetIndex / ammoIndex / clipIndex
尺寸    clipSize / maxAmmo / shotCount / attachmentCount
分类    weaponType / weaponClass / penetrateType / impactType / fireType
时序    fireDelayMs / fireTimeMs / dropTimeMs / raiseTimeMs
散布    6 个 hipSpread + adsSpread
伤害    damageCurve / hitLocationMultipliers[HitLocationCount]
标志    aimDownSight / hasOverlayReticle / rifleBullet / bulletExplosiveDamage
        dualWieldCapable / fmjPenetration
附件    6 个 attachmentItemIds + 15 个 attachmentAssetIndexes
模块化  modularValue8 / modularValue9 / modularDependencies
名字    weaponName
```

### 2.1 FMJ 的那句规则

```cpp
// 28700: the loadout carries FMJ. The operator's rule is explicit --
// "普通穿透是 1，装上 FMJ 就是 2" -- so the bullet path doubles the
// material depth instead of consulting a second table. Set from the
// merged attachment NAME list below, where "mag_fmj*" already appears.
```

**设置来源是已合并的附件名列表**——与之前报告里"去重键是名字"直接衔接：`mag_fmj*` 在合并后的名字列表里存活，所以这里能看见它。

### 2.2 两个附件数组尺寸不同

```cpp
std::array<std::uint32_t, 6>  attachmentItemIds{};      // 6
std::array<std::uint32_t, MaximumModularWeaponAttachmentCount>  // 15
    attachmentAssetIndexes{};
```

**6 vs 15** 的原因在 `sv_weapon_loadout_mp.hpp` 里没有直接写，但结合 `TriggerHintRules` 与之前的 `primaryAttach` 在 16、`secondaryAttach` 在 23 且"宽 6"，可以推断 **6 是 profile 槽位数，15 是线格式的附件上限**。

### 2.3 `ClientWeaponLoadout`

```cpp
characterIndex / classIndex / primary / secondary
```

只有两把枪，没有副手（lethal/tactical）——那些在 `SvResolvedEquipment` 里。

## 三、`GenericCharacterViewhandsName = "viewhands_tf141"`

```cpp
// The viewhands model every character falls back to. The client finds its own
// viewmodelIndex by searching the model configstrings for this exact name, so
// the server resolves it the same way rather than inventing an index.
```

**服务端用同一个名字去查**，而不是硬编码一个索引。这与之前报告里"动画索引必须由本引擎解析"是同一条纪律。

## 四、`ClientCharacterPresentation`：12 个槽的两个来源

```text
selectionIds[11]        11 个选择
characterItemId         第 0 号，来自 characterClasses[<character>].slots[0]
recordItemIds[12]       0..11，其中 0 镜像 characterItemId
```

注释：

> §67 的输入，**而它就是全部输入**。引擎从角色自身的 per-slot 默认值推导另外十一个记录项，**所以这一个 id 就是模型解析所需的东西**。

```cpp
// It is NOT a wire field and SV_PackCharacterCustomization does not touch it.
std::uint16_t characterItemId{};
```

**明确标注"不是线字段"**——防止有人把它塞进打包路径。

`recordItemIds` 的说明：

> 条目 0 镜像 `characterItemId`；条目 1..11 是服装件，**每一件已经在它自己的 item definition 声称的记录条目上**。**零是 `sub_619AD0` 从角色 per-slot 默认值填充的**，所以空数组正好是旧行为。

**"空数组 = 旧行为"是一个重要设计**：新字段不影响未使用它的路径。

## 五、审计方法的公开化

```cpp
// THE AUDITS ARE PUBLIC because the client bridge can now trigger them on a
// RUNNING client (DedicatedControl::MessageType::RunDiagnostic). Every one of
// these used to cost a full cycle -- rebuild, relaunch, and the player queueing up
// again -- to answer a question that is a loop over a table the client already holds.
```

**这句话值得记**：审计从"每次要一整轮"变成"运行中触发"，因为**它们只是遍历客户端已经持有的表**。

公开的审计：

```text
auditWeaponItemsTable / auditRewardTable / reportUnlockAllCoverage
probeOwnership / auditItemNames / auditEquippedPerks / auditEquippedEquipment
```

## 六、连杀武器解析的三层

```cpp
resolveUavWeapon()                       // 固定名字
resolveAc130Weapon()                     // 固定名字 killstreak_ac130_mp
resolveKillstreakWeapon(std::string_view name)   // 通用
```

注释说 `resolveAc130Weapon` **走同一条解析路径**，只换名字。而 `resolveKillstreakWeapon` 是**通用化**：

> **任意名字走同一条已验证路径**，供探测与后续"槽 → 连杀物品 → 授予"链路复用。

**三层是逐步泛化的结果**，不是一次设计出来的。

## 七、`characterCatalog()` 的三个要点

```cpp
// The catalogue is not a file: it is the intersection of the item table
// (id -> internal name, readItemInternalName) with the rows of
// mp/coCharItemStatsTable.csv, whose column 0 IS that same internal name
```

**目录不是文件，是两个来源的交集**。

```cpp
// EXPENSIVE THE FIRST TIME (the same ~60,000-lookup sweep auditItemNames
// runs), so call it off the frame thread and never while holding a lock
// the frame wants.
```

**六万次查找**，所以：

1. 不在帧线程调用；
2. 不持帧想要的锁。

## 八、`altWeaponAssetIndex` 的两个关键事实

```cpp
// SECTION 190: the weapon's ALT, straight off weaponDefinition +3720.
// sub_42EF60 links it from the name at +3716 during registration, and
// for a modular weapon it BUILDS the modular alt (sub_431490) rather
// than looking one up -- so this is already correct for the `** ...`
// weapons this server publishes. 0 means the weapon has no alt.
```

1. **偏移 `+3720` 是索引，`+3716` 是名字**——与之前报告里 `SV_SetAltWeaponResolver` 的说明一致；
2. **模块化武器的 alt 是构建出来的**，不是查表——所以 `** ` 开头的武器也对。

## 九、`DB_FindXAssetHeader`：少一个参数的完整病理

这是本组最重要的一段。

### 9.1 两个形式

```text
sub_49CF30(type, name, allowDefault)   <- 0x09CF30，绑定的这个
sub_49D3B0(type, name)                 <- 0x09D3B0，硬编码 1 的包装
```

### 9.2 为什么只读一个调用点会误判

> 武器解析器恰好调的是**包装**，而**只读那一个调用点就导致这里一度被声明成两个参数**。

### 9.3 为什么不会崩——这才是最危险的地方

> 在 `__cdecl` 下**调用者清理**，所以**丢掉参数也不会崩**：被调用者从**调用者栈上恰好放着的东西**里读 `allowDefault`，而 `if (a3)` 然后**随机决定**一个缺失的资产是回来成 `nullptr` 还是**一个刚创建的、内部字符串为空的默认占位符**。

**三重危险**：

1. 不崩；
2. 行为随机（取决于栈上残留）；
3. 两种结果都是"看起来能跑"。

### 9.4 工具的那个缺陷

> `audit-binding-abi.py --reference` 在两个构建上都读 `+0x8`、`+0xC` 和 `+0x10`。**它直到停止在第一次调用处结束扫描才看见这一点**：`sub_49CF30` 在 **`0x49D335`** 读 `a3`，**在十几次调用之后**。

即：**扫描工具只看了函数开头**，而这个函数在十几条 call 之后才用到第三个参数。

### 9.5 `findXAsset()` 仍要单独问 `DB_IsXAssetDefault`

```text
allowDefault=false 只在【未命中】路径上抑制默认值 ——
一个存在但尚未加载的资产仍然会作为默认值回来。
```

**这是第二个必须的检查**，`allowDefault=false` 不够。

## 十、自定义 ABI 的那两个 typedef

### 10.1 `sub_619E90`：EAX + 一个栈参数

```text
618bbe  push ecx        ; 144 字节目标记录
618bbf  mov eax, edi    ; <- 索引，在 EAX
618bc1  call sub_619E90
618bc6  add esp, 4      ; 一个栈参数，调用者清理
```

**两个参数，第一个在 EAX** ⇒ 无 C 调用约定 ⇒ 存成裸指针。

### 10.2 索引是**会话成员**索引不是角色索引

```text
edi 是一个跑 0 .. dword_82E13A4-1 的循环计数器
sub_619E90 把它按 160 缩放（lea edi,[edi+edi*4] 然后 shl edi,5）
  → 成员数组 unk_C911424
sub_620B90 用 v0 <= 0x11 清那个数组 —— 十八项 = MaximumSessionMembers
  而不是 CharacterItemCount 的十二
```

### 10.3 声明错的后果

> **声明成 `void(__cdecl*)(void*)` 时，它在 EAX 里跑的是最后一个表达式留下的东西**，也就是说**它按任意偏移索引了成员数组**。

这与 `BG_PlayerStateToEntityState` 的参数位置错误是同一类：**不崩，但用错数据**。

## 十一、关键结论

1. **少一个参数不会崩，因为 `__cdecl` 由调用者清理**——这使错误完全静默。
2. **只读一个调用点会误判 ABI**，而这个函数在十几条 call 之后才用第三个参数。
3. **`allowDefault=false` 不够**，还需单独问 `DB_IsXAssetDefault`。
4. **"空数组 = 旧行为"** 让新字段不影响未使用的路径。
5. **审计方法公开化**把"一轮重编译"变成"运行中触发"。
6. **抽象要逐步泛化**：固定名字 → 固定名字（换了名字）→ 任意名字。

## 十二、未闭合点

- `ClientWeaponSelection` 的 6 vs 15 两个附件数组的语义差未在本组确认。
- `EngineBindings.hpp` 419 行之后的声明未读取。
