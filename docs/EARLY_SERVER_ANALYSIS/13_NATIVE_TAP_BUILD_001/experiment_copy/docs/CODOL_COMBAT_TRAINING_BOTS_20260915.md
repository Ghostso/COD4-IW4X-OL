# Native CoDOL combat-training bots — source increment

## Authority and scope

User requested T5 combat-training style bots using `D:/CoD/OpenBLOPS`, GSC adaptation and available CSV waypoint paths. Native IW4OL facilities may be rewritten for C1. No hooks, client changes, teleportation, script-driven damage, or proxy AI entities are used.

Primary local reference: `D:/CoD/OpenBLOPS/Game/Server/server_mp/sv_bot_mp.cpp` and `Game/Server/game_mp/g_client_script_cmd_mp.cpp`.

Reference entry points reviewed:

- `SV_BotThink` line299: clear input each command; skip archive/dead; update weapon, threat, sight, movement, combat, reload, use override.
- `SV_BotSetScriptGoal`182 / clear204: separate persistent goal flag/vector/radius.
- `SV_BotSetScriptEnemy`223 / clear246: explicit threat override.
- `Bot_UpdateThreat`538: team/alive filtering, FOV/visibility acquisition, close-threat retention, ten-second lost-sight memory.
- `Bot_UpdateBestThreat`797: threat prioritization uses distance, angle, target retention and probability. This increment uses closest visible candidate plus close-target retention; it does not claim the entire T5 priority policy.
- `Bot_UpdateDirection`1702 / `Bot_UpdatePitch` / `Bot_UpdateYaw`: view tracking and command angle minus delta_angles.
- `Bot_UpdateCombat`2298: visible alive target, reaction deadline, real weapon ammo, nonautomatic trigger delay, actual attack command.
- `Bot_UpdateReload`2264 and registration2984: real reload input and timing/distance/FOV dvars. Defaults retained for included parameters: FOV65, close256, reaction500..1000ms, nonautomatic400..600ms.
- Player method wrappers4145 onward validate a bot player receiver; setScriptGoal takes vector/radius; pressUseButton takes seconds converted to milliseconds.

No T5 bot GSC files were found in OpenBLOPS. The staged integration uses the mounted IW4 gametype callbacks rather than claiming nonexistent script provenance. Existing `_menus.gsc` dispatches `level.autoassign` and `level.class` for team/class choices. Those same callbacks preserve class grants, playerdata handling, spawn, perks, equipment and death lifecycle for bots.

## Source implemented

`src/codol/player/codol_bot.c/.h`:

- Opt-in combat AI per real NA_BOT client. Entity generation checks and map/time reset prevent stale control of a reused slot. Human commands never enter this override.
- Real visible enemy acquisition, faction/FFA filtering, last-seen target location, reaction delay, smooth shortest-angle aiming, ADS, dual-hand trigger selection, paced nonautomatic fire, empty-magazine reload and delayed dead-player use input.
- Patrol or script-goal graph routes, goal radius, current waypoint stance and C1 jump input for climb/mantle negotiation. The existing C1 movement/weapon implementation performs actual movement and damage.
- Script methods enableCombatBot, setScriptGoal, clearScriptGoal, hasScriptGoal, setScriptEnemy, clearScriptEnemy, pressUseButton; loadBotWaypoints global.
- Typed finite argument validation and native real state; no success-only methods.

`src/codol/player/codol_bot_nav.c/.h`:

- Strict bounded directed graph reader, maximum2048 nodes/32 neighbors, finite positions and neighbor range checks. Count must match row count. Missing/invalid load drops the previous graph; it cannot navigate another map's stale data.
- A* using Euclidean edge lengths and admissible Euclidean heuristic. Unreachable or over-capacity paths produce no movement.
- CSV first line is node count. Following columns: xyz, space-separated zero-based links, stance/action, optional view angles, optional tactical target, unused tail. Types seen: stand/crouch/prone/climb/claymore/grenade/javelin. Tactical-placement labels remain traversable but their placement tactics are NOT implemented.
- Last three columns are not interpreted as extra graph edges or commands.

Shared integration:

- `src/sv_main.c::SV_BotUserMove`: enabled combat bot gets a full native C1 command, stages BOT provenance, then calls normal SV_ClientThink. Legacy manually controlled bots preserve their original path.
- `src/scr_vm_main.c`: register new bot facilities after existing manual bot methods.
- `codol_weapon_input.c/.h`: full C1 BOT command binding with raw_valid, not masquerading as NETWORK. Existing command-reset lifecycle clears both raw record and provenance. Remote-network-only controls remain network-only.
- `codol_weapon_state.c` and `codol_sprint_state.c`: full BOT commands use real C1 raw buttons. Legacy no-raw bot input keeps its former behavior.

This fixes an architectural prerequisite: CODOL_PmoveC1Run required CODOL_ExecutedUsercmd, but old bots staged no full command and therefore returned to retained movement. Combat bots now supply their own full C1 representation. The reduced command exists only for retained server bookkeeping, just as with the network input boundary.

`delta_angles` is a native vec3 float in degrees (`player.h`); C1 native update_viewangles reads SHORT2ANGLE(command)+delta_angles. AI subtracts degrees before ANGLE2SHORT. It does not reuse T5 field offsets. ClientSpawn resets gclient but does not G_InitGentity; that call belongs to ClientConnect. Staged spawned_player watcher explicitly enables/resets AI on every spawn. Invalid script enemies clear their override so ordinary acquisition resumes.

## Staged deployment, not live

`obj/combat-training-stage/maps/mp/gametypes/_codol_bots.gsc`
`obj/combat-training-stage/waypoints/*.csv` (15 original copies)

Original data root: `D:/CoD/CODOL Builds/Call of Duty Online 1.1.1.13/CODOL/1.1.1.13_server/alpha0022/resources/waypoints`.

Map counts: afghan292, bloc_sh464, bog_sh229, cargoship_sh234, crash_intro316, crash_tropical316, cross_fire444, estate_tropical447, fav_tropical302, killhouse_sh181, nuked235, overgrown558, rust192, storm_spring392, underpass415. Actual maximum neighbor count10. Coordinates are used as recorded, not copied to player origin.

Parent integration needed: call `maps\mp\gametypes\_codol_bots::init()` once after gametype initialization has established team/class callbacks; deploy staged CSVs under native filesystem `waypoints/`. Set `scr_codol_bots` before map initialization (default0, stage caps16). No automatic midmatch live reload is implemented. Missing graph prevents automatic bot spawning. Default `class0` uses the normal class callback; no human profile is copied or mutated.

## Explicit remaining work

This is not a full T5 parity claim. Still missing: exact probabilistic threat priority, threat attacker notification, target death hold, weapon-choice policy for empty reserve/vehicle targets, aim lead/lean refinements, grenade trajectory selection/cooking, melee tactics, strafe/cover tactics, dynamic blocked-edge avoidance, objective/killstreak/vehicle decisions, tactical CSV annotations and C1-specific path negotiation refinement. CSV graph collision behavior needs live observation; it is supplied authoring data, not proof every route is physically traversable. No map without a supplied valid graph is claimed navigable.

Worker performed source/reference audit only. No builds, tests, process changes or gameplay verification. Parent review and build are required before deployment/counting this increment.


### Verified deployment paths and staged init

Current `bin/home/main/qconsole.log` reports fs_homepath `bin/home`, with its `main` directory first in the search path. `filesystem.c::FS_FOpenFileReadForThread` searches these mounted directories, not codol_scriptPath. Parent should copy staged `waypoints/*.csv` to `bin/home/main/waypoints/`. The general FS qpath remains `waypoints/<map>_wp.csv`.

Staged `_gamelogic.gsc` is a copy of the currently active repo overlay with exactly one added thread call to `_codol_bots::init`, immediately after `[[level.onStartGameType]]()` (before existing development/startGame threads). Its attribution and unrelated fixes remain intact. Both staged GSC files deploy to the matching `scripts/codol/maps/mp/gametypes/` override path. The CSV destination is deliberately separate from the script override path.


### Parent integration status

Parent reports combined native build linked hash prefix `7AB1562C`, deployed/restarted, copied CSVs to `bin/home/main/waypoints`, and installed `_codol_bots.gsc`. Parent placed live gamelogic init after `_defcon::init` (the stage copy proposes later after onStartGameType; do not overwrite the parent's live integration blindly). Native spawn thread waits for team/class callbacks and enterGame yields before selecting, so it does not depend on immediate callback availability at the init call.

Enable on a subsequent map initialization with server console `set scr_codol_bots 4`, then the normal map command, for example `map mp_killhouse_sh`. Set0 before map initialization to disable automatic spawning. Existing enabled bots are not removed merely by changing the dvar midmatch. Default remains0; no bots were injected into the user's current match by this worker. Use the existing bot-removal facility or normal server lifecycle for already-connected bots; this increment does not claim hot population management.

Parent confirms compilation; no live combat bot behavior has been observed. Bounded read of the latest75 startup log lines by this worker found no matching script/unknown-function errors, which is not a gameplay validation.

## CSV bot classes and native navigation increment (source ready)

The editable source of bot loadouts is now `obj/combat-training-stage/mp/botclasstable.csv`. Deploy it to `bin/home/main/mp/botclasstable.csv`. The native loader reads the general filesystem qpath `mp/botclasstable.csv` with `FS_ReadFile`; it does not use the mounted stringtable as a competing source. The cache resets when the map's bot graph is loaded. Changes therefore take effect on the next ordinary map initialization.

The export preserves the nine explicitly named C1 botclass0..8 columns from `obj/fastmag-offline-tables.json` (`mp/botclasstable.csv`), excluding the extra unlabeled source column. All nine weapon bases, attachment item names and faction appearance items were compared offline with the supplied C1 marketplace/weapon-attachment tables. One invalid shipped recipe was corrected in the editable export: botclass6 `fal_mp` used `red_reflex`, which has no matching FAL pair; the C1 attachment table explicitly provides `fal_mp,red_swat1,reflex_base,0`, so this cell uses `red_swat1`. All gender cells are literal `m`; native code also supports `f`. Some source charELP cells contain `eye_aviators`; actual marketplace group determines the appearance slot instead of forcing that item into an elbow slot.

`codol_bot_loadout.c/.h` provides bot-only validated CSV member, composed weapon and character methods. Both weapon recipes include all selected attachment columns (eight primary, four secondary) and optional camo, with complete C1 defaults required. Character parts use the same character defaults, vest selection, model ordering, runtime registration and snapshot publication as human characters through the extracted `CODOL_PublishCharacterComposition` function. The bot entry point never requests a playerdata blob. Human appearance still resolves its normal profile and calls the same publisher.

Staged `_class.gsc` routes flagged bots to CSV weapons/equipment/perks/deathstreaks/reward selection before custom/default profile paths. The complete recipe then follows the existing native giveweapon/ammo lifecycle. `_teams.gsc` selects the explicit CSV character composition for bots. `_codol_bots.gsc` assigns class index modulo nine before entering ordinary team/class callbacks. Deploy these together with the parent's bot account-stat separation overlays; this worker does not claim unrelated script profile accesses are globally removed by the loadout branch alone. Do not replace the parent's live `_gamelogic.gsc` with the earlier stage copy.

Navigation source now preserves CSV pitch/yaw/target/tactic annotations, including lower/upper ladder direction; native C1 input uses departure-node ladder aim and avoids jump while already on a ladder. A stuck route marks its directed edge unavailable for five seconds, then recalculates via filtered A*. The five-second cache is an explicit local CSV navigation policy, not an asserted T5 constant. T5 `Bot_UpdatePath` supplies the two-second stalled-path reset precedent; native mantle/ladder states are treated separately. Script goal arrival and route failure now emit the T5 `goal`/`bad_path` notifications, with entity-generation validation before subsequent client think. Tactical grenade/claymore/javelin annotations are retained but their decision logic remains unimplemented. DOM/objective behavior was investigated but deferred when CSV loadouts became the priority.

Status: source written and offline source/data reviewed; parent notified of a coherent build boundary. No worker builds, tests, process changes or live gameplay verification. The prior deployed 7AB1562C hash does not include this CSV increment. Remaining T5 scope still includes objective/killstreak/vehicle tactics, sophisticated threat/weapon selection and tactical actions; basic CSV navigation is not complete T5 parity.
