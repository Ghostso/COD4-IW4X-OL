# 179 · profile def 的路径解析与索引累加

## 一、范围

本报告学习 `PlayerDataDef.cpp` 120–319 行。

## 二、`findProperty`：跳过不可读的名字，不整体失败

```cpp
if (!readable_(properties, propertyCount * Layout::PropertyRecordBytes))
    return std::nullopt;

for (position = 0; position < propertyCount; ++position) {
    property = properties + position * PropertyRecordBytes;
    // A property whose name pointer does not read is skipped, not fatal
    if (!nameEquals(pointerAt(property, Layout::PropertyName), name))
        continue;
    ...
    return found;
}
```

注释：

> **名字指针读不出的属性被跳过，而不是致命**：提取出来的 def 携带少量解析到切片之外的 name，**而没有一个是本服务器会问的**。

这是"部分损坏可容忍"的一次有意识选择——**属性表整体可读但个别名字指针越界**时，跳过而不是整体拒绝。

对比 `open()` 里的六项结构校验，那些是**致命的**（没有 struct、没有偏移表、根不是 struct）。区别在于：**结构校验失败意味着"这不是这个 schema"，而单个名字不可读只是"这一条读不到"**。

## 三、`elementSpan`：递归但有限

```cpp
if (depth > MaxTypeDepth(8)) return nullopt;

if (category == CategoryStruct) {
    if (typeIndex >= structCount_) return nullopt;
    readU32(structs_ + typeIndex*StructRecordBytes + StructIndexCount, indexCount);
    return indexCount;
}
if (category == CategoryIndexedArray) {
    array = indexedArray(typeIndex);
    inner = elementSpan(array->elementCategory, array->elementType, depth+1);
    total = (uint64)array->size * *inner;
    if (total > offsetTableCount_) return nullopt;
    return (uint32)total;
}
// Everything else -- int, byte, bool, string, enum -- is one index.
return 1u;
```

### 3.1 三条

1. **struct 占 `indexCount` 个索引**（不是 1）；
2. **indexed array 占 `size × 内层 span`**，且**乘积不能超过偏移表长度**——"因为它索引的就是那张表"；
3. **其余（int/byte/bool/string/enum）各占 1 个索引**。

`uint64` 的乘积然后与 `offsetTableCount_` 比 —— **防溢出**（`size` 与 `inner` 都是 `uint32`，直接乘会溢出）。

### 3.2 为什么递归有界

> **数组的数组之数组不能嵌套得比 def 拥有的类型更深。**

`MaxTypeDepth = 8` 是保守上界，而真实最深的路径（按注释）只是"装标量的数组的数组的结构体"。

## 四、`byteOffset`：一步转换

```cpp
if (index >= offsetTableCount_) return nullopt;
readU32(offsetTable_ + index * 4, offset);
```

这正是引擎 `sub_50F410` 的最后一步：

```text
byteOffset = *(_DWORD *)(*(_DWORD *)(def + 0x38) + 4 * index)
```

## 五、`resolve`：索引累加的五处溢出防护

### 5.1 第一处：属性偏移

```cpp
if (property->offsetIndex >= offsetTableCount_ ||
    index > offsetTableCount_ - property->offsetIndex)
    return nullopt;
index += property->offsetIndex;
```

**两个条件**：偏移本身在表内，且**累加后不越界**（用减法而非加法比较，避免 `index + offset` 溢出）。

### 5.2 第二处：下标 span

```cpp
moved = (uint64)subscript * *span;
if (moved > offsetTableCount_ || index > offsetTableCount_ - moved)
    return nullopt;
index += (uint32)moved;
```

`moved` 用 `uint64` 算，然后**先判 `moved > count`**（此时减法会下溢），**再判 `index > count - moved`**。**顺序不可交换**。

### 5.3 递归保护

`elementSpan(category, typeIndex)` 在 5.2 里被调用时**没有传 depth**，所以从 0 开始——每层 subscript 都重新计数。这是正确的，因为每次调用的嵌套深度是独立的。

## 六、路径语法：点分段 + 方括号剥层

```cpp
while (at <= path.size()) {
    stop = path.find('.', at);
    step = path.substr(at, stop == npos ? stop : stop - at);
    if (step.empty() || !inStruct) return nullopt;

    bracket = step.find('[');
    name = step.substr(0, bracket);
    property = findProperty(structIndex, name);
    if (!property) return nullopt;

    category = property->category;
    typeIndex = property->typeIndex;
    ... 累加 offsetIndex ...

    // 剥掉每一个下标
    cursor = bracket;
    while (cursor != npos && cursor < step.size()) {
        if (step[cursor] != '[') return nullopt;
        close = step.find(']', cursor);
        digits = step.substr(cursor+1, close-cursor-1);
        from_chars(digits, subscript);
        if (category != CategoryIndexedArray) return nullopt;
        array = indexedArray(typeIndex);
        if (!array || subscript >= array->size) return nullopt;
        category = array->elementCategory;
        typeIndex = array->elementType;
        span = elementSpan(category, typeIndex);
        moved = subscript * span;
        index += moved;
        cursor = close + 1;
    }
    ...
}
```

### 6.1 `inStruct` 门

```cpp
if (step.empty() || !inStruct) return nullopt;
```

**一旦落到非 struct（标量或数组），就不能再往下一段点**。所以 `"a.b.c"` 里 `a` 必须是 struct，`b` 必须是 struct，`c` 可以是任何东西。

### 6.2 `from_chars` 的完整校验

```cpp
parse = from_chars(first, first + digits.size(), subscript);
if (parse.ec != std::errc{} || parse.ptr != first + digits.size())
    return nullopt;
```

**`ptr` 必须走到末尾** —— 否则 `"3x"` 会被解析成 3 而忽略 `x`。这是 `from_chars` 的正确用法。

### 6.3 下标必须是 indexed array

```cpp
if (category != CategoryIndexedArray) return nullopt;
```

**对标量或 struct 加下标是错误**，而不是忽略。

### 6.4 剥一层就换 category/typeIndex

```cpp
category = array->elementCategory;
typeIndex = array->elementType;
```

所以 `"a[3][5]"` 里第二个下标作用在**第一层元素类型**上，必须是数组。

### 6.5 多层下标的分隔

`cursor = close + 1` 之后循环继续；`if (step[cursor] != '[')` 保证**两个下标必须紧邻**，`"a[3].b"` 会在 `cursor` 指向 `.` 时……等等，`.` 不在 `step` 里（`step` 已经被 `.` 切开了）。

所以 `"a[3][5]"` 的 `step` 是 `"a[3][5]"`，两次剥层后 `cursor` 越过 `step.size()`，循环结束 ✓。

## 七、停在数组上时报告形状

```cpp
if (category == CategoryIndexedArray) {
    // A path that stops on an array names its element 0 and reports the shape,
    // so a caller asking for "characterClasses" learns that it is twelve
    // elements fourteen indices apart without carrying either number.
    array = indexedArray(typeIndex);
    span = elementSpan(array->elementCategory, array->elementType);
    resolved.count = array->size;
    resolved.stride = *span;
    resolved.category = array->elementCategory;
    inStruct = false;
}
```

**这是 `Resolved` 结构里 `count`/`stride` 两个字段的唯一来源**。

注释给出的具体例子：

> `"characterClasses"` 是**十二个元素、相隔十四个索引**——**而调用方两个数字都不必携带**。

这与头文件里的声明完全一致，也是这个设计最重要的价值：**schema 变了不需要改调用方**。

### 7.1 三种收尾

```text
category == IndexedArray  → 报元素 0 + count/stride，inStruct = false
category == Struct        → structIndex = typeIndex，inStruct = true（可以继续点）
其他                      → inStruct = false（路径结束）
```

## 八、关键结论

1. **单个名字不可读要跳过，结构不符才致命** —— 两者是不同的失败类别。
2. **索引累加必须用减法比较**（`index > count - offset`），加法比较会溢出。
3. **`uint64` 中间量 + 先判 `moved > count` 再判减法**，顺序不可交换。
4. **`from_chars` 必须检查 `ptr` 走到末尾**，否则 `"3x"` 会被静默当成 3。
5. **`inStruct` 门阻止对标量继续点路径**。
6. **停在数组上要报告 `count`/`stride`**，这是"schema 变了不用改调用方"的实现。

## 九、未闭合点

- `resolve` 的 319 行之后（收尾）未读取。
- `PlayerDataDef.cpp` 的全部行数未确认。
