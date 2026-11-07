# Native GSC compatibility work

The requested target is the IW4 and T5 builtin surface implemented in the native
sh1x server. Registration alone does not establish compatible behavior. Python
effect ledgers, dummy objects, and refusal handlers must not become native stubs.

## Inventory

[CODOL_BUILTIN_INVENTORY.json](CODOL_BUILTIN_INVENTORY.json) currently records 1,307
distinct names from alpha0022's `vendor/builtins/iw4_builtins.json`, the actual
`BuiltinTable` registrations in `gsc/gscbuiltins.py` and `gsc/builtin_surface.py`,
`docs/BASE.md` Appendix A, and the verified local T5 server resolver tables in
[CODOL_T5_BUILTINS.json](CODOL_T5_BUILTINS.json). The Python table is instantiated with CaptureHost
for enumeration only; it does not serve gameplay.

Each Python registration now includes reference-relative source paths, line
numbers, and callable names in `python_sources`. EFFECT registrations include
both the counter wrapper and its stored target, so the list leads to the actual
reference body. These locations are navigation aids, not proof that a Python
implementation has native engine behavior. The reference's
`docs/builtin_surface.md` describes its own census and limitations;
`gsc/census.py` separately inventories script call candidates.

480 names have bindings for the catalog's expected function/method forms; 827
lack a matching binding. These are **name coverage counts, not implementation
counts**. In particular, bindings to retained IW3 implementations need behavioral
and wire-format review. The inventory records the native symbol and developer
restriction. A name with both forms in the reference catalog requires both forms
for that count; catalog classification differences still need investigation.

The previous Python/IW4/Appendix inventory contained 844 names (444 with matching
bindings, 400 missing). The expanded scope adds 463 distinct names; the higher
missing count is not a loss of native implementations. Python-only CoDOL helper
names retain their source labels and are not confirmed IW4 or T5 functions.
The reference's BASE document excludes 331 engine-looking T5 call names, and its
mentioned `_calls.json` scratchpads have not been located. Direct resolver-table
extraction now provides a stronger engine-builtin source for the local T5 build.
It does not establish coverage of other T5 builds or client-script builtins.

A stronger local T5 source was located on 2026-09-08 through alpha0022's
`scratchpad/dis_t5.py`: `D:/t5server-pdb/CoDMPServer.exe` and its matching-name
`.map` and `.pdb` files. Static disassembly of the executable confirms
`Scr_GetFunction` at 0x660a50 loops over 383 twelve-byte entries at 0xe08510
(name, function pointer, developer flag). `BuiltIn_GetMethod` at 0x661680
loops over 234 entries of the same shape at 0xe09708. These are not the entire
method surface: `Scr_GetMethod` at 0x6615c0 first calls six specialized
resolvers (0x60f9a0, 0x665cd0, 0x67d110, 0x620a30, 0x640b30, 0x919ac0).
All eight tables have now been extracted: 1,008 records resolve to 383 function
names and 601 method names. Duplicate methods retain their records and the
first-match precedence from `Scr_GetMethod`. The six specialized resolvers do
not propagate the third table word as a developer flag; the catalog records
both that raw word and the effective flag. Every name is bounded and validated,
and each function target must belong to an executable PE section. The extractor
requires the verified executable SHA-256 before interpreting fixed addresses.
No live process was attached or modified.

Regenerate the T5 catalog with `tools/codol_t5_builtin_catalog.py --executable
<CoDMPServer.exe> --output docs/CODOL_T5_BUILTINS.json` (requires pefile).
Then run `tools/codol_builtin_inventory.py --reference <alpha0022>
--preprocessed <registry.i> --t5-catalog docs/CODOL_T5_BUILTINS.json
--output docs/CODOL_BUILTIN_INVENTORY.json` after
preprocessing `src/scr_vm_main.c` using the compiler with `-m32 -E -P
-DCODOL_SERVER -D_GNU_SOURCE`. Preprocessing excludes commented and inactive
registrations. Run this analysis only against trusted reference Python code.

## New math implementations

`getdvarvector` now reads native dvars, supports an optional string default for
absent variables, and parses parenthesized/comma or whitespace-separated vectors.
IW4's table entry at 0x79a290 binds 0x5ec6e0; the implementation checks one or two
arguments, calls lookup/default helper 0x43ac20, and requires three assignments
from `(%f, %f, %f)` or `%f %f %f`. Existing empty/invalid values raise a script
error rather than selecting the fallback. As in the observed code, trailing
characters after three assignments are accepted. Its unusual implicit default
at 0x6f7bb0 is `0.0f 0.0f 0.0f`, which fails that parser; this behavior is retained.
Python's partial-vector padding and punctuation normalization are not used.
Focused Linux ASan/UBSan checks cover both formats, defaults, missing versus
empty values, parse failures and argument counts. Windows build passed in
`/tmp/sh1x-dvar-win32.log`.
An isolated shipped Bog startup on UDP 17770 executed `codol_dvar_vm` through
the native GSC VM and printed `SH1X_DVAR_VECTOR_VM_PASS`, verifying a real dvar
read and an absent-dvar explicit default. The probe was stopped afterward;
C1 and the Python lobby remained responsive. This does not resolve the separate
`isItemUnlocked` vendor-script dependency.

Native HUD `changefontscaleovertime` now owns transition metadata, captures it
alongside client HUD copies and supplies CoDOL interpolation fields. See
[HUD font-scale transitions](CODOL_HUD_FONTSCALE.md).

Native `enableusability` and `disableusability` now control the retained player
activation path, including pending-use cancellation and release-edge handling.
See [player usability](CODOL_USABILITY.md) for the IW4 evidence and assembly test.

Native `enableweaponswitch` and `disableweaponswitch` now gate requested weapon
changes and publish the restriction through the CoDOL player-state adapter.
See [weapon-switch controls](CODOL_WEAPON_SWITCH_CONTROLS.md) for evidence and
remaining live-client validation limits.

Native `getnode`, `getnodearray`, and `getallnodes` now query owned map records
through VM class 2. Both path-node and vehicle-node VM assertion groups pass on
the isolated shipped Bog probe; see [path-node integration](CODOL_PATH_NODES.md).
This does not implement graph navigation or validate the full gametype.

`src/codol_script_math.c` implements:

- `angleclamp180`: finite angles folded to (-180, 180], including -180 -> 180.
- `averagepoint`: centroid over native VM array vector values, including
  associative/sparse entries.
- `averagenormal`: normalized vector sum; empty or cancelling sums return zero.

These functions operate on native VM values. Vector accumulators use doubles
to avoid overflowing when averaging large finite float components. Malformed
arrays and nonfinite values raise script errors without producing a result.
This is intentionally stricter than the Python reference's filtering of
non-vector entries; retail error-message and malformed-input parity is unverified.
Valid-input semantics follow the reference's pure-function implementations and
the IW4 javelin script usage. Live match execution remains unverified.

The focused test checks angle boundaries, sparse native child traversal, centroid
versus normalized sum, cancellation, large vectors, and error output behavior.
VM access is a fixture in that test, so it does not prove full VM integration.
The test passes under Linux AddressSanitizer and UndefinedBehaviorSanitizer.

## New server queries

`src/codol_script_server.c` adds `getplayers`, `getsystemtime`, `getbuildnumber`,
and `getbuildversion`. The player query enumerates in-use native client entities
in slot order, includes connected spectators, and excludes connecting or
disconnected slots. The clock returns Unix seconds in a 32-bit GSC integer;
the existing `getrealtime` instead subtracts the start of 2012 and is unsuitable
as an alias. Build queries report this server's build count and sh1x product
identity, rather than pretending to be the retail client's build.

The focused server-query fixture checks player selection and slot bounds,
epoch handling, signed 32-bit time boundaries, and build identity. It passes
under Linux AddressSanitizer and UndefinedBehaviorSanitizer. This is fixture
coverage, not a successful live multiplayer session.

## Vehicle-node queries

`getvehiclenode`, `getvehiclenodearray`, and `getallvehiclenodes` now query
native class-3 objects backed by the current map's `info_vehicle_node` and
`info_vehicle_node_rotate` records. Initialization uses the retained
`G_ParseSpawnVars` parser and restores its parse point for the normal spawn pass.
Each accepted record owns its copied strings. Script shutdown clears this store;
the next initialization replaces it.

Source-edited object-field dispatch exposes targetname, target, script_linkname,
script_noteworthy, classname, origin, angles, speed, lookahead, spawnflags, and
model. Missing keys return undefined; malformed numeric fields raise errors.
Lookup values compare exactly, following the retained entity lookup's string
identity semantics. Singular duplicate matches raise an error, following the
retained `getent` behavior, rather than the Python reference's first-match rule.
Exact retail vehicle-node defaults and error parity are still unverified.
Writes to these native fields explicitly fail until implemented; this is not a
complete vehicle path/simulation implementation. Dynamic script fields remain
the responsibility of the native VM.

The focused sanitizer fixture passes for ownership, record filtering, lookup,
misses, duplicate rejection, fields, and reset. Its map parser and VM calls are
fixtures. A real Windows startup with the normal IW4 reference scripts passes
the old GetVehicleNode compiler failure and now stops at PhysicsLaunchClient
in `common_scripts/utility.gsc:3103`. That proves name resolution only.

Separate isolated VM probes with minimal test scripts on mp_bog_sh and
mp_crash_tropical stopped before script execution at native collision assembly.
They do not prove field access in the running VM. The subsequent mp_bog_sh
collision audit finds successful native brushes, terrain, leaves, 1193 static
models, 704 dynamic/effect physics models, and all 432 presets, but **17 of 51
dynamic effect instances fail native conversion**. This asset-loader gap blocks
the Bog VM probe. All diagnostic processes exited; client/lobby were untouched.

Follow-up: [particle-cloud conversion](CODOL_FX_CLOUD.md) fixes all 17 failed
Bog effect instances. The map now installs native collision, and the isolated
VM probe reaches game initialization. Subsequent native movement-table support
passes `idlelaststand`; animation parsing now rejects `akimbo` at line 139.
See [animation-script status](CODOL_PLAYERANIM_STATUS.md). Node field execution is still
unverified. Normal reference GSC startup retains the separate
PhysicsLaunchClient compiler blocker above.

## Rebranding

The CoDOL build now identifies itself as **sh1x server**, with the long product
name **Call of Duty Online Closed Alpha Server**. This covers the startup/info
banner, product/window title macros, default hostname, and server-info project
field. `bin/codol_dedrun` / `.exe` stays the executable path used by existing
launch configurations. Upstream attribution and the optional IW4OL build profile
remain in place. This branding does not imply a completed playable port.

Validation: Windows server build and `--codol-info` probe pass (exit 0); the
banner reports sh1x. Full Linux `make -B -j6 all test-codol` passes, including
the two new focused fixtures. Existing client and lobby processes were untouched.
