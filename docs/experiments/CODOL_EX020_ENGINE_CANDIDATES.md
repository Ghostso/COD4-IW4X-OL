# EX-020-ENGINE-ENTRY Result

## Method

Scanned EXE for code refs to `Initializing...`, `codoMP_client_ship.exe`, `main\%s`, `Renderer`, `RenderPipelineManagement`, `TextureManager`, then tried to locate prologue and caller.

## Findings

`Initializing...` string RVA `0x009DBF50`, code ref at `EXE RVA 0x1321A9`, near prologue `0x131F57`. Linear disassembly around it is heavily obfuscated/not clean; the apparent prologue continues as invalid/VM-like instructions. No reliable plain text Engine entry.

`main\%s` ref at `0x239BA7`, `codoMP_client_ship.exe` ref at `0x239BA7` nearby is same region, but also not a clean function.

Renderer references:
- `Renderer` string ref `0x7036DC`
- `RenderPipelineManagement` string ref `0x70370C`
- `TextureManager` string ref `0x703784`

These land in a pointer/resource table area (`0xA176DC` etc), not a plain executable function. They can be used as data anchors, not Engine Entry.

## Candidate table

| Candidate | Type | RVA | Evidence |
|---|---|---:|---|
| 1 | Engine-ish string ref | 0x1321A9 | ref to `Initializing...`; no clean caller / function |
| 2 | FS-ish string ref | 0x239B7D | ref to `main\%s`; no clean function |
| 3 | Renderer table anchor | 0x7036DC / 0x70370C / 0x703784 | refs to Renderer names in data table |
| 4 | Network | not found as clean code | 2241..2301 strings are data anchors only |
| 5 | Game | not found as clean code | only asset/config evidence |
| 6 | Main Loop | not found | not reached |

## Most important candidate

```text
RVA: 0x1321A9 (Initializing ref)
Type: Engine/Startup string ref
caller: UNKNOWN; prologue candidate 0x131F57 is not clean
caller's caller: UNKNOWN
```

## Result

```text
Engine candidates:
1. 0x1321A9 Initializing ref (unreliable)
2. 0x239B7D main\\%s ref (unreliable)
3. Renderer table anchors 0x7036DC/0x70370C/0x703784 (data table only)

FS candidate:
RVA: no reliable code entry
evidence: main\\%s string ref only

Renderer candidate:
RVA: 0x7036DC/0x70370C/0x703784
evidence: string refs in pointer table, not executable function

Network candidate:
RVA: no reliable code entry
evidence: port strings only

Game candidate:
RVA: no reliable code entry
evidence: config/assets only

最重要候选:
RVA: 0x1321A9
类型: Engine/Startup string ref

caller:
RVA: UNKNOWN

caller 的 caller:
RVA: UNKNOWN

动态命中:
NO

当前执行链:
EXE Entry -> Base ordinal_1 -> VM boundary -> no Engine/FS/Renderer reached

正常 Engine Entry:
NOT FOUND

当前断点:
Base VM boundary; no clean plain Engine entry found

是否 patch:
NO

第一新节点:
NO NEW NODE

结论:
NO NEW ENGINE CANDIDATE
```

No patch performed.
