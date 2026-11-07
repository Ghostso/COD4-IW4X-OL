# Second Round A-S Matrix

Legend: `S` = source/static evidence, `A` = host/ABI layer required, `B` = build proof, `R` = runtime proof.

| Domain | CoD4x 21.2 | IW4X revision |
|---|---|---|
| A identity | S: 21.2 / cod4x18_dedrun / 1,093 paths | S: 675c4f... / 604 paths + rawfiles |
| B lifecycle | S: Com_Init/SV_Init/Com_Frame/SV_Frame; B/R absent | S: DllMain/Loader/Dedicated; A exact host; B/R absent |
| C frame/thread | S: residual frame loop + packet sleep + wrap recovery; R absent | S: Scheduler/Threading; A host frame; B/R absent |
| D sockets/OOB | S: UDP/TCP OOB challenge; R absent | S: extension OOB + host socket; A; R absent |
| E connect | S: challenge/direct/primed/active; R absent | S: auth envelope then host direct-connect; A; R absent |
| F transport | S: netchan/fragment/encode/Huffman; vectors absent | S+H: custom Huffman/RCon, host netchan; A; vectors absent |
| G assets | S: FF or BSP path; assets absent | S: mount/dependency logic; format dep absent; host required |
| H world | S: CM load/link/trace chain; runtime tiles absent | A: host CM/SV_Trace plus extension patches; host unproven |
| I movement | S+A: source call chain plus asm Pmove; fixtures absent | A: host Pmove/PM trace plus patches; host unproven |
| J entities/state | S: state/delta structures and writers; field audit incomplete | S+A: declared sizes and host addresses; host unproven |
| K snapshots | S: baseline/delta/frame history/send chain; R absent | A: host parser/writer, demo sink and Theatre; R absent |
| L game logic | S+A: asm G_InitGame/G_RunFrame/spawn/ClientThink; semantic audit incomplete | A: host game logic absent from source |
| M scripts/rules | S+A: GSC VM and script exports; semantics incomplete | S+A: GSC components over host VM; semantics incomplete |
| N admin/download | S: Source RCON; WebAdmin code but startup commented; download/checksum | S: RCon + RSA safe path + Mongoose routes; E2E absent |
| O security | S: auth/challenge/ban/XAC/update/pure/rate limits; protocol tests absent | S: auth/Huffman/ACK/UI protections; host and fuzz tests absent |
| P plugins/platform | S: handler ABI 4.000 + 14 plugins; load test absent | S: component/hook ABI + Steam/IPC/Sentry; build absent |
| Q external | S: master 20810/auth 20800/globalconfig/autoupdate; live tests absent | S: master/node/party/server-list/updater; live tests absent |
| R build/test | B/R absent; CI builds only; delta test bodies commented | B/R absent; 16 submodules absent; no build directory |
| S gaps | toolchain, Cod4 assets, symbol semantics, captures, trace/pmove fixtures | submodules, exact host, host RE, captures, deterministic fixtures |

## Completion judgment

Both projects have broad static domain discovery. Neither has sufficient B/R evidence for a complete-server completion claim.

CoD4x is structurally closer to a reconstructable standalone server because lifecycle, netchan, snapshot writer, map loader, trace interface, physics/game logic assembly, RCON, plugin ABI and external services are all present in one tree.

IW4X is structurally an injected extension: its useful C++ source covers auth, OOB, Huffman, RCON/HTTP, scheduling, node/party, asset orchestration and host patches, while core server/game behavior remains in a host binary that has not been identified.

These are independent structural observations, not a lineage conclusion. Cross-project comparison remains blocked until the second round freeze is accepted.
