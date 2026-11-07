# Explosion FX publication audit - 2026-09-14

## Confirmed missing producer

`src/asmsource/_g_missile.asm`, `G_ExplodeMissile`, allocates an ET_GENERAL
explosion entity and copies the missile weapon into native entityState.weapon
(+0xc4). It queues EV_GRENADE_EXPLODE / EV_FLASHBANG_EXPLODE /
EV_CUSTOM_EXPLODE with DirToByte(normal), broadcasts, links, and frees it after
its event. The original missile is freed independently.

The snapshot seed accepted this ET_GENERAL through the model overlay, but neither
that overlay nor the generic entity overlay wrote the C1 weapon selector +0xd4.
Only missile/player/item/turret/vehicle paths published weapon selectors. Thus the
explosion lost its weapon identity while keeping its correctly mapped event.

## Original C1 evidence

Examined installed C1.exe offline at `D:/CoD/CODOL Builds/Call of Duty Online 1.1.1.13/C1.exe`.
Addresses are image VAs (base 0x400000).

- 0x52edc4 calls entity allocation; 0x52edd1 writes ET_GENERAL (0).
- 0x52eddd reads missile word +0xd4; 0x52ede4 copies it into explosion +0xd4.
- 0x52edeb / 0x52edf7 copy the weapon model byte +0xe6 independently.
- 0x52eed4 reads WeaponDef +0x7b4 (projectile explosion kind).
- 0x52eefe selects event78 (flashbang), 0x52ef0d event79 (custom), and
  0x52ef28 event73 (grenade). Each passes DirToByte result to G_AddEvent 0x572d30.
- 0x52eec0..0x52eeca also publish traced surface type into explosion +0x90.

A directly readable C1 persistent-smoke FX consumer exists at 0x44ffd3..0x4500ed.
Its entity cursor is state+0x7c: it checks flag0x40 at cursor-0x74 (state+8),
reads times at cursor and cursor-0x24 (state+0x7c/+0x58), reads the most recent
normal parameter, then 0x4500a8 reads word[cursor+0x58] = state+0xd4.
0x4500ac selects WeaponDef through 0x150d720, 0x4500b3 reads its +0x7b8 FX,
and 0x4500d1 calls FX playback 0x4fe430. This confirms the weapon field's FX
selection role without guessing a configstring FX ID.

The transient grenade/flash/custom client dispatcher body remains unresolved;
no claim that the smoke consumer is that transient dispatcher. Original C1's
explicit explosion weapon copy independently proves the missing publication.

## Source change

`src/codol/snapshot/codol_sv_gameframe.c` now recognizes the seven mapped
explosion event families and publishes the captured source.weapon through the
native-to-C1 weapon registry into +0xd4. Applies to queued general-entity events
and event-typed temporary entities. The source identity belongs to the captured
snapshot/archive, so no mutable live entity or freed missile is consulted.
Unknown registry mappings reject with a specific seed failure; the null weapon
remains representable exactly as registry zero. Non-explosion entities and
normal-byte event parameters retain their prior behavior.

Existing event mappings: grenade73, rocket76, rocket-no-marks77, flash78,
custom79, custom-no-marks80, dud82. They were already present and are unchanged.
C1 field tables include +0xd4 for the general/event wire types.

## Scope and validation

Source inspection only; no tests, builds, restarts, UI input, or process writes.
Parent reviews/builds. Live confirmation of grenade/stun visual effects remains
pending. Smoke lifetime flags/times remain separate concerns;
this change does not claim those paths complete. No replacement assets or fake FX.

## Captured surface/model and sound follow-up

The same explosion overlay now publishes native surfType (+0x84) into C1 +0x90,
and native weaponModel (+0xc8) into the byte at C1 +0xe6. The latter updates
bits16..23 of the +0xe4 network word while preserving its other bytes. Weapon
identity likewise updates only the low word at +0xd4. Original C1 copy sites
are listed above. Retained G_ExplodeMissile writes surface from
(trace.surfaceFlags >> 20) & 31, matching the original C1 producer. Inputs
outside surface0..31 or native archived weaponModel0..15 reject explicitly;
negative values are rejected as well. Native msg.c archives surfType with8bits
and weaponModel with4bits. All three fields derive from the captured entity.

OpenBLOPS Game/Client/cgame/cg_event.cpp grenade handler around1078 and flash
handler around1143 use the selected WeaponDef for both projExplosionEffect and
projExplosionSound. The grenade branch also resolves material impact FX/audio
using surfType. C1 WeaponDef +0x7c0 explosion-sound names are already measured
and loaded by codol_weapon_native.c / codol_sound_native.c. Consequently the
missing weapon selector plausibly explains the missing sound as well as FX;
the precise protected transient C1 consumer remains unverified. No extra sound
events, guessed aliases, or duplicate playback were added. Surface publication
restores original material identity rather than selecting a fabricated effect.

Updated source remains unbuilt by this worker; parent review/build and real C1
explosion/stun playback verification remain outstanding.
