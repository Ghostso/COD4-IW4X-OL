# What `fs_game` actually means to C1 (CoDOL 1.1.1.13) — evidence file

Date: 2026-09-17. Read-only investigation. Every claim below is tagged **MEASURED**
(read out of `C1.exe`, a shipped `.ff` set, a client log or a lobby capture) or
**INFERRED** (reasoned from measured facts).

Binary under test: `D:\CoD\CODOL Builds\Call of Duty Online 1.1.1.13\C1.exe`
(33 608 704 B, PE image base `0x400000`).
Sections (MEASURED, PE headers): `.text 0x401000+0x741000`, `.rdata 0xB42000+0x158000`,
`.data 0xC9A000`, `.tvm0 0x82F8000+0x1725000` (obfuscated/relocated code — real code
lives there too; several call sites below are in it).

---

## 0. BOTTOM LINE (item 6 first)

**`fs_game` is a red herring for the mp -> coop/zm handoff.** It is a
filesystem-search-path dvar only, its value domain forbids `"coop"`/`"zm"`, and
nothing in C1 turns a server-supplied `fs_game` into an asset category. The real
carriers are **(a) the gamestate `type` field** (decides `common_gametype_<cat>`)
and **(b) the gamestate map string** (decides the level zones, including the
`coop_*` split). `codol_zoneType` is the correct server-side spelling of (a), and
the server already puts it on the wire.

Exact recommendation, with the evidence in §1–§5:

| For | fs_game should be | why |
|---|---|---|
| mp | `""` | measured default; only legal non-empty value is `mods/<dir>`, and no `mods/` exists |
| coop | `""` | same |
| zm | `""` | same |

The two strings that DO matter, and where they go:

* The **gamestate `type` field** (second string of the svc-2 gamestate, i.e.
  `codol_zoneType`) must be exactly `mp` | `coop` | `zm` — this is the string C1
  prefix-tests to pick `common_gametype_coop` / `_zm` (§4 + §7.4). **NOT** CS[0]
  `g_gametype`; the first edition of this file said `g_gametype` and was wrong.
  The server already sends the right thing, so nothing changes here.
* The **gamestate map string** must be the **playlist spelling** for coop
  (`coop_training_mp_killhouse_sh`), not the stripped level name
  (`mp_killhouse_sh`) — C1 derives the base map zone from the playlist name
  itself and loads **both** (§5, MEASURED in the disassembly and in a live
  capture). See §7.3 for the server-side prerequisite.

---

## 1. Does C1 set / read `fs_game` at all?  (dvar id 1006)

**MEASURED — the dvar exists and is registered exactly once.**

* The string `"1006"` occurs exactly **once** in the whole image, at file offset
  `0x8693D4` = VA `0xC6A3D4`. It has exactly **one** code reference:
  `0x00617A45  push 0xC6A3D4`.
* `0x00617A45..0x00617A4F`:
  `Dvar_RegisterString("1006", "" , 0xC08, "")` -> pointer stored at
  `[0x02A9DDFC]`.
  `0xC08` == 3080 == `CODINFO|SERVERINFO|INIT`, which matches
  `alpha0022/resources/dvars_c1exe.json` (`"flag_bits": 3080`,
  `"register_va": ["0x00617A4F"]`).
  * **Note / discrepancy (MEASURED):** `alpha0022/docs/BASE.md:49` says fs_game is
    "also SYSTEMINFO". The flag word `0xC08` has no `SYSTEMINFO` (0x1000) bit.
    `dvars.py:1540-1548` appends `1006` to CS[1] on the strength of that BASE.md
    note; on the flag bits it belongs in CS[0], not CS[1]. Harmless (value is
    `""` either way) but the note is wrong.
* Neighbours registered in the same function (`FS_Startup`, VA `0x00617AC0`):
  `"1749"` -> `[0x2A9EF08]` (fs_basepath), `"2232"` -> `[0x2A9DBEC]` (fs_basegame),
  `"1006"` -> `[0x2A9DDFC]` (fs_game), `"940"` (bool), `"941"` -> `[0x2A9EF0C]`
  (fs_homepath, default = fs_basepath's value at `[edx+0x2C]`).
  The unstripped helper strings around them confirm the module:
  `0xC6109C "FS_SV_FOpenFileWrite: %s"`, `0xC610C8 "FS_SV_FOpenFileRead (fs_homepath): %s"`,
  `0xC610F0 "... (fs_basepath) ..."`, `0xC61118 "... (fs_cdpath) ..."`.

**MEASURED — the domain callback: the ONLY legal values are `""` and `mods/<x>`.**

`0x00617A61  mov dword [eax+0x44], 0x617810` installs a validator on the `1006`
dvar. `0x00617810`:

```
617817  esi = value
61781A  if (*esi == 0)            -> return 1          ; "" is accepted
617827  mov edx,"mods" ; eax=4 ; call Q_strncasecmp
617836  if (result != 0)         -> 0x6178A5 (reject)  ; must start with "mods"
617849  if (strlen(value) < 6)   -> 0x6178A5 (reject)
61784E  if (value[4] != '/' && value[4] != '\\') -> reject
617859  if (strstr(value,"..") ) -> 0x617880 (reject)
61786E  if (strstr(value,"::") ) -> 0x617880 (reject)
61787E  -> 0x61781C  return 1                          ; accept "mods/<name>"
reject paths: Com_Printf(3, "895 %s %s", value, cvar) ; return 0
```

`"mods"` lives at `0xC62140` and has exactly one xref (`0x00617827`).
**So `set fs_game coop` / `set fs_game zm` is rejected by C1's own validator.**

**MEASURED — what the value is used for: search paths, nothing else.**

15 references to `[0x02A9DDFC]` exist in the image; all of them are filesystem or
server-info code, none of them is client parse code:

| VA | what it does |
|---|---|
| `0x006178E4` | `FS_Startup` helper: copies fs_game into a 0x108 buffer, `\` -> `/`, lowercases (path sanitiser) |
| `0x0061796A` | same helper |
| `0x00617A5D` | the registration itself |
| `0x00617DB2..0x00617E77` | `FS_Startup`: `if (fs_game[0] && Q_stricmp(fs_game,"main"))` then `FS_AddGameDirectory(fs_cdpath, fs_game)`, `(fs_basepath, fs_game)`, `(fs_homepath, fs_game)`; then `mov byte [fs_game+9], 0` (clears `modified`) |
| `0x00618735` | `FS_InitFilesystem` (VA `0x006186E0`, one caller, `0x00598825` = Com_Init): `Q_strncpyz(lastValidBase, fs_basepath, 0xFF)` / `Q_strncpyz(lastValidGame, fs_game, 0xFF)` |
| `0x00618920` | **`FS_ConditionalRestart`** (entry `0x00618910`): `if (fs_game->modified \|\| checksumFeed != [0x2A9DDF8]) { FS_Restart(...); return 1; } return 0;` |
| `0x0059C4F7 / 0x0059C690 / 0x0059CEB1 / 0x0059CF0D` | pure-file list builders (compare an iwd's gamedir against fs_game and `"usermaps"` @`0xC6222C`) — these produce what the CLIENT sends, not what it consumes |
| `0x005D4C7C / 0x005D501D` | server-side info-string builders (the listen/dedicated server half of C1): `if (fs_game[0]) Info_SetValueForKey(info, "game", fs_game)` @`0x005D5036` |

**INFERRED:** `fs_game` in C1 is ordinary IW3-lineage `fs_gameDirVar`: an extra
search directory, a browser "game" key, and an input to the pure-file lists.
There is no asset-category, zone-path or gametype meaning anywhere.

---

## 2. Values the client expects per category, and the `mods/` question

* **MEASURED:** registered default is `""` (`0x00617A3B push 0xC2FEAD` = the shared
  empty string).
* **MEASURED:** the only other accepted shape is `mods/<name>` (§1 validator).
* **MEASURED:** the install has **no `mods/` directory and no `usermaps/`**.
  `ls` of `D:\CoD\CODOL Builds\Call of Duty Online 1.1.1.13` gives
  `CODOL/ Cross/ DirectX/ Logs/ TCLS/ TenproxyLog/ __pycache__/ client-files/
  client_shipRetail/ main/ miles/ players/ tqm/` — no `mods`, and `main/mods`
  does not exist either.
* **MEASURED:** nothing in the client launch config sets it —
  `3-START-CLIENT.cmd`, `client-files/*.ini` and `players/config_mp.cfg` contain
  no `fs_game` and no `1006`.
* **MEASURED:** `fs_game` carries the `INIT` flag (0x8 of `0xC08`). On the IW
  dvar system `CVAR_INIT` means "set only from the command line at startup".

**INFERRED:** there is no per-category fs_game value on this build. For mp, coop
and zm alike the value C1 has, and the only one it will accept, is `""`. Setting
anything else would (a) be rejected by the validator unless it is `mods/<x>`, and
(b) if accepted, add a search path to a directory that does not exist, changing
nothing except the pure lists and the browser "game" key.

---

## 3. Where fs_game reaches the client from the server — and what C1 does with it

### 3a. Verification of the `patch_doc4.py` claim

`alpha0022/_scratch/patch_doc4.py:87-89` claims the strings `fs_game`, `sv_pure`,
`sv_referencedIwds`, `sv_referencedFFNames`, `FS_Restart`, `FS_ConditionalRestart`
"do not exist anywhere in the image".

**MEASURED — the claim HOLDS for the strings** (byte scan of the whole 33.6 MB
image, ASCII and UTF-16LE): `fs_game` 0 hits, `sv_pure` 0, `sv_referencedIwds` 0,
`sv_referencedFFNames` 0, `FS_Restart` 0, `\fs_game\` 0, `fs_ignoreLocalized` 0,
`sv_allowDownload` 0. (For contrast `fs_basepath`/`fs_homepath`/`fs_cdpath` DO
exist, once each, but only inside `Com_Printf` format strings.)

**MEASURED — but the CONCLUSION needs correcting on two points:**

1. The absence of the string `fs_game` proves nothing on its own: **every** dvar
   name in this build is stripped to a decimal id, so `fs_game` could not appear
   under that spelling. The dvar is present as `"1006"` (§1).
2. `FS_ConditionalRestart` and `FS_Restart` **exist as code** even though their
   names do not. `FS_ConditionalRestart` is at VA `0x00618910` and is called from
   `0x084B188F` (in `.tvm0`, obfuscated). The tell-tale source string survives:
   `0xC49434 "CL_ParseGamestate: restarting file system due to checksumFeed"`
   (neighbours `0xC49408 "CL_ParseGamestate: end wait on fast files"`,
   `0xC49474 "CL_ParseGamestate: comparing files with server"`).
   So patch_doc4's *operational* conclusion — the FS restart is driven by the
   gamestate **checksumFeed**, which the emulator already drives via `fs_crc` — is
   right; its premise ("the function doesn't exist") is not.

### 3b. `connectResponse %s` — `src/sv_client.c:662`

**MEASURED: C1 IGNORES the argument.** The handler is at `0x004967EB`
(`"connectResponse"` @`0xC47F78`, two xrefs: `0x004967F8` = the client parse,
`0x005D17E2` = the server send). Its whole body:

```
4967EB  if (stricmp(argv[0],"connectResponse")) -> next handler
49680C  if (connstate >= 5) -> "Dup connect received.  Ignored."          (0xC47F88)
496820  if (connstate != 4) -> "connectResponse packet while not connecting." (0xC47FAC)
49682F  NET_CompareAdr(from, clc.serverAddress)  (0x5A3680)
4968A1  mismatch -> "connectResponse from a different address.  Ignored." (0xC47FE4)
496937  Netchan_Setup (0x5A2160); CL_SetConnState(6) (0x486E90); zero 0x6C bytes; ret 1
```

There is **no `Cmd_Argv(1)` read, no Dvar_Set, no filesystem call** on that path.
The `%s` payload is discarded. (INFERRED: it is a CoD4-1.7/IW4OL-era mod-stats
extension that this client never implemented.)

### 3c. serverinfo `"game"` key — `src/sv_main.c:1105-1106`

**MEASURED: browser metadata only.** `"game"` @`0xC48BFC`, 3 xrefs.
`0x0049ABD9` is inside `CL_ServerInfoPacket`:
`Info_ValueForKey(info,"game")` -> `strncpy(serverEntry+0x108, value, 0x17)`, i.e.
23 chars into a server-browser record, right between `"2485"` (`+0xC8`) and
`"gametype"` (`+0x120`). `0x004A1429` is the reverse direction — re-packing that
record into an info string for the Scaleform UI. `0x005D5037` is C1's own server
half writing the key. **No filesystem, pure-check or zone effect.**

### 3d. gamestate / systeminfo — `src/sv_main.c` `SV_SetSystemInfoConfig` (`\fs_game\\` @4353)

**MEASURED, two independent reasons this is inert:**

1. The server writes the **ASCII key `fs_game`**, but C1's dvar is named `1006`.
   A generic systeminfo applier keyed on the wire name would look for `1006`; it
   would never match `fs_game`. And there is exactly one reference to the string
   `"1006"` in the image (the registration), so no name-based lookup of fs_game
   in an info string exists anywhere.
2. `patch_doc4.py §7.4` (re-checked, consistent with this scan): **CS[1] has no
   dispatch case at all** — `CG_ConfigstringModified` (`0x004673A3..0x00467460`)
   has cases for 0, 5, 24..423, 425..443, 444.., 1300, 1301, 5363..6061, 6517;
   `CL_ConfigstringModified` @`0x00487440` special-cases only index 3.

`src/sv_main.c:1348-1352` (`MSG_WriteString(msg, fs_gameDirVar->string)` else
`"main"`) is in the **Source-engine master/browser query reply** (the next field
is the literal `"Call of Duty 4 - Modern Warfare"`), not the client gamestate.
C1 never parses it.

**INFERRED (item 3 summary): there is no wire path by which `fs_game` can carry
anything to C1.** Not filesystem restart, not pure check, not zone path —
nothing. The only thing a non-empty fs_game would change on the wire is the
browser `"game"` key, and it would simultaneously break the byte-for-byte parity
of the info strings with an mp match.

---

## 4. How C1 picks its zone chain for coop / zm

**MEASURED — the category comes from the GAMETYPE string, not the map name.**

The zone-list builder is `0x004CCDF0` (`__usercall`: `ecx` = gametype,
`edx` = map name). Sequence:

```
4CCEB0  call 0x4CCD80                 ; append common_mp group (if not loaded):
                                      ;   patch_common_mp, common_mp,
                                      ;   patch_localized_common_mp, localized_common_mp
4CCEBB  edi = gametype                ; from [ebp-0x1EC] = incoming ecx
4CCEC1  Q_strncasecmp(gametype, "zm",   2)  -> zm group     (0xC689AC)
4CCF83  Q_strncasecmp(gametype, "coop", 4)  -> coop group   (0xC42378)
4CD03E  else                              -> mp group
```

Each group appends 4 entries, e.g. for zm:
`patch_common_gametype_zm` (`0xC4E8A8`), `common_gametype_zm` (`0xC4E894`),
`patch_localized_common_gametype_zm` (`0xC4EB70`),
`localized_common_gametype_zm` (`0xC4E8C4`), then `DB_LoadXZones` (`0x08465768`).

Callers confirm the argument order:
`0x00499450` (stack arg = gametype, `esi` = map name) is called by
`0x00499560` = `CL_MapLoading`, which prints
`"Server changing map %s, gametype %s"` (`0xC48830`) with `(esi, [ebp+8])`; and by
`0x0049BB90` = the `preloadmap` console command, whose usage string is
**`"usage: preloadmap <map name> <game type>"`** (`0xC48DE4`) and which passes
`argv[1]` in `esi` and `argv[2]` on the stack. Further call sites exist in
`.tvm0` (`0x084CBC98` -> `0x00499450`; `0x0839DA81`, `0x084AFB6D`, `0x085A4673` ->
`0x004CCDF0`), i.e. the normal `CL_ParseGamestate` path.

**MEASURED — the same zm(2)-then-coop(4) prefix test also selects the const
configstring table.** `0x00612850` does `Q_strncasecmp(x,"coop",4)` then
`Q_strncasecmp(x,"zm",2)` to choose between
`"mp/constConfigStrings_mp.csv"` (`0xC6DF94`),
`"mp/constConfigStrings_coop.csv"` (`0xC6DFB4`),
`"mp/constConfigStrings_zm.csv"` (`0xC6DFD4`).
`alpha0022/zone_crc.py:381-405` reproduces this correctly (its "zm first, then
coop" order matches `0x004CCEBB`; `0x00612850` happens to test coop first — the
prefixes are disjoint, so the answer is identical).

**MEASURED — the load order, from real client logs.**
`main/console_mp.log`, `DB_LoadXFile:` lines, MP (16 Sep 2026 23:21):

```
mp_killhouse_sh_load
patch_common_gametype_mp / common_gametype_mp
patch_localized_common_gametype_mp / localized_common_gametype_mp
patch_mp_killhouse_sh / mp_killhouse_sh
ffotd_client
```
`common_mp` + `localized_common_mp` are loaded once at process start (the same
log, earlier: `patch_common_mp`, `common_mp`, `patch_localized_common_mp`,
`localized_common_mp`) and are not reloaded per level — which is exactly what
`0x004CCD80`'s "already loaded?" guard (`call 0x4CD7D0`) does.

ZM (`main/console_mp-003.log`, 16 Sep 2026 00:39):
```
zm_prototype_sh_load
patch_common_gametype_zm / common_gametype_zm
patch_localized_common_gametype_zm / localized_common_gametype_zm
patch_zm_prototype_sh / zm_prototype_sh
```

**MEASURED: `fs_game` plays NO part in that selection.** The function
`0x004CCDF0` and everything it calls reference only the two argument strings and
a fixed table of literal zone names at `0xC4E858..0xC4ECF8`; `[0x02A9DDFC]` is
never touched anywhere in `0x004CC000-0x004CE000` (see the complete xref list in
§1).

---

## 5. The `coop_*` playlist spelling vs the level zone

**MEASURED — the shipped set** (`client_shipRetail\chinese`, 90 files) contains
both spellings side by side:

```
coop_training_mp_killhouse_sh.ff        41 861 397 B   (full level zone)
coop_training_mp_killhouse_sh_load.ff       24 853 B   (loadscreen zone)
patch_coop_training_mp_killhouse_sh.ff      24 853 B
mp_killhouse_sh.ff                      44 695 829 B
mp_killhouse_sh_load.ff                     24 853 B
patch_mp_killhouse_sh.ff                    24 853 B
common_gametype_coop.ff                 49 307 925 B
```
Others follow the same `coop_<mode>_<basemap>` shape:
`coop_spec1_mp_killhouse_sh`, `coop_defense_mp_crash_tropical`,
`coop_prolog_mp_crash_intro`, `coop_spec_mp_{crash_tropical,estate_tropical,fav_tropical}`,
`coop_take_mp_{estate_tropical,fav_tropical}` — and every one of their `mp_*`
tails is itself a shipped zone.

**MEASURED — C1 loads BOTH, and derives the base map zone by string surgery.**
Tail of `0x004CCDF0`, starting `0x004CD0FE` (`edi` = map name):

```
4CD0FE  Q_strncasecmp(map, "coop_", 5)                 ; 0xC6DFF8
4CD113  not coop -> 0x4CD1D6 (single-zone path)
4CD11F  strchr(map + 5, '_')  ; must exist
4CD130  sprintf(tmp, "patch_%s", map)                  ; 0xC4E9D4
4CD149  list = { tmp, map }
4CD16D  edi = strchr(map + 5, '_') + 1                 ; <-- the base map name
4CD1A8  DB_LoadXZones(list, 2, 0)                      ; loads patch_coop_*, coop_*
4CD1D6  sprintf(tmp, "patch_%s", edi)
4CD1E7  list = { tmp, edi, "ffotd_client" }            ; 0xC4F7DC
4CD22E  DB_LoadXZones(list, 3, 0)
```

So `coop_training_mp_killhouse_sh` -> skip `coop_` -> `training_mp_killhouse_sh`
-> first `_` -> `+1` -> **`mp_killhouse_sh`**. Full chain for a coop match:

```
common_mp  (once)
common_gametype_coop           <- from the GAMETYPE prefix
coop_training_mp_killhouse_sh  <- the map name itself
mp_killhouse_sh + ffotd_client <- the substring after the second '_'
```

> **PARTLY SUPERSEDED — see §7 (round 2).** The two capture lines below are quoted
> correctly, but (a) the 16:18 load was **not** driven by a lobby room-info push —
> this capture contains no `SET_MAP` push at all before 20:05 — and (b) the causal
> claim about the `CA_LOADING` drop was overclaimed. §7 resolves both.

**MEASURED — confirmed live in the lobby capture**
`CODOL\re\alpha0022\dw-capture.log`. The client's own `ClientLoadTime` telemetry,
line 2232 (16:18:56), when the only map string in play was
`coop_training_mp_killhouse_sh`:

```
ClientLoadTime|...|2|10350|  2005 common_mp|  1324 common_gametype_coop|
              1720 coop_training_mp_killhouse_sh|  4956 mp_killhouse_sh|NONE
```

Four zones, in exactly the order the disassembly predicts.

**MEASURED — and the counter-example, same capture, line 14087 (17:51:58),**
where the *gamestate* announced the stripped level name:

```
ClientLoadTime|...|17|3448|  1051 common_gametype_coop|  1414 mp_killhouse_sh|NONE|NONE|NONE
ClientDisconnect|...|181 aa12_mp 0 2|CA_LOADING|0.025000|...
```

Only two zones — the `coop_training_mp_killhouse_sh` zone was never loaded — and
the client dropped while still in `CA_LOADING`.

**INFERRED:** the comment at `src/filesystem.c:2752-2756` ("a coop match loads an
*mp_* level zone ... so the map name alone says 'mp' for it") is half right and
half wrong. Right: the map name alone does not carry the category — a separate
category string does. Wrong: the map name the server announces must be the
**coop_ playlist spelling**; C1 expands it to the base `mp_` zone itself.
Announcing `mp_killhouse_sh` costs the client the entire coop content zone.
`startgame_map.py:277-303`'s split (dwRoomInfo gets the coop spelling, gamestate
gets the mp spelling) is therefore only correct for the *preload*.

> **CORRECTION (§7.3):** the original text continued "...the gamestate half is what
> produced the 17:51:58 `CA_LOADING` drop above." That is **overclaimed and now
> retracted.** The drop's proximate cause is the error code in the record itself,
> `181 aa12_mp 0 2` — a const-configstring/weapon mismatch (the server published
> an `_mp` weapon name into a coop const table), which is a *different* bug from
> the missing coop zone. The missing zone is real and measured; that it caused
> that particular drop is not established.

---

## 6. Recommendation

1. **Stop using `fs_game` as the category carrier.** Keep
   `FS_CoDOLNormalizeGameDir()` (it already consumes and empties the token, so
   the wire stays clean) as a compatibility shim for the lobby's existing rcon,
   but make `codol_zoneType` the documented authority.
   Server value to set for coop and for zm: **`""` (empty) in both cases.** There
   is no legal category value; `"coop"`/`"zm"` are rejected by C1's own validator
   at `0x00617810` and would be inert even if accepted.
2. ~~**`g_gametype` is the category on the wire.** CS[0] `g_gametype` must begin
   with `coop` or `zm` ...~~
   **RETRACTED — see §7.4. Replaced by:** the **gamestate `type` field** must be
   exactly `mp` | `coop` | `zm`. That is the string `0x004CCEBB`/`0x004CCF83`
   prefix-test and `0x00612850` reads, and the server **already sends it**
   (`CODOL_WriteServerGamestate(msg, sv_mapname->string, codol_zoneType->string, ...)`,
   `src/sv_main.c:3599`). **No `g_gametype` rename is needed or wanted.**
3. **Send the coop playlist spelling as the gamestate map.** For coop entries the
   gamestate map string should be `coop_training_mp_killhouse_sh`, not
   `mp_killhouse_sh`. C1 loads the base `mp_*` zone from it automatically (§5),
   on the same code path for every caller. **Prerequisite (§7.3):** the server
   must also mount that map identity server-side — `CODOL_ServerMapIdentityMatches`
   (`src/codol/snapshot/codol_sv_state.c:85`) requires the announced map to equal
   the mounted one, and `fs_crc`/const-configstrings are keyed on it. This is not
   a lobby-only change.
4. **`\fs_game\\` in `SV_SetSystemInfoConfig` is dead weight** — the key spelling
   C1 would need is `1006`, and CS[1] has no dispatch case at all. Leaving it is
   harmless; it is not a carrier.
5. **The FS restart that does exist is checksumFeed-driven**
   (`FS_ConditionalRestart` @`0x00618910`, string `0xC49434`), and the emulator
   already drives it through `fs_crc`. Nothing about coop/zm needs an FS restart.

### Open / not established here

* **INFERRED, unverified:** no coop level load appears in any surviving
  `main/console_mp*.log` (`DB_LoadXFile:` lines for `coop*` / `common_gametype_coop`:
  zero hits across all 21 logs). All coop evidence above comes from the client's
  own `ClientLoadTime` telemetry inside `CODOL\re\alpha0022\dw-capture.log`. A
  fresh coop attempt with console logging on would upgrade §5 from "telemetry +
  disassembly" to "engine log".
* The `.tvm0` call sites into `0x00499450` / `0x004CCDF0` / `0x00618910` are
  obfuscated (junk-jump + `lea`/`call` trampolines); I did not decompile them, so
  the gamestate path's argument sourcing is established structurally (§7.4)
  rather than by reading the gamestate parser itself.

---

## 7. Round 2 — resolutions requested by the coordinator (2026-09-17)

### 7.0 The one fact that reframes everything: this capture has NO room-info push

**MEASURED.** Every `PUSH push 7 ...` line in
`CODOL\re\alpha0022\dw-capture.log`, in order:

* 16:18:40 .. 19:41:39 — **`START_GAME` only**, 29 pushes, **zero `SET_MAP`**.
* The first `SET_MAP` push in the whole file is at **20:05:27** (line 31318),
  2 h 14 m after the 17:51 event.
* **Every** `SET_MAP` in the file carries `mp_killhouse_sh` — the coop playlist
  spelling is never pushed by the lobby anywhere in this capture.

So neither the 16:18 nor the 17:51 zone load can have been caused by a lobby
room-info push. The `coop_training_mp_killhouse_sh` string at 16:18 came from the
**client's own** room info / playlist selection (the UI telemetry in the same
batch is a walk through `matchQuickCoopMapView` / `matchQuickCoopInfoView`).

### 7.1 The full timeline (MEASURED, reconstructed from the capture)

`ClientLoadTime` field 7 is a **per-session counter**, not a load-kind code; it
resets to 0 when the client process restarts. Loads, pushes and disconnects, with
capture line numbers:

```
 277   16:16:57  LOAD idx=0   ui_viewer_mp                       <- session A starts
 655   16:17:51  LOAD idx=1   ui_viewer_mp
1918   16:18:40  PUSH START_GAME
2232   16:18:56  LOAD idx=2   common_mp  common_gametype_coop
                              coop_training_mp_killhouse_sh  mp_killhouse_sh
                              (same batch: QoSProbeStart, then QoSProbeFail)
2538   16:21:41  LOAD idx=0   ui_viewer_mp                       <- session B starts
4008   16:23:18  LOAD idx=1   common_gametype_mp  mp_crash_tropical
4297   16:24:34  DISC EXE_ERR_SERVER_TIMEOUT  CA_CONNECTING  0.056 s
4641   16:25:12  LOAD idx=3   mp_killhouse_sh          (map zone only)
5150   16:25:44  DISC EXE_DISCONNECTED  CA_ACTIVE  31.315 s
5742   16:53:04  LOAD idx=0   ui_viewer_mp                       <- session C starts
 ...            (13 mp_crash_tropical matches, various failures)
13966  17:51:53  PUSH START_GAME
14087  17:51:58  LOAD idx=17  common_gametype_coop  mp_killhouse_sh
14087  17:51:58  DISC 181 aa12_mp 0 2  CA_LOADING  0.025 s
```

### 7.2 (1a) What drove the 16:18 load — a preload, and NOT a gamestate

**MEASURED.** It was a **client-side preload**, driven by neither of the two
inputs the coordinator named:

* Not a lobby room-info push — there was none (§7.0).
* Not the gamestate — **the client never reached a gamestate.** The same
  telemetry batch that carries the 4-zone `ClientLoadTime` also carries
  `QoSProbeStart` followed by `QoSProbeFail` to `127.0.0.1:17733`, and session A
  produces no `ClientDisconnect` with a connection state above `CA_CONNECTING`.
  A gamestate is only parsed at `CA_CONNECTED` -> `CA_PRIMED`.

**INFERRED:** the map string was the client's own dwRoomInfo value
(`coop_training_mp_killhouse_sh`), selected through the coop UI in that session,
fed to the same zone builder `0x004CCDF0`. The shape of the result (4 zones,
including the `coop_`-split base zone) is exactly what that function produces and
matches the `preloadmap <map name> <game type>` argument shape (§4).

**Contrast, MEASURED:** a *gamestate* load is visible in the same telemetry and
looks different. Session B `idx=3` (16:25:12) loaded `mp_killhouse_sh` **alone**
— no `common_gametype_*`, because `common_gametype_mp` was already resident from
`idx=1` — and that session went on to `CA_ACTIVE` for 31.3 s. So gamestate loads
do appear as `ClientLoadTime` rows, and they load the map zone the gamestate
names.

### 7.3 (1b) Why the playlist zone did not load at 17:51 — and (1c) whether 16:18 worked

**(1b) The premise is REFUTED, MEASURED.** "dw-capture pushes room info with the
session map" is not true of this capture: the first `SET_MAP` push is at 20:05:27
and every one of them says `mp_killhouse_sh` (§7.0). There was no preload with the
playlist spelling at 17:51, so nothing could have produced that zone.

The 17:51 row is unambiguously the **gamestate** load: it follows a successful
connect (the client reached `CA_LOADING`, past `CA_CONNECTED`), it switched the
category zone from `common_gametype_mp` (resident since 17:30) to
`common_gametype_coop`, and it loaded `mp_killhouse_sh` — the exact pair
`(type=coop, map=mp_killhouse_sh)` the server announced.

**The crux therefore resolves in favour of recommendation 3, and the disassembly
is what settles it, not the telemetry:** the `coop_` expansion at `0x004CD0FE` is
**inside `0x004CCDF0` itself**, the single zone-list builder shared by *every*
caller — `preloadmap` (`0x0049BBFC`/`0x0049BC0C`), `CL_MapLoading`
(`0x004995AD`) and the gamestate path (`.tvm0 0x084CBC98` -> `0x00499450`).
Nothing on the gamestate path is special-cased. The zone set is a pure function
of the map string the client is handed, whoever hands it over:
`coop_training_mp_killhouse_sh` -> coop zone **plus** `mp_killhouse_sh`;
`mp_killhouse_sh` -> base zone only. 16:18 and 17:51 are two measured instances of
exactly that function.

**Cold-vs-incremental is a real confound, but it only explains `common_mp`.**
`common_mp` and `common_gametype_*` are guarded by the "already loaded?" check at
`0x004CCD80` / `0x004CD7D0`; the **map zones at `0x004CD0FE` / `0x004CD1D6` have
no such guard** — they are appended unconditionally. So residency cannot explain
the absence of `coop_training_mp_killhouse_sh` at 17:51, and in any case 13
`mp_crash_tropical` loads sat between 16:18 and 17:51.

**(1c) No — the 16:18 session did NOT reach `CA_ACTIVE`. MEASURED.** It never
connected at all: `QoSProbeFail`, no disconnect record above `CA_CONNECTING`, and
the client process restarted ~3 min later. "Loaded four zones" is exactly not the
same as "worked". The only `CA_ACTIVE` in that stretch (31.3 s at 16:25:44)
belongs to session B's **mp** match on `mp_killhouse_sh`; `common_gametype_coop`
was never loaded in session B.

**Consequences for recommendation 3, stated plainly:**

* It is supported by the disassembly (one shared code path) and by two measured
  instances, but it has **never been observed working end-to-end** — no coop
  session anywhere in this capture reached `CA_ACTIVE`.
* It is **not a lobby-only change**. If the gamestate announces
  `coop_training_mp_killhouse_sh`, the server must mount that identity too:
  `CODOL_ServerMapIdentityMatches()` (`src/codol/snapshot/codol_sv_state.c:85`)
  refuses to build a gamestate whose map differs from the mounted one, and
  `fs_crc` / const-configstrings are keyed on the same name.
* The 17:51 drop is **not** evidence for it. Its proximate cause is
  `181 aa12_mp 0 2`: the server published an `_mp` weapon name into the **coop**
  const table. That is an independent bug (compare `181 beretta_so 0 2` at 17:01,
  17:04, 17:05 and 17:18, and `181 cheytac_mp 11 10` at 17:30 on the mp table).

### 7.4 (2) The category string is the gamestate `type`, NOT `g_gametype` — I was wrong

**I am correcting myself. `map_handoff.py:85-108` is the better evidence and my
recommendation 2 was wrong as written.** What I had right was the *mechanism*
(`0x004CCDF0` prefix-tests its second argument); what I had wrong was the
*source* of that argument — I labelled it "g_gametype" from the `preloadmap`
usage string's wording ("game type") without checking where the connect path
fills it from.

**MEASURED — the zone loader never reads `g_gametype` or `mapname`.**
The strings `"g_gametype"` (`0xC408D4`) and `"mapname"` (`0xC41CD0`) occur once
each in the image, with 22 and 12 code references respectively. **Zero** of them
fall inside `0x00499000-0x0049A000` or `0x004CC000-0x004CE000` (the zone-load
code). `g_gametype` is read by `CG_ParseServerinfo` at `0x00465BD8` and by the
server/browser code — never by the zone chooser. `0x00499450` passes its own
stack argument straight through (`0x00499524  mov ecx, ebx ; mov edx, esi`);
there is no info-string lookup anywhere in it.

**MEASURED — the category arrives as the SECOND STRING of the message.**
Decoded the `loadingnewmap` out-of-band handler, the one non-obfuscated caller of
`CL_MapLoading` (`0x00499560`, reached from `0x00496F75`):

```
00496E9B  Q_stricmp(argv[0], "loadingnewmap")          ; 0xC4812C
00496F32  esi = msg_t*
00496F38  lea eax,[ebp-0x448] ; call 0x0059F6D0        ; MSG_ReadString -> STRING #1
00496F43  strncpy([ebp-0x48], eax, 0x3F)
00496F66  lea eax,[ebp-0x448] ; call 0x0059F6D0        ; MSG_ReadString -> STRING #2
00496F71  push eax                                     ; stack arg = STRING #2
00496F72  lea eax,[ebp-0x48]                           ; reg  arg = STRING #1
00496F75  call 0x00499560                              ; CL_MapLoading
00499560  Com_Printf("Server changing map %s, gametype %s", STRING#1, STRING#2)
00499524  -> 0x004CCDF0(ecx = STRING#2, edx = STRING#1)
```

(`0x0059F6D0` is `MSG_ReadString`: it walks `[esi+0x14/0x18/0x1C]`, the msg cursor
triple, byte by byte into the caller's buffer.)

Two adjacent strings, map first, category second. **That is byte-for-byte the
same field order the server writes into the gamestate:** `CODOL_WriteGamestate`
(`src/codol/snapshot/codol_configstrings.c:291-294`) emits
`byte 2 / long cmdseq / string map / string zone_type / long const_crc / ...`,
fed from
`CODOL_WriteServerGamestate(msg, sv_mapname->string, codol_zoneType->string, ...)`
(`src/sv_main.c:3599`).

**INFERRED (strong):** the gamestate path passes the gamestate's own `type`
string, for three converging reasons — the wire layout matches `loadingnewmap`
field-for-field; the zone loader demonstrably cannot look up `g_gametype`; and
CS[0] is parsed by `CG_ParseServerinfo`, which runs at `CG_Init`, i.e. **after**
the zones are already mounted, so it cannot be an input to choosing them.

**Corroborated by `map_handoff.py:85-108`'s A/B**, which is direct behavioural
evidence for the source and which I should have deferred to:
`map: mp_killhouse_sh / type: coop` -> coop const table (`181 beretta_so 0 2`);
`map: mp_crash_tropical / type: mp` -> mp const table, while that run's
descriptor gametype was **"combat"**, not "mp". The 17:51 row in §7.1 is a third
instance: `type: coop` + `map: mp_killhouse_sh` -> `common_gametype_coop` +
`mp_killhouse_sh`.

**So: do not rename or reshape `g_gametype`.** Recommendation 2 becomes "the
gamestate `type` field must be exactly `mp` | `coop` | `zm`", which
`codol_zoneType` already satisfies. Note the prefix test would also accept
`"coopfoo"` / `"zmfoo"`, and would silently bucket any other playlist gametype
name (`"combat"`, `"tdm"`) into **mp** — so `mp`/`coop`/`zm` verbatim remains the
only safe set, matching `map_handoff.py`'s "Send 'mp'" conclusion.
