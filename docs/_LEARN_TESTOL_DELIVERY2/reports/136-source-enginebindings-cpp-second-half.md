# 学习报告 136（重开）— `EngineBindings.cpp` 后半（11,601–17,867 / 17,867 行）：**全文收官**

**学习范围**：`EngineBindings.cpp` 第 **11,601–17,867 行**（**917,344 B / 17,867 行全文完成**）
**性质**：全实测（**逐行读完**）
**★★★★★ 本报告收录十四个重大发现**：①**`weapon registry` 重建的完整七步与五个故障阶段** ②**Alpha 武器的 XAssetEntry 池 `120000 × 28`** ③**Barrett 资产闭包的 15 秒流式等待** ④**21 个 XAnim 槽的完整表** ⑤**`0x10`/`0x18` 与 `0x14`/`0x54` 的模型数组** ⑥**`resolveWeaponItem` 的 12 步完整链** ⑦**`attachmentIdForWeapon` 的模型索引翻译** ⑧**`0x3FFD` / `0x3FFF` 两个上界** ⑨**`resolveSessionPerks` 的 96 位与 192 位** ⑩**`publicProfileReady` 的四重校验** ⑪**`reportClientCharacterInfo` 的九个字段** ⑫**`resolveGlassMapMetadata` 的三条关系** ⑬**三个 trace ABI 的完整对照表** ⑭**`SV_Trace` 在本 build 上不存在**

---

## 一、★★★★★ **`weapon registry` 重建的完整七步**

### 1.1 ★★★★★ 完整实现（第 11387–11575 行）

```cpp
__try
{
    // ① 仅在 count == 0 时 reset
    if (registryWord(WeaponRegistryCountRva) == 0) {
        *registryMode = **2**;
        weaponRegistryReset_();
    }
    // ② 两遍 walk（pass 0 跳过 '*' / pass 1 只要 '*'）
    for (pass = 0; pass < 2; ++pass) {
        skipModular = (pass == 0);
        for (index = 1; index < **0x6A4**; ++index) {
            name = nativeConfigString(**0x1748** + index);
            if (skipModular ? *name == '*' : *name != '*') continue;
            tryWeaponResolve(weaponResolver_, name, resolvedIndex, fault);
            if (resolvedIndex != index) { /* 记不匹配,前 6 个 */ }
        }
        if (pass == 0) {
            // ③ 两遍之间的三步
            defaultWeapon = weaponResolver_("**defaultweapon_mp**", nullptr);
            weaponRegistryInitialize_(**1**);
            if (weaponKnifeStatsLoad_) weaponKnifeStatsLoad_();
        }
    }
    // ④ 验证
    tryWeaponLookup(weaponLookup_, "defaultweapon_mp", verifyLookup, fault);
    initialized = initialized && defaultWeapon != 0 && verifyLookup == defaultWeapon;
}
__except (captureNativeFault(GetExceptionInformation(), fault)) { ... }
```

### ★★★★★ **五个阶段的编码与故障专用码**

| `stage` | 含义 |
|---|---|
| **1** | `reset` |
| **2** | configstring walk |
| **3** | default resolve |
| **4** | `initialize(1)` |
| **5** | verify |

```
故障专用：**`20 + pass`**（20/21）/ **`51`**（verify 的 lookup）/ **`90 + stage`**（`__except` 兜底）
```

### ★★★★★ **失败时的七行日志**（第 11576–11691 行）

```
① `weapon registry rebuild failed stage=%u fault=%u index=%u resolved=%u name=%s default=%u count=%u walked=%u named=%u faults=%u exception=0x%08X`
② `weapon registry first names [idx:name] ...`（前 6 个）
③ `weapon registry globals count=%u next=0x%08X`
④ `before reset count=%u cache=%u counter=%u initialized=%u`
⑤ `after reset count=%u cache=%u counter=%u attachModels=%u map0=%u`
⑥ `weapon registry fault at rva=0x%07X op=%u target=0x%08X code=0x%08X`
⑦ `weapon registry com_error depth=%u level=%u text=%.240s`
⑧ `weapon registry mismatches=%u [idx->resolved:name] ...`（前 6 个）
```

★★★ **⇒ **八行日志**,其中第 ⑦ 行读 `Com_Error` 的三个全局（`0x31053DC` / `0x2FE7904` / `0x2FE7958`）。**
**⇒ 第 ⑥ 行的判据（第 11636–11639 行逐字）：**
```
"**WHERE it faulted, as an RVA that pastes straight into IDA, and WHAT it touched.
 `0x02F060` reading address 0 is a **null WeaponDef string**; anything inside `0x0F82E0`
 is **Com_Error, which means the engine RAISED this rather than tripping over it**.**"
```

### ★★★ **`0x1588634` 的第三个数**（第 11346 / 11426 / 11620 行）

```cpp
registryWord(**0x1588634u**)
```
★★★ **⇒ 在 `PerWeaponAttachmentCountsRva = 0x1588638` 之前 4 字节 ⇒ 一个独立的计数器。**

### ★★★★★ **`Com_Error` 深度语义**（第 11653–11656 行，逐字）

```
"**Com_Error's own state. `sub_4F82E0` bumps the depth, keeps the level, formats the
 message, and THEN longjmps** -- so **a non-zero depth here says the engine reported a
 real error and the text is its own words, not our guess about them**."
```

### ★★★ **`0x1588634` 的 `map0`**（第 11430–11431 行）

```cpp
*(module_ + PerWeaponAttachmentCountsRva)   // ★ map0 = 第 0 个武器的附件计数
```
★★★ **⇒ `map0` = `PerWeaponAttachmentCountsRva` 的第 0 个字节（**武器 0** 的附件计数）。**

---

## 二、★★★★★ **Alpha 武器的 XAssetEntry 池 `120000 × 28`**

### 2.1 ★★★★★ 五个常量（第 11817–11822 行）

```cpp
constexpr std::uint32_t WeaponAssetType      = **28**;
constexpr std::uint32_t StringTableAssetType = **37**;
constexpr std::size_t XAssetEntryPoolRva     = **0x1F9B120**;
constexpr std::size_t XAssetEntryCount       = **120000**;
constexpr std::size_t XAssetEntrySize        = **28**;
constexpr std::size_t XAssetEntryTypeOffset  = **0**;
constexpr std::size_t XAssetEntryDataOffset  = **8**;
constexpr std::size_t XAssetEntryZoneOffset  = **16**;
```

★★★★★ **⇒ 完整结构：**
```
池 @ **`0x1F9B120`**（VA `0x0239B120`）
**120,000 条 × 28 字节** = **3,360,000 字节**（3.2 MB）
        ↓
`+0`  = **type**（`u32`）
`+8`  = **data 指针**（`void*`）
`+16` = **zone 字节**（`u8`）
        ↓
★★★ ⇒ 注释（第 13689–13691 行逐字）："**DB_InitPool `0x0049C690` threads 120,000
 28-byte XAssetEntry rows starting at `0x0239B120`**"
```

### ★★★★★ **`assetZoneForHeader` 的线性扫描**（第 11823–11850 行）

```cpp
for (index = 0; index < 120000; ++index) {
    entry = entries + index * 28;
    if (!readableSpan(entry, 28)) return nullopt;
    if (entryType == type && entryHeader == header && entry[16] != 0)
        return entry[16];
}
return nullopt;
```

★★★ **⇒ 最多 **120,000 次迭代** ⇒ 每次查 zone 都全扫。**

### ★★★★★ **为什么需要 zone 提升**（第 13129–13135 行，逐字）

```
"**DB_LinkXAssetEntry allocates with the current loading-zone byte. At this late runtime
 boundary that byte is zero, which makes an otherwise valid new WeaponDef a default
 placeholder and causes the native resolver to reject it.** Give the clone **its retained
 source's resident zone** before asking the DB or weapon registry for it."
```

### ★★★★★ **生成过期与重建**（第 12100–12115 行，逐字）

```cpp
// **common_mp is loaded once for the front end and again for the booked map.** The engine
// **removes every runtime-linked entry owned by the old generation** during that
// transition, **while this process-local cache naturally survives**. Use the private
// base model as the **generation sentinel** and **rebuild the closure from the immutable
// metadata when it disappears**. At that point **every private entry from the same zone
// has already been unlinked**, so **releasing its old backing storage is safe**.
if (barrettMetadataEnabled && publishedBarrettAssets.ready &&
    !findXAsset(XModelAssetType, "**viewmodel_barrett**", false).data)
{
    publishedBarrettAssets = {};
    OlMod::RuntimeLog::write(..., "alpha Barrett asset generation expired; rebuilding closure");
}
```

★★★ **⇒ **`viewmodel_barrett`** 是**代际哨兵**。**

---

## 三、★★★★★ **Barrett 资产闭包的 15 秒流式等待**

### 3.1 ★★★★★ 完整实现（第 12872–12913 行）

```cpp
constexpr DWORD StreamWaitMilliseconds = **15000**;
const auto streamDeadline = GetTickCount64() + StreamWaitMilliseconds;
bool streamsReady{};
do {
    streamsReady =
        all_of(surfs, [](storage) {
            // XModelSurfs: +4 surfaces 指针,+8 surfaceCount
            return surfaces && surfaceCount;
        }) &&
        all_of(models, [](storage) {
            // XModel +349 bit 3
            return readableSpan(linked, 350) && (linked[**349**] & **0x08**) != 0;
        });
    if (!streamsReady) Sleep(**1**);
} while (!streamsReady && GetTickCount64() < streamDeadline);
if (!streamsReady) return failBarrettAssets(LinkFailed,
    "native XModel streaming did not finish within 15 seconds");
```

★★★★★ **⇒ 三个精确值：**
```
超时 **15,000 ms**
`XModelSurfs +4` = **surfaces 指针**,`+8` = **surfaceCount**
`XModel +349` 的 **bit 3（`0x08`）** = **最终 LOD 重建完成的标志**
        ↓
★★★ 注释（第 12865–12871 行逐字）："**Queue every linked type-4 asset through the
 engine's model-stream worker. Do not call the three post-link helpers here: racing that
 worker lets two loaders see the same null XModelSurfs pointer and can hand the renderer
 a null index source. Wait for the native attach -> renderer init -> LOD rebuild sequence
 instead. Bit 3 at XModel +349 is set only by the final rebuild step.**"
```

### ★★★★★ **六个资产结构体**（第 12018–12081 行）

```cpp
struct PublishedBarrettImage     { name[128]; loadDef[16]; header[AlphaBarrettOlfinalGfxImageSize]; linked; };
struct PublishedBarrettMaterial  { name[128]; textures(12B each); constants; stateBits; header[...]; linked; };
struct PublishedBarrettSurfs     { name[128]; header[48]; linked; };
struct PublishedBarrettModel     { name[128]; boneNames; parentList; quaternions; translations;
                                   partClassification; baseMatrices; materials; boneInfo;
                                   header[**360**]; linked; };
struct PublishedBarrettAnimation { name[128]; boneNames; notify; dataByte; dataShort; dataInt;
                                   randomDataShort; randomDataByte; randomDataInt; indices;
                                   emptyStreamSentinel[1]; header[**88**]; sourceName; linked; };
struct PublishedBarrettAssets    { attempted; ready; images; materials; surfs; models; animations; };
```

★★★ **⇒ 五个资产类型 + 一个容器；**`XModel` 头 360 字节**,**`XAnim` 头 88 字节**。**

### ★★★★★ **`XAnim` 的九个流指针**（第 12528–12545 行）

```cpp
setAnimationPointer(0, boneNames.data(),        boneNames.empty());
setAnimationPointer(1, dataByte.data(),         dataByte.empty());
setAnimationPointer(2, dataShort.data(),        dataShort.empty());
setAnimationPointer(3, dataInt.data(),          dataInt.empty());
setAnimationPointer(4, randomDataShort.data(),  randomDataShort.empty());
setAnimationPointer(5, randomDataByte.data(),   randomDataByte.empty());
setAnimationPointer(6, randomDataInt.data(),    randomDataInt.empty());
setAnimationPointer(7, indices.data(),          indices.empty());
setAnimationPointer(8, notify.data(),           notify.empty());
```

★★★ **⇒ **九个流**,写入 `header + 48 + pointer*4`（`pointerPresence[pointer]` 为真时）。**

### ★★★★★ **`XModel` 的九个指针写入**（第 12768–12803 行）

```cpp
writePointer(header, **0**,   name.data());
writePointer(header, **44**,  boneNames.data());
writePointer(header, **48**,  parentList.data());
writePointer(header, **52**,  quaternions.data());
writePointer(header, **56**,  translations.data());
writePointer(header, **60**,  partClassification.data());
writePointer(header, **64**,  baseMatrices.data());
writePointer(header, **68**,  materials.data());
writePointer(header, **312**, boneInfo.data());
// 每个 LOD：
writePointer(header, **72 + lod*56 + 8**,  surfs->linked);
writePointer(header, **72 + lod*56 + 12**, surfs->name.data());
```

★★★★★ **⇒ 十一个指针偏移：**
```
`0` 名字 / `44` 骨名 / `48` 父列表 / `52` 四元数 / `56` 平移 / `60` 部件分类 /
`64` 基矩阵 / `68` 材质 / **`312` boneInfo** / **`72 + lod*56 + 8`** surfs 指针 /
**`72 + lod*56 + 12`** surfs 名字
```

### ★★★★★ **三个材质回退名**（第 12679–12687 行）

```cpp
const char *fallback = "**mc/mtl_weapon_m16**";
if (name.find("**reticle**") != npos)       fallback = "**mc/mtl_ret_acog02_acota31ncm_alpha**";
else if (name.find("**lens**") != npos ||
         name.find("**screen**") != npos)   fallback = "**mc/mtl_weapon_lens_eot_exps**";
else if (name.find("**acog**") != npos)     fallback = "**mc/mtl_weapon_acog_2_alpha**";
```

★★★ **⇒ 四个材质名 + 四个匹配子串（`reticle` / `lens` / `screen` / `acog`）。**

### ★★★★★ **`barrettSafeMaterialsEnabled` 与 `routingCompatible`**（第 12326–12330 行）

```cpp
if (barrettSafeMaterialsEnabled || !routingCompatible) {
    retainedBarrettMaterialNames.insert(source.name);
    continue;   // ★ 不发布,走回退
}
```

★★★ **⇒ 两个条件任一成立就**不发布材质**：**
```
① `OLMOD_ALPHA_BARRETT_SAFE_MATERIALS=1`
② `!routingCompatible`（纹理槽头或常量前 4 字节与模板不符）
        ↓
★★★ 注释（第 12318–12320 行逐字）："The **first four bytes identify the material
 constant**. The **remaining 28 bytes are the material-specific value that the alpha port
 intentionally replaces**."
```

### ★★★★★ **21 个 XAnim 槽**（第 13038–13060 行）

| 槽 | 名字 |
|---|---|
| **1** | `alpha_barrett_idle` |
| **2** | `alpha_barrett_idle` |
| **3** | `alpha_barrett_fire` |
| **5** | `alpha_barrett_fire` |
| **9** | `alpha_barrett_reload` |
| **11** | `alpha_barrett_reload_empty` |
| **15** | `alpha_barrett_pullout` |
| **16** | `alpha_barrett_pullout` |
| **17** | `alpha_barrett_breach` |
| **18** | `alpha_barrett_putaway` |
| **21** | `alpha_barrett_pullout_quick` |
| **22** | `alpha_barrett_putaway_quick` |
| **23** | `alpha_barrett_pullout` |
| **24** | `alpha_barrett_putaway` |
| **25** | `alpha_barrett_sprint_in` |
| **26** | `alpha_barrett_sprint_loop` |
| **27** | `alpha_barrett_sprint_out` |
| **34** | `alpha_barrett_ads_fire` |
| **35** | `alpha_barrett_ads_fire` |
| **46** | `alpha_barrett_ads_up` |
| **47** | `alpha_barrett_ads_down` |

★★★ **⇒ 21 个槽,9 个不同名字；`AnimationArrayOffset = **0x7C**`。**
**⇒ 注释（第 13031–13037 行逐字）："The **0.0.2.2 WeaponDef loader reads 48 XStrings at
`+0xEC`**. Its **packed block-3 pointers advance in the same order** as the directly
serialized `viewmodel_barrett` XAnimParts; **the three inline strings at 34/46/47
corroborate ADS fire, up and down independently**. **OLfinal extends this enum to 62
without reordering these original slots.**"**

### ★★★★★ **两个模型数组的偏移变化**（第 12990–13000 行，逐字）

```
"CODREF(alpha_weapondef): **the alpha loader keeps sixteen first-person XModels at
 `+0x14` and sixteen world XModels at `+0x54`. Barrett selects `viewmodel_barrett` and
 `weapon_m82` in element zero of those arrays. OLfinal reduced the two arrays to two
 entries apiece at `+0x10`/`+0x14` and `+0x18`/`+0x1C`.**"
```

★★★ **⇒ 两个版本的两个数组：**

| 版本 | 第一人称 | 世界 |
|---|---|---|
| **alpha** | **`+0x14`**（16 项） | **`+0x54`**（16 项） |
| **OLfinal** | ★ **`+0x10`** / **`+0x14`**（各 2 项） | ★ **`+0x18`** / **`+0x1C`**（各 2 项） |

### ★★★ **`markAlphaBaseWeapon` 的进程分支**（第 11727–11738 行）

```cpp
if (OlMod::processRole() == OlMod::ProcessRole::Client)
    return true;                        // ★ 客户端不改
auto *const type = module_ + ConfigStringTypesRva + WeaponConfigStringBase + index;
*type = **19**;                          // ★ 专服改成 19（普通武器类型）
```

★★★★★ **⇒ 完整理由（第 11714–11726 行，逐字）：**
```
"**The DEDICATED must retag them while it derives the outgoing modular boundary. The
 CLIENT must not**: runtime-only alpha base names **are absent from its constant
 configstring table**, so **type 19 makes `CL_GetConfigString` return null and `sub_59B560`
 dereference it**. Its gamestate hook **restores the same native registry entries directly
 and leaves those empty wire slots tagged as dynamic**, which makes **the accessor return
 the safe empty gamestate string until the real `** ...` row**. **Type 19 is this build's
 ordinary weapon type; type 21 and >=23 are the measured dynamic sentinels.**"
```

### ★★★ `exactPrefix` 的两条校验（第 12439–12447 行）

```cpp
ScriptStringInternRva = **0x34BD10**  ⇒ `{ 0x55, 0x8B, 0xEC, 0x83, 0xEC, 0x14 }`
XModelStreamQueueRva  = **0x09A2B0**  ⇒ `{ 0x55, 0x8B, 0xEC, 0xA1 }`
GfxImageInitializeRva = **0x7E7470**  ⇒ `{ 0x8B, 0x44, 0x24, 0x04, 0x83, 0xEC, 0x20 }`
```

★★★ **⇒ 三个 RVA + 三个前缀。`GfxImageInitialize` 就是报告 129 的 `sub_BE7470`（`0x7E7470`）✓**

---

## 四、★★★★★ **`resolveWeaponItem` 的 12 步完整链**

### 4.1 ★★★★★ 完整流程（第 14179–14754 行）

```
① 三个绑定检查（`weaponLookup_` / `weaponResolver_` / `attachmentLookup_`）
② ★ **别名文件查表**（`aliasedWeaponName`）
③ 名字解析（别名优先,否则 `readItemInternalName`）
④ ★ **`barrett_heartbeat_mp` 的提前安装**
⑤ `weaponResolver_(name, nullptr)` ⇒ `resolvedWeaponAssetIndex`
⑥ ★★ **上界 `BaseWeaponAssetCount = 1300`**
⑦ `weaponLookup_(name) == resolvedWeaponAssetIndex` 回读校验
⑧ ★ **Alpha 网络资产索引覆盖**
⑨ ★ `OLMOD_AUDIT_WEAPON_TABLE` 一次性全表审计
⑩ 默认附件（`readDefaultWeaponAttachments`）
⑪ ★ **已装备附件逐个校验（五重）**
⑫ ★ **`SV_MergeWeaponAttachments` 合并**
⑬ ★ **FMJ 检测**
⑭ ★ **构建 `** <base> 0 0 <att...>` 字符串**
⑮ ★ `weaponResolver_(modularName)` ⇒ 模块化武器索引
⑯ ★ **依赖发现**（`registryCountBefore+1 .. registryCountAfter`）
⑰ ★ **回读完成的定义**（`readWeaponDefinition(modularWeaponAssetIndex)`）
```

### ★★★★★ **`BaseWeaponAssetCount = 1300` 的纠正**（第 14240–14244 行，逐字）

```cpp
// CODDIFF(1649370): **the bound was `0x400` = 1024, which is 3.3.3.3's base weapon
// table**. This build's is **BaseWeaponAssetCount = `0x514` = 1300**, measured from
// **the gap between PerWeaponAttachmentCountsRva and AttachmentModelCountRva**, so
// **every base weapon from 1024 up was being rejected as out of range by a constant
// from the other build**.
if (!resolvedWeaponAssetIndex || resolvedWeaponAssetIndex >= BaseWeaponAssetCount)
```

### ★★★★★ **失败时的全定义字符串 dump**（第 14248–14278 行）

```cpp
// 遍历 ItemDefinitionSize(40) 的每个 4 字节偏移,打印所有 validBookingName 的字符串
std::string fields;
for (offset = 0; offset + 4 <= 40; offset += 4) {
    const auto *candidate = *(const char *const *)(definition + offset);
    const auto text = readCString(candidate, 64);
    if (text && !text->empty() && validBookingName(*text))
        fields += " +" + std::to_string(offset) + "=" + *text;
}
```

★★★★★ **⇒ 理由（第 14250–14257 行逐字）：**
```
"**`sf_weapon_m4_mp_name` is a LOCALISATION KEY, not a weapon asset name**, so
 **ItemDefinitionNameOffset is pointing at the wrong field on this build** -- another
 constant carried from 3.3.3.3. **Rather than guess which neighbouring offset holds the
 internal name, report every readable string in the definition and let the log name it.
 Guessing +8 and then +16 costs two launches; this costs none.**"
```

### ★★★★★ **已装备附件的五重校验**（第 14379–14448 行）

```
① `readItemInternalName(attachmentItemId)` ⇒ 否则 `skip("has no internal name")`
② `readAttachmentModelSlot(name)` ⇒ 否则 `skip("has no model slot")`
③ `attachmentLookup_(name)` 且 `< 0x3FFF` ⇒ 否则 `skip("is not in the attachment registry")`
④ ★ **`attachmentIdForWeapon` 翻译**（§187h）
⑤ ★ **`attachmentSupportedByWeapon`（严格测试）** ⇒ 否则 `skip("is not supported by this weapon")`
⑥ ★ **`attachmentModelResolutionAvailable`** ⇒ 否则 `skip("has no model for this weapon")`
```

★★★★★ **⇒ 第 ④ 步的完整理由（第 14397–14419 行，逐字）：**
```
"**AND TRANSLATE IT TO THIS WEAPON FIRST. Section 187h.**
 **The profile stores one generic attachment item and hangs it on several weapons, but the
 modular string wants that weapon's OWN id: 6206 for a TMP's red dot, 14268 for an M9's,
 both model 17. Without this step the canonical name resolves to another weapon's id, the
 strict test below correctly rejects it, and the player gets nothing.**"
```

★★★★★ **⇒ 第 ⑤ 步的完整理由（第 14421–14432 行，逐字）：**
```
"**THE STRICT TEST, NOT THE LOOKUP. Section 187.**
 **attachmentModelResolutionAvailable answers "which model" and returns the engine's NONE
 model when a weapon has no entry for an attachment** -- which **reads as available and is
 how a red dot ended up on an MSR, faulting both clients at spawn with
 `1073 tag_reticle_red_dot ..._vmchar`**. **A reticle mounts on a tag the weapon's model
 does not carry, so nothing downstream could have caught it.**
 **DEFAULTS KEEP THE LENIENT CHECK** in the merge below, deliberately: they are the
 weapon's own and the none model is a legitimate answer for them. **Only an attachment the
 PLAYER chose has to prove the weapon supports it.**"
```

### ★★★★★ **`attachmentIdForWeapon` 的两遍翻译**（第 13942–13996 行）

```cpp
// 第一遍：全表找 canonicalAttachmentId 对应的 model
for (weapon = 1; weapon < 1300 && !model; ++weapon)
    for (row : entriesFor(weapon))
        if ((u16)row == canonicalAttachmentId) { model = (u16)(row >> 16); break; }

// 第二遍：在目标武器里找同 model 的条目
for (row : entriesFor(targetWeaponAssetIndex))
    if ((u16)(row >> 16) == *model) return (u16)row;
```

★★★★★ **⇒ 完整注释（第 13946–13951 行，逐字）：**
```
"**Section 187h. Two passes over `word_198C0A0[128 * weapon]`, the same
 (nameId, modelIndex) pair table `sub_42F9B0` walks**:
   1. **find the MODEL the canonical id names, anywhere it is registered**;
   2. **find the entry in the TARGET weapon carrying that same model.**
 **Both RMRs are model 17, both extended magazines model 10**, so **the model is what
 survives the change of weapon while the id does not**."
```

### ★★★ **`MaximumAttachmentsPerWeapon = 64`**（第 13885 行）

```cpp
constexpr std::uint32_t MaximumAttachmentsPerWeapon = **64**;
```
★★★ **⇒ `128 u16 per weapon = 64 (attachment, model) pairs`（第 14031 行）。**
**⇒ 低半 = **interned name id**（不是附件索引）,高半 = **model 索引**。**

### ★★★★★ **`sub_42F9B0` 的完整反汇编**（第 14024–14034 行，逐字）

```
"**out.exe sub_42F9B0, the engine's own lookup, exactly:**
     **v2 = byte_1988638[weapon];**                       per-weapon COUNT
     **if (!v2) return dword_198B8A0[word_19DDECC];**     NONE model
     **for (i = &word_198C0A0[128*weapon]; *i != attachment; i += 2)**
         **if (++v3 >= v2) return dword_198B8A0[word_19DDECC];**   NOT FOUND
     **return dword_198B8A0[i[1]];**                      FOUND
        ↓
★★★ **128 u16 per weapon is 64 (attachment, model) pairs**, which is the same layout
 this file reads as **`uint32_t[64]` with the attachment in the low half**. And
 **`sub_42F910` never registers a pair whose model is the none model**, so **anything
 present here is genuinely supported**."
```

### ★★★★★ **`internedAttachmentName` 的 `0x3FFD` 上界**（第 13930 行）

```cpp
if (!module_ || !attachmentId || attachmentId >= **0x3FFD**)
    return std::nullopt;
```
★★★ **⇒ `0x3FFD` = **16,381**；与 `0x3FFF`（16,383）**差 2**。**
**⇒ 而第 14392 / 14517 行用的是 `>= 0x3FFF`** ⇒ **两个不同的上界** ⇒ 记录为**待核对**。

### ★★★★★ **`modularName` 的完整格式**（第 14512–14543 行）

```cpp
std::string modularName = "** " + std::to_string(selection.baseWeaponAssetIndex) + " 0 0";
for (attachment : *effectiveAttachments) {
    const auto attachmentIndex = attachmentLookup_(attachment.name.c_str());
    if (!attachmentIndex || attachmentIndex >= 0x3FFF) return false;
    if (!attachmentModelResolutionAvailable(resolvedWeaponAssetIndex, attachmentIndex)) return false;
    selection.attachmentAssetIndexes[selection.attachmentCount++] = attachmentIndex;
    modularName += " " + std::to_string(attachmentIndex);
}
```

★★★★★ **⇒ 格式：**`** <base> 0 0 <att1> <att2> ...`**
**⇒ 零售实测对照（第 14481–14483 行，逐字）：**
```
     `** 682 0 0 9930 8738 6747 10545 9321 6690 6825`
     `** 652 0 0 8738`
     `** 249 0 0`                          <- a weapon with no attachments
```

### ★★★★★ **FMJ 的穿透翻倍**（第 14488–14511 行，逐字）

```cpp
// 28700 (FMJ): **the merged attachment NAME list is the only place this server knows
// "the player attached FMJ"** -- **the modular string carries asset ids, not names**, and
// **the operator's rule is concrete: "普通穿透是 1，装上 FMJ 就是 2"**. **The bullet path
// doubles the material depth when this flag is set; no second table is involved.**
selection.fmjPenetration = false;
for (attachment : *effectiveAttachments)
    if (attachment.name.rfind("**mag_fmj**", 0) == 0) { selection.fmjPenetration = true; break; }
```

### ★★★★★ **`defaultsInTable` 的实测**（第 14575–14583 行，逐字）

```
"**THE TABLE ITSELF, AS TEXT. `defaultsInTable` came back `0/1`, `0/4` and `1/3` with
 `tableCount` 10..19** -- **the tables are populated and the weapons' OWN DEFAULTS are
 missing from them, which can only mean the key we compute is not the key they are stored
 under.**
        ↓
★★★ **`sub_42F910` interns `dword_198B8A0[model]->name` -- the attachment MODEL's name** --
 so **the low half is an interned name id, not an attachment index**. **`dword_1978640[id]`
 is that id's `char*`**, so **the entries can be printed rather than guessed at**."
```

### ★★★★★ **"零售的仅默认变体看起来和我们一模一样"**（第 14631–14641 行，逐字）

```
"**WHY THE SPLIT MATTERS.** Our `** 646 0 0 8738 9321` and `** 992 0 0 9321` are
 **BYTE-IDENTICAL to retail's cs 7184 and cs 7204**, so **the format and the ids are right**.
 But retail also publishes `** 992 0 0 6206 9321`, `** 646 0 0 14268 8738 9321` and
 `** 534 0 0 9930 4415 5153 8738 6747 10545` -- **EVERY ATTACHMENT COMBINATION IS ITS OWN
 WEAPON STRING**, and those variants carry **ids ours never produce**. **Matching retail's
 DEFAULT variant exactly is what publishing defaults-only looks like, so the number that
 decides it is EQUIPPED, not the total.**"
```

### ★★★★★ **Barrett 的 1234 / 1154 陷阱**（第 14657–14683 行，逐字）

```
"**The dedicated's map reset moves its private `barrett_mp` base from 1234 to 1154, while
 the client keeps Barrett at 1234 and has `chicken_melee_mp` at 1154.** Session preparation
 already resolved the canonical Barrett variant before that reset, when both processes
 agreed on 1234. **Reuse that retained dynamic WeaponDef afterwards.**
 **Building a fresh "** 1154" is correct only inside the dedicated and sends the client a
 fully functional knife**; **building a new "** 1234" after reset would inherit the
 dedicated's now-unrelated killstreak WeaponDef**. **If the proven canonical variant
 disappeared, refuse the loadout instead of constructing either wrong weapon.**"
```

### ★★★ **依赖发现与缓存**（第 14705–14734 行）

```cpp
for (index = registryCountBefore + 1; index <= registryCountAfter; ++index) {
    if (index == modularWeaponAssetIndex) continue;
    dependency = SV_ParseModularWeaponConfigString(readWeaponDefinitionName(index));
    if (!dependency) { ModularWeaponDependency; return false; }
    discoveredDependencies.push_back(*dependency);
}
if (!discoveredDependencies.empty())
    modularDependencyCache_.insert_or_assign(modularName, discoveredDependencies);
```

★★★ **⇒ 依赖 = `registryCountBefore+1 .. registryCountAfter` 之间的**所有新条目**（除自己）。**

---

## 五、★★★★★ **`resolveSessionPerks` 的 96 位与 192 位**

### 5.1 ★★★★★ 完整流程（第 14761–14893 行）

```
① `mp/coPerkStatsTable.csv`（至少 2 列）⇒ 每行的 column 1 是名字,column 0 是位索引
② ★ **位索引上界 96** ⇒ `bits[i >> 5] |= 1 << (i & 31)`（**3 个 dword**）
③ `mp/coAbilityModifiersTable.csv`（至少 7 列,实际至少 **27** 列）
④ ★ **列 15..26（步长 2）= 12 个 modifier/amount 对**
⑤ ★ **`mp/coAbilityModifiersTable` 的五个列**：`0` id / `2` valueIndex / `3` initial /
   `4` minimum / `5` maximum
⑥ ★ **id 上界 192** ⇒ `abilities.mask[id >> 5] |= 0x80000000 >> (id & 31)`（**6 个 dword**）
⑦ ★ **`valueIndex` 上界 36**
⑧ ★ **三个具名 modifier**：`modMoveSpeedScale` / `modFallDamageScale` / `modKillstreakShift`
```

★★★★★ **⇒ 两个位宽：**
```
perk 位集：**96 位 = 3 个 dword**（`bits[3]`）
ability 掩码：**192 位 = 6 个 dword**（`abilities.mask[6]`）
        ↓
★★★ 注意 **ability 的位序是 `0x80000000 >> (id & 31)`**（**高位优先**）
★★★ 而 perk 的位序是 **`1 << (i & 31)`**（**低位优先**）⇒ **两者相反**
```

### ★★★ **`sub_413980` 与 `sub_4442E0`**（第 14776–14778 行，逐字）

```
"CODREF(1649370): **`sub_413980` looks up column 1 (canonical name), reads column 0
 (decimal bit index), and rejects indices >= 96**. **`sub_4442E0` sets
 `ps+0x584 + 4*(index>>5)`, bit (index&31)**. **The row ordinal is NOT the perk index.**
 BO1 `BG_SetPerk 0x60E0E0` and Ghosts `PlayerCmd_SetPerk 0x14011A760` confirm bitset
 ownership; **their perk counts and player-state offsets are different**."
```

★★★ **⇒ 三个精确值：**
```
perk 位集在 **`ps + 0x584`**,`+ 4*(index>>5)`
`sub_413980` 上界 **96**
**"行序号不是 perk 索引"**
```

### ★★★★★ **Fast Hands 与 Marathon 的实测**（第 14854–14857 行，逐字）

```
"**The live asset describes additive deltas, defaults, and clamps.** **Retail DM
 corroborates Fast Hands' 1.5 switch / 1.6 offhand scales and Marathon's -1 sprint
 sentinel (default 4, delta -7, minimum -1).** **The native consumers divide durations by
 these speed scales.**"
```

★★★ **⇒ 三个精确值：**
```
**Fast Hands**：**1.5**（switch）/ **1.6**（offhand）
**Marathon**：default **4**,delta **-7**,minimum **-1** ⇒ **-1** 是冲刺哨兵
```

---

## 六、★★★★★ **`publicProfileReady` 的四重校验**

### 6.1 ★★★★★ 完整实现（第 15122–15153 行）

```cpp
const auto *profile = module_ + ProfileManagerRva + PublicProfileOffset;   // ★ 0xE14BC48 + 16
if (!readableSpan(profile, ProfileParsedOffset + 1)) return false;         // ★ 0x1112C + 1
if (!profile[ProfileParsedOffset]) return false;                           // ★ 已解析
if (*(u32*)(profile + ProfileChunkMaskOffset) != ProfileRequiredChunkMask)  // ★ 0x1008C == 0x07FFFFFF
    return false;
return *(i32*)(profile + ProfileOperationOffset) == 0;                      // ★ 116 == 0
```

★★★★★ **⇒ 四重校验：**
```
① 可读（`0x1112C + 1` 字节）
② `profile[0x1112C] != 0`（已解析）
③ `*(u32*)(profile + 0x1008C) == **0x07FFFFFF**`（**相等**,不是掩码测试）
④ `*(i32*)(profile + 116) == 0`（**无操作在飞**）
```

★★★★★ **⇒ 第 ③ 条的注释（第 15142–15144 行，逐字）：**
```
"**EQUALITY, not a mask test.** `chunkMask === PROFILE_REQUIRED_CHUNK_MASK` is what the
 tool checks, so **extra bits set is NOT ready**, and **a subset test would call a
 half-loaded profile ready**."
```

### ★★★★★ **`ProfileManagerRva` 是**管理器本身,不是指针****（第 15129–15136 行，逐字）

```
"**ProfileManagerRva IS THE MANAGER, not a pointer to it.** CodolMatchFlow.py's
 `readPublicProfileState` does `profileManager.add(PUBLIC_PROFILE_OFFSET)` on
 `module.base.add(PROFILE_MANAGER_RVA)` -- **no dereference anywhere**, and the arithmetic
 checks out against what it printed live this session: **`0x400000 + 0xE14BC48 + 0x10 =
 0xE54BC58`**, which is the address it reported.
        ↓
★★★ **The first version of this dereferenced twice and returned false forever**, which
 read as **"the profile is never ready"** on a run where it demonstrably was."
```

### ★★★★★ **`currentCharacterIndex` 的 0..11 边界**（第 15065–15089 行，逐字）

```cpp
if (characterIndex < 0 || characterIndex >= **12**) {
    // ★ 12 是我们的上界,不是引擎的
    ...
}
```

★★★★★ **⇒ 完整注释（第 15071–15076 行，逐字）：**
```
"**12 IS OUR BOUND, NOT THE ENGINE'S.** out.exe's own consumers -- **`sub_6B87C0` and
 `sub_7C5BA0`**, which is the function that actually indexes the table -- **do only
 `if (index < 0) index = 0` and then scale by 156 with no upper check**. So **this is
 stricter than the code it is modelling, and may simply be wrong here**. **Widening it on
 that reasoning alone would be inventing a bound; report the value and let a measurement
 decide.**"
```

★★★ **⇒ 三个精确值：**
```
我们的上界 **12**
引擎的做法：**`if (index < 0) index = 0`**（只钳负数）
引擎的缩放：**156**
```

### ★★★★★ **`profileSlotProbeEnabled` 的默认关闭理由**（第 15094–15109 行，逐字）

```
"**OFF BY DEFAULT, and this is a calibration decision rather than caution.**
 **Reading the roster is a bounded memory read behind readableSpan and is demonstrably
 safe** -- it ran on a live client and produced the 686 measurement.
 **CALLING `sub_50FF30` is a native call on the bridge thread, and its safety is NOT
 established**: it walks the public profile, formats two strings and reads through a
 manager the game thread also owns.
        ↓
★★★ **Six ClientException reports exist on this build with the same innermost frame,
 `sub_779510 +0x230`, and THREE OF THEM PREDATE THIS BATCH.** Today's three share a
 different caller frame from the older three, which is **suggestive and is not a
 demonstration** -- **the probe ran twice with no crash, and did not run at all in two
 runs that crashed**. **Nothing isolates a cause either way.**"
```

★★★ **⇒ 六个 `ClientException`,最内帧 **`sub_779510 +0x230`**,其中 **三个早于本批次**。**

---

## 七、★★★★★ **`reportClientCharacterInfo` 的九个字段**

### 7.1 ★★★★★ 完整字段（第 15189–15361 行）

```
① `pid`（当前进程 id）
② `[N]`（clientNum 0..3）
③ ★ `cs{model=<+0x150>,item=<+0x7C&0xFFFF>,body=<+0x14>}`
④ ★ `req{model=,variant=,female=,item=,[overrides|no-overrides]}`（**+1024 的 64 字节**）
⑤ `valid`（`+0`）
⑥ ★ `dobj`（**`+900`**）
⑦ ★ `namePtr`（`+0x18` 的十六进制）
⑧ ★ `rebuild`（**`+660`**）
⑨ `model`（`NULL` / `UNREADABLE` / `EMPTY` / 实际名字）
⑩ `attach`（前 4 个附件名）
```

### ★★★★★ **四个关键偏移**

| 偏移 | 字段 |
|---|---|
| **`+0`** | `infoValid` |
| **`+0x18`** | 基础模型名指针 |
| **`+0x20`** | 十个附件名（每个 `char*`） |
| **`+660`** | rebuild 标志 |
| **`+900`** | DObj 句柄 |
| ★ **`+1024`** | **解析器请求**（64 字节） |

### ★★★★★ **客户端的 characterInfo 定位**（第 15163–15170 行，逐字）

```
"**`sub_53DF40` picks the block with**
     **`(char *)dword_827F730 + 1104 * entityState.clientNum + 717648`**
 **for ET_PLAYER, and passes it as BG_UpdatePlayerDObj's third argument.**"
```
★★★ **⇒ 步长 **1104**（`0x450`）+ 基址 **717648**（`0xAF350`）⇒ 与报告 133 **完全一致** ✓**

### ★★★★★ **`req` 的三态判定**（第 15283–15309 行，逐字）

```
"**`request` all zero ⇒ the modelIndex gate fired.** The client's clientState has no
 model index: **a WIRE fault, ours, on the way in.**
 **`request` populated ⇒ the gate passed and the resolver `0x0080E600` returned NO NAMES
 for that characterItemId** -- **the client cannot resolve that character, which is an
 ITEM-TABLE fault, not a wire one.**"
```

### ★★★★★ **`received` 的 clientState 定位**（第 15314–15324 行，逐字）

```
"**The clientinfo loop inside `sub_54B3F0` walks it:**
     **`mov ebx, [esp+0x24]`**      ; the CG object
     **`add ebx, 0x56C1C`**         ; clientState = ebx - 4  ->  **CG + 0x56C18**
     **`add ebx, 0x160`**           ; and the **stride is 0x160**
 and **`dword_827F730` is CG + 858368 (0x4557FE)**, so **the array sits at
 `dword_827F730 - 503016`**. Fields are the ones `0x00541800` reads: **the model index at
 `+0x150`, the character item at `+0x7C`, and the plain body model index at `+0x14`** that
 the fallback `0x00541BD0` turns into a name."
```

★★★ **⇒ 五个精确值：**
```
`CG + 0x56C18` = clientState 数组
步长 **`0x160`**
`dword_827F730` = `CG + 858368`
数组在 **`dword_827F730 - 503016`**
三个字段：**`+0x150`** model / **`+0x7C`** item / **`+0x14`** body
```

### ★★★★★ **电池读取的崩溃与撤回**（第 15340–15355 行，逐字）

```
"**NO BATTERY READ HERE.** `+0x0A4` was read from this struct for one run, to settle
 whether the zm meter's numerator is ever non-zero -- **it is not, measured `battery=0`
 with `valid=1`** -- and **the client CRASHED while firing shortly after, `0xC0000005` on
 a corrupted pointer**. **Isolated by reverting to the last commit and firing again: no
 fault, so the read is the prime suspect and it is gone.**
        ↓
★★★ **Why it was unsafe**: this function **RUNS OFF THE GAME THREAD**, and **the loop's
 only structural guard covers the first 32 bytes** (`CharacterInfoAttachmentNamesOffset`).
 **A read 164 bytes in, across four slots including ones no client occupies, is a
 check-then-use race against a struct the engine is rebuilding.** **A local readableSpan
 does not close that.**"
```

### ★★★★★ **`0x0044B310` / `0x004555D0` 的缓冲池**（第 15234–15240 行，逐字）

```
"**cgame hands every one of these slots a PERMANENT 64-byte buffer out of one pool at
 init** (**`0x0044B310` and `0x004555D0` walk 19 + 18 blocks of stride 1104 and deal out
 25 buffers each; the pool is memset `0xE740` = 37 * 1600**). **Nothing writes the POINTER
 afterwards** -- **`CG_SetupClientCharacterInfo 0x00541800` strncpy's INTO it.** So **a
 slot whose pointer cannot be read is not a race: it says this probe is not looking at
 that process's characterInfo at all.**"
```

★★★ **⇒ 四个精确值：**
```
池：**19 + 18 块 × 1104 步长**,每块**发 25 个 64 字节缓冲**
memset **`0xE740` = 37 × 1600**
        ↓
★★★ ⇒ **指针**永不被写** ⇒ 不可读的槽**不是竞态**,而是**探针看错了进程**
```

### ★★★★★ **`tag_` 出现在附件槽的缺陷**（第 15249–15254 行，逐字）

```
"**THE REBUILD FLAG AND THE ATTACHMENT SLOTS.** `BG_UpdatePlayerDObj 0x0040AB30` walks
 **the ten names at `+0x20` and STOPS AT THE FIRST EMPTY ONE**, registering every non-empty
 one as an XModel. **When the character resolver returns no names at all, `0x00541800`'s
 second loop is off by one slot and writes a TAG STRING into an attachment MODEL slot** --
 which is what **"tag index 0 kills the whole player's DObj"** was. **A `tag_` here names
 that defect on sight.**"
```

---

## 八、★★★★★ **`resolveGlassMapMetadata` 的三条关系**

### 8.1 ★★★★★ 完整校验（第 16154–16172 行）

```cpp
if (glass.definitionCount > MaximumFxGlassDefinitionCount ||           // ★ 1024
    glass.pieceLimit > MaximumFxGlassPieceLimit ||                     // ★ 2048
    glass.initialPieceCount > SvGlassPieceCount ||                     // ★ 1024
    glass.initialPieceCount > glass.pieceLimit ||
    // ★ 两条关系
    (glass.pieceLimit &&
        (glass.pieceWordCount != ((glass.pieceLimit + 31) >> 5) ||
         glass.pieceLimit != glass.initialPieceCount + SvGlassPieceCount)) ||
    (glass.initialPieceCount &&
        (!glass.definitionCount || !readableSpan(glass.initialPieceStates,
            glass.initialPieceCount * sizeof(*glass.initialPieceStates)))))
{
    return std::nullopt;
}
```

★★★ **⇒ 六条校验,其中两条是报告 134 的**精确关系**：**
```
`pieceWordCount == (pieceLimit + 31) >> 5`（= ceil/32）
`pieceLimit == initialPieceCount + **1024**`
```

### ★★★ 六个 piece 字段的校验（第 16180–16192 行）

```cpp
if (!finite(piece.quaternion) || !finite(piece.origin) ||
    !finite(piece.textureCoordinateOrigin) ||
    !std::isfinite(piece.radius) || piece.radius < 0.0f ||
    !std::isfinite(piece.doubledArea) || piece.doubledArea < 0.0f ||
    piece.definitionIndex >= glass.definitionCount)
{
    return std::nullopt;
}
```

### ★★★ `fxglass header` 的日志（第 16146–16150 行）

```
"fxglass header map=%.32s definitions=%u pieceLimit=%u pieceWords=%u initialPieces=%u cells=%u active=%u"
```

---

## 九、★★★★★ **三个 trace ABI 的完整对照表**

### 9.1 ★★★★★ **`traceTransformedCapsule`（第 17421–17438 行，逐字）**

```
//                    3.3.3.3 0x0058B330      1649370 0x00668560
//   [ebp+08] arg1    result                  result
//   [ebp+0C] arg2    start                   start
//   [ebp+10] arg3    bounds                  bounds
//   [ebp+14] arg4    targetBounds            **contents**
//   [ebp+18] arg5    contents                **targetOrigin**
//   ECX              targetOrigin            **targetBounds**
//   end              EAX                     **EDX**
```

★★★ **⇒ 三处不同：arg4 / arg5 / ECX / end 寄存器。**
**⇒ 实测四路（第 17432–17435 行逐字）："**Both of out.exe's own call sites agree
 (`0x0046DC81` in the box clip, `0x0046E3F6` in the point clip) and so do both of
 3.3.3.3's (`0x005FB4D1` server, `0x00458DCE` client).**"**

### ★★★★★ **`traceTransformedBrushModel`（第 17482–17500 行，逐字）**

```
//                    3.3.3.3 0x0058B230      1649370 0x00668470
//   [ebp+08] arg1    start                   **result**
//   [ebp+0C] arg2    end                     end
//   [ebp+10] arg3    bounds                  bounds
//   [ebp+14] arg4    clipHandle              clipHandle
//   [ebp+18] arg5    contents                contents
//   [ebp+1C] arg6    targetOrigin            **targetAngles**
//   ECX              targetAngles            **targetOrigin**
//   EDX              result                  **start**
```

★★★★★ **⇒ 后果（第 17499–17500 行逐字）：**
```
"**CARRYING 3.3.3.3's FORM HANDED THE CALLEE A 12-BYTE vec3 AS ITS 40-BYTE RESULT BUFFER.**"
```

### ★★★★★ **`traceWorld`（第 17347–17359 行）**

```cpp
__asm
{
    push edi
    mov edi, endPointer
    mov edx, mask
    push callbacksPointer
    push boundsPointer
    push startPointer
    push resultPointer
    call function
    add esp, 10h        // ★ 4 个栈参数
    pop edi
}
```
★★★ **⇒ `EDI = end` / `EDX = mask` / 4 个栈参数。**

### ★★★★★ **`invokePointTraceStaticModels`（第 2901–2912 行）**

```cpp
__asm
{
    push edi
    mov edi, output
    mov edx, contentMask
    mov ecx, endPointer
    push startPointer
    mov eax, function
    call eax
    add esp, 4          // ★ 1 个栈参数
    pop edi
}
```
★★★ **⇒ `EDI = output` / `EDX = contentMask` / `ECX = end` / **1 个栈参数（start）**。**

### ★★★★★ **`traceWorld` 的慢 trace 报告**（第 17243–17249 行，逐字）

```
"OLMOD(slow-trace-report): **section 97h found the frame thread parked at
 `out.exe+0x266938` -- a function whose only direct caller is itself, sitting immediately
 below WorldTrace, i.e. the engine's RECURSIVE clipmap descent**. **Traces of 199217 us,
 111549 us and 459473 us were measured on this map.** **A 459 ms trace stalls a whole
 frame on its own, which is what two players moving feels like.**"
```

★★★ **⇒ 三个精确值：`0x266938` / **199,217 µs** / **111,549 µs** / **459,473 µs**。**
**⇒ `slowMicroseconds = 50'000`,`reportLimit = 16`。**

### ★★★★★ **`TRACE CENSUS` 的 5 秒窗口**（第 17293–17315 行）

```cpp
if (window >= **5'000'000** && !SV_PerfBaseline() && OlMod::RuntimeLog::verbose()) {
    // "TRACE CENSUS %llu traces in %llu ms = %llu/s, %llu us in traces (%.1f%% of wall), mean %.1f us"
}
```
★★★ **⇒ 5 秒窗口,`verbose()` 门禁。**

### ★★★★★ **`SV_Trace` 在本 build 上不存在**（第 17682–17707 行，逐字）

```
"**CODREF(sv_trace): THIS BUILD HAS NO SV_Trace. Section 74.**
        ↓
★★★ **The comment this replaces said CODOL's server Pmove handler owns collision through
 SV_Trace and the linked g_entities tree, and on 3.3.3.3 that is true** -- **SVTrace
 0x005FB940 has exactly one caller**, reaches `0x0058D500` and `0x0058D790`, and those
 reach `0x005FB390` and `0x005FB510`, which read the gentity at **stride 0x2C8**.
 **1649370 has none of them.**
        ↓
★★★ **SVTraceRva 0x0046E780 is the counterpart of 3.3.3.3's 0x00459940, the GENERAL
 trace** -- **a thin wrapper calls it on both builds, it has 37 callers here to that one's
 24**, and its **box walker's leaf `0x0046DCF0` is instruction-for-instruction identical
 to 3.3.3.3's CLIENT leaf `0x00458E40` (319 of 319) and 6% similar to the server's
 `0x0058D200`**.
        ↓
★★★ **Its per-entity clip `0x0046DAE0` reads the client centity array through
 `dword_1C1D188[dword_82C3B60] ^ 0x2168F672` at stride 0x270 with the entityState at
 +0xF4** -- **the SAME array section 73 measured EMPTY on a live dedicated**, which is why
 **the locational point trace returned `hitType=0` with a healthy DObj standing in the ray**.
        ↓
★★★ **The two shared clip helpers confirm it from the other side: `0x0058B230` and
 `0x0058B330` have FOUR callers each there and `0x00668470` and `0x00668560` have TWO
 here -- the two that are gone are the server clips.**
        ↓
★★★★★ **So the entity half of every capsule query on this server was dead. The world half
 was not, because WorldTrace is genuinely shared, which is why a player has always stood on
 the ground and walked.**"
```

★★★ **⇒ 八个精确值：**
```
3.3.3.3 的 `SVTrace 0x005FB940`：**1 个调用者** ⇒ `0x0058D500` / `0x0058D790` ⇒
`0x005FB390` / `0x005FB510`（gentity **stride `0x2C8`**）
        ↓
1649370 的 `SVTraceRva 0x0046E780` = 3.3.3.3 的 `0x00459940`（**通用 trace**）
⇒ **37 个调用者 vs 24**
⇒ 叶子 `0x0046DCF0` 与 3.3.3.3 的**客户端叶子** `0x00458E40` **319/319 逐指令相同**,
   与服务端 `0x0058D200` 只有 **6%** 相似
        ↓
★★★ 每实体 clip `0x0046DAE0` 读**客户端 centity 数组**：
   `dword_1C1D188[dword_82C3B60] ^ 0x2168F672`,stride **`0x270`**,entityState @ **`+0xF4`**
★★★ ⇒ **同一数组在活专服上被测为**空****
        ↓
★★★ 两个共享 clip 辅助的调用者数：**3.3.3.3 各 4 个 / 本 build 各 2 个** ⇒ **消失的是两个服务端 clip**
        ↓
★★★★★ ⇒ **"每个胶囊查询的实体半边都是死的。世界半边没死,因为 WorldTrace 是真共享的,
   这就是为什么玩家一直能站在地上走路。"**
```

### ★★★★★ **`traceServerLocationalEntities` 的完整理由**（第 17827–17850 行，逐字）

```
"**CODREF(sv_trace): 3.3.3.3's `SV_PointTraceToEntity 0x005FB510`, done here.**
        ↓
★★★ **On 3.3.3.3 the clipmap walker `CM_PointTraceToEntities 0x0058D790` calls
 SV_PointTraceToEntity for every entity in the SERVER's sector tree**, and that function
 **reads the gentity at stride 0x2C8 from the pointer at 0x03150048**, tests **svFlags bit
 2 at gentity +0x112** to pick the locational pair, **builds an orientation from the
 entity's own currentOrigin +0x148 and currentAngles +0x154**, carries the ray into model
 space, calls DObjTraceline, and **rotates the hit normal back out at 0x005FB7DC**.
        ↓
★★★ **1649370 DOES NOT CONTAIN THAT FUNCTION.** Both builds also carry a **CLIENT twin --
 byte-identical outer, different leaf** -- and **out.exe kept only the twin**: its leaf
 reads **a heap centity array through the obfuscated slot
 `dword_1C1D188[dword_82C3B60] ^ 0x2168F672` at stride 0x270 with the entityState at
 +0xF4**, **offsets the ray by a GLOBAL vec3 rather than by any entity**, and **copies the
 normal without rotating it**. **The image has no `test byte [reg + 0x11A], 4` anywhere**,
 and **DObjTraceline has one fewer caller here than on 3.3.3.3 -- the server leaf's.**
        ↓
★★★★★ **So the ray this project handed `0x0046E6D0` was transformed into a space no player
 is in and matched against a list the dedicated never fills**, which is why **section 55's
 probe returned `fraction=1.0 hitType=0` before the DObj existed and returned exactly the
 same after it did (section 72).**
```

### ★★★ **`result.fraction` 必须**播种****（第 17946–17949 行，逐字）

```cpp
// **SEED IT.** The engine's own caller loads the **running best fraction** into this field
// before the call (**`0x0046E1FC`**), so **leaving it zero asks the traceline to beat zero
// and it never reports a hit**.
result.fraction = aggregate.fraction;
```

### ★★★ **法线回世界空间**（第 18019–18026 行）

```cpp
for (component = 0; component != 3; ++component)
    aggregate.normal[component] =
        result.normal[0] * axis[component] +
        result.normal[1] * axis[3 + component] +
        result.normal[2] * axis[6 + component];
```
★★★ **⇒ 用 `axis` 的**列**做线性组合（转置应用）。**

### ★★★★★ **`traceServerPoint` 的五个拒绝原因**（第 18161–18196 行）

```cpp
"request-invalid"           // SV_IsPointTraceRequestValid
"not-game-thread"           // 非游戏线程
"entity-mirror-mismatch"    // 镜像不匹配
"no-priority-map"           // priorityMap 空
"world-trace-failed"        // traceWorld 失败
"anim-condition-storage"    // 安装失败
```
★★★ **⇒ 六个原因串,上限 **12** 次。**

### ★★★★★ **`actor_skeletal_precedence`**（第 18301–18310 行，逐字）

```
"**OLMOD(actor_skeletal_precedence): an admitted posed actor already received a native
 bone trace, including its misses.** **A nearer broad capsule must not erase
 partGroup/partName or turn an actual gap between posed limbs into a body hit.**"
```

### ★★★★★ **`locational-candidacy-diagnostics` 的三字**（第 18328–18337 行，逐字）

```
"**OLMOD(locational-candidacy-diagnostics): report the words the NATIVE trace reads, not
 the source mirror it was built from.** The capsule log in Appmain prints
 **SvCollisionEntity::linked, which is this project's own flag**; **CM_PointTraceToEntities
 instead reads gentity `+0x110` isLinked, `+0x112` svFlags and `+0x12C` contents**, and
 **SV_ToNativeServerEntity deliberately writes isLinked as ZERO and leaves SV_LinkEntity to
 set it.** **A respawned player that the source believes is linked but the native never
 linked looks exactly like the measured symptom: capsule present, linked=1, maxsZ=70, ray
 2.5 units off its axis, and no hit for a whole magazine while the same setup hit at 103
 units before the death.**"
```

★★★ **⇒ 三个 gentity 偏移：**`+0x110` isLinked / `+0x112` svFlags / `+0x12C` contents**。**
**⇒ 实测症状：**`linked=1` / `maxsZ=70` / **射线偏离轴 2.5 单位** / **整弹匣无命中**（而死亡前同设置命中 **103 单位**）。**

### ★★★★★ **`traceTransformedDObjContentsPassed` 的完整流程**（第 18056–18101 行）

```
① `serverDObjGetAdapter` ⇒ DObj
② `installServerAnimConditionStorage`
③ `prepareNativeServerDObjPoses`（单实体）
④ `invokeAngleVectors`
⑤ 世界 → 局部
⑥ `invokeDObjContentsTraceline(dobj, start, end, contentMask, result)`
⑦ `restoreServerAnimConditionStorage`
⑧ 返回 `result.fraction == 1.0f`
```

### ★★★★★ **`traceRadiusDamageVisibility` 的两段**（第 18103–18148 行）

```
世界段：
  `traceWorld` ⇒ `fraction < 1.0 || startSolid || allSolid` ⇒ **false**
  ⇒ `invokePointTraceStaticModels` ⇒ 再次判定
        ↓
实体段：
  `ScriptModelDObj` ⇒ `traceTransformedDObjContentsPassed`
  其他 ⇒ `traceTransformedBrushModel` / `traceTransformedCapsule`
  ⇒ `fraction == 1.0 && !startSolid && !allSolid`
```

---

## 十、★★★★★ **其余关键细节**

### 10.1 ★★★★★ **`validateMessageBindings` 的三段测试**（第 18370–18418 行）

```cpp
// ① MSG_Init 后的初始状态
if (message.overflowed || message.readOnly || message.data != buffer.data() ||
    message.maxsize != 64 || message.cursize || message.bit) return false;

// ② MSG_WriteBits(0x78, 8)
MSG_WriteBits(message, **0x78**, **8**);
if (message.overflowed || message.cursize != **1** || message.bit != **8** ||
    buffer[0] != **0x78**) return false;

// ③ MSG_WriteString("codol")
MSG_WriteString(message, "**codol**");
if (message.overflowed || message.cursize != **6** ||
    memcmp(buffer.data(), "**codol\0**", 6) != 0) return false;

// ④ 完整 gamestate（**512** 字节缓冲）
std::array<std::uint8_t, **512**> gameStateBuffer{};
SvGameState gameState{ .mapName = "**mp_crash**", .gameType = "**tdm**" };
SV_PopulateRequiredConfigStrings(gameState);
gameState.configStrings.emplace(TimescaleConfigStringIndex, "**0 0 1 1**");
if (SV_PerfBaseline()) return SV_WriteGameState(writer, gameState, 0, 0);
return SV_WriteGameState(...) && std::ranges::equal(writer.data(), SvGameStateFixtureBytes);
```

★★★★★ **⇒ 三个精确值：**
```
`MSG_WriteBits(0x78, 8)` ⇒ `cursize == 1` / `bit == 8`
`MSG_WriteString("codol")` ⇒ `cursize == 6`（含 NUL）
gamestate 缓冲 **512**（不是 256）
        ↓
★★★ 第 18397–18400 行注释（逐字）："**512, NOT 256. The serverinfo now carries retail's
 ten measured keys (see `formatServerInfo`) and the gamestate is ~277 bytes; at 256 this
 writer overflowed and the stage failed for lack of room rather than for a real mismatch.**"
```

### ★★★★★ **`timescale` 的精确值**（第 18408 行）

```cpp
gameState.configStrings.emplace(TimescaleConfigStringIndex, "**0 0 1 1**");
```
★★★ **⇒ `timescale` 是四个值：`0 0 1 1`。**

### ★★★★★ **`OLMOD_PERF_BASELINE` 抑制 vision 配置串**（第 18409–18415 行，逐字）

```
"**OLMOD_PERF_BASELINE deliberately suppresses the vision configstrings, so
 `SvGameStateFixtureBytes` stops describing what the writer produces and this stage would
 fail on the mode rather than on a defect** -- **which took the dedicated down once
 already**. **The write is still exercised; only the byte comparison is skipped, and only
 in the diagnostic mode.**"
```

### ★★★ **`EngineMsgWriter` 的五个方法**

```cpp
EngineMsgWriter(bindings, buffer)   // ★ 检查 buffer > INT32_MAX ⇒ overflowed
MSG_WriteData(span)                 // ★ 四个溢出条件 + memcpy
MSG_WriteBits(value, bits)          // ★ 仅当未溢出才转 native
MSG_WriteString(string_view)        // ★ 含 NUL ⇒ overflowed
overflowed() / data()
```

★★★ **⇒ `MSG_WriteData` 的四个条件（第 18436–18438 行）：**
```cpp
message_.overflowed || message_.cursize < 0 ||
message_.maxsize < message_.cursize ||
value.size() > (size_t)(message_.maxsize - message_.cursize)
```

### ★★★★★ **`readMapEntityString` 的两种资产**（第 15937–15958 行，逐字）

```cpp
const std::array<MapEntsCandidate, 2> candidates{
    MapEntsCandidate{ AssetTypeMapEnts,      "maps/mp/" + map + ".**d3dbsp**" },
    MapEntsCandidate{ AssetTypeAddonMapEnts, "maps/mp/" + map + ".**mapents**" },
};
```

★★★★★ **⇒ 两个候选：**
```
**`AssetTypeMapEnts = 19`** ⇒ `maps/mp/<map>.d3dbsp`
**`AssetTypeAddonMapEnts = 42`** ⇒ `maps/mp/<map>.mapents`
        ↓
★★★ 实测（第 15940–15941 行逐字）：
   `mp_nuked` ⇒ **`maps/mp/mp_nuked.d3dbsp`**（**无** `.mapents`）
   `coop_training_mp_cargoship` ⇒ **`maps/mp/....mapents`**（**无** `.d3dbsp`）
        ↓
★★★ 后果（第 15943–15946 行逐字）："**Building only the .d3dbsp form made this return
 nullopt on every coop level**, which surfaced as **`world spawn pending
 stage=map_entity_asset`**, then **no entities**, then **`spawn refused ... NO_SPAWN_POINT`**
 -- **a fully rendered map the player cannot stand in.**"
```

### ★★★★★ **`resolveTriggerModelHulls` 的三个上限**（第 16032–16034 行）

```cpp
constexpr std::int32_t MaximumTriggerModels = **4096**;
constexpr std::int32_t MaximumTriggerHulls  = **65535**;
constexpr std::int32_t MaximumTriggerSlabs  = **65535**;
```

★★★★★ **⇒ 完整注释（第 16029–16031 行，逐字）：**
```
"**EVERY BOUND CHECKED BEFORE ANY READ.** These arrays are reached through pointers in a
 foreign process image; **a wrong stride still yields plausible floats**, so **refuse
 rather than return something shaped correctly**."
```

### ★★★★★ **三个 trigger 结构体**

```cpp
struct MapTriggerModel { u32 contents; u16 hullCount; u16 firstHull; };        // ★ 8 字节
struct MapTriggerHull  { float midpoint[3]; float halfSize[3]; u32 contents;
                         u16 slabCount; u16 firstSlab; };                      // ★ 32 字节
struct MapTriggerSlab  { float direction[3]; float midPoint; float halfSize; };// ★ 20 字节
```

### ★★★★★ **`resolveBrushModelCollision` 的两个偏移**（第 17144–17145 行）

```cpp
constexpr std::size_t BrushModelCountOffset = **0x90**;
constexpr std::size_t BrushModelsOffset     = **0x94**;
```
★★★ **⇒ `CollisionMapRva = 0x73E1C00` 的 `+0x90` 是计数,`+0x94` 是数组指针。**
**⇒ `NativeBrushModel` = **72 字节**,`leafBrushContents @ 0x24` / `leafTerrainContents @ 0x28`。**

### ★★★★★ **`directionToByte` 的 162 个方向**（第 16219 行）

```cpp
constexpr std::size_t DirectionCount = **162**;
```
★★★ **⇒ `ByteDirectionsRva = 0xA51C70` 有 **162 个 `float[3]`**（1,944 字节）,取**最大点积**。**

### ★★★★★ **`modelBoneIndex` 的 script-string 池**（第 16688–16702 行）

```cpp
constexpr std::size_t ScriptStringPoolRva = **0x749C524**;
...
const auto *text = (const char *)(scriptStrings + **20** * names[i] + **4**);
```
★★★★★ **⇒ 完整注释（第 16682–16687 行，逐字）：**
```
"**CODDIFF(actor_head_attachment): XModel boneNames are script-string IDs, not weapon
 attachment IDs.** CODOL **`0x485300` retains these IDs in the pool at VA `0x789C524`;
 `0x4EAAD0` resolves text as `pool+20*id+4`**. **AK live server/client reads confirmed
 `j_neck` at base bone20 and `j_spinelower` at bone5.** **The attachment table returned
 weapon names for the same numeric IDs, disabling every death-FX model change.**"
```

★★★ **⇒ 三个精确值：**`20 * id + 4`**（stride 20,名字在 +4）/ **`j_neck` = bone 20** / **`j_spinelower` = bone 5**。**

### ★★★★★ **`animationNotifyTimes` 的六个偏移**（第 16544–16553 行）

```cpp
const auto count = parts[**27**];
std::memcpy(&frames, parts + **14**, 2);      // u16 frameCount
std::memcpy(&rate,   parts + **40**, 4);      // float framerate
std::memcpy(&markers, parts + **80**, 4);     // 指针
// 每个 marker 8 字节：+0 u16 id,+4 float normalized
const auto seconds = normalized * frames / rate;
```

★★★★★ **⇒ 六个精确偏移：**
```
`+27`  = **marker count**（`u8`）
`+14`  = **frameCount**（`u16`）
`+40`  = **framerate**（`float`）
`+80`  = **markers 指针**
每个 marker **8 字节**：`+0` id / `+4` normalized
公式：**`seconds = normalized * frames / rate`**
```

### ★★★ **`animationNotifyName` 的池**（第 16581–16591 行）

```cpp
constexpr std::size_t NotifyStringPoolRva = **0x0749C524**;
const auto address = (u64)pool + **20** * nameId + **4**;
```
★★★ **⇒ 与 `modelBoneIndex` 的 `0x749C524` **同一个池**（`0x0749C524`）⇒ 同一个 stride 20 / +4。**

### ★★★★★ **`resolveScriptModelAnimationTree` 的 BST 遍历**（第 16491–16523 行）

```cpp
const auto *countAddress = module_ + **0x749C634**;
...
if (!count || count > **64** || !readableSpan(module_ + **0x749C534**, 4*(count+1)))
    return nullopt;
for (i = 1; i <= count; ++i) {
    memcpy(&definition, module_ + 0x749C534 + 4*i, 4);
    const auto wireId = definition[**10**];
    u32 nodeCount; memcpy(&nodeCount, definition, 4);
    if (!wireId || wireId > **31** || !nodeCount || nodeCount > **4096**) continue;
    // 对每个 alias 在 definition+4 的 BST 里查 node
    for (alias : aliases) {
        link = *(definition + 4);
        for (depth = 0; link && depth < **64**; ++depth) {
            key = *(u16*)link;
            if (key == alias) { node = *(u16*)(link+2); break; }
            link = *(link + (key > alias ? **4** : **8**));
        }
        if (!node || node >= nodeCount) { matches = false; break; }
    }
    if (!matches) continue;
    if (result) return nullopt;   // ★ 歧义 ⇒ 失败
    result = wireId;
}
```

★★★★★ **⇒ 七个精确值：**
```
计数 @ **`0x749C634`**（上界 **64**）
定义数组 @ **`0x749C534`**（`4*(count+1)`）
`definition[**10**]` = **wireId**（上界 **31**）
`definition[0..3]` = **nodeCount**（上界 **4096**）
`definition[**+4**]` = **BST 根**
BST 节点：`+0` **u16 key** / `+2` **u16 node** / `+4` 或 **`+8`** 子指针
        ↓
★★★ 子指针选择：**`key > alias ? +4 : +8`**
★★★ **深度上界 64**
★★★ **歧义 ⇒ `return nullopt`**（`OLMOD(script_model_tree_resolution)`）
```

### ★★★★★ **`resolveWeaponConfigStringIndex` 的 165–300 ms 修复**（第 16604–16647 行，逐字）

```cpp
// ★★★ 2026-10-14 修复（甲方「进图到创建人机完毕这段卡」的**真因**）——
//   原来**每次调用都线性扫 1700 条配置串**（`for index = 1 .. WeaponConfigStringCount`，
//   每次 `readCString(..., 128)` + 比较），一次未命中的名字要交两遍（配置串表 + 注册表回退）
//   ⇒ 实机实测 **单次 165–300 ms**（`BOTTRACE|class-resolve … lookupUs=1184729 lookupCalls=4`
//   ⇒ 4 次调用 0.66–1.18 s；**11 个人机 ≈ 8–13 s 的连续卡顿**）。
//   改为「**扫一次建名表，之后 O(1) 查**」；表随**配置串基址指针变化**（= 新 gamestate）自动重建。
//   语义完全不变：仍然返回**第一个**字符串相等的下标，未命中仍走原注册表回退。
struct WeaponNameIndex { const void *generation{}; std::unordered_map<std::string, u16> byName; };
static WeaponNameIndex nameIndex;
const void *const generation = nativeConfigString(WeaponConfigStringBase + **1**);
if (generation && nameIndex.generation != generation) { /* 重建 */ }
```

★★★★★ **⇒ 五个精确值：**
```
单次 **165–300 ms**
`lookupUs=**1184729**` / `lookupCalls=**4**` ⇒ **4 次 0.66–1.18 s**
**11 个人机 ≈ 8–13 s 连续卡顿**
        ↓
★★★ 代际哨兵 = **`nativeConfigString(WeaponConfigStringBase + 1)`**（**+1 的指针**）
★★★ 名表未建立时**保留原线性扫描作为兜底**
```

### ★★★ **`resolveSoundAliasEventParameters` 的 `%` 前缀与大小写**（第 16836–16848 行，逐字）

```
"**28800: EXACT COMPARISON WAS TOO STRICT FOR THREE SOURCES AT ONCE.** The name can arrive
 **with a `%` prefix** (resolveScriptAnimation already strips one for animations),
 **in a different case** (`AB_1mc_...` and `ab_1mc_...` both ship), or **with
 map-registered spelling**. **Compare on a normalised copy** and **return the real key** so
 the caller can erase it."
```

### ★★★★★ **`sound alias` 的两次扫描**（第 16869–16917 行）

```
① 配置串段（`SoundAliasConfigStringBase + 1 .. SoundAliasConfigStringCount`）
② ★ **CCS 常量串段**（`relativeIndex 0 .. SoundAliasEventParameterLimit - SoundAliasConstantStringBase`）
   ⇒ 返回值 = `SoundAliasConstantStringBase + relativeIndex`
```

★★★ **⇒ 第 ② 条的注释（第 16901 行）："**28800: sparse CCS chain -- a miss is not the end**"。**

### ★★★★★ **`resolveSoundAliasEventParameters` 不 gate 资产**（第 16817–16828 行，逐字）

```
"**CODREF(sound_alias_event): do NOT gate on the sound ASSET being loaded.** **The
 server's only job is to put an alias INDEX on the wire**; **the client owns playback and
 looks the asset up itself**. **A dedicated server loads no sound assets**, so
 **`findXAsset(AssetTypeSound, ...)` fails for every name and this filter emptied
 `unresolved` before either scan below could run** -- **which is why the resolver has NEVER
 answered on this build.** **MEASURED: 63 level loads, every one logging
 `sound=unavailable`, including the damage-feedback hit alert**, while **the material
 lookups beside it resolve fine (`material=125 killMaterial=144`)**. **The dm demo confirms
 the wire needs only a small index** -- its **98 sound events are eType 26
 (SoundAliasAsMaster) carrying 14/27**."
```

★★★ **⇒ 五个精确值：**
```
**63 次**关卡加载全部记 `sound=unavailable`
对照：`material=**125**` / `killMaterial=**144**`（能解析）
dm demo：**98 个声音事件**,eType **26**,值 **14/27**
```

### ★★★★★ **`collectServerSoundAliasAuditions` 的四个语言前缀**（第 16974–16978 行）

```cpp
if (prefix == "**ab_**" || prefix == "**uk_**" || prefix == "**za_**" || prefix == "**rb_**")
    continue;
```
★★★★★ **⇒ 完整注释（第 16947–16954 行，逐字）：**
```
"CCS type 5 is the networked sound alias pool -- **CCS_GetConstantString indexes a
 per-type list head table with stride 8, at VA `0x077D8188` HERE** (section 84; 3.3.3.3's
 is `0x02DF7CE8`, and that is the number this comment used to carry) -- and **1432 of its
 1507 entries carry ab_/uk_/za_/rb_ language prefixes, i.e. announcer voice-over**. Return
 the remainder."
```

★★★ **⇒ 四个精确值：**`0x077D8188`（头表）/ **1,432 / 1,507** 是语音 / 四个前缀。**

### ★★★★★ **`CCS_GetConstantString` 的 `[eax*8 + 0x77D8188]`**（第 17039–17044 行，逐字）

```
"**CCSGetConstantStringRva `0x261C50` puts the function at VA `0x00661C50`, whose body is
 instruction-for-instruction 3.3.3.3's `0x005851F0` with ONE operand changed:
 `mov eax, [eax*8 + 0x77D8188]` at `0x00661C53` against `[eax*8 + 0x2DF7CE8]` at
 `0x005851F3`. So the shape and the stride carry over and THE HEAD TABLE IS AT `0x077D8188`
 on this build.**"
```

### ★★★★★ **`resolveScriptAnimation` 的 0xFFF 上界**（第 16930 行）

```cpp
for (std::uint32_t key = 1; key <= **0xFFF**; ++key)
```
★★★ **⇒ CCS type **18**,上界 **0xFFF**（4,095）；`%` 前缀作为**次选**返回。**

### ★★★★★ **`auditAlphaBarrettAssetTemplates` 的六种资产**

```cpp
constexpr std::uint32_t MaterialAssetType = **5**;
constexpr std::uint32_t GfxImageAssetType = **10**;
constexpr std::size_t MaterialHeaderSize = **104**;
constexpr std::size_t MaterialNameOffset = **0x10**;
constexpr std::size_t MaterialTextureCountOffset = **0x51**;
constexpr std::size_t MaterialTextureTableOffset = **0x5C**;
constexpr std::size_t MaterialTextureRowSize = **12**;
constexpr std::size_t MaterialTextureSemanticOffset = **7**;
constexpr std::size_t MaterialTextureImageOffset = **8**;
constexpr std::uint8_t WaterSemantic = **11**;
constexpr std::size_t GfxImageHeaderSize = **52**;
constexpr std::size_t GfxImageLoadDefOffset = **0x2C**;
constexpr std::size_t GfxImageNameOffset = **0x30**;
constexpr std::size_t GfxImageLoadDefSize = **16**;
constexpr std::size_t GfxImageLoadDefDataSizeOffset = **0x0C**;
```

★★★★★ **⇒ 完整的 `Material` / `GfxImage` 布局：**

| 结构 | 偏移 | 字段 |
|---|---|---|
| **`Material`** | **`0x10`** | 名字指针 |
| | **`0x51`** | 纹理数（`u8`） |
| | **`0x5C`** | 纹理表指针 |
| | 每行 **12 字节** | `+7` semantic / `+8` image 指针 |
| **`GfxImage`** | **`0x2C`** | loadDef 指针 |
| | **`0x30`** | 名字指针 |
| | loadDef 内 **`+0x0C`** | dataSize |

★★★★★ **⇒ 完整注释（第 13598–13608 行，逐字）：**
```
"**CODREF(1649370): `Load_Material 0x00488250` reads a 104-byte header, with its asset
 name at `+0x10`, texture count at `+0x51`, and texture table at `+0x5C`. `Load_GfxImage
 0x00487380` reads a 52-byte header, resolves its name at `+0x30`, and `Load_GfxImageLoadDef
 0x00487300` reads the 16-byte load definition reached through `+0`. The renderer
 initializer `0x00BE7470` clears `+0` and retains that definition at `+0x2C`. Alpha
 `Load_GfxImage 0x004B2E30` instead reads 32 bytes and resolves its name at `+0x1C`.**"
```

★★★ **⇒ 三个 GfxImage 加载器：**
```
`0x00487380`（OLfinal）：**52 字节头**,名字 @ **`+0x30`**
`0x00487300`：**16 字节 loadDef**,经 **`+0`** 到达
`0x00BE7470`（渲染器）：**清 `+0`,把 loadDef 保留在 `+0x2C`**
`0x004B2E30`（alpha）：**32 字节头**,名字 @ **`+0x1C`**
```

### ★★★★★ **五个材质控制 + `detail_gray_01`**（第 13783–13789 行）

```cpp
static constexpr std::array<const char *, 5> Materials{
    "**mc/mtl_weapon_m16**",
    "**mc/mtl_weapon_acog_2_alpha**",
    "**mc/mtl_ret_acog02_acota31ncm_alpha**",
    "**mc/mtl_weapon_lens_eot_exps**",
    "**mc/mtl_wea_javelin_javelin_lens**",
};
```
★★★ **⇒ 五个材质 + 一个直接图像 **`detail_gray_01`**。**

### ★★★★★ **`opticCandidates` 的五个子串**（第 13723–13728 行）

```cpp
if (materialName.find("**scope**") == npos && materialName.find("**lens**") == npos &&
    materialName.find("**optic**") == npos && materialName.find("**thermal**") == npos &&
    materialName.find("**acog**") == npos && !alphaLensCounts)
    continue;
```
★★★ **⇒ 五个子串 + 一个结构判据 `alphaLensCounts`（`material[0x51]==3 && [0x52]==2 && [0x53]==4`）。**

### ★★★ **`auditXModelSurfaces` 的十一个偏移**

```cpp
XModelLod0ModelSurfsOffset       = **0x50**;
XModelSurfsSize                  = **0x30**;
XModelSurfsNameOffset            = **0x00**;
XModelSurfsSurfacesOffset        = **0x04**;
XModelSurfsCountOffset           = **0x08**;
XSurfaceSize                     = **0x54**;
XSurfaceVertCountOffset          = **0x04**;
XSurfaceTriCountOffset           = **0x06**;
XSurfaceBlendCountsOffset        = **0x14**;
XSurfaceBlendPointerOffset       = **0x1C**;
XSurfaceVertexPointerOffset      = **0x20**;
XSurfaceRigidListCountOffset     = **0x28**;
XSurfaceRigidListPointerOffset   = **0x2C**;
XSurfaceIndexPointerOffset       = **0x10**;
PackedVertexSize                 = **0x20**;
RigidVertListSize                = **0x0C**;
MaximumSurfaceCount              = **64**;
```

★★★ **⇒ **17 个常量**；混合权重公式（第 13535–13538 行）：**
```cpp
blendWordCount = blendCounts[0] + 3*blendCounts[1] + 5*blendCounts[2] + 7*blendCounts[3];
blendBytes = 2 * blendWordCount;
vertexBytes = vertCount * 0x20;
rigidListBytes = rigidListCount * 0x0C;
indexBytes = triCount * 6;
```

### ★★★★★ **`auditRig` 的八个字段**（第 13303–13315 行）

```cpp
const auto boneCount    = model[**4**];
const auto rootCount    = model[**5**];
const auto surfaceCount = model[**6**];
memcpy(&boneNames,        model + **44**, 4);
memcpy(&parents,          model + **48**, 4);
memcpy(&quaternions,      model + **52**, 4);
memcpy(&translations,     model + **56**, 4);
memcpy(&baseMatrices,     model + **64**, 4);
```

★★★ **⇒ 三个 `u8` 计数 + 五个指针。**
**⇒ `baseMatrices` 每骨 **8 个 float**（第 13333 行：`boneCount * 8 * sizeof(float)`）。**

---

## 十一、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★★★ **weapon registry 五阶段** | **1** reset / **2** walk / **3** default / **4** initialize / **5** verify；故障 **`20+pass`** / **`51`** / **`90+stage`** |
| 2 | ★★★ 八行失败日志 | 含 `Com_Error` 三全局（`0x31053DC` / `0x2FE7904` / `0x2FE7958`） |
| 3 | ★★★★★ 判据 | **`0x02F060` 读地址 0 = null WeaponDef 字符串**；**`0x0F82E0` 内 = Com_Error（引擎 raise）** |
| 4 | ★★★ 新 RVA | **`0x1588634`**（`PerWeaponAttachmentCountsRva` 之前 4 字节） |
| 5 | ★★★★★ **XAssetEntry 池** | **`0x1F9B120`** / **120,000 条 × 28 字节** / `+0` type / `+8` data / `+16` zone |
| 6 | ★★★★★ **zone 提升的理由** | DB_LinkXAssetEntry 用**当前 loading-zone 字节**（运行时为 0）⇒ 新 WeaponDef 变**默认占位符** ⇒ 原生解析器拒绝 |
| 7 | ★★★★ 代际哨兵 | **`viewmodel_barrett`** 消失 ⇒ **重建整个闭包** |
| 8 | ★★★★★ **15 秒流式等待** | `XModelSurfs +4/+8` + **`XModel +349` bit 3（`0x08`）** |
| 9 | ★★★ 六个资产结构 | Image（loadDef 16 + 头）/ Material（12B 纹理）/ Surfs（48B 头）/ Model（**360B 头**）/ Animation（**88B 头**） |
| 10 | ★★★★★ **XAnim 九个流** | 写入 `header + 48 + i*4`（i = 0..8） |
| 11 | ★★★★★ **XModel 十一个指针** | `0`/`44`/`48`/`52`/`56`/`60`/`64`/`68`/**`312`**/`72+lod*56+8`/`72+lod*56+12` |
| 12 | ★★★ 四个材质回退 | `mc/mtl_weapon_m16` / `mc/mtl_ret_acog02_acota31ncm_alpha` / `mc/mtl_weapon_lens_eot_exps` / `mc/mtl_weapon_acog_2_alpha` |
| 13 | ★★★ 四个匹配子串 | `reticle` / `lens` / `screen` / `acog` |
| 14 | ★★★ 材质常量前 4 字节 | 标识常量,**后 28 字节是 alpha 移植有意替换的值** |
| 15 | ★★★★★ **21 个 XAnim 槽** | 1,2,3,5,9,11,15,16,17,18,21,22,23,24,25,26,27,34,35,46,47（**9 个名字**）；`AnimationArrayOffset = 0x7C` |
| 16 | ★★★★★ **两个模型数组** | alpha：**`+0x14`/`+0x54`**（16 项）；OLfinal：**`+0x10`/`+0x14`**、**`+0x18`/`+0x1C`**（各 2 项） |
| 17 | ★★★★★ **客户端不改 type** | 专服 `*type = **19**`；客户端**直接 return true** |
| 18 | ★★★ 三个前缀 | `0x34BD10` `{55 8B EC 83 EC 14}` / `0x09A2B0` `{55 8B EC A1}` / `0x7E7470` `{8B 44 24 04 83 EC 20}` |
| 19 | ★★★★★ **`BaseWeaponAssetCount = 1300`** | 旧的 **`0x400` = 1024**（3.3.3.3）⇒ **1024 以上全部越界** |
| 20 | ★★★★★ 失败时全字符串 dump | 遍历 **40 字节**的每个 4 字节偏移,打印所有 `validBookingName` |
| 21 | ★★★★ `sf_weapon_m4_mp_name` 教训 | **本地化键不是武器名** ⇒ 不猜偏移,打印全部 |
| 22 | ★★★★★ **五重附件校验** | 名字 / model slot / registry `< 0x3FFF` / **翻译** / **严格支持测试** / 模型解析 |
| 23 | ★★★★★ **翻译的两遍** | 全表找 canonicalId 的 **model** ⇒ 目标武器里找同 **model** |
| 24 | ★★★ 四个 model 索引 | **两个 RMR = model 17** / **两个扩容弹匣 = model 10** / `mag_fast*` = **11** / `mag_fmj*` = **12** |
| 25 | ★★★ `MaximumAttachmentsPerWeapon` | **64**（`128 u16` = 64 对） |
| 26 | ★★★★★ **`sub_42F9B0` 五指令** | `v2 = byte_1988638[weapon]` / `if (!v2) return dword_198B8A0[word_19DDECC]` / `for (i = &word_198C0A0[128*weapon]; *i != attachment; i += 2)` / `if (++v3 >= v2) return NONE` / `return dword_198B8A0[i[1]]` |
| 27 | ★★★ `0x3FFD` vs `0x3FFF` | `internedAttachmentName` 用 **`>= 0x3FFD`**；另外两处用 **`>= 0x3FFF`** ⇒ **待核对** |
| 28 | ★★★★★ **`modularName` 格式** | **`** <base> 0 0 <att...>`** |
| 29 | ★★★★ 零售对照 | `** 682 0 0 9930 8738 6747 10545 9321 6690 6825` / `** 652 0 0 8738` / `** 249 0 0` |
| 30 | ★★★★★ **FMJ 规则** | 名字前缀 **`mag_fmj`** ⇒ `fmjPenetration = true` ⇒ **穿透 ×2** |
| 31 | ★★★★★ **`defaultsInTable` 实测** | **`0/1` / `0/4` / `1/3`**（`tableCount` 10..19）⇒ **键不匹配** |
| 32 | ★★★★★ 键的真相 | 低半是 **interned name id**（`sub_42F910` intern `dword_198B8A0[model]->name`）,不是附件索引 |
| 33 | ★★★★★ **1234 / 1154 陷阱** | 专服 reset 后 Barrett 从 **1234 → 1154**,客户端 **1154 是 `chicken_melee_mp`** |
| 34 | ★★★★★ **perk 位集** | **96 位 = 3 dword**,`ps+0x584 + 4*(i>>5)`,**`1 << (i & 31)`** |
| 35 | ★★★★★ **ability 掩码** | **192 位 = 6 dword**,**`0x80000000 >> (id & 31)`**（**位序相反**） |
| 36 | ★★★ `valueIndex` 上界 | **36** |
| 37 | ★★★ 12 个 modifier 对 | `mp/coAbilityModifiersTable.csv` 列 **15..26**（步长 2） |
| 38 | ★★★★★ 三个具名 modifier | `modMoveSpeedScale` / `modFallDamageScale` / `modKillstreakShift` |
| 39 | ★★★★ Fast Hands / Marathon | **1.5 / 1.6**；Marathon default **4** / delta **-7** / min **-1** |
| 40 | ★★★★★ **`publicProfileReady` 四重** | 可读 / `[0x1112C] != 0` / **`*(u32*)(+0x1008C) == 0x07FFFFFF`（相等）** / `*(i32*)(+116) == 0` |
| 41 | ★★★★★ 管理器不 deref | **`0x400000 + 0xE14BC48 + 0x10 = 0xE54BC58`** |
| 42 | ★★★★★ **12 是我们的上界** | 引擎只 **`if (index < 0) index = 0`** 然后**按 156 缩放** |
| 43 | ★★★★★ **`profileSlotProbeEnabled` 默认关** | 六个 `ClientException`,最内帧 **`sub_779510 +0x230`**,**三个早于本批次** |
| 44 | ★★★★★ **characterInfo 定位** | **`dword_827F730 + 1104 * clientNum + 717648`** |
| 45 | ★★★★★ **九个字段** | `pid` / `cs{}` / `req{}` / `valid` / `dobj(+900)` / `namePtr(+0x18)` / `rebuild(+660)` / `model` / `attach` |
| 46 | ★★★★★ **`req` 三态** | 全零 ⇒ **modelIndex 门 fired（线材故障）**；有值 ⇒ **物品表故障** |
| 47 | ★★★★★ **clientState 定位** | **`dword_827F730 - 503016`**,stride **`0x160`**,字段 **`+0x150`/`+0x7C`/`+0x14`** |
| 48 | ★★★★★ **电池崩溃** | `+0x0A4` 读后 **`0xC0000005`**；回退后无故障 ⇒ **读是主嫌** |
| 49 | ★★★ 为何不安全 | **游戏线程外**,循环只守护**前 32 字节**,**读 164 字节深处 = check-then-use 竞态** |
| 50 | ★★★★★ 缓冲池 | **`0x0044B310`/`0x004555D0`**,19+18 块 × 1104,每块 25 个 64B,memset **`0xE740` = 37×1600** |
| 51 | ★★★★★ **`tag_` 在附件槽** | `0x00541800` 第二循环**偏一槽**,把 tag 字符串写进附件模型槽 |
| 52 | ★★★★★ **`resolveGlassMapMetadata` 六校验** | `definitionCount ≤ 1024` / `pieceLimit ≤ 2048` / `initialPieceCount ≤ 1024` / `initialPieceCount ≤ pieceLimit` / **两条关系** / 可读 |
| 53 | ★★★ 六个 piece 字段校验 | quaternion / origin / texCoord / radius≥0 / doubledArea≥0 / definitionIndex < count |
| 54 | ★★★★★ **capsule ABI 对照** | 3.3.3.3 `0x0058B330` vs 1649370 `0x00668560`：arg4/arg5/ECX/end **四处不同** |
| 55 | ★★★★★ **brush ABI 对照** | 3.3.3.3 `0x0058B230` vs 1649370 `0x00668470`：arg1/arg6/ECX/EDX **四处不同** |
| 56 | ★★★★★ 后果 | **"CARRYING 3.3.3.3's FORM HANDED THE CALLEE A 12-BYTE vec3 AS ITS 40-BYTE RESULT BUFFER"** |
| 57 | ★★★ 四路实测 | out.exe `0x0046DC81`/`0x0046E3F6`；3.3.3.3 `0x005FB4D1`/`0x00458DCE` |
| 58 | ★★★★★ **`traceWorld` ABI** | **`EDI = end` / `EDX = mask` / 4 栈参数** |
| 59 | ★★★ `invokePointTraceStaticModels` | **`EDI = output` / `EDX = mask` / `ECX = end` / 1 栈参数** |
| 60 | ★★★★★ **慢 trace 实测** | `0x266938`（**递归 clipmap 下降**,唯一调用者是它自己）/ **199,217 µs** / **111,549 µs** / **459,473 µs** |
| 61 | ★★★ 慢 trace 阈值 | `slowMicroseconds = **50'000**` / `reportLimit = **16**` |
| 62 | ★★★ TRACE CENSUS | **5 秒窗口** + `verbose()` 门禁 |
| 63 | ★★★★★ **本 build 无 `SV_Trace`** | 3.3.3.3 的 `0x005FB940`（1 调用者）→ `0x0058D500`/`0x0058D790` → `0x005FB390`/`0x005FB510`（stride `0x2C8`） |
| 64 | ★★★★★ **`0x0046E780` 是通用 trace** | 37 调用者 vs 24；叶子 `0x0046DCF0` 与客户端 `0x00458E40` **319/319 逐指令相同**,与服务端 `0x0058D200` 只有 **6%** |
| 65 | ★★★★★ **客户端 centity 数组** | `dword_1C1D188[dword_82C3B60] ^ 0x2168F672`,stride **`0x270`**,entityState @ **`+0xF4`** |
| 66 | ★★★ 两个共享 clip 的调用者 | 3.3.3.3 各 **4** / 本 build 各 **2** ⇒ **消失的两个是服务端 clip** |
| 67 | ★★★★★ 结论 | **"the entity half of every capsule query on this server was dead"** |
| 68 | ★★★★★ **`SV_PointTraceToEntity 0x005FB510`** | gentity stride **`0x2C8`** from **`0x03150048`**；`svFlags` bit 2 @ **`+0x112`**；`currentOrigin +0x148`；`currentAngles +0x154`；法线旋转 @ **`0x005FB7DC`** |
| 69 | ★★★★★ **`result.fraction` 必须播种** | `0x0046E1FC` 载入 running best ⇒ 留 0 则**永不报告命中** |
| 70 | ★★★ 法线回世界 | `axis` 的**列**线性组合（转置应用） |
| 71 | ★★★ 六个拒绝原因 | `request-invalid` / `not-game-thread` / `entity-mirror-mismatch` / `no-priority-map` / `world-trace-failed` / `anim-condition-storage`（上限 **12**） |
| 72 | ★★★★ `actor_skeletal_precedence` | 已摆姿的 actor **不得**被更近的宽胶囊覆盖 |
| 73 | ★★★★★ **三个 gentity 偏移** | `+0x110` isLinked / `+0x112` svFlags / `+0x12C` contents |
| 74 | ★★★★★ 实测症状 | `linked=1` / `maxsZ=70` / 射线偏轴 **2.5 单位** / 整弹匣无命中（**死亡前命中 103 单位**） |
| 75 | ★★★★★ **`validateMessageBindings` 三段** | `MSG_WriteBits(0x78, 8)` ⇒ cursize 1/bit 8；`"codol"` ⇒ cursize 6；gamestate 缓冲 **512** |
| 76 | ★★★ 512 的理由 | **serverinfo 十键 + gamestate ~277 字节**；256 时**因空间不足而失败** |
| 77 | ★★★ `timescale` | **`0 0 1 1`** |
| 78 | ★★★ `OLMOD_PERF_BASELINE` | 抑制 vision 配置串 ⇒ **跳过字节比较**（**曾让专服崩过一次**） |
| 79 | ★★★★★ **`readMapEntityString` 两候选** | **`AssetTypeMapEnts = 19`** `.d3dbsp` / **`AssetTypeAddonMapEnts = 42`** `.mapents` |
| 80 | ★★★★★ 实测两例 | `mp_nuked` 只有 `.d3dbsp` / `coop_training_mp_cargoship` 只有 `.mapents` |
| 81 | ★★★★★ 只建 `.d3dbsp` 的后果 | **每个 coop 关卡返回 nullopt** ⇒ `world spawn pending stage=map_entity_asset` ⇒ **`spawn refused ... NO_SPAWN_POINT`** |
| 82 | ★★★ trigger 三上限 | **4096** / **65535** / **65535** |
| 83 | ★★★ trigger 三结构 | Model **8B** / Hull **32B** / Slab **20B** |
| 84 | ★★★ `BrushModelCountOffset` | **`0x90`** / **`0x94`**；`NativeBrushModel` **72B**（`+0x24`/`+0x28`） |
| 85 | ★★★ `DirectionCount` | **162**（`0xA51C70`） |
| 86 | ★★★★★ **script-string 池** | **`0x749C524`**,`pool + 20*id + 4`；**`j_neck` = bone 20** / **`j_spinelower` = bone 5** |
| 87 | ★★★★★ **XAnim notify 六偏移** | `+27` count / `+14` frames / `+40` rate / `+80` markers；每 marker **8B**；`seconds = normalized*frames/rate` |
| 88 | ★★★ notify 池 | **`0x0749C524`**（**同一个池**）,`pool + 20*id + 4` |
| 89 | ★★★★★ **`resolveScriptModelAnimationTree`** | 计数 **`0x749C634`**（≤64）/ 定义 **`0x749C534`** / `definition[10]` wireId（≤31）/ `definition[0..3]` nodeCount（≤4096）/ `definition+4` BST 根 / 子指针 **`key>alias ? +4 : +8`** / 深度 **64** |
| 90 | ★★★ 歧义处理 | **歧义 ⇒ `return nullopt`** |
| 91 | ★★★★★ **`resolveWeaponConfigStringIndex` 修复** | 单次 **165–300 ms** / `lookupUs=1184729` / `lookupCalls=4` / **11 人机 8–13 s** |
| 92 | ★★★ 代际哨兵 | **`nativeConfigString(WeaponConfigStringBase + 1)`** |
| 93 | ★★★★ 声音别名的三源差异 | `%` 前缀 / 大小写 / 地图注册拼写 ⇒ **归一化比较** |
| 94 | ★★★★★ **不 gate 声音资产** | **63 次关卡加载全部 `sound=unavailable`**；对照 `material=125`/`killMaterial=144`；dm demo **98 个 eType 26,值 14/27** |
| 95 | ★★★★★ **CCS 头表 `0x077D8188`** | stride **8**；**1,432 / 1,507** 是语音；四个前缀 `ab_`/`uk_`/`za_`/`rb_` |
| 96 | ★★★ `resolveScriptAnimation` | CCS type **18**,上界 **`0xFFF`**,`%` 前缀作次选 |
| 97 | ★★★★★ **Material 三偏移** | **`0x10`** 名 / **`0x51`** count / **`0x5C`** 表；每行 **12B**（`+7` semantic / `+8` image） |
| 98 | ★★★★★ **GfxImage 三偏移** | **`0x2C`** loadDef / **`0x30`** 名 / loadDef **`+0x0C`** dataSize |
| 99 | ★★★★★ **三个 GfxImage 加载器** | OLfinal `0x00487380`（**52B** 头,名 @ `0x30`）/ `0x00487300`（16B loadDef）/ **alpha `0x004B2E30`（32B 头,名 @ `0x1C`）** |
| 100 | ★★★ 五个材质 + 一个图像 | `mc/mtl_weapon_m16` / `acog_2_alpha` / `ret_acog02_acota31ncm_alpha` / `lens_eot_exps` / `wea_javelin_javelin_lens` + **`detail_gray_01`** |
| 101 | ★★★ 五个 optic 子串 | `scope` / `lens` / `optic` / `thermal` / `acog`；结构判据 `[0x51]==3 && [0x52]==2 && [0x53]==4` |
| 102 | ★★★ **XSurface 17 常量** | `0x50`/`0x30`/`0x00`/`0x04`/`0x08`/`0x54`/`0x04`/`0x06`/`0x14`/`0x1C`/`0x20`/`0x28`/`0x2C`/`0x10`/`0x20`/`0x0C`/`64` |
| 103 | ★★★ 混合权重公式 | `blendCounts[0] + 3*[1] + 5*[2] + 7*[3]`；`blendBytes = 2 * words`；`indexBytes = triCount * 6` |
| 104 | ★★★ **`auditRig` 八字段** | `model[4]` bones / `model[5]` roots / `model[6]` surfaces / `+44`/`+48`/`+52`/`+56`/`+64` |
| 105 | ★★★ baseMatrices 尺寸 | 每骨 **8 个 float** |

---

## 十二、结论

### 1. ★★★★★ **`weapon registry` 重建是**七步 1:1 复刻**游戏自己的流程,含五个阶段码与八行日志**

### 2. ★★★★★ **Alpha 武器的 `XAssetEntry` 池是 `120,000 × 28`,而 zone 字节决定"默认占位符"**

★ **⇒ 必须从源资产的 zone **提升**（`assetZoneForHeader` 全扫 120,000 条）。**

### 3. ★★★★★ **Barrett 闭包有 15 秒流式等待,判据是 `XModel +349` bit 3**

★ **⇒ 不等就会**两个加载器看到同一个 null `XModelSurfs` 指针**。**

### 4. ★★★★★ **21 个 XAnim 槽 + 两个模型数组的偏移变化（`0x14/0x54` → `0x10/0x18`）**

### 5. ★★★★★ **`resolveWeaponItem` 是 12 步链,其中附件有**五重校验**与**两遍翻译****

★ **⇒ 翻译靠 **model 索引**（两个 RMR 都是 17）,因为 id 随武器变。**

### 6. ★★★★★ **`defaultsInTable = 0/1, 0/4, 1/3` 揭示"我们算的键不是它们存的键"**

★ **⇒ 低半是 **interned name id**（模型名）,不是附件索引。**

### 7. ★★★★★ **Barrett 的 1234 / 1154 陷阱是"两个进程的注册表在 reset 后分叉"**

### 8. ★★★★★ **perk 96 位与 ability 192 位的**位序相反**（`1<<(i&31)` vs `0x80000000>>(id&31)`）**

### 9. ★★★★★ **`publicProfileReady` 的 chunkMask 用**相等**而非掩码测试**（"多出的位 = 未就绪"）

### 10. ★★★★★ **`reportClientCharacterInfo` 的九个字段能区分**线材故障**与**物品表故障****

★ **⇒ 且**电池读取曾让客户端崩溃**,已撤回。**

### 11. ★★★★★ **三个 trace ABI 各差四处,其中 brush 的旧形式把 12 字节 vec3 当 40 字节结果缓冲**

### 12. ★★★★★ **本 build **没有 `SV_Trace`**,实体半边全靠本项目自己实现**

★ **⇒ 通用 trace 的叶子与 3.3.3.3 的**客户端**叶子 319/319 逐指令相同,与服务端只有 6% 相似。**

### 13. ★★★★★ **`resolveWeaponConfigStringIndex` 的 165–300 ms × 11 人机 = 8–13 s 卡顿已修**

### 14. ★★★★★ **`readMapEntityString` 的两个资产类型（19 `.d3dbsp` / 42 `.mapents`）**

★ **⇒ 只建一种 ⇒ **每个 coop 关卡都渲染出地图但玩家站不进去**。**

---

## 十三、`EngineBindings.cpp` 全文完成总账

| 项 | 值 |
|---|---|
| **字节** | **917,344** |
| **行数** | **17,867** |
| **报告** | **134**（1–7,600）/ **135**（7,601–11,600）/ **136**（11,601–17,867） |
| **`static_assert` 数** | 约 **30** |
| **RVA 常量** | 约 **200**（报告 133 已分类） |
| **前缀守卫** | **60+** |
| **`__try` / `__except`** | 约 **50 处** |
| **原生调用适配器** | 约 **40 个**（`invoke*` / `try*`） |
| **诊断/审计函数** | **14 个**（`audit*` / `report*` / `probe*` / `log*`） |
| **环境变量** | 约 **20 个**（`OLMOD_*`） |

---

## 十四、下一步

`game_server` 根剩余：

1. ★ **`Appmain.cpp`（565,999 B / **10,564 行**）**
2. 然后 `server_mp` 154 文件（12,604,630 B）
3. 然后 `localnetworking` 6 / `platformwrapper` 7 / `client_bridge` 2 / `win32` 2
4. 然后 `source\` 非 `src`（`docs` 75 / `tools` 148 / `assets` 55 / `tests` 24 / `distribution` 7 / `.agents` 59 / `references` 12 / 根 14）
