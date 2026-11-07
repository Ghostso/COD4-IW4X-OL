# RESTORE-002 — Event Dispatcher → Resource Event → FF/Zone 链定位

## 判定

```text
RESTORE002_STATUS              = D (Event Dispatcher 与 Resource pipeline 无关)
DISPATCHER_OBJECT              = CONFIRMED (Scaleform/GFx object)
DISPATCHER_VTABLE              = CANDIDATE
EVENT_CREATOR                  = CONFIRMED (0x008876F0, Scaleform/GFx event factory)
EVENT_OBJECT                   = CONFIRMED (Scaleform/GFx event)
EVENT_QUEUE                    = UNKNOWN
EVENT_CONSUMER                 = CONFIRMED (process_item = GFx event processor)

DISPATCHER_TO_SLOT41           = REFUTED (不是 Resource chain)
DISPATCHER_TO_008876F0         = CONFIRMED (但都是 Scaleform/GFx)
DISPATCHER_TO_009C2940         = CONFIRMED (但都是 Scaleform/GFx)

RESOURCE_EVENT_CONSUMER        = NOT_FOUND (process_item 是 GFx, 不是 Resource)
FF_ENTRY                       = NOT_LOCATED
ZONE_ENTRY                     = NOT_LOCATED
ASSET_ENTRY                    = NOT_LOCATED

STATE_TRIGGER                  = SCALEFORM_GFX_EVENT
RESOURCE_TRIGGER               = NOT_LOCATED

NEXT_TARGET                    = STOP (Scaleform 链 ≠ Resource 链)
```

## 核心发现：[State+0x14] 是 Scaleform/GFx Event Dispatcher

### Format String 内容揭示真实语义

从 EXE 文件中直接读取被 push 到 event creation 函数的 "format string"：

| 地址 | 内容 | 类型 |
|---|---|---|
| 0x00CD3468 | "The method instance::ContextMenu::builtInItemsSet() is not implemented" | **ActionScript error** |
| 0x00CD34F8 | "The method instance::ContextMenu::clone() is not implemented" | **ActionScript error** |
| 0x00CC40C4 | "pan" | **Flash/AS property** |
| 0x00CC374C | "rotate" | **Flash/AS property** |
| 0x00CC3998 | "greenOffset" | **Flash ColorTransform property** |
| 0x00CD3404 | "zoom" | **Flash/Bink property** |

**这些全部是 Scaleform/GFx (Flash UI) 的错误消息和属性名。**

### 修正后的对象模型

此前 ICH-047~052 将以下对象/函数标为 Resource/Zone：

| 对象/函数 | ICH-047~052 分类 | RESTORE-002 修正 |
|---|---|---|
| [State+0x14] Event Dispatcher | Resource Event Dispatcher | **Scaleform/GFx Event Dispatcher** |
| Cluster 3 (0x009C12D0..0x009C1930) | Resource/Zone manager | **Scaleform/GFx methods** |
| Slot 41 (0x009C2E30) | Resource State Sync | **Scaleform/GFx function** |
| process_item (0x009C2940) | Resource Event Processor | **Scaleform/GFx event processor** |
| 0x009C19C0 | FF_OPERATION | **GFx array resize** (已有 ICH-051) |
| 0x008876F0 | Resource event factory | **Scaleform/GFx event factory** |
| "Root Object" | Engine Root Object | **可能是 Scaleform/GFx movie/view object** |

### "Root Object" 重新解释

96-entry dispatch table 的所有函数（包括 Cluster 1~10）可能都属于
**Scaleform/GFx UI subsystem**，而不是 Engine 核心逻辑。

证据：
1. EXE 导出 22 个 Scaleform C++ symbols（ICH-006/007 确认）
2. Cluster 3 函数 push 的字符串是 ActionScript 错误/属性名
3. "Event Dispatcher" 的 vtable[1] 是 GFx event creation
4. "State Object" 的 +0x2C/+0x2F 可能是 GFx movie 状态
5. "Root Object" 可能是 GFx movie root / view 对象

### 对整个项目的重大影响

如果 96-entry dispatch table 是 **Scaleform/GFx subsystem**：

1. 它不是 Engine 的核心 dispatch 机制
2. Resource/Zone/Asset 加载不通过这个 table
3. PRCL 阻塞的不是 Engine 核心，而是 **GFx UI 初始化**
4. Engine 可能有**另一个**独立的 dispatch/resource 初始化路径
5. 我们一直在分析的可能是 **UI layer** 而不是 **Engine core**

### 但也有另一种可能

96-entry table 可能**同时**包含 GFx 函数和 Engine 函数：
- 某些 cluster 是 GFx（Cluster 3 被确认为 GFx）
- 某些 cluster 是 Engine core（Cluster 5/10 的 Major Init/Major Subsystem）
- "Root Object" 是一个包含多种子系统的复合对象

需要进一步验证其他 cluster 的函数语义。

## RESTORE-001 修正

| RESTORE-001 结论 | RESTORE-002 修正 |
|---|---|
| [State+0x14] = Resource Event Dispatcher | **Scaleform/GFx Event Dispatcher** |
| Cluster 3 = Resource/Zone | **Scaleform/GFx methods** |
| Event = Resource Event | **Scaleform/GFx event** |
| process_item = Resource processor | **GFx event processor** |
| Resource Activation Chain | **Scaleform/GFx UI chain, NOT Resource** |

## Hard Stop

按任务条件 D：证明 Event Dispatcher 与 Resource pipeline 无关。

**EVENT_DISPATCHER_AS_RESOURCE_TRIGGER = REFUTED**

## 输出

- RESTORE002_DECISION.md
