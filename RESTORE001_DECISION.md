# RESTORE-001 — Engine-Side Object/State Restoration

## 判定

```text
RESTORE001_STATUS           = PARTIAL
ROOT_OBJECT_LAYOUT          = CONFIRMED (4-level, including Event Dispatcher)
STATE_OBJECT_LAYOUT         = CONFIRMED (+0x10 bitfield, +0x14 EventDispatcher, +0x2C value, +0x2F saved)
RESOURCE_OBJECT_LAYOUT      = CONFIRMED (from ICH-049, refined)
EVENT_DISPATCHER            = CONFIRMED ([State+0x14] object, vtable[1] = event creation)
STATE_OBJ_CONSTRUCTOR       = NOT_LOCATED
RESOURCE_ACTIVATION         = CANDIDATE ([State+0x14] → vtable[1] → event → process_item)
NEXT_TARGET                 = RESTORE-002 (State+0x14 Event Dispatcher deep dive)
```

## 关键发现：[State+0x14] Event Dispatcher Object

### 发现过程

从 runtime dump 的 15 个 Engine 函数 prologue 中，发现 Cluster 3 的多个函数
都通过同一路径创建 Resource Event：

```
0x009C12D0:
  mov eax, [ecx+0x20]      ; State Object
  mov ecx, [eax+0x14]      ; State->+0x14 = Event Dispatcher Object
  mov edx, [ecx]           ; vtable
  mov eax, [edx+0x04]      ; vtable[1]
  push 0x00CD3468          ; format string
  push 2                   ; event type
  call eax                 ; → creates event + dispatches
```

0x009C1310 使用不同 format string 但相同 event type 2。
0x009C1660 直接读 this+0x14（Resource Object）而不经过 State Object。

### [State+0x14] Event Dispatcher Object

这个对象：
- 存储 在 State Object 的 +0x14 偏移
- 有自己的 vtable
- vtable[1] 是 event creation + dispatch 方法
- 被多个 Cluster 3 函数调用
- 传入 format string 和 event type

**这就是 Resource Event 的实际创建机制。**

### 修正后的 Root Object 完整图

```
Root Object (dispatch table owner)
 ├── +0x00  vtable → 0x00E83B00 (96 entries)
 ├── +0x14  → Resource Object
 │            ├── +0x0C  → counter/list
 │            ├── +0x40  → Nested Object
 │            │            ├── +0x08  → inner query
 │            │            ├── +0x0C  → counter
 │            │            ├── +0x10  → refcount
 │            │            └── +0x90  → handle
 │            └── +0x90  → handle (direct)
 ├── +0x20  → State Object
 │            ├── +0x10  → bitfield (bits 4/5/6)
 │            ├── +0x14  → Event Dispatcher Object ★
 │            │            └── vtable[1] = create event + dispatch
 │            ├── +0x2C  → 24-bit state value
 │            └── +0x2F  → saved byte
 └── +0x4C  → Config/FS Object
```

### State Object Layout (从 Cluster 1 函数确认)

| Offset | Type | 用途 | 确认函数 |
|---|---|---|---|
| +0x10 | DWORD | bitfield (bits 4/5/6 = state flags) | 0x009B9C40, 0x009B9CC0 |
| +0x14 | pointer | → Event Dispatcher Object | 0x009C12D0, 0x009C1310 |
| +0x2C | DWORD | 24-bit state value | 0x009B9C00 (getter), 0x009B9C20 (setter) |
| +0x2F | BYTE | saved byte | 0x009B9C20 (setter) |

### Resource Activation Chain (完整)

```
PRCL dispatch (VM opaque)
    ↓
Slot 41 (0x009C2E30) = Resource State Sync
    → [Root+0x14] → [+0x40] → [+0x90] → query
    → update *arg1
    → per active bit:
        0x008876F0 → create event object
        process_item (0x009C2940) → read filename from state+0x20

Cluster 3 functions (0x009C12D0 etc.)
    → [Root+0x20] → [State+0x14] → vtable[1]
    → push format_string + event_type
    → creates Resource Event

两条路径都汇聚到 Resource Event creation：
  Path 1: Slot 41 → 0x008876F0 → process_item
  Path 2: Cluster 3 → [State+0x14] vtable[1] → event

[State+0x14] Event Dispatcher 是两条路径的交汇点。
```

### 下一步：RESTORE-002

最值得追的对象是 **[State+0x14] Event Dispatcher Object**：
1. 它的 vtable 地址（从 runtime 或静态分析）
2. vtable[1] 的具体函数（event creation）
3. 它接收 format string + event type 的处理逻辑
4. 它的构造者

如果找到 [State+0x14] 的 vtable 和 vtable[1] 函数，
就可以建立完整的 Resource Event → FF/Zone 链。

## 输出文件

- RESTORE001_FUNCTION_DUMPS.csv
- RESTORE001_DECISION.md
