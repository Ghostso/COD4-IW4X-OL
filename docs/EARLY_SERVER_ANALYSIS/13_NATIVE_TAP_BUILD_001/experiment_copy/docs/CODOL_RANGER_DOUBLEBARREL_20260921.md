# The Ranger: C1's complete double-barrel model, and why 36353140 did not fix it

2026-09-21. Everything below is MEASURED from `C1.exe` (CoDOL 1.1.1.13,
ImageBase 0x400000, pefile+capstone over `.text`) and from
`src/asmsource/_bg_weapons.asm`, unless labelled INFERRED.

Standing fact, not re-litigated: `ranger_mp`, `ranger_zm` and
`ranger_upgraded_zm` all carry `fireType(+0x350) = 5` (double barrel) and
`dualWield(+0xbd5) = 0`. Magazine 2.

---

## 0. Lead

**The double discharge is not a broken pin. It is C1 firing the weapon twice
on purpose, from a code path this server does not have.**

C1's per-hand fire dispatch calls **two** shot producers in one pmove frame:
`0x41bb20` at `0x41daf7`, which fires hand 0 whenever the **second trigger**
`0x100000` is down on a non-akimbo `fireType 5` weapon, and then the ordinary
hand gate `0x41b240` at `0x41db03`, which fires hand 0 on bit `0x1`. Hold both
triggers and `0x41b930` runs twice off one command: both barrels leave
together, and `0x41bb6a..0x41bb80` raises `ps+0x344` bit `0x200`, the doubled
kick `BG_WeaponFireRecoil` reads at `0x00422407`.

The retained server has no counterpart to `0x41bb20`, and worse, the raw
`0x100000` never even reaches its fire gate: `CODOL_ToEngineUsercmd` masks the
CoDOL command word with `0xff3f`, and the gate at `PM_Weapon_840` tests
`pm->cmd.buttons` directly. So:

* **holding both triggers** (which is what a player who aims and clicks does —
  `0x100000` is the right mouse button) makes the **client** predict two
  barrels and the **server** fire one → the reported "both barrels fire
  simultaneously on a single left click";
* **holding the right trigger alone** makes the **client** predict one barrel
  and the **server** fire none → the reported "fires on the client, does not
  register on the server".

One root cause, both symptoms. Commit `36353140` could not have fixed either,
because none of its four changes touches the fire dispatch.

Of those four changes: **#2 and #4 are correct and kept, #3 is correct but was
incomplete, #1 was in the wrong place and is reverted** (the same rule now
lives at C1's own arming site). Details in §5.

---

## 1. The complete C1 model

### 1.1 Triggers and hand masks — `0x41b1f0`

`ecx` = weapon index, `eax` = hand, `[ebp+8]` = playerState.

```
0041b1ff  cmp dword [ecx+0x340], edx(1)   weapType grenade ...
0041b207  cmp byte  [ecx+0xbe0], 0        ... with the remote-detonate byte
0041b210  mov eax, 0x100000               -> second trigger, either hand
0041b21a  cmp dword [ecx+0x35c], edx(1)   the akimbo flag
0041b222  neg eax / sbb eax,eax / and eax,0xfff00001 / add eax,0x100000
                                          akimbo: hand0 -> 0x100000, hand1 -> 0x1
0041b232  neg eax / sbb eax,eax / and eax,0xfffff     / add eax,edx(1)
                                          plain:  hand0 -> 0x1,      hand1 -> 0x100000
```

Primary trigger = `0x1`. Second trigger = `0x100000`, C1's raw right-mouse
button. For the Ranger (not akimbo, one hand) the mask is `0x1`.

### 1.2 The quota helper — `0x41a9d0`, table `0x41aa4c`

```
0041a9d3  mov ecx, [ebp+8]            the WeaponDef
0041a9d6  mov ecx, [ecx+0x350]        fireType
0041a9dc  dec ecx
0041a9dd  cmp ecx, 5 / ja 0x41aa00    fireType 0 and >6 -> 0
0041a9e2  jmp dword [ecx*4 + 0x41aa4c]
0041a9f7  cmp dword [edx + eax*0x1c + 0x280], 1 / jae -> 1
```

Table bytes at `0x41aa4c`: `e9 a9 41 00 | 04 aa 41 00 | 1b aa 41 00 |
32 aa 41 00 | e9 a9 41 00 | 00 aa 41 00`, i.e.

| fireType | arm | "spent" when |
|---|---|---|
| 0 | `ja` at 0x41a9e0 | never |
| 1 single shot | 0x41a9e9 | shotCount >= 1 |
| 2 burst2 | 0x41aa04 | shotCount >= 2 |
| 3 burst3 | 0x41aa1b | shotCount >= 3 |
| 4 burst4 | 0x41aa32 | shotCount >= 4 |
| **5 double barrel** | **0x41a9e9** | **shotCount >= 1** |
| 6 spin-up | 0x41aa00 | never |

Per-hand block stride `0x1c`: weaponTime `+0x26c`, weaponDelay `+0x270`,
kick-restriction `+0x274`, fresh-pull bit `+0x27c`, shotCount `+0x280`,
weaponstate `+0x278`. So a double barrel is **semi-automatic: one round per
trigger pull**, exactly like a single-shot rifle.

### 1.3 The fresh trigger-pull latch — `0x41ab10` (called once, `0x41dc1d`)

```
0041ab23  mov edx, [edx+0x350]       fireType
0041ab29  cmp edx, 2 / jl 0x41ab72   <- leaves
0041ab2e  cmp edx, 4 / jg 0x41ab72   <- leaves
0041ab38  cmp dword [eax+0x35c], edx(1)      akimbo?
0041ab40  test byte [ecx+8], dl  / 0041ab45 test byte [ecx+0x30], dl
0041ab4a  or dword [eax+0x298], edx          akimbo hand 1, from bit 0's edge
0041ab50  test dword [ecx+8], 0x100000 / 0041ab59 [ecx+0x30]
0041ab6c  or dword [eax+0x27c], edx          hand 0's latch
```

`[ecx+8]` = `pm->cmd.buttons`, `[ecx+0x30]` = `pm->oldcmd.buttons` (usercmd
stride `0x28`). **The latch exists for burst weapons (2..4) only** and is set
on the rising edge of that hand's trigger. A double barrel never gets one.

### 1.4 The semi-automatic pin — `0x41ace0`, per hand at `0x41dc36`

The function only reaches its decision on the frame `weaponTime` expires:

```
0041ad3e  mov eax, [ebx+0x26c]       weaponTime   (ebx = ps + hand*0x1c)
0041ad4a  test eax,eax / je 0x41af6d          idle: nothing to decide
0041ad52  sub eax, ecx / mov [ebx+0x26c], eax
0041ad5a  jg 0x41af6d                         still counting: nothing to decide
```

Then:

```
0041adc9  mov eax, [ebx+0x27c] / and eax,1    the fresh-pull bit
0041add2  mov [ebp-0x10], eax
0041add5  jne 0x41adf2                        latched -> spent = 0
0041addf  call 0x41a9d0                       else spent = quota helper
0041ade7  mov dword [ebp-8], 1
0041adee  test al,al / jne 0x41adf9
0041adf2  mov dword [ebp-8], 0
0041adf9  [ebp-0xc] = (def+0x340 == 1 && def+0xbe4 != 0)   "always pins"
0041ae1c  ecx = ps->weapon;  eax = hand;  call 0x41b1f0     the mask
0041ae2a  mov ecx, [ebp+8] / mov ecx, [ecx+8]               cmd.buttons
0041ae30  mov edi, ecx / and edi, eax         EDI = buttons & mask
0041ae37  cmp dword [esi+0x35c], 1 / je 0x41ae7b        akimbo leaves
0041ae3e  mov eax, edi
0041ae45  cmp dword [edx+0x350], 5 / jne 0x41ae7b       double barrel only
0041ae4e  mov edx, [esi+0x344] / and edx, 0x100         the ARMED BARREL
0041ae5a  je 0x41ae60
0041ae5c  test eax,eax / jne 0x41ae6c   armed && primary   -> clear spent
0041ae60  test edx,edx / jne 0x41ae73
0041ae64  test ecx, 0x100000 / je 0x41ae73
0041ae6c  mov dword [ebp-8], 0         !armed && second    -> clear spent
0041ae73  and ecx, 0x100000 / or eax, ecx     EAX = EDI | second trigger
0041ae7b  mov ecx, [ebx+0x278]                weaponstate
0041ae81  cmp ecx,0x10 / 0041ae86 cmp ecx,0x15 / jle 0x41af3d    16..21 leave
0041ae8f  cmp [ebp-8],0 / jne / cmp [ebp-0xc],0 / je 0x41af3d
0041ae9f  test eax,eax / je 0x41af3d                  the pin needs EAX
0041aeaa  movzx ecx, word [cmd+0x18] / cmp ps->weapon, ecx / jne 0x41af3d
0041aec3  call 0x40f220                               can this weapon fire?
0041aed5  mov dword [ebx+0x26c], 1                    PIN: weaponTime = 1
```

and the not-pinned tail:

```
0041af3d  test edi,edi / je 0x41af47      EDI, the PLAIN request
0041af41  cmp [ebp-0x10],0 / je 0x41af63  held and no fresh pull -> keep count
0041af4a  call 0x41aa70                   still inside a burst?
0041af57  jne 0x41af63
0041af59  mov dword [ebx+0x280], 0        RESET the hand's shot count
0041af63  mov dword [ebx+0x26c], 0        weaponTime = 0
```

Two things to keep straight, because the retained engine conflates them:

* **EAX** (mask ∪ second trigger, for a non-akimbo double barrel) gates the
  **pin** at `0x41ae9f`.
* **EDI** (mask only) gates the **shot-count reset** at `0x41af3d`.

`0x41aa70`, the burst-continuation helper, answers "still bursting" only for
`fireType != 0 && fireType != 6 && shotCount != 0 && !quotaDone`
(`0x41aaa3`, `0x41aaa7`, `0x41aab5`, `0x41aac4..0x41aacf`). For fireType 5 the
quota is met at one round, so it answers **no** and the counter is reset.

### 1.5 The armed barrel — written at every shot, `0x41babc` (inside `0x41b930`)

```
0041babc  cmp dword [esi+0x35c], eax(1) / je 0x41baef     akimbo skips
0041bac4  cmp dword [ebx+0x350], 5      / jne 0x41baef    double barrel only
0041bacd  mov edx, [ebp+8]                                 the pmove
0041bad0  test dword [edx+8], 0x100000                     the command's second trigger
0041bad9  or  dword [esi+0x344], 0x100                     -> armed
0041bae5  and dword [esi+0x344], 0xfffffeff                -> not armed
```

`ps+0x344` bit `0x100` is therefore **"the last shot was taken by the second
trigger"**, and §1.4 reads it as "the *other* trigger releases the pin". That
is how both barrels get out on one magazine without releasing the trigger.

### 1.6 The fire dispatch — the part that was missed

```
0041da54  cmp dword [ecx + hand*0x1c + 0x26c], ebx(0)   weaponTime must be 0
0041da5e  jne 0x41db1f
0041da64  cmp dword [eax + 0x270], ebx                  weaponDelay must be 0
0041da6a  jne 0x41db1f
...
0041daf7  call 0x41bb20                    <-- SECOND-TRIGGER SHOT, hand 0
0041db03  call 0x41b240                    <-- the hand gate
0041db0d  je 0x41db1f
0041db17  call 0x41b930                    <-- the primary shot, hand EDI
```

and `0x41bb20` itself:

```
0041bb28  mov esi, [ebx]                        ps
0041bb2a  cmp dword [esi+0x35c], 1 / je 0x41bb9e         akimbo leaves
0041bb41  cmp dword [ecx+0x350], 5 / jne 0x41bb9e        double barrel only
0041bb4a  and dword [esi+0x344], 0xfffffdff     clear bit 0x200 every frame
0041bb54  mov ecx, [ebx+8]                      cmd.buttons
0041bb5d  test ecx, 0x100000 / je 0x41bba8      no second trigger: return
0041bb65  test cl, 1        / je 0x41bb86       primary too?
0041bb6d  call 0x417fc0                         rounds in the magazine
0041bb75  cmp eax, 1 / jle 0x41bb86
0041bb7a  or edi, 0x200 / mov [esi+0x344], edi  BOTH BARRELS flag
0041bb8f  xor eax, eax
0041bb91  call 0x41b930                         FIRE HAND 0
```

The hand gate `0x41b240` takes only `mask & pm->cmd.buttons`
(`0x41b270..0x41b275`) — that part of the previous pass was right. What it got
wrong is the conclusion: `0x41bb20` is a *separate* producer that the gate
knows nothing about, and it is the one that fires the second barrel. **In C1
the right trigger fires a barrel on its own, and both triggers together fire
both barrels in the same frame.** `ps+0x344` bit `0x200` has exactly one
reader, `0x00422407` in `BG_WeaponFireRecoil`, where it squares the horizontal
kick — it is a recoil flag, not a second shot.

### 1.7 Summary of the model

| input | C1 | magazine |
|---|---|---|
| left, tap | one barrel; `armed` cleared; pin holds while held | −1 |
| left, held after the shot | pinned (`weaponTime = 1`) | — |
| left released | shot count reset (`0x41af59`), pin released | — |
| right alone | one barrel via `0x41bb20`; `armed` set | −1 |
| left then right without releasing | second barrel: `!armed && 0x100000` clears spent at `0x41ae64` | −1 |
| right then left without releasing | second barrel: `armed && primary` clears spent at `0x41ae5c` | −1 |
| **both at once** | **two barrels in one pmove frame**, `0x200` doubled kick | **−2** |
| any | never a fresh-pull latch; `0x41ab10` is burst-only | — |

---

## 2. Symptom (a): both barrels, "one left click"

The player's right mouse button *is* the second trigger. Aiming and clicking
puts `0x1` and `0x100000` on the same command, and C1's client prediction then
runs `0x41bb20` **and** the hand gate, emptying the two-round magazine in a
single frame with the `0x200` kick. That is C1 behaving as designed.

Our server fires once for that command, so the two barrels the player sees are
the client's prediction; the snapshot then argues with it. Nothing in
`36353140` addressed it, because the missing code is the fire dispatch, not the
pin.

A second, smaller contributor once the pin started working: with the commit's
`PM_Weapon_1560` arm in place but no matching reset, `PM_Weapon_1660` left
`fireType 5` in the *keep the counter* arm (§3.2), so the hand stayed spent
after its first round.

## 3. Symptom (b): right trigger fires on the client, not on the server

Three measured facts compose it:

1. **The client fires.** `0x41bb20` is not gated by the hand mask, only by the
   pin. Once the server stopped publishing a bogus fresh-pull latch and started
   publishing a truthful shot count and armed barrel (changes #1/#3/#4), the
   client's pin released on the second trigger at `0x41ae64` and the prediction
   fired. Before that the client's pin state was wrong in the other direction
   and the predicted shot was reverted on the next snapshot, so the trigger
   looked dead.
2. **The server's gate cannot see the button.** `CODOL_ToEngineUsercmd`
   (`src/codol/snapshot/codol_game.c`) does
   `engine->buttons = game.buttons & UINT32_C(0xff3f)`, so `0x100000` never
   reaches `pm->cmd.buttons`, and the retained fire gate is a raw test:

   ```
   PM_Weapon_670:  mov eax,[ebp-0x5c] / mov eax,[eax+0x8] / mov [ebp-0x28],eax
   PM_Weapon_830:  mov eax, 0x1
   PM_Weapon_840:  test [ebp-0x28], eax
                   setnz bl
   ...             test bl, bl / jnz PM_Weapon_760   -> the shot
   ```

   (`PM_Weapon_700` swaps the mask to `0x80000` for `def+0x5a8`, which is C1's
   `0x41b1f0` grenade arm.) `bl` was always 0 for the right trigger.
3. **There is no second producer.** Nothing in the tree corresponds to
   `0x41bb20`.

## 4. The other measured divergences this pass found

### 4.1 The fresh-pull arm brackets the wrong fire types

`PM_Weapon_360` drops fire types 0 and 1 and lets **everything else** through
to `PM_Weapon_170`, which sets `ps->weapFlags |= 0x100` on the trigger edge.
C1 `0x41ab29..0x41ab31` requires 2..4. So a double barrel (5) and a spin-up (6)
latched a bit C1 never sets, and `codol_engine_state.c:693` publishes it to the
client as `ps+0x27c`, where `0x41adc9/0x41add5` read it as *skip the pin*.

Commit `36353140` cleared the latch in `CODOL_WeaponStateUpdate`, which the asm
calls at `PM_Weapon_20` — PM_Weapon's **exit**. `PM_Weapon_170` sets the latch
and `PM_Weapon_1830` consumes it inside one and the same `PM_Weapon` call, so
the clear could never reach the decision that read it. It only sanitised the
published copy.

### 4.2 The shot count is never reset for fireType 5

C1 resets it through the generic helper (§1.4 tail). The retained
`PM_Weapon_1610` switch stops at 4:

```
PM_Weapon_1660: cmp eax,0x3 / jz PM_Weapon_2170
                cmp eax,0x4 / jnz PM_Weapon_1630      <- 5 and 6 land here
```

`PM_Weapon_1630` keeps the counter; `PM_Weapon_1640` is the reset. With the
counter stuck at 1 a Ranger is permanently "spent" after its first round, which
is what `36353140`'s `PM_Weapon_1560` arm would have produced on its own.

### 4.3 The pin request and the reset request were the same query

`PM_Weapon_1600` (C1's `0x41ae9f`, needs **EAX**) and `PM_Weapon_1590` (C1's
`0x41af3d`, needs **EDI**) both called `CODOL_WeaponStateFireRequest`, the plain
mask. With the second trigger now able to fire, the plain query at the pin site
would have let the right trigger re-fire every frame it was held.

### 4.4 The armed barrel was read one frame late

`CODOL_WeaponStateRecordShot` took the second-trigger bit from
`state->command_buttons`, which `CODOL_WeaponStateUpdate` captures at
`PM_Weapon_20` — i.e. the **previous** command. C1 reads the command being
executed, inside the shot (`0x41bad0`). On a rising edge, which is exactly when
a shot starts, the captured word is the wrong one.

---

## 5. What changed in this pass

Files touched: `src/asmsource/_bg_weapons.asm`,
`src/codol/weapon/codol_weapon_state.c`,
`src/codol/weapon/codol_weapon_state.h`. Line endings preserved exactly:
`_bg_weapons.asm` 9363 CR / 9434 lines and `codol_weapon_state.c`
2352 CR / 2362 lines, both keeping their pre-existing LF-only islands (71 and
10 lines) untouched; the header is pure LF as before.
`src/codol/snapshot/codol_engine_state.c` and
`src/codol/weapon/codol_weapon_flags.h` were **not** touched.

### 5.1 `_bg_weapons.asm`

| site | change | C1 evidence |
|---|---|---|
| `PM_Weapon_360` | `cmp eax,0x3 / ja PM_Weapon_160` after the existing 0/1 drops, so only fire types 2..4 arm the latch | `0x41ab29..0x41ab31` |
| `PM_Weapon_840` | after `setnz bl`, call `CODOL_WeaponStateSecondTriggerFires(esi)` and force `bl = 1` on a hit | `0x41bb20` called at `0x41daf7` |
| `PM_Weapon_1790` | call `CODOL_WeaponStateDoubleBarrelSecondShot(edi)` right after the first shot's event is queued | `0x41bb20` + `0x41db17`: `0x41b930` twice per command |
| `PM_Weapon_1600` | the pin's request is now `CODOL_WeaponStatePinRequest`, not the plain hand request | `0x41ae73` feeding `0x41ae9f`, vs `0x41af3d` |
| `PM_Weapon_1660` | `cmp eax,0x5 / jae PM_Weapon_1640` — fire types 5 and 6 reset the shot count | `0x41af47..0x41af59` + helper `0x41aa70` |

### 5.2 `codol_weapon_state.c` / `.h`

* new `double_barrel_command()` — C1's two standing exclusions (`0x41bb2a`
  akimbo, `0x41bb41` fireType) plus the executed CoDOL command word;
* new `CODOL_WeaponStateSecondTriggerFires(ps)` — `0x41bb20`'s gate;
* new `CODOL_WeaponStateDoubleBarrelSecondShot(ps)` — the simultaneous second
  barrel: `PM_Weapon_2210`'s magazine decrement with its turret and
  `player_sustainAmmo` exclusions, `PM_Weapon_1320`'s saturating counter,
  `CODOL_WeaponStateRecordShot`, and the fire event. Guarded by
  `CODOL_WeaponLockFireEvent` exactly as `PM_Weapon_1310` guards the first;
* new `CODOL_WeaponStatePinRequest(ps, hand)` — EAX as against EDI;
* `CODOL_WeaponStateRecordShot` now reads the executed command directly rather
  than last frame's capture (§4.4);
* **reverted**: the fresh-pull clear in `CODOL_WeaponStateUpdate` (§4.1). The
  rule now lives at the arm, where C1 puts it.

### 5.3 Verdict on commit 36353140's four changes

| # | change | verdict |
|---|---|---|
| 1 | clear `CODOL_WEAP_FRESH_PULL` outside 2..4, in `CODOL_WeaponStateUpdate` | **right rule, wrong place — reverted**, moved to `PM_Weapon_360` |
| 2 | `CODOL_WeaponStateDoubleBarrelReleasesPin` | **correct, kept** — it is `0x41ae37..0x41ae6c` verbatim |
| 3 | the `PM_Weapon_1560` double-barrel arm | **correct but incomplete, kept** — it needed §4.2's reset to be usable |
| 4 | publishing `ps+0x344` bit `0x100` from the armed barrel | **correct, keep it** — `0x41ae4e` reads it out of the playerState, it is prediction-base state the client cannot rebuild, and `0x41babc` shows the server is the writer. It did not *cause* symptom (b); it revealed it by fixing the client's pin |

Nothing in `codol_engine_state.c` needs to change.

## 6. Known remaining divergences (deliberate, documented)

1. **Empty-magazine second trigger.** C1 calls `0x41b930` for the second
   trigger even with an empty magazine and lets the fire routine dry-fire it.
   `CODOL_WeaponStateDoubleBarrelSecondShot` returns instead and leaves the
   retained empty/reload handling in charge.
2. **`ps+0x344` bit `0x200`.** Its only reader is the client's own
   `BG_WeaponFireRecoil` at `0x00422407`, and `0x41bb4a` recomputes it from the
   command every frame, so the client derives it during prediction. The server
   applies its own (undoubled) kick for the pair. Publishing it would mean a
   producer in `codol_engine_state.c`, which this pass does not own.
3. **Fire animation on the simultaneous pair.** `PM_Weapon_1950/1360` picks the
   fire/fire-empty animation from the magazine before the extra round leaves,
   so a 2→0 pair animates as a non-empty shot. C1 re-selects per shot inside
   `0x41b930`.
4. **Akimbo fresh-pull edges.** C1 `0x41ab38..0x41ab6a` arms hand 1 from the
   raw bit-0 edge and hand 0 from the raw `0x100000` edge while akimbo;
   `PM_Weapon_170` still tests the raw native bit 0 for the edge. It only
   matters for akimbo **burst** weapons, of which the shipped zones have none.

## 7. Build

`tools\BUILD-CODOL.ps1 -ObjectsOnly` → exit 0. Symbols present:

```
obj/codol/codol_weapon_state.o:  T _CODOL_WeaponStateSecondTriggerFires
                                 T _CODOL_WeaponStatePinRequest
                                 T _CODOL_WeaponStateDoubleBarrelSecondShot
obj/codol/_bg_weapons.o:         U _CODOL_WeaponStateSecondTriggerFires
                                 U _CODOL_WeaponStatePinRequest
                                 U _CODOL_WeaponStateDoubleBarrelSecondShot
                                 t PM_Weapon_CoDOLNoSecondTrigger
```

Not linked, not promoted, no server started or stopped.

## 8. What to watch on the next live test

* left tap → **one** round, and the gun can fire the second on a second tap
  (this exercises §4.2's reset);
* right tap alone → **one** round that registers on the server;
* hold left, add right → the second barrel leaves immediately;
* hold both → **two** rounds in one frame and an empty gun, with client and
  server now agreeing (this is C1's behaviour, not a bug);
* holding either trigger down after a shot must not auto-fire.
