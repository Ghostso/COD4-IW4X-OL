# EX-010 Runtime DLL Loader Boundary

Experiment: EX-010 (one short CDB LdrLoadDll trace, no patch)

Observed dynamic loads before crash:
- Only system/runtime DLLs: `api-ms-win-*`, `kernel32`, `ADVAPI32`, `CRYPT32`, `GDI32`, `IPHLPAPI`, `NETAPI32`, `OLEAUT32`, `PSAPI`, `SETUPAPI`, `SHELL32`, `SHLWAPI`, `USER32`, `VERSION`, `WINMM`, `WINTRUST`, `WLDAP32`, `WS2_32`, `WSOCK32`, `gdiplus`, `ntdll`, `ole32`.
- No project DLL dynamic load before `Base+0x306A` AV.
- `codoMP_client_shipRetailBase.dll` and `libcef.dll` are already loaded via static imports, not by a dynamic project-DLL loader in this window.

Last actual execution node:
```text
Base+0x306A  cmp [ecx+18h],10h ; ecx=3, AV at 0x1B
```

Direct caller:
```text
Base+0x2F14 -> Base+0x306A
Base+0x2ED2 -> Base+0x2F14
.tvm0 boundary Base+0x267AC6D -> Base+0x2ED2
```

Verdict:
```text
project DLL loader = NOT FOUND before crash
first project DLL = N/A (no dynamic project load observed)
Runtime Bootstrap Dispatcher = behind .tvm0 boundary, not reached
TenProxy = NOT LOADED
Invoke = NOT HIT
```

No single-point experiment was performed.
