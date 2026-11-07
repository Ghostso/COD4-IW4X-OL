# 240 · **附件在武器【之前】**、37 序号类块的完整转储、装备/技能/连杀

## 一、范围

本报告学习 `EngineBindings.cpp` 9096–9242 行。

## 二、**ATTACHMENTS PRECEDE THEIR WEAPON**（本组最重要的一段）

### 2.1 那句断言

```cpp
// ATTACHMENTS PRECEDE THEIR WEAPON. Section 187m, and this is measured.
```

### 2.2 一个完整 class 块的转储（**实测**）

```text
class=0 weapons=10609/10028
  16=for_gripvtlong2ak104ss   17=sco_targetfinderak104ss
  22=ak104ss_mp   <- PRIMARY   23=red_rmrtmp   29=tmp_mp <- SECONDARY
class=2 weapons=10015/10042
  16=red_rmrl86   17=mag_extclipl86
  22=l86_mp       <- PRIMARY   29=stinger_mp <- SECONDARY
```

### 2.3 从两个 class 推出的布局

```text
16..21   六个附件  ⇒ 主武器
22       主武器
23..28   六个附件  ⇒ 副武器
29       副武器
```

**"16 和 17 在两个 class 里都命名【主武器自己的部件】"**

**而 `23 = red_rmrtmp` 是 TMP 的部件，`29 = tmp_mp` 是副武器** —— 所以 **23..28 属于副武器，不属于主武器**。

### 2.4 那个错误的读取与三层后果

```text
This code read 23..28 and gave them to the PRIMARY -- the secondary's
attachments on the wrong gun.
```

**三层后果**：

```text
1. 只有 23 号那个曾经显示出来
2. 其它每一个都回答 "not supported by this weapon"
3. 翻译后的 id 造出一个客户端不共享索引的变体 ⇒ 拒绝每一颗子弹（§187l）
```

**"副武器的附件装到了错误的枪上"** —— 一句话概括。

### 2.5 那句自我更正

```cpp
// The "gap of exactly SEVEN" I built the first reading on was right about
// the width and wrong about the ORDER: six attachments then the weapon, not
// the weapon then six attachments.
```

**"我用第一次读法建立的那个『间隔恰好是七』在【宽度】上对、在【顺序】上错"**

**22 - 16 = 6**（六宽）而 **29 - 22 = 7**（间隔七）—— 两个数字都被观测到，但**哪个是宽度哪个是间隔必须先确定顺序**。

**这是本项目"两个吻合的数字被误配"的又一例** —— 与 §144 里"指针 100% 吻合也骗人"同族。

### 2.6 而现在两个序号**来自 def**

```cpp
readAttachments(layout.primaryAttach, 0);
readAttachments(layout.secondaryAttach, 1);
```

**`resolveProfileLayout` 直接问 `primaryAttach` 与 `secondaryAttach`（§238）** —— 间距与宽度**都不再推断**。

## 三、`readAttachments` 的三重跳过

```cpp
const auto value = readIndex(base + firstAttachmentOrdinal + entry);
if (!value || !*value || *value > 0xFFFFu)
    continue;
```

**三项**：有值、非零、`<= 0xFFFF`。

**注意是 `continue` 而不是失败** —— 附件缺失是合法的（枪可以不带镜）。

**与 §237 里"没有武器不是失败"的注释相反** —— 这里是**真的**跳过。

## 四、那条"分不清两个 bug"的逐条日志

### 4.1 具名证据

```cpp
// WHICH CLASS, WHICH WEAPON SLOT, WHICH ORDINAL, AND WHAT THE ITEM IS CALLED.
// Section 187e: item 25703 resolves to `red_rmrtmp`, a TMP-specific model,
// and the profile presents it for an MSR and an M4.
```

**§187e 的实测**：物品 **25703 → `red_rmrtmp`（TMP 专用模型）**，而 profile 把它呈现给 **MSR 和 M4**。

### 4.2 两个需要相反修法的候选

```text
A. 25703 是【通用】红点，其每武器模型必须按类型从武器自己的表里取
B. 这次读取把【一个 class 的附件】错配到了另一个 class 的武器上
```

**"两者需要相反的修法，而差别在这里可见"**

### 4.3 判据

```text
同一个 id 只在【一个】classIndex 下出现 ⇒ 读取对、id 是通用的
同一个 id 在【几个】classIndex 下出现 ⇒ 序号算术错
```

**这是"一个日志字段分开两个假设"的干净例子** —— 与 §239 里 `index` + `record0` 同构。

### 4.4 去重方式

```cpp
static std::mutex ordinalMutex;
static std::set<std::string> ordinalReported;
if (ordinalReported.insert(line).second)
    OlMod::RuntimeLog::write(...);
```

**对**整行文本**去重**（不是对 id 去重）—— 所以同一 id 出现在不同 class 下**都会打印**。

**这正是上面判据需要的** —— 如果按 id 去重，第二个 class 的出现就被吃掉了。

## 五、那两次**曾经上线过的错误读法**

### 5.1 第一次：武器之后

```text
class=0 weaponSlot=1 ordinal=32 item=60006 name=emp_grenade_mp
class=1 weaponSlot=1 ordinal=32 item=60005 name=smoke_grenade_mp
class=2 weaponSlot=1 ordinal=34 item=60186 name=fragshort_grenade_mp
```

**三个 30+ 的序号读出来全是投掷物** —— 因为那是**致命/战术装备槽**。

**而后果是**：`readAttachmentModelSlot` 每一个都失败，报 **"has no model slot"**。

### 5.2 第二次：`weaponOrdinal - AttachmentCount`

```cpp
// Section 187m then put them BEFORE the weapon
// (`weaponOrdinal - AttachmentCount`), which lands on 16 and 23 and is right
// -- but only because six happens to be both the array's width and the
// distance to it.
```

**"落在 16 和 23 上，而且是对的 —— 但只是因为 6 恰好既是数组宽度又是到它的距离。"**

### 5.3 而附带的注释还有一个**未核对**的断言

```text
The comment that came with it also asserted this def has "NO secondaryAttach";
it has one, at ordinal 23, six wide, on BOTH builds. That claim was never
checked against the def.
```

**"随它来的注释还断言这个 def 没有 `secondaryAttach`；它有一个，在序号 23，宽六，【两个 build 都有】。那个断言从未对着 def 核对过。"**

**这是"注释断言未核对"的第二例** —— 与 §237 里"注释说没有武器不是失败而代码仍返回 false"同族。

## 六、装备槽的两个字段、两种语义

```cpp
for (equipmentSlot = 0; equipmentSlot < 2; ++equipmentSlot)
{
    if (layout.equipmentBase[equipmentSlot])
    {
        const auto value = readIndex(base + *layout.equipmentBase[equipmentSlot]);
        if (value && *value <= 0xFFFFu)
            equipment.itemIds[equipmentSlot] = *value;
    }
    if (layout.equipmentDoubleAmmoBase[equipmentSlot])
    {
        const auto index = base + *layout.equipmentDoubleAmmoBase[equipmentSlot];
        if (readableSpan(offsetTable + index, sizeof(std::uint32_t)))
        {
            const auto bit = offsetTable[index];
            if ((bit >> 3) < ProfileDocumentSize &&
                readableSpan(dataBuffer + (bit >> 3), 1) &&
                (dataBuffer[bit >> 3] & (1u << (bit & 7))))
                equipment.doubleAmmoMask |= 1u << equipmentSlot;
        }
    }
}
```

### 6.1 物品字段：`readIndex` 的完整解码

**`readIndex` 走 `offsetTable[index]` → `dataBuffer[byteOffset]` → `ROL32(raw ^ key, 8)`**（§239 的五步）。

### 6.2 布尔字段：**绕开 `readIndex`**，直接读位

```text
offsetTable[index] = bit position（不是字节偏移）
bit>>3             = 字节
bit & 7            = 位
dataBuffer[bit>>3] & (1u << (bit&7))
```

**这是 §238 里"`equipmentDoubleAmmoBase` 存的是【位偏移】"的落地证据。**

### 6.3 关键差异

```text
equipmentBase           → readIndex → 字节偏移 + ROL32 解码
equipmentDoubleAmmoBase → 手工位读 → 位偏移 + 无 ROL32
```

**布尔字段【不解码】** —— 因为一个位没什么可混淆的。

**而这正是为什么它不能走 `readIndex`**：`readIndex` 会做 `byteOffset + 4 > ProfileDocumentSize` 的检查，而布尔这里只有 1 字节、且偏移语义完全不同。

### 6.4 两个上界的顺序

```cpp
if ((bit >> 3) < ProfileDocumentSize && readableSpan(...) && (dataBuffer[...] & ...))
```

**先检查 `bit>>3 < 0x8000`，再检查可读** —— 顺序正确（先算再解引用）。

## 七、技能的读取

```cpp
for (entry = 0; entry < layout.perksCount; ++entry)
{
    const auto value = readIndex(base + layout.perksBase + entry * layout.perksStride);
    if (value && *value <= 0xFFFFu)
        classes[classIndex].perkItemIds[entry] = *value;
}
```

**三个量**：`perksBase`、`perksCount`、`perksStride`。

**`perksBase` 是相对 `weaponClasses` 基址的**（§238）✓

**而这里用 `base` 而不是 `weapons->index`** —— `base = weaponClassBase + slot * weaponClassStride`，所以 `base + perksBase` 是**这个具体 class 元素内**的位置。

**这只有在 `perksBase < weaponClassStride` 时成立** —— 而 §238 的四重校验保证了这一点（`base + count*stride <= weaponClassStride`）。

## 八、`classMask` 的置位

```cpp
classMask |= static_cast<std::uint8_t>(1u << classIndex);
```

**在循环末尾无条件置位** —— 因为前面已经 `if (!weaponId(primary)) continue;`，所以到这里必有主武器（§239）。

**注意 `1u << classIndex`** 而 `classIndex < classesPerCharacter(5)` —— 所以最大 `0x10`，在 `uint8` 内。

**但 `classMask` 是 `uint8_t`** —— 如果 `classesPerCharacter > 8` 就会溢出。

**§239/§237 的实测 `classMask=3` 与 `classMask=31`（= 五个 class）** ✓

## 九、`if (!classMask) return false` 的位置

```cpp
if (!classMask)
    return false;
request.characterIndex = characterIndex;
request.characterItemIds = characterItemIds;
...
```

**在填 `request` 之前** —— 所以失败时 `request` 不变（调用方持有旧值）。

**这是一个"不写半成品"的守卫。**

## 十、连杀奖励：**三槽固定，读 `weaponClasses[0]`**

```cpp
// Native 0x7C633D reads three slots from weaponClasses[0], regardless
// of the selected character/class. Keep raw ID+1 values on this bridge.
if (layout.rewardsBase)
    for (slot = 0; slot < request.rewardItemIds.size(); ++slot)
    {
        const auto value = readIndex(*layout.rewardsBase +
            (uint32)slot * layout.rewardsStride);
        if (value && *value <= 0xFFFFu)
            request.rewardItemIds[slot] = *value;
    }
```

### 10.1 关键：**不乘 class 偏移**

```cpp
readIndex(*layout.rewardsBase + slot * layout.rewardsStride)
```

**没有 `base`！** —— 而装备/技能/武器都用 `base`。

**因为**：

```text
Native 0x7C633D reads three slots from weaponClasses[0], regardless
of the selected character/class.
```

**"原生的 `0x7C633D` 从 `weaponClasses[0]` 读三个槽，【不管】选中的是哪个角色/职业。"**

**这与 §238 里"`rewardsBase` 存的是绝对 index"一致** ✓ —— 两个证据独立吻合。

### 10.2 "Keep raw ID+1 values"

**"在这个 bridge 上保留原始的 ID+1 值"** —— 所以连杀槽里存的是**编码过的**，而后面的消费者要减一。

**这是第三套编码约定**（与 `sub_50FC20` 返回值减一、`readIndex` 的 ROL32 不同）。

## 十一、`request.rewardItemIds = {}` 的位置

```cpp
request.classes = classes;
request.classMask = classMask;
request.rewardItemIds = {};        // ← 先清零
if (layout.rewardsBase)            // ← 再填
```

**清零在填之前** —— 否则 `layout.rewardsBase == 0` 时残留旧值。

## 十二、关键结论

1. **附件在武器【之前】** —— 六附件 + 武器，不是武器 + 六附件。
2. **"间隔恰好是七"在宽度上对、顺序上错** —— **两个吻合的数字被误配**。
3. **错误顺序的三层后果**：只显示一个、其余报"不支持"、变体索引客户端不共享 ⇒ 拒绝子弹。
4. **附件去重必须按【整行】而不是按 id** —— 否则第二个 class 的出现会被吃掉，判据失效。
5. **装备的布尔字段绕开 `readIndex` 直接读位** —— 位偏移 vs 字节偏移。
6. **连杀读 `weaponClasses[0]` 不乘 class 偏移** —— 与 §238 的"绝对 index"独立吻合。
7. **`classMask` 是 `uint8_t`，最多 8 个 class**。
8. **`if (!classMask) return false` 在填 `request` 之前** —— 不写半成品。

## 十三、未闭合点

- `classMask` 的 `uint8_t` 上限与 `classesPerCharacter` 的潜在冲突。
- `rewardItemIds` 的 "ID+1" 编码契约未在结构定义处说明。
- `EngineBindings.cpp` 9242 行之后未读取（本批已续读到 9505）。
