# ICH-049 — Slot 41 (0x009C2E30) Complete Function Analysis

## Function Signature
- Calling convention: __thiscall, ret 4 (1 stack arg)
- ECX = Engine Root Object (dispatch table owner)
- arg1 (at [ebp+0x08]) = pointer to state variable (DWORD ptr)

## Access Chain
```
this → [this+0x14] → Resource Object
Resource Object → [+0x40] → Nested Object
Nested Object → [+0x90] → handle/state pointer
handle → [+0x08] → inner query object
```

## Complete Disassembly (0x009C2E30..0x009C2F7A)

Function size: 0x14A bytes (0x009C2E30 to 0x009C2F7A, ending with ret 4)

### Phase 1: Resource Query (0x009C2E30..0x009C2E6E)
1. `mov eax, [ecx+0x14]` — get Resource Object
2. `mov edi, [eax+0x40]` — get Nested Object
3. `mov ecx, [edi+0x90]` — get handle
4. `mov ecx, [ecx+0x08]` — get inner object
5. `call 0x00831DF0` — query method (Base.dll)
6. `call 0x009F0020` — get result (Engine gap)
7. `call 0x009FF300` — check validity (Engine gap)
8. `call 0x00A597D0` — get final value (Engine gap)
Result saved to [ebp-4] as bitmask.

### Phase 2: State Update (0x009C2E70..0x009C2E9C)
1. `mov ebx, [ebp+0x08]` — arg1 = state pointer
2. Compare query result (esi) with *arg1 (ecx)
3. If different: refcount decrement old value
4. `mov [ebx], esi` — update state

### Phase 3: Event Dispatch (0x009C2E9C..0x009C2F74)
Checks [ebp-4] bitmask (from Phase 1 query):
- bit 0 (test 0x01) → event type 3
- bit 2 (test 0x04) → event type 6
- bit 3 (test 0x08) → event type 5
- bit 1 (test 0x02) → event type 4

For each active bit:
1. `call 0x008876F0` (log/report) with format string + event type
2. `call 0x009C2940` (process_item) — **Engine gap function**
3. `call 0x008875F0` (cleanup)

### Epilogue (0x009C2F74)
`ret 4`

## Callees

| Address | Module | Purpose | Evidence |
|---|---|---|---|
| 0x00831DF0 | Base.dll | query helper | callee |
| 0x009F0020 | Engine gap | get result | callee |
| 0x009FF300 | Engine gap | check valid | callee |
| 0x00A597D0 | Engine gap | get final value | callee |
| 0x0093B6E0 | Base.dll | refcount decrement | callee |
| 0x008876F0 | Base.dll | log/report (4 calls) | callee |
| **0x009C2940** | **Engine gap** | **process_item (4 calls)** | **callee** |
| 0x008875F0 | Base.dll | cleanup | callee |

## Semantic Role

This is a **Resource State Synchronization function**.

It queries the Resource subsystem for current state, updates a caller-provided state pointer, and dispatches 0-4 notification events based on the query result bitmask.

It does NOT directly:
- Open/read files
- Allocate zone memory
- Initialize Asset DB
- Reference FF strings

It indirectly triggers resource operations through `process_item (0x009C2940)`.
