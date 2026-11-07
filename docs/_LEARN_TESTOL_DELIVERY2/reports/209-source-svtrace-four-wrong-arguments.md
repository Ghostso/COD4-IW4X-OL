# 209 · 补丁的失败回滚、trace 结果的编解码、`SV_Trace` 四个错参数与"永远上升"

## 一、范围

本报告学习 `EngineBindings.cpp` 3019–3198 行。

## 二、玻璃补丁的**失败回滚**

```cpp
VirtualProtect(first, patchLength, PAGE_EXECUTE_READWRITE, &oldProtection);  // 成功才继续
...
for (const auto& instruction : CallbackInstructions)
    memcpy(module + instruction.rva + 3, &replacement32, 4);
FlushInstructionCache(...);
DWORD ignored{};
if (VirtualProtect(first, patchLength, oldProtection, &ignored))
    return true;                                    // ← 成功路径

// 恢复保护失败 ⇒ 把操作数写回去
for (index...) memcpy(..., &previousOperands[index], 4);
FlushInstructionCache(...);
VirtualProtect(first, patchLength, oldProtection, &ignored);
return false;
```

### 2.1 这段的逻辑

**"恢复保护失败"被当作整个操作失败**，所以要**把操作数写回原值**。

**这是一个少见的"提交后回滚"**：补丁已经写入并刷过缓存，但因为恢复保护失败而判定整体失败，于是撤销。

### 2.2 可以指出的问题

**此时页仍处于 `PAGE_EXECUTE_READWRITE`**（因为恢复失败），所以回滚的 `memcpy` 能成功。

但如果**第一次 `VirtualProtect` 成功、第二次失败**，说明保护状态在这之间变了 —— 而回滚操作本身没有重新 `VirtualProtect` 就直接写，这依赖"页仍可写"这个推断。

## 三、`ScopedGlassState`：`thread_local` 的 RAII

```cpp
class ScopedGlassState final {
public:
    explicit ScopedGlassState(const SvGlassState& glassState)
        : previous_(activeGlassState) { activeGlassState = &glassState; }
    ~ScopedGlassState() { activeGlassState = previous_; }
    // 不可拷贝
};
```

**保存/恢复前值** —— 所以**可以嵌套**（与 §181 的 `NativeStageScope` 不同，那个恢复固定值 `"none"`）。

**这里的 `previous_` 是必要字段** —— 而 `NativeStageScope` 没有，因为它是扁平的。

## 四、`validTraceInput`：五项

```cpp
return contentMask
    && finiteVector(start) && finiteVector(end)
    && finiteVector(bounds.midpoint) && finiteVector(bounds.halfSize)
    && none_of(bounds.halfSize, v < 0);
```

**五项**：掩码非零、两个端点有限、包围盒有限、半尺寸非负。

**与 §`sv_collision_mp.cpp` 的 `validBounds` 不同**：那里还检查 `finiteVector(bounds.midpoint)` 与 `halfSize >= 0`，这里都有；但这里**没有**检查 `bounds.halfSize` 是否全零。

## 五、`decodeTraceResult`：七项校验

```cpp
if (!isfinite(native.fraction) || fraction < 0 || fraction > 1 ||
    any_of(native.normal, !isfinite) ||
    native.hitId > 2047 || native.allSolid > 1 ||
    native.startSolid > 1 || native.walkable > 1)
    return nullopt;
```

### 5.1 七个条件

```text
fraction 有限
fraction ∈ [0, 1]
normal 三个分量有限
hitId <= 2047      （EntityNumNone）
allSolid <= 1
startSolid <= 1
walkable <= 1
```

**`hitId <= 2047`** —— 因为它是 `uint16`，而合法实体号上限是 2047。超过就是垃圾。

**三个布尔字段 `<= 1`** —— 因为原生是 `uint8`，只该是 0 或 1。

### 5.2 三个 bool 的转换

```cpp
.allSolid  = native.allSolid != 0,
.startSolid = native.startSolid != 0,
.walkable  = native.walkable != 0,
```

**`!= 0` 而不是 `== 1`** —— 因为前面已经校验过 `<= 1`，所以两者等价；但 `!= 0` 更宽容。

## 六、`encodeTraceResult`：反方向

```cpp
NativeTraceResult native{};
... 逐字段 ...
native.allSolid = trace.allSolid ? 1 : 0;
```

**`{}` 初始化** —— 所以 `unknownEnd` 被清零。

**`? 1 : 0`** 而不是 `static_cast<uint8>` —— 因为 `bool` 到 `uint8` 的转换值是实现定义的（虽然实践上都是 0/1）。

## 七、`NativeIgnoreEntParams`：12 字节

```cpp
struct NativeIgnoreEntParams {
    int32 baseEntity{};
    int32 parentEntity{};
    uint8 ignoreSelf{};
    uint8 ignoreParent{};
    uint8 ignoreSiblings{};
    uint8 ignoreChildren{};
};
static_assert(sizeof(NativeIgnoreEntParams) == 12);
```

**4 + 4 + 4×1 = 12** ✓

**四个忽略标志**：

```text
ignoreSelf / ignoreParent / ignoreSiblings / ignoreChildren
```

与 §`sv_collision_mp.hpp` 的 `SV_ShouldClipToEntity` 三层排除对应 —— 但**原生有四个维度，项目侧只有三个**（self / parent / owner）。

## 八、`SV_Trace` 的四个错参数：本组最重要的一段

### 8.1 那是一个字节级相同的函数

> **这个编组是 3.3.3.3 的，而八个参数里有四个是错的。整个函数与 `..\ol-mod-ffa` 逐字节相同。**

### 8.2 本 build 的签名

```text
void __usercall sub_46E780(
    float *end@<ecx>, Bounds *bounds@<edx>,
    trace_t *results, float *start, int passEntityNum, int contentMask,
    unsigned __int8, char)          // 六个栈参数，CALLER 清理 0x18
```

### 8.3 从反编译读出的三项

```text
`*a3` 与 0.0 比较 ⇒ a3 是那个首 float 是 fraction 的 trace_t
`a2[3] + a2[4] + a2[5] == 0.0` 选出 point-trace 分支 ⇒ a2 是六 float 的 Bounds
    —— 正好是本项目的 TraceBounds{midpoint[3], halfSize[3]}
a4 与 a1 是两个端点，各自按 bounds midpoint 偏移，
    而 a4 的分量落在【较低】的槽位，这让 a4 是 start、a1 是 end
```

**"a4 的分量落在较低的槽位"** —— 这是从代码里读出参数角色的方法：**看它加到哪个分量上**。

### 8.4 镜像自己证明了映射

```text
sub_46EA60 是一个纯透传：
    sub_46EA60(a, b, c, d, e, f)
        -> ecx = c, edx = d, push a, b, e, f, 0, 0; add esp, 18h
```

**这正是 `SV_Trace(results, start, end, bounds, passEntityNum, contentMask)` 的自然 CoD 顺序**。

而：

> `sub_46E9C0` 与 `sub_46EA10` 是它的 point-trace 兄弟，**两者都在 edx 传一个固定的零 Bounds 全局**。

**"固定的零 Bounds"** 解释了为什么 point trace 不需要 bounds。

### 8.5 那四个错的参数

```text
ecx 拿到了【一个 IGNORE 结构的指针】而引擎要的是 end 位置
edx 拿到了 END 而它要的是 bounds
a5  拿到了 bounds【指针】而它要的是 int 实体号
a7/a8 【从来没压过】，所以引擎从本帧的栈上读两个参数
```

**三个错位 + 两个缺失**。

### 8.6 那个致命的后果

```text
1349 次命中里实测：
    向上法线【零】个
    每次命中都在 fraction 0.0000
    同样的 hitId 2046
    walkable 【从未置位】
所以 groundEntityNum 每一帧都是 ENTITYNUM_NONE，
而玩家每个 pmove 调用上升约【一】个单位，永远。
```

**"每帧上升一个单位，永远"** —— 这正好是玩家"飘在空中"或"贴不上地面"的直接机制。

**而 §205 里 `fraction` 是"调用者预置"的** —— 如果传 0，那么任何命中都是"更近"，结果就是 fraction 恒 0。

## 九、`reportTraceWriteHighWater`

```cpp
void reportTraceWriteHighWater(
    const std::array<std::byte, sizeof(NativeTraceResult) + 512>& padded,
    const bool completed)
{
    std::size_t highest{};
    ...
}
```

**`sizeof(NativeTraceResult) + 512`** —— 多留 **512 字节的填充**，然后报告"引擎写到的最高水线"。

**这是"用填充检测越界写"的标准手法**：

```text
传一个 40 + 512 的缓冲
调用后扫描 512 个填充字节，找出最高被写到的位置
如果 highest > 40，说明结构定义比引擎实际写的少
```

## 十、关键结论

1. **补丁失败要回滚已写入的操作数** —— 这是"提交后撤销"。
2. **`ScopedGlassState` 保存前值所以可嵌套**，而 `NativeStageScope` 恢复固定值所以扁平。
3. **`decodeTraceResult` 的七项校验**覆盖 fraction/normal/hitId/三个布尔。
4. **`SV_Trace` 的四个参数错位**导致"每帧上升一个单位，永远"。
5. **参数角色可以从"它加到哪个分量上"读出**。
6. **"多留 512 字节填充"是检测越界写的标准手法**。

## 十一、未闭合点

- `reportTraceWriteHighWater` 的完整实现未读取。
- `SV_Trace` 的正确编组代码（本组之后）未读取。
- `EngineBindings.cpp` 3198 行之后未读取。
