# 207 · 第一次"重造引擎函数"被见证器否决、MapEnts.trigger 的三张表、FxGlassSystem 布局

## 一、范围

本报告学习 `EngineBindings.cpp` 2661–2840 行。

## 二、`invokeScrPrecacheAnimTrees`：`__usercall` 的又一次

```asm
push allocator
mov edi, animUser
mov eax, function
call eax
add esp, 4
```

注释：

> `sub_74AF50` 是 `__usercall`：**anim USER 在 EDI、allocator 在栈**。
> 见 `ScrPrecacheAnimTreesRva` 的 CODDIFF —— **它过去是一次普通的 `__cdecl(void*, int)` 调用，而那个函数根本是错的。**

**与 §197 的"旧前缀也通过了"是同一个缺陷的两面**：签名错了，前缀也验不出。

## 三、`invokeScrClearObject`：**唯一没有 `__try` 的适配器**

```cpp
void invokeScrClearObject(void* function, uint32 object) noexcept
{
    __asm {
        mov ecx, object
        mov eax, function
        call eax
    }
}
```

**返回 `void`，没有 `__try`** —— 因为它是**内层辅助**，调用者 `invokeScrEndLoadAnimTrees` 已经废弃。

**参数在 ECX**。

## 四、那次"四十行手工重造被见证器否决"

这是本组最重要的一段。

### 4.1 见证器抓到的

```text
`rva=0x01F82A2 op=1 target=0x3` —— 一次【写】到地址 3
而 0x1F82A0 就是本函数自己的 ScrClearObjectRva
```

**`target=0x3`** —— 写地址 3。这是"把一个整数当指针"的典型。

**`rva` 落在 `ScrClearObjectRva` 内部** —— 所以是那个函数在做错事。

### 4.2 那些常量全是另一个 build 的

```text
object 变量表、temp arena、loading 标志、Scr_ClearObject、
Scr_RemoveRefToObject、TempMallocAlignStrict
    —— 【没有一个不是从另一个 build 原样搬来的】
```

### 4.3 结论

> **out.exe 有那个函数。`sub_74B010` 不接受参数，而 `CL_ParseGamestate` 在 `0x454D3D` 调它，在 `BG_FindAnimTrees` 与 `BG_FinalizePlayerAnims` 之间，正好是本函数所在的位置。**
>
> **重造一个引擎函数，只有在引擎不提供它的时候才值得做。**

**"只有引擎不提供时才值得重造"** —— 这是一条应当写进方法论的原则。

### 4.4 替代实现只有十行

```cpp
constexpr std::size_t ScrEndLoadAnimTreesRva = 0x034B010;
reinterpret_cast<void(__cdecl*)()>(module + ScrEndLoadAnimTreesRva)();
```

**从四十行降到十行，且正确**。

## 五、MapEnts 与它的"分离视图"

### 5.1 基础结构

```cpp
struct MapEnts {
    const char* name;
    const char* entityString;
    int32 numEntityChars;
};
```

### 5.2 为什么触发器要用**另一个结构**

```cpp
// A SEPARATE VIEW, not an extension of MapEnts above: readMapEntityString
// checks the asset is at least sizeof(MapEnts) bytes, and widening that struct
// would tighten a check on a path that four maps already load correctly.
```

**"加宽那个结构会收紧一条四张地图已经正确加载的路径上的检查"** —— 所以用第二个视图。

**这是一个很精细的判断**：`sizeof(MapEnts)` 被用作"资产至少这么大"的检查，加宽它会**把原本通过的资产判为不够大**。

### 5.3 `MapEntsWithTriggers` 的九个字段

```cpp
const char* name;
const char* entityString;
int32 numEntityChars;
int32 modelCount;
const MapTriggerModel* models;
int32 hullCount;
const MapTriggerHull* hulls;
int32 slabCount;
const MapTriggerSlab* slabs;
```

**三对（count + pointer）** —— 与 §`sv_map_triggers_mp.hpp` 里"`MapEnts.trigger` 紧跟实体串"一致。

## 六、三张表的结构与尺寸

```cpp
struct MapTriggerModel {      // 8 字节
    uint32 contents;
    uint16 hullCount;
    uint16 firstHull;
};

struct MapTriggerHull {       // 32 字节
    array<float,3> midpoint;
    array<float,3> halfSize;
    uint32 contents;
    uint16 slabCount;
    uint16 firstSlab;
};

struct MapTriggerSlab {       // 20 字节
    array<float,3> direction;
    float midPoint;
    float halfSize;
};
```

### 6.1 尺寸验算

```text
Model: 4 + 2 + 2 = 8 ✓
Hull:  12 + 12 + 4 + 2 + 2 = 32 ✓
Slab:  12 + 4 + 4 = 20 ✓
```

三条 `static_assert` 全部钉住。

### 6.2 与项目侧结构的差异

§`sv_map_triggers_mp.hpp` 里：

```cpp
struct SvTriggerSlab {
    std::array<float,3> direction;
    float midPoint;
    float halfSize;
};
struct SvTriggerHull {
    std::array<float,3> midpoint;
    std::array<float,3> halfSize;
    uint16 slabFirst;
    uint16 slabCount;
};
```

**差异**：`SvTriggerHull` **没有 `contents`**（12 + 12 + 2 + 2 = 28，不是 32）。

**所以原生是 32 而项目侧是 28** —— 项目侧视图比原生少一个 `contents` 字段。

**而 `SvMapTrigger` 另有 `contents`？不，§`sv_map_triggers_mp.hpp` 里 `SvMapTrigger` 有 `cost` 但那不是 `contents`。**

**这是一处需要指出的差异** —— 项目侧的 hull 少了 `contents`，所以如果它按 32 步长读原生数组会错位。

### 6.3 提取器已解析过

> 尺寸由离线提取器已经解析的 fastfile 固定（`Tools/gen-mapent-numbering.py`）：**model 8 字节、hull 32、slab 20**。

## 七、`NativeFxGlassInitPieceState`：52 字节

```cpp
struct NativeFxGlassInitPieceState {
    array<float,4> quaternion;              // 16
    array<float,3> origin;                  // 12
    float radius;                           //  4
    array<float,2> textureCoordinateOrigin; //  8
    uint32 supportMask;                     //  4
    float doubledArea;                      //  4
    uint8 definitionIndex;                  //  1
    uint8 vertexCount;                      //  1
    uint8 fanDataCount;                     //  1
    uint8 padding;                          //  1
};
static_assert(sizeof(NativeFxGlassInitPieceState) == 52);
```

**验算**：16 + 12 + 4 + 8 + 4 + 4 + 1 + 1 + 1 + 1 = **52** ✓

**与 §`sv_collision_mp.hpp` 的 `SvGlassInitialPieceGeometry` 字段完全一致**（quaternion/origin/radius/uv/supportMask/doubledArea/definitionIndex/vertexCount/fanDataCount）—— 项目侧少了个 `padding`，但字段序相同。

## 八、`NativeFxGlassSystem`：112 字节，11 个指针

```cpp
int32 time, previousTime;
uint32 definitionCount, pieceLimit, pieceWordCount, initialPieceCount;
uint32 cellCount, activePieceCount, firstFreePiece;
uint32 geometryLimit, geometryCount, initialGeometryCount;
array<const void*, 11> runtimePointers;
const NativeFxGlassInitPieceState* initialPieceStates;
const void* initialGeometry;
uint8 needsCompaction, initialCount;
uint16 padding;
float effectChanceAccumulator;
int32 lastPieceDeletionTime;
```

### 8.1 偏移验算

```text
time                +0
previousTime        +4
definitionCount     +8
pieceLimit          +12
pieceWordCount      +16
initialPieceCount   +20
cellCount           +24
activePieceCount    +28
firstFreePiece      +32
geometryLimit       +36
geometryCount       +40
initialGeometryCount +44
runtimePointers     +48  （11 × 4 = 44 字节，到 +92）
initialPieceStates  +92  ✓（断言）
initialGeometry     +96
needsCompaction     +100
initialCount        +101
padding             +102
effectChanceAccumulator +104
lastPieceDeletionTime   +108
总 = 112 ✓
```

**四组字段**：

```text
时间    2 个
计数    10 个（definition/piece/pieceWord/initialPiece/cell/active/firstFree/
                geometryLimit/geometryCount/initialGeometry）
指针    11 + 2
尾      needsCompaction/initialCount/padding/effectChance/lastDeletion
```

### 8.2 与 §198 的三条关系的对应

§198 记的三条（37 份 fastfile 实测）：

```text
pieceWordCount == ceil(pieceLimit / 32)
pieceLimit     == initialPieceCount + 1024
geometryLimit  == 8 * pieceLimit
```

**三个字段都在这里**：

```text
pieceWordCount    +16
pieceLimit        +12
initialPieceCount +20
geometryLimit     +36
```

**所以那三条关系是可以在这里运行时校验的**。

## 九、`NativeFxWorld`：116 字节

```cpp
struct NativeFxWorld {
    const char* name;
    NativeFxGlassSystem glassSystem;
};
static_assert(offsetof(NativeFxWorld, glassSystem) == 4);
static_assert(sizeof(NativeFxWorld) == 116);
```

**4 + 112 = 116** ✓

**`glassSystem` 在 `+4`** —— 因为 x86 上指针 4 字节。

## 十、关键结论

1. **重造引擎函数只在引擎不提供它时才值得做** —— 四十行手工重造被见证器的 `target=0x3` 否决。
2. **`MapEnts` 不能加宽**，因为 `sizeof` 被用作"资产至少这么大"的检查。
3. **原生 `MapTriggerHull` 是 32 字节含 `contents`，而项目侧是 28 字节不含** —— 按原生步长读会错位。
4. **`NativeFxGlassSystem` 里三个关键字段（pieceLimit/pieceWordCount/initialPieceCount）都在**，所以 §198 的三条关系可运行时校验。
5. **结构分离视图**是"不收紧既有检查"的标准手法。

## 十一、未闭合点

- `SvTriggerHull` 少 `contents` 是否影响按原生读（本组未见读取代码）。
- `EngineBindings.cpp` 2840 行之后未读取。
