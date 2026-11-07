# ICH-029 - Compat Surface Summary

## Object Size Validation

```text
RESOLVED: 0x410 is sufficient (not 0x480)
Maximum field offset across all 48 vtable methods: 0x3BC
Accesses beyond 0x410: 0
Accesses beyond 0x480: 0
0x480 allocation is excessive padding; 0x410 is correct for GetResourceManagerII
```

## Compatibility Layer Summary

```text
IMPLEMENTATION: DLL proxy (replace iips.dll with local implementation)
OBJECT SIZE: 0x410 bytes
VTABLE ENTRIES: 48 (minimum 3 implemented, 45 stubs)
NESTED OBJECT: at +0x70, 0x40 bytes, 4-entry vtable
KEY METHOD: vtable[2] CheckState → return 1 (TRUE)
KEY METHOD: vtable[3] Process → return 0 (success)
KEY METHOD: vtable[0] Destructor → safe cleanup
KEY FIELD: +0x3BC flag → set to 0
```

## Implementation Status

```text
DESIGN = COMPLETE
CODE = PENDING (next step: write proxy DLL)
TESTING = PENDING (EX-029-A: ABI-only, then EX-029-B: State-enabled)

The design is ready for implementation. The proxy DLL approach
avoids modifying the original EXE or Base.dll. The local
ResourceManager object satisfies the confirmed ABI contract
(48-entry vtable, 0x410 bytes, nested object at +0x70).
```
