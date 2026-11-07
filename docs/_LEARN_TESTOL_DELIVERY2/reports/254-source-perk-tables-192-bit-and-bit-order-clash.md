# 254 · 技能的两张表与 192 位掩码、`profile +1` 编码的第五处、`429E10` 的三个断言

## 一、范围

本报告学习 `EngineBindings.cpp` 14850–15050 行。

## 二、技能的两张表（本组最重要的一段）

### 2.1 `mp/coPerkStatsTable.csv` 的两列语义

```cpp
// CODREF(1649370): sub_413980 looks up column 1 (canonical name),
// reads column 0 (decimal bit index), and rejects indices >= 96.
const auto *table = readStringTable(..., "mp/coPerkStatsTable.csv", 2);
...
const auto rowName = readStringTableCell(row[1]);      // ← 列 1 名字
if (!rowName || *rowName != *name) continue;
const auto indexText = readStringTableCell(row[0]);    // ← 列 0 位索引
...
if (parsed.ec != std::errc{} || parsed.ptr != end || index >= 96) break;
return index;
```

```text
列 0   十进制位索引（< 96）
列 1   规范名
```

**而 `readStringTable(..., 2)` 的 `2` 是期望列数。**

### 2.2 `mp/coAbilityModifiersTable.csv` 的**七列用法**

```cpp
const auto *abilityTable = readStringTable(..., "mp/coAbilityModifiersTable.csv", 7);
if (!abilityTable || table->columnCount < 27)
    return nullopt;                                    // ← 注意查的是【table】不是 abilityTable
```

### 2.3 **这里有一处可能的笔误**

```cpp
if (!abilityTable || table->columnCount < 27)
```

**`table` 是 `coPerkStatsTable`（期望 2 列），而 `27` 是 `coAbilityModifiersTable` 的列要求。**

**所以：如果 `coPerkStatsTable` 真的只有 2 列（`readStringTable(..., 2)` 成功意味着至少 2 列），那 `table->columnCount < 27` 恒为真 ⇒ 永远 `return nullopt`。**

**⇒ 除非 `coPerkStatsTable` 实际有 >= 27 列。**

**这是一个高度可疑的判据** —— 两个表的列数被混用了。

**如果 `coPerkStatsTable` 真有 27+ 列，那这个检查是正确的（但语义仍混乱）；如果只有 2 列，整个技能解析永远失败。**

**这解释了 `PERK_AUDIT ... unresolved` 可能出现。**

## 三、**第一遍：累加增量**

```cpp
std::unordered_map<std::string, float> additions;
for (r = 0; r < table->rowCount; ++r)
{
    const auto *row = table->values + r * table->columnCount;
    const auto index = number(row[0], -1);
    if (!index || *index < 0 || *index >= 96 || std::floor(*index) != *index) continue;
    const auto i = (uint32)*index;
    if (!(result.bits[i >> 5] & (1u << (i & 31)))) continue;      // ← 【只处理已置位的技能】
    for (c = 15; c < 27; c += 2)                                   // ← 【列 15..26，步长 2】
    {
        const auto modifier = readStringTableCell(row[c]);
        if (!modifier || modifier->empty()) continue;
        const auto amount = number(row[c + 1], 0);
        if (!amount) return nullopt;
        additions[*modifier] += *amount;
    }
}
```

### 3.1 三项

```text
1. 只看 result.bits 里已置位的技能（即玩家已经解的）
2. 每行的【列 15..26 步长 2】是 (修饰符名, 数值) 对
3. 同名修饰符【累加】
```

### 3.2 **六对**

```text
15/16, 17/18, 19/20, 21/22, 23/24, 25/26
```

**六对 = 六个修饰符槽** ✓

### 3.3 `std::floor(*index) != *index` 是**整数检查**

**`number(row[0], -1)` 返回 `float`** ⇒ 需要验证它是整数。

**这是本文件里第三次出现"float 解析 + 整数检查"**（§254 后面还有）。

## 四、**第二遍：从能力表解析**（本组第二重要）

```cpp
for (r = 0; r < abilityTable->rowCount; ++r)
{
    const auto *row = abilityTable->values + r * abilityTable->columnCount;
    const auto name = readStringTableCell(row[1]);        // ← 列 1 名字
    if (!name || !additions.contains(*name)) continue;    // ← 【只处理第一遍发现的】
    const auto id         = number(row[0], -1);           // 列 0  id
    const auto valueIndex = number(row[2], -1);           // 列 2  值索引
    const auto initial    = number(row[3], 0);            // 列 3  初值
    const auto minimum    = number(row[4], -FLT_MAX);     // 列 4  下限
    const auto maximum    = number(row[5], +FLT_MAX);     // 列 5  上限
    if (!id || *id < 0 || *id >= 192 || std::floor(*id) != *id ||
        !valueIndex || !initial || !minimum || !maximum || *minimum > *maximum)
        return nullopt;
    const auto modifierId = (uint32)*id;
    result.abilities.mask[modifierId >> 5] |= 0x80000000u >> (modifierId & 31);      // ← 【MSB first】
    const auto value = std::clamp(*initial + additions.at(*name), *minimum, *maximum);
    result.abilities.resolvedValues[modifierId] = value;
    if (*valueIndex >= 0)
    {
        if (*valueIndex >= 36 || std::floor(*valueIndex) != *valueIndex) return nullopt;
        result.abilities.values[(size_t)*valueIndex] = value;
    }
    if (*name == "modMoveSpeedScale")   result.abilities.moveSpeedScale = value;
    if (*name == "modFallDamageScale")  result.abilities.fallDamageScale = value;
    if (*name == "modKillstreakShift")  result.abilities.killstreakShift = value;
    additions.erase(*name);
}
if (!additions.empty()) return nullopt;
```

### 4.1 **六列**

```text
列 0   id           (0..191)
列 1   名字
列 2   valueIndex   (0..35，-1 表示不存)
列 3   initial
列 4   minimum
列 5   maximum
```

### 4.2 **三个上界**

```text
id          < 192        （6 个 uint32 = 192 位）
valueIndex  < 36
perk index  < 96         （第一遍）
```

**三个不同的宽度** —— 而 §254 的内存里记着"192 abilities, MSB-first" ✓

### 4.3 **`mask[modifierId >> 5] |= 0x80000000u >> (modifierId & 31)`**

**注意与第一遍的 `result.bits` 不同：**

```cpp
// 第一遍读 bits（输入）
result.bits[i >> 5] & (1u << (i & 31))              // ← LSB first
// 第二遍写 mask（输出）
result.abilities.mask[modifierId >> 5] |= 0x80000000u >> (modifierId & 31)   // ← MSB first
```

**两个比特序相反！**

**而记忆里"perks (192 abilities, MSB-first)"指的是 `mask`** ✓

**所以 `bits` 是 LSB-first 而 `mask` 是 MSB-first** —— 两个不同的结构用不同的顺序。

**这解释了为什么它们是两个字段而不是一个。**

### 4.4 那三个"便利字段"

```cpp
if (*name == "modMoveSpeedScale")   moveSpeedScale = value;
if (*name == "modFallDamageScale")  fallDamageScale = value;
if (*name == "modKillstreakShift")  killstreakShift = value;
```

**三个名字被单独拎出** —— 因为它们有专门的消费者。

**而这些名字**仍然**会被写进 `values[valueIndex]`** —— 所以是冗余存储 ✓

### 4.5 `additions.erase(*name)` 与 `additions.empty()` 的**闭合检查**

```cpp
additions.erase(*name);
...
if (!additions.empty()) return nullopt;
```

### 4.6 **这是一个"全部消费"的判据**

**"第一遍累加的每一个修饰符名字，都必须在第二遍里被找到并处理。"**

**⇒ 如果某个修饰符只在 `coPerkStatsTable` 里有而在 `coAbilityModifiersTable` 里没有，整个技能解析失败。**

**这与 §249 里 `closedAnimations.size() == animations.size()` 是同一族**（"恰好全部"）。

### 4.7 四个"两个表必须一致"的检查汇总

```text
§249  closedAnimations ⊇ animations          （每个动画都被用）
§254  additions ⊆ abilityTable 行             （每个增量都有定义）
```

**两个都是"没有孤儿"** —— 方向相反（一个"输入全覆盖输出"，一个"输出全覆盖输入"）。

## 五、三个实测值

```cpp
// The live asset describes additive deltas, defaults, and clamps.
// Retail DM corroborates Fast Hands' 1.5 switch / 1.6 offhand scales
// and Marathon's -1 sprint sentinel (default 4, delta -7, minimum -1).
// The native consumers divide durations by these speed scales.
```

### 5.1 两套实测

```text
Fast Hands      switch scale 1.5
                offhand scale 1.6
Marathon        sprint sentinel -1
                default 4，delta -7，minimum -1
```

### 5.2 Marathon 的算术

```text
4 + (-7) = -3
clamp(-3, -1, max) = -1
```

**⇒ 哨兵 -1 由 clamp 得到** ✓

### 5.3 而"原生消费者除以这些速度倍率"

**"The native consumers divide durations by these speed scales."**

**⇒ 1.5 意味着"耗时除以 1.5" = "快 50%"** ✓ 合理

## 六、`resolveSessionEquipment` 的**五个检查**（本组第三重要）

```cpp
for (slot = 0; slot < result.weapons.size(); ++slot)
{
    const auto raw = equipment.itemIds[slot];
    if (raw <= 1) continue;                                  // ← 【<= 1 跳过】
    const auto name = readItemInternalName(raw - 1);         // ← 【-1】
    if (!name) return nullopt;
    const auto index = weaponLookup_(name->c_str());
    if (!index || index > MaximumWeaponAssetIndex) return nullopt;
    ...
    const auto kind     = read(1436);                        // offhandClass
    const auto ammo     = read(WeaponAmmoIndexOffset);
    const auto clip     = read(WeaponClipIndexOffset);
    const auto capacity = read(WeaponClipSizeOffset);
    if (read(WeaponTypeOffset) != 1 || kind <= 0 || kind > 255 ||
        ammo <= 0 || ammo > 0x7FF || clip <= 0 || clip > 0x7FE ||
        capacity <= 0 || capacity > 0x1FF) return nullopt;
    const auto count = 1u + ((equipment.doubleAmmoMask >> slot) & 1u);
    if (count > (uint32)capacity) return nullopt;
    result.weapons[slot] = { ... };
}
```

### 6.1 **`raw <= 1` 跳过**与 **`raw - 1`**

```text
raw == 0    ⇒ 空
raw == 1    ⇒ 空（保留）
raw >= 2    ⇒ 物品 id = raw - 1
```

**这是 `profile +1` 编码** —— 与 §251 里"`rewardItemIds` 保留原始的 ID+1 值"一致 ✓

### 6.2 那句 CODREF

```cpp
// CODREF(1649370): profile +1 encoding (50FD05), verified against
// the item catalog and all five live classes. Base offhand assets
// are already loaded; lookup does not allocate modular weapons.
```

**两个信息**：

```text
50FD05               编码的来源地址
lookup 不分配模块化武器   （所以是安全查询）
```

### 6.3 **`WeaponTypeOffset == 1`**

**type 1 = 投掷物/装备** —— 与 §240 里"`type=1` is a THROWABLE and `class=6`"一致 ✓

### 6.4 **`+1436` 是 `offhandClass`**

```cpp
const auto kind = read(1436);
// 429E10 asserts type1 and nonzero offhandClass(+1436).
```

**§243 里 `inv1436` 被打印过**：

```cpp
" inv1436=" + std::to_string(*(const int32*)(def + 1436))
```

**而现在知道它是 `offhandClass`** ✓ —— 这是一处交叉确认。

### 6.5 三个界**又是 2047/2046/511**

```text
ammo     <= 0x7FF (2047)
clip     <= 0x7FE (2046)
capacity <= 0x1FF (511)
```

**与 §240/§243 完全一致** —— 这已经是**第四次**出现这同一组界。

### 6.6 `count = 1 + ((doubleAmmoMask >> slot) & 1)`

**基础 1 发，加上 double-ammo 位的 1 发。**

**"Retail semtex spawn: clip1/reserve0"** —— 默认 1 发。

**而 `count > capacity` 被拒绝** ✓

### 6.7 **`SV_IsEquipmentValid` 是最后的门**

```cpp
return SV_IsEquipmentValid(result) ? std::optional{result} : std::nullopt;
```

**在头文件里做的整体校验** —— 与 §242 里 `SV_PlaceCharacterItemsByRecordEntry` 同一分层 ✓

## 七、`resolveFactorySpecialEquipment`：**四个白名单**

```cpp
if (name != "trap_fire_zm" && name != "trap_freeze_zm" && name != "trap_shock_zm" &&
    name != "trap_shrink_zm" && name != "zombie_cymbal_monkey") return nullopt;
```

### 7.1 五个名字

```text
trap_fire_zm            火焰陷阱（§144 的僵尸工厂）
trap_freeze_zm          冰冻陷阱
trap_shock_zm           电击陷阱
trap_shrink_zm          缩小陷阱
zombie_cymbal_monkey    猴子炸弹（"铙钹猴"）
```

**§144 学过的 `zm_factory` 陷阱** ✓

### 7.2 而 `spawnCount` 是 **`min(capacity, 3)`**

```cpp
static_cast<std::uint8_t>(std::min(capacity, 3))
```

**"Original Prototype freeze pickup adds three charges. Other counts follow bounded native capacity as provisional reward policy."**

```text
冰冻陷阱  3 发（原型的实测）
其它      min(capacity, 3)（临时策略）
```

**"provisional reward policy"** —— 明确标注为**临时** ✓

### 7.3 代码风格**明显不同**

**这个函数是**压缩风格**（`if(name!="...")return std::nullopt;` 无空格）** —— 与其他函数的风格不一致。

**说明它是后来加入的、可能来自不同作者或不同批次。**

## 八、`auditEquippedEquipment` 的**五个字段**

```cpp
line = "EQUIPMENT_AUDIT character=N class=M";
for (slot) {
    const auto raw = equipment.itemIds[slot];
    const auto name = raw > 1 ? readItemInternalName(raw - 1) : optional<string>{"none"};
    line += string(slot ? " tactical=" : " lethal=") + N + "/" + name;
}
line += " doubleAmmoMask=N";
const auto resolved = resolveSessionEquipment(request, c);
if (resolved)
    for (weapon) line += " grant=" + weaponAssetIndex + "/" + clipIndex + "/" + spawnCount;
else
    line += " grant=<unresolved>";
```

### 8.1 六项

```text
character / class
lethal=<raw>/<name>
tactical=<raw>/<name>
doubleAmmoMask
grant=<assetIndex>/<clipIndex>/<spawnCount>（可能多个）
或 grant=<unresolved>
```

### 8.2 **`slot ? " tactical=" : " lethal="`**

**slot 0 = lethal，slot 1 = tactical** ✓ 与 §238 的 `names{"lethal", "tactical"}` 一致

### 8.3 注意 `class=` 是 `c + 1`

**而 `classMask & (1u << c)` 用 `c`** —— 所以日记里是 1-based 而下标是 0-based。

**这是一个易错的偏移** —— 但与 §241 的 `report += " class" + classIndex` （0-based）**不一致**。

**两处日志的 class 编号不同基准。**

## 九、`auditEquippedPerks` 的**六个字段**

```cpp
line = "PERK_AUDIT character=N class=M";
line += " profile="; for (item : itemIds) line += N + ",";
line += " bits="; for (word : bits) line += N + ",";
line += " abilityMask="; for (word : abilities.mask) line += N + ",";
line += " values="; for (i < values.size()) if (values[i] != 0) line += i + ":" + N + ",";
line += " move=" + moveSpeedScale + " fall=" + fallDamageScale;
```

### 9.1 六个字段

```text
profile        输入 itemIds
bits           位集（3 个 word）
abilityMask    能力掩码（6 个 word）
values         非零的值
move / fall    两个便利字段
```

### 9.2 **没有 `killstreakShift`**

**而 §254 里 `abilities.killstreakShift` 是被设置的** —— 但审计不打印它。

**这是一处遗漏** —— 与 §249 的"日志漏了 animations"同族。

### 9.3 **`bits` 与 `abilityMask` 是两个不同的掩码**

**所以审计同时打印两者** ✓ —— 因为它们的比特序相反（§4.3），能对上才说明实现正确。

**这是一个有意的设计** —— 打印更多信息以支持交叉验证。

## 十、关键结论

1. **`coPerkStatsTable` 列 0 = 位索引（<96）、列 1 = 名**。
2. **`if (!abilityTable || table->columnCount < 27)` 疑似笔误** —— 查的是 `table` 而非 `abilityTable`。
3. **第一遍只处理已置位的技能**，列 `15..26` 步长 2 是六对修饰符。
4. **第二遍 `id < 192`、`valueIndex < 36`** —— 两个不同的宽度。
5. **`bits` 是 LSB-first 而 `mask` 是 MSB-first** —— 两个字段两种比特序。
6. **`additions.empty()` 是"没有孤儿"的闭合检查**，与 §249 的 `closedAnimations` 相反方向。
7. **Fast Hands 1.5/1.6、Marathon -7 到 -1** 三个实测值。
8. **`profile +1` 编码的第五处出现**（`raw <= 1` 跳过、`raw - 1` 查名）。
9. **`+1436` = `offhandClass`** —— 解决了 §243 的 `inv1436` 含义。
10. **2047/2046/511 第四次出现**。
11. **`trap_*_zm` 五个白名单 + `min(capacity, 3)`** 的临时策略。
12. **两处日志的 class 编号基准不同**（1-based vs 0-based）。
13. **`PERK_AUDIT` 漏了 `killstreakShift`**。

## 十一、未闭合点

- `table->columnCount < 27` 的笔误（可能是技能系统整体失效的原因之一）。
- `bits` 与 `mask` 比特序相反的依据（只从代码读出，未与参照核对）。
- `PERK_AUDIT` 缺 `killstreakShift`。
- `EngineBindings.cpp` 14950 行之后未读取（本批已续读到 15050）。
