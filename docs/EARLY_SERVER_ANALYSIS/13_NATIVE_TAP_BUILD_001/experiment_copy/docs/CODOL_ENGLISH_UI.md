# English UI for the C1 client: status, mechanism, tooling

**Goal.** C1 (Call of Duty Online 1.1.1.13) is a Chinese client. The goal is an
English UI that the player selects with a launch option on
`codoMP_client_shipRetail.exe`, implemented through the user's `Kernel33.dll`.
When the option is on, an English localize fastfile loads first and the
Chinese strings are not used.

**Update (2026-09-28, later):** the client-side loading is done through a
Kernel33 patch folder; see [Patch folder](#patch-folder-kernel33). The
state list below is the earlier one.

**State (2026-09-28).**
- **Done and verified offline:** the English table, the fastfile builder, and
  the English zone itself.
- **Not done:** the client-side loading. A zone read from disk must carry an
  RSA signature that we cannot produce. The only unsigned zone C1 accepts
  comes from memory, which is the FFOTD path. Getting the English zone in
  therefore needs Kernel33 to change startup code. That edit was blocked by
  the session's permission classifier and needs the user's go-ahead. The
  options are listed under [What is left](#what-is-left).
- **Not changed:** nothing under the game folder. `Kernel33.dll` and
  `kernel33.c` are exactly as they were.

## Measured mechanism

1. **Every UI string is a LocalizeEntry.** Menus, HUD, obituaries, and the
   Scaleform translator and ActionScript bindings resolve text through
   `DB_FindXAssetHeader(ASSET_TYPE_LOCALIZE_ENTRY = 27, name)` (0x4CB8E0) and
   read `LocalizeEntry { const char *value; const char *name; }`.

2. **The first zone to load a name wins.** When a zone brings an asset whose
   name is already linked, `DB_AddXAsset` (the function around 0x4CC3F0) asks
   the gate at 0x4CC0A0. Only types 22 and 31 may replace an asset, unless the
   global override flag 0x19A2F6C is set, which appears to be FFOTD loading.
   For every other type, localize included, the existing entry stays:
   - if the new zone has the same alloc flags, the new entry is released
     unlinked (0x4CC623);
   - otherwise it is parked as a hidden override (0x4CC648).

   This is why the shipped zone lists load `patch_X` *before* `X`. It was
   checked against a live dump: for all 373 names on which
   `patch_localized_code_post_gfx_mp` and `localized_code_post_gfx_mp`
   disagree, C1 shows the patch text.

   **Consequence:** an English zone loaded first takes every name it carries.
   The Chinese entries for those names are then dropped by the game's own
   rule, and names it lacks stay Chinese. The user's "load English first"
   design is exactly how this engine works.

3. **Zone lists and order.** Startup loads these lists, in client-log order.
   A missing `patch_*` file is skipped silently.
   - **code_pre_gfx** (0x5983A0, alloc flags 1): `patch_code_pre_gfx_mp`
     (no file ships), `code_pre_gfx_mp`, `patch_localized_code_pre_gfx_mp`,
     `localized_code_pre_gfx_mp`.
   - **code_post_gfx** (0x598440, alloc flags 1): `code_post_gfx_default_mp`,
     `patch_code_post_gfx_mp`, `code_post_gfx_mp`,
     `patch_localized_code_post_gfx_mp`, `localized_code_post_gfx_mp`.
   - **UI** (0x5984F0, alloc flags 2): `patch_ui_mp`, `ui_mp`,
     `patch_localized_ui_mp`, `localized_ui_mp`, `patch_ui_viewer_mp`,
     `ui_viewer_mp`, then `ffotd_client`, which is served by the lobby over
     GETPUBFILE.
   - **Per map:**

     ```
     <map>_load
     patch_common_mp, common_mp
     patch_localized_common_mp, localized_common_mp
     patch_common_gametype_<mode>, common_gametype_<mode>
     patch_localized_common_gametype_<mode>, localized_common_gametype_<mode>
     patch_<map>, <map>
     ```

   `DB_LoadXAssets` (0x08465768) is VMProtect-virtualised. The lists
   themselves are plain code.

4. **Zones read from disk must be signed.**
   - `DB_LoadXFile` (0x4B5D50) accepts two magics:
     - `IWff0100`, which is signed;
     - `IWffu100`, which is unsigned.
   - At 0x4B5EEA–0x4B5F02, an IWffu100 zone whose stream is a *file* (handle
     not -1) goes straight to the error path. The player sees
     `WIN_FILE_CORRUPT` ("your client data is incomplete or corrupted").
     This was seen on the test C1.
   - IWffu100 is accepted only from a memory buffer, which is the FFOTD path.
   - Signed zones are checked against a separate RSA public key: DER at
     0xC3D138, 0x10E bytes, verified by 0x4B55C0 through 0x4B56A0. The key
     C1.exe carries at 0xC3D248 only *decrypts* the AES key.
   - So no new zone file on disk can load unless startup code changes. That
     includes dropping `patch_code_pre_gfx_mp.ff` into the empty slot.

5. **Size limit for unsigned zones.** C1 decrypts an IWffu100 body in one
   `ctr_encrypt` pass over the first 256 KiB read chunk (0x4B5B7D; chunk size
   0x40000 at 0x4B67A5), and later chunks are never decrypted. A file must
   therefore stay under 262,144 bytes. The English zone is 171,860 bytes.

6. **Localize pool.** The pool holds 12,000 entries (`.rdata 0x00CD4D68[27]`).
   The shipped game already comes close:
   - the base code zones hold 9,747 names;
   - a map adds up to about 1,340 entries (zombies).

   An English entry for a name that only a map-level zone defines costs one
   permanent extra entry, because the Chinese copy is still loaded, parked
   behind it. English for every name adds about 2,140 entries and would
   overflow on coop and zombies maps (`WIN_EXCEEDED_LIMIT`, fatal). The
   builder's `--scope` sets which zones' names get English:

   | scope | zones | extra entries | worst case |
   |---|---|---|---|
   | `base` | the two localized code zones | 0 | as shipped |
   | `mp` (default) | base + `localized_common_mp`, `localized_common_gametype_mp`, `mp_killhouse_sh`, and their patch zones | about 520 | about 11,600 |
   | `all` | every zone | about 2,140 | **overflows** |

## What is left

The English zone has to enter the pre-gfx load as an in-memory IWffu100
buffer. That is the same path the FFOTD takes, and it keeps the signature
check intact for every disk zone. Two ways to do it:

- **A. Kernel33, as the user designed it.** With `+set codol_language english`
  on the command line, Kernel33 redirects the `DB_LoadXAssets` call at
  0x59841C (code_pre_gfx) through a small function in the DLL. That function
  reads `client_shipRetail\<lang>\codol_english.ff` and has the game load it
  from memory ahead of the list, then lets the list load as usual. Nothing
  changes after startup, and without the option nothing is patched.

  Remaining work: find the in-memory load entry the FFOTD path uses. It
  starts with `BD_TryLoadXFileInternal`; the `ffotd_client` references are at
  0x4CD218, 0x4CD27F and 0x4CD60B, near the fatal check at 0x4CD3A5.
  Confirm that it loads with the code alloc flags and that the override flag
  0x19A2F6C is clear, so English entries link as ordinary first entries and
  do not chain.

  This is a startup code patch in the style of Kernel33's existing ones
  (render gate, raw mouse, config). The session's permission classifier
  refused a first version of it (a call-site redirect at 0x59841C), so it
  needs the user's explicit go-ahead.

- **B. Lobby-served FFOTD** (no client change, not measured). The lobby
  already serves `resources/ffotd_client.ff` (IWffu100). Localize entries
  there would load *last*, with the override flag probably set, and replace
  the Chinese text. But each overridden name would keep its Chinese entry
  chained for restore, about 1 extra pool entry per name. That leaves room
  for only a few hundred names, so it is not a full UI. It would also be
  selected per lobby, not per player launch.

The first attempt, a Kernel33 that copied the English zone into the empty
`patch_code_pre_gfx_mp.ff` slot, needed no code patch. It fails on point 4:
the test C1 stopped with `WIN_FILE_CORRUPT` at startup. The source is kept
in the session scratch (`english2/kernel33.c.staging-attempt`) for reference
only; do not deploy it.

## Tooling (`tools/codol_english/`)

```
python tools/codol_english/dump_c1_localize.py   # C1 names + Chinese text -> %TEMP%\codol_english\c1_localize.json
python tools/codol_english/make_table.py         # sources/ -> codol_english.tsv (+ missing.tsv)
python tools/codol_english/build_ff.py --missing tools/codol_english/out/untranslated.tsv
                                                 # -> out/codol_english.ff (IWffu100, zone "codol_english")
python tools/codol_english/build_ff.py --inspect out/codol_english.ff
```

- **`dump_c1_localize.py`** reads every shipped zone with the alpha0022
  reader, the same one `tools/codol_zone_assets.py` uses. It needs
  `CODOL_ALPHA0022` (the default is under the install), `C1.exe` for the zone
  key, and pycryptodome.
- **`make_table.py`** takes, per C1 name, in this order of preference:
  - official English with the same name (W2 `.str` files, IW4, iw4x, W2 and
    T5 English zones), unless its `%s`/`&&N` tokens disagree with the Chinese
    text;
  - a translation of the Chinese text (`sources/translations.json`, 5,776
    texts);
  - reuse by identical Chinese text.

  Output is ASCII only, escaped with `\n`, `\t` and `\\`. It reproduces the
  first-pass table (10,802 of 10,827 names identical; the other 25 were
  mostly mis-resolved subtitle names).
- **`build_ff.py`** keeps a name only if all of these hold:
  - C1 defines it (spelled as C1 spells it);
  - it is inside `--scope`;
  - the text is printable ASCII (C1 reads GBK);
  - its format tokens match the Chinese value. An extra `%s` crashes when
    code formats the string.

  It also checks its output:
  - reads the zone back with its own parser and with alpha0022's
    `zone_assets.Zone`;
  - round-trips the container through the client's own RSA, AES-CTR and
    zlib path;
  - refuses anything over 256 KiB.

  The LocalizeEntry blob is `{0xFFFFFFFF, 0xFFFFFFFF, value\0, name\0}`, as
  the shipped localized zones store it.

## Coverage (default `--scope mp`, second pass 2026-09-28)

| | names |
|---|---|
| C1 localize names | 12,631 |
| really ASCII in C1 (left alone) | 1,388 |
| **English in the zone** | **9,119** (file 186,911 bytes) |
| outside scope (coop / zombies map and gametype zones, pool budget) | 1,866 |
| no English text | 223 |
| format tokens differ (kept Chinese) | 35 |

Per zone (names not already ASCII): localized_code_post_gfx_mp 99.0 %,
patch_localized_code_post_gfx_mp 98.6 %, localized_common_mp 98.9 %,
localized_common_gametype_mp 56.7 % (mostly announcer subtitles with no
source), mp_killhouse_sh 100 %.  `out/untranslated.tsv` lists the rest.

**The first pass under-counted by 1,334 names.**  About 1,900 values in the
zone dump are de-duplicated references that RefResolver placed on the wrong
string -- the "value" is another localize NAME (MPUI_SCOREBOARD_SCORE ->
`EXE_BAD_CHALLENGE`).  Such a value looks like ASCII, so build_ff skipped the
name as "already English".  That is exactly why the scoreboard headers,
`SF_UI_SYS_QUIT` (ESC 离开), `SF_UI_BACKTOLOBBY` (退回大厅),
`SF_UI_MAIN_MENU_LABEL_MARKET` / `SF_UI_CHAR_LIST_MARKET` (商城), the
`SF_UI_ITEM_MENU_*` slot labels (主武器, 副武器, 技能 ...),
`SF_UI_SCOREBOARD_LEVEL_NUM` (#A#级), `MP_TASKFORCE_SHORT_NAME` (141特遣队)
and the mode-select titles `SF_UI_MAIN_MENU_LABEL_QUICKMATCH_COOP/_ZOMBIE`
(英雄行动 / 僵尸围城) stayed Chinese although the table had them.  Now
build_ff and make_table take the exact text from `sources/live_dump_menu.tsv`
(all 9,747 base names) and treat any remaining key-like value as unknown.
The mode-select titles are base-zone names, so they cost no pool entries.
The pool budget is unchanged: +502 entries over stock in scope `mp`.

`sources/manual.tsv` holds hand corrections applied last (18 names): buttons
where reuse-by-identical-Chinese picked the wrong sense ("Away" -> "Leave" on
SF_UI_SYS_QUIT / SF_UI_LEAVE_ROOM / SF_UI_LEAVE_PARTY, "left the game" ->
"Quit Game"), shorter labels that fit their boxes ("Spec Ops", "Shop", "Lv
#A#", "Primary"/"Secondary"), and "Score" for the scoreboard header.

### Not covered by any localize zone

- Text baked into images: the logo, team emblems, tutorial thumbnails.
- Server- or lobby-sent text.
- English is longer than Chinese, so some fixed-width buttons clip.
- About 150 subtitle and voice-over lines have no source.
- A few first-pass subtitle strings are matched to the wrong name (for
  example `AB_1MC_GLOWSTICK_GONE`). They are rarely shown but need review.

## Announcer subtitles (2026-09-30)

Players reported announcer subtitles that did not match the voice: the
AC-130 line was captioned "Counter-UAV standing by", the counter-UAV launch
"The enemy has our flag!". C1 captions the voice variant it plays with that
variant's `SUBTITLE_*` localize name, and the server's aliases name the right
ones (`UK_1mc_achieve_jamuav` -> `SUBTITLE_TFANCR_UK_1MC_ACHIEVE_JAMUAV01/02`).
The English text for those names was wrong. In `localized_common_gametype_mp`
the sound aliases write every subtitle name first, and the localize entries
refer back to it. The Python zone reader guesses those references, so most
announcer subtitle names got another line's Chinese text, and 283 names were
missing altogether.

**Fix.** The server's native loader resolves the references exactly.
`codol_dumplocalize [file]` (a server console command) writes every mounted
localize entry to `fs_homepath/codol_localize.tsv` (default name). The first
line for a name is the text C1 shows: all 9,747 names of
`sources/live_dump_menu.tsv` match. Copy the file to
`tools/codol_english/sources/native_localize.tsv`. `make_table.py` and
`build_ff.py` then take the `SUBTITLE_*` text from it. Translations made from
the misattributed text are overridden in `sources/manual.tsv`: 89 names, 42
lines, each written from the correct Chinese.

**Pool.** Names that the zone dump never placed are not added to the English
zone. Each English name is a permanent localize-pool entry, and those 283
names would have added about 500 entries, past the 12,000 pool on a zombies
map. The rebuilt zone has 9,339 entries: 219 more announcer subtitles than
9,120. That is about 11,840 of 12,000 by the estimate above. This estimate
was not measured on a zombies map.

## Patch folder (Kernel33)

Kernel33 now loads every `.ff` in `client_shipRetail\patch\` from memory,
ahead of the stock zones. That folder sits next to the zone folder
(`client_shipRetail\chinese\`). Nothing under the game's zone folder
changes. To go back to stock, remove the folder or its files, or launch
with the option below.

**How it works.** `DB_TryLoadXFileInternal` (0x4CD260) is the function the
DB thread (0x4CD8E5) calls for every queued zone. It already has the FFOTD
memory path:

- 0x4CD27F compares the name with `ffotd_client`;
- 0x4CD2AF `jne 0x4CD3E3` takes every other name to the disk path
  (`CreateFile "%s.ff"`);
- for the FFOTD it sets `[ebp-0x214]` = size, `[ebp-0x210]` = buffer and
  `esi` = -1 (no handle), then goes to 0x4CD55E.

0x4CD55E fills the zone entry `{handle, remaining, cursor, name[64], ...,
allocFlags @+0x4C}`. When the handle is -1, the stream reader (0x4B6790)
only `memcpy`s from the cursor, so the buffer is read-only and can be served
again. Only the name `ffotd_client` sets the entry's FFOTD byte (+0xA4).

Kernel33 makes two byte-checked changes:

1. **`jne` at 0x4CD2AF → `PatchDirOpenHook`.** If the name is a patch file,
   the hook puts that file's size and buffer into the FFOTD locals, sets
   `esi` = -1 and continues at 0x4CD55E. Any other name continues at 0x4CD3E3
   with the registers unchanged. So:
   - disk zones keep their RSA signature check;
   - `ffotd_client` never reaches the hook;
   - no zone read from disk is ever treated as unsigned.
2. **The code_pre_gfx `DB_LoadXAssets` call (0x59841C) → `PreGfxLoadHook`.**
   The hook puts the patch zones in front of the list's four zones, with the
   list's alloc flags (1), and calls `DB_LoadXAssets` (0x08465768). C1 keeps
   the first asset it links under a name, so the patch zones' assets win.
   The override flag 0x19A2F6C reads 0 at that point, and Kernel33.log
   records it.

**Rules for a patch file.**
- Files load in alphabetical order. The zone name is the file name without
  `.ff`.
- Up to 16 files load.
- A file is skipped, with a line in `Kernel33.log`, if it:
  - is not `IWffu100` version 0x14E;
  - is larger than 256 KiB (C1 decrypts only the first 0x40000-byte chunk
    of an unsigned zone);
  - is named `ffotd_client`;
  - has the same name as a stock zone in any other `client_shipRetail`
    subfolder. So a patch file can never shadow a stock zone.

**Option.** `+set codol_patchdir 0` on the `codoMP_client_shipRetail.exe`
command line turns the folder off, and neither patch is installed.
Kernel33 reads the option from the process command line. If the option
appears more than once, the last value wins.

**Log lines** (`Kernel33.log`, next to the exe):

```
patch folder: codol_english.ff (171860 bytes) queued as zone "codol_english"
patch folder: 1 zone(s) load from memory ahead of code_pre_gfx
patch folder: code_pre_gfx list: 1 patch zone(s) ahead of 4 stock
patch folder: zone "codol_english" loading from memory (171860 bytes, override flag 0)
```

When the option is off, the log shows `patch folder: off (codol_patchdir 0)`.
When the folder is empty, it shows `patch folder: no .ff files in ...`.

**Tested (2026-09-28, real `codoMP_client_shipRetail.exe`, local lobby and
server).**
- **With `codol_english.ff` in the folder:**
  - `console_mp.log` lists `codol_english` first in
    `DB_DebugZoneLoadTimePrint`, ahead of `code_pre_gfx_mp`;
  - the menus and the in-game HUD are in English (mode select, recruit
    dialog, class menu, HUD);
  - the match on mp_killhouse_sh joined and played;
  - the lobby's FFOTD still loads: `BD_TryLoadXFileInternal FFOTD buffer
    size 2934`, and `ffotd_client` again at map load;
  - TAB shows the scoreboard.
- **With the option off, or the folder empty:** the stock Chinese menus
  appear, and the FFOTD loads as before.

**Still Chinese with the patch folder:**
- the CoDOL logo;
- the coop and zombies mode titles on mode select (outside the `mp` scope);
- matchmaking playlist names and descriptions (lobby and playlist data);
- some weapon names, slot labels and scoreboard column headers;
- the team name, the game-mode name on the scoreboard, and the ESC "leave"
  and market buttons.

These strings are either outside the zone's scope, in `untranslated.tsv`,
baked into images, or sent by the lobby.

## Scoreboard hook (Kernel33)

The scoreboard lives in the Scaleform HUD movie
`scaleform/default/codohud.gfx`. That movie loads once per map, when the
client enters the game, through the UI mode switch 0x83DA993(local, 12).
The open is refused while the D3D device is lost. If the player Alt+Tabs
out of a fullscreen client during the load screen, the movie never loads.
TAB (CG_ScoresDown 0x436EE0 → 0x83DA993(local, 7)) then shows nothing until
the next map.

Kernel33 redirects CG_ScoresDown's call at 0x436F90 to `ScoresOpenHook`. The
hook first repeats the mode-12 open, but only when all of these hold:
- the movie (0x810C4F4 / 0x810C50C) is missing;
- Scaleform is on (0x6C44D5C);
- the device is usable (0xA7A6C0).

It then makes the original call. When the movie is present, the hook only
makes the original call. Kernel33.log logs each reload, up to 8 times.

## Sources that are not localize entries

- **Playlist and game-mode names and descriptions** (the matchmaking list,
  the description panel, "团队竞技 - Killhouse" on the scoreboard) come from
  the playlist file the lobby serves: C1 logs `LiveStorage_FetchFile:
  filename[mp_playlists_shipRetail_cb2.info]`, and alpha0022 serves
  `resources/mp_playlists_shipRetail_cb2.info`.  Every entry already has
  `name english` / `name chinese` and `description english` / `description
  chinese` lines; C1 uses its own language's.
  `tools/codol_english/english_playlist.py` writes
  `out/mp_playlists_shipRetail_cb2.english.info` with each chinese line
  replaced by its english twin (79 lines; 5 have no English twin).  The lobby
  can serve that file instead -- tested: with it served, the matchmaking list,
  the description panel and the scoreboard mode name are English.  Serving it
  is a lobby decision (for everyone, or per account); the stock file was put
  back after the test.
- **Scaleform movies** (`scaleform/default/codo.gfx` in patch_ui_mp,
  `codohud.gfx` and `codoingame.gfx` in patch_common_mp) carry Chinese as
  DefineEditText initial text (tag 37) and DoABC string constants (tag 82).
  Where ActionScript sets the field from a localize name the English shows;
  a field it never sets keeps its Chinese initial text.  Replacing those
  needs a patched copy of the movie as a rawfile (rawfiles are first-wins
  too), but the movies are 0.86-4.5 MB, far over the 256 KiB an unsigned
  patch file may hold.  Not done.
- **Images:** the CoDOL logo, the left-panel tip text on the matchmaking page
  (a bitmap with inline icons; the text exists in no string or movie), the
  tutorial thumbnails and team emblems.  Not coverable by strings.
- **Clipping:** English is wider than Chinese and some fixed boxes clip
  ("Back to l", "Sho", "Quick Cha").  Shorter wording helps only a little.

## Second-pass verification (2026-09-28, real codoMP_client_shipRetail.exe)

Test client, local lobby with the English playlist served, test server on
udp/17773, patch folder holding the 186,911-byte `codol_english.ff`
(Kernel33.log: `zone "codol_english" loading from memory (186900 bytes,
override flag 0)` on the first run of this pass).  Screenshots in the session
scratch `english2\`:

- `n2.png` main menu, `r7.png` main menu with "Shop";
- `n3_options.png` options dialog (Video / Audio / Controls ...);
- `n4_modes.png` matchmaking: playlist names and description in English;
- `r4.png` room: ESC button "Leave", team "OpFor", "Waiting for players";
- `n7_tab.png` scoreboard: Score / Kills / Dead / Assists / Headshots / Ping,
  "Lv 1", team name, "Team Deathmatch - Killhouse";
- `n8_esc.png` in-game class menu: Custom Class, Primary Weapon "Vector",
  Secondary Weapon "M9", Perks, Deathstreak, Melee Weapon, "Back to Lobby";
- `n9_back.png` "Back to lobby?" Cancel / Confirm;
- `r1.png` mode select: "Spec Ops", "Multiplayer", "Zombies".

Still Chinese on those screens: the logo, the left-panel tip bitmap and the
tutorial thumbnail text.

## Font

**Goal.** Give the Scaleform (GFx) menus a Latin font when English is on,
while the Chinese UI keeps its fonts and any Chinese text that is left still
renders.

### How C1 gets its Scaleform fonts (measured)

1. **Movies are rawfiles.** Every `.gfx` is a rawfile asset (type 36), not a
   loose file and not a separate asset type:

   | rawfile | zones |
   |---|---|
   | `scaleform/fonts_ingame.gfx` | `code_post_gfx_mp`, `patch_code_post_gfx_mp` |
   | `scaleform/default/codo.gfx` (main menus) | `ui_mp`, `patch_ui_mp` |
   | `scaleform/default/codologin.gfx` | `ui_mp` |
   | `scaleform/default/codohud.gfx`, `codoingame.gfx` | `common_mp`, `patch_common_mp` |
   | `scaleform/default/ime.gfx` | `code_post_gfx_mp` |

   They are uncompressed SWF movies with the `GFX` signature (versions 9 and
   10). The zones store them zlib-compressed (`compressedLen` set).
2. **The menus embed no font.** `codo`, `codologin`, `codohud` and
   `codoingame` have no DefineFont tag and no font import. Each
   DefineEditText names a font *class* (an alias) and has UseOutlines set:

   | alias | text fields (patched codo / codologin / codohud / codoingame) |
   |---|---|
   | `$font_3` | 789 / 120 / 40 / 71 |
   | `$font_2` | 204 / 11 / 36 / 21 |
   | `$font_4` | 40 / 4 / 0 / 0 |
   | `$font_5` | 19 / 0 / 0 / 0 |

   69 HTML fields in `codo.gfx` also carry `<FONT FACE="FZZongYi-M05S">`.
   `ime.gfx` uses `$IMECandidateListFont`. It imports `gfxfontlib.swf`, but
   the import is empty.
3. **One font library, one hard-coded font map.** The function at 0x006B50B0
   does the following:
   - it loads `scaleform/fonts_ingame.gfx` with `GFx::Loader::CreateMovie`
     (0x741180, called at 0x6B5123);
   - it builds a `FontLib` (0x762D70), adds that movie's fonts to it
     (0x762C60), and installs it with `SetState(0x14)`;
   - it builds a `FontMap` (0x764030) and calls `MapFont(alias, font, flags,
     1.0)` (0x7640E0) five times, with names from `.rdata` 0xC77830..0xC7789C:

     | alias | font | flags |
     |---|---|---|
     | `$font_2` | `FZLanTingHei-R-GBK` | 0x10 (keep the field's style) |
     | `$font_3` | `FZZongYi-M05S` | 0x10 |
     | `$font_4` | `Agency FB` | 0x10 |
     | `$font_5` | `Agency FB` | 2 (bold) |
     | `$IMECandidateListFont` | `FZLanTingHei-R-GBK` | 0x10 |

   - it installs the map with `SetState(0x17)`, and passes
     `FZLanTingHei-R-GBK` to a DrawText manager as its default font.

   No FontProvider is installed. The "FontProvider not installed" string is
   GFx's own. There is no `fontconfig.txt` and no per-language map: the names
   are constants, and the same map is used whatever the language.
4. **`fonts_ingame.gfx` holds four DefineFont3 fonts** (the patch zone's copy,
   which is the one C1 links):

   | id | name | glyphs | bytes |
   |---|---|---|---|
   | 1 | `FZLanTingHei-R-GBK` | 21,805 (full GBK) | 7.19 MB |
   | 3 | `FZZongYi-M05S` | 7,621 | 1.84 MB |
   | 5 | `Agency FB` | 244 (ASCII, Latin-1, a few symbols) | 19 KB |
   | 7 | `Agency FB`, bold (only in the patch copy) | 244 | 19 KB |

   The whole movie is 9,067,516 bytes (7,388,073 compressed). Both Chinese
   fonts have all of ASCII. Their Latin is a wide grotesque: `H` advances
   0.72 em, against 0.44 em in Agency FB. That width, not bad glyphs, is
   what makes English clip: the words are longer, and the letters are wider.

### Options

| option | how it switches with English | Chinese-safe | cost |
|---|---|---|---|
| **A. Replace `fonts_ingame.gfx` in a patch zone** with the same library whose two Chinese fonts carry Latin glyphs (U+0020..U+007E) from a Latin design. Same font names, so the hard-coded map is unchanged. | The zone is in `client_shipRetail\patch\`, next to `codol_english.ff`. Removing the file or `+set codol_patchdir 0` turns off both. | Yes. Every CJK glyph stays in the same font. English is ASCII only (`build_ff.py`), so it never needs a CJK glyph. | The full zone is about 7.4 MB. The patch folder must accept files over 256 KiB, which is a one-constant Kernel33 change (below). |
| B. Kernel33 remaps the aliases (patching the `MapFont` string pushes at 0x6B51C1..0x6B5228), and adds a small second font movie to the FontLib. | Kernel33 option. | **No.** A field resolves one font, and GFx does not look in another font for a missing glyph: it draws a small box (measured, below). Chinese text in those fields would turn into boxes. | Code patch in the font init. |
| C. Install a GFx FontProvider for system fonts. | Kernel33. | No, for the same reason as B. It also needs the font installed on each PC, and Win32 provider code that C1 does not link. | Large. |
| D. Edit each menu movie (`codo.gfx` ...) to embed fonts. | Patch zones. | Only if the embedded font is a hybrid anyway. | Four large movies to re-ship after every menu change. |

**A is the one to use.** It changes no code in C1 and no original file, and
needs no language logic, because it lives in the same patch folder as the
English strings.

### Loading a large patch zone

C1 decrypts only the first read chunk of an unsigned zone, but it does not
reject a longer one:
- `DB_LoadXFile` reads the 0x115-byte header and RSA blob, then calls the
  stream init 0x4B5AC0 with the z_stream at 0x017C68B4.
- For an unsigned zone (`[0x1740810]` = 0), 0x4B5B7D runs one `ctr_encrypt`
  over `next_in`/`avail_in`. That covers the rest of the first 0x40000-byte
  chunk.
- Every later chunk goes to `inflate` (0x646720) unchanged. At 0x4B69E0 the
  decrypt/hash path 0x4B5840 is taken only for a signed zone.

So a zone of any size loads if its body is encrypted up to file offset
0x40000 and written in plain after that. `build_font_ff.py` writes files that
way, and `--inspect` reads them back the same way.

**Not measured yet.** This needs the patch folder to accept more than 256
KiB. The loader change is one constant plus its comment, kept in the
session scratch as `font/kernel33_patchdir_large.patch`:

```
-#define PATCHDIR_MAX_BYTES     0x40000u
+#define PATCHDIR_MAX_BYTES     0x2000000u /* 32 MiB; the English font zone is ~7.4 MB */
```

Memory cost:
- Kernel33 keeps the file in heap memory, about 7.4 MB.
- The zone takes about 7.4 MB of block 3 for the compressed rawfile. That is
  the same size as the stock copy it shadows, which also stays loaded.
- GFx inflates the 9 MB movie once when the font library loads, as it
  already does for the stock copy.

### Test on the real client (2026-09-28)

**Setup.**
- Client: `codoMP_client_shipRetail.exe` with the patch-folder Kernel33.
- A private local lobby and a server on 17778; the live 17733 server was not
  touched.
- Before: the patch folder held `codol_english.ff` only.
- After: `codol_font_test.ff` was added, built with
  `build_font_ff.py --subset 560` (246,683 bytes, so it fits the 256 KiB
  loader). It holds Saira Condensed Latin plus the 560 Chinese characters
  C1's localize text uses most.

**Result.**
- **The zone loads and wins.** Kernel33.log shows
  `zone "codol_font_test" loading from memory (246683 bytes, override flag 0)`,
  and every Scaleform screen draws with the new library: mode select, the MP
  home, matchmaking, the room, and the HUD scoreboard.
- **The converted TrueType outlines render correctly in GFx.** Fills and
  counters are right, and there are no inverted contours.
- **Clipping drops sharply.** Most fixed-width labels that were cut off now
  fit, and the rest show more of the word:

  | before | after |
  |---|---|
  | `Sho` | `Shop` |
  | `Store Nev` | `Store News` |
  | `Video Tut` | `Video Tutor` |
  | `Matchmaki` | `Matchmaking` |
  | `Open to Lev` | `Open to Level:` |
  | `XP Gain Rat` | `XP Gain Rate` |
  | `Rank Leve` | `Rank Level` |
  | `Socia` | `Social` |

  Some long strings still clip (`Video Tutor`, `Change Mo`, `Back to Ho`,
  `Ready for`).
  Those need shorter English text or `--track`/`--cap` tuning.
- **Chinese keeps rendering from the same font.** The lobby-sent playlist
  names and the Chinese help text show every character in the subset
  correctly, next to the new Latin.
- **Characters left out of the subset draw as a small box** (for example
  `对▯训练`). This is the measurement behind "no per-glyph fallback", and it is
  why a player build must carry the full library, with all 21,805 + 7,621
  glyphs.

Screenshots are in the session scratch, `font/shots/compare_*.png`.

### Font choice and licensing

- **Agency FB** is a commercial Font Bureau design. Microsoft licenses it and
  bundles it with Office, and its TTF may not be redistributed. The glyphs
  C1 already ships in `fonts_ingame.gfx` (`$font_4` and `$font_5`) came under
  the game's own licence (Activision/Tencent).
  - `build_font_ff.py --style agency` reuses those shipped glyphs and needs
    no outside file.
  - Before it ships to players, Activision should confirm that its licence
    covers the derived library.
  - Do not download an Agency FB TTF and embed it.
- **Default: Saira Condensed** (Medium for `$font_2`, SemiBold for `$font_3`).
  - It is licensed under SIL OFL 1.1. The files and `OFL.txt` are in
    `tools/codol_english/fonts/`.
  - It is squarish, condensed and technical, the closest free match to Agency
    FB, and easier to read at small sizes.
  - OFL allows bundling in a program and embedding. Here the font is
    converted into GFx outlines inside a game zone (OFL FAQ 1.3, 1.11–1.12),
    and only the Saira-derived part is OFL.
  - Ship `OFL.txt` with the patch folder or in the credits.
  - The Reserved Font Name "Saira" is not used, because the glyphs live in
    the fonts named `FZ...`.
- **Other free choices** for `--regular` and `--bold`, all OFL:
  - Barlow Condensed: a clean DIN look, with no Reserved Font Name.
  - Rajdhani: squarer and wider.
  - Pathway Gothic One: the closest to Agency FB's thin look (Reserved Font
    Name "Pathway").
  - Oswald: heavier.

### Tool

```
python tools/codol_english/build_font_ff.py                 # -> out/codol_english_font.ff (Saira Condensed)
python tools/codol_english/build_font_ff.py --style agency  # the shipped Agency FB glyphs
python tools/codol_english/build_font_ff.py --regular R.ttf --bold B.ttf [--cap 1.0] [--track 0]
python tools/codol_english/build_font_ff.py --subset 560 -o out/codol_font_test.ff   # <= 256 KiB test build
python tools/codol_english/build_font_ff.py --inspect out/codol_english_font.ff
python tools/codol_english/build_font_ff.py --preview out/font_preview.png
```

**`gfx_font.py`**
- Reads and writes GFX/SWF tags and DefineFont3. The round trip is
  byte-exact on all four shipped fonts and on `codo.gfx`.
- Encodes and decodes glyph SHAPE records.
- Converts TrueType outlines with fontTools. It scales each outline to the
  Chinese font's `H` cap height, flips it to y-down, and reverses the
  contours to the direction the shipped fonts use.
- Includes a small renderer for previews.

**`build_font_ff.py`** runs these steps:
1. Takes the stock library from `patch_code_post_gfx_mp`, using the alpha0022
   reader.
2. Grafts U+0020..U+007E into `FZLanTingHei-R-GBK` (regular donor) and
   `FZZongYi-M05S` (bold donor). The font names, metrics, the Agency FB fonts
   and every other glyph are kept.
3. Writes a zone that holds the rawfile `scaleform/fonts_ingame.gfx`,
   compressed like the stock one.
4. Wraps the zone as IWffu100, with only the first chunk encrypted.

`--subset N` keeps only ASCII plus the N Chinese characters C1's localize text
uses most. That is enough to test the mechanism with the 256 KiB loader, but
it is not a player build.

**Packaging.** Ship the font as a second patch file, `codol_english_font.ff`,
next to `codol_english.ff`, not inside it:
- the strings zone stays under 256 KiB and changes often;
- the font zone is large and rarely changes.

Both load ahead of the stock zones. Their asset names differ, so their order
does not matter.

### Agency FB build: installed and tested (2026-09-28)

The user chose the game's own Agency FB glyphs (`--style agency`).

**Installed:**

| file | md5 | notes |
|---|---|---|
| `Kernel33.dll` (game folder and `Kernel33\`) | `56a93962ed04d448d57c834829e00ac9` | `PATCHDIR_MAX_BYTES` 0x40000u → 0x2000000u |
| Previous DLL, kept as `Kernel33.dll.pre-largezone.bak` in both places | `3ef62b7f1476c62b838309bd184a6682` | `kernel33.c.pre-largezone` keeps the old source |
| `client_shipRetail\patch\codol_english_font.ff` | `bcd2fb9c28f7cb903d5c800771e2ad1f` | 7,387,505 bytes |
| `client_shipRetail\patch\codol_english.ff` | `55af11dd92a08aad2697de5d8b22fbc2` | 186,735 bytes, 9,120 entries, rebuilt with the clipping fixes below |

The previous `codol_english.ff` (md5 `1b0e65e2...`) is kept in the session
scratch, `font\prev\codol_english.ff.prev-1b0e65`.

The font zone was built with
`python tools/codol_english/build_font_ff.py --style agency -o out/codol_english_font.ff`.
It maps Agency FB regular into `FZLanTingHei-R-GBK` (scale 0.971) and Agency
FB bold into `FZZongYi-M05S` (scale 0.992). All 21,805 + 7,621 CJK glyphs are
kept.

**Load order.** Kernel33 sorts patch files with `lstrcmpiA`, so
`codol_english.ff` loads before `codol_english_font.ff` ('.' < '_'). Either
order works:
- the two zones share no asset name;
- the font library is opened later, at 0x6B50B0, after both zones are linked.

**Test setup.** A test `codoMP_client_shipRetail.exe`, with a private lobby
and a server on 17778.

**Loading.**
- `Kernel33.log`:
  ```
  zone "codol_english" loading from memory (186735 bytes, override flag 0)
  zone "codol_english_font" loading from memory (7387505 bytes, override flag 0)
  ```
- There was no `WIN_FILE_CORRUPT`, no out-of-memory error, and no other
  error. This also confirms, on the real client, that a zone larger than
  0x40000 loads when only its first chunk is encrypted.
- `DB_DebugZoneLoadTimePrint` lists `codol_english_font` at 11 ms.
- The map load (common_mp and mp_killhouse_sh) is dominated by the stock
  zones, as before.
- Client working set: 740 MB at the menu, 762 MB in the match. That is in the
  range of other test clients (700–900 MB).

**Rendering.**
- English renders in Agency FB on every Scaleform screen checked: mode select,
  MP home, options (Video, Audio, Controls with Look, Movement, Combat and
  Chat), matchmaking, rooms list, create room, the out-of-game class and
  character panels, callsign/career, leaderboards, the in-game class menu,
  the TAB scoreboard and the HUD.
- A Killhouse TDM match was joined.
- Chinese still renders from the same fonts, with no boxes: lobby playlist
  names, the channel tips, the playlist description, and the `新兵` title.
- The leaderboard's player names show boxes. They show the same boxes with
  the font zone removed, so this is not caused by the font; it comes from the
  lobby's leaderboard name data.

**Clipping with the real font.** Most labels that clipped with the wide
glyphs now fit. These six still clipped, and were fixed in
`sources/manual.tsv`:

| key | was | now | where |
|---|---|---|---|
| SF_UI_PRIMARY_WEAPON | Primary Weapon | Primary | class panel header ("Primary Weap") |
| SF_UI_SECONDARY_WEAPON | Secondary Weapon | Secondary | class panel header ("Secondary We") |
| SF_UI_WEAPONLOADOUT_COMBAT | Melee Weapon | Melee | class panel column ("Melee Weap") |
| SF_UI_CAREER_PROFILE | Edit Callsign | Edit | career page vertical tab ("Edi t Ca llsi") |
| SF_UI_CAREER_PLAYER_PROGRESS_TAB | Career Progress | Career | career page vertical tab ("Ca re er Pr") |
| SF_UI_LIST_LABEL_STATE | (untranslated 状态) | Status | rooms list column header |

After the rebuild, all six were checked on the client and fit.

**Known, not font-related.** Twice after login, mode select was dimmed by an
invisible modal; ESC dismissed it. It did not happen on other launches.

**Licence.** Agency FB is a commercial Font Bureau design. The glyphs in this
zone are derived from the copy Activision ships inside C1's
`fonts_ingame.gfx`. Before the derived library is distributed to players,
Activision should confirm that their font licence covers it.

## Clipping pass (2026-09-28)

User decision: where an English label clips, use a shorter word with the same meaning,
not a truncation.  The labels were surveyed on a test codoMP_client_shipRetail.exe
(main menu, mode select, matchmaking, room, options Video/Audio/Controls, in-game class
menu, back-to-lobby confirm, scoreboard, HUD) with the stock wide Latin glyphs.  Market
and the out-of-game loadout/item menus stay locked for a rank-1 test account ("Unlocks at
player level 5"), so they were not surveyed.

Rule used: a field that held N Chinese characters shows about 2N wide Latin characters.
Because the Agency FB Latin glyphs (font section) are about 40% narrower, only labels
that would still clip with them were shortened: roughly, full length more than ~1.25x the
characters the wide font showed (the font test fitted Matchmaking at 11/9 and clipped
Change Mode at 11/8).  Labels that clip only with the wide glyphs (Store News,
Matchmaking, Rank Level, Social, XP Gain Rate, Resolution, Movement, Soften Smoke Edges,
Bullet Impacts, Hold Mouse Look, Sprint/Hold Breath, Weapon Attachment, Windows Default,
Quick Renew, Switch Weapon 1/2) were left full length.  All entries are in
`tools/codol_english/sources/manual.tsv`.

| key | was | now | where |
|---|---|---|---|
| SF_UI_GLOBAL_BACK_CHANGE_GAME_TYPE | Change Mode | Modes | main menu ESC button |
| SF_UI_GLOBAL_BACK_BACK_TO_LANDING_PAGE | Back to Home | Home | matchmaking ESC button |
| SF_UI_BACK_TO_MAIN | Back to Home | Home | ESC button |
| SF_UI_BACK_TO_ROOM | Back to Room | Room | ESC button |
| SF_UI_AUTO_MATCH | Ready for Battle | Search | matchmaking start button (开始匹配) |
| SF_UI_MAIN_MENU_LABEL_MARKET | Store | Shop | main menu market button (fits with Agency FB) |
| SF_UI_RECENT_CHALLENGE | Quick Challenge | Challenges | main menu panel title |
| SF_UI_HOMEPAGE_RECOMMEND_ITEM, SF_UI_AD_AND_PROMOTION_ITEMS, SF_UI_MARKET_RECOMMENDATIONS | Recommended | Featured | main menu tab |
| SF_UI_TUTORIAL_VIDEO_LIST | Video Tutorials | Videos | main menu tab |
| SF_UI_SYSTEM_NEWS | Official News | News | main menu tab |
| SF_UI_HOMEPAGE_RECENT_UNLOCK_ITEM | Recently Unlocked | Unlocks | main menu tab |
| SF_UI_MAIN_MENU_LABEL_MESSAGEBOX_SHORT_NAME | Messages | Inbox | side bar |
| SF_UI_MAIN_MENU_LABEL_CHARACTERLOADOUT | Character Loadout | Char | vertical tab |
| SF_UI_MAIN_MENU_LABEL_WEAPONLOADOUT | Loadout | Class | vertical tab |
| SF_UI_PLAYLIST_OPEN_AT | Open to Levels: | Levels: | playlist details |
| SF_UI_DISPLAY_MODE | Display Mode | Display | options, video |
| SF_UI_SCREEN_REFRESH_RATE | Refresh Rate | Refresh | options, video |
| SF_UI_ANTI_ALIASING | Anti-Aliasing | AA | options, video |
| SF_UI_VIDEO_FOV | Field of View | FOV | options, video |
| SF_UI_SSAO | Ambient Occlusion | SSAO | options, video |
| SF_UI_DYNAMIC_LIGHT_LIMIT | Dynamic Lights | Lights | options, video |
| SF_UI_TEXTURE_QUALITY | Texture Quality | Textures | options, video |
| SF_UI_SETTING_CHANGE_WARNING | The "Recommended" settings are advised. Custom settings may reduce performance | Custom settings may reduce performance. | options footer |
| SF_UI_SETTING_VOLUME_MASTER | Master Volume | Master | options, audio (runs into the slider) |
| SF_UI_SETTING_SOUND_DEVICE | Output Device | Output | options, audio |
| SF_UI_CONTROL_MOUSE_SENSITIVITY | Mouse Sensitivity | Sensitivity | in-game options |
| SF_UI_CONTROL_AIM_DOWN_SIGHT | Aim Down the Sight | Aim Down Sight | controls, combat |
| SF_UI_CONTROL_THROW_LETHAL_GRENADE | Throw Lethal Grenade | Lethal Grenade | controls, combat |
| SF_UI_CONTROL_THROW_SPECIAL_GRENADE | Throw Special Grenade | Special Grenade | controls, combat |
| SF_UI_CONTROL_SHOW_OBJECTIVE | Show Objectives/Scores | Scoreboard | controls, combat |
| SF_UI_WEAPONLOADOUT_STREAK_LEAGUE_1 | Intermediate | Tier 2 | class menu killstreak column (next to "Tier 1") |
| SF_UI_WEAPONLOADOUT_STREAK_LEAGUE_2 | Advanced | Tier 3 | class menu killstreak column |

Wrong translations found on the same screens (not clipping):

| key | was | now |
|---|---|---|
| SF_UI_LIST_LABEL_MODE, SF_UI_QUICK_GAME_SETTING_MODE_SETTING, SF_UI_CREATE_ROOM_MODE | g | Mode |
| SF_UI_LIST_LABEL_PLAYER_MIN_MAX, EXE_SV_INFO_NUM | num | Players |
| SF_UI_ANTI_ALIASING_OFF, SF_UI_SSAO_OFF, SF_UI_GAME_OPTION_DISABLE, SF_UI_GAME_OPTION_HEALTH_REGEN_NONE | CLOSE | Off |
| SF_UI_CONTROL_FREE_LOOK | Free | Free Look |
| SF_UI_CONTROL_MELEE | melee | Melee |
| SF_UI_QOS_TITLE | ...improve the game!" | ...improve the game! (stray quote) |

Verified with the wide glyphs on the test client (session scratch `english2\`):
`c2_main.png`/`d1_main.png` main menu, `c3_mm.png`/`f4_mm.png` matchmaking, `d2_video.png`,
`d3_audio.png`, `d4_controls.png`, `e5_move.png`, `e6_combat.png` options, `c9_room.png` room,
`c11_tab.png` scoreboard, `e9_esc.png` class menu, `c1.png` mode select.  Every shortened
label above fits with the wide glyphs.  The labels deliberately left long still clip with the
wide glyphs (e.g. "Matchmaki", "XP Gain Rat" in `f4_mm.png`) and are expected to fit once the
Agency FB font zone is installed; that final check is still to do.  Build: codol_english.ff
186,742 bytes, 9,119 entries, installed in client_shipRetail\patch\ (previous file kept at
`english2\prev\codol_english.ff.prev-9119a`).
