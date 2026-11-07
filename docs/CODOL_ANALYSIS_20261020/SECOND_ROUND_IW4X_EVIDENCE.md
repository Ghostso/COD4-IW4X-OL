# Second Round IW4X Evidence

Date: 2026-10-21 (Asia/Shanghai)

Scope: evidence index for `IW4X/iw4x-client`, its rawfiles candidate, and the
unproven host candidates. This file does not compare IW4X with CoD4x or CODOL.
The extension source, host behavior, dependencies and runtime are separate proof
layers.

## Identity and inventory

| Item | Evidence |
|---|---|
| Main repository | `IW4X/iw4x-client` |
| HEAD | `675c4f1e0355c0f07e9d2679429f3d90d9ed175d` |
| Worktree | clean at inspection time |
| Target binary | injected x86 `SharedLib` (`iw4x.dll`), C++20/MSVC |
| Main source inventory | 604 paths, 15,083,242 B, 604 unique content hashes |
| Rawfiles inventory | 7,439 paths, 1,033,997,734 B, 7,364 unique content hashes |
| Submodules | 16 declared, all uninitialized |
| Generated version headers | absent |
| Build directory | absent |
| Built `iw4x.dll` | absent |
| Host candidates | `iw4x.exe` from rawfiles and `COD8/iw4mp.exe`; SHA recorded, host/address match not proven |
| Static ABI surface | 538 function-pointer typedefs; 3,236 address tokens; 2,202 hook/prototype call sites by text count |

The hook/address counts are source-search counts, not unique effective patch
sites: generic hook helpers, declarations and repeated references are included.

## Component registration

`Components/Loader.cpp:92` registers components in a fixed order. Relevant server
flow includes:

```text
ZoneConvert -> Singleton -> Auth -> Command -> Dvar -> Exception -> IPCPipe
-> Network -> Logger -> Sentry -> UIScript -> ZoneBuilder -> ConfigStrings
-> AssetHandler -> ... -> Dedicated -> ... -> Download -> ... -> Huffman
-> ... -> Node -> Party -> ... -> RCon -> ... -> Scheduler -> Security
-> ServerCommands -> ServerDemo -> ... -> Session -> ... -> Threading
-> GSC -> BotLib
```

This proves availability/registration in this revision. It does not prove that all
components are enabled in `-dedicated` mode.

## Domain evidence

| Domain | Evidence found | Actual implementation owner | Missing |
|---|---|---|---|
| B lifecycle | `DllMain.cpp` host-entry hook; Loader; Dedicated post-init and host patches | extension starts inside host | build/run |
| C frame/thread | `Scheduler` pipelines ASYNC/RENDERER/SERVER/CLIENT/MAIN/QUIT; one jthread; host-frame hooks at 0x416049, 0x4B0F81, 0x4B724F | scheduling in extension, simulation in host | timing/load run |
| C pacing | `Threading.cpp`: 1 ms timer period, net-aware select sleep, residual; dedicated `SVFrameWait`; client 1 ms residual `ComFrameWait` | hybrid extension/host | build and measured frames |
| D OOB | 4-byte `0xffffffff` prefix then command/newline/data; client packet callback table; host OOB dispatcher hook at 0x5AA703 | extension constructs/dispatches, host socket | host version match, captures |
| E connect/auth | proto `Auth::Connect`; challenge signature; XUID/public-key/info identity checks; security level by SHA-512 leading zero bits; then host `SV_DirectConnect` at 0x460480 | extension auth, host connect state | E2E and malicious cases |
| F netchan | `netchan_t` size 0x62C; host `SV_Netchan_Transmit` 0x47CB60; protocol `0x99`; client clc is 3-bit | host | byte vectors and host RE |
| F Huffman | custom compressor/decompressor, 256 symbols, max 11 bits decode; hooks SV/CL compress/decompress | extension in source | cross-check against captured wire |
| G map/assets | zone search paths, dependencies, patch files; IWD mount/unmount; `AssetInterfaces/IclipMap_t`, `IMapEnts`; actual format reader in `deps/iw4-open-formats` | extension orchestration, missing dep format, host engine | initialize submodule and parse assets |
| H world | host `CM_*` and `SV_Trace`; source `Structs.hpp` trace/clip layouts; `PlayerMovement` trace patches | host | host RE and map traces |
| I movement | host `PMoveSingle` 0x5743E0, `PM_Trace` 0x441F60, `PM_playerTrace` 0x458980; extension modifies masks, bounce, speed, trace surfaces | host core, extension patches | deterministic fixtures and host checksum |
| J entities/state | `playerState_s` 0x311C, `entityState_s` 0x100, `gentity_s` 0x274, `client_s` 0xA6790, `gclient_s` 0x366C | struct declarations, host behavior | verify exact host build |
| K snapshots | `clSnapshot_t` 0x314C; `snapshot_s` 0x339EC; host parse/write addresses; Theatre baseline and snapshot hooks | host writer/parser | field-by-field host audit |
| L game logic | no complete game source in main repo; host functions and GSC patches only | host/game VM | host binary or independent reimplementation |
| M scripts | GSC VM component plus IO, entity, field, string, patches, script storage, int64 | extension plus host VM | semantic and abuse tests |
| N RCon | OOB `rcon` and `rconSafe`; constant-time plain password compare; 10 failures/s global budget; per-IP limiter; RSA-signed safe path | extension | E2E and rate-limit tests |
| N HTTP/download | Mongoose TCP listener on same game port in dedicated; routes `/info`, `/list`, `/map`, `/file`, `/serverlist`; SHA-256 file manifests | extension | dependency and transfer E2E |
| O security | Huffman bounds, negative reliable-ACK drop, deferred packet cap, UI string truncation, DVAR protections, auth and bin check | extension patches | host RE and fuzz tests |
| P platform | Steam interface/proxy, IPC protobuf, Sentry, named mutex, crash capture | extension | submodule/build/run |
| Q external | master heartbeat `IW4`, node list protocol (protobuf + ZLib), party protobuf, server list HTTP, updater | extension | live and fault-path E2E |
| R build/test | `generate.bat`, premake, submodules, buildinfo action | source inspection | actual configure/build/test/run |

## Exact anchors

- `SRC/DllMain.cpp:35` host filename check at `0x6F9358`; `:50` entry hook
  0x6BAC0F.
- `SRC/Components/Loader.cpp:92` ordered registration.
- `SRC/Components/Modules/Dedicated.cpp:39` fastfile patch; `:180`
  constructor; `:188` frame callback; `:190` host init hook; `:199-245`
  rendering/thread/UI patches; `:245` time-wrap hook.
- `SRC/Components/Modules/Dedicated.cpp:163` heartbeat; `:280` GUID/title/tag
  broadcast; `:287-288` heartbeat schedule.
- `SRC/Components/Modules/Scheduler.cpp:77` server-frame hook; `:159`
  constructor.
- `SRC/Components/Modules/Threading.cpp:64` server wait; `:86` client pacing;
  `:199` packet-event stub; `:211` constructor.
- `SRC/Components/Modules/Network.cpp:184` OOB prefix; `:215` command data;
  `:296` command dispatch; `:357` host patches.
- `SRC/Components/Modules/Auth.cpp:216` connect parse; `:298-364`
  identity/signature/security checks; `:369` host redirect; `:705`
  constructor; `:721` default security level 23.
- `SRC/Proto/auth.proto:12` Connect message.
- `SRC/Components/Modules/Session.hpp:7` `DISABLE_SESSION`; `Session.cpp:19`
  direct send plus delayed resend.
- `SRC/Components/Modules/RCon.cpp:180` plain auth; `:258` safe executor;
  `:282` constructor.
- `SRC/Proto/rcon.proto:5` signed command.
- `SRC/Components/Modules/Download.cpp:585` password hash check; `:773` file
  route; `:883` route table; `:937` dedicated Mongoose startup; `:961`
  listen on `Network::GetPort()`.
- `SRC/Components/Modules/ServerDemo.cpp:327` network record; `:346`
  transmit hook; `:401` pre-encode capture.
- `SRC/Components/Modules/Node.cpp:245` response processing; `:303` list
  send; `:397` constructor.
- `SRC/Components/Modules/Party.cpp:443` info response; `:275` constructor.
- `SRC/Components/Modules/Security.cpp:118` reliable ACK guard; `:170`
  constructor.
- `SRC/Game/Server.cpp:16` host `SV_DirectConnect`; `:20` host
  `SV_ClientThink`; `:29-38` host server globals.
- `SRC/Game/Structs.hpp`: protocol 0x99; static sizes including `netadr_t` 20,
  `netchan_t` 0x62C, `client_s` 0xA6790, `playerState_s` 0x311C,
  `entityState_s` 0x100, `trace_t` 0x2C, `pmove_s` 296.
- `SRC/Components/Modules/PlayerMovement.cpp:927` constructor; host trace
  addresses and patches appear before this line.

## Host boundary

The extension source cannot by itself reconstruct the following server layers:

- UDP/TCP socket loop and socket ownership;
- actual `SV_DirectConnect` state transitions;
- host netchan encode/decode and sequence/ACK policy;
- snapshot visibility, baseline, delta writers and entity serialization;
- collision brush/BSP algorithms and `CM_*` implementation;
- pmove ground/step/slide algorithms;
- game entity spawning, weapon, damage, scoring and mode logic;
- host GSC VM execution semantics.

The exact host must therefore be locked by hash and disassembled. File names such
as `iw4mp.exe` and `iw4x.exe` are not sufficient identity evidence.

## Rawfiles evidence

The rawfiles tree is a runtime/asset repository, not the server implementation.

| Item | Value |
|---|---|
| Root | `DEV-BOOKING/_lineage021/iw4x-rawfiles` |
| Files / bytes | 7,439 / 1,033,997,734 B |
| Unique content | 7,364 |
| Largest file family | `iw4x/` 7,333 paths |
| Fastfiles | 53 `.ff`, 91,117,816 B |
| Scripts | 396 `.gsc`, 2,179,215 B |
| Entity sources | 61 `.ents`, 7,239,839 B |
| Textures | 1,234 `.iwi` |
| Audio | 5,134 `.wav`, 30 `.mp3` |
| Runtime binaries | `iw4x.exe`, `binkw32.dll`, `mss32.dll`, `Unlinker.exe` |

`zone/patch` includes patch fastfiles for maps such as `mp_firingrange`,
`mp_cross_fire`, `mp_killhouse`, `mp_nuked`, `mp_rust_long` and `mp_shipment`.
The tree confirms assets are present as a candidate. It does not prove that the
currently checked-out `iw4x-client` revision consumes them without a matching
host binary.

## Confirmed conflicts

1. `IW4X` is an injected extension, not a standalone server kernel.
2. `DISABLE_SESSION` means the ECC session protocol is compiled out by default;
   Node/Party code therefore uses the direct-plus-resend path in this revision.
3. Web/HTTP and RCon are implemented in the extension, but authentication and
   game netchan are split across extension and host.
4. `sv_securityLevel` defaults to 23, but no runtime proof shows a real client
   satisfying it in this checkout.
5. The custom Huffman implementation is testable in isolation but has no
   captured target wire vector here.
6. The rawfiles tree proves asset availability, not host ABI compatibility.
7. No submodule, generated header, solution or DLL is present, so no source
   revision can be called build-verified.