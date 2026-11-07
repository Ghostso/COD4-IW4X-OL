# EX-013-IW4X Map

## IW4X startup stages (known public architecture, concise)

1. WinMain / Process Entry -> Common init (`Com_Init`, command line, `com_error`, `Com_Error`).
2. Common/System init -> OS, security, thread setup.
3. Filesystem init -> `FS_Init`, root paths, `main/`, `players/`, archive handles.
4. Database/asset system -> `DB_Init`, fastfile loading (`code_post`, `localized_*`, map `.ff`).
5. Renderer init -> D3D9/GFX, resource managers (`Renderer`, TextureManager, etc).
6. Game/UI init -> game modules, UI shell, menu state.
7. Engine main loop -> frame, cmd, render, net.
8. Network -> client/server session, host connection.

## CODOL mapping

| IW4X stage | CODOL evidence | Level |
|---|---|---|
| Process Entry / Common init | EXE Entry `0xE5DC690` -> Base ordinal 1; strings `Initializing...`, `COM_FATAL_ERROR`, ports | CONFIRMED for entry, PROBABLE for common init |
| System/security/runtime init | Base auto-init, `.tvm0`, locale crash; TenSafe/TP strings | PROBABLE |
| Filesystem | `main/video/*.bk2`, `main/demo/*.demo`, `players/config_mp.cfg`, `players/*.iw4`, `IIPS\\IIPSDown...`, `%s.lst` | PROBABLE |
| Database/asset | `main\\%s`, `main\\%s_%s`, TCLS `ifs_file`, `%s_test.lst` | PROBABLE |
| Renderer | EXE strings `Renderer`, `RenderPipelineManagement`, `MeshCacheManagement`, `TextureManager`, `MatrixPool`, `Font` | PROBABLE (string-level only) |
| Game init | `config_mp.cfg`, `settings_*.iw4`, `CODO_logo.bk2`, game/title strings | UNKNOWN (no runtime entry) |
| Engine/UI module | CEF/libcef, Scaleform exports, CODO web/UI strings | PROBABLE |
| Network | EXE network port strings (`2241/2296/2297/2298/2299/2300/2301`), `WS2_32`, sock census | PROBABLE |

## Most likely Game Bootstrap

Evidence: `config_mp.cfg`, `settings_m.zip.iw4`, `settings_c.zip.iw4`, `main/video/*.bk2`, `main/demo/*.demo`, map/UI asset layout.
Level: PROBABLE architecture, UNKNOWN runtime address because code is behind VM.

## Most likely Renderer/FS

Evidence: EXE data includes `Renderer`, `RenderPipelineManagement`, `MeshCacheManagement`, `TextureManager`, `MatrixPool`; filesystem assets in `main/` and `players/`.
Level: PROBABLE by asset/string alignment, not confirmed code entry.

## Most likely Network

Evidence: port strings `2241..2301`, WS2_32 thunk census, server/client architecture strings.
Level: PROBABLE by IW4 convention and binary inventory, UNKNOWN runtime path.

## CODOL currently missing stages

Base ordinal 1 crashes before returning, so no confirmed runtime node for FS/DB/Renderer/Game/Network has been observed. The mapping can locate likely assets but cannot bypass the missing VM/system init return.

## Next dynamic target

Stop targeting `Base+0x306A`. Next target: locate the point inside Base ordinal 1 after CRT/locale init where main/common startup resumes and first touches `players/config_mp.cfg`, `main/`, `settings_*.iw4`, or filesystem/archive APIs. That FS/first-asset access will be the concrete post-locale bootstrap node.

## IW4X study import (2026-09-16)

Source ingested:
`F:\下载\ChatGPT-IW4X架构研习-20260916-2018.md`

Key facts used for CODOL direction:
- IW4X is not a rewritten engine; it is original binary + hooks/patches/extensions.
- IW4X initialized inside DLL_PROCESS_ATTACH before original CRT startup: DEP policy, binary check, entry hook, `Main::EntryPoint`, security cookie, environment, platform proxy, cryptography, components loader.
- Semantic function table pattern: `FunctionName = FunctionType(0xADDRESS)`. This is the strongest search pattern for CODOL Base/EXE.
- FS and DB are separate layers. `CreateFile/ReadFile` implies filesystem, not asset loading.
- Asset load path expected: Zone/Stream -> `DB_*StreamPos` -> `Load_Stream` -> type-specific serializers -> pointer/string/asset fixups -> runtime asset -> asset DB/lookup.
- Client state should be split into connection/static/UI/active/CG/CGS/entity rather than one blob.
- Network expected via `CL_ConnectFromParty`, `CL_ParseGamestate`, `CL_ParseSnapshot`, `CL_ParseServerMessage`, `CL_AddReliableCommand`.

Implication for CODOL experiments:
Stop treating `Base+0x27E3B0`/`Base+0x2928AC`/`Base+0x306A` as asset/FS errors. They remain Base runtime/locale startup symptoms until proven otherwise.
Next CODOL static search should look for semantic-table style mappings (`mov eax,0xADDRESS` or `Type(0xADDRESS)` clusters) matching IW4-style FS/DB/Renderer/Network calls, not single string hits.
