# EX-007 Hardware Write Probe Result

Experiment: EX-007 (provenance only, no binary patch)

Probe:
```text
ba w4 0x141CE024
```

Result:
- The fixed write breakpoint did not fire in a fresh run.
- The AV at `Base+0x306A` with `ecx=3` reproduced, but the heap object address was not stable across runs, so `0x141CE024` from EX-006 was not valid for this process instance.

Conclusion:
```text
writer UNKNOWN
field = object+4
value = 3
```

No patch, no NOP, no TenProxy module observed.
