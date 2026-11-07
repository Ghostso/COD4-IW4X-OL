# Mounted-turret ADS zoom is instantaneous — 2026-09-20

**One-sentence defect:** C1 ramps a linked player's `ps.fWeaponPosFrac` over the dvar-driven
turret transition time (`"210"`, default **250 ms**) in an arm it reaches *before* the
`WeaponDef +0xbc8 aimDownSight` gate, while this server evaluated `aimDownSight` first — and
`turret_minigun_mp` ships with `aimDownSight == 0`, so the server pinned the fraction at `0.0`
every command and its turret arm (which snapped to the endpoint anyway) was unreachable.

Same neighbourhood as `docs/CODOL_MINIGUN_CRASH_20260920.md`, different subsystem: that was
`turret_think_client` in `_g_misc_mp.asm`; this is the C1 pmove ADS producer.

---

## 0. Confirming which weapon

The brief's identification holds and I found nothing pointing at a carried or killstreak minigun.
`turret_minigun_mp` is the only weapon asset in `mp_overgrown`'s fastfile
(`docs/zone_assets/mp_overgrown.txt:229`), `maps/mp/_utility.gsc:632 isMG()` names it, and it is
the only minigun that is mountable — i.e. the only one that can ever set
`PLAYER_EFLAG_TURRET_MASK` and reach the code below. [MEASURED — I re-read the asset list and
re-extracted the definition from the fastfile, see §2.]

The fix is **not** weapon-specific: C1's turret ADS arm never reads the weapon definition, so it
applies identically to every mountable turret on every map (§1). A carried or killstreak minigun
would take the *ordinary* ADS path, which is untouched by this change.

---

## 1. What actually drives turret zoom

### 1.1 The reference is C1, because IW4 and IW3 have no turret ADS at all

Retained CoD4/IW3 `PM_UpdateAimDownSightLerp` (`src/asmsource/_bg_weapons.asm:5752`):

```asm
PM_UpdateAimDownSightLerp_40:
	test dword [ebx+0xb0], PLAYER_EFLAG_TURRET_MASK
	jnz PM_UpdateAimDownSightLerp_60      ; -> fWeaponPosFrac = 0; adsDelayTime = 0; return
```

A mounted MG in IW3/IW4 simply cannot aim down sight. [MEASURED — retained source in this tree.]

IW4 agrees: `iw4mp.pdb` (`D:\CoD\iw4x_development`) contains `PM_UpdateAimDownSightLerp` and
`player_adsExitDelay`, but **no `BG_PlayerCanAds`** and **no turret-ADS dvar** — the bypass and its
tuning dvars do not exist in MW2. T5/OpenBLOPS has no turret-ADS symbol either.
[MEASURED — symbol/string search of the PDB and the OpenBLOPS tree.]

So "what the correct behaviour is" cannot be taken from IW4 or T5. **C1.exe 1.1.1.13 is the
reference**, and it is a better one: it is the client that predicts this exact field.

### 1.2 C1 `PM_UpdateAimDownSightLerp` 0x004185a0 — the turret arm

[MEASURED — `objdump -d -M intel` of `C1.exe`, image base 0x400000.]

```
4185c2  test DWORD PTR [esi+0xec],0xc00   ; ps->eFlags & PLAYER_EFLAG_TURRET_MASK
4185cc  fild DWORD PTR [ecx+0x28]         ; (float)pml->msec  -- raw, computed before the branch
4185cf  mov  edi,DWORD PTR [eax*4+0x150d720]   ; bg_weaponDefs[weapon]
4185d9  je   418655                       ; NOT linked -> ordinary ADS path (aimDownSight gate)
; ---- linked / turret ----
4185dd  mov  ecx,ds:0x1509e94             ; dvar "210"
4185e3  fcom DWORD PTR [ecx+0xc]          ; 0.0 vs value
4185eb  jp   418642                       ; value <= 0 (or NaN) -> snap arm
4185ed  test BYTE PTR [esi+0xc],0x10      ; pm_flags & PMF_ADS_BUTTON
4185f1  fld  DWORD PTR [ecx+0xc]
4185f4  fld1
4185f6  fdivrp st(1),st                   ; rate = 1.0 / value
4185fd  fld rate / fmul msec / fadd [esi+0x348]     ; button down  -> frac + rate*msec
41860b  fld [esi+0x348] / fld rate / fmul msec / fsubp   ; button up -> frac - rate*msec
418619  fstp DWORD PTR [esi+0x348]
41861f  call 0x4010e0                     ; clamp(frac, 0.0, 1.0)
41863d  jmp  4187ef                       ; store, then adsDelayTime = 0, return
; ---- snap arm (value <= 0) ----
418642  test BYTE PTR [esi+0xc],0x10
418646  je   4187ef                       ; -> frac = 0.0
41864e  fld1                              ; -> frac = 1.0
4187f5  mov  DWORD PTR [esi+0x350],0      ; adsDelayTime = 0
```

Three things this arm does **not** do, all load-bearing:

* it never reads the weapon definition — not `+0xbc8 aimDownSight`, not the `+0xa28/+0xa2c`
  per-millisecond ADS rates the ordinary path multiplies by;
* it never reads the hand state (`ps+0x278`);
* it never applies the ability-10 elapsed-time modifier — C1 applies that at `0x0041875b`,
  downstream of the `je 418655`, so it is on the ordinary path only.

The turret transition is therefore **global tuning data, not weapon data**.

### 1.3 C1 `BG_PlayerCanAds` 0x00418140 — the same bypass on the flag

```
418172  test DWORD PTR [edx+0x10],0x1000  ; ps->otherFlags & 0x1000
418179  je   41816f                       ; -> false
41817b  test DWORD PTR [edx+0xec],0xc00   ; turret?
418181  je   41818d                       ; no -> weapon-definition tests
418183  mov  ecx,ds:0x150c5ac             ; dvar "209"
418189  mov  al,BYTE PTR [ecx+0xc]
41818c  ret                               ; RETURN THE DVAR
41818d  ... test BYTE PTR [esi+0xbc8],0 ... ; aimDownSight, states, PMF_* -- unreached when linked
```

`PM_UpdateAimDownSightFlag` (0x00418240) calls it and sets `pm_flags |= 0x10` from
`canAds && (cmd->buttons & 0x800)`. So on a turret, `PMF_ADS_BUTTON` is gated by dvar `"209"`
alone. [MEASURED.]

`PM_UpdateAdsFlag` (0x00415330) is the one place C1 *does* refuse a turret:
`test DWORD PTR [eax+0xec],0xc00 / jne ret` — `PMF_ADS` (0x40) is never set while linked.
This server already matches that (`codol_pmove_c1.c:496`); **no change needed there**, and it
confirms the zoom is driven purely by `fWeaponPosFrac`, not by `PMF_ADS`.

### 1.4 The two dvars

Registered in one block at `0x0040c1f3..0x0040c258`. Pairing rule: a `mov ds:X,eax` sitting
between an argument block and a `call` holds the **preceding** call's return value, so the name
pushed immediately before a `call` pairs with the store that appears after the *next* argument
block. [MEASURED, and cross-checked in §5.]

| C1 name | type | default | range | flags | pointer | sole reader |
|---|---|---|---|---|---|---|
| `"209"` | bool  | `1`     | —          | `4` | `0x150c5ac` | `BG_PlayerCanAds+0x43` (0x418183) |
| `"210"` | float | `250.0` | `[0,5000]` | `4` | `0x1509e94` | the turret arm (0x4185dd) |

Names decoded from `.rdata` (`0xc40668 = "209"`, `0xc4066c = "210"`); default `250.0` at
`0xc845b0`, max `5000.0` at `0xbeedfc`; `Dvar_RegisterBool = 0x624370`,
`Dvar_RegisterFloat(name,value,min,max,flags,desc) = 0x6244d0`. Descriptions are empty strings
(C1 is name-stripped — see the "C1.exe dvars are stripped/numeric" note). [MEASURED.]

C1 flags `4` is IW4's `DVAR_CHEAT`, so an unmodified client always runs the defaults.
Neither dvar is `SYSTEMINFO`/`CODINFO`, so neither travels in C1's replicated-dvar bank
(`CODOL_CS_DVAR_NAMES 24` / `CODOL_CS_DVAR_VALUES 224`); `CODOL_RefreshServerDvars` only
replicates `CVAR_SYSTEMINFO` cvars whose names are already in the inherited bank. [MEASURED —
`src/codol/assets/codol_sv_assets.c:405-430`.]

**The timing the reference implies: a full hip -> ADS zoom in 250 ms, and a full ADS -> hip
zoom out in 250 ms, linear, clamped, identical for every turret.**

---

## 2. `turret_minigun_mp`'s real WeaponDef

Extracted from the type-28 blob in `mp_overgrown`'s fastfile with
`tools/codol_weapondef_zone_diff.py` (blob `[0:0xBFC]` is the runtime def verbatim; the asset is
4420 bytes with the name at `+0xBFC`). [MEASURED.]

| offset | field | value |
|---|---|---|
| `+0xbc8` | `aimDownSight`      | **0** |
| `+0xbc9` | `bRechamberWhileAds`| 0 |
| `+0xbcf` | `adsFireOnly`       | 0 |
| `+0xa28` | `fOOPosAnimLength[0]` (ADS-in rate/ms)  | `0x3b5a740e` = 0.003333 (= 1/300) |
| `+0xa2c` | `fOOPosAnimLength[1]` (ADS-out rate/ms) | `0x3b03126f` = 0.002 (= 1/500) |
| `+0x694` | `overlayReticle` | 0 |

`src/codol/weapon/codol_weapon_native.c:451` copies `blob[0xbc8]` straight into
`def->aimDownSight`, so the server's definition really does hold `0`. [MEASURED.]

The `+0xa28/+0xa2c` pair is **not** what governs turret zoom (§1.2) — those 300 ms / 500 ms
numbers are a decoy. Correcting the definition would be the wrong fix: the client would still
ignore it while linked.

---

## 3. What was wrong

`src/codol/player/codol_pmove_c1.c` diverged from C1 at three points, all of them ordering:

1. **`update_ads_lerp_c1` (line 619)** put the `aimDownSight` gate *ahead* of the turret test:

   ```c
   if(!def || !def->aimDownSight || (state_known && state>=13 && state<=15)) {
       ps->fWeaponPosFrac=0.0f; ps->adsDelayTime=0; goto trace;
   }
   if(!state_known) { ps->adsDelayTime=0; goto trace; }
   if(ps->eFlags&0x0c00) { ... }        /* unreachable for turret_minigun_mp */
   ```

   With `aimDownSight == 0` the first `if` fires on every command of the mount and clamps the
   fraction to `0.0`.

2. **The turret arm itself (line 628)** snapped:

   ```c
   ps->fWeaponPosFrac=(ps->pm_flags&0x10) ? 1.0f : 0.0f;
   ```

   Its comment ("a global transition record absent from the retained server … its zero-duration
   C1 branch") describes C1's `value <= 0` arm. That arm exists, but it is not the one C1 takes:
   the dvar defaults to 250, not 0. This is the code the bug report is named after — it would
   produce an instantaneous zoom on any turret whose definition *did* set `aimDownSight`.

3. **`update_aim_down_sight_flag` (line 468)** gated `can_ads` on `def->aimDownSight`
   unconditionally, so `PMF_ADS_BUTTON` was never set while mounted — C1 answers with dvar `"209"`
   and never looks at the definition.

**Net server behaviour before the fix:** `ps.fWeaponPosFrac == 0.0` and `pm_flags & 0x10 == 0`
for the entire time a player is on the minigun. [MEASURED by reading the code paths; not observed
live — I was not permitted to start a server or client.]

---

## 4. Where the value reaches the client — **server publish, every frame**

`src/codol/snapshot/codol_engine_state.c:484`:

```c
if(!put_float(&out,0x348,ps->fWeaponPosFrac) || !put_float(&out,0x34c,ps->aimSpreadScale)) return 0;
```

`ps+0x348` is published **unconditionally in every playerstate**, and the only server-side writers
of the field are the three sites in `codol_pmove_c1.c` plus the reset in `g_cmds.c:913` (the
retained IW3 lerp is disabled; no `.asm` writes `ps+0x348`). The client predicts the same field in
its own pmove but re-bases on each snapshot, so the server's value is authoritative at every
snapshot boundary. [MEASURED — grep of every writer; the prediction re-basing itself is INFERRED
from standard Q3/CoD prediction, not observed.]

**Therefore: this is a server publish / pmove-parity fix, not a weapon-def correction.**
Editing `turret_minigun_mp`'s `aimDownSight` would be wrong twice over — C1 never reads it on this
path, and it is shipped client data.

---

## 5. The fix

### 5.1 New, in my tree: `src/codol/weapon/codol_weapon_turret_ads.{c,h}`

Registers C1's two dvars as real server dvars with the same type, default and range (the existing
in-tree precedent for a stripped C1 dvar is `codol_script_weapon_visual_queries.c:90`, which also
uses a readable name and a lazy `Cvar_Register*`), and implements the arm from §1.2 instruction
for instruction:

```c
int   CODOL_TurretAdsAllowed(void);          /* dvar bg_turretAdsEnabled, bool,  1              */
float CODOL_TurretAdsTransitionMsec(void);   /* dvar bg_turretAdsTime,    float, 250, [0,5000]  */
int   CODOL_TurretAdsLerp(playerState_t *ps, int msec);   /* 1 = owned the frame */
```

`CODOL_TurretAdsLerp` returns 0 unless `ps->eFlags & PLAYER_EFLAG_TURRET_MASK`; otherwise it
snaps when the duration is `<= 0` or NaN (C1's `fcom`/`jp` arm covers the unordered case, which
`!(duration > 0.0f)` reproduces), and otherwise computes `rate = 1.0f/duration` **once** and adds
or subtracts `rate * (float)msec` — same operation order as C1, because
`msec/duration` would diverge in the last bits from the fraction the client predicts. It clamps to
`[0,1]` and clears `adsDelayTime`, as both C1 arms do.

**No hardcoded lerp duration and no per-weapon constant.** The 250 ms is a dvar default taken from
C1's registration, exactly as C1 stores it; the value is read through the dvar on every call.
Flags are `CVAR_CHEAT`, which is IW4OL's spelling of C1's `DVAR_CHEAT` — locked to the default
unless cheats are enabled, matching the client.

Residual caveat, called out as required: the *identity* of the two dvars rests on the
argument-block pairing rule in §1.4. Cross-check that made me confident: the same block registers
the pointer `0x150c550`, which is read at `0x00548f1d` inside C1's silenced-flash-tag query
(`0x548ea0`) — the dvar `codol_script_weapon_visual_queries.c:86` already documents. Under the
pairing rule that pointer is dvar `"208"`, and the existing comment there calls it `"209"`; the
comment pairs the name pushed at `0x40c1fc` with the store at `0x40c201`, but a store of `eax`
placed *before* a `call` cannot hold that call's result. So `0x150c550 = "208"` (flash tag),
`0x150c5ac = "209"` (turret ADS gate), `0x1509e94 = "210"` (turret ADS time).
**That existing comment is wrong by one and should be corrected — it is a comment only, no
behaviour depends on it, and the file is not mine to edit.**

### 5.2 Build

```
make obj/codol/codol_weapon_turret_ads.o     ->  clean, no warnings (-Wall)
nm obj/codol/codol_weapon_turret_ads.o
  T _CODOL_TurretAdsAllowed  T _CODOL_TurretAdsLerp  T _CODOL_TurretAdsTransitionMsec
  U _Cvar_RegisterBool       U _Cvar_RegisterFloat
```

Objects only — no bare `make`, nothing linked, nothing copied into `bin/`. Both new files are LF,
matching `.gitattributes * text=lf` and every other file I touched; **no existing file was
modified**, so no line-ending churn is possible from this pass.

---

## 6. HAND-BACK — patch for `src/codol/player/codol_pmove_c1.c` (not my file)

**Verified, not hand-derived:** I applied these four hunks to a scratch copy at
`obj/_tmp/turretads/patched.c` and compiled it with the makefile's exact command line for
`obj/codol/codol_pmove_c1.o` (`-Wall -std=gnu11 -O1 -DCODOL_SERVER …`). **Exit 0, no warnings**,
and the resulting object shows `U _CODOL_TurretAdsAllowed` / `U _CODOL_TurretAdsLerp`. Each anchor
below occurs exactly once in the file at `8239d806`. The file is LF; keep it LF.

**Hunk 1 — include** (after `#include "codol_weapon_state.h"`, line 28):

```c
#include "codol_weapon_state.h"
#include "codol_weapon_turret_ads.h"
```

**Hunk 2 — `update_aim_down_sight_flag`, replace lines 468-469:**

```c
/* OLD */
    int can_ads=(ps->otherFlags&0x1000) && def && def->aimDownSight &&
                !blocked_state;
/* NEW */
    /* C1 BG_PlayerCanAds 0x0041817b: once ps->eFlags carries the turret pair
     * the answer is dvar "209" alone and the weapon definition is never
     * consulted.  turret_minigun_mp ships aimDownSight == 0, so the def test
     * below refuses every mounted MG and the turret never leaves the hip. */
    int turret=(ps->eFlags&(int)PLAYER_EFLAG_TURRET_MASK)!=0;
    int can_ads=(ps->otherFlags&0x1000) &&
                (turret ? CODOL_TurretAdsAllowed()
                        : (def && def->aimDownSight && !blocked_state));
```

**Hunk 3 — same function, replace line 477:**

```c
/* OLD */
    if(!state_known) return;
    flags&=~0x10u;
/* NEW */
    /* C1's turret arm reads no hand state, so an unclassifiable pair must not
     * hold PMF_ADS_BUTTON down while linked. */
    if(!state_known && !turret) return;
    flags&=~0x10u;
```

**Hunk 4 — `update_ads_lerp_c1`, replace lines 617-632** (this both inserts the call and deletes
the old snapping turret block):

```c
/* OLD */
    state_known=CODOL_ResolveEngineWeaponState((unsigned)ps->weaponstate,
                                               (unsigned)ps->weapAnim,&state);
    if(!def || !def->aimDownSight || (state_known && state>=13 && state<=15)) {
        ps->fWeaponPosFrac=0.0f;
        ps->adsDelayTime=0;
        goto trace;
    }
    if(!state_known) { ps->adsDelayTime=0; goto trace; }
    /* Linked/turret modes use a global transition record absent from the
     * retained server. Its zero-duration C1 branch snaps to the requested
     * endpoint and avoids carrying an IW3 timer into C1 prediction. */
    if(ps->eFlags&0x0c00) {
        ps->fWeaponPosFrac=(ps->pm_flags&0x10) ? 1.0f : 0.0f;
        ps->adsDelayTime=0;
        return;
    }
/* NEW */
    state_known=CODOL_ResolveEngineWeaponState((unsigned)ps->weaponstate,
                                               (unsigned)ps->weapAnim,&state);
    /* C1 0x004185c2 tests the turret pair FIRST -- ahead of the +0xbc8
     * aimDownSight gate at 0x00418655 and ahead of every hand-state test --
     * and lerps the fraction over dvar "210" milliseconds (default 250)
     * instead of snapping.  In the old order turret_minigun_mp's
     * aimDownSight == 0 zeroed the fraction for the whole mount and the
     * turret branch below was unreachable. */
    if(CODOL_TurretAdsLerp(ps,move->local.msec)) return;
    if(!def || !def->aimDownSight || (state_known && state>=13 && state<=15)) {
        ps->fWeaponPosFrac=0.0f;
        ps->adsDelayTime=0;
        goto trace;
    }
    if(!state_known) { ps->adsDelayTime=0; goto trace; }
```

`move->local.msec` is the raw millisecond count C1 uses at `0x4185cc` — deliberately **not**
`ads_frame_msec_c1()`, whose ability-10 modifier is on the ordinary path only.

After applying, rebuild objects only:
`make obj/codol/codol_pmove_c1.o obj/codol/codol_weapon_turret_ads.o`.

---

## 7. Live verification checklist (I could not run it)

1. Mount the Overgrown minigun, hold ADS. Expect a ~250 ms ramp in and out, not a snap.
2. `bg_turretAdsTime 0` (with cheats) must reproduce the old instantaneous behaviour — that is
   C1's own `value <= 0` arm and is the falsification test for the whole diagnosis.
3. `bg_turretAdsEnabled 0` must disable turret ADS entirely.
4. Trace `CoDOL sway:` (`CODOL_TRACE_VERBOSE`) while mounted: `posFrac` should walk
   `0x00000000 -> 0x3f800000` over ~250 ms instead of jumping, and `pmf` should show `0x10` set
   while the button is held and `0x40` (PMF_ADS) *clear* — C1 refuses PMF_ADS on a turret.

---

## 8. Adjacent findings, not fixed

* **`src/codol/script/codol_script_weapon_visual_queries.c:86-89`** — comment mis-names the
  flash-tag dvar as C1 `"209"`; it is `"208"` (§5.1). Comment only.
* **`ads_frame_msec_c1` is missing C1's second scaler.** On the ordinary (non-turret) path C1 runs
  `call 0x0040ebf0` at `0x00418783` and doubles the elapsed millisecond count when it returns
  true (`fadd st(0),st` at `0x0041878f`); the same predicate is consulted in
  `PM_UpdateAimDownSightFlag` at `0x004182ce`. This port applies the ability-10 modifier but not
  that doubling, so ordinary ADS runs at half speed whenever the predicate holds. [MEASURED that
  the instructions exist and are absent from the port; the predicate's *meaning* is
  INFERRED/unidentified.] Out of scope here — it is on the path this change does not touch, and it
  is not my file.
* `src/bg_public.h` `bgs_s` layout — still open from the crash pass, unrelated, parent-owned.

## Artifacts

* Full C1 disassembly used above: regenerate with
  `objdump -d -M intel "…/Call of Duty Online 1.1.1.13/C1.exe"` (PE image base `0x400000`;
  `.rdata` file offset = `0x741000 + (VA - 0xb42000)`). ~515 MB; deleted after use.
* Scratch verification build of the hand-back patch: `obj/_tmp/turretads/`.
