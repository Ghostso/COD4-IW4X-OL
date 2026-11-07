# The 128-weapon ceiling: what it actually is, and what widening costs

2026-09-15. Status discipline: **WRITTEN** / **BUILT-TESTED** / **LIVE**.

## The symptom

Every bot class degrades to a stock gun:

```
Warning: CoDOL bot class 5 primary weapon: the retained 128-slot weapon table is full; falling back to cheytac_mp
```

## Where the 128 goes — MEASURED LIVE

`report_weapon_budget()` (`src/codol/weapon/codol_sv_weapons.c`) categorises the
native table by name shape at map start and on every composed publish. Build
`98552F0E…`, PID 23396, `mp_rust`:

```
map start:        1/128 native definitions - 0 stock, 0 partner, 0 composed; 127 free
first composed: 112/128 - 110 stock, 0 partner, 1 composed;  16 free
second:         113/128 - 110 stock, 0 partner, 2 composed;  15 free
```

**110 of 128 are stock. Zero partner definitions.** Composed loadouts fight over
18 slots, and a 12-bot lobby needs ~18-22 (9 classes x primary+secondary) plus
the human's — so it runs out around the ninth bot, exactly the observed pattern.

This kills the cheap fix: there is no demand-side trim, because partners aren't
consuming anything. The stock set is `mp/coWeaponAttachmentTable.csv`
(`codol_sv_weapons.c` `CODOL_InitializeServerWeaponConfigstrings`).

## C1 is not the constraint

Measured in `C1.exe`, three ways agreeing:

- `bg_weaponDefs` @ **`0x0150D720`** is **700 pointers**: `BG_ClearWeaponDefs`
  `0x0041F570` does `memset(0x0150D720, 0, 0xAF0)`; the next live global sits at
  `0x0150E210` = base + 0xAF0 with no padding; CG_Init `0x00450ADC` walks
  1..699 (`cmp edi, 0x2bc`).
- **No 128 anywhere on C1's weapon path**: zero `cmp …,0x80` and zero
  `and …,0x7f` across `0x41E000`–`0x42C000`. `BG_GetWeaponDef` is inlined at 561
  sites with no bounds check at any of them, and `BG_RegisterWeaponDef`
  `0x0041F640` appends with no cap.
- The ceiling is **700, not 1024**: the playerstate weapon fields are 10 bits
  (0..1023), but `CS_WEAPONS` is a 700-slot window (5362..6061) and entity field
  `0x098` encodes `weapon + 700*modelIndex` (`0x0052FBC3`) — 700 is literally
  the modulus.

So the 128 is entirely ours, from the retained IW3 layout. IW4's own
`BG_MAX_WEAPONS` is far above 128.

## What actually binds: four 128-wide arrays in `playerState_t`

Measured with `offsetof` against the real struct:

```
ammo             0x15c   int[128]
ammoclip         0x35c   int[128]
weapons          0x55c   4 dwords = 128 bits   <- ownership
weaponold        0x56c   4 dwords = 128 bits
weaponrechamber  0x57c   4 dwords = 128 bits
weaponmodels     (byte[128])
sizeof(playerState_t) = 0x2f64, and gclient_t.sess sits at exactly 0x2f64
```

`BG_IsWeaponValid` does `ps->weapons[index>>5] & (1<<(index&31))` against
`ps+0x55c`. **Engine index 128 does not overflow the definition table — it
writes through `weapons[]` into `weaponold[]`.** Growing `bg_weaponDefs`
(`_bg_weapons.asm:9242`, `resb 0x204` = 129) on its own would convert today's
clean rejection into silent cross-field corruption, which is why that was not
done first.

### `ammo` / `ammoclip` stay at 128, behind a capacity gate (corrected 2026-09-28)

They are indexed by `def->iAmmoIndex` / `def->iClipIndex`
(`codol_weapon_reload.c:137-142`), a separate domain that weapons share by
name. The earlier "C1 pools ammo at 256 and magazines at 512" was wrong:
C1's BG_ClearWeaponDefs (`0x41F570`) clears four 700-pointer tables
(defs `0x0150D720`, clips `0x015106F8`, shared caps `0x0150CC30`, ammo
`0x0150FC08`), so C1 can never overflow a pool, and it keeps player ammo per
weapon slot rather than per pool index. The server's pools are 128 each with
unchecked appends; entry 128 overwrote the next pool's counter. Stock MP maps
use about 105. `CODOL_AdmitWeaponPools` now refuses a definition that would
need a 129th entry (BG_GetWeaponIndexForName returns 0), and a rolled-back
publish restores the pool counts. Widening to C1's 700 means moving
ps ammo/ammoclip into the playerState extension (113+ retained asm sites),
like the weapon bitsets; deferred.

### `playerState_t` cannot change size — MEASURED

**521 retained-assembly sites reference `gclient_t` offsets at or above `sess`
(0x2f64), across 110 distinct offsets** (`0x2f64` x21, `0x2f8c` x23, ...).
Appending the widened arrays to the end of `playerState_t` would shift every one
of them. A mechanical "add delta to constants in range" rewrite cannot
distinguish a gclient displacement from an unrelated immediate in the same
numeric range, so that route is not safe.

Therefore the widening has to happen **inside the existing 0x2f64 footprint**.

## The shape that works

`weapons[4]`, `weaponold[4]` and `weaponrechamber[4]` are contiguous at
0x55c/0x56c/0x57c — 48 bytes. Let the ownership bitset absorb all three:

- `weapons[12]` at 0x55c = **384 bits**, no `sizeof` change, no displacement
  change, every field from 0x58c on stays exactly where it is.
- `weaponold` and `weaponrechamber` move to a CoDOL-native side table, also 384
  bits each.

384 leaves ~274 free after the 110 stock — against a real need of ~25.

### The remaining cost, scoped

The asm sites that read those two bitsets must be redirected. Filtered to the
real ones (the raw grep over-counts: a `_dobj.asm` stack local at `ebp-0x57c`
and `_g_missile.asm` floats off another struct are not this array):

| array | offset | real asm sites |
|---|---|---|
| `weaponold` | 0x56c | 7 |
| `weaponrechamber` | 0x57c | ~11 (`_bg_weapons.asm`, `_g_weapon.asm`) |

They are uniform — each computes `edx = index>>5`, `eax = 1<<(index&31)` and
then does one of `test` / `and` / `or` on `[psreg + edx*4 + 0x57c]`:

```
mov edx, ecx
sar edx, 0x5
and ecx, 0x1f
mov eax, 0x1
shl eax, cl
or [edi+edx*4+0x57c], eax
```

A side table cannot be reached by a constant swap, because the asm holds `ps`
and not a client index, so each site needs either a call (clobbers the cdecl
caller-saved registers, which are live here) or a `ps->clientNum` load plus a
scaled base. That is per-site register analysis on pmove — 18 careful edits, and
a missed one is silent gameplay corruption rather than a crash.

`weaponmodels[128]` is a fourth per-weapon array and needs its own decision;
CoDOL publishes player models through clientState attachments, so it may be
unused here, but that is not yet established.

## What is in the current build

- `report_weapon_budget()` — the measurement above. **LIVE.**
- `CODOL_NATIVE_WEAPON_SLOTS` in `codol_sv_weapons.h`, the single place the
  number is written. `codol_bot_loadout.c:195` still carries its own identical
  `#define`; it must switch to the header when the widening lands or the
  widening half-applies.
- Registration rollback on a failed publish (`rollback_native_weapons`), so a
  rejected composed publish no longer leaves a registered-but-unpublished
  definition — the blanked `*a` shape CG_Init walks at `0x47d1d0`. **BUILT.**
- `ammo`/`ammoclip` left alone, per the finding above.

## Not done

The bitset absorption and the 18 asm redirects. Everything needed to do it is
above: the target layout, the exact site list, the uniform instruction shape and
the reason a constant swap is not sufficient.

---

# The 2026-09-15 crash, and the per-site register audit

## What happened

A 384-bit checkpoint of this widening went live at 21:37 and crashed every
instance immediately after the first player spawn (dumps at 21:43:17, 21:44:53,
21:46:25, 21:47:48 — one per relaunch). Rolled back to `2035702B`.

## Why: `[A+B+disp]` does not say which register is the base

x86 addressing treats the two registers in `[A+B+disp]` symmetrically; the
assembler picks base and index. The generated transform assumed the **first**
register held the playerState. At `BG_PlayerStateToEntityState`
(`_bg_misc.asm:2301`) it is the **second**:

```
2300   mov eax, [ebx+0xe8]              ; eax = ps->weapon  (scalar index)
2301   movzx eax, byte [eax+ebx+0x81c]  ; ebx is the playerState
```

so the rewritten sequence loaded `clientNum` from `[ps->weapon + 0xdc]`, and with
`ps.weapon == 0` at spawn that is `[0x000000DC]` — an unconditional NULL
dereference on every spawn.

## The audit

Only the six sites with `*4` scaling are provable from syntax (the scaled
register is the index). The other 19 were determined by backtracking each
register to its nearest preceding write. The tally is the point:

**9 of the 19 ambiguous sites were wrong in the generated transform — 47%.**
The transform was a coin flip, and patching it site-by-site rather than
reverting would have shipped roughly nine latent memory-corruption bugs.

| site | expression | ps reg | evidence (nearest write) | transform was |
|---|---|---|---|---|
| `_bg_misc.asm:2301` | `[eax+ebx+0x81c]` | **ebx** | `:2253 mov ebx,[ebp+0x8]` (arg1); `:2300 eax=[ebx+0xe8]` | **WRONG** |
| `_bg_weapons.asm:1007` | `[ebx+edx+0x57c]` | ebx | `:1003 lea edx,[eax*4]` → edx is index | correct |
| `_bg_weapons.asm:1018` | `[ebx+edx+0x57c]` | ebx | `:1003 lea edx,[eax*4]` | correct |
| `_bg_weapons.asm:7088` | `[edi+ebx+0x57c]` | edi | `:7084 lea ebx,[eax*4]`; edi untouched arg | correct |
| `_bg_weapons.asm:7836` | `[ebx+eax+0x56c]` | ebx | `:7831 shl eax,0x2` → eax is index | correct |
| `_bg_weapons.asm:7838` | `[ebx+eax+0x56c]` | ebx | `:7831 shl eax,0x2` | correct |
| `_bg_weapons.asm:8596` | `[edi+ebx+0x57c]` | edi | same function as `:8057`, whose scaled form proves edi=ps | correct |
| `_g_client_script_cmd_mp.asm:1032` | `[ebx+eax+0x81c]` | **eax** | `:1031 mov eax,[edi+0x15c]` = `ent->client` | **WRONG** |
| `_g_client_script_cmd_mp.asm:5553` | `[esi+edx+0x81c]` | **edx** | `:5546 mov edx,[edi+0x15c]` = `ent->client` | **WRONG** |
| `_g_client_script_cmd_mp.asm:5624` | `[ebx+esi+0x81c]` | **esi** | `:5608 mov esi,[edi+0x15c]`; `:5615 test [esi+edx*4+0x55c]` proves esi=ps | **WRONG** |
| `_g_cmds_mp.asm:249` | `[edx+eax+0x81c]` | **UNRESOLVED** | reached by jump to `Cmd_Give_f_100`; needs jump-source trace | unknown |
| `_g_combat_mp.asm:183` | `[ebx+edx+0x81c]` | **edx** | `:179 mov edx,[ecx+0x15c]` = `ent->client` | **WRONG** |
| `_g_combat_mp.asm:393` | `[esi+eax+0x81c]` | **eax** | `:392 mov eax,[ecx+0x15c]` = `ent->client` | **WRONG** |
| `_g_items.asm:877` | `[esi+edi+0x81c]` | esi | `:853 add edi,0x1` → edi is a loop counter | correct |
| `_g_weapon.asm:782` | `[edx+eax+0x81c]` | **eax** | `:779 mov eax,[ebx+0x15c]` = `ent->client` | **WRONG** |
| `_g_weapon.asm:1015` | `lea ecx,[ecx+eax+0x57c]` | ecx | `:1014 mov ecx,[ebp+0x8]`; `:1012 lea eax,[esi*4]` | correct |
| `_g_weapon.asm:1021` | `[ebx+eax+0x56c]` | ebx | `:1020 mov ebx,[ebp+0x8]`; `:1012 lea eax,[esi*4]` | correct |
| `_g_weapon.asm:1023` | `[edi+ebx+0x81c]` | **ebx** | `:1020 mov ebx,[ebp+0x8]` (arg1) | **WRONG** |
| `_g_weapon.asm:1099` | `[edx+edi+0x81c]` | **edi** | `:1098 mov edi,[ebp+0x8]` (arg1) | **WRONG** |

The reliable signals, for whoever checks this: the **index** register is the one
built by `lea r,[x*4]`, `shl r,2`, `sar r,5` or a loop `add r,1`; the
**playerState** register comes from `[ebp+0x8]` (argument one), from
`[ent+0x15c]` (`gentity->client`, whose first member is the playerState), or is
an untouched argument. A sibling access in the same function using the
unambiguous `*4` form settles any remaining doubt.

## Consequence for the plan

Porting the five small self-contained functions removes **8** of the 25 sites,
and **6 of those 8 are ones the transform got wrong** — `dropItem` (1032),
`giveMaxAmmo` (5553), `giveStartAmmo` (5624), `G_UseOffHand` (782) and
`G_GivePlayerWeapon` (1023, 1099). So the port is not a side quest; it deletes
the densest cluster of errors outright.

`Cmd_Give_f:249` is the one site local backtracking cannot settle, because
control reaches `Cmd_Give_f_100` by jump. It needs either a jump-source trace or
the same port treatment.

---

# 2026-09-15 22:40 - resolved site table, second 128 domain, step-0 numbers, C ports

Status discipline: **WRITTEN** / **BUILT-TESTED** / **LIVE**. This section is the
weapon-ceiling worker's handoff; the widening design itself (700-wide arrays in
the storage-keyed `codol_ps_ext_t`, `codol_weapon_bits.inc` macros) is owned
and documented by the agent implementing it.

## Step 0: the deployed `2035702B` binary after the killstreak fix

Boot 1 died before map load: `script compile error: unknown function
(maps/mp/_dogs.gsc line 1661)` - `dog setFlashBanged(true, 500)` is not a
registered builtin, and the `_killstreaks.gsc` dogs hook made it reachable.
The two hook lines (`thread maps\mp\_dogs::init()` and
`level.killStreakFuncs["dogs_mp"]`) were commented out with a `DISABLED
2026-09-15` marker and the root re-collated. Boot 2 (PID 6648) loaded `mp_rust`:

| measure | before (21:49 log) | step 0 |
|---|---|---|
| `killstreak_pro_` lookups | 34 | **0** |
| budget line | `122/128 - 113 stock, 0 partner, 8 composed; 6 free` | `112/128 - 97 stock, 0 partner, 14 composed; 16 free` |
| "table is full; falling back" | present | 0 at 14 composed (ceiling still real: 16 free) |

**LIVE** (measured), no crash dumps in `bin/`.

## The resolved 25-site table

ps = the register holding the playerState, idx = the register holding the
scaled or unscaled weapon index. Evidence is the nearest preceding write.
Only the `*4` rows are provable from syntax; the rest were backtracked by hand.

| site | instruction | ps | idx | evidence |
|---|---|---|---|---|
| `_bg_misc.asm:2301` | `movzx eax, byte [eax+ebx+0x81c]` | ebx | eax | `:2253 mov ebx,[ebp+0x8]`; `:2300 mov eax,[ebx+0xe8]`; next insn `mov [edi+0xc8],eax` (no flag consumer) |
| `_bg_weapons.asm:1007` | `test [ebx+edx+0x57c], eax` | ebx | edx | `:1003 lea edx,[eax*4]`; ebx = regparm arg (`:995 mov ebx,eax`) |
| `_bg_weapons.asm:1018` | `and [ebx+edx+0x57c], eax` | ebx | edx | same function |
| `_bg_weapons.asm:1163` | `test [ebx+edx*4+0x57c], eax` | ebx | edx | scaled |
| `_bg_weapons.asm:1351` | `test [ebx+edx*4+0x57c], eax` | ebx | edx | scaled |
| `_bg_weapons.asm:7088` | `test [edi+ebx+0x57c], eax` | edi | ebx | `:7084 lea ebx,[eax*4]`; the `%ifdef CODOL_SERVER jz` right after it consumes ZF |
| `_bg_weapons.asm:7457` | `and [ebx+edx*4+0x57c], eax` | ebx | edx | scaled; mask is `rol 0xfffffffe, cl` |
| `_bg_weapons.asm:7640` | `and [ebx+edx*4+0x57c], eax` | ebx | edx | scaled |
| `_bg_weapons.asm:7836` | `test [ebx+eax+0x56c], edx` | ebx | eax | `:7831 shl eax,2`; **`:7837 setz cl` consumes ZF of this test** |
| `_bg_weapons.asm:7838` | `or [ebx+eax+0x56c], edx` | ebx | eax | same |
| `_bg_weapons.asm:8057` | `or [edi+edx*4+0x57c], eax` | edi | edx | scaled |
| `_bg_weapons.asm:8596` | `and [edi+ebx+0x57c], eax` | edi | ebx | same PM_Weapon frame as :7088/:8057 |
| `_bg_weapons.asm:8940` | `and [edi+edx*4+0x57c], eax` | edi | edx | scaled |
| `_g_client_script_cmd_mp.asm:958` | `add ebx,0x56c` then `or [ebx+edx*4], eax` | ebx | edx | `:957 mov ebx,[ebx+0x15c]`; PlayerCmd_setSpawnWeapon |
| `_g_client_script_cmd_mp.asm:1032` | `movzx eax, byte [ebx+eax+0x81c]` | eax | ebx | `:1031 mov eax,[edi+0x15c]`; dropItem |
| `_g_client_script_cmd_mp.asm:5553` | `movzx eax, byte [esi+edx+0x81c]` | edx | esi | `:5546 mov edx,[edi+0x15c]`; giveMaxAmmo |
| `_g_client_script_cmd_mp.asm:5624` | `movzx ecx, byte [ebx+esi+0x81c]` | esi | ebx | `:5608 mov esi,[edi+0x15c]`, `:5615 test [esi+edx*4+0x55c]`; result lands in **ecx** (the `cl` model arg of regparm `G_InitializeAmmo`) |
| `_g_cmds_mp.asm:249` | `movzx eax, byte [edx+eax+0x81c]` | **eax** | **edx** | **resolved**: the only jump source is `:112 jnz Cmd_Give_f_100`, after `:109 mov ecx,[ebp+0x8]` (ent), `:110 mov eax,[ecx+0x15c]` (ps), `:111 mov edx,[eax+0xe8]` (ps->weapon). ecx=ent and edx=weapon are both consumed after the site (`[esp+0x4]=edx`, `[esp]=ecx`) |
| `_g_combat_mp.asm:183` | `movzx eax, byte [ebx+edx+0x81c]` | edx | ebx | `:179 mov edx,[ecx+0x15c]`; ecx=ent live after |
| `_g_combat_mp.asm:393` | `movzx eax, byte [esi+eax+0x81c]` | eax | esi | `:392 mov eax,[ecx+0x15c]`; ecx=ent live after |
| `_g_items.asm:877` | `movzx eax, byte [esi+edi+0x81c]` | esi | edi | `:853 add edi,0x1` loop counter; Touch_Item |
| `_g_weapon.asm:782` | `movzx eax, byte [edx+eax+0x81c]` | eax | edx | `:779 mov eax,[ebx+0x15c]`, `:780 mov edx,[eax+0xe0]`; G_UseOffHand |
| `_g_weapon.asm:1015` | `lea ecx, [ecx+eax+0x57c]` | ecx | eax | `:1014 mov ecx,[ebp+0x8]`, `:1012 lea eax,[esi*4]`; pointer saved in `[ebp-0x1c]` and dereferenced again at `:1096 and [eax],esi` for the **alternate** weapon (IW3 quirk: re-clears the original weapon's word/mask, not the alternate's) |
| `_g_weapon.asm:1021` | `and [ebx+eax+0x56c], esi` | ebx | eax | `:1020 mov ebx,[ebp+0x8]` |
| `_g_weapon.asm:1023` | `mov [edi+ebx+0x81c], al` | ebx | edi | write; edi = weapon arg |
| `_g_weapon.asm:1099` | `mov [edx+edi+0x81c], cl` | edi | edx | `:1098 mov edi,[ebp+0x8]`; write for the alternate |

Also in G_GivePlayerWeapon: `:1010-1012 add ecx,0x55c; mov [ebp-0x20],ecx`
saves a base+0x55c pointer that `:1093 or [edi+eax*4],ecx` (edi=[ebp-0x20])
uses for the alternate's ownership bit - a saved pointer, not a direct site.
BG_TakePlayerWeapon (`_bg_weapons.asm:2261 add edi,0x55c`) carries the same
saved-pointer shape (the widening owner found it).

### Raw-grep hits that are NOT this domain

- `_g_weapon.asm:1223`, `:1561` `cvtsi2ss xmm0, dword [reg+0x56c]` - WeaponDef+0x56c
  (`projectileSpeedUp`; the next instruction reads +0x570).
- `_g_missile.asm:2142/2240/2311/2326/3208` `[reg+0x57c]` floats - WeaponDef+0x57c
  (`timeToAccelerate`).
- `_g_combat_mp.asm:564` `movss xmm0, [eax+edx*4+0x81c]` - WeaponDef location
  damage multipliers (+0x81c is `locNone`).
- `_dobj.asm` `[ebp-0x57c]` - a stack local.

## The second 128 domain: the item table

`bg_itemlist` (`_bg_misctables.asm`) is 0x2000 bytes = 2048 four-byte entries =
**128 weapons x 16 models**; `itemRegistered` is 128 x 16 dwords
(`SaveRegisteredItems` `_g_items.asm:1863-1890` walks `ebx < 0x80` in 16 strides
of 0x200); `BG_ClearWeaponDef` zeroes `bg_itemlist+4..0x1ffc`. Everywhere,
`item = weapon + 128*model`:

- `Drop_Weapon` `_g_items.asm:1084-1088`: `movzx eax,bl; shl eax,7; lea eax,[edi+eax];
  lea esi,[bg_itemlist+eax*4]` - unbounded.
- The signed mod-128 idiom `sub r,1; or r,0xffffff80; add r,1` at `_g_items.asm`
  :313 (WeaponPickup_LeechFromWeaponEnt), :548 and :773 (Touch_Item), :852
  (Touch_Item_250), :1465 (G_SpawnItem), :1853 (G_GetItemClassname), :2507 and
  :2521 (Drop_Item); `_bg_misc.asm:1310`, `:3049`; `_g_cmds_mp.asm:305`.
- C: `codol_script_player_builtins.c:661` `weaponmodels[weapon & 127]` and
  `bg_itemlist + 4*((weapon & 127) + 128*model)` (scavenger bag).

A native weapon index >= 128 dropped through any of these **aliases another
weapon's item** (weapon 200 becomes item 200 = weapon 72, model 1). Either the
item domain is widened with the weapon domain (table 0x2000 -> 700x16x4, the
eleven mod-128 sites, `SaveRegisteredItems`, and the CS_ITEMS window), or
`Drop_Weapon` refuses `[ebp+0xc] >= 0x80` (return NULL, like a failed drop) and
the scavenger path errors instead of masking. **Not done; recorded for the
widening owner.**

## The five function ports - **BUILT** (object compiles), not linked, not live

`src/codol/weapon/codol_weapon_give.c` / `.h` define, on the 700-wide
`CODOL_WeaponBits*` API (`codol_weapon_bits.h`), never the ps arrays:

| C function | retained original | asm body |
|---|---|---|
| `CODOL_GivePlayerWeapon(ps, weapon, model)` | `G_GivePlayerWeapon` | `_g_weapon.asm:944-1136` |
| `CODOL_UseOffHand(ent)` | `G_UseOffHand` | `_g_weapon.asm:740-794` |
| `CODOL_PlayerCmd_dropItem(ref)` | `PlayerCmd_dropItem` | `_g_client_script_cmd_mp.asm:991-1080` |
| `CODOL_PlayerCmd_giveMaxAmmo(ref)` | `PlayerCmd_giveMaxAmmo` | `_g_client_script_cmd_mp.asm:5492-5577` |
| `CODOL_PlayerCmd_giveStartAmmo(ref)` | `PlayerCmd_giveStartAmmo` | `_g_client_script_cmd_mp.asm:5578-5648` |

Names are distinct from the retained symbols so both link side by side until
the asm owner retargets. Compiled with the tree's flags
(`gcc -c -m32 -msse2 -mfpmath=sse -Wall ... -DCODOL_SERVER -std=gnu11`) to
`obj/codol/codol_weapon_give.o` with no warnings; `nm` shows the five `T`
symbols and only expected `U` externs (`Add_Ammo`, `Drop_Weapon`, `Drop_Item`,
`G_FindItem`, `G_InitializeAmmo` (regparm(3): eax=ent, edx=weapon, cl=model,
4th on stack), `Weapon_Throw_Grenade`, `BG_GetAmmoPlayerMax`,
`Scr_GetConstLowercaseString`, `GScr_AddEntity`, the `CODOL_WeaponBits*`
accessors, `CODOL_WeaponStateOffhandGranted`).

Behaviour (from the asm, cross-checked with the widening owner's reading):
G_GivePlayerWeapon rejects an owned weapon (0); weapClass 7/8 skip the
`gunXModel[model]` existence check, all others need it; the grant sets
owned, clears rechamber and old, stores the model; weapClass 9 or any
`offhandClass != 0` then returns 1 (the IW3 offHandIndex arm is dead under
`CODOL_SERVER`, `:1031 jmp G_GivePlayerWeapon_30`, and the port never touches
`offHandIndex`); otherwise the `altWeaponIndex` (+0x540) chain is walked and
every alternate not already owned is granted with the same model. Quirk
decision (agreed): the port clears the alternate's own rechamber/old bits
where the asm re-cleared the original's. The CODOL hook after a grant is
`CODOL_WeaponStateOffhandGranted(ps, weapon)` (`_g_weapon.asm:985`).
G_UseOffHand builds angles from `client->fGunPitch/fGunYaw` (gclient+0x30a4/
+0x30a8) and `ps->viewangles[2]`, `AngleVectors` -> forward/right/up,
`G_GetPlayerViewOrigin` -> muzzleTrace, then `Weapon_Throw_Grenade(ent,
ps->offHandIndex, weaponmodels[offHandIndex], &parms)`. dropItem's default
fourth argument is `scr_const.tag_weapon_right` (scr_const+0xac).

### Anchored asm diffs to retarget the retained callers (for the asm owner)

Every caller stays untouched (`_g_cmds_mp.asm:148`, `_g_items.asm:843/864/931/2135`,
`src/g_cmds.c:264`, `_g_active_mp.asm:2403 jmp G_UseOffHand`,
`scr_vm_main.c:553/554/589 Scr_AddMethod`) - each retained body becomes a
cdecl tail-jump trampoline, which is argument-exact for stack-passed cdecl
(including the by-value `scr_entref_t`):

1. `src/asmsource/_g_weapon.asm` - from the line `G_GivePlayerWeapon:` (after
   `;G_GivePlayerWeapon(playerState_s*, int, unsigned char)`) up to but not
   including `;G_SelectWeaponIndex(int, int)`, replace the whole body with:
   ```
   G_GivePlayerWeapon:
   	extern CODOL_GivePlayerWeapon
   	jmp CODOL_GivePlayerWeapon

   ```
   Keep `global G_GivePlayerWeapon` (`:68`). The internal labels
   `G_GivePlayerWeapon_10..100`, `_CoDOLReturn` and the `extern
   CODOL_WeaponStateOffhandGranted` inside the body go with it.
2. `src/asmsource/_g_weapon.asm` - from `G_UseOffHand:` (after
   `;G_UseOffHand(gentity_s*)`) up to but not including
   `;LogAccuracyHit(gentity_s*, gentity_s*)`, replace with:
   ```
   G_UseOffHand:
   	extern CODOL_UseOffHand
   	jmp CODOL_UseOffHand

   ```
   Keep `global G_UseOffHand` (`:65`).
3. `src/asmsource/_g_client_script_cmd_mp.asm` - from `PlayerCmd_dropItem:` up
   to but not including `;PlayerCmd_finishPlayerDamage(scr_entref_t)`:
   ```
   PlayerCmd_dropItem:
   	extern CODOL_PlayerCmd_dropItem
   	jmp CODOL_PlayerCmd_dropItem

   ```
4. same file - from `PlayerCmd_giveMaxAmmo:` up to but not including
   `;PlayerCmd_giveStartAmmo(scr_entref_t)`:
   ```
   PlayerCmd_giveMaxAmmo:
   	extern CODOL_PlayerCmd_giveMaxAmmo
   	jmp CODOL_PlayerCmd_giveMaxAmmo

   ```
5. same file - from `PlayerCmd_giveStartAmmo:` up to but not including
   `;PlayerCmd_GetWeaponsList(scr_entref_t)`:
   ```
   PlayerCmd_giveStartAmmo:
   	extern CODOL_PlayerCmd_giveStartAmmo
   	jmp CODOL_PlayerCmd_giveStartAmmo

   ```
   Keep the three `global PlayerCmd_*` lines (`:122`, `:169`, `:170`).

Alternative to 3-5: register `CODOL_PlayerCmd_*` directly in
`src/scr_vm_main.c:553/554/589` and delete the asm bodies plus their globals.
Either way the eight 0x81c/0x57c/0x56c sites inside those bodies (`:782`,
`:1015`, `:1021`, `:1023`, `:1099`; `:1032`, `:5553`, `:5624`) disappear.

## A 384-bit in-struct layout was tried and withdrawn

For the record: `weapons[12]` at 0x55c absorbing 0x56c/0x57c, with
`weaponold[12]`/`weaponrechamber[12]` relocated into the unused
`weaponmodels[128]` bytes at 0x81c/0x84c (no other asm reference exists in
0x820..0x87c), makes the 13 bitset sites pure displacement swaps with no
register analysis. It was implemented in source and **reverted by hand** the
same evening, never built, because the user's requirement is 700 with no
128/384 residue anywhere; 0x55c..0x58b is 48 bytes and `proneDirection`
starts at 0x58c, so the in-struct route cannot reach 700. The tree carries
none of it.
