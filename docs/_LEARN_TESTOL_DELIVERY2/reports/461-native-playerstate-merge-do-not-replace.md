# 461 · **"合并，不要替换"** —— `ps+0x10` 的 `0x1800` 掩码、一个被遗漏的常量（`0x3FF`/`0x7FF`）如何拒绝整个出生、以及 `static_assert` 钉在数组的**末端**

## 一、范围

本报告学习 `sv_native_playerstate_mp.cpp` 480–820 行（三个数组的读取与六个拒绝、`writeObjectives`/`readObjectives`、八个 `static_assert`、`SV_OverlayPlayerStateToNative` 的 `otherFlags` 合并）。

## 二、**"合并，不要替换"**（本组最重要的一段）

### 2.1 那段

```cpp
// MERGE, DO NOT REPLACE. ps+0x10 carries the ENGINE's flags word -- stance and
// toggle state among them -- captured back out through the GET accessor after
// every native stage. This server owns only the two bits
// BG_PlayerStateToEntityState tests to pick ET_PLAYER over ET_INVISIBLE.
// Assigning the whole word here is what threw the engine's state away every
// frame, and dest1yo's 3.3.3.3 server has none of this machinery at all -- ps+0x10
// is a plain dword there, which is exactly why stance works on it.
writeValue(
    destination, OtherFlagsOffset,
    (readValue<std::uint32_t>(destination, OtherFlagsOffset) &
        ~PlayerOtherFlagsServerOwnedMask) |
        (source.otherFlags & PlayerOtherFlagsServerOwnedMask));
```

### 2.2 二十四层

```text
1. **合并，不要替换**
2. ⇒ **`ps+0x10` 携带【引擎的 `flags` 字**（**姿态与开关状态在其中**）**
3. ⇒ **⇒ 它【通过 `GET` 访问器【在每个原生阶段之后【捕获回来**】】**
4. ⇒ **这个服务器【只拥有【两个位**】**
5. ⇒ **（`BG_PlayerStateToEntityState` 测它们以选 `ET_PLAYER` 而不是 `ET_INVISIBLE`）**
6. ⇒ **⚠ 【在这里赋整个字**正是【每帧【扔掉引擎的状态**】的东西**
7. ⇒ **而 dest1yo 的 3.3.3.3 服务器【完全没有这套机械**】**
8. ⇒ **⇒ 那里的 `ps+0x10` **是一个普通的 `dword`**】**
9. ⇒ **⇒ 而那【正是为什么姿态在它上面能工作**】**
10. ⇒ **⇒ 所以【`(own & ~mask) | (source & mask)`**】
```

### 2.3 ⭐⭐⭐ **"那里的 `ps+0x10` 是一个普通的 `dword`，而那正是为什么姿态在它上面能工作"**

**✅ 这是本报告里**最重要的一条"外部实现的简单性来自它的 build**。**

**✅ 与 §456 的"那个注释想避免的错误，在另一个方向上犯了"**——**完全同族** ✓

**⇒ 三层**：
```text
3.3.3.3 ⇒ **`ps+0x10` 是一个普通 `dword`** ⇒ **赋整个字【无害**】
本 build ⇒ **它是一个【混淆的 getter**】⇒ **赋整个字【扔掉引擎状态**】
⇒ **⇒ 所以【同一个代码【在两个 build 上一个对一个错**】
```

**✅ ⭐⭐⭐ **"同一个代码在两个 build 上一个对一个错"** —— 而**这正是 `AGENTS.md` 的"ol-mod 服务的是 3.3.3.3"那条纪律的又一个实例**。

**⇒ 三层**：
```text
`AGENTS.md`：**"ol-mod 只在同类参考，不得引用其常量"**
§456  **"那个注释想避免的错误，在另一个方向上犯了"**
§461  **"3.3.3.3 的服务器没有这套机械，而那就是为什么姿态在它上面能工作"**
⇒ **⇒ 三次"3.3.3.3 的简单来自它的 build**】
```

**✅ ⭐⭐⭐ **"3.3.3.3 的简单来自它的 build"**。

**⚠ 而"一个混淆的 getter"⇒ **§460 二.4 的 `dword_E60B78 ^ ps[36] ^ (ps+32)`** ✓

**⇒ 三层**：
```text
§460  **"`+0x10` 通过一个混淆的 getter 读：`sub_411360` 调 `dword_E60B78 ^ ps[36] ^ (ps+32)` 而 `ps+16` 是它的参数**"
§461  **"通过 `GET` 访问器在每个原生阶段之后捕获回来"**
⇒ **⇒ 所以【那个 getter 是【一个 XOR 混淆**】
```

**✅ ⭐⭐ **"那个 getter 是一个 XOR 混淆"**。

### 2.4 而**"`0x1800` 掩码"**

**✅ 与 §415 的 `PlayerOtherFlagsServerOwnedMask = 0x1800`** 完全闭合 ✓

**⇒ 三层**：
```text
§415  **"`ps+0x10` 的 `flags` 字与引擎共享；`BG_PlayerStateToEntityState` 测 `(flags & 0x1800)`，而那两位是服务器唯一拥有的部分"**
§461  **`(own & ~0x1800) | (source & 0x1800)`**
⇒ **⇒ 一个掩码的完整实现**
```

**✅ ⭐⭐⭐ **"一个掩码的完整实现"**。

## 三、**"一个被遗漏的常量拒绝整个出生"**（本组第二重要）

### 3.1 那段

```cpp
// CODDIFF(1649370): 0x3FF and 0x7FF WERE 3.3.3.3's TEN- AND ELEVEN-BIT
// WIDTHS. This build writes the pool index in 11 bits and the count in
// 12 (AmmoPoolIndexBits/AmmoPoolCountBits in sv_snapshot_mp.cpp), and
// EngineBindings already validates weapon defs against 0x7FF. This copy
// was missed, so a legitimate ammo index -- the wire carries 1188 and
// 1297, both past 0x3FF -- failed the reverse admission, which refused
// the native round trip, which refused the spawn. One constant in more
// than one file, exactly as section 36a wrote down.
```

### 3.2 二十层

```text
1. **`0x3FF` 与 `0x7FF` 曾是 3.3.3.3 的【十位与十一位**宽度**】**
2. ⇒ **这个 build 【把池索引写在 `11` 位而计数在 `12` 位**】**
3. ⇒ **（`sv_snapshot_mp.cpp` 的 `AmmoPoolIndexBits`/`AmmoPoolCountBits`）**
4. ⇒ **而 `EngineBindings` 【已经把武器 def 验证到 `0x7FF`**】**
5. ⇒ **⚠ 【这个拷贝【被漏掉了**】**
6. ⇒ **⇒ 所以【一个合法的弹药索引 ⇒ 线上携带 `1188` 与 `1297`，**两者都超过 `0x3FF`**】**
7. ⇒ **⇒ 【失败了反向往返** → **失败了原生的往返** → **失败了那个出生**】**
8. ⇒ **⇒ 一个常量在多于一个文件里，正如第 `36a` 节写下的**
```

### 3.3 ⭐⭐⭐ **"一个合法的弹药索引 ⇒ 失败了反向往返 ⇒ 失败了原生的往返 ⇒ 失败了那个出生"**

**✅ 这是本报告里**最重要的一条"一个常量的三阶后果**。**

**✅ 与 §431 的"一个裸字面量是三条已记录的隐藏方式之一"**——**完全同族** ✓

**⇒ 三层**：
```text
§431  **"一个在比较里的裸字面量【从每一个审计器那里藏起来**】"
§461  **"一个常量【在多于一个文件里】，而【这个拷贝被漏掉了**】"
⇒ **⇒ 同一根：**重复的常量**
```

**✅ ⭐⭐⭐ **"同一根：重复的常量"**。

**⚠ 而"三阶后果"⇒ **一个精确的链条**。**

**⇒ 三层**：
```text
① 反向往返失败 ⇒ 一个 `ammoPool/index_out_of_range`
② 原生往返失败 ⇒
③ 出生失败 ⇒ **一个客户端卡在加载屏**
```

**✅ 与 §428 的"gamestate 死锁的六个环节"**同族（**第二次"一个因果链**）。

**⇒ 三层**：
```text
§428  **六个环节**（没有 gamestate → ClientLoading → ... → 没有快照）
§461  **三个环节**（反向往返 → 原生往返 → 出生）
⇒ **⇒ 两次"一个因果链**】
```

**✅ ⭐⭐ **一个"因果链"的两例**。

**⚠ 而"线上携带 `1188` 与 `1297`"⇒ **两个具体的值**。**

**✅ 与 §388 的"`1147..1154` 八个模块化武器"**、§413 的"`1148` 是 loot 带的第一个"**配合。

**⇒ 三层**：
```text
`1147` ⇒ `firstDynamicWeapon`
`1148` ⇒ loot 带的第一个
`1188` / `1297` ⇒ **两个在线上实测的弹药索引**
⇒ **⇒ 所以【`1297` 远超 `0x3FF`（`1023`）**】
```

**✅ ⭐⭐ **"`1297` 远超 `0x3FF`"**。

### 3.4 而**`AmmoClipIndexBits = 11` ⇒ `0x7FE` 而 `-1` 是哨兵**

```cpp
// AmmoClipIndexBits is 11 on this build, so the last usable index is
// 0x7FE and -1 stays the empty sentinel. EngineBindings agrees.
if (clipIndex < -1 || clipIndex > 0x7FE)
    return refuse("ammoClip/index_out_of_range");
```

**⇒ 十层**：
```text
1. **`11` 位 ⇒ `0..2047`**
2. ⇒ **而 `-1` 是一个哨兵**
3. ⇒ **⇒ 所以【可用的最大是 `0x7FE`（`2046`）**】
4. ⇒ **⇒ 因为【`0x7FF`（`2047`）被【`-1` 的位模式占用了**】】
```

### 3.5 ⭐⭐⭐ **"`0x7FE` 是最大而 `-1` 占用了 `0x7FF`"**

**✅ 与 §416 的"`EntityNumNone = 2047`"**——**第四次"`2047` 是一个哨兵** ✓

**⇒ 三层**：
```text
`-1`（`int32`）⇒ **在 `11` 位里是 `0x7FF`**
而 `0x7FF` ⇒ **`2047`**
⇒ **⇒ 所以【一个 `11` 位的域【只能用到 `0x7FE`**】
```

**✅ ⭐⭐⭐ **"`-1` 的位模式占用了那个最大值"**。

**⚠ 而"`-1` vs `0` 的空弹夹哨兵策略【未被恢复**】"**

```cpp
// TODO(CODOL): recover the exact -1 versus 0 empty-clip sentinel policy from
// MSG_ReadDeltaPlayerstate and the ammo helpers before tightening nonzero
// counts for clipIndex -1.
```

**✅ 与 §416 的"`clipIndex == 0` 是空槽"**——**一个未闭合的区别**。

**⇒ 三层**：
```text
§416  **"`clipIndex` 的空槽是 `0`"**
§461  **"`-1` vs `0` 的空弹夹哨兵策略【未被恢复**"**
⇒ **⇒ 所以【两个哨兵【共存**而【语义未定**】
```

**⚠ 一个**重要的未闭合点**。

## 四、**八个 `static_assert`，钉在数组的末端**（本组第三重要）

### 4.1 八个

```cpp
static_assert(HeldWeaponIndexesOffset + 15 * sizeof(std::uint32_t) == HeldWeaponStatesOffset);
static_assert(HeldWeaponStatesOffset + 15 * HeldWeaponStateStride == 0x3E4);
static_assert(HeldWeaponStatesOffset + 15 * HeldWeaponStateStride <= CurrentWeaponOffset);
static_assert(AmmoClipsOffset + 15 * AmmoClipStride == 0x548);
static_assert(AmmoPoolsOffset + 15 * AmmoPoolStride == AmmoClipsOffset);
static_assert(AmmoClipsOffset + 15 * AmmoClipStride <= ObjectivesOffset);
static_assert(ObjectivesOffset + 32 * ObjectiveStride <= SvNativePlayerState::Size);
static_assert(PredictableEventsOffset + 4 * sizeof(SvNativePredictableEvent) <= ClientNumOffset);
```

### 4.2 那段注释

```php
// Pin the array to its END, not merely below the next member. The
// `<=` form alone passes for any stride at or under the real one, and
// that is exactly how a stride of five survived a 180-byte region.
// 0x3E4 is playerState netfield index 53, the first field above the
// array in re/demo-re/netfields-ol/playerstate-0x00DA8540.tsv. (That
// filename is OL.exe's address; the same table is at 0x00DA8520 on
// out.exe and its CONTENT is byte-identical -- section 84.)
```

### 4.3 二十层

```text
1. **把那个数组【钉在它的【末端**】，不只是【在下一个成员之下**】**
2. ⇒ **⚠ 【`<=` 形式单独【对【任何【等于或小于**真实步长的步长【都通过**】】
3. ⇒ **⇒ 而【那正是【一个步长 `5` **在一个 `180` 字节的区域里【存活下来**】的方式**】**
4. ⇒ **`0x3E4` 是 `playerState` 的网络字段索引 `53`**
5. ⇒ **⇒ 那个数组之上的【第一个字段**】
6. ⇒ **⇒ 在 `re/demo-re/netfields-ol/playerstate-0x00DA8540.tsv` 里**
7. ⇒ **⚠ （那个文件名【是 `OL.exe` 的地址**；同一个表在 `out.exe` 上是 `0x00DA8520`）
8. ⇒ **而【它的内容【是逐字节相同的**】——第 `84` 节）
```

### 4.4 ⭐⭐⭐ **"`<=` 形式单独对任何等于或小于真实步长的步长都通过，而那正是一个步长 `5` 在一个 `180` 字节的区域里存活下来的方式"**

**✅ 这是本报告里**最重要的一条"一个弱的断言的失败**。**

**✅ 与 §423 的"`static_assert(sizeof(WorldClientState) == 25184)` 是一条规则而不是一个意外"**——**相反** ✓

**⇒ 三层**：
```text
§423  **`==` 形式** ⇒ **一条不可违反的规则**
§461  **`<=` 形式** ⇒ **一个步长 `5` **存活下来**】
⇒ **⇒ 所以【`==` 优于 `<=`**】
```

**✅ ⭐⭐⭐ **"`==` 优于 `<=`"** —— 一个**极精确的断言设计判据**。

**⚠ 而"一个步长 `5` 在一个 `180` 字节的区域里存活"**⇒ **`15 × 5 = 75` 而【区域是 `180`**】** ⇒ **`75 <= 180` ⇒ 通过**。

**⇒ 三层**：
```text
`15 × 5 = 75`
`<= 180` ⇒ **通过**
⇒ **⇒ 所以【一个错的步长【通过了那个断言**】
```

**✅ ⭐⭐ **"一个错的步长通过了那个断言"**。

### 4.5 而**"`0x00DA8540` 是 `OL.exe` 的而 `0x00DA8520` 是 `out.exe` 的，而内容逐字节相同"**

**✅ 与 §415 的"`OL.exe` 自己的名字数组（`0xE5FD38`）"**、§415 的"out.exe 的 `0x00DA6B08` vs OL.exe 的 `0x00DA6B28`"**完全闭合 ✓

**⇒ 三层**：
```text
§415  **"`0x00DA6B28`/`0x00DA4920` 与 `sub_671250`/`sub_678390` 是 `OL.exe`（build 1608541）的，而 `out.exe` 的 `0x00DA6B08`/`0x00DA4900`"**
§461  **"`0x00DA8540` 是 `OL.exe` 的地址；同一个表在 `out.exe` 上是 `0x00DA8520`，而内容逐字节相同"**
⇒ **⇒ 两次"-0x20 的偏移而内容相同"**
```

**✅ ⭐⭐⭐ **"两次 `-0x20` 的偏移而内容相同"** —— 而 **`0xDA8540 - 0xDA8520 = 0x20`** ✓，**`0xDA6B28 - 0xDA6B08 = 0x20`** ✓

**✅ ⭐⭐⭐ **"一个统一的 `-0x20`"** —— 与 §415 的"**数据半部那个翻译是一个统一的 `-0x20`，而代码半部不是统一的**"**完全一致** ✓

**⇒ 三层**：
```text
§415  **"数据半部是一个统一的 `-0x20`"**
§461  **两个表的差也是 `0x20`**
⇒ **⇒ 一个一致的规律**
```

**✅ ⭐⭐⭐ **"一个一致的规律"**。

## 五、`SV_OverlayPlayerStateToNative` 的"故意的保留每一个未知的原生字节"

```cpp
// OLMOD(native-playerstate-forward-projection): source gameplay owners
// maintain the recovered field domains; this overlay deliberately
// preserves every unknown native byte. The reverse projection below
// remains the fail-closed admission boundary after native mutation.
```

**⇒ 十层**：
```text
1. **源玩法所有者【维护那些恢复的字段域**】**
2. ⇒ **这个覆盖【故意地【保留每一个未知的原生字节**】**
3. ⇒ **⇒ 所以【一个"只写已知的**"的覆盖**
4. ⇒ **而【下面的反向投影【仍然是那个【fail-closed**的准入边界**】
5. ⇒ **⇒ 所以【一个【前向覆盖 + 一个【反向准入**】
```

**✅ 与 §429 的"`base = ours` ⇒ 字段相等 ⇒ 不发"**不同（这是**一个方向性的不对称**）。

**⇒ 三层**：
```text
前向（源 → 原生）⇒ **只写已知的，保留未知的**
反向（原生 → 源）⇒ **fail-closed，拒绝任何越界**
⇒ **⇒ 所以【两个方向两个策略**】
```

**✅ ⭐⭐⭐ **"两个方向两个策略"**。</br>

**✅ 与 §418 的"`SvEntityState{}` 不是零"**同族（**第五次"一个方向性的不对称**）。

**⇒ 三层**：
```text
§418  **`SvEntityState{}` 的默认值【不是零**】⇒ **一个陷阱**
§461  **前向保留未知字节而反向 fail-closed** ⇒ **一个策略**
⇒ **⇒ 两次"方向性的不对称**】
```

**✅ ⭐⭐ **"方向性的不对称"两例**。

## 六、`readObjectives` 的"私有副本"

```cpp
// OLMOD(native-playerstate-objective-admission): use a private
// copy so a malformed late record cannot publish earlier records.
auto next = destination;
for (...) { ... if (bad) return false; next[index] = {...}; }
destination = std::move(next);
return true;
```

**⇒ 八层**：
```text
1. **一个私有副本**
2. ⇒ **⇒ 所以【一个畸形的【后面的**记录【不能【发布前面的**记录**
3. ⇒ **⇒ 而【那个副本【只在全部有效**时才 `move`**
4. ⇒ **⇒ 一个"全或无**"的提交**
```

**✅ 与 §443 的"`spawnModel` 的两步一个事务"**同族（**第八次"事务性**）。

**⇒ 三层**：
```text
§409/§422/§430/§433/§443/§457/§461  ⇒ **七次"全或无**】
```

**✅ ⭐⭐ **"七次全或无"**。

**⚠ 而"一个畸形的**后面的**记录不能发布前面的"⇒ **一个精确的表述**。**

**⇒ 三层**：
```text
若【直接写 `destination[index]`**】⇒ **前面几个【已经改了**】
而【最后一条失败**】⇒ **一个【部分更新**】
⇒ **⇒ 所以【必须私有副本**】
```

**✅ ⭐⭐ **"一个部分更新"**。

## 七、`SV_SetNativeAbilityModifiers` 的 `0x590`/`0x5A8`

```cpp
// CODREF(1649370): identical destinations to the retail snapshot
// consumer at 0x54C236 and 0x54C278; 0x4E8020 copies 36 floats.
std::memcpy(state.bytes.data() + 0x590, abilities.mask.data(), 24);
std::memcpy(state.bytes.data() + 0x5A8, abilities.values.data(), 144);
```

**⇒ 十层**：
```text
1. **`0x590` ⇒ `24` 字节（`6` 个 `uint32`）** ⇒ **`mask`**
2. ⇒ **`0x5A8` ⇒ `144` 字节（`36` 个 `float`）** ⇒ **`values`**
3. ⇒ **⇒ 而 `0x4E8020` **拷贝 `36` 个 `float`**】**
4. ⇒ **⇒ 所以【`36` 与 `144/4 = 36` 吻合**】
```

**✅ ⭐⭐ **"`144 / 4 = 36` 与那个 `36` 吻合"**。

**⚠ 而"`0x590` 与 §416 的 `PerksOffset = 0x584`"**⇒ **`0x590 - 0x584 = 0xC`**。

**⇒ 三层**：
```text
`PerksOffset = 0x584`（**`3` 个 `uint32` `0x584..0x58F`**）
`0x590` ⇒ **紧接其后**
⇒ **⇒ 所以【`perks` 与 `abilities` 相邻**】
```

**✅ ⭐⭐ **"`perks` 与 `abilities` 相邻"**。

**✅ 与 §416 的"`perks` 三个连续 `32` 位 netfield 在 `0x584/0x588/0x58C`"**完全闭合 ✓

## 八、`observeUavWeaponChanges` 与 `SvUavEarningState` 的"六个字段"

**⇒ 从 `sv_main_mp.hpp` 的 `UavOwner`**：

```cpp
struct UavOwner {
    std::uint64_t xuid{};
    SvUavEarningState state;
    std::optional<SvRewardWeapon> weapon;
    std::uint16_t lastGun{}, committedWeapon{};
    std::optional<std::uint8_t> committedLife;
    bool returning{}, returnQueued{};
    bool testRewardGranted{};
    bool radarManaged{};
    std::vector<std::uint32_t> radarExpiries;
};
```

**⇒ 十层**：
```text
1. **`xuid` ⇒ 一个身份**
2. ⇒ **`state` ⇒ 一个`SvUavEarningState`**（**一个外部类型**）
3. ⇒ **`weapon` ⇒ 一个可选的 `SvRewardWeapon`**
4. ⇒ **`lastGun`/`committedWeapon` ⇒ 两个武器号**
5. ⇒ **`committedLife` ⇒ 一个可选的代次**
6. ⇒ **`returning`/`returnQueued` ⇒ 两个布尔**
7. ⇒ **`testRewardGranted` ⇒ 一个测试标志**
8. ⇒ **`radarManaged` ⇒ 一个管理标志**
9. ⇒ **`radarExpiries` ⇒ 一个过期时间列表**
10. ⇒ **⇒ 十个字段**】
```

**✅ 与 §457 的"`noclip` 的 peer 地址"**不同（这是**一个 UAV 的状态**）。

**⚠ 而"`radarExpiries` 是一个 `vector`"**⇒ **一个可增长的状态**。】

**⇒ 三层**：
```text
其它字段 ⇒ **标量**
`radarExpiries` ⇒ **一个 `vector<uint32>`**
⇒ **⇒ 所以【一个 UAV 可以【有多个雷达过期时间**】
```

**✅ ⭐⭐ **"一个 UAV 可以有多个雷达过期时间"** — 与 §413 的"`setPlayerRadarFlags`"配合。

## 九、关键结论

1. **⭐⭐⭐ "合并，不要替换：`ps+0x10` 携带引擎的 `flags` 字（姿态与开关状态在其中），这个服务器只拥有 `BG_PlayerStateToEntityState` 测以选 `ET_PLAYER` 而不是 `ET_INVISIBLE` 的两个位 ⇒ 在这里赋整个字正是每帧扔掉引擎的状态的东西"`**，而 **"dest1yo 的 3.3.3.3 服务器完全没有这套机械 —— 那里的 `ps+0x10` 是一个普通的 `dword`，而那正是为什么姿态在它上面能工作"`** —— **"同一个代码在两个 build 上一个对一个错"**（第三次"3.3.3.3 的简单来自它的 build"）。
2. **⭐⭐ `ps+0x10` 的 getter 是一个 XOR 混淆**（`dword_E60B78 ^ ps[36] ^ (ps+32)`，§460）⇒ 与"通过 `GET` 访问器在每个原生阶段之后捕获回来"闭合。
3. **⭐⭐⭐ "一个合法的弹药索引 ⇒ 失败了反向往返 ⇒ 失败了原生的往返 ⇒ 失败了那个出生"`**：**`0x3FF`/`0x7FF` 曾 3.3.3.3 的位宽，而这个 build 把池索引写在 `11` 位而计数在 `12` 位，`EngineBindings` 已改而【这个拷贝被漏掉了】，所以线上携带的 `1188` 与 `1297`（两者都超过 `0x3FF`）被拒绝** ⇒ **"一个常量在多于一个文件里，正如第 `36a` 节写下的"`** —— **"同一根：重复的常量"**（与 §431 同族），也是一个**三阶因果链**（与 §428 同族）。
4. **⭐⭐⭐ `AmmoClipIndexBits = 11` ⇒ 最大 `0x7FE` 而 `-1` 是哨兵** ⇒ **"`-1` 的位模式（`0x7FF`）占用了那个最大值"`** —— 第四次"`2047` 是一个哨兵"。
5. **⚠ 一个重要的未闭合**：**`-1` vs `0` 的空弹夹哨兵策略【未被恢复**】（`TODO(CODOL)`）—— 而 §416 说 `clipIndex == 0` 是空槽 ⇒ **两个哨兵共存而语义未定**。
6. **⭐⭐⭐ "把那个数组钉在它的【末端】，不只是【在下一个成员之下】：`<=` 形式单独对任何等于或小于真实步长的步长【都通过】，而那正是【一个步长 `5` 在一个 `180` 字节的区域里存活下来**】的方式"`** —— **"`==` 优于 `<=`"**（与 §423 的 `==` 断言相对照）。
7. **⭐⭐⭐ 一个统一的 `-0x20`**：**`0x00DA8540`（`OL.exe`）vs `0x00DA8520`（`out.exe`）差 `0x20`**，而 **`0x00DA6B28` vs `0x00DA6B08` 也是 `0x20`**（§415）⇒ **"一个一致的规律"**（与 §415 的"数据半部是一个统一的 `-0x20`"完全一致）。
8. **⭐⭐⭐ `SV_OverlayPlayerStateToNative` 的"故意的保留每一个未知的原生字节"`**：**前向只写已知的，反向 fail-closed** ⇒ **"两个方向两个策略"**（第五次"方向性的不对称"，与 §418 同族）。
9. **⭐⭐ `readObjectives` 的"私有副本 ⇒ 一个畸形的后面的记录不能发布前面的"`** —— **第八次"事务性（全或无）"**。
10. **⭐ `SV_SetNativeAbilityModifiers` 的 `0x590`（`24` 字节 = `6` 个 `uint32`）与 `0x5A8`（`144` 字节 = `36` 个 `float`）**，而 **`144 / 4 = 36` 与 `0x4E8020` 的"拷贝 `36` 个 `float`"吻合**；而 **`0x590` 紧接 `PerksOffset = 0x584` 的 `3` 个 `uint32`** ⇒ **"`perks` 与 `abilities` 相邻"**。
11. **⭐ `UavOwner` 的十个字段**（`xuid`/`state`/`weapon`/`lastGun`/`committedWeapon`/`committedLife`/`returning`/`returnQueued`/`testRewardGranted`/`radarManaged`/`radarExpiries`），其中 **`radarExpiries` 是一个 `vector`** ⇒ **"一个 UAV 可以有多个雷达过期时间"`**。

## 十、未闭合点

- `-1` vs `0` 的空弹夹哨兵策略。
- `HeldWeaponStateStride` 的精确值（注释说"步长 `5`"曾存活）。
- `SvUavEarningState` 的定义。
- `observeUavWeaponChanges` 的实现。
- `sv_native_playerstate_mp.cpp` 820 行之后未读取（**共 `1687` 行**）。
