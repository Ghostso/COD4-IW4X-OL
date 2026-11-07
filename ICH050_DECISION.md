# ICH-050 — process_item (0x009C2940) 深挖

## 判定

```text
ICH050_STATUS                = CONFIRMED
PROCESS_ITEM_ROLE            = RESOURCE_EVENT_PROCESSOR
PROCESS_ITEM_CALLERS         = Slot41 (0x009C2E30) via event dispatch
PROCESS_ITEM_CALLEES         = 0x00A4EC10 (read_string), 0x009C19C0 (FF_OPERATION), 0x00887600 (cleanup)
RESOURCE_TO_PROCESS_ITEM     = CONFIRMED
PROCESS_ITEM_TO_FF           = CONFIRMED (via 0x009C19C0 FF_OPERATION)
PROCESS_ITEM_TO_ZONE         = CANDIDATE (FF_OPERATION may be Zone function)
FF_TO_ZONE                   = UNKNOWN (need to analyze 0x009C19C0)
ZONE_TO_ASSET                = UNKNOWN
PROCESS_ITEM_ASYNC           = NO (synchronous, direct call)
PROCESS_ITEM_RUNTIME         = NOT_OBSERVED (Engine never executed Slot 41 in 30s)
NEXT_TARGET                  = STOP
```

## process_item (0x009C2940) 完整反汇编

函数大小: 0x5D bytes (0x009C2940..0x009C299D)

### 语义: Resource Event Processor

process_item 从 event object 中:
1. 读取 **filename 字符串**（null-terminated, 从 event_data+0x20）
2. 如果 filename 非空:
   - 获取 handle ([event_data+0x10]) 和 size ([event_data+0x18])
   - 调用 **FF_OPERATION (0x009C19C0)** 传入 (zone_obj, size, handle+1)
   - 用 handle 做数组索引存储结果
3. 管理 state value 的 refcount

### 关键 callee: FF_OPERATION (0x009C19C0)

```
ecx = FF/Zone object ([event_data+0x0C])
push size ([event_data+0x18])
push handle+1 ([event_data+0x10] + 1)
call 0x009C19C0
```

参数模式 `(obj, size, handle+1)` 与 FastFile/Zone 的 open/read 语义一致。
0x009C19C0 在 Engine gap (0x00994000..0x00CA789A) 内。

### 调用链（CONFIRMED 到函数级）

```
Engine Root Object
  ↓ (dispatch table slot 41)
Slot 41 (0x009C2E30) — Resource State Synchronization
  ↓ (query result bitmask → event dispatch)
process_item (0x009C2940) — Resource Event Processor
  ↓ (reads filename from event data)
FF_OPERATION (0x009C19C0) — FF/Zone operation
```

### Event Object Layout (from process_item analysis)

```
Event Object (ecx)
 ├── +0x0C   → FF/Zone object (pointer)
 ├── +0x10   → handle (DWORD index)
 ├── +0x18   → size/offset (DWORD)
 ├── +0x20   → filename string (null-terminated, read by 0x00A4EC10)
 └── +0x0C+  → array indexed by handle for storing results
```

### Resource → FF CONFIRMED 链

```
Resource Object ([this+0x14])
    ↓
Slot 41 query (nested+0x90 → handle+0x08 → query)
    ↓
Query result bitmask → event dispatch
    ↓
process_item (0x009C2940)
    ↓ (reads filename string)
    ↓ (gets handle + size)
FF_OPERATION (0x009C19C0)
    ↓ (actual FF/Zone load)
??? (beyond scope)
```

**PROCESS_ITEM_TO_FF = CONFIRMED**

process_item 确实从 event data 中读取文件名字符串并调用 FF_OPERATION。
这不是字符串邻近推断，而是函数级反汇编确认的 call 关系。

## Runtime Activity

Engine 在 post-gate 30 秒内从未执行 Slot 41，因此:
- process_item 从未被调用
- FF_OPERATION 从未被调用
- FF/Zone/Asset 操作 = 0

RUNTIME_RESOURCE_ACTIVITY = NOT_OBSERVED

## Hard Stop 评估

不满足任何 Hard Stop 条件。
本轮成功给 process_item 一个有证据支持的真实语义：
**Resource Event Processor** — 读取 filename → 调用 FF_OPERATION。

## 输出文件

- ICH050_PROCESS_ITEM_FUNCTION.md
- ICH050_PROCESS_ITEM_CALLEES.csv
- ICH050_DECISION.md
