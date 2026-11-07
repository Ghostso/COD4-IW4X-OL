# CODOL EX-053 IFS2 Path Causality / IIPS New Execution Node

## Final Classification

```text
IFS2_PATH_CAUSALITY_UNCONFIRMED
IIPS_NEW_NODE_NONE
IIPSHOSTAPP_NODE_NONE
CREATE_IFS_RETURN_DATAFLOW_UNRESOLVED
TVM0_BOUNDARY
OBSERVER_NO_DIVERGENCE
```

EX-053 的直接结果是：在已建立的独立副本上，只改变 IFS2 可见位置，没有获得新的可重复执行节点。基线保持稳定 NODE-B，三个 IFS2 路径候选也都回到同一 fatal window，没有出现 `IFS2.dll`、`IIPSHostApp.exe`、新模块群、新线程群或运行阶段延长。

## 1. Method

```text
observer      : non-invasive CreateProcess + window/module sampling
debugger      : not used as primary experiment
API hook      : not used as primary experiment
EXE patch     : none
8189FEC patch : none
.tvm0 reverse : none
independent copies: 工具\EX053_*
```

## 2. Experiments

```text
EXP053_BASELINE
EXP053_IFS2_PATH_A
EXP053_IFS2_PATH_B
EXP053_IFS2_PATH_C
```

Each experiment changed only one filesystem condition and launched normal `-q` from the experiment directory.

## 3. Baseline Result

PID: `20924`

Observed fatal window:

```text
title : 致命错误
class : #32770
```

Observed relevant pre-fatal modules:

```text
libcef.dll
TenProxy.dll
TenRpcs.dll
policyprobe.dll
tcj.dll
GameRpcs.dll
BugTrace.dll
GbSpy.dll
GDPLoader.dll
codoMP_client_shipRetailBase.dll
```

Not observed in final module snapshot:

```text
iips.dll
IFS2.dll
IIPSHostApp.exe
```

IIPS observer periods:

```text
IIPS_PERIODS []
```

The baseline is stable NODE-B.

## 4. IFS2 Path Result

All three IFS2 visibility experiments returned to the same fatal window and module/time pattern as baseline:

```text
fatal_title     : 致命错误
fatal_text      : 致命错误
new_module      : none
new_thread_cluster: NO
new_window      : none beyond fatal #32770
ifs2_dll_loaded : NO
iipshostapp_loaded : NO
new_execution_node : NONE
```

No stable causality between IFS2 visibility and NODE-B exit was established.

## 5. Conclusion

```text
IFS2_PATH_CAUSALITY_UNCONFIRMED
IIPS_NEW_NODE_NONE
IIPSHOSTAPP_NODE_NONE
CREATE_IFS_RETURN_DATAFLOW_UNRESOLVED
TVM0_BOUNDARY
OBSERVER_NO_DIVERGENCE
```

Stop blind environment expansion.

Next recommended focus is static dataflow around:

```text
LoadLibraryW parameter construction
CreateIFSLibDll return
InitInGameApp caller state
```

without debugger/hook/tvm0.
