# EX-016-FAST Base ordinal_1 Return Boundary

Experiment: EX-016-FAST (one CDB trace, no patch)

Probes:
- `Base+0x1D6582C` ordinal_1 entry
- EXE `0xE5DC696` return breakpoints (intended return-after-ordinal paths)
- `Base+0x306A` crash/state

Observed:
- No `RET_TO_EXE` breakpoint hit; Base ordinal_1 did not return to EXE before the traced endpoint.
- `Base+0x306A` was hit with a valid object first: `ecx=0x128A4CE8`, `[ecx+18h]=0x0F`.
- Later the known bad state occurred (`ecx=3`, AV at `0x1B`).

Result:
```text
ordinal_1 RET: NO
RET→EXE EIP: none observed
last non-tvm0 node: Base+0x306A (with valid ecx first, then ecx=3)
caller: Base+0x2F14 / Base+0x2ED2 path
next execution: no new stage
LEVEL: L2-L3
```

Key evidence:
`Base+0x306A` is not a VM-internal-only crash; it is reached from non-`.tvm0` Base code and can first see valid objects before the object is later corrupted.
