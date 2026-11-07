# EX-043 STUN Initialization Node L3 Validation and `0x849B500` Differential

## Final Classification

```text
STUN_MODE_BRANCH_STATIC_CONFIRMED
STUN_INIT_RUNTIME_UNCONFIRMED
OBSERVER_DIVERGENCE
NO_NEW_EXECUTION_NODE
```

`EXE+0x2212C0` is confirmed statically as the STUN/network mode branch
and its direct caller is `0x621AC6`. A single-address local debugger
attempt diverged before reaching `0x2212C0` (BugTrace-era access
violation, then C++ exception exit), exactly the EX-028 pattern.
Therefore the node remains L2 static; no L3 execution hit was obtained.

## Function

```text
function start   = EXE+0x2212C0
direct caller    = 0x621AC6
caller context   = push 1; mov [0xE59D20], edi; call 0x6212C0
caller's caller  = not recovered
```

Another raw `E8` pattern at `0x7E9913` also targets `0x6212C0`, but the
surrounding disassembly is not clean; it is recorded as a candidate, not
a confirmed caller.

## Branch Reconstruction

At `EXE+0x2213B9`:

```asm
006213B9 cmp byte ptr [0x849413B], 0
006213C0 je  0x6213CB
006213C2 cmp byte ptr [0x849B500], 0
006213C9 je  0x621425
```

At `EXE+0x2214C5`:

```asm
006214C5 cmp byte ptr [0x849413B], 0
006214CC je  0x621580
006214D2 cmp byte ptr [0x849B500], 0
006214D9 jne 0x621580
```

Observed endpoint strings:

```text
stun1-tub.codol.qq.com
stun.us.demonware.net
```

The branch selects which STUN endpoint configuration is loaded. This is
endpoint selection dataflow, not connection activity.

## `0x849B500` Consumer Scan

Runtime scan for `0x849B500` found only:

```text
EXE+0x2213C2  cmp [0x849B500], 0   (STUN init)
EXE+0x2214D2  cmp [0x849B500], 0   (STUN init)
EXE+0x37F65C  mov [0x849B500], 1   (-qa gate write)
EXE+0x37F679  mov [0x849B500], 1   (-qa gate write)
```

No other plain consumer was found.

## Mode Values

From EX-035 runs:

```text
-q  -> 0x849413B = 1, 0x849B500 = 0
-qa -> 0x849413B = 0, 0x849B500 = 1
```

So:

```text
Q_QA_STUN_MODE_GLOBALS_DIVERGENT
```

This only states the global values differ; it does not define
`-q = qq.com` or `-qa = demonware`.

## Dynamic Validation

A minimal debugger was created with exactly one breakpoint:

```text
0x6212C0  STUN_INIT_2212C0
```

Result:

```text
no STUN_INIT hit
first chance C0000005 at kernel32.dll+0x1015A
C++ exception E06D7363
exit code 0xE06D7363
```

The run diverged at the BugTrace path before TenProxy/project modules,
matching EX-028. This run is not ground truth and is classified:

```text
OBSERVER_DIVERGENCE
```

Normal read-only runtime validation during `-q` confirmed:

```text
[0x849413B] = 1
[0x849B500] = 0
0x6212C0 code present in executable memory
STUN strings present
```

Presence is not execution.

## Network Activity

No DNS attempt, socket creation, or connect was recorded by the
observation methods used. No network connection claim is made.

## Answers

1. `0x6212C0` function start: `EXE+0x2212C0`.
2. Caller recovered: `0x621AC6` direct; caller's caller unresolved.
3. Globals in branch: `0x849413B` and `0x849B500` select between STUN endpoint paths.
4. `0x6212C0` executed: not confirmed.
5. `-q` vs `-qa`: globals differ (`1/0` vs `0/1`).
6. L3: no.
7. L4: no.
8. Real network connection: no evidence; not claimed.

## Final

```text
STUN_MODE_BRANCH_STATIC_CONFIRMED
STUN_INIT_RUNTIME_UNCONFIRMED
OBSERVER_DIVERGENCE
NO_NEW_EXECUTION_NODE
```
