# DOGS killstreak server crash, 2026-09-22 17:22:43

Status: root cause PROVEN from the crash record + symbols (byte-for-byte),
FIX WRITTEN (one header), objects BUILT (`tools\BUILD-CODOL.ps1 -ObjectsOnly`,
exit 0, the three reader objects recompiled and now read the right offset).
NOT LINKED, NOT LIVE: the parent links and promotes. The production server
on udp/17733 was found DOWN (nothing bound) after the crash; not restarted
by this worker.

## What overwrote `a->species`

Nothing. `a->species` is intact and points at `species_table[0]` (the dog
row). The corruption is in how that row is READ: `codol_actor_species_t`
(src/codol/player/codol_actor_scripts.h) has two different layouts in the
binary because the header was the only CoDOL struct header not wrapped in
`#pragma pack(push, 8)` / `#pragma pack(pop)`.

- `codol_actor_scripts.cpp` (defines `species_table[]`) includes
  `codol_actor_scripts.h` BEFORE anything that reaches `src/server.h`, so the
  typedef closes under the DEFAULT layout.
- `codol_actor_lifecycle.cpp`, `codol_actor_spawn.cpp`, `codol_sentient.cpp`
  include it after `src/server.h:125`'s bare `#pragma pack(1)` has leaked in
  (via codol_actor_lifecycle.h -> ... -> g_sv_shared.h -> server.h), so their
  readers use the PACKED layout.

Measured with the preprocessor (`obj/claude-workers/packstate_i.py` over
`g++ -E` output, build flags), before the fix:

| TU | pack state at `} codol_actor_species_t;` |
|---|---|
| codol_actor_scripts.cpp (table definer) | default |
| codol_actor_lifecycle.cpp (reader that crashed) | 1 |
| codol_actor_spawn.cpp | 1 |
| codol_sentient.cpp | 1 |

### Row layout under the two packings

| column | default (definer) | pack(1) (readers) |
|---|---|---|
| name, animtree | 0x00, 0x04 | same |
| treeSelector, animlistMask, talkBit | 0x08, 0x0c, 0x10 | same |
| category, classname, animscript | 0x14, 0x18, 0x1c | same |
| perfectInfo (u8) | 0x20 (+3 pad) | 0x20 |
| stateIndex | 0x24 | **0x21** |
| stateName | 0x28 | **0x25** |
| stateApply | 0x2c | **0x29** |
| sizeof | 0x30 | 0x2d |

The reader fetching `stateName` at +0x25 gets bytes
`stateIndex[1..3] ++ stateName[0]`.

### Byte-for-byte match with the crash record

`bin/codol_crash.txt`, last record: `EXCEPTION_ACCESS_VIOLATION`, eip = eax =
`0xf300330e`; frame #00 `G_RunFrameForEntity+0x151` (return after
`call _CODOL_ActorRunFrame`), `[esp+0] = CODOL_ActorRunFrame+0x1ca`. The
module was loaded at base 0x001c0000 (frames read
`codol_dedrun_next.exe+0x2c87 (0x001c2c87)`), not the link-time 0x400000.
`codol_dedrun_next.exe` is md5-identical to `bin/codol_dedrun.exe`
(57c753b9...), whose symbols are:

```
00570e5a T _CODOL_DogStateIndex   -> rebased 0x00330e5a = bytes 5a 0e 33 00
00570ff3 T _CODOL_DogStateName    -> rebased 0x00330ff3 = bytes f3 0f 33 00
```

dword at row+0x25 = `0e 33 00 | f3` = **0xf300330e**. That is the faulting
eip exactly. The disassembly at `CODOL_ActorRunFrame+0x19f..+0x1ca`
(`mov 0x25(%eax),%eax ... call *%eax`) is source line
`codol_actor_lifecycle.cpp:1284-1285`:

```
const char *st = a->species && a->species->stateName ?
    a->species->stateName((unsigned)a->animationState) : NULL;
```

The lifetime struct's own odd offsets in that disassembly (`species` at
`0x47(%ebx)`) are the same leak: `codol_actor_lifetime_s` is compiled under
pack(1) too (17 + 36 + 2 + 16 = 0x47), but it is private to
codol_actor_lifecycle.cpp so its layout is consistent and harmless.

### Why zombies never crashed, and why dogs did not crash before

The zombie row's three backend columns are `NULL, NULL, NULL`; the misread of
three all-zero pointers is still zero, so every `a->species->stateX ?` guard
fails cleanly and the zombie takes the GSC-driven path. The dog row is the
only one with non-NULL backends; the misread of `stateIndex` (+0x21 = 3 pad
bytes + 1 real byte = 0x5a000000) and `stateApply` (+0x29 = 0x1100330f) are
garbage too, so `a->species->stateApply(...)` at :1528 would have crashed on
the same first frame had :1284 not run first. The defect dates from commit
9b0ec4a8 (2026-09-20, "species table replaces the hardcoded dog"), which
introduced the unwrapped header; no include order changed since (`git diff
9b0ec4a8 HEAD` on the four files shows no `#include` change). Dogs were not
exercised on any binary after that commit until 2026-09-22 17:22.

## Ruled out

- Overflow into `species` from the fields ahead of it: not needed to explain
  the value, and `CODOL_ActorAllocate` memsets the slot; the only writer of
  `species` is the `self.type` setter (:313) storing a table-row pointer.
  The rebased-symbol match leaves no room for a different origin.
- Entity 999: `bin/home/main/qconsole.log` shows only ONE actor ever
  allocated in that session (`CoDOL actor: ent 999`, 3 lines), so 999 is
  simply where `G_Spawn()` placed the first non-client entity, not an index
  past a small array. The entity-indexed arrays in the actor code are
  `s_sentientForEntity[MAX_GENTITIES]` and `dog_combat targets[MAX_GENTITIES]`;
  the rest (`actors[32]`, `identity actors[32]`, `clients[MAX_CLIENTS]`)
  are slot- or client-indexed.
- The 2026-09-21 actor batch (negotiation/scripted-anim/stuck fields,
  `ActorDescribeTree` stack[64], `dump[512]`): all of those are in the
  lifetime struct AFTER `species` or are function locals; none touch the
  species row.

## Repro

Live repro in the crash harness was NOT possible from this worker:
`bin/codol_dedrun_crash.exe` is a 2026-09-16 build (predates 9b0ec4a8, so it
has no species table), the fix cannot be linked here, and the dogs trigger
(`rcon set codol_dogsTest 1`, `maps/mp/_dogs.gsc:150-200`) requires a live
non-spectator player to call the dogs in. The deterministic repro used
instead is the preprocessor pack-state table above (definer=default,
readers=1), and the object-level proof: before the fix the reader's
`CODOL_ActorRunFrame` loads `stateName` from `0x25(%eax)`; after the fix the
fresh `obj/codol/codol_actor_lifecycle.o` loads it from `0x28(%eax)`.

Live verification for the parent after linking: harness (`bin/START-CRASH-TEST.cmd`,
udp/17799, developer 1, mp_killhouse_sh) with a client, `rcon set
codol_dogsTest 1`; expect the per-second `CoDOL actor: ent N ... anim <state>`
lines to print a real dog state name instead of a crash record.

## The change

`src/codol/player/codol_actor_scripts.h` (LF file, 0 CRs before and after):
the whole header body is now wrapped in `#pragma pack(push, 8)` ...
`#pragma pack(pop)` like `codol_animation_tables.h`, `codol_dog_animation.h`,
`codol_actor_anim_journal.h` and the other CoDOL headers, with a comment
naming this crash. No source changes to the lifecycle/negotiation/scripted-
anim/stuck code, no snapshot/net/engine_state edits. `species_table[]` bytes
are unchanged (the definer was already on the default layout); only the
readers' displacements move (+0x21/+0x25/+0x29 -> +0x24/+0x28/+0x2c).

Objects-only build: `tools\BUILD-CODOL.ps1 -ObjectsOnly` -> "Objects done",
exit 0; `codol_actor_lifecycle.o`, `codol_actor_scripts.o`,
`codol_actor_spawn.o`, `codol_sentient.o` recompiled (17:34).

## Tree-wide check

`obj/claude-workers/packsweep_win.py` (Windows port of
`obj/claude-workers/packcheck.py`: preprocesses every TU with the build flags
and reports any header whose struct definitions close under more than one
pack state). Result (447 TUs, 0 preprocess failures): `codol_actor_scripts.h`
no longer appears. 69 headers are still mixed tree-wide, almost all retained
IW4OL/xassets headers (a pre-existing condition, out of scope). The CoDOL
headers on the ACTOR path that lifecycle.cpp reads under pack(1) while their
definers use default were checked field by field:

| header | struct | mixed layout? |
|---|---|---|
| codol_actor_physics.h | `codol_actor_physics_t` (float[3] + 3 int) | no: all 4-byte members, identical layout |
| codol_dog_combat.h | `codol_dog_attack_goal_t` (2x float[3] + 2 int) | no: identical layout |
| codol_bot_nav.h | `codol_bot_annotation_t` (2x float[3] + 3 u8) | offsets identical, **sizeof 27 vs 28**; harmless today (lifecycle.cpp never names the type or indexes an array of it), but the next `sizeof`/array use across TUs would bite. Recommend wrapping it the same way in a follow-up. |

Other CoDOL headers the sweep flags (vehicle `codol_rc_lifecycle.cpp` reads
`codol_vehicle_*.h` under pack(1); `codol_missile_stickiness.h`,
`codol_radar_types.h`, `codol_character_composition.h`,
`codol_glass_groups.h`) are outside this crash and were not audited; the
sweep log is `obj/_tmp/packsweep.log` and the tool reruns in seconds from a
Windows shell with `C:\msys64\mingw32\bin` on PATH.
