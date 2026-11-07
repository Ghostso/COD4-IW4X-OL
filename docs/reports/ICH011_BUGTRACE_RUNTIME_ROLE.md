# ICH-011 — BugTrace.dll Runtime Role

## Objective

Classify BugTrace.dll as Platform/Diagnostic, IIPS/IFS2 bridge, Game
Engine bridge, or startup failure boundary.

## Evidence Basis

- ICH-008 shared dynamic timeline (3/3 stable runs)
- ICH-009 complete post-ordinal-1 event attribution
- Static PE analysis of `COD OL\BugTrace.dll` (SHA256 `1FDB07E47C0BAD6024309D6DCDDA0EED3B1A87BCAC61B57DC0EF750CB2225646`)
- EX-057 normal `-q` kernel image trace

## Runtime Participation

```text
BUGTRACE_RUNTIME_PARTICIPATION = CONFIRMED
```

BugTrace.dll loads in 3/3 stable runs at `t≈0.64s`, creates its own
native thread (`BugTrace.dll+0xB233`), and re-enters ordinal-1 (the
Base.dll `.tvm0` VM entry stub) via `GetProcAddress`-resolved function
pointer call at `BugTrace.dll+0x11F2F`.

## Thread Creation

```text
BUGTRACE_THREAD_CREATION = CONFIRMED
```

The VM dispatch creates a native thread starting at `BugTrace.dll+0xB233`
(`thread_id=11856` in run `ORD1_A_01`). This is BugTrace's own worker
thread, not a game engine thread.

## BugTrace-to-IIPS/IFS2

```text
BUGTRACE_TO_IIPS_IFS2 = NOT_OBSERVED
```

Static PE analysis confirms BugTrace.dll has:

- **Zero references** to `iips.dll`, `IFS2.dll`, or `CreateIFSLibDll`
- No shared call chain with IIPS initialization
- No cross-module dependency on IIPS or IFS2 components

`iips.dll` loads separately during normal `-q` runs, after BugTrace has
already completed its platform initialization role.

## BugTrace-to-Engine

```text
BUGTRACE_TO_ENGINE = NOT_OBSERVED
```

BugTrace re-enters ordinal-1 (VM re-entry), then creates its own
platform thread. All post-BugTrace thread start addresses, exception
addresses, and call targets resolve to:

| Component | Evidence |
|-----------|----------|
| Base.dll `.tvm0` | VM internal threads (3/3 runs) |
| BugTrace.dll `.text` | Own thread start (3/3 runs) |
| mswsock.dll `.text` | Network thread |
| kernel32.dll `.text` | Access violation during OS call |
| ntdll.dll | Fail-fast termination |

No thread start, exception address, or call target falls within the
EXE 2.7 MB virtual-only Game Engine region (`0x00994000..0x00CA789A`).

## Failure Path

```text
BUGTRACE_FAILURE_PATH = CONFIRMED
```

The BugTrace-reentered VM thread attempts a native OS call via
`combase.dll` which fails with an access violation (`0xC0000005` at
`kernel32.dll+0x1015A`). Subsequently, the process terminates with
fail-fast (`0xC0000409`) from `ntdll.dll`. BugTrace's own activity is
the **immediate trigger** of the failure path that prevents Engine
activation in the debug-observer environment.

**Classification:** BugTrace.dll is a **Platform/Diagnostic/anti-cheat
component**. It is not an IIPS/IFS2 bridge and not a Game Engine bridge.

## Static Priority Point Verification

The task specification identified `BugTrace.dll+0x11F2E` as a priority
observation point (`call eax`).

### Static confirmation

```text
RVA 0x11F1E: call [0x1009D094]  ; KERNEL32.dll::GetProcAddress
RVA 0x11F24: test eax, eax
RVA 0x11F26: je 0x11F33         ; NULL → skip
RVA 0x11F28: push 0x38689866
RVA 0x11F2D: call eax           ; ← priority point (dynamic hit)
RVA 0x11F2F: mov [esp+0xC], eax ; return slot (dynamic hit)
```

### Dynamic confirmation (3/3 runs)

```text
ordinal-1 entry #3 retaddr = BugTrace.dll+0x11F2F
ordinal-1 entry #3 [ESP+4] = 0x38689866 (push constant)
```

The push constant `0x38689866` is an arbitrary identifier/handle pushed
before the call. Its semantic meaning is `UNKNOWN` per evidence
discipline.

## Hard Stop Check

BugTrace → Engine confirmed? **No.** Failure/termination without Engine
handoff confirmed? **Yes.** Hard stop condition met.

