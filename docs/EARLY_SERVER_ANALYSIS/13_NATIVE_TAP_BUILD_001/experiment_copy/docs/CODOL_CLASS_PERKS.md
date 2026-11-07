# Class perks from uploaded player data

The previous full vendor/overlay script probe stopped at `getClassPerk` in
`maps/mp/perks/_perks.gsc:103`. This is an alpha0022 overlay helper, not a verified
IW4/T5 resolver entry. Its Python implementation (`gsc/gscbuiltins.py:940`)
calls `perks_support.profile_perk_names`, which reads a profile file through
`weapon_loadout.loadout_from_profile`. That path can select the newest per-UID
file rather than the calling player's profile. Native multiplayer must select
the current script player's completed stats upload instead.

## Implemented native data access

`CODOL_ClientClassPerkItem(client, class_index, slot, out)` reads only the named
client's complete, native-owned 32768-byte stats blob. The layout follows
alpha0022 `mpdata_tool.py` and `weapon_loadout.py`:

- Version at +4 must be 220; format checksum at +8 must be 0xe4fd5218.
- Eight class records start at +0x1511, with packed stride 92 bytes.
- Perk item IDs are signed little-endian 16-bit words 7 through 11.
- The API takes zero-based classes and one-based slots 1 through 5; it preserves
  -1 and 0 rather than inventing a perk for an empty slot.
- Missing/incomplete stats, wrong schema, invalid client/class/slot and a null
  output reject without changing output. Resetting a client removes access.

This API does not validate the stored profile CRC or implement other playerdata
schemas. It does not make the raw stats-upload transport dependent on this schema.
The focused tests cover all 40 fields, negative values, separate client uploads,
reset/incomplete state and failure preservation. Linux ASan/UBSan passed.
The same focused test passed as a Windows executable, and the Windows server
rebuilt successfully (`/tmp/sh1x-class-perks-win32.log`). Shared static libraries
remain Windows builds; the Linux focused test does not rebuild those libraries.

## GSC integration

The global overlay call has no explicit player argument, so the binding obtains
the current script `self`. The retained VM exports `gFs`, a 20-byte
`function_stack_t` with current `localId` at +4. Its builtin dispatch at
`VM_ExecuteInternal_1020` saves the instruction and stack top, then calls the
native binding. `Scr_GetSelf(localId)` provides the owning script object; its
entity type, class and player client are checked before reading stats.

Marketplace mapping is also data-backed: alpha0022
`marketplace_catalogue.py:build` reads `mp/comarketplaceitems.csv` column 0 as
the item ID, column 2 as category, and column 1 as name. Perks use category
`per`; the Python table strips the `per/` prefix to produce `specialty_*` names.
The native binding queries the mounted table through
`CODOL_LoadEngineStringTable`, preserving patch precedence. Missing tables or
items, duplicate matching rows, and non-perk items are script errors. Empty
profile slots return the empty string. It does not load Python JSON.

The binding is registered in the CoDOL function table. Its focused Linux
ASan/UBSan test passed with actual native stats uploads and mocked VM/table
accessors, including two clients holding different perks and invalid contexts.
The Windows build passed (`/tmp/sh1x-class-binding-win32.log`).

The isolated native VM probe on UDP 17753, home
`%TEMP%/sh1x-class-vm-final-20260908-074003`, logged
`SH1X_CLASS_PERK_VM_PASS` from the real player-connect script thread. The
synthetic peer uploaded a CRC-correct v220 profile with item 3002 in class 1
slot 1. Mounted marketplace lookup returned `specialty_fastreload`; class 0
and other empty slots returned empty strings. The callback uses ordinary
assignments and `print`, so evaluation is not removed with developer-only
assertions. An earlier fixture used developer-only assertions/println and
produced no marker; that run is not counted as VM validation.

Use `tests/fixtures/codol_class_vm` as `codol_scriptOverlay` over the existing
node VM fixture and pass `--class-perk-fixture` to the encrypted transport
probe. Its two-second callback delay is for the synthetic immediate upload,
not production readiness logic. The probe also completed checksum validation,
CS_ACTIVE, and independently decoded baseline/delta snapshots.

The full vendor/overlay compile probe on UDP 17754, home
`%TEMP%/sh1x-class-reference-20260908-073757`, advanced to missing
`getClassIndex` at `_perks.gsc:82`. Both isolated servers were stopped; the
existing C1/Python lobby were preserved. Full vendor scripts, native perk
effects, and real C1 match entry remain incomplete.

## Class-name parsing

Native `getClassIndex` now mirrors the Python overlay's ASCII class names:
case-insensitive `customN` and `classN`, surrounding ASCII whitespace ignored,
positive decimal N mapped to N-1. Invalid names return -1. It does not clamp
to eight classes; profile access enforces that separate bound. Unlike Python's
unbounded integers, results must fit signed 32-bit GSC integers, so N above
2147483648 returns -1. Unicode numeral/whitespace normalization is not supported.
Leading zeros are accepted without risking arithmetic overflow.

The expanded sanitized test covers normal names, whitespace/case, invalid
suffixes and prefixes, zero, signs, long numbers and the signed-result boundary.
The Windows server rebuild passed (`/tmp/sh1x-class-index-win32.log`).
The real player-thread fixture on UDP 17755, home
`%TEMP%/sh1x-class-index-20260908-074251`, logged `SH1X_CLASS_PERK_VM_PASS`
after resolving ` CUSTOM2 ` to class 1, rejecting `autoassign`, and using the
resolved index to obtain `specialty_fastreload` from the uploaded profile.
Its encrypted baseline/delta snapshot checks also passed.

The full-reference probe on UDP 17756, home
`%TEMP%/sh1x-class-index-reference-20260908-074312`, advanced past the class
helpers. The next failure is syntax in `maps/mp/killstreaks/_killstreaks.gsc:5`:
`KILLSTREAK_STRING_TABLE = "mp/killstreakTable.csv";` at top level. This requires
source-language support, not another missing builtin registration. Both probe
servers were stopped after inspection. Full vendor-script execution remains
unverified.
