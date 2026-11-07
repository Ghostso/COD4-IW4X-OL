# Shared actor blend: IDA comparison

Status: September 17, 2026 research snapshot on upstream `18928325`.
The isolated blend-only candidate failed human testing: it retained the mismatched
traversal clock and frozen sliding. The native blend findings below remain valid;
the accepted combined correction and validation are in
[actor-traversal-20260917.md](actor-traversal-20260917.md).
This does not recover the original AI controller.

## Exact inputs and method

IDA Professional 9.3 and Hex-Rays were accessed through local
`ida-multi-mcp` commit `6f9e085a78512f2b9e3da8350141666a2c03e6f7`.
Each input used a separate headless worker. Analysis completion and database
identity were checked before decompilation. No executable was launched as a game.

| Input | SHA-256 |
|---|---|
| CODOL deployed `out.exe`, x86 | `044c396c90a7cfa63eac32bea194bf4dfa4d1eab547d9082ae8a575eb49257f9` |
| BO1 `CoDMPServer.exe`, x86 | `4e325afa62cd2e1c2cea2af42cfe80282233f2e25706b865a51b3ded0842eff5` |
| Ghosts `iw6mp64_dh_server_orbis.exe`, x64 | `46d92b7e3033baa4012b9d6192b9189196ed6c8b6949f5a6b631eaf15692edfe` |

BO1/Ghosts databases and symbols came from the user's `treyarch pdbs.zip`.
The Ghosts reference is the Windows-hosted Orbis server executable used by the
project, not a CODOL ABI substitute. CODOL addresses here belong to the exact
`out.exe` above, not the historical 3.3.3.3 target named elsewhere in the catalog.

Local canonical databases and raw MCP responses are in the sibling workspace
folder `ida-research-20260917/databases` and `ida-research-20260917/evidence`.
`input-manifest.json` records the separate input/database hashes. Binary inputs,
databases, symbols and raw decompilation stay outside the repository.

## Finding

Upstream's actor writer forces blend time zero. Its explanation says the weight
ramp advances only when a command is dispatched, roughly once per second.
The exact CODOL client contains a separate elapsed-time update path:

1. `0x549870`, labeled by the native profiling string `update ent info`, iterates
   entities with DObjs. At `0x54990D` it computes current client time minus the
   entity's last animation update. If positive and not excluded by `0x523630`,
   it converts milliseconds to seconds and calls `0x788200` at `0x549932`.
2. `0x788200` advances a nonempty tree through `0x787490`, then invokes its
   time/notetrack stage. `0x787490` interpolates weight toward goalWeight using
   elapsed time and decreases goalTime. This is independent of shared-command
   dispatch through `0x527B40`.
3. The inspected exclusion predicate only admits entity types 1 or 2, combined
   with additional flags/mode conditions; it does not blanket-exclude actors.
4. `0x6714D0` decodes a single zero bit as the float at `0xE6AD88`. IDA byte reads
   confirm `CD CC 4C 3E`, or 0.2 seconds. The old writer instead sends `11100`,
   selecting zero from the table at `0xE56EBC`.
5. `0x789570` gives zero blend immediate full weight. For a nonzero blend it seeds
   a previously zero weight at goalWeight * 0.001, then the update owner advances
   the ramp. The small initial weight is intentional, not proof of a frozen tree.

The large caller containing `0x550221 -> 0x549870` has imperfect automatic IDA
function boundaries. The bounded entity-update disassembly and its direct call
to the clock are verified; no invented name/prototype is assigned to that large
caller. Rendered transition quality still needs a playtest.

## Reference comparison

| Responsibility | CODOL | BO1 | Ghosts |
|---|---|---|---|
| Set goal weight/time | `0x789570` | `XAnimSetGoalWeightNode`, `0x7F3DC0` | `XAnimSetGoalWeightNode`, `0x140251160` |
| Advance weight ramp | `0x787490` | `XAnimUpdateOldTime`, `0x7EE130` | `XAnimUpdateOldTime`, `0x1402517A0` |
| Client tree update wrapper | `0x788200` | `DObjUpdateClientInfo`, `0x7EE850` | Wrapper not claimed; ramp body inspected |

All three goal setters distinguish immediate zero-time changes from nonzero-time
ramps. All three ramp bodies interpolate using elapsed time, reduce the remaining
goal time, and settle at goal weight when it expires. BO1 additionally carries
command-index/recording state. Ghosts uses different x64 structures. These
differences do not change the inspected weight-ramp branch; no reference offsets,
calling conventions or controller policy are copied. BO2 is not required to
resolve this narrow comparison because these ramp semantics agree.

Four confirmed CODOL names/comments were applied to the canonical database,
followed by one decompiler-cache invalidation and refreshed pseudocode. Portable
annotations are in `tools/reverse/annotations/out.exe.json`; apply only to its
declared hash. No guessed structures or function prototypes were installed.

## Candidate boundary

The only runtime change uses the existing compact 0.2-second blend for the
existing shared actor command path. It does not alter command type, flags,
timestamps, root motion, navigation, collision, attachment state or wave lifetime.

Original player-recorded Factory demo analysis previously found 0.2-second
traversal commands, but those used type 2 / flags 3. The current producer uses
type 8 / flags 0. Therefore the uniform blend is explicitly
`OLMOD(actor-blend-policy)`, not a claim that the original controller has been
ported. Prior private-memory command/clock probes also supported ramp progression;
those were synthetic probes, not natural gameplay evidence.

The source audit covers **only this blend field**. Its wider snapshot function
and movement controller remain unaudited by this change. The full upstream audit
has seven pre-existing errors involving reviews 50 and 62; the new symbol review
adds no errors. Do not claim the entire audit passes.

## Required human check

Compare unchanged upstream and this exact candidate at the same starting windows:
walk to tear, tear to vault, and vault to walk. Repeat with several occupants and
check attacks/deaths as well, since they share this writer. Report snapping,
frozen/low-weight poses, or improvement. Check the first red door and drop back,
but distinguish existing movement failures from this blend-only change. The
larger accepted movement patch has not been silently included.

No commit or replacement PR is justified by compilation alone. Obtain the user's
PASS, preserve the exact build hash, then review the complete diff before any
publication.
