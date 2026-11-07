# RESTORE-003 — 96-entry Table 身份钉死

## 判定

```text
RESTORE003_STATUS           = PARTIAL
TABLE_TYPE                  = COMPOUND_INTERFACE (not single subsystem)
TABLE_OBJECT_TYPE           = UNKNOWN (GFx/Engine composite candidate)
TABLE_ENTRY_COUNT           = 96 (CONFIRMED)
TABLE_ENTRY_SIZE            = 8 bytes (CONFIRMED)

CLUSTER3_ROLE               = SCALEFORM_GFX (CONFIRMED by format strings)
CLUSTER5_ROLE               = UNKNOWN (same access pattern as Cluster 3 this+0x14 path)
CLUSTER10_ROLE              = UNKNOWN

SAME_OBJECT                 = YES (all 96 functions share same ECX)
MULTIPLE_VTABLES            = YES ([State+0x14] has its own vtable; [this+0x4C] has vtable calls)
ROOT_OBJECT_REVISED         = COMPOSITE_OBJECT (not single Engine Root, not single GFx)

RESOURCE_OBJECT             = UNKNOWN (may be GFx resource, not Engine Zone/FF)
RESOURCE_ENTRY              = NOT_LOCATED
ZONE_ENTRY                  = NOT_LOCATED
ASSET_ENTRY                 = NOT_LOCATED
GAME_INIT_ENTRY             = NOT_LOCATED

NEXT_TARGET                 = STOP (需要新的分析策略)
```

## 96-entry Table Access Pattern 全量分析

从 runtime dump 的 96 个函数 prologue（64 bytes each），确认以下分组：

### Group A: this+0x20 → [State+0x14] → vtable[1] — ~26 slots

这些函数的统一模式：
```
mov eax, [ecx+0x20]       ; State Object
mov ecx, [eax+0x14]       ; Event Dispatcher Object
mov edx, [ecx]            ; vtable
mov eax, [edx+0x04]       ; vtable[1]
push format_string        ; ← 全部是 Scaleform/GFx 消息！
push event_type (2)
call eax
```

push 的 format string 全部是 Scaleform/GFx 内容：
- "The method instance::ContextMenu::builtInItemsSet() is not implemented"
- "The method instance::ContextMenu::clone() is not implemented"
- Flash/AS property names (pan, rotate, greenOffset, zoom, etc.)

**结论：这 26 个函数全部是 Scaleform/GFx event dispatch wrapper。**

**包括 Cluster 6 的部分函数 (0x009C4D00, 0x009C49A0, 0x009C4B30, 0x009C4800, 0x009C48A0, 0x009C4DA0) 也是 GFx！**
这推翻了 ICH-025 将 Cluster 6 标为 "Config/Dvar/FS" 的分类。

### Group B: this+0x14 → [+0x40] → [+0x90] — ~15 slots

这些函数：
```
mov eax, [ecx+0x14]       ; Resource Object (直接)
mov ecx, [eax+0x40]       ; Nested Object
mov edx, [ecx+0x90]       ; handle
mov ecx, [edx+0x08]       ; inner object
call 0x00831DF0           ; Base.dll query helper
```

**注意：Cluster 5 的函数 (0x009C37C0..0x009C3920) 也使用这个 pattern！**

这意味着 Cluster 5 和 Cluster 3 的 this+0x14 子群共享同一个 Resource Object chain。

它们可能都是 **GFx 内部 resource management**（GFxResource, GFxMovieDef 等），
而非 Engine Zone/FF/Asset。

### Group C: this+0x4C — ~15 slots

这些函数通过 [this+0x4C] 访问不同子系统：
- bitfield 操作 (+0x68, +0x3E)
- vtable calls (间接调用)
- FP arithmetic
- flag set/clear

这些函数**没有 push GFx 字符串**，也没有使用 [+0x40]→[+0x90] chain。
它们的语义最不明确。

可能是：
- Engine Config/Dvar/FileSystem
- GFxLog/GFxFileHandler
- 或者另一个完全不同的子系统

### Group D: 其他 — FP ops, list management, misc

- FP arithmetic (0x009B9390, 0x009B93C0, 0x009B9770, 0x009BA5B0, 0x009BA620)
- Array/list management (0x009C0010, 0x009BFFA0)
- Simple writes (0x009DEBD0)

## 关键结论

1. **所有 96 个函数共享同一个 ECX** → 确实是同一个对象的 vtable

2. **约 41 个函数是 GFx**（Group A 的 26 + 部分 Group B）
   包括此前标为 Resource/Zone 的 Cluster 3 和 Cluster 6 部分

3. **约 15 个函数通过 this+0x14 → [+0x40] → [+0x90]**
   可能是 GFx resource management（GFxResource 体系）
   语义仍不确定

4. **约 15 个函数通过 this+0x4C**
   最不明确，可能是 Engine 或 GFx 的另一个子系统

5. **96-entry table 不是单一 GFx vtable**
   它是一个复合对象的接口，包含多个子系统的方法
   但 "Root Object" 的身份仍不确定

6. **此前的 "Engine Root Object" 模型整体错误**
   它可能是一个 **GFx/GUI 复合对象** 而非 Engine 核心
   或者是一个 **包装层**（包含 GFx view + Engine 接口）

## 对项目的影响

如果 96-entry table 主要是 GFx/GUI subsystem：

1. Resource/Zone/Asset 加载**不通过**这个 table
2. PRCL 阻塞的是 **GFx UI 初始化**（而非 Engine 核心）
3. Engine 可能有**另一个独立的**初始化路径
4. 此前所有基于 "96-entry table = Engine Root" 的分析需要重新评估

**但是：**
- 0x00CA0000 执行了 global init (写 0xE83C18 = 0x009B9C00)
- Local RM 可以跨越 IIPS Gate
- 进程稳定运行 30s+
- 这些是 Engine 层面的事实

所以 Engine **确实**执行了 bootstrap。
96-entry table 可能只是 bootstrap 的一部分（UI/初始化接口），
而 Engine 的核心初始化可能有其他路径。

## 输出

- RESTORE003_ALL_FUNCTIONS.csv
- RESTORE003_DECISION.md
