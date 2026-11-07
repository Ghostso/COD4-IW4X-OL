# Minigun / mounted-turret server crash — 2026-09-20

**Fault site:** `XAnimGetNumChildren+0x9`, called from `turret_think_client+0x28f`.

**One-sentence defect:** `turret_think_client` in `src/asmsource/_g_misc_mp.asm` still masked the
lerpFrame animation toggle bit with IW3's hardcoded `and bh, 0xfd` (bit `0x200`) instead of CoDOL's
widened `ANIM_HIGH_MASK` (bit `0x400`), so every animation number that had the toggle bit set was
handed to the animtree as `N + 1024` and read off the end of the allocation the instant a player
mounted the Overgrown minigun turret.

The map is **incidental**. `mp_overgrown` is simply the map the user tried, because
`turret_minigun_mp` is the only weapon asset in its fastfile. Any mountable turret on any map hits
the same code path.

The "1096 is a weapon index past a 128-entry table" hypothesis in the brief is **wrong** and is
retracted below with evidence.

---

## 1. Symbolization

### Method (reproducible)

The shipped binary is **not stripped** — `objdump -f` reports `HAS_SYMS, HAS_LOCALS` and `nm`
returns 44 037 defined symbols. No linker map is needed.

```
objdump -f bin/codol_dedrun_next.exe
  -> file format pei-i386, start address 0x004013d0   [MEASURED]
```

The PE `ImageBase` is `0x400000` (confirmed: dump frame `#09 +0x12de` and stack entry `+0x13d0`
correspond to `___tmainCRTStartup` and the PE entry point `0x4013d0`). The dump's load base was
`0x00860000`, so:

```
file VA = 0x400000 + (dump address - 0x00860000)
        = 0x400000 + RVA
```

Symbolizer (written to `obj/_tmp/symz.py`; regenerate the symbol list with
`nm --numeric-sort --defined-only bin/codol_dedrun_next.exe > obj/_tmp/syms_next.txt`):

```python
# keeps only [tTwW] symbols, bisects the sorted list, prints name+offset
python obj/_tmp/symz.py 2679c2 1f652e 14e821 ...
```

Environment: `C:\msys64\usr\bin;C:\msys64\mingw32\bin` on `PATH`.

### Results

Frame chain (dump entry `2026-09-20 15:20:56`):

| # | RVA | Symbol |
|---|---|---|
| fault (eip) | `+0x2679c2` | **`XAnimGetNumChildren+0x9`** |
| #00 | `+0x1f652e` | **`turret_think_client+0x28f`** (dump prints the local label `turret_think_client_50`) |
| #01 | `+0x14e821` | `ClientEndFrame_TurretThink_Stub+0xe3` |
| #02 | `+0x1e1866` | `ClientEndFrame+0xb` |
| #03 | `+0x1f42b2` | `G_RunFrame+0x11` |
| #04 | `+0x7d1d6`  | `SV_Frame+0xd6` |
| #05 | `+0x9eb4`   | `Com_Frame+0x75` |
| #06 | `+0x8392c`  | `Sys_Main+0xbd` |
| #07 | `+0x2d4d`   | `WinMain@16+0xcb` |
| #08 | `+0x30c224` | `main+0xc4` |
| #09 | `+0x12de`   | `___tmainCRTStartup+0x18e` |

`ebp == esp` at the fault because `XAnimGetNumChildren` is a five-instruction leaf; frame `#00` is
its caller, as the brief predicted.

Useful dead-stack entries from the scan (leftovers inside `turret_think_client`'s own frame, not
live frames): `XAnimSetAnimRate+0x23`, `BG_RunLerpFrameRate`, `BG_PlayerAnimation+0x1b`,
`DObjGetBoneIndex+0x20`, `SV_Trace+0x180`. `BG_RunLerpFrameRate` / `BG_PlayerAnimation` being on the
stack is the tell — they are the functions that *write* the animation number this crash then
misreads.

---

## 2. The defect

### The faulting instruction (MEASURED)

```
00667 9b9 <_XAnimGetNumChildren>:
  6679b9: 55                push %ebp
  6679ba: 89 e5             mov  %esp,%ebp
  6679bc: 8b 45 0c          mov  0xc(%ebp),%eax     ; arg1 = animIndex
  6679bf: 8b 55 08          mov  0x8(%ebp),%edx     ; arg0 = XAnim_s *anims
  6679c2: 0f b7 44 c2 0c    movzwl 0xc(%edx,%eax,8),%eax   <-- FAULT
```

`XAnim_s` = 12-byte header + 8-byte entries; `numAnims` is the `u16` at entry+0.
With `edx = 0x307e0320` and `eax = 0x448 (1096)`:
`0x307e0320 + 1096*8 + 0xc = 0x307e256c` — **exactly** the reported faulting address. There is no
bounds check in this function.

### Where the index comes from

`src/asmsource/_g_misc_mp.asm`, `turret_think_client`, at the pre-fix line 1647:

```asm
	mov ecx, [ebp-0x1c0]
	mov ecx, [ecx+0x999b8]     ; bgs->animtree
	mov [ebp-0x174], ecx
	mov ebx, [ebx+0x10]        ; ci->legs.animationNumber
	and bh, 0xfd               ; <-- clears bit 0x200 (IW3 ANIM_TOGGLEBIT)
	mov [ebp-0x170], ebx
	...
	call XAnimGetNumChildren
```

`ebx` here is `&bgs->clientinfo[client].legs`, verified three independent ways:

* `[ebx+0x10]` is non-zero-tested and `[ebx+0x14]` is a pointer whose `+0x50` flags are tested for
  bit `0x4` — exactly `lerpFrame_t::animationNumber` / `::animation` (`src/q_shared.h:663`).
* `_bg_animation_mp.asm:320` compares a lerpFrame pointer against `clientinfo + 0x37c` to decide
  "is this the legs frame".
* `src/codol/player/codol_animation_tables.c:121` places `clientConditions` at
  `bgs + 0x99e5c + client*0x4cc`, which agrees with `clientinfo[0] @ bgs+0x99a04`, stride `0x4cc`,
  and with `level_bgs: resb 0xacd20` in `_g_main_mp.asm:1848`
  (`0x99a04 + 64*0x4cc = 0xacd04`).

### The widening that this site missed

`src/asmsource/_bg_animation_mp.asm` (now `src/asmsource/codol_anim_bits.inc`) already declares the
CoDOL ABI:

```asm
%ifdef CODOL_SERVER
%define ANIM_COUNT(reg) CODOL_AnimationCount
%define ANIM_TOGGLE     0x400
%define ANIM_HIGH_MASK  0xfb        ; clears bit 0x400
%else                               ; IW3
%define ANIM_COUNT(reg) reg+0xc000
%define ANIM_TOGGLE     0x200
%define ANIM_HIGH_MASK  0xfd        ; clears bit 0x200
%endif
```

CoDOL's animation record array is **1024** entries wide (`CODOL_ANIM_RECORD_COUNT 1024`,
`src/codol/player/codol_animation_tables.h:14`) versus IW3's 512, so the restart/toggle bit had to
move from `0x200` to `0x400`. `_bg_animation_mp.asm` was converted to the macros;
`turret_think_client` in `_g_misc_mp.asm` was not, and kept the literal `0xfd`.

### The arithmetic of the crash (MEASURED against the register dump)

Stored `ci->legs.animationNumber` = `0x648` = `584 | 0x400` (animation 584 with the toggle set).

| mask | result | outcome |
|---|---|---|
| correct `& ~0x400` | `584` | in range (`< CODOL_AnimationCount`) |
| shipped `& ~0x200` | `0x448` = **1096** | past the end of the animtree → **crash** |

`eax = ebx = 0x00000448` in the dump. This reproduces the faulting index exactly.

Because the toggle bit flips on every animation change, roughly every other animation transition
while mounted on a turret produces an out-of-range index — hence "immediately crashed".

`BG_RunLerpFrameRate` does the same computation correctly *and* bounds-checks it
(`_bg_animation_mp.asm:328-333`: `and bh, ANIM_HIGH_MASK` / `cmp ebx,[ANIM_COUNT(eax)]` / `jae`
bail). `turret_think_client` had neither.

### Retraction: 1096 is not a weapon index

The brief's leading hypothesis was an unwidened weapon table. It is **false**:

* CoDOL weapon indices are capped at **699** (`CODOL_WEAPON_SLOTS 700`,
  `src/codol/snapshot/codol_configstrings.h:31`; C1's `CG_Init` validates `1..0x2BC`). There is no
  weapon 1096 and nothing near it.
* `0x448 * 8 == 0x2240` looked like an index-scaled table read because it *is* one — the stride is
  the 8-byte `XAnimEntry`, not a weapon record.

### Which weapon "minigun" is

`turret_minigun_mp` — a **map-placed mounted MG emplacement**, not a loadout or killstreak weapon.

* `docs/zone_assets/mp_overgrown.txt:229` — `weapon turret_minigun_mp` is the **only** weapon row in
  the entire Overgrown fastfile, bundled with `minigun_gatling_spinup/spindown/spinloop` sounds,
  `muzzleflashes/minigun_flash_view` and `rumble/minigun_rumble`.
* `scripts/codol/maps/mp/_utility.gsc:632` — `isMG()` returns true for `turret_minigun_mp`.
* It is deliberately absent from the killstreak switch in `_utility.gsc:2160-2180` (which does list
  `cobra_player_minigun_mp`, `pavelow_minigun_mp`, `sentry_minigun_mp`).

Other CoDOL minigun assets exist (`sentry_minigun_mp`, `pavelow_minigun_mp`,
`killstreak_helicopter_minigun_mp`, `minigun_zm`, `cobra_player_minigun_mp`, …) but none of them is
mountable, so none of them reaches `turret_think_client`.

### Map specificity

**Not map-specific.** `turret_think_client` is generic engine code reached from
`ClientEndFrame`; nothing in the path reads the map. Overgrown is where the user happened to find a
mountable turret. Any map whose fastfile places a `misc_turret` reproduces it.

---

## 3. The fix

### New file: `src/asmsource/codol_anim_bits.inc`

The `ANIM_TOGGLE` / `ANIM_HIGH_MASK` / `ANIM_COUNT` / `ANIM_BASE` / `ANIM_ADD_BASE` definitions were
private to `_bg_animation_mp.asm`, which is precisely why a second file could quietly keep the IW3
literal. They now live in one include (`%ifndef`-guarded) that both files pull in, with a comment
naming this crash.

`_bg_animation_mp.asm` lines 3-33 were replaced by `%include "src/asmsource/codol_anim_bits.inc"`.
**Verified as a pure no-op:** the `.text` section of the rebuilt object is byte-identical (md5) to
the `.text` of the pristine `HEAD` source assembled with the same flags.

### `src/asmsource/_g_misc_mp.asm`

Added the include at line 2, and at the defect site:

```asm
	mov ebx, [ebx+0x10]
	; CoDOL: ci->legs.animationNumber carries the 0x400 toggle bit, not IW3's
	; 0x200, because the record array is 1024 wide. Masking 0x200 here left
	; the 0x400 bit set and handed XAnimGetNumChildren index N+1024, which
	; read off the end of the animtree and crashed the server the moment a
	; player mounted a turret. Guard the index the way BG_RunLerpFrameRate
	; does; turret_think_client_40 is the existing "animation not usable"
	; path already taken when legs.animation is still null.
	and bh, ANIM_HIGH_MASK
	mov [ebp-0x170], ebx
%ifdef CODOL_SERVER
	cmp ebx, [ANIM_COUNT(ecx)]
	jae turret_think_client_40
%endif
```

Two parts:

1. **`ANIM_HIGH_MASK`** — the actual bug. `0xfb` under `CODOL_SERVER`, still `0xfd` for a vanilla
   CoD4 build.
2. **A bounds guard**, mirroring `BG_RunLerpFrameRate`. `CODOL_AnimationCount` is set from
   `XAnimGetAnimTreeSize(animtree)` in `BG_LoadAnim` (`_bg_animation_mp.asm:2224-2233`), so it is
   exactly the entry count of the tree that `XAnimGetNumChildren` indexes — the correct bound.
   `turret_think_client_40` is the pre-existing graceful path already taken from inside this same
   block when `legs.animation` is null; it re-enters via `G_TurretCalcFireTime` and touches no
   locals that are unset at this point. The guard is CoDOL-only because vanilla CoD4's 512-entry
   tree cannot produce an out-of-range index.

The guard matters independently of the mask: without it `turret_think_client_90`, the "unknown
animation" error path, calls `XAnimGetAnimDebugName(anims, animIndex)` — which would have
out-of-bounds-read with the *same* bad index before it could print the diagnostic. The Com_Error
never had a chance to fire, which is why `qconsole.log` ends with no `Sys_Error` and no shutdown
banner.

All five other `XAnimGetChildAt` / `XAnimGetAnimDebugName` call sites in `turret_think_client`
(lines 1784, 1821, 1996, 2234, 2253, 2278, 2309) take either `[ebp-0x170]` or a child index returned
by `XAnimGetChildAt`, so they are all covered by the single corrected value.

### Build

Object-file builds only (never a bare `make` — the default target relinks and `ld` deletes its
output on failure):

```
make obj/codol/_bg_animation_mp.o obj/codol/_g_misc_mp.o
```

Both assemble clean. `_g_misc_mp.o`'s `.text` grows by exactly 12 bytes (`cmp r32,[m32]` = 6 plus
`jae rel32` = 6; the mask instruction is the same length). Emitted code verified:

```
1705: 8b 5b 10          mov  0x10(%ebx),%ebx
1708: 80 e7 fb          and  $0xfb,%bh
170b: 89 9d 90 fe ff ff mov  %ebx,-0x170(%ebp)
1711: 3b 1d 00 00 00 00 cmp  0x0,%ebx
      1713: dir32 _CODOL_AnimationCount
```

Line endings preserved: both `.asm` files remain CRLF-dominant on disk exactly as before, and
`.gitattributes` `* text=lf` means git sees no line-ending churn.

**The executable has not been relinked** — per the brief I built objects only and copied nothing
into `bin/`. The parent needs to link and deploy.

---

## 4. Sibling audit

### Same pattern (stale IW3 animation constants outside the macro set) — **one site, now fixed**

Swept `src/asmsource/*.asm` for `and bh, 0xfd`, `0xfffffdff`, `and eax, 0x1ff`, `+0xc000`,
`globalScriptData`, and every `XAnimGetNumChildren` / `XAnimGetChildAt` /
`XAnimGetAnimDebugName` caller. Results:

* `_g_misc_mp.asm:1647` — **the bug, fixed.** The only `and bh, 0xfd` in the tree.
* `_bg_pmove.asm:7552`, `_bg_weapons.asm:2700/6236/7368/7771/7982/8678/8745/8832/8951/8987` —
  `0xfffffdff` on `[reg+0xc]` / `test eax`. These are **playerState `pm_flags`** bit operations, not
  animation numbers. Not the same pattern. Correctly left alone.
* `_g_client_mp.asm:874/884` — `and eax, 0x1ff` inside `G_GetNonPVSPlayerInfo`; 9-bit *coordinate*
  packing (`sar 2` / `add 0xff` / `shl 6` / `shl 0xf`). Unrelated.
* `_bg_pmove.asm:1678`, `codol_pmove_c1.c:695` — `CODOL_AnimationRecords+0x48` with **no index**
  (record 0). Safe.
* `src/codol/player/codol_player_worldweapon.c:64` — already guards with
  `if(anim>=CODOL_AnimationCount || anim>=CODOL_ANIM_RECORD_COUNT) return 0;`. Correct; no change.
* `src/codol/snapshot/codol_engine_state.c` (7 sites) and `codol_weapon_reload.c:27` — these
  deliberately *translate* `raw & 0x200 -> animation |= 0x400`, i.e. they convert the wire's IW3
  restart bit into the CoDOL bit. That is the correct direction and is already CoDOL-aware.
* `bgs->animtree` (`+0x999b8`) is read in exactly three places: `_bg_animation_mp.asm:338` (bounds
  checked), `:2212` (the loader), and `_g_misc_mp.asm:1644` (now bounds checked).

The include refactor means a future file cannot reintroduce the literal without noticing.

### Different pattern found — **NOT fixed, handing back** (`src/bg_public.h`)

While confirming the `clientinfo` offsets I measured a **separate, live memory-corruption bug**. I
deliberately did not bundle it into this crash fix: it is an unrelated struct-layout change, and
mixing it in would make the minigun fix unfalsifiable when the user tests it.

`src/bg_public.h` declares

```c
struct __align(8) bgs_s {
  byte animScriptData[0x9a9d0];   /* WRONG */
  byte generic_human[0x10];
  int time, latestSnapshotTime, frametime, anim_user;
  /* 6 function pointers */
  struct clientInfo_t clientinfo[64];
};
```

but the real layout, cross-checked four ways, puts `clientinfo[0]` at `bgs + 0x99a04` with stride
`0x4cc`:

| evidence | value |
|---|---|
| `_g_misc_mp.asm:1495` `lea edx,[ecx+edx*4+0x99a00]`, then `lea eax,[edx+0x4]` = real base | `0x99a04`, stride `0x4cc` |
| `codol_animation_tables.c:121` `clientConditions` | `bgs+0x99e5c` = `0x99a04 + 0x458` |
| `_bg_animation_mp.asm:320` `legs` | `ci + 0x37c` |
| `_g_main_mp.asm:1848` `level_bgs: resb 0xacd20` | `0x99a04 + 64*0x4cc = 0xacd04` ✓ fits |

The header therefore overstates `animScriptData` by **`0x1004`** (`0x9a9d0` vs `0x999cc`) and
`clientControllers_s` by **4** (`clientConditions` must land at `ci+0x458`, `pXAnimTree` at
`ci+0x4a8`, making `sizeof(clientInfo_t)` `0x4cc`, not `0x4d0`).

Measured consequence — `src/codol/player/codol_player_appearance.c:261`
(`level_bgs.clientinfo[client].dobjDirty=1;`) compiles to:

```
7dc: c7 80 fc ad 09 00 01 00 00 00   movl $0x1,0x9adfc(%eax)   reloc _level_bgs
```

`0x9adfc` instead of the correct `0x99df8` — off by `0x1004`. So the DObj-dirty flag is never set on
an appearance change, and the write lands in an unrelated clientinfo slot.

Also affected: `src/codol/player/codol_pmove_c1_ground.c:1099,1100,1124,1133`
(`bgs->clientinfo[ps->clientNum]`, `ci->turnAnimEndTime`, `bgs->time`). With both a wrong base and a
wrong stride, `clientNum 63` computes `0x9aa08 + 63*0x4d0 + 0x4c0 ≈ 0xade38`, which is **past the end
of `level_bgs` (`0xacd20`)** — a write into adjacent `.bss`.

Proposed patch (measured, but unverified at runtime — needs its own pass):

```diff
--- a/src/bg_public.h
@@ struct __align(8) bgs_s
-   byte animScriptData[0x9a9d0];
+   byte animScriptData[0x999cc];
```

plus shrinking `clientControllers_s` by 4 bytes so `clientConditions` sits at `ci+0x458`. Because
`level_bgs` is allocated in asm (`resb 0xacd20`), the C `sizeof` is not load-bearing — only field
offsets are — so the change is contained to the accessors listed above.

### Not reachable from my files

Nothing. Both `src/codol/script/**` and `bin/home/codol_rawfiles/**` are clean of animation-toggle
arithmetic; `turret_minigun_mp` appears there only in `_utility.gsc:632` (`isMG`) and
`_damage.gsc:1139-1150` (shield-damage clamp), neither of which is implicated.

---

## Artifacts

* Crash log preserved: `bin/home/main/qconsole.log.minigun-20260920`
  (it is a pre-crash startup log; it contains no "minigun" string — the name is a tag).
* Crash dump: last entry of `bin/codol_crash.txt`, `2026-09-20 15:20:56`.
* Symbolizer: `obj/_tmp/symz.py` + `obj/_tmp/syms_next.txt`.
