# EX-037 IIPS Runtime Boundary and `0x8189FEC` Responsibility

## Final Classification

```text
IIPS_MODULE_PRESENT_USAGE_UNCONFIRMED
IIPS_FAILURE_NODE_CONFIRMED
IIPS_FAILURE_SOURCE_UNRESOLVED
NO_NEW_EXECUTION_NODE
NO_IISHostApp_OBSERVED
NO_IFS2_MODULE_OBSERVED
NO_TCLS_MAPPING_OBSERVED
```

`iips.dll` is confirmed loaded in the game process during an independent
`-q` run. No evidence was obtained that `GetResourceManagerII`,
`IIPSHostApp.exe`, or `ifs2.dll` executed. `0x8189FEC` remains a
packed/VM-produced status and cannot yet be attributed to a specific IIPS
layer.

## Runtime Module Evidence

Observer run with:

```text
independent copy   : 工具/EX035_DIR
command line       : codoMP_client_shipRetail.exe -q
current directory  : 工具/EX035_DIR
observer type      : non-invasive Toolhelp/module/window polling
```

Captured module list included:

```text
iips.dll   : present in game process module list
```

Not observed in the game process module list:

```text
ifs2.dll
IIPSHostApp.exe
IIPSCheck.dll
IIPSVFS.dll
IIPSHost.dll
Download.dll
```

No separate process named `IIPSHostApp` was found after the `-q` run.
`HostPid` had a stale PID and no matching live process was observed.

## Windows Observed

```text
#32770  fatal dialog "致命错误" (IIPS init error)
iipsinit Environment List Box window
IME windows
```

The `iipsinit` window is present. This is consistent with IIPS resource
manager initialization starting. It does not prove HostApp or IFS2 load.

## `GetResourceManagerII` Status

`iips.dll` exports `GetResourceManagerII` and `ReleaseResourceManagerII`.

```text
GetResourceManagerII was NOT confirmed executed.
ReleaseResourceManagerII was NOT confirmed executed.
Return value NOT observed.
```

The export disassembly for `GetResourceManagerII` shows it allocates a
resource manager object and may fail by returning `NULL`, but an actual
runtime call was not captured.

## `ifs2.dll` Status

`COD OL/IIPS/IFS2.dll` exists on disk and exports IFS-related functions,
but no runtime load was observed during the `-q` run.

## `IIPSHostApp.exe` Status

`COD OL/IIPS/IIPSHostApp.exe` exists on disk.

```text
Process creation: NOT observed
Parent PID: N/A
Command line: N/A
Exit: N/A
```

No fake/constructed HostApp protocol was used. This is observation only.

## IPC Status

No IIPS shared memory, named pipe, or HostApp file activity was correlated
to the failure window. The observer did not hook APIs, so absence of hook
records means not observed, not proof of absence.

## `0x8189FEC`

No exact plaintext constant was found in:

```text
codoMP_client_shipRetail.exe
codoMP_client_shipRetailBase.dll
iips.dll
```

Classification:

```text
8189FEC_PACKED_OR_VM_GENERATED
```

This is a working classification, not final semantics.

## Boundary Decision

Current evidence supports:

```text
CODOL -> iips.dll loaded -> iipsinit window -> WIN_IIPS_INIT_ERROR 0x8189FEC
```

It does not support:

```text
CODOL -> iips.dll -> GetResourceManagerII failure
CODOL -> iips.dll -> IIPSHostApp failure
CODOL -> iips.dll -> ifs2.dll failure
```

Therefore:

```text
CASE D
IIPS_MODULE_PRESENT_USAGE_UNCONFIRMED
```

## Answers to Final Questions

1. `iips.dll` participated in `-q` run: loaded into game process, yes.
2. `GetResourceManagerII` executed: not confirmed.
3. Return value: not observed.
4. `ifs2.dll` loaded/executed: not observed.
5. `IIPSHostApp.exe` created: not observed.
6. HostApp PID/parent: N/A.
7. Real IIPS IPC: not observed.
8. IIPS failure layer: unresolved.
9. `0x8189FEC` linked to return value: no.
10. CODOL-side failure after IIPS success: not proven.
11. Globals new runtime consumers: none observed.
12. New stable L3/L4 node: no new execution node beyond the confirmed `iips.dll` module load and IIPS init dialog.
