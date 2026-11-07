# Native match-startup probe

Latest probe: default-weapon and mantle initialization succeed. With the
configured reference script directories and native syntax adaptation,
codescripts load. [Native PhysicsLaunchClient](CODOL_PHYSICS_LAUNCH_CLIENT.md)
now clears that missing method. [Native offhand controls](CODOL_OFFHAND_CONTROLS.md)
clear `EnableOffhandWeapons`; [native weapon-switch controls](CODOL_WEAPON_SWITCH_CONTROLS.md)
now clear `enableWeaponSwitch`. [Native usability](CODOL_USABILITY.md) clears
`EnableUsability`. [Native HUD font transitions](CODOL_HUD_FONTSCALE.md) clear
`changeFontScaleOverTime`. Compilation next fails on `weaponInheritsPerks`
in `maps/mp/perks/_perks.gsc:155`. Its [asset flag mapping](CODOL_WEAPON_INHERITS_PERKS.md)
is unresolved; the Python name blacklist is not an established field mapping.
Match entry remains unverified. See [native script sources](CODOL_SCRIPT_SOURCES.md).

An isolated minimal-script probe on `mp_bog_sh` now also installs native
collision (658 leaves, 432 dynamic entities, checksum `a228f2cd`) after
[particle-cloud FX conversion](CODOL_FX_CLOUD.md). It then fails at animation
script parsing. [Native movement/condition support](CODOL_PLAYERANIM_STATUS.md)
now passes `idlelaststand`, `akimbo`, `meleehalberd`, `stunned`, and the former
eight-command item limit. Empty animation-delta containers now convert too;
the expanded 1024-record native animation table clears the prior name-scan
crash. [Native model DB lookup](CODOL_MODEL_DATABASE.md) passes
`me_electricbox4`; [native trigger installation](CODOL_TRIGGER_MODELS.md)
also clears `?0`. Native brush physics conversion now clears `com_cellphone_on`.
The subsequent [native path-node store](CODOL_PATH_NODES.md) clears
`G_Spawn: no free entities`: path nodes no longer occupy game-entity slots.
The isolated Bog probe now completes initialization and passes both native VM
node assertion groups (2026-09-08). See also
[physics brush conversion](CODOL_PHYSICS_BRUSH.md).
This probe does not use the full reference gametype and does not demonstrate
match entry. Path-node and vehicle-node VM assertions now execute successfully.

Verified 2026-09-07 using the Windows native server, original CoDOL 1.1.1.13
archives, `g_gametype dm`, and `map mp_killhouse_sh`. The probe used loopback
port 17739 and a separate temporary home directory, then executed `quit`.
The existing lobby service and C1 client were not restarted or modified.

The log establishes this startup sequence:

1. Six native map archives mount for `mp_killhouse_sh`, zone type `mp`.
2. 2,053 inherited configstrings install.
3. Native collision installs for `maps/mp/mp_killhouse_sh.d3dbsp`: 4,689
   leaves, 191/0 dynamic entities, checksum `a26a76c3`. Visibility currently
   uses the documented all-visible policy.
4. Native common world installs with 30 primary lights.
5. Game initialization begins and the native `none` weapon lookup occurs.
6. Initialization fails while loading the default weapon asset:
   `Could not load default asset 'defaultweapon_mp' for asset type 'weapon'.`
7. The server shuts down its game state and exits after `quit`.

This is the first observed failure in this probe. It does not establish script
startup, client spawn, or a playable match. Separate diagnostics successfully
compose the intermediate default weapon core, models, animations, muzzle
flashes and brass effects, but that intermediate record is intentionally not
registered as a complete WeaponDef. The complete provider currently accepts
the validated `none` definition. Completing weapon registration is therefore
required before this probe can test subsequent initialization stages.

The raw diagnostic log is in the isolated home directory
`%TEMP%/codol-match-probe/main/qconsole.log`. No running analysis server remains.

## Registration audit

The retained `BG_GetWeaponIndexForName` installs a mutable definition, assigns
ammo/shared-cap/clip indices, resolves the alternate weapon, and invokes its
registration callback. `G_RegisterWeapon` in `_g_items.asm` consumes the two
hint strings (+7dc/+7e0), sixteen world-model slots (+2bc), and projectile
model (+584). These dependencies have native conversion paths. This audit
does not establish that the remaining gameplay fields are complete.

Static inspection of C1 1.1.1.13 identifies function 0x535c10 through its error
string at 0xc55b80: `unknown weapon '%s' in GetWeaponScriptMods`. Its successful
path loads the registered definition from 0x150d720, reads +a24 at 0x535c88,
and passes that string to Scr_AddString at 0x5ce8a0. Consequently +a24 must
not be guessed to be IW3's `szScript`. The native intermediate record now
retains this string as `script_mods`, with archive-backed lifetime and empty
normalization. Missing, duplicate, or mistyped dependency records reject
conversion before replacing the previous core. A CoDOL script builtin still
needs to consume this extension; preserving it alone does not implement that
builtin or unblock complete default-weapon registration.

Validation for this extension: the native weapon and mounted-loader fixtures
pass under 32-bit AddressSanitizer/UndefinedBehaviorSanitizer; the full Linux
server build and `test-codol` suite pass; the full Windows native server build
passes. No new match-entry success is claimed from these checks.

## Archive-owned default provider and follow-up probe

The database now asks the mounted default-weapon provider to compose
`defaultweapon_mp` through `CODOL_LoadEngineWeaponCore`. The provider owns the
result in its defining archive, reuses it on repeated lookup, and retains the
old definition when archives are retired. Failed construction is freed and
can be retried. General weapon names still require further implementation.
Unconverted gameplay fields remain zero: this is a startup integration step,
not a claim of complete weapon behavior.

The follow-up Windows probe used the same original archives, map and isolated
loopback port as above, with home `%TEMP%/codol-default-provider-probe`.
The log now shows successful native lookups of `none` and `defaultweapon_mp`
(twice), followed by:

```
ERROR: CoDOL animation mp_mantle_up_57 has unsupported or invalid data
```

The process exited after game shutdown and `quit`; no analysis server remains.
The existing lobby and C1 were untouched. This supersedes the earlier
first-failure result. It does not establish script startup or client spawn.
The animation converter explicitly rejects delta tracks; the failing asset
must be inspected to determine whether that restriction caused this failure.

Validation: the Windows native server build passed and supplied the live
probe above. A forced Linux build and full `test-codol` suite passed. The
asset-registry fixture also passed with 32-bit AddressSanitizer and
UndefinedBehaviorSanitizer, including failed-build cleanup/retry, case-folded
cache lookup, replacement, and continued access to the retired definition.

## Native mantle root motion

The native animation converter now owns translation and two-component rotation
tracks, including constant and animated payloads, small/wide translation
frames, and byte/ushort frame indices. It rewrites all pointers and validates
source spans, counts, finite translation bounds, and ordered endpoint indices.
Four-component rotation remains unsupported rather than being dropped.

The retained `XAnim_CalcDeltaForTime` consumes translation indices at +32 and
rotation indices at +8, matching the converted layouts. A fixture runs this
actual evaluator at start/midpoint/end for both index and translation widths
and checks the resulting motion. The ownership fixture covers copied payloads,
constant tracks, malformed data, and failed replacement under sanitizers.

C1 mantle function 0x4098d0 calls its absolute-delta evaluator at 0x63ac30.
That function evaluates a leaf without IW3's `XAnimParts +0x11` flag gate.
Retained `XAnimGetAbsDelta` requires this flag; the converter therefore sets
native `bDelta` from the presence of converted delta data. Source byte 29
must not be copied as this flag. Before this correction the real mantle
validation observed zero forward motion; afterwards it passed.

Mantle slot 10 also now names `mp_mantle_over_low` in `_bg_mantle.asm`, matching
C1's roster and alpha0022's `docs/mantle_mount.md`, instead of the retained
`player_mantle_over_low` name absent from the CoDOL archives.

The final Windows probe used `%TEMP%/codol-mantle-delta-final`, the same
isolated loopback port and `mp_killhouse_sh`. It passed weapon and mantle
initialization and stopped at:

```
Error: Could not load rawfile "codescripts/delete.gsc".
ERROR: Could not find script 'codescripts/delete'
```

The diagnostic server exited after shutdown and `quit`. This establishes
progress into script loading, not successful script initialization or spawn.
The existing lobby service and C1 were not changed.

Validation for the final delta conversion and mantle-name change: Windows
native build and live probe passed through mantle initialization; forced
Linux build and full `test-codol` suite passed; the native animation ownership
fixture passed 32-bit ASan/UBSan. The retained evaluator fixture checks actual
root-motion samples, in addition to the startup validation using real assets.
