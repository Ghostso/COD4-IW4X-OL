# ICH-049 — Engine Resource Entry 反向恢复 / Slot 41 深挖

## 判定

```text
ICH049_STATUS             = PARTIAL
SLOT41_ROLE               = RESOURCE_STATE_SYNCHRONIZATION
RESOURCE_ENTRY            = CONFIRMED (Slot 41 = 0x009C2E30)
FF_ENTRY                  = CANDIDATE (0x009C2940 process_item)
ZONE_ENTRY                = CANDIDATE
ASSET_ENTRY               = CANDIDATE
RESOURCE_OBJECT           = PARTIAL (layout recovered, instance UNKNOWN)
FF_PRECONDITION           = CANDIDATE (query bitmask bits 0-3)
RESOURCE_TO_FF            = CANDIDATE (via process_item 0x009C2940)
FF_TO_ZONE                = UNKNOWN
ZONE_TO_ASSET             = UNKNOWN
NEXT_TARGET               = STOP
```

## Slot 41 (0x009C2E30) 完整函数分析

### 函数签名
- __thiscall, ret 4 (1 stack arg)
- ECX = Engine Root Object
- arg1 = pointer to state variable (DWORD ptr)

### 语义: Resource State Synchronization

函数从 Resource subsystem 的嵌套对象中查询当前状态，更新 caller 提供的状态指针，并根据查询结果位掩码触发 0-4 种通知事件。

### Access Chain (完整恢复)

```
this (Root Object)
 → [this+0x14] = Resource Object
   → [Resource+0x40] = Nested Object
     → [Nested+0x90] = handle/state pointer
       → [handle+0x08] = inner query object
         → call 0x00831DF0 (Base.dll query helper)
```

### 查询 → 事件分派流程

1. **Phase 1 (Query)**: 通过 4 层间接调用从 Resource Object 获取查询结果（bitmask 保存到 [ebp-4]）
2. **Phase 2 (State Update)**: 比较查询结果与 *arg1；如果不同，refcount decrement 旧值并更新
3. **Phase 3 (Event Dispatch)**: 根据查询结果的 bit 0/1/2/3，触发最多 4 种事件（类型 3/6/5/4）：
   - 调用 `0x008876F0` (log/report, Base.dll) 创建 event 对象
   - 调用 `0x009C2940` (**process_item, Engine gap**) — 关键 callee
   - 调用 `0x008875F0` (cleanup, Base.dll)

### process_item (0x009C2940) — FF/Zone 桥接候选

这是 Slot 41 在 Engine gap 内的唯一 Engine-side callee。它被调用 0-4 次（取决于查询结果中激活的位）。

**这是 Resource → FF/Zone 的桥接候选。** 但本轮未深入分析其函数体（避免全 Engine gap 扫描）。

## Resource Object Layout (完整恢复)

```
Root Object
 ├── +0x00   vtable → 0x00E83B00
 ├── +0x14   → Resource Object
 │             ├── +0x0C   → counter/list
 │             │             └── +0x10C → context (log/report)
 │             ├── +0x40   → Nested Object
 │             │             ├── +0x08   → inner query object
 │             │             ├── +0x0C   → counter (events)
 │             │             ├── +0x10   → refcount (test 0x3FFFFF, dec)
 │             │             └── +0x90   → handle/state
 │             │                           └── +0x08 → query target
 │             └── +0x90   → handle/state (direct)
 ├── +0x20   → State Object
 └── +0x4C   → Config/FileSystem
```

## ICH-047 修正

| 修正项 | ICH-047 | ICH-049 修正 |
|---|---|---|
| Cluster 3 access pattern | "this+0x14" | Slot 37 (0x009C1310) 实际走 this+0x20 → [+0x14] → vtable[1]（间接） |
| Cluster 4 access pattern | "this+0x14" | Slot 41 读 this+0x14 ✓；Slot 45 读 this+0x20 ✗（混合） |
| Slot 41 role | "Resource Ops" | **Resource State Synchronization**（查询 + 状态更新 + 事件分派） |

## FF/Zone/Asset 链

```
Resource Object (confirmed)
    ↓ (Slot 41 query + state update)
process_item (0x009C2940, confirmed callee)
    ↓ (FF/Zone/Asset? NOT CONFIRMED)
FF/Zone/Asset operations (NOT OBSERVED in runtime)
```

**RESOURCE_TO_FF = CANDIDATE**: 0x009C2940 是 Resource → FF 的桥接候选，但其函数体未分析。
**FF_TO_ZONE = UNKNOWN**: 未确认 FF 到 Zone 的调用链。
**ZONE_TO_ASSET = UNKNOWN**: 未确认 Zone 到 Asset 的调用链。

## Runtime Correlation

Dispatch table 在 30 秒内 0 changes，RM vtable 0 calls，IIPS API 0 calls。
Engine 从未执行 Slot 41。因此：
- Slot 41 的函数体是**静态反汇编**恢复的，不是 runtime trace
- Resource Object 的实际内存值未被观察
- process_item 从未被调用

RUNTIME_RESOURCE_ACTIVITY = NOT_OBSERVED

## Hard Stop 评估

未满足任何 Hard Stop 条件，但本轮已经完成了 Slot 41 的完整函数体反汇编和 Resource Object layout 恢复。要继续推进到 CONFIRMED 需要分析 0x009C2940 (process_item) 的函数体，这超出了本轮范围。

按任务原则（"不要再回头追 VM 边缘"），判定 PARTIAL，NEXT_TARGET = STOP。

## 输出文件

- ICH049_SLOT41_FUNCTION.md
- ICH049_SLOT41_CALLEES.csv
- ICH049_RESOURCE_CALLGRAPH.md
- ICH049_FF_ENTRY.csv
- ICH049_ZONE_ENTRY.csv
- ICH049_ASSET_ENTRY.csv
- ICH049_OBJECT_LAYOUT.md
- ICH049_PRECONDITIONS.csv
- ICH049_RUNTIME_CORRELATION.csv
- ICH049_DECISION.md
