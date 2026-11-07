# Mounted stock weapons in the native database

The mounted weapon cache now accepts stock weapon names through
`CODOL_LoadMountedNativeWeapon`, using the existing native core converter.
`none` retains its stricter dedicated converter. The default-only API remains
available as a wrapper.

Each archive owns a linked cache keyed by the winning definition's identity.
Repeated and case-insensitive lookups reuse the same native definition. A failed
conversion frees its temporary core and leaves the output and cache unchanged;
replacing archives keeps previously published definitions alive until unmount.
The asset test covers these properties for both `defaultweapon_mp` and `m4_mp`.

Both database lookup and `DB_IsXAssetDefault` now recognize converted mounted
weapons. The retained `BG_GetWeaponIndexForName` calls both: a successful lookup
alone was followed by a hash-table miss in the default check, returning weapon
index zero and causing native GSC `precacheItem("m4_mp")` to report an unknown
item. Successfully converted weapons now use the configured default-name check;
missing or rejected conversions retain the existing database fallback.

This does not establish complete weapon behavior. The native core converter's
unsupported dependencies, custom weapon construction, live player-state inputs,
and remaining GSC implementations still need work.

Validation on 2026-09-08: Linux build and full `test-codol` suite passed
(`/tmp/sh1x-stock-weapon-final-linux.log`), followed by a forced Windows build
(`/tmp/sh1x-stock-weapon-final-win32.log`). The isolated Bog probe at
`%TEMP%/sh1x-stock-weapon-final-20260908-040455` passed the native
`SH1X_STOCK_WEAPON_PRECACHE_PASS` marker and all four existing VM markers,
reported native weapon mapping ready, and exited normally. The same precache
assertion sequence is now included in the persistent native VM fixture.
The existing C1 and Python lobby processes were not changed.
