# Second Round CoD4x Evidence

Date: 2026-10-21 (Asia/Shanghai)

Scope: evidence index for `CoD4x_Server-21.2` only. This file does not compare
CoD4x with CODOL or IW4X. Source proof, build proof and runtime proof are kept
separate.

## Identity and inventory

| Item | Evidence |
|---|---|
| Version | `src/version/version.c`: `SYS_COMMONVERSION 21.2` |
| Target | Makefile: `TARGETNAME=cod4x18_dedrun` |
| License | AGPL-3.0 |
| Inventory | 1,093 paths, 52,815,753 B, 1,085 unique content hashes |
| Readable source layer | 218 top-level C/C++/H/HPP files; 129 `.c/.cpp`, 89 headers |
| Recovered assembly layer | 110 `.asm` in `src/asmsource` |
| Plugin tree | 14 plugin directories plus 5 public ABI headers |
| Built output | none; `bin` contains only a 0 B `dummy` |
| Build tools present | none found in PATH: GCC/G++, NASM, make/MinGW make, CMake, premake |

## Domain evidence

| Domain | Evidence found | Proof level | Missing |
|---|---|---|---|
| B lifecycle | `Sys_Init -> Com_Init -> SV_Init`; `Com_Frame -> SV_Frame`; `SV_Shutdown` | source chain | build/run |
| C frame/thread | `SV_Frame`: `frameUsec`, `sv.timeResidual`, bounded `G_RunFrame` loop, packet sleep; 32-bit time and snapshot-index wrap recovery | source chain | real clock/load run |
| D sockets/OOB | UDP+v6 UDP; TCP stream; sequence sentinels `0xffffffff` OOB, `0xfffffffe` update, `0xfffffff0` reliable fragment; challenge cookie | source chain | packet captures |
| E connect | `getchallenge`, `SV_DirectConnect`, CS_CONNECTED, CS_PRIMED, `SV_ClientEnterWorld`, CS_ACTIVE; reconnect/full/queue/password/protocol paths | source chain | real client |
| F transport | netchan sequence/qport/fragments; encode/decode keyed by challenge/serverId/sequence; Huffman; reliable command replay | source chain | byte-level vectors |
| G assets | Fastfile path checks `DB_FindXAssetHeader(ASSET_TYPE_CLIPMAP_PVS)`; non-FF path parses BSP; map entity string; static models/dynents | load chain | Cod4 zone/IWD |
| H world | `SV_Trace -> CM_BoxTrace`; `SV_ClipMoveToEntity -> CM_TransformedBoxTrace`; CM world link/query exports | source + asm symbols | map-coordinate trace corpus |
| I movement | `SV_UserMove -> SV_ClientThink -> ClientThink -> Pmove`; `Pmove`, `PM_GroundTrace`, `PM_StepSlideMove`, `PM_playerTrace` in asm | source + asm symbols | deterministic pmove fixtures |
| J entities/state | `gentity_s`, `playerState_t`, `clientState_t`, entity/client delta writers; baseline creation | structures and callers | field-by-field layout audit |
| K snapshots | frame history, delta selection, entity/client/playerstate deltas, baseline/archive/cached buffers, Huffman+netchan send | source chain | real snapshots and loss tests |
| L game logic | `G_InitGame`, `G_RunFrame`, `G_SpawnEntitiesFromString`, ClientConnect/Think/Disconnect in asm | assembly entry points | mode/weapon/damage semantics |
| M scripts/rules | GSC VM and script command asm exports; script documentation and notifies | implementation present | per-function behavior |
| N admin/download | Source RCON TCP service `9038723`; named admin or global password; WebAdmin code and HTTP handler; client download/checksum path | source chain | auth and transfer E2E |
| O security | auth address/port `20800`, challenge, banlist, XAC, update proxy, pure checks, query rate limits | source chain | protocol and abuse tests |
| P plugins | handler ABI v4.000; info/init/frame/network/player/game callbacks; 14 plugin dirs | ABI and implementations | load/ABI/runtime tests |
| Q external | master `cod4master.activision.com:20810`, configured masters, `sv_authtoken`, remote global config, autoupdate | source chain | live service and failure tests |
| R build/test | build path present in Makefile; CI builds/packages; `tests.c` delta bodies commented | source inspection | actual build and regression run |

## Additional exact anchors

- `SRC/sv_main.c:4156` `SV_Frame`.
- `SRC/sv_main.c:4727` `SV_SpawnServer`; `:4890` `CM_LoadMap`; `:4896`
  `CM_LinkWorld`; `:4907` `SV_InitGameProgs`; `:4916` baseline.
- `SRC/sv_snapshot.c:109` `SV_WriteSnapshotToClient`; `:451`
  `SV_SendMessageToClient`; `:1078` `SV_SendClientMessages`.
- `SRC/sv_net_chan.c:42` decode; `:79` encode; `:114` transmit; `:150`
  next fragment.
- `SRC/sv_client.c:1004` `SV_UserMove`; `:1672`
  `SV_SendClientGameState`; `:1865` `SV_ExecuteClientMessage`; `:3030`
  `SV_ClientThink`.
- `SRC/sv_world.cpp:1457` `SV_Trace`.
- `SRC/asmsource/_bg_pmove.asm:5633` `Pmove`; `_bg_slidemove.asm:620`
  `PM_StepSlideMove`; `_g_active_mp.asm` calls `Pmove`.
- `SRC/cm_load.c:172` `CM_LoadMap`.
- `SRC/hl2rcon.c:136` Source RCON identification; `:183` auth; `:529`
  command events; `:660` service registration.
- `SRC/httpftp.c:2425` HTTP service event; `:2510` service registration.
- `SRC/webadmin.c:747` HTTP response/session route.
- `SRC/common.c:793` `HL2Rcon_Init`; `:795-799` WebAdmin init is commented
  out; `:800` admin auth init.

## Confirmed conflicts

1. WebAdmin is registered/configured (`sv_webadmin`) but its startup call in
   `Com_Init` is commented out. Presence of `webadmin.c` does not prove WebAdmin
   is reachable in this checkout.
2. Source RCON and client game traffic share the configured server port but use
   separate TCP stream event identification. Do not model them as one protocol.
3. `sv_authtoken` is checked as 32 characters in the host-migration path; this is
   not proof of a working public authentication service.
4. `globalconfig.cfg` can be fetched and executed before normal filesystem init;
   transfer success and content marker are checked, but no signature is shown in
   this path.
5. The asm layer provides thousands of symbols, but symbol presence is not proof
   of semantic equivalence to a particular retail client.