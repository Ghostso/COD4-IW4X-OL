# `addon_map_ents` (IW4 asset type 42) — layout, composition and wiring

2026-09-20. Everything below is labelled MEASURED (read out of the shipped
`.ff` files, out of C1.exe, or out of this repo's own retained assembly) or
INFERRED (a reasoned choice the data supports but does not by itself prove).

Follow-on from `docs/CODOL_CATEGORY_SCRIPT_SETS_20260917.md` §2.3, which
established the problem: the nine coop zones ship **no world assets at all**
and exactly one `addon_map_ents` each, and this server had no loader for it, so
a coop match saw only the base multiplayer entities and none of its Spec Ops
spawns.

---

## 1. The nine addons (MEASURED)

`docs/zone_assets/ALL_addon_map_ents.txt` lists nine, one per coop playlist
zone, and nothing else in the whole 90-zone corpus ships one. Re-verified this
pass by walking each zone's directory for type 42: exactly one hit per zone,
zero in every `patch_*`, `mp_*`, `zm_*`, `common_*` and `ui_*` zone.

| zone | asset name | extent | entity chars | trigger models / hulls / slabs |
|---|---|---:|---:|---|
| `coop_defense_mp_crash_tropical` | `maps/mp/coop_defense_mp_crash_tropical.mapents` | 78302 | 76179 | 35 / 45 / 16 |
| `coop_prolog_mp_crash_intro` | `maps/mp/coop_prolog_mp_crash_intro.mapents` | 31772 | 30813 | 18 / 18 / 8 |
| `coop_spec1_mp_killhouse_sh` | `maps/mp/coop_spec1_mp_killhouse_sh.mapents` | 14548 | 13129 | 27 / 27 / 13 |
| `coop_spec_mp_crash_tropical` | `maps/mp/coop_spec_mp_crash_tropical.mapents` | 34182 | 33442 | 14 / 14 / 5 |
| `coop_spec_mp_estate_tropical` | `maps/mp/coop_spec_mp_estate_tropical.mapents` | 65212 | 62811 | 31 / 31 / 54 |
| `coop_spec_mp_fav_tropical` | `maps/mp/coop_spec_mp_fav_tropical.mapents` | 48998 | 47980 | 19 / 19 / 9 |
| `coop_take_mp_estate_tropical` | `maps/mp/coop_take_mp_estate_tropical.mapents` | 83312 | 78751 | 59 / 59 / 106 |
| `coop_take_mp_fav_tropical` | `maps/mp/coop_take_mp_fav_tropical.mapents` | 61072 | 56822 | 93 / 94 / 21 |
| `coop_training_mp_killhouse_sh` | `maps/mp/coop_training_mp_killhouse_sh.mapents` | 50714 | 48912 | 34 / 34 / 18 |

---

## 2. The on-disk layout (MEASURED)

`AddonMapEnts` is `MapEnts` truncated after the trigger arrays.

```
+0x00  uint32  name pointer          0xFFFFFFFF => inline, after the header
+0x04  uint32  entityString pointer  0xFFFFFFFF in all nine (always inline)
+0x08  uint32  numEntityChars        includes the terminating NUL
+0x0C  uint32  trigger model count   record stride  8
+0x10  uint32  trigger model pointer
+0x14  uint32  trigger hull  count   record stride 32
+0x18  uint32  trigger hull  pointer
+0x1C  uint32  trigger slab  count   record stride 20
+0x20  uint32  trigger slab  pointer
= 0x24 (36) bytes
```

`MapEnts` continues `+0x24 uint32 stage pointer`, `+0x28 byte stage count`, for
0x2C (44) bytes. Confirmed on the base maps too: for `mp_killhouse_sh`,
`mp_crash_tropical`, `mp_crash_intro`, `mp_estate_tropical` and
`mp_fav_tropical` the 44-byte header sits immediately before the entity text
inside `col_map_mp`, with a pooled (block-3) name reference, `+0x04 ==
0xFFFFFFFF`, and `+0x08` equal to the exact text length.

Payload order after the header: optional inline name (NUL-terminated), the
entity text (`numEntityChars` bytes, last byte NUL, no interior NUL), then the
model, hull and slab arrays. For **all nine**, `36 + name + numEntityChars +
8*models + 32*hulls + 20*slabs` equals the asset extent to the byte.

This matches the 36-byte figure the offline `tools/codol_zone_assets.py`
already used for name recovery, and it matches the 36-vs-44 split this repo's
zone-stream replay already encoded in `replay_map_entities_body(..., addon)`
(`src/codol/assets/codol_load_blocks.c:1105`, annotated "C1 MapEnts 0x4be8c0 …
AddonMapEnts 0x4beae0 shares the prefix but has no stages"). `case 42:` was
already routed there — the gap was never the stream reader, it was that
nothing looked the asset up or consumed it.

### Entity text shape (MEASURED, all nine)

* The text is exactly `{\n"k" "v"\n…\n}\n{\n…\n}` with LF separators; it starts
  `{\n` and ends `\n}` before the NUL.
* The **only** `?` characters anywhere in the text are `"model" "?N"` trigger
  references, each on a line of exactly that shape. The count equals the
  trigger model count and the indices cover `0 .. count-1`.
* **Zero** `"model" "*N"` static brush-submodel references, in any of the nine.
  Their base maps carry 165–337 of them (`script_brushmodel`,
  `script_vehicle_collmap`).
* The first entity is always a `worldspawn`.

---

## 3. Composition semantics: overlay, not replace

**Decision: the addon entity string is APPENDED to the base map's, minus the
addon's own leading `worldspawn`, with every addon `?N` biased by the base's
trigger model count.** The evidence:

1. MEASURED — no addon references a single `*N` brush entity, while their base
   maps carry hundreds. An addon that replaced the base string would delete
   every `script_brushmodel` in the level (334 on `mp_killhouse_sh`, 246 on
   `mp_estate_tropical`, …). The addon cannot stand alone.
2. MEASURED — seven of the nine carry **no** `minimap_corner` entity at all,
   while every base map carries exactly two. Replacing would leave those seven
   coop maps with no minimap data, and `maps/_compass.gsc` requires exactly two.
3. MEASURED — the coop zones ship no `col_map_mp`/`com_map`/`game_map_mp`/
   `gfx_map`/`map_ents`; the geometry the addon's triggers and origins sit in
   *is* the base map's. The base level zone and the coop playlist zone are both
   mounted for a coop match (the client's own `ClientLoadTime` line, quoted in
   `src/codol/assets/codol_asset_commands.c:480`).
4. MEASURED — the addon's leading `worldspawn` must not become entity 0 and
   must not become a stray gentity. `G_SpawnEntitiesFromString`
   (`src/asmsource/_g_spawn_mp.asm:1423`) parses one entity, calls
   `SP_worldspawn` unconditionally on it, and then never looks at the classname
   `worldspawn` again — a second one matches neither `s_bspOnlySpawns` nor
   `s_bspOrDynamicSpawns` and falls through to a bare `G_Spawn`. Of the
   server-visible worldspawn keys (`northyaw`, `gravity`, `ambienttrack`,
   `message`, per the `_cstring_*` set `SP_worldspawn` references), every addon
   either omits them or repeats the base value, and two base maps
   (`mp_estate_tropical`, `northyaw 144`) carry one the addon omits. So keeping
   the **base** worldspawn as entity 0 and dropping the addon's loses nothing
   and preserves something.
5. MEASURED — `"?N"` indexes the trigger model array of the MapEnts the entity
   came from, so concatenating two entity strings requires biasing the addon's
   indices. `CODOL_AppendNativeTriggers`
   (`src/codol/collision/codol_trigger_native.c`) turns that array into one
   contiguous submodel range starting at `trigger_model_base`, so merging the
   arrays *before* it runs leaves that code untouched.

INFERRED, not proven: IW4 keeps `cm_mapEnts2` and `Com_IsAddonMap` as separate
symbols (both present in `D:/CoD/iw4x_development/iw4mp.pdb`, alongside
`Load_AddonMapEnts` and `aAddon_map_ents`), which suggests IW4 held the addon
as a *second* MapEnts rather than splicing one string. I did not disassemble
IW4's consumer — no `iw4mp.exe` is on disk — and C1.exe is stripped of every
related string (`strings C1.exe | grep -i mapents` yields only the asset-name
literal `addon_map_ents` at file offset 0x84d5ec). Splicing one string reaches
the same parser with the same entities and needs no change to
`CM_EntityString`, `G_SpawnEntitiesFromString` or the trigger code, so that is
what is implemented. If a later pass reads IW4's consumer and it turns out to
parse the addon as a separate pass, the observable difference would be in
`?N` resolution — which this implementation gets right by construction.

---

## 4. What was implemented

| file | change |
|---|---|
| `src/codol/assets/codol_assets.h` | `CODOL_ASSET_MAP_ENTS 19`, `CODOL_ASSET_ADDON_MAP_ENTS 42`; declarations for `CODOL_ReadAddonMapEntities` and `CODOL_MergeMapEntities`. |
| `src/codol/collision/codol_map_entities.c` | `CODOL_ReadMapEntities` refactored onto a header-size-parameterised `read_map_entities`; new `CODOL_ReadAddonMapEntities` (36-byte header, no stages); new `CODOL_MergeMapEntities`. |
| `src/codol/collision/codol_collision.h` | declares `CODOL_LoadMountedAddonMapEntities`. |
| `src/codol/assets/codol_asset_registry.c` | `CODOL_LoadMountedAddonMapEntities(playlist, out)`: walks each mounted zone's directory backwards for a type-42 asset named `maps/mp/<playlist>.mapents`, resolving inline or pooled names. Type 42 has no `record_asset()` entry, so it cannot use the dependency index; this mirrors `CODOL_FindRawFileStatus`. Returns 1 / 0 / -1. |
| `src/codol/assets/codol_sv_xmodel.c` | `CODOL_InstallEngineClipMap` overlays the addon between `CODOL_LoadEngineCollisionMap` and `CODOL_BuildEngineClipMap`, keyed on `CODOL_SessionMapName()` differing from the level name. Logs the before/after sizes; warns (does not fail) when no addon is mounted; fails the load when one is present but unreadable or uncomposable. |

`CODOL_MergeMapEntities` produces one owned `codol_map_entities_t`:

* text = base text (NUL dropped) + `\n` + addon text after its worldspawn
  block, with every `"model" "?N"` rewritten to `?N+base.model_count`; a single
  trailing NUL. The rewriter refuses (rather than guesses) if a `?` is not
  preceded by `"model" "` at a line start, or is not followed by digits and a
  closing quote at a line end — a mis-rewrite silently rebinds a trigger volume
  to the wrong brush.
* models/hulls/slabs = base then addon, with each addon model's first-hull
  index biased by `base.hull_count` and each addon hull's first-slab index by
  `base.slab_count`, u16-range-checked.
* stages = the base's (addons carry none; the merge refuses an addon that does).

### Ordering (MEASURED, code read)

`SV_SpawnServer` installs the session map name at `src/sv_main.c:5553-5554`,
mounts the archives at `:5555` (the mount list includes the playlist zone —
`codol_asset_commands.c` `names[3]=session`), and calls `CM_LoadMap` at `:5654`
→ `CM_LoadMapData_FastFile` → `CODOL_InstallEngineClipMap`. The addon is
mounted and the session name is set before the overlay runs.

### `g_assetNames` was deliberately NOT changed

`src/asmsource/_db_assetnames.asm` `g_assetNames` and the `XAssetType` enum in
`src/xassets.h` are the **IW3** 33-type numbering, and `g_poolSize[]`,
`DB_XAssetPool[]`, `DB_GetXAssetSizeHandler[]` and the Set/GetName handler
tables are all indexed by it. The CoDOL/IW4 zone numbering that
`codol_load_blocks.c` dispatches on disagrees with it from index 1 onwards
(IW4 inserts `phys_collmap`, `xmodelsurfs`, `pixelshader`, `vertexshader`,
`vertexdecl`). Writing `addon_map_ents` into slot 42 of a 33-entry IW3 table
would be meaningless at best; renumbering the enum to IW4 would touch every
retained DB consumer for no gain, because the CoDOL zone path never consults
`g_assetNames` (its only readers are `src/bspc/db_miniload.cpp` and the
retained `_db_registry.asm`). The asset type is registered where it is actually
dispatched: `CODOL_ASSET_ADDON_MAP_ENTS` in `codol_assets.h` and `case 42:` in
`CODOL_ReplayZoneAsset`.

---

## 5. Acceptance test (MEASURED)

`obj/_addon_test.c` compiles the shipped `codol_map_entities.c` against real
blobs extracted from the zones and merges each coop addon onto its base map.

Build and run (obj/ is git-ignored; regenerate the blobs first with
`python obj/_addon_base_dump.py`, which also re-asserts the §2 layout):

```
gcc -m32 -O1 -Wall -Wextra -I src/codol/assets -I src/codol/collision \
    -o obj/_tmp/addon_test.exe obj/_addon_test.c src/codol/collision/codol_map_entities.c -lm
obj/_tmp/addon_test.exe obj/_addon/base_mp_killhouse_sh.bin \
    obj/_addon/coop_training_mp_killhouse_sh.bin coop_training_mp_killhouse_sh
```

All nine pass (exit 0): every addon decodes with `consumed == extent`, every
merge succeeds, the merged text holds exactly one `worldspawn`, every merged
`"?N"` is in range, and **every** trigger model in the merged array decodes
through `CODOL_ReadTriggerModel` (128/128, 99/99, 170/170, 107/107, 124/124,
80/80, 152/152, 154/154, 177/177).

### The Spec Ops spawn classnames — the acceptance numbers

Counted in the base entity string, the addon entity string and the merged
string, by the C harness (`"classname" "<x>"\n` byte match):

| coop map | base `_so` | addon `_so` | merged `_so` | `_pmc` b/a/m | `_pmcDefend` b/a/m |
|---|---:|---:|---:|---|---|
| `coop_defense_mp_crash_tropical` | 0 | 6 | **6** | 0/0/0 | 0/0/0 |
| `coop_prolog_mp_crash_intro` | 0 | 2 | **2** | 0/0/0 | 0/**2**/**2** |
| `coop_spec1_mp_killhouse_sh` | 0 | 1 | **1** | 0/0/0 | 0/0/0 |
| `coop_spec_mp_crash_tropical` | 0 | 2 | **2** | 0/0/0 | 0/**2**/**2** |
| `coop_spec_mp_estate_tropical` | 0 | 0 | 0 | 0/**2**/**2** | 0/0/0 |
| `coop_spec_mp_fav_tropical` | 0 | 0 | 0 | 0/**2**/**2** | 0/0/0 |
| `coop_take_mp_estate_tropical` | 0 | 2 | **2** | 0/0/0 | 0/0/0 |
| `coop_take_mp_fav_tropical` | 0 | 0 | 0 | 0/**4**/**4** | 0/0/0 |
| `coop_training_mp_killhouse_sh` | 0 | 2 | **2** | 0/0/0 | 0/0/0 |
| **total** | **0** | **15** | **15** | 0/**8**/**8** | 0/**4**/**4** |

Every base map contributes **zero** of all three classnames — confirming §2.3's
diagnosis — and every one the addon carries survives the merge intact. These
totals also fill in the two zones
(`coop_prolog_mp_crash_intro`, `coop_spec1_mp_killhouse_sh`) that
`CODOL_CATEGORY_SCRIPT_SETS_20260917.md` §2.4 could not extract; the other
seven agree with it exactly.

Merged sizes, for the record:

| coop map | text bytes (base → merged) | trigger models (base + addon = merged) |
|---|---|---|
| `coop_defense_mp_crash_tropical` | 285329 → 361339 | 93 + 35 = 128 |
| `coop_prolog_mp_crash_intro` | 276482 → 307105 | 81 + 18 = 99 |
| `coop_spec1_mp_killhouse_sh` | 227010 → 239942 | 143 + 27 = 170 |
| `coop_spec_mp_crash_tropical` | 285329 → 318588 | 93 + 14 = 107 |
| `coop_spec_mp_estate_tropical` | 313241 → 375886 | 93 + 31 = 124 |
| `coop_spec_mp_fav_tropical` | 316781 → 364571 | 61 + 19 = 80 |
| `coop_take_mp_estate_tropical` | 313241 → 391836 | 93 + 59 = 152 |
| `coop_take_mp_fav_tropical` | 316781 → 373467 | 61 + 93 = 154 |
| `coop_training_mp_killhouse_sh` | 227010 → 275732 | 143 + 34 = 177 |

`make objects` builds clean (exit 0); the only warnings are the three
pre-existing `src/sv_main.c` ones.

---

## 6. What still will not work

1. **Coop actors / enemy AI.** The bulk of every addon is
   `actor_enemy_favela_*_so`, `actor_enemy_desert_elite_*_so`,
   `actor_enemy_dog_so`, `actor_ally_codo_tf_*_so`, `actor_ally_hero_*_so`.
   Those classnames now *reach* the spawn parser, but nothing spawns an AI from
   them. That is the concurrent ACTOR workstream and was explicitly out of
   scope here; no file under `src/codol/player/codol_actor_*` or
   `bin/home/codol_rawfiles/zm/` was touched.
2. **`minimap_corner` duplication on the two killhouse coop maps.** MEASURED:
   `mp_killhouse_sh` carries 2 and both `coop_spec1_*` and `coop_training_*`
   carry 2 of their own, so the merged string has 4. `maps/_compass.gsc` and
   `maps/mp/_compass.gsc` both require exactly two and log
   "not exactly two `minimap_corner` entities" otherwise, so those two maps will
   skip minimap setup. The other seven addons carry none and inherit the base
   pair correctly. Fixing this needs a rule for which singleton map-metadata
   entities an addon overrides; I did not invent one, because the wrong rule
   silently deletes the wrong entity.
3. **Gentity budget is an open risk.** `MAX_GENTITIES` is 1024
   (`src/entity.h:514`). Counting entity blocks and removing the ones
   `G_SpawnEntitiesFromString` demonstrably skips (`node_*` via
   `CODOL_IsStoredPathNode`, `dyn_*` by prefix, `script_struct` because its
   spawn function is `G_FreeEntity`) gives an estimate of 774–1158 for the base
   maps alone and 1091–1400 merged. That estimate is **known to over-count** —
   `mp_killhouse_sh` estimates 1158 and multiplayer runs on it today — so the
   skip set above is incomplete and the real headroom has to be read off a live
   coop boot rather than from this arithmetic. It is flagged because the
   overlay adds 146–382 candidate entities per map and this is where it would
   show up first (`G_Spawn` running out).
4. **MP leftovers.** The base entity string still contributes its multiplayer
   spawn points and objective entities (`mp_tdm_spawn*`, `mp_dom_spawn*`,
   `mp_sd_spawn*`, `mp_ctf_spawn*`, `mp_dd_spawn*` …) to a coop match. They are
   inert unless a coop script asks for them by classname, and removing them is
   exactly the "replace" semantics §3 rules out, but they do occupy entity
   slots (see 3).
5. **No live verification.** Nothing here was checked against a running server
   or client — per the task constraints no server, lobby or client was started
   or stopped. The offline harness proves the decode, the composition and the
   spawn counts; it does not prove that a coop match boots.
6. **Only the nine shipped addons are proven.** `mp/basemaps.arena` names coop
   playlist entries with no zone on disk (`coop_chopper_mp_suburbs`,
   `coop_suspension_mp_bridge`, `coop_zac130_mp_derail`, …). Those still have
   nothing to load; `CODOL_LoadMountedAddonMapEntities` returns 0 and the
   overlay logs a warning and continues with the base entities.
