# ICH-049 — Engine Object / Resource Object Layout

## Engine Root Object (confirmed from runtime dispatch table)

```
Root Object (runtime instance UNKNOWN)
 ├── +0x00   vtable → 0x00E83B00 (96-entry dispatch table)
 ├── +0x14   → Resource Object (pointer)
 ├── +0x20   → State Object (pointer)
 └── +0x4C   → Config/FileSystem subsystem (pointer)
```

## Resource Object (accessed via Root+0x14)

```
Resource Object
 ├── +0x0C   → counter/list object (pointer)
 │             └── +0x10C → context object (for log/report)
 ├── +0x40   → Nested Object (pointer)
 │             │
 │             ├── +0x08   → inner query object (pointer)
 │             │
 │             ├── +0x0C   → counter (event notification)
 │             │
 │             ├── +0x90   → handle/state pointer
 │             │             └── +0x08 → inner object (for query)
 │             │
 │             └── +0x10   → refcount/state flags (bitfield)
 │                          test eax, 0x3FFFFF
 │                          dec eax
 │                          mov [ecx+0x10], eax
 │
 └── +0x90   → (same as nested+0x90, direct access)
```

## Key offsets confirmed from disassembly

| Object | Offset | Type | Purpose |
|---|---|---|---|
| Root | +0x00 | vtable | 96-entry dispatch table |
| Root | +0x14 | pointer | → Resource Object |
| Root | +0x20 | pointer | → State Object |
| Root | +0x4C | pointer | → Config/FS subsystem |
| Resource | +0x0C | pointer | → counter/list |
| Resource | +0x40 | pointer | → Nested Object |
| Resource | +0x90 | pointer | → handle/state |
| Nested | +0x08 | pointer | → inner query object |
| Nested | +0x0C | pointer | → counter (for log) |
| Nested | +0x90 | pointer | → handle/state |
| Counter | +0x10C | pointer | → context object (log/report) |
| Inner | +0x08 | pointer | → query target |
| State ptr | +0x10 | DWORD | refcount (test 0x3FFFFF, dec) |
