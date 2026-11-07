# 239 · 校验日志的六项对照、两个 `call_once`、文档读取的完整实现

## 一、范围

本报告学习 `EngineBindings.cpp` 8897–9096 行。

## 二、六项对照日志

```cpp
const auto compare = [](const char* name, uint32 got, uint32 measured) {
    return got == measured ? std::string()
        : " " + std::string(name) + "=" + std::to_string(got) +
          "(measured " + std::to_string(measured) + ")";
};
```

### 2.1 六项

```text
characterSlots      vs CharacterClassesBaseIndex + CharacterSlotsOrdinal  (605+5=610)
characterStride     vs CharacterClassIndexStride                          (14)
weaponClassBase     vs WeaponClassesBaseIndex                             (1607)
weaponClassStride   vs WeaponClassIndexStride                             (37)
primary             vs WeaponClassPrimaryBaseOrdinal                      (22)
secondary           vs WeaponClassSecondaryBaseOrdinal                    (29)
```

**注意 `characterSlots` 的"测量值"是 `605 + 5 = 610`** —— 因为 `characterSlotsBase` 是"`characterClasses[0].slots` 的索引"，而 605 是 `characterClasses` 的基址、5 是 `slots` 的序号。

### 2.2 两种结论

```cpp
line += disagreement.empty()
    ? " -- agrees with every measured ordinal"
    : " -- DISAGREES WITH THE MEASURED ORDINALS:" + disagreement;
```

**"与每一个测量过的序号一致"** vs **"与测量序号不一致"**

### 2.3 这正是 §188 里说的"交叉校验"

```text
resolveProfileLayout() 走 def 读它们，所以 def 变了它们就跟着动，
不需要任何人重新测量。`byName` 说明那次 walk 是否成功；
没成功时字段带着 OLfinal 1649370 的常量，而调用方已经记录过这件事。
```

**"调用方已经记录过"** —— 就是这个日志。

## 三、`CharacterItemCount` 的误用

```cpp
// BOUNDED BY characterClasses, NOT BY THE ITEM RECORD. CharacterItemCount is the
// width of the twelve-entry item record sub_619E90 fills, which is a DIFFERENT
// array that merely happens to be twelve long on this build too -- the note on
// CharacterProfileSlotCount says as much, and the same conflation is what read
// past the end of the nine-wide `slots`.
```

**"`CharacterItemCount` 是 `sub_619E90` 填的十二项物品记录的宽度，那是【另一个】数组，只是在这个 build 上恰好也是十二长"**

**"同样的混淆正是那个读过九宽 `slots` 末端的读取"**

**这解开了 §219 里"9 不是 12"的另一面** —— 两个数组都恰好是 12 长（或 9 vs 12），所以容易混。

## 四、两个 `call_once`

### 4.1 第一个：`OLMOD_UNLOCK_ALL`

```cpp
static std::once_flag checked;
std::call_once(checked, [this] {
    char* value = nullptr;
    size_t size = 0;
    if (_dupenv_s(&value, &size, "OLMOD_UNLOCK_ALL") != 0 || !value) return;
    const bool wanted = value[0] == '1';
    free(value);
    if (wanted) reportUnlockAllCoverage();
});
```

**为什么要放在这里**：

```cpp
// THE UNLOCK-ALL CHECK BELONGS HERE, NOT ON resolveWeaponItem.
//
// It was hung off the first weapon resolution, and that is a DEDICATED-side path:
// the dedicated got there first and the client never ran it at all, so the probe
// answered from a process with no player in it and the gate then made it answer
// nothing. This function is the client's own profile read ...
// so it runs in the process the patch is applied to, and late enough that the
// inventory exists.
```

**三层**：

```text
1. 原位置在 resolveWeaponItem，那是 dedicated 侧路径
2. dedicated 先跑到，客户端根本没跑
3. ⇒ 探针在一个【没有玩家】的进程里回答，而门控让它什么都不答
```

**"这个函数是客户端自己的 profile 读取"** —— 所以放在这里。

### 4.2 第二个：`OLMOD_AUDIT_ITEM_NAMES` 的**独立线程**

```cpp
static std::once_flag swept;
std::call_once(swept, [this] {
    ...if (!wanted) return;
    // ON ITS OWN THREAD, AND THIS IS NOT A TIDINESS POINT. Run inline it
    // stalled the client BRIDGE thread for 60,249 item lookups, which is the
    // thread `--capture-from` talks to -- so the loadout capture never
    // answered, the host sat at `clients=1 active=0`, and the player sat on
    // the loading screen watching nothing happen. A diagnostic that stops the
    // game is worse than no diagnostic.
    std::thread([this] { auditItemNames(); }).detach();
});
```

### 4.3 五步因果链

```text
1. 内联跑 ⇒ 阻塞 client BRIDGE 线程 60,249 次 item 查找
2. 那是 `--capture-from` 说话的线程
3. ⇒ loadout capture 永不回答
4. ⇒ host 停在 `clients=1 active=0`
5. ⇒ 玩家停在加载屏看什么都不发生
```

**"一个让游戏停下的诊断比没有诊断更糟。"**

**这已经是本项目第三次记录同类问题**：

```text
§219  每帧 11 次 asset 查找 ⇒ 帧停顿 1.24s ⇒ 控制口超时 ⇒ 比赛按钮失效
§237  ...（同类的性能/阻塞问题）
§239  60,249 次内联查找 ⇒ bridge 线程阻塞 ⇒ 加载屏
```

### 4.4 `_dupenv_s` 而不是 `getenv`

**`_dupenv_s(&value, &size, name)`** —— 分配一个新缓冲区，需要 `free`。

**与 §201 的 `getenv_s`、§211 的 `GetEnvironmentVariableA` 是三种不同做法。**

**这个文件里三种都在用** —— 可以指出的一致性问题。

## 五、`readIndex`：五步边界检查

```cpp
const auto readIndex = [&](uint32 index) -> optional<uint32> {
    if (!readableSpan(offsetTable + index, sizeof(uint32))) return nullopt;
    const auto byteOffset = offsetTable[index];
    if (byteOffset + sizeof(uint32) > ProfileDocumentSize) return nullopt;
    if (!readableSpan(dataBuffer + byteOffset, sizeof(uint32))) return nullopt;
    const auto raw = *(const uint32*)(dataBuffer + byteOffset);
    return obfuscated ? std::rotl(raw ^ key, 8) : raw;
};
```

### 5.1 五步

```text
1. offsetTable[index] 可读（间接验证 index 不越界）
2. byteOffset + 4 <= ProfileDocumentSize
3. dataBuffer + byteOffset 可读 4 字节
4. 读 raw
5. 若混淆 ⇒ ROL32(raw ^ key, 8)
```

### 5.2 那句"未写字段解码成 ROL32(key, 8)"

```cpp
// The document is 0x8000 bytes; a byte offset at or past that is a corrupt
// table read, not a value. An unwritten field decodes to ROL32(key, 8),
// which is far above 0xFFFF and so is rejected as a weapon id anyway.
```

**"一个未写字段解码成 `ROL32(key, 8)`，那远高于 0xFFFF 所以无论如何会被当武器 id 拒绝"**

**`ProfileDocumentSize = 0x8000`**（§185）✓

### 5.3 `std::rotl(raw ^ key, 8)`

**与 §201 的 `decodeCharacterItemId` 的 `std::rotl(decodeKey ^ encodedLow ^ encodedHigh, 8)` 不同**：

```text
物品记录     ROL32(key ^ low ^ high, 8)      三个操作数
profile 字段 ROL32(raw ^ key, 8)             两个操作数
```

**两套混淆** —— 因为一个是 12 字节记录、一个是 4 字节字段。

## 六、`weaponId` 的三重判据

```cpp
const auto weaponId = [](const optional<uint32>& value) {
    return value && *value != 0 && *value <= 0xFFFFu;
};
```

**三项**：

```text
有值
非零
<= 0xFFFF
```

**`!= 0` 是因为"空槽"表示为 0**（§185 里 `sub_50FC20` 返回值减一，所以 0 = 空）。

## 七、角色物品的读取与重排

```cpp
array<uint32, CharacterItemCount(12)> characterItemIds{};
const auto characterSlotBase = layout.characterSlotsBase +
    characterIndex * layout.characterStride;

array<uint32, CharacterProfileSlotCount(9)> profileSlots{};
for (uint32 slot = 0; slot < layout.slotCount; ++slot)
{
    const auto item = readIndex(characterSlotBase + slot);
    if (item && *item <= 0xFFFFu)
        profileSlots[slot] = *item;
}

placeCharacterItemsByRecordEntry(profileSlots, characterItemIds);
```

### 7.1 两个数组宽度

```text
profileSlots      9  （CharacterProfileSlotCount）
characterItemIds 12  （CharacterItemCount）
```

**`placeCharacterItemsByRecordEntry` 做重排** —— 与 §188 里"密集按装备顺序打包 → 引擎按槽位寻址的十二项记录"一致。

### 7.2 那个"这个路径才在跑"的诊断

```cpp
// SAY WHICH CHARACTER THIS DOCUMENT READ, AND WHAT ITS SLOTS HOLD.
//
// THIS is the path that runs. The same line was first put on the profile-slot
// probe at ~10002 and printed NOTHING for a whole cycle, because that path
// needs a room cache that is empty until a room join -- the comment above says
// so outright and I instrumented the other one anyway.
```

**"同样的日志行最初放在 profile-slot 探针上，整整一轮什么都没打印，因为那条路径需要一个在加入房间之前为空的 room cache —— 上面的注释明说了这一点，而我还是给另一条装了仪器。"**

**这是一个自我批评** —— 而不是一个技术发现。

## 八、那条"两个不同的 bug 而没有日志能分开"

```cpp
// What it decides: the room roster carries real, DISTINCT character items per
// player (measured 2056 and 686 in one cycle, and 545 for everyone before
// that), while every model request this server makes still carries one item.
// So either this document read returns the same character whatever the player
// picked, or it returns the right one and the value is lost downstream. Those
// are different bugs and nothing currently logged separates them.
```

### 8.1 两个候选缺陷

```text
A. 这个文档读取【无论玩家选什么都返回同一个角色】
B. 它返回正确的，而那个值在【下游】丢了
```

### 8.2 三个实测数字

```text
2056 和 686     ← 一个周期里两个玩家的真实、不同的角色物品
545             ← 在那之前所有人都是 545
```

**"房间名册携带真实的、每个玩家不同的角色物品，而本服务器发出的每一个模型请求仍只携带一个物品。"**

### 8.3 为什么这条日志能分开

```cpp
line = "character document: index=" + characterIndex + " slots=" + 九个 + " record0=" + 第一个;
```

**`index` 与 `record0` 一起** —— 如果 `index` 变了而 `record0` 不变 ⇒ A；如果两者都变但下游没变 ⇒ B。

## 九、`slot >= layout.weaponClassCount` 的双界

```cpp
const auto slot = characterIndex * layout.classesPerCharacter + classIndex;
// The def says how many classes the array holds AND how many of them belong
// to one character. Reading past the first walks into whatever property
// follows weaponClasses; past the second, into the NEXT character's loadout,
// which is the more dangerous of the two because it yields a real weapon.
if (classIndex >= layout.classesPerCharacter || slot >= layout.weaponClassCount)
    continue;
```

### 9.1 两种越界

```text
classIndex >= classesPerCharacter  ⇒ 走进【下一个角色的 loadout】
slot >= weaponClassCount           ⇒ 走进 weaponClasses 之后的【任何属性】
```

**"后者更危险，因为它产出一个真实的武器"**

**这正是 §202 里"错误的槽位映射会产生一组貌似合理的、完全填充的、错误的模型名"的机制。**

### 9.2 `base` 的计算

```cpp
const auto base = layout.weaponClassBase + slot * layout.weaponClassStride;
```

**三次分别读 `primaryBase` 与 `secondaryBase`**：

```cpp
const auto primary = readIndex(base + layout.primaryBase);
const auto secondary = readIndex(base + layout.secondaryBase);
```

### 9.3 主武器必须有，副武器可空

```cpp
// A primary is required; an empty secondary is a legal class state and
// is retained so custom4 does not disappear from the class mask. The
// downstream resolver maps that empty slot to chicken_melee_mp.
if (!weaponId(primary)) continue;
classes[classIndex].weapons[0].itemId = *primary;
if (weaponId(secondary)) classes[classIndex].weapons[1].itemId = *secondary;
```

**"空副武器是合法职业状态，保留它以便 custom4 不从职业掩码里消失。下游解析器把那个空槽映射到 `chicken_melee_mp`。"**

**`chicken_melee_mp` 是空手的替代武器** —— 与 §`sv_client_spawn` 的 `dmz_empty_mp` 是两个不同的空手武器。

## 十、关键结论

1. **六项对照日志** 是 §188 里"按名 walk + 交叉校验"的落地。
2. **`CharacterItemCount` 与 `CharacterProfileSlotCount` 是两个不同数组**，只是宽度接近。
3. **`OLMOD_UNLOCK_ALL` 必须放在客户端进程的路径上** —— 否则探针在没有玩家的进程里跑。
4. **`auditItemNames` 必须独立线程** —— 60,249 次查找阻塞 bridge 线程 ⇒ 加载屏。
5. **"一个让游戏停下的诊断比没有诊断更糟"**。
6. **两种混淆**：物品记录三操作数、profile 字段两操作数。
7. **两个候选缺陷（读取错 vs 下游丢）需要 `index` 与 `record0` 一起才能分开**。
8. **`base + primaryBase` 与 `base + secondaryBase`** 的间隔是 7，而 `AttachmentCount` 是 6。

## 十一、未闭合点

- 三种环境变量读取方式（`getenv_s` / `_dupenv_s` / `GetEnvironmentVariableA`）并存。
- `EngineBindings.cpp` 9096 行之后未读取。
