# EX-045 Native Bootstrap Dispatcher Static Call Chain

## Final Classification

```text
BOOTSTRAP_DISPATCHER_STATIC_CHAIN_CONFIRMED
BOOTSTRAP_UPSTREAM_CALLER_CONFIRMED
NETWORK_SUBSYSTEM_STATIC_CHAIN_CONFIRMED
MULTI_SUBSYSTEM_INIT_CONFIRMED
NO_NEW_EXECUTION_NODE
NO_TVM0_DEPENDENCY
```

The plain `.text` chain is fully recovered as L2:

```text
0x77F8B3 (inside gate/bootstrap function 0x77F580)
  -> 0x4FD9B0
  -> 0x4FCEE0
  -> 0x808650
  -> 0x7E98F0
  -> 0x6212C0 (STUN/network mode init)
       -> 0x621AC6 (internal recursive call)
```

All links are direct `E8` calls in live executable memory. No L3/L4.

## Function Boundaries

```text
0x6212C0 start
0x621AF5 end

0x7E98F0 start
0x7E9A35 end

0x808650 start
0x808932 end

0x4FCEE0 start
0x4FD8DF end (first ret path)

0x4FD9B0 start
0x4FDADB end

0x77F580 gate/bootstrap function start
0x77FA6F end before error-display function 0x77FA70
```

## Caller/Callee Graph

```text
0x77F8B3 -> 0x4FD9B0
0x4FDA03 -> 0x4FCEE0
0x4FD287 -> 0x808650
0x808658 -> 0x7E98F0
0x7E9913 -> 0x6212C0
0x621AC6 -> 0x6212C0 (recursive)
```

## Direct Callsites

### 0x7E98F0

```text
0x7E84A0
0xB76D80
0x6212C0
0x7FA4C0
0x7EF830
0x639D00
0x4A1F60
0x642620
0x4AB840
0xB74220
0x4B6510
0x801020
0x4A9A60
0x4A3300
0x7F9F60
0x6C2E30
0x724EB0
0x4B1B10
```

### 0x808650

```text
0x7E98F0
0xBAEDF0
0xBAEAB0
0x758A10
0x66B7A0
0x480A30
0x7C1070
0x809E00
0xB74220
0x4B6510
0x721550
0xC42DE0
0x770C60
0x770890
```

### 0x4FCEE0

Contains a long initialization sequence, including:

```text
0x4F86E0
0x74B800
0x774440 / 0x7744A0
0x4F3B70
0xBC9790
0x4F89E0
0x4FC400
0x77C500
0x74ADF0
0x74B6D0
0x768650
0x528DE0
...
0x4FD287 -> 0x808650
...
0x4F37A0
0xC3F4DC
```

This is a multi-subsystem initialization function.

### 0x4FD9B0

```text
0xC43280
0xC435C0
0x4FCEE0
0x774900
0x4F2FF0
0x4F2EC0
0x4F8B20
0x401130
0x7755D0
0x4FD900
0xC3C20F
```

## Indirect Calls

Indirect calls are present through internal IAT/thunk slots:

```text
0xCA812C
0xCA8190
0xCA819C
0xCA8170
0xCA8534
0xCA8114
0xCA818C
0xCA84C8
```

Function-pointer calls via registers also occur:

```text
call edi / esi / ebx
```

The exact API names behind these slots are not named in this report.

## Global Read/Write

Mode globals:

```text
0x849413B read at 0x6213B9, 0x6214C5, and earlier consumers
0x849B500 read at 0x6213C2, 0x6214D2
```

These reads happen inside `0x6212C0` STUN mode selection.

Other state globals in the dispatcher path:

```text
0xE59D20
0x82E13F8
0x82C4A78
0x82C4A68 / 0x82C4A6C
0x849B5CC
0x81AA110 / 0x81AA114 / 0x81AA118
0x849BA38
0x76595A4 / 0x76595A8 / 0x76595AC
0x766929C
```

## Initialization Ordering

High-level order:

```text
gate function 0x77F580
  -> 0x4FD9B0
    -> 0x4FCEE0
      -> ... subsystem init ...
      -> 0x808650
        -> 0x7E98F0
          -> 0x6212C0 STUN mode selection
        -> subsequent network/config init
      -> subsequent subsystem init
```

## Bootstrap Dispatcher Evidence

`0x4FCEE0` and `0x4FD9B0` both satisfy the dispatcher shape:

```text
multiple direct initialization calls
state/global writes
network init call in the middle
subsequent init calls
```

`0x77F580` is now confirmed as the native gate/bootstrap function that
contains the direct call `0x77F8B3 -> 0x4FD9B0`.

## TVM0 Boundary

The recovered links are all plain `.text` direct calls:

```text
NO_TVM0_DEPENDENCY
```

The caller above `0x77F580` was not recovered; if pursued further it may
reach a packed/VM boundary.

## Evidence Level

```text
L2 only
```

No normal-run execution confirmation exists for this chain.

## Answers

1. Function boundaries: listed above.
2. Caller/callee graph: listed above.
3. Direct callsites: selected callsites listed per function.
4. Indirect-call evidence: IAT slots and register calls listed.
5. Global read/write: mode globals and dispatcher state globals listed.
6. Initialization ordering: gate -> 0x4FD9B0 -> 0x4FCEE0 -> 0x808650 -> 0x7E98F0 -> STUN.
7. Bootstrap dispatcher candidate evidence: `0x4FCEE0` / `0x4FD9B0` confirmed as multi-call dispatcher candidates.
8. `.tvm0` boundaries: none in this chain; possible above gate caller.
9. Evidence level: L2 static.
10. Final classification: above.

## Final

```text
BOOTSTRAP_DISPATCHER_STATIC_CHAIN_CONFIRMED
BOOTSTRAP_UPSTREAM_CALLER_CONFIRMED
NETWORK_SUBSYSTEM_STATIC_CHAIN_CONFIRMED
MULTI_SUBSYSTEM_INIT_CONFIRMED
NO_NEW_EXECUTION_NODE
NO_TVM0_DEPENDENCY
```
