# CoDOL server vs C1 client parity inventory (2026-09-09)

> **Status.** This is the raw inventory. The actionable plan derived from it is
> [CODOL_PARITY_PLAN.md](CODOL_PARITY_PLAN.md), which supersedes this file wherever
> the two disagree. A verification pass on 2026-09-09 corrected several rows here;
> each correction is marked **[CORRECTED]** inline and is carried in the plan.

Scope: what the sh1x server (a CoD4x fork) in this repository (branch codex/codol-server)
still lacks or only partially provides relative to what the CoDOL 1.1.1.13 client (C1.exe)
expects. Offline source and document inspection only; no build, run or git action was taken.

Reading notes
- Path move during this research: every `src/codol_*.c|cpp|h|inc` file was relocated into
  `src/codol/{assets,collision,net,player,script,snapshot,stats,vehicle,weapon}/` by another
  session while this inventory was being compiled. Line numbers were re-checked in the new
  location wherever a file is cited by line. Rows that still cite the old flat name
  (`src/codol_foo.c`) mean `src/codol/<subdir>/codol_foo.c` (use `find src -name`); the move did
  not change line numbers. Non-CoDOL files (`src/sv_client.c`, `src/g_cmds.c`, `src/sv_main.c`,
  `src/scr_vm_main.c`, `src/asmsource/*`) did not move.
- Status vocabulary: implemented / partial / stub / missing / unverified (with what would verify).
  "Source written" is distinguished from "verified against C1" (AGENTS.md).
- Priorities: P0 blocks or breaks a real C1 match; P1 visibly broken feature; P2 accepted but
  incomplete / no effect; P3 verification only or cosmetic.
- alpha0022 (`D:\CoD\CODOL Builds\Call of Duty Online 1.1.1.13\CODOL\1.1.1.13_server\alpha0022\`)
  is used only as evidence about the client; its MISSING-FEATURES.md sec. 5 marks several of its
  own docs stale, and its sec. 6 ranking table is explicitly superseded.
- Real-client baseline (docs/CODOL_IMPLEMENTATION_PASS.md:2314-2383): connect, secure profile,
  team autoassign, ESC class panel, spawn, move, sprint, crouch, jump, fire, reload, grenade,
  melee, fall death, map restart bookkeeping. Nothing past first-life gameplay has been observed.

## 1. Client-to-server commands

Correction first: `docs/CODOL_C1_COMMAND_DISPATCH.json` is C1's CG_ServerCommand table
(server->client; dispatcher 0x469320, byte map 0x46a118, jump table 0x46a024: JSON lines 3-6,
generator obj/claude-workers/parent-c1-command-export.py:9-10). It tells which letters the client
accepts from the server (`e` = GAME_UNKNOWNCLIENTCOMMAND from src/g_cmds.c:1007; `q u v r H d`
emitted by codol_script_menu.c:46-87; no `G`, so IW3 setteamscore's letter is unknown to C1) but it
is not a list of what the client sends. C1's client->server console-command table is at 0xcd149c;
only its `matchdatadone` entry has been exported (docs/CODOL_CLIENTMATCHDATA.md:244-248). Rows
below come from the server dispatch tables plus the C1 sender traces that exist in docs/.

Dispatch locations: engine `ucmds[]` src/sv_client.c:2807-2827, dispatcher :2836-2867, developer
trace of every reliable command :2890, flood-protect whitelist :2899-2910; game ClientCommand
src/g_cmds.c:931-1009; unknown fallthrough g_cmds.c:1007 (replies `e` to the client, logs nothing).

| command | client sends it for (args) | server status | evidence | prio |
|---|---|---|---|---|
| `mr <serverId> <menu 0..31> <response>` | menu response; C1 senders 0x5fde90/0x6a5390 | handled | g_cmds.c:693-739, 966-969; docs/CODOL_MENU_RESPONSE_TRACE.md:5-20; codol_script_menu.c:8-17 | P3 |
| `n <actionId>` | action press/release edge, CL_SendActionNotify 0x499aa0, 86 IDs | handled | g_cmds.c:942-946; codol_script_notify.c:11-31, 142-170 | P3 |
| `matchdatadone` | ack of a clientmatchdata section (C1 table 0xcd149c -> 0x5d1fb0) | handled | sv_client.c:2804-2809; codol_matchdata.c:7; docs/CODOL_CLIENTMATCHDATA.md:244-290 | P3 |
| `cp @ <17 crc> <aggregate>` | pure/IWD checksum report at connect | partial: IWD checksums only, no fastfile validation | sv_client.c:2313-2332; codol_pure.c:22-54; docs/CODOL_PURE_COMMAND.md:1-27 | P2 |
| `userinfo`, `disconnect`, `vdr` | standard | handled | sv_client.c:2199-2217, 2477-2479 | P3 |
| `muteplayer` / `unmuteplayer <n>` | voice mute from muteplayer menu | partial: writes `cl->muteList[]`, no reader anywhere; no voice path | sv_client.c:2774-2793, 2824-2825; server.h:236; g_sv_cmds.c:443-514 has no mute check | P2 |
| `say <text>` / `say_team` | chat; server->client `V`/`W` (C1 G_SayTo 0x520363, handlers 0x4695a6/0x469618) | handled (receive side); C1 sender token unverified | g_cmds.c:674-691, 948-955; g_sv_cmds.c:431-437, 518+ | P2 |
| `tell <n> <text>` | private message | stub: matched then `return`; call commented out; client gets no `e` either | g_cmds.c:958-961 (`// Cmd_Tell_f`), dead impl 524-554 | P2 |
| `score` | scoreboard request -> 10-column `b` (7-column `4` for zm) | handled; whole send aborts if `skills/tdm` profile missing; C1 caps 19 rows | g_cmds.c:741-744; codol_scoreboard_sender.c:11-58 (46-50 abort); docs/CODOL_SCOREBOARD_CONTRACT.md:10-34 | P1 |
| `callvote <what> [args]` / `vote <y/n>` | vote | handled server-side; client vote UI mirror unmapped and vote configstring publication suppressed (CS 13-16 collide with C1 fog/match-end/map-center) | g_cmds.c:573-620, 995-999; g_sv_cmds.c:88-200, 355; codol_sv_assets.c:514-521; docs/CODOL_IMPLEMENTATION_PASS.md:1286-1293, 1446 | P1 |
| `kill`, cheats (`give god noclip ufo ...`) | suicide / dev | handled (cheats gated) | g_cmds.c:505-518, 977-1002 | P3 |
| `printentities` | entity dump | disabled deliberately | g_cmds.c:1003-1005 | P3 |
| **`s` (args unknown)** | observed from the real client during the lobby->spawn drive | traced-as-unknown: falls to g_cmds.c:1006-1008, nothing logged | docs/CODOL_IMPLEMENTATION_PASS.md:2344; memory codol-map-load-state.md | **P0** |
| `download nextdl stopdl donedl retransdl wwwdl` | IW4OL download protocol | missing by design (no CoDOL transfer) | sv_client.c:2815-2823; docs/CODOL_RELIABLE_CHANNEL.md:13-14 | P3 |
| quick-chat via `mr` (`menu_quickcommands/quickstatements/quickresponses`) | quick messages | dead branch: menus never precached, `game["menu_quick*"]` never assigned | scripts/codol/maps/mp/gametypes/_menus.gsc:11-77 vs 227-235 | P2 |

Not text commands (verified mechanism): spectator follow/next/prev are usercmd buttons in
SpectatorThink (src/asmsource/_g_active_mp.asm:1149-1178; g_cmds.c:747-918); team and class change
are `mr` responses `allies/axis/autoassign/spectator`, `class0..14/custom1..10/copycat`
(_menus.gsc:196-226, _class.gsc:17-44); killstreak use is `n 17..26` plus GSC `+actionslot N`
(codol_script_notify.c:17-19, 151-155); playercard / clan tag / unlocks / ping are server-derived
(sec. 5); "ready" belongs to the external lobby.

Out-of-band (src/sv_main.c:1884-1968): getchallenge/connect/getstatus/getinfo/rcon handled;
`stats` 27-chunk profile upload + `statResponse` mask handled (1925-1928; docs/CODOL_STATS_UPLOAD.md:1-26);
`heartbeat`->`heartbeatresponse` handled (1908-1922); `v` voice routed only (1950-1951, 5296);
unknown OOB is logged developer-only without the text (1964-1966).

To act on: (1) identify `s` (developer 1, read sv_client.c:2890, then find the C1 sender in
table 0xcd149c); (2) log unknown commands at g_cmds.c:1007; (3) export the full 0xcd149c table into
docs/ - it is the authoritative client->server list; (4) mute and tell are inert.

## 2. Script builtins

Method: registered set = every `Scr_AddFunction` / `Scr_AddMethod` literal in src/** (no macro
tables exist; the set is 837 distinct names, 870 call sites, identical before and after the
src/codol move). Inventory = docs/CODOL_BUILTIN_INVENTORY.json `entries[]` (1307 names).
Script corpus for ranking = alpha0022 gsc_overlay + vendor/iw4 maps/mp + common_scripts +
scripts/codol (269 files, "MP scope"), plus the full 1545-file corpus for secondary ranking.
Registration tables: src/scr_vm_main.c:80-469 (functions), :471-1054 (methods; CoDOL block under
CODOL_SERVER), :1057-1075 driver; src/codol/script/codol_script_startup_extra.c:1040-1047;
src/sv_bots.cpp:364-369; implementations src/scr_vm_cmd.c:40, :143.

Counts: registered ∩ inventory 742; registered extras 95; inventory names unregistered 565, of
which 161 are referenced anywhere in the corpus and 31 in MP scope (11 of those are ordinary GSC
functions, not natives); stubs 6 names; developer-only registrations 17. The inventory is stale:
262 entries marked `missing_binding` are in fact registered, and docs/CODOL_GSC_COMPATIBILITY.md:24-28
("480 bound / 827 missing") is superseded by 742 / 565. About 402 of the 837 registered names
resolve to retained assembly bodies (src/asmsource/*.asm) whose stub-ness was not audited.
The 2026-09-09 probe closure (IMPLEMENTATION_PASS.md:2229-2233) confirmed the dm/mp_killhouse_sh
compile closure is complete; the rows below are what other gametypes, killstreaks and maps hit.

| builtin | type | scripts use it for (call site) | server status | prio |
|---|---|---|---|---|
| createintervalsound | script fn, not native | createfx sound emitters, 143 sites, e.g. alpha0022 gsc_overlay/maps/createfx/mp_bloc_sh_fx.gsc:689 | missing script: defined in vendor/iw5/common_scripts/_createfx.gsc:89; iw4 `_createfx.gsc` only has createLoopSound | P1 (needed by every non-killhouse map's createfx; ship a script, not a native) |
| codol_damagebot, codol_bullethitbot | fn | overlay bullet damage vs bots: gsc_overlay/maps/mp/_weapons.gsc:169, 208, 224 | unregistered (alpha Python-host bridge only) | P1 if the overlay `_weapons.gsc` is on the load path; otherwise P3 |
| setclientsubtitle, nativesplash | method | deathstreak captions/splash: gsc_overlay/maps/mp/perks/_deathstreaks.gsc:183-184 | unregistered (Python-registry only) | P1 |
| magicgrenade | method | Martyrdom: _deathstreaks.gsc:142 (12 sites corpus-wide) | unregistered | P1 |
| givedeathstreakhealth, setcopycatloadout, enterlaststand | method | Painkiller / Copycat / Final Stand deathstreaks: _deathstreaks.gsc:195, 152, 38 | unregistered | P1/P2 |
| setsuppressiontime, setaispread | method | sentry gun AI tuning: vendor/iw4/common_scripts/_sentry.gsc:1316-1317 | unregistered (real IW4 natives) | P2 |
| useanimtree | method | AC130 animtree bind: vendor/iw4/maps/mp/killstreaks/_ac130.gsc:1827 | unregistered; usually a compiler construct - unverified whether this VM needs a runtime binding | P2 |
| alternatescenecameralinkto, alternatescenecameraunlink | method | rear-view camera wrapper: vendor/iw4 _utility.gsc:1942, 1951; scripts/codol/maps/mp/_utility.gsc:1946, 1955 | unregistered | P2 |
| setrearviewrenderenabled | method | same path | STUB: `Scr_Error("ALTERNATE_SCENE_RENDER is disabled")` (IW4 0x5f50b0 does the same) - hard error, not a no-op | src/scr_vm_main.c:1053; src/codol/script/codol_script_player_builtins.c:799 | P2 |
| setsoundblend | method | rain sound blending: vendor/iw4/maps/mp/_fx.gsc:153-223 (11 sites) | unregistered and absent from the inventory JSON (inventory gap) | P2 |
| getglassarray, destroyglass | fn | map glass pre-break: vendor/iw4/maps/mp/mp_strike.gsc:23, 26 | unregistered; native glass store exists (sec. 5) but no GSC binding | P3 |
| createlootmail, getrandomloot | method | IW4 loot: vendor/iw4/maps/mp/_loot.gsc:284-496 | unregistered; unused by CoDOL | P4 |
| logstring (fn+method), getuid, setuid, arraytest | fn/method | general | STUBS: empty bodies src/scr_vm_functions.c:3240, 3245, 3232; getuid/setuid print "Removed script function" and push 0 (:65, :307) | P4 |
| getstruct, getstructarray, isusingremote, isemped, isnuked, getlastweapon, isweaponenabled, ischangingweapon, getweaponattachments, setadrenaline, getspawnpoint, isflashbanged, addspawnpoints | GSC functions | listed in the inventory but defined in vendor/iw4 _utility.gsc / utility.gsc / _spawnlogic.gsc / _flashgrenades.gsc | no engine work | - |
| SP/AI-only natives (getaiarray 368 sites, isai 298, setgoalnode 247, setgoalpos 218, setanim 202, orientmode, animmode, connectpaths, pushplayer, allowedstances, stopanimscripted, playerlinktodelta, playerlinktoblend, dodamage, cansee, forceteleport, vehicle_setspeedimmediate ...) | fn/method | referenced only outside MP scope | unregistered; defer unless bots/AI/coop are planned | P3 |
| 404 inventory names with no call site anywhere (319 T5-only, 43 python+treyarch, 25 python-only, 13 iw4_catalog) | - | none | unregistered; no script demand | - |

Semantics caveat: "registered" is name coverage. Families flagged "registered in source, not
runtime-proven" in IMPLEMENTATION_PASS.md (turret family :1937-1940, radar :1110, vehicle builtins
:2135-2165, weapon-class mapping sniper/throwingknife/riotshield :2255, forwarded `::builtin`
pointers :2263) still need C1 verification.

## 3. Player state / snapshot fields

Method: `src/codol/snapshot/codol_player_fields.inc` holds the 244 measured playerStateFields
(names inferred in alpha0022 playerstate_fields.py:215-460; slots without a comment are CoDOL-only).
Writers address a field by wire offset via `put()/put_float()` in codol_engine_state.c or by
named overlays elsewhere. A static sweep found 91 of 244 written by literal `put`; vectors and
event rings are written through `base+4*i` loops (origin, velocity, delta_angles, viewangles,
vLadderVec, events, eventParms, unpredictable*), and further overlays write from their own
tables: perks src/codol/player/codol_perks.c:73-87 (0x4b0..0x4cc, called from
src/codol/snapshot/codol_sv_gameframe.c:237), links codol_player_links_wire.c (0x14, 0x1d4..0x1e8),
radar codol_radar_state.c (0x21c, 0x220), sprint codol_sprint_state.c (0x238..0x248, 0x494, 0x498,
0x5b8), use-hint codol_usehint_wire.c (0x208..0x214, 0x1f4), recoil codol_recoil_state.c (0x3330,
0x344), loop sound (0x1f0), weapon lock and HUD icons (codol_sv_gameframe.c:233, 258).
Ground truth at runtime: the developer build prints "CoDOL field audit: N of 244 player wire
fields never non-zero so far: <offsets>" every 30 s (src/codol/snapshot/codol_frame_builder.c:55-68);
that list should be captured on the next launch and diffed against the rows below, which are the
fields for which no writer of any kind was found in src/codol.

| field(s) (wire offset) | client expects / does | server status | evidence | prio |
|---|---|---|---|---|
| damage indicators 0x17c damageEvent, 0x180 damageYaw, 0x184 damagePitch, 0x188 damageCount, 0x18c damageFlags | directional hit indicator on the HUD | not published, deliberately; the action audit's "now published" claim is contradicted by source (no writer, no `ps->damageYaw` use under src/codol) | src/codol/snapshot/codol_engine_state.c:261-263; docs/CODOL_PLAYER_ACTION_AUDIT.md:56 (stale) | P1 |
| prone direction 0x1a0/0x1a4/0x1a8 | prone body yaw/pitch | not published (same comment) | codol_engine_state.c:261-263 | P2 |
| view lock 0x1ac viewlocked, 0x1b0 viewlocked_entNum; 0x1ec linkWeaponEnt | turret / linked-weapon camera lock | never published | audit sec. 2 row "view lock"; grep src/codol finds no writer | P1 (turrets, sentry) |
| remote control 0x44 remoteEyesEnt, 0x48 remoteEyesTagname, 0x4c remoteControlEnt | predator / AC130 / RC killstreak view | never published | no writer; audit row "remote control ... unverified" | P1 (killstreaks) |
| view-angle clamp 0x16c/0x170 base, 0x174/0x178 range | turret and vehicle look limits | never published | no writer | P2 |
| killcam 0xa50 deltaTime, 0xa54 killCamEntity, 0xa58, 0xa5c | killcam replay entity | never published; no native killcam producer for the CoDOL wire | alpha0022 docs/INTEGRATION-NEXT.md:193, ERRORS.md:10707; no writer | P1 |
| viewmodelIndex 0x144, 0x148 | first-person hands model | never published; whether C1 reads 0x144 or composes hands from playerdata parts is unverified | no writer; docs/CODOL_PLAYER_APPEARANCE.md | P1 verify against C1 |
| throwbackWeaponIndex 0x40 | grenade throwback prompt | never published (0x34/0x38/0x3c are) | no writer | P2 |
| counter-UAV radar gate 0x224, 0x228 | second radar class (counter-UAV) | never published; 0x21c/0x220 are | alpha0022 parity_roadmap.md:1506-1522; codol_radar_state.c writes only 0x21c/0x220 | P2 |
| 0x48c (IW4 shellshockIndex - name trap), 0x490, 0x49c, 0x4a0 (-70 bits, hint 3), 0x4a4..0x4ac | shellshock / DOF / unknown | never published; 0x494/0x498 written by sprint | alpha0022 iw4_reference.md:810 | P2 |
| 0x1b4..0x1c8 (six 8-bit), 0x1cc/0x1d0, 0x1fc..0x204 (angles), 0x218, 0x22c, 0x230, 0x234, 0x24c, 0x250, 0x274, 0x27c, 0x280, 0x290, 0x32c..0x338, 0x354, 0x358 | CoDOL-only slots, semantics unknown | never published | no names in playerstate_fields.py or docs/ | P3 until a consumer is traced |
| 0x350 | none: "no reader anywhere in C1.exe" | correctly not sent | alpha0022 ERRORS.md:4746-4747 | - |
| 0x53c..0x58c block, 0x590, 0x594, 0x59c, 0x5a0..0x5cc | CoDOL-only (fire_timing.md offsets in this range are weaponDef, not ps) | never published; 0x598 is written (engine_state, scoreboard_wire) | alpha0022 MISSING-FEATURES.md:1715 | P3 |
| trailing 0x3310..0x333c (after HUD arrays 0xa60..0x3310) | CoDOL-only trailing state | never published except 0x3330 (recoil) | alpha0022 hudelem.md:383, 630 | P3 |
| 0x78, 0x84, 0x8c inside the 0x68..0x8c block | 10-slot block (five 8-bit, five 5-bit) | unverified: siblings written, these absent from the literal grep | codol_engine_state.c (grep 0x068); confirm via field audit | P3 |
| client fields 0x008, 0x00c (32-bit), 0x010 (3-bit), 0x018, 0x01c (1-bit), 0x0a0..0x0b8, 0x12c, 0x130 (11-bit), 0x134 (8-bit) of the 77 clientState fields | per-client rank / prestige / head icon / vehicle seat | never published; published are team 0x004, model 0x014, attachments 0x020..0x09c, vehicle 0x0bc, ability masks/values 0xc0..0x128 | codol_engine_state.c:851-866 ("Rank/perks/vehicle-seat fields need their own maps"); codol_clients.c:24-45; docs/CODOL_GAMEPLAY_FRAME.md "progression metadata currently defaults to zero" | P1 |
| objective/waypoint array (32 x 0x24 at ps+0x5d0, table 0xc39818) | compass and on-screen objective markers | unverified: no producer found by name; needed by dom/sd/ctf/dd | alpha0022 playerstate_fields.py:471-482; grep "objective" in src/codol/snapshot | P1 |
| entity types | producer supports players, missiles, base weapon items, general entities, script movers, brush models, turrets, radar jammer, effects/sounds; rejects vehicle state, alternate-mode weapon items, actors, animation commands | partial | docs/CODOL_GAMEPLAY_FRAME.md:17-25; codol_sv_gameframe.c:122-201 | P1 |
| HUD element fields | 33 hudelem fields mapped; fonts 0..7 and alpha/8 quantisation fixed | implemented | codol_engine_state.c:25-45; IMPLEMENTATION_PASS.md:2330-2334 | P3 |

Doc staleness: docs/CODOL_FRAME_ENTITIES.md:48-56 still says the live writer emits IW3 bodies;
superseded by docs/CODOL_LIVE_SNAPSHOT_WRITER.md.

## 4. Player actions and movement (from docs/CODOL_PLAYER_ACTION_AUDIT.md, 2026-09-09)

| action / input | client does | server status | evidence | prio |
|---|---|---|---|---|
| mantle | jump at a CONTENTS_MANTLE ledge; expects PMF_MANTLE, mantle block 0x258..0x264, EF_MANTLE | retained Mantle_Check runs every frame but never starts in any run; publication exists | audit sec. 2, sec. 4 item 1; codol_engine_state.c:255-260; IMPLEMENTATION_PASS.md:2378-2383 | P1 |
| weapon switch by key | keys 1/2, next weapon | raise/drop phases published, but the driver run never changed weapon; bind unknown | audit sec. 2 "weapon switch"; docs/CODOL_WEAPON_SWITCH_CONTROLS.md | P1 |
| 4th equipment slot 0x400000 | CoDOL fourth equipment | dropped by CODOL_ToEngineUsercmd | audit sec. 1, sec. 4 item 3 | P2 |
| marker slot 0x1000000 | marker / ping | dropped | audit sec. 1 | P2 |
| selected-location 0x20000, ADS-throw 0x100000, remote-control 0x200000 | killstreak location pick / remote | forwarded, unverified | audit sec. 1 | P2 |
| hold breath 0x2000 | sniper steady | forwarded, unverified | audit sec. 1 | P3 |
| view lock / linked weapon | turret use | never published (sec. 3) | audit sec. 4 item 4 | P1 |
| perk HUD icons 0x4b0..0x4cc | perk icons | writer exists (codol_perks.c:73 via codol_sv_gameframe.c:237); audit's "never published" is stale or the seed path is not reached | confirm with the field audit | P2 |
| ladder | PMF ladder + vLadderVec | published (codol_engine_state.c:293-296); no ladder near spawn, unverified | audit sec. 2 | P3 |
| damage indicators | HUD hit direction | not published (sec. 3) despite audit text | codol_engine_state.c:261-263 | P1 |
| tactical throw 0x10000 | third equipment | implemented via raw-word offhand selector; live throw unverified | audit sec. 1 correction | P3 |
| dive 0x800000 | dolphin dive | implemented natively, verified | src/codol/player/codol_dive.c; audit sec. 2 | - |
| prone level->toggle | C1 sends prone as a level | one press per change in sv_client.c | audit sec. 2 | - |
| animation timers/indices 0xc0..0xcc | third-person anim | published, visually unverified; conditions fastmantle, riotshieldnext, divedirection, scripted have no producer | codol_engine_state.c:264-267; IMPLEMENTATION_PASS.md:2346-2352 | P2 |
| movement prediction (rov) | prediction | fixed: rov only on first frame, teleport, pm_type change | IMPLEMENTATION_PASS.md:2366-2377 | - |
| melee, fire, reload, sprint, crouch, jump, ADS, frag/smoke, walk | core | verified | audit sec. 1-2 | - |

## 5. Gameplay systems the client renders but the server never drives

| system | client expects / does | server status | evidence | prio |
|---|---|---|---|---|
| team scores on HUD | **[CORRECTED]** two equivalent routes to the same two client fields: reliable `C <int>` -> cg+0xBEB20 and `D <int>` -> cg+0xBEB24, and configstrings **5** and **6** which hold the same values for the win/lose banner (0x550960). CS 6 is TEAM_ALLIES (blue, top of the HUD), CS 5 is TEAM_AXIS. | **broken**: `setteamscore` still sends IW3 `G`/`H` (C1 has no `G`; C1 `H` hides the scoreboard). `updatescores`/`updatedmscores` were already corrected to `C`/`D`/`E`. CS 5/6 are never published. | src/asmsource/_g_scr_main_mp.asm:6524, 6542 (unfixed) vs _g_client_script_cmd_mp.asm:4413, 4434, 4527 (fixed); alpha0022 docs/parity_roadmap.md App. B; docs/CODOL_C1_COMMAND_DISPATCH.json | **P0** |
| intermission / match end | only `pm_type == 6`; client force-opens the board (0x43b7ef); alpha0022 measured pm_type 6 freezes reliable ACKs (one-way door); `t "EXE_MATCHENDED"` drops the client | partial: pm_type mode table maps intermission; native CS_INTERMISSION (14) untranslated and collides with C1 slots; exit path never exercised natively | codol_engine_state.c:172-193; src/g_shared.h:416; sv_main.c:4756-4782 raw `d <index>`; alpha0022 MISSING-FEATURES.md:372 (GS-5); IMPLEMENTATION_PASS.md:1448, 1458 | **P0** |
| scoreboard | `b <count> <t1> <t2> <limit>` + ten ints per row (zm: `4` + seven); 19-row cap; status/head icon banks 6062/6070 | implemented in source, never shown on C1; skill column aborts send without `skills/<mode>` | docs/CODOL_SCOREBOARD_CONTRACT.md; codol_scoreboard_sender.c:16-25, 46-50; codol_configstrings.h:37-38, 53 | **P0** |
| killcam | `_killcam.gsc` uses forcespectatorclient + archivetime/psoffsettime; C1 needs PMF_FROZEN 0x80000, pm_type<8, POF_FOLLOW, follow clientNum | partial: script fields and engine archive exist; no evidence PMF_FROZEN / POF_FOLLOW / killCamEntity (0xa54) reach the CoDOL wire | src/g_client_fields.cpp:485-491; g_cmds.c:789; _g_active_mp.asm:2717; alpha0022 hud_arch_killcam.md:152-235; sec. 3 row killcam | **P0** |
| killcam skip (use button -> abort_killcam) | script notify | unverified; no native equivalent found | alpha0022 hud_arch_killcam.md:270-309 | P2 |
| final killcam | level.showingFinalKillcam + doFinalKillCamFX (slowmo + vision) | unverified; script exists, `setslowmotion` native, never exercised | vendor _killcam.gsc:42,163,222; IMPLEMENTATION_PASS.md:2075-2083 | P2 |
| match clock | `d 15 <matchEndMs>` at cgs+0x1b0 | implemented (native CS 11 -> CoDOL 15) | codol_sv_assets.c:587; codol_configstrings.h:19 | P3 |
| end-of-game results menu | `q <slot>` into the 32-slot menu bank | implemented; content unverified | scr_vm_main.c:527-531; g_cmds.c:705-734; IMPLEMENTATION_PASS.md:2260 | P1 |
| match-end grayscale / winners | per-player vision set, top three | **[CORRECTED]** both routes are implemented: per-player sends the reliable letters `N O P Q R` (codol_script_vision.c:33, 158-160) and the global sets publish configstrings 1305+ (:202). Only the match-end *use* of them is missing. | alpha0022 matchend_fix.md A.1/A.5; codol_configstrings.h:58 | P2 |
| killstreak scripts (17 IW4 streaks) | maps/mp/killstreaks/*.gsc drive everything; C1 has no native streak logic | partial: vendor scripts load; builtins closed 2026-09-09; never run past first spawn | alpha0022 vendor/iw4/maps/mp/killstreaks/; IMPLEMENTATION_PASS.md:2229 | P1 |
| killstreak HUD (count, ladder, splash `w <slot> <row> <dur>`) | splash table 914 rows; icons from material bank | implemented in source, unverified | codol_script_hud_notifications.c:280 (C1 0x51e631); scr_vm_main.c:914 | P1 |
| UAV / advanced UAV; counter-UAV / EMP jam | setTeamRadar / blockTeamRadar bits; C1 draws blips | implemented in source, "unvalidated in C1"; counter-UAV gate 0x224 unpublished | scr_vm_main.c:266-271; codol_radar_state.c; IMPLEMENTATION_PASS.md:1110 | P1 |
| EMP whiteout + equipment disable | client vision force | missing (no wire found) | alpha0022 killstreaks_full_fix.md:287 sec. 9 | P3 |
| airstrike / stealth bomber / mortar | losRadiusDamage + plane model + FX | partial: damage native; aircraft entity publication never shown | codol_script_combat_builtins.c; alpha0022 killstreaks_full_fix.md sec. 3 | P2 |
| attack helicopter / pave low / harrier | spawnvehicle / spawnhelicopter + flight path + turret AI | partial/stub: `spawnvehicle` deliberately unregistered; `spawnhelicopter` registered | scr_vm_main.c:345-346; IMPLEMENTATION_PASS.md:2135-2165 | P1 |
| sentry gun | spawnturret + turret AI + canplayerplacesentry | partial: registered in source only | scr_vm_main.c:94-97; IMPLEMENTATION_PASS.md:1937-1940 | P2 |
| turret minimap visibility | compass marker | stub: value stored, no consumer | codol_script_vehicle_builtins.c:961-979 | P2 |
| AC-130 ride/gunship | startAC130/stopAC130 + camera + ambience CS 1301 | stub for gameplay (`ac130_active[]` write-only); ambience implemented | codol_script_vehicle_builtins.c:908-940; scr_vm_main.c:187; IMPLEMENTATION_PASS.md:1468-1475 | P2 |
| predator / RC / chopper gunner ride cameras | remote entity + usercmd forwarding + remoteEyes/remoteControl ps fields | partial: missile flight/controls native; ride camera unvalidated; ps 0x44/0x48/0x4c unpublished (sec. 3) | IMPLEMENTATION_PASS.md:1255-1325; codol_remote_missile.c | P2 |
| care package / airdrop | heli -> crate -> hold-use capture | partial: use-hint native; crate/heli model publication unproven | docs/CODOL_USABILITY.md; codol_script_usehint.c | P2 |
| nuke | announce, whiteout, end match | unverified: no native producer found (grep "nuke" in src: none) | alpha0022 killstreaks_full_fix.md sec. 3 | P3 |
| dogs | model + bite anim | missing (no `_dogs.gsc`, no model) | alpha0022 killstreaks_full_fix.md:287 | P3 |
| vehicles (general) | vehicle snapshot identity, pose, suspension, controlling client | partial: conversion/pose/collision/precache written; factory dispatch and snapshot seeding unfinished; gameplay frame rejects vehicle state | IMPLEMENTATION_PASS.md:1568-1678, 2128-2169; docs/CODOL_VEHICLE_SNAPSHOT_IDENTITY.md; codol_vehicle_native.cpp; docs/CODOL_GAMEPLAY_FRAME.md:23 | P1 |
| attached-vehicle client info (cs+0xbc) | 2047 = none | implemented + tested | docs/CODOL_CLIENT_VEHICLE.md | P3 |
| vehicle path nodes | getvehiclenode / attachpath / startpath | implemented in source | scr_vm_main.c:409-414; docs/CODOL_PATH_NODES.md | P2 |
| turrets (map/player) | isusingturret, getturretowner, target/fire/timing family | partial; `isfiringturret` semantics unmapped; view lock unpublished | IMPLEMENTATION_PASS.md:222-248, 1932-1945; codol_script_turret_target.cpp | P2 |
| HUD elements | Scaleform-pull HUD + ps HUD section; fonts 0..7; alpha/8 | implemented; codec corrected against live C1 | docs/CODOL_FRAME_HUD.md; IMPLEMENTATION_PASS.md:2330-2340 | P1 (verify each gametype HUD) |
| waypoints / objective icons | setwaypoint + edge styles | implemented in source; ps objective array producer unverified (sec. 3) | codol_script_hud_waypoint.c; scr_vm_main.c:635-638 | P1 |
| obituaries / kill feed | temp entity 0x42 -> CoDOL event 107 | mapping implemented, rendering unverified | codol_event_map.inc:77; _g_scr_main_mp.asm:6854-6884 | P1 |
| lower message / hud_message | hudelems | unverified (rides on hudelems) | vendor _hud_message.gsc | P2 |
| sounds (music `l/m/n`, ambience CS 1300/1301, aliases) | reliable letters + configstrings | implemented in source; audio parity unverified | IMPLEMENTATION_PASS.md:1439, 1462-1475; scr_vm_main.c:184-187, 679-691, 1000-1003; codol_sound_native.c | P1 |
| announcer / battlechatter | _music_and_dialog.gsc, _battlechatter_mp.gsc | unverified | vendor scripts; alpha0022 sound_support.md sec. 2 | P3 |
| effects / FX | CS 3651 effects, CS 3971 tagged, per-recipient FX, stopfxontag | implemented in source | codol_configstrings.h:30,33; scr_vm_main.c:195-201, 383, 405; IMPLEMENTATION_PASS.md:1237-1249, 2099-2108 | P1 |
| client match data (end-of-match highlights) | asset type 39 schema, opcode 4 section, `matchdatadone` | implemented; verified against a synthetic peer only | docs/CODOL_CLIENTMATCHDATA.md "Encrypted native delivery verification"; codol_matchdata_wire.c; codol_sv_snapshot.c:106-136 | P1 |
| server matchdata upload (`sendmatchdata`) | backend delivery | stub (draft; queue/session/backend incomplete) | IMPLEMENTATION_PASS.md:751, 2183, 2227 | P2 |
| profile write-back to the client/account | - | missing by design; no receiver identified | codol_profile_updates.h:35-46 | P2 |
| ranks / XP persistence | _rank.gsc writes experience/rankxp/prestige via playerdata | stub: twelve IW4-only roots go to a per-client session store; nothing persisted or uploaded | IMPLEMENTATION_PASS.md:2267-2285; codol_script_profile_vm.c | P1 |
| challenges | challengeProgress / challengeState | stub (session store) + bridge doc | IMPLEMENTATION_PASS.md:2274; docs/CODOL_ITEM_UNLOCKS.md "challenge progress bridge" | P2 |
| unlocks / isItemUnlocked | marketplace items | implemented (native rule evaluator + XP conversion) | docs/CODOL_ITEM_UNLOCKS.md; scr_vm_main.c:532 | P2 |
| skill rating (UpdateSkill) | reducer into skills/<mode> | partial; guards/schema unverified | IMPLEMENTATION_PASS.md:2181-2193; codol_skill_rating.c | P2 |
| player cards | handles 0..1023; card title is a marketplace id | implemented with out-of-range guard | IMPLEMENTATION_PASS.md:2296-2312; scripts/codol/maps/mp/gametypes/_playercards.gsc | P2 |
| clan tags | IW4OL svc_configclient carried name+clantag | missing under CoDOL: envelope disabled; no CoDOL field mapped | src/sv_snapshot.c:467-474; server.h:174 | P3 |
| voice chat | - | missing/unverified: only IW4OL OOB `voice`, sv_voice off, C1 traffic DTLS-framed | sv_main.c:5296, 3162; no voice under src/codol | P3 |
| chat (public `V`, team `W`) | C1 handlers 0x4695a6/0x469618 | implemented in source | IMPLEMENTATION_PASS.md:897; g_cmds.c:948-956 | P2 |
| spectator controls | free/follow, setSpectateDefaults, allowSpectateTeam, team 6 | implemented in source, unverified | docs/CODOL_SPECTATE_DEFAULTS.md; codol_spectate_defaults.c; IMPLEMENTATION_PASS.md:1370-1376 | P1 |
| vote UI | C1 vote UI unconfirmed; native CS 13-16 collide | missing: publication suppressed | codol_sv_assets.c:514-521; IMPLEMENTATION_PASS.md:1286-1293, 1427 | P2 |
| host migration | vendor _hostmigration.gsc; C1 is a dedicated-server client | missing: only server-to-server code, command disabled; `ishost` registered as a draft | sv_cmds.c:2384; sv_main.c:5369-5615; IMPLEMENTATION_PASS.md:1290, 2227 | P3 |
| dynamic entities / destructibles | 92-byte dynent records + _destructible.gsc cook-off | partial: decoded into the clip map only; no damage/state/FX/snapshot path | codol_dynents.c, codol_dynents_native.c, codol_collision_native.c:318-336; alpha0022 gsc_props_fix.md:12-37 | P2 |
| glass / breakables | GameWorldMp glass groups | partial: native store written, no GSC/wire lifecycle | IMPLEMENTATION_PASS.md:2199-2207; codol_glass_groups.c | P3 |
| minimap / compass | icon bank 6085..6099, minimap CS 1303, north CS 1302 | implemented in source; icon indices unreviewed | codol_script_minimap.c; codol_configstrings.h:22,36; IMPLEMENTATION_PASS.md:1355-1362, 1952 | P2 |
| perks (client ability modifiers vs server _perkfunctions) | C1 applies ability modifiers client-side | open: `_perkfunctions` override applies IW4 effects server-side, needs comparison with client modifiers | IMPLEMENTATION_PASS.md:2265 | P2 |
| composed weapon ammo HUD | ammo counts for composed weapons | open: HUD shows 0|0 for the composed weapon | IMPLEMENTATION_PASS.md:2342 | P1 |
| opfor body/head models | playerdata parts | open: opfor xmodels absent from mounted zones (void used) | IMPLEMENTATION_PASS.md:2343 | P1 |
| IW4 class popup after team select | - | does not appear; ESC panel is the working path (as alpha0022 measured) | IMPLEMENTATION_PASS.md:2345-2347 | P3 |

## 6. Game modes and maps

Naming: engine gametype names come from the client's own rawfile `maps/mp/gametypes/_gametypes.txt`
(19 names; dumped on the last probe to %TEMP%\codol-claude-run-probe\codol_rawfiles\...); playlist
aliases (`tdm->war`, `kc->conf`, `hq->koth`, `inf->infect`, `ffa->dm`) are in alpha0022
resources/mp_playlists_shipRetail_cb2.info; the room UI puts the engine name on the wire
(alpha0022 docs/map_selection.md sec. 13.1). The server has no gametype mains of its own:
scripts/codol/maps/mp/gametypes/ holds forks of `_class _gamelogic _menus _missions _playercards
_teams`; mains come from alpha0022/vendor/iw4/maps/mp/gametypes/. Loader src/scr_vm_main.c:1170-1191
falls back silently to `dm` (:1185-1190) while serverinfo advertises the requested name. Note
src/sv_main.c:3202 registers g_gametype default "war" (latched) and scr_vm_main.c:1176 "dm".

| gametype (engine) | client lists it | server script | status | evidence | prio |
|---|---|---|---|---|---|
| dm (ffa) | yes; 29 rotation rows | vendor/iw4 dm.gsc | proven on mp_killhouse_sh | IMPLEMENTATION_PASS.md:2263, 2341; memory codol-map-load-state | - |
| war (tdm and variants) | yes; 109 of ~300 rows; room wire crc32("war") measured | vendor/iw4 war.gsc | present, unverified | map_selection.md sec. 13.1 | **P0** |
| dd, dom, ctf, sd | yes; 40/25/25/14 rows | vendor/iw4 | present, unverified; need objective array (sec. 3) and team scores (sec. 5) | vendor dir listing | P1 |
| conf (kc) | yes; 33 rows | missing (no conf.gsc anywhere) | falls back to dm | vendor list; scr_vm_main.c:1185 | P1 |
| combat (人机/新手训练 playlists 1/3; lobby currently sends desc[23]="combat") | yes | missing | falls back to dm | map_selection.md sec. 8b, 11.2 | P1 |
| infect (inf) | yes; 14 rows | missing | falls back to dm | - | P2 |
| sab, koth (hq) | yes; 2 / 1 rows | vendor/iw4 | present, unverified | - | P2 |
| arena, oneflag, vip, gtnw | yes (no playlist rows) | vendor/iw4 | present, unverified | - | P3 |
| hp, clanwars | yes | missing | - | - | P3 |
| coop | yes; 9 coop_* zones | missing; codol_zoneType would need `coop` | sv_main.c:3205 | P3 |
| zm | yes; 3 zm_* zones, room wire measured | missing; zm fs_crc never harvested | map_selection.md sec. 9 | P3 |

Maps: 15 mp_* zones installed under `...\client_shipRetail\chinese\` (plus 9 coop_*, 3 zm_*);
mounting is generic (`<map>.ff`, `patch_<map>.ff`, `common_gametype_<type>`, localized) at
src/codol/assets/codol_asset_commands.c:255-294, nothing hard-codes a map.

| map | client lists it | server loadable | evidence | prio |
|---|---|---|---|---|
| mp_killhouse_sh | yes (playlists 1/4/8) | proven: 6 archives, 2053 configstrings, 4,689 leaves, dm match, client spawns | docs/CODOL_MATCH_STARTUP.md:38-49; IMPLEMENTATION_PASS.md:2221, 2263, 2341 | - |
| mp_bog_sh | yes (8 gametypes) | partly proven: archives mount, collision 658 leaves / 432 dynents, game init under a minimal script set only | docs/CODOL_MATCH_STARTUP.md:15-31; docs/CODOL_MAP_CUSTOM.md:21-24 | **P0** (cheapest second map) |
| mp_afghan | yes (playlists 3/4/8) | unverified natively (Python prototype only) | alpha0022 map_selection.md sec. 8c, 11.3-11.4 | P1 |
| mp_rust, mp_overgrown, mp_underpass | yes; room-pick wire measured | unverified | map_selection.md sec. 13.1 | P1 |
| mp_cargoship_sh, mp_cross_fire, mp_nuked, mp_storm_spring, mp_bloc_sh, mp_estate_tropical, mp_fav_tropical | yes | unverified | .ff present; alpha0022 all_maps_readiness.md PASS rows are prototype-only | P2 |
| mp_crash_tropical | yes; also the dwRoomInfo default sentinel | unverified; 13+ historical client-side load failures | all_maps_readiness.md sec. 3 | P3 |
| mp_crash_intro | mp: no (coop only) | unverified | playlist grep | P3 |
| zm_asylum_sh, zm_prototype_sh, zm_zombie_training; coop_* | yes | unverified; no gametype | map_selection.md sec. 13.1, 9 | P3 |
| mp_bloc, mp_shipment | playlist rows but no .ff installed | not loadable | ff listing | - |

Structural loader limits: zone container format narrow (codol_fastfile.c:61-73, 512 MiB cap);
asset-type dispatch not total - types 17, 23, 32, 33, 34, 35 abort the whole zone replay
(codol_load_blocks.c:1699-1739, `default: return 0` at :1739; message at codol_asset_commands.c:290) -
the likely failure mode for untested zm_*/coop_* and unverified for the 13 untested mp zones
(verify with `codol_loadzone <map>.ff C1.exe` / `codol_checkcollision <map>`); PVS is an all-visible
stub (codol_collision_native.c:321-331); 2048 entities but `entityList[1024]` callers remain
(src/entity.h:461-472; IMPLEMENTATION_PASS.md:2244-2248); no in-process map change (sec. 7);
gametype fallback silent (scr_vm_main.c:1181-1190); codol_zoneType single-valued latched
(sv_main.c:3205; codol_asset_commands.c:259); missing assets substituted with defaultweapon_mp/void
(IMPLEMENTATION_PASS.md:2242); first-frame precache ~30 s with the infinite-loop guard off during
level.initializing (:2261).

## 7. Networking / session

| item | client expects / does | server status | evidence | prio |
|---|---|---|---|---|
| lobby / matchmaking (Demonware session create/find/join, party, ready, playlists, service 102 chat, store, rank push) | C1 reaches the game server only through the lobby (开始匹配 -> 准备) | external: alpha0022 `dw-capture.py` on port 3074 is still the lobby; nothing under src/ implements lobby services (grep findSessions/bdService: none) | IMPLEMENTATION_PASS.md:2316-2321; AGENTS.md ("preserve ... Python lobby/auth"); alpha0022 docs/lobby_open_items.md (a)-(h), MISSING-FEATURES.md LB-1..LB-10 | P1 (P0 if the Python lobby is retired) |
| bdDTLS association (INIT / COOKIE_ECHO / COOKIE_ACK / DATA 6/2, NAT INTRO, persisted associations) | secure transport | implemented natively | src/codol/net/codol_network.c:93-283 | - |
| DTLS record type 40 (18 bytes) from the client | alpha0022 observed it as the "<3" keepalive | dropped with a developer trace; harmless so far; whether C1 expects an answer is unverified | codol_network.c:280-283; IMPLEMENTATION_PASS.md:2344, 2362-2363 | P2 |
| secure profile (`stats` 27-chunk upload, `statResponse` mask, auto-attach, re-attach after restart) | profile at connect | implemented; twelve IW4-only playerdata roots answered from a discarded session store | sv_client.c:482-487, 1353-1358; docs/CODOL_STATS_UPLOAD.md; IMPLEMENTATION_PASS.md:2270-2290 | P1 (persistence) |
| end-of-game stats return / `uploadStats` | C1 58ba60 queues local console text uploadStats (not an outbound message) | reconnect/upload lifecycle "still under review"; no upload producer | docs/CODOL_MAP_LOADING_NOTICE.md:13, 34; IMPLEMENTATION_PASS.md:1456 | P1 |
| map_restart / map change | C1 `k`/`x` -> CG_MapRestart 0x467980 preserve 1/0 | k/x sent, but the restart fails to remount the map archives (CODOL_OpenFastFile failure); every script runtime error needs a process restart | sv_main.c:3830-3844; codol_asset_commands.c:255-299 (CODOL_ReplaceRuntimeArchives); codol_fastfile.c:47-49; IMPLEMENTATION_PASS.md:2265; memory codol-map-load-state | **P0** |
| reconnect after a server restart | fresh handshake each time; C1 caches its bdDTLS association | associations persisted across restarts (codol_network.c:93-181); alpha0022 found restore-on-startup revives stale sessions; native behaviour unverified | alpha0022 docs/reconnect_fresh_session_fix.md:13-57, 84-112 | P2 |
| host migration | C1 has partymigrate_* dvars (0x4aace0) | IW3 server-to-server OOB kept, console command disabled, no client-facing path | sv_main.c:1947-1949, 5369-5545; sv_cmds.c:2384; alpha0022 dvars_c1exe.md:213-215 | P3 |
| configstring transport | 1015-byte `d` values, single command each, C1 dispatcher 0x467350 | implemented; "separate specialized publishers and unmapped vote/system namespace issues remain" | IMPLEMENTATION_PASS.md:1446; docs/CODOL_DYNAMIC_CONFIGSTRING_TRANSPORT.md | P1 |
| snapshot recovery | client tolerates loss | unsupported frames go through reliable-message recovery, never an IW3 body | docs/CODOL_LIVE_SNAPSHOT_WRITER.md | - |
| voice (`v` OOB) | in-game voice | routed only; mute list unread | sv_main.c:1950-1951, 5296; sv_client.c:2774-2793 | P2 |
| box queries at 2048 entities | - | `entityList[1024]` stack buffers passed to SV_AreaEntities truncate | IMPLEMENTATION_PASS.md:2248 | P2 |

## 8. Biggest gaps (summary)

(pending)
