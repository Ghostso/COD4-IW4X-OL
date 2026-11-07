# Source-code audit findings (battle server + baseline) — 2026-10-29

Scope: `CODOL_SERVER_319_20261021/src`, `include`, `tests`, `CMakeLists.txt`,
`run_codol_001/run_frozen_chain_once.py`, `CODOL_VERIFIED_GOLDEN_20261019/`,
`REF_LOBBY_KIT/_golden_hashes.json`, `docs/*20261028*.md`, latest run dirs.

All findings below are read from files on disk in this workspace. Nothing here
is executed or launched.

---

## S-01 — Baseline hash drift: `marketplace_store.py` (verified by recomputation)

`REF_LOBBY_KIT/_golden_hashes.json` declares:
```
marketplace_store.py  size=46226  sha256=28b4a1be67de06f41e789e723f8befecf1ea5ac7b2a3ca20cfef557a6f571a16
```
Actual on disk: size=50022, sha256=`e44358f0eb951b62c244a136a181952c26850e841d537bcb70ebb0ffc5dd034e`.

The other 8 protected files recompute to their declared hashes (OK=8, MISMATCH=1).
Per AGENTS.md "A changed protected hash means the chain was modified and the run is invalid."
`--verify-only` only covers the 6 launch_core files, so this is not caught at startup.
Referenced in `docs/FIX_MEMBERCOUNT_APPLIED_20261027.md` §"一处既有偏差(非本次造成)".

## S-02 — Working kits diverge from the protected baseline and keep growing

| file | size |
|---|---|
| `REF_LOBBY_KIT/lobby_server.py` (protected, 2026-10-07) | 76,410 |
| `CODOL_VERIFIED_GOLDEN_20261019/lobby_server.py` (working, 2026-10-27) | 88,162 |
| `run_codol_001/runs/ONCE_20261029_000806/kit/lobby_server.py` | 108,173 |
| `run_codol_001/runs/ONCE_20261029_001513/kit/lobby_server.py` | 108,944 |
| `run_codol_001/runs/ONCE_20261029_002046/kit/lobby_server.py` | 109,705 |

Growth across three runs on 2026-10-29 alone: +1,532 bytes. There is no source
of truth for "the" lobby server; the frozen kit and every run kit differ.

## S-03 — No version control anywhere

`D:\BaiduNetdiskDownload\使命召唤OL` is not a git repository; no `.git` exists in
any scanned subdirectory. Every experiment is an untracked copy. Provenance of
any given `lobby_server.py` variant can only be reconstructed from the prose
docs, not from a diff.

## S-04 — Battle server executable is not reproducible from the CMake test targets

`CODOL_SERVER_319_20261021/build/Debug/codol_battle_server.exe` = 314,368 B,
sha256 `275B165F...` mtime 2026-10-26 22:07.
`build/Debug/test_session.exe` is also 314,368 B (different hash).
The kit copy shipped to runs is byte-identical (same size and hash), so the
running binary matches this one — but the CMakeLists has no target that
reproduces `test_session` at that size, and `test_session.c` is 2 KB. The build
tree has accumulated links/binaries from several different source states
(mtimes 10-21 .. 10-26). No build manifest records what produced what.

## S-05 — 26 test source files, 22 registered ctests, 3 probes not automated

Registered (`add_test`): snapshot_delta, equipment, player, weapondefs, collision,
regression_20261022, backpack_reliable, evidence_gate, crypto, p224, fe, msg,
netchan, gs_vector, usercmd, snapshot, battle, session, wire_codec, snapshot_run,
snapshot_codec_run, static_closure.

Not registered / never run by `ctest`:
`tests/probe_snapshot_size.c`, `tests/probe_world_damage.c`, `tests/sim_check.c`,
`tests/test_snapshot_codec_run.py` runs outside ctest, `tests/e2e_client.py`,
`tests/test_weapondefs_direct.exe` (built but no target in the current CMakeLists).

Consequence: the "22/22 passed" figure quoted in reports does not include the
probes that produced the strongest evidence (world damage, clipmap trace), and
does not include any client-interop test.

## S-06 — `codol_ground_z = -116.0f` is a hard-coded infinite floor plane

`src/world/collision.c:11` `const float codol_ground_z = -116.0f;`
`src/world/collision.c:93-104`: any trace with `delta[2] < 0` is clamped at
`codol_ground_z - mins[2]`. There is no real geometry below the spawn point:
`docs/CLIPMAP_EXTRACTION_20261026.md` documents that the coop clipmap's 30 brushes
cover x -824..-177 and the spawn is at (48, -572) — outside every brush.

So server-side gravity always terminates at z=-116 regardless of map. Any map
change or vertical feature is silently wrong.

## S-07 — Weather simulation: gravity is applied only `if (!pm->walking)`, and `walking` is never refreshed

`src/movement/movement.c:79-85`:
```c
if (pm->cmd.buttons & 0x01) {
    if (pm->walking) { pm->ps->velocity[2] = jump_velocity; pm->walking = false; }
}
if (!pm->walking) apply_gravity(pm, dt);
```
`codol_movement_process_usercmd_dt()` at :116-129 zeroes a local `codol_player_t
player`, sets `player.on_ground = true` and calls `codol_player_move_in_world()`
— it never propagates `walking` back to `ps`. `codol_pmove_single()` is not
called from the usercmd path at all. Jump therefore can never fire through the
network path as written.

## S-08 — Ground state in the snapshot is hard-coded `false`

`src/battle/battle_service.c:524-532` passes `false` for the `groundEntityNum`
slot (idx 61). The comment states this is deliberate: the server's collision is
degenerate (S-06) so `on_ground` would always be true, and constant 2046 made the
client enter "flight mode" and lose ADS. Constant 2047 ("always airborne") is a
workaround, not a measurement. Consequence: the client can never be told it is
standing on anything.

## S-09 — Server never sends a position after the first frame

`src/battle/battle_service.c:486`: `omit = svc->snapshot_sent;`
`src/battle/battle_service.c:414-419`: documented rollback of the "always send
position" experiment. `HANDOFF_20261025_BINARY_BISECT.md` §13 records that three
different coordinates × two send rates all produced zero client movement.

Net effect: authoritative server position is a dead feature; only the client's
own simulation moves the player.

## S-10 — Entity section is capped at 8 and carries no model reference

`src/battle/battle_service.c:425` `codol_snap_entity_t ents[8];`
`:497-510` copies only `number/type/x/y/z`. `src/entity/entity.c` allocates with
`memset` so `model_index` is always 0. `HANDOFF_20261025_BINARY_BISECT.md` §17.3
confirms: entities are accepted by the client but invisible; entity numbers 0..7
collide with the client's own slot range.

## S-11 — TX snapshot buffer is 512 bytes vs retail 7000–15000

`src/battle/battle_service.c:425` `uint8_t snap[512], payload[520];`
`HANDOFF_20261025_BINARY_BISECT.md` §16.4: retail snapshots measured at 7000-15000 B
(14962 B first frame in the 2020 corpus). No fragmentation of the downlink exists.
Ceiling ≈ 10 entities.

## S-12 — Complete-gameplay systems exist but are not wired into the live path

Verified by grep over `src/`:

| subsystem | defined | called from live path |
|---|---|---|
| `codol_projectile_spawn/step/trigger` | `world/projectile.c` | **never** |
| `codol_damage_apply` | `world/combat.c` | only from `apply_test_hit()`, which is only invoked on a fire edge against a synthetic target |
| `codol_mode_player_killed` | `world/gamemode.c:60` | **never** (no caller) |
| `codol_mode_respawn_due` | `world/gamemode.c:73` | **never** |
| `codol_replication_build` / `_ack` | `replication/replication.c` | **never** (only `init` and `commit_frame` are called) |
| `codol_world_step(..., commands, count)` | `world_assets/world.c:97` | called with `NULL, 0` from `main.c:164` — the `commands` branch is dead |

`codol_battle_service_bind_world` is now called (the 2026-10-25 fix), but the
subsystems downstream of it are still unreachable.

## S-13 — Synthetic damage target with a magic owner id

`src/battle/battle_service.c:53-74`: `ensure_damage_target()` spawns an actor at
`(0,0,-116)` and marks it `owner = 1001`. It is not a map entity. The hit is
computed from the player's position to this fixed point at fire time
(`:76-102`, hard-coded weapon `"m4a1tech_mp"`), with `CODOL_HITLOC_TORSO_UPPER`
always. No ray is cast; no line of sight; no cover.

## S-14 — Hit detection is not a bullet trace

`apply_test_hit()` uses `distance = |target.origin - player.origin|`, then
`codol_weapondef_damage_for_hit(weapon, distance, true, hitloc)`. There is no
bullet direction, no `codol_movement_trace()`, no misses. `codol_movement_trace()`
exists and is exercised by tests but never used in the damage path.

## S-15 — `apply_test_hit` is called from inside the per-command loop for *every* fire edge; health does not reset

`src/battle/battle_service.c:984-993` and `:789-798`. The target is never
respawned or healed. After ~4 hits (33 damage each on 100 hp) the target is dead
and all later fires hit a 0-health entity (`codol_damage_apply` clamps at 0).
Any long run therefore reports damage but no further health change.

## S-16 — Player position in the snapshot still uses the svc->player copy, which requires a usercmd

`src/battle/battle_service.c:482-486` reads `svc->player.{x,y,z}` in the
non-mirror branch. `svc->player` is only updated inside
`codol_battle_service_apply_usercmd()`. Before the first usercmd it is the init
value (48, -572, -116) from `:170`. That is the spawn the user reported as "on
the roof".

## S-17 — `send_gamestate` has a fixed-size 1200-byte state buffer and a 1100-byte gate

`src/battle/battle_service.c:376-389`: `uint8_t state[1200]`, rejects `n > 1100`.
A real retail gamestate is 259 B in this project's fixture but the ceiling is a
magic number; any larger gamestate is silently refused (warn + -1).

## S-18 — Gamestate is sent at most 5 times (`gamestate_attempts < 5`)

`src/battle/battle_service.c:610-611`. If all 5 attempts fail or the client does
not answer, the session never receives a gamestate again; there is no retry on
usercmd after that point.

## S-19 — `handle_stats` uses a 32-bit chunk bitmap with no bound check against count

`src/battle/battle_service.c:675-695`: `count = (total + 1237) / 1238`; with
`total` up to 32768, `count` ≤ 27 so `1u << index` is safe — but `svc->stats_chunks`
is a global field (not per-peer), so two simultaneous clients would corrupt each
other's stats state.

## S-20 — Per-connection state reset only occurs inside the key-exchange branch

`src/battle/battle_service.c:1100-1127`. `gamestate_sent`, `snapshot_sent`,
`snapshot_epoch_ms`, `processed_input_time`, FAT buffers are reset there. A
session that times out and is re-created without a fresh key exchange keeps stale
state. Also `stats_total/stats_chunks/stats_buf` are **not** reset here (S-19).

## S-21 — `svc->player` / `svc->equip` / `snap_from` / `snap_cur` / input_baselines are single-client

The battle service holds exactly one `player`, one `equip`, one baseline ring.
`CODOL_MAX_CLIENTS` is used to size the world player array, but the snapshot
encoder writes only the local client's state. Multi-client is not representable in
the current Svc struct.

## S-22 — `world.c` sets `gametype = "dm"` regardless of the lobby-selected mode

`src/world_assets/world.c:74` `snprintf(mode_config.gametype, ..., "dm");`
score_limit=30, time_limit=600000, respawn=3000 hard-coded. The lobby sends
`g_gametype coop` or `playlist` selections; none of it reaches the world.

## S-23 — Server map is a single hard-coded default

`src/main.c:64` `const char *map_name = "mp_firingrange";`
`BATTLE_CONNECT_DIVERGENCE_20261028.md` and `ROOM_PUSH_CHANNEL_WRONG_20261028.md`
§六.2 record that the room picker returns `mp_raid` / SD maps while the server
loads `mp_firingrange`. There is no path from `mmstart`'s map to `--map`.

## S-24 — World collision data is the coop clipmap, not the loaded map

`src/world_assets/world.c:66-67`: `world->clipmap = codol_static_boxes;` and
`world->map_ents = codol_static_boxes;` — both point at the compile-time
`codol_clipmap_coop_train.inc`. `--map` only sets a string
(`codol_world_init:60`) and is never used to select collision. Same conclusion is
recorded in `docs/PVE_BATTLESTART_STATUS_20261027_1220.md` §3 ("换图不会改变客户端
是否连 28960").

## S-25 — Map entity table is compiled in from a single extraction

`include/codol_mapents_coop_train.inc` is generated by `tools/gen_mapents_inc.py`
from `_map_extract/coop_train_entities.txt`. 334 entries, 333 props + 1 actor.
No regenerator is run by the build; the `.inc` is checked in as data.

## S-26 — `send_snapshot` server_time base 1000 ms

`src/battle/battle_service.c:436` `server_time = 1000 + (now_ms - epoch)`.
Magic offset. Whether the client expects the epoch at 0 or 1000 is not stated in
code or docs.

## S-27 — `svc->snap_from = svc->snap_cur` happens before `send_frame`

`src/battle/battle_service.c:541`. If `send_frame` fails, the baseline has already
advanced; the next frame deltas against a state the client never received.

## S-28 — Keymap CSV writer opens with mode "w" on first usercmd and never closes

`src/battle/battle_service.c:805` `km = fopen("keymap_cal.csv", "w");` — file
truncated at start of every session, `fopen` result never `fclose`d. Also a stray
escaped `"\\n"` in the header at `:1002` writes a literal backslash-n in the
non-FAT branch.

## S-29 — `handle_netchan_frame` and the inline non-FAT path are duplicated

`src/battle/battle_service.c:708-839` and `:923-1053` contain near-identical
usercmd/reliable/fire/keymap logic. Divergences already exist (the escaped header
newline in one, the `CMD_FIELD_CHANGE` logger only in the other). Any fix must be
applied twice.

## S-30 — `_gs_adapt_dynamic` rewrites the gamestate in place with no length check on the receiving side

`src/battle/battle_service.c:302-372`. `memmove(state + hdr_len_new, state + pos, rest_len)`
is only bounded by `hdr_len_new + rest_len > cap`. `rest_len = *len_io - pos`, and
`pos` is computed by `strlen()` on attacker-controlled (map) strings read from
`active_room.json`. A map name without a NUL inside the 1200-byte buffer would
read past it.

## S-31 — `active_room.json` is read from the process CWD each snapshot

`src/battle/battle_service.c:391` `snprintf(room_path, ..., "%s/active_room.json", ".")`.
Same for `firingrange-gamestate.bin` (`:175`), `snapshot_entities.on` (`:178`),
`keymap_cal.csv` (`:805`). The battle server's behaviour depends on whatever the
current directory contains — no configuration file, no arguments.

## S-32 — `input_baselines` ring slot collision ignored

`src/battle/battle_service.c:575-584`: `slot = seq % 513`. `input_baseline_count`
is incremented but never used to detect that a slot was overwritten while a
client could still be using it (ack lag > 513 frames).

## S-33 — Hard-coded crypto test vector / no key rotation

`src/crypto/*` implements AES-128, SHA-1, P-224. `tests/test_crypto.c` and
`test_p224.c` pin fixed vectors. There is no evidence in `src/` of a per-session
key derivation beyond the ECDH in `battle.c`; `stats` traffic and OOB are all
inside the same encrypted frame. No rekey path.

## S-34 — `send_oob_text` buffer is 512 bytes, no length check

`src/battle/battle_service.c:643-652`: `buf[4 + tl] = 0` with
`tl = strlen(text)`. Current callers pass short strings, but `statResponse %u` and
`challengeResponse 1` are the only ones; a future longer reply overflows.

## S-35 — `handle_plain` parses OOB only when `plain[0..3] == 0xFF`

`src/battle/battle_service.c:847`. If the client's OOB framing changes (e.g. a
`getchallenge` variant without the 4×FF prefix) the packet falls into the netchan
branch and is parsed as a frame body.

## S-36 — `world.c:128` player entity spawn position is a literal, duplicated in three files

`(48, -572, -116)` appears in:
- `src/world_assets/world.c:128`
- `src/battle/battle_service.c:170`
- `src/world/collision.c` implicitly via `codol_ground_z = -116`

No single constant; changing spawn requires all three.

## S-37 — No mechanism to report server state to the client for map load

`send_gamestate` sends the file `firingrange-gamestate.bin` with a `+4` seq header
and an XOR mask. There is no code path that answers `gamestateupdate <n>` with
anything other than "stop resending". The client's `CA_LOADING → CA_CONNECTED →
CA_GAMESTATE → CA_PRIMED → CA_ACTIVE` progression
(`docs/PVE_STUCK_INVESTIGATION_20261027.md` §4) is only observed up to whatever
point the client gets on its own; the server never verifies the state.

## S-38 — `codol_world_step` is called at 20 Hz in `main.c` but snapshots at 128 Hz

`src/main.c:154` tick interval from `--tick` default 20; `src/battle/battle_service.c:412`
`CODOL_SNAP_DT_MS 7` (≈143 Hz) and the comment says 128 Hz. The world only steps
50 ms while the snapshot requests a frame every 7 ms; most snapshots carry the
same `svc->player` state, and `codol_mode_tick(mode, 16)` in `world.c:106`
hard-codes 16 ms regardless of actual elapsed.

## S-39 — `session_check_timeouts` uses a different clock than the battle service

`main.c:165` `codol_session_check_timeouts(server, now)` where `now` is
`codol_platform_time_us()`, while `battle_service_tick` overrides its `now_ms`
with `mono_ms()`. Two clocks in one loop; the battle service's comment at :596-599
says this caused a comparison that "永远不成立".

## S-40 — `tests/test_snapshot_delta.c` still encodes the *old* assumption in a comment

`tests/test_snapshot_delta.c:89` comment says `玩家永远不离开地面 ⇒ on_ground 恒 true`,
but production code now always sends `false` (S-08). The test passes because it
only checks sizes, not the semantic.

---

## Contradiction register (source vs. docs)

| # | Doc claim | Source reality |
|---|---|---|
| C-1 | "22/22 tests pass" = quality bar | 3 probes and e2e client outside ctest (S-05) |
| C-2 | "world damage / collision closed" | `apply_test_hit` is a distance formula, not a trace (S-14); projectiles never spawned (S-12) |
| C-3 | "gamemode state machine closed" | `codol_mode_player_killed` / `respawn_due` never called (S-12) |
| C-4 | "full match lifecycle implemented" | No caller closes the loop; server map never changes (S-22/S-23) |
| C-5 | `HANDOFF_20261025 §17` "client accepts the entity section" | Accepted ≠ parsed ≠ rendered; no model index sent (S-10) |
| C-6 | `INMATCH_COMPLETENESS_GAP_MATRIX` "transport handshake DONE" | Contradicted by 2026-10-28: battle server zero RX in every BOT-room run (`BATTLE_ZERO_RX_ROOT_CAUSE_20261028.md`) |
| C-7 | `SNAPSHOT_FIELD_DIFF` "idx61 dynamic" | Rolled back; production sends constant false (S-08) |
| C-8 | "position sent every frame" | `omit = snapshot_sent` → never after frame 1 (S-09) |
