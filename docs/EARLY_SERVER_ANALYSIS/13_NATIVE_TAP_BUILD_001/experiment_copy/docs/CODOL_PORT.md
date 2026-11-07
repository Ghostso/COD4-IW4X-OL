# CoDOL 1.1.1.13 native source port

Status: **incomplete, not playable**. This is a source fork on
`codex/codol-server`, based on CoD4x commit
`def475a7c3681171698a6bf365bc2a3ae9747fe7`. No upstream commit was replaced.
No client process, binary patch, trampoline, or Python proxy is required by the
new code. Existing upstream assembly remains statically assembled into the server.

## Reference

Weapon work should start from alpha0022's existing implementation and its
measured notes: `weapon_configstrings.py` for registration order,
`weapon_spawn.py`/`custom_weapon_pool.py` for composed weapons,
`alt_weapons.py` for companion registration, and `ammo_model.py`,
`weapon_fsm.py`, `wpn_firemodes.py`, and `equipment.py` for gameplay and wire
state. These are source references for the native port, not runtime dependencies.
The native weapon core now binds the resolved +0xb78 alternate name to
`szAltWeaponName` and retains +0xb88's separate partner name. This follows
`alt_weapons.py`'s documented registrars at C1 0x41f4b0 and 0x41f510. Null
resolved names become empty strings, as required by the retained IW3 registrar;
serialized client indices are not copied. Missing, duplicate, or incorrectly
typed companion entries fail atomically. Native companion registration and
attachment composition remain unfinished, and this intermediate core still
cannot be published as a general WeaponDef.

The timing converter also uses `harvest_firetime.py`'s measured +0x59c fire
delay, +0x5a8 detonation delay, +0x5b8 hold-fire time, and +0x5bc detonation
duration. `docs/ads_simulation.md` identifies +0x950/+0x954 as the integer ADS
transition durations; these now populate the native duration fields while
the independently serialized +0xa28/+0xa2c rates remain intact. All six
durations preserve zero, reject negative values, and participate in the
existing atomic timing conversion. This supplies definition data; it does
not by itself implement CoDOL's additional weapon phases or attachment overrides.

Weapon animation-name conversion now binds 28 shared roles. The additional
roles are fire/hold-fire/last-shot (source slots 3/4/5), ADS fire/last-shot
(34/35), reload-start (13), first-raise (16), alternate-raise (19), and
detonation (31). The dispatcher referenced by `weapon_fsm.py`, C1 0x47be58,
routes the corresponding animation IDs to slot selections at 0x47b96f,
0x47bc07, 0x47b982, 0x47b9a8, 0x47b9bb, 0x47badb, 0x47ba7c,
0x47bb14, and 0x47bc1a. Native targets come from retained
`weaponDefFields` in `_bg_weapons_load_obj.asm`. Null/empty names remain
null/empty, and unverified native slots remain untouched. All 144 source
names and their loaded native XAnimParts remain available in the core;
these bindings do not substitute for client animation IDs or complete
weapon registration.

The native core now binds pickup/use and drop hints from resolved +0x9fc and
+0xa00 strings. C1's registrar at 0x529abf/0x529aee matches the retained
`G_RegisterWeapon` string accesses at +0x7dc/+0x7e0. Null resolved names become
empty strings; nonempty text is retained with archive lifetime. Serialized
hint indices +0xa04/+0xa08 are never copied into native runtime indices.
Missing, duplicate, or incorrectly typed entries reject the entire core
transaction. This closes the null-string dereference risk identified in the
registration audit, without publishing the still-incomplete general definition.

The reference's measured model-role table also supplies source +0x24 magazine,
+0x2c view-knife, and +0x30 world-knife bindings to the native fields. Remaining
leading model slots 6/9/10 are retained without assigning unverified roles.
The leading display-name mapping was corrected from +0x04 to +0x08, matching
`WEAPON_DEFAULTWEAPON` in the shipped default asset. All four source strings
are retained in source order; +0x04/+0x0c are no longer presumed to be IW3
overlay/mode names. Their native roles remain unbound pending evidence.

The supplied reference was found at:

```
D:\CoD\CODOL Builds\Call of Duty Online 1.1.1.13\CODOL\1.1.1.13_server\alpha0022
```

This differs from the requested `1.1.1.13\_server\alpha0022` spelling.
The reference was read only. No account data, security keys, captures, game
assets, or reference launcher settings have been copied into this repository.

## Implemented

The composed-player regression now crosses the real serializer/history bridge:
it composes player fields, inventory/ammo updates and two HUD arrays, prepares
and accepts a full snapshot, then prepares a delta that changes ADS and removes
the HUD. It verifies that prepared frames are invisible to ACK lookup, rejected
sends never become bases, accepted bases own their player/HUD storage, and later
source mutations do not alter them. The full Linux regression suite and native
fixture under 32-bit ASAN/UBSAN pass. Unfinished player fields use a controlled
test seed; this is not proof that the live player producer or match entry is
complete. No production serializer change was needed for this fixture.

HUD collection is now part of the player composition transaction. Resolved
archival/current HUD arrays, player fields, array updates and the event clock
commit together after every producer succeeds. A missing resolver or an invalid
late HUD element leaves all four outputs intact. Empty source HUD arrays clear
previous elements without requiring a resolver. Resolver-context side effects
remain outside this output transaction. The complete live snapshot writer is
still not connected.
Verification: full Linux server/regression and Windows server builds pass.
The native state/networking fixture passes under 32-bit ASAN/UBSAN, checking
both HUD arrays, late resolver failure, a missing resolver, empty-array removal
and rollback of all four outputs after earlier player/event updates.

Player composition now includes exact ADS fraction (`+0x348`) and aim-spread
scale (`+0x34c`) from the named native player fields. C1's fire selector reads
ADS at `0x41b7e7`; spread integration reads/writes `+0x34c` at
`0x418deb/0x418e2f`. Both netfields use float-word XOR codec `-88`, so the
producer preserves fractional values instead of rounding them. Nonfinite or
out-of-range values (ADS outside `0..1`, spread outside `0..255`) reject the
entire player composition. These values are now produced but still await live
snapshot integration.
Verification: full Linux server/regression and Windows server builds pass.
The native state/networking fixture passes under 32-bit ASAN/UBSAN, checking
fractional/boundary values, nonfinite/out-of-range rejection, unrelated-field
preservation and rollback of the complete player transaction.

`CODOL_OverlayEnginePlayer` now composes the measured player producers in one
transaction: movement/mode, weapon selection/phase/aim, grenade state, health,
inventory, ammo, predictable events and HUD. Player fields, array updates, HUD and the
event-generation clock commit together only after every producer succeeds.
Bindings explicitly supply alternate-weapon selection, previous-use bits,
ammo slot/key mappings and event parameters. Ammo masks retain update semantics;
callers must request clears for vacated slots. Other player fields retain their
existing owners, and entity/client collections remain separate. This supplies atomic player
composition without treating an incomplete record as a complete live snapshot.
Verification: full Linux server/regression and Windows server builds pass,
as does the native state/networking fixture under 32-bit ASAN/UBSAN. The new
composition fixture checks concrete mapped output, reserved owner IDs, ammo
clears, event-clock wraparound and rollback of all four outputs at each of the
producer stages. Live snapshot integration and match entry remain pending.

The grenade-state producer now overlays the signed grenade/throwback timers,
throwback owner and offhand-use flag. C1 sets the grenade fuse at `0x41c561`,
uses the expired sentinel `-1` at `0x41cd1d`, and tests the throwback timer at
`0x421dec/0x421e45`. Prepare/end set and clear weapon flag mask `0x2` at
`0x41c3d5/0x41c946`. Native fields come from the retained player-state layout;
world/none owner IDs `1022/1023` become CoDOL `2046/2047`. Both timers must fit
signed 16-bit values, including negative sentinels. Invalid input preserves
the entire output, while unrelated weapon flags and fields remain untouched.
This producer is available for frame construction; it is not yet wired into
the live snapshot body.
Verification: full Linux server/regression and Windows server builds pass.
The native state/networking fixture passes under 32-bit ASAN/UBSAN, covering
timer boundaries/sentinels, ordinary and reserved owners, every individual
source flag bit, unrelated-field preservation and atomic rejection.

The primary dispatcher now includes measured offhand initialization,
preparation/throwback, hold, throw/post-throw, end, and main-weapon detonation.
Native states `15/16/17/18/19/20/21` map to CoDOL `16/17/19/18/19/21/22`;
the two native throw stages share CoDOL state `19`. Animation roles are selected
per phase and restart bits are translated without copying native enums.
C1 writes the actual offhand throw state at `0x41c66d` and animation `2` at
`0x41c70a`. The reference's inferred throw-animation attribution to `0x41ce5f`
instead belongs to main-weapon detonation, whose state `22` is written at
`0x41ce43`. Preparation and hold are established at `0x41c3c5/0x41c536` and
end at `0x41c887`; the retained native branches establish their counterparts.
CoDOL's special offhand detonation state `20` needs its own gameplay extension.
Selection, usage flags, grenade timers and live snapshot integration are separate
requirements; these phase mappings alone do not establish equipment gameplay.
Verification: full Linux server/regression and Windows server builds pass.
The native state/networking fixture passes under 32-bit ASAN/UBSAN, covering
each measured offhand/detonation mapping, restart toggles, preservation of
unrelated fields and rejection of other tested 11-bit animation values.

`CODOL_OverlayEnginePrimaryWeapon` now dispatches measured idle, fire,
rechamber, raise, drop, reload, melee and sprint phases using native state and animation
together. Hip/ADS fire (including empty variants) uses IDs `2/3/5/6` in both
engines, established by retained `PM_Weapon_1360/1950` and C1
`0x41b7e0..0x41b817`; rechamber uses `4/7`. The dispatcher translates the restart
bit and retains the engine's selected animation rather than recalculating its
ammo/ADS decision. Normal/charged melee IDs `8/9` are verified in retained
`PM_Weapon_460`/charge branches and C1 `0x41bef8..0x41bf09`; native melee states
`12/13/14` become CoDOL `13/14/15`. The engine's timers are preserved across
these phases. Other unmeasured phase adapters, including night vision, still
reject explicitly. It does not yet replace the live IW3 snapshot writer.
Verification: full Linux server/regression and Windows server builds pass.
The native networking/state fixture passes under 32-bit ASAN/UBSAN, covering
dispatch across the measured phase families, restart bits, alternate-drop
disambiguation and atomic rejection. These are producer tests, not live client
snapshot or match-entry verification.
The melee extension also passes the full Linux/Windows builds and 32-bit
ASAN/UBSAN native fixture. It checks all three melee phases with both animation
roles and restart values, rejects every other tested 11-bit animation value,
and preserves unrelated player fields. Live melee remains unverified.

The snapshot raise adapter now translates normal, first, alternate, quick and
empty raise animations `11/12/18/20/22` to CoDOL `11/12/20/22/24`, including
restart-bit conversion. Normal/alternate states remain `1/2`, established by
retained `PM_Weapon_2270` and C1 `0x419abb`. Animation evidence is the retained
`PM_Weapon` raise branches and C1 `0x419ec5/0x419e71/0x419e2a/0x419eb2/0x419e55`.
The adapter preserves engine timers, including first-raise duration and zero,
and rejects invalid input without altering primary or secondary state. Live
initial equip and weapon switching still require full snapshot integration.
Verification: the full Linux server/regression and Windows server builds pass.
The native state/networking fixture passes under 32-bit ASAN/UBSAN, including
both raise states, five animation roles, restart toggles, zero/first-raise
timers and atomic rejection of unsupported states, animations and overflow.

The snapshot weapon-drop adapter now handles ordinary, quick, empty and
alternate drops, including the animation restart bit and primary timers.
Retained `PM_BeginWeaponChange` uses states `3/4` and animations `10/17/19/21`;
CoDOL uses animations `10/19/21/23`. Alternate animation `17` must also select
CoDOL state `5`, confirmed by C1 `0x4198d4/0x4198e4`; ordinary/quick states are
selected at `0x4199e1..0x4199ec`. Thus native drop states deliberately remain
unsupported by the state-only mapper. This adapter resolves the ambiguity from
both state and animation, preserves unrelated/secondary-hand fields, and rejects
invalid input atomically. Complete live snapshot composition remains pending.
Verification: the full Linux server/regression and Windows server builds pass.
The native state/networking fixture passes under 32-bit ASAN/UBSAN, including
both drop states, four animation roles, both restart values, zero timers,
invalid states/animations and timer overflow. Tests assert whole-record
preservation outside the primary phase fields; live weapon switching remains
unverified until snapshot integration and match initialization are complete.

The movement snapshot adapter now translates the native sprint level
(`pm_flags & 0x8000`) to CoDOL's `+0x0c & 0x4000`, including clearing the target
bit when sprint ends. The retained `PM_Weapon` branch tests the sign of the low
native flag word; C1 `0x41d477/0x41d47a` explicitly reads/tests the CoDOL bit
before entering or leaving its sprint phase. Other target flags remain intact;
unrelated source bits are not copied. Invalid movement data still rejects the
whole update, including its flag change. This complements the sprint phase
adapter, but does not finish other flag producers or connect the live writer.
Verification: full Linux server/regression and Windows server builds pass.
The native networking/state fixture passes under 32-bit ASAN/UBSAN, checking
all 32 individual native flag bits against two existing destination patterns,
explicit sprint entry/exit and rollback after a later invalid movement field.
These checks establish adapter behavior, not live client prediction or entry.

The snapshot engine adapter now translates sprint entry/loop/exit states
`22/23/24` into CoDOL `23/24/25`, animation IDs `23/24/25` into `25/26/27`,
and the restart bit from `0x200` to `0x400`. Native evidence is the retained
`PM_Weapon` sprint branches, including loop label `PM_Weapon_2410`; C1 writes
the corresponding states/animations at `0x41d0a3/0x41d0ca`,
`0x41d0fc/0x41d139`, and `0x41d171/0x41d1c8`. Primary timing is preserved,
including the loop's zero timer, and invalid input leaves the whole player
field record unchanged. This supplies another frame-construction component;
movement-flag production and the live CoDOL snapshot writer are still pending.
Verification: the full Linux server/regression build and Windows server build
pass. The native networking/state fixture also passes under 32-bit ASAN/UBSAN,
including sprint state/animation combinations, restart toggles, rejected values,
unchanged unrelated player fields and zero-time loops. No client match-entry
or live sprint-prediction result is claimed by these fixture checks.

Weapon timing conversion now maps sprint entry/exit (`+0x618/+0x620`) to the
native sprint fields and retains dive entry/exit (`+0x630/+0x638`) separately.
C1 reads these at `0x41d0aa`, `0x41d162/0x41d1ad`, `0x41d22a` and `0x41d2da`;
the retained IW3 movement code consumes native sprint fields `+0x3c8/+0x3d0`.
CoDOL's sprint loop writes a zero timer at `0x41d106`; the converter does not
infer a loop duration or mislabel the dive fields as IW3 night-vision timers.
Negative durations reject atomically, and zero durations remain zero. Dive
gameplay and transmission of the complete locomotion state remain unfinished.
Verification: focused Windows and 32-bit Linux ASAN/UBSAN fixtures pass, as do
the full Linux server/regression and Windows server builds. Both real-asset map
startup checks retain `500/500` ms for default-weapon sprint and dive entry/exit;
native `none` loads and `defaultweapon_mp` registration still fails. A successful
build or diagnostic output is not evidence of match entry.

Weapon-core ammo conversion now preserves the shared ammo cap (`+0x584`) and
clip-only flag (`+0xbcd`). C1's maximum-ammo consumer reads the registered pool's
cap at `0x41dfb0/0x41e040` and selects clip capacity at `0x41dfbc`; pickup handling
tests the same flag at `0x41e085`. These correspond to the retained native
`iSharedAmmoCap` and `bClipOnly` fields used by `BG_GetMaxPickupableAmmo`.
The source shared-cap index (`+0x580`, assigned by C1 `0x41f310`) remains excluded
from conversion, along with the source ammo/clip indices. Zero and caps above
clip/reserve capacity are preserved; negative caps and nonboolean flag bytes
reject the whole conversion. This prepares native ammo handling but does not
yet register general weapons or establish CoDOL ammo-index parity.
Verification: the native weapon fixtures pass on Windows and on 32-bit Linux
with ASAN/UBSAN, covering cap boundaries, every invalid clip-only byte, unchanged
runtime indices and atomic rejection. The full Linux server/regression build and
Windows server build pass. Both real `mp_killhouse_sh` startup checks report the
default weapon's cap/clip-only values as `0/0`, load native `none`, and still fail
at `defaultweapon_mp`; neither run entered a match.

Weapon-core composition now preserves the ADS and hip recoil groups: two reduced
kick bullet counts and 26 floats covering percentages, gun pitch/yaw ranges,
acceleration, speed/decay and view pitch/yaw ranges. C1 selects the counts at
`0x41b56d/0x41b588`, percentages at `0x4221ac/0x4221b4`, angular ranges through
`0x422200..0x422403`, and interpolated gun dynamics at `0x4242f9..0x424355`.
Signed and reversed angle ranges remain unchanged; nonfinite values and negative
counts/percentages/dynamics reject atomically. Percentages above 100 remain valid
source values. View centering/scatter, player modifiers and recoil gameplay
integration remain separate work.
Linux full build/regressions, weapon ASan/UBSan, Windows fixture and Windows x86
build pass. Tests cover all fields, signed/reversed ranges, out-of-range floats,
negative counts/dynamics, zero values and atomic failure. Both executables load
the default weapon's ADS/hip counts 4/4 and gun pitch ranges -85/-90 and -30/-35.
Killhouse initialization still passes native `none` and stops at the unfinished
`defaultweapon_mp` lookup; these results do not establish live recoil behavior.

Weapon-core conversion now retains starting ammo (`+55c`) and first-raise time
(`+60c`) as native `iStartAmmo` and `iFirstRaiseTime`. C1 reads the ammo field at
`0x50ffb3/0x5100d7`, and its script-facing getter reads it at `0x541cc3`; the
retained IW3 `GScr_WeaponStartAmmo` reads native `+320`. This corrects the
reference's `ammo_fix.md` claim that no such per-weapon scalar exists. Loading
the value does not choose the gameplay spawn-ammo policy or derive it from
maxAmmo minus clip size. C1's first-raise branches read `+60c` at
`0x419e94/0x419ee8`, matching the retained IW3 first-raise duration at `+3bc`.
Nonnegative integer values, including zero, are preserved without clamping;
invalid inputs leave the complete output unchanged.
Linux full build/regressions, weapon ASan/UBSan, Windows fixture and Windows x86
build pass. Both executables load the installed default weapon's starting ammo
100 and first-raise duration 3000 ms into its core. Their Killhouse runs still
pass native `none` and stop at the unfinished `defaultweapon_mp` lookup.

Weapon-core composition now maps all 19 shared hit-location multipliers and
retains CoDOL's shield multiplier separately. C1 `0x521035` reads the weapon
array at `+a4c`, then multiplies by global damage settings; these remain separate
in the port. `hitLocName[20]` at `0xcce0d0` matches IW3's interleaved right/left
limb order through gun (18), followed by shield (19). The array ends at `+a98`;
the neighboring `+a9c` value is not included. Nonfinite or negative values reject
the whole conversion; zero multipliers remain zero. This fills weapon fields
but does not yet activate the complete weapon or shield damage path.
Validation covers each of the 20 source slots, nonfinite/negative values,
neighbor exclusion, zero values and core rollback. Linux full build/regressions,
weapon ASan/UBSan, Windows fixture and Windows x86 build pass. Both executables
read `defaultweapon_mp` head/upper-torso multipliers 1.4/1.2 and gun/shield 0/0.
Their Killhouse runs continue past native `none` and still stop at the unfinished
`defaultweapon_mp` database lookup.

The engine database lookup now supplies a complete native `none` weapon from its
mounted archive. This special case follows retained
`BG_LoadDefaultWeaponDef_LoadObj`: zero gameplay fields, empty strings, the
source `noweapon.accu` graphs and sprint scale 1.75. A strict source profile
rejects nonempty dependencies, nonzero unconverted fields, changed sprint scale,
unexpected graph names and inconsistent counts. The native record and graph
allocations belong to its defining archive; cached and retired pointers survive
replacement until full unmount. Other weapon names still require conversion.
Linux and Windows Killhouse map runs now pass the `none` lookup and fail next at
`defaultweapon_mp`; this is progress through initialization, not a playable map.
Validation: full Linux build/regressions, weapon and archive ASan/UBSan checks,
Windows weapon fixture and Windows x86 server build pass. Archive tests verify
cache reuse, malformed replacement rejection, retained old pointers and unmount
cleanup. Both map logs explicitly report `CoDOL native weapon lookup: none`.

Weapon-core composition now translates source penetration class `+348` and
offhand class `+354`. C1's penetration reader `0x507cf7` and name table
`0xcd7f8c` identify none/small/medium/large. Offhand selectors
`0x421dca/0x421e20` compare `+354`; the script-string pointer table at
`0xcd49cc` orders none/frag/smoke/flash before additional classes. The frag,
smoke and flash handles are initialized via the string calls at
`0x5774c7/0x5774b3/0x57749f` and stored at `0x24ee060/05e/05c` respectively.
The four shared roles map explicitly to native enums; unsupported values reject
the core atomically. This adds definition fields, not grenade or penetration
gameplay. Weapon stance remains unconverted: the examined `+358` reads at
`0x418c66/0x422663` refer to player state, not weapon definitions.
Validation covers all 16 shared combinations, unsupported/high values, malformed
inputs and core rollback. Linux full build/regressions, weapon ASan/UBSan,
Windows fixture and Windows x86 build pass. Both server executables load the
installed `none` and `defaultweapon_mp` cores with penetration/offhand 0/0;
this does not prove grenade selection or bullet penetration during a match.

Weapon-core composition now translates source `+340` weapon type and `+34c`
inventory type using verified semantic tables. C1 readers `0x541b43/0x541b49`
index `0xcd727c` (bullet, grenade, projectile, riotshield, bomb); readers
`0x541c33/0x541c39` index `0xcd7f58` (primary, offhand, item, altmode, exclusive,
scavenger). The shared first three weapon types and four inventory roles map
explicitly to IW3 enums. Remaining roles reject the core without replacing its
output; riotshield is never mistaken for IW3 binoculars.
Weapon class conversion uses C1 `0x541ba3/0x541ba9`, which indexes `+344` through
`0xcd7f28`, whose order is rifle, sniper, mg, smg, spread, pistol, grenade,
rocketlauncher, turret, throwingknife, non-player, item. This differs from IW3
and now maps its ten shared names explicitly to IW3 class enums during core
composition. Sniper (1) and throwingknife (9) reject conversion without replacing
the previous core; they still require gameplay extensions before publication.
Class validation covers all ten shared mappings, unsupported/high values,
malformed inputs and core rollback. Linux full build/regressions, weapon
ASan/UBSan, Windows fixture and Windows x86 build pass. Both executables load
the installed `none` and `defaultweapon_mp` cores with type/inventory/class 0/0/0.
This verifies the loader component, not native weapon registration or gameplay.
Validation: all 12 shared type/inventory combinations, unsupported/high values,
malformed inputs and core rollback pass. Linux full build/regressions, weapon
ASan/UBSan, Windows fixture and Windows x86 build pass. Both executables still
load `none` and `defaultweapon_mp` with type/inventory 0/0. `frag_grenade_mp` is
absent from the startup mounts used by the Windows diagnostic, so that run does
not establish real grenade loading or gameplay behavior.

The engine weapon-core loader now binds native XAnimParts for every nonempty
animation name across all 144 source slots. Duplicate names retain their slot
positions and share the archive's cached payload; null and empty names leave null
slots. Missing, invalid, or unexpectedly null provider results reject the load
before replacing its output. Animation payloads and script-string references
remain owned by their defining archives through replacement until full unmount.
The standalone core builder retains names only; the engine loader adds these
bindings. This does not yet register complete weapons or activate animations.
Linux full build/regressions, loader ASan/UBSan, Windows fixture and Windows x86
build pass. Both server executables bind 20 populated animation slots for the
installed `defaultweapon_mp` core and zero for `none`. Tests also cover provider
failure, missing and null payloads, duplicates, gaps and clearing prior bindings.

`CODOL_LoadEngineWeaponCore` now provides a single mounted-to-native core load
operation. It resolves the winning weapon views, all eleven leading model slots,
native model providers, and engine tag handles before transactional composition.
Missing root weapons return absent; missing/invalid dependencies reject the load
without replacing an existing core. `codol_checkweapon` uses this production
loader. The core remains an intermediate record, pending complete weapon
conversion and database publication.
Validation covers failure at every dependency/provider step, absent root,
invalid arguments, conversion failure and successful replacement. Linux full
build/regressions, loader ASan/UBSan, Windows fixture and Windows x86 build pass.
Both server executables load the installed `none` and `defaultweapon_mp` cores
through this entry point; these are loader diagnostics, not match-entry tests.

The native weapon converters now assemble one owned intermediate core containing
the verified scalar fields, leading strings, model roles, animation roles, ammo
names and accuracy graphs. Full 144-slot animation and 32-slot hide-tag views and
CoDOL timing variants remain alongside the IW3 fields. Graph allocation and
replacement are transactional; failed conversion preserves the previous core.
Names, models and tag references borrow their providers' lifetimes. An engine SL
adapter supplies archive-owned weapon tag handles, and `codol_checkweapon` now
exercises the composed core on mounted assets. Unconverted fields remain pending:
this core is explicitly not a complete WeaponDef and is not registered in DB.
Validation: Linux full build/regressions, weapon-core ASan/UBSan and Windows
fixture pass; the Windows x86 server builds. Both native server executables
assemble the installed `none` and `defaultweapon_mp` cores successfully.
These diagnostic runs do not prove weapon activation or client match entry.

Weapon hide-tag binding now acquires native script-string references for all 32
source slots. The archive owns the handles, caching them by source definition,
callback pair, and context; retired archive bindings survive replacement until
full unmount. Duplicate names acquire separate references, and zero slots remain
zero even before later populated slots. Invalid strings are rejected before any
acquisition; zero or oversized handles roll back every acquired reference without
changing the output. This supplies a full CoDOL handle view; publication into a
native weapon and gameplay consumption still require integration because IW3's
weapon structure has only eight hide-tag slots.
The archive regression fixture covers acquisition failure and oversized handles
at every slot, repeated names, cache reuse, independent contexts, malformed
replacement rejection, retained old handles, gaps, and balanced unmount releases.
The full Linux build/regressions, archive ASan/UBSan run, and Windows x86 server
build pass.

Mounted weapon views now resolve all 32 hide-tag script-string indices at source
`+3c` against the weapon's defining archive. C1's consumer at
`0x422847/0x422852` establishes the field; serialized indices are not engine SL
handles. Zero entries remain absent, and all slots (including after gaps) remain
available to the composition/native-binding layer. Invalid or empty referenced
strings reject the view without changing output or falling back to an older
weapon. Borrowed names remain valid across retired archive groups until full
unmount. The archive fixture covers 32 populated slots, invalid newer indices,
absent weapons, gaps and retained old-name lifetime. `codol_checkweapon` reports
the resolved tag count. Native handle binding and IW3's smaller hide-tag array
still require integration before full weapon publication.
Linux build/regressions and the full archive ASan/UBSan fixture pass. Real Linux
startup archives resolve both `none` and `defaultweapon_mp` with zero hide tags;
populated and invalid lists are covered by the synthetic archive fixture.
The full Windows build passes and Windows startup diagnostics agree.

Native weapon loading now maps hip/ADS movement scales at source `+670/+674`
and sprint-duration scale at `+678`. C1 movement consumers `0x41023f/0x410266`
and maximum-sprint consumer `0x40e9e6` establish the roles; retained IW3
movement/footstep and sprint code consumes native `+418/+41c/+420`.
The converter preserves zero and scales above one instead of substituting
defaults or flattening player perks. Negative/nonfinite values fail atomically.
Tests cover distinct scales, values above one, malformed/truncated definitions
and zero clearing; the ASan/UBSan fixture passes. Composed-weapon overrides,
complete WeaponDef publication and live movement parity remain unfinished.
Both server builds, Linux regressions and the Windows fixture pass. Real
Linux/Windows archives agree on hip/ADS/sprint values: `none` is 0/0/1.75 and
`defaultweapon_mp` is 1/1/1.

Native weapon conversion now preserves the two serialized ADS rates at
`+a28/+a2c` directly in IW3 `fOOPosAnimLength`, whose retained ADS lerp consumes
them at `+7f8/+7fc`. C1 readers `0x418798/0x4187af` use the same per-millisecond
rates. Enable byte `+bc8` and rechamber-while-ADS byte `+bc9` map to their native
flags, based on C1 `0x418655/0x4186e1`. Integer durations are not synthesized
from rounded reciprocals, and CoDOL's reload-while-ADS behavior remains separate.
Nonfinite/negative rates and malformed boolean bytes fail atomically. The weapon
fixture verifies exact float bits, preserved duration fields, invalid inputs and
zero clearing under ASan/UBSan. Windows build and real archive diagnostics pass:
`none` is disabled with zero rates; default weapon is enabled/rechamber-enabled
with in/out rates 0.00333333341/0.00249999994 per ms. Complete WeaponDef publication
and live ADS behavior remain unverified.
Linux build/regressions and the native Windows weapon fixture pass; Linux
archive diagnostics reproduce the same ADS fields.

The configured `sv_hostname` now reaches numeric serverinfo key `2492`, consumed
by C1 `CG_ParseServerinfo` at `0x465bc1`. Both initial gamestate generation and
live serverinfo updates pass the hostname to the native producer. Values are
bounded to the client's 255-byte payload; malformed info-string delimiters and
CR/LF fail before replacing the bank. Spaces, explicit empty names and the
maximum valid length are tested. This is a CS[0] mapping, not an invented
replicated-table alias. The gamestate fixture also exposed an existing unaligned
32-bit store in `MSG_WriteLong`; an alignment-safe copy now preserves its bytes.
The isolated ASan/UBSan gamestate fixture passes after that correction.
Linux build/regressions and the full Windows server build pass. Client display
of the hostname remains unverified while match startup is incomplete.

`CODOL_RefreshServerDvars` now publishes values for existing IW3 SYSTEMINFO
cvars whose names occur in the effective CoDOL replicated table. It traverses
names at 24..223 until the first empty name (C1 applier `0x466020`), preserving
inherited names and pairing values at name+200. Unchanged inherited values create
no override; changed or explicitly empty values update the bank and send reliable
commands to primed clients with a gamestate. Unknown/nonreplicated cvars remain
untouched, and CR/LF or oversized command values are rejected. Publication is
per value; earlier successful changes remain if a later value fails. The existing
asset refresh now invokes this producer before gamestates and snapshots.
Tests cover inherited reuse, changed/empty values, explicit name termination,
unknown/private variables, invalid values and recipients without a gamestate.
ASan/UBSan and the Windows build pass. Numeric CoDOL names requiring semantic
mapping to differently named IW3 cvars are still unimplemented.
The full Linux build/regressions and native Windows publication fixture pass.

Live `SV_UserMove` now uses `CODOL_ReadUsermoveMSG` to decode the complete
movement payload before converting commands into retained IW3 input. The
decoder reads the zero-based command chain and four-word predicted-origin
trailer using CoDOL's byte/bit-pool rules. It publishes commands, finite origin,
origin time and engine read cursors together only after success. Malformed or
truncated payloads mark overflow and preserve those outputs; command count,
destination capacity and cursor bounds are checked. Existing reliable ACK/ping
bookkeeping and authentication gates remain in `SV_UserMove`; this is not an
atomic transaction over the entire client structure. Tests exercise 1, 2 and
255 commands, every truncation of the two-command payload, nonfinite origin
coordinates and insufficient capacity. The isolated ASan/UBSan fixture passes.
This change is on the live input path; it does not establish successful match
entry while weapon publication and snapshot assembly remain incomplete.
Linux build/regressions, the Windows packet fixture and the full Windows server
build pass with the live batch-decoder integration.

Playerstate and remote-player entities now share explicit eFlags conversion
for teleport (0x2), crouch (0x4), prone (0x8), dead (0x20000), and ADS (0x40000).
The reference's `spawn_delivery.py`, `entity_codec.py`, and `damage_death.md`
establish these target bits; retained SetOrigin, BG_PlayerStateToEntityState,
and the active stance/ADS definitions establish the native bits. The converter
preserves other destination bits and clears owned bits when the native state
clears them. Both player and entity composition call it. Single-bit, combined,
clearing, and composition tests cover the mappings; other flags remain unbound.

`CODOL_OverlayEngineEntity` now combines the measured trajectories, normal
model scale, entity event queue, remote-player client-info index, and missile
weapon selector in one transaction. State and event-generation clock commit
together. It requires a seed with the correct CoDOL type and explicit resolved
event parameters, preserving fields owned by model, flags, ownership and other
type-specific producers. Tests exercise all 17 ordinary types and late failure
rollback. This is a shared-field producer, not yet a complete live entity frame.

Remote-player weapons now have a dedicated
`CODOL_OverlayEnginePlayerEntityWeapons` adapter. C1 `BG_PlayerStateToEntityState`
at `0x40d154` writes the current weapon as the low word at `+0xd4`; `0x40d0fd`
writes the high word at `+0xd6`, substituting the primary weapon for inventory
type 3. Both native IDs are resolved through the registered weapon map. The
caller must provide the primary relationship explicitly, because native entity
state alone does not retain it. Tests cover distinct/current/absent pairs,
unmapped IDs, wrong entity types and atomic failure.

This corrects the older Python `entity_codec.py` label that calls `+0x80` a weapon
field. The later `bot_animation.md` and `viewmodel_notes.md` identify the packed
pair, confirmed against C1 code; `0x40d0bb` instead copies `ps+0x1b0` to `es+0x80`
conditionally on eFlags. The adapter preserves that unrelated field. This pair
is not yet wired into the live snapshot frame producer.

The mounted weapon core loader now binds the tail's projectile XModel at source
`+0x7b0` through the existing native physics/model provider. The reference's
`docs/projectiles_fix.md` identifies the missile renderer's read at C1 `0x443c0f`;
retained IW3 `G_RegisterWeapon` consumes native `projectileModel` at `+0x584`.
This dependency is separate from the eleven leading weapon models. A null source
clears the native pointer; a missing, duplicate, malformed or unresolved tail
entry rejects the load without replacing the prior core. Tests exercise native
binding, clearing, provider failure and malformed metadata. General WeaponDef
registration still requires completion of other native fields and dependencies.

`codol_checkweapon` now audits the source graph of each failed leading effect,
following runner visuals and all three effect references with name deduplication
and limits of 64 effects/256 elements. The Windows check against the supplied
startup assets identifies element 5, type 3, in each of
`muzzleflashes/pistolflash_wv_a`, `_wv_b`, and `_wv_c`; all three have one visual
and no extension bytes. The root `muzzleflashes/pistolflash` is a type-14 runner
with those three children. Type 3 now maps to native tail type 2 after comparing
C1 renderer 0x4e6020 with the retained FX_DrawElem_Tail implementation; see
CODOL_FX_TAIL.md for the evidence. Both leading effects now convert. The default weapon core still converts;
general weapon registration remains incomplete.

The mounted weapon-core loader now binds the two leading muzzle flashes to
`viewFlashEffect` and `worldFlashEffect`. It verifies source pointer/name
presence, resolves each populated slot through the native FX graph, and only
then replaces the caller's core. Null source slots clear both pointers;
missing, empty, mismatched or failed dependencies preserve the prior output.
This connects the tail-enabled world flash to the native weapon definition.
The Windows startup diagnostic confirms both bound names for defaultweapon_mp;
focused 32-bit sanitizer coverage includes a world dependency failure after a
successful view dependency. Complete weapon registration remains unfinished.

The next four FX dependencies now bind `viewShellEjectEffect`,
`worldShellEjectEffect`, `viewLastShotEjectEffect` and
`worldLastShotEjectEffect`. C1 brass selection at `0x4819d0/0x4819da` reads
the last-shot pair from +448/+44c; +440/+444 are its ordinary fallback at
`0x481a00/0x481a08`. Both pairs use the local-view predicate. This matches
the retained named `CG_EjectWeaponBrass` routine in
`tools/cod4_dasm/src/_cg_weapons.asm` (line 6436), which reads the native
last-shot pair at +214/+218 and the ordinary pair at +20c/+210.
Every source slot requires exactly one matching asset dependency entry;
wrong kinds/types, missing/duplicate entries and failed native resolution
preserve the previous core. Null slots clear their native fields.
The real Linux startup binds `shellejects/rifle_view` and `shellejects/rifle`
for both ordinary and last-shot pairs of defaultweapon_mp. Linux regressions
and focused 32-bit ASan/UBSan tests pass. This is native dependency binding,
not proof of full weapon registration or match entry.
The full Windows build and native Windows startup diagnostic also pass, with
the same four brass-effect names bound to the composed weapon definition.

`CODOL_OverlayEnginePlayerEntity` now composes shared remote-player entity
fields and the current/primary weapon pair in one transaction. It requires a
typed player seed, resolved event parameters, and the explicit gameplay primary
weapon for alternate inventory. Ordinary inventory supplies the current weapon
twice. A failed current or primary weapon mapping leaves both the caller's
entity and event-generation clock unchanged, even after shared event mapping
succeeds locally. Tests cover alternate/ordinary pairs, clears, invalid types,
client-info bounds, missing inputs, and retry after a failed weapon lookup.
The CoDOL reachability and entity serializer retain the packed weapon pair.
Full Linux regressions and the focused native fixture under ASan/UBSan pass.
The full Windows server build passes. The supplemental standalone Windows
native fixture does not link with its Linux linker-wrap setup: MinGW retains
the engine NET_SendPacket implementation and reports unresolved engine symbols,
including Sys_SendPacket. No Windows fixture execution is claimed for this change.
This is a frame-producer building block: the live snapshot writer still uses
the IW3 body pending complete native CoDOL frame production.

Live map/game configstrings now remap native match end time 11 to CoDOL 15
and native map center 12 to CoDOL 16. `SV_SetGameEndTime` and `SV_SetMapCenter`
remain native producers; `SV_SetConfigstring` routes their updates through
the CoDOL bank instead of broadcasting the IW3 indices. The existing pre-gamestate
refresh also imports both values. The measured C1 match timer consumer is
`0x466780` (reference `matchflow.py`); map-center consumer `0x467020` reads
`0x6d0d170 = configstringOffsets + 16*4`, then parses into the three position
base floats at `0x6c450c8..0x6c450d0`. Source values preserve the absolute server
time in milliseconds and the three map-center coordinates, respectively.
The production publication fixture verifies both target indices, suppression
of unchanged values, explicit clears, invalid line breaks and pre-gamestate
bank updates without premature reliable commands. It passes under 32-bit
ASan/UBSan. This supplies the client position base; complete live snapshot
production must still use the matching center in its delta context.
Full Linux/Windows server builds and Linux regressions pass. The same
production publication fixture also passes as a native Windows executable
(MinGW with link-time optimization to discard unused engine functions).

`CODOL_PrepareClientSnapshot` now derives its position base from the published
CoDOL map-center string before preparing quantized history and encoding bytes.
It parses the actual transmitted text into floats, avoiding disagreement with
the native map center when `%g` formatting loses decimal precision. The new
`CODOL_SetDeltaPositionBase` applies C1's wide-position base rule from
`entity_codec.py`, `FISTP(center + 2^-30)` with nearest/even rounding, and rejects
nonfinite or out-of-int32 results. Empty/unset centers use zero. All other
context fields are preserved; failed preparation leaves context and pending
history unchanged. The fixture exercises half-integer centers of both signs,
malformed/extra/missing coordinates, nonfinite/overflow values, and a real
client-message/history preparation with a nonzero center. The focused native
fixture passes under 32-bit ASan/UBSan. This closes the base selection gap in
the CoDOL client snapshot bridge; the full live frame producer remains pending.
Inherited CS 16 is used when no override exists; an explicit empty override
clears an inherited center. This precedence is covered by the same fixture.
Full Linux regressions (including the production send fixture) and complete
Linux/Windows server builds pass. The send fixture now links the real
configstring state used to derive the base.

`CODOL_OverlayServerModelEntity` resolves ordinary general/script-mover XModel
indices through the published model bank and writes the CoDOL selector at
`+0x98`. The Python reference's `gsc_props.py` and `g_entity.py` establish this
field and bank (CS_MODELS 1315); retained `G_DObjUpdate` writes its IW3 counterpart
at `+0x88`. Zero clears the selector. Brush entities address inline geometry
instead and are rejected by this asset adapter, as are unpublished indices,
unsupported types and mismatched seed types. Controlled publication tests cover
mapped indices, clearing, slot limits, brush rejection and unchanged output on
failure. The live frame producer still needs to call this adapter after refreshing
asset publication; this does not establish client rendering or brush support.

`CODOL_OverlayEngineEntityEventQueue` combines translated entity event IDs and
sequence with four explicitly resolved CoDOL parameters. Measured offsets
`+c4/+c8/+cc/+d0` use codec -93, the 11-bit reader at C1 `0x5a07a2`; physical
queue slot order is preserved. Parameter semantics (weapon/entity IDs and other
event-specific values) remain the caller's responsibility. Any failed event,
parameter or clock validation leaves both the complete wire state and event
clock unchanged. Tests cover 0/255/1024/2047, overflow in each slot, an invalid
event after prior successful output and clearing parameters. The isolated
ASan/UBSan fixture and Windows build pass. Live `SV_WriteSnapshotToClient`
still uses the IW3 body: full player/entity production and its CoDOL encoder
integration remain required before match entry.
The full Linux build/regressions and native Windows event-queue fixture also pass.

The playerstate bridge now translates all five IW3 reload states 7..11 to
CoDOL 8..12, including interrupted reload/start. `CODOL_OverlayEngineReloadPhase`
also translates native ordinary/empty/start/end animations 13/14/15/16 to
CoDOL 13/15/17/18 and moves restart bit `0x200` to `0x400`. Evidence is the
retained reload setters and C1 `0x419476`, `0x419605`, `0x419425`, `0x41939e`,
`0x4195ee`, plus the measured reload-end animation in alpha0022. The adapter
accepts only reload states/animations and uses the existing atomic timing
writer; secondary-hand and unrelated fields stay owned by other producers.
Tests cover all 40 state/animation/toggle combinations and reject every other
11-bit animation value. The isolated ASan/UBSan fixture passes. This producer
is not yet connected to live snapshot assembly.
Linux build/regressions, the native Windows adapter fixture and the full
Windows server build pass with the reload translation.

Weapon loading now maps ordinary reload-add time (`+5dc`), reload-start duration
(`+5ec`) and reload-start add time (`+5f0`). C1 readers `0x419242`, `0x4195f9`
and `0x41925c` establish these roles. The distinct alternate, empty and
empty-alternate add times (`+5e0/+5e4/+5e8`) are retained in the timing extension
instead of collapsed into IW3's single add-time field. The ammo converter also
loads segmented-reload byte `+bd8`, measured at C1 `0x4195de` and corresponding
to the retained IW3 start-phase gate on `+530`. Both outputs remain atomic on
invalid durations or a malformed boolean. Tests cover the new fields, malformed
values and both segmented modes. ASan/UBSan and the Windows build pass; real
Windows archives report default-weapon add time 400 ms, no start phase and no
segmented reload. Empty/alternate scheduling still needs native gameplay
integration; complete weapons are not yet published.
The full Linux build/regressions pass; Linux archive diagnostics reproduce the
same default-weapon schedule as Windows.

The native ammo converter now also supplies ordinary/start reload transfer caps
from source `+764/+768` to `iReloadAmmoAdd/iReloadStartAdd`. C1's
`PM_ReloadClip` (`0x41e4f0`) selects these fields by reload phase; retained IW3
`PM_ReloadClip` consumes its corresponding fields at `+534/+538`. Values are
preserved, including zero and caps at/above clip size, rather than clamped during
loading. Invalid signed values preserve the entire native definition. Tests
cover both caps at zero, one, below/equal/above clip capacity and INT_MAX,
malformed values and clearing a previously populated definition. The isolated
ASan/UBSan and Windows weapon fixtures pass. This does not yet publish complete
weapons or prove CoDOL reload behavior in a live match.
Linux regressions and both server builds pass. Real Linux/Windows archive
diagnostics agree: `none` has caps 0/0; `defaultweapon_mp` has caps 5/5 with
a clip capacity of 10, so preserving the cap matters for ammo transfer.

Native weapon conversion now maps the five shared trigger modes (full-auto,
single-shot and bursts of two/three/four) from CoDOL `+350`, plus its per-shot
rechamber byte at `+bc6` into IW3 `bBoltAction`. The evidence is C1's quota
dispatcher `0x41a9d0`/table `0x41aa4c`, its rechamber gate `0x418f89`, and the
retained IW3 gate on WeaponDef `+4e8`. Double-barrel mode 5 and spin-up mode 6
require gameplay extensions and fail conversion instead of silently becoming a
different firing mode. Malformed mode/boolean values fail atomically. The weapon
fixture covers all ten shared mode/rechamber combinations, preservation of
unrelated fields, unsupported modes and malformed/truncated inputs.
ASan/UBSan passes. The Windows server build and real archive diagnostics pass:
`none` and `defaultweapon_mp` both resolve to full-auto with no rechamber flag.
The full Linux build/regressions pass and Linux archive diagnostics agree.
Complete WeaponDef publication and live firing behavior remain unfinished.

Native weapon scalar conversion now includes ordinary/player damage, minimum
ordinary/player damage and both distance-falloff endpoints. These are measured
from C1's reader at `0x505c40`: source `+588/+58c/+a30/+a34/+a38/+a3c` maps to
named IW3 WeaponDef fields. The reader selects damage endpoints, computes trace
distance, then interpolates between the two ranges; the retained IW3
`Bullet_Process` consumes ordinary damage at `+34c`, minimum at `+800` and ranges
at `+808/+80c`. Conversion is atomic, rejects negative damage and nonfinite or
negative ranges, and preserves zero/equal/reversed endpoints without inventing
defaults. This is asset conversion, not proof of complete bullet behavior:
CoDOL's player-damage selection and its equal-range branch still need gameplay
integration. `codol_checkweapon` now reports these six native fields. Real Linux
startup archives produce `none` 0/0 and `defaultweapon_mp` ordinary 100/80,
player 100/30, falloff 1200/2200; `m4_mp` is absent from that startup mount.
Linux build/regressions and the isolated ASan/UBSan weapon fixture pass.
The full Windows server build and native fixture also pass; Windows startup
diagnostics reproduce the same `none` and default-weapon values.

`CODOL_TranslateEngineWeaponState` explicitly maps verified IW3 ready, firing,
rechamber and melee init/fire/end states to CoDOL: 0/5/6/12/13/14 become
0/6/7/13/14/15. Evidence comes from the retained weapon assembly and alpha0022's
measured client setters. `CODOL_OverlayEnginePrimaryWeaponPhase` combines this
translation with the existing atomic timing writer; callers still supply a
resolved CoDOL animation ID and toggle. Unsupported states preserve the output.
The fixture exercises every accepted state, all other six-bit state values and
negative/null inputs. Remaining weapon states, animation translation and live
snapshot assembly are still unfinished.
The isolated ASan/UBSan fixture, full Linux build/regressions and incremental
Windows server build pass with this translation.

`CODOL_OverlayEngineWeaponPhase` now writes primary-hand animation, weapon time,
delay and phase into the measured CoDOL playerstate fields +0x268/+0x26c/+0x270/
+0x278. Timings must fit the client's signed 16-bit fields. Gameplay supplies
resolved CoDOL state and animation IDs; native enum values are never copied.
Invalid timing/ID values preserve the prior output, and secondary-hand fields
remain separate. Tests cover normal melee timing, signed limits and invalid IDs.
Complete weapon phase-ID translation and live snapshot assembly remain unfinished.
Linux regressions/build, the isolated ASan/UBSan adapter fixture and the full
Windows server build pass.

Snapshot finalization now detects any pending frame whose message or packet
sequence no longer matches preparation. The earlier guard only caught sequence
advancement inside download handling; advancement before `SV_EndClientSnapshot`
could append another EOF and send the encoded snapshot under the wrong sequence.
The new guard forces reliable-command recovery and discards pending history.
Production send tests cover both timing cases, modified message size, overflow,
transport rejection and successful history commit. These pass on Linux; the
Windows server rebuild passes. Live CoDOL snapshot assembly remains unfinished.
The full Linux regression/build and isolated ASan/UBSan send fixture pass.

Native HUD material and localized-string ranges now participate in live
configstring publication. The server resolves names against the inherited bank,
retains stable wire slots, publishes explicit overrides to primed clients and
suppresses redundant updates for inherited values. Recycled native handles are
checked against current text; removing a native binding leaves retained wire
values intact. CR/LF and overlong reliable-command values are rejected.
`CODOL_CollectServerHud` refreshes those ranges and resolves labels, text,
materials and verified flags into complete HUD arrays. Unsupported nonzero
HUD sound IDs and unnamed flags still fail explicitly. The snapshot writer
has not yet been connected to this collector.
The production publication fixture covers inherited reuse, custom updates,
preallocated overrides, recycled/removed native indices, resolver failures and
reset. It passes ASan/UBSan and as a Windows executable. Linux regressions/build
also pass. This does not establish live client HUD rendering or match entry.
The full Windows server build passes with the publication path included.

Map startup now installs the mode's inherited configstrings immediately after
native map archives load. Server state owns this bank independently of archive
storage, exposes it read-only, rejects reinstallation until reset, and clears it
with the published override bank in `SV_ClearServer`. The lifecycle fixture
covers failed initialization, map-mode validation, repeated installation and
reset/reinitialization; it passes ASan/UBSan and on Windows.
The real Windows `mp_killhouse_sh` path installs all 2053 multiplayer constants
and reaches game initialization. It still stops at missing native `none` /
`defaultweapon_mp` weapon definitions; no match-entry success is claimed.
The full Linux regression/build passes, and Linux map startup installs the
same 2053 constants before reaching the same weapon-definition failure.

Inherited constant-configstring import and HUD allocation are now available.
`CODOL_ImportConstantConfigstrings` builds a separate owned bank from decimal
index/value rows, rejecting duplicates and invalid indices atomically.
`CODOL_RegisterHudMaterial` and `CODOL_RegisterLocalizedString` reuse effective
values before allocating a slot. Occupied inherited slots remain reserved even
if an override explicitly clears them; inherited matches create no overrides.
The banks remain separate so constants need not be retransmitted as updates.
Tests cover ownership, reuse, cleared constants, full ranges, malformed rows
and unchanged state after failures, including ASan/UBSan. All three real tables
import on Linux and resolve `white` to slot 1 with zero overrides. Live HUD
resolver/publication integration remains unfinished.
Linux regressions/build and the Windows build/standalone fixture pass. Windows
loads the three real inherited banks and reuses `white` with zero overrides too.

Mounted StringTables now resolve pooled cell strings through their owning
archive's replay blocks. Previously any unresolved cell caused rejection, so
all three shipped constant-configstring tables failed native lookup. Inline and
pooled strings now share the same case-folded, signed-byte hash validation.
Cached pooled strings retain the archive lifetime, including retired archives;
invalid references/hash mismatches fail without returning an older definition.
`codol_checkconstants <table name>` inspects the native table path. Windows
startup now loads `mp/constConfigStrings_mp.csv` (2053 rows), `_coop.csv` (1803)
and `_zm.csv` (1625), all with two columns. Inherited-slot allocation/publication
is still pending; this fix makes the source tables available for it.
Linux regression/build and the archive ASan/UBSan fixture pass. Linux startup
loads the same three tables with the same dimensions. The fixture covers cached
pooled lookup, invalid pooled hashes and retained old table strings after replacement.

`CODOL_TranslateEngineHudFlags` validates and translates the three verified
named HUD flags: foreground (1), hide-when-dead (2), hide-when-in-menu (4).
Retained IW3 setters and C1 setters 0x5242f0/0x5243d0/0x524440 agree on these
meanings. Other bits are rejected without modifying the output, including
server-only and still-unmapped waypoint/style flags. Tests cover all eight
accepted combinations and every individual unsupported bit. The full HUD
fixture passes under ASan/UBSan and as a Windows executable; the Windows server
build passes. Live material/localized-string resolution remains unfinished.

`CODOL_BuildEngineHudElement` now combines the presentation overlay with verified
HUD type/font translation and explicit CoDOL label/text/material/sound/flag
bindings. Material and timer type numbers are remapped; the four shared fonts
retain their measured identifiers. Native map-name/gametype types, additional
fonts and offscreen-material variants still require translation and are rejected.
Entity world/none sentinels become 2046/2047. Native configstring IDs and flags
are never copied as CoDOL bindings.
`CODOL_CollectEngineHud` gathers archival then current packed arrays, terminates
at `HE_TYPE_FREE`, supports all 31 slots and clears deleted tails. A supplied
resolver owns semantic bindings; any failure preserves the complete previous
output. Tests cover shared types, binding limits, unsupported variants, ordering,
full arrays, resolver failure and empty-array replacement. The isolated fixture
passes ASan/UBSan and as a native Windows executable. Live configstring/flag
resolution and snapshot publication remain unfinished.
The full Linux regression/build and Windows server build pass as well.

`CODOL_OverlayEngineHudPresentation` translates named IW3 HUD geometry, colors,
alignment, values and timing fields into CoDOL wire order. The CoDOL table at
C1 0xc39860 is exposed through `CODOL_HudFieldOffset`; it is not an IW3 memory
layout. IW3 lacks font-scale animation, so the adapter sets the previous scale
to the current scale and clears interpolation start/duration. Nonfinite floats
reject the entire overlay. Type, font, flags, target entity, text/label/material
and sound fields remain owned by their semantic/configstring adapters.
The fixture checks independent target indices, displaced fields, preserved
semantic fields and failure atomicity. This producer is not yet wired into
`SV_WriteSnapshotToClient`; live snapshot assembly remains unfinished.
Linux full regression/build and an isolated ASan/UBSan run of the HUD fixture
pass. The same fixture passes as a native Windows executable with its real
codec dependencies linked.

`CODOL_LoadMountedWeaponVisuals` now returns the four middle FX and ten material
slots that ammo-name loading previously traversed without exposing. Each slot
retains its original offset, null state, resolved name and source asset. Inline
and pooled references resolve through the catalog; named overrides are selected
after advancing over original inline data. Ammo-name loading consumes this view.
The fixture checks inline FX, inline/pooled material identity, null slots,
missing weapons, invalid aliases and retained views after archive replacement.
Linux regression/build passes; real `none` has no populated middle visuals and
`defaultweapon_mp` has seven. Both still resolve the complete tail to the exact
source-record end. Native binding of these visual roles remains unfinished.
The ASan/UBSan fixture and full Windows build pass. Windows real-default
diagnostics agree with Linux on the populated counts and final record extents.

`CODOL_BindNativeWeaponGraphs` now installs owned native accuracy-graph arrays
from the resolved weapon tail. Source names at +0x9a0/+0x9a4, active arrays at
+0x9a8/+0x9ac and original arrays at +0xbb4/+0xbb8 map to the corresponding
IW3 WeaponDef fields. Both graph sets retain their counts independently. Float
pairs are decoded from little-endian bytes into aligned allocations; names
borrow archive lifetime. Invalid/duplicate/missing fields and nonfinite points
leave the prior native definition and owned arrays unchanged.
The ASan/UBSan fixture covers unaligned input, distinct graph sets, mutable
native arrays, failed replacement and replacement with empty arrays. Windows
real-default diagnostics show `none` has 2/2 active and 2/2 original points;
`defaultweapon_mp` has 0/0 for both sets. These components are not yet published
as a complete native WeaponDef or exercised by live gameplay.
Linux full regression/build, the Windows build and standalone fixture pass;
Linux real-default diagnostics agree with the Windows graph counts.

`CODOL_LoadMountedWeaponTail` resolves all 53 trailing dependency fields after
ammo names, preserving their original header offsets and kinds. It handles
materials, physics maps, models, effects, tracer assets, strings, indirect sound
names and the four accuracy-graph point arrays in replay order. Inline extents
come from the replay catalog; named references select the winning mounted
definition. Tracers (type 40) are now catalogued for inline and directory lookup.
Point arrays retain borrowed little-endian float pairs and reject nonfinite
values. Output is atomic and requires the final cursor to equal the source size.
The regression and ASan/UBSan fixture covers interleaved graph names/points,
an inline tracer, indirect sound, missing names, invalid points and retained
views after replacement. Linux real-default diagnostics resolve 53 fields and
finish at 3119/3119 bytes for `none`, 14109/14109 for `defaultweapon_mp`.
The full Windows build and the same two real-default diagnostics also pass.
These are resolved source dependencies; native WeaponDef assembly remains open.

Native weapon translation now includes base-definition melee damage (+0x590),
delay (+0x5a0), charge delay (+0x5a4), duration (+0x5c0) and charge duration
(+0x5c4). C1's melee gate at 0x41c0f7 and initialization reads at
0x41bdb1..0x41bdd5 confirm the reference offsets. Negative values are rejected
atomically; zero remains zero. The attachment override branch remains separate
and is not replaced with base values. Melee/charge animation-name slots 7/8 now
map to native slots 7/8, confirmed by C1 dispatch and IW3 weaponDefFields.
The mapper passes ASan/UBSan. Windows startup reads real `none` as all zero and
`defaultweapon_mp` as damage 75, delay 150 ms, duration 649 ms, with zero charge
timings. This is asset translation, not proof of melee gameplay or a complete
native WeaponDef.
Linux full regression/build and the Windows build and standalone mapper fixture
pass. The real-default diagnostic also passes on Linux with the same values.

Native animations now have persistent archive-owned payloads, cached by source
definition and script-string provider. Repeated lookups reuse the pointer;
archive replacements create new payloads while retaining old payloads and string
references until full unmount. Payloads are freed before their string references.
The engine's `DB_FindXAssetHeader(ASSET_TYPE_XANIMPARTS)` now resolves these
translated records. Unsupported delta animations still fail explicitly.
The diagnostic exercises this DB path twice to check stable lookup, then samples
the retained evaluator. Cache lifetime, provider isolation, missing assets and
valid/invalid replacements pass the asset fixture under ASan/UBSan.
Full Linux and Windows builds pass. Both executables resolve the six real default
animations through this DB path and complete all 30 finite evaluation samples,
then quit cleanly. This does not establish client pose parity or match entry.

The animation consumer fixture now goes through full `XAnimCalc` leaf dispatch,
covering 8-bit and 16-bit translation indices and exact final-frame evaluation.
Its initial 8-bit fixture placed keys in the short stream; retained assembly
showed they follow the bone index in `dataByte`, while 16-bit keys follow the
count in `dataShort`. The corrected fixture checks both encodings at five times.
A shared statically assembled ABI adapter is used by the fixture and the native
`codol_checkxanim <name>` diagnostic, with no runtime patching.

The diagnostic resolves a cached native payload and builds an identity bone map, initializes
the retained evaluator constants, evaluates five times from 0 through 1, checks
finite components and releases its temporary map. Real Linux startup
archives pass for all six `viewmodel_default_*` animations: idle/fire/pullout/
putaway each have 52 bones; ADS up/down each have one. This is 30 finite pose
samples, not a comparison against client poses or a test of game-entity use.
Linux regressions/full build and the Windows dispatcher fixture pass. Broader
animation families, delta conversion and match
entry remain unfinished.
The full Windows server build and the same bounded six-animation diagnostic
pass, with matching bone counts and 30 finite samples followed by clean shutdown.

An executable consumer fixture now calls the retained IW3
`XAnimCalcParts<unsigned short>` implementation on converted native payloads
through a statically assembled test ABI adapter. It verifies constant translation,
byte-quantized translation interpolation at frames 0/64/128/192 of a 256-frame
animation, bone remapping, blend weight, ignored-bone masks and output canaries.
The standalone fixture passes on Linux and Windows. No runtime patch or hook is
used. The first interpolation probe included time 1.0 and hung; inspection of
`XAnimCalc` confirmed that exact endpoint uses a separate dispatch path. The
fixture now exercises the interpolation entry's [0,1) interval and runs under a
15-second timeout. Full dispatch and real assets are sampled above; quaternion
correctness and client-pose parity remain unverified. This is not broad
compressed-stream compatibility or match-entry proof.
The full Linux rebuild and regression suite pass with this consumer fixture.
The initial regression attempt used shared libraries left by the Windows build;
forcing their Linux rebuild resolved the toolchain link errors.

`CODOL_BuildNativeXAnim` constructs owned IW3-layout animation payloads for
sources without delta tracks. It remaps loop/bone-count/notify/asset-type fields,
copies six data streams and frame indices into aligned storage, installs copied
native bone handles, and rebuilds notify records with native names. Handles
borrow the archive's SL-reference lifetime; all payload bytes and the asset name
are independently owned. Counts, source spans, rates and notify times are checked;
invalid input or unsupported delta data leaves the previous output intact.
Delta conversion and validation of broader compressed-stream families remain
unfinished. No unsupported delta is discarded.

Linux regressions/full build and the constructor ASan/UBSan fixture pass, as does
the standalone Windows fixture. Tests cover header mapping, owned data surviving
source changes, native notify handles/times, out-of-span streams and atomic
rejection of delta/NaN inputs. With real startup archives, all 20 populated
default-weapon animation references construct native payloads. The diagnostic
immediately frees these scratch results; this is not yet animation playback or
weapon activation.
The full Windows build and bounded real-archive diagnostic also pass, producing
the same 20 native payloads and exiting cleanly.

The native `XAnimParts` declaration now names IW3's loop and delta flags at
`0x10/0x11` separately from its ten bone counts at `0x12..0x1b`. Previously the
header incorrectly described all twelve bytes as bone counts. Retained
`XAnimFillInSyncNodes_r`, `XAnimCalcDeltaTree`, `XAnimCalc` and
`XAnimResetAnimMap_r`/`Load_XAnimParts` establish these offsets. The correction
preserves the 88-byte ABI and every following field offset; no C/C++ code was
found indexing the old array. A compiled ABI fixture checks the flags, bone
counts, notify fields, pointers and two-track native delta structure against
the assembly consumers. The fixture passes Linux and Windows. This removes a
layout error before native conversion; it does not itself convert animation
payloads or prove the compressed stream formats compatible.
Linux regressions and full Linux/Windows server builds pass. The standalone
Windows ABI fixture uses static C++ runtime linkage so it runs without external
MinGW runtime DLLs.

Animation bone/notify script strings now bind through the native SL reference
system. `CODOL_BindMountedXAnimHandles` validates all source indices and resolved
texts before acquiring any handles, rejects zero/oversized handles with complete
rollback, and caches successful bindings per source asset and provider identity.
Archive replacement retains old handles; full unmount releases every acquisition.
The engine adapter uses the same SL acquire/release functions as model bones.
This prepares native names without publishing an incomplete XAnimParts object.
Fixtures cover acquisition failure after one success, oversized handles, retry,
cache reuse, separate providers, invalid notify indices and retired-cache release.
Linux regressions/full build and ASan/UBSan pass. With real startup archives,
all 20 populated default-weapon animation references now have native bone/notify
handles. Native animation payload construction and evaluation remain pending.
The full Windows build and bounded startup diagnostic pass with the same 20
ready bindings and clean process shutdown.

`CODOL_LoadMountedXAnim` now resolves replayed type-2 animation definitions by
name and traverses their complete source payload: bone indices, notifies, three
delta tracks, six data streams and frame indices. Views retain the owning zone's
script-string pool and survive archive replacement. Counts, spans and the final
asset extent are checked before replacing the caller's output. Both index widths
and constant/animated delta records are represented; the extra four-component
quaternion track is preserved. C1 replay at `0x4b7a50/0x4b7690` supplies the source
layout. IW3's retained loader uses a different bone-count offset and two delta
tracks, so these source views are explicitly not native XAnimParts.

Linux regression/full build and ASan/UBSan pass, including two-width source
fixtures, all six streams, notifies, retained third delta tracks and old views
after replacement. With the actual startup archives mounted, all 20 populated
animation-name references in `defaultweapon_mp` now resolve complete source
assets; none are missing or invalid. Script-string binding is implemented above;
native XAnim construction and engine animation evaluation remain unfinished.
The full Windows build and bounded native diagnostic pass with the same 20
resolved references. Offline inspection of the six `viewmodel_default_*` assets
in `code_post_gfx_mp.zone` finds no delta parts (four have 52 bones, ADS up/down
have one; all have one notify), which narrows the next native conversion check.

Weapon ammo-name loading now traverses the four intervening FX and ten material
references after sound arrays, using exact replayed inline extents and validating
pooled aliases. It resolves the ammo, clip and shared-cap strings at
`0x564/0x56c/0x57c`; C1's shared-cap registration at `0x41f310` confirms the last
field's role. `CODOL_ApplyNativeWeaponAmmoNames` assigns native keys and defaults
empty ammo/clip names to the internal weapon name, following the loader behavior
recorded in the reference's `weapon_spawn.py`. Empty shared-cap names remain empty.
Runtime indices and unrelated fields stay unchanged; complete registration is
still pending. Source traversal and native key fixtures pass Linux regressions
and ASan/UBSan, including inline FX/materials, pooled materials, missing names,
invalid final references, retired strings and empty-name fallback. Full Linux
build and actual startup diagnostics pass. Both startup weapons have empty source
keys and receive their internal names as native ammo/clip keys. The returned
cursors are 3,073 (`none`) and 13,982 (`defaultweapon_mp`).
The full Windows build, standalone native weapon fixture and bounded startup
diagnostic pass with matching keys and dependency cursors.

Weapon sound loading now includes both 31-entry arrays at `0x438/0x43c`.
The returned dependency cursor follows both arrays. Inline serialized arrays
consume their wrappers/names without alignment padding; pooled block-3 arrays
apply four-byte wrapper alignment and do not consume weapon bytes. Shared
resolution handles null slots and pooled wrapper/name references. A fixture
resolves the same array inline and pooled with differently sized names at its
first/last entries, exercising padding between wrappers. It also verifies
failure on an out-of-range second array preserves the previous complete result
and its retired strings. Linux regression/full build and ASan/UBSan pass.
The two real startup weapons have no populated array entries, so their cursors
remain 3,073 and 13,593; populated-array coverage currently comes from fixtures.
Native sound aliases and later weapon dependencies remain unfinished.
The full Windows build and bounded startup-weapon diagnostic pass with matching
array counts and dependency cursors.

`CODOL_LoadMountedWeaponSounds` resolves the 53 indirect sound-name slots at
`0x364..0x434`, following the leading FX dependencies. C1's `0x4b7160` loader
uses a four-byte string-pointer record, not an inline native sound alias.
Inline wrappers advance the serialized cursor; pooled wrappers resolve through
the owning archive's block 3 without consuming weapon bytes. Null slots remain
null and failed resolution preserves the whole previous output. Names borrow
archive lifetime, including retired groups. Inline/pooled, final-slot, invalid
block, absent-weapon and replacement fixtures pass Linux regressions and
ASan/UBSan. Full Linux build and real-archive diagnostic pass: `none` resolves
zero populated names with the next dependency at 3,073; `defaultweapon_mp`
resolves five, with the next dependency at 13,593. The two following sound arrays
are now handled above; native alias lookup and complete weapon registration
remain pending.
The full Windows build and bounded native diagnostic pass with matching sound
counts and dependency offsets for both startup weapons.

World-muzzle-flash type 3 now has a verified tail mapping to native type 2.
The comparison uses the renderer dispatch and velocity-aligned geometry
algorithm, documented in CODOL_FX_TAIL.md, in addition to serialization.

Native FX conversion now supports the common light element (CoDOL type 10 to
IW3 type 6, with null visual data) and runner elements (14 to 10). C1 visual
loader `0x4bcf60` resolves type 14 names through asset type 30; retained
`Load_FxElemVisuals` resolves IW3 type 10 through `Load_FxEffectDefFromName`.
Runner visuals therefore bind genuine native effect pointers, including visual
arrays, rather than copying source strings. They participate in the existing
graph transaction: all nodes must build before placeholder references are
replaced and published. Self/mutual cycles, missing children, retry, archive
replacement, null array entries and retained old graphs are covered by fixtures.
Linux regression/full build and sanitizer checks pass, including the additional
runner-array graph fixture under ASan/UBSan.

The actual default weapon's `muzzleflashes/pistolflash_view` now converts into
native FX. Its world flash now also converts: the three-visual runner binds
children `pistolflash_wv_a`, `_b` and `_c`, including their type-3 tail elements.
These are all under `muzzleflashes/`.
This is dependency conversion, not proof of weapon activation or match entry.
The earlier Windows diagnostic exposed the world-flash children; the tail
conversion and its current validation are documented in CODOL_FX_TAIL.md.

`CODOL_LoadMountedWeaponEffects` resolves the two leading FX dependencies at
`0x35c/0x360`, after models and animation names. It uses exact source extents
recorded by complete replay for inline FX, supports pooled aliases, and applies
newer named definitions without changing the original dependency cursor. Null
slots remain null; failures leave the complete previous result unchanged.
Inline/insertion-alias, override, missing-weapon, malformed-reference, null-slot
and retired-view fixtures pass Linux regressions and ASan/UBSan. The full Linux
build and real-archive diagnostic pass. The default weapon resolves
`muzzleflashes/pistolflash_view` and `muzzleflashes/pistolflash`, with the next
dependency at byte 13,499. Both initially failed native FX conversion; this loader
does not make the weapon ready for registration or activation. `none` resolves
zero effects successfully. Remaining sound/material dependencies and complete
weapon construction are still pending.
Offline inspection of their original `code_post_gfx_mp.zone` records finds
element types `[10,0,0,0,0,0,0]` and `[14]` respectively. Types 10 and 14
were initially outside the native converter's supported set; the subsequent
light/runner implementation and remaining child issue are described above.
The full Windows build and bounded native diagnostic also pass, reproducing
both resolved names, the dependency offsets and the two native-conversion failures.

`CODOL_ApplyNativeWeaponAnimationNames` maps 17 verified shared roles into IW3's
33-slot name array: idle/empty idle, hip/ADS rechamber, reload/empty reload/end,
normal drop/raise, alternate drop, quick/empty drop/raise and sprint in/loop/out.
The C1 dispatcher at `0x47be58` supplies name slots (based at `0x7c`), and the
measured state transitions in `weapon_fsm.py` identify their roles. Native slots
come from the retained IW3 `weaponDefFields` table. This deliberately preserves
unverified native slots and the complete 144-slot source view for CoDOL variants;
it does not translate network animation IDs or load XAnimParts. Distinct-slot,
null/empty and unchanged-field fixtures pass Linux ASan/UBSan. Linux regressions
and the full build pass; the mounted default weapon resolves native drop/raise
to `viewmodel_default_putaway`/`viewmodel_default_pullout`. Complete WeaponDef
registration, remaining animation roles and XAnim loading remain unfinished.
The full Windows build, standalone weapon fixture and bounded native diagnostic
also pass, with matching default-weapon names and empty names for `none`.

`CODOL_LoadMountedWeaponAnimations` now resolves all 144 serialized animation
name slots at `0x7c`, after traversing the weapon's inline model dependencies.
It shares checked inline/pooled string resolution with the leading weapon
strings, preserves null versus empty names, and returns the next dependency
offset for subsequent FX/sound traversal. First/last-slot, inline-model cursor,
malformed-reference and archive-replacement fixtures pass Linux regression checks.
The live default weapon resolves 20 populated and 121 empty slots; `none` has
zero populated and 141 empty slots (three null slots in each). Their next
dependency offsets are 13,499 and 3,073 respectively. Seventeen shared roles
are now mapped as described above; conversion/loading of XAnim assets remains
unfinished.
The asset fixture also passes AddressSanitizer/UndefinedBehaviorSanitizer. Full
Linux/Windows builds pass, and both native diagnostics report matching counts
and dependency offsets for the two startup weapons.

`CODOL_ApplyNativeWeaponSpread` maps the twelve hip-spread parameters at
`0x6b8..0x6e4` and ADS spread at `0x940` into native fields. The supplied
`docs/ballistics.md` identifies their client consumers; C1 spread interpolation
at `0x4226b0..0x422719` and stance decay at `0x418c04/35` were also inspected.
Non-finite or negative values fail without changing the target. Distinct-field,
NaN, negative and zero fixtures pass Linux sanitizers and a standalone Windows
run. All 905 inspected weapon definitions satisfy these value constraints.
This maps asset parameters only; it does not establish firing/prediction parity
or complete weapon construction. Damage-value mapping remains pending stronger
evidence, including the reference's separate script-driven damage behavior.
Linux regressions/full build pass. The live diagnostic reports zero spread for
`none`, and standing spread 0.8/7 with ADS spread 0.05 for `defaultweapon_mp`.
The full Windows build and bounded diagnostic pass with the same spread values.

`CODOL_BindNativeWeaponModels` now maps source hands (`0x10`), two indexed view
models (`0x14..0x18`) and two indexed world models (`0x1c..0x20`) into native
weapon fields. C1 reads hands at `0x47d268`, view models at `0x47c994` (with a
slot-zero fallback), and world models at `0x45c90b` / `0x5357db`; replay provides
the eleven-slot extent. The earlier eight-world-model interpretation was wrong:
the registrar at C1 `0x529b1d..0x529b78` iterates two world entries and registers
other leading references separately. All eleven resolved pointers are retained
in `core.source_models`; the six additional references are not placed in the world
array. Unused tails of IW3's sixteen-entry arrays are cleared.
Every populated reference requires a native model; failure leaves the target
unchanged. The fixture tests all roles with distinct model objects, null slots,
tail clearing and atomic rejection, and passes Linux sanitizers and a standalone
Windows run. Other weapon dependencies and full weapon publication remain pending.
Linux regressions/full build pass. Its live diagnostic binds both the null-model
`none` definition and the default weapon's three populated model slots into
their native roles, without activating either weapon.
The full Windows build and bounded diagnostic also pass with the same bindings.

`CODOL_LoadMountedWeaponModel` resolves the eleven leading source model slots
at `0x10..0x38`, walking inline model extents and resolving pooled aliases in
the weapon's owning archive before applying named overrides. Null slots and
invalid indices/references leave output unchanged. Fixtures cover inline and
pooled references to the same model, null/invalid slots and newer model overrides.
Linux regressions/full build and the asset sanitizer fixture pass.

The live default weapon resolves three source/native models: slot 0 is
`viewmodel_base_viewhands`, slot 1 is `viewmodel_default`, and slot 3 is
`defaultweapon`. The `none` weapon has no populated leading slots. These names
suggest native roles, but this resolver does not bind role fields yet. C1 also
has indexed reads from weapon+`0x1c` at `0x45c90b` and `0x5357db`; their full
role/index semantics remain to be verified before native assignment.
The full Windows build passes; its bounded diagnostic likewise resolves all
three populated default-weapon slots to native models with zero failures.

`CODOL_ApplyNativeWeaponAmmo` now maps maximum reserve (`0x574`), clip capacity
(`0xb60`) and shot/pellet count (`0x578`) into the native fields. Client consumers
at `0x41e017`, `0x41e55f` and `0x47f32e` corroborate the roles; all 127 shipped
definitions matched to the reference's measured `weapon_ammo_table.json` agree
on these offsets. Native ammo/clip registration indices and unrelated fields
remain unchanged. Timing conversion additionally maps fire time at `0xb68`,
corroborated by C1 `0x41b573` and the same 127-definition comparison.
The extended fixture passes Linux AddressSanitizer/UndefinedBehaviorSanitizer
and a standalone Windows run, including invalid-output preservation and zero
values. These scalar components are not yet complete native weapon definitions.
Linux regressions/full build pass. The native diagnostic converts
`defaultweapon_mp` to maximum ammo 100, clip capacity 10, shot count 1 and
fire time 330 ms, with indices left unregistered. An offline scan of 905 weapon
definitions finds no negative values in these four source fields.
The full Windows build and bounded diagnostic also pass, with matching ammo
and fire-time values for both startup weapons.

`CODOL_ApplyNativeWeaponTimings` maps twelve verified shared reload, rechamber
and weapon-change durations into the retained `WeaponDef`, leaving other fields
unchanged. It retains three CoDOL-only timing variants (`0x5b0`, `0x5cc`,
`0x5d8`) separately. C1 consumers at `0x4190af/ba/c9` and
`0x419361/3a3/3ee/42a` corroborate the rechamber/reload offsets; the supplied
`weapon_fsm.py` documents the weapon-change and reload-end phases.
Negative durations fail atomically, while zero durations remain zero. The native
fixture passes Linux AddressSanitizer/UndefinedBehaviorSanitizer and a standalone
Windows build/run. This is an incomplete weapon construction component; these
fields alone do not create a publishable weapon or implement the extra variants.
Linux regressions/full build pass. The live diagnostic maps the shipped default
weapon's reload to 500/500 ms, rechamber to 100 ms and drop/raise to 400/500 ms;
its separate variants are 100/2000/2000 ms. An offline directory scan of 905
weapon definitions finds no negative values in these fifteen source fields.
That scan checks the duration constraint, not full native weapon behavior.
The full Windows build passes, and its bounded native diagnostic reports the
same converted timing values for both startup weapons.

Weapon definitions (CoDOL type 28) are now recorded in the replay lookup catalog.
`CODOL_LoadMountedWeapon` returns the newest replayed serialized definition and
resolves its four leading string references, including pooled block-3 strings.
Invalid references preserve the caller's previous output; retired archive data
remains alive until full unmount. This is source access for native conversion,
not an IW3 `WeaponDef` or a substitute default weapon.

The new `codol_checkweapon` command confirms both startup definitions exist:
`none` is 3,119 bytes and `defaultweapon_mp` is 14,109 bytes. Offline inspection
of the shipped directory finds 167 nonzero words in `none`'s 0xbfc-byte header;
it must not be replaced with an empty object just to advance startup.
The live default weapon has `WEAPON_DEFAULTWEAPON` in leading string slot 2.
The reference's `weapon_spawn.py` documents separate ammo/clip registration
(C1 `0x41f200` / `0x41f3f0`, fields `0x568` / `0x570`), which still needs native
integration alongside the remaining scalar and dependency field conversion.
Linux regression/full build checks pass; actual startup still stops at weapon
loading because serialized source views are deliberately not published as native
weapons.
The weapon-view fixture also passes AddressSanitizer/UndefinedBehaviorSanitizer,
covering case-insensitive lookup, absence, invalid pooled references, valid pooled
strings, inline cursor preservation, overrides, and retained retired blocks.
The full Windows build passes, and its bounded native diagnostic resolves both
shipped startup weapons with the same sizes and leading strings as Linux.

Common-world assets (CoDOL type 16) are now recorded in the replay lookup
catalog and converted into cached native `ComWorld` objects. The 16-byte world
and 68-byte primary-light layouts match the retained IW3 loader. Conversion
owns the world name, light array and definition-name strings, preserves the
light parameters, validates finite floats and exact source extent, and retains
older cached generations until unmount. Fixtures cover two lights, null names,
cache reuse, invalid overrides and retired views.

The existing `DB_FindXAssetHeader` now publishes this translated object in
`comWorld` for both C++ and statically assembled callers. Linux regression/full
build checks pass. Actual Killhouse startup installs 30 primary lights and
reaches game initialization. It now stops on the missing native weapon `none`
and its `defaultweapon_mp` fallback, superseding the `com_map` failure below.
This does not prove gameplay or client entry, and the earlier Windows second-load
archive-remount failure remains unresolved.
The world-cache fixture passes AddressSanitizer/UndefinedBehaviorSanitizer.
The full Windows build also passes; its bounded live run installs the same
30-light world and reaches game initialization before the weapon failure.

The native collision map is now connected to `CM_LoadMapData_FastFile` in the
CoDOL build. `CODOL_BuildEngineClipMap` resolves dynamic model/FX/preset bindings
and assembles the owned clipmap using the explicit all-visible policy.
`CODOL_InstallEngineClipMap` accepts the engine's multiplayer BSP path, retains
the source MapEnts extensions and publishes the fully constructed map in `cm`.
The existing `CM_LoadMap` initializes trace-thread data and marks it in use.
`CM_Shutdown` releases native collision storage; quit clears it before archives.
Temporary construction failure leaves the installed map unchanged.

Linux regressions/full build pass. Live Killhouse construction produces 191/0
dynamic entities and 4,689 leaves. Two consecutive map-load attempts successfully
install that collision map and initialize trace data with checksum `a26a76c3`.
Startup now fails later in `Com_LoadWorld_FastFile`, whose `com_map` asset lookup
is not yet backed by a native conversion. This supersedes the missing-BSP
startup failure recorded below. Dynamic physics, CoDOL trigger/stage extensions,
script startup and client entry remain unverified/incomplete.
The full Windows build passes. Its first live Killhouse load also installs the
native map and initializes trace data, then fails at `com_map`. A second load
in the same Windows process fails earlier while remounting `mp_killhouse_sh.ff`
(asset diagnostic `4294967295`); its cause is unresolved. Linux's two successful
collision installations do not establish Windows reload correctness. Both
bounded processes exited after the checks.

Native FX conversion now supports source type-13 decals as IW3 type 9.
Each decal retains its two material handles in an owned array, including the
single-decal case, and preserves null material slots. The retained
`Load_FxElemDefVisuals` assembly confirms native type 9 uses eight-byte marks
with two material handles. The mounted graph resolver now accepts this type.
Fixtures cover one/two decals, array ownership, null slots, invalid bindings,
and a mounted model/decal effect with a real converted material.
The Linux regression/full build passes; live Killhouse inspection now constructs
all five destruction-effect reference occurrences, including the nested
`props/fire_extinguisher_ground_splat`. This supersedes the four rejected
references recorded below. Effects and dynamic entities are still not activated,
and map startup still fails before the diagnostic.
The asset and native FX fixtures pass AddressSanitizer/UndefinedBehaviorSanitizer.
The standalone Windows FX fixture and full Windows server build also pass;
bounded Windows Killhouse inspection likewise reports five native effects ready
and zero failures. No running check processes remain.

`CODOL_LoadMountedPhysicsXModel` now provides a separate native model view with
both physics dependencies resolved before publication to its caller. It shares
the static collision model's retained skeleton and mesh storage, while the
static-only view remains unchanged. Missing/invalid physics fails without
changing the output; cache generations and string-provider ownership follow
the existing model lifetime rules. `CODOL_LoadEnginePhysicsXModel` supplies the
engine string adapter. Tests cover both attached dependencies, repeated lookup,
provider mismatch, an invalid newer definition, replacement and retired views.
Linux regression checks pass. Live Killhouse inspection constructs all 199
dynamic/effect model reference occurrences with native physics attached.
The full Windows build and bounded Windows Killhouse inspection pass the same
construction checks (199 model occurrences, one native effect ready/four failed).
Both platform checks still encounter the known map-startup failure before the
diagnostic; neither proves map installation or client entry.

`CODOL_LoadEngineNativeEffect` now connects the supported native FX graph loader
to that physics-model provider. Live Killhouse inspection constructs one of five
destruction-effect reference occurrences; four remain rejected. These model and
effect objects are not yet used by active dynamic entities or physics simulation.
All four failed occurrences refer to `props/fire_extinguisher_exp`, whose
`props/fire_extinguisher_ground_splat` child contains one source type-13 decal
element. The current native graph converter explicitly rejects that visual type;
the parent's extra fields at offsets 252/256 are zero. Decal conversion remains
necessary for this graph. The model-binding fixture and real dynamic-effect
source inspection also pass AddressSanitizer/UndefinedBehaviorSanitizer checks.

`CODOL_BuildNativePhysicsMap` now constructs owned primitive `PhysGeomList`
objects and `CODOL_LoadEnginePhysicsMap` caches them through archive retirement.
Source type 1 boxes retain IW3 type 1; source type 5 cylinders become IW3 type
4. Mass, orientation, offsets, dimensions, and source map bounds are preserved.
Brush/unknown shapes, non-finite values and negative dimensions are rejected
without replacing the previous output. Tests cover multiple shapes, ownership,
malformed values, cache reuse, invalid overrides, and retired native objects.

The type numbering and matching geometry field order are corroborated by
[iw3x-port's XModel converter at b6517af](https://github.com/iw4x/iw3x-port/blob/b6517af7387a87e89e464dc5280a417e1658e89d/src/Components/Modules/IXModel.cpp#L220-L302).
That converter also reports unresolved physics problems; its existence is not
evidence of correct simulation. The retained `Phys_ObjSetCollisionFromXModel`
dispatches boxes through type 1 and the supported cylinder through its other
primitive branch. Live Linux Killhouse inspection finds 88 geometry records
across 84 references: four type-1 boxes, 84 type-5 cylinders, and no brushes.
All 84 native map constructions succeed. These are reference occurrences,
not unique-map counts. Linux regression/full build and sanitizer checks pass.
The full Windows build also passes, and its live Killhouse diagnostic reports
the same 84 successful native map constructions and 88 primitive records.
Map startup still fails before this diagnostic because the converted clipmap
has not been installed; the diagnostic does not demonstrate a playable map.
Native XModel physics activation and actual body/contact behavior remain
unverified; general brush/capsule/glass conversion and match entry are unfinished.

`CODOL_BuildUnculledNativeClipMap` supplies an explicit conservative visibility
policy: every leaf belongs to cluster 0, `vised` is false, and the single
eight-byte visibility row is all FF. This follows the retained loader's
absent-PVS fallback and its 64-cluster row rounding, with an explicit cluster
assignment for CoDOL's clusterless leaf format. It disables visibility culling
and can increase snapshot traffic; it is not recovered CoDOL PVS data. The
original constructor still accepts translated visibility when available.
Tests exercise the policy through retained leaf/PVS functions, ownership and
failed replacement. Linux regression, full Linux/Windows builds and sanitizer checks pass.
The fallback is available to construction but is not installed into `cm` yet.

The Killhouse diagnostic now audits model physics dependencies as well:
191 dynamic model uses plus eight effect model uses have 199 preset references
and 84 physics-map references, with zero failed geometry reads on both Linux
and Windows. These are
reference occurrences, not counts of unique definitions. Native physics-map
conversion remains necessary; substituting box shapes would discard real
dependencies. Real map startup and match entry remain unfinished.

Combined collision staging now preserves the uint32 at header offset `0xcc`,
and native clipmap assembly uses that staged value instead of accepting a
caller-supplied checksum. The checksum interpretation is corroborated by the
[IW4x clipMap declaration](https://github.com/iw4x/iw4x-client/blob/main/src/Game/Structs.hpp#L3176-L3226):
the field follows the same dynamic-entity arrays whose offsets are verified in
C1's `0x4bf410` loader. This is layout evidence, not a recovered CoDOL checksum
consumer or a checksum-generation algorithm. It is separate from the existing
configstring-table checksum. All 19 collision fixtures preserve the source
value exactly; native assembly verifies a high-bit checksum and passes
sanitizers. Linux regression and full Linux/Windows builds pass. Killhouse's
diagnostics on both platforms report `0xa26a76c3`; map startup remains incomplete.

`CODOL_BuildNativeClipMap` now assembles the converted brushes, terrain, leaves,
materials/static models, common entity text, and bound dynamic definitions and
runtime arrays into a single owned `clipMap_t` container. Native dependency
objects remain borrowed. Callers must supply explicit PVS storage,
and leaf-cluster assignments; missing or inconsistent visibility is rejected.
Cross-component material/BSP references are checked, including forward-only
BSP links. Owned pointers survive source-buffer changes and successful
replacement; failures preserve the previous object. The result remains
uninstalled (`isInUse == 0`); thread initialization and physics activation are
separate operations. CoDOL trigger/stage extensions remain a separate startup
consumer and must be retained by the caller.

Synthetic assembly tests exercise retained `CM_PointLeafnum`, `CM_LeafCluster`,
`CM_ClusterPVS`, `CM_NumInlineModels`, and `CM_EntityString` against the assembled
object, including both PVS modes, source ownership, invalid visibility,
cyclic/out-of-range BSP links, and missing dynamic bindings. Linux regression,
full Linux/Windows builds, and address/undefined-behavior sanitizer checks pass. This does not
prove real-map installation: the real visibility mapping, complete
dynamic native bindings, and trigger startup remain unresolved. A standalone
Windows consumer fixture failed to link unused engine functions; no standalone
Windows fixture success is claimed.

Collision leaf staging and native conversion now retain an owned leaf-surface
array and count. Like retained `CMod_LoadLeafSurfaces`, the conversion preserves
32-bit values without inventing a renderer-index limit. Success replaces the
previous owned arrays; failures preserve them. Fixtures exercise non-empty
arrays, high-bit values, truncation, ownership, and replacement. All 19 shipped
collision fixtures pass, but all have **zero** leaf-surface entries: non-empty
coverage is synthetic. Linux regression and decoder/native sanitizer checks
pass, as do full Linux/Windows builds. Killhouse diagnostics on both platforms
report zero leaf surfaces and still fail map startup before clipmap publication. Leaf-surface
content is therefore not the current blocker for these inspected maps.

`CODOL_BuildNativeCollisionAssets` creates owned native material and static-model
arrays from collision staging, retaining borrowed XModel dependencies. The
retained loader confirms 72-byte materials and 80-byte static-model records;
`CM_TraceStaticModel` consumes the converted origin/axis at offsets 8/20.
Conversion rejects unresolved references, missing models, non-finite transforms,
inverted bounds, and unterminated or empty material names. Failure preserves
the previous result. Tests cover multi-record layout, ownership, malformed
staging, and replacement; address/undefined-behavior sanitizers pass. The
`codol_checkcollision` command now checks this conversion against mounted data.
Full Linux/Windows builds and Linux regression tests pass. Real Killhouse
diagnostics on both platforms convert 1,165 materials and 3,575 static models.
Both map commands still fail at clipmap/BSP loading before the diagnostic;
these arrays are not yet aggregated into or published as a complete clipmap.

`CODOL_LoadMountedPhysicsMap` now resolves the newest named collision map,
including inline definitions, and retains a stable decoded view until unmount.
Archive replacement keeps older borrowed views alive; a malformed newer map
fails without falling back. The decoder now reads finite center-of-mass,
inertia-moment, and inertia-product values at header offsets 12, 24, and 36.
C1 `0x658be0` passes header+12 to `0x658b50`; `0x658030` uses the latter two
vectors for the ODE tensor diagonal and off-diagonal entries. Source values
are preserved without applying runtime scaling or fallback values. Fixtures
cover all nine fields with NaN/infinity rejection, cache identity, replacement,
and invalid overrides. Linux regression and sanitizer checks pass, together
with full Linux/Windows builds. The mounted multiplayer check loads and caches
all 12 collision-map dependencies, with 6,480 models and 22,988 material
references completing without failure. CoDOL's
consumer passes a whole map into a compound collider, while retained IW3
`Phys_ObjSetCollisionFromXModel` adds its geometries individually. Native
collider conversion and behavioral equivalence remain unverified.

Physics collision maps now have a C source decoder in `codol_physics.c`, beyond
the existing extent traversal. It exposes the 72-byte header, 68-byte geometry
and brush records, 8-byte sides, adjacency bytes, and inline or bounded pooled
20-byte planes. Descriptor arrays are owned; byte views borrow the archive.
Failed decoding preserves the previous output, and successful replacement
releases its descriptors. Fixtures cover every truncation of a two-geometry
map, inline and pooled plane arrays, invalid blocks, short pools, and empty
maps. Linux regression and address/undefined-behavior sanitizer checks pass,
as do full Linux and Windows builds. The mounted multiplayer corpus decodes
all 12 physics collision-map dependencies, alongside 6,480 models, 22,988
material references, and 64 native common-field physics presets without failure.
This is a source representation: native geometry-type, mass, and brush-contents
conversion and physics simulation integration remain unfinished.

Native model cores now preserve CoDOL's flags byte instead of leaving it zero.
C1's model diagnostic at `0x4374ba` reads byte `0x12b` and prints it using
`flags = %d`; byte `0x15d` is separately identified as load-on-demand flags.
The decoded geometry retains the flags, and native binding checks the byte
range before placing it at the retained `XModel.flags` offset `0xd0`.
The unchanged assembly `XModelGetFlags` is tested for all 256 byte values via
a separate ELF test section. Fixtures distinguish model flags from demand-load
metadata and verify atomic rejection of an out-of-range staged value. All
15,040 corpus model flag bytes match their source (0: 1,660; 4: 13,375;
12: 2; 2: 1; 8: 2), with all 90 archives replaying successfully. Linux tests
and full Linux/Windows builds pass; real checks on both platforms construct 3,575/3,575 static
models. General model memory/streaming/physics metadata and publication remain
unfinished; preserving flags alone does not complete that path.

Mounted native-effect loading now constructs supported nested graphs as an
atomic transaction. It resolves native materials through the archive cache,
requires an explicit native XModel provider, and handles self/mutual effect
references without exposing temporary pointers. Only after every graph member
has final storage are references patched and cache entries published. Failure
frees the pending native graph and preserves the caller's output; valid decoded
source/material caches remain archive-owned. Cache keys include mounted
generation, model provider and context, retaining old graph pointers until
unmount. Fixtures cover cycles, missing-child retries, generation replacement,
provider failures/changes, real native material handles and cleanup under
AddressSanitizer/UBSan. Linux tests and full Linux/Windows builds pass. The API does not register FX in
the global engine database; general native model integration and unsupported
FX forms remain required before complete map publication.

Native FX construction now owns one contiguous allocation containing the
32-byte effect header, 252-byte elements, sample arrays, visual pointer arrays
and copied names/sound strings. Its `totalSize` records that owned allocation;
the source-declared `totalSize` remains available separately. ABI checks cover element
stride, visual type, samples, visuals, nested-effect references and trail offsets.
The constructor translates verified source forms 0/9/12 to native 0/5/8,
requires supplied native material/model/effect dependencies, and rejects other
types, extension records and unconverted CoDOL tail fields explicitly. Tests
cover ownership, multi-visual arrays, type translation, binding/count failures
and atomic replacement; AddressSanitizer and UBSan pass. Linux tests and full
Linux/Windows builds pass, and the constructor fixture also runs on Windows.
This constructor is not yet connected to mounted native effect publication:
general FX model binding and remaining element forms still require work.

Mounted effects now cache decoded source descriptors by their winning archive
definition. Model/material visual lookup resolves inline or pooled references
against the effect's owning archive, then applies current named overrides.
Decal slots address both materials; sound/runner/light entries remain explicit
non-asset visuals. Cached descriptors and older borrowed views survive group
replacement until unmount. Fixtures verify repeated lookup, material overrides,
new effect generations, invalid indices and malformed newer definitions without
fallback or output mutation; the native asset fixture suite passes ASan.
Killhouse's five effect references resolve all eight model visuals and twenty
material visuals with no missing dependencies, also verified through real
Linux and Windows server diagnostics. Linux tests and both builds pass. These remain source bindings;
native FX construction and clipMap installation are unfinished.

Effect-source decoding now traverses the complete serialized extent: velocity
and visual samples, inline model/material dependencies, visual arrays and decal
pairs, sound/runner strings, nested effect names, trail geometry and other
extension records, plus the extra CoDOL string. Descriptor arrays are owned;
payloads remain borrowed from retained archives. Invalid/truncated input leaves
prior output intact, and replacement/destruction frees partial descriptors.
Fixtures cover nested inline assets, pooled names, samples, trail arrays,
extensions and every truncation of a representative effect. The full native
asset fixture suite passes AddressSanitizer. Across 90 archives,
`--effect-sources` decodes 2,873 effects containing 14,867 elements without
failures; `--dynamic-effects` also traverses all five Killhouse dependencies.
Linux tests and full Linux/Windows builds pass. This resolves source traversal, not native FX layout,
visual type mapping, runtime dependency binding or clipMap installation.

Effect-prefix decoding now validates inline/pooled names, signed count limits,
the contiguous 260-byte element span and the offset where nested dependencies
begin. It returns borrowed source views, preserves output on failure, and
does not reinterpret elements as native records. Fixtures cover malformed
counts/spans, missing element storage, pooled-name termination and atomicity.
The new `test_codol_assets --dynamic-effects <map> <zones...>` inspection path
uses real mounted dependency resolution. Killhouse's five references resolve
to two definitions: four `props/fire_extinguisher_exp` references (six elements
each) and one `props/coffeemug_des` reference (five elements). Their element
types are 0, 9 and 12 (material, model and sound visual loaders); none has an
extension record. These observations identify the next native conversion
targets; sample arrays, visual binding and remaining fields are not yet
converted. Linux tests and full Linux/Windows builds pass.

Effect replay now retains typed model/material aliases for single element
visuals, visual arrays and both materials of decal pairs. References identify
the actual pointer slots in loader block 3, rather than serialized file offsets;
sound/runner strings and light visuals are not misclassified as materials.
A fixture verifies exact slots and complete inline dependency extents across
all three visual forms. Linux tests, full Linux/Windows builds and all 90 archive replays pass,
including 2,873 standalone effects. Native FX conversion remains pending:
the retained element stride is 252 bytes versus CoDOL's 260, and visual type
IDs differ (for example, native model 5 versus CoDOL 9). These aliases supply
dependencies for that conversion, not empty substitutes for effect objects.

Native dynamic-entity construction now owns the runtime arrays alongside its
definitions: 32-byte poses, 12-byte clients and 20-byte collision records for
each category. Allocation and zero initialization match retained
`DynEnt_LoadEntities`, its array accessors and CoDOL runtime block replay.
Construction keeps prior output intact on failure and frees all arrays on
replacement or destruction. Fixtures exercise both categories, multi-record
extents, writable independent storage, zeroed replacement and empty-state
cleanup; AddressSanitizer, Linux tests and full Linux/Windows builds pass.
This is the loader's initial runtime storage,
not engine activation or an installed clipMap.

The retained `DynEntityDef` is now a typed 96-byte structure, with ABI checks
for model, destroyed-pieces, physics, health, mass and contents offsets. An owned
converter maps decoded CoDOL definitions into this layout, inserts a null
destroyed-pieces pointer (absent from CoDOL), and requires a native dependency
for every nonnull source reference. It rejects unsupported types, mismatched
bindings, oversized categories and nonfinite values without replacing a prior
result. Fixtures cover both categories, field placement, borrowed dependency
identity, source independence, replacement and cleanup under AddressSanitizer.
C1's table at `0xc3cb84` has the same clutter/destructible flags as retained
`dynEntProps` (0x00010001 and 0x01010001); consumers reference the table's flag
bytes at `0x4de8bc`, `0x4e1a0e`, `0x4dfc7d` and `0x4dfce0` (operand addresses).
All 90 archives replay, yielding 8,885 clutter and 1,999 destructible definitions
with no unsupported types. Linux tests and full Linux/Windows builds pass. Complete native dependency
binding, runtime dynamic arrays and clipMap installation are still pending;
the converter does not fabricate effect/model objects to bypass those steps.

Native physics presets now have an archive-owned cache keyed by the winning
serialized definition. Named lookup returns a stable native pointer, copies
the preset's strings, retains extension data, and excludes temporary loader
block 0. Map-group replacement selects new definitions while existing native
pointers remain valid until unmount. Tests exercise repeat lookup, replacement,
retired-object lifetime, missing/invalid names and atomic rejection of a newer
nonfinite preset without older fallback. The Linux suite and full Linux/Windows
builds pass. Real diagnostics on both platforms construct all 191 Killhouse presets with
zero failures. Only verified common fields and the cylinder fallback flag are
applied; CoDOL extension parameters, complete dynamic entities and clipMap
publication still require integration.

Dynamic model, effect and physics-preset dependencies now resolve through their
own collision archive's pointer aliases and the mounted set's newest named
definitions. FX replay retains directory, insertion and inline dynamic-field
aliases, including name-only references that must resolve to another archive.
The API returns borrowed source assets and persistent block views; it does not
cast source records to engine pointers. Tests cover effect insertion/field
aliases, type mismatches, null dependencies, invalid category/index/type,
unchanged outputs on failure, and newer FX overrides with older views retained.
The Linux suite, full Linux/Windows builds and all 90 archive replays pass.
Real Linux and Windows Killhouse checks resolve 191 dynamic models, 5 effects
and 191 presets with zero unresolved
references. These source definitions still require native object construction
and integration before clipMap publication.

Dynamic-entity decoding now retains CoDOL's 92-byte records from complete
archive replay and owns their type, pose, brush-model indices, health, mass,
contents and model/effect/physics references. The retained IW3 definition is
96 bytes: it inserts a destroyed-pieces pointer before the physics preset.
These records are therefore decoded explicitly, not cast to native definitions.
Replay catalogues each category against its exact collision owner and captures
inline dynamic-model pointer aliases. Invalid extents and nonfinite pose/mass
data fail without replacing the prior result. Fixtures cover both categories,
alias resolution, owner mismatch, failure atomicity and source-independent
lifetime; the Python loader-state mirror includes the new catalogue fields.
All 90 real archives replay successfully, and their 19 collision assets decode
10,884 category-0 definitions (none in category 1). Linux tests and full
Linux/Windows builds pass. Real server diagnostics on both platforms decode
all 191 Killhouse definitions through the mounted archive API. Native dynamic
model/effect/physics binding and type translation remain pending, as do clipMap
publication and visibility; normal map loading still fails before match entry.

Native leaf and inline-brush-model construction now owns the retained 44-byte
leaf and 72-byte model records, preserving bounds, contents, brush-tree/AABB
references and cluster values. It rejects invalid references and model counts
that would consume the reserved temporary-box handle. Fixtures check source
independence, atomic replacement/failure, retained inline-model counting and
AddressSanitizer cleanup. Visibility is still unresolved (`cluster == -1`);
no visibility data is fabricated by this conversion.
Linux `test-codol` and full Linux/Windows builds pass. Bounded real server
checks on both platforms convert all 4,689 Killhouse leaves and 338 inline
models; neither check installs the resulting map.
Inspection of Killhouse's serialized collision header also confirms 191
dynamic-entity definitions in category 0 (count at byte 168, traversed by the
native loader). These remain required dependencies before full map publication;
successful static geometry conversion does not account for them.

Native terrain construction now owns vertices, triangle indices, walkability
bits, borders, partitions and AABB nodes. Partition border spans are checked and
relocated; triangle/partition ranges, walkability extent and forward-only AABB
links are validated before replacing an existing result. Dedicated ABI checks
cover partition stride/pointer offset and the native AABB field ordering.
Fixtures check ownership after source mutation and atomic rejection of broken
references/ranges/cycles, including an AddressSanitizer run. This terrain is
construction data for the native clipMap, not a published map or match load.
Bounded live Linux and Windows Killhouse checks convert 36,436 triangles, 4,279
partitions and 10,073 AABB nodes alongside the existing model/brush conversion.
Linux `test-codol` and full Linux/Windows builds pass.

Native brush construction now owns its planes, sides, edge bytes, BSP nodes,
aligned brushes, leaf-brush nodes and index arrays. Pointer spans are checked
and relocated into the new allocations, so decoded collision staging can be
released independently. The builder adds the spare brush/index/tree node and
initializes the temporary box hull following retained `CM_InitBoxHull`.
Tests cover relocation, source independence, atomic failure, alignment and the
actual `CM_TempBoxModel` function. Bounded live Linux and Windows Killhouse checks convert
27,672 brushes and 23,947 tree nodes including the box hull. The native brush
result remains separate from the published clipMap; visibility, complete map
metadata/dependencies and engine installation are still pending.
Linux `test-codol`, full Linux/Windows builds and the brush ownership fixture
under AddressSanitizer pass.

The archive registry now owns assembled native collision XModels: skeleton,
triangle descriptors, active LOD meshes and dedicated material handles. Bone
strings use the engine SL adapter, and repeated lookups reuse the same object
within a mounted generation. Failed construction preserves the caller's output;
group replacement creates a new object while retired generations retain old
borrowed models until full unmount. Fixtures cover reuse, provider mismatch,
missing materials, successive group replacements and failed replacement.
These objects are for static collision consumers; general DB XModel publication
and dynamic physics remain unfinished.
`CODOL_LoadEngineCollisionMap` binds these models into owned collision staging.
The `codol_checkcollision <mounted map basename>` console command exercises this
path without installing a clipMap. A bounded real server run, using the nine
startup and six Killhouse map/gametype archives plus original IWD files,
reported 3,575/3,575 native models and zero unresolved materials on two successive
checks, then exited normally. This was verified in both Linux and native Windows
server runs; Windows output was captured with `+set logfile 2` in a temporary
home directory. Linux `test-codol` and full Linux/Windows builds pass.
The standalone `--native-collision <streamed-model
directory> <map> <zone>...` check also binds every instance and verifies release
of all 494 acquired bone-string references. Normal map startup still stops at
the missing published `col_map_mp`; visibility, other collision dependencies
and map/script startup still require integration.

Native model collision descriptors now match the retained `XModelTraceLine`
assembly ABI: 44 bytes, with triangle pointer/count at offsets 0/4, bounds at
8/20, bone index at 32, contents at 36 and surface flags at 40. The previous
36-byte C declaration omitted the triangle fields and could not be passed to
the tracer. Native core conversion now binds the owned geometry's 48-byte
triangle arrays and rejects missing arrays or counts outside signed-int range.
Core destruction frees descriptors; borrowed triangles remain geometry-owned.
A new fixture calls the actual retained assembly tracer and production box
helpers, checking a hit on the second descriptor's second triangle (both
record strides), fraction/normal/flags,
contents filtering, back-face/outside-triangle misses and disabled collision.
The assembly function has its own ELF text section for fixture linking;
its instructions are unchanged. General model and clipMap publication remain
unfinished; this fixes a required runtime ABI before that integration.
Linux `test-codol` and full Linux/Windows builds pass with the corrected ABI.

Static-model collision binding now has a native name-based resolver adapter.
Runtime replay retains typed XModel aliases for directory entries, insertion
slots and graphics-world static-model pointer fields. Killhouse's 3,575
references use the latter fields; resolving only directory aliases is
insufficient. Model lookup now includes real definitions embedded inside other
assets, with newest-archive/last-definition precedence and reference-only
comma names excluded from overriding definitions. The adapter removes that
comma before invoking the caller's native model resolver; failed resolution
retains the encoded dependency and never creates a placeholder model.
Fixtures cover directory/insertion/world aliases, type rejection, canonical
names, caller-owned binding, unresolved results, and a world-embedded model
without a top-level XModel entry. With all nine startup archives and six
gametype/map archives mounted, Killhouse resolves all 3,575 instances to names,
skeletons and collision geometry. The map and patch alone resolve 3,376;
shared archives supply the remaining dependencies. This does not yet bind
fully constructed native XModels or publish engine collision/visibility.
Linux `test-codol` and full Linux/Windows builds pass. The six-zone MP model
regression also passes: 6,480 models/meshes, 22,988 material bindings, 64 physics
presets and 12 physics maps, with zero failures.

Mounted collision staging now resolves pooled material names from the owning
archive's replayed block 3. The bounded string resolver rejects sentinels,
scratch/runtime blocks, unwritten capacity and unterminated strings. A native
mount fixture checks pooled-name resolution and ownership after unmount.
The real `mp_killhouse_sh.zone` stages 1,165 materials with zero unresolved
names, 27,672 brushes and 4,689 leaves. All 3,575 static-model references still
need native XModel binding; visibility and engine clipMap publication remain
unfinished. This is decoded collision data, not a successful map load.
The asset fixture runner's `--mounted-collision <map> <zone>...` mode exercises
production runtime mounting and reports these dependencies explicitly.
Linux `test-codol`, full Linux/Windows builds, and the Killhouse staging check
with and without its patch pass. These checks do not validate match entry.

Normal map initialization now mounts the CoDOL gametype/localized-gametype and
map fastfiles, with available patches loaded after each base. Co-op mission
names also load their base map. This replaces the retained map-zone load call
in the CoDOL branch. A bounded real `mp_killhouse_sh` attempt mounted six map
archives and issued no legacy map-zone request. It still stops at the request
for a native `col_map_mp` object, whose engine publication remains unfinished.
The registry supports atomic replacement of a nonzero logical archive group:
all new files validate before old group members leave active lookup. Startup
archives remain active. Retired archives preserve already-borrowed objects until
full unmount/shutdown, so memory for prior maps remains resident in this phase.
Fixtures check fallback to startup assets after replacement, exclusion of old
map overrides, borrowed-cache lifetime, a later-file failure after staging an
earlier file, and complete cleanup. Reclamation at map teardown and end-to-end
map rotation still require runtime integration.
Linux `test-codol` and full Linux/Windows builds pass with grouped map mounting.

Fastfile discovery now uses the same CoDOL path resolver as startup mounting
for the default archive directory. Both honor `codol_zonePath` and otherwise
resolve `client_shipRetail/<language>/<name>.ff`. The bounded resolver rejects
invalid basename/language tokens and preserves the output buffer on failure;
fixtures exercise default/override paths, traversal, extensions and truncation.
A real `map mp_killhouse_sh` request passes discovery and enters map
initialization. At this earlier stage it failed in the retained map-zone loader;
native map mounting above supersedes that failure. Collision-map publication
still must be connected before this can load a match.
Linux `test-codol` and full Linux/Windows builds pass with the shared path resolver.

The CoDOL `R_Init` branch now mounts nine dedicated startup fastfiles through
the native signed-container reader and block replay: default/code-post-gfx,
code-post-gfx patch, localized code-post-gfx and patch, common and patch,
localized common and patch. Bases precede patches in the registry's override
order. The directory defaults to `fs_basepath/client_shipRetail/<language>`;
`+set codol_zonePath <directory>` overrides it. Key extraction uses the existing
`codol_clientExe` setting or `fs_basepath/C1.exe`. The complete set mounts
atomically. DB pool initialization is shared with the retained loader, so it
will not be repeated on a later DB load. IW4OL startup remains on its old branch.
A bounded Linux startup against the real installation mounted all nine archives,
completed common initialization and quit without legacy startup-zone requests
or a `cod4x_patchv2` request. A subsequent bounded `map mp_killhouse_sh` request
still failed the legacy map-discovery check; map-zone loading, runtime asset
publication, VM startup and match entry remain unfinished.
Linux `test-codol` and full Linux/Windows builds pass with the native startup branch.

The Linux filesystem enumerators now use explicit `readdir64`/`stat64`
interfaces. On this 32-bit server, the CoDOL installation's WSL-mounted volume
returned `EOVERFLOW` from legacy `readdir` and `stat`, causing startup to index
zero IWD files. The local 32-bit probe reproduced both failures. The updated
bounded server startup indexes 42,246 IWD entries from the installation.
Exported engine structure layouts are unchanged; the obsolete local stat guard
padding was removed in favor of the correctly sized libc structure. Linux
`test-codol` and the full build pass. This is a Unix-only change.
That initial filesystem check still requested legacy zones and `cod4x_patchv2`;
the later native startup branch above removes those startup requests. Both
checks used `+quit` and are not evidence of map loading or match entry.

Model caches now record the mounted-archive generation. After a successful
mount, new lookups rebuild the model's dependency views against the current
archive set; earlier borrowed models, surfaces and bone handles stay owned until
unmount. Failed mounts leave cache identity unchanged. Surface resolution also
selects the newest real named definition when the original reference was a
full definition rather than a comma stub. This prevents patch-only surface
overrides from leaving a cached older model on obsolete geometry. A native
fixture mounts a surface-only patch after caching a stub-backed model, verifies
the new surface byte and defining blocks, checks the old view remains readable,
and tests that a subsequent malformed mount preserves the current cached view.
Normal DB zone startup/unload integration remains unfinished.
Linux tests and full Linux/Windows builds pass. The mounted MP corpus checks
6,480 model/mesh, 22,988 material, 64 preset and 12 physics-map lookups with
zero failures after the cache/override changes.

Map initialization now publishes native northyaw (822) and minimap (823) at
CoDOL 1302 and 1303, both in gamestate refresh and live updates. Native
`SP_worldspawn` writes 0x336 and `GScr_SetMiniMap` writes 0x337 using the same
raw-angle / quoted-material-and-four-floats formats consumed by C1 `0x450e21`
and `0x43db30`. Native 824 is `Scr_VisionSetNaked`, so it is deliberately not
treated as CoDOL's optional second minimap at 1304. Empty values explicitly
clear the translated slots. Fixtures cover exact quoted text, stable refresh,
removal, invalid multiline values and the adjacent unmapped vision slot.
Runtime map drawing remains unverified while native map/script startup is
still being integrated.
Linux `test-codol` and full Linux/Windows builds pass with map configstring publication.

Native sound names now publish at `3395 + native sound index` during gamestate
refresh and live configstring changes. The sound range is consumed by the
CoDOL dispatcher, preventing legacy sound updates from writing into CoDOL model
slots. C1 LocalSound `0x468765` resolves the alias name through that configstring
at playback time; indices are therefore preserved, including replacements.
The retained engine supplies indices 1..255 within the client's 1..256 range.
Removal sends an explicit empty string; unchanged names send no duplicate.
Fixtures cover the highest native index, replacement, malformed aliases,
removal, range boundaries and absence of a write at the IW3 index. This does
not yet verify actual client audio playback or complete sound-event payloads.
Linux `test-codol` and final Linux/Windows builds pass with sound publication.

Live retained model/tag configstring changes now dispatch to the CoDOL asset
publisher and return before the legacy IW3-index broadcast. The native string
bank is still updated first; startup changes are published by the gamestate
refresh. This prevents a translated model/tag announcement from being followed
by a second write into an unrelated CoDOL slot. Invalid asset names fail the
publication instead of falling through to the raw-index path. Native fixture
coverage includes each range boundary, translated destinations, reserved slots,
invalid names and removal without recycling stable wire names. Other native
configstring ranges still need explicit translation before full publication.
Linux `test-codol` and full Linux/Windows builds pass with this routing change;
live client application of these updates has not yet been verified.

Initial and live serverinfo publication now use one CoDOL formatter and include
numeric key `2485` with the configured `sv_maxclients`. C1 `0x465f57` loads
the literal at `0xc44704` and stores its parsed value at `cgs+0x168`; sending
only the IW3 name does not satisfy this reader. The CoDOL server registration
now caps clients at 18, matching the reference's measured C1 dvar domain 1..18.
The existing default remains 16; the IW4OL build retains its original 64 limit.
Gamestate rejects invalid limits and client slots outside the advertised count.
Live CS0 updates format the CoDOL bank after updating the retained native bank;
startup updates continue to defer network publication until game state is ready.
Tests cover the numeric key, invalid counts and the highest valid client slot.
Other serverinfo/systeminfo keys and general replicated-dvar production remain
unfinished, as does translation of other retained configstring update ranges.
Linux `test-codol` and final Linux/Windows builds pass. Live client parsing and
match entry still need runtime verification.

The predictable-player event adapter now maps four native IDs and explicitly
resolved CoDOL parameters into the primary player queue (`0xf0`, `0xf4..0x100`,
`0x104..0x110`). It shares the validated 8-to-11-bit counter expansion with the
entity adapter, but requires a separate per-player clock. It rejects unsupported
IDs, parameters above 2047 and inconsistent clock state atomically. Fixtures
cover skipped samples across 255-to-0, parameter limits and preservation of
other counters. No IW3 event parameter array is copied implicitly.
Direct inspection of C1 `0x45d723..0x45d778` establishes that the second event
loop consumes the counter at **0x118**, with events at 0x120 and parameters at
0x130. This corrects alpha0022's comment calling 0x114 the second queue's
sequence. The adapter leaves 0x114, 0x118 and the secondary queue untouched.
Semantic parameter producers and live clock lifecycle integration remain pending.
Linux `test-codol` and full Linux/Windows server builds pass with the player
adapter and shared clock validation; no live match-entry result is implied.

Entity snapshot event translation now maps the four retained IW3 event IDs
and expands the engine's 8-bit event counter into CoDOL's 11-bit counter.
`G_AddEvent_10` writes integer event words through the legacy `vec4_t` member
and masks its counter with `0xff`; the adapter reads those words without float
conversion. The measured entity table places the CoDOL counter at `0xb0`
(codec `-75`) and four event IDs at `0xb4..0xc0` (codec `-94`). A per-entity
clock handles 255-to-256 and 2047-to-0 transitions independently of ACKs.
Invalid input or an unsupported event leaves both clock and wire state intact.
Fixtures cover both rollovers, duplicate sampling, failed translation and reset.
The live producer must sample these clocks each engine frame and reset them on
entity-slot reuse/map reset; that lifecycle wiring remains pending. Event
parameters still require their own semantic/asset adapters and are preserved.
Linux `test-codol`, the full Linux build and the Windows server build pass with
this adapter. Live snapshot transmission remains unverified.

Native physics-preset construction now translates the common parameters and
the cylinder-fallback flag into IW3's 44-byte `PhysPreset`, with ABI assertions
and owned strings. C1's dynamic-entity shape selection at `0x4e1ac0` reads its
preset pointer at `+0x2c`, then tests preset byte `+0x40` at `0x4e1b13`.
Nonzero selects `0x658cc0`, which takes the smaller horizontal half extent and
the vertical half extent for cylinder geometry; zero selects `0x658a40`, which
doubles all three half extents for box geometry. The adapter therefore maps
CoDOL byte 64 to IW3 byte 40, normalizing any nonzero byte to true. Fixtures
distinguish byte 40 from byte 64 and adjacent padding, check truncation rollback,
and verify string lifetime after source release. The full extension remains
retained in the owned source representation. Its additional simulation fields
are still unmapped, and these objects are not yet published or bound to models.
Validation: Linux `test-codol` and full build, the Windows executable build and
`--codol-info` pass. The mounted MP set constructs all 64 native presets while
checking 6,480 model/mesh and 22,988 material lookups with zero failures. These
are asset and build checks, not a live physics or match-entry test.

Physics presets now have an owned decoder for name, sound prefix, type, mass,
bounce, friction, force scales and piece-spread/velocity fields. It resolves
inline or retained-block strings, rejects nonfinite common scalar values and
retains the final 28 CoDOL bytes verbatim. The default preset contains a float
at offset 40, whereas native IW3 `PhysPreset` uses that offset for a cylinder
flag; direct structure copying is therefore invalid. Mapping the remaining
extension fields into native physics behavior remains pending. Fixtures cover pooled/inline strings,
truncation, invalid values and ownership after source release.
All 64 preset lookups in the mounted MP startup corpus decode successfully; the
existing 6,480 model/mesh and 22,988 material checks also pass with zero failures.

Model physics dependencies now expose validated inline source views and resolve
typed pooled references for presets (type 0) and collision maps (type 1). The
catalogue includes directory/insertion aliases plus preset pointer fields in
glass and dynamic-entity definitions. All 734 preset references and 203 collision
map references in the 90-zone model corpus resolve to complete source assets.
Mounted lookup selects the current named definition and returns its retained
blocks, with explicit absent/invalid results. Native fixtures cover type
separation, insertion slots, mounted lookup, null dependencies and truncated
inline payloads. Native physics-object conversion and binding remain unfinished.
The mounted MP startup set resolves 64 preset and 12 collision-map dependencies
alongside its 6,480 model/mesh and 22,988 material lookups, with zero failures.

Native mesh binding now derives `XModel.lodRampType` from the assembled surfaces:
any nonzero deformation byte selects skinned behavior, otherwise rigid behavior.
This follows the retained IW3 `XModelLoad_230` path and preserves byte offset 7.
Tests cover a deformed surface in the last LOD, failed-bind rollback, resetting
to rigid on rebinding, and the actual assembly `XModelGetLodRampType` accessor.
Other model flags still require verified mapping before complete publication.

Native material lookup is connected to `DB_FindXAssetHeader` through the existing
source-level CoDOL asset branch. Definitions are converted lazily and cached in
their owning archive; repeated case-insensitive lookups reuse the same pointer.
Newer definitions win while old returned objects stay alive until unmount.
Known unresolved CoDOL stubs fail explicitly. Cache entries and owned names are
released on unmount. Tests cover overrides, pointer reuse, lifetime and missing
dependencies. This supplies the engine lookup path; it does not add entries to
the legacy DB enumeration pool or publish complete native XModels.
The MP corpus passes all 6,480 model/mesh and 22,988 material lookups, including
repeated cache-pointer checks and mesh bindings using the cached engine objects.

Dedicated native material conversion now uses the existing 80-byte `Material_t`
ABI. It owns the resolved name and preserves the basic 24-byte MaterialInfo
prefix's flag, sort, atlas and surface-type fields. Renderer-specific packed draw
keys, techniques and GPU/texture/constant/state resources remain unset, matching
the existing disabled renderer in `null_client.cpp`; this is not a graphical
client material converter. Native fixtures verify ABI offsets, input rejection,
field preservation and name lifetime. The native engine lookup path is described above.
The MP startup corpus passes 6,480 model/mesh lookups and constructs 22,988 native
dedicated materials with zero failures. Its mesh-binding checks now use these
native material objects instead of placeholder test handles.

Mounted model materials now resolve comma-prefixed stubs and select the newest
real named definition, including overrides used by older models. All inline
material definitions are catalogued, including those outside model slot arrays.
The source API returns the resolved name and defining archive's retained blocks,
excluding scratch block 0, for subsequent native dependency conversion. Fixtures
cover cross-archive stubs, real-definition overrides, missing dependencies and
unchanged outputs on failure. The 90-zone corpus contains 3,407 pooled model
material slots that point at stubs. Dedicated native conversion is described above.
With `code_post_gfx_mp` added after `code_post_gfx_default_mp`, the expanded MP
startup set passes 6,480 mounted model/mesh lookups and 22,988 resolved material
definition lookups with zero failures. Every returned material has a non-stub
name and the owning archive's retained blocks. Counts include repeated names;
this remains an extracted-IWD corpus check, not live engine/client validation.

Surface dependency stubs now follow the retained IW3 `DB_LinkXAssetEntry`
leading-comma convention. A stub resolves to the newest real named surface
definition across mounted archives, including unaliased inline definitions.
Geometry uses that definition's retained blocks; pooled names also resolve in
the defining archive. Missing definitions fail explicitly without reusing an
older model. Fixtures cover cross-archive ownership and missing dependencies.
The optional `test_codol_assets --mounted-set <extracted-model-dir> <base.zone>
<patch.zone> ...` check exercises mounted models, streamed geometry and material
lookup together, using numbered extracted IWD files in descending priority.
`--mounted` checks each zone separately and can expose obsolete base/IWD pairs;
these checks do not start the game filesystem or a client session.
The earlier MP source-view check (`code_post_gfx_default_mp`, `common_mp`, `patch_common_mp`,
`common_gametype_mp`, `patch_common_gametype_mp`, in that order) passed 6,479
mounted model lookups/native mesh constructions and 22,987 serialized material
lookups with zero failures, but accepted material stubs at that stage.
Real-definition resolution additionally requires `code_post_gfx_mp`, which owns
the `mc/lambert1` definition used by `tag_origin`.
Counts include repeated model names across archives;
each lookup uses the winning definition. Materials are still source views,
not native engine material handles. Omitting common/startup zones deliberately
fails on unresolved prop/default-model dependencies.

Mounted model LODs now resolve pooled type-3 surface assets through a typed
catalogue of directory entries and insertion slots. Resolution stays in the
winning model's archive and rejects aliases of another asset type. All 23,048
pooled LOD references in the 90-zone corpus resolve to complete surface assets.
The native corpus now covers 33,916 surface asset views and 16,057 constructed
surfaces with zero failures. It assembles 1,664 whole model meshes; 13,376 still
require external surface resolution in this test path, which does not load IWDs.
Native fixtures cover directory/insertion aliases, cache reuse and a mesh whose
owned geometry survives unmount. Named empty surface assets continue through the
existing streamed-model provider. This removes the blanket rejection of pooled
LOD dependencies; runtime model publication remains unfinished.

Model material-slot decoding now retains each slot's null, pooled or inline
reference and exposes validated views of inline material assets. The descriptor
array is owned; inline views borrow the mounted zone. Winning-model caching
preserves archive override behavior and releases descriptors on unmount. All
15,040 models passed independent slot/extent comparisons; native tests cover
mixed reference kinds, truncation, cache reuse and invalid newer patches. This
exposes actual dependencies for the binder. Complete zone replay now retains a
typed material catalogue for directory entries, insertion slots and inline model
slots, without treating temporary block 0 as persistent asset storage. Mounted
model lookup resolves within the winning model's archive. All 60,574 pooled model
slots in the 90-zone corpus resolve to complete material source views; the corpus
also contains 9,537 inline slots. Regression tests cover directory/slot aliases,
invalid references, failed replay rollback and mounted lookup. Other asset-family
material pointer-slot aliases are not catalogued yet. Runtime publication remains
pending; named definitions and dedicated native conversion are available.

Native model cores can now bind an assembled mesh with resolved material
handles. Binding uses each surface's original material index, copies the handle
array into core-owned storage, and installs native surface/LOD/collision-LOD
fields while preserving skeletal and collision data. Missing handles and invalid
ranges leave the old binding intact. Mesh geometry and material assets remain
borrowed and must outlive the core. Tests cover reordered slots, rebinding,
rollback and ownership. Engine publication is still pending. Dedicated material objects are now available
for binding; they do not allocate rendering resources.

Native model-wide mesh assembly now combines converted LODs into one owned
surface array, with native LOD distances, counts, ranges and bone masks. It
preserves original material indices and remaps the collision LOD when active
LODs are compacted. Partial construction rolls back atomically. A mounted-model
entry point uses inline or streamed LOD caches. All 15,040 source model records
were measured to have contiguous full material ranges. The zone corpus assembled
1,664 complete meshes from inline and pooled dependencies; 13,376 require external
surface resolution in that test path. The original 12,785 surface conversions still
pass. Material-handle binding is provided above; actual material resolution and
full runtime model publication remain pending.

Filesystem startup now derives the IWD key from `fs_basepath/C1.exe`, or the
startup override `+set codol_clientExe <path>`. Initial archive indexing and
independent file-handle opens select CoDOL encryption by archive basename using
the client format's `iw_image`, `iw_model`, `iw_config`, `iw_sound`, `iw_ui_image`
and `iw_adlc` patterns. Other ZIPs retain ordinary handling. Failed key setup
clears previous state and prevents new encrypted opens; filesystem shutdown
wipes the key. Open ZIP handles own independent key copies. Tests exercise
archive selection on all original model IWDs, ordinary ZIPs, basename-only
classification, failed reinitialization and existing-handle lifetime. This
connects the original-archive read path; live engine model publication and
client entry remain unverified.

The retained ZIP reader now exposes explicit `unzOpenIwd(path,key)` mode. It
decrypts filenames before returning them and compressed data at the reader's
0x4000-byte refill boundary. A central-directory offset index preserves entry
ordinals for cached-offset seeks. Ordinary `unzOpen` retains its original ZIP
behavior. Tests read all 3,438 original model entries through this ZIP API and
compare contents against repacked entries by name, including partial filename
buffers and offset seeks. Synthetic stored/deflated/empty entries exercise
varied caller read sizes and CRC rejection. Filesystem initialization and
archive selection are connected above.

Native IWD crypto now derives its AES-192 key from the verified C1 RSA material
and encrypted IWD blob (`0x59dc60`, blob VA `0xc39b20`), without embedding either
key. Filename counters use the archive CRC and entry ordinal; compressed data
uses absolute offsets with 0x4000-byte chunk resets and big-endian CTR increment.
All 3,438 entries in the original model IWDs decrypt to the existing repacked
files byte-for-byte (176,726,900 bytes), with ZIP CRC verification. Synthetic
counter vectors, invalid OAEP data and length mismatches are tested. The shared
RSA helper also preserves fastfile loading: the common coop archive's metadata
and asset digests match its inflated zone. The ZIP API is connected above;
filesystem key setup and encrypted archive selection are described above.

Empty named LOD dependencies now use the engine filesystem to read
`models/<surface-name>` and decode the streamed model. The mounted-model cache
owns the replacement blocks until unmount. Name/count mismatches and missing or
invalid files fail atomically; successful requests reuse the cache. The provider
is installed during asset-command initialization, and cannot be changed while
archives are mounted. Tests exercise absent files, name/count mismatches,
successful replacement, cache reuse and geometry surviving unmount, plus the
actual filesystem adapter with controlled reads. Original CoDOL IWD filenames
and compressed data are encrypted (the installation's `main/codol_iwd.py`
documents the format); native ZIP reading and filesystem selection are connected above.
The corpus tests use the existing repacked ZIPs. Live engine asset publication
remains unverified.

Streamed surface descriptors now decode from the relocated root block, with an
owned name/header array and explicit references to vertex, blend, triangle and
rigid-tree data. Native tree conversion distinguishes these explicit node/leaf
references from fastfile inline allocation order. All 3,438 streamed files now
build 11,645 owned native surfaces, whose lifetime is independent of the input
blocks. Tests cover noncontiguous tree arrays, invalid targets, truncated names
and header ranges, and atomic failure. Engine filesystem loading and replacement
of named mounted LOD placeholders are connected above; engine publication is pending.

The native streamed-model container reader now validates the 88-byte version-1
header and 1.1.1.13 schema ID, copies its three payload blocks, and translates
the relocation table into retained block references (3/6/7). It checks payload
ranges, overlapping blocks, relocation ranges and pointer destinations before
publishing owned output. C1 `0x4c9f20` reads `models/<name>` and its descriptors;
`0x5817d0` defines relocation selection and offsets. All 3,438 entries in the
six existing repacked model IWD archives passed byte-for-byte relocation tests.
This supplies the container layer for the surface/tree decoding above; the
engine filesystem/mounted-LOD connection is described above.

Mounted model LOD lookup now checks the declared material range and requires
the decoded dependency's surface count to match the model's LOD count before
caching it. A nonempty LOD with no dependency or an empty stream placeholder
returns unresolved if a matching streamed replacement cannot be loaded,
preserving output and never falling back to an older model patch. Inactive LODs
return absent. Pooled cross-asset dependencies still require resolution.
The installation contains matching `models/<surface-name>` entries in
`main/iw_model_*.iwd` (inspected through the existing `_repacked` ZIP copies).
For example, `heg_scarfmask_tf_s_lod040` has streamed payloads in model archives
00 and 04 despite its empty fastfile record. These files have a distinct header
and require a streamed-model decoder; they cannot be treated as the 48-byte
XModelSurfs fastfile format. Archive precedence must also be retained.

Native LOD construction now assigns per-surface triangle/vertex base offsets
and combines surface bone masks into the LOD mask. The retained IW3
`XModelLoad_640..680` implementation establishes both operations: offsets are
LOD-local cumulative counts stored as 16-bit values, and masks are a four-word
union. This avoids copying CoDOL's unpopulated serialized LOD mask fields.
The native XSurface fields at offsets 8 and 10 are now declared separately,
with ABI assertions. The combined mask is retained for model-level binding;
materials, LOD ranges and runtime publication remain pending.
Validation passed on Linux (`make -B test-codol all`), the Windows cross-build,
and 90 zones containing 12,785 native surface conversions. A separate corpus
probe found every model's active material range within its declared surface
count and first LOD zero, but 6,816 inline LOD assets had zero surfaces despite
nonzero model LOD counts. The other 3,897 inline LOD assets matched their model
counts. Empty dependency records must be resolved before model publication;
successful conversion of an empty surface asset does not establish a usable LOD.

The signed collision-LOD byte at XModel `0x12a` now survives LOD decoding and
native core construction, including negative collision-disabled values. C1's
model tracing at `0x64221c` exits for negative values; leaving native collLod at
its zero default would lose that distinction. Native and corpus tests verify
signed decoding and the native field. Model LOD-range/material binding remains pending.

Whole LODs now construct as contiguous native XSurface arrays backed by owned
geometry, with a mounted-model entry point. All surfaces must convert before
the output is returned; a later failure frees earlier pending surfaces and
preserves the caller's output. Tests cover multi-surface stride, separate ownership,
late failure and lifetime after unmount. The native corpus also exercises whole
LOD assembly. Model-level LOD/material binding and publication remain pending.

Native surface construction now maps the four representable bone-mask words
from source offset `0x34`, preserving bit order and all bits. Nonzero upper
source words fail explicitly because the retained XSurface has only 128 mask
bits. The corpus reconstructs masks independently from rigid bone offsets and
weighted blend records; all 9,782 rigid and 3,003 blended surfaces agree exactly
and fit the native range. Regression tests cover high-bit preservation and
atomic rejection of wider masks. Full asset publication is still unfinished.

Native surfaces now preserve source tile mode and deformation bytes. C1 skinning
dispatch at `0xac6df0` tests byte 1 and passes blend/vertex data to the skinned
path when nonzero; byte 2 is separately used for graphics-buffer flags by
`0x4b907b`. Corpus measurements cover 9,782 rigid and 3,003 blended surfaces,
with byte 2 equal to `0x20` in both groups. Regression checks prevent interpreting
that graphics flag as deformation. Part-bit and remaining metadata mapping is pending.

Mounted models now cache their inline LOD surface assets with the owning zone's
retained block views. A native entry point builds an owned surface geometry by
model name, LOD and surface index. Cache reuse, missing/invalid LOD handling and
patch precedence follow the model cache. Pooled surface-asset headers now use the
typed catalogue described above. Native tests cover these paths and confirm that built
geometry survives archive unmount. Surface metadata and publication remain pending.

Validated XModels now expose borrowed views of their four inline LOD surface
assets, preserving null/pooled slots for separate resolution. Independent Python
traversal checks the embedded bytes and lengths. The native corpus check now
constructs geometry for standalone and embedded assets: 90 zones, 10,868 surface
assets, 12,785 native surface geometries, zero failures. This verifies array/tree
construction from real retained blocks; header metadata and complete asset
publication remain unfinished.

The native surface corpus check exposed two valid flat-axis trees whose scale
is positive infinity. The retained tree builder computes `65535 / axis_width`
without a zero-width special case, so conversion now preserves positive-infinite
scales while rejecting NaNs, negative scales and non-finite translations.
Regression tests cover these distinctions. Passing zone paths to the native
asset test runs full replay followed by native standalone-surface construction.

Native surface construction now combines owned aligned blend/vertex/index arrays
and resolved rigid lists into native XSurface geometry pointers and counts. The
source header is retained for remaining flag/part-bit mapping. Construction is
atomic, including cleanup if rigid resolution fails after array allocation.
Native tests cover pointer wiring, packed-vertex stride, ownership and late
failure. This construction object is not yet a publishable surface asset.

Rigid-list conversion can now follow pooled list and tree references in retained
block 3, including pooled trees referenced by inline lists. It applies the
loader's 4-byte record, 16-byte node and 2-byte leaf alignment while keeping
serialized cursors packed. Results own every allocation and survive block release.
Native tests cover both reference paths, alignment padding, every truncated block
extent and output preservation. Complete native surface publication is pending.

Inline surface rigid lists now convert into owned native lists, collision trees,
nodes and leaves, with ABI size checks. The converter validates stream extents
and finite tree transforms and rejects unresolved pooled tree references.
Native tests cover every truncation point, unresolved references, invalid floats,
cleanup and independence from the source buffer. Pooled rigid-tree relocation
and installation into complete native surfaces remain unfinished.

Surface blend/vertex/triangle arrays can now resolve pooled references from
retained loader blocks into aligned owned copies. The helper validates expected
counts/strides, block bounds, finite vertex components and triangle vertex indices;
failure preserves the caller's output. Native tests cover short blocks, invalid
geometry and independence from source buffers. Owned-stream corpus checks now
also cover embedded XModel surface assets. Rigid-tree relocation and native
surface construction remain unfinished.

An owned model-surface reader now exposes 84-byte source surface headers,
inline blend/vertex/triangle arrays and inline rigid-tree streams. Pooled array
and tree references remain explicitly unresolved. Validation precedes copying,
and failed reads leave output unchanged. Native tests cover packed array values,
every truncated input and source-buffer lifetime; corpus checks cover all 155
standalone surface assets. These packed records still require relocation and
native conversion before engine publication.

Native XSurface declarations now match the retained assembly's 56-byte stride,
triangle pointer at `+0x0c`, vertex pointer at `+0x1c`, rigid lists at `+0x20/24`
and part bits at `+0x28`. Packed vertices include the fields consumed at offsets
`0x14/18` and have the required 32-byte stride. The prior declarations omitted
these fields on desktop builds. Compile-time checks cover the layout, and native
tests call the real assembly surface accessors across all four LODs. CoDOL
surface reconstruction and dependency binding remain unfinished.

Mounted model geometry now retains four decoded 56-byte CoDOL LOD records,
including unresolved surface/name references and the remaining raw fields.
C1 accessors `0x643a40`–`0x643b77` verify the base, stride, distance, surface
count, material-table index and distinct first-LOD/count bytes at `0x128/0x129`.
The corpus compares all LOD record bytes for 15,040 models. Native tests cover
truncation, invalid ranges, active non-finite distances and preserved inactive
records. Conversion into native surface arrays remains unfinished.

The retained XModel C declaration now uses the assembly's 28-byte LOD stride,
with its four trailing cache bytes inside each record. The previous declaration
used 24-byte records plus four placeholder integers after the array, preserving
total size but misplacing LODs 1–3. Native tests link the actual retained assembly
and verify all four LOD pointers, distances, surface counts, cache fields and
distance selection. Compile-time checks enforce the corrected stride and cache
offsets. CoDOL LOD metadata and surface binding remain unfinished.

Model contents now survive bounds decoding and native core construction with
all 32 bits preserved. C1's DObj mask test at `0x635ce0` and aggregation at
`0x635d10` both read XModel `+0x134`; static-model filtering at `0x58acbd`
uses the same field. The native converter copies that model-level mask rather
than deriving one from collision surfaces. Native tests use differing model and
surface masks, and the model corpus checks the source field for every model.

Prepared models now have a native core construction path: aligned skeletal
arrays and engine string handles populate the retained XModel fields, while
collision surfaces are copied into its 44-byte native records, including borrowed
triangle pointers and counts verified against the retained tracer. Bone/world bounds
are included and physics references are preserved for later binding. Compile-time
checks enforce the 32-bit XModel offsets and sizes. Native tests cover conversion,
borrowed-versus-owned lifetime and atomic rejection of invalid inputs. The mounted
entry point uses the engine SL adapter. This core is not published as an asset:
remaining header metadata, materials, LODs and physics still need conversion.

The retained native bone lookup now checks the array boundary before reading,
interprets model bone counts as unsigned bytes and rejects combined indices
that overflow its byte output. A production-function guard-page test covers
empty models, absent tags, 159-bone models, first-match behavior and overflow.
The engine's existing DObj part limit is unchanged.

Owned skeletal arrays now have 16-byte-aligned addresses for native consumers,
including arrays resolved from pooled loader blocks. Packed source byte counts
and reference values are preserved. The native mount test and full model corpus
check alignment as well as decoded contents; this is preparation for native
XModel construction, which remains incomplete.

Prepared model mounts now retain owned collision surfaces, triangle records,
world bounds and converted bone bounds in a lazy geometry cache. Geometry uses
the same winning archive entry as the skeleton and remains valid until unmount.
Failed conversion releases pending allocations and leaves the caller's output
unchanged; an invalid newer model cannot fall back to an older cached model.
Native tests cover nonempty geometry, repeated lookup, patch precedence, invalid
bounds and lifetime after source-file deletion. Physics dependencies and full
native XModel publication remain unfinished.

Mounted model bone names can now bind to owned 16-bit engine string handles.
The native adapter uses `SL_GetString(name, 0)` and balances every acquired
reference with `SL_RemoveRefToString` at unmount. Duplicate bone names retain
one reference per bone. Partial acquisition failure or a handle outside the
16-bit XModel field releases pending references without publishing a binding;
cache hits do not reacquire strings. Provider/context mismatches fail explicitly,
and invalid newer patches cannot reuse older bindings. Native tests exercise
rollback, oversized handles, duplicate names, cache reuse, patch precedence and
unmount release. The source zone-local indices remain unchanged. This prepares
the native bone-name field; complete XModel objects and their installation into
the engine are still unfinished.

Prepared mounts now expose cached, owned XModel skeletons and bone names.
Lookup respects newest-archive/last-entry priority and normalized asset names;
invalid matching patches fail rather than falling through to an older model.
Inline skeletal data and pooled references are copied through the validated
converter, using retained blocks with scratch block 0 explicitly excluded.
Bone names are resolved against the owning zone's script-string table and
copied into the cache. Results survive later mounts and source-file deletion
and are freed at unmount. Native tests cover pooled bone arrays, cache reuse,
missing names, invalid patch indices and ownership lifetime. Corpus checks now
resolve all 15,040 complete skeletons and bone-name sets, including the 10,840
previously unresolved pooled bone arrays. Engine SL handles, full XModel
objects, collision model publication and map installation remain unfinished.

The production `codol_loadzone`/`codol_loadzones` commands now prepare and
retain reconstructed loader blocks before publishing mounts. Whole-zone replay
is transactional, rejects unsupported/invalid entries and trailing bytes, and
reports the failing asset. If any archive in a requested set fails, pending
blocks are freed and existing mounts/caches remain intact. Unmount frees loader
memory before its source zone. The source-only mounting API remains available
for script-source consumers; production console mounts require full replay.
Native tests verify rollback after a valid pending archive, stable existing
block/cache addresses, source-file deletion and unmount lifetime. Whole-zone
transaction checks pass all 90 supplied zones. Borrowed block views are now
available to runtime converters; block 0 remains scratch, and retained blocks
do not by themselves constitute runtime asset objects or installed worlds.

Serialized replay now completes all 90 supplied zones: 74,857 ordered asset
entries with no unsupported stops in this corpus. StructuredDataDefSet
(type 39, C1 0x4c61c0/0x4c6150/0x4c5fd0) adds 60-byte definitions,
enum records/entries, struct records/properties, indexed/enumerated arrays
and trailing four-byte records. All eight structured-data assets reach their
exact extents. The single sound-driver-globals entry (type 29) has zero extent
and an external reference; C1's 0x4c8ed0 dispatcher performs no load for this
type. Replay accepts that no-payload case without dereferencing its address
and rejects nonempty payloads. Native tests cover nested counts, pooled names,
multiple definitions, every truncation, late allocation failure and continuing
to the next asset after the zero-length entry.

This milestone proves serialized traversal for the supplied corpus, not runtime
asset relocation/publication or client match entry. Asset references and script
string indices still need runtime binding, temporary block-0 objects need owned
runtime representations, and map installation/session/snapshot integration
remain unfinished. Unsupported types outside the measured corpus still fail
explicitly; no general-purpose unknown-asset skipping was introduced.

Full menu replay is now registered for types 25/26, following C1 MenuList
0x4c18c0, menuDef 0x4c12b0 and itemDef 0x4c0c90. It combines window
strings/materials, event sets, bounded key-handler chains, expressions, sound
aliases and item-specific listbox/edit/multi-choice/string/scalar payloads.
Item expression arrays preserve their serialized order; menu event ordering
follows 0xd0, 0xd8, 0xd4, 0xdc. All 53 menu lists and 22 standalone menus
reach their exact corpus extents. Ordered replay now reaches 74,675 assets and
completes 87 of 90 zones, exposing remaining stops at types 29 and 39.
Native fixtures cover pooled/inline menu references, insertion slots, all
item payload families, nested materials/sounds/events, null items, all
truncations, late allocation failure and key-chain depth limits. Menu object
publication and event execution remain separate from serialized reconstruction.

Menu event-set replay follows C1 0x4c0630/0x4c0570/0x4c04b0, with
conditional payloads at 0x4c0330 and local-variable payloads at 0x4c03e0.
Eight-byte event sets contain arrays of handler pointers; nonzero handlers
load eight-byte tagged records. Type 0 carries script text, type 1 loads an
expression before a nested event set, type 2 loads a nested set, and types
3-6 load a variable name and expression. Other types consume no payload.
Native fixtures cover all these types, null handlers, nested branches,
alignment, every truncation, oversized counts, late allocation failure and
the 64-level recursion bound. The reader reconstructs data without executing
scripts. Full menu types 25/26 remain unregistered pending window/item and
key-handler loading; the previous 82/90 complete-zone result is unchanged.

LeaderboardDef (type 38, C1 0x4c64d0/0x4c6460/0x4c63c0) now replays
its 24-byte header and 32-byte columns, with each column's name and statistic
string loaded in order. All 37 leaderboard definitions reach their exact
corpus extents. Ordered replay reaches 70,160 assets; 82 of 90 zones complete
and only menu types 25/26 stop traversal. Native checks cover pooled strings,
truncated columns/strings, oversized counts and late allocation failure.

The menu expression reader follows C1 Statement 0x4c0260, entries 0x4c00c0
and nested pointers 0x4c01c0. It reconstructs 20-byte statements and 12-byte
entries in block 3, retaining operators/scalars and loading inline strings or
nested statements. Native tests check every truncation, nested alignment,
pooled references and the 64-level recursion bound. Full menu replay is not
registered yet: window/item records and event handlers remain to be implemented.
This reader does not evaluate expressions or install runtime menu objects.

WeaponAttach (type 43, C1 0x4c3dd0/0x4c3d00) now replays its 12-byte
header and 12-byte field records, loading string values for signed types below
16 and type 39. Other field values remain scalar, even when their bits equal
the inline-pointer sentinel. Fonts (type 24, C1 0x4c8c00/0x4c8bc0) replay
their 24-byte headers, two material references and 24-byte glyph records.
All 277 attachments and 11 fonts reach their exact corpus extents. Ordered
replay reaches 70,093 assets and completes 82 of 90 zones; only types
25/26/38 currently stop traversal. Native fixtures cover signed type boundaries,
pooled strings, scalar sentinels, nested material insertion, glyph alignment,
all truncations, oversized counts and late allocation failure. Applying
attachment fields to runtime weapons remains separate from serialized replay.

VehicleDef (type 41, C1 0x4c4ec0/0x4c4e10) now replays its 788-byte
header, embedded physics names/preset, weapon, materials and sound-name
indirections, including the 31-entry surface-sound array. AddonMapEnts
(type 42, C1 0x4beae0) shares the MapEnts text/trigger reader with a 36-byte
header and no stages. All 30 vehicles and nine add-on entity assets reach
their exact corpus extents. Ordered replay reaches 58,334 assets and completes
79 of 90 zones; remaining stops are types 24/25/26/38/43. Native tests cover
nested weapons/presets/materials, insertion slots, the last surface sound,
trigger alignment, every truncation and late allocation failure. Vehicle
script-string binding, entity installation and runtime simulation remain
separate from this serialized-data reconstruction.

WeaponDef (type 28) now replays C1's 0xbfc-byte header and dependencies in
the order established by 0x4c2630. This includes model/material/effect/physics
references, animation names, indirect sound names, two 31-entry sound arrays,
and four accuracy-graph point arrays. Sound indirection follows 0x4b7160;
it is a four-byte string-pointer record, not an inline sound-alias asset.
TracerDef (type 40, C1 0x4c23d0) replays its 112-byte header, name and material
and is also available to nested weapon references. All 1,262 weapons and four
tracers consume their exact extents in the 90-zone corpus. Ordered replay
reaches 46,620 assets and completes 67 zones, stopping at types
24/25/26/38/41/42/43. Native fixtures exercise nested dependencies, sound
indirection, graph ordering, pointer insertion, every truncation and a late
allocation failure. Serialized script-string indices and asset references
still require runtime binding; this is not yet an engine WeaponDef conversion.

Effect-impact tables (type 31) now follow C1 0x4c2180/0x4c20c0:
an eight-byte header and name, followed by 16 records containing 35 effect
references each. Nested effects reuse the native dependency loader, including
pointer insertion. All 19 tables consume their exact asset extents; ordered
replay now reaches 29,954 assets and completes 60 of 90 zones, including the
11 map zones previously stopped at this type. Native tests cover every
truncation and late allocation failure without modifying destination state.
Remaining ordered stops are types 24/25/26/28/38/40/41. This reconstructs
serialized data; asset publication and live match entry remain unfinished.

Complete collision-map replay is registered for types 14/15, following C1
0x4bf410. It reconstructs planes, static-model/material dependencies, brush
trees, terrain, aligned brush arrays, MapEnts and dynamic-entity definitions.
Dynamic definitions reuse the XModel/effect/physics readers; their runtime
arrays are zero-filled in block 2. All 19 collision maps reach their exact
asset-table ends. Native checks cover every truncation, inline planes/brush
edges, 16/128-byte alignment and late dynamic-state allocation failure.
Ordered replay reaches 28,129 assets and completes 49 zones; effect-impact
tables now stop the 11 map zones previously stopped by collision maps.
Owned collision conversion and engine map installation remain separate work;
serialized replay alone does not prove movement or live-client match entry.

MapEnts now has loader-block replay (type 19), following C1 0x4be8c0,
trigger arrays at 0x4be6f0 and stage records at 0x4be820. Entity text consumes
its declared length; trigger model/hull/slab arrays and stages align in block
3, with inline stage names following their records. All 19 embedded MapEnts
records agree with the existing owned reader's consumed extent. Native tests
cover every truncation, mixed inline/pooled names and late capacity failure.
The owned reader remains responsible for semantic geometry/text validation.
Collision type 15 still needs its full replay path connected to this dependency;
ordered zone totals and runtime match-entry status are unchanged.

Multiplayer game-world replay now handles type 18 (C1 0x4bca00), including
vehicle-track segments/sectors/branches and glass-piece name/index tables.
Track branches recurse only for inline references, with an explicit depth
limit. The 68-byte runtime path-data region is cleared in reconstructed memory
without changing the borrowed archive image. All 19 local GameWorldMp assets
reach their exact ends. Native tests exercise nested branches, every truncation,
late allocation failure and header clearing. Ordered replay reaches 28,065
assets, with 49 complete zones; collision type 15 now stops 11 map zones.
Runtime track/glass publication and map installation are still pending.

Complete serialized GfxWorld replay is now registered for type 21. The final
stage follows C1 static/dynamic DPVS loaders 0x4c7630 / 0x4c7290 and the
56-byte trailing records at 0x4c68e0, including nested material/XModel
references and zero-filled visibility arrays with 8/16/128-byte alignment.
All 19 graphics worlds reach their exact asset-table ends. Native tests cover
every truncation, count overflow and late runtime allocation exhaustion.
Ordered loading reaches 28,054 assets and completes 49 zones; type 18 now
stops the 11 map zones previously stopped by graphics worlds. Earlier prefix
APIs remain available for inspection. Replay reconstructs serialized block
images; it does not patch all runtime pointers, install an engine world or
prove live-client match entry.

The world prefix now includes model records, material references, scene
visibility allocations, shadow geometry and light-region hulls, following
C1 0x4c81e3..0x4c86c8. Eight runtime arrays use checked counts and remain in
zero-filled block 2; nested shadow indices and hull axes consume block 3.
All 19 graphics worlds agree with the independent extent walker through this
stage. Native checks cover every truncation, invalid non-sun light counts and
runtime allocation exhaustion. `CODOL_ReplayWorldScene` includes the earlier
prefix stages and leaves block 3 entered for static/dynamic DPVS data. Full
graphics-world dispatch, runtime installation and client match entry remain
unfinished; ordered zone completion totals are unchanged.

The graphics-world prefix now extends through draw data and the light grid
(C1 0x4c7d20 and 0x4c6e60). This includes reflection probes, lightmap image
references, three zero-filled runtime texture arrays, 44-byte vertices,
vertex-layer bytes, indices, grid row offsets, entries and 168-byte colors.
Grid row counts validate the bounds axis and reject reversed bounds. All 19
worlds agree with the independent serialized-extent walker. Native tests
exercise every truncation, alignment, invalid grid bounds and late capacity
failure. `CODOL_ReplayWorldDraw` includes the visibility prefix and leaves
block 3 entered for world models; full type-21 dispatch and runtime visibility
are still unfinished. No GPU buffers are created by replay.

Graphics-world loading now has an atomic prefix stage through skies, BSP
planes/nodes, cell trees and portals, following C1 0x4c7fe0..0x4c81be.
It preserves the 128-byte cell-tree alignment and zero-filled per-cell entity
bitsets in block 2. All 19 world prefixes agree with an independent extent
walker. Native tests cover nested tree indices, portal vertices, every
truncation and late capacity exhaustion. `CODOL_ReplayWorldVisibility` leaves
block 3 entered for the next draw-data stage; it is deliberately not registered
as a complete type-21 loader. Ordered zone totals remain 28,043 assets and 49
complete zones. Remaining world draw/visibility data and runtime installation
are still necessary before map loading and live snapshot visibility can work.

Effect-world replay now follows the 116-byte FxWorld header (C1 0x4be220),
36-byte glass definitions with physics/material dependencies (0x4bdac0),
and glass-system allocations (0x4bdb50). Nine runtime arrays reserve and zero
block 2 without consuming archive input, including the two 16-byte alignment
rules; initial piece indices, states and geometry remain in block 3.
All 19 effect worlds pass exact-extent replay. Ordered loading reaches 28,043
assets; 49 of 90 zones complete, with graphics-world data now stopping 11 map
zones. Native checks exercise every truncation and runtime allocation failure
without partial writes. This reconstructs serialized loader memory; glass
simulation and runtime world installation remain unfinished.

Common-world lighting and light definitions now participate in ordered replay
(types 16/22). C1 0x4bfec0 and 0x4bfe10 establish the 16-byte world header,
68-byte primary-light records and trailing definition names; 0x4bab40 loads
the light definition's attenuation image through the existing image reader.
All 19 common worlds and 29 light definitions pass exact-extent replay,
including assets beyond earlier unsupported entries. Ordered traversal reaches
27,064 assets and completes 49 of 90 zones. A native fixture checks every
truncation, pooled light names and late capacity failure without partial
memory writes. These are serialized block images, not installed engine worlds;
effect-world data now stops 11 map zones.

Sound replay now handles alias lists, sound curves and loaded sounds (types
11/12/13), including five alias strings, streamed file names, inline loaded
audio, speaker maps and insertion slots. C1 loaders 0x4b8750, 0x4b84b0,
0x4b8240, 0x4b82b0 and 0x4b80b0 establish the layouts; 0x4b7f30 places audio
payloads in temporary block 0. The corpus verifies exact consumption for
15,485 alias lists, 85 loaded sounds and one curve. Ordered replay now reaches
26,851 assets and completes 49 of 90 zones. Native tests cover every truncation
of a nested alias/loaded-sound/curve/speaker-map fixture and late allocation
failure, with unchanged memory on rejection. Replay does not publish runtime
sound pointers or initialize audio; weapon/world and other loaders still
prevent full map loading.

Effect replay follows C1's 32-byte FxEffectDef and 260-byte element records,
velocity/visual samples, inline model/material visuals, decal pairs, trail
geometry, spark extensions and name references. All 2,873 local effect assets
reach their exact serialized ends. Ordered replay now reaches 21,243 assets
across 90 zones, with 40 complete zones. Native truncation and late-capacity
tests verify that failure preserves block memory and cursors. FX references
remain serialized names; runtime lookup, pointer publication and effect
simulation are not supplied by replay. Other asset families still stop the
remaining zones, and client match entry remains unproven.

Animation replay now follows the 88-byte XAnimParts header (C1 0x4b7a50),
bone indices, notifications, delta translations/quaternions, packed sample
arrays and frame indices. Delta tracks preserve constant and varying branches,
packed translations, and the one/two-byte index transition at 256 frames.
All 12,023 local animation assets reach their exact serialized ends. Native
tests exercise mixed delta tracks, the frame-width boundary, every truncation
and late memory exhaustion. Ordered zone replay reaches 20,104 assets; 40 zones
complete, with sound/effects and other families still stopping the remainder.
Animation evaluation and engine script-string remapping are not implemented
by replay and remain required for runtime character animation.

Zone dispatch now handles standalone pixel/vertex shaders, vertex declarations
and localized string entries, reusing the nested shader reader. Localized
entries follow C1 0x4c1ea0's two-string order. Native tests exercise all four
dispatch types, shader bytecode alignment and atomic rejection of an
unterminated localization key. The 90-zone run now replays 17,857 ordered assets
and completes 40 zones; 50 still stop at unsupported families, most commonly
animations and effects. No GPU objects or runtime localization registry are
created by replay, and gameplay acceptance remains unproven.

Ordered zone replay now includes rawfiles (C1 0x4c58a0) and string tables
(0x4c5b90). Rawfile payloads consume compressed length or uncompressed length
plus terminator; table cells follow checked row/column multiplication and
4-byte memory alignment. Both use their actual nonzero-pointer loading rules.
The 90-zone check now replays 6,765 assets in order and reaches the exact end
of 34 zones. The other 56 stop at unsupported families, without skipping.
Native tests preserve an already loaded rawfile when a subsequent table fails
on dimensions or block capacity. Full-map replay and runtime pointer binding
are still incomplete; replay does not replace rawfile decompression or table
hash validation in the existing native readers.

Zone replay now initializes block-3 script strings and the asset directory from
C1's `DB_LoadXFile` sequence, with page-rounded declared block capacities.
`CODOL_ReplayZoneAsset` enforces stream order and per-asset byte boundaries,
dispatches supported model/material/physics/image families, and stops without
mutation at unknown types. All 90 local zones initialize; 1,200 prefix assets
replay before unsupported types: vertex declarations (one zone), string tables
(nine), rawfiles (70), localized strings (seven), and sound aliases (three).
A native synthetic-zone test resolves a shared model name after ordered replay
and validates its ownership after zone release. No zone is yet fully replayed
by this dispatcher, and runtime pointer publication remains pending.

`CODOL_ReplayXModel` now composes the full skeletal prefix, material dependencies,
four LODs, collision surfaces/triangles, bone bounds and physics dependencies.
It verifies the serialized extent with the existing model reader before replay,
preflights all block operations, and restores the caller's block stack. All
15,040 local XModels replay to their exact ends. Native tests verify every
truncation and a late capacity failure after nested physics data, including
unchanged block memory. This establishes per-model reconstruction; zone-wide
cursor initialization, other asset families and pointer patching still prevent
runtime registration of the shared models.

Technique-set and material replay now compose nested declarations, shader
bytecode, argument/literal arrays, textures, water and images. C1's temporary
asset-block transitions and insertion slots are preserved, along with technique
names after passes and 16-byte material-constant alignment. All 4,553 standalone
technique sets and 4,913 standalone materials replay to their exact asset ends.
Native tests verify every truncation of nested examples, memory placement and
atomic failure. These routines still copy serialized records; runtime pointer
patching and complete XModel/zone replay remain pending.

Image/water block replay now follows C1 0x4b92d0/0x4b9250/0x4b95a0. Image
headers use temporary block 0; names and load definitions use block 3. Water
arrays stay in block 3, and nested `-2` image references reserve their insertion
slot before replay. All 594 standalone local images reach their exact ends.
Native tests cover every truncation of water with nested image data, late
allocation failure, insertion-slot layout and restoration of block-0 position.
No texture upload occurs. Material/technique replay and full zone reconstruction
remain pending.

`CODOL_ReplayModelSurfaces` now rebuilds surface records, blend arrays, rigid
lists and collision trees in block 3, vertices in block 6, and triangle indices
in block 7. C1 0x4b8ff0 establishes both block switches and 16-byte vertex/index
alignment; 0x4b8d50 establishes 16-byte collision-node alignment. All 10,868
standalone/inline surface assets encountered locally replay to their exact
serialized ends. Native tests cover every truncation, late block exhaustion,
cross-block placement, alignment and unchanged memory after failed preflight.
GPU creation is omitted. Pointer patching and full zone replay remain pending.

`CODOL_ReplayPhysicsAsset` now reconstructs block memory for physics presets
and collision maps, including geometry records, nested brushes, sides, planes
and edge bytes. It validates the full operation sequence before writing, and
returns with the caller's block stack restored. Native tests verify alignment,
every truncation, allocation exhaustion and unchanged memory on failure.
All 353 standalone/inline physics assets encountered in the 90 local zones
replay to their exact serialized ends. This copies serialized records; runtime
pointer patching, physics conversion and full zone replay remain pending.

`CODOL_ReplayXModelSkeleton` now drives loader memory for the XModel header,
name and six skeletal arrays, with C1's per-array alignment. It converts inline
sentinels to reconstructed locations and leaves block 3 pushed for the remaining
dependencies. A validation pass precedes writes, so insufficient memory leaves
block contents, cursors and output unchanged. Native integration tests replay
two model prefixes: the second references the first's arrays, resolves through
block views, and remains valid after source and block release. Full dependency
replay and zone mount integration are still required before resolving shipped
models this way.

`codol_load_blocks.c` now implements the block cursor rules needed to replay
asset loading: independent memory/file positions, memory-only alignment,
nested push/pop with block-0 rewind, block-2 zero allocation without consuming
input, and block-3 insertion slots. C1 0x4cee10/0x4cee70/0x4ceec0 establish the
stack and insertion behavior. Allocations and operations are bounded; failed
operations preserve state and output. Native tests cover nesting, padding,
source exhaustion, block exhaustion and stack limits. Views expose the written
extent to skeletal relocation. Asset-specific traversal must still drive this
cursor to reconstruct full zone blocks; this is not yet wired into zone mounts.

`CODOL_RelocateXModelSkeleton` resolves names and all six skeletal arrays from
explicit reconstructed loader blocks using `(reference - 1)`'s high nibble and
28-bit offset. It checks block/range bounds, copies data into owned storage,
retains original references and stream consumption, and reapplies inline
parent/finite-float validation. Tests cover block-zero offset-zero references,
every short block extent, invalid block numbers, unterminated names, malformed
resolved arrays and ownership after source release. This does not infer block
images from file offsets: zone-wide loader-block reconstruction remains pending,
so the 10,840 local models with pooled bone indices are not yet runtime-resolved.

`CODOL_ResolveXModelBoneNames` now binds inline bone indices to the owning zone's
decoded script-string pool. It copies text into owned storage, preserves null
and pooled string references, rejects out-of-range indices, and leaves output
unchanged on failure. These indices remain distinct from engine SL handles.
Pooled bone-index arrays still require relocation before this step. Native
tests verify ownership after source mutation, unresolved references and atomic
failure; local-model tests compare each resolved name to its own zone pool.

Complete XModel stream traversal now includes inline physics presets and
collision maps. C1 loaders 0x4bb3f0 and 0x4bb650 establish their 68/72-byte
headers; geometry, nested brushes, sides, inline planes and edge bytes follow
0x4bb5c0/0x4bb360/0x4bb2c0. `CODOL_ReadXModelExtent` reaches the exact asset
end for all 15,040 local models, including those with inline physics assets.
Standalone physics assets are also checked against their complete extents.
Native tests cover every truncation of both dependencies and a complete model,
plus oversized geometry/edge counts and atomic failure. These are structural
readers: runtime physics conversion and pooled reference resolution remain.

XModel bounds loading (`codol_xmodel_bounds.c`) now traverses to and owns the
28-byte bone records loaded by C1 0x4b7ea0, immediately after collision data.
Midpoint/half-size bounds become IW3 minimum/maximum bounds and center offsets;
the serialized squared radius is preserved. Static assertions verify the
converted bone structure against retained `XBoneInfo_t`. Model bounds/radius
and both physics references are also retained. All 15,040 local XModels pass
field comparisons, and models without physics dependencies reach their exact
asset ends. Native tests reject truncation, negative extents/radius and NaN
without changing the caller's result. An absent bone array remains explicitly
absent. Physics dependencies and runtime XModel registration are still pending.

Technique-set traversal now handles all 48 references, inline techniques and
passes, vertex declarations, vertex/pixel shaders and length-prefixed bytecode,
argument arrays and literal vectors. Technique names load after their passes,
matching C1 0x4b9ef0; the set loader is 0x4ba130. All 15,040 local XModel assets
now reach and decode their collision records. All 4,913 materials, 155 surface
assets and 4,553 technique sets reach their exact standalone asset boundaries.
Native tests cover every truncation of a technique with all nested dependencies
and reject oversized pass/bytecode counts. These results establish serialized
traversal, not complete runtime XModel creation, shared reference relocation,
physics loading or engine map publication.

Inline water traversal now follows the 68-byte header, M*N complex/real arrays
and referenced image, as established by C1 loader 0x4b95a0. Multiplication is
checked before advancing; invalid dimensions and truncated arrays leave the
stream position untouched. Native tests cover every truncation of a water
record containing both arrays and an inline image. Model collision coverage is
now 14,883/15,040; 157 models remain blocked on inline technique-set traversal.
The technique-set loader was identified at 0x4ba130: a 204-byte header with 48
technique references beginning at +12, providing the next traversal step.

Inline LOD surface traversal now follows the 48-byte XModelSurfs header,
84-byte surfaces, weighted blend indices, vertex arrays, rigid-vertex lists,
collision trees and triangle indices. C1 loaders at 0x4bb890, 0x4b8ff0 and
0x4b8d50 establish the order and sizes. All 155 standalone surface assets
reach their exact boundaries. XModel collision coverage is now 14,881 of
15,040 local assets; the remaining 159 need material technique/water loaders.
Native tests exercise every truncation of a surface containing all nested
arrays and reject oversized tree counts and negative blend counts. Runtime
XModel creation and static-model reference resolution remain separate work.

Inline material traversal (`codol_asset_stream.c`) now follows 96-byte material
headers, inline names, texture arrays/images, image load definitions/payloads,
constants and state bits, using local C1 loader evidence. Positions advance
atomically; unsupported inline technique sets and water records fail.
4,860 standalone materials reach their exact asset boundary; 53 still need
those nested loaders. Integrated into XModel traversal, this increases verified
collision coverage to 10,882 models, with 4,158 still requiring nested
dependencies. Native tests cover every truncation of an inline-image material,
oversized payloads and unsupported branches. This is serialized traversal,
not renderer or runtime model publication.

XModel collision reading now traverses pooled material/LOD dependencies and
converts collision bounds while retaining owned 48-byte triangle records.
C1's collision-surface loader at 0x4bbaa0 establishes a 44-byte surface header,
including triangle reference/count before bounds. 5,609 local model assets
pass full surface/triangle comparisons; 9,431 explicitly fail because their
inline material or LOD assets require additional nested loaders. No offset
scan or skipped dependency is used. Native tests verify truncation, ownership,
bone-index bounds and non-finite triangle rejection. This remains an asset
reader, not a complete native XModel installation path.

XModel skeletal-prefix loading (`codol_xmodel_skeleton.c`) now reads the
0x168-byte header, name, bone-name indices, parent offsets, four-component
16-bit quaternions, translations, classifications and base matrices. C1's
loader at 0x4bbb80 establishes the array order and quaternion stride of 8
bytes. Retained `DObjCalcBaseSkel` also reads four shorts at stride 8; the
earlier claim that IW3 required six bytes was incorrect. All 15,040 XModels in the 90 cached zones pass
array/metadata comparisons. Inline data is owned; pooled references remain
explicit. Native tests reject truncation, invalid parent links and non-finite
translations. Material/LOD/collision-surface traversal, shared references,
script-string interning and conversion to a runtime XModel remain pending.

Static-model placement conversion (`codol_collision_static_models.c`) now owns
transforms and converted world bounds in the retained `cStaticModel_t` layout.
Model references stay explicit when unresolved; an optional resolver supplies
borrowed native XModel pointers whose lifetime remains with that resolver.
All 19 map fixtures compare every placement, transform, bound and reference.
Native tests cover resolution, ownership and non-finite transform rejection.
Atomic map staging now includes these records, but native XModel loading and
reference resolution are still required before static collision can run.

Mounted collision loading now selects a world by its inline basename and a
matching collision asset within that same zone. Duplicate or malformed matches
fail; a matching invalid newer mount blocks older fallback. Returned collision
data remains owned after archive unmount. Native tests verify selection,
missing names, failed replacement and patch precedence. All 19 world basenames
are checked against fixtures, including `ui_viewer_mp.zone` whose internal name
is `mp_ui_viewer`. Pooled world basenames are not guessed. This stages geometry
through `CODOL_LoadMountedCollision`; engine publication still awaits remaining
dependencies and visibility integration.

`CODOL_ReadCollisionMap` now stages materials, brushes/BSP nodes, terrain,
leaves/submodels, leaf-brush trees and map entities as one owned result from a
same-zone world/collision pair. Failure frees all staging allocations and
preserves the previous result; success frees and replaces the prior result.
All 19 fixtures pass aggregate loading and replacement, including failures
deliberately injected at the final MapEnts stage. The result retains unresolved
material counts and static-model dependency counts explicitly. It is not an
installed engine map; static models, shared names and visibility still require
integration before publication.

Leaf-brush trees (`codol_collision_brush_tree.c`) now own both shared and
inline brush-index lists and native node records. Shared references must
describe consistent contiguous slices; every brush index and forward child
offset is checked. Split coordinates and ranges must be finite, and negative
counts preserve the retained overlap-child convention. All 19 map fixtures
compare every node, list and relocated pointer. Native tests cover truncation,
missing brushes, cyclic links and inconsistent shared references. This
completes another collision-data conversion stage; full clipMap publication,
static models, pooled material names and visibility integration remain pending.

Leaf and submodel conversion (`codol_collision_leaves.c`) now owns the native
records, converts midpoint/half-size bounds, preserves contents and brush-node
indices, and validates terrain ranges, finite bounds and submodel radii.
Compile-time checks cover the retained engine layouts. All 19 map fixtures
verify every leaf and submodel field; native tests cover truncation, ownership
and malformed geometry. CoDOL has no serialized IW3 visibility-cluster field,
so converted clusters remain -1 until visibility integration provides them.
Complete clipMap installation remains pending.

BSP node conversion now shares the owned brush loader's plane array and
preserves signed 16-bit child/leaf links in the native `cNode_t` layout.
All 19 maps verify every plane pointer and child pair. Forward node edges,
leaf ranges and aligned plane references are validated before publication;
native tests reject cycles, missing leaves and malformed plane references
without replacing an existing result. Complete clipMap installation is still
pending.

Collision material conversion (`codol_collision_materials.c`) now copies the
surface/content flags and inline names into the retained 72-byte material
layout, checked at compile time. Pooled names are represented by an explicit
reference array and unresolved count; a caller-supplied resolver can provide
names, which are copied immediately. Empty/oversized resolved names fail
atomically instead of being silently truncated. All 19 maps pass per-entry
name, reference and flag comparisons. Native tests cover resolver ownership,
truncation, unresolved names and invalid resolver results. The shared-name
resolver and publication into clipMap remain pending: an unresolved material
set must not be installed as a complete map.

Shared collision planes now resolve structurally from a paired graphics-world
asset (`codol_world_planes.c`). Local C1 loader disassembly establishes the
0x274-byte header, name strings, 16-byte sky records, surface indices, inline
36-byte images, optional image names and 16-byte load definitions plus payload,
then the plane array. The traversal matches all 19 independently fingerprinted
plane fixtures without scanning or map-specific offsets. `CODOL_ReadWorldBrushes`
checks same-zone map identity and plane count before passing the resolved array
to owned brush conversion. Synthetic tests cover every truncation of an inline
sky-image fixture, oversized payload/counts, and unresolved plane ownership;
fixture tests reject map/count mismatches. Engine map lifecycle selection and
clipMap installation remain pending; this does not implement renderer loading.
Evidence: C1 loaders at 0x4c7fe0, 0x4c7cb0, 0x4c7b00, 0x4b92d0 and 0x4b9250.

Brush conversion (`codol_collision_brushes.c`) now owns planes, sides, edge
bytes, and brushes in the retained engine's field layout. It requires an
explicitly resolved shared plane array, validates serialized side/edge slice
references, widens material/adjacency fields, and converts Bounds midpoints
and half-sizes to engine minima/maxima. Plane normals, indices, edge ranges,
allocation alignment, and output ownership are checked. All 19 map fixtures
pass full field and pointer comparisons using fingerprinted plane arrays from
their graphics-world assets; those test offsets are not used by the runtime.
Material loading, glass associations, and clipMap installation remain
unfinished. Native tests also reject truncated assets,
invalid normals and out-of-range adjacency without replacing existing data.

Terrain conversion now owns vertices, triangle indices, walkability words,
borders, partitions, and AABB trees (`codol_collision_terrain.c`). All 19
fingerprinted collision fixtures validate the contiguous border-reference
relationship before serialized references become pointers. AABB fields are
reordered into IW3 order, with compile-time engine layout assertions. The
retained partition counts now use unsigned bytes (shipped CoDOL maps
contain up to 247 triangles per partition), preserving their ABI. Bounds,
finite coordinates, material/triangle indices, and forward tree edges are
checked; unsupported relationships fail without replacing the caller's data.
Fixture tests compare every converted array and reject corrupted geometry;
native synthetic tests cover truncation, ownership, and cyclic trees. This is
an owned terrain reader, not yet a complete installed clipMap: static models
and map lifecycle integration remain required.

| Area | Source | Current behavior |
| --- | --- | --- |
| Build profile | `makefile`, `net_game_conf.h`, `sys_cod4defs.h` | Default `GAME=codol`, `codol_dedrun`, protocol 187, port 17733; `GAME=iw4ol` retains the original protocol. Separate engine object directories and header dependency files. |
| Native netchan | `netchan.c`, `codol_netchan.c`, `codol_wire.c` | Direct source calls to CoDOL send/receive functions. 1162-byte fragments, u8 index/last, u16 stride/length; one sequence for the entire message, no empty terminator. |
| Reassembly | `codol_wire.c` | Bitmask completion, reordered/duplicate fragments, bounds checks, inconsistent metadata/content rejection, stale-sequence rejection. |
| Netchan XOR | `sv_net_chan.c`, `codol_wire.c` | Raw command bytes, direction-specific initial key, encoding before fragmentation. Existing IW3 command storage is retained. |
| bdDTLS DATA codec | `codol_crypto.c` | Tiger192(shared X + security key); Tiger192(counter LE32) IV; AES192 CTR with LE increment; HMAC-SHA1(header6 + ciphertext) truncated to 8 bytes. Rejects wrong tag, version, length or MAC before decrypting. **Not yet connected to UDP sessions.** |
| Counter extension | `codol_wire.c` | Restores the 32-bit IV counter from 16-bit wire values, including wrap and late packets. |
| Fork isolation | `common.c`, `sec_update.c`, `sv_main.c` | CoDOL profile skips upstream downloaded global config, updater, and master heartbeats. |
| Inspection | `sys_main.c` | `--codol-info` returns port capability status before engine initialization. |
| User-command wire | `codol_msg.c`, `codol_usercmd.c` | Interleaved byte/bit pools, A/B/C delta paths and 7/2/5 tags, 10-bit weapon IDs, extra location/remote/melee fields, command-key hash and input filters. |
| Engine input | `codol_game.c`, `sv_client.c`, `sv_main.c` | Native command decoding for batches up to 255, CoDOL packet headers and uncompressed bodies, explicit weapon mapping and raw-command side storage. Rejects invalid predicted origins before updating client state. |
| Archive reader | `codol_assets.c`, `codol_fastfile.c` | Native IWff0100/IWffu100 decryption, signed-container block hashes, bounded inflation, zone directory and compressed/uncompressed rawfiles. |
| Script source | `codol_asset_registry.c`, `codol_asset_commands.c`, `cscr_parser.cpp` | Owned mounted archives, newest mount first, rawfile source lookup before IW3 database lookup, embedded-NUL rejection. Loose script files retain precedence. |
| Configstring/gamestate codec | `codol_configstrings.c` | Owned 6519-entry bank, explicit empty versus inherited/unset entries, contiguous replicated-dvar block replacement, 13-bit absolute indices and CoDOL gamestate header/tail. |
| Gamestate publication | `codol_sv_state.c`, `sv_main.c`, `sv_client.c`, `sv_snapshot.c` | The engine appends the CoDOL gamestate after reliable commands in an ordinary netchan message. No IW4OL config-data envelope or Huffman compression. The bank resets with the server. Asset and numeric-dvar producers remain pending. |
| Snapshot field values | `codol_delta.c` | Native value encoders for all 32 special codecs in the reference, float-zero codec, and signed/unsigned widths through 32 bits. Shared interleaved cursor, explicit position bases and optional bounds clamping. |
| Player-state stream | `codol_playerstate.c`, `codol_player_fields.inc`, `codol_player_arrays.c` | All 244 measured player-state field descriptors, rov/lc flags, gap ordering, hint-3 zero-base handling, hint-2 second pass, stats, clip/reserve ammo, equipped weapons and both HUD arrays. Sections 5/7 remain empty, matching the reference. Live engine snapshot integration remains pending. |
| Entity section | `codol_entities.c`, `codol_entity_fields.inc` | All 22 measured tables, entity-number/gap encoding, baselines, inherited records, removals, clears and type changes. eType 13's hint-2 second pass is encoded from the measured client read order. Live engine snapshot integration remains pending. |
| Client section | `codol_clients.c`, `codol_client_fields.inc` | All 77 measured clientState descriptors, unary field gaps, 5-bit client numbers, sorted complete-state additions/removals, inherited records, and zero clears. Live engine snapshot integration remains pending. |
| Actor section | `codol_actors.c`, `codol_actor_fields.inc` | All 24 measured descriptors and sorted actor records. A canonical 0x5C-byte image keeps the unaligned overlapping words at 0x44/45/46 consistent. Live engine snapshot integration remains pending. |
| Animation commands | `codol_animcmd.c` | Six terminal command types, entity/time reference registers, blend/rate/weight/fraction/sub codecs and section termination. Always emits fresh records rather than previous-ring reuse. |
| Snapshot assembly | `codol_snapshot.c` | CoDOL header, relative delta number, player state, animation commands, actors, entities, clients, sixth-section terminator and EOF. Rejects expired (>31) or invalid base sequence. Caller-owned state; the message bridge supports prepared history, but the live snapshot sender is not wired to it. |

`netchan_t`, `usercmd_t`, `playerState_t`, and `entityState_t` were not enlarged:
the assembled IW3 routines depend on their offsets. Reassembly metadata occupies
28 bytes of the existing caller-owned fragment buffer. The default IW4OL incoming
buffer is only 2048 bytes, so the integrated receiver accepts at most 2020 bytes
per fragmented message. The standalone codec supports 148736 bytes. Outgoing
messages retain the engine's 131072-byte buffer limit. Larger native buffers need
a deliberate allocation/ABI audit, not a global constant substitution.

## Evidence and tests

`CODOL_ReadCollisionLayout` retains the forward walk's 21 section spans with
asset-relative offsets, counts, strides and serialized references. Externally
pooled planes use SIZE_MAX as their unresolved offset. Geometry consumers can
now reuse the verified traversal instead of locating arrays independently.
Across all 19 fixtures, triangle indices fit the vertex arrays and partition
triangle/border counts close exactly on their header totals. Native tests check
section offsets after inline data and unchanged output on failure. The portable
fixtures, four native test executables and Linux build pass. These spans still
need geometry relocation and conversion into retained engine structures.

`codol_collision_stream.c` now walks the collision stream forward to MapEnts.
Two ordering details come from retained `_db_load.asm`: leafbrush indices load
before leafbrush nodes, and an inline partition border consumes exactly one
28-byte object even if its border count is zero. The walker also consumes the
28-byte records counted at header +0xA0 before MapEnts. It reaches all 19
independently recorded nested offsets exactly, then `CODOL_ReadCollisionMapEntities`
loads and validates the entity text, triggers and stages. No runtime text scan
or map-specific offset is used. Inline static XModels remain unsupported.
Portable fixture tests, malformed-stream tests, four native test executables
and the Linux build pass. Collision geometry relocation and publication to the
engine remain required before map spawning can work.

MapEnts validation now covers all 19 collision-bearing cached zones, using fixed
asset indices/nested offsets and asset SHA-256 fingerprints stored in
`tests/codol_map_entities_fixtures.json`. The portable test checks entity-text
digests, copied trigger arrays, stage names/origins/references and consumed
lengths. The native reader additionally rejects invalid model-to-hull and
hull-to-slab ranges, nonfinite geometry, negative half-sizes, and invalid stage
trigger indices (preserving sentinel 1024). Synthetic rejection tests and all
19 shipped fixtures pass, as do the Linux build and four native test executables.
Fixture offsets are test data, not a replacement for collision stream traversal.

The nested MapEnts reader now continues through trigger models (8-byte
records), hulls (32), slabs (20), stage records (20), and inline stage names.
It owns the copied arrays and strings, preserves unresolved stage-name
references, and rejects truncated arrays or pooled array pointers it cannot
resolve. Killhouse matches 143/152/35 trigger records and three stages named
`stage 0`, `stage 1`, `stage 2`; total consumed size is 233846 bytes. Stage 0's
trigger index 1024 is preserved. Synthetic tests cover every truncation across
these sections and ownership after source mutation. The Linux build and four
native test executables pass. Trigger geometry interpretation and collision
stream traversal remain separate work; this does not yet enable map spawning.

`CODOL_ReadMapEntities` reads an owned entity-text prefix from an already
resolved nested MapEnts stream position. Killhouse's collision asset contains
the observed 44-byte header at zone offset 0x5E5FFD9, followed by 227010 bytes
including NUL. The native reader reproduces that text exactly (SHA-256
869d44c2316f394dc9f88490aed698599bbe67e0b9b0a20c2433df740852a243).
Synthetic tests cover inline/pooled names, copied ownership, truncation,
embedded NUL rejection, unresolved text pointers and unconsumed trailing data.
This does not locate nested headers by scanning at runtime: the collision loader
must resolve their positions. Trigger/stage interpretation and database publication are
still pending, and live engine integration remains unverified.

`CODOL_OverlayEngineMissile` translates retained ET_MISSILE trajectories, maps
its weapon into the measured CoDOL selector at 0xD4, and sets scene scale at
0x54 to 1.0. It requires a destination type-4 table and preserves other fields.
This follows `alpha0022/docs/projectile_wire.md`'s measured render arm at
0x443BE5; the player entity's 0x80 selector is not reused. Native coverage
serializes a gravity-driven missile using wire weapon 769 and checks preserved
fields and atomic rejection of unmapped weapons, wrong types and invalid
motion. The Linux build and four native test executables pass. Flags, ownership,
events, weapon-definition loading and live missile frame publication remain open.

Trajectory translation now covers all six retained IW3 modes. The measured
client `BG_EvaluateTrajectory` table at 0x40CCA8 maps linear-stop/sine/gravity
to 3/4/5 (`alpha0022/docs/projectile_wire.md`, section 1.2). The retained
`_bg_misc.asm` and client evaluator both use gravity 800. Zero-duration sine,
negative durations, unknown modes and nonfinite vectors fail atomically.
Native tests exercise both position and angular trajectories across all 22
entity field tables. The Linux build and four native test executables pass;
projectile gameplay and live entity frame integration remain unverified.

`CODOL_CollectServerClients` gathers a snapshot's client span from the retained
engine ring, translates each record through the published asset map, and copies
the complete result to caller-owned storage. It checks ring capacity, overwritten
and future spans, client count/ID limits, ordering and unresolved attachments
before changing the destination. Production-module tests cover ring wraparound,
insufficient output space, duplicate/out-of-range IDs, overwritten/future spans,
missing ring storage and empty spans. The Linux build and four native test
executables pass. The live frame producer must still combine these records with
translated player/entity state and invoke snapshot preparation.

Model/tag publication now lives in `codol_sv_assets.c` and feeds
`CODOL_OverlayServerClient`, which resolves engine indices before invoking the
client-state field translator. The production-module harness verifies exact
reliable commands, unchanged-update suppression, recycled handles, reset,
resolved wire fields and atomic rejection of unknown attachments. The Linux
server build and four native test executables pass. Frame construction still
needs to collect and send these translated records.

Before gamestate and snapshot command publication, the server now reads retained
model/tag configstrings, registers their names in the CoDOL bank, and queues
reliable updates for primed clients. Native indices resolve through
`CODOL_ServerModelToWire` and `CODOL_ServerTagToWire`; unresolved indices return
-1, zero remains absent. Map reset clears the mapping. Cached engine string
handles are also compared by name, so handle recycling cannot retain an old
mapping. Unparseable reliable-command asset tokens fail publication rather than
being renamed. This publishes names already registered by the engine; it does
not load CoDOL models or prove their availability on a live client. The frame
producer still needs to consume these indices.

The production send harness now executes `SV_EndClientSnapshot` with the real
MSG writer, CoDOL snapshot encoder and history. It checks one EOF on success,
no committed history after rejection, and ACK/EOF-only recovery after overflow.
A fourth case advances the channel sequence before transmission: the server now
recovers instead of sending a delta encoded for a different packet number.
Transport, downloads and engine diagnostics are controlled test substitutes;
this does not constitute live client acceptance.

`CODOL_PrepareClientSnapshot` binds a prepared frame to its client slot, message
object, buffer, length, outgoing sequence and exact serialized bytes. It reserves
an owned copy before serialization and releases it on acceptance, rejection,
discard, or reset. Same-size payload changes and split-message substitutions
cannot become acknowledged bases. `SV_EndClientSnapshot` recognizes
its existing EOF and commits history only after the send is accepted. Beginning
a new message or recovering an overflow discards the pending frame first.
Native bridge tests cover acceptance, rejected sends, overflow, changed message
length, another message object, and explicit discard. The production send fixture
mutates every byte in turn, including the reliable prefix and EOF, and checks
that each mutation sends only the recovery message and never commits a base.
The live frame producer
still needs translation and the call to this preparation API; ordinary engine
snapshots still use the IW3 serializer until that producer is implemented.

CoDOL `SV_Netchan_Transmit` now encodes an owned temporary copy before
submission. The caller's plaintext remains unchanged after both accepted and
rejected sends, so post-send history validation and retries see the original
message. Submission sends synchronously or retains its own fragment copy.
The send fixture exercises the real XOR/transport wrapper with controlled
submission results, verifying plaintext preservation and every-byte mutation
rejection together under sanitizers.

Snapshot histories now have lazy per-client storage outside `client_t`.
Connection slot initialization (including bots), disconnect, server clearing,
and process shutdown destroy the corresponding histories and pending frames.
Reinitializing a slot also clears its raw CoDOL input history. Native tests check
slot isolation, same-slot reuse, exact ACK visibility, per-slot reset, full reset,
and destruction with a pending frame. The live frame producer still must use
these histories and finish prepared frames according to transport acceptance;
this lifecycle change alone does not switch the IW3 snapshot serializer.

`CODOL_MountArchives` stages a complete archive set before publishing it. Failed
opens discard staged zones and leave prior mounts and cached pointers intact;
successful sets use input order as ascending override priority, last wins.
The console command `codol_loadzones <C1.exe|-> <base> ... <patch>` uses this
operation (`-` selects inflated zone files). This order describes the native
registry's precedence, not the client's patch-first loading sequence.
Native tests cover a failed second input (null and malformed file), successful
patch precedence, old cache lifetime, and file deletion after mounting.
Automatic selection and mounting during `SV_SpawnServer` remains pending; the
retained map-loading path still needs collision/model/weapon translation.

Mounted rawfiles now have a cached retained-engine `RawFile` view with decoded
length, bytes and trailing NUL. `DB_FindXAssetHeader` checks this cache and the
CoDOL string-table cache, so direct C++ lookups and the assembly wrapper use the
same source. Compile-time checks compare every field offset and structure size
with the retained engine layouts. The generic rawfile view preserves binary
payloads; source compilation continues to use its separate text validation.
Cache tests cover reuse, case/slash normalization, newest-mount precedence,
old-pointer lifetime, malformed patch rejection and cleanup. Full map loading
and model/animation translation are still unverified and incomplete.

`CODOL_ReadScriptStrings` exposes the zone-local script-string index table for
native asset loaders. It preserves each serialized reference and distinguishes
null/pooled entries from inline empty strings. The caller owns the returned
array; its text pointers remain valid until the owned zone is closed. This is
the script-string pool used by indexed asset fields, not a resolver for pooled
StringTable cells or asset names. Mapping these indices into engine string
handles remains part of the model/animation loaders.

The archive inspector compares each script-string index, reference and inline
SHA-256 against an independent parser, in addition to existing asset digests.
Synthetic coverage includes duplicate strings, empty strings, unresolved
references, source ownership, and truncated pool data.
The four archive differential suites pass with this check enabled: all 90
cached zones (19889 inline script strings and 37 null entries), four encrypted
fastfiles, generated archives and malformed inputs. The Linux server rebuild
and all three native test executables also pass.

`SV_SendMessageToClient` now returns acceptance to its caller. CoDOL rejects
overflowed messages and delayed-drop sends, restores frame timing/size metadata
after transport rejection, and schedules a retry. Gamestate sending rolls back
primed state, message/reliable counters and pure state after rejection without
reviving a client dropped during the attempt. `test_codol_send.c` exercises the
production send function with controlled transport outcomes: rejection,
metadata preservation, successful retry, delayed drop and overflow. This is
included in `make test-codol`; live-client gamestate delivery remains unverified.

The CoDOL server send path now uses `CODOL_NetchanSubmit` to distinguish message
acceptance from the first UDP attempt. A newly copied fragment queue counts as
accepted even when its first send fails; an existing queue or failed single
packet rejects the submission. Rejected submissions no longer clear the current
engine frame. Native tests inject socket failure, verify queued ownership and
retry, reject queue overwrite, and check sequence exhaustion. Snapshot-history
completion can use this acceptance result once frame/send integration is wired.

Snapshot history now supports prepare/finish ownership: preparation allocates
and quantizes a pending frame without exposing it to ACK lookup, and finishing
the exact sequence either retains it without allocation or discards it.
`CODOL_PrepareServerSnapshot` joins ACK-base selection, pending history and
engine-message serialization. Missing/expired ACKs fall back to a full baseline;
failed writes discard the newly prepared frame. Tests cover full/delta headers,
transport rejection, wrong sequences, source mutation, overflow and reset.
The delta suite now passes 17 tests. Actual engine frame construction and the
transport call site's finish/reset wiring remain required.

`CODOL_WriteServerSnapshot` now appends the CoDOL serializer to the retained
engine's `msg_t` after reliable ACK/commands. Successful writes advance cursize
and establish a byte boundary; failed serialization leaves cursize and codec
context unchanged and marks overflow. It owns the final EOF. Native tests cover
the reliable prefix, full snapshot output, capacity failure and invalid state.
This bridge is not yet selected by `SV_WriteSnapshotToClient`; frame translation,
history/send acceptance and EOF ownership must be connected together first.

`codol_events.c` now maps 129 IW3 event names to the installed C1.exe's measured
event-name table at VA 0xCD81D8. `tools/codol_event_map.py` independently verifies
the generated switch against that local image. Six names lack exact matches
and remain unsupported: stop-sounds, empty-offhand, MG42 fire, frag/special
grenade hints and the clearance hint. Entity types 0..16 retain their meaning;
temporary events translate both the event number and the base (IW3 17, CoDOL
21). The botlib dummy mover type is rejected. Native tests check firing,
obituary, jumping, temporary-event types and unsupported inputs. Payload
semantics and event publication still need integration; equal names alone do
not prove identical event parameters.

`CODOL_OverlayEngineTrajectories` translates named IW3 position/angular
trajectories into a caller-selected CoDOL entity table. It uses the corrected
pos.trBase offset 0x18 and pos.trDelta offset 0x24, carries trajectory times and
durations, and preserves fields owned by other adapters. All six retained
trajectory modes map to the measured client enum; unknown modes fail without
substituting movement. Native tests cover distinct origins/velocities,
angular state, invalid floats and atomic rejection. Entity-type selection,
flags, events and send-path integration remain open.

Script resolution now distinguishes missing assets from matching invalid assets.
`CODOL_FindRawFileStatus` and `CODOL_LoadScriptAssetStatus` return ready/missing/
invalid separately; the source compiler stops on invalid CoDOL data instead of
falling through to an IW3 rawfile. The legacy boolean APIs remain wrappers for
existing callers. Native tests cover corrupt patch precedence, binary-source
rejection, untouched failure outputs and missing assets after unmount. Pooled
rawfile names still require relocation before they can participate in lookup.

`codol_stringtable.c` implements the native type-37 two-pass table reader with
owned storage, row/column bounds, inline-name parsing and cell-hash validation.
Hashes use ASCII lowercase and signed-byte promotion, including Chinese bytes.
Pooled references remain explicit with NULL text and their original pointer/hash;
there is no collision-prone hash-to-string guess. `test_codol_tables.py` passes
all 518 shipped tables across the cached zones: 132,240 inline cells hash-check
and 501,634 pooled references remain unresolved. Synthetic native tests cover
ownership, invalid hashes, truncation and repeated cleanup. Block relocation and
engine StringTable publication remain incomplete.
Fully resolved tables now have cached engine-compatible views in the mounted
archive registry. `DB_FindXAssetHeaderReal` consults that registry for IW3
StringTable requests, so existing script lookup routines can consume CoDOL
tables without hooks. A matching table with unresolved cells fails explicitly;
it does not fall back to an older mount. Native tests exercise cache identity,
case-insensitive names, mount overrides, retained old pointers and cleanup.
Tables with pooled names cannot yet be found, and pooled cells still require
block relocation; those limitations prevent general shipped-table gameplay.

Gamestate publication now populates CoDOL player names from connected engine
clients through `CODOL_SetPlayerNames`. Names occupy CS[1280..1299], with empty
slots explicitly cleared and names bounded to 63 bytes. CS[1300] and later are
preserved because they contain local-client information. The active
`snapshot_sections.py` correction identifies clientState+0xC0..0xCC as perk
masks, despite older `bot_snapshot.py` comments calling them names. Native tests
cover replacement, clearing, rejection of oversized slot counts and preservation
of the adjacent local-info slot. Identity for
client numbers outside this measured name block remain unresolved.
The send path now refreshes names before gamestate and snapshot command output:
changed slots enqueue reliable `d <index> <value>` commands for recipients with
a gamestate, and disconnected slots publish empty values. Unchanged slots do
not enqueue repeated updates. The same normalized token is stored in the bank
and sent reliably; whitespace and tokenizer punctuation become separators,
while color codes remain intact. Native token tests cover boundaries, empty
names and parser-sensitive characters. Live-client display verification remains
pending, including the empty-value clear command.

The standalone `codol_history.c` ring now owns deep copies of player, HUD,
entity, client and actor state. It retains 32 sequence slots, accepts commits
only in increasing sequence order, and selects only an exact acknowledged frame
within a 31-message delta gap. Failed commits leave the previous ring intact.
Tests cover source-buffer mutation, ring overwrite, missing/stale ACKs, rejected
commits and reset. This is not yet connected to engine send/ack events: callers
must commit only after transport acceptance. `CODOL_CommitReachedHistory`
prepares quantized player, entity, client and HUD values against an exact retained
base before replacing a frame atomically. Zero selects a full snapshot base;
an unavailable nonzero base fails. Actor images retain their canonical bytes.
Tests cover rounded positions, signed angles, HUD quantization/deletion and
failed preparation preserving the ring. Engine integration remains pending.

The fragment constants/layout come from `netchan_fragment.py` and
`docs/netchan_fragmentation.md`, which identify C1.exe functions at
0x005A21D0, 0x005A2360, 0x005A2490, and 0x005A27D0. Tests compare C packet bytes
directly against that Python module at boundary and maximum lengths.

XOR semantics are described by `docs/netchan_xor_fix.md` and agree with the
existing IW4OL loops. Native tests include raw `%` and high-byte command data.

The crypto reference is the **active functions** in `dtls_crypto.py`:
`shared_key20`, `counter0`, `aes_ctr_le`, `build_data`, `decrypt_data`, and
`extend_ctr16`. The file's introductory SHA1/AES128 description and exploratory
3DES solver comments are stale. The function named `shared_key20` actually returns
24 bytes. The DATA length field is excluded from the MAC, but is checked for exact
agreement with the packet length before MAC verification.

`tests/test_codol_native.c` embeds an independent alpha0022-generated crypto
fixture using synthetic bytes, with counter 65536. It also flips every packet byte
and tests every truncation. Net tests call the real `Netchan_*` and `MSG_*`
functions; only the socket send is substituted at link time in the Linux test
executable, to simulate a failed send. There is no such substitution in the server.

`tests/test_codol_usercmd.py` compares the native decoder with the active
`usercmd_codec.py`, including 49 captured bodies, generated A/B/C transitions,
high-byte/percent command hashing, 10-bit IDs, all truncations, and batches up to
255 commands. The Linux native test also exercises the actual `msg_t` bridge,
mapping, state reset, and failure atomicity.

`tests/test_codol_archives.py` compares native manifests against `zone_assets.py`
and `ffwriter/codol_ff.py`. All **90 cached shipped zones** matched, including
decoded rawfile SHA256 digests. Native encrypted loads matched cached images for
`code_pre_gfx_mp`, `code_post_gfx_mp`, `common_gametype_mp`, and `mp_killhouse_sh`.
Generated unsigned fastfiles exercise inflation across buffer growth boundaries,
empty and compressed rawfiles, malformed lengths, and container corruption.
No client process or reference game server runs in these tests.

`tests/test_codol_configstrings.py` extracts only the reference's pure writer
definitions through Python AST, without importing or starting `game-server.py`.
It verifies all 6519 indices, high bytes, explicit empty entries, the gamestate
header/tail, every output-buffer truncation, and atomic replicated-dvar replacement.
The 1.1.1.13 launcher selects opcode 2 and `CODOL_NO_SECTIONS=1`; the new writer
uses those settings rather than the exploratory defaults in the method signature.
The native checksum selector uses the active `zone_crc.py` measurements for
the unmodified 1.1.1.13 mp/coop/zm constant tables. It is not a checksum algorithm
for modified tables. The source's older introductory claim that zm is unknown
is superseded by its September 2 measurement (`0x801cef02`).
The native bridge is now called by `SV_WriteGameState` and `SV_SendClientGameState`.
It publishes basic map/gametype serverinfo and CS[2], uses `codol_zoneType` (mp by
default, also coop/zm) separately from `g_gametype`, and preserves explicit entries
from native asset/dvar producers. Reliable commands use opcode 1 and EOF uses 5.
Failed gamestate serialization restores the client's previous priming/reliable
send bookkeeping and never sends the partial message. Native tests exercise ACK
and command prefixes, appending to `msg_t`, checksum/header order, capacity failure,
invalid zone categories, and bank reset.

`tests/test_codol_delta.py` compares each native snapshot value codec with
`entity_codec.py` using all eight bit-pool offsets, width boundaries, alternate
encoding branches, negative zero, escaped IDs, time ranges, and nonzero bases.
It also checks every insufficient output capacity and invalid field values.
Inputs to the native API are 32-bit words; float test inputs are rounded to
float32 before comparing, matching the engine's state storage. This validates
field encoding, not complete snapshots or live client acceptance.

Player-state tests compare every native descriptor with the reference table and
reconstruct native field streams using its independent field readers. Cases cover
each field individually, all fields together, random sparse sets, clears, empty
updates, both rov values, and a shared preceding snapshot bit pool. Hint-2-only
changes are delivered by making the final changed slot the gap-loop endpoint;
hint-2 slots below it use the required second pass. The extracted table contains
244 entries even though the client's lc overflow bound is 245; no unmeasured
245th descriptor is invented. `CODOL_WritePlayerFields` exposes this portion;
`CODOL_WritePlayerState` appends the array/HUD sections using the same bit cursor.

`tests/test_codol_player_arrays.py` compares combined stats/ammunition/equipment
and HUD wire bytes against the reference at every bit-pool offset. It covers
15 equipped slots, 16 clip/reserve slots, omitted hand/index values, width limits,
both 31-element HUD arrays, unchanged HUD, and deletion by reducing their counts.
Native HUD fields are complete states, so omitted/zeroed fields clear old values.
The undocumented ps+0x5D0 and ps+0x3340 sections still have zero gates, as in
alpha0022; their nonempty formats are not implemented. None of these tests proves
a complete server snapshot or client gameplay.

Entity tests compare all 22 native field tables and baseline record bytes with
the reference, plus number boundaries, unchanged records, removals, field clears,
and type changes. A type change emits the complete destination table, including
zero fields, so old data cannot survive just because the table layout changed.
The reference itself does not implement eType 13's hint-2 second pass. Native
encoding now follows the local C1.exe decoder at 0x5A0C00: 0x5A0DD9 loads lc as
the second-pass iteration count, 0x5A0DF0 checks hint==2, and 0x5A0E35 advances
the 12-byte descriptor until exactly indices [0,lc) have been visited. The lc
field stays in the normal gap pass, including when it is hint-2. Both passes
use the same type/noDeltaPos base selection (0x5A0D84 and 0x5A0DF6).

The 18-test delta suite checks this path with a test decoder transcribed from
that read sequence, using the reference's independent value decoders. It covers
single-field baselines across all 66 descriptors, same-type deltas, type changes,
inherited hint-2 values and output exhaustion. The Linux build and native tests
also pass. Live client acceptance and engine snapshot integration remain open.

Client-record tests compare every descriptor and each single-field baseline with
the reference writer, plus unchanged-record omission, removal, explicit zero
updates, and rejection of client number 32. The native client section supports
numbers 0..31 independently of the retained engine's configured client limit;
the engine adapter must enforce the smaller wire limit when producing snapshots.

Actor tests compare wire bytes against `actor_codec.py` with its overlap option
enabled, then reconstruct the actual byte image from independently decoded words.
They cover each field, changes and clears, unchanged records, and a combined
overlapping-byte pattern. Unlike independent logical field slots, the canonical
byte image makes every overlapping word describe the same destination bytes.
This is codec-level evidence; actor models, animation references and live engine
actor creation are not established yet.

Animation tests compare all six command types with the isolated reference codec,
including repeated references, all bit-pool offsets, quantizer boundaries and
output truncation. Snapshot assembly tests compare full-baseline and delta body
bytes with reference primitives, including the seven player-array gates, every
section terminator and EOF, and reject a delta base outside the 32-frame window.
These initial assembly fixtures have empty world sections; richer record
composition and live acceptance still require verification. The serializer does
not select acknowledged frames, retain history, translate engine state, or
replace the engine's old snapshot sender yet. Nonempty section six and the
previously noted unsupported sections/eType 13 also remain incomplete.

Publication is not yet sufficient for a match: CoDOL asset and numeric-dvar
producers have not populated the full bank, baseline/snapshot encoding remains
IW3, and the existing connection/authentication path still requires adaptation.

### Native archive and script mounts

The engine console accepts:

```
codol_loadzone "path/to/inflated.zone"
codol_loadzone "path/to/archive.ff" "path/to/C1.exe"
```

The fastfile reader obtains the format's RSA key from the local 1.1.1.13 C1.exe
and checks its fingerprint. It neither embeds nor exports that key. Signed
containers have their stored SHA256 block hashes checked; the header's RSA
signature is **not** verified. Hash checking should not be described as signature
authentication.

Mounted rawfiles feed the existing source compiler. This does not supply CoDOL
script builtins, binary script support, or runtime collision/model/weapon objects.
Deduplicated rawfile names still require block fixups and cannot be looked up by
name yet. Mounts currently last until shutdown; automatic shared/map archive
selection and unload lifecycle remain pending.

## Build and verify

### Preparing values for snapshot history

`codol_engine_state.c` now overlays named IW3 movement and camera fields into
the measured CoDOL player-state descriptors. It covers command time, client
number, origin, velocity, view/delta angles, bob cycle, movement direction,
gravity, speed, movement scale and view height. Ground world/none sentinels
translate from 1022/1023 to 2046/2047. Other wire fields are preserved for separate
gameplay adapters. Invalid ranges or nonfinite floats leave the output untouched.
Native tests exercise the real retained `playerState_t`, including the corrected
gravity/speed/scale offsets (0x90/0x98/0x254). This bridge is not yet called by
the server snapshot path; flags, weapons, animations and world entities still
need translation before replacing its IW3 serializer.
`CODOL_OverlayEnginePlayerMode` additionally translates the retained engine's
movement modes 0..8 to CoDOL's 0,1,2,3,5,6,7,8,9 and its follow/player bits
2/4 to 0x800/0x1000. The source evidence is `SpectatorThink` and
`ClientEndFrame` in `_g_active_mp.asm`; target modes and gates come from
`spawn_player.py`. The reference measures CoDOL spectator mode directly and
infers the other mode names from IW4 numbering. Tests cover all nine mappings,
follow/player combinations, clearing stale presence bits and atomic rejection
of unsupported modes. Other flag bits are preserved for separate adapters.
`CODOL_OverlayEngineWeaponSelection` translates current/alternate/offhand IDs
through the registered asset map into offsets 0x33C/0x340/0x328. Gameplay must
supply the resolved native alternate index. Unknown IDs fail atomically, and
zero explicitly clears a selection. Tests use CoDOL IDs above the IW3 7-bit
limit to verify that no truncation occurs. `CODOL_OverlayEngineHealth` publishes
health/max health in stat slots 0/2, preserving other array updates and rejecting
values that cannot survive the client's signed-short reader. These adapters
still require snapshot-path integration; equipped inventory, ammunition and
weapon actions are not inferred from selection alone.
`CODOL_OverlayEngineInventory` translates the retained engine's ownership bitset
into all 15 CoDOL equipped slots in native-ID order. Every slot is explicitly
published, including index-zero/flags-zero clears for removed weapons. An
optional gameplay-maintained native-ID bitset supplies the `usedBefore` flag;
this is not inferred from IW3's unrelated weapon-history arrays. Unmapped IDs,
null-weapon ownership and inventories exceeding 15 slots fail atomically. Tests
cover replacement, removal, empty inventories, full capacity and rejection.
Ammo translation remains dependent on native/CoDOL ammo and clip asset mappings.
The native `CODOL_OverlayEngineAmmo` bridge now accepts explicit slot bindings
from that mapping layer and reads the retained engine's `ammo`/`ammoclip`
arrays. It publishes one IW3 magazine plus an explicit zero second-hand count,
supports empty clip sentinels and zero reserve updates, and preserves unrelated
array sections. Invalid indices, keys and counts fail atomically; counts are
never wrapped into CoDOL's 9/11-bit fields. Native tests cover distinct weapon,
ammo and clip IDs, highest engine indices, range boundaries and clearing.
Asset-loader production of these bindings and snapshot-path wiring remain open.
`CODOL_OverlayEngineClient` translates the retained `clientState_t` team and
client number and accepts explicitly resolved CoDOL base/attachment model and
tag slots. It publishes all 16 target attachment slots, clearing the ten beyond
IW3's six and any removed attachments. Missing mappings, invalid slot ranges
and tags without models fail atomically. Native tests cover high model/tag
indices, removal, preserved perk words and invalid input. Model/tag mapping
production, rank/perk/vehicle translation and snapshot integration remain open;
the function never treats native asset IDs as CoDOL slots automatically.
`CODOL_RegisterModelName` and `CODOL_RegisterTagName` now publish resolved names
into the measured CS_MODELS (1315, 2048 slots) and CS_TAGS (5299, 64 slots)
ranges. They reserve slot zero, reuse existing names, retain assigned slots,
reject invalid names/range exhaustion and reset with the configstring bank.
Native tests fill both ranges, check repeated registration and preserve the
neighboring nonzero weapon slot. These functions allocate protocol slots only;
loaders still must resolve actual assets and supply names, and live asset
registration still needs reliable configstring publication.
The CoDOL build now also suppresses `SV_UpdateConfigData`'s IW4OL-only client-info
envelope and ACK checks. CoDOL's nine-byte client header has no config-data ACK;
client identity must instead come from its native client-state snapshots.

`CODOL_ReachDeltaValue` calculates the value the client receives after native
quantization. `CODOL_ReachPlayerFields` additionally preserves the base's
predicted fields when rov is zero. Tests compare these results with independent
reference decoders, including signed angles, negative zero and quantized floats.
Entity, client and HUD preparation now uses the same value codecs and feeds the
owned history ring through `CODOL_CommitReachedHistory`. Callers must use the
same base, context and rov as the successful snapshot writer. Engine translation
and send/ack integration are still pending.

Two reference edge cases were exposed during this work. The trimmed float writer
must use raw XOR when the old integer lies outside the trimmed range, otherwise
the reference reader retains its high bits (for example 100000 -> 3). The native
writer now takes that valid fallback. Also, `entity_codec.decode_value(-87)`
sign-extends an already signed short twice; tests use the dedicated player-state
reader for that arm, which matches a single signed-short conversion. Reference
files were not modified.

Linux/WSL prerequisites: `nasm`, `make`, `gcc-multilib`, `g++-multilib`.

```sh
make -j6
make test-codol
python3 tests/test_codol_wire.py --reference /path/to/alpha0022 -v
python3 tests/test_codol_usercmd.py --reference /path/to/alpha0022 -v
python3 tests/test_codol_configstrings.py --reference /path/to/alpha0022 -v
python3 tests/test_codol_delta.py --reference /path/to/alpha0022 -v
python3 tests/test_codol_player_arrays.py --reference /path/to/alpha0022 -v
make codol-archive
python3 tests/test_codol_archives.py --reference /path/to/alpha0022 \
  --root /path/to/1.1.1.13 --cache /path/to/codol_zones -v
./bin/codol_dedrun --codol-info
```

The Python tests use ctypes and the C compiler, with no Python runtime dependency
for the server. They also run on Windows with a native gcc available. The full
engine integration test target uses Linux ELF section garbage collection and is
run under WSL; MinGW's PE linker does not discard all unused engine references.

Windows executable cross-build from WSL (requires the i686 MinGW-w64 toolchain):

```sh
make -B -j6 OS=Windows_NT CC=i686-w64-mingw32-gcc \
  CPP=i686-w64-mingw32-g++ AR=i686-w64-mingw32-ar \
  OBJ_DIR=obj/codol-win32 bin/codol_dedrun.exe
```

The original third-party makefiles keep their objects and archives in shared
locations. **Use `-B` when switching between Linux and Windows toolchains** so
those libraries are rebuilt for the selected platform. The engine profile object
directories alone do not isolate third-party library formats.

On native Windows, use the upstream 32-bit MinGW/NASM prerequisites and
`mingw32-make bin/codol_dedrun.exe`; this native tool invocation has not been tested here. The supplied
Windows executable was cross-compiled with MinGW-w64. `shlobj.h` casing was fixed
to make that cross-build work on a case-sensitive system.

The upstream `release` target is disabled for the CoDOL profile.

### Validation in this workspace

The Windows executable was rebuilt again after per-client snapshot history,
send acceptance/recovery, entity hint-2 encoding, model/tag publication,
client-record collection and missile translation. The MinGW-w64 build passes,
and the resulting `bin/codol_dedrun.exe --codol-info` exits 0. Windows portable
suites pass: 18 delta, seven user-command, five configstring and three
player-array tests. This checks the current native code and executable startup,
not map loading or live client gameplay.

The Windows cross-build was repeated after the string-table database bridge,
script failure handling, prepared snapshot history, and send-acceptance changes.
The resulting `bin/codol_dedrun.exe --codol-info` exits 0. Windows differential
checks also pass: 17 delta tests, five configstring tests, three player-array
tests, and 518 cached string tables (132240 inline cells checked; 501634 pooled
references remain explicitly unresolved). These checks do not establish match
entry or runtime map loading.

- Built `bin/codol_dedrun` as a 32-bit Linux ELF executable.
- Built `bin/codol_dedrun.exe` as a 32-bit Windows PE executable with MinGW-w64.
- Rebuilt the preserved `GAME=iw4ol` Linux profile successfully.
- Ran `--codol-info` on both platforms: exit 0, explicitly reports not playable.
- Ran all seven Python/C wire tests on Windows, including alpha0022 byte parity.
- Ran all seven user-command tests on Windows, including 49 captured bodies.
- Ran the four archive differential suites: all 90 cached zones, four shipped
  encrypted fastfiles, generated archives, and malformed input cases passed.
- Ran `make test-codol` on Linux: native entry-point, send-failure, reassembly,
  crypto fixture, malformed-packet, user-command bridge and script registry
  ownership/override tests passed.
- `git diff --check` passed.

The Linux linker still reports the upstream assembly executable-stack and
text-relocation warnings. Engine map loading and CoDOL client gameplay were not
tested; those paths are not compatible yet.

## Required before a client can play

1. **Native bdDTLS association and lobby handoff.** Port INIT/COOKIE_ECHO/COOKIE_ACK,
   P-224 key export/agreement, cookie verification, NAT routing, security-key
   lifecycle, replay protection, and rekey/reconnect behavior from the reference.
   Connect DATA encryption/decryption at the UDP transport boundary. The current
   codec alone does not implement any of these session behaviors.
2. **CoDOL connection and message grammar.** Adapt `SV_ConnectionlessPacket`,
   challenge/connect/stats exchange and the opcode tables using `game-server.py`
   and `docs/iw4_reference.md`. Merely advertising protocol 187 is insufficient.
3. **User-command gameplay extensions.** The separate native wire structure,
   decoder, key hash, input filters, and engine bridge are implemented. Retained
   IW3 gameplay still needs CoDOL remote controls, dive, alternate weapon behavior,
   and related fields. Asset registration must populate the explicit weapon map;
   the retained engine currently has 128 slots, not CoDOL's 1024 wire IDs.
4. **Gamestate, configstrings and snapshots.** CoDOL has 6519 configstrings;
   weapon configstrings begin at 5362. Connect the remaining semantic indices,
   asset names and numeric-dvar producers to the implemented bank. The gamestate
   sender uses the CoDOL grammar, but `SV_WriteSnapshotToClient` still uses the
   IW3 snapshot serializer. Complete engine-to-CoDOL frame construction, bind
   the implemented history to each client's lifecycle, and commit prepared
   frames only after transport acceptance. Standalone section codecs and the
   message bridge do not yet supply a valid CoDOL world.
5. **Runtime asset and script compatibility.** The native fastfile/zone/rawfile
   reader and script-source mount path are implemented. Collision, weapon definitions,
   models, animation references and script builtins still require format-specific
   translation to the retained engine structures. Do not point the IW3 loaders
   at CoDOL assets and assume layout compatibility. Use the reference's
   `ffwriter`, `cm_terrain.py`, `cm_submodels.py`, weapon and animation work as
   evidence; replace runtime-pointer assumptions with native asset ownership.
6. **Gameplay parity and live acceptance.** Connect the native engine movement,
   combat, spawning, actors, match flow, classes and inventory to the translated
   state. Validate join, map load, movement, firing, death/respawn, two clients,
   packet loss, a counter wrap and a second match. None of these live CoDOL
   acceptance scenarios has been established by this port.

Fragment ACK-response/retransmission scheduling is also pending. Outbound first
passes never request ACKs (matching alpha0022); inbound ACK-only packets are
consumed. Incoming force-ACK requests are not answered yet. Sequence exhaustion
stops transmission rather than emitting reserved flag bits. These must be
completed as part of the session/transport stage.
