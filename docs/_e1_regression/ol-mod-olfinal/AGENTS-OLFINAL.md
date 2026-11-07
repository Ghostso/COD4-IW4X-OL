# ol-mod — OLfinal fork, agent entry point

**Last updated: 2026-09-06.**

This file is **ours**. `AGENTS.md` and `.agents/AGENTS.md` in this repo are **dest1yo's upstream
documents** — they describe the 3.3.3.3 work, they were last touched 2026-08-16, and they are
deliberately left alone so this fork does not conflict with upstream. Read them for the long-lived
engineering conventions; read this one for the OLfinal fork.

**THE FULL PROJECT HANDOFF LIVES IN THE OTHER REPO:**
`Downloads/CODOL-main/CODOL-main/AGENTS.md`, and the running log is
`re/OLFINAL-FFA-HANDOFF.md` **§191ak**. This file covers only what is specific to building and
changing the plugin.

**2026-09-06 feature checkpoint:** see the other repo's
`re/demo-re/34-equipped-perks.md`. Session schema 6 carries class perks (v5
read-compatible). Profile perk integers are catalog ID + 1; the table's column
0 is the bit index, not its row ordinal. Native ability masks/floats travel in
clientState fields 2..16 and 60..86. `RunDiagnostic` name `equipped-perks` resolves
all five classes without a match. Live class/respawn confirmation remains open;
desktop input activation failed during unattended testing. All seven suites and
the 50 ms scheduler run passed. Do not enlarge WorldClientState for these fields.
The subsequent checkpoint is `re/demo-re/35-equipped-equipment.md` in the CODOL
repo. Schema 7 adds equipped lethal/tactical requests and double-ammo flags,
read-compatible with v5/v6. Backend and live client agree on all five classes;
grenade grants/projectiles are still missing. The native matchmaking test
committed a gamestate but failed before becoming active; its cause is open.
The same checkpoint now covers selected offhand field 53 and button-slot fields
109..111. All four are networked; prior absence/dead-field claims are disproved.
Their source projections use existing padding so WorldClientState stays 25104.
Checkpoint `36-equipped-grants.md` now implements equipped inventory/ammo grants
once per life and offhand switch/use admission. Projectiles, tactical effects,
and live throw confirmation remain open; read its evidence limits. The aligned
DM/RustLong diagnostic reached active=1 with acknowledged snapshots. Client
memory confirms class 1 frag/smoke grants and corrected perk HUD cache 3/5/13;
visual icons, class switching and respawn still need confirmation.
Checkpoint `37-native-trajectories.md` adds `EngineBindings::evaluateTrajectory`
using the retained 0x410BD0 plain trajectory evaluator. Its build and seven suites
pass; a separate live ABI probe passes 14 vectors. It is not yet connected to a
missile owner. The new adapter build has not replaced the running grant build.
Checkpoint `38-missile-wire.md` adds ET_MISSILE source projection, snapshot writer,
all three admission paths and six independent decoder fixtures. Two source member
names changed to `lerpData0058` and `modelScale`; storage/defaults are unchanged.
WorldClientState still passes its 25104-byte assertion. Production throw staging,
collision/fuse/damage are next; this build has not replaced the running grant build.
Checkpoint `39-offhand-continuation.md` adds owned event-73 continuation, native
offhand aiming, and cooked-fuse access without growing WorldClientState. Handler
and native-mirror rejection both restore a consumed fuse; eight private native
hold probes pass. All suites and the plugin build pass. Production still defers
the throw until missile spawn/simulation is connected; this build is not deployed.
Checkpoint `40-missile-ownership.md` implements the staged missile spawn and world
lifetime owner. `pendingEntitySpawns` replaces the bullet-only vector with typed
variants, without changing enclosing size. Allocation, fuse/native rollback,
removal, exhaustion and reset tests pass at both cadences, as do all seven suites
and the plugin build. Simulation/collision/fuse expiry and the production throw
connection remain open; the stored fuse deadline is not scheduled yet.
Checkpoint `41-missile-flight.md` adds `SV_ComputeMissileFlightStep` with retained
trajectory/trace providers, impact-time/start-solid handling and fuse-due reporting.
Suites and plugin pass; it is not installed in the world frame runner. Next,
recover absolute demo entity scalars for bounce calibration: existing entity
captures frequently contain raw deltas, and framing checks do not prove values.
Checkpoint `42-absolute-entity-values.md` in CODOL closes that decoder gap with
native codec probes and full 6,160-snapshot DM parity. Its trajectory miner emits
absolute native words; the historical DemoDB scalar capture remains raw.
Checkpoint `43-missile-world-frames.md` connects configured missile simulation
to the end-frame transaction, including retirement, rollback and generation reuse.
Fresh throws are eligible at their spawn clock. Suites and plugin pass; production
throw/contact/explosion continuations are still open and this build is not deployed.
Checkpoint `44-grenade-launch.md` implements ordinary launch calculation and
loaded speed/fuse/cooking fields, with retained vectoangles 764C10. Eleven retail
Semtex launches, native probes and suites pass. Production contact/effects,
rotation random policy and event137 in-hand explosion still need integration.
Checkpoint `45-semtex-world-contact.md` adds world sticking, precise contact-plane
ownership and native rollback tests. The old missile `field0094` is confirmed
`surfaceType`; storage is unchanged. Ten retail world stops and all suites pass.
Production attachment, frag bounce and explosion/tactical continuations remain open.
Checkpoint `46-area-damage-batches.md` expands atomic player damage to all 18
clients and delays vocals/regeneration until successful publication. Full-server
damage, death and native rollback tests pass at both cadences. Radius selection,
cover and grenade integration are still open; the build is not deployed.
Checkpoint `47-player-radius-damage.md` implements bounds falloff, five-point
cover exposure, cone gating and shield scaling for up to 18 players. All suites,
both cadences and plugin pass. Read its two-exclusion/null-priority trace evidence
before binding production visibility. Shield flags differ in IW4/Ghosts; neither
is imported as a CODOL constant. Script/effects/detonation integration remains open.
Checkpoint `48-radius-visibility.md` connects a world-owned visibility runner to
retained world/glass, static-model 66A3D0 and DObj contents 783290 geometry, with
two independent exclusions. Private native probes produce real hits and pass
mask/canary controls on both processes. Suites/plugin pass. Production detonation,
effects and script dispatch remain next; this build has not replaced the grant stack.

---

## Push rule

`origin` is **dest1yo's** repository. **Never push to it.** Push only to `olfinal`
(`edenfps/ol-mod-olfinal`).

## Build

```bash
export VCPKG_ROOT="C:\\Users\\bobya\\vcpkg"    # without this, xmake HANGS for ten minutes
export XMAKE_ROOT=y
export LINK="crypt32.lib advapi32.lib user32.lib"
export PATH="$PATH:/c/Users/bobya/tools/xmake/xmake"

xmake build ol_game_server
xmake build ol_game_server_tests && xmake run ol_game_server_tests
```

`xmake` resolves **every** `add_requires` in the project at configure time, so "my target has no
dependencies" is not protection. And `xmake … | Select-Object -Last N` shows nothing until the
command exits — during a hang the output looks empty rather than stuck. Redirect to a file.

Seven suites must pass: `ol_game_server_tests`, `ol_backend_tests`, `ol_playerdata_def_tests`,
`ol_dedicated_control_tests`, `ol_lua_runtime_tests`, `ol_localnetworking_tests`,
`ol_platformwrapper_tests`.

**The scheduler suite is frame-rate independent and must stay that way.** It passes at both 100 and
50 ms via `OLMOD_SV_FRAME_MS`, which is how you show a change is behavioural rather than tuned to
one number. Three tests used to encode a 50 ms *timeline* — a literal frame interval, a clock jump
assumed to be a frame, and two jumps assumed to be enough frames for a reset and a respawn. If you
add a test that advances time, express it in **frames or milliseconds derived from
`SV_FrameMilliseconds()`**, never a literal.

## Where things are

| file | what |
| --- | --- |
| `src/game_server/server_mp/sv_main_mp.cpp` | the frame scheduler, `SV_FrameMilliseconds`, the think budget |
| `src/game_server/server_mp/sv_client_mp.cpp` | client ingress, the pending-usercmd queue |
| `src/game_server/server_mp/sv_snapshot_mp.cpp` | snapshot encode; the netfield writers live here |
| `src/game_server/EngineBindings.hpp` | **every RVA into `out.exe`**, each with its provenance |
| `src/game_server/ClientProcessPatches.cpp` | in-process byte patches (unlock-all, plaintext config, fps ceiling) |
| `src/game_server/ClientCommandTrace.cpp` | the live diagnostics: command trace, playerstate mirror, fps probe |
| `assets/game_scripts/gametypes/*.lua` | gametype rules |

## Environment switches

| variable | effect |
| --- | --- |
| `OLMOD_SV_FRAME_MS` | server frame interval. **Default 100** — retail's own cadence |
| `OLMOD_SV_THINK_BUDGET_MS` | override the think budget; default is `2 × frame`, `0` means drain |
| `OLMOD_PLAINTEXT_CONFIG` | `0` to restore the encrypted `config_mp.cfg`; **on by default** |
| `OLMOD_MAXFPS_CEILING=<n>` | raise `com_maxfps`' registered max above 200 |
| `OLMOD_UNLOCK_ALL=1` | own every item |
| `OLMOD_LOG_ENTITY_EVENTS=1` | histogram every predictable event the pmove produced, with out.exe's own networked/local verdict |

All of these must be set **inside** the elevated process that launches the stack — `RunAs` does not
carry the caller's environment.

## Checkpoint 49

`49-grenade-explosion-publication.md` in CODOL records the measured event98
generic effect, shared brush/explosion writer and atomic frame publication of
missile removal, effect and script damage. Target life, native rollback, slot
reuse and effect expiry are tested. Health still commits through gameplay scripts.
All suites, 50 ms and plugin build pass. Production throw/detonation calculation
and tactical continuations remain open; the deployed grant stack is unchanged.

Checkpoint `50-dry-grenade-detonation.md` adds the loaded blast parameter binding
and due-fuse calculation returning checkpoint49's detonation. Cover/falloff,
thrower damage, life metadata and visual contact normal are composed and tested.
Both live processes agree on frag/Semtex fields; effect-up +3833 follows the IW4
timer-relative layout and CODOL Semtex demo. All suites/plugin pass. Production
throw/frame wiring, water, shields and tactical continuations remain incomplete.

## Conventions this codebase actually holds to

- **Every constant carries its provenance.** `CODREF(...)` names the build and address a value came
  from; `CODDIFF(...)` marks a deliberate divergence and says why. A constant with neither is a
  guess, and guesses from four different games are what put a Ghosts queue in a CODOL server.
- **Comments record the measurement, not the intention.** The ones that earned their length quote
  log lines and player sentences.
- **When a comment turns out to be wrong, correct it in place and say so.** There is a comment in
  `sv_snapshot_mp.cpp` that does exactly this about its own neighbouring fix.
- **Never hook a per-frame client function** — it killed three clients. State needs a *reader* on a
  thread, not a trampoline. Hooks are for events.
- **A diagnostic must not do slow work on the bridge's request path**; start a thread and report to
  the log. A synchronous sweep once stalled a live match.

Checkpoint `52-podium-animation.md in CODOL re/demo-re` resolves native CCS type-18 animation names,
serializes podium pose/time/full orientation, and installs rank-specific rifle idles.
All suites and both cadences pass. Fresh live client accepts the named idle with
its seven-model outfit and returns to frontend. Emotes, held weapons, moving
camera and results content remain. Killcams and grenade work are excluded.

Checkpoint 53 in CODOL `re/demo-re/53-podium-held-weapons.md` adds linked podium
weapons using the separate tag band 12248. Suites, both cadences and ten wire
fixtures pass; live player testing shows an A/default pose and no visible held
weapon despite the accepted native fields/DObjs. Use **mp_nuked** for the user's
queue. Their 2026-09-06 RustLong attempt returned a blank loading error.

Checkpoint 54 in CODOL `re/demo-re/54-podium-animation-commands.md` closes the
missing packet-animation stream formerly emitted empty under the stale
"packet sounds" label. All 6,160 retail endpoints pair exactly; 135 records
are reconstructed. The server writes typed goal/clear commands, CCS aliases,
equal-record baseline reuse and four-frame redundancy. All suites, both
cadences and independent wire fixtures pass. The fresh mp_nuked player
screenshot confirms the winner in the retail rifle idle with its rifle attached
and visible. The earlier A/default pose and empty hands are closed; timed rank
emotes are the next end-match implementation step.

Checkpoint 55 in CODOL `re/demo-re/55-podium-emote-sequence.md` implements the
complete retail rank-animation timeline through match exit: staggered emote-ins,
three main emotes, first/third emote-outs and first-place idle restore. The world
publishes clear/goal and weight-zero/clear/goal batches with measured clocks and
four-frame lifetimes. All suites, both cadences, independent wire fixtures and
the plugin build pass. Automatic review rejected the first elevated host launch
before it executed. A later fresh mp_nuked cycle completed, and the player
reported seeing an emote work while all
four first-place animation events logged on schedule with `frameReject=none:0`.

Checkpoint 56 in CODOL `re/demo-re/56-podium-camera-motion.md` adds the retail
camera entity's type-7 500 ms entrance and type-4 16500 ms continuation. The
scriptmover writer now publishes its measured trajectory delta, clocks and
durations in native field order, while static mover packets remain compatible.
All suites, both cadences, twelve independent wire fixtures and the plugin build
pass. A fresh elevated mp_nuked match accepted camera entity 182 and its type-4
transition on the retail offsets, retained `frameReject=none:0`, ran the emotes
and published `EXE_MATCHENDED` at +32700. Player visual confirmation of the
subtle camera motion remains separate.

Checkpoint 57 in CODOL `re/demo-re/57-podium-card-identity.md` fills the final
known account field in the podium callsign record. `SvScoreboardEntry` carries
the connected slot's authenticated XUID, and the AAR `J`/`K` transaction writes
its high and low dwords at `9626/9630 + 8*clientNum`, exactly matching the parsed
profile def. Two-row byte fixtures, the one-player 119-byte command, all seven
suites, both cadences and the plugin build pass. Fresh elevated `mp_nuked` demo
`C-2026-9-6[13-20-9]dm.demo` contains all 48 identity runs at offset `0x259A` as
`000000002c0f0100`, the exact hi/lo encoding of XUID 69420; the podium sequence
and clean match exit remained intact.

Checkpoint 58 in CODOL `re/demo-re/58-ffa-outcome-notify.md` implements the
retail FFA outcome notification at +1100 through +11100: title, end reason,
three placement names and the rank/participation match bonus. HudElem types
3/4/8 and fields 22/28..32 serialize through type-specific aliases so the
pinned `WorldClientState` size stays unchanged. All seven suites, both
cadences and the plugin build pass. Fresh elevated `mp_nuked` demo
`C-2026-9-6[14-6-35]dm.demo` carries the exact one-player subset and retains
`frameReject=none:0`, the podium schedule and +32700 `EXE_MATCHENDED` exit.
Persistent XP, tie-title presentation and the multi-client live variants are
still open; match-ending killcams remain outside the current scope.

Checkpoint 59 in CODOL `re/demo-re/59-ffa-aar-bonus-and-ties.md` applies the
frozen DM match bonus to the AAR scoreboard row and makes the HudElem consume
the same cached value. Retail proves row XP 5997->7796 beside bonus 1799; fresh
`mp_nuked` demo `C-2026-9-6[14-49-59]dm.demo` proves XP 0->35 and the live
Action Report shows XP 35. FFA placement now uses kills, fewer deaths, then
stable slot, and OLfinal text 367 supplies the shipped equal-score/equal-deaths
tie title. All seven suites, both cadences and the plugin build pass; podium and
+32700 exit remain intact. Persistent account progression, per-kill rewards,
GP and multi-client result variants remain open.

CODOL `re/demo-re/60-live-ffa-video-reference.md` catalogs the user-supplied
August 8, 2021 live Afghan FFA recording. It shows the desaturated start
countdown, live perk HUD, twelve-player scoreboard, 30 kills = 1500 points,
the score-limit final-kill replay, three-card podium and live emotes. This is a
visual source rather than packet timing; its score-limit end ordering remains
an explicit branch question against the time-limit theater demo.

Checkpoint 61 in CODOL `re/demo-re/61-offhand-movement-rollback.md` accepts
native offhand prepare's `ps+0x400` bit `0x02` after validating the selected
weapon at `ps+0x3E4`. This prevents the transactional usercmd rollback that a
remote UK player saw as a duplicate shot. Tactical and lethal offhand use both
completed live without movement rejection. The intermittent knife/respawn HUD
ammo fault remains a separate open issue.

Checkpoint 62 in CODOL `re/demo-re/62-ffa-aar-round-and-kill-xp.md` adds the
retail root `aarRoundNumber = 1` patch at byte 59 and a gametype-owned `addxp`
method. Production DM now awards 50 match XP for an enemy kill and 50 more for
a headshot, independently supported by the retail AAR deltas and IW4
`_rank.gsc`. All seven suites, both cadences and the plugin build pass. Fresh
one-minute `mp_nuked` demo `C-2026-9-6[16-33-15]dm.demo` carries the round
0->1 transition with the existing XP 35 match bonus; the live Action Report
opens and shows 35. Persistent service-4 XP, exact root bonus multipliers, GP
and multi-client/score-limit live variants remain open.

Checkpoint 63 in CODOL `re/demo-re/63-ffa-outcome-visual-correction.md` fixes
the pre-podium result overlay after the live player saw only `0:00`. The former
HudElem decode omitted acknowledged-snapshot baselines and map-center coordinate
reconstruction. Direct `out.exe` renderer `0x538B70` and the corrected retail
decode prove type-1 localized text plus Y positions 20/66/110/154/192/230 for
the title, reason, placements and bonus. The server now writes that exact
template. All seven suites, both cadences and the plugin build pass; fresh
elevated `mp_nuked` visual validation is pending.
