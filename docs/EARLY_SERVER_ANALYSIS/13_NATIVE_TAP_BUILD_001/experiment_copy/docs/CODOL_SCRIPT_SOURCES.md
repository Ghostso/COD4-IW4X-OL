# Native server script sources

The client archives do not supply the server's codescripts or gametype scripts.
The alpha0022 reference documents their absence in `docs/gsc_notes.md` and
provides an IW4 source base and CoDOL overlay. These are source GSC files, not
a shipped CoDOL bytecode package. The native server retains its source compiler.

Startup variables connect those directories and the server's adaptations to the compiler:

```
+set codol_scriptPath "<alpha0022>/vendor/iw4"
+set codol_scriptOverlay "<alpha0022>/gsc_overlay"
+set codol_scriptNativeOverlay "<sh1x checkout>/scripts/codol"
```

Lookup checks the user overlay, the native adaptation directory, `scriptPath/mp`,
then `scriptPath`. The native directory defaults to `scripts/codol` relative to
the process working directory; use an absolute path when launching elsewhere.
It currently contains the reviewed utility adaptation; class adaptation is pending.
If absent from all roots, filesystem and mounted rawfile lookup still runs.
Empty variables omit their layers. These roots supply source only, not other
assets. Original alpha0022 files remain unchanged.

Successful reads return owned, terminated source to the retained compiler and
source-debug registry. Embedded NULs, oversized files, read errors and invalid
relative paths are errors; a broken override does not silently load a base
script. Relative names cannot traverse parents or name absolute paths.

## Verified startup result

Windows probe on 2026-09-07: original CoDOL client archives, `mp_killhouse_sh`,
`dm`, loopback port 17739, isolated home `%TEMP%/codol-script-roots-probe`, and
the reference paths above. It passed default-weapon and mantle initialization,
loaded the codescripts, and reached compilation of gametype dependencies.
The next failure was:

```
bad syntax: maps/mp/_utility.gsc, line 283
foreach ( message in self.lowerMessages )
```

The retained IW3 grammar does not accept this IW4 construct. This is a native
compiler compatibility task; finding the source alone does not complete script
support. The isolated server remained at its fatal-error handler and was
stopped after verifying its executable and probe command line. The reference
lobby and C1 were untouched. No successful match or player spawn is claimed.

Validation: full Windows and forced Linux server builds pass, as does the
Linux `test-codol` suite. The standalone source-directory fixture passes
32-bit ASan/UBSan and checks precedence, absent files, binary overrides,
relative-path rejection, and preservation of outputs on failure.

## Native syntax adaptation

All three source paths (configured directories, normal filesystem and mounted
rawfiles) now pass through `CODOL_LowerScriptSyntax` before source registration
and compilation. This native C++ pass leaves original files untouched. It
handles `foreach(value in expression)` and `foreach(key, value in expression)`
by capturing the array expression once, obtaining its keys with the existing
`getarraykeys` builtin, and emitting an IW3 `for` loop. Values are read from the
captured array at each iteration. This key-snapshot strategy is not a claim of
parity for every possible mutation of an array during iteration.

Generated variables avoid existing identifiers case-insensitively. The pass
tracks comments, strings, balanced groups and complete statement bodies, so
nested loops, unbraced if/else bodies, and normal break/continue statements
retain their control-flow nesting. It preserves source line counts; generated
columns and text can differ. It also removes the explicit `call` marker from
IW4 `call [[function]]()` syntax, including calls inside a foreach expression.
The retained compiler still resolves and emits the calls and loop bytecode.

The follow-up Windows probe at `%TEMP%/codol-syntax-probe` passed the earlier
foreach and explicit-call parse failures. Its next failure is an unresolved
native method in `common_scripts/_fx.gsc`, line 298:

```
fxEnt willNeverChange();
```

That method has not been replaced with a no-op. Its semantics need inspection
and native implementation. The probe was stopped after verifying its process
identity at the fatal-error handler. There is still no verified match entry.

Syntax-pass validation: Windows server build and the live probe above; forced
Linux build and full `test-codol` suite; focused 32-bit ASan/UBSan checks for
nesting, statement boundaries, string/comment handling, temporary collisions,
line preservation, malformed input, and combined foreach/pointer-call syntax.
These checks do not yet prove runtime script behavior in a started match.

## Static entity method

`willNeverChange()` is now registered as a native method. C1 function 0x53c070
resolves the script entity at 0x534a10 and ORs entity +8 with 0x80000000 at
0x53c07f. The delete path checks this bit at 0x53d295 and references the explicit
willNeverChange error at 0xc56aa0. Visibility methods also check it near
0x54d9b8/0x54da26/0x54dab6/0x54dbd6, with the change error at 0xc58f18.

The native implementation sets that same entity-state marker, preserves other
flags, and guards script delete/show/hide/showToPlayer before invoking retained
engine behavior. Invalid entity references raise object errors. This is
ordinary native method registration and source code, without client hooks.
The marker is server-only: the CoDOL -98 entity-flags codec carries 30 bits,
so bit 31 is deliberately not copied into snapshot flags. Other entity
mutation methods and simulation-side changes still need a separate audit;
these guards are not a claim of universal entity immutability.

The Windows probe in `%TEMP%/codol-static-entity-probe` compiled beyond the
previous missing method and next failed on `closePopupMenu()` at
`common_scripts/_createfx.gsc:1472`. The isolated process was stopped at its
fatal-error handler after identity checks. Match startup remains incomplete.

Static-method validation: Windows build and the live compiler probe above;
forced Linux build and full `test-codol` suite; focused 32-bit ASan/UBSan
checks of marker preservation/idempotence, invalid references, rejection of
the four guarded methods, and delegation for ordinary entities.

## Native menu methods and configstrings

Native menu methods now emit CoDOL commands: open/open-no-mouse `q slot` /
`q slot 1`, close current/named `r` / `r slot`, close pause menu `H`, and
open/close popup `u slot` / `v slot`. Indexed open/popup operations require a
fully connected player and return a success integer, matching the measured
C1 sender checks. Entity/player validation precedes command output.

Evidence: C1 popup sender 0x513630 checks client connection state at +33a4,
resolves the menu through 0x5387b0, emits byte 0x75 at 0x5136e0 and returns
0/1. The matching sender 0x513750 emits 0x76 at 0x513800. Client handler
0x467fc0 validates the slot against 31 and reads names through 0x6d1137c,
which is configstring index 4243 relative to the 0x6d0d130 table base.
Close-current/named sender 0x51359a selects `r` or `r slot`. The pause command
`H` is documented in the reference `matchflow.py` and `docs/pause_menu.md`.

`precacheMenu` now registers in the 32-slot CoDOL menu bank rather than IW3
CS 1970. Effective lookup respects explicit overrides (including empty clears)
then inherited constants. Existing names are reused case-insensitively; new
names occupy an empty slot and publish a reliable `d <index> <name>` command.
Malformed names, exhausted slots and unknown names raise script errors.
Only integer slots enter menu commands, avoiding unquoted script name payloads.

The Windows probe at `%TEMP%/codol-menu-probe` compiled beyond the menu methods
and next failed on `org AddRoll(...)` in `common_scripts/_createfx.gsc:610`.
The isolated process was confirmed absent during cleanup after the fatal error.
This verifies compile progress, not menu rendering, input focus in C1, or a
started match. The reference lobby and C1 were untouched.

Menu validation: Windows native build and the compiler probe above; forced
Linux build and full `test-codol` suite; focused 32-bit ASan/UBSan checks of
exact command bytes, player/connection checks, inherited slot zero, explicit
clears, case-insensitive reuse, new configstring publication and invalid input.

## Immediate angle increments

`AddPitch`, `AddYaw`, and `AddRoll` now have native implementations. The retained
`ScriptEntCmd_DevAdd*` functions are empty assembly bodies, so aliasing those
names would not implement the operation. The new methods read the entity's
current angles, add the supplied float to exactly one Euler component, and
call the same `G_SetAngle` used by the native script `angles` field setter.
That retained setter updates current angles and sets a stationary angular
trajectory with zero time/duration/delta.

This follows the component-addition behavior in the reference `_addangle`
implementation and the one-argument calls in `_createfx.gsc`. It is immediate;
no unverified timed rotation or deferred notification behavior is added.
Non-finite inputs/results and protected static entities raise script errors
before invoking the setter. Other angle components are preserved.

The Windows probe in `%TEMP%/codol-addangle-probe` compiled past these methods.
Its next failure is `SetDevDvar("createfx_map", level.script)` in
`common_scripts/_createfx.gsc:107`. The isolated probe had already exited when
cleanup checked its process handle after the fatal compiler error. No match or client interaction has been verified.

Angle-method validation: Windows build and compiler probe; forced Linux build
and full `test-codol` suite; focused 32-bit ASan/UBSan checks of each axis,
positive/negative increments, preservation of other components, protected
entities, and rejection of infinity/NaN before setter dispatch.

## Dvar setter names

`SetDevDvar` now uses the retained `GScr_SetCvar` implementation. Both
`SetDevDvarIfUninitialized` and `SetDvarIfUninitialized` check `Cvar_FindVar`
first and invoke that same setter only when the dvar is absent. An existing
empty string or zero is initialized and remains unchanged. New assignments
retain the native name validation, script value conversion, localized-string
handling and dvar flag behavior.

This follows the reference's `host.set_dvar(..., only_if_new=...)` behavior;
it is not a claim of independently reconstructed retail developer-dvar flags.
No extra parser or replacement dvar store was introduced.

The final Windows probe at `%TEMP%/codol-dvar-family-probe` passed these names
and next failed at `GetVehicleNode(target, "targetname")` in
`common_scripts/utility.gsc:3166`. The isolated probe was stopped after its
fatal compiler error. Vehicle-node storage/lookup needs investigation; it was
not replaced with a generic entity lookup. Match startup remains unverified.
