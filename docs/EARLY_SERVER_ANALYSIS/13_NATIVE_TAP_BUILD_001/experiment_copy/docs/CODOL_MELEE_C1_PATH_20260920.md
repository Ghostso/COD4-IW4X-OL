# C1's melee path, end to end — and the one server input we never send

Reverse engineering of `C1.exe` (CoDOL 1.1.1.13, ImageBase `0x400000`) to find
why ~22 of 40 zm weapons play no melee animation on our server while every
weapon plays one on the vanilla CoDOL server.

**VERDICT (one line): C1 takes the melee viewmodel animation, the melee damage,
the melee timings, the melee rate, the knife view/world model and the melee
sounds from a row of the client stringtable `mp/coKnifeStatsTable.csv`, selected
by the playerstate field `ps+0x338` (netfield index 129, 32 bits). Our server
never writes that field, so it is 0, so no row is selected, so nothing overrides
the held weapon's animation slot 7 — and when slot 7 is the pooled empty string
C1 falls back to the *idle* animation, which looks like "no melee animation".**

Everything below is MEASURED from `C1.exe` and the shipped fastfiles. Every
claim carries the address and the instruction text it rests on. Linear
disassembly was produced with capstone over the whole `.text` section with
resume-over-bad-bytes; every xref quoted here was verified by disassembling the
target, not by `tools/codol_c1_disasm.py --xref`.

---

## 0. Two corrections to previously recorded anchors

### 0.1 `0x45c500` is NOT the weapon xanim name getter

It is a killstreak/HUD field getter. Full body:

```
0045c500  833de8c26f0108     cmp dword ptr [0x16fc2e8], 8
0045c507  7d03               jge 0x45c50c
0045c509  33c0               xor eax, eax
0045c50b  c3                 ret
0045c50c  a1acd2c306         mov eax, dword ptr [0x6c3d2ac]
0045c511  8b0485583b6d01     mov eax, dword ptr [eax*4 + 0x16d3b58]
0045c518  350c400b49         xor eax, 0x490b400c          ; deobfuscated cgs/cg ptr
0045c51d  8b88c0350000       mov ecx, dword ptr [eax + 0x35c0]
0045c523  69c9500b0000       imul ecx, ecx, 0xb50
0045c529  83bc0124ae150000   cmp dword ptr [ecx + eax + 0x15ae24], 0
0045c531  74d6               je 0x45c509
0045c533  8b44907c           mov eax, dword ptr [eax + edx*4 + 0x7c]
0045c537  c3                 ret
```

`eax` here is a *client global*, not a `WeaponDef`. Its only three callers are
`0x5debaa`, `0x5debec`, `0x5dec16`, inside a string dispatch that compares
`killstreakID4` (`0xc67ae8`), `killstreakTarget0..4` (`0xc67af8`, `0xc67b0c`,
`0xc67b20`, `0xc67b34`, `0xc67b48`) and `score` (`0xc44478`), passing
`edx` = 0..4. It never touches a weapon definition. **Any reasoning that used
`0x45c500` as "the weapon xanim name getter" should be discarded.** The
question "what does *that* caller do with the pooled empty string" has no
answer because that function is not on the melee path at all.

### 0.2 The real name array is 3 × 48 entries, not 144 flat

`BG_WeaponHasAnim` at `0x421e70`:

```
00421e70  push ebp
00421e71  mov ebp, esp
00421e73  mov edx, dword ptr [ebp + 8]          ; playerState
00421e76  cmp dword ptr [edx + 0x35c], 1        ; dual-wielding?
00421e7d  mov eax, dword ptr [eax*4 + 0x150d720]; bg_weaponDefs[weaponIndex]
00421e84  jne 0x421eb9
00421e86  mov edx, dword ptr [eax + 0x140]
00421e8c  cmp byte ptr [edx], 0
00421e8f  je 0x421eb9
00421e91  cmp dword ptr [ebp + 0xc], 0
00421e95  jne 0x421ea9
00421e97  mov eax, dword ptr [eax + ecx*4 + 0x13c]   ; dual, right hand
...
00421ea9  mov edx, dword ptr [eax + ecx*4 + 0x1fc]   ; dual, left hand
...
00421eb9  mov eax, dword ptr [eax + ecx*4 + 0x7c]    ; normal hand
00421ebd  xor ecx, ecx
00421ebf  cmp byte ptr [eax], cl
00421ec1  setne cl                                    ; "has anim" = name non-empty
```

`0x13c - 0x7c = 0xc0 = 48*4` and `0x1fc - 0x13c = 0xc0`. So the def carries
**three 48-entry name arrays**: `+0x7c` (normal), `+0x13c` (dual right),
`+0x1fc` (dual left). Loop bounds elsewhere confirm 48: `mov ecx, 0x2f` at
`0x47b856`, `cmp eax, 0x2e / jl` at `0x47b933`, `cmp edi, 0x30 / jl` at
`0x47c12a`.

**The weapon-def pointer array is `0x150d720`, indexed by weapon index**
(`mov eax, dword ptr [eax*4 + 0x150d720]`, seen at `0x41bd3c`, `0x421e7d`,
`0x47ad66`, `0x47b6f3`, `0x47b7df`, `0x47c1d0`, `0x47c5a0`).

---

## 1. Slot 7 IS the melee animation — proven through the weapAnim jump table

`PM_StartWeaponAnim` at `0x4180b0`:

```
004180b0  83780408           cmp dword ptr [eax + 4], 8       ; pm_type >= 8 -> ignore
004180b4  7d40               jge 0x4180f6
004180b6  8b9068020000       mov edx, dword ptr [eax + 0x268] ; ps->weapAnim
004180bc  f7d2               not edx
004180be  81e200040000       and edx, 0x400                   ; toggle the restart bit
004180c4  0bd1               or  edx, ecx                     ; new anim id
004180c6  83b85c03000001     cmp dword ptr [eax + 0x35c], 1   ; dual wield
004180cd  899068020000       mov dword ptr [eax + 0x268], edx
004180d3  7517               jne 0x4180ec
004180d5  8b9084020000       mov edx, dword ptr [eax + 0x284] ; second hand weapAnim
...
004180ec  c7808402000000000000 mov dword ptr [eax + 0x284], 0
```

`PM_Weapon_Melee` (see §3) ends with:

```
0041bef8  cmp byte ptr [ebp - 1], cl      ; cl = 0; [ebp-1] = "charge" flag
0041befb  mov eax, esi                    ; ps
0041befd  mov ecx, 9
0041bf02  jne 0x41bf09                    ; charge  -> weapAnim 9
0041bf04  mov ecx, 8                      ; normal  -> weapAnim 8
0041bf09  call 0x4180b0
```

`CG_IsPlayerMeleeing` at `0x47cce0` confirms the pair:

```
0047ccf2  mov eax, dword ptr [ecx + 0x268]
0047ccf8  and eax, 0xfffffbff
0047ccfd  cmp eax, 8
0047cd00  je 0x47cd0a
0047cd02  cmp eax, 9
0047cd05  je 0x47cd0a
0047cd07  xor al, al
```

`weapAnim` is then mapped to an *animation index* through the jump table at
`0x47be58` used by the viewmodel-rate function `0x47b770`:

```
0047b8aa  and eax, 0xfffffbff       ; eax = ps->weapAnim without the restart bit
0047b8b2  cmp eax, 0x28
0047b8b5  ja 0x47be08
0047b8bb  jmp dword ptr [eax*4 + 0x47be58]
```

Table entries 8 and 9 (dumped from `0x47be58`):

```
weapAnim  8 -> 0047b9dd    0047b9e1  push 7   ; call 0x47ad10
weapAnim  9 -> 0047b9f0    0047b9f4  push 8   ; call 0x47ad10
```

So **weapAnim = animIndex + 1**, and **animation index 7 = melee, 8 = melee
charge**, i.e. name slots `def+0x098` and `def+0x09c`. The prior worker's
index claim is CONFIRMED (their `0x45c500` anchor was not).

Cross-check from the duration table at `0xcd6640` (`{primary, fallback}` def
offsets, indexed by animation index):

```
index 07 -> 0x5c0 (iMeleeTime)          index 08 -> 0x5c4 (meleeChargeTime)
```

matching what `PM_Weapon_Melee` writes into `weaponTime`.

---

## 2. THE NAME-SIDE ANSWER: `0x47c090` — fallback **and** a knife-table override

This is the function the parent asked for: the one that turns the 48 names into
registered XAnims. It is the only consumer of the name array on the play path.

```
0047c090  push ebp
0047c091  mov ebp, esp
0047c093  push ebx
0047c094  mov ebx, dword ptr [ebp + 0xc]    ; arg2 = knife-table ROW pointer (may be 0)
0047c099  push 0x18c
0047c09e  mov ecx, 0x20
0047c0a3  call 0x61d2e0                     ; alloc 0x18c = 0x31 * 8 - header
0047c0b5  mov dword ptr [esi], 0x31
0047c0c3  mov edi, 1                        ; anim index 1 .. 0x2f
0047c0d0  mov ecx, dword ptr [ebp + 0x10]   ; arg3 = &def->szXAnims[0]  (= def+0x7c)
0047c0d3  mov eax, dword ptr [ecx + edi*4]  ; names[i]
0047c0d6  cmp byte ptr [eax], 0
0047c0d9  je 0x47c0df
0047c0db  mov ecx, eax                      ; non-empty: use it
0047c0dd  jmp 0x47c0e2
0047c0df  mov ecx, dword ptr [ecx + 4]      ; *** EMPTY NAME -> names[1] (idle) ***
0047c0e2  mov eax, dword ptr [ebp + 8]      ; arg1 = WeaponDef
0047c0e5  cmp byte ptr [eax + 0xbf0], 0     ; per-weapon "own melee anims" flag
0047c0ec  jne 0x47c113                      ; set -> no override
0047c0ee  cmp edi, 7
0047c0f1  jne 0x47c0fc
0047c0f3  test ebx, ebx
0047c0f5  je 0x47c113                       ; no row -> no override
0047c0f7  mov eax, dword ptr [ebx + 0x3c]   ; row->meleeAnimName        (CSV column 21)
0047c0fa  jmp 0x47c108
0047c0fc  cmp edi, 8
0047c0ff  jne 0x47c113
0047c101  test ebx, ebx
0047c103  je 0x47c113
0047c105  mov eax, dword ptr [ebx + 0x40]   ; row->meleeChargeAnimName  (CSV column 22)
0047c108  test eax, eax
0047c10a  je 0x47c113
0047c10c  cmp byte ptr [eax], 0
0047c10f  je 0x47c113
0047c111  mov ecx, eax                      ; *** OVERRIDE the melee name ***
0047c113  push ecx
0047c114  push 2                            ; asset type 2 = xanim
0047c116  call 0x4cb8e0                     ; DB_FindXAssetHeader
0047c11d  mov word ptr [esi + edi*8 + 4], cx
0047c122  mov dword ptr [esi + edi*8 + 8], eax
0047c126  inc edi
0047c12a  cmp edi, 0x30
0047c12d  jl 0x47c0d0
```

Two decisive facts:

1. **There IS a name-side fallback, and it is the idle animation.** An empty
   `szXAnims[7]` does not mean "play nothing"; it means the melee slot is
   registered with `szXAnims[1]`. The viewmodel therefore *continues to look
   idle* for the whole melee — which is exactly the reported symptom, and is
   why the bug reads as "no animation" rather than a hitch or a T-pose.
2. **Indices 7 and 8 — and only 7 and 8 — can be overridden from a
   knife-stats-table row**, provided `def+0xbf0 == 0`.

The caller supplies the three arguments:

```
0047c23b  mov dword ptr [edi], eax           ; cache the melee row index
0047c23d  lea eax, [esi + 0x7c]              ; &def->szXAnims[0]
0047c240  push eax
0047c241  push ebx                           ; knife row pointer
0047c242  push esi                           ; WeaponDef
0047c243  call 0x47c090
```

and `ebx` is resolved a few instructions earlier, in `0x47c1c0`:

```
0047c1c0  cmp dword ptr [edi + 4], 0         ; anim set already registered?
0047c1c4  je 0x47c1ce
0047c1c6  cmp dword ptr [edi], eax           ; ... for this melee row?
0047c1c8  je 0x47c294                        ; yes -> nothing to do
0047c1d0  mov esi, dword ptr [ecx*4 + 0x150d720]   ; def = bg_weaponDefs[weaponIndex]
0047c1d7  test eax, eax                      ; eax = melee row index (1-based)
0047c1d9  jne 0x47c1df
0047c1db  xor ebx, ebx                       ; *** row index 0 -> NO ROW ***
0047c1dd  jmp 0x47c1f7
0047c1df  lea ebx, [eax - 1]
0047c1e2  cmp ebx, dword ptr [0x1536be4]     ; knifeTableRowCount
0047c1e8  jb 0x47c1ee
0047c1ea  xor ebx, ebx                       ; out of range -> NO ROW
0047c1ec  jmp 0x47c1f7
0047c1ee  imul ebx, ebx, 0x5c                ; 0x5c bytes per row
0047c1f1  add ebx, 0x150e210                 ; knifeTable base
```

and the melee row index comes straight from the playerstate. Both call sites:

```
0047c5e0  mov edx, dword ptr [esi + 0x338]   ; ps->meleeRow
0047c5e6  push edx
0047c5e7  push ebx                           ; weapon index
0047c5e8  call 0x47c430                      ; -> 0x47c49b -> 0x47c1c0

00480956  mov eax, dword ptr [esi + 0x338]
0048095c  push eax
0048095d  push ebx
0048095e  call 0x47c430
```

and the weapon whose def is used is the **held** weapon (or the offhand when
`ps+0x344 & 2`), never a separate melee weapon:

```
0047c5b7  test byte ptr [esi + 0x344], 2
0047c5be  je 0x47c5c8
0047c5c0  mov eax, dword ptr [esi + 0x328]   ; offhand weapon index
0047c5c6  jmp 0x47c5ce
0047c5c8  mov eax, dword ptr [esi + 0x33c]   ; ps->weapon
```

---

## 3. `PM_Weapon_Melee` (`0x41bd30`) — the same row drives the timings

```
0041bd30  push ebp
0041bd31  mov ebp, esp
0041bd36  mov eax, dword ptr [esi + 0x33c]           ; ps->weapon
0041bd3c  mov edx, dword ptr [eax*4 + 0x150d720]     ; def
0041bd43  mov eax, dword ptr [esi + 0x338]           ; ps->meleeRow
0041bd51  test eax, eax
0041bd53  jne 0x41bd5c
0041bd55  xor edi, edi                               ; no row
...
0041bd5d  cmp eax, dword ptr [0x1536be4]
0041bd71  imul eax, eax, 0x5c
0041bd74  add eax, 0x150e210
0041bd7e  cmp byte ptr [edx + 0xbf0], 0              ; weapon has its own melee?
0041bd85  je 0x41bde4                                ; no -> knife-table branch
  ; ---- def+0xbf0 != 0 : legacy branch, timings from the def ----
0041bdb1  mov edi, dword ptr [ecx + 0x5c4]           ; meleeChargeTime
0041bdbd  mov eax, dword ptr [edx + 0x5a4]           ; meleeChargeDelay
0041bdc3  mov byte ptr [ebp - 1], 1                  ; charge
0041bdcf  mov edi, dword ptr [edx + 0x5c0]           ; iMeleeTime
0041bdd5  mov eax, dword ptr [edx + 0x5a0]           ; iMeleeDelay
0041bddb  mov byte ptr [ebp - 1], 0                  ; normal
  ; ---- def+0xbf0 == 0 : knife-table branch ----
0041bdf1  fld dword ptr [edi + 0x1c]                 ; row+0x1c = charge threshold (CSV col 7)
0041bdf6  fld dword ptr [0xc323a8]                   ; default 64.0 when no row
0041bdff  fild dword ptr [esi + 0x4a8]               ; ps melee-charge counter
0041be33  fld dword ptr [edi + 0x34]                 ; row+0x34 (CSV col 14) charge
0041be38  fld dword ptr [edi + 0x2c]                 ; row+0x2c (CSV col 12) normal
0041be42  fld dword ptr [edi + 0x38]                 ; row+0x38 (CSV col 13) charge
0041be47  fld dword ptr [edi + 0x30]                 ; row+0x30 (CSV col 11) normal
0041be4d  fld dword ptr [edi + 0x28]                 ; row+0x28 (CSV col 10) rate
0041be96  test cl, cl                                ; no row -> fall back to the def
0041be9a  mov edi, dword ptr [edx + 0x5c4]
0041bea8  mov edi, dword ptr [edx + 0x5c0]
0041bed8  mov dword ptr [esi + 0x26c], edi           ; ps->weaponTime
0041bede  mov dword ptr [esi + 0x270], eax           ; ps->weaponDelay
```

Called from the melee trigger `0x41c0f7`..`0x41c1a5` (see §5).

The animation *rate* uses the row too, in `0x47ad10`
(`CG_GetWeaponAnimRate(clientIdx, weaponIdx, animIdx)`):

```
0047ae18  cmp byte ptr [edx + 0xbf0], 0
0047ae1f  jne 0x47ae5b
0047ae21  mov eax, dword ptr [ebp + 0xc]     ; animation index
0047ae24  cmp eax, 7
0047ae27  je 0x47ae2e
0047ae29  cmp eax, 8
0047ae2c  jne 0x47ae5b
0047ae2e  mov esi, dword ptr [esi + 0x338]   ; ps->meleeRow
0047ae41  imul esi, esi, 0x5c
0047ae44  add esi, 0x150e210
0047ae4c  fld dword ptr [esi + 0x28]         ; row rate  (CSV col 10)
0047ae54  fld1                               ; no row -> rate 1.0
```

Melee **damage** is also row-sourced (`0x4dfdd9`..`0x4dfe11`):

```
004dfdd9  mov eax, dword ptr [edi + 0x64]    ; entityState melee row (see §6)
004dfdf0  add eax, 0x150e210
004dfdfc  cmp byte ptr [ecx + 0xbf0], 0
004dfe03  jne 0x4dfe11
004dfe05  mov ebx, dword ptr [eax + 0x10]    ; row+0x10 = damage (CSV col 4)
004dfe0a  mov dword ptr [ebp - 0x18], 0
004dfe11  mov ebx, dword ptr [ecx + 0x590]   ; else def iMeleeDamage
```

and so are the melee **range/width** (`0x573a84`..`0x573ac0`,
`row+0x10/0x1c/0x20/0x24`) and the **world knife model**
(`0x4503d5`..`0x4503f9`, `row+0x44`, falling back to `def+0x30`).

---

## 4. `ps+0x338` is the melee slot. It is a knife-table row index, not a weapon index

### 4.1 The table: `mp/coKnifeStatsTable.csv`

`BG_LoadKnifeStatsTable` at `0x41fd00`:

```
0041fd09  push 0xc40cf4                      ; "mp/coKnifeStatsTable.csv"
0041fd10  push 0x25                          ; asset type 37 = stringtable
0041fd12  mov dword ptr [0x1536be4], ebx     ; rowCount = 0
0041fd18  call 0x4cb8e0
0041fd35  cmp eax, 1                         ; need > 1 rows
0041fd3a  cmp dword ptr [esi + 4], 0xb       ; need > 11 columns
0041fd48  mov dword ptr [ebp - 4], 0x150e214 ; dest = &rows[0].field04
...
004200b9  add dword ptr [ebp - 4], 0x5c      ; 0x5c bytes per row
004200cc  mov dword ptr [0x1536be4], eax     ; rowCount
```

Row layout, derived from the per-column stores (`0x61ee90` =
`StringTable_GetColumnValueForRow`, `0xada2a7` = atoi, `0xada3fa` = atof,
`0x4cb8e0` = `DB_FindXAssetHeader`):

| CSV col | row offset | writer | meaning |
|---|---|---|---|
| 0 | +0x00 | `0041fd60 mov [ecx-4], eax` | row name (`mel_knife`, `zknife_standard`, …) |
| 1 | +0x04 | `0041fe02` | localized display string |
| 2,3 | +0x08,+0x0C | `0041fe0f`, `0041fe2d` | (unused in the shipped table) |
| 4 | +0x10 | `0041fe44` (atoi) | **melee damage** |
| 5 | +0x14 | `0041fe6b` (atoi) | secondary damage |
| 6 | +0x18 | `0041fe7f` | |
| 7 | +0x1C | `0041fea1` | **charge threshold** (default `0xc323a8` = 64.0) |
| 8,9 | +0x20,+0x24 | `0041fec0`, `0041fedc` | melee range / width |
| 10 | +0x28 | `0041fefe` | **animation rate** |
| 11 | +0x30 | `0041ff1d` | |
| 12 | +0x2C | `0041ff39` | normal melee time factor |
| 13 | +0x38 | `0041ff5b` | |
| 14 | +0x34 | `0041ff7a` | charge melee time factor |
| 15 | +0x44 | `0041ffa8` (xmodel) | **world knife model** |
| 16 | +0x48 | `0041ffde` (xmodel) | **viewmodel knife model** |
| 17–20 | +0x4C..+0x58 | `00420003`…`00420087` | melee sounds |
| 21 | +0x3C | `004200a0 mov [edx+0x38], eax` | **melee viewmodel xanim** |
| 22 | +0x40 | `004200b6 mov [ecx+0x3c], eax` | **melee-charge viewmodel xanim** |
| 23 | — | read at `0041fd75` | **zm-only flag** |

The zm gate, verbatim:

```
0041fd74  push ebx
0041fd75  mov edi, 0x17                      ; column 23
0041fd7c  call 0x61ee90
0041fd85  call 0xada2a7                      ; atoi -> edi
0041fd8d  push 0xc408d4                      ; "g_gametype"
0041fd94  call 0x6232c0                      ; Dvar_FindVar
0041fdc9  mov eax, 2                         ; compare 2 chars
0041fdce  mov edx, 0xc689ac                  ; "zm"
0041fdd3  call 0x6283d0
0041fddb  test eax, eax
0041fddd  je 0x41fde7                        ; g_gametype starts with "zm" -> load row
0041fddf  test edi, edi
0041fde1  jne 0x4200b9                       ; otherwise skip a col23!=0 row
```

A skipped row still advances the destination pointer (`0x4200b9` is the shared
loop tail), so **row indices never shift**; a skipped row is simply left zeroed.

### 4.2 The shipped table (MEASURED, `tools/codol_stringtable_dump.py code_post_gfx_mp mp/coknifestatstable.csv`, 21 × 24)

| `ps+0x338` | name | col4 dmg | col10 rate | col15 world | col16 view | col21 melee xanim | col23 zm |
|---|---|---|---|---|---|---|---|
| 1 | mel_prison | 30 | 1.4 | t5_weapon_prison_knife | t5_weapon_prison_knife | viewmodel_knife_melee_slice | 0 |
| 2 | mel_knife | 120 | 1 | | | viewmodel_knife_melee_slice | 0 |
| 3 | mel_sog | 60 | 0.9 | t5_knife_sog | t5_weapon_sog_knife_viewmodel | viewmodel_knife_melee_slice | 0 |
| 4 | mel_karambit | 80 | 0.8 | t5_knife_karambit_world | t5_knife_karambit | viewmodel_knife_melee_slice | 0 |
| 5 | mel_bowie | 150 | 0.6 | world_knife_bowie | viewmodel_knife_bowie | viewmodel_knife_melee_slice | 0 |
| 6 | mel_hatchet | 150 | 0.3 | t5_weapon_hatchet | t5_weapon_hatchet_viewmodel | viewmodel_knife_melee_slice | 0 |
| 7 | mel_shovel | 40 | 1 | tool_shovel | tool_shovel | player_blunt_melee_attack | 0 |
| 8 | mel_cleaver | 100 | 1 | static_berlin_knives_cleaver | … | player_blade_melee_attack | 0 |
| 9 | mel_bonesaw | 80 | 1 | p_jun_surgical_bonesaw | … | player_blade_melee_attack | 0 |
| 10 | mel_axe | 150 | 1 | com_hatchet | com_hatchet | player_chopping_melee_attack | 0 |
| 11 | mel_hammer | 60 | 1 | p_int_surgical_hammer | … | player_blunt_melee_attack | 0 |
| 12 | mel_hook | 70 | 1 | p_jun_metal_hook | … | player_chopping_melee_attack | 0 |
| **13** | **zknife_standard** | **150** | 1 | | | **viewmodel_knife_melee_slice** | **1** |
| **14** | **zknife_bowie** | **1000** | 0.6 | world_knife_bowie | viewmodel_knife_bowie | **viewmodel_knife_melee_slice** | **1** |
| **15** | **zknife_bowie (sickle)** | **1000** | 0.6 | p_jun_metal_hook | p_jun_metal_hook | **viewmodel_knife_melee_slice** | **1** |
| **16** | **zknife_halberd** | **1000** | 1 | codo_lubu_polearm_temp | codo_lubu_polearm_temp | **player_lubu_polearm_attack** | **1** |
| 17 | coop_mel_knife | 1000 | 1 | | | viewmodel_knife_melee_slice | 0 |
| 18 | coop_mel_karambit | 1000 | 0.8 | t5_knife_karambit_world | t5_knife_karambit | viewmodel_knife_melee_slice | 0 |
| 19 | coop_mel_bonesaw | 1000 | 1 | p_jun_surgical_bonesaw | … | player_blade_melee_attack | 0 |
| 20 | coop_mel_sog | 1000 | 0.9 | t5_knife_sog | t5_weapon_sog_knife_viewmodel | viewmodel_knife_melee_slice | 0 |
| 21 | coop_mel_bowie | 1000 | 0.6 | world_knife_bowie | viewmodel_knife_bowie | viewmodel_knife_melee_slice | 0 |

Column 22 (melee charge xanim) is empty on every shipped row, so anim index 8
keeps the def's own name.

This is the CoDOL form of the WaW/BO1 "carried knife, upgraded by the Bowie
purchase": `zknife_standard` → `zknife_bowie`. It is a **row swap**, not a
weapon swap; the melee model, animation, damage, range, rate and sounds all
come from the row. `viewmodel_knife_melee_slice` is already mounted in both
`common_gametype_zm` and `patch_common_gametype_zm`, so **no `_mp` asset is
involved anywhere in this path**.

### 4.3 Name → row index, and the script setter that writes `ps+0x338`

`BG_GetKnifeRowForName` at `0x4200e0` — linear strcmp against column 0,
returning the **1-based** index:

```
004200e4  mov ebx, dword ptr [0x1536be4]
004200f2  mov edi, 0x150e210
004200f7  mov ecx, dword ptr [edi]           ; row->name
00420100..00420122                            ; inline strcmp
0042012a  add edi, 0x5c
00420133  xor eax, eax                       ; not found -> 0
00420139  lea eax, [esi + 1]                 ; found  -> index + 1
```

The only writer of `ps+0x338` in the whole image (`0x516ecf`):

```
00516e47  mov eax, dword ptr [ebp + 8]       ; script entity id
00516e59  imul esi, esi, 0x2cc               ; gentity stride
00516e5f  add esi, 0x220cfb0                 ; g_entities
00516ec4  call 0x5169b0                      ; resolve the name argument
00516ec9  mov edx, dword ptr [esi + 0x17c]   ; ent->client / playerState
00516ecf  mov dword ptr [edx + 0x338], eax
```

with the resolver at `0x5169b0`:

```
005169b3  call 0x5cded0                      ; Scr_GetString(0)
005169c0  mov edx, 0xc30704                  ; "none"
005169c5  call 0x6283d0                      ; == "none" -> 0, i.e. bare hands
005169d5  call 0x4200e0                      ; else name -> row index
005169fd  push 0xc55748                      ; 'Unknown weapon name "%s": script may
                                             ;  need to call PreCacheItem("%s")...'
00516a12  call 0x5cec10                      ; script error
```

This is a **GSC field/method on the player**. Its name is stripped in the
builtin table (`0xc3bce0 -> {0x516e40, 0, ""}`; every name slot in that table
points at the pooled empty string `0xc2fead`), but the UI side keeps the key:
`meleeWpn` at `0xc5fe5c` (in the loadout key table at `0xcd2348`, next to
`lethal`/`special`/`tactical`) and `loadoutMeleeWpn` at `0xc77dec` (class-table
row key at `0xccd1d8`). Our own `bin/home/main/mp/botclasstable.csv:30` already
carries `loadoutMeleeWpn,mel_knife,…`, and
`bin/home/codol_rawfiles/coop/maps/mp/gametypes/_coopmode.gsc:199` already does
`weaponFromRow("loadoutMeleeWpn", "coop_mel_knife", "coop_mel_karambit")`.

`ps+0x338` never appears in pmove, so it is **not predicted**: it is pure
server state that reaches the client only over the wire.

### 4.4 The wire

`playerStateFields` at `0xC38CA8` (244 entries of `{offset, bits, changeHint}`):

```
index  43  off 0x33c  bits 10   (ps->weapon)
index  57  off 0x328  bits 10   (offhand)
index 129  off 0x338  bits 32   *** the melee row ***
```

`src/codol/snapshot/codol_player_fields.inc:133` already lists
`{0x0338, 32, 0}`, so the transport exists. Nothing writes it.

`BG_PlayerStateToEntityState` at `0x40d144` also republishes it to other
clients:

```
0040d144  mov edx, dword ptr [eax + 0x338]
0040d14a  mov dword ptr [ecx + 0x64], edx    ; entityState+0x64
```

and `entityState+0x64` is entity netfield `{0x064, 32, 0}` in eType 0
(`src/codol/snapshot/codol_entity_fields.inc:55`). The three remote-player
consumers each re-run the same `(index-1)*0x5c + 0x150e210` row lookup on a
non-local copy of the index — `0x4dfdd9 mov eax, dword ptr [edi + 0x64]`
(melee damage), `0x448415 mov eax, dword ptr [edi + 0x64]` (melee reach) and
`0x4503d5 mov eax, dword ptr [edx + 0xaec]` (world knife model, INFERRED to be
the same value carried in a cg_entity rather than the entityState, since the
row-lookup and `+0xbf0` sequence is byte-identical).

---

## 5. Every server-controlled input to the melee path

| # | input | where C1 reads it | our state |
|---|---|---|---|
| 1 | **`ps+0x338` melee row index** (netfield **129**, 32 bits) | `0x41bd43`, `0x415c89`, `0x47ae2e`, `0x47c5e0`, `0x480956`, `0x40d144`, `0x420147`, `0x516f6a` | **NEVER WRITTEN — always 0. ROOT CAUSE.** |
| 2 | **`entityState+0x64`** (eType 0 netfield, from `ps+0x338`) | `0x4503d5`, `0x448415`, `0x4dfdd9` | never written (other players get no knife model / def damage) |
| 3 | **dvar `g_gametype` must begin with `zm`** or rows 13–16 are skipped | `0x41fd8d`..`0x41fde1`; client re-syncs it from serverinfo at `0x465ed0`..`0x465f03`, and the serverinfo copy lands in `cgs+0x20` at `0x465bd6` | we send `\g_gametype\<sv_g_gametype>` in CS 0 (`codol_sv_state.c:115`) and the zm launch path sets `g_gametype zm` — **satisfied, but it is a hard prerequisite: re-verify per match** |
| 4 | `def+0x590` `iMeleeDamage != 0` gates the melee entirely | `0041c0f7 cmp dword ptr [ecx + 0x590], 0 / je` | we ship 25 — OK |
| 5 | `def+0xbf0` "weapon owns its melee anims" byte | `0x41bd7e`, `0x47ae18`, `0x47c0e5`, `0x4503cc`, `0x4dfdfc`, `0x573ac0`, `0x415cbb` | shipped data: **0** on every ordinary gun (`coltanaconda_zm`, `m14ebr_zm`, `famas_zm`, `p90_zm`, `spas12_zm` all `00` at `+0xbf0`), **1** on `knife_ballistic_zm`. So the override path is live for exactly the weapons that need it |
| 6 | usercmd melee button (`buttons & 4`) and the "second hand is busy" check | `0041c10e mov eax, [edx+8] / test al, 4`; `0041c119 test byte ptr [edx+0x30], 4`; the weaponstate scan `0041c14e`..`0041c16d` rejects states 8,9,10,11,12 and 1..5 | implemented (`_bg_weapons.asm:6985-7012`, `CODOL_WeaponStateSecondHandBlocksMelee`) |
| 7 | `ps->weapAnim` `+0x268` = 8 / 9 (netfield 9, 11 bits) | `0x4180b0`, `0x47cce0`, jump table `0x47be58` | produced by pmove on both sides — OK |
| 8 | `ps->weaponTime` `+0x26c`, `weaponDelay` `+0x270` | `0x41bed8`, `0x41bede` | produced — but computed from the **def**, because we have no row |
| 9 | `ps+0x4a8` melee-charge counter, `ps+0x4a4`, `pm_flags & 0x10000` | `0x415c4e`..`0x415d28`, `0x41bd87`, `0x41bd90` | ported |
| 10 | `ps+0x344 & 2` (offhand selects the viewmodel weapon) | `0x47b7c4`, `0x47c5b7`, `0x48092f` | produced |
| 11 | `ps+0x35c` dual wield, `ps+4` pm_type < 8 | `0x4180b0`, `0x421e76` | produced |
| 12 | melee events 47 `EV_MELEE_SWIPE`, 48 `EV_FIRE_MELEE`, 52 `EV_MELEE_HIT`, 53 `EV_MELEE_MISS`, 54 `EV_MELEE_BLOOD` (table `0xCD81D8`) | — | correct in `codol_event_map.inc:51-62` |
| 13 | configstrings publishing the weapon list | — | zm window publishes 131/131 — not implicated |

**Answer to "does melee use a separate weapon index?" — No.** There is no
melee weapon class (`0xcd7f28` = rifle, sniper, mg, smg, spread, pistol,
grenade, rocketlauncher, turret, throwingknife, non-player, item, primary,
offhand, item, altmode — no melee entry), and no code path resolves the melee
animation from a second `bg_weaponDefs[]` entry: `0x47c1d0`, `0x47b7df` and
`0x41bd3c` all index the def with the held/offhand weapon index. T5's
`playerState_s::meleeWeapon`-by-`WEAPCLASS_MELEE` mechanism does **not** exist
in C1. **C1's equivalent melee slot is `ps+0x338`, a row index into
`mp/coKnifeStatsTable.csv`.** The carried-knife model, animation, damage and
sounds all hang off that row, which is why the zm assets `zombie_melee`,
`hatchet_zm`, `revive_knife_zm`, `knife_ballistic_zm` exist as *weapons* for the
ballistic-knife / revive-tool cases while ordinary melee stays a row.

---

## 6. Why the 15-works / 39-silent split is exactly this bug

With `ps+0x338 == 0`, `0x47c1db xor ebx, ebx` gives `0x47c090` a NULL row, so
the `edi == 7` override at `0x47c0f7` is skipped for **every** weapon, and the
melee slot registers whatever `def->szXAnims[7]` holds:

* slot 7 populated (15 zm weapons; `p90_zm`, `spas12_zm`, `m1911_zm`, …):
  registers the weapon's own melee xanim → **melee animates**;
* slot 7 = pooled empty `0x3007f4b7` (39 zm weapons; `coltanaconda_zm`,
  `m14ebr_zm`, `famas_zm`, `ak104_zm`, …): `0x47c0df mov ecx, [ecx+4]`
  registers **`szXAnims[1]`, the idle animation** → **melee plays nothing
  visible**. Exactly the two weapons the user named.

MP looks healthy for the same reason in reverse: every held MP gun ships a
populated slot 7 (`coltanaconda_mp` = `0x300f55bc`), so the missing row is
invisible there. It is not invisible in damage: with no row, MP melee also uses
`def+0x590` = 25 instead of `mel_knife`'s 120, and zm melee uses 25 instead of
`zknife_standard`'s 150 — the zombie knife should be a one-hit kill in the early
rounds and on our server it is not. That is an independent, cheap live
confirmation of this diagnosis.

The previous conclusion in `docs/CODOL_MELEE_ANIM_20260920.md` — "the shipped zm
data has a gap, the server cannot fix it, emit a patch zone" — is **refuted**.
The data is complete; the zm weapons deliberately leave slot 7 empty *because
the knife row supplies it*, which is also why the empty-slot pattern is
systematic in zm and absent in mp. No patch zone, no `_mp` asset and no
composed weapon name is required.

---

## 7. The fix this implies

Server-side only, zm assets only:

1. **Write `ps+0x338`.** Add the melee row to our playerstate producer
   (`src/codol/snapshot/codol_engine_state.c`, alongside the
   `put(&out,0x33c,weapon)` / `0x340` / `0x328` line at :456) and resolve the
   row index from a name exactly as `0x4200e0` does — by linear match on column
   0 of `mp/coKnifeStatsTable.csv`, 1-based, 0 = "none"/bare hands. The table is
   client data; the server only needs the name→index mapping, which is fixed by
   the shipped CSV (§4.2) and should be read from our own copy of that table
   rather than hardcoded.
2. **Set it per category**: zm spawn → `zknife_standard` (13), Bowie purchase →
   `zknife_bowie` (14), sickle (15), halberd (16); mp/coop → the class's
   `loadoutMeleeWpn`, which `codol_script_profile_loadout.c` already parses into
   `loadout.melee` and currently drops on the floor.
3. **Expose the GSC setter** that C1's `0x516e40` implements, so
   `_zombiemode_weapons.gsc` can do the Bowie upgrade as a row swap the way the
   vanilla scripts do.
4. **Mirror it to `entityState+0x64`** (eType 0 netfield `{0x064,32,0}`) in the
   entity producer so other players' knife model and melee damage are right.
5. **Keep `g_gametype` starting with `zm` for zm matches** — without it C1 never
   loads rows 13–16 at all (`0x41fddf test edi, edi / jne`), and any row index
   13–16 we send then points at a zeroed row (`0x47c1f1` yields a row whose
   `+0x3c` is NULL → no override, and whose `+0x00` is NULL, which would also
   make `0x4200e0` dereference NULL if the client ever looked the name up).

Falsifiable prediction: set `ps+0x338 = 13` for every zm player and **all 54**
zm weapons gain the melee animation (`viewmodel_knife_melee_slice`) and 150
melee damage, including `coltanaconda_zm` and `m14ebr_zm`, with no change to any
weapon definition, fastfile or configstring.

---

## 8. Nothing in this path is in `.tvm0`

Every address cited is in `.text` (`0x401000`–`0x1147000`). The Themida
`.tvm0` section at `0x82F8000` was not needed; the only call into it on any
nearby path is `0x8308dbd` (a logging helper) at `0x47c166` / `0x47c1a2`, which
is diagnostics, not behaviour.
