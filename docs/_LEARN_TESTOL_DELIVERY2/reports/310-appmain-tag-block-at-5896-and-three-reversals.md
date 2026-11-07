# 310 · **标签块在 `5896` 而不是 `12249`**、**62 个 demo 里只有 tag 28 有配置串**、三次推理反转

## 一、范围

本报告学习 `Appmain.cpp` 8737–8960 行。

## 二、**标签块的位置**（本组最重要的一段）

### 2.1 那段五重证据

```php
// The tag block is at 5896, not 12249 -- CG_SetupClientCharacterInfo
// 0x541800 resolves each attachment as `model + 2568` and `tag + 5896`, and
// 5896+28 is cs 5924 `tag_stowed_back`, which is the stowed weapon's tag.
// Five independent checks agree, including
// ServerMaterialConfigStringBase 4872 + 1024 == 5896 and 5896 + 64 ==
// WeaponConfigStringBase 5960, 64 being exactly what six bits address.
```

### 2.2 六层

```text
1. **标签块在 `5896`，不是 `12249`**
2. `CG_SetupClientCharacterInfo 0x541800` 把每个附件解析为 **`model + 2568`** 与 **`tag + 5896`**
3. ⇒ `5896 + 28 = 5924` 是 cs `tag_stowed_back` —— **收纳武器的标签**
4. ⇒ **五项独立检查一致**
5. ⇒ 包括 **`ServerMaterialConfigStringBase 4872 + 1024 == 5896`**
6. ⇒ 与 **`5896 + 64 == WeaponConfigStringBase 5960`**，**64 正是六位能寻址的**
```

### 2.3 **三个配置串带的首尾相接**

```text
4872  材质基址
+1024 ⇒ 5896   标签基址      （1024 = 材质带的大小）
+64   ⇒ 5960   武器基址      （64 = 6 位）
```

**✅ 一个**完美的算术链** —— 三个带连续排列。**

**⇒ 与 §262 的 `ServerMaterialConfigStringBase` 与 §259 的 `WeaponConfigStringBase 5960` **完全对上** ✓**

**⇒ 而 `4872` 是**第一次**给出材质基址的具体值。**

### 2.4 而 `64` 与六位

**⇒ 所以标签索引是**六位**（0..63）。**

**⇒ 与 §310 后面的"tags 13, 14, 21, 28, 30, 50, 51, 60, 62 和 63"**完全吻合** ✓**

**✅ 算术闭合。**

## 三、**62 个 demo 里只有 tag 28 有配置串**（本组第二重要）

```php
// MEASURED ACROSS ALL 62 RETAIL DEMOS: players carry attachment tags 13, 14,
// 21, 28, 30, 50, 51, 60, 62 and 63 in these very slots -- and ONLY index 28
// ever has a configstring set. C-2021-7-18[21-59-51]clash sets NONE of the
// tag block and still ships tags 50, 62 and 63. So the great majority of
// retail's attachment tags resolve to an UNSET configstring, i.e. to an
// EMPTY tag string, and the attachments render regardless.
```

### 3.1 五层

```text
1. **跨全部 62 个零售 demo 测量**
2. 玩家携带附件标签 **13、14、21、28、30、50、51、60、62、63** 在这些槽里
3. ⇒ 而**只有索引 28 有配置串被设置**
4. `C-2021-7-18[21-59-51]clash` **一个标签块的配置串都不设**而**仍然出货 tags 50、62、63**
5. ⇒ 所以**零售的绝大多数附件标签解析到一个未设置的配置串**，即**空标签串**
6. ⇒ **而附件仍然渲染**
```

### 3.2 十个标签值

```text
13, 14, 21, 28, 30, 50, 51, 60, 62, 63
```

**⇒ 十个，都在 0..63 内 ✓**

### 3.3 **"一个空标签是正常的而不是致命的"**

**⇒ 三层**：

```text
1. 空标签**是正常的**
2. 不是**致命的**
3. ⇒ 这与"索引 0 是一个找不到的查找而 DObj 构建对整个玩家失败"**相反**
```

**✅ 这是**第三次推理反转**（见下）。**

## 四、**三次推理反转**（本组核心）

### 4.1 第一版：发 tag index 0 ⇒ 玩家不渲染

```php
// So the model half is right and the TAG half is not. This sent tag index 0
// on the reasoning that a character piece merges onto the base skeleton by
// bone name, which is what this server does on its OWN DObj -- but that
// path writes a stable EMPTY STRING, whereas the client resolves a tag
// INDEX through configstrings this server never populates. Index 0 there is
// not "no tag", it is a lookup that finds nothing, and the DObj build fails
// for the whole player rather than for one attachment.
```

**⇒ 推理**："一个角色部件按骨骼名合并到基础骨架" ⇒ 所以发 tag index 0。**

**⇒ 而实测**："带着那些附件上线 ⇒ **玩家完全不渲染**"**

### 4.2 第二版：零售的线上反驳

```php
// AND THE REASONING ABOVE IS REFUTED BY RETAIL'S OWN WIRE. Section 181.
// ... (见 §3 的 62 demo 测量) ...
// An empty tag is therefore NORMAL, not fatal -- which is also what this
// server's own DObj has always done: it writes stable EMPTY strings into
// characterInfo's ten attachment tags and the models build. "Index 0 is a
// lookup that finds nothing and the DObj build fails for the whole player"
// was reasoning, never a measurement, and the wire disagrees with it.
```

**⇒ "『索引 0 是一个找不到的查找而 DObj 构建对整个玩家失败』是**推理，从未是测量**，而线上不同意它。"**

**⇒ 所以**默认开**（`OLMOD_OUTFIT_ATTACHMENTS` 默认开）。**

### 4.3 第三版：**通道认错了**

```php
// OFF AGAIN, AND THIS TIME BECAUSE THE CHANNEL IS KNOWN. Section 184i.
//
// These five model/tag pairs mount a model on one of the PLAYER's tags.
// The only attachment retail was ever observed publishing in 62 demos is
// `+0x018 = 172` with tag 28 = cs 5924 `tag_stowed_back` -- the STOWED
// WEAPON on the player's back. They are not the outfit channel and never
// were: an outfit piece is selected by BIT in netfields 21..32 and lands in
// one of twelve prefix-named slots (cha/fpa/boo/fja/han/hea/ves/heg/elp/
// knp/pat/eye), which is a different mechanism entirely.
//
// So section 182b's "a complete, resolvable, accepted model/tag pair
// rendered NOTHING" was never a defect in the pair -- it was an outfit model
// posted to the stowed-weapon channel, which correctly renders nothing.
// Leaving it on occupies a slot retail uses for the weapon on the player's
// back, and section 181f's "a tag meant for a sight blocks the ironsights"
// lives in exactly this area.
```

### 4.4 八层

```text
1. **又关掉了，而这次是因为【通道已知】**
2. 这五个 model/tag 对把模型挂在【玩家的】某个标签上
3. ⇒ 62 个 demo 里唯一观察到的附件是 **`+0x018 = 172` with tag 28 = cs 5924 `tag_stowed_back`**
4. ⇒ = **玩家背上的收纳武器**
5. ⇒ **它们不是服装通道**，从来不是：一个服装件由 **netfields 21..32 的【位】** 选中
6. ⇒ 并落在**十二个前缀命名的槽**之一（`cha/fpa/boo/fja/han/hea/ves/heg/elp/knp/pat/eye`）
7. ⇒ **那是一个完全不同的机制**
8. ⇒ 所以 §182b 的"一个完整、可解析、被接受的 model/tag 对渲染了**什么都没有**"从不是**那一对**的缺陷
9. ⇒ 而是**一个服装模型被投到收纳武器通道**，那**正确地什么也不渲染**
```

### 4.5 **十二个前缀槽**（本组第三重要）

```text
cha / fpa / boo / fja / han / hea / ves / heg / elp / knp / pat / eye
```

**⇒ 十二个！而 §300 的 `isCharacter` 只查了**八个**（`fpa_`/`cha_`/`boo_`/`fja_`/`han_`/`hea_`/`ves_`/`heg_`）。**

**⚠ 所以 §300 漏了 `elp_`/`knp_`/`pat_`/`eye_` 四个。**

**⇒ 而那四个可能是**饰品/小物**（`elp` = elbow pads? `knp` = knee pads? `pat` = patches? `eye` = eyes）。**

**✅ 与 §242 的"十二个槽"**完全一致** ✓ —— 而那 12 正是 `optionMask[12]` 的 12。**

**✅ 三层算术闭合：`netfields 21..32` = 12 = `optionMask[12]` = 12 个前缀槽。`

### 4.6 而"§181f 的『一个给瞄准镜的标签挡住了机瞄』就在这个区域"

**⇒ 三层**：

```text
1. 让它开着会**占用一个零售用于"玩家背上的武器"的槽**
2. ⇒ 而 §181f 的"一个给瞄准镜的标签挡住了机瞄"
3. ⇒ **就在这个区域**
```

**✅ 与记忆里"开镜失效未归因：候选之一是字段20 `pm_flags=aiming?0x10:0`"**——而这里是**第二个候选**。**

**⇒ 所以"开镜失效"可能有两个原因。**

## 五、`OLMOD_OUTFIT_ATTACHMENTS` 的**默认关**

```cpp
static const bool OutfitAttachmentsEnabled = [] {
    const auto *const value = std::getenv("OLMOD_OUTFIT_ATTACHMENTS");
    return value && *value == '1';
}();
if (!OutfitAttachmentsEnabled)
    return customization;
```

### 5.1 而 `value && *value == '1'` 是**严格首字符**

**⇒ 所以 `"10"` 也开。**

**⚠ 第十五种解析。**

### 5.2 而**默认关**是因为通道认错

**⇒ 与 §308 的 `OLMOD_VIEWHANDS_TF141` **默认开**相反。**

**⚠ 两个相邻的开关默认相反** —— 因为一个是**必需的覆盖**（否则崩），一个是**错误的通道**（否则不渲染）。**

**✅ 语义正确但容易混淆。**

## 六、`outfit attachments` 报告的**七个量**

```php
"outfit attachments xuid=" + xuid + " character=" + characterItemId +
" extras=" + extras.size() +
" resident=" + (空 ? " none" : list) +
" NOT IN BAND=" + (空 ? " none" : list)
```

**⇒ 五个字段（`resident` 与 `NOT IN BAND` 各是一个列表）。**

### 6.1 而"**resident** 与 **NOT IN BAND**"

**⇒ 与 §299 的"`character body published INTO THE GAMESTATE` / `-- NO BAND SLOT`"同族。**

**✅ 三分：已存在 / 注册成功 / 注册失败。**

### 6.2 而"**地图自己的带先；它不花任何东西且不需要广播**"

```php
// The map's own band first; it costs nothing and needs no broadcast.
// Only a name the map never published gets a slot.
auto index = Bindings.resolveModelConfigStringIndex(name);
if (!index)
    index = Server.registerOutfitModelConfigString(name);
```

**⇒ 与 §299/§309 的**同一条两步**（第五次）。**

## 七、**六个 runner 的注入**

```cpp
Server.setSharedPmoveRunner(...)                    // 1
Server.setWeaponMovementRunner(...)                 // 2
Server.setPlayerStateToEntityStateConverter(...)    // 3
Server.setDeathAnimationRunner(...)                 // 4
Server.setSpawnAnimationRunner(...)                 // 5
Server.setZmBoardTrajectoryEvaluator(...)           // 6
Server.setPointTraceRunner(...)                     // 7
Server.setRadiusDamageVisibilityRunner(...)         // 8
Server.setCapsuleTraceRunner(...)                   // 9
```

**⇒ 九个。**

### 7.1 而 `setZmBoardTrajectoryEvaluator` 的**中文注释**

```php
// OLMOD(multiplayer_offhand_projectile): 这个求值器是**通用**的
// (EngineBindings::evaluateTrajectory 走保留的 0x410BD0 plain trajectory
// evaluator)，不是 zm 专属。它原先只装在 `if (request->gameType == "zm")`
// 块里 ⇒ MP 的投掷物（手雷/闪光/烟雾）没有求值器可用，步进器会在第一帧
// 就把它们退役。这里与其它 runner 一起无条件安装（见 sv_offhand_kind_mp.hpp）。
```

### 7.2 四层

```text
1. 这个求值器是**通用的**（走保留的 `0x410BD0` plain trajectory evaluator）
2. **不是 zm 专属**
3. ⇒ 它原先只装在 `if (gameType == "zm")` 块里
4. ⇒ **MP 的投掷物没有求值器可用 ⇒ 步进器会在第一帧就把它们退役**
5. ⇒ 所以现在与其它 runner 一起**无条件安装**
```

**✅ 与 §298 的"`Ammo` 跳过而 `ammoWeight=15`"配合 —— MP 投掷物与 zm 共用。**

### 7.3 而 `0x410BD0` 是一个**具体的原生函数**

**⇒ 与 §254 的"`sub_5E3760` 的 `__usercall`"同族（具体地址）。**

## 八、`setSharedPmoveRunner` 的**六项前置**

```cpp
Server.setSharedPmoveRunner([](nativePlayerState, commandState, resolvedLoadout, glassState,
    collisionEntities, output) {
    if (!resolvedLoadout) return false;                    // ① 无武器 ⇒ 失败
    SvNativePmoveFailure failure{};
    const auto result = Bindings.runServerPmove(
        nativePlayerState,
        commandState.currentUserCmd,
        commandState.oldUserCmd,
        PlayerCollisionContentMask,
        true,                                              // ② 【一个 bool】
        glassState,
        collisionEntities,
        &failure);
    if (!result) { output.failure = failure; return false; }
    output = *result;
    return true;
});
```

### 8.1 五项 + 一个 `true`

**⇒ 而 `true` 的语义未知**（待读 `runServerPmove` 的签名）。

**⇒ 可能是"allow bhop"或"is server"之类。**

## 九、关键结论

1. **标签块在 `5896`**，`model + 2568` / `tag + 5896`。
2. **三个带首尾相接**：`4872 + 1024 = 5896`，`5896 + 64 = 5960`。
3. **`4872` 是材质基址的首次具体值**。
4. **`64` = 六位** ⇒ 标签索引 0..63。
5. **62 个 demo 里十个标签值（13/14/21/28/30/50/51/60/62/63）只有 28 有配置串**。
6. **"一个空标签是正常的而不是致命的"** —— 零售的绝大多数附件标签解析到空串。
7. **三次推理反转**：发 tag 0 → 零售线上反驳 → 通道认错了。
8. **"§182b 的『一对完整可解析的 model/tag 渲染了什么都没有』从不是那一对的缺陷"** —— 而是**投错了通道**。
9. **12 个前缀槽**（`cha/fpa/boo/fja/han/hea/ves/heg/elp/knp/pat/eye`）—— 而 §300 只查了 8 个，**漏了 `elp_`/`knp_`/`pat_`/`eye_`**。
10. **`netfields 21..32` = 12 = `optionMask[12]` = 12 个前缀槽** —— 三层算术闭合。
11. **§181f 的"给瞄准镜的标签挡住机瞄"就在这个区域** —— 开镜失效的**第二个候选**原因。
12. **`OLMOD_OUTFIT_ATTACHMENTS` 默认关**（与 `OLMOD_VIEWHANDS_TF141` 默认开**相反**）。
13. **`outfit attachments` 报告的三分**（已存在 / 注册成功 / 注册失败）。
14. **九个 runner 注入**，其中 `setZmBoardTrajectoryEvaluator` 是**通用的而不是 zm 专属**。
15. **"MP 的投掷物没有求值器可用 ⇒ 步进器在第一帧就把它们退役"** —— 一个已修的 gap。

## 十、未闭合点

- `elp_`/`knp_`/`pat_`/`eye_` 四个前缀的语义。
- `runServerPmove` 第五个参数 `true` 的语义。
- `0x410BD0` trajectory evaluator 的完整契约。
- `Appmain.cpp` 8960 行之后未读取。
