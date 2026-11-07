# EX-017-FAST Object Corruption Writer Result

Experiment: EX-017-FAST (no patch)

Goal: locate the first writer that changes the valid object into `ECX=3` before `Base+0x306A`.

Observed context:
- `Base+0x306A` first valid hit: `ECX=0x128A4CE8`, `[ECX+18]=0x0F`
- Later hit: `ECX=3`, AV at `0x1B`

Tooling limitation:
- Hardware write breakpoint on `object+4` / `object+18` requires dynamic address from the first valid hit.
- CDB script cannot safely set a new `ba` on `poi(@ecx+4)` in the current command-file path; object address is heap/process dependent, so fixed addresses are invalid.

Result:
```text
writer = UNKNOWN
first valid object observed: yes (EX-016)
destination = object+4 / object+18 candidates
old value = unknown (object valid at +0x18 first: 0x0F)
new value = 3
module/RVA = unknown, before Base+0x306A
```

No patch, no FS/TenProxy/locale analysis.
