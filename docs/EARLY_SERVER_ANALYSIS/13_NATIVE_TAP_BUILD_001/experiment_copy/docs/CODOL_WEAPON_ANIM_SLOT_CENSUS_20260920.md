# WeaponDef xanim-name slot census, zm vs mp, 2026-09-20

Pure measurement pass on the shipped fastfiles.  Every number below is
read out of the zone bytes; nothing is inferred from IW4.

## 0. Method and layout authority

* The type-28 blob is the runtime `WeaponDef`: `blob[0:0xBFC]`, internal
  name the first inline string at `+0xBFC`.
* The xanim NAME array is **144 entries at `def+0x7c`**, not a guess:
  `replay_weapon()` (`src/codol/assets/codol_load_blocks.c:1254`) declares
  the field group `{0x7c, 144, STRING}`, and
  `CODOL_LoadMountedWeaponAnimations`
  (`src/codol/assets/codol_asset_registry.c:1245`) walks exactly those 144
  slots.  So slot *n* is at `def + 0x7c + 4n`; slot 7 = `+0x098`,
  slot 8 = `+0x09c`.
* A slot holds `0` (null), `0xFFFFFFFF` (the name follows inline, in field
  order) or a de-duplicated block-3 reference.  References were resolved
  offline: block 3 is bump-allocated in zone-asset order and each
  `replay_<type>()` puts the fixed part in block 0 and the rest in block 3,
  so a string at file offset F inside asset i has
  `block3 = (F - ACC(i)) - r` with `ACC(i)` the running sum of the block-0
  fixed sizes and `r` a locally constant residual.  `r` was fitted per
  weapon and cross-checked by majority vote across the weapons that share
  each reference.  Spot check: `coltanaconda_zm`'s references resolve to
  `viewmodel_coltanaconda_idle/fire/reload/pullout/putaway/sprint_*`, which
  are zone assets 2757..2764, i.e. the xanims serialized immediately before
  the weapon.

## 1. THE FALSIFICATION TEST -- `_zm` vs `_mp` twins at slots 7 and 8

Pooled empty string: `3007f4b7` in `common_gametype_zm` (used by 18593 of 21352 de-duplicated anim
slot references) and `3002f501` in `common_gametype_mp` (21531 of 24775).

| weapon | zone | slot 7 ref | slot 7 | slot 8 ref | slot 8 |
|---|---|---|---|---|---|
| `coltanaconda_zm` | common_gametype_zm | `3007f4b7` | **EMPTY** | `3007f4b7` | **EMPTY** |
| `coltanaconda_mp` | common_gametype_mp | `300f55bc` | `viewmodel_knife_melee_slice` | `300f6d5a` | `viewmodel_knife_melee_stab` |
| `m14ebr_zm` | common_gametype_zm | `3007f4b7` | **EMPTY** | `3007f4b7` | **EMPTY** |
| `m14ebr_mp` | common_gametype_mp | `300f55bc` | `viewmodel_knife_melee_slice` | `300f6d5a` | `viewmodel_knife_melee_stab` |
| `ranger_zm` | common_gametype_zm | `30205ddd` | `viewmodel_knife_melee_slice` | `3020757a` | `viewmodel_knife_melee_stab` |
| `ranger_mp` | common_gametype_mp | `300f55bc` | `viewmodel_knife_melee_slice` | `300f6d5a` | `viewmodel_knife_melee_stab` |
| `famas_zm` | common_gametype_zm | `3007f4b7` | **EMPTY** | `3007f4b7` | **EMPTY** |
| `famas_mp` | common_gametype_mp | `300f55bc` | `viewmodel_knife_melee_slice` | `300f6d5a` | `viewmodel_knife_melee_stab` |
| `ak104_zm` | common_gametype_zm | `3007f4b7` | **EMPTY** | `3007f4b7` | **EMPTY** |
| `ak104_mp` | common_gametype_mp | `300f55bc` | `viewmodel_knife_melee_slice` | `300f6d5a` | `viewmodel_knife_melee_stab` |

**Result: the thesis is NOT falsified by this comparison.**  The `_mp`
twins of the two reported weapons do NOT share the `_zm` empty slot:
`coltanaconda_mp` and `m14ebr_mp` both carry the pooled generic melee
pair at slots 7/8, while `coltanaconda_zm` and `m14ebr_zm` carry the
pooled EMPTY string.  Slots 7 and 8 really are the melee and
melee-charge xanim names, and the zm definitions really do leave them
empty.

So the reason those same weapons melee correctly in zm on the VANILLA
server has to lie OUTSIDE the weapon definition, and it does: see
`docs/CODOL_MELEE_C1_PATH_20260920.md`.  C1 `0x47c090` overrides anim
indices 7 and 8 from a `mp/coKnifeStatsTable.csv` row selected by
`ps+0x338`, gated on `def+0xbf0 == 0`, and when no row is selected and
the slot is empty it falls back to `szXAnims[1]` (idle), which reads on
screen as 'no melee animation'.  The census here is the data side of
that finding.

## 2. Full 144-slot dumps

Slots holding the pooled empty string or NULL are omitted from the
per-weapon listings below; every slot that holds something is shown.

### coltanaconda_zm  vs  coltanaconda_mp

```
    coltanaconda_zm                    asset 2768  8670 bytes   (common_gametype_zm)
      [  1] 30a67419  viewmodel_coltanaconda_idle
      [  2] 30a67419  viewmodel_coltanaconda_idle
      [  3] 30a67dd5  viewmodel_coltanaconda_fire
      [  5] 30a67dd5  viewmodel_coltanaconda_fire
      [  9] 30a68da7  viewmodel_coltanaconda_reload
      [ 11] 30a68da7  viewmodel_coltanaconda_reload
      [ 15] 30a6f1fc  viewmodel_coltanaconda_pullout
      [ 16] 30a6f1fc  viewmodel_coltanaconda_pullout
      [ 18] 30a71a42  viewmodel_coltanaconda_putaway
      [ 19] 30a6f1fc  viewmodel_coltanaconda_pullout
      [ 20] 30a71a42  viewmodel_coltanaconda_putaway
      [ 21] 30a6f1fc  viewmodel_coltanaconda_pullout
      [ 22] 30a71a42  viewmodel_coltanaconda_putaway
      [ 23] 30a6f1fc  viewmodel_coltanaconda_pullout
      [ 24] 30a71a42  viewmodel_coltanaconda_putaway
      [ 25] 30a744ae  viewmodel_coltanaconda_sprint_in
      [ 26] 30a75814  viewmodel_coltanaconda_sprint_loop
      [ 27] 30a76c8c  viewmodel_coltanaconda_sprint_out
      [ 34] ffffffff  (inline, run-scan) viewmodel_coltanaconda_ADS_fire
      [ 35] 30a7a1bd  codo_weapon_magnum_world   [UNCONFIRMED]
      [ 46] ffffffff  (inline, run-scan) viewmodel_coltanaconda_ADS_up
      [ 47] ffffffff  (inline, run-scan) viewmodel_coltanaconda_ADS_down

    coltanaconda_mp                    asset 419   6981 bytes   (common_gametype_mp)
      [  1] 302dc5d5  viewmodel_coltanaconda_idle
      [  2] 302dc5d5  viewmodel_coltanaconda_idle
      [  3] 302df2b3  viewmodel_coltanaconda_fire
      [  5] 302df2b3  viewmodel_coltanaconda_fire
      [  7] 300f55bc  viewmodel_knife_melee_slice <<< MELEE SLOT
      [  8] 300f6d5a  viewmodel_knife_melee_stab <<< MELEE SLOT
      [  9] 302e2019  viewmodel_coltanaconda_reload
      [ 11] 302e2019  viewmodel_coltanaconda_reload
      [ 15] 302f1513  viewmodel_coltanaconda_pullout
      [ 16] 302f1513  viewmodel_coltanaconda_pullout
      [ 17] 302f7654  viewmodel_coltanaconda_breach
      [ 18] 302fbe0c  viewmodel_coltanaconda_putaway
      [ 21] 302f1513  viewmodel_coltanaconda_pullout
      [ 22] 302fbe0c  viewmodel_coltanaconda_putaway
      [ 23] 302f1513  viewmodel_coltanaconda_pullout
      [ 24] 302fbe0c  viewmodel_coltanaconda_putaway
      [ 25] 30302231  viewmodel_coltanaconda_sprint_in
      [ 26] 3030578e  viewmodel_coltanaconda_sprint_loop
      [ 27] 3030958e  viewmodel_beretta_akimbo_l_nvg_takeoff
      [ 34] ffffffff  (inline, run-scan) viewmodel_coltanaconda_ADS_fire
      [ 35] 3030e6d5  viewmodel_beretta_akimbo_L_sprint_out
      [ 46] ffffffff  (inline, run-scan) viewmodel_coltanaconda_ADS_up
      [ 47] ffffffff  (inline, run-scan) viewmodel_coltanaconda_ADS_down
      [ 49] 302dcf91  viewmodel_coltanaconda_idle_r
      [ 50] 302dcf91  viewmodel_coltanaconda_idle_r
      [ 51] 302e0283  viewmodel_coltanaconda_fire_r
      [ 53] 302e0283  viewmodel_coltanaconda_fire_r
      [ 55] 300f55bc  viewmodel_knife_melee_slice
      [ 56] 300f6d5a  viewmodel_knife_melee_stab
      [ 57] 302e846c  viewmodel_coltanaconda_reload_r
      [ 59] 302e846c  viewmodel_coltanaconda_reload_r
      [ 63] 302f3d5a  viewmodel_coltanaconda_pullout_r
      [ 64] 302f3d5a  viewmodel_coltanaconda_pullout_r
      [ 66] 302fe876  viewmodel_coltanaconda_putaway_r
      [ 69] 302f3d5a  viewmodel_coltanaconda_pullout_r
      [ 70] 302fe876  viewmodel_coltanaconda_putaway_r
      [ 71] 302f3d5a  viewmodel_coltanaconda_pullout_r
      [ 72] 302fe876  viewmodel_coltanaconda_putaway_r
      [ 73] 30303598  viewmodel_coltanaconda_sprint_in_r
      [ 74] 30306c08  viewmodel_coltanaconda_sprint_loop_r
      [ 75] 3030a97a  viewmodel_coltanaconda_sprint_out_r
      [ 94] 3030e6f5  viewmodel_beretta_akimbo_L_NVG_puton
      [ 95] 3030e713  viewmodel_beretta_akimbo_L_NVG_takeoff
      [ 97] 302de1f4  viewmodel_coltanaconda_idle_l
      [ 98] 302de1f4  viewmodel_coltanaconda_idle_l
      [ 99] 302e1215  viewmodel_coltanaconda_fire_l
      [101] 302e1215  viewmodel_coltanaconda_fire_l
      [103] 300f55bc  viewmodel_knife_melee_slice
      [104] 300f6d5a  viewmodel_knife_melee_stab
      [105] 302ed76d  viewmodel_coltanaconda_reload_l
      [107] 302ed76d  viewmodel_coltanaconda_reload_l
      [111] 302f5e4c  viewmodel_coltanaconda_pullout_l
      [112] 302f5e4c  viewmodel_coltanaconda_pullout_l
      [114] 30300a09  viewmodel_coltanaconda_putaway_l
      [117] 302f5e4c  viewmodel_coltanaconda_pullout_l
      [118] 30300a09  viewmodel_coltanaconda_putaway_l
      [119] 302f5e4c  viewmodel_coltanaconda_pullout_l
      [120] 30300a09  viewmodel_coltanaconda_putaway_l
      [121] 30304691  viewmodel_coltanaconda_sprint_in_l
      [122] 303080a8  viewmodel_coltanaconda_sprint_loop_l
      [123] 3030ba77  viewmodel_beretta_fire_ads
      [142] 3030e6f5  viewmodel_beretta_akimbo_L_NVG_puton
      [143] 3030e713  viewmodel_beretta_akimbo_L_NVG_takeoff

```

### m14ebr_zm  vs  m14ebr_mp

```
    m14ebr_zm                          asset 2865  11224 bytes   (common_gametype_zm)
      [  1] 30ae8049  viewmodel_m14ebr_idle
      [  2] 30ae8049  viewmodel_m14ebr_idle
      [  3] 30ae8a94  viewmodel_m14ebr_fire
      [  5] 30ae8a94  viewmodel_m14ebr_fire
      [  9] 30ae9699  viewmodel_m14ebr_reload
      [ 11] 30aeeda8  viewmodel_m14ebr_reload_empty
      [ 15] 30af5b5e  viewmodel_m14ebr_pullout
      [ 16] 30af7bb1  viewmodel_m14ebr_pullout_first
      [ 18] 30afb6fb  viewmodel_m14ebr_putaway
      [ 19] 30af5b5e  viewmodel_m14ebr_pullout
      [ 20] 30afb6fb  viewmodel_m14ebr_putaway
      [ 21] 30afd351  viewmodel_m14ebr_pullout_fast
      [ 22] 30afb6fb  viewmodel_m14ebr_putaway
      [ 23] 30af5b5e  viewmodel_m14ebr_pullout
      [ 24] 30afb6fb  viewmodel_m14ebr_putaway
      [ 25] 30aff738  viewmodel_m14ebr_sprint_in
      [ 26] 30b00a87  viewmodel_m14ebr_sprint_loop
      [ 27] 30b01fab  viewmodel_m14ebr_sprint_out
      [ 34] 30b03365  viewmodel_m14ebr_fire_ads
      [ 35] 30b03365  viewmodel_m14ebr_fire_ads
      [ 46] 30b03e7a  viewmodel_m14ebr_ads_up
      [ 47] 30b03f23  viewmodel_m14ebr_ads_down

    m14ebr_mp                          asset 778   9994 bytes   (common_gametype_mp)
      [  1] 3052d165  viewmodel_m14ebr_idle
      [  2] 3052d165  viewmodel_m14ebr_idle
      [  3] 3052dbb0  viewmodel_m14ebr_fire
      [  5] 3052dbb0  viewmodel_m14ebr_fire
      [  7] 300f55bc  viewmodel_knife_melee_slice <<< MELEE SLOT
      [  8] 300f6d5a  viewmodel_knife_melee_stab <<< MELEE SLOT
      [  9] 3052e7b5  viewmodel_m14ebr_reload
      [ 11] 30533ec4  viewmodel_m14ebr_reload_empty
      [ 15] 3053ac7a  viewmodel_m14ebr_pullout
      [ 16] 3053cccd  viewmodel_m14ebr_pullout_first
      [ 17] 30540817  viewmodel_m14ebr_breach
      [ 18] 3054535f  viewmodel_m14ebr_putaway
      [ 21] 30546fb5  viewmodel_m14ebr_pullout_fast
      [ 22] 3054535f  viewmodel_m14ebr_putaway
      [ 23] 3053ac7a  viewmodel_m14ebr_pullout
      [ 24] 3054535f  viewmodel_m14ebr_putaway
      [ 25] 3054939c  viewmodel_m14ebr_sprint_in
      [ 26] 3054a6eb  viewmodel_m14ebr_sprint_loop
      [ 27] 3054bc0f  viewmodel_m14ebr_sprint_out
      [ 34] 3054cfc9  viewmodel_m14ebr_fire_ads
      [ 35] 3054cfc9  viewmodel_m14ebr_fire_ads
      [ 46] 3054dade  viewmodel_m14ebr_ads_up
      [ 47] 3054db87  viewmodel_m14ebr_ads_down

```

### ranger_zm  vs  ranger_mp

```
    ranger_zm                          asset 3183  6013 bytes   (common_gametype_zm)
      [  1] 30ccd471  viewmodel_ranger_idle
      [  2] 30ccd471  viewmodel_ranger_idle
      [  3] 30ccdbb0  viewmodel_ranger_fire
      [  5] 30ccdbb0  viewmodel_ranger_fire
      [  7] 30205ddd  viewmodel_knife_melee_slice <<< MELEE SLOT
      [  8] 3020757a  viewmodel_knife_melee_stab <<< MELEE SLOT
      [  9] 30cce762  viewmodel_ranger_reload
      [ 11] 30cce762  viewmodel_ranger_reload
      [ 15] 30cd319b  viewmodel_ranger_pullout
      [ 16] 30cd319b  viewmodel_ranger_pullout
      [ 18] 30cd5602  viewmodel_ranger_putaway
      [ 19] 30cd319b  viewmodel_ranger_pullout
      [ 20] 30cd5602  viewmodel_ranger_putaway
      [ 21] 30cd319b  viewmodel_ranger_pullout
      [ 22] 30cd5602  viewmodel_ranger_putaway
      [ 23] 30cd319b  viewmodel_ranger_pullout
      [ 24] 30cd5602  viewmodel_ranger_putaway
      [ 25] 30cd6c4b  viewmodel_ranger_sprint_in
      [ 26] 30cd7981  viewmodel_ranger_sprint_loop
      [ 27] 30cd884d  viewmodel_ranger_sprint_out
      [ 34] 30ccdbb0  viewmodel_ranger_fire
      [ 35] 30ccdbb0  viewmodel_ranger_fire
      [ 36] 30ccd471  viewmodel_ranger_idle
      [ 46] ffffffff  (inline) <inline, unlocated>
      [ 47] 30cd9c7d  viewmodel_ranger_pullout   [UNCONFIRMED]

    ranger_mp                          asset 1422  7507 bytes   (common_gametype_mp)
      [  1] 3091c805  viewmodel_ranger_idle
      [  2] 3091c805  viewmodel_ranger_idle
      [  3] 3091e1bd  viewmodel_ranger_fire
      [  5] 3091e1bd  viewmodel_ranger_fire
      [  7] 300f55bc  viewmodel_knife_melee_slice <<< MELEE SLOT
      [  8] 300f6d5a  viewmodel_knife_melee_stab <<< MELEE SLOT
      [  9] 30920a4c  viewmodel_ranger_reload
      [ 11] 30920a4c  viewmodel_ranger_reload
      [ 15] 3092cc7d  viewmodel_ranger_pullout
      [ 16] 3092cc7d  viewmodel_ranger_pullout
      [ 17] 3093159a  viewmodel_ranger_breach
      [ 18] 30935e34  viewmodel_ranger_putaway
      [ 21] 3092cc7d  viewmodel_ranger_pullout
      [ 22] 30935e34  viewmodel_ranger_putaway
      [ 23] 3092cc7d  viewmodel_ranger_pullout
      [ 24] 30935e34  viewmodel_ranger_putaway
      [ 25] 3093a962  viewmodel_ranger_sprint_in
      [ 26] 3093d64d  viewmodel_ranger_sprint_loop
      [ 27] 30940f83  viewmodel_ranger_sprint_out
      [ 34] 3091e1bd  viewmodel_ranger_fire
      [ 35] 3091e1bd  viewmodel_ranger_fire
      [ 46] ffffffff  (inline, run-scan) viewmodel_ranger_ADS
      [ 47] 309444f9  viewmodel_usp_ADS_up   [UNCONFIRMED]
      [ 49] ffffffff  (inline, run-scan) viewmodel_ranger_akimbo_R_idle
      [ 50] 3094450e  viewmodel_usp_ADS_down   [UNCONFIRMED]
      [ 51] ffffffff  (inline, run-scan) viewmodel_ranger_akimbo_R_fire
      [ 53] 3094452d  viewmodel_akimbo_usp_idle_R   [UNCONFIRMED]
      [ 55] 300f55bc  viewmodel_knife_melee_slice
      [ 56] 300f6d5a  viewmodel_knife_melee_stab
      [ 57] ffffffff  (inline, run-scan) viewmodel_ranger_akimbo_R_reload
      [ 59] 3094454c  viewmodel_akimbo_usp_fire_R   [UNCONFIRMED]
      [ 63] ffffffff  (inline, run-scan) viewmodel_ranger_akimbo_R_pullout
      [ 64] 3094456d  viewmodel_akimbo_usp_lastshot_R   [UNCONFIRMED]
      [ 66] ffffffff  (inline, run-scan) viewmodel_ranger_akimbo_R_putaway
      [ 69] 3094456d  viewmodel_akimbo_usp_lastshot_R   [UNCONFIRMED]
      [ 70] 3094458f  viewmodel_akimbo_usp_reload_R   [UNCONFIRMED]
      [ 71] 3094456d  viewmodel_akimbo_usp_lastshot_R   [UNCONFIRMED]
      [ 72] 3094458f  viewmodel_akimbo_usp_reload_R   [UNCONFIRMED]
      [ 73] ffffffff  (inline, run-scan) viewmodel_ranger_akimbo_R_sprint_in
      [ 74] ffffffff  (inline, run-scan) viewmodel_ranger_akimbo_R_sprint_loop
      [ 75] ffffffff  (inline, run-scan) viewmodel_ranger_akimbo_R_sprint_out
      [ 94] 309444f9  viewmodel_usp_ADS_up   [UNCONFIRMED]
      [ 95] 309444f9  viewmodel_usp_ADS_up   [UNCONFIRMED]
      [ 97] ffffffff  (inline, run-scan) viewmodel_ranger_akimbo_L_idle
      [ 98] 30944620  viewmodel_akimbo_usp_empty_pullout_R   [UNCONFIRMED]
      [ 99] ffffffff  (inline, run-scan) viewmodel_ranger_akimbo_L_fire
      [101] 3094463f  viewmodel_akimbo_usp_empty_putaway_R   [UNCONFIRMED]
      [103] 300f55bc  viewmodel_knife_melee_slice
      [104] 300f6d5a  viewmodel_knife_melee_stab
      [105] ffffffff  (inline, run-scan) viewmodel_ranger_akimbo_L_reload
      [107] 3094465e  viewmodel_akimbo_usp_sprint_in_R   [UNCONFIRMED]
      [111] ffffffff  (inline, run-scan) viewmodel_ranger_akimbo_L_pullout
      [112] 3094467f  viewmodel_akimbo_usp_sprint_loop_R   [UNCONFIRMED]
      [114] ffffffff  (inline, run-scan) viewmodel_ranger_akimbo_L_putaway
      [117] 3094467f  viewmodel_akimbo_usp_sprint_loop_R   [UNCONFIRMED]
      [118] 309446a1  viewmodel_akimbo_usp_sprint_out_R   [UNCONFIRMED]
      [119] 3094467f  viewmodel_akimbo_usp_sprint_loop_R   [UNCONFIRMED]
      [120] 309446a1  viewmodel_akimbo_usp_sprint_out_R   [UNCONFIRMED]
      [121] ffffffff  (inline, run-scan) viewmodel_ranger_akimbo_L_sprint_in
      [122] ffffffff  (inline, run-scan) viewmodel_ranger_akimbo_L_sprint_loop
      [123] ffffffff  (inline, run-scan) viewmodel_ranger_akimbo_L_sprint_out
      [142] 309444f9  viewmodel_usp_ADS_up   [UNCONFIRMED]
      [143] 309444f9  viewmodel_usp_ADS_up   [UNCONFIRMED]

```

### famas_zm  vs  famas_mp

```
    famas_zm                           asset 2963  11338 bytes   (common_gametype_zm)
      [  1] 30b7b041  viewmodel_famas_idle
      [  2] 30b7b041  viewmodel_famas_idle
      [  3] 30b7b9cd  viewmodel_famas_fire
      [  5] 30b7b9cd  viewmodel_famas_fire
      [  9] 30b7c662  viewmodel_famas_reload
      [ 11] 30b829d4  viewmodel_famas_reload_empty
      [ 15] 30b89c25  viewmodel_famas_pullout
      [ 16] 30b89c25  viewmodel_famas_pullout
      [ 18] 30b8c066  viewmodel_famas_putaway
      [ 19] 30b89c25  viewmodel_famas_pullout
      [ 20] 30b8c066  viewmodel_famas_putaway
      [ 21] 30b89c25  viewmodel_famas_pullout
      [ 22] 30b8c066  viewmodel_famas_putaway
      [ 23] 30b89c25  viewmodel_famas_pullout
      [ 24] 30b8c066  viewmodel_famas_putaway
      [ 25] 30b8dffc  viewmodel_famas_sprint_in
      [ 26] 30b8f3a2  viewmodel_famas_sprint_loop
      [ 27] 30b908ef  viewmodel_famas_sprint_out
      [ 34] ffffffff  (inline) <inline, unlocated>
      [ 35] 30b93fe5  <unresolved>
      [ 46] ffffffff  (inline) <inline, unlocated>
      [ 47] ffffffff  (inline) <inline, unlocated>

    famas_mp                           asset 534   10293 bytes   (common_gametype_mp)
      [  1] 303b67ee  viewmodel_famas_idle
      [  2] 303b67ee  viewmodel_famas_idle
      [  3] 303b7179  viewmodel_famas_fire
      [  5] 303b7179  viewmodel_famas_fire
      [  7] 300f55bc  viewmodel_knife_melee_slice <<< MELEE SLOT
      [  8] 300f6d5a  viewmodel_knife_melee_stab <<< MELEE SLOT
      [  9] 303b7e0e  viewmodel_famas_reload
      [ 11] 303be180  viewmodel_famas_reload_empty
      [ 15] 303c53d1  viewmodel_famas_pullout
      [ 16] 303c53d1  viewmodel_famas_pullout
      [ 17] 303c7812  viewmodel_famas_breach
      [ 18] 303cd07a  viewmodel_famas_putaway
      [ 21] 303c53d1  viewmodel_famas_pullout
      [ 22] 303cd07a  viewmodel_famas_putaway
      [ 23] 303c53d1  viewmodel_famas_pullout
      [ 24] 303cd07a  viewmodel_famas_putaway
      [ 25] 303cf010  viewmodel_famas_sprint_in
      [ 26] 303d03b6  viewmodel_famas_sprint_loop
      [ 27] 303d1903  viewmodel_famas_sprint_out
      [ 34] ffffffff  (inline) <inline, unlocated>
      [ 35] 303d4da9  viewmodel_famas_gl_reload_empty   [UNCONFIRMED]
      [ 46] ffffffff  (inline) <inline, unlocated>
      [ 47] ffffffff  (inline) <inline, unlocated>

```

### ak104_zm  vs  ak104_mp

```
    ak104_zm                           asset 3348  13275 bytes   (common_gametype_zm)
      [  1] 30e0a2e5  viewmodel_ak47_tac_idle
      [  2] 30e0a2e5  viewmodel_ak47_tac_idle
      [  3] 30e0ac91  viewmodel_ak47_tac_fire
      [  5] 30e0ac91  viewmodel_ak47_tac_fire
      [  9] 30e0baec  viewmodel_ak104_tac_reload
      [ 11] 30e10d60  viewmodel_ak104_tac_reload_empty
      [ 15] 30e177ef  viewmodel_ak47_tac_pullout
      [ 16] 30e19c5e  viewmodel_ak47_tac_first_time_pullout
      [ 18] 30e1d9a6  viewmodel_ak47_tac_putaway
      [ 19] 30e177ef  viewmodel_ak47_tac_pullout
      [ 20] 30e1d9a6  viewmodel_ak47_tac_putaway
      [ 21] 30e1f89f  viewmodel_ak47_tac_pullout_quick
      [ 22] 30e21fb2  viewmodel_ak47_tac_putaway_quick
      [ 23] 30e177ef  viewmodel_ak47_tac_pullout
      [ 24] 30e1d9a6  viewmodel_ak47_tac_putaway
      [ 25] 30e236b8  viewmodel_ak47_tac_sprint_in
      [ 26] 30e24c37  viewmodel_ak47_tac_sprint_loop
      [ 27] 30e26546  viewmodel_ak47_tac_sprint_out
      [ 34] ffffffff  (inline, run-scan) viewmodel_ak47_tac_ADS_fire
      [ 35] 30e2a7c1  <unresolved>
      [ 46] ffffffff  (inline, run-scan) viewmodel_ak47_tac_ADS_up
      [ 47] ffffffff  (inline, run-scan) viewmodel_ak47_tac_ADS_down

    ak104_mp                           asset 210   12644 bytes   (common_gametype_mp)
      [  1] 301a5991  viewmodel_ak47_tac_idle
      [  3] 301a633d  viewmodel_ak47_tac_fire
      [  5] 301a633d  viewmodel_ak47_tac_fire
      [  7] 300f55bc  viewmodel_knife_melee_slice <<< MELEE SLOT
      [  8] 300f6d5a  viewmodel_knife_melee_stab <<< MELEE SLOT
      [  9] 301a7198  viewmodel_ak104_tac_reload
      [ 11] 301ac40c  viewmodel_ak104_tac_reload_empty
      [ 15] 301b2e9b  viewmodel_ak47_tac_pullout
      [ 16] 301b530a  viewmodel_ak47_tac_first_time_pullout
      [ 17] 301b9052  viewmodel_ak47_tac_breach
      [ 18] 301bd849  viewmodel_ak47_tac_putaway
      [ 21] 301bf743  viewmodel_ak47_tac_pullout_quick
      [ 22] 301c1e56  viewmodel_ak47_tac_putaway_quick
      [ 23] 301b2e9b  viewmodel_ak47_tac_pullout
      [ 24] 301bd849  viewmodel_ak47_tac_putaway
      [ 25] 301c355c  viewmodel_ak47_tac_sprint_in
      [ 26] 301c4adb  viewmodel_ak47_tac_sprint_loop
      [ 27] 301c63ea  viewmodel_ak47_tac_sprint_out
      [ 34] ffffffff  (inline) <inline, unlocated>
      [ 35] 301ca2a5  <unresolved>
      [ 46] ffffffff  (inline) <inline, unlocated>
      [ 47] ffffffff  (inline) <inline, unlocated>

```

### zm-only weapons

```
    m1911_upgraded_zm                  asset 2753  7497 bytes   (common_gametype_zm)
      [  1] 30a2c0e1  viewmodel_usp_idle
      [  2] 30a2c0e1  viewmodel_usp_idle
      [  3] 30a2fb21  viewmodel_usp_fire
      [  5] 30a31e04  viewmodel_usp_lastfire
      [  7] 30205ddd  viewmodel_knife_melee_slice <<< MELEE SLOT
      [  8] 3020757a  viewmodel_knife_melee_stab <<< MELEE SLOT
      [  9] 30a340ad  viewmodel_usp_reload
      [ 15] 30a3c606  viewmodel_usp_pullout
      [ 16] 30a3c606  viewmodel_usp_pullout
      [ 17] 30a418b5  viewmodel_usp_breach
      [ 18] 30a4e6bb  viewmodel_usp_putaway
      [ 21] 30a3c606  viewmodel_usp_pullout
      [ 22] 30a4e6bb  viewmodel_usp_putaway
      [ 23] 30a3c606  viewmodel_usp_pullout
      [ 24] 30a4e6bb  viewmodel_usp_putaway
      [ 25] 30a5951d  viewmodel_usp_sprint_in
      [ 26] 30a5c360  viewmodel_usp_sprint_loop
      [ 27] 30a5fed4  viewmodel_usp_sprint_out
      [ 34] 30a62ad4  viewmodel_usp_fire_ads
      [ 35] 30a31e04  viewmodel_usp_lastfire
      [ 37] 30a634c5  viewmodel_colt1911_dw_full_d2p_in
      [ 38] 30a63f1f  viewmodel_colt1911_dw_full_d2p_loop
      [ 39] 30a64ec6  viewmodel_colt1911_dw_full_d2p_out
      [ 46] ffffffff  (inline, run-scan) viewmodel_usp_ADS_up
      [ 47] ffffffff  (inline, run-scan) viewmodel_usp_ADS_down
      [ 49] ffffffff  (inline, run-scan) viewmodel_akimbo_usp_idle_R
      [ 50] ffffffff  (inline, run-scan) viewmodel_akimbo_usp_empty_idle_R
      [ 51] ffffffff  (inline, run-scan) viewmodel_akimbo_usp_fire_R
      [ 53] ffffffff  (inline, run-scan) viewmodel_akimbo_usp_lastshot_R
      [ 55] 3020757a  viewmodel_knife_melee_stab
      [ 56] 3020757a  viewmodel_knife_melee_stab
      [ 57] ffffffff  (inline, run-scan) viewmodel_akimbo_usp_reload_R
      [ 63] ffffffff  (inline, run-scan) viewmodel_akimbo_usp_pullout_R
      [ 64] 30a664e9  <unresolved>
      [ 65] ffffffff  (inline, run-scan) viewmodel_akimbo_usp_breach_R
      [ 66] ffffffff  (inline, run-scan) viewmodel_akimbo_usp_putaway_R
      [ 69] 30a664e9  <unresolved>
      [ 70] 30a66526  <unresolved>
      [ 71] ffffffff  (inline, run-scan) viewmodel_akimbo_usp_empty_pullout_R
      [ 72] ffffffff  (inline, run-scan) viewmodel_akimbo_usp_empty_putaway_R
      [ 73] ffffffff  (inline, run-scan) viewmodel_akimbo_usp_sprint_in_R
      [ 74] ffffffff  (inline, run-scan) viewmodel_akimbo_usp_sprint_loop_R
      [ 75] ffffffff  (inline, run-scan) viewmodel_akimbo_usp_sprint_out_R
      [ 82] 30a6648f  viewmodel_akimbo_usp_ads_down_l   [UNCONFIRMED]
      [ 83] 30a664ab  <unresolved>
      [ 94] ffffffff  (inline, run-scan) viewmodel_akimbo_usp_ADS_up_R
      [ 95] ffffffff  (inline, run-scan) viewmodel_akimbo_usp_ADS_down_R
      [ 97] ffffffff  (inline, run-scan) viewmodel_akimbo_usp_idle_L
      [ 98] ffffffff  (inline, run-scan) viewmodel_akimbo_usp_empty_idle_L
      [ 99] ffffffff  (inline, run-scan) viewmodel_akimbo_usp_fire_L
      [101] ffffffff  (inline, run-scan) viewmodel_akimbo_usp_lastshot_L
      [103] 3020757a  viewmodel_knife_melee_stab
      [104] 3020757a  viewmodel_knife_melee_stab
      [105] ffffffff  (inline, run-scan) viewmodel_akimbo_usp_reload_L
      [111] ffffffff  (inline, run-scan) viewmodel_akimbo_usp_pullout_L
      [112] 30a666cb  viewmodel_usp   [UNCONFIRMED]
      [113] ffffffff  (inline, run-scan) viewmodel_akimbo_usp_breach_L
      [114] ffffffff  (inline, run-scan) viewmodel_akimbo_usp_putaway_L
      [117] 30a666cb  viewmodel_usp   [UNCONFIRMED]
      [118] 30a66708  viewmodel_akimbo_usp_lastshot_R   [UNCONFIRMED]
      [119] ffffffff  (inline, run-scan) viewmodel_akimbo_usp_empty_pullout_L
      [120] ffffffff  (inline, run-scan) viewmodel_akimbo_usp_empty_putaway_L
      [121] ffffffff  (inline, run-scan) viewmodel_akimbo_usp_sprint_in_L
      [122] ffffffff  (inline, run-scan) viewmodel_akimbo_usp_sprint_loop_L
      [123] ffffffff  (inline, run-scan) viewmodel_akimbo_usp_sprint_out_L
      [130] 30a66671  viewmodel_coltanaconda_sprint_out   [UNCONFIRMED]
      [131] 30a6668d  viewmodel_usp_ADS_up   [UNCONFIRMED]
      [142] ffffffff  (inline, run-scan) viewmodel_akimbo_usp_ADS_up_L
      [143] ffffffff  (inline, run-scan) viewmodel_akimbo_usp_ADS_down_L

    glockdw_zm                         asset 3123  3103 bytes   (common_gametype_zm)
      [  1] 30a7d1b5  viewmodel_glock_idle
      [  2] 30a7d1b5  viewmodel_glock_idle
      [  3] 30a7e66d  viewmodel_glock_fire
      [  5] 30a7e66d  viewmodel_glock_fire
      [  7] 30205ddd  viewmodel_knife_melee_slice <<< MELEE SLOT
      [  8] 3020757a  viewmodel_knife_melee_stab <<< MELEE SLOT
      [  9] 30a7f209  viewmodel_glock_reload
      [ 11] 30a84487  viewmodel_glock_reload_empty
      [ 15] 30a8a660  viewmodel_glock_pullout
      [ 16] 30a8bb5c  viewmodel_glock_first_time_pullout
      [ 17] 30c78ec1  viewmodel_glock_breach_v1
      [ 18] 30a8eea3  viewmodel_glock_putaway
      [ 21] 30a8a660  viewmodel_glock_pullout
      [ 22] 30a8eea3  viewmodel_glock_putaway
      [ 23] 30a8a660  viewmodel_glock_pullout
      [ 24] 30a8eea3  viewmodel_glock_putaway
      [ 25] 30a903f8  viewmodel_glock_sprint_in
      [ 26] 30a91b00  viewmodel_glock_sprint_loop
      [ 27] 30a93695  viewmodel_glock_sprint_out
      [ 37] 30c8e477  viewmodel_cz75_dw_full_d2p_in
      [ 38] 30c8ef0b  viewmodel_cz75_dw_full_d2p_loop
      [ 39] 30c8feba  viewmodel_cz75_dw_full_d2p_out
      [ 49] 30c64a05  viewmodel_glock_akimbo_idle_r
      [ 50] 30c64a05  viewmodel_glock_akimbo_idle_r
      [ 51] 30c66b11  viewmodel_glock_akimbo_fire_r
      [ 53] 30c66b11  viewmodel_glock_akimbo_fire_r
      [ 55] 30205ddd  viewmodel_knife_melee_slice
      [ 56] 3020757a  viewmodel_knife_melee_stab
      [ 57] 30c6844f  viewmodel_glock_akimbo_reload_r
      [ 59] 30c6eaac  viewmodel_glock_akimbo_reload_empty_r
      [ 63] 30c761e9  viewmodel_glock_akimbo_pullout_r
      [ 64] 30c761e9  viewmodel_glock_akimbo_pullout_r
      [ 65] 30c7db19  viewmodel_glock_akimbo_breach_v1_r
      [ 66] 30c84e17  viewmodel_glock_akimbo_putaway_r
      [ 69] 30c761e9  viewmodel_glock_akimbo_pullout_r
      [ 70] 30c84e17  viewmodel_glock_akimbo_putaway_r
      [ 71] 30c761e9  viewmodel_glock_akimbo_pullout_r
      [ 72] 30c84e17  viewmodel_glock_akimbo_putaway_r
      [ 73] 30c87a7f  viewmodel_glock_akimbo_sprint_in_r
      [ 74] 30c89b2d  viewmodel_glock_akimbo_sprint_loop_r
      [ 75] 30c8c435  viewmodel_glock_akimbo_sprint_out_r
      [ 97] 30c6581f  viewmodel_glock_akimbo_idle_l
      [ 98] 30c6581f  viewmodel_glock_akimbo_idle_l
      [ 99] 30c67695  viewmodel_glock_akimbo_fire_l
      [101] 30c67695  viewmodel_glock_akimbo_fire_l
      [103] 30205ddd  viewmodel_knife_melee_slice
      [104] 3020757a  viewmodel_knife_melee_stab
      [105] 30c6b03f  viewmodel_glock_akimbo_reload_l
      [107] 30c71df6  viewmodel_glock_akimbo_reload_empty_l
      [111] 30c7774c  viewmodel_glock_akimbo_pullout_l
      [112] 30c7774c  viewmodel_glock_akimbo_pullout_l
      [113] 30c8112e  viewmodel_glock_akimbo_breach_v1_l
      [114] 30c86322  viewmodel_glock_akimbo_putaway_l
      [117] 30c7774c  viewmodel_glock_akimbo_pullout_l
      [118] 30c86322  viewmodel_glock_akimbo_putaway_l
      [119] 30c7774c  viewmodel_glock_akimbo_pullout_l
      [120] 30c86322  viewmodel_glock_akimbo_putaway_l
      [121] 30c88a4e  viewmodel_glock_akimbo_sprint_in_l
      [122] 30c8af7e  viewmodel_glock_akimbo_sprint_loop_l
      [123] 30c8d3bf  viewmodel_glock_akimbo_sprint_out_l

    knife_ballistic_zm                 asset 3556  23696 bytes   (common_gametype_zm)
      [  1] 30f6a85d  viewmodel_b_knife_zm_idle_loop
      [  2] 30f6a85d  viewmodel_b_knife_zm_idle_loop
      [  3] 30f6c650  viewmodel_b_knife_zm_fire
      [  5] 30f6c650  viewmodel_b_knife_zm_fire
      [  7] 30f6d78a  viewmodel_b_knife_zm_melee_swipe <<< MELEE SLOT
      [  8] 30f6e913  viewmodel_b_knife_zm_melee_stick <<< MELEE SLOT
      [  9] 30f7020d  viewmodel_b_knife_zm_reload
      [ 15] 30f73098  viewmodel_b_knife_zm_pullout
      [ 16] 30f75334  viewmodel_b_knife_zm_first_raise
      [ 18] 30f772a6  viewmodel_b_knife_zm_putaway
      [ 19] 30f73098  viewmodel_b_knife_zm_pullout
      [ 20] 30f772a6  viewmodel_b_knife_zm_putaway
      [ 21] 30f78581  viewmodel_b_knife_zm_pullout_quick
      [ 22] 30f772a6  viewmodel_b_knife_zm_putaway
      [ 23] 30f73098  viewmodel_b_knife_zm_pullout
      [ 24] 30f772a6  viewmodel_b_knife_zm_putaway
      [ 25] 30f79550  viewmodel_b_knife_zm_sprint_in
      [ 26] 30f7a1f8  viewmodel_b_knife_zm_sprint_loop
      [ 27] 30f7b2d5  viewmodel_b_knife_zm_sprint_out
      [ 34] 30f6c650  viewmodel_b_knife_zm_fire
      [ 35] 30f6c650  viewmodel_b_knife_zm_fire
      [ 37] 30f7bf7d  viewmodel_b_knife_d2p_in
      [ 38] 30f7cc92  viewmodel_b_knife_d2p_loop
      [ 39] 30f7db4d  viewmodel_b_knife_d2p_out
      [ 46] 30f7e8c7  viewmodel_b_knife_zm_ads_up
      [ 47] 30f7e8fd  viewmodel_b_knife_zm_ads_down

    knife_ballistic_upgraded_zm        asset 3557  3136 bytes   (common_gametype_zm)
      [  1] 30f6a85d  viewmodel_b_knife_zm_idle_loop
      [  2] 30f6a85d  viewmodel_b_knife_zm_idle_loop
      [  3] 30f6c650  viewmodel_b_knife_zm_fire
      [  5] 30f6c650  viewmodel_b_knife_zm_fire
      [  7] 30f6d78a  viewmodel_b_knife_zm_melee_swipe <<< MELEE SLOT
      [  8] 30f6e913  viewmodel_b_knife_zm_melee_stick <<< MELEE SLOT
      [  9] 30f7020d  viewmodel_b_knife_zm_reload
      [ 15] 30f73098  viewmodel_b_knife_zm_pullout
      [ 16] 30f75334  viewmodel_b_knife_zm_first_raise
      [ 18] 30f772a6  viewmodel_b_knife_zm_putaway
      [ 19] 30f73098  viewmodel_b_knife_zm_pullout
      [ 20] 30f772a6  viewmodel_b_knife_zm_putaway
      [ 21] 30f78581  viewmodel_b_knife_zm_pullout_quick
      [ 22] 30f772a6  viewmodel_b_knife_zm_putaway
      [ 23] 30f73098  viewmodel_b_knife_zm_pullout
      [ 24] 30f772a6  viewmodel_b_knife_zm_putaway
      [ 25] 30f79550  viewmodel_b_knife_zm_sprint_in
      [ 26] 30f7a1f8  viewmodel_b_knife_zm_sprint_loop
      [ 27] 30f7b2d5  viewmodel_b_knife_zm_sprint_out
      [ 34] 30f6c650  viewmodel_b_knife_zm_fire
      [ 35] 30f6c650  viewmodel_b_knife_zm_fire
      [ 37] 30f7bf7d  viewmodel_b_knife_d2p_in
      [ 38] 30f7cc92  viewmodel_b_knife_d2p_loop
      [ 39] 30f7db4d  viewmodel_b_knife_d2p_out
      [ 46] 30f7e8c7  viewmodel_b_knife_zm_ads_up
      [ 47] 30f7e8fd  viewmodel_b_knife_zm_ads_down

    knife_ballistic_bowie_zm           asset 3558  5657 bytes   (common_gametype_zm)
      [  1] 30f6a85d  viewmodel_b_knife_zm_idle_loop
      [  2] 30f6a85d  viewmodel_b_knife_zm_idle_loop
      [  3] 30f6c650  viewmodel_b_knife_zm_fire
      [  5] 30f6c650  viewmodel_b_knife_zm_fire
      [  7] 30f6d78a  viewmodel_b_knife_zm_melee_swipe <<< MELEE SLOT
      [  8] 30f6e913  viewmodel_b_knife_zm_melee_stick <<< MELEE SLOT
      [  9] 30f7020d  viewmodel_b_knife_zm_reload
      [ 15] 30f73098  viewmodel_b_knife_zm_pullout
      [ 16] 30f75334  viewmodel_b_knife_zm_first_raise
      [ 18] 30f772a6  viewmodel_b_knife_zm_putaway
      [ 19] 30f73098  viewmodel_b_knife_zm_pullout
      [ 20] 30f772a6  viewmodel_b_knife_zm_putaway
      [ 21] 30f78581  viewmodel_b_knife_zm_pullout_quick
      [ 22] 30f772a6  viewmodel_b_knife_zm_putaway
      [ 23] 30f73098  viewmodel_b_knife_zm_pullout
      [ 24] 30f772a6  viewmodel_b_knife_zm_putaway
      [ 25] 30f79550  viewmodel_b_knife_zm_sprint_in
      [ 26] 30f7a1f8  viewmodel_b_knife_zm_sprint_loop
      [ 27] 30f7b2d5  viewmodel_b_knife_zm_sprint_out
      [ 34] 30f6c650  viewmodel_b_knife_zm_fire
      [ 35] 30f6c650  viewmodel_b_knife_zm_fire
      [ 37] 30f7bf7d  viewmodel_b_knife_d2p_in
      [ 38] 30f7cc92  viewmodel_b_knife_d2p_loop
      [ 39] 30f7db4d  viewmodel_b_knife_d2p_out
      [ 46] 30f7e8c7  viewmodel_b_knife_zm_ads_up
      [ 47] 30f7e8fd  viewmodel_b_knife_zm_ads_down

    knife_ballistic_bowie_upgraded_zm  asset 3559  3102 bytes   (common_gametype_zm)
      [  1] 30f6a85d  viewmodel_b_knife_zm_idle_loop
      [  2] 30f6a85d  viewmodel_b_knife_zm_idle_loop
      [  3] 30f6c650  viewmodel_b_knife_zm_fire
      [  5] 30f6c650  viewmodel_b_knife_zm_fire
      [  7] 30f6d78a  viewmodel_b_knife_zm_melee_swipe <<< MELEE SLOT
      [  8] 30f6e913  viewmodel_b_knife_zm_melee_stick <<< MELEE SLOT
      [  9] 30f7020d  viewmodel_b_knife_zm_reload
      [ 15] 30f73098  viewmodel_b_knife_zm_pullout
      [ 16] 30f75334  viewmodel_b_knife_zm_first_raise
      [ 18] 30f772a6  viewmodel_b_knife_zm_putaway
      [ 19] 30f73098  viewmodel_b_knife_zm_pullout
      [ 20] 30f772a6  viewmodel_b_knife_zm_putaway
      [ 21] 30f78581  viewmodel_b_knife_zm_pullout_quick
      [ 22] 30f772a6  viewmodel_b_knife_zm_putaway
      [ 23] 30f73098  viewmodel_b_knife_zm_pullout
      [ 24] 30f772a6  viewmodel_b_knife_zm_putaway
      [ 25] 30f79550  viewmodel_b_knife_zm_sprint_in
      [ 26] 30f7a1f8  viewmodel_b_knife_zm_sprint_loop
      [ 27] 30f7b2d5  viewmodel_b_knife_zm_sprint_out
      [ 34] 30f6c650  viewmodel_b_knife_zm_fire
      [ 35] 30f6c650  viewmodel_b_knife_zm_fire
      [ 37] 30f7bf7d  viewmodel_b_knife_d2p_in
      [ 38] 30f7cc92  viewmodel_b_knife_d2p_loop
      [ 39] 30f7db4d  viewmodel_b_knife_d2p_out
      [ 46] 30f7e8c7  viewmodel_b_knife_zm_ads_up
      [ 47] 30f7e8fd  viewmodel_b_knife_zm_ads_down

    revive_knife_zm                    asset 164   3292 bytes   (common_gametype_zm)
      [  1] 301e4f95  viewmodel_knifethrow_hold_rhand
      [  2] 301e4f95  viewmodel_knifethrow_hold_rhand
      [  3] 301e58f5  viewmodel_knifethrow_throw_rhand
      [  4] 301e4f95  viewmodel_knifethrow_hold_rhand
      [  5] 301e58f5  viewmodel_knifethrow_throw_rhand
      [  7] 301e4f95  viewmodel_knifethrow_hold_rhand <<< MELEE SLOT
      [ 15] 301e4f95  viewmodel_knifethrow_hold_rhand
      [ 18] 301e4f95  viewmodel_knifethrow_hold_rhand
      [ 19] 301e4f95  viewmodel_knifethrow_hold_rhand
      [ 20] 301e4f95  viewmodel_knifethrow_hold_rhand

    zombie_bowie_flourish              asset 2667  3499 bytes   (common_gametype_zm)
      [  1] 30a01cd5  viewmodel_zombie_perksacola_idle
      [  2] 30a01cd5  viewmodel_zombie_perksacola_idle
      [  3] 30a01cd5  viewmodel_zombie_perksacola_idle
      [  4] 30a01cd5  viewmodel_zombie_perksacola_idle
      [  5] 30a023a1  viewmodel_zombie_perksacola_lower
      [ 15] 30a02eed  viewmodel_zombie_bowie
      [ 16] 30a02eed  viewmodel_zombie_bowie
      [ 18] 30a023a1  viewmodel_zombie_perksacola_lower
      [ 19] 30a02eed  viewmodel_zombie_bowie
      [ 20] 30a023a1  viewmodel_zombie_perksacola_lower
      [ 21] 30a02eed  viewmodel_zombie_bowie
      [ 22] 30a023a1  viewmodel_zombie_perksacola_lower
      [ 23] 30a02eed  viewmodel_zombie_bowie
      [ 24] 30a023a1  viewmodel_zombie_perksacola_lower
      [ 31] 30a01cd5  viewmodel_zombie_perksacola_idle

    zombie_melee                       asset 2674  12647 bytes   (common_gametype_zm)
      [  1] 30a04b9e  viewmodel_zombie_idle
      [  2] 30a04b9e  viewmodel_zombie_idle
      [  3] 30a0526d  viewmodel_zombie_fire
      [  5] 30a0526d  viewmodel_zombie_fire
      [  7] 30a0526d  viewmodel_zombie_fire <<< MELEE SLOT
      [  8] 30a0526d  viewmodel_zombie_fire <<< MELEE SLOT
      [  9] 30a04b9e  viewmodel_zombie_idle
      [ 15] 30a0677f  viewmodel_zombie_raise
      [ 16] 30a0677f  viewmodel_zombie_raise
      [ 18] 30a09eb7  viewmodel_zombie_lower
      [ 19] 30a0677f  viewmodel_zombie_raise
      [ 20] 30a09eb7  viewmodel_zombie_lower
      [ 21] 30a0677f  viewmodel_zombie_raise
      [ 22] 30a09eb7  viewmodel_zombie_lower
      [ 23] 30a0677f  viewmodel_zombie_raise
      [ 24] 30a09eb7  viewmodel_zombie_lower
      [ 34] 30a0526d  viewmodel_zombie_fire
      [ 35] 30a0526d  viewmodel_zombie_fire
      [ 46] ffffffff  (inline, run-scan) viewmodel_zombie_ADS_down
      [ 47] ffffffff  (inline, run-scan) viewmodel_zombie_ADS_up

    throwingknife_zm                   asset 156   8753 bytes   (common_gametype_zm)
      [  1] 301e4f95  viewmodel_knifethrow_hold_rhand
      [  2] 301e4f95  viewmodel_knifethrow_hold_rhand
      [  3] 301e58f5  viewmodel_knifethrow_throw_rhand
      [  4] 301e4f95  viewmodel_knifethrow_hold_rhand
      [  5] 301e58f5  viewmodel_knifethrow_throw_rhand
      [  7] 301e4f95  viewmodel_knifethrow_hold_rhand <<< MELEE SLOT
      [ 15] 301e4f95  viewmodel_knifethrow_hold_rhand
      [ 18] 301e4f95  viewmodel_knifethrow_hold_rhand
      [ 19] 301e4f95  viewmodel_knifethrow_hold_rhand
      [ 20] 301e4f95  viewmodel_knifethrow_hold_rhand

```

## 3. Byte diff of the 0xBFC definition between the twins

```
coltanaconda_zm        / coltanaconda_mp        : 679 of 0xBFC bytes differ in 234 runs
m14ebr_zm              / m14ebr_mp              : 815 of 0xBFC bytes differ in 319 runs
ranger_zm              / ranger_mp              : 776 of 0xBFC bytes differ in 265 runs
famas_zm               / famas_mp               : 751 of 0xBFC bytes differ in 270 runs
ak104_zm               / ak104_mp               : 736 of 0xBFC bytes differ in 264 runs
```

The twins are different assets built from different source GDTs, so the
byte diff is dense and carries no signal on its own.  What matters is
section 1.

## 4. Melee-name index histogram

For every slot index 0..143, how many weapon definitions hold a name
matching `melee|knife|slice|stab|swipe|bayonet|bash|gutcheck|flourish` there.  Only indices with a non-zero count are listed.

| slot | zm defs | mp defs |
|---|---|---|
| 1 | 6 | 0 |
| 2 | 6 | 0 |
| 3 | 6 | 0 |
| 4 | 2 | 0 |
| 5 | 6 | 0 |
| 7 | 40 | 133 |
| 8 | 38 | 133 |
| 9 | 4 | 0 |
| 15 | 6 | 0 |
| 16 | 4 | 0 |
| 18 | 6 | 0 |
| 19 | 6 | 0 |
| 20 | 6 | 0 |
| 21 | 4 | 0 |
| 22 | 4 | 0 |
| 23 | 4 | 0 |
| 24 | 4 | 0 |
| 25 | 4 | 0 |
| 26 | 4 | 0 |
| 27 | 4 | 0 |
| 34 | 4 | 0 |
| 35 | 4 | 0 |
| 37 | 4 | 0 |
| 38 | 4 | 0 |
| 39 | 4 | 0 |
| 46 | 4 | 0 |
| 47 | 4 | 0 |
| 55 | 7 | 15 |
| 56 | 7 | 15 |
| 103 | 7 | 15 |
| 104 | 7 | 15 |

## 5. Slot-7 census over every definition in each zone

* `common_gametype_zm`: 153 defs -- {'EMPTY': 109, 'pool': 44}
* `common_gametype_mp`: 178 defs -- {'pool': 142, 'unresolved': 4, 'EMPTY': 32}
* `patch_common_gametype_zm`: 18 defs -- {'inline': 1, 'pool': 13, 'EMPTY': 4}
* `patch_common_gametype_mp`: 43 defs -- {'inline': 1, 'pool': 36, 'unresolved': 2, 'EMPTY': 4}

### zm definitions whose slot 7 is NOT the empty string

```
  9É0Ì0ÿÿÿÿ                         30205ddd pool       viewmodel_knife_melee_slice
  WEAPON_M1911                         30205ddd pool       viewmodel_knife_melee_slice
  WEAPON_MP5                           30205ddd pool       viewmodel_knife_melee_slice
  at4_upgraded_zm                      30205ddd pool       viewmodel_knife_melee_slice
  at4_zm                               30205ddd pool       viewmodel_knife_melee_slice
  aug_acog_mk_upgraded_zm              30205ddd pool       viewmodel_knife_melee_slice
  bouncingbetty_zm                     30205ddd pool       viewmodel_knife_melee_slice
  c4_zm                                30205ddd pool       viewmodel_knife_melee_slice
  care_package_zm                      30205ddd pool       viewmodel_knife_melee_slice
  defaultweapon                        309fcf33 pool       viewmodel_default_fire
  glockdw_upgraded_zm                  30205ddd pool       viewmodel_knife_melee_slice
  glockdw_zm                           30205ddd pool       viewmodel_knife_melee_slice
  killstreak_sentry_mp                 30205ddd pool       viewmodel_knife_melee_slice
  knife_ballistic_bowie_upgraded_zm    30f6d78a pool       viewmodel_b_knife_zm_melee_swipe
  knife_ballistic_bowie_zm             30f6d78a pool       viewmodel_b_knife_zm_melee_swipe
  knife_ballistic_upgraded_zm          30f6d78a pool       viewmodel_b_knife_zm_melee_swipe
  knife_ballistic_zm                   30f6d78a pool       viewmodel_b_knife_zm_melee_swipe
  m1911_upgraded_zm                    30205ddd pool       viewmodel_knife_melee_slice
  m1911dw_zm                           30205ddd pool       viewmodel_knife_melee_slice
  m79_upgraded_zm                      30205ddd pool       viewmodel_knife_melee_slice
  m79_zm                               30205ddd pool       viewmodel_knife_melee_slice
  model1887_upgraded_zm                30205ddd pool       viewmodel_knife_melee_slice
  model1887_zm                         30205ddd pool       viewmodel_knife_melee_slice
  money_ball_zm                        301c4a01 pool       viewmodel_semtex_idle
  mp5k_upgraded_zm                     30205ddd pool       viewmodel_knife_melee_slice
  p90_upgraded_zm                      30205ddd pool       viewmodel_knife_melee_slice
  p90_zm                               30205ddd pool       viewmodel_knife_melee_slice
  pp2000_upgraded_zm                   30205ddd pool       viewmodel_knife_melee_slice
  pp2000_zm                            30205ddd pool       viewmodel_knife_melee_slice
  ranger_upgraded_zm                   30205ddd pool       viewmodel_knife_melee_slice
  ranger_zm                            30205ddd pool       viewmodel_knife_melee_slice
  remote_missile_invasion_so           30205ddd pool       viewmodel_knife_melee_slice
  remote_missile_not_player_invasion_so 30205ddd pool       viewmodel_knife_melee_slice
  revive_knife_zm                      301e4f95 pool       viewmodel_knifethrow_hold_rhand
  scar_h_eotech_zm                     30205ddd pool       viewmodel_knife_melee_slice
  semtex_grenade_zm                    301c4a01 pool       viewmodel_semtex_idle
  sentry_zm                            30205ddd pool       viewmodel_knife_melee_slice
  spas12_upgraded_zm                   30205ddd pool       viewmodel_knife_melee_slice
  spas12_zm                            30205ddd pool       viewmodel_knife_melee_slice
  throwingknife_zm                     301e4f95 pool       viewmodel_knifethrow_hold_rhand
  tmp_upgraded_zm                      30205ddd pool       viewmodel_knife_melee_slice
  ump45_upgraded_zm                    30205ddd pool       viewmodel_knife_melee_slice
  ump45_zm                             30205ddd pool       viewmodel_knife_melee_slice
  zombie_melee                         30a0526d pool       viewmodel_zombie_fire
```

## 6. Patch-zone overrides

```
patch_common_gametype_zm overrides (18 weapon defs):
  WEAPON_MP5                         base slot7=pool       patch slot7=pool       
  as50_upgraded_zm                   base slot7=n/a        patch slot7=pool       CHANGED
  as50_zm                            base slot7=n/a        patch slot7=pool       CHANGED
  aug_eotech_upgraded_zm             base slot7=EMPTY      patch slot7=pool       CHANGED
  aug_eotech_zm                      base slot7=EMPTY      patch slot7=pool       CHANGED
  crossbow_explosive_upgraded_zm     base slot7=EMPTY      patch slot7=EMPTY      
  crossbow_explosive_zm              base slot7=EMPTY      patch slot7=EMPTY      
  m1911dw_zm                         base slot7=pool       patch slot7=inline     CHANGED
  model1887_upgraded_zm              base slot7=pool       patch slot7=pool       
  model1887_zm                       base slot7=pool       patch slot7=pool       
  mp5k_upgraded_zm                   base slot7=pool       patch slot7=pool       
  p90_upgraded_zm                    base slot7=pool       patch slot7=pool       
  p90_zm                             base slot7=pool       patch slot7=pool       
  sentry_minigun_mp                  base slot7=EMPTY      patch slot7=EMPTY      
  sentry_minigun_pro_mp              base slot7=EMPTY      patch slot7=EMPTY      
  spas12_upgraded_zm                 base slot7=pool       patch slot7=pool       
  spas12_zm                          base slot7=pool       patch slot7=pool       
  ump45_zm                           base slot7=pool       patch slot7=pool       

patch_common_gametype_mp overrides (43 weapon defs):
  aa12_mp                            base slot7=pool       patch slot7=inline     CHANGED
  acr_mp                             base slot7=pool       patch slot7=pool       
  ak104_mp                           base slot7=pool       patch slot7=pool       
  ak47_mp                            base slot7=pool       patch slot7=pool       
  as50_mp                            base slot7=pool       patch slot7=pool       
  at4_mp                             base slot7=pool       patch slot7=pool       
  beretta_mp                         base slot7=pool       patch slot7=pool       
  briefcase_bomb_defuse_mp           base slot7=pool       patch slot7=pool       
  briefcase_bomb_mp                  base slot7=pool       patch slot7=pool       
  cartevent_mp                       base slot7=n/a        patch slot7=pool       CHANGED
  cheytac_mp                         base slot7=pool       patch slot7=pool       
  famas_mp                           base slot7=pool       patch slot7=pool       
  fn2000_mp                          base slot7=pool       patch slot7=pool       
  frag_grenade_short_mp              base slot7=pool       patch slot7=unresolved CHANGED
  g18_mp                             base slot7=pool       patch slot7=pool       
  javelin_mp                         base slot7=pool       patch slot7=pool       
  m1014_mp                           base slot7=pool       patch slot7=pool       
  m14ebr_mp                          base slot7=pool       patch slot7=pool       
  m16_mp                             base slot7=pool       patch slot7=pool       
  m21ebr_mp                          base slot7=pool       patch slot7=pool       
  m4_mp                              base slot7=pool       patch slot7=pool       
  m4a1tech_mp                        base slot7=pool       patch slot7=pool       
  m4a1techevent_mp                   base slot7=n/a        patch slot7=pool       CHANGED
  mcsevent_mp                        base slot7=n/a        patch slot7=pool       CHANGED
  miniuzi_mp                         base slot7=pool       patch slot7=pool       
  mp5k_mp                            base slot7=pool       patch slot7=pool       
  mp5sd_mp                           base slot7=n/a        patch slot7=pool       CHANGED
  p90_mp                             base slot7=pool       patch slot7=pool       
  pp2000_mp                          base slot7=pool       patch slot7=pool       
  rpg_mp                             base slot7=pool       patch slot7=pool       
  scar_mp                            base slot7=pool       patch slot7=pool       
  semtex_mp                          base slot7=pool       patch slot7=unresolved CHANGED
  sentry_minigun_mp                  base slot7=EMPTY      patch slot7=EMPTY      
  sentry_minigun_pro_mp              base slot7=EMPTY      patch slot7=EMPTY      
  stinger_mp                         base slot7=pool       patch slot7=pool       
  tar21_mp                           base slot7=pool       patch slot7=pool       
  tmp_mp                             base slot7=pool       patch slot7=pool       
  tow_turret_mp                      base slot7=EMPTY      patch slot7=EMPTY      
  type95_mp                          base slot7=pool       patch slot7=pool       
  ump45_mp                           base slot7=pool       patch slot7=pool       
  vector_mp                          base slot7=pool       patch slot7=pool       
  wa2000_mp                          base slot7=pool       patch slot7=pool       
  ÿÿÿÿ                               base slot7=n/a        patch slot7=EMPTY      CHANGED

```

## 7. `def+0xbf0` -- the per-weapon "owns its melee anims" flag

C1 tests this byte at `0x47c0e5` (the anim-name override), `0x41bd7e`
(`PM_Weapon_Melee` timings), `0x47ae18` (anim rate) and `0x4dfdfc`
(melee damage).  Zero means the `mp/coKnifeStatsTable.csv` row wins;
non-zero means the weapon keeps its own melee data.  Census:

* `common_gametype_zm`: {0: 149, 1: 4}
* `common_gametype_mp`: {0: 177, 1: 1}
* `patch_common_gametype_zm`: {0: 18}
* `patch_common_gametype_mp`: {0: 43}

```
common_gametype_zm -- definitions with def+0xbf0 != 0:
    knife_ballistic_bowie_upgraded_zm
    knife_ballistic_bowie_zm
    knife_ballistic_upgraded_zm
    knife_ballistic_zm

common_gametype_mp -- definitions with def+0xbf0 != 0:
    riotshield_mp

```

Slot-7 state cross-referenced with `def+0xbf0`:

```
common_gametype_zm         {('EMPTY', 0): 109, ('pool', 0): 40, ('pool', 1): 4}
common_gametype_mp         {('pool', 0): 141, ('pool', 1): 1, ('unresolved', 0): 4, ('EMPTY', 0): 32}
```

## 8. `mp/coKnifeStatsTable.csv` (from `code_post_gfx_mp`)

This is the override source C1 uses at `0x47c090`: for anim index 7 it reads
`row+0x3c` (CSV column 21) and for index 8 `row+0x40` (CSV column 22), and it
overrides the slot only when that pointer is non-NULL *and* the string is
non-empty.  The table is a client-global stringtable in `code_post_gfx_mp`, not
an `_mp` weapon or weaponattach asset, and it is the only copy in the game
(`docs/zone_assets/ALL_stringtable.txt` lists it in that zone alone).

MEASURED, 24 columns x 21 rows.  Column 21 by row, column 22 for completeness:

```
  row  name                 col 21 (melee anim)             col 22 (charge anim)
    0  mel_prison           viewmodel_knife_melee_slice     (empty)
    1  (unnamed)            (empty)                         (empty)
    2  mel_sog              (empty)                         (empty)
    3  mel_karambit         (empty)                         (empty)
    4  mel_bowie            (empty)                         (empty)
    5  mel_hatchet          (empty)                         (empty)
    6  mel_shovel           player_blunt_melee_attack       (empty)
    7  mel_cleaver          player_blade_melee_attack       (empty)
    8  mel_bonesaw          (empty)                         (empty)
    9  mel_axe              player_chopping_melee_attack    (empty)
   10  mel_hammer           (empty)                         (empty)
   11  mel_hook             (empty)                         (empty)
   12  (unnamed)            (empty)                         (empty)
   13  zknife_bowie         (empty)                         (empty)
   14  (unnamed)            (empty)                         (empty)
   15  zknife_halberd       player_lubu_polearm_attack      (empty)
   16  coop_mel_knife       (empty)                         (empty)
   17  coop_mel_karambit    (empty)                         (empty)
   18  coop_mel_bonesaw     (empty)                         (empty)
   19  coop_mel_sog         (empty)                         (empty)
   20  coop_mel_bowie       (empty)                         (empty)
```

Reproduce with:

    python tools/codol_weapondef_zone_diff.py table mp/coKnifeStatsTable.csv code_post_gfx_mp

Three consequences fall straight out of that table:

* **Column 22 is empty in every row**, so anim index 8 (melee charge) is never
  overridden from the table.  Slot 8 always comes from the weapon definition.
* **Exactly one row supplies a viewmodel melee animation**: row 0,
  `mel_prison`, with `viewmodel_knife_melee_slice` -- byte-for-byte the same
  string the 38 populated zm definitions and the 133 populated mp definitions
  already point at in slot 7.  The other four non-empty column-21 values are
  `player_*` third-person attack animations, not viewmodels.
* That string is a real xanim asset of `common_gametype_zm`
  (`docs/zone_assets/ALL_xanim.txt`), so selecting that row needs **no `_mp`
  asset of any kind** -- only the playerstate field.

## 9. Definitions whose INTERNAL NAME is itself a de-duplicated reference

34 of the 174 type-28 assets in `common_gametype_zm` (10 of 187 in
`common_gametype_mp`) carry a de-duplicated name pointer, so the string at
`+0xBFC` is *not* the internal name -- it is whichever head string happened
to be the first inline one.  That is why rows like `WEAPON_M1911` and
`WEAPON_MP5` appear in section 5.  `docs/zone_assets/ALL_weapon.txt` lists
the names the zone must contain, and each of these occurs exactly once in
the zone bytes.  A single residual, `r = 319489`, places 8 of them at once; an
eight-way coincidence is not plausible, so the assignment is settled:

```
  asset 3522  ray_gun_zm       (+0xBFC reads ZOMBIE_RAY_GUN      )  slot7 3007f4b7 EMPTY                                slot8 3007f4b7 EMPTY  
  asset 3617  tesla_gun_zm     (+0xBFC reads ZOMBIE_TESLA_GUN    )  slot7 3007f4b7 EMPTY                                slot8 3007f4b7 EMPTY  
  asset 2702  m1911_zm         (+0xBFC reads WEAPON_M1911        )  slot7 30205ddd pool   viewmodel_knife_melee_slice   slot8 3020757a pool   viewmodel_knife_melee_stab
  asset 2882  m16_zm           (+0xBFC reads WEAPON_M16          )  slot7 3007f4b7 EMPTY                                slot8 3007f4b7 EMPTY  
  asset 2998  mp5k_zm          (+0xBFC reads WEAPON_MP5          )  slot7 30205ddd pool   viewmodel_knife_melee_slice   slot8 3020757a pool   viewmodel_knife_melee_stab
  asset 3014  uzi_zm           (+0xBFC reads WEAPON_UZI          )  slot7 3007f4b7 EMPTY                                slot8 3007f4b7 EMPTY  
  asset 3410  wa2000_zm        (+0xBFC reads WEAPON_WA2000       )  slot7 3007f4b7 EMPTY                                slot8 3007f4b7 EMPTY  
  asset 4228  minigun_zm       (+0xBFC reads ZOMBIE_MINIGUN      )  slot7 3007f4b7 EMPTY                                slot8 3007f4b7 EMPTY  
```

`m1911_zm` -- the zm starting pistol -- and `mp5k_zm` DO carry the pooled
melee pair.  `ray_gun_zm`, `tesla_gun_zm`, `uzi_zm`, `wa2000_zm`, `m16_zm`
and `minigun_zm` do not.

## 10. Reconciliation with the live loader

The running server logged, for the 54 zm definitions it touched, 39 with an
empty slot 7 and 15 populated.  Re-deriving that split purely from the zone
bytes (base definition, patch zone where it overrides) reproduces it with
**zero disagreements**: 45 of the 54 are named inline and all 45 match; the
other 9 (`m16_zm`, `m1911_zm`, `mp5k_zm`, `ray_gun_zm`, `tesla_gun_zm`,
`uzi_zm`, `wa2000_zm`, `m16_gl_upgraded_zm`, `scar_h_eotech_mk_upgraded_zm`)
are the de-duplicated-name cases of section 9 and match once named.

That agreement is also what confirms `3007f4b7` is the empty string rather
than an unresolvable reference: the live loader reported those exact
definitions as *empty*, not as *missing*.

One patch-zone subtlety (see section 6): `patch_common_gametype_zm` flips
`aug_eotech_zm` and `aug_eotech_upgraded_zm` from EMPTY in the base zone to
the pooled melee pair, and it adds `as50_zm` / `as50_upgraded_zm`, which the
base zone does not define at all.  Every other patch definition keeps the
slot-7 state its base definition had.  A census that reads only the base
zone mis-reports those two.

## 11. The pooled melee name pairs in `common_gametype_zm`

```
  30205ddd  used by  46 anim slots   viewmodel_knife_melee_slice
  3020757a  used by  50 anim slots   viewmodel_knife_melee_stab
  30f6d78a  used by   4 anim slots   viewmodel_b_knife_zm_melee_swipe
  30f6e913  used by   4 anim slots   viewmodel_b_knife_zm_melee_stick
  301e4f95  used by  16 anim slots   viewmodel_knifethrow_hold_rhand
  301e58f5  used by   4 anim slots   viewmodel_knifethrow_throw_rhand
```

`30205ddd`/`3020757a` are the generic pair every populated gun points at,
and the identification is independent of the residual fit: the two strings
are a measured 6045 block-3 bytes apart, and `viewmodel_knife_melee_slice`
/ `viewmodel_knife_melee_stab` is the ONLY melee-named pair in the whole
zone at that spacing (6043 in the file; the 2-byte difference is residual
drift).  The identical search in `common_gametype_mp` returns the same two
strings for `300f55bc`/`300f6d5a`.

Both xanims are real assets of `common_gametype_zm` (see
`docs/zone_assets/ALL_xanim.txt`), so nothing about them is mp-only.
