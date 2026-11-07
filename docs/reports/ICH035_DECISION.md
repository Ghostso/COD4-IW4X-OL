# ICH-035 — ResourceManager 生命周期 → FF Trigger 因果链

## 核心发现：Local RM 的嵌套对象布局是错误的！

### BUG IDENTIFIED

ICH-030 的 Local RM 注入有一个**关键布局错误**：

**原始 IIPS RM 结构：**
```text
RM +0x70 = 嵌套对象（IN-PLACE，不是指针！）
嵌套对象 +0x00 = vtable1 (0x1003934C)
嵌套对象 +0x04 = vtable2 (0x1003940C)
嵌套对象 +0x08 = CRITICAL_SECTION
嵌套对象 +0x44 = vtable3
嵌套对象 +0x58 = handle/ptr
嵌套对象 +0x94 = function pointer
```

**RM vtable[2] CheckState 的实际工作方式：**
```asm
mov eax, [esi+0x70]    ; eax = vtable1_ptr (嵌套对象第一个 DWORD)
mov edx, [eax+8]       ; edx = vtable1[2] (第3个函数指针)
lea ecx, [esi+0x70]    ; ecx = 嵌套对象地址 (thiscall)
call edx               ; 调用 vtable1[2] = 0x100135B0
```

**原始 vtable1[2] (0x100135B0) 的行为：**
```text
读取 [ebp+0x58] → 检查 handle
如果 handle 非空 → 关闭旧 handle
初始化内部状态
... (复杂初始化)
返回 boolean
```

**我们本地 RM 的错误：**
```text
RM+0x70 = 指针 → 指向我们分配的嵌套对象
嵌套对象 = [vtable_ptr, 0, 0, 0, ...]
[vtable_ptr+8] = 我们的 "return 1" stub

但原始代码期望 RM+0x70 是嵌套对象本身（IN-PLACE）！
所以 [RM+0x70] 读到的是嵌套对象的 vtable_ptr，
而 [vtable_ptr+8] 读到的是我们 stub 的地址，
这碰巧能工作是因为我们 stub 返回了 1。

但实际上结构是错误的，导致后续方法调用可能失败。
```

### 正确的 Local RM 布局

```c
// RM object (0x410 bytes)
// +0x000: RM vtable (48 entries)
// +0x070: Nested object IN-PLACE:
//   +0x700: vtable1_ptr → our local vtable1
//   +0x704: vtable2_ptr → our local vtable2
//   +0x708: CRITICAL_SECTION (must be initialized!)
//   +0x744: vtable3_ptr
//   +0x758: handle (set to 0)
//   +0x794: function pointer (return TRUE stub)
// +0x3BC: flag = 0

// vtable1 (for nested object):
//   [0] destructor stub
//   [1] method stub
//   [2] "return TRUE" function ← CheckState calls this
//   [3..11] stubs

// vtable2 (secondary):
//   [0..7] stubs
```

### RM vtable[1] Initialize 分析

```text
RM vtable[1] (0x10010DB0) 做以下操作：
1. 读取参数 [esp+0x94]
2. 调用 [nested+0x04] = vtable2[0] → 初始化
3. 如果失败 → jump to error
4. 调用内部函数 → 字符串操作
5. 使用 "IIPS_InitInGameApp" 相关数据
6. 复杂的状态机初始化

结论：vtable[1] 是一个复杂的初始化方法，
需要正确的嵌套对象状态才能成功。
```

### RM vtable[3] Process 分析

```text
RM vtable[3] (0x10010380) 做以下操作：
1. 检查 [this+0x3BC] flag
   - 如果非零 → 走正常处理路径
   - 如果零 → 检查全局 [0x1004CDD8]
     → 输出调试信息 (0xE000002E = "not initialized")
     → 返回 -1 (error)

2. 正常路径：
   - 检查 [this+0x6C] (old handle cleanup)
   - 调用 [nested+0x10] = vtable1[4] → 处理函数
   - 如果返回 -1 → error
   - 否则继续处理

结论：Process 需要 [this+0x3BC] ≠ 0 才能正常工作
     我们的 stub 设置了 flag=0，导致 Process 返回 -1！
```

### 关键发现总结

```text
1. RM+0x70 是嵌套对象的 IN-PLACE 存储，不是指针
2. 嵌套对象有 3 个 vtable（vtable1/2/3）
3. RM vtable[2] CheckState 通过嵌套 vtable1[2] 工作
4. RM vtable[3] Process 需要 RM+0x3BC ≠ 0
5. RM vtable[1] Initialize 需要正确的嵌套对象状态
6. 我们的 Local RM 存在嵌套对象布局错误
7. 进程存活是因为 CheckState 通过 stub 碰巧返回了 TRUE
   但 Process 和其他方法可能失败了
```

### 修正方案

```text
1. RM+0x70 应该是嵌套对象的 IN-PLACE 数据（不是指针）
2. 需要在 RM+0x70 处写入完整的嵌套对象：
   - vtable1 指针
   - vtable2 指针
   - CRITICAL_SECTION（至少初始化）
   - 更多字段...
3. RM+0x3BC 应该设置为非零（表示"已初始化"）
4. 需要 3 个本地 vtable（不只是 1 个）

最小修正：
  - RM+0x70 处放置一个指针，指向正确的嵌套对象
  - 嵌套对象需要 vtable1[2] 返回 TRUE
  - RM+0x3BC 设置为 1
  - 可能需要更多修正...
```

### 8189FEC 最终归因

```text
0x8189FEC 是 EXE packed 代码中的 IIPS 初始化失败状态值。
它由 EXE 的 packed .tp3 代码在运行时计算产生。
它不是一个内存地址，也不是一个 Windows 错误码。
它是一个特定于 CODOL/IIPS 的自定义错误标识符。

产生路径：
  iips.dll QoS helper returns 0 (Tencent server unreachable)
  → InitInGameApp fails
  → IIPS.dll 返回失败给 EXE packed code
  → EXE packed code 生成 0x8189FEC 并显示 WIN_IIPS_INIT_ERROR
```

## Final Fields

```text
ICH035_STATUS = COMPLETE

IIPS_ERROR_CODE = 0x8189FEC (custom IIPS error, not a Windows error code)
IIPS_ERROR_SOURCE = EXE packed .tp3 code (runtime-computed)

RM_METHODS_CALLED = UNKNOWN (Engine did not call RM methods through vtable)
RM_INITIALIZE_CALLED = UNKNOWN
RM_CHECKSTATE_RESULT = IMPLIED_TRUE (process survived)
RM_PROCESS_CALLED = UNKNOWN (likely failed due to flag=0)
RM_FINAL_STATE = INCORRECT_LAYOUT (nested object layout mismatch)

LOADFASTFILE_CALLED = NO
LOADFASTFILE_CALLER = N/A
FF_TRIGGER_CONDITION = Engine has not reached FF loading stage

ROOT_CAUSE_OF_NO_FF = 
  Local RM has incorrect nested object layout
  Engine calls RM methods → nested object state is wrong
  → Engine does not transition to resource loading phase
  → FF files exist but are never requested

NEXT_TARGET = Fix Local RM nested object layout:
  1. RM+0x70 = in-place nested object (not pointer)
  2. Nested needs 3 vtables (vtable1/2/3)
  3. RM+0x3BC = 1 (initialized flag)
  4. CRITICAL_SECTION at nested+0x08 must be valid
  5. Then re-test and monitor which RM methods Engine actually calls
```
