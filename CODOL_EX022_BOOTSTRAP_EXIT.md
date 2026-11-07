# CODOL_EX022_BOOTSTRAP_EXIT.md

## Experiment environment

Running `工具/EXPERIMENT_017_BOOT\codoMP_client_shipRetail.exe` under cdb, original binaries.

## Observed

### VM boundary

`Base+0x1AA13B0` (VM boundary) hit repeatedly.

First boundary entry:
```text
eip=79EA13B0
esp=0019F900
[esp]=77C131A6
```

This is the return address from Base entry/CRT initialization into the VM boundary.

### Thread StartAddress evidence

`NtCreateThreadEx` observed with stack dumps.

- A thread created from `CRYPT32!CryptQueryObject -> Base+0x25E7A64` path; start address near `0x1466EFAC`, not resolved into project/engine code.
- A thread created from `mswsock!WSPConnect -> Base+0x265F4F7` path; start address near `0x0017A654`.

These are not confirmed Engine bootstrap threads. The first observable `NtCreateThreadEx` has start address in stack-allocated/VM-adjacent memory rather than a clear project `StartAddress`.

### TCLS/launcher API trace

Breakpoints on `OpenFileMappingW`, `CreateFileMappingW`, `MapViewOfFile`, `GetCommandLineW`, `GetModuleFileNameW`, `GetEnvironmentVariableW` could not be installed as command-file breakpoints in cdb due to syntax/resolution limits. Existing EX-010 and EX-015 traces show no `TCLS_SHAREDMEMEMORY` / project DLL load before the first crash.

This run does NOT prove a TCLS/launcher context check failure.

### BugTrace / IsBadReadPtr thread attribution

First exception: `KERNEL32!IsBadReadPtr+0x5a` (`75CE015A`).

The stack is not clear, and this exception occurs in a thread separate from the main boundary entries observed. It is not proven to be the same control chain as `Base ordinal_1`.

## Classification

Mapping of requested questions:

1. Base ordinal_1 failure due to TCLS/launcher? No evidence in these runs. `TCLS_CONTEXT_NOT_OBSERVED` is appropriate.
2. Base bootstrap location failure? VM boundary is reached, then thread/API activity occurs; no clean return to plain Base text was proven. `BASE_BOOTSTRAP_FAILURE` is possible but not fully confirmed as the final root.
3. Does VM boundary return to Base .text? No clean return observed before the reported exception/exit.
4. What terminates process? `NtTerminateProcess` not cleanly observed in this run; the process was stopped by debugger after first-chance AV.
5. Final failing thread/EIP/module/RVA/call chain? `KERNEL32!IsBadReadPtr+0x5a`, module KERNEL32, RVA not cleanly resolved; caller chain not recoverable.

Root Cause Classification:
```text
UNRESOLVED
```

## Deliverable log

Logs:
- `工具/logs/exp022.log`
- `工具/logs/exp022_context.log`

Generated combined log:
- `工具/logs/ex022_bootstrap_exit_20260916-...log`
