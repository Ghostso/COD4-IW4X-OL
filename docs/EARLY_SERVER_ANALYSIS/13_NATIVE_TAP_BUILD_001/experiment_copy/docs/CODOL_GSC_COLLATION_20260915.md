# CoDOL GSC collation into one redistributable root (2026-09-15)

The sh1x server used to resolve GSC from three separate roots on two different
drives. Everything it can load through a script root is now collated into a
single directory:

```
bin\home\codol_rawfiles
```

The launcher points all three script dvars at that one directory. Redistributing
the server is now `bin/` plus the retail CoDOL 1.1.1.13 client install (for the
zones/IWDs); the alpha0022 `vendor/iw4` and `gsc_overlay` trees are no longer on
the server's runtime path.

## 1. What the loader actually does

`src/cscr_parser.cpp:Scr_ReadFile` calls
`src/codol/script/codol_script_source.c:CODOL_ReadScriptSourceWithNativeOverlayForZone`
for every module name the compiler requests. That function probes, in order:

| # | probe | dvar |
|---|---|---|
| 1 | `<native>/<zoneType>/<name>` | `codol_scriptNativeOverlay` (+ `codol_zoneType`: `mp`/`coop`/`zm`) |
| 2 | `<native>/<name>` | `codol_scriptNativeOverlay` |
| 3 | `<overlay>/<name>` | `codol_scriptOverlay` |
| 4 | `<base>/mp/<name>` | `codol_scriptPath` |
| 5 | `<base>/<name>` | `codol_scriptPath` |
| 6 | two exact filename aliases under `<base>` | see `docs/CODOL_SCRIPT_EXPORT_FILENAMES.md` |

First hit wins. A root that is empty or absent is a clean miss (`read_source()`
returns 0 for a NULL/empty root and for `ENOENT`). A file that is unreadable,
larger than 16 MiB, or contains an embedded NUL returns -1, and `Scr_ReadFile`
turns that into `ERR_DROP`. After all probes miss, the engine falls through to
`FS_FOpenFileRead` and then to the mounted fastfile/rawfile reader.

Two consumers outside the compiler also read through `codol_scriptPath`:
`CODOL_LoadReferenceStringTable` (`src/db_load.cpp`, `codol_script_unlock.c`,
`codol_asset_commands.c`) for `.csv` string tables, which is why probe 4's
`mp/` prefix matters — `rankTable.csv` resolves to `mp/rankTable.csv`.

`animtrees/*.atr` are special-cased at the top of `Scr_ReadFile`: a mounted
client archive wins, and the script roots only stand in when no archive defines
the tree.

## 2. Precedence rule

```
scripts/codol        (native overlay, highest)
  > gsc_overlay      (alpha0022 project overlay)
    > vendor/iw4     (alpha0022 IW4 source export)
      > whatever bin/home/codol_rawfiles already held (lowest)
```

This is exactly the loader's own order, so the collated root resolves every
name to the same bytes the three-root configuration did. Newly added CoDOL
logic under `scripts/codol` wins every conflict, as requested.

**Relative paths are preserved verbatim — nothing is flattened.** In
particular:

* `vendor/iw4/mp/**` lands at `codol_rawfiles/mp/**`, so probe 4 still works.
  (Checked: no name exists as both `vendor/iw4/mp/X` and `vendor/iw4/X`, and
  `vendor/iw4/mp/` contains no `.gsc` at all — it is the string-table
  directory.)
* `scripts/codol/zm/**` lands at `codol_rawfiles/zm/**`, so probe 1 still
  routes a `codol_zoneType zm` match to the zombie callbacks/gametype instead
  of the multiplayer ones.

Because every probe keeps its prefix, all three dvars can name the same
directory. Probes 2/3 then become duplicates of each other, and probe 2 (the
highest) fires first, which is the correct precedence in every case.

## 3. Copy set — what "being used" means here

Script resolution is **demand driven**. There is no manifest in the engine: the
requested names come from `#include`, `precacheShader`/model/menu calls, the
gametype and level script names built from the map identity, and per-character
and per-weapon module names built at runtime. A single boot's
`CoDOL lowering: <path>` list (281 distinct names for the last `dm` boot) is a
lower bound for one map and one gametype, not the reachable set — another map,
gametype, character or loadout requests names that boot never touched.

**Rule: carry the full vendor tree, filtered to the extensions a script root can
actually serve.** Extensions copied:

| ext | why | count |
|---|---|---|
| `.gsc` | script modules, `Scr_ReadFile` | 1539 |
| `.csv` | string tables, `CODOL_LoadReferenceStringTable` via `codol_scriptPath` | 86 |
| `.atr` | animation trees, `Scr_ReadFile` animtrees fallthrough | 18 |
| `.def` | structured-data schemas; carried for redistribution only — the loader reads `.def` through `CODOL_LoadMountedStructuredSchema` (mounted client zones), never through a script root | 1 |
| `.csc` | client script modules, same reader | 0 (none ship) |

Everything else in `vendor/iw4` (639 `.menu`, 284 `.vision`, 81 `.cfg`, 64
`.rmb`, 42 `.shock`, weapon files, `.arena`, `.graph`) is client/zone content
that never reaches a script root and is **not** copied.

Files already in `bin/home/codol_rawfiles` whose extension is outside the copy
set are never touched or deleted. That directory is also the developer rawfile
dump target (`src/db_load.cpp`, `FS_SV_HomeWriteFile("codol_rawfiles/%s")`
under `developer 1`), which is where the client's own shipped rawfiles live
(`info/`, `shock/`, `radiant/`, `maps/*.txt`, `mp/playeranim.script` — 36 files,
none of them in the copy set, so there is zero overlap today). If the client
ever mounts a rawfile whose name collides with a collated script, the dump would
overwrite it at boot; re-running the collation restores it.

## 4. Results of this run

```
scanned vendor    1584 loadable files
scanned overlay     52
scanned native      55
total collated    1644   (vendor 1543, overlay 46, native 55)
destination       1682 files / 21 MB  (1644 collated + 36 pre-existing client rawfiles + 2 reports)
conflicts            43
```

Artifacts written into the root itself:

* `COLLATION_MANIFEST.json` — per path: winning source root, absolute source
  path, sha1, byte count, which lower roots it overrode, plus the probe order,
  counts, pruned list and warnings.
* `COLLATION_CONFLICTS.txt` — the human-readable conflict report below.

### Conflicts (path present in more than one root)

43 of 1644 paths. `native` = `scripts/codol`, `overlay` = `gsc_overlay`,
`vendor` = `vendor/iw4`.

| path | won | overrode |
|---|---|---|
| common_scripts/_destructible.gsc | native | vendor, overlay |
| maps/createfx/mp_afghan_fx.gsc | overlay | vendor |
| maps/createfx/mp_overgrown_fx.gsc | overlay | vendor (identical bytes) |
| maps/createfx/mp_rust_fx.gsc | overlay | vendor |
| maps/createfx/mp_underpass_fx.gsc | overlay | vendor |
| maps/mp/_animatedmodels.gsc | native | vendor |
| maps/mp/_awards.gsc | native | vendor |
| maps/mp/_entityheadicons.gsc | native | vendor |
| maps/mp/_flashgrenades.gsc | native | vendor |
| maps/mp/_load.gsc | native | vendor |
| maps/mp/_scoreboard.gsc | native | vendor |
| maps/mp/_utility.gsc | native | vendor |
| maps/mp/gametypes/_class.gsc | native | vendor |
| maps/mp/gametypes/_damage.gsc | native | vendor |
| maps/mp/gametypes/_gamelogic.gsc | native | vendor |
| maps/mp/gametypes/_hud_message.gsc | native | vendor |
| maps/mp/gametypes/_menus.gsc | native | vendor |
| maps/mp/gametypes/_missions.gsc | native | vendor |
| maps/mp/gametypes/_music_and_dialog.gsc | native | vendor |
| maps/mp/gametypes/_persistence.gsc | native | vendor |
| maps/mp/gametypes/_playercards.gsc | native | vendor |
| maps/mp/gametypes/_playerlogic.gsc | native | vendor |
| maps/mp/gametypes/_rank.gsc | native | vendor |
| maps/mp/gametypes/_spawnlogic.gsc | native | vendor |
| maps/mp/gametypes/_teams.gsc | native | vendor |
| maps/mp/gametypes/_weapons.gsc | native | vendor |
| maps/mp/gametypes/war.gsc | native | vendor |
| maps/mp/killstreaks/_ac130.gsc | native | vendor |
| maps/mp/killstreaks/_airstrike.gsc | native | vendor |
| maps/mp/killstreaks/_autosentry.gsc | native | vendor |
| maps/mp/killstreaks/_emp.gsc | native | vendor |
| maps/mp/killstreaks/_harrier.gsc | native | vendor |
| maps/mp/killstreaks/_helicopter.gsc | native | vendor |
| maps/mp/killstreaks/_killstreaks.gsc | native | vendor, overlay |
| maps/mp/killstreaks/_uav.gsc | native | vendor |
| maps/mp/mp_afghan_fx.gsc | overlay | vendor |
| maps/mp/mp_fav_tropical.gsc | native | overlay |
| maps/mp/mp_killhouse_sh.gsc | native | overlay |
| maps/mp/mp_overgrown_fx.gsc | overlay | vendor |
| maps/mp/mp_rust_fx.gsc | overlay | vendor |
| maps/mp/mp_underpass_fx.gsc | overlay | vendor |
| maps/mp/perks/_perkfunctions.gsc | native | vendor, overlay |
| maps/mp/perks/_perks.gsc | native | vendor, overlay |

Only one conflict is a no-op (`maps/createfx/mp_overgrown_fx.gsc`, identical
bytes in overlay and vendor). Every other conflict is a real override, and in
all 43 the winner is the same file the three-root loader was already choosing.

### Warnings carried over from the vendor export

Three vendor `.gsc` files contain an embedded NUL and are rejected with
`ERR_DROP` by `read_source()` **if a script ever requests them**:

* `maps/mp/_menus.gsc`
* `maps/mp/gametypes/_clientids.gsc`
* `maps/mp/gametypes/_hardpoints.gsc`

This is unchanged by the collation — the same bytes were in `vendor/iw4` and
would have failed the same way. None of them is on the current boot path
(`scripts/codol/maps/mp/gametypes/_menus.gsc` is a different module name and
wins its own path).

## 5. Verification (offline, no server started)

`bin/codol_dedrun_next.exe --codol-info` was run: it prints a **static build
banner and returns before `Com_Init`** (`src/sys_main.c:466`). It does not open
sockets, load assets, or validate script roots — so it verifies nothing about
this change. There is no script-parse CLI in the tree either
(`tests/test_codol_script_source.c` and `tests/test_codol_script_lower.cpp` are
unit fixtures, not file drivers).

`tools/verify_gsc_collation.py` therefore does the verification offline by
replaying the loader's probe order in Python:

```
python tools/verify_gsc_collation.py            # zone mp
python tools/verify_gsc_collation.py --zone zm  # zone zm
```

Result for both zones:

```
[1] manifest integrity: 1644 files, 0 missing, 0 sha1 mismatches
[2] boot logs: 281 distinct 'CoDOL lowering:' module names
[3] resolution parity over 1646 names: 1643 identical, 0 differing,
    0 lost, 0 new-only, 3 rejected by both
[4] every logged lowering path resolves in the collated root: 0 unresolved
[5] source admissibility: 1557 checked, 3 embedded NUL, 0 unbalanced, 0 oversize
OK
```

Check [3] is the strong one: for every module name the server actually requested
(harvested from `bin/home/main/qconsole.log` and `.log.old`) **and** every path
in the manifest, it resolves the name twice — once against the old three roots
and once against the collated root — and compares the returned bytes. 0
differing, 0 lost. The 3 "rejected by both" are the embedded-NUL vendor files
above, which behave identically before and after.

Check [5] is a structural pre-check (16 MiB limit, embedded NUL, brace/paren
balance outside strings and comments), not the real lowering pass, which is C++.

## 6. Re-running

The tool is idempotent: it hashes before writing, so a re-run with no upstream
changes reports `copied 0 / updated 0 / unchanged N`.

```
python tools/collate_gsc.py                  # sync all three roots into the collated root
python tools/collate_gsc.py --dry-run        # report only, write nothing
python tools/verify_gsc_collation.py         # parity + integrity check
```

Useful flags: `--repo`, `--reference`, `--vendor`, `--overlay`, `--native`,
`--dest` to relocate any root; `--no-prune` to keep files that vanished
upstream; `--quiet` to suppress the per-file lines.

Pruning: a file this tool previously wrote that no longer exists in any root is
deleted on the next run — but **only** when its bytes still match the sha1 in
the previous manifest. A hand-edited or client-dumped file is never removed; it
is reported as a warning instead.

**The other agents are still adding GSC under `scripts/codol`.** The native root
grew from 51 to 55 files during this pass alone. Re-run `tools/collate_gsc.py`
as the final sync after they finish, and again any time `scripts/codol`,
`gsc_overlay` or `vendor/iw4` changes — otherwise the server runs the stale
collated copy, because it no longer reads those roots.

## 7. Launcher change

`bin/START-CODOL-SERVER.cmd` now sets:

```
if not defined CODOL_SCRIPTS set "CODOL_SCRIPTS=%CODOL_HOME%\codol_rawfiles"
...
  +set codol_scriptPath        "%CODOL_SCRIPTS%" ^
  +set codol_scriptOverlay     "%CODOL_SCRIPTS%" ^
  +set codol_scriptNativeOverlay "%CODOL_SCRIPTS%" ^
  +codol_scriptPath ^
  +codol_scriptOverlay ^
  +codol_scriptNativeOverlay ^
```

The pre-collation three-root form is kept verbatim in comments above the launch
block, and the untouched original is `bin/START-CODOL-SERVER.cmd.pre-collate`.
The startup guard now checks for
`%CODOL_SCRIPTS%\maps\mp\gametypes\_callbacksetup.gsc` instead of
`%CODOL_REFERENCE%\vendor\iw4`. `CODOL_REFERENCE` is still required, but only
for `securitykey.bin`, `startgame.txt`, `native_server_rcon.txt` and
`resources/` — not for scripts.

The patched launcher was parse-tested end to end with the executable stubbed
out; the emitted command line is correct and `errorlevel` is 0.

### Confirming it on the next deploy

**The server was not started — another agent owns deploy.** The next launch of
`bin/START-CODOL-SERVER.cmd` picks up the collated root automatically.

The loader itself does not print its roots, so the three `+codol_script*` bare
cvar commands were appended to the command line: a bare cvar name is a console
print (`Cvar_Command`, `src/cvar.c:1652`). Confirm in
`bin/home/main/qconsole.log` that these three lines appear, all naming the same
directory:

```
"codol_scriptPath" is: "bin\home\codol_rawfiles" default: ""
"codol_scriptOverlay" is: "bin\home\codol_rawfiles" default: ""
"codol_scriptNativeOverlay" is: "bin\home\codol_rawfiles" default: "scripts/codol"
```

(The launcher console also echoes
`  scripts   bin\home\codol_rawfiles  (collated single root)`
before the process starts.)

The functional confirmation is the usual `CoDOL lowering:` block in
`qconsole.log` — it must list the same ~281 modules as before, with no
`CoDOL external script ... is unreadable or invalid source` and no
`script compile error: could not find script`.

## 8. Redistribution

The server now needs:

* `bin/` — `codol_dedrun*.exe`, `START-CODOL-SERVER.cmd`, and
  `bin/home/codol_rawfiles/` (every GSC, string table and animtree it can
  resolve, 21 MB).
* the retail **Call of Duty Online 1.1.1.13 client install**, for `fs_basepath`
  (zones, IWDs, fastfiles).
* the alpha0022 lobby directory, only for the live-session files the launcher
  reads from it: `securitykey.bin`, `startgame.txt`, `native_server_rcon.txt`,
  `resources/`.

`vendor/iw4` and `gsc_overlay` are no longer runtime dependencies. They remain
the **sources of truth** — edit `scripts/codol` (or the overlay) and re-run
`tools/collate_gsc.py`; do not hand-edit files inside `codol_rawfiles`, because
the next collation overwrites anything whose upstream copy differs.
