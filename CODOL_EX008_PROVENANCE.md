# EX-008 TenProxy Push Result

Experiment: EX-008 (dynamic observation only, no binary patch)

Observed:
- `EXE+0x184F5E`: NOT HIT
- Binding consumer: NOT OBSERVED
- `LdrLoadDll`: observed many times, only system/runtime DLLs
- `LoadLibraryA/W`, `GetProcAddress` breakpoints: could not be installed with cdb command syntax in this run
- `ModLoad: TenProxy.dll`: NOT PRESENT
- `TenProxy!Invoke`: NOT HIT
- New bootstrap execution node: NONE

Current blocker:
```text
Base CRT/locale initialization prevents reaching EXE binding consumer.

Known binding:
EXE+0x184F5E
-> CA8158
-> CA8150
-> TenProxy.dll / Invoke

Runtime execution:
NOT OBSERVED
```

No patch, no NOP, no exception swallow.
