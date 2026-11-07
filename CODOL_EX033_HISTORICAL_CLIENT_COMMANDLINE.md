# EX-033 Historical Client Command Line and `-q/-qa` Source

## Final Classification

```text
HISTORICAL_CLIENT_COMMANDLINE_UNRESOLVED
HISTORICAL_CLIENT_Q_QA_ABSENT
CLIENT_DIRECT_CREATEPROCESS_PARTIAL
PREDICATE_HISTORICAL_RELATION_UNRESOLVED
OBSERVER_DIVERGENCE=NO
NO_NEW_NODE=NO
```

No historical log or dump was found in the workspace that contains the
full real command line used by `Client.exe -> codoMP_client_shipRetail.exe`.
Tenproxy logs exist from 2020 and show successful TCLS shared-memory
initialization, but they do not record the game process command line. The
`-q` / `-qa` / `-src=tgp` source remains unresolved from historical
evidence.

## Search Summary

Searched:

```text
COD OL/docs
COD OL/TenproxyLog
COD OL/Logs
COD OL/TCLS
COD OL/WeGameLauncher
WeGame/log
工具/
日志/
_dyn_stage1/
```

No command line of the form:

```text
Client.exe ... -> codoMP_client_shipRetail.exe ... -q / -qa
```

was found in logs, dumps, or existing experiment output.

## Existing Historical Evidence

Tenproxy logs from 2020 prove a successful historical game session:

```text
[T:InitlizeLog] tenproxy Path:d:\wegameapps\使命召唤ol
GetCurrentProcessId = 12768
OpenFileMapping TCLS_SHAREDMEMEMORY+12768 Success!
MapViewOfFile Success!
GetGameSignatrue Success!
GetJumpSignatrue Success!
```

These logs show TCLS shared-memory/tenproxy flow, but they never record
the parent process, game command line, or `lpCommandLine` used to create
the game process.

## Static String Evidence

The extracted context scan contains a UTF-16 cluster around the TCLS
shared-memory strings:

```text
-api
-q
-q:
%allusersprofile%\application data\tencent\tas\TASData.dat
TCLS_SHAREDMEMEMORY
id=
key=
ID=
GetCommandLineW
```

This is the strongest static hint that the historical Client-side flow
uses command-line style keys `-q`, `-q:`, `id=`, `key=`, and `ID=`. The
project protocol note also states:

```text
写入方是 TCLS/ClientBase.dll（12.7 MB），凭据经命令行 -q: / uid= / key= / ID= 传入。
```

However:

```text
string presence != command-line flow confirmation
```

No disassembly yet proves that this string cluster reaches the
`lpCommandLine` of a `CreateProcessW` call that creates the CODOL game
process.

## Client Executable Analysis

`COD OL/TCLS/Client.exe` statically imports:

```text
KERNEL32.dll
  CreateProcessW
  GetCommandLineA
  CreateFileW

SHELL32.dll
  ShellExecuteExW
```

It does not import `GetCommandLineW`, `CommandLineToArgvW`, or contain
the literal `-q` / `-qa` strings according to the existing scan. This
makes it likely that `ClientBase.dll` or another component builds any
login arguments, not `Client.exe` itself.

`ClientBase.dll` / `TCLS\ClientBase.dll` is a much larger component and is
the better static target for `-q:` / `id=` / `key=` construction. That
proof was not completed in this pass.

## Process Creation Path

The existing per-module scan found only:

```text
Client.exe
  CreateProcessW import at 0x42228E
```

The surrounding disassembly contains many embedded option-like strings,
but no complete `lpApplicationName` / `lpCommandLine` flow to
`codoMP_client_shipRetail.exe` was reconstructed.

## Real-Time Observation Decision

The experiment allowed one non-invasive real-time Client launch if
historical evidence is insufficient. In this workspace, `Client.exe` is
present, but the TCLS environment is not provisioned and any GUI login
would require live TCLS components. Given the existing signed/anti-tamper
environment and the observer-divergence constraints, no live
`Client.exe` observer was started this turn.

## Answers to Final Questions

1. Historical real `Client -> Game` command line obtained: no.
2. Does `Client.exe` directly create the game process: unproven, but it imports `CreateProcessW`.
3. Intermediate helper if not direct: unresolved.
4. Game parent PID equals Client: unresolved.
5. Game full command line: unresolved.
6. Contains `-q`: unresolved from historical logs.
7. Contains `-qa`: unresolved from historical logs.
8. Contains `-src=tgp`: unresolved from historical logs.
9. Are `-q/-qa` dynamically injected by Client: unresolved.
10. Does Client contain corresponding parameter construction: unresolved; `Client.exe` itself has no literal hits, `ClientBase.dll` not yet proven.
11. `-src=tgp` handler/semantics: unresolved.
12. Can historical Client launch satisfy EXE+0x37F580: unresolved from historical command line evidence.
13. Other unresolved conditions: yes, the actual historical launch path.

## Summary

The 2020 Tenproxy logs confirm that the historical game session reached
TCLS shared-memory flow. Static strings show `-q`, `-q:`, `id=`, `key=`,
and `ID=` in the Client-side context cluster, but no complete command-line
construction chain was proven. EX-033 therefore closes with:

```text
HISTORICAL_CLIENT_COMMANDLINE_UNRESOLVED
HISTORICAL_CLIENT_Q_QA_ABSENT
CLIENT_DIRECT_CREATEPROCESS_PARTIAL
PREDICATE_HISTORICAL_RELATION_UNRESOLVED
```

The next useful step is static analysis of `ClientBase.dll` for the exact
`-q:` / `uid=` / `key=` / `ID=` command line builder and its target
`CreateProcessW` / `ShellExecuteExW` call site.
