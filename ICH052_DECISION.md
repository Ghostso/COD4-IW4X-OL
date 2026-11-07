# ICH-052 — Resource Event Producer 定位

## 判定

```text
ICH052_STATUS               = PARTIAL
EVENT_PRODUCER              = 0x008876F0 (Base.dll) — event object factory
FILENAME_SOURCE             = state object +0x20 (via process_item this)
STATE_OBJECT_SOURCE         = Slot 41 caller (arg1 pointer)
EVENT_TYPE_SOURCES          = Slot 41 query result bitmask (bits 0/1/2/3)
DIAGNOSTIC_8189FEC_PRESENT  = NO (Local RM gate crossed)
ENGINE_GATE                 = YES
LOCAL_RM                    = YES
RESOURCE_EVENT_ACTIVITY     = NOT_OBSERVED (Engine never called Slot 41)
FF_ACTIVITY                 = NOT_OBSERVED
ZONE_ACTIVITY               = NOT_OBSERVED
ASSET_ACTIVITY              = NOT_OBSERVED
NEXT_TARGET                 = STOP
```

## Event Producer Chain (完整恢复)

### Event Object Constructor

```
0x008876F0 (Base.dll) — EVENT OBJECT FACTORY
  输入: format_string_ptr, event_type (3/6/5/4), param (0)
  输出: EAX = event object pointer
  
  event object layout:
    +0x0C → refcount
    +0x10 → context
    ...
```

### Event Data Source

```
process_item (0x009C2940) 的 ECX = *arg1
*arg1 是一个 object pointer (state object)
state object +0x20 = event data area

event data area:
  +0x0C  → FF/Zone object (array)
  +0x10  → handle
  +0x18  → size
  +0x20  → filename string (null-terminated)
```

### filename 来源

filename 不在 event object 中。filename 在 **state object 的 +0x20 偏移处**。

state object 由 Slot 41 的 caller 提供（arg1 是 pointer-to-state-ptr）。
Slot 41 做 `mov ecx, [ebx]` (ebx = arg1) 得到实际 object address。

**state object 的构造者是 Slot 41 的 caller。**
Slot 41 的 caller 是 Engine dispatch table 的调用方（VM dispatch 或 Engine 内部调用）。

### 完整 Event Producer Flow

```
1. Slot 41 caller 提供 arg1 (pointer to state object ptr)
2. Slot 41 Phase 1: 查询 Resource subsystem → bitmask
3. Slot 41 Phase 2: 更新 *arg1 = new state
4. Slot 41 Phase 3 (per active bit):
   a. call 0x008876F0 (format_string, event_type, 0) → event object
   b. mov ecx, [ebx] → state object
   c. push event object
   d. call 0x009C2940 (process_item)
      → process_item 从 state object+0x20 读 filename
      → process_item 从 state object+0x10 读 handle
      → process_item 从 state object+0x18 读 size
      → process_item 调用 0x009C19C0 (array resize, NOT FF loader)
```

## 8189FEC 状态标记

在 Local RM v3 环境下（ICH-037~052 所有 baseline）：

```
DIAGNOSTIC_8189FEC_PRESENT = NO
ENGINE_GATE = YES (96 entries, 0xE83C18 = 0x9B9C00)
LOCAL_RM = YES
RESOURCE_EVENT_ACTIVITY = NOT_OBSERVED (Slot 41 never executed in 30s)
FF_ACTIVITY = NOT_OBSERVED (loadfastfile = 0)
ZONE_ACTIVITY = NOT_OBSERVED
ASSET_ACTIVITY = NOT_OBSERVED
```

8189FEC 只在 **IIPS failure path** (无 Local RM) 时出现。
在 Local RM gate crossed 后，8189FEC 不存在。
这确认 8189FEC 是 **上游 IIPS 初始化失败的诊断值**，
与 Engine 内部 Resource Event / FF / Zone / Asset 链无关。

## 修正链状态

```
EXE → Base ordinal 1 → VM → Engine decode → Engine execution
→ 96-entry table → Local RM → IIPS Gate crossed
→ Engine Resource subsystem (CONFIRMED)
→ Slot 41 (CONFIRMED as Resource State Sync)
→ Event Producer 0x008876F0 (CONFIRMED as event factory)
→ process_item (CONFIRMED as Resource Event Processor)
→ array resize 0x009C19C0 (REFUTED as FF loader)
→ FF/Zone/Asset loader → NOT_LOCATED (wrong path closed)
```

## 核心结论

Resource Event 的生产者是 **0x008876F0 (Base.dll)**，它创建 event object shell。
filename 数据来自 **state object +0x20**，而 state object 由 **Slot 41 的 caller** 构造。

Slot 41 的 caller 是 Engine dispatch mechanism（VM 或 Engine 内部）。
**Event 的真正触发者是 dispatch mechanism 选择执行 Slot 41 的那一刻。**

在 Local RM 环境下，Slot 41 在 30 秒内从未被执行。
Resource Event / FF / Zone / Asset 全部 NOT_OBSERVED。

## 输出文件

- ICH052_DECISION.md
