# C1 collision contents and surface flags, and an audit of our masks

Read out of C1.exe 1.1.1.13 (ImageBase 0x400000), 2026-09-17. The material
`infoParms` table lives at **file offset 0x008cd8a8 .. 0x008cddbc** (VA 0x00ccf6a8,
`.data`): **65** records of 20 bytes,
`{ const char *name; int clearSolid; int surfaceFlags; int
contents; int pad }`. Constants are in `src/codol/collision/codol_collision_flags.h`.

Before this, the tree had **no** contents or surface-flag definitions for this
engine — the only `CONTENTS_*` symbols anywhere were legacy Quake/BSPC ones in
`src/botlib/` and `src/bspc/`. Every collision mask in the server was an
unsourced magic number.

## The one thing to understand about the format

There is no `solid` infoParm. **Solid is the default**, and materials with
`clearSolid = 1` *remove* `CONTENTS_SOLID`. Those are: `clipmissile`,
`ai_nosight`, `clipshot`, `playerclip`, `monsterclip`, `aiclipallowdeath`,
`vehicleclip`, `itemclip`, `nodrop`, `nonsolid`, `portal`, `origin`, `foliage`,
`glass`, `water`. So a surface whose contents lack bit 0 is a clip or
non-solid volume, however many other bits it carries.

## Surface type

`(surfaceFlags >> 20) & 31`, index 0 = default, 1 bark, 2 brick, 3 carpet,
4 cloth, 5 concrete, 6 dirt, 7 flesh, 8 foliage, 9 glass, 10 grass, 11 gravel,
12 ice, 13 metal, 14 mud, 15 paper, 16 plaster, 17 rock, 18 sand, 19 snow,
20 water, 21 wood, 22 asphalt, 23 ceramic, 24 plastic, 25 rubber, 26 cushion,
27 fruit, 28 paintedmetal, 29 riotshield, 30 slush.

## Audit of masks already in this server

| where | mask | verdict |
|---|---|---|
| `CODOL_PM_FootstepsC1`, `crash_land` | `(sflags>>20)&31` | **verified correct** |
| mantle census, `codol_collision_native.c` | `0x01000000` = `mantleOn`/`mantleOver` | **verified correct** |
| `_g_active_mp.asm` ClientThink_real | was `0x02810011` / `0x00810011` | **WRONG, fixed** -> `0x02814011` / `0x00800011` |
| `_bg_pmove.asm` PM_UpdateLean | was `0x02810011` | **WRONG, fixed** -> `0x02814011` |
| bot traces, `codol_bot.c` (6 sites) | was `0x02810011` | **WRONG, fixed** -> `0x02814011` |
| `codol_pmove_c1.c:332`, `codol_bot.c:146` | `0x02814011` | **already correct** |
| `SENTRY_TRACE_MASK`, `codol_script_vehicle_builtins.c:142` | `0x02810011` | **not a C1 constant; left alone, no evidence for its correct value** |
| `stance_clear` | `tracemask & ~0x02000000` | **unresolved** |

### The player trace mask, settled

C1 builds it at **`0x0050cbc1`**:

```
cmp dword ptr [ebx+4], 8
setl dl
dec edx
and edx, 0xfdffc000
add edx, 0x2814011
```

so the mask is **`0x02814011`** when that field is `< 8` and **`0x00800011`** otherwise.
Our `ClientThink_real` already had the identical predicate and `cmov` shape — it was a
faithful transcription with **one bit wrong in each branch**: `0x4000` missing from the
first, and `playerclip 0x10000` wrongly retained in the second. `0x02810011` occurs
**nowhere** in C1.exe; `0x02814011` occurs at **20** sites.

**This fix is parity only and must be credited with no improvement.** Measured on
mp_storm_spring, brushes selected by `0x02810011` and by `0x02814011` are 12241 and
12241 — delta 0 — because none of `0x4000`, `0x00800000`, `0x02000000` occurs in any
brush, leaf or material. The bits are entity contents; world geometry cannot carry them.

### Observed values decoded

* `sf 0x1300000` → surface type **19 = snow**. Independently corroborated: the
  location it came from is the snow slab in the user's screenshot.
* `sf 0x1600000` → 22 = asphalt (mp_storm_spring ground).
* `sf 0x0500000` → 5 = concrete (mp_killhouse_sh ground).
* `cf 0x08031640` → `detail | monsterclip | playerclip | ai_nosight | itemclip |
  vehicleclip | canshootclip`, **zero residue, solid bit clear** — a clip
  volume, not world solid.
* `cf 0x00000001` → `CONTENTS_SOLID` alone — ordinary world solid.

## Open: two bits with no name

`0x00800000` and `0x02000000` appear in our masks but have **no authoring
material** in the table, so their meaning cannot be established from it.
`stance_clear` strips `0x02000000` specifically, which is consistent with a
body/actor bit, but that is **not established** — do not guess it. Note
`0x02000000` *is* `mantleOn` in SURFACE flags, which is a different field and an
easy confusion to make.

Resolving these, and finding C1's own player-trace mask constant to compare
against `0x02810011`, is the natural follow-up: a wrong mask includes or
excludes a whole class of volume, which presents as extra solid in one place and
missing solid in another.

## Appendix: the phantom-submodel question, settled (2026-09-17)

The project memory note "phantom submodel brushes" records that the Python server
indexed the clipmap's brush tail — brush-ENTITY geometry in model-local coordinates —
as world collision, and that on **mp_storm_spring** one map-sized bmodel box made
**273 of 309 spawns read startsolid**. The native tree has no equivalent of the Python
fix (`cm_submodels.world_brush_count()`); `codol_collision_native.c:406` publishes all
14100 brushes, tail included. That looks alarming. It is not a bug here, and porting
the Python fix would fix a bug this server does not have.

**Why Python was exposed and this server is not.** Python's `BrushIndex` never walked
the leaf-brush tree at all: it prefiltered on every brush's AABB and then tested side
planes (`pmove.py:661`). With no tree, every brush is reachable, so the tail had to be
excluded arithmetically. This server uses the retained engine traversal —
`CM_TestInLeafBrushNode_r` / `CM_TraceThroughLeafBrushNode_r` in `_cm_trace.asm`, nine
call sites — which culls on the node's own `contents` and on the split planes, and
reaches only what the BSP leads it to.

**Measured.** `tests/test_codol_assets.c --treequery` transcribes that traversal from
the asm. With it, brushes 13629/13631 (the map-sized box, contents `0x08000001`) are
reached at **no probe point**. An earlier, permissive version of the same query — no
contents cull, both children always, leaves found by bounding box — reported them at
almost every point. That is the whole difference between "reachable in principle" and
"the engine visits it".

Two incidental facts worth keeping:

* **Leaf `mins`/`maxs` are not tight.** At one probe, **424 of 3906** leaves have
  bounds containing a single point, and the leaf the BSP descent lands in spans
  1024x2176x640. Iterating leaves by bounding box is not a filter; descend the BSP.
* The lowest brush index claimed by any inline submodel on this map is **13357**, so
  the tail is real — it is simply never traversed.

**Residual risk, checked:** no collision query in the native tree iterates brushes
linearly. Every linear scan is a loader or a census (`codol_collision_native.c:139/193/370`,
`codol_collision_brushes.c:96`, `codol_collision_stream.c:102`, `codol_glass_world.c:72`,
`codol_trigger_native.c:47`). If a future query iterates `cm.brushes` directly, it will
hit the phantoms, and then the split becomes necessary.

## Appendix: how the engine reaches terrain (and the trap in it)

From `CM_MeshTestInLeaf` (`_cm_mesh.asm:2786`) and `CM_PositionTestInAabbTree_r`
(`_cm_mesh.asm:615`). Sizes and offsets here are read off the asm, not assumed:

* terrain aabb record is **32 bytes**: `origin[3]@0`, `halfSize[3]@0xc`,
  `materialIndex@0x18` (u16), `childCount@0x1a` (u16), `index@0x1c` (i32)
* `dmaterial_t` is **72 bytes** (`matIndex*9*8`), `surfaceFlags@0x40`, `contentFlags@0x44`
* partition is **12 bytes**, `triCount@0` (u8), `firstTri@4` (i32); triangles are u16 triples
* `CM_MeshTestInLeaf` walks `leaf->collAabbCount` aabbs from `leaf->firstCollAabbIndex`;
  each is the **root of a tree**, and it gates on that root's material contents against
  the trace mask before descending

**The trap.** For an INTERIOR node (`childCount != 0`), `index` is the **absolute index
of the first child**, and the children are `childCount` consecutive records:
`ebx = index<<5; ...; ebx += 0x20` per child. Only for a LEAF (`childCount == 0`) is
`index` a partition index. Treating `index` as a partition index unconditionally, and
skipping interior nodes, hides every triangle below the root — a query that does this
returns "no terrain here" for ground a player is provably standing on. It cost this
investigation two wrong negatives before a self-check caught it.

**The self-check that catches it:** query a point where a player demonstrably stands and
require the triangle underfoot to come back. On mp_storm_spring at (-372.2, -826.9, -9.2)
that is tri 66640, `asphalt_cracked_002_wet`. A terrain path that cannot find the ground
under a standing player cannot be trusted to report its absence anywhere else.

The engine also dedupes partitions per trace via a checkcount array
(`traceWork+0xa0`/`+0xa4`), so the same partition legitimately appears under more than
one aabb node; duplicate triangle reports are expected and are not a data fault.

## Appendix: C1's ground trace does not test the surface normal

`CODOL_PM_GroundTraceC1` rejected ground with `!tr.walkable || tr.normal[2] < 0.7f`.
**C1 has no normal test.** Its PM_GroundTrace (`0x00411910`) ends at `0x00411b66` with:

```
cmp byte  [ebp-0x1e], 0          ; trace(ebp-0x48)+0x2a = walkable
je   reject
cmp dword [ebp-0x34], 0x2000000  ; trace+0x14 = cflags
je   reject
; accept: walking=1, groundPlane=1, almostGroundPlane=1
reject (0x00411bc6):
  groundEntityNum = 0x7ff; walking=0; groundPlane=1; almostGroundPlane=1
  jumpOriginZ = 0; pm_flags &= 0xffbfdfff
```

Frame offsets are pinned by the trace copy at `0x00411a33` (`add edi, 0x38` = `pml_t.groundTrace`,
`rep movsd` of 0xb dwords = 44-byte `trace_t`), and cross-checked against the `allsolid`
test at `0x004119ab` (`ebp-0x20` = trace+0x28).

Corroboration: every float constant compared against in C1's whole ground region
(`0x40f000..0x412000`) is 0.001, 10, 12, 0.015625, or a surface-type lookup value.
**`0.7f` appears nowhere in it** — its eight occurrences in `.rdata` are referenced only
from unrelated code (`0x42a9f8`, `0x523cee`, …).

**Why it mattered.** Walkability is decided *inside* the trace and arrives as
`trace->walkable`. Re-testing `normal[2]` afterwards is a second, stricter gate, and it
rejects surfaces the engine had already accepted. On mp_storm_spring the measured
departures reported `walkable 1` with `normal[2]` of 0.39–0.66: every one would be
accepted by C1 and was refused by us, dropping the player off the snow onto the rooftop
clip lid 6–16 units below.

The reported normals were **correct** — the triangle at the first departure computes
`|nz| 0.6414` against a trace-reported `0.6414`. This was never a normals bug, a mask
bug, a walkable-bit bug or a traversal bug. It was one clause that should not exist.

Also corrected with it: C1's reject path has fixed effects and the `cflags == 0x2000000`
test is a second way *into* it, not a modifier. The `groundPlane = 0` variant this port
had there is gone.
