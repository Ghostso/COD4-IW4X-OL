# EX-005 ECX=3 Provenance

Experiment: EX-005 (provenance only, no binary patch)

Dynamic context at `Base+0x306A`:
```text
eip = codoMP_client_shipRetailBase+0x306A
ecx = 3
esp = 0x0017E16C
AV  = 0x0000001B
[esp] = codoMP_client_shipRetailBase+0x2F19
```

Direct call chain:
```text
Base+0x306A  cmp [ecx+18h], 10h
  <- call from Base+0x2F14
  <- mov ecx, esi at Base+0x2F0B
  <- function entry Base+0x2ED2
```

Provenance:
```text
Base+0x2ED2 entry (last capture before AV):
  ecx = 0x141E5020
  [esp] = 0x7AA7AC6D

0x7AA7AC6D = Base + 0x267AC6D
  -> inside Base .tvm0 (0x19DD000..0x393A600)

At Base+0x2F0D:
  esi = 3
  -> ecx = esi = 3
  -> Base+0x306A
```

Conclusion:
- `ecx=3` is consumed as an object/`this` pointer by `Base+0x306A`.
- It is produced inside the `Base+0x2ED2` execution path after entry from `.tvm0`-resident caller code.
- Visible `.text` path does not show a clean `mov esi,3`; remaining provenance crosses the `.tvm0` boundary.
- Not classified as locale category/index without further evidence.

Evidence level:
L3 (actual runtime execution) / L4 partial (executed control-flow chain up to `.tvm0` boundary).
