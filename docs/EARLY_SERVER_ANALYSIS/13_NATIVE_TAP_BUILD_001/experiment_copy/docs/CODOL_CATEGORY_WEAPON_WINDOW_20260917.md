# The coop/zm weapon configstring window, 2026-09-17

Worker deliverable for the `mp -> coop/zm` handoff. Owner scope:
`src/codol/weapon/**`. Every claim is labelled **MEASURED** (read out of shipped
data, source, a capture or a compile) or **INFERRED**.

Nothing was live-verified in this pass: no server, lobby or client was started
or stopped, and no binary was copied into `bin/`.

---

## 0. Verdict first

**The in-code claim at `src/codol/weapon/codol_sv_weapons.c:427-432` — that coop
and zm "publish no MP window and keep the empty value, which skips the loop as
the client's own tables do" — is REFUTED.**

The client's own tables do not skip anything. Each category's constant
configstring table *is* a complete weapon window: it names every weapon in the
`CS_WEAPONS` space and carries its own `CS 6517` count. The coop table names
`beretta_so` at index 2, which is literally the client error the transcripts
recorded. So "the client has its own tables" is true, and that is precisely why
the empty window is wrong: the client is not skipping, it is registering from a
window the server has either contradicted or blanked.

Settled at instruction level in §2.2: C1's `CG_Init` runs
`for (i = 1; i < 700; i++) ValidateWeaponConfigString(i)` over the whole
`CS_WEAPONS` window (`0x00450ADC..0x00450AF1`), unconditionally and
independently of `CS 6517`, in every category.

**And the second verdict, on `181 aa12_mp 0 2` (the parent's question): it is
(b) — our server publishing mp names into a coop match.** Proof in §2.1.

---

## 1. What the three constant tables actually contain

**MEASURED.** Decoded from the inflated startup zone
`%TEMP%\codol_zones\code_post_gfx_mp.zone` — the same fastfile
`docs/zone_assets/ALL_stringtable.txt` places all three tables in, so all three
are resident for every category. Method: walk the type-37 (stringtable) assets,
read the 16-byte header `{name*, columnCount, rowCount, values*}`, then the
`rowCount*columnCount` 8-byte `{string*, hash}` cells. Cells written inline
(`string* == 0xFFFFFFFF`) carry their bytes in the stream; de-duplicated cells
were resolved by matching `hash` against `CODOL_StringTableHash`
(`src/codol/assets/codol_stringtable.c:28`) over every NUL-terminated string in
the zone. That hash lower-cases, so the only ambiguities were case pairs
(`ZOMBIE_CYMBAL_MONKEY` / `zombie_cymbal_monkey`), resolved by neighbour
convention.

Shape: 2 columns, `(configstring index, value)`, sorted by value.

| table | rows | weapon block | weapon slots | `CS 6517` |
|---|---|---|---|---|
| `mp/constconfigstrings_mp.csv` | 2053 | CS 5363..5537 | 152 present, **22 holes** | `176` |
| `mp/constconfigstrings_coop.csv` | 1803 | CS 5363..5425 | 63, **hole-free** | `64` |
| `mp/constconfigstrings_zm.csv` | 1625 | CS 5363..5492 | 130, **hole-free** | `131` |

Row counts corroborate `alpha0022/zone_crc.py:146-148` (2053 / 1803 / 1625).

`CS_WEAPONS` is 5362 (`src/codol/snapshot/codol_configstrings.h:31`), so weapon
index = CS - 5362, and CS 5363 = index 1 = `defaultweapon_mp` in **all three**
tables. Index 0 (`none`) is implicit and appears in none of them.

`CS 6517` (`CODOL_CS_WEAPON_COUNT`, same header line 67) is the last row of every
table:

```
mp    row 2052   6517   176
coop  row 1802   6517   64
zm    row 1624   6517   131
```

The coop and zm numbers are exactly `slots + 1` — both tables are internally
complete: every index `1..count-1` that C1's `CG_Init` loop (`0x47d1d0`,
`1..count-1` over `bg_weaponDefs`) will touch is named. The mp table is **not**:
`176` demands indices 1..175 but only CS 5363..5436, 5439 and 5461..5537 are
present, leaving 22 unnamed indices (CS 5437-5438 and 5440-5460). That is the
"141 names + 33 hole fillers" shape `alpha0022/docs/ERRORS.md:8529-8540`
recorded for mp, and it is why mp cannot simply publish 176.

### 1.1 The coop window, in full (MEASURED)

`CS <configstring>  <weapon index>  <name>`

```
  CS 5363  1    defaultweapon_mp
  CS 5364  2    beretta_so
  CS 5365  3    mp5_silencer_so
  CS 5366  4    cheytac_silencer_so
  CS 5367  5    ump45_so
  CS 5368  6    rpd_so
  CS 5369  7    m16_basic_so
  CS 5370  8    mp5_silencer_reflex_so
  CS 5371  9    rpd_reflex_so
  CS 5372  10   m16_reflex_so
  CS 5373  11   ump45_digital_reflex_so
  CS 5374  12   m16_grenadier_reddot_so
  CS 5375  13   m203_reddot_so
  CS 5376  14   usp_silencer_so
  CS 5377  15   tmp_silencer_so
  CS 5378  16   aa12_so
  CS 5379  17   rpg_so
  CS 5380  18   barrett_so
  CS 5381  19   barrett_zoom_so
  CS 5382  20   usp_silencer_akimbo_so
  CS 5383  21   tmp_silencer_reflex_so
  CS 5384  22   at4_so
  CS 5385  23   hatchet_so
  CS 5386  24   throwingknife_so
  CS 5387  25   semtex_grenade_so
  CS 5388  26   fraggrenade_so
  CS 5389  27   smoke_grenade_american_so
  CS 5390  28   flash_grenade_so
  CS 5391  29   c4_so
  CS 5392  30   claymore_so
  CS 5393  31   destructible_car
  CS 5394  32   mp5k_codo_so
  CS 5395  33   usp_so
  CS 5396  34   m4_grunt_reflex_so
  CS 5397  35   m4techgrip_eotech_so
  CS 5398  36   m4techm203_reflex_so
  CS 5399  37   m203_m4tech_reflex_so
  CS 5400  38   mg4_new_so
  CS 5401  39   cheytac_new_so
  CS 5402  40   mp5k_reflex_so
  CS 5403  41   usp_new_so
  CS 5404  42   fraggrenade_training_so
  CS 5405  43   m79_so
  CS 5406  44   saw_so
  CS 5407  45   spas12_so
  CS 5408  46   spas12_reflex_so
  CS 5409  47   glock_so
  CS 5410  48   m4_grunt_so
  CS 5411  49   m4_grenadier_so
  CS 5412  50   m203_m4_so
  CS 5413  51   usp_silencer
  CS 5414  52   ak47_so
  CS 5415  53   coltanaconda_so
  CS 5416  54   winchester1200_so
  CS 5417  55   m1014_so
  CS 5418  56   mp5_so
  CS 5419  57   mp5_reflex_so
  CS 5420  58   ump45_acog_so
  CS 5421  59   ump45_reflex_so
  CS 5422  60   masada_acog_so
  CS 5423  61   rpg_player_so
  CS 5424  62   minigun_littlebird_spinnup
  CS 5425  63   deserteagle_so
```

Note indices 12/13, 36/37 and 49/50: `m16_grenadier_reddot_so` ->
`m203_reddot_so`, `m4techm203_reflex_so` -> `m203_m4tech_reflex_so`,
`m4_grenadier_so` -> `m203_m4_so`. Those are parent/launcher pairs at adjacent
slots — i.e. the constant table already carries the **partner** definitions the
client's registrar appends on its own. **MEASURED** for those three pairs;
**INFERRED** that the table is generally the client's slot map including partner
insertions.

### 1.2 The zm window, in full (MEASURED)

```
  CS 5363  1    defaultweapon_mp
  CS 5364  2    frag_grenade_zm
  CS 5365  3    semtex_grenade_zm
  CS 5366  4    flash_grenade_zm
  CS 5367  5    throwingknife_zm
  CS 5368  6    hatchet_zm
  CS 5369  7    money_ball_zm
  CS 5370  8    revive_knife_zm
  CS 5371  9    zombie_cymbal_monkey
  CS 5372  10   zombie_nesting_dolls
  CS 5373  11   zombie_black_hole_bomb
  CS 5374  12   claymore_zm
  CS 5375  13   bouncingbetty_zm
  CS 5376  14   proximity_alarm_zm
  CS 5377  15   teleporter_zm
  CS 5378  16   trap_fire_zm
  CS 5379  17   trap_shock_zm
  CS 5380  18   trap_shrink_zm
  CS 5381  19   trap_freeze_zm
  CS 5382  20   care_package_zm
  CS 5383  21   rcbomb_zm
  CS 5384  22   sentry_zm
  CS 5385  23   zombie_starburst_bomb
  CS 5386  24   destructible_car
  CS 5387  25   sentry_minigun_mp
  CS 5388  26   sentry_minigun_pro_mp
  CS 5389  27   minigun_zm
  CS 5390  28   dog_bite_zm
  CS 5391  29   tesla_gun_zm
  CS 5392  30   crossbow_explosive_zm
  CS 5393  31   crossbow_explosive_upgraded_zm
  CS 5394  32   remote_missile_not_player_invasion_so
  CS 5395  33   weapon_blackhawk_minigun
  CS 5396  34   perkpop_deadshot_zm
  CS 5397  35   perkpop_longersprint_zm
  CS 5398  36   perkpop_disguise_zm
  CS 5399  37   perkpop_carpenter_zm
  CS 5400  38   perkpop_discount_zm
  CS 5401  39   perkpop_flakjacket_zm
  CS 5402  40   perkpop_electro_zm
  CS 5403  41   perkpop_additionalprimary_zm
  CS 5404  42   perkpop_scavenger_zm
  CS 5405  43   perkpop_pandora_zm
  CS 5406  44   ray_gun_fire_zm
  CS 5407  45   zombie_melee
  CS 5408  46   m1911_zm
  CS 5409  47   m1911_upgraded_zm
  CS 5410  48   coltanaconda_zm
  CS 5411  49   coltanaconda_upgraded_zm
  CS 5412  50   glock_zm
  CS 5413  51   glock_upgraded_zm
  CS 5414  52   glockdw_zm
  CS 5415  53   glockdw_upgraded_zm
  CS 5416  54   m1911dw_zm
  CS 5417  55   ump45_zm
  CS 5418  56   ump45_upgraded_zm
  CS 5419  57   mp5k_zm
  CS 5420  58   mp5k_upgraded_zm
  CS 5421  59   uzi_zm
  CS 5422  60   uzi_upgraded_zm
  CS 5423  61   pp2000_zm
  CS 5424  62   pp2000_upgraded_zm
  CS 5425  63   tmp_zm
  CS 5426  64   tmp_upgraded_zm
  CS 5427  65   tavor_zm
  CS 5428  66   tavor_upgraded_zm
  CS 5429  67   spas12_zm
  CS 5430  68   spas12_upgraded_zm
  CS 5431  69   striker_zm
  CS 5432  70   striker_upgraded_zm
  CS 5433  71   ranger_zm
  CS 5434  72   ranger_upgraded_zm
  CS 5435  73   model1887_zm
  CS 5436  74   model1887_upgraded_zm
  CS 5437  75   m14ebr_zm
  CS 5438  76   m14ebr_upgraded_zm
  CS 5439  77   m16_zm
  CS 5440  78   m16_gl_upgraded_zm
  CS 5441  79   gl_m16_upgraded_zm
  CS 5442  80   p90_zm
  CS 5443  81   p90_upgraded_zm
  CS 5444  82   famas_zm
  CS 5445  83   famas_upgraded_zm
  CS 5446  84   scar_h_eotech_zm
  CS 5447  85   scar_h_eotech_mk_upgraded_zm
  CS 5448  86   mk_scar_h_upgraded_zm
  CS 5449  87   ak104_zm
  CS 5450  88   ak104_upgraded_zm
  CS 5451  89   m4a1tech_zm
  CS 5452  90   m4a1tech_upgraded_zm
  CS 5453  91   fal_zm
  CS 5454  92   fal_upgraded_zm
  CS 5455  93   wa2000_zm
  CS 5456  94   wa2000_upgraded_zm
  CS 5457  95   cheytac_zm
  CS 5458  96   cheytac_upgraded_zm
  CS 5459  97   aug_eotech_zm
  CS 5460  98   aug_eotech_upgraded_zm
  CS 5461  99   l86_zm
  CS 5462  100  l86_upgraded_zm
  CS 5463  101  stielhandgranate
  CS 5464  102  at4_zm
  CS 5465  103  at4_upgraded_zm
  CS 5466  104  m79_zm
  CS 5467  105  m79_upgraded_zm
  CS 5468  106  ray_gun_zm
  CS 5469  107  ray_gun_upgraded_zm
  CS 5470  108  zombie_quantum_bomb
  CS 5471  109  explosive_bolt_zm
  CS 5472  110  explosive_bolt_upgraded_zm
  CS 5473  111  sniper_explosive_bolt_zm
  CS 5474  112  sniper_explosive_bolt_upgraded_zm
  CS 5475  113  zombie_knuckle_crack
  CS 5476  114  zombie_perk_bottle_doubletap
  CS 5477  115  zombie_perk_bottle_jugg
  CS 5478  116  zombie_perk_bottle_revive
  CS 5479  117  zombie_perk_bottle_sleight
  CS 5480  118  zombie_perk_bottle_marathon
  CS 5481  119  zombie_perk_bottle_nuke
  CS 5482  120  zombie_perk_bottle_deadshot
  CS 5483  121  zombie_perk_bottle_additionalprimaryweapon
  CS 5484  122  zombie_bowie_flourish
  CS 5485  123  zombie_nesting_doll_single
  CS 5486  124  cobra_20mm_mp
  CS 5487  125  kis_bonus_points_team_zm
  CS 5488  126  kis_bonus_points_player_zm
  CS 5489  127  kis_pandora_zm
  CS 5490  128  kis_minigun_zm
  CS 5491  129  kis_fire_sale_zm
  CS 5492  130  kis_all_revive_zm
```

Three zm names collided case-insensitively in the hash resolution and were read
as their lower-case forms: index 9 `zombie_cymbal_monkey`, 11
`zombie_black_hole_bomb`, 23 `zombie_starburst_bomb`. **INFERRED**, but the
neighbours 10 `zombie_nesting_dolls` and 123 `zombie_nesting_doll_single` set
the convention and the alternative spelling is a localized-string id, which is
not a weapon name.

Corroboration for zm: `alpha0022/docs/zombies_mode.md:703-711,725-727` records
the same geometry — "the **zm** table supplies **130** weapon slots
(CS 5363..5492 = indices 1..130) and sets CS[6517] = **131** ... **The zm const
table is internally complete.**" The coop weapon block was never enumerated
there (`alpha0022/docs/gsc_streaming.md:349` has only its row count); the table
in §1.1 is the first enumeration of it.

### 1.3 Weapon-ish stringtables per category

**MEASURED**, `docs/zone_assets/ALL_stringtable.txt`. There is **no** coop or zm
equivalent of `mp/coWeaponAttachmentTable.csv`. The only weapon-named
stringtables in the whole shipped set are mp-prefixed and mp-only in content:

```
mp/constconfigstrings_coop.csv          code_post_gfx_mp
mp/constconfigstrings_mp.csv            code_post_gfx_mp
mp/constconfigstrings_zm.csv            code_post_gfx_mp
mp/coweaponattachmenttable.csv          code_post_gfx_mp, patch_code_post_gfx_mp
mp/coweaponprimaryranktable.csv         code_post_gfx_mp
mp/coweaponsecondaryranktable.csv       code_post_gfx_mp
mp/coweaponuislottable.csv              code_post_gfx_mp, patch_code_post_gfx_mp
```

So for coop and zm the constant configstring table is not merely *a* source for
the window — it is the **only** shipped source. That is the single most
important finding here.

---

## 2. What `181 <name> <a> <b>` is, and what it settles

**MEASURED**, `alpha0022/docs/ERRORS.md:35-45` (recovered
`ValidateWeaponConfigString @0x00483600`):

```c
name = configstring[CS_WEAPONS + weapIdx];
if (!name[0]) return;                        // empty slot -> skipped
got = BG_GetWeaponIndexForName(name);        // 0x41F7A0
if (got == weapIdx) return;
for (i = 0; i <= bg_lastParsedWeaponIndex; i++) Com_Printf(" * %d %s\n", ...);
Com_Error(ERR_DROP, "181 %s %d %d", name, got, weapIdx);
```

The two integers are two **indices for the same weapon** — "where I found it"
and "where you said it is". Not a count, not an overflow. Two distinct shapes:

* **`181 <name> 0 N`** — `got == 0`, the name did not resolve at all. This is
  both `181 beretta_so 0 2` and `181 aa12_mp 0 2`.
* **`181 <spec> N+1 N`** — the **partner** shape
  (`alpha0022/alt_weapons.py:3-38`, `ERRORS.md:65-68`):
  `BG_RegisterWeaponDef @0x0041F640` resolves `def+0xB78` (altWeaponName) and
  `def+0xB88` immediately after appending a definition, so the client inserts a
  launcher/masterkey partner at index N on its own and everything after shifts
  by exactly +1. `register_stock()` (`codol_sv_weapons.c:196-224`) already
  mirrors that (`partners[] = {0xb78, 0xb88}`), which is why the "extra" slot
  must never be stripped. The 17:30 record `181 cheytac_mp 11 10` in
  `docs/CODOL_FS_GAME_EVIDENCE_20260917.md` §7.3 is that shape, on the **mp**
  table — a separate, mp-side off-by-one.

### 2.1 `181 aa12_mp 0 2` — provenance, settled

The parent asked whether `aa12_mp` in a coop context comes from (a) the coop
constant table as shipped, (b) our server publishing mp names into a coop match,
or (c) the client composing a partner/attachment name. **It is (b).** MEASURED,
three independent ways:

1. **(a) is refuted.** The coop constant table's weapon window (CS 5363..5425)
   contains exactly **one** `_mp`-suffixed name — `defaultweapon_mp` at index 1,
   which is shared by all three categories. `aa12_mp` appears **nowhere** in the
   coop constant table's weapon block; the coop analogue is `aa12_so` at
   CS 5378 (index 16). Coop index 2 is `beretta_so` (see §1.1).
2. **`aa12_mp` is exactly mp index 2.** MEASURED: `constconfigstrings_mp.csv`
   CS 5364 = `aa12_mp`, and it is verbatim the first entry the Python reference
   server publishes — `alpha0022/weapon_configstrings.py:229-230`:
   ```python
   WEAPONS_MP = [
       (5364, "aa12_mp"),           # weapon 2
   ```
   Same configstring index, same name. The mp window was published into a
   session whose client was in the coop namespace with `common_gametype_coop`
   mounted, where no `aa12_mp` weapon asset exists — hence `got == 0`.
3. **(c) is refuted** on two counts: the trailing `0 2` is the *not-found*
   shape, not the `N+1 N` partner shape; and `aa12_mp` is a plain stock name,
   not a `*`-prefixed composed spec, so no `BG_BuildCustomWeaponDef` /
   partner-registration path is involved.

**The two coop failure families are the same root defect seen from both sides,
and both are in this subsystem's scope:**

| record | what the client had at slot 2 | why it failed |
|---|---|---|
| `181 beretta_so 0 2` (17:01, 17:04, 17:05, 17:18) | its own coop **constant**, because the server published nothing there | the server never registered or published a coop window |
| `181 aa12_mp 0 2` (17:51) | the server's **mp** window | the server published the wrong category's window |

Both say the same thing: *the server's published weapon window was not the
category's window.*

Why the coop transcript also disposes of the "client skips the loop" claim: for
`181 beretta_so 0 2` to fire at all, the client's configstring 5364 must have
held `beretta_so` and `bg_weaponDefs` must have held only the two entries the
server published (the ` * 0 none / * 1 defaultweapon_mp` dump). That name came
from the constant table, because no server published it — the client validated
its own constant. **MEASURED**, `alpha0022/map_handoff.py:93-95` (2026-08-19)
and `docs/CODOL_FS_GAME_EVIDENCE_20260917.md` §7.3.

Note also that `CS 6517` does not gate this at all:
`ValidateWeaponConfigString` early-outs on an **empty name**, not on a count.
Publishing `CS 6517 = ""` only skips the `CG_Init` registration loop; it does
not stop configstring validation. **INFERRED** from the pseudocode above, and
consistent with every `181` record listed here.

### 2.2 Disassembly: the validator runs over ALL 699 slots, unconditionally

Everything in §2.1 was settled from data. This subsection settles the *mechanism*
from the binary, and it is stronger evidence than any transcript.

**MEASURED**, `C1.exe` (ImageBase 0x400000), `ValidateWeaponConfigString`
@ `0x00483600` — the recovered pseudocode is confirmed instruction for
instruction, including the format strings `0xC45FF4 = " * %d %s\n"` and
`0xC46000 = "181 %s %d %d"`, and `CS_WEAPONS` is confirmed a third way by
`0x00483609  mov ebx, [esi*4 + 0x6D124F8]` with
`(0x6D124F8 - 0x6D0D130)/4 == 5362`. One correction: `BG_GetWeaponIndexForName`
@ `0x0041F7A0` takes **two** arguments (`name`, `registerCallback`) and the
validator passes NULL for the callback.

**It has exactly two callers** (whole-binary E8/E9 rel32 scan, `.tvm0` included):

1. **The unconditional sweep**, inside CG_Init / CG_RegisterGraphics
   @ `0x00450640`:

   ```
   00450ADC  mov  edi, 1                 ; i = 1
   00450AE1  push edi
   00450AE2  call 0x483600               ; ValidateWeaponConfigString(i)
   00450AE7  inc  edi
   00450AEB  cmp  edi, 0x2BC             ; 700
   00450AF1  jb   0x450AE1
   ```

   **`for (i = 1; i < 700; i++)` — a hard-coded constant, straight-line, not
   derived from `CS 6517` and not conditional on anything.** 700 matches the
   `bg_weaponDefs` array exactly (`0x41F571: memset(0x150D720, 0, 0xAF0)` =
   700 dwords).

2. **The per-update path**, `CG_ConfigStringModified` @ `0x00467350`, gated by
   `(unsigned)(index - 5363) <= 0x2BA` — i.e. exactly CS 5363..6061 — which
   validates only the one slot the server just sent. (The same dispatcher sends
   index 6517 to `jmp 0x47D1D0`, re-running the CG_Init weapon loop.)

So the answer is **both**: every weapon-window configstring is validated on
arrival, *and* all 699 slots are re-validated at CG_Init **regardless of
`CS 6517`**. There is no "only up to the count" path for the validator. That
disposes of the "coop/zm skip the loop" claim at the instruction level: the
sweep runs in every category and reads whatever is in the pool.

Blank slots are safe from the sweep — `0x0048361A  je 0x483677` early-outs on an
empty name — but only as a *tail*. Registration is strictly append-at-`++last`
(`0x0041F648  mov [esi*4 + 0x150D720], eax` after `inc esi` /
`mov [0x6C3D28C], esi`), so **a blank in the middle of the window shifts every
later slot by one** and the sweep then trips `181 <name> <last+1> <slotIdx>` —
the partner shape, now confirmed at instruction level. A contiguous prefix
followed by an all-blank tail is therefore the only correct shape, which is what
§3 implements.

**Reported but treated as UNVERIFIED**: the same pass read
`0x0041F7B8..0x0041F7BD` as "`name == "defaultweapon_mp"` -> return 0". Taken at
face value that would make the sweep's very first iteration raise
`181 defaultweapon_mp 0 1` in every category, since CS 5363 is
`defaultweapon_mp` in all three constant tables and the server publishes it too.
Every working mp match contradicts that, so the branch polarity or the return
value is misread. Recorded here only so nobody rediscovers it and acts on it.

### 2.3 Does an empty server value actually clear a constant?

This matters because §3 blanks the tail. **MEASURED** for the *reliable command*
path, `CL_SetConfigstring` @ `0x00487440`, read in full: there is **no
`if (!value[0]) return;` anywhere in it**. The only gate is
`strcmp(old, new) != 0`. On a difference it memcpys the gameState aside,
`memset(stringOffsets, 0, 0x65DC)`, sets `dataCount = 1` (so `stringData[0]` is
`'\0'`) and rebuilds; an empty value simply is not appended, leaving
`stringOffsets[N] == 0`, which points at that `'\0'`.

**So `d <idx> ""` genuinely stores an empty string and the constant is gone.**
No reader in `.text` has a constant-table fallback
(`0x4673A3`, `0x47D1D6`, `0x483609`, `0x44EE40`, ...); they all read the pool
directly. The layout is confirmed alongside it: `stringOffsets[]` @ `0x06D0D130`,
`stringData[]` @ `0x06D1370C`, `MAX_CONFIGSTRINGS = 0x1977 = 6519` (matching
`CODOL_MAX_CONFIGSTRINGS`), `MAX_GAMESTATE_CHARS = 0x20000`,
`sizeof(gameState) = 0x265E0`.

**The one thing that could NOT be measured**, and the caveat this section exists
to record: the *gamestate* block reader at `0x0072FAD0` hands off to
`0x084A5FCF`, which is inside the Themida-virtualized `.tvm0` section and is not
statically recoverable — and so is the constant-table -> gameState merge itself
(`0x00612850`, the CSV selector, writes `g_constConfigStrings` @ `0x2A99A44`
and a CRC @ `0x2A99A50` that **nothing in `.text` reads**, and `0x612850` has
zero `.text` callers). C1's *own* writer at `0x0072AF20` skips any index whose
offset is 0, so it never emits an empty value; our `CODOL_WriteConfigstrings`
does emit an allocated `""`. **Whether the virtualized reader stores that as
`""` or ignores it as "inherit the constant" is unmeasured.**

Why this is nevertheless not a blocker for coop and zm: their constant windows
**end exactly where a complete published window ends** (index 63 and 130). When
the full window publishes, there is nothing above it to inherit and the
ambiguity is moot. It only bites on a *truncated* window, and in that case the
surviving constants are validated by the 699-slot sweep — which is precisely the
`181 beretta_so 0 2` family. That is the residual risk of truncation, and it is
the reason the new warning line names the slot that truncated: a truncation is
something to go and fix, not a steady state to live in.

---

## 3. Where the window already was, and what I changed

**MEASURED**, `src/sv_main.c:5556-5568`: the server already loads
`mp/constConfigStrings_<category>.csv` for the current category and installs it
through `CODOL_SetServerInheritedConfigstrings()` **immediately before** calling
`CODOL_InitializeServerWeaponConfigstrings(codol_zoneType->string)`; and
`CODOL_ImportConstantConfigstrings` (`src/codol/snapshot/codol_configstrings.c:76`)
stores each row at its own configstring index. So the category's whole weapon
window was already sitting in the inherited configstrings when the old code
decided coop and zm had none. No new asset load was needed — the data was one
`CODOL_GetConfigstring(inherited, CODOL_CS_WEAPONS + i)` away.

Also **MEASURED** and reassuring for this fix: the gamestate's `type` field and
the constant table the server loads come from the same string
(`CODOL_WriteGamestate(..., zone_type, ...)` in
`src/codol/snapshot/codol_configstrings.c:281`, and `sv_main.c:5556`), so the
two sides genuinely share a namespace and a name mismatch inside it is a
publication bug rather than a category mix-up.

### The change (`src/codol/weapon/codol_sv_weapons.c`, the only file edited)

1. **`collect_weapon_window()`** (new) establishes the window against a
   **scratch** registry, so a half-registered chain can never survive into the
   registry the server keeps. Two deliberately different walks:

   * **mp** keeps its previous walk byte for byte:
     `mp/coWeaponAttachmentTable.csv` is an *ordered list*, not a slot map — a
     parent's partner is appended *between* two rows, so row `k` does not sit at
     slot `k+2`, and the `181 cheytac_mp 11 10` record is what that looks like
     when it drifts. A row that will not register is still a hard failure, as
     before.
   * **coop/zm** walk the constants *by slot*, because the constant table **is**
     the slot map (§1.1). When a slot is already filled by the partner the
     previous row appended, the walk only has to *agree* with the constant;
     disagreeing means our replay and the client's have diverged and the window
     stops there.

2. The kept registry is **replayed from exactly the surviving names**, so it
   holds no slot the published window does not name.

3. **`CS 6517` is now published for every category** as our own contiguous
   prefix. The old `table ? count : 0u` / `table ? count_text : ""` is gone, and
   with it the "coop/zm keep the empty value" comment that §0 refutes.

4. **State across a category change.** `CODOL_InitializeServerWeaponConfigstrings`
   now calls `CODOL_ResetServerWeaponRegistry()` and clears
   `codol_ammo_binding_refused[]` **on entry**. `registry`, `valid` and `error`
   are file-static; previously a *failed* init left the previous category's
   registry allocated behind `valid = 0`. Now a category change cannot carry one
   across even on the fail path. (`published` is already cleared for every spawn
   by `SV_ClearServer -> CODOL_ResetServerConfigstrings`,
   `src/sv_main.c:3042-3043`, and the engine->wire map by `CODOL_ResetWeaponMap`,
   `src/codol/snapshot/codol_game.c:273` — **MEASURED**; not duplicated here.)

5. **One log line per map**, saying what the category's constants demand versus
   what was published, and — as a `Com_PrintWarning` — the slot and weapon name
   that truncated it. A short window is now a diagnosis instead of a silent
   unarmed match. Grep `CoDOL weapon window (`.

The blanked tail is deliberately kept. **MEASURED**,
`src/codol/snapshot/codol_configstrings.c:272`: `CODOL_WriteConfigstrings` skips
only `NULL` values, so an explicitly-set empty string **is** transmitted. That
is what suppresses the constants above our count on the client and keeps its
registration order identical to ours. Leaving them unset instead would let the
client register weapons the server has no wire slot for.

---

## 4. The `CS 6517` count published per category, and why it is safe

The hard invariant: C1's `CG_Init` loop at `0x47d1d0` walks `1..count-1` over
`bg_weaponDefs` and dereferences the definition at `0x47c1f7`
(`cmp dword [esi+0x344], 8`) with **no NULL check**. The count must never exceed
the number of published, buildable definitions.

What this implementation publishes is, by construction, **the longest contiguous
prefix `0..count-1` in which every slot registered through `register_stock()`**
— i.e. `replay_weapon()` plus a successful
`CODOL_LoadMountedWeaponTail` / `CODOL_ComposedWeaponTail` against the archives
*this match actually mounted*. It is a runtime property of the mounted set, not
a number written down anywhere, and it cannot exceed what registered. That is
the entire safety argument, and it is why I did not simply publish the
constants' own `64` / `131`.

Two measured facts sharpen it (§2.2). First, registration is strictly
append-at-`++bg_lastParsedWeaponIndex` (`0x0041F648`), so every index above
`bg_lastParsedWeaponIndex` is still the zero left by the `0x41F570` memset —
confirming that `0x0047C1F7` (`cmp dword [esi+0x344], 8`) faults on
`NULL + 0x344` and that this is a **NULL definition, not a count cap**. The
requirement is `atoi(CS[6517]) <= bg_lastParsedWeaponIndex + 1`, which a
registered contiguous prefix satisfies by construction. Second, because
registration only ever appends, **a blank in the middle of the window shifts
every later slot by one**; a contiguous prefix followed by an all-blank tail is
the only shape that does not, and it is the shape this code produces.

Expected values, **INFERRED** from an offline roster check and stated as an
expectation, not a result — the runtime walk is the authority and the new log
line reports the real number:

| category | constants demand | expectation |
|---|---|---|
| mp | 176 (22 holes) | unchanged: whatever the attachment table yields today |
| coop | 64 | 64 if the de-duplicated zone names resolve; otherwise a truncation the log names |
| zm | 131 | 131 likewise |

That caveat is honest about a real limit of the offline check, worth recording
because it is a trap. Harvesting weapon names from the zones by reading the
inline name at `blob+0xBFC` (the method in `alpha0022/zm_weapons.py:167-188`,
and the method `docs/zone_assets/ALL_weapon.txt` partly relies on) only sees
**inline-named** definitions. **MEASURED**: `common_gametype_zm` holds 174
type-28 assets of which **140 are inline-named and 34 carry a de-duplicated name
reference**; `common_gametype_coop` holds 78, of which 64 inline and 14
de-duplicated. Against the full mounted set (9 startup archives + the gametype
pair + the level and session zones) that harvest reports 3 coop and 16 zm window
names as absent — but every one of them
(`minigun_zm`, `uzi_zm`, `m16_zm`, `ray_gun_zm`, `m1911_zm`,
`m16_grenadier_reddot_so`, ...) **is present as bytes in its own gametype
zone**, so they are almost certainly among those de-duplicated definitions.
Only the server's own loader, which resolves block references exactly
(`CODOL_LoadBlockString`), can settle it — which is exactly why the
implementation asks it at runtime instead of trusting a harvest.

Corroborating datum that the harvest is otherwise sound: it reports `m1911_zm`
as not inline-named, and `alpha0022/zm_weapons.py:70-73` independently records
`m1911_zm` as *not buildable in this build*, while listing `coltanaconda_zm`,
`glock_zm`, `pp2000_zm`, `tmp_zm` as buildable — all four of which the harvest
does find.

### 4.1 Prior art, and where it stops

`alpha0022` solved zm with **one** weapon: `coltanaconda_zm` published at slot 2
with `CS[6517] = "3"` and the rest of the window blanked
(`zm_weapons.py:68-87,120-131`; `game-server.py:7770-7796`), live-verified
2026-09-02 (player spawned holding it, round HUD rendered, no `0x0047C1F7`
fault). That is the proof this work builds on: **a server-published non-mp
weapon configstring does register a non-NULL def.**

Two limits of it, both **MEASURED**:

* its cap table is
  `WEAPON_COUNT_BY_ZONE_TYPE = {"mp": 55, "coop": 0, "zm": 0}`
  (`configstring_map.py:327`), with an `armed_high` escape hatch documented as
  "the ONE sanctioned way to a nonzero CS[6517] on coop/zm";
* its `arm_plan()` gates on `ztype != "mp"`, so **coop gets `coltanaconda_zm`
  too** — a zm asset name under coop zones, where the constants demand
  `beretta_so` (`zm_weapons.py:126`; the selftest asserts it at `:234`). That is
  the same class of bug as §2.1, in the other direction.

This implementation supersedes both: the window comes from each category's own
constants, and the count is the measured prefix rather than a per-category
constant. Note also that the zm starting pistol is index **48**
(`coltanaconda_zm`) in the real zm window, not index 2.

---

## 5. Build

**MEASURED.** `src/codol/weapon/codol_sv_weapons.c` compiles clean:

* `make obj/codol/codol_sv_weapons.o` (msys2 make, `TMP` redirected to
  `obj/tmpbuild`) succeeds;
* a `-Wall -Wextra` compile of the translation unit emits only the three
  pre-existing `-Wsign-compare` warnings in `CODOL_BuildServerAmmoBindings`
  (lines 150/156/164), none from the new code.

The default target was **not** built and nothing was copied into `bin/`.

The makefile's `test_codol_sv_weapons` recipe could not be run: its link line is
stale and fails with ~25 undefined references out of
`src/codol/snapshot/codol_game.c` (`CODOL_MsgReadInit`, `CODOL_ReadLong`,
`CODOL_WeaponStatePrimaryWeapon`, `CODOL_PlayerStateExtClear*`, ...) — a missing
source list, pre-existing and unrelated to this change. **Every translation unit
compiled, including the edited one**; only the link failed. Reading the test
against the new code (`tests/test_codol_sv_weapons.c:104,154-156`): line 104
exercises the unchanged mp path including the partner at CS 5365
(`scarsapr_mp`); lines 154-156 assert that a failed init leaves no registry and
does not touch `published`. Both still hold, and the new entry-reset makes the
first assertion stronger rather than weaker.

---

## 6. What is still missing

1. **Live verification.** Nothing here was confirmed against a running client.
   A coop and a zm connect are the real test, and the new
   `CoDOL weapon window (<category>): published N ...` line is the first thing
   to read.
2. **mp is still on the attachment table.** The mp constants demand 176 over
   CS 5363..5537 with 22 unnamed holes (CS 5437-5438, 5440-5460). Matching
   vanilla there means deciding what fills those holes, and it is a change to
   the live mp path, so it is deliberately out of this pass. It is the obvious
   next item for the "700 weapons like C1" mandate — and `181 cheytac_mp 11 10`
   says the mp window has a live partner off-by-one of its own.
3. **The `ps.weaponsEquipped[15]` ring.** **MEASURED**,
   `alpha0022/docs/zombies_weapon_crash.md:20-27`: `CS[6517]=0` does *not*
   prevent a second, independent weapon-index sink — the equipped ring at
   `ps+0x2A0`, seeded from the class loadout, whose fill (`sub_422BE0`) and
   cycle (`sub_4812F0`) both deref `bg_weaponDefs[idx]`. A coop/zm spawn must
   not carry mp loadout indices into it. That is player/loadout code
   (`src/codol/player/**`, `codol_script_profile_loadout.c`), **not** this
   subsystem, and it is not covered by this change.
4. **No coop/zm starting loadout.** Publishing the window makes the weapons
   registerable; something still has to give the player one. For zm the prior
   art is `coltanaconda_zm` (index 48 in the real window); for coop, index 2
   `beretta_so` is what the constants put first.
5. **No patch handed to another owner.** This change is confined to
   `src/codol/weapon/codol_sv_weapons.c`. No edit is needed in `src/sv_main.c`,
   `src/filesystem.c`, `src/sv_client.c`, `src/codol/assets/**`,
   `src/codol/script/**` or `bin/home/codol_rawfiles/**`.
6. **Unmeasured: does the virtualized gamestate reader honour an empty
   value?** §2.3 proves `d <idx> ""` blanks a slot on the *reliable command*
   path, but the gamestate block reader is inside `.tvm0` and could not be
   read. If it treats a zero-length string as "inherit the constant", a
   *truncated* coop/zm window leaves live constants above the prefix for the
   699-slot sweep to validate. Cheap live check: publish a deliberately short
   coop window and look for a `181 <name> 0 <slot>` naming a slot above the
   count. Moot when the full window publishes, since the coop/zm constant
   windows end exactly where a complete published window ends.
7. **The map-identity coupling noted in the evidence doc** (`§7.3`: if the
   gamestate ever announces `coop_training_mp_killhouse_sh`, the server must
   mount that identity too) affects which archives are resident and therefore
   how long the coop prefix gets. It is another owner's call; this subsystem
   will report the resulting count either way.

---

## §7. Parent resolution of the two flagged items, 2026-09-17

Two items left open above are resolved here. Both were re-measured by the
parent directly against
`D:\CoD\CODOL Builds\Call of Duty Online 1.1.1.13\C1.exe` (pefile + capstone,
ImageBase 0x400000), not taken from a worker report.

### 7.1 The `defaultweapon_mp` branch: it is `"none"`. No contradiction exists.

The helper pass read `0x0041F7B8 mov edx, 0xC30704` as pointing at
`"defaultweapon_mp"` and reported "name == defaultweapon_mp -> return 0" as
MEASURED. The weapon-window pass flagged that as self-contradicting, because
taken literally it would raise `181 defaultweapon_mp 0 1` on the CG_Init
sweep's first iteration in every category and no mp match would ever start.

**The flag was right and the reading was wrong — but the error was the string,
not the branch polarity.** MEASURED:

```
0xC30704 = "none"
```

So the special case is `BG_GetWeaponIndexForName("none") -> 0`, which is simply
slot 0 naming itself. The real sequence is:

```
0041F7B2  push esi                 ; name
0041F7B3  mov  eax, 0x7fffffff     ; n
0041F7B8  mov  edx, 0xC30704       ; "none"
0041F7BD  call 0x6283D0            ; case-insensitive strncmp, 0 == match
0041F7C5  test eax, eax
0041F7C7  je   0x41F80F            ; match -> xor eax,eax; return 0
0041F7C9  push esi / xor eax,eax
0041F7CC  call 0x41F6C0            ; otherwise the ordinary registered lookup
```

`0x6283D0` confirmed MEASURED as a length-bounded case-insensitive compare
(`lea ebx,[eax-0x41] / cmp ebx,0x19 / add eax,0x20` on both operands, `xor
eax,eax` on the equal path at `0x628411`, `setge`-based sign otherwise). Its
`0 == match` polarity is corroborated by the const-table selector at
`0x00612850`, which does `test eax,eax / jne <keep mp csv>` against `"coop"`
(`0xC42378`) and `"zm"` (`0xC689AC`) — both strings also re-measured here.

Consequence: `validate(1)` on `defaultweapon_mp` falls through to the ordinary
lookup, gets its registered index 1, `got == weapIdx`, and returns cleanly.
The sweep starts at `i = 1`, so slot 0 (`"none"`, CS 5362) is never validated
at all. Everything is consistent and **nothing in the shipped code needed to
change**.

Recorded because this is the [[offset-name-trap]] pattern in a new place: the
disassembly was right, the symbol name attached to a data address was not.
Re-measure the string literal before believing a branch that contradicts a
working match.

### 7.2 The empty-value question is now HALF measured, and the open half is the half that matters

Split the question by path, because the two do not share a reader:

**Reliable-command path — MEASURED, and the answer is "it really does blank".**
`CL_SetConfigstring @0x00487440` has **no** `if (!value[0]) return;`. Its only
gate is `strcmp(old,new) != 0`. On a difference it memcpys the pool aside,
`memset`s all 6519 offsets to 0, sets `dataCount = 1` (so `stringData[0]` is
`'\0'`), and re-appends every non-empty value. An empty value is "skipped" at
`0x4875F0`, which leaves `stringOffsets[N] == 0` pointing at that `'\0'` — i.e.
skipping *is* how the slot becomes `""`. No reader in `.text` has a const-table
fallback. So `d <idx> ""` is a real, effective blank, and in the weapon window
it also re-runs `ValidateWeaponConfigString` immediately at `0x4673C7`.

**Gamestate-block path — STILL UNMEASURED, and unchanged from §6.** C1's own
writer at `0x0072AF20` *skips* indices whose offset is 0, so an empty
configstring is not representable in the block it emits; our
`CODOL_WriteConfigstrings` instead emits an allocated `""` for tail slots. The
matching reader at `0x0072FAD0` dispatches into the Themida-virtualised `.tvm0`
section (`call 0x084A5FCF`) and could not be read. Whether it stores a
zero-length string as `""` or treats it as "inherit the constant" is the one
thing still not known.

This only bites on a **truncated** window. The coop and zm constant windows end
exactly where a complete published window ends (63 and 130), so a full publish
has nothing above it to inherit. The live check stands: publish a deliberately
short coop window and watch for `181 <name> 0 <slot>` naming a slot above the
count.

### 7.3 Tooling correction

`tools\ps_xref.py` does not exist (the `ps_xref.py` in the
project notes is the alpha0022 one, for playerstate offsets).
`tools/codol_c1_disasm.py` exists, but its `--xref` sweeps linearly from the
section start and silently desynchronises on inline data, returning zero hits
for real constants. For address-level work on C1.exe, use pefile + capstone
directly with a section-map lookup, and scan `E8`/`E9` rel32 across **all**
sections — `0x00450640` (CG_Init) and `0x00612850` (const-CSV selector) have no
`.text` callers at all; they are entered from `.tvm0`.
