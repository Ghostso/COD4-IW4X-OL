# Third-person pain/flinch animation state (2026-09-15)

User report: "a playermodel will be stuck in their flinch/hurt walking animation
after being damaged and it doesn't seem to reset until respawn."

Cause, in one line: the C1 pmove core this server runs
(`CODOL_PmoveC1Try`) replaced the retained `Pmove`, and the replacement never
carried over the damage-timer **discharge**. The charge side still ran, so
`ps->damageTimer` latched at its charged value for the rest of the life.

## 1. Audit — what actually drives the third-person pain animation

There is no client-side "pain" animscript condition in MP and no
`ANIM_ET_PAIN` producer. The MP pain animation is a **movement variant chosen
on the server** and published in the entityState as `legsAnim`/`torsoAnim`
(with `ANIM_TOGGLEBIT`) by `BG_PlayerStateToEntityState`. The client plays the
movement the server names; it does not re-derive it.

Three playerState ints are the entire input:

| field | native offset | C1 ps offset | netfield | role |
|---|---|---|---|---|
| `damageTimer` | `src/player.h:125` (+160) | +0xd8 | `src/msg.c:2422`, 10 bits | time left in the pain window |
| `damageDuration` | `src/player.h:126` (+164) | +0xdc | `src/msg.c:2453`, 16 bits | value the timer was charged to |
| `flinchYawAnim` | `src/player.h:127` (+168) | +0xe0 | `src/msg.c:2455`, 2 bits | quadrant of the incoming hit |

`damageEvent` / `damageYaw` / `damagePitch` / `damageCount`
(`src/codol/snapshot/codol_engine_state.c:287-293`) feed the client's damage
direction indicator only; they do not select animations.

### Movements the pain state selects

From `docs/CODOL_PLAYERANIM_TABLES.json` (extracted from C1 by
`tools/codol_playeranim_catalog.py`):

```
32 flinch_forward   33 flinch_backward   34 flinch_left   35 flinch_right
36 stumble_forward  37 stumble_backward  38 stumble_walk_forward
39 stumble_walk_backward  40 stumble_crouch_forward
41 stumble_crouch_backward  42 stumble_sprint_forward
```

These are the "hurt walking animation" in the report.

### Charge (still correct)

`PlayerCmd_finishPlayerDamage`, retained assembly
`src/asmsource/_g_client_script_cmd_mp.asm:1220..1371`:

```
mov eax, player_dmgtimer_timePerPoint ; ...
add [edx+0xa0], eax                   ; ps->damageTimer += damage*timePerPoint
...  0x7fffffff overflow guard
mov dword [esi+0xa8], 0x1             ; ps->flinchYawAnim = hit quadrant (0..3)
cvtsi2ss xmm0, dword [esi+0xa0]
ucomiss xmm0, [ebp-0x50]              ; vs player_dmgtimer_maxTime
ja  ..._200                           ; clamp: damageTimer = (int)maxTime
mov eax, [esi+0xa0]
mov [esi+0xa4], eax                   ; ps->damageDuration = ps->damageTimer
```

Reached live: `scripts/codol/maps/mp/gametypes/_damage.gsc:1593`
(`self finishPlayerDamage(...)`), the MP damage receiver for players and bots
alike. Dvar defaults `src/g_sv_main.c:630-634`: timePerPoint 100, maxTime 750,
stumbleTime 500, flinchTime 500.

### Selection (correct, but reading a latched input)

`src/codol/player/codol_pmove_c1_ground.c`:

* `flinching_c1()` — C1 `PM_GetNotMovingAnim` `0x004135d5..0x004135fa`:

  ```
  004135d5  mov eax, [edi+0xdc]            ; damageDuration
  004135db  mov edx, [0x1509d38]           ; player_dmgtimer_flinchTime
  004135e1  sub eax, [edx+0xc]
  004135e4  jns +                          ; clamp negative to 0
  004135e8  cmp [edi+0xd8], eax            ; damageTimer > end ?
  004135ee  jle +
  004135f4  mov eax, [edi+0xe0]            ; flinchYawAnim
  004135fa  add eax, 0x20                  ; movement 32..35
  ```

* the stumble column — C1 `PM_GetMoveAnim` `0x00413773..0x0041379a`, table
  `0x00C40978`:

  ```
  00413773  mov eax, [esi+0xdc]
  00413779  mov ecx, [0x150c59c]           ; player_dmgtimer_stumbleTime
  0041377f  sub eax, [ecx+0xc]
  00413788  cmp [esi+0xd8], eax
  00413791  setg cl                        ; cl selects the stumble column
  0041379a  mov eax, [eax*4 + 0xc40978]
  ```

### Discharge — the missing producer (the bug)

C1 discharges the timer inside `PM_WalkMove`, **not** at the top of
`PmoveSingle`:

```
00410997  mov esi, [edi+0xd8]              ; ps->damageTimer
004109ad  call 0x004102c0                  ; PM_DamageSpeedScale(damageTimer)
004109bb  fld dword [ebx+0x24]             ; pml->frametime
004109be  fmul qword [0xc842b0]            ; * 1000.0
004109c4  call 0x00ae0410                  ; ftol
004109c9  mov ecx, esi
004109cb  sub ecx, eax
004109cd  mov [edi+0xd8], ecx              ; ps->damageTimer -= msec
004109d3  test ecx, ecx
004109d5  jg  0x004109e1
004109d7  mov dword [edi+0xd8], 0          ; clamp at zero
```

The retained IW3 path has the identical block inside `Pmove`
(`src/asmsource/_bg_pmove.asm:8260-8272`, `mov [ebx+0xa0], eax`). A whole-.text
scan of C1 for writes to `ps+0xd8` finds exactly two sites: this one and
`0x0041678f` in `PmoveSingle`, the latter guarded by
`otherFlags & 0x400000` (remote-vehicle control, `test [ebx+0x10],0x400000` at
`0x0041673e`) — a branch that never reaches `PM_WalkMove`.

This server stopped running either of them. `src/asmsource/_g_active_mp.asm:1741`:

```
call CODOL_PmoveC1Try
test eax, eax
jnz ClientThink_real_C1PmoveDone     ; retained Pmove, and its decay, skipped
```

and `CODOL_PmoveC1Try` (`src/codol/player/codol_pmove_c1.c:674`) never touched
`damageTimer` — `drop_timers()` (line 641, C1 `PM_DropTimers 0x00413cf0`) only
handles `pm_time`, `legsTimer` and `torsoTimer`.

Consequence: `damageTimer` stayed at its charged value (up to `maxTime` 750)
forever, so `damageTimer > damageDuration - 500` stayed true, so
`CODOL_PM_FootstepsC1` kept selecting 36/38/40/42 while moving and
`idle_animation_c1` kept selecting 32..35 while standing. The only thing that
cleared it was the playerState being rebuilt at respawn — exactly the reported
symptom.

**Bots are affected identically.** `CODOL_StageBotCommandInput`
(`src/codol/weapon/codol_weapon_input.c:43`) sets `raw_valid`, so
`CODOL_ExecutedUsercmd` succeeds for bots and `CODOL_PmoveC1Try` owns their
movement too.

## 2. Fix

New `src/codol/player/codol_pain_state.{c,h}` holds the pain-state arithmetic
(discharge, both windows, both selectors) with the C1 authority addresses, so
it can be exercised without a pmove or a loaded animation script.

`src/codol/player/codol_pmove_c1_ground.c`:

* `CODOL_PM_NormalMoveC1` (the CoDOL port of C1 `PM_WalkMove`) now discharges
  the timer at C1's position — after `friction()`/`wish()` (PM_Friction /
  PM_CmdScale) and before the wish direction:

  ```c
  m->ps->damageTimer=CODOL_PainTimerStep(m->ps->damageTimer,m->local.msec);
  ```

  `m->local.msec` is the chopped command substep `CODOL_PmoveC1Try` already
  uses, so the discharge tracks simulated time exactly, matching
  `(int)(pml->frametime*1000.0)`.
* `flinching_c1()`, the flinch idle movement and the stumble/move-anim table
  now call `CODOL_PainFlinching` / `CODOL_PainFlinchIdleAnim` /
  `CODOL_PainStumbling` / `CODOL_PainMoveAnim`. Behaviour unchanged; the table
  and the windows moved to the tested module.

Deliberately **not** changed:

* No decay in `CODOL_PM_AirMoveC1`, `CODOL_PM_LadderMoveC1`,
  `CODOL_PM_MeleeChargeMoveC1`, the mantle frame or the dive frame. C1 does not
  decay there either (single `ps+0xd8` write in `PM_WalkMove`); a player
  damaged mid-jump resumes discharging on landing.
* C1's second discharge site (`0x0041678f`) belongs to the
  `otherFlags & 0x400000` remote-vehicle pmove branch, which has no equivalent
  branch in `CODOL_PmoveC1Try`. Left unported and recorded here.
* C1's `PM_DamageSpeedScale 0x004102c0` reads `-0.0` from `0xC84920` as its
  minimum-scale constant, so it returns 1.0 for every input: C1 removed the
  damage movement slowdown. Nothing to port; `command_scale()` is already
  correct in omitting it.

## 3. Verification

* `gcc -m32 -Wall -Wextra` on `codol_pmove_c1_ground.c` and
  `codol_pain_state.c` with the makefile's flags: clean, no warnings.
* Full Linux build links:
  `make -j6 OBJ_DIR=obj/codol-painverify LIB_DIR=lib-native bin/codol_dedrun`.
  (A plain `make` currently fails to link because `obj/codol/` holds MinGW
  objects from a concurrent Windows cross-build, and `lib/` holds the Windows
  mbedtls/tomcrypt archives — pre-existing, unrelated to this change.)
* New `tests/test_codol_pain_state.c`, wired into `make test-codol`
  (`makefile:532`). It asserts the discharge, both windows, the C1 table and
  the sprint override, and prints the requested offline trace of a simulated
  8-point hit followed by 66 ms command substeps:

  ```
  elapsed  damageTimer  duration  stumble  flinch  legsAnim
        0          750       750        1       1        36   <- stumble_forward
       66          684       750        1       1        36
      ...
      462          288       750        1       1        36
      528          222       750        0       0        10   <- back to run
      726           24       750        0       0        10
      792            0       750        0       0        10   <- fully cleared
  ```

  It also re-charges to 300 and re-clears, proving the state does not latch.

* Pre-existing failures in `make test-codol`, untouched by this change and
  caused by other workers' in-flight files: `test_codol_native` (undefined
  `CODOL_ResetClientActionSlotState`, `CODOL_ResetClientKillstreakHud`,
  `CODOL_GlassWorld*`, `CODOL_ResetPerkRuntime`, `CODOL_Reset*RadarTypes` — the
  test's explicit source list is stale) and `test_codol_animation_tables`
  (undefined `CODOL_WeaponStateIsDualWielding`, `BG_GetWeaponDef`).

## 4. Live check to run

1. Join Killhouse with bots, take damage from a bot, keep walking.
2. Third-person model must play `stumble_*` for ~500 ms after the last hit and
   then return to the ordinary run/walk movement without respawning; standing
   still must leave `flinch_*` after the same window.
3. `damageTimer` in the playerstate should visibly ramp down to 0 rather than
   sitting at 750 — the 10-bit netfield now changes every frame while it is
   non-zero.
4. Shoot a bot and watch it: bots use the same pmove core, so the bot model
   must recover identically.
