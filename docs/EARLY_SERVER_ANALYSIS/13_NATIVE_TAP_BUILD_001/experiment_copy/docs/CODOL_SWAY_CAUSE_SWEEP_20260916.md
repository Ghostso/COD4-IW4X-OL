# Scoped sniper sway jitter — cause sweep (2026-09-16)

Research/enumeration pass. **No fix is written here.** Everything is marked
`[DIS]` (read out of C1.exe disassembly), `[MEAS]` (measured from
`docs/captures/sway_live3.jsonl`, 4169 rendered frames, 3879 of them scoped),
`[SRC]` (read out of this server's source) or `[INF]` (inferred).

Prior state of play is the 2026-09-16 15:40 / 16:35 / 17:00 / 19:30 / 20:45
entries in `docs/CODOL_IMPLEMENTATION_PASS.md`. Nothing already ruled out there
is re-derived.

---

## 0. Executive summary — what this pass actually settled

Three things moved from "hypothesis" to "measured", and they collapse most of
the candidate space:

1. **The drawn sway phase is not an accumulator. It is rebuilt from ZERO on
   every rendered frame and equals `3 x (predicted ps.commandTime - snapshot
   ps.commandTime)`.** `[MEAS]` The seed at `predCmd == snapCmd` is **exactly
   0**, not "non-zero" — the earlier "no decrease lands on 0" reading was an
   artefact of never sampling a frame with an empty replay. 126 scoped frames
   in the capture have `swayPhase == 0` exactly, including frames whose
   snapshot age was 129-136 ms.
2. **The unexplained factor of 2 in the `+3.000/ms` rate is RESOLVED and is
   not a bug.** `[DIS]` `0x0045E830` advances the phase **twice** per replayed
   usercmd: once via `BG_AdvanceSwayPhase 0x00424B90` (`hbs * dt * 1000 *
   speed`) and once inline at `0x0045E891..0x0045E8A5` (`dt * 1000 * speed`,
   with **no** hold-breath factor). `speed = 1.5` at `fWeaponPosFrac == 1`, so
   the replay rate is `2 x 1.5 = 3.0` units per ms. This is C1's own code;
   vanilla does it too. **Close this lead.**
3. **The phase sawtooth accounts for essentially all of the measured jitter.**
   `[MEAS]` Modelling the drawn offset as
   `pitch = sin(phase*0.0007)*A*0.01`, `yaw = sin(phase*0.001)*A*0.01`,
   `A = stanceRamp*40*posFrac*holdBreathScale`, the predicted frame-to-frame
   jump magnitude is **med 0.01731 deg / p95 0.11339 deg**, against the
   measured clean **med 0.01726 deg / p95 0.13237 deg**. There is almost no
   residual left for a second cause. Any remaining candidate must be a
   candidate for *why the phase sawtooths*, not for an independent wobble.

The measured frame table that makes this unambiguous (scoped, hbs = 1.000):

```
 cgTime  ftime  snapCmd  predCmd  age  phase  phase/age   d(phase)
 127852     12   127804   127852    48    142    2.958      -178
 127864     12   127804   127864    60    178    2.967        36
 127875     11   127804   127804    71      0    0.000      -178   <-- empty replay, phase EXACTLY 0
 127888     13   127804   127888    84    248    2.952       248
 127900     12   127840   127900    60    178    2.967       -70
```

### Two falsifiable predictions that test the whole model for free

Because the second add at `0x0045E8A5` is **not** scaled by `holdBreathScale`
and **not** gated on `fWeaponPosFrac != 0` (the guards live inside
`BG_AdvanceSwayPhase 0x00424B90`), the model makes two sharp predictions that
cost nothing to check in the same capture:

| state | first add (`0x00424BFE`) | second add (`0x0045E8A5`) | predicted rate |
|---|---|---|---|
| scoped, `holdBreathScale = 1` | `1.5 x 1.0` | `1.5` | **3.000 / ms** (measured 2.96 ✔) |
| scoped, holding breath (`hbs -> 0`) | ~0 | `1.5` | **1.5 / ms — it should HALVE, not stop** |
| hip fire (`fWeaponPosFrac = 0`) | skipped by the internal guard | `5.0` (`def+0x6F8`) | **5.0 / ms** |

If a hold-breath capture shows the phase *frozen* rather than halved, or a
hip-fire capture does not show ~5.0/ms, the whole "phase = replay span x rate"
model is wrong and the sweep needs restarting. **Run this first — it is one
capture and it validates or destroys everything below.**

`2.96` rather than `3.00` is the `ftol` truncation of ~10 adds per frame
(2 adds x ~5 replayed commands), which is also why the per-frame residual
`phase - 3*(predCmd-snapCmd)` sits flat at **-3 to -5** across the whole
epoch `[MEAS]` — flat, i.e. **no accumulation at all between frames**, which is
what proves the per-frame rebuild.

So the question is now narrow and concrete: **what writes 0 into `cg[0xBF980]`
once per rendered frame, and what is it supposed to write instead?**

### Decision aid — the ranking at a glance

The drawn sway is `seed + 3 x (predictedPS.commandTime - snapshot ps.commandTime)`.
Two things independently determine whether that is smooth:

* the **seed** — `ps[0x4A0]`, which the server never produces, so it is 0 on
  every snapshot. This is the **generator** of the sawtooth.
* the **step in `snapshot ps.commandTime`** — which sets the sawtooth's
  amplitude (`drop = 3 x step`). This is the **amplitude modulator**, and it is
  independently broken (R1d).

Fixing the seed removes the jitter regardless of the step. Fixing the step
alone only halves it.

| # | candidate | status | worth spending time on? |
|---|---|---|---|
| R1 | `ps[0x4A0]` force-sent every ADS snapshot carrying 0 | **generator; effectively confirmed** | **yes — this is the fix** |
| R1d | published `ps.commandTime` advances in `{0, 0, ~35 ms}` lumps | **amplitude modulator; confirmed server-side** | **yes — explains the exact drop sizes** |
| R2 | missing per-frame writer of `cg[0xBF980]` | open, structural | yes, but behaviourally (see R2b) |
| R2b | C1 is VM-protected; static sweeps are not exhaustive | new, methodological | **yes — changes how to look** |
| R3 | server has no sway-phase producer at all | source fact | yes, prerequisite for R1 |
| R4 | server rate must match the client's 2x replay rate | predicted 2nd-order failure | yes, before attempting R1 |
| R1b | `ps[0x4A0]` is snapshot-interpolated | corroboration | no work needed |
| R17 | spawn publishes `commandTime = level.time - 100` (backwards) | new, one-off +300-unit kick | yes, cheap |
| R18 | dvar `"1871"` / `cl_paused` freeze the clock and force viewangles | new; explains the "prediction stalls" | yes, one read |
| R19 | merged server frames + uncapped hitch catch-up | new; trips C1's 500 ms reset band | yes, separately |
| R20 | `cg.time` jumped at `0x0046DC09` without a matching `cg.frametime` | new, minor | only if R1 fails |
| R2c | lean + earthquake/rumble also in the drawn offset | new confounder | only if jitter shows at 4.0/7.5 Hz |
| R1c | killcam enter/leave thrash zeroing the phase | **KILLED** — `deltaTime` is zeroed every frame | no |
| R5 | `otherFlags & 0x1800` -> spurious `CG_Respawn` | **killed three ways** | no |
| R6 | ftol truncation | quantified, too small | no |
| R7 | `cg[0xBF984]` gate flicker | **killed by measurement** | no |
| R8 | `cg[0xB035C]` skipping the aggregator | **killed by measurement** | no |
| R9 | "is it even the idle sway" | answered: yes | no |
| R10 | second aggregator `0x00425020` | not on the render path | no |
| R11 | third `&phase` consumer `0x0047D330` | disputed between sweeps — see R11 | low |
| R12 | client time base (`CL_AdjustTimeDelta`, interpolation) | fully decoded; not the generator | only if R1 fails |
| R13 | dvars in the sway chain | no dvar reaches the phase | no |
| R14 | changeHint-2 second pass | field is index 4 | no |
| R15 | codec/delta-base fault on `ps[0x4A0]` | ruled out by construction | no |
| R16 | `ps->deltaTime` published, never assigned | resolved: zeroed every frame | no |

---

## Ranked candidates

### R1 — `ps[0x4A0]` (the ADS sway phase) is force-sent every scoped snapshot carrying the value 0
**Rank: 1. This is now effectively confirmed as the cause; only the exact
write site is open.**

* **Mechanism** `[DIS]+[SRC]` `{0x04a0, -70, 3}` is netfield index 4 of C1's
  playerstate table (`src/codol/snapshot/codol_player_fields.inc:8`). This
  server's own replication of C1's send predicate
  (`src/codol/snapshot/codol_playerstate.c:50`, ported from C1
  `0x5a44b0..0x5a4561`) contains a **special case for `bits == -70`: the field
  is FORCE-SENT whenever `ps[0x348]` (fWeaponPosFrac) != 0.0f** — i.e. on every
  snapshot while the player is aiming down sights. That predicate is proof from
  C1's own wire code that `ps[0x4A0]` is the ADS sway phase and that vanilla
  refreshes it on the client every ADS snapshot.
  `src/codol/snapshot/codol_engine_state.c` emits `0x4a4`/`0x4a8`/`0x4ac`
  (melee charge) and **never writes `0x4a0`** — a repo-wide grep finds the
  offset only in the field table. So the field is transmitted every scoped
  snapshot carrying 0, and the client's phase is pinned to a 0 seed.
* **Predicted signature vs measured** Exact match on all four discriminators:
  the `+3.000/ms` rate (= C1's replay double-add at `speed 1.5`), the
  snapshot/frame-locked reset, the reset **value** (0, as measured — the brief's
  "non-zero reset values" were observations of `phase` *after* the replay had
  already run, not of the seed), and the 33.7% of jumps with nothing on the
  wire (the phase is a pure function of the replay span, which changes every
  frame regardless of wire content). It also explains the two user-visible
  facts: hold breath kills it (amplitude `A` is proportional to
  `holdBreathScale`, and `BG_AdvanceSwayPhase`'s add is too), and it is present
  while standing still (idle sway is the only live contributor when
  `|vel.xy| = 0`; see R9).
* **Confirming evidence** Publish a monotonically-advancing `ps[0x4A0]` and
  re-run the probe: the measured seed at `predCmd == snapCmd` should become
  non-zero and should track the server's accumulator; `phase` should become
  continuous across snapshot boundaries and the sawtooth should vanish.
* **Killing evidence** If the per-frame write of 0 turns out to come from a
  site that does **not** source `nextSnap->ps[0x4A0]` (see R2), publishing the
  field alone will not fix it.
* **Cheapest decisive test** A 30 s stationary scoped capture after publishing
  a deliberately distinctive ramp (e.g. `ps[0x4A0] = ps->commandTime * 3`) will
  show the client seed following it. If it does, the chain is proven end to end.
* **Implementation warning for whoever fixes it** `[DIS]` The client's replay
  advances at **2 x speed** per command (`0x0045E830`'s double add) while
  `BG_AddIdleSway`'s per-frame call advances at **1 x speed**. The server's
  accumulator must match the client's *replay* rate over the replayed span, or
  a residual sawtooth of the difference will remain. Also note the second add
  is **not** scaled by `holdBreathScale`, so the two adds are only equal when
  `hbs == 1`.

### R1d — NEW: the published `ps.commandTime` advances in `{0, 0, ~35 ms}` lumps, and that sets the sawtooth's amplitude
**Rank: 2. Confirmed from the server's own telemetry. This is what makes the
drop sizes exactly what they are, and no `sv_fps` value can fix it.**

* **Mechanism** `[SRC]` Usercmds are executed **on receipt**, the whole packet
  drained in one burst: `NET_Sleep` -> `SV_PacketEvent` (`src/sv_main.c:2120`)
  -> `SV_ExecuteClientMessage` -> `SV_UserMove` (`src/sv_client.c:1146`) ->
  the drain loop at `src/sv_client.c:1303-1337`. There is **no per-frame client
  think**: `G_RunClient` (`src/asmsource/_g_active_mp.asm:133-143`) calls
  `ClientThink_real` only when `g_synchronousClients` is set, and its default
  is 0 (`src/g_sv_main.c:712`). So `ps->commandTime` jumps by a whole packet
  (~35 ms, 3 cmds) on the frame a packet lands and **does not move at all** on
  every other frame.
* **Measured, already in the log** `[SRC]` `CODOL_PacingSnapshot`
  (`src/sv_snapshot.c:236`, reported by
  `src/codol/snapshot/codol_snapshot_pacing.c:102-140`) across **147
  consecutive windows** in `bin/home/main/qconsole.log`:

  ```
  CoDOL pacing: c12 n 58 advance mean 16.9 sd 18.6 min 0 max 64 near 0
     short 31 long 27  P(short|long) 0.926 P(short|short) 0.200
     cmds/snap 1.45 pkts/snap 0.48 cmds/pkt 3.00 wall/snap 17.2
  ```

  `near 0` in **all 147 windows** — the advance distribution has *zero* mass at
  the snapshot interval; it is purely bimodal. `min 0` with `short ~ 31/58`
  means **50-55% of snapshots publish a `ps.commandTime` identical to the
  previous one**. Closed form: `repeat fraction = 1 - pkts/snap`.
* **Predicted signature vs measured — this is the strongest quantitative match
  in the whole sweep.** Since `phase = seed + 3 x (predCmd - snapCmd)`, a step
  of `S` ms in the snapshot's `commandTime` produces a drop of exactly `3 x S`
  units.
  - At `sv_fps 20` (the conditions the capture was taken under): snapshot
    interval 50 ms > packet interval ~35 ms, so each snapshot swallows 1 or 2
    packets -> steps of 35 or 70 ms -> **drops of 105 or 210 units at ~20 Hz**.
    `[MEAS]` measured **~19 Hz, drop median 88 (= 29.3 ms), p90 187
    (= 62.3 ms)**. Match within ~15%, the residual being `cg.time` advancing
    during the render frame in which the drop is sampled.
  - At `sv_fps 60` (today): snapshot interval 16.7 ms < packet interval ~34 ms,
    so the step is `{0, 0, ~35}` -> **~104-unit drops clocked at the PACKET
    rate, ~29-30 Hz**, with half the snapshots carrying no drop at all.
  **Raising `sv_fps` removed the 210-unit drops but cannot remove the 104-unit
  ones — the floor is set by the CLIENT's 3-cmd/~35 ms batching, not by
  `sv_fps`.** That is why the earlier `sv_fps 20 -> 40 -> 60` work reduced the
  symptom without eliminating it.
* **Relationship to R1** Orthogonal and complementary. With a correct seed the
  lumpiness is invisible (the seed rises by `3 x S` exactly as the span falls
  by `S`). With a correct step but no seed, the sawtooth persists at about half
  the amplitude. **R1 is the cure; R1d is why the symptom has the size and rate
  it does, and it is a genuine defect in its own right.**
* **Cheapest decisive test** Already run and already in the log (`near 0`,
  `min 0`). To bind it to the client: log `svs.time`, `frame->ps.commandTime`
  and the advance **per snapshot** (not the 1 Hz summary) beside the existing
  `CODOL_PacingSnapshot` call at `src/sv_snapshot.c:236` for ~200 snapshots and
  diff those timestamps against the client-side phase-drop timestamps.
  Prediction: 100% of phase drops fall on non-zero-advance snapshots.
* **Null test that would kill it outright (diagnostic only)** For one capture,
  publish `frame->ps.commandTime = svsHeader.time` on the wire after
  `src/sv_snapshot.c:1194` — wire only, do not touch the simulated `ps`. If the
  sawtooth's amplitude collapses, the lumpy command clock is confirmed as the
  amplitude source. It breaks `rov`/prediction agreement, so it is a one-shot
  experiment, not a fix.
* **Where a real fix would live (not implemented — research task)** Meter
  usercmd execution against the frame clock: queue the batch and drain it at
  the frame boundary up to `previously published commandTime + frame interval`,
  reusing the <=66 ms sub-step chopping the C1 mover already has
  (`src/codol/player/codol_pmove_c1.c:841-852`). Cost: up to one frame of added
  input latency — `src/codol/snapshot/codol_snapshot_pacing.h:26` already warns
  that no drain rule can smooth this "without deferring input". That trade
  belongs to the user, not to a worker.
  *(Those files are owned by another worker; this entry is analysis only.)*

### R1b — corroboration: `ps[0x4A0]` is snapshot-interpolated, i.e. C1 treats it as a continuous per-playerstate quantity
`[DIS]` `0x0045E987..0x0045E9A6` (in the function beginning `0x0045E8B0`, the
snapshot playerstate lerp, immediately after `0x0045E830`) does
`out[0x4A0] = from[0x4A0] + frac * (to[0x4A0] - from[0x4A0])` as an integer
lerp between `snap` and `nextSnap`. A field that is interpolated between
snapshots is a field the server is expected to produce continuously. Together
with the `bits == -70` force-send-while-ADS predicate, this is independent
confirmation that `ps[0x4A0]` is the server-owned sway phase.

### R1c — C1 entering/leaving its killcam state repeatedly (the killcam-enter block zeroes the phase)
**Rank: DEMOTED to 6 after the xref sweep — see the kill at the end of this
entry. Kept because the reasoning is reusable and the `ps->deltaTime` defect
behind it (R16) is real.**

* **Mechanism** `[DIS]` Decoded at `0x0046BE2B..0x0046BECD`:

  ```
  0046be2b  cmp  [esi+0xc8b60], edi     ; edi == 0 ; cg.inKillcam
  0046be31  jne  0x46bf0c               ; already in killcam -> LEAVE check
  0046be37  cmp  [esi+0xa50], edi       ; ps->deltaTime == 0 ?
  0046be3d  je   0x46bf00               ; no transition
  0046be43  call 0x46bd20               ; ENTER killcam
  0046be48  mov  [esi+0xc8b60], 1
  ...
  0046bebb  mov  edx, [esi+0x35e4]      ; nextSnap
  0046bec1  mov  eax, [edx+0x4a0]       ; nextSnap->ps[0x4A0]
  0046becd  mov  [esi+0xbf980], eax     ; <-- THE SWAY PHASE RESET
  0046bee7  lea  edi,[esi+0xae348]; mov ecx,0x800; rep stosd   ; 8 KB cleared
  ```

  The enter block is edge-triggered on `inKillcam == 0 && ps->deltaTime != 0`
  and the leave path at `0x0046BF0C` clears `inKillcam` when `deltaTime`
  returns to 0. **If `ps->deltaTime` oscillates on the wire, C1 enters and
  leaves killcam repeatedly and re-runs this reset every time.**
* **Why it fits the measurement better than anything else** `[MEAS]` The enter
  block writes `cg+0xC8B60..0xC8BE0`, `cg+0xAE348..0xB0348` and the sway phase
  — but it does **not** touch `cg[0xBF990]`/`cg[0xBF994]` (kick amplitudes) or
  `cg[0x3594]` (stance ramp). That is exactly the measured pattern: the phase
  is reset constantly while the kick amplitudes survive 40 consecutive frames
  and the stance ramp never moves. CG_Respawn, which *does* clear the kick,
  is excluded by the same measurement. **This is the only known code path that
  resets the phase without also clearing the kick.**
* **Server-side weakness that would drive it** `[SRC]` `ps->deltaTime` is
  published every snapshot (`src/codol/snapshot/codol_engine_state.c:374`) but
  written in exactly one place in the whole tree,
  `src/sv_snapshot.c:2785` (`ps->deltaTime += offsettime`), inside the archived
  client path. **Nothing ever assigns it, and nothing ever clears it back to
  0.** So its value for a live client is whatever the playerstate memory
  happens to hold, and any path that runs the archived accumulation on a
  structure that is later used live will leave it permanently non-zero. Both
  failure modes are bad: a permanently non-zero `deltaTime` pins C1 in killcam
  state, and a toggling one re-runs the enter block.
* **Predicted signature vs measured** A toggling `deltaTime` gives a
  phase reset at exactly the rate at which it toggles. If it toggles per
  snapshot, the reset is per snapshot — which the flat-residual measurement
  rules out (see R2). If it toggles per frame (e.g. because the published
  value depends on which server frame built the snapshot), the reset is per
  frame, which is exactly what is measured.
* **Cheapest decisive test — this is the single highest-value capture to run
  next.** Add three fields to `tools/codol_sway_probe.py` and take one 30 s
  stationary scoped capture: `cg[0x0A50]` (`ps->deltaTime`), `cg[0xC8B60]`
  (C1's `inKillcam` flag) and `nextSnap->ps[0x4A0]` (read through
  `*(cg+0x35E4) + 0x4A0`). If `cg[0xC8B60]` oscillates, R1c is the mechanism
  and R2 is closed without any further disassembly. If `cg[0xC8B60]` is a
  steady 0 and `cg[0xBF980]` still resets every frame, R1c is dead and R2's
  bulk writer is real.
* **KILL (direct, decisive)** `[SRC]` `ps->deltaTime` is **zeroed
  unconditionally on every game frame for every in-use client**:
  `src/asmsource/_g_active_mp.asm:400`, `mov dword [eax+0x89c], 0` — the fourth
  instruction of `ClientEndFrame`, at the native offset of `deltaTime`
  (`src/player.h:236`), driven from `src/asmsource/_g_main_mp.asm:1128-1141`.
  The only `+=` (`src/sv_snapshot.c:2785`) sits inside `SV_GetArchivedClientInfo`
  behind `if (cachedSnapshot)` and `*pArchiveTime > 0`, reachable only from
  `SpectatorClientEndFrame` (`_g_active_mp.asm:2817,2872`, requires
  `SESS_STATE_SPECTATOR`) and `Cmd_FollowCycle_f` (`src/g_cmds.c:799`, writing a
  throwaway local). `SV_BuildClientSnapshot` takes the live `ps` directly
  (`src/sv_snapshot.c:1192-1194`).
  **So `cg[0xA50]` is 0 for the whole match, C1's killcam latch `cg[0xC8B60]`
  never leaves 0, and `0x0046BECD` never fires.** This also closes the
  four-times-attempted measurement in the brief: `deltaTime` is not "stuck at
  0 because nothing writes it" — it is *actively* zeroed every frame.
  Consequence: **R1's seed does not arrive via `0x0046BECD`**, and R2's missing
  writer is now the sole remaining route.
* **KILL (indirect, corroborating)** `[DIS]+[MEAS]` The xref sweep decoded the
  sole writer of `cg[0xB035C]` as `0x004771E0`, called once per frame from
  `CG_DrawActiveFrame 0x004788E5`, whose first clause is
  `if ((nextSnap->ps.otherFlags & 0x800) && cg[0xC8B60] == 0) cg[0xB035C] = 0`.
  `cg[0xB035C]` is measured **0 on all 3879 scoped frames**, which can only
  happen if, at that point in every frame, **`otherFlags & 0x800` is set and
  `cg[0xC8B60]` (inKillcam) is 0**. So the killcam latch is not oscillating at
  a per-frame rate. Verify it directly with the capture anyway — it is one
  extra `u32` read — but do not build on R1c.

### R2 — an unfound BULK writer that restores `cg[0xBF980..0xBF998]` every frame
**Rank: 2. This is the one genuine structural unknown left, and it gates R1.**

* **The reset is definitely per-FRAME, not per-snapshot** `[MEAS]` Both
  per-snapshot models are refuted arithmetically:
  - *reset per snapshot + full replay each frame* would give
    `phase = 3*(span_0 + span_1 + ...)` accumulating within an epoch. The
    measured residual `phase - 3*span` is **flat** at -3..-5 across frames 0-7
    of an epoch.
  - *reset per snapshot + incremental replay* would make the **first** frame of
    an epoch read `phase ~ 3*frametime ~ 36`. Measured first-frame-of-epoch
    values are the full `3*span` (e.g. `span 48 -> phase 142`).
  So `cg[0xBF980]` is set to 0 and rebuilt over the whole replay span on every
  rendered frame.

* **Mechanism** `[DIS]` A literal-displacement sweep of the entire `.text`
  section finds only these references in `0xBF960..0xBF99F`:
  - `cg[0xBF980]` (phase): written at `0x0045D3AB` (`= ebx`, inside the
    stance-ramp-to-1.0 / kick-clear block, i.e. CG_Respawn) and at
    `0x0046BECD` (`= nextSnap->ps[0x4A0]`); `lea`'d at `0x0045E872`,
    `0x004711BD`, `0x0047D33B`.
  - `cg[0xBF984]` (the gate byte): **exactly one reference in the whole
    binary**, the read at `0x0045E849`. **Nothing writes it by literal
    displacement**, yet it measurably changes: `[MEAS]` 1 on all 3879 scoped
    frames, 0 on 270 of the 290 non-scoped frames.
  Therefore there **must** be a non-literal or bulk writer covering
  `cg+0xBF980..0xBF984`, and whatever it is almost certainly restores the phase
  too — which is the missing per-frame writer the measurement demands.
* **Why the two known writers cannot be it** `[MEAS]` CG_Respawn cannot be
  running per frame: `kickPitch`/`kickRoll`/`kickStart` hold non-zero for 40
  and 14 consecutive frames in the capture, and CG_Respawn zeroes them.
  `0x0046BECD` is inside the **killcam-enter** block — this server's own source
  comment at `src/codol/snapshot/codol_engine_state.c:374` records C1
  `0x46be37`/`0x46bf0c` as killcam enter/leave on the `ps->deltaTime` (+0xa50)
  edge, and the surrounding block does a `rep stosd` of 0x2000 bytes at
  `cg+0xAE348` plus four heavyweight calls. It is not a per-frame path.
* **Predicted signature** Identical to R1 (it is the *delivery mechanism* for
  R1's value), unless its source is something other than the snapshot ps.
* **Confirming evidence / cheapest test** A `rep movs` / `rep stos` sweep of
  `.text` for a destination `cg + K` with a size spanning `0xBF980` was run
  for this pass (`obj/scan_bulk.py`, 16-instruction lookback for the count and
  a cg-relative `lea`) and returned **zero candidates**. So if a bulk writer
  exists it establishes its base far from the copy, or it is a `memcpy` call
  rather than an inline `rep movs`. **Run R1c's capture first** — it is far
  cheaper and, if `cg[0xC8B60]` oscillates, it closes this item outright.
* **Why it matters even if R1 is right** If the bulk restore's source is a
  *saved* copy rather than `nextSnap->ps`, the server may also need to keep
  that saved copy correct — i.e. the field may need to be right at a different
  point in the frame than we assume.

### R2b — NEW, and it reframes the whole search: **C1 is VM-protected, so no static sweep of this binary is exhaustive**
**Rank: 2. This is a methodological finding, and it is the reason R2 has stayed
open through several passes.**

* **Mechanism** `[DIS]` A full-image scan (every PE section, including
  `.rdata`, `.data` and the **24 MB `.tvm0`** section) for the 4-byte literal
  `0x000BF984` finds **exactly one occurrence in the entire file**: the *read*
  at `0x0045E849`. Nothing in the static image writes the sway gate byte, and
  the only thing that ever touches it would be the one-shot
  `memset(cg, 0, 0x174890)` at `0x0044E153`. `[MEAS]` Yet the byte is **1 on
  all 3879 scoped frames** and 0 on the non-scoped ones — i.e. it tracks ADS.
  The probe's `cg` derivation is byte-for-byte the same expression C1 uses at
  `0x0045E833..0x0045E843`, so the read is not at the wrong address.
* **Independent confirmation that the gate really is 1** `[MEAS]+[INF]` If the
  gate were 0, `0x0045E830` would never run and the *only* advance would be
  `BG_AddIdleSway`'s per-frame `1.5 * frametime`, which **accumulates with wall
  time**. The measured phase does not accumulate — it tracks the replay span
  and resets. So the replay path is demonstrably live, so the gate is
  demonstrably 1, so a writer exists that the static image does not contain.
* **Conclusion** `[INF, high confidence]` The writer is in `.tvm0` —
  VMProtect-style virtualized code carries no literal displacements, so a
  literal or even taint-based sweep of `.text` **cannot** find it. The same
  applies to the missing per-frame writer of `cg[0xBF980]` (R2): the most
  likely explanation for "the measurement demands a per-frame reset and no
  static writer exists" is that the resetter is virtualized.
* **Consequences for how this bug should be worked**
  1. Stop treating "no static writer found" as evidence of absence. Three
     separate leads in this investigation (`0xBF984`'s writer, `0xBF980`'s
     per-frame reset, and by extension anything else that comes back empty)
     are all consistent with virtualized code.
  2. Prefer **behavioural** probes over static sweeps from here: sample the
     value at two different points in the frame, or correlate it against
     candidate inputs, rather than trying to find the instruction.
  3. This project reads the client with `PROCESS_VM_READ` only, so a hardware
     write-watchpoint is out of scope; behavioural probing is the tool.
* **Cheapest decisive test** In the same capture, sample `cg[0xBF980]` **twice
  per frame** at two different hook points (or sample at a much higher rate
  than the frame rate, ~1 kHz, and look at the shape within a frame). If the
  value goes `0 -> 3*span` within a frame, the per-frame rebuild is confirmed
  directly and the search narrows to "what runs at the start of
  CG_PredictPlayerState".

### R2c — NEW: the drawn offset contains two contributors nobody has been subtracting
**Rank: 7. Small in this capture, but it invalidates naive attribution.**

* **Mechanism** `[DIS]` Between the seed at `0x00476985` and the end of
  `CG_CalcViewValues 0x004766E0`, `cg[0xB4418]` is added to by **more than
  `0x00471150`**:
  - `0x00476A8B -> 0x00471950` (`+=` at `0x00471A21/27`), gated on
    `ps[0xEC] & 0xC00` (vehicle/turret) and `cg[0xB035C] == 0`;
  - `0x00476AC6 -> 0x004710C0`: `pitch += asin(f * cg[0xB0380]) * 57.2958` —
    **view lean**, gated on `pm_type not in {5,6}`, `cg[0xB035C] == 0`,
    `!(ps[0xEC] & 0x100000)`;
  - `0x00476ACE -> 0x0042C440`: **earthquake/rumble**, an independent sine,
    `pitch += sin(t*25.1327 + ph) * amp * 18 * s` with a yaw term at
    `47.1239 rad/s`, driven by the per-client array at
    `0x016A0918 + clientNum*0x94` (the array CG_Respawn memsets at
    `0x0045D3D0`).
  So `cg[0xB4418] - ps.viewangles` is sway **+ lean + rumble**, not sway alone.
* **Why it is nonetheless not the cause here** `[MEAS]` The pure sway-phase
  model reproduces the drawn frame-to-frame jump at med `0.01731` vs measured
  `0.01743` deg, so lean and rumble contribute almost nothing in this capture
  (stationary, not leaning, nothing exploding). **But 25.13 rad/s is 4.0 Hz and
  47.12 rad/s is 7.5 Hz** — if a future capture shows jitter at those rates
  rather than at the snapshot rate, this is where to look.
* **Cheapest test** Sample `0x016A0918 + clientNum*0x94` (0x90 bytes) in the
  capture; if the amplitude word is 0 throughout, rumble is out.

### R3 — the server has no sway-phase producer at all, so even the right wire field would carry garbage
**Rank: 3 (a prerequisite, not an independent cause).**

* **Mechanism** `[SRC]` `grep -rn "swayPhase|AdvanceSway|0x4a0"` over
  `src/codol/snapshot` and `src/codol/player` returns **nothing**. There is no
  server-side integrator for this quantity anywhere. So R1 is not a "publish an
  existing field" job; the server must first implement `BG_AdvanceSwayPhase` in
  its pmove with C1's exact semantics. `BG_GetSwayScales 0x00422FE0` `[DIS]`
  has **three** branches, not one — the port must carry all of them:

  | condition | maxAngle out | speed out |
  |---|---|---|
  | `def[0xBC8] != 0` (byte) | `BG_GetAdsSteadySwayAngle 0x00422E20` | `def[0x6F8] + (def[0x6F4] - def[0x6F8]) * fWeaponPosFrac` |
  | else `def[0x6F0] != 0.0f` | `def[0x6F0]` | `def[0x6F8]` |
  | else | `80.0` | `1.0` |

  and `phase += ftol(holdBreathScale * dt * 1000 * speed)`, gated on
  `def[0x694] != 0` and `fWeaponPosFrac != 0.0f` exactly — plus the ungated
  second add described in R4. Only then publish it.
* **Codec constraint on the value — non-obvious and load-bearing** `[SRC]`
  Encoding `-70` is the **TIME codec** (`src/codol/snapshot/codol_delta.c:136-141`):
  it transmits `serverTime - value` in `1 + 8` bits when the difference is
  `0..255`, and falls through to a full 32-bit long otherwise. **C1 therefore
  expects `ps[0x4A0]` to be a serverTime-referenced stamp that normally stays
  within 255 of `serverTime`**, not a free-running counter from 0. A phase
  seeded at 0 and advanced at 3/ms leaves the cheap arm within ~85 ms and costs
  4 bytes every frame thereafter. Seed the accumulator from `level.time` (or
  otherwise keep it anchored near `serverTime`) so it stays on the 8-bit arm —
  and treat the fact that the codec is time-shaped as a hint about the intended
  semantics of the field, which nobody has pinned down yet.
* **Cheapest test** None needed; it is a source fact.

### R4 — the server's accumulator rate will not match the client's replay rate
**Rank: 4. A predicted *second-order* failure of the R1 fix, worth writing down
before the fix is attempted rather than after.**

* **Mechanism** `[DIS]` Client per replayed usercmd: `hbs*dt*1000*speed`
  (`0x00424BFE`) **plus** `dt*1000*speed` (`0x0045E8A5`) = `(1+hbs)*speed` per
  ms. Client per rendered frame: `hbs*frametime*speed` (`0x00424C6B`, via the
  aggregator at `0x00471150`). `0x0045E830` is **skipped for the last command**
  in the replay (`0x0045F780: cmp ebx,[ebp-0x40]; jge`).
  **The second add is not merely unscaled — it is also UNGATED** `[DIS]`: the
  `def[0x694] != 0` and `fWeaponPosFrac != 0.0f` tests live inside
  `BG_AdvanceSwayPhase 0x00424B90` (`0x00424BB6`, `0x00424BC7`), whereas
  `0x0045E891..0x0045E8A5` runs whenever `cg[0xBF984] != 0` and a weapon def
  exists. So the phase keeps advancing at `1 x speed` even at hip fire and even
  for weapons with no idle sway. Any server-side port must reproduce that
  asymmetry. A server that advances
  at a plain `speed` per ms will leave a residual sawtooth of amplitude
  `speed * snapshotInterval` — i.e. the jitter will halve, not disappear, and
  the pass will look like a partial failure.
* **Predicted signature** After the R1 fix: seed non-zero and tracking, but
  `phase - (seed + 3*span)` still sawtoothing at the snapshot rate with about
  half the present amplitude.
* **Cheapest test** Re-run the sway probe after the fix and fit the seed
  increment per snapshot against `3 x (snapCmd_n - snapCmd_{n-1})`.

### R5 — `otherFlags` (ps 0x010) bits `0x1800` and the spurious `CG_Respawn` route
**Rank: 5. Not the cause of the present sawtooth, but not clean either.**

* **Mechanism** `CG_SetNextSnap` tests mask `0x1800` (`POF_PLAYER|POF_FOLLOW`)
  at `0x0046CEBD`; failing it routes to `0x0046D365 -> CG_Respawn`, whose body
  (around `0x0045D2CE..0x0045D3B1` `[DIS]`) does
  `cg[0xBF990] = cg[0xBF994] = 0` (kick amplitudes), `cg[0xBF96C] = 0` (kick
  start), `cg[0xBF998] = 0`, `cg[0x3594] = 1.0f` (stance ramp) and
  `cg[0xBF980] = 0` (the sway phase). `otherFlags` is netfield 58, changeHint 0
  — sent only on change.
* **Why it is NOT the present cause** `[MEAS]` `kickPitch`/`kickRoll` survive
  40 and 14 consecutive frames non-zero, and `kickStart` holds a fixed
  `168350` across 40 frames. CG_Respawn is therefore not firing per frame or
  per snapshot. **Demoted from "direct hit on the signature" to "ruled out as
  the per-frame resetter".**
* **Second, independent kill** `[DIS]+[MEAS]` The route to `CG_Respawn` at
  `0x0046D365` is taken only when `newSnap->ps.otherFlags & 0x1800 == 0`
  (`0x0046CED0  je 0x46D28A`). Separately, the sole writer of `cg[0xB035C]`
  (`0x004771E0`, once per frame from `CG_DrawActiveFrame`) sets it to 0 only
  when `nextSnap->ps.otherFlags & 0x800` is **set**. `cg[0xB035C]` is measured
  **0 on all 3879 scoped frames**, so bit `0x800` is set, so the `0x1800` test
  passes, so the bits-clear branch that leads to `CG_Respawn` is **not taken**.
  `otherFlags` is being published correctly for these bits. **Close this lead.**
* **Resolved sub-question: the stance ramp being pinned at 1.0 is NOT a bug**
  `[DIS]` `0x00471150` copies `cg[0x3594]` into `ctx+0x1C`; `BG_AddIdleSway`
  ramps that **stack copy** toward `def[0x700]`(prone)/`def[0x6FC]`(crouch)/1.0
  at `dt*0.5` per second (`0x00424CCE`, `0x00424CF3`) and `0x00471150` never
  writes it back. The only write-back is `0x0047D51A` in `0x0047D490` (the
  viewmodel pipeline). So `cg[0x3594]` is expected to look static from the
  sway block's point of view. `[MEAS]` 1 distinct value across 4169 frames is
  consistent with this, not with a spurious CG_Respawn.
* **Load-bearing warning** `[DIS]` `ps.otherFlags` bit `0x800` gates
  `cg[0xB035C]` at `0x004771E0`. If the server ever stops publishing it,
  `cg[0xB035C]` goes to 1 and **all** weapon sway, kick and lean are skipped
  outright (`0x00476AB9 jne` past `0x00471150`). Worth an assertion.

### R6 — ftol truncation of the phase adds
**Rank: 6. Real, quantified, far too small to be the symptom.**

* **Mechanism** `[DIS]` Every add is `ftol(...)`, truncating toward zero;
  ~10 truncations per frame. `[MEAS]` This is exactly the measured `2.96`
  instead of `3.00` and the flat `-3..-5` residual. `[INF]` Converted to drawn
  angle that is `< 0.002 deg` — two orders below the measured jitter.
* **Verdict: not a cause. Noted so nobody re-chases the `2.96 != 3.00` gap.**

### R7 — `cg[0xBF984]` (the sway gate byte) flickering off and suppressing the replay advance
**Rank: 7. Attractive on paper, killed by measurement.**

* **Mechanism** `[DIS]` `0x0045E849` returns from `0x0045E830` without touching
  the phase when `cg[0xBF984] == 0`, so a flicker would drop a whole frame's
  replay advance — exactly an "advance then yank back".
* **Killed** `[MEAS]` `swayEnable == 1` on **3879/3879 scoped frames**. The 270
  zeros are all non-scoped frames. **Do not chase this.** (The gate byte is
  still interesting for R2, as the only thing in the binary that reads it
  without anything writing it.)

### R8 — `cg[0xB035C]`, the gate that can skip the whole aggregator
**Rank: 8. Killed by measurement.**

* **Mechanism** `[DIS]` `0x004710FB`, `0x00476AAB`, `0x00480BB6` and ~14 other
  sites test `cg[0xB035C] != 0` and skip the sway/viewmodel block; writers are
  clustered at `0x00477218..0x0047731C`.
* **Killed** `[MEAS]` `gate == 0` on 4164 of 4169 frames and on **all 3879
  scoped frames**. Not a factor.

### R9 — "is the symptom even the idle sway?"
**Rank: answered, not a candidate.**

* `[DIS]+[MEAS]` While stationary `|vel.xy| = 0`, and both `0x00424D90`
  (scoped bob) and `0x00424F30` (weapon bob) scale their amplitude by
  `ctx+0x14 = |vel.xy|`, so both are zero. `0x00424A20` (weapon-kick decay) is
  zero unless recently fired (`kickPitch/kickRoll == 0` on 4115/4169 frames).
  `BG_AddIdleSway 0x00424C10` is therefore the only live contributor, its
  amplitude is `stanceRamp * maxAngle(40) * fWeaponPosFrac * holdBreathScale`,
  and the model reproduces the drawn offset (section 0.3). **It is the idle
  sway, and hold-breath killing it is consistent.**

### R10 — a second sway aggregator at `0x00425020` (caller `0x0050CC8B`)
**Rank: 10. Investigated, not our path.**

* `[DIS]` `BG_AdvanceSwayPhase 0x00424B90` has **exactly two callers**:
  `0x00424C6B` (inside `BG_AddIdleSway`) and `0x0045E87B` (inside
  `0x0045E830`). `BG_AddIdleSway` has two callers: `0x0047121A` (the render
  aggregator `0x00471150`) and `0x00425038` (the aggregator `0x00425020`).
  `0x00425020`'s only caller is `0x0050CC8B` (in `0x0050C8D0`, itself called
  only from `0x0050FA00` — the 0x50xxxx script/UI/anim block, **not** reachable
  from `CG_DrawActiveFrame`). Whatever its base register is, it passes
  `&base[0x384C]` as the phase pointer and writes a caller-supplied `out`
  vector, never `cg[0xB4418]`. **It cannot advance `cg[0xBF980]` and cannot
  contribute to the drawn offset.** (`0x00425020` runs the same four
  contributors in the same order as `0x00471150`, which is why it looks like a
  duplicate.)

### R11 — a third site taking `&cg[0xBF980]`: `0x0047D330`, called from `0x00480C3E`
**Rank: 11. New, benign, but it doubles the blast radius of the bug.**

* `[DIS]` `0x0047D330` builds a 0xC0-byte context (`ctx+0x04 = cg[0xBF998]`,
  `ctx+0x08 = cg[0xB034C]*0.001`, `ctx+0x18/0x1C = cg[0xBF990]/[0xBF994]`,
  `ctx+0x20 = &cg[0xBF980]`, plus `cg[0xBFA4C]/[0xBFA50]/[0xBFA48]`) for the
  **viewmodel/weapon-render** path at `0x00480BB6..0x00480C67`, gated by
  `cg[0xB035C] != 0` and `ps->pm_flags & 0x100C00`. Since nothing else calls
  `BG_AdvanceSwayPhase`, this path only *reads* the phase.
* **Consequence** `[INF]` The same sawtooth also shakes the **weapon model**,
  not just the view angles. Useful as a confirmation channel: if the user
  reports the gun model jittering in lockstep with the reticle, that is this
  path and it corroborates R1 rather than indicating a second bug.

### R12 — client time base (`CL_AdjustTimeDelta`, `cl_timeNudge`, snapshot interpolation, serverTime cadence)
**Rank: 12. Demoted, with a caveat.**

* **Why demoted** `[MEAS]` The phase tracks `predicted ps.commandTime -
  snapshot ps.commandTime`, **not** `cg.time`. The 127875 frame proves it:
  `cg.time - snapCmd = 71` but `predCmd == snapCmd` and the phase is 0. So the
  quantity driving the sway is a *usercmd-time span*, and `cg.time` enters only
  indirectly (it decides how far prediction runs). Perturbing `cg.time` changes
  the span but does not create the sawtooth; the sawtooth comes from the seed
  being 0.
* **Residual caveat** Snapshot `serverTime` irregularity, duplicated or
  non-monotonic snapshot times, and the client batching 3.00 usercmds per
  ~35 ms packet while the server runs at `sv_fps 60` all change *how* the span
  steps, so they modulate the sawtooth's amplitude and rate. They are amplitude
  modulators, not the generator. After R1 is fixed they should become invisible;
  if jitter persists with a correct seed, come back here first.
* **The machinery, now fully decoded — kept so nobody re-derives it** `[DIS]`
  - `cg.time` **is** `cl.serverTime` verbatim: `CG_DrawActiveFrame 0x00478680`
    is called with `ECX = cl.serverTime` (`0x0049F912`), sets
    `cg.time = serverTime` (`0x0047871F`) and
    `cg.frametime = serverTime - cg.oldTime` (`0x00478737`), clamping a
    negative frametime to 0 (`0x0047876F`). `cl = *(u32*)0x016FC318 ^ 0x9056BBC8`;
    `cl.serverTime = cl+0x33B4`, `cl.serverTimeDelta = cl+0x33C0`,
    `cl.oldSnapServerTime = cl+0x33C4`, `cls.realtime = *(u32*)0x06C450A8`.
  - `CL_AdjustTimeDelta` is **`0x00488380`**, `CL_SetCGameTime` is
    **`0x00488600`**, `CG_SetFrameInterpolation` is **`0x00440250`**,
    `CG_ProcessSnapshots` is **`0x0046DA20`**.
  - **Bands: 500 ms hard reset / 100 ms halve / +/-1 ms slow drift, with -2 on
    an extrapolated snapshot** — identical thresholds to Q3. Slow drift is
    gated on `com_timescale == 1.0f` **exactly** (cached at `0x00CD1B4C`).
  - **There is NO `cl_timeNudge` dvar in C1.** The nudge is hardcoded `-16 ms`
    *plus one whole snapshot interval*, because the drift target anchors to
    `cl.oldSnapServerTime`, not `cl.snap.serverTime` (`0x00488406`). Steady
    state is `cg.time ~ newestSnapServerTime - snapInterval - 16`: **-66 ms at
    `sv_fps 20`, -33 ms at `sv_fps 60`**. That alone accounts for the measured
    81 ms median snapshot age — no bug required.
  - **There is no `cl_extrapolate` dvar either.** `cg.frameInterpolation`
    (`cg+0xB0348`) is clamped **below only** (`0x004402B0`); `f > 1` is C1's
    unconditional extrapolation mode, entered whenever
    `cg.time >= cg.nextSnap->serverTime`.
  - **Snapshots arriving faster than the client consumes them are SKIPPED, not
    queued or dropped**: `CG_ProcessSnapshots` transitions through every one
    (events still fire) until `snap->serverTime <= cg.time < nextSnap->serverTime`.
  - **Non-monotonic snapshot `serverTime` is a hard `Com_Error`**, twice over
    (`0x004886FF` and `0x0046DB74`), and a backwards `messageNum` likewise
    (`0x0046DA85`). `[SRC]` Our `svs.time` only ever increments
    (`src/sv_main.c:4583-4590`, correct fractional 16/17 accumulator). **So the
    absence of client crashes is itself proof that our snapshot times are
    monotonic and ordered** — that question is closed.
  - **Duplicated `serverTime` is not fatal** (the compares are `<`): it forces
    `frameInterpolation = 0` for that frame, i.e. a one-frame pop. Our only
    duplicate source is `SV_SendClientSnapshot()` on the two terminal paths
    `SV_DropClient` (`src/sv_main.c:2947`) and `SV_SpawnServer`
    (`src/sv_main.c:5281`).

### R13 — dvars in the sway chain
**Rank: 13. Cannot explain the factor of 2 (already resolved), low prior.**

* `[DIS]` A dvar sweep of `0x00422E20`, `0x00422FE0`, `0x00424A20`,
  `0x00424B90`, `0x00424C10`, `0x00424D90`, `0x00424F30`, `0x00425020`,
  `0x0045E830`, `0x00471150`, `0x004766E0..0x00476C00` and
  `0x00477150..0x004772D0`, resolving every dvar dereference to its
  registration site, finds that **every function on the phase-rate path reads
  ZERO dvars**: `BG_GetAdsSteadySwayAngle`, `BG_GetSwayParams`, the kick decay,
  `BG_AdvanceSwayPhase`, `BG_AddIdleSway`, the weapon bob, both aggregators and
  `0x0045E830`. The rate is entirely `WeaponDef+0x6F4/+0x6F8` x
  `ps->holdBreathScale` x `ps->fWeaponPosFrac` x a hardcoded `1000.0`
  (`0xC842B0`). **No dvar can explain the x2, and none exists that could.**
  There is **no sway dvar in C1 at all** — sway is 100% weapon-def driven
  (`+0x6EC/+0x6F0/+0x6F4/+0x6F8/+0x6FC/+0x700/+0x714/+0x718`).
* The only other dvars in the wider block are gates and debug: `"719"` (bool,
  0) and `"1871" == 2 && "727" != 0` force `cg[0xB035C] = 1` and skip the
  aggregator entirely; `"695"` (100.0) and `"703"` (0) gate only the
  prediction-error-decay debug window and the
  `"Adjusting view.org with factor %f"` print. None modulates rate or
  amplitude; the most they can do is turn the chain **off**.
* Dvars `142` (0.16), `147` (1.5), `149` (0.25) only feed `0x00424D90`, whose
  amplitude is `|vel.xy|`-scaled and therefore zero while stationary.
* The one live question left in this area is the project's "server-only dvar
  delivered through the playerstate" pattern (`ps.speed`/`ps.gravity`).
  **`ps[0x4A0]` is exactly an instance of that pattern** — which is why R1 sits
  at the top.

### R14 — changeHint-2 second pass / trailing-section loss
**Rank: 14. Not applicable to this field.**

* `[SRC]` The project's `changeHint == 2` finding applies to netfields above
  index 100. `{0x04a0, -70, 3}` is netfield **index 4** — the fourth-lowest in
  the table, in the same high-priority group as `commandTime`, origin, velocity
  and `bobCycle`. It is nowhere near the trailing sections.

### R15 — encoding/delta-base fault on `ps[0x4A0]` rather than a missing value
**Rank: 15. Ruled out by construction.**

* `[SRC]` `CODOL_ReachPlayerFields` uses `from = rov && hint == 3 ? 0 :
  base->field[i]`. With `requested->field[i]` never populated it is 0 on both
  sides, so the codec is being asked to send 0 and is sending 0 faithfully.
  There is no codec fault to find here — the value simply does not exist.
  This matters because it means the fix is a *producer* job, not a codec job.

---

### R16 — `ps->deltaTime` — RESOLVED, not a defect
`[SRC]` It is zeroed unconditionally every game frame in `ClientEndFrame`
(`src/asmsource/_g_active_mp.asm:400`) and published as 0
(`src/codol/snapshot/codol_engine_state.c:374`). `[DIS]` That is the correct
value outside killcam: C1 subtracts it from `cg.time` to form the sway/viewkick
time base (`0x004711A1`, `0x0047D3A2`, `0x0043EEF3`, `0x00483C01`) and uses the
0 -> non-zero edge to latch its killcam. **No action.** Two notes for later:
wire `0x0A54` `killCamEntity` is published unconditionally
(`codol_engine_state.c:375`) and is *not* zeroed by `ClientEndFrame`, so it is
live garbage the moment `0x0A50` ever becomes non-zero; and `CG_SetNextSnap`
deliberately preserves `cg.snap->ps.deltaTime` across the playerstate memcpy
(save `0x0046CEC4`, restore `0x0046D109/0x0046D16B/0x0046D230/0x0046D344`), so
a non-zero value would be partly ignored anyway.

---

## Second wave — candidates surfaced by the time-base and netfield sweeps

### R17 — NEW: every spawn publishes a BACKWARDS `ps.commandTime`
**Rank: 8. A real, one-off phase kick at every respawn and round start.**

* **Mechanism** `[SRC]` `src/g_client_mp.cpp:237-238` sets
  `client->ps.commandTime = level.time - 100`, while the previously published
  value is typically `level.time - 50`. That is a **50-100 ms backwards step**
  on the wire. Since `phase = seed + 3 x (predCmd - snapCmd)`, a snapshot whose
  `commandTime` moves backwards makes the span *larger* -> a **one-off kick of
  about +300 phase units**, about 3.4x the median sawtooth drop.
* **Why nobody has seen it in the telemetry** `[SRC]`
  `CODOL_PacingSnapshot` deliberately filters these out
  (`advance >= 0 && advance < 1000`,
  `src/codol/snapshot/codol_snapshot_pacing.c:110`). "Pacing looks clean" is
  therefore **not** evidence that no backwards step occurred.
* `[DIS]` C1 does not error on it — its two `Com_Error` guards
  (`0x004886FF`, `0x0046DB74`) cover snapshot `serverTime`, not `ps.commandTime`.
  It just eats the kick.
* **Cheapest test** Log `ps.commandTime` before and after
  `src/g_client_mp.cpp:237` for one spawn.

### R18 — NEW: dvar `"1871"` and `cl_paused`, and what the "prediction stalls" really are
**Rank: 9. One read settles it, and it may reclassify measurements already taken.**

* **Mechanism** `[DIS]` C1's frozen/step dvar is the stripped name `"1871"`
  (global `0x025745F8`, default 0, range 0..2, flags 0x2008, registered at
  `0x598010..0x5980B1`). When non-zero it:
  - forces `cg.frametime = 0` (`0x00478752`),
  - forces `cg.frameInterpolation = 0` (`0x00440291`),
  - **forces `ps.viewangles` from `cg+0x1740C4` at `0x0045F7AC`/`0x0045F7BB`** —
    which are **the exact two addresses the brief calls "prediction stalls"**,
  - changes the whole `cl.serverTime` formula (`0x004887FB`): mode 1 steps
    `+10 ms` capped at `snap.serverTime + 100`; mode 2 pins
    `cl.serverTime = snap.serverTime - 1`.
  `cl_paused` (global `0x02572034`, one of the few *unstripped* names) gates
  the frozen-delta branch in `CL_AdjustTimeDelta` (`0x004883B7`), but only
  together with `"1871"`.
* **Why this matters** `[SRC]` The server log shows C1 sending
  `userinfo "\cl_paused\0"` and `"\cl_paused\1"` live. If `"1871"` is ever
  non-zero, the frames the analysis has been filtering out as "prediction
  stalls" are actually **frozen-clock frames**, and the 80-119 ms `cg.time -
  ps.commandTime` band attributed to stalls has a different explanation.
* **Cheapest test** One read of `*(int*)(0x025745F8 + 0xC)` (the dvar's current
  integer) at capture start. It should be 0.

### R19 — NEW: merged server frames and an uncapped hitch catch-up trip C1's 500 ms reset band
**Rank: 10. Not an 11-16 Hz source, but it is very likely the "episodic
killcam stalls" this project already has on file.**

* **Mechanism** `[SRC]` `SV_SendClientMessages` is called once per `Com_Frame`,
  **outside** the catch-up `while (sv.timeResidual >= frameUsec)` loop
  (`src/sv_main.c:4583-4619`). An overrunning `Com_Frame` runs two or more
  `G_RunFrame`s and emits **one** snapshot carrying a 33 ms+ `serverTime` step.
  Measured live: `wall/snap` 16.7-27.2 ms, 31-60 snaps/sec against a nominal
  60 — **~10% of snapshots merged away in steady state**. There is also no cap
  on the loop: `Com_ModifyUsec` clamps at `clampTime = 5000000`
  (`src/common.c:818-878`), so after a hitch the loop can emit one snapshot
  whose `serverTime` jumped **+5000 ms**, while `ps->commandTime` is separately
  capped at +1000 ms (`src/codol/player/codol_pmove_c1.c:828`).
  `qconsole.log` carries 8 hitch warnings, worst **10806 msec**.
* **What C1 does with it** `[DIS]` `CL_AdjustTimeDelta 0x00488380` hard-resets
  when `deltaDelta > 500` (`0x00488456`): it installs
  `cl.serverTimeDelta = newDelta - 16` (`0x00488460`) and jumps
  `cl.serverTime = cl.snap.serverTime` (`0x0048846C`). **But the slow-drift
  target is `cl.oldSnapServerTime - cls.realtime - 16` (`0x00488406`) — one
  whole snapshot interval lower.** So every reset leaves the client one
  interval "hot" and it crawls back at 1 ms per snapshot: ~280 ms at
  `sv_fps 60`, ~2.5 s at `sv_fps 20`. During that window `cg.time` repeatedly
  overruns `cg.nextSnap->serverTime`, forcing extra transitions and
  `frameInterpolation > 1`.
* **Cheapest test** Correlate the hitch-warning timestamps already in
  `bin/home/main/qconsole.log` against the jitter episodes; and log the
  iteration count whenever the loop at `src/sv_main.c:4583` runs more than once
  (predicted ~10% of frames).

### R20 — NEW: `cg.time` is force-advanced after `cg.frametime` has been computed
**Rank: 11. Small, but it is a genuine per-frame inconsistency in C1 that
anything integrating `cg.frametime` will feel.**

* **Mechanism** `[DIS]` `CG_DrawActiveFrame 0x00478680` computes
  `cg.frametime = serverTime - cg.oldTime` at `0x00478737`. Later,
  `CG_ProcessSnapshots 0x0046DA20` ends with
  `if (cg.time < cg.snap->serverTime) cg.time = cg.snap->serverTime`
  (`0x0046DC09`). On those frames `cg.time` advances by **more than
  `cg.frametime` claims**. The sway aggregator takes
  `ctx+0x18 = cg.frametime * 0.001`, so the per-frame idle-sway advance
  under-counts exactly the jumped interval on those frames.
* **Why it is not the generator** It perturbs the *per-frame* advance, and the
  measured phase is a function of the *replay span*, with no wall-time
  accumulation at all. It is a second-order term.
* **Cheapest test** Read `cg[0xB0350]` immediately before and after the
  `CG_ProcessSnapshots` call site at `0x004787AA`; a difference marks the frames.

### R22 — NEW (systemic): the replicated-dvar configstring bank carries FRIENDLY IW4 NAMES and is inert
**Rank: 12 for sway (benign here), but a standing defect for everything else.**

* **Mechanism** `[SRC]+[DIS]` The replicated-dvar bank (CS 24..223 names,
  224..423 values) publishes friendly IW4 names such as
  `bg_viewBobAmplitudeBase`, `bg_viewBobLag`. C1's applier
  (`0x00466020 -> 0x00625330`) does **not** map friendly names onto its numeric
  registrations, so every such name becomes an inert EXTERNAL string variable
  and the real numeric dvar keeps its compiled-in default forever. Already
  proven empirically for the renderer pair (`r_specularColorScale = 2` in the
  bank while C1's real dvar `1477` simultaneously held 2.5) —
  `docs/CODOL_SHADOW_FINAL_VISION_TRACE_20260914.md:599,612,646`.
* **Why it is benign for the sway** The three bob dvars the server publishes
  into that dead namespace — `142` (0.16), `147` (1.5), `149` (0.25) —
  coincidentally already equal C1's defaults, **and none of them touches the
  phase**; they only scale `0x00424D90`'s scoped-bob amplitude, which is
  `|vel.xy|`-scaled and therefore zero while stationary. Dvar `142` is not even
  replication-class (flags `0x00`).
* **The working routes, for whoever needs them later** `[SRC]`
  `CODOL_PublishReplicatedDvar` with a **numeric** name (used today only for
  `"1617"`, `src/codol/script/codol_map_shadow.c:31,50`) and the per-client
  `s <numericID> "<value>"` command (used for `"291"/"292"/"794"/"796"/
  "1611"/"1612"`).

### R23 — NEW: `cl->rate` defaults to 5000 because C1 never sends a `rate` userinfo key
**Rank: 13 locally (bypassed on loopback), but it lands exactly on the reported
11-16 Hz band and would bite any non-loopback client.**

* **Mechanism** `[DIS]+[SRC]` The strings `rate`, `snaps`, `cl_maxpackets`,
  `cl_timeNudge`, `com_maxfps`, `sv_fps` and `protocol` **do not exist anywhere
  in C1.exe** — all stripped to numeric IDs (only `cl_paused` and `cg_fov`
  survive as literal names). The decrypted connect capture shows C1's userinfo
  carrying only `xuid`, `challenge`, `qport` and the numeric key `2490`
  (`docs/CODOL_ASSOCIATION.md:216-219`). So `src/sv_client.c:863`
  `Info_ValueForKey(userinfo,"rate")` returns empty and `cl->rate = 5000`.
* **The arithmetic that makes this worth listing** 5000 B/s / ~350 B per
  snapshot ≈ **14 snapshots/s** — squarely inside the reported "11-16 times a
  second".
* **Why it is not the current cause** `[SRC]` `src/sv_snapshot.c:695-698`
  bypasses the rate path entirely for `NA_LOOPBACK || Sys_IsLANAddress`
  (`nextSnapshotTime = svs.time - 1`, send every server frame), and every
  pacing window in the log reports `ratedelayed 0/n`. The user tests on
  loopback.
* **Cheapest test** Log `cl->rate` and `client->rateDelayed` once for the
  connected client. **And it must be fixed before anyone plays remote** —
  otherwise the bug will appear to "come back" off LAN.

### R21 — settled: why hold breath removes the symptom
Not a candidate, but it closes a loose end. `[DIS]` `BG_GetSwayParams 0x00422FE0`
-> `BG_GetAdsSteadySwayAngle 0x00422E20`, and at **`0x00422E26`**:
`eax = ps[0x4D0]; shr eax,5; test al,1` — if bit `0x20` of `ps+0x4D0` is set the
rate base becomes `0.0f` instead of `weaponDef[0x6EC]`. The phase increment goes
to zero and the accumulator **freezes**, so no seed error can be expressed.
`ps+0x4D0` is **not in the netfield table at all** — it is purely
client-predicted, so there is nothing for the server to publish and nothing to
chase there. Hold-breath removing the symptom therefore tells us only that the
symptom lives in this accumulator; it is not evidence about which input is
wrong.

---

## Disagreements between the independent sweeps (do not treat these as settled)

Four passes read the same code and did not agree everywhere. Recording the
conflicts so nobody builds on the wrong one:

1. **What gates `cg[0xB035C]`.** One decode of `0x004771E0` reads the first
   clause as `(nextSnap->ps.otherFlags & 0x800) && cg[0xC8B60] == 0`; another
   reads the same writers (`0x00477218/0x0047722A/0x0047725D/0x0047728A`) as
   driven by dvars `"719"` (bool, default 0) and `"1871" == 2 && "727" != 0`.
   Both are probably present — the function has several passes. It does not
   matter for the diagnosis (`cg[0xB035C]` is measured 0 on every scoped
   frame, so every clause passes), but it does matter if anyone tries to
   *reason* from `cg[0xB035C]` back to `otherFlags`. **Re-derive before using.**
2. **Whether `0x0047D330`'s `ctx+0x20` phase pointer is ever dereferenced.**
   One sweep read the whole `0x004247A0` viewmodel pipeline and found no write
   through it; another reports a third `add [ptr], eax` at `0x004230E3` inside
   `0x00423080`, reached from `0x00424701`. If the second is right there is a
   third advance site and the per-frame arithmetic changes. **Unresolved.**
   Note that `BG_AdvanceSwayPhase 0x00424B90` has only two callers — both
   sweeps agree on that — so any third site advances the phase *inline*, as
   `0x0045E830` does.
3. **Where `ps+0x4D0`'s hold-breath bit comes from.** One sweep calls it purely
   client-predicted (absent from the netfield table). Another reports it
   arriving over the **clientState** wire (`src/codol/snapshot/codol_clients.c:32-47`,
   `cs+0xC0..0xCC`), copied into C1's local ps at `0x0046C988..0x0046C9EC`.
   Both agree it is not a playerstate netfield. If the clientState route is
   real and we do not populate it, `BG_GetAdsSteadySwayAngle` picks the wrong
   branch — an **amplitude** defect, not a phase one, so it cannot be this bug,
   but it is worth resolving on its own.
4. **The numeric value of the sway rate.** This pass and two sweeps derive
   `speed = 1.5` at `fWeaponPosFrac = 1` from `def+0x6F4/+0x6F8` and attribute
   the `3.0` to the double-add. One sweep instead attributed `3.0` to
   `def+0x6EC`, which is the *max angle* (40.0) and cannot be the rate. **The
   double-add derivation is the supported one**, and the hip-fire/hold-breath
   predictions above test it directly.

---

## Open items handed forward

0. **Run the free model test first**: one capture with ~5 s scoped-idle, ~5 s
   scoped-holding-breath, ~5 s hip-fire. Predicted phase rates 3.0 / 1.5 / 5.0
   per ms. This validates or destroys the entire analysis for the cost of one
   capture and needs no new code beyond what `tools/codol_sway_probe.py`
   already reads.
1. **Then run the augmented capture** (below). The single most informative
   addition is sampling `cg[0xBF980]` **twice per frame** (R2b) plus
   `nextSnap->ps[0x4A0]` (R1).
2. **Do not spend more time on static sweeps for the missing writer** (R2b).
   Both the inline `rep movs` sweep and a full-image literal scan over every
   section came back empty; `.tvm0` virtualization is the most likely answer,
   and behavioural probing is cheaper than defeating it.
3. **Confirm the seed source experimentally** (R1) with a deliberately
   distinctive published `ps[0x4A0]` — this is the one test that both proves
   the chain and delivers the fix.
4. **Add an assertion that `ps.otherFlags` bit `0x800` is always published**
   for a live in-match player (R5's load-bearing warning).

## What one 30-second stationary scoped capture should record next

Per rendered frame: `cg.time`, `cg.frametime`, `cg[0xBF980]`, `cg[0xBF984]`,
`cg[0x3594]`, `ps.commandTime`, `snap->ps.commandTime`, plus the **five fields
the current probe does not sample**, which are what this pass is blocked on:

| read | why |
|---|---|
| `cg[0x0A50]` (`ps->deltaTime`) | R1c: drives C1's killcam enter/leave edge |
| `cg[0xC8B60]` (C1 `inKillcam`) | R1c: if this oscillates, the cause is closed |
| `*(cg+0x35E4) + 0x4A0` (`nextSnap->ps[0x4A0]`) | R1: the seed source; should be 0 today |
| `*(cg+0x35E0) + 0x4A0` (`snap->ps[0x4A0]`) | R1b: the lerp endpoints |
| `snap->serverTime`, `nextSnap->serverTime` | R12: snapshot cadence |
| `0x016A0918 + clientNum*0x94` (0x90 bytes) | R2c: rule out the rumble sine |
| `cg[0xB0380]` | R2c: rule out the view-lean term |
| `cg[0xBF980]` sampled **twice per frame**, or at ~1 kHz | R2b: see the `0 -> 3*span` rebuild directly |

Also worth one deliberate crouch/prone while scoped in the same capture, to
confirm R5's stance-ramp conclusion.

## Implementation of R1 (2026-09-16 — written and compile-checked; NOT built, NOT verified live)

* **New** `src/codol/player/codol_sway_phase.c` / `.h` — the server-side
  accumulator. Per-client, keyed on `ps->commandTime` so it is idempotent for
  the ~50% of snapshots that republish an unchanged commandTime (R1d), seeded
  **from `commandTime`** (see below), re-seeded on any backwards commandTime,
  and clamped to a 1000 ms step so a hitch cannot fling it. Reproduces C1's
  asymmetry exactly: the gated add (`holdBreathScale x dt x speed`, requires
  `def[0x694] != 0` and `fWeaponPosFrac != 0.0f` exactly) **plus** the ungated,
  unscaled second add (`dt x speed`). `speed` is `BG_GetSwayParams 0x00422FE0`
  in all three branches. Weapon-def fields are read from the composed
  definition's serialized image with the type-43 attachment overrides replayed,
  as `BG_BuildCustomWeaponDef 0x00421590` does — skipping that replay is the
  known composed-weapon index trap.
* **Changed** `src/codol/snapshot/codol_engine_state.c` — one include and one
  `put(&out, 0x4a0, CODOL_SwayPhase(ps))` beside the existing `commandTime`
  put in `CODOL_OverlayEngineMovement`. The force-send predicate in
  `codol_playerstate.c:50` is untouched; only the value was ever missing.
* **Changed** `makefile` (shared file) — the new TU appended to the eight test
  targets that link `codol_engine_state.c`. The TU also weak-declares its asset
  and weapon-composition dependencies, so it links standalone where those
  subsystems are absent and falls back to `BG_GetSwayParams`' third branch.

### The codec question, settled
Encoding `-70` shares its wire format with `-97` (`serverTime - value`, 1+8
bits within 255, else a long), and `-97` is what `commandTime` and eight other
timestamps use — which argues the field is an epoch, not a fast accumulator.
**The live measurement settles it the other way:** the client's phase is the
wire value **plus** the replayed span, i.e. the value is assigned straight into
the accumulator. An epoch would have to be *differenced*, and a zero epoch
would then have produced `phase ~ 3 x commandTime` (six figures), not the
measured `3 x span`. The two are reconciled by **seeding the accumulator from
`commandTime`**: the value then starts within 255 of `serverTime`, takes the
cheap 9-bit arm at the start of every ADS, and drifts onto the 33-bit arm at
`(2 x speed - 1)` units per ms. `-70` exists as a separate code from `-97`
precisely because it is the only field carrying it — which is what lets C1 hang
the "force-send while `fWeaponPosFrac != 0`" rule on exactly this field.

### Correction: R17 is a FALSE ALARM — do not "fix" it
`src/g_client_mp.cpp:237` does set `ps.commandTime = level.time - 100`, but
`ClientThink_real(ent, &client->sess.cmd)` runs **on the next line** with
`cmd.serverTime = level.time`. The `-100` exists to give that spawn think a
100 ms `msec`; commandTime is back at `level.time` before any snapshot is
built, so the backwards value never reaches the wire. Removing it would zero
the spawn think's msec. No change made. The accumulator is robust to it either
way (a backwards commandTime re-seeds rather than winding backwards).

## Tooling written for this pass

* `obj/dis1.py` — range disassembler over C1 `.text` (capstone, resume over bad bytes).
* `obj/scan_disp.py` — literal displacement/immediate sweep for a set of offsets.
* `obj/scan_range.py` — same, over an offset range (this is what found the
  `cg[0xBF984]` "read with no writer" anomaly).
* `obj/callers.py` — exact call/jmp caller enumeration for a set of targets.
* `obj/sway_epoch.py` — per-snapshot-epoch regression of phase against cg.time.
