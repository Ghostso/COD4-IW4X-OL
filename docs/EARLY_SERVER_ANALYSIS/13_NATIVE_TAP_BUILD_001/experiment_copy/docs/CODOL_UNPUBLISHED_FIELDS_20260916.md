# CoDOL snapshot fields C1 reads that the server never publishes (2026-09-16)

Implementation backlog derived from docs/CODOL_SNAPSHOT_BITMASK_AUDIT_20260916.md
("documented, unfixed" list). Every entry below was re-checked in C1.exe
1.1.1.13 (ImageBase 0x400000) with the capstone cache used by that audit
(`C:\Users\Michael\AppData\Local\Temp\claude\psaudit\ins.pkl`, whole-image
xref by displacement + base-register provenance) so that offset-name traps are
called out: several audit sites turned out to read WeaponDef / cg structs, not
the playerState. Widths and netfield indices are from
src/codol/snapshot/codol_player_fields.inc and codol_client_fields.inc. IW4
names are from the iw4x lineage (semantics only, never offsets).

Severity: **high** = visible gameplay defect in CoDOL modes today, **medium** =
cosmetic / edge case, **low** = no consumer in CoDOL modes or a trap (nothing to
do).

## Summary

| struct | high | medium | low | entries |
|---|---|---|---|---|
| playerState (fields) | 2 | 1 | 6 | 9 (0x354/0x358 counted as one) |
| playerState bits (weapFlags 0x344, linkFlags 0x14) | 1 | 1 | 2 | 4 |
| clientState | 0 | 3 | 3 | 6 |
| entityState / actor / hudelem / objective | 0 | 0 | 0 | 0 (audit found none) |
| **total** | **3** | **5** | **11** | **19** |

Work items (non-trap) in priority order:

1. **ps+0x354/0x358 spreadOverride / spreadOverrideState** (high) — native
   fields exist and the server pmove already consumes them; just publish.
2. **ps+0x14 bit 1 PLF_ANGLES_LOCKED** (high) — produced by C1's link methods,
   53 GSC files link players.
3. **ps+0x333c spawn time** (high) — C1 PM ignores a stale `cmd.weapon==0` for
   200 ms after this stamp; unpublished it is 0 and the gate never fires.
4. **clientState 0x018 dualWielding / 0x01c riotShieldNext / 0x0a8 diveState**
   (medium) — third-person animation conditions for other players.
5. **clientState 0x008/0x00c 64-bit party id, 0x134 colour index, 0x12c
   vehicle entity** (medium/low).
6. **weapFlags 0x100000 disable-weapon-pickup** (medium, GSC-only source).
7. weapFlags 0x10000 / 0x200 (low, client-managed or no consumer).

Traps (no work): ps+0x0060, ps+0x0218, ps+0x0350, ps+0x053c/0x0540 — the audit
sites read other structs; no playerState reader exists.

---

## 1. playerState

### 1.1 [HIGH] ps+0x354 spreadOverride (idx 209, 6 bits) and ps+0x358 spreadOverrideState (idx 210, 2 bits)

**Status:** BUILT-TESTED 2026-09-16 (build 01bbe537): published by CODOL_OverlayEngineAim, codol_engine_state.c:451-479; trace `CoDOL ps: client N spreadOverride`. Wire check needs a C1 client.

**C1 readers (verified playerState-based):**
- BG_CalcSpread 0x422660 (esi = ps, ecx = WeaponDef, ebx = &minSpread, edi = &maxSpread):
  `if (ps->0x358 == 2) min = max = (float)ps->0x354; else <stance/viewheight
  formula from def+0x6b8..0x6cc>; if (ps->0x358 == 1) max = (float)ps->0x354;`
  (0x422663-0x422734).
- Spread integration 0x418B70 (server calls it "spread integration 0x418b90"):
  `band = ((float)ps->0x354 - def->fHipSpreadStandMin) / (def->hipSpreadStandMax - min)`
  (0x418BBB), prone/ducked variants (0x418C04..), `if (ps->0x358 == 1)` branch
  at 0x418C66 -> 0x418DF7; at 0x418E28-0x418E4F the client itself clears
  `ps->0x358 = 0` once `band * aimSpreadScale` reaches the target (state 1 is a
  one-shot "max override").
- Other `+0x354` sites (0x40C7EB, 0x40C883, 0x421DCA, 0x444BDD, 0x469938,
  0x486C55, ...) are WeaponDef+0x354 (offhandClass) — traps.

**C1 server producers:** GSC method at 0x513080..0x51312D
(`setspreadoverride: spread must be > 0` / `< %d`): `ps->0x354 = value;
ps->0x358 = 2`. Method at 0x513130..0x5131D0 (`resetspreadoverride`):
`ps->0x358 = 1; ps->aimSpreadScale(0x34c) = const`. ClientSpawn path 0x50F861/
0x50F867 zeroes both.

**IW4/IW3 counterpart:** `playerState_t.spreadOverride` /
`spreadOverrideState` (IW4OL src/player.h:148-149, offsets 252/256),
written by PlayerCmd_SetSpreadOverride / PlayerCmd_ResetSpreadOverride
(registered: src/scr_vm_main.c:655-656). The server's C1 pmove port already
consumes them exactly like C1 (src/codol/player/codol_pmove_c1.c:168-209,
including the state-1 auto-clear at :208).

**Effect today:** `bin/home/codol_rawfiles/maps/mp/perks/_perkfunctions.gsc`
and `maps/_load.gsc` call `setSpreadOverride(1|2|20)` / `resetSpreadOverride()`.
The server integrates hip spread with the override (its BG_CalcSpread port and
hit registration) while the client draws the crosshair and predicts spread
without it -> bullets land tighter/wider than the crosshair shows for the
duration of the perk/scripted override, and on reset the client never runs
the state-1 convergence. Severity high (visible accuracy/crosshair mismatch
whenever the perk script fires).

**Implementation:** src/codol/snapshot/codol_engine_state.c
`CODOL_OverlayEngineAim` (:430) already puts 0x348/0x34c; add
`put(&out,0x354,(uint32_t)ps->spreadOverride)` and
`put(&out,0x358,(uint32_t)ps->spreadOverrideState)` with validation
`0 <= spreadOverride < 64` (6-bit field; the wire cannot carry a larger
value — reject with the same `return 0` pattern and log once) and
`spreadOverrideState <= 3`. Both are hint-0 DEF fields, so the delta base is
the history ring like every other DEF field; nothing else changes. Prerequisite:
none (PlayerCmd_SetSpreadOverride already writes the native fields).

### 1.2 [HIGH] ps+0x333c spawn time (idx 98, -97 TIME)

**Status:** BUILT-TESTED 2026-09-16: codol_ps_ext_t.spawn_time stamped in ClientSpawn (g_client_mp.cpp:229), published codol_engine_state.c:260-277, server gate CODOL_ApplySpawnWeaponGate codol_game.c:182 (sv_client.c:1221). 48+ bot spawns logged.

**C1 reader:** PM_Weapon_CheckForChange 0x41AFB0 (edx = pm, esi = ps;
pm->cmd at pm+4 so `[edx+4]` = cmd.serverTime, `[edx+0x18]` = cmd.weapon):
at 0x41B109-0x41B14B, when `cmd.weapon != ps->weapon`, the player is not on
a turret (`eFlags & 0xC00 == 0`) and `cmd.weapon == 0`, the switch to "no
weapon" is only begun if `cmd.serverTime - ps->0x333c > 200`; inside the 200 ms
window a `cmd.weapon==0` is ignored unless the current weapon is no longer
held (0x41B1C0 path via 0x40ABB0).
The client copies it from the received snapshot at CG transition 0x45D253
(`cg.predictedPlayerState+0x333c = snap->ps+0x333c`); that is not a producer.

**C1 server producer:** ClientSpawn tail 0x50F975-0x50F9AD: `ps->pm_flags |=
0x400 (PMF_RESPAWNED)`, ..., `client->0x70 = level.time`,
`ps->0x333c = level.time` (0x24B74C0 = level.time).

**IW4 counterpart:** none on the wire; IW4 relies on `PMF_RESPAWNED` +
`cg.spawnTime`. CoDOL added the explicit stamp so the first usercmds after a
spawn (still carrying the dead/spectating `weapon = 0`) cannot holster the
freshly given weapon.

**Effect today:** field is 0 -> `cmd.serverTime - 0 > 200` always -> the C1
prediction honours the stale `cmd.weapon==0` on spawn and begins a switch to
weapon 0; the next authoritative snapshot snaps it back. Visible as a
weapon-lower/raise flicker or a delayed first-raise right after (re)spawn and
after every server-side loadout swap that lands while cmd.weapon is 0. Severity
high (every spawn; likely the "weapon dips on spawn" symptom if observed live).

**Implementation:** stamp it where the server runs its ClientSpawn additions
(`CODOL_ResetClientInputCore`, src/codol/snapshot/codol_game.c:186-200, is
called from the ClientSpawn/gclient-memset sites) into a new
`codol_ps_ext_t` member (e.g. `spawn_time`, src/codol/snapshot/codol_playerstate_ext.h:422
struct) and publish it from codol_engine_state.c next to the other TIME
fields (`ES:337` commandTime / `ES:257` dive_end_time pattern:
`put(&out,0x333c,(uint32_t)ext->spawn_time)`). TIME (-97) encoding is
relative to serverTime (codol_delta.c), so it must be a level.time value, never
0. The server's own pmove port should apply the same 200 ms rule in its
weapon-change check (grep shows no such gate in codol_pmove_c1*.c) so
prediction and authority agree.

### 1.3 [MEDIUM] ps+0x3334 (idx 183, 3 bits) — dive direction slot, never written by C1

**C1 readers:** 0x406074 (BG, own ps -> per-client anim condition slot
`+0x92ce0`), 0x50D187 and 0x50D361 (C1 server module, builds clientState
0x0a8 / gclient+0x3510 from it). All three compute
`(pm_flags & 0x400000) && !(pm_flags & 0x800 FROZEN) && pm_time == 0 ? ps->0x3334 + 1 : 0`.
**No writer exists anywhere in C1.exe** (whole-image scan: only those three
reads), so its value is always 0 and the derived condition is 0/1.

**IW4 counterpart:** position and gating match IW4 `clientState_t.diveState`
(derived from `PMF_DIVING = 0x400000` in IW4 numbering); ps+0x3334 would be the
dive direction. The server names C1 pm_flags 0x400000
`C1_PMF_VIEWHEIGHT_SLOW` (codol_pmove_c1.c:53) from the 0x409225/0x409279
pm_time sites; CoDOL's dive-to-prone uses 0x40000000 instead. Both readings
agree that 0x3334 itself is dead.

**Effect today:** none from 0x3334 (0 is what C1 would send). The live part is
clientState 0x0a8 (see 3.3). Severity medium only through 3.3; publishing
ps+0x3334 stays "always 0" — no work.

### 1.4 [LOW] ps+0x0060 (idx 192, -97 TIME) — no playerState reader (trap)

Audit site 0x47A793 `cmp byte [eax+0x60],0` sits in a copy loop
(0x47A721-0x47A7BA) that moves floats at +0x3c..+0x6c of a definition struct
into cg+0xB0400.. (a shellshock/vision-style parameter block: byte +0x60 gates
+0x64/+0x68 defaults of 1.0). Not a playerState. The remaining 30 `+0x60`
accesses in bg/cg whose base is not WeaponDef/centity are DObj/trace/
usercmd structs (0x40D138, 0x413B96.., 0x441160, 0x4530D5..). No ps+0x60
consumer -> nothing to publish. C1's own server never sends it either (no
writer found). Keep 0.

### 1.5 [LOW] ps+0x0218 (idx 195, 32 bits) — no playerState reader (trap)

Audit site 0x48FCA2 tests bytes `+0x218`/`+0x219` of a struct the client
itself writes (`mov byte [esi+0x219],0` at 0x48FCBD; siblings +0x4c, +0xb0,
+0xc4 bytes; function 0x48F7D0 helpers) — an input/UI state block, not ps.
Other `+0x218` sites are centity (`^0x189bfead`, 0x443AFB/0x450142) and
DObj/scene structs. No ps consumer; keep 0.

### 1.6 [LOW] ps+0x0350 (idx 234, 32 bits, hint 1) — no playerState reader (trap)

0x41A9D6 switches on `[arg1+0x350]` (1..6) against `ps->hand[i].shotCount`
(0x280 + i*0x1C): arg1 is the **WeaponDef** and +0x350 is `fireType`
(single 1, burst2/3/4 = 2/3/4, double-barrel 5, spin-up 6; jump table
0x41AA4C = {0x41A9E9,0x41AA04,0x41AA1B,0x41AA32,0x41A9E9,0x41AA00}), exactly
what src/codol/weapon/codol_weapon_native.c:466 harvests. 0x415FA5 and
0x41BB41 `cmp [WeaponDef+0x350],5` are the same field. alpha0022 ERRORS.md
already recorded "no reader anywhere". Keep unsent (the only hint-1 field; C1
reads it like hint 0, so sending 0 would be harmless but pointless).

### 1.7 [LOW] ps+0x053c / ps+0x0540 (idx 235/236, 10 bits) — no playerState reader (trap)

0x4568D6 `cmp [eax+0x540],0` / `[eax+0x544]` / `[eax+0x548]` / `[eax+0x54c]`:
eax = `[weapon*4 + 0x150D710]` = WeaponDef; +0x540 is `altWeaponIndex`
(src/codol/weapon/codol_weapon_state.h:64) and +0x544.. its neighbours, used by
the weapon HUD ownerdraw 0x456700.. to decide whether an alt-mode icon is
drawn. ps+0x53c/0x540 (in front of the action-slot types 0x544-0x554) have no
reader; keep 0.

---

## 2. playerState bit fields

### 2.1 [HIGH] ps+0x14 linkFlags bit 0x1 (idx 167, 3 bits) — PLF_ANGLES_LOCKED

**Status:** BUILT-TESTED 2026-09-16: anglesLocked in codolPlayerLink_t/codol_ps_links_t, playerlinktoabsolute + playerlinktodelta registered (codol_script_startup_extra.c:1080), wire codol_player_links_wire.c:50-55, PM pitch-clamp bypass codol_pmove_c1.c. playerLinkToBlend not registered (needs the blend). Needs a human ride to verify live.

**C1 reader:** PM_UpdateViewAngles 0x4141A0: when `pm_type == 1
(NORMAL_LINKED) || pm_type == 9 (DEAD_LINKED)` and `linkFlags & 1`, local
`locked = 1` (0x4141B8); at 0x414209-0x414216 a set flag bypasses the
free-look pitch clamp that otherwise rewrites `delta_angles[0]`
(0x41423F/0x414266), i.e. the view is driven by the link frame, not by the
usercmd pitch.

**C1 server producers:** link methods at 0x53B2E0.. (`or [ps+0x14],1` at
0x53B37A together with `gclient+0x3768 = 1.0` (viewRotationFraction),
`gclient+0x36e4 |= 4`, `and [ps+0x14],~4` — forces full view rotation and
clears the weapon-view bit: the PlayerLinkToAbsolute shape) and 0x53BA40..
(`or [ps+0x14],1` at 0x53BAD6 after `gclient+0x3764=0, +0x3765=1,
+0x3767=1`). Cleared at 0x53A8FA (unlink) and 0x53B0BF. 0x53BC6B tests it and
errors with `"Angle locked to linked entity.  View clamp is 0."` when a
view-clamp method is used while locked — confirming the IW4 name.

**IW4 counterpart:** `PLF_ANGLES_LOCKED 0x1` (with `PLF_USES_OFFSET 0x2`,
`PLF_WEAPONVIEW_ONLY 0x4`), set by PlayerCmd_PlayerLinkToAbsolute /
angle-locked PlayerLinkTo variants; PM_UpdateViewAngles skips cmd-driven
angles when set.

**Effect today:** src/codol/snapshot/codol_player_links_wire.c:50-52 writes
only 0x2 (offsetEnabled) and 0x4 (mode == weapon-view). 53 GSC files under
bin/home/codol_rawfiles call playerLinkTo* (heli ride, killstreak rides,
_debug, dog combat...). For any absolute/angle-locked link the C1 client keeps
clamping pitch against its own delta_angles while the server rotates the view
with the link -> jittery or wrongly clamped look while riding, and the C1
server-side "View clamp is 0" contract is not reproduced. Severity high.

**Implementation:** extend `codol_ps_links_t` (src/codol/snapshot/codol_player_links.h:6)
with `anglesLocked`, capture it in `CODOL_CaptureClientPlayerLinks` from the
script record (`codolPlayerLink_t`, src/codol/script/codol_script_startup_extra.h:36-60:
set when the link method is the absolute variant or when all four arcs are 0
and viewRotationFraction == 1.0, mirroring 0x53B37A), and in
`CODOL_OverlayPlayerLinks` change `linkFlags &= ~0x6` to `~0x7` and OR 0x1.
Prerequisite: a PlayerLinkToAbsolute method (grep finds none registered;
`CODOL_PlayerCmd_PlayerLinkTo` exists) — add it in codol_script_startup_extra
with the same record, `mode` = absolute. The pmove consumer
`CODOL_PlayerLinkClampView` must skip the pitch clamp when locked, like
0x414216.

### 2.2 [MEDIUM] ps+0x344 weapFlags bit 0x100000 — disable weapon pickup

**Status:** BUILT-TESTED 2026-09-16: disableweaponpickup/enableweaponpickup registered (scr_vm_main.c:1163), CODOL_WEAP_PICKUP_DISABLED 0x100000 published (codol_engine_state.c:920), Touch_Item weapon path gated (_g_items.asm Touch_Item_150).

**C1 reader:** CG weapon-pickup hint 0x481105-0x48113B: hint is built only
when `cg+0xC8B60 == 0 && 0x480F10() && pm_type < 8 && !(weapFlags & 0x100000)`.
**C1 server producers:** GSC methods 0x5145C3 (`or [ps+0x344],0x100000`) /
0x5145DC (`and ~0x100000`) = disableWeaponPickup / enableWeaponPickup.
**IW4:** PlayerCmd_DisableWeaponPickup / EnableWeaponPickup on
`ps.weapFlags` (PWF_DISABLE_WEAPON_PICKUP), consumed by CG_WeaponPickupHint
and by G_Touch_Item server-side.
**Effect today:** no file in bin/home/codol_rawfiles calls either method and
the server registers neither (grep), so nothing is lost yet; once IW4/IW5
scripts that use them are ported (laststand, some killstreak rides) the
"press F to swap" hint would appear while the server refuses the pickup.
**Implementation:** add `disable_weapon_pickup` to `codol_ps_ext_t`, register
the two methods (src/codol/script/codol_script_player_builtins.c), OR the bit
in `CODOL_OverlayEngineWeaponUseControl` (codol_engine_state.c:859, widen the
0x9d mask to include 0x100000), and gate the server's item touch on it. The
21-bit field already carries it.

### 2.3 [LOW] ps+0x344 weapFlags bit 0x10000 — weapon taken, awaiting switch

**C1:** set only by the C1 server module 0x5110C7 (take-weapon method: when
the taken weapon is the held one and the "switch" argument is set, `ps->weapon
= 0; ps->weapFlags |= 0x10000`, 0x5110B7-0x5110C7); cleared client-side in
PM weapon-state reset 0x41A0C0. No test site in the image (checked plain,
shifted and `bt` forms) -> it only survives until the next weapon change and
has no consumer. **IW4:** no networked equivalent (IW4 TakeWeapon switches
server-side). **Effect:** none. Optional: set it in the takeWeapon path
(codol_script_player_builtins.c) for wire parity; no priority.

### 2.4 [LOW] ps+0x344 weapFlags bit 0x200 — double-barrel dual trigger

**C1:** tested at 0x422407 (BG view-kick: multiplies the kick by the extra
factor when set); cleared at 0x41BB4A/0x41BB9E when the held WeaponDef
`fireType == 5` (double barrel) and in PM. No setter in the image (set through
a computed mask or only by C1's own pmove for fireType 5/6 weapons).
**IW4:** `PWF_TRIGGER_DOUBLE_FIRE 0x200` (akimbo/double-barrel both-trigger
fire), pmove-managed on both sides. **Effect:** none unless a CoDOL weapon with
fireType 5/6 is used; the server pmove port would have to set it for parity
(codol_pmove_c1.c weapon fire path). Low.

---

## 3. clientState (77 fields, table 0xC38890; copied per client in CG_ProcessSnapshot 0x46C8DC..)

C1's own server fills the per-client record at 0x50D0F0 (called from 0x50D1C0
with eax = ps, ecx = ci-like record 0x241CB84 + client*0xB50):
`+0xB14 = (ps->dualWield(0x35c) == 1)`, `+0xB18 = diveState (see 1.3)`,
`+0xB1C = (ps->weapFlags >> 12) & 1`, and the wire fields 0x018/0x0a8/0x01c
land back in `ci+0xB14/0xB18/0xB1C` on the client (0x46CBAA/0x46CA18/0x46CA24).
BG 0x407184-0x4071B7 copies those three into the third-person animation
condition slots (`+0x92cd8`, `+0x92ce0`, `+0x92ce8` of the per-client anim
state), the same slots the local player fills from its own ps at
0x406007-0x406094. IW4 `clientState_t` order confirms the names:
`team, modelindex, dualWielding, riotShieldNext, attachModel[6], attachTag[6],
name, maxSprintTimeMultiplier, rank, prestige, perks, diveState,
voiceConnectivityBits, playerCardIcon/Title/Nameplate`.

### 3.1 [MEDIUM] 0x018 dualWielding (1 bit) -> ci+0xB14

**Status:** BUILT-TESTED 2026-09-16: codol_client_assets_t.dual_wield from the live ps (codol_sv_assets.c CODOL_OverlayServerClient), put at 0x018 (codol_engine_state.c:1090). Third-person anim check needs a human.

**Reader:** BG 0x407184 -> anim condition slot `+0x92cd8` (the "akimbo"
condition, src/codol/player/codol_animation_conditions.inc:57 / tables.c:153),
0x46CBA2 dirty check. **IW4:** `clientState_t.dualWielding =
ps->weapFlags/dualWield` from G_UpdateClientState. **Effect:** other players
holding akimbo weapons animate with single-gun third-person anims (the local
player is fine — its slot comes from its own ps 0x35c which ES:824 publishes).
**Implementation:** `CODOL_OverlayEngineClient` (codol_engine_state.c:1014):
`put_client(&out,0x018, dual_wield ? 1 : 0)` using the same `dual_wield`
predicate as ES:823 (needs the recipient-independent per-client value: derive
from that client's live playerState, as the model/attachments already do).

### 3.2 [MEDIUM] 0x01c riotShieldNext (1 bit) -> ci+0xB1C

**Status:** BUILT-TESTED 2026-09-16: native CODOL_WEAP_RIOTSHIELD_NEXT set in select_weapon from def+0x340==3 (codol_weapon_state.c), wire bit 0x1000 + clientState 0x01c. Needs a shield-class weapon and a human.

**Reader:** BG 0x407197 -> anim condition slot `+0x92ce8`. Source bit:
weapFlags 0x1000, which C1's PM sets at 0x41979A when the incoming
weapon's `[edi+0x340] == 3` (the alt-mode/class selector; 0x4197A6 clears)
and 0x41DB67 clears. **IW4:** `clientState_t.riotShieldNext =
(ps->weapFlags & PWF_SWITCHING_TO_RIOTSHIELD) != 0`. **Effect:** shield
third-person stance not selected for other players while switching to a
riot shield; no effect for weapons without a shield class. **Implementation:**
publish `((weapFlags_wire >> 12) & 1)` at 0x01c in `CODOL_OverlayEngineClient`
once the server pmove sets C1 bit 0x1000 on shield switch (it does not today:
ES:882 maps native 0x1000 to 0xE0000, a different meaning). Prerequisite: a
shield-class weapon in the composed set.

### 3.3 [MEDIUM] 0x0a8 diveState (4 bits) -> ci+0xB18

**Status:** BUILT-TESTED 2026-09-16: C1 0x50d16a formula on the C1-numbered pm_flags, put at 0x0a8. Needs a human dive.

**Reader:** BG 0x4071AA -> anim condition slot `+0x92ce0` (dive animation
selector). **Producer rule (C1 server 0x50D16A-0x50D18E):**
`(pm_flags & 0x400000) && !(pm_flags & 0x800) && pm_time == 0 ? ps->0x3334 + 1 : 0`
(= 1 in practice, 1.3). **IW4:** `clientState_t.diveState`. **Effect:** other
players never get the dive-state anim condition while the server's
`C1_PMF_VIEWHEIGHT_SLOW`/0x400000 window is active; harmless until the server
produces pm_flags 0x400000 (codol_pmove_c1 currently only reads it).
**Implementation:** in `CODOL_OverlayEngineClient` put
`(ps->pm_flags & 0x400000) && !(ps->pm_flags & 0x800) && ps->pm_time == 0 ? 1 : 0`
at 0x0a8. Keep in step with 1.3.

### 3.4 [MEDIUM] 0x008 / 0x00c (32+32 bits) -> ci+0x54..0x5b: 64-bit party/group id

**Status:** SKIPPED 2026-09-16 (lobby plumbing).

**Reader:** 0x45C080 `CG_ClientsShareGroup(a,b)`: returns 1 when
`ci[a].+0x54:+0x58` is nonzero and equals `ci[b].+0x54:+0x58` (b = the local
`ps->clientNum` record). Callers 0x4342B9 and 0x43E2F9 are compass/name-plate
colour selection (CG ownerdraw range). **IW4:** no wire equivalent (party
membership is Live-side); CoDOL puts the lobby party/squad id on the wire so
squad mates get their own HUD colour. **Effect:** party-mate highlighting on
the compass/nameplates never shows. **Implementation:** the lobby already
knows the party (createSession desc / lobby SQLite); carry the 64-bit id into
the client's `codol_client_appearance_t` (codol_clients.c:12
`CODOL_OverlayClientAppearance`) and `put_client` low/high words at
0x008/0x00c. 0 = no party (C1 treats 0 as "never matches").

### 3.5 [LOW] 0x134 (8 bits) -> ci+0xB4C: player colour/index selector

**Status:** PUBLISHED 0 explicitly 2026-09-16 (codol_engine_state.c:1090); no C1 server producer identified yet.

**Readers:** 0x460452 inside 0x4603D0 (per-client colour: `if ci->0xB4C == 0`
-> white 1,1,1 else a table colour; called from 0x4607A9/0x4607CA/0x461F4A —
name/marker colour), 0x484E34 (`self ? ci->0xB4C : ci->0xB48` feeding a
per-entity draw). **IW4:** none (CoDOL-specific; nearest is the clan-tag /
faction colour). **Effect:** names/markers draw in the default colour. Low
until the lobby exposes the value it should carry.

### 3.6 [LOW] 0x12c / 0x130 (11 bits) -> ci+0xAF4 / 0xAF8; 0x010 (3 bits) -> ci+0x5C

**Status:** BUILT-TESTED 2026-09-16: 0x12c = remote-driver ownerNum-1 or ET_VEHICLE tag parent (codol_sv_assets.c); 0x130/0x010 untouched.

**0x12c:** readers 0x44C15F, 0x48262B, 0x4851EC: for an ET_PLAYER cent, if
`ci->0xAF4 != 0` the code re-targets to `cg_entities[ci->0xAF4]` and looks up
the vehicle record (`word[0x25D9ED8 + number*2] * 0xC8`) — a vehicle entity
number used to place/animate the rider from the vehicle; the published 0x0bc
attachedVehEntNum (ci+0xB38, reader 0x44E6F2) is the seat link. **0x130:** no
reader in bg/cg. **0x010:** no reader beyond the copy (0x46C95E). **Effect:**
riders of scripted vehicles may be drawn from their own origin instead of the
vehicle's; CoDOL MP vehicles are killstreak-only (already published via 0x0bc).
Low. Implementation when needed: publish the vehicle entity number at 0x12c
from the same link record as 0x0bc (ES:1028).

---

## 4. How to verify (high items)

### 4.1 spreadOverride (1.1)
- Log: in `CODOL_OverlayEngineAim` print once per transition
  `CoDOL spread wire: client %u override %d state %d aimSpreadScale %.2f`.
- Client: with `_perkfunctions.gsc` calling `setSpreadOverride(20)` the hip
  crosshair opens to a fixed gap and stays fixed while moving (state 2), then
  after `resetSpreadOverride()` converges over ~0.5 s (state 1 -> client clears
  to 0). Server log must show the state flip 2 -> 1 -> (client-cleared; the
  server's pmove_c1.c:208 clear shows as state 0 next frame).

### 4.2 PLF_ANGLES_LOCKED (2.1)
- Log: in `CODOL_OverlayPlayerLinks` print `CoDOL link wire: client %u flags
  0x%x mode %u locked %u` on change.
- Client: `maps/_heli_ride.gsc` or the ac130 ride — while linked with the
  absolute variant, looking straight up/down must not fight the ride (no pitch
  snap-back), and a subsequent `playerSetViewClamp`-style call must be refused
  server-side with the C1 message. Bit 0x1 visible in the log during the ride
  and cleared on unlink.

### 4.3 spawn time (1.2)
- Log: in the spawn hook print `CoDOL spawn wire: client %u spawnTime %d` and
  in the usercmd path count `cmd.weapon==0` commands within 200 ms of it
  (`CoDOL spawn gate: client %u ignored stale weapon 0 (%d ms)`).
- Client: respawn repeatedly; the weapon must be raised once without a
  lower/raise flicker, and the gate counter must be > 0 on spawns where the
  previous state was dead/spectating (proving the client would have switched
  to 0 before). A TIME field must be within ±8 s of serverTime or the -97
  codec falls back to the 32-bit arm — check the delta log stays on the 8-bit
  arm right after spawn.
