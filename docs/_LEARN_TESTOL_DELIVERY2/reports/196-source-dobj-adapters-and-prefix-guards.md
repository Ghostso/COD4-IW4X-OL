# 196 · 三个 DObj 适配器与 40+ 条前缀守卫

## 一、范围

本报告学习 `EngineBindings.cpp` 668–868 行。

## 二、`serverDObjGetAdapter` 自己内联

### 2.1 为什么不再调那个函数

```text
out.exe 没有独立的 getter 可以重新指向：
每一个调用点都内联同样的两行（sub_4EC9E0 是其中之一），
这很可能就是为什么一次签名移植挑中了那个谓词 ——【它是唯一形状像 getter 的函数】。
所以在这里也内联它，用本项目已经绑定的 map 和 pool，并【完全去掉这个操作的 RVA 依赖】。
ServerDObjGetTarget 仍保持绑定，因为其它检查会找它；【已经没有东西读它了】。
```

**"唯一形状像 getter 的函数"** —— 这是签名移植的典型陷阱：**按形状找函数，而不是按调用点确认**。

### 2.2 实现

```cpp
static_cast<void>(base);      // 只是为了让 base 的 acquire 读发生
map  = ServerDObjMap.load(acquire);
pool = ServerDObjPool.load(acquire);
if (!map || !pool) return nullptr;
dobjIndex = map[entityNum];
if (!dobjIndex || dobjIndex >= NativeServerDObjCapacity) return nullptr;
return pool + dobjIndex * NativeServerDObjSize;   // 0xD8
```

`static_cast<void>(base)` 是一处刻意的"读而不使用" —— 保持内存序，同时告诉编译器这是有意为之。

**注意 `base` 完全没参与计算**：`map` 和 `pool` 是独立的全局，不需要 `base` 偏移。

## 三、`serverDObjFreeAdapter`：三步清理

```cpp
++*freeCount;
inUse[dobjIndex] = 0;
map[entityNum] = 0;
invokeDObjFree(freeDObj, pool + dobjIndex * 0xD8);
```

**顺序**：先加空闲计数，再清 in-use 位，再清映射，最后调原生释放。

### 3.1 整个函数包在 `__try` 里且 `__except` 是**空的**

```cpp
__try { ... } __except (EXCEPTION_EXECUTE_HANDLER) { }
```

**空处理器** —— 意味着"释放失败就算了"。

**这在哪些情况下可接受**：

- 释放是**尽力而为**；
- 已经改了的状态（`freeCount`/`inUse`/`map`）**不会回滚** —— 所以如果 `invokeDObjFree` 崩溃，前三步已经生效。

**这是一个可以指出的问题**：前三步先改、后四步可能崩，导致**状态与实际不一致**。正确顺序应该是先释放再改状态（或者反过来但用回滚）。

### 3.2 七重前置检查

```cpp
!map || !inUse || !freeCount || !pool || !freeDObj
|| entityNum < 0 || (uint32)entityNum >= 2046
```

**五个指针 + 两个范围**。

## 四、`serverDObjCreateAdapter`：EAX + 三个栈参数

```cpp
__asm {
    mov eax, entityNum       ; 第一个参数在 EAX
    push tree
    movzx ecx, modelCount
    push ecx
    push models
    mov edx, function
    call edx
    add esp, 12              ; 三个栈参数
    mov result, eax
}
```

**四个参数**：EAX = entityNum，栈 = `models` / `modelCount` / `tree`。

### 4.1 压栈顺序与参数顺序**相反**

```text
push tree        （第三个）
push modelCount  （第二个）
push models      （第一个）
```

所以函数签名是 `(models, modelCount, tree, entityNum_in_eax, ...)`。

而声明是：

```cpp
void* serverDObjCreateAdapter(
    void* models, uint16 modelCount, void* tree, int32 entityNum,
    int32, int32, int32)
```

**后面三个 `int32` 是未使用的** —— 说明原生函数可能接受更多栈参数，但这里传了三个。

`add esp, 12` = 三个参数 ✓。

## 五、40+ 条前缀守卫

### 5.1 结构

```cpp
constexpr std::array<std::uint8_t, N> XxxPrefix{ ... };
```

长度从 **5 到 16**，覆盖 `bind()` 要绑定的每一个函数。

### 5.2 `ComFramePrefix`（5 字节）

```text
55 8B EC 56 57      push ebp / mov ebp,esp / push esi / push edi
```

**这正是 §178 里"Com_Frame 的序言恰好落在五字节边界"的那五个字节。**

### 5.3 `DBLinkXAssetEntryPrefix`（10 字节）

```text
55 8B EC 83 EC 24 8B 45 0C 8B
push ebp / mov ebp,esp / sub esp,24h / mov eax,[ebp+0Ch] / mov ...
```

**`8B 45 0C` = `mov eax,[ebp+0Ch]`** —— 正好是 §182 里"它的序言从 `[ebp+0xC]` 读第二个参数，所以这是普通 `__cdecl`"的证据。**前缀守卫把这个证据固定下来了。**

### 5.4 `SVLinkEntityPrefix`（16 字节，最长）

```text
55 8B EC 83 E4 F8 83 EC 3C 53 56 8B F0 8B CE 81
push ebp / mov ebp,esp / and esp,-8 / sub esp,3Ch
push ebx / push esi / mov esi,eax / mov ecx,esi / [81 ...]
```

最后那个 `81` 是 `add/or/and/sub/cmp` 的 opcode 起始 —— **停在这里，因为下一条是绝对地址操作数**。

### 5.5 那条关于"停在哪里"的注释

```cpp
// Prefix guards stop before loader-relocated absolute operands. The
// opcode and addressing form remain fixed while ASLR rewrites the
// following image address.
```

**同一个原则在两处出现**：

```cpp
// Stop before loader-relocated absolute address operands.  （SVUnlinkEntityPrefix）
```

**`0x8B 0x04 0xC5`（`CCSGetConstantStringPrefix`）** 就是 `mov eax, [eax*8 + abs32]` —— `0xC5` 是 ModRM/SIB，后面跟 4 字节绝对地址。

**所以守卫必须停在那里**，否则 ASLR 一改就失配。

### 5.6 `ByteDirectionsPrefix`（12 字节，不是代码）

```text
4F 96 06 BF 00 00 00 00 44 C4 59 3F
```

**这不是指令** —— 它是一段**数据**：

```text
4F 96 06 BF   → 0xBF06964F  (?)
00 00 00 00
44 C4 59 3F   → float 0.850000024
```

注释（§194 里提到过）：

```cpp
static constexpr std::size_t ByteDirectionsRva = 0xA51C70;
```

**`ByteDirections` 是"方向 → 字节"的查找表**（`DirToByte` 那个）。12 字节 = 3 个 float 或者 1 float + 8 字节其它。

`0x3F59C444` = 0.850000024f —— 这看起来是**某个归一点的分量**。

**这是唯一一个"守卫不是代码前缀"的条目** —— 它是**数据表的内容校验**。

## 六、前缀守卫的完整统计

到 868 行，已经出现 **约 35 条**：

```text
ComFrame(5)              DBFindXAssetHeader(6)    DBLinkXAssetEntry(10)
MsgInit(6)               MsgWriteBits(9)          MsgWriteString(9)
LevelZoneLoad(9)         CollisionMapLoad(7)      CollisionWorldLink(7)
CCSClear(8)              CCSInitialize(9)         CCSGetConstantString(6)
Trace(9)                 WorldTrace(9)            TransformedBrushModelTrace(7)
TransformedCapsuleTrace(9)  CalcTraceExtents(7)   PointTraceToEntities(7)
DObjGeomTracelinePartBits(9)  DObjContentsTracelinePartBits(9)
DObjTraceline(9)         DObjContentsTraceline(9) PointTraceStaticModels(7)
DObjCalcSkel(9)          SVLinkEntity(16)         SVUnlinkEntity(9)
SVTrace(10)              BGGetPlayerEyePosition(9)  BulletEndpos(9)
ByteDirections(12，数据)   ViewMovementDamageKick(9)  ViewMovementIdleAngles(9)
ViewMovementBobAngles(9)   ViewMovementAdsBob(9)
```

**长度分布**：

```text
5   : 1
6   : 2
7   : 4
8   : 1
9   : 17
10  : 2
12  : 1
16  : 1
```

**9 字节最多**（17 条）—— 因为典型的 `push ebp; mov ebp,esp; sub esp,N` 是 3 + 3 + 3 = 9 字节（`sub esp, imm8` 是 3 字节）或 `81 EC imm32` 的组合。

## 七、`DObjTracelinePrefix` 的那条自我标注

```cpp
// `push ebp; mov ebp,esp; and esp,-8; sub esp,364h`. Byte-identical to
// 3.3.3.3's DObjTraceline at 0x00645DD0 for the whole prologue.
// OLMOD(section-84): and READ BACK off out.exe at VA 0x007825F0
// (DObjTracelineRva 0x3825F0) -- same nine bytes, same 0x364 frame.
// The guard is what enforces it; this line records that it was looked
// at on the host and not only inherited.
```

**"这个守卫就是强制执行它的东西；这一行记录的是它在主机上被看过，而不只是被继承。"**

**"被看过" vs "被继承"** —— 这是本项目最核心的方法论区分。

## 八、关键结论

1. **按形状找函数**导致把谓词当 getter；正确做法是确认调用点。
2. **前缀守卫必须停在绝对地址操作数之前**，否则 ASLR 一改就失配。
3. **`ByteDirectionsPrefix` 是数据校验不是代码前缀** —— 唯一一条。
4. **`serverDObjFreeAdapter` 先改状态再调原生释放，且 `__except` 为空** ⇒ 如果原生崩溃，状态已经改了。
5. **9 字节前缀最多**，因为 `push ebp; mov ebp,esp; sub esp,N` 是最常见序言。
6. **"被看过"与"被继承"必须区分**。

## 九、未闭合点

- `serverDObjFreeAdapter` 的状态不一致风险未修。
- `ByteDirectionsPrefix` 那 12 字节的语义未完全解读。
- `EngineBindings.cpp` 868 行之后未读取。
