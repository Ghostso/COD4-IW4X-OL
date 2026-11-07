# CODOL_EXE_ROOT_CAUSE.md

## Q1: Why cannot double-click start the game?

The EXE entry is not a normal game entry. It immediately calls `Base+0x1D6582C` through a custom import slot, and Base bootstrap does not return to EXE before the observed crash. The double-click launch therefore stalls inside Base bootstrap.

## Q2: Expected startup context?

From PE and runtime evidence, the client is designed as a custom Base/VM bootstrap plus later binding layers. Standard IW4 engine startup is not directly visible. The exact external context expected by Base is not fully confirmed; possible launcher/TCLS shared memory context is suspected but not code-confirmed.

## Q3: What is missing?

The Base bootstrap completion. Before it completes, the process does not reach FS/Engine/TenProxy. No game file access occurred before the crash in observed runs.

## Q4: Where is the missing context detected?

The first concrete stop is inside Base bootstrap:
- `Base+0x306A` when the direct locale/object path is reached.
- `KERNEL32!IsBadReadPtr+0x5a` in BugTrace/crash-report thread in some runs.

No launcher-forced check was proven.

## Q5: Minimal launch context?

Not conclusively identified. The clear precondition is that `Base ordinal_1` must complete and return to EXE. Evidence quality is L3-L4 for the entry->Base->VM boundary chain and L2 for custom import/binding layout.

## Root cause grading

CONFIRMED:
- EXE Entry -> Base ordinal_1 -> VM boundary executed.
- Base ordinal_1 did not return before observed crashes.
- No project DLL after Base before first exception in observed runs.

HIGH CONFIDENCE:
- Standard engine code is not directly reachable before Base bootstrap.
- FS/Asset code is not reached before Base bootstrap.

PROBABLE:
- Custom import/binding table is VM-protected and non-standard.

UNKNOWN:
- Whether launcher/TCLS context is required.
- Whether restoring Base bootstrap would lead to TenProxy or straight to engine.

## Result

Double-click failure is not proven to be caused by launcher check. It is caused by the inability to complete the custom Base bootstrap chain before returning to EXE, with later Engine/Game states unreachable.
