# C1 protected-code questions: partial results (2026-09-28)

Status: partial. Only question 1 has an answer, and it comes mostly from
**unprotected** `.text` code. The other questions and the `.tvm0`
inventory were not done (see "Stopped" below). This is read-only
analysis. No server code was changed.

## Method

- Black-box emulation (Python unicorn) of the C1.exe image, run on
  controlled memory. C1's encoded global pointers
  (`[0x16d3b58 + [idx]*4] ^ key`) point at watched sentinel regions:

  | Index      | Pointer  | XOR key      |
  |------------|----------|--------------|
  | 0x6c3d2ac  | cg       | 0x490b400c   |
  | 0x6c3d2b0  | cgs      | 0x3958bead   |
  | 0x6c3d2b4  | entities | 0x189bfead   |
  | 0x6c3d2b8  | ?        | 0x093df532   |
  | 0x6c3d2bc  | ?        | 0x90834eee   |
  | 0x6c3d2c0  | ?        | 0xddeea363   |

- The emulator logs which fields a routine reads and writes, and which
  `.text` callees it enters.
- The protected routines examined behave as obfuscated native code with
  a small instruction count (about 9k instructions for CG_Missile), not
  as a heavy bytecode interpreter.

## Q1: missile compass team colour

### CG_Missile (`0x43f510` -> `.tvm0 0x8418652`)

Emulation matches T5 `CG_Missile` (OpenBLOPS `cg_ents_mp.cpp:4182`).
Here `es = cent+0xe4`:

- It reads the eFlags byte `es+8` and returns early on 0x20 (nodraw).
- It checks `es+0x58` (launch time) against `cg+0xb0350` (time).
- If the weapon at `es+0xd4` is `>= [0x6c3d28c]`, it clamps the weapon
  to 0.
- It reads the weapon definition from `[0x150d720 + w*4]`.
- It resolves the DObj through `0x25d9ed8` / `0x2575ed8`.
- If `wd+0x8e0 == 4` (ballistic), it calls `0x43f3a0`
  (SetBallisticAngles).
- If `wd+0x340` (weapType) == 1, it runs the HUD-grenade path, which
  reads `wd+0x7b4` and `wd+0xbe2`.

What it does not do, on any path explored:

- It never reads `es+0x9c` or `es+0xa4`.
- It never tests eFlags bit 0x1000.
- It never reached the compass-missile update. This held for guidance
  values 0..39, for weapType 0..11, and for single-field sweeps of every
  field it reads.

### Compass missile list (unprotected)

- **Drawer `0x436030`** (called from 0x436718). It walks 8 entries of
  0x1c bytes at `0x16c75b0 + localClient*0xe0`:
  - `+0` entityNum
  - `+4` lastUpdate
  - `+8/+0xc/+0x10` origin
  - `+0x14` yaw
  - `+0x18` owner client index

  It skips an entry unless `cent.eType == 4` (entity stride 0x228) and
  `lastUpdate >= cg.time - 500`.

- **Colour choice at 0x43625a..0x43629c:**
  - Local team `[cg + 0x15ae70 + cg.clientNum*0xb50]` is compared with
    the owner's team `[cg + 0x15ae70 + entry.owner*0xb50]`.
  - In FFA (local team 0), it compares `cg.clientNum` with the owner
    instead.
  - Equal gives material `[0x16d9c80]` (friendly). Otherwise it uses
    `[0x16d9c84]` (enemy).
  - **So the colour comes from the owner client's clientinfo team, not
    from a team field on the entity.**

- **Slot allocator `0x4369f0`** (ecx = list, edi = entityNum) has one
  caller, in `.tvm0` (0x83fb3bb). I emulated from that call site with a
  sentinel frame (a hand-built stack filled with marker values):
  - entry+0 = entityNum
  - entry+4 = `cg+0xb0350`
  - entry+8..0x10 = cent+0x18..0x20 (via `0x443d90`)
  - entry+0x14 = yaw (via `0x61b730`)
  - entry+0x18 = a local, `[ebp-0x20]`, computed earlier in the
    enclosing routine

  I did not find which es field feeds that local. The enclosing routine
  is not CG_Missile, as far as the sweeps show.

### Answer and confidence

- **The colour depends on the owner index only** (high confidence,
  static read of the unprotected drawer). Then:
  - friendly if the owner's clientinfo team equals the local team;
  - in FFA, friendly only if the owner is the local client.
- **`es+0xa4` does not decide the colour in the drawer.** It could only
  matter if the unidentified producer derives the owner from it, the way
  T5 does with `iHeadIconTeam >> 2`.
- **eFlags 0x1000 is not read** by CG_Missile or the drawer (medium
  confidence: only the explored paths).
- **Unresolved:** which entity field supplies the owner (`es+0x9c`
  versus `es+0xa4`-packed). Server commit 56fda476 publishes owner in
  `es+0x9c` and team in `es+0xa4`.

### Recommendation for the server (not applied)

1. Keep the owner client number correct in `es+0x9c`.
2. Also make the owner's clientinfo team (the configstring the client
   builds clientinfo from) correct. That team is what colours the icon.
3. A live check settles which field is the owner:
   - on a separate test client (never the user's session), put a
     breakpoint at `0x4369f0`;
   - log `edi` and the caller frame's `[ebp-0x20]`;
   - vary `es+0x9c` and `es+0xa4` in turn.

## Stopped

The next step would have meant building tooling that reconstructs the
protected code's control flow (resolving its computed jumps across
`.tvm0`). That falls under the brief's exclusion of general
devirtualization tooling, so I stopped there.

Not done, needing another approach (live test-client plans, or reading
unprotected callers and callees):

- questions 2-9;
- the A/B/C/D inventory of `.tvm0` entry points.

Scratch scripts (emulator only): `scratchpad\tvm2\` (`emu3.py`,
`env.py`, `mid.py`, `q1*.py`).

---

# Part 2: live dynamic analysis (2026-09-28, later the same day)

Status: all eight questions have a live answer. Q1 changed server code
(uncommitted, see "Server change"). The first part's statement that the
routine calling the slot allocator "is not CG_Missile" is wrong. It is
CG_Missile; see Q1.

## Method

- **Test loop, all mine, nothing shared:**
  - My own C1 instance (`C1.exe +set dw_username DynProbe ...
    +set r_fullscreen 0`), driven through the lobby UI (multiplayer, recruit
    training on mp_killhouse_sh, ready) with synthetic clicks and keys.
  - The alpha0022 lobby (`dw-capture.py --port 3074 --respond`). None was
    running, so I started it, with `CODOL_INSTANCE_PORTS=17770`, instance
    spawning off and `CODOL_ADMISSION=0`. Admission enforcement needs a
    launcher JWT, and a local test has none.
  - A test server built from main into `obj/dyn-obj`/`obj/dyn-bin`, on
    udp/17770 with home `D:\t70` and 6 bots.
  - Test-only additions:
    - a `CODOL_DYN_PROBE` build flag with dvar overrides of es+0x80, es+0x9c
      and es+0xa4, since removed from the tree;
    - GSC hooks in a copy of the script tree at `D:\t70\rawfiles`
      (`codol_dynRocket`, `codol_dynAim`/`codol_dynAimPull`, `codol_dynKill`,
      `codol_dynAnglesOut`), never in `bin/home/codol_rawfiles`.
- **Debugger:** `cdb` (x86, Windows Kits) with a late attach to the
  in-match PID. The exe is not relocated: module `C1_exe` sits at 0x400000.
  - Themida did not react to attach, `ba` hardware breakpoints, `bp` at
    0x4369f0, or `t`-tracing 3000 instructions. That includes its own
    `pushfd`/`popfd` sequences, which ran under TF with no visible effect.
- **Three crashes of the test C1, all my tooling, none detection:**
  1. cdb read EOF on stdin and quit without detaching, which killed C1.
  2. A killed cdb left int3 breakpoints behind.
  3. `bc *; qd` inside a breakpoint action detached before DR7 was written
     back. The dump shows a single-step exception at the still-armed DR0.
- **The procedure that works** (`scratchpad\dyn\dbg.py` + `cleardr.py`):
  1. Run `cdb -pd` with CREATE_NO_WINDOW, so it doesn't steal focus from
     the game (focus loss drops held input such as ADS).
  2. Use hardware breakpoints only.
  3. A finished action does `bc *; gc`.
  4. The harness then suspends C1, kills cdb, zeroes DR0-3/DR6/DR7 on every
     thread through Wow64SetThreadContext, and resumes.
- **Read-only sampling** (`ReadProcessMemory`, as in the existing probes)
  answered much of the rest without a debugger.
- **Side effect:** a long watch that fires thousands of times (a noisy
  stack slot) stalls the client long enough for the server to drop it
  (EXE_TIMEDOUT). Keep watches filtered and bounded.

## Q1: missile compass owner (answered, fixed)

- **Call chain:**
  - `.text 0x443cea` calls `.tvm0 0x8418652`, the jump target of
    `CG_Missile` at `0x43f510`.
  - At 0x84d21bf CG_Missile calls an inner routine, `.tvm0 0x832ca85`.
    That is T5's `CG_CompassUpdateGuidedMissileInfo`.
  - The inner routine calls the slot allocator `0x4369f0` from
    `0x83fb3bb`, which returns the entry in `eax`.
- **Single-step trace** of the inner routine for entity 0x193
  (`s7.log`, parsed by `parse7.py`/`flow7.py`). The only centity fields it
  reads are:
  - es+0x118 (a flag byte);
  - es+0xd4 (weapon);
  - **es+0x80**;
  - es+0x00;
  - cent+0x18..0x28 (pose origin and angles).
- **Owner data flow:**
  - step 1091 loads es+0x80;
  - it passes through stack temporaries into `esi`;
  - step 1200 stores it to the owner local `[ebp-0x20]` (0x14fa10);
  - step 1201 compares the same value with `0x7FF` (ENTITYNUM_NONE);
  - step 1646 reloads the local;
  - step 1846 stores it at entry+0x18 (`.tvm0 0x83c63e0 mov [ebp],eax`,
    with ebp used as a data pointer).
- **C1's own producer:** the rocket spawn in C1's server module, at
  `0x5310ce..0x5310d9`:

  ```
  if (weapDef+0x8e0 == 2) ent->s[+0x80] = parent->s.number
  ```

  Guidance 2 is IW4's HELLFIRE, the predator. The same spawn sets
  `eFlags |= 0x1000`, eType 4, weapon +0xd4 and launch time +0x58.
- **A/B, read-only, list at `0x16c75b0`:** a scripted `MagicBullet`
  `remotemissile_projectile_mp`, with the server overriding one field at a
  time.

  | es+0x80 | es+0x9c | es+0xa4 | entry+0x18 (owner) |
  |---|---|---|---|
  | 0 (before the fix; firer 1, 3, 5) | firer | team | **0** |
  | 3 (fix; firer 3) | 3 | 2 | **3** |
  | 5 (forced) | 3 | 2 | **5** |
  | 2 (fix; firer 2) | 12 (forced) | 2 | **2** |

  Before the fix, es+0x9c = 1/5 and es+0xa4 = 1/3 made no difference; the
  owner stayed 0.
- **Entry layout** (C1, not T5): `{entityNum, lastUpdate, origin[3], yaw,
  owner}`. There is no team member.
- **Visual:** the same missile next to the local player draws a **green**
  ring with es+0x80 = self and a **red** ring with es+0x80 = an enemy bot
  (`c_friend_crop.png`, `c_enemy_crop.png`).
- **Side observation:** a guided missile whose es+0x80 is the local client
  also brought up the predator target-box HUD (the red boxes). C1 uses
  es+0x80 == local client for its "my remote missile" view as well, so
  publishing it for someone else's missile would be wrong.

**Answer:** C1 takes the missile's compass owner from **es+0x80**, the
parent's entity number, 11 bits. It is not es+0x9c, and not
es+0xa4>>2 as in T5. The drawer then colours by that owner's clientinfo
team (part 1). The server never published es+0x80 for missiles, so every
missile's owner was client 0, and the icon took client 0's team for
everyone.

### Server change (uncommitted, main tree)

- `src/codol/weapon/codol_weapon_lock_missile.c`:
  `CODOL_ApplyRocketWeaponLock` sets `s.otherEntityNum = owner->s.number`
  when the weapon's `guidedMissileType == MISSILE_GUIDANCE_HELLFIRE`, and 0
  otherwise, mirroring C1 0x5310ce. `otherEntityNum` is unused on missiles
  and is already the +0x80 carrier for script movers.
- `src/codol/snapshot/codol_engine_state.c`: `CODOL_OverlayEngineMissile`
  publishes `otherEntityNum` at es+0x80 when it is 0..ENTITYNUM_WORLD-1.
- Tests:
  - `tests/test_codol_weapon_lock_missile.c` gets a `BG_GetWeaponDef` stub
    and stamp assertions (passes in WSL).
  - `tests/test_codol_native.c` gets the new es+0x80 semantics. It compiles,
    but `test_codol_native` does not link on main for unrelated reasons
    (`CODOL_KillcamTraceFrame`, `codol_debugTrace`, `Com_Printf`... are
    missing from its link line).
- Verification: the fixed probe build was checked live (rows 2-4 of the
  table and the screenshots).
- Not changed: es+0x9c and es+0xa4 are still published for missiles. The
  compass does not read them, and nothing here shows another reader;
  removing them would need its own check.

## Q2: killcam follow (answered: locked follow)

- **Setup:** a scripted kill (`doDamage` from an enemy bot) ran the
  gametype's killcam. Predicted ps sampled at 20 Hz (`kc.py`, `kc2.txt`):
  - alive: pm_type 0, otherFlags 0x1000;
  - dead: pm_type 8;
  - killcam: **pm_type 0, otherFlags 0x800 (POF_FOLLOW), clientNum = killer
    (0), deltaTime (+0xa50) = 6500/6516, killCamEntity (+0xa54) = 2047**;
  - then back to otherFlags 0x1000, clientNum 6.
- **Result:** during the killcam, 40 injected relative mouse moves
  (1200 px) left the drawn angles (`cg+0xB4418`) equal to the followed ps
  viewangles (3.7, 92.3) throughout. The control is the same injection
  while alive, which turns the view about 6.5 degrees per sample.
- **Answer:** with the state this server publishes, C1 runs a **locked
  first-person follow of the killer; local look input does not move the
  camera**. No PM_SPECTATOR fallback is needed for input leakage. The
  killcam draws as "阵亡回放" with the victim marked "你" (`kc_a.png`).
- **Not done:** the killcam-enter block's full field reads (a trace from
  0x46be37) weren't captured. The behavioural A/B settles the
  locked-versus-free question.

## Q3: producer of ps+0x344 bits 0x8/0x10 (answered)

- **Setup:** the `codol_dynAim` hook keeps a bot in front of the player,
  and a change-filtered write watch sits on `cg+0x344` (predicted
  weapFlags).
- **Per rendered frame:**
  1. `memcpy` at `0xae00f7`, called from `0x46c88a` (snapshot to predicted
     playerState), restores the snapshot word.
  2. The client's own **crosshair scan** recomputes the bits. Chain:
     `CG_DrawActiveFrame 0x478cda` → `0x43b9c0` → ... → `0x43bac1` → ... →
     `.text 0x43b8b5` → `.tvm0 0x84aab51`. It then:
     - clears both bits: `.tvm0 0x8400416 and dword ptr [eax],0FFFFFFE7h`;
     - sets **0x10** for an enemy target at `.tvm0 0x842eebc`;
     - for a friendly target calls `0x433a1a` → `0x4331c0`, which sets
       **0x8** at `.tvm0 0x848d2be or dword ptr [ecx],8`.
- **Counts:** 379/379 set/clear pairs on a friendly and 196/254 on an
  enemy.
- **Answer:** the bits are recomputed from the client's own trace every
  frame. They do not come from Pmove, and they are not the server's
  value.
  - The friendly crosshair now turns green with the name shown, and the
    enemy one red: 64% and 77% of samples carry 0x8 and 0x10 respectively.
    The earlier es+0xa8 `solid` fix is what made the trace hit players.
  - The server's published bits only survive in the snapshot copy. The
    crosshair **name** path reads `cg.snap->ps`, so keep publishing them.

## Q4: sway gate cg+0xBF984 and phase cg+0xBF980 (answered)

Write watches, with ADS held through a synthetic right button and cdb
kept off-focus.

- **Gate byte:** written every frame inside `CG_DrawActiveFrame`'s own
  frame (return 0x49f91f):
  - `.tvm0 0x847798f mov byte ptr [edx],0` always;
  - then, under ADS, `.tvm0 0x841a1ca mov byte ptr [eax],1`.

  This is the "writer the static image does not contain" of
  CODOL_SWAY_CAUSE_SWEEP R7/R2b.
- **Phase, per ADS frame, in order:**
  1. `.tvm0 0x8407511` (CG_DrawActiveFrame's frame) **restores the phase
     from a snapshot playerState's +0x4A0**. At the store, `ebx` is a
     snapshot ps (0x1f91a71c or cg+0x35e8), `[ebx+0x4a0]` equals the value
     written, and `edx` = &cg[0xBF980].
  2. `.text 0x45e8a7` (the replay advance, 0x45E830 region; chain
     0x45f791 ← 0x45fb20 ← 0x478952) advances it once per replayed usercmd,
     2-4 times.
  3. `.text 0x4230e5` (chain 0x424706 ← 0x4247d8 ← 0x480c4f ← 0x478b33)
     adds the per-frame idle term.

  Without ADS only the gate=0 write and 0x4230e5 run, and the phase
  accumulates.
- **Answer:** R2 is confirmed and located. The per-frame reset is
  snapshot `ps+0x4A0`, so the server's `CODOL_SwayPhase` value is the
  base C1 rebuilds from every frame while scoped.

## Q5: the `cp @ <ints>` command (answered)

- **Sender:** C1 sends **two** `cp` per gamestate, both through the same
  sender (`CL_AddReliableCommand 0x493bb0` called from `0x4a1e96`):
  - the first directly from `.tvm0 0x844022a` in the gamestate path
    (← `.tvm0 0x838f6cb` ← `.text 0x497558`);
  - the second one level deeper, through `.text 0x4cb35f`.
- **Offline check of five pairs from the server log** (`aggregate ^ count
  ^ XOR(checksums)`): the **first `cp` carries the previous gamestate's
  checksum feed** (stale; 16-18 archives), and **the second carries the
  current feed** (8-12 archives).

  | cp | implied feed | server feed at the time |
  |---|---|---|
  | n=18 | 0x7be51a8b | (earlier session) |
  | n=9 | 0x54ea1175 | 0x54ea1175 |
  | n=16 | 0x54ea1175 | 0x7f8acceb (stale) |
  | n=8 | 0x7f8acceb | 0x7f8acceb |
  | n=16 | 0x0a0c716b | 0x1a9d3fd6 (stale) |
  | n=11 | 0x1a9d3fd6 | 0x1a9d3fd6 |

- **Server behaviour:** `SV_VerifyPaks_f` sets `pureAuthentic = 2` on the
  stale one and `1` on the current one. With `developer 1`, only one
  "CoDOL verified 12 client IWD checksums" appears per pair. The second
  arrives during the load, before the first usermove, so ClientBegin's
  drop at `pureAuthentic == 2` never fires today.
- **Recommendation:** make a failed `cp` whose aggregate matches the
  *previous* feed leave `pureAuthentic` unchanged. That removes a latent
  race.

## Q6: first-command baseline in CL_WritePacket (answered; server discrepancy)

- **Setup:** `MSG_WriteDeltaUsercmdKey 0x59fa30` takes `to` in eax, key at
  [esp+4], `from` at [esp+8] and msg in esi. It is called from
  `.tvm0 0x837624b`.
- **Result:** the first command of every packet uses `from` = a stack
  buffer (0x14eb20); the rest chain from the previous command.
  - Spectating: the buffer is all zero.
  - Alive, sampled three times (standing, with ADS toggled, and after a
    server `setPlayerAngles`):

    | field | base | command | reading |
    |---|---|---|---|
    | buttons | 0x800 with ADS active | 0x20000800 | matches T5 |
    | pitch/yaw (+0x08/+0x0c) | 0x0000/0x8000, later 0x0043/0x802a | 0x0000/0xd25d | base = **-delta_angles** |
    | weapon (+0x14) | 0x78 | 0x78 | |
    | alt weapon (+0x16) | 0x78 | 0 | |
    | offhand (+0x18) | 0 | 0 | |

    In the last sample the view was (-0.37, 115.6) and delta_angles
    (-0.37, 179.77).
- **Explanation:** it is T5's `MSG_SetDefaultUserCmd(&cl->snap.ps)`
  (OpenBLOPS `cl_input_mp.cpp:243`, `msg_mp.cpp:3601`), built from the
  **snapshot** playerState. The snapshot's viewangles are 0 in C1
  (read-only: both snapshot ps copies have delta_angles correct and
  viewangles (0,0,0)). C1's own sender predicate 0x5a44b0, mirrored in
  `codol_playerstate.c field_is_sent`, sends the -87 viewangles fields only
  while following, view-locked, at pm_type 1/6, or with ps+0x14 & 4. The
  server's own angles are right (`getPlayerAngles` (0, -65.45) against the
  client's -65.5).
- **Discrepancy:** `CODOL_DefaultWireUsercmd` (`sv_client.c:1289`) seeds
  the decode base with `ANGLE2SHORT(live viewangles - delta_angles)`, which
  is the command's own value, and `offHandIndex` from the live ps. C1's base
  is `ANGLE2SHORT(snapshot viewangles - delta_angles)`, normally
  `ANGLE2SHORT(-delta_angles)`. The two disagree whenever the view isn't
  0.
  - The decode goes wrong only when a first command's angle equals C1's
    base (the angle is left out as unchanged) but not the server's, i.e.
    view pitch or yaw exactly 0. Level pitch is common, so the pitch
    component can stick for as long as the player looks exactly level
    after looking elsewhere.
- **Recommended fix (not applied, since it needs a live A/B of decoded
  angles):** build the base from the playerState the client last received,
  i.e. the server's held wire fields for that client:
  - viewangles as last published (0 unless the -87 predicate sent them);
  - delta_angles as published;
  - weapon, alt weapon and offhand as published.

## Q7: cl_paused and Menus_CloseAll (answered)

- **Dvar record:** found by a read-only search; name pointer `0xc42d64`.
  It is at `0x02abeed0`: flags 0x2200 at +4, type 0x105 at +8,
  **current value at +0xc**, max 2 further on.
- **Watches** on the value, the key catcher `0x016fc2e0` and
  `Menus_CloseAll .tvm0 0x8411826`, across escape-menu open and close and a
  death:
  - `cl_paused` is written **only 1 (open) and 0 (close)**. Both go
    through the generic `.text` dvar store `0x623267 mov [edi+0Ch],esi`,
    called from the Scaleform UI (`0x948a75` → ... → `0x6a4fd7` →
    `0x62536e` → `0x6251af`). The virtualised `Dvar_SetBool` and
    `Dvar_Set*ByName` do not take part in the escape-menu pause.
  - Opening sets the catcher to 0x10 (`0x6b78e4`, `0x4939e2`), then calls
    `Menus_CloseAll` from the key path (return `.tvm0 0x83ecfd0`, frame to
    `0x49341c`).
  - The server's `r` also reaches `Menus_CloseAll` (`0x46a1de` →
    `0x5f4f91`).
  - **Neither Menus_CloseAll call wrote cl_paused or the catcher.** The
    catcher is cleared at `0x5ecfc8`.
- **Answer:** gate 6 (`cl_paused == 2`) was never observed; nothing wrote
  2. `Menus_CloseAll` is not an unpause and does not strand the catcher.

## Q8: gamestate configstrings and zone arguments (answered)

- **Empty strings:** after a live gamestate, a read-only read of C1's
  `stringOffsets[] 0x06D0D130` / `stringData[] 0x06D1370C`:
  - CS 6517 = 122; CS 5363..5483 carry the published weapons;
  - **all 55 slots CS 5484..5538 have offset 0**, i.e. empty. The mp
    constant table names weapons up to 176 there, but none shows on the
    client.

  So a blank tail leaves those slots empty on the client and does not fall
  back to the constants. Caveat: I did not separately prove that an index
  the server omits (NULL) would show its constant.
- **Zone arguments:** hardware breakpoints on `0x499450`, `0x4CCDF0`,
  `0x618910`:
  - on `map_restart`: the out-of-band `loadingnewmap` path
    (`0x496f7a` → `0x4995b2` → `0x499450("combat")` →
    `0x4CCDF0(ecx="combat", edx="mp_killhouse_sh")`);
  - on a fresh join: the `preloadmap` path (`0x58bf41` → `0x58cac5` →
    `0x49bc01` → `0x499450("combat")`);
  - the `.tvm0` gamestate path never called the zone loader in these runs,
    because the zones were already resident.
- **How the category is used:** `0x4CCDF0` compares the category only
  with `"zm"` (2 chars) and `"coop"`; anything else loads the mp
  category.
- **Discrepancy:** the server's `loadingnewmap` (`src/sv_main.c:5769`)
  sends `sv_g_gametype` ("combat") as the category, while the gamestate
  sends the zone type. Harmless for mp, since any non-zm/coop name selects
  mp. A coop or zm session whose g_gametype does not start with
  "coop"/"zm" would reload the mp category on a map change or restart.
- **Recommendation:** send `codol_zoneType` (CODOL_ServerZoneType()) as
  the second line of `loadingnewmap`. This needs a live coop/zm check
  before it is changed.

## Scratch

- Folder: `scratchpad\dyn\`.
- Harness: `dbg.py`, `cleardr.py`.
- Readers: `mpoll.py`, `kc.py`, `wf.py`, `gate.py`.
- cdb scripts `s*.txt` and their logs `s*.log`.
- Screenshots: `*.png`.
- Server launcher: `server.cmd`.
- GSC hooks: `D:\t70\rawfiles\maps\mp\_load.gsc` (test copy only).

---

# Part 3: the Q5, Q6 and Q8 recommendations, applied and checked live (2026-09-28)

Same test loop as part 2: my own C1, the lobby on udp/17770, home
`D:\t70`, hardware breakpoints only, debug registers cleared after
each session. All three changes are uncommitted.

## Q6: usermove delta base

- **Change:** `SV_UserMove` builds the base with
  `CODOL_DefaultWireUsercmdFromFields` (T5 MSG_SetDefaultUserCmd) over the
  held wire frame the client has at its `messageAcknowledge`. The lookup is
  `CODOL_HistoryReceivedState`: the newest committed frame after
  `gamestateMessageNum`. It used to use the live playerState.
- **Second change:** `CODOL_ReachPlayerFields` now keeps the delta base's
  value for an omitted `-87` view-angle field, which is what C1's snapshot
  playerState holds. The `-87` codec is an absolute short, so no XOR
  desync is possible.
- **Trace:** `set codol_traceUsercmdBase 1` prints each packet's base and
  first command.

Same packets, before and after (C1's base read at `0x59fa30 [esp+8]`):

| build | C1 base | server base |
|---|---|---|
| before, view (8.7,174.9), delta (0,-180) | p0000 y8000 w78/78/0 b0 | p062e yfc67 w120/120/0 b0 |
| after, view (8.8,-5.1), delta 0 | p0000 y0000 w78/78/0 b0 | p0000 y0000 w120/120/0 b0 |
| after, delta (-9.19,58.80), ADS held | p0689 yd631 w78/78/0 b800 | p0689 yd631 w120/120/0 b800 |

After the fix, every decoded first command equals the one C1 sent. A
200 s scripted session (movement, turning, firing both weapons empty,
ADS) ended with a worst difference between server `getPlayerAngles` and
C1's view of 0.0021 deg over 83 settle points.

Note: the old mismatched base never showed up as a live decode error.
C1 repeats up to six commands per packet, so an omitted first command is
almost always one the server has already run.

## Q8: loadingnewmap category

- **Change:** the second line is now `codol_zoneType`, the value the
  gamestate uses, not `sv_g_gametype`.
- **Checked with a hardware breakpoint on 0x499450/0x4CCDF0:**
  - map_restart on mp_killhouse_sh: `"combat"` before the fix, `"mp"`
    after;
  - `map zm_zombie_training`: `"zm"`, and C1 loaded the zm zones (zm HUD);
  - back to mp_killhouse_sh: mp.

## Q5: stale cp

- **Change:** a well-formed `cp` whose implied feed
  (`CODOL_PureCommandFeed`) isn't the current one is no verdict, and the
  pure state stays as it is. A `cp` for the current feed that fails, or a
  malformed one, is still impure (2).
- **Two feeds seen:** the first `cp` names the previous map load's feed
  on a restart or map change, and the client's previous session's feed on
  a join. So the rule compares against "not current" rather than
  "previous".
- **Log, four gamestates** (join, map_restart, zm, mp):

  ```
  CoDOL ignored 18-checksum cp for feed 0bc0d61a (current 690b869a, ...)   join
  CoDOL verified 9 client IWD checksums
  CoDOL ignored 16-checksum cp for feed 690b869a (current 7463a154, previous map load 690b869a)
  CoDOL verified 12 client IWD checksums
  CoDOL ignored 16-checksum cp for feed 7463a154 (current 0990ad73, previous map load 7463a154)
  CoDOL verified 0 client IWD checksums
  CoDOL ignored 18-checksum cp for feed 0990ad73 (current 688cc17e, previous map load 0990ad73)
  CoDOL verified 8 client IWD checksums
  ```

  The client was never marked impure.
- `tests/test_codol_pure.c` covers the stale, genuine-mismatch and
  malformed cases.
