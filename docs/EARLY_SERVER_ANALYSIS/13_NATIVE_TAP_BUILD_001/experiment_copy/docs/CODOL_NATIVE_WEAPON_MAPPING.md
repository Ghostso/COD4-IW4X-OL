# Native weapon IDs and the client registry

## Weapon composition reference

CoDOL weapon assembly must follow alpha0022's attachment composition system.
`weapon_spawn.py` explicitly corrects the older hideTags explanation: the client
builds a custom weapon from component XModels selected through
`mp/coWeapModels/<weapon>.csv` and `mp/coWeapItems/<item>.csv`. Publishing only a
stock base index can select the shipped IW4-style fallback mesh. Toggling bone
visibility does not implement this assembly path.

The reference implementation is in `weapon_loadout.py`, `weapon_spawn.py`,
`custom_weapon_pool.py`, and `alt_weapons.py`; the correction and measurements
are documented in `docs/loadout_classes.md` and the updated `weapon_spawn.py`
header. Custom weapon names carry the base index and attachment item/variant
pairs through the weapon configstrings. Marketplace item IDs, attachment item
indices, and registered weapon IDs are distinct namespaces.

The existing native registry handles weapon IDs and ammo-pool relationships;
it does not yet implement the complete custom attachment composition path or
apply its gameplay overrides. That work must use the reference's patched tables,
custom-definition publication order, model selection and alternate-weapon rules.
The `J_Spine4` argument to `PrecacheFxTeamThermal` is a skeletal FX attachment
point, independent of this weapon assembly system.

## Existing native ID mapping

`CODOL_RefreshServerWeaponMappings` enumerates the retained engine's actual
weapon definitions using `BG_GetNumWeapons` and `BG_GetWeaponDef`. It resolves
each internal name against the server-owned CoDOL registry, then replaces both
directions of the existing usercmd/snapshot weapon map together. The retained
assembly getter returns `bg_lastParsedWeaponIndex + 1`, including index zero.

Native order may differ from published order. Unknown names, duplicate target
IDs, missing definitions, invalid null-weapon mapping and counts beyond the
128-entry retained weapon domain fail without partially changing the old map.
A successful smaller replacement removes mappings for old native slots.

Gamestate preparation refreshes the registry and this mapping before encoding.
Snapshot preparation refreshes mappings after asset/player-name publication.
Successfully decoded input batches also refresh before converting weapon IDs,
covering native registrations that occur after the last outgoing snapshot.
A failed server-side refresh drops that batch without marking its bytes malformed.
The existing usercmd translator and player/entity/inventory snapshot adapters
already use these two lookup directions, so they now share the same name-based
registration association. This does not load a weapon just because the client
requested its ID; only native definitions actually loaded by gameplay can map.

The server fixture deliberately registers SCAR variants in a different native
order, checks both lookup directions and unavailable wire IDs, then verifies
unknown-name/duplicate/count failures and stale-slot removal. ASan and UBSan
pass with halt-on-error. `codol_checkweaponregistry` also reports whether native
mapping succeeds against the loaded server.

The input regression uses the actual `CODOL_ToEngineUsercmd` conversion before
and after swapping native weapon order without changing definition count. Both
selected weapon and offhand follow the refreshed mapping, movement/time remain
intact, and an unloaded client weapon retains the current native selection.
This tests translation, not a live authenticated C1 movement packet.

General gameplay weapon loading remains incomplete. This mapping does not
replace the missing live frame seeds, custom-definition construction or the
unresolved `weaponInheritsPerks` script function. Match entry is not yet proven.

The isolated Bog probe at `%TEMP%/sh1x-native-weapon-map-20260908-034832`
reported 54 client registry definitions and `CoDOL native weapon mapping: ready`.
This confirms mapping of the definitions currently loaded by the native fixture,
not that all 54 client weapons have native gameplay implementations. All four
existing VM markers passed, and PID 72980 exited through normal quit.

Forced Windows build `/tmp/sh1x-native-weapon-map-win32.log` and forced Linux
build/full suite `/tmp/sh1x-native-weapon-map-linux.log` pass; the sequential
command exited zero. Shared static libraries were last built for Linux.

The subsequent input-refresh change passes its updated sanitizer fixture,
Linux build/full suite (`/tmp/sh1x-input-weapon-map-linux.log`) and forced
Windows build (`/tmp/sh1x-input-weapon-map-win32.log`). That sequential command
also exited zero; shared libraries are now built for Windows.

---

## 2026-09-16: the WA2000 wore its IW4 body for the player and its CoDOL body
## for the bot — the two loadout bridges disagreed about one declared group

Status: **WRITTEN** and **compile-checked** (`obj/wa2000-check/`, no warnings in
`codol_script_profile_loadout.c`). **Not yet built into an exe, not yet verified
against a live C1 client.**

### The symptom, and what "the IW4 model" is

User report, 2026-09-16 ~20:50: the WA2000 rendered with its stock/IW4 mesh.
That is the failure this document already names at the top:

> "the client builds a custom weapon from component XModels selected through
> `mp/coWeapModels/<weapon>.csv` and `mp/coWeapItems/<item>.csv`. **Publishing
> only a stock base index can select the shipped IW4-style fallback mesh.**"

"Index 0" is `gunXModel[0]` / `worldModel[0]` of the *stock* definition: the
model slot `G_GivePlayerWeapon` checks and the client draws when it is handed a
plain base name. A composed `*a …` definition never uses it — composition binds
the `mp/coweapmodels/<base>.csv` row's world/view pair into **every** one of the
sixteen retained model variants (`docs/CODOL_IMPLEMENTATION_PASS.md`,
"2026-09-10: composed weapon model binding"). So "WA2000 on index 0" means
exactly "the server handed the client `wa2000_mp` instead of `*a 53 …`".

### Proof from the 20:27 session log, not inference

`bin/home/main/qconsole.log`, one map, one recipe, two producers:

```
:2432  ^3Warning: CoDOL bot wa2000_mp: 1 declared default(s) have no legal C1
              attachment/model pair; retaining complete legal recipe
:2438  CoDOL giveweapon: name *a 53 0 150 0 32 0 33 0 155 0 engine 111 wire 123 …
...
:7183  ^3Warning: CoDOL loadout: *a 53 0 150 0 32 0 33 0 155 0 leaves 1 declared
              group(s) empty; using stock wa2000_mp
:7195  CoDOL giveweapon: name wa2000_mp engine 29 wire 53 …
```

The bot (`Training 4`) and the human (`Nucleur`, class `custom4`) composed the
**identical** name. The bot published it; the human was given the stock base.
The user's own in-process client read agrees: the client held `slot 53
wa2000_mp` alongside composed `*a …` definitions at slots 127 and 135
(`docs/captures/bob_capture_20260916_2042.jsonl`).

### Cause

`wa2000_mp` declares `gri_default` in `mp/coweapitemswea.csv`, but neither
`mp/coWeaponAttachmentTable.csv` nor `mp/coweapitems/gri.csv` gives this weapon
any grip row at all. The group can never be covered and has no legal
replacement, so `CODOL_ComposeLoadoutWeaponRecipe` always reports
`missing_defaults == 1` for it. C1 composes the gun regardless.

`src/codol/player/codol_bot_loadout.c` has known this since `efc3e2ee`
(`missing_defaults_unconstructible`, comment at :120). `efc3e2ee` did **not**
propagate the same test to the human bridge, so
`CODOL_Scr_GetLoadoutWeapon` in `src/codol/script/codol_script_profile_loadout.c`
kept the unconditional reject it has carried since `11e5f6f6`. Confirmed with
`git log -S`: the human-side string appears only in `11e5f6f6`, the bot-side
exemption only in `efc3e2ee`. Nothing in the 2026-09-16 commits touched either.

So this is **not** a freshly reintroduced regression from the recent
weapon/attachment work. It is the long-standing divergence created by
`efc3e2ee`, first reached tonight because this is the first session in which a
human played a WA2000 class (every earlier `qconsole*` log has zero
`CoDOL loadout:` warnings and zero stock `wa2000_mp` gives).

### Fix

One implementation of the rule, shared by both bridges:

* `CODOL_LoadoutMissingDefaultsUnconstructible()` — new, in
  `src/codol/script/codol_script_profile_loadout.{c,h}`, next to the recipe it
  judges. 1 only when *every* uncovered declared group is one the weapon's own
  C1 tables cannot fill; a group with a legal pair or a legal replacement is
  still a composer defect and still rejects the recipe.
* `CODOL_Scr_GetLoadoutWeapon` degrades to the stock base only when that test
  fails, and otherwise logs the same observation the bot bridge logs, once per
  weapon slot, on its own latch so it cannot mask a later real fallback.
* `codol_bot_loadout.c`'s private copy became a one-line forwarder, so the two
  producers cannot drift apart again.

### Left unproven

A live C1 capture showing the human's WA2000 arriving as `*a 53 0 150 0 32 0 33
0 155 0` (wire 123) rather than `wa2000_mp` (wire 53), and the correct body
rendering. The composed definition is already known to build and publish
successfully on this exact build — the bot was given it in the same match — so
the remaining risk is confined to the human give path.
