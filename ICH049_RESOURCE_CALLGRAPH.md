# ICH-049 — Resource Cluster Callgraph

## Confirmed Structure

```
Engine Root Object (dispatch table owner)
 │
 │  Slot 41 (0x00E83C48)
 │  → 0x009C2E30 (Resource State Sync)
 │
 │  ┌────────────────────────────────────────────┐
 │  │ 0x009C2E30 (Resource State Sync)           │
 │  │                                            │
 │  │  Read: [this+0x14] → Resource Object       │
 │  │  Read: [Resource+0x40] → Nested Object     │
 │  │  Read: [Nested+0x90] → handle             │
 │  │  Query: call 0x00831DF0 (Base.dll)        │
 │  │  Get: call 0x009F0020 (Engine)            │
 │  │  Check: call 0x009FF300 (Engine)          │
 │  │  Final: call 0x00A597D0 (Engine)          │
 │  │  Update: *arg1 = new_state                │
 │  │                                           │
 │  │  For each active bit in query result:      │
 │  │    → call 0x008876F0 (log, Base.dll)      │
 │  │    → call 0x009C2940 (process, Engine)    │
 │  │    → call 0x008875F0 (cleanup, Base.dll)  │
 │  └────────────────────────────────────────────┘
 │
 │  0x009C2940 (process_item) — Engine gap
 │  → THE key Engine-side callee from Slot 41
 │  → Called 0-4 times depending on query bitmask
 │  → This is the candidate bridge from Resource → FF/Zone
```

## Cluster 3 (0x009C12D0..0x009C1930) — 15 dispatch slots

Revised from ICH-048 probe:
- Slot 37 (0x009C1310): this+0x20 → [+0x14] → vtable[1] — **NOT direct Resource** (virtual dispatch)
- First function 0x009C1310 dispatches through State Object, not directly through Resource

## Cluster 4 (0x009C2A40..0x009C2E30) — 2 dispatch slots

- Slot 45 (0x009C2A40): this+0x20 — **State Object function** (REFUTED as Resource)
- **Slot 41 (0x009C2E30): this+0x14 — CONFIRMED Resource function**

## Resource → FF/Zone chain status

```
Slot 41 → 0x009C2E30 → 0x009C2940 (process_item)
                             ↓
                      FF/Zone? → NOT CONFIRMED
                      (need to analyze 0x009C2940)
```

The chain from Resource to FF/Zone goes through `0x009C2940 (process_item)`.
This is the only remaining link that needs to be traced to close the loop.

## Direct callees from 0x009C2E30

| Address | Module | Role | In Engine Gap? |
|---|---|---|---|
| 0x00831DF0 | Base.dll | query helper | NO (before gap) |
| 0x009F0020 | Engine gap | get result | YES |
| 0x009FF300 | Engine gap | check valid | YES |
| 0x00A597D0 | Engine gap | get final value | YES |
| 0x0093B6E0 | Base.dll | refcount dec | NO |
| 0x008876F0 | Base.dll | log/report | NO |
| **0x009C2940** | **Engine gap** | **process_item** | **YES** |
| 0x008875F0 | Base.dll | cleanup | NO |
