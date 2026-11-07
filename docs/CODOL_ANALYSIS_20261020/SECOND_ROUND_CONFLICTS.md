# Second Round Conflicts

| ID | Conflict | Resolution |
|---|---|---|
| R-01 | CoD4x source exists but no build toolchain/output is present | Build status remains unverified |
| R-02 | CoD4x needs proprietary Cod4 IWD/zone assets; workspace lacks a verified complete set | Do not claim map/live capability |
| R-03 | CoD4x `sv_webadmin` is registered but `HTTPServer_Init()` is commented out in `Com_Init` | Treat WebAdmin implementation and startup as separate facts; no reachability claim |
| R-04 | CoD4x has TCP Source RCON and HTTP share the same configured server port | Model them as separate stream services and verify event identification |
| R-05 | CoD4x automatically fetches, writes and executes `globalconfig.cfg` before normal filesystem setup | Record as supply-chain/external-service input; no trust claim |
| R-06 | `sv_authtoken` is checked as 32 chars only in host migration | Do not infer a working retail auth service |
| R-07 | `tests.c` delta bodies are commented out | Do not claim test coverage from file existence |
| R-08 | Core pmove/trace/game logic are assembly sources, not readable C | Keep source and semantic verification separate |
| I-01 | IW4X has 16 uninitialized submodules | No reproducible build or format-parser claim |
| I-02 | IW4X is injected extension code, not complete standalone server source | Exact host binary is a mandatory layer |
| I-03 | IW4X host binary version is not locked to fixed addresses | Fixed addresses remain unverified |
| I-04 | IW4X rawfiles are assets/runtime distribution | Do not count as server implementation |
| I-05 | `Session.hpp` defines `DISABLE_SESSION` | Default Node/Party path is direct send plus delayed resend; ECC session is not current behavior |
| I-06 | IW4X implements Huffman and RCon/HTTP in source, but host owns netchan/connect/snapshot | Separate extension proof from host proof |
| I-07 | IW4X contains no complete game-logic implementation | Game rules require host RE or independent reconstruction |
| I-08 | Static ABI types/sizes exist, but effective host offsets are unverified | Do not call declarations version-matched evidence |
