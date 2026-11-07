# Headless bots and the red FAL — cause, evidence, fix (2026-09-15)

Two reported visual defects on the `Training N` combat-training bots:

* **(A)** some bots draw with no head;
* **(B)** a red placeholder draws on the FN FAL those bots carry.

Both were traced to the same shape of defect: a shipped table row that is
*selectable* but not *buildable*, accepted silently by a producer that has no
availability check. Neither is an FX bug and neither is a snapshot bug.

All offline table evidence below was read out of the shipped fastfiles with
`D:/CoD/CODOL Builds/Call of Duty Online 1.1.1.13/CODOL/1.1.1.13_server/alpha0022/zone_assets.py`.
Stringtable blobs decode as
`{u32 namePtr, u32 cols, u32 rows, u32 valuesPtr, name\0, cells[rows*cols]{u32 strPtr, u32 hash}, inline strings}`
with the case-insensitive hash `h = h*31 + tolower(c)`; cells whose pointer is
not `0xFFFFFFFF` were emitted earlier in the zone and were recovered by hashing
candidate strings, which is how the `coCharItems` key column was read.

---

## (A) Missing heads

### What is actually published

The bot path is `codol_applyBotCharacter`
(`scripts/codol/maps/mp/gametypes/_teams.gsc:618`), which
reaches `character()` in
`src/codol/player/codol_bot_loadout.c`. It reads
`mp/botClassTable.csv`'s `charXXX` columns for `tf` and `charXXX_sc` for `sc`,
resolves each name through `mp/coMarketplaceItems.csv`, and selects a model per
slot with `CODOL_LoadCharacterItemModels` → `CODOL_CharacterVariant`.

`CODOL_CharacterVariant`
(`src/codol/assets/codol_character_variant.c`) is a faithful
port of C1 `0x729090`. Verified against the image this pass:

| C1 | behaviour |
| --- | --- |
| `0x729097`, `0x7290ad` | running best starts at **-1**, so a row must score **> -1** |
| `0x729416..0x729424` | `key[0]` must equal the gender char (score -1) or be `'s'` (-2), else the row is **skipped** |
| `0x72942f..0x729452` | `key[2..3]` must equal this faction (+2) or be `"ss"` (+1), else the row is **skipped** |
| `0x729459..0x72948b` | `key[5..7]` must equal the camo (+2) or be `"sss"` (+1), else **skipped** |
| `0x72948c..0x7294d1` | for kind `model`, `strstr(column3, skin)` adds +100 |
| `0x7294f5` | no eligible row returns the empty string |

`mp/coCharItems/hea.csv`'s key column decodes with **spaces**, not underscores:
`"m sc sss"`, `"m tf sss"`, `"m ss sss"`, `"f tf sss"`, `"m zm sss"`, …

### The defect

`mp/coCharItems/hea.csv` gives `hea_socomc` exactly one row:

```
hea_socomc , model , "m sc sss" , hea_socomc_sc_m
```

It is an **`sc`-only** head. Both the shipped `mp/botClassTable.csv` (extracted
from `client_shipRetail/chinese/code_post_gfx_mp.ff`) and the loose
`bin/home/main/mp/botclasstable.csv` put `hea_socomc` in the
**`charHEA`** column — the *team-force* column — for **classes 3 and 8**:

```
charHEA,hea_odom,hea_veiga,hea_socomb,hea_socomc,hea_victor,hea_odom,hea_veiga,hea_socomb,hea_socomc
```

So for a TF bot on class 3 or 8 the head variant selector is asked for faction
`tf`, finds no eligible row, and returns nothing. `character()` treated
`CODOL_LoadCharacterItemModels` status `0` (absent) as success, left
`composition.models[4]` NULL, and `CODOL_OrderCharacterParts`
(`src/codol/player/codol_player_appearance.c:30-36`) skips a NULL model
silently. `CODOL_PublishCharacterComposition` only warns for a *named* part it
cannot mount, so nothing was logged at all.

C1 does the same thing, which is why this is a data defect and not a port
defect: `0x0044f01c` / `0x0044f030` call the bot-character builder `0x00729ec0`
twice, once with column list `0xCCCAB4` and faction **0 (tf)** and once with
`0xCCCADC` and faction **1 (sc)**; the builder's per-slot loop (`0x00729f65..
0x0072a007`) passes the *requested* faction straight into `0x729090`, and its
callback `0x0044e8b0` returns immediately on an empty name (`0x0044e8cb`,
`0x0044e8d0`) — the part is simply not appended.

`hea_socomb` (classes 2 and 7) survives only because its row is keyed
`"m ss sss"` — shared — so it scores `-1 +1 +1 = 1`.

### Exhaustive result

Replaying the exact selector over the shipped tables for all 9 classes × both
factions (script kept in the session scratchpad) drops **exactly one part, in
exactly two places**:

```
FACTION tf
 class0 skin=yel head=hea_odom    parts=10 HEAD-OK
 class1 skin=blk head=hea_veiga   parts=9  HEAD-OK
 class2 skin=wht head=hea_socomb  parts=10 HEAD-OK
 class3 skin=wht head=hea_socomc  parts=9  *** NO HEAD ***   dropped: hea_socomc(slot4,hea)->no-eligible
 class4 skin=yel head=hea_victor  parts=9  HEAD-OK
 class5 skin=yel head=hea_odom    parts=10 HEAD-OK
 class6 skin=blk head=hea_veiga   parts=9  HEAD-OK
 class7 skin=wht head=hea_socomb  parts=10 HEAD-OK
 class8 skin=wht head=hea_socomc  parts=9  *** NO HEAD ***   dropped: hea_socomc(slot4,hea)->no-eligible
FACTION sc
 class0..8                        parts=8  HEAD-OK
```

The part counts match the live producer log exactly
(`CoDOL profile appearance: … faction sc parts 8` and `… faction tf … parts 9`),
and the sc/tf part lists match the saved client DObj capture
`obj/bot-torso-audit/missing-head-capture-90404-followup.json`,
whose entities all carried a head — that capture happened to contain no class-3
or class-8 TF bot, which is why the earlier bounded audit
(`docs/CODOL_BOT_HEAD_AUDIT_20260915.md`) found "no evidence-backed missing-head
source patch" and closed inconclusively.

### Fix

`src/codol/player/codol_bot_loadout.c`

* `head_resolves()` (:233) and `faction_character_head()` (:242) — new. The
  second walks `mp/coCharacterDefTable.csv`, whose **column 1 is each
  character's own faction tag** (`TF` / `SC` / `ZM`), and returns the first head
  of the requested faction that actually resolves a model. For `TF` that is
  `hea_odom`; for `SC`, `hea_socomb`.
* `character()` (:277-289) — if the CSV's head resolves no model for this bot's
  faction, substitute the character table's head **before** the skin tone and
  the character-default merge, because C1 `0x0060D354` keys both on the head
  item. Warned once per (class, faction).
* `character()` (:298-305) — any composition slot whose item resolves no model
  now warns once per (class, faction, slot). This was the silent path that hid
  the defect; it can no longer be silent.

The faction eligibility rule is **not** relaxed: doing that would dress every
faction in the other one's geometry. No head is hardcoded.

Replaying the selector with the substitution gives TF classes 3 and 8 a complete
ten-part outfit:

```
fpa_soccomjeans_tf_m_00, boo_conceptb_tf_s_00, fja_ghost_tf_m_00,
han_typea_ss_m_09, hea_odom_ss_m_yel_00, ves_spcs_ss_m_10,
heg_basehat_tf_s_09, elp_tactical_ss_m_00, knp_typec_tf_s_00,
bar_spcsassault_tf_m_10
```

`hea_odom_ss_m_yel_00` is already a live-registered, mounted head (it is on
entity 0 and entity 2 of the saved DObj capture), so the substitute is known
good rather than merely table-legal. Note the tone also changes from the
fallback `wht` to `yel`, which is correct: C1 derives the tone from the head
item, so the rest of the outfit now matches the face that is actually drawn.

### Hypotheses ruled out

* **Not the hide-tag system.** Hide tags in this engine belong to `WeaponDef`
  (`hideTags[32]`, `src/codol/assets/codol_assets.h:196`, `:327`), not to
  XModels, and `alpha0022/docs/loadout_classes.md` §1.5 measured that of the 70
  attachments legal for `m4_mp` exactly three carry a type-`0x27` field,
  contributing only `tag_up` and `tag_down` — the sight rail. There is no
  headgear-drives-head-hiding mechanism to misfire, and no headgear part was
  missing in any bot class anyway.
* **Not a missing mounted zone.** `CODOL_PublishCharacterComposition`
  (`src/codol/player/codol_player_appearance.c:224-227`) warns
  `CoDOL appearance: unavailable part …` for a named part whose skeleton is not
  mounted, and the live log contains no such line; every `hea_*` model the bot
  classes name is mounted. The failure is upstream of availability — no name was
  produced at all.
* **Not the DObj bone budget.** `CODOL_AppendCharacterDObjParts` drops cosmetic
  parts over `DOBJ_PART_BIT_COUNT`, but that is the **server-only** 128-bone
  pose; the client receives the complete sixteen-slot appearance independently,
  and the head is ordered fifth (`ordered_slots[] = {0,1,2,3,5,4,6,7,8,13}`),
  well inside any bound.
* **Not attachment tags.** Every attachment tag is published as zero and the
  saved DObj capture shows every other bone-merged part arriving correctly, so
  the empty-tag merge is working.

### The same hole exists on the human path

`CODOL_ComposeProfileCharacter`
(`src/codol/assets/codol_character_composition.c:97-103`) has the identical
silent drop for a profile-selected part:

```c
        status=CODOL_LoadCharacterItemModels(next.items[i],gender,f,camo,skin,
            &next.models[i],&next.viewmodels[i]);
        if(status<0)return 0;
        if(status!=1)next.viewmodels[i]=NULL;
```

That file is owned by the hands-composition worker, so the change is **not**
applied here. Suggested diff for that owner — warn, and for the head slot only,
substitute the character table's own faction head exactly as the bot path now
does:

```c
        if(status!=1) {
            next.viewmodels[i]=NULL;
            Com_PrintWarning(CON_CHANNEL_SERVER,
                "CoDOL character: slot %u item %u has no %s variant; part omitted\n",
                i,(unsigned)next.items[i],faction);
        }
```

A human whose `tfCharacterIndex` record selects `hea_socomc` (or any other
faction-locked head) is headless today for the same reason.

---

## (B) The red placeholder on the bot FAL

### It is not an effect

No fx asset, fx configstring index or bot fire path is involved. The bot fire
path (`src/codol/player/codol_bot.c`) and the linked world-weapon producer
(`src/codol/player/codol_player_worldweapon.c`) publish no per-weapon
muzzle-flash, shell-eject or tracer fx index of their own; the client resolves
those from the `WeaponDef` it built for the composed name. Whether the artifact
is visible only while firing was not established from the log, but no producer
exists on the server side that could emit a wrong fx index for it. The artifact is
C1's **default XModel substitution** for a part whose geometry is not in any
mounted zone: a flat, unlit, uniform-colour quad. `alpha0022/docs/loadout_classes.md`
§1.6/§1.7 records the same artifact on a composed M4 ("one of the nine pieces
draws as a large untextured **red plane**") and never identified it; §9.9.3
explicitly warns that the *other* salmon quad (the heartbeat-sensor screen,
gated by `ps+0x22C` / `WeaponDef+0xBED`) is a different artifact. This is §1.6's.

### The chain

`mp/botClassTable.csv` botclass6 is `loadoutPrimary = fal`. The loose table had
`loadoutPrimaryAttachment = red_swat1` for that class.

1. `mp/coWeaponAttachmentTable.csv` **does** list `(fal_mp, red_swat1)` →
   `reflex_base`, variant 0, so the pair is legal and
   `CODOL_ComposeLoadoutWeaponRecipe` accepts it.
2. `mp/coweapitems/sco.csv` gives every `red_swat1` row the weapon-independent
   models `red_swat1_s_<camo>` / `red_swat1_s_<camo>_vmgun` on `TAG_RED_DOT`.
   botclass6 has no camo (`loadoutPrimaryAttachment7 = none`), so flag 0 selects
   **`red_swat1_s_blk`** and **`red_swat1_s_blk_vmgun`**.
3. **Neither XModel exists in any of the 90 shipped `.ff` zones**, nor in the
   `iw_model_*.iwd` streams. The string `red_swat1_s_blk` occurs in the shipped
   data only inside the `sco.csv` stringtable itself. Every sibling red dot
   (`red_ak`, `red_normal`, `red_pst`, `red_reflex`, `red_rmr`) has its
   `_lod010/110/210` and `_vmgun10` XModelSurfs in `common_gametype_mp.ff`.
   Only `red_swat1` is unshipped. Its two materials
   (`mc/mtl_red_swat1_s_blk_lens`, `mc/mtl_red_swat1_s_blk_small`) *are* shipped,
   which is why the header/`fx10` substitution reading is the consistent one.
4. The other eight parts of the bot FAL — the base `wea_fal_fal_blk` and the six
   declared defaults `muz/sto/gri/mag/rai/iro_default_fal*` from
   `mp/coweapitemswea.csv` row 33 — are all present with all their materials.

So exactly one of the FAL's parts is a placeholder, which is what the user sees.

### Why the FAL specifically, and why the shipped value cannot just be restored

`fal_mp` has **50** attachment-table rows and `red_swat1` is its **only** red-dot
optic — the other 49 are camos, grenade launchers, shotguns, magazines, muzzles,
stocks, rails and irons. `red_swat1` is therefore the only weapon-legal sight the
FAL can be given, and it is the one sight with no geometry.

The **shipped** `botClassTable.csv` names `red_reflex` for botclass6. `red_reflex`
has no `(fal_mp, red_reflex)` row in `mp/coWeaponAttachmentTable.csv` at all, so
C1 resolves it to `bg_attachIdx == 0` and its own bot FAL carries **no optic**.
Our composer rejects an illegal pair outright, which is why a previous pass
substituted `red_swat1` and introduced the placeholder.

### Fix

* `bin/home/main/mp/botclasstable.csv:4` —
  `loadoutPrimaryAttachment` botclass6 `red_swat1` → **`none`**. This reproduces
  C1's own effective result for that class: the FAL composes with its declared
  defaults, including `iro_default_fal*` iron sights, and no placeholder part.
  `sra_hbs` on botclass5 was left alone; it is a deliberate earlier change away
  from the shipped `hbs_normal` (which merges no model at all) and is
  geometry-checked separately.
* `src/codol/player/codol_bot_loadout.c` —
  `part_models_mounted()` (:148) and the filtering pass in `get_weapon()`
  (:191-211) are the backstop: after composing, every **class-chosen** part is
  resolved through `CODOL_ComposedItemModelRow` and its world and view models are
  checked against the mounted asset set with `CODOL_LoadMountedXModelSkeleton` —
  the same availability test the appearance publisher uses. An unbuildable choice
  is named in a warning, dropped from the id list and the recipe is composed once
  more; if the reduced recipe will not compose, the original stands, so the guard
  can never make things worse. Parts with no model row at all (`cam_*`,
  `sco_none`, `hbs_normal`, `gps_default`) are correctly not treated as absent.

Legality is not availability. That distinction is now enforced for the bot
weapon recipe the same way it already was for character parts.

---

## (C) Match-ending `cannot publish bot weapon` — the retained 128-slot table

Reported live on PID 21224 (mp_killhouse, one human as client 0, bots up to
`Training 11`), `bin/home/main/qconsole.log:3406-3412`:

```
CoDOL native weapon lookup: *a 14 0 33 0 41 0 16 0 32 0 34 0 31 0
CoDOL reliable -> Nucleur: d 2214 wea_fal_fal_blk
throwing script exception: cannot publish bot weapon *a 14 0 33 0 41 0 16 0 32 0 34 0 31 0
----- Server Shutdown ----- With the reason: Server disconnected
```

### Cause: capacity, not the spec

The spec is base 14 (`fal_mp`) with only the six declared defaults
(33 `muz_default`, 41 `sto_default`, 16 `gri_default`, 32 `mag_default`,
34 `rai_default`, 31 `iro_default`). `d 2214 wea_fal_fal_blk` is broadcast
immediately before the exception, so `CODOL_LoadComposedWeapon` **succeeded** and
the base model was registered; the failure is `CODOL_PublishComposedWeapon`
returning -1.

`append_weapon_set` (`src/codol/weapon/codol_sv_weapons.c:173-174`) rejects any
publish whose final `BG_GetNumWeapons()` exceeds 128, because its engine->wire
`mapping[128]` and the live `reverse_weapon_map[128]`
(`src/codol/player/codol_usercmd.c:119`) index engine slots 0..127 only. The log
shows engine indices already in use up to **127** — the table held 128 entries
before this call. One more definition made it 129 and the guard fired.

Contributors, from the same log: ~52 stock weapons plus the partner/alternate
definition each of them registers, the human's own composed loadout
(`*a 14 16 146 0 28 0 190 0 33 0 41 0 16 0 34 0`, engine 111), and 15 distinct
bot composed definitions — two per distinct bot class.

**The three leads, resolved:**

* *Weapon CS table cap* — no. The wire side is `CODOL_WEAPON_SLOTS 700`
  (`src/codol/snapshot/codol_configstrings.h:32`; C1 validates 1..699) and was
  nowhere near full. What is exhausted is the **native** `bg_weaponDefs`,
  `resb 0x204` = 129 pointers (`src/asmsource/_bg_weapons.asm:9242`).
* *Attachment missing from the zone, or over a per-weapon limit* — no. This spec
  carries no chosen attachment at all, only the weapon's own declared defaults,
  and the zone sweep confirms all six `*_default_fal*` models ship.
* *The bot loadout edits changed the recipe* — the **string** changed: removing
  `red_swat1` in (B) turned class 6's spec from `*a 14 0 82 0 33 …` into
  `*a 14 0 33 …`. It is **not causal**: either spelling is one composed
  definition, and the rejection is on the post-registration count, not the name.
  The same call fails identically with the old spec.

### Damage beyond the crash

`BG_GetWeaponIndexForName(requested, G_RegisterWeapon)` runs **inside**
`append_weapon_set` *before* the count is re-read and checked. A rejected publish
therefore leaves the native table one entry longer with no wire slot and no
configstring — a definition `CODOL_WeaponToWire` maps to -1. That is the
blanked/unbuildable `*a` shape that also crashes `CG_Init` on the client. The
pre-check below stops that path being entered at all.

### Fix — `src/codol/player/codol_bot_loadout.c`

1. **Never end the match.** Every data, asset and capacity failure in all three
   bot builtins now degrades and logs once instead of raising:
   * `weapon_fallback()` returns the **stock base weapon** (`fal_mp`), already
     registered and costing no native slot — the IW4 behaviour for a bot whose
     loadout cannot be built. Used for an unknown base, an unknown attachment or
     camo, a recipe that will not compose, an unbuildable definition, and a
     failed publish (which now reports `CODOL_ServerWeaponRegistryError()`).
   * `get_item()` answers `"none"` with a warning instead of raising on a
     missing CSV member.
   * `character_fallback()` keeps the bot's existing appearance with a warning
     instead of raising on any table, item, default, rig, model or publication
     failure.
   * The only remaining raises are script-contract violations — wrong receiver,
     wrong argument type, out-of-range class/side/faction.
2. **Do not burn the last native slot.** `native_weapon_room()` checks
   `BG_GetNumWeapons() + CODOL_NATIVE_WEAPON_HEADROOM <=
   CODOL_NATIVE_WEAPON_SLOTS` *before* composing (headroom 2 covers the composed
   definition plus one retained alternate). When the table is full the bot takes
   an already-registered weapon and the doomed registration never happens, so the
   native table and the wire map stay consistent.

   `CODOL_NATIVE_WEAPON_SLOTS` is owned by `src/codol/weapon/codol_sv_weapons.h`
   and is deliberately **not** restated in `codol_bot_loadout.c`: the deploy
   owner is widening the native table (ownership bitset 128 -> 384 bits,
   definition table to 700), and a second copy of the ceiling would leave this
   room check gating at the old value while everything else moved.

### Known remaining limit (reported, not changed)

`bg_weaponDefs` has 129 pointer slots (0..128) but the CoDOL wire map indexes
0..127, so engine slot 128 is unusable and the `>128` guard is one short of the
engine's real capacity. Recovering it means widening `mapping[]` in
`codol_sv_weapons.c` **and** `reverse_weapon_map[]` / the `engine>=128` bounds in
`src/codol/player/codol_usercmd.c` together; that file is outside this worker's
ownership, so it is reported rather than applied. It is worth one slot, not a
solution: a full training lobby needs materially more than 128 definitions, so
either the retained table grows or bot classes share composed weapons. Until
then the fallback is what keeps the match alive.

---

## (D) `Invalid CoDOL asset configstring 2258` — the (C) fallback's own overflow

Next deploy (PID 10456), `bin/home/main/qconsole.log:2890`. **(C)'s fix worked**:
zero `cannot publish bot weapon` in the whole session, and the degrade fired
four times —

```
Warning: CoDOL bot class 4 primary weapon: the retained 128-slot weapon table is full; falling back to the stock m1014_mp
Warning: CoDOL bot class 5 secondary weapon: the retained 128-slot weapon table is full; falling back to the stock g18_mp
```

— but two lines later:

```
CoDOL giveweapon: name g18_mp engine 128 wire -1 ...
ERROR: Invalid CoDOL asset configstring 2258
```

### What 2258 is

**`2258 == 0x8d2`**, which `CODOL_PublishAssetConfigstring`
(`src/codol/assets/codol_sv_assets.c:604`) intercepts *by exact value* as the
retained `SaveRegisteredWeapons` list, returning
`CODOL_RefreshServerWeaponMappings() ? 1 : -1`. It is **not a model or material
slot**. The compiled block map is:

```
CS_MODELS 830..1341   CS_SOUNDS 1342..1597   CS_FX 1598..1697
CS_FXONTAGS 1698..1953  CS_SHOCKS 1954..1969  CS_MENUS 1970..2001
CS_MATERIALS 2002..2257  [2258 = 0x8d2, the weapon list]  CS_STATUSICONS 2259..2266
CS_HEADICONS 2267..2281  CS_TAGS 2282..2313
```

### Cause

(C)'s fallback handed back "the stock base weapon", on the assumption that a
stock name costs no native slot. That is false for a name the table does not
already hold: `giveWeapon` resolves through `BG_GetWeaponIndexForName`, which
calls `G_RegisterWeapon` and **appends**. `g18_mp` had never been given this
session, so it was registered at **engine index 128** — one past the 128-entry
`reverse_weapon_map` — which the log states outright as `engine 128 wire -1`.
The retained `SaveRegisteredWeapons` write that follows lands on CS 0x8d2,
`CODOL_RefreshServerWeaponMappings()` hits `native_count > 128` and fails, the
publisher returns -1, and `sv_main.c:4973` `Com_Error(ERR_DROP)`s the match.

So (C)'s degrade turned a script exception into an engine drop. Same ceiling,
one layer lower.

### Ruled out

* **The head substitution** — no. That bot is faction **sc** and `hea_socomc`
  *is* the sc head (`"m sc sss"`), so no substitution ran; the substitution path
  only fires for a head with no variant for the requested faction, i.e. tf
  classes 3 and 8.
* **Model configstring block overflow** — no. The wire model block is
  `CODOL_CS_MODELS 1315` + `CODOL_MODEL_SLOTS 2048` (wire 1315..3362) and the
  last indices published were 1420/1456/1516, roughly 200 of 2048 in use; the
  native block is 512 wide. The three `d ...` model commands before the error
  are simply the last traffic, not the failing operation.
* **Missing dedupe across bots** — no. `CODOL_RegisterRuntimeModel`
  (`src/codol/player/codol_player_appearance.c:105-128`) scans the published
  `CS_MODELS` range and returns the existing index for an equal name before it
  allocates, so identical parts on different bots already share one slot. And a
  cosmetic part that cannot be registered is already dropped rather than fatal:
  `CODOL_PublishCharacterComposition` skips a part whose
  `CODOL_RegisterRuntimeModel` returns 0.
* **The (B) mounted-geometry guard** — no. It only removes attachments from a
  recipe; it never registers a weapon.

### Fix

1. `src/codol/player/codol_bot_loadout.c` — `weapon_already_live()` uses the
   find-only `BG_FindWeaponIndexForName` (registers nothing) plus
   `CODOL_WeaponToWire()` to test whether a name is *already* in the native
   table **and** mapped. `weapon_fallback()` now answers `"none"` instead of a
   base weapon whenever there is no room and the fallback is not already live.
   An unarmed bot is a degraded bot; a dropped server is a dead match.
2. `src/codol/assets/codol_sv_assets.c` — the `0x8d2` branch no longer returns
   -1 on a failed refresh. It warns once per level (naming
   `CODOL_ServerWeaponRegistryError()`), keeps the previous map and consumes the
   update. Only definitions past the 128-slot table stay unmapped, and
   `CODOL_WeaponToWire` already answers -1 for those, which every consumer
   handles. Nothing else in the server can turn this capacity condition into an
   `ERR_DROP` any more.

The underlying 128-definition ceiling is unchanged and still the real limit —
see the note at the end of (C).

---

## (E) Same ceiling on the human path — `codol_getLoadoutWeapon`

Live at `qconsole.log:~11010`, on a human class change
(`maps/mp/gametypes/_class.gsc:484` via `_menus.gsc:225` menuresponse ->
`spawnClient`), after the budget line
`CoDOL weapon budget: 128/128 native definitions - 113 stock, 0 partner, 14
composed; 0 free` and a working rollback
(`publish failed; rolled the native table back from 129 to 128`):

```
could not be published into a weapon slot (composed weapon publication failed)
```

Same ceiling as (C)/(D), reached by the **human** bridge, which still raised.
The bot bridge degraded correctly.

### Fix

**Shared budget module (new, owned here):**
`src/codol/weapon/codol_weapon_budget.{h,c}` now holds the three helpers both
producers need, so the rule has one implementation and the ceiling one
definition:

* `CODOL_NativeWeaponRoom()` — room for one composed definition plus the
  retained alternate it may drag in. Ask **before** composing, because
  `append_weapon_set` only refuses the publish *after*
  `BG_GetWeaponIndexForName` has appended.
* `CODOL_WeaponAlreadyLive(name)` — the name already occupies a definition slot
  *and* has a wire index, via the find-only `BG_FindWeaponIndexForName`.
* `CODOL_SafeStockWeapon(name)` — `name` when there is room or it is already
  live, `"none"` otherwise. Never NULL.

`CODOL_NATIVE_WEAPON_SLOTS` is *not* restated there; it stays owned by
`codol_sv_weapons.h` so the in-flight widening of the native table applies
everywhere at once. `codol_bot_loadout.c` dropped its private copies of these
helpers and calls the shared ones.

**`src/codol/script/codol_script_profile_loadout.c`** —
`CODOL_Scr_GetLoadoutWeapon` now contains **zero** `Scr_Error` calls:

* `loadout_weapon_fallback()` warns once per weapon slot and answers
  `CODOL_SafeStockWeapon(base)`.
* `CODOL_NativeWeaponRoom()` is checked before `CODOL_LoadComposedWeapon` /
  `CODOL_PublishComposedWeapon`, so a full table never produces a definition
  with no wire index.
* The publish failure degrades instead of raising, reporting
  `CODOL_ServerWeaponRegistryError()`.
* The four pre-existing "use the stock base" degradations (no composed art,
  missing declared groups, overflowed recipe, unbuildable definition) now route
  through `CODOL_SafeStockWeapon` — previously they could hand back an
  unregistered base and cause exactly the (D) overflow.
* The three optional-data raises in the getter (tables not mounted / composed
  name does not fit; stored base is not a `wea` row; marketplace malformed) now
  degrade with a warning.
* `loadout_for_optional()` is a non-raising variant of `loadout_for` used only
  by this getter: identical validation, but an unusable profile is *reported*
  (-1) rather than thrown, so "this player has no complete profile upload"
  degrades instead of unwinding `spawnClient`. The raising `loadout_for` is
  untouched for the six query getters that scripts call defensively.

Script-contract violations — wrong receiver, wrong parameter count, wrong
argument type, out-of-range class or slot index — still raise in both bridges.
Those are caller bugs, not runtime conditions.

---

## Build, tests, verification

* `src/codol/player/codol_bot_loadout.c` compiles clean under the Windows
  profile (`make OS=Windows_NT obj/codol/codol_bot_loadout.o -B`, i686
  mingw32 gcc 14.1): the only warnings are the three pre-existing
  `-Wmisleading-indentation` notes on lines this change did not touch.
  `src/codol/assets/codol_sv_assets.c` also compiles clean (its `-Waddress`
  warnings are pre-existing and on untouched lines).
* `test-codol` is Linux/WSL-only by design (`makefile:379` errors on Windows),
  so the character/appearance/loadout fixtures were built and run against this
  tree under WSL Ubuntu-24.04 — all seven pass:

  ```
  PASS: C1 character variants, skin priority, shared fallback, reverse ties and contiguous groups
  PASS: eighteen-slot defaults, preserved overrides, reverse name lookup and atomic invalid IDs
  PASS: marketplace last-row lookup, canonical IDs, mounted part routing and material exclusion
  PASS: chest-rig active column, exact flags, last-row replacement, missing-ID clear and atomic errors
  PASS: C1 raw-row visibility, numeric suffix, exact-length terminator and malformed data
  PASS: selected profile -> defaults -> rig -> visibility -> model names; immutable input and atomic failure
  PASS: full profile attachment set, camo/variant distinction, declared defaults, invalid selection atomicity
  ```

* Toolchain note for other workers: MSYS `make` scrubs `TMP`/`TEMP` from recipe
  environments, so `gcc` puts its intermediate `.s` in `C:\WINDOWS\` and the
  assembler then fails with `can't open C:\WINDOWS\ccXXXXXX.s`. Pass them as
  make command-line variables:
  `make OS=Windows_NT TMP='C:\Users\<user>\AppData\Local\Temp' TEMP='...'`.
  `OS` also has to be passed explicitly from a Git Bash shell or the makefile
  takes its Linux branch and links `bin/codol_dedrun` instead of
  `bin/codol_dedrun.exe`. The `obj/codol` tree currently mixes PE C objects with
  ELF `.asm` objects from an earlier Linux profile run; that predates this change
  and a full link needs it resolved.
* Zone sweep (independent): all 18 bot weapons compose to 162 distinct
  world/view models and **every one has shipped geometry** once `red_swat1` is
  gone. `sra_hbs` on `cheytac_mp`+`cam_hex` resolves to `hbs_normal_ss_11`
  (present), `eot_exps` on `ump45_mp` and `red_rmr` on `ak104_mp` are present.
  Across all `coweapitems`/`coweapmodels` tables 264 geometry families over 97
  attachment items are unshipped but none are reachable from the bot table —
  the notable landmines if attachments are ever changed are `eot_553`,
  `red_swat1`, `sco_mid2`, `sco_longfix4/5/6`, `gre_m320*` and every `*_gld`
  (camo 30) variant.
* No GSC was edited, so no `tools/collate_gsc.py` run was required.
  `python tools/verify_gsc_collation.py` was run anyway and reports OK
  (1226 files, 0 missing, 0 sha1 mismatches, 0 unresolved lowering paths).
* No server was deployed, restarted or launched; the running C1 client and the
  Python lobby were untouched.

### Live check, (A)

1. Start a match with enough bots to reach class 3 or class 8 on the TF side
   (`scr_codol_bots` ≥ 4; `_codol_bots.gsc` assigns `serial % 9`).
2. In the server console, the substitution must appear once:
   `CoDOL bot class 3 (tf): hea_socomc has no tf head variant; using the
   character table's hea_odom instead`.
3. Those bots' appearance line must read `parts 10`, not `parts 9`.
4. Visually, or with the existing player render probe, the TF class-3/8 bot's
   DObj must now contain `hea_odom_ss_m_yel_00`.
5. Regression guard: no `slot N item … has no … variant; part omitted` warning
   should appear for any class. If one does, that slot is the next data defect
   and is now named in the log rather than silent.

### Live check, (B)

1. Spawn a class-6 bot (`serial % 9 == 6`) and look at the FAL it carries, in
   third person and in a killcam.
2. The gun must be a plain FAL with iron sights and no flat red quad anywhere on
   it.
3. No `attachment red_swat1 needs xmodel red_swat1_s_blk, which is in no mounted
   zone` warning should appear, because the CSV no longer asks for it. Putting
   `red_swat1` back in the CSV should produce exactly that warning and still
   produce a clean gun — that is the backstop test.
