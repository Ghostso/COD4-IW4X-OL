# ICH-044 — Engine External Trigger / Initialization Event 定位

## Run mode: B

### Timeline summary

```text
Process lifetime   = 30.1s
Modules            = 130
Threads            = 55
Gate crossed       = NO
```

### Post-gate activity

```text
New threads after gate   = 0
New modules after gate   = 0
Dispatch table changes   = 0
```

### Decision

BASELINE_FAILED (gate not crossed)
ICH044_STATUS = INSTRUMENTATION_BLOCKED

### Anchor correlation (static, no runtime address recovery)

```text
Anchor A RVA 0x18AE194 = 0x00E83B00 (96-entry dispatch table base)
Anchor B RVA 0x15EC784 = 0x00E83C00 (dispatch base + 0x100)
RVA distance A - B = 0x2C1A10
Both in Base.dll .tls section (VM-generated data, not reloc target)
Runtime correlation: Base.dll is loaded in process, but the VM-resolved
  candidate object address cannot be recovered without debugger or scan.
```
