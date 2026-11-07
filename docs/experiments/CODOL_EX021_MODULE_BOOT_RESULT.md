# EX-021-MODULE-BOOT Result

## Actual execution

Ran `工具/EXPERIMENT_017_BOOT\codoMP_client_shipRetail.exe` under cdb, broke on `ntdll!NtCreateThreadEx`.

## PE module structure

- EXE: no normal export/TLS directory found in this PE scan; entry `Base+0xE5DC690`.
- Base.dll: no normal export/TLS directory found; entry `0x149C`.
- TenProxy/TenSLX/TerSafe/libcef/TCJ/TenRpcs/GameRpcs/PolicyProbe/VSDDrvDll: PE entry recorded, no normal export/TLS directory reported by `pefile`.

## Module load order (first visible event on this run)

```text
1. codoMP_client_shipRetail.exe
2. ntdll.dll
3. KERNEL32.DLL
4. KERNELBASE.dll
5. codoMP_client_shipRetailBase.dll
6. libcef.dll
7. system DLLs (PSAPI, VERSION, msvcrt, shell32, winhttp, etc.)
8. BugTrace.dll / dbghelp.dll after threads started
```

No TenProxy or other CODOL project DLL appeared before the first exception in this run.

## TLS

No `IMAGE_DIRECTORY_ENTRY_TLS` callback list was recovered in this scan for EXE/Base/project DLLs. Reported absence is based on this PE parse, not a claim that no hidden TLS exists.

## CreateThread / NtCreateThreadEx

`NtCreateThreadEx` hit before exception. Stack-dump values suggested StartAddress pointers around:
- `0x0017C800` (first)
- `0x0017DF40` (second)
- `0x1464EFAC` (third)
- `0x0017A654` (fourth, after BugTrace load)

These are not confirmed project/engine thread entries; no caller module was resolved before first AV.

## First non-system thread

Not confidently attributable. The first AV at `KERNEL32!IsBadReadPtr+0x5a` in crash-report/BugTrace context prevented module attribution.

## Conclusion

```text
Module load order: EXE -> Base -> libcef -> system -> BugTrace/dbghelp
EXE TLS: none recovered
Base TLS: none recovered
CODOL DLL DllMain: not mapped to plain symbols
Exports: no meaningful export names recovered for CODOL binaries
CreateThread: NtCreateThreadEx hits, but no confirmed engine start address
First CODOL DLL loaded after Base: none visible before crash
Engine candidate: NOT FOUND
Evidence: no module-level bootstrap candidate
Conclusion: NO MODULE BOOTSTRAP CANDIDATE
```
