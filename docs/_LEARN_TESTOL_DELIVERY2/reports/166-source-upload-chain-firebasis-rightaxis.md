# 166 · 上传单步、Forge 链、开火基座与右轴取反

## 一、范围

本报告学习 **2 处实现**：

- `ClientRenderFrameHook.cpp` 100–280 行
- `NativeWeaponBindings.cpp` 259–378 行

## 二、`uploadOne` 七步

```text
1. header = image->header()
   loadDef = storage.data() + loadDefOffset

2. slot = FiberSlot()          // 未绑定时 0xFFFFFFFF
   slot != 1  → WrongFiberSlot

3. rendererAcceptsUploads()    // *(dvar+0x0C) != 0
   否  → RendererClosed

4. memcpy(header+0, &loadDef, 4)      // load def 到达时在 +0

5. guardedUpload(header)              // sub_BE7470(header, header)
   失败 → UploadFaulted

6. memcpy(&texture, header+0, 4)      // 上传后 +0 是纹理
   texture == nullptr → NoTexture

7. （若 link）
   slotValue = header
   guardedLink(&slotValue, &entry)
   失败 / entry 空 / slotValue 空 → LinkFaulted / LinkRefused
   → Published
```

### 2.1 fiber 槽位为什么必须先查

```cpp
record.detail = "fiber slot " + std::to_string(slot) + ", expected 1";
```

注释：

> `sub_67C170` 在槽位不对时到达 `Error("1190")`，而**一个错误对话框是比不上传更糟的结果**。

所以**宁可跳过上传，也不要让客户端弹错误框**。

### 2.2 为什么先写 `+0` 再调

```cpp
std::memcpy(header + OlfinalGfxImageLoadDefSlot, &loadDef, sizeof(loadDef));
```

注释：

> **load def 到达时在 +0；`sub_BE7470` 把它搬迁到 +0x2C 并把纹理留在 +0。**

所以调用前必须把 load-def 指针放进 `+0`，**即使它本来就在 `storage` 里的那个偏移**——因为 header 是独立的内存，它的 `+0` 槽需要显式填。

### 2.3 上传后的唯一信号

```cpp
if (texture == nullptr) {
    record.detail = "CreateTexture produced nothing";
    return ForgeImageUploadStatus::NoTexture;
}
```

注释：

> `sub_BE6F40` 在 `CreateTexture` 失败时把 0 写回去，**那是它给出的唯一信号**。

即：没有返回值、没有 HRESULT，只有"槽位被写成 0"。

### 2.4 链接用**局部** `slotValue` 而不是 header

```cpp
void *slotValue = header;
void *entry{};
guardedLink(&slotValue, &entry);
record.published = (uintptr_t)slotValue;
if (entry == nullptr || slotValue == nullptr) → LinkRefused
```

`DB_LinkXAssetEntry(type, void**)` 会**改 `*slot`**，所以 `record.published` 记的是**链接后的槽值**，而不是传入的 header。

## 三、Forge 链的状态

```cpp
struct ChainState {
    bool active; ForgeChainPhase phase;
    filesystem::path root;
    std::string cloneSource;
    SvForgeBundle bundle;
    std::vector<std::string> models;      // 想要的，已解析
    std::vector<std::string> materials;   // 想要的，按依赖顺序
    std::vector<ForgeChainStep> steps;
    std::vector<std::unique_ptr<SvForgeMaterialAsset>> retainedMaterials;
    std::vector<std::unique_ptr<SvForgeXModelAsset>>  retainedModels;
};
```

两个 `retained*` 的理由与 `Retained` 相同：**引擎保留 header 内部的指针，所以存储永不释放**。

### 3.1 语义映射

```cpp
semanticFor(sampler):
    "normalMap"   → 5
    "specularMap" → 8
    其他           → 2      // colorMap，以及任何没有测量值的
```

注释：`colorMap，以及任何 port 没有测量值的情况`。**这是有意把未知归到 2 而不是拒绝**——因为 material 槽位匹配失败会整体拒绝，而颜色是最保守的回落。

### 3.2 只读克隆

```cpp
bool publishOneMaterial(const SvForgeMaterial &material, std::string &error)
{
    table = SV_ForgeXAssetTableFor(hostBase());
    clone = SV_ForgeFindXAsset(table, OlfinalMaterialAssetType, Chain.cloneSource);
    ...
}
```

注释：

> 从客户端里读出克隆、按 nameHash 重绑它的槽、发布。**克隆自己的内存只被读。**

这与之前报告里"Material 是克隆不是创作"完全对应：**techniqueSet / constants / stateBits 全部保持指向克隆的引擎内存**。

### 3.3 克隆的两个前置

```cpp
slotCount = cloneBytes[OffMtlTextureCount];        // +81
memcpy(&cloneTable, cloneBytes + OffMtlTextureTable, 4);   // +92 处的指针
if (slotCount == 0 || cloneTable == nullptr) → "the clone has no texture table"
```

即：**先验证克隆真的有纹理表**，再用它做模板。

### 3.4 素材三件套

```cpp
span{ cloneBytes, MaterialHeaderBytes }                       // 104
span{ cloneTable, TextureDefBytes * slotCount }               // 12 × N
slots                                                          // {semantic, image} 对
SV_BuildForgeMaterial(name, header, table, slots, resolveImage, error)
```

`resolveImage = SV_ForgeImageTableResolver(hostBase())` —— 用**只读表遍历**而不是 `DB_FindXAssetHeader`（可阻塞）。

## 四、`buildServerFireBasis`：右轴必须再取反一次

### 4.1 六个前置

```cpp
!isfinite(gunPitch) || !isfinite(gunYaw)          → 拒绝
!weaponAssetIndex || > MaximumWeaponAssetIndex    → 拒绝
currentWeapon != weaponAssetIndex                 → 拒绝
!muzzleTrace（眼位失败）                           → 拒绝
!isfinite(viewAngles[2])                          → 拒绝
weaponPositionFraction 不在 [0,1]                  → 拒绝
```

`currentWeapon` 的偏移是**两选一**：

```cpp
offhand ? 0x3E4 : CurrentWeaponOffset (0x3F8)
```

注释：

> offhand 准入 `429E10` 要求 WeaponDef **type 1**。**手雷在 `+3E4` 处被选中，而 `+3F8` 仍命名着手里那把枪。**

即：`+0x3F8` 是枪，`+0x3E4` 是副手。用错偏移会让副手发射检查手里的枪。

### 4.2 三次读 + 一次原生调用

```text
currentWeapon   = +0x3E4 或 +0x3F8
weaponPositionFraction = +0x404
viewAngles[3]   = +0x160
muzzleTrace     = getPlayerEyePosition(playerState, time)
```

### 4.3 `fireAngles` 的第三个分量来自 viewAngles[2]

```cpp
fireAngles = { aimState.gunPitch, aimState.gunYaw, viewAngles[2] };
```

即：**pitch 与 yaw 由服务端拥有（`aimState`），而 roll 来自 playerState 的 viewAngles 第三分量**。这是一个不对称但明确的分工。

### 4.4 右轴取反**第二次**

```cpp
.right = { -axis[3], -axis[4], -axis[5] },
```

注释：

> CODOL `AnglesToAxis 0x0062C1A0` 把 **left 轴存在第 1 行**（0 基），而 `weaponParms`/`Bullet_Endpos` 拥有的是 **right**。

而 `invokeAngleVectors` 内部已经对 3..5 取反过一次（把 `AngleVectors` 的 right 变成 `AnglesToAxis` 的 left）。

**所以这里是两次取反**：

```text
AngleVectors → (forward, right, up)
内部取反 3..5 → (forward, left, up)        ← 模拟 AnglesToAxis
再把 3..5 取反 → (forward, right, up)      ← 转回 weaponParms 期望的
```

净效果是**回到 `AngleVectors` 的原始输出**。这两次取反各自有明确理由，但**合起来是恒等**——这是一个值得指出的结构冗余：如果哪天有人删掉其中一处"看起来多余"的取反，行为会立刻改变。

### 4.5 结局校验

```cpp
return SV_IsWeaponFireBasisValid(basis) ? optional{basis} : nullopt;
```

这是整套体系里最重要的一道：**前面所有可能读出垃圾的地方，最后都在这里被拦住**。

## 五、`calculateBulletEndpos` 的三重门

```cpp
!valid()
|| !SV_IsBulletEndposRequestValid(request)
|| gameThreadId_ != GetCurrentThreadId()
→ nullopt
```

然后：

```cpp
if (!invokeBulletEndpos(...) || !finiteVector(result.end) ||
    !finiteVector(result.direction))
    return nullopt;
```

注释：

> 校验与线程所有权**围绕**保留的 CODOL `Bullet_Endpos` 原语，而**不是**在源码里重实现它的三角与随机方向计算。

即：三角与随机**必须**用原生实现（LCG 与 DEG2RAD 位相同，但算法本身不该重写），因为**服务端与客户端必须产生同一随机序列**。

## 六、关键结论

1. **宁可不上传，也不要让客户端弹 `Error("1190")`**——错误对话框比功能缺失更糟。
2. **`CreateTexture` 失败的唯一信号是槽位被写 0**，没有返回值。
3. **`DB_LinkXAssetEntry` 会改 `*slot`**，所以要记录链接后的值而不是传入值。
4. **两次取反合起来是恒等**，但两处各自有理由；删任何一处都会改变行为。
5. **`+0x3F8` 是枪、`+0x3E4` 是副手**，用错会让副手检查手里的枪。
6. **三角与随机不能重写**——服务端与客户端必须产生同一序列。

## 七、未闭合点

- Forge 链的 models 阶段实现不在本次读取范围。
- `NativeWeaponBindings.cpp` 的三个 `playerState` 偏移仍未与本 build 对齐（文件自己指出）。
