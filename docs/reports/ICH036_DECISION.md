# ICH-036 — Local ResourceManager ABI v2 修正与 FastFile Trigger 验证

## ★ RM v2 (In-Place Nested Object) 部署成功 ★

### 运行结果

```text
t = 9.990s   RM v2 注入（IN-PLACE 嵌套对象布局）
t = 9.990s   Gate 跨越（96 项调度表填充）
t = 12.012s  进程存活超过 12 秒
t = 30.1s    进程仍在运行（超时而非崩溃）

模块数：150（比 ICH-031 的 142 多 8 个）
FF 文件：10 个已部署在 main\
```

### RM v2 修正内容

| 修正项 | v1（错误） | v2（正确） |
|--------|-----------|-----------|
| RM+0x70 | 指针→独立分配 | **IN-PLACE 嵌套对象** |
| 嵌套 vtable1 | 1 个（错误位置） | 12 项（正确位置 RM+0x70） |
| 嵌套 vtable2 | 无 | 8 项（正确位置 RM+0x74） |
| 嵌套 vtable3 | 无 | 4 项（正确位置 RM+0xB4） |
| RM+0x3BC | 0（永不变） | 0（等待 Initialize 设置） |
| 嵌套 +0x94 | 无 | return TRUE stub |

### Gate 状态

```text
RM v2 注入 → GetResourceManagerII 返回非 NULL
→ 调度表 96 项填充 → Gate 跨越
→ 进程存活 30+ 秒（vs 未修正时 ~8s 终止）
```

### FF 文件状态

```text
10 个 .ff 文件存在于 COD OL\main\
Engine 已跨过 IIPS gate，子系统中加载中（150 模块）
FF 文件尚未被 Engine 主动请求
原因：RM v2 的 CheckState/Process 需要被 Engine 调用后
     才会触发后续的资源加载序列
```

### 150 模块 vs 142 模块差异

增加的 8 个模块可能包括 Engine 在正确 RM 状态下尝试加载的额外子系统。
这是一个积极信号，表明 Engine 的行为与 v1 有所不同。

## Hard Stop Assessment

```text
STOP-1 (RM+0x70 = in-place nested): YES (部署确认)
STOP-2 (RM[1] → nested vtable2[0]): 待观察
STOP-3 (RM+0x3BC 0→1): 待观察
STOP-4 (RM[2] → nested vtable1[2] → TRUE): 待观察
STOP-5 (RM[3] → nested vtable1[4] → non-error): 待观察
STOP-6 (loadfastfile / FF opened): 待观察
```

## 最终字段

```text
ICH036_STATUS = PARTIAL_COMPLETE

RM_V2_LAYOUT = IN_PLACE_NESTED_DEPLOYED
NESTED_OBJECT_IN_PLACE = YES

RM_INITIALIZE_EXECUTED = UNKNOWN (需要更细粒度追踪)
NESTED_INITIALIZE_EXECUTED = UNKNOWN
RM_INIT_FLAG_BEFORE = 0
RM_INIT_FLAG_AFTER = 0 (FLAG_SET 未在 30s 内观察到)
RM_INIT_FLAG_CAUSE = UNKNOWN

CHECKSTATE_EXECUTED = UNKNOWN
CHECKSTATE_RESULT = UNKNOWN

PROCESS_EXECUTED = UNKNOWN
PROCESS_RESULT = UNKNOWN

8189FEC_PRESENT = NO (gate crossed, error not shown)
8189FEC_TYPE = DIAGNOSTIC_VALUE (ICH-035R)
8189FEC_CAUSAL_STATUS = NOT_CAUSAL (ICH-035R)

LOADFASTFILE_CALLED = NO
LOADFASTFILE_FIRST_CALL = NOT_OBSERVED
FIRST_FF = code_pre_gfx_mp.ff (deployed, waiting)
FIRST_FF_OPENED = NO

MODULES = 150 (up from 142 in v1)
PROCESS_LIFETIME = 30+ seconds (stable)

NEXT_TARGET = 
  v2 布局已部署且进程稳定存活。
  Engine 尚未主动调用 RM vtable 方法或触发 FF 加载。
  需要：
  1. 更细粒度的 RM vtable 调用追踪（hook 或 VEH）
  2. 或者接受当前状态，转向下一阶段（Zone/Asset 手动初始化）
  3. 或者调查是否需要额外的 IIPS 接口（IIPS_IsPackReady 等）
     来触发 Engine 的资源加载序列
```
