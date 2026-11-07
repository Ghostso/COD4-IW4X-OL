# ICH-051 — FF_OPERATION (0x009C19C0) 深挖

## 判定

```text
ICH051_STATUS              = REFUTED (as FF/Zone loader)
FF_OPERATION_ROLE          = ARRAY_RESIZE_TRUNCATE
PROCESS_ITEM_TO_FF         = REFUTED (downgraded from ICH-050 CONFIRMED)
FF_TO_ZONE                 = UNKNOWN
ZONE_TO_ASSET              = UNKNOWN
NEXT_TARGET                = STOP
```

## 关键发现

ICH-050 将 process_item → 0x009C19C0 标为 CONFIRMED FF bridge。
本轮通过完整反汇编 0x009C19C0（0x76 bytes）发现：

**0x009C19C0 不是 FF/Zone loader。它是一个 dynamic array resize/truncate 函数。**

### 证据

1. 函数读取 [this+0x04] 作为当前 capacity
2. 比较 requested size vs capacity
3. 如果 size < capacity：遍历 array 元素做 refcount decrement + free
4. 如果 size >= capacity：调用 RESIZE (0x0097F580) 重新分配数组
5. 按 25% 增长策略或精确分配

整个函数体没有任何：
- 文件打开/读取调用
- FF 字符串引用
- Zone 初始化逻辑
- Asset DB 操作

### 参数的真实含义

ICH-050 中的参数解释需要修正：
- `handle+1` 不是 FF handle，是 **array new size**（元素数量）
- `size/offset` 不是文件偏移，是 **capacity 调整值**

### process_item (0x009C2940) 的修正语义

process_item 确实从 event data 读取 filename 字符串并调用 0x009C19C0。
但 0x009C19C0 做的是**数组容量管理**，不是文件加载。

修正后的 process_item 语义：
- 读取 filename（通过 read_string）
- 读取 handle 和 size（从 event data）
- 调用 array_resize 调整 FF/Zone object 的 element array 大小
- 将 state value 存入数组指定位置

这是一个 **resource slot allocation/management** 操作，
不是 FF/Zone loader。

## Hard Stop 触发

按任务要求："如果 0x009C19C0 最终只是底层文件读取/句柄操作，也不要硬把它定义成 Zone loader；那就把它降级为 FF I/O primitive"。

实际情况更极端：它甚至不是文件 I/O。它是纯内存数组管理。
因此正式降级。

## 对 ICH-050 的修正

| ICH-050 结论 | ICH-051 修正 |
|---|---|
| PROCESS_ITEM_TO_FF = CONFIRMED | **REFUTED** |
| FF_OPERATION = FF/Zone entry | **ARRAY_RESIZE** |
| handle+1 = FF handle | **array new size** |
| size/offset = file offset | **capacity adjustment** |

## 输出文件

- ICH051_FF_OPERATION_FUNCTION.md
- ICH051_DECISION.md
