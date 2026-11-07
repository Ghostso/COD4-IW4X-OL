# weaponInheritsPerks mapping and remaining integration

The previous full-reference script compile stopped at this function in
`maps/mp/perks/_perks.gsc:155`. The native binding now uses the identified asset
flag described below; it does not use the Python weapon-name blacklist.

## Native implementation

`CODOL_BuildNativeWeaponCore` validates +0xbc2 as a serialized boolean and retains
it as `inherits_perks`, outside the assembly-visible IW3 `WeaponDef` layout.
Invalid flag bytes reject construction without changing the existing core.
`CODOL_GetNativeWeaponInheritsPerks` matches the exact native definition pointer
in mounted or retired archive caches, preserving metadata across replacements.
`CODOL_Scr_WeaponInheritsPerks` calls the retained `G_GetWeaponIndexForName`,
returns 1 for resolver index zero, and otherwise reads that definition's metadata.
Missing metadata raises a script error rather than inventing an answer.

The tests cover both valid values, every invalid byte, atomic core failure,
archive replacement with old/new definitions holding different values, and the
VM binding's resolver-zero and metadata-error paths. VM calls are fixtures in
the unit test; they do not establish full vendor-script or client gameplay.

## Validation

The forced Linux build followed by the complete `test-codol` suite passed
(`/tmp/sh1x-inherits-linux-final.log`), then the forced Windows build passed
(`/tmp/sh1x-inherits-win32.log`). The initial Linux test invocation caught a
test-double return-type mismatch; the final run includes that correction and
the archive replacement assertions. Shared libraries were last built for Windows.

The isolated Windows full-reference probe on UDP 17752, home
`%TEMP%/sh1x-inherits-reference-20260908-072914`, loaded `mp_bog_sh` with
alpha0022 `vendor/iw4` and `gsc_overlay`. Compilation advanced past the previous
`weaponInheritsPerks` failure and now stops at **getClassPerk** in
`maps/mp/perks/_perks.gsc:103`. Thus the full script set remains incomplete.
The probe server was stopped after its fatal shutdown; C1/Python lobby were
not stopped or modified. A read-only attempt to inspect C1's live weapon table
returned zero records and supplies no live weapon flag validation.

## CoDOL field identified

Static inspection on 2026-09-08 identified **definition byte +0xbc2** in C1.exe
(SHA-256 `d990610732258b1d00dd6fe63d6691f294312a2e0562955a01ce16216115390d`).
Two independent consumers correspond to the known IW4 query and reload gate:

- C1 routine `0x541a80` obtains script argument zero via `0x5cded0`, resolves
  the weapon through `0x41f7a0` or `0x41f6c0` according to global `0x24b7030`,
  and tests the returned index at `0x541aab`. Index zero returns integer 1 via
  `0x5ce690`. Otherwise `0x541aba` loads the definition from
  `[index*4 + 0x150d720]`, and `0x541ac1` reads byte +0xbc2 and returns it.
  This matches the independently identified IW4 `weaponInheritsPerks` query,
  including its zero-index special case. The CoDOL resolver name itself is
  not present as a plaintext string; this identification is behavioral.
- C1 `0x41ab80` adjusts the per-hand weapon timer step. States 8, 10, 12, 11,
  and 9 enter its reload branch. Player perk bit 30 at +0x4d0 is required,
  then `0x41abc7` requires definition byte +0xbc2. `0x41abd6` resolves perk
  parameter 1 via `0x402f20`; the value in the player's +0x4e0 array scales
  the input step. IW4 `0x576b40` tests the same five states and checks its
  known inheritance byte +0x65a at `0x576b7d` before applying reload scaling.
  CoDOL scales the timer step, so its multiplier must not simply be copied
  into the IW3 reload-duration field.

A linear disassembly of C1's `.text` section found these two +0xbc2 consumers.
This is not an exhaustive claim about virtualized sections. By contrast,
+0xbc7 selects timing variants together with equipped-record byte +2, and
+0xbc6 combines equipped-record hand bytes +3/+4 with rechamber time +0x5b4.
Neither should be used in place of +0xbc2.

Native metadata and query integration are implemented above. Verification of
real mounted weapon records and the full vendor-script compile remains required.
Native perk timer behavior remains a separate integration requirement.

## Earlier investigation

Alpha0022 `gsc/gscbuiltins.py:2152-2169` documents that the engine truth is a
weapon-definition flag. Its Python implementation instead returns false for a
list of killstreak weapon names and names containing `killstreak`. That is an
approximation and is insufficient to identify the serialized CoDOL field.

Static local IW4 evidence (`D:/CoD/shx/iw4x.exe`): the registered function at
0x5f2800 resolves its weapon string, returns true for weapon index zero, and
otherwise reads the definition byte at +0x65a. Another consumer at 0x576b7d
checks this byte alongside player perk state before applying a reload-time
multiplier. Thus the flag also affects native gameplay, beyond the GSC query.

C1.exe has no case-insensitive `inheritsPerks`/`weaponInheritsPerks` string,
nor the searched IW4 `perk_weapReloadMultiplier` name. This does not establish
that the field is absent: the corresponding CoDOL definition offset and native
consumer were initially unidentified (resolved above). Neither IW4 offset +0x65a nor the Python name
blacklist should be treated as an established CoDOL asset mapping.

The next evidence sought at that stage was to trace the CoDOL reload/perk modifier path or recover a
matching CoDOL server/asset layout that names this flag, then compare original
weapon records. The script-loading blocker remains open.

A subsequent reload trace distinguished another flag rather than resolving
inheritance: C1 +0xbd7 is the no-partial-reload restriction consumed at
0x41a17d, alongside the transfer cap at +0x764. It now maps to the retained
native reload field (see `CODOL_WEAPON_PARTIAL_RELOAD.md`). It must not be
used as the inheritance flag. The main reload setup at 0x4192f0 also uses
+0xbc7 to choose alternate reload timing/animation branches; that observation
alone does not establish perk inheritance either.

Revalidated with the current executable on 2026-09-08 at
`%TEMP%/sh1x-full-reference-20260908-042328`: the full-reference compile still
stops at this function. Further reload disassembly confirmed parameterless
reload/rechamber events, now supported by the snapshot resolver, but did not
identify inheritance. See [reload event parameters](CODOL_RELOAD_EVENT_PARAMETERS.md).
