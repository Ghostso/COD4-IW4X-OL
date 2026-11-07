# Live crash evidence, 2026-09-11

## Native mantle crash

`%LOCALAPPDATA%/CrashDumps/codol_dedrun.exe.78052.dmp` records an access
violation at runtime `0x0104fc04`. The module loaded at `0x00eb0000`, so the
linked address is `0x0059fc04`, inside `G_SetLastServerTime`. EAX is zero;
`cmp esi,[eax+0x3168]` reads address `0x3168`. Entity 0 is zeroed in the dump.

The last gameplay log starts a mantle at command time 36430. C1 mantle sets
player eFlags `0x10000` (`C1.exe` `0x0040a102`). `G_RunFrameForEntity` still
used that bit as an IW3 temporary-entity lifetime marker and freed the player
because `level.time > ent->s.time2`. The next user command hit the cleared
client pointer. The native fix excludes C1 client entities from that retained
temporary-entity expiry rule. It does not disable mantle or mask its wire flag.

## C1 team-color crash

`DMP9B39.tmp` in the C1 install records a read of address 1 in `strlen` at
`0x00aea51c`. Stack: `0x621f9c -> 0x43e214 -> 0x488a99`. The saved ESI in
the color-conversion frame is 7. The color pointer array at `0x02373000`
contains seven color dvars (type 8, indices 0..6). Index 7 instead reaches
boolean dvar `1289`, value 1. `0x43e208` treats that non-color value as a
string pointer. This is an invalid decoded team, not a missing color string.

The server team producer emits only 0, 1, 2, or 6. ClientState copying at
`0x46c944..0x46c950` copies its team directly to clientInfo; no team remap
occurs there. The three-bit XOR codec agrees with the C1 decoder.

`CL_ParseSnapshot` provides the decisive base rule:

- `0x49d9ce`: deltaNum 0 without flag 8 uses saved baseline `0x06d33710`.
- `0x49d9d7`: flag 8 uses a null base.
- `0x49dd8d`: receiving flag 8 copies the new snapshot into the saved baseline.
- `0x49dbd2..0x49dc1f`: the first payload bit independently selects the
  playerState base. Actors, entities, and clients still use the header base.

The server sent later deltaNum-0/flag-0 snapshots relative to zero. C1 decoded
their clients against its saved baseline. Baseline spectator team 6 XOR a
zero-based axis team 1 produces invalid team 7. The server must retain the
same baseline beyond the normal 32-frame acknowledgement ring and use it
for these snapshots. Baseline ownership must advance only after accepted
transmission, and resets must clear both histories.

These findings do not establish that every remaining gameplay defect is fixed.

## Corpse script animation toggle (native dumps54208 and80500)

The latest XAnimNotetrackExists fault used index0x42a; the prior fall-death fault used0x42f. These are animation42/47 plus C1 toggle0x400. GScr_GetCorpseAnim retained `and dh,0xfd`, which clears only IW3 toggle0x200. `_damage.gsc` passes its result to animhasnotetrack. CoDOL now clears0x400 with0xfb. The apparent stale/unmapped tree was an incorrect earlier hypothesis: minidump page omission was not mapping evidence, and the bad indices exceeded actual hunk allocation. Built in91EF2D; live death confirmation pending.
