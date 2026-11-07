# Native weapon lock state

`WeaponLockFinalize` remains a missing vendor-script method. The Python
`gsc/builtin_surface.py` implementations store object markers and do not
establish native weapon-lock semantics. No placeholder binding was added.

Offline disassembly of `D:/CoD/shx/iw4x.exe` establishes:

| Method | Address | Behavior |
| --- | --- | --- |
| weaponlockstart | 0x5dd3e0 | Select entity or vector target, set bit 1, clear bits 2/4/8 |
| weaponlockfinalize | 0x5dd500 | Select target, set bits 1/2, set optional missile offset, OR bit 4 for true third argument or bit 8 otherwise |
| weaponlockfree | 0x5dd670 | Clear bits 1/2/4/8 and set entity target to 2047 |
| weaponlocktargettooclose | 0x5dd710 | Set/clear bit 0x10 |
| weaponlocknoclearance | 0x5dd790 | Set/clear bit 0x20 |

IW4 stores flags at player state +0x404, entity at +0x408, position at +0x40c,
and the server missile offset at gclient +0x3654. Position targeting sets bit
0x40 and preserves the stored entity; entity targeting clears bit 0x40 and
preserves the stored position. Start and free preserve warnings and free also
preserves the target-mode bit. Finalize ORs its fire-mode bit rather than
clearing the opposite mode. These details are preserved in the native
`codol_weapon_lock.c` state transitions outside the retained IW3 ABI.

C1 `0x41b9b5` tests player state +0x48c bit 2 before allowing a lock-required
weapon to fire; absent lock emits event 0x70. At `0x41b9fb` it reads the same
field and tests bits 2/0x10 for event 0x6e and bit 0x20 for event 0x6f. Thus
the client flag field and these three flag meanings are directly confirmed.
The existing CoDOL wire table represents +0x48c with seven bits. Further C1
disassembly found its own finalize implementation: entity target writes
+0x490 at 0x519b6d, vector target writes +0x494 at 0x519c1f, and missile
offset writes gclient +0x3a44 at 0x519bf5. Its mode and warning behavior
matches the IW4 transitions above. `CODOL_OverlayWeaponLock` now maps the five
confirmed player-state fields into the semantic snapshot state, preserving
unrelated fields and excluding the server missile offset. The focused test
also verifies this mapping and atomic rejection of out-of-range flags.

The focused 32-bit ASan/UBSan test covers entity/position transitions, repeated
finalization, warning preservation, offset reset, and atomic rejection of
invalid entity numbers or nonfinite vectors. Windows build passed with the
native state module (`/tmp/sh1x-weapon-lock-state-win32.log`).

## Live state and snapshot integration

`codol_weapon_lock_clients.c` owns thirty-two independent native states,
initialized with entity target 2047. `CODOL_ResetClientInput` clears the selected
slot on the existing bot/connect/disconnect paths, and `CODOL_ResetGameInput`
clears every slot on map initialization. The focused lifecycle test invokes
these production reset functions and verifies that other clients remain intact
until the map reset.

`CODOL_BuildGameplayFrame` seeds its player fields from the state selected by
`source->ps.clientNum`, before retained IW3 overlays. The production frame test
now verifies flags/target survival through the full builder and that recipient 1
following player 0 receives player 0's target rather than its own. The existing
snapshot serialization check then runs with those fields populated. Both the
lifecycle test and production frame test passed with 32-bit ASan/UBSan; Windows
build passed (`/tmp/sh1x-weapon-lock-clients-win32.log`). This is controlled
engine-state validation, not a live script or C1 missile demonstration.

The retained `Weapon_RocketLauncher_Fire` already forwards target and offset
arguments to `G_FireRocket`; that function stores an `EntHandle`, target offset,
and missile flight state. This provides a source integration point without
changing the IW3 ABI. Still required before registering the methods: GSC input
validation, respawn behavior, server firing gates, and consuming the selected
lock/offset/mode in native missile launch and guidance. Full vendor-script
loading and real C1 match entry remain incomplete.

## Entity-target missile consumption

The CoDOL build of retained `G_FireRocket` now calls
`CODOL_ApplyRocketWeaponLock` after default stage/flight initialization and before
linking or `missile_fire` notification. A finalized entity lock with an active
native target copies the server missile offset, selects top/direct flight mode,
and assigns the target through the existing `EntHandle::setEnt` bookkeeping.
Unlocked states, invalid/inactive targets, non-player owners, and position-only
locks leave the missile unchanged. Position-only guidance is still missing and
must not accidentally reuse the stale stored entity target.

This uncovered a retained C header mismatch: `missile_ent_t` contained a
nonexistent inline `targetEntNum`. The assembly stores the target in the outer
handle at +0x214 and uses +0x1dc for offset, +0x1e8 for stage, and +0x1ec for
flight mode. Removing that inline member makes the C fields match those
instructions. Compile-time assertions in `test_codol_weapon_lock_missile.c`
verify all four offsets. The focused test passed with 32-bit ASan/UBSan and
covers entity offset/mode consumption plus unchanged output for inactive and
position targets. It does not prove in-client guidance or script execution.
The production frame regression also passed with the corrected header, and a
full forced Windows rebuild passed (`/tmp/sh1x-weapon-lock-missile-win32.log`).

Position guidance, firing gates, respawn reset, and the GSC method bindings
remain outstanding. No new method has been advertised as implemented yet.

## Respawn and lock-required firing gate

`ClientSpawn` now resets the independent weapon-lock slot immediately after
clearing `gclient_s`. The existing connect/disconnect/map reset behavior remains
in place; a finalized target cannot survive a new life through the side storage.

The native weapon converter now copies the validated byte at C1 WeaponDef
+0xbbe into `requireLockonToFire`. C1 tests this byte at 0x41b9ad and requires
player lock bit 2 at 0x41b9b5, emitting event 0x70 if absent. The retained
`PM_Weapon_1310` now checks the corresponding native state after weapon delay
expires and before ammunition consumption; denial emits the retained
`EV_LOCKON_REQUIRED_HINT`, which the existing event mapping converts to 0x70.
The call resumes normal firing only with a finalized lock, or for a weapon
without this requirement. It is a compiled source call, not a runtime hook.

The focused conversion-to-gate test verifies no lock, started lock, finalized
lock, freed lock, optional lock, and atomic rejection of malformed source flag
values. It and the native weapon conversion regression passed with 32-bit
ASan/UBSan. Windows builds passed for both respawn and firing integration
(`/tmp/sh1x-weapon-lock-respawn-win32.log`,
`/tmp/sh1x-weapon-lock-fire-win32.log`). No live respawn or shot was claimed
from these controlled tests.

Remaining work in this family: position guidance, the separate C1 +0xbbd
warning gate for target proximity/clearance, and GSC bindings with validated
arguments. Full script startup and real C1 match entry remain unverified.

## Proximity and clearance firing checks

The native core now retains C1 WeaponDef +0xbbd as `lock_warning_gate`, without
guessing an equivalent IW3 weapon category. Its lookup uses the exact native
definition pointer across active and retired archive generations, so an old
registered definition retains its own flag after an archive replacement.
Malformed non-boolean bytes reject core conversion atomically.

The existing native firing check now follows C1 0x41b9ad..0x41ba76 in order:

1. A required but unfinished lock emits `EV_LOCKON_REQUIRED_HINT` (wire 0x70).
2. With the warning gate enabled, both finalized-lock bit 2 and proximity bit
   0x10 emit `EV_TARGET_TOO_CLOSE_HINT` (wire 0x6e).
3. Otherwise, enabled clearance bit 0x20 emits
   `EV_TARGET_NOT_ENOUGH_CLEARANCE` (wire 0x6f), even without a finalized lock.
4. A disabled warning gate ignores both warnings.

The production call remains before ammunition consumption. Focused sanitizer
tests cover this precedence, flag conversion, and atomic malformed input.
The Windows archive-registry regression checks the warning flag before and
after replacement, including the retained old definition. It passed, as did
the full forced Windows build (`/tmp/sh1x-weapon-lock-warnings-win32.log`).

Position-target guidance and GSC argument/binding integration are still missing.
These checks are not evidence of a real client entering a match.

## Position-target launch and retained guidance

C1 launch code 0x57498d..0x574a23 distinguishes position locks from entity
locks. With bit 0x40 it passes a null target entity and copies player-state
+0x494..0x49c as an absolute target; only the entity branch copies gclient
+0x3a44 missile offset. Both branches select direct mode from bit 4.

The native launch path now records this absolute target independently per
missile, clears the entity handle through existing bookkeeping, and zeroes the
entity-relative offset. Retained `MissileTrajectory` accepts this target without
an entity handle and reads its coordinates in both guidance branches. Existing
steering/stage calculations remain in the retained source. The launched target
does not change when the player's lock changes or resets.

`G_InitGentity`'s existing generation reset also clears position metadata, and
map generation reset clears every slot. Every rocket launch additionally clears
its reused slot before choosing a target. Tests cover absolute coordinates,
ignored missile offset, independent lifetime, and resets. The missile ownership
test and production frame regression passed with 32-bit ASan/UBSan; Windows
build passed (`/tmp/sh1x-missile-position-win32.log`). Guidance branches have
compiled, but actual in-flight position guidance still needs runtime validation.
GSC bindings and real C1 match entry remain incomplete.

## Native GSC bindings

The registry now binds `weaponlockstart`, `weaponlockfinalize`, `weaponlockfree`,
`weaponlocktargettooclose`, and `weaponlocknoclearance` to native state operations.
Entity/vector arguments are validated through the retained VM. Finalize reads
its optional offset and direct-fire argument before committing state; VM errors
leave the prior lock intact. The adapter uses the retained VM's `VAR_ENTITY`
value rather than copying C1's different internal type number.

The focused adapter test passed with 32-bit ASan/UBSan, covering both target
forms, default offset, warning/free behavior, wrong receivers, and getter errors.
Windows build passed (`/tmp/sh1x-weapon-lock-gsc-win32.log`). The full vendor
script retry no longer reports `WeaponLockFinalize`; its next compile failure
is `SortByDistance` in `maps/mp/_stinger.gsc:304`. The isolated probe's log is
`obj/lock-gsc-vendor.log`. These results establish registry resolution and
controlled adapter behavior, not a successful live missile or match entry.

The regenerated inventory has 479 matching names and 828 missing names. As
before, name coverage is not a semantic-completeness score. Full script startup,
in-flight guidance validation, and real C1 match entry remain outstanding.
