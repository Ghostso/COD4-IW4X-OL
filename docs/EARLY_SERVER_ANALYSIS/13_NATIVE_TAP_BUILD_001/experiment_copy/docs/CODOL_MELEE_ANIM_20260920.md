# No knife animation for the .44 Magnum and the M14 EBR (zm), 2026-09-20

Reported live on `zm_prototype_sh`: meleeing with the ".44 magnum" or the
"M14 EBR" plays no animation. Other weapons appeared fine, so the report was
framed as a two-weapon differential.

**Verdict: (b) — the weapon definition names no melee xanim at all. The slot
holds the pooled empty string.** It is shipped CoDOL zm data, it is not a
server defect, and it affects 22 of the 40 weapons our zm roster hands out,
not two. The user's framing is *real but under-counted*: the weapon they melee
with for the first several rounds, the starting `m1911_zm`, is one of the 18
that do have the animation, so their baseline works and the two they named
stood out.

Everything below is MEASURED from the shipped fastfiles and `C1.exe` unless
labelled INFERRED.

---

## 1. The two weapons' real internal names

MEASURED, from the shipped zm weapon assets and from our own roster script
`bin/home/codol_rawfiles/zm/maps/mp/gametypes/_zombiemode_weapons.gsc`:

| display | internal (base) | internal (Pack-a-Punch) | defining zone |
|---|---|---|---|
| ".44 Magnum" / "Anaconda" | `coltanaconda_zm` | `coltanaconda_upgraded_zm` | `common_gametype_zm` |
| "M14 EBR" | `m14ebr_zm` | `m14ebr_upgraded_zm` | `common_gametype_zm` |

`_zombiemode_weapons.gsc:116` registers `coltanaconda_zm` with the display
string `"Anaconda"`, and `:134` registers `m14ebr_zm` as `"M14 EBR"`. There is
no `magnum*_zm` asset at all — `magnumncm_mp` is MP-only — so "the .44 magnum"
in a zm match can only be the Colt Anaconda. Neither weapon is overridden by
`patch_common_gametype_zm` or by the map zone, so the base definition is the
one that reaches the client.

## 2. Where the melee animation actually lives (re-measured)

The serialized type-28 blob **is** the runtime `WeaponDef` (`blob[0:0xBFC]`,
internal name at `+0xBFC`). The 144 animation-name slots start at `+0x7c`, so
slot *n* is at `def + 0x7c + 4n`.

`src/codol/weapon/codol_weapon_native.c:702` maps source slot 7 to
`szXAnims[7]` (melee) and slot 8 to `szXAnims[8]` (melee charge), citing C1
`0x47b9dd` / `0x47b9f0`. That citation is *weak on its own* — those two sites
`push 7` / `push 8` into `0x47ad10`, and `0x47ad10` uses its argument to index
a table at **`0xcd6640`** whose entries are `{primary, fallback}` byte offsets
into the def. Those offsets are `0x5b8`..`0x648` — the **duration** fields, not
the name array. animID 7 resolves to `def+0x5c0` (`iMeleeTime`) and animID 8 to
`def+0x5c4` (`meleeChargeTime`), which is what
`CODOL_ApplyNativeWeaponMelee` (`codol_weapon_native.c:557-558`) already
records. So `0x47b9dd`/`0x47b9f0` prove animID 7/8 = melee/melee-charge, but
they do **not** prove the name-slot index.

The name-slot index is proven independently, by the shipped `weaponattach`
(type-43) override records, which write a def offset and carry a
self-describing anim name. MEASURED in `common_gametype_mp`:

| attachment | record | name written |
|---|---|---|
| `tactical_de` | `+0x098` (slot 7) | `viewmodel_deserteagle_tactical_melee` |
| `tactical_beretta` | `+0x098` (slot 7) | `viewmodel_beretta_tactical_melee` |
| `tactical_magnum` | `+0x098` (slot 7) | `viewmodel_coltanaconda_tactical_melee` |
| `gl_acr`, `gl_m4a1tech` | `+0x098` / `+0x09c` | the pooled generic pair `0x300f55bc` / `0x300f6d5a` |

Three independent attachments write a string literally named `*_melee` to
`+0x098`. **Slot 7 = the melee viewmodel xanim. Slot 8 = melee charge.**

The same attachment dumps confirm the rest of our table in
`CODOL_ApplyNativeWeaponAnimationNames` — slot 1 idle, 3 fire, 5 last-fire,
9 reload, 11 reload_empty, 15 pullout, 16 first_time_pullout, 17 breach,
18 putaway, 21/22 quick pullout/putaway, 23/24 pullout/putaway empty,
25/26/27 sprint in/loop/out, 34/35 ADS fire / ADS last-fire. That table is
correct as written; no change needed.

> Note for whoever reads the attachment dumps next:
> `tools/codol_weapondef_zone_diff.py attach` **mis-pairs offsets with
> strings.** Its `read_attachment()` consumes an inline string for every record
> whose type is `<16` and whose value is non-zero. C1 (and our
> `CODOL_LoadMountedWeaponAttachment`, `codol_asset_registry.c:1017`) only
> consumes one when the value is the inline marker `0xFFFFFFFF`; a
> de-duplicated block-3 reference consumes nothing. The Python tool therefore
> walks off by one record per dedup'd value and prints, for example,
> `tactical_magnum +0x098 -> viewmodel_coltanaconda_tactical_sprint_out`.
> The correct value is `viewmodel_coltanaconda_tactical_melee`.

## 3. What the two weapons actually hold in slot 7

MEASURED. In `common_gametype_zm` the pooled empty string is the ref
`0x3007f4b7`; it occupies 118-119 of the 144 slots in *every* weapon in the
zone, which is what identifies it (no real animation name is used in 119 roles
of one weapon).

```
coltanaconda_zm            slot7 = 0x3007f4b7 (empty)   slot8 = 0x3007f4b7 (empty)
m14ebr_zm                  slot7 = 0x3007f4b7 (empty)   slot8 = 0x3007f4b7 (empty)
coltanaconda_upgraded_zm   slot7 = 0x3007f4b7 (empty)   slot8 = 0x3007f4b7 (empty)
m14ebr_upgraded_zm         slot7 = 0x3007f4b7 (empty)   slot8 = 0x3007f4b7 (empty)

m1911_zm / mp5k_zm / p90_zm / ump45_zm / spas12_zm / model1887_zm /
ranger_zm / pp2000_zm / glockdw_zm / scar_h_eotech_zm / tmp_upgraded_zm
                           slot7 = 0x30205ddd           slot8 = 0x3020757a
```

C1 offers no substitute. The name getter at `0x45c500` returns
`def[0x7c + 4*index]` raw, with only a null-container guard; there is no
fallback to `defaultweapon`, to a knife weapon, or to a sibling slot. An empty
name means nothing is played.

## 4. Ruling out (a), (c) and (d)

**(a) — names an xanim that does not ship.** Impossible silently.
`CODOL_LoadEngineWeaponCore` (`src/codol/weapon/codol_weapon_loader.c:144`)
resolves *every* non-empty name of the 144 through
`CODOL_LoadEngineNativeXAnim` and `core_fail()`s the whole weapon if one does
not resolve. An unshipped melee xanim would refuse the weapon at boot, exactly
as `m1911_zm`'s muzzle flash did before d6b75caa. It would not degrade to a
missing animation. Separately, the generic melee xanims **do** ship in a zm
match — `viewmodel_knife_melee_slice` and `viewmodel_knife_melee_stab` are
present in both `common_gametype_zm` (assets 186/187) and
`patch_common_gametype_zm`. The content is mounted; only the definitions fail
to name it.

**(c) — resolves but nothing selects it.** There is nothing to resolve: the
slot is empty. And the server-side melee path is demonstrably identical for
these weapons — the five fields C1's melee reads are byte-identical between
the two reported weapons and the comparison weapons:

```
                  +0x590 dmg  +0x5a0 delay  +0x5a4 chgDelay  +0x5c0 time  +0x5c4 chgTime
coltanaconda_zm      25          250            0              699           0
m14ebr_zm            25          250            0              699           0
famas_zm             25          250            0              699           0
glock_zm             25          250            0              699           0
ak104_zm             25          250            0              699           0
```

The full 144-slot presence vector is likewise identical between
`coltanaconda_zm`, `m14ebr_zm`, `famas_zm`, `glock_zm`, `ak104_zm`,
`tavor_zm` and `fal_zm`. **There is no two-weapon differential anywhere in the
weapon data**, which is the finding that redirects the whole investigation.

**(d) — a different melee path (knife-weapon swap, T5 style).** Considered and
rejected. If zm melee ran through a separate knife weapon, *no* zm weapon would
need slot 7 — yet 18 of the 40 roster weapons carry the pooled generic melee
pair, including the starting `m1911_zm`. The split is inconsistent in a way
design would not produce: `p90_zm` has it and `famas_zm` does not; `spas12_zm`
has it and `striker_zm` does not. That is an incomplete data port, not a
second code path.

## 5. Are other weapons genuinely unaffected? No.

MEASURED against our roster in `_zombiemode_weapons.gsc`, effective definition
after patch/map override:

**No melee animation (22):** Anaconda `coltanaconda_zm`, Glock `glock_zm`,
Uzi `uzi_zm`, TMP `tmp_zm`, Striker `striker_zm`, **M14 EBR `m14ebr_zm`**,
M16 `m16_zm`, FAMAS `famas_zm`, FAL `fal_zm`, AK-104 `ak104_zm`,
Tavor `tavor_zm`, M4A1 `m4a1tech_zm`, CheyTac `cheytac_zm`, WA2000 `wa2000_zm`,
Explosive Sniper `sniper_explosive_zm`, L86 LSW `l86_zm`,
Explosive Crossbow `crossbow_explosive_zm`, Ray Gun `ray_gun_zm`,
Wunderwaffe `tesla_gun_zm`, Thundergun `thundergun_zm`,
Frag Grenade `frag_grenade_zm`, Claymore `claymore_zm`.

**Has melee animation (18):** M1911 `m1911_zm`, Dual Glock `glockdw_zm`,
MP5K `mp5k_zm`, P90 `p90_zm`, PP2000 `pp2000_zm`, SPAS-12 `spas12_zm`,
Model 1887 `model1887_zm`, Ranger `ranger_zm`, AUG `aug_eotech_zm`,
SCAR-H `scar_h_eotech_zm`, AS50 `as50_zm`, M79 `m79_zm`, AT4 `at4_zm`,
Ballistic Knife `knife_ballistic_zm`, Bowie Ballistic Knife
`knife_ballistic_bowie_zm`, Semtex `semtex_grenade_zm`,
Bouncing Betty `bouncingbetty_zm`, C4 `c4_zm`.

Upgraded variants follow their base in every case.

**Falsifiable prediction, cheap to check live:** melee with the FAMAS, the
FAL, the AK-104, the Tavor or the M4A1 and no animation will play either;
melee with the P90, the SPAS-12 or the Ranger and it will. If that does not
hold, this diagnosis is wrong.

Contrast with MP, which is where the defect shows as a zm-specific data gap:
in `common_gametype_mp`, 146 of 178 definitions carry slot 7, and the 32 that
do not are all non-held assets — killstreaks, projectiles, turrets, dogs,
`tabun_*` gas volumes, barrels. Every held MP weapon has a melee animation.

## 6. Why the server cannot fix this, and what would

Weapons reach the client as **names only**. `codol_sv_weapons.c:411-413`
publishes the zm window as `CS 5363..5492` plus the count at `CS 6517`; the
client then builds `bg_weaponDefs[i]` from *its own* zone copy of that named
type-28 asset. Slot 7 of that copy is the empty string. Nothing the server
sends in the playerstate (`weapAnim` at `ps+0x268`, `weaponstate` at
`ps+0x278`, `weaponTime` at `ps+0x26c`) can supply a name.

The one override channel C1 has is `BG_BuildCustomWeaponDef` (`0x4216C4`),
which memcpy's the 0xBFC base def for a composed `*a <base> ...` name and then
applies type-43 `weaponattach` records — records that *can* write `+0x098` and
`+0x09c`, as §2 shows. That channel is unavailable here: MEASURED, **every zone
a zm match mounts contains zero weaponattach assets** —

```
common_mp                  weaponattach=0
patch_common_mp            weaponattach=0
common_gametype_zm         weaponattach=0
patch_common_gametype_zm   weaponattach=0
zm_prototype_sh            weaponattach=0
patch_zm_prototype_sh      weaponattach=0
```

So there is no composed name we could publish that would make C1 write a melee
animation name into the custom def.

**The fix is data, and it is small.** Whoever can emit a patch zm zone needs,
per affected weapon, two override records — or two edited name slots:

```
def + 0x098  (slot 7) <- "viewmodel_knife_melee_slice"
def + 0x09c  (slot 8) <- "viewmodel_knife_melee_stab"
```

Both xanims are **already mounted** in `common_gametype_zm` and
`patch_common_gametype_zm`, so this adds no content and changes no fastfile
dependency set. It is also exactly what the 18 working zm weapons and the 132
pooled MP weapons already point at. Delivering it as a `patch_common_gametype_zm`
weaponattach asset would additionally re-open the composed-name channel for
`src/codol/weapon/**` to use.

Until that exists, the server change in this pass is diagnostic only: the
weapon loader now names, once at load, every weapon that C1 will let melee
(`iMeleeDamage != 0`) but whose melee animation slot is empty. This is the same
treatment d6b75caa gave the unresolvable muzzle flash — a silent gap that cost
a boot cycle to interpret becomes a line that names the weapon.

## 7. Conflicts recorded

* **`tools/codol_weapondef_zone_diff.py` vs C1 / our C loader** — the Python
  attachment parser's string pairing is wrong (§2). C1 and
  `CODOL_LoadMountedWeaponAttachment` win. The tool is not corrected here
  because it is outside `src/codol/weapon/**`; the exact defect and the
  one-line rule (`consume only when value == 0xFFFFFFFF`) are recorded above.
* **Comment in `codol_weapon_native.c:702` vs what `0x47b9dd` proves** — the
  cited addresses establish the animation *ID*, not the *name slot*. The
  mapping it asserts is nonetheless correct; §2 supplies the evidence that
  actually proves it. Left as a note rather than a rewrite, since the table is
  right.
* **CoDOL shipped data vs "every weapon has a knife melee"** — the standing
  mandate makes shipped CoDOL data the source of truth, and it says 22 zm
  weapons have no melee animation. Recorded as a content gap to be fixed in a
  patch zone, not worked around in the server.
