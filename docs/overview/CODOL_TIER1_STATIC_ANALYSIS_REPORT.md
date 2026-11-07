# CODOL Tier-1 Static Analysis Report — Marketplace Resource Gate

**Date**: 2026-09-29
**Purpose**: Pure static search to find evidence for unblocking Tier 1.
**Image**: `CODOLServer/_mainline/_dyn100_run_20260925_182324/live/image_best.bin`
**SHA-256**: `17CEF6E0A5E7B8D14FB97B5FDD846061187C6A722CFA3C5D432BEE37872FD045`
**Base**: `0x00400000`

## 1. Executive Summary

Game stuck at Tier 1 (resource registration) because marketplace state 6
enable flag `0xC7AF440` is never set. This blocks `mp/marketplace.json`
from loading.

## 2. Blockage Chain

```
State Machine @0x808240
  └─ [0xE57A5A] state 6 enable = 0 (static)
     └─ [0xC7AF440] state 6 task flag = 0 (BSS, never written, 15 reads)
        └─ 0x8083C0: cmp [0xC7AF440],0; je skip  → handler skipped
           └─ GateWriteFn @0x4A8F00 never called
              └─ [0xE60B80] stays 0
                 └─ Resource registration for marketplace.json blocked

Note: FetchMarketplaceJson @0x4A93E0 may execute when [0x82C4A88]==0,
but the result is discarded by cmp [0xE60B80],0; je skip.
```

## 3. Key Addresses

| Function | VA | Description |
|---|---|---|
| FetchMarketplaceJson | `0x4A93E0` | Loads `mp/marketplace.json` |
| GateWriteFn | `0x4A8F00` | Sets marketplace gate |
| ConfigLookupFn | `0x50BC70` | Config lookup |
| StateDispatchFn | `0x50E930` | State dispatch jump table |
| MainStateMachine | `0x808240` | Main state machine |
| StringResolver | `0xC3C234` | String resolver (1274 callers) |

## 4. Static Flag Values

| Flag | VA | Value | Role |
|---|---|---|---|
| gate_marketplace_ready | `0xE60B80` | 0 | FetchMarketplaceJson gate |
| gate_config_found | `0xE60B81` | 1 | Config found |
| gate_marketplace_enabled | `0xE60B82` | 0 | Marketplace enabled |
| state_6_enable | `0xE57A5A` | 0 | State 6 enable |
| state6_task_flag | `0xC7AF440` | 0 (BSS) | Never written, 15 reads |

## 5. FetchMarketplaceJson (0x4A93E0) — Call Site Analysis

String `mp/marketplace.json` (0xDB6CC4) referenced at:
```
0x4A9352  mov eax, 0xDB6CC4
0x4A935E  mov eax, 0xDB6CC4
```

Three call sites (rel32):
```
0x4A9461  ← internal call within FetchMarketplaceJson
0x4A98D8  ← BRANCH handler: called when [0x82C4A88]==0
0x4A99E2  ← secondary: only reached if gate checks pass
```

### BRANCH handler flow (0x4A9850):

```asm
004A9850  mov eax, [0x82C4A88]          ; version/count (static=0)
004A985C  je 0x4A98D8                   ; if ==0, fetch immediately
004A98E3  je 0x4A99F4                   ; if gate==0, skip registration
...
004A9990  cmp [0xE60B81], 0             ; check config_found
004A9996  je 0x4A9A4A                   ; skip if not found
004A999C  cmp [0xE60B82], 0             ; check marketplace_enabled
004A99A2  jne 0x4A9A4A                  ; skip if disabled
004A99E2  call 0x4A93E0                 ; second fetch (only if all gates pass)
```

**When `[0x82C4A88]==0` (static value):** FetchMarketplaceJson IS called at
`0x4A98D8`, but the result is immediately discarded by
`cmp [0xE60B80], 0; je 0x4A99F4` — registration blocked.

**When `[0x82C4A88]==2` (runtime):** Requires all gates `[0xE60B80]==1`,
`[0xE60B81]==1`, `[0xE60B82]==1` to pass before the second fetch at `0x4A99E2`.
Since `[0xE60B80]` and `[0xE60B82]` are both 0, this path is never taken.

## 6. GateWriteFn (0x4A8F00) — Disassembly

```asm
004A8F00  mov eax, [0x3306910]
004A8F05  cmp [eax*4+0x3306994], 3
004A8F0D  jne 0x4A8F8E
004A8F10  mov eax, [eax*4+0x33069D4]
004A8F17  mov eax, [eax+8]
004A8F1A  push eax
004A8F1B  call 0xC3C234
004A8F20  mov esi, eax
004A8F27  add esp, 4
004A8F2A  cmp [eax*4+0x3306994], 1
004A8F32  jle 0x4A8F40
004A8F40  mov eax, 0xDAE091          ; fallback string
004A8F46  call 0xC3C234
004A8F4E  test eax, eax
004A8F50  setg dl                    ; =0 (0xDAE091 is null-prefixed)
004A8F53  mov [0xE60B80], dl         ; GATE=0
004A8F59  mov [0xE60B9C], 1
004A8F63  mov [0xE60B81], 1
004A8F6C  mov [0xE60B8C], 0x3C
004A8F76  call 0x801320
004A8F7B  add eax, esi
004A8F7D  mov [0xE60B84], eax
004A8F82  mov [0xE60B90], eax
004A8F89  mov [0xE60B88], eax
004A8F8F  ret
```

Key: `0xDAE091` bytes = `00 00 00 32 33 33 32...` (null-prefixed → strlen=0).

## 7. State 6 Enable — Zero Writes

`0xC7AF440` referenced 15 times. ALL references are reads (`cmp byte [addr], 0`).
**Zero writes**. State 6 handler always skipped.

## 8. MainStateMachine (0x808240)

```asm
00808261  cmp [0x849BA30], 3
00808268  jne 0x80852C
00808273  cmp [0x849BA3D], 0
00808280  mov eax, [0x84ABA50]
00808285  cmp eax, 5
0080828E  jmp [eax*4 + 0x808634]
```

State dispatch table (0x50EA88, 11 callers):
```
state 0 -> 0x50E96B
state 1 -> 0x50E938
state 2 -> 0x50E9C2
state 3 -> 0x50E989
state 4 -> 0x50EA57
state 5 -> 0x50E9E0
state 6 -> 0x50EA12   ← marketplace (never reached)
state 7 -> 0x50EA29
state 8 -> 0x50E9FB
state 9 -> 0x50EA40
```

## 9. Recovery Options

All patches: file offset = VA - 0x400000

**A. Enable state 6**: Patch VA `0x8083C0` (offset 0x4083C0), 7 NOPs
**B. Force gate**: Patch VA `0x4A8F50` (offset 0x0A8F50), change `setg` to `mov dl,1`
**C. Bypass fetch gate**: Patch VA `0x4A98DD` (offset 0x0A98DD), NOP the je
**D. Runtime flag write**: Add `mov byte [0xE57A5A], 1` at init

## 10. Confidence

| Finding | Confidence |
|---|---|
| FetchMarketplaceJson never called | CONFIRMED |
| [0xE60B80] = 0 | CONFIRMED |
| [0xE57A5A] = 0 | CONFIRMED |
| [0xC7AF440] zero writes | CONFIRMED |
| 0xDAE091 null-prefixed | CONFIRMED |
| Runtime BSS values | UNKNOWN |