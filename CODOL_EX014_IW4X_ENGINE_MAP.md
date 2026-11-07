# EX-014-IW4X-MAP

## Goal

Use IW4X public architecture as a reference to list CODOL engine bootstrap candidates, without investigating `0x306A`, locale, TenProxy, or `.tvm0` internals.

## IW4X Reference

`DllMain`/`EntryPoint` chain confirmed from IW4X source:
```text
DLL_PROCESS_ATTACH
  -> Binary Check
  -> Hook original entry
  -> Main::EntryPoint
     -> security cookie
     -> Initialize()
        -> srand
        -> SetEnvironment
        -> platform proxy
        -> Cryptography
        -> Components::Loader
  -> original __tmainCRTStartup
```

Semantic functions relevant to engine later stages:
- `NET_Init`
- `CL_IsCgameInitialized`
- `CL_ParseGamestate`
- `CL_ParseSnapshot`
- `CL_ParseServerMessage`
- `DB_*StreamPos` / `Load_Stream` for FS/DB
- `FS_ReadFile` / `FS_*` for filesystem layer distinct from DB layer
- `R_*` / graphics globals for renderer layer

## CODOL Candidate Table

| IW4X Stage | CODOL Candidate | Evidence |
|---|---|---|
| Entry/CRT | EXE Entry `0xE5DC690` -> `Base ordinal 1` (`Base+0x1D6582C`) | CONFIRMED by dynamic breakpoint; Base export ordinal 1 called before returning |
| Runtime Init | Base ordinal 1 / Base auto-init `.tvm0`, locale/CRT path, TenSafe/TP strings | PROBABLE; no clean runtime function recovered |
| FS/Asset | `main/video/*.bk2`, `main/demo/*.demo`, `players/config_mp.cfg`, `players/settings_*.iw4`, `%s.lst`, TCLS `ifs_file`, `IIPS` strings | CONFIRMED asset layout; UNKNOWN code entry |
| Renderer | EXE strings `Renderer`, `RenderPipelineManagement`, `MeshCacheManagement`, `TextureManager`, `MatrixPool`, `Font` | PROBABLE string-level only |
| Game | `config_mp.cfg`, `settings_*.iw4`, `CODO_logo.bk2`, Scaleform/CEF UI | PROBABLE by assets; UNKNOWN runtime |
| Network | EXE port strings `2241..2301`, WS2_32 census, `Net`/`Network` strings | PROBABLE by convention; UNKNOWN entry |
| Main Loop | CEF/libcef, Scaleform, dynamic windows, fatal error UI | UNKNOWN; not reached |

## Most likely CODOL original-engine startup completion candidate

Observations:
- CODOL entry is externally a VM thunk (`EXE Entry -> Base export ordinal 1 -> .tvm0`).
- `GameBabyConfig.dat` explicitly names `codoMP_client_shipRetailBase.dll`, `TenSLX.dll`, `TerSafe.dll` as ignored DLLs for FPS checks, which is consistent with Base being a runtime/bootstrap layer.
- IW4X architecture maps best onto: Base ordinal 1 is the CODOL analog of IW4X `Main::EntryPoint -> Initialize -> Component Loader`, before CRT/engine resume.

Verdict:
- CODOL candidate for original engine startup completion = the point after Base ordinal 1 returns and original `codoMP_client_shipRetail.exe` engine code begins.
- Since that entry is behind `.tvm0`/VM boundary, no plain `.text` entry is reachable yet.

## Frozen topics

`Base+0x306A`, locale object provenance, `EXE+0x184F5E`, `CA8150/CA8158`, TenProxy, and `.tvm0` internals are frozen.

## Next dynamic target

Do not patch `Base+0x306A`. Instead locate the first post-Base filesystem/asset access: trace `CreateFileW`/`ReadFile`/`FindFirstFileW` callers after Base autos, filtering for `players/`, `main/`, `*.ff`, `*.iwd`, `config_mp`, `settings_*.iw4`; that caller is the strongest CODOL FS/Asset bootstrap candidate beyond Base.
