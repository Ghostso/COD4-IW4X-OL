# 163 · 原生转换器 ABI 调用、profile def 读取器

## 一、范围

本报告学习 **2 处实现**：

- `NativeEntityStateBindings.cpp` 前 120 行
- `PlayerDataDef.cpp` 前 120 行

## 二、`BG_PlayerStateToEntityState` 的参数位置**变了**

### 2.1 3.3.3.3

```text
BG_PlayerStateToEntityState 0x00413AB0
接收 playerState_s 在 ECX、entityState_s 在 EAX
```

### 2.2 1649370

```text
sub_4116F0 开头：
    4116f4  mov ebx, [ebp+arg_0]    ← playerState_s，从【栈】来
    4116f9  mov edi, eax            ← entityState_s，仍在 EAX
    411703  mov eax, [ebx+104h]     ← 经 ebx 读，输入
    41170c  mov [edi+8], eax        ← 经 edi 写，输出
帧声明恰好【一个】参数槽位
```

诊断：

> **EAX 是对的；playerState 本来要进 ECX，而没有任何东西读 ECX，而被调用者真正读的那个栈槽拿到的是之前就在那里的东西。**

即：把 3.3.3.3 的"ECX 传 playerState"照搬过来，会让被调用者读到一个**残留的栈值**——不崩溃，只是用错数据。

### 2.3 正确的调用序列

```asm
mov eax, entityStateBytes     ; entityState 在 EAX
push playerStateBytes         ; playerState 走栈
mov edx, function
call edx
add esp, 4
```

**cdecl，一个参数**，entityState 走寄存器。这就是"帧只声明一个参数槽"的落地形式。

`__try/__except(EXCEPTION_EXECUTE_HANDLER)` 包裹——注释说明这是 **ol-mod 的进程边界**，不改变原生转换器的寄存器 ABI 或状态所有权。

## 三、事务：先做候选副本

```cpp
auto playerCandidate = playerState;
auto entityCandidate = entityState;
std::byte *previousAnimConditionBase{};
if (!installServerAnimConditionStorage(previousAnimConditionBase))
    return false;
```

注释：

> 原生函数**会改两个输入**，所以源发布要等到**转换、动画上下文恢复、类型化投影**三者全部成功。

即三个候选对象，任一失败都不发布。

### 3.1 线程门

```cpp
if (!valid() ||
    gameThreadId_.load(std::memory_order_acquire) != GetCurrentThreadId())
    return false;
```

`gameThreadId_` 用 `memory_order_acquire` 读——保证读到的是已发布的线程 ID。

## 四、那段"打印输入而不是猜"

```text
"WHAT THIS CALL IS ACTUALLY HANDED"
sub_411280(ps+0x10C, ps+0x108, ps+0x12C)
末尾是 mov [edi+eax*8+0xB8], esi
    edi = 本服务器放进 EAX 的 entityState
    0xB8 = 它的 event 数组（这使 0xD0 成为索引 3，即本 build 已知使用的那个事件槽）
    eax = 由那三个 playerState 字算出的索引
```

> **那里出错是本服务器提供的索引，所以打印输入而不是猜哪一个错了。**

### 4.1 为什么不按内容去重

```text
"又一个全服务器共用的 static，而且更糟：这一行带着 seq@108，
它在几乎每一条命令上都会推进，所以即使按身份做变化检测也不会节流。
这是已经完成使命的 bring-up 诊断，所以按 entity-state 缓冲封顶——
每个客户端的前几次转换才是任何人会读的，
而稳态在 RuntimeLog 的全局锁下约 140 行/秒。"
```

`ReportsPerEntityState = 64`，按 `entityCandidate.bytes.data()` 的**地址**分桶。

### 4.2 日志格式

```text
playerstate->entitystate inputs es=0x%08X esSize=%u eFlags@104=0x%08X
seq@108=%u parms@12C=%u events@10C=%u,%u,%u,%u,%u,%u,%u,%u
```

`events@10C` 打八个字 —— 覆盖 `0x10C..0x128`，即四个 8 字节事件的四个槽（或八个 4 字节字）。

## 五、`PlayerDataDef::open`：逐字段读头 + 三项结构校验

### 5.1 编译期门

```cpp
static_assert(sizeof(void*) == sizeof(uint32_t),
    "the StructuredDataDef pointer fields are 32-bit; this is an x86 image");
```

> def 里的每个指针字段都是一个 32 位字，因为客户端与本插件都是 x86。**64 位构建会静默截断 `pointerAt()` 重建的每一个地址，所以它在这里失败。**

### 5.2 递归深度上限

```cpp
constexpr std::uint32_t MaxTypeDepth = 8;
```

> 类型图里有环的 def 否则会无限递归。**没有任何真实的东西嵌套到这么深——两个随包 def 里最深的路径是"装标量的数组的数组的结构体"。**

### 5.3 头部八个字段

```text
Version / FormatChecksum / StructCount / IndexedArrayCount
RootCategory / RootType / DocumentSize / OffsetTableCount
```

任一读不出即返回 `nullopt`。

### 5.4 三个指针

```cpp
structs_        = pointerAt(def_, Layout::Structs);
indexedArrays_  = pointerAt(def_, Layout::IndexedArrays);
offsetTable_    = pointerAt(def_, Layout::OffsetTable);
```

### 5.5 六项拒绝

```text
!structs_ || !offsetTable_ || !structCount_ || !offsetTableCount_
|| rootCategory_ != CategoryStruct
|| rootType_ >= structCount_
```

注释：**"一个没有 struct、没有偏移表、或者根不是 struct 的 def 不是这个 schema。在这里拒绝它，而不是从它解析出胡说。"**

`indexedArrays_` 可以合法为空，**只有当 def 声明了零个时**：

> 每个随包 def 都声明了一些，**而一个非零计数配空指针是损坏。**

## 六、`pointerAt`：占位符与野指针用同一种方式拒绝

```cpp
if (!readU32(record+offset, raw) || !raw || raw == 0xFFFFFFFFu)
    return nullptr;
address = (const uint8_t*)(uintptr_t)raw;
return readable_(address, 1) ? address : nullptr;
```

注释：

> 一个指针字段在这个 32 位镜像里是 32 位的，而一个**未链接**的 def 携带的占位符是 `0xFFFFFFFF`。**两者用同一种方式拒绝：问它指名的地址是否可读。**

即：`0xFFFFFFFF` 不需要特殊的分支逻辑——它本身就不是可读地址，`readable_` 会拒。但显式写出来更清楚，也避免某些 `Readable` 实现对高位地址有特殊行为。

## 七、`nameEquals`：NUL 是比较的一部分

```cpp
if (!name || want.empty() || want.size() >= MaxNameLength) return false;
if (!readable_(name, want.size()+1)) return false;
return memcmp(name, want.data(), want.size()) == 0 && name[want.size()] == '\0';
```

注释：

> **NUL 是比较的一部分**：没有它，`"primaryBase"` 会匹配 `"primaryBaseSomething"`，**而这个 def 确实携带共享前缀的名字**（`primaryAttach` / `primaryBase`、`lethal` / `lethalDoubleAmmo`）。

这是一个真实存在的歧义：按前缀匹配会选错属性。

`findProperty` 还有一道边界：

```cpp
if (structIndex >= structCount_) return nullopt;
record = structs_ + structIndex * StructRecordBytes;
```

## 八、关键结论

1. **参数的寄存器/栈位置会跨 build 变**，而错位不会崩，只会让别人读到残留栈值。**帧的参数槽个数是最硬的线索**（"exactly one argument slot"）。
2. **原生函数会改输入**，所以必须先做副本，三者（转换/动画上下文/投影）全成才发布。
3. **按内容去重在某些诊断上无效**——字段每条命令都变，只能按对象地址封顶。
4. **前缀匹配是真实的歧义**：`primaryAttach`/`primaryBase` 共享前缀，NUL 必须参与比较。
5. **`0xFFFFFFFF` 占位符与野指针可以用同一条"可读吗"规则拒绝**。
6. **结构合法性要在解析前判**（根必须是 struct、根类型在范围内、指针非空），否则会"从胡说里解析出胡说"。

## 九、未闭合点

- `installServerAnimConditionStorage` 的实现不在本组。
- `resolve(path)` 的完整解析循环不在本组。
- `NativeEntityStateBindings.cpp` 120 行之后的转换与投影未在本组。
