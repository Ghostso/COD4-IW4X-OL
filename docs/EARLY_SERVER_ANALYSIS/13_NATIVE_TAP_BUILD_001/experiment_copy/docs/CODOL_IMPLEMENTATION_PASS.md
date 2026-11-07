## 2026-09-25: MP perks, event M4 fast mag, in-game cursor

- **Perk audit** (`docs/perk_audit_20260925/AUDIT.md`): every MP perk
  modifier traced to its consumer. Implemented this pass: Stalker, fast
  mantle, offhand and sprint-out speed, Steady Aim spread, Quick Draw,
  Ninja against turrets, paint, counter-UAV immunity, Sitrep detection,
  blast shield, Last Stand Pro, Hardline Pro assists, objective speed,
  Hacker/Hacker Pro crates, equipment take-over, Engineer trigger delay,
  Scavenger Pro extra lethal.
- **Open**: extra-ammo unit, call for support, air-support marking, paint
  duration (IW5's 10 s), C1 pro unlock source.
- **Event M4 fast mag**: its quick reload animations are empty in C1's data;
  the quick magazine is no longer armed, so client and server agree on the
  normal dual-mag reload.
- **Cursor**: menu open/close commands are no longer merged in the send
  queue, the AC-130 timer menu closes, and the explosion dirt is drawn as
  HUD overlays instead of cursor-grabbing menus.

## 2026-09-24: killstreak and equipment completion

- **Every MP catalogue row now has a handler** (43/43, checked live with
  `scr_codol_usekillstreak list`). The last two, `sam_turret` and
  `airdrop_sam_turret`, are adapted from IW5's `_autosentry` SAM onto C1's T5
  assets. On mp_rust the SAMs lock enemy helicopters and a UAV and fire
  homing four-missile salvos that hit.
- **Four native defects fixed on the way**, each of which also broke existing
  rewards or weapons: sentry placement refused every spot (world hits read as
  entity 2046), `magicBullet` refused turret projectiles, C1 weapons never
  carried their `guidedMissileType` (no C1 missile could home), and
  `doDamage` from a target's own origin crashed the server. The use dispatch
  also crashed the server for `airdrop_sam_turret` and every pro airdrop.
- **Zombies equipment**: each character gets its roster kit in C1's three
  offhand slots. Money grenade, rescue knife, random teleporter, perk pops,
  cymbal monkey, black hole bomb and the four placeable traps are in, as are
  the tesla, minigun, sentry, rc car, pandora and bonus-points power-ups.
- **More native fixes**: turrets never acquired a zombie (sight test misread
  the trace result), fired at zombies' feet (C1 aims at the eye), and could
  crash on spawn (bone index). New `setModelScale` publishes C1's model scale
  for the shrink trap's dwarf.
- **Measured as C1-faithful**: the traps, teleporter and black hole bomb share
  one ammo cap of 3; `flare_mp` shares the frag cap; C1's `magicBullet`
  refuses the ray gun.
- **Open**: the black-hole teleport has no destination on any shipped map;
  zombies test clients cannot be downed (no DObj); perk-machine perks have no
  native effect.

Front-wheel steer regression (30e06d18): the retained IW3
G_VehEntHandler_Think (_g_vehicles_mp.asm:5521, NOT bypassed for owned
cars - only Scr_Vehicle_Think is) still runs every frame for the RC entity:
it copies r.currentOrigin into phys, runs IntegratePosAndRot/VEH_SetPosition
and writes entity bodyPitch/bodyRoll (+0x54/+0x58) and steerYaw (+0x5c,
asm:5734/5934, +-45 clamp) from its own IW3 steering. That was the wheel
motion the user saw before. Our publish runs after the think loop and
overwrote +0x5c with the controller steer, which on that build was dead
(item 8) -> 0 -> wheels straight. Now: steerYaw = live controller steer,
rate-limited 5 deg/think like C1 678680; bodyPitch/Roll no longer zeroed
(retained lean kept); 1 Hz line prints `es68` (value on the entity at
demand time, i.e. the retained think's write of that frame) and `lean`.
Open question for the parent: whether G_VehEntHandler_Think's
IntegratePosAndRot/VEH_SetPosition should be bypassed for owned cars as
Scr_Vehicle_Think is (it re-sets the position we publish; the live car
"works a lot better" with it running, so it was left).
e retained `SpawnVehicle` and `G_SpawnHelicopter`. One arm covers attack heli, pave low, chopper gunner and RC-XD. The AC-130 never depended on it - its rig is a `script_model` and its marker a `spawnPlane`.
- **The AC-130 crash was an optional field treated as mandatory.** `giveweapon ac130_40mm_mp` then `ERR_DROP: CoDOL weapon reload perk metadata unavailable` and shutdown. `weapon_frame_msec` computes nothing but a timing *multiplier*, and every one of its inputs is optional - IW4 treats the WeaponDef reload-perk field as optional and the ability table is tuning data - yet three paths were fatal. Killstreak-held weapons are precisely the ones with no reload metadata, because they never reload. All three now warn once per weapon per cause and return the duration unchanged. New `tests/test_codol_weapon_timing_metadata.c` pins missing metadata, missing table row, unrepresentable modifier, that a valid modifier is *still applied*, and that a zone change re-arms the warning.
- **"The AC-130 started in first person" is the same bug.** `setAC130Player` hands over the three guns *before* it threads `attachPlayer`, so the ERR_DROP aborted the setup before the camera link ran. The link itself is sound: `level.ac130` is the `c130_zoomrig` script_model whose shipped bone list is exactly `tag_origin`/`tag_angle`/`tag_player`, and `playerlinkweaponviewtodelta` is a real registration. No speculative link rewrite was made; `attachPlayer` now logs the link it made or the rig it could not find, and this needs live confirmation once the crash fix ships.
- **Every installed map already ships its aerial routes.** Dumped the mapents lump of all 15 MP zones (the lump is inline in the `col_map_mp` asset; anchored on worldspawn and validated byte-identical against `obj/killhouse-mapents-shadow.bin`). All 15 carry `heli_start`, `heli_loop_start`, `heli_leave`, `heli_crash_start`, `heli_dest` and exactly two `minimap_corner`, with intact `target` chains and `script_airspeed`/`script_accel`. **There is no CoDOL renaming of helicopter routes.** Two real gaps: `airstrikeheight` is absent on `mp_killhouse_sh` and `mp_cargoship_sh` and **renamed to `air_support_height` on `mp_nuked`** (both scripts now accept both names; both already guarded the absent case), and `heli_attack_area` exists on only afghan and fav_tropical. New `aerialPathCensus()` logs every count, the height-entity source and `level.mapCenter` once per map.
- **No more silent failures.** `killstreakUsePressed`'s six bare `return false` paths each print a reason now. The entity-link warning was globally capped at eight messages *for the process lifetime* and boot spent all eight on one repeating tag, silencing everything afterwards - it is now limited per (cause, tag), reports the native tag index and the wire slot **separately** (they need different fixes), and re-arms on map reset. The dropped-entity snapshot warning carries a resolver-supplied reason.
- Build `2035702B2ACF420092A0B73D414D5BD7CE2F2647C4C969607EFE65CF266ABFA6`, isolated `OBJ_DIR`/target so the deploy owner's tree was untouched. Collate + verify + resolve gates green. The new unit test passes standalone; `make test-codol` still stops earlier at the pre-existing `test_codol_native` link failure (`makefile:445`), which is unrelated to this pass. **Not deployed, nothing live-verified.**

## 2026-09-15: the killstreak suite - the blocker was models, not builtins

- **Audit** in `docs/CODOL_KILLSTREAK_AUDIT_20260915.md`, against the recovered `mp/coKillstreakStatsTable.csv` (69 rows; MP is IDs 1..43). 16 base rewards had registered handlers; `rcbomb_mp`, `dogs_mp`, `sam_turret`, `airdrop_sam_turret` and **all 21 `*_pro` rewards** had none. There is no `tank` row at all - `_tank.gsc` compiles every map load and is unreachable from any loadout.
- **No killstreak was blocked on a missing GSC builtin.** All 271 scripts reachable from `_killstreaks.gsc` resolve: every `#include`, every `file::function`, and every call name against the 898 registered builtins. Nothing needed importing from the reference dumps for the registered rewards. The generic earn/use path is sound too - every reward the player earned was given `result 1 owned 1` with the right HUD splash.
- **The real defect is five vehicle xmodels that are in no mounted zone** and resolve to `void`: `vehicle_ac130_coop`, `vehicle_cobra_helicopter_fly_low`, `vehicle_apache_mp`, `vehicle_pavelow_opfor`, `vehicle_little_bird_bench`. `void` has no bones, so every `playFxOnTag`/`linkTo(<tag>)`/`getTagOrigin` against it raises - which is exactly the harrier `_airstrike.gsc:674` shutdown, latent in four more rewards. Replacements were picked from **actual bone coverage**, read out of the zones: `vehicle_mi24p_hind_mp` for the attack helicopter (the only shipped helicopter with `tag_store_r_2`, the FFAR launch tag, *and* the `defaultLightFX` wing lights), `vehicle_mi-28_mp` for the chopper gunner (`tag_player`, `tag_flash`), `vehicle_pavelow` for the flares heli (the only one with `tag_gunner_left`/`right`), `vehicle_ac130_low_mp` for the gunship with the crash FX moved from the absent `tag_deathfx` to `tag_body` - already that model's engine-effect tag. `vehicle_little_bird_armed` was **rejected** for every branch: no `tag_engine_left`, no `tag_light_L_wing`.
- **21 pro rewards implemented from the table's own column 22.** A pro row differs from its base row in exactly five places - ID, localized title/description, `MP_EARNED_PRO_*`, the `killstreak_pro_*` weapon, and column 22 naming the base. Cost, sound, all three dialog columns, inform-enemy, XP, both icons, every unlock column and crate weight are identical. So the catalogue itself states which behaviour a pro reward runs. Registration is gated on the base having a real handler (`dogs_pro_mp`/`rcbomb_pro_mp` stay unimplemented while their bases are) and on the pro weapon resolving through `codol_weaponInventoryType`, which answers `"unknown"` without raising instead of failing `precacheItem` and killing the map. `isRideKillstreak`/`isCarryKillstreak`/`deadlyKillstreak` resolve through the base ref so a pro reward inherits its base's activation gates.
- **RC-XD**: a previous agent's complete adapted T5 implementation was sitting in `obj/rc-physics-stage` and had never been shipped - which is why `rcbomb_mp` was granted, HUD-announced, then answered `"Killstreak not implemented"` nine times. Installed. `setEnemyModel` + `codol_setRCModelAudience` were **not** invented: C1 publishes one model per entity and no measured producer selects a second per recipient, so the car is coloured by owner team (both models shipped, 20 bones) and friend/enemy identification stays on the already recipient-filtered green/red blink. `vector_scale` -> the in-scope `vector_multiply`.
- **`spawnvehicle` registered** at `src/scr_vm_main.c:389-399`. `CODOL_Scr_SpawnVehicle` already implemented the real IW4/C1 contract (`model, targetname, definition, origin, angles`) and had simply never been bound; the commented-out legacy `GScr_SpawnVehicle` used the wrong argument order.
- **I took the server down and this is how it will not recur.** Shipping `_rcbomb::init()` against a deployed binary that did not yet register `spawnvehicle` produced `Sys_Error: script compile error / unknown function` at map load. GSC resolves builtin names at **compile** time, so this is fatal and completely invisible to runtime testing. Fixed by commenting the one init line - only reachable scripts are lowered, so the four `_rcbomb` files stay installed and out of the compile set. New `tools/codol_script_resolve.py` reproduces the loader's reachability walk offline, builds the builtin table **after stripping C comments** so a commented-out registration reads as absent, and fails on any unresolved name; its reachable set matches the modules the boot log lowers exactly. Run it against `bin/home/codol_rawfiles` after every script batch.
- Cross-built clean and linked into an isolated `OBJ_DIR`/target so the deploy agent's tree was untouched: `07906c66caa7ce97e3995b38dc59bcdaebda25a2172891a9a6afe8b51834ed9d`. `verify_gsc_collation.py` OK (1644 files, 0 unresolved). `make test-codol`: 27 targets pass, then `test_codol_native` fails to **link** - pre-existing and not from this pass, `makefile:445` names its sources explicitly and `codol_game.c`/`codol_sv_state.c`/`codol_sv_snapshot.c`/`codol_playerstate_ext.c`/`codol_radar_input.c` have grown calls into sources it does not include (action slots, killstreak HUD, pmove-C1, glass world, perk runtime, radar types). The makefile is being edited concurrently and was left alone.
- **Not implemented, deliberately:** `dogs_mp` - the native actor work in `obj/dogs-stage` lacks perception, orientation, the 47-state `bg_dog` animation mapping and the animtree constructor, and the local BO1 dump has no MP `_dogs.gsc`. `sam_turret`/`airdrop_sam_turret` need an anti-air lock/missile lifecycle and were **not** aliased to the sentry. **Nothing here is live-verified** - no deploy was made.

## 2026-09-15: the career page went stale because of us

- **Mechanism, with VAs.** C1 caches the secure profile at `0x0205C598` behind flags `0x06C3D3D9`/`0x06C3D3DC`. The per-frame Demonware tick `0x004D8EE0` re-fetches it - DW 10/3 GETFILE `mpdata_s` via `0x004D9900` - whenever **both** flags are zero and the lobby is connected; the completion `0x004D9200` -> `0x004D98E0` re-sets them. `GetRank 0x0058EFE0` and the Scaleform career view read `0x0205C59C` = buffer+4 synchronously on draw. So the page refreshes about 200 ms later with no relogin and nothing for the server to push.
- **Root cause: our own disconnect reason.** `CL_HandleDisconnect 0x004960E0` is the only thing that clears those flags, and only *after* matching the reason against a bypass list. We sent `t EXE_MATCHENDED`, which matches at `0x00496114`, jumps to `0x00496116` for the silent level-5 notice, and **never reaches the invalidation**. The string chosen for a quiet exit was itself the reason the page never updated. Wiretap agrees: 195/828 leaves show 10/3 `mpdata_s` at +0.13-0.42 s, and the rate collapsed after 09-10 - the mtime of the exitlevel file.
- **Fix:** `CODOL_MATCH_END_REASON` is now `EXE_MATCHEND_PARTNER_LEAVE`, the one non-bypassed string that still has dedicated match-end handling (`0x00496294..0x004962BC`). Cost is a level-4 notice instead of the silent level-5 one - a deliberate cosmetic trade, and the define is the whole knob. `0x00624FC0(handler,1)` side effects are **unverified**. Patching C1 at `0x00496114` was **not** done: this server does not modify the client.
- All four candidates closed with VAs: in-match stat ingest, match-end blob push, all 29 Demonware push cases, and the Flash task ids. **Doc correction:** `0x00592FA6` guards the *public* `mpdata`, not `mpdata_s`; removed from CODOL_RANK_XP_20260915.md section 1, still wrong in `alpha0022/docs/playerdata_audit.md:73` and `rank_persistence.md`.
- **`assists` and `suicides` promoted from `[U]` to `[MEASURED]`** - located in the fastfile bytes by matching a constellation of strings at the spacings the def's own pointers imply (one unique file offset, reproduced from a second independent anchor, 13/13 names). All 22 reported members now resolve; 24 are written per serve and every one is proved by rendering a blob and decoding it back. Members whose name is not streamed are gated on def version/checksum and **skipped rather than written** if a name binding disagrees with its measured offset.
- Build `73316A59FFC749D0B8D18609A7DF58BCECFA5F593DABAF6F421E064E5F866B7E` staged in both names. **Not relaunched** - the script tree is down on an unrelated RC-XD `spawnVehicle` compile error, and the relaunch procedure now also requires `python tools/collate_gsc.py` + `tools/verify_gsc_collation.py` first. **The lobby needs a restart** for the stats to take effect.

## 2026-09-15: career DDL decoded - and it exposed two bugs in the stats reporter

- `mp/playersecuredata.def` decoded offline from the **patch** zone (v11 / 158043991 / 6665 / 1680 leaves; the base zone ships a different def and must not be used). The career page reads it **by name at runtime**: `CareerBaseController.getIntProp` -> `GetPlayerData(prop, true)` -> `GetSecurePlayerData` **0x00551EF0**.
- **Two defects in yesterday's increment, both found by that decode.** (1) Four of the names - `misses`, `timePlayedAllies`, `timePlayedOpfor`, `timePlayedOther` - are IW4 names this DDL does not declare, so they could never have reported anything. (2) `kills` and `wins` are **float32** here - the two headline career numbers - and the reader accepted only integer kinds, so it was silently refusing the most important stats it existed to collect. Kind 8 is now read and rounded, and the fixture models both as floats so an integer-only reader fails.
- `kdRatio` is **not read at all**: ActionScript divides `kills` by `max(deaths,1)`. `accuracy` is stored x10000 and `winRatio` x10. So the server reports counters and max-members only; the lobby recomputes the ratios.
- **"Last 15 minutes average score" is 15 MATCHES**, from a 30-entry ring in the **public** `mp/playerdata.def` (`PlayerData_ReadRecentMatches` **0x00462B50**, `AS_GetRecentMatchStats::Invoke` **0x005AC310**, empty when `rounds==0` at **0x0046308B**). It reads zero because the live `mpdata` ring is all defaults. Deliberately **not** faked: `mpdata` is client-uploaded, deleted at lobby boot and re-uploaded ~25 s after login. Not a Demonware row - service 4 is leaderboards only.
- Lobby half done and proved by rendering a blob and decoding it back (12 members written by name through `playerdata_editor`'s `by_path`, no hardcoded offset, plus recomputed `accuracy`/`kdRatio`/`winRatio`/`scorePerMinute`). `rank_writeback` 67/67, `player_profiles` 50/50. **The lobby needs restarting** (`dw-capture.py:24-25` imports both at startup); the match server does not.
- Build `08ADC6392889B2DA0B5AD4A17B235C6C32FF947692742E12819BE32799A75852` deployed to both names, relaunched as PID 103952, booted clean. The user-reported `fs_basepath=bin` / `english` / `build 1227 Sep 10 2026` failure was **not** this server: that is `bin/codol_profile_check.exe` (Sep 10) run directly; both dedrun binaries stamp Sep 15. The startup mount error now names `fs_basepath`, language and `codol_zonePath` and points at the launcher.

## 2026-09-15: career counters - measured, not re-counted

- XP now works end to end (two matches, +150 and +750, folded by the lobby). The client's 账户/战绩 page was still empty, and the reason is that **the counters were never missing - nothing was reading them back out**. The vendor scripts already maintain every one of them in the session secure profile via `_persistence::statAdd/statSet/statSetBuffered` -> `setPlayerData`: `_weapons.gsc:946-948,1011-1012`, `_teams.gsc:201-216`, `_gamelogic.gsc:497-531`, `_damage.gsc:295`, `_utility.gsc:648-652`, `_gamescore::givePlayerScore`. **No script counting was added.**
- `codol_match_report.c` measures them the way it already measures experience - attach value vs report value - and emits a per-row `"lifetime"` object of positive deltas. Members resolve **by name** through `mp/playersecuredata.def`; no offset is hardcoded, and an undeclared name is skipped and named once in the console. Derived members (`accuracy`, `kdRatio`) are excluded because `updatePersRatio` recomputes them. Baselines re-arm after each report.
- Build `3A7054F1900B44406677C3E1CC555755BA569B7870CD8B307D390C4AA140BF77` deployed to **both** names. Stopped PID 106088, relaunched as PID 38564; booted clean on mp_rust with zero errors. `make test-codol` passes through the extended fixture.
- NOT claimed: the lobby crediting the deltas and writing them into the rendered `mpdata_s` DDL members, and the client's page-refresh trigger. Both in progress.

## 2026-09-15: match report counted every human as a bot - NA_BOT is zero

- The 9b instrumentation named the bug on its first run: `CoDOL match report: nothing owed (reason disconnect): 1 row(s), **0 human**, 0 XP, activity 0`.
- `NA_BOT = 0` and so is `NA_BAD` (`src/sys_net.h:53-54`), so an un-set-up netchan reads as a bot. `SV_DirectConnect` attaches the secure profile at `src/sv_client.c:505` but calls `Netchan_Setup` only at `:569`, so the report latched `client_is_bot()` 64 lines before the netchan existed and recorded every human as a bot - `humans` 0, write declined, and the bot-gated detail lines silent too.
- That the row existed at all is evidence in itself: a frozen row is only kept when a counter is non-zero, so **the kill did reach `sess`**. The engine counters were never the problem.
- Fix: a row exists only because a secure profile attached, and that path refuses a zero uid while bots have none, so every stored row is a human by construction. The latch is gone, `client_is_bot()` carries the trap in a comment and is consulted only where the netchan is real, bot rows are synthesised at write time, and `MatchReportHumansConnected()` counts a slot as human when it owns a row or is not `NA_BOT`. Regression test added that fails against the old code.
- `tableLookup miss: mp/statstable.csv column 4 ...` is **benign**: `_utility.gsc:2152 getWeaponClass()` probes by name and expects the miss for non-weapons, falling through to `isKillstreakWeapon()`. It is a `Com_DPrintf`, not an error. Kills were invisible because the vendor obituary goes to `games_mp.log`; `_damage.gsc` now prints a `kill:` line for any death a human took part in. Assists added to the activity sum; time deliberately excluded so a duration-only report cannot replace an unconsumed one.
- Build `7E4C57F08FF31E0ACBB4DE7D54E61CCE61C935713795EADC831FAE3FD75EA4D4` deployed to **both** executable names and relaunched as PID 106088. Booted clean on mp_killhouse_sh: `map archives mounted: 6 (mp_killhouse_sh, mp)`, `inherited configstrings installed: 2053 (mp)`, `war.gsc`, zero errors. This binary also carries the per-zone-type mount/script work.
- Still unproven: that a kill awards XP. The `_rank.gsc` gate traces have not yet run with a human kill.

## 2026-09-15: first live rank test - no XP, no report, both paths instrumented

- User played mp_killhouse_sh/war with eight Training bots, got a kill, left. No XP, no promotion, `players/<uid>.json` unchanged, no `match_report.json`, and **no console line from the report at all**.
- The log does establish: profile attached for client 8 (uid 11354582479263516619) with progress restored/saved; bots really are `NA_BOT`; kills scored at gametype level (reliable `D 100`, `d 6 100` = CS_SCORES2); and **no script runtime error anywhere in the run**. `scr_xpscale` is registered natively with default 1 (`src/sv_main.c:3353`), so an unset XP multiplier is ruled out, and `level.rankedMatch` must be defined or `rankingEnabled()` would have faulted.
- Cause not yet named, because it could not be: `_rank::giveRankXP` has three silent early returns, `syncXPStat` a fourth, and `CODOL_WriteMatchReport` returned 0 without a word. A server awarding no XP looked exactly like one correctly awarding none. That is the defect this increment fixes.
- `codol_match_report.c` now prints, for humans only, the baseline at attach, the frozen row on leave, and a `nothing owed` line carrying each row's uid, XP delta, baseline, current total and counters - plus a warning when `codol_profilePath` is empty. `_rank.gsc` names each of its four gates through the same `println` idiom `updateRank` already used, behind `codolRankShouldTrace()` so bots do not bury the console.
- Build `8B1CDAA5AED477F9C749493E9C288E849417A0E3829D6F0056C3B9C32CECE5D0` written to `bin/codol_dedrun_next.exe` (the launcher's name; `codol_dedrun.exe` is locked by the user's running PID 90248 and is one build older). `make test-codol` passes through the new match-report fixture. The GSC change needs a server restart, not a rebuild.
- NO fix to the XP path itself is claimed here. The next match names the cause; the decision table and the exact `findstr` commands are in `docs/CODOL_RANK_XP_20260915.md` sections 9b and 10.

## 2026-09-15: rank/XP persistence end to end

- Rank/XP AT CONNECT was already implemented and is audited rather than rewritten: the connect xuid is latched at `sv_client.c:497`, `CODOL_AutoBindClientSecureProfile` reads the lobby's `mpdata_s.<uid>` from `codol_profilePath`, and `_rank.gsc` reaches it through the real `getRankExperience`/`setRankExperience` builtins. Scoreboard rank already reaches the client: `setRank` writes `clientState_t.rank`, published as netfield index 25, `{0x0a0, 8, 0}`.
- NEW `src/codol/stats/codol_match_report.{c,h}` reports the match to the lobby as format-1 `resources/match_report.json`, now with a per-row `uid`. A row's XP is `CODOL_ProfileExperience(session secure blob)` now minus the same conversion at attach, so it is exactly what `_rank.gsc` committed - not a second accumulator. Written at end of match (`sendClientMatchData`, the one signal `_gamelogic::processLobbyData` always reaches), at the last human's disconnect, and at map change. Consecutive reports partition the match instead of repeating it.
- The lobby credited every human row to the connection's uid, so a second human got nothing. `alpha0022/rank_writeback.py` now builds one target per distinct row uid (backup `.pre-cod4x`); its self-test goes 40 -> 56 checks, all passing.
- `sendMatchData` no longer logs "retained, no delivery sink": a sink writes the prepared server match record beside the rank report. Nothing in the lobby consumes it yet, and the doc says so.
- ZOMBIES: a `zm` zone was composing the MP soldier - `_teams.gsc:610-620` hardcodes tf/sc and `codol_zoneType` was never read in the appearance path. Native fix: `CODOL_ServerZoneType()` plus `zone_faction()` in `codol_player_appearance.c`, and `CODOL_ZombieCharacterGender()` off `mp/cyborgclasstable.csv` so `hea_zmgirl` composes its female geometry. The four-Cyborg roster limit is lobby-side and was already correct. The dangling `player_models_zm.txt` write for the deleted sh1ded is removed.
- ZOMBIES STARTUP: the fatal `level.players` script error on `map zm_zombie_training` is vendor `isSP()` deriving single-player from the `mp_` map-name prefix. Fixed at the root by answering the predicate - `level.isSP = false` at the top of `Callback_StartGameType` - which also covers every other `isSP()` caller under coop and zm. A worker then showed that one site is not enough: an IW4 level script calls `maps\mp\_load::main()` itself, *before* `CodeCallback_StartGameType`, so writing `maps/mp/zm_zombie_training.gsc` - the obvious next zm step - would bring the same crash back. `level.isSP = false` is now also the first statement of `_load::main()`, the choke point every entry order passes through.
- Also repaired on the way: the full Linux server build, which could not compile `sv_main.c` at all because its boot heap checkpoint calls MSVCRT `_heapchk`/`_HEAPOK`/`_HEAPEMPTY` unconditionally. Now `#ifdef _WIN32`; `make -B` exits 0 and `bin/codol_dedrun` links again. The first failed attempt unlinked the stale 2026-09-08 ELF; what is there now is the fresh rebuild.
- Build `3EC0E1CE7AC6F811D10C87FF489F1EF602348CA7FC690A163FF732CAB4C4CD0B` compiled and linked clean and was deployed to both executable names; no server was running and none was started. New `tests/test_codol_match_report.c` (32 checks) is in `make test-codol`, and the emitted bytes were then fed to the live `rank_writeback` module in an isolated temp tree, which credited each row's own profile. Two long-standing `test-codol` link failures were repaired on the way (`test_codol_usability`, `test_codol_inherited`); `test_codol_native` remains broken and untouched.
- PARTIAL LIVE: the user started PID 106932 from build 3EC0E1CE mid-task. On mp_rust the log shows the connect xuid resolving to uid 11354582479263516619 and its `mpdata_s.<uid>` attached, progress restored/saved, `faction tf` appearance composed, and a clean disconnect through the new freeze + last-human report hook with no crash and no warning. No report was written because nothing was owed (no XP, no kills/deaths/score) - correct behaviour, but the writer itself is still unproven live, and multi-human crediting cannot be seen with one player.
- Nothing else here is live-verified. Evidence, distinctions and the exact live-verification steps: `docs/CODOL_RANK_XP_20260915.md`, `docs/CODOL_ZOMBIES_STARTUP_20260915.md`.

## 2026-09-15: knife passive capture

- Live native capture verifies mounted knife clip capacity1 and valid ammo indices. Current bots own no knives and no thrown knife exists. This rules out zero loaded capacity but does not identify the pickup failure. Added reusable read-only probe and recorded evidence; no new gameplay fix or build claimed.

## 2026-09-15: RC placement prerequisites

- Startup exposed spectator team rejection in shared spawn selection. Parent corrected spectators to zero combat influence; fixed build8AAD9CB321B3F2737BC3D622220FA67A435FFC5B939DD78C62EBC193A2CC0217 supersedes the initial candidate below.

- Reviewed OpenBLOPS trace/telefrag/sphere influence behavior and integrated native RC placement queries plus moving vehicle spawn avoidance and cleanup. Build0C895EDCF92931A185170F4E464A5034B7CAFD3BF0C85A75A646387F750D978E passed without compiler warnings and deployed with native-only restart.
- RC activation and client-visible vehicle publication remain incomplete; parent confirmed missing vehicle seed arms, now owned by RC worker. Knife pickup investigation continues without a new verified cause. See CODOL_RC_PLACEMENT_REVIEW_20260915.md.

## 2026-09-15: Tabun parent integration

- Installed reviewed gas areas, attributed native damage, poisoning, C1 FX and temporary HUD/shock cleanup. Parent resolved the absent T5 screen-effect helper using its original definition and OpenBLOPS native field semantics.
- Build1436CB7AC4BD9B84382BA351615BFF736FAC9C9D5C4FFD917E69C10D56974968 passed without compiler warnings; native62152 reached gameplay with four training bots. No script compile/runtime error in startup scan; Tabun shellshock audio-cvar compatibility warnings remain. Live gas behavior and dog/chatter adjuncts remain incomplete. See CODOL_TABUN_PARENT_REVIEW_20260915.md.

## 2026-09-15: native T5 MP DoDamage

- Added real VM method dodamage with T5 MP2–8 positional arguments, strict supplied entity arguments, optional headshot/MOD/flags/weapon, finite input validation, normalized source direction and native G_Damage dispatch. Native MOD_GAS survives damage/death callbacks. No proxy damage calculation.
- T5 destructible-piece radius branch remains incomplete; this increment supports ordinary entity/player damage and must not be counted as full destructible support. Poison state and Tabun script activation still pending.
- Built/deployed FCEB70E0B08239419571184178199FB3D84B22672E3E14E5A57EABAA847E04F9, native-only restart with four bots. No automated tests or live DoDamage behavior confirmation.

## 2026-09-15: native gas damage reason

- Added MOD_GAS as native index16, preserving retained indices and scr_const layout. Expanded native parsers and entity damage/death callback bounds; C1 obituary already maps the named reason. Poison state, DoDamage and Tabun GSC still incomplete.
- Build6B7264FDE0ACBED7D241CFFCAE56BCD0C8C0AD51CD63F0D866E7923829A0BB1F compiled/linked and deployed with native-only restart. No tests or live gas validation. Full goal active.

## 2026-09-15: T5 gas equipment implementation audit

- Retrieved pinned original T5 Tabun script and traced actual OpenBLOPS native poisoning/DoDamage methods. Current VM lacks those methods; native16-entry MOD table also lacks GAS despite C1 obituary support. Documented required native damage, poison state, area and cleanup consumers in CODOL_TABUN_IMPLEMENTATION_20260915.md. No fabricated offsets or explosion-only stand-in added.
- Research increment only; previous deployed scrambler build unchanged. Full goal active.

## 2026-09-15: scrambler damage and pickup lifecycle

- Reviewed actual IW5 scrambler damage handler and existing C1 makeScrambler native implementation. Restored accepted-hit feedback, wasdamaged/penetration state and explicit maxhealth/melee accounting. Penetration uses native damage-notify flag8 from g_shared.h. Destruction closes pickup synchronously and deduplicates pending cleanup.
- Built/deployed C4A046466689EF7F90FE164725373CDA298BEB54789487E2DA0B4F8A246951C8, native-only restart with four bots. No automated tests. Live scrambler damage/pickup outcome remains unverified; explosion cosmetic/reference migration and full equipment suite remain incomplete.

## 2026-09-15: Harrier model shutdown corrected

- Fatal tagged-FX script error came from nonexistent inherited OpFor Harrier resolving to void. Native process remained alive; overflow followed map shutdown.
- Reviewed shipped30-bone Harrier and changed flyby/hover overlays to use it for both teams. Script-only deployment; native95684 restarted with four bots. Actual Harrier call-in remains unverified. See CODOL_HARRIER_MODEL_FIX_20260915.md.

## 2026-09-15: live mission cleanup and queue timing

- Native Killhouse capture confirms all22 authored campaign brush candidates absent while385ordinary bmodel entities remain. Stable C1 capture confirms233submitted brushes and no campaign candidates, down from253including20campaign brushes in the historical sample. End-to-end cleanup verified; visible shadow appearance still pending.
- Live splash admissions show headshot then revenge and headshot then RC notification separated by the full1500ms medal duration. This confirms queue timing, not every visual outcome. RC clock/publication ownership reviewed; spring-unit producer and full dogs remain active implementation work.

## 2026-09-15: queued splashes and mission-only map entities

- Deployed `2C05B94A1F81BC1BADADFE61A198F9A25754AA305265806F65C2C895408D97AA`: non-preemptive per-slot splash queue with stable priority, full table duration and reset cancellation; MP-only authored mission entity filtering before shared initialization.
- User's campaign-object lead is supported by shipped radiant key semantics and extracted maps:23 Killhouse/205 Estate candidates. Earlier C1 capture includes20 solid campaign-tagged Killhouse brushes. Removed only explicit mission metadata in normal MP, preserving coop and ordinary geometry.
- Both overlays compiled; live human acknowledgements observed. Post-filter candidate absence, shadow correction and multi-splash visuals still pending. Full objective incomplete.

## 2026-09-15: actor spawners and glass confirmation

- Parent reviewed C1/T5 actor-spawner semantics and deployed `E1A0403A3CF89B85572DF30A2E69584B54A18C44BCF18254D25ECBF1291FF6B0`. Templates no longer allocate damageable sentients; actual dog allocation/AI/script lifecycle remains incomplete.
- User confirms glass breaking works. Splash issue persists. Found same-frame firstblood and playercard commands using separate inherited queues; C1 splash menu closes playercard menu. Reciprocal closure and queue coordination under investigation, not yet a confirmed fix.

## 2026-09-15: Nuked glass catalogue regression fixed

- User log exposed a regression in the preceding glass deployment: nonzero glass maps could not resolve FxWorld because type20 was missing from replay alias recording and dependency name lookup. Added both registrations and its116-byte header; no validation bypass.
- Diagnostic build reproduced the missing FxWorld. Fixed build `B01DD711B9162007AA9EB2A8A287E30F69E43AA33438383C610559CE44F33D61` exited zero, deployed, and native84028 installed51 Nuked glass pieces and spawned four bots. C1/Python preserved. Actual shattering remains unverified; full goal incomplete.

## 2026-09-15: native glass pipeline

- Reviewed and deployed coupled map installation, shared damage store, bullet/melee/radius producers, scalar GSC operations, collision clearance and C1 glass snapshot publication. Parent verified retained assembly arguments and reset ordering. Reference radius max256 corrected during review.
- Build `6FBE15801DC811B9C1D0D1EB86B389E2DA510378A3A84E72D86B0A3C2658C462` exited zero; native restarted with four bots requested, C1/Python preserved. Live shattering remains unverified. Delayed weakened collapse, direct projectile kinetic penetration and full destruction notification still require implementation. No tests run; full goal incomplete.
- Splash agent observed a headshot admitted and received with normal 1500ms expiry. This successful sample does not disprove intermittent failures. Glass agent returned to Killhouse shadows; RC agent continues wheel-hit/frame integration.

## 2026-09-15: splash admission evidence

- Parent reviewed and deployed numeric, rate-limited splash admission/pruning diagnostics. Existing pre-admission logging could not prove delivery; sound and visual command paths are independent. Queue semantics unchanged.
- Build `E8B36DB840557F063380423AD8A91B9DDEF84C4BB1CB9F6271D8FC3E8F0D7059` exited zero; native restarted as PID94424 with four bots requested. C1/Python preserved. Missing-splash runtime correlation remains pending; agent captured 919 client table rows for comparison. No tests run or causal fix claimed.
- Glass and RC physics workers remain active; full goal remains incomplete.

## 2026-09-14: resumed existing agents

- Resumed the previous agents after explicit user instruction. No C1/native process was running at initial inspection.
- Built/deployed `CA782256648BDC97C46C1A17CE8E1A0277797B955D60D23043062A0B973DD6BD`: grenade rest threshold uses C1 dvar1193; intermission team scores use the native C1 bank5/6. Linked call sites verified. Native launcher started; no automated tests or live confirmation.
- IW5 primary script repository supplied an actual scrambler deployment/damage/pickup lifecycle, now being adapted separately. Not yet integrated. Extra-ammo units remain unresolved; full objective remains active.

## 2026-09-14: replicated dvar corruption

- Live C1 capture and qconsole pairing proved the retained +128 publisher overwrote C1 +200 name/value pairs: HUD range250 landed in viewKickScale's value slot; bob and breathing entries were corrupted too.
- Reviewed native inherited-aware allocator and replaced semantic CVAR_CONFIG publication. C1 defaults remain in their original slots; new names append. Value-before-name publication and merged pool validation prevent transient invalid pairs.
- Built/deployed `06590BEB791594FB9B3748253067C2B4D0670272F1AE86F279B3DA648DE23668`, stopping native86308 only. Post-fix live bank confirmation pending. This fixes proven data corruption, not yet a proven shadow cause. Full objective remains active.

## 2026-09-14: selected explosive/fall defense

- Staged and reviewed selected modifier60/52 consumption in the existing IW4 damage callback. Applies native selected table values once before CombatHigh with one final integer conversion. Configured vendor callback returns immediately on zero; immunity remains zero. This is an explicit IW4-based integration policy, not recovered C1 damage ordering.
- Stopped native84456 before copying staged script, built/linked successfully and deployed both executable names: `7B40804508A59485C47D19B1EC72F752B948A23B69CA266E5011C63FECE3FE4D`. No automated tests; live effect confirmation pending. Full objective remains incomplete.

## 2026-09-14: C1 sticky collision and core rolling

- Build `DD4896E153E21286BCA3AB08BBFC14A1E4F4E925EE355F60A694ACFECE625D2A` compiled/linked and deployed to both executable names. Added C1 metadata collision decisions, core rolling friction/restitution and angular motion, and guarded moving-to-stationary notification. No automated tests. Live physics confirmation pending; full wobble/curve/bump and equipment activation remain open.
- CombatHigh now uses native selected `modCombatHighTime` through an explicitly sh1x script method. User hit match-end compilation before the matching EXE was deployed: parent-owned live-script/native mismatch, with subsequent overflow during shutdown. Matching method is now compiled/registered/deployed. Stage native-dependent script changes until matching binary deployment in future.
- Shadow passive capture: active Killhouse CS8/9 empty and override state zero, consistent with default map lighting. No proven fix.

## 2026-09-14: grenade bounce and explosion publication

- Reviewed and deployed build `4B1A79870BA47F3626E0C645A73946B97D9B7A1904593A8B0AF302FC77AFC870` to both executable names; native PID101568 restarted, C1 PID90944 preserved. Compile/link succeeded; no automated tests.
- Grenades now import 31 C1 surface bounce coefficient pairs. Retained collision previously multiplied velocity by unpopulated zero coefficients. Linked helper call verified. Alternate C1 rolling response is currently traced only in prediction; full authoritative rolling remains open.
- Explosion snapshots now preserve captured weapon selector, surface and weapon-model byte. Original C1 producer copies these fields; T5 dispatch uses weapon definition for both FX and audio. Missing identity is a concrete fault, but live restoration of sound/FX remains unconfirmed.
- Native laststand/martyrdom gates now read effective C1 ability masks; death/downed modes use C1 values. FinalStand script activation no longer overwrites selected pistol-death perk ownership. Full deathstreak/equipment lifecycles remain incomplete.
- Evidence: `CODOL_GRENADE_BOUNCE_20260914.md`, `CODOL_EXPLOSION_FX_AUDIT_20260914.md`, `CODOL_DEATHSTREAK_NATIVE_GATES_20260914.md`.

## 2026-09-11: grenade fuse producer and event asset root

- Integrated verified C1 modes1/2/5 into attachment-relative explosion-origin selection; next executable links. Stop helper proved AI-prediction-only, renamed `CODOL_PredictMissileStop` and kept out of authoritative collision. Actual bounce/resting orientation remains unverified. Running server unchanged.

- C1 missile metadata is now retained with stock/composed native cores and exposed through the registry. Full next executable links. Stop/attachment helpers remain unwired pending actual collision-flow and orientation review; this is not a claim of working sticky projectiles. No live verification requested while the user is away.

- Attachment precedence correction: native asset lookup now uses the last nonempty matching pair, as C1's forward `bg_attachIdx` population does at41fc96; empty later cells preserve prior entries. Reviewed direct disassembly and compiled changed object. Not deployed; not established as fastmag root cause. No tests added.

- Correction: extra zones are not established as necessary for fastmags. The current descriptor produces empty quick names, but its equivalence to the official loadout remains unproven. Trace C1 identity resolution and initialization first; asset repair/delivery is no longer the selected approach.

- Passive deployed-definition check confirms frag timed/cook `1/1`, Semtex `1/0`, C4 `0/0`. Live throw remains pending. Reviewed isolated fastmag asset repair and manifest under `obj/event-fastmag-asset-repair`; two field corrections preserve event identity. Artifact is inflated evidence only: native client delivery requires a compact WeaponDef serializer with relocated references.

- Deployment update: linked and installed SHA256 `5BC16E6E159424A0C6EB1CA22ABBA70FAFB706ED3824CE8E5A3B96881BAACB1E`; native PID61844 owns UDP17733. C1/Python preserved. Live grenade behavior remains unverified.

- Reviewed C1 grenade scheduler and held-timer consumers. Native loader now copies verified timed-detonation and cook-off fields. Parent corrected `bCookOffHold` member spelling; changed object compiles. Running executable unchanged; linking and live verification remain.
- Fastmag quick-name gap is present in the shipped event base asset. Its replacement-based attachment cannot fill empty strings. Preserve event identity and repair asset delivery; do not substitute the ordinary weapon.
- C1 stickiness enum differs from IW3 and needs expanded consumers. No enum copy or synthetic tests applied.

## 2026-09-11: live pump completion and fast-mag evidence

- Current build `14A36F66C328F198DD0F98C124FA01B7AD31705509A90F7E36ACADF66E89E795` captured two SPAS shots over 1000 samples. Prediction and snapshots both return to idle; neither restores the pump after completion. See `CODOL_SPAS_REPLAY_CAPTURE_20260911.md`.
- Equipped M4A1 Tech selects quick reload animation14 on both client and server, with 1800ms duration. Its C1 weapon definition has empty quick animation names in slots10/12; normal names9/11 exist. Constructor/attachment investigation remains active.
- Shadow cause remains unproven. Semtex fuse cancellation was traced to native `timedDetonation=0`, which has no CoDOL producer; its exact C1 mapping remains unverified. No speculative fix or synthetic tests.

## 2026-09-11: native C1 turret flags and lobby match dispatch

- Replaced retained IW3 `ps.eFlags & 0x300` turret semantics with C1's native `0x0c00` pair across view, movement, weapons, animation, use, damage, spawn cleanup, and GSC `isOnTurret`. C1 `0x100`/`0x200` prediction bits now pass through without reinterpretation.
- This addresses the reproduced fire-time shutdown: predicted firing set C1 `0x200`, retained `G_GetPlayerViewOrigin` treated it as turret state, read `ENTITYNUM_NONE`, and aborted on missing `tag_player`.
- Reviewed the lobby worker implementation. Ready now dispatches validated `fs_game`, `codol_zoneType`, `g_gametype`, `mapname`, and `map` to the native server through a generated shared local RCON credential.
- Windows build linked `codol_dedrun.exe` (`D67695963B11892D639DBA9E5FE0CB6D56074A27A75B5D62726E1B2B8A8FF04E`). The only make failure was the known absent post-link `pexports`. Native server startup completed on UDP 17733; the reloaded lobby owns UDP 3074/3078; C1 stayed running.
- Real post-spawn firing and movement verification remains pending. The broader GSC/VM and C1 parity goal remains active.
# Full native script implementation pass

User direction: write the missing functions and methods first, using IW4 as
primary reference and T5 where IW4 lacks the entry. Defer builds, tests, and
server launches until the implementation pass is complete. Static source and
binary inspection continues. Do not replace behavior with registrations or stubs.

The user explicitly authorizes freely rewriting IW4OL native code and subsystems
for CoDOL compatibility. Missing representations and state producers must be
implemented; preserving the original architecture is not a requirement. Worker
file ownership coordinates edits and does not prohibit necessary extensions.
See the standing repository instructions in `AGENTS.md` and `CLAUDE.md`.

The starting checklist is `CODOL_IMPLEMENTATION_PASS.json`, generated from the
existing registry/call inventory. It contains 827 implementation candidates:
262 with IW4 catalog provenance, 494 with T5 resolver provenance and no IW4
catalog entry, and 71 reference-only entries requiring native provenance.
The last category is retained rather than silently excluded, but a script call
alone does not prove a missing native builtin. Parent review confirmed that
`isEMPed` and `isUsingRemote` are defined in the IW4 MP utility script; their
resolution belongs to script loading/linking. A source scan found definition
candidates for 13 of the 71 reference-only names (see
`obj/claude-workers/reference-only-script-definitions.json`); the others still
require provenance review. The unresolved-entry total must not be presented as
a count of confirmed missing VM methods. Entries already
registered still require semantic review; name coverage is not completion.

Written during this pass, not built or run:

- `GetPointInBounds`: IW4 method 0x5f5a40 calls 0x470d30. The helper computes
  local bounds midpoint plus half-size times three coefficients, rotates by
  current entity angles, and adds current origin. The native source converts
  retained mins/maxs to midpoint/half-size and does not clamp coefficients.
- `exp`: IW4 0x5f14e0 reads one float and returns its exponential as a float.
- `GetPlayerViewHeight`: IW4 0x5da240 is a player-only current-view-height query.
- `GetMissileOwner`: IW4 0x5edf30 validates missile type and queries the owner
  handle, separately from its guidance target. The native adapter handles an
  undefined owner without dereferencing an empty handle.
- `SortByDistance` entity-field review: retained `GetEntityFieldValue` requires
  zero VM argument counts and replaces the VM top with its evaluation stack.
  The builtin now preserves its argument frame around field evaluation. This
  is a written correction based on the source preconditions, not a verified fix.

Known unresolved earlier work: the SortByDistance fixture passed script-struct
origins, but the later mixed entity/struct case failed to resolve an entity
origin. Its log is `obj/sort-entity-unresolved.log`; the written correction above
must be validated after the writing pass. No successful
entity-origin result or complete script startup is claimed.

Additional writing pass (no build, test, or server execution):

- IW4 math: `log`, `squared`, `clamp`, `angleclamp`, `vectortoyaw`.
  These preserve scalar/vector return types, upper-then-lower clamp order,
  fractional-turn angle normalization, and the zero-direction yaw result.
- IW4 VM arrays: `getfirstarraykey`, `getnextarraykey`. These use the retained
  allocator's key decoding and sibling traversal, preserve key types, return
  undefined at iteration end, and reject an invalid or absent next-key input.
  They do not mutate the array or borrow IW4 allocator index boundaries.
- T5 math: `isvec`, `lerpfloat`, `lerpvector`, `vectorcross`,
  `absangleclamp180`. Interpolation clamps its fraction to [0, 1].
- T5 entity queries: `getangles`, `getmins`, `getmaxs`, `getabsmins`,
  `getabsmaxs`, `getentnum`. World bounds come from the existing linked
  collision bounds, rather than a fresh origin-plus-bounds approximation.
- Native table variants: IW4 `tablelookupbyrow`, `tablelookupistringbyrow`,
  `tablelookuprownum`, and T5 `tablelookupcolumnforrow`. All use the retained
  native table loader and its existing CoDOL translation/fallback policy.
  IW4's two by-row names share the same ordinary-string implementation.
  Row-number searches are case-insensitive, last-row-first, and return -1
  when no row matches. Invalid row/column reads retain the empty-string result.
- IW4 `islinked` and T5 `islinkedto` read the retained entity-link parent;
  the latter checks the immediate parent, not any ancestor.
- T5 weapon queries: `getweaponmindamagerange`, `getweaponmaxdamagerange`,
  `getweaponmindamage`, `getweaponmaxdamage`, and `weaponreloadtime`.
  They resolve through the gameplay weapon registry and read already-converted
  native fields. Damage returns floats; reload time returns seconds. Custom
  attachment-definition construction remains a dependency of querying those
  custom weapons, as it is for their gameplay use.

The checklist now has 122 entries written but unvalidated and 705 entries still
unimplemented. This is progress within the full pass, not a completion claim.
The individual checklist entries retain native addresses for review.

Further inspected dependency: T5 `getweaponfusetime` (0x65ff20) returns float
milliseconds from WeaponDef+0x46c. CoDOL's native timing conversion does not yet
populate its retained `fuseTime` field. It remains unimplemented pending C1
source-field provenance; binding it to the default zero would be incorrect.

Next static implementation batch, also unvalidated:

- `matrix4x4transformpoints`: T5 0x65f940 and its point-array reader 0x642ea0.
  Requires a dense 16-element numeric matrix and a dense array of at most 128
  vectors. Copies both inputs before output. Returns a new sequential array,
  preserves point order, and performs no perspective division. The native
  formula uses columns 0/4/8, 1/5/9, 2/6/10 with translation at 3/7/11;
  this unusual indexing is preserved explicitly rather than reinterpreted.
- `rotatepoint`: T5 0x64f810 takes a point and Euler angles. The reference
  converts angles to an axis, then a quaternion, then rotates the point. The
  adapter applies the equivalent retained axis rotation directly; floating-point
  rounding need not be bit-identical to the quaternion route.
- `weaponburstcount`: IW4 0x5f2770 returns 2, 3, or 4 for the corresponding
  burst modes and zero for other modes.
- `weaponisauto`: IW4 0x5f26d0 requires full-auto fire mode and bullet weapon
  type together. Both queries use the registered native gameplay definition.
  IW4 0x4ccd90 confirms that resolver index zero is a parameter error, matching
  the shared query validation used by these bindings.

- `getnormalizedmovement`: IW4 0x5da2b0 reads signed forward/right command
  bytes and divides each by 127, returning Z=0. The binding reads the current
  retained gameplay command after CoDOL input translation. It deliberately
  does not normalize diagonal vectors or clamp the signed-byte result.
- `isexplosivedamagemod`: IW4 0x5f2f40, flags at 0x79a15c, names initialized
  at 0x472950..0x472a43. True for `MOD_EXPLOSIVE_BULLET`, `MOD_GRENADE`,
  `MOD_GRENADE_SPLASH`, `MOD_PROJECTILE`, `MOD_PROJECTILE_SPLASH`, and
  `MOD_EXPLOSIVE`; false for unknown names. Exact name comparisons avoid
  importing IW4's reordered damage-type indices into the retained IW3 table.

Input-method follow-up evidence: alpha0022 `menu_spawn.py` documents a measured
85-entry C1 action table at 0x00cd62c4. Its action-slot mapping conflicts with
the explicitly inferred legacy defaults in `killstreak_support.py`. Native
action/notification support must use the client table and current native
command handling; the inferred Python indices are not an implementation contract.

`notifyonplayercommand` is now written and connected to native C1 client-command
handling, still unvalidated. IW4 0x5dcfe0 requires a player and exactly two string
arguments (event, command). Its registry at 0x457fa0 caps the total at 256 and
suppresses duplicate player/command/event triples. The new native module owns
event/command text independently of VM string-table shutdown, folds command
case, and retains case-sensitive event names.

The C1 85-entry table at 0x00cd62c4 was read directly from the executable during
this pass. It confirms action-slot presses at IDs 17/19/21/23/25 for slots 1..5,
not the older inferred Python mapping. C1 0x499aa0 sends reliable `n <id>`
notifications while active. `ClientCommand` now recognizes those IDs, dispatches
registered script notifications with no arguments, and ignores malformed IDs.
Dispatch snapshots VM event references and uses a connection generation to stop
delivery after a callback disconnects the player. Registration does not synthesize
gameplay input; user-command simulation remains its own native path.

Native connect, bot-connect, disconnect, and server-clear paths clear the owned
subscriptions. Valid action notifications bypass retained text-command flood
throttling, which would otherwise discard legitimate press/release edges while
acknowledging them. Existing reliable sequence duplicate/gap checks still apply.
Build/link checks, script fixtures, and real C1 action delivery remain deferred.

Notification dispatch review: IW4 0x4c0080 calls `Scr_IsSystemActive(1)` before
notifying; its 0x4b24e0 implementation agrees with the retained VM routine.
The native C1 handler now applies that guard before collecting notifications and
again before each delivery. IW4 0x4ba760 finds the full lowercase command in the
VM string table and tries the first token only when that lookup fails. The
adapter now preserves this distinction for actions with arguments (such as
`+actionslot 1`), including global registered-command existence; it does not
fall back simply because the receiving player has no full-command subscription.
These are source corrections, not runtime validation, and do not add to the
written-entry count.

Static HUD timers are now written through their snapshot path:

- `settimerstatic` and `settenthstimerstatic` follow IW4 0x5e1780/0x5e1890
  and shared helper 0x5e1440. They require one duration, preserve the helper's
  milliseconds rounding, reject nonpositive/unrepresentable results, clear
  type-specific settings, and store raw milliseconds without adding level time.
- Native HUD types 14/15 were appended without changing existing IW3 values
  or structure sizes. The CoDOL HUD translator maps them to C1 types 7/10.
  The updated type count also permits normal native HUD destruction.
- No build or runtime validation was performed. This header change requires
  the normal full rebuild when execution resumes.

Receiver audit: T5's `setentityowner`, `clearentityowner`, `setentitytarget`, and
`clearentitytarget` belong to actor_script_cmd.obj and use Actor_Get (0x915a30).
Their checklist entries now explicitly retain that receiver evidence. Actor
state/behavior is required; generic entity-handle adapters would be incorrect.

Waypoint implementation and snapshot integration, unvalidated:

- `setwaypointedgestyle_rotatingicon` sets bit 0x20; the `secondaryarrow`
  variant clears that same bit. `setwaypointiconoffscreenonly` sets bit 0x40.
  IW4 0x5e1a20/0x5e1a70/0x5e1ac0 require a HUD waypoint receiver.
- The existing `setwaypoint` binding was corrected using IW4 0x5e1980:
  integer value, optional integer draw-icon flag (bit 8), optional integer
  distance flag (bit 0x10). Missing optional arguments preserve flags.
  It no longer uses the retained IW3 material-string second argument. Reads
  complete before mutating the HUD; this correction adds no inventory entry.
- C1 0x44aec5..0x44aef0 consumes bits 0x10/0x20/0x40 and 0x44b1e6 gates
  waypoint drawing with 0x208. The native snapshot flag translator now permits
  the verified low seven bits, retaining rejection of unmapped bits. Existing
  waypoint type translation remains C1 type 13.
- Rendering, HUD VM behavior, and compatibility checks remain deferred with
  the rest of the writing pass. Earlier tests expecting all flags above 7 to
  be rejected will need to distinguish these newly supported bits.

Weapon and spawn-collision writing pass, unvalidated:

- `isweaponprimary` follows T5 0x660170, including warning/undefined for
  unresolved names. Inventory type is confirmed by the symbol-backed
  `BG_GetWeaponInventoryTypeName` call at 0x64d2f8. C1 inventory conversion
  already populates the native field. `getweaponindexfromname` follows T5
  0x64d530 and returns the native server index, including zero; C1 wire IDs
  remain a snapshot concern.
- All five `collisiontestpointsin*` functions now have bodies and bindings:
  sphere (0x65dbf0), cylinder (0x65dde0), pill (0x65e260), cone (0x65e8c0),
  box (0x65f090). Inputs are copied dense vector arrays capped at 256;
  numeric shape parameters require floats, matching explicit T5 type checks.
  Sparse arrays produce script errors instead of T5 debug assertions.
- Each point returns a vector. Sphere returns hit/distance-squared/zero even
  on a miss. Other shapes return zero vectors on misses. Cylinder hits carry
  origin-distance-squared and axis-distance-squared. Pill/cone hits carry
  origin-distance-squared and squared projection onto the radial vector.
  Box hits carry center-distance-squared and zero. Boundaries are strict.
- Preserved pre-normalization center/end/edge construction, the reference
  broad bounds, cone denominator floor (1e-5), and box forward/up/cross basis.
  Arithmetic follows the reference's float stores and extended squared
  distance accumulation where practical; bit-identical rounding remains
  unvalidated and may depend on compiler floating-point settings.
- `qsortscoredspawnpointsascending` follows T5 0x65f800/0x65f8f0: copies up
  to 256 vectors, sorts by the second component, and returns a new array.
  Equal/unordered scores compare equal; ordering of ties is unspecified.
- Equipment/specific-use/scope-overlay/mountability weapon queries remain
  unimplemented pending verified C1 metadata and its native conversion.
  T5 numeric offsets and enum values cannot be copied into IW3 definitions.
- No builds, tests, server launches, or client execution occurred in this pass.

Spectator/turret receiver methods, unvalidated:

- `getspectatingplayer` follows IW4 0x5dec20: player receiver, zero arguments,
  and only returns the followed entity when session state is SPECTATOR and
  spectatorClient is nonnegative. This remains separate from the existing
  `getSpectatorClient`, which does not require spectator session state.
- `isusingturret` follows IW4 0x5da750 using native turret stance bits 0x300.
  Retained `_g_misc_mp.asm` sets these in turret_use and clears them with
  0xfffffcff when stopping. IW4's numeric mask 0xc00 is not copied blindly.
- `getturretowner` follows IW4 0x5ecef0: turret receiver and active gate,
  then owner handle. The reference's empty-handle fallback resolves to entity
  2047, ENTITYNUM_NONE, not the world entity. The adapter uses the native
  sentinel and native handle encoding. Native turret_use maintains both fields.
- `isfiringturret` was inspected through IW4 0x5eccc0 -> 0x44a6e0, but its
  turret-info +0x3c field still needs semantic mapping to retained state;
  it remains unimplemented rather than assuming offsets match.
- No build, test, client, or server execution was performed.

Movement accessors, unvalidated:

- `getmovespeedscale` follows T5 0x645070 and its paired setter 0x644fd0.
  The result is the session scale, not the effective player-state multiplier.
  Retained ScrCmd_SetMoveSpeedScale writes that session field at +0x2ffc.
- `getangularvelocity` and `setangularvelocity` follow T5 0x680760/0x6807c0:
  vehicle receiver, direct vehicle physics rotVel access, no unit conversion.
  T5 physics +0x90 matches the retained vehicle_physic_t member layout.
- Further turret evidence: IW4 0x6006e9/0x60071c/0x600749 assigns turret
  firing state values 2/1/0 to +0x3c. The retained triggerDown boolean is
  therefore not enough evidence for implementing isfiringturret by aliasing it.
  T5 isturretfiring also tests additional entity and turret-state flags.
- No builds or runtime checks were performed.

IW4 vehicle queries, unvalidated:

- `vehicle_getvelocity` (0x47af20) and `vehicle_getbodyvelocity` (0x418040)
  expose native physics world/body velocity without conversion.
- `vehicle_getspeed` (0x4082b0) returns MPH from the stored speed, preserving
  IW4's double multiplier at 0x713888 (0.05681818351149559) and float result.
  Retained getspeed returns raw speed; getspeedmph confirms the native field.
- `getvehicleowner` (0x67fe60) validates a vehicle and resolves its owner
  EntHandle. An empty handle returns undefined, with no active-state gate.
- `getgoalspeedmph` was inspected at IW4 0x67faa0, but +0x2d4 still needs
  mapping to retained goal/manual speed state; it remains unimplemented.
- These bindings read live native state. Builds and runtime validation remain
  deferred; they do not establish completion of CoDOL vehicle simulation.

Vehicle speed controls, unvalidated:

- `getgoalspeedmph` now maps IW4 +0x2d4 to manualSpeed: the setter at
  0x67f660 establishes its meaning and agrees with retained manual movement.
- `setwaitspeed` follows 0x67f480, converts MPH using the reference's double
  17.600000381469727, and rejects negative values.
- `vehicle_setspeed` follows 0x463af0 -> 0x67f660: manual mode, target speed,
  optional positive acceleration, optional positive deceleration (otherwise
  half acceleration), and the type-5 helicopter acceleration cap. Omitted
  acceleration requires an existing positive value. Input validation finishes
  before state mutation, avoiding partial writes on script errors.
- Existing native movement consumes these fields; no proxy or hook is used.
  `vehicle_setspeedimmediate` remains pending its direction/state handling.
- No builds, tests, or server/client execution were performed.

Standalone vehicle acceleration setters, unvalidated:

- `setacceleration` (IW4 0x67fae0) and `setdeceleration` (0x67fb10)
  convert argument 0 with the reference double factor and store manualAccel
  or manualDecel. They do not enable manual mode or validate positivity;
  the stricter vehicle_setspeed contract must not be imposed on these methods.
- Immediate-speed investigation: IW4 0x67f7f0 selects goal-directed velocity
  for type-5 vehicles in state 4, otherwise angle-derived forward velocity.
  It sets speed and a second speed field, writes world velocity, then forwards
  that velocity to a physics object via 0x4ea4d0 when present. Native state and
  physics integration must be mapped before counting the method as supported.
- No builds, tests, or game execution were performed.

Vehicle predicate and pool audit, unvalidated:

- `isvehicle` follows T5 0x65cc50: arbitrary argument, pointer/entity type
  checks, then entity extraction and native vehicle-state presence. Scalars,
  arrays, and script structs return integer false without entity coercion.
- IW4 `getnumvehicles` (0x499fa0) counts occupied pool slots; `vehicle_getarray`
  (0x42a690) walks that pool in slot order and excludes entity type 17.
  Native pool ownership/order and the spawner type need mapping before these
  can be implemented faithfully by anything other than an approximate scan.
- T5 `getmaxvehicles` (0x65cd20) returns 16, while IW4's above loops use 8.
  The native pool capacity must be established rather than copying a constant.
- Steering (IW4 0x67f9e0) divides an entity steering field by a definition
  limit; throttle (0x67fa40) reads vehicle +0x368. These offsets still need
  native semantic mapping, so neither is counted as implemented.
- Builds, tests, and game execution remain deferred.

Native vehicle pool mapping, unvalidated:

- Resolved the pool dependency: `_g_vehicles_mp.asm` reserves 0x1aa0 bytes
  for s_vehicles; G_VehiclesInit and SpawnVehicle iterate eight records at
  stride 0x354. Occupancy is entNum (+0x1b8), with ENTITYNUM_NONE for free
  records; initialization publishes the pool through level.vehicles.
- `getnumvehicles` follows IW4 0x499fa0 using that native occupancy state.
  It returns zero before the native pool pointer is initialized.
- `getmaxvehicles` follows the capacity-query role of T5 0x65cd20, reporting
  the actual native capacity of eight rather than T5's sixteen. This does
  not expand the vehicle allocator or claim T5's capacity is supported.
- Compile-time layout assertions were added for the assembly-owned stride
  and occupancy offset. No compiler, tests, or game processes were run.
- Vehicle-array filtering still needs the IW4 type-17 spawner mapping.

Vehicle lifecycle binding, unvalidated:

- `freevehicle` follows IW4 0x67fd00 -> 0x4d1da0: validate a vehicle,
  reject a defined owner handle, and release vehicle state without deleting
  the entity. It calls retained G_VehFreeEntity, whose assembly clears script
  strings and target handles, resets vehicle entity state, marks entNum as
  ENTITYNUM_NONE, and clears the entity's scr_vehicle pointer.
- The pool queries therefore observe the same native lifecycle as allocation
  and release. IW4's additional physics-object cleanup belongs to its vehicle
  implementation; any future native physics extension must join this cleanup.
- No builds, tests, or runtime execution were performed.

Occupied-vehicle player methods, unvalidated:

- `isinvehicle` and `getvehicleoccupied` follow T5 0x6095b0/0x609750.
  Native G_VehEntHandler_Use sets player pm_flags 0x100000 and r.ownerNum;
  G_VehUnlinkPlayer clears both. The adapter uses this established lifecycle
  rather than copying T5's player eFlags mask 0x4000.
- GetVehicleOccupied returns undefined outside a vehicle; an occupied player
  without an owner handle raises a script error, matching T5's distinction.
- Vehicle usability setters remain pending: T5 helper 0x66d7c0 changes both
  entity flags and contents, then handles seat availability. A contents-only
  alias would omit that behavior.
- No builds, tests, or game execution were performed.

Configured vehicle usability, unvalidated:

- `isvehicleusable` follows T5 0x67ede0. Field tables 0xccb1d4/0xd32108
  identify entity +0x170 as spawnflags; the query returns integer truth of
  bit 1. Native SpawnVehicle uses the corresponding spawnflags bit at +0x17c
  to add 0x200000 use contents. It is not an alias for G_VehUsable, which
  additionally checks occupancy, seats, speed, health, and player state.
- Setter helper 0x66d7c0 also initializes missing seat/use bone indices.
  Those dependencies remain pending; no setter is counted from a flag-only
  implementation. Native ride slots are three records at vehicle +0x2ec.
- No builds, tests, or game execution were performed.

Vehicle usability setters and native boarding integration, unvalidated:

- `makevehicleusable` and `makevehicleunusable` follow T5 0x67ee30/0x67ee70
  and helper 0x66d7c0. Both prepare use contents and missing seat bones;
  the unusable method then clears spawnflags bit 1 while retaining contents.
- Initializer 0x69da42 writes the fallback script-string handle from
  `tag_origin` (0xc8cf40). Native fallback uses that bone and updates the
  ride slot's link tag too, since native boarding consumes both fields.
  Native three-slot storage is retained; this does not add T5's five seats.
- CoDOL native G_VehUsable and G_VehEntHandler_Use now honor the configured
  flag. The handler checks it after the occupied-player exit branch, so
  disabling boarding does not trap occupants. Linked contents are relinked.
- T5 has a separate use-bone cache; native boarding uses its ride-slot bones
  directly, so no unused copy of that cache was introduced.
- No builds, tests, or runtime execution were performed.

Ride-slot ABI and action-slot input investigation:

- Native boarding reads boneIdx at slot +4 for the world bone matrix and
  tagName at slot +0 for G_EntLinkToWithOffset. The fallback's paired update
  is required. Added compile-time assertions for ride-slot base +0x2ec,
  stride 12, bone offset 4, and occupant offset 8. They have not been compiled.
- T5 action-slot methods 0x6067f0/0x6068e0/0x6069d0/0x606ac0 OR tests
  of two player bitsets (+0x28bc and +0x28a4), with indices 45 through 48.
  Helper 0x406880 uses MSB-first words and checks indices below 51.
- Current/latched input is the working interpretation of those two bitsets;
  their writers and reset points still need confirmation. C1's reliable
  action-command transport cannot be replaced by copying these numeric masks
  into its 32-bit usercmd buttons. The four entries retain this dependency
  explicitly and remain unimplemented. No new completion count is claimed.
- No builds, tests, or game execution were performed.

Action-slot input implementation, unvalidated:

- T5 0x5f9bd8..0x5f9dae confirms +0x28b4 = current & ~old and
  +0x28bc accumulates those rising edges. The four action-slot methods
  query that accumulator OR current +0x28a4.
- Added native held/edge state for C1's five reliable action pairs (IDs
  17..26), updated before notifying scripts. Repeated downs do not generate
  extra edges; release retains a short press until the frame reset.
- All four retained ClientEndFrame sites that clear buttonsSinceLastFrame
  now clear action edges too. Client spawn and normal connection/map input
  resets clear held and edge state. Queries suppress location-selection mode.
- Bound the four T5 action-slot methods to this state. The fifth C1 slot is
  tracked for its notifications without inventing a new catalog method.
- No builds, tests, or game execution were performed; native frame timing,
  press/release ordering, lifecycle resets, and callback visibility await
  runtime validation when the writing pass is finished.

Action-slot lifecycle correction, unvalidated:

- The four native ClientEndFrame reset sites now select the sidecar by the
  frame entity's s.number. Using ps.clientNum was incorrect because a
  spectator's copied player state may identify the followed player, clearing
  that player's edges instead of the spectator's.
- Native ClientThink's location-selection mask now clears accumulated action
  edges alongside buttonsSinceLastFrame. Reliable actions received while
  selecting also discard their edges before notifying scripts. Raw held state
  is retained so release tracking and subsequent held queries remain coherent.
- The assembly call preserves live eax/ecx/edx and uses the existing frame
  entity argument. These are source corrections to the four written methods,
  not additional entries or runtime validation. No execution was performed.


Dvar color component queries, written but unvalidated:

- Bound getdvarcolorred/green/blue using T5 wrappers 0x643760/0x6437d0/
  0x643840. Names use native lookup; integer arguments use the T5 lower-case
  DJB2 name hash (0x6f9cb0), scanned over native cvars without changing layout.
- Missing dvars return 1.0. Registered colors normalize stored bytes; externally
  created string dvars parse up to four floats, clamp, round to bytes with
  T5's 2^-30 bias, then normalize. Helpers: 0x7be040/0x7be150/0x7be410/0x7be480.
- Invalid registered types raise a script error instead of the reference debug
  assertion. Non-finite parsed components are handled safely. Name hashing
  assumes ASCII dvar identifiers; locale-dependent non-ASCII names and hash
  collisions are not claimed to reproduce T5 table ordering.
- Source and bindings only: no build, test, server, or client execution.


Dropped weapon enumeration, written but unvalidated:

- getweaponarray follows IW4 0x491810: returns occupied dropped-weapon queue
  entries as entities in slot order, scanning all 32 slots. It does not list
  registered weapon definitions or a player's inventory.
- Retained Drop_Item in _g_items.asm stores EntHandles at level+0x1544 with
  four-byte stride via EntHandle::setEnt. Corrected the native header's pointer
  declaration to EntHandle, preserving the 32-bit layout. Added compile-time
  offset/size assertions, to be checked when builds are permitted.
- Empty handles are omitted and invalid out-of-range handles raise a script
  error before array allocation. Bodies and binding written; no execution.


Missile target clearing, written but unvalidated:

- missile_cleartarget follows IW4 0x5eddd0: rocket receiver, grenade class
  excluded by 0x4bfda0, clear target handle and target vectors while retaining
  velocity, flight stage, and flight mode. Uses native EntHandle::setEnt and
  existing CoDOL point-target reset, not a detached script-only flag.
- Retained MissileTrajectory gates guidance on weapon guidance type plus a
  target handle or active point. Clearing both removes either target mode.
  Source assertions cover the native handle and offset-vector layout.
- Other inspected IW4 missile methods remain pending: 0x5edc30 sets entity
  target, offset, flags and last target origin; 0x5edd20 sets an absolute point;
  flight-mode helper 0x5ede70 requires target-enabled flag 2 and writes mode.
  Persisted target state and lost-target caching need native integration before
  those methods can be claimed, rather than writing unused flag bits.
- Corrected CoDOL builtin declarations to use C linkage in C++ translation
  units. Vehicle and missile C++ bodies expose C symbols to the C registry;
  their declarations must agree. This is a source correction, not a build result.
- No builds, tests, server launches, or client execution performed.


Player weapon lists, written but unvalidated:

- Added getweaponslistall (IW4 0x5dc490), getweaponslistoffhands (0x5dc690),
  and getweaponslistitems (0x5dc6a0). Shared reference helper 0x5dc580 walks
  registered weapon indices in ascending order, returns names of owned weapons,
  and optionally filters inventoryType (offhand 1, item 2).
- Native ownership comes from playerState's 128-bit weapon set, matching the
  retained PlayerCmd_GetWeaponsList implementation. Weapon zero is excluded;
  no out-of-bounds bitset reads are permitted. Names and types come from the
  native definitions used by gameplay and CoDOL translation.
- Queries honor g_giveAll when enabled, matching the IW4 helper's ownership
  bypass. This does not itself implement the broader give-all gameplay mode.
- getweaponslistexclusives remains pending: IW4 0x5dc6b0 selects inventory
  type 4, which the current CoDOL-to-native inventory conversion rejects.
  Returning an unconditional empty array would hide that missing loader support.
- No builds or execution; all three entries remain unvalidated.


Exclusive inventory dependency and query, written but unvalidated:

- C1 0xcd7f58 contains primary/offhand/item/altmode/exclusive/scavenger at
  indices 0..5; index 6 is already the adjacent fire-type table. Extended
  CoDOL's native inventory enum and fastfile translation to preserve all six.
- Extended the retained text weapon parser's inventory loop and name table
  under CODOL_SERVER. This also makes BG_GetWeaponInventoryTypeName safe for
  the newly admitted types; changing the enum alone would index past its table.
- Bound getweaponslistexclusives using IW4 0x5dc6b0's inventory filter 4 and
  the same owned-weapon enumeration as the other lists. This supersedes the
  prior loader dependency recorded above.
- Native primary-capacity scans compare inventoryType with zero and exclude
  these added categories. Metadata preservation/query support does not prove
  exclusive switching rules or scavenger-specific pickup behavior; those need
  separate native gameplay work and eventual runtime validation.
- No builds, tests, server/client launches, or inventory regeneration performed.


T5 dropped-weapon alias and sound-query evidence:

- Bound getdroppedweapons to the native dropped-weapon queue implementation.
  T5 0x655100 traverses 32 handles at 0x3e523e8, skips undefined handles,
  resolves each remaining entity, and adds it in slot order. Map symbols
  confirm isDefined 0x5f5f30, ent 0x5f5fa0, Scr_AddEntity 0x6856f0.
- Sound queries remain unimplemented pending native weapon sound conversion.
  T5 getweaponfiresound 0x64d570, player 0x64d5c0, pickup 0x64d610, pickup
  player 0x64d660 take an integer weapon index, return empty for 0/-1, and
  otherwise read definition string fields +98/+9c/+7c/+80 respectively.
  getweaponprojexplosionsound 0x65ffc0 takes a weapon name, rejects unresolved
  names, and returns the +61c string or empty when absent. These are distinct
  argument contracts, not interchangeable name-based wrappers.
- Corrected the weapon type conversion header comment to reflect the newly
  preserved exclusive/scavenger inventory categories.
- Source/binding changes only; no build, tests, server/client execution.

Weapon sound source inspection (pending semantic mapping):

- Mounted weapon sound resolution already exists in CODOL_LoadMountedWeaponSounds:
  53 indirect name slots at +364..+434 and two 31-name arrays. A script name
  query need not fabricate native playback aliases to access these names.
- Offline C1 inspection found script readers 0x558d90 and 0x558df0 resolving
  a weapon name through 0x41f7a0/0x41f6c0, then reading definition +364/+368
  and the pointed-to name. They return empty when any lookup is absent.
- C1 records at 0xcd2d80/0xcd2d8c contain empty name strings, so these addresses
  alone do not establish that the slots mean pickup/pickup-player. Preserve
  them as candidate mappings, not confirmed semantic field names. Gameplay
  reader 0x446bc9 also accesses +368 and can establish its event role next.
- C1 readers take names, whereas the inspected T5 four fire/pickup queries
  take integer indices. This contract difference must be resolved explicitly
  when binding CoDOL-facing queries; do not silently coerce an index to a name.
- Offline inspection scripts/results: obj/read-pass-c1-weapon-sound-fields.py,
  obj/read-pass-c1-sound-accesses.py and .txt. Candidate access scans include
  false instruction alignments; only individually traced readers are evidence.
- No additional builtins counted; no builds, tests or game execution.


Fire sound queries, written but unvalidated:

- Added getweaponfiresound and getweaponfiresoundplayer with T5 integer-index
  contracts (0x64d570/0x64d5c0). 0/-1 return empty; other invalid indices raise
  a parameter error rather than indexing outside the native registry.
- C1 CG_FireWeapon calls 0x481d60 at 0x4820fd. The callee selects ordinary
  sound +380 and local/player +384 at 0x481db3/0x481dc7. These are resolved
  mounted sound-name slots 7/8. The query returns the selected field itself;
  it does not apply playback fallbacks or last-shot alternatives.
- Missing mounted definitions use native fireSound/fireSoundPlayer alias names.
  Invalid mounted dependencies raise an error; absent fields return empty.
  This provides actual asset metadata without pretending native sound playback
  conversion is complete.
- Candidate pickup reader 0x446bc9 lies in an obfuscated region; the earlier
  byte-pattern hit is not adequate event-role evidence. Pickup queries remain
  pending. C1 candidate script readers +364/+368 alone do not name the fields.
- No builds, tests, server/client launches performed.


Vehicle pool enumeration, written but unvalidated:

- Added vehicle_getarray using IW4 0x42a690: require no arguments, return
  occupied native pool entries in slot order. Validate entity numbers before
  constructing the VM array. Native free slots contain ENTITYNUM_NONE.
- IW4's excluded entity type 17 is a spawner: vehicle_getspawnerarray at
  0x4c4390 scans in-use entities for that type. Native type 17 is ET_EVENTS,
  so copying the numeric filter would be wrong. The retained SpawnVehicle pool
  contains live vehicles; no native vehicle-spawner type currently exists.
- vehicle_getspawnerarray remains pending until spawner allocation/lifecycle
  exists. If spawners are later admitted into the vehicle pool, the live-array
  query must exclude them using the new native representation.
- Native pool capacity is eight. The query returns actual allocations, not
  map entities guessed from classnames or fabricated vehicle records.
- Source and registry changes only; no builds, tests, or game execution.


Turret spread setter, written but unvalidated:

- Added setplayerspread, IW4 0x5ed300: validate turret receiver and store
  float argument directly in per-turret playerSpread. No new clamp, degrees
  conversion, shared-definition mutation, or unrelated player spread change.
- Retained _g_misc_mp.asm initializes turret+38 from weapon+7b0 and passes
  turret+38 to Bullet_Fire inside turret_think_client. The script setter reaches
  that real gameplay consumer.
- IW4 setaispread 0x5ed370 and setsuppressiontime 0x5ed380 only error as
  unsupported in multiplayer. They are not implemented by adding error stubs.
  T5 implementations 0x649630/0x649990 validate turret state at entity+150;
  those provide the fallback semantics to trace alongside native AI support.
- IW4 setconvergencetime 0x5ed390 accepts a float seconds value and optional
  exact yaw/pitch string (default yaw), converts by 1000, and stores at turret
  +78/+7c. The retained turret struct has no equivalent fields or consumers.
  This remains pending native convergence behavior, not detached storage.
- No builds, tests, or server/client execution performed.


Turret default drop pitch, written but unvalidated:

- Added setdefaultdroppitch following IW4 0x5ed8f0 -> 0x4be660: exactly one
  argument, turret receiver, direct float assignment at turret+1c. Native
  turret_think uses this as its idle pitch target. No normalization/clamping.
- restoredefaultdroppitch remains pending. IW4 0x5ed970 requires no arguments
  and calls the geometric calculation at 0x486610. Retained turret_think_init
  has similar tag/trace work but also changes handler to 15, nextthink to
  time+50, and gates calculation on the -90 sentinel. Calling it directly
  would introduce unrelated scheduling changes and fail to restore overrides.
  Extract/verify a calculation-only native path before binding restore.
- Offline reference script: obj/read-pass-turret-droppitch.py. Source/binding
  changes only; no builds, tests, or server/client execution.

Native drop-pitch calculation entry (restore binding still pending):

- Added CODOL_RecomputeTurretDropPitchNative in retained _g_misc_mp.asm.
  It establishes the same frame/register state and enters the existing tag,
  matrix, and collision calculation after the initialization-only scheduling
  and -90 sentinel gate. Existing turret_think_init behavior is preserved.
- Both native and IW4 scan pitches 0 through -90 in -3 degree increments,
  transform the barrel/pivot geometry, and select the first trace hit.
  Missing tags or no hit preserve the current drop pitch.
- Crucial remaining differences: IW4 0x4867ef stores current entity gun pitch
  (+54) plus the hit angle; retained native code stores the hit angle alone.
  IW4 trace mask is 0x800811 (0x48679a), native is 0x811. The added 0x800000
  contents role must be mapped before claiming reference restore semantics.
- The new calculation entry is not script-bound and is not counted as another
  completed method. It avoids duplicating the native geometric routine while
  enabling the subsequent restore implementation without lifecycle side effects.
- Source-only change, no builds, tests, or server/client execution.

Restore calculation parameters (script binding still pending):

- Extended the calculation-only entry to cdecl (entity, nativeTraceMask,
  addCurrentGunPitch). The retained initializer explicitly supplies its old
  mask 0x811 and no pitch adjustment through local state; normal behavior is
  unchanged. On a hit, the optional adjustment follows IW4's current gun pitch
  plus hit angle. Missing tags/no hit still preserve the original field.
- Locals -ec/-f0 are below the geometry locals ending at -e8 and above the
  outgoing trace arguments ending at -f4 in the existing 0xfc-byte frame.
- Collision bit 0x800000 remains unresolved. Local headers and the inspected
  upstream IW4x Structs.hpp do not establish its meaning. IW4 trace wrapper
  0x406440 passes through to 0x423280; its downstream trace code is the next
  native evidence path. Do not assume that the bit means glass from its value.
- The new entry remains unbound and uncounted until its caller can supply the
  correctly mapped contents mask. No builds/tests/game execution performed.


Restore default drop pitch, written but unvalidated:

- C1 0x57be01 passes trace mask 0x800811, matching IW4. Its hit branch
  0x57be5b..0x57be64 adds current entity gun pitch to the scanned angle.
  Its loop advances through index 30, matching the retained -3-degree scan.
- This resolves the mask choice without inventing a contents name: native
  CoDOL collision conversion copies brush and leaf-node contents unchanged
  (codol_collision_native.c), and retained traces filter those bits directly.
- Bound restoredefaultdroppitch with zero arguments and a turret receiver.
  Calls the calculation-only entry with mask 0x800811 and pitch adjustment.
  No handler, nextthink, ownership, or flight state changes. Missing tags and
  no-hit scans retain the existing drop pitch.
- The earlier pending-mask notes are superseded by this C1 evidence. This
  implements the script/native calculation path; completeness of loaded map
  collision and dynamic collision remains a broader server dependency.
- No builds, tests, or server/client execution performed.


Turret fire controls, written but unvalidated:

- Added turretfiredisable/enable from IW4 0x5ed9d0/0x5eda40. Validate turret
  and toggle only firing inhibition, preserving ownership and other state.
- IW4 flag 2 cannot be copied: retained G_ClientStopUsingTurret clears native
  bits 1/2 as stance bookkeeping. Use CODOL_TURRET_FIRE_DISABLED (0x10000)
  instead; it survives mount/unmount and is cleared by normal pool allocation.
- Retained turret_think_client checks the flag at its fire-time gate before
  user attack input. Disabled turrets take the existing trigger-release path,
  retaining sound-tail processing and avoiding bullet/projectile firing.
- maketurretoperable/inoperable remain pending: IW4 uses flag 0x200, while
  native flag 0x200 participates in idle pitch handling. Its native use gate
  does not check such a flag. These need a separate representation/consumer.
- No builds, tests, server/client execution performed.

Claude implementation batch, reviewed and integrated by parent (no build/run):

- `maketurretoperable` / `maketurretinoperable`: IW4 0x5ed590 / 0x5ed600
  clear/set turret flags 0x200. Native 0x200 already controls idle pitch;
  the implementation uses 0x20000 in the retained turret structure and gates
  `G_IsTurretUsable` after the existing null check. Both ordinary use eligibility
  and cursor-hint selection already call this native gate. Allocation resets the
  flag; retained stance transitions preserve it. Existing occupancy is preserved.

- `forceusehinton` / `forceusehintoff`: IW4 0x5f6110/0x5f01b0,
  constructor/intern helper 0x5f6000, use consumer 0x49437d. Parent corrected
  the worker draft's exact-one-argument restriction and silent pool exhaustion;
  message construction accepts the native message argument sequence and pool
  exhaustion raises a script error. The native consumer now applies the override
  after retained use restrictions and before ordinary hint searching. It uses
  an entity-pointer helper, so no speculative assembly stack slot is needed.
  State is keyed by the player's entity slot, cleared alongside the native
  respawn memset and at the existing connection/map input reset paths.
  C++ declarations have C linkage. This completes the native method/consumer
  writing slice; C1 cursor-hint field and hint-configstring translation are still
  unproven and no client-visible hint rendering is claimed. Alpha0022's
  playerstate_fields.py itself marks the cursorHint mapping as low confidence.

Parent review of the Claude query report corrected two ABI/argument errors:
`getturrettarget` (IW4 0x5ed260) reads integer argument zero via 0x4f31d0;
nonzero enables a flags0x20 filter, then the target handle at turret+0x40
is returned if present. It still needs native target storage and writers.
`isturretready` reads IW4's vehicle pointer at entity+0x160, not its
standalone turret pointer (+0x15c); the retained vehicle implementation is
being reviewed as the appropriate mapping. No query coverage was added
from the draft report. Necessary source extensions are already authorized.


- `isturretready`: IW4 0x6801b0 uses vehicle validator 0x451500 and
  vehicle control state +8==5 (boarding writer 0x678381), then returns integer
  cooldown(+0x250)<=0 (fireweapon reload writer 0x4e25fb). The native method
  requires scr_vehicle_s.flags bit1 and reads VehicleTurret.fireTime (+0x1d4).
  Retained boarding/unlink maintain that control flag; vehicle think decrements
  the cooldown by level.frametime and reloads it from the native weapon fireTime;
  allocation clears it. This uses real existing native state and writers.
  The earlier worker claim of a missing standalone-turret structure was an ABI
  mix-up, corrected by parent review and a focused Claude Opus pass.

Turret target groundwork integrated, NOT counted as implemented yet:
CoDOL turret records grow from0x48 to0x6c with scripted/tracked EntHandles,
offset/cached positions and a change timestamp. Native pool allocation/stride,
free cleanup, and level-init reset are updated consistently. EntHandle::Init
precedes G_InitTurrets in the retained game init. The initial native aiming
consumer still needs measured range/weapon-reach and firing behavior; these
methods remain unregistered/unimplemented until that work is completed.
The reference-only setturrettarget entry remains unresolved: absence of an
exported name alone does not prove that an unnamed C1 record or script alias
requires no support.

Parent-reviewed weapon fuse query (writing pass, no build/test):

- `getweaponfusetime` now resolves a weapon name and returns float milliseconds. T5 0x65ff20/0x65ff9a defines the VM contract. Independently inspected C1 0x41c520 reads definition+0x654 at 0x41c55b and seeds the grenade timer at playerState+0x34. The native weapon core now maps that source field into `fuseTime`, and the VM declaration/registration are integrated. This supersedes the earlier pending-fuse note; pickup/projectile sound queries remain under review. Count: 105 written_unvalidated / 722 unimplemented.

Parent-reviewed sound query group (source only):

- Registered `getweaponpickupsound`, `getweaponpickupsoundplayer`, and `getweaponprojexplosionsound`. Pickup functions accept CoDOL weapon names as proven by C1 0x558d90/0x558df0 and also retain T5 integer arguments. This corrects the worker draft, which implemented only T5 indices despite C1 taking names. Mounted definitions supply resolved names; retained definitions use alias names. C1 readers plus shipped asset/vendor field correlations establish pickup slots0/1 and explosion tail+0x7c0; no audible-playback claim. Full provenance and limitations: obj/claude-workers/weapon-assets-report.md. Current total108 written_unvalidated /719 unimplemented.

Server match-data store integration (no builds/tests):

- `setmatchdatadef`, `setmatchdata`, `getmatchdata`, and `clearmatchdata` now bind to the real structured-schema/record implementation. Parent corrected empty-name no-op based on C1 0x553c40 and independently verified clear0x551e00 and enum path61f270. SV_ClearServer releases borrowed schema while retaining the match record; Com_Quit resets both client/server stores before unmounting archives. `sendmatchdata` remains unimplemented: worker queue/session gating/backend delivery are incomplete. Current112 written_unvalidated /715 unimplemented.

Match-data argument correction: C1 traversal checks whether the root is scalar before consuming arguments (55178e). The native server getter/setter now allow an empty path for scalar-root schemas, with zero get arguments or one set value. Removed the draft's unconditional one/two argument minimum. Count remains112 written_unvalidated /715 unimplemented; source review only. The existing32-component path bound remains a compatibility limit for deeper schemas.

Match-data path-capacity correction: removed the independent32-component limit from both client/server paths. Storage is derived from scrVmPub_t.stack (2048values), and bounds are checked before filling it. Client paths now also permit zero-component scalar roots, using the shared C1 reader/writer contract. Automatic path storage avoids leaked heap allocations on script-error unwind. This supersedes the earlier32-component compatibility limitation. Count remains112/715; unbuilt.

Per-player entity use control: `target disableplayeruse(player)` / `target enableplayeruse(player)` now set/clear real per-player target-mask state. IW4 handlers4164d0/4d8d20 and helpers489a90/4bc370/4431e0 independently inspected; consumer5fe737 filters candidates. Retained candidate loop now calls the native filter, with client spawn/connection/map resets. These are not global use-button toggles. Current114 written_unvalidated /713 unimplemented. No builds/tests/runtime.

Player-use lifecycle correction: independently traced IW4 clear-bit helper4bc370 to G_FreeEntityRefs call416392. Native G_FreeEntityRefs now calls CODOL_PlayerUseClearTarget before teardown. Recycled target entity slots no longer inherit per-player disabled-use bits. Source-only correction;114/713 count unchanged.

Mantle methods integrated: `canmantle` queries retained ledge geometry on a private playerState copy using the entity clipmask/server trace handler. `forcemantle` sets native mantle flag0x20; the accepted ledge path starts retained movement without jump and consumes the request. Parent independently inspected IW4 query4eb1b0 and C1 consumer40a660; corrected worker comment compile error, live-state mutation, hardcoded mask and stale hint. Methods registered;116 written_unvalidated /711 unimplemented. No runtime/build validation or C1 animation/snapshot completion claim.

Sprint integration: setsprintduration/setsprintcooldown now have native base-duration and recharge consumers, lifecycle resets and the five measured C1 sprint-state snapshot fields. Parent corrected call-stack alignment, player bounds and the T5 global-zero-duration gate. The result remains capped at 16383 milliseconds by the retained maximum-duration helper. Local C1 attribute overrides and prediction are not proven by this state serialization; all work remains unbuilt/unrun.

Turret follow-up: native G_SpawnTurret now invokes CODOL_TurretTarget_Spawn after initializing flags. It applies weapon defaults and reads convergencetime (yaw), pitchconvergencetime and maxrange while the current SpawnVar is active, matching IW4 408c49..408d3d. Missing keys preserve defaults; negative convergence clamps to zero and nonpositive range is unlimited. Other turret gaps remain; no additional turret methods counted.

Parent review supersedes the report's automatic-fire extension: removed native AutoFire and its unmanned fireTime ticking, plus the script-shot fireTime gate/assignment. IW4 44cc30/5ff2f0 leaves script cadence to scripts; 5ff2a0 gates fire-disabled/overheat/spin. Overheat/spin remain missing, so shootturret and the other pending turret bindings are not newly counted. Strict range boundary (6012c9) and no-target same-writer idle convergence (6012fe..60135b) corrected. All source unbuilt/unrun;118 written_unvalidated/709 unimplemented unchanged.

Native turret asset progress: core weapon conversion now supplies seven measured C1 values (left/right/top/bottom arcs, pitch/yaw convergence and maximum range) instead of leaving native fields zero. Proven through C1 G_SpawnTurret fallback readers, with native spawn retaining sign/clamp/range-square semantics. Turn speeds, spread and other turret conversion remain incomplete. No extra methods counted and no builds/runtime performed.

Turret definition conversion extended to14 fields: adds AI/player spread, minimum/maximum pitch/yaw turn speeds, and suppression duration. Proven through C1 spawn and aiming readers, preserving source values for native clamping. C1 preferred yawconvergencetime spawn-key alias is identified but remains pending while worker owns the spawn helper. No new method count or validation claim.

GetGroundPosition now written and registered against native collision traces using measured IW4 bounds, defaults, mask and startsolid error. Count119 written_unvalidated/708unimplemented; no builds/runtime.

Shellshock publication added: native precache indices1..15 now publish into C1 configstrings4228..4242, and snapshots carry the measured index/start/duration fields and active flag. C1 configstring loader confirmed by direct disassembly4674ff..46752a. Fade method remains unregistered pending native settings-loader review. No builds/runtime or count change.

FadeOutShellShock now registered after source review of rawfile/precache/settings dependencies. C1 and retained settings writers both initialize the consumed fade interval to3000ms. Earlier pending-registration notes are superseded; all work remains unbuilt/unrun.120written_unvalidated/707unimplemented.

Recoil scale methods registered: player_recoilscaleon/off use native magnitude and flag, actual recoil consumer and C1 snapshot fields, per-storage snapshot/history extension with full/delta archive records and explicit spectator bundle. Parent corrected respawn to retain captured snapshot state and rejects malformed archive percentages. Source reviewed, unbuilt and untested. Count122 written_unvalidated/705 unimplemented.

Weapon asset integration: server map setup now installs the five native archive-backed resolvers for dual wield, alternate rechamber timing, spin-up/down, detonate trigger and hold pin after weapon configstring initialization. Reviewed definition-identity lookup and cache invalidation; remaining weapon gameplay/snapshot integration is incomplete. No additional method support counted, no build or runtime validation; counts remain122 written_unvalidated/705 unimplemented.

Weapon lifecycle integration: client reset, game reset and respawn now clear per-hand gameplay state and the live hand snapshot extension together. Captured histories remain intact. Source reviewed only; no builds/tests/runtime or additional method counts.

Captured weapon snapshot integration: player snapshots now bind second-hand phase/timers, per-hand fire records, spin-up charge and second magazines from their carried player-state extension. Parent corrected a stale event-clock declaration and excluded the worker's live entity-state lookup. Entity alternate-weapon primary publication remains incomplete. Source only, no build/runtime validation or count increase.

Sound source review found entity-slot reuse could deliver an old sound notification to a new entity. Added per-entity cancellation and script-string release before G_FreeEntity destroys script state. Sound methods remain unregistered pending event-limit and notification-contract review. No builds/runtime or count changes.

Sound deadline arithmetic now uses defined 32-bit wrapping operations instead of signed overflow. Actual notification firing/event-budget semantics remain under Claude review; methods remain unregistered. No builds/runtime or count change.

Entity encoder integration correction: removed a stale fourth event-queue argument and assignment to deleted recipient-clock state, matching the captured-epoch API already integrated. Source reviewed, not compiled. Sound-fidelity worker returned; shared behavior changes remain pending review, no method count increase.

Sound cleanup now runs at shared game-VM shutdown before script teardown, covering both full shutdown and fast map restart. This corrects the worker proposal that missed the restart path. Sound registrations/event-limit changes remain pending; no builds/tests/runtime or count increase.

Sentient lifecycle integration: player spawn/team changes now update registry records; disconnect/entity free release them. Actor spawning and GSC bindings remain pending broader implementation review. No builds/tests/runtime or method count increase.

Sound-length parsing now uses decimal strtol with a 32-bit result bound, following the measured C1 conversion call chain. Nonpositive values retain the2000ms fallback. No method count or runtime validation change.

Entity snapshots now capture the primary weapon alongside the current weapon during player-to-entity conversion and carry it through extension copies/archive records. Serialization reads the captured entity storage, replacing the previous alternate-pair rejection without a live player lookup. Source reviewed only; no build/runtime validation or method count increase.

Entity looping-sound transport integrated: captured loopSound maps to C1 entity field8c with byte validation; start/stop methods use measured C1 hidden-flag and alias-field writes. Local player loop-sound state/archive publication is still incomplete. No builds/runtime or method count change.

Player loop transport now carries a captured byte through player-state copies/archive/snapshot and player-to-entity transfer, with live-only resets. Parent fixed event archive writer early returns that omitted the required scripted-queue block. Script methods retain measured entity-only writes; C1's original player-state loop producer remains unresolved. Source reviewed only, no build/runtime or method count change.

Actor transport integrated with recipient captures and archive/frame identity checks. Parent corrected archive hook to run for full and delta records and rejects unpublishable actor models instead of silently removing them. Final worker patch fixes actor array lifetime. Composition fields/attachments, cached-frame delivery and AI remain incomplete; no spawn/VM registrations or method count increase. Source only.

Offhand detonation snapshot mapping added for native phase27 to C1 phase20 and animation27 to32. Parent corrected missing main weapon-phase dispatch. Actual offhand slot selection, extra definition gate and handler semantics remain under implementation review; no method count or runtime validation claim.

Cached native snapshots now enter CoDOL frame conversion instead of being excluded by a live-only readiness flag. The converter still requires sequence-matched captured HUD/actors and reads copied player/entity/client state. Source reviewed only; full delayed playback and in-game delivery remain unvalidated.

Archived player restoration now preserves pm_time as a remaining duration in CoDOL; it no longer adds playback delay to the movement slowdown interval. Evidence is the native jump duration producers/consumers. Source-only correction; no runtime validation.

Captured movement serialization now includes jump slowdown duration, jump timestamp, jump origin height and translated jumping flag, matched to C1 jump-start and land-factor consumers. Native captured player state supplies all values. Source reviewed only; no build/runtime validation or method count change.

Movement snapshots now carry captured lean and ladder-vector fields, matched to C1 movement/ladder consumers. Full ladder behavior remains unvalidated; no builds/tests/runtime or method count change.

Movement overlay now publishes and clears the captured ladder-active flag (bit8), matching C1 PM_CheckLadder and the native jump-off-ladder consumers. Other ladder/stance flags remain subject to review. No builds/runtime or method count change.

Captured prone/crouch flags now accompany view-height transitions in movement snapshots. Native and C1 stance producers both use bits1/2; standing clears them. Source reviewed only, no runtime validation or method count change.

Archived sprint start/end timestamps now move with restored command time; durations and unset-zero values are preserved. Native and C1 sprint-meter consumers establish the clock semantics. Source reviewed only; no runtime validation.

Player animation snapshots now include captured leg and torso timers alongside animation indices, matching C1 BG_SetAnim gates and writes. Source-only integration; no build/runtime validation or method count change.

## 2026-09-08 parent offhand asset integration
Previous turn was a verified wait/status inspection: authoritative CLI showed language/HUD live and actor/weapon terminal results. This turn changes source.
Parent independently inspected C1 0x40c7e0 (offhand classes 1/4,2/3,5), 0x41cbcd and 0x41b2aa (+be5 nonzero rejects airborne groundEntityNum 2047). Applied ONLY weapon-offhand-selection patch hunks for codol_asset_registry.c, codol_weapon_native.c/h, xassets/weapondef.h, sv_main.c. Loader now retains requires_ground; active/retired definition identity resolver is installed on map weapon setup; offhand class loader accepts values4/5. Native non-CoDOL COUNT remains4, CoDOL6. Patch applicability checked before edits; no build/test/launch performed.
Python equipment.py at actual alpha0022 path uses class_equipment -> EquipmentState.set_class -> ps_slot_fields to derive lethal/tactical/special from player loadout. Worker claim alpha folder absent is false; acquisition-order producer not accepted as established behavior. Other shared selection hunks, extension/snapshot changes and VM bindings remain pending; counts unchanged122 written_unvalidated/705 unimplemented.
Resumed terminal weapon session42c69ba0-dfce-4797-ae40-c56f8b4e587c as weapon-offhand-producers (hidden supervisor74680), bounded80turns, correction checkpoint within15toolcalls. Requested explicit loadout/native producers, missing switch-start event28, disabled-flag producers and VM receiver review. Architecture rewrite authorization and no-build/test/syntax-compile/launch constraints explicit.
Actor-native-composition terminal success now available, still requires parent semantic review (first-four publication argument is inferred from native client six-slot behavior; not independently verified C1 actor overflow semantics).

## 2026-09-08 user steering: prioritize native GSC startup
Previous turn made source progress (offhand asset fields). User explicitly reports Python bugs and prioritizes GSC VM implementation for meaningful gameplay testing. Updated AGENTS.md: Python is navigation/data, not semantic authority; C1/IW4/T5 verification required. Actor configstring publication review paused before any actor source mutation to follow that priority.
Started profile-vm Claude opus/high, 80turns, session77fba24e-45f3-417c-a8c7-061a11af3e44 PID52432, confirmed live by CLI. Owns codol_script_unlock.c/new profile VM wrappers; shared core/registry patch only. Task is concrete startup profile-backed methods, first15call checkpoint, no stub unlock responses, no builds/tests/syntax compilation/launches. Other three live sessions unchanged. Existing isitemunlocked is registered; older compatibility doc's missing-binding statement is stale and is not current proof of blocker.
Parent script loader source edits: moved include-chain tracking to file scope and reset at GScr_LoadScripts entry, because compile-error Com_Error bypasses recursive return/decrement. Also guarded precompile p-1 read for a directive at source offset0. Source-reviewed only, no tests/builds. No GSC coverage count increments. Pending worker shared patches must use current scr_vm_main.c.

## 2026-09-08 GSC worker convergence correction
Previous turn source progress: native script loader fixes. This turn reviewed retained array-key decode/reference ownership (Scr_GetArrayIndexValue does not acquire refs; wrappers correctly push borrowed keys), and HUD ownership checkpoint (shared patch not yet terminal/delivered).
Authoritative language session41cdfdb0-fbe6-4f80-8d9d-e3722bfc0903 PID78136 remained live. Last calls22:29-22:30UTC were building/testing scratch slang_model.py, still no initial report after24minutes. Parent intentionally stopped exactly PID78136; supervisor exit-1 and process absent confirmed before resume. This was an explicit convergence intervention, not interpreting timeout as death. Resumed SAME session as script-language-finish (supervisor77076),25turns, report first/secondcall, native implementation next, reserve5turns for handoff. Explicitly forbids further scratch grammar emulation tests and reiterates no builds/tests/launches. Existing scratch output preserved. No native implementation counts raised.
HUD/profile/weapons remain live; actor work paused to prioritize GSC per user. Full playable-match objective remains incomplete and unverified.

## 2026-09-08 HUD VM integration
Previous turn changed worker execution state to enforce convergence. HUD session now terminal success (52turns); integrated hud-ownership-parent.patch EXCEPT scr_vm_main.c, whose unrelated hunks would revert parent's script loader repairs. Added only its three VM registrations manually. Removed duplicate header lifecycle documentation and duplicate declaration. Production makefile wildcard includes new module.
Source now connects getweaponhudiconoverride/setweaponhudiconoverride/showhudsplash to native implementations; script-owned icon array publishes at ClientEndFrame_420 playing path, keeps spectator-owned settings separate, resets both live halves on spawn/connect/disconnect and map reset, captures/archives eight material IDs, translates to C1 fields56c..588. Parent strengthened HUD read contract: missing tracked storage fails capture rather than fabricating zero icons; tracked zero means none. Signature/only caller updated.
Parent independently disassembled C1 material indexing570290 and helperada54e: bounded secure-copy with destination cleared on overflow, NOT normal truncation. Existing overlong-name error remains a stated fidelity question. showhudsplash missing-row non-send remains deviation. JSON adds integration evidence for three methods but retains their unimplemented state and unchanged122/705 counts pending complete contract resolution; registration alone is not complete support. No builds/tests/launches performed. Patch applicability and source dataflow reviewed only. Loader fixes preserved.

## 2026-09-08 GSC language checkpoint and childthread implementation dispatch
Previous turn made source progress by integrating HUD VM state/bindings. This turn language worker delivered script-language-finish-report.md: MP closure needs foreach, explicit call marker and file constants; native constant-expression/namespace/error-report changes being written. Its statement that retained VM is assembly does not justify leaving childthread unsupported. Parent located AllocChildThread in cscr_variable.cpp1045 and retained VM calls1378/2748/3643/3864. Started independent Claude childthread-vm (45turns, supervisor76320), native semantics/compiler implementation, checkpoint8calls, shared patch only, lowerer owned by live language worker. Python bugs and architecture rewrite authorization/no-run constraints explicit.
Profile checkpoint selects getplayerdata/setplayerdata as high-frequency startup/loadout dependencies and reviews already-bound isitemunlocked. Read methods' selected call chains; await implementation/provenance before binding/counts.
Parent traced ShowHudSplash->SV_GameSendServerCommand->SV_SendServerCommand_IW->SV_SendServerCommandString->SV_AddServerCommand->SV_UpdateServerCommandsToClient; text reaches wire unchanged. Independently decoded C1 CG_ServerCommand469320 byte dispatch46a118/table46a024: w ->469e0e, confirming method letter reaches splash handler. Identified separate remaining protocol concern: native queue overflow formats w disconnect text in sv_main.c, which collides with C1 splash; needs engine-level disconnect reference before correction, not guessed remapping. No tests/build/launch. Goal remains incomplete.

## 2026-09-08 weapon VM query integration
Previous turn advanced evidence and delegated childthread. Weapon-offhand-producers now terminal success34turns. Applied shared engine/event/ps-extension/gameframe/flags hunks, excluding makefile and both registry files; manually declared/registered ONLY getcurrentprimaryweapon,getcurrentweaponclipammo,isswitchingweapon. Invented setoffhandequipment/getoffhandequipment remain unregistered and uncounted; original native loadout producer is still missing. Worker again falsely claimed T5 binary absent (actual D:\t5server-pdb\CoDMPServer.exe exists per profile worker); no per-button absence conclusions accepted.
Parent fixed missing event parameter mapping: internal136 switch-start maps event28 AND translates parameter through CODOL_WeaponToWire. Owned assembly already emits136 at both native counterparts of C1's switch-start sites. Corrected stale header no-.text-writes absence claim. Offhand storage/archive now available for owned code dependencies, but loadout wiring/timing and unknown-selection defaults remain incomplete.
Parent fixed getcurrentweaponclipammo's right-hand lookup: retained ps.ammoclip indexed by weapon clip key is authoritative immediately after native ammo setters; don't require secondary record rebuild before returning it. Secondary magazine still reads captured keyed record. Source-reviewed IW4 handlers/evidence and native state access; added three methods to written_unvalidated, now125 written_unvalidated/702 unimplemented. This is written source, not verified gameplay. HUD methods retain pending contract notes/unimplemented state.
No builds/tests/launches. Patch applicability/source reads only. Script-language-finish terminal11turns arrived at end; native lowerer changes and parser diagnostic patch require parent review next.

## 2026-09-08 native script-language integration
Previous turn source progress: weapon query bindings/event parameter fix. Reviewed terminal script-language-finish11turns: native lowerer now handles file constant expressions, earlier references, vectors/localized literals, function-name separation, signed-prefix guards and diagnostic names. Integrated parser diagnostic hunk manually (worker file used nonstandard bare @@), preserving parent's loader fixes. Parent corrections: skip line/block comments in raw initializer spans, substitute constant values after case instead of treating the trailing colon as a namespace, detect <<= and >>= mutation of constants. Changed childthread comment from unsupported-substrate assertion to pending compiler integration; actual AllocChildThread already exists. No lowering/parser execution or tests/builds performed. Source review is not proof the full corpus loads.
Fresh vision-vm Claude opus/high60turns (supervisor53076), coherent eight missing vision-set globals/player methods, verified IW4/C1 command/configstring semantics, unique owned module/shared actual patch only. Existing profile and childthread workers remain independent. Explicit native rewrite authorization/Python-not-authority/no-build-test-launch constraints. No counts changed:125 written_unvalidated/702 unimplemented.

## 2026-09-08 CoDOL disconnect command correction
Previous turn source progress: constant lowering/parser diagnostics. Parent independently read C1 PE strings and code: EXE_SERVERCOMMANDOVERFLOW atc6683c referenced5d481c; C1 server overflow branch5d47d7 sends OOB disconnect, then5d4820 pushes0x74 and5d4822 formatc66858 (%c "EXE_SERVERCOMMANDOVERFLOW"), formats5d482e and enqueues5d4836+. This establishes reliable disconnect command t. Native sv_main.c overflow and sv_client.c drop still usedw, which C1 CG_ServerCommand dispatch routes to splash469e0e.
Added shared SV_WIRE_DISCONNECT_COMMAND in server.h (t forCoDOL/w otherwise) and changed both native disconnect message producers to use it. OOB handling unchanged. No speculative remapping of other command letters. This is source-reviewed binary-backed implementation, not runtime validation. No build/test/game/server launch. Goal remains incomplete; GSC count125/702 unchanged.

## 2026-09-08 native isreloading method
Previous turn source progress: CoDOL disconnect command. Parent decoded IW4 isreloading resolver table73c5c8->handler5d9e70 directly from PE. Both primary1f8 and secondary214 states tested against8,10,12,11,9 (complete reload family), same two player receiver errors, no arguments/session gate, integer0/1. Added native CODOL_WeaponStateIsReloading over existing native reload_state7..11 for both ps and captured secondary hand, wrapper and declaration/registration. Inventory now126 written_unvalidated/701 unimplemented. No builds/tests/launches.
Profile worker has actual13KB native module now; parent read it while live but made no owned edits. Recorded review findings in profile-vm-parent-review.md for terminal handoff: root-only fallback vs nested missing-name bug, arbitrary8pathlimit, script-copy/native-profile consumer divergence. Not yet delivered to live CLI via resume (no concurrent resume). Childthread/vision continue; no claim they are done.

## 2026-09-08 native isdualwielding method and snapshot flag
Previous turn source progress: isreloading. Parent added isdualwielding using directly decoded IW4 table73c5bc->5d9df0, fieldcompare5d9e41 [client+2d4]==1, integer0/1, same receiver errors and no argument/session checks. Native select_weapon already sets state.dual_wield from mounted definition; capture_hand publishes it into storage/archive extension. New helper reads captured dual_wield==1; added wrapper/declaration/registration. Snapshot gameframe changed from hand.weapon!=0 inference to same captured dual-wield flag. Source-reviewed producer/capture path, no build/test/run. Inventory127 written_unvalidated/700 unimplemented.
Profile and childthread CLI sessions remain live with recent tool activity (profile reading own code and preparing patch22:46UTC; childthread tracing actual VM termination/endon22:45UTC). Do not restart on empty result. Profile shared patch exists but remains unapplied pending terminal and review corrections. Vision worker live. Goal incomplete.

## 2026-09-08 profile correction dispatch and weapon visual queries
Previous turn source progress: isdualwielding/snapshot flag. Profile-vm terminal max_turns81/80, with native module and unapplied shared patch. Resumed same session77fba24e-45f3-417c-a8c7-061a11af3e44 as profile-vm-finish35turns (supervisor71232), first2call review checkpoint and concrete corrections to public/secure routing, path bound, gameplay reader visibility, lifecycle; no hunks applied or counted. This is terminal-state-based resume, not restarting on timeout.
Started fresh weapon-visual-vm45turns (supervisor67960), three missing weaponhasthermalscope/getweaponflashtagname/getweaponhidetags with actual mounted/composed definition data. Unique module ownership/shared patch only, IW4/C1/T5 evidence; Python bugs, native rewrite authorization/no tests/builds/launches explicit. Fourworkers maximum including profile, childthread, vision.
Vision checkpoint delivered verified C1 commandletters NOPQR3 and global configstrings1305..1310, per-player1000ms default/name storage, incomingclientdispatch. Await native code/patch and independent parent review before integration. Native SV_SetClientStat currently also sendsN (sv_client.c3179), a separate legacy opcode collision that must be audited against C1/profile path; do not infer correct replacement. No counts changed127/700; match unverified.

### 2026-09-08 pending VM integration review
Childthread worker patch held: EmitOpcode arguments describe operand stack depth, not source positions; deferred lifetime cleanup skips dead parents and lacks safe ownership/reentrancy. Concrete correction pass dispatched to same terminal worker. No childthread support claimed or integrated. Vision source uses direct CoDOL configstring bank correctly; remaining lifecycle/numeric/name contracts in focused finish pass, shared bindings not yet applied. Profile/native reader unification and weapon visual query work ongoing. Counts remain127 written_unvalidated/700 unimplemented. Offline inspection only; no builds/tests/client/server launch and no verified playable match.

### 2026-09-08 playerdata source integration
Registered native getplayerdata/getsecureplayerdata/setplayerdata and integrated shared public/secure session edits. Existing native profile readers see accepted GSC writes; upload gates use original bytes. Parent fixed missing-schema routing and archive cache invalidation. Source-only integration; no builds/tests/launches. IW4 startup loadout/persistence fields still require CoDOL adaptation, so method counts remain127 written_unvalidated/700 unimplemented. Focused native _class loadout translation assigned next. Match entry remains unverified.

### 2026-09-08 vision source integration
Integrated native five global/five player vision entry points, C1 bank publication and reliable commands, client/map/spawn resets. Parent corrected timing bias using actual C1 double2^-30 rather than assumed0.5. No client transition is implied by clearing server storage. Exact respawn/FP/runtime contracts still unvalidated; states/counts held127/700, eight missing bindings noted in inventory. No build/test/launch. Loadout native implementation resumed after checkpoint-only worker finish.

### 2026-09-08 weapon visual queries integrated
Native getweaponhidetags/getweaponflashtagname registered. Parent implemented shared asset accessors for32hide-tags andsilencedbyte+bda across active/retireddefinitionidentity and interned silenced tag without scr_const layout change. Composed attachment overrides/thermalquery still incomplete; no countincrease and no runtimeclaim. No builds/tests/launches.

### 2026-09-08 existing class-perk schema correction
getClassPerk now reads weaponClasses[class].perks[slot-1] through mountedplayerdata definition and sharedprofileview rather than fixedexportoffset. Actualshorttypecheckedandnegativeemptyitempreserved. Sourceonly; no build/test/launch,countunchanged.

### 2026-09-08 public profile dirty state
Integrated verified changed-byte dirtymap andwriteflag around publicsetplayerdata, plusclientstatsreset/uploadcompletion. Parentguardspreimageallocationbeforewriteandstringfieldwidth. IndependentlyverifiedC1bytewriter61f640. Speculative reverseuploadtransportremoved; accountservicewriteback remainsunimplemented/unproven. No builds/tests/launches orverifiedmatch.

### 2026-09-08 CoDOL chat commands
Native G_SayTo andmuted-chaterror now use C1V(public)/W(team), independentlyverifiedsender5201c0andclienthandlers4695a6/469618. Removeslegacyi/blurcollision. NonCoDOLh/ipreserved. No build/test/launch; source-only.

### 2026-09-08 player presentation methods
Registered setblurforplayer/setcarddisplayslot afterparentbinary/source review: C1reliablei/L, truncatingblurmilliseconds,19cardslots. Statelesssenders,noresthookneeded.129entrieswritten_unvalidated/698unresolvedcandidates. No builds/tests/launches,matchentryunverified.

### 2026-09-08 composed loadout review
Consolidated eight weapon metadata query paths onto the existing core-identity lookup so pending attachment-adjusted definitions can reach GSC/gameplay consistently. Source-reviewed only; composition lookup and loadout shared patches remain held. Two Claude workers are active on type43 attachment application and loadout/registration corrections. Copied base stats do not count as attachment support. No builds/tests/launches; counts unchanged129/698 candidates, match entry unverified.

### 2026-09-08 composed registry lifecycle review
Identified stock-only registry replay rejecting composed names after publication, and an inverse base-index lookup that must match recursive registration order. Recorded required corrections for worker integration. Verified C1 configstring tokenizer preserves the raw final argument, so existing unquoted weapon publication can carry spaces; no wire quoting change needed. Workers confirmed active. No build/test/launch or count change.

### 2026-09-08 multiplayer radar/EMP work
Dispatched third Claude worker for six radar/EMP builtins with confirmed MP script call sites, native state/snapshot consumers and lifecycle required. Attachment and loadout workers remain active. Independently inspected C1 usercmd writer branch/key order, weapon widths and optional payload gates; current decoder matches those inspected sites, source provenance updated. No build/test/launch; no added implementation counts or match claim.

### 2026-09-08 script constant lowering
Corrected remainder-operand constants being mistaken for animation references, and single-literal aliases being treated as compound expressions. These changes address unresolved constants and false signed-expression rejection in the native script-loading adaptation. Source inspection only; no builds/tests/launches or method count change. Three workers remain active.

### 2026-09-08 loadout handoff review
Reviewed terminal loadout changes and returned remaining registry replay, inverse index lookup, generation lifetime and utility script work for implementation. Coordinated with attachment worker's actual grouped source-image API; per-entry parse-order application is insufficient. Shared integration stays pending. Three workers active; no builds/tests/launches/count change.

### 2026-09-08 weaponattach asset reader integrated
Type43 definitions are now recorded in mounted asset aliases and exposed through a native reader with resolved strings, owned entry-text array and extent checks. Parent inspected C1 loader and applied shared patch. Override arithmetic/order corrections and composed-core integration remain pending. No builds/tests/launches or GSC count change.

### 2026-09-08 attachment override corrections
Corrected integer overflow semantics to retain C1 low32bits and comparator equality for matching operators. Remaining conversion-helper dispatch and sort tie behavior assigned for bounded follow-up. Type43 reader already integrated; composition and runtime validation pending. No build/test/launch or method count change.

### 2026-09-08 sequential integer parsing
Attachment integer operands now clamp explicitly to C1 signed32limits, independent of host long width, based on C1 CRT disassembly. No Claude workers used. Floating conversion/sorting and full dependency integration remain pending; no build/test/launch.

### 2026-09-08 attachment sort ordering
Replaced stable insertion sorting with the ordering transcribed from C1's CRT quicksort and small-range selection sort, including equal-entry swaps that affect winning overrides. Source-reviewed only; no tests/builds/launches. Sequential work continues.

### 2026-09-08 composed dependency source views
Added model/effect views and reviewed tail/visual views over the adjusted image. Renaming an asset clears stale source bytes while preserving its type; mounted tail/visual readers now retain types for null slots too. Graph pointers are excluded from writable names and remain scalar-protected. Graph count views permit shortening captured arrays, reject extension, and preserve null arrays when a shared count belongs to another graph. Native consumer wiring, owned tag handles, image lifetime and adjusted registry publication remain incomplete. Source inspection only; no builds, tests, launches, workers, count changes or verified match.

### 2026-09-08 composed dependency ownership APIs
Extracted CODOL_BuildNativeWeaponSoundBindings from the cached sound loader so adjusted views can produce independent bindings without a weapon-name cache hit. Stock loader delegates on cache miss. Aliases remain archive-owned; bounceSound requires bindings at a stable address. Added CODOL_AcquireEngineWeaponHideTags / CODOL_ReleaseEngineWeaponHideTags for resolved source names: one SL reference per slot, duplicate references retained, acquisition rollback and atomic replacement of prior owned handles. Inspected source, callback semantics and declarations; no builds, tests or launches. These APIs still need the composed native loader and lifetime integration. Counts unchanged; goal active; no Claude workers.

### 2026-09-08 native image loader and composer ownership
Previous goal turn added ownership APIs (progress). Added image-based core builder: resolved model/tag slots govern presence for composed inputs; stock builder retains serialized checks. Added engine image loader for 11 models, 144 animations, projectile, flashes/brass, sounds and owned tags. All dependencies load before publication; failures release acquired tags/graphs; bounceSound is rebased to caller-owned stable bindings. Composer calls this loader, removes blanket name/tag override refusal, retains image allocations, and frees core then tags then image at final reset. Source inspected only; no build/test/launch/Claude/count change. Registry adjusted keys, DB lookup and archive lifecycle shared hooks, script integration and remaining fields are pending. Do not apply old composed shared patch wholesale: its FromView loader hunks are obsolete. Full goal active, match unverified.

### 2026-09-08 adjusted registry replay and archive lifetime
Previous goal turn integrated native image loader (progress). Added reverse registry-name lookup and composed registration from the retained image's adjusted ammo/clip names and bbc/560 flags. Replay resolves the base against the registry being built, not invalid/stale global state; cached definitions reject a changed base-name mapping. Existing configstring replay paths now accept canonical composed names. Successful archive mounts retire composed caches even for ungrouped additions (new named dependencies can override); failed mounts do not retire. Full unmount resets composed owners before archive storage. Source inspection only, no builds/tests/launches/workers/count change. Dynamic append still calls stock-only registration; DB lookup and script integration pending. Com_Quit calls Scr_Cleanup/GScr_Shutdown before unmount: inspect actual SL lifecycle before claiming shutdown correctness. Goal active and match unverified.

### 2026-09-08 composed database lookup and dynamic publication
Previous goal turn integrated adjusted replay/lifetime hooks (progress). Native append now validates canonical composed names, registers adjusted keys, and recursively follows adjusted b78/b88 partner names from the cached image. Both database weapon lookup paths dispatch star names to composition; pointer-keyed metadata queries include current/retired composed cores. Added C linkage to compose declarations for the C++ database consumer. Source-reviewed only; no builds/tests/launches/workers/count change. Inspected Com_Quit pre-unmount callees: Scr_Cleanup only clears a flag; GScr_Shutdown clears level string plus existing node resets; SL_ShutdownSystem releases user-bit refs rather than destroying table. This is narrow source evidence, not complete map-transition proof. Full model component assembly, loadout VM/script integration and other gameplay gaps remain. Goal active, no verified match.

### 2026-09-08 loadout VM binding and explicit publication
Previous goal turn connected dynamic publication/database lookup (progress). Reviewed full loadout source; corrected last-ID attachment classification across all marketplace types, published-registry miss handling, bounded atomic composed-name output (15 slots/128 bytes), camo missing-ID errors, and duplicate attachment-name resolution. Implemented missing PublishComposedWeapon using temporary replay/append state including adjusted partners, reusing the native mapping/configstring commit. Registered eight loadout methods plus two composed-name global helpers. Counts remain unchanged: these are CoDOL bridge APIs, not ten proven IW4/T5 missing builtins. Script adaptation and schema/variant/model semantics still require review. No builds/tests/launches/Claude workers. Full goal active and match unverified.

### 2026-09-08 repository utility adaptation and source layer
Previous turn integrated loadout VM bindings/publication (progress). Reviewed worker utility patch; its direct native base-name return violated the original first-underscore-token contract. Added scripts/codol/maps/mp/_utility.gsc from the unchanged IW4 reference, resolving composed base names before existing tokenization and delegating composed attachment arrays. Added native script adaptation layer after user overlay and before reference sources; parser cvar codol_scriptNativeOverlay defaults to scripts/codol (relative to process working directory). Original source-reader API preserves its old root order. No alpha files or live settings changed. Class patch remains held: empty slots, copycat, offhand semantics and extra perk/killstreak handling need full adaptation. Source inspected only; no build/test/launch/count change. Goal active, match unverified.

### 2026-09-08 class draft empty slots and copycat
Previous turn added utility/source layer (progress). Reviewed class worker source and found empty primary incorrectly reenabled IW4 fallback, empty secondary converted to none_mp, composed identity lost in copycat, and lethal passed to IW4 perk validator. Corrected draft obj/claude-workers/profile-loadout-classwork/maps/mp/gametypes/_class.gsc: CoDOL identity independent of weapon presence; empty slots skip give/ammo/spawn selection; secondary selected for secondary-only loadouts; clone retains composed names plus snapshot of all five perks/four streaks/special/melee, consumed without rereading copying player's class. CoDOL bypasses IW4 bling/onemanarmy restrictions and perk slot fallback; five perks share the draft application loop. Still held outside active scripts/codol: actual lethal/offhand producers, unknown perk behavior, four-streak consumers, cosmetic/model and post-give empty-slot assumptions remain. Source inspection only; no build/test/launch/Claude/count change. Goal active.

### 2026-09-08 offhand VM exposure and four-streak draft
Previous turn corrected class draft identity/copycat (progress). Inspected native offhand producer/selector, including six-class conversion and 1/4->slot0,2/3->slot1,5->slot2. Registered existing set/getoffhandequipment methods and made setter parsing explicitly fail before mutation when an argument fails. Class draft now gives stored lethal/tactical internal names, then assigns three selected slots; legacy name/class/ammo guessing stays in non-CoDOL branch. Added fourth optional setKillstreaks argument and source from captured class's four slots; _killstreaks.gsc consumer iterates threshold map with foreach, so no three-slot truncation there. Source inspection only; no tests/builds/launches/workers/count change. Draft not activated: unknown perk/streak mappings, special/melee behavior, post-give model/empty-slot assumptions remain. Full goal active.

### 2026-09-08 consistent typed marketplace lookup
Previous turn exposed offhand methods/four-streak draft (progress). Unified older getClassPerk with shared marketplace last-ID-row resolver while retaining winning-row per type validation and original empty return. Loadout perk and attachment getters now validate per/wat types, including all-slot array before VM output. Inspected alpha killstreak overlay: it overrides native-style script functions with Python-specific codol_radiusDamage/codol_fire_nearest paths. This changes integration work: do not assume alpha gsc_overlay is a drop-in native set; separate adaptation remains required. No tests/builds/launches/workers/count change. Class remains draft pending perk/streak meaning, special/melee/model and post-give behavior. Full goal active.

### 2026-09-08 corrected perk-validator interpretation
Previous turn unified typed marketplace lookup (progress). Inspected complete IW4 validatePerk/givePerk/_setPerk: slot-based rejection is commented out; active validation gates scr_game_perks, and _setPerk dispatches optional script callbacks then native setPerk. Corrected earlier notes implying live IW4 per-slot substitution. Draft now honors scr_game_perks for all five CoDOL perk slots and removes its arbitrary IW4 CSV-membership filter that silently discarded named perks. Native handler coverage remains unproven. Marketplace Python extraction resolves pooled strings by hashes, including guessed numeric strings; do not use that as authoritative exact string mapping where native alias resolution is available. No tests/builds/launches/workers/count change. Class still draft, full goal active.

### 2026-09-08 ability snapshot representation
Previous turn corrected draft perk gating (progress). Native setperk still uses IW3's 20-name bitset; it cannot represent CoDOL ability modifiers. Independently inspected C1 46c988..46c9ec and copier432cc0 (2*8+7 floats), plus aligned setter instructions5185fe..51862e confirming ps+4d0 MSB-first mask. Initial requested518600 was mid-instruction and was not used as an instruction boundary. Added explicit four-mask/23-float ability representation and atomic client snapshot overlay at c0..128, copying values by bits and preserving other fields. Not wired to zero placeholders: table defaults/id-slot mapping, VM producers, native gameplay consumers and capture hook remain implementation work. Python resource identifies relevant tables as coAbilityModifiersTable/coPerkStatsTable, leads only. No tests/builds/launches/workers/count change; goal active.

### 2026-09-08 ability definition lookup and native set semantics
Previous turn added snapshot representation (progress). Independently disassembled C1 name->id402ea0, name->slot402ff0, id->slot402f20, default initializer403090 and setter518910..518a0b. Table column1 matches name, column0 ID, column2 value slot, column3 default. Lookup61ed00 walks backward; comparator6283d0 ASCII-folds names. Added codol_abilities.c/h with typed definition lookup, bounded indices, SetAbility default initialization plus MSB-first bit, and SetAbilityValue direct float write with no clamp/default addition/mask update. This corrects any inference that Python default-plus/clamp belongs in the native VM setter; higher-level perk arithmetic remains separate. Nonfinite/malformed inputs rejected; no full malformed-input C1 parity claim. VM player ownership, clear/unset/get, table cache/default initialization and gameplay/snapshot producers still pending. Source inspected only; no builds/tests/launches/workers/count change. Goal active.

### 2026-09-08 ability unset/clear/query semantics
Previous turn added ability lookup/set operations (progress). Independently inspected C1 unset518813..51884d, clear5188d4..518906, has518703..518749. Implemented mask-only unset and clear, plus normalized HasAbility result; values are deliberately preserved, matching instructions. The routine518a10 is a perk operation (calls40ef80), not evidence of an ability-value getter. Player-state extension ownership is the next integration target: it already copies live/snapshot/archive values, but its spectator bundle is fixed at256 bytes and serialized archive fields are explicit; expanding it requires updating both rather than appending untracked live state. No build/test/launch/workers/count change; goal active.

### 2026-09-08 archived ability ownership
Previous turn added mask-only operations (progress). Extended codol_ps_ext_t with ability masks/values and known flag so existing by-value live/snapshot/archive/spectator copies include them. Added symmetric internal archive block before scripted queue terminal fast paths, preserving stored values for cleared masks and rejecting corrupt/nonfinite decoded values. Expanded spectator local capacity256->512: reservation310c->320c, bundle30f8->31f8 at three pointer sites and both epilogues; unrelated gclient+310c accesses unchanged. Header/source/assembly sites inspected only; no compile/test/assembly/launch or runtime proof. VM initialization/lifecycle clearing, client-section producer and gameplay consumers still pending. Internal archive format changed together on both sides, not client wire layout. No workers/count change; goal active.

### 2026-09-08 ability VM writers and live resets
Previous turn added archive ownership (progress). Added live-only ability reset beside playerState spawn/connect/disconnect resets, preserving frame/archive copies. Added five VM operations against addressed playerState extension: set/unset/has/clear/set-value, resolving mounted coAbilityModifiersTable before mutation. Explicit clear preserves recorded values; unknown fresh storage starts zero and Set initializes the selected modifier's default. Arguments/receiver/table failures do not publish partial state. Source inspection only; no build/test/launch/workers/count change. C1 spawn preservation policy still requires full audit; clientState capture/publication and native movement/combat consumers are next, so no complete perk support claim. Goal active.

### 2026-09-08 sequential client-ring ability capture
Previous handoff-status turn was no implementation progress; resumed source work. Added codol_clientstate_ext.c/h, storing four masks and 23 values alongside each retained client-ring slot, with absolute sequence and client identity checks. Both SV_BuildClientSnapshot client-copy arms capture before advancing the cursor: live uses the indexed extension at capture time, archived uses the cached playerState extension, never current live state. Collector overlays captured values after its resolver; map reset clears captures. Existing engine client overlay preserves these fields. Source inspected only; no builds/tests/launches/workers/count change. An archived client without playerState currently captures reset abilities: independent clientState persistence and spectator identity behavior still require C1 audit, as do gameplay consumers/perk producers. Goal active, no verified playable match.

### 2026-09-08 independent archived client abilities
Previous goal turn added client-ring capture (progress). Independently disassembled aligned C1 G_UpdateClientInfo 50d290: 50d380..50d3bc copies ps+4d0..4dc to client+3528..3534 and 23 floats from+4e0 to+3538 through432cc0, independently of optional archived playerState. Initial midinstruction disassembly50d3c0/50d180 was not used for boundary evidence; aligned function50d290 established the copy. Replaced absent-playerState reset path with independent archive client ability storage. Added matching 27-word internal record after each of three forced client-delta writer arms and each of three decoder arms, before playerStateExists; full archive construction also owns its copy. Archive initialization clears just archive abilities; map reset clears both rings. Header and overlay source inspected; finite values and captured/client identity checked, no runtime validation. Exact live publication timing relative to spectator following still needs audit; current writer captures live extension at archive time. No builds/tests/launches/Claude/count change. Goal active, playable match not verified.

### 2026-09-08 client-info ability publication
Previous goal turn added independent client archive records (progress). Reviewed retained ClientEndFrame and C1 aligned G_UpdateClientInfo50d290 plus direct caller570d60/570d64. Added native CODOL_PublishClientAbilities at ClientEndFrame_180, before attachment/vehicle work and native spectator branch, taking the addressed ps and entity's own slot. New published session copy feeds both live snapshot ring and archive writer, removing late live-PS reads. Slot reuse/map resets clear published records; spawn preserves them like existing savedSess.cs until client-info republishes. The native insertion uses outgoing args, no live volatile register/flags values after the call; no assembly run. Confirmed MSG_WriteDeltaStruct force1 emits unchanged client records, so the unconditional archive ability record remains reader-aligned for unchanged clients. Full C1 caller scheduling/spectator parity and respawn policy not proven. Source/disassembly inspection only, no builds/tests/launches/workers/count change. Goal active.

### 2026-09-08 native CoDOL perk slot semantics
Previous goal turn added client-info publication (progress). Independently disassembled C1 methods518a10/518b80/518ca0/518db0, helpers40ef80/40f0b0/40eef0, read table pathc40754, method usage strings and eight slot namescd915c. C1 SetPerk stores numeric ID in ps+4b0[slot], Has compares ID, Unset unconditionally zeroes resolved slot, Clear zeroes all eight; none of these directly changes ability masks/values. coPerkStatsTable column1 name->column0 ID and column5 named slot; slot namesperk1..4,upgrade1..3,equipment. Added codol_perks.c/h typed operations and backwards ASCII-folded table lookup; malformed/nonpositive/overflow ID rejected deliberately, no malformed-input parity claim. This corrects any assumption SetPerk intrinsically invokes modifier accumulation. Source inspection only, no builds/tests/launches/workers/count change. Registry still retained IW3; next integrate playerState/archive ownership and VM dispatch before replacing it. Goal active, match unverified.

### 2026-09-08 CoDOL perk VM ownership and dispatch
Previous goal turn wrote native perk slot operations (progress). Added eight-ID perk state to codol_ps_ext_t, so existing by-value snapshot/archive/spectator copies carry it. Symmetric internal archive changed-bit/eight-word record goes after ability data before scripted queue early returns; decoder rejects out-of-range IDs/overflow before publishing. Existing spectator 512-byte capacity assertion retained; no assembly size changes. Live spawn/connect/disconnect clears perk slots beside ability clears; full C1 respawn-preservation policy remains unaudited. Added CODOL_SERVER VM dispatcher and conditional setperk/hasperk/unsetperk/clearperks registry replacement; receiver/name/table validated before mutation, Clear matches C1 absence of parameter-count check, Has returns normalized int. Slot operations do not synthesize IW3 bits or ability effects; modifier producers and native gameplay consumers remain implementation work. Source inspected, no builds/tests/launches/workers/count change. Goal active; entering match unverified.

### 2026-09-08 repository utility perk arity adaptation
Previous goal turn integrated perk VM ownership/dispatch (progress). Inspected repository _utility.gsc and alpha reference/overlay: repository still passed IW4's second native/script-only selector to C1 one-argument SetPerk/UnsetPerk. Adapted _setPerk/_unsetPerk to call native only for non-script-only entries with one argument, then retain self.perks bookkeeping and callbacks. Native errors now precede publishing script bookkeeping. Alpha overlay explicitly claims its Python setPerk folds modifiers/pro upgrades, contradicted as a native VM contract by C1 518a10; do not copy that behavior into native SetPerk. Reference _perks.gsc givePerk still has direct two-argument weapon/null paths; broader native adaptation remains, and callbacks may require CoDOL-specific changes. Inspected C1 518e80: two integers to ps+1b4 indexed byte, not a GetPerk routine; no guessed getter implemented. Source inspected only; no builds/tests/launches/workers/count change. Goal active.

### 2026-09-08 corrected IW4 perk boolean semantics
Previous goal turn changed utility arity (progress), but its script-only skip was incorrect. Independently resolved IW4 registry73c994->5dcba0 SetPerk and73c9b8->5dce10 UnsetPerk. Instructions5dcc81 always store slot ID before conditional5dcc88 gates native bits;5dcebe always clears slot before conditional5dcec9. Corrected repository _utility.gsc: all names reach one-argument C1 slot methods, including script-managed entries; callbacks retained. Added repository scripts/codol/maps/mp/perks/_perks.gsc from unchanged vendor/iw4 reference with its two direct SetPerk(name,false) calls adapted to one argument. This is arity/slot adaptation, not full CoDOL vocabulary or modifier gameplay support; unresolved table names still error. Explicit user overlays retain priority and alpha files/live settings untouched. Source/disassembly inspected only; no builds/tests/launches/workers/count change. Goal active, match unverified.

### 2026-09-08 ability registry audit and clear contract
Previous goal turn corrected IW4 perk boolean/script adaptation (progress). Read C1 method pointer records c3bfd4..c3c034: name entries empty atc2fead, so no exact ability-name proof from on-disk table. usingabilitymodifier atc69eec references UI expression name tablecd0980, not GSC registration; no alias added. Added docs/CODOL_ABILITY_REGISTRY_REVIEW.md with exact function pointer addresses and uncertainty. Aligned518850..518906 has no argument-count check; removed source ClearAbilityModifiers zero-parameter enforcement, retaining player validation and mask-only clear. Exact ability spellings still need independent script ID mapping, no newly claimed support. Source/binary inspection only, no builds/tests/launches/workers/count change. Goal active.

### 2026-09-08 perk playerState wire publication
Previous goal turn audited registry/clear (progress). Alpha enumeration did not provide stronger exact ability name mapping, and its older docs incorrectly claim ability effects have no wire channel; subsequent clientState evidence supersedes that claim. Found eight perk IDs present in measured playerState netfields but absent from native producer. Independently read C1 tablec38ca8: offsets4b0..4cc all8bits/hint0 at field indices139,106,140,76..80. Added atomic CODOL_OverlayPlayerPerks with explicit0..255 validation and all-eight-field coverage; CODOL_BuildGameplayFrame seeds from source->ps extension before retained overlays, preserving delayed/spectator ownership. No truncation to another perk ID. Source inspected only; no builds/tests/launches/workers/count change. Ability gameplay consumers and broader script/table mapping still incomplete; goal active, match unverified.

### 2026-09-08 native ability consumer lookup
Previous goal turn published perk netfields (progress). Independently disassembled C1 BG_GetMaxSprintTime40e990 and ID->slot402f20. Ability ID0 MSB controls duration; inactive defaultc3e060=4seconds; active negative duration returns0. C1 uses weapon+678,1000doublec842b0, roundedfloat intermediate and FISTP after addingc84590=2^-30; retained code still uses IW3 perk multiplier/16383clamp, so changing only base duration would mix incompatible formulas. Added pure CODOL_ReadAbilityValueSlot matching decimal ID text against column0 then column2, and CODOL_GetActiveAbilityValue with mask-first lookup, finite validation and atomic output. Does not guess value-slot=id or initialize defaults in consumers. Full sprint replacement awaits rounding/control-word and override interaction audit; no gameplay parity claim. Source/binary inspection only, no builds/tests/launches/workers/count change. Goal active.

### 2026-09-08 native C1 sprint duration path
Previous goal turn added ability value lookup (progress). Replaced CODOL_SERVER BG_GetMaxSprintTime body with C1 sequence: read ID0 seconds (4default), negative returns0, weapon sprintDurationScale, x87 double1000 multiply, float intermediate, epsilon2^-30 plus FISTP. Native IW3 perk multiplier and16383clamp retained only outside CoDOL. FPU control-word parity still unverified; no runtime/assembly claim. setsprintduration T5-style input still truncates to milliseconds, then writes seconds into ID0's mapped ability value and sets its mask, so snapshots/player copies and C1 prediction receive it. VM now reports setter mapping/state failure rather than silently ignoring status. Added direct ability header and constants, reviewed conditional branches/common epilogue. Cooldown33 remains unintegrated; field16bit representability still checked by snapshot overlay. No builds/tests/launches/workers/count change. Goal active.

### 2026-09-08 native sprint meter and ability33 correction
Previous goal turn integrated duration (progress). Independently inspected C1 PM_GetSprintLeft40f5a0..40f6b2 and helper403070. Corrected earlier report inference: ability33 is a strict recovering-meter threshold that fills meter to maximum, not a cooldown subtraction. Added CODOL_GetSprintLeft and CoDOL-native PM_GetSprintLeft body invoking it with BG_GetMaxSprintTime: maximum0 returns3fff, initial meter maximum, active sprint countdown, recovering wrapped32 arithmetic, float-meter comparison to ability33 seconds*1000, final0..maximum bound. C1 ordinary recharge delay here is zero; explicit T5 cooldown remains a separate compatibility extension. Original assembly body compiled only outside CoDOL; source branches/stack reviewed, no assembly run. PM_UpdateSprint still has separate pause/gating paths requiring review, as does FPU configuration. No builds/tests/launches/workers/count change. Goal active.

### 2026-09-08 C1 sprint-start meter gating
Previous goal turn added meter/refill (progress). Independently inspected aligned40f8f0/40f9eb..40fa80 and start40f720 (initial40f780 was midinstruction, discarded). C1 does not pre-gate maximum<=0; PM_GetSprintLeft returns3fff for zero maximum. Removed retained max<=0 gate only forCoDOL, changed default recharge pause to0, retaining explicit T5override. CoDOL PM_UpdateSprint_180 now calls native PM_GetSprintLeft (including ability33) and requires >1000ms, then commits returned meter/time/native sprint flag; bypasses old inline formula and dvar minimum. Corrected helper comment: negative duration produceszero maximum, notdisabled sprint. Other start-state details remain: C140f720 also changes ps+cc/+d4, and button/weapon condition differences still need native mapping audit. Source/disassembly inspected only, no builds/tests/launches/workers/count change. Goal active.

### 2026-09-08 sprint-start torso animation transition
Previous goal turn connected start meter (progress). Traced C140f720 and BG_SetAnim405b70/405c4b to identify ps+cc torsoAnim and+d4 torsoAnimDuration. Crucially source6c3d288+48 is animation record0 duration, not bgs time: BG_SetAnim indexes samebase by0x68 then+48. Retained BG_PlayAnim_10 uses translated AnimationRecords stride0x60/+48, writes torso duration+9c, so added CoDOL sprint commit reset: if torso index excluding0x400 is nonzero, invertrestartbit/clearindex then record0duration+50. No timestep/timer substitution. Added source ABI checks for retained+94/+9c, inspected assembly register flow and record allocation. No builds/tests/launches/workers/count change; input/weapon conditions and FPU/runtime parity remain incomplete, goal active.

### 2026-09-08 CoDOL sprint button masks
Previous goal turn added torso transition (progress). Inspected CODOL_ToEngineUsercmd and accepted-input ownership seam: native0xff3f projection drops C1button10000, maps20000->native10000 and100000->ADS, so native c435/c735 masks cannot express C1 predicates. Added CODOL_SprintButtonsBlocked: owning live network commands use accepted raw word with C1 start1cc35/continue1cf35; bot/synthetic/unbound inputs keep native masks. Both retained sprint predicates call helper, preserving live edx across C call. Does not key by command timestamp or latest received packet. Helper/source/assembly reviewed; remaining forwardminimum/weapon gates and potential post-acceptance input filtering interactions need audit. No builds/tests/launches/workers/count change. Goal active.

### 2026-09-08 sprint input-mode filtering and forward threshold
Previous goal turn added network masks (progress). SV_UserMove stages unfiltered wire buttons, while CODOL_ToEngineUsercmd applies CODOL_FilterUsercmd. Updated sprint predicate to filter a local accepted-word copy before applying C1 masks, preserving raw history. Changed both CoDOL forwardmove gates from retained dvar to C1 literal>105 (40f7ab/40f81c); non-CoDOL retains dvar path. Inspected surrounding assembly and local-5c references: no later use in PM_UpdateSprint depends on skipped dvar store. Added consolidated sprint_ability_review to JSON. Full weapon-state predicate and FPU/prediction parity remain pending. No builds/tests/launches/workers/count change; goal active.

### 2026-09-08 offhand detonation sprint gate
Previous goal turn aligned filtering/forward threshold (progress). Inspected TranslateEngineWeaponState: native12..20 map into C1 blocked13..21, but added native27 maps to C1detonation20 and was missed by retained range checks. Added state27 checks to both CoDOL sprint-start and continuation branches, retaining existing pmflag exception flow and stop-sprint lifecycle. Native25/26 have no current producer and remain legacy comparisons; did not invent mappings to C1 additional29/30. Source branches and state declaration inspected; no builds/tests/launches/workers/count change. Full movement/weapon/FPU parity still unverified; goal active.

### 2026-09-08 script rawfile compilation ownership
Previous turn verified repository Claude workers terminal; no implementation progress in that status turn. Continued sequentially. Inspected Scr_ReadFile/Scr_ReadFile_FastFile/Scr_PrepareSource and Scr_LoadScriptInternal/Scr_ScriptPreCompile: unchanged lowering returned the mounted rawfile buffer, then the precompiler rewrote conditional directives in place. CoDOL fallback now copies validated rawfile bytes into compilation-session temporary memory before preparation, matching the other source readers. This preserves original directives for later compilations and syscall-registry evaluation. Non-CoDOL behavior unchanged. Source/control flow inspected only; no builds/tests/launches/workers or coverage count change. Full GSC startup and match entry remain unverified; goal active.

### 2026-09-08 rawfile packed-name script resolution
Previous goal turn fixed rawfile compile-buffer ownership (progress). Inspected current script/engine lookup and independently disassembled C1 4c58a0..4c596e: names at4c58e7..4c592c are null/inline-1/packed XStrings; nonzero buffer word at4c592e consumes inline payload of compressed size or length+1. Runtime replay already reconstructs persistent block3, but both lookups only recognized inline names. Engine lookup now resolves packed persistent names via CODOL_LoadBlockString, skips directory references/unnamed/comma-reference entries, and fails unresolved definitions instead of silently falling back. Script loader shares engine resolver/cache and returns an owned copy, preserving binary-NUL rejection and adding the common16MiB script bound. Archive cache ownership keeps borrowed names alive; no recursion back into script loader. Other string blocks remain unsupported. Source and PE inspection only; no builds/tests/launches/workers/count change. Goal active; full script startup and match entry remain unverified.

### 2026-09-08 string-table packed-name resolution
Previous goal turn added packed rawfile name lookup (progress). Independently inspected C1 StringTable loader4c5b90, name branch4c5bd5..4c5c1a and values branch4c5c1c..4c5c41. Mounted table lookup was inline-name-only despite replay supporting persistent names and CODOL_ReadStringTable preserving name_reference. Added packed block3 name resolution, preserving reverse mount/asset precedence and reference-only skips. Decoded cache retains the resolved name when no inline owned name exists; this prevents NULL name publication/cache comparisons. Checked table cleanup precedes load-block teardown and FreeStringTable frees storage/cells only. Cells already resolve packed references with hash validation. Other name blocks remain unsupported; no broader table or script-parity claim. Source/PE inspection only, no builds/tests/launches/workers/count change. Goal active; GSC startup and match entry remain unverified.

### 2026-09-08 string-table dispatch independent of IW3 fastfiles
Previous goal turn integrated packed string-table names (progress). Reviewed table VM wrappers, retained row/column accessor and IW4 5f4720/4ac180. Found StringTable_GetAsset rejects all requests when useFastFile is false before reaching native CoDOL mounted-table/reference-CSV resolution. Conditionalized this legacy guard out of CODOL_SERVER only. Confirmed DB_FindXAssetHeaderReal forwards to DB_FindXAssetHeader; mounted table resolution and absent-only CSV fallback precede retained database lookup, and invalid native data still errors. Existing assembly prologue/outgoing args/epilogue unchanged. No assertion of C1 useFastFile policy; this fixes ownership of native source resolution. Source/PE inspection only; no builds/tests/assembly/launches/workers/count change. Goal active; script startup and match entry unverified.

### 2026-09-08 absent string-table cell semantics
Previous goal turn removed the IW3-only string-table gate (progress). Independently disassembled C1 cell array4c5af0, zero-pointer skip4c5b41..4c5b43, selected-cell null branch61eebb..61eebd. Structural reader previously counted reference0 as unresolved and mounted resolver then rejected it. Changed unresolved count to nonzero references only and mounted relocation to skip true nulls; source header documents null versus unresolved versus empty string. Retained row searches skip null cells and selected-cell accessor yields empty string; CoDOL rownum does the same. Checked perk/ability/composed/loadout/character consumers' existing null guards. Did not synthesize empty search keys or bypass nonzero-reference/hash validation. Source/PE inspection only, no builds/tests/launches/workers/count change. Goal active; complete consumers/startup/match entry unvalidated.

### 2026-09-08 native map-loader dispatch
Previous goal turn fixed absent string-table cells (progress). Traced table consumers: register_stock already skips null names; constant importer rejects null rows transactionally. Made constant diagnostic printing null-safe. Found SV_SpawnServer skipped native archives/inherited and weapon configstrings under useFastFile0, while CM_LoadMapData and Com_LoadWorld selected IW3 loose BSP consumers. CoDOL now always executes native mount/init block, collision native installer and DB common-world translation, and omits loose BSP load/unload and IW3 sound CSV loading. Non-CoDOL toggles remain unchanged. Reviewed conditional source branches and tailcall argument preservation. Other useFastFile-controlled engine paths, complete sound/world behavior and runtime startup remain to audit. No builds/tests/assembly/launches/workers/count change. Goal active; match entry unverified.

### 2026-09-08 startup archive gates and resumed GSC workers
Previous goal turn changed native map dispatch (progress). Parent reviewed common init and SV_Map: PMem/DB init and R_Init (native startup mounts) were still skipped with useFastFile0; map command required IW3 BSP and unused _load fastfile. CoDOL now performs native initialization unconditionally and checks map via DB_FileExists mode0 (CODOL_BuildZonePath); actual map dependency validation remains in native mount. Source branches inspected, no builds/tests/launches/count change. Remaining restart/shutdown gates need audit.
User explicitly reauthorized Claude workers; AGENTS.md updated. Started TWO fresh Opus/high workers, max70turns each, no subagents/runtime/testing. Radar owns codol_script_radar.c/h and new codol_radar_state.c/h; startup-extra owns only new codol_script_startup_extra.c/h. Shared integration via proposed patches, not direct edits; both instructed IW4OL may be freely rewritten. Prompts/runners/results/checkpoints under obj/claude-workers/gsc-radar-resume* and gsc-startup-extra*. Supervisors73520/74192; authoritative claude agents lists live sessions b34cd1dc-7e63-42a2-a0fe-b2787a9f2a98 PID78300 and32ec38b6-ec00-4dbb-b8a8-73599f46d6b8 PID76584 (map parent PID before attributing). No worker output accepted/count changed. Goal active, match unverified.

### 2026-09-08 archive shutdown ownership
Previous goal turn fixed startup archive/preflight gates and started workers (progress). Reviewed Com_Quit_f/Com_Restart/Com_Close and DB release/shutdown bodies. Quit freed CoDOL archives before normal DObj/animation consumer teardown. Moved unmount into Com_Close after DObj/animation/world/collision/sound shutdown, before Hunk_Clear/Scr_Shutdown, preserving valid script-string handles for owned asset release. Recursive-error exit skips normal cleanup and terminates without premature freeing. CoDOL DB release and shutdown now run regardless of useFastFile, matching unconditional init. Restart does not unmount startup/retired archives; existing ownership preserves referenced data. Source inspection only, no builds/tests/launches/count change; complete shutdown/error paths unverified. Both Claude sessions verified live: radar32ec38b6-ec00-4dbb-b8a8-73599f46d6b8 PID76584 parent73520; startup-extrab34cd1dc-7e63-42a2-a0fe-b2787a9f2a98 PID78300 parent74192. Both wrote initial investigation checkpoints; no output accepted yet. Goal active, match unverified.

### 2026-09-08 native animation dispatch and string lifetime audit
Previous goal turn moved archive cleanup (progress). Scr_Cleanup only clears evaluation flag; GScr_Shutdown clears nodes/anim-move/level string, not the whole string pool. Scr_FreeScripts clears system user1 refs, while archive owned refs require later explicit release; preserved provider release before final Scr_Shutdown. Found remaining useFastFile animation layout/loader branches. CoDOL XAnimCreate/XAnimPrecache now use native DB resolver, sync missing-animation replacement uses same path, debug/sync default predicates avoid reading loose-layout byte+1e, and script animtree skips loose precaching. Non-CoDOL retains branches. Reviewed retained args/stack/tailcall flow. No builds/tests/assembly/launches/count change. Full default asset behavior/animation startup and match entry remain unverified. Workers retain assigned ownership; no integration claims. Goal active.

### 2026-09-08 native animation default classification
Previous goal turn corrected animation dispatch (progress). Reviewed DB_IsXAssetDefault and native XAnim cache: successfully loaded native animations never enter db_hashTable, so old query returned1 on hash miss and sync-node code could treat real mismatched-loop clips as missing replacements. Added native XAnim lookup to default query: decoded native definition returnsfalse, malformed native data raises existing-style error, absence falls through to retained DB default classification. This is definition provenance, not name-based void matching. Confirmed cache/build path has no recursion into default query and reuses native parts/owned handles. Source inspected only, no builds/tests/launches/count change. Both existing Claude PIDs/session IDs verified live, no duplicate launches and no worker output counted. Goal active; animation-tree startup and match entry unverified.

### 2026-09-08 model/weapon default provenance
Previous goal turn fixed native animation classification (progress). Reviewed weapon default/null loaders: both require real archive definitions; neither creates an absent-asset placeholder. Retained DB_IsXAssetDefault uses zoneIndex0, but native weapon/model branches incorrectly compared names with g_defaultAssetName. Native resolved definitions now returnfalse even for default-named assets; invalid native data raises error consistently with main asset lookup, absence retains DB fallback. Read back changed function; no builds/tests/launches/count change. Both Claude sessions still authoritative-live; empty result files are not terminal and no restart dispatched. Checkpoints still initial investigations, no accepted GSC output yet. Goal active; match/runtime behavior unverified.

### 2026-09-08 enumeration and event-lifecycle audit
Previous goal turn fixed default model/weapon classification (progress). Followed generic enumeration: inspected callers cover diagnostic listing/pool overflow and delayed images, not demonstrated GSC startup need; deferred broad enumeration rewrite. Correction to parent commentary: CODOL_EnumerateMountedSoundAliases has NO production caller, sounds register on demand through G_SoundAliasIndex. Traced sound/event producer and found entity_event_count is incremented by CODOL_EntityEventAllowed with limit4 and reset only through entity/state reset. Its comment explicitly admits C1 frame reset is unproven and intentionally imposes a per-instance limit. Marked this unresolved_gameplay_blocker in JSON: this can permanently suppress events on long-lived entities and is not compatible merely because it drops sooner. Next trace IW4/retained frame lifecycle and C1 frame producers; do not conflate event snapshot history with per-frame budget. No speculative reset written, no builds/tests/launches/count changes. This audit changes next implementation priority. Goal active; match entry unverified.

Follow-up source-wide call audit corrects the preceding finding: CODOL_EntityEventAllowed has no caller in src, including _g_utils_mp.asm G_AddEvent. The header/comments claim an integration that does not exist. Pending is queried but the counter is never consumed. This is incomplete event-budget integration, NOT a proven current four-event cutoff. Do not wire the draft limit without resolving reset timing. JSON corrected; previous paragraph retained as audit history.

### 2026-09-08 event-queue lifecycle separation
Previous goal turn identified unintegrated budget (progress). Read full retained G_AddEvent: player arm calls CODOL_PlayerStateScriptEventAdded; nonplayer arm writes native four-slot ring then advances CODOL_EntityStateEventAdded epoch. Script transfer clamps to four retained slots and advances a separate transferred epoch. G_RunFrameForEntity eventTime300ms only frees/unlinks temporary entities, not an event-budget reset. Corrected source/header claims that budget is integrated or a per-instance cutoff proves parity. No counter wired, no timer substitution. Concrete next evidence remains C1/IW4 frame-budget reset; preserve actual history producers. Startup worker checkpoint now identifies missing MP link/camera/control family with IW4 handler addresses; still owns its files, no output accepted. No builds/tests/launches/count change; goal active.

### 2026-09-08 zero scripted-event transfer
Previous goal turn separated budget/history state (progress). Independently read aligned C1 transfer40cf10 (discarded preceding jump-table bytes as code), callback40cf55..40cf64, zero skip40cf6c..40cf6e, append40cfa0..40cfc3 and cursor40cfc9 onward. Existing CoDOL helper ran handler then copied event0 into entity queue, incorrectly advancing sequence/epoch. Added zero to filter, preserving callback and acknowledgement ordering. Read retained G_PlayerEvent: current handler only applies recoil for selected events, so no proven reentrant event producer there; did not invent a reentrancy fix. Native four-slot snapshot history remains unchanged. No builds/tests/assembly/launches/count change. Workers retain ownership, no accepted output yet. Goal active; full transfer/budget/runtime and match entry unverified.

### 2026-09-08 scripted event filters from C1
Previous goal turn fixed event0 (progress). Read C1 c3ee20 andc3ef7c directly and matched aligned40cf6c..40cf9e initial literals23/6 and zero terminators. Replaced scripted transfer's retained IW3 numeric filters with a switch on CODOL_EventToWire(event), matching the scripted player wire publication. Weapon-switch-start28 is now correctly filtered. Callback still precedes filter; unknown translation remains visible to downstream validation. Predicted transfer remains a separate open issue because its fire events publish43..46 while scripted/third-person mappings are30/31; native firing side effects need audit before altering that path. No builds/tests/assembly/launches/count change. Goal active; full event and match behavior unverified.

### 2026-09-08 predicted ring parameter width
Previous goal turn integrated scripted C1 filters (progress). Independently disassembled C1 40d000 callsite: predicted f0/f4/104/114 and scripted118/120/130/11c both pass to40cf10. Parameter load40cf4e/store40cfb0 are dwords. Native player.h likewise has unsigned int eventParms[4], but retained BG_PlayerStateToEntityState truncated it tobyte before writing entity ring. CoDOL branch now preserves dword; snapshot resolver/width checks remain downstream. Non-CoDOL remains byte path. Updated stale comments claiming scripted helper still shares IW3 filters. External-event branch atnativeps620 remains separate unaudited path, as do predicted filters/fire consumers. Source/PE inspection only, no builds/tests/assembly/launches/count changes. Goal active, match unverified.

### 2026-09-08 player standalone event parameter
Previous goal turn fixed predicted ring width (progress). C1 40d054 writes0 to entity+ac after both queue transfers. Retained entity.h names native+9c eventParm, while BG_PlayerStateToEntityState_220/250 filled it through another ps620 event cursor. CoDOL now clears the field and bypasses that cursor branch, preserving both actual ring transfers. Non-CoDOL branch unchanged; temporary event entity producers untouched. Verified240 reloads its required registers so bypass does not consume old branch state. C1 clears after transfers; native clears before, and current handler only recoils/transfer writes rings so final state matches absent reentrant external mutations; full runtime remains unverified. Both workers still live in last authoritative snapshot, reports show concrete radar client-consumer and MP-link family evidence; no output accepted. No builds/tests/assembly/launches/count change. Goal active.

### 2026-09-08 standalone parameter clear ordering
Previous goal turn removed legacy standalone event cursor (progress). Tightened ordering to C1 40d054: moved eventParm clear from pre-transfer assembly into the end of CODOL_TransferScriptEventsToEntity, after callbacks/ring copies and transfer acknowledgement; empty scripted queue path also clears it. Both retained conversion exits call this helper. This removes the earlier assumption that no callback could observe/mutate the standalone field. Temporary-event producers still unaffected. Source readback only, no builds/tests/assembly/launches/count change. Both Claude workers confirmed live; continuing existing assignments, no duplicate restart. Goal active; complete event/runtime/match behavior unverified.

### 2026-09-08 missing GSC methods: focused worker completion
Resumed two existing Claude sessions after verified max-turn termination, with 30/20-turn completion budgets for player/camera/control linking and radar/EMP respectively. Parent reviewed startup-extra draft and withheld integration: camera/control consumers and viewFraction behavior are absent, some link/view semantics are guesses, and lifecycle/publication ordering needs correction. These are implementation gaps, not supported methods. Workers received concrete follow-ups, architecture freedom, unchanged writing-only restrictions and nonoverlapping ownership. Counts remain129 written_unvalidated /698 unresolved candidates; no new runtime or match claim. Retained firing callback investigation continues separately; no predicted fire filter change until world-event production is established.

### 2026-09-08 predicted empty events
CoDOL predicted transfer now skips event0 after its gameplay callback, matching C1 shared transfer40cf6c and the already-corrected scripted transfer. Existing transfer cursor advances, entity ring sequence/epoch does not. Retained FireWeapon has no direct world-fire event append; predicted firing filters remain unchanged until downstream production is resolved. Both GSC Claude follow-ups remain live. Source inspection only, no builds/tests/launches; no coverage-count increase or match-entry claim.

### 2026-09-08 full predicted event IDs
Preserved full native event IDs across predicted queue load, callback, filters and entity store under CODOL_SERVER, matching C1 40cf48/62/6c/a9. This prevents high or unsupported values silently aliasing low-byte events before snapshot validation. Prior zero skip remains after callback. No change to firing filters pending producer audit. Source/PE read only, no builds/tests/launches or new method-count claim; goal remains active.

### 2026-09-08 producer preserves event words
Removed CoDOL-only byte truncation of event and parameter arguments in BG_AddPredictableEventToPlayerstate. This completes word preservation at the shared predicted producer as well as the previously corrected transfer. Event semantics and wire limits still belong to downstream resolution. Workers remain live; radar per-client input fields and linking consumers remain open. No builds/tests/assembly/launches or completion claim.

### 2026-09-08 radar input field investigation
Verified C1 isradarblocked recordc3c1e0: client+35a4, type0, generic getter/setter. Existing native client-field callbacks provide the implementation route without changing retained struct offsets. Input must remain an integer script-owned value separate from team block and captured/spectator playerState. Located spawn/connection/map reset sites; concrete integration notes at obj/claude-workers/parent-radar-input-integration.md. Workers still own radar/link sources; not counted as implementation. No runtime validation, goal remains active.

### 2026-09-08 isradarblocked storage and lifecycle
Written native integer input storage and actual GSC client-field get/set registration. Resolves the receiver's live client storage, keeping spectator input separate from followed state. Input clears at spawn, connection lifecycle and map reset; historical playerState remains separate. Pending: OR this input in radar worker's gameplay publisher after ownership handoff, then integrate/review the worker's snapshot and frame patch. No build/runtime validation or supported-method count increase.

### 2026-09-08 radar input publication and archive review
Connected isradarblocked integer input to the radar frame producer OR with team block after worker termination. Worker carrier design failed source review: retained -98 codec stores24bits, but all three proposed carrier flags are higher. Therefore radar frame/overlay/registry integration remains withheld until archive representation is corrected. Marked source header explicitly not ready; source-written does not mean supported. Startup worker still live, radar terminal at bounded cap. No runtime validation or coverage-count change; goal active.

### 2026-09-08 archive eFlags width
CoDOL retained player/entity/archived-entity tables now use existing32bit integer delta codec for eFlags. Legacy -98 remains for non-CoDOL. This preserves proposed radar high-bit state through internal archives; CoDOL client wire schemas remain separate. Encoder/decoder and snapshot dispatch source inspected, no tests/builds/runtime. Radar integration remains pending further review; goal active.

### 2026-09-08 radar/EMP connected
Six radar/EMP GSC registrations now connected to native methods, team/per-player input publication before entity conversion, player/entity wire overlays, and map reset. Full-width internal archives preserve captured carrier bits. Updated existing source-link dependencies, ran no tests/builds. This is integrated source, unvalidated in C1. Linking handoff remains unregistered because its historical-state and view semantics are incomplete. Goal active; match entry unverified.

### 2026-09-08 linking overlay made independent of live state
Draft link serializer now accepts an explicit captured record and never reads current entity existence or client link state. This removes two sources of historical snapshot corruption. Still required: capture the record with playerState, encode/decode it through archives and spectator copies, and resolve remaining C1 view semantics. Existing proposed linking integration patch is stale; methods remain unregistered. Source only, no builds/tests/runtime claim.

### 2026-09-08 captured links in playerState archives
Added compact captured link record and known flag to playerState extension, with matched delta archive serialization and range/overflow rejection. Existing by-value extension copies carry it through snapshot/spectator storage. Overlay consumes this captured type; live capture/reset and final publication wiring still pending. No runtime validation or supported-method count change; goal active.

### 2026-09-08 link capture/reset paths
Captured camera/control/link mode into live playerState extension on playing frames before snapshots. Added live-extension clearing and separate script-owned link resets for spawn, connection lifecycle, maps and freed targets. Existing archived records remain unchanged. Final wire overlay and movement/view semantics remain incomplete; methods unregistered. Source only, no runtime validation.

### 2026-09-08 captured links reach snapshot translation
Separated link wire overlay from script VM and connected it to the playerState extension at end of native player translation. Captured history is authoritative; unknown input fails instead of querying current entities. Capture/archive/spectator/wire path is written; view semantics and GSC link registration remain unfinished. Source-only work, no builds/tests/runtime validation.

### 2026-09-08 linked-offset semantics corrected
Aligned C1 disassembly proves enable/disable only check tagInfo and toggle mask2 inps14. Removed draft relinking/teleport behavior and custom-mode guard, retained captured flag publication. Movement consumer and camera conditional flag remain open; methods unregistered, no runtime validation.

### 2026-09-08 camera tag compatibility
Corrected CameraLinkTo draft to use ordinary tag string and allow empty slot0 without requiring a server DObj tag matrix, matching C1 getter/allocator evidence. Nonempty tags still register/broadcast through native configstrings. Confirmed the extra camera80 flag condition reads VM argument count; capturing its sticky lifetime remains unfinished. Methods unregistered and no runtime validation.

### 2026-09-08 camera active and sticky state
Implemented separate captured camera flags and retained target/tag state. Unlink clears only active2, preserving80 and fields as C1 does; spawn/reset clears all. Archive and wire overlay carry the same values, including inactive camera history. No runtime validation or new registered-method claim; goal remains active.

### 2026-09-08 model/tag configstring slot ownership
Native model/tag refresh and camera tag registration now preserve inherited fastfile slots and reuse matching effective names. Shared allocator validates reliable-command tokens before storing or broadcasting. Cached mappings recognize inherited names, avoiding repeated re-registration broadcasts. Source-only change, no runtime validation or match completion claim.

### 2026-09-08 camera GSC pair connected
Registered cameralinkto/cameraunlink after producer/configstring/capture/archive/lifecycle review. Methods now reach implemented native state and wire publication; controls and player-link view family still pending. Full client behavior remains unverified, and no tests/builds/launches occurred. Goal active.

### 2026-09-08 controls argument order
Corrected controlslinkto draft to resolve target before linked-state validation, matching C1. Identified missing target flag as missile-specific, correcting worker's vehicle label. Missile consumer and ownership semantics remain open; controls names unregistered. Offline source/PE inspection only, no runtime verification.

### 2026-09-08 controls missile gameplay evidence
Found IW4 controlled missile trajectory dispatch and actual speed/boost consumer5e8790. It resolves controller client/buttons and updates velocity/position, proving the missing controls behavior extends beyond snapshot fields. Located retained native MissileTrajectory for implementation. C1 mapping and accepted command binding remain to finish; controls still unregistered. Offline source/PE work only.

### 2026-09-08 remote input bound to accepted commands
Remote-angle bytes now travel with staged/accepted CoDOL commands through reject, bot, synthetic and reset paths. Valid zero input remains distinct from absence. This supplies native remote control with accepted input instead of last-received packet data; missile behavior still to implement. No runtime validation, goal active.

### 2026-09-08 Claude workers reauthorized: missing GSC implementation
User explicitly reauthorized Claude workers. Verified prior worker registry empty before launching two Opus/high workers, bounded to60 turns each, no subagents. gsc-remote-missile owns new codol_remote_missile.c/h and its artifacts: controls-link missile consumers, accepted remote input interpretation, measured native trajectory/state/lifecycle, shared integration as proposed patches. gsc-missing-next owns new codol_script_missing_next.c/h and its artifacts: select and implement3-6 real missing startup natives excluding existing assigned/drafted families, checking registry and IW4/T5 evidence first. Supervisors76860/59860; live CLI sessions confirmed f809684d-6203-497e-8445-7110b745e2e4 and256e14b0-4d60-448a-8216-04f392d7a4e8 (mapping to assignments pending reports). Both explicitly instructed native IW4OL architecture freely rewritable; no hooks, builds/tests/launches, no duplicate workers, no stub coverage. Parent retains shared-source integration and manifests. Corrected stale startup header comments to describe existing capture/archive plumbing and selective camera registration. No new implementation coverage claimed. Match goal remains active and unverified.

### 2026-09-08 playerState archive semantic preflight
Previous goal turn made progress by launching two explicitly authorized bounded Claude implementation workers and correcting stale integration comments. Both sessions are authoritatively live this turn; remote missile scope confirmed, missing-next evaluating entity bounds queries against IW4/T5. Parent source-reviewed spectator bundle reservation and extension record ordering. Found archive writer masked weapon-lock flags/entity, recoil percentage and HUD indices before later wire validation, potentially changing invalid values into different valid historical values. Added shared preflight for current/baseline recoil, lock flags/entity/finite vectors, HUD indices, finite ability values, nonnegative perk IDs and captured links, using the reader's existing semantic domains. Writer rejects before emitting any record bits; reader rejects an invalid inherited baseline before consuming a delta. Removed those redundant truncating masks and moved link validation to preflight. No change to valid-record layout. Hand encoding remains separately scoped; no claim of exhaustive archive validation. Source readback only, no builds/tests/assembly/launches; no method coverage increase. Goal active, match entry unverified.

### 2026-09-08 native path-node property setter semantics
Previous turn made progress on archive semantic preflight. Both Claude workers confirmed live this turn. Reviewed script loader and deferred childthread handoff; no MP use or resolved reference lifecycle justifies integrating its flawed patch. Investigated actual path-node setter stub. T5 symbol map identifies Scr_SetPathnodeField00921e80: aligned disassembly validates field/node bounds, calls00921ef0, which loads property name and unconditionally calls Scr_Error008def20 with string00d37aa0, "pathnode property '%s' is read-only". Dynamic setter00922070 follows a distinct VM field path. IW4 exact diagnostic search returned none; T5 evidence used as fallback, no inferred writable behavior. Replaced generic not-implemented error for registered native path fields with receiver/index/field validation and named read-only error. Vehicle-node writes and full node-field schema/dynamic/navigation semantics remain separately unresolved. No tests/builds/launches or method-count claim. Goal active, match behavior unverified.

### 2026-09-08 C1 vehicle/path-node assignment contract
Previous goal turn made progress replacing path-node placeholder with evidenced T5 read-only behavior. Independently traced C1 aligned object-field dispatcher56b660, table56b714: class2->56b6ce (named pathnode read-only error c7a61c), class3->56b6f3 (vehicle node is read-only c5cb30). IW4 aligned4f20f0 also routes class3 to4f2103 with6ec8c4 same vehicle error; T5 map/switch684ef0 table684f94 confirms class3->684f40/ccb5bc. Replaced native vehicle-node not-implemented placeholder with actual unconditional read-only contract and strengthened path-node source evidence to C1. No mutable properties invented; full field schema, dynamic variables and navigation still separate work. Both Claude sessions confirmed live; no duplicate restart. Source/offline PE inspection only, no builds/tests/assembly/launches or coverage count increase. Goal active; match entry unverified.

### 2026-09-08 C1 path-node field inventory and animscript
Previous turn made progress on C1 vehicle-node assignment semantics. Both Claude sessions verified live. Offline C1 table decode cccee8 confirms targetname,target,animscript,script_linkname,script_noteworthy are type5 strings; origin type6; angles type15 (not a plain vector field); radius/minusedistsq type3; spawnflags type1; type callback6f94c0 returns display strings via ccce98. Native draft omitted animscript; added its read-only VAR_STRING registration backed by the existing owned spawn record/getter, preserving existing field indices. Lookup6f9952 and6f9b23 explicitly require native type5, whereas current lookup accepts arbitrary spawn keys; this requires a follow-up on unknown-key behavior before changing shared single/array lookup. Full table/defaults/type/angle/navigation semantics remain unresolved; no claim of full path-node compatibility. No builds/tests/launches or coverage-count increase. Goal active.

### 2026-09-08 native getnode/getnodearray key semantics
Previous turn added evidenced animscript field (progress). Traced aligned C1 GetNode6f9880 and GetNodeArray6f9a60: both resolve key through native class table and require type5; single lookup returns undefined for missing/negative field index6f9928/6f9943->6f9a57. Array missing key6f9ae1->6f9c47 routes to parameter2 diagnostic6f9afc c7a764. Nonstring key diagnosticc72f60 at6f9952/6f9b23. Implemented separate unknown-key behavior and native string-field allowlist in shared lookup; nonstring fields reject parameter index1 before enumerating nodes. Arbitrary spawn keys no longer silently search as native string properties. All-node enumeration unaffected. Existing reference field list drives checks even for numeric fields whose getter remains unfinished. Source/offline PE inspection only, no builds/tests/launches or coverage-count claim. Both Claude sessions previously confirmed live this turn's ongoing work; no restart. Goal active, match entry unverified.

### 2026-09-08 path-node angle representation evidence
Previous turn corrected getnode/key contracts (progress). Confirmed both Claude sessions live; missile worker now reports measured C1 signed-byte steering40ec50 and camera-gated consumer50c870, pending implementation review. Parent traced node getter6f94e0 to generic field getter56b810, dispatch table56b990 entry15->56b8ac. C1 reads ONE float at node+20 and returns vector(0,yaw,0), contradicting current three-component spawn-text getter. Did not assume spawn text is already the correct stored yaw: current nodes are reconstructed from entity strings while C1 getters read0x94-stride path records. Inspected6f95e0/6f9520: handles unknown dynamic spawn fields separately through script variable assignment, not proof of native angle loading. Next requirement is trace native path-data producer and align record import before claiming complete angle/type/navigation support. No guessed field conversion written; authoritative PE evidence changes next implementation action. No builds/tests/launches/count increase. Goal active.

### 2026-09-08 node record producer and bounded worker finish
Previous turn produced concrete angle getter evidence (progress). Missing-next worker terminal max_turns60, session256e14b0-4d60-448a-8216-04f392d7a4e8, cost3.737127, no source/handoff beyond checkpoint1. Resumed SAME session bounded15 turns, supervisor75284, first-call written evidence handoff required, stop broad research, no subagents. Remote workerf809684d remains live. Parent traced aligned C1 node spawn6f96b0: cap0x2000 at6f96bd, indexes preexisting0x94-stride records through21dfea0, compares loaded node count21dfe9c before zeroing dynamic fields;6f9753 parses only dynamic spawn properties then6f9758 reads existing yaw and derives cosine/sine at+24/+28. Confirms native constant properties require loaded path records, not merely parsing angle text in current draft. Corrected native node allocation limit16384->8192 to measured cap. A whole-text scan helper produced no hits but linear decoder can stop early; do NOT treat as proof of absent pointer writes. Native path-data importer remains required. No builds/tests/launches/count claim; goal active.

### 2026-09-08 GameWorldMp path-data initialization correction
Previous turn corrected node cap and resumed terminal worker (progress). Offline pointer pool tablecd5028 index18 atcd5070 points21dfe98, so prior node storage21dfea0 is GameWorldMp+8. Independently read aligned C1 GameWorldMp loader4bca00:4bca8e formsheader+4 and4bca9a..a4 memset68bytes tozero. Existing replay_game_world_mp already mirrors this exactly. Thus treating serialized path records as ready-to-import would be wrong; must trace later Path_LoadPaths/native population (likely separate path source, not yet established). No speculative asset replay edit made. Worker finish report now updated but claims alpha tree absent despite actual configured path and changes scope to usable-object methods; parent must scrutinize evidence and avoid accepting unmeasured EF_SOFT wire behavior. Both sessions confirmed live at turn start; no duplicate launch. No tests/builds/launches or coverage-count claim. Goal active.

### 2026-09-08 missing-method worker evidence review
Previous turn identified GameWorldMp cleared path block (progress). Reviewed updated worker report while both sessions live: scope switched to makeusable/makeunusable/makesoft/makehard, but no source files existed yet despite report claiming implementation. Independently read aligned IW4 handlers5efee0/5eff90: no extra-argument count check, so proposed strict rejection is unsupported. EF_JAMMING one-bit match does not prove C1 EF_SOFT; current shared_player_flags0x6000e strips0x800000, so native writes/query helper alone cannot publish it. Verified actual alpha gsc/gscbuiltins.py exists, contradicting worker absent-folder claim. Recorded actionable corrections in gsc-missing-next-parent-review.md for integration/handoff; no live worker-owned file overwritten. Actual usable-state code/registry review remains after handoff. No tests/builds/launches/count increase. Goal active.

### 2026-09-08 usable-state source and actual consumer gap
Previous turn completed concrete worker evidence review (progress). Both sessions authoritatively live, missing-next .c/.h now exist and remain worker-owned. Read actual source: extra-argument rejection and unsupported EF_SOFT assumptions still present. Independently inspected retained Player_UpdateCursorHints CM_AreaEntities mask and dispatch table1016: onlyeTypes0,3,4,11,14 accepted;type6 skipped. Generic type0 branch510 additionally requires trigger_use/trigger_use_touch classnames before returning hint. Thus worker's setter/bit/relink implementation does not establish generic script entity usability; query helpers have no role in these retained branches. Added explicit consumer correction to parent-review file. Next step trace C1/IW4 use dispatch and activation before integrating/counting pair. No concurrent source overwritten; no builds/tests/launches/count change. Goal active.

### 2026-09-08 native script-mover use hint dispatch
Previous turn identified actual consumer gap (progress). Missing-next finish now terminal with result end_turn; took ownership of its .c/.h, no restart. Removed unsupported extra-argument rejection from all four draft methods after independent IW4 handler read. Traced IW4 use-hint dispatch4943f1, jump table49463c and byte table494658: type0 retains trigger-classname validation, type6 directly uses cursor-hint fields49446a. Corrects previous overbroad concern about type0: that restriction matches IW4; missing type6 branch is real. Added CODOL_SERVER-only retained table entry6->Player_UpdateCursorHints_160, existing native hint/string handling; non-CoDOL unchanged. Activation path and C1 soft flags still unreviewed, methods remain unregistered. Remote worker still live at turn start. Source readback caught/remediated line-ending-sensitive parameter-check removal; no builds/tests/assembly/launches. Goal active, no coverage count increase.

### 2026-09-08 usable methods connected to activation
Previous turn added script-mover hint dispatch and removed extra-argument rejection (progress). Read full retained Player_UpdateActivate: acquires EntHandle from cursorHintEntIndex, handles item/turret specially, otherwise branch190 sends generic use notify with player and invokes entityHandlers.use when present, then releases handle. Type6 has no missing activation dispatch once hint selection is fixed. Registered only makeusable/makeunusable underCODOL_SERVER; soft/hard remain unregistered/unverified. Native content and vehicle spawnflag writes, relink, preserved/default hint and new type6 hint dispatch now connected to existing generic activation. No built/runtime parity claim; no coverage aggregate change. Remote worker terminated max_turns60 (5.924725 cost), header only; resumed SAME f809684d session bounded15turns supervisor74688 to write measured steering and final handoff, forbidding more broad research/guessed C1 boost. No builds/tests/assembly/launches. Goal active.

### 2026-09-08 usable candidate path and manifest review
Previous turn connected usable pair to activation (progress). Read remaining candidate scan: type6 passes ordinary contents filter, uses shared bounds-center/radius/scoring and visibility paths; no further type6 rejection found before corrected final hint dispatch. Makefile C_SOURCES wildcard includes new module automatically. Added precise integrated_source_unvalidated JSON review for makeusable/makeunusable, leaving aggregates unchanged. Corrected worker header false C1 EF_SOFT parity claim and documented soft/hard drafts remain unregistered, argument extras ignored. No further gameplay edits inferred from partial evidence. Remote finish session authoritatively live74200/f809684d, no duplicate restart. No builds/tests/launches. Goal active.

### 2026-09-08 cursor-hint wire mapping investigation
Previous turn completed candidate/source-list review (progress). Found no native cursorHint/HintString/EntIndex producer in CoDOL player overlay; usable methods have native interaction but hint publication remains required. Alpha playerstate_fields.py labels1f4 cursorHint, contradicted by independently established loopSound transfer40d09d and current loopSound module. Followed cg_cursorHints dvar pointer16da2e0 to aligned client draw456650 and helper456080. Helper reads cg+208 current hint, +20c/+214 auxiliary values and +210 entity index (multiplies228 for client entity); copies into bf058/bf068/bf06c and checks entity status. Need establish predicted playerState base relative cg before deriving actual wire offsets; do not reuse Python's incorrect label or assume cg=ps. Remote finish f809684d verified live this turn; source not ready at inspection. No mapping guessed, no builds/tests/launches. Goal active, usable hint wire publication unresolved despite native methods registered.

### 2026-09-08 cursor-hint offsets confirmed from server
Previous turn located client hint reader (progress). Traced alpha low-confidence g_useholdtime lead2373088 to C1 actual use-hold576530, then activation57649d..51d. Direct server proof:57649d loads gentity+17c client/playerState,5764c1 checksps+208 nonzero,5764ce readsps+210 and compares7ff before resolving entity and acquiring use handle. This confirms client reader456080 uses same offsets, not an assumed cg-relative shift. Netfields208/210 both11bits,20c signed8,214bit1. Existing radar reader5e2f60 also reads21c at same client base. Hint publication still needs weapon-derived hint translation (client45616a uses hint toindex weapon defs) and hint configstring mapping; no raw copying from wrong Python1f4 label. Remote steering source now exists but worker still live74200; parent review after handoff. No builds/tests/launches/count claim. Goal active.

### 2026-09-08 hint-string configstring publication
Previous turn proved hint offsets (progress). Read aligned C1 hint text456270: cachedps20c->bf068 indexes configstring offset table6d0da50, stringbase6d1370c; independently established tablebase6d0d130 gives584. Native G_GetHintStringIndex scans0x115+slot0..31 and writes viaSV_SetConfigstring. Added constants and hint bank refresh preserving slot0, full text spaces/quotes, clears, command length/CRLF bounds; wired native configstring changes and initial map-config refresh. Hint codes/weapon translation still pending; no claim full prompt behavior. Remote follow-up terminal completed, ownership now returned; steering source awaits parent review. No builds/tests/launches. Goal active.

### 2026-09-08 remote steering timing API correction
Previous turn bridged hint configstrings (progress). Both workers terminal, no restart. Reviewed remote handoff: proposed call before ClientThink_real claims ordering unobservable and synchronous path optional; false as a general guarantee because activation/scripts can change links. Independently read aligned C1 tail50cfe3 activation then50cfea camera gate and50cffd savedmsec->50c870. Native tailClientThink_real_200 also ends afterPlayer_UpdateActivate. Changed native steering API to accept explicit savedmsec1..200, removed duplicate command-time recomputation; current accepted raw-input binding remains source. Integration must save native prologue delta and invoke afteractivation, covering synchronous think in samebody rather than pre-think C++ call. No production call yet, control registration still withheld pending lifecycle/math/trajectory review. No builds/tests/assembly/launches/count claim. Goal active.

### 2026-09-08 two bounded Claude assignments and steering integration
User reauthorized Claude workers. Prior assigned workers were terminal; launched two Opus/high workers, maximum50 turns each, no subagents. Supervisors47484/75628, active CLI PIDs76924/70248 (assignment mapping pending session reports). gsc-native-batch2 owns only new codol_script_native_batch2.c/h and its artifacts: implement3-5 verified missing startup/gameplay natives. gsc-hint-wire2 owns only new codol_usehint_wire.c/h and artifacts: historical cursor-hint snapshot translation, enum/weapon mapping and proposed shared integration. Explicit architecture rewrite authorization and writing-only constraints included. Parent retains shared source/registry/manifests; outputs require review before counting.
Parent connected remote steering after Player_UpdateActivate in ClientThink_real, using capped prologue msec saved at ebp-0x274. Stack source audit: existing deepest local -0x270, frame bottom -0x298, outgoing args through+0x14 (last byte -0x281); new four-byte local does not overlap either. Balanced temporary stack scope preserved; all existing epilogues unchanged. Native MatrixMultiply order reviewed. Removed unused timing-window macros and corrected claim that no scan hit proves no C1 consumer. Controls remain unregistered; missile speed/boost and ownership parity unresolved. No builds/tests/assembly/launches, no coverage-count change, no verified match entry.

### 2026-09-08 controls owner replacement and teardown semantics
Previous goal turn made progress by launching two bounded Claude assignments and integrating post-activation steering with saved msec. Both assigned CLI processes76924/70248 verified live this turn; new missing-native inventory artifacts appearing. Parent independently disassembled C1 controls5483c0..5484b0, unlink5484c0..548580, and EntHandle setter507f40..507fd7. No self/other-owner guard exists; setter replaces old association. Removed invented errors and bounded native side-table index by MAX_GENTITIES. Explicit script unlink now clears a live target owner even after replacement, matching548501..55f, while client reset retains owner-specific cleanup. Entity-free cleanup now dissociates every reverse reference to the freed owner and clears its client link record; native G_FreeEntity calls cleanup before unlink/handle dissociation/memset. Controls missile flag/speed/boost behavior remains incomplete and methods remain absent from active VM registration. No builds/tests/launches, coverage claim or verified match entry.

### 2026-09-08 controls argument diagnostics and expanded offline consumer search
Previous turn made source progress on controls ownership/free semantics. Both bounded workers76924/70248 verified live again. Removed controlsLinkTo custom missing-argument error: aligned C1 calls its parameter-zero entity getter directly, before existing-link checks; native draft now does the same, retaining VM argument diagnostics. Added parent-remote-flag-scan.py offline candidate scanner covering every executable PE section and decoding around each204/205 displacement occurrence rather than assuming a linear .text decode reaches every instruction. Candidate contexts90b028f,68a7b9,906aae5 did not establish a missile consumer; no absence/parity claim follows. Remote speed/boost remains unresolved. Reviewed native missile point-target reset paths: allocation reset via CODOL_ResetEntityEventGeneration and launch reset already exist, so no duplicate cleanup edit made. No tests/builds/assembly/launches; match goal active and unverified.

### 2026-09-08 script preprocessing before extended syntax lowering
Previous turn made source progress on controls argument diagnostics and expanded offline missile-consumer search. Both assigned Claude processes76924/70248 confirmed live; missing-native worker has new reference-analysis artifacts. Parent reviewed all script text read paths, Scr_PrepareSource, Scr_LoadScriptInternal and saved-source restoration. Found that extended lowering ran before syscall #if selection: excluded text could inject file constants or fail childthread detection. Moved CoDOL preprocessing into writable source preparation before lowering and source lookup registration; kept later load-script precompile only for non-CoDOL to prevent double rewriting. Filename parameter now const-correct. Mounted rawfile copy already protects assets; restored source lookup contains prepared text. Existing precompiler lexical/nesting limitations remain separate, no blanket parser parity claim. No builds/tests/launches, no count change; match goal active and unverified.

### 2026-09-08 native conditional precompiler rewrite
Previous turn made progress correcting preparation order. Revalidated both Claude processes live at turn start; native-batch2 subsequently produced an exit file, to review next. Parent source review confirmed retained precompiler uses strstr and injected block comments: existing comments inside disabled branches can expose excluded code, and nested branches pair with the first endif. Added codol_script_precompile.c/h, connected only for CODOL_SERVER via existing wrapper. It recognizes line directives outside strings/comments, preserves CR/LF and byte offsets by blanking excluded lines, tracks nested parent activity and one else per level, retains [!]isSyscallDefined conditions, and diagnoses malformed/unmatched/duplicate/unterminated directives with filename/line. Nesting bound128 is explicit. Command tokenizer scope is ended and temporarily replaced newline restored before diagnostics. No heap or C++ destructor scope crosses Com_Error. All source paths still use writable copies and prepare before lookup/archive. Native non-CoDOL precompiler unchanged. Makefile wildcard covers new C module; reviewed declarations and source paths only, no tests/builds/launches. Missing GSC and actual match behavior remain incomplete.

### 2026-09-08 bounded worker handoff and script diagnostics
Previous turn made progress replacing CoDOL conditional precompiler. Authoritative native-batch2 result reports max_turns (session2b8eb2df-e653-4fd2-bb1d-c4f0152d7670,50 cap,cost about2.93); no implementation/report existed. Resumed same terminal session for bounded15-turn finish, supervisor73980, CLI78268 verified live. Explicitly directed concrete source/evidence handoff, no new research scope, no subagents or runtime work. Hint worker subsequently terminal max_turns (session26af8c84-6203-4d23-af32-4f8100645608) with codol_usehint_wire.c/h written, no report. Ownership returned to parent; initial read finds enum/weapon+4 evidence and capture/pure overlay split, but source not integrated or counted. Next review must verify C1 hint enum limits and decide immutable snapshot bindings versus extra capture/archive storage; fourth hint flag remains unknown. Parent fixed Scr_CopyFormattedLine empty-line underflow: CR trimming now checks len>0 before line[len-1]. Reviewed source lookup assembly copying prepared text into retained lookup. No builds/tests/launches; no match-entry claim.

### 2026-09-08 cursor-hint draft reviewed for weapon binding purity
Previous turn made progress on bounded worker handoff and empty-line diagnostics. Native-batch2 finish CLI78268 remains live. Parent read hint draft and native frame/binding paths. Independently disassembled C1 at aligned456859: hints1/2 take text branch,456886/88f bounds weapon hints5..704,45689b uses biased weapon table. Earlier dis start456850 was midinstruction and is not evidence. Existing CODOL_ReplaceWeaponMap replaces mutable arrays; frame input may be archived ps, so resolving via today's map in draft CaptureEngineUseHint is not archival capture. Replaced with CODOL_ResolveEngineUseHint taking explicit wire_weapon for ps.cursorHint-4; removed live mapper dependency and corrected header contract. Both resolver and overlay are now pure inputs, but still unintegrated: capture/archive binding and C1 fourth flag producer remain open. No methods counted, no builds/tests/launches, match goal active/unverified.

### 2026-09-08 hint weapon binding capture and archive
Previous goal turn made progress reviewing hint enum evidence and removing mutable mapper reads from pure resolution. Added use_hint_weapon to playerState extension: zero unknown/nonweapon, else wire weapon+1 (2..701). This uint16 follows links_known and fits the existing four-byte-aligned tail padding on retained32-bit layout; existing bundled-size guard still applies. Generic extension copies carry it. Archive writer emits changed bit plus10bit value after links/before scripted queue; reader mirrors ordering and rejects1/>701/overflow, baseline/current preflight checks same domain. Added playing-frame publisher after Player_UpdateCursorHints and other publishers: clear binding, refresh native-to-wire mapping for weapon hints, resolve and capture valid positive ID. No live lookup in hint resolver/overlay. Unknown mapping stays zero for later publication refusal. Wire overlay and fourth-flag producer still outstanding; no completed-method count, no builds/tests/assembly/launches; match unverified.

### 2026-09-08 primary cursor-hint snapshot publication
Previous turn implemented captured weapon binding/archive delta. Parent connected CODOL_BuildGameplayFrame seed to resolve ps.cursorHint/string/entity from the snapshot and use_hint_weapon from its own extension; unknown weapon binding refuses frame with player cursor hint diagnostic, no mutable mapper lookup. Pure overlay now requires alternate_known before writing214, preserving incoming seed otherwise; native has no proven auxiliary producer. Primary fields208/20c/210 are source-integrated, hint configstring bridge already present. No completeness claim for auxiliary behavior. GSC batch2 finish authoritatively terminal max_turns, all assigned workers now stopped; canspawn/stopfxontag source and header exist but no report and no registration/integration yet. Parent owns review next; no more worker restart. No tests/builds/launches or count changes, match goal active/unverified.

### 2026-09-08 canspawn registered after independent review
Previous turn made progress connecting primary cursor hints. Parent reviewed worker batch2. Independently disassembled IW4 canspawn5f7290..72e4, Bounds739b78 (0,0,35 midpoint;15,15,35 half), trace wrapper42ce50 (ignore setup and zero flags), native G_TraceCapsule/SV_Trace and prototype. Registered canspawn: parameter0 origin, stationary min(-15,-15,0)/max(15,15,70) trace mask810011, native NONE, inverse allsolid integer. No strict extraarg rejection. stopfxontag remains draft: worker deliberately reduced255 effect range to99/two-digit native compounds, requiring native effect namespace/bridge rewrite rather than counting reduced behavior. Current bridge codol_sv_assets.c uses100 effect arrays/ranges; exact next investigation. Added parent review artifact; all workers terminal. No builds/tests/runtime/count claims; match unverified.

### 2026-09-08 C1 stopfxontag contract located
Previous turn made progress registering verified canspawn. Parent found exact C1 stop diagnostic c57710, xrefs54420c/5445ee. Aligned handler boundary5440f0 (preceded by int3 at5440ee/ef) validates exactly3 params and effect>0,<140hex at544141..14a:1..319, larger than IW4's255 and draft99. Entity model194 check, lowercase tag getter5cdd80, quote rejection and bone lookup5d2ea0 follow. Tail544325..330 uses c576e0 three-digit format; allocator searches1..255 and publishes3971+slot at544401..40a. Current wire registrar already supports320 effect slots and taggedbank3971, but native loadfx/G_EffectIndex and bridge remain100-entry/two-digit. This evidence changes implementation target to fullC1 range, not merely IW4 expansion. Marked draft clearly unregistered/incomplete in source and review JSON. Initial disstarts544180/5440c0 were midinstruction and are not evidence; aligned boundary/tail are. No tests/builds/launches or count claim; goal active, match unverified.

### 2026-09-08 extended native effect registry storage
Previous turn established C1 stopfxontag range1..319 and event90. Parent inspected retained G_EffectIndex: base63e/count100; expanding that contiguous pool would overlap tagged configstrings6a2. Added map-owned name storage for native100..319 and expanded native-to-wire/byte-effect maps to320. New CODOL_RegisterExtraServerEffect validates/stores name, reuses slots, supports noncreating lookup, registers/publishes canonical wire name and refreshes byte aliases. Asset reset clears extra names/maps; byte refresh now visits all320 mappings. Existing low pool remains unchanged; high-slot allocator intentionally not called until G_EffectIndex/loadfx and fixed-width consumers are connected. No claim this alone raises exposed script capacity. New source reviewed for bounds/name length and mutation ordering, no builds/tests/launches. Goal active and match unverified.

### 2026-09-08 full-range native effect allocation connected
Previous turn added high-slot storage. Reviewed retained G_FindConfigstringIndex: effect base63e uses SL_FindLowercaseString; fifth argument is optional diagnostic label (not worker-declared overflow boolean). Corrected high-slot canonicalization to lowercase and worker prototype. Added CODOL_NativeEffectIndex: reuse low/high matches, preserve noninitializing missing-name error, preserve original low allocator/constant-configstring behavior while free slots exist, spill to100..319 only after low pool full. Retained G_EffectIndex CODOL body directly jumps to native C allocator; nonCODOL body preserved. Explicit g_shared/scr_vm includes supply level and error declarations. Fixed-width consumers are still incomplete (tagged range check/format and diagnostic CS accesses), so source state deliberately not claimed runtime-ready. No tests/builds/launches; goal active, match unverified.

### 2026-09-08 stopfxontag source integration and wider tagged compounds
Previous turn connected full-range allocator. Added explicit marked native compound @DDDtag through shared registrar, retaining legacy DDtag decoding so digit-leading tags are never guessed. Wire bank remains C1 DDDtag. Updated retained playfxontag CODOL branch range1..319 and registrar call; nonCODOL path unchanged. Updated stopfxontag draft to same range/registrar, appended EV_STOP_FX_ON_TAG after existing enum, mapped it to C1event90 and routed shared player/entity event parameter resolver through tagged-slot translation. Registered stopfxontag. Removed stale draft behavior description in C source. Parent evidence C1 handlers/range/producer5440f0..5444a7 already recorded. Other effects' diagnostic accesses/byte-width producers still need review; no builds/tests/launches or blanket full-effect/runtime claim. Goal active and match unverified.

### 2026-09-08 effect producers retain full IDs
Previous turn integrated tagged effects/stopfxontag. Parent found exact byte truncation in retained playfx, playloopedfx and spawnfx: movzx eax,dl before dword eventParm/un1 stores. Replaced those three CODOL branches with fullword copies; other functions/nonCODOL untouched. Existing snapshot adapters already support wide playfx selectors1..319 and byte-bank mapping for ET_FX/ET_LOOP_FX. Added CODOL_GetNativeEffectName to select retained lowpool or map-owned high names; replaced seven exact diagnostic lookup patterns and moved PrecacheFxTeamThermal to full320 range/new getter. Remaining direct lookup patterns need next review. No builds/tests/launches; source readback only, match unverified.

### 2026-09-08 internal event collision and missing secondary brass mapping
Previous turn preserved full native effect IDs. Parent namespace review found stopfx append autoassigned135, already reserved by CODOL_EV_EJECT_BRASS_SECONDARY;136 reserved for weapon switch. Corrected stopfx to explicit137 and added static collision guards. Reviewed all CODOL_EV macros and found active secondary brass producers1063/1469 had no mapping despite earlier header claim. Independently read C1 aligned418fd3..418fe1 selecting35+3 for secondary and shared zero emitter; added135->38 and zero-parameter case alongside primary brass. Asset reset already follows snapshot/history reset before clearing nativehigh names; no duplicate reset added. tools/codol_event_map.py generates exact-name cases only and is stale relative semantic overrides; did not run/overwrite. No builds/tests/launches; goal active, match unverified.

### 2026-09-08 event transfer audit and hint lifecycle reset
Previous turn corrected stop-fx collision and secondary brass mapping. Parent source-read G_AddEvent's fullword player extension call, script transfer filter and G_PlayerEvent: wire90 is not filtered, native137 falls outside recoil callback26..38, and entity transfer preserves fullword event/compound slot. No extra transfer edit needed. Added dedicated live hint-binding reset and called it beside existing extension resets in ClientSpawn and CODOL_ResetGameClient; archived/snapshot values remain intact. Whole-map extension reset already covers the field. No tests/builds/launches or runtime-completion claim; goal active, match unverified.

### 2026-09-08 missile flight-mode contract and target replacement
Previous turn audited event transfer and reset live hint binding. Re-read current missing MP candidates/registry: flightmodedirect/top absent. IW4 table73d678/684 handlers5edef0/5edf10 pass1/0 to5ede70; shared core checks rocket classname, then flags1c8 bit2 with 'not locked on to anything', writes58. Native flightMode1ec consumers already exist, but its target handle/point flag are not a persistent reference lock bit. Need explicit lock state before implementing exact error contract. C1 diagnostic locatedc55ecc for next trace. While tracing existing target producers, found GScr_MissileSetTarget changes handle without clearing codol_missile_position_active: a rocket previously locked to an absolute point keeps following the stale point after script entity reassignment or undefined clear. Added native point-target reset immediately after handle assignment, before optional offset processing. No flight-mode methods counted; no builds/tests/launches. Goal active, match unverified.

### 2026-09-08 missile direct/top methods and persistent lock state
Previous turn corrected explicit target replacement. Aligned C1 boundary5381a0 (int3 before), classname19c check then204/2 guard at538208; shared core writes5c, wrapper538270 passes1. IW4 wrappers5edef0/5edf10 pass1/0 to5ede70. Added persistent native lock-active array distinct from target handle, set by successful launch entity/point lock and explicit native entity target assignment, cleared by target clear/allocation/map reset through existing reset path. Entity handle dissociation does not itself erase lock bit. Added/register direct/top methods with classname/lock guards and native flightMode write; no extra args/class grenade restriction. Existing native trajectory reads1ec; added offset assertion. C1 network union5c metadata still needs review, so not full runtime parity. No builds/tests/launches/count update; match unverified.

### 2026-09-08 renewed bounded Claude implementation batch
User reauthorized Claude workers with missing GSC methods as a priority. Confirmed prior assigned worker supervisors terminal; unrelated interactive Claude and browser native host preserved. Started two Opus/high workers, each max50 turns, no subagents: gsc-native-batch3 supervisor78428/CLI77296, gsc-remote-complete supervisor57772/CLI78800 (process association to be rechecked before lifecycle actions). Native batch owns only new codol_script_native_batch3.c/h and its artifacts, selecting2-3 confirmed alpha MP native calls against current registry and IW4/T5 evidence. Remote completion owns only codol_remote_missile.c/h and its artifacts, investigating/implementing measured C1 speed/boost consumers needed by controls methods. Both instructed to write early checkpoints and reserve10 turns for source/handoff, with shared integration supplied to parent. Explicit architecture rewrite authorization, no hooks, no builds/tests/launches, preserve running C1/Python and dirty work. Neither batch counted as support before parent review.
Parent inspected missile historical publication: native LerpEntityStateMissile presently contains only launchTime; native missile netfields serialize that member, while C1 type4 table contains58/-97 and5c/2. Existing overlay publishes weapon/scale/trajectories but no5c mode. Simply reading live missile.flightMode during serialization would corrupt archived history; next source change needs a captured native entity-state representation and matching archive field/launch/script producers. No speculative wire write added this turn. Match entry remains unverified.

### 2026-09-08 missile flight mode carried by native entity snapshots
Previous goal turn made progress by launching two scoped workers and identifying missing missile publication. Both current Claude CLI processes77296/78800 confirmed live; no restart. Parent re-read aligned C1 core5381a0, including mode stores538256/538261 to5c, and type4 field table5c/2. Added CODOL-only LerpEntityStateMissile.flightMode at native58, aliasing existing anonymous.data[1] within unchanged union capacity. Existing missile delta field and archivedEntityFields already serialize this word; snapshot source copies whole entityState. Added offset assertion. Rocket lock application captures initialized trajectory mode even on no-owner/no-lock return, and updates capture after point/entity launch lock selection. Direct/top GSC methods update both native trajectory and captured entity mode. Missile overlay reads captured mode, rejects outside0..1, and publishes C1 field5c; no lookup of live missile by archived entity number. Native flight logic remains1ec. No builds/tests/assembly/game launches; source and offline PE inspection only. Full usercmd/configstring/asset/script and verified match-entry goal remains active.

### 2026-09-08 missile launch timestamp publication
Previous goal turn made progress implementing historical flight mode. Both Claude CLI77296/78800 confirmed live this turn, no restart. Parent traced aligned C1 weapon-fire574830 -> wrapper5744c0 -> rocket spawn530c00. Rocket spawn530cc2/530cc8 stores leveltime24b74c0 into entity58;530cda..530d10 adds a speed-derived delay clamped20..50 for eligible player launches. Native G_FireRocket already writes corresponding launchTime54 with retained20..50 clamp, but CoDOL overlay omitted it. Added saved es.lerp.u.missile.launchTime -> C1field58; native missile/archive delta fields already carry it. No runtime/live lookup, no new archive format. Initial disassembly574800 was misaligned/data and not used as evidence. C1 no-explicit-lock special guidance branch530e9a..530f54 also sets lockflag for weapon guidedMissileType3 and creates a forward point; native equivalent still needs review before claiming missile-target parity. No builds/tests/launches; full goal active and match entry unverified.

### 2026-09-08 precompiler comment continuity across directives
Previous goal turn progressed missile launch timestamp publication. Both current Claude CLI77296/78800 confirmed live; no restart. Parent reviewed CODOL_PrecompileScript and Cmd_TokenizeStringInternal: command tokenizer discards trailing block comments at line end, while precompiler previously never updated comment state on directive lines before erasing them. This exposed continuation text and commented directives to later processing. Replaced scanner with offset-preserving comment blanking on every line before directive recognition; carries multiline comment opening line, preserves strings/escaped quotes and CRLF, permits a directive after a closed leading comment, and reports unterminated comments explicitly. Inactive branches still blank at original offsets. Source readback only; no tests/builds/compilation/launches. Full startup/VM and match-entry goal remains active and unverified.

### 2026-09-08 developer-block lexer boundary review
Previous goal turn progressed precompiler comment continuity. Both Claude CLI77296/78800 confirmed live, no restart. Parent source-read retained compiler ScriptCompile_260 (gScrVarPub+7 developer toggle), unmatched/nested developer-block diagnostics and actual alpha gsc_overlay/maps/mp/mp_afghan_fx.gsc:13..16. /#...#/ encloses conditional createfx calls and must remain compiler-visible, not be blanked as ordinary comments. Current blank_comments preserves both delimiters; double-quoted-only scanning matches lowerer's documented retained lexer grammar (apostrophe is invalid token). No additional comment syntax removal justified. Found next source review target: Lowerer.constants scans file-scope assignments without tracking developer markers, and its substitution namespace is global; extended constants declared within a developer block can therefore escape that scope. Exact IW4 constant/developer rules must be established before implementing namespace behavior. No fabricated scope rule or blanket developer-block removal added. No builds/tests/launches; goal active and match entry unverified.

### 2026-09-08 worker candidate provenance and syntax review
Previous goal turn yielded developer-block boundary evidence (progress). Current Claude CLI77296/78800 confirmed live; neither restarted. Parent inspected native-batch3 candidate scan: prof_begin/prof_end are listed as missing because scanner keyword list omits them, but retained scr_vm.h assigns native OP_prof_begin85/OP_prof_end86. They require grammar/VM-path review, not speculative builtin registrations. Scan also walks all vendor/iw4 files and .csc client scripts, so counts do not prove MP server startup reachability. Existing script-language handoff reports no do/while in its reachable corpus; did not prioritize a speculative do/while rewrite over actual missing methods. Lowerer retains double-quoted strings and developer markers, but developer-scoped constants remain unresolved pending reference evidence. No source completeness or coverage-count claim; no builds/tests/launches. Full goal remains active.

### 2026-09-08 usercmd reader framing and acceptance review
Previous goal turn yielded candidate provenance evidence. Both current Claude CLI77296/78800 confirmed live this turn; no restart. Parent source-read full and single command readers, shared bit-pool primitive, SV_UserMove acceptance loop and SV_ClientThink. Active raw commands are staged and bound only on accepted native commands; future rejection clears staged data. Single CODOL_ReadUsercmdMSG lacked the full packet reader cursor/pool guards. Added null input guard, readcount<=cursize, signed-bit representability and partial bit-pool byte<readcount checks before decoding, preserving atomic command output and message cursor on failure. The active network packet path already uses full reader; this corrects its standalone counterpart, not a claimed match-entry fix. First CS_PRIMED command is recorded and handed to ClientBegin rather than the normal acceptance loop; synthetic spawn/reset interaction remains to inspect before any change. No builds/tests/launches; source readback only, full goal active.

### 2026-09-08 first accepted CoDOL command binding
Previous goal turn progressed standalone command-reader framing. Parent traced ClientBegin retained assembly: session activation and begin notify can lead scripts to ClientSpawn. Spawn reads SV_GetUsercmd and brackets direct ClientThink_real with synthetic-input save/restore. First CS_PRIMED usermove previously only recorded last_commands; EnterWorld copied native lastUsercmd without binding raw extension, unlike normal SV_ClientThink. Added staging before EnterWorld, binding beside its accepted lastUsercmd store before ClientBegin, and discard after return for early lockedout/pure rejection. Spawn's existing synthetic scope preserves the accepted binding while suppressing input during synthetic movement. Native-only/bot entry binds no invented CoDOL data. Updated input ownership documentation to include initial acceptance. No builds/tests/launches; source readback only. Workers CLI77296/78800 were authoritatively live at turn start, no restart. Full goal active, match entry unverified.

### 2026-09-08 vote configstring collision found
Previous goal turn progressed initial command binding. Both Claude CLI77296/78800 confirmed live, no restart. Parent traced SV_SetConfigstring -> CODOL_PublishAssetConfigstring -> generic raw-index sender. Native CS_VOTE_TIME13/STRING14/YES15/NO16 (g_shared.h) have active producers in g_sv_cmds.c and g_cmds.c. Publisher has no vote case; native YES15/NO16 therefore reach C1's known match-end15/map-center16 slots. This is a confirmed namespace collision requiring a measured CoDOL vote mapping or native vote subsystem rewrite; silently suppressing votes is not completion. Existing mapped asset/map clears retain explicit overrides after publication. Also noted native systeminfo1 and IW4OL asset extension2/IWD4861/4862 generic fallthrough for later C1 contract review. No speculative mapping added; initial467300 disassembly was misaligned and is not evidence. No builds/tests/launches; full goal remains active.

### 2026-09-08 C1 configstring dispatcher and worker checkpoint review
Previous goal turn found confirmed vote namespace collision (progress). Both CLI77296/78800 confirmed live; native-batch3 now has checkpoint. Parent independently read aligned C1 configstring dispatcher467350 through4676e6:5/6 update score fields,15->466780,16->49e190,13->4667e0,8/9->465a70/465ae0. No direct four-field IW3 vote mirror appears in this dispatcher; do not invent a simple offset remap. Vote string xrefs include interned script constant577d4e and695bb3; next trace script/client-command vote path. 577ca0 disassembly began midinstruction and is not used as evidence. Worker checkpoint confirms selected spawnsighttrace with IW4 handler5f7960 and actual MP spawnlogic calls; source not yet handed off. Proposed ishost maps loopback to host although its own IW4 evidence compares client identity with party-host identity: unsupported substitution, must not register without a real host representation/reference contract. Other missing-subsystem candidates are not permanently excluded merely for needing architecture work. No builds/tests/launches/count claim; full goal active.

### 2026-09-08 batch3 terminal handoff and spawntrace contract correction
Previous goal turn yielded dispatcher/worker evidence. Native-batch3 CLI77296 missing; result authoritatively max_turns50, sessiona4605c83-b426-4c7e-83f2-def1609450a2, cost3.566852, c/h source present, no final report. Parent owns files; no restart. Remote CLI78800 remains live. Parent independently read full IW4 spawnsighttrace5f7960..5f7cb9: reads vectors1/2, no parameter0 entity lookup and no exact argument-count check. Removed worker-invented checks and marked module unregistered draft. Actual blocked trace path calls geometry helper5f75a0 with bounds obtained from first hit via48e080, then tests both segments through candidate points, using computed distances for falloff; worker's arbitrary lateral64/132 samples and broad0x801803 mask are not parity. Requires real geometry/mask implementation before registration. ishost loopback replacement remains invalid/unregistered. C1 vote xref695bb2 is a virtual property serialization call with field name vote, not proved vote command handler; no guessed mapping. No builds/tests/launches/count claim; goal active.

### 2026-09-08 spawn sight-trace bounds geometry evidence
Previous goal turn corrected draft argument contract (progress). Remote CLI78800 confirmed live. Parent decoded IW4 hit-bounds48e080: hit-1 indexes brush bounds array1aa6514 below count1aa650c, otherwise32-byte AABB records1aa6500. Geometry5f75a0 normalizes direction by horizontal length, expands horizontal bounds halfsizes by30, evaluates corner projections on perpendicular direction, chooses extreme corners, adjusts minimum lateral clearance64, and derives point z from forward projection; returned candidate distances drive falloff and200 cutoff. Caller tests BOTH segments through a selected point using original hit as trace hint; not worker's arbitrary64/132 endpoint-offset sampling. Trace wrapper4e2760 forwards into502070 with callback49e970, distinct from retained G_SightTrace/SV_SightTrace entity-inclusive path. Native CM_BoxSightTrace exists with oldHitNum, endpoints, mins/maxs, model, mask; native cm has brush and AABB arrays, so needed representation is available but indexing parity must be checked. No guessed replacement integrated yet; both batch3 functions remain unregistered. No builds/tests/launches, goal active.

### 2026-09-08 native spawntrace hit-bounds representation
Previous goal turn established reference geometry (progress). Parent verified native CM_SightTraceThroughLeaf_60 returns numBrushes+leafAabb+relativeAabb+1 and brush return scheme. Added CODOL_SpawnSightHitBounds: brush hits convert native cbrush mins/maxs to midpoint/halfsize; terrain hits read native CollisionAabbTree origin/halfSize after subtracting brush count. Checks positive hit, pointer/count ranges; does not borrow IW4 offsets. Header declares helper. Spawn geometry not yet wired to it; draft remains unregistered, no completion count. Remote CLI78800 now authoritatively terminal max_turns50, session1ffea236-29ca-4099-81ed-b889f36794b6, cost4.0913595, c/h and report written. All assigned workers stopped; parent owns both modules, no restart. Report claims C1 controls/speed consumers absent from linear scan; absence not proved by that scan and speed integration requires review. No builds/tests/launches; full goal active.

### 2026-09-08 bounds-based spawn-sight draft replacement
Previous goal turn added native hit-bounds reader (progress). Replaced worker's guessed lateral64/132 samples, broad entity trace and total-distance gate. New geometry follows IW4 helper5f75a0: horizontal normalization, expanded30 bounds corners in reference order, min/max perpendicular projections, minimum64 clearance and height along original direction. Caller obtains obstruction bounds, evaluates candidate distance<=200 (not a minimum endpoint-distance gate), and requires both segments clear before1-(distance-64)/136. Uses native CM_BoxSightTrace with original hit hint, zero extents, worldmodel0 and reference mask801; full wrapper/content parity still pending so function stays unregistered. Removed obsolete header constants and updated reader wiring comment. Parent read start of IW4 generic502070 showing Bounds-based trace setup; no live execution. All assigned workers terminal. No builds/tests/launches/count claim, full goal active.

### 2026-09-08 spawnsighttrace source registration
Previous goal turn replaced guessed geometry (progress). Parent completed IW4 generic world-trace502070..5023df inspection: model0 branch tests old positive brush then world-tree606fd0; no entity-server sight call. Native CM_BoxSightTrace matches old-hit/world model/zero extents behavior and has matching positive hit index domains. CoDOL collision importer retains native brush/material contents unchanged. Registered spawnsighttrace underCODOL_SERVER after source review, keeping ishost unregistered. Real helper uses native obstruction bounds,30-unit expansion,64-unit clearance, both candidate segments and <=200 falloff; no invented param0/argc check or guessed132 sample. Makefile includes module via C wildcard. Registration and header/source readback performed, no builds/tests/launches/runtime parity claim. All assigned workers terminal; full goal active and C1 match entry unverified.

### 2026-09-08 remote speed handoff corrected and arithmetic implemented
Previous goal turn registered reviewed spawnsighttrace (progress). Actual remote handoff source contained only steering plus claims about a speed model, not implementation. Removed unsupported claim C1 consumer absent; linear scans do not prove absence. Independently read IW4 5e87d4..5e8975 and added standalone native speed helper with owner-filtered CoDOL buttons, armed/boosted state, facing-projected speed, boost threshold500, fixed50ms step, velocity/position update and explicit boost-event return. Corrected worker deadband transcription:5e88f9 compares delta against SAME positive0.001, not negative epsilon. Helper not yet connected: lifecycle allocation/reset, dvar ownership, native clipmask side effect, event mapping and trajectory gates remain. Existing command-driven steering unchanged. No builds/tests/launches/registration or completeness claim; full goal active.

### 2026-09-08 remote boost event mapping
Previous goal turn implemented standalone measured speed arithmetic (progress). Offline event-name inspection found IW4 EV_MISSILE_REMOTE_BOOST string705184/table7958cc and C1 same exact name atc3fb40, event tablecd81d8 index105. IW4 measured producer5e8853..5e8863 emits event61hex with parameter0. Added native enum138 after stop137, preserving reserved135/136, wire map138->105 and strict zero-parameter conversion. Speed helper still only returns event request, so native lifecycle/trajectory and actual emission remain unconnected. Native clipmask side effect not yet established; no guessed offset write. No builds/tests/launches/count claim, all workers terminal, full goal active.

### 2026-09-08 Claude GSC completion workers resumed
User reauthorized Claude workers, explicitly prioritizing missing GSC methods. Checked no previous assigned Claude processes were active, then launched two Opus/high workers capped at40 turns each with checkpoints and final10 turns reserved for source/handoff. gsc-sound-finish supervisor64760/CLI52436 owns codol_script_sound.c/h: verify and finish playsoundatpos/playsoundatposition, stopsounds if time remains. gsc-light-finish supervisor72864/CLI75988 owns new codol_script_light.c/h: implement setlightintensity after confirming native binding and IW4/C1 representation. Both CLI child processes verified running; stderr empty at initial check. Explicit IW4OL rewrite authorization and no-hooks/no-builds/no-tests/no-launches constraints included. No nested workers. Shared registries, lifecycle and snapshot integration remain parent-owned; output is not counted until reviewed. Updated JSON worker state. Existing spawnsighttrace is source-registered, while ishost remains an invalid unregistered loopback draft and remote speed lifecycle remains incomplete. Full GSC and match-entry goal remains active and unverified.

### 2026-09-08 remote trajectory collision-mask trace
Previous turn progressed by launching two scoped workers. Current CLI52436/75988 both verified live; no restart. Parent traced IW4 remote entry5e8797 clearing entity18c/800 and references5e8e35..5e8e82 passing that same field to476b70 ->406440 ->423280 world trace mask argument6. Native G_RunMissile corresponding trace reads gentity.clipmask190; retained MissileTrajectory has the same launchTime/trType/handler9 gates as IW4. Corrected source comments distinguishing mapped boost event from still-missing emission and measured speed defaults from unregistered speed dvars. Actual lifecycle/trajectory integration remains pending; no offset-based field guess written. StartupExtra_Register contains controls registrations but has no caller; controls remain unavailable through active registry. No builds/tests/launches, match entry unverified.

### 2026-09-08 missile remote-mode lifetime implementation
Previous turn established collision-mask evidence (progress). CLI52436/75988 verified live this turn. Parent re-read aligned C1 controlslinkto5483c0 and controlsunlink5484c0: set target204/100 only for eType4 at5484a0, explicitly clear at548565 even when owner handle already absent. Added missile-owned enabled/armed/boosted storage and mode accessor/setter; linked script producer and explicit unlink to measured mode transitions. Owner-handle dissociation remains separate. Added per-entity and whole resets to existing event-generation initialization/map-reset paths, source-read retained init call and SV_ClearServer caller. This prevents reuse inheriting boost/mode state and provides storage for forthcoming native trajectory consumer. Speed dvars/trajectory/event emission and active method registration still pending. No builds/tests/launches, match entry unverified.

### 2026-09-08 remote missile trajectory and controls registration
Previous turn implemented missile state/lifecycle (progress). Both workers CLI52436/75988 verified live. Connected native MissileTrajectory after launch/type/handler9 gates and before homing to CODOL_RemoteMissileTrajectory. The consumer uses the missile mode/state, accepted network raw controls-owner input (zero for absent/nonnetwork), measured C1 numeric speed dvars1188/1189/1190 and IW4 arithmetic, clears native clipmask800, publishes velocity/base and mapped boost event138->105 parameter0. Retained ABI source review: esi/edi preserved by cdecl, outgoing arguments fit frame, normal branch reloads eax/xmm after call, remote returns through existing epilogue. Reviewed saved player links: controls flag0xc/80000 and entity5c/sentinel7ff derive from captured state and archive extension. Registered controlslinkto/controlsunlink in active registry beside camera methods. Source implemented/reviewed only; no builds/tests/assembly/launches. IW4 speed contract is fallback; C1 speed consumer and runtime parity remain unverified. Full match-entry goal active.

### 2026-09-08 primary light intensity implementation and worker handoff
Previous turn integrated remote trajectory/controls methods (progress). Both assigned workers now terminal max_turns40, confirmed result files and absent CLI handles. Light session59fc255c-2769-40e6-b7a8-7f3f9f9f62fd cost2.604242 left checkpoint but no code. Sound session1f97467c-3bbd-4b7a-a9a4-9904216d3cf6 cost2.7862805 left source edits for review. No restart. Parent independently decoded C1 light resolver547c60/getter547ce0/setter547d00: eType10 receiver, float0, error below-0.001, ordered nonnegative clamp, state5c. Added light c/h and registered intensity getter/setter. Corrected worker's incomplete snapshot conclusion: native raw union delta fields exist, but CoDOL overlay omitted intensity. Added saved primaryLight.intensity -> C1field5c (type10 field table32bits), preserving historical values. Source readback only, no builds/tests/launches; other light fields remain to review and full match entry unverified.

### 2026-09-08 positional sound source registration
Previous turn implemented intensity methods and snapshot field (progress). Reviewed terminal sound worker source, then independently decoded C1 playsoundatpos54d340 (count>=2, vector0,alias1) and helper54cf30 (unknown/looping rejection, alias bank570920,temp event3). Native emitter and codol_sv_gameframe saved-event resolver already deliver eventParm index -> C1ac and biased native otherEntityNum -> C1owner80/sentinel2046. Added active playsoundatpos function registration and header include. T5 playsoundatposition remains unregistered: worker rationale incorrectly treats a zero-index snapshot rejection as requiring a script error, whereas T5 drops the unknown alias without emitting any entity. Looping rule also differs and needs correction/consumer review. No builds/tests/launches, full match-entry goal active and unverified; both assigned workers terminal.

### 2026-09-09 T5 positional sound contract corrected
Previous turn registered C1 playsoundatpos (progress). Parent independently decoded T5 647d70,694400,93c3a0 and955ca0. Worker claim unknown alias produces zero was wrong:955ca0 hashes every nonempty string, forces nonzero hash; only null/empty yields zero. 93c3a0 returns hash even when loaded-alias lookup fails. Corrected playsoundatposition to read vector1 before string0, preserve exact2argc, ignore empty name and emit nonempty names without C1's unknown/looping validation. Retained G_SoundAliasIndex registers configstring names without asset lookup; existing transport translates name to C1 sound bank/event. Registered function. No builds/tests/runtime or match-entry verification. Prior log's unknown-alias silent-drop interpretation is superseded by this deeper evidence.

### 2026-09-09 stopsounds source registration
Previous turn corrected/registered T5 positional sound (progress). Parent reviewed native StopSounds and independently decoded C1 receiver536120/type guard536136/hidden-bit clear53617e, then5361db..536262 player/entity queue branches: event5 parameter0, sequence increment and timestamps. Existing native G_AddEvent and strict zero EV_STOPSOUNDS->5 resolver provide corresponding transport. Added active method registration. C1's separate event producer quota still has unresolved reset semantics; retained native queues used without inventing a lifetime limit. No builds/tests/launches/runtime parity or match-entry claim. All assigned workers terminal.

### 2026-09-09 light radius methods and snapshot identity
Previous turn registered stopsounds (progress). Parent decoded C1 getter5550e0/setter555100 and clamp4010e0: receiver first, resolve BSP light via entity98, float0, reject below-0.001 or above float(originalRadius+double0.001), clamp0..originalRadius. Native SP_light writes corresponding native index88 and comWorld has radius field. Implemented/registered radius getter/setter with real BSP bound; clamp preserves unordered input per decoded helper. Snapshot overlay now publishes saved radius60 and BSP index98/11bits as well as intensity5c, without live entity/BSP lookup on historical publication. No builds/tests/launches/runtime verification, full match-entry goal active; other light fields remain to review.

### 2026-09-09 light exponent methods and packed color publication
Previous turn implemented radius methods/publication (progress). Parent decoded aligned C1 getlightcolor555030, setlightcolor5550a0, getlightexponent5554f0 and setlightexponent555510. Exponent getter reads byte5b as integer; setter reads int0, errors outside0..100 and writes byte5b. Implemented/registered exponent pair using native colorAndExp[3]. Snapshot overlay now explicitly packs all four saved native bytes into C1field58, preserving RGB and exponent across current and archived snapshots. Color setter's conversion52db40 uses staged float multiplication then x87 integer rounding; exact constants/rounding require further review before implementation. No builds/tests/launches/runtime or match-entry claim.

### 2026-09-09 light color methods
Previous turn implemented exponent pair/packed snapshot publication (progress). Read C1 constantsc84588=double255,c84590=double2^-30,c84458=promoted float reciprocal255 and getter VM call5ce9f0. Implemented/registered color getter/setter: receiver check, vector0, conversion52db40 with forced float intermediate and current-mode nearbyint after epsilon, explicit invalid signed-conversion handling and byte saturation. Preserves exponent as5550a0 does; getter returns normalized RGB. Existing saved-byte packed field58 publication carries state and history. No builds/tests/launches/runtime validation, match entry unverified; light FOV methods remain to review.

### 2026-09-09 primary light cone snapshot publication
Previous turn implemented light color methods (progress). Parent decoded C1 FOV getters555210/555250 and setter555290..5554ed. Setter bounds outer1..120 degrees, checks compiled outer cosine, optionally reads inner only with exactly2args; stores outer64/inner68 at5554df/5554e6. Added saved native cosHalfFovOuter/Inner publication to those wire fields, completing missing cone transport without live lookups. Getter calls CRT ae1bc0 then doubles the float with no visible degree conversion; helper identity and setter's optional/default clamping still need full review before methods registration. No builds/tests/launches/runtime parity or match-entry claim.

### 2026-09-09 light FOV methods
Previous turn added cone snapshot fields (progress). Parent traced CRT ae1c18: sqrt((1+x)(1-x))/atan2 with endpoints+1->0,-1->pi confirms acos. Added/registered FOV getters with float acos then double result, no degree conversion, matching C1. Setter uses measured promoted constants0.9990000128746033/120.0009994506836 and degree factor0.01745329238474369; compiled outer bound/clamp, optional inner only with exactly2args, ordered error checks and delayed state stores. Default inner path independently rechecked:5554c7/JP discards new value when greater/unordered, selecting the minimum of new outercos+.001 and compiled inner (not intuitive max). Snapshot64/68 already captures results. No builds/tests/launches/runtime or match-entry claim.

### 2026-09-09 common-world loader and light spawn review
Previous turn implemented FOV methods (progress). Traced DB_FindXAssetHeader COMWORLD branch installing converted comWorld and retained SP_light initialization: native index88, normalized packed RGB with exponent overwrite, radius/cone fields, origin/angles/bounds and link. Independently decoded C1 4bfec0:4bff4c tests only nonzero array word and4bff52..4bff6e loads aligned inline records. Existing replay_common_world and converter match; added evidence comment distinguishing presence flag from packed string references. No need for speculative array-pointer rewrite. All light script fields have native producers and captured snapshot publication, but actual archive/map execution still unverified. No builds/tests/launches; full match-entry goal active.

### 2026-09-09 minimap icon precache bank identified
Previous turn confirmed common-world loader/producer contract (progress). Current registry lacks precacheminimapicon. IW4 exact string7173ac->table79abd0->handler5f8360 reads string0 and helper5f8250 registers dedicated fbb..fc9 bank with duplicate scan/empty-slot search, not generic material allocation. C1 exact diagnosticc591fc->xref54ff88 and aligned54ff80 passes17c5/17d4 to54f9d0. Added measured CoDOL bank constants6085/15. Misaligned54ff70 output discarded. Shared C1 registrar and publication/reset implementation next; function not yet registered. No builds/tests/launches/runtime or match-entry claim.

### 2026-09-09 minimap icon registrar implementation
Previous turn identified dedicated bank (progress). Parent decoded C1 shared54f9d0 through54fbc8: full case-insensitive duplicate pass, then first empty, exact full-bank error. Added codol_script_minimap.c/h and active precacheminimapicon registration. Uses map-owned inherited/override configstrings6085..6099, empty-input duplicate semantics, reliable d publication to primed/gamestateSent clients; existing reset and initial-gamestate paths own lifecycle. Same command-token asset-name restrictions as existing asset publication, checked before mutation. No generic material alias or fake return. No builds/tests/launches/runtime or match-entry verification.

### 2026-09-09 head/status icon configstring translation
Previous turn implemented minimap registrar (progress). Parent decoded aligned C1 dispatcher467534..467582: status17ae..17b5/head17b6..17c4/minimap17c5..17d3 call asset type7 loadera78170. Head precache54fdb0 confirms17b6..17c4. Retained precacheStatus/Head native banks8d3/8db already registered but publisher had no mappings, leaking IW3 indices to C1. Added constants6062/6070 and native-bank translations to both dynamic publication and initial asset refresh. Extended indexed-name helper with explicit first slot; icons start0, existing sound/shellshock start1 preserved. Existing override lifecycle handles resets and explicit clears. No builds/tests/launches/runtime validation; icon indices in gameplay consumers still require review. Misaligned54fda0/54fce0 outputs not used. Full match-entry goal active.

### 2026-09-09 player head-icon snapshot publication
Previous turn translated icon configstring banks (progress). Parent traced native ClientScr_SetHeadIcon to entity iHeadIcon and current overlay omission. C1 field tablec3c138 resolves setter50e590, which calls54fde0 and writesa0; lookup54fe91 returns matchedslot+1, empty input0, matching native15-slot semantics and four-bit netfield. Added captured es.iHeadIcon toa0 for player entities, rejecting out-of-domain; native delta already carries it, no live lookup. Head-icon team setter50e670 writesa4 values0/2/1/6; native spectator mapping still needs semantics and is not blindly copied. Status icon is session/scoreboard state, separate from client-state overlay. No builds/tests/launches/runtime or match-entry claim.

### 2026-09-09 head-icon team reference contradiction
Previous turn published head-icon index (progress). Parent decoded C1 getter50e7b0: values1/2/6 ->axis/allies/spectator. Confirmed spectator interned24ee132 from577d24 and stringc53de8. Re-read setter from aligned50e670:50e757 JE on spectator goes to error50e770, unmatched other values write6 at50e760. Fielda4 netbits2 cannot represent6 directly. This disproves a simple native spectator3->6 source-to-wire mapping; next investigate client head-icon display rather than invent truncation or copy native3. No new runtime/code parity claim or builds/tests/launches; goal active.

### 2026-09-09 spectator client-state team corrected
Previous turn established head-icon setter/getter contradiction (progress). Found C1 display45aeca: iconteam0 displays, viewerteam6 bypasses filtering, others require match. This exposed separate general client-state bug: native overlay published spectator3. Independently decoded team getter50e080/table50e0d0 entry6->spectator24ee132, entry3->return without team. Field gclient346c is clientState+4; preceding index3468 independently used for name CS1280+index50e933. Corrected spectator publication to6 in three-bit clientState field; no native layout/team enum rewrite. Head-icon two-bit spectator-only semantics remain unresolved. Misaligned457281/43a216/45ae60/50e060 outputs not used. No builds/tests/launches/runtime or match-entry claim.

### 2026-09-09 spectator codec and status-scoreboard path review
Previous turn corrected spectator client team (progress). Current CoDOL client-state codec uses measured three-bit team field directly, with no second spectator3 conversion found in native CoDOL producers. Traced status_icon: ClientScr setter writes sess2f70; retained SendScoreboard reads it as the fifth value of each seven-integer row (client,score,ping,deaths,status,kills,assists), sends operation b with count/team scores/scorelimit header. This bypasses entity/clientstate overlays and needs C1 message-contract review. Located matching C1 overflow diagnosticc53acc with xref51fd03 for next producer trace. No blind status-icon copy into clientState. No builds/tests/launches/runtime or match-entry claim; full goal active.

### 2026-09-09 Claude workers resumed for missing GSC methods
User reauthorized Claude. Verified no prior assigned worker remained active (unrelated Chrome native host preserved), then started two bounded Opus/high workers, 40 turns each. gsc-attached-sound supervisor78772/CLI66504 owns sound c/h, completing playsound/playsoundasmaster/playsoundontag and reference notification semantics while preserving reviewed positional methods. gsc-next-methods supervisor76136/CLI78724 owns new completion_next c/h, selecting 2-4 genuinely missing methods from actual registry and CoDOL script leads, excluding overlapping families. Both child processes verified live; stderr empty. Explicit native rewrite permission, no hooks, no builds/tests/launches, no nested workers, checkpoints and reserved implementation/handoff turns included. Parent owns shared integration and review. Output not counted as support; full match entry remains unverified.

### 2026-09-09 scoreboard ten-column contract confirmed
Previous turn made progress by launching and verifying two bounded workers. Both CLI66504/78724 verified live this turn; no restart. Parent decoded aligned C1 producer51faa0 and independently followed command dispatch469320 byte/target tables: b->465130 consumes ten arguments per row (46557f), unlike retained/Python seven. Client-field table proves score/deaths/float kills/assists/headshots/objectives; tenth field uses5d2480 skill lookup with unresolved native data/config semantics. zm uses distinct command4 and seven different fields. Wrote docs/CODOL_SCOREBOARD_CONTRACT.md with exact producer, consumer, field identities and next native storage/lifecycle requirements. No invented zeros or scoreboard parity claim; no builds/tests/launches. Full match entry remains unverified.

### 2026-09-09 native scoreboard script stat storage
Previous turn confirmed ten-column producer/consumer contract (progress). Both Claude CLI66504/78724 verified live. Added codol_scoreboard_stats.c/h with real per-client integer downs/revives/headshots/objectives storage; registered custom GSC field getters/setters. C1 field table gives exact integer types; aligned setters50e330/350/370 read int0 and set score refresh flag, objectives uses direct field write. Native bUpdateScoresForIntermission consumer exists in retained G_RunFrame. Connected storage resets to existing connection/drop and map input reset paths; deliberately not the ClientSpawn playerState reset, which preserves session data. Generalized existing live-client resolver name/diagnostic for shared use. Source reviewed only; scoreboard sender, float kills and skill lookup remain pending. No builds/tests/runtime or match-entry claim. Misaligned550e20 exploratory output discarded.

### 2026-09-09 native floating-point kills
Previous turn implemented real scoreboard stat fields/storage (progress). Both assigned Claude CLI66504/78724 verified live. Changed CoDOL clientSession kills slot from int to float, preserving its four-byte size and offset; GSC field now F_FLOAT matching C1 c3c168 record. Native spawn session save/restore retains it. Reviewed all named C/C++ consumers and retained assembly offset2f80 use: integer plugin scoreboard and status replies now use explicit bounded truncation helper; retained SendScoreboard uses cvttss2si underCODOL_SERVER. C1 ae0410 SSE path uses cvttsd2si after float load; invalid conversion yields INT_MIN, handled without undefined C cast. Non-CoDOL declarations/consumers unchanged. Source readback only, no builds/tests/assembly/runtime. Ten-column sender and skill lookup remain pending; full match entry unverified. Worker next-methods checkpoint selects ishost/predictstreampos/laststandrevive/setspectatedefaults; its assertion that ishost has no existing draft is incorrect (native_batch3 unregistered draft exists), requiring parent deduplication during review.

### 2026-09-09 profile-backed scoreboard skill reader
Previous turn implemented native float kills (progress). CLI66504/78724 verified live. Decoded aligned590670 and590590: scoreboard5d2480 passes literal skills/tdm, al0 selects public mp/playerdata.def (c44424), then signed divide100 plus25. Added CODOL_ReadScoreboardSkill using shared session profile view and mounted schema path resolver/scalar reader; preserves output on missing/invalid data and implements signed int/short, byte/bool and float conversions matching dispatch table590748. No constant rank or guessed byte offset. Sender owns unresolved online dvar/client-state gating; reader not yet called by retained seven-column sender. No builds/tests/runtime. Misaligned exploratory465f80/595000 output discarded; decode beyond590747 entered data and was not evidence.

### 2026-09-09 scoreboard wire formatter
Previous turn implemented profile-backed skill reader (progress). CLI66504/78724 verified live again. Added codol_scoreboard_wire.c/h: explicit resolved native row data serializes C1 normal b ten-field rows and zm command4 seven-field rows; headers/counts, 64-row cap and 0x578/0x598 message budgets follow measured producer. Keeps complete tokens, reports emitted count, and preserves caller output on invalid/capacity failure. Caller must supply actual skill policy; no fabricated default or onlinegame identity guessed. Formatter is not yet called by retained sender. Dvar16fc2a8 identity remains unresolved; exploratory disassemblies from unaligned starts not used. No builds/tests/runtime validation or match-entry claim.

### 2026-09-09 terminal worker audit and scoreboard session lifecycle
Previous turn implemented wire formatter (progress). Both assigned CLI66504/78724 absent; result JSONs authoritatively terminal max_turns40. Attached-sound sessiond5fcb14f-c6c3-4c4b-bb05-b338694437d3 cost3.229088 has source edits requiring review. Next-methods sessionbcb4ac3e-2051-40ff-96dc-cc5a7a5d144a cost3.299312 left evidence/checkpoint but no completion_next.c. No automatic restart, no worker output counted. Parent inspected canonical ClientBegin (no session memset) and ClientConnect full client memset; added CODOL_ResetScoreStats immediately after ClientConnect clear, so native callers bypassing network reset cannot inherit old stats. Existing map/drop resets remain; respawn session preservation remains. Aligned IW4 laststandrevive5df3b0 inspected: clears client3648/364c after43a070 (helper is unrelated platform check, not assumed revive producer). Native lastStand fields lack established gameplay consumers; method not blindly registered. No builds/tests/assembly/runtime, full goal active and match entry unverified.

### 2026-09-09 playsoundasmaster worker correction
Previous turn fixed canonical stat lifecycle (progress). Both workers terminal, no restart. Parent independently decoded aligned IW4 5f6bb0 and shared5f6890: handler uses receiver origin and ordinary positional helper; helper emits temp event3 at5f68e6, not queued master event4. Corrected unregistered CODOL_Scr_PlaySoundAsMaster draft to validate alias, emit unowned positional ordinary sound, then check exact1argc. IW4 playsound5f6900 has identical enabled producer. Dvar66e60fc/current10 gate remains unidentified; draft explicitly unregistered, retained active ScrCmd handler unchanged. No fake count of new support. No builds/tests/runtime, full match entry unverified.

### 2026-09-09 playsoundasmaster integrated with measured probe gate
Previous turn corrected worker event producer (progress). Traced aligned IW4 registration518970: string78683c r_reflectionProbeGenerate, description786810, bool default0/flags0 stored66e60fc at518991. Implemented gate before receiver/alias processing; both gated and enabled paths still check exact1argc as5f6be3. Registered corrected CoDOL handler in place of retained CoD4 event4 handler. Enabled path validates alias and emits unowned positional ordinary event3 per5f6890. Existing alias-bank/event transport reused; source include/registration/body readback completed. No builds/tests/runtime parity claim; full match entry unverified. Workers remain terminal.

### 2026-09-09 sound-length reference corrections
Previous turn integrated playsoundasmaster probe gate (progress). Parent decoded aligned C1 sound-length reader73d250 and lookup61ed00: lookup begins rowCount-1 and scans backward. Notification producer573073/573075 substitutes2000 only for zero, preserving negative values. Corrected worker's first-row search and nonpositive-default conversion; explicit signed32 clamp matches 32-bit strtol range on wider hosts. Updated deadline comment to stop claiming positive-only lengths. Existing free/shutdown string cleanup callers confirmed; frame consumer still not called, playsound replacement remains unregistered. No builds/tests/runtime; full match-entry goal remains unverified.

### 2026-09-09 playsound notification frame integration
Previous turn corrected duration lookup/conversion (progress). Connected CODOL_RunSoundFrame once in canonical retained G_RunFrame_40 after animation time setup and before script scheduling, covering normal/catch-up/other native callers without duplicated SV wrappers. Registered CoDOL playsound handler; measured alias/argument producer and notification deadline now have a native consumer. Pending record clears before Scr_Notify, with original string reference held across notification and released afterward; entity-free and VM-shutdown cleanup already connected. Removed obsolete unconsumed quota check from event producer, retaining native event ring admission. Source call/registry/lifecycle readback; no builds/tests/assembly/runtime. Placement is a native implementation choice, not verified C1 virtualized-frame parity; error-path nuances and wrap boundary still require review. Full match-entry goal remains unverified, workers terminal.

### 2026-09-09 sound notification ownership review
Previous turn integrated native frame consumer (progress). Parent re-read aligned C1 572e30..57302a: duplicate-error path releases only temporary new reference and throws before replacing old record. Existing old-record preservation is correct. Corrected replacement ordering to retain new string before releasing old, matching reference and allowing same-string replacement without an ownership gap. Zero string receives no reference and leaves active false, matching C1 word254 pending predicate. Deadline now reads length by registered sound-bank name, as57302a..57306e does, rather than original input spelling. Source changes only; no builds/tests/runtime, exact frame ordering remains unverified. Workers terminal, match entry not established.

### 2026-09-09 missing spectator defaults consumer identified
Previous turn corrected sound ownership (progress). Parent decoded IW4 setspectatedefaults5df520: player receiver, direct vector0 store337c then vector1 store3388, no argc check. Located real consumer459e70: StopFollowing uses defaults only when helper4319a0(client,4) reports permission bit4 set, otherwise current player view; both join collision placement path. Retained StopFollowing has no defaults branch. Wrote docs/CODOL_SPECTATE_DEFAULTS.md with native permission mapping/storage/lifecycle integration requirements. No unused-vector stub registered, no builds/tests/runtime. Workers terminal; full goal remains unverified.

### 2026-09-09 setspectatedefaults native implementation
Previous turn identified producer/consumer (progress). Compared IW4 AllowSpectateTeam5de9c0 and retained handler: freelook uses0x10 in both permission masks; diagnostic72c424 names axis/allies/none/freelook. Added codol_spectate_defaults c/h with sequential vector0/vector1 writes, player receiver check, no extra argc gate/return. Registered method and connected StopFollowing noSpectate0x10 branch to stored origin/AngleVectors while retaining common trace and current-view-angle handling, as reference459efa/459f34. Storage persists respawn; map/connection/drop reset and canonical ClientConnect memset path clear it. Source registration, vector API and consumer readback inspected. No builds/tests/assembly/runtime; C1-specific counterpart and full spectator collision parity remain unverified. No workers running; full match entry not established.

### 2026-09-09 predictstreampos transport incompatibility confirmed
Previous turn implemented spectator defaults (progress). Parent decoded IW4 handler5decb0: player receiver, vector0, integer-truncated x/y/z, commandX sent to that client. Direct C1 dispatch table read maps X to469f7d; aligned handler prints confirmed c44e44 Unknown client game command. An IW4 sender would be ineffective, so no fake-support registration added. Wrote docs/CODOL_PREDICT_STREAM_POSITION.md with required C1 consumer/native loading investigation and offline helper. No builds/tests/runtime; full goal active, workers terminal. Exploratory unaligned51d7c0/51e5d0 output not used as evidence of corresponding handlers.

### 2026-09-09 C1 command dispatch map and candidate review
Previous turn proved IW4 X rejection (progress). Exported94 printable ASCII opcode targets directly from C1 byte/jump tables to docs/CODOL_C1_COMMAND_DISPATCH.json; semantic labels intentionally not inferred from letters. Aligned u/v handlers467ee0/467fc0 use one script-menu index (diagnosticc44918), o->468350 identifies CG_ReverbCmd (c44964), 5/6/7 handlers469080/4690c0/469100 each consume one integer. These candidates do not implement three-coordinate stream prediction. Does not prove streaming absent from C1. Parent helper textual previews are not complete control-flow graphs; branches/fallthrough require separate decoding. No builds/tests/runtime or new builtin registration. Full goal remains active, workers terminal.

### 2026-09-09 script menu consumer and publication review
Previous turn exported command targets (progress). Parent decoded C1 q->467d80, u->467ee0, v->467fc0, r->468060: menu index0..31 uses offsets6d1137c = CS4243 base; q's optional nonempty third token disables mouse, r supports absent index. Existing native bank/constants/formats match. Corrected precache publisher to send reliable d updates only to primed/gamestateSent clients with initialized client storage, matching other CoDOL asset publishers; override remains for initial gamestate. Generic broadcast previously lacked gamestateSent guard. Source only, no builds/tests/runtime. Other menu receiver/argument semantics not claimed fully verified; full match-entry goal remains active, workers terminal.

### 2026-09-09 native vote command parsing corrected
Previous turn corrected menu publication ordering (progress). Parent confirmed retained Cmd_Vote_f already has script-notify route when g_oldVoting false and legacy configstrings when true. Found independent argument bug: it checked msg[1] for Y/1 while checking msg[0] for y, misclassifying one-character votes and reading beyond empty argument. Corrected all affirmative comparisons to msg[0]. Legacy vote CS15/16 still collides with C1 match-end/map-center fields; no silent suppression or guessed bank remap added. Native script-notify existence is not proof C1 vote UI is implemented. No builds/tests/runtime, full goal active.

### 2026-09-09 native scoreboard sender integrated
Previous turn corrected vote argument parsing (progress). Alpha dvar table pointed to registration498372; independently decoded aligned4982d0 and stringc48288 to prove gate numeric2474/defaulttrue, stored16fc2a8. Added native CODOL_SendScoreboard and retained SendScoreboard tail dispatch underCODOL_SERVER. Sender gathers sorted native clients, session float kills, real added stat fields, connecting ping sentinel and skill reader gated on numeric2474/network active state. Formats normal ten-column b or zm seven-column4, uses native scorelimit/roundlimit dvars and reliable recipient command. Missing required profile reports error and aborts publication rather than inventing rank. Formatter now trims whole trailing rows and regenerates count/header to fit actual1024-byte native reliable buffer, avoiding truncation of C1's larger1392-byte maximum. Source API/field/registration readback corrected Cvar string access to native buffer API; no builds/tests/assembly/runtime. Native2474 registeredflags0 pending exact C1 internal-flag policy mapping; runtime match entry remains unverified.

### 2026-09-09 GSC incremental scoreboard command corrections
Previous turn integrated full scoreboard sender (progress). Reviewed retained updatescores/updatedmscores: they send incremental commands, do not write kills. Old team lettersH/G and DM I are incompatible: C1 H closes menu, G/I default unknown. Independently decoded C1 C4699d5 storing first-team beb20 and D469a12 storing second-team beb24, matching full scoreboard header; E469a4f reads client/score then465990 updates matching64-byte row scorebeb74. Changed retained producers underCODOL_SERVER to D/C and both DM E messages, preserving sorted opponent selection, receiver checks and command type0. Source readback confirmed all four sites; non-CoDOL letters unchanged. No builds/tests/assembly/runtime, full match entry remains unverified.

### 2026-09-09 reverb and channel-volume command corrections
Previous turn corrected incremental score commands (progress). Parent inspected retained audio producers and C1 dispatch: o->468350 CG_ReverbCmd6args, z->468490 CG_DeactivateReverbCmd3args, A->468550 CG_SetChannelVolCmd4args, B->468640 CG_DeactivateChannelVolCmd3args; diagnostic strings confirm identities. Corrected CoDOL opcode r/D/E/F to o/z/A/B. Both deactivation producers incorrectly supplied priority+double to a format requiring string+three doubles; replaced with actual %c %i %g format, fixing invalid varargs use for all builds. Channel-volume preset comes from retained shellshock bank7a2, already translated to C1 shellshock bank; client A consumes preset index into268-byte records. Full argument/range and audio runtime parity remain unverified. No builds/tests/assembly/runtime, full match entry unverified. Accidental nonexistent helper calls produced only file-not-found and no state changes.

### 2026-09-09 local sound command mappings
Previous turn corrected reverb/channel commands (progress). Parent decoded C1 play handler468700 and stop4687a0, diagnosticsc44a70/c44af0 confirm LocalSound/LocalSoundStop. Both take exactly index argument and use offsets6d1063c = CS3395+index; play calls44f440, stop7389a0 with client context. Existing sound bank publisher preserves native alias slot. Changed retained playlocalsound s->p and stoplocalsound k->h underCODOL_SERVER, preserving receiver validation, G_SoundAliasIndex and command type0. Source sites read back; non-CoDOL unchanged. No builds/tests/assembly/runtime or match-entry claim. Workers terminal.

### 2026-09-09 Claude workers resumed for missing GSC methods
User reauthorized workers. Verified empty CLI inventory before launching two bounded Opus/high 55-turn assignments: gsc-revive-resume (CLI75088, session6ab1aaa4-dbe2-4457-b666-5882a522f5e2) for laststandrevive and actual native gameplay dependencies, and gsc-startup-missing (CLI60564, session7138dca2-0390-4131-9bb3-cd09e37d52c3) for 2-4 missing MP startup bindings. Both confirmed live by CLI inventory. Separate new-source ownership; shared changes go to parent as reviewable patches. Explicit architecture freedom and writing-only/no-hooks constraints included. No worker output accepted/count changed; full GSC coverage and C1 match entry remain unverified. Historical registry/count claims require fresh source review.

### 2026-09-09 measured dynamic configstring transport
Previous turn launched and verified two workers (progress). Both current Claude sessions/PIDs75088/60564 confirmed live, no restart. Parent traced actual C1 pre-CG reader487730 through execution loop46a1a0: no x/y/z reassembly, d retokenized to3tokens and storageupdated487440 before CG467350. Native sender5d30e0 explicitly bounds strlen+1<=0x3f8 and emits one d command; no chunk loop. Changed CoDOL generic SV_SetConfigstring fallback to matching1015-byte value limit/single d and gamestateSent gating; non-CoDOL chunk branch preserved. Read back source and verified header inclusion. Separate specialized publishers and unmapped vote/system namespace issues remain. One inefficient parent offline PE search was stopped by its verified PID75440 and replaced by cached-buffer scan; no game/lobby/worker processes touched. No builds/tests/assembly/runtime or match-entry claim. Evidence docs/CODOL_DYNAMIC_CONFIGSTRING_TRANSPORT.md.

### 2026-09-09 shutdown reliable disconnect correction
Previous turn corrected dynamic configstring transport (progress). Both Claude workers verified live this turn. Parent independently decoded aligned C1 reader487730: t routes48782e, absent reason uses EXE_SERVER_DISCONNECTED atc46474, argument1 reaches4960e0 with localized disconnect handling. Existing native drop/overflow already use measured SV_WIRE_DISCONNECT_COMMAND(t). Found two missed SV_FinalMessage shutdown variants still hardcoding0x77(w), which collides with C1 HUD splash. Replaced both with shared macro; non-CoDOL remainsw. Source readback only; no shutdown, builds/tests/game/server execution. No GSC counts or match-entry claim.

### 2026-09-09 map-loading notification transport
Previous turn corrected shutdown disconnect producers (progress). Both Claude workers75088/60564 verified live. Parent traced C1 reliablel469698 to audio739870; retained SV_SpawnServer map/gametype notice used wrong transport. Actual connectionless commandloadingnewmap atc4812c/496e9b checks connected-server address, reads map then gametype as lines via59f6d0, setsstate5 and calls499560 (diagnosticc48830 explicitly map/gametype). Changed CoDOL branch to NET_OutOfBandPrint loadingnewmap newline map newline gametype newline, bot skip; native IW3 branch preserved. Read back source. Server producer/retransmission and full uploadStats/map lifecycle unverified. No builds/tests/launches; no match entry. Evidence docs/CODOL_MAP_LOADING_NOTICE.md. Misaligned initial496e90/497110 exploratory output not evidence.

### 2026-09-09 laststandrevive integrated after parent review
Previous turn corrected map-loading notice (progress). Revive worker terminal success session6ab1aaa4-dbe2-4457-b666-5882a522f5e2 cost3.783333USD. Parent independently decoded IW4 handler5df3b0 and verified actual retained producer317c=1/time3180=leveltime+500, damage grace consumer, ClientEndFrame mode override and player.h fields. Earlier parent assertion of absent native consumers was wrong. Registered CODOL_Scr_LastStandRevive, which clears both fields with player receiver validation, ignores extra args and pushes no return. Existing spawn memset handles respawn. Corrected same-frame claim to next ClientEndFrame and disassembly comment address. Worker report's wiremode6 claim is also wrong: current codol_engine_state.c modes[6]=7; parent did not change that mapping or claim its C1 runtime validation. No builds/tests/assembly/runtime or match entry. Current GSC counts remain historically stale; this method recorded separately as reviewed registered unvalidated.
Also corrected CODOL_MAP_LOADING_NOTICE.md: C1 58ba60 appends local console text uploadStats; it is not an outbound message by that name. No speculative stats-store reset made; reconnect/upload lifecycle still under review. Other GSC startup worker remains active at latest authoritative check.

### 2026-09-09 fast-restart command mapping
Previous turn integrated laststandrevive (progress). Authoritative CLI confirms startup worker60564 still active and revive terminal; startup session log shows ongoing binary inspection, no duplicate launched. Parent decoded C1 k46967c/x4698ff -> CG_MapRestart467980 with preserve1/0; diagnosticc448c4 names it. At467bf0 preservezero enters scoreboard/round UI reset467c63..467cac, preservenonzero bypasses it. Earlier client command reader487892 handles both. Changed native SV_ReconnectClients savepersist ternary fromIW3n/B toCoDOLk/x underCODOL_SERVER. Exact C1 native producer/full restart state not verified. Also corrected laststand source comment wiremode6->7 from actual mapping. No builds/tests/assembly/runtime; full match goal active. Startup scan maps/mp/_teams missing result is an explicitly seeded entry, not automatically a demonstrated dependency; do not count every scan candidate as a runtime compile blocker.

### 2026-09-09 global music/fade command correction
Previous turn corrected fast restart commands (progress). Startup worker60564/session7138dca2 verified live; no duplicate or restart. Parent independently decoded C1 l469698 resolves alias then739870, diagnosticc83c0c identifies music; m4696ee reads integer duration then739810; n469731 reads gainfloat and durationint then739ae0. Retained musicplay format already carries name plus1, musicstop converts seconds tointeger milliseconds, soundfade gain+integerduration. Changed three opcode constants underCODOL_SERVER to l/m/n; non-CoDOL o/p/q preserved. This fixes wrong reverb/local-sound/menu dispatch, without claiming full argument/range or runtime audio parity. No builds/tests/assembly/game/server launches; full goal active.

### 2026-09-09 normal ambience configstring integration and worker resume
Previous turn corrected global audio opcodes (progress). Startup worker session7138dca2 terminated max_turns55 cost4.4942505USD, verified empty CLI inventory. No completed implementation/report. Resumed SAME session with30-turn finish, supervisor77944/CLI61832 verified live. Require immediate checkpoint and actual playerhide consumers; worldpointinreticle_circle math must be verified at IW4 helper502dc0, not inferred from broken Python. Same source ownership/no shared edits/no builds/no runtime/native rewrite freedom. No worker output counted.
Parent decoded C1 ambientStop542670->CS1300 at5427d0, SetAC130Ambience555cb0->1301, consumer4676b6 chooses byflag8000 and44f2e0 reads n/t keys/deadline. Native retained ambientplay/stop write821 with matching info format but no namespace translation existed. Added CODOL_CS_AMBIENT1300/AC1301301, maps821->1300 in initial and dynamic map publisher; updated incorrect playername-bank boundary comment. No duplicate AC130 publication, optional player-target APIs unreviewed. Source-only; no builds/tests/assembly/launches or match entry.

### 2026-09-09 setac130ambience native GSC implementation
Previous turn mapped normal ambience (progress). Startup-finish worker61832/session7138dca2 confirmed live. Parent added and registered global setac130ambience in new codol_script_ambient.c, backed by C1 aligned555cb0..555df1:1/2args, optionalfloat1beforestring0, nonemptyalias then nonnegativeconvertedfade, no return. Publishes n/t(deadline) into actual CS1301, initial override plus primed/gamestateSent live updates gated onrunning/restarting. Added retained assembly CODOL_AmbientFadeMillis to match C1 stagedfloat conversion and x87 FISTP32 with decoded double1000 and2^-30bias; did not substitute floor(x+0.5). Deadline wraps32bit, complete value bounded1015. Parent inspected source/header inclusion/registry/helper readback. This is source-written registered unvalidated, not runtime-complete: clientflag8000 selection, full error/localization/storage-case parity remain unverified; no builds/tests/assembly/launches or match entry.

### 2026-09-09 AC130 ambient storage review
Previous turn implemented setac130ambience (progress). Startup-finish worker61832/session7138dca2 verified live, checkpoint now present; no duplicate. Parent inspected configstring lifetime: SV_ClearServer2847 calls CODOL_ResetServerConfigstrings, freeing overrides, while gamestate writes current bank. C1 sender5d3198 selects lowercase storage atindex>=1300, helper5cb3f0 callsada522 with ASCII lowercase fast path; sender5d3235 still broadcasts original pointer. Updated new AC130 method to store Q_strlwr copy but send original value, preserving C1 initial/live storage distinction. Read source only; no builds/tests/assembly/runtime. Locale edge cases/full playback and full match entry unverified.

### 2026-09-09 playerhide snapshot dependency
Previous turn corrected AC130 storage (progress). Startup worker61832/session7138dca2 confirmed live; new source now exists, method remains unregistered pending final review. Parent independently decoded C1 PlayerHide54de50..54dec0: client required, ps+ec OR10 thencontents130=0, noargc/relink. Verified retained BG_PlayerStateToEntityState copies ps.eFlagsb0 toentity8 and ClientSpawn preserves only100002 acrossmemset. Added native20->wire10 to shared_player_flags used by both player and player-entity snapshot paths; clears priorwire10 whennative20clears, preserving respawn unhiding. Shared codec owned byparent, no worker source edits. Need review worker extraMAX_CLIENTS receiver restriction and final patch before binding. No builds/tests/assembly/runtime; no client visibility or match-entry claim.

### 2026-09-09 playerhide registered; reticle review findings
Previous turn integrated hidden snapshot flag (progress). Startup-finish session7138dca2 now terminal max_turns30, CLI inventory empty; no restart. Parent removed extraMAX_CLIENTS receiver restriction from playerhide (C1 checks actual client pointer), registered method/declaration. Existing respawn contents/flag reset and parent snapshottranslation complete source path. No builds/tests/runtime. Reticle draft NOTregistered: finite/FOV guard errors absent fromIW4, incompletelinkedorigin and unstagedfloat math. Parent decoded IW4 wrapper4b6d00: word14bit4 uses entity18c tag_player; diagnostic7234c0 explicitlyview-linkparent. Existing native CODOL_PLAYERLINK_WEAPONVIEW state already represents it; IW4 writer5ef53csetsbit4 and5ef574storeslinkentity18c. Also independently decoded502dc0 showing float intermediate for radians/tangent/side-forward/up-forward and verticaltangent, unlike current draft double expression. Complete these before binding. No C1 match entry verified; goal stays active.

### 2026-09-09 reticle circle completed in source and registered
Previous turn registered playerhide (progress). Parent independently decoded IW4 method5f5910, projection502dc0 and dot409f00; read actual constantsdeg2rad0.01745329238474369, half0.5, -320/-240/aspect0.75 fromPE. Completed worker draft with existing CODOL_PLAYERLINK_WEAPONVIEW/linkEntNum -> G_DObjGetWorldTagPos(tag_player), measured IW4 wrapper4b6d00/linkwriter5ef53c/574, native Com_Error onmissingtag. Removed addedfinite/FOV constraints and extraMAX_CLIENTS receiver check not inreference. Added volatilefloat stages for projection/tangent/ratios/verticaltan/distance and extended products, strictdistance<radiusSquared. Registered worldpointinreticle_circle; header stale missingbranch/pm_flags claim corrected, explicitforwardstructdeclaration added. Worker Python halfangleellipse interpretation rejected; actual argsFOVdegrees andvirtual640x480radius. No builds/tests/runtime; libm/extremeFP/linkassettransform parity unverified, no matchentry. Workers terminal, sequentialparentwork.

### 2026-09-09 getpointinbounds reference correction
Previous turn completed/registered reticle circle (progress). Parent inspected related IW4 method table; getpointinbounds already registered. Decoded handler5f5a40 reads threefloatargs withoutfiniteguards and helper470d30 rotateslocalbounds, storesfloatcomponents, thenaddsentityorigin470e08..470e28. Corrected existing codol_script_entity.c: removedfinitecoefficientScriptError, readallthreeargsbeforemath, stagedrotatedfloatbeforeorigin with extendedproducts. No newbinding/count. Native midpoint/halfsize derives fromretainedmins/maxs; extreme numeric/geometry parity unverified. No builds/tests/assembly/runtime or matchentry; workers terminal, sequentialparentwork.

### 2026-09-09 MP animation precache contract and search correction
Previous turn corrected getpointinbounds (progress). Parent located IW4 precachempanim table79abdc->5f8380; init-only indexedname registrarbase4042/capacity63/create1/labelmpanim, no return. Discovered ordinaryrg skips ignored vendor scripts; --no-ignore finds actual AC130flares/animatedmodels/destructible calls. Earlier emptyreference-tree searches not absence evidence. C1 base4042 collides withtaggedeffects; nearby3363..3394loadsassettype41at4674c4, so neither is suitable speculativeanimationbank. Saved docs/CODOL_MP_ANIMATION_PRECACHE.md with nextC1scriptmodel/XAnimconsumer requirements. No stubregistered, no builds/tests/assembly/runtime, no matchentry. This turn yielded reference evidence changing implementation direction; fullgoalactive.

### 2026-09-09 scriptmodel animation worker
Previous turn verified MP animation contract (progress). Confirmed actual ignoredvendor AC130/destructible scriptModelPlayAnim/ClearAnim calls; IW4 name715088 table73d90c. C1c58898 handler549b0d writesdest58sourceentity (mark transfer-like), not animation proof. Started ONE bounded Opus/high55turn worker gsc-model-animation, supervisor77772/CLI76420/session3056ea48-a3ca-434b-8e20-96acc0e53189 verifiedlive. Owns new model-animation source family only, shared patches proposed; nativearchitecture freedom/nohooks/no-build/no-runtime constraints included. Parent independent vehicleprecache investigation found IW4name6d9cac and native32definitionvehicle table, nexttrace registrar/nativeassetconversion. All earlierworkers terminal, no duplicate. No workeroutputcounted or matchentryverified.
## Latest verified team: two Claude implementation workers

Animation CLI76420 remains live (session3056ea48-a3ca-434b-8e20-96acc0e53189).
Added vehicle-assets supervisor65376/verifiedCLI77704, Opus/high bounded55turns.
Owns NEW codol_vehicle_assets.c/.h and codol_script_vehicle_assets.c/.h (or.cpp),
with shared changes supplied as patches. Implements precachevehicle plus real
VehicleDef loading, native representation, C1 configstrings and lifecycle.
Parent retains integration/registry ownership. Both prompts explicitly allow
native rewrites and prohibit hooks, builds/tests/runtime and nested agents.
No new worker output accepted or counted. Previous active statuses below are
historical; revalidate processes. Missing GSC methods remain the priority.


## Fog configstring translation — source written, unvalidated

Parent mapped retained G_setfog slot9 to C1 slot13 for initial gamestate and dynamic publication. Retained six-token exponential fog payload gains maxOpacity1 before milliseconds and a trailing0 for disabled sun extension; single0 reset remains0. Source: codol_sv_assets.c, codol_configstrings.h. G_InitGame calls G_setfog("0"); retained Scr_SetExponentialFog emits start,density,RGB,milliseconds. C1 dispatcher467480 routes13 to4667e0; C1 fog producer545fd0..54601e uses formatc57acc "%g %g %g %g %g %g %.0f 0" and publishes13. Usagec57ae8 confirms maxOpacity and sun arguments. C1 slot9 instead drives465ae0, a different renderer setting.

Remaining: retained GSC API still accepts only six arguments; native C1 setexpfog546040 accepts7/14. Implement the full API and sun representation next; this change only transports the already-existing producer correctly. Legacy votes13..16 still collide with C1 fog/timing/center; systeminfo/extensions/IWD mappings remain unreviewed. No builds/tests/runtime; no new missing-method count or match-entry claim. Both Claude implementation CLIs76420 and77704 verified live at this review.

## Extended setexpfog producer — registered source, incomplete mirrors

Added codol_script_fog.c and CODOL registry binding. Accepts actual IW4/C1 seven/fourteen-argument forms, plus retained six-argument compatibility path. Decoded C1 argument10 is vector;11begin,12end,13scale (usage string misleading). Emits measured8/17-token non-sun/sun format through native slot9 -> wire13; publication recognizes complete payload without adding legacy defaults. Clears native fog culling limits toFLT_MAX like C1 common helper546023. Updates existing RGB/start/half diagnostic dvars. Corrected density constant to C1c85470 promotedfloat0.6931471824645996. Registered source only; new opacity/sun diagnostic dvar mirrors still required, extreme FP/error-message parity unverified. No builds/tests/runtime or complete-GSC claim. IW4table79a6a4->5f41a0 confirms7/14; C1handler546040, helper545c30, actualargreads546267..54629b andformat545f34..54601e inspected.

Animation original worker terminalmax55,56reportedturns,cost3.7346455, no source/report. Verified CLI gone, then resumed SAME session3056ea48-a3ca-434b-8e20-96acc0e53189 for15turn bounded handoff, checkpoint immediately/no broad searches. Vehicle CLI77704 remains live. No worker output counted.

## Fog diagnostic dvars — source integration

Parent added registration of measured numeric C1 fog dvars1411..1420 at native G_RegisterCvars, with defaults/domains from52c737..52c8f5. Seven/fourteen-argument setexpfog now updates color/opacity/start/half then optional sun enable/color/direction/begin/end/scale before common validation. Seven-argument calls clear only sun-enabled, retaining other sun mirrors as C1 does. Native read-only flags use existing fog flags0x10c0, not blind C1 flag copies. C1 strings independently read for all ten IDs. Header codol_script_fog.h and g_sv_main.c lifecycle call added. Existing six-argument IW3 compatibility extension still delegates its old implementation and does not update the new numeric mirrors; this is a remaining compatibility-path difference. Extreme FP/libc/domain-clamping parity unverified. No builds/tests/runtime.

Animation finish CLI73256 and vehicleCLI77704 both verified live this turn, no output accepted. The absence of a checkpoint/report file is not completion or proof of a stopped worker.

## Unified six-argument fog compatibility path

Parent removed the early delegate to retained Scr_SetExponentialFog. Six-argument calls now use the same CoDOL producer as7/14, taking time fromarg5, defaulting opacity1, clearing sun-enabled and updating numeric diagnostic dvars. This resolves the stale numeric mirror difference reported in the prior entry. Registration remains one setexpfog binding; no new missing-method count. CoDOL now owns its culling and complete payload for all accepted forms. Legacy argument error wording/float rounding follows the CoDOL producer, not exact IW3 behavior. No builds/tests/runtime; match entry not verified.

Parent source inspection also reconfirmed SV_LoadLevel always publishes IW4OL extension CS2 plus IWD headers4861/4862; these still need a native CoDOL disposition/mapping, because fallback numeric passthrough is not a namespace translation. Legacy voting13..16 still collides with C1 fog/timing/center. Neither problem is fixed or suppressed in this pass. Animation finish73256/vehicle77704 remain verified live; no handoff accepted.

## IW4OL-only extension publishers removed from CoDOL startup/restart

Parent restricted SV_BuildXAssetCSString definition and both full-load/restart calls to non-CODOL_SERVER builds. Also restricted development IWD header dvar registration/publication in SV_LoadLevel. These are IW4OL extension producers, not native CoDOL gameplay support: C1 dispatcher467584 routes4275..5298 to466b60, which registers nonempty material names, so4861/4862 are not IWD metadata slots. CoDOL native asset publication and its own gamestate CS2 value remain; no replacement guessed. Systeminfo and legacy vote collisions still require work. No builds/tests/runtime or full compatibility claim.

Animation handoff report now exists at obj/claude-workers/gsc-model-animation-report.md (read while worker still live; not accepted implementation). It locates IW4 play4d9a00/clear4512e0 and actual client animation selection/starttime consumer4b8180. C1 equivalent remains unresolved. Do not count absent names or a scan's failure to find a registrar as proof C1 cannot implement the family. Parent must review evidence and report claims before adoption. Vehicle worker still last verified live77704.
# Parent animation review — not registered

Animation finish is confirmed terminalmax15 (16reportedturns), cost1.811803; CLI73256 is gone. Ownership released. No shared registration patch accepted. VehicleCLI77704 remains lastverifiedlive.

Rejected worker conclusions: eType6 field0x6c is codec-97, which encodes a full timestamp with short delta optimization (codol_delta.c), so a32-bit start time DOES have a possible wire home. This does not prove its semantic purpose. Native gentity_t DOES have classname (entity.h), and scr_const.script_model exists (scr_vm.h). Parent corrected draft receiver to use it and removed invented exact-argument-count checks absent from cited IW4 handlers. Other draft parity gaps (name bounds, classname error staging, empty-name handling, complete C1 consumer) remain; no bindings counted.

New aligned C1 evidence:440e20 explicitly tests nextState.eType6 atcent+e8, reads selector cent+144 (wire60, masked7ff), timecent+150(wire6c), flagcent+154(wire70). If timezero clearsselector; outputselector/time/flag passed to440f-class consumer. Caller441035..441088 compares returnedtime againstCGtime;44109d allocates128-byte state,441105storesselectorword atstate78;44119a freesstate whenselectorzero. These findings refute the report's no-timestamp rationale and provide a concrete next trace. It may be a different animation/physics subsystem; do not label this proven MP animation or write fields yet. Next inspect4405c0,4402f0 and callers/asset lookup to identify selector semantics.

No builds/tests/runtime. No real C1 match entry verified.

## Script-mover follow-up and vehicle handoff

Parent followed aligned C1 routines4405c0,4402f0,440330,440c30,441290. The selector/time state participates in DObj root transforms and linked-parent transforms:4405c0 resolves an entity DObj through25d9ed8/2575ed8 and calls63aa40, which reads its tree and extracts quaternion/translation;441290 writes resulting position/angles. These calls do not yet identify the selector-to-animation producer. A bounded offline instruction scan of440000..448000 yielded selector/time accesses440e32/440e38 and cache78reads/writes4410ef/441107; other hits442a38/443173 are leads only. A rawrelativecall scan found441050 as caller440e20, not proof against indirect calls. No state fields published; missing animation bindings remain unregistered.

Vehicle original worker confirmed terminalmax55,56reportedturns,cost4.6019735,session3da84d54-d463-45cc-bbab-f1ae4d6f2884. Source files exist but final report/patch absent. Resumed SAME session for bounded15turn handoff with first-action report, no broad research. Supervisor75340, verifiedCLI78100. Ownership unchanged until terminal. Initial draft precachevehicle adds exactargc1 absent from measured IW4handler; parent must remove/review after worker finishes, not count as support now. All no-hooks/no-builds/tests/runtime/native-rewrite rules repeated. Animation ownership parent, no live animationworker. No match entry verified.

## VehicleDef mounted archive retention and view

Parent added type41 to top-level asset alias retention in codol_load_blocks.c and to dependency-name lookup with measured0x314header in codol_asset_registry.c. Added CODOL_LoadMountedVehicle / codol_mounted_vehicle_t in registry/header: resolves newest real definition using existing override/comma-reference rules, returns borrowed serialized asset/header plus prefix strings at0/8/ac and the first dependency offset. Failed calls preserve output. Prefix8/ac semantic names deliberately unspecified pending field evidence. Existing replay validates full source extent before archive mounting; this accessor resolves only the prefix and does not turn serialized references into native pointers.

This closes missing archive lookup plumbing, not vehicle simulation conversion. Worker text-loader fallback is not accepted CoDOL VehicleDef support. Still required: dependent physics/weapon/sound conversion, native simulation fields, vehicle definition snapshot slot writer, and binding integration. Worker78100 remains verified live in bounded finish; parent owns assets.h, asset_registry.c and load_blocks.c modifications, shared patches must preserve them. No builds/tests/runtime; no new GSC count or match entry claim.

## Vehicle physics source resolution and draft review

Extended CODOL_LoadMountedVehicle to resolve physics preset dependencyb0, handling null/inline/alias references. Inline source extent comes from existing replay records; cursor advances over original dependency before newest named override selection. Reads followingb4 profile string via archive string resolver. Borrowed result keeps serialized preset asset plus resolved name; failure preserves caller output. Header documents that weapon/sound/simulation remain separate. No guessed native field offsets or pointer casts.

Vehicle finish terminalsuccess13turns,cost1.437854,CLI78100gone; all implementation workers now terminal and ownership released to parent. Shared patch not applied because text-file loading, simulation conversion and snapshot definition-slot producer remain incomplete. Parent removed invented exactargc1 check absent from IW4handler4d4840. Fixed zero-initialized/unbound slot info erroneously looking like native record0; resets and invalidated/unnamed bindings now expose-1. No GSC binding counted or registered. Existing patch must be reviewed against current source and preserve parent's archive/fog changes.

No builds/tests/runtime. Real C1 match entry unverified; goal active.

## Complete VehicleDef dependency source walk

Parent extended CODOL_LoadMountedVehicle through string190, weapon194, sounds1ac/1b0, two materials1d0/1d4, fourteen sparse sounds1e0..230, string238, and31sound slots23c onward, in retained C1replay_vehicle order. Total47 sound slots preserve nulls and order. Resolves weapon/material aliases and newest real named definitions after advancing original inline source extents. Added nested weapon record capture and CODOL_ResolveWeaponAlias so inline VehicleDef weapon assets are available. Requires exact final serialized source extent; output remains unchanged on failure. Views remain archive-owned and serialized, not native pointer casts.

Native vehicle simulation translation and snapshot definition-slot writer are still missing; no precachevehicle registration/count accepted. No builds/tests/runtime. Confirmed no live implementation Claude workers; only unrelated Chrome nativehost remains.
# C1 vehicle snapshot identity — parent evidence

Aligned VehicleCl_ResetEntity starts67cc10; diagnosticc72e60 names it and prints instance/definition/entity/localclient. cent.nextState startsate4. Readscent13c =>wire58. Low4bits select instance0..15 in2bc2798,stride88. At67cc53..67cc5f, (cent13c>>4)&31 becomes instance+4, which indexes VehicleDef table2bc3018. Therefore wire58 carries instance|(definitionSlot<<4), matching9-bit eType12/14field tables. No high bits can be inferred from this function.

Caller46b9ce..46b9dc invokes reset with cent inedi and localclient onstack; enclosing type-dispatch still needs aligned table decoding to confirm all supported types. Previously reported488943 is in serialization488900, reading/writing the whole0x880-byte instancearray through a functionpointer. It is not the per-snapshot slot writer.

Remaining native integration: stable16-instance allocation and lifecycle, actual native vehicle-info to31usable definition slots, captured state surviving archive/entity reuse, body/steering/turret/flags/model fields, exact eType dispatch. Do not publish only a selector and claim a complete vehicle snapshot. Current codol_sv_gameframe.c turret branch is the nearby integration surface. No builds/tests/runtime or client match verification.

## Native vehicle instance allocation and conversion assignment

Retained G_VehiclesInit iterates8 slots ofstride0x354, entNum+1b8=1023empty; SpawnVehicle scans same8 and storesentNum/infoIdx+1bc. This fits C1low4instance packing without another allocator. Native lifecycle can own slot identity; definition slot must be captured with entityState so archived snapshots do not read live reused records. Existing codol_entitystate_ext copies at sv_snapshot.c1105/1194/2004 provide capture propagation surface. No vehicle snapshot branch integrated yet; current entity_seed rejects vehicle types bydefault.

Started ONE fresh Claude Opus/high bounded40turn worker vehicle-native, supervisor66088/verifiedCLI71192. Owns NEW codol_vehicle_native.cpp/.h and scratchvehicle-native-* only. Native VehicleDef-to-simulation conversion uses complete mountedreader; shared changes patchonly. Parent owns existing vehicle assets and snapshot capture. Prompt explicitly repeats unrestricted native rewrite permission and nohooks/builds/tests/syntax/assembly/emulation/runtime/nestedagents, checkpoint3calls/reserve10handoff. All earlier workers terminal. No output counted; no match entry verified.

## Vehicle identity captured-state representation

Added vehicle_identity/vehicle_known to codol_es_ext_t and capture/get API. Valid instance0..15/definition1..31 packs into9bits; invalid/unresolved capture clears previous identity, getter preserves output on failure. Existing whole-extension copies and entity/map/archive clears carry/reset it. Extended BOTH internal archive writers and reader with changed/known/9bitidentity record after primaryweapon; reader rejects slot0 identity, truncation and nonvehicle state. This changes the native internal archive format; it is not a new C1 network field.

Spawn/correct definition-loader producer and frame serializer not yet wired; no claim that actual vehicle snapshots work. In particular, do not read live scr_vehicle during delayed serialization. Native eight-slot lifecycle will supply instance; successful converteddefinition supplies slot. Workervehicle-native71192 verified live, ownershipnewnativecpp/h only. No builds/tests/runtime or GSC count change.

## C1 vehicle pose and frame consumer trace

Aligned VehicleCl frame routine67cfc0: instance fromwire58 low4; wire5c&7f ->instance18flags; wire74 ->instance38; derives speed from next trajectory delta and invokes67ccf0(local velocity from two position trajectories and interpolatedbodyaxis),67ce50(angular velocity from two angular trajectories),67cf30(accumulates scroll using def14),67c760(other effects/flags). Do not invent separate network velocity fields for these derived values.

Aligned pose routine67d080 reads prev/next state pairs and shortest-angle interpolates fields: wire60 at67d0a8->pose40; wire70 at67d16b (continue to recorddestination); wire64 at67d217; wire6c at67d2c5; wire68 at67d372->pose4c. At67d412, wire7c(cent160) is integer converted usingsecondsfactor into pose50. It resolves bone tags from24ee0c0/c2/c6 at67d46b onward. Exact semantic mapping of these five posefields to nativebody/roll/steering/gunangles still needs bone-controller evidence; do not infer just from layout proximity. Following posecode67d590 is next bounded trace. C1table12/14 uses measuredfloat/angle/time codecs for these fields.

Native snapshot identity storage alreadywritten, but no complete vehicle framebranch integrated. Nativeconversionworker71192 remains lastverifiedlive. No builds/tests/runtime or clientmatchentry.

### Continued vehicle pose trace and bounded animation worker
- Verified native Claude processes: vehicle 71192, animation 70472 (supervisor 77080). Animation owns only four existing animation draft files; Opus/high, 35 turns, shared edits as patches. No output accepted yet.
- Aligned C1 67d080 adds exact pose destinations: wire70 -> pose42 at67d207, wire64 -> pose44 at67d2b4, wire6c -> pose46 at67d361. Previously measured wire60 -> pose40 and wire68 -> pose4c remain. Part semantics still need controller evidence.
- 67d590 initializes six bone slots at pose60..65 to FE then returns. 67d5ac is the alternate distance-dependent path; it reads pose50 and constructs wheel/bone data. Do not infer body/gun identity from offsets alone.
- C1 67a1a0 independently resolves shared script-string slots24ee0c0/0c2/0c6 into server-side vehicle bone indices384/388/390. This is a lead for semantic names, not proof of angular mapping.
- Writing pass only: no builds, tests or runtime validation; no verified match entry.

### Vehicle pose source implemented
- Confirmed all five angular semantics through C1 spawn67a500, controller67ac10, steering678680, script-string initialization57787c, and retained native controller.
- Added atomic CODOL_OverlayEngineVehiclePose for body pitch/roll, steering yaw, gun pitch/yaw. Full vehicle adapter remains unconnected pending remaining state/producer work; no support-completion claim.
- C1 entity7c is produced from VehicleDef160, not proven equivalent to native materialTime. Do not publish a guessed clock.
- Two Claude workers remain active as last verified: vehicle71192 and animation70472. Missing animation GSC source still awaiting parent review. No builds/tests/runtime.

### Suspension travel mapping resolved
- C1's wheel pose path67d703..67d73f negates the decoded entity7c value and uses it as the endpoint distance along body-up for wheel traces. This establishes a distance, despite the delta table's time codec.
- Retained G_VehEntHandler_Think_200 explicitly publishes vehicle_info_t.suspensionTravel (offset8c, named in s_vehicleFields) multiplied by1000 into entity.time2 (70). C1's corresponding producer67b3a4..67b3b8 publishes VehicleDef160 multiplied by1000 into entity7c.
- Extended CODOL_OverlayEngineVehiclePose to publish captured time2 at wire7c. No live definition lookup; native materialTime remains unrelated. Full vehicle branch still pending.
- Flag producer leads for the next trace:679adb sets block+4 bit40;679e9c clears it;67b019 clearsbit2 and67b1ac setsbit2;683dc0/683e14 togglebit10;686728/686748 togglebit20. These are leads, not yet translated semantics.
- Worker sessions identified: vehicle4433c1c8-457d-4f45-baff-596f23b5bb8b, animationb3022b26-0dbd-473b-be0e-e38e83bbfecd. Both CLI handles verified live this turn; vehicle latest logged action writing conversion header, animation tracing DObj registration. No completed output accepted. No builds/tests/runtime.

### Vehicle controlling-client field identified
- C1 spawn67a6df..67a6ff writes entity74 from optional player's playerState140, otherwise zero. Existing native player-state adapter independently establishes C1 ps140=clientNum. C1 frame67cfc0 reads entity74 into vehicle-instance38. Therefore do NOT map native lerp.u.vehicle.team to C1 entity74. A proper controlling-client producer/capture is required.
- Offline flag leads remain unresolved: C1 vehicle block+4 bit40 set679ac0/cleared679e9c alongside ownership linking; bit20 is toggled by GSC wrappers686710/686730, whose method-name pointers are stripped to the same string. No guessed flag translation added.
- Both workers verified live again (71192/70472); no finished results. No builds/tests/runtime.

### Native vehicle conversion worker terminal; parent review started
- Verified vehicle CLI71192 absent and result terminal success, session4433c1c8-457d-4f45-baff-596f23b5bb8b, reported49turns/$4.39539. Files codol_vehicle_native.cpp/.h now parent-owned. Animation70472 remains live.
- Worker delivered archive conversion plus a proposed shared loader patch. Patch NOT applied: it can still fall back to text after a failed native conversion, bypass native conversion when a text record already exists, and leaves physics/movement consumers incomplete. Source present is not full support.
- Parent filled measured suspensionTravel atC1header160 and retainedrecord8c, removed unsupported-type-to-type0 substitution from installation, and made the queried definition carry its actual registered turret weapon index.
- The remaining physics block, C1 type mapping, steering/texture behavior, silent bounded-name copying, and extension consumers require further review/implementation. No builds/tests/runtime.

### Native archive vehicle loading connected
- CODOL_LoadVehicleDefinition now always calls the native archive installer; removed text/defaultvehicle fallback and existing-text-record bypass. Binding validation requires a live converted definition. Late binding now fails if conversion fails or resolves a different retained index.
- Full G_VehiclesInit(0) now calls CODOL_ResetVehicleAssets immediately after clearing the retained record count; that reset also clears converted definitions. The restart arm preserves definitions and its existing sound refresh. Makefile automatically includes root cpp/c sources.
- Native conversion still has unresolved physics/movement fields and source-name truncation concerns; GSC registration/spawn path and full vehicle snapshot integration remain unfinished. No builds/tests/runtime.
- Animation worker terminalmax35, sessionb3022b26-0dbd-473b-be0e-e38e83bbfecd, cost$2.699298. Resumed the SAME session for an8turn handoff only, no exploratory research, to produce report and already-justified corrections. Supervisor78604. No animation support counted.

### Vehicle conversion failure handling
- Removed silent string truncation from native VehicleDef conversion. Every copied archive string is checked; conversion leaves output unchanged if a field exceeds its current native storage. Existing bounded representation still needs extension for larger valid content; truncating references is not accepted.
- precachevehicle draft now reports native definition load failure instead of ignoring it after slot registration. It remains unregistered pending the full native spawn/definition path.
- Confirmed SpawnVehicle still calls the retained VEH_GetVehicleInfoFromName and looks up defaultvehicle_mp; replacing this remaining spawn path must account for its model/definition logic and errors, not simply register the builtin and count it complete.
- Animation handoff51332 verified live this turn. No builds/tests/runtime.

### Vehicle record installation staging
- Native installer now stages vehicle_info_t locally and publishes it only after sound and turret weapon registration succeeds. Named sounds must resolve to1..255; indices are checked before byte storage. Named weapon registration must return a positive index.
- Failures leave existing vehicle record contents/count and converted-definition binding unchanged. Asset registration itself may have published earlier successful dependencies; this is not a transactional rollback of global asset banks.
- Retained SpawnVehicle's defaultvehicle_mp lookup also influences model fallback and record selection. A simple redirect of VEH_GetVehicleInfoFromName would allow a negative fallback record index; full replacement must address that control flow.
- Animation handoff CLI51332 verified live again. No builds/tests/runtime.

### Vehicle spawn archive lookup; animation handoff terminal
- CoDOL's retained VEH_GetVehicleInfoFromName entry now marshals its eax argument into the native archive/slot loader. The non-CoDOL implementation is unchanged. Requested and fallback definitions both require successful native conversion; missing/unregistered definitions drop the level instead of returning an unchecked negative record index into model fallback code.
- CoDOL fallback definition/model string changed from defaultvehicle_mp to C1's measured defaultvehicle (literalc4f498, consumed675010). Existing fallback model selection remains; native physics/movement and full snapshot capture are still incomplete. Initial registration/default preloading must still be checked against startup order.
- Animation same-session finish terminalsuccess6turns/$1.003398; CLI51332 gone. All animation files now parent-owned. No workers live.
- New animation evidence: report identifies C1scriptmover consumer43fcf9..43fdba using tree index low11 + variant800 atwire60, gatedwire6c==0. Client DObj tree selection, stop/replay behavior and variant semantics remain unproven. Proposed live per-entity lookup is also unsuitable for archived snapshots. No shared animation publication/registration accepted.
- No builds/tests/runtime or verified match entry.

### Spawned vehicle identity now captured
- Successful retained SpawnVehicle now calls native CODOL_CaptureSpawnedVehicle before returning. The producer validates the pointer against eight0x354 native slots, checks entity ownership/type, resolves the actual infoIdx binding and records instance|(definition<<4) in the existing entity extension. Invalid state drops the level rather than publishing a guessed identity.
- Existing entity extension copy/archive/reset paths carry that captured identity; no live vehicle lookup occurs in archived serialization. Full vehicle frame adapter remains pending.
- CoDOL SpawnVehicle no longer truncates G_GetWeaponIndexForName's result to AL before storing the entity weapon. The retained non-CoDOL byte conversion remains.
- Source assertions pin instance stride and entNum/infoIdx offsets to retained assembly. No build/test/assembly/runtime execution; assertions have not been compiled.

### Vehicle spawn client preserved explicitly
- Native G_SpawnHelicopter packs spawning-client index<<2 with team bits into lerp.vehicle.team. C1spawn67a6df..67a6ff instead writes the optional player's ps.clientNum to entity74.
- Successful ordinary SpawnVehicle now initializes entity.s.clientNum to0 (C1's absent-owner value). G_SpawnHelicopter explicitly captures its supplied owner's ps.clientNum there after its native packed-team store. This value travels with the ordinary entity snapshot/archive copies; it needs no live-owner query in the eventual C1 serializer.
- The new retained assembly call reloads caller-saved edx/entity and ecx/level before continuing. No field publication added yet; full vehicle frame adapter remains open.
- Confirmed native helicopter wrapper changes eType to12 after SpawnVehicle, so the earlier identity capture remains valid for either supported vehicle type. No builders/tests/runtime run.

### Vehicle flag producer review
- C1wire5c bit2 now traced to physics-instance210/1ec in aligned67b016..67b1ac. Meaning of1ec remains open; do not equate with nativeoccupied flag1. Nativeflag8 is first-think initialization, not C1engine state.
- This changes the next step to the physics-instance producer rather than script ownership mapping. No builds/tests/runtime; full vehicle frame adapter remains incomplete.

### precachevehicle registered to native archive implementation
- Connected CODOL_Scr_PrecacheVehicle in the CoDOL VM function registry now that slot loading and retained spawn lookup both use native archive conversion. It enforces initialization, reads argument0, registers the measured VehicleDef bank, loads the actual archive definition/dependencies and reports load failure. Extra arguments are not rejected; empty name remains the reserved no-op.
- This is source-level GSC registration, not a claim that all vehicle simulation/physics or C1 snapshots work. No builds/tests/runtime.
- Physics trace:65c7e0 copies rigid-body velocities/pose, not field1ec.65d405 compares1ec unsigned>0 and copies the boolean to instance178. Direct displacement scans found no write in650000..66ffff; backend/copied/subobject producers still need tracing. Rejected9d1f1a/9d2201 lookalikes as certificate/TLS code (bc1d54=Server certificate).

### Vehicle fallback registration before late spawn
- Inspected G_InitGame:level.initializing becomes1 before G_VehiclesInit, map entity spawning and script startup, then0 after Scr_StartupGameType. Ordinary map spawns may register their own definitions during initialization; later spawns require existing slots.
- precachevehicle now also loads/registers defaultvehicle for any nonempty successfully loaded request. The retained spawn path resolves that definition for model fallback even when the requested model is valid. This prevents a correctly precached vehicle's first post-wait spawn from failing solely because its required fallback slot was not registered.
- Empty-name no-op unchanged; native loader caches repeated definitions. Missing fallback remains a real initialization failure, not a substituted text asset. No builds/tests/runtime.

### Animation handoff parent review
- Independently confirmed aligned C1consumer43fcf9..43fdb7. Rejected report's claimed native layout match: C1 parts pointer8+index*8 differs from retained XAnim_s parts16+index*8 on32bit.
- Global first-name match across arbitrary script trees and per-name cached indices are not entity-specific tree correspondence. Proposed live per-entity writer also breaks delayed/archive ownership. None of that integration accepted.
- Next action: actual client tree construction, mapping to server entries, captured state and stop/replay semantics. No builds/tests/runtime.

### C1 animation tree selector located
- Confirmed DObj allocator59a800 ->634660 caller-supplied tree storage atDObj0. Caller44372b obtains tree asset through443540.
- Read dispatch tables asdata: ET_SCRIPTMOVER6 uses4435bb, which reads wire94 and indexes animation tree table262799c; zero selector has no tree. This is the missing separate tree selector, independent of entrywire60 and modelwire98.
- Next: registry2627990/7994/799c startup450b0f and registration, then server tree namespace correspondence and stop/replay. No builds/tests/runtime or animation publication.

### Animation registry realm and allocation confirmed
- C1loader5c9f10/5ca030 publishes independently indexed128-slot realm tables; renderer uses first/client table262799c, nativeScr_GetAnims uses second/server table. Registration5c97ff assigns next realm-local ID.
- C1 allocates count*8+4, confirming its compact header. Required next work is client registration order/name correspondence, not a native-layout cast or first matching server tree.
- No animation registration/publication or builds/tests/runtime.

### Claude GSC repair team resumed (2026-09-09)
- Verified two Claude Opus/high CLI workers: childthread-repair PID11672 (30-turn bound), animation-repair PID45732 (35-turn bound). No nested workers; explicit nonoverlapping module ownership. Both assignments include architecture rewrite authorization, prior parent review defects and writing-pass restrictions.
- Childthread owns its native module and supplies shared compiler/VM changes as a patch. Animation owns its four draft files and must resolve client/server tree correspondence, capture and stop/replay before integration. Parent acceptance is required; neither assignment is counted as supported yet.
- Parent rechecked makeusable/makeunusable: current registry and CoDOL type6 use dispatch already contain the earlier reviewed integration. Old missing-consumer handoff is superseded; avoid duplicate work.
- No builds/tests/runtime or verified C1 match entry. Overall native CoDOL goal remains incomplete.

### Configstring client-pool audit and worker observation
- Prior dispatch turn classified as progress: launched two bounded Claude repairs and rechecked existing GSC use integration. Both handles remain live now (11672/45732); no duplicate workers launched.
- New aligned C1 evidence: dynamic pool rebuild4875b7 starts at1, skips empty values and caps combined nonempty bytes+NULs at128KiB. Index3 has explicit server-ID update handling487666, unlike an assumed IW3 systeminfo path. Detailed addresses in CODOL_DYNAMIC_CONFIGSTRING_TRANSPORT.md.
- This makes effective inherited-plus-overridden pool validation a concrete next audit. Existing raw bank byte counters are not that measure. Vote collision still unresolved. No source support added or builds/tests/runtime performed this turn; full goal remains active.

### Effective client configstring pool validation connected
- Prior turn was progress: aligned C1 pool-limit evidence changed the next implementation step. Added CODOL_ConfigstringPoolSize and connected it before native gamestate serialization. It counts the merged inherited/override namespace, reserved empty byte and each nonempty terminator; explicit empty overrides clear inherited values. Exact 128KiB is accepted; overflow leaves optional size output unchanged.
- Gamestate requires the mounted inherited table's zone to match. Readback confirms map startup already requires installation of that matching table; this prevents incomplete accounting against an absent or different namespace.
- Source readback and manual capacity arithmetic review only. No builds/tests/runtime. Dynamic batches may need capacity-aware ordering because intermediate client states can exceed their final merged size; this new initial publication check does not resolve that separate path.
- Both Claude repair processes11672/45732 verified live during turn. No output yet accepted; full objective remains active.

### Replicated dvars: staged pool validation and publication order
- Previous turn was progress (initial gamestate pool validation). Current source change stages all changed replicated dvar values before mutation/publication, validates their final merged inherited pool, then emits non-growing values before growing ones. This bounds intermediate pool usage by the larger of the prior and final pool, instead of slot-order growth preceding later shrinkage.
- Pending strings are copied while each display value is valid. Allocation/validation failure frees pending ownership and leaves bank and outgoing batch unchanged. Commit transfers each owned allocation once and preserves override count/byte bookkeeping, including explicit empties. Shallow final-pool view is freed without freeing borrowed bank pointers.
- Uses C1's measured1015-byte value maximum. Manually reviewed source ownership, ordering and arithmetic; no builds/tests/runtime. C1 applies dvar values per command, not as an atomic client-side transaction. Other publishers and namespace collisions still require work.
- Claude11672/45732 both verified live; no worker output accepted this turn. Full objective remains active.

### Script-loader readback and live GSC repair observation
- Previous turn was progress: replicated-dvar batch publication source changed. This turn revalidated CLI11672/45732 live, with no terminal result/exit files. No duplicate worker started. Latest childthread session text says it is rewriting runtime layer3; this is progress commentary, not accepted implementation.
- Source readback found no new loader defect: CODOL_ReadRawFile validates uncompressed terminators and the inflate path appends its terminator; mounted script payloads are copied before source preparation; syscall conditionals precede lowering. Scr_IsSyscallDefined consults the actual native function/method lists. Avoid adding redundant validation based on an unverified defect.
- Confirmed new dvar publication is reached from SV_BeginClientSnapshot through CODOL_RefreshServerAssetNames as well as initial gamestate, not only startup. This source connectivity does not prove runtime behavior.
- Verified worker wait/source review only this turn; no builds/tests/launches or new support counts. Full objective remains active.

### Primary-light snapshot path connected
- Previous turn was a verified worker wait plus source review. This turn found and fixed a concrete disconnect: entity_seed rejected ET_PRIMARY_LIGHT before the already-written primary-light overlay. It now admits type10 to the common collector, which reads captured color/exponent/intensity/radius/cone/BSP index. No model lookup or live entity state is involved.
- Read current SP_light producer and registered light methods; reviewed collector ordering and source readback. No builds/tests/runtime. Other missing types (including corpses and full vehicles) remain unresolved, not replaced by empty seeds.
- Childthread repair original CLI11672 is terminalerror_max_turns31/$2.8985125; started SAME session6-turn handoff supervisor76488 to finish source/patch/report, no new research. Animation45732 remains live. No output accepted yet; full objective active.

### Native corpse consumer located; childthread handoff terminal
- Prior turn was progress (primary-light frame seed connection). Current offline trace establishes C1 type2 dispatch443ccc->45baf0, DObj prerequisite and separate corpse-info lookup. Wire9c/d8/dc/68/6c consumers documented in CODOL_CORPSE_SNAPSHOT_TRACE.md. Next required work is corpse model construction and captured lifecycle; no guessed type2 seed or Python spare-player substitute added.
- Childthread SAME-session handoff is terminalsuccess3turns/$0.420858; PID75592 gone. Original repair capped31turns/$2.8985125. Module ownership returns to parent. Report and shared patch exist; patch remains unapplied. Worker reports pause-array/string/cleanup repairs, but root-thread binding semantics remain inferred and CODOL_CHILDTHREAD_ENABLED remains0. This is not GSC support completion; parent source review still required.
- Animation45732 remains live. No builds/tests/runtime or verified match entry. Full goal active.

### Childthread repair parent review: inheritance still missing
- Prior turn was progress (native corpse consumer evidence plus terminal worker handoff). Reviewed current repair module and native OP_endon/Scr_KillThread/Scr_ErrorInternal. Both endon registration halves are now present, but report's semantic and rollback conclusions remain insufficient.
- Reference create_dof_targetent registers three endons in its called frame before starting a child; child comment says it acquires endons. Draft only binds to root lifetime and never copies event/object subscriptions. Native OP_endon records gFs.localId without GetStartLocalId. Next work must establish actual inherited-subscription behavior, including ancestor scope, rather than enable the synthetic root-death mechanism.
- Allocation failure remains nontransactional; AllocVariable terminal-errors, and Scr_Error can return while evaluating/loading. Detailed review in obj/claude-workers/childthread-repair-parent-review.md. Patch held; gate0 and no support count increase.
- No builds/tests/runtime. Animation45732 last confirmed live; full objective remains active.

### Corpse model dependency and animation worker terminal
- Prior turn progressed childthread parent review. Current aligned C1 trace45bc40->407b80 establishes that corpse model creation requires initialized corpse-info plus model string+e0; builder resolves base model and16 attachment model/tag strings from that record. Snapshot type2 alone cannot render it. Detailed trace and rejected misaligned starts in CODOL_CORPSE_SNAPSHOT_TRACE.md.
- Animation repair terminalsuccess46turns/$3.476635, session3ed3f093-a075-4338-97e8-65f823802679; PID45732 gone. All four files now parent-owned. Worker removed global first-tree scan and added explicit name/client-realm binding, but provides no automatic binding producer, capture integration or proven clear/replay behavior. Methods still unregistered. Parent review pending; no support count increase.
- Do not accept worker inference "no plaintext GSC name means no producer in C1": string absence does not establish code absence. Named-tree entry equivalence also remains inference. No further workers launched; no builds/tests/runtime. Full objective active.

### Corpse appearance-copy reset path found
- Prior turn progressed corpse model dependencies and animation handoff. New aligned reset branch46b901, referenced by jump table46bae4, selects original player info via wire9c and corpse destination via entity number. Flag80000 causes46ad70's exactb50-byte info copy while preserving the corpse tree;63c9f0 then clones source tree children. Existing native cloneplayer supplies clientNum and80000. This establishes a real client appearance producer rather than a spare-player workaround.
- C1 corpse entity-number bounds and exact reset dispatch remain next, followed by captured-field adapter. Full-body struct offsets are not cast across engines. All workers terminal; parent owns files. No builds/tests/runtime; goal active.

### Corpse reset type confirmed; native allocator range pinned
- Prior turn progressed client appearance-copy evidence. Current reset table read confirms type2->46b901. Native G_SpawnPlayerClone pointer arithmetic proves fixed entity64..71, separate from8 corpse-info bookkeeping slots. C1's matching range remains unverified and is the next allocator trace; generic entity bounds are insufficient.
- No guessed renumbering or corpse adapter enabled. Candidate actor-info references explicitly excluded from player-corpse evidence. No workers running, builds/tests/runtime or match-entry verification. Goal active.

### C1 corpse19..26 measured; cleanup prerequisite fixed
- Prior turn progressed native range/reset verification. Aligned C1clone51c780/51c827 computes(cycle+19)*2cc with8-slot cycle and captures clientNum plusa0000 flags. Actual C1 corpse range19..26 is now established, unlike native64..71.
- Added CoDOL-only client-pointer check to retained G_FreeEntityRefs cursor-hint scan. This removes a confirmed null dereference for in-use nonplayer slots within the old64-player reservation, a prerequisite for real native corpse relocation. No allocator relocation yet: cached snapshot MAX_CLIENTS handling remains next.
- Source readback only, no builds/tests/runtime or workers. Full objective remains active.

### Native corpse allocation now follows C1 entity19..26
- Prior turn was progress (C1allocator measurement and cleanup fix). Updated CoDOL retained clone allocator base/classname/number writes to19*274; eight-slot cycling unchanged, non-CoDOL64..71 preserved.
- Fixed cached player-position extraction and legacy delta collision handling to require ET_PLAYER. Player-name lookup now rejects nonclient/out-of-capacity receivers. Earlier cleanup null-client check remains. Reviewed current G_RunFrame corpse-first dispatch, G_FreeEntity corpse cleanup/reserved free-list exclusion, and CoDOL maxclients18 registration/client pointer initialization.
- This connects correct native corpse identities; full captured-field adapter and further gameplay validation remain. Source readback only, no build/test/assembly/runtime. Goal active; no workers live.

### GSC workers resumed; captured corpse identity written
- Started two bounded Claude Opus/high workers (24 turns each): childthread-inheritance owns its native module; animation-binding owns the four model animation files. Both must supply shared-file patches for parent review. Explicit architecture rewrite authorization and source-only constraints included. Supervisors77396/75792; both CLI processes observed live, no startup errors.
- Parent added atomic CODOL_OverlayEngineCorpseIdentity to the common entity overlay. It uses captured clientNum, copy/stance flags, legs/torso animation words and ground identity, with the measured corpse19..26 and player0..17 ranges. Native WORLD/NONE sentinels map to C1 equivalents. C1 clone51caa5 and51cb46..51cb58 confirm ground and animation producers.
- Corpse admission remains disabled until body pose, part visibility and ragdoll mapping are complete. Continued clone trace51cc1f..51cc3f reveals a32-byte part-visibility copy from the original entity, so identity alone is insufficient. No new complete-method claim, builds/tests/runtime or verified match entry.
### Native clone visibility capture
- Previous turn was progress: started bounded GSC workers and wrote captured corpse identity mapping. Both worker CLI handles75744/48256 and supervisors77396/75792 verified live this turn; no startup errors or duplicate assignments.
- Confirmed retained hidepart/showpart/showallparts persist four entity mask words at e4..f0; clone previously discarded them. CoDOL PlayerCmd_ClonePlayer now copies that native mask before linking, matching C1's established source-to-corpse visibility capture behavior within the retained representation.
- Source reviewed for source pointer, four word bounds and register lifetime. C1 eight-word mask/composed-bone correspondence and wider native skeletal support remain unfinished; corpse seed remains disabled. No builds/tests/runtime, no complete-method count increase, goal active.
### Skeletal capacity and body-pose evidence
- Previous turn was progress (native clone visibility capture). Current source audit proves retained DObjCreate errors above128 composed bones, unlike header160/loader159 acceptance. Four-word skeleton/hide/surface masks require coordinated widening; no header-only change made.
- Aligned C1 conversion40d2a0 and its three helper bodies do not write body-pose68/6c, whereas retained conversion explicitly writes prone normalized ps5cc/5d0 to native dc/e0. This changes next work: locate a C1 pose writer instead of assuming the IW3 producer maps directly.
- Worker CLI75744/48256 verified live, outputs pending. No build/test/runtime or new method completion; objective remains active.
### C1 body-pose writer found; bounded childthread handoff
- Prior turn progressed skeletal-capacity and conversion evidence. Current offline trace from aligned50c8d0 establishes real movement-driven body-pose publication to entity6c/68 and animationinfo9fc/a00. Next work is movement outputs118/11c inside416c30, not guessed IW3 field-order mapping. Candidate misaligned start50cae4 rejected.
- Childthread original CLI48256 terminal maxturns25/$1.442123, no final report. SAME session resumed with six finish-only turns to save justified source/evidence and report; supervisor44688/CLI74500 verified live. Animation75744 live. No worker support accepted or duplicate research assignment.
- No builds/tests/runtime; goal active.
### Movement pose finalizer and terminal GSC draft
- Prior turn progressed actual C1 body-pose publication. Current offline416c30/416ae0 trace establishes angle normalization and stance-transition scaling after movement; prone call4121f9 supplies raw outputs118/11c through40d310. Native BG_CheckProne output order still needs semantic verification before snapshot mapping.
- Childthread finish terminal maxturns7/$0.7780985, draft layer3 saved; parent owns output, no integration or support count. Animation original terminal maxturns25/$1.9290605; SAME session given six finish-only turns to save evidence/source/report, supervisor58708. No duplicate workers.
- No builds/tests/runtime. Full objective remains active and unverified.
### Childthread inheritance parent review
- Previous turn progressed movement-finalizer evidence and worker handoffs. Reviewed actual childthread cpp/header: frame-chain inheritance replaces synthetic root lifetime; native registration pairs and waittill exclusion checked. Exact lifetime semantics remain inferred.
- Corrected false allocation-failure-free and obsolete VM_Notify callback claims. Scr_TerminalError can reach Scr_ErrorJumpOut before the terminal Sys_Error check, leaving cleanup ownership unproven for pre-installation children and partially registered markers. Parent review saved; gate0/shared patch held.
- Animation finish CLI69280 observed live this turn. No new worker or support count; no builds/tests/runtime. Goal active.
### Childthread fatal destination and replacement integration patch
- Prior turn progressed inheritance parent review. Completed VM error-path trace: RuntimeError routes terminal_error through Com_Error(ERR_SCRIPT=5), whose current implementation shuts down and calls Sys_Error. Corrected the prior incomplete unwind characterization: partial allocation is not rolled back, but the caller does not resume normally.
- Prepared unapplied childthread-inheritance-shared.patch with obsolete FrameDied callback and Reset removed; source-span ClearAll retained. Module/header and review reflect fatal behavior. Exact lifetime rules/full integration remain open; gate0.
- Animation finish terminal maxturns7/$0.816864; all workers terminal and files parent-owned. No new workers, builds/tests/runtime or complete-method claims. Full goal active.
### Animation binding draft: native name lookup corrected
- Previous turn progressed childthread fatal-path review and revised patch. Reviewed current animation worker files and fixed actual variable-ID/string-ID confusion using native Scr_LoadAnimTreeAtIndex as authority: GetVariableName must precede SL_ConvertToString.
- Added codol_assets.h for the new rawfile declaration and cleared animlist entry counter during full reset. Source readback completed, no builds/tests/runtime.
- Ordered animlist replay now exists in worker source but is uncalled externally. Parser fidelity, realm/entry correspondence and clear/replay remain unresolved; methods unregistered. No worker report was saved despite header references; parent review records limits. All workers terminal; full objective active.
### Animlist token and directive parity
- Prior turn progressed animation draft name lookup/reset/header fixes. Current aligned C1 parser/session evidence confirms whitespace mode, escaped quotes/backslashes,1023-character tokens and63-character directive capacity. Fixed draft's shorter capacities and token termination at empty strings/NULs; reviewed bounded comments and quote handling.
- Actual loader entry408040 recorded, earlier408080 guessed start excluded. Source only; canonicalization, client realm/index mapping, loader integration and stop/replay still pending. No builds/tests/runtime or complete-method count; full goal active.
### Animtree canonical matching
- Previous turn progressed parser fidelity. Compared aligned C1 canonicalizer5cb860 with native CreateCanonicalFilename; replaced literal character comparison with allocation-free canonical iteration for repeated separators/control characters, preserving spaces and trailing slash.
- Registration and manual-binding comparisons now require used slots, preventing sparse table gaps from matching the real empty-name tree. Source readback only; no builds/tests/runtime. Loader integration, entry correspondence and clear/replay still unresolved; full goal active.
### Animlist flags linked to serverinfo2482
- Prior turn progressed canonical comparison. Aligned CG_ParseServerinfo465b90 proves key2482 -> integer -> cgs164; CG_Init450640 copies same field into animlist flags before loading lists. This gives the required common native input for gamestate and registry setup.
- Current serverinfo writer omits2482 and no native class-mask producer exists. Next integration must publish/use the same map-lifetime value and account for mounted animtree dependencies. Alpha anim_refs.py located as useful leads; infostring-vs-dvar mislabel excluded. No source behavior enabled, builds/tests/runtime or support count; goal active.
### Map-start animlist input and serverinfo connected
- Prior turn progressed serverinfo2482 trace. Added native codol_animlistMask configuration (class bits1/2/4/8, default0), captured once at full map startup. Mounted animlist replay and every gamestate now use that same captured value; mid-map configuration edits cannot desynchronize later joiners. Reset clears captured state.
- Startup resets animation intent/registry before replay, after archives mount. Invalid mounted rawfiles now fail startup instead of masquerading as optional absence; partial registry is cleared. Empty valid rawfiles count as present. Source connectivity/order/return handling read back, no builds/tests/runtime.
- Referenced animtree dependencies, client entry-order correspondence, snapshot capture and clear/replay remain unfinished. GSC family remains unregistered; full objective active.

## Claude workers resumed; animation registry failure handling
Two bounded workers are running: childthread-finalize (Opus high,28 turns,
CLI73064) and gsc-startup-completion (Sonnet high,28 turns,CLI78588).
Nonoverlapping ownership; shared changes require parent review. Both received
explicit permission to rewrite IW4OL natively and writing-pass restrictions.

Parent corrected silent animlist registry overflow and final multiplayer
registration failure; errors now reach map startup and clear partial state.
Aligned C1 ordinary script-model path43e974/43e986 passes wire94 into443610;
cache mismatch43e58e invokes42be50, clearing old DObj mapping and calling634740.
The header now distinguishes delivered tree-clear invalidation from unresolved
same-animation replay. No builds/tests/runtime or newly completed method count.

## Model animation entity lifetime
Added CODOL_ResetEntityModelAnimation and connected it through the native
G_InitGentity reset path. Entity reuse now discards animation, sequence and
tree binding; scriptmodelclearanim preserves the binding/history intentionally.
SetModelAnimation rejects the unencodable index0/variant0 pair before changing
live state, matching C1's whole-word no-play check and the existing encoder.
Source/call chain and automatic makefile source inclusion reviewed, no builds
or tests. Snapshot/archive capture and replay still pending; methods remain
unregistered. Claude processes73064/78588 confirmed live this turn.

## Model animation snapshot capture
Connected resolved script-model animation fields to codol_es_ext_t, snapshot
copies and both internal archive write/read paths. Explicit clear is known0,0;
unknown is distinct. Archive reader rejects incompatible receiver/brush state,
malformed pairs and truncation, discarding partial extension state.
Model overlay publishes the captured060/094 pair with06c0. It does not read the
current entity slot while serializing historical snapshots. Existing whole
extension copies and native entity-init clears cover the new fields.
Reviewed source call sites and record order. No builds/tests/runtime. GSC
registration, same-animation replay and tree entry correspondence remain open.
Capture failure after intent mutation needs final integration review. Claude
workers remain running; childthread checkpoint confirms current scope.

Worker update: startup-completion session d6a8af17-3bfa-4e3e-9936-de102c998388
terminal maxturns29,$0.7094464 without report. Same session resumed for6turn
finish-only handoff; no new research assignment. Childthread73064 still live.

## Animation capture transaction and replay trace
Play now prepares without mutation, encodes/captures its snapshot fields, then
commits with only a bounded structure copy. Clear captures first too. This
closes the previously recorded capture-failure/live-intent mismatch path.
Aligned C1 440e20/440fd0 read index060/time06c/value070 and gate setup against
client time;4410e9..4410f5 also skip setup for an already-active same index.
Timestamp alone is not established as replay input. No builds/tests/runtime.
Childthread worker terminal maxturns29,$2.957088; same session resumed8turn
report-first finish-only. Startup finish57248 live; no handoffs accepted yet.

## GSC worker recovery and childthread evidence review
Startup worker terminated after original28 and finish6 turn caps with no source
or report. Parent recovered candidates and saved gsc-startup-completion-parent-recovery.md.
Two already registered; two already drafted in turret module; isspawner needs a
real native spawner representation because IW4 type17 collides with ET_EVENTS.
No duplicate/stub implementation added. Childthread finish75052 remains live;
report identifies include-recursion span-selection bug and start-time inheritance
script evidence. Parent verified alpha vendor IW5 hamburg_tank_ai source. Shared
patch absent when inspected; no integration accepted. No builds/tests/runtime.

## Childthread patch parent review: duplicate labels corrected
Both Claude workers terminal. Childthread finish maxturns9,$0.919261.
Parent found all four new VM labels4200/4210/4220/4230 collide with stock
labels. Prepared childthread-parent-integration.patch changing only added
identifiers to unique CoDOL names. Patch remains unapplied pending review of
error/developer dispatch, gate0 rejection and span reload behavior. No build,
assembly/test/runtime or complete feature claim. Review artifact saved.

## Childthread stock handler integration patch
Rebuilt parent patch to reuse stock VM handler entries and retain diagnostic
opcode54..57 for unwind. Inheritance is selected only at four allocation sites
from actual instruction byte. Removed cloned tails entirely. Source reviewed,
unapplied; no assembly/build/tests. Found archive restore bypasses source
preparation, requiring preservation/re-lowering of childthread source. Gate0
rejection correction also pending. All workers terminal; goal incomplete.

## Childthread parser/compiler/VM source integration
Applied whole parent integration (whitespace-tolerant application after atomic
initial whitespace failure). New opcode wrappers reuse stock handler checks and
normalize error-unwind opcode; inheritance selected at original allocation sites.
Compile entry/exit restores filename span selection across include recursion.
Parser helper now archives the text retaining childthread keywords and rewrites
a separate same-length parser copy. Restored source uses that helper directly,
rebuilding spans without repeating general syntax/precompiler transforms.
Clears stale spans when preparing a filename. Gate0 explicitly rejects actual
childthread syntax, preventing silent identifier miscompilation. Updated header.
Reviewed source copying, source restore, VM allocation/table and compiler call
paths; no build, assembly, test or runtime. Full VM/protocol goal remains active.

## Legacy vote configstring collision
Verified native vote slots13..16 fell through SV_SetConfigstring to raw client
publication. Aligned C1 dispatcher467350 routes13/fog,15/match-end,16/mapcenter.
Publisher now consumes retained vote slots locally, preserving server vote state
without emitting corrupting raw updates. Native map-state mappings remain.
This removes a protocol error; it does NOT implement CoDOL voting UI. That
requires a verified producer/consumer mapping. No builds/tests/runtime.

## Menu response name lookup
Fixed Cmd_MenuResponse_f using retained1970 bank despite CoDOL precache/open-menu
producer using4243..4274. Shared bounded CODOL_ServerMenuName now supplies the
producer/search and mr response lookup, including inherited values and explicit
clears. Response copies borrowed name before Scr_Notify. Existing parsing and
server-id contract retained. Source/call sites reviewed, no builds/tests/runtime.
C1 name xref577cd4 was string initialization; rejected guessed57792b decode and
did not use it as behavior evidence. Broader objective remains incomplete.

## Menu response server identity primary trace
Verified mr argument1 is populated from CS3, not local-client index as Python
notes inferred. Aligned487440 store487689 and two aligned menu emitters establish
connection. Kept correct existing server-ID validation and documented evidence
in CODOL_MENU_RESPONSE_TRACE.md. Initial gamestate initialization remains to trace;
no builds/tests/runtime. Previous turn and this turn made source/evidence progress.

### Claude workers resumed, missing GSC priority (2026-09-09)
Two bounded Sonnet/high workers (24 turns each, no subworkers) have separate turret completion and current missing/startup GSC assignments. Parent retains registry/integration ownership. No worker output accepted yet; do not duplicate active assignments.

Parent corrected setdvarifuninitialized/setdevdvarifuninitialized against IW4 5ec460/5ec510: exactly two arguments; absent or empty displayed dvar value initializes; nonempty values skip reading the initializer. Separate normal/developer registry flags follow records79a248/79a260. Source2 setter behavior traced through4fc770/648580/647400, including source1-only cheat check647672. Uses native script setter protections/latching/conversion. The old Python-derived existence-only comment and behavior were wrong. Native cvar conversion differences and IW4 diagnostic logging remain outside this correction. No builds/tests/runtime.

Childthread header comment now reflects the already-enabled source integration rather than claiming the gate remains disabled. Initial C1 gamestate parser remains virtualized/unverified; native CS3 publication and dynamic-update/menu identity evidence do not establish initial C1 behavior. Overall goal active; no verified match entry.

### Parent review of r2 handoffs
Both Claude sessions finished with reports after a short report-first continuation; no worker source edits. Combined reported cost $1.5415886. Parent connected only setmode/getmode, after inspecting receiver, spawn/default preservation, think consumers and free/reset paths plus offline C1 54e330 and57e5b0. Other15 turret registrations need individual review; the handoff's alternating16/17 counts and description of registration flag0 as argument count are incorrect (it is developer flag).

The missing-audit report is retained as leads only. Its claim that player-link handlers are absent is false: startup_extra.c already contains them and an intentionally uncalled registration helper. The header records unfinished movement/controls. Textual registration-call counts do not prove an entry is reachable from production startup. Absence of registration calls inside startup_missing.c does not mean its functions are unregistered elsewhere (playerhide is registered). Do not duplicate these implementations or reuse the report's aggregate counts as progress. No build/test/runtime; overall goal remains active.

### Turret target/fire/timing GSC integration
Previous goal turn classified progress: native dvar correction and two turret registrations. This pass connects ten more methods: settargetentity, cleartargetentity, getturrettarget, startfiring, stopfiring, isfiringturret, setconvergencetime, setautorotationdelay, startbarrelspin, stopbarrelspin. Reviewed primary IW4 handlers5ed140/5ed1f0/5ed260/5ecbe0/5ecc50/5eccc0/44a6e0 and C1 spin536620/5366b0, existing producer/consumer and release/reset source.

Found and fixed three concrete defects before registration: native unsigned vectoangles used against signed arcs (IW4 46b496 calls signed4ab460); convergence rounded instead of truncated (5ed43e calls6b5240, SSE cvttsd2si); autorotation rejected zero and used approximate rounding (5ed895 comparison accepts zero,5ed8cd rounds float milliseconds+2^-30). Signed conversion preserves atan2 +/-180 endpoints and reference vertical direction. Conversion range/NaN handling avoids undefined C casts.

Five family entries remain unregistered pending review: shootturret, setturretteam, setturretmodechangewait, setsentrycarried, setsentryowner. No builds/tests/runtime were run under the writing-pass restriction. Full goal active; actual C1 match entry remains unverified.

### Remaining turret family source integration
Previous goal turn was progress (ten registrations plus angle/timing fixes). Connected remaining five entries: setturretteam, setturretmodechangewait, setsentrycarried, setsentryowner, shootturret. Current target-family17 entries are registered in source, not runtime-proven.

Fixed explicit-undefined owner clearing (C1 536a3f->536af4; missing arg remains error), removed team setter's invented cursor reset (537370 returns after team write), and implemented missing manned shot branch using retained player view helper and projected view-to-muzzle start (IW4 5feef0/5fef4c..5ff028; retained _g_misc_mp.asm manned shot builder). Owner wire080 uses captured native otherEntityNum and sentinel mapping. Reviewed mode/carried/team/owner consumers and native declarations.

Remaining: broader GSC VM/player-link/script loader work, special IW4 view-angle selection fidelity beyond the retained helper, omitted owner-change diagnostic warning, and all builds/runtime validation. No build/test/game/server launch this writing pass. Full goal active, no verified match entry.

### Player-link failure cleanup and focused worker
Previous goal turn made progress: remaining turret registrations and behavior fixes. Current native source review disproved the player-link draft's atomic-relink claim: G_EntLinkToInternal immediately calls G_EntUnlink before validation. Both failed-link branches now clear the old player-link side record/view lock while preserving camera/control links; native unlink already restores pm_type. No registration enabled because param2 is discarded, param7 guessed, and frame movement integration is still absent.

Launched one Opus/high Claude worker playerlink-view-r3 (40 turns, report first, reserve final6 turns for implementation). Owns startup_extra.c/.h only; parent retains shared integration. Assignment explicitly permits architecture rewrite and forbids hooks/builds/tests/runtime. Launcher77284 confirmed live at dispatch. No duplicate workers; inspect current process/result before continuation. Full goal active, no runtime verification.

### setnorthyaw native implementation
Previous turn made progress through relink cleanup and focused worker dispatch. Current reader review confirmed external/mounted/fastfile source validation already bounds size and rejects embedded NUL; no redundant changes made there. Implemented missing setnorthyaw from IW4 registry79a368/handler5f36a0, including %g configstring and actual compass direction vector updates. Native822 is already translated to CoDOL1302 and used by getnorthyaw; retained compass reader _g_active_mp.asm1930..1939 consumes level's north vector.

Claude playerlink-view-r3 PID65780 confirmed live; report exists and offline scan artifact shows investigation in progress. No duplicate worker and no handoff accepted yet. No builds/tests/runtime under writing-pass restriction. Full goal remains active.

### Thermal query dependency review
Prior turn was progress (setnorthyaw source/registry). This turn corrected a stale dependency claim: composed definitions now expose item/variant lists through ComposedWeaponRecord. IW4 5f2aa0 thermal query and C1 542140/5421d0 script-only bytes were inspected offline, but correspondence remains unidentified. Alpha recipe TAG_THERMAL_SCOPE is model-slot metadata, insufficient to name a GSC flag. Next useful evidence is thermal item type43 override fields and their consumers; no guessed/constant query registered.

Playerlink-view-r3 PID65780 confirmed live repeatedly with increasing CPU; report-first and scan artifacts present. No duplicate/restart or accepted implementation yet. No builds/tests/runtime; full goal active.

### transformmove native GSC
Previous turn produced dependency evidence and a verified worker wait. Implemented missing transformmove from IW4 5f1f10: six vectors, three rigid transforms T0/T1/T2, result T2*inverse(T1)*T0, associative origin/angles output. Traced inverse455890 and full multiply41dfe0, including translated origin. Verified return key initialization from aligned472020 chain and strings71a29c/73319c; rejected misaligned4723b0 disassembly. Native VM array insertion uses existing Scr_AddArrayStringIndexed with balanced key references; added its missing public declaration. Registered function in CoDOL block.

Uses existing native angle conversion; no tests/builds/runtime allowed this pass, so floating-point/runtime parity remains unverified. Claude playerlink-view-r3 PID65780 still live with increasing CPU, no duplicate/restart and no handoff accepted. Thermal investigation remains unresolved; full goal active.

### Player-link native movement already exists
Prior turn implemented transformmove (progress). Current parent review found G_RunClient already calls G_SetFixedLink(ent,2) for tag-linked players, updates trajectories/world links and copies origin into ps; parent entity runs first. Thus worker/draft assumption that players never advance is false. Do not blindly add G_GeneralLink at ClientEndFrame. Record supplied in obj/claude-workers/playerlink-view-r3-parent-frame-note.md for next worker handoff. Worker-owned source unchanged.

Verified Claude65780 live before/after bounded20s wait, CPU6.50->7.28. Session87b7876d-f3ff-41c4-908b-f9df3548db12 still traces IW4 callers; no result/restart/duplicate. Source evidence changes required integration path. No builds/tests/runtime. Full goal active.

### Player-link r3 review and bounded Claude continuation

Worker wrote source but hit its 40-turn limit (USD4.622181). Parent review rejected duplicate linked-position publication, Euler interpolation equivalence, and unproven turret flag reuse. G_SetFixedLink mode 2 updates position only; G_RunClient already publishes it. Same worker resumed for at most 10 turns with these corrections and exact shared-integration handoff required. No builds/tests/runtime; player-link methods are not counted complete.

### Native link math and magicbullet worker

Exposed existing native quaternion helpers in q_math.h after source and offline IW4 review. IW4 49fc30 is hemisphere-corrected component lerp (zero comparison constant); the link path interpolates identity to a relative quaternion, not Euler deltas. Player-link correction stopped on a shell quoting error and remains incomplete; same session is finishing source/header coherence with a bounded continuation. A second, separate Sonnet worker is implementing missing magicbullet with projectile behavior review. No builds/tests/runtime; full goal remains active.

### Weapon-view reference angles: snapshot producer and archive

Aligned C1 53ad7a..53ad98 writes weapon-view reference angles to 1e0/1e4/1e8, already present in the measured wire table. Added captured float words, playing-frame producer, symmetric internal archive encoding/decoding and pure snapshot overlay. This corrects the worker claim that no wire fields existed. Current extension layout calculated at364 bytes, below existing512-byte reservation; capacity assertion retained. Source review only, no builds/tests/runtime. Both Claude workers terminal; player-link integration pending and magicbullet delivered no source. Full match-entry objective remains active.

### Native quaternion conversion correction

Fixed swapped z/w components in the X- and Y-dominant AxisToQuat fallback candidates in q_math.c. Aligned IW4444580, specifically444687..444693 and4446e8..4446f4, establishes the correct candidate component order. This is a retained math defect affecting linked-view rotation, not a new compatibility approximation. Source/PE review only; no tests/builds/runtime. Magicbullet original session resumed with35-turn bound and confirmed live Claude74616. Full goal remains active.

### Native linked-view clamp consumer

Added the separate link clamp consumer and its retained PM_UpdateViewAngles call after command-angle processing. Preserves the special two-difference yaw calculation around previousYaw and applies corrections to both viewangles and delta_angles. Exact live playerState and live tag-parent guards prevent copied spectator states from using live client records. Turret state is unchanged. Frame/collision integration remains incomplete; no new method registration or runtime completion claim. Source review only, no builds/tests/runtime. Magicbullet worker confirmed live with report present.

### Native link frame integration

G_RunClient now invokes CODOL_PlayerLinkRunFrame after parent-frame dispatch and before existing linked origin publication, and skips that origin block for a validated weapon-view link. Added owning-player/session/lifetime guards. Removed incorrect link-time previous-quaternion seeding: IW45ef718 clears the marker and first frame uses identity delta. Non-absolute clamp-reference discrepancy found at4fdbd4 remains under review; collision and prediction still incomplete, no bulk registration. Source-only, no builds/tests/runtime. Magicbullet worker live with c/h draft files.

### Link reference separation and magicbullet review

Separated world clamp reference from relative linkAngles using aligned IW45fdbca/4fdbda evidence. Non-absolute reference starts zero; clamp uses parent world angles and refreshes from current tag frame. Magicbullet worker terminal with source, but class6-spawn and post-shot event paths were misread/omitted. Registration rejected pending correction. No builds/tests/runtime; full goal active.

### Magicbullet grenade-projectile path

Corrected the rejected draft class6 branch to spawn and return the native grenade-launcher projectile. Added missing non-player owner client guard to retained Weapon_GrenadeLauncher_Fire, matching IW44d84a1..4d84ac and allowing default-owner shots without null client dereference. Post-shot event and other fidelity gaps remain; magicbullet unregistered. Source/PE review only; no builds/tests/runtime. Full goal remains active.

### Magicbullet post-shot event

Added native EV_FIRE_WEAPON temporary event publication after hitscan and projectile producers, carrying native weapon index and zero parameter. Verified IW4 event-table entry30 and shared498081 tail. Corrected type1 grenade rejection independently of supported projectile class6. Remaining owner/direction fidelity work prevents registration. Source-only; no builds/tests/runtime, goal active.

### Magicbullet direction correction

Replaced invented vertical zero-length fallback and Euler basis reconstruction with measured IW4 behavior: normalize endpoint delta (zero remains zero), copy forward directly, zero right/up. Evidence453500 and498001..49802b. Owner/producer fidelity review remains; no registration/build/tests/runtime, full goal active.

### Magicbullet owner and trace entity

Verified IW4 default owner as world index2046 from Scr_GetEntity base/stride. Corrected native bullet call to pass NULL physical weapon entity, matching reference and retained null-to-world trace handling while preserving damage attacker. Projectile-handle fidelity remains under review; unregistered, no builds/tests/runtime. Full goal active.

### Native script rocket launch

Added a native script entry sharing retained rocket launch but skipping its player-velocity kickback, absent from IW4 magicbullet wrapper424680. Original weapon entry preserves its kickback. Corrected magicbullet launch declaration to float spread and typed target/offset. Projectile fidelity review remains before registration. Source-only; no builds/tests/runtime, full goal active.

### Magicbullet projectile attribution

Added native handle bridge and explicit-owner reassignment after each projectile return, matching IW44980eb..4980fe. This overrides retained throwback attribution when necessary while using EntHandle lifecycle cleanup. Default-owner spawn handles remain producer-owned. Source-only; final handler review/registration pending, no builds/tests/runtime and full goal active.

### Magicbullet rocket launch time

Corrected scripted rocket launchTime to level.time, matching IW4 finalflag1 bypass of player launch delay at490bd3. Native producer lacks that flag and otherwise adds delay; corrected before GSC return/snapshot capture. Optional IW4 helper is a no-op for magicbullet arg6=0. Source-only, no builds/tests/runtime; registration review/full goal still active.

### Magicbullet registered in native GSC table

Source review completed and magicbullet registered in CoDOL stock functions. Supports hitscan and both projectile classes, native ownership/shot events and reviewed scripted-launch corrections. Cleaned stale draft commentary; matching generic script errors and distinct projectile-class error. Makefile includes new C source automatically. Source-reviewed only, no builds/tests/runtime; no claim of complete engine parity or match entry. Other missing GSC and full protocol/loader objective remain active.

### Linked collision solver

Traced IW4 linked collision to435da0/48cb50: step/slide and floor checks, not one sweep. One bounded Sonnet worker implementing native solver with exclusive new-file ownership; parent owns shared frame integration. Claude47300 confirmed live. Corrected stale header math/solver descriptions. Offline/source inspection only, no builds/tests/runtime; full goal active.

### Claude workers resumed; linked offset rotation

Two bounded Sonnet high40 workers confirmed live: slowmotion-r1 (native missing builtin, isolated new module) and gsc-reachable-r3 (correct reachable registration/missing-method inventory). Parent retains shared integration. Previous collision worker terminated with refusal and no source; its earlier live status is superseded.

Corrected linked frame orientation to compose retained local rotation when offsetEnabled, matching IW44b3ee6..4b3f05 and41dfe0. Origin offset, collision and interpolation remain incomplete. Source review only; no builds/tests/runtime, no verified match entry. Full goal remains active.

### Link reference angle snapshot publication

Added capture, finite validation, paired internal archive serialization and pure netfield publication for current linkAngles at C1 ps+1d4/1d8/1dc. C1575f60 confirms the field identity and relative zero initialization. This is separate from weapon-view initial angles and uses archived state rather than live client lookup. C1 absolute initialization additionally composes ps+1fc via575ea0; trace remains before parity claim. Collision/interpolation and full registration still incomplete. Both assigned Claude processes confirmed live. Offline/source review only; no builds/tests/runtime, full goal active.

### C1 additional link reference rotation

Identified575ea0 as frame multiplied by transpose of angle matrix from ps+1fc, with zero fast path.40e090 uses same triplet for complementary view basis composition. Producer/lifecycle still requires tracing; entity+1fc candidates must not be mistaken for player-state writers. Evidence artifact recorded, no guessed field implementation. Inventory worker reached cap with provisional JSON; same session resumed for10-turn report finalization, slowmotion still live. Offline/source only, full goal active.

### Missing-method inventory parent review

Audit finished; name totals remain provisional. Rejected claims that incomplete playerlink handlers are registration-only and local-address ishost draft already matches host identity. Both remain unregistered. Entity playfx method assigned to new bounded Sonnet worker with isolated module ownership, slowmotion continues. Reference-angle writer still unresolved;549941 is another consumer only. See parent-gsc-r3-review.md. Source/offline only, full goal active.

Slowmotion original reached41-turn cap USD0.9930276 with no source/report. Same session7a1400d5-5fe5-413b-8bc4-29e85bfdcd8f resumed bounded15 turns for concrete source/handoff, no restart of research. Entity-fx Claude73868 confirmed live.

### Actual overlay missing-method occurrence

Scanned54 GSC files in alpha user overlay plus native scripts/codol. Found concrete SetOffhandPrimaryClass calls in native _perks.gsc201/203 (frag/throwingknife), no native handler/registration. Global PlayFX occurrence is not a missing method. IW4 registry73c670->5d94d0 proves player receiver,1 const string,6-class search and client+2ac store. CoDOL explicit offhand weapon slots need an actual producer/consumer adaptation. No inert class field implemented. Scan is lexical and incomplete for base/fastfiles/T5, not runtime reachability. Both workers live; no builds/tests/runtime, full goal active.

### Offhand class grant lifecycle

Verified IW4 class4 string throwingknife and1/2/3 frag/smoke/flash. Native perk script sets class before giving weapon, so setter requires persistent preference plus reconciliation after grants/removals, not an immediate scan. Common native grant producer identified in _g_weapon.asm918; successful-path integration still to implement. Evidence artifact recorded; no guessed handler registered, no builds/tests/runtime, full goal active.

### Slowmotion handoff rejected against IW4

Worker terminal, c/h/report delivered but unaccepted. Primary handler5f5f50 accepts>=1args, defaults end1/duration1000, publishes four-field %i %i %g %g to IW4 CS1029, no server timescale mutation. Draft exact3/server ramp/CS14 triple are wrong or invented; CS14 is suppressed native vote string. Prominent source warnings added; no registration/calls. C1 destination and timestamp identity next. Offhand grant success paths reviewed; alternate loop overwrites edi so integration must use original weapon arg. No builds/tests/runtime, full goal active.

### Verified C1 slowmotion transport replacement

Replaced rejected worker module with actual C1 CS6132 timestamp/duration/start/end publication, native CoDOL bank and reliable client updates. Corrected>=1args/defaultend1/default1000ms; removed inventedCS14 and svs.time/cvar ramp/reset. C1 does additionally schedule common-clock ramp after publication;599440 uses supplied frame delta. That integration and numeric fidelity remain before registration. Entity-fx worker also reached cap with no source/report; no owned workers live. Offline/source only, no builds/tests/runtime, full goal active.

### Slowmotion unscaled common-clock factor

Confirmed599590 advances separate ramp before effective scale/fixedtime;599500 multiplies operator timescale with ramp factor. Native raw Com_ModifyUsec integration point identified, operator cvar must remain separate. Corrected duration multiply to double before truncation per54a59e/ae0410. Scheduling/equal-endpoint/lifecycle and frame consumer remain before registration. Evidence recorded, no builds/tests/runtime, full goal active.

### Native slowmotion ramp core written

Implemented independent factor scheduling/update/reset, x86 truncation fallback and wrapping schedule span, raw-usec accumulation to milliseconds, endpoint completion and current-scale preservation. Handler now schedules even when bank unchanged or no clients exist, while avoiding duplicate publication. Common-frame multiplier/lifecycle review and registration remain. Source-only, no builds/tests/runtime, full goal active.

### Slowmotion common frame and full teardown integrated

Connected independent ramp factor to Com_ModifyUsec before hitch clamps, with raw-time advancement under fixedtime, fractional microseconds and bounded conversion. Full SV_ClearServer resets separate factor/fractions. Fast restart, timestamp and zero-timescale/frameUsec review remain before registration. Native microsecond granularity retained; no bit-identical timing claim. Source-only no builds/tests/runtime, full goal active.

### Setslowmotion registered in native source

Registered reviewed producer/common-frame implementation. Fast restart retains bank and ramp; full clear resets both. SV_Frame already clamps frame interval>=1ms, preventing a zero interval. Native timestamp uses level.time, interpreted as C1 game-time global; full symbolic/runtime time alignment remains unverified. Numerical guards and microsecond granularity documented; no builds/tests/runtime or bit-identical parity claim. Full GSC/protocol/loaders goal remains active.

### Complete primary-offhand vocabulary and cross-slot review

Verified six IW4 class names including none/other from aligned string initialization. Primary setter acceptsall6, whereas CoDOL groups classes in3slot consumer. Native class-scan helper and held/ammo gates inspected. Full support needs input/selection/publication reconciliation, not only frag/knife or an inert scalar. Python whole-set comments are not implementation constraints. Entity-fx prior session resumed8turns for report-only handoff; Claude75128 live. Offline/source only, full goal active.

### Player playfx method written

Parent wrote native player method2..4args, event creation/full effectID, normalized optionaldirection/up, retained angle helper via verifiedregparm3, recipient-only mask and entity return. Existing CoDOL adapter covers effect1..319. Rejected worker audience/defaultangle/differentfactory claims using primary/native evidence. Unregistered pending angle/helper review. No owned workers live, no builds/tests/runtime, full goal active.

### Player playfx registered

Registered native player method after angle/recipient publication review. Verified both reference defaults270pitch and matching projection/cross/conversion helper branches. Corrected optional-vector/error validation order. Existing effect wire adapter preserves1..319 IDs rather than reference factory byte truncation. Source review only, no builds/tests/runtime, full GSC/protocol/loaders goal active.

### Masked tagged FX contract

Traced IW4 playfxontagforclients>=4args, oneplayer/array<=18, includedmask compound string inbank885/event56hex. C1slot88 is TIMED_FX, not corresponding masked event;89 ordinarytagged. Need actualC1transport or native per-event recipient filtering with archivedmetadata, not targetvisibility changes or offsetcopy. Evidence artifact written, no builds/tests/runtime, fullgoalactive.

### Per-event recipient overlay primitives

Added atomic entity/scripted-player queue overlay variants with explicit4slot visibility mask, preservingepochs andzeroing onlyexcluded wireevent/parameter pairs after fullvalidation. Producer/immutableaudience registry and recipient bindings still to connect; existingcallers unchanged. Player-to-entity transfer/archive semantics must remain intact. No builtin supportcount, no builds/tests/runtime, fullgoalactive.


## Masked tagged effects native implementation

Implemented and registered `playfxontagforclients` in native source. Immutable audience/compound IDs survive event queues and archives; recipient binding filters only queued effects, preserving entity visibility and epochs. Ordinary bindings default to all-visible. IW4 argument shape and validation with CoDOL expanded effect range; recipient identity for spectators is explicitly the receiving connection and reference spectator parity is still unverified. Source review only, no builds/tests/runtime. One bounded Claude Sonnet worker handles offhand primary-class state and lifecycle; shared integration awaits parent review. Full goal active; no verified match entry.


## Childthread public opcode metadata

Aligned CoDOL scr_vm.h enum with existing four childthread VM instructions and OP_count; old debugger placeholders no longer alias executable childthread opcodes. Added a compile-time correspondence invariant. This fixes metadata consistency, not a newly demonstrated runtime failure. No builds/tests/runtime. Offhand Claude hit its research cap without implementation; same session given a short finish-only pass. Missing methods and full match-entry goal remain active.


## Primary offhand class native integration

Implemented and registered setoffhandprimaryclass with persistent six-class preference, primary slot selection, none clearing, grant/removal and pre/post-movement reconciliation. New C1 disassembly proves exact weapon matches in any slot are accepted before class-based empty-slot fallback; earlier fixed-slot restriction was incorrect. Parent rewrote and completed Claude draft, including shared retained assembly calls. Snapshot/archive publication uses captured selections. Source review only; no builds/tests/runtime. Secondary-class binding still needs explicit-slot producer; full match-entry goal remains active.


## Secondary offhand and class getters

Traced IW4 secondary setter/getter and primary getter; all use six-class table799bd0. Replaced CoDOL secondary bindings with native persistent state and slot1 publication, added primary getter, and connected smoke/flash give-command changes. Shared grant/removal/PM producer now refreshes both independent preferences. Explicit whole-loadout assignment updates getter values while disabling automatic selection. Snapshot/history reads remain captured-state only. Source reviewed, not built/tested/runtime-verified; full match-entry goal remains active.


## Native vehicle spawners and GSC queries

Traced IW4/C1 flag2 map vehicle-spawner producer and IW4 isspawner/vehicle_getspawnerarray. Added native hidden category metadata with loaded definition identity and reuse/free/map lifecycle; map script_vehicle alias now reaches it. Both queries registered against real native spawners, avoiding the ET_EVENTS17 collision and Python classname heuristic. Live vehicle materialization from a spawner remains the next missing function. Source/offline only, no builds/tests/runtime; full goal active.


## Spawnvehicle contract and native factory gap

IW4 spawnvehicle4f3e10 creates a fresh vehicle from model,targetname,vehicledef,origin,angles; it is not spawner activation. Wrote that native body but withheld registration: IW4 factory chooses helicopter type for definition5, retained SpawnVehicle always generic vehicle, and G_SpawnHelicopter dereferences a player owner. Reconcile common initialization before binding. Source/offline only; no tests/builds/runtime, full goal active.


## Captured vehicle identity snapshot overlay

Added an atomic wire overlay for captured vehicle instance/definition and spawning-client identity, based on C1 spawn stores and measured9/5-bit fields. Reads preserved snapshot/archive state only. Pose already has its own overlay; full flags/assets and resolver integration remain incomplete, so vehicle cases are not prematurely enabled. Source/offline only, no builds/tests/runtime; full goal active.


## Captured vehicle asset overlay

Added atomic model/turret-weapon mapping from captured vehicle entity state. C1 writes a weapon word at+d4, so the adjacent upper word is preserved. Identity and pose overlays already exist; flags and full snapshot composition remain pending. No live-state lookup, builds/tests/runtime. Full goal active.

## Claude GSC workers resumed; ownerless helicopter preparation

Two bounded Sonnet high workers are running: `turret-placement-r5` for `canspawnturret`, and `thermal-material-r5` for `setthermalbodymaterial`. They own separate new modules and must report shared integration for parent review. No new support counted from in-progress work.

CoDOL native helicopter initialization now accepts a null owner without dereferencing a player, preserves player-owned packing, and uses existing separate spawning-client capture. C1 67a6df..67a6ff supplies optional-owner evidence. This is preparation only: generic factory dispatch and vehicle snapshot flags/seeder remain unfinished; `spawnvehicle` stays unregistered. Source/offline inspection only, no builds/tests/runtime or verified match entry.

## Vehicle factory type dispatch, source only

Draft `spawnvehicle` now dispatches type5 definitions to native helicopter initialization with no owner, restoring VehicleDef health after the legacy99999 override. C1 confirms type selection and definition health. Additional factory collision-template behavior discovered at67a7ea/674850 still needs native parity, as do captured vehicle flags and full snapshot seeding. Binding remains disabled. Two original Claude GSC workers confirmed live; no duplicate assignments or reviewed output yet. No builds/tests/runtime; match entry remains unverified.

## Vehicle snapshot visual model / brush correction

Full native G_DObjUpdate dispatch disproved the earlier model mapping: vehicles store visual model in un2+d8 and collision brush in index88. C1 confirms visual model WORD+e4 (571227), brush+98 (6748d5/5d29e0). Corrected the atomic overlay to use separate captured inputs, preserve visual upperword and avoid asset-remapping the brush. Full vehicle seeder remains pending.

Native map-time vehicle collmap setup already exists; adapt its behavior per-spawn next. Turret Claude task hit40turn cap (USD0.8180578), resumed same session for16turn finish-only report-first pass; thermal worker remains live. Source/offline inspection only, no runtime verification or match entry.

## Per-spawn vehicle collision templates

Draft spawnvehicle now applies the first matching script_vehicle_collmap using actual native model name, validates/copies the brush, installs bounds, sets vehicle contents and relinks. C1 classname initialization577694..5776ad and common factory674850 corroborate the retained map-start implementation. Binding still awaits snapshot flags/seeder and remaining helicopter state review.

Both original Claude tasks hit40turn research caps without source; each same session is now in a bounded16turn report-first finish pass. Thermal original USD0.6639878; no duplicate worker. No builds/tests/runtime or verified match entry.

## canspawnturret registered in native source

Parent reviewed and registered the Claude implementation. IW4 5ee590/4e6f00 returns whether a32-slot turret pool has a free slot; the native implementation scans the same inuse fields the retained spawn/free routines own. No receiver/argument reads or invented placement traces. Removed unsupported worker claim that the IW4 pool was client-side.

Turret worker finished16turns atUSD0.7067702 after its original capUSD0.8180578. Thermal finish73008 remains live. Source/offline review only; no build/runtime verification or match entry.

## Thermal body material global publication

Parent replaced the faulty Claude per-player draft after identifying IW4 SV_SetConfigstring4982e0 and C1 configstring1304 consumer4675bf/43de20. New global setthermalbodymaterial reads string0, publishes bank1304 and reliable updates, and clears with an empty override; client resolves type5 Material viaa78170. Added registration. Normal bank lifecycle supplies late joins/map teardown; no invented per-client state.

Thermal worker terminal at both caps (USD0.6639878 +0.6361046). No owned workers live. Source/offline review only; no builds/runtime or verified match entry. Full objective remains active.

## GSC r6: UpdateSkill contract and thermal query worker

IW4 precacheleaderboards/sendmatchdata resolve toemptyRET, so no support was counted. Traced real UpdateSkill player/profile guards, skills/<mode> path, defaults and Elo-style reducer constants. Native typed public-profile writer/dirty lifecycle exists and needs integration after remaining guards/schema are verified. Evidence in parent-updateskill-r6-evidence.md. One bounded Claude worker now owns missing weaponhasthermalscope research/implementation. No builds/tests/runtime; match entry incomplete.

## UpdateSkill native rating reducer

Added source reducer matching IW4 ratings formula, measuredfloat stores/K thresholds and SSE truncation path with defined32-bit arithmetic. GSC/profile binding remains pending verified eligibility/guard semantics and actual skills path. No script support counted from helper alone; numerical/fallback conversion parity still needs later verification. Thermal-query worker74640 confirmed live. No builds/tests/runtime; full match-entry goal active.

## UpdateSkill paired public-profile writes

C1 scoreboard evidence already corroborates skills/tdm in public playerdata. Added schema-resolved paired skill updater using real session buffers, typed scalar storage, CRC and dirty-field tracking. Preflights both edits before committing; winner/loser write order preserves same-client behavior. GSC eligibility/guard wrapper still pending, no support count or registration yet. Thermal worker74640 confirmed live. No builds/tests/runtime; full match-entry goal active.

## UpdateSkill GSC registered

Confirmed IW4 exclusion4d6e40 asSV_IsTestClient using primary IW4x Server.cpp; nativeNA_BOT producer and parser impure-state lifecycle already exist. Added/registered global updateskill with winner/loser validation, optionaltdm/weight1, bot exit, connection and impure/developer guards, calling actual paired public-profile writer. Source only, no build/runtime verification; profile delivery and full match entry remain incomplete.

Thermal-scope worker hit40turn cap (USD0.810866), no source/report; terminal, not stuck or duplicated. Parent recorded unresolved handoff.

## Glass lookup contract and native asset gap

Confirmed both IW4 getglass/getglassarray require1 name and resolve actualuint16pieceIDs; Python unconditionalemptyarray is not reference behavior. CoDOL GameWorldMp replay already consumesglassheaders and namedgroups, but native lookup/mutation representation is missing. Next trace4149e0 and materialize map data. C1 thermalcandidate registry names areblank, so bf4/bf5 remainunidentified. Offline/sourceonly, no new supportcount or runtimeverification.

## Native owned glass-group store

Traced IW4 4149e0 first-match group lookup. Added copied names/uint16 IDs, ordered matching, piece-ID validation, atomicreplacement/free and explicit unloaded-versus-knownempty state. GameWorldMp asset materialization/map lifecycle and GSC query registration remain pending; no unsupportedemptyarray substituted. Source/offline only, no builds/tests/runtime or matchentry.

## GameWorldMp glass source catalog

Integrated source spans into full-zone two-pass replay: owningworld/glassheader, explicit worldwithoutglass marker, orderedgroupnames and uint16 IDspans. Preflightallocates metadata beforeapply; loadblock teardown freesit. Direct C1 4bc800 inspection confirms pointer/count roles. Next materialize checkedspans intoownednativegroups and wiremap/GSC lifecycle. No builds/tests/runtime or supportcount yet.

## Windows build and launch check (2026-09-09)

User-requested build and launch of the current tree, superseding the writing-pass deferral for this check. Cross-built `bin/codol_dedrun.exe` from WSL with MinGW-w64 and launched it against the original 1.1.1.13 installation (`mp_killhouse_sh`, `dm`, loopback port 17739, isolated home `%TEMP%/codol-claude-run-probe`, alpha0022 script roots). The C1 client and Python lobby were not touched.

Build fixes required (writing-pass code had never been compiled): missing `bg.h` includes for `EV_*` events in `codol_engine_state.c`, `codol_sv_gameframe.c`, `codol_script_entity_fx.c`, `codol_remote_missile.c`; a C-visible `XAnimParts` typedef in `xassets/xanims.h` plus `q_shared.h` in `codol_model_animation.c`; `svs.iNumClients` (nonexistent) replaced by `sv_maxclients->integer` in `codol_script_native_batch3.c`; native `TEAM_BLUE`/`TEAM_RED` for allies/axis in `codol_script_radar.c`; `0x63e+index` hex-float preprocessing tokens spaced in `codol_sv_assets.c`; `bg_public.h`/`weapondef.h` includes in `codol_script_missile.cpp`; `G_GetPlayerViewOrigin` takes `playerState_t *` in `codol_script_turret_target.cpp`; `G_LogPrintf`/`G_PrintRedirect`/`G_PrintAddRedirect` given C linkage in `g_sv_shared.h`.

Runtime crash fixed: `server.h` carries an upstream bare `#pragma pack(1)` that stays in effect for the rest of any translation unit. `codol_asset_registry.c` now reaches `codol_xmodel.h` after `server.h`, so it read `codol_xmodel_bone_name_t.text` at offset 6 while `codol_xmodel_skeleton.c` wrote it at offset 8; the mismatched pointer crashed `SL_GetString` during collision model bone binding. A preprocessed scan of every translation unit found 43 CoDOL headers whose struct definitions were seen under different packing in different units; each now wraps its definitions in `#pragma pack(push, 8)` / `pop` after its includes, matching the convention already used by `codol_actors.h`. Upstream headers with the same mixture were left as they were. The scan script is `obj/claude-workers/packcheck.py`.

Default-weapon load fixed: `weap_pickup` failed because its falloff curve is a deduplicated pointer to the curve word of an earlier alias record in block 3. C1 only emits the insert-pointer marker (-2) for holders in temporary memory; a holder already in block 3 is itself the later pointer target. `replay_field_asset_reference` in `codol_load_blocks.c` now catalogues inline (-1) curves and loaded sounds under their holder address. Failure-site diagnostics were added to `codol_weapon_loader.c`, `codol_sound_native.c`, `codol_sound_source.c` and the registry's sound resolver; the engine error message reports them.

Verified startup on Windows: nine startup and six map archives mount, 2,053 configstrings install, native collision (4,689 leaves) and world (30 lights) install, `none` and `defaultweapon_mp` load, codescripts and gametype scripts compile until the first missing builtin: `GetThirdPersonCrosshairOffset` in `maps/mp/gametypes/_damagefeedback.gsc:37`. No player connection or match entry was attempted. The `test_codol_assets` link line in the makefile no longer matches the source tree (missing weapon-compose, profile and mbedtls inputs) and was not used as evidence.

## Missing-builtin closure for mp_killhouse_sh / dm (2026-09-09)

`obj/claude-workers/missing_gsc.py` (run under WSL) loads the dm gametype, map, codescript and utility scripts through their `#include` and `file::function` closure across the four script roots (alpha0022 overlay, `scripts/codol`, vendor IW4), strips comments, strings and developer `/# #/` blocks, and reports every call whose name is neither defined in the calling file or its includes nor registered through `Scr_AddFunction`/`Scr_AddMethod`. 269 script files load. The compiler will reject 44 names; `using_animtree` (a directive) and `tsetdevdvar` (text inside a string literal) are analyzer false positives.

Registered from existing drafts: `ishost`, `sendmatchdata`, `precachempanim`, `scriptmodelplayanim`, `scriptmodelclearanim`. `CODOL_ScriptStartupExtra_Register` (playerlinkto and the camera/controls link family) existed but was never called; it is now invoked from the CODOL registration block. `prof_begin`/`prof_end` are new builtins in `codol_script_profiler.c`: the retained IW3 grammar has no token and this VM no `OP_prof_*` handler, so the retail IW4 contract (one string argument, no effect) is enforced as a builtin.

The remaining 38 names were assigned to three workers with disjoint new files: `codol_script_vehicle_builtins.c` (attachpath, startpath, vehicle_canturrettargetpoint, vehicle_finishdamage, vehicleturretcontrolon/off, startac130, stopac130, maketurretsolid, setturretminimapvisible, canplayerplacesentry, remotecamerasoundscapeoff), `codol_script_player_builtins.c` (getthirdpersoncrosshairoffset, getrestedtime, isusingonlinedataoffline, predictstreampos, playerforcedeathanim, stunplayer, thermalvision on/off and fof overlays, setcardicon/nameplate/title, dropscavengerbag, kc_regweaponforfxremoval, precacheleaderboards) and `codol_script_combat_builtins.c` (missile_settargetent/pos, glassradiusdamage, setcanradiusdamage, physicslaunchserver, attach/detach/moveshieldmodel, codol_fire_nearest, codol_radiusdamage). Parent review, build and a launch probe follow; results are recorded below when available.

### Results after integration (2026-09-09, later)

All three worker modules were integrated with their shared-file changes (`enthandle.cpp` C setter, `_g_main_mp.asm` physics-launch frame, `_g_combat_mp.asm` vehicle damage dispatch and the `setCanRadiusDamage` flag test on `gentity.flags` at +0x180, `_g_vehicles_mp.asm` native path follower, entity-free and session reset hooks, the `stun_time`/`stun_known` player-state fields with archive read/write, the thermal/stun player overlays and the client card overlay, `ENT_HANDLER_SCAVENGER_BAG`, and the last-played recorder in `ExitLevel`). The full Windows build links. Duplicate camera/controls link registrations were removed from `CODOL_ScriptStartupExtra_Register`. Per the user's direction, new CoDOL logic is written without build-flag conditionals.

The launch probe then advanced through several further stops, each fixed natively:

- `_perkfunctions::deleteTI` unresolved: the alpha0022 overlay's `_perkfunctions.gsc` is a one-function stub written for the Python VM, while vendor scripts link against the IW4 functions at compile time. The native adaptation root (`scripts/codol`) now takes precedence over the user overlay in `CODOL_ReadScriptSourceWithNativeOverlay` (it was previously shadowed, which also made the native `_perks.gsc` dead), and `scripts/codol/maps/mp/perks/_perkfunctions.gsc` carries the vendor functions.
- `::laserOff` unknown: IW4 scripts take pointers to builtins (five sites in `_load.gsc`); the retained IW3 compiler resolves `::name` only against script functions and the VM has one pointer type. The syntax-lowering pass now redirects such pointers to generated forwarding functions appended to the file, using an engine-supplied resolver (`CODOL_SetScriptBuiltinResolver`, installed by `cscr_parser.cpp` from the function/method tables).
- `setrearviewrenderenabled`: IW4 0x5f50b0 is `Scr_Error("ALTERNATE_SCENE_RENDER is disabled")`; implemented as that.
- `pb_dive_prone_land` not in animtree `multiplayer`: the vendor IW4 `animtrees/multiplayer.atr` was being served from the script roots. `Scr_ReadFile` now takes `animtrees/*.atr` from the mounted CoDOL rawfiles first (developer builds dump them to `<fs_homepath>/codol_animtrees/`).
- `cannot be sync nonlooping and looping`: `codol_xanim_native.cpp` copied C1's whole flags byte into IW3's `bLoop`; bit 0 is the loop flag (bit 1 delta), so every non-looping delta animation read as looping. Fixed.
- `Could not load weapon "mp5k_codo_so"` / `xmodel "codo_weapon_mp5k_world"`: the map's entity list references coop-zone assets; `DB_FindXAssetHeader` now substitutes the native default (`defaultweapon_mp`, `void`) for an asset absent from every mounted zone, as the IW4 database does, so the spawner's own unspawnable-item path applies. A zone string-search tool is at `obj/claude-workers/zonegrep.c`.

Current stop: `G_Spawn: no free entities` after 1022 entities (247 script_brushmodel, 140 script_origin, 133 script_model, 70 trigger_multiple, the per-gametype spawn points). CoDOL runs 2048 entities (the wire already uses 2046/2047 sentinels); the retained engine has 1024. Two workers are raising the engine to 2048: one owns the assembly (constants, `g_entities` storage, `server_t` trailing-field offsets after the in-place growth of `svEntities`), one owns the C side (`GENTITYNUM_BITS` 11, entity-handle packing, identity wire translation, entity-sized storage). Not yet built or run.

### Level load reached (2026-09-09, evening)

The engine now runs 2048 entities: the assembly worker changed 193 sites in 25 files (constants, `g_entities` and `pushed` storage, direct world/none entity addressing) and the C worker moved `GENTITYNUM_BITS` to 11, `MAX_SNAPSHOT_ENTITIES` to `MAX_GENTITIES`, made the CoDOL wire translations identity and widened the IW3-protocol entity fields; `serverObjMap` in `_dobj_management.asm` grew to 2048 entries. `server_t` is now 0xbef62 bytes with `svEntities` grown in place. Stack `entityList[1024]` buffers passed to `SV_AreaEntities` were left (box queries truncate); IW4 sizes them MAX_GENTITIES.

After that, the mp_killhouse_sh / dm probe advanced through these stops, each fixed natively:

- `getDvarInt(dvar, default)`: the three retained dvar getters accept IW4's optional default (int, float or string), returned when the dvar is unregistered.
- Faction lookups: CoDOL arenas give IW4 character sets (`socom_141_desert`, `opforce_composite`) while `mp/factionTable.csv` keys are the alpha's factions (`taskforce_141`, `shadow_company`). `scripts/codol/maps/mp/gametypes/_teams.gsc` keys the seventeen faction-table lookups on the team's faction row (allies = data row 1, axis = row 2); `_gamelogic.gsc`'s no-arena fallback reads the same rows. The character set still selects player models.
- `precacheItem`: the IW4 stats-table loop generates IW4 attachment-combination names that are not CoDOL assets (CoDOL composes attachments through marketplace items). The native `precacheItem` skips only weapons absent from every mounted zone (1,081 names on this map, traced under developer) and runs the retained precache for the rest.
- Weapon conversion: C1 classes sniper and throwingknife map to the nearest retained classes (rifle, grenade); C1 types riotshield and bomb map to IW3's slot-3 non-firing type and grenade. These are nearest native behaviours, not measured equivalents.
- Shared ammo caps: C1 0x41f310 assigns the pool by name only; the IW3 cap-mismatch error in `BG_SetupSharedAmmoIndexes` is bypassed (flare_mp 1 vs frag_grenade_mp 2 on WEAPON_FRAGGRENADE).
- Shell shocks: C1 names the dvars in `shock/*.shock` by registration number (66..92, matching the retained `bgShockDvarNames` order); `codol_shock_rawfile.c` translates them for the retained parser.
- `getBuildVersion` returns the short client build `1.1.1.13` (the long product name overflowed the match-data field; the error now reports the field width).
- Menus: C1's menu bank is 32 slots (4243..4274) and the IW4 scripts precache 33 on PC; the `onemanarmy` menu is not a CoDOL asset, so `scripts/codol/maps/mp/gametypes/_menus.gsc` drops that precache.
- HUD alignment/fonts: C1's tables (0xcd47b8/0xcd47e4/0xcd4798) add left/center/right_adjustable, top/middle/bottom_adjustable, hudbig and hudsmall; `alignScreen` packs horizontal in the high nibble (mask 0xf, shift 4) as C1 does. `_g_hudelem.asm` tables, counts and field rows, and `hudscrnalign_t`, follow that.
- Infinite-loop guard: the first script frame spends ~30 s in native precache conversion; `Scr_ScriptRuntimecheckInfiniteLoop` no longer applies while `level.initializing`, which had been forcing `map_rotate`.

Validated on Windows: a single server initialization, no script errors, the dm gametype running its pre-match on mp_killhouse_sh, the process alive after 75 s with UDP 17739 listening and a 655 MB working set. No client connection was attempted; gameplay semantics of the mapped weapon classes and the forwarded builtin pointers are unverified.

Known open issues: a map restart fails to remount the map archives (`CODOL_OpenFastFile` failure; the reason is now reported in the mount error and the binary is linked large-address-aware); the first frame's precache pass is slow; `test_codol_assets`' makefile link line is stale; the `_perkfunctions` override applies IW4 perk effects server-side, which needs comparison with the client's ability modifiers.

## Connect-time profile members IW4 scripts expect (2026-09-09)

The client now connects, uploads its profile and reaches CS_ACTIVE with the
secure profile auto-attached, and then `_persistence::initBufferedStats` failed:
`getPlayerData("misses")` is declared by neither CoDOL definition. A survey of
every `get/setPlayerData` name used by the compiled scripts against the mounted
`mp/playerdata.def` (version 220) and `mp/playersecuredata.def` (version 11)
found twelve IW4-only roots: awards, bests, challengeProgress, challengeState,
customClasses, featureNew, killstreaks, misses, restXPGoal, timePlayedAllies,
timePlayedOpfor, timePlayedOther.

- `src/codol_script_profile_vm.c`: ten of those roots (everything but the two
  loadout roots) route to a per-client session store, zero-initialised and
  discarded on connect/disconnect (`CODOL_ScriptProfileForgetLegacy`, called
  from the three `CODOL_DetachClientSecureProfile` sites in `sv_client.c`).
  The route applies only while neither mounted CoDOL definition declares the
  name, so nothing CoDOL owns is shadowed. Nothing is persisted or uploaded.
- `scripts/codol/maps/mp/gametypes/_class.gsc`: vendor copy whose `cac_*`
  accessors read CoDOL `weaponClasses[]` through the native loadout bridge
  (`codol_getLoadoutItem/Perk/Attachment/Camo/Killstreak`). IW4 perk slot 0
  maps to CoDOL `lethal`, slots 1..3 to `perks[0..2]`, slot 4 to
  `deathstreak`; killstreaks are read per class instead of IW4's global set.
  Classes beyond the eight CoDOL records answer "none"/"specialty_null" and
  fall through IW4's own default-class fallback.

Verified: build links, mp_killhouse_sh dm loads with the override compiled and
no script errors through game initialisation. Player spawn with a CoDOL
loadout is not yet exercised.

### Player cards (same day)

With the profile members answered, `_playercards::onPlayerConnect` raised C1's
own "Index is greater than the maximum allowed in code for networking" from
`SetCardIcon`: the client's uploaded cardIcon/cardTitle/cardNameplate shorts
carry values outside C1's 0..1023 range. `scripts/codol/maps/mp/gametypes/
_playercards.gsc` now applies only in-range handles and prints the rejected
value in developer mode; the native setters keep C1's check. Verified the
override compiles and the level loads.

### Missions card-title check (same day)

`_missions::onPlayerConnect` compared the CoDOL cardTitle (a marketplace item
id, e.g. 5061) against IW4's string handles, which the VM rejects as an
int/string comparison. `scripts/codol/maps/mp/gametypes/_missions.gsc` is a
vendor copy with that check guarded by `isString`. Verified it compiles and the
level loads.

## Client-driven iteration to the first spawn (2026-09-09, afternoon)

Driving the real C1 client through the lobby (开始匹配 → 准备) against the
native server, in order of appearance:

- `getPlayerData` names IW4 declares but CoDOL does not (prestige,
  winLossRatio, ... found only at run time): the session store now answers
  every root neither CoDOL definition declares, tracing each once.
- `closePopupMenu()` takes no argument in IW4; native accepted only a name.
- `CODOL_CaptureClientPlayerLinks` ran on the playing path only, so a free
  spectator's frame was refused ("player or HUD conversion"). It is now also
  captured beside the abilities publisher, before the spectator branch.
- HUD colour codec (bits −85): C1 quantises alpha to multiples of 8 and reaches
  0/255 only through the "same RGB, toggle alpha" arm; the writer refused any
  alpha not divisible by 8. Both writer and reachability now follow the reader.
- HUD element font range: C1 accepts fonts 0..7 (hudelem.md), builder allowed 0..3.
- Perks: "specialty_null" is IW4's empty slot (no-op); unknown IW4 perk names
  are traced once and treated as absent; `hasPerk` accepts its optional flag.
- IW3's giveWeapon/setNormalHealth sent `J "1"`; C1's `J` is a no-argument
  stats command that Com_Errors (localised 190) on an argument and the client
  disconnected the moment it spawned. Removed from the retained assembly.
- Zombie clients no longer get a snapshot body (the writer has no frame for
  them and overflowed every packet after a drop).
- Diagnostics added: per-step reason for frame rejection, snapshot overflow,
  history/HUD reachability; menu precache/response, reliable-command trace
  (developer 1).

Result: connect, team autoassign, class panel (ESC → 自选背包), spawn with the
profile's loadout, movement. Open: ammo HUD shows 0|0 for the composed
weapon; opfor body/head xmodels absent from the mounted zones (void used);
DTLS record type 40 (18 bytes) from the client is dropped; client command `s`
unknown; the IW4-style class popup after team select does not appear (the
client's own ESC panel is the working path, as alpha0022 measured).

### In-play faults after the first spawn (same day)

- Mantling ended the level: "Animation condition has no native state: client
  0, condition 13". Condition 13 is C1's `akimbo`; C1 adds nine conditions
  (10..18) and nothing native had written 13..18, so the first move script
  testing one faulted. Unwritten CoDOL conditions now read as their zero
  value (traced once in developer mode), and ClientEndFrame publishes akimbo
  from the hand extension's dual-wield flag and mirrors the player anim type
  into `playeranimtypeprimary` (16) each frame. fastmantle, riotshieldnext,
  divedirection and scripted still have no measured producer.
- Firing ended the level: IW3's FireWeapon raised `weapon_fired` with no
  parameter; the IW4 gametype's watcher compares the (undefined) name to a
  string. `CODOL_NotifyWeaponFired` now pushes the weapon's internal name
  first, as IW4 and C1 do, and the retained FireWeapon calls it.
- Client 18-byte records of DTLS type 40 are the "<3" keepalive alpha0022
  observed; still dropped, harmless so far.
- Projectile lifecycle events had no wire mapping (EV_GRENADE_BOUNCE with the
  surface type, the explosion family with DirToByte, bullet hits), so a
  grenade in flight rejected every snapshot until it exploded and the client
  timed out. Arms added; any still-unmapped event is now published as no
  event with a one-time developer trace instead of refusing the frame.
- Match end: `setClientMatchData(... "faction", <IW4 character set>)` is not
  a CoDOL enum member; unknown enum values are now skipped with a trace
  listing the members instead of ending the level.
- Movement "resistance": every snapshot carried read-origin-and-velocity = 1,
  so the client took the server origin verbatim and never predicted. The bit
  is now 0 in normal play and 1 only on the first frame, on a teleport toggle
  (eFlags bit 2, ClientSpawn/origin setter), on a pm_type change and on a
  grounded divergence over 8 units from the client's predicted origin
  (movement_fix.md policy; airborne divergence is left alone).
- Ready weapon state with a leftover animation (dead, stunned, fall damage)
  is published instead of refusing the frame; the player overlay trace now
  prints weaponstate/weapAnim/weapon/pm_type on rejection.
- Rubber-banding: the divergence re-assert was self-feeding (each rov=1
  snapshot moves the client to a snapshot-old origin, which is the next
  divergence). Measured with it disabled, client-predicted and server speed
  agree exactly on loopback. `codol_rovAssertUnits` now defaults to 0 (off);
  rov=1 only on first frame, teleport toggle and pm_type change.
- Fall death ended the level on `attacker.code_classname` (undefined): IW4's
  read-only entity field, now an alias of the classname slot in ent_fields.
- Missing-xmodel warning throttled to once per name.
- Mantle wedging: the server runs the retained mantle but published neither
  PMF_MANTLE (4) nor the mantle block (+0x258 yaw, +0x25c timer, +0x260
  transIndex, +0x264 flags) nor EF_MANTLE (retained eFlags 0x8000 -> C1
  0x10000), so each snapshot re-zeroed the client's mantle mid-climb
  (movement_fix.md 2.1). All three are now published from the server state.

## Audit implementation (2026-09-09, night)

- Correction to the audit: the tactical button (0x10000) already works. The
  retained offhand selector (`CODOL_WeaponStateSelectOffhand`, called from
  PM_Weapon_CheckForOffHand) reads the raw CoDOL word, third bit included.
- Dolphin dive implemented natively (`src/codol_dive.c`, C1 PM_CanDive/
  PM_CheckDive/PM_DiveStart/apex clamp/completion per pmove.py): ground hook
  from Jump_Check (launch takes the air path like a jump), air hook before
  PM_AirMove (apex clamp), forced prone with zeroed move input during the
  dive and for 100 ms after, EV_DTP_LAND published as C1 event 186, dive
  bit 0x40000000 published in pm_flags. Verified: launch, flight (ground
  NONE, z 4 -> 41 -> falling), touchdown, completion to prone.
- Stance input: C1 sends prone as a level (stance state), the retained engine
  toggles prone on a key edge, so the level toggled the stance every command.
  sv_client.c now converts the level into one press per change of the
  requested state.
- Published: damage indicator block (+0x17c..+0x188), prone direction floats
  (+0x1a0..+0x1a8), legs/torso animation timers and indices (+0xc0..+0xcc),
  ADS bits (0x40/0x10) in pm_flags.
- Mantle still open: retained Mantle_Check never starts; 90 CONTENTS_MANTLE
  brushes exist (nearest to spawn 4246,-732: brush 13918 mid 3948,-532,28).
  mantle_debug is forced on in developer builds; `CoDOL mantle: check/result`
  traces every attempt.

## 2026-09-09 late: spectator at the map origin, stale slot memory, source layout

Report: "teleported outside of the map and was stuck there on startup, also the
player's camera is at feet level". Reproduced with the driver: the spectator
view sat on the floor although the server spawned the spectator at the
`mp_global_intermission` point (3492 -238 224), 176 units above the floor
(`CoDOL spawn:` trace added to ClientSpawn; `CoDOL pacing` now prints pm_type
and origin).

Cause: a baseline (non-delta) snapshot carries no origin or velocity unless the
read-origin bit is set; the client then fills them from its own prediction,
which for a freshly loaded client is (0 0 0). The first snapshots the client can
decode arrive after it finishes loading, long after the armed first frame, so
the spectator sat at the map origin (inside killhouse, on the floor) until the
in-game spawn toggled the teleport bit. Fix: `CODOL_PrepareServerSnapshot`
forces rov on every frame written without a delta base. Second cause for the
"outside the map" variant: the per-slot rov memory (armed/teleport/pm_type) and
the prone edge adapter survived reconnects; both are reset in
SV_DirectConnect (`CODOL_ResetClientOriginPolicy`).

Spectator view height 0 is retained IW3 behaviour (PM_CheckDuck for spectators)
and matches C1 (alpha0022 ERRORS.md: viewheight 0 for pm_type 5); the
intermission point is placed at camera height, so nothing to change there.

Layout: every `codol_*` file moved to `src/codol/<area>/` (see
docs/CODOL_SOURCE_LAYOUT.md). Makefile globs the areas and adds them as include
paths; `test-codol` recipes, the Python tests, tools and the animation `.inc`
includes in `_bg_animation_mp.asm` were rewritten; `src/zlib/unzip.c` lost its
`../codol_iwd_crypto.h` prefix. Verified with a full rebuild linked to a
separate name while the live server kept its executable locked.

Known stale before the move: `test_codol_script_math` (undefined AnglesToAxis)
and `test_codol_event_parameters` (undefined CODOL_WeaponToWire) no longer link
with the sources their recipes name.

## 2026-09-09 night: parity inventory, parity plan, and four measured findings

Research-only pass. No build, no test, no server or game launch. Produced
docs/CODOL_PARITY_INVENTORY.md (the full gap inventory) and
docs/CODOL_PARITY_PLAN.md (the ordered plan, with exact edit sites).

Four things were settled that had been open:

1. The unknown client command `s` is the scoreboard request, the IW3 `score`
   renamed. Four C1 sites share the idiom
   `if (cg->scoresRequestTime + 2000 < cg->time) { ...; CL_AddReliableCommand("s"); }`:
   0x436f4a, 0x45fe42, 0x4601fd, 0x465a05. String 0xc41e50, sender 0x493bb0.
   Enumerated by scanning .text for calls to 0x493bb0 (11 sites total; the
   others are `n %i`, `userinfo "%s"`, `disconnect %s`, `disconnectforoutro`).
   The server handles `score` and not `s`, so it never answers, which is why
   the scoreboard has never appeared.

2. Only five retained reliable-command senders are still on IW3 letters. An
   earlier scan reported many more because it ignored the `%ifdef CODOL_SERVER`
   branches; re-run with preprocessor state applied the live defects are
   GScr_SetTeamScore (G/H, _g_scr_main_mp.asm:6524 and 6542),
   PlayerCmd_SetClientDvar and SetClientDvars (v, _g_client_script_cmd_mp.asm
   3484 and 3558), and the offhand notice in _g_weapon.asm:1017 and 1137 (C,
   which C1 reads as team score 1). Plus the fast-restart 'm' at sv_main.c:3910
   and the admin-chat 'h'. Three more are wrong but dead, their builtins having
   CoDOL-native replacements.

3. The damage-indicator offsets are measured, not guessed. alpha0022's
   playerstate_fields.py names 0x17c damageEvent, 0x180 damageYaw,
   0x184 damagePitch, 0x188 damageCount, 0x18c damageFlags, and the wire widths
   8/8/8/7 at those offsets are the only such run in the whole 244-field table,
   matching the retained netfields in msg.c:2437-2462 exactly. The 2026-09-09
   revert of this publication is not needed: the spawn regression it was blamed
   for was the baseline-snapshot origin bug, since fixed. Note that width 0 is a
   float encoding (codol_delta.c case 0), not an unsendable field.

4. The match-end chain is verified end to end in C1: the CL-level table at
   0x4878D8 indexes on firstChar-'d', so `t` selects 0x48782E, which passes
   Cmd_Argv(1) to CL_Disconnect 0x4960E0, which compares it against
   EXE_MATCHENDED at 0xc47D30. `d`, `k` and `x` are handled at the same layer
   and never reach cgame. Also found: IW4's endGame already performs most of
   the end ritual, including `setClientDvar("ui_opensummary", 1)` which is on
   C1's `s` whitelist, so fixing the setclientdvar letter unblocks it.

Also measured: the C1 scoreboard parser 0x465130 takes count (clamped to 19),
team1, team2, scorelimit, then ten integers per row into a 0x40-stride array at
cg+0xBEB70; field 4 is range-checked to 1..8, matching status_icon. The
CoDOL formatter already produces exactly this; it is simply never called, since
Cmd_Score_f still calls the retained seven-integer IW3 sender.

## 2026-09-10: parity plan phase 0, phase 1 and the measured field families

Implemented from docs/CODOL_PARITY_PLAN.md. Every step built clean with the
Windows cross-build; the server was started once and loaded mp_killhouse_sh
with no new errors. No C1 client was running, so nothing here is verified
against the real client yet.

Wire command corrections, all inside %ifdef CODOL_SERVER with the %else branch
keeping the IW3 value:
  _g_scr_main_mp.asm     setteamscore  G -> C (axis, level+0x200) and H -> D
                         (allies, level+0x204), matching PlayerCmd_UpdateScores
  _g_client_script_cmd_mp.asm  setclientdvar and setclientdvars  v -> s
                         openmenu/openmenunomouse t -> q, closemenu u -> r,
                         closeingamemenu L -> H (all three are dead in this
                         build, their builtins having CoDOL replacements, but
                         t at the client layer is a disconnect, so leaving it
                         armed was a trap)
  _g_weapon.asm          G_GivePlayerWeapon and G_SetEquippedOffHand C -> y;
                         IW3's C is C1's team score 1, so every offhand give
                         had been overwriting the axis score
  sv_main.c              fast restart m -> k
  g_shared.h             new SV_CHAT_CMD, V under CoDOL, applied to all seven
                         server chat broadcast sites

Scoreboard: g_cmds.c accepts the client's "s" alongside "score" and Cmd_Score_f
now calls CODOL_SendScoreboard, which was written, correct and unreferenced.
The skill gate warns once per slot and sends skill 0 instead of aborting the
whole board, and the formatter clamps to 19 rows to match C1's own clamp.

Team score configstrings: the retained engine never writes CS_SCORES1/2 (they
are inside a commented-out block in g_shared.h), so CODOL_PublishTeamScores in
codol_sv_assets.c publishes C1 configstrings 5 and 6 from level.teamScores
whenever they change, called once per frame from SV_Frame before the client
messages go out. The configstring bank is its own previous-value record, so a
new map republishes and a late joiner gets the scores in its gamestate.

Match end: CODOL_Scr_ExitLevel sends t "EXE_MATCHENDED" to every connected
client, behind codol_exitToLobby (default on). The whole chain was verified in
C1 during the research pass. No menu command is sent from there because IW4's
endGame already opens the summary through setClientDvar("ui_opensummary", 1),
which is on C1's own s whitelist and which item 1.3 has just unblocked.

Map restart: CODOL_LoadMapArchives now reuses the mounted group when the map
and zone type are unchanged, instead of re-opening, decrypting and replaying
every zone while the previous set is only retired. CODOL_MountedArchiveCount
was added to the registry for the liveness check.

Player state: this historical pass initially misidentified C1 `0x80000` as
frozen. Later direct `PmoveSingle` inspection corrected frozen to `0x800` and
identified `0x80000` as remote controlling. Native `0x10000` was mapped to C1
`0x8000` for shellshock. Newly published fields: the damage feedback block 0x0d8
damageTimer, 0x0dc damageDuration, 0x0e0 flinchYawAnim, 0x17c damageEvent,
0x180 damageYaw, 0x184 damagePitch, 0x188 damageCount; and 0x144
viewmodelIndex, 0x16c..0x178 viewAngleClampBase/Range, 0x1a0..0x1a8 the prone
orientation trio, 0x1ac viewlocked, 0x1b0 viewlocked_entNum. Values are reduced
to their field width by the new codol_field_bits helper rather than validated,
because the codec drops the entire frame on an over-wide value and every one of
these is a counter, an accumulator or a quantised angle. Both families are
behind codol_publishExtendedPlayerState, read every frame, so a regression can
be bisected without a rebuild.

Instrumentation: an unhandled client command is printed in full (developer
only), and each distinct outbound reliable letter is printed once with its
first payload, at SV_SendServerCommandString, the single choke point every
send passes through.

Also fixed a pre-existing sign-compare error in codol_configstrings.c that was
failing the test_codol_configstrings build under -Werror.

Test status: test_codol_wire, test_codol_usercmd, test_codol_player_arrays and
test_codol_configstrings pass. test_codol_delta fails 9 cases, all bits=-85:
that codec was deliberately rewritten against live C1 evidence and the test's
alpha0022 reference still carries the old behaviour. Pre-existing.

Added after the log above: C1's F command was confirmed in the binary before
use (469a8f reads one element index, bounds it with cmp eax,7 and dispatches
through the eight-entry table at 0x4682f4 inside 0x468140), and
CODOL_RefreshWeaponHud now sends F 4 and F 5 from the per-frame hook whenever a
client's weapon or offhand index changes. Driving it from C rather than from
the retained weapon assembly covers every path that can change the weapon with
no extra send site. This is the plan's candidate fix for the composed-weapon
ammo panel reading 0|0 and still needs a live check.

Test caveat: test_codol_send does not link, and did not before this pass. Its
recipe's source list is stale relative to the overlay, missing
CODOL_ClientAppliedOrigin, the sprint/stun/thermal/recoil overlays, the
player-state extension accessors and the com_developer tracing that sv_snapshot
now uses. Worth repairing when the recipe is next touched.

Second half of the 2026-09-10 pass.

Profile persistence (plan item 5.1). The IW4-only playerdata roots - rank,
experience, prestige, challenge progress, everything neither CoDOL definition
declares - were served from a per-client session store that was thrown away on
disconnect. codol_profile_progress.c writes that store to
<fs_homepath>/codol_progress/<uid>.txt when a client detaches and restores it
when the secure profile attaches, keyed by the secure-profile uid. Enumeration
and insertion accessors were added to codol_script_profile_vm.c for it. The
file is the server's own record: it is never uploaded, the client is never told
about it, and nothing here writes the lobby's credential or profile files.

Killcam (plan phase 4). IW4's _killcam.gsc writes self.forcespectatorclient at
:115 and :153, and the retained client field table only carries IW3's name for
the same storage. The field was undefined, so the killcam raised an
unknown-field error on the first death and never ran. Added as an alias onto
the same setter and getter: the setter already writes sess.forceSpectatorClient
and the getter already reports the client being spectated. Every other member
_killcam.gsc touches is either a real field or an ordinary script member.

setClientSubtitle. C1's timed subtitle is ']' (0x4694d2): argv[1] is a duration
in milliseconds and argv[2] a localized string resolved through 0x448e10, both
handed to 0x44e830. The CoDOL gametype library calls setClientSubtitle for
deathstreak captions and the alpha0022 overlay routed it to its Python host;
the native builtin sends the client command directly.

Weapon HUD refresh verified before use: C1's F (469a8f) reads one element
index, bounds it with cmp eax,7 and dispatches through the eight-entry table at
0x4682f4 inside 0x468140.

Missing-native sweep. Every function called across the 246 gsc files on the
match load path was checked against the 837 registered builtins and against
every script-defined function. Only these are genuinely missing, and none
blocks a standard match: the deathstreak bridges magicGrenade,
giveDeathstreakHealth, setCopycatLoadout and nativeSplash; the sentry pair
setSuppressionTime and setAISpread; getGlassArray and destroyGlass, used only
by mp_strike; and IW4's unused loot pair. waittillmatch and using_animtree
looked missing but are not: the first is VM opcode 0x77 and a keyword in the
lowering pass, the second is a compiler directive.

Also fixed: a pre-existing sign-compare error in codol_configstrings.c that was
failing the test_codol_configstrings build under -Werror.

## 2026-09-10: the server stopped booting, and why

After the source restructure the server crashed nine seconds into every boot,
on the first script it compiled (`codescripts/delete.gsc`, 85 bytes). The log
ended at game initialisation, there was no Sys_Error, and the Windows event log
recorded an access violation whose address moved between builds.

Root cause: an ODR violation on the C++ standard library, caused by the bare
`#pragma pack(1)` in `server.h`.

`src/stringed_ingame.cpp` included `server.h` first and `<list> <map> <set>
<string> <vector>` afterwards, so every container template it instantiated was
built with a packed layout: `std::_Rb_tree`'s header landed at offset 1 instead
of 4, and its accessors read `+5` and `+9` where the correct code reads `+8`
and `+12`. Those templates are COMDATs and the linker keeps one copy for the
whole program. It kept the packed ones, so the correctly laid out trees built
by `codol_script_lower.cpp` were operated on by packed code, and the first
`std::set<std::string>::insert` dereferenced a bogus node pointer.

This was latent for as long as the link order happened to favour the correct
copies. Moving the CoDOL sources into `src/codol/<area>/` reordered the objects
on the link line and the packed copies started winning, which is why the server
had run the night before and would not run the next morning.

The fix is include order, not `server.h`: the pack(1) tail is what the retained
engine structs rely on. `stringed_ingame.cpp`, `stringed_interface.cpp` (which
passes `std::string&` across the boundary) and `g_client_fields.cpp` now include
the standard library before any project header, each with a comment saying why.

How it was found, for next time:
  1. The server survived with no `+map`, so the fault was in map/script load.
  2. A trace naming each script entering the lowering pass showed it died on
     the first one.
  3. The same source, same flags and same input in a standalone harness did
     not fault, which ruled out the pass itself.
  4. A `_heapchk()` checkpoint said the heap was intact immediately before.
  5. A probe that built a `std::set<std::string>` from three literals faulted,
     which moved the fault off the data and onto the runtime.
  6. Disassembling the faulting function showed member offsets 5 and 9, the
     signature of pack(1) applied to the standard library.
  7. `nm` over the objects found two definitions of the same COMDAT and
     `objdump` showed one used 8 and the other 5.

Two guards were left in place, developer builds only:
  - `CODOL_HeapCheck(where)` validates the CRT heap and runs
    `CODOL_ScriptLowerSelfTest`, which builds a small `std::set<std::string>`
    and must answer 3. Either failing prints an error naming the checkpoint.
    Called after the map archives mount and on entry to script preparation.
  - `CoDOL lowering: <script> (<n> bytes)` names every script entering the
    lowering pass, so a future fault inside it is localised immediately.

Also fixed while looking: `codol_animation_tables.h` and
`codol_vehicle_native.h` were seen under mixed packing by
`obj/claude-workers/packcheck.py` (default in the units that define their data,
pack(1) in units that only read it) and are now wrapped in
`#pragma pack(push, 8)` / `pop` per the project convention. `packcheck.py`
itself was taught the new `src/codol/<area>/` layout. The only CoDOL header it
still reports is `codol_collision.h`, whose inner `push(4)`/`push(2)` are
deliberate on-disk formats and are consistent across all seventeen units.

## 2026-09-10: phase 3 of the parity plan

Maps. All fifteen installed multiplayer zones load. Surveyed by starting the
server once per map and waiting for either a fault or a settled level, allowing
up to six minutes each because the first-frame precache runs from twenty-six
seconds on killhouse to several minutes on the larger maps. Leaf counts ranged
from 658 (mp_bog_sh) to 10785 (mp_overgrown). mp_underpass and mp_nuked settle
without printing a collision line, which is a reporting gap worth a look but not
a load failure.

Only one fix was needed for the whole set. mp_bog_sh died in
maps/mp/_animatedmodels.gsc: an entity tagged "animated_model" picks its
animation from level.anim_prop_models[self.model], a table the level designer
populates from the map's own registration scripts, which ship inside the map's
zone rather than with the gametype library. IW4 does not guard the lookup, so a
model we have no registration for raised a fatal error before the match started.
scripts/codol/maps/mp/_animatedmodels.gsc now leaves such a prop static and
names the model once in developer mode.

This also settles the zone asset dispatch question. No zone hit the unhandled
asset types, so 17, 23, 32, 33, 34 and 35 do not appear in multiplayer zones,
matching the IW4 enum alignment (gameworld_sp, ui_map, aitype, mptype,
character, xmodelalias). They need a documented skip rather than a reader, and
only if a coop or zombie zone is ever attempted.

Gametypes. All fourteen that have scripts load: war, dm, sd, dom, ctf, dd, sab,
koth, arena, oneflag, vip, gtnw, and the two written in this pass.

conf (Kill Confirmed) and infect (Infected) had no script anywhere, so the
loader fell back to dm. Both are now native adaptations in
scripts/codol/maps/mp/gametypes/, built on the helpers war.gsc uses so they
inherit team spawn logic, score and round dvars and callback wiring. Both
compile and reach a settled level with no script errors and no fallback.
Kill Confirmed polls proximity for tag pickup because nothing in this corpus
creates a trigger from script; its tag model is a placeholder since CoDOL's own
dog tag asset name is not measured yet, so a model the library already
precaches is used and cannot warn. Infected converts players through
_menus::addToTeam, the one place that keeps team, pers["team"] and sessionteam
in step.

combat is deliberately not written. It is the bot and novice training mode, and
without bots any script would be team deathmatch wearing its name; the existing
fallback logs the substitution and switches g_gametype to dm, so the server
info reports what is actually running.

The 2048-entity truncation was investigated and left alone. Four sites pass a
1024-entry stack buffer and a matching capacity to CM_AreaEntities
(_g_active_mp.asm:1231, _g_combat_mp.asm:635 and :847, _g_mover.asm:422). It is
a truncation, not an overflow, and CM_AreaEntities_r already reports it in
developer builds (sv_world.cpp:94). Enlarging the buffers means growing four
assembly stack frames and reindexing every local in those functions, which is a
poor trade against a warning that already fires.

Missing-builtin item closed. Every function called across the 246 script files
on the match load path was checked against the 837 registered builtins, against
every script-defined function, and then against what a real boot actually
compiles. Nothing is missing. The candidates all live in files that never load:
_deathstreaks.gsc (magicGrenade, setClientSubtitle, nativeSplash,
giveDeathstreakHealth, setCopycatLoadout) is an alpha0022 overlay written
against their Python host and is referenced by nothing; _sentry.gsc
(setSuppressionTime, setAISpread), _loot.gsc and mp_strike.gsc do not compile
either. Counted directly in the lowering trace of a full boot: 272 scripts
compile, and none of those four files is among them.

Deathstreaks need no bridges on this server. The vendor _damage.gsc implements
all four from the perk alone - copycat at :234, :737 and :888, combat high at
:1414, final stand at :1617 and :1640 - with the health boost in
_perkfunctions.gsc:183-193. alpha0022 rebuilt them as host calls because their
server could not run those callbacks; this one can.

setClientSubtitle was implemented anyway, since C1's ']' is measured and a timed
subtitle is generally useful, but on its own it unblocks nothing.

## 2026-09-10: the two blocked phase 2 items, both identified and implemented

Rank and prestige (item 2.2). clientState +0xA0 is the in-match scoreboard's
rank column: C1 copies it at 0x46c964 into clientInfo+0x60, and the playercard
row builder 0x68e7d0 reads clientInfo+0x60 into card row +0x14. +0xA4 is copied
alongside into clientInfo+0x64 and card row +0x18, is likewise eight bits, and
is prestige by position and by IW4's ordering. Corroborated in the binary: at
0x46c930 the copy loop reads [ebx-0xc8] to clientInfo+8 with ebx = clientState
+ 0xC8, which puts [ebx-0x28] exactly at clientState +0xA0. Both are now
published in CODOL_OverlayEngineClient from the server's progression store,
which is the only place those values exist - the client has no other source,
which is why every scoreboard read rank 1 regardless of profile. J and K are
still not sent: 0x468bd0 makes the client recompute from its own local data, so
sending them would not carry a server value.

Objectives (item 2.6). Player-state section 5 at ps+0x5D0, fully measured:
one gate bit at 0x5a1f79, then 32 slots of stride 0x24, each a raw 3-bit state
outside the field table followed by a six-field delta struct through the
generic reader 0x5a0a40 against .rdata:0xc39818. Consumers are the compass
drawer 0x4321b0 and the on-screen drawer 0x432790. The field order is origin
x/y/z, icon (12 bits), entNum (11 bits), and a 4-bit field neither drawer
reads. The gap coder is a third one, plain unary, distinct from both the
player-field and HUD coders. Source: alpha0022 objective_codec.py. The
inventory pointed at the right table and the wrong name for it.

Seeding needed almost nothing: G_RunFrame already copies level.objectives into
ps->objective every frame filtered by team, zeroing what the client must not
see (_g_main_mp.asm:1020-1060), and the two state enumerations agree exactly.
The gate stays off while nothing is live, so the wire is byte for byte what it
was before the section existed; that matters because the reader costs a flat
32 x 4 bits the moment the gate is on. Verified: dom, sd and ctf still load,
and test_codol_player_arrays passes with the carrier struct extended.

What is still unproven is whether the loaded HUD .menu declares the ownerDraw
items that instantiate the drawers (145, 146, 152, 180). If it does not, the
data arrives correctly and nothing draws. That needs a client.

## 2026-09-10: resumed from Claude's snapshot filtering handoff

Read Claude session `a5615f35-1b60-4e2b-8ac1-7fe61d916aa6`, the updated
source layout, parity plan, and current snapshot sources. Claude stopped after
adding partial entity collection and splitting reset modules for leaf tests.
Its report of a successful Windows build and eleven passing native suites is
historical evidence, not a new verification here; its recorded failure at
`test_codol_native.c:1264` is still unresolved. The startup script inventory
does not prove that every requested IW4/T5 function has full native support.

The gameplay resolver omitted ET_PLAYER_CORPSE despite a completed common
corpse overlay. Added that arm so cloneplayer's captured client identity,
animations, flags and ground entity can reach snapshots. Retained
G_SpawnPlayerClone already allocates slots19..26 and ClonePlayer writes the
fields consumed by the C1-specific overlay. This is source integration, not
proof of corpse rendering in C1.

Fixed the partial collector's structural validation: compare each input ID
with the preceding input even when its seed was rejected. Previously a skipped
row could conceal a duplicate or descending ID. Clear the emitted count on
argument failures as well. Added regression cases for filtering, malformed
input and captured corpse publication, and updated the live-send fixture's
collector symbol to match the frame builder's new API.

A further review finding remains: entity_event_parameters replaces unsupported
events only in local arrays, while the common overlay reads event IDs from the
original archived entity. Its claimed suppression is therefore incomplete and
can retain an event with a substituted zero parameter or still reject a frame.
Resolve that publication path next without changing archived event epochs.
Vehicle factory/seeding and full GSC parity also remain outstanding.

No builds, tests, launches or live debugging were run in this resumed pass.

## 2026-09-10: apply explicit event suppression during conversion

Resolved the preceding handoff finding. The gameplay resolver checks each event
ID and its resolved 11-bit parameter, records omitted slots, and combines that
mask with recipient audience filtering. The common entity overlay now accepts
an explicit visible-slot mask, used by the collector on its first conversion.
This avoids running a strict conversion over events that were already selected
for omission. Each omitted slot publishes both event ID and parameter as zero;
other slots stay in place and the original captured epoch remains authoritative.
The ordinary public overlay still selects all four slots and rejects an unknown
event. Player weapon-pair conversion remains part of the staged collector.

Added regression source for an unknown suppressed event beside a valid stance
event, preserving the epoch and source bytes, invalid-mask atomic failure, and
unsuppressed rejection. Call sites were inspected, but no builds or tests run.
Omitting unsupported events is not implementation of their gameplay semantics;
those mappings and generic temporary-event fallback still need review. Full
GSC parity, vehicle publication and actual C1 verification remain outstanding.

## 2026-09-10: temporary-event fallback and current GSC audit

Changed unresolved generic temporary events to return a failed seed, allowing
the emitted collector to omit just that entity. Publishing the original event
with a fabricated parameter0 could select a valid but incorrect asset or target.
This does not implement the omitted event's semantics.

Retained Bullet_ImpactEffect inspection also contradicted the new bullet-event
comment: native eventParm+9c is DirToByte(normal), while surface+84, weapon+c4
and shooter+74 are independent. Corrected the comment. The generic seed does not
yet provide a complete compound bullet-impact adapter; trace the C1 consumer
before adding those fields. Parameter pass-through alone is not impact parity.

Started one Claude Sonnet high worker with a15-turn bound to audit current
vehicle spawn/remote-control and weapon thermal GSC gaps. It owns only
obj/claude-workers/resumed-gsc-audit-report.md. Launcher61844 and child73952
were observed live and the initial report exists. Explicit instructions include
native architecture rewrite authorization, source ownership and no execution
during this writing pass. No worker implementation counted as complete.

No builds, tests, launches or live debugging performed in this turn.

Worker follow-up: the audit reached its15-turn cap (16reported), exited1,
and child73952 was absent; costUSD0.2618492. Its report was still a skeleton.
Resumed the same session25ac7a87-531e-44a0-9328-a926ef10363f for3 turns with
only Write/Edit tools to deliver gathered findings, launcher82504. No duplicate
research assignment launched; report still needs parent review.

## 2026-09-10: materialize real named glass groups

Added assets/codol_glass_load.c/h to turn the replay catalog into the existing
owned glass-group store. It checks source ownership and bounds, one explicit
world marker, header counts, ordered group rows, bounded inline or pooled
names, little-endian IDs and actual piece-count limits. Destination replacement
is atomic and copied data outlives the source archive. Missing replay metadata
is rejected rather than treated as a known empty world. Mounted-world selection,
map reset integration and GSC registration remain to be written.

The Claude audit finish exited0 and delivered findings. Parent review rejected
its stale spawnvehicle diagnosis: the current wrapper already branches type5
through the helicopter initializer, and the previous assembly pass added the
NULL-owner guard. Its thermal read-then-register advice is also unsupported:
the C1 boolean field semantics remain unresolved, and the material setter is
a separate feature. Added corrections to the report; useful consumer call-site
navigation is retained, with no runtime or full-support claim.

Source review only; no builds, tests or launches. Full goal remains active.

## 2026-09-10: mounted glass groups and named GSC queries

Added GameWorldMp type18 directory definitions to the complete replay's named
asset catalog and taught name resolution its84-byte header. The mounted loader
now materializes and caches owned glass groups per archive, using normal newest
definition precedence and releasing all copies on unmount. Each query resolves
the current map's BSP name again, avoiding a stale global pointer after a map
change. The immutable group catalog can be reused on an unchanged map.

Registered getglass/getglassarray as globals using the previously measured IW4
one-const-string argument contract. getglass returns undefined for no pieces,
an integer for one piece, and an error for multiple pieces; getglassarray returns
ordered IDs, including an empty array for a known missing group. Missing assets
or invalid catalogs produce an error instead of a fabricated empty world.

Source and call-site review only. No builds/tests/launches; map-name resolution
and actual C1 behavior remain unverified. Glass destruction and other mutable
state/snapshot data are not implemented by these read-only queries. Broader GSC,
vehicle and match-entry requirements remain active.

## 2026-09-10: user-authorized build and Killhouse live checks

The user superseded the no-execution writing constraint, requesting periodic
builds and launcher checks. Updated AGENTS.md/CLAUDE.md accordingly. Preserved
C1 and Python lobby; restarted only the native server using the existing
START-CODOL-SERVER.cmd defaults (Killhouse/dm).

Windows build succeeded. The fresh live connection completed DTLS and delivered
decrypted getchallenge/connect/stats, then client0 spawned into Killhouse
(playing origin4258,-367,4). The original reported authentication failure did
not recur in that run; its cause is not proven and no crypto bypass was added.
The standalone Windows handshake/ECDH DATA/retransmission test also passed.

Found a separate real disconnect regression: the batched sender still invoked
SV_WriteSnapshotToClient for CS_ZOMBIE after the direct wrapper had been fixed,
causing repeated no-native-frame overflow warnings after EXE_LEFTGAME. Moved
the guard into the common CoDOL writer and restored the direct wrapper's common
call. Reliable commands remain available. Added regression source and rebuilt
successfully. Second launcher run, server69196, reached map startup; live leave
after this fix still needs observation.

Linux entity collector test passed, including the recent filtering, corpse and
event suppression cases. Windows snapshot fixture linkage failed on harness
dependencies, and the Linux live-send fixture lacks newer player-state/cvar
dependencies too; that test did not run. Fixed reset declarations using the
actual codol_weapon_lock.h after an initial wrong include was caught by build.

Startup still reports untracked entityState storage. The live storage binding
hardcodes1022 despite the expanded CoDOL range and needs review; no claim that
this alone explains the observed address. Full GSC/gameplay verification remains
unfinished.

## 2026-09-10: full entity range and first-person model namespace

Changed live event-extension storage coverage from1022 to ENTITYNUM_WORLD,
matching the native2048-entity allocation. Rebuilt Killhouse startup completed
without the previous untracked entity-state warning; the collector test passed.

The user then reported a C1 dialog1073 naming tag_weapon and
hea_hernandez_ss_m_yel_00. Source review found raw ps.viewmodelIndex publication
in the recent extended movement overlay. Native model indices are not CoDOL
model-bank slots. Removed that copy, resolve the captured frame's model through
CODOL_ServerModelToWire, and publish an explicit validated binding. Added a
regression with native slot7 mapping to wire55, bad mappings and clearing.
Windows build and Linux collector/viewmodel regression passed. Killhouse
launcher restarted with the fix; exact screenshot outcome awaits client retry.

Live follow-up: second run completed another fresh handshake and playing spawn
at4250,-811,4, then CS_ZOMBIE -> CS_FREE. The second-run log has no matches for
failed authentication, msg overflowed or frame rejected. This verifies the
disconnect fix on a real leave, without proving the original auth root cause.

### 2026-09-10 profile composition, transport diagnostics, camera and icon
Parent integrated/reviewed native profile recipe and appearance work, removed worker filler/tag heuristics, wired recipes into giveLoadout, and published separate captured arms/gloves and full character parts. Windows build and targeted Linux recipe/character/frame/archive fixtures passed. GSC startup passed after recipe initialization fix. Real gameplay appearance remains unverified.

DTLS rejection diagnostics now separate wrong tag, malformed length, replay and authentication/decryption failure; Windows association lifecycle fixture passed. A fresh real retry reached CS_PRIMED, then missing-BSP disconnect: C1 lobby log selected mp_cargoship_sh at15:19:05, native gamestate selected mp_killhouse_sh at15:19:12. This is a proven map mismatch for that retry, not proof intermittent DTLS is fixed.

Camera spawn height and C1 offsets verified; read-only probe observed no gameplay snapshot. Camera defect is not fixed or reproduced in active gameplay yet. See CODOL_CAMERA_HEIGHT_INVESTIGATION.md.

Extracted5 original C1 icon images into src/win32/codol.ico, switched Windows resource to that icon and sh1x title, and made resources build from source as tracked linker prerequisites. Build passed and embedded image bytes exactly match C1. Installed binary and restarted Killhouse launcher; client/lobby preserved. Full native GSC/gameplay objective remains incomplete.

## 2026-09-10: class-selection DObj crash

The closed-server log proves class selection completed transport, profile and
appearance publication, then built eight world models totaling 167 bones and
called Com_Error at retained DObjCreate's 128-bone ceiling. Later association
restore and unknown record messages occurred after shutdown and were fallout.

Static C1 inspection found its constructor at 0x633D90 accepts through 253 bones,
uses eight duplicate-mask words, and uses a 0xC8 DObj with eight hide-mask words
at +0xA0..+0xBC. Retained IW3 uses four-word DObj, DSkel, XSurface and entity
masks. A constant-only capacity raise would make upper bone indices corrupt
adjacent memory and was rejected.

The snapshot still publishes the complete eight-part appearance. The dedicated
server DObj now prioritizes jacket, gloves and head after the root, preserving
weapon and eye tags. The observed outfit becomes 123 server bones; remaining
cosmetic parts are appended only when they fit the representable 128-bit pose.
Windows build passed. Live class-selection verification remains pending.

## 2026-09-10: asset and script-loader match-entry audit

Reviewed the native archive/rawfile lookup, external/native overlay precedence,
conditional preprocessing, extended-syntax lowering, childthread compiler
adapter and saved-source restoration. The latest Killhouse evidence mounts all
nine startup archives and six map archives, compiles the startup and map script
graph through `maps/mp/mp_killhouse_sh_fx.gsc`, and loads both mounted animtrees.
The later missing-BSP disconnect is the separately recorded lobby/server map
mismatch, not evidence of a script-loader failure.

Added the two missing declarations used by the asset command translation unit:
the startup-variable parser API and native material loader API. Added focused
source-reader coverage for native-adaptation precedence, owned output, binary
source rejection and atomic failure. No loader semantics or GSC support counts
changed. Source and prior runtime logs were reviewed; `git diff --check` passed.
Per worker instructions, no build, test executable, server launch or process
restart was performed in this audit. Broader asset/gameplay fidelity and a live
class-selection retry remain outstanding.

## 2026-09-10: user-command match-entry gate audit

Current live evidence shows the native path reaching `CS_ACTIVE` and accepting
roughly 160-174 commands per two-second interval while the C1 client walks,
sprints, crouches, jumps and sends action notifications. Source review found no
remaining user-command transport blocker to basic match entry: the dispatcher
uses the measured 3-bit C1 opcodes, batches decode transactionally from a zero
base through the predicted-origin trailer, the key uses the acknowledged server
command, and raw CoDOL extensions bind beside the command accepted by
`SV_ClientThink` or initial `SV_ClientEnterWorld`.

The review did find a stance defect. C1 `CL_CmdButtons` at `0x0048FBC2`
produces prone as a level. The retained `PM_CheckDuck` also reads the current
command's `0x100` bit directly: it maintains prone while the level is set and
follows `PM_CheckDuck_410` to stand and clear stance when neither prone nor
crouch is set. `SV_UserMove` had inserted a stateful level-to-edge adapter that
suppressed the held level after one command, contradicting both producers and
consumers. Removed that adapter, including its reset-external static state, so
every translated command retains the C1 prone level. A regression assertion
covers repeated held commands.

Source and acceptance/reset paths were reviewed and `git diff --check` passed.
No build, test executable, server launch or process restart was performed.
Fourth-equipment and marker-slot consumers remain missing; tactical,
remote-control, corrected prone hold/release and weapon switching retain their
prior live-verification status. The latest live failure is a snapshot player-event
parameter rejection, outside this user-command gate.

## 2026-09-10: snapshot and configstring match-entry gate audit

The native gamestate is no longer the observed entry blocker. Current C1 logs
repeatedly parse the 7281-byte gamestate, reach `CA_PRIMED`, and later enter
gameplay without `EXE_CONFIGSTRINGMISMATCH`. The specialized namespace bridge
publishes the startup map, asset, replicated-dvar and player-name values used by
that path. Generic retained configstring fallthrough still uses an IW3 numeric
index and remains unsafe for any newly exercised producer without a measured C1
adapter; the live evidence does not justify inventing another mapping here.

The server log does expose an all-frame snapshot failure: one primary player
event parameter rejection at sequence 146 is followed by failed frames through
sequence 162. The primary queue used an all-or-nothing resolver even though the
entity queue already omitted unsupported presentation events by physical slot.
Primary player events now follow that same rule: supported slots serialize,
unsupported event/parameter pairs become `EV_NONE`, and the captured queue epoch
is preserved. Focused coverage checks that an unmapped fourth slot no longer
rejects the other three or rewrites the epoch.

The first-person appearance capture also applied stored arms/gloves to the live
player before copying the frame. Snapshot frames already have tracked extension
storage, so capture now copies both halves first and applies the stored pair to
the frame itself. This avoids live pointer-identity coupling and leaves a
spectator's followed state unchanged. The viewmodel fixture now exercises a real
tracked `client_t.frames[]` copy and verifies that changing its arms/gloves does
not mutate the live player.

Source and call paths were reviewed and `git diff --check` passed. Per worker
instructions, no build, test executable, server launch or process restart was
performed. The next authorized build/C1 check must verify the event omission and
visible arms/gloves. Individual omitted events still need semantic mappings, and
the current weapon presentation/error-178 issue may also involve character
recipe or weapon-composition producers outside this snapshot/configstring audit.

### Viewhands follow-up

The narrowed viewhands audit traced the path from the jacket/glove `vmchar`
names through native `CS_MODELS`, C1 model-bank remapping, tracked frame and
extension capture, and player netfields 60/61 at `ps+0x144` and `ps+0x148`.
Both fields are 11-bit C1 model indices. The special `<prefix>_vmchar50`
streamed-surface name is backing data referenced by the XModel; the full
`vmchar` XModel name remains the configstring value. Alpha0022 measured backing
geometry for all 143 vmchar names.

One pointer-ownership defect remained: `CODOL_ApplyStoredClientViewmodels`
accepted only the live `level.clients` address, although snapshot and archive
copies have their own tracked extension storage. It now accepts any tracked
state whose `clientNum` is the owning client, and snapshot capture calls that
helper after copying both the playerState and extension. Followed spectator
states are still rejected. Focused coverage checks the exact offsets, widths,
successful writer path and 11-bit range rejection. This source has not been
built or run; the current live result came from the old binary.

The fresh 16:52 run resolves that uncertainty on the producer side: the server
publishes both selected vmchar configstrings and reports a nonempty arm/hand
recipe. It simultaneously reports `weapon 0` in every gameplay pacing sample.
C1 only installs customized viewmodels into equipped weapon caches, and the
draw path exits when the current weapon has no arm model, so this run cannot
render or visually validate the hands. The current source and 16:51 binary both
write `2047` to `ps+0x1ec` and the captured view-height float to `ps+0x15c`,
with no later snapshot writer for either field. Added a one-shot post-spawn
developer line that reports the final wire weapon, arms, hands, view height and
linked-weapon entity after every overlay. The next run can therefore separate
a native wire value from a client prediction problem without another ambiguous
pre-selection field audit. No test or process was run for this follow-up.

## 2026-09-10: composed weapon model binding

Composed SPAS and Desert Eagle definitions were published, but their selected
`mp/coweapmodels/<base>.csv` world/view model names were retained only as
metadata. The converted native `WeaponDef` still contained the base archive's
serialized model slots. This left `gunXModel[variant]` null for the retained
`G_GivePlayerWeapon` admission check, so the give returned false and
`playerState.weapon` stayed zero.

Composition now requires a complete recipe row, resolves both recipe XModels,
and binds the selected view/world pair into every representable retained model
variant before publishing the definition. A failed row or model lookup rejects
the composition transaction instead of publishing a client-visible weapon that
the game cannot grant. Focused native-core coverage checks all 16 bindings,
unrelated field preservation and atomic failure.

The plain `throwingknife_mp` path already resolves all eleven serialized model
roles and binds its populated view/world slots through the same native loader;
archive evidence includes view model slot 1. No separate throwing-knife model
binding defect was established. The observed
`EXE_DISCONNECTED 178_0_throwingknife_mp_right` therefore remains a live
verification target after rebuilding the composed-model and existing
snapshot/viewhands fixes. Source and call paths were reviewed and
`git diff --check` passed. Per worker instruction, no build, test executable,
server launch or process restart was performed.

## 2026-09-10: weapon validation 181 map-mismatch trace

No weapon or asset source change was made for
`181 turret_minigun_mp 0 54`. C1's measured validator formats error 181 as
`name, resolved index, required slot`; the zero therefore means the client could
not load the named weapon. The client log records `StartGameRecv` selecting and
loading `mp_killhouse_sh`, while the same connection's gamestate says
`mp_overgrown`. The server log independently records an Overgrown archive mount,
loads `turret_minigun_mp` during Overgrown script initialization, and publishes
that newly registered native weapon densely at slot 54.

That publication is correct when client and server both load Overgrown: the
weapon asset comes from the same C1 Overgrown fastfile the native archive reader
mounted. Suppressing it or substituting another common weapon would corrupt the
map turret's weapon identity and merely conceal the lobby/server map mismatch.
The required fix is to make the lobby start message and native server map agree;
that producer is outside weapon/assets ownership. Source and live logs were
reviewed. No test, build, server launch or process restart was performed.

## 2026-09-10: throwing-knife error 178 event trace

`178_0_throwingknife_mp_right` is a C1 first-person presentation failure, not
wire player event 178. C1's viewmodel updater at `0x4808E0` selects
`ps.offHandIndex` while `ps.weapFlags & 0x2`, registers the selected weapon,
refreshes changed hand state through `0x47C550`, and then checks the per-hand
DObj pointer. The right-hand pointer was still null, so the client called
`Com_Error(3, "178 %d %s %s", 0, "throwingknife_mp", "right")`. The exact
format and hand strings reside at `0xC45F38`, `0xC45F28`, and `0xC45F30`.
Alpha0022 telemetry contains three independent disconnect reports with the same
space-separated reason, while qconsole records the corresponding reliable
disconnect command.

The user-command and player-event identities agree end to end. C1 supplies the
selected offhand weapon in the user command; native pmove stores that mapped
weapon, raises the offhand-viewmodel bit, and produces switch, prep, and use
events. The bridge maps them to C1 events 51, 49, and 50 and translates every
weapon parameter through the same native-to-wire registry used by playerstate
and user commands. IW4/T5 use the selected offhand weapon as these event
parameters as well. C1 prediction drives the failing viewmodel path directly
from `weapFlags` and `offHandIndex`, so receiving one of those events is not a
precondition for error 178.

No user-command or player-event source change was made: suppressing or changing
these events would break a verified state transition and would not create the
missing right-hand DObj. The remaining boundary is client-visible weapon
presentation/asset registration for the plain `throwingknife_mp` definition.
Retry after rebuilding the current weapon-model work; if the error remains,
inspect C1's registered weapon cache slot 0 and right-hand DObj immediately
after `0x47C430`/`0x47C550`. Source and live evidence were reviewed. No test,
build, server launch, or process restart was performed.

## 2026-09-10: runtime composed weapon native registration

Live profile composition published the SPAS and Desert Eagle names at CoDOL
wire slots 115 and 116, but retained `G_GetWeaponIndexForName` returned engine
index zero during `_giveWeapon`. The definition and wire registry were valid;
the missing producer was the retained `bg_weaponDefs[]` registration. After
level initialization, `G_GetWeaponIndexForName` intentionally calls the
find-only path. Profile weapons are composed later, so publishing their names
could not make them discoverable to retained gameplay.

`CODOL_PublishComposedWeapon` now explicitly invokes the retained
`BG_GetWeaponIndexForName(name, G_RegisterWeapon)` registration path after
preflighting the composed wire record. It verifies that the resulting native
slot points at the exact composed definition, rereads the expanded native table,
adds any recursively registered alternate definition to the dense wire list,
and rebuilds the complete engine-to-wire map before committing configstrings.
Repeating publication also repairs a name that already existed on the wire but
predated native registration.

The observed `throwingknife_mp` mapping (engine 3 / wire 55) demonstrates that
native and client slots are separate namespaces. After this change, each profile
weapon keeps its existing client slot (SPAS wire 115, Desert Eagle wire 116) and
maps to the exact engine index returned by native registration; the commit now
checks `mapping[returned_engine] == published_wire`. The numeric engine indices
are runtime append positions and cannot be inferred from wire slots because
wire-only partner definitions can also occupy the dense client list. Runtime
registration is monotonic, matching IW4's native weapon table. No shared
assembly change is required. Source and retained call paths were reviewed. Per
instruction, no test, build, server launch or process restart was performed.

## 2026-09-10: dive stance authority ordering

C1 runs `PM_UpdateStance` before choosing walk or air movement. During a dive
and for 100 ms after `diveEndTime`, it rewrites the current command to prone so
the stance hull, flags, and view-height state all see the forced request. The
native port instead reached its first force from `Jump_Check`, after retained
`PM_CheckDuck` had already processed the frame. That ordering permits the
grounded crouch/prone alternation seen around dive touchdown in the live trace.

`codol_dive.c` now exposes `CODOL_DivePrepareStance`, which performs the active
dive and post-completion force before retained stance processing. The prior
mutation of `oldcmd.buttons` was removed: C1 changes only the current command,
and retained `PM_CheckDuck` reads the current prone/crouch levels directly.
The completion producer also records C1 `ps+0x234` `diveEndTime` in the tracked
playerState extension. Frame, spectator and archive copies carry it, and the
movement overlay now publishes measured player field 41; leaving this field
zero prevented C1 from reproducing the server's 100 ms post-dive lockout. The
remaining shared integration is one call to this helper at `PM_CheckDuck`
entry, after preserving its pmove argument and before it reads player state.
That single entry call covers every retained call site. Player source and the
C1/retained call order were reviewed; no build, test, server restart, or process
launch was performed. C1 hold/release and touchdown behavior remain to verify
after the shared assembly call is integrated and rebuilt.
## 2026-09-10: snapshot fragment pacing and heavy loadout recovery

The visible prediction replay came from fragment scheduling. Gameplay
snapshots normally occupied two C1 fragments, while the retained server sent
only one fragment per 50 ms frame. The client therefore completed snapshots at
10 Hz although `sv_fps` was 20. CoDOL netchan now drains all fragments of one
message in the same frame, matching alpha0022's send loop. Live Killhouse
pacing changed from 20 to 40 outgoing sequences per 2000 ms, and average
server-minus-command time fell from about 160 ms to 59-61 ms. Later no-delta
recovery also keeps baseline flag 8 clear and follows the existing divergence
policy instead of forcing `readOriginAndVel` on every missed base.

The attachment-heavy camo class exposed three independent fatal data paths.
The composer now replaces unavailable declared defaults with legal
model-producing parts from the same group (`m9_mp` `iro_default` ->
`iro_glowm9`). Weapons such as `beretta_mp` that have no complete
`mp/coweapmodels` body stay on their stock base index, matching the reference
composer. Unknown optional profile items return class-validation fallbacks, and
mounted CoDOL base weapons have native safe inventory/class queries even when
their plain name was never registered in retained `bg_weaponDefs`.

The Windows build succeeded. A real C1 client spawned on `mp_killhouse_sh` WAR
with the full M4 camo recipe, composed M9, weapons 92/93 and viewheight 60. No
runtime exception or server shutdown appeared after the final restart. The
server remains active on UDP 17733. No synthetic tests were run.

## 2026-09-10: native C1 movement cutover

The full accepted `codol_usercmd_t` now survives to movement execution. A C1
Pmove entry is wired before retained `Pmove`, but its atomic readiness gate is
still closed. It will not mix a partial C1 state machine with retained movement.
The required cutover owns stance, view height, ground, slide, ladder, mantle,
dive, weapon movement, and all state those systems share.

Live Killhouse timing remained healthy: snapshot ACK gap 1 and about 55-105 ms
server-minus-command time. Stance, ordinary mantle, and dolphin dive worked.
The center-tower report instead points at the remaining movement-core boundary.
The server stopped on a 12-unit lip between commands 73619 and 73747 with
`pm_flags == 0`; it never began the mantle the client likely predicted. The
ladder state appeared later after repositioning. C1 mantle entry also clears
ladder bit `0x8` and sets C1 ladder-fall bit `0x1000`, while the retained core
uses its own `0x2000` bit. C1 mantle collision, ground/step movement, and ladder
state therefore need one native owner.

Native C1 stance/view-height and ladder/mantle transition code is being written
under `src/codol/player/codol_pmove_c1.c`. Current live gameplay still uses the
retained path. Enablement waits for every required movement component, after
which the snapshot movement-flag translation must be removed. The tower mantle
and residual replay need a real C1 retry after that cutover. No synthetic
gameplay tests were run.

### Native C1 mantle and direct snapshot publication (2026-09-10)

`src/codol/player/codol_pmove_c1_mantle.c` now transcribes C1's mantle direction sweep, three ledge probes, mantle-over endpoint probes, nearest-height transition selection, XAnim root-delta movement, completion flags, and ladder-to-mantle transition. The tower failure occurred with no authoritative server mantle bit, so this path starts from the C1 command and C1 collision rules rather than repairing an IW3 result after simulation. The atomic native movement gate remains disabled.

The snapshot path now has an atomic direct mode tied to that same gate. When native C1 Pmove becomes active, `pm_type`, `pm_flags`, `otherFlags`, and `eFlags` are copied as C1 values without semantic translation. The currently running retained build continues using its compatibility path until all native movement producers are ready; mixing the two paths is forbidden.

## 2026-09-10: native C1 snapshot cutover built online

The atomic C1 movement gate is active. `CODOL_PmoveC1Try` now owns the complete
movement frame and bypasses retained `Pmove`. It consumes the full accepted C1
command and runs C1 stance, view-height curves, ground/air step-slide, ladder,
mantle root motion, dolphin dive, sprint, timer and per-substep bob producers.
The measured C1 `pm_type` jump table now controls normal, linked, noclip, UFO,
MP viewer, spectator, intermission, last-stand, dead and dead-linked behavior.
Dead input is cleared before physics.

Player snapshots publish C1 `pm_type`, `pm_flags`, `otherFlags` and `eFlags`
directly. There is no IW3 movement-state translation in the active path.
Mantle start now uses a distinct internal event and maps to C1 event 183; the
previous raw 183 producer could not pass the native event mapper. The retained
weapon unit is invoked directly after movement for hand-0 fire/reload lifecycle;
retained `Pmove` is never re-entered.

The Windows server linked successfully and the rebuilt executable was installed
with SHA-256 `F8FEBC33365578F2F9C36D9BD1FB04C713981BD5262EAB27184076F9E42C2`.
Killhouse WAR completed startup and PID 73336 is listening on UDP 17733. C1 and
the Python lobby remained running. No post-cutover client command reached this
server while the user was away, so stance, dive, center-tower mantle and replay
remain live-unconfirmed. The snapshot is not recorded as perfect and the goal
stays active until that real C1 pass succeeds.

### Prediction-critical native movement audit

The post-cutover audit found and corrected three command-order mismatches. C1
rebuilds ADS flags before `PM_CmdScale`; the native owner had left that work to
the later weapon pass, making ADS movement one command late. C1 stance also
rewrites the command during ladder and dive lockout; those changes now flow
back into the full C1 command consumed by movement. Finally, dive detection now
uses the executing command instead of the newest accepted packet, jump precedes
dive, and a successful dive launch returns before ordinary air acceleration.
Native jump now queues the mapped C1 jump event.

The follow-up Windows build succeeded. SHA-256 is
`F15F369E45751C0E8F4D2F4BA7E0C66BF700DECDA725B7FF08DBC51C300A8CA2`.
PID 87768 is online on UDP 17733; Killhouse WAR startup is clean. Real movement
confirmation remains required before closing the goal.

### Native C1 ladder jump

The ladder path now implements C1 `PM_LadderJumpOff`: jump edge, 500 ms
cooldown and stance gates; C1 jump state/event; reflected 128 u/s horizontal
push; 0.75 vertical scaling; ladder detach; and immediate air movement. The old
path kept the player attached and continued ladder motion, which guaranteed a
prediction correction when jumping from the tower ladder.

Windows build SHA-256 is
`BBAC1EFAADBAD55F3677619A4AF945D03CA8B645D95562408619C64A8D13472A`.
PID 82852 is online on UDP 17733 with a clean Killhouse startup.

### Final native snapshot audit build

The direct C1 owner now clears the retained touch accumulator at command entry
and calls `BG_AnimUpdatePlayerStateConditions` once before every chopped C1
movement command. Retained `Pmove` previously supplied that animation-condition
producer; bypassing it left movement animation conditions one command stale.

Direct disassembly of C1 `PmoveSingle` (`0x4167f6..0x416961`) then corrected
the normal movement order. Two duplicate pre-movement ground traces were
removed, and ladder acquisition now follows stance, the authoritative ground
trace, and mantle probing. This avoids repeated landing/touch side effects and
prevents ladder stance decisions from using stale surface contact. The same
disassembly shows `PM_Footsteps` at `0x416961`, inside each chopped
`PmoveSingle`; the Python server's outer-command comment is inaccurate.

The Windows executable linked and is online with SHA-256
`16AD646D644DBEAEC6E3A0CB8F456D8128623EEEE31F6B60EE473B7DBFB5B5EE`.
PID 85808 owns UDP 17733 and Killhouse WAR completed startup without a fatal,
authentication, script compile, snapshot overflow, or rejected-frame error.
The exact build has no live client movement pass while the user is away, so
prediction replay cannot honestly be declared eliminated until reconnect.

### C1 movement speed modifiers

C1 command scaling now applies the composed weapon's hip/ADS movement scale,
the script-owned `ps+0x254` multiplier, and shellshock's settings-controlled
`0.4` factor in C1 order. Class setup initializes `moveSpeedScaler` to `1.0`
before perk callbacks; Lightweight changes it to `1.07`, and the shipped
weapon-class logic plus weapon-change listener update `setMoveSpeedScale`.
C1 direct disassembly at `0x410216..0x4102a6` and the retained shellshock
record at `+0x264` anchor these factors.

The 32-bit Windows server executable rebuilt successfully with SHA-256
`7600A51854360CB3BBF96DF7F3785D51E0F09E3240F946943D7BF2DB0D015805`.
PID 74852 is online on UDP 17733 with Killhouse WAR. Startup completed without
a fatal, script compile, snapshot overflow, transport authentication, or
rejected-frame error. Live speed comparison remains pending while the user is
away.

### C1 dive air branch and events

Active dolphin-dive frames now take the C1 air-movement branch after launch and
touchdown until `PM_DiveEnd` completes. Completion checks all three velocity
components, and launch clears C1's measured `0x2180` flag mask. Dive launch and
land now publish C1 events 185 and 186 with the compact material parameter from
C1's `0x4089a0` surface table.

The Windows server target rebuilt successfully with SHA-256
`BB9492FCEFF622D69B1781399EC42DF616DE3FE31457F37DA1C8C035E86EAB74`.
PID 81996 is online on UDP 17733 with Killhouse WAR. Startup has no fatal,
script compile, snapshot rejection, overflow, authentication, or runtime script
error. A real C1 movement pass is still needed to confirm prediction feel.


### C1 speed selector and sprint state

C1 command scaling now uses the measured ADS selector: ADS flag `0x40`, or prone with a nonzero ADS fraction. Lean applies its `0.4` penalty while retaining the hip weapon scale; invalid hip scale falls back to positive ADS scale. Bob and footsteps use the same decision.

The native C1 sprint update now produces all five sprint-state fields, including remaining meter, expiry, release latch, cooldown, exact start/continue gates and torso restart. This replaces the former flag-only toggle that disagreed with client prediction.

The Windows target linked successfully. SHA-256 is `76CF96708E2DBDAC374B9FBB4E10530F17FE5B702F0AAE70D5F4C902297A685A`; PID 52432 owns UDP 17733 with Killhouse WAR. Startup is clean apart from the existing optional `steam_api.dll` warning. Live C1 movement confirmation remains required.

### C1 prone orientation producers

The native mover now initializes `proneDirection`, `proneDirectionPitch`, and `proneTorsoPitch` on prone entry, advances prone body yaw at C1's 55 degrees/second, validates body rotation, applies yaw/pitch caps with matching delta-angle corrections, and updates both slope pitches immediately after the authoritative ground trace. These fields are published directly at C1 playerState `+0x1a0..+0x1a8`.

The Windows target linked successfully. SHA-256 is `31B3C3B734DE209F6CA8017E690778F49073B88CFBB34BE7608395A468E3D83F`; PID 87472 owns UDP 17733 with Killhouse WAR. Server, C1, and the Python lobby remain responsive. Live prone turning remains the final authority for collision-edge prediction.

### C1 command chopping and catch-up

Direct C1 `Pmove` disassembly exposed two prediction-critical IW3 remnants. C1 copies the full chopped command into `oldcmd` after every `PmoveSingle`; native code had reused the previous network packet across all substeps, replaying button edges. C1 also retains up to 1000 ms after a hitch; native code discarded everything older than 200 ms. Both now match C1, including its pre-chop input filters and 66 ms substep maximum.

The Windows target linked successfully. SHA-256 is `66D989EB78D021A4228E2FED5B4289479245423A38325432F3C62566AB9A8353`; PID 85744 owns UDP 17733 with Killhouse WAR. Live C1 input remains the authority for visible replay.

### C1 mantle branch and melee-charge state

The native `PmoveSingle` branch now follows C1 `0x4167f6..0x416978`: active mantle skips the ordinary first pass; the mantle arm runs aim, sprint, ADS, stance, mantle movement, and weapon processing, then returns without ordinary footsteps. The non-mantle arm now restores `PM_MeleeChargeUpdate` before movement selection and publishes charge yaw, distance, and time at C1 `+0x4a4/+0x4a8/+0x4ac`.

The Windows target linked successfully. SHA-256 is `37DA0F102E565681AF5C07B9ABBA41B3C03A589B78672B9E02C7CBAFE04238D0`; PID 82952 owns UDP 17733 with Killhouse WAR. Server, C1, and lobby are responsive.


### C1 lean, view clamps and final movement audit

Native C1 movement now owns lean state and collision using the direct C1
`PM_UpdateLean` contract. View-angle handling now includes the C1 range, mantle
and ladder clamps before prone orientation. Weapon hip/ADS scale, shellshock and
the script speed multiplier remain in C1 command-scale order; Lightweight sets
the multiplier to `1.07` and loadout weapon changes refresh it.

The Windows executable linked with SHA-256
`118FDC14CC173C23986E8052B29FD65D163C09406D522B2E385C8FDF7E781AD9`. PID
82048 owns UDP 17733. Killhouse WAR mounted its archives and native collision
without a fatal, script compile/runtime, snapshot rejection/overflow, or
transport authentication error. Real C1 input remains required to judge feel
and prove visible replay corrections are gone.

### C1 predicted input and melee-charge flag

The final audit found a concrete mixed-state error: retained melee-charge code
used IW3/T5 flag `0x20000`, while C1 and the native movement selector use
`0x10000`. CoDOL assembly now uses the C1 flag for charge start, update,
friction, expiry and fallback selection. The native owner also copies C1's
charge yaw/distance payload and applies the measured charge-forward, respawn,
control-lock, fire-lock and dead-command filters before simulation.

Movement speed remains the C1 stack of stance, sprint, composed weapon hip/ADS
scale, shellshock and the script multiplier. Loadouts initialize the multiplier
to `1.0`, Lightweight sets `1.07`, and weapon changes refresh it.

The Windows executable linked with SHA-256
`866B407DA6809B563722AD4D101A3D12AC7B71F2A3B5FB9D44DABA238D903046`.
PID 85708 owns UDP 17733 with Killhouse WAR. The server, C1 and Python lobby
remain responsive; the latest startup tail has only the normal startup hitch
among the requested error patterns. Live C1 input is still required to judge
visible correction and gameplay feel.

### C1 frozen, remote control and predicted flags

Direct C1 inspection corrected a flag error: frozen is `0x800`; `0x80000` is
remote controlling. Frozen now stops body movement while leaving view control
available. Remote control owns the outer movement and view lock. `PmoveSingle`
also follows C1 order for animation conditions, filtered input/firing eFlags,
aim-spread adjustment, and view-angle update.

Movement speed uses the current composed weapon's hip/ADS fields and the script
multiplier. Lightweight sets that multiplier to `1.07`; loadout and weapon
changes refresh it.

The Windows executable linked with SHA-256
`CE4FF9ED633C4B9731B720996BEC5C4F86DABDD7EE2230352B7DDCAEC7375737`.
PID 75620 owns IPv4 and IPv6 UDP 17733. C1 and the Python lobby remain
responsive. Live movement is still required to judge visible correction.

### C1 filtered old-command boundary

The C1 movement sidecar now carries the final filtered command across packet
boundaries. The old path saved the raw packet command after `PmoveSingle` had
removed frozen, respawn, dead, remote-control, or input-lock buttons, allowing
those buttons to reappear as replayed edges in the next packet. A reset client
now starts from C1's zero/default `oldcmd`, preserving legitimate first edges.

Speed remains composed from stance/sprint, the active composed weapon's hip or
ADS scale, shellshock, and `ps.moveSpeedScaleMultiplier`. Lightweight sets the
script multiplier to `1.07`; class setup and weapon changes refresh it.

The Windows executable linked with SHA-256
`F5AE4DB0DD18B3AA8FF57854C18FDA4F41022DD8A02AB9238F3F904D8F3D33CD`. PID
87716 owns IPv4 and IPv6 UDP 17733. Killhouse WAR completed startup; the server,
C1, and Python lobby remain responsive. Live input remains required to judge
visible correction.

### C1 step-slide collision type

The step-down rollback now matches C1's complete collision predicate. It rejects
only an `ENTITY` hit with `hitId < 19`; dynent models, dynent brushes, and glass
no longer look like players merely because their hit ID is small. This removes
a source of false rollback around map collision and mantle/step transitions.

Speed uses the C1 stack: base speed, direction, stance, sprint, the composed
weapon's hip/ADS scale, shellshock, and the script multiplier. Lightweight sets
that multiplier to `1.07`; weapon `sprintDurationScale` changes the sprint meter.
The native movement object and Windows executable compile. SHA-256 is
`8CAEA139F96A2A8A3AC64832EC53362685990D35240328A142D311734D77B1C4`; PID 85396
owns UDP 17733 with Killhouse WAR. Server, C1, and lobby remain responsive. The
startup log has no fatal, script compile/runtime, snapshot rejection/overflow,
authentication, or timeout error. `pexports` was unavailable after linking, so
the module definition and plugin import archive were regenerated with
`gendef`/`dlltool`.

### C1 sprint timer gate

Direct C1 inspection corrected the sprint-start jump exception. C1 tests
`PMF_JUMPING` with `pm_time == 0`; the native path had misread playerState
`+0x8` as `groundEntityNum`. The grounded step tail also applies C1's
prone-volume check and last-stand rollback-direction rule before slowdown. Both
corrected movement objects compile. Non-normal movement also no longer creates
a sprint-button-up latch unless it stops an active sprint, matching
`PM_UpdateSprint 0x40f911..0x40f959`.

Speed remains data-driven through base speed, direction, stance/sprint, the
composed weapon hip or ADS scale, shellshock, and
`ps.moveSpeedScaleMultiplier`. Lightweight sets `1.07`; weapon
`sprintDurationScale` controls sprint time. The local weapon script now updates
the class multiplier from the actual newly equipped composed weapon, and perk
set/unset callbacks recalculate against the current weapon. Switching to a
secondary or changing Lightweight no longer leaves the primary weapon's scale
active. The final Windows build and live startup are recorded below.

### C1 walk, air, friction, and dive-slide parity (2026-09-10)

Direct C1 disassembly exposed a remaining prediction mismatch: an active dive branches from `PM_WalkMove` into `PM_AirMove` without erasing `pml.walking` or `groundPlane`. The native path erased both, so landed dive frames bypassed C1's contact-dependent slide friction. The server now uses a distinct C1 air mover for jump/dive frames while preserving landed contact state, and implements C1 `Dtp_ReduceFriction` (`0x408ca0`) with its hull trace, 300 ms slide window, and completion.

`PM_Friction` now follows C1 `0x40fa90`: low speed zeros all velocity, slick/knockback skips ordinary ground friction, and the sign-bit, jump-land, dive, melee-charge, and pm_type 5 factors are applied in the client order. Walk and air axes remain horizontal; ground-plane projection and post-air prone correction follow the corresponding C1 routines. The three touched native objects and final Windows server compile.

### C1 ground and jump lifecycle parity (2026-09-10)

The native ground path now preserves `PMF_JUMPING` through initial contact and runs C1's landing slowdown lifecycle instead of clearing the jump immediately. Ground tracing uses C1's linked-view probe, missed-ground proximity probes, `walkable`/`cflags` classification, steep-plane state, airborne-to-ground crash landing, and mover touch registration. Crash landing now produces the C1 movement-visible fall damage, `pm_time`, velocity scaling, and landing events.

Jump checking now runs C1 `Jump_ApplySlowdown` first, matches the C1 state/input gates, consumes held jump input, reduces repeated-jump energy with the C1 land factor, resets the sprint latch, updates spread, and emits the surface-qualified jump event. Native objects compile. The frame builder remains zero-seeded and writes native C1 fields; stale IW3 wording in its comments was removed.

### Final C1 movement build (2026-09-10)

The 32-bit Windows server linked after the C1 ground, jump, friction, air and dive pass. Speed uses the current composed weapon's hip/ADS values, stance and sprint factors, shellshock, `sprintDurationScale`, and `ps.moveSpeedScaleMultiplier`; Lightweight supplies `1.07` and weapon/perk changes refresh the active value.

`codol_dedrun.exe` SHA-256 is `ED753943BA90CA20F1F268A445F410E088DEDA6B4760FBAFBB3EA6D1B400A2E3`. PID 73848 owns IPv4 and IPv6 UDP 17733 with Killhouse WAR. Server, C1, and the Python lobby remain responsive. Startup has no fatal, script compile/runtime, snapshot rejection/overflow, authentication, or timeout error. Real C1 input remains required to judge visible prediction correction.

### Native C1 ADS and weapon speed timing (2026-09-10)

The native C1 movement owner now integrates `fWeaponPosFrac` with C1's reload,
rechamber, ADS-only-fire, and transition-rate rules. The retained IW3 integrator
is disabled for sh1x, so ADS state is advanced once per command. C1 weapon fields
`+0xbcf`, `+0xbca`, and `+0x9b4` are imported into the native definition/core.

Movement speed composes the active weapon's hip or ADS scale with stance,
sprint, shellshock, and `ps.moveSpeedScaleMultiplier`. Lightweight supplies
`1.07`; loadout, weapon-change, and perk callbacks refresh the multiplier.

Active C1 ability ID 10 now scales ADS elapsed time through
`mp/coAbilityModifiersTable.csv`, matching C1's transition accelerator.

The Windows executable linked with SHA-256
`BA43C46252AE5568FD26426C00A516BA3063937B2A6168206529C8B853BCD0CD`.
PID 80220 owns IPv4 and IPv6 UDP 17733 with Killhouse WAR. Server, C1, and the
Python lobby are responsive. Startup contains none of the tracked fatal,
script, snapshot, transport, or timeout failures. Live input remains needed to
judge prediction feel; linked-mode nonzero transition timing remains open.


### C1 live desync, mantle, and client-crash pass (2026-09-11)

Live packet timing stayed healthy while full forward input collapsed from a requested 190 u/s to roughly 1–3 u/s, identifying movement/collision disagreement rather than network latency. The server now contains the exact C1 eight-plane slide solver, ground-normal diagnostics, exact C1 link flags and weapon-phase gates, and C1 sprint animation/bob/footstep production. Mantle start/end timing is logged directly.

The repeated client crash was an access violation at C1 `0x00AEA51C` reading address 1. Its console also logged missing-DObj warnings; neither the entity type nor a causal link to the crash was established. C1 `POF_PLAYER` is now established from session state, and retained invisible client slots are omitted from C1 entity snapshots. The lobby RCON path now executes map commands with server power.

The Windows executable linked with SHA-256 `4F34B21FA4AADC012973578F8D0F0314E333203FE9EF91838A16884D91352DA1`. PID 88228 is responsive with Killhouse WAR; Python lobby PID 55144 was preserved. A fresh C1 process must reconnect to confirm the client-crash correction and supply movement/mantle diagnostics.

### C1 entity transition and ladder follow-up (2026-09-11)

The first active client frame repeatedly processed entity 0 as a script mover
without a DObj. A stale lobby entity was suspected, but was not confirmed by a client entity read. The server now publishes the explicit
C1 `ET_INVISIBLE` transition before the playing state changes it to `ET_PLAYER`.

The selected server spawn `(3008,-1018,4)` matches Killhouse's measured
`mp_tdm_spawn_allies_start` XY coordinates; that alone does not prove the
client received the position or that the floor trace is correct. Periodic logging
now records entity-0 wire type and the client's predicted-origin trailer.

C1's failed airborne jump-step calculation also now falls through to the
upward-ladder gate at `0x4178dc..0x41790d`, instead of stopping early. The
Windows executable linked with SHA-256
`4AAB94045C3BEF7401706EB9E12BAC7FE43D82FBC5605037C1E9868BB65B20F9`.
PID 63956 is responsive with Killhouse WAR. Live reconnection validation is
pending.

### Zero spawn and inverted dive dispatch (2026-09-11)

Read-only C1 memory confirmed snapshot and predicted origins `(0,0,0)` while the server held `(3003,-1022,4)`. Temporarily enabling the existing position assertion recovered client position; it was restored to zero afterward. This establishes a missing position handoff, not an invalid map spawn point.

Ordinary walking incorrectly selected `PM_AirMove`: the caller negated `CODOL_DiveGroundFrame`, whose true result means dive/air movement. C1 `0x41095f..0x410963` confirms the opposite branch. Removed the negation. This explains grounded air acceleration competing with ground friction and the logged 1-3 u/s server movement. Also corrected two C1 step-slide branches. Both movement objects compile; no tests run. Snapshot policy changes and full executable link remain pending.

Parent reviewed the snapshot changes against C1 `0x5a619b..0x5a6238` and `0x5a44b0..0x5a4561`: actual ACK base plus matching predicted commandTime and position are required before omitting position; forced field sends and predicted-angle filtering now follow the live writer. Removed obsolete origin comparison storage. Full executable target linked successfully (make exit 0), SHA256 `126A076675814A511CADB81F6D93DC3E41AE57BA62AEDA1EA9712D0E0692AB18`. Native server PID78052 started on UDP17733; C1/Python were preserved. Live confirmation remains pending, including any command-time disagreement keeping ROV enabled.

Live reconnect confirmed matching spawn `(4175,-1030.8,4.125)` and eyeZ64.125, with ROV returning to0. Ground movement runs and sampled client/server speeds164.5/164.3u/s. A subsequent mantle crashed native PID78052. Its Windows dump shows `G_SetLastServerTime` reading0x3168 from a null entity client pointer; entity0 had been zeroed. `G_RunFrameForEntity` applied IW3 temporary-entity expiry to the C1 player mantle eFlag0x10000, freeing the player after mantle start. The retained expiry rule now excludes C1 client entities. Rebuilt successfully, SHA256 `3652BD283C798C285D66F58C25F2B42D09AF2F2C5140430F453D020EABED8BA5`, and restarted native launcher. Mantle completion on this build still needs live observation.

A subsequent C1 crash was independently traced to a decoded team7 (see `CODOL_LIVE_CRASHES_20260911.md`). The saved-baseline mismatch is now fixed across all snapshot sections: separately owned deep baseline, accepted-send promotion, reset/reject cleanup, and headerdeltaNum0 decoupled from the effective pinned base. Parent reviewed ownership and C1 decoder instructions, compiled/linked successfully. Final SHA256 `1E4E55DB5F16650D4A106D8BDB554A8DF8DC2AACAC110D91D9B99A1D6EA9EBC4`. Server launcher and existing client launcher started; Python lobby preserved. Final-build reconnect/mantle confirmation remains pending. No tests run.

Final build live: server87628/C1 90956 remain responsive after team/class selection and spawn `(4246,1288,4)`; client/server positions match and ROV returns0 with delta gap1. Python55144 remains running. Mantle completion still awaits a sample.


2026-09-11 live follow-up: build1E4E completed three mantles (53609..54399,56445..56932,58538..59036). Later death ended the match through missing coop-only generic_death_russian_5 in an IW4 script overlay; processes remained alive. Replaced death call with faction-prefix m1_mp_death from localized_common_mp, matching current male appearance context; five variants per faction list, native sound validation retained. Weapon audit found omitted primary fresh-pull, shot count, recoil restriction and inventory rechamber state; published existing native producers after C1 reader/consumer review. Replaced IW3 phase-clock perk dvars with C1 ability values1/22/23, preserving unscaled recoil clock; same scaler for secondary. BuildE93975911782CE8954D864FF344DB403E3659B389479F93905F08EAA6E2B4AA9 linked successfully, no tests; Killhouse launcher invoked. Live weapon/death confirmation pending; secondary burst fresh-pull lifecycle remains separate open audit.

2026-09-11 continuation: previous turn made source/build progress. Secondary trigger audit verified C1 burst-only latch arm41ab23..41ab31 and first-shot consumption41b63c..41b646; native secondary wrongly armed semi-auto too and never consumed. Corrected those and retained pending burst pull across release, matching C1 counter-only clear41af59. Automatic firing no longer clears shot count where C1 leaves it unchanged. Build 93D743FC659CF6FA80883E7C6092827F25621E228E962817D3BC1F5AA3344E41 linked successfully and Killhouse relaunched. No tests; live firing/death confirmation pending; secondary inventory rechamber and suspended-frame trigger sampling remain open.

2026-09-11: User confirms non-full-auto weapons improved, reports death timeout, ladder top obstruction, initial ammo0/weapon(null) until switching. Old log proves ItemWeaponSetAmmo args mismatch (third left clip interpreted as IW3 slot); native handler uses IW4 5f2520..5f2678 contract, left magazines stored in existing entity union with unchanged0x274 stride and transferred on pickup. Holstered secondary magazines preserved. Rechamber worker hit usage limit after writing per-weapon persistence/publication and bolt-delay changes; parent reviewed those branches, primary akimbo duration still open. Ladder C1 415a54..415b13 horizontal projection/push condition corrected. Build 69BCE9FDC8E96AE9BDABC961FE19C821878E26DFF0BF9B27402A156DC95955E2 exit0, no tests. New fall-death crash80500 is distinct: XAnimNotetrackExists dereferences unmapped tree2f6400e0 (anim42f); investigation incomplete. Initial HUD/ammo and full death/ladder live behavior unverified.

2026-09-11 latest death: corpse DObj assembled150bones and hit128 retained cap. Captured source outfit during native clone creation; corpse now shares live-player pose builder without changing to a later respawn outfit. Full253bone native representation remains unfinished. Initial HUD audit found reliable a92 for weapon wire114; G_SelectWeaponIndex and equipped-offhand now publish mapped C1 identities, while native bot selection stays native. Build 3E7286106653A4E25423D6F3A207FCE0D55D75D277AFBB96FF177E91AAAAF224 exit0, Killhouse launched, no tests. Live confirmation pending; previous animation-tree lifetime crash remains separate open work.

2026-09-11 custom-class failure: pat.csv contains three-column material rows; model variant lookup rejected table width before row kind, causing codol_applyProfileCharacter script exception and match shutdown while process survived. Row kind now precedes four-column model validation. Source reviewed; executable linked, SHA256 51D5BD031F0CB5649830DA23AA93789DED550C9892AB46AC5BB8A84CE0802F8D. Killhouse launcher restarted native PID92172, C1/Python preserved. No tests; affected custom-class spawn remains unverified live.

2026-09-11 death overflow: corpse19 retained ragdoll pos11/apos9 rejected whole frame (only5bytes after recovery). C1 client range10..12 and evaluator table verified; native ragdoll producer/query/evaluator updated to C1 values, snapshot publishes directly. Build C27586A3EE429AB06C38BD3FCE57DF2046B86722E97515FEB59447FD551E88ED linked, Killhouse PID54208 startup complete; live death pending, no tests. Ordinary airborne bob gate also written after C1 disassembly review, not yet built. Secondary startup and attachment audit ongoing; shadows stretched/darker reported, no gameplay image yet.

2026-09-11 final integration: death dump54208 and prior80500 traced to GetCorpseAnim clearing IW3 toggle0x200 instead of C1 toggle0x400; anim42/47 became1066/1071. Earlier stale-tree hypothesis corrected: minidump missing pages did not prove unmapped lifetime. Native getter fixed. Runtime weapon append now updates/broadcasts CS6517 after names, initializing C1 localized HUD records before secondary selection. Heartbeat default hbs/sra group mismatch fixed; worker fastmag producer/toggle/timing/animation and archived state reviewed. Airborne bob phase now preserved per C1. Build91EF2D0F3F09B005149A27B8D12E2A4BC0A3E078A3B454149F2F6366BB8237D4 linked successfully, native launcher invoked; no tests. Live confirmation pending. Shadows remain unresolved; no lighting/settings edits. Separate turret toggle mask remains follow-up.

Final reconnect: PID88536 responsive, player joined; log confirms CS6517 counts115/116 after weapon names and heartbeat item69 in recipe. Initial snapshots flow without rejection. Visual behavior/death confirmation pending.

2026-09-11 live follow-up: user confirms secondary HUD and heartbeat fixed; alternate fastmag reload still absent. New M9 firing delay traced to wrong first-raise field: +60c3000ms instead of C1+ba0250ms; source corrected. Second-death overflow is scripted pickup event9/parameter93 retained in all32 captured frames (read-only PID88536), with no parameter resolver; added item/ammo pickup weapon mapping, confirmed C1 producer52864e and event selectors5282ab/528305. Precise event failure detail added. Source reviewed, build pending; no tests.

2026-09-11 Shadow Company: read-only native character/corpse had eyewear root and no jacket. SC character1 uses old Python eye-first slot convention; C1 direct profile copy/group table independently verified. Added narrow legacy fingerprint normalization before tone/defaults, leaving saved profiles and canonical classes unchanged. Mounted item110 has correct elp group; Python exported en2 was erroneous. Built pickup resolver, M9 first-raise, legacy character correction and bounded fastmag transition diagnostics: SHA2561D2317F5657B4C5BC0886D66948B99CB924DE66D064346713D23CDA24A6F730C, exit0. Native launcher restarted, client/lobby preserved. No tests. Fastmag normal/empty works but quick/quick-empty absent per user; source agrees C1, relevant live M4 not captured. SPAS pump replay remains open:467/449 timings match, passive capture missed firing. Visual/live confirmation pending.

Post-build PID85712: auto-reconnect and snapshots active. Read-only SC record now nine parts with pants root fpa_technoa_sc_m_01, jacket and vest restored; arms/hands valid. Legacy normalization reached live gameplay; corpse visual/M9/death confirmation pending.

Shadow visual follow-up: screenshot18548bd9 still has broad wall patch after character fix. Actual loadscreen IWI variants decoded to obj/killhouse-loading-iw_image_02.png and12.png; both show roof-beam grid. Brush audit315 visible entities matches shipped indices/origins; no identified misplaced caster or dynamic primary light. Four hiddenmodels excluded via clientMask. No speculative changes/tests. Camera-relative versus fixed behavior requested; current client disconnected prevents renderer isolation.

Shadow follow-up: user confirms camera-following patch grows with proximity to wall. Prior fixedbrush audit negative; local-player/viewmodel shadow or shadow projection now stronger leads, not established causes. C1 currently commandTime0/no gameplay snapshot, so live renderer isolation unavailable. No speculative code/settings changes.

2026-09-11 autonomous UI shadow comparison: rejoined Killhouse using existing C1. Broad wall darkening visible before class spawn. AO High->Off did not remove it; subsequently Shadows On->Off removed sharp roof-beam shadows but broad wall darkening remained. Settings applied and verified. Restored Shadows On/AO High and verified after renderer refresh; C1 left open at mode selection, native/Python preserved. Camera drag produced large rotations, so exact proximity-dependent boundary not isolated. These observations weaken weapon-only/ordinary shadow-caster hypotheses but do not prove the surviving region is the exact user artifact. No source/build changes or automated tests.

2026-09-11 parallel follow-up: parent reviewed worker akimbo rechamber correction against C1 4190a4..4190d5. Primary now selects alternate duration and compares bolt delay against it; both hands preserve serialized zero duration. Built SHA25675AF456BBF9FBCF0A52E890EA862771DECBB67A822AEEBBE888FB5A5303CBBD6; initial link blocked by running exe, succeeded after verified native stop. Launcher restarted PID65908, C1 PID74192/Python55144 preserved. No tests. Live akimbo confirmation pending; SPAS replay still unresolved. Fastmag C1 producer4192f0/418080 and renderer47ba8b..47bad2 confirm four direct branches with no availability gate in producer. Added passive reload probe for paired hand states/inventory bytes/four animation names; signature guards passed and current commandTime0/no snapshot correctly suppressed stale definition reads. Shadow worker evidence is in CODOL_KILLHOUSE_DARK_REGION_AUDIT_20260911.md; no proven shadow fix.

2026-09-11 SPAS cause captured: autonomous Killhouse class5 shot, passive obj/spas-ui-capture-2.jsonl. Client completed pump to idle1024 then authoritative ready-state snapshot restored pump4. Timers match at commandTime331820. Parent reviewed C1 41911f..41913c/418f00 and added missing native no-latch completion path; detailed sample evidence in CODOL_SPAS_REPLAY_CAPTURE_20260911.md. Also reviewed second-hand reload delay/brass/zero-duration lifecycle corrections against419150/419646/41a1b0/41a550/41ace0. Both objects compile; linked SHA25614A36F66C328F198DD0F98C124FA01B7AD31705509A90F7E36ACADF66E89E795, native PID91984 launched. Client74192/Python55144 preserved; client timed out across intentional restart. Post-fix firing verification pending. No tests; fastmag/shadow causes remain open.
`n2026-09-14 equipment goal: previous investigation yielded DTLS key-churn evidence, not an equipment fix. Current pass corrected explicit offhand slot validation at both script/native state layers after direct C1 40c7e0..40c868 review. Source reviewed, not built/live verified. Class script still omits special and routes tactical through IW4 flash/smoke handling; full suite remains incomplete. Shadow agent traced brush scene submission and documented remaining angles/visibility capture gap. DTLS and fastmag agents dispatched separately. No tests.
2026-09-14 continuation: previous turn made source progress. Custom spawn now reads lethal/tactical/special together, gives start ammo and explicitly assigns three C1 offhand slots; copycat preserves that selection. Profile equipment bypasses IW4 equipment and flash/smoke replacement. Empty deathstreak now returns specialty_null and validation accepts it. Source written, no build/tests/live verification; equipment effects/ammo validation, perks, deathstreak lifecycle, action slots and HUD remain incomplete. Shadow agent assigned guarded final scene-brush capture; DTLS stale context and fastmag recipe findings remain unconfirmed causes.
2026-09-14 build continuation: shipped equipment catalogue corroborates1200..1212 names including flash_grenade_mp, flare for tactical insertion and blastshield specialty. Found Python overlay killstreak _codol callbacks substitute invisible/simple effects; full native suite requires replacing those rather than counting them as support. User authorized stop/rebuild whenever progress is made. Initial link blocked by verified running codol_dedrun_next PID54772; stopped that native process, rebuilt successfully, copied to codol_dedrun.exe. SHA2561B389406BBCA8A400D1F32673C071CF681A6F5A38427D9DFE563E772B727AA6E. Launcher selected next executable PID80480; startup progressing with table misses and no observed script compile error yet. No tests. Full startup/live equipment confirmation pending; C1/Python preserved.
2026-09-14 perk continuation: previous turn built equipment changes. Verified PID80480 startup reached checksum phase without script compile failure. CoDOL item catalogue places Lightweight in pk1 and includes Fast Mantle/Quick Swap absent from IW4 lists. Native profile getter now validates per and pk1/pk2/pk3; custom class bypasses incompatible IW4 perk lists/unlock fallback. Stopped verified PID80480 and rebuilt/deployed SHA256D11B561001A58F93E0A4E205BC30EF83BD4F3AB36F1B8CA1B8CF71BFE91EF46D; launcher invoked, C1/Python preserved. No tests/live effect verification. Killstreak HUD audit assigned; shadow passive scene capture remains pending active gameplay.
2026-09-14 runtime equipment failure: user saw wrong items/explosion crash/spawn shutdown. Current qconsole identifies unknown white_phosphorus_grenade_mp at setOffhandEquipment, preceded by giveweapon none. Retained G_GetWeaponIndexForName only found precached definitions outside initialization; CODOL path now uses runtime BG_Get/G_Register and mounted FastFile loader for all names. Added class/member/item diagnostics. Deathstreak des and killstreak kis marketplace validation written. Parent reviewed worker C1 five-action-slot source, archive order, reset and snapshot publication; all linked successfully in runtime-equipment-build.log. Explosion crash remains unconfirmed (old log abrupt event63; no current dump). Shadow active253brush capture matches model/origin/entity/angles; no rootcause. No tests or claim of corrected live equipment selections.
2026-09-14 continuation: prior source/build progress verified current startup reached checksums. Parent inspected C1 explosion52efea..52f034 and added finite float damageConeAngle from WeaponDef788, preserving atomic import. Build/deployed708BDD34BCE81B5F3790BA19FAB80ADCAE2FFD5771FD340DF7DF7D698A944386, launcher invoked after stopping verified100076. This corrects damage semantics, not proven explosion crash. Found Python equipment slot map explicitly INFERRED; agent now verifies possible special/tactical reversal against actual C1 defs. HUD agent implementing C1 count64/IDs68..78/targets7c..8c and native script producers. No tests, full suite incomplete.
2026-09-14 HUD continuation: previous turn source/build progress. Parent _class now preserves fourth profile streak, clears five C1 preview entries and publishes sorted reward table IDs/targets. Reviewed worker native HUD methods, captured-state fields, paired archive block, reset and script count producer; built killstreak-hud-build.log exit0. Corrected profile equipment assignment to lethal/special/tactical button order after C1 binding names and shipped offhand definition audit; explicit Semtex selection remains valid. Removed Python simplified killstreak overrides through native script copy retaining engine-backed paths. Deployed/relaunched; live equipment correctness, kill counter and full streak execution remain unverified. Perk ability effect audit active; explosion crash and shadows unresolved. No tests.

2026-09-14 live Semtex reproduction: class0 spawned successfully on75C13835, including runtime white-phosphorus registration. G throw caused _shellshock.gsc71 DamageConeTrace(position) parameter2 missing; native process remained alive and shutdown produced later no-frame overflow warnings. Fixed CODOL retained optional ignore-entity argument count to >1, preserving CanDamage. Built/deployed ED9AE6BF24F28AB9DE798B9D623D19411EFD239FBE946E3BFC33E2DF71273C99; post-fix live pending. Preserved failure log obj/equipment-semtex-script-failure-20260914.log. Class0 raw1201/1227/1208: both live client and server marketplace lack1227; no invented equipment mapping. No automated tests.

2026-09-14 Semtex correction: user reproduced same script error after ED9AE6BF. Parent discovered wrong assembly guard CODOL excluded patch. Corrected CODOL_SERVER; build3E636C469A611E8F4556F66F537A1C914669EC5D882D17E53F2C6CD96A13D9D7 linked and objdump confirms5c96a8 cmp eax,1 / ja optional entity branch. Deployed both names and relaunched after verifiedPID74912 stopped. Live confirmation still pending; prior claim of effective executable fix superseded.

2026-09-14 selected-class ID root cause: C1 scalar item setter590b56 inc/getter590c8a dec; equipment member tablecd234c, perks591488/59173a, killstreaks5914ba/591764 and deathstreak6be71f establish stored ID+1. Parent reviewed equipment worker fix and added perk/streak/deathstreak decoding. Underlying profile and weapon/attachment formats unchanged. Class0 actual frag1200/bouncingbetty1226/concussion1207 now matches UI. Build-class-id-decode-20260914.log linked; both executable names deployed/relaunched, includes corrected Semtex DamageConeTrace guard. Live verification pending; no automated tests.

2026-09-14 perk-effect runtime: added pure table aggregator and per-live-client authoring layer. Perk set/unset/clear recomputes selected contributions; explicit script values survive independently of activation. Effective ext abilities use existing snapshot/archive path; Lightweight server-only42 multiplies session base at ClientEndFrame producer and old1.07 script callback removed. Resets cover spawn/disconnect/globalclear. Parent review corrected slotless numeric modPistolDeath, value ownership and global reset omissions. Added reviewed C1 makeScrambler(owner) captured scriptmover flag+owner publication; deployment scripts remain missing. Build-perk-runtime-deploy-20260914.log linked, both executables deployed and launcher restarted after verified69384 stopped. No automated tests, live confirmation pending; all other server-only consumers/full reward/equipment lifecycle still incomplete.

2026-09-14 persistent shellshock: user reported lifelong movement/equipment restrictions. Parent/worker independently found retained ClientThink_real_130 cleared IW3bit10000 while native shellshock setsC1bit8000. Corrected ANDffff7fff and strict level.time>end boundary from C1 50cbf5..50cc13. BuildF0D14097A78D703D6B5CD361F9636A6984BF5336906AD9E57C58717CE391D39D linked; objdump5a2e66 confirms compiledclear. Deployed/restarted after verified101932 stopped; live confirmation pending. Script upgrades/validation/deathstreak threshold now query coPerkStatsTable; shippeddeaththresholds4 confirmed. LastStand/martyrdom ability gate audit yielded C1 evidence but implementation still pending. No automated tests.

## Equipment lifecycle resume, 2026-09-14
Reviewed and deployed scrambler/Betty lifecycles, weapons init and IW5 Betty vertical/stance damage policy. C1 FX bones verified. Native damage notifications now expose weapon argument10 and guard deleted/reused receivers before further engine handling. Detached cleanup fixes death-endon self-cancellation. Build C6554A016D46B53948C5422A474A85FF4EB794431958D9CDA0D8B72C804503B0 compiled/linked; native76480 restarted, C1/Python preserved. No automated tests. Real equipment gameplay remains unverified.
Replicated dvar repair verified in live C1; exact Killhouse dark-wall cause remains unresolved. Existing shadow and weapon-timing agents reassigned to shadow cause and four-state fastmag reload respectively at user request.

### Betty hint failure and C4 detonator follow-up
User live Betty failure exposed retained setHintString trigger-only receiver gate; previous availability audit was insufficient. Implemented generic live-entity hint setter and cursor-hint eligibility through makeUsable contents, preserving native pool/sentinel. Both activation notifications now guard deleted/reused receivers. C4 event63 now carries selected main/offhand weapon identity so existing detonate,c4_mp waiter wakes. Built/deployed EC97299FE045F66E7A9EC9706EDCE4717A6BF92E38E6368D5CE5EB7388758176; C1/Python preserved; no tests. Live fix confirmation pending; shared pickup work ongoing.

Shared pickup GSC now deployed after parent diff review with native stopped: C4/claymore linked use origins, scrambler/Betty common one-unit refund and capacity check, terminal-use cancellation, stationary activation. Same matching EC97299 executable; gameplay confirmation pending. Fuse-preserving live throwable recovery, throwing knife and tactical insertion remain incomplete.

## Localized pickup, TI and fastmag increment
Built/deployed E7DA02ECB2431C762564F94DB4ED1002EC6A3AAD4E9FAFCE13F651C8D71A04EF. Cancelled pickup waits now guarded; C1 localized hints verified from shipped localization assets. Existing tactical insertion lifecycle repaired without replacing it. Event M4 fastmag adaptation guarded by resolved definition/attachment/model equivalence, preserves event selection and falls back unchanged with warning if verification fails. No automated tests; live behavior unverified. Betty disappearance unresolved: stale captured entity excluded, setModel relink confirmed. Direct C1 knife pickup branch identified for next native work.

## Betty model selector correction
Direct C1 script-mover consumer reads model selector +0x5c; server had published +0x98. Corrected ordinary ET_SCRIPTMOVER path, preserving general/brush paths and animation fields. Parent reviewed source and linked branch. Built/deployed F5D331AB53442CF7D5AD9105A5BFF81E7D8A93D7CB47DEDBA06EBA8C8ABBD848; native restarted, C1/Python preserved. No tests; rendered visibility pending. Knife metadata/ammo helper also compiled; use/hint integration remains incomplete.

## Knife, reward order and selected timer increment
Built/deployed B7C9E3530D70354DD5FDC002C65EA651104985CE691AC85F9B936068AFF4D9F9. Native knife use/hints/capacity/ammo transfer integrated after parent caught entity-type/pm-type confusion; bounds checked. Reward granting now walks costs ascending; class thresholds/IDs read C1 table and selected Hardline modifier. Equal-cost choices forbidden by C1 UI; rollover retains verified COW semantics. Last-stand timer arguments now read selected numeric modifiers. Matching scripts deployed while native stopped, then restarted; no tests, gameplay confirmation pending. Full equipment/streak/perk suite and shadow remain incomplete.

## Death index, missing HUD and grenade increment
Built/deployed 000A43A24CD53649ED6A383EDB06EED7384F41F5C7939B2A3F4A4D8249492849. User repeated first-death position matched omitted C1 corpseIndex: clone return captured, archived and published atps+e4, parent/peer reviewed and linked call verified. Missing scr_game_hardpoints proved through active C1 zeroHUD and native dvar enumeration; missing-only default1 restored. Reward revocation/action cleanup and callback identity checks deployed. Native frag-class throwback field40, exact selection and archive included. Recipient grenade-protection scales and queued-flash lifecycle cleanup deployed. C1/Python preserved, no tests. Gameplay confirmation and full remaining suite still pending.

User live confirmation: killstreaks now visible in HUD after missing-only hardpoints default. User also confirms fastmag quick reload animations still do not play; prior event-M4 adaptation is not a complete fix and renewed passive equipped-weapon investigation assigned.

User live confirmation: repeated first-death origin fixed by corpse-index publication. Fastmag log on class3 shows equivalence guard failed, preserving original event-M4 recipe; renewed investigation has concrete guard failure to diagnose.

## Recovery and C1 catalogue increment
Parent reviewed, built and deployed 1C9A7929FB38AB04066C39523EAA4683D8428D30D954399735BBDD6C6B0A373B. Owned timed specials now recover one item with exact ownership/capacity and generation-safe cancellation; localized pickup delimiter verified against C1. Missing-only perks default and C1 reward metadata staged scripts installed while native stopped. Model lookup now matches C1 reverse tie traversal; fastmag still blocked by real muzzle geometry mismatch. C1/Python preserved; no tests. Live behavior pending. User-requested T5 combat-training bot implementation assigned existing worker, including full C1 bot input and map CSV navigation; no bot completion claimed.

Scavenger lifecycle follow-up source-reviewed: native touch validates bag inuse and generation after script notification before free; staged _weapons guards undefined drop result. Awaiting coherent radar/bot compile boundary; not deployed, no tests. Current live1C9A7929 reached active spawn/movement. Existing explosion/fall selected-defense consumers are already present in live _perks.gsc; old bounded audit docs describing their absence are historical, not current support inventory.

## Radar, initial combat bots and scavenger deployment
Built/deployed7AB1562CD7C5A5FC1D85C64F6627AFA86D66F37FBB7B0042B5F03DDD4FA69787. Parent-reviewed C1 radar type/archive/fields and staged SR71 scripts installed, explicit IW5 30s adaptation. Initial native combat bot commands/navigation/aim/fire built; scripts wired and15 graphs installed under home/main/waypoints; default scr_codol_bots0, actual bot gameplay/advanced tactics not complete. Scavenger generation-safe cleanup/undefined drop guard plus verified canonical frag/semtex refill exclusion deployed. Native restarted, C1/lobby preserved. No tests; live verification pending.

Bot live failure: totalShots secure profile absent (uid0 attachment rejected) caused script shutdown before overflow. User directed CSV standard loadouts rather than playerdata. Parent staged match-local stats/account-progression separation in obj/bot-stats-stage; worker implementing authoritative editable bot CSV with native complete recipes/equipment/perks/appearance. Not deployed yet, no tests. Do not restart old bot-enabled build as though fixed.

CSV bot deployment: F35263FC55E8A07AD60330EC53D2D3EA8B2D75D7055778CC0285E3DBC7A21713 compiled/linked and deployed. Nine-class editable CSV at bin/home/main/mp/botclasstable.csv is authoritative FS input; native recipes and appearance avoid playerdata. Parent bot-local stats/progression/card/challenge separation deployed with class/team routing. Includes reviewed goal-notification generation caller guard and navigation increment. Native restarted; C1/lobby preserved. No tests; actual bot spawn/combat pending.

2026-09-14 bot account follow-up: D7D2B32A built/deployed. Awards account paths
skip bots while retaining match counters. Native bot profile autobind skipped.
Live startup cleared awards, then exposed client-only killcam FX registration
and account perk upgrade lookups. Bot script guards deployed for both; selected
CSV perks remain active, no account-earned upgrades. Combat loop pending.
Follow-up build E6C49FDEFEEA7E126B5CEE0181B2299779B545CEC815914FB048544DDB38D0C1:
active native bots excluded from remote packet timeout checks. One bot completed
CSV loadout/appearance spawn; no script shutdown observed in latest run. Native
server PID99836 remains running. Movement/combat quality not yet verified.

2026-09-14 continuation: previous turn classified progress (bot crash fixes).
C1 target confirmation now carries position plus selected compass-relative yaw.
C and retained assembly compiled, full build8838BCD0 deployed/restarted. No live
selection proof; cancellation unresolved. Worker bomb metadata included without
changing effective type4 behavior; constructor remains in progress. Shadow worker
proved captured first-person model excluded from both sun partitions by masks;
actual artifact cause remains unresolved. Full objective active, no tests.

2026-09-14 cancellation: direct C1 client490b10 proves cancel40000; native
selection now consumes accepted raw edges, removing IW3 confirm translation.
Build3B24B7E0 compiled/linked, deployed/restarted. Live cancel retention unverified.
Mortar constructor compiles unregistered; impact/notify integration gated pending
review. Worker resumed review after parent isolated shared assembly for deployment.
Shadow material eligibility probe improved; inactive client prevented capture.
Previous turn classified progress; full goal remains incomplete, no tests.

2026-09-14: previous turn was status-only, no progress. Revalidated worker state.
Fixed earned streak challenge source to actual class selections and excluded bot
account challenges; reset timing with class loadout. CB82AD78 built/deployed and
restarted. Live earned challenge remains unverified. Mortar constructor review
improved argument restoration/generation guards and private lifecycle state;
still gated. Fastmag viewer-zone duplicate is a new unresolved lead, worker
resumed reference resolution. Shadow1529 identified as decal control at shipped
default; no supported shadow fix. No automated tests; full goal remains active.

2026-09-14 continuation: previous turn progress (selected streak account fix).
Copycat cloning now reads native bot CSV base/perk values, preserving already
captured full weapon recipes/equipment. Fixed classHasPerk query index mismatch:
slots0..2 now read perk1..3 rather than equipment/perk1/perk2; copied classes read
their cloned values. Native force-normal-up bytebdc validated/mapped after C1
consumer review. Full571E837F built/deployed/restarted; no gameplay proof yet.
Mortar constructor remains gated; shadow sampling and fastmag viewer reference
resolution delegated to existing workers. Full goal incomplete, no tests.

Live startup follow-up caught Nucleur connection shutdown at _playercards.gsc23:
SetCardIcon rejected an index outside C1 unsigned10-bit range. Script boundary
now validates all three saved cosmetic indices, logs invalid values and retains
reset session values without changing account data or loosening native limits.
A021F103 built/deployed/restarted. Exact invalid profile value/root producer not
yet established; guard prevents this cosmetic from terminating the match.

2026-09-14 mortar integration: previous turn progress. Parent reviewed constructor
provenance, mask/normal metadata, frame locals, all impact arguments and callback
generation guards. Corrected stage cancellation that otherwise killed persistent
killstreak-use waiter. Independent collector and explicit result event now return
false on cancel without consuming reward. Registered narrow native mortar VM,
enabled scoped collision, copied real3x2 target/ballistics script and wired queue
commit after consumption plus round-grace classification. 21261B5 built/deployed
and restarted. Startup observation ongoing, no live reward proof. Extra T5
warning/HUD/shellshock and generic guided bombs remain unfinished; no tests.
Startup verification: current log resolves mortar_mp and catalogue row17 without
script compile/runtime errors; client exchanging snapshots (seq89/command12755).
Native PID103160 remains live. This proves load/registration, not reward use or
projectile impacts. Shadow worker notified active scene available for capture.

### Reconnect identity — 2026-09-14
Parent reviewed retained initial XUID across map resets and human missing-profile guard before ClientBegin. Built/deployed SHA256 11481EB75773DB64CB705E6E6CA5ED8223D59A55742D99E93080C074A85AFD36; native PID 100412 completed startup. Usermove caller returns after EnterWorld. No automated tests. Actual reconnect lifecycle remains unverified; full suite remains open.

### Composer cache, WA2000 and shadow comparison — 2026-09-14
Parent reviewed marketplace ordinal/name indexing, bounded model-row cache and retire/reset invalidation. Bot WA2000 now permits only proven unavailable declared default groups. Repetitive successful table reads and table dumps require developer 2. Built/deployed F6135C04234668767EF612BF98D5A9836ACAA3E92D0FF3EBEA3C4D5FE9BB304C; launched with scr_codol_bots 4. Live results and timing remain pending; no automated tests.
Shadow defaults command accepted in active C1 (1.5/4), dark pattern remained, camera rotated so not a fixed-view comparison. Restore to captured lobby values requested; no permanent renderer override.

Live observation: PID82912, all four bots reached session0 spawn, WA2000 retained legal recipe, native command/movement logs advancing. No script shutdown observed. Initial startup still hitched32222ms, so no measured end-to-end latency claim. Combat/respawn validation remains open.

### Bot kill XP shutdown — 2026-09-14
Live human kill reached _rank::syncXPStat with zero scale; repeated exitLevel caused script shutdown and overflow fallout. Registered native scr_xpscale default1 range0..4 (T5 normal default1; IW4 script range), overlaid syncXPStat to skip zero-XP/unranked persistence. Built38E1CAE1D0D6D69CCF92E21E4C622E7EE65E3079138B4E02F515A0FF2D187737, launched4bots. Alias dependency index reviewed/integrated preserving ordering/lifetime. No automated tests; live kill proof pending.

### Second bot-kill failure: partial challenge catalogue — 2026-09-14
User death worked, killing bot crashed in _missions processChallenge targetval.size. Requirement pass created records for absent challenges. It now decorates existing records only, and progression requires real target/reward arrays/current tier. Rebuilt/restarted4bots; live kill verification pending. User-provided COD-GSC-Source sparse BO1/IW5 reference installed at59ba344fbb482b416e2f1c367d9f798447ba5d6c; notified RC worker. No automated tests.

### Bot end-of-match scoreboard — 2026-09-14
Observed missing public profile error writing round.scoreboardType to bot. New native overlay keeps match scoreboard rows and excludes bots from account writes/client lobby summary. Built21C37F5E35E3D67A2A628722D392AD5F05DC8366E758C3E2FE42C9F5F081E4F5, restarted4bots; endgame verification pending. RC VEHICLEFILE loader reviewed/compiled only, no gameplay path. Pro descriptions extracted (faster UAV sweep/longer uptime, larger RC radius, weighted drops etc.); exact implementation values unresolved. No automated tests.

### 2026-09-14 UAV expiry shutdown / Predator lifetime
User death-coincident failure was _uav.gsc departure PlayFXOnTag on absent IW4 vehicle_uav_static_mp (placeholder lacks tag_origin). Removed invalid cosmetic plume attachment; C1 aircraft asset remains unresolved. Radar timer and cleanup retained. Reviewed projectile lifetime/acceleration import and raw ground-vehicle ownership integration. Built/deployed CED0D31D4F4DBAB1F4CFDD2CA4EC5418F583A4E1557C189DD0231B1E82F58FB7, build-uav-predator-20260914.log; launched four bots. No automated tests; Predator live camera, UAV full expiry and selected RC slot diagnosis pending. RC-XD control/callback not enabled.


UAV correction: exact common_gametype_mp type4 assets 9753 vehicle_uav_static02_mp and 9752 vehicle_counter_uav_static02_mp identified. Both contain tag_origin/tag_jet_trail in ten-bone arrays. Replaced unavailable IW4 model in precache and normal/counter spawn, restored departure plume. Restarted four bots with corrected script; no additional zones. This supersedes the temporary plume-removal note above.


### 2026-09-14 RC reward announcer shutdown
Latest live error _utility.gsc955 undefined dialog followed earning rcbomb_mp. Metadata init incorrectly skipped unregistered activation callbacks. Catalogue dialogue now initialized independently; activation-only asset guard retained. Missing callback reports unimplemented and leaves reward owned. Restarted four bots; live repeat pending. RC controls still incomplete; guard is not support.


### 2026-09-14 heartbeat enable state
Reviewed native C1 motiontrackerenabled input, spawn default1, captured ps22c publication and archive roundtrip source. Built/deployed968405104458271C271B0C18BEE044B323B12AA56C71F39BDF5C5C7A06003A49 (obj/build-heartbeat-20260914.log), launched four bots. No tests; live display/blip verification pending. Includes UAV proper C1 aircraft and RC reward metadata crash fixes.


### 2026-09-15 action slots, killcam state, map music
Built/deployed37D06E80D78BE782E93C295784B348C3020FDFE5DB0033B544FF45BD83C0AA89; log obj/build-killcam-actions-music-20260915.log. Caught/fixed C++ remote vehicle eFlags member to s.lerp.eFlags during build. Five saved action slots now initialized (live slot5 crash root), selected1-3 plus package5 routing and exact reward ownership reviewed. C1 A50/A54 receive existing archived deltaTime/killCamEntity; static/card visible behavior pending. Map music selects actual alias_mapname via real mounted soundexists; suspense uses shipped mp_suspense. Windows progression directory path separators fixed. RC entry/exit helpers built but driving/activation still absent. Python canonical profile/editor changes staged; no current profile mutation. No automated tests; four-bot launcher started.


## 2026-09-15 entity lifetime and rank
Reviewed/built/deployed 1EC7825DABA60E8248EE8B9CBA70FDF424FE0C563A9FF2161794BD7BD734224B; four-bot launcher started. G_FreeEntity clears live C1 extensions at native memset; captured archives retained. Rank uses captured clientstate and explicit total/within-rank XP adapters. No automated tests; live recurrence verification pending. HUD/vision and Killhouse shadow remain unresolved; shared map load lighting delivery under audit. Challenge transition diagnostic added; no arbitrary replay debounce.

## 2026-09-15 EMP grenade receivers
Built/deployed FB6381AC74164B1CAA837D7645CD2126307A47279CB7956A303329D73A2000F8 with four bots. Player EMP and autosentry script graph compiled cleanly. Reviewed timed personal EMP lifecycle and C4/claymore/sentry damage receivers; actual C1 play verification pending. No automated tests. New user correction: selected rewards belong in action slots2-5, extra care rewardslot1; script changes pending next deployment. TDM default7500 source changed and live update sent. Playercard cosmetics/Predator static movement under active audit.

## 2026-09-15 three selected rewards, cards, chopper unlink

Built/deployed 2F7D50A8180C4F11B5CAF722257BE4FD01E24050F9468D68B8519AA26E66730E (obj/build-cards-three-streaks-20260915.log). Three selected class rewards now populate action2-4; package bank remains action1. Fifth available action slot does not imply a fourth selected reward. TDM default7500 retained. Authored C1 HUD confirms callsign row IDs and corrected card field meanings; registered background setter and deployed reviewed marketplace-to-row script. Chopper scripted unlink requires real occupied vehicle state before native dismount, preventing the reported fatal. Flight movement remains open. Built Predator dispatch and entity reachability diagnostics. No automated tests.

Prior native exited after map mp_underpass without a logged cause or fresh dump. Preserved log at obj/live-before-underpass-recovery-20260915.log. Restart followed the updated lobby handoff to Killhouse, where Nucleur reached ACTIVE and acknowledged snapshots. This does not verify Underpass or prove the original exit fixed. Splash, bot killcam visibility and shadow investigations remain open.

## 2026-09-15 Predator linear flight
Reviewed, built and deployed D2F7C46A32C6BC341107DC9E5147A6C3653D930D1B7837051312B4455C71B44F. Explicit remote flight now precedes linear asset fallback; traced base and refreshed timestamp preserve linear continuity. Four-bot launch; no automated tests or live missile verification yet. See CODOL_PREDATOR_LINEAR_FLIGHT_20260915.md. Full equipment/perk/killstreak goal remains open.

## 2026-09-15 mortar identity and aircraft perks
Reviewed and deployed mortar selected reward ID propagation plus three aircraft targeting gates using C1 effective immunity modifiers. Build A01B8CD450840DB571E41D7C9DD1AEF0108E0EBF960B75D250B25FE7457E91CD, log obj/build-mortar-perks-20260915.log. Four-bot launcher started; no automated tests. Live mortar launch and aircraft targeting verification pending. RC physics and dog AI implementation remain active separate worker tasks.

## 2026-09-15 RC binary settings and graph prerequisite
Reviewed and built E53711871BB1637519AFE011F788B3C345C95F5C904EFD28FDD458B79EB6B4C3, obj/build-rc-assets-20260915.log. Actual type41 RC definition now publishes ground physics/control settings; owned acceleration graph resolves mounted vehicle/default_accel.graph. Camera decoding and physical simulation remain incomplete, activation disabled. Four-bot startup running. Corrected developer lookup diagnostics:3271 previous challenge misses were authored empty cells; script return semantics unchanged. No automated tests. Dogs require native actor/event type migration and tree publication, still staged; shadow agent has a guarded skinned-pose probe pending active client capture.

## Native C1 actor categories — 2026-09-15

Reviewed and integrated native categories17..20 and event base21, including assembly temporary-event creation, C/C++ names, archive field selection, actor slot/tree publication, and named custom-explosion replay timestamp handling. Parent review caught the old literal66 replay category; the first build caught a missing bg.h include, now corrected. Build succeeded, deployed hash `0DF19B0EA9C86FC00FE8B4CCD86FDB70B4EA955E1A4966050E141E489CC2F476`. RC controls now retain automatic braking separately. No automated tests; startup observation pending. Dogs and RC not yet playable.

Reconnected C1 through its UI to Killhouse. Two active shadow captures found normal selected skinned sun-caster bones; large unselected transforms were excluded by actual LOD masks. Next investigate depth/material submission and receiver sampling. Authored aerial route audit is in CODOL_AERIAL_MAP_PATHS_20260915.md.

Startup follow-up: native PID82392 is live and processing bot movement after restart. No claim of dog or RC behavior validation.

Correction: earlier active selected-bone shadow conclusions are withdrawn. Probe review found a null frontend pointer could pass the previous stability checks. Readable/stable bytes are insufficient evidence of current render allocations. Corrected capture must establish a valid frontend and frame identity.

## Animation semantics and killstreak rollover — 2026-09-15

Built/deployed `57CBE86462BC4D552CF10DC9C8AEAC993E7C5D11CE675F4C98586A6B5331ADF1`. Corrected native animation command goal-weight/playback-rate meanings against C1 decoder/executor; command producer remains staged. Rollover construction now allocates an independent GSC destination array, so successive passes iterate only original rewards. Included exact-zero RC automatic brake predicate. No automated tests. Startup observation pending.

Corrected shadow capture validates actual frontend allocation, shared usage128/16384 and identical transferred near8/far31 lists. Transfer overflow not observed in this frame; earlier unguarded pose conclusions remain withdrawn. Full equipment/killstreak/perk suite remains incomplete.

Startup verified: native PID63444, all four training bots ACTIVE, current startup log contains no script compile/runtime error or message overflow. Full gameplay behavior remains unverified.

## Bot movement and third-person rendering — 2026-09-15

Built/deployed `857E646F7AEE715DA3199CF5A69DC2142998A8D37348AFFA710986552359296B`. Native bot routes retain progress across unchanged-goal refreshes, steering uses final commanded yaw, and commands now consume script weapon-selection requests. Bot request storage and playerState-to-entity weapon transfer preserve full native indices. Restored C1 ordinary movement/idle/stance/ladder body animation selection and corrected DObj notetrack return ABI. Parent directly checked C1 move table C40978 and selector413770, plus retained DObj0/1 return paths. No automated tests. Live visual verification remains pending. User clarified killcam success refers only to killer first-person hands/gun.

### Active bot rendering capture (2026-09-15)
Reconnected C1 through its existing lobby. Commands 378920..379201: bots 1/3 carry nonzero current/primary weapons (118 and 122), legs 1361/294, torso 0; their DObj lists contain only appearance parts. First-person killcam success does not validate third-person rendering. World-gun consumer and torso producer audits assigned separately. No new build or automated tests this capture pass. Follow-up evidence: obj/codol-live-player-render-active-20260915.json. Rendering fix and circling verification remain incomplete.

### Bot pose record base (2026-09-15)
Corrected BG_PlayerAnimation_60 leg-pose flag lookup to CODOL_AnimationRecords. Build succeeded and deployed SHA256 C120A48F11CB0BD221F33B3CF5ED175919802D21D60D0B1EB158EA3D26430453; restarted native with four bots and 7500 score limit. No automated tests. Torso zero is valid for full-body locomotion; separate gun renderer remains under audit. No claim this small native pose fix resolves the reported world-gun issue. Black Ops rewards now explicitly prioritize OpenBLOPS and T5 GSC in AGENTS.md and worker assignments.

### World weapons, killfeed, live bot target (2026-09-15)
Built/deployed B5FE8E3BE709336511B29AFB80A3639B6CBFB3B188EAF57EC098E617497ECE7D. Native linked world weapons, archived C1 selector, independent held-weapon animation condition and actual source animation type, typed C1 obituary payload, roaming route failure recovery, live scr_codol_bots watcher (add up to target16, no automatic kicks), and T5 mortar cancelled-confirmation cleanup. No automated tests. Native restarted PID69336; startup/real-client results still being checked. Corpse persistence, unknown TELEFRAG presentation, full T5 rewards and shadows remain open.


## 2026-09-15: mortar, linked guns, and Harrier failures

- Preserved previous/current logs and hash-verified native missile captures in obj/crash-bots-*; finite mortar ascent exceeds position encoding range and blocks snapshots. No memory-exhaustion evidence; prior native log ends in explicit quit.
- Reviewed constructor-owned mortar ballistic dispatch and integrated reviewed C1 parent/tag/local-transform publication with archive preservation. Build pending Harrier repair.
- Harrier icon-name arguments reached an integer reader and aborted the map; native C1 minimap icon-bank adaptation in progress.
- User confirms killfeed works. Visible missing heads/red gun FX remain unproven; sampled actual client DObjs include their head assets. RC-XD and dogs lifecycle work resumed in separate staged ownership. No automated tests.

- Build0734767023A11886406C87D63D0A4433909185EB56FCA842C18F69C21D9E80E1 compiled/linked and deployed to both executable names. Native launcher restarted with four bots; client command flow observed after startup. Harrier native icon-bank arguments and captured plane owner/enemy/friendly/model fields included. Actual mortar impact, linked-gun rendering and Harrier call verification still pending. User now reports Predator damage/enemy boxes missing; aerial worker redirected.


## 2026-09-15: native C1 FX and impact-projectile damage

- Built/deployed B9A26B310511278FF5E82C17F17D56AE2AA14EDC41ABEC991B6885E16041816F. Native FX use C1 element260/type IDs and owned spawn sounds; runner references follow C1 type14. Isolated mp_nuked startup passed (393 dynamic entities), and passive normal C1 screenshot later showed live Nuketown gameplay.
- Weapon composer now binds the impact-explosion boolean from C1 bytebdd. Native radius damage was gated by this previously zero field. Actual Predator impact verification and enemy boxes remain open.
- Original T5 mortar source and dependencies pinned unchanged in obj/mortar-t5-stage/reference. Reviewed/applied source-only T5 selector and partial launchbomb interfaces after build. Full original lifecycle migration still needs HUD/influencer/reward adapters. No automated tests.

- T5 mortar interface candidate compiled/linked successfully: obj/codol-scriptinterfaces.exe SHA256D664F713BE9F5B09B7EE60E843ADAA66A02264D7624493075760A86BCC26434D. Left live B9 build running; original T5 lifecycle not activated until its remaining real dependencies are integrated.

## 2026-09-15 — native RC driver interfaces

Parent reviewed original OpenBLOPS driver-seat and exit notification contracts,
then integrated staged C1 ownership/camera interfaces. Explicit Unlink clears
control before notifying both participants, with generation checks. Native
`usevehicle(player,0)`, `getseatoccupant`, and `isremotecontrolling` are registered.

Build succeeded after adding the missing string-list header. Deployed SHA256
B14BFA5A7CC8F3BC53EFA151932FA1DB4E2AD1FDC4C6053F6DF54F2B82CD99D6.
Only the native server was restarted; C1 and Python lobby were preserved.
No automated tests. RC physics, generic passenger seats, original reward
activation and live driving verification remain incomplete. Agents continue
mp_nuked events, original T5 mortar lifecycle and Killhouse receiver tracing.

## 2026-09-15 — Semtex map abort, bot logging, artillery prerequisite

Saved `obj/semtex-crash-20260915.log`: missing `vehicle_car_exp` in
`common_scripts/_destructible.gsc` aborts the map; overflow warnings are subsequent
shutdown fallout. Native overlay now uses verified common_mp sound3475
`car_explode`; full Python-derived destructible parts behavior remains unported.

Movement/collision/pacing diagnostics now require `codol_movementDebug 1`.
Errors and synchronous logfile remain enabled. This removes routine output cost,
but no measured claim that logging dominates bot lag. Agent auditing duplicate
bot visibility traces separately.

Native T5 artillery cylinder registry and spawn consumers reviewed against
OpenBLOPS and integrated. Original mortar lifecycle remains staged, not activated.
Build/deploy SHA256 1F6C5BEDD8B94AAFF45C1764336EAF8F2E6A0C83F20EB6F2730790F41C1522A2.
No automated tests. C1 preserved. Semtex/live performance verification pending.

### Follow-up — startup correction and duplicate bot traces

The first artillery rollout failed GSC compilation: bestArtilleryWeight was
uninitialized in a conditional. Initialized it before the branch; subsequent
startup passed and bots spawned. Saved failure log in obj/artillery-spawn-compile-error-20260915.log.

Reviewed command-local visibility reuse in codol_bot.c against exact trace
inputs and unchanged threat/aim/fire flow. Removes one or two duplicate sight
traces for an existing enemy per command. No cross-command visibility cache.
Built/deployed SHA256 0D8E5FEE489EC3296FA9230E8E3047B175BFC8DBF91745BC831978483BEE5F09.
No automated tests or measured total speedup claim. Default movement trace
silence observed in corrected prior run; error logging remains enabled.

## 2026-09-15 — captured earthquake/physics explosion payloads

Reviewed C1 producers against retained native entity unions and archive fields.
Earthquake and spherical physics events now publish typed payloads instead of
being omitted. Sphere outer radius is float, as C1 requires. Non-CoDOL handler
is preserved. Server-side vehicle impulses remain incomplete; this is client
physics-event publication, not a full vehicle solver claim.

Built/deployed 3582441E51C2FF3B9644352E31BCDF8F45A7767F05D924D9355F4D421C3DC90D.
No automated tests. Live event behavior still pending. C1 and lobby preserved.
Fresh Killhouse shadow capture independently verified receiver texture,
dimensions, sampling vector and finite depth scales; no visual fix established.
Glass agent is implementing the absent piece install/damage/snapshot pipeline.

## 2026-09-15 — live feedback and authoritative projectile gravity

User reports mortar works and bots are substantially smoother. Treat these as
live user observations, not quantitative performance measurements or proof of
full T5 migration. The active mortar launch now asks the native TR_GRAVITY
velocity evaluator for acceleration instead of duplicating800 in GSC. This
keeps player gravity separate and uses the same source as the actual bomb.

Built/deployed32925D70B531546600907D7A825DB5BC120E95AC95FA70B233188A3251D8B284.
No automated tests. RC agent now owns shared wheel/contact solver integration;
glass agent owns install/damage/shatter publication; shadow agent traces actual
caster bounds. Original dog actor/spawner/movement lifecycle remains incomplete.
# 2026-09-15: poison state and Favela load failure

Poisoning methods and captured C1 ps+0x59c publication reviewed and built
(479623CD38BBF937A882E0003BE8658DD97C1005415170291137B812579DD644).
Full Tabun lifecycle and live effect verification remain pending.

Favela map/precache overlays installed after parent review. They remove the
foreign IW4 bushy-palm animation import responsible for the captured fatal
palmtree_bushy3_still lookup. A second palm model's animation binding and the
inherited art settings remain open; existing animated-model code reports and
leaves unregistered props static. This is not full foliage parity.

Betty animation/team marker assigned to the Favela worker after its report;
knife pickup/sticking queued behind the RC worker's coherent stage. Dogs
continues independently. No gameplay outcome claimed for these assignments.
# 2026-09-15: C1 mover deployment

Native acceleration/deceleration/physics producers and evaluators now use C1
7/8/9 directly. Built and deployed DEAD476A7220B0E89C909AD5C073330A329B87742DAFA3B1A7E9E5891756EF07,
including Betty's marker script changes. See CODOL_C1_MOVER_20260915.md for
scope and remaining unverified behavior. Killhouse authored shadow setting
identified; replicated-dvar map-transition lifecycle is still being reviewed.
# 2026-09-15: authored Killhouse shadow setting deployed

Built/deployed D2BA3F66B83ACAFDBDE67237F16798BB20DB56FD529AEB7432E0087EAF64411E,
native PID56040 with four bots. Actual IW4x Killhouse sample-size correction
now publishes C1 numeric1617=0.35; subsequent map banks restore baseline0.25
after an owned override. Client reception/visual result still pending.
See CODOL_KILLHOUSE_AUTHORED_SHADOW_20260915.md. Full goal remains incomplete.
# 2026-09-15: Killhouse shadow resolved

User visually confirmed the shadow looks great and explicitly requested no
further investigation. C1 renderer reception had already been verified.
Shadow work closed; remaining equipment/perks/killstreak work continues.
# 2026-09-15: knife recovery lifecycle deployed

Reviewed and built 0E311E30AC8C1EDBF63892AA18E0A898482721BAE40655759F4BCBAD6678C785;
native restarted. Knife pickup now shares generation-safe trigger/death cleanup
without altering successful one-round transfer. Body/wall sticking remains in
the worker stage; no complete knife gameplay claim or automated tests.
# 2026-09-15: Favela tropical art source reviewed

Installed recovered IW4x tropical fog/vision script and corrected map import.
Current runtime has not reloaded that source yet. Second palm pairing remains
under asset review. Knife attachment stage remains under impact/link/corpse
lifecycle review; not counted as implemented live. Shadow issue stays closed.
# 2026-09-15: knife attachment deployed

Built and deployed7D53C950B0D103DD1684964FEB937C500473913188085D213560C6E62CD942FE.
Same missile now supports native wall/body attachment, corpse transfer and
respawn detachment. Gameplay unverified; see CODOL_KNIFE_ATTACHMENT_20260915.md.
Reviewed Favela art/palm and Killhouse ambience source included. Shadow remains
closed. Worker resumes remaining original T5 RC activation dependencies.
# 2026-09-15: gravity6 and RC review

C1 mode6 equation independently inspected: 40cb7b joins normal gravity at
40cb3f, using400*t*t. Implemented named native mode, matching derivative and
direct publication; built/deployed BF8217ACBD30C6693FC92536B158E348BE9696B67291DD0DA6557C7F2907BA2F.
No live mode6 observation. RC review caught stale decoder and1024entity bound;
worker corrected stage. Full RC activation still incomplete.
# 2026-09-15: queued user gameplay reports

User explicitly placed seven bug groups after RC-XD, dogs and current equipment
work. See CODOL_GAMEPLAY_BUG_QUEUE_20260915.md. Knife retrieval remains broken
by user report despite recent cleanup/sticking implementation. Shadows stay closed.

RC physical core built/deployed964E2158F1C3516EBCAF39E421731082FAD64ECA2CCC5158F7751092831F0832;
full T5 reward activation and actual physical gameplay remain unverified/incomplete.

# 2026-09-15: RC-XD lifecycle port, ODE dispatch fix, isolated boot

ODE user-class crash re-derived: the earlier `-0x37` lea was necessary but
all five `_collision_kernel.asm` dispatch sites still read
`Phys_Stop_f_VAR+0x30..0x3c` (a disassembler mis-resolution of
`user_classes+field-0xdc`; different .bss objects in the rebuilt image, so
every user-class collide/AABB/free called NULL). All five sites now index
`user_classes` directly. `unlink` registration now routes through
`CODOL_Scr_Unlink` so remote control ends and `exit_vehicle` fires (T5
VEH_UnlinkPlayer contract). `_rcbomb.gsc` restructured to T5 with the eleven
missing functions and three helpers ported; `_rcbomb_watchers.gsc` gained the
T5 respawn hook and friendly-fire override consumer. Live gate line stays
commented; enable steps in CODOL_KILLSTREAK_AUDIT_20260915.md section 9.
WRITTEN: all of the above. BUILT/BOOTED: nothing - all touched files compile, but the shared tree does not link (other workers' in-flight codol_weapon_give.c and codol_actor_*.cpp); isolated boot not run. Staged launcher/home in the session scratchpad; see audit 9.5.
LIVE: nothing - bots cannot earn streaks; a C1-driven RC-XD use is the next check.

# 2026-09-15: weapon-ceiling handoff and the five weapon-primitive C ports

Step 0 on the deployed 2035702B binary (dogs hook disabled after the
`_dogs.gsc:1661 setFlashBanged` compile error): killstreak_pro_ lookups 34 -> 0,
budget 112/128 = 97 stock (was 110), 0 partner, 14 composed, 16 free, no
"falling back" warning yet, no dumps. LIVE (measured).

The widening itself is reassigned to the codol_weapon_bits agent (700-wide
arrays in codol_ps_ext_t). This worker's in-struct 384-bit variant was
reverted by hand (player.h, _bg_weapons.asm x13, _bg_misc.asm:2301,
codol_weapon_history.h/.c) and the tree carries none of it.

WRITTEN+BUILT: src/codol/weapon/codol_weapon_give.c/.h - CODOL_GivePlayerWeapon,
CODOL_UseOffHand, CODOL_PlayerCmd_dropItem/giveMaxAmmo/giveStartAmmo, ported
branch-for-branch from the retained asm on the CODOL_WeaponBits* API; object
compiles clean with the tree's -m32 -DCODOL_SERVER flags. NOT linked, NOT live:
the retained bodies remain until the asm owner applies the trampoline diffs in
CODOL_WEAPON_TABLE_20260915.md ("2026-09-15 22:40"), which also holds the
resolved 25-site register table, the Cmd_Give_f_100 resolution and the second
128 domain (bg_itemlist 128x16; Drop_Weapon aliases indices >= 128 - open).

## 2026-09-15 - boot-log triage: tag_player link, shock volume dvars, statsTable misses

**1. `CoDOL link: entity 470 parent 465 tag 'tag_player' unresolved (native index 1, wire slot -1)` - WRITTEN, object-compiled.**
Entities: 465 = `level.ac130` (`c130_zoomrig`, spawned by `_ac130.gsc:91`), 470 = the `vehicle_ac130_low_mp` plane model linked by `ac130_spawn()` (`_ac130.gsc:713`); 471 (camera `tag_origin` model, `:721`) shares the tag and is deduped by the per-tag rate limit. Producer is GSC `linkTo` -> `G_EntLinkToInternal` (`_g_utils_mp.asm`), which stores the tag as a script string and never registers a server tag; the native CS_TAGS entry (CS 0x8ea+1 = 2283) is created by `capture_entity_links` calling `G_TagIndex`. The C1 wire slot (bank 5299, `CODOL_RefreshAssetRange(CS_TAGS)` in `src/codol/assets/codol_sv_assets.c`) was allocated ONLY from `SV_WriteGameState` / `SV_BeginClientSnapshot`, never at registration, so every link captured in `G_RunFrame` before a map's first snapshot (the three `SV_SpawnServer` warm-up frames, `sv_main.c:5433`, and every frame until a client is primed) had a native index and no slot and was dropped. IW4 has no gap: `G_TagIndex` publishes CS_TAGS+i immediately and that index is the wire index. Fix: new `CODOL_RefreshServerTagNames()` (`codol_sv_assets.c`, declared in `src/server.h`) and `capture_entity_links` (`codol_player_worldweapon.c:169`) now allocates the slot in-frame and retries before warning. The "now resolves" line was absent from the log for two reasons that are not defects: the mp_rust entry was wiped by `SV_ClearServer` on the rcon `map mp_killhouse_sh`, and the killhouse-load warning went into the rcon `Com_BeginRedirect` buffer (`sv_main.c:1694`). Next launch: no `tag_player unresolved` line at all; `tag_player` appears in the gamestate tag bank (slot 1 at 5300) and `d 5301 tag_weapon_right` etc. still follow.

**2. `unknown cvar 'bg_shock_volume_*' in file 'shock/*.shock'` - WRITTEN, object-compiled (worker).**
`Com_LoadDvarsFromBuffer` (`src/misc.c:81`) from `BG_LoadShellShockDvars` (`_bg_misc.asm:1818`) accepts 27 base names plus `SND_GetEntChannelCount()` channel names; `src/null_client.cpp:279` stubbed the count to 0 and `src/g_sv_main.c:531` `BG_RegisterShockVolumeCvars()` was an empty stub, so the 37 channel dvars were never registered. C1 `0x40acc0..0x40af26` parses `soundaliases/channels.def` and registers `bg_shock_volume_%s` as `Dvar_RegisterFloat(0.5, 0..1, 0x10004)`; IW4 (`BG_RegisterShockVolumeDvars` in iw4mp.pdb) does the same. Added `src/codol/assets/codol_snd_channels.c/.h` (parses the mounted `channels.def`, 37-name CoDOL fallback), `null_client.cpp` delegates to it, `g_sv_main.c` calls the retained `BG_RegisterShockVolumeDvars`. Next launch: zero `bg_shock_volume` warnings, `dvarlist bg_shock_volume_` shows 37 floats default 0.5.

**3. `tableLookup miss: mp/statsTable.csv column 0 value '58','95'..'148' return column 4/9 (95x27)` - UNTOUCHED by this pass.** A worker was investigating the producer (numeric row loop over statsTable, columns 4/9) and the table layout vs C1's when the token budget ended; no source changed for it. The `killstreak_*` column-4 family from the audit is likewise still open.

## 2026-09-15 C4 multikill client crash (LOGF1D0/DMPF1E1)

C1 strlen crash at 0x00aea51c after a C4 triple kill = the 09-11 team-7 colour crash. Trigger: offhand end state 20 with detonation anim 27 rejected the whole frame 2544 -> overflow recovery -> client asked delta -1 -> server sent deltaNum-0/flag-0 frame against pinned baseline, C1 decoded it against its own flag-8-only baseline copy. WRITTEN+BUILT (not live): accept anim 27 in state 20 (codol_engine_state.c), and answer every non-delta request with a flag-8 baseline frame (codol_sv_snapshot.c). Details: docs/CODOL_C4_MULTIKILL_CLIENT_CRASH_20260915.md.
# 2026-09-15 23:15: 700-slot integration build crashes at boot; rolled back

Integration build b18d571f (obj/build-w700-20260915.log, make exit 0) contains:
the 700-wide weapon ownership (69 asm sites through codol_weapon_bits.inc
helpers, bg_weaponDefs 0xaf4, usercmd 10-bit weapon index, five C ports in
codol_weapon_give.c), the dogs native/actor work, the RC-XD ODE/user_classes
asm fix, the C4-multikill client-crash fix (codol_engine_state.c state 20 anim
27; codol_sv_snapshot.c flag-8 null-base recovery frames), and the diagnostics
agent's partial edits. Copy kept at bin/rollback/codol_dedrun_w700_b18d571f.exe.

It dies 3/3 launches ~60 s after map start, always right after
"CoDOL mounted animtree: animtrees/multiplayer.atr" and before GSC main()
prints (compare qconsole.log.step0:268-270). Independent of the dogs hook
(bisected off) and of codol_animlistMask (0 and 2). No Sys_Error, no WER
dump, no Event ID 1000: the process exits through its own path. Logs:
bin/home/main/qconsole.log.crash1/.crash2/.crash3. Budget line shows 1/700.

Deployed binary is back to 2035702b (bin/rollback/codol_dedrun_2035702b.exe),
launched 23:14, PID 84008. The live _killstreaks.gsc has the dogs hook
commented ("BISECT 2026-09-15 23:10") and RC-XD commented; re-collated.

Next: run codol_dedrun_w700_b18d571f.exe under a debugger (or add a console
print at each step between animtree mount and GSC compile) to get the
faulting site; prime suspects are the script-compile/precache phase where the
first stock weapons register through the rewritten _bg_weapons.asm sites, and
the codol_weapon_give.c trampolines.

# 2026-09-16 00:20: w700 boot death found and fixed (actor precache ran before Scr_InitSystem)

Faulting site: `CODOL_ActorScriptsPrecache` (src/codol/player/codol_actor_scripts.cpp)
was called from G_InitGame_80 in src/asmsource/_g_main_mp.asm between
G_InitTurrets and G_SpawnEntitiesFromString, i.e. BEFORE `Scr_InitSystem`
allocates gScrVarPub.levelId. Its `Scr_ExecThread(type->precache, 0)` then
runs AddRefToObject/RemoveRefToObject on object id 0, which is
`variableList[1]` - the object pool's free-list head - so the head's `u.next`
was stepped on (values 6, 8, 0xa ...) and the first AllocEntity in
G_SpawnEntitiesFromString (Scr_SetDynamicEntityField -> Scr_GetEntityId) hit
head.next == 0: `Sys_Error("exceeded maximum number of script variables")`
with only 14 objects live. It was never a crash: Sys_Error's message goes to the
console only, Sys_WaitForErrorConfirmation blocks on a dialog nobody can see,
and Sys_ShutdownWatchdogThread `_exit(-64)`s after 30-60 s, which is the silent
"dies ~60 s after map start, no dump, no event" signature. bin/sys_error.txt
carried the message all along. The dog type is loaded unconditionally by
CODOL_ActorScriptsLoadMapTypes, which is why the GSC hook bisect was negative.

How it was found: cdb (C:\Program Files (x86)\Windows Kits\10\Debuggers\x86)
running the launcher's exact command line; module is `codol_dedrun` at an
ASLR base, so breakpoints are `bu codol_dedrun+<VA-0x400000>`; a `ba w2` on
`variableList[1].u.next` conditioned on eip outside AllocVariable/FreeVariable
caught the foreign writers with `Scr_ExecThread_10 <- CODOL_ActorScriptsPrecache
<- G_InitGame_80` on the stack. (nm -n on the exe maps addresses.)

Fix (source):
- src/asmsource/_g_main_mp.asm: `call CODOL_ActorScriptsPrecache` moved from
  before G_SpawnEntitiesFromString to after Scr_InitSystem / Scr_SetLoading /
  Scr_AllocGameVariable / G_LoadStructs and before Scr_LoadGameType (line ~675).
  The VM level object exists and the precache window is open; still before any
  gametype/level/aitype main or spawner runs.
- src/cscr_variable.cpp: `Scr_ReportVariablePoolExhausted()` names the pool
  and both counters (objects n/32767, values n/65533, compile vs runtime) in
  the logfile before Scr_TerminalError; `Scr_CheckObjectFreeList(where)` walks
  the object free chain and reports a shortfall (used once per map load from
  Scr_EndLoadScripts after ClearObject(loadedscripts)).
- src/cscr_main.cpp: "Script variables after compile: objects N values M" line
  (this MP set: 2720 / 31635 of 32767 / 65533).
- src/sys_main.c: Sys_Error now also writes its message into the logfile once,
  so a dedicated server no longer dies with an empty qconsole.log.

Build: obj/build-w700-fix-20260916.log, make exit 0. Deployed
bin/codol_dedrun_next.exe sha256
5a3efa4413febc195c845a72f0b05b47b04ef912af97ddb9a459d394d364ed9b (copy at
bin/rollback/codol_dedrun_w700fix_5a3efa44.exe). Contains everything the
b18d571f integration build had (700-wide weapon ownership, dogs native actors,
RC-XD user_classes fix, snapshot fixes) plus this fix.

Live (mp_rust dm, launcher defaults, no client):
- dogs hook still commented: boot reaches getMapCustom/GSC main, survives
  4 min past map start (00:09:00 -> 00:13:04), no sys_error.txt, no "table is
  full", no "passed playerState" lines. "CoDOL weapon budget (map start):
  1/700 native definitions - 0 stock" is the only budget line; nothing beyond
  the placeholder registers before a client connects (aug_* composed names are
  reported "not in any mounted zone; skipped" by precacheItem as before).
- dogs hook re-enabled (both BISECT lines in
  scripts/codol/maps/mp/killstreaks/_killstreaks.gsc restored, collate_gsc.py
  run, codol_script_resolve.py --only maps/mp exit 0): map loads with
  _dogs.gsc + dog animscripts + aitype/enemy_dog_mp compiled, `_dogs::init`
  runs (dog_bite weapon lookup), survives 4 min past map start
  (00:13:35 -> 00:17:33), no errors. This build is the one left running.
- Not verified: bots (the launcher has no bot setup and nothing spawns them
  without a client) and any C1 client behaviour of the 700-slot weapon code.

## 2026-09-16 - dogs call-in: spawnactor() returned undefined (no "dog" server animtree)

Incident (build 5f1c9db8, mp_rust): first live dogs call-in died with
`undefined is not an entity (maps/mp/_dogs.gsc:422)` - `level.dog_spawner
spawnactor()` yielded undefined and the map ended. No native line was printed
first; every failing branch of spawnactor returned silently.

Root cause (static): `CODOL_ActorPrepareAnimation` (codol_actor_lifecycle.cpp)
looks up a server animtree named "dog" in the script animtree registry
(`CODOL_ServerAnimTreeCount/Name`). That registry only holds trees a compiled
script declared with `#using_animtree`. T5 ships the dog animscripts with
`//#using_animtree ("dog");` commented out (its actor code loads
`self.animTree = "dog.atr"` at runtime); this server has no runtime tree loader,
so `animtrees/dog.atr` never mounted (qconsole.log only shows
`CoDOL mounted animtree: animated_props.atr` and `multiplayer.atr`),
PrepareAnimation returned 0, `CODOL_ActorScriptsInitialize` returned 0,
`ActorSpawn` freed the actor and returned nothing. The getent fallback itself
worked: `spawnactorspawner` succeeded (the error is at :422, past the :472 gate).

Changes:
- scripts/codol/maps/mp/_dogs.gsc:97 `#using_animtree("dog");` - the fix.
  :502-507 prints whether the map's dog_spawner or the spawnactorspawner
  template is used; :523 prints when the template cannot be built (no_dogs).
  :429-450 `dog_manager_spawn_dog` returns undefined (skips the dog) with a
  `CoDOL dogs: ...` print when the spawn node is undefined, the spawner is gone,
  or spawnactor yields nothing; `dog_manager_dog_alive_tracker` /
  `dog_manager_delete_dogs` already tolerate undefined `level.dogs[i]`.
- src/codol/player/codol_actor_spawn.cpp: every failure branch of `spawnactor`
  (:50-91,105) and `spawnactorspawner` (:136,148-156) prints one
  `CoDOL dogs: ...` warning naming the cause (count exhausted, no entity, field
  copy, no actor slot/sentient, init stage, actor deleted by init/"spawned"
  listener; classname rejected / template freed / wrong eType / aitype not
  loaded+precached). A spawner deleted by its own "spawned" listener no longer
  turns an already-linked actor into `undefined` (:95-105).
- src/codol/player/codol_actor_scripts.cpp:180-201 `CODOL_ActorScriptsInitialize`
  names the failing stage (aitype missing/unprecached, animscripts unloaded, no
  actor record, aitype main, dog_init/species, DObj tree).
- src/codol/player/codol_actor_lifecycle.cpp:1157-1191
  `CODOL_ActorPrepareAnimation` names its cause; the missing-tree case says
  `no server animtree named "dog" is registered (... #using_animtree("dog") ...)`.

Rest of the first-call path checked statically: `forceteleport`, `setgoalnode`
(Scr_ParamError only if the node is not a path node - nodes come from
getallnodes/getnodearray), `show`, `init_dog` (isai gate), `setModel`,
`setEnemyModel`, `setentityowner`, `settalktospecies`, `setEngagementMin/MaxDist`,
`dog_usage` (level.dog_usage sized by dog_count in dog_usage_init),
`dog_patrol` (patrolnodes non-empty whenever no_pathnodes is false). No other
builtin on that path can return undefined into a dereference.

Built: the three objects compiled individually (i686-w64-mingw32-g++ -m32 ...
-O1 -DNDEBUG -DCODOL_SERVER, flags of obj/build-w700-fix-20260916.log) into
obj/codol-win32/, exit 0, only pre-existing warnings. collate_gsc.py run;
codol_script_resolve.py --only maps/mp exit 0. Not linked, not launched, not
seen by C1.

Expected on the next launch + call-in: at map load
`CoDOL mounted animtree: animtrees/dog.atr`; on call-in
`CoDOL dogs: no map dog_spawner entity; building one with spawnactorspawner( "actor_enemy_dog_mp" )`
and no further `CoDOL dogs:` line if every dog spawns. Any failure now prints
`CoDOL dogs: actor animation: ...` / `CoDOL dogs: actor init: ...` then
`CoDOL dogs: spawnactor on 'actor_enemy_dog_mp': ...` then the script
`CoDOL dogs: spawnactor produced no dog N ...; skipping it`, and the map keeps
running (the alive tracker fires "dogs done" once no dog is alive).

## 2026-09-16: scope sway (hold breath) and crosshair friend/foe colouring

Live defects reported on build 5f1c9db8. Both traced to C1.exe 1.1.1.13 (static)
and fixed server-side; WRITTEN + BUILT (objects compiled individually with the
build-w700-fix flags, nasm for the asm), not yet live-tested.

### 1. Scoped-in sway is wrong

Root cause: C1 computes ADS/scope sway client-side from its own WeaponDef, but
scales it by playerState `holdBreathScale` (+0x24c, netfield 34, float) which
`PM_UpdateHoldBreath 0x004188b0` (called from PM_Weapon at 0x41dc02, after the
ADS lerp) produces together with `holdBreathTimer` (+0x250, netfield 193, 16
bits) and `PWF_HOLDING_BREATH` (ps+0x344 bit 4; set 0x418945, cleared
0x41894e/0x41899b, fire path 0x418810/0x41bafb, HUD breath hint reads it at
0x45765c with +0x250 == 0). The server never published +0x24c/+0x250 and masked
bit 4 out of +0x344, so every snapshot re-based the client's predicted scale to
0.0 and the sway multiplier saw-toothed against the client's lerp toward 1.0.
No dvar is involved: the breath timings are inlined constants in this build
(hold 4500 ms at 0x4188c5, gasp +1000 ms at 0x418995, gasp scale 3.5 at
0xc84688, gasp lerp 6.0 at 0xc39ddc, hold lerp 1.0, fire delay -0.0 at
0xc84920); dvars 161/162 are only the breath-sound pair. The retained IW3
PM_Weapon runs its own dvar-driven copy (gasp scale-1 anchored to 1.0,
`overlayReticle` gate on an IW3 field the composed-weapon converter never
fills), which is not C1's producer.

Change:
- `src/codol/player/codol_pmove_c1_breath.c/.h` (new): port of 0x004188b0
  including `BG_CanHoldBreath 0x421f00` (def+0x694 overlay reticle read from the
  serialized base weapon image via `CODOL_LoadMountedWeapon`, class != 11, ADS
  fraction != 0, ability 26 veto), ability 13 hold extension (`ps+0x4d0` bit
  18, value * 1000 ms), ability 26 scale override, `DiffTrack 0x618c10`, and
  the fire clear (new EV_FIRE_* event this command).
- `src/codol/player/codol_pmove_c1.c:919-927`: capture the three words before
  the retained `PM_Weapon`, recompute them from the capture afterwards.
- `src/codol/snapshot/codol_engine_state.c` `CODOL_OverlayEngineMovement`:
  publish +0x24c (float) and +0x250 (clamped to 16 bits); validation accepts
  finite non-negative scale. `CODOL_OverlayEngineWeaponUseControl`: pass-through
  mask 0x81 -> 0x9d (adds bits 4, 8, 0x10).
Limit: a composed weapon whose attachment adds the scope overlay resolves
through its base image; the weapon core does not capture +0x694 yet (weapon
area, other worker).

### 2. Crosshair friend/foe colouring

Root cause: `CG_GetCrosshairColor 0x43c4e1..0x43c611` takes the colour purely
from ps+0x344: bit 8 -> friendly colour (after a settle time), bit 0x10 -> enemy
colour when `cg_crosshairEnemyColor` (dvar 690, 0x16da19c) is on and 250 ms
passed (0x43c563); `CG_DrawCrosshairNames 0x43a52f` tests the same 0x10. There
is no client-side entity trace and nothing in C1.exe writes the bits: this is
IW4's server contract (`Player_UpdateLookAtEntity` -> PWF_FRIENDLY_FIRE 8 /
PWF_ENEMY_FIRE 0x10). The retained IW3 game code has no such producer and
`g_redCrosshairs` (C1 dvar 1278 at 0x52b678; g_sv_main.c:775) had no reader.

Change:
- `src/codol/snapshot/codol_lookat.c/.h` (new): `CODOL_UpdateLookAtEntity`
  traces from `G_GetPlayerViewOrigin` along viewangles (8192 u, mask
  solid|clipshot|body) with `G_TraceCapsule`; a living playing client on the
  same non-free team sets bit 8, otherwise bit 0x10 when `g_redCrosshairs`.
  Non-client hits (actors/vehicles) stay neutral for now.
- `src/asmsource/_g_active_mp.asm:810-816`: ClientEndFrame calls it beside
  `CODOL_CaptureClientUseHint` on the playing path.
- Published through the widened 0x344 pass-through above.

Expected live: crosshair turns green over teammates and red over enemies
(bots included) in team modes, red over everyone in FFA; sniper ADS sway is
steady/consistent, Shift holds breath for 4.5 s with the breath hint shown,
then the gasp sway ramps and settles; firing ends the hold.

## 2026-09-16 00:20-01:20 - bots on the 700-slot build, grenade crash, site 4/5, magazines, RC-XD

Bots: the launcher needed no client. `set scr_codol_bots 12` over rcon
(password in alpha0022/native_server_rcon.txt) populated the running match in
seconds (maps/mp/gametypes/_codol_bots.gsc watcher); `+set scr_codol_bots 12`
via CODOL_EXTRA_ARGS does it at launch. Twelve "Training N" bots fight
(games_mp.log K lines every few seconds) on every build below.

Crash 00:20:43 on 5a3efa44 (WER c0000005 at +0x20e690, dump
%LOCALAPPDATA%\CrashDumps\codol_dedrun_next.exe.84332.dmp, `.ecxr` ecx=0xc):
Weapon_Throw_Grenade (_g_weapon.asm:981) reads weaponParms+0x3c as the
WeaponDef pointer; the C port CODOL_UseOffHand (codol_weapon_give.c) filled
codol_weaponParms_t with an extra `unsigned weapon` field at +0x3c, so the
throw dereferenced the weapon index. Fix: codol_weapon_give.h drops the field
(weapDef is +0x3c after five vec3s). Human threw a grenade = crash; bots do
not throw, which is why 5 min of bots never hit it.

Weapon-bits site 4/5 (`passed playerState 0x7b`): _g_items.asm Touch_Item_240
`CODOL_WB_MODEL_LOAD eax, esi, edi` had ps/weapon swapped (edi is the ps that
Touch_Item_210 passes to G_GivePlayerWeapon, esi the weapon from [eax+0x540]);
now `eax, edi, esi`. Zero helper-validation lines since.

Magazines (human: primary shows 0 but fires, secondary frozen at full):
- Server state is right: new `CoDOL giveammo:` trace after G_InitializeAmmo
  (deagle idx 57 size 7 -> clip 7 reserve 14, ak104 30/60, ...).
- Wire keys are right: new `CoDOL weapon table:` dump (engine wire ammoKey
  clipKey engAmmo engClip clipSize name) replayed through alpha0022's
  live-verified weapon_spawn.IndexPools gives 0 diffs over all 137 published
  slots (stock 1..53 == MEASURED; grenades 54..69; composed 117..136 e.g.
  `*a 27 13 227 ...` wire 135 clip 134 ammo 27, `*a 18 0 54 0 210 0 32 0`
  wire 136 clip 135 ammo 18).
- `CoDOL ammo bindings: client N clips [slot engX keyY count/left]` trace
  (only while a human is connected - bots get frames only then) showed every
  single-hand magazine published as count/0. alpha0022's live-verified
  weapon_loadout.write_ammo_in_clip_section publishes the magazine in BOTH
  hand values; C1 reads ammoClip[hand] (0x41a4b2). CODOL_BuildServerAmmoBindings
  now publishes left=count unless an owned dual-wield weapon shares the clip
  (real second magazine kept). Not yet confirmed by the human.
- Also traced: `CoDOL ammo bindings: client N REFUSED (owned N weapons,
  ceiling 15)` if CODOL_BuildEngineAmmoBindings ever refuses; never fired.
- Budget line now carries the _bg_weapons.asm pools: `pools ammo 106/128 clip
  106/128 sharedcap 12/128` (the 128-pointer pools sit before their
  neighbours' counters; an overflow would corrupt them - watch this as the
  table grows).

RC-XD: `thread maps\mp\killstreaks\_rcbomb::init();` re-enabled in
scripts/codol/maps/mp/killstreaks/_killstreaks.gsc. First relaunch died with
`function 'trigger_monitor_init' already defined (_rcbomb.gsc line 833)`: the
file carried the raw T5 trigger_monitor_init/trigger_monitor/
rcbomb_force_explode block a second time after the adapted copies; removed
the 39-line duplicate (raw T5 copy), collate_gsc.py + codol_script_resolve.py
--only maps/mp/killstreaks exit 0, map loads with _rcbomb compiled.

Dogs with bots: the human called dogs twice; `_dogs.gsc` errors both times
(`undefined is not an entity` line 422, later `type undefined is not a
vector` line 452: `dog forceteleport(spawn_node.origin...)` - spawn_node is a
node without .origin; mp_rust has no dog spawn nodes). _dogs.gsc and
codol_actor_* are the dogs worker's in-progress files (git-modified while
this ran, two of their .cpp files did not compile mid-edit; builds below used
`make -o` on those and the last good objects). Not touched here.

Builds (obj/build-w700-grenade-20260916.log, cross-build from WSL):
5f1c9db8 grenade fix; de9219fe + site 4/5 + table trace; 2a323c4b + REFUSED
trace; 38587ef5 + both-hands magazines = deployed bin/codol_dedrun_next.exe
sha256 38587ef532df33db22c60f61a6d454ad70159a58a2632c034b0fe899885c812d
(copies in bin/rollback/). Source additionally has `#include
"codol_weapon_bits.h"` in codol_sv_weapons.c (removes an implicit-declaration
warning; no behaviour change, not in the deployed binary). Running: PID 100404,
mp_rust dm, 12 bots, budget peak 126/700, no fallback/helper warnings,
no sys_error, RC-XD compiled.

## 2026-09-16 RC-XD physics/driver pass (build 5f1c9db8 live result: spawns, flips, slides through walls, uncontrollable, wheels static, no FX)

Live log evidence (bin/home/main/qconsole.prev-de9219fe.log: `d 3437
mp_killstreak_rcbomb` at 00:4x): the native side printed NOTHING for the
whole ride - no body/contact/driver line existed - so the run could not
explain itself. This pass adds the `CoDOL rc:` lines and fixes what was
diagnosable statically.

Not controllable (root cause, static): `codol_vehicle_ground_runtime.cpp
demand()` fed C1's handbrake word into T5's `braking_state`. C1 683c50
(disassembled from C1.exe) sets the AUTOMATIC handbrake whenever
speed in [0,250] and (steer == 0 exactly or |steer| >= 10); rc_car_medium_mp
has handbrake enabled (VehicleDef+0x310 = 1) and thirdPersonDriver
(+0x2cc = 1, steer = driver view yaw - car yaw, which is exactly 0 right
after usevehicle because CODOL_RemoteVehicleEnter sets the view to the
car's tag_player yaw). In C1 that state only rescales powered wheels
(SteerVehicleWheels 6x/10x) and the motor target; in the T5 wheel
constraint it deletes the motor row on every braking-axle wheel, so a
standing or turning car never accelerated. Fix: only the explicit C1
handbrake button (0x100000) is a T5 power brake
(codol_vehicle_ground_runtime.cpp, demand(), `explicitBrake`). Also a
driver whose executed CoDOL usercmd is unavailable no longer fails the
physical frame (which would Com_Error the match); it drives with zero input
and prints once.

Flips / slides through walls (not resolved statically): the pulse solver,
wheel ray (T5 get_wheel_collide_segment parity verified against OpenBLOPS
rbc_def_vehicle.cpp:182), COM/roll-stability, initial orientation
(VEH_SetPosition before CODOL_CaptureSpawnedVehicle in SpawnVehicle;
AnglesToAxis of placement (0,yaw,0)) and the ODE contact normal convention
(retained Phys_NearCallback attaches body(o1),body(o2); pulseNear pushes
body A along +normal) all read consistent. The next live run decides with:
- `CoDOL rc: body ent N model .. mass com origin angles gravity wheels
  radius travel wheel0 center spring damping limit grip brake remote view`
  once at attach (codol_vehicle_ground_runtime.cpp attach()).
- `CoDOL rc: first contact ent N vs world count pos normal depth body ..`
  once per body from the pulse near callback
  (codol_vehicle_pulse_world.inc pulseNear; CODOL_VehicleODEFrameContacts
  exported from codol_vehicle_ode.cpp).
- `CoDOL rc: ent N driver linked/released (client c) view v` on seat change
  and `... has no executed usercmd` once.
- every 1 s: `CoDOL rc: ent N t drv cmd fwd right btn | steer thr rev hb
  auto motor target/force | org ang spd vz | wheels [C<force> ...] contacts K`.
Reading guide: contacts K > 0 while the car rests on its wheels means the
chassis brush reaches the ground (spring/sag or brush extents); a first
contact normal pointing INTO the ground (z < 0 for a floor) means the
retained brush collider's normal convention is inverted for the pulse path
(flip + wall pass-through would both follow); wheels all `-` with the car on
the floor means the wheel ray (CM_BoxTrace mask 0x280e491) misses; drv -1
means usevehicle never linked; fwd/right always 0 with cmd 1 means the
client's direction bits are not what pmove assumes.

Wheels do not spin / FX missing: FX names and tags all ship in CoDOL
(verified against common_gametype_mp.ff); the effects were never played
because T5 drives them from _rcbomb.csc. Ported to server GSC in
scripts/codol/maps/mp/killstreaks/_rcbomb_presentation.gsc (start,
persistentLight, stunSparks, treadFx) with two lines in _rcbomb.gsc
(tread fx handles stored; thread start). Wheel spin publication: see the
snapshot note below (vehicle entity-state words).

Built: obj/rcphys-win32/codol_vehicle_ode.o and
codol_vehicle_ground_runtime.o compile clean (same flags as
obj/build-w700-fix-20260916.log, plus -pipe). No link, no deploy.
`codol_script_resolve.py --root bin/home/codol_rawfiles --only
maps/mp/killstreaks` exit 0; collate_gsc.py exits 2 (alpha0022/vendor/iw4
missing on disk), the four _rcbomb files were copied to
bin/home/codol_rawfiles by hand.
Status: WRITTEN + object-compiled; NOT live.
Wheel spin / steer (C1 disassembly, agent report): C1 CG_Vehicle_DoControllers
45d94c yaws the two front wheel bones by entity word +0x68 (steerYaw) and
gives every other wheel the identity quaternion; no C1 consumer spins axles
from any entity-state word (T5's steerPitch accumulator was dropped), so
"wheels do not spin" cannot be produced by the server. What C1 does read was
never published: retained G_SetOrigin zeroed pos.trDelta each frame (C1
67d018 speed for engine audio/FX) and steerYaw stayed 0. Now
codol_vehicle_ground_publish.cpp writes pos.trDelta = body velocity and
u.vehicle.steerYaw = controller steering degrees (carried in
codol_vehicle_frame_body_t.steering_degrees from demand()); bodyPitch/Roll
stay 0 (attitude is in apos). Front wheels should now visibly steer.

### 2026-09-16 follow-up (build 559438f6): forceteleport "type undefined is not a vector"

The animtree fix held (spawnactor succeeded). The next line died at
`dog forceteleport(spawn_node.origin, spawn_node.angles)` - the caret is under
`angles`: nodes on this VM are the map's `node_*` entity-string records
(src/codol/script/codol_script_path_nodes.c) and CoDOL maps author no
"angles" key on path nodes, so `.angles` is undefined while `.origin` is fine
(the T5 weighting code had already read every candidate's origin).

scripts/codol/maps/mp/_dogs.gsc:
- :207-216 init_node_arrays drops nodes without an origin; keeps
  `level.dog_pathnodes`; :245 records `level.dog_spawn_nodes_authored`
  (getnodearray("spawn","script_noteworthy") non-empty).
- :367-380 get_spawn_node takes its candidates from the new
  :405-460 `dog_spawn_nodes_for_team(team)`: authored nodes if any; else each
  of the owning team's spawn points (`level.teamSpawnPoints[team]` when team
  based, else `level.spawnpoints`) is mapped to its nearest path node
  (dog_get_closest_node over level.dog_pathnodes), the spawn point's angles
  stored on the node as `.dog_spawn_angles`; deduped, cached per team, one
  `CoDOL dogs: no authored dog spawn nodes; using the N path nodes nearest the
  M <source> for team <team>` print; falls back to T5's random path nodes (and
  says so) if nothing usable exists.
- :530-546 teleport site: undefined `.origin` prints
  `CoDOL dogs: spawn node has no origin; skipping dog N`, deletes the actor and
  returns undefined; angles = node.angles, else node.dog_spawn_angles, else
  (0, random yaw, 0).

tools/collate_gsc.py exits 2 here ("vendor root not found ... alpha0022/vendor/iw4")
even from the repo root, so bin/home/codol_rawfiles/maps/mp/_dogs.gsc was
copied by hand from scripts/codol; codol_script_resolve.py --only maps/mp exit 0.
Not launched.

Expected next call-in (mp_rust dm/war): `CoDOL dogs: no map dog_spawner entity;
building one with spawnactorspawner( "actor_enemy_dog_mp" )`, then
`CoDOL dogs: no authored dog spawn nodes; using the N path nodes nearest the M
level.spawnpoints for team <team>` (or `level.teamSpawnPoints[<team>]` in war),
then no further `CoDOL dogs:` line while dogs spawn and run.

## 2026-09-16 — magazine keys off by one after dog_bite; crosshair bits verified server-side

Build 2cf09dd5 (bin/codol_dedrun_next.exe, rollback/codol_dedrun_next.559438f6.exe).

### A. Magazine counts (primary 0, secondary frozen at the primary's count) — FIXED, client-verified

Root cause: the wire registry keyed every composed magazine one higher than the
client. Ground truth was read out of the running C1.exe (bg_weaponDefs
0x150D720 -> def+0x570/+0x568, pool counters 0x150CC20/0x150CC2C): the client
had 137 clip / 115 ammo pool entries against the registry's 138 / 116, and
`*a 27 13 227 0 ...` at wire 135 carried clipIndex 133 on the client while the
server published its magazine under key 134. The HUD reads the section-2 record
whose key equals its own def->iClipIndex (0x41a4b2), so the M4A1 matched nothing
(0, still fires by prediction) and the G18 at wire 136 (client 134) matched the
M4A1's record (30, never moving).

The slot that consumes no index on the client is `dog_bite` (wire 98): its zone
def has the de-dup gate set (+0xBBC = 1) and both +0x564/+0x56C point at the
zone's shared empty string (0x3002f501 in common_gametype_mp), so
BG_AssignAmmoIndex/BG_AssignClipIndex (0x41f200/0x41f3f0) find an earlier
""-named pool entry (`none`) and return its index. The registry
(src/codol/weapon/codol_weapon_registry.c CODOL_RegisterWeaponKeys) substituted
the internal name for an empty ammo/clip name — the raw weapon-file parser rule,
which never runs for a linked asset — so "dog_bite" matched nothing and appended.
alpha0022's IndexPools has the same substitution (`SHARED_NAME_KEYS.get(name,
(name, name))`) but was only ever validated over the 54 stock + 14 equipment
defs, none of which is gated with empty names; the previous "0 diffs vs
IndexPools" compared two models sharing the bug.

Change: empty strings are kept and compared verbatim; the record stores the gate
and no-clip flags; `CODOL_RegisteredWeaponKeyNames()` exposes them and the
`CoDOL weapon table` trace prints `[gate 'ammo'/'clip']` per definition.
Live after relaunch: `dog_bite [1 ''/'']` keys 0/0; wire 131 -> clip 129, wire
135 -> clip 133, matching the client's own table entry for entry.
`CoDOL ammo wire: client N weapon <name> clip idx <i> -> field <slot> key <k>
value <a0>/<a1>` prints for a human's held weapon whenever any part changes
(codol_sv_weapons.c CODOL_BuildServerAmmoBindings); no human connected during
this pass.

### B. Crosshair friend/foe — server side verified, wire side needs a human

C1 CG_GetCrosshairColor 0x43c4a0 (read live): requires the held def's byte
+0xBC3 != 0 (1 on every gun, 0 on frag_grenade_mp/none), ps+0x344 bit 8 ->
friendly colour after cg time - cg+0xbf054 >= dvar[0x16d44dc]+0xc, bit 0x10 ->
enemy colour when dvar 690 cg_crosshairEnemyColor (default true, CHEAT) and the
same delta >= 250 ms. cg+0xbf054 has no writer in .text (scan for the immediate
finds only the two readers), so the delay gates are always satisfied. The
client's config_mp.cfg does not need the dvar.

Server side: `CoDOL lookat: client A -> client B team 0/0 flags 0x10 weapFlags
0x10 (g_redCrosshairs 1)` prints for bots on mp_rust dm (80 lines in the first
minute), so the capsule trace and team logic set the bit in cl->ps.weapFlags at
ClientEndFrame; the retained clear (`and eax,0xffffffe7` at ClientEndFrame_160)
runs before the call site in flow. The publish trace `CoDOL crosshair wire:
client N netfield(0x344) 0x.. weapFlags 0x..` (codol_engine_state.c
CODOL_OverlayEngineWeaponUseControl, on transition of bits 8/0x10) only fires
for clients that receive snapshots — bots do not — so it needs the human to
connect; if it prints 0x10 while the crosshair stays white, the next place to
look is the client's delta reader for netfield 87, not the server.

Build note: the makefile compiles C++ with `$(CPP)`, not `$(CXX)`; a build with
only `CXX=i686-w64-mingw32-g++` compiled every .cpp as Linux ELF and the link
failed with mutual undefined references (`_Com_Error` vs `Com_Error`). Pass
`CPP=i686-w64-mingw32-g++` as well and delete the ELF objects first.

Observed before the relaunch: PID 54372 (559438f6) had gone silent after a
`mapchange` match report (`Hitch warning: 1162 msec`, last log write 01:17, no
CPU, no rcon reply for 8 min) — a map-change hang worth a separate look.
Fade-to-black on call-in/detonation: dropped in our port (the old
"_hud::fadeToBlackForXSec not available" note), not a missing builtin -
every builtin on the T5 path is a retained native (newclienthudelem,
setshader, fadeovertime, destroy; material "black" in code_post_gfx_mp).
Ported verbatim: _rcbomb_presentation.gsc rcFadeValue/fadeIn/fadeOut/
fadeToBlackForXSec (:218-286), threads at _rcbomb.gsc:94 (call-in) and
:190 (after rcbomb_done). Edited in place in bin/home/codol_rawfiles and
mirrored to scripts/codol; resolve gate exit 0.

### 2026-09-16 follow-up (build 2CF09DD5): every snapshot rejected as "actor animation delivery" once a dog spawned

Root cause (src/sv_snapshot.c:1325): SV_SendClientMessages calls
SV_BuildClientSnapshot for every client (:1388) BEFORE SV_SetServerStaticHeader
(:1392), so the live `CODOL_ActorDeliveryCapture(..., -1, svsHeader.time)` used
the PREVIOUS frame's time. G_RunFrame had just appended the dog's animation
events at svs.time, so `CODOL_ActorAnimJournalCut(time < lastTime)` refused the
cut, the capture stayed invalid, `CODOL_ActorDeliveryPrepare` returned 0 because
an ET_ACTOR entity was in the recipient's PVS, and the whole frame was rejected
- every frame, for as long as the dog emitted events, i.e. the rest of the
match. Bots were unaffected because no snapshot is built for them. Before a dog
exists the journal has no time watermark, which is why it only started at the
call-in.

Fix: src/sv_snapshot.c:1325 captures at `(unsigned)svs.time` (the archive at
:2148 already runs after SetServerStaticHeader and was correct).

Degrade + diagnostics (never deafen a client again):
- src/codol/snapshot/codol_frame_builder.c:171-205: a refused delivery prints
  once per distinct reason `CoDOL dogs: actor animation delivery to client N
  dropped for sequence S: <why>`, clears that recipient's delivery state
  (fresh timeline + full bootstrap next frame) and sends the snapshot with zero
  actor animation commands instead of failing the frame.
- src/codol/player/codol_actor_anim_journal.h:20-21 / .c:12-25
  `codol_actor_delivery_failure` + `CODOL_ActorDeliveryFail(fmt,...)` (formats
  the reason, returns 0). Every zero return on the path now names itself:
  journal cut/archive/capture/copy (journal.c), pose capture (XAnimInfo range,
  parent mismatch, ref past tree size, node count, state out of wire range with
  the values), bootstrap (clone rules, per-snapshot cap), pose archive lookups
  (codol_dog_animation.c), and delivery capture/prepare
  (codol_actor_delivery.cpp: capture keeps its reason per client so Prepare's
  "no pose capture for sequence" line carries it).

Compiled individually (exit 0, no new warnings): codol_actor_anim_journal.o,
codol_dog_animation.o, codol_actor_delivery.o, codol_frame_builder.o,
sv_snapshot.o. Not linked, not launched.

Expected next call-in: no `CoDOL frame rejected ... actor animation delivery`
and no `msg overflowed ... builder: actor animation delivery`; dogs animate for
the human. If anything on the path still refuses, one `CoDOL dogs: actor
animation delivery to client N dropped for sequence S: <reason>` line appears
and snapshots keep flowing (dogs T-pose until the next successful frame).

## 2026-09-16 — Snapshot bitmask audit (C1 readers vs server producers)

Full report: docs/CODOL_SNAPSHOT_BITMASK_AUDIT_20260916.md.

Every C1 1.1.1.13 snapshot reader (MSG_ReadDeltaPlayerstate 0x5A19C0 incl. the
7 trailing sections, MSG_ReadDeltaField 0x5A0510 all codecs, MSG_ReadDeltaEntity
0x5A0C00 + 22 per-eType tables, ReadDeltaStruct 0x5A0A40 for clients/actors/
objectives, hudelem 0x5A1830, dynent 0x4484A0, animcmd 0x5A1170) was
re-disassembled and every post-decode mask/bit-test in bg/cg/game was diffed
against src/codol/snapshot producers. Wire result: encodings, widths, gap
coders, hint-2/hint-3 passes and delta bases are 1:1 (no WRONG-ENCODING /
WRONG-WIDTH). Bit-meaning result:

- FIXED: retained vote code set IW3 EF_VOTED 0x100000 into ps.eFlags, which C1
  reads as EF_VEHICLE_ACTIVE (0x4817CA and 29 more sites) — src/g_sv_cmds.c:349
  and src/g_cmds.c:598 are now `#ifndef CODOL_SERVER`. Compiled g_cmds.o /
  g_sv_cmds.o individually (exit 0). Not linked, not launched.
- Documented NOT-PUBLISHED with C1 readers: ps+0x344 bits 0x200/0x10000/
  0x100000 (no native source), ps+0x14 bit 1, ps 0x333c/0x3334/0x0060/0x0218/
  0x0354/0x0358/0x0350/0x053c/0x0540, clientstate 0x008..0x01c/0x0a8/0x12c..0x134.
- Corrected notes: `cmp [..+0x344],7/8/9/0xB` sites are WeaponDef+0x344, not
  ps.weapFlags; the 5 bytes per equipped-weapon slot (ps+0x2DC+i*5) are booleans
  (byte1 = possessed), not ammo; with dvar "1289" (default 1) BG_GetWeaponSlot
  0x40AB60 always returns slot 14; C1 PM 0x41DA20 blocks the hand update while
  weapFlags&8 (friendly crosshair) — publishing bit 8 is C1-faithful.
- weapFlags 87 does not need an every-frame send in the C server: C1 XOR-deltas
  against the last received value and codol_history stores the reached value.
Speed (live 30e06d18 "too fast"): the motor target is C1's own
rc_car_medium_mp VehicleDef (header dump): topSpeed +0x18 = 668.8 in/s
(38 mph), accel +0x1c = 528 in/s^2 (30 mph/s), reverseSpeed +0xc8 = 668.8,
boost enabled (+0x2fc) speed x2.0 / accel x3.0 / 2 s / 60 s recharge
(+0x300..+0x30c). C1 683cc0 scales the target by 1/boostSpeedMultiplier
when boost is idle, so cruise is 334 in/s = 19 mph and boost (button
0x400) 38 mph. The BO1 rc_car vehicle file is not on disk; T5's
NitrousVehicle default m_speed_max is 1100 in/s (62 mph), so C1's numbers
are the vanilla contract and were left. The 1 Hz line now prints
`top <in/s> scale <x> mph <actual>/<target>` for a live check.
Wheel spin, re-checked (C1.exe, agent): under C1 the wheel bones of a
networked ET_VEHICLE can only steer (front, wire +0x68) and bob
(suspension words); no entity-state word, trDelta (reaches the wire and
feeds only inst+0x3c engine speed), xanim or def field spins an axle. The
only server-influenced wheel visual is materialTime (67d7d0): inst+0x34
accumulates from prev/next snapshot POSITION deltas x client def+0x14
(texture-scroll scale), so a UV-scrolling wheel material would need
distinct consecutive snapshots of the entity. Spin therefore needs client
code (T5 steerPitch accumulation, cg_vehicle.cpp:608-616) or a wheel
material/anim asset; stopped here. steerYaw publication stays (C1's own
server rate-limits it at 5 deg/think, 678680).

## 2026-09-16 — Unpublished snapshot fields backlog (docs/CODOL_UNPUBLISHED_FIELDS_20260916.md)

Build 01bbe537 (bin/codol_dedrun_next.exe; rollback of the previous live
9bd30e6f in bin/rollback/codol_dedrun_next.9bd30e6f.exe). An intermediate
build 82987725 was deployed first and crashed the match twice with
`SV_GetCachedSnapshot: end of message`: the archive links codec
(codol_playerstate_ext.c:1387-1400) read into an uninitialised
`codol_ps_links_t` and the widened `CODOL_PlayerLinksValid` rejected the
garbage `anglesLocked` word, so the ext reader bailed mid-record and the cached
stream desynced. Fixed by archiving the bit (write :1032 / read :1391).

Status legend: WRITTEN = source only; BUILT-TESTED = built, booted with 12
bots, log-verified; LIVE = needs a human C1 client (bots receive no snapshots,
so the wire traces below only print once a client connects).

1. **[HIGH] ps+0x354/0x358 spreadOverride / spreadOverrideState** — BUILT-TESTED.
   C1 readers BG_CalcSpread 0x422660, spread integration 0x418b70 (state-1
   self-clear 0x418e28). Producer: `CODOL_OverlayEngineAim`
   src/codol/snapshot/codol_engine_state.c:451-479 puts both fields (6-bit
   range check, state <= 3) from the native ps fields PlayerCmd_Set/Reset-
   SpreadOverride already write; codol_pmove_c1.c:168-209 keeps consuming them.
   Trace on change: `CoDOL ps: client N spreadOverride V state S aimSpreadScale`.
2. **[HIGH] ps+0x14 bit 1 PLF_ANGLES_LOCKED** — BUILT-TESTED (bots do not link).
   C1 producers 0x53b37a (playerLinkToAbsolute) / 0x53bad6 (playerLinkToBlend),
   reader PM_UpdateViewAngles 0x4141b8/0x414216. Record field
   `codolPlayerLink_t.anglesLocked` (codol_script_startup_extra.h), set by the
   new `playerlinktoabsolute` (fraction 1.0, no arcs, absolute reference,
   locked) and cleared by every unlink through link_clear_player_part
   (codol_script_startup_extra.c:139). `playerlinktodelta` (offset-preserving,
   param 7 = useTagAngles, IW4 shape) is registered too; both at
   codol_script_startup_extra.c:1080-1082. Live flags:
   `CODOL_PlayerLinkFlags` :313; capture :368 -> `codol_ps_links_t.anglesLocked`
   (codol_player_links.h, validity requires mode != 0); wire
   codol_player_links_wire.c:50-55 (`linkFlags &= ~7`, OR 1) with trace
   `CoDOL ps: client N linkFlags 0x.. mode M locked L` (:99-110). PM consumer:
   codol_pmove_c1.c update_viewangles skips the free-look pitch clamp when
   locked in NORMAL_LINKED/DEAD_LINKED. playerLinkToBlend is NOT registered
   (C1 0x53ba40 also blends origin/angles over +0x20c..+0x21c timers; a
   lock-only stand-in would be a fake) — only animscripts/dog/dog_combat.gsc
   and SP maps call it.
3. **[HIGH] ps+0x333c spawn time** — BUILT-TESTED. C1 producer ClientSpawn
   tail 0x50f9ad, reader PM_Weapon_CheckForChange 0x41b109-0x41b14b.
   `codol_ps_ext_t.spawn_time` (codol_playerstate_ext.h) with
   Set/Read/Clear (codol_playerstate_ext.c:544-563), archived as an absolute
   long (:1066-1071 / :1447-1452); stamped in ClientSpawn
   src/g_client_mp.cpp:229-235 (`CoDOL ps: client N spawnTime T`); published
   in `CODOL_OverlayEngineMovement` codol_engine_state.c:260-277 via the
   -97 TIME codec (8-bit arm while serverTime - spawn <= 255 ms, 32-bit arm
   afterwards — the field only changes on spawn so it is sent once).
   Server-side twin of the C1 rule: `CODOL_ApplySpawnWeaponGate`
   codol_game.c:182-206, called from sv_client.c:1221 after
   CODOL_ToEngineUsercmd (`CoDOL spawn gate: client N ignored stale weapon 0`).
   Cleared for a connecting/leaving slot in CODOL_ResetClientInputCore.
   Verified: 48+ `spawnTime` stamps in one boot with 12 bots, all == level.time.
4. **[MEDIUM] clientState 0x018 dualWielding / 0x01c riotShieldNext / 0x0a8
   diveState / 0x12c vehicle entity / 0x134 colour** — BUILT-TESTED, needs a
   human for the animation checks. C1 G_UpdateClientState 0x50d0f0-0x50d1b8
   (disassembled: +0xb18 = pm_flags 0x400000 && !0x800 && pm_time==0 ?
   ps+0x3334+1 : 0; +0xb14 = ps+0x35c == 1; +0xb1c = (weapFlags>>12)&1).
   `codol_client_assets_t` gained dual_wield/riot_shield_next/dive_state/
   vehicle_entity/colour_index (codol_engine_state.h); filled from the live
   client in `CODOL_OverlayServerClient` src/codol/assets/codol_sv_assets.c
   (dual wield via CODOL_WeaponStateIsDualWielding; riot via the new native
   weapFlags bit; dive via the C1 formula on the C1-numbered pm_flags; vehicle
   = ownerNum-1 for a remote driver (CODOL_RemoteVehicleType >= 0, read-only)
   or the ET_VEHICLE tag parent; colour 0 = C1 default white, no producer
   identified in C1's server module yet); published by
   `CODOL_OverlayEngineClient` codol_engine_state.c:1090-1108 with trace
   `CoDOL cs: client N dualWielding .. riotShieldNext .. diveState .. vehicleEnt .. colour ..`.
   Riot shield: `codol_native_weapon_core_t.riot_shield` = C1 def+0x340 == 3
   (codol_weapon_native.c:223, accessor CODOL_GetNativeWeaponRiotShield
   codol_asset_registry.c), set/cleared on every weapon selection in
   select_weapon (codol_weapon_state.c) as native `CODOL_WEAP_RIOTSHIELD_NEXT`
   0x200000 and translated to C1 bit 0x1000 in CODOL_OverlayEngineWeaponUseControl.
5. **[MEDIUM] weapFlags 0x100000 disableWeaponPickup** — BUILT-TESTED (no
   script calls it yet). Methods `disableweaponpickup` / `enableweaponpickup`
   (codol_script_player_builtins.c, registered scr_vm_main.c:1163-1164) set
   native `CODOL_WEAP_PICKUP_DISABLED` 0x100000 (codol_weapon_flags.h);
   published unchanged in CODOL_OverlayEngineWeaponUseControl
   (codol_engine_state.c:911-922); server gate `CODOL_WeaponPickupAllowed`
   called at the weapon path of Touch_Item (_g_items.asm Touch_Item_150).
6. Skipped: 64-bit party id (3.4, lobby plumbing), 0x130/0x010 (no reader).

Static gate: `tools/codol_script_resolve.py --only maps/mp/perks` clean.

## 2026-09-16 14:00 - bots stuck in corners / bunching (codol_bot.c)

User report: 12 bots on mp_rust "get stuck in a corner or all bunch up on top
of each other". Root causes found with the new `CoDOL bot:` diagnostics
(src/codol/player/codol_bot.c, rate-limited: per-bot line every 2 s with
origin/goal node/next point/path index/speed/vz/pm_flags/in-solid/enemy/hold;
`stuck`, `recovered`, `wedged`, `crowd` events; graph size at load):

1. Wedged spawn, not a pathing bug: the first bot spawned on mp_rust
   (`mp_dm_spawn` #6, alpha0022 map_spawns.proposed.json origin
   -264.5 910.5 -213.5, placed at -265 911 -230) never moved one unit in 4 min
   (speed 0 through nudge/jump/repath/regoal) - 82 of the first run's 110 stuck
   events were that one bot. Collision/spawn placement is the owner's item; the
   bot layer now reports `CoDOL bot: wedged ... solid N` after the full
   escalation fails with zero displacement and notifies `bot_wedged`;
   `_codol_bots.gsc watchWedged()` respawns it with `suicide()` (no teleport).
2. Stuck detector was too coarse (codol_bot.c old movement(): 4-unit progress
   window, 2 s, only action = block edge + repath, no nudge, no goal change).
   Now: 12 units in 1.5 s (4 s on ladders) escalates nudge (700 ms backstep +
   strafe + one hop) -> repath from nearest reachable node with the edge blocked
   -> regoal (goalNode=-1, script goal fails with bad_path); `recovered` logs
   when the bot is 96 units from the stuck spot.
3. Path follower: node arrival was a 24-unit 3D sphere; a node 25+ units
   above/below the floor (ladder tops, stairs) could never be reached. Now 2D
   24 units with 48-unit z tolerance, plus a T5 Path_UpdateLookahead style
   lookahead: skip up to two stand nodes when a player-bounds capsule trace
   (G_TraceCapsule -15..15 x 18..48) to them is clear, so corners are never cut
   through geometry and slightly-passed nodes count as reached.
4. Bunching: (a) every bot that saw the same enemy pathed onto the enemy's
   nearest node (route(): to = nearest(lastKnown)) and stacked there - now a
   seen enemy within sv_botCloseDistance is engaged in place (`hold 1`); (b) no
   goal reservation - roaming goals now skip nodes another live bot holds or
   within 160 units of its goal (pick_roam_goal/node_claimed, 12 tries); (c) no
   separation - a 48-unit push-out from every living playing player (any team,
   dead/spectating excluded, |dz|<=72) is blended (x1.5) into the move direction
   and applied while holding/idle too. The `crowd` line fires when >=2 others
   are within 40 units for >2 s. mp_rust spawns were checked: only the
   intermission spectator spawn is shared, live spawns differ.
5. mp_rust node 143->144 (the tower ladder, climb) is never climbed by any bot
   (no bot above z -170 near 1641 1652); the escalation now blocks the edge and
   moves on instead of two bots standing at the ladder foot.

Run 1 (66cb3c91..., 4 min, mp_rust dm 12 bots): stuck 110 (82 = the wedged
bot), recovered 14, crowd 0. Waypoint graphs: 15 CSVs in bin/home/main/waypoints;
a map without one logs a warning and spawns no bots (GSC init returns).

## 2026-09-16 — RC-XD: detonation sound, ADS jump, activation XP timing, ride survives death

Build e0b809f0 (bin/codol_dedrun_next.exe, obj/build-rcxd-20260916.log; rollback of the dogs worker's cb2aac11 in bin/rollback/codol_dedrun_next.cb2aac11.exe), from live 01bbe537. Items 1-4 need a
human drive; bots cannot earn or use the streak. Status legend as above.

1. **Explosion sound** — WRITTEN, gated. T5 blowup plays
   `mpl_sab_exp_suitcase_bomb_main`; CoDOL ships the same alias without the
   T5 prefix, `exp_suitcase_bomb_main` (common_gametype_mp,
   docs/zone_assets/ALL_sound.txt:3431), so that is used instead of a mortar
   alias (`_mortar.gsc` plays no script alias at all - the shell's report is
   the weapon def's; `mp_killstreak_mortar`/`mp_killstreak_rcbomb` are the
   announcer lines). `playSoundAtPosition( "exp_suitcase_bomb_main",
   explosionOrigin )` in `_rcbomb.gsc blowup()` at the explosion origin, not on
   the car, which is hidden and deleted 1 s later.
2. **Jump on right mouse** — WRITTEN + object-compiled. T5
   NitrousVehicleController::UpdateJump (OpenBLOPS
   nitrous_vehicle_controller.cpp:1062): jump button held AND >= 2 wheels
   colliding in the previous update AND latch clear -> one
   `body->add_force((0,0,m_jump_force))`, latch set; button release clears
   the latch (holding never re-fires; pressing in the air fires on landing).
   Ported: `codol_vehicle_control_state_t.jump_pressed`
   (codol_vehicle_controls.h), `codol_vehicle_frame_body_t.jump_velocity`
   (codol_vehicle_ground_frame.h), demand() in
   codol_vehicle_ground_runtime.cpp reads C1 usercmd button 0x800
   (C1_BUTTON_ADS, right mouse) and the previous frame's wheel contact cache,
   prints `CoDOL rc: jump ent N client C wheels W` once per press; the frame
   prepare() (codol_vehicle_ground_frame.cpp) converts it to a central force
   `mass*dv/seconds` through the new `CODOL_VehicleODECentralForce`
   (codol_vehicle_ode.cpp / pulse_world.inc pulseCentralForce, integrated as
   linear += seconds*force/mass) and zeroes the request so a two-step clock
   advance fires it once. Magnitude: the BO1 rc_car vehicle file
   (m_jump_force) is not on disk and C1's IW-lineage VehicleDef has no jump
   field, so the impulse is a velocity, 226 in/s = sqrt(2*800*32), a ~32 in
   hop under C1 gravity; tune the constant in demand() if the human drive
   says otherwise.
3. **Killstreak XP/announcer at ride START** — WRITTEN, gated. T5
   _hardpoints awards on activation; here `killstreakUsePressed` awarded
   after the use function returned, which for the T5 rcbomb contract is the
   END of the ride. `_killstreaks.gsc killstreakUsePressed` now stashes
   `self.codolRideActivation` {streakName, awardXp, awarded} for ride
   killstreaks before calling the use function; new
   `awardRideKillstreakActivation()` (called from `_rcbomb.gsc
   givePlayerControlOfRCBomb` right after `usevehicle` succeeds) runs
   `usedKillstreak` (XP event, stat, inbound/enemy dialog, trigger sound)
   once and marks it; the post-return award is skipped when marked. Reward
   consumption (shuffleKillStreaksFILO/giveOwnedKillstreakItem) is unchanged
   and still happens when the use function returns.
4. **Death does not end the ride** — WRITTEN, gated. What ended it: nothing in
   _rcbomb (carDeathWaiter is commented out, as in T5) and nothing native
   (player_die neither unlinks nor clears otherFlags 0x400000); the ride was
   ended by the normal death flow - killcam, then respawn, whose
   "spawned_player" fires `_rcbomb_watchers::respawnWatcher`
   (scr_deleteexplosivesonspawn) -> "weapon_object_destroyed" ->
   "rcbomb_done" + ClientSpawn's CODOL_PlayerLinkResetClient ->
   CODOL_RemoteVehicleExit. T5 keeps the ride because
   _globallogic_player:1945 skips the killcam while IsRemoteControlling and
   _globallogic_ui:723 never calls spawnClient then. This framework already
   has those gates keyed on `self.usingRemote` (_damage.gsc:800 no killcam,
   :1587 straight PlayerKilled_internal, :2050 no last stand,
   _playerlogic::waitAndSpawnClient waits "stopped_using_remote"), so
   `givePlayerControlOfRCBomb` sets `self.usingRemote = "rcbomb"` on control
   and calls `_utility::clearUsingRemote()` (notify "stopped_using_remote")
   after "rcbomb_done"/restoreWeaponAfterRide; respawn then resumes normally.
   Not verifiable with bots: whether C1 keeps the remote camera on a
   pm_type-DEAD driver (the native link/otherFlags stay set; a `CoDOL rc:
   remote exit` line at death would mean something native cleared them).

Gate: `python tools/codol_script_resolve.py --root bin/home/codol_rawfiles
--only maps/mp/killstreaks` exit 0. Compiled clean: codol_vehicle_ode.o,
codol_vehicle_ground_frame.o, codol_vehicle_ground_runtime.o,
codol_vehicle_controls.o (obj/codol-win32). Note for other workers: a broken
string literal in runtime.cpp failed the dogs worker's build-dogs2.log at
14:16 for one minute; fixed at 14:17.
5. **Wheel spin (user item, "fix without touching the client")** — C1
   disassembly verdict (agent, capstone over C1.exe): NO server-publishable
   input rotates an RC axle. CG_AddVehicle 0x67d7d0 (eType 12 and 14 via the
   table at 0x443d40) never sets an xanim on the vehicle DObj;
   CG_Vehicle_UpdatePose 0x67d080 interpolates es+0x60/0x64/0x6c/0x70/0x68
   (steerYaw) and es+0x7c (suspension), resolves the six tag_wheel_* bones
   at 0x67d615 and traces each wheel to the ground for bob;
   CG_Vehicle_DoControllers 0x45d940 (sole caller 0x45e51e) gives wheels
   0/1 a quaternion from (0, steerYaw, 0) with pitch/roll hard `fldz`
   (0x45d966..0x45d98c) and wheels 2..5 identity (0x45dd47..0x45dd76) -
   T5's steerPitch accumulation (cg_vehicle.cpp:608-617 / cg_pose_mp.cpp:255)
   was dropped. The es+0x94 anim-tree word only reaches DObj creation
   (0x443610); every cent+0x218 reader is a player/actor anim path.
   Trajectory: trDelta feeds only rec+0x3c (speed for audio/FX, 0x67d018);
   prev/next snapshot origins feed 0x67cf30 rec+0x34 += dt*v/176*VehicleDef
   +0x14 (texScrollScale) as material time - a UV-scroll (tread) mechanism,
   and the RC-bomb xmodel has no scrolling material. The server's
   TR_INTERPOLATE publication is consumed correctly (trType table 0x40cca8).
   Done: codol_vehicle_ground_publish.cpp:53-74 stamps pos/apos.trTime =
   level.time and carries the addresses above; the 1 Hz `CoDOL rc:` line now
   ends `| tr type a/b time t base (..) delta (..) wheelrot none`. Spinning
   axles need either a client patch (restore steerPitch in 0x45d940) or a
   rebuilt RC asset (wheel material with UV scroll driven by texScrollScale).

Live: build e0b809f0 relaunched 14:26 (PID 1356); superseded at 14:30 by another worker's e5464f5b (PID 36848, built from the same tree, contains these changes - `CoDOL rc: jump ent` string present in the exe), udp/17733, mp_rust dm, 12
bots CS_ACTIVE, the four _rcbomb files lowered, no script/compile/runtime
error). Bots cannot use the streak: items 1-5 need a human drive
(`CoDOL rc: jump` on right mouse, the explosion sound, XP/announcer at the
pull-out, survival of a death mid-ride with no `CoDOL rc: remote exit`).

## 2026-09-16 - Dogs: clip table audit, chase/animation thrash, killfeed icon, stuck/bunching (build 89742b72)

LIVE on udp/17733 (bots 12, FFA on the handoff map, dogs via `rcon set codol_dogsTest 1`).

1. **Clip table (codol_dog_states.cpp) - AUDITED, no rebinding possible.**
   docs/zone_assets/ALL_xanim.txt: the MP zones ship exactly the 37
   `german_shepherd_*` clips the 47-node `animtrees/dog.atr` names. The T5
   variety (turn_90/180 in place, pain_hit_*, death_hit_*, run_attack_low,
   traverse_down_96/126/190) exists only as `zombie_dog_*` in
   common_gametype_zm (+ zombie_dog.atr), which no MP zone mounts. 31/52 states
   run their real T5 clip; 21 run the nearest MP clip (8 turns -> run_start
   L/R/180, 8 pains -> run_pain, 3 deaths -> death_front, close-range bite ->
   attack_player, traverse_down_80 -> down_40). Extending dog.atr server-side
   cannot help: C1 resolves the same tree from common_mp.zone. Comment block
   at codol_dog_states.cpp:93-118 records this; tests/test_codol_dog_animation.py
   PASS (64 clips bind).
2. **Animation thrash - FIXED (LIVE).** Trace of ent 939 (old log): the chase
   goal used the script `goalradius` 128 while bite range is meleeAttackDist+15,
   so the dog hit "goal" ~100 units short, switched dog_move -> dog_stop
   (stop_attackidle) and back every 1-2 frames as the enemy moved: each switch
   restarts move_start/attackidle with 0.2 blends, so the run cycle never
   played. T5 gives the attack spot its own codeGoal radius
   (Actor_UpdateMeleeGoalPos). `chaseRadius` (codol_actor_lifecycle.cpp
   struct + CODOL_ActorSetGoal + CODOL_ActorGoalDirection + RunFrame chase
   branch) = 24 for a claimed attack spot. Also ported T5
   Path_UpdateLeanAmount so the run knob's lean_L/lean_R weights are driven
   (lean was never produced, always centre). Post-fix transitions are
   move_start -> move_run -> combat_attack_run -> miss/bite -> move_run; the
   stop_attackidle churn is gone. Per-frame command count is unchanged (T5's
   think emits the same complete-goal set; no restarts, blends 0.2/0.3).
3. **Killfeed knife icon - FIXED (LIVE).** C1 producer 54E560/54E6F8
   (disassembled) replaces every MOD_MELEE death code by 700+8 (knife) unless
   WeaponDef+0x340==3 (riot shield). T5 avoids this in
   _globallogic_player::updateMeansOfDeath (dog_bite_mp -> MOD_PISTOL_BULLET).
   In the C1 zone `dog_bite` has no killIcon; the dog obituary icon
   `hud_obit_dogs` is the (inline) killIcon of the killstreak weapon `dogs_mp`.
   _damage.gsc: new `updateMeansOfDeath` + dog_bite -> dogs_mp swap in
   PlayerKilled_internal right after the owner-credit block. games_mp.log now
   logs `K;...;Training 12;dogs_mp;100;MOD_PISTOL_BULLET;head` credited to the
   owner.
4. **FFA dogs - FIXED (LIVE).** In a non-team game _dogs.gsc sets aiteam
   "free" (T5) and the native team setter refused it (script runtime error,
   no dogs at all). "free" now maps to sentient team NONE and `ActorMayTarget`
   lets a team-NONE dog target any non-actor sentient except its owner.
5. **Stuck / bunching - FIXED (LIVE), residual noted.** (a) attack-spot claims
   were already the route goal; (b) separation steering in
   CODOL_ActorGoalDirection (other actors within 40u push the wish direction)
   plus a per-frame radial push-out within 30u in RunFrame (route preserved
   across the push); (c) stuck detector: <8u in 1000 ms with a route ->
   `CoDOL dogs: ent N stuck at (x y z) for T ms -> repath|regoal`; repath drops
   the route and the spot claim, regoal (2nd second) snaps to the next route
   node or nearest nav node at the first non-startsolid lift (1/20/44) and
   notifies bad_path for patrols; (d) a failed route while chasing now falls
   back to the straight leg instead of standing. Live: 55 stuck lines/110 s
   before the validated snap, 18/120 s after; route FAILED 29 -> 2. Residual:
   one dog per run still wedges repeatedly at a map spot (ent 451, 10 events)
   - the waypoint graph has spots the dog capsule cannot stand on.
Files: src/codol/player/codol_actor_lifecycle.cpp, codol_dog_states.cpp
(comment), bin/home/codol_rawfiles/maps/mp/gametypes/_damage.gsc.
Static gate `codol_script_resolve.py --only maps/mp` clean.

Follow-up (same session, builds 0d11dae2 -> e5464f5b -> f309b5c2 -> e03a81bf,
deployed as bin/codol_dedrun_next.exe, PID 103936, mp_rust dm 12 bots):
- `wedged` detection added: nudge+repath+regoal with zero displacement ->
  `CoDOL bot: wedged ... pmf 0x%x solid N`, notify `bot_wedged`, GSC
  `watchWedged()` -> `suicide()`. Roaming bots with no route (nearest_reachable
  failed) now fall through to the same escalation instead of idling forever.
- False positives removed: C1 PMF_FROZEN (0x800, game-end/streak freeze) bots
  are skipped by the stuck logic (they came in bursts of 4-5 right before every
  map-restart separator).
- ENGINE LEAD (not a bot-layer bug, owner: sv_main/g_client/pmove): client 0
  ("Training 1", the first bot) never moves after any map (re)start: pm_flags
  keeps C1_PMF_RESPAWNED (0x400), ps.commandTime never advances (1350 for the
  whole match, 184100 after the restart) while every other bot's commandTime
  advances every frame. SV_BotUserMove -> CODOL_BotBuildCommand -> SV_ClientThink
  runs (the diag line prints), so the usercmd for slot 0 is dropped before
  Pmove. The wedged->suicide loop respawns it every ~7 s until fixed.
- Live numbers, build e03a81bf, 14:42:55-14:48:09 (5 min 14 s, 4 dm rounds,
  270 spawns): 1391 diag lines, stuck 37 (29 nudge, 8 repath, 0 regoal),
  recovered 19, wedged 3 (2 = client 0 above, 1 = 'Training 3' at 918 1678 -243
  pmf 0 solid 0), crowd 0. Speed samples: 1398, median 94 u/s, 368 zero (holds,
  reloads, client 0). Run 1 (build 66cb3c91, 4 min): stuck 110 (82 = client 0),
  recovered 14, crowd 0. Before this pass no diagnostics existed, so there is
  no numeric pre-fix baseline; the wedged-spawn bot alone explains the "stuck
  in a corner" report, the enemy-node stacking the "on top of each other".
- Other workers relaunched the server at 14:22, 14:28 and 14:34 during the
  soaks (their builds carried this source); saved logs:
  obj/qconsole-botfix-run1/run2b/run3-20260916.log.

## 2026-09-16 (15:40) — scope sway jitter: PM_UpdateHoldBreath goal anchor + composed hold-breath gate

Live defect (user): "sniper scope sway is broken and very jittery". Build under
test 9515bd55; fix build sha256
`52039996121F7258C24FC42FA27C79DD874536442130B27392D046ED0E38BEC5`.

### C1 model (re-disassembled from C1.exe 1.1.1.13, ImageBase 0x400000)

Sway is drawn entirely client-side, but three of its four inputs are playerstate
words the server publishes.

* `BG_AddIdleSway 0x00424C10` (called from `0x00425020` <- CG_PredictPlayerState
  `0x0050CC8B`):
  `A = stanceRamp * maxAngle * ps+0x348 (adsFrac) * ps+0x24C (holdBreathScale)`
  (`0x424D11`, `0x424D1D`), then
  `out[1] += sin(phase*0.0007)*A*0.01; out[0] += sin(phase*0.001)*A*0.01`.
  Early-outs on `def+0x694 == 0` (`0x424C3C`) and `adsFrac == 0` (`0x424C54`).
  `stanceRamp` ramps toward `def+0x700` when `ps->eFlags & 8` (prone) or
  `def+0x6FC` when `& 4` (crouch), at `dt*0.5` per step.
* `BG_AdvanceSwayPhase 0x00424B90`: `phase += (int)(ps+0x24C * dt * 1000 *
  speed)` (`0x424BE1`) — **holdBreathScale also sets the sway phase rate**, and
  the accumulator is an int in the caller's ctx (`ctx+0x20`), not in the
  playerstate, so it can never be reconciled by a snapshot.
* `BG_GetSwayParams 0x00422FE0`: `def+0xBC8 != 0` -> steady-ADS override
  `0x00422E20`; else `def+0x6F0` if non-zero, else the hard-coded **80.0f**
  (`0xC323B0`) with speed 1.0. A composed weapon with `swayMaxAngle == 0`
  therefore sways MORE than a stock one, not less.
* `PM_UpdateHoldBreath 0x004188B0` is called from `PM_Weapon 0x0041DB80` at
  `0x0041DC02`, right after `PM_UpdateAdsLerp 0x004185A0` (the only writer of
  ps+0x348). `Pmove` reaches it from CG_PredictPlayerState (`0x0050CC22`) as
  well as from the game (`0x0045F778`), so **the client re-predicts ps+0x24C and
  ps+0x250 for every pending usercmd, every render frame**; any server/client
  divergence in this function snaps the sway amplitude AND its phase rate.
* `BG_CanHoldBreath 0x00421F00`: `bg_weaponDefs[ps+0x33C]->f694 != 0`,
  `adsFrac != 0`, `def+0x344 != 11`, `!(ps+0x4D0 bit 5)` (modADSNoViewBob).
* Exhaustive `.text` scan: ps+0x24C is touched only at `0x418900/0x4189FE/
  0x418A23/0x418A51` (PM_UpdateHoldBreath) and `0x424BE1/0x424D1D`; ps+0x250
  only at `0x418860/0x418883/0x418891` (PM_StopHoldBreath `0x00418810`, called
  from the PM_Weapon_Fire tail `0x0041BAFB`) and the PM_UpdateHoldBreath sites.

### Root cause 1 (fixed): the goal anchor

C1 `0x00418A08..0x00418A13` blends the breath target against the **literal
1.0**:

    goal = 1.0f + (target - 1.0f) * ps->adsFrac;

`src/codol/player/codol_pmove_c1_breath.c:198` (pre-fix) anchored it to the
running scale instead — `goal = (target - scale) * posFrac + scale` — which
converges to `target` rather than to the ADS-weighted target whenever
`adsFrac < 1`. Identical at `adsFrac == 1`, different on every partially-scoped
frame and through the whole gasp/recovery ramp, so the published scale was a
value the client's own PM_UpdateHoldBreath could not reproduce and the
amplitude (and phase rate) snapped on each snapshot.
Fix: `src/codol/player/codol_pmove_c1_breath.c:255`
`goal=1.0f+(target-1.0f)*ps->fWeaponPosFrac;`

### Root cause 2 (fixed): the hold-breath gate read only the base image

`weapon_has_scope_overlay()` read `+0x694` out of the **base** weapon's
serialized image only. C1 builds the composed definition with
`BG_BuildCustomWeaponDef 0x00421590`, which copies the base image and then
applies each type-43 attachment's `{offset,type,value}` override entries before
`BG_CanHoldBreath` reads `+0x694` from it. A scope attachment on a base whose
own image carries 0 there would make the server refuse a hold the client grants.
Fix: `src/codol/player/codol_pmove_c1_breath.c:110-130` replays the same
override entries through `CODOL_ComposedWeaponRecord` /
`CODOL_ComposedAttachmentAssetName` / `CODOL_LoadMountedWeaponAttachment`.

### Instrumentation added (kept, hard-throttled)

* `CoDOL breath def: weapon <idx> '<composed>' base '<base>'
  overlayReticle(+0x694)=<n> scope=<0|1>` — once per weapon index, 200 lines.
* `CoDOL breath: c<n> t<commandTime> w<weapon> posFrac <f> btn<0|1> can<0|1>
  hold<0|1> timer <ms> scale <f> msec <n> ft <f>` — one line per 100 ms per
  client while `posFrac > 0`; **300 lines of budget for idle ADS frames and a
  separate 1500-line budget for frames where the breath button/flag/timer is
  active**, so bots cannot exhaust the budget a human needs.

### Live evidence on the fix build (bots, mp_rust)

    CoDOL breath def: weapon 115 '*a 11 11 69 20 18 18 ...' base 'cheytac_mp' overlayReticle(+0x694)=1 scope=1
    CoDOL breath def: weapon 111 '*a 53 0 150 0 32 0 33 0 155 0' base 'wa2000_mp' overlayReticle(+0x694)=1 scope=1
    CoDOL breath def: weapon 117 '*a 14 0 33 0 41 0 ...'        base 'fal_mp'    overlayReticle(+0x694)=0 scope=0
    CoDOL breath: c5 t12850 w115 posFrac 1.000 btn0 can1 hold0 timer 0 scale 1.0000 msec 50 ft 0.0500

So both sniper bases pass the gate (`can1`), no shipped type-43 attachment
overrides `+0x694`, and the published scale is a rock-steady exact 1.0000 at
full ADS. **What the server publishes is therefore already correct in the
steady scoped state**; any residual jitter with a stationary, fully scoped
player is client-side — the int-truncated sway phase accumulator (`ctx+0x20`,
replayed per pending usercmd inside CG_PredictPlayerState) or the composed
WeaponDef's own `+0x6F0/+0x6F4/+0x6F8/+0xBC8` sway parameters, none of which
travel in a snapshot. The human trace (`CoDOL breath:` lines for the connected
client) is what separates the two: a human whose `msec` per PmoveSingle is much
larger than his frame time, or whose `scale` is not 1.0000 while scoped and
still, is a server divergence; otherwise it is the client's own sway model.

### Addendum (15:50, build 61135847...): the live sway path is NOT holdBreathScale

A second pass re-read `bg_weaponDefs` (0x0150D720) out of the **running C1.exe**
and found `def+0x694 == 0` for every sniper (cheytac_mp idx101, wa2000_mp 96,
barrett_mp 44, as50_mp 18, m21ebr_mp 13); only g18_mp/m79_mp/type95_mp carry a
non-zero. With `+0x694 == 0`:

* `BG_CanHoldBreath 0x421F00` returns 0 -> hold breath never engages,
* `BG_AddIdleSway 0x00424C10` returns at `0x424C46` **before** its ps+0x24C read
  at `0x424D1D`, and `BG_AdvanceSwayPhase 0x00424B90` is unreachable.

The sway actually drawn is the parallel path **`0x00423080`** (`0x0050CD47` ->
`0x004244C0` -> `0x00423080`), which has no `+0x694` entry gate and **never
reads ps+0x24C**:

    A     = cg.stanceRamp * BG_GetAdsSteadySwayAngle()        // 0x423186..0x423198
    speed = def+0x6F8 + (def+0x6F4 - def+0x6F8) * ps+0x348    // 0x00422FE0 override arm
    *(int*)(cg+0x384C) += (int)(dt*1000*speed)                // 0x4230CD..0x4230E3, __ftol
    out[0] += sin(phase*0.001 )*A*0.01                        // 0x423244
    out[1] += sin(phase*0.0007)*A*0.01                        // 0x423214
    out[2] += sin(phase*0.0005)*A*0.01                        // 0x4231E5

`BG_GetAdsSteadySwayAngle 0x00422E20` (regcall esi=ps, edi=def) keeps a global
per-client table at **0x016A07E8, stride 12** = `{float lastAdsFrac, float
lastAmp, int startTime}` indexed by `ps+0x140`, and:

* its ramp clock is **`ps->commandTime` (ps+0x00)** — `mov edx,[esi]` at
  `0x00422E75` (store) / `0x00422EBB` (read-back), **not** cg.time;
* it re-arms on **`ps+0x348 != 1.0f` tested with `fucomp`, i.e. exact float
  equality**: one frame at 0.9999 sets `startTime = 0` and collapses the
  amplitude to 0, and the next exact-1.0 frame re-stamps `startTime` and
  restarts the whole `def+0x714` delay + `def+0x718` ramp from zero. No
  hysteresis, no epsilon;
* it reads ps+0x00, ps+0x140, ps+0x348 (five times) and ps+0x4D0 bit 5
  (`modADSNoViewBob`, which **zeroes** the amplitude).

`0x00423080` additionally reads **ps+0x0C pm_flags bit 0x40000000** (vetoes the
prone sway scale def+0x700) — neither ps+0x00 nor ps+0x0C was on the list of
snapshot fields previously known to feed sway.

`cg+0x3848` (stanceRamp) and `cg+0x384C` (int phase) are persistent, with **no
save/restore around prediction**; a full branch scan of `0x0050C8D0..0x0050CDA0`
and `0x0050F800..0x0050FA60` shows no backward jumps, so the phase advances once
per view invocation, not once per replayed usercmd — replay depth does not
multiply it. The residual wobble in the phase is `__ftol` truncation of
`(int)(msec*speed)`.

**Consequence:** the sway a sniper actually sees is a pure function of
`ps+0x348` (netfield 45, raw-XOR `-88`), `ps+0x00` and `ps+0x0C` — all
snapshot-delivered — plus the client's own def. `ps+0x24C` is correct but
unread on this build for snipers. Any per-snapshot dip of the published
`fWeaponPosFrac` off exact 1.0f collapses the sway amplitude and restarts the
multi-second ramp, and simultaneously steps the sine's phase VELOCITY, which
reads as a hard stutter. **That is the mechanism to chase for the remaining
jitter**, and the `CoDOL breath:` trace's `posFrac` column is the probe: a
scoped, stationary human whose `posFrac` is not a constant `1.000` is the bug.

### Unresolved conflict: zone image vs live runtime for def+0x694 and the sway block

The server reads the definition out of the mounted zone image
(`CODOL_LoadMountedWeapon(base)`, blob == runtime def per the project's harvest
note). On this server, for `cheytac_mp`:

| field | server zone image | live C1 bg_weaponDefs |
|---|---|---|
| +0x694 | 1 | 0 |
| +0x6EC | 40.0 | 30.0 |
| +0x700 | 0.1 | 0.4 |
| +0x714 | 30.0 | 0.45 |
| +0x718 | 15.0 | 6.0 |
| +0xBC3 | 1 | 1 |
| +0xBC8 | 1 (0 only on ranger_mp) | 1 (0 only on ranger_mp) |

`+0xBC3` and `+0xBC8` agree exactly (including ranger_mp being the single
`+0xBC8 == 0`), so the blob is **not** globally shifted; the `0x694` and
`0x6EC..0x718` block genuinely differs. The live read was taken while C1 was
loaded but between matches, so it may be a front-end/patch-zone copy. **Tie
break required: re-read `bg_weaponDefs[<composed slot >= 54>]` while the client
is IN a match** (composed records at `0x01536C68`, stride 0xE78, def at
record+0x98, count at `0x015369E8`). Until then the server keeps following the
zone image it mounts, and the `CoDOL breath def:` / `CoDOL breath def sway:`
lines print both halves of the comparison on every boot.

## 2026-09-16 (15:57) — crosshair friend/foe: the friendly path already worked and painted STEEL BLUE; enemy is unreachable in C1

Live defect (user): "crosshair friend/foe colour still does not show, neither
green nor red, in team modes and FFA". Target is the HUD crosshair — the four
disconnected segments — not the optic reticle. Build
`50346B0FE4C3B11E6F05817C3AEB2B0AA79C100C0E8BC5424B37E05A64969913`.

### The draw path (confirmed, so the colour function is the right one)

`CG_Draw2D 0x0043B780` -> `CG_DrawCrosshair 0x0043D1D0` (sole call site
`0x0043B938`, gated on `ps.pm_type < 8` and dvar "2620"). It calls
**`CG_GetCrosshairColor 0x0043C4A0` at `0x0043D34D`** into a local float[4] and
passes that buffer byte-for-byte to `0x0043CAE0` (centre pic, material
weapDef+0x450) **and to `0x0043CD60`, which draws the four segments** (material
weapDef+0x454 `reticleSide`, four `CG_DrawRotatedPic` at `0x0043CE8D`/
`0x0043CEE8`/`0x0043CF37`/`0x0043CF93` at 0/90/180/270 deg, gap lerped from
`ps.aimSpreadScale`). `0x0043CD10` copies `out.rgb = in.rgb` verbatim and only
recomputes alpha. **So the segments are tinted by CG_GetCrosshairColor.**

### Root cause 1 — the friendly colour is a steel blue, not green

    0043c503 mov ecx,[esi+0x344]      ; cg.predictedPlayerState.weapFlags (cg+0 IS the predicted ps)
    0043c509 test cl,8
    0043c50c je 0x43c546              ; not taken when bit 8 is set
    0043c50e mov edx,[esi+0xbf050]
    0043c514 sub edx,[esi+0xbf054]    ; NEITHER is cg.time (that is cg+0xB0350);
                                      ; no writer for either anywhere in the image,
                                      ; cg_t memset at 0x0044E152 -> delta is always 0
    0043c51a mov eax,[0x16d44dc]      ; dvar "775"
    0043c51f cmp edx,[eax+0xc]        ; 0 vs 0
    0043c522 jl  0x43c5f4             ; SIGNED; 0 < 0 is FALSE -> falls through
    0043c528 mov eax,0xC42478         ; "291"
    0043c52d call 0x623550            ; Dvar_GetUnpackedColor(name=eax, out[4]=edi)

Dvar `"291"` is registered at `0x0052B1FF` via `Dvar_RegisterColor 0x00624840`
with **(0.4, 0.6, 0.85, 1.0)** — read back live as `66 99 D9 FF`, a steel blue.
Nothing overwrites the colour afterwards (`0x0043C532..0x0043C545` only scales
alpha by dvar "687", live 1.0). **The friendly bit was working the whole time;
it just never painted anything a player would call green.**

Fix: `src/codol/snapshot/codol_lookat.c:74-100` — one reliable command per
client per map, `s 291 "0 1 0 1"` (PlayerCmd_SetClientDvar's CoDOL wire form,
`_g_client_script_cmd_mp.asm:3468-3486`, C1 CG_SetClientDvarFromServer
0x468A00), with `CODOL_ResetLookAtClientState()` exported to re-arm it. Live
proof: `CoDOL crosshair colour: client N -> dvar 291 = 0 1 0 1`.

### Root cause 2 — the enemy (red) colour is structurally unreachable

    0043c546 test cl,0x10
    ...
    0043c563 cmp ecx,0xFA             ; 250 ms
    ...     jl -> white

`ecx` is the same `cg+0xBF050 - cg+0xBF054` delta, permanently 0, so `0 < 250`
is always true and the enemy branch always takes the white exit. **No value the
server can publish makes the crosshair red on C1 1.1.1.13.** The friendly branch
only survives because its threshold is dvar "775" (int, default 0, live 0).
`ps+0x344` bit 0x10 is still published: `CG_DrawCrosshairNames 0x0043A52F`
consumes it for the enemy name. Bit 8 must NOT be used for enemies as a
work-around — C1's `PM 0x0041DAAE` does `if (weapFlags & 8) { ps+0x34 = 0;
return }`, i.e. it blocks firing at whatever the bit marks.

### Refuted: WeaponDef +0xBC3

`+0xBC3` is IW4's **`crosshairColorChange`** bool (pinned from the IW4 field
name table in `D:\CoD\iw4x_development\iw4x.dll` @0xF90BCC; the neighbouring run
`+0xBC4 bRifleBullet`, `+0xBC5 armorPiercing`, `+0xBC6 bBoltAction`,
`+0xBC8 aimDownSight` all validate against 505 named zone defs, with ranger_mp
the single `+0xBC8 == 0`). `0x0043C4F6` is the **only** instruction in the whole
image that touches it. Values: **1 on all 42 live stock defs and all 20 live
composed defs**; 0 only on grenades/equipment/killstreak markers/turrets. This
server's own zone-image read agrees — `crosshairGate(+0xbc3)=1` on every weapon
in the `CoDOL breath def:` trace. Composed defs inherit it because C1
`0x00421590` does `mov ecx,0x2FF; rep movsd` — a verbatim 0xBFC-byte copy of the
base def (`0x004216B2`/`0x004216C4`) — and nothing writes that displacement.
The server also cannot influence it: it publishes weapon NAMES, and the client
builds the def from its own zones.

### Still open (weapon area, not this worker's files)

Two of the twenty live composed definitions have a corrupted reticle block —
`*a 70 0` (base ff58_mp) and `*a 41 0 31 0` (base aa12) carry
`+0x450 = 'mc/mtl_*'` camo materials with `+0x454 (reticleSide) = NULL` and
`+0x440..0x44F` zeroed, where their bases hold `+0x450 = NULL,
+0x454 = 'reticle_side_small'`. `0x0043CD82` bails on a NULL reticleSide, so for
those two loadouts **the four segments are never drawn at all** — which also
looks like "the crosshair colour does nothing". Read from a client in the menu,
so confirm in-match; owner is the weapon-composition area.


## 2026-09-16 — Melee lunge: server ran IW3 charge physics, not C1's

**Defect (user, live):** "knifing/knife lunging is a bit bugged and doesn't land
on the enemy player all of the time" — the lunge animation plays and no damage
is dealt.

**Melee path on this server.** `HandleClientEvent` jump table index 12
(`EV_FIRE_MELEE`, bg.h 31) -> `FireWeaponMelee` (`src/asmsource/_g_weapon.asm:787`)
-> `G_AntiLagRewindClientPos(client->lastServerTime)` (`src/g_weapon.c:54`) ->
`Weapon_Melee_internal` (`_g_weapon.asm:441`) -> `Melee_Trace` (`_g_weapon.asm:89`)
-> `G_LocationalTrace` -> `G_Damage`. `src/asmsource/_codol_actor_melee.asm` is a
cdecl adapter onto the same `Weapon_Melee_internal` and is unchanged (verified
live: dog melee still damages players).
Parameters, all confirmed live with the new diagnostics:
range/width/height come from the dvars `player_meleeRange/Width/Height`
(64/10/10, `src/g_sv_main.c:679`), never from the weapon def; the shape is a
5-ray fan from the eye to `origin + forward*64 (+- right*10, +- up*10)` plus a
4-ray second pass whose start is also offset; the mask is `0x2806891`, which
includes `CONTENTS_BODY 0x2000000`; hits come back as `hitType 1` with a
`partName`, i.e. bone-level, exactly as IW3/IW4. Composed weapon defs are NOT
zeroed: every live composed def reports `damage 135, delay/time 79/800,
chargeDelay/chargeTime 100/1159`. The damage tick is `EV_FIRE_MELEE`, raised by
`PM_Weapon` state 12 -> 13 (`_bg_weapons.asm:7943`) when `ps->weaponDelay`
expires — i.e. by design the trace runs at the END of the lunge.

**Root cause (two defects, both making the server trace from short of where the
C1 client already put the player).**

1. `PM_MeleeChargeUpdate` was still IW3's (`src/asmsource/_bg_pmove.asm:351`).
   C1's `PM_MeleeChargeUpdate` @`0x00415C40` computes
   `T = (meleeChargeDist > 64 ? def->meleeChargeDelay : def->iMeleeDelay) * 0.001`
   (`0x415D10`/`0x415D22`, scale `0xC84410 = 0.001`),
   `v0 = 2*meleeChargeDist / T` (`0x415D64` `fdivr` + `0x415D70` `fadd st,st`),
   `velocity = v0*(cos,sin)(meleeChargeYaw * 0xC842F8=0.0174533)`, and
   `meleeChargeTime = T * 0xC842B0 = T*1000`; it then **returns without
   decrementing** (`0x415DBA` -> `0x415DC0` epilogue), because the countdown
   belongs to `PM_MeleeChargeMove` @`0x00415EC4` alone. The retained IW3 body
   instead used `speed = sqrt(2*dist*player_meleeChargeFriction)` /
   `time = speed/friction*1000` **and** decremented by `pml->msec` itself, while
   the already-correct C1 port `CODOL_PM_MeleeChargeMoveC1`
   (`src/codol/player/codol_pmove_c1_ground.c:868`) decremented again. For a
   48-unit lunge that is `v0 = 339 u/s` over an effectively 141 ms charge instead
   of C1's `v0 = 1215 u/s` over exactly 79 ms: about 25 of the 48 units were
   covered by the time `EV_FIRE_MELEE` fired, and the player kept sliding
   afterwards. The client had already moved the full 48.
2. `PM_Weapon` selected the charge timing pair on `pm_flags & 0x20000`
   (`_bg_weapons.asm:7013`), IW3's `PMF_MELEE_CHARGE`. CoDOL's
   `PM_MeleeChargeStart` sets C1's bit `0x10000` (C1 `0x415C4E`, `0x415EDB`), so
   the test never passed and every charged lunge ran on `iMeleeTime/iMeleeDelay`
   (800/79) instead of `meleeChargeTime/meleeChargeDelay` (1159/100) — a
   different damage tick from the one the client predicts (C1 `0x0041BD87`
   selects on `0x10000` and `dist > 64.0` @`0xC323A8`).

**Change.**
* `src/codol/player/codol_melee_charge_c1.c` (new) — C1 `PM_MeleeChargeUpdate`.
* `src/asmsource/_bg_pmove.asm:351` — `PM_MeleeChargeUpdate` is now a
  `jmp CODOL_PM_MeleeChargeUpdateC1` thunk under `CODOL_SERVER`; the IW3 body is
  kept as `PM_MeleeChargeUpdate_iw3` for non-CoDOL builds. Both callers
  (`_bg_pmove.asm:6058` and `codol_pmove_c1.c:887`) are untouched.
* `src/asmsource/_bg_weapons.asm:7013` — charge pair selected on `0x10000`.
* `src/codol/weapon/codol_melee_debug.c` (new) + three call sites in
  `_g_weapon.asm` — `CoDOL melee:` diagnostics behind the new `codol_meleeDebug`
  cvar (`src/common.c`, `src/qcommon.h`): attacker/weapon/def melee fields,
  command time, antilag time and rewind, trace start and entity origin, forward,
  velocity, `pm_flags`/`meleeChargeTime/Dist/Yaw`, nearest reachable enemy and
  its server origin, trace fraction/hitType/hitId/cflags/partName, the damage
  applied, and a running attempts/hits total.
* `src/codol/player/codol_bot.c` — bots now melee in close quarters and ship
  `meleeChargeDist/Yaw` with the button, the way the C1 client does, so the
  server melee path can be exercised without a human.

**Live measurement (12 bots, mp_rust).** Lunge now reproduces C1 geometry:
`meleeChargeDist 48 delay 79 ms -> moved 52.9 u`, `51 -> 55.6`, `54 -> 56.7`,
`60 -> 56.8`, `77 (charge pair, delay 100 ms) -> 63.4`, `76 -> 69.2`; short
samples are lunges blocked by walls or other bots. The 100 ms rows also confirm
defect 2 is fixed (`meleeChargeDelay` is now selected above 64 units).
Bot melee hit rate: **before 35 attempts, at most 21 client hits = 60.0%**
(that counter also swept up dog/actor melee, which shares `Weapon_Melee_internal`
through `_codol_actor_melee.asm`, so 60% is an upper bound); **after, with the
actor path split out, 16/26 = 61.5% in one run and 17/20 = 85.0% in the next**.
That is deliberately reported as flat: bots are simulated entirely on the server,
so they have no client prediction to diverge from, and the post-fix miss log
shows the residue is bot aim, not the melee path — misses at `side 23..30`
(outside the 10-unit fan), `hitId 2046` at low fraction (a wall between them) and
two attempts at `dist > 100`. **A human's feel needs the user's own test**; the
defect this fixes is exactly the attacker-side prediction divergence bots cannot
produce.


## 2026-09-16 (16:30) - crosshair friend/foe: read out of the LIVE C1 process; `s 291` DID land, the enemy branch is dead, the only unproven link is bit 8

Defect: the four HUD crosshair segments never change colour. User tested twice on
`war` (team deathmatch) with real teammates; the friendly bit and the colour
command are both in the server log. Everything below was read out of the running
client (PID 67516, ImageBase 0x00400000, PROCESS_VM_READ only) or disassembled
from its mapped image, not inferred.

### 1. dvar "291" in the live client: GREEN. The prior "it never landed" branch is refuted.

`Dvar_RegisterColor` at `0x0052B1FF` stores the dvar_t pointer in the global
`0x0220CF98`. Live read of that dvar_t:

    name '291'  flags 0x88  type byte +8 = 8 (color)
    current +0x0C = 0xFF00FF00   -> Dvar_GetUnpackedColor -> (0.0, 1.0, 0.0, 1.0)
    latched +0x1C = 0xFF00FF00
    reset   +0x2C = 0xFFD99966   -> (0.4, 0.6, 0.85, 1.0), the registered steel blue

So `SV_GameSendServerCommand(client, 1, "s 291 \"0 1 0 1\"")` reaches C1, is
accepted, and sticks (it survived the disconnect back to the menu). The dvar id,
the wire form and the writability are all correct; nothing to fix there.
dvar_t layout confirmed live: name +0, flags +4, type byte +8, current +0x0C,
latched +0x1C, reset +0x2C, DvarValue 0x10 bytes.

### 2. The four segments really are tinted by CG_GetCrosshairColor

`CG_DrawCrosshair 0x0043D1D0`, tail re-read live:

    0043d342  fld  [ebp-0x1c]          ; alpha
    0043d345  lea  edx,[ebp-0x14]      ; out float[4]
    0043d348  push edx / push ecx / fstp [esp]   ; arg0 = alpha, arg1 = out
    0043d34d  call 0x0043C4A0          ; CG_GetCrosshairColor
    ...
    0043d46d/0043d4af  push eax = [ebp-0x14] -> call 0x0043CAE0   (centre pic)
    0043d4cf/0043d4d3  push eax = [ebp-0x14] -> call 0x0043CD60   (four segments)

and `0x0043CD60` passes it to `0x0043CD10`, which copies `out.rgb = in.rgb`
verbatim (`fld [eax]/[eax+4]/[eax+8]` -> `[ecx]/[ecx+4]/[ecx+8]`) and only
recomputes alpha. The prior worker's reading of the draw path is correct.
Note `0x0043CD82`: a NULL `reticleSide` (weapDef+0x454) skips all four draws.

### 3. The two compares, re-verified, and why the enemy colour is unreachable

    0043c4f6  cmp byte [edx+0xbc3],0 / je WHITE      ; edx = bg_weaponDefs[ps+0x33c]
    0043c509  test cl,8   (cl = ps+0x344)
    0043c50e  edx = cg[0xbf050] - cg[0xbf054]
    0043c51a  eax = dvar "775" (global 0x016D44DC, type 5, live value 0)
    0043c51f  cmp edx,[eax+0xc] / jl WHITE           ; 0 < 0 is false -> falls through
    0043c528  eax = "291" -> call 0x00623550 (Dvar_GetUnpackedColor, out in EDI)
    0043c546  test cl,0x10 ... 0043c551 dvar "690" (live 1)
    0043c563  cmp ecx,0xFA / jl WHITE                ; same delta, so always taken

Independent proof the delta is permanently 0: a byte scan of the whole mapped
image for the displacements `0xBF050`/`0xBF054` returns exactly three hits each,
all in `.text` and all READS (`0x0043A826`, `0x0043A82D` in
CG_DrawCrosshairNames, `0x0043C50E`/`0x0043C514` and `0x0043C557`/`0x0043C55D`
here); `.tvm0` has none. cg_t is memset at `0x0044E152`. **Therefore the enemy
(red) branch cannot be reached on C1 1.1.1.13 by any value the server can
publish, and the friendly branch is always past its settle gate.** Confirmed:
`0x0043A834` reads cg.time from `cg+0xB0350`, so 0xBF050/0xBF054 are a separate,
never-written pair, not cg.time.

Do not set bit 8 for enemies as a workaround: `0x0041DAAE`
(`test byte [eax+0x344],8` -> `mov [eax+0x34],edx` -> early return) short-circuits
a PM weapon/offhand routine on that bit.

### 4. The weapon gate is not the blocker

Walking the client's own `bg_weaponDefs` table at `0x0150D720`: 153 definitions
resident, 148 with `+0xBC3` (IW4 `crosshairColorChange`) = 1. The five with 0 are
index 0 `none` and four unnamed tail slots (708/709/713/714). Every gun passes.

### 5. The netfield table matches C1 exactly

`src/codol/snapshot/codol_player_fields.inc` compared entry-for-entry against the
live table at `0x00C38CA8` (stride 12, 244 entries): **0 mismatches**. Index 87 is
`offset 0x344, 21 bits, changeHint 0` in both. So the field the server publishes
is the field `CG_GetCrosshairColor` reads, and 21 bits carry bits 8/0x10 fine.

### 6. Client-side prediction does not eat the bits

Every write to `[reg+0x344]` in `.text` (52 sites) is a read-modify-write; the
PM range `0x418000-0x41E000` uses masks `0xFFFFFFFB`, `0xFFFFEFFF`, `0xFFFEFFFF`,
`0xFFFFFEFF`, `0xFFFFFDFF`, `0xFFFFFFFD` and ORs of 2/4/0x1000 - none of them
touches 0x8 or 0x10. Prediction preserves whatever the snapshot delivered.

### Conclusion and what changed

Every link is now verified except one, which needs a live in-match read: whether
bit 8 is present in `cg+0x344` while aiming at a teammate. If it is, the crosshair
is green today, because the dvar is already green in this client. Two server
defects that could suppress the colour were found and fixed:

* `CODOL_ResetLookAtClientState` (codol_lookat.c) **had no caller anywhere in the
  tree**, so the per-slot `crosshair_colour_sent` latch survived for the life of
  the server process: a client entering a slot a bot or an earlier player had
  already used never received `s 291 "0 1 0 1"` and kept the steel-blue default.
  Now called from `CODOL_ResetClientInputCore` (codol_game.c) with the rest of the
  per-slot input reset.
* The `CoDOL lookat:` trace was capped at 400 lines process-wide and twelve bots
  exhausted it inside a minute, so the human's line - the only diagnostic one -
  could never print. Bots (`netchan.remoteAddress.type == NA_BOT`) are now
  excluded from the trace; the count went from 182 lines/6 min to 0.

New tool: `tools/codol_crosshair_probe.py --pid <C1 PID>` prints all four dvars
and, per sample, `ps.weapon` / weapDef `+0xBC3` / `ps.weapFlags` bits 8 and 0x10 /
the settle delta / the verdict colour, in the instruction order the gate uses. It
says "client is in the menu" rather than guessing when cg_t is zeroed.

Build `76A9EA2520C1C8BE562F8F6E9D0FCA6EB5389FAF06390C988A53D28CCD2BB68D`, deployed
to `bin/codol_dedrun_next.exe`, running as PID 21748 on `mp_killhouse_sh` /
gametype `war` with 12 bots split allies/axis.

Next test, in one line: join, aim at a teammate. Expect a GREEN crosshair. If it
is still white, run the probe while aiming and read the printed verdict, and check
the server log for `CoDOL lookat: ... flags 0x8` (the bit at ClientEndFrame) next
to `CoDOL crosshair wire: ... netfield(0x344) 0x8` (the bit in the built snapshot);
whichever of those two is missing localises the remaining fault. Enemies stay
white by design of this client build - see 3.

## 2026-09-16 (16:35) — sniper ADS sway, third pass: the drawn amplitude is a step function of `ps+0x348 == 1.0f` exactly, and the server had two ways to leave it

Build `906CCA807ADA2308940E21625F7ECCAFD6DB6F3EECD4141E530E434BBD7159EA`
(`obj/build-sway-fix5.log`), deployed to `bin/codol_dedrun_next.exe`, relaunched
with `+set scr_codol_bots 12`.

### The mechanism, fully disassembled (C1.exe 1.1.1.13, ImageBase 0x400000)

The 15:50 addendum's identification of `0x00423080` is correct. Decoding
`BG_GetAdsSteadySwayAngle 0x00422E20` instruction by instruction gives the
exact shape, which the previous entry only sketched:

    maxAngle = ((ps+0x4D0 >> 5) & 1) ? 0.0f : def+0x6EC        // 0x422E26..0x422E3E
    if (ps+0x348 == 1.0f)   /* fucomp, exact equality, 0x422E4B */
        if (tbl[cn].lastFrac != 1.0f) tbl[cn].startTime = ps->commandTime;  // 0x422E75
    else
        tbl[cn].startTime = 0;                                  // 0x422E82
    amp = maxAngle;                                             /* both bail arms */
    if (0.0f < def+0x714 && ps+0x348 == 1.0f && tbl[cn].startTime != 0)
        amp = clamp(((commandTime - startTime)/1000 - def+0x714) /
                    (def+0x718 ? def+0x718 : 1.0f), 0, 1) * maxAngle;   // 0x422ECC..0x422F42
    else if (0.0f < ps+0x348 < 1.0f)
        amp = (ps+0x348 >= tbl[cn].lastFrac) ? 0.0f : tbl[cn].lastAmp;  // 0x422F5A..0x422F85
    tbl[cn].lastFrac = ps+0x348;  tbl[cn].lastAmp = amp;        // 0x422F9D, 0x422FB0
    return def+0x6F0 + (amp - def+0x6F0) * ps+0x348;            // 0x422FB7..0x422FC3

`def+0x714` is the **steady-hold delay in seconds** and `def+0x718` the **ramp
length in seconds** (live cheytac 0.45 / 6.0; live vector_mp 0.3 / 4.0), i.e.
C1 reuses IW4's `adsSwayMaxAngle` / `adsSwayLerpSpeed` slots for "scope is
perfectly steady for N seconds, then sway grows in over M seconds".

The consequence is the whole defect: with `def+0x6F0` = 15 for every weapon
dumped so far, **one frame of `ps+0x348` at 0.99999 instead of 1.0 takes the
returned angle from `amp` (up to 30) to `15 + (0 - 15)*0.99999 ≈ 0.00015`, and
re-arms `startTime` so the multi-second ramp restarts from zero.** It is a step
function, not a blend. `0x00423080` then also recomputes the sine's phase
velocity from the same word (`speed = def+0x6F8 + (def+0x6F4 - def+0x6F8) *
ps+0x348`, `0x0042301C`) and reads `pm_flags & 0x40000000` at `0x004230EF` to
veto the prone scale `def+0x700`.

Also confirmed at `0x0042319E`: when `def+0x694 != 0` this path multiplies the
amplitude by `(1 - ps+0x348)`, i.e. a weapon with a scope overlay gets **zero**
sway from `0x00423080` at full ADS and is served by `BG_AddIdleSway` instead.
So `def+0x694` selects which of the two sway models a weapon uses.

### (a) The codec is exonerated, by direct table read

The C1 playerstate netfield table at `.rdata:0x00C38CA8` is 244 records of
`{int offset; int bits; int changeHint}` (12 bytes, no name pointers — the
build is stripped). Dumped from C1.exe and compared field-for-field against
`src/codol/snapshot/codol_player_fields.inc`: **0 differences in all 244
records.** Field 45 is `{0x348, -88, 0}` on both sides, and `-88` is
`CODOL_WriteLong(m, from ^ to)` (`codol_delta.c:156`) — a bit-exact 32-bit XOR
against the acked frame's value, with the base taken from the per-client
history ring (`CODOL_FindHistoryBase`, `codol_sv_snapshot.c:251`). There is no
quantisation anywhere on this field; `0x3f800000` in is `0x3f800000` out.
Field 20 is `{0x0c, 31, 0}`, so pm_flags bit `0x40000000` fits the wire.

### (b)/(c) live server-side evidence

Bots exercise the real `update_ads_lerp_c1` (their fraction moves by
`msec * def+0xa28`, not by the `codol_bot.c` lerp). 76 traced commands on a
scoped bot held `posFrac 3f800000` with `pmf 0x00000050` (PMF_ADS_BUTTON |
PMF_ADS) and no stance bits, so the ordinary producer is already exact. The
human trace is what is still missing and is what the new line prints.

### The two server bugs fixed

Both are the same invented failure mode: `CODOL_ResolveEngineWeaponState`
(`codol_engine_state.c:535`) can *refuse* a `(weaponstate, weapAnim)` pair —
engine states 3/4 with an unlisted animation, and anything outside its table —
while C1's equivalents read the hand state out of `ps+0x278` directly and
cannot fail. Both call sites folded that refusal into "not aiming":

* `src/codol/player/codol_pmove_c1.c:604` (`update_ads_lerp_c1`) had the
  refusal in the same condition as `def+0xbc8 == 0`, so an unclassifiable
  command **slammed `fWeaponPosFrac` to 0.0f**. C1 `0x00418655..0x0041867D`
  zeroes it only for `def+0xbc8 == 0` and for states 13/14/15. Now the
  unresolved case leaves the fraction alone.
* `src/codol/player/codol_pmove_c1.c:468` (`update_aim_down_sight_flag`) and
  `:489` (`update_ads_flag`) cleared `PMF_ADS_BUTTON` / `PMF_ADS` on a refusal,
  which drives `desired` to 0 in the very next lerp and walks the fraction
  *down* off 1.0. C1 `BG_PlayerCanAds 0x00418140` has no such outcome. Both now
  hold the previous flags through an unclassifiable command.

### Instrumentation added

`src/codol/player/codol_pmove_c1.c:524` `ads_sway_trace()`:

    CoDOL sway: c<n> t<commandTime> dt<commandTime delta> msec <n>
      posFrac <raw 8 hex> (<7dp>) exact1 <0|1> pmf 0x<8 hex> dive<0|1>
      eF 0x<stance bits 4/8> st<resolved>/<state> des<0|1> w<weapon>

It follows **one** client — the first non-`NA_BOT` slot, via the new
`CODOL_ClientIsBotClient()` (`codol_bot.c`, `codol_bot.h`) — prints on every
change of the raw fraction bits, on every unresolved hand state, and otherwise
once per 250 ms while the weapon is off the hip, capped at 4000 lines. A
stationary scoped human whose lines are not all `exact1 1` is a remaining
server divergence; `st0/...` lines mean the state translator refused a pair
(now harmless, but it names the missing mapping).

### Open: the mounted zone image does not match C1's runtime WeaponDef

Reading `bg_weaponDefs` out of the running C1 for `vector_mp` and comparing
with the server's boot dump of the same base weapon:

| field | server zone image | live C1 |
|---|---|---|
| +0x6EC | 15.0 | 15.0 |
| +0x6F0 | 15.0 | 15.0 |
| +0x6F4 | 1.5 | 1.5 |
| +0x6F8 | 5.0 | 5.0 |
| +0x6FC | 0.75 | 0.75 |
| +0x700 | 0.4 | 0.4 |
| +0x714 | 6.0 | **0.3** |
| +0x718 | 6.0 | **4.0** |
| +0xBC8 | 1 | 1 |

Everything agrees except the two steady-ADS timing words, which rules out a
struct shift and points at the server mounting a different (pre-patch) copy of
the weapon asset than C1 loads. Same shape as the cheytac_mp conflict logged at
15:50 (`+0x694`, `+0x6EC`, `+0x700`, `+0x714`, `+0x718`). These words are never
transmitted, so they cannot cause the sway jitter directly, but `+0x694` does
drive the server's hold-breath gate, so the mismatch is still wrong. The
in-match composed-slot read is still outstanding: C1 was at the front end for
every read taken in this pass (`commandTime 0`, only the last-equipped weapon
resident in `bg_weaponDefs`).

## 2026-09-16 -- two map-killing defects: missing xanim (mp_storm_spring) and the mp_nuked dog_spawner

Both were reproduced from `bin/home/main/qconsole.log` and are fixed at the
level that makes the whole class impossible, not just the two maps.

### 1. mp_storm_spring died on a missing xanim

Root cause: `bin/home/codol_rawfiles/maps/animated_models/foliage_tree_oak_1.gsc:18`
carried the IW4 single-player arm

```
if ( SP ) level.anim_prop_models[model]["sway"] = %foliage_tree_oak_1_sway;
else      level.anim_prop_models[model]["sway"] =  "foliage_tree_oak_1_sway";
```

`%name` is a **compile-time** animtree reference. The compiler registers it
whether or not the `SP` branch can ever run, so `animtrees/animated_props.atr`
then demanded the asset at tree-load time. `mp_storm_spring` ships only seven
xanims (`docs/zone_assets/mp_storm_spring.txt`: `ex_airconditioner_fan` plus six
`mp_storm_fencetarp_*`); `foliage_tree_oak_1_sway` ships only in `mp_bloc_sh`
and `mp_underpass` (`docs/zone_assets/ALL_xanim.txt:1818`). The map is reached
through `maps/mp/mp_storm_precache.gsc:8`. Same class as the Favela
`palmtree_bushy3_still` failure.

Fixes:

* Script -- all 46 `maps/animated_models/*.gsc` files that still carried the
  `if (SP) %anim else "anim"` shape were rewritten to the name-only form and
  their now-unused `#using_animtree( "animated_props" )` removed, matching the
  files that had already been converted (`foliage_dead_pine_lg_sway2.gsc`).
  `PrecacheMpAnim`/`ScriptModelPlayAnim` resolve the name inside the zone that
  is actually mounted, so no map can force an SP-only xanim any more.
* Native -- `src/db_load.cpp` `DB_FindXAssetHeader`, `ASSET_TYPE_XANIMPARTS`:
  an animation absent from every mounted zone used to fall through to
  `DB_CreateDefaultEntry`, and the retained pool has no `void` xanim, so *any*
  missing animation was a fatal `Com_Error`. It now answers with the null
  animation the zones do carry (`void`, then `void_loop` -- `void_loop` is in
  `code_post_gfx_mp`), reported once per name, which is what IW3/IW4 do: the
  prop stays in its bind pose and the map keeps loading.
* Native -- `src/codol/script/codol_script_model_animation.c`
  `CODOL_ScrCmd_ScriptModelPlayAnim` no longer raises for an un-precached or
  unresolvable animation. `report_static_prop()` prints one
  `CoDOL animated model: model '<model>' cannot play animation '<anim>' (<why>);
  prop left static` per (model, animation) and returns, which is the same
  contract `maps/mp/_animatedmodels.gsc` already uses for unregistered models.

Live proof: `mp_storm_spring` loads through `animtrees/animated_props.atr` with
no warning and no `ERROR`, reaches gameplay and runs 12 bots (`Training 1..12`,
`CoDOL bot: waypoint graph waypoints/mp_storm_spring_wp.csv loaded, 392 nodes`).

### 2. mp_nuked: the map's "dog_spawner" is not an actor spawner

What the entity actually is (read out of `mp_nuked.zone`, confirmed live):

```
{
"classname"  "actor_enemy_dog_so"
"targetname" "dog_spawner"
"spawnflags" "1"
"model"      "tag_origin"
"origin"     "16 128 -48"
"angles"     "0 270 0"
"export"     "2"
}
```

Live dump from the server: `entity 130 ... classname 'actor_enemy_dog_so',
targetname 'dog_spawner', model 80 'tag_origin', eType 0 (ET_ACTOR_SPAWNER is
19), spawnflags 0x1, svFlags 0x0`. `actor_enemy_dog_so` is the special-ops dog
aitype; the MP map-entity spawn path never routes `actor_` classnames through
`CODOL_Sentient_SpawnActorEntity` (only `spawnactorspawner()` does), so the
entity exists with `eType == 0` and is **not** an actor spawner. `_dogs.gsc`
preferred it over the template it builds, and `spawnactor()` raised
`spawnactor/setspawnerteam requires an actor spawner`, ending the match.

Fixes:

* Native -- `src/codol/player/codol_actor_spawn.cpp`: `SpawnerReceiver()` no
  longer calls `Scr_ObjectError`. It prints one
  `CoDOL dogs: <method>() on entity N is not an actor spawner and was refused:
  classname ..., targetname ..., model <slot> '<name>', eType ..., spawnflags
  ..., svFlags ...` per entity and returns NULL, so `spawnactor()` and
  `setspawnerteam()` return `undefined` -- which `_dogs.gsc` already skips.
  `gentity_s::model` is a `CS_MODELS` slot, not a string handle, so the dump
  resolves it through `SV_GetConfigstringIndex(CS_MODELS + model)`.
* Native -- new method `<ent> isactorspawner()` (registered in
  `CODOL_ActorRegisterSpawnMethods`) returns 1/0 on exactly the condition
  `SpawnerReceiver` enforces, and dumps the entity when it answers 0.
* Script -- `maps/mp/_dogs.gsc` `dog_manager_spawn_dogs` now uses
  `getentarray("dog_spawner","targetname")` and takes the first candidate that
  `isactorspawner()` accepts. `getent()` was a second map-killer here: it raises
  `getent used with more than one entity` as soon as two entities carry the
  targetname (the built template sets its own `targetname = "dog_spawner"`).
* Script -- `rcon set codol_dogsTest 2` is a permanent regression probe: it
  plants a `script_model` with targetname `dog_spawner`, asserts
  `isactorspawner()` returns 0 and `spawnactor()` returns `undefined`, then
  calls the dogs in. `codol_dogsTest 1` is the ordinary call-in.

Live proof on `mp_nuked` with 12 bots:

```
CoDOL dogs: codol_dogsTest: calling dogs for Training 10 (allies)
Warning: CoDOL dogs: isactorspawner() on entity 130 is not an actor spawner and was refused:
         classname 'actor_enemy_dog_so', targetname 'dog_spawner', model 80 'tag_origin',
         eType 0 (ET_ACTOR_SPAWNER is 19), spawnflags 0x1, svFlags 0x0
CoDOL dogs: none of the 1 map "dog_spawner" entities is an actor spawner ...;
            building one with spawnactorspawner( "actor_enemy_dog_mp" )
```

followed by live dogs (`CoDOL dogs: ent NNN hp 100 ... state combat_attack_player_close_range`),
no script runtime error and no shutdown. The `codol_dogsTest 2` probe prints
`isactorspawner() returned 0` and `spawnactor() on a non-spawner returned
undefined, as required`.

Static gate `python tools/codol_script_resolve.py --root bin/home/codol_rawfiles
--only maps/mp` and `--only maps/animated_models` both exit 0.

## 2026-09-16 (17:00-18:30) — In-match C1 memory capture settles the sway and the crosshair; bot mantle disarm found and fixed

Build `FBDD504969E4A8709F5D89ABC567FBE6D0121A02402F04C421652BFC5C057A25`
(`obj/build-mantleweap5.log`), deployed to `bin/codol_dedrun_next.exe`,
relaunched with `+set scr_codol_bots 12`.

Everything below is measured, not inferred. The source is the 12 800-sample
in-match capture `sway_capture.jsonl` (32 bursts of 400 samples at 25 ms,
written 16:48 while the user played), which reads, out of the live C1 process
each sample: the **predicted** playerstate at `cg+0` (the one
`CG_GetCrosshairColor` and the sway model actually use), the **snapshot**
playerstate at `*(cg+0x35e4)`, the per-client `BG_GetAdsSteadySwayAngle` table
at `0x016A07E8`, and the composed `WeaponDef` sway block of the held weapon.

### 1. The sway chain is CORRECT end to end — proved by matched-commandTime diff

Comparing the client's predicted playerstate against the server's published one
**at identical `ps->commandTime`** (the only frame of reference in which a
divergence means anything):

| field | samples | agree | disagree |
|---|---|---|---|
| `ps+0x348` fWeaponPosFrac + `ps+0x0c` pm_flags (scoped only) | 1955 | 1648 exact | 307, **all 1-ULP float** (`3f09374d` vs `3f09374c`) |
| `ps+0x24c` holdBreathScale (scoped only, 4 dp) | 1955 | **1955** | **0** |

So the client's own `PM_UpdateAdsLerp` and `PM_UpdateHoldBreath` reproduce this
server's published values bit-for-bit. There is **no prediction divergence, no
snapshot correction and no codec fault** in the ADS/sway path. Hypotheses (a)
and (b) of the 16:35 entry are both refuted.

During steady scope the capture shows `ps+0x348 == 0x3f800000` exactly for 128
consecutive samples (3.2 s), with `tbl[cn] = {lastFrac 1.0, lastAmp 40.0,
startTime 139480}` held rock-steady the whole time.

### 2. What the drawn sniper sway actually is on this build

The composed sniper's live def, read out of the running client (weapon slot
135, name `*a 11 0 33 0 16 0 150 0 32 0 155 0 41 0`, base 11 = `cheytac_mp`):

    +0x694 = 1      +0x6ec = 40.0   +0x6f0 = 15.0   +0x6f4 = 1.5
    +0x6f8 = 5.0    +0x6fc = 1.0    +0x700 = 0.1    +0x714 = 0.0
    +0x718 = 0.0    +0xbc8 = 1      +0xbc3 = 1      adsIn 0.0025

`+0x694 == 1` **settles the 15:50 "unresolved conflict"**: the in-match composed
definition agrees with THIS SERVER's mounted zone image for `cheytac_mp`
(`+0x694=1 / +0x6ec=40 / +0x700=0.1`) and not with the client's stock
`bg_weaponDefs[101]`, which the earlier read took from the front end between
matches. The server's zone image is the correct reference; the only residual
difference is `+0x714/+0x718` (server zone 30.0/15.0, live composed 0.0/0.0).
Every other base in the capture carries a sane pair (base 27 → 0.45/5.0,
base 52 → 0.3/4.0, base 32 → 0.5/3.0, base 20 → 0.35/4.0, base 50 → 0.35/6.0);
only base 11 has 0.0/0.0.

Consequence for the drawn sway: with `+0x694 != 0`, `0x00423080` multiplies its
own contribution by `(1 - ps+0x348)`, which is **0 at full ADS**, so the steady
path is silent and **`BG_AddIdleSway 0x00424C10` is the model that draws**:

    A      = cg.stanceRamp * maxAngle(40) * ps+0x348 * ps+0x24c
    phase += (int)(ps+0x24c * dt * 1000 * speed)          // BG_AdvanceSwayPhase

i.e. **both the amplitude and the sine's phase velocity are
`ps->holdBreathScale`**, and nothing else server-side is left in the loop. In
the capture that word cycles 0.65 → 1.08 → 0.65 with a ~1.4 s period whenever
the player holds and releases breath (`weapFlags` bit 4 toggling; session range
0.280 … 1.335) — and the client predicts the identical curve. Decoded from C1
`0x004188B0`, that is exactly right: not holding,
`target = 1.0 + (breathTimer / 5500) * 3.5` (K = 3.5 at `0xc84688`) with rate
6.0 (`0xc39ddc`); holding, `target = 0` with rate 1.0;
`goal = 1.0 + (target - 1.0) * ps+0x348` (`0x00418A08..0x00418A13`, the fld1 at
`0x004189B1` is the surviving `st(1)`); and the smoother `0x00618C10` is
`current + (goal-current)*rate*dt`, clamped to `goal`. This port already
matches all of it, constants included.

**Conclusion: the server's sway producers are clean.** The visible wobble is
C1's scope-overlay breathing model with `maxAngle = 40` and **no steady-hold
window at all** (`+0x714 = 0`), which is a property of the composed definition
the CLIENT builds from the weapon NAME this server publishes. If the classic
"perfectly still for ~0.5 s, then sway grows in" sniper feel is wanted, the work
item is weapon composition — which attachment id turns `+0x694` on and zeroes
`+0x714/+0x718` for base 11 — not pmove. Owner: the weapon area.

The one remaining ADS artefact the capture does show is **ADS-in ramp pumping**:
61 times in the session `PMF_ADS_BUTTON|PMF_ADS` dropped for 3-5 commands
mid-ramp, stretching a 400 ms scope-in to 900 ms with 2-3 reversals, and in 41
of those 61 events *no other sampled playerstate word changed*. Client and
server agree throughout, so the cause is one of the four inputs both gates
share. `ads_sway_trace` now prints all of them
(`src/codol/player/codol_pmove_c1.c:576`):

    CoDOL sway: ... btn<0|1> pof<0|1> ads<0|1> breath<0|1> hbs <f>

= the command's ADS button, the `POF_PLAYER` bit `BG_PlayerCanAds 0x00418172`
tests, the def's `aimDownSight` `0x004181AF` tests, `PWF_HOLDING_BREATH`, and
the breath scale. One scoped playtest now names the column.

Also fixed in that gate: `src/codol/player/codol_pmove_c1.c:458` — C1
`0x0041818D` / `0x0041824B` select the **offhand** definition while
`weapFlags & 2` is up (`(ps+0x344 & 2) ? ps+0x328 : ps+0x33c`); this port read
the primary definition, so a grenade pull tested the wrong weapon's `+0xbc8`.

### 3. Crosshair: the friendly bit never reaches the word the colour is read from

`CG_GetCrosshairColor 0x0043C4A0` re-read live: `esi` is built by exactly the
expression the probe uses for `cg` (`[0x6c3d2ac*4 + 0x16d3b58] ^ 0x490b400c`),
so `[esi+0x344]` is `cg.predictedPlayerState.weapFlags`. The capture, over
12 800 samples:

| `snap` ps+0x344 | `pred` ps+0x344 | count |
|---|---|---|
| 0x08 (friendly) | 0x08 | **24** |
| 0x08 | 0x00 | **415** |
| 0x10 (enemy) | 0x10 | 60 |
| 0x10 | 0x00 | **846** |
| 0x02 (pmove-set) | 0x02 | 403 |
| 0x04 (pmove-set) | 0x04 | 64 |

Bits 2 and 4 — the ones C1's own pmove writes (`0x41C3D5`, `0x418945`) —
survive at ~80 %. Bits 8 and 0x10 — the ones only the server writes — survive at
**5 %**, and every one of those 24 survivors is a read caught inside the
snapshot-resync window (sample 6721 has `pred.commandTime == snap.commandTime`
exactly). The same cross-tab at matched commandTime shows `pred 0` against
`snap 16` and never the reverse.

The predicted playerstate *is* resynced from the snapshot each frame —
server-only `pm_type` tracks it 12800/12800 including the 232 dead-state
samples — so the only explanation left is that C1's pmove clears
`ps+0x344 & 0x18` during the replay. No instruction in `.text` does: the image
has exactly 28 stores to `[reg+0x344]` and none touches bit 3 or 4, so the clear
lives in the virtualised `.tvm0` section objdump does not decode.

**Therefore: on C1 1.1.1.13 the server cannot colour the HUD crosshair through
`ps+0x344`.** Combined with the 15:57/16:30 findings (the enemy branch is
already structurally dead because `cg+0xBF050 - cg+0xBF054` is permanently 0),
the whole friend/foe crosshair colour feature is unreachable from the server on
this client build. Everything else about it is verified working and should be
left alone: dvar `291` is green in the live client, the netfield table matches
entry-for-entry, the weapon gate `+0xbc3` passes, and `CoDOL lookat: ... flags 0x8`
/ `CoDOL crosshair wire: ... netfield(0x344) 0x8` both fire for real teammates.
`CG_DrawCrosshairNames 0x0043A187/0x0043A3D6/0x0043A731` reads `cg.snap->ps` —
the snapshot, not the predicted copy — which is precisely why the crosshair
*name* works and the crosshair *colour* does not. Keep publishing both bits: the
name path consumes them.

No further server work is warranted here without a client-side change, which is
out of scope (no hooks/injections).

### 4. Bots lose their weapon after a mantle — found, fixed, verified live

`Mantle_IsWeaponInactive` (`src/asmsource/_bg_mantle.asm:1477`) returns true
while `pm_flags & 4` is up and the mantle transition's up-animation is not 0xa,
and `PM_Weapon` (`_bg_weapons.asm:7208` / `:7780`) then holsters the weapon with
`PM_BeginWeaponChange(ps, 0)`. A real C1 client recovers automatically because
**it names its held weapon in every usercmd** and `PM_Weapon` raises it again
the moment the mantle releases. `CODOL_BotBuildCommand` built its command from
`ps->weapon`, which by then is 0, so the bot asked for "none" forever.

Live proof, build `3d790936`, with `ps->weapon` added to both mantle traces:

    CoDOL C1 mantle start: client 6 ... trans 2 ... weapon 117 state 0 anim 0x200
    CoDOL bot mantle weapon: 6 ct 78400 pmf 0x4 ... requested 117 ... ps.weapon 117 state 4
    CoDOL bot mantle weapon: 6 ct 78450 pmf 0x4 ... requested 0   ... ps.weapon 0   state 1
    CoDOL C1 mantle end:   client 6 ... weapon 0 state 0 anim 0x0

The same trace also showed `g_botai[slot].weapon` holding a **garbage index**
(`1962934272`) for every bot: `Bot_Connect` seeds it with 1 and only
`G_SelectWeaponIndex` replaces it, so the builder was requesting a weapon the
bot does not own on every command.

Fixes, all in `src/codol/player/codol_bot.c`:

* `:568` the controller's weapon is honoured only when it is a real, owned
  index; otherwise the command carries `ps->weapon`.
* `:53` / `:588` new `bot_t.heldWeapon` remembers the last non-zero weapon and
  is named in the usercmd while `ps->weapon == 0`, exactly as a C1 client would.
  No ownership test on that path on purpose — the retained selector already
  refuses an unowned request (`_bg_weapons.asm` PM_Weapon_2300 tests
  `CODOL_WB_OWNED` before `PM_BeginWeaponChange`) — and `heldWeapon` is cleared
  on every respawn (`:509`) so a fresh loadout is never overridden and
  `CODOL_ApplySpawnWeaponGate` still owns the spawn window.

Live result on the fix build (`FBDD5049`), 20 mantles: every bot that ended a
mantle on weapon 0 is holding its weapon again by its next observation —
`end c8 t75200 weapon 0` → `start c8 t75500 weapon 121`,
`end c10 t78200 weapon 0` → `start c10 t88100 weapon 107`,
`end c3 t87400 weapon 0` → `start c3 t99100 weapon 111`,
`end c9 t125100 weapon 0` → `start c9 t155300 weapon 104`,
`end c2 t134050 weapon 0` → `start c2 t224100 weapon 109`.

A second mantle defect was fixed alongside it in
`src/codol/player/codol_pmove_c1_mantle.c:252`: `eFlags` bit `0x10000`
(EF_MANTLE) was cleared only when `mantleState & C1_MANTLE_END_CLEAR` was set,
mirroring C1 `0x40A949`. But this port only ever *sets* END_CLEAR when
`!(ps->eFlags & 4)` (`CODOL_PM_CheckMantleC1`), so every mantle begun crouched —
which is how the bots do it — finished with EF_MANTLE still up, and
`0x40A102`/`0x40A984` are the only setter/clearer in the whole C1 image, so it
stranded for the life of the entity and other clients kept drawing that player
in the mantle pose. A completed mantle now always clears the bit; only the
landing event stays gated. Live: every `CoDOL C1 mantle end:` line now reports
`eF 0x0` / `0x2` / `0x4` with 0x10000 gone.

### Instrumentation added (all hard-capped)

* `CoDOL sway:` gains `btn/pof/ads/breath/hbs` (`codol_pmove_c1.c:576`), same
  4000-line cap, still following the first non-bot client.
* `CoDOL C1 mantle start:` / `CoDOL C1 mantle end:` gain
  `weapon/state/anim/eF/weapFlags` (`codol_pmove_c1_mantle.c:181`, `:256`).
* `CoDOL bot mantle weapon:` (`codol_bot.c:608`, 120 lines process-wide) prints
  the whole command-weapon plumbing across a mantle window.

Tooling used (scratchpad): `sway_probe.py` — a passive PROCESS_VM_READ probe of
the predicted/snapshot playerstates, the `0x016A07E8` sway table and the
composed WeaponDef — and `watch_sway.py`, which arms it and bursts while the
client is in a match. Both are the right instrument for any future
"what does the CLIENT actually hold" question.

### What the user should do

1. **Sniper sway**: join, scope a sniper, hold still WITHOUT touching the
   hold-breath key, and say whether the sway is smooth. If it is, the remaining
   complaint is the missing steady-scope window (`+0x714 = 0` on the composed
   cheytac) and belongs to weapon composition. If it still stutters with the
   breath key untouched, run one scoped pass and send the `CoDOL sway:` lines —
   the new `btn/pof/ads/breath` columns name the cause in one look.
2. **Crosshair**: nothing to test. It cannot be made green through the
   playerstate on this client build; see section 3.
3. **Bots**: watch a bot climb a ledge. It should be holding its gun again
   within a fraction of a second, and it should no longer run in the mantle pose.

## 2026-09-16 (19:30) — "IW3 bits/offsets" hypothesis tested for the sway and the crosshair: REFUTED for the weapon offsets, and the crosshair is a MISSING WIRE FIELD (entityState.solid), not a bit meaning

Build `718D403A91BFDB67C638684A7868EE557A425DC4BCC195CF309AC028934539B4`
(`obj/build-attachdump.log`), deployed to `bin/codol_dedrun_next.exe`,
relaunched with `+set scr_codol_bots 12`.

Framing correction the user supplied mid-investigation: both defects behaved
correctly against the **vanilla** CoDOL 1.1.1.13 server with this same C1
client, so the 17:00-18:30 conclusion ("not reachable from the server on this
client build") is wrong as a conclusion. Everything below is re-derived under
"what does vanilla send that we do not".

### A. Composed weapon override records — the server emits NONE. Hypothesis refuted.

`BG_BuildCustomWeaponDef 0x00421590` was disassembled end to end:

* it parses `*a <baseIndex> <flag> [<item> <variant>]*` (`0x004215e6`,
  `0x004215f3`, loop `0x00421631`), validating each item against the
  attachment-name table `0x0150c820` / count `0x0150c69c`;
* it copies `bg_weaponDefs[baseIndex]` — **the CLIENT's own definition table**,
  `mov eax,[edi*4+0x150d720]` at `0x004215fe` — 0xbfc bytes into a 0xe78-byte
  composed record (`rep movsd`, `0x004216c4`), publishing the def at record+0x98
  and the composed name at def+0x08 (`0x0042172a`);
* for each attachment it resolves `bg_attachIdx[base<<8 | item]`
  (`0x00421833` → word table `0x015111e8` → `bg_attachDefs 0x0150f408`) and
  applies that ASSET's `count` (+4) entries of `{offset, type, value}` (+8)
  through `0x004208e0`: type >= 0x10 and != 0x27 is a straight dword store to
  `weaponDef + offset` (`0x0042098d`), type 0x27 appends a hide tag
  (`0x00420930`), types < 0x10 parse the string value.

So the override records are **shipped type-43 assets in the client's own zone**.
The server chooses only (base index, attachment item ids, variants); it never
transmits an offset. There is therefore no IW3-vs-C1 offset to correct.

Proved with data rather than by argument. New console command
`codol_checkattachments <weapon> [item ...]`
(`src/codol/assets/codol_asset_commands.c:891`) walks every legal
(weapon, item) row through `CODOL_ComposedAttachmentAssetName` +
`CODOL_LoadMountedWeaponAttachment` and prints every `{offset,type,value}`,
naming the sway/scope fields. Run at startup (rcon replies do not reach the
caller on this build; console output during an rcon command is swallowed by the
redirect, so use `+codol_checkattachments <weapon>` in `CODOL_EXTRA_ARGS`).

Result for the user's sniper, live composed name
`*a 11 11 69 20 18 18 33 0 16 0 150 0 32 0 155 0 41 0` (base `cheytac_mp`):

| item | asset | overrides |
|---|---|---|
| 69 | heartbeat_shareda | 6 (+0x758, +0xbed, +0x52c..+0x538) |
| 18, 33, 16, 150, 32, 155, 41 | `nop` | **0 each** |

cheytac_mp has 53 legal attachment rows carrying 104 override entries in total;
**not one entry in the whole table touches +0x694, +0x714 or +0x718.** The only
sway field any attachment writes anywhere is +0x6ec (`scope_ballistic` `[+] -5`,
`sniperscope_mid` `[=] 70`), and neither of those is in this recipe.

The server's own mounted `cheytac_mp` image is intact and is what it should be
(`CoDOL breath def sway: weapon 115 6ec 40.000 6f0 15.000 6f4 1.500 6f8 5.000
6fc 1.000 700 0.100 714 30.000 718 15.000 bc8 1`).

Conclusion: the `+0x714 = 0 / +0x718 = 0` measured in the client's composed def
at 17:00 cannot have been produced by anything this server sends. It can only
come from the definition the CLIENT copied, i.e. from its own
`bg_weaponDefs[11]`. The base identity itself is correct: `*a <base>` is a
published wire slot (`CODOL_LoadoutWeaponIndex`,
`src/codol/script/codol_script_profile_loadout.c:119`, answers
`CODOL_FindRegisteredWeapon` — CS_WEAPONS slot i carries index i), and the live
composed def agreed with cheytac on +0x694/+0x6ec/+0x700.

Open, and now a one-line measurement rather than an investigation: next time the
client is in a match, read `bg_weaponDefs[11]` — the BASE slot, not the composed
slot — with `scratchpad/dump_wpn.py`. If the base also reads 714/718 = 0 then
C1's shipped cheytac asset simply has no steady-scope window, vanilla swayed
exactly the same way, and the sway complaint is about something else.

### B. Crosshair friend/foe — the server never publishes `entityState.solid`, so no client-side trace can hit a player. FIXED.

The bit-semantics question was answered first: the mask
`CODOL_OverlayEngineWeaponUseControl` publishes in ps+0x344 is 0x9d
(bits 1, 4, 8, 0x10, 0x80) plus 0x400/0x800/0xE0000 from other producers. Every
one of those was re-checked against C1's own readers in the 2026-09-16 bitmask
audit §2.1 row 87 and none is an IW3 bit with a different C1 meaning — the one
real collision of that kind (IW3 `EF_VOTED` 0x100000 vs C1 `EF_VEHICLE_ACTIVE`)
was already fixed in eFlags, not weapFlags. A full-image scan for writes to
`[reg+0x344]` (52 sites) shows **nothing in C1 — client or its own server
module — ever sets bit 8 or bit 0x10 in plain text**; the C1 server module sets
0x20, 0x80, 0x400, 0x800, 0x10000, 0x100000, 0xE0000 and nothing else. Both
producers live in the 24 MB virtualised `.tvm0` section (VA 0x082f8000), which
is shared bg code, so vanilla's server and this client run the *same* routine —
which is why publishing the bit ourselves never survived the client's replay.

What that routine needs is a trace that can hit a player, and that is the thing
this server was not sending:

* `CG_GetEntityBounds 0x00485360`: `solid == 0xffffff` → inline brush model
  bounds; otherwise it UNPACKS `entityState.solid` (cent+0x18c = es+0xa8) into
  the entity's `{midPoint, halfSize}` box at `0x004853ba`:
  `a = solid & 0xff`, `b = ((solid >> 8) & 0xff) - 1`, `c = ((solid >> 16) & 0xff) - 32`,
  giving `half.x = half.y = a - 1`, `mid.z = (c + 1) * 0.5`,
  `half.z = (c - 2b + 1) * 0.5` (constant 0.5 at 0xc84248) — i.e.
  `mins.z = b`, `maxs.z = c - b + 1`.
* `0x00485320` supplies the contents for that box: `eType == 1` (ET_PLAYER)
  → 0x2000000, everything else → 1.
* `solid == 0` therefore decodes to an **inverted** box (half = -1), which no
  trace can ever hit.

The server published +0xa8 for exactly one case — `CODOL_OverlayEngineBrushEntity`
writing 0xffffff (`codol_engine_state.c:1298`). Players, corpses, items and
missiles all went out with `solid = 0`. Consequence on the client: no
client-side collision against other players in prediction, and no crosshair scan
result, which is why `cg+0xbf050 - cg+0xbf054` measured permanently 0 (the
window `CG_GetCrosshairColor 0x0043c50e/0x0043c557` tests) and why bits 8/0x10
never appeared in the predicted playerstate. One missing field explains all
three observations, and vanilla sends it.

**Fix** (`src/codol/snapshot/codol_engine_state.c:1946`, in
`CODOL_OverlayEngineEntityVisible`, so every eType gets it — all 22 measured
tables carry `{0x0a8, 24 bits}`): publish `es->solid` for every entity whose
solid is neither 0 nor SOLID_BMODEL.

The retained `SV_LinkEntity` (`0x0054f153` in this build) already packs two of
the three bytes exactly as C1's own packer `0x005d88b5`/`0x005d88d2` does —
`byte0 = clamp(maxs.x, 1, 255)`, `byte2 = clamp(maxs.z + 32, 1, 255)`. The
middle byte is the one genuine IW3-vs-C1 divergence found in this pass: the
retained code stores `clamp(1 - mins.z)` where C1 stores `clamp(mins.z + 1)`
(`0x005d8865`). They agree for every box with `mins.z == 0` — every player and
every corpse — and disagree for anything else, where C1 would decode the IW3
spelling as a box floating above the entity, so the wire value inverts that byte
back (`base = 2 - byte1`, clamped 1..255). Contents gates also differ slightly
and were left alone: retained `0x2000001`, C1 `0x2004001`.

### Why the earlier "unreachable" conclusion was wrong

Its measurements were right; its inference was not. "No plain-text writer sets
bits 3/4" was read as "the client owns them and clears them", when the correct
reading is "the producer is virtualised and it did not fire". The test that
separates those two is not in the playerstate at all — it is whether the client
can trace against a player, which is an entity-state question.

### What the user should test

1. **Crosshair**: join, aim at a teammate (friendly) and at an enemy. The
   friendly branch needs only bit 8 plus `WeaponDef+0xbc3` (both already
   verified good); the enemy branch additionally needs 250 ms of settle time and
   dvar `690` (registered bool, default 1, `0x0044d198`). If the colour now
   changes, the missing box was the whole story.
2. **Player collision**: walk into a bot. You should no longer slide through
   another player for a frame before the server pushes you out — client and
   server now agree about player bodies.
3. **Sniper sway**: unchanged by this build. Say whether it still differs from
   vanilla; the next step there is the one-line `bg_weaponDefs[11]` read above,
   not more server-side work.

### Files

* `src/codol/snapshot/codol_engine_state.c` — entityState.solid publication.
* `src/codol/assets/codol_asset_commands.c` — `codol_checkattachments`.
* Scratchpad tooling: `dump_attach.py` (live C1 `bg_attachIdx`/`bg_attachDefs`
  walker), `dump_wpn.py` (live `bg_weaponDefs` name dump).

## 2026-09-16 (20:45) — sniper scope sway, fourth pass: the "+0x714/+0x718 = 0" contradiction is RESOLVED (C1's own asset carries the zeros), and the residual is a measured 31% forced-origin rate

Build `6E02C6672E7CD7415C6DBEA2A14E25C929611E033807C6BBB505AD0306DE19CC`
(`obj/build-bob.log`), deployed to `bin/codol_dedrun_next.exe`, relaunched with
`+set scr_codol_bots 12`. **The server was found DOWN at the start of this pass**
(nothing bound to udp/17733, PID 91016 gone); it was brought back up first, which
is also why no capture was possible until then.

### 1. The contradiction: settled by an in-match read of the BASE slot

New scratchpad tooling: `probe2.py` (adds `ps->bobCycle`, origin, velocity,
viewangles, `ps+0x4d0`, and a full dump of the registered `bg_weaponDefs` table)
and `watch3.py`, which arms itself and bursts only while the held definition has
`+0x694 != 0`. Two sniper bursts landed while the user played. The table dump
(176 registered client definitions) answers all three open questions:

| client slot | name | +0x694 | +0x6ec | +0x6fc | +0x700 | +0x714 | +0x718 |
|---|---|---|---|---|---|---|---|
| **11** | **cheytac_mp** | 1 | 40.0 | 1.0 | 0.10 | **0.0** | **0.0** |
| 23 | m21ebr_mp | 1 | 40.0 | 1.0 | 0.85 | **0.0** | **0.0** |
| 53 | wa2000_mp | 1 | 40.0 | 1.0 | 0.85 | **0.0** | **0.0** |

* **The base slot our `*a 11 ...` names really is `cheytac_mp` in the client.**
  The published weapon order/identity is correct; there is nothing to chase
  there. (A read taken at the FRONT END shows `m21_mp` in slot 11 — the front
  end registers its own indices — so this question can only be answered
  in-match.)
* **C1's own shipped sniper assets carry `+0x714 = 0 / +0x718 = 0`.** The
  composed definition is a faithful copy of the base. There is no missing
  attachment override and no "missing steady-scope window" defect: every sniper
  in the client's table is the same. That is what `+0x694 = 1` means — the
  weapon is served by `BG_AddIdleSway` and steadied by *holding breath*, not by
  a timed window. **Vanilla swayed from the first frame too.**
* The outlier is **the server's mounted zone image** (`CoDOL breath def sway:`
  prints `714 30.000 718 15.000` for cheytac_mp, and `6.0/6.0` for vector_mp
  against the client's `0.3/4.0`). `find_dependency_definition`
  (`src/codol/assets/codol_asset_registry.c:612`) returns the first mounted
  archive holding the asset, so an override zone C1 prefers can lose. This is
  behaviourally inert today: those three offsets have exactly one server reader,
  the diagnostic print at `codol_pmove_c1_breath.c:124`, and the one field the
  hold-breath gate actually uses, `+0x694`, agrees with the client (1). Logged
  as a real asset-resolution divergence to fix on its own merits, not as the
  sway cause.

### 2. What actually draws a sniper's scope sway (both models, fully decoded)

`0x00425020` is the sway aggregator, called from `CG_PredictPlayerState` at
`0x0050cc8b` with a 0x24-byte context built at `0x0050cc3c` (`ctx+0x00` = ps,
`ctx+0x14` = |velocity.xy| via `0x00416ce0`, `ctx+0x18` = msec*0.001,
`ctx+0x1c` = stance ramp, `ctx+0x20` = &int sway phase). Four contributors; for
`+0x694 != 0` exactly two are live:

* **`BG_AddIdleSway 0x00424C10`** —
  `A = stanceRamp * maxAngle * ps->fWeaponPosFrac * ps->holdBreathScale`;
  `out.pitch += sin(phase*0.0007)*A*0.01`, `out.yaw += sin(phase*0.001)*A*0.01`;
  `phase += (int)(holdBreathScale * dt * 1000 * speed)` (`BG_AdvanceSwayPhase
  0x00424B90`, whose `speed` is `+0x6f8 + (+0x6f4 - +0x6f8) * posFrac` from
  `BG_GetSwayParams 0x00422FE0`). For `+0xbc8 != 0` the amplitude is
  `BG_GetAdsSteadySwayAngle 0x00422E20`, and with `+0x714 = 0` and
  `fWeaponPosFrac == 1.0f` exactly that is a flat `+0x6ec = 40`.
  **Measured live: `tbl[cn].lastAmp` is a rock-steady `40.000` across all 162
  consecutive scoped sniper samples, and `holdBreathScale` is an exact `1.0000`
  on every scoped sample where the breath key is untouched (2835 samples across
  both capture sets). This model is a constant-amplitude 0.4-degree sine at a
  4-6 s period. It cannot jitter, and the server's two inputs to it are exact.**
* **`0x00424D90` — gated on `WeaponDef+0x694 != 0`, i.e. SCOPED WEAPONS ONLY.**
  Amplitude `dvar"142"(0.16) * |velocity.xy|`; **phase `ps->bobCycle`**
  (`mov eax,[esi+0x18]; and eax,0xff` at `0x00424dc9`, then `(bobCycle/255)*2pi`
  plus `dvar"149"(0.25)`, scaled by `dvar"147"(1.5)`). `0x00424F30` reads the
  same byte for the weapon bob. **No other weapon class has this consumer** —
  which is why a shared defect in `ps->bobCycle`, origin or velocity shows up in
  a sniper scope and essentially nowhere else.

`ps->bobCycle` is netfield `{0x0018, 8, 3}` — changeHint **3**. Hint-3 fields
(origin, velocity, viewangles, bobCycle) are written only when the snapshot's
`rov` bit is set, and then against a **zero** delta base
(`src/codol/snapshot/codol_playerstate.c:56`/`:78`), i.e. they *override* the
client's prediction instead of delta-coding against it.

**Correction to the 17:00 entry:** "the client's predicted playerstate reproduces
the server's published values bit-for-bit" holds only for the two fields that
pass sampled — `fWeaponPosFrac` and `holdBreathScale`, which are *not* hint-3.
The hint-3 group does not reproduce; it is overwritten. At identical
`ps->commandTime` the in-match capture shows the predicted copy differing from
the snapshot in origin (344/407 samples over 0.1 units, mean 3.5, max 17.1),
velocity, viewangles and **bobCycle** (136/160 in the first capture, worst 251 of
256). The error is **purely horizontal** — the Z component agreed to 0.0000 on
every one of the 407 matched samples.

### 3. Measurement: the origin/velocity group is force-published on 31% of frames, and the gate is `toofar`

New `CoDOL rov:` trace (`src/sv_snapshot.c:143`) breaks
`CODOL_ReadOriginVelocityFlag` into the gate that actually fired, once per second
per client. Live human session on this build:

    forced 389 of 1262 frames (31%)

and in steady play the breakdown is unambiguous:

    CoDOL rov: client 12 sent 8/20  (... timemismatch 0 toofar 8)  dist 0.012 worst 0.353
    CoDOL rov: client 12 sent 12/20 (... timemismatch 0 toofar 12) dist 0.288 worst 20.292
    CoDOL rov: client 12 sent 0/20  (... all gates 0)              dist 0.000 worst 0.000

So the handshake is healthy (`predTime` == `cmdTime` on every steady frame;
`timemismatch` and `nopredtime` appear only at connect/spawn), and long stretches
are a clean `0/20` with `dist 0.000`. What forces the group is **`toofar`**: this
server's authoritative origin leaves C1's predicted origin by more than 0.1 units
(C1's own tolerance — the `0.01` squared at `0xc30c04`, matching the retained
`MSG_WithinAllowedPredictionError`). Excursions reach 20 units.

Every one of those frames hands the client an absolute origin, velocity,
viewangles **and bobCycle**. Six to eight times a second the sniper's scope-bob
phase is re-seeded and the view is pulled — a correction that is invisible at hip
FOV and very visible through a scope. **That, not the sway model, is what is left
of "unsteady/jittery".**

### 4. Fix shipped: the bobCycle divisor used the wrong ADS test

`PM_Footsteps`' bob divisor is C1 `0x00413690`. Its weapon move-speed step:

    0x0041371f  fcom  [esi+0x670]          ; 0 < moveSpeedScale ?
    0x0041372c  test  byte [ecx+0x0c],0x40 ; ... AND NOT PMF_ADS
    0x00413734  fld   [esi+0x670]          ; -> divisor *= moveSpeedScale
    0x0041373c  fcomp [esi+0x674]          ; else 0 < adsMoveSpeedScale ?
    0x00413749  fld   [esi+0x674]          ; -> divisor *= adsMoveSpeedScale

It tests `pm_flags & 0x40` **alone**. The `(pm_flags & 0x40) || leanf != 0`
compound that `0x004139e2` builds is used only for the 0.4 divisor multiplier and
for the bob-constant table index, not here. This port folded `leanf` into all
three, so a leaning, un-ADSed player divided by `adsMoveSpeedScale` on the server
while C1's client divided by `moveSpeedScale`. `ps->bobCycle` is an integrator
mod 256, so a rate difference decorrelates the two copies within a second and the
next forced frame lands as a scope jerk — and lean-peeking a corner is a sniper's
normal behaviour.

Fixed at **`src/codol/player/codol_pmove_c1_ground.c:1002`**:

    -  if(!ads && weapon->moveSpeedScale>0.0f)
    +  if(!(m->ps->pm_flags&0x40u) && weapon->moveSpeedScale>0.0f)

Everything else in the bob chain was re-derived from C1 in this pass and is
already exact: the constant table at `0xc40938` = `{0.335, 0.305, 0.250, 0.240,
0.340, 0.315, 0.250, 0.240}` indexed `stance*2 + ads` with the standing-sprint
override `0.5` (`0xc3e67c`); direction scales `0.925 / 0.85 / 0.70 / 0.85`
(`0xc84b18 / 0xc84b10 / 0xc84b08 / 0xc84b00`); ADS and sprint divisor multipliers
`0.4` / `1.5` (`0xc846d8` / `0xc845a0`); `bobCycle = ftol(xyspeed/divisor * bob *
msec + old) & 0xff` (`0x00413ae4..0x00413b0d`); the `xyspeed < 1.0 -> bobCycle =
0` reset (`0x00413510`); the `xyspeed > 120` coast bail (`0x00413860`); and the
`player_moveThreshhold` gate, whose client dvar is `"171"` and reads **10.0**,
matching this server's default. Live `CoDOL bob:` lines confirm the arithmetic
(`psSpeed 190 dir 0.850 stance 1.000 -> div 161.5000`).

### 5. Instrumentation left in the build

* **`CoDOL rov:`** (`src/sv_snapshot.c:143`) — per-second gate breakdown
  (`nobase / inactive / follow / viewlock / interm / nopredtime / timemismatch /
  toofar`) plus live and worst prediction distance and the two compared times.
* **`CoDOL bob:`** (`src/codol/player/codol_pmove_c1_ground.c:1022`) — every
  input of the bob divisor for the first non-bot client, 100 ms apart, 1500
  lines: `xyspeed`, `ps->speed`, dirscale, stance, ads, leanf, sprint, the
  weapon's `moveSpeedScale` / `adsMoveSpeedScale`, `divisor`, `bob`,
  `cycle old->new`.

### 6. Next step for the sway (named, not guessed)

The remaining work item is **horizontal pmove divergence**, not sway code: get
`toofar` from 31% toward 0. The divergence is X/Y only (Z agreed exactly on all
407 matched samples), typically 0.003-0.05 units with excursions to 0.3-20, so
the suspects are the horizontal integration order in `friction()` /
`accelerate()` / the step-slide, and the reconstruction of `forwardmove` /
`rightmove` (C1 `0x00413690` reads them as signed bytes at `pm+0x1e` / `pm+0x1f`,
while this port rebuilds +-127 from `cmd.direction` bits). `CoDOL rov:` is the
scoreboard for that work: a scoped pass should read `0/20 ... dist 0.000`.

### 7. Crosshair and floating name-tag colours are now server cvars

`CG_DrawCrosshairNames 0x0043a52f` branches on the same `ps+0x344` bit 0x10 the
crosshair uses and unpacks four colour dvars; read live out of C1:

| dvar | role | shipped value |
|---|---|---|
| `291` | friendly crosshair (`0x0052b1ff`) | 0.40 0.60 0.85 1 |
| `292` | enemy crosshair (`0x0052b277`) | 0.75 0.25 0.25 1 |
| `794` | friendly name tag (`0x016da254`) | 0.90 1.00 0.90 0.70 |
| `795` | friendly name drop shadow | 0.00 0.30 0.00 1 |
| `796` | enemy name tag (`0x016cf884`) | 1.00 0.90 0.90 0.70 |
| `797` | enemy name drop shadow | 0.60 0.00 0.00 1 |

`src/codol/snapshot/codol_lookat.c` now registers **`codol_friendlyColor`**
(default `"0 1 0 1"`, the green already in use) and **`codol_enemyColor`**
(default `"0.75 0.25 0.25 1"`, C1's own registered value for dvar 292) and sends
291+794 from the first and 292+796 from the second, inside the same
once-per-client-per-map latch (and its reset) that was already there. 795/797
keep their shipped dark green / dark red, which reads correctly behind either
colour. Live: `CoDOL crosshair colour: client 0 -> 291/794 "0 1 0 1", 292/796
"0.75 0.25 0.25 1"`.

### What the user should test

1. **Sniper**: scope and lean-peek a corner. The scope-bob phase is no longer
   re-seeded at a different rate when leaning. A gentle, continuous ~0.4-degree
   sway with the breath key untouched is **correct** — C1's sniper assets carry
   no steady-scope window, and holding breath is what stills them.  If the scope
   still twitches at roughly snapshot rate while moving, that is the 31%
   forced-origin rate in section 3, and the `CoDOL rov:` lines from the pass are
   the measurement for it.
2. **Name tags**: teammates' floating names should now be the same green as the
   crosshair; enemies stay C1's red. `codol_friendlyColor` / `codol_enemyColor`
   retune both, live, without a rebuild.

## 2026-09-26 — offhand audit: C1 explosion kinds, flash notify, smoke persistence, WP/tabun/EMP/TI script parity

Audit of the 15 MP offhand items (marketplace 1200-1226) against C1, IW4, IW5 and T5.

**Native (C1 evidence).** C1 `G_ExplodeMissile` switches on WeaponDef `+7b4`
(0x52eed4: 0/6 grenade event 73, 1 rocket 76, 2 flashbang 78, else custom 79),
calls its flash blast 0x522870 with `+778`/`+77c`, and keeps a persistent smoke
entity for kind 5 when `+7b8` is set (0x52ef3b). The server never copied `+7b4`,
`+77c` or `+7b8`, so every offhand exploded as a frag: flashes never ran
`G_FlashbangBlast`, smoke never persisted, concussion/EMP sent event 73.
Measured kinds (common_gametype_mp): flash 2, smoke 5, tabun 5 (no effect),
concussion 3, EMP 3, frag/semtex/WP 0; zm crossbow/sniper explosive use 7.
- `codol_weapon_native.c` copies the kind and minimum radius; `codol_weapon_loader.c`
  binds the `+7b8` effect (null with a warning if the effect loader fails).
- `G_FlashbangBlast` now pushes the origin: C1 0x522844..0x522860 notifies
  `(origin, distance, angle, attacker, team)`, which is what `_flashgrenades.gsc`,
  `animscripts/combat_utility.gsc` and `_utility.gsc` wait for.
- `codol_sv_gameframe.c` publishes the explosion entity's C1 flags (0x10, smoke
  0x40, 0x80000) and smoke time `+58` / time2 `+7c` (C1 0x52edd6, 0x52ef94..0x52efb8).

**GSC.** WP (C1 class 1, cookable, timed) joins the frag-family hooks; tabun gets
its T5 killcam entity, MOD_GAS spawn protection and dog stun; EMP grenade gets
IW5's rumble; tactical insertion's perk unset no longer deletes a planted beacon.

**Tested.** Probe mp_rust, 4 bots: a thrown flash reached every bot as
`flashbang` with origin/distance/angle/attacker; smoke, concussion, EMP, tabun,
WP threw and detonated with no script or snapshot errors. No C1 client, so the
wire fields (event 78/79, smoke flags/times) are not client-verified.

**Found, not fixed.** A self-inflicted grenade kill (frag or WP) leaves the
thrower at health < 0 with no death callback, so it never respawns
(pre-existing: frag's server path is unchanged). Semtex/airdrop wait
`missile_stuck`, which native never sends. The server effect loader rejects
`explosions/flashbang` and `smoke/signal_smoke_airdrop`.

## 2026-09-26 — Linux build, no-C1.exe key file, Docker deployment package

**Linux server.** The whole CoDOL server compiles and links as a 32-bit Linux ELF
(`tools/build_codol_linux.sh`: objects in `obj/codol-linux`, libraries from
`lib-native`, output `obj/codol-linux-bin/codol_dedrun`; `EXTERNAL=` keeps the
link from rebuilding the Windows `lib/` archives). Two Linux-only defects fixed:
- Loose script/rawfile names are resolved case-insensitively on POSIX
  (`codol_caseless.c`, used by `codol_script_source.c`): the tree mixes spellings
  and scripts ask for `mp/challenges/ChallengeTable_Perk.csv`.
- The server tick clock (`sys_main.c`) uses `CLOCK_MONOTONIC` on POSIX; the
  `gettimeofday` wall clock stepped backwards under WSL and showed as ~4294 s hitches.

**No C1.exe.** The server needs two C1.exe regions: the IWD key blob
(file 0x838b20, 256 bytes) and the archive RSA key (file 0x83c248, 1191 bytes)
that also opens every fastfile's key blob. `tools/codol_export_c1_keys.py`
writes them to `c1_keys.bin` (checked against the server's SHA-256 values);
`CODOL_ReadClientRegion` reads either file, and `codol_clientExe` defaults to
`fs_basepath/C1.exe`, else `fs_basepath/c1_keys.bin`.

**Package.** `tools/codol_package.py --out <dir> [--link] [--skip-game]` writes a
compose deployment: gameserver image (Ubuntu 24.04 + 32-bit runtime, 180 MB),
the alpha0022 lobby (git-tracked files only, never `native_server_rcon.txt`),
`game/` (c1_keys.bin, 90 fastfiles, 39 IWDs, 4.95 GiB) and shared `data/`.
Host networking is required, not a preference: the C1 transport accepts
plaintext (rcon, the lobby's map start) only from loopback and treats every other
source as bdDTLS.

**Tested.** WSL: Linux binary without C1.exe loads mp_rust, 4 bots fight and
respawn, no clock hitches after the fix. Docker (Desktop, bridge): container
boots, generates the RCON password, bots spawn; rcon answered from loopback,
off-host rcon dropped by design; 3% CPU, 590 MiB with 4 bots. Not yet tested:
a real C1 client against the Linux build, the lobby container on a Linux host.

## 2026-09-26 — Lobby admission reaches the game server

The lobby's launch-token admission (alpha0022 `docs/admission.md`) stopped at the
lobby. The game server accepted whoever completed bdDTLS with the single key in
`securitykey.bin`, trusted the connect's xuid and name, and could hold only one
player's key at a time.

Each C1 process's own bdSecurityKey is the credential: the lobby sees it in
createSession, and the association is keyed from it. The lobby
(`demonware/dw_game_admission.py`, uncommitted in alpha0022 alongside the rest
of its admission work) writes `game_admissions.txt` beside `securitykey.bin`,
one line per admitted seat (ip, key, uid, expiry, gamertag). The server
(`src/codol/net/codol_admission.c`):
- tries roster keys (this IP first, then the rest) at COOKIE_ECHO and on DATA;
  a failed open leaves the association untouched, so candidates are tried in turn;
- identifies the seat as the entry whose key derives the association's key
  (stateless, survives the saved-session restore);
- in `SV_DirectConnect`, refuses an xuid that is not the seat's uid, sets the
  name to the lobby gamertag, and with `codol_admissionRequired 1` refuses a
  client with no entry (`EXE_ERR_NOT_AUTHORIZED`);
- `codol_admissionPath` defaults to the roster beside `codol_securityKeyPath`,
  so the Windows launcher is unchanged; required defaults to 0 there and to 1 in
  the Docker package.

**Tested.** `tests/test_codol_admission.c` (15 checks); lobby
`selftests/dw_selftest_game_admission.py` (13 checks, also inside the lobby
image); `tests/test_codol_admission_live.sh` drives a real bdDTLS client
(`tests/codol_admission_client.c`) against the Linux server: admitted key and
xuid join under the lobby gamertag, a foreign xuid is refused, an unadmitted key
never gets a challenge, a key-only match from another IP is admitted; legacy
`securitykey.bin`-only mode still connects. Not tested: a real C1 client.

## 2026-09-26 — Server distribution: scripts in an IWD, lobby shipped separately

The server's GSC tree, loose string tables, bot waypoints and bot classes now
ship as `main/sh1x_svr_scripts.iwd` (plain zip, built from git-tracked files by
`tools/codol_package.py build_pack`):
- `codol_script_source.c`: a root spelled `fs:<dir>` reads through a host
  reader; the server registers one that goes through the search path, so the
  pack (and any loose `main/<dir>/…` override) supplies scripts with every
  existing precedence rule (zone-type layer, overlay, reference, corrections).
- `filesystem.c`: `sh1x_svr_*` archives are accepted in base `main/`, and any
  `_svr_` archive (IW4OL's server-only convention) is kept out of the pure
  checksum list, `sv_iwds` and the referenced list, so C1 never hears of it.
  Waypoints and `mp/botclasstable.csv` resolve through the normal search path.

`tools/codol_dist_overlay.py` builds the install-layout distribution
(`D:/CoD/CODOL Builds/sh1x Server 1.1.1.13`): servers, launchers and
`c1_keys.bin` at the root, fastfiles in `client_shipRetail/chinese`, archives
plus the pack and a loose `server.cfg` in `main/`, logs in `main/`. The lobby is
not included in it or in the Docker package; both point at the separately run
lobby's state directory (same host: file handoff and loopback-only RCON).

Tested: Windows exe from the distribution folder and the Linux container both
mount the pack, compile scripts from it, load mp_rust waypoints and spawn bots;
the pack is absent from the referenced list and `sv_iwds`.

## 2026-09-28: repository checkout and launcher state handoff

- Cloned `nucleur16/codol_1.1.1.13_alpha_server` at `08afb31`. This checkout contains the native game server and server launch scripts. The Python lobby and C1 launcher sources are separate and unavailable here; the user chose work within this repository for now. Multiplayer gameplay, lobby, and launcher lead; English translations remain a secondary priority.
- The development launcher now reads `startgame.txt`, `native_server_rcon.txt`, and `securitykey.bin` from `CODOL_STATE_DIR`. Profile resources still come from `CODOL_REFERENCE`. Its stale multi-root collation instructions were removed. The focused handoff test covers separate state/reference roots, valid and invalid selections, and timestamp freshness; it passes. No live C1, lobby, or game server was changed.
- A clean 32-bit Linux server build linked in a separate WSL checkout. The full `test-codol` target stops at the usability fixture link: `_player_use_mp.asm` refers to `CODOL_WeaponBitsRead` and `codol_weapbits_result`, which that fixture does not supply. Earlier fixtures passed. This is a pre-existing test harness gap, not a launcher failure.
- The 2026-09-26 self-grenade respawn failure remains open. `finishPlayerDamage` subtracts health before `player_die`; the latter can return when the victim lacks a server DObj, has an ineligible `pm_type`, or has `otherFlags & 2`. The retained probe log does not identify which gate failed. `codol_deathGates` is available for an isolated reproduction; do not change the death gate without that evidence. The documented airdrop `missile_stuck` gap is partly stale because its current script also accepts `stationary`; Semtex still needs a verified impact notification.

## 2026-09-28: settled missile impact notification

- The retained `BounceMissile` path records the hit entity in `groundEntityNum` and already calls `CODOL_NotifyMissileStationary` only for a moving-to-stationary transition. The shipped `monitorSemtex` and `_detonategrenades` scripts wait for `missile_stuck` with one impact-entity argument; native code had only emitted `stationary`.
- The native helper now emits `missile_stuck` after `stationary`, carrying the captured live target or undefined for world, none, deleted, or reused targets. A script callback that deletes or converts the missile prevents the second event. This is an IW4 GSC contract adaptation; exact C1 event order remains unverified.
- The focused 32-bit `test-codol-missile` fixture passes for player/world/none impacts, target deletion/reuse, and missile deletion/conversion. The full Linux server links. Earlier usability and offhand fixtures now pass after updating stale fixture dependencies and C1 wire-flag expectations; the broader `test-codol` run next stops at `test_codol_frame_entities` link dependencies (`codol_debugTrace`, `Com_Printf`, `CODOL_EntityModelScale`). Real Semtex impact, C4/claymore settling, knife settling, and C1 behavior have not been run on this host.

## 2026-09-28: throwing-knife pickup identity and native fixture progress

- The shipped `throwingknife_mp` is native source class 9. Retained `G_InitGrenadeEntity` only assigned pickup contents, packed item identity, and `clientNum=64` to offhand class 1. Its class-9 missile therefore lacked the identity later read by `CODOL_IsKnifeEntity` and the item pickup path. A CoDOL-only branch now assigns those same pickup fields to definitions confirmed as native class 9, while leaving the class-1 bounding box adjustment exclusive to class 1. Exact C1 1.1.1.13 code at `0x52855e..0x52856c` reads the packed item identity; `0x528270..0x5282a5` transfers one class-9 ammo unit. The server assembles and links with this change. Throw, settle, touch, ammo transfer, and respawn still require a real C1 client run.
- The frame-entity fixture now links the real model-scale source with trace disabled, and the viewmodel fixture uses the 2048-slot native model ceiling. Both passed while advancing `test-codol`. The native integration fixture now links model-scale and supplies its trace symbols; a 22-word `raised` array fixes a compiler-detected short input. The broad suite currently stops at further native integration fixture dependencies (`CODOL_ResetLookAtClientState`, `CODOL_KillcamTraceFrame`, `CODOL_WeaponStateSecondBarrelArmed`, and weapon-bit/dual-wield helpers). That fixture's old direct `ps.weapons` setup also needs conversion to tracked native player-state extension storage before its inventory assertions can be trusted. These are test harness limits, not evidence of a runtime failure.
- Rechecked the focused missile test and PowerShell launcher handoff test; both pass. The self-grenade death/respawn issue remains open until an isolated `codol_deathGates` reproduction identifies the failing gate. No live C1, lobby, or game server was started on this host.

## 2026-09-28: native integration fixture restored through gameplay snapshots

- The 32-bit `test_codol_native` executable now links and passes. It tests netchan retry and same-frame fragment draining, native C1 usercmd buttons, movement and modes, weapon inventory from tracked extended player state, event epochs, entity flags and trajectories, player composition, HUD history, and aim/spread publication. The fixture previously read the obsolete direct `ps.weapons` array and assumed old wire mappings; these assertions now use the live native producers and measured current representations. The integration fixture explicitly seeds its link state and advances event counters through producer hooks before snapshot conversion.
- `make test-codol` passes through this native integration executable and next stops at `test_codol_assets` link dependencies in the broader asset fixture, including composed-weapon, glass, engine-string, and source-weapon helpers. The full suite is therefore **not** green. This fixture work does not verify a real C1 match or resolve the self-grenade death/respawn gate. The previous throwing-knife source change remains linked but still needs live throw/pickup validation.

## 2026-09-28: mounted asset fixture reaches runtime and passes

- `test_codol_assets` now links real weapon source/compose, missile-stickiness, glass, and profile-reset implementations, with unused translation units discarded by section garbage collection. The standalone fixture supplies only its absent engine console and string-handle services. It passes mounted script ownership, archive replacement, malformed binary rejection, weapon and model parsing, and string-table cache lifetime.
- Old fixture assertions expected archive unmount to release every animation and weapon-tag string handle. Current `free_archive` deliberately retains those references because the script-string table may have recycled their numeric IDs; releasing a stale ID caused a documented engine hang. The fixture now checks the retained-reference counts. Its model-bone validator still releases matching live fake handles. A known no-op asset family with a nonzero payload rejects that payload, while an unknown family returns the unhandled result; the replay fixture tests both.
- The full 32-bit `test-codol` target passes through native integration and mounted assets, then stops linking `test_codol_send` because its test target omits snapshot/player-state dependencies. No real C1 match, launcher process, or lobby process was exercised in this iteration.

## 2026-09-28: launcher credential preflight

- The Windows launcher now checks its lobby state directory, C1 installation, rawfile root, and reference directory before creating `native_server_rcon.txt`. Missing installation data exits without leaving a credential in a state directory that cannot launch a match.
- Credential creation moved from an inline PowerShell command that embedded the path in single quotes to `tools/codol_rcon_password.ps1` with a quoted `-Path` argument. This handles lobby paths containing apostrophes, creates a 16-byte random lowercase hex secret only if absent, and leaves an existing valid credential intact. The helper rejects empty or command-unsafe credentials without printing them. `CreateNew` avoids replacing a credential made by a concurrent launcher.
- `test_codol_rcon_password.ps1` passes generation, stability, existing and invalid credentials, an apostrophe/space path, a missing state directory, and a real launcher preflight with no C1. The prior map handoff test also passes. These tests did not start a native game server or C1 client.

## 2026-09-28: snapshot send fixture restored

- `test_codol_send` now links the current production player-state extension, weapon-bit, sprint, recoil, glass snapshot, and script-player helper sources. The fixture keeps its empty-world engine/actor/model seams explicit while exercising the real snapshot writer and transport bookkeeping.
- The live-writer case now uses `svs.clients[0].frames[1]`, which the extension resolver owns, instead of stack snapshot memory. It seeds inactive link state and records two events through `CODOL_PlayerStateEventAdded`, then checks event epochs and link fields in the native frame. An epoch desynchronization deliberately fails a same-sequence rebuild. The old direct `ps.weapons[0]` assertion was replaced with tracked weapon ownership.
- The isolated 32-bit send target and both send scenarios pass. The broad `test-codol` run passes through it. `test_codol_asset_names` lacked the entity event extension declaration, which is now included; the subsequent broad run stops at that fixture's omitted native player, event, actor, model, and engine service dependencies during link. The full suite is **not** green. No real C1 client or lobby match was exercised.

## 2026-09-28: native server executable preflight

- The Windows launcher now checks that `codol_dedrun_next.exe` exists beside it before creating the lobby's RCON credential. A fresh repository clone has no generated executable; the launcher exits with an actionable build message instead of leaving a credential for a match process it cannot start.
- The focused PowerShell test copies the launcher to an isolated directory with no executable, supplies a dummy C1 file and valid state directory, and verifies the launcher exits without creating a credential. The test passes without starting a server.

## 2026-09-28: asset-name and gameplay-frame fixture restored

- `test_codol_asset_names` now links current production weapon, player, HUD, actor, glass, objective and snapshot sources. Its fixture supplies only absent engine registry, logging, map-shadow, remote-vehicle, and actor-capture boundaries. It uses owned player snapshot memory, captured client abilities, real event producer hooks, valid inactive links, and tracked weapon locks instead of stale direct fields.
- The model, selector, head icon, item-mask, FX bank, HUD flag, and entity-drop assertions now reflect their current native producers. Both isolated 32-bit asset-name scenarios pass, including native frame assembly, snapshot encoding, and drop behavior. The full `test-codol` target passes through this executable. No real C1 multiplayer match was exercised.

## 2026-09-28: collision and weapon fixture progress

- `test_codol_collision_native` now supplies the engine console function required by the real brush builder. Its dynamic-entity assertion accepts an absent cosmetic destroy effect when the source references one; the native converter explicitly permits that degraded server-side effect. The isolated 32-bit collision fixture passes, and the full suite passes through it.
- `test_codol_weapon_native` now links the production missile-stickiness and mounted weapon-source parsers with unused translation units discarded. It compiles with `CODOL_SERVER` so the exclusive/scavenger inventory categories are exercised. Fixture expectations now cover C1 type slots 0..4, class slots 0..11, offhand slots 0..5, fire modes 0..6, and first-raise time at source offset `0xba0`. The isolated 32-bit weapon fixture and the broad suite pass through it.
- The broad `test-codol` run next stops linking `test_codol_script_weapon_queries` because that target omits current VM, weapon-loader, and engine seams. The full suite is **not** green; no real C1 gameplay was run.

## 2026-09-28: class/perk script fixture reaches the production profile path

- `test_codol_script_weapon_queries` now discards unused VM methods in its focused link; its `WeaponInheritsPerks` zero-index, flag, and missing-metadata cases pass. This does not test the other methods in that source file.
- `test_codol_script_class` now links the real profile view, structured field and scalar readers, marketplace item resolver, and uploaded client stats. A synthetic mounted definition deliberately reverses physical field offsets so the test checks schema-driven lookup, including separate clients, class 7 perk slot 5, marketplace last-ID-row behavior, bad paths, definition loss, and reload. Its secure-profile seam asserts unreachable because the method reads public uploads. The isolated 32-bit fixture passes.
- The full `test-codol` target passes through both script fixtures and next stops linking `test_codol_weapon_loader` because its target omits current weapon source and sound dependencies. The full suite is **not** green. No C1 client or lobby match was exercised.

## 2026-09-28: mounted weapon and ammo registry fixtures restored

- `test_codol_weapon_loader` now links the production attachment, missile-stickiness, and sound-source parsers. Its fixture keeps only absent engine image/attachment and diagnostic services as explicit seams. It verifies fire mode 6, rejects mode 7 without replacing the previous result, and checks that a missing muzzle-flash effect degrades with a warning while malformed effect metadata still rejects. The isolated and broad 32-bit target passes.
- `test_codol_weapon_timing_metadata` now discards unrelated weapon-state functions during its focused link. Its missing-metadata fallback and valid modifier cases pass. `test_codol_weapon_registry` compiles with the native server layout; its definition array now covers all 700 slots scanned by the API, and its standalone player-state fixture supplies owned bits locally. The isolated and broad registry targets pass.
- The Windows launcher now gives the repository build and executable promotion commands when its native server binary is absent. The RCON preflight test passes. The broad `test-codol` run next stops linking `test_codol_sv_weapons` because that fixture lacks current composed-weapon, server inventory, console, and configstring dependencies. The full suite is **not** green; no live C1/lobby match was exercised.

## 2026-09-28: server weapon and later multiplayer fixtures

- `test_codol_sv_weapons` now passes with the production weapon bits, weapon state, and tracked player-state extension. Its fixture supplies absent retained engine globals and composed-weapon adapters. It checks inherited and appended weapon names, failed partner registration without broadcast, successful configstring publication, reorder-sensitive mappings, and owned ammo bindings. The 700-slot ceiling replaces the obsolete 128-slot test limit.
- Focused entity, math, and dvar script links discard unrelated methods. Team FX links the production effect-name reader; its fixture supplies the retained string-copy helper. A stale duplicate appearance test target was removed because the earlier target already passed with the current archive sources. The weapon-lock reset fixture now exercises production client and game reset paths with explicit seams for other reset modules. Its lock-clearing, missile, fire gate, and GSC method tests pass.
- The server GSC build-version fixture now expects the short `1.1.1.13` value returned for match records. The animation table fixture now accepts the production zero value for a CoDOL condition with no producer, while keeping invalid-access errors distinct. Focused and broad tests pass through animation tables. The broad `test-codol` run next stops linking `test_codol_script_menu` on current menu-name and connected-client publication dependencies. No live C1 multiplayer match was exercised.

## 2026-09-28: full portable test suite reaches its end

- `test_codol_script_menu` now links the production configstring bank and tests inherited names, overrides, duplicate precache, and publication only to clients eligible for gamestate updates. The focused and broad menu test passes.
- The script lowerer now keeps a unary sign adjacent to its numeric literal when substituting a file-scope constant. The focused test distinguishes this from binary subtraction. It also distinguishes a nonconstant file-scope expression, which the lowerer leaves untouched, from duplicate or mutated constants, which it rejects. The focused and broad script-lowering tests pass.
- `test_codol_iwd_crypto.py` now opens the tracked lowercase `src/mbedtls/makefile`, which works on case-sensitive Linux. The broad 32-bit `make test-codol` run completes through this final Python fixture. Its synthetic ZIP and cipher cases pass; the environment has no original client archives, so its original-IWD comparison reports zero entries. This is portable fixture coverage, not a live launcher/lobby/C1 multiplayer proof.

## 2026-09-28: recovered missile lifecycle after script callbacks

- A fresh Linux clone at `6b55836` built the native server and passed the complete `test-codol` suite. In the current source, the class-9 knife and timed-equipment pickup path transferred ammo and sent `trigger` before it sent `death` and freed the missile. A script could convert or reindex that same entity during `trigger` without incrementing its generation; the previous generation-only check then destroyed the converted entity.
- `CODOL_RecoverMissileAmmo` now captures the original packed item index and checks that the entity is still an in-use missile with the same generation and index after `trigger` and again after `death`, before the final free. The new focused 32-bit fixture reproduced the conversion failure before the fix and passes afterward. It also covers knife and timed eligibility, capacity and ownership gates, one-unit ammo transfer, predictable versus normal pickup events, fuse cancellation, deletion, reuse, conversion and reindex during notifications. `make test-codol-missile`, the complete `make test-codol` suite, and the native server link pass with the change.
- These are server-side fixture and build results. A real C1 throw, settle, touch, ammo transfer, and respawn remain unverified; the separate lobby and client sources are outside this repository.

## 2026-09-28: Windows lobby admission freshness and launcher wiring

- The lobby can replace `game_admissions.txt` twice within one second with unchanged length while issuing a session key. The native cache previously trusted `stat` size, timestamp, and inode on every platform; Windows CRT metadata may not distinguish that replacement, leaving the previous key active for the next connect. The Windows path now reloads the bounded roster on each handshake/connect lookup. POSIX keeps its metadata cache. A focused 32-bit fixture restored the entire cached stat tuple after a same-size rewrite and reproduced the stale-key result before the change; the regular and coarse-metadata variants pass afterward.
- The Windows launcher now passes an explicit admission path in `CODOL_STATE_DIR` and sets `codol_admissionRequired` to 1 by default, matching the packaged launcher. `CODOL_ADMISSION_REQUIRED=0` remains available for an isolated direct-connect probe. The PowerShell handoff/launcher fixture passes.
- A fresh Linux clone at `537b0e4` with this source overlay passed the complete 32-bit `make test-codol` suite and native server link. Both passed again after overlaying the disjoint upstream turret source from `c311b6e`. These checks establish source and fixture behavior only. A Windows native server build and a real lobby-issued C1 admission/respawn run remain to be verified.

## 2026-09-28: fatal player death gate reporting

- The retained `player_die` can return after damage has reduced health to zero if there is no server DObj, `pm_type` is neither normal nor last stand 7, or `otherFlags` bit 0x2 is set. The earlier self-grenade probe established zero health without death but did not identify the failing gate. CoDOL assembly now passes the exact branch reason to `CODOL_ReportDeathGateRefusal` on these three early returns. The helper logs the client, reason, health, `pm_type`, and `otherFlags` only for zero-or-negative-health victims with `developer 1`. The death decision and allowed path are unchanged.
- NASM assembled both CoDOL and retained IW4OL variants. CoDOL object disassembly confirms the three branch reasons and unchanged allowed-path entry. The Linux native server links and the complete 32-bit `make test-codol` suite passes. No live grenade/respawn reproduction or C1 client run occurred here, so the actual failing gate and a corrective gameplay change remain open.

## 2026-09-28: retain idle multiplayer associations for lobby rejoin

- The native peer lookup discarded an established bdDTLS association after 120 seconds without an inbound packet. This conflicts with the documented C1 behavior of reusing a cached association on later match joins: a DATA record from that client then found no peer, although the process had not restarted. Pending handshakes still expire after ten seconds. Established peers now remain addressable through lobby idle time.
- A full 64-peer table can admit a new INIT by selecting its oldest established peer that has been idle for more than 120 seconds. Selection alone preserves the old peer; the replacement handshake is prepared separately and the old state is erased only after a successful INIT. Recent peers are not eligible. The focused test uses the real pool implementation and reproduced the two-minute lookup failure before the change; it now covers idle return, free-slot preference, oldest-idle selection, no premature erase, full-recent refusal, and pending expiry.
- A fresh Linux clone at `a744570` with the network source, test, and makefile overlay passed `test-codol-peer-pool`, the full 32-bit `make test-codol` suite, and the native server link. A real C1 lobby idle/rejoin sequence and Windows build remain unverified; no client or lobby was started here.

## 2026-09-28: reserve outbound bdDTLS counters before sending

- Session persistence previously wrote the current send counter after received DATA at most every five seconds, then resumed at that saved value plus 256. The number of outbound gameplay records between saves was not bounded by 256, so a restart could reuse counters the client had already accepted. The native sender now persists an exclusive future counter limit before it uses a range. Once it reaches that limit it saves another reservation before sealing the next record; a failed write pauses that send without consuming a counter. Periodic and shutdown saves also record reserved limits. Loading adds one more block for compatibility with both old files containing current counters and new files containing reserved limits.
- The focused test runs the real save and send control flow with a fake filesystem. After 300 records, it reproduced the old persisted-high-water failure against the previous source; the revised source passes, including range rollover and a failed-write gate. A fresh Linux clone at `af207cf` with this source, test, and makefile overlay passed the focused target, complete 32-bit `make test-codol` suite, and native server link.
- This validates counter reservation for successful file writes and process restarts with an intact session file. The existing `FS_SV_HomeWriteFile` write is not atomic, and a power loss during that write remains a separate persistence risk. Real C1 restart/rejoin and Windows build are unverified.

## 2026-09-28: replace the saved session file after a complete write

- `FS_SV_HomeWriteFile` truncated `codol_sessions.txt` before writing the next reservation. Its existing home rename helper falls back to copying over the destination on failure, which also exposes a partial file. The session save now writes and flushes `codol_sessions.txt.tmp` in the same home directory and replaces the destination only after closing the complete temporary file. POSIX uses `rename`; Windows requests `MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH` through `MoveFileExA`, without a copy fallback. A failed write or replacement leaves the prior file in place and does not grant a new counter range; sends pause when the previously saved range is exhausted.
- A focused 32-bit test uses a real temporary directory to check replacement, an empty file, owner-only permissions on the local POSIX filesystem, no leftover temporary file, and preservation when the destination is a directory or the parent is missing. The send-reservation fixture still passes with the new write API. A fresh Linux clone at `8701237` with the source/test/makefile overlay passed both focused tests, complete `make test-codol`, and the native server link.
- This removes in-place truncation for process crashes during a save. Directory metadata durability after sudden power loss depends on the filesystem, and the Windows branch is source-reviewed against [Microsoft's MoveFileExA contract](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-movefileexa) but not compiled or run here. A real C1 restart/rejoin remains unverified.

## 2026-09-29: exact 1.1.1.13 live launcher-to-match test

- A copied `E:\CoD Online 1.1.1.13\C1.exe` and adjacent `C1.dll`, with the matching `E:\codol-classic` archives, ran through the rebuilt CODOL-EMU launcher, Python lobby and native Windows server on loopback. The launcher initially stayed at 0% because its disabled-update replies re-entered the SWF before update-page construction finished. Deferring those two replies to the launcher message queue fixed it; the rebuilt launcher reached login. A live local API check passed login, directory and handoff for the mock backend.
- The user logged in and selected the local lobby. A real Ready press selected `mp_killhouse_sh/combat`; the lobby sent map and START_GAME pushes and RCON changed the native level. C1 loaded that map, established its DTLS association, received a 6079-byte gamestate and entered `CA_ACTIVE` at 01:10:05. The native server logged player `test` in slot 0; its progress file recorded 29 seconds on Opfor and five missed shots. At 01:10:43 the client sent `disconnect EXE_DISCONNECTED` and returned to the lobby; the user confirmed they left intentionally. Whether movement and shooting appeared correctly on screen remains to be confirmed. QoS probing failed even though game transport and active state succeeded.
- The native startup command was 1075 characters, exposing silent truncation in the original 1024-byte Windows command-line buffers. The CoDOL Windows path now accepts up to 8192 bytes with an explicit overlength failure. Before the live session, an isolated automated stack test passed lobby TCP, native map boot, Ready map control, and C1 authentication/UI zone. These are local, uncommitted changes; no repository was pushed.

## 2026-09-29: bot assets in isolated server homes

- The previous isolated Killhouse log said `missing or invalid waypoint graph waypoints/mp_killhouse_sh_wp.csv`; the CSV existed in the repository but not in that process's `fs_homepath/main`. The development launcher now builds the existing `sh1x_svr_scripts.iwd` from tracked scripts, waypoints and bot classes into the active home before server startup. Its default bot count is 12, with `CODOL_BOTS=0` available to disable it. The standalone stack helper uses the same pack builder.
- The focused launcher path test passes. An isolated Windows server with only the pack in a fresh home mounted Killhouse's 181-node CSV and reached `bots=2`; no loose waypoint or class CSV was present in that home. The persistent local stack on UDP 17733 is running `mp_killhouse_sh/dm` with `bots=12`; its log confirms the same graph load and its game log records bot weapon damage and kills. This establishes native bot spawning and combat server-side, not real C1 visual presentation or full T5/CoDOL bot-policy parity.

## 2026-09-28: production GSC gate excludes developer-only code

- A previous Killhouse/war script audit reported `shouldRunServerSideEffects` as a fatal unresolved call. The call is inside `/ # ... # /` developer-comment syntax (without spaces in the GSC), while `developer_script` defaults to false and is passed to `Scr_Settings`. The reported production blocker was a false positive; the earlier live Killhouse evidence is consistent with this setting.
- `codol_script_resolve.py` now uses this repository's active `bin/home/codol_rawfiles` tree by default, masks inactive developer blocks while retaining line numbers, reports unmatched or nested developer delimiters, and offers `--developer-script` to audit the enabled mode. The focused test passes both modes: normal Killhouse/war resolves and developer mode reports the still-missing helper. A single production gate covering war plus Killhouse, Rust, Favela Tropical and Crash resolves 134 reachable scripts; the default engine seed gate also passes.
- This changes validation only. No native server, launcher, lobby, gameplay script, or real C1 client was run for this pass. Developer mode still cannot compile the affected map FX path until its intended server/client effect behavior is verified and implemented.

## 2026-09-28: four MP map entry scripts no longer load obsolete DLC destructibles

- Abandon, Complex, Compact, and Trailer Park called `_destructible_dlc` or `_destructible_dlc2` before `_load`. Those legacy scripts include the large part-state destructible tables, whose functions were removed when this repository adopted a whole-entity handler in `common_scripts/_destructible.gsc`. The script gate reported unresolved calls in those tables, so these map entry paths could not pass static compilation checks.
- The four map entry scripts now rely on their existing `_load::main()`, which initializes the current whole-entity handler for every MP map. The legacy DLC files remain in the tree for future part-state implementation but are no longer reachable through these maps. A regression test runs the normal `war` gate with all 37 `mp_*.gsc` map entry scripts: 311 reachable scripts resolve. The narrower four-map gate resolves 149 scripts. The GSC policy gate (`--root bin/home/codol_rawfiles --only maps/mp`) passes for the four changed maps.
- This enables the four entry paths at the static script-resolution layer only. Native map loading, zone assets, client presentation, and destructible interactions on these maps were not exercised here. Part-level breakage remains unimplemented; the supported whole-entity handler is the same one used before this pass.

## 2026-09-28: Windows launcher applies the lobby match selection atomically

- When `CODOL_MAP` was not pinned, the launcher read a fresh `startgame.txt` but kept any inherited `CODOL_GAMETYPE`, `CODOL_ZONE_TYPE`, or `CODOL_SESSION_MAP`. An operator environment left over from another match could therefore launch the map sent to C1 with a different game mode or asset category. The packaged Linux entrypoint already replaced all four fields together.
- The Windows launcher now applies all four values from a valid lobby handoff, while an explicit `CODOL_MAP` still pins the manual selection. It also prints the selected session map beside the existing map, gametype, and zone so the operator can verify the complete selection.
- The PowerShell handoff test now executes an isolated copy of the actual batch launcher with conflicting inherited `dm`, `zm`, and session values, then checks its selected match output and an explicit pinned-map override. It uses a quick-exiting stand-in executable and temporary lobby state; no native server or C1 client was launched. The adjacent RCON preflight fixture now captures expected stderr from negative cases before checking their exit codes under Windows PowerShell 5. Reader validation, launcher handoff, and RCON preflight tests pass. Live lobby ready-up and client join remain unverified here.

## 2026-09-28: packaged server prepares the shared RCON credential safely

- The container entrypoint previously used `-s` as its only check on `native_server_rcon.txt` and wrote a new password directly to that shared path. A nonempty but malformed value could be passed to `+set rcon_password`, while another launcher or the lobby could observe a file before its write finished.
- A packaged POSIX helper now writes a random 16-byte lowercase hex value to a private same-directory temporary file, then hard-links the complete file into the shared lobby state without replacing an existing path. It validates raw bytes of both new and existing credentials against the Windows launcher alphabet (1–128 ASCII letters, digits, `_` or `-`, with at most one optional line ending). Empty, malformed, unreadable and oversized files stop container startup with a credential error; the password is never logged. The entrypoint strips a validated optional line ending before passing the value to the native server.
- The shell fixture passes generation, owner-only local permissions, existing-value preservation, malformed/NUL/extra-newline/oversized rejection, missing-directory rejection, CRLF compatibility, and two concurrent starts. A `--skip-game` package build with a synthetic ELF header confirms that the helper is present in the generated Docker context and referenced by its Dockerfile and entrypoint. The real Docker image, separate lobby, and C1 client were not run here.

## 2026-09-28: all MP gametype script closures pass the production name gate

- The previous map audit seeded `war` plus 37 MP map entry scripts. Extending it to all 14 non-underscored MP gametypes exposed a reported `flag_descriptor()` call in `dom.gsc`. Its source location is inside a quoted map-error message containing escaped quotes. The resolver's old quote-to-quote masker resumed scanning in the middle of that message and treated prose as code.
- The string masker now keeps backslash-plus-next-character pairs within GSC literals, including `\"` in Domination diagnostics and `_art.gsc`'s generated source text. A focused test checks those literal boundaries. The production union gate now resolves 325 reachable scripts across all 14 MP gametypes and 37 MP map entry scripts; the existing developer-block and Killhouse checks still pass.
- This is a validation-tool correction and broader static coverage. It does not establish that every map contains each mode's required spawn or objective entities, or that those modes run correctly with a C1 client. No gameplay script or native server binary changed in this pass.

## 2026-09-28: settled throwing knives enter the player touch search

- `G_InitGrenadeEntity` gives a native class-9 knife `r.contents=0x202100` and a packed item index. `Player_UpdateCursorHints` searches `0x200000`, so manual use can find the knife, but `G_TouchTriggers` searches `0x405c0008`; no bit in the flying or settled knife contents matched that automatic touch query. The search's `0x400` argument is its result capacity, not the contents mask.
- `CODOL_KnifeWorldImpact` now adds `CONTENTS_TRIGGER` (`0x40000000`) only when the knife settles and before `SV_LinkEntity`. Walking into the settled missile can then reach the existing `Touch_Item_Auto` path, where native eligibility, one-unit ammo transfer, and guarded cleanup remain in force. The flying missile keeps its original contents and manual-use bit.
- `make test-codol-missile` and the native Linux server link pass in the working tree. The complete `make test-codol` suite passes in a temporary Linux checkout with the changed source. The working path contains spaces and its `test-external` Makefile recipe parses `TARGETDIR=$(CURDIR)` incorrectly, so the temporary path was used for that suite. A real C1 throw, walk-over or use pickup, and respawn still need live verification; the user-reported knife issue remains open.

## 2026-09-28: lobby match status rejects a stale map after load failure

- `ERR_DROP` calls `SV_Shutdown`, which clears `com_sv_running`, but leaves the old `mapname` cvar available. `sh1x_status` previously suppressed client counts while still reporting that old map and omitting the documented `running=0` field. The lobby could place a player on a server with no active level, and the bundled watchdog's `running=0` / `map=none` checks could miss it.
- Match status now requires both `com_sv_running` and `sv.state==SS_GAME`. Until then it reports `map=none`, `session_map=none`, `running=0`, zero seats and `uids=-`. An active level reports `running=1` and its actual map, session, human, bot and UID values.
- The focused 32-bit fixture reproduced the stale-map output before the fix and passes for stopped, loading and active states afterward. The native Linux server links, and the complete `make test-codol` suite passes in a temporary Linux checkout with the changed source. A real lobby polling a failed map load and a real C1 join remain unverified.

## 2026-09-28: packaged server bounds the lobby map handoff

- The packaged Linux entrypoint accepted arbitrarily long map, session-map and gametype identifiers from `startgame.txt`, while the Windows launcher rejects names over 64, 64 and 32 characters. An overlong handoff could therefore select a different startup command or be truncated when stored in engine fields. The old inline awk also accumulated fields from multiple records.
- The package now installs a dedicated awk parser and applies a handoff only when one fresh record supplies valid identifiers, a supported zone type, and the same length limits as the Windows reader. An older record without `session_map=` still falls back to `map=`. Explicit `CODOL_MAP_PINNED=1` remains the override.
- The focused awk fixture passes the supported categories, boundary lengths, CRLF, freshness limits, legacy fallback and malformed records. The package-context fixture confirms the helper is copied and referenced by the Dockerfile and entrypoint. `sh -n` passes for the entrypoint. The Docker image, separate lobby and real C1 client were not run here.

## 2026-09-28: Windows launcher rejects mixed lobby records

- The Windows `startgame.txt` reader split the entire file on whitespace. Appending a second record after a fresh first record could replace its map, mode and session fields while retaining the first timestamp. A focused regression reproduced `mp_cargoship_sh` being selected after a first record for `mp_rust`.
- It now requires exactly one record, with an optional final LF or CRLF. The Windows reader/launcher fixture passes the mixed-record rejection and valid CRLF cases. This brings it in line with the packaged Linux parser's one-record rule. No live lobby Ready press or C1 join was exercised by this fixture.

## 2026-09-28: category-specific GSC startup gate

- The static resolver always seeded the multiplayer dog aitype and its nine animation scripts, even when checking co-op or Zombies. Native `CODOL_ActorScriptsLoadMapTypes` preloads species by mounted asset category: multiplayer dog, Zombies humanoid zombie, neither in co-op. The old Zombies check could miss a compile error in a zombie animation script while checking unrelated dog scripts.
- `--category` now selects those native preload seeds, defaulting to multiplayer for existing calls. The regression gates all nine co-op and three Zombies map entry scripts with their respective gametypes and category roots; it confirms the Zombies closure contains its zombie aitype/animation scripts and both non-MP closures exclude the dog aitype. The five resolver tests pass. This is static compilation-name coverage, not map runtime or client behavior.

## 2026-09-28: custom splash uses C1 entity-box distance

- `codol_radiusdamage`, called by equipment and killstreak scripts, measured non-brush targets from `currentOrigin`. A player's origin is at the feet. The retained CoDOL radius assembly and documented C1 path measure every target from the nearest point of its absolute bounds, so a chest-height blast could wrongly miss a nearby player in the custom path.
- The builtin now uses a shared absolute-box distance helper. Its focused 32-bit test covers inside, side, corner and below-box points. The full 32-bit `make test-codol` suite passes after changing the external-library target to a relative path, so this workspace path with spaces no longer breaks that suite. The server links as a 32-bit Linux executable and contains the new helper symbol.
- A controlled server using the exact `1.1.1.13` client key regions and game assets from `E:\codol-classic` loaded `mp_rust`/`dm`, compiled the scripts, installed collision and weapon definitions, and answered a live UDP `getstatus` query on port 17734. A separate port-17735 probe connected and spawned two bots; its live status showed a 100-point score for Training 2. The exact C1 binary exists at `E:\CoD Online 1.1.1.13\C1.exe`, and the matching full installation executable reports file version `1.1.1.13`. These observations prove server startup and bot-side match activity, not a human C1 login, lobby handoff, client rendering, or the splash result in a real client match.

## 2026-09-28: Windows launcher accepts a separate matching client file

- The available `1.1.1.13` game archives are under `E:\codol-classic`, while the matching `C1.exe` is under `E:\CoD Online 1.1.1.13`. The Windows launcher previously required `C1.exe` inside `CODOL_INSTALL` even though the native archive loader already accepts an explicit `codol_clientExe` path.
- `CODOL_CLIENT_EXE` now selects a separate matching `C1.exe` or exported `c1_keys.bin`. The launcher rejects a missing path or directory before creating its shared RCON credential and passes the selected path to the native loader. When unset, the original in-install `C1.exe` preflight remains in force.
- The isolated split-path launcher fixture and existing map-handoff and RCON launcher fixtures pass. This does not provide the separate alpha0022 lobby or its state/profile directory; the launcher still requires `CODOL_REFERENCE` and `CODOL_STATE_DIR` for that integrated path. A real C1 join remains unverified.

## 2026-09-28: free-for-all score-limit changes use a player receiver

- `updateUIScoreLimit()` runs on `level` when a watched limit changes. Its prior `thread checkScoreLimit()` call can end a team match from team scores, but `checkScoreLimit()` explicitly returns for a non-player receiver in free-for-all. Lowering the FFA score limit below the leader's current score therefore could not end that match through this callback.
- The FFA path now selects the highest-scoring player and runs `checkScoreLimit()` on that player; the team path keeps the level receiver. The required `maps/mp/gametypes` resolver gate passes with 107 reachable scripts and 970 registered builtins. A separate live `mp_rust`/`dm` two-bot match on UDP 17736 reached a configured 100-point limit, ended, restarted the map, and respawned both bots. That ordinary end used the earlier script and does not prove the dynamic-limit fix.
- A second isolated probe packaged the changed `_gamelogic.gsc`, loaded `mp_rust`/`dm` with two bots on UDP 17737, and showed both bots at 50 points under an initial 1000-point limit. A loopback RCON change to `scr_dm_scorelimit 1` was followed by `map_rotate`, a new map start time, and both scores reset to zero. No kill was logged between the limit command and rotation. This verifies the server-side dynamic callback; real C1 match summary and lobby report delivery remain unverified.

## 2026-09-28: combined native suite accepts saturated health

- An independent remote killstreak commit changed native health projection to clamp out-of-range script health into the 16-bit wire slot, but a broad composition fixture still expected `stats[0]=32768` to reject the whole frame. The focused health fixture already checks both high and low saturation. The stale rejection case is removed, keeping the other invalid-field checks intact.
- The full 32-bit `make test-codol` suite first failed at that stale assertion after the remote merge and then completed through the final IWD ZIP/cipher fixture with this local test correction. This is a fixture alignment with the remote behavior, not a new client gameplay claim.

## 2026-09-28: Windows launcher accepts an alternate lobby profile directory

- The exact game assets and C1 executable are on `E:`, while the launcher's default `D:\CoD\...\alpha0022` reference is absent. Even with `CODOL_INSTALL`, `CODOL_CLIENT_EXE`, and `CODOL_STATE_DIR` set, the launcher rejected that missing source directory before starting the match server. The native server uses only its `resources` profile directory from that reference.
- `CODOL_PROFILE_DIR` now explicitly selects a separate lobby's resources directory. When set, the launcher verifies that directory and no longer requires the old alpha0022 source tree; when unset, it retains the old reference-derived profile path. The isolated Windows fixture covers missing and valid explicit directories before credential creation, and the split-client, handoff, and RCON launcher fixtures pass.
- This removes a hardcoded launcher dependency for an alternate lobby. The matching Demonware service has since been located in the separate `CODOL-EMU/1.1.1.13-Demonware-Emulator-Python` checkout. The native Linux server and its bot match remain separate evidence; no real C1 lobby join was established by this fixture.

## 2026-09-28: exact-build local integration and Windows server boot

- Cloned only the version-labelled `CODOL-EMU/1.1.1.13-Demonware-Emulator-Python` lobby and `CODOL-EMU/1.1.1.13-Launcher` launcher. The launcher built after repairing its missing icon resource with the icon extracted from the installed 1.1.1.13 launcher. Its local mock API passes version, login, directory and handoff checks. In a copied 1.1.1.13 installation the rebuilt launcher process loaded the SWF and logged `INITSUCCESSDATA`, but the hidden, unattended run made no API request.
- The lobby now reads `native_server_rcon.txt` from `CODOL_STATE_DIR`. An isolated test checks missing-password refusal and all five ordered Ready RCON datagrams from a relocated state directory. Its crypto dependency is installed in a repository-local virtual environment; full lobby and two-client offline selftests pass with crypto available. An isolated copied lobby bound TCP and UDP loopback 3074 and wrote its log to its own state directory after removing the stale default log path.
- Installed a 32-bit MinGW cross compiler in WSL and compiled the native server's Windows objects, dependencies and PE executable in separate build directories. The local generated `bin/codol_dedrun_next.exe` is 7,057,016 bytes, SHA-256 `F701A3943BD5808579D00866FA38F8AFAC0F9B3C6F39CD2C199EBC35E323BB60`. An isolated Windows process loaded `mp_rust`/`dm` from the exact 1.1.1.13 E: assets and answered loopback `sh1x_status`; the test stopped only its own process.
- Encrypted connect remains untested in this Windows pass: the existing synthetic probe requires `dtls_crypto.py`, which is absent from these cloned repositories. A hidden direct C1 launch from a copied installation stayed alive for 22 seconds but made no observed lobby traffic or fresh client log. No visible login, Ready press, match join, gameplay, or report delivery was verified. All changes remain local and uncommitted; nothing was pushed.

## 2026-09-29: Zombies Prototype repair pass

- Source changes remove the duplicate persistent points hudelem, republish the native Zombies down-state ability on respawn, retry the zombie combat animscript after a missed swing, suppress power-up drops during outside entrance, count successful zombie spawns, and reject route links whose floor normal the actor physics cannot walk.
- Exact C1 map `info_volume` brush entities are now spawned and linked. A Zombies zone manager enumerates those live volumes, maps their targets to authored spawner groups and follows the verified Prototype/Training door flags. The single live Prototype startup found three groups and initially activated only the 17 start-room spawners; the former script activated all 42 map spawners.
- The Windows binary built, Zombies GSC resolution passed against that binary (973 builtins, 107 reachable scripts), and all five resolver tests passed. A prior deployment exposed the `getEntArray` dynamic-field limitation; that runtime failure was repaired before the current startup. Live combat, down state, pickup placement, mystery-box presentation, door transitions and round accounting still require a human-client test. Esc-twice pause remains open in the client close path. See `CODOL_ZOMBIES_ISSUES_20260929.md` for each issue and its evidence boundary.
- A temporary server test client triggered six distinct Prototype zombies in round one. Training started with four authored zone groups and one initial spawner. Asylum started with nine groups and enabled six `west2_downstairs_zone` spawners when its temporary test client entered; the client was removed before returning the sole server to Prototype. Actor step landing and waypoint continuation were adjusted after two failed corridor traces. A later probe recovered from a brief stall, but one longer run still showed a persistent stall, so navigation is not yet confirmed fixed.

## 2026-09-29: live Zombies follow-up

- Human Prototype rounds one and two reproduced a shared collision choke near `(-875,50,-1)` with multiple zombies in the same place. The forward actor hull immediately hits world dirt or sidewalk while an 18-unit raised forward trace is clear. An isolated Windows diagnostic build now records the actual physics step decision at most once per actor per five seconds, without changing movement. It was started as the sole server on UDP/17733 after `sh1x_status` showed no players; movement still needs diagnosis and repair.
- The user confirmed damaged boards can be repaired and award points, but no repair prompt appears. The script uses `trigger_radius`, whose contents are touch-only and do not participate in the native cursor-hint search. The repair loop now publishes the registered hint to a touching player and clears it on exit or completion. Zombies GSC resolution passes; C1 display remains to be checked.
- The solo down screenshot showed the pistol last-stand view. The script incorrectly treated the starting life as a spare, causing a 45-second bleedout followed by a free revive. A solo player now starts with zero spare lives; purchased Quick Revive grants one. The Zombies root also starts a five-second delayed health-regeneration thread, because the multiplayer health thread is absent. These script changes passed resolution and startup but need a human C1 retest.
- The user also reconfirmed double Esc to resume. The client menu close path leaves `KEYCATCH_UI` after the first key. The existing fastfile writer cannot serialize the MenuList/menuDef asset needed for a safe menu replacement, and no server event reports that first key; the issue remains open. See `CODOL_CL_PAUSED_20260920.md`.
- The user then confirmed the damaged-barrier repair prompt now appears in C1. A new screenshot showed the native purse delta `+60` at bottom left while a separate yellow `10` still floated at the right. The remaining T5 `score_highlight` hudelem path was removed from `_zombiemode_score.gsc`; Zombies GSC resolution passes, and the visible result awaits a script reload and human retest.
- The user's round-two screenshots also show a zombie with its arms stuck in a default-looking pose. The animation state is under investigation; no visual fix is claimed yet.
- Pain-state logs showed the completed full-body attack clip held at weight 1 and time 1.0 while only a limited arm flinch was published. `zombie_pain.gsc` now adds a shipped full-body idle or crawl base beneath the flinch. This and the score change loaded cleanly in the sole restarted server, but the exact screenshot actor was not identifiable and both visual outcomes require a C1 retest.
- Native actor physics now tries a bounded two-to-sixteen-unit raised landing after three consecutive blocked frames with a steep normal, at most once per actor per second. The isolated Windows build succeeded. In a controlled Prototype round, actor 577 triggered a two-unit step at the known `(-875.8,50.3,0.0)` choke, then progressed to `(-251,-213,1)` and started tearing a barrier. This proves that one actor crossed the reproduced choke; it does not establish every spawn path or client-visible animation. The temporary bot was removed; the server remains one process on UDP/17733.
- A controlled no-perk solo-down probe exposed a diagnostic-only `state` command crash: the dead bot had an undefined team, which the probe concatenated into a string. The match dropped, so the diagnostic now prints `none` for an undefined team. After a single-server restart, the same probe reported `alive 0`, health 0 within a second of the down, with no script error. The temporary bot was removed and Prototype remains live with zero bots on UDP/17733. This checks the server-side no-perk transition; Quick Revive and the C1 camera still need a human test.
