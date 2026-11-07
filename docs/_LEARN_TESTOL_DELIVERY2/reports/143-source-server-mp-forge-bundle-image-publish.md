# 143 · CodolForge 资产发布链（bundle / image / publish）

## 一、范围

本报告完整学习 **6 个文件**：

- `sv_forge_bundle_mp.hpp/.cpp`
- `sv_forge_image_mp.hpp/.cpp`
- `sv_forge_publish_mp.hpp/.cpp`

`server_mp` 进度推进到 **69/154**。forge 系列不是游戏逻辑，而是**把外部素材（CoD4/CoDOL-alpha/自建）变成本 build 客户端能直接 link 的资产**的工具链；它决定了"换皮肤、加武器、加模型"这条路能不能走通。

## 二、bundle：闭集交叉验证的清单

### 2.1 格式与拒绝条件

格式串必须是 `codolforge-bundle-1`。全部为**硬拒绝**（任一不满足整包作废），因为"半有效闭包比没有更糟"：

- 每个 model header 必须**恰好 360 字节**；
- header 的 `numBones`/`numRootBones`/`numsurfs` 必须与所引 skeleton 和 material 数量一致；
- skeleton 各数组长度必须与骨头数/根骨数相符；
- model 引用的每个 material 必须存在于本包；
- material 引用的每张 image 必须在 `images` 列表里；
- 每个 model 至少命名一个 loose resource；
- 动画必须有 name、asset、1..255 帧、1..255 根**互不相同**的骨头名；
- 每个 weapon 必须有 name、clone_source 和至少一个 key。

### 2.2 六个资源类型的角色分工

| 资源 | 走向 | 为什么 |
|---|---|---|
| mesh 字节 | loose overlay `main/models/<resource>` | 走 `models/%s` 通道，不进 zone |
| IWI 字节 | loose overlay `main/images/<image>.iwi` | 同上 |
| XModel | `DB_LinkXAssetEntry`（type 4） | 需要 header + skeleton 数组 + material 指针 |
| Material | `DB_LinkXAssetEntry`（type 5） | 克隆已有 material 再换 image |
| XAnimParts | `DB_LinkXAssetEntry`（type 2） | 需 relocate 后再 link |
| WeaponDef | `DB_LinkXAssetEntry`（type 28） | 由 `sv_alpha_weapon_port_mp` 已有路径克隆 |

### 2.3 skeleton 结构

`SvForgeSkeleton` 有六条数组：

- `boneNames`：全部骨头（含根）；
- `parentList`：仅非根，1 字节/项，长度 = boneCount - rootCount；
- `quaternions`：8 字节/非根（i16×4）；
- `translations`：12 字节/非根（float×3）；
- `partClassification`：1 字节/骨；
- `baseMatrices`：32 字节/骨（DObjAnimMat）。

`rootBoneCount()` = `boneNames.size() - parentList.size()`，即**用长度差推根数**而非额外字段。

### 2.4 动画的骨头名是槽位

骨头名不是"标签"而是**槽位索引**：translation 记录里的 bone-index 字节就是 `bones[]` 的下标。因此重复名会让某根骨头永久不可寻址，bundle 直接拒绝重复。

同理 256 帧以上走的是 u16 索引路径，CodolForge 不产生这种资产，所以 bundle 也拒绝 ≥256 帧。

### 2.5 weapon 必须克隆

`WeaponDef` 不是凭空构造的：目标 build 的 weapon 结构有大量 pipeline 生成字段无法重算，只能克隆已发布的一个再打补丁。所以 `clone_source` 为空即整包拒绝——**没有可克隆源就根本无法构建**。

## 三、image：GfxImage 是唯一"不能只 link"的资产类型

### 3.1 为什么必须上传

其余四类（XModel/Material/XAnimParts/WeaponDef）都是纯数据：`DB_LinkXAssetEntry` 复制 header、插哈希、即刻可用。

GfxImage 不是：渲染器采样的那个字段是**GPU 资源**，必须有人创建：

```text
sub_487380 (Load_GfxImage)  读 52 字节，load-def 指针在 +0
sub_4872A0                   修正该指针并调 sub_BE7470(image, image)
sub_BE7470                   把 load-def 从 +0 搬迁到 +0x2C、清 +0、创建
                             IDirect3DTexture9、逐 mip 拷贝、把纹理写回 +0
```

所以"linked 但未上传"的 image，其 +0 仍是一个 load definition，而渲染器会把它当纹理指针解引用——**不是画不出，而是跟着一张假 vtable 跑**。

### 3.2 引擎的确切尺寸算术（三个纯函数）

`SV_ForgeImageLevelBytes(f,w,h,d)` 复刻 `sub_BE8690`：

| 格式 | 每级字节 |
|---|---|
| DXT3 / DXT5 (0x33545844 / 0x35545844) | `16*d*((h+3)>>2)*((w+3)>>2)` |
| DXT1 (0x31545844) | `8*d*((h+3)>>2)*((w+3)>>2)` |
| 112 / 114 | `4*d*h*w` |
| 80 | `2*d*h*w` |
| 21 / 22 / 75 | `4*d*h*w` |
| 28 / 50 | `d*h*w` |
| 51 | `2*d*h*w` |
| 其他 | 0（客户端无法定尺寸 ⇒ 必然致命） |

`SV_ForgeImageLevelCount(flags,w,h,d)` 复刻 `sub_BE8C30`：**只读 flags 低字节的 bit1（0x2）**；置位 ⇒ 1 级，清零 ⇒ 完整链（逐级折半直到覆盖全部维度）。

`SV_ForgeImagePayloadBytes(...)` = faces 外层 × levels 内层，每维 clamp 到 1。`sub_BE7470` 用一个游标跨全部 face 前进而不重置，所以这个总数**就是它会读的字节数**。

### 3.3 .iwi 解析

两个版本：

- **v6（IW3）**：header 28 字节，format +4、dims +6/+8/+10；**最大级在前**。
- **v8/v9（IW5/CODOL）**：header 32 字节，flags u32 +4（bit16 = cubemap）、format +8、dims +10/+12/+14；**最小级在前**。

`SV_ForgeIwiFormatToD3D`：1→21(A8R8G8B8)、3→51(A8L8)、4→50(L8)、5→28(A8)、11→DXT1、12→DXT3、13→DXT5。

**2 (X8R8G8B8) 被刻意拒绝**：文件里是 3 字节/像素，D3DFMT_X8R8G8B8 是 4，直拷会把图剪切错位。6..10 是流编码变体，根本不是平铺像素。

**存储级数由"前缀和恰好等于 payload"唯一确定**：前缀和严格递增，至多一个 count 能匹配，所以这是判定而不是猜测。

### 3.4 构建与自检

`SV_BuildForgeGfxImage` 的硬性前提：

- payload 不越界；
- **拒绝 cubemap**（面序从未验证过，这正是"看起来合理的错误答案"的典型来源）；
- storedLevels 只能是 1 或 fullLevels —— 因为 `sub_BE8C30` 只会回答"一级"或"整链"，其他数量会让引擎走出 payload；
- 引擎将读的字节数必须等于文件实际 payload。

布局：`header(52) | name | pad到4 | loadDef(16) | payload`。

header 字段：

- +4 = MapType2D(3)；
- +5 = semantic（2 颜色 / 5 法线 / 8 高光）；
- +6 = category（3；上传后 +8 ⇒ 读回是 11）；
- +32/+34/+36 = width/height/depth；
- +38 "no pixels" = 0，+40 状态字节 = 0 —— `sub_4999E0` 在 `(b&1)&&!(b&2)` 时返回 true 并让 `sub_BE7470` 什么都不做，所以 0 才是让上传继续的值；
- +16..+31 = cardMemory 四份，写成实际 payload 字节数。

loadDef 16 字节：+0 = `storedLevels==1 ? 1 : 0`（即 CreateTexture 的 Levels 参数）；+4 = flags；+8 = d3dFormat；+12 = payload 字节数。

payload 若 v8/v9 是"最小级在前"，则从文件尾**逐级倒着**搬，最终 largest-first 写入；并强制 `readAt==0 && writeAt==payloadBytes`（必须精确吃完）。

`SV_VerifyForgeGfxImage` 再按 `sub_BE7470` 的方式重走一遍，要求游标**恰好落在 payload 最后一字节**，且级数相等、名字在 storage 内 NUL 结尾且内容一致。

### 3.5 线程与时机约束

实测（2026-09-09）：设备 BehaviorFlags = 0x42（FPU_PRESERVE | HARDWARE_VERTEXPROCESSING），**没有 D3DCREATE_MULTITHREADED**，且其调用来自不是跑 `Com_Frame` 的那个线程。因此上传挂在 `ClientRenderFrameHook` 上，而不是已有的 frame hook。

## 四、publish：relocate 与 link 的分离

### 4.1 为什么必须分离

- **relocation** 是纯的、确定的、可离线单测；
- **publication** 是一句引擎调用，无法离线验证，所以保持最薄、带守卫、失败即关。

### 4.2 XAnimParts 的 relocate

88 字节 header 的字段偏移（从 `Load_XAnimParts` 0x485B40 自身的反汇编读出，不是从 IW4 笔记转移）：

```text
+0  name(u32 指针槽)      +4  dataByteCount(u16)   +6  dataShortCount
+8  dataIntCount          +10 randomDataByteCount  +12 randomDataIntCount
+14 numframes(u16)        +26 boneCount(u8)        +27 notifyCount(u8)
+32 randomDataShortCount(u32)  +36 indexCount(u32)
+48 names   +52 dataByte  +56 dataShort  +60 dataInt
+64 randomDataShort  +68 randomDataByte  +72 randomDataInt
+76 indices +80 notify   +84 deltaPart
```

指针槽语义：`0` = NULL，`0xFFFFFFFF` = **payload 紧随其后内联**（与 zone stream 完全一致）。relocate 把 blob 拷进自有内存，再按 loader 的访问顺序把这些占位符重写成真实地址，并要求各数组**恰好铺满**整个 blob（`p == storage.size()`），否则判为"没读懂"。

强制拒绝：

- `numframes==0 || >=256`；
- `indexCount!=0` 或 `indices` 非零（<256 帧时不应存在）；
- `deltaPart` 非零；
- `randomDataIntCount!=0`（无任何随包动画使用）；
- boneCount==0；
- 给定骨头名数量 ≠ header 的 boneCount；
- 给定 notify 名数量 ≠ notifyCount；
- 某个指针槽既非 0 也非 0xFFFFFFFF。

**key 名数组最后才解析**，这样字符串解析失败不会留下"结构上看起来还行"的半搬迁资产。

### 4.3 字符串解析的两条路

1. `SV_ForgeStringResolver(bindings)` —— 调引擎 `0x74BD10`（`(const char*, int kind, unsigned len)`，zone loader 传 kind 4）。**必须进临界区，调用约定从未被验证过**。
2. `SV_ForgeStringTableResolver(moduleBase)` —— **只读遍历字符串表**，无临界区、无分配、无调用约定风险。

表指针槽在 RVA `0x749C524`（VA 0x0789C524）。条目 20 字节：`+0 u16 refcount / +2 u8 kind / +3 u8 length（含 NUL） / +4 名字内联`。实测 2026-09-09：读回指针 0x789c700，骨头名存在且 kind 4，length = strlen+1。

**索引是进程私有的**：同机两个客户端给同一骨头不同索引，所以发出包里的资产**不能携带这些索引**——这正是为什么 forge 发出时写 0、由发布方现场解析并回填。

PPSh 的 67 个骨头名里 66 个已是 OLfinal 脚本串，唯一不是的就是枪模型自己的名字。

### 4.4 XModel 是"构建"不是"搬迁"

XModel 不是自包含 blob：forge 发出 360 字节 header（标量已填、指针槽全零）并单独发 skeleton 数组，所以这里没有可 relocate 的东西，**布局在这里现搭**。

loader 0x489B20 的字段（从它自己的寄存器加载读出）：

```text
+44 boneNames          u16 × numBones          (sub_484F80(bones,1))
+48 parentList         u8  × nonRoot           (sub_484D00, esi=bones-roots)
+52 quats              i16 × 4*nonRoot         (sub_484E80)
+56 trans              float × 3*nonRoot       (sub_484D80)
+60 partClassification u8  × numBones          (sub_484D00, esi=bones)
+64 baseMat            32  × numBones          (sub_485FF0, eax<<5)
+68 materials          ptr × numsurfs          (sub_488490, edi*4)
+72 XModelLodInfo[4]，每项 56 字节，内联在结构里
+300 collSurfs (+304 count)   +312 boneInfo
+352 physPreset   +356 physCollmap
```

`nonRoot = numBones - numRootBones`，由 0x489C1F / 0x489CCF 的减法固定，这就是那四个数组长度的来源。

`lodInfo[0].modelSurfs` 必须携带流式哨兵 **0xFFFFFFFE**，`lodInfo[0].name` 是 **loose resource 名**——`models/%s` 是 out.exe 仍然认的三条通道之一，所以表面数据来自 overlay 而非 zone。

构建时再硬校验：header 标量与各数组长度、`lodInfo[0].numsurfs == numsurfs`、`lodInfo[0].modelSurfs == 0xFFFFFFFE`。**任何一处不符即崩溃级错误，不是视觉瑕疵**。

未作者化的字段一律显式写 NULL 而不是听凭发出的 header 携带什么：collSurfs/numCollSurfs/boneInfo/physPreset/physCollmap，以及 LOD 1..3 的 modelSurfs/name/surfs。

### 4.5 XAsset 哈希表：只读遍历优先于 DB_FindXAssetHeader

`DB_FindXAssetHeader`（0x49CF30）是**错误入口**：它取临界区、等流事件、按 `GetCurrentThreadId` 对三个线程 id 分支；活客户端实测它确实这么做。

但那些全是 wrapper，真正的查表是 `sub_49CA70`，它是纯的：

```text
bucket = sub_49C870(type, name)
for (i = heads[bucket]; i; i = entries[i].next)
    if (entries[i].type == type && iequals(name, nameOf(entries[i])))
        return &entries[i]
```

```text
entries  dword_239B120  步长 28     +0 u32 type  +8 header  +20 u32 next
heads    dword_1E2D338  每桶一个 u32，0 终止链
buckets  0x1D4C0 = 120,000
```

`sub_49C870` 以**资产类型**为种子（0x49DA60 `mov eax, edi`）：

```text
h = type
for each char: c = tolower(ch); h = 31*h + (c=='\\' ? '/' : c)
return h % 120000
```

值得注意的是**不对称**：哈希把反斜杠折成正斜杠，**比较不折**。只差斜杠方向的两个名字共享桶却比较不等。

实测 2026-09-09：遍历全部 120,000 桶并按条目自身名字重算哈希，**81,128/81,128** 全部复现所在桶，零不符。剩下 18,882 条是 type 27，其名字访问器不属于下面三个，因此**拒绝读取**而不是按猜测偏移去读。最长链 7，`mc/mtl_t6_wpn_pda` 一步命中（此前用 200,000 条线性扫描）。

三个名字访问器 thunk（从引擎读，不是从样本推）：

```text
0x483390  **(DWORD**)p        名字在 header +0    (XAnimParts, XModel)
0x4833A0  *(DWORD*)(*p + 16)  Material 在 +16
0x4833C0  *(DWORD*)(*p + 48)  GfxImage 在 +48
```

不在表里的 thunk ⇒ 拒绝。

### 4.6 Material 是克隆，不是创作

`MaterialTextureDef.nameHash` 由资产流水线生成，客户端里根本不存在，所以无法重算——但也不需要：**hash 覆盖的是 sampler 名**，同一槽位在任何 material 里都是同一个 hash，这就使它成为可靠的匹配键。

实测 2,849 个已发布 material（`nameStart`/`nameEnd` 字面就是 sampler 名的首尾字符）：

| sampler | 首尾 | hash | semantic | 用量 |
|---|---|---|---:|---:|
| colorMap | c..p | 0xA0AB1041 | 2 | 2920 |
| normalMap | n..p | 0x59D30D0F | 5 | 2575 |
| specularMap | s..p | 0x34ECCCB3 | 8 | 2251 |
| detailMap | d..p | 0xEB529B4D | 5 | 92 |

Material 104 字节：+16 name、+81 textureCount、+82 constantCount、+83 stateBitsCount、+88 techniqueSet、+92 textureTable（每项 12 字节）、+96 constantTable、+100 stateBitsTable。

`SV_BuildForgeMaterial` 只替换 **texture table 和 name**；techniqueSet/constants/stateBits 保持指向克隆的引擎内存——这正是"克隆"的意义，和 WeaponDef port 用的是同一套浅拷贝策略。

`texture table` 每项前 8 字节（nameHash / nameStart / nameEnd / samplerState / semantic）由流水线产生、客户端里不存在，**必须从 cloneSource 拷贝**，只有 `+8` 的 image 指针被替换。

**按 hash 匹配槽位而非按位置**：写错槽位不是失败，而是把法线贴图当漫反射画出来。clone 里没有该 slot、或同一 slot 被给两次，都拒绝。

### 4.7 CoD4 material 文件解析

槽位信息不能从 `_c`/`_n`/`_s` 后缀猜——那是"约定"，正是这个路径要避免的"看起来合理的错误答案"。CoD4 material 把自己 sampler 名作为字面串带在 texture table 旁：

```text
+0  u32 material 名偏移   +48 u8 textureCount   +50 u8 constantCount
+52 u32 techniqueSet 名偏移   +56 u32 texture table 偏移   +60 u32 constant table 偏移

texture table 项 12 字节：
  +0 u32 SAMPLER 名偏移   +4 u8 sampleState   +5 u8 semantic   +8 u32 IMAGE 名偏移
```

文件内**每个指针字段都是文件偏移**（导出时已重定基），所以整份文件自包含。

实测 PPSh 的两个 material（各 299 字节）：

```text
mtl_t4_ppsh41_base   colorMap    sem 2  t4_ppsh41_base_c
                     normalMap   sem 5  t4_ppsh41_base_n
                     specularMap sem 8  ~t4_ppsh41_base_s-rgb&...
```

这些 semantic 与 2,849 个 OLfinal material 实测的 2/5/8 一致，这正是 sampler 名能跨两个引擎做键的原因。

解析器拒绝：任何越界偏移、任何在文件内找不到终止符的字符串、任何**未实测过 nameHash 的 sampler**——按位置绑定正是它拒绝犯的错。

### 4.8 WeaponDef 调参映射

`SV_ForgeWeaponTuning` 把 CoD4 weaponfile 的字符串与秒换算成本 build 的枚举与毫秒。所有枚举值都来自 `SV_AlphaWeaponPorts()` 里某个已解码的实际武器：

| 键 | 映射 |
|---|---|
| weaponType | `bullet` → 0 |
| weaponClass | `rifle`/`assault` → 0（Fal/Tavor/Masada）、`sniper` → 1（Barrett）、`smg` → 3（Uzi）、`pistol` → 5（Anaconda） |
| penetrateType | `small`→1、`medium`→2、`large`→3 |
| impactType | `bullet_small`/`bullet_large` → 0 |
| fireType | `full auto`→0、`single shot`→1 |

**没有见证者的值一律缺席**：未映射的字符串被拒绝而不是取默认——错误的 weaponClass 是外观上像 port bug 却会拖几周的游戏性变更。

数值约束：

- 秒单位，范围 0..60，转毫秒 `v*1000+0.5`（fireTime/fireDelay/dropTime/raiseTime）；
- startAmmo 0..4000、maxAmmo 1..4000、clipSize 1..4000、shotCount 1..64、damage/minDamage/meleeDamage 0..10000；
- 交叉校验：`minDamage<=damage`、`maxDamageRange<=minDamageRange`、`startAmmo<=maxAmmo`、`fireTime>0`。

**散布六元组顺序** `{standMin, duckedMin, proneMin, max, duckedMax, proneMax}` 由 Uzi 的实装值 `{2.0,1.75,1.5,5.0,4.5,4.0}` 与 PPSh 的 CoD4 键按同样顺序携带同样六个数确定——这也说明**单位已经一致**，不需换算。

命中部位倍率：

- Standard 集 `{1.0, 1.4, 1.4, 1.0, 1.0, 1.0, 1.0, ...}`（共 21 项，索引 18/19 为 0.0，末项 1.0）；
- 只有前六个键 `locNone/locHelmet/locHead/locNeck/locTorsoUpper/locTorsoLower` 有见证（Standard 与 Barrett 的 `1.0 后 1.5×5` 都同意索引 0 是 none，1..5 是头与躯干组）；
- 索引 5 之后**无见证**，保留 Standard 值，CoD4 的 `locGun` 不做映射。

`overlayReticle` 无 CoD4 对应（源是 shader 名，目标是索引），保留 clone 值。`aimDownSight` 接受 `"1"` 或 `"true"`。

## 五、关键结论

1. **forge 是"把外部素材变成可 link 资产"的完整闭环**，但它只保证"资产能被引擎接受"，不保证"玩法正确"——后者仍要靠 weapon/anim 数据本身。
2. GfxImage 是整条链上**唯一需要 GPU 上传**的类型，也是唯一必须在渲染线程上完成的步骤；其余四类纯 link 即可。
3. XAnimParts 的 relocate 用"数组精确铺满"作正确性标准；XModel 用"header 标量与数组长度全等"作正确性标准。两者都不接受"看起来差不多"。
4. **只读表遍历优先于引擎调用**：字符串表、XAsset 哈希表都可无锁、无分配、无调用约定风险地读，活客户端已证明 `DB_FindXAssetHeader` 会阻塞。
5. Material 与 WeaponDef 都是**克隆+打补丁**，不是创作；这正是为什么 bundle 强制要求 `clone_source`。
6. `SV_PublishForgeBundleXAnims` 有 `enable` 门且**本仓库无任何调用点带 enable**——发布入活客户端不是加载 bundle 的副作用。

## 六、未闭合点

- `SV_PublishForgeXAnim` / `XModel` / `Material` 的 `Ready` 只表示"引擎调用返回了"，**不表示动画播放/模型绘制**；从未对活客户端验证。
- XAnimParts 的 `deltaPart`、`randomDataInt`、`indices` 路径完全不建模。
- cubemap 面序未验证，直接拒绝。
- `X8R8G8B8` 与流编码 IWI 变体（6..10）未支持。
- type 27 资产的名字访问器未知，因此该层不可查。
- Material 的 constants/stateBits 全程不触碰（靠克隆继承），无法据此定制 shader 参数。

**本组 6 文件完成。下一步继续 ZM 系列（约 30 个文件）。**
