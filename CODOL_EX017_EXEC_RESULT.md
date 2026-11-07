# EX-017-EXEC Actual Execution Result

## What was actually executed

Created `工具/EXPERIMENT_017_BOOT` with original binaries.
Hash evidence:
- EXE `36997674b18f2896de5e9d755686f6922af10708f355175714058d0a0172b537`
- Base `ef75220de1d6973f34c7069f5bf211b11bd61520c6c0de1882f7359fa5bc6a20`
- TenProxy `a5ee7ede762c473f58a87b214213097f6dda8950ac537b0a959389aef31348cb`

Run 1: original EXE under cdb.
Observed:
- EXE, Base, libcef loaded.
- First chance exception at `KERNEL32!IsBadReadPtr+0x5a` (`75CE015A`), thread had crash-report/BugTrace context.
- `codoMP_client_shipRetailBase.dll` loaded.
- No TenProxy module logged before the caught exception.

Run 2: EXE-only skip experiment.
Created `工具/EXPERIMENT_017_BOOT_SKIP`.
Single EXE Entry patch:
- RVA `0xE5DC690`, file offset `0x776690`
- original `ff 15 65 c6 9d 0e` -> `b8 00 00 00 00 c3` (`mov eax,0; ret`)
- modified EXE SHA256 `7b31168d42a5a6ba11750d404971ee52f9fd1cab93c56a8a85da94ae76c41342`

Observed:
- Process started, loaded Base DLL and libcef.
- Then exited via `ntdll!NtTerminateProcess` (`77C134AC`) without reaching `TenProxy.dll` or Engine startup.
- No game-file access / no Renderer / no Game bootstrap observed in this skipped-entry run.

## Result

```text
PID: recorded per cdb session (Run1/Run2 process IDs in cdb logs)
Entry EIP: 0x0E9DC690
Base ordinal_1 executed: YES in original run
Skip experiment executed: YES (EXE-only patch)
Skipped first EIP / result: NtTerminateProcess exit, no new engine node
New DLL loaded: Base DLL and libcef loaded in both runs; TenProxy NOT LOADED
First exception (original): KERNEL32!IsBadReadPtr+0x5a in BugTrace/crash-report thread
Exit: exited/terminated, no TENPROXY, no Invoke
```

## Next

Skipping Base ordinal_1 via EXE entry alone does not start the original Engine; it terminates. Original run first hits a BugTrace/IsBadReadPtr AV before returning to the main Base+0x306A path observed historically. Next step requires handling the pre-return Base/bootstrap sequence, not EXE-entry bypass.
