# CoDOL server source layout

Restructured 2026-09-09. Every CoDOL-specific source file now lives under
`src/codol/<area>/`; the retained IW4OL engine stays flat in `src/` and its
disassembled functions in `src/asmsource/`. File names were not changed, so
`grep codol_dive` still finds the same file, and `#include "codol_x.h"` keeps
working from anywhere because every area directory is on the include path.

## Where things are

| path | what lives there |
|---|---|
| `src/*.c`, `src/*.cpp`, `src/*.h` | retained IW4OL engine (server loop, netchan, filesystem, script VM, game logic). CoDOL hooks into it are guarded by `#ifdef CODOL_SERVER`. |
| `src/asmsource/*.asm` | retained IW3 functions kept as assembly (pmove, mantle, animation, weapons, game entities). CoDOL calls are inserted as `call CODOL_*`. |
| `src/codol/net/` | client transport: DTLS/handshake, ECDH, association, connect, netchan framing, wire codec, pure check. |
| `src/codol/snapshot/` | everything published to the client each frame: native frame builder, snapshot writer and history, delta codec, player/entity/client/actor field tables (`*_fields.inc`), engine-state overlays (`codol_engine_state.c`), events and the event map, config strings, HUD and radar wire state. |
| `src/codol/player/` | input and movement: usercmd decode, dive, sprint and recoil state, perks and abilities, stance/animation tables (`codol_animation_*.inc` are also included by `_bg_animation_mp.asm`), spectate defaults, use hints, loop sounds, team fx. |
| `src/codol/weapon/` | weapon composition from attachments, weapon registry and loader, weapon state machine, weapon locks and missiles, turret heat, server weapon config strings. |
| `src/codol/vehicle/` | vehicle assets, native vehicle simulation, spawner. |
| `src/codol/script/` | GSC builtins added for CoDOL scripts (`codol_script_<topic>.c`), the syntax-lowering pass (`codol_script_lower.cpp`), precache, profile/loadout access, menus, startup shims. |
| `src/codol/assets/` | fastfile and IWD reading, asset registry and streaming, xmodel/xsurface/xanim/material/sound/effect natives, character composition, string tables, shock rawfiles, map custom data. |
| `src/codol/collision/` | BSP collision (brushes, leaves, terrain, static models, materials), world planes, physics, dynamic entities, triggers, map entity string. |
| `src/codol/stats/` | secure profile (read only), experience/challenge/unlock rules, skill rating, match data and its wire format, scoreboard, structured data schema. |
| `scripts/codol/maps/mp/...` | native GSC adaptations that override the alpha0022 `gsc_overlay` and the IW4 vendor scripts (`_class`, `_menus`, `_teams`, `_gamelogic`, `_missions`, `_playercards`, ...). |
| `bin/START-CODOL-SERVER.cmd` | launcher (developer 1, port 17733, script paths); log at `bin/home/main/qconsole.log`. |
| `tests/test_codol_*.c|.cpp|.py` | unit tests, run by `make test-codol` under WSL. |
| `tools/` | offline helpers (`codol_archive.c`, `codol_event_map.py`). |
| `docs/CODOL_*.md` | design notes per subsystem; `CODOL_IMPLEMENTATION_PASS.md` is the running log, `CODOL_PLAYER_ACTION_AUDIT.md` the per-action status, `CODOL_PARITY_PLAN.md` the gap list. |

## Build rules

- The makefile lists the areas in `CODOL_AREAS`; `C_SOURCES`/`CPP_SOURCES`
  glob each area, objects stay flat in `$(OBJ_DIR)`, and `CODOL_INC` adds
  `-Isrc` plus every area directory to `COMMON_FLAGS`.
- Adding a file: drop it into the area it belongs to. Nothing else is needed for
  the server build. File names must stay unique across areas (objects are flat).
- Adding an area: create the directory and append its name to `CODOL_AREAS`.
- Unit tests in `test-codol` name their sources explicitly
  (`src/codol/<area>/codol_x.c`); the Python tests build the include list from
  `src/codol/*` at run time (`CODOL_INCLUDE`).
- Cross-build from WSL:
  `make -j8 -k OS=Windows_NT CC=i686-w64-mingw32-gcc CPP=i686-w64-mingw32-g++ AR=i686-w64-mingw32-ar OBJ_DIR=obj/codol-win32 bin/codol_dedrun.exe`
  (stop `codol_dedrun.exe` first or the link cannot open the output file).

## Naming inside an area

- `codol_<topic>.c` holds the engine-facing logic; `codol_<topic>_native.c`
  parses the raw asset or BSP format; `codol_<topic>_wire.c` is the client
  encoding; `codol_sv_<topic>.c` is the server-frame glue; `codol_script_<topic>.c`
  is the GSC builtin surface.
- Developer traces are prefixed `CoDOL <topic>:` in the console log so a paste
  can be grepped by subsystem (`CoDOL pacing`, `CoDOL rov`, `CoDOL mantle`,
  `CoDOL spawn`, `CoDOL field audit`, `CoDOL reliable ->`).
