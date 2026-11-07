# Reload event parameters in native snapshots

The parameter resolver now accepts zero for native `EV_RELOAD`,
`EV_RELOAD_FROM_EMPTY`, `EV_RELOAD_START`, and `EV_RECHAMBER_WEAPON`. Their CoDOL
IDs remain 18, 19, 20, and 34. Previously their IDs were mapped but their
parameters were unresolved, preventing automatic queue composition.

Retained `_bg_weapons.asm` emits these through `PM_AddEvent`; the implementation
in `_bg_pmove.asm` explicitly passes parameter zero to
`BG_AddPredictableEventToPlayerstate`.

Static C1 evidence on the previously recorded executable hash:

| Event | Event write | Zero parameter write |
| --- | --- | --- |
| Reload | `0x41944b`, ID `0x12` | `0x419456` |
| Empty reload | `0x4193c4`, ID `0x13` | Jumps at `0x4193cf` to `0x419456` |
| Reload start | `0x419618`, ID `0x14` | `0x419623` |
| Rechamber | `0x4190ee`, ID `0x22` | `0x4190f9` |

The recipient frame builder now derives all four predictable-event parameters
from its exact native snapshot using the semantic resolver. Supplied event
parameters are replaced in a local binding copy; caller memory stays unchanged.
An unsupported event or nonzero parameter for these four events invalidates the
recipient frame, including retries of the same outgoing sequence. The low-level
builder still accepts explicit semantic bindings for its other consumers.

The event test checks all four IDs and zero-only semantics. The native adapter
test resolves a complete reload queue and composes the player fields. The send
test follows a native reload event through owned frame assembly and full/delta
serialization, replaces stale supplied parameters, and rejects unsupported
sound events. These are native fixtures, not proof of live C1 reload behavior.

The full-reference startup probe at
`%TEMP%/sh1x-full-reference-20260908-042328` still fails compilation at
`weaponInheritsPerks` in `_perks.gsc:155`. PID 72392 completed fatal shutdown and
exited; the existing C1 and Python lobby were not changed. The reload trace did
not establish the missing perk-inheritance asset flag, so no substitute GSC
binding was added.

Validation on 2026-09-08: the focused event test passed ASan/UBSan. The Linux
build/full suite passed in `/tmp/sh1x-reload-events-linux.log`; after the final
recipient event-resolution wiring, the production send fixture was rebuilt and
passed separately (`/tmp/sh1x-reload-send.log` contains its compiler output).
The forced Windows build includes that wiring and passed in
`/tmp/sh1x-reload-events-win32.log`. The sequential build command exited zero.
