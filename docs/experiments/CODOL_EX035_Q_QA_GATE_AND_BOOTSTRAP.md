# EX-035 `-q/-qa` Gate and Post-Gate Bootstrap Semantics

## Final Classification

```text
GATE_BYPASS_CONFIRMED
POST_GATE_BOOTSTRAP_NODE_CONFIRMED
POST_GATE_FATAL_NODE_CONFIRMED
MODE_SEMANTICS_UNRESOLVED
NO_TCLS_MAPPING_OBSERVED
OBSERVER_DIVERGENCE=NO
```

Running from an independent copy with command-line arguments confirms:

```text
-q  -> WIN_NO_TCLS gate bypass, then IIPS init error dialog
-qa -> WIN_NO_TCLS gate bypass, then IIPS init error dialog
-src=tgp -> still WIN_NO_TCLS gate
```

`-q` and `-qa` are gate-only tokens with respect to `WIN_NO_TCLS`; they
do not complete bootstrap. After the gate, a new fatal node appears:

```text
WIN_IIPS_INIT_ERROR
message = 初始化IIPS错误：8189fec
window class = #32770
title       = 致命错误
```

An `iipsinit` window also appears in `-q` / `-qa` runs:

```text
class = iipsinit
text  = Environment List Box
```

This indicates IIPS initialization began after the gate.

## Method

An independent copy was created at:

```text
工具/EX035_DIR
```

The copy was populated from the full `COD OL` tree. Original binary hash
before any edits:

```text
codoMP_client_shipRetail.exe
36997674B18F2896DE5E9D755686F6922AF10708F355175714058D0A0172B537
```

Each launch used:

```text
CreateProcessW(lpApplicationName=EX035_DIR\codoMP_client_shipRetail.exe,
               lpCommandLine=<EXE> [args],
               CurrentDirectory=EX035_DIR)
```

No original binary, original DLL, WeGame, TCLS, or Client.exe was started.

## Parameter Matrix

### A: no args

```text
WIN_NO_TCLS fatal    : yes
IIPS init error      : no
iipsinit window      : no
[0x849413B]          : 0
[0x849B500]          : 0
[0x849B501]          : 0
project modules      : TenProxy/TenRpcs/GameRpcs/tcj/GDPLoader/policyprobe loaded
```

Matches EX-026 ground truth.

### B: `-q`

```text
WIN_NO_TCLS fatal    : no
IIPS init error      : yes, 8189fec
iipsinit window      : yes
[0x849413B]          : 1
[0x849B500]          : 0
[0x849B501]          : 0
```

### C: `-qa`

```text
WIN_NO_TCLS fatal    : no
IIPS init error      : yes, 8189fec
iipsinit window      : yes
[0x849413B]          : 0
[0x849B500]          : 1
[0x849B501]          : 0
```

### D: `-src=tgp`

```text
WIN_NO_TCLS fatal    : yes
IIPS init error      : no
iipsinit window      : no
[0x849413B]          : 0
[0x849B500]          : 0
[0x849B501]          : 1
```

### E: `-q -src=tgp`

```text
WIN_NO_TCLS fatal    : no
IIPS init error      : yes, 8189fec
iipsinit window      : yes
[0x849413B]          : 1
[0x849B500]          : 0
[0x849B501]          : 1
```

### F: `-qa -src=tgp`

```text
WIN_NO_TCLS fatal    : no
IIPS init error      : yes, 8189fec
iipsinit window      : yes
[0x849413B]          : 0
[0x849B500]          : 1
[0x849B501]          : 1
```

## Gate Semantics

```text
-q
   -> suppresses WIN_NO_TCLS
   -> sets [0x849413B]

-qa
   -> suppresses WIN_NO_TCLS
   -> sets [0x849B500]

-src=tgp
   -> sets [0x849B501]
   -> does not suppress WIN_NO_TCLS
```

`-q` and `-qa` are not sufficient for complete bootstrap. Both then
proceed to IIPS initialization and fail.

## Post-Gate Node

New stable L3 node after gate bypass:

```text
IIPS initializer
  -> iipsinit window
  -> WIN_IIPS_INIT_ERROR
  -> code 0x8189FEC
  -> #32770 致命错误
```

Localization key:

```text
WIN_IIPS_INIT_ERROR
"初始化IIPS错误：%x。"
```

This is a separate fatal node from `WIN_NO_TCLS`.

## State Variable Consumers

Observed state during fatal dialog:

```text
0x849413B = 1 for -q / -q -src=tgp
0x849B500 = 1 for -qa / -qa -src=tgp
0x849B501 = 1 for any -src=tgp
```

Full consumer graphs for these globals are not yet reconstructed.

## Answers to Final Questions

1. `-q` removes `WIN_NO_TCLS`: yes.
2. `-qa` removes `WIN_NO_TCLS`: yes.
3. `-src=tgp` still does not remove it: yes.
4. `-q` and `-qa` enter different control flow: not from these observations; both reach the same IIPS failure node.
5. `[0x849413B]` actual consumers: only gate path observed so far.
6. `[0x849B500]` actual consumers: only gate path observed so far.
7. `[0x849B501]` actual consumers: only gate path observed so far.
8. First new stable native node after gate bypass: IIPS initialization / WIN_IIPS_INIT_ERROR.
9. Engine/Game/Renderer/filesystem reached: not confirmed.
10. New fatal condition: yes, IIPS init error.
11. TenProxy/TCLS mapping: TenProxy modules loaded in all observed cases; no TCLS shared-memory mapping observed.
12. `WIN_NO_TCLS` separated from full bootstrap: yes. It is a pre-bootstrap command-line gate, not the sole requirement.

## Final

```text
GATE_BYPASS_CONFIRMED
POST_GATE_BOOTSTRAP_NODE_CONFIRMED
POST_GATE_FATAL_NODE_CONFIRMED
MODE_SEMANTICS_UNRESOLVED
```

Stop condition met: do not enumerate more `-q/-qa` combinations. The next
useful step is the consumer graph for `0x849413B`, `0x849B500`, and
`0x849B501`, plus the IIPS init call site returning `0x8189FEC`.
