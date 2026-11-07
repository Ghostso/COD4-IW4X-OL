# CODOL_EXE_DEPENDENCY_GRAPH.md

Observed import/dependency:

```text
codoMP_client_shipRetail.exe
  -> codoMP_client_shipRetailBase.dll (ordinal 1 custom binding)
  -> libcef.dll
  -> system DLLs
  -> BugTrace.dll / dbghelp.dll when crash-report path starts
```

Not observed:
- TenProxy.dll
- TenSLX.dll
- TerSafe.dll
- TCJ.dll
- TenRpcs.dll
- GameRpcs.dll

Before the first crash, no project DLL after Base was dynamically loaded in observed runs.

Static custom export/binding:
- TenProxy.dll / Invoke strings exist in EXE data.
- EXE slot CA8150/CA8158 point to .tp3 data placeholders.
- That binding path is not proven to be the actual startup path.
