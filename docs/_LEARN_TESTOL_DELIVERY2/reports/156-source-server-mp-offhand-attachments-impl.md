# 156 · 投掷物分类、武器附件合并（实现）

## 一、范围

本报告学习 **2 处实现**：

- `sv_offhand_kind_mp.cpp`（29 行，完整）
- `sv_weapon_loadout_mp.cpp` 前段（80 行）

`server_mp` 进度推进到 **151/154**。

## 二、投掷物分类：名字匹配的三层顺序

### 2.1 第一层：排除"不是丢出去"的

```cpp
if (contains(name,"claymore") || contains(name,"c4") ||
    contains(name,"betty")   || contains(name,"throwing") ||
    contains(name,"trap"))
    return nullopt;
```

五个关键词覆盖：放置类地雷（claymore / betty）、遥控炸药（c4）、投掷冷兵器（throwing*）、陷阱（*trap*）。

注释：**先排除**。这很重要——如果先判 grenade，`trap_frag_*` 这类名字会被误判成手雷。

### 2.2 第二层：顺序有意

```cpp
smoke                                   → Smoke
flash | concussion                      → Flash
frag | semtex | white_phos | grenade    → Grenade
```

注释直接说明顺序的理由：

> **顺序有意：先判更具体的烟/闪，最后才是 grenade 兜底，避免 `flash_grenade_mp` / `smoke_grenade_mp` 被兜底吞掉。**

这是"更长的模式意味着更具体的语义"的一个实例：`flash_grenade_mp` 同时含 `flash` 与 `grenade`，先判 `flash` 才对。

### 2.3 第三层：返回 nullopt 而非默认

未命中任何规则返回 `nullopt`。调用方（`registerMultiplayerOffhandWeapons`）对 nullopt 的处理是**不登记**，于是外层门不进、行为与改动前一致——这是之前报告里那个"表非空而求值器缺失导致每枚投掷物第一帧退役"的防线的另一半。

## 三、附件合并：去重键是名字，但**槽位集合仍然必需**

### 3.1 两个容器各司其职

```cpp
std::vector<std::string> seenDefaultNames;   // 名字去重
std::vector<NamedWeaponAttachment> defaultAttachments;

std::array<bool, WeaponAttachmentSlotCount> equippedSlots{};  // 槽位
std::vector<std::string> seenEquippedNames;
std::vector<NamedWeaponAttachment> equippedAttachments;
```

关键注释：

> **仍然按槽位跟踪**，因为抑制武器自己在该槽的默认值的是**这个集合**，不是名字列表。

即：

- **名字去重**决定"这一条要不要收"；
- **槽位集合**决定"武器的默认值要不要被压掉"。

两者不能互相替代。这正是修 bug 时最容易搞反的地方——把槽位集合删掉会让 `mag` 的默认值重新出现；把名字去重删掉会重复发同一条。

### 3.2 那次活体报告

> 这条规则（每槽一个）正是活体报告的内容：`mag_extclip*`（扩容弹夹）和 `mag_fmj*`（金属披甲弹）**都解析到 slot 11**（`mag`，`EngineBindings.cpp:3536-3538` 的 `SlotNames`），所以**后出现的那条被丢掉**——FMJ 从未进入武器串，玩家带着只有扩容弹夹的枪进图。**零售把多个同槽附件放进同一个串里**：`m4a1techsd_mp` 带 `EQUIPPED=3` 时是
>
> ```text
> mag_extclipm4a1techsd sto_stalkerm4a1techsd mag_fmjm4a1techsd
> ```
>
> 而客户端两条都认。

### 3.3 那句最重要的纠正

> **强制每槽一个从来不是那道保护。** 保护是"一个坏的附件只损失一个附件，绝不损失武器"——那才是调用方当成致命的 `std::nullopt`。而**完全重复（同名两次）仍然丢弃并计数**。

### 3.4 校验

```cpp
attachment.slot > 0 &&
attachment.slot < WeaponAttachmentSlotCount &&
!attachment.name.empty()
```

slot 0 被拒（与各处的"slot 0 不可达"一致），越界被拒，空名被拒——任一出现即**整个合并返回 nullopt**（即调用方会丢整个职业）。

这与 3.3 的"保护是只损失附件"看起来有张力，但注意区别：

- **重复名** → 丢弃并计数（不致命）；
- **非法槽位/空名** → 致命。

前者是数据的正常冗余，后者是数据损坏。

## 四、关键结论

1. **模式匹配的顺序就是语义**：先排除再兜底，先具体后一般。`flash_grenade_mp` 同时命中两个关键词，顺序决定结果。
2. **两个容器两种职责不能合并**：名字去重与槽位抑制是两件事。
3. **"去重键选错会损失整件东西"的修复要保住原有保护**——保护是"只损失附件不损失武器"，而不是"每槽一个"。
4. **重复 vs 非法要分级**：前者计数丢弃，后者致命。

## 五、未闭合点

- 投掷物分类按**本机武器内部名**子串匹配，新武器命名若不符约定会落到 nullopt（静默不生效而非报错）。
- `sticky`、`sensor` 等其它投掷物形态未在分类表里出现。
