# Native C1 radar types and SR71 increment (2026-09-14)

## Source and evidence

New native `src/codol/snapshot/codol_radar_types.c/.h` supplies missing C1
spyplane/satellite inputs, captured state and snapshot fields. Existing
radar-enabled/blocked/EMP behavior remains separately owned.

Direct C1 evidence:
- Client field table c3c1b0 is `hasspyplane` integer at gclient3890;
  c3c1c8 is `hassatellite` integer at3894. These were absent natively.
- 43322e checks ps224 for swept spyplane updates;433272 checks ps228 for
  continuous satellite updates, calling433170 with current client time.
- 433170 copies enemy position into continuous satellite position10/14 and,
  on the client dvar interval, static satellite position1c/20 and timestamps.
  Only recent actor positions qualify (500ms freshness); server publishes
  ordinary entity positions/angles, not fabricated map pings.
- 435730/43573a consider224/228;43574d selects nonzero228 before224.
  Type3 selects dvar16c754c, type2 selects16c7558, otherwise16c7504.
- The C1 satellite enemy material is `compassping_enemysatellite` c43128,
  registered44ec2a and stored16d9b94;434eab uses it for the static image.
  Directional material `compassping_enemydirectional` c43108 is registered
  44ec19 and stored16d9b90. At434ccb/434cdf the renderer subtracts actor
  yaw24 from map/view heading, normalizes through61b730 and draws that
  material beginning434cf1. Satellite ping timers feed this existing renderer.

The prior radar-state header inferred224 was IW4 radarMode from nearby
strings; this was incorrect and is corrected. No actual old224 publisher
existed. Native radar overlay previously supplied only21c,220 and EMP10.

OpenBLOPS `g_active_mp.cpp:2668` provides the authoritative producer policy:
start with teamHasSatellite/teamHasSpyplane, then a nonzero individual
hasSatellite/hasSpyplane overrides the team value. `g_scr_main_mp.cpp:13603`
provides set/getteamsatellite team-name validation and integer storage.
These semantics are implemented without treating types as booleans or max.
Raw script integers are retained; copied network state has the low two bits,
matching C1's field widths. Both setter/getter pairs and two client fields
are registered. Existing IW4 hasRadar/setTeamRadar requests explicitly imply
normal spyplane type1 only when no C1 spyplane type is present.

## Ownership and lifecycle

Inputs are separate live per-client/team values. CODOL_PublishClientRadar
captures them once at the existing authoritative frame producer into the
playerState extension. Snapshot overlay reads only the supplied copied state.
Archive delta writes/read/preflight include the two types; spectator copies
therefore preserve the followed player's captured radar rather than querying
live owners. Existing client radar resets clear input and live captured types;
map input reset clears all team/client inputs. Recent corpse and throwback
fields were preserved.

## Staged SR71 behavior

`obj/radar-stage/maps/mp/killstreaks/_sr71.gsc` registers real `sr71_mp` use.
The staged `_uav.gsc` calls its initializer; the separately reviewed C1
catalogue initializer then discovers/pre-caches its actual row19 activation
weapon `radardirection_mp`, dialog, hints and icons. No pro alias is registered.

Team games set the satellite type on the owner's team; native frame production
covers present members, later joins and respawns. The team effect survives
owner death/disconnect/team change for its remaining lifetime. FFA owns an
individual effect, reapplies it after respawn, and revokes it on team change;
disconnect uses native input reset. Overlapping activations extend the deadline
through the newest activation. Expiry and game end restore the previous input
when the SR71-owned type1 remains present. No UAV plane/entity or movement
proxy is spawned; the real C1 satellite renderer consumes entity snapshots.

Lifetime is explicitly an adaptation:30 seconds comes from local primary IW5
`_uav.gsc:19,541` directional_uav using level.radarviewtime. No C1/T5 SR71
script duration was recovered, and this is not claimed exact C1 timing. An
exact recovered duration should replace this isolated constant. Cosmetic SR71
flyby model/effect is not implemented. Client-driven immunity/jamming and
actual displayed enemy direction require live verification; no server-side
blanket enemy reveal override or invented perk exemption was added.

Source review only. No tests/builds/process changes or live script edits.
Parent must rebuild/restart before deploying the staged scripts, since their
hassatellite/getteamsatellite/setteamsatellite facilities are new native APIs.
