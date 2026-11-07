# 241 · 160 字节 loadout 记录的缓存选择、四武器 = 两个经典、`missing_playerstate` 的三个死假设

## 一、范围

本报告学习 `EngineBindings.cpp` 9242–9505 行。

## 二、`LoadoutRecordWords` 的**全量清零**

```cpp
std::array<unsigned short, LoadoutRecordWords> record{};
```

```text
ZEROED, and the whole 160 bytes of it. sub_7C6480 qmemcpy's exactly this much
around the record, and a field the callee does not write must read as "nothing"
rather than as whatever was on the stack.
```

**"160 字节"** ⇒ `LoadoutRecordWords = 80`（80 × 2 = 160）✓

**理由**：`sub_7C6480` 会 `qmemcpy` 这整块，而**被调用方没写的字段必须读作"空"而不是栈上的残留**。

## 三、**先读 owner 的 cache key，再选槽**

```cpp
std::uint32_t ownerKeys[2]{};
bool haveOwnerKeys = false;
for (const auto rva : {LoadoutOwnerPrimaryRva, LoadoutOwnerFallbackRva})
{
    if (!readableSpan(module_ + rva, sizeof(uint32))) continue;
    const auto owner = *(const uint32*)(module_ + rva);
    if (!owner) continue;
    const auto *at = (const uint8*)(uintptr_t)owner + LoadoutOwnerKeyOffset;
    if (!readableSpan(at, sizeof(ownerKeys))) continue;
    ownerKeys[0] = ...; ownerKeys[1] = ...;
    haveOwnerKeys = true;
    break;
}
```

### 3.1 三个层次的容错

```text
主 RVA 可读且非零           ← 先用
不可读 / 为零 ⇒ 回退 RVA     ← 备用
两个都不行 ⇒ haveOwnerKeys = false
```

**"WHOSE RECORD ARE WE AFTER. Read the owner's cache keys first; with them the slot is chosen rather than guessed."**

**"有了 key，槽是【被选中】的而不是【被猜】的"** —— 这是本段的核心意图。

### 3.2 `LoadoutOwnerKeyOffset` 是一个**偏移**

**`owner + LoadoutOwnerKeyOffset`** —— 所以 owner 是一个对象，key 在它里面的某个位置。

**而 `ownerKeys` 是两个 `uint32`** —— 8 字节。

## 四、缓存槽的遍历

```cpp
std::size_t populated = 0;
for (slot = 0; slot < LoadoutRecordCacheSlots; ++slot)
{
    const auto at = module_ + LoadoutRecordCacheRva +
        slot * LoadoutRecordCacheStride + LoadoutRecordCacheOffset;
    if (!readableSpan(at, LoadoutRecordWords * sizeof(unsigned short))) continue;
    const auto *words = (const unsigned short *)at;

    if (haveOwnerKeys)
    {
        const auto *keys = (const uint32*)at;
        if (keys[0] != ownerKeys[0] || keys[1] != ownerKeys[1]) continue;
    }

    const auto primary   = words[LoadoutRecordWeaponWord];
    const auto secondary = words[LoadoutRecordWeaponWord + LoadoutRecordWeaponStride];
    if (!primary || !secondary) continue;

    if (!populated) std::copy_n(words, LoadoutRecordWords, record.begin());
    ++populated;
}
```

### 4.1 四次筛选

```text
1. 这一槽的 160 字节可读
2. （有 owner key 时）前两个 dword 与 owner 匹配
3. 主武器字 与 副武器字 都非零
4. 只有【第一个】通过的槽被复制出来
```

### 4.2 **`keys` 与 `words` 是同一块内存**

```cpp
const auto *words = (const unsigned short *)at;
const auto *keys  = (const uint32*)at;
```

**同一个指针两种视图** —— 所以 **`keys[0]` = `words[0..1]`、`keys[1]` = `words[2..3]`**。

**这就是"记录的前两个 dword 是 cache key"**（注释说的）—— 所以：
```text
words[0..3]    = cache key（8 字节）
words[4..]     = 实际载荷
```

**而 `LoadoutRecordWeaponWord` 必然 >= 4**。

### 4.3 主/副武器是**隔 `LoadoutRecordWeaponStride` 的两个字**

```cpp
words[LoadoutRecordWeaponWord]
words[LoadoutRecordWeaponWord + LoadoutRecordWeaponStride]
```

**不是连续的两个** —— 中间隔着 stride。

**这与 §241 后续的"四个 7 字武器组"是同一布局** —— 每组 7 字（1 武器 + 6 附件）。

**所以 `LoadoutRecordWeaponStride = 7`** ✓（见第五节）

## 五、`populated > 1` 的歧义日志

```cpp
if (populated > 1)
{
    static std::size_t LastPopulated;
    if (populated != LastPopulated)
    {
        LastPopulated = populated;
        OlMod::RuntimeLog::write(..., "client loadout cache has " +
            std::to_string(populated) + " populated slots -- taking the first");
    }
}
```

### 5.1 那句诊断理由

```text
AND SAY IF THE CHOICE WAS AMBIGUOUS. One populated slot is the local player's
loadout; several means this is picking one of them and the keys would have to
disambiguate. Silence here would make a wrong class look like a decode bug.
```

**"一个填充槽 = 本地玩家的 loadout；多个意味着这是在其中挑一个，而 key 需要来消歧。这里的沉默会让一个错误的职业看起来像一个解码 bug。"**

**这是"沉默读起来像健康"的第 N 次**（§225/§234/§235/§239）—— 但这次是**主动避免**。

### 5.2 去重是"值变了才打"

```cpp
if (populated != LastPopulated)
```

**不是"打一次"，是"值变化时打"** —— 所以如果从 3 变成 1 再变回 3，会打三次。

## 六、`!populated` 时的原生回退

```cpp
// Only rebuild if the cache had nothing. This is the native call the probe gate
// exists to worry about, so it is the fallback and not the first move.
if (!populated)
    static_cast<void>(loadoutRecordBuild_(record.data()));
```

**"只在缓存为空时重建。这是探针门控存在的理由所说的那次原生调用，所以它是【回退】而不是【第一步】。"**

**顺序**：

```text
1. 先读缓存（零成本、零风险）
2. 缓存空 ⇒ 才调原生 build
```

**这是 §239 里"`OLMOD_PROBE_PROFILE_SLOTS` 门控的正是 `sub_50FF30`"的接续** —— 现在连 `loadoutRecordBuild_` 都降级为回退。

## 七、**四武器 = 两个经典**（本组最重要的一段）

### 7.1 语义

```text
FOUR WEAPONS IS TWO CLASSES, NOT ONE. sub_7C5A50 writes four 7-word weapon
groups, and WeaponsPerClass is 2 -- so the record carries classes 0 and 1 back
to back.
```

**`sub_7C5A50` 写四个 7 字的武器组**，而 `WeaponsPerClass = 2` ⇒ **4 / 2 = 2 个 class**。

### 7.2 那个错误的后果

```text
Reading only the first two threw half of it away and produced a one-class
request, and EVERY SessionStart that has ever been accepted on this build
logged classMask=3. The one-class ones queue and never commit.
```

**"只读前两个扔掉了一半，产出一个单 class 请求，而在这个 build 上曾经被接受的【每一次】 SessionStart 都记录 `classMask=3`。单 class 的那些排队而永不提交。"**

### 7.3 `classMask=3` 是一个**硬门槛**

**这解释了 §239 里"`classMask=3` 与 `classMask=31`"两个观测**：

```text
classMask=3    可以提交
classMask=1    排队、永不提交
```

**所以"两个 class"不是一个偏好，是一个必需条件。**

### 7.4 7 字组的布局（从代码推出）

```cpp
const auto at = LoadoutRecordWeaponWord + weaponIndex * LoadoutRecordWeaponStride;
const auto itemId = record[at];
for (index = 0; index < AttachmentCount(6); ++index)
    weapon.attachmentItemIds[index] = record[at + 1 + index];
```

```text
record[at + 0]        武器 id
record[at + 1..6]     六个附件
```

**共 7 字** ⇒ **`LoadoutRecordWeaponStride = 7`** ✓

**而 §240 里 `words[W]` 与 `words[W+7]` 是主/副武器** —— 完全吻合（主武器组 0、副武器组 1）。

### 7.5 `at + AttachmentCount >= record.size()` 的越界检查

```cpp
if (at + OlMod::DedicatedSession::AttachmentCount >= record.size())
{
    whole = false;
    break;
}
```

**`>=` 而不是 `>`** —— 因为要读的最后一个下标是 `at + 6`，所以需要 `at + 6 < size`，即 `at + 7 <= size - 1 + 1`……

**实际上 `at + 6 < size` ⇔ `at + 6 <= size - 1` ⇔ `at + AttachmentCount(6) <= size - 1` ⇔ `at + 6 >= size` 为越界。**

**而代码写 `at + 6 >= size` ⇒ 越界。这就是 `>=`** ✓ 正确。

## 八、**ALL OR NOTHING PER CLASS**

```cpp
// ALL OR NOTHING PER CLASS, because valid() enforces
// `present != (weapon.itemId != 0)`: a class whose bit is set must have every
// weapon filled, and a class whose bit is clear must have none.
```

### 8.1 `present != (itemId != 0)` 的含义

```text
present=true  且 itemId!=0    ⇒ 一致 ✓
present=false 且 itemId==0    ⇒ 一致 ✓
present=true  且 itemId==0    ⇒ 矛盾 ✗
present=false 且 itemId!=0    ⇒ 矛盾 ✗
```

**这是"位与载荷必须同真同假"** —— 一个**异或不变式**。

### 8.2 所以 `whole` 的定义

```cpp
bool whole = true;
for (slot = 0; slot < WeaponsPerClass(2); ++slot)
{
    const auto itemId = record[at];
    if (!itemId) { whole = false; break; }
    ...
}
stagedComplete[classIndex] = whole;
complete = complete || whole;
```

**两个武器**都要非零。

## 九、角色物品来自**记录本身**

```cpp
// THE CHARACTER ITEMS COME FROM THE RECORD TOO, and that is the point of this
// path: valid() needs characterItemIds.front(), and the only other source for it
// is sub_50FF30, whose call is exactly what OLMOD_PROBE_PROFILE_SLOTS gates off.
// Words 12..23 are the same twelve ids, already decoded by the client for itself.
for (index = 0; index < CharacterItemCount(12); ++index)
    request.characterItemIds[index] = record[LoadoutRecordCharacterWord + index];
```

### 9.1 三个信息

```text
1. 唯一其它来源是 sub_50FF30 —— 而它正是被门控掉的
2. 字 12..23 = 同样那十二个 id
3. 客户端【已经为它自己解过码了】
```

**所以 `LoadoutRecordCharacterWord = 12`** ✓

### 9.2 这是一个**规避门控**的设计

**"这条路径的要点就是"** —— 不用去调被门控的那个函数，直接从记录里拿已经解码的十二项。

**这与 §239 里 `CharacterItemCount`（12）不是 `CharacterProfileSlotCount`（9）的区分互相印证** —— 这里用的正是 12 宽的那个数组。

## 十、`currentCharacterGet_` 的安全声明

```cpp
// AND THE INDEX THE WAY THE ENGINE TAKES IT. sub_6B87C0 reads a cached dvar and
// clamps negatives to zero; it does not call sub_50FF30 and is not what the probe
// gate protects, so it is safe to use here where currentCharacterIndex() is not.
if (currentCharacterGet_)
{
    const auto raw = currentCharacterGet_();
    if (raw >= 0 && raw < CharacterItemCount(12))
        request.characterIndex = (uint32)raw;
}
```

### 10.1 两个函数的区别

```text
currentCharacterIndex()    ⇒ 不安全（可能走 sub_50FF30）
currentCharacterGet_       ⇒ 安全（sub_6B87C0，读缓存 dvar，负数夹到零）
```

**"它不是探针门控保护的那个"** —— 所以可以用。

### 10.2 上界是 `CharacterItemCount(12)` 而**不是角色数**

**这是一个可疑点**：把 `characterIndex` 上限设为 12（物品记录宽度），而角色数可能不同。

**§239 里那条"两个数组只是恰好都十二长"的混淆在这里又出现了一次** —— 只是方向相反（用 12 去限 index）。

## 十一、**MIRROR THE CAPTURED CLASS ACROSS EVERY SLOT**（本组第二重要）

### 11.1 那次失败的实测

```text
The record reports ONE class -- weapons 2 and 3 read zero -- but the player's UI
has five, and the spawn asks for whichever slot they have selected. Registering
only class 0 left `snapshot build rejected failure=missing_playerstate` and both
clients stuck on 等待玩家数据 with active=2 and snapshots=0, while a two-class
fixture on the same stack produced snapshots immediately.
```

**完整链条**：

```text
1. 记录只报一个 class（武器 2 与 3 读出来是零）
2. 而玩家 UI 有五个，spawn 要的是玩家选中的那个槽
3. 只注册 class 0 ⇒ `snapshot build rejected failure=missing_playerstate`
4. ⇒ 两个客户端卡在「等待玩家数据」，active=2 而 snapshots=0
5. 而同一个栈上的【两 class fixture】立刻产出快照
```

### 11.2 那句"镜像不是猜测"

```text
Mirroring is not a guess about which slot they will pick: it makes every slot
resolve to the weapons they are actually holding. When the record eventually
yields more than one real class, the loop below already prefers the real one.
```

**"镜像不是猜他们会选哪个槽：它让每一个槽都解析到他们实际持有的武器。"**

### 11.3 **而它没有修好 `missing_playerstate`**

```text
AND IT DID NOT FIX missing_playerstate. classMask=31 was accepted and the spawn
still had no playerstate, so the class COUNT was never the cause -- the third
hypothesis about this failure to die on contact with the log, after "classMask=1
is refused" and "four weapon groups are two classes".
```

### 11.4 三个死掉的假设

```text
假设 1  "classMask=1 被拒绝"          ⇒ 死（classMask=31 也被接受但无 playerstate）
假设 2  "四个武器组是两个 class"        ⇒ 死（同上）
假设 3  "class 数量是原因"              ⇒ 死（classMask=31 仍失败）
```

**"这是关于这个失败第三个一碰日志就死的假设"**

### 11.5 那段保留的理由

```text
Kept because every slot resolving to the player's real weapons is right on its
own terms, not because it fixed anything. The open question is why a playerstate
is not built for these weapon ids when the 3.3.3.3 fixture's ids spawn on the
same stack.
```

**"保留它是因为每个槽解析到玩家真实武器【在它自己的标准上是对的】，不是因为它修好了什么。"**

**而开放问题是一个对照实验**：

```text
我们的武器 id        ⇒ 【不】造 playerstate
3.3.3.3 fixture 的 id ⇒ 在同一个栈上【能】spawn
```

**这是一个干净的差分** —— 同一个栈、不同的 id、不同的结果。

### 11.6 镜像的两段循环

```cpp
const auto *source = stagedComplete[0] ? &staged[0] : nullptr;
for (classIndex = 0; classIndex < LoadoutRecordClasses; ++classIndex)
    if (stagedComplete[classIndex]) source = &staged[classIndex];
if (source)
    for (auto &target : request.classes) target = *source;      // ① 全部镜像
for (classIndex = 0; classIndex < LoadoutRecordClasses; ++classIndex)
    if (stagedComplete[classIndex]) request.classes[classIndex] = staged[classIndex];  // ② 真实覆盖
```

```text
① 把【最后一个】完整 class 抄到【所有】槽
② 再把真实的完整 class 放回它们自己的槽
```

**`source` 取的是"最后一个完整"** —— 而不是第一个。

**这是一个两遍写法** —— 第一遍全镜像，第二遍把真值盖回。

## 十二、`!complete` 时的**字节转储**

```cpp
// SHOW THE BYTES. "it did not work" is not a measurement, and this failing
// silently is what made the previous build look like it had not been deployed.
// Dumping the head of the record separates "sub_7C5BA0 wrote nothing" from
// "it wrote something and the offsets are wrong" -- two different bugs that
// are indistinguishable from a bare false.
static std::string LastRecordDump;
std::string dump = "client loadout record REJECTED, words 0..31:";
for (index = 0; index < 32 && index < record.size(); ++index)
    dump += " " + std::to_string(record[index]);
if (dump != LastRecordDump) { LastRecordDump = dump; write(dump); }
```

### 12.1 两个候选缺陷

```text
A. sub_7C5BA0 什么都没写
B. 它写了东西，而偏移是错的
```

**"两个不同的 bug，从一个裸的 false 无法区分"**

### 12.2 为什么失败静默让上一版"看起来没部署"

**"这个静默失败正是让上一版看起来像没有部署的原因"** —— 一个运维报告。

### 12.3 只转储 32 字（64 字节）

**160 字节里只转储前 64** —— 足够看到 key（字 0..3）、主武器（字 W）、角色物品（字 12..23 在前 32 内）。

## 十三、成功时的那条报告

```cpp
std::string report = "client loadout record:";
for (classIndex = 0; classIndex < request.classes.size(); ++classIndex)
{
    if (!request.classes[classIndex].weapons[0].itemId) continue;
    request.classMask |= (1u << classIndex);
    report += " class" + N + " " + weapons[0].itemId + "/" + weapons[1].itemId;
}
```

### 13.1 `classMask` 在这里**第二次**置位

**第一次在 `readLoadoutRecord` 的 `!complete` 检查之前？**

**不** —— **这里才是唯一的置位**。**§239 里的置位是 `readProfileWeaponRequest` 那条路径**，不是这条。

**所以两条路径各自置位** —— 结构相同但不是同一个函数。

### 13.2 条件 `weapons[0].itemId`

**只看主武器** —— 因为 `valid()` 保证同真同假（§8.1），所以主武器有 ⇒ 副武器也有。

## 十四、**名字不是 id**

```cpp
// NAME THE WEAPONS, not just their ids. `tmp_mp` only reached the log because
// that weapon happened to FAIL its default-attachment read; a weapon that
// resolves cleanly went unnamed, which is backwards -- the id alone cannot be
// checked against a fastfile and a name can.
```

**"`tmp_mp` 只因为那个武器恰好【失败】了默认附件读取才进到日志里；一个干净解析的武器反而没有名字，这是反的 —— 单独的 id 无法对着 fastfile 核对，而名字可以。"**

### 14.1 这解释了 §240 里为什么有名字

**§240 的转储有 `name=ak104ss_mp`** —— 因为那条日志**主动**查名字（`readItemInternalName`），不依赖失败。

### 14.2 `break` 的理由

```cpp
break;   // one class is enough; they are mirrors of each other
```

**"一个 class 就够；它们互为镜像"** —— 直接引用上面 §11 的镜像机制。

## 十五、关键结论

1. **160 字节记录，全量清零** —— 未写字段读作"空"。
2. **先读 owner key 再选槽** —— 槽是"被选的"不是"被猜的"。
3. **`keys` 与 `words` 是同一块内存的两种视图** —— 前 8 字节是 key。
4. **四个 7 字武器组 = 两个 class**，`WeaponsPerClass = 2`。
5. **`classMask=3` 是硬门槛**，单 class 的 SessionStart 排队永不提交。
6. **`present != (itemId != 0)` 是异或不变式** ⇒ ALL OR NOTHING PER CLASS。
7. **角色物品从记录的字 12..23 拿** —— 规避被门控的 `sub_50FF30`。
8. **镜像没有修 `missing_playerstate`** —— 三个假设全死，开放问题是一个干净的差分（同栈不同 id）。
9. **字节转储区分"没写"与"偏移错"** —— 两个从裸 false 无法区分的 bug。
10. **名字必须主动查，不能只在失败时才有** —— id 无法对着 fastfile 核对。

## 十六、未闭合点

- `request.characterIndex` 的上界用 `CharacterItemCount(12)` 而不是角色数。
- `missing_playerstate` 的根因未定（同栈不同 id 的差分未做）。
- `LoadoutRecordWeaponWord`、`LoadoutRecordCharacterWord` 的具体值未在本段给出（由 `weapons[0]` 与 `words[12..23]` 推得 `CharacterWord = 12`）。
