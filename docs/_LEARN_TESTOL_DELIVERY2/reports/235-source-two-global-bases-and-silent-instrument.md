# 235 · 两个全局基址、`0x144` 让仪器完全沉默、`verbose()` 热日志修复

## 一、范围

本报告学习 `EngineBindings.cpp` 8099–8299 行。

## 二、`-1` 的两个成因，与"DEATH 的第二个不可能"

这是本组最重要的一段。

### 2.1 `BG_AnimScriptEvent` 的 -1 机制

```text
BG_AnimScriptEvent sub_407E10 只在它的遍历器 sub_407790 【从未写入】
调用者在 0x00407E4B 预置为 -1 的 out 参数时返回 -1，
而那恰好以【两种】方式发生：
    该事件没有 set（0x004077B0 处 numItems <= 0）
    或每一个 set 的条件都失败
```

### 2.2 DEATH 的第二个不可能

```text
OLfinal 自己的 mp/playeranim.script 用【一个无条件 default set】
（十一个动画）结束 DEATH 块，
而 sub_407790 无法拒绝一个零条件的 set —— 它的内层循环干脆不运行 ——
所以对 DEATH 第二个原因【不可能】，空表就是全部答案。
```

**"`sub_407790` 无法拒绝一个零条件的 set —— 它的内层循环干脆不运行"**

**所以零条件 = 无条件通过** ⇒ **只要 `numItems > 0`，DEATH 一定选中一个动画。**

**这使 `numItems` 成为唯一需要检查的量。**

## 三、**两个全局基址**：`0x827F734` 与 `0x827F730`

### 3.1 反汇编

```text
sub_407E10 从 dword_827F734（0x00407E14）取【脚本表】
          从 dword_827F730（0x00407E37）取【characterInfo】
```

### 3.2 而 `installServerAnimConditionStorage` **只装第二个**

```text
installServerAnimConditionStorage 只装第二个；
第一个持有【本进程里最后一次 sub_407530 留在那里的任何东西】，
而本项目在初始化之后【从不写它】。
```

### 3.3 后果

```text
If `live` and `ours` differ, every death since that moment walked a
foreign script block -- which no existing line could have shown.
```

**"如果 `live` 与 `ours` 不同，那么从那一刻起每一次死亡都走了一个外来的脚本块 —— 而没有任何现有日志行能显示这一点。"**

### 3.4 所以 `logServerAnimScriptEvent` **从两个基址读**

```cpp
const auto* ours = serverAnimConditionStorage_.data();
const auto* live = (const std::byte*)InterlockedCompareExchangePointer(
    (void* volatile*)animScriptDataPointer_, nullptr, nullptr);
const auto read = [offset](const std::byte* base) {
    return base && readableSpan(base + *offset, sizeof(int32))
        ? *(const int32*)(base + *offset)
        : numeric_limits<int32>::min();
};
snprintf(detail, sizeof(detail),
    "server animation scriptEvent event=%d offset=0x%zX "
    "ours=0x%08X items=%d live=0x%08X items=%d same=%u",
    animationEvent, *offset, (uint32)(uintptr_t)ours, read(ours),
    (uint32)(uintptr_t)live, read(live), live == ours ? 1u : 0u);
```

### 3.5 那个 `numeric_limits<int32>::min()` 哨兵

**"读不出"用 `INT32_MIN` 表示** —— 而不是 0。

**因为 0 是合法值（`numItems <= 0` 触发 -1）** —— 所以需要一个不可能的值。

**与 §219 里 `0xFFFFFFFF` 作为 `uint8` 的哨兵同一手法。**

### 3.6 注释里的那句"没有一行能显示"

**"Nothing in this project has ever read that dword."**

**`dword_827F734` 的 `numItems` 从未被读过** —— 而这条日志是第一次。

## 四、`logServerAnimConditions`：`0x144` 让仪器完全沉默

### 4.1 那次"静默的仪器读起来像健康的"

```cpp
// CODDIFF(1649370): 0x144 IS 3.3.3.3'S clientNum OFFSET. This build keeps
// clientNum at ps+0x158 -- audit-ported-offsets has ClientNumOffset moving
// 0x144 -> 0x158 -- and the engine itself indexes the characterInfo array
// with it: sub_407E10 does `mov ecx, [edi+158h]` then
// `imul ecx, 450h; lea ecx, [ecx+edx+0AF350h]`. Reading 0x144 got some
// other field, which is almost always >= 18, so this diagnostic returned
// WITHOUT LOGGING ANYTHING -- a silent instrument, which reads exactly like
// a healthy one.
```

### 4.2 完整链条

```text
1. `0x144` 是 3.3.3.3 的 clientNum，本 build 在 `+0x158`
2. 读 `0x144` 得到某个其它字段，几乎总是 >= 18
3. `if (slot >= ServerCharacterInfoSlotCount(18)) return;` ⇒ 直接返回
4. ⇒ 【什么都不记】
5. ⇒ 【一个沉默的仪器读起来完全像一个健康的】
```

**这是本项目第三次出现同一条教训**：

```text
§225：闩锁让三个状态从未出现过（"仪器瞎了"）
§234：只读健康的那一半（"populated=43/47"而死亡全失败）
§235：读错偏移导致提前返回（"silent instrument = healthy"）
```

### 4.3 三条独立证据

```text
audit-ported-offsets 的 ClientNumOffset 0x144 → 0x158
sub_407E10 的 `mov ecx,[edi+158h]` 然后 `imul ecx,450h; lea ecx,[ecx+edx+0AF350h]`
    —— 与 §184 里 `0xAF350 + 18*0x450` 的布局一致
```

## 五、`verbose()` 的热日志修复

### 5.1 两处

```cpp
if (slot >= ServerCharacterInfoSlotCount)
{
    if (OlMod::RuntimeLog::verbose())   // ★ 2026-10-13（热日志修复）
    OlMod::RuntimeLog::write(...);
    return;
}
...
if (OlMod::RuntimeLog::verbose())   // ★ 2026-10-13（热日志修复）：逐帧动画条件诊断默认关
OlMod::RuntimeLog::write(...);
```

### 5.2 注意缩进

```cpp
if (verbose())
RuntimeLog::write(...);   // ← 【没有缩进】
```

**`write` 在下一行但【没有匹配 if 的缩进】** —— 所以看起来像无条件调用。

**但它实际在 `if` 的控制下**（C++ 不看缩进）。

**这是一处可读性问题** —— 容易让人误判。

### 5.3 中文注释

**"★ 2026-10-13（热日志修复）：逐帧动画条件诊断默认关"**

**这是文件里少数中文注释之一** —— 说明这次修复是后来的运维发现。

## 六、`logServerAnimConditions` 的两个判据

```cpp
// OLMOD(locomotion-anim-diagnostics): read back the conditions the
// native PmoveSingle just wrote through the derived characterInfo. A
// zero at +0x288 means the relocation is still wrong; a non-zero
// +0x288 with a zero +0x2A0 means the conditions arrive but the
// locomotion selector still refuses to pick an animation.
```

**两个判据**：

```text
+0x288 为零           ⇒ 重定位仍是错的
+0x288 非零 +0x2A0 零 ⇒ 条件到达了但选择器仍拒绝选动画
```

### 6.1 两个偏移

```cpp
constexpr size_t CharacterInfoConditionBaseOffset = 0x2EC;              // §222 里确认
constexpr size_t CharacterInfoMoveTypeConditionOffset = 0x304;
```

**而注释说的是 `+0x288` 与 `+0x2A0`** —— **那是 3.3.3.3 的**。

**§199 明确说过**：

> **CODDIFF(1649370): 0x288 和 0x2A0 是 3.3.3.3 的。**

**所以注释里的偏移已过时，而代码里用的是新值** —— 这与 §222 里 `+0x1C` 的注释滞后是同一类。

### 6.2 `CharacterInfoConditionCount = SvNativeAnimConditionCount = 19`

```cpp
for (index = 0; index < CharacterInfoConditionCount; ++index)
    if (read(CharacterInfoConditionBaseOffset + index * 8)) ++nonZero;
```

**19 个条件、每个 8 字节** —— 与 §199 里 `0x2EC + 8*index` 一致。

## 七、`CCS_Clear` 的返回值是**取反**

```cpp
bool EngineBindings::CCS_Clear() const
{
    if (!ccsClear_ || thread mismatch) return false;
    if (!invokeNoArgument(ccsClear_)) return false;
    constantConfigStringChecksum_.store(0);
    return !CCS_Initialized();
}
```

**`return !CCS_Initialized()`** —— **"清空成功"意味着"现在未初始化"**。

**所以语义是"清空后确认为未初始化"** —— 而不是"清空调用成功"。

## 八、`CCS_EnsureInitialized` 的三段

```cpp
if (CCS_Initialized()) return true;
if (!ccsInitialize_) return false;
ccsInitialize_();
return CCS_Initialized();
```

**模式**：

```text
1. 已经初始化 ⇒ true
2. 没绑定 ⇒ false
3. 调一次再验证
```

**与 §233 里 `initializeMantleAnimations` 的幂等形状相同。**

## 九、`findXAsset` 的第二问

```cpp
XAssetHeader EngineBindings::findXAsset(type, name, allowDefault) const
{
    if (!dbFindXAssetHeader_ || !name) return {};
    const auto header = dbFindXAssetHeader_(type, name, allowDefault);
    // allowDefault=false only suppresses the default on the MISS path.
    if (!allowDefault && header.data && dbIsXAssetDefault_ &&
        dbIsXAssetDefault_(type, name))
    {
        return {};
    }
    return header;
}
```

**四个条件 AND**：

```text
!allowDefault        ← 只在严格模式
header.data          ← 有返回
dbIsXAssetDefault_   ← 绑定存在
dbIsXAssetDefault_(type, name)  ← 真的是默认值
```

**这是 §182/§212/§233 里那条规则的**唯一**集中实现** —— 所以所有调用方都被保护。

## 十、`readConfigString` 的"空串即合法"

```cpp
if (!configStringGet_ || !maximumLength || !CCS_Initialized())
    return nullopt;
const auto* value = nativeConfigString(index);
if (readableSpan(value, 1) && !*value)
    return std::string{};        // ← 首个字节是 0 ⇒ 空串（合法）
return readCString(value, maximumLength);
```

**`readableSpan(value, 1) && !*value`** —— **指针可读且首字节为 0 ⇒ 返回空串**。

**否则交给 `readCString`** —— 而它会拒绝空串。

**所以这里区分了"明确的空串"与"读不出"** —— 与 §211 里 `readStringTableCell` 的"空即合法"同族。

## 十一、`firstDynamicWeaponAssetIndex` 的类型枚举

```cpp
auto* types = module_ + ConfigStringTypesRva;    // 0x73D8250
for (index = 1; index < WeaponConfigStringCount(1700); ++index)
{
    const auto type = types[WeaponConfigStringBase(5960) + index];
    // CODDIFF(1649370): the configstring class enum gained two members,
    // so both sentinels shift +2 - 3.3.3.3 asks for `19 || >= 21`.
    // The gamestate parser is the source: A 0x46DBF6 rejects an index
    // unless `type >= 0x15 || type == 19`, C 0x472E56 unless ...
}
```

### 11.1 两个 build 的判据

```text
3.3.3.3  接受 `type == 19 || type >= 21`
本 build  接受 `type >= 0x15(21) || type == 19`（3.3.3.3）
                         ↓ +2
         接受 `type >= 0x17(23) || type == 21`
```

**注意注释里的 `A 0x46DBF6` 与 `C 0x472E56`** —— `A`/`C` 是本项目对 3.3.3.3 与本 build 的代号。

### 11.2 `0x15` 是 21 而不是 0x15 = 21 ✓

**`0x15 = 21`**，而 3.3.3.3 的 `>= 21` 与 `== 19` —— 本 build 是 `>= 23` 与 `== 21`。

**"枚举多了两个成员，所以两个哨兵都 +2"**。

## 十二、关键结论

1. **DEATH 的第二个 -1 成因不可能**（零条件 set 无法被拒绝）。
2. **两个全局基址 `0x827F730`（characterInfo）与 `0x827F734`（脚本表）**，本项目只装前者。
3. **`numItems` 从未被读过** —— 而这条日志是第一次。
4. **`INT32_MIN` 作"读不出"哨兵**（因为 0 是合法值）。
5. **`0x144` 让仪器完全沉默** —— 第三次出现"沉默读起来像健康"。
6. **注释里的 `+0x288`/`+0x2A0` 已过时**（代码用 `0x2EC`/`0x304`）。
7. **`CCS_Clear` 返回"清空后确认为未初始化"**。
8. **`findXAsset` 是"两次问"的唯一集中实现**。

## 十三、未闭合点

- `logServerAnimConditions` 注释里的两个偏移需更新。
- `if (verbose())` 下的 `write` 缩进未对齐。
- `EngineBindings.cpp` 8299 行之后未读取。
