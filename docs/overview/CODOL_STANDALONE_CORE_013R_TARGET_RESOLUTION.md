# CODOL_STANDALONE_CORE_013R_TARGET_RESOLUTION

## Outcome

```text
E01201_TARGET = UNRESOLVED
TARGET_STATUS = NO_UNIQUE_STATIC_TARGET
DYNAMIC_TEST_READY = NO
NEXT_TRACK = STANDALONE_ENTRY_UNRESOLVED
```

This is static target resolution only. No process was launched, no debugger
was attached, no dynamic breakpoint was set, and no new EXE scan was run.

## Attribution Matrix

| RVA | Section | File-backed | Alignment | Exclusion |
|---|---|---|---|---|
| 0x0077F580 | .tp3 | NO | ALIGNMENT_UNCONFIRMED | NOT_FILE_BACKED_OR_VIRTUAL_ONLY |
| 0x004FD9B0 | .tp3 | YES | ALIGNED | HISTORICAL_CHAIN_MEMBER_ONLY |
| 0x004FCEE0 | .tp3 | YES | ALIGNMENT_UNCONFIRMED | INSTRUCTION_ALIGNMENT_NOT_CONFIRMED |
| 0x00808650 | .tp3 | NO | ALIGNMENT_UNCONFIRMED | NOT_FILE_BACKED_OR_VIRTUAL_ONLY |
| 0x007E98F0 | .tp3 | NO | ALIGNMENT_UNCONFIRMED | NOT_FILE_BACKED_OR_VIRTUAL_ONLY |
| 0x006212C0 | .tp3 | NO | ALIGNMENT_UNCONFIRMED | NOT_FILE_BACKED_OR_VIRTUAL_ONLY |
| 0x00561133 | UNKNOWN | NO | ALIGNMENT_INVALID | NOT_FILE_BACKED_OR_VIRTUAL_ONLY |
| 0x0037FA70 | UNKNOWN | NO | ALIGNED | NOT_FILE_BACKED_OR_VIRTUAL_ONLY |

The CORE-012 attribution set contains the seven historical-chain RVAs
`0x77F580`, `0x4FD9B0`, `0x4FCEE0`, `0x808650`, `0x7E98F0`, `0x6212C0`,
plus `0x00561133` (argv provider call site) and `0x37FA70` (fatal error
display). None satisfies the CORE-013R nine-part uniqueness rule.

## CORE-011 Separation

CORE-011 remains:

```text
EXE_IMAGE_EXECUTION_AFTER_BOUNDARY = NOT_OBSERVED
ENVIRONMENT_DEPENDENT = NO
```

Its `NOT_OBSERVED` result is retained as a dynamic observation only. It is
not used to claim that any attribution RVA is unreachable.

## Conclusion

```text
STANDALONE_ENTRY_TARGET = UNKNOWN
E01201_TARGET = UNRESOLVED
TARGET_STATUS = NO_UNIQUE_STATIC_TARGET
DYNAMIC_TEST_READY = NO
```

Stop here. Do not run E-012-01 and do not expand the search space.
