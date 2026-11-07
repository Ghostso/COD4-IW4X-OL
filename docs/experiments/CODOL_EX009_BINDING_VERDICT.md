# EX-009 TenProxy Binding Reachability Verdict

Experiment: EX-009 (static reachability audit, no patch)

Findings:
- `EXE+0x184F5E` is inside executable `.tp3` (RVA `0x1000..0x593000`), but the bytes are VM-encrypted/obfuscated; linear disassembly is not clean.
- Function prologue candidate: `EXE+0x184C7D`. No direct `E8` caller found, no pointer-table reference to `0x184C7D` or `0x184F5E` in the file.
- `CA8150` static content: `0x00A13848` (`RVA 0xA13848`).
- `CA8158` static content: `0x00A1386A` (`RVA 0xA1386A`).
- Both target RVAs point into `.tp3` memory that is all zeros on disk.
- No static writer instruction for `CA8150` or `CA8158` was found (`mov [slot], reg` patterns: 0 hits).
- The slot targets must be filled by a runtime VM/resolver, not by visible `.text` code.

Verdict:
```text
184F5E = VM-internal / alternate binding path
current startup path = NOT PROVEN
CA8150/CA8158 runtime writer = NOT FOUND in static code
resolver = EXISTS as requirement, NOT OBSERVED at runtime
TenProxy = NOT LOADED
```

Recommendation:
Do not keep treating `184F5E -> CA8150/CA8158` as the primary startup TenProxy path. Look for the actual runtime bootstrap dispatcher that initializes these slots, or for another TenProxy load path.
