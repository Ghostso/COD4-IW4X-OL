# Primary fire event parameters

Native `EV_FIRE_WEAPON` and `EV_FIRE_WEAPON_LASTSHOT` now resolve parameter zero
for CoDOL events 30 and 31. Their ID mappings were already present; the missing
parameter resolution rejected otherwise valid native firing queues.

Retained `_bg_weapons.asm` sends native events `0x1a` and `0x1b` through
`PM_AddEvent`, whose `_bg_pmove.asm` implementation supplies zero. C1's firing
producer at `0x41b8b0` selects its SV firing family and writes a zero parameter
at `0x41b908`. It chooses primary/secondary hand and ordinary/last-shot variants
through the event ID.

Alpha0022's `docs/parity_roadmap.md` section 4.6.2 records that ordinary events
30–31 and SV events 43–46 share the `CG_FireWeapon` consumer at `0x481f50`.
Its hand and last-shot tables distinguish the variants. This change preserves
the existing ordinary ID mappings. Hit-client variants have separate hit-entity
parameter semantics and are not covered by this zero-parameter rule.

The recipient frame entry point already resolves native predictable-event
parameters. It can now compose these firing events without caller-supplied
parameters. Nonzero values are rejected without modifying the output queue.

The parameter fixture checks IDs, zero acceptance, nonzero rejection and mixed
queues. The production send fixture emits primary fire in a full snapshot, then
last-shot fire in the acknowledged delta, verifying the owned field values and
the actual send/history path. Its world and transport are controlled fixtures;
this does not establish connected-client weapon FX, hit registration, or match
entry. The unresolved GSC and complete-frame input work remain open.

Validation on 2026-09-08: the focused parameter test passed ASan/UBSan;
the Linux build/full suite passed (`/tmp/sh1x-fire-events-linux.log`), followed
by the forced Windows build (`/tmp/sh1x-fire-events-win32.log`). The sequential
command exited zero. Static analysis and isolated tests did not alter C1 or the
Python lobby process.
