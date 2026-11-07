# EX-044 STUN Caller Upstream Native Bootstrap Chain

## Final Classification

```text
STUN_CALLER_STATIC_CONFIRMED
STUN_BOOTSTRAP_PARENT_CONFIRMED
BOOTSTRAP_DISPATCHER_CANDIDATE_CONFIRMED
ONLY_KNOWN_WRITERS_CONFIRMED
NO_NEW_EXECUTION_NODE
```

The STUN init function `EXE+0x2212C0` is statically reachable from a
plain `.text` network/bootstrap chain:

```text
0x4FD9B0
  -> 0x4FCEE0
  -> 0x808650
  -> 0x7E98F0
  -> 0x6212C0
       -> 0x621AC6 (internal recursive call)
```

All links are direct `E8` calls recovered from live executable memory.
No L3/L4 execution was obtained.

## Correction of EX-043 Caller

`0x621AC6` is not an external caller of `0x6212C0`. It is an internal
recursive/re-entry call inside `0x6212C0`:

```asm
00621AB8 inc [0x82E13F8]
00621ABE push 1
00621AC0 mov [0xE59D20], edi
00621AC6 call 0x6212C0
00621ACB mov ecx, [0x766A20C]
00621AD1 add esp, 4
00621AD4 mov [0xE9BD714], ecx
```

The external caller is `0x7E9913`, inside function `0x7E98F0`.

## Function Boundaries

```text
0x6212C0  start
0x621AF5  end (ret)
0x7E98F0  start (network subsystem init)
0x7E9A35  end (ret)
0x808650  start (wrapper)
0x808650  short function, calls 0x7E98F0 then 0xBAEDF0
0x4FCEE0  start (bootstrap dispatcher candidate)
0x4FDA??  large body includes 0x4FD287 call
0x4FD9B0  start (top-level bootstrap candidate)
```

`0x4FD9B0` and `0x4FCEE0` are marked as candidates because they contain
multiple initialization calls, not because their names are known.

## Caller Table

| Caller | Callee | Type | Evidence |
| --- | --- | --- | --- |
| 0x621AC6 | 0x6212C0 | direct, internal recursive | L2 |
| 0x7E9913 | 0x6212C0 | direct, external | L2 |
| 0x808658 | 0x7E98F0 | direct | L2 |
| 0x4FD287 | 0x808650 | direct | L2 |
| 0x4FDA03 | 0x4FCEE0 | direct | L2 |

## Network Subsystem Init

`0x7E98F0` is a network bootstrap function:

```text
call 0x7E84A0
check [0xE85C28]
call 0x6212C0
call 0x7FA4C0
call 0x7EF830
call 0x639D00
call 0x4A1F60
call 0x642620
call 0x4AB840
call 0x801020
call 0x4A9A60
call 0x4A3300
call 0x7F9F60
```

It writes network/state globals:

```text
0x82C4A78
0x82C4A68
0x82C4A6C
0x849B5CC
0x81AA110
0x81AA114
0x81AA118
0x849BA38
```

This is a strong plain `.text` network bootstrap parent.

## Bootstrap Dispatcher Candidate

`0x4FCEE0` is a large initialization function with many calls. It
includes the path to `0x808650 -> 0x7E98F0 -> 0x6212C0`.

`0x4FD9B0` calls `0x4FCEE0` and then performs string/global setup. It is
the highest recovered plain `.text` bootstrap candidate in this chain.

## Return Value Propagation

`0x6212C0` return value:

```text
external caller 0x7E9913: NOT TESTED
internal caller 0x621AC6: NOT TESTED
```

The internal recursive call stores:

```text
[0xE9BD714] = [0x766A20C]
```

No return-status branch was found after either call to `0x6212C0`.

## Mode Global Writers

`0x849413B` writers:

```text
0x37F5F7  mov [0x849413B], 1
0x37F612  mov [0x849413B], 1
```

`0x849B500` writers:

```text
0x37F65C  mov [0x849B500], 1
0x37F679  mov [0x849B500], 1
```

No other plain `.text` writer was found:

```text
ONLY_KNOWN_WRITERS_CONFIRMED
```

## Causal Limitation

The STUN init function is statically located in the post-gate
network/bootstrap chain. This does not prove a causal relation to IIPS
fatal or to module load order.

## Answers

1. `0x621AC6` function boundary: same function as `0x6212C0`, start `0x6212C0`, end `0x621AF5`.
2. Callers: external `0x7E9913`; internal recursive `0x621AC6`.
3. Higher bootstrap dispatcher: `0x4FCEE0` and `0x4FD9B0` candidates.
4. `0x6212C0` return: not tested by callers; no status branch.
5. Other mode global writers: none found.
6. New L2 bootstrap chain: yes, `0x4FD9B0 -> 0x4FCEE0 -> 0x808650 -> 0x7E98F0 -> 0x6212C0`.
7. New L3/L4: none; this is static L2 only.

## Final

```text
STUN_CALLER_STATIC_CONFIRMED
STUN_BOOTSTRAP_PARENT_CONFIRMED
BOOTSTRAP_DISPATCHER_CANDIDATE_CONFIRMED
ONLY_KNOWN_WRITERS_CONFIRMED
NO_NEW_EXECUTION_NODE
```
