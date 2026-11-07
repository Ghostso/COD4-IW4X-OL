# C1 mortar activation audit — 2026-09-15

## Implemented prerequisite: native C1 location selector

C1 5161f0 takes `(shader, directional, optionalRadius)`. It is not the T5 typed selector. C1 516278..5162a7 reads string argument0, integer argument1, optional float argument2. Radius defaults0.15; explicit values normalize by compass-map height, or1000 without a positive height. 516360..5163b6 scales to31, rounds the single-precision product plus2^-30 with x87 round-to-nearest, and stores `selector&3 | (radiusBits&31)<<2 | (directional&1)<<7` in playerstate+230.

The retained setter accepted radius as argument1 and packed six radius bits. The C1 snapshot overlay omitted the selector byte. New `src/codol/script/codol_location_selection.c/.h` replaces the two VM registrations in `scr_vm_main.c`. `codol_engine_state.c` publishes captured native `ps.locationSelectionInfo` to C1+230, an eight-bit netfield. That native field is copied, archived, followed and cleared with the complete playerstate, so no extension or archive-version change is required.

C1 GScr_GetLocSelIndex5410f0 reads string handles at27d46fa. The configstring base is27d3cba (SV_SetConfigstring5d3122), yielding selector bank1312..1314. `codol_sv_assets.c` maps native slots827..829 to that bank during full refresh and individual updates. Client431276..43128b reads five radius bits; client478527 uses+230 to enter selection input mode. Existing IW4 airstrike calls already use `(map_artillery_selector, chooseDirection, targetSize)`, matching C1.

Parent reports build D7D2B32A includes this prerequisite. No live location-selection verification. Input completion still needs C1 review: current code translates confirm button20000 to retained10000 and preserves two selected coordinates, but directional angle is not represented in the retained command and cancellation mapping remains unverified. Targeting lifecycle is not yet complete.

## Real mortar reference and remaining constructor work

Primary stock reference: https://github.com/AtomicLizard99/Black-Ops-1-GSC-Raw-Dump/blob/main/RawDump/common_mp.ff/maps/mp/_mortar.gsc

Downloaded `obj/reference/t5-mortar/_mortar.gsc`, SHA256 ec594e1a90d3bc558ed38dd8d3cbb1ac4686249d3a3ed3e539f988fb9fd441ca. OpenBLOPS `Game/Server/game_mp/g_scr_main_mp.cpp:13892` and `Game/Server/game/g_missile.cpp:5698` supply LaunchBomb/DropBomb counterparts. IW5 mobile mortar and remote mortar are different rewards; no alias used.

C1 catalogue ID17 names mortar_mp, activation weapon mortar_mp, cost6, reward200, use hint MP_EARNED_MORTAR. ID32 mortar_pro_mp is separate. Stock T5 selects three positions (line111), starts three strikes, calculates a ballistic arc, then calls `owner launchbomb("mortar_mp", start, explicitVelocity)` at line367. Impact shellshock follows real projectile_impact, not guessed FX indices. T5 asset and sound names need verification against shipped C1 before deployment.

C1 VM LaunchBomb55bf20 resolves a player, requires exactly3 arguments, resolves the registered weapon, accepts original type0/2/4 at definition+340, reads start/velocity, normalizes a direction copy, then invokes531460. This differs from T5's additional gas type; do not import its enum offsets.

Offline shipped common_gametype_mp.ff mortar WeaponDef asset offset2b020f3 (zone-relative) has type4, class6, projectileSpeed9999 at794, lifetime30 at7a4, acceleration0 at7a8, curvature0 at7ac, guidance4 at8e0, destabilizationAngle0 at a40 and distance30000 at a48. C1 DropBomb531460 initializes a missile, explicit owner/parent handles, launch time, clipmask, lifetime, explicit velocity and real model. At531742 it starts gravity trajectory5; at5317a8..5317e9 explicit velocity replaces calculated projectile speed and is snapped to integers. Guidance4 remains gravity;5319c7 sets angular trajectory2 with z spin75 (float c84b84). Lifetime53169b..5316c8 uses7a4 * -1000 (c842b8), then subtracts from current time, adding the positive lifetime capped60s.

Do not fire a stock rocket and patch velocity afterward: retained G_FireRocket can dispatch missile_fire before the caller finishes initialization, invokes player lock acquisition, starts linear trajectory and treats every nonzero guidance as stationary except javelin. Existing weapon builder does not preserve these bomb/guidance/lifetime fields. Native type4 currently maps to grenade, requiring explicit review against collision/explosion consumers. Missing representations are implementation work, not justification for a fake barrage.

Direct excerpts: `obj/reference/t5-mortar/c1-location-bomb-disassembly.txt`. No bomb implementation or mortar GSC installed or counted. Next increment needs native bomb metadata/constructor, collision explosion/sound/projectile_impact verification, then three-target selection/cancellation/consumption and strike lifecycle. Death/disconnect must not leave selection armed or consume rewards before targeting succeeds.

Parent direction follow-up: C1 50ca63..50cb3b reads signed selected XY bytes,
then unsigned cmd+23 angle. It adds angle*(360/255) to compassNorth yaw,
normalizes with 61b730 to [0,360), pushes float then position. Retained confirm
emitted only position. CODOL_ConfirmLocation now uses the bound executed raw
command and emits position,yaw (VM reverse push order), preserving the existing
one-position path when no raw command exists. Both C/assembly objects compile.
No cancellation bit is present in the inspected C1 50ca58..50cb57 path; do not
invent an IW3 cancel-bit translation. Cancellation producer remains unresolved.

Cancellation producer resolved: client490700 location input routine sees
selection input state2 at490b0b and ORs cmd.buttons40000 at490b10. State1
confirms with20000 at490ae4/490af7. New native selection action reads accepted
C1 raw button edges directly and dispatches existing confirm/cancel script
notifications. Removed reduced-command confirmation remap to IW3bit10000.
C/assembly objects compile. This closes the previously missing cancel input;
live end-to-end cancellation/reward retention remains unverified.

## Constructor review boundary (not enabled)

Native `codol_bomb.c/.h` now contains the source-type4/guidance4 explicit-velocity
constructor. Metadata is captured by `codol_weapon_native.c` and exposed by the
asset registry; effective retained weapon type mapping stays unchanged. The VM
entry is deliberately unregistered. Both assembly integration sites remain behind
undefined `CODOL_MORTAR_INTEGRATION`; no new mortar gameplay is claimed deployed.

The constructor makes a real ET_MISSILE with owner/parent handles, gravity,
angular trajectory, projectile model, launch time and bounded lifetime. Explicit
velocity conversion truncates toward zero: C1 helper ae0410 uses cvttsd2si on
its SSE path, so this is not a round-to-nearest approximation. Only the observed
zero acceleration/curvature/destabilization mortar branch is implemented.

Contact interception now requires private constructor provenance, matching
entity generation and weapon identity; it cannot change previously deployed
type4 weapons created through retained firing paths. Per-entity and map reset
hooks clear this server-only state. Contact position and owner generation are
captured. The pending notification no longer borrows gentity.active.

Assembly review: G_RunMissile reconstructs all four retained MissileImpact
arguments after the C helper returns false (entity, trace, direction, contact
position). It never relies on the C callee preserving incoming stack slots.
G_ExplodeMissile captures useCount in ebp-b0 at entry; its outgoing argument
area ends at ebp-bc, below that local. Both the self `explode` notification and
radial damage callbacks are followed by inuse/generation checks before further
access. The owner `projectile_impact` notification also checks generation after
return. Its fourth argument is the still-live missile, following OpenBLOPS
G_MissileImpact, and fires after damage rather than using a freed entity.

Still required before enabling: collision-mask semantic verification, complete
impact FX normal/force-up behavior, actual C1 sound/selector asset availability,
and a reviewed staged mortar selection/strike/consumption script. Generic guided
LaunchBomb branches are not implemented or counted by this mortar-only helper.

## Reviewed next source increment and staged activation

Collision mask corrected to C1 0x280e091: native collision brush contents
(`codol_collision_native.c:143`), material flags and dynamic contents preserve
the original C1 values. No contents-bit remapping justifies retained 0x2806891.
Force-normal-up mapping now reads C1 bytebdc. At52eeae..52eebc it selects
C5511c, verified three floats(0,0,1), otherwise the trace normal. Parent built
these safe changes in571E837F; constructor remains unregistered/gated.

`obj/mortar-stage/maps/mp/killstreaks/_mortar.gsc` contains the actual activation
stage: three confirmed positions using shipped map_mortar_selector, ground
traces, detached cancellation cleanup, reward-commit boundary, and3x2 real
projectiles with native damage/FX/sound. Collector and cancellation endons live
only in separate threads; the persistent killstreak-use caller waits on done
and reads an explicit result. The collector unconditionally waits for its first
confirmation before completion, avoiding a completion lost before caller wait.
The same selection instance guards cleanup and pending commit identity.

T5 _tweakables.gsc369..370 explicitly sets3 cannons and2 shells. The stage uses
2.5 seconds between targets and1.1..1.5 seconds between shells,75-degree
ballistics over6000 horizontal units, beginning30% into the arc. C1 trajectory5
dispatches via40cca8 to40cb36;40cb66 uses doubleC847a0=400, proving gravity800.
The six-origin/closest-line directional selection follows T5, with signed
coordinate subtraction corrected to use positive distances beyond map bounds.
It checks mapped spawn bounds rather than borrowing undefined T5 globals.

Asset evidence saved in `obj/reference/t5-mortar/c1-assets.json` and two
c1-mortar-strings JSON files. map_mortar_selector is material5 at3614f04 in
common_gametype_mp. T5 `prj_mortar_incoming_00/01/02` and launch aliases were
absent from MP common/gametype and their patches. They are intentionally not
invented or replaced with unrelated sounds. Real explosion sound/effect remains
selected by the actual mortar weapon on C1. T5 extra HUD danger markers and
shellshock profile behavior are not counted as implemented by this stage.

Parent integration required after review:

- Include codol_bomb.h and register `codol_launchmortarbomb` to
  `CODOL_Scr_LaunchMortarBomb` (not a claim of general LaunchBomb support).
- Enable the two `CODOL_MORTAR_INTEGRATION` assembly consumer blocks plus the
  self-notify guard together; constructor provenance limits their new effects.
- Initialize `_mortar::init()` before initKillstreakData; classify mortar_mp as
  deadlyKillstreak so existing grace-period restrictions apply.
- After successful stillOwned check, usedKillstreak, queue removal and owned-item
  refresh, call `self maps\\mp\\killstreaks\\_mortar::commitMortar(lifeId,kID)`
  for mortar_mp only. Selection never launches a projectile before this point.

No automated tests or live activation performed by worker. Staged script not
installed. Source helpers and current integration are compile-coherent, pending
parent activation review.
