# Zombie walk looks choppy: the origin goes out as a STATIONARY integer, and the fix

Date: 2026-09-21. Scope: `zm_prototype_sh`, build 518b3190, the session in
`bin/home/main/qconsole.log` (3,889 `CoDOL actor:` lines, 123 `CoDOL anim:`
lines, one connected loopback client). User report: "they work now, but
their animations are a bit choppy". Dogs (same actor subsystem) were
reported smooth.

Everything below is MEASURED from the log, the retained source/asm, the C1
client disassembly and the T5 reference unless marked INFERRED. This worker
did not link, promote or start the server; the objects-only build passes.

---

## 1. The single cause

**Every actor origin producer ends in the retained `G_SetOrigin`, which
publishes the entity as `TR_STATIONARY`, and the C1 entity origin codec is
integer.** A zombie walking at 15 u/s therefore reaches the client as an
origin that advances by exactly one whole unit every ~4 snapshots, and the
client, told the entity is stationary, places it on that integer without
interpolating between snapshots. That is the stepping the user sees. A dog
moves ~17 units per frame, so the same integer wire is a 3 % error for it
and its stepping is invisible.

The animation state on the wire is NOT the cause (section 4): the walk clip
is delivered once as a knob-all command and the client runs the tree
itself; the only per-snapshot payload for an actor is its entity state.

The fix is what T5's own MP actor does every frame (section 6): publish the
actor's `pos`/`apos` trajectories as `TR_INTERPOLATE` (C1 mode 1) so C1 lerps
the actor between the two snapshots it holds instead of snapping to the
newest one.

## 2. Measurements

### 2.1 Origin cadence (hypothesis 1) -- the cause

| quantity | zombie (this session) | dog (2026-09-16 session, `qconsole.log.quit2`) | source |
|---|---|---|---|
| server tick | 60 Hz (`phys ok 60` per actor-second; `bin/START-CODOL-SERVER.cmd:136 +set sv_fps 60`) | 20 Hz then (`phys ok 20`) | log |
| root motion per frame | `rm (0.26 0.00 0.00)` (225 lines), 0.23..0.27 (500+ lines) | `rm (16.88 0.00 0.00)` (72 lines) | `CoDOL actor:` / `CoDOL dogs:` diag, `lastTranslation` printed by `codol_actor_lifecycle.cpp:881` |
| speed | `moved 15/s` (221 lines) / `16/s` (155) for ent 576; a 100..105 u/s burst while chasing | 338 u/s (16.88 x 20) | log |
| snapshot cadence to this client | every server frame: loopback/LAN recipients get `nextSnapshotTime = svs.time - 1` (`sv_snapshot.c:699`) | same | source |
| units per snapshot | **0.26** | ~17 | derived |
| origin codec | integer: `position()` rounds both sides with `floor(x+0.5)` and writes a 16-bit whole-unit offset (`codol_delta.c:103-120`); C1's reader is the same on both arms: narrow `from + (Bits(7) - 64)`, wide `fistp` integer around POS_BASE (`docs/CODOL_SNAPSHOT_BITMASK_AUDIT_20260916.md:59`, MATCH) | same | source |
| integer error per snapshot | 100 % (origin advances 0,0,0,1,0,0,0,1 ...) | ~3 % | derived |
| trajectory type on the wire | mode 0 (`TR_STATIONARY`) | mode 0 | `G_SetOrigin`, below |

`G_SetOrigin` (`src/asmsource/_g_utils_mp.asm:748-773`) stores `trBase`
(+0x18) and `currentOrigin` (+0x13c) and zeroes `trType`, `trTime`,
`trDuration` (+0x0c/+0x10/+0x14) and `trDelta` (+0x24..). It is the only
origin writer on every actor path: `CODOL_ActorMoveDelta`
(`codol_actor_lifecycle.cpp:586`), `CODOL_ActorPhysicsMoveMode`
(`codol_actor_physics.cpp:93` and `:137`), the stuck-recovery teleport
(`codol_actor_lifecycle.cpp:966`) and the spawn. No actor code sets
`s.lerp.pos.trType` afterwards (`grep trType src/codol/player/` is empty).
The wire converter `trajectory()` (`codol_engine_state.c:1658`) maps
`TR_STATIONARY` to mode 0 and every actor eType-18 table row carries the
mode at +0x00c/+0x030 (`codol_entity_fields.inc:1248-1249`).

What C1 does with mode 0 versus mode 1 (`tools/codol_c1_disasm.py --range
0x443300 0x443530`, the entity lerp dispatch the existing comments call
0x443337):

```
00443337  cmp eax, 9            ; pos.trType == 9 (physics) -> 0x847d9fb
00443354  cmp eax, 1            ; pos.trType == 1 (TR_INTERPOLATE)
00443359  cmp [ebx+0xf0], 9     ;   unless the previous state was physics
00443365  call 0x442ac0         ;   -> interpolate between the two held snapshots
0044337e  cmp eax, 3            ; TR_LINEAR_STOP and eType >= 19 -> interpolate too
004433d9  call 0x40ca40         ; everything else: BG_EvaluateTrajectory(pos)  (mode 0 = trBase)
004433ed  call 0x40ca40         ;                  BG_EvaluateTrajectory(apos)
```

So with mode 0 the client evaluates the newest snapshot's integer `trBase`
directly every render frame: the zombie holds still for ~3 snapshots and
jumps one unit, ~15 times a second. With mode 1 it lerps from the previous
snapshot's origin to the next over the snapshot interval, which is what
players (whose `BG_PlayerStateToEntityState` sets `TR_INTERPOLATE`) and the
vehicles here (`codol_vehicle_ground_publish.cpp:53`) already get.

### 2.2 Why dogs looked smooth

Same producer, same codec, same mode 0. The difference is only the number
of units per snapshot: 17 for the dog (integer error 3 %, and even the
20 Hz stepping of that session was at 17 u steps along a straight run)
against 0.26 for the zombie (the origin cannot express the motion at all
between whole units). The user's observation is consistent with a
speed-dependent quantisation artefact and not with anything in the
animation channel, which both species share unchanged.

### 2.3 Residual after the fix (honest limit of the C1 wire)

The codec is integer on the client side, so a 15 u/s actor still advances
one unit per ~4 snapshots after the change; interpolation spreads each unit
over a 16.7 ms snapshot interval instead of presenting it as a jump, and
the angles (16-bit, 1/182 deg) are lerped as well. This is the same wire
CoD has always used for other players' entities (a running player is
~3 u/snapshot at 20 Hz); the effect is only visible for very slow movers.
If the walk still reads as micro-stepping at close range, the next lever is
the zombie's speed (15 u/s is a crawl; `ai_zombie_walk_v7` at `rate 0.50`
is what the log shows, and the T5 walk is authored at rate 1), which is not
this worker's file.

## 3. Animation state on the wire (hypothesis 2) -- not the cause

* Actor animation is NOT in the entity state. The eType-18 table has no
  animation word: +0x058 is `slot | tree<<8` (C1 42A69E / 428BA6), the
  player anim words +0x0d8/+0x0dc are `hint 1` rows the actor overlay never
  writes.
* It travels as animation COMMANDS (`CODOL_WriteAnimCommands`,
  `codol_animcmd.c:34`): the script layer journals one event per builtin
  call (`codol_script_anim.c:anim_publish`, type 5 = knob-all, `sub` =
  root anim, `arg2` bit0 complete / bit1 restart), and the frame builder
  appends the recipient's pending journal range to the snapshot
  (`codol_frame_builder.c:171-219` -> `CODOL_ActorDeliveryPrepare`). C1
  applies them to its own XAnim tree (0x443e90 type dispatch: type 5 ->
  0x63b9c0/0x63bad0 = knob-all) and advances the clip on its own clock.
* Delivery cadence MEASURED: the zombie GSC re-issues
  `setflaggedanimknoball(ai_zombie_walk_vN, %body, 1, 0.2, rate)` every
  ~10 s per zombie (ent 576: actor-seconds 12, 22, 32, ... 245), 112 walk
  knobs over the session, all without restart. On the client that is a
  no-op on a clip already at goal 1 / weight 1 (no time reset: restart bit
  is 0). No `animation delivery ... dropped` warning was printed (0
  matches for `delivery` in the log), so no frame lost its commands.
* Knob-all encoding (hypothesis 2's "nested root" concern): type 5 writes
  `ref` (11 bits) then `sub`: a 1-bit "is root 0 or 3" arm, else the
  11-bit root (`codol_animcmd.c:64-68`). `%body` is entry 2, so it takes
  the 11-bit arm; nothing is lost. The dog's direct knobs are type 4 and
  never use `sub`.
* Bootstraps (a new delivery timeline re-sends the whole tree with a type 6
  `SetTime`) happen only when the recipient's visible-actor set changes,
  when the killcam toggles replay, or when the acknowledged snapshot is not
  in the 32-deep history (`codol_actor_delivery.cpp:Prepare`,
  `codol_actor_anim_journal.c:Capture`). They are not per-snapshot. Their
  cadence was not measurable from this log (no line for them existed);
  section 7 adds one so the next boot records it.

## 4. Clip rate versus server tick (hypothesis 3) -- not a per-snapshot resync

There is no wire field that re-syncs the clip time every snapshot. The only
time-bearing command is type 6 (`SetTime`, 5-bit fraction = 1/31 of the
clip, `codol_animcmd.c:72`), emitted solely inside a bootstrap. The
playback rate is 5 bits over 0..2 (`playback_rate()`, `:27-32`):
`0.50 -> 8/31*2 = 0.516`, `0.53 -> 0.516`, `0.60 -> 0.581`. INFERRED
consequence: the client's foot cycle runs ~3 % faster than the server's
root motion for the 0.50/0.53 zombies -- a slight foot-slide, not a
stutter, and identical in kind to what the dog gets.

## 5. The per-second diagnostic (hypothesis 4) -- ruled out

The three `Hitch warning` lines (2147, 4720, 4482 ms; log lines 79, 189,
427) all precede the first actor line (444) -- they are map/zone load.
After that there is no hitch line in 3,889 actor lines. `ActorDescribeTree`
prints once per actor per second and is bounded; frame time is not the
problem.

## 6. What the reference does

OpenBLOPS (T5) `Game/Server/game_mp/actor_mp.cpp:1491-1504`, in the per-frame
actor update after `Actor_CallThink`:

```
isRagdoll = Com_IsRagdollTrajectory(&self->s.lerp.pos);
AssignToSmallerType<unsigned char>(&self->s.lerp.pos.trType, isRagdoll ? 14 : 1);
Vec3Copy(self->r.currentOrigin, self->s.lerp.pos.trBase);
...
isRagdoll = Com_IsRagdollTrajectory(&self->s.lerp.apos);
AssignToSmallerType<unsigned char>(&self->s.lerp.apos.trType, isRagdoll ? 14 : 1);
Vec3Copy(self->r.currentAngles, self->s.lerp.apos.trBase);
```

Every live actor frame is published as `TR_INTERPOLATE` for both tracks,
ragdolls keep their own type. C1's dispatch above has exactly the mode-1
interpolation arm this relies on. Our port never had the equivalent because
`G_SetOrigin` was the last writer on every path.

## 7. The change

### 7.1 `src/codol/snapshot/codol_engine_state.c` (CRLF, 2080 -> 2101 lines, CR count == line count) -- the fix

`CODOL_OverlayEngineEntityVisible`, `ET_ACTOR` branch: after the slot/tree
word, a `TR_STATIONARY` `pos` trajectory is written to the wire as mode 1
(+0x00c) and a `TR_STATIONARY` `apos` as mode 1 (+0x030). Any other
trajectory type (ragdoll 10..12/14, physics 9, linear) keeps its own mode.
Applied at the wire so the live snapshot and the archived (killcam) actor
states agree, and so no producer in `codol_actor_lifecycle.cpp` /
`codol_actor_physics.cpp` (another worker's file) had to change. The
`trBase`/`trDelta`/`trTime` payload is untouched.

### 7.2 Bounded measurements added (all off after their cap, developer-independent)

* `src/codol/snapshot/codol_frame_builder.c` (LF): `CoDOL actor wire:
  client C seq S time T cmds N | ent E mode M org (x y z) d (dx dy dz) wire
  (ix iy iz) ...` -- one line per actor-bearing snapshot, first 150 such
  snapshots of the process (2.5 s at 60 Hz). `d` is the float delta since
  the previous snapshot that carried that entity, `wire` the whole-unit
  delta the codec will publish, `mode` the pos trajectory type as sent
  (expect 1), `cmds` the animation commands appended.
* `src/codol/player/codol_actor_delivery.cpp` (CRLF, 148 -> 166): `CoDOL
  actor: delivery timeline T for client C at seq S (ack A): <reason>; N
  visible actors, B bootstrap commands, cut time X` on every timeline
  change, first 64.
* `src/codol/player/codol_actor_anim_journal.c` (LF): `CoDOL actor:
  bootstrap replayed to client C at seq S: acknowledged A not in delivery
  history (...)` when a bootstrap is re-sent into an established timeline,
  first 64.

### 7.3 Build

`tools\BUILD-CODOL.ps1 -ObjectsOnly`: `build OK (exit 0)`;
`codol_engine_state.o`, `codol_frame_builder.o`, `codol_actor_delivery.o`,
`codol_actor_anim_journal.o` rebuilt. The only warning is the pre-existing
`-Wmisleading-indentation` at `codol_engine_state.c:803`. Not linked, not
promoted, server not touched.

## 8. What the next boot must show

1. `CoDOL actor wire:` lines with `mode 1` for every zombie entity, `d`
   around `(0.26 ...)` per snapshot along the walk direction and `wire`
   mostly `(0 0 0)` with a `1` every ~4 lines -- the integer stream this
   document predicts. `cmds` should be 0 on almost every line (commands
   only on knob or bootstrap snapshots).
2. `delivery timeline` lines only at first sight of the actors and when
   zombies enter/leave the client's view; no `bootstrap replayed` lines in
   steady state. If `bootstrap replayed` prints every snapshot, the
   published/acknowledged sequence spaces have diverged and THAT becomes
   the next cause (each replay would re-`SetTime` the clip).
3. On screen: the zombie no longer freezes-and-jumps between snapshots; it
   slides continuously between integer positions, and its turning is
   lerped. Dogs unchanged.
