# 197 · 前缀守卫（续）：三条"钉住被重定位操作数"的特例与一个后缀守卫

## 一、范围

本报告学习 `EngineBindings.cpp` 868–1048 行。

## 二、`ScrPrecacheAnimTreesPrefix`：旧前缀**也通过了**

```cpp
// sub_74AF50, NOT the per-tree worker sub_74AAF0 this used to name.
// `mov ebx, [ebp+8]` at the end is the allocator argument; the anim
// user arrives in EDI. The old prefix was
//     0x55, 0x8B, 0xEC, 0x83, 0xEC, 0x20, 0x8B, 0x15, 0x28
// and it passed, because the worker is a real function too.
```

**这是本组最重要的一句话**：

> **旧前缀【也通过了**，因为那个 worker 也是一个真实函数。

即：**字节前缀守卫无法区分两个都存在的函数** —— 它只能证明"这里有一个形状相符的函数"，**不能证明"这是我们想要的那个"**。

**这是一个根本性的守卫局限**，而这里的修法是**靠注释把这段历史记下来**，不是靠更强的守卫。

13 字节前缀：

```text
55 8B EC 51 A1 30 F7 27 08 53 8B 5D 08
push ebp / mov ebp,esp / push ecx / mov eax,ds:0827F730 / push ebx / mov ebx,[ebp+08]
```

`A1 30 F7 27 08` = `mov eax, ds:0827F730` —— **这是绝对地址操作数**（`animConditionBasePointer` 那个全局）。**所以这个守卫也钉住了一个会被 ASLR 重定位的操作数** —— 而它通过了，说明这个镜像就是 RVA 推导时那个。

## 三、`ServerDObjGetSuffix` —— 唯一的后缀守卫

```cpp
constexpr std::array<std::uint8_t, 3> ServerDObjGetSuffix{
    0x8B, 0xC8, 0xB8,
};
```

**`8B C8` = `mov ecx,eax`；`B8` = `mov eax, imm32` 的 opcode 起始**。

**这是唯一一个"后缀"而不是"前缀"** —— 因为 §195/§196 已经证明那个 RVA 指向的是**谓词**而不是 getter，所以守卫方式也变了：**取一个能在内部区分的位置**（`mov ecx,eax; mov eax,...`）。

**名字叫 Suffix 但实际是"某个内部偏移处的字节"** —— 具体在哪里要看 `bind()` 的实现（不在本组）。

## 四、三条"钉住被重定位操作数"的特例

### 4.1 `CurrentCharacterGetPrefix`（10 字节）

```cpp
// CODDIFF(1649370): was 3.3.3.3's 55 8B EC 83 E4 F8 -- a stack-aligning
// prologue this build's function does not have. sub_6B87C0 opens by reading
// its cache directly:  mov eax, ds:0E567C0h / cmp eax, -1 / jnz short.
//
// Bytes 1..4 are a RELOCATED absolute operand. That would disqualify them from
// a cross-build signature (the byte-signature relocation trap), and it does not
// disqualify them here: this guard's whole job is to ask whether the image is
// still the one the RVA was derived against, so pinning the operand makes it
// stricter, not wronger.
constexpr std::array<std::uint8_t, 10> CurrentCharacterGetPrefix{
    0xA1, 0xC0, 0x67, 0xE5, 0x00, 0x83, 0xF8, 0xFF, 0x75, 0x1F,
};
```

**逐字节**：

```text
A1 C0 67 E5 00    mov eax, ds:00E567C0
83 F8 FF          cmp eax, -1
75 1F             jnz short +0x1F
```

**这就是注释描述的代码**，逐字节对应。

### 4.2 那条关键的推理

> **字节 1..4 是一个【被重定位的绝对操作数】。那会取消它们作为跨 build 签名的资格（字节签名重定位陷阱），而它在这里不取消资格：这个守卫的全部工作就是问"这个镜像是否仍是 RVA 被推导时对着的那个"，所以【钉住操作数使它更严格，而不是更错】。**

**这是一个精确的区分**：

| 用途 | 能否钉住重定位操作数 |
|---|---|
| 跨 build 找函数 | **不能**（ASLR/重建都会变） |
| 确认"这是同一个镜像" | **可以，而且更好** |

**同一条字节串，在两种用途下有效性相反。**

### 4.3 `CharacterRecordFillDefaultsPrefix`（16 字节）

```cpp
// sub_619AD0. Bytes 6..10 are the relocated /GS cookie address, pinned on purpose
// for the same reason CurrentCharacterGetPrefix pins its operand: this guard asks
// whether the image is still the one the RVA was derived against.
constexpr std::array<std::uint8_t, 16> CharacterRecordFillDefaultsPrefix{
    0x55, 0x8B, 0xEC, 0x83, 0xEC, 0x44, 0xA1, 0x40,
    0xF2, 0xE3, 0x00, 0x33, 0xC5, 0x89, 0x45, 0xFC,
};
```

**`A1 40 F2 E3 00` = `mov eax, ds:00E3F240`**，`33 C5` = `xor eax, ebp`（/GS cookie 检查），`89 45 FC` = `mov [ebp-4], eax`。

**这是标准的 /GS 序言**：读全局 cookie、与 EBP 异或、存进栈上槽位。

### 4.4 `CharacterRecordToSelectionNamesPrefix`（16 字节）—— 自我守卫

```cpp
// sub_61B6C0, and this one guards itself: the `6A 2C` at bytes 12..13 is the
// `push 0x2C` of its own opening memset, which is the ELEVEN-POINTER output size
// this port depends on. A build whose selection-name array stopped being eleven
// dwords would fail this guard on exactly the byte that says so.
```

**`6A 2C` = `push 0x2C` = push 44**，而 **44 = 11 × 4 = 十一个指针**。

> **一个选择名数组不再是一个 dword 的构建，会【正好在那个说出这一点的字节上】失败。**

**这是最优雅的一种守卫**：**它守的不是"这是同一个函数"，而是"这个我们依赖的尺寸没变"**。

与 §185 里"`CharacterSelectionNameCount = 11`"、§188 里"`array<const char*, 11>`"直接对应。

## 五、`ConfigStringGetPrefix` 的两个字节

```cpp
constexpr std::array<std::uint8_t, 7> ConfigStringGetPrefix{
    0x55, 0x8B, 0xEC, 0x51, 0x81, 0xFE, 0xD9,
};
```

```text
55 8B EC      push ebp / mov ebp,esp
51            push ecx
81 FE D9 ...  cmp esi, 0x31D9      ← 只钉住前两个地址字节
```

**`81 FE` = `cmp esi, imm32`**，后面跟着 `D9`（`0x31D9` 的低字节），**故意只取第一个字节**，因为这是"验证 ESI 是索引寄存器"而不是"验证比较值"。

**但 `D9` 也顺便把它钉住了一半**。

## 六、资产类型常量的完整表

```cpp
AssetTypeXModel              = 4
AssetTypeSound               = 11
AssetTypeClipMapSp           = 14
AssetTypeClipMapMp           = 15
AssetTypeComWorld            = 16
AssetTypeMapEnts             = 19
AssetTypeFxMap               = 20
AssetTypeFx                  = 30
AssetTypeRawFile             = 36
AssetTypeStringTable         = 37
AssetTypeAddonMapEnts        = 42
```

**11 个类型**，而注释对 42 有特别说明：

> CODOL 的 zone 表把它命名为 `addon_map_ents`（类型 42）。**Wetwork 的 zone 把它的实体串放在这里**（`maps/mp/coop_training_mp_cargoship.mapents`），**而普通 MP 地图把它们的放在 19 旁边与 clipmap 一起**。

**这解释了为什么需要两个 MapEnts 类型** —— 战役地图与 MP 地图的存放位置不同。

### 6.1 `ConstantStringTypeSoundAlias = 5`

**CCS 类型 5 = sound alias** —— 与 §152 里"`n ≥ 512` 走客户端自己的常量字符串表（CCS type 5）"完全一致。

### 6.2 `MaximumMapEntityChars = 16 MiB`

**实体串最大 16 MiB** —— 一个非常宽的上限。

## 七、`AssetTypeAddonMapEnts` 与 §184 的 `AssetTypeStructuredDataDef = 39`

两个"特殊编号"：

```text
36  RawFile            ← animtrees/<name>.atr
37  StringTable
39  StructuredDataDef  ← mp/playerdata.def
42  AddonMapEnts       ← Wetwork 的实体串
```

**36 在两个地方出现**：`tryInternScriptString` 之外的 `readAssetSize` 用 `findAsset(36, path)` 读 `.atr`；而 `AssetTypeRawFile = 36` 一致。

## 八、关键结论

1. **字节前缀无法区分两个都存在的函数** —— `ScrPrecacheAnimTrees` 的旧前缀通过了，因为 worker 也是真函数。
2. **同一条字节串在"跨 build 找函数"与"确认同一镜像"两种用途下有效性相反**。
3. **`6A 2C` 守的不是函数身份，而是"我们依赖的尺寸"** —— 最优雅的守卫形态。
4. **`ServerDObjGetSuffix` 是唯一的后缀守卫**，因为那个 RVA 已被证明指向谓词。
5. **42 = `addon_map_ents`**，战役/Wetwork 地图的实体串在这里而普通 MP 地图在 19。
6. **`ConfigStringGetPrefix` 只钉住 `cmp esi, 0x31D9` 的第一个字节**。

## 九、未闭合点

- `ServerDObjGetSuffix` 的具体使用位置（`bind()` 内）未读取。
- `EngineBindings.cpp` 1048 行之后未读取。
