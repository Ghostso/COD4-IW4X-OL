# 215 · 五个阶段名、`valid()` 的 80 项合取、把四者排除的理由

## 一、范围

本报告学习 `EngineBindings.cpp` 4113–4311 行。

## 二、五个阶段名的完整清单

到这里 `bind()` 全部读完，五个阶段：

```text
stage=function_prefixes     ← 约 60 项前缀校验
stage=runtime_slots         ← 六个运行时可写槽
stage=message_bindings      ← validateMessageBindings()
stage=glass_bridge          ← installBrushTraceGlassBridge()
（无阶段名）                 ← PE 头与时间戳/镜像大小
```

**五个明确的失败点，每个都有独立日志**。

**这与 §`Appmain` 里记录的"`bind()` 在 `stage=message_bindings` 失败，整个 dedicated 起不来"直接对应** —— 那次失败就是这四个阶段之一。

## 三、`runtime_slots` 的六项检查

```cpp
if (!writableBytes(pmoveTraceHandlerSlot_, sizeof(Trace) * 2) ||
    pmoveTraceHandlerSlot_[0] != clientPmoveTrace_ ||
    pmoveTraceHandlerSlot_[1] != nullptr ||
    !writableBytes(animConditionBasePointer_, sizeof(void*)) ||
    !writableBytes(animScriptDataPointer_, sizeof(void*)) ||
    !writableBytes(mantleAnims_, sizeof(void*) * 2))
```

### 3.1 五项可写 + 一项值校验

```text
pmoveTraceHandlerSlot_ 可写 8 字节（两个 Trace 指针）
pmoveTraceHandlerSlot_[0] == clientPmoveTrace_    ← 【值校验】
pmoveTraceHandlerSlot_[1] == nullptr               ← 【值校验】
animConditionBasePointer_ 可写 4 字节
animScriptDataPointer_    可写 4 字节
mantleAnims_              可写 8 字节（两个指针）
```

### 3.2 那两条值校验的含义

```cpp
clientPmoveTrace_ = trace_;
```

**所以 `pmoveTraceHandlerSlot_[0]` 应当等于 `TraceRva` 的地址。**

**这是"确认槽里装的就是引擎自己的 `SV_Trace`"** —— 如果它已经是别的（比如另一个 mod 改过），拒绝。

**`[1] == nullptr`** —— 第二个槽应当是空的。

**所以这是"槽还没被别人占"的检查** —— 本项目要往这两个槽里写自己的 trace 处理器。

## 四、那段"留 null 而不是留 3.3.3.3 的 RVA"

```cpp
// CODDIFF(client_loadout_capture): unbound on OLfinal -- no address is
// established on 1649370 for either. Every consumer already null-checks
// these (currentCharacterIndex() and readStagedWeaponSlot() return
// nullopt), so the loadout-capture path degrades rather than misreads.
// Leaving them pointing at the 3.3.3.3 RVAs would have been the silent
// failure instead: a plausible address, called through a function
// pointer, on a build where it is some unrelated function.
```

### 4.1 三点

1. **每个消费者已经检查 null** ⇒ 路径降级而不是误读；
2. **留 3.3.3.3 的 RVA 才是静默失败**；
3. **"一个貌似合理的地址，通过函数指针调用，而它在这个 build 上是某个无关函数"**。

**这与 §183 里"`AnglesToQuaternion 0x3853E0` 被当成 `AnglesToAxis`"是同一种失败** —— 而那次真的发生了。

### 4.2 `WeaponSlotReadStaged` 的理由更精确了

```cpp
// weaponSlotReadStaged_ IS still unestablished: the only address anywhere in this
// tree is CodolWeaponResolve.py's 0x1945B0, and that file targets
// codoMP_client_shipRetail.exe -- 3.3.3.3. Leaving it null is correct.
```

**关键**：`codoMP_client_shipRetail.exe -- 3.3.3.3`

**即"那个文件名对应的是 3.3.3.3 版本，不是本 build"** —— 这解决了 §214 里我指出的张力。

**同一个 EXE 文件名在不同版本里都存在**（本 build 也叫这个名字，SHA256 是 `3699...B537`），所以**文件名不是版本标识**，而 `CodolWeaponResolve.py` 里的那个地址是 3.3.3.3 的。

## 五、`valid()`：**80 项合取**

```cpp
return bindingCommitted_.load(acquire) && module_ &&
    dbFindXAssetHeader_ && dbIsXAssetDefault_ &&
    msgInit_ && msgWriteBits_ && msgWriteString_ &&
    levelZoneLoad_ && collisionMapLoad_ && collisionWorldLink_ &&
    ccsClear_ && ccsInitialize_ && trace_ && worldTrace_ &&
    ... 约 80 项 ...
```

### 5.1 三项结构

```text
1. bindingCommitted_        ← 事务标志
2. module_                  ← 模块基址
3. 约 78 个函数/数据指针
```

### 5.2 那段"不能以非空代替 bind() 成功"

```cpp
// OLMOD(engine-binding-transaction): non-null staged pointers cannot
// substitute for the successful completion of bind(). In particular,
// message validation and glass-bridge failures happen after assignment.
```

**"赋值之后仍可能失败"** —— 所以 `bindingCommitted_` 是必需的。

而 `valid()` 同时检查 `bindingCommitted_` **和**所有指针 —— **因为重绑失败会先清 `bindingCommitted_`，但指针仍是上次的值**。

### 5.3 那四个被排除的指针

```cpp
// CODDIFF(character_customization, client_loadout_capture): four
// pointers that 3.3.3.3 requires here are deliberately NOT part of
// validity on OLfinal -- worldCharacterModelResolve_ and
// characterSelectionResolve_ because §16a establishes the subsystem is
// absent from the build, weaponSlotReadStaged_ and currentCharacterGet_
// because no 1649370 address is established for either.
```

**四个**：

```text
worldCharacterModelResolve_    §16a 不存在
characterSelectionResolve_     §16a 不存在
weaponSlotReadStaged_          无地址
currentCharacterGet_           无地址（但§214 说已解决）
```

**注意：`currentCharacterGet_` 在 §214 里已经被赋值了**：

```cpp
currentCharacterGet_ = (CurrentCharacterGet)(module_ + CurrentCharacterGetRva);
```

**所以这条注释的表述已经过时** —— 它说"无地址"，而实际已经绑上了。

**这是一个可以指出的注释滞后**。

### 5.4 那次"静默失败"

```cpp
// Keeping them in this conjunction is what made the first version of
// this change fail silently: every target still built and all six test
// suites still passed, while valid() would have returned false on the
// first frame and taken the entire engine binding with it.
```

**"每个目标仍然构建，六个测试套件全部通过，而 `valid()` 会在第一帧返回 false 并把整个引擎绑定一起带走"**

**这是一个非常具体的教训**：

```text
编译通过 + 六个测试套件通过  ≠  运行时正确
```

**因为测试不覆盖"第一帧的 valid()"**。

### 5.5 那句"服务器帧不调这四个"

```cpp
// Nothing in the SERVER frame calls any of the four; see
// clientLoadoutBindingsAvailable() for the one path that does.
```

**所以有一个独立的方法 `clientLoadoutBindingsAvailable()` 报告它们** —— 与 §182 里"可选绑定的失败不折进 valid()"完全对应。

## 六、`directionToAngles`：**函数内联的前缀校验**

```cpp
std::optional<array<float,3>> EngineBindings::directionToAngles(
    const array<float,3>& direction) const
{
    constexpr std::size_t rva = 0x364C10;
    constexpr array<uint8_t,16> prefix{
        0x55,0x8B,0xEC,0xD9,0x46,0x04,0x83,0xEC,0x08,0xD9,0xEE,0xD9,0xC0,0xDD,0xEA,0xDF };
    if (!bindingCommitted_ || !module_ ||
        !all_of(direction, isfinite) ||
        !readableSpan(module_+rva, prefix.size()) ||
        !equal(prefix, module_+rva)) return nullopt;
    ...
}
```

### 6.1 这段的特殊性

**这是一个 16 字节的前缀，但它没有出现在 `bind()` 的 OR 链里** —— 而是**每次调用时校验**。

### 6.2 十六字节的解码

```text
55 8B EC        push ebp / mov ebp,esp
D9 46 04        fld dword ptr [esi+4]
83 EC 08        sub esp,8
D9 EE           fldz
D9 C0           fld st(0)
DD EA           fucomp st(2)   （或类似）
DF ...          （后续）
```

**`D9 46 04` = `fld [esi+4]`** —— 与 §194 里 `invokeDirectionToAngles` 的注释"ESI=input, EDI=output"一致：**ESI 是输入向量，所以 `[esi+4]` 是 y 分量**。

**`D9 EE` = `fldz`**、**`D9 C0` = `fld st(0)`** —— 浮点栈操作。

**这是 `vectoangles` 的典型开头**（计算方位角需要 atan2 类型的操作）。

### 6.3 为什么在这里而不是 bind()

**注释没写理由**，但可能的解释是：**这个 RVA 是本文件内部的常量，不在 `EngineBindings.hpp` 的 RVA 表里**，所以不走统一校验。

**这是一处不一致**：其它所有 RVA 都在 `bind()` 里统一校验，而这个每次调用校验。

### 6.4 三重检查

```text
bindingCommitted_（事务）
module_（基址）
direction 三分量有限
prefix 可读
prefix 匹配
```

**五项**。

### 6.5 `NativeStageScope`

```cpp
const NativeStageScope stage("vectoangles");
```

**所以如果 `vectoangles` 崩了，VEH 会报 `stage=vectoangles`**。

**这正是 §193 里那个机制的实际使用**。

## 七、关键结论

1. **五个阶段名**：`function_prefixes` / `runtime_slots` / `message_bindings` / `glass_bridge` / （PE 头无名字）。
2. **`runtime_slots` 检查两件事**：可写 + 槽里装的还是引擎自己的 `SV_Trace`。
3. **留 null 是正确降级，留 3.3.3.3 的 RVA 才是静默失败**。
4. **`valid()` 是 80 项合取**，四个指针被故意排除。
5. **"编译通过 + 六个测试套件通过" 不等于运行时正确** —— 第一帧的 `valid()` 就能带走整个绑定。
6. **`directionToAngles` 的 16 字节前缀是每次调用校验的**，与本文件其它 RVA 的处理不一致。

## 八、未闭合点

- `currentCharacterGet_` 已被赋值，但 `valid()` 的注释仍说它"无地址" —— 注释滞后。
- `directionToAngles` 为何不走 `bind()` 统一校验未说明。
- `EngineBindings.cpp` 4311 行之后未读取。
