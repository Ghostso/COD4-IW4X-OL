# EX-018-RET Result

## Actual execution evidence

Ran original copy from `工具/EXPERIMENT_017_BOOT` under cdb.

Observed:
- Base ordinal_1 entry breakpoint hit (`Base+0x1D6582C`) more than once.
- Base entry `Base+0x149C` hit: `jmp codoMP_client_shipRetailBase+0x1AA13B0`, confirming Base entry/ordinal thunk path jumps toward VM boundary.
- Did not observe a `ret` back to EXE.
- First chance exception: `KERNEL32!IsBadReadPtr+0x5a` (`75CE015A`), same crash-report/BugTrace thread symptom as previous actual run.
- No `RET_TO_EXE` / EXE continuation breakpoint hit.

Executed scripts:
- `工具/exp018.cdb`
- `工具/exp018_ret.cdb`

Result:
```text
PID: in cdb logs (new process each run)
ordinal_1 entry EIP: Base+0x1D6582C (hit)
ordinal_1 RET: NO
RET EIP: N/A
[ESP]: N/A
return module: N/A
return RVA: N/A
RET后第一EXE EIP: N/A
TenProxy: NO
新 DLL: Base/libcef/BugTrace loaded; no TenProxy
第一新节点: KERNEL32!IsBadReadPtr+0x5a crash-report thread
```

No patch performed in this experiment.
