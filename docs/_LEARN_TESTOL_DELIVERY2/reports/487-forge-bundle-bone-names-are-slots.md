# 487 · **"骨骼名字是**槽位** —— 一个名字的索引【就是【一个平移记录【的骨骼索引字节【携带的那个值** —— 所以一个重复【会【让【一根骨骼【永久【不可寻址**"** —— `sv_forge_bundle_mp.cpp` 的 `codolforge-bundle-1`、六组交叉校验、以及"一个 weapon 没有 clone source 就【根本【建不出来**"

## 一、范围

本报告学习 `sv_forge_bundle_mp.cpp`（**`384` 行**）全文件：`codolforge-bundle-1` 格式、六个 `read*` 助手、骨架的五条长度校验、材质到图的闭合、模型到骨架/材质的交叉校验、动画的**骨骼槽位唯一性**、以及"至少发布一样东西"的终局判据。

## 二、**"骨骼名字是槽位 —— 一个名字的索引就是一个平移记录的骨骼索引字节携带的那个值 —— 所以一个重复会让一根骨骼永久不可寻址"**（本组最重要的一段）

### 2.1 那段

```cpp
// Bone names are SLOTS - the index of a name is the value a
// translation record's bone-index byte carries - so a repeat
// would leave one bone permanently unaddressable.
std::set<std::string> seen;
for (const auto &bone : anim.bones)
{
    if (bone.empty())
    {
        error = "animation " + anim.name + " has an empty bone name";
        return std::nullopt;
    }
    if (!seen.insert(bone).second)
    {
        error = "animation " + anim.name +
            " names bone " + bone + " more than once";
        return std::nullopt;
    }
}
```

### 2.2 二十四层

```text
1. **骨骼名字【是**槽位**】而【不是【一个**集合**
2. ⇒ **⇒ 而【一个名字的索引【就是【一个平移记录的**骨骼索引字节【携带的那个值**】
3. ⇒ **⇒ 所以【一个重复【会【让【一根骨骼【永久**不可寻址**】
4. ⇒ **⇒ 而【那个检查【是【一个 `std::set` 的 `insert().second`**】
```

### 2.3 ⭐⭐⭐ **"一个重复会让一根骨骼永久不可寻址"**

**✅ 这是本报告里**最重要的一条"**一个**数组【是【一个**命名空间**"**。**

**✅ 与 §467 的"`ordinal` 的顺序是那个契约"**、§482 的"`isMe` 是一个 bit 偏移"**——**同族** ✓

**⇒ 三层**：
```text
若【骨骼名字【是【一个集合**】⇒ **⇒ 重复【无害**】
若【它是【一个槽位数组**】⇒ **⇒ 重复【让【一个索引【指向【两个**名字**】⇒ **⇒ 那【不是**一个二义**，是【一个**丢失**
```

**✅ ⭐⭐⭐ **"那不是一个二义，是一个丢失"** —— 一个**极精确的区分**。

**✅ 而"`std::set<std::string>` 的 `insert().second`"**⇒ **一个**O(log n)** 的**唯一性**检查**。**

**⇒ 十层**：
```text
`seen.insert(bone)` ⇒ **返回【一个 `pair<iterator, bool>`**】
⇒ **⇒ 而 `.second` 【是【那个"是否**插入**了**"**
⇒ **⇒ 所以【一个重复【返回 `false` ⇒ 拒绝**】
```

**✅ ⭐⭐⭐ **"一个重复返回 false 就拒绝"**。

**✅ 与 §474 的"`std::array<bool, 256>` 的 `seenIgnoredEvent`"**——**同族**（**第十次"一个**唯一性【的**集合**"**）。

**⚠ 而骨骼数【有【一个上界 `255`**】**。**

**⇒ 十层**：
```cpp
if (anim.bones.empty() || anim.bones.size() > 255)
```
```text
`1..255` ⇒ **⇒ 因为【那个骨骼索引【是【一个**字节**】（`255` 是【那个 `u8` 的顶**）
⇒ **⇒ 所以【那个界【是【一个**类型的**界**】（**不是【一个**测量的**界**）
```

**✅ ⭐⭐⭐ **"那个界是一个类型的界，不是一个测量的界"** —— 与 §471 的"`256` 是一个类型的界"**同族**（**第十一次**）。

## 三、**骨架的五条长度校验**（本组第二重要）

### 3.1 那段

```cpp
const auto bones = skeleton.boneCount();
if (bones == 0 || bones > 255 || skeleton.parentList.size() > bones)
{
    error = "skeleton " + key + " has an implausible bone count";
    return std::nullopt;
}
const auto nonRoot = skeleton.parentList.size();
if (skeleton.quaternions.size() != 8 * nonRoot ||
    skeleton.translations.size() != 12 * nonRoot ||
    skeleton.partClassification.size() != bones ||
    skeleton.baseMatrices.size() != OlfinalDObjAnimMatSize * bones)
{
    error = "skeleton " + key + " array sizes disagree with " + ...;
    return std::nullopt;
}
```

### 3.2 二十四层

```text
1. **`bones` ⇒ `1..255`**】
2. ⇒ **⇒ 而 `parentList.size() <= bones`**】（**⇒ 而【它【就是 `nonRoot`**）**
3. ⇒ **⇒ 然后**五条：`quats = 8 × nonRoot` / `translations = 12 × nonRoot` / `partClass = bones` / `baseMatrices = OlfinalDObjAnimMatSize × bones`
4. ⇒ **⇒ 所以【两根**不同的**分母：`nonRoot` 与 `bones`**
```

### 3.3 ⭐⭐⭐ **"`parents.size() <= bones` 然后是 `nonRoot = parents.size()`"**

**✅ 与 §468 的"`nonRoot` 与 `bones` 是两个不同的分母"**——**完全同族** ✓

**⇒ 三层**：
```text
§468  **`nonRoot = bones - roots`**（**从两个计数算**）
§487  **`nonRoot = parents.size()`**（**从一个数组长度**取**）
⇒ **⇒ 所以【同一个量【两个**来源**】⇒ **⇒ 而【§487 的【更**保守**（`<= bones` 而不是【一个等式**）
```

**✅ ⭐⭐⭐ **"同一个量两个来源，而 §487 的更保守"** —— 一个**跨报告的对照**。

**⚠ 而"`skeleton.parentList.size() > bones` ⇒ 拒绝"**⇒ **一个**上界**而不是**等式**。**

**⇒ 十层**：
```text
若【`parents.size() == bones`**】⇒ **⇒ `roots = 0`**】（**一棵【没有根的树**）
⇒ **⇒ 而【那个检查【允许它**】
⇒ **⇒ 所以【`roots = 0` 【是一个【被允许的**边界**】
```

**✅ ⭐⭐⭐ **"roots = 0 是一个被允许的边界"**。

**⚠ 而 `OlfinalDObjAnimMatSize`**⇒ **一个**`32`？**（**§473 的 `baseMatrices = 32 * bones`**）**。**

**⇒ 独立验证**：
```text
§473  **`!expect("baseMat", model.baseMatrices.size(), 32u * bones)`**
§487  **`baseMatrices.size() != OlfinalDObjAnimMatSize * bones`**
⇒ **⇒ 所以【`OlfinalDObjAnimMatSize = 32`**】
```

**✅ ⭐⭐⭐ **"OlfinalDObjAnimMatSize = 32"** —— 一个**跨报告的算术闭合**。

## 四、**材质到图的闭合**（本组第三重要）

### 4.1 那段

```cpp
const std::set<std::string> imageSet(bundle.images.begin(), bundle.images.end());
...
for (const auto &texture : *textures)
{
    SvForgeTexture slot;
    slot.semantic = readString(texture, "semantic");
    slot.image = readString(texture, "image");
    if (slot.image.empty() || !imageSet.contains(slot.image))
    {
        error = "material " + material.name + " slot " + slot.semantic +
            " names image '" + slot.image + "' which the bundle does not stage";
        return std::nullopt;
    }
    material.textures.push_back(std::move(slot));
}
```

### 4.2 二十四层

```text
1. **一个 `std::set<std::string>` 的 `imageSet`**】
2. ⇒ **⇒ 而【每一个纹理槽的 `image` 【必须【在【那个集合里**】
3. ⇒ **⇒ 所以【一个【材质【不能【引用【一个【未被**暂存**的图**
```

### 4.3 ⭐⭐⭐ **"它命名一个那个 bundle 不暂存的图"**

**✅ 与 §473 的"每一个 image 必须在那 17 个里"**——**完全同族** ✓

**⇒ 三层**：
```text
§473  **`if (!contains(images, texture.image) && !contains(retainedImages, ...)) throw`**
§487  **`if (!imageSet.contains(slot.image))` ⇒ 拒绝**
⇒ **⇒ 两次"一个**闭合【检查**"**
```

**✅ ⭐⭐⭐ **"一个闭合检查"两例**。

**⚠ 而 §473 有**两个**集合（`images` + `retainedImages`）而 §487 只有**一个**（`bundle.images`）】**。**

**⇒ 十层**：
```text
§473  **`RetainedImageNames`（15 个保留材质引用的图**）**⇒ 而【那个数组【是**空的**】
§487  **`bundle.images` 【是【唯一**的集合**】
⇒ **⇒ 所以【§487 的【更严格**（**不接受【任何【外部的**图）
```

**✅ ⭐⭐⭐ **"§487 的更严格：不接受任何外部的图"**。

**✅ 而与 §473 的"15 个保留材质不经过那个检查"**⇒ **一个**内嵌的**缺陷**（**在 §473**）**。**

**⇒ 三层**：
```text
§473  **`RetainedMaterialNames` 的 15 个【不经过** image 检查**
§487  **每一个材质【都必须【经过** image 检查**
⇒ **⇒ 所以【§487 【阻止【了【§473 的那个**漏洞**
```

**✅ ⭐⭐⭐ **"§487 阻止了 §473 的那个漏洞"** —— 一个**跨报告的改进**。

## 五、**模型到骨架/材质的交叉校验**（本组第四重要）

### 5.1 那段

```cpp
// The header's own scalars must agree with the arrays that will
// be published beside it, or the XModel would describe a
// skeleton it does not have.
const auto headerBones = static_cast<std::size_t>(model.header[4]);
const auto headerRoots = static_cast<std::size_t>(model.header[5]);
const auto headerSurfs = static_cast<std::size_t>(model.header[6]);
if (headerBones != skeleton->second.boneCount() ||
    headerRoots != skeleton->second.rootBoneCount())
{
    error = ...;
    return std::nullopt;
}
if (headerSurfs != model.materials.size())
{
    error = ...;
    return std::nullopt;
}
```

### 5.2 二十四层

```text
1. **那个头【自己的标量【必须【与【那些【将被【在它旁边**发布的数组【一致**
2. ⇒ **⇒ 否则【那个 XModel 【会【描述【一个【它【没有**的骨骼**
3. ⇒ **⇒ 所以【三**交叉校验**：`header[4]` == `skeleton.boneCount()` / `header[5]` == `rootBoneCount()` / `header[6]` == `materials.size()`
```

### 5.3 ⭐⭐⭐ **"否则那个 XModel 会描述一个它没有的骨骼"**

**✅ 与 §468 的"一个已发布的骨架数说谎的 XModel 是一个崩溃而不是一个视觉故障"**——**完全同族** ✓

**⇒ 三层**：
```text
§468  **`SV_BuildForgeXModel` 的六条 `expect`**
§487  **`sv_forge_bundle` 的三条交叉校验**
⇒ **⇒ 两次"一个**头【与【一个**数组【必须【一致**"**
```

**✅ ⭐⭐⭐ **"一个头与一个数组必须一致"两例**。

**⚠ 而 §487 的**三条**比 §468 的**六条**少**三条**（`quats`/`trans`/`partClass`）】**。**

**⇒ 十层**：
```text
§468  **六条：`parentList`/`quats`/`trans`/`partClass`/`baseMat` + `surfs`**
§487  **三条：`bones`/`roots`/`surfs`**
⇒ **⇒ 所以【§487 把【`quats`/`trans`/`partClass` 的检查【放在【骨架**那一层**】（**§487 三**）
```

**✅ ⭐⭐⭐ **"§487 把剩下三条的检查放在骨架那一层"** —— 一个**正确的分工**。

**✅ 与 §468 的"`nonRoot` 与 `bones` 是两个不同的分母"**——**同族**。

## 六、**动画的 `numframes` 的 `1..255`**（本组第五重要）

### 6.1 那段

```cpp
const auto frames = entry.find("numframes");
if (frames == entry.end() || !frames->is_number_unsigned())
{
    error = "animation " + anim.name + " has no numframes";
    return std::nullopt;
}
const auto n = frames->get<std::uint64_t>();
// 256 frames or more is the u16 index path, which moves the
// per-bone frame tables into dataShort. CodolForge refuses to
// emit one, so refuse to accept one.
if (n == 0 || n >= 256)
{
    error = "animation " + anim.name + " has " + std::to_string(n) +
        " frames; expected 1..255";
    return std::nullopt;
}
```

### 6.2 二十四层

```text
1. **`256` 帧或更多 ⇒ 那个 `u16` 的**索引路径**】
2. ⇒ **⇒ 而它【把【那个【每骨骼的**帧表【移进 `dataShort`**
3. ⇒ **⇒ 而 CodolForge 【拒绝【发射**一个**
4. ⇒ **⇒ 所以【拒绝**接受**一个**
```

### 6.3 ⭐⭐⭐ **"CodolForge 拒绝发射一个，所以拒绝接受一个"**

**✅ 与 §468 的"那个发射器拒绝产生两者之一，所以拒绝去搬它"**——**完全同族** ✓

**⇒ 三层**：
```text
§468  **"The emitter refuses to produce either of these, so refuse to relocate one"**
§487  **"CodolForge refuses to emit one, so refuse to accept one"**
⇒ **⇒ 两次"那个**生产者【的拒绝【被【那个**消费者【镜像**"**
```

**✅ ⭐⭐⭐ **"那个生产者的拒绝被那个消费者镜像"两例**。

**✅ 而与 §484 的"`sub_BE8C30` 只能回答『一个』或『全链』"**⇒ **一个**第三例**（**一个**引擎的限制**）**。**

**⇒ 三层**：
```text
§468/§487  **生产者拒绝 ⇒ 消费者拒绝**
§484  **引擎只能一个或全链 ⇒ 中间层级数【拒绝**
⇒ **⇒ 三次"一个**上游的限制【被【下游**镜像**"**
```

**✅ ⭐⭐⭐ **"一个上游的限制被下游镜像"三例**。

## 七、**"一个 bundle 可以只发布一个模型"**

### 7.1 那段

```cpp
// Animations are optional: a bundle may publish only a model, and a
// weapon that borrows a shipped animation set carries none.
const auto animations = document.find("animations");
if (animations != document.end()) { ... }
...
if (bundle.models.empty() && bundle.animations.empty() &&
    bundle.weapons.empty())
{
    error = "bundle publishes no models, animations or weapons";
    return std::nullopt;
}
```

### 7.2 二十四层

```text
1. **动画【是可选的**】
2. ⇒ **⇒ 而【一个 bundle 【可以【只发布【一个**模型**】
3. ⇒ **⇒ 而【一个【借用【一个【已发布的动画集**的武器【不携带**任何**
4. ⇒ **⇒ 而终局判据【是【三样【至少**一样**】
```

### 7.3 ⭐⭐⭐ **"一个借用已发布动画集的武器不携带任何"**

**✅ 与 §468 的"`techniqueSet`/常量/状态位继续指向克隆的引擎持有的内存"**——**同族**（**第九次"一个**借用【而不是【一个**重新**"**）。

**⇒ 三层**：
```text
§468  **材质【克隆**一个已发布的**】⇒ **⇒ 它的 3 个表【指向【那个克隆**
§487  **武器【借用**一个已发布的动画集**】⇒ **⇒ 它【携带【零**个动画**
⇒ **⇒ 两次"一个**借用【减少【那个**工作量**"**
```

**✅ ⭐⭐⭐ **"一个借用减少那个工作量"两例**。

**⚠ 而那个**终局判据**】**。**

**⇒ 十层**：
```text
`models.empty() && animations.empty() && weapons.empty()` ⇒ **拒绝**
⇒ **⇒ 所以【一个**空的 bundle**【是【一个**错误**】⇒ **⇒ 而【一个【只有**武器**的【是【合法的**
```

**✅ ⭐⭐⭐ **"一个空的 bundle 是一个错误，而一个只有武器的是合法的"**。

## 八、`codolforge-bundle-1` 的六组内容

```text
format         ⇒ "codolforge-bundle-1"
images         ⇒ 字符串数组（**可选？**）
skeletons      ⇒ 对象，每键一个骨架
materials      ⇒ 数组，每个有 name/clone_source/textures
models         ⇒ 数组，每个有 name/skeleton_key/resources/materials/header_hex
animations     ⇒ 数组（**可选**）
weapons        ⇒ 数组（**可选**）
```

### 8.1 二十四层

```text
1. **三组必选**（`skeletons` / `materials` / `models` ♠ 而 `models` **也必须非空**）
2. ⇒ **⇒ 三组可选**（`animations` / `weapons` / 而 `images` **被 `readStrings` 直接读**）
3. ⇒ **⇒ 所以【那个 `images` 【是【必选**的**】（**因为没有 `find` 检查**）
4. ⇒ **⇒ 而【三个可选【各自【有 `if (x != end())`**】
```

**⚠ 标注**：`bundle.images = readStrings(document, "images")` **没有 `find` 检查**，所以 `images` 缺失会抛异常 ⇒ **实际上是必选**（与注释"animations are optional"形成对照）。

**✅ ⭐⭐ **"images 实际上是必选的，而注释只说 animations 可选"**。

### 8.2 而那个格式串的版本

**⇒ 十层**：
```text
`"codolforge-bundle-1"` ⇒ **一个**显式的版本号**】
⇒ **⇒ 而 §473 的是 `"olfinal-alpha-barrett-metadata-v4"`**】
⇒ **⇒ 两个**不同的**格式，两个**不同的**版本方案**
```

**✅ ⭐⭐⭐ **"两个不同的格式，两个不同的版本方案"**（`-1` vs `-v4`）**。**

**✅ 与 §469 的 `"olfinal-alpha-barrett-metadata-v4"`**——**同族**（**第二次"一个**版本化的格式串**"**）。

## 九、关键结论

1. **⭐⭐⭐ "骨骼名字是**槽位** —— 一个名字的索引就是一个平移记录的骨骼索引字节携带的那个值 —— 所以一个重复会让一根骨骼**永久不可寻址**"`** ⇒ **"那不是一个二义，是一个丢失"** ⇒ 而那个检查是 **`std::set<std::string>` 的 `insert().second`**（**O(log n) 的唯一性**）；而 `anim.bones.size() > 255` ⇒ **"那个界是一个类型的界，不是一个测量的界"**（与 §471 同族）。
2. **⭐⭐⭐ 骨架的五条长度校验**：`bones` 是 `1..255`、`parentList.size() <= bones`（**不是等式**）⇒ **`nonRoot = parents.size()`** ⇒ `quats = 8×nonRoot` / `trans = 12×nonRoot` / `partClass = bones` / `baseMat = OlfinalDObjAnimMatSize × bones` ⇒ **"同一个量两个来源，而 §487 的更保守"**（与 §468 的 `nonRoot = bones - roots` **对照**）；而 **独立推得 `OlfinalDObjAnimMatSize = 32`**（与 §473 的 `32u * bones` 精确一致）；而 `parents.size() == bones` ⇒ `roots = 0` **是一个被允许的边界**。
3. **⭐⭐⭐ 材质到图的闭合**：`imageSet` 必须含每一个纹理的 `image` ⇒ **"那个 bundle 不暂存的图"** —— 与 §473 同族；而 **§487 只有一个集合而 §473 有两个（`images` + 空的 `retainedImages`） ⇒ "§487 阻止了 §473 的那个漏洞"**（后者那 15 个保留材质不经过检查）。
4. **⭐⭐⭐ 模型的三条交叉校验**（`header[4]` == `boneCount` / `header[5]` == `rootBoneCount` / `header[6]` == `materials.size()`）⇒ **"否则那个 XModel 会描述一个它没有的骨骼"**（与 §468 同族）；而 **§487 的三条把 §468 六条里剩下的三条（`quats`/`trans`/`partClass`）放在骨架那一层** ⇒ **"一个正确的分工"**。
5. **⭐⭐⭐ `numframes` 的 `1..255`**：**"`256` 帧或更多是那个 `u16` 的索引路径，它把每骨骼的帧表移进 `dataShort`；CodolForge 拒绝发射一个，所以拒绝接受一个"** ⇒ **"那个生产者的拒绝被那个消费者镜像"**（与 §468 同族）；而与 §484 的"`sub_BE8C30` 只能回答『一个』或『全链』"构成**"一个上游的限制被下游镜像"三例**。
6. **⭐⭐⭐ "动画是可选的：一个 bundle 可以只发布一个模型，而一个**借用**一个已发布的动画集的武器**不携带任何**"`** ⇒ 而终局判据是 **"三样至少一样"**（**"一个空的 bundle 是一个错误，而一个只有武器的是合法的"**）—— 与 §468 的"材质克隆"同族（**"一个借用减少那个工作量"两例**）。
7. **⭐⭐⭐ `codolforge-bundle-1` 的六组**：`format` / `images` / `skeletons` / `materials` / `models` 是**必选**（`images` 缺失会抛异常，虽然没有 `find` 检查），`animations` / `weapons` 是**可选** ⇒ **"images 实际上是必选的，而注释只说 animations 可选"**；而那个版本方案（`-1`）与 §473 的（`-v4`）**是两个不同的方案**。
8. **⭐⭐ `OlfinalXModelSize` 的 `360`**：`header.size() != OlfinalXModelSize` ⇒ **与 §468 的 `XModelSize = 360` 精确一致**。

## 十、`sv_forge_bundle_mp.cpp` 全文件总览

**`384` 行。**

**`1` 个格式串**：`codolforge-bundle-1`。

**`3` 个读助手**：`readHex` / `readString` / `readStrings`。

**`1` 个函数**：`SV_LoadForgeBundle`（**一个 `try/catch` 包住全部**）。

**`6` 组内容**（3 必选 + 3 可选）+ **`1` 个终局判据**。

**`13` 条拒绝**（每个缺字段 / 每个长度不符 / 每个交叉不符 / 终局空）。

**`3` 个跨文件常量**：`OlfinalDObjAnimMatSize = 32`（**独立推出**）/ `OlfinalXModelSize = 360`（与 §468 一致）/ `255`（骨骼与动画的 `u8` 界）。

## 十一、未闭合点

- `SvForgeSkeleton::rootBoneCount()` 的推导（`boneCount()` 显然是 `boneNames.size()`）。
- 下一个文件：`sv_weapon_fire_mp.cpp`（`16,342` 字节）。

**已核实（本轮，`.hpp`）**：
```text
sv_forge_bundle_mp.hpp:119  OlfinalXModelSize     = 360   ← 与 §468 的 XModelSize = 360 精确一致
sv_forge_bundle_mp.hpp:122  OlfinalDObjAnimMatSize = 32    ← 与 §473 的 32u * bones 精确一致
sv_forge_bundle_mp.hpp:41   SvForgeSkeleton::boneCount()
sv_forge_bundle_mp.hpp:45   SvForgeSkeleton::rootBoneCount()
```

**两个跨文件一致性结论（本轮闭合）**：
1. **`OlfinalXModelSize = 360` 与 §468 的 `XModelSize = 360` 是同一个数** ⇒ 而 §468 的注释说 **"the emitter emits a 360-byte header"** ⇒ **两个文件在同一个头上独立一致**。
2. **`OlfinalDObjAnimMatSize = 32` 与 §473 的 `!expect("baseMat", model.baseMatrices.size(), 32u * bones)` 是同一个数** ⇒ 而 §473 的字段表还独立给出了 `OffXmBoneInfo = 312` ⇒ **`32` 既是 `baseMatrices` 的每骨骼步长，也是一个 DObj 动画矩阵的大小**（**两个不同的东西共享这个数，或者它们本来就是同一个类型**）—— **⚠ 标注为待确认**。
