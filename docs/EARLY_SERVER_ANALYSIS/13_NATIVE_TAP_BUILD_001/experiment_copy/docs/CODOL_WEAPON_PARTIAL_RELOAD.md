# Weapon partial-reload restriction

The native weapon core now reads CoDOL definition byte +0xbd7 into retained
`WeaponDef.bNoPartialReload`. It is validated as a serialized boolean before
any ammo fields are committed. Zero clears the restriction, and malformed
values leave the complete destination unchanged. This is part of the existing
core loader; it requires no runtime hook or substitute gameplay implementation.

Evidence from local C1.exe:

- `0x41a16d` requires reserve ammo, and `0x41a173` reads clip capacity at +0xb60.
  A full clip fails before testing the flag.
- `0x41a17d` tests +0xbd7. When clear, a partly empty clip may reload.
- When set, `0x41a186` reads the ordinary transfer cap at +0x764. A zero cap,
  or a cap at least as large as the clip, requires an empty clip. A smaller cap
  requires at least that many free rounds of capacity (`0x41a194..0x41a198`).
- The retained `_bg_weapons.asm` `PM_Weapon_CheckForReload_90` follows the same
  decisions with native offsets +0x52c and +0x534. Compiled `offsetof` checks
  identify those as `bNoPartialReload` and `iReloadAmmoAdd` respectively.

The weapon fixture covers both flag values independently of segmented reload,
all invalid byte values, preservation of runtime ammo/clip registration indices,
and propagation through the assembled native weapon core. The retained reload
assembly supplies the gameplay behavior; no new approximation was added.

This does not establish the unrelated `weaponInheritsPerks` asset flag. General
weapon registration and a connected client exercising native reloads remain
required for full match validation.

Validation passed a forced Linux build and full `test-codol` suite
(`/tmp/sh1x-partial-reload-linux.log`), followed by a forced Windows build
of `bin/codol_dedrun.exe` (`/tmp/sh1x-partial-reload-win32.log`). Both exited
successfully. Shared static libraries were last built for Windows.
