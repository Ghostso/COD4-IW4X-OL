# zm prompts, score tracking and the weapon limit -- 2026-09-20

Scope: `bin/home/codol_rawfiles/zm/**` only. No `src/**` file was touched; the
one native observation that matters to another owner is in "Handoffs" at the
end. Every claim is labelled MEASURED or INFERRED.

Reported by the user from a live `zm_prototype_sh` match:

1. "the prompts are not using the game's localized strings"
2. "not sure whether the score is tracked or not"
3. "appears I was able to get 3 guns without mule kick"

plus a batch of GSC runtime errors handed over mid-task.

---

## 1. Localization -- the brief's premise was wrong, in our favour

The task brief said the keys "are CoDOL's, NOT T5's (`ZOMBIE_*` WaW/T5 keys
will not exist here)".

**MEASURED, and the opposite is true.** `docs/zone_assets/ALL_localize.txt`
carries **458 distinct `ZOMBIE_*` keys in `localized_code_post_gfx_mp` alone**,
and the same set again in `zm_prototype_sh` and `zm_zombie_training`. CoDOL
ships Treyarch's zombies localize table effectively verbatim -- including the
cost-suffixed families that T5's hint registry is built around:

| family | steps CoDOL ships | T5 registers |
|---|---|---|
| `ZOMBIE_BUTTON_BUY_OPEN_DOOR_<n>` | 100 200 250 500 750 1000 1250 1500 1750 2000 **2500** | all but 2500 |
| `ZOMBIE_BUTTON_BUY_OPEN_AREA_<n>` | 100 200 250 500 750 1000 1250 1500 1750 2000 **2500** | all but 2500 |
| `ZOMBIE_BUTTON_BUY_CLEAR_DEBRIS_<n>` | 100 200 250 500 750 1000 1250 1500 1750 2000 | same |
| `ZOMBIE_BUTTON_BUY_BACK_BARRIER_<n>` | 10 20 50 100 | same |
| `ZOMBIE_BUTTON_REWARD_BARRIER[_<n>]` | base, 10 20 30 40 50 | same |
| `ZOMBIE_RANDOM_WEAPON_<n>` | **650 750 850** 950 | 950 only |

Zone mounting is not a problem: `localized_code_post_gfx_mp` is a base zone the
client always mounts, so every key resolves on all three zm maps -- including
`zm_asylum_sh`, which MEASURED ships **no localize assets of its own**
(`ALL_localize.txt` has zero rows for that zone).

### Keys adopted, per prompt

| prompt | was (hardcoded English) | now | ships in |
|---|---|---|---|
| rebuild barrier | `Hold [{+activate}] to Rebuild Barrier` | ref `default_reward_barrier_piece` to `&"ZOMBIE_BUTTON_REWARD_BARRIER"` | post_gfx + both zm map zones |
| open door | `... to Open Door [Cost: N]` | ref `"default_buy_door_" + cost` to `&"ZOMBIE_BUTTON_BUY_OPEN_DOOR_<n>"` | same |
| remove debris | `... to Remove Debris [Cost: N]` | ref `"default_buy_debris_" + cost` to `&"ZOMBIE_BUTTON_BUY_CLEAR_DEBRIS_<n>"` | same |
| needs power | `Requires Power` | `&"ZOMBIE_NEED_POWER"` | same |
| power switch | `... to Turn On Power` | `&"ZOMBIE_ELECTRIC_SWITCH"` | same |
| buy perk | `... to Buy <name> [Cost: N]` | `perk_hint(perk, solo)`, cost as `&&1` | same |
| Pack-a-Punch | `... to Pack-a-Punch [Cost: N]` | `&"ZOMBIE_PERK_PACKAPUNCH", cost` | same |
| wall buy / ammo | `... to Buy <weapon> [Cost: N]` | `&"ZOMBIE_WEAPONCOSTAMMO", cost, ammo_cost` | same |
| mystery box | `... for Mystery Box [Cost: N]` | ref `"default_treasure_chest_" + cost`; cost 10 (fire sale) to `&"ZOMBIE_FIRE_SALE_COST"` | same |
| box swap | `... to Swap for <weapon>` | `&"ZOMBIE_SWITCH_WEAPON"` | same |
| **revive** | `... to Revive` | **`&"PLATFORM_REVIVE"`** | `localized_code_post_gfx_mp` |

Per-perk keys, all MEASURED-shipped:
`specialty_armorvest` to `ZOMBIE_PERK_JUGGERNAUT`;
`specialty_quickrevive` to `ZOMBIE_PERK_QUICKREVIVE` / `..._SOLO`;
`specialty_fastreload` to `ZOMBIE_PERK_FASTRELOAD`;
`specialty_rof` to `ZOMBIE_PERK_DOUBLETAP`;
`specialty_longersprint` to `ZOMBIE_PERK_MARATHON`;
`specialty_flakjacket` to `ZOMBIE_PERK_DIVETONUKE`;
`specialty_deadshot` to `ZOMBIE_PERK_DEADSHOT`;
`specialty_additionalprimaryweapon` to `ZOMBIE_PERK_ADDITIONALPRIMARYWEAPON`;
fallback `ZOMBIE_PERK_GENERIC`.

### C1 vs T5 conflicts, and which side won

* **Revive prompt. C1 WON.** T5 has no `_zombiemode_laststand` revive key worth
  porting; CoDOL's own shipped mp tree uses `&"PLATFORM_REVIVE"` for exactly
  this prompt (MEASURED,
  `bin/home/codol_rawfiles/maps/mp/gametypes/_damage.gsc:1875` and `:1905`, the
  `dieHardMode` revive entity). The in-repo working idiom was taken over any
  T5 zombies key.
* **`&"ZOMBIE_UNDEFINED"`. C1 WON.** It is the one key of T5's hint set CoDOL
  does **not** ship (MEASURED). T5's `get_zombie_hint()` falls through to it;
  ours returns `undefined` and each caller names a shipped generic instead
  (`ZOMBIE_OPEN_DOOR`, `ZOMBIE_CLEAR_DEBRIS`, `ZOMBIE_BUY_WEAPON` -- all
  MEASURED-shipped).

### Keys that do NOT ship -- reported, not papered over

* **`ZOMBIE_UNDEFINED`** -- handled above.
* **Per-weapon wall-buy names.** CoDOL ships a `ZOMBIE_WEAPON_*` family, but it
  is Treyarch's weapon roster, not CoDOL's zm roster. MEASURED gaps against
  this tree's `init_weapons()` table: **`glock_zm`, `glockdw_zm`, `ak104_zm`,
  `tavor_zm`, `m4a1tech_zm`, `as50_zm`, `l86_zm`, `c4_zm`** have no
  `ZOMBIE_WEAPON_*` counterpart. Because the set is incomplete, the wall buy
  uses T5's own generic `&"ZOMBIE_WEAPONCOSTAMMO"` (cost + ammo cost as `&&1`
  / `&&2`), which names no weapon and therefore has no gap. Wiring the
  per-weapon names would be a partial job and is deliberately **not** done.
* INFERRED, not verifiable from here: the *values* behind these keys. The zone
  listing gives names only. Whether each Chinese string's `&&1`/`&&2` slots
  match the argument count passed is unverified by tooling and must be read off
  a live screenshot.

### Mechanism

T5's registry is ported verbatim into
`zm/maps/mp/gametypes/_zombiemode_utility.gsc` -- `add_zombie_hint(ref, text)`
(precaches and stores) and `get_zombie_hint(ref)`. `set_hint_string()` gains a
third parameter, `fallback_ref`, in place of T5's `ZOMBIE_UNDEFINED`. All
registrations live in a new `init_hints()` in
`zm/maps/mp/gametypes/_zombiemode.gsc`, called from `init()`.

The in-repo reference idiom (`precacheString( &"KEY" )` then
`setHintString( &"KEY" )`) is what the shipped mp tree does --
`common_scripts/_elevator.gsc:17,880`, `common_scripts/_sentry.gsc:71,190`.

**Variadic hint arguments are supported. MEASURED** from the engine, not
assumed: `GScr_SetHintString` in `src/asmsource/_g_scr_main_mp.asm` calls
`Scr_GetNumParam`, subtracts one, and hands the remainder to
`Scr_ConstructMessageString`, so `setHintString( &"KEY", cost )` substitutes
`&&1`. (The same routine caps the hint-string configstring pool at 32 distinct
rendered strings, which the cost-suffixed scheme should stay well inside.)

---

## 2. Is the score tracked? -- evidenced, and the answer is "awarded: no; spent: yes"

### Method

Script runtime errors on this engine do **not** kill the running thread -- they
print and execution resumes at the next statement (MEASURED two ways: the
hudelem error at `_zombiemode_score.gsc:267` is followed by another at `:268`
in the same call, which is impossible if the thread died; and the actor spawn
continues past its own failing line to thread `zombie_think`). That makes the
now-fixed `user_right` / `user_bottom` hudelem errors an accidental but exact
**execution tracer**: `create_highlight_hud()` cannot run without logging two
errors, and it is reached only from `score_highlight()`, which
`set_player_score_hud()` threads only when `score_diff != 0`.

### The measurement

From `bin/home/main/qconsole.log`:

| stack frame | occurrences | meaning |
|---|---|---|
| `_zombiemode_score.gsc:267/268` (`score_hud_init`) | 2 + 2 | the purse hudelem was created -- **the HUD exists** |
| `_zombiemode_score.gsc:316/317` (`create_highlight_hud`) | 5 + 5 | **5 non-zero score changes** |
| `_zombiemode_score.gsc:231` (`minus_to_player_score`) | 10 | all 5 changes were **spends** |
| `_zombiemode_score.gsc:218` (`add_to_player_score`) | **0** | **no award ever moved the purse** |
| `_zombiemode_score.gsc:200` (`player_reduce_points`) | **0** | no penalty either |

### Verdict

**The HUD works and the spend path works. The award path did not fire once in
that match.** This is not "unverifiable" -- `add_to_player_score` has a
zero-occurrence count against a tracer that is unconditional on every call, and
the two paths share the same hudelem budget guard, so budget exhaustion cannot
explain the asymmetry.

### Root cause: NOT the notify signature

The brief named the INFERRED notify parameters as the prime suspect. **MEASURED
from the engine, they are correct and the port reads them exactly right:**

* `"damage"` on a non-client entity (`src/asmsource/_g_combat_mp.asm`, the
  `G_Damage` non-client path) pushes ten arguments; reversed (this VM binds
  last-pushed to parameter one, stated at
  `src/codol/script/codol_equipment_lifecycle.c:10-12`) they are exactly
  `amount, attacker, direction, point, mod, modelName, tagName, partName,
  flags, weapon`.
* `"death"` on the same path pushes one argument, `attacker`.

So `_zombiemode_spawner.gsc`'s `waittill` lists are right, and the open question
recorded at `docs/CODOL_ZOMBIES_LOOP_20260920.md:465-468` is **now closed as
correct**.

The remaining explanation consistent with both notifies being silent is that
`G_Damage` was never reached for these actors. Corroborating MEASURED evidence
in the same log: **354 `moved 0/s` lines** and
`route FAILED (no waypoint graph) ... 0 graph nodes` -- the zombies were
completely static for the whole match. Whether they were also untouchable is
the open half.

### Three real defects fixed on the way

1. **Hudelem alignment (the tracer itself).** `user_right` / `user_bottom` /
   `user_left` / `user_top` are T5 values; this engine's legal sets are
   enumerated at `src/g_shared.h:655-680`. Replaced with `right` / `bottom` /
   `left` / `top`, which preserves the intended corner because the offsets are
   already negative (`x = -103`, `y = -71`). MEASURED that this is the in-repo
   idiom: the mp tree uses plain `right` 37x and `bottom` 22x and contains
   **zero** `user_*` values -- all six were this tree's alone. 6 sites in
   `_zombiemode_score.gsc` and `_zombiemode_utility.gsc`. Every remaining
   hudelem field in the zm tree was swept; `fontScale` is already 1.5-3, inside
   the 0.0..6.3 wire range, and `alignX`/`alignY` were already legal.
2. **The hit-location bonus never scored.** `player_add_points_kill_bonus()`
   switched on T5 `hitLocation_t` names (`"head"`, `"neck"`, `"torso_upper"`),
   but the value reaching it is the notify's 8th argument `partName`, which is
   the **bone** const string from the bullet trace -- `hitLoc` itself is never
   pushed. MEASURED bone names on the shipped `c_zom_*_body` models are
   `j_head`, `j_neck`, `j_spine4`, `j_spineupper`, `j_spinelower`, `j_helmet`.
   Those cases were added; the T5 names are kept as aliases.
3. **Dead-code attacker fallback.** `zombie_death_event`'s
   `if ( !isDefined( attacker ) )` can never be true: MEASURED, `G_Damage`
   substitutes `g_entities[2046]` (the world entity) for a NULL attacker
   *before* pushing the notify, so `attacker` is always defined and world kills
   arrive as a defined non-player. Changed to `!isPlayer( attacker )`.

### The diagnostic

So the next live test answers this outright rather than by inference, three
always-on probes were added (no dvar, no kill switch -- per the standing
no-flag-proliferation rule):

* `CoDOL zm DIAG damage notify #N: ...` -- first 5 actor damage notifies, every
  parameter stringified safely. Says immediately whether the notify arrives at
  all and whether `attacker` is a player.
* `CoDOL zm DIAG death notify #N: ...` -- first 5, both the argument and the
  cached `.attacker`.
* `CoDOL zm DIAG award: event=... points=... count=... purse=...` -- a ledger in
  `player_add_points`, printing the first award of each event type then every
  25th.

Reading it: **no `DIAG damage` lines at all** means damage never reaches the
actor (pathing/collision, not scoring). **`DIAG damage` with
`attacker=ent(...)` instead of `attacker=PLAYER`** means the credit is going
somewhere else. **`DIAG award` lines with a rising purse** means the economy
works and only the readout was ever in doubt.

---

## 3. Three weapons without Mule Kick -- found and fixed

**MEASURED root cause: `weapon_give()` had no limit at all.**

```
weapon_give( weapon_name )
{
	self giveWeapon( weapon_name );      // <- no limit check anywhere
	self giveMaxAmmo( weapon_name );
	self switchToWeapon( weapon_name );
}
```

T5's `weapon_give()` (`maps/_zombiemode_weapons.gsc:2370-2412`) opens with the
limit and every purchase path funnels through it:

```
primaryWeapons = self GetWeaponsListPrimaries();
weapon_limit = 2;
if ( self HasPerk( "specialty_additionalprimaryweapon" ) ) weapon_limit = 3;
if ( primaryWeapons.size >= weapon_limit ) { ...take getCurrentWeapon()... }
```

The two paths here had **drifted apart**: the wall buy (`weapon_give`) was
unbounded, while the mystery box (`treasure_chest_give_weapon`) open-coded a
*different* rule -- always swap the held weapon, but never the starting pistol.
That combination is exactly the reported bug: start pistol + one wall buy + one
box pull = three primaries, with Mule Kick nowhere in it.

Fix: T5's rule, in two new functions in `_zombiemode_weapons.gsc` --
`player_weapon_limit()` and `enforce_weapon_limit(new_weapon)` -- called from
`weapon_give()`, and `treasure_chest_give_weapon()` reduced to a call to
`weapon_give()` so the two paths can never diverge again. Re-buying a weapon
already held is not a new slot. The unconditional starting-pistol exemption is
**removed**: T5 does not have it (it records `last_pistol_swap` for `m1911_zm`
and takes it anyway), and keeping it would reintroduce the stack whenever the
pistol is what is in hand.

`getWeaponsListPrimaries()` covers only primary slots, so grenades, claymores
and bouncing betties are excluded by the engine -- which is why T5's
`is_placeable_mine()` / `is_equipment()` / `is_offhand_weapon()` guards are not
needed, and just as well: MEASURED, none of the three exists in this tree.

### Does Mule Kick exist in CoDOL?

**Partly, and the honest answer is "the name yes, the perk unproven".**

* MEASURED shipped: the localized name
  `ZOMBIE_PERK_ADDITIONALPRIMARYWEAPON` and `ZOMBIE_PERKPOP_ADDITIONALPRIMARY`
  (`ALL_localize.txt`); the bottle weapon
  `zombie_perk_bottle_additionalprimaryweapon` and the power-up
  `perkpop_additionalprimary_zm` (`ALL_weapon.txt`, `common_gametype_zm`).
* MEASURED absent: the specialty string
  `"specialty_additionalprimaryweapon"` appears **nowhere** in `src/**` or in
  the shipped mp rawfiles. Whether CoDOL's `mp/coPerkStatsTable.csv` carries it
  could not be read from here (it lives inside a fastfile).
* Consequence, MEASURED from `src/codol/script/codol_script_perks.c:40-53`: an
  unknown perk name is reported once in developer mode and **treated as
  absent**, returning 0 from `hasPerk` without erroring. So if CoDOL's table
  lacks it, the limit simply stays at the base two -- which still fixes the
  reported bug and never throws. The two-weapon base rule is enforced
  regardless, exactly as asked.

---

## 4. The handed-over runtime errors

| # | error | count | status |
|---|---|---|---|
| 1 | `"user_right"/"user_bottom"` not valid hudelem align | 14 | **FIXED** -- see 2 above; 6 sites, plus `user_left`/`user_top` the brief did not list |
| 2 | `tag 'tag_eye' does not exist on entity with model 'c_zom_ger_body1'` | 12 | **FIXED** -- real root cause below |
| 3 | `unknown sound alias 'zmb_no_purchase'` | 11 | **FIXED** -- 4 aliases, all remapped to shipped CoDOL names |
| 4 | `ai setMoveSpeedScale( ai move_speed_scale() )` | 12 | **FIXED** -- builtin is player-only; no actor equivalent exists |
| 5 | `precacheItem must be called before any wait statements` | 2 | **FIXED** (not in the brief) |
| 6 | `cannot set field of removed entity` | 1 | **FIXED** (not in the brief) |

### 2. tag_eye -- the error was a symptom; zombies had no head

A bone dump of the shipped zm fastfiles (MEASURED, read-only, via the
`obj/harrier-model-audit/scan.py` idiom already used by the killstreak audit):

* every `c_zom_*_body` model carries **73 bones and no `tag_eye`** -- the
  head-region bones it does have are `j_head`, `j_head_end`, `j_neck`,
  `j_helmet`;
* every `c_zom_*_head` model carries **29 bones that DO include `tag_eye`**,
  plus `j_eyeball_le` / `j_eyeball_ri`;
* all four body variants share one identical skeleton, as do the heads.

`character_zm_zombie.gsc` was doing `self.headModel = heads[index]` **with no
`attach` call**. MEASURED: `headModel` is a script field the engine never reads
(zero hits for `headmodel` across `src/**`); `attach()` is what merges the
head's bones into the entity DObj, and it is registered
(`src/scr_vm_main.c:739`). The shipped stock helper
`codescripts/character.gsc:32-33` does both.

So the zombies were spawning **with no head model attached at all**, and
`tag_eye` was missing because the bone that carries it was never there. Fixed by
adding `self attach( heads[ index ], "", true );`. The eye-glow FX is kept
unchanged -- no tag was invented, and none had to be.

Related MEASURED note worth keeping: `ActorEye()`
(`src/codol/player/codol_actor_lifecycle.cpp:1022-1029`) asks for `tag_eye` and
**silently falls back to `origin + (0,0,64)`**, which is why `getEye()` never
errored and hid this. `playFxOnTag` has no such fallback, which is the only
reason it surfaced.

### 3. Sound aliases

Every alias in the zm tree was checked against `docs/zone_assets/ALL_sound.txt`,
not just the one that logged: **37 distinct aliases, 33 ship, 4 did not.**

| T5 alias (absent) | CoDOL alias used | ships in |
|---|---|---|
| `zmb_no_purchase` | `zmb_no_cha_ching` | `common_gametype_zm` |
| `zmb_perks_deny` | `evt_perk_deny` | `common_gametype_zm` |
| `zmb_perks_bottle_dispense` | `evt_bottle_dispense` | `common_gametype_zm` |
| `zmb_debris_move` | `zmb_debris_clear` | `common_gametype_zm` |

These are name-matches in the shipped table, each the single best candidate and
each in a mounted zone -- INFERRED equivalence, not auditioned. `zmb_no_cha_ching`
is the strongest: this tree's positive purchase sound is `zmb_cha_ching`, and
CoDOL ships the negated twin under the same stem. Naming note worth recording:
**CoDOL re-homed part of the perk SFX set out of `zmb_*` into `evt_*`**
(`evt_perk_deny`, `evt_perk_swallow`, `evt_perk_bottle_open`,
`evt_bottle_dispense`) and the perk jingles into `mus_perks_*` -- search those
prefixes before concluding a zombies alias is absent.

All 33 survivors resolve in `common_gametype_zm`,
`patch_common_gametype_zm` or `localized_common_gametype_zm`, all three of which
a zm match mounts (MEASURED,
`docs/CODOL_CATEGORY_ASSET_TEARDOWN_20260917.md:161-167` quoting a real client
load). No zone-scope problem among them.

**Two silent dead refs found and left as findings** (they hit the
`!isDefined(level.zombie_sounds[ref])` early return, so they log nothing and
play nothing): `"zombie_scrape"` (`zm/maps/mp/animscripts/zombie_shared.gsc:155`)
and `"zombie_teardown"` (via `do_zombies_playvocals("teardown")`,
`_zombiemode_spawner.gsc:1075`). Neither ref is ever registered by `add_sound`.
Not fixed here -- picking their aliases is a separate audition job.

### 4. setMoveSpeedScale is player-only

MEASURED: the error was not "unknown function" but
`only valid on players; called on entity N ... classname actor_enemy_zombie_zm`.
`setmovespeedscale` **is** registered as a method (`src/scr_vm_main.c:867`), but
its handler calls `GetPlayerEntity` first and writes
`client->sess.moveSpeedScaleMultiplier`, so it rejects anything without a
client. There is no actor speed-scale builtin on this server.

`move_speed_scale()` itself is innocent -- it returns only 0.5, 0.9 or 1.4.

Fixed with a new `apply_move_speed_scale( scale )` used at **all four actor
call sites**, not just the one that logged. The brief named one; a sweep found
three more that would throw identically and had simply not been reached yet:

| site | why it had not fired |
|---|---|
| `_zombiemode_spawner.gsc:365` (`spawn_zombie`) | the logged one, 6 per spawn wave |
| `_zombiemode_spawner.gsc` (`zombie_think`) | needs `needs_run_update`, never raised in that match |
| `_zombiemode_spawner.gsc:630` (`make_crawler`) | needs a legs gib |
| `_zombiemode_spawner.gsc:912` (straggler sprint) | needs a late-round straggler |

The crawler site passes T5's 0.35 explicitly, since that is lower than any
bucket `move_speed_scale()` returns. The three `setMoveSpeedScale` calls that
remain in the zm tree (`_zombiemode.gsc:588`, `_zombiemode_laststand.gsc:152`
and `:436`) are on **players** and are correct.

It scales
`self.moveplaybackrate`, which is the lever that actually moves an actor here:
actor translation is pure animation root motion
(`CODOL_ActorAdvanceGoalAnimation` -> `XAnimCalcDelta`, no speed multiplier
anywhere in the actor sources), `animplaybackrate` is a registered actor class
field (`src/codol/player/codol_actor_lifecycle.cpp:194`), and the zm move
animscript already drives off `self.moveplaybackrate`
(`zm/maps/mp/animscripts/zombie_move.gsc:105,122`). Normalised on 0.9, the
`"run"` value, so a running zombie keeps exactly the rate it was assigned.

### 5 & 6. Two errors the brief did not list

* `precacheItem must be called before any wait statements in the gametype or
  level script` x2, at `_zombiemode_perks.gsc:218` -- `precacheItem( bottle )`
  sat *after* `level waittill( perk + "_power_on" )`. Hoisted: a new
  `precache_perk_bottles()` precaches all eight bottles from `init_hints()`,
  inside the precache window.
* `cannot set field of removed entity` x1, at `_zombiemode_blockers.gsc:596`
  (`self._door_open = true`) -- the door trigger can be deleted while the
  thread sits between its `waittill` and the assignment. Guarded with
  `if ( !isDefined( self ) ) return;`.

---

## 5. Gate results

Both mandatory gates clean, after every change:

```
zm:  builtins registered: 949 | scripts in effective tree: 1200 | lowered: 121
     every reachable script resolves against the registered builtin table
mp:  builtins registered: 949 | scripts in effective tree: 1174 | lowered: 108
     every reachable script resolves against the registered builtin table
```

mp held at the required 108. Line endings verified LF across all 27 zm `.gsc`
files (`tr -cd '\r' | wc -c` == 0 for each).

Hand-checked because the gate cannot see them:

* every localize key used was confirmed present in `ALL_localize.txt` together
  with its zone;
* every sound alias was confirmed present in `ALL_sound.txt` with its zone;
* no `%anim` reference was added or changed;
* `array()` is **not** a registered builtin here, so `perk_list()` builds its
  list by assignment.

## 6. Files changed

All under `bin/home/codol_rawfiles/zm/`:

* `character/character_zm_zombie.gsc` -- attach the head model
* `maps/mp/gametypes/_zombiemode.gsc` -- `init_hints()`, bottle precache
* `maps/mp/gametypes/_zombiemode_utility.gsc` -- hint registry, diag helpers, align
* `maps/mp/gametypes/_zombiemode_blockers.gsc` -- prompts, aliases, removed-entity guard
* `maps/mp/gametypes/_zombiemode_laststand.gsc` -- revive prompt
* `maps/mp/gametypes/_zombiemode_perks.gsc` -- prompts, `perk_hint`, precache hoist, aliases
* `maps/mp/gametypes/_zombiemode_power.gsc` -- power switch prompt
* `maps/mp/gametypes/_zombiemode_score.gsc` -- align, bone-name bonus, award ledger
* `maps/mp/gametypes/_zombiemode_spawner.gsc` -- move speed, attacker gate, diag probes
* `maps/mp/gametypes/_zombiemode_weapons.gsc` -- prompts, **weapon limit**

No `src/**` file was touched.

## 7. Handoffs

* **No native patch is required by this work.** The `setMoveSpeedScale` failure
  is resolved entirely in GSC; no new builtin is needed.
* **For the actor/snapshot owner:** MEASURED in the same log, 354 `moved 0/s`
  lines and `route FAILED (no waypoint graph) ... 0 graph nodes` -- the zombies
  did not move at all for the whole match. That is very likely why the score
  award path never fired, and it is outside `zm/**`.
* **For whoever owns the mp equipment tree:** MEASURED transposition at
  `bin/home/codol_rawfiles/maps/mp/equipment/_bouncingbetty.gsc:139`, which
  names the damage notify's arguments 7 and 8 as `part, tag` where the engine
  sends `modelName, tagName, partName`. Same notify, separate bug, not mine to
  fix.
* **Doc correction:** `docs/CODOL_ZOMBIES_LOOP_20260920.md:465-468` flags the
  actor damage/death notify parameters as INFERRED. They are now MEASURED and
  correct; that line can be upgraded, citing the `G_Damage` push sequence in
  `src/asmsource/_g_combat_mp.asm`.
