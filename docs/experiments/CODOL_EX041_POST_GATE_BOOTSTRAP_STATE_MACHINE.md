# EX-041 Post-Gate Native Bootstrap Timeline and State Machine Differential

## Final Classification

```text
POST_GATE_BOOTSTRAP_TIMELINE_RECONSTRUCTED
Q_QA_POST_GATE_BEHAVIOR_EQUIVALENT
DIFFERENTIAL_NODE_CONFIRMED
BOOTSTRAP_DISPATCHER_UNRESOLVED
STATE_MACHINE_UNRESOLVED
NO_NEW_EXECUTION_NODE
```

`-q` and `-qa` share the same observable post-gate lifecycle. The only
differential node against no-argument startup is the appearance of
`iips.dll` plus the `iipsinit` window before the fatal UI. No new
executed native callsite was captured, so the bootstrap dispatcher and
state machine remain unresolved.

## Method

Independent copy:

```text
工具/EX035_DIR
```

Runs:

```text
A = no args
B = -q
C = -qa
```

Observer: Toolhelp module/thread polling plus window enumeration. No API
hook, no debugger, no memory write, no process-tree spoofing.

## A/B/C Module Differential

### A: no args

```text
libcef -> BugTrace -> VSDDrvDll -> ACE-DRV32 -> tersafe
  -> TenRpcs -> GameRpcs -> GDPLoader/tcj
  -> GameDataPlatformServer -> policyprobe/ace-ats32/gcloudvoice
  -> TenProxy/GbSpy
  -> WIN_NO_TCLS

threads: 56
iips.dll: absent
iipsinit: absent
```

### B: -q

```text
same module order through TenProxy/GbSpy
  -> iips.dll
  -> iipsinit
  -> WIN_IIPS_INIT_ERROR / 8189FEC

threads: 63
iips.dll: present
iipsinit: present
```

### C: -qa

```text
same module order through TenProxy/GbSpy
  -> iips.dll
  -> iipsinit
  -> WIN_IIPS_INIT_ERROR / 8189FEC

threads: 63
iips.dll: present
iipsinit: present
```

## Differential Node

```text
DIFFERENTIAL_NODE:
iips.dll load
iipsinit Environment List Box window
extra thread cluster
```

This appears only in B/C, not A. It is a temporal differential, not a
proven caller/callee relation.

## Thread Temporal Correlation

In B and C, thread first-seen counts were both 63, and the iips-stage
thread cluster appeared at the same sample as `iips.dll`. Thread start
addresses could not be obtained with non-elevated
`NtQueryInformationThread`, so thread-to-module attribution is
`L3 TEMPORAL CORRELATION` only.

## State Machine Candidates

Runtime-decoded references to `0x849413B` from EX-031:

```text
EXE+0x402423
  cmp byte ptr [0x849413B], 0
  setne al
  push flags
  call 0x759F50

EXE+0x402CD3
  cmp byte ptr [0x849413B], 0
  jne skip three log/string calls

EXE+0x237772
  cmp byte ptr [0x849413B], bl
  jne 0x6377D1
  test eax, eax
  jle 0x6377D1

EXE+0x355873
  cmp byte ptr [0x849413B], al
  mov dword ptr [0x8426AEC], 1
  sete al
```

These are write/read/branch candidates with actual instruction-level
dataflow, but none were proven executed in this experiment. They are:

```text
L2 STATE-MACHINE CANDIDATE
```

No equivalent runtime consumer list was obtained for `0x849B500` or
`0x849B501`.

## Fatal Dispatcher Candidate

Known runtime error display path:

```text
EXE+0x37FA70
```

was executed for `WIN_NO_TCLS` in EX-031. It formats a localized message
and displays the `#32770` fatal dialog.

The IIPS error keys are in the same EXE localization/error cluster:

```text
WIN_IIPS_INIT_ERROR
WIN_IIPS_INIT_FAILED
WIN_IIPS_DLL_ERROR
```

This makes `EXE+0x37FA70` a candidate common fatal dispatcher:

```text
startup_error(key/code)
  -> localization lookup
  -> EXE+0x37FA70
  -> #32770
```

Classification:

```text
FATAL_DISPATCHER_CANDIDATE_L2
```

The IIPS-specific execution of `0x37FA70` was not observed, so it is not
upgraded to L3 for the IIPS path.

## Answers

1. First verifiable post-gate bootstrap node after `-q`: no new executed node was captured; the first differential observable is `iips.dll` load plus `iipsinit`.
2. `-q` vs `-qa`: equivalent in module order, thread count, window set, and fatal node for this experiment.
3. Initialization state variables found: `0x849413B` has four runtime-decoded consumer/branch sites; full state machine unresolved.
4. Unified fatal dispatcher: candidate `EXE+0x37FA70`; not confirmed for IIPS.
5. New L3 execution node: none.
6. New L4 caller/callee chain: none.
7. Stop expanding dynamic observer: yes.

## Final

```text
POST_GATE_BOOTSTRAP_TIMELINE_RECONSTRUCTED
Q_QA_POST_GATE_BEHAVIOR_EQUIVALENT
DIFFERENTIAL_NODE_CONFIRMED
BOOTSTRAP_DISPATCHER_UNRESOLVED
STATE_MACHINE_UNRESOLVED
NO_NEW_EXECUTION_NODE
```
