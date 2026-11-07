# m4a1techevent + FASTMAG: missing quick-reload animation (2026-09-21)

Status: measured, root cause established, server-side fix written and
built (objects only). No link, no binary promotion, no server restart, no
client asset change, no commit. Live verification is the parent's step.

## Root cause in one paragraph

The client plays the reload viewmodel animation from ITS OWN composed
WeaponDef, using the wire animation ID the playerstate carries. For a
dual-mag weapon C1 selects the quick branch (wire 14 / 16) from inventory
byte2 and def+0xbc7 alone and never looks at the animation names. Wire 14/16
resolve to name slots 10/12 (source +0xa4 / +0xac). In the shipped
`patch_common_gametype_mp.ff` (the winning zone) the base
`m4a1techevent_mp` has EMPTY strings in exactly those two slots, while its
sibling `m4a1tech_mp` was seeded with the normal reload names. The patched
`dualmags_m4tech` attachment writes those slots with `[r] reload
dualmag_reload_quick`-style REPLACE operators, and replacing text inside an
empty string yields an empty string. C1's viewmodel registrar treats an
empty slot as the idle animation (0x47c0df). So every quick reload of this
composed weapon shows idle: "the fast-mag reload plays nothing".

The server (same zone data, same operator semantics) ends up with the same
empty slots in its composed core, which is what makes the fix data-driven.

## Measurements

### The published weapon

Composed name published for this loadout (games_mp.log, qconsole.*.log,
>2000 occurrences):

    *a 27 13 227 0 16 0 31 0 153 0 34 0 106 0 52 0 69 0 23 0 33 0

base 27 = `m4a1techevent_mp`, camo 13 (tiger), item 153 = `mag_dualar15`
(-> attachment asset `dualmags_m4tech`). Live server weapon index 123.
Reload phases logged by the native producer (`codol_weapon_reload.c`
trace), e.g.

    CoDOL dualmag start-empty: client 12 weapon 123 quick 1 -> 1 state 7
        anim 14 expectedC1Anim 16 phaseQuick 1 time 2100 add 1150 clip 0

i.e. the server did select the quick phase and did publish wire 16 (and 14
for non-empty) with the quick durations 1800 / 2100 ms. Timing was right;
the client just had no name behind those IDs.

### Base definitions (type-28 blobs, `tools/codol_weapondef_zone_diff.py dump`)

patch_common_gametype_mp, `m4a1techevent_mp`, bank 0 slots 9..12
(+0xa0..+0xac):

    09c  3001001a 30090205 300080b1 30095066
    0ac  300080b1 300080b1 300080b1 3007d757

patch_common_gametype_mp, `m4a1tech_mp`:

    09c  3001001a 30090205 30090205 30095066
    0ac  30095066 300080b1 300080b1 3007d757

`0x30090205` = `viewmodel_m4a1tech_reload`, `0x30095066` =
`viewmodel_m4a1tech_reload_empty`, `0x300080b1` = the pooled empty string
(resolved live in CODOL_FASTMAG_EVENT_ASSET_20260911.md). Only +0xa4 and
+0xac differ between the two (plus the three inline-vs-shared name refs at
+0x008/+0x134/+0x138 which resolve to equal text; see the 2026-09-14
review). Reload durations are IDENTICAL in both and in the unpatched base:

    5c8  000007d9(2009) 000006d6(1750) 00000000 000008fb(2299)
    5d8  000007d0(2000) 00000546 00000000 00000546

so the normal dual-mag reload time (2009/2299) is the STOCK reload time;
only the quick variants (+0x5cc/+0x5d8, set to 1800/2100 by the attachment)
make the fast mag fast. Downgrading the phase itself would therefore be a
stock-timing degrade; the fix below keeps the quick timing.

### Attachment records (type-43, raw {offset,type,value} + inline text)

Read with the loader rule that only value `0xFFFFFFFF` consumes inline text
(the `attach` mode of the dump tool consumes text for every non-zero value
and mis-aligns).

common_gametype_mp `dualmags_m4tech` (11 entries, SET operators, inline):

    +0xbc7 type 6  (shared)             dualMag byte
    +0x574 type 4  (shared)  +0x55c type 4 (shared)
    +0x5cc type 9  (shared)  +0x5d8 type 9 (shared)
    +0x5e0 type 9  (shared)  +0x5e8 type 9 (shared)
    +0x0a0 type 0  'viewmodel_m4a1tech_dualmag_reload_normal'
    +0x0a4 type 0  'viewmodel_m4a1tech_dualmag_reload_quick'
    +0x0a8 type 0  'viewmodel_m4a1tech_dualmag_reload_normal_empty'
    +0x0ac type 0  'viewmodel_m4a1tech_dualmag_reload_quick_empty'

patch_common_gametype_mp `dualmags_m4tech` (11 entries, all shared refs):

    +0x0a0 type 0 3006791d   +0x0a4 type 0 3006793e
    +0x0a8 type 0 3006795e   +0x0ac type 0 3006798b

The ref spacing is 0x21 / 0x20 / 0x2d = strlen+1 of
`[r] reload dualmag_reload_normal` (33), `[r] reload dualmag_reload_quick`
(32), `[r] reload_empty dualmag_reload_normal_empty` (45), matching the
live-map read of the same entries in the 2026-09-11 audit. The patch turned
the SET operators into REPLACE operators and, to make replace work, seeded
`m4a1tech_mp`'s quick slots with the normal names; it did not seed the
event weapon. With the unpatched base zone alone the event weapon would
have worked. This is a shipped data inconsistency, not a server bug.

Server-side replace semantics: `codol_weapon_attachment.c`
`apply_text_operator('r', current="", ...)` produces "" (loop over an empty
`current`), stored via `store_name`, and the composed core's
`animations.names[]` are read from that post-override image
(`CODOL_LoadEngineWeaponCoreFromImage`), so slots 10/12 are "" server-side
as well.

### C1 disassembly (ImageBase 0x400000; all verified by direct disassembly)

Reload branch selection, `0x4192f0`:

    0041930a  movzx eax, byte ptr [eax + 2]     ; inventory byte2
    00419347  cmp byte ptr [esi + 0xbc7], 0     ; def dualMag
    0041934e  je   0x41937e                     ; -> normal branch
    00419350  cmp dword ptr [ebp - 4], 0        ; byte2
    00419354  je   0x41937e
    00419356  push 0x10 ; call 0x418080         ; quick-empty  = wire 16, time +0x5d8
    004193e3  push 0xe  ; call 0x418080         ; quick        = wire 14, time +0x5cc
    0041939e  or edx, 0xf  ... [esi+0x5d4]      ; normal-empty = wire 15
    00419425  or ecx, 0xd  ... [esi+0x5c8]      ; normal       = wire 13

`0x418080` is plain PM_StartWeaponAnim (`not/and 0x400 | id`). No name check
anywhere on the selection path.

Wire ID -> name slot, viewmodel rate function `0x47b770`, jump table
`0x47be58`:

    entry 13 -> 0x47ba8b  push 9  ; call 0x47ad10
    entry 14 -> 0x47ba9e  push 0xa
    entry 15 -> 0x47bab1  push 0xb
    entry 16 -> 0x47bac4  push 0xc

so wire 13/14/15/16 = slots 9/10/11/12 = source +0xa0/+0xa4/+0xa8/+0xac.

Name registrar `0x47c090` (from CODOL_MELEE_C1_PATH_20260920.md, re-read):

    0047c0d3  mov eax, [ecx + edi*4]   ; names[i]
    0047c0d6  cmp byte ptr [eax], 0
    0047c0d9  je  0x47c0df
    0047c0df  mov ecx, [ecx + 4]       ; EMPTY -> names[1] = idle

Chain: server publishes 14 -> client slot 10 -> "" -> idle. Same for 16/12.

## What was rejected and why

- Client asset repair (seeding +0xa4/+0xac in the zone): not deliverable
  (signed FF gate 0x4B5F02; FFOTD is 64 KB, no weapon serializer). See the
  2026-09-11 doc. Out of scope for a server-side fix anyway.
- Aliasing the recipe onto `m4a1tech_mp` (`codol_loadout_fastmag.c`,
  2026-09-14): C1's reverse model-row lookup gives the event weapon a
  different muzzle model (`muz_default_m4a1techncm_blk` vs
  `muz_flashhiderar_ssncm_blk`), so the equivalence guard correctly rejects
  it on every composition (11x `CoDOL fastmag: equivalent composition could
  not be verified` in the current qconsole.log). It is inert for this
  weapon and left untouched; the parent may retire it.
- Suppressing the quick phase entirely (publish byte2=0, use normal
  timing): consistent on both sides, but 2009/2299 ms IS the stock reload
  time (measured above) -> forbidden stock degrade.

## The fix (server-side, data-driven, no per-weapon table)

Keep C1's quick phase and its quick DURATION (the client predicts the same
1800/2100 from its own def, so prediction stays in agreement), but when the
composed definition's selected quick name slot is empty and the normal slot
of the same phase is not, capture the phase as "normal" for the publisher so
the wire carries 13/15 instead of 14/16. The client then resolves slot 9/11
= `viewmodel_m4a1tech_dualmag_reload_normal[_empty]`, the real dual-mag
reload animation. If both slots are empty the C1 branch is kept (idle either
way). Akimbo weapons are checked on the two dual banks (+0x13c/+0x1fc)
instead of the primary bank.

Files changed:

- `src/codol/assets/codol_asset_registry.c` (CRLF preserved, +8 lines):
  `CODOL_GetNativeWeaponAnimationName(def, slot, &name)` returning one of
  the 144 retained post-override names of the exact registered/composed
  core (`CODOL_FindNativeWeaponQueryCore`).
- `src/codol/weapon/codol_weapon_native.h` (LF): declaration.
- `src/codol/weapon/codol_weapon_reload.c` (LF): `slot_named()`,
  `quick_animation_shown(def, empty)`, and in
  `CODOL_FastMagSetReloadingState`
  `hand->primary_reload_fast = fast && quick_animation_shown(def, empty)`
  (timing `*fast` untouched), plus a bounded `CoDOL dualmag fallback:` dev
  trace when the fallback triggers.

`CODOL_OverlayEngineReloadPhase` (`codol_engine_state.c`, not edited) already
maps native 13/14 -> wire 13|14 / 15|16 from `primary_reload_fast`, so no
publisher change is needed.

Expected behaviour after the fix for this weapon: quick phase = 1800 ms
(empty 2100 ms) with the dual-mag normal animation; since C1 sizes the
animation rate from the wire ID's duration slot (index 9 -> +0x5c8 =
2009 ms), the last ~10 % of that animation is cut when the state returns to
idle. During the client's prediction window (one RTT) the client still
predicts wire 14 -> idle, then snaps to the normal animation with the
restart bit when the snapshot arrives; on LAN that is about one frame.
Ordinary `m4a1tech_mp` + fastmag and every other dual-mag weapon with
populated quick slots are unaffected (`quick_animation_shown` returns 1).

Build: `tools\BUILD-CODOL.ps1 -ObjectsOnly` -> `build OK (exit 0)`
(codol_weapon_native.o, codol_weapon_reload.o, codol_asset_registry.o
rebuilt). No GSC touched.

## Live check

1. Link/promote and restart per the parent's procedure; equip the event M4
   (class with `*a 27 13 227 0 16 0 31 0 153 0 ...`).
2. Reload repeatedly: the first reload after a raise and every second one is
   the quick phase; it must now show the dual-mag flip animation instead of a
   frozen idle viewmodel.
3. With `developer 1`, expect in qconsole.log:
   `CoDOL dualmag fallback: client N weapon 123 nonempty quick slot 10 is
   empty; publishing normal animation 13 with quick time 1800` (and the
   `empty ... slot 12 ... 15 ... 2100` variant), and `expectedC1Anim 13/15`
   on the start lines where it used to say 14/16.
4. Regression: ordinary `m4a1tech_mp` with fastmag must still log
   `expectedC1Anim 14/16` and play its quick animation.
