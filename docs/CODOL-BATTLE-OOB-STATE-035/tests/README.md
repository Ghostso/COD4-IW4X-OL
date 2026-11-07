# tests/ -- reserved

The offline test suite for this task is implemented as a compiled self-test
harness and lives next to the code it exercises:

* source   : `..\src\SelfTest.cs`
* build    : `..\src\build.ps1`  -> `..\build\bin\OobStateMachine.exe`
* run      : `..\src\run_selftest.ps1`
* results  : `..\build\selftest.output.txt`, `..\build\selftest.exitcode.txt`

Run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "..\src\build.ps1"
& "..\build\bin\OobStateMachine.exe"
```

Actual result: pass=84 fail=0, exit code 0 (see `..\TV01_TV06_TEST_RESULTS.md`).
This directory is intentionally reserved and holds no additional test files.
