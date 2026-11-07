# 283 · **`>=` 把真人判成人机 ⇒ 11 个装饰被抹掉**、两处覆盖漏斗、`BOTTRACE` 的三缺口分类

## 一、范围

本报告学习 `Appmain.cpp` 2795–3020 行。

## 二、**占位符的两个值**（本组第二重要）

### 2.1 那段推理

```php
// The trade this branch already chose was a WRONG player model over a
// failed match. A zeroed one is not wrong, it is invalid, which is a
// different and much worse thing. So fill the two fields the validator
// insists on with the smallest legal placeholders: viewmodel 1, and
// selection 0 set to 1 (slot 0 is 7 bits, so 1..128 are legal). The
// model, colour and viewmodel remain wrong exactly as advertised --
// now they are wrong AND the player spawns.
```

### 2.2 三层

```text
1. 这条路已经选的是"错误玩家模型"胜过"失败比赛"
2. 而【清零的】不是"错"而是"无效" —— 那是更糟的东西
3. ⇒ 用【最小合法占位符】填校验器坚持的两个字段：
     viewmodelIndex = 1
     selectionIds[0] = 1
```

### 2.3 而"slot 0 是 7 位，所以 1..128 合法"

**⇒ 所以 `selectionIds[0]` 有 7 位宽。**

**⇒ 与 §256 的 `selectionIds` 是 11 项（`array<uint16,11>`？）—— 而第一项只有 7 位有效。**

**⚠ 一个字段内的**不均衡位宽**。**

### 2.4 而"错 AND 玩家能 spawn"

**⇒ 这是一个明确的取舍声明** ✓

## 三、`characterItemIds[0]` 的**语义**

```php
// AND SINCE SECTION 67 IT CARRIES THE ONE THING MODEL
// RESOLUTION ACTUALLY NEEDS. characterItemIds[0] is
// characterClasses[<character>].slots[0] -- the character item
// itself -- and sub_619AD0 derives the other eleven record entries
// from that character's own per-slot defaults. The viewmodel and
// selectionIds below stay the placeholders they were; they are the
// WIRE fields and this is not one.
```

### 3.1 四层

```text
1. `characterItemIds[0]` **就是** `characterClasses[<character>].slots[0]` —— 角色物品本身
2. 而 `sub_619AD0` 从那个角色的**自己的每槽默认值**推导出其它十一项
3. ⇒ viewmodel 与 selectionIds 是**线字段**而这一个**不是**
4. ⇒ 所以这个值比那十一个更重要
```

### 3.2 **"线字段 vs 不是线字段"**

**⇒ 这是一个精确的分类** —— 而 §282 说"它产生的是装饰性的"是指 viewmodel/selectionIds。

**⇒ 而 `characterItemId` 是**功能必需**的**（因为客户端从它推导装饰）。

### 3.3 而"零在这里不是缺陷"

```php
// A zero here is not a defect: it is every match this build ran
// before the capture existed, and resolveCharacterModelNames refuses
// a zero rather than resolving definition index 0.
```

**⇒ 所以零是**安全的**（拒绝而不是解析定义 0）。**

## 四、**`recordItemIds` 的 `static_assert`**

```php
static_assert(
    std::tuple_size_v<decltype(ClientCharacterPresentation{}.recordItemIds)> ==
    DedicatedSession::CharacterItemCount,
    "the presentation record and the session record must be the same "
    "twelve entries, or an outfit lands in the wrong slot");
```

### 4.1 与 §242 的 `static_assert` **同一条理由**

**§242**："`CharacterItemCount == SvCharacterRecordEntryCount`" / "or an outfit lands in the wrong slot"

**⇒ **完全相同的错误消息**。**

**⇒ 所以这是同一个不变式的**第二处**强制。**

### 4.2 而复制循环的**双界**

```php
for (std::size_t entry = 0;
     entry < recordItemIds.size() && entry < sessionMember.loadout.characterItemIds.size();
     ++entry)
{
    const auto itemId = sessionMember.loadout.characterItemIds[entry];
    if (itemId && itemId <= 0xFFFFu)
        recordItemIds[entry] = (uint16)itemId;
}
```

**⇒ 三项**：

```text
entry < 目标大小
entry < 源大小
itemId 非零 且 <= 0xFFFF
```

**⇒ 所以这是一个**有界的元素级复制**（不是 `memcpy`）。**

## 五、**`>=` 把真人判成人机**（本组最重要的一段）

### 5.1 那段完整的中文注释

```php
// ★★★ 2026-10-14 修复（甲方「我进图人物装饰还是没有」）—— **原来是 `>=`，把真人判成了人机**：
//   真人的 xuid 是本代 64 位平台号（实测 `16701785630074219790` ≈ 0xE7C2…），
//   **大于** `0x0B07'0000'0000'0000`（= 794,603,859,254,181,888）⇒ 该条件对**真人也为真**
//   ⇒ 真人被当成 bot 处理：`recordItemIds.fill(0)` + `recordItemIds[0] = 10362`
//   ⇒ **11 个装饰条目被抹掉、角色被强制成 `cha_zombiehunter`**。
//   实机证据（新埋点）：同一行里 `inputItems=12 inputNonZero=7`（客户端确实送了 7 项装饰），
//   而结果 `recordNonZero=1/12 slots=[0:10362]` ⇒ 就是被这一段清零的。
//   改为**区间判定**：bot 的 xuid 是 `base + index`（index 0..10）⇒ 只认 [base, base+4096)。
```

### 5.2 六层

```text
1. 真人的 xuid 是【本代 64 位平台号】，实测 `16701785630074219790` ≈ 0xE7C2…
2. 而它【大于】 `0x0B07000000000000`（794,603,859,254,181,888）
3. ⇒ 原来的 `>=` 对**真人也为真**
4. ⇒ 真人被当 bot：`recordItemIds.fill(0)` + `[0] = 10362`
5. ⇒ 11 个装饰条目被抹掉、角色被强制成 `cha_zombiehunter`
6. ⇒ 改为**区间判定** `[base, base + 4096)`
```

### 5.3 两个 64 位数字的**量级对比**

```text
真人 xuid    16701785630074219790  ≈ 1.67e19  ≈ 0xE7C2...
bot base     794603859254181888    ≈ 7.95e17  ≈ 0x0B07'0000'0000'0000
```

**⇒ 真人比 bot base **大 21 倍**。**

**⇒ 所以 `>=` 恒真。**

**⚠ 一个**经典的**边界方向错误。**

### 5.4 而"实机证据"的两个对比

```text
inputItems=12 inputNonZero=7        ← 客户端确实送了 7 项装饰
recordNonZero=1/12 slots=[0:10362]  ← 而结果只有 1 项
```

**⇒ **输入 7 项而输出 1 项** ⇒ 中间被清零。**

**⇒ 这是一个**完美的差分证据**。**

### 5.5 而 `cha_zombiehunter` 是 `10362`

**⇒ 所以默认 bot 角色是**僵尸猎人**。**

**⇒ 而 §283 后面说 `10362` 在 2026-10-08 的会话里渲染成 `fpa_tightjeans_red`。**

**⚠ `cha_zombiehunter` 与 `fpa_tightjeans_red` 是两个不同的名字。**

**⇒ 可能 `10362` 的**内部名**是 `cha_zombiehunter` 而**模型**是 `fpa_tightjeans_red`。**

**⇒ 或者注释里的两个说法不一致。**

### 5.6 **修复后的区间判定**

```php
constexpr std::uint64_t botXuidBase = 0x0B07'0000'0000'0000ull;
constexpr std::uint64_t botXuidCount = 4096;
if (sessionMember.userId >= botXuidBase &&
    sessionMember.userId < botXuidBase + botXuidCount)
```

**⇒ 区间 `[base, base + 4096)`。**

**⇒ 而注释说"bot 的 xuid 是 `base + index`（index 0..10）"** ⇒ 11 个 bot。

**⇒ 所以 4096 是**宽松的上界**。**

### 5.7 而 `BotXuidBase` 的**重复声明**

```php
// BotXuidBase is declared further down this translation unit, so
// the sentinel is repeated here rather than reordered: same value,
// same band. Bots only -- a real member never matches.
constexpr std::uint64_t botXuidBase = 0x0B07'0000'0000'0000ull;
```

**⇒ 重复是为了避免重排**（因为 `BotXuidBase` 在文件后面声明）。

**⚠ 一处**重复常量** —— 如果两处不一致就会出错。**

**⇒ 与 §280 的 `pinnedSession` 命名过时同族（小的技术债）。**

## 六、`OLMOD_CHARACTER_ITEM` 的覆盖

```php
// OLMOD(character-item-override): FORCE THE CHARACTER, so the
// operator can enter with a chosen character without depending on
// the in-game selector (which needs entitlements and a working
// CharacterSelectionResolve). ONE variable, unset = byte-identical
// behaviour to before. Entry 0 carries the character; entries 1..11
// are the outfit pieces, and the client derives a character's own
// per-slot defaults from entry 0 alone, so an override zeroes them
// rather than mixing two characters' clothes.
if (const auto overrideItem = overriddenCharacterItem(); overrideItem != 0)
{
    characterItemId = overrideItem;
    recordItemIds.fill(0);
    recordItemIds[0] = (uint16)overrideItem;
    logGameServer("character item override: item=" + N + " (from OLMOD_CHARACTER_ITEM or Ayria\\Logs\\olmod-character.txt; outfit record zeroed to the character default)");
}
```

### 6.1 四层

```text
1. 让操作者用一个选定的角色进入，不依赖游戏内选择器（它需要 entitlements 和可用的 CharacterSelectionResolve）
2. 一个变量，未设置 ⇒ 与之前逐字节相同
3. Entry 0 携带角色；1..11 是服装件
4. ⇒ 客户单从 entry 0 单独推导角色的每槽默认值 ⇒ 所以覆盖时清零它们而不是混两个角色的衣服
```

### 6.2 而"清零而不是混两个角色的衣服"

**⇒ 一个**重要的正确性论点**。**

### 6.3 而那段证据

```php
// Evidence this is the right funnel: the 2026-10-08 13:32 session
// selected character index 3 (item 10362) through the normal path and
// the client rendered `fpa_tightjeans_red` with its own attaches, so
// the chain characterItemId -> model names is proven end to end.
```

**⇒ 所以 `10362` 渲染成 `fpa_tightjeans_red`。**

**⇒ 而 §5.5 说 `cha_zombiehunter` 是 10362。**

**⇒ 所以 `cha_zombiehunter` 的**表现**是 `fpa_tightjeans_red`。**

**✓ 不矛盾 —— 一个是 item 名一个是模型名。**

## 七、**两个覆盖漏斗的顺序**

```text
① OLMOD_CHARACTER_ITEM 覆盖（全局，对所有成员）
② OLMOD_BOT_CHARACTER 覆盖（只对 bot）
```

**⇒ ② 在 ① 之后 ⇒ 所以 bot 的覆盖**优先**。**

**⚠ 而 ① 的日志说 "from OLMOD_CHARACTER_ITEM or Ayria\Logs\olmod-character.txt"。**

**⇒ 所以 ① 会先作用于**所有人**（包括 bot），然后 ② 再改 bot。**

**⇒ 如果 ① 设了而 ② 也设了，bot 用 ② 的而真用 ① 的。** ✓

## 八、**`BOTTRACE|human-presentation` 的三缺口分类**（本组第三重要）

```php
// ★★★ 2026-10-14（② 诊断）—— 甲方「**我进图人物装饰还是没有**」。
//   注意：这一条**不是**被"人机复制我"顶掉的（撤掉那份拷贝后依然没有）⇒ 根因在**真人自己**这份呈现。
//   这一行把**发出去的**呈现原样打出来（每次会话准备一行，低频），据此一次性区分三种缺口：
//     a) characterItemId 或 recordItemIds 全 0 ⇒ 我们**根本没解析出装饰条目**（缺口在解析/配装来源）
//     b) 条目非 0 但客户端不显示 ⇒ 缺口在**发布/客户端呈现**（转 clientInfo 与外观槽核对）
//     c) 只有 entry0 非 0（= 只发角色、不发部件）⇒ 缺口在"部件没进 recordItemIds"
```

### 8.1 三个缺口

```text
a) characterItemId 或 recordItemIds 全 0    ⇒ 缺口在【解析/配装来源】
b) 条目非 0 但客户端不显示                   ⇒ 缺口在【发布/客户端呈现】
c) 只有 entry0 非 0                          ⇒ 缺口在"部件没进 recordItemIds"
```

**⇒ 而 §5 的 bug 正是 (c)！**

**⇒ 所以这个诊断的设计**恰好**抓住了那个 bug。**

### 8.2 而"不是被人机复制顶掉的"

**⇒ "撤掉那份拷贝后依然没有"** —— 一个**排除法**。

**⇒ 与 §277 的"我瞄的正是那堵墙"同族（排除一个假设）。**

### 8.3 而 `inputItems` / `inputNonZero` 的**输入侧**

```php
" inputItems=" + loadout.characterItemIds.size() +
" inputNonZero=" + count_if(begin, end, [](v) { return v != 0; })
```

**⇒ 两个**输入侧**量。**

### 8.4 而注释的**两个分支**

```php
// ★ 输入侧（甲方 ②"装饰不生效"的下一半）：客户端**送上来的**装饰条目有几项、几项非零。
//   若 `inputItems` 只有 1 项或 `inputNonZero=1` ⇒ 缺口在**客户端上传的配装**（我们没东西可发）；
//   若输入多项非零而 `recordNonZero=1` ⇒ 缺口在**我们这段拷贝/落槽**。
```

### 8.5 三层

```text
inputItems == 1 或 inputNonZero == 1   ⇒ 缺口在【客户端上传的配装】
输入多项非零 而 recordNonZero == 1      ⇒ 缺口在【我们的拷贝/落槽】
```

**⇒ 而实测 `inputItems=12 inputNonZero=7` 而 `recordNonZero=1/12`。**

**⇒ 正是第二个分支 ⇒ 缺口在**我们的拷贝/落槽**。**

**✓ 诊断精准定位了那个 `>=` bug。**

## 九、`slots` 字符串的**90 字符上限**

```php
if (slots.size() < 90)
{
    slots += std::to_string(i) + ":" + std::to_string(p.recordItemIds[i]) + " ";
}
```

**⇒ 所以最多列出到 90 字符。**

**⇒ 一个**有意的截断**（避免日志行过长）。**

## 十、`nonZero` 与 `slots` 的**两个计数**

```text
nonZero     统计所有非零项（不截断）
slots       只列到 90 字符（截断）
```

**⇒ 所以 `recordNonZero=7/12` 可能只列出前几项。**

**✓ 正确的分离。**

## 十一、`failSession` 与 `characterFailure` 的**双记录**

```php
failSession(CharacterPresentationFailed, -1, resolvedClassMask);
{
    const std::lock_guard lock(DedicatedControlMutex);
    DedicatedSessionConsumption.characterFailure(
        (uint32)resolveStatus.failure, resolveStatus.recordIndex, resolveStatus.itemId);
}
memberResolutionFailed = true;
break;
```

### 11.1 三项

```text
failSession(...)                    通用失败
DedicatedSessionConsumption.characterFailure(...)   【角色特定】的三字段
memberResolutionFailed = true
break
```

**⇒ 两层记录** —— 通用 stage + 角色的三字段细节。

**⇒ 与 §255 的三字段快照一致** ✓

### 11.2 而 `-1` 的 `failedClassIndex` 与 `resolvedClassMask`

**⇒ 角色失败传 `resolvedClassMask` 而其它传 `0`。**

**⇒ 因为角色失败时 classMask 可能已经部分解析。**

## 十二、关键结论

1. **占位符 `viewmodelIndex = 1` 与 `selectionIds[0] = 1`** —— 因为"清零不是错而是无效"。
2. **`selectionIds[0]` 有 7 位宽（1..128 合法）**。
3. **`characterItemIds[0]` 是"线字段之外"的关键值** —— 客户端从它推导另外十一项。
4. **`recordItemIds` 的 `static_assert` 与 §242 同一条错误消息** —— 同一不变式的第二处强制。
5. **`>=` 把真人判成人机** —— 真人 xuid ≈ 1.67e19 是 bot base 7.95e17 的 21 倍。
6. **7 项输入而 1 项输出的差分证据**精准定位了那个 bug。
7. **修复是区间判定 `[base, base + 4096)`**。
8. **`botXuidBase` 重复声明**（因为声明在文件后面）—— 小的技术债。
9. **两个覆盖漏斗的顺序**（先全局后 bot）。
10. **`BOTTRACE|human-presentation` 的三缺口分类** —— 而那个 `>=` bug 正是 (c)。
11. **`inputItems` / `inputNonZero` 与 `recordNonZero` 的对比**是定位的关键。
12. **"不是被人机复制顶掉的"** —— 撤掉拷贝后依然没有 ⇒ 排除法。
13. **`slots` 截断到 90 字符而 `nonZero` 不截断**。
14. **角色失败用双层记录**（通用 stage + 角色三字段）。

## 十三、未闭合点

- `cha_zombiehunter`（item 名）与 `fpa_tightjeans_red`（模型名）的关系。
- `selectionIds[0]` 的 7 位宽依据。
- `botXuidBase` 的重复声明是否已同步。
- `Appmain.cpp` 3020 行之后未读取。
