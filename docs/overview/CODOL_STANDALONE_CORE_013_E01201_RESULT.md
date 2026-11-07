# CODOL_STANDALONE_CORE_013_E01201_RESULT

## Outcome

```text
FINAL_MARKER = E01201_TARGET_UNRESOLVED
E01201_TARGET = UNRESOLVED
POST_BOUNDARY_EXECUTION = NOT_OBSERVED
MINIMUM_STATE = UNKNOWN
NEXT_TRACK = STANDALONE_ENTRY_UNRESOLVED
```

## Gate

CORE-013 requires `exe_core012_next_experiment.csv` to identify exactly one
explicit EXE RVA before any dynamic observation starts.  The frozen
`E-012-01` row instead specifies the EXE `.text` section as a whole and lists
eight attribution addresses.  CORE-013 STOP-3 therefore applies.

No process was launched.  No candidate was selected or substituted.  No EXE,
DLL, `.tvm0` file, hook, patch, or Tencent component was modified or inspected
internally.

## Evidence

```text
target_candidate = EXE .text section as a whole
attribution_rvas = 0x77F580 / 0x4FD9B0 / 0x4FCEE0 / 0x808650 /
                   0x7E98F0 / 0x6212C0 / 0x00561133 / 0x37FA70
required_unique_target_count = 1
resolved_unique_target_count = 0
```

The CORE-012 candidate remains `CANDIDATE`.  This result does not rewrite it
to `NOT_FOUND`, and it does not claim dynamic reachability.

## Stop Condition

`STOP-3 TARGET_UNRESOLVED`: stop without manufacturing a candidate or running
a widened census.
