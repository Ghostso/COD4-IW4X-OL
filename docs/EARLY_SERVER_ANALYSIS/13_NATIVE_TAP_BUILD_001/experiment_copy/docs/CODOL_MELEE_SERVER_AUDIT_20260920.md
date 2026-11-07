# Server-side melee audit for zm — 2026-09-20

Scope: audit only. No file outside `docs/` was modified, nothing was built,
committed, started or stopped. Every claim is labelled **MEASURED** (read out of
shipped data, source, or a log on disk) or **INFERRED**.

Brief: ground truth is that on the vanilla CoDOL server every weapon plays a
melee animation in zombies, and on ours roughly 22 of the 40 roster weapons play
none (user-confirmed silent: `coltanaconda_zm`, `m14ebr_zm`). The previous
investigation (`docs/CODOL_MELEE_ANIM_20260920.md`) closed this as "shipped
content gap, server cannot fix". This audit re-opens it from the server side.

---

## 0. Answers first

1. **The mp/zm ".44 magnum" experiment does not isolate a server path, because
   it is not the same weapon.** `coltanaconda_mp` and `coltanaconda_zm` are two
   different type-28 assets in two different zones. MEASURED with
   `tools/codol_weapondef_zone_diff.py dump`:

   | asset | zone | `+0x098` (anim slot 7 = melee) | `+0x09c` (slot 8 = melee charge) |
   |---|---|---|---|
   | `coltanaconda_mp` | `common_gametype_mp` | `0x300f55bc` | `0x300f6d5a` |
   | `coltanaconda_zm` | `common_gametype_zm` | `0x3007f4b7` (pooled empty) | `0x3007f4b7` |
   | `m14ebr_zm` | `common_gametype_zm` | `0x3007f4b7` | `0x3007f4b7` |
   | `p90_zm` | `common_gametype_zm` | `0x30205ddd` | `0x3020757a` |

   Every other server-side input to melee is category-independent (§4). So the
   sharpest experiment returns "the data differs", not "the server differs" —
   which is exactly why it cannot, on its own, exonerate the server: it only
   says the *held weapon's* animation name is absent in zm.

2. **The composed-vs-bare theory is dead for zm, and the 18/22 coincidence is a
   different 18/22.** MEASURED: the zm session log publishes **zero** composed
   (`*a …`) names, and by construction it cannot publish any (§2). The real
   18/22 split is the animation-slot-7 split, and it matches the runtime warning
   list one-for-one (§2.3, Appendix A).

3. **Our loader's "animation slot 7 is empty" warning changes nothing.** It is a
   pure `Com_PrintWarning`. No degradation, no suppressed event, no zeroed
   field (§3.1).

4. **The zm weapon window is published complete: 131 of 131, no truncation.**
   MEASURED, `bin/home/main/qconsole.log.old:150`. `zombie_melee`,
   `hatchet_zm`, `revive_knife_zm`, `throwingknife_zm`, `zombie_knuckle_crack`
   and `zombie_bowie_flourish` **are all published**. The
   `knife_ballistic_*` family is **not** in the vanilla zm window at all (§5).
   54 is not a cap and is not a zm number — it is the **mp** window's
   truncation in the *current* log (§6).

5. **Our zm GSC never gives the player a melee weapon, and T5's does.**
   MEASURED in the vendor tree: T5 gives every zombies player `knife_zm` at
   spawn and swaps it for `bowie_knife_zm` on the Bowie purchase, tracked
   through a `current_melee_weapon` subsystem that we did not port at all
   (§7). Our `giveStartingLoadout()` gives one pistol and nothing else.

6. **The `defaultweapon_mp` fallback is not an mp leak, and the unsuffixed
   `defaultweapon` would be the wrong substitute** (§8).

Ranked candidate root causes are in §9.

---

## 1. How a weapon name reaches the client (docs summary)

From `CODOL_WEAPON_PUBLICATION.md`, `CODOL_SERVER_WEAPON_CONFIGSTRINGS.md`,
`CODOL_WEAPON_REGISTRY.md`, `CODOL_WEAPON_COMPOSER_CACHE_20260914.md`,
`CODOL_NATIVE_WEAPON_MAPPING.md`, cross-checked against
`src/codol/weapon/codol_sv_weapons.c`:

1. **Weapons reach the client as NAMES ONLY.** The client builds
   `bg_weaponDefs[i]` from *its own* zone copy of the named type-28 asset.
   Nothing the server puts in the playerstate can supply an asset field.
2. `CODOL_InitializeServerWeaponConfigstrings(zone_type)` runs at map start
   (`codol_sv_weapons.c:482`). It registers implicit `none` (slot 0) and
   `defaultweapon_mp` (slot 1), then:
   * **mp** walks `mp/coWeaponAttachmentTable.csv` as an ordered list;
   * **coop/zm** walk the category's own *constant* configstring table by slot
     (`collect_weapon_window`, `codol_sv_weapons.c:445`), because that constant
     table **is** the slot map the client registers from.
3. Each name is probed against a scratch registry. The first name that will not
   register **truncates** the window (`*stopped_name`, `count=i`), and the
   truncation is reported as a `CoDOL weapon window (…): published N of the M
   its constants demand; truncated at slot S by '<name>'` warning.
4. The surviving prefix is written to `CS 5362+i`, the tail is **blanked**
   (empty strings, not left inherited), and `CS 6517` is set to our own count —
   never the constants' count, because C1's `CG_Init` loop at `0x47d1d0`
   dereferences `bg_weaponDefs[i]` with no NULL check.
5. After map start, `CODOL_RefreshServerWeaponMappings` appends any weapon the
   native registry loaded that the bank does not hold (script `precacheItem`,
   `giveWeapon`, composed `*a` publication), recursively registering `+0xb78`
   and `+0xb88` partners, and sends primed clients `d <cs> <name>` reliable
   commands in ascending slot order.
6. `CODOL_PublishComposedWeapon` is the only path that can emit a `*a <base>
   <item> …` name. The client then runs `BG_BuildCustomWeaponDef` (`0x4216C4`),
   which memcpy's the 0xBFC base def and applies type-43 `weaponattach`
   override records to the copy.

---

## 2. Item 2 — the composed/bare decision, and why it does not apply to zm

### 2.1 Where the decision is made

The `*a` name is produced by exactly two loadout bridges, both of which take a
**marketplace class profile** (a base item ordinal plus attachment item
ordinals) as input:

* `CODOL_Scr_GetLoadoutWeapon` — `src/codol/script/codol_script_profile_loadout.c:823`
* `codol_bot_loadout.c:223` (bot CSV bridge)

Both call `CODOL_ComposeLoadoutWeaponRecipe` and then degrade to the **bare
stock base name** on any of four conditions
(`codol_script_profile_loadout.c:849/866/878/897`):

| condition | message |
|---|---|
| no complete composed art | `%s has no complete composed art; using stock base` |
| a declared attachment group left empty *and* the weapon's own C1 tables could fill it | `%s leaves %u declared group(s) empty; using stock %s` |
| part overflow | `%s overflowed by %u part(s); using stock %s` |
| construction/publication failure | `cannot build %s (%s); using stock %s` |

`codol_weapon_compose.c` itself contains **no** composed-vs-bare decision: it
parses/canonicalises the name, resolves the marketplace ordinals, scores the
component-model row, applies the attachments and owns the composed-entry cache.
The choice is entirely upstream, in the loadout bridges.

### 2.2 Why zm never composes

MEASURED, `bin/home/codol_rawfiles/zm/**`: the zm script tree never calls the
loadout bridge. Weapons are handed out by **literal name**:

* `_zombiemode.gsc:632` `self giveWeapon( level.zombie_start_weapon );`
* `_zombiemode_weapons.gsc:346` `self giveWeapon( weapon_name );` (box / wall buy)
* `_zombiemode_perks.gsc:377/560/648`, `_zombiemode_laststand.gsc:214/236`

`level.zombie_weapons[]` is built by 40 literal `add_zombie_weapon(...)` calls
(`_zombiemode_weapons.gsc:113-172`). There is no marketplace ordinal anywhere in
the zm tree, therefore no recipe, therefore no `*a` name. This agrees with the
parent's log measurement (zero `*a` publications in the zm session).

It is also structurally impossible for the composed channel to help in zm even
if it were wired: MEASURED from `docs/zone_assets/ALL_weaponattach.txt`, the
**only** zones that carry type-43 `weaponattach` assets are
`common_gametype_mp` (225), `patch_common_gametype_mp` (51) and
`code_post_gfx_default_mp` (1, named `null`). **No zm zone ships a single
weaponattach record**, so `BG_BuildCustomWeaponDef` would memcpy the base def
and apply nothing. Under the user's "no `_mp` asset in a zm match" constraint
the mp records are off the table regardless.

### 2.3 The real 18/22 — animation slot 7, not composition

Keeping the two lists as the brief asked, but re-labelled to what they actually
are. Effective definition after patch/map override, over the 40 base names our
`_zombiemode_weapons.gsc` roster hands out.

**Slot 7 EMPTY — no melee animation (22):**
`coltanaconda_zm`, `glock_zm`, `uzi_zm`, `tmp_zm`, `striker_zm`,
**`m14ebr_zm`**, `m16_zm`, `famas_zm`, `fal_zm`, `ak104_zm`, `tavor_zm`,
`m4a1tech_zm`, `cheytac_zm`, `wa2000_zm`, `sniper_explosive_zm`, `l86_zm`,
`crossbow_explosive_zm`, `ray_gun_zm`, `tesla_gun_zm`, `thundergun_zm`,
`frag_grenade_zm`, `claymore_zm`.

**Slot 7 POPULATED — melee animation present (18):**
`m1911_zm`, `glockdw_zm`, `mp5k_zm`, `p90_zm`, `pp2000_zm`, `spas12_zm`,
`model1887_zm`, `ranger_zm`, `aug_eotech_zm`, `scar_h_eotech_zm`, `as50_zm`,
`m79_zm`, `at4_zm`, `knife_ballistic_zm`, `knife_ballistic_bowie_zm`,
`semtex_grenade_zm`, `bouncingbetty_zm`, `c4_zm`.

Upgraded variants follow their base in every case.

**Both user-confirmed silent weapons are in the empty list**, and the list
matches the 39 runtime warnings in `bin/home/main/qconsole.log.old` exactly
(Appendix A). **This 18/22 is not the composed/bare 18/22 the brief suspected;
there is no composed 18 in a zm match.** The coincidence is that the same two
numbers fall out of a completely different partition.

---

## 3. Item 3 — the four suspect files

### 3.1 `src/codol/weapon/codol_weapon_loader.c` — the warning (added scope)

Emit site: `codol_weapon_loader.c:161-172`, inside `CODOL_LoadEngineWeaponCore`.

```c
if(source.asset.size>=0xbfc) {
    const uint8_t *melee=source.asset.data+0x590;
    unsigned damage= …;
    if(damage && damage<=0x7fffffffu && (!animations.names[7] || !*animations.names[7]))
        Com_PrintWarning(CON_CHANNEL_SYSTEM,
            "CoDOL weapon %s: melee damage %u but animation slot 7 is empty; …");
}
```

**It is a `Com_PrintWarning` and nothing else.** No `core_fail()`, no early
return, no field write, no flag, and no caller reads any state it sets — the
whole block is inside an `if` whose only statement is the print. Control flow
continues into the hide-tag load exactly as if the block were deleted. Tripping
the warning has **zero** behavioural consequence for the weapon.

The premise in its comment ("the server has no channel to close it") is
accurate as far as the composed-name channel goes (§2.2), but the comment also
asserts this is not a server defect, which §5/§7 dispute.

### 3.2 `src/codol/weapon/codol_knife_attachment.c` / `.h`

**What it does:** the *ballistic-knife projectile* lifecycle — a thrown knife
entity (`ET_MISSILE`) that sticks into the world or into a body, links to a
ragdoll bone (`bone()` maps `HITLOC_*` to `j_head`/`j_spineupper`/… via T5's
`MapHitLocationToRagdollBoneName` cases), goes `TR_STATIONARY`, and stays
retrievable by the knife-pickup path.

**Gating:** `knife()` (`:49`) accepts an entity only when
`e->s.eType == ET_MISSILE` and `CODOL_IsKnifeDefinition(BG_GetWeaponDef(w))`.
There is **no category gate** — nothing tests `zm`/`mp`/`coop`, and nothing
tests composed-vs-bare.

**Dead code:** none. All seven exported entry points are called:
`CODOL_RunAttachedKnife` from `src/asmsource/_g_missile.asm:3519-3522`,
`CODOL_KnifePlayerSpawning` from `src/g_client_mp.cpp:66`,
`CODOL_ResetKnifeAttachments` from
`src/codol/snapshot/codol_sv_entity_events.c:45`, the impact pair and the
corpse/reset pair from the knife-pickup and damage paths.

**Relevance to the reported bug: none.** This is the *thrown* knife, not the
melee swing. In a zm match it can only be reached if a player is carrying
`knife_ballistic_zm`, which our roster only offers from the mystery box.

### 3.3 `src/codol/weapon/codol_melee_debug.c`

**What it does:** diagnostics around the retained melee trace
(`FireWeaponMelee` → `Weapon_Melee_internal` → `Melee_Trace`). It records
attempt/hit/damage counters and, when `codol_meleeDebug` is set, prints the
attacker, the weapon and its `iMeleeDamage / iMeleeDelay / iMeleeTime /
meleeChargeDelay / meleeChargeTime`, the trace volume and the closest reachable
enemy.

**Gating:** the printing is behind `melee_verbose()` (`codol_meleeDebug->boolean`).
Counter bookkeeping runs unconditionally. **No category gate, no weapon gate.**

**Dead code:** none — `CODOL_MeleeDebugFire`/`Trace`/`Damage` are called from
`src/asmsource/_g_weapon.asm:873-887` and `:468-483`.

**Relevance:** it is the right instrument to prove whether the melee *action*
runs in zm (it would count `attempts` per swing). It cannot affect the
animation. It was not enabled in the captured zm session.

### 3.4 `src/codol/weapon/codol_weapon_attachment.c` / `.h`

**What it does:** reads a type-43 `weaponattach` asset into
`{offset, type, value, text}` records and applies them to an owned copy of a
serialized weapon image (`CODOL_ReadWeaponAttachment`,
`CODOL_ApplyWeaponAttachments`). This is the server-side mirror of C1's
`BG_BuildCustomWeaponDef` override application — **the only mechanism in the
whole server that can write a new animation name into `def+0x098`**.

**Gating:** none by category. It is called from
`codol_weapon_compose.c:apply_attachments` (composed weapons),
`codol_script/codol_loadout_fastmag.c:104-111`,
`codol_player/codol_pmove_c1_breath.c:162-176` and
`codol_player/codol_sway_phase.c:195-221`.

**Effectively dead in zm, for a data reason, not a code reason:** every caller
resolves an attachment asset name through `CODOL_ComposedAttachmentAssetName`,
and no zm zone ships a weaponattach asset (§2.2). In a zm match this module
loads nothing and applies nothing.

---

## 4. Item 4 — every server-side melee path, and which zm reaches

| path | file | category gate? | reached in zm? |
|---|---|---|---|
| melee event IDs `EV_MELEE_SWIPE→47`, `EV_FIRE_MELEE→48`, `EV_MELEE_HIT/MISS/BLOOD→52/53/54` | `src/codol/snapshot/codol_event_map.inc:51-62` | none | yes |
| melee event **parameters** (both forced to literal 0, per C1 `0x41c02c` / `0x41bcfc`) | `codol_events.c:144-155` | none | yes |
| melee damage/timing fields from the shipped def (`+0x590`, `+0x5a0`, `+0x5a4`, `+0x5c0`, `+0x5c4` → `iMeleeDamage`, `iMeleeDelay`, `meleeChargeDelay`, `iMeleeTime`, `meleeChargeTime`) | `codol_weapon_native.c:548-560` | none | yes |
| melee charge (lunge) C1 port, `PMF_MELEE_CHARGE 0x00010000` | `codol_melee_charge_c1.c` via `_bg_pmove.asm:355-357` | none | yes |
| usercmd `meleeChargeYaw` / `meleeChargeDist` decode | `codol_usercmd.c:65-66` | none | yes |
| melee as a **player-wide weapon phase** (states 12..14) driving both hands, `set_animation(hand, ps->weapAnim & 0x1f)` | `codol_weapon_state.c:851-855`, `:1871-1893` | none | yes |
| second-hand melee veto (C1 `0x41c070`) | `codol_weapon_state.c:2204` | none | yes |
| server melee trace/damage | `_g_weapon.asm` `FireWeaponMelee`/`Weapon_Melee_internal`, dispatched from `_g_active_mp.asm:2440` | none | yes |
| actor (zombie) melee | `_codol_actor_melee.asm` → `Weapon_Melee_internal`; `codol_actor_lifecycle.cpp:1295 ActorMelee` | AI only | yes (zombies) |
| riot-shield melee kill icon | `codol_obituary.c:55` | none | n/a |
| thrown-knife projectile stick | `codol_knife_attachment.c` | none | only with a ballistic knife |
| melee diagnostics | `codol_melee_debug.c` | `codol_meleeDebug` dvar | yes, silent by default |

**Nothing on this list is gated on category, on composed-vs-bare, or on the
animation-slot-7 warning.** `MELEE`/`melee`/`knife` appears nowhere in
`codol_weapon_give.c`, and `altmelee` / `altMeleeWeapon` / `meleeWeapon`
appear **nowhere in `src/` at all** (zero hits).

---

## 5. Item 5 — does the server publish a melee weapon?

### 5.1 The zm window is complete

MEASURED, `bin/home/main/qconsole.log.old:150`:

```
CoDOL weapon window (zm): published 131 definitions, CS 6517 = 131 (constants demand 131)
```

No truncation warning, so `collect_weapon_window` walked all 130 constant slots
and every one registered. The **only** weapon that failed to resolve in that
session was `thundergun_zm` ("not in any mounted zone; using defaultweapon_mp"),
and that is correct for `zm_asylum_sh` — MEASURED, `thundergun_zm` ships only in
`zm_prototype_sh`.

### 5.2 Which melee-shaped weapons are published

Cross-referencing the measured zm constant window
(`docs/CODOL_CATEGORY_WEAPON_WINDOW_20260917.md` §1.2) with the zone's
melee-shaped assets (`docs/zone_assets/ALL_weapon.txt`):

| weapon | in `common_gametype_zm`? | in the 131-slot zm window? | published by us? |
|---|---|---|---|
| `zombie_melee` | yes | **yes, index 45** | **yes** |
| `hatchet_zm` | yes | **yes, index 6** | **yes** |
| `throwingknife_zm` | yes | **yes, index 5** | **yes** |
| `revive_knife_zm` | yes | **yes, index 8** | **yes** |
| `zombie_knuckle_crack` | yes | **yes, index 113** | **yes** |
| `zombie_bowie_flourish` | yes | **yes, index 122** | **yes** |
| `knife_ballistic_zm` | yes | **no** | only if something registers it |
| `knife_ballistic_upgraded_zm` | yes | **no** | " |
| `knife_ballistic_bowie_zm` | yes | **no** | " |
| `knife_ballistic_bowie_upgraded_zm` | yes | **no** | " |

**So the answer to "is the default melee weapon published" is: every
melee-shaped weapon that vanilla's own constant table names IS published,
including `zombie_melee`. Nothing is being silently dropped.** The window is the
client's own constant table replayed verbatim.

What is *missing* is not publication but **use**: nothing in
`bin/home/codol_rawfiles/zm/**` ever gives a melee weapon to a *player*.
`zombie_melee` is precached and assigned as the **zombie AI's** `aiweapon`
(`_zombiemode_spawner.gsc:84,101-113` `resolve_melee_weapon()`), which is T5's
use for it too.

### 5.3 The melee-shaped defs do have the animation

MEASURED, `tools/codol_weapondef_zone_diff.py dump … --from common_gametype_zm`:

| weapon | `+0x098` (slot 7) | `+0x09c` (slot 8) |
|---|---|---|
| `zombie_melee` | `0x30a0526d` | `0x30a0526d` |
| `knife_ballistic_zm` | `0x30f6d78a` | `0x30f6e913` |

Both carry real melee animation names. A weapon whose def *does* name the
animation exists in the zone and is already published.

### 5.4 Budget / cap check — 54 is not a cap

* `CODOL_WEAPON_SLOTS` = **700** (`src/codol/snapshot/codol_configstrings.h:32`,
  re-exported through `codol_weapon_slots.h`). `CODOL_WEAPON_STATE_WEAPONS`
  is the same 700 (`codol_weapon_state.h:82`). The old IW3 128 was removed; the
  weapons/weaponold/weaponrechamber/weaponmodels arrays live in the playerstate
  extension at full width.
* `CODOL_NativeWeaponRoom()` (`codol_weapon_budget.c`) refuses a new composed
  definition only when `BG_GetNumWeapons() + 2 > 700`.
* The only surviving 128 is `ammo[]`/`ammoclip[]`, indexed by
  `def->iAmmoIndex`/`iClipIndex` — a separate, much smaller pool
  (`clip_of`/`reserve_of`, `codol_weapon_state.c:1889-1899`). That pool is not
  the weapon-index domain and does not truncate at 53/54.
* **The "54" is the mp window in the *current* log, not the zm one.** MEASURED,
  `bin/home/main/qconsole.log:150`:
  `CoDOL weapon window (mp): published 54 definitions, CS 6517 = 54 (constants demand 176)`.
  The zm log line, 150 in `qconsole.log.old`, says 131 of 131. The prior
  finding about "tables stopping at 53 returning silent defaults" (composed
  weapons living at slot 54+) does not bite here: zm publishes no composed
  weapons and its window is 131 wide.
* **Separate real problem, mp side:** the mp window is truncated to 54 of the
  176 its constants demand, and the truncation warning was NOT printed for it
  (the mp path takes the attachment-table branch of `collect_weapon_window`,
  which sets no `stopped_name`). That is out of scope here but worth its own
  work item.

### 5.5 Our zm roster names six weapons vanilla's zm window does not

MEASURED, diffing the 40 `add_zombie_weapon` base names against the 130-name
constant window:

```
as50_zm  c4_zm  knife_ballistic_zm  knife_ballistic_bowie_zm
sniper_explosive_zm  thundergun_zm
```

`as50_zm` and `c4_zm` do ship as assets (`patch_common_gametype_zm` /
`common_gametype_zm`) but are not named by the client's own constant table;
`thundergun_zm` only exists on `zm_prototype_sh`. Handing any of these out
forces a late append + `d <cs> <name>` republish, which vanilla never does.
This is a roster-fidelity defect independent of melee.

---

## 6. Item 6 — mp vs zm for the same weapon, in detail

MEASURED server-side differences for "the .44 magnum" between an mp match and a
zm match:

| input | mp | zm | same? |
|---|---|---|---|
| weapon name given | `coltanaconda_mp` (or a `*a 11 …` composed name over it) | `coltanaconda_zm` | **no — different asset, different zone** |
| how the window is built | ordered walk of `mp/coWeaponAttachmentTable.csv` | slot walk of `mp/constconfigstrings_zm.csv` | no |
| composed names published | yes (loadout bridge) | **never** (§2.2) | no |
| weaponattach overrides available | 276 records in 2 mp zones | **none** | no |
| `iMeleeDamage / iMeleeDelay / meleeChargeDelay / iMeleeTime / meleeChargeTime` | read from def `+0x590/+0x5a0/+0x5a4/+0x5c0/+0x5c4` | identical code, identical values (25 / 250 / 0 / 699 / 0) | **yes** |
| melee event IDs and parameters | 47/48/52/53/54, parameter 0 | identical | **yes** |
| melee charge port, usercmd decode, weapon-state phase 12..14, second-hand veto, `FireWeaponMelee` trace | identical | identical | **yes** |
| animation name in def slot 7 | `0x300f55bc` (present) | `0x3007f4b7` (pooled empty) | **no** |

**Conclusion: every server code path is byte-for-byte the same; the only
difference is the animation name in the shipped definition of a *different*
asset.** That is why this experiment cannot by itself locate a server bug — but
it also means that if vanilla plays the animation, vanilla must be making the
client read slot 7 from *something other than the held gun*, and choosing that
something is a server responsibility (§7, §9).

---

## 7. What T5/BO1 does, and what our zm port dropped

MEASURED in `D:\CoD\COD-GSC-Source\T5-STEAM-GSC` and `D:\CoD\OpenBLOPS`:

* **Default melee weapon: `knife_zm`.** `maps\_loadout.gsc:564-580`, the
  zombies branch of `init_models_and_variables_loadout`:
  `add_weapon( "knife_zm" ); add_weapon( "m1911_zm" );
  PrecacheItem( "bowie_knife_zm" ); set_laststand_pistol( "m1911_zm" );`
  `add_weapon()` queues into `level.player_loadout[]`, which `give_loadout()`
  (`:783-793`) turns into real `GiveWeapon` calls at spawn. Every zombies
  player spawns holding a **knife weapon plus** the pistol.
* **Melee-weapon tracking subsystem:** `maps\_zombiemode_utility.gsc` —
  `register_melee_weapon_for_level()` (`:3643`),
  `get_/set_player_melee_weapon()` (`:3689`, `:3695`),
  `init_player_melee_weapon()` (`:3701`),
  `register_offhand_weapons_for_level_defaults()` (`:3795-3817`) which sets
  `level.zombie_melee_weapon_player_init = "knife_zm"` and registers
  `bowie_knife_zm`. `init_player_offhand_weapons()` is called from player spawn
  (`_zombiemode.gsc:1608`).
* **Bowie purchase swaps the carried knife:** `maps\_zombiemode_bowie.gsc`,
  `do_bowie_flourish_end()` (`:173`, grant at `:200-231`) — plays the
  `zombie_bowie_flourish` prop weapon, then
  `self GiveWeapon( "bowie_knife_zm" ); self set_player_melee_weapon(
  "bowie_knife_zm" ); if ( self HasWeapon("knife_zm") ) self TakeWeapon(
  "knife_zm" );`, and separately reskins a carried `knife_ballistic_zm` to
  `knife_ballistic_bowie_zm`. The Sickle mirrors this
  (`_zombiemode_weap_sickle.gsc:269`).
* **Native support in T5:** `playerState_s::meleeWeapon`
  (`Game\Shared\bgame\bg_local.h:633`), networked at
  `Engine\Core\qcommon\msg_mp.cpp:468,2243`, set automatically on give when
  `weapDef->weapClass == WEAPCLASS_MELEE`
  (`Game\Server\game\g_weapon.cpp:1781-1782`), mirrored to the entity as
  `meleeWeapon` / `meleeWeaponModel` (`bg_misc.cpp:2882-2883`). The identifier
  `altmeleeweapon` does not exist in T5.

**What our port dropped** (MEASURED, zero hits across
`bin/home/codol_rawfiles/**`): `knife_zm`, `bowie_knife`, `revive_knife`,
`register_melee_weapon_for_level`, `set_/get_player_melee_weapon`,
`current_melee_weapon`, `zombie_melee_weapon_player_init`, and the whole
`_zombiemode_bowie.gsc` file. Our `giveStartingLoadout()`
(`zm/maps/mp/gametypes/_zombiemode.gsc:625-641`) is:

```
self takeAllWeapons();
if ( !isDefined( level.zombie_start_weapon ) ) return;
self giveWeapon( level.zombie_start_weapon );
self giveMaxAmmo( level.zombie_start_weapon );
self switchToWeapon( level.zombie_start_weapon );
```

— one pistol, no knife, and no Bowie system. The only knife that survived the
port is the unrelated **Ballistic Knife firearm** in the box roster
(`_zombiemode_weapons.gsc:158-159`), and `_zombiemode_perks.gsc:623-652` reuses
T5's flourish pattern (including the `"zmb_lost_knife"` notify) for the
Pack-a-Punch presentation instead.

### Caveat that must not be skipped

C1 is IW4-derived, and **its weapon-class table has no melee class.** MEASURED,
`codol_weapon_native.c:339-360`: C1's class table at `0xcd7f28` is
`rifle, sniper, mg, smg, spread, pistol, grenade, rocketlauncher, turret,
throwingknife, non_player, item` — twelve entries, no `WEAPCLASS_MELEE`. And
MEASURED from the serialized defs (`+0x344`): `zombie_melee` = 5 (pistol),
`knife_ballistic_zm` = 5, `hatchet_zm` = 9 (throwingknife),
`revive_knife_zm` = 9, `zombie_knuckle_crack` = 6, `throwingknife_zm` = 6.
Nothing declares itself a melee class. Neither is there a partner link:
`+0xb78` and `+0xb88` are the pooled empty string on `coltanaconda_zm`,
`m14ebr_zm` and `p90_zm` alike, so the held gun does not point at a knife.

So the T5 `ps->meleeWeapon` mechanism is **not proven to exist in C1**, and
"give the player a knife weapon" is a hypothesis to be tested, not an
established fix. What *is* established is that we dropped the T5 behaviour
without replacing it with anything, and that we never tested whether C1 honours
it.

---

## 8. The `defaultweapon_mp` fallback (added scope)

Two distinct uses; only one is a fallback.

1. **Slot 1 of every published window is `defaultweapon_mp`**
   (`codol_sv_weapons.c:460`). This is **not ours and not a leak**: MEASURED,
   `CS 5363 = "defaultweapon_mp"` in all three of C1's own constant tables,
   including `mp/constconfigstrings_zm.csv`
   (`CODOL_CATEGORY_WEAPON_WINDOW_20260917.md` §1). Vanilla's zm client
   registers that exact name at that exact slot. Changing it would desync our
   registration order from the client's and produce a `181 <name> <got> <want>`
   fatal.
2. **The missing-asset fallback** is `src/db_load.cpp:3500-3503`:
   ```c
   if (name && name[0] != '*' && strcmp(name, "defaultweapon_mp") &&
       CODOL_LoadMountedNativeWeapon("defaultweapon_mp", CODOL_LoadEngineWeaponCore, &weapon) == 1) {
     Com_PrintWarning(CON_CHANNEL_FILES, "CoDOL weapon '%s' is not in any mounted zone; using defaultweapon_mp\n", name);
   ```
   This substitutes the **already-registered slot-1 definition** for a weapon
   the zones do not carry, so an unspawnable map pickup skips instead of ending
   the level load. `defaultweapon_mp` itself ships in `code_post_gfx_mp`, a base
   zone mounted in every category.

**Is the unsuffixed `defaultweapon` the right zm substitute? No — it would be
wrong and unsafe.** MEASURED, `docs/zone_assets/ALL_weapon.txt:191-192`:
`defaultweapon` ships only in `common_gametype_zm`, and `defaultweapon_mp` only
in `code_post_gfx_mp`. But `defaultweapon` appears **nowhere in the zm constant
configstring window** — it has no configstring slot and therefore no wire ID, so
`CODOL_WeaponToWire` could not resolve it and the client could not name it. The
name `defaultweapon_mp` is carried into a zm match by C1's own zm data; keeping
it is parity, not contamination. The correct reading of the user's constraint is
that no **gameplay** weapon or asset may be borrowed from an `_mp` **zone**;
`defaultweapon_mp` is named by the zm table itself.

(If the parent wants the cosmetics fixed anyway, the honest change is to stop
*needing* the fallback — i.e. remove `thundergun_zm` from the roster on maps
that do not ship it — not to swap in an unpublished name.)

---

## 9. Ranked candidate root causes

### R1 — the zm player is never given a melee weapon, and vanilla's is (HIGH)

**Evidence for.** T5, the source of this game mode, gives every zombies player
`knife_zm` at spawn and swaps it for `bowie_knife_zm` on the Bowie purchase
(§7); T5's engine has a first-class `ps->meleeWeapon` slot for exactly this.
CoDOL's zm zone ships a full melee-weapon set (`zombie_melee`, `hatchet_zm`,
`revive_knife_zm`, `zombie_knuckle_crack`, `zombie_bowie_flourish`, four
`knife_ballistic_*`), names six of them in its own constant window, and the ones
we checked carry real melee animation names in slots 7/8 (§5.3) — content that
serves no purpose if melee is purely the held gun's animation. Our port dropped
the grant and the entire tracking subsystem (§7). This is unambiguously a
server-side (script-tree) omission, it is fixable from zm assets only, and it
explains why 22 guns with no melee animation of their own still melee on
vanilla.

**Evidence against / unresolved.** C1's class table has no melee class and
`+0xb78/+0xb88` are empty (§7 caveat), so the *mechanism* by which a carried
knife would supply the viewmodel animation for a swing made while holding a
rifle is not yet identified in C1. `zombie_melee` is also T5's zombie-AI claw
weapon, and our spawner already uses it that way. **The cheap decisive test:**
give a connected zm player `zombie_melee` (or `hatchet_zm`) as a second carried
weapon and melee with the Anaconda. If the animation appears, R1 is proved and
the fix is a `giveStartingLoadout()` change plus a ported melee-tracking
subsystem. It costs one GSC line to test.

### R2 — the held-weapon animation slot genuinely is empty and vanilla fills it another way we have not found (MEDIUM)

**Evidence for.** Independently re-measured this pass (§0.1): `coltanaconda_zm`
and `m14ebr_zm` hold the pooled empty string in both slot 7 and slot 8, while
`p90_zm` holds real names. The user's 22-silent report matches the 22-empty set
exactly, including both named weapons. C1's name getter `0x45c500` returns
`def[0x7c+4*index]` raw.

**Evidence against.** If this were the whole story, vanilla would be silent for
the same 22 weapons, and the user says it is not. So either R1 supplies the
name, or C1 has a fallback nobody has found yet — the `{primary, fallback}`
table at `0xcd6640` that `0x47ad10` indexes by animID is a **duration** table
(`+0x5b8..+0x648`), and no equivalent fallback has been looked for on the *name*
side. **Unclosed: nobody has disassembled the caller of `0x45c500` to see what
it does with an empty name.** That is the single highest-value piece of missing
evidence and it is a C1 question, not a data question.

### R3 — our zm roster is not vanilla's roster (MEDIUM, certain but probably not the melee cause)

Six of our 40 roster names are not in the client's own zm constant window
(§5.5), one of them (`thundergun_zm`) does not exist on two of the three zm
maps, and vanilla's window names weapons we never offer (`ump45_zm`,
`m1911dw_zm`, `hatchet_zm`, `explosive_bolt_zm`, …). Handing out an unwindowed
name forces a late append and a `d <cs> <name>` republish that vanilla never
performs. This is a real fidelity defect and it perturbs weapon indices, but no
mechanism links it to a missing melee animation.

### R4 — the animation is fine and what is actually missing is the melee *action* (LOW)

`codol_melee_debug.c` exists precisely to tell a miss apart from a zeroed
definition, and it was not enabled in the captured session. The melee event map,
the charge port, the weapon-state phase and the trace are all category-neutral
(§4), and `iMeleeDamage=25` is read identically for all these weapons, so there
is no positive evidence for this — but it has also never been ruled out live.
**Cheap check:** `set codol_meleeDebug 1` and count `CoDOL melee: fire …` lines
while swinging an Anaconda in zm.

### R5 — the loader warning degrades the weapon (RULED OUT)

§3.1. Pure print. Zero behavioural effect.

### R6 — composed/bare (RULED OUT for zm)

§2. No composed name is or can be published in a zm match, and no zm zone ships
a weaponattach record to apply.

### R7 — a table or budget silently drops weapons past a cap (RULED OUT for zm)

§5.4. The zm window publishes 131 of 131. `CODOL_WEAPON_SLOTS` is 700. The 54 is
the mp window in a different log. (The mp window's own 54-of-176 truncation is a
real separate defect, and notably it truncates **without** printing the
truncation warning, because the mp branch of `collect_weapon_window` never sets
`stopped_name`.)

---

## Appendix A — the runtime warning list vs the slot-7 list

MEASURED, `bin/home/main/qconsole.log.old` (zone type zm, `zm_asylum_sh`): 39
`melee damage 25 but animation slot 7 is empty` warnings. Distinct base weapons,
with their upgraded twins folded in:

`coltanaconda`, `glock`, `uzi`, `tmp`, `striker`, `m14ebr`, `m16` (+
`gl_m16_upgraded_zm`, `m16_gl_upgraded_zm`), `famas`, `fal`, `ak104`, `tavor`,
`m4a1tech`, `mk_scar_h_upgraded_zm`, `cheytac`, `wa2000`, `sniper_explosive`,
`l86`, `crossbow_explosive`, `ray_gun`, `tesla_gun`.

This is the §2.3 empty list minus `thundergun_zm` (not mounted on
`zm_asylum_sh`), `frag_grenade_zm` and `claymore_zm` (not precached in that
session). No weapon from the populated list warns. The two user-confirmed silent
weapons are both present.

MEASURED, `bin/home/main/qconsole.log` (zone type mp): **10** warnings, every
one a non-held asset — `scavenger_bag_mp`, `ac130_25mm_mp`, `ac130_40mm_mp`,
`ac130_105mm_mp`, `remotemissile_projectile_mp`, `harrier_missile_mp`,
`heli_remote_mp`, `mortar_mp`, `dog_bite`, `dogs_mp`. Every real mp gun has the
animation; most real zm guns do not.

## Appendix B — commands used

```
python tools/codol_weapondef_zone_diff.py dump coltanaconda_mp --start 0x7c --end 0xa8
python tools/codol_weapondef_zone_diff.py dump <w> --from common_gametype_zm --start 0x94 --end 0xa0
python tools/codol_weapondef_zone_diff.py dump <w> --from common_gametype_zm --start 0xb70 --end 0xb94
python tools/codol_weapondef_zone_diff.py dump <w> --from common_gametype_zm --start 0x340 --end 0x350
```

Note the caveat already recorded in `CODOL_MELEE_ANIM_20260920.md` §2: this
tool's `attach` subcommand mis-pairs offsets with strings (it consumes an inline
string for every record with type `<16` and a non-zero value, where C1 and
`CODOL_LoadMountedWeaponAttachment` consume one only when the value is the
inline marker `0xFFFFFFFF`). The `dump` subcommand used here is unaffected.

---

# Addendum, 2026-09-20 — R1 patch spec and the mp 54-of-176 window

Still audit-only. Nothing outside this file was written.

## A. CORRECTION to §5.4 / R7: the mp window is NOT silently truncated

My first pass said the mp branch "truncates 54 of 176 without printing the
truncation warning". **That characterisation is wrong and is withdrawn.** The
mp branch of `collect_weapon_window` (`codol_sv_weapons.c:461-465`) has no
partial-stop path at all:

```c
if(table) {
    for(i=0;i<(unsigned)table->rowCount;++i)
        if(!register_stock(scratch,names,&count,table->values[(size_t)i*table->columnCount])) { count=0; goto done; }
    goto done;
}
```

Any failure sets `count=0`, which trips `if(count<2)` in
`CODOL_InitializeServerWeaponConfigstrings` and **fails the whole map start**
with `cannot register weapon '<name>'`. So mp either publishes the table's
entire yield or refuses to start. It never stops early, which is exactly why it
never sets `stopped_name`. Nothing is being silently dropped by the loop.

This is also already a **known, documented open item**:
`CODOL_CATEGORY_WEAPON_WINDOW_20260917.md` §6.2 — "mp is still on the
attachment table … deliberately out of this pass".

## B. Why 54 — exact loop, condition and limit

MEASURED. `mp/coWeaponAttachmentTable.csv` is a **stringtable asset**, and two
zones ship it (`docs/zone_assets/ALL_stringtable.txt:410-411`):

| zone | shape | column 0 |
|---|---|---|
| `code_post_gfx_mp` | 4 cols x 1836 rows | **empty in every row** |
| `patch_code_post_gfx_mp` | 4 cols x 1907 rows | 52 distinct non-empty names |

`CODOL_LoadEngineStringTable` searches newest-zone-first, so the server gets the
patch copy. The loop walks all 1907 rows of column zero;
`register_stock(...)` (`codol_sv_weapons.c:196-199`) begins

```c
if(!name || !*name) return 1;          /* empty cell -> skipped, success */
...
for(i=0;i<*count;++i) if(!strcmp(names[i],name)) return 1;   /* duplicate -> skipped */
```

so 1907 rows collapse to **52 names**. Plus the two implicit registrations
(`none`, `defaultweapon_mp`, `:459-460`) that is **54**, and the walk completes
with no failure — hence `published 54 definitions, CS 6517 = 54`.

The 52, in table (alphabetical) order and therefore in published slot order
2..53:

```
aa12_mp acr_mp ak104_mp ak47_mp as50_mp at4_mp aug_mp barrett_mp cartevent_mp
cheytac_mp coltanaconda_mp deserteagle_mp fal_mp famas_mp ff58_mp fn2000_mp
g18_mp l86_mp m1014_mp m14ebr_mp m16_mp m21ebr_mp m240_mp m4_mp m4a1tech_mp
m4a1techevent_mp m9_mp m93_mp magnumncm_mp mcsevent_mp mg4_mp miniuzi_mp
model1887_mp mp5k_mp mp5sd_mp p90_mp pp2000_mp ranger_mp rpd_mp rpg_mp scar_mp
scarsapr_mp spas12_mp spbc_mp striker_mp tar21_mp tmp_mp type95_mp ump45_mp
usp_mp vector_mp wa2000_mp
```

**54 is not a cap and not a coincidence: it is literally `2 + 52`.** And it
*is* the boundary the "Composed weapon index trap" memory refers to — the
stock prepass owns 0..53, so every composed loadout weapon, every killstreak,
every grenade and every late script precache lands at **slot 54 or above**.
That memory and this number are the same fact.

### Fragility worth flagging

If `patch_code_post_gfx_mp` ever fails to mount, the base
`code_post_gfx_mp` copy has an **entirely empty column zero**, the loop
registers nothing, and `count` stays at 2 — a two-weapon mp match. There is no
guard for this and no warning distinguishes it from success.

## C. What is dropped

The mp constant window names 152 weapons over CS 5363..5537 with 22 unnamed
holes (CS 5437-5438, 5440-5460) and `CS 6517 = 176`
(`CODOL_CATEGORY_WEAPON_WINDOW_20260917.md` §1). We publish 53 of indices
1..175 and blank the rest.

I could not enumerate the constant window's 152 names: the tool's stringtable
reader returns empty for de-duplicated cells, and the mp table's **index**
column is entirely de-duplicated (the zm list in that doc was recovered by
hash-matching every NUL-terminated string in the zone, which I did not redo).
What I can give exactly is the **asset-level** drop list — weapons that exist in
`common_gametype_mp` / `patch_common_gametype_mp` and are not in our 54:
**138 of 190**. Highlights:

* **Real held guns:** `masada_mp`, `tavor_mp`, `uzi_mp`, `glock_mp`,
  `beretta_mp`, `beretta393_mp`, `m21_mp`, `m79_mp`, `riotshield_mp`,
  `deserteaglegold_mp`.
* **Every `gl_*` launcher partner** (`gl_acr_mp`, `gl_m4_mp`, `gl_m16_mp`,
  `gl_famas_mp`, `gl_scar_mp`, `gl_tavor_mp`, `gl_type95_mp`, …) and **every
  `*_shotgun_attach_mp` masterkey partner**.
* **Every grenade/equipment:** `frag_grenade_mp`, `semtex_mp`, `flash_grenade_mp`,
  `concussion_grenade_mp`, `smoke_grenade_mp`, `emp_grenade_mp`,
  `white_phosphorus_grenade_mp`, `c4_mp`, `claymore_mp`, `bouncingbetty_mp`,
  `throwingknife_mp`, `scrambler_mp`, `lightstick_mp`, `tabun_*`.
* **Every killstreak** (`killstreak_*`, `ac130_*`, `harrier_*`, `cobra_*`,
  `pavelow_minigun_mp`, `sentry_*`, `tow_turret_*`, `rcbomb_mp`, `nuke_mp`,
  `airdrop_*`, `stinger_mp`, `javelin_mp`, `artillery_mp`, `mortar_mp`, …).
* `dog_bite`, `dogs_mp`, `remote_missile*`, `barrel_mp`, `destructible` props.

## D. User-visible consequence

1. **No `CG_Init` NULL crash, and this is provable rather than hopeful.**
   `CODOL_InitializeServerWeaponConfigstrings` publishes `CS 6517 = 54`, our own
   prefix, never the constants' 176, and blanks CS 5363+54..5537.
   `ValidateWeaponConfigString` (`0x00483600`) early-outs on an **empty name**
   (`if (!name[0]) return;`), so the 699-slot sweep skips every blanked slot,
   and `CG_Init`'s registration loop (`0x47d1d0`, `1..count-1`) only touches the
   54 buildable definitions. The crash at `0x0047c1f7` needs a counted index
   with no buildable definition; we never create one.
2. **The real cost is ORDER, not absence.** All 138 arrive later, through
   `CODOL_RefreshServerWeaponMappings` appending and sending
   `d <cs> <name>` — in *script execution order*, which is not the client's
   constant order. From slot 54 up, our indices and vanilla's disagree
   wholesale. Anything client-side that keys off a weapon's vanilla index
   (menus, `ui_viewer_mp`, HUD/icon tables, anything the lobby hands over) is
   reading a different weapon than the one the server means.
3. **It is a per-match cost, not a one-off.** Every publication rebuilds the
   whole wire registry and clones up to 6519 configstring slots
   (`CODOL_WEAPON_COMPOSER_CACHE_20260914.md`), so 138 late appends is 138
   rebuild-and-republish cycles.
4. **Known mp misbehaviour it plausibly explains:** the `181 cheytac_mp 11 10`
   partner-shape off-by-one recorded in
   `CODOL_FS_GAME_EVIDENCE_20260917.md` §7.3 sits inside this prefix —
   `cheytac_mp` is the 10th table name, so our slot for it is 11, and the record
   says the published slot was 10, i.e. one earlier name did not register in
   that session (`cartevent_mp`, the 9th, ships only in
   `patch_common_gametype_mp` and `ui_viewer_mp`). **INFERRED**, not proved: I
   did not reproduce it. It is *not* a `+0xb78` partner insertion — MEASURED,
   `aa12_mp`, `acr_mp`, `ak47_mp`, `m4_mp`, `m16_mp`, `famas_mp` and
   `cheytac_mp` all carry the pooled empty string at both `+0xb78` and `+0xb88`
   in `common_gametype_mp`, so neither the client nor `register_stock` appends a
   partner from these defs. That is also why our count lands on exactly
   `2 + 52` with no partner inflation.
5. It does **not** explain the melee bug. zm does not use this branch.

## E. The fix

Three parts, in order of value.

1. **Make the mp branch report, like the zm branch does.** The loop currently
   has only "complete" and "kill the map start". Give it the same
   `stopped_name`/`stopped_slot` contract: on a `register_stock` failure, set
   `*stopped_name = <row name>`, `*stopped_slot = count`, keep the prefix
   (do not zero `count`) and `break` instead of `count=0`. The existing warning
   at `codol_sv_weapons.c:539-545` then prints
   `published N of the 176 its constants demand; truncated at slot S by '<name>'`
   for mp too. Separately, warn when the table yields fewer than some sane floor
   (the empty-column-zero case in §B) — "the attachment table named 0 weapons"
   is currently indistinguishable from success.
2. **Move mp onto the constant window, as coop/zm already are.** A plain slot
   walk gets to **index 74** before the first hole (CS 5437), i.e. `count = 75`
   — already 21 more than today and in the client's own order. That alone
   removes the ordering divergence for the whole 1..74 range.
3. **Fill the 22 holes to reach the full 176.** The holes are CS 5437-5438 and
   5440-5460. `ValidateWeaponConfigString` compares
   `BG_GetWeaponIndexForName(name)` against the slot, so a filler must be a name
   the client resolves to *that* slot — which, because the client registers in
   configstring order, any buildable name does, provided the server's order and
   the client's stay identical. Vanilla's own shape for this is
   `alpha0022/docs/ERRORS.md:8529-8540`'s "141 names + 33 hole fillers".
   Choosing the fillers is the actual work item and it needs a live mp connect
   to validate, since a wrong choice is an `ERR_DROP`, not a degradation.

Note `CS 6517` must stay **our** count at every step, never the constants' 176,
until every counted index is genuinely backed.

## F. R3 update (accepted from the parent)

The honest fix for the `defaultweapon_mp` fallback line is to stop *needing*
it: drop `thundergun_zm` (and any other name) from the roster on maps that do
not ship it, rather than change the fallback. `thundergun_zm` ships only in
`zm_prototype_sh`; on `zm_asylum_sh` and `zm_zombie_training` it resolves to the
slot-1 default. `_zombiemode_weapons.gsc` already validates names with
`precacheItem` + `getWeaponIndexFromName` elsewhere, so gating the
`add_zombie_weapon` call on the same test is the minimal change. The five other
off-window names (`as50_zm`, `c4_zm`, `sniper_explosive_zm`,
`knife_ballistic_zm`, `knife_ballistic_bowie_zm`) do resolve as assets but are
still late appends.

---

# G. R1 patch SPECIFICATION (for the parent to apply; nothing was edited)

## G.0 Which weapon, justified from def contents

The five published candidates, MEASURED out of `common_gametype_zm`
(`iMeleeDamage +0x590`, `iMeleeDelay +0x5a0`, `meleeChargeDelay +0x5a4`,
`iMeleeTime +0x5c0`, `meleeChargeTime +0x5c4`, anim name slots 7/8 at
`+0x098`/`+0x09c`, weapClass `+0x344`, offhandClass `+0x354`):

| weapon | dmg | delay | chgDelay | time | chgTime | slot 7 | slot 8 | class | offhand |
|---|---|---|---|---|---|---|---|---|---|
| **`zombie_melee`** | **50** | 50 | **150** | 699 | **699** | `0x30a0526d` | `0x30a0526d` | 5 | 0 |
| `hatchet_zm` | 0 | 250 | 0 | 699 | 0 | — | — | 9 | 0 |
| `revive_knife_zm` | 0 | 100 | 0 | 660 | 0 | — | — | 9 | 0 |
| `zombie_knuckle_crack` | 0 | 250 | 0 | 699 | 0 | — | — | 6 | 0 |
| `zombie_bowie_flourish` | 0 | 250 | 0 | 699 | 0 | — | — | 6 | 0 |
| `knife_ballistic_zm` (control) | 0 | 50 | 100 | 500 | 1000 | `0x30f6d78a` | `0x30f6e913` | 5 | 0 |
| `coltanaconda_zm` (control) | 25 | 250 | 0 | 699 | 0 | empty | empty | 5 | 0 |

**Choose `zombie_melee`,** on three independent facts and not on its name:

1. It is the **only** candidate with a non-zero `iMeleeDamage` (50, twice a
   gun's 25). C1's `PM_Weapon_CheckForMelee` (`0x41c0f7`) gates on `+0x590`;
   the other four are 0 and therefore **cannot melee at all** — they are
   animation props.
2. It is the only candidate with a non-zero `meleeChargeDelay` **and**
   `meleeChargeTime` (150 / 699), i.e. the only one that describes a melee
   lunge — the exact pair `CODOL_PM_MeleeChargeUpdateC1` consumes.
3. Both melee animation name slots are populated (and identical — one animation
   for swing and charge), which is precisely what the 22 silent guns lack.

`offhandClass = 0` and `weapClass = 5` mean it is a **primary-hand** weapon, so
`giveWeapon` places it in the player's hands as a selectable weapon.

### Flagged uncertainties — read before applying

* **`zombie_melee` is also the zombie AI's claw weapon in our own tree**
  (`_zombiemode_spawner.gsc:84,101-113` `resolve_melee_weapon()`), and in T5 it
  is what a *player* is given when they turn into a zombie
  (`T5 _zombiemode.gsc:4226 GiveWeapon("zombie_melee", 0)`). Sharing one def
  between the player's knife and the AI's claw is probably not what vanilla
  CoDOL does. It is the right weapon for the **decisive test**; it may not be
  the right weapon for the shipped fix.
* **The mechanism is unproven.** C1's weapon-class table (`0xcd7f28`) has no
  melee class and `+0xb78`/`+0xb88` are empty on the guns, so there is no
  identified C1 path by which a *carried* knife supplies the melee animation
  for a swing made while holding a rifle. This patch tests that hypothesis; it
  does not rest on it.
* Because `weapClass = 5`, the player can **cycle to** `zombie_melee` and hold
  a claw viewmodel. For the test that is informative; for a shipped fix it is
  wrong and would need the T5 tracking layer (Part B) plus a hide.

## G.1 Line endings

MEASURED:

```
F=bin/home/codol_rawfiles/zm/maps/mp/gametypes/_zombiemode.gsc
tr -cd '\r' < "$F" | wc -c               ->  0
tr -cd '\n' < "$F" | wc -c               ->  1097
git show HEAD:"$F" | tr -cd '\r' | wc -c ->  0
git show HEAD:"$F" | tr -cd '\n' | wc -c ->  1097
```

**Pure LF, worktree and HEAD identical.** `.gitattributes` is `* text=lf` and
`core.autocrlf=false`. `_zombiemode_utility.gsc` is likewise pure LF (0 CR,
681 LF) and ends with `}` + LF. Indentation in both files is **hard tabs**.

## G.2 Part A — the minimal change (this is the whole decisive test)

File: `bin/home/codol_rawfiles/zm/maps/mp/gametypes/_zombiemode.gsc`
(function `giveStartingLoadout()`, currently lines 625-641).

**Anchor — match exactly. Leading whitespace is one TAB per level; every line
ends LF.**

```
giveStartingLoadout()
{
	self takeAllWeapons();

	if ( !isDefined( level.zombie_start_weapon ) )
		return;

	self giveWeapon( level.zombie_start_weapon );
```

**Replacement:**

```
giveStartingLoadout()
{
	self takeAllWeapons();

	// T5 _loadout.gsc:564-580 gives every zombies player a melee weapon
	// ("knife_zm") alongside the starting pistol, and _zombiemode_bowie.gsc
	// swaps it for "bowie_knife_zm" on the wall purchase.  This port dropped
	// that grant entirely.  CoDOL has no knife_zm; the zm window's melee
	// weapon is "zombie_melee" (index 45), the only published candidate with
	// a non-zero iMeleeDamage (+0x590 = 50), a real melee charge
	// (+0x5a4/+0x5c4 = 150/699) and both melee animation name slots populated
	// (+0x098/+0x09c).  22 of the 40 roster guns name no melee animation of
	// their own -- docs/CODOL_MELEE_SERVER_AUDIT_20260920.md.
	// Given before the pistol so the pistol is still what ends up equipped.
	if ( !isDefined( level.zombie_player_melee_weapon ) )
		level.zombie_player_melee_weapon = "zombie_melee";

	if ( getWeaponIndexFromName( level.zombie_player_melee_weapon ) > 0 )
		self giveWeapon( level.zombie_player_melee_weapon );

	if ( !isDefined( level.zombie_start_weapon ) )
		return;

	self giveWeapon( level.zombie_start_weapon );
```

Everything after that line is unchanged (`giveMaxAmmo`, `switchToWeapon`, the
`codol_applyProfileCharacter` comment and call, closing brace).

Notes for the applier:

* The melee give is placed **before** the `isDefined( level.zombie_start_weapon )`
  early return on purpose, so the knife is still granted on a map with no
  resolved start weapon.
* `getWeaponIndexFromName` is the same guard `resolve_melee_weapon()` already
  uses (`_zombiemode_spawner.gsc:110`); it keeps the give from firing if the
  weapon is somehow unregistered. `zombie_melee` is already precached by
  `_zombiemode_spawner.gsc:109`, so no new registration should occur.
* Do **not** add a `switchToWeapon` for the knife — the test is "melee with the
  Anaconda while carrying it".
* No `giveMaxAmmo`: `zombie_melee` is a melee def and an ammo grant would only
  perturb the clip/reserve pools.
* Builtins used are registered: `giveweapon` (`src/scr_vm_main.c:541`),
  `getweaponindexfromname` (already used in the zm tree).
* After applying, run the mandated gate:
  `python tools/codol_script_resolve.py --root bin/home/codol_rawfiles --only zm`
  (must exit 0).

**Expected outcome of the test.** Spawn, keep the Anaconda equipped, melee. If
an animation plays, R1 is confirmed and the mechanism exists in C1. If nothing
plays, R1 is refuted for the "carried weapon" form and R2 becomes the live
theory — at which point the next step is disassembling the caller of C1
`0x45c500` to see what it does with an empty animation name.

## G.3 Part B — the T5 tracking subsystem (OPTIONAL, not needed for the test)

Apply only once Part A has shown the mechanism works; it adds no behaviour on
its own. It is the faithful T5 port, renamed to what our zone publishes.

File: `bin/home/codol_rawfiles/zm/maps/mp/gametypes/_zombiemode_utility.gsc`.
Append at end of file (the file ends `}` + LF; add one blank LF line first).
Hard tabs, LF endings.

```
// --------------------------------------------------------------------------
// Player melee weapon.  T5 _zombiemode_utility.gsc:3643 / :3689 / :3695 /
// :3701 / :3795-3817, with CoDOL names: T5's "knife_zm" and "bowie_knife_zm"
// do not exist in this game.  The zm weapon window publishes "zombie_melee"
// (index 45) as the only melee-capable definition (iMeleeDamage 50, melee
// charge 150/699, animation name slots 7 and 8 populated).
// --------------------------------------------------------------------------

register_melee_weapon_for_level( weaponname )
{
	if ( !isDefined( level.zombie_melee_weapons ) )
		level.zombie_melee_weapons = [];

	for ( i = 0; i < level.zombie_melee_weapons.size; i++ )
	{
		if ( level.zombie_melee_weapons[ i ] == weaponname )
			return;
	}

	level.zombie_melee_weapons[ level.zombie_melee_weapons.size ] = weaponname;
}

is_melee_weapon( weaponname )
{
	if ( !isDefined( level.zombie_melee_weapons ) || !isDefined( weaponname ) )
		return false;

	for ( i = 0; i < level.zombie_melee_weapons.size; i++ )
	{
		if ( level.zombie_melee_weapons[ i ] == weaponname )
			return true;
	}

	return false;
}

get_player_melee_weapon()
{
	return self.current_melee_weapon;
}

set_player_melee_weapon( weaponname )
{
	self.current_melee_weapon = weaponname;
}

init_player_melee_weapon()
{
	self set_player_melee_weapon( level.zombie_melee_weapon_player_init );
}

register_melee_weapons_for_level_defaults()
{
	register_melee_weapon_for_level( "zombie_melee" );
	level.zombie_melee_weapon_player_init = "zombie_melee";
}
```

Call sites, if Part B is applied: `register_melee_weapons_for_level_defaults()`
once during zm level init (alongside `init_weapons()`), and
`self init_player_melee_weapon()` inside `giveStartingLoadout()` after the
melee give. **I have not verified that `_zombiemode_utility.gsc` has no
existing symbol with any of these six names** — check before appending.

The Bowie purchase (`_zombiemode_bowie.gsc`: wall trigger, 3000 points,
`zombie_bowie_flourish` presentation, swap the melee weapon and reskin a
carried `knife_ballistic_zm` to `knife_ballistic_bowie_zm`) is deliberately
**not** specified here. It cannot be designed until Part A says whether a
carried melee weapon reaches the client at all, and CoDOL ships no
`bowie_knife_zm` for the upgraded slot — the substitute would have to be
`hatchet_zm` (weapClass 9, iMeleeDamage 0, so it cannot melee) or a patched
def, and neither is obviously right.

---

# Addendum 2, 2026-09-21 — Bowie row swap spec, and the R3 gate is already there (and broken)

Audit/spec only. Nothing outside this file was written. R1 (carried melee
weapon) is **withdrawn**, superseded by the parallel disassembly agent's
`ps+0x338` / `mp/coKnifeStatsTable.csv` row model, which I accept: it explains
mp and zm with one mechanism, and my own §7 caveats (no melee class at
`0xcd7f28`, `zombie_melee` is weapClass 5 and is the AI's claw) pointed the same
way.

## H. Independent corroboration of the row model

MEASURED this pass, my own reads, not taken from the other agent:

* **`mp/coKnifeStatsTable.csv` ships only in `code_post_gfx_mp`**
  (`docs/zone_assets/ALL_stringtable.txt:152`) — a base zone mounted in every
  category, so the table is resident in a zm match with **no `_mp` zone
  dependency**. That satisfies the user's constraint.
* **Shape: 24 columns x 21 rows.** Row order (1-based), column 0:

  | row | name | row | name |
  |---|---|---|---|
  | 1 | `mel_prison` | 12 | `mel_hook` |
  | 2 | *(de-dup'd)* | **13** | *(de-dup'd)* = `zknife_standard` |
  | 3 | `mel_sog` | **14** | **`zknife_bowie`** (inline, read directly) |
  | 4 | `mel_karambit` | 15 | *(de-dup'd)* = `zknife_sickle` |
  | 5 | `mel_bowie` | 16 | `zknife_halberd` |
  | 6 | `mel_hatchet` | 17 | `coop_mel_knife` |
  | 7 | `mel_shovel` | 18 | `coop_mel_karambit` |
  | 8 | `mel_cleaver` | 19 | `coop_mel_bonesaw` |
  | 9 | `mel_bonesaw` | 20 | `coop_mel_sog` |
  | 10 | `mel_axe` | 21 | `coop_mel_bowie` |
  | 11 | `mel_hammer` | | |

  Blank cells in my dump are **de-duplicated string references**, not empty
  cells — the tool's stringtable reader only resolves inline cells. Row 13's
  name and its `viewmodel_knife_melee_slice` are de-dup'd, which is why they
  read blank here; row 14 `zknife_bowie` is inline and reads directly. Row 13's
  own inline cells are the zm melee sounds `zmb_knife_swing`,
  `zmb_knife_impact_robot`, `zmb_knife_miss` — which independently confirms row
  13 is the zombies knife.
  The `zknife_*` block is exactly rows 13..16 and the `coop_mel_*` block
  17..21, matching the `g_gametype`-prefix gate.
* **`0x4200e0` is the name -> row resolver, and it returns a 1-based index.**
  MEASURED disassembly: count at `[0x1536be4]`, record array at `0x150e210`,
  **stride 0x5C**, record field 0 is the name pointer; inline strcmp; on match
  `lea eax,[esi+1]; ret`; on exhaustion `xor eax,eax; ret`. So **0 = not
  found**. (`0x150e210` is also where `bg_weaponDefs` ends —
  `codol_weapon_slots.h` already names that address as "the next live global".)
* **`0x420140` reads `[ps+0x338]`**, confirming the field.
* **`0x5169b0` is the GSC setter front half.** MEASURED: `xor eax,eax; call
  0x5cded0` (Scr_GetString, param 0) -> `esi`; compare against `0xc30704`,
  which `CODOL_CATEGORY_WEAPON_WINDOW_20260917.md` §7.1 already established is
  **`"none"`**; equal -> return with 0. Otherwise `0x5169d3`: `push esi; call
  0x4200e0`; non-zero -> `0x516a1a` (store); zero -> a second `"none"` compare
  and then a script error through `0x6286d0` with format `0xc55748`.
  **So the C1 contract is exactly: one string argument; `"none"` -> row 0
  (override off); any other name -> 1-based row; unknown name -> script error.**

### The C1 builtin's NAME is not recoverable — and does not matter

MEASURED. The method-table entry holding `0x516e40` is at `.rdata 0x00c3bce0`,
in a **12-byte-stride** table. Every entry's name pointer in that region is the
*same* pointer, `0xc2fead`, and the byte there is `0x00` — an empty string.
Neighbouring `.rdata` reads `"ph\0\0" "25 %s %i\0\0\0\0" "53\0\0" "AimTarget_Ge…"`,
i.e. the same stripped-to-numeric-ID treatment the
`c1exe-dvars-stripped-numeric` finding records for dvars. **C1's GSC builtin
name table is stripped.**

This is fine, because **the builtin we need is a SERVER one.** C1's VM never
runs our GSC; our GSC tree is parsed and executed by our own VM
(`src/scr_vm_main.c`). The name is ours to choose. The one real risk is if a
*shipped* CoDOL GSC ever had to resolve the original name — our zm tree is
hand-written, so it does not. Flagged rather than assumed.

---

## I. SPEC — the `ps+0x338` row setter (four small pieces)

The current implementation
(`src/codol/snapshot/codol_engine_state.c:477-482`) computes the row at encode
time from the zone type:

```c
const char *zone = CODOL_ServerZoneType();
unsigned melee_row = (zone && zone[0]=='z' && zone[1]=='m' && !zone[2]) ? 13u : 0u;
if (!put(&out, 0x338, melee_row)) return 0;
```

That is correct for "everyone has the standard knife" and is **the right thing
to ship first**. It cannot express the Bowie swap, because the row is a
constant, not per-player. The four pieces below turn it into per-player state.
Piece 4 is the only one that touches a file another agent owns.

### I.1 — a per-player field in the playerstate extension

File: `src/codol/snapshot/codol_playerstate_ext.h`, in `codol_ps_ext_t`
(the struct ending at `:427`), beside `int32_t spawn_time;` (`:409`):

```c
    /* mp/coKnifeStatsTable.csv row for ps+0x338, 1-based; 0 = no override.
     * zm spawns at 13 (zknife_standard) and the Bowie purchase swaps to 14
     * (zknife_bowie).  C1 0x47c090 skips the whole override at row 0. */
    uint32_t melee_row;
```

Accessors, mirroring `CODOL_PlayerStateSpawnTimeSet/Read` exactly
(`src/codol/snapshot/codol_playerstate_ext.c:544-558`):

```c
int CODOL_PlayerStateMeleeRowSet(const playerState_t *ps,unsigned value)
{
    codol_ps_ext_t *ext=resolve(ps);
    if(!ext) { miss(ps); return 0; }
    ext->melee_row=value;
    return 1;
}

int CODOL_PlayerStateMeleeRowRead(const playerState_t *ps,unsigned *value)
{
    const codol_ps_ext_t *ext=resolve(ps);
    if(!ext || !value) return 0;
    *value=ext->melee_row;
    return 1;
}
```

plus `void CODOL_PlayerStateExtClearClientMeleeRow(unsigned client);` following
the `...ClearClientSpawnTime` pattern, and declarations next to `:437-439`.
The extension is already copied live -> snapshot -> archive by
`CODOL_PlayerStateExtCopy`, so nothing else is needed for it to survive.

### I.2 — the encoder reads the field, with the zone default as the fallback

Same site in `codol_engine_state.c`. Keep the existing comment block; replace
only the computation:

```c
{
    const char *zone = CODOL_ServerZoneType();
    unsigned melee_row = (zone && zone[0]=='z' && zone[1]=='m' && !zone[2]) ? 13u : 0u;
    unsigned stored;
    /* A script may override the row per player (the Bowie swap, 13 -> 14).
     * An unset extension keeps the category default, so behaviour is
     * unchanged until a script calls the setter. */
    if (CODOL_PlayerStateMeleeRowRead(ps, &stored) && stored)
        melee_row = stored;
    if (!put(&out, 0x338, melee_row)) return 0;
}
```

Note the encoder function currently receives `ps`; confirm it is the *live*
playerstate and not a scratch copy — `CODOL_PlayerStateExt` returns NULL for a
scratch buffer, in which case the read fails and the default applies, which is
the safe direction.

### I.3 — the server builtin

New file `src/codol/script/codol_script_melee_row.c` (area `script/`, so the
makefile globs it; no directory prefix needed in includes).

Name: **`codol_setknifetype`**. Rationale: C1's own name is stripped and
unrecoverable (§H), the `codol_` prefix is the established convention for
server-specific builtins in this tree (`codol_isweaponpublished`,
`codol_getweaponclass`, `codol_weaponinventorytype`), and it cannot collide
with a real C1 name we might later recover. `Scr_AddMethod` names in this tree
are **all lowercase** — the VM lowercases on lookup.

Signature, mirroring C1's contract from §H:

```
<player> codol_setKnifeType( <row name> )     // "none" turns the override off
```

Body:

```c
/* <player> codol_setKnifeType( <mp/coKnifeStatsTable.csv row name> )
 *
 * C1 keeps the melee viewmodel animation, damage, range, rate, knife models
 * and sounds in a row of mp/coKnifeStatsTable.csv and selects the row from
 * ps+0x338 as a 1-based index (0x47c1c0; applied at 0x47c090, skipped
 * entirely when the row is 0 at 0x47c0f3).  This is C1's own setter contract,
 * read out of 0x5169b0: one string argument, "none" -> 0, otherwise the
 * 1-based row from the name resolver 0x4200e0 (returns esi+1, 0 = not found),
 * and a script error on an unknown name.  C1's builtin NAME is not
 * recoverable -- its method-table name pointers are all the empty string at
 * 0xc2fead, stripped exactly as its dvar names are -- so this server names it
 * itself; nothing in C1 parses our GSC.
 *
 * The table ships in code_post_gfx_mp, a base zone every category mounts, so
 * this resolves in zm with no _mp zone dependency. */
void CODOL_Scr_SetKnifeType(scr_entref_t ref)
{
    gentity_t *ent = /* the tree's existing player-entity resolver, as
                        codol_weapon_give.c:145 uses give_player_entity(ref) */;
    const char *name;
    unsigned row;
    if (!ent) return;
    if (Scr_GetNumParam() != 1) {
        Scr_Error("Usage: <player> codol_setKnifeType( <knife row name> )"); return;
    }
    name = Scr_GetString(0);
    if (!name || !*name || !Q_stricmp(name, "none")) row = 0;
    else if (!CODOL_KnifeStatsRowForName(name, &row)) {
        Scr_Error(va("codol_setKnifeType: '%s' is not a row of "
                     "mp/coKnifeStatsTable.csv", name));
        return;
    }
    CODOL_PlayerStateMeleeRowSet(&ent->client->ps, row);
}
```

`CODOL_KnifeStatsRowForName` is the server-side twin of C1 `0x4200e0`. It must
use the existing `CODOL_LoadEngineStringTable("mp/coKnifeStatsTable.csv", …)`
(the same loader `codol_sv_weapons.c:509` uses for the attachment table),
compare **column 0 case-sensitively** the way `0x4200e0`'s inline strcmp does,
and return the **1-based** row. Cache the table pointer per map; a missing
table must fail the lookup, not crash.

> **Flagged:** C1 resolves against its *parsed* knife-stat array
> (`0x150e210`, stride 0x5C, count `[0x1536be4]`), which is built from the
> table but may drop rows the client rejects. Resolving against the raw CSV
> assumes the parse keeps every row and its order. Row 14 `zknife_bowie` is
> inline and unambiguous, so the Bowie swap is safe either way; a general
> name->row map should be sanity-checked live before it is relied on.

Registration, `src/scr_vm_main.c`, with the other player methods (the
`giveweapon`/`takeweapon`/`hasweapon` block at `:541-561`):

```c
	Scr_AddMethod("codol_setknifetype", CODOL_Scr_SetKnifeType, 0 );
```

The static gate treats an unknown builtin as a fatal map load, so register
before editing GSC, then run
`python tools/codol_script_resolve.py --root bin/home/codol_rawfiles --only zm`
(and re-seed it if it keeps its own builtin list).

### I.4 — the GSC (SPEC ONLY; `_zombiemode.gsc` is owned by another agent)

**Spawn.** In `giveStartingLoadout()`
(`bin/home/codol_rawfiles/zm/maps/mp/gametypes/_zombiemode.gsc:625-641`), after
`self switchToWeapon( level.zombie_start_weapon );`:

```
	// C1 takes the melee animation, damage, range and knife models from a row
	// of mp/coKnifeStatsTable.csv selected by ps+0x338, not from the held
	// weapon -- which is why 22 of the 40 roster guns ship with an empty
	// animation slot 7 (def+0xbf0 = 0, "does not own its melee anims").
	// Row 13 zknife_standard is the zombies knife; row 14 zknife_bowie is the
	// Bowie upgrade.  See docs/CODOL_MELEE_SERVER_AUDIT_20260920.md.
	if ( !isDefined( self.zombie_knife_type ) )
		self.zombie_knife_type = "zknife_standard";

	self codol_setKnifeType( self.zombie_knife_type );
```

Keeping the row on `self.zombie_knife_type` rather than calling with a literal
is what makes the Bowie survive respawn and Last Stand — the T5 equivalent of
`self.current_melee_weapon`.

**Bowie purchase.** T5's `_zombiemode_bowie.gsc` `do_bowie_flourish_end()`
(`:200-231`) becomes, in CoDOL terms, a **row swap plus the same two
side-effects**:

```
// T5 maps\_zombiemode_bowie.gsc:173 do_bowie_flourish_end.  T5 swaps the
// carried weapon knife_zm -> bowie_knife_zm; C1 has no such weapons and
// instead swaps the coKnifeStatsTable row 13 -> 14, which is the same
// WaW/BO1 mechanic expressed as a row.  zknife_bowie is row 14, inline in
// the shipped table; rows 13..16 are gated on g_gametype starting "zm",
// which our serverinfo satisfies.
give_bowie()
{
	if ( isDefined( self.zombie_knife_type ) && self.zombie_knife_type == "zknife_bowie" )
		return;

	self.zombie_knife_type = "zknife_bowie";
	self codol_setKnifeType( self.zombie_knife_type );

	// T5 :200-231 also reskins a CARRIED Ballistic Knife.  Both names are
	// real assets in common_gametype_zm.
	if ( self hasWeapon( "knife_ballistic_zm" ) )
	{
		self notify( "zmb_lost_knife" );
		self takeWeapon( "knife_ballistic_zm" );
		self giveWeapon( "knife_ballistic_bowie_zm" );
	}
	else if ( self hasWeapon( "knife_ballistic_upgraded_zm" ) )
	{
		self notify( "zmb_lost_knife" );
		self takeWeapon( "knife_ballistic_upgraded_zm" );
		self giveWeapon( "knife_ballistic_bowie_upgraded_zm" );
	}
}
```

Builtins used are all registered: `hasweapon` (`scr_vm_main.c:551`),
`takeweapon` (`:542`), `giveweapon` (`:541`).

The wall trigger itself (T5 `bowie_init()` / `bowie_think(cost)`, entities
`GetEntArray("bowie_upgrade","targetname")`, default 3000 points, the
`zombie_bowie_flourish` presentation weapon at window index 122) is a separate,
larger port and is deliberately not specified here. **Unverified: whether our
zm maps place `bowie_upgrade` trigger entities at all** — check
`docs/zone_assets/ALL_addon_map_ents.txt` / the map ents before building the
trigger side. The row swap works from any caller, so a devgui/testing hook can
prove it before the wall exists.

**Not needed:** the Part B `register_melee_weapon_for_level` /
`get_/set_player_melee_weapon` subsystem from Addendum 1 §G.3 is withdrawn
along with R1. `self.zombie_knife_type` replaces it in two lines.

---

## J. R3 CORRECTED — the gate already exists, does NOT work, and costs slots

**The patch the brief asks for is already in the tree.** MEASURED,
`bin/home/codol_rawfiles/zm/maps/mp/gametypes/_zombiemode_weapons.gsc:75-87`,
inside `add_zombie_weapon` itself, so it already covers all 40 entries:

```
	precacheItem( weapon_name );
	if ( getWeaponIndexFromName( weapon_name ) <= 0 )
		return;

	if ( isDefined( upgrade_name ) )
	{
		precacheItem( upgrade_name );
		if ( getWeaponIndexFromName( upgrade_name ) <= 0 )
			upgrade_name = undefined;
	}
```

**But it does not do what its own header comment claims**, and the two
`thundergun_zm` warnings in `qconsole.log.old:279-280` are the proof — one per
`getWeaponIndexFromName` call, base and upgrade. Traced:

1. `precacheItem` is safe: `CODOL_Scr_PrecacheItem`
   (`src/codol/script/codol_script_precache.c:20-28`) probes with
   `CODOL_LoadMountedNullWeapon` / `CODOL_LoadMountedNativeWeapon`, and on
   status 0 returns **before** `Scr_PrecacheItem()`. No registration, no
   warning.
2. `getWeaponIndexFromName` is **not** safe. `scr_vm_main.c:445` binds it to
   `CODOL_Scr_GetWeaponIndexFromName`
   (`codol_script_weapon_queries.c:182-185`), which is a bare
   `G_GetWeaponIndexForName(...)` — the **registering** path.
3. `BG_GetWeaponIndexForName` (`src/asmsource/_bg_weapons.asm:5098`) calls
   `BG_LoadWeaponDef_FastFile` (`:247`), which is only
   `DB_FindXAssetHeaderReal(0x17, name)`. **Neither has a default-asset
   check** — I read both. `_bg_weapons.asm:5140-5163` then unconditionally
   `inc bg_lastParsedWeaponIndex`, stores the returned def into
   `bg_weaponDefs[]`, and returns that **non-zero** index.
4. Our `db_load.cpp:3499-3503` returns the **`defaultweapon_mp` definition**
   for a name in no mounted zone (that is where the warning is printed).

So `getWeaponIndexFromName("thundergun_zm")` returns a **non-zero** index and
`thundergun_zm` **stays in the mystery-box pool**, backed by a clone of
`defaultweapon_mp`. Consequences:

* A box roll can hand the player "Thundergun" and give them the default weapon.
* Each probe **burns a native weapon-definition slot** and a
  publish/republish cycle — two per absent roster entry.
* It puts an `_mp` asset's *definition* into a zm match under a zm name, which
  is exactly the contamination the user forbade. (The `defaultweapon_mp` *name*
  at CS 5363 remains vanilla-correct and untouched; this is a different thing —
  its **def body** standing in for `thundergun_zm`.)

The comment at `_zombiemode_weapons.gsc:53-57` asserting that
"`getWeaponIndexFromName` only answers non-zero afterwards for a name the zones
really carry" is **false**, and should be corrected in the same edit.

### J.1 The correct fix

`add_zombie_weapon` needs a test that **neither registers nor depends on wire
state**. Two options:

**Option A (recommended) — a new find-only builtin.** Add
`codol_isweaponmounted(name)` wrapping exactly what
`CODOL_Scr_PrecacheItem` already does internally
(`CODOL_LoadMountedNullWeapon` then `CODOL_LoadMountedNativeWeapon`; status 1 =
present). Pure asset presence: no registration, no slot cost, no dependence on
the engine->wire map having been refreshed yet.

**Option B — reuse the existing `codol_isweaponpublished`**
(`scr_vm_main.c:447` -> `CODOL_WeaponAlreadyLive`, `codol_weapon_budget.c`),
which *is* find-only. **Risk, flagged:** it also requires
`CODOL_WeaponToWire(engine) > 0`, i.e. that the engine->wire map has already
been refreshed. `init_weapons()` runs at map script init, before the first
gamestate, so the map may be stale there and the test could return 0 for a
perfectly good weapon — which would empty the **entire** roster, not just
thundergun. Do not take Option B without checking the refresh ordering first.

### J.2 Patch spec, Option A GSC side

File: `bin/home/codol_rawfiles/zm/maps/mp/gametypes/_zombiemode_weapons.gsc`.

**Line endings:** MEASURED — `tr -cd '\r'` = **0**, `tr -cd '\n'` = **810**,
identical in `git show HEAD:`. Pure LF. Indentation is **hard tabs**.

**Anchor (exact; hard tabs, LF):**

```
	precacheItem( weapon_name );
	if ( getWeaponIndexFromName( weapon_name ) <= 0 )
		return;

	if ( isDefined( upgrade_name ) )
	{
		precacheItem( upgrade_name );
		if ( getWeaponIndexFromName( upgrade_name ) <= 0 )
			upgrade_name = undefined;
	}
```

**Replacement:**

```
	// getWeaponIndexFromName is the REGISTERING lookup: for a name no mounted
	// zone carries, db_load.cpp:3499 substitutes the defaultweapon_mp
	// definition, BG_GetWeaponIndexForName (_bg_weapons.asm:5140) appends it
	// and returns a NON-ZERO index, so the old guard let thundergun_zm stay in
	// the box pool backed by the default weapon -- and burned a weapon slot
	// per probe.  codol_isWeaponMounted is the find-only asset test
	// CODOL_Scr_PrecacheItem already uses internally: it registers nothing.
	if ( !codol_isWeaponMounted( weapon_name ) )
		return;

	precacheItem( weapon_name );

	if ( isDefined( upgrade_name ) )
	{
		if ( codol_isWeaponMounted( upgrade_name ) )
			precacheItem( upgrade_name );
		else
			upgrade_name = undefined;
	}
```

Also correct the stale claim in the file header, `:53-57`:

* old: `getWeaponIndexFromName only answers non-zero afterwards for a name the zones really carry`
* new: `codol_isWeaponMounted answers only for a name a mounted zone really carries; getWeaponIndexFromName must NOT be used as that test, because it registers the defaultweapon_mp substitute and returns a non-zero index for a missing weapon`

After applying: `python tools/codol_script_resolve.py --root bin/home/codol_rawfiles --only zm` must exit 0 (register the builtin first).

**Expected effect:** the two `thundergun_zm` warnings disappear, two weapon
slots per absent entry stop being consumed, and the box can no longer roll a
weapon the map does not ship. It has no bearing on melee.

---

## K. mp constant-window work: proposal only

Addendum 1 §E parts 2 and 3 (move mp onto the constant window; fill the 22
holes) stay a **documented proposal**. Picking hole fillers wrong is an
`ERR_DROP`, not a degradation, so it needs a live mp connect to validate and
must not be landed blind. §E part 1 (make the mp branch set `stopped_name` so
it warns, and warn when the attachment table yields no names) is independent,
carries no client risk, and can land on its own.
