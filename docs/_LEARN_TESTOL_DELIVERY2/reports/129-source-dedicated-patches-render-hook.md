# 学习报告 129（重开）— `DedicatedProcessPatches.cpp`（969 行）+ `ClientRenderFrameHook.cpp`（811 行）

**学习范围**：`DedicatedProcessPatches.cpp`（39,058 B / 969 行）+ `ClientRenderFrameHook.cpp`（32,154 B / 811 行）
**性质**：全实测（**两文件逐行读完**）
**★★★★★ 本报告收录十个重大发现**：①**八个补丁的完整 RVA 与原始字节** ②**单实例 GUID 的两个版本（…BB30 / …BB31）** ③**`OLMOD_CLIENT_INSTANCE` 1..9 的第四字符替换** ④**双页解包判据（`0x37EE5A` + `0x34EF10`）** ⑤**两页的 13:27 / 13:37 对照实测** ⑥**渲染钩子的 `pushad`+`pushfd`+尾跳** ⑦**`Material` 头的 104 字节布局** ⑧**fiber slot 必须 = 1** ⑨**纹理语义的三种判定（`sampler` 名 / `_n`/`_s`/`_c` 后缀 / `~` 破坏形式）** ⑩**`queueForgeChain` 的"先全建后入队"**

---

## 一、★★★★★ **`DedicatedProcessPatches.cpp` —— 八个补丁的完整清单**

### 1.1 ★★★★★ **补丁 1：单实例守卫**

```cpp
SingleInstanceGuardRva   = **0x37EE5A**;
SingleInstanceNameRva    = **0x9DBA14**;
BranchOpcodeOffset       = **23**;
RelocatedAddressOffset   = **2**;
RelocatedAddressSize     = **4**;
ConditionalJumpOpcode    = **0x75**;   // jnz
UnconditionalJumpOpcode  = **0xEB**;   // jmp
NoOperationOpcode        = **0x90**;   // nop
```

### ★★★★★ **25 字节的完整守卫字节**

```cpp
constexpr std::array<std::uint8_t, 25> SingleInstanceGuard{
    0x81, 0x3D, 0xC0, 0x80, 0x1F, 0x0E, 0xB7, 0x00,   // [0..7]
    0x00, 0x00, 0x8B, 0x45, 0x08, 0x53, 0x56, 0x57,   // [8..15]
    0x8B, 0x7D, 0x10, 0x89, 0x44, 0x24, 0x10, 0x75,   // [16..23]
    0x2D,                                             // [24]
};
```

★★★ **⇒ 反汇编：**
```
`[0]`      **`81 3D`** ⇒ `cmp dword ptr [imm32], imm32`
`[2..5]`   **`C0 80 1F 0E`** ⇒ 地址 **`0x0E1F80C0`**（**可重定位**）
`[6..9]`   **`B7 00 00 00 00`** ⇒ 立即数 **`0x000000B7`**（= **183**）
`[10..11]` **`8B 45 08`** ⇒ `mov eax, [ebp+8]`
`[12..14]` **`53 56 57`** ⇒ `push ebx; push esi; push edi`
`[15..18]` **`8B 7D 10`** ⇒ `mov edi, [ebp+0x10]`
`[19..22]` **`89 44 24 10`** ⇒ `mov [esp+0x10], eax`
`[23]`     **`75`** ⇒ `jnz`（**条件跳转**）
`[24]`     **`2D`** ⇒ 位移 **+0x2D**
```

★★★★★ **⇒ 完整的单实例守卫逻辑：**
```
`cmp dword ptr [0x0E1F80C0], 0x000000B7`   ← ★ **183** 是"已存在"的标志
        ↓
`mov eax, [ebp+8]`
`push ebx/esi/edi`
`mov edi, [ebp+0x10]`
`mov [esp+0x10], eax`
        ↓
★★★ `jnz +0x2D` ⇒ **若已存在 ⇒ 跳走**（跳过创建）
        ↓
★★★★★ ⇒ 补丁把 `jnz` 改成 `jmp`（**无条件跳**）⇒ **永远跳过创建**
   ⇒ **允许第二个实例**
```

### ★★★★★ **两个 GUID**

```cpp
ClientSingleInstanceName    = "Global\\{{5BD75B76-601A-4b20-80C8-D2317C94BB**30**}}";
DedicatedSingleInstanceName = "Global\\{{5BD75B76-601A-4b20-80C8-D2317C94BB**31**}}";
static_assert(ClientSingleInstanceName.size() == DedicatedSingleInstanceName.size());
```

★★★★★ **⇒ 两个 GUID **只差最后一个字符**（`30` vs `31`）⇒ 长度相同 ⇒ `memcmp` 可互换。**

### ★★★★★ **`OLMOD_CLIENT_INSTANCE` 的第四字符替换**

```cpp
auto clientInstanceSingleInstanceName(const std::uint32_t instance)
{
    auto result = ClientSingleInstanceName;
    result[result.size() - 4] = static_cast<char>('0' + instance);   // ★ 倒数第 4 字符
    return result;
}
```

★★★ **⇒ 字符串尾部：**
```
`...D2317C94BB30}}`
             ^^^^
             `30}}`   ⇒ 长度 4
        ↓
★★★ `result[size-4]` = **`'3'`**（`30` 的第一个字符）
★★★ 替换成 `'0' + instance`
        ↓
★★★ `instance = 2` ⇒ **`...BB20}}`**
★★★ `instance = 9` ⇒ **`...BB90}}`**
```

★★★ **⇒ 范围校验（第 426 行）：`instance < 2 || instance > 9` ⇒ 拒。**
**⇒ 但 `configuredClientInstance()` 允许 **1..9**（第 509 行）⇒ **不一致**：**

```
`configuredClientInstance()`：**1..9**（1 = 默认，不改名）
`patchClientInstanceSingleInstanceBuffer()`：**2..9**（1 走默认路径）
        ↓
★★★ ⇒ **逻辑一致**（1 不替换，2..9 替换）✓
```

### 1.2 ★★★★★ **补丁 2：客户端帧的四次调用**

```cpp
constexpr std::array ClientFrameCalls{
    { 0x**FE650**, { 0xE8, 0x6B, 0x43, 0x0C, 0x00 } },   // rel32 = 0x000C436B
    { 0x**FE695**, { 0xE8, 0xE6, 0x43, 0x0C, 0x00 } },   // rel32 = 0x000C43E6
    { 0x**FE6A9**, { 0xE8, 0xD2, 0xF9, 0xFF, 0xFF } },   // rel32 = 0xFFFFF9D2 = -1582
    { 0x**FE6B4**, { 0xE8, 0x17, 0x72, 0xF7, 0xFF } },   // rel32 = 0xFFF77217 = -559081
};
ClientFramePatchStartRva = **0xFE650**;
ClientFramePatchEndRva   = **0xFE6B4 + 5** = **0xFE6B9**;
```

★★★ **⇒ 四个调用,跨 **`0xFE650..0xFE6B9`**（**0x69 = 105 字节**）⇒ 一起 `VirtualProtect`。**

### 1.3 ★★★★★ **补丁 3-8 的完整表**

| # | 补丁 | RVA | 原始字节 | 长度 | 补丁方式 |
|---|---|---|---|---|---|
| **3** | **音频驱动启动** | **`0x0FD694`** | **`E8 77 2F 32 00`** | 5 | **全 `0x90`** |
| **4** | **前端启动** | **`0x37F8B8`** | **`E8 C3 81 CB FF`** | 5 | **全 `0x90`** |
| **5** | **焦点启动** | **`0x37F8D8`** | ★ **`52 FF 15 18 38 9D 0E`** | ★ **7** | **全 `0x90`** |
| **6** | **无障碍启动** | ★ **`0x37F816`/`0x37F82F`/`0x37F846`** | — | 2 各 | ★ **`75` → `EB`** |
| **7** | **光标可见性** | **`0x7E01C4`** | **`E8 67 AC B9 FF`** | 5 | **全 `0x90`** |
| **8** | **输入帧启动** | **`0x0FD99C`** | **`E8 9F D5 27 00`** | 5 | **全 `0x90`** |

★★★ **⇒ 补丁 5 的 7 字节反汇编：**
```
`52`            ⇒ `push edx`
`FF 15 18 38 9D 0E` ⇒ `call dword ptr [0x0E9D3818]`   ← ★ **间接调用**（IAT）
        ↓
★★★ ⇒ 7 字节全 NOP ⇒ **完全跳过这个调用**
★★★ ⇒ 且 `FocusRelocatedAddressOffset = 3`（跳过 `0x0E9D3818` 这 4 字节）⇒ **地址可重定位**
```

### ★★★★★ **补丁 6 的三个分支**

```cpp
AccessibilityStartupBranch{ 0x37F816, **0x12** },
AccessibilityStartupBranch{ 0x37F82F, **0x10** },
AccessibilityStartupBranch{ 0x37F846, **0x11** },
```

★★★ **⇒ 三个 `jnz` 的三个不同位移：**
```
`0x37F816` ⇒ `75 12`（+0x12）
`0x37F82F` ⇒ `75 10`（+0x10）
`0x37F846` ⇒ `75 11`（+0x11）
        ↓
★★★ ⇒ 补丁把 **`75` 改成 `EB`**（`jnz` → `jmp`）⇒ **无条件跳过**
★★★ ⇒ **位移字节不变**（`0x12`/`0x10`/`0x11`）
```

### ★★★★★ **补丁 7 的注释（第 920–926 行，逐字）**

```
// LOCAL OVERRIDE (olmod-local, **2026-10-03**). See the header for the measured
// **t=0 / t=4 s byte pairs**. **Two INDEPENDENT pages are checked**, because **a single
// page only proves the packer got that far** -- **2026-10-03 13:37 measured a client that
// ran initialize() the moment 0x0037EE5A flipped (t=2080 ms) and then died at t=4567 ms**,
// while **the 13:27 client that flipped at t=2240 ms survived**.
// **Requiring both pages makes "the unpack is essentially done" much more likely than
// "the packer happened to write this one page".**
```

★★★★★ **⇒ 六个精确值：**
```
**13:37** 的客户端：`0x0037EE5A` 在 **t=2080 ms** 翻转 ⇒ **t=4567 ms 死亡**
**13:27** 的客户端：在 **t=2240 ms** 翻转 ⇒ **存活**
        ↓
★★★ ⇒ **单页翻转不足**
★★★ ⇒ **要求两页都翻转**
```

---

## 二、★★★★★ **`startupImageUnpacked()` 的双页判据**

### 2.1 ★★★★★ 完整实现（第 927–968 行）

```cpp
constexpr std::size_t SvLinkEntityRva = **0x0034EF10**;
constexpr std::array<std::uint8_t, 4> SvLinkEntityPrefix{
    **0x55, 0x8B, 0xEC, 0x83**,      // ★ push ebp; mov ebp,esp; and ...（标准序言）
};

bool startupImageUnpacked()
{
    ...PE 校验...
    if (SingleInstanceGuardRva + 25 > imageSize ||
        SvLinkEntityRva + 4 > imageSize) return false;
    const auto *guard = module + **0x37EE5A**;
    if (guard[0] != **0x81** || guard[1] != **0x3D** || guard[2] != **0xC0**) return false;  // ★ 只查 3 字节
    const auto *entity = module + **0x0034EF10**;
    for (index...) if (entity[index] != SvLinkEntityPrefix[index]) return false;            // ★ 查 4 字节
    return true;
}
```

★★★★★ **⇒ 两个判据的**不对称**：**
```
页 A：`0x37EE5A` ⇒ 只查 **3 字节**（`81 3D C0`）
      理由：第 4 字节起是**可重定位地址**（`80 1F 0E B7`）,会变
        ↓
页 B：`0x0034EF10` ⇒ 查 **4 字节**（`55 8B EC 83` = `push ebp; mov ebp,esp; and ...`）
      理由：**标准 x86 函数序言**,不含地址
```

★★★ **⇒ 与报告 126 的 `.tp3` 密文/明文对照**完全吻合** ✓**
```
报告 126：`0x0034EF10` 在 t≤2068ms 读 **`EC 36 00 01 8D 39 B0 0F`**（密文）
          在 t=4065ms 读 **`55 8B EC 83 E4 F8 ...`**（明文）
        ↓
★★★ 本报告：前缀是 **`55 8B EC 83`** ✓
★★★ 而密文首字节是 **`EC`** ≠ **`55`** ⇒ **密文时不通过** ✓
```

### ★★★ 结论：`startupImageUnpacked()` 是**只读、无副作用**的就绪信号

★ **⇒ 两页都匹配 ⇒ 可以安全地跑补丁。**

---

## 三、★★★★★ **`inspect*` 的八种状态机**

### 3.1 ★★★★★ 五种状态机类型

```cpp
SingleInstanceGuardState:  Original / Patched / **LegacyBypass** / Unexpected   // ★ 4 个
ClientFramePatchState:     Original / Patched / Unexpected                      // 3 个
FrontendStartupPatchState: Original / Patched / Unexpected
AudioStartupPatchState:    Original / Patched / Unexpected
FocusStartupPatchState:    Original / Patched / Unexpected
AccessibilityStartupPatchState: Original / Patched / Unexpected
CursorVisibilityPatchState: Original / Patched / Unexpected
InputFrameStartupPatchState: Original / Patched / Unexpected
```

★★★ **⇒ 只有单实例守卫有 **`LegacyBypass`**（`0xEB` 已经存在）。**

### ★★★★★ **`inspectSingleInstanceGuard` 的六步判定**（第 174–223 行）

```cpp
① 长度检查（`SingleInstanceGuardRva > size || 25 > size - rva`）⇒ Unexpected
② 逐字节比对，**跳过** `[23]`（分支操作码）和 `[2..5]`（可重定位地址）
③ 名字检查（`0x9DBA14`）：必须是 **Client** 或 **Dedicated** 之一 ⇒ 否则 Unexpected
④ `guard[23] == 0xEB` ⇒ **LegacyBypass**
⑤ `guard[23] != 0x75` ⇒ Unexpected
⑥ `hasDedicatedName` ⇒ **Patched**；`hasClientName` ⇒ **Original**
```

★★★ **⇒ 五层判定的完整矩阵：**

| `guard[23]` | 名字 | 结果 |
|---|---|---|
| `0xEB` | 任意 | ★ **`LegacyBypass`** |
| `0x75` | **Dedicated**（…BB31） | ★ **`Patched`** |
| `0x75` | **Client**（…BB30） | ★ **`Original`** |
| 其他 | 任意 | `Unexpected` |
| 任意 | 其他名字 | `Unexpected` |

### ★★★★★ **`inspectClientFrameCalls` 的混合状态**（第 225–252 行）

```cpp
bool hasOriginal{};
for (const auto &call : ClientFrameCalls)
{
    if (equal(actual, call.bytes)) { hasOriginal = true; continue; }   // ★ 原始
    if (!all_of(actual, [](b){ return b == 0x90; })) return Unexpected;  // ★ 必须全 NOP
}
return hasOriginal ? **Original** : **Patched**;
```

★★★ **⇒ 一个**部分补丁**的判定：**
```
4 个调用中**任意一个**是原始 ⇒ **Original**（可继续补）
4 个**全是** NOP ⇒ **Patched**
任意一个是既非原始也非 NOP ⇒ **Unexpected**
        ↓
★★★ ⇒ 允许**部分补丁状态**（`hasOriginal` 为真 ⇒ 走 `patchDedicatedClientFrameBuffer`）
   ⇒ 会把**全部 4 个**都填 NOP（`std::fill_n` 无条件）✓
```

### ★★★ `inspectAccessibilityStartupBranches` 的同款逻辑（第 337–358 行）

```cpp
if (image[branch.rva + 1] != branch.displacement) return Unexpected;   // ★ 位移必须不变
if (image[branch.rva] == 0x75) { hasOriginal = true; continue; }
if (image[branch.rva] != 0xEB) return Unexpected;
```

---

## 四、★★★★★ **`installDedicatedProcessPatches()` 的完整流程**

### 4.1 ★★★★★ 九步

```
① `GetModuleHandleW(nullptr)` ⇒ module
② DOS/NT 签名校验
③ ★★★ 三重身份校验：
   `FileHeader.Machine == IMAGE_FILE_MACHINE_I386`
   `FileHeader.TimeDateStamp == EngineBindings::ExpectedTimestamp`
   `OptionalHeader.SizeOfImage == EngineBindings::ExpectedImageSize`
④ 八个 `inspect*` 全跑
⑤ 八个全 `Patched` ⇒ **AlreadyPatched**
⑥ 逐个检查 Unexpected ⇒ 返回**专用**错误码
⑦ 计算八个 `patch*` 布尔（只有 `Original` 才补）
⑧ 构造 **9 个 `WritableRegion`**（单实例占 2 个：opcode + name）
⑨ 逐个 `VirtualProtect` ⇒ 失败则**逆序回滚**
⑩ 应用补丁（8 个 `if`）
⑪ `FlushInstructionCache`（全部区域）
⑫ **逆序** `VirtualProtect` 恢复
```

### ★★★★★ **9 个 `WritableRegion` 的完整表**

| # | 地址 | 大小 | 条件 |
|---|---|---|---|
| **1** | `module + 0x37EE5A + 23` | ★ **1** | `patchGuard` |
| **2** | `module + 0x9DBA14` | ★ **43**（GUID 长度） | `patchGuard` |
| **3** | `module + 0xFE650` | ★ **0x69**（105） | `patchClientFrame` |
| **4** | `module + 0x0FD694` | **5** | `patchAudioStartup` |
| **5** | `module + 0x37F8B8` | **5** | `patchFrontendStartup` |
| **6** | `module + 0x37F8D8` | ★ **7** | `patchFocusStartup` |
| **7** | `module + 0x37F816` | ★ **0x32**（50） | `patchAccessibilityStartup` |
| **8** | `module + 0x7E01C4` | **5** | `patchCursorVisibility` |
| **9** | `module + 0x0FD99C` | **5** | `patchInputFrameStartup` |

★★★ **⇒ 第 7 条的跨度：**
```
`AccessibilityStartupPatchStartRva` = **0x37F816**
`AccessibilityStartupPatchEndRva`   = **0x37F846 + 2** = **0x37F848**
        ↓
★★★ 大小 = **0x37F848 - 0x37F816** = **0x32** = **50 字节**
★★★ ⇒ 覆盖**三个分支**（`0x37F816`/`0x37F82F`/`0x37F846`）的连续区间
```

### ★★★★★ **`patchGuard` 的语义**（第 734 行）

```cpp
const auto patchGuard = guardState != SingleInstanceGuardState::Patched;
```

★★★ **⇒ **只要不是 `Patched` 就补**（包括 `LegacyBypass`）。**
**⇒ 这与 `patchDedicatedSingleInstanceBuffer` 的第 410–412 行**一致**：**
```cpp
if (state != Original && state != LegacyBypass) return false;
```

### ★★★ 逆序回滚（第 782–793 行）

```cpp
for (auto index = protectedRegionCount; index-- != 0;)
{
    auto &protectedRegion = regions[index];
    if (!protectedRegion.enabled) continue;
    VirtualProtect(..., protectedRegion.oldProtection, &ignored);
}
```

★★★ **⇒ 失败时**逆序**恢复已改的保护（`index--` 是后置递减 ⇒ 从 `protectedRegionCount-1` 开始）。**

### ★★★ 结果名（13 个）

```
patched / already_patched / unsupported_host / unexpected_bytes /
unexpected_single_instance_bytes / unexpected_client_frame_bytes /
unexpected_frontend_startup_bytes / unexpected_focus_startup_bytes /
unexpected_accessibility_startup_bytes / unexpected_cursor_visibility_bytes /
unexpected_input_frame_startup_bytes / unexpected_audio_startup_bytes /
protection_failed
```

---

## 五、★★★★★ **`ClientRenderFrameHook.cpp` —— 材质头的 104 字节布局**

### 5.1 ★★★★★ 完整常量（第 34–39 行，逐字）

```cpp
// CODREF(material): **Load_Material out.exe 0x488250 reads 104 bytes**;
// **+81 textureCount**, **+92 MaterialTextureDef ***, **12 bytes each**.
constexpr std::size_t MaterialHeaderBytes = **104**;
constexpr std::size_t OffMtlTextureCount  = **81**;
constexpr std::size_t OffMtlTextureTable  = **92**;
constexpr std::size_t TextureDefBytes     = **12**;
```

★★★★★ **⇒ 五个精确值：**
```
`Load_Material` = **`0x488250`**
Material 头 = **104 字节**
`+81` = **textureCount**（**`uint8`**）
`+92` = **MaterialTextureDef***（**指针**）
每个 `MaterialTextureDef` = **12 字节**
```

★★★ **⇒ 结构体布局推断：**
```
`+0..80`   （81 字节：name / 其他字段）
`+81`      **`uint8 textureCount`**
`+82..91`  （10 字节填充/其他）
`+92..95`  **`MaterialTextureDef* textureTable`**（32 位指针）
`+96..103` （8 字节其他）
        ↓
★★★ 总 **104 字节** ✓
```

### ★★★★★ **三个函数指针的签名**（第 24–30 行）

```cpp
using RenderBeginFn = void(__cdecl *)(void *);              // ★ 1 个栈参数
using ImageUploadFn = void(__cdecl *)(void *, void *);      // ★ 2 个栈参数
using FiberSlotFn   = std::uint32_t(__cdecl *)();
using LinkFn        = void *(__cdecl *)(std::uint32_t, void **);
```

★★★ **⇒ 第 2 条的注释（第 26–28 行，逐字）：**
```
"sub_BE7470, __cdecl (void **loadDefSlot, GfxImage *). **Load_GfxImage passes the image
 for BOTH, because the load-def pointer arrives at image+0.**"
        ↓
★★★ ⇒ `Upload(header, header)`（**同一个指针两次**）✓ 第 81 行
```

### ★★★★★ **`rendererAcceptsUploads()` 的三重检查**（第 63–72 行）

```cpp
if (LoadForRendererDvar == nullptr) return false;
const std::uint32_t *const dvar = *LoadForRendererDvar;
if (dvar == nullptr) return false;
// sub_BE7470: `mov ecx, dword_E899CC / cmp dword ptr [ecx+0Ch], 0 / jz`.
return **dvar[3] != 0**;      // ★ [ecx+0Ch] = dvar[3]
```

★★★★★ **⇒ 三个精确值：**
```
`dword_E899CC` ⇒ **`LoadForRendererDvarRva = 0xA899CC`**
`[ecx+0Ch]` = **`dvar[3]`**
        ↓
★★★ ⇒ 反汇编：`mov ecx, dword_E899CC` / `cmp dword ptr [ecx+0Ch], 0` / `jz`
★★★ ⇒ **三级解引用**：`LoadForRendererDvar` → `dvar` → `dvar[3]`
```

### ★★★★★ **`uploadOne` 的七步**

```
① `FiberSlot()` ⇒ **必须 == 1**（否则 `WrongFiberSlot`）
② `rendererAcceptsUploads()` ⇒ 否则 `RendererClosed`
③ `memcpy(header + OlfinalGfxImageLoadDefSlot, &loadDef, 4)` ⇒ **把 loadDef 写到 +0**
④ `guardedUpload(header)` ⇒ 否则 `UploadFaulted`
⑤ 读回 `header + OlfinalGfxImageLoadDefSlot` ⇒ `texture`
   ⇒ **null ⇒ `NoTexture`**
⑥ 若 `!job.link` ⇒ **`Published`**（不链接）
⑦ `guardedLink(&slotValue, &entry)` ⇒ 否则 `LinkFaulted`
   ⇒ `entry == null || slotValue == null` ⇒ `LinkRefused`
   ⇒ **`Published`**
```

### ★★★★★ **Fiber slot 必须 = 1 的理由**（第 112–113 行，逐字）

```
"**sub_67C170 reaches `Error("1190")` when the slot is wrong**, and **an error dialog is a
 worse outcome than not uploading**."
```

### ★★★ `Load_GfxImage` 的 +0 → +0x2C 重定位（第 123–124 行，逐字）

```
"The **load def arrives at +0**; **sub_BE7470 relocates it to +0x2C** and **leaves the
 texture in +0**."
```

★★★ **⇒ 完整的 +0 生命周期：**
```
① 我们写 **`loadDef`** 到 **`header + 0`**
② `sub_BE7470` **把 loadDef 搬到 `+0x2C`**
③ `sub_BE7470` **把 `texture` 留在 `+0`**
        ↓
★★★ ⇒ 调用后读 **`header + 0`** 得到**纹理指针** ✓
```

### ★★★ `NoTexture` 的理由（第 138–139 行，逐字）

```
"**sub_BE6F40 writes 0 back when CreateTexture fails**, which is **the only signal it gives**."
```
★★ **⇒ `sub_BE6F40` 是 `CreateTexture` 的封装。**

---

## 六、★★★★★ **`pumpChain` 的三阶段推进**

### 6.1 ★★★★★ 完整实现（第 317–366 行）

```cpp
std::unique_lock lock(ChainMutex, std::try_to_lock);     // ★ try_lock
if (!lock.owns_lock() || !Chain.active) return;
        ↓
if (phase == **Images**)
{
    if (PendingCount != 0) return;                      // ★ 等图像队列排空
    phase = **Materials**;
    return;                                             // ★ 一帧一步
}
if (phase == **Materials**)
{
    if (materials.empty()) { phase = **Models**; return; }
    const auto name = materials.front();
    materials.erase(materials.begin());                  // ★ 弹出一个
    ...publishOneMaterial...
    note("material " + name, ok, ...);
    return;
}
if (phase == **Models**)
{
    if (models.empty()) { phase = **Done**; active = false; return; }
    ...同上...
}
```

★★★ **⇒ 三个关键设计：**
```
① **`try_to_lock`** ⇒ 入队线程**永远不会卡住一帧**
② **一帧一步**（每次 `return`）⇒ **卡住时能在 phase 上看出来**
③ **`Images` 阶段等 `PendingCount == 0`** ⇒ 图像先全部完成
```

### ★★★ `pumpImageUploads` 的分流（第 369–376 行）

```cpp
if (PendingCount == 0)
{
    pumpChain();      // ★ 图像做完了 ⇒ 推进链
    return;
}
...弹出一个 job...
```

### ★★★★★ **一次一个的理由**（第 391–392 行，逐字）

```
"**ONE PER FRAME.** A **512x512 DXT5 chain is 349,552 bytes** through LockRect and
 UpdateTexture; **six of those in one frame is a hitch**."
```

★★★★★ **⇒ 两个精确值：**
```
512×512 DXT5 = **349,552 字节**（= 341.4 KB）
        ↓
★★★ 512×512 = 262,144 像素；DXT5 = 每 16 像素 16 字节 ⇒ 262,144/16 × 16 = 262,144
★★★ 加 mipmap 链（1/4 + 1/16 + ... ≈ 1/3）⇒ **262,144 × 4/3 ≈ 349,525**
★★★ ⇒ **349,552** 与理论值吻合（含 mipmap）✓
        ↓
★★★ ⇒ **一帧六个 = 卡顿**
```

### ★★★ 纹理语义的三种判定

| # | 函数 | 判据 |
|---|---|---|
| **1** | `semanticFor(sampler)` | `"normalMap"` ⇒ **5**；`"specularMap"` ⇒ **8**；其他 ⇒ **2** |
| **2** | `semanticForName(name)` | 尾 2 字符 `"_n"` ⇒ **5** / `"_s"` ⇒ **8** / `"_c"` ⇒ **2** |
| **3** | `semanticForName` 的兜底 | 含 `"_s-"` ⇒ **8** / 含 `"_n-"` ⇒ **5** / 其他 ⇒ **2** |

★★★ **⇒ 第 3 条的注释（第 449–450 行，逐字）：**
```
"The **CoD4 pipeline mangles combined maps into `~<name>_s-...~<hash>`**, so **the suffix
 is gone but the role is still readable**."
```

---

## 七、★★★★★ **`queueForgeChain` 的"先全建后入队"**

### 7.1 ★★★★★ 完整流程（第 583–729 行）

```
① `Installed` 检查 ⇒ 否则 "the render-frame hook is not installed"
② `SV_LoadForgeBundle(bundlePath, error)`
③ `cloneSource` 必须非空 ⇒ "no clone source; **a Material is cloned, never authored**"
④ 解析 `models`（空 = 全部）
⑤ 从 models 传递出 `materials`（去重）+ `images`（去重）
   ⇒ 材质缺失 ⇒ 报错并**拒绝整个请求**
⑥ ★★★★★ **先构建每一个图像**（`built` 向量）
   任一个失败 ⇒ **拒绝整个请求**
⑦ 写入 `Chain` 状态（phase = **Images**, active = **true**）
⑧ 逐个 `queueForgeImageUpload(std::move(image), link=**true**)`
```

### ★★★★★ 为什么先全建（第 655–656 行，逐字）

```
"**Build every image BEFORE queueing anything, so a bad one refuses the whole request
 rather than leaving the client half published.**"
```

### ★★★ 图像路径（第 660 行）

```cpp
const auto file = root / "main" / "images" / (imageName + ".iwi");
```
★★★ **⇒ `<bundle 目录>/main/images/<name>.iwi`。**

### ★★★ 语义的二次判定（第 686–698 行）

```cpp
imageRequest.semantic = **2**;                                    // ★ 默认
for (const auto &materialName : materials)
    for (const auto &texture : material->textures)
        if (texture.image == imageName)
            imageRequest.semantic = semanticFor(texture.semantic);   // ★ 覆盖
```
★★★ **⇒ 从材质里找到该图像的 sampler 名 ⇒ 用 `semanticFor` 转换。**

### ★★★★★ **`publishOneMaterial` 的克隆逻辑**（第 219–269 行）

```cpp
void *const clone = SV_ForgeFindXAsset(table, OlfinalMaterialAssetType, Chain.cloneSource);
if (clone == nullptr) { error = "the clone '" + ... + "' is not in this client"; return false; }

const auto slotCount = std::to_integer<std::uint8_t>(cloneBytes[**OffMtlTextureCount**]);   // ★ +81
std::memcpy(&cloneTable, cloneBytes + **OffMtlTextureTable**, sizeof(cloneTable));         // ★ +92
if (slotCount == 0 || cloneTable == nullptr) { error = "the clone has no texture table"; return false; }

// 用克隆的 104 字节头 + 克隆的纹理表（12 × slotCount）+ 新槽位
auto built = SV_BuildForgeMaterial(
    material.name,
    std::span<const std::byte>{ cloneBytes, **MaterialHeaderBytes** },           // ★ 104
    std::span<const std::byte>{ cloneTable, **TextureDefBytes** * slotCount },    // ★ 12 × N
    slots, resolveImage, error);
```

★★★★★ **⇒ 克隆的完整机制：**
```
① 在客户端里找到 `mc/mtl_t6_wpn_pda`（`OlfinalMaterialAssetType`）
② 读 **`+81`** 得 `slotCount`
③ 读 **`+92`** 得 `cloneTable` 指针
④ 用 **克隆的 104 字节头** + **克隆的纹理表（12 × N）** + **新槽位** 构建新材质
        ↓
★★★ ⇒ **克隆的内存只被 READ**（第 218 行逐字："The clone's own memory is only READ."）
```

### ★★★ `publishOneModel` 的七个字段（第 279–292 行）

```cpp
ref.name             = model.name;
ref.header.assign(model.header.begin(), model.header.end());   // ★ 360 字节
ref.boneNames        = skeleton->second.boneNames;
ref.parentList       = skeleton->second.parentList;
ref.quaternions      = skeleton->second.quaternions;
ref.translations     = skeleton->second.translations;
ref.partClassification = skeleton->second.partClassification;
ref.baseMatrices     = skeleton->second.baseMatrices;
ref.materials        = model.materials;
if (!model.resources.empty()) ref.resource = model.resources.front();
```

★★★ **⇒ 第 282 行注释：**"The bundle carries the **360 bytes** as a fixed array; the ref
wants a **vector**, and the **size check belongs to `SV_BuildForgeXModel`**."

### ★★★ `renderFrameHook` 的裸函数（第 404–419 行）

```cpp
__declspec(naked) void renderFrameHook()
{
    __asm
    {
        pushad
        pushfd
        call pumpImageUploads
        popfd
        popad
        jmp dword ptr [RenderBegin]     // ★ 尾跳,栈不动
    }
}
```

★★★ **⇒ 注释（第 406–409 行，逐字）：**
```
"**Transparent by construction**: run the pump, then **tail-jump to the original with the
 stack exactly as the call site left it**, so its own `retn` returns to **0x00BE2213** and
 the caller's `add esp, 4` still balances. **Nothing here needs to know sub_BE2150's signature.**"
```

### ★★★ `installClientRenderFrameHook` 的五个 RVA 长度校验（第 506–514 行）

```cpp
if (RenderFrameCallSiteRva + 5 > imageSize ||
    RenderFrameTargetRva >= imageSize ||
    ImageUploadRva >= imageSize ||
    FiberSlotRva >= imageSize ||
    LoadForRendererDvarRva >= imageSize ||
    **DBLinkXAssetEntryRva** >= imageSize)
    return UnsupportedHost;
```

### ★★★ 三个内存所有权容器

```cpp
std::vector<Job> Pending;                                    // 待处理
std::vector<std::unique_ptr<SvForgeGfxImage>> **Retained**;   // ★ 永不释放
std::vector<ForgeImageUploadRecord> Records;                 // 结果
        ↓
Chain:
std::vector<std::unique_ptr<SvForgeMaterialAsset>> **retainedMaterials**;
std::vector<std::unique_ptr<SvForgeXModelAsset>>   **retainedModels**;
```

★★★ **⇒ 三处注释都说同一件事：**"**Published assets are never released: the engine keeps
the pointers**"（第 57/181–182 行）。**

---

## 八、★★★★ **`queueForgeImageDirectory` 的批量路径**

### 8.1 ★★★★★ 六步

```
① `is_directory(root)` ⇒ 否则 `{"not a directory"}`
② 遍历，取 `.iwi`（扩展名**转小写**后比较）
③ `std::sort(files)` ⇒ **确定性顺序**
④ `report.found = files.size()`
⑤ 逐个读文件 ⇒ 建图像 ⇒ 入队
⑥ 失败记入 `report.failures`（**file, why**）
```

### ★★★ 与 `queueForgeChain` 的对比

| 项 | `queueForgeChain` | `queueForgeImageDirectory` |
|---|---|---|
| 原子性 | ★ **全建后入队**（任一失败 ⇒ 全拒） | ★ **逐个**（失败只跳过该个） |
| 语义来源 | 材质里的 `sampler` 名 | ★ **文件名的后缀** |
| 路径 | `<root>/main/images/<name>.iwi` | 目录内所有 `.iwi` |

★★★ **⇒ 两种语义，两种容错策略。**

---

## 九、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★★★ **单实例守卫 RVA** | **`0x37EE5A`**（25 字节）/ 名字 **`0x9DBA14`** |
| 2 | ★★★★★ **25 字节** | **`81 3D C0 80 1F 0E B7 00 00 00 8B 45 08 53 56 57 8B 7D 10 89 44 24 10 75 2D`** |
| 3 | ★★★★★ 反汇编 | `cmp dword ptr [0x0E1F80C0], **0xB7**` / `mov eax,[ebp+8]` / `push ebx,esi,edi` / `mov edi,[ebp+0x10]` / `mov [esp+0x10],eax` / **`jnz +0x2D`** |
| 4 | ★★★ 可重定位 | `[2..5]` = 地址 `0x0E1F80C0`；`[23]` = 分支操作码 ⇒ **比对时跳过** |
| 5 | ★★★★★ **两个 GUID** | Client **`...D2317C94BB30}}`** / Dedicated **`...D2317C94BB31}}`**（**只差末字符**） |
| 6 | ★★★★★ **`OLMOD_CLIENT_INSTANCE`** | **1..9**；替换 **`result[size-4]`**（倒数第 4 字符 = `'3'`）⇒ `2` ⇒ `...BB20}}` |
| 7 | ★★★ 两处范围 | `configuredClientInstance` **1..9**；`patchClientInstanceSingleInstanceBuffer` **2..9** ⇒ **逻辑一致** |
| 8 | ★★★★★ **客户端帧 4 调用** | `0xFE650` **`E8 6B 43 0C 00`** / `0xFE695` **`E8 E6 43 0C 00`** / `0xFE6A9` **`E8 D2 F9 FF FF`** / `0xFE6B4` **`E8 17 72 F7 FF`** |
| 9 | ★★★ 跨度 | **`0xFE650..0xFE6B9`**（**0x69 = 105 字节**）⇒ 一起 `VirtualProtect` |
| 10 | ★★★★★ **音频启动** | **`0x0FD694`** **`E8 77 2F 32 00`** ⇒ 全 NOP |
| 11 | ★★★★★ **前端启动** | **`0x37F8B8`** **`E8 C3 81 CB FF`** ⇒ 全 NOP |
| 12 | ★★★★★ **焦点启动（7 字节）** | **`0x37F8D8`** **`52 FF 15 18 38 9D 0E`** = `push edx; call dword ptr [0x0E9D3818]`；`FocusRelocatedAddressOffset = **3**` |
| 13 | ★★★★★ **无障碍启动（3 分支）** | **`0x37F816`** `75 **12**` / **`0x37F82F`** `75 **10**` / **`0x37F846`** `75 **11**` ⇒ **`75`→`EB`**（位移不变） |
| 14 | ★★★ 无障碍跨度 | **`0x37F816..0x37F848`** = **0x32 = 50 字节** |
| 15 | ★★★★★ **光标可见性** | **`0x7E01C4`** **`E8 67 AC B9 FF`** ⇒ 全 NOP |
| 16 | ★★★★★ **输入帧启动** | **`0x0FD99C`** **`E8 9F D5 27 00`** ⇒ 全 NOP |
| 17 | ★★★★ **13:37 / 13:27 对照** | **13:37**：`0x37EE5A` 在 **t=2080ms** 翻转 ⇒ **t=4567ms 死亡**；**13:27**：**t=2240ms** 翻转 ⇒ **存活** |
| 18 | ★★★★★ **双页判据** | 页 A **`0x37EE5A`** 查 **3 字节**（`81 3D C0`）；页 B **`0x0034EF10`** 查 **4 字节**（**`55 8B EC 83`**） |
| 19 | ★★★ 页 A 只查 3 字节的理由 | 第 4 字节起是**可重定位地址** |
| 20 | ★★★★★ **单实例四态** | `Original` / `Patched` / **`LegacyBypass`（`0xEB`）** / `Unexpected` |
| 21 | ★★★ 判定矩阵 | `0xEB` ⇒ LegacyBypass；`0x75`+Dedicated ⇒ Patched；`0x75`+Client ⇒ Original |
| 22 | ★★★★★ **部分补丁的判定** | 4 调用中**任一原始** ⇒ Original；**全 NOP** ⇒ Patched；否则 Unexpected |
| 23 | ★★★ 无障碍的位移校验 | `image[branch.rva + 1] != displacement` ⇒ **Unexpected** |
| 24 | ★★★ 三重身份校验 | `Machine == I386` && `TimeDateStamp == ExpectedTimestamp` && `SizeOfImage == ExpectedImageSize` |
| 25 | ★★★★★ **9 个 WritableRegion** | opcode(1) / name(**43**) / clientFrame(**105**) / audio(5) / frontend(5) / focus(**7**) / accessibility(**50**) / cursor(5) / input(5) |
| 26 | ★★★ `patchGuard` 语义 | `guardState != **Patched**` ⇒ 补（**含 `LegacyBypass`**） |
| 27 | ★★★ 逆序回滚 | `VirtualProtect` 失败时**逆序**恢复已改的保护 |
| 28 | ★★★ 13 个结果名 | `patched` … `unexpected_audio_startup_bytes` / `protection_failed` |
| 29 | ★★★★★ **`Material` 头 104 字节** | `Load_Material` **`0x488250`**；**`+81` textureCount（`uint8`）**；**`+92` MaterialTextureDef*** |
| 30 | ★★★★★ **`MaterialTextureDef` = 12 字节** | — |
| 31 | ★★★ 四个函数签名 | `RenderBegin(void*)` / **`ImageUpload(void*, void*)`（**同一指针两次**）** / `FiberSlot()` / `Link(u32, void**)` |
| 32 | ★★★★★ **dvar 三级解引用** | `LoadForRendererDvar` → `dvar` → **`dvar[3]`（`[ecx+0Ch]`）**；`dword_E899CC` = **`0xA899CC`** |
| 33 | ★★★★★ **Fiber slot 必须 = 1** | 否则 **`Error("1190")`** ⇒ **错误对话框比不上传更糟** |
| 34 | ★★★★★ **`+0` 生命周期** | 我们写 `loadDef` 到 **`+0`** ⇒ `sub_BE7470` 把 loadDef 搬到 **`+0x2C`**、把 texture 留在 **`+0`** |
| 35 | ★★★ `NoTexture` | `sub_BE6F40`（`CreateTexture` 封装）失败时**写 0**,**唯一信号** |
| 36 | ★★★★★ **`try_to_lock`** | 入队线程**永远不会卡住一帧** |
| 37 | ★★★★★ **一帧一步** | `pumpChain` 每次 `return` ⇒ **卡住时能在 phase 上看出来** |
| 38 | ★★★★★ **一帧一个图像** | 512×512 DXT5 = **349,552 字节**（含 mipmap）；**一帧六个 = 卡顿** |
| 39 | ★★★ 语义判定 3 种 | `sampler` 名（`normalMap`⇒5/`specularMap`⇒8/其他⇒2）/ 后缀（`_n`⇒5/`_s`⇒8/`_c`⇒2）/ **`~` 破坏形式**（`_s-`⇒8/`_n-`⇒5） |
| 40 | ★★★★★ **"先全建后入队"** | 任一图像失败 ⇒ **拒绝整个请求**,**不让客户端半发布** |
| 41 | ★★★ 图像路径 | **`<bundle>/main/images/<name>.iwi`** |
| 42 | ★★★ `cloneSource` 必须非空 | "**a Material is cloned, never authored**" |
| 43 | ★★★★★ **克隆机制** | 读 **`+81`** slotCount、**`+92`** 表指针 ⇒ 用**克隆的 104 头 + 12×N 表 + 新槽位**建新材质 |
| 44 | ★★★ 克隆只读 | "**The clone's own memory is only READ.**" |
| 45 | ★★★ 模型 360 字节 | `ref.header` 从固定数组拷到 vector；**尺寸检查在 `SV_BuildForgeXModel`** |
| 46 | ★★★★★ **尾跳** | `pushad`+`pushfd`+`call pump`+`popfd`+`popad`+**`jmp [RenderBegin]`** ⇒ 返回到 **`0x00BE2213`** |
| 47 | ★★★ 五个 RVA 长度校验 | 六项（含 `DBLinkXAssetEntryRva`） |
| 48 | ★★★ 三处所有权 | `Retained` / `retainedMaterials` / `retainedModels` ⇒ **永不释放**（引擎保留指针） |
| 49 | ★★★ 目录批量路径 | `.iwi` 扩展名**转小写**比较；`std::sort` ⇒ **确定性**；**逐个**容错 |
| 50 | ★★★ 两种容错 | `queueForgeChain` **原子**；`queueForgeImageDirectory` **逐个** |

---

## 十、结论

### 1. ★★★★★ **八个补丁的 RVA 与字节全部精确记录**（含两个 7 字节和三个 2 字节分支）

### 2. ★★★★★ **单实例守卫的 25 字节完整反汇编**

★ **⇒ `cmp [0x0E1F80C0], **183**` + `jnz +0x2D` ⇒ 补丁把 `jnz` 改 `jmp` ⇒ 永远跳过创建。**

### 3. ★★★★★ **两个 GUID 只差末字符**（`…BB30` / `…BB31`）⇒ `memcmp` 可互换

### 4. ★★★★★ **`OLMOD_CLIENT_INSTANCE` 2..9 替换倒数第 4 字符**

### 5. ★★★★★ **双页解包判据有精确的失败对照**（13:37 死 / 13:27 活）

★ **⇒ 页 A 只查 3 字节（因地址可重定位）,页 B 查 4 字节（标准序言 `55 8B EC 83`）。**

### 6. ★★★★★ **`Material` 头的 104 字节布局**（`+81` count / `+92` table / 12 字节/项）

### 7. ★★★★★ **fiber slot 必须 = 1,否则 `Error("1190")`**

### 8. ★★★★★ **`+0` 的三段生命周期**（loadDef ⇒ 搬到 +0x2C ⇒ texture 留在 +0）

### 9. ★★★★★ **`try_to_lock` + 一帧一步 + 一帧一个图像** 三个性能设计

★ **⇒ 512×512 DXT5 = **349,552 字节**，一帧六个就是卡顿。**

### 10. ★★★★★ **"先全建后入队"** 保证客户端不会半发布

### 11. ★★★ **`semanticForName` 处理了 CoD4 的 `~<name>_s-...~<hash>` 破坏形式**

---

## 十一、下一步

`game_server` 根剩余：

1. ★ **`EngineBindings.cpp`（917,344 B）** + `EngineBindings.hpp`（133,088 B）
2. ★ **`Appmain.cpp`（565,999 B）**
3. `NativePmoveBindings.cpp`（113,000 / **2,090 行**）
4. `ClientProcessPatches.cpp`（82,545 / **1,815 行**）
5. `ClientCommandTrace.cpp`（27,720 / **602 行**）
6. 然后 `server_mp` 154 文件（12,604,630 B）
