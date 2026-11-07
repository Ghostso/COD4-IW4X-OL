# CODOL_EXE_STARTUP_STATE_MACHINE.md

| State | Meaning | Evidence | Current actual |
|---|---|---|---|
| S0 | Process Created | cdb process start | reached |
| S1 | PE Loaded / custom import | Import size=0, custom resolver implied | reached (static) |
| S2 | TLS | callback count 0 | not active |
| S3 | EXE Entry | `0xE5DC690` executes call to Base ordinal_1 | reached |
| S4 | CRT/runtime | not reached as plain CRT; Base handles runtime | unknown |
| S5 | Base | `Base+0x1D6582C` entered | reached |
| S6 | VM boundary | `Base+0x1AA13B0` hit, Base entry jmp | reached |
| S7 | Runtime/TCLS/IPC | not observed | not reached |
| S8 | Dynamic binding | not observed | not reached |
| S9 | TenProxy | not loaded | not reached |
| S10 | Engine | not found | not reached |
| S11 | FS/Asset | no game file access before crash | not reached |
| S12 | Renderer | no renderer code reached | not reached |
| S13 | Game/Main loop | no client/game code reached | not reached |

Known stop points:
- `Base+0x306A` (historical main crash)
- `KERNEL32!IsBadReadPtr+0x5a` in BugTrace/crash-report thread

Both are before returning to EXE, so all later states are not reached.
