# Publishing weapons registered by native scripts

`CODOL_RefreshServerWeaponMappings` now appends mounted stock weapons that the
native registry has loaded but the client's weapon configstring bank does not
yet contain. The lobby attachment-table prepass is only the initial list: map
scripts can precache additional weapons, including offhand weapons.

Existing slots are replayed without changing their order or ammo/clip keys.
New definitions append in native registration order, recursively registering
their +b78 and +b88 partners in client order. Previously registered partners and
cycles reuse the existing slot. Custom `*` definitions remain unsupported.

The new registry, configstrings, and both weapon-ID maps are staged together.
A missing partner, failed conversion, capacity limit, or duplicate native ID
leaves the previous state intact. Reliable-command token validation applies to
new names. After the commit, primed clients with a sent gamestate receive each
new `d <configstring> <name>` command in ascending slot order. Other clients get
the resulting bank in their gamestate. Existing mapping refresh call sites
cover gamestate construction, snapshot startup, and decoded user commands.

The registry test exercises a stock rifle and partner appended after an existing
shared-ammo pair, verifies preserved indices and pool keys, retries after a
partner failure, and checks that repeated refreshes do not republish names.
The production asset-publication test checks reliable command formatting,
recipient eligibility, and bank bounds.

This supplies weapon publication needed by input and snapshots. It does not
complete the missing live frame producers or prove authenticated match entry.

Validation on 2026-09-08: Linux build and full suite passed in
`/tmp/sh1x-weapon-append-linux.log`, followed by the forced Windows build in
`/tmp/sh1x-weapon-append-win32.log`. The updated focused registry test also
passed AddressSanitizer and UndefinedBehaviorSanitizer.

The isolated native Bog probe at
`%TEMP%/sh1x-weapon-append-20260908-041233` precached `frag_grenade_mp`, which
is absent from the initial 54-name lobby prepass. The registry increased to 55,
native mapping reported ready twice, all six VM markers passed, and PID 74700
exited normally. The offhand precache is now part of the persistent VM fixture.
This probe had no connected client; reliable delivery is covered by the native
publication fixture, not a live C1 receipt measurement.
