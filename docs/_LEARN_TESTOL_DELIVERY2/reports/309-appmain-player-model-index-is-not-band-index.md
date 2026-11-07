# 309 · **"玩家模型索引不是模型配置串索引"** —— 隐形玩家的四个环节、`6/7/8` 的四值命名空间

## 一、范围

本报告学习 `Appmain.cpp` 8518–8740 行。

## 二、**"玩家模型索引不是模型配置串索引"**（本组最重要的一段）

### 2.1 那段完整的纠正

```php
// THE PLAYER MODEL INDEX IS NOT A MODEL CONFIGSTRING INDEX. Section 166.
//
// This block used to resolve the player's own body name to a MODEL BAND
// INDEX and write it into customization.modelIndex, on the reasoning that a
// model index must address the map's model band the way the viewhands index
// above does. IT DOES NOT, and the override was the invisible player:
```

### 2.2 五层

```text
1. **玩家模型索引【不是】模型配置串索引**
2. 这段过去把玩家自己的身体名解析成一个**模型带索引**并写进 `customization.modelIndex`
3. ⇒ 理由是"一个模型索引必须像上面的 viewhands 索引那样寻址地图的模型带"
4. ⇒ **它【不】是，而那个覆盖就是隐形玩家**
5. ⇒ 所以那是一个**看起来同构但实际不同的两个字段**
```

### 2.3 **四个环节**（本组核心）

#### ① 线字段是**四位**而带索引是**数百**

```php
//   * the wire field is FOUR BITS (clientState index 17, +0x150), and
//     validCharacterCustomization refuses anything outside 1..0xF. A band
//     index is in the hundreds -- resolveModelConfigStringIndex returns 139
//     for the viewhands right above -- so the customization this produced
//     was INVALID.
```

```text
线字段  四位（clientState index 17，+0x150）
合法    1..0xF（1..15）
而带索引 数百（viewhands 是 139）
⇒ 所以产出的 customization 是【无效的】
```

**⇒ 与 §283 的"`selectionIds[0]` 有 7 位宽（1..128 合法）"**不同位宽**。**

**⇒ 所以四个字段四种位宽：**

```text
modelIndex（+0x150）    4 位
selectionIds[0]         7 位
viewmodelIndex          10 位（0x3FF）
```

**✅ 三个不同位宽。**

#### ② 无效的 customization **从不被推进 snapshot** ⇒ **REMOVE 位**

```php
//   * an invalid customization is never pushed into snapshot clientInfos,
//     and writeClientInfos then emits the REMOVE bit for a client that was
//     in the observer's baseline. The observer CLEARS that clientInfo.
```

```text
1. 无效的 customization【从不】被推进 snapshot 的 clientInfos
2. ⇒ `writeClientInfos` 然后对一个【在观察者基线里】的客户端发出 **REMOVE 位**
3. ⇒ 观察者**清空**那个 clientInfo
```

**⚠ 这是"一个无效值触发一个删除"的**放大**。**

**⇒ 与 §155 的"`writeClientInfos` 的批量提交"相关。**

#### ③ `+0x150 <= 0` 的**早期返回** ⇒ 一个名字都不写

```php
//   * CG_SetupClientCharacterInfo 0x00541800 opens with
//     `if (*(int *)(clientState + 0x150) <= 0) return;` and writes NO model
//     names at all, so characterInfo+0x18 stays EMPTY and
//     BG_UpdatePlayerDObj refuses to draw the LIVING player while letting
//     the CORPSE through -- the flash on death, with a fallback body, which
//     is where "a COMPLETELY DIFFERENT MODEL" came from in the first place.
```

```text
1. `0x00541800` 开头是 `if (*(int *)(clientState + 0x150) <= 0) return;`
2. ⇒ **一个模型名都不写**
3. ⇒ `characterInfo +0x18` 保持**空**
4. ⇒ `BG_UpdatePlayerDObj` **拒绝画活着的玩家**而**让尸体通过**
5. ⇒ **死亡时的一闪 + 一个回退身体**
6. ⇒ **这就是"一个完全不同的模型"的来源**
```

**✅ 与 §255 的 `EMPTY` 与 §304 的"两个来源一个沉默"**完全对上** ✓**

**⇒ 所以"死亡时闪出一个不同的模型"= 活着不画（`+0x18` 空）+ 尸体画（走另一条路）。**

#### ④ **粘性且每玩家** ⇒ 一个可见一个不可见

```php
//   * and it was STICKY AND PER-PLAYER: the cache latched per character, and
//     a body name the map's band does not publish left the override unset,
//     so that player stayed visible. One visible, one invisible, flipping
//     run to run with what happened to be in the band.
```

```text
1. **粘性且每玩家**：缓存按角色闩锁
2. 而一个地图的带不发布的身体名 ⇒ 让覆盖**未设置**
3. ⇒ 那个玩家**保持可见**
4. ⇒ **一个可见，一个不可见，逐运行翻转，取决于带里恰好有什么**
```

**✅ 一个"部分成功"的典型症状。**

## 三、**那个字段实际做什么**（本组第二重要）

```php
// What the field actually does, read off 0x00541800 and 0x0080E600: the
// request's +0 word is NEVER READ by the resolver. Its only job is that
// `> 0` gate. The BODY comes from characterItemId (+0x7C) through the
// character definition table, and the retail corpus agrees the field only
// ever carries 0, 6, 7 or 8 -- a four-value namespace, not a band index.
//
// So the bootstrap 6 is not a placeholder to be improved: it is a legal
// value of the field, and the character is chosen elsewhere. Removing this
// also takes the 1024-configstring scan back out of the per-frame provider.
// TODO(CODOL): derive 6/7/8 per character once the selector is found; it is
// cosmetic against the character id, not the thing that makes a body render.
```

### 3.1 六层

```text
1. 从 `0x00541800` 与 `0x0080E600` 读出：**请求的 `+0` 字从不被解析器读**
2. ⇒ 它唯一的工作是那个 **`> 0` 门**
3. ⇒ **身体来自 `characterItemId`（`+0x7C`）** 通过角色定义表
4. ⇒ 而**零售 corpus 同意**那个字段**只承载 0、6、7 或 8**
5. ⇒ **一个四值命名空间，不是一个带索引**
6. ⇒ 所以 bootstrap **6 不是一个待改进的占位符**：**它是那个字段的一个合法值**
```

### 3.2 **四值命名空间：`{0, 6, 7, 8}`**

**⇒ 所以 `modelIndex` 只有四个可能值。**

**⚠ 而"6 是 bootstrap"** —— 所以我们的默认是 6。**

**⇒ 与 §283 的"`viewmodelIndex = 1`"**不同的字段不同的默认**。**

### 3.3 而"**移除这个也把 1024 配置串扫描从每帧 provider 里拿掉**"

**⇒ 三层**：

```text
1. 移除"把身体名解析成带索引并写进 modelIndex"
2. ⇒ 也把那个 1024 扫描拿出去
3. ⇒ 因为 provider 每帧每客户端跑
```

**✅ 与本文件反复的"每帧昂贵操作"同族**（第六次）。

### 3.4 而 `TODO` 的**精确边界**

```text
"derive 6/7/8 per character once the selector is found; it is cosmetic
 against the character id, not the thing that makes a body render."
```

**⇒ 三层**：

```text
1. 等选择器找到后按角色推导 6/7/8
2. ⇒ 它**相对角色 id 是装饰性的**
3. ⇒ **不是让身体渲染的那件事**
```

**✅ 与 §307 的"本刀只做授予面"同族**（第九次"明确边界"）。

## 四、**身体模型的第三个缓存**（本组第三重要）

```php
// THE BODY, AS A MODEL-BAND INDEX, so a player renders even when the
// character system does not resolve. Section 168: 0x00541800 returns 0 and
// its caller runs the fallback 0x00541BD0, which takes the base model name
// from clientState +0x14 + 2568. We have never sent that field, so a client
// that lost the character path had an EMPTY model name and drew nothing --
// the invisible player, measured in both clients' own memory.
//
// Same two-step the outfit models use: the map's own band first, and only a
// name the map never published gets a slot broadcast into it.
//
// CACHE THE MISS TOO, AND PER CHARACTER.
struct BodyModelCacheEntry
{
    std::uint16_t characterItemId{};
    std::uint16_t index{};
    bool asked{};
};
static std::map<uint64, BodyModelCacheEntry> BodyModelCache;
auto &bodyCache = BodyModelCache[xuid];
if (!bodyCache.asked || bodyCache.characterItemId != customization->characterItemId)
{
    ...
}
customization->bodyModelConfigStringIndex = bodyCache.index;
```

### 4.1 五项

```text
1. **身体作为一个【模型带索引】**
2. ⇒ 所以即使角色系统不解析，玩家也渲染
3. `0x00541800` 返回 0 ⇒ 其调用者跑回退 `0x00541BD0`
4. ⇒ 而**它从 `clientState +0x14` + **2568** 取基础模型名**
5. ⇒ **我们从没发过那个字段** ⇒ 所以一个丢失角色路径的客户端**有一个空模型名且什么也不画**
```

### 4.2 **`clientState +0x14 + 2568`**

**⇒ 与 §301 的 `ModelConfigStringBase = 2568`**完全一致** ✓**

**⇒ 而 `clientState +0x14` 是**一个索引**而 `+2568` 是**基址**。**

**✅ 第五次确认 2568。**

### 4.3 而"**在两个客户端自己的内存里测量过**"

**⇒ 三层**：

```text
1. 隐形玩家在**两个客户端自己的内存**里被测到
2. ⇒ 不是"服务器认为"
3. ⇒ 是**客户端内部状态**
```

**✅ 与 §255 的"读客户端的 `characterInfo`"配合。**

### 4.4 而 `bodyCache` 的**三项**

```text
characterItemId    键
index              索引（0 = 无）
asked              【是否问过】
```

**⚠ 而这里是 `asked` 而不是 `resolved`。**

**⇒ 与 §308 的 `ViewhandsCacheEntry` 用 `resolved` **不同命名**。**

**⚠ 同构但不同名。**

### 4.5 而"**问角色解析器，不是 DObj**"

```php
// ASK THE CHARACTER RESOLVER, NOT THE DObj. characterModelNames reads
// what the DObj build cached, and that arrives a frame or more after the
// first customization exists -- so the first clientInfo writes went out
// with a ZERO body index, and an observer that then never received the
// 0 -> 418 change was left with an EMPTY model name for that slot.
// Measured: one client held slot 0 at `model=fpa_goose_ss_m_15` and slot
// 1 at `model=EMPTY rebuild=1` in the same line. The resolver answers
// from the character record on the FIRST frame, so the field is right in
// the very first write and never has to change.
```

### 4.6 六层

```text
1. **问角色解析器，不是 DObj**
2. `characterModelNames` 读 **DObj 构建缓存的东西**
3. ⇒ 而那个**比第一次 customization 存在晚一帧或更多**
4. ⇒ 所以**第一次 clientInfo 写出去时 body index 是零**
5. ⇒ 而一个**从未收到 0 → 418 变化**的观察者**留下了空模型名**
6. **实测**：一个客户端在**同一行**里槽 0 是 `model=fpa_goose_ss_m_15` 而槽 1 是 `model=EMPTY rebuild=1`
```

### 4.7 **"0 → 418"** 与 §300 的 `body418`

**§300**："线上对两个观察者的每次写都携带 `body418`"

**⇒ 所以 418 是**那个身体模型的带索引**。**

**✅ 跨报告闭环 —— §300 的 `body418` 就是这里的 `bodyCache.index`。**

### 4.8 而"**解析器从第一帧就从角色记录回答**"

**⇒ 三层**：

```text
1. 解析器从角色记录回答 ⇒ **第一帧就有答案**
2. ⇒ 所以那个字段**在第一次写就对**
3. ⇒ 而**永不需要变化**
```

**✅ 与 §300 的"没有 live 投递可错过"**完全同一设计原则** ✓**

## 五、**战栗语音性别来自模型名**（本组第四重要）

```php
// THE BATTLECHATTER VOICE'S GENDER, from the one place it
// is actually stated. customization->female comes from the
// character definition and was measured false for a female
// character in a live match; the body model name says
// `..._sc_f` / `..._tf_m` and is right for 452 of the 456
// body models in the shipped zones. Pushed rather than
// stored on the customization because that struct is
// embedded in an address-keyed buffer whose size is pinned.
if (const auto female = SV_BattleChatterFemaleFromModelName(body))
{
    Server.setBattleChatterVoiceFemale(clientNum, *female);
}
```

### 5.1 六层

```text
1. **战栗语音的性别来自唯一真正声明它的地方**
2. `customization->female` 来自**角色定义**而**在一个活比赛里对一个女性角色实测为 false**
3. 而**身体模型名说 `..._sc_f` / `..._tf_m`** 而**对 456 个随包身体模型里的 452 个是对的**
4. ⇒ **推**而不是**存在 customization 上**
5. ⇒ 因为那个结构**嵌在一个地址键控的缓冲区里而其大小被钉死**
6. ⇒ 所以又一处"不能动那个结构"
```

### 5.2 而"**452 / 456**"

**⇒ 所以模型名判定有 99.1% 的准确率。**

**⚠ 4 个例外。**

**✅ 与 §152 的"`f1` 是**女声 1**不是前缀（男性角色得到女声）"**完全同族**（第十次"性别来源不可靠"）。**

**⇒ 而这里是**第二个**性别来源 —— 比角色定义更可靠。**

### 5.3 而"**大小被钉死**"是第三次

```text
§184h  48 字节破坏死亡动画
§180   复制地址键控的缓冲区让指针失效
§309   customization 嵌在地址键控缓冲区里，大小被钉死
```

**✅ 三次同类约束。**

## 六、`SV_ResolveCharacterCustomization` 的**七个参数**

```cpp
auto customization = SV_ResolveCharacterCustomization(
    presentation->selectionIds,      // 11 个
    presentation->female,            // bool
    presentation->color,             // 
    viewmodelIndex,                  // 【我们算出的】
    faction,                          // 阵营
    presentation->characterItemId,   // 角色物品
    presentation->recordItemIds);    // 12 个
```

**⇒ 七项。**

### 6.1 而 `viewmodelIndex` 是**我们算的**（§308 的手部解析）

**⇒ 其余六项来自 `presentation` + `faction`。**

## 七、`OutfitCacheEntry` 的**五个字段**

```php
struct OutfitCacheEntry
{
    std::uint16_t characterItemId{};
    std::array<std::uint16_t, 12> recordItemIds{};
    std::array<std::uint16_t, 4> attachments{};
    std::array<std::uint32_t, 12> optionMask{};
    bool resolved{};
};
```

### 7.1 四项 + 一个标志

```text
characterItemId     键 1
recordItemIds[12]   键 2（12 个 uint16 = 24 字节）
attachments[4]      值 1
optionMask[12]      值 2（12 个 uint32 = 48 字节）  ← 【那个 48 字节！】
resolved            标志
```

### 7.2 **`optionMask[12]` 正是那 48 字节**

**⇒ 而 §308 说"48 字节在 `SvCharacterCustomization` 上破坏死亡动画"。**

**⇒ 所以那个掩码现在**放在这个缓存里**而不是那个结构里。**

**✅ 这就是 §308 的"掩码在定制化**旁边**走"的实现。**

### 7.3 而缓存的**两个键**

```text
characterItemId
recordItemIds    （12 项的数组相等）
```

**⇒ 所以**装备变了**（`recordItemIds` 变）⇒ 缓存失效。**

**✓ 正确的失效条件。**

## 八、**"每装备一次，不是每帧一次"**

```php
// ONCE PER OUTFIT, NOT ONCE PER FRAME. THIS PROVIDER IS CALLED FROM
// ServerCore::runFrame FOR EVERY ACTIVE CLIENT, so anything expensive here
// runs at the tick rate times the player count. characterOutfitAttachmentModels
// resolves the character record TWICE through the native engine, and doing
// that per frame cost a measured match its framerate AND left both players
// unrendered -- the same lesson as never hooking a per-frame client function,
// on the server side.
```

### 8.1 五层

```text
1. **每装备一次，不是每帧一次**
2. 这个 provider 从 `ServerCore::runFrame` 对**每一个活跃客户端**调用
3. ⇒ 所以这里任何昂贵的东西都以 **tick 率 × 玩家数** 跑
4. `characterOutfitAttachmentModels` **通过原生引擎把角色记录解析两次**
5. ⇒ 每帧做那个**让一场实测比赛丢掉它的帧率**，**而且让两个玩家都不渲染**
6. ⇒ **与"绝不钩一个每帧客户端函数"同一个教训，在服务端**
```

### 8.2 **"让两个玩家都不渲染"**

**⇒ 三层**：

```text
1. 每帧两次原生解析
2. ⇒ 帧率丢失
3. ⇒ **而且两个玩家都不渲染**
```

**⚠ 后者是**功能性后果**而不只是性能。**

**✅ 与 §309 开头的"隐形玩家"**同一个症状**。**

## 九、**`sub_80E600` 的掩码语义**

```php
// THE OUTFIT AS THE CLIENT READS IT: a selection mask, not a list of ids.
//
// Section 184. sub_80E600 -- the function CG_SetupClientCharacterInfo hands
// netfields 21..32 to -- tests bit i of this block against option i of the
// character definition's own list and renders optionList[i]. Sending the
// item ids there (section 182) set whatever bits those ids spell, which is
// precisely why pieces finally rendered and were the wrong ones.
```

### 9.1 四层

```text
1. **服装按客户端读它的方式：一个选择掩码，不是一个 id 列表**
2. `sub_80E600` —— `CG_SetupClientCharacterInfo` 把 netfields **21..32** 交给它
3. ⇒ 它把这一块的**位 i** 对着**角色定义自己的列表的选项 i** 测试并渲染 `optionList[i]`
4. ⇒ **把物品 id 发到那里（§182）设了那些 id 拼出的任何位**
5. ⇒ **这正是为什么部件终于渲染了而且是错的**
```

### 9.2 **"把物品 id 当位图"** 与 §242 的"把 id 当下标"

**§242**："把原始物品 id 当掩码发过去 ⇒ 客户端画出了与 loadout 无关的部件"

**⇒ 这里是同一个 bug 的**另一处记录**。**

**✅ 跨报告确认 —— 同一个 `sub_80E600`。**

### 9.3 而 **netfields 21..32 = 12 个**

**⇒ 与 `optionMask[12]` 的 12 **完全一致** ✓**

**⇒ 所以那 48 字节 = 12 × 4 = 12 个 netfield。**

**✅ 算术闭合。**

### 9.4 而"**它对每进程没有任何键**"

```php
// IT IS KEYED ON NOTHING PER-PROCESS, which is the property section 182e
// proved was required: the character item id is already on the wire as
// field 20, both sides reach the same per-character table through it, and
// no decode key is involved anywhere.
```

**⇒ 三层**：

```text
1. 它对**每进程没有任何键**
2. §182e 证明那是必需的：角色物品 id **已经在线路上作为 field 20**
3. ⇒ 双方**通过它到达同一个每角色表**，而**任何地方都不涉及解码键**
```

**✅ 与 §255 的"`decodeKey` 是全局还是每 profile"配合 —— 而这里**不需要**解码键。**

## 十、关键结论

1. **"玩家模型索引不是模型配置串索引"** —— 一个**看起来同构但实际不同**的两个字段。
2. **四个环节**：四位线字段 vs 数百带索引、无效 ⇒ REMOVE 位、`+0x150 <= 0` 早期返回 ⇒ `+0x18` 空 ⇒ 活人不画、粘性且每玩家 ⇒ 一个可见一个不可见。
3. **"死亡时的一闪 + 一个回退身体" = 活人不画（`+0x18` 空）+ 尸体画。**
4. **`modelIndex` 只有四值：`{0, 6, 7, 8}`** —— 一个**命名空间**而不是带索引。
5. **bootstrap 6 是合法值而不是待改进的占位符。**
6. **三个字段三种位宽**（`modelIndex` 4 位 / `selectionIds[0]` 7 位 / `viewmodelIndex` 10 位）。
7. **`clientState +0x14 + 2568`** 是回退身体名的路径 —— 第五次确认 2568。
8. **"在两个客户端自己的内存里测量过"** —— 不是服务器认为。
9. **`bodyCache` 用 `asked` 而 `ViewhandsCacheEntry` 用 `resolved`** —— 同构不同名。
10. **"问角色解析器而不是 DObj"** —— 因为 DObj 晚一帧 ⇒ 第一次写成 0。
11. **"同一行里槽 0 是 `fpa_goose_ss_m_15` 而槽 1 是 `EMPTY rebuild=1`"** —— 一个精确的不一致。
12. **"0 → 418"** 与 §300 的 `body418` **闭环**。
13. **"解析器从第一帧就回答 ⇒ 那个字段永不需要变化"** —— 与 §300 同一原则。
14. **战栗语音性别来自模型名（452/456 正确）**，因为 `customization->female` 实测错。
15. **"大小被钉死"第三次**（§184h / §180 / §309）。
16. **`optionMask[12]` 正是那 48 字节** —— 现在放在缓存里而不是结构里。
17. **"每装备一次不是每帧一次"** —— 每帧两次原生解析**让两个玩家都不渲染**。
18. **`sub_80E600` 的 netfields 21..32 = 12 个** ⇒ 与 `optionMask[12]` **算术闭合**。
19. **"把物品 id 当位图"** 与 §242 的"把 id 当下标"是同一个 `sub_80E600`。
20. **"它对每进程没有任何键"** ⇒ 不需要解码键。

## 十一、未闭合点

- `6/7/8` 三个值的具体语义。
- `452/456` 的 4 个例外是哪些。
- `faction` 参数的语义。
- `Appmain.cpp` 8740 行之后未读取。
