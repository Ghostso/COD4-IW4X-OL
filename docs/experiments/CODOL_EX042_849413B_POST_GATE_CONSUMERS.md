# EX-042 `0x849413B` Post-Gate Consumer Static and Local Runtime Validation

## Final Classification

```text
POST_GATE_GLOBAL_CANDIDATES_RECONSTRUCTED
0x849413B_CONSUMERS_STATIC_CONFIRMED
STUN_MODE_BRANCH_CONFIRMED
FIRST_READ_UNCONFIRMED
NO_NEW_EXECUTION_NODE
```

All four requested candidates are real `0x849413B` reads and affect
control flow. A new, more significant consumer was found at
`EXE+0x2213B9` / `EXE+0x2214C5`: the STUN/network initialization function
at `EXE+0x2212C0` selects server/behavior based on both `0x849413B` and
`0x849B500`. Runtime memory validation confirmed the global is `1` during
`-q`, but no executed hitsite was captured, so this round produces no new
L3/L4 execution node.

## Method

```text
independent copy : 工具/EX035_DIR
launch           : codoMP_client_shipRetail.exe -q
observer         : read-only runtime executable memory scan + disassembly
```

No write, no hook, no debugger attach was used.

## Runtime Global State

At the IIPS fatal dialog:

```text
[0x849413B] = 0x01
```

Runtime scan found 9 byte-pattern hits. The real read instructions are:

```text
EXE+0x2213B9  cmp byte ptr [0x849413B], 0
EXE+0x2214C5  cmp byte ptr [0x849413B], 0
EXE+0x237770  cmp byte ptr [0x849413B], bl
EXE+0x355871  cmp byte ptr [0x849413B], al
EXE+0x37F5F7/0x37F612  mov byte ptr [0x849413B], 1
EXE+0x37F6E8  cmp byte ptr [0x849413B], 0
EXE+0x402423  cmp byte ptr [0x849413B], al
EXE+0x402CD3  cmp byte ptr [0x849413B], 0
```

The requested four candidates all appear in this list.

## Candidate Classification

### `EXE+0x402423`

```text
read: YES
branch: YES
classification: C2
```

It reads:

```text
0x849413A
0x849413B
```

then computes booleans and calls `0x759F50` with them. `0x759F50` is a
large structure builder used by a network/config path. Function start and
direct caller were not recovered; no standard prologue was found within
0x1000 bytes before the read.

### `EXE+0x402CD3`

```text
read: YES
branch: YES
classification: C1
```

It controls whether three string calls run:

```text
_CODO_disconnect0.log
_CODO_disconnect1.log
_CODO_disconnect2.log
```

Function start:

```text
EXE+0x402CA0
```

Direct caller:

```text
0x6424AF
```

This candidate controls logging, not module initialization.

### `EXE+0x237772`

```text
read: YES
branch: YES
classification: C1/C2
```

Function start:

```text
EXE+0x237720
```

Direct caller:

```text
0x637945
```

When the flag is zero the function proceeds through a block that can call
`0x780140`; when nonzero it jumps away. The called function is not yet
identified.

### `EXE+0x355871`

```text
read: YES
branch: YES
classification: C1
```

Function start:

```text
EXE+0x354840
```

This is a command/dispatch-style function with switch cases. The flag read
sets:

```text
[0x8426AEC] = 1
```

and produces a boolean return. No direct `E8` caller was found; it is
likely reached through a function pointer/vtable.

## New High-Value Consumer: STUN/Network Mode Branch

The scan found two additional real reads:

```text
EXE+0x2213B9
EXE+0x2214C5
```

Both are inside:

```text
EXE+0x2212C0
```

which is a network/STUN initialization function. It selects between:

```text
stun1-tub.codol.qq.com
stun.us.demonware.net
```

Control flow:

```asm
006213B9 cmp byte ptr [0x849413B], 0
006213C0 je  0x6213CB
006213C2 cmp byte ptr [0x849B500], 0
006213C9 je  0x621425
```

So:

```text
q==0 OR qa!=0  -> path using stun.us.demonware.net
q!=0 AND qa==0 -> path using stun1-tub.codol.qq.com
```

This is a real post-gate mode branch, not just the `WIN_NO_TCLS` gate.

Function callers:

```text
0x621AC6 direct call
0x7E9913 direct call pattern
```

`0x621AC6` is the cleaner caller:

```asm
00621AC0 mov [0xE59D20], edi
00621AC6 call 0x6212C0
```

## FIRST READ

```text
FIRST_READ_UNCONFIRMED
```

Execution order was not proven. `EXE+0x2213B9` is the strongest candidate
for the first significant post-gate read because it selects STUN/network
behavior and reads both q/qa flags, but it was not observed executing.

## Dynamic Validation Result

Runtime validation confirmed:

```text
[0x849413B] == 1
candidate instructions present in executable memory
STUN strings resolved
```

It did not confirm execution of any candidate instruction. No local
debugger breakpoint was used because EX-028 demonstrated debugger-induced
divergence and no safe single-address validation method was available.

## Answers

1. Four candidates: all real reads; `0x402423` C2, `0x402CD3` C1, `0x237772` C1/C2, `0x355871` C1.
2. Which truly read `0x849413B`: all four, plus `0x2213B9` / `0x2214C5`.
3. FIRST READ: unconfirmed; strongest candidate `0x2213B9`.
4. Control flow impact: yes for all; `0x2213B9` selects STUN/network mode.
5. Init/thread/module link: `0x2212C0` is network/STUN initialization; `0x402423` feeds `0x759F50`; no thread/LoadLibrary link proven.
6. L3/L4: none.
7. Stop: yes, no further candidate enumeration.

## Final

```text
POST_GATE_GLOBAL_CANDIDATES_RECONSTRUCTED
0x849413B_CONSUMERS_STATIC_CONFIRMED
STUN_MODE_BRANCH_CONFIRMED
FIRST_READ_UNCONFIRMED
NO_NEW_EXECUTION_NODE
```
