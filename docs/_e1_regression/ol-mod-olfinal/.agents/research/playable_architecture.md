# CODOL Playable Architecture

> Status: architectural evidence and responsibility model. It is not the live task list. Process-placement conclusions were updated after the in-process `ol_game_server` scaffold became viable; current priorities live in `../AGENTS.md`.

## Scope

Restoring the online menus and restoring a playable match are different
problems. Demonware coordinates identity, content, player state, lobbies and
server allocation. It does not simulate the map or run the authoritative game
frame. A playable CODOL setup therefore needs three distinct roles even when
they initially run on one PC.

## Project Nova author evidence

In a November 22, 2024 discussion, Ayria/Project Nova author Convery described
the same boundary directly:

- Ayria supplies a platform layer and utility plugins rather than a complete
  standalone game service.
- A COD title still needs a plugin which emulates its Demonware server.
- CODOL additionally needs a dedicated game server because, when last checked,
  the client did not contain hosting code.
- A Demonware Gen4 emulator for IW6 or later should be adaptable by adding the
  Tencent services used by CODOL.
- The difficult part is the dedicated server. He described most of that
  protocol as similar to COD4, with CODOL-specific changes still requiring
  substantial implementation work.

The context places the COD4 comparison in the dedicated-server discussion, so
it is best read as the gameplay connection/gamestate/snapshot protocol, not the
Demonware lobby service protocol. Likewise, his `Gen4` label names a Demonware
implementation family; it does not contradict CODOL service messages carrying
wire protocol-version byte `3` in the current captures.

This is strong architectural evidence from the original author, but not final
proof for this exact 2015 QA executable. Convery qualified the hosting-code
statement as based on a check roughly three years earlier. Gate A below must
still establish whether this particular binary retained any dormant server
frame loop.

## Logical boundaries and current placement

### CodolPatch (injected into the game)

Keep only work that must execute inside the original process here:

- redirect or intercept the original endpoints;
- apply verified startup patches before the main thread resumes;
- restore stripped command or asset lookup entry points when possible;
- add runtime tracing around party, connection, asset and script transitions;
- optionally launch or health-check the local backend.

This patch-only layer should not quietly absorb authoritative profile or
matchmaking state. The separately owned `ol_backend` module currently shares
the injected process for compatibility, but keeps its interfaces and state
ownership independent so it can later move out of process without changing the
wire contract.

### CodolBackend (logical control plane; currently injected)

Keep the control-plane state and interfaces independent from gameplay state:

- Auth3 and LSG authentication;
- Storage, publisher files and content manifests;
- profiles, inventory, progression, currencies and statistics;
- lobby/session state and matchmaking queries;
- dedicated-server registration, allocation and reservation;
- post-match result validation and persistence;
- a request/reply ledger with raw packet capture.

The current `ol_backend` keeps this role in the injected Localnetworking plugin
to preserve the validated startup ABI. Auth, LSG and persistence can move to a
standalone process later. Process separation is an operational and reliability
choice, not a wire-protocol requirement.

### CodolGameServer (logical gameplay data plane; currently injected)

This role must own:

- map and fastfile loading;
- the server GSC VM;
- entity and player-state simulation;
- client user-command processing;
- snapshots, configstrings, reliable server commands and game events;
- score, match completion and post-match result submission.

It must ultimately be backed by a recoverable engine server path, a compatible
CODOL server binary, or a new compatible implementation. The current
`ol_game_server` supplies the first part of that implementation inside the
client process. A Demonware emulator cannot replace this role, and sharing a
process does not make client state authoritative.

## Reference behavior from s1x

s1x keeps these roles logically separate even though its local Demonware
implementation is embedded in the mod client:

- `component/demonware.cpp` starts Auth3, lobby and STUN emulators on a named
  thread and intercepts Winsock imports.
- `component/dedicated.cpp` starts the original S1 executable in a dedicated
  mode and patches client-only rendering, sound and UI systems. The original
  executable still supplies the `SV_*` frame loop and script VM.
- `component/party.cpp` implements `map` by entering the original `StartServer`
  UI path. Remote clients query a server address and then call the original
  `CL_ConnectFromParty` with map and gametype.
- `component/gsc/script_loading.cpp` compiles loose source to the engine's
  `ScriptFile` bytecode/stack layout, hooks asset lookup, then executes custom
  `main` and `init` handles inside the server VM.

This design works because S1 still contains a usable gameplay server. It does
not establish that the CODOL ship client contains one.

## Match lifecycle

The target end-to-end lifecycle is:

1. Client authenticates and receives valid Auth3/LSG session material.
2. Client downloads publisher configuration and loads its persistent profile.
3. Party/lobby records the roster, playlist, map and gametype preferences.
4. Matchmaking selects or allocates a registered game server and returns its
   address plus the exact CODOL session descriptor.
5. Party `go` transitions the client to `CL_ConnectFromParty` (or CODOL's
   equivalent) with that descriptor.
6. Client and game server complete challenge, authorization and gamestate
   exchange.
7. Both sides load compatible map assets; the server loads server GSC.
8. The server consumes user commands and publishes snapshots, configstrings,
   events and reliable server commands for the duration of the match.
9. The game server sends final results to the backend, which commits profile,
   inventory and statistics changes transactionally.

Returning a fake matchmaking success without steps 4-8 can only move the UI to
a later failure.

### Validated client transition

The reconstructed backend now drives the unmodified client through the real
room transition rather than a forced function call:

```text
ready room message (event 8)
  -> FIND_SERVERS
  -> mmbook
  -> mmbook accepted (event 21)
  -> mmstart
  -> gameplay connection challenge
```

The historical PVP trace returned a client-created lobby session as the server.
This happened because task `0x15/5` ignored CODOL's leading query discriminator:
`1` means `FIND_SERVERS`, while `3` means `FIND_LOBBIES_BY_PLAYLIST`. CODOL then
sent an `mmstart` command containing `playlist 33` and
`start_map_rotate_once 5`, but no gameplay server owned the advertised endpoint,
so the client reached `EXE_CLIENTFAILEDTOCHALLENGE`. The handler now excludes
the local player lobby from an explicit `FIND_SERVERS` query. A positive server
result must come from an independently registered authoritative-server
candidate. The first story mission already stopped when no such server existed.
This confirms the distinction between a working lobby control plane and the
missing gameplay data plane.

### Controlled gameplay probe

At this stage, `references/client_probe/CodolGameplayProbe.py` was the next
diagnostic boundary. It binds a real UDP gameplay endpoint, watches the
reconstructed plugin log for the latest
matchmaking task-1 request, clones that request's native `Session.Demonware`
tail, replaces only the advertised network endpoint, and publishes a legacy
`Matchmaking::Update` event with `Session.Role=server`. The matchmaking handler
returns such explicitly-labelled remote sessions for query kind `1` and keeps
them out of playlist-lobby query kind `3`.

CODOL's `bdCommonAddr_Serialize` at `0xA36F60` establishes the 37-byte address
layout used by the probe: five local `bdAddr` values, one public `bdAddr`, then
one NAT byte. Each IPv4 `bdAddr` is four address bytes plus a little-endian
`uint16` port. Unused local entries use CODOL's native
`00 FF 00 FF 00 00` sentinel.

The probe answers `getchallenge` with a controlled `challengeResponse` and
records the subsequent UDP payload, including `connect`, without pretending to
provide gamestate or snapshots. A successful capture closes only the endpoint
selection and connection-request part of the authoritative-server endpoint contract.

```powershell
python references\client_probe\CodolGameplayProbe.py --log diagnostics\gameplay-probe.jsonl
```

Start the probe before entering a player room. It waits for a native task-1
descriptor before advertising itself. `--descriptor-hex` can supply a captured
descriptor explicitly when testing a flow such as PVE that does not first
create a player lobby.

### Synthetic snapshot result and boundary

The probe has since closed more of the client wire contract. It can complete
CODOL's NAT introduction and DTLS exchange, accept profile-stat chunks, enter
gamestate, and send a bounded snapshot. The entity delta needed CODOL's actual
field-0 descriptor (`offset 4`, encoding `-77`) and its raw-byte msg cursor.
With one local client and one `ET_PLAYER` entity, runtime inspection showed:

```text
snapshot overflow = 0
entity count = 1
client count = 1
entity 0 eType = ET_PLAYER
client rendering loop ~= 84 FPS
```

This moved the client past `waiting for player data` and into the map, but the
world remained black and the player was not in a valid spawn state. That is a
useful successful experiment: it proves the receive-side framing and delta
decoder, while also marking the point where additional hand-authored fields
would become a fake game implementation.

`CodolGameplayProbe.py` is therefore a conformance harness, not the first draft
of `CodolGameServer`. Keep it for handshake fixtures, minimal gamestate and
snapshot regression, packet recording, and differential comparison with a real
server. Do not grow it by manually adding weapons, movement, spawning,
objectives, animation, collision, or match rules.

## Authoritative server frame loop

The native server does not decide independently which network fields should be
faked. It owns gameplay state and derives packets from that state:

```text
network receive
  -> decode client usercmds
  -> SV_Frame / time accumulation
  -> G_RunFrame
     -> server GSC VM
     -> spawn, movement, weapons, damage, objectives and entities
  -> SV_BuildClientSnapshot
     -> visibility and client-specific playerState
     -> configstrings, events and reliable server commands
  -> SV_WriteSnapshotToClient
     -> baseline/ack-aware netfield delta serialization
  -> netchan / DTLS transmit
```

The first native scaffold now lives in `CodolGameServer`. It is an x86 plugin
loaded into the CODOL process, not a BO1 binary. For the validated QA build it
checks the PE identity and instruction prefixes, hooks CODOL `Com_Frame`, calls
the original frame, and advances an isolated fixed 20 Hz server scheduler. It
now owns the CODOL DTLS endpoint, challenge/connect/profile-upload flow,
per-client netchan sequences and reliable-command acknowledgements. A real
client completed that chain without dropped packets.

The first server-owned gamestate boundary is also in source. Its
`SV_WriteGameState` follows the BO1 `SV_SendClientGameState` ordering while
using CODOL's recovered command IDs, 13-bit configstring indexes, two 10-bit
terminators and 0x30-byte `msg_t`. Production serialization calls the verified
CODOL `MSG_Init`, `MSG_WriteBits` and `MSG_WriteString` ABIs; plugin startup
constructs and byte-compares a complete fixture before installing hooks. Map,
gametype and checksum state must be configured explicitly, so an ordinary
launch continues to send only bounded EOF replies. Once configured, the first
netchan request after profile upload sends gamestate once and moves that client
from `Connected` to `ClientLoading`.

The configstring checksum is not a synthetic server constant. CODOL
`CCS_InitializeConstantConfigStrings` at `0x005850B0` builds the local NCS table
and stores the value compared by `CL_ParseGameStateMessage` at `0x02DF7D90`.
The plugin reads that initialized client value and refuses gamestate
configuration before it exists or when an operator-supplied assertion differs.
A clean runtime initialized it to `962763178` (`0x396299AA`); zero must not be
used as a fallback.

This is a parser-compatible connection milestone, not a playable server. The
plugin still lacks authoritative map spawning, baselines, player/entity state,
snapshots, usercmd execution, GSC and `G_RunFrame`. Subsequent server-world work
depends on deriving gamestate configuration from the booked playlist/server
state and producing an initial snapshot from state owned by that server world.

KisakBlack and other related COD sources are implementation blueprints only.
Each ported `SV_*` or `G_*` stage must use CODOL-owned layouts, recovered CODOL
wire formats, and verified CODOL engine bindings. Compatible CODOL functions
are called in place; server-only functions absent from the client are compiled
as native code inside this plugin.

The COD4 reimplementation in KisakCOD exposes this complete ownership chain in
buildable source, including `SV_Frame`, `G_RunFrame`,
`SV_BuildClientSnapshot`, `SV_WriteSnapshotToClient`, the GSC VM and fastfile
loading. Its protocol and assets are not CODOL-compatible without adaptation,
but it is a materially better implementation base than extending the Python
probe. IW4x is closer in engine lineage, but its dedicated mode patches and
calls server functions still present in the original MW2 executable; those
functions are absent from the CODOL QA client.

The preserved FourDeltaOne `warfare2` source is supporting evidence rather
than a recoverable server implementation. It downloaded an early CODOL package
as an asset source and loaded an unpreserved `w2core.dll`; that core is not in
the repository. It shows that an IW4-derived runtime consuming selected CODOL
content was practical, but it does not supply a buildable CODOL 3.3.3.3 server.

The evidence-derived implementation sequence at that stage was:

1. Run a buildable related authoritative server unchanged on one native map and
   capture its complete `SV_*` lifecycle as the baseline.
2. Put a protocol adapter at the server boundary: CODOL challenge/connect,
   DTLS/netchan, usercmd decoding, gamestate and snapshot netfields.
3. Differentially compare adapter output with the client-side probe and traces;
   never infer game rules from isolated packet fields.
4. Add a CODOL asset compatibility layer one asset class at a time, beginning
   with map collision/map ents, weapon definitions and ScriptFile/GSC.
5. Only after one stock CODOL map and gametype run under the authoritative
   frame loop, connect backend allocation and persistent match results.

This sequence explains dependencies; it is not maintained as the current task
list. Completed and next work is recorded only in `../AGENTS.md`.

## GSC distribution model

Server GSC normally executes on the gameplay server. It is not copied to every
client and remotely executed as source code. Its visible effects cross the
gameplay protocol as authoritative entity/player-state changes, snapshots,
configstrings, events and server commands. A client may also have separate
client scripts or cgame logic for presentation.

If CODOL downloaded scripts during online startup, that is more likely a
publisher/content delivery path which installs compiled assets before map load,
not arbitrary GSC source carried in normal match packets. This must be verified
from the CODOL storage requests and asset loader rather than assumed from other
titles.

Given GSC source, the safest development path is:

1. Recover CODOL's `ScriptFile` layout, opcode table, token/name mapping and VM
   build from existing assets and the executable.
2. Extract and decompile an existing small script.
3. Compile it back and prove bytecode/stack compatibility with a no-op change.
4. Hook asset lookup to load a loose compiled script for one map.
5. Only after the loose-asset path works, build or modify fastfiles/content
   packages.

Numeric asset or token strings are not proof that a console command exists.
CODOL may use token IDs for script/asset names while separately stripping or
omitting command registrations. Commands should be recovered from registration
tables, call sites and runtime dispatch, then reintroduced by a plugin only
when the underlying implementation still exists.

## Player-state ownership

Use separate state models with explicit handoffs:

| State | Authority | Examples |
|---|---|---|
| Persistent, out of match | CodolBackend | identity, loadouts, inventory, progression, currency, stats |
| Session/lobby | CodolBackend | roster, party owner, playlist, map vote, reservation, server address |
| Runtime, in match | CodolGameServer | entities, health, ammo, score, objectives, spawn state |
| Client presentation | Game client | interpolation, effects, HUD and local prediction |

The game server should receive a signed or otherwise verifiable match profile
snapshot. At match end it submits a result transaction with a unique match ID;
the backend applies it once and records the before/after state.

## CODOL feasibility gates

### Gate A: gameplay server viability

Before expanding matchmaking, determine whether the QA client retains enough of
the authoritative server:

- `SV_Init`, `SV_Frame`, `SV_SpawnServer` or functional equivalents;
- `G_RunFrame`, game entities, client command processing and snapshot building;
- server script loading and execution;
- connectionless server challenge/connect handlers;
- a dedicated/listen-server mode selector and map spawn path.

Gate A is negative only for a dormant, complete native hosting path in this QA
ship client. The client retains the complete
consumer side of the connection:

- `CL_CheckForResend` at `0x465C00` sends `getchallenge`, `connect`, `stats`,
  and `heartbeat`;
- `CL_DispatchConnectionlessPacket` at `0x466790` consumes
  `challengeResponse` and other server replies;
- `CL_ParseGameStateMessage` at `0x46DEA0` enters `CA_GAMESTATE` and parses the
  gamestate sent by a server.

The corresponding producer side is absent. In the symbolized BO1 server,
`SV_ConnectionlessPacket` references standalone `getchallenge` and `connect`
tokens and dispatches to `SV_GetChallenge`, which emits
`challengeResponse %i`. CODOL has the client format `getchallenge 0 \"%s\"` and
the client token `challengeResponse`, but neither server token/format nor an
equivalent dispatch call graph. The BO1 `SV_Init`, `SV_Startup`,
`SV_SpawnServer`, `SV_Frame`, `G_RunFrame`, server gamestate/snapshot builder,
and server GSC signatures also have no CODOL counterpart found by the targeted
string-xref and call-graph pass. The surviving `EXE_SERVERKILLED` string is only
classified by the client's disconnect-error function at `0x4EC9A0`.

The room chain independently reaches the same conclusion. The
`mmbook accepted` handler at `0x6E6F60` calls `0x6E6BF0` to construct
`mmstart sv_resetServer; ... map ...`, then sends it through the room interface
to an external allocator/server. `sv_resetServer`, `sv_post_options`, and
`start_map_rotate_once` occur only in those outbound format strings; the client
does not register or receive them. The package also contains no separate CODOL
game-server executable.

This does not mean the CODOL protocol is unrecoverable, nor does it require the
first implementation to be a separate process. It means CodolPatch cannot
expose a dormant complete listen server from this executable. The practical
paths are a compatible CODOL dedicated-server build, a related engine server
adapted to CODOL's protocol/assets, or a new protocol-compatible server such as
the current in-process `ol_game_server` scaffold. Any option must own real
authoritative state rather than synthesize client-facing packets ad hoc.

### Gate B: script toolchain viability

Identify CODOL's server/client script asset types and prove one extracted script
can be round-tripped. Do not begin by converting the entire IW4 script tree:
those scripts are structural references, not drop-in CODOL content.

## Roadmap ownership

The earlier eight-item milestone list duplicated the active handoff and became
stale as the backend and in-process game-server scaffold advanced. It has been
removed. `../AGENTS.md` is the only current roadmap; this document retains the
architectural dependencies and feasibility evidence used to evaluate it.
