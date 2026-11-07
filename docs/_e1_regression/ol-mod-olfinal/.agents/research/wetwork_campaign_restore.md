# Wetwork campaign restoration

Status: implemented from capture and shipped MapEnt evidence; live end-to-end
validation is still pending.

The authoritative capture is
`C-2021-7-25[22-11-33]coop.demo`. The recorded session is 7:51 long, loads
`coop_training_mp_cargoship` with gametype `coop`, creates the player at server
time 10950, begins mission success at 475600, calls the match-end owner at
480850, and emits `EXE_MATCHENDED` at 481850. The user replayed the capture in
theatre mode and confirmed it is the intended Wetwork mission.

The implementation is split between `gametypes/coop.lua`, the cargoship map
layer, and native server primitives. It currently provides:

- a campaign gametype that disables PvP scoring and generic multiplayer
  respawns;
- the shipped cargoship collision, logical MapEnts, trigger hulls and actor
  spawners;
- the decoded 10950--182350 insertion path, two Blackhawk presentation
  models, thirteen initial ally agent rows, and recorded opening animations;
- all major bridge, hallway, cargo-hold, sinking, deck and extraction route
  gates from the shipped trigger names;
- the recorded single-objective stream and map/vision/ambient/weapon command
  handoffs;
- all nineteen map-specific positional sound events from the capture, resolved
  through the loaded client's sound-alias constant-string table and published
  as the same temporary `ET_EVENTS` carriers used by retail;
- all ten scripted RPG lifetimes from the helicopter insertion, including 122
  usable captured trajectory states, exact birth/rebase timing, and removal at
  each recorded lifetime boundary; these persistent `ET_MISSILE` carriers are
  presentation-only so they cannot enter the grenade collision/damage runner;
- checkpoint save and death respawn at route boundaries;
- MapEnt-driven hostile waves, reusable hostile agent slots, rifle/UMP
  attachments, traced actor fire, damage/death callbacks, and the explicit
  force-goal movement authored on runner spawners;
- cargo-door interaction and the recorded sinking presentation timeline;
- the magazine-blast knockdown transition: shellshock profile 9 with its
  recorded 14-second lifetime, the complete 362950--375950 player-origin
  track, movement ownership, and the measured final link-flag change;
- both MapEnt-authored hull-breach gates and the three animated hull panels:
  `hullpanel01` starts `iu_hull_breach_panel_01` at the first rupture, while
  `hullpanel01a` and `hullpanel02` start their named panel animations at the
  second rupture; the server publishes the script-mover animation state and
  its ordered packet-animation clear/goal commands together;
- the complete authored destruction-event stream: all 29 exploder
  configstring records, their 30 timed `EV_EXPLODER` activations (the intro
  record is reused during the escape), and all twelve `EV_EARTHQUAKE` camera
  shakes with captured origins, scales, radii and durations;
- the six `EV_PHYS_EXPLOSION_SPHERE` impulses from the sinking escape, with
  their captured origins, inner/outer radii and magnitudes, so nearby ragdolls
  and dynamic props receive the same client-side impulse track;
- the three MapEnt-authored flood/fall death volumes;
- the decoded 440250--475600 extraction flight with 133 player-origin keys, a
  CH-46 presentation model, recorded player movement flags, and exact mission
  success/match-end timing.

New native Lua methods own only state the dedicated server must author:
`sendservercommand`, `setconfigstring`, `servertime`, `savecheckpoint`,
`respawn`, `setobjective`, `spawnactor`, `setactorstate`, `setactorposition`,
`actorfire`, `playsoundat`, `triggerexploder`, `earthquakeat`,
`physicsexplosionsphereat`,
`spawnscriptedmissile`, `setscriptedmissile`,
`playanimation`,
`setscriptedposition`, `clearscriptedposition`, `setshellshock`, and
`finishmission`. The source
loader allows map scripts up to 1 MiB because the two decoded flight tracks
alone exceed the old 64 KiB metadata ceiling.

The destruction carriers use the exact retail protocol recovered from the
demo. `EV_EXPLODER` is event 130 and selects configstring
`11990 + eventParm`; `EV_PHYS_EXPLOSION_SPHERE` is event 131 and places inner
radius, outer radius and magnitude in entity-state fields 11, 12 and 18;
`EV_EARTHQUAKE` is event 136 and places camera-shake scale, radius and duration
in those same fields. The COD4 client source independently identifies the
corresponding event handlers. The server serializer, snapshot admission and
temporary-entity lifetime paths now cover all three event types, including
multiple events emitted in one frame.

This is not yet a 1:1 claim. The missing work is concentrated in live proof and
presentation fidelity: navmesh/cover-based ally and hostile choreography,
localized subtitles and non-positional dialogue layers, live hostile RPG
targeting/damage after the recorded insertion sequence, residual particle/water
presentation outside the authored exploder stream, the global physical ship
tilt and large hull/world breakup beyond the three animated breach panels, and
the blast's linked view-angle animation, plus exact checkpoint/failure
behavior. The existing
actor force-goals move on authored direct legs because native campaign nav is
not restored. No client has yet completed this implementation from insertion
through the result screen, so any start-to-finish statement must remain an
implementation claim until that run succeeds.

Useful reproduction commands:

```powershell
python tools/demo-re/demoq.py --demo '<demo>' cmds --from 0
python tools/demo-re/demoq.py --demo '<demo>' ps --from 10950 --to 182350 --changes --field origin
python tools/demo-re/demoq.py --demo '<demo>' ps --from 362950 --to 375950 --changes --field origin
python tools/demo-re/demoq.py --demo '<demo>' ps --from 440250 --to 475600 --changes --field origin
```

The Lua load boundary is covered by `ol_lua_runtime_tests`; the native map,
trigger, actor, damage, checkpoint, objective, campaign result, exploder,
physics-impulse, camera-shake, shellshock and named script-model animation
primitives are covered by
`ol_game_server_tests`. The destruction test also verifies the captured float
and duration fields survive the
`ET_EVENTS` wire writer. These tests establish source/native consistency, not
visual or end-to-end mission fidelity.
