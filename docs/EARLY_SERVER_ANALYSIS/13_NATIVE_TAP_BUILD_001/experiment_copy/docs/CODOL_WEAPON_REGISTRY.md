# Client weapon ammo registration and native snapshot bindings

`codol_weapon_registry.c` replays the C1 ammo and magazine pools in explicit
weapon registration order. It owns all names and rejects gaps, duplicate weapon
names, invalid flags, unresolved custom bases and pool overflow without changing
the registry. Callers register implicit `none` and `defaultweapon_mp` first,
then follow the client's weapon order, including alternate definitions registered
as side effects. Serialized asset runtime indices are never imported.

The reference is alpha0022 `docs/ammo_index_dedup.md`, which documents C1
`BG_RegisterWeaponDef` at 0x41f640, ammo assignment at 0x41f200 and magazine
assignment at 0x41f3f0. Its final registration analysis supersedes the earlier
candidate-key guesses in `weapon_loadout.py`.

The local C1 disassembly was rechecked: +0xbbc gates the ammo-name scan at
0x41f20a; the '*' branch starts at 0x41f27e and reads base+0x568 at 0x41f2b0.
Magazine assignment checks +0x560 at 0x41f3f8, gates its name scan at 0x41f40d,
and stores newly appended keys at 0x41f48f. Those paths agree with the replay.

- Source +0xbbc permits case-sensitive name reuse in each pool.
- For reserve ammo, name reuse takes precedence; otherwise a custom definition
  inherits its resolved base's ammo key. Stock definitions append.
- Source +0x560 suppresses a magazine and produces key -1. Otherwise magazines
  reuse names only when permitted, or append. Custom weapons do not automatically
  inherit the base's magazine key.

`CODOL_RegisterMountedWeaponKeys` obtains stock facts from the existing mounted
weapon/name loaders. Custom definitions use the same registry with their resolved
base and names. `CODOL_BuildEngineAmmoBindings` joins those client keys to owned
native weapons and their registered `WeaponDef.iAmmoIndex/iClipIndex` values.
It produces fifteen slots, deduplicates common wire pools, rejects contradictory
native aliases, and explicitly clears unused slots. The existing ammo adapter
then reads native counts, including zeroing the secondary magazine hand.

The fixture includes the 54 stock records from alpha0022's live-harvested
`weapon_ammo_table.json`. All 108 ammo/magazine keys match. It also covers custom
append versus reuse, name-search precedence, no-magazine pool accounting,
native count lookup, conflicting aliases and inventory removal. Mounted-loader
tests cover dependency failure, name mismatch and serialized flags. The dedicated
registry/native-binding fixture passes AddressSanitizer and UndefinedBehaviorSanitizer.

This provides the ammo inputs needed by the recipient frame builder. The server
now owns the registry and initializes weapon configstrings from the mounted MP
attachment table (see `CODOL_SERVER_WEAPON_CONFIGSTRINGS.md`). It still needs to
call the ammo binding builder during snapshot construction. Name-based association
with loaded native definitions now runs during gamestate/snapshot preparation
(see `CODOL_NATIVE_WEAPON_MAPPING.md`).
Neither this registry nor the measured stock fixture proves arbitrary custom
weapon construction, complete gameplay weapon support or client match entry.

Validation passed a forced Linux build and the full `test-codol` suite
(`/tmp/sh1x-weapon-registry-linux.log`), plus a forced Windows cross-build of
`bin/codol_dedrun.exe` (`/tmp/sh1x-weapon-registry-win32.log`). Both exited zero.
The dedicated sanitizer fixture was rerun after its final additions and passed
with `UBSAN_OPTIONS=halt_on_error=1`. Shared libraries were last built for Windows.
