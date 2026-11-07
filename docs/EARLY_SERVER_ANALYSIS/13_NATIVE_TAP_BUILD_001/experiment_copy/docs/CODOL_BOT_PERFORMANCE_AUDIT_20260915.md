# Bot performance: command-local visibility duplication

Source-audited optimization, staged for parent review. No timing benchmark,
automated test, launch, debugger attachment or runtime mutation performed.
Do not attribute the user's entire lag to this issue without profiling.

## Proven repeated work

`src/codol/player/codol_bot.c::CODOL_BotBuildCommand` calls `acquire`, which:

1. Traces an existing valid enemy from the bot eye to target eye minus one
   quarter of target view height, using G_LocationalTrace mask0x2806831.
2. Unless that enemy is close or explicitly script-selected, scans candidates
   and can trace the same current enemy again.
3. On return, BuildCommand traces the selected enemy again for ADS/fire.

There is no script callback, simulation step, command execution or world update
between these reads. An existing close visible enemy causes exactly two same
endpoint traces per bot command. A farther visible current enemy in the scan
can cause three. Newly acquired targets are also traced during acquisition and
again before firing. These are source call counts, not sampled milliseconds.

`obj/bot-performance-audit/visibility-reuse.patch` changes acquire to return
whether the final selected target was actually seen during this command. Its
existing lastKnown and lastSeen writes already preserve the tested aim point.
The candidate scan skips the current enemy already checked, including its
negative visibility result. BuildCommand consumes the returned observation.

No visibility survives across commands. No FOV, target validity/generation,
trace origin/endpoint/mask, reaction delay, memory duration, aiming, ADS hold,
trigger cadence or reload rule changes. A remembered but occluded target
returns false, so memory cannot authorize firing. An invalid/recycled target
is still cleared before evaluation; acquisition of another visible target
retains its own current command result.

With a close visible enemy this removes one of two visibility traces; with the
same farther enemy it removes up to two of three. Other candidate sight tests
remain, so this is not a claim of halving total bot/frame cost.

## Other inspected paths; unchanged

- `CODOL_BotNavRouteFiltered` uses A* with an O(V²) open-set scan and Euclidean
  edge/heuristic distances. Current supplied graphs have229 Bog nodes and181
  Killhouse nodes. `route` gates searches to1000ms and keeps an intact route to
  the unchanged goal. Stalls invalidate their actual blocked edge; this is not
  an unconditional route search every command. Heap/index work needs separate
  evidence and review; it is not part of this patch.
- `CODOL_UpdatePlayerWorldWeapons` reuses generation-checked native child
  entities. It recreates on player generation/weapon/hand-count changes or a
  missing child. Per-frame G_GeneralLink and SV_LinkEntity remain necessary to
  follow the animated parent. No unconditional worldgun model creation found.
- `codol_bot_loadout.c` composer calls are in the explicit bot loadout VM path,
  not CODOL_BotBuildCommand. No evidence found here of recomposing weapons each
  command. Character publication/model cache lookup is separate from targeting.
- Entity-link capture scans the entity pool per frame and native DObj work is
  also present, but no measured dominant cost established. Do not remove
  animation/link updates merely to reduce work; they produce actual gameplay
  and snapshot state.

Parent independently owns routine movement/collision/pacing log gating via
codol_movementDebug. This staged source does not alter logging or shared files.
Patch and full source snapshot are under obj/bot-performance-audit; use patch
after review, not a stale full-file overwrite.
