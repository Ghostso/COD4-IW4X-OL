# Owned native frame assembly

`CODOL_BuildNativeFrame` now combines the existing native collectors into one
owned semantic snapshot. It consumes the exact entity/client ring spans from a
retained `clientSnapshot_t`, composes its player state with the sequence-matched
HUD capture, and copies explicitly supplied actor and animation-command records.
Accessors expose the snapshot state, array updates and commands for the existing
serializer. No retained ring, HUD object or caller-owned actor/command memory
backs the resulting frame.

The caller must supply complete player and array seeds, explicit weapon/ammo/
event bindings, a type-specific entity resolver, and a client metadata resolver.
The new `CODOL_CollectServerClientsResolved` preserves that client's supplied
metadata while applying shared native team/model/attachment/vehicle fields.
Nonempty client spans cannot silently substitute zero metadata. The older client
collector remains a shared-fields-only convenience and is not used here.

The recipient entry point, `CODOL_BuildClientNativeFrame`, now replaces the
caller's ammo bindings with `CODOL_BuildServerAmmoBindings` results. It refreshes
native/client weapon mappings, reads the registered native definitions, and
resolves all fifteen ammo slots from this snapshot's `ps.weapons` inventory.
Native runtime ammo/clip indices select the counts; replayed client pool keys
select their wire identities. Dropped slots are explicitly cleared. Other
player bindings remain caller-owned, and the low-level builder retains its
explicit-binding API. Failed ammo resolution invalidates the recipient frame,
including a retry using the same outgoing sequence, without changing the
caller's bindings or event clocks.

The focused server-weapon test uses different native indices and client pool
keys, checks the resulting magazine/reserve counts, rejects an owned but unloaded
weapon atomically, and clears a dropped inventory. The live-writer fixture checks
that the entry point uses resolved ammo masks and invalidates a frame when its
ammo service fails. Its ammo service is controlled; the separate server-weapon
test exercises the production resolver.

This integration passed the focused ASan/UBSan server-ammo test and the full
Linux build/suite (`/tmp/sh1x-server-ammo-linux.log`), followed by the forced
Windows build (`/tmp/sh1x-server-ammo-win32.log`) on 2026-09-08. The sequential
build command exited zero. At that validation point there was no gameplay
caller; the subsequent initial caller is described in `CODOL_GAMEPLAY_FRAME.md`.

Both the frame and event clocks are transactional. The builder stages player and
entity clocks, then resolves every section. Only complete success replaces the
prior owned frame and commits both clock stores. Missing HUD capture, unresolved
client/entity fields, stale rings, invalid records or allocation failures retain
the old frame and clocks. Resolvers must remain read-only; their external side
effects cannot be rolled back by this API. Clock lifecycle remains the caller's
responsibility and separate from recipient ACK history.

The integration fixture uses the production player, entity and client collectors,
HUD capture and asset resolver. It checks successful composition, preservation
of supplied client metadata, ownership after actor/command source changes, and
failure in client conversion after entity events have advanced in staging.
Subsequent success advances both clock stores together. ASan and UBSan pass with
`UBSAN_OPTIONS=halt_on_error=1`.

Validation also passed forced Windows cross-compilation of
`bin/codol_dedrun.exe`, followed by a forced Linux build and the complete
`test-codol` suite. The builds ran sequentially because they share static
library outputs.

That sanitizer run found engine-header packing leaking into semantic CoDOL
types: an embedded HUD could become misaligned, and array-member layout could
depend on include order. The affected snapshot/type headers now scope their
normal alignment with balanced packing directives and restore the caller's
packing afterward. Compile-time checks cover HUD alignment, stats offset and
netfield descriptor size after including the packed engine headers. This changes
in-memory consistency, not the field-by-field wire encoding.

The assembled frame still requires serializer reachability checks and successful
transport acceptance before entering ACK history. The live writer now consumes
recipient-owned, sequence-matched frames (see `CODOL_LIVE_SNAPSHOT_WRITER.md`).
The initial live caller and baseline bindings are now implemented in
`CODOL_BuildGameplayFrame`; see [gameplay frame producer](CODOL_GAMEPLAY_FRAME.md)
for supported states and incomplete fields/modes. Actor/animation-command
integration and complete state parity remain open. This is not proof of client
match entry, and it does not clear `weaponInheritsPerks`.
