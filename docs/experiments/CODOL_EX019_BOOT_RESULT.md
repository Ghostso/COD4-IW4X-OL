# EX-019-BOOT Result

## Actual execution

Ran original `工具/EXPERIMENT_017_BOOT\codoMP_client_shipRetail.exe` under cdb with breakpoints:

- `Base+0x1D6582C` (ordinal_1)
- `Base+0x149C` (Base entry)
- `Base+0x1AA13B0` (VM boundary)

## Observed

```text
ordinal_1: ENTER
Base+149C: HIT (jmp Base+0x1AA13B0)
VM boundary: HIT (Base+0x1AA13B0)
last non-VM node: Base+0x1AA13B0 after jmp from Base+0x149C
failure condition: no obvious test/cmp failure branch captured before AV
original normal path: NOT FOUND in this run
patch: NO
patch RVA: n/a
first new node after patch: n/a
EXE continuation: NO
TenProxy: NO
first exception: KERNEL32!IsBadReadPtr+0x5a
```

## Notes

- BugTrace/dbghelp loaded after repeated VM boundary hits, then first exception in `KERNEL32!IsBadReadPtr+0x5a`.
- No failure->normal branch was confirmed before the exception.
- No patch was made.

## Result

```text
NO NEW NODE
```
