# The Ranger fires wrong: the double-barrel input contract, 2026-09-20

Reported: *"left click fires the rangers shotgun twice while right click
doesn't fire at all"*, broken "for a while now", not zm-specific.

**Verdict: the Ranger is not dual wield. It is a `fireType 5` double barrel,
and both halves of the symptom are one missing C1 contract — the second
trigger and the armed-barrel flag that goes with it.** The doubling has a
single, cheap root cause that is fixed in this pass; the dead right trigger
needs two more hunks in files this worker does not own, written out verbatim
in §6.

Everything is MEASURED from the shipped fastfiles and from `C1.exe`
(ImageBase 0x400000, pefile+capstone, `.text`) unless labelled INFERRED.

---

## 1. The Ranger is a double barrel, not akimbo

MEASURED, type-28 blobs (`blob[0:0xBFC]` is the runtime `WeaponDef`, name at
`+0xBFC`):

| zone | asset | `fireType` (+0x350) | `dualWield` (+0xbd5) | `weapType` (+0x340) |
|---|---|---|---|---|
| `common_gametype_mp` | `ranger_mp` | **5** | **0** | 0 |
| `common_gametype_zm` | `ranger_zm` | **5** | **0** | 0 |
| `common_gametype_zm` | `ranger_upgraded_zm` | **5** | **0** | 0 |
| `ui_viewer_mp` | `ranger_mp` | **5** | **0** | 0 |

Two corrections to the task framing:

* `ranger_zm` **does** exist (`docs/zone_assets/ALL_weapon.txt:789`,
  `common_gametype_zm`). Nothing interesting follows from its absence because
  it is not absent.
* The Ranger the server actually hands out in MP is the composed
  `*a 39 0` — base index 39 = `ranger_mp`, camo 0, **no attachment items**.
  MEASURED from `bin/home/main/qconsole.premelee.log`:
  `CoDOL giveammo: name *a 39 0 engine 121 ammo ranger_mp idx 26 clip
  ranger_mp idx 26 size 2 start 20 -> clip 2 reserve 18`. Magazine size 2.
  Akimbo Rangers are a *different* composition: the `akimbo_ranger`
  `weaponattach` asset exists in `common_gametype_mp` and its record `[0]`
  writes `off=0xbd5 type=6 (bool)` — the dual-wield byte. Nothing in the
  live loadout selects it, so `CODOL_WeaponIsDualWield` is correctly 0 here
  and the akimbo hand machinery is not on the path. Both hands collapsing
  onto one input was a good hypothesis; it is not what happened.

`fireType 5` = double barrel (C1 quota dispatcher `0x41a9d0`, table
`0x41aa4c`, six entries `0x41a9e9 0x41aa04 0x41aa1b 0x41aa32 0x41a9e9
0x41aa00`; type 5 shares the single-shot arm and is spent at one round).

## 2. What C1 does with a double barrel (three measured sites)

**(a) `0x41b1f0` — which button fires which hand.** `ecx` = weapon index,
`eax` = hand, `[ebp+8]` = playerState.

```
0041b1ff  cmp [ecx+0x340], 1        weapType grenade ...
0041b207  cmp byte [ecx+0xbe0], 0   ... and the remote-detonate byte
0041b210  mov eax, 0x100000         -> the second trigger, either hand
0041b21a  cmp [ecx+0x35c], 1        the akimbo flag
0041b222  neg eax / sbb / and 0xfff00001 / add 0x100000
                                    akimbo: hand0 -> 0x100000, hand1 -> 0x1
0041b232  neg eax / sbb / and 0xfffff / add 1
                                    plain:  hand0 -> 0x1,      hand1 -> 0x100000
```

`hand_request_mask()` in `src/codol/weapon/codol_weapon_state.c:317`
reproduces this exactly. It is **correct as written** — no change needed.
For the Ranger (not akimbo, one hand) the mask is `0x1`, the left trigger.

**(b) `0x41babc..0x41bae5` — the armed barrel is written at every shot.**

```
0041babc  cmp [esi+0x35c], eax      not while akimbo
0041bac4  cmp [ebx+0x350], 5        fireType double barrel
0041bacd  mov edx, [ebp+8]          the pmove
0041bad0  test [edx+8], 0x100000    the command's second trigger
0041bad9  or  [esi+0x344], 0x100    -> armed
0041bae5  and [esi+0x344], ~0x100   -> not armed
```

So **C1 keeps "which trigger took the last shot" in its playerState weapon
flags word, `ps+0x344` bit `0x100`.**

**(c) `0x41ae37..0x41ae79` — the armed barrel releases the semi-auto pin.**
Inside the pin block `0x41adc6..0x41aed5` (`eax` = `buttons & mask`,
`ecx` = raw `cmd.buttons`, `[ebp-8]` = "quota spent"):

```
0041ae37  cmp [esi+0x35c], 1 / je 0x41ae7b      akimbo skips the arm
0041ae45  cmp [edx+0x350], 5 / jne 0x41ae7b     double barrel only
0041ae4e  mov edx, [esi+0x344] / and edx, 0x100 the armed barrel
0041ae5a  je 0x41ae60
0041ae5c  test eax, eax / jne 0x41ae6c          armed && this hand's trigger
0041ae60  test edx, edx / jne 0x41ae73
0041ae64  test ecx, 0x100000 / je 0x41ae73      !armed && the second trigger
0041ae6c  mov dword [ebp-8], 0                  the quota flag, cleared
0041ae73  and ecx, 0x100000 / or eax, ecx       the live request gains 0x100000
```

Read plainly: **a double barrel pins after one round like any semi-auto, and
un-pins the moment the trigger asking is not the one that took the last
shot.** That is how the second barrel gets out on the same magazine.

**(d) What C1 does *not* do.** The fire gate `0x41b240` (single caller,
`0x41db03`) takes `mask & pm->cmd.buttons` at `0x41b270..0x41b275` and
nothing else. There is no `0x100000` arm there. MEASURED: **in C1, the right
trigger on its own never opens the gate.** It only releases the pin while the
left trigger is held, which is what lets both barrels go. Any "fix" that
makes right-click fire from idle would be inventing a third answer; per the
standing mandate C1 wins and the correct end state is *left trigger fires a
barrel, and the second barrel follows when the other trigger joins in.*

## 3. Root cause of "left click fires twice"

MEASURED, C1 `0x41ab10` (the fresh trigger-pull latch, called from `PM_Weapon`
at `0x41dc1d` before the per-hand machines):

```
0041ab23  mov edx, [edx+0x350]      fireType
0041ab29  cmp edx, 2 / jl 0x41ab72  <- leaves
0041ab2e  cmp edx, 4 / jg 0x41ab72  <- leaves
```

**C1 arms the latch for fire types 2..4 only.** Burst weapons. A double
barrel (5) or a spin-up (6) never gets one.

The retained arm, `src/asmsource/_bg_weapons.asm` `PM_Weapon_360` (line 6712)
to `PM_Weapon_170` (line 7317), brackets only 0 and 1:

```
	mov eax, [eax+0x140]        ; fireType
	test eax, eax / jz PM_Weapon_160      ; full auto leaves
	sub eax, 0x1  / jz PM_Weapon_160      ; single shot leaves
	<fire request hand 0>                  ; everything else falls through
PM_Weapon_170:
	test byte [edx+0x28], 0x1   ; old command's trigger -> an edge
	or dword [ebx+0x10], 0x100  ; ps->weapFlags |= 0x100
```

So on this server a left-click edge on the Ranger sets `weapFlags` bit
`0x100`, and `src/codol/snapshot/codol_engine_state.c:693` publishes it:

```c
!put(&result,0x27c,((unsigned)ps->weapFlags>>8)&1u)
```

`ps+0x27c` is C1's own per-hand fresh-pull bit, read back at `0x41adc9`:

```
0041adc9  mov eax, [ebx+0x27c] / and eax, 1
0041add5  jne 0x41adf2              -> [ebp-8] = 0, the quota flag is dropped
```

**The client is therefore told, every time the player clicks, that its
semi-automatic pin does not apply.** With the pin gone and the trigger still
held the gate reopens on the next frame and the second barrel goes out. The
Ranger's magazine is exactly 2, so the player sees exactly two shots per
click and then a reload. That is the reported symptom, exactly.

(The same bogus latch reaches fire type 6, the spin-up weapons, for the same
reason.)

## 4. Root cause of "right click doesn't fire at all"

Three things, in order of how much they matter:

1. **Nothing on this server produces C1's armed barrel.** `ps+0x344` bit
   `0x100` is never written to the wire: `CODOL_OverlayEngineWeaponUseControl`
   masks `0x9d` and `0x101000`; the switch/offhand overlays mask `0x800` and
   `0xe0000`. Bit `0x100` is untouched, so the client's copy is stomped back
   to the delta base on every snapshot. C1's `!armed && second trigger` arm
   (`0x41ae64`) is the one that would let the right trigger release the pin,
   and it is being fed a flag the server never maintains.
2. **The server's own pin never takes the double-barrel arm.** The quota latch
   for fire type 5 is set unconditionally at `PM_Weapon_1560`
   (`_bg_weapons.asm:8788`); `0x41ae5a..0x41ae6c` has no counterpart there.
   `CODOL_WeaponStateSecondBarrelArmed()` — the query that answers it — had
   **zero callers** in the tree before this pass. `state->second_barrel` was
   being computed at every shot by `CODOL_WeaponStateRecordShot` and thrown
   away.
3. **Right-click from idle is supposed to do nothing** (§2d). Once 1 and 2 are
   fixed the second trigger does what C1 makes it do: it lets the other barrel
   out while the first trigger is held. If the user's expectation is
   "right-click fires a barrel from a standing start", that is not C1 and is
   not what should be built.

## 5. What landed in this pass (files this worker owns)

`src/codol/weapon/codol_weapon_flags.h`
: New `CODOL_WEAP_FRESH_PULL 0x100u`, documenting the collision: the retained
  engine uses that bit number for the fresh-pull latch, C1 uses the same bit
  number in `ps+0x344` for the armed barrel, and they are different things.

`src/codol/weapon/codol_weapon_state.c`, `CODOL_WeaponStateUpdate`
: **The fix for "fires twice".** `CODOL_WeaponStateUpdate` is called from
  `PM_Weapon_20` (`_bg_weapons.asm:6581`), which every exit of `PM_Weapon`
  reaches, so it is the retained machine's own exit. C1's arming rule is
  enforced there, before the hand-0 mirror and before `publish_hand`:

```c
    if(ps->weapFlags & (int)CODOL_WEAP_FRESH_PULL) {
        const struct WeaponDef *held = weapon_def(ps->weapon);
        if(!held || held->fireType < WEAPON_FIRETYPE_BURSTFIRE2 ||
           held->fireType > WEAPON_FIRETYPE_BURSTFIRE4)
            ps->weapFlags &= ~(int)CODOL_WEAP_FRESH_PULL;
    }
```

  Burst weapons (2..4) keep the latch. Everything else loses it, which is
  what C1 does. The server's next frame and the published `ps+0x27c` both
  stop claiming a fresh pull that C1 would never have.

`src/codol/weapon/codol_weapon_state.c` / `.h`
: New `CODOL_WeaponStateDoubleBarrelReleasesPin(ps, hand)`, a faithful port
  of `0x41ae37..0x41ae6c`: returns 1 when the quota flag must be cleared —
  akimbo leaves, non-double-barrel leaves, otherwise `armed ? (buttons &
  mask) : (buttons & 0x100000)`. It reads the live `state->second_barrel`
  (updated at this frame's shot, as C1 updates `ps+0x344` at `0x41bae5`) and
  the executed CoDOL command word. It has no caller yet; §6.1 wires it.

Build: `tools/BUILD-CODOL.ps1 -ObjectsOnly` → exit 0. Symbol present:
`00001639 T _CODOL_WeaponStateDoubleBarrelReleasesPin` in
`obj/codol/codol_weapon_state.o`. Not linked, not promoted, nothing copied
into `bin/`.

## 6. Handoff — two hunks in files this worker does not own

### 6.1 `src/asmsource/_bg_weapons.asm` (CRLF file, 9262 CRs before the edit)

At `PM_Weapon_1560`'s CoDOL double-barrel arm, line 8788. `EBX` is the
playerState at this point, as the neighbouring hooks assume.

```diff
 	cmp eax, 0x5
 	jnz PM_Weapon_1540
 	cmp dword [ebx+0xf0], 0x1
 	jb PM_Weapon_1540
+	; C1 0x41ae37..0x41ae6c: a double barrel whose *other* trigger is asking
+	; clears the quota flag instead of latching it, so the barrel that did
+	; not take the last shot still comes out on this magazine.
+	; PM_Weapon_1540 stores 0 and falls through to the same PM_Weapon_1690.
+	extern CODOL_WeaponStateDoubleBarrelReleasesPin
+	pushad
+	mov ecx, esp
+	and esp, 0xfffffff0
+	sub esp, 0x10
+	; ECX is caller-clobbered; keep the saved stack in our unused slot.
+	mov [esp+0xc], ecx
+	mov dword [esp+0x4], 0x0
+	mov [esp], ebx
+	call CODOL_WeaponStateDoubleBarrelReleasesPin
+	mov esp, [esp+0xc]
+	test eax, eax
+	popad
+	jnz PM_Weapon_1540
 	mov byte [ebp-0x4a], 0x1
 	jmp PM_Weapon_1690
```

### 6.2 `src/codol/snapshot/codol_engine_state.c` (CRLF file, 2045 CRs before the edit)

Publish C1's armed barrel. In `CODOL_OverlayEngineWeaponUseControl`, after
the existing pickup/riot-shield statement:

```diff
         wire->field[i]=(wire->field[i]&~UINT32_C(0x101000)) |
             ((ps->weapFlags&CODOL_WEAP_PICKUP_DISABLED) ? UINT32_C(0x100000) : 0) |
             ((ps->weapFlags&CODOL_WEAP_RIOTSHIELD_NEXT) ? UINT32_C(0x1000) : 0);
+        /* C1 keeps the armed barrel of a double-barrel weapon in this word
+         * at bit 0x100 (written 0x41bad9/0x41bae5, read 0x41ae4e). The
+         * retained weapFlags uses that bit number for its own fresh-pull
+         * latch, which publishes to ps+0x27c instead, so the value here comes
+         * from the hand bundle and never from ps->weapFlags. Without it the
+         * client's armed barrel is reset by every snapshot and the second
+         * trigger can never release its pin. */
+        wire->field[i]=(wire->field[i]&~UINT32_C(0x100)) |
+            (CODOL_WeaponStateSecondBarrelArmed(ps) ? UINT32_C(0x100) : 0);
```

`CODOL_WeaponStateSecondBarrelArmed` is already declared in
`codol_weapon_state.h:261` and already implemented; this is its first caller.

### 6.3 Live check after both land

1. MP, equip the Ranger. One left click → **one** shot, magazine 2 → 1.
2. Hold left, tap right → the second barrel fires, magazine 1 → 0, reload.
3. Right click alone from idle → nothing. That is C1 (§2d); do not "fix" it.
4. Burst weapons must be unchanged — they are the only types that keep the
   fresh-pull latch.

---

# Task 2 — second look at "the melee animation is not fixable"

**The conclusion in `docs/CODOL_MELEE_ANIM_20260920.md` holds.** It survived
an adversarial pass and I strengthened two of its measurements rather than
breaking any.

**The composed-weapon channel is real, and it is genuinely shut in zm.**
The doc's strongest claim is that `weaponattach` records can write animation
name slots but no zm zone ships one. Both halves re-measured independently
today:

* *Records can write slot 7.* Dumping `akimbo_ranger` from
  `common_gametype_mp` by raw record layout (not through the buggy `attach`
  mode of `codol_weapondef_zone_diff.py`) gives records at `off=0x098` and
  `off=0x09c`, type 0 (string), alongside `off=0xbd5` type 6. So a composed
  `*a <base> ...` name *can* carry a melee-animation override. The channel
  exists.
* *No zm zone has one.* `docs/zone_assets/ALL_weaponattach.txt` has 277 rows
  over 91 catalogued zones: `common_gametype_mp` 225,
  `patch_common_gametype_mp` 51, `code_post_gfx_default_mp` 1. **Zero rows
  name any `*_zm` zone**, and `patch_common_gametype_zm`, `zm_prototype_sh`,
  `zm_zombie_training` and `zm_asylum_sh` are all present in the census, so
  this is a measured absence and not a gap in the catalogue. Opening
  `common_gametype_zm` directly and counting type-43 assets gives **0**.

Composition happens on the client, from the client's own zone
(`BG_BuildCustomWeaponDef 0x4216C4` memcpy's the 0xBFC base then applies
type-43 records it looks up itself). A composed name the server invents that
refers to an attachment only `common_gametype_mp` holds resolves to nothing
in a zm match. There is no third route: no server field carries a name, and
C1's name getter `0x45c500` returns `def[0x7c + 4*index]` raw with no
fallback.

**The 18/22 split is real.** Independently re-measured on
`common_gametype_zm`: of 153 type-28 assets, **109 hold `0x3007f4b7` at slot
7 (`def+0x098`) and 44 hold something else**. `0x3007f4b7` is the pooled
empty string — it occupies 41 of the first 64 name slots in `ak104_zm`,
`coltanaconda_zm`, `m14ebr_zm` and `famas_zm` alike, which no real animation
name would. The four named in the report are all in the empty group;
`m1911_upgraded_zm` and `glockdw_zm` carry a real ref (`0x30205ddd`) at slot
7. Restricted to the 40-weapon zm roster that is the doc's 22/18.

**The falsifiable prediction stands and is strengthened, not refuted:** melee
with the FAMAS, the FAL or the AK-104 and nothing plays; melee with the
Ranger, the SPAS-12 or the P90 and it does. `ak104_zm` and `famas_zm` are
byte-identical to `coltanaconda_zm` across slot 7, so if the reported weapons
are silent these must be too.

**What a real fix would take** — this is data authoring, not server work:

1. Build a `weaponattach` (type-43) asset, e.g. `zm_melee_fix`, whose records
   write `+0x098` = `viewmodel_knife_melee_slice` and `+0x09c` =
   `viewmodel_knife_melee_stab` (both xanims already mount in
   `common_gametype_zm`, assets 186/187).
2. Ship it inside a zone a zm match mounts — realistically
   `patch_common_gametype_zm`, which already carries 530 assets and is the
   intended override point — **and** give it a row in
   `mp/coWeaponAttachmentTable.csv` so a `*a <base> <item> 0` name resolves
   to it.
3. Only then does the server's part become trivial: hand out the composed
   name instead of the bare one, which `codol_weapon_compose.c` already does
   for 18 composed definitions per match.

Step 2 means rebuilding a shipped fastfile. Until someone does that, the
answer to "can the server fix the missing knife animation in zm" is **no**,
and the reason is that the 22 definitions name no animation and the only
override channel C1 has needs an asset that no zm zone contains.
