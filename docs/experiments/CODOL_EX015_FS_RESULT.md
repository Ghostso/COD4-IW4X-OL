# EX-015 FS/Asset Bootstrap Result

Experiment: EX-015 (one CDB file API trace, no patch)

Observed before `Base+0x306A`:
- `CreateFileA` hit only `C:\Windows\system32\ntdll.dll`
- `ReadFile` hit only system loader/CRC reads
- No `CreateFileW`, `FindFirstFileW`, `FindFirstFileA` game-path hits

Result:
```text
first game-file API: none
filename: n/a
caller: system/runtime only
RVA: n/a
caller+1: n/a
caller+2: n/a
FS candidate: none
Engine bootstrap candidate: none
reachable: NO
LEVEL: L2-L3
next target: confirm whether any game file access happens after Base ordinal 1 returns, or start from higher-level FS conv/stub once VM boundary can be crossed
```

FS bootstrap currently unreachable before Base+0x306A in this startup chain.
