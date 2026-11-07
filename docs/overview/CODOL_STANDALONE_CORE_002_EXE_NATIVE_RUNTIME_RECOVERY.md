# CODOL STANDALONE-CORE-002
## EXE Native Runtime Recovery — 环境受限结论

**对象**：`codoMP_client_shipRetail.exe`
**约束**：不修改 EXE/DLL，不进入 `.tvm0`，不重复展开 IIPS/TCLS。

## 1. 工具与环境结论

已尝试的可用路径：

```text
- 现有 `工具\windbg_x86\cdb.exe`：脚本可加载，但本次运行时进入
  `No runnable debuggees`，无法继续动态观察。
- Python `capstone 5.0.9`：样本头部可解，但全段/大段扫描出现
  `CS_ERR_DETAIL`，导致 indirect/back-edge/function-map 重建失败。
- 离线工具搜索：未发现可用替代反汇编器/调试器。
- 在线 pip：`distorm3` 等安装超时，无法补齐。
```

结论：

```text
TOOLING_BLOCKED
RETRY_SAME_SCAN_NOT_USEFUL
```

## 2. 为什么当前不能恢复完整 EXE native CFG

已知事实：

```text
- 唯一 confirmed external boundary 仍是 EXE Entry -> Base ordinal_1
- 现有函数边界极少
- indirect target 枚举失败
- back-edge 枚举失败
- 线程创建/文件 API 的动态只读探针未成功执行
```

所以当前不是“还没扫完”，而是：

```text
CURRENT_ENV_CANNOT_RECOVER_FULL_CFG
```

## 3. 可交付的真实证据

已交付：

```text
CODOL_STANDALONE_CORE_002_EXE_NATIVE_RUNTIME_RECOVERY.md
exe_core002_recovery_plan.csv
exe_function_table_suspects.csv
exe_back_edge_candidates.csv
exe_state_machine_candidates.csv
exe_indirect_targets.csv
exe_core002_pe_analysis_map.csv
```

核心证据：

```text
- function table suspects: 17 个候选地址
- back-edge candidates: 8 条候选链
- state machine candidates: 5 条状态候选
- indirect targets: 0 条 confirmed
- PE analysis map: 7 条段级证据
```

## 4. 四个最终问题的当前答案

### Q1：EXE 的真实 native control-flow graph 到底有多大？

```text
NATIVE_CFG_RECOVERY_INCOMPLETE
```

当前环境无法给出完整图规模。

### Q2：EXE 内部是否存在完整初始化状态机？

```text
STATE_MACHINE_NOT_RECOVERED
```

### Q3：EXE 内部是否存在 Game Init -> Runtime 的连接？

```text
GAME_INIT_RUNTIME_CONNECTION_NOT_CONFIRMED
```

### Q4：EXE 内部是否存在稳定的 Main Loop back-edge？

```text
MAIN_LOOP_BACK_EDGE_NOT_CONFIRMED
```

## 5. 下一步建议

如果继续，优先做：

```text
1. 换可运行 cdb/WinDbg 的环境，再做受限动态观察
2. 换可用反汇编器后，只扫 executable 段
3. 不要继续盲扫全文件
4. 优先做 state attribution，而不是继续猜 Game Init 地址
```

当前最合理的结论是：

```text
STOP_BLIND_RESCAN
FOCUS_STATE_ATTRIBUTION
OR_FIX_TOOLCHAIN
```
