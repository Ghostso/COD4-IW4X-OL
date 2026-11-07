# `cl_paused` does not return to 0 when the escape menu closes — 2026-09-20

Worker scope: `src/sv_client.c`, `src/sv_main.c`, `src/codol/net/**`.
Every claim below is labelled **MEASURED** (bytes or source read directly) or
**INFERRED**.

---

## 0. The short answer

**Question 1 — is C1 sending the unpause? Not answerable from the current
server, because the server logs nothing about it.** That is the finding, not a
dodge:

* **MEASURED** `grep -rn cl_paused src/` returns exactly two hits, both in
  `src/sv_main.c`, and nothing anywhere parses `cl_paused` out of a userinfo
  string.
* **MEASURED** the `userinfo` client command *is* handled
  (`ucmds[]` in `src/sv_client.c`: `{"userinfo", SV_UpdateUserinfo_f, 0}`), and
  the handler is reached regardless of flood protection — `clientOK` only gates
  the pass-through to `ClientCommand`; the `ucmds` table runs on any
  non-download packet. So updates were arriving and being applied silently.
* **MEASURED** the only trace that ever existed was the `Com_DPrintf`
  ("clientCommand: …") in `SV_ClientCommand`. `com_developer` is 0 in a normal
  boot, so the preserved log (`bin/home/main/qconsole.log`, map
  `zm_prototype_sh`, 214085 bytes, copy kept at
  `/tmp/codol_preserve/qconsole_20260920_preserve.log`) contains **0**
  occurrences of `userinfo` and **0** of `clientCommand`.

Two unconditional diagnostics have been added to close that hole. **One live
boot now answers question 1 definitively.**

**Question 3 is already answered from C1, and the answer is unusually
concrete:** C1 clears `cl_paused` entirely on its own, from three UI paths, and
every one of them is guarded. The guards are in §2.4. The single most important
fact is that **`cl_paused` is an `int` with range 0..2, and every menu-close
unpause is written as `if (cl_paused == 1) cl_paused = 0`.**

---

## 1. What the server does and does not do with pause state (MEASURED)

| Fact | Evidence |
|---|---|
| `DEDICATEDONLY` is **not** defined | `Makefile:70-72` — `IW4OL_DEFINES` is `IW4OL_UPDATE BUILD_NUMBER… CODOL_SERVER`. Both `#ifndef DEDICATEDONLY` blocks are live code. |
| `SV_CheckPaused()` reads `cl_paused->boolean` | `src/sv_main.c:4249` |
| …but `SV_CheckPaused()` is **never called** | its only call site, `src/sv_main.c:4605`, is commented out |
| `SV_SpawnServer` does `Cvar_SetInt(cl_paused, 0)` | `src/sv_main.c:5651` |
| `cl_paused` is not declared anywhere in `src/` | it is an external symbol resolved from the reassembled CoD4 image: `tools/cod4_dasm/objmap.txt:7282  cl_paused, SYM_VAR, 0x1861540` |

**Conclusion (INFERRED, but tightly):** the server's `cl_paused` is a *different
variable* from C1's. It is a leftover CoD4 client cvar in the reassembled
image, written once per map spawn, never read, and never put on the wire. The
server can neither observe nor set the client's pause state today.

`sv_paused` is registered (`src/sv_main.c:3322`, `CVAR_ROM`) but, because
`SV_CheckPaused` is never called, it is never set either.

---

## 2. What C1 actually does (MEASURED by disassembly)

pefile + capstone against
`D:\CoD\CODOL Builds\Call of Duty Online 1.1.1.13\C1.exe`, ImageBase 0x400000,
raw dword scan for `34 20 57 02` over all section raw data plus linear
disassembly with byte-by-byte resume. `tools/codol_c1_disasm.py --xref` was
**not** used.

### 2.1 Registration — and it is not a bool

```
0x00598061  push 0xC2FEAD      ; description "" (stripped)
0x00598066  push 0x2200        ; flags
0x0059806B  push 2             ; max
0x0059806D  push 0             ; min
0x0059806F  push 0             ; default
0x00598071  push 0xC42D64      ; "cl_paused"
0x00598076  mov  [0x025745F8], eax     ; <- the PREVIOUS dvar, "1871"
0x0059807B  call 0x00624420            ; Dvar_RegisterInt
0x00598080  add  esp, 0x40
   ...
0x00598094  mov  [0x02572034], eax     ; <<< cl_paused dvar_t*
```

* **`cl_paused = Dvar_RegisterInt("cl_paused", 0, min 0, max 2, flags 0x2200)`.**
  It is a **three-state int, not a boolean.** Two consumers (`0x0043ABA3`,
  `0x00480BF5`) test `== 2` specifically.
* The string `"cl_paused"` is at `0x00C42D64`, embedded in the stripped
  numeric-name blob (`…"724" "725" "cl_paused" "726" "727"…`) — it really is an
  unstripped survivor.
* `dvar_t` layout: `+0x08` = type byte, `+0x0C` = value (proven from
  `Dvar_GetInt` at `0x006233F0`).
* **There are TWO globals holding the same pointer**: `0x02572034` (store at
  `0x00598094`) and **`0x016DA2DC`** (store at `0x0044D6E1`, from an identical
  second `Dvar_RegisterInt("cl_paused", 0,0,2,0x2200,"")` at `0x0044D6C6`).
  `Dvar_RegisterInt` reuses an existing dvar for a duplicate name (MEASURED in
  its body), so at runtime both point at one `dvar_t` (INFERRED). **Any tool
  that watches only `0x02572034` misses 12 consumer sites** in the
  0x43xxxx–0x48xxxx CG/renderer range.
* The neighbouring dvar `"1871"` → `0x025745F8` is
  `Dvar_RegisterInt("1871", 0, 0, 2, 0x2008, "")` — matches the R18 anchor in
  `docs/CODOL_SWAY_CAUSE_SWEEP_20260916.md` exactly. **INFERRED: it is
  `sv_paused`**; it is read paired with `cl_paused` at every consumer, the IW4
  `Com_IsPaused() = cl_paused && sv_paused` idiom.

Key API addresses (MEASURED by body inspection): `Dvar_FindVar` `0x006232C0`,
`Dvar_GetBool` `0x006233B0`, `Dvar_GetInt` `0x006233F0`, `Dvar_RegisterBool`
`0x00624370`, `Dvar_RegisterInt` `0x00624420`, `Dvar_RegisterString`
`0x00624740`.

### 2.2 `cl_paused` IS a userinfo dvar — MEASURED, bit 0x200

Read directly out of the info-string builder, not inferred from flag-enum
folklore. `dvar_t` **`+0x04` = flags**.

`Dvar_InfoString(bitmask)` at `0x0059BB00` clears the shared buffer
`0x25DAEE0` and runs `Dvar_ForEach` (`0x00621710`) with the callback at
`0x0059BA60`, whose entire filter is:

```
0x0059BA6B  mov  eax, [esi+4]        ; dvar->flags
0x0059BA6E  test [ecx], eax          ; bitmask & dvar->flags
0x0059BA70  je   skip
            ... Dvar_ValueToString(0x00621C60) ...
0x0059BA95  mov  ecx, [esi]          ; dvar->name == the userinfo KEY
0x0059BA9E  call 0x00628B00          ; Info_SetValueForKey
```

The in-game sender `CL_CheckUserinfo` (`0x004977A0`) supplies the mask as a
literal:

```
0x004977CD  mov  eax, 0x200
0x004977D2  test [ecx+4], eax        ; dvar_modifiedFlags & 0x200
...
0x004977EA  call 0x00621710          ; build from flags & 0x200
0x004977F4  push 0xC48238            ; 'userinfo "%s"'
0x004977FF  call 0x00493BB0          ; CL_AddReliableCommand
```

and the connect sender (`0x00495700`) opens its userinfo buffer with
`push 0x200 / call 0x0059BB00` at `0x00495C3D`. **So bit 0x200 is USERINFO by
definition, and `cl_paused`'s `0x2200` carries it.**

**Correction to a plausible-looking wrong model:** C1's flag enum is *not*
stock IW4. Measured: `0x1` = ARCHIVE (consumed and cleared at `0x00599321`),
`0x200` = USERINFO (IW4 puts USERINFO at `0x2`), `0x2000` = on essentially
every dvar in the binary (`cl_paused` 0x2200, `"1871"` 0x2008, `"1875"` 0x2000,
`name` 0x2000) and is INFERRED to be a blanket CoDOL registration marker, not
an info bit. **`0x8` has no identified consumer** — the earlier guess that it
means `DVAR_CODINFO` is unverified, so `"1871"` being `sv_paused` still rests
only on its pairing with `cl_paused` at every consumer. Also `0x006230C2` does
`test ecx, 0x1200 / jne <error>`: a dvar carrying `0x200` is refused on the
restricted/off-thread set path, i.e. **USERINFO dvars can only be set from the
main thread.**

**Also correct a tempting misreading of the connect capture**
(`docs/CODOL_ZOMBIES_STARTUP_20260915.md:971`):

```
connect 79a6c4813004f32e "\cl_paused\0\name\Chud\xuid\…\qport\-27166\onlineStats\0"
```

`name`, `xuid`, `natType`, `rank`, `clan`, `checksum`, `2490`, `statver`,
`quickmatched`, `invited`, `csi`, `session`, `partyid`, `qport`, `onlineStats`
are **not** userinfo dvars. They are literal string constants in one contiguous
`.rdata` block (`0x00C47C5C..0x00C47CF8`) appended by hand-rolled
`Info_SetValueForKey` calls at `0x00495D6D` onward — `name` is registered with
flags `0x2000`, no `0x200` at all. `cl_paused` appears **first** in that string
simply because the `Dvar_InfoString(0x200)` dump is written before the literals
and `Dvar_ForEach` walks the dvar array in registration order.

The practical consequence is the one that matters: the server's view of the
client's pause state is *already* arriving for free in the userinfo, and needs
only the parsing that §3.1 now logs — no new protocol.

### 2.3 Every write of the pause state

| Site | Function | Value | Guard |
|---|---|---|---|
| `0x00497CD1` | `CL_InitRenderer` (`0x00497C60`) | **0** | none — startup / `vid_restart` |
| `0x00594C21` | engine init (`0x00594B70`) | **0** | none |
| `0x005ECB3B` | disconnect / "Leave" (`0x005ECB00`) | **0** | none; clears `KEYCATCH_UI`, then `Cmd_ExecuteString("disconnect")` |
| `0x005EFFB5` | `UI_RunMenuScript` (`0x005EF880`) | **1** | UI script token is the literal `"Controls"`; then `Key_SetCatcher(0x10)` |
| `0x005F0107` | `UI_RunMenuScript` | **0** | UI script token `"closeingame"`; unconditional once matched |
| `0x005F34DC` | `UI_SetActiveMenu`-style (`0x005F3490`), `enable != 0` | **1** | skipped if already 1 |
| `0x005F355F` | same function, `enable == 0` | **0** | **only if `cl_paused == 1` exactly** |
| `0x005F38EE` | `UI_KeyEvent` (`0x005F3760`) | **0** | see §2.4 — the normal escape-menu path |

### 2.4 The normal "closed the escape menu" unpause, and its gates

`UI_KeyEvent` at `0x005F3760` (callers `0x00493462`, `0x0049357F`,
`0x004935DC`, `0x004936E7`, `0x004938C9`, all in the `Key_*` module).
All of the following must hold **within the same key event** or the unpause is
skipped:

1. `[0x28339E0] != 0` — UI context initialised.
2. the calling thread is the main thread (`[0x2609030]`).
3. `0x00A80380()` returns 0 — a busy/loading guard.
4. **`Menus_TopVisible(&uiContext)` (`0x00606E00`) returns 0** — *no menu is
   left open and visible*. `0x00606E00` walks the stack top-down and returns
   the first entry whose flags at `[menu+0x48]` have bits `0x4|0x2` set.
5. **the UI key-catcher bit `0x10` in `[0x016FC2E0]` is still set** — it is
   cleared immediately afterwards by `Key_RemoveCatcher(~0x10)`.
6. **`Dvar_GetInt("cl_paused") == 1` exactly**
   (`0x005F38E2  cmp eax,1 / jne DONE`).

Only then: `0x005F38EE  Dvar_Set*ByName("cl_paused", 0)`.

**This is the crux.** Three ways the flag gets stranded at 1 with the menu gone:

* **Gate 4** — some other menu is still open and visible. The escape menu
  closes, the stack is not empty, the unpause never runs.
* **Gate 5** — something cleared `KEYCATCH_UI` *before* the key event. C1's
  server-command `'r'` handler (`0x00468060` → `0x005F4F20`) does exactly that:
  it empties the open-menu list and then clears `KEYCATCH_UI`, and it **never
  touches `cl_paused`**. A server-sent `r` landing while the escape menu is up
  tears the menu down behind the client's back and permanently disarms the
  unpause.
* **Gate 6** — `cl_paused` is 2, not 1. Nothing in readable code writes 2, but
  the registered range is 0..2 and two consumers test for it.

Note also that **the unpause only ever runs inside a key event.** If the last
menu is closed by any route that does not pass through `UI_KeyEvent`, this path
never fires at all; the only fallbacks are `UI_SetActiveMenu(enable=0)`
(`0x005F355F`, itself gated on `== 1`) and the `"closeingame"` UI script token
(`0x005F0107`).

### 2.5 Honest caveats — Themida

* `0x083C5D50` (`Dvar_SetBool`) and `0x0845E7F2` (`Dvar_Set*ByName`, `esi` =
  name, `edi` = value) are inside the virtualised `.tvm0` section at
  `0x082F8000`. Their entry bytes are obfuscated dispatch stubs
  (`call $+5 / lea reg,[reg-imm] / jmp reg`). Their identity is **INFERRED**
  from call-site shape, argument counts and the IW4 inline idiom that appears
  verbatim at `0x00594C0E` and `0x005ECB27`. **It cannot be proven from the
  bytes whether they clamp or validate the value**, which is why gate 6 cannot
  be ruled out statically.
* `0x08411826` (`Menus_CloseAll`, called at `0x005F3868`) is also `.tvm0` and
  unreadable.
* `.tvm0` hit `0x083879D5` pushes the `"cl_paused"` string after a
  `Key_RemoveCatcher`, through an unresolvable indirect
  (`lea eax,[eax+0x12BF9E]; jmp eax`). It looks like a stolen copy of a
  close-menu/unpause sequence; no claim is made about what it sets.
* There is **no `.reloc`** section, so the raw dword scan is the only
  enumeration method. A Themida VM bytecode stream could carry the address in
  encrypted form; that blind spot cannot be closed statically.

### 2.6 Will the 1→0 edge actually be reported? YES (MEASURED)

This was the one thing that could have made an empty log ambiguous. It does
not. `CL_CheckUserinfo` (`0x004977A0`, 44 instructions, all plain `.text`) has
exactly one caller, `0x00497960` inside `CL_Frame` (`0x00497940`), which itself
has exactly one caller, `0x00599C10` inside `Com_Frame` (`0x00599500`). Its
gates:

| Gate | Test |
|---|---|
| 0 | `[0x016FC2D9] != 0`, in `CL_Frame` at `0x00497941` — else the whole block is skipped |
| 1 | `cls.state (`[0x016FC2E8]`) >= 4` (`0x004977A4`) |
| 2 | bail **iff `cl_paused != 0` AND `sv_paused != 0`** (`0x004977B2`..`0x004977C2`) — a `Com_IsPaused()`-style conjunction, *not* a test on `cl_paused` alone |
| 3 | `dvar_modifiedFlags & 0x200` (`0x004977D2`) |

`dvar_modifiedFlags` is thread-local: `*(DWORD*)(*(void**)fs:[0x2C] + 4)`.
`Dvar_SetVariant` (`0x00622D30`) ORs the dvar's own flags into it at
`0x00623107`, so **any** write to `cl_paused` sets bit `0x200`. That OR lives
in plain `.text` even though `Dvar_SetBool` at `0x083C5D50` is Themida'd, since
every set path must reach the `.text` core to change `+0x0C`.

Therefore, on the frame C1 writes `cl_paused = 0`:

* gate 2 passes trivially — the value is *already* 0 when `CL_CheckUserinfo`
  reads it;
* gate 3 passes — the write just set `0x200`;
* gates 0/1 hold in a live match.

**So the unpause edge is sent on the very frame it happens.** The diagnostic in
§3.1 is a clean binary test: no `cl_paused "1" -> "0"` line means C1 genuinely
did not clear the dvar.

*Separate real defect, worth knowing:* `Com_Frame` clears the bit
**unconditionally every frame** at `0x00599C1E`
(`and dword [eax+4], 0xFFFFFDFF`), immediately after `CL_Frame` returns,
whether or not `CL_CheckUserinfo` consumed it. There is no re-arm, no pending
queue. **Any USERINFO dvar changed on a frame where `CL_CheckUserinfo` bails —
`cls.state < 4`, `[0x016FC2D9] == 0`, or `cl_paused && sv_paused` — is never
reported to the server at all.** The 0→1 pause edge is specifically at risk
whenever `sv_paused` is already non-zero. On this server `"1871"`/`sv_paused`
is never replicated to the client, so it should read 0 and both edges should
arrive; if only the unpause shows up in the live log, that is the reason.

---

## 3. What was changed

Both files are in this worker's ownership. Both diagnostics are **unconditional**
`Com_Printf` — not `Com_DPrintf`, not dvar-gated. Userinfo updates and menu
commands are rare, and the whole point is that they must appear in an ordinary
boot without the user changing anything. Neither adds a dvar, per the standing
"no flag proliferation" rule.

### 3.1 `src/sv_client.c` — userinfo key delta (this answers question 1)

`CODOL_LogUserinfoDelta()` is called from `SV_UpdateUserinfo_f` **before** the
string is overwritten. It prints the raw incoming userinfo, then one line per
changed key, tagging the one that matters:

```
CoDOL userinfo 0 raw: "\cl_paused\1\name\Chud\…"
CoDOL userinfo 0: cl_paused "0" -> "1"   <== CL_PAUSED EDGE
```

### 3.2 `src/sv_client.c` — client-command visibility

`SV_ExecuteClientCommand` now prints every inbound client command except the
four high-frequency verbs: `n` (per-edge action notify, C1 `0x499aa0`),
`s`/`score` (scoreboard poll) and `mr` (menu response):

```
CoDOL clientcmd 0: userinfo "\cl_paused\1\…"
```

This is what would catch a menu-close signal that is *not* a userinfo update.

### 3.3 `src/sv_main.c` — outbound menu-command visibility

`SV_AddServerCommand` now prints any reliable command whose verb is a bare
`q`, `u`, `v` or `r`:

```
CoDOL menucmd -> 0 (Chud): r
```

This is the direct test for gates 4 and 5. Verb meanings are **MEASURED** from
`docs/CODOL_C1_COMMAND_DISPATCH.json` (dispatcher `0x469320`, byte map
`0x46a118`): `q` → `0x469816` (open menu), `u` → `0x46984b` (open popup),
`v` → `0x469865` (close popup), `r` → `0x469830` (close-everything teardown) —
all distinct from `s` → `0x469891`, the per-client dvar verb.

**Build (MEASURED):** `obj/codol/sv_client.o` and `obj/codol/sv_main.o` both
compile with exit 0 and no new warnings, using the `tools/BUILD-CODOL.ps1`
environment (Windows `TMP`/`TEMP` pointed at `obj\_tmp`, msys2 ahead on `PATH`)
and a per-object `make` target. **Not linked** — the parent links and promotes.
Line endings verified LF in the working tree before and after, matching `HEAD`.

---

## 4. Where this leaves the diagnosis

**For the reported zm case specifically, the "server sent `r`" explanation is
currently NOT supported (MEASURED):**

* the only native emitters of `q`/`u`/`v`/`r` are
  `src/codol/script/codol_script_menu.c` and two calls in
  `src/scr_vm_functions.c` (see §5);
* `grep -rn "openMenu\|closeMenu\|openPopupMenu\|pulseScriptMenu"` over
  `bin/home/codol_rawfiles/zm/` returns **nothing**. zm runs its own
  `_zombiemode.gsc` trio and does not pull in `_playerlogic.gsc` or
  `_damage.gsc`, which is where the multiplayer `pulseScriptMenu` calls
  (`killedby_card_display`, `youkilled_card_display`, `perk_hide`, …) live;
* `setgravity` / `setjumpheight` are not called from any GSC in the tree.

So a zm match should currently emit **zero** `CoDOL menucmd` lines. Worth
knowing: in **multiplayer** the same code path fires an `r`,`r` pair on every
kill (`_damage.gsc:115,139,142,189,192` → `_playerlogic.gsc:737`
`pulseScriptMenu`), so if this bug also reproduces in mp, gate 5 becomes the
prime suspect there even though it is not the zm explanation.

**This needs one more live boot.** The decisive observation is the pairing:

| What the log shows | What it means |
|---|---|
| `cl_paused "0" -> "1"` on menu open **and** `"1" -> "0"` on close | C1 is clearing it correctly; the freeze is elsewhere — `"1871"`/`sv_paused`, or the clock |
| `"0" -> "1"` only, never the reverse | C1 is not clearing it — gates 4/5/6 in §2.4; next step is deciding which |
| `"1" -> "0"` but no `"0" -> "1"` | expected if `sv_paused` is non-zero on the client at the moment of the pause — see §2.6; harmless, and it still tells us C1 clears the flag |
| neither edge | C1 never changed the value, or `cls.state`/`[0x016FC2D9]` gating is off; read the `CoDOL clientcmd` lines for what C1 sends instead |
| a `CoDOL menucmd -> … r` shortly before a stuck `1` | gate 5 — the server is tearing the menu down behind the client |

Because §2.6 settles that the 1→0 edge is emitted on the frame it happens, the
absence of an unpause line is **not** ambiguous: it means the dvar was never
cleared, and the next step is deciding between gates 4, 5 and 6 of §2.4. The
`CoDOL menucmd` lines discriminate gates 4 and 5 directly. Gate 6
(`cl_paused == 2`) cannot be distinguished from the server, because a value of
2 would still be reported as `cl_paused "1" -> "2"` or `"0" -> "2"` in the
userinfo — so **watch the printed value, not just the presence of an edge.**
Nothing in readable C1 code writes 2, but `Dvar_SetBool`/`Dvar_Set*ByName` are
Themida-virtualised (§2.5) and cannot be proven not to.

---

## 5. Latent defect found on the way (not the pause bug)

`src/scr_vm_functions.c:626` and `:745` send:

```c
SV_SendServerCommandNoLoss(&svs.clients[entityNum], va("v g_gravity \"%d\"", gravity));
SV_GameSendServerCommand(entityNum, 1, va("v jump_height \"%d\"", height));
```

**MEASURED:** in C1's dispatch table `v` (opcode 118) is `0x469865`, the
**close-popup-menu** handler. The per-client dvar verb is `s` → `0x469891`,
which is what `docs/CODOL_SWAY_CAUSE_SWEEP_20260916.md` R22 records as the
working route (`s <numericID> "<value>"`). So `setgravity()` and
`setjumpheight()` set nothing on the client — they fire a popup-close with a
garbage argument.

It is latent today because no GSC in `bin/home/codol_rawfiles/` calls either
builtin, and `src/scr_vm_functions.c` is outside this worker's file ownership,
so it is reported rather than changed. The new `CoDOL menucmd` line will make
it obvious the moment a script does call one.

---

## 6. C1 addresses named in this pass (all MEASURED unless noted)

Recorded so the next investigation does not have to re-derive them. Every one
of these decodes cleanly in `.text`; the only Themida contact in this whole
document is `Dvar_SetBool` `0x083C5D50`, `Dvar_Set*ByName` `0x0845E7F2` and
`Menus_CloseAll` `0x08411826` (see 2.5).

| Address | Identity |
|---|---|
| `0x004977A0` | `CL_CheckUserinfo` — builds and sends `userinfo "%s"` |
| `0x00497940` | `CL_Frame` (sole caller of the above, at `0x00497960`) |
| `0x00599500` | `Com_Frame` (sole caller of `CL_Frame`, at `0x00599C10`) |
| `0x00495700` | connect-packet sender; builds userinfo, clears the USERINFO bit at `0x00496063` |
| `0x0059BB00` | `Dvar_InfoString(bitmask)` |
| `0x0059BA60` | per-dvar info-string callback; tests `dvar->flags & mask` |
| `0x00621710` | `Dvar_ForEach(callback)` (array `0x2AB98E0[]`, count `0x2AB98C4`) |
| `0x00621C60` | `Dvar_ValueToString` |
| `0x00622D30` | `Dvar_SetVariant`; ORs flags into `modifiedFlags` at `0x00623107` |
| `0x006232C0` | `Dvar_FindVar(name)` |
| `0x006233B0` / `0x006233F0` | `Dvar_GetBool` / `Dvar_GetInt` |
| `0x00624370` / `0x00624420` / `0x00624740` | `Dvar_RegisterBool` / `Int` / `String` |
| `0x00628B00` | `Info_SetValueForKey(buf, key, value)` |
| `0x00606E00` | `Menus_TopVisible(uiContext)` — 0 when no menu is open+visible |
| `0x005F3760` | `UI_KeyEvent` (the escape-menu unpause lives at `0x005F38EE`) |
| `0x005F3490` | `UI_SetActiveMenu`-style `(localClientNum, enable)` |
| `0x005EF880` | `UI_RunMenuScript` |
| `0x00497C60` | `CL_InitRenderer` |
| `0x016FC2E8` | `cls.state` |
| `0x016FC2E0` | `keyCatchers` (UI bit `0x10`) |
| `0x025DAEE0` | shared info-string buffer |
| `0x02572034`, `0x016DA2DC` | the two `cl_paused` `dvar_t*` globals |
| `0x025745F8` | `"1871"` `dvar_t*` — INFERRED `sv_paused` |
| `0x081C6290` | one-shot flag consumed by the `UI_KeyEvent` unpause block |

`dvar_t` layout: `+0x00` name, **`+0x04` flags**, `+0x08` type byte,
`+0x0C` value. `dvar_modifiedFlags` is thread-local at
`*(DWORD*)(*(void**)fs:[0x2C] + 4)`.

Reusable disassembly scripts were left at `D:\CoD\_c1scan\` (`c1dis.py`
section map + capstone disassembler that resumes past bad bytes, `callers.py`
E8/E9 rel32 caller scan, `mflags.py` the `fs:[0x2C]` field scan). C1.exe was
not modified.


---

## 7. 2026-09-21 - zombies needs a second ESC; what "fixed in multiplayer" really is

Scope of this pass: `bin/home/codol_rawfiles/zm/**` and this document. No
engine source changed. Tags as above: **MEASURED** = bytes/source/log read
directly, **INFERRED** = reasoning over measured facts.

### 7.1 The zm session log (MEASURED)

`bin/home/main/qconsole.log` (zm_prototype_sh, category zm, server stopped):

```
2077  CoDOL clientcmd 0: userinfo "\cl_paused\1"
2079  CoDOL userinfo 0: cl_paused "0" -> "1"   <== CL_PAUSED EDGE
      ... ~6 s of actor lines; NO "CoDOL menucmd" line anywhere in the file ...
2114  CoDOL clientcmd 0: userinfo "\cl_paused\0"
2116  CoDOL userinfo 0: cl_paused "1" -> "0"   <== CL_PAUSED EDGE
```

* Both edges arrive, so gate 6 of section 2.4 (`cl_paused == 2`) is ruled out
  and C1 *does* clear the dvar - on **some** key press. The log cannot say
  which press.
* The server sent **zero** `q`/`u`/`v`/`r` in the whole session (the 3.3 print
  is unconditional), so gate 5 ("a server-sent `r` tore the menu down behind
  the client") is ruled out for zm. Gate 4 is what is left, and it is the
  client's own doing (7.2).
* `qconsole.log.old` is the previous zm session: `0 -> 1` at line 4273 and
  then `disconnect EXE_DISCONNECTED` - the player left from the pause menu, no
  unpause edge, as expected.
* There is **no mp log with the section 3 diagnostics** on disk (they landed
  09-20; every log since is zm), so "single ESC works in mp" is the user's
  observation, not a measured edge pair.

### 7.2 Why the first ESC leaves the client stuck - the same defect as MP #13 (MEASURED)

This is the bug the Python server documented on 2026-08-21 as *MP #13, "press
ESC twice"* (`alpha0022/docs/pause_menu.md`, `movement_fix.md` section 3),
re-verified here against C1.exe:

1. ESC in play (`CL_KeyEvent`, `0x0049338A..`): with no key-catcher, the
   in-game branch at `0x004933F6` calls the Themida'd pause-menu toggle
   `0x083DA993(localClient, 1|2)`. That opens **two** things: the Scaleform
   `MainPause` movie *and* a classic `.menu`, `sf_pausemenu_minimap`
   (`ui_mp/ingame.txt` + `ui_mp/sf_pausemenu_minimap.menu`, both in
   `common_mp.ff`; the zm client mounts the same mp UI zones,
   `docs/CODOL_CATEGORY_ASSET_TEARDOWN_20260917.md:158`). The only open of
   that panel is `.tvm0:0x0830C7E3 -> Menus_OpenByName 0x00601680`; its
   `staticFlags == 0`, so `Menus_Activate 0x006014D0` gives it **focus**
   (`dynamicFlags |= 6`). `UI_SetActiveMenu(1)` (`0x005F3490`) then writes
   `cl_paused = 1` and `keyCatchers |= 0x10` - that is the `0 -> 1` edge.
2. First ESC to leave: the Scaleform half closes (`cpp_closePauseMenu`,
   `Scaleform_CloseMenu(2) 0x006B7E10`) and the legacy stack is emptied by
   one pass of `0x005F4F20`; the pass that closes a focused menu is **not**
   the pass that releases `KEYCATCH_UI` (`pause_menu.md` 5.4; `0x005F4F3B` /
   `0x005F4F58` here). Result: no menu open, catcher still set, `cl_paused`
   still 1, all keyboard and mouse input routed to the UI.
3. Any further key (the user's "second ESC"): `CL_KeyEvent` sees the catcher
   (`0x004933B3`) and hands the key to `UI_KeyEvent 0x005F3760`; no menu is
   visible (`0x00606E00` returns 0), so `0x005F38AC` releases the catcher and
   `0x005F38EE` writes `cl_paused = 0` - the `1 -> 0` edge at line 2116.

Two facts that closed dead ends this pass:

* **`Menus_OpenByName 0x005F4FB0` refuses a `q` while a legacy menu has focus
  unless `uiMenu` is 6 or 7** (`0x005F5030..0x005F504A`, returns 0). A refused
  `q` is parked in the per-client pending slot `0x016EC420` (`0x00467E44..`)
  and **retried every CG frame** (`0x0046C8B1..0x0046C8CB`) until it succeeds;
  `r` clears the pending slot unconditionally (`0x00468128`). When the name is
  not a loaded menu (`Menus_FindByName` miss) the legacy tail still sets
  `uiMenu = 6`, sets the catcher and runs `Menus_CloseAll`
  (`0x005F5061..0x005F50DD`).
* dvar **`"2711"` is the error-popup flag**, not a UI mode: written 1 by the
  `Com_Error` UI path (`0x005F5430`, strings `error_quit`/`error_popmenu`,
  callers `0x005951C9`/`0x0043B5C2`) and 0 by `0x006080E0` (`com_errorMessage`
  reset). `UI_KeyEvent` uses it at `0x005F37DF` to bypass the "Scaleform owns
  this key" test (`0x006B76D0`: `uiMenu == 7`). The 09-16 commit's "2711
  reads 1 on this client" was a stale error popup, not a category difference.

### 7.3 What the multiplayer "fix" actually is (MEASURED source, INFERRED effect)

Nothing in `src/` reacts to either `cl_paused` edge in any category
(`grep -rn cl_paused src/` is still the two `sv_main.c` hits). What the mp
script tree does, and zm did not, is send the legacy teardown constantly:

| mp source | wire | when |
|---|---|---|
| `_playerlogic.gsc:864-865` `closepopupMenu(); closeInGameMenu();` | `v`, `H` | every spawn |
| `_playerlogic.gsc:737` `pulseScriptMenu` = `openMenu` + `closeMenu()` | `q N`, `r`, `r` | spawn (`perk_display`), perk timers (`perk_hide` x3), every kill (`youkilled_card_display`), every death (`killedby_card_display`: `_damage.gsc:115/142/192`, `_killcam.gsc:131`) |
| `_gamelogic.gsc:605-606, 2215-2216` | `v`, `H` | intermission / end of game |

`q` forces `uiMenu = 6` (`0x005F5065`), and `r` under `uiMenu == 6` runs
`0x005F4F20`; the second `r` is the pass that releases `KEYCATCH_UI`. `H`
under `uiMenu == 2` does the same release. So in a multiplayer match the stuck
state of 7.2 step 2 lasts only until the player's next death, kill, respawn or
perk timer - with bots, seconds - and the pause menu itself is never touched
by it, because while the pause menu is up (`uiMenu == 2`, minimap focused) `q`
is refused and `r` is a no-op. That is the whole "fixed in multiplayer":
incidental, and always a few seconds late. The `_zombiemode.gsc` trio that
replaces `_gamelogic/_playerlogic/_damage` in the zm category sent none of it
- no `closeInGameMenu`, no `closeMenu`, no script menus at all (section 4) -
so a first-ESC stuck state in zm persisted until the player pressed a key.

### 7.4 The change

`bin/home/codol_rawfiles/zm/maps/mp/gametypes/_zombiemode.gsc`:

* `spawnPlayer()` now opens with `self closeMenu(); self closeInGameMenu();`
  - IW4 `_playerlogic::spawnPlayer` (`closepopupMenu` + `closeInGameMenu`) and
  T5 `_globallogic_player::spawnPlayer:8-9` (`closeMenu` + `closeInGameMenu`)
  both do this on every spawn. Our `closeMenu()` with no argument is the
  two-pass `r`,`r` (`src/codol/script/codol_script_menu.c`); `closeInGameMenu`
  is `H`.
* `end_game_watcher()` sends the same pair to every player before
  `freezeControls`, as T5 `_zombiemode::player_intermission:5999-6000` does.

`python tools/codol_script_resolve.py --root bin/home/codol_rawfiles --only zm`
exits 0. The file stays LF. `tools\BUILD-CODOL.ps1 -ObjectsOnly` exits 0
(no C changed). Not linked, not promoted, server not started.

### 7.5 What this does and does not cover (honest bound)

* It gives zm exactly the guaranteed release points mp has: first spawn,
  respawn at the round boundary, game over. In zm a player stuck after a
  first ESC cannot shoot, gets downed, and is respawned at the next round -
  the analogue of the mp death -> `killedby` pulse -> respawn `H` path. In a
  live zm boot the new `r`,`r` at spawn will show up as
  `CoDOL menucmd -> 0 (...): r` pairs; `H` is not in the 3.3 print.
* It does **not** make the first ESC release input mid-round, and nothing
  server-side can: the first ESC emits nothing on the wire (`pause_menu.md`
  section 6 measured every `n` id; 3.2 here filters `n`/`mr`, and no other
  verb appeared between the two edges). The remaining levers are
  1. a blind periodic `q`,`r` while `cl_paused == 1` - safe by construction
     while the pause menu is up (refused / no-op), and it would release a
     stuck catcher within one period; but the client never reports `1 -> 0`
     after such a release (`0x005F4F20` does not touch `cl_paused`), so the
     stream could not stop itself, and the useful window is only the
     sub-second gap before the player's next key press. Deliberately **not**
     shipped: it is the Python `CODOL_PAUSE_UNSTICK` mitigation under another
     name.
  2. a client-side change (`sf_pausemenu_minimap` gaining `staticFlags
     0x100000` so it opens without focus, or the Scaleform close calling the
     `closeingame` uiScript `0x005F00CF`). No shipped menu in `common_mp.ff`
     or `patch_common_mp.ff` references `closeingame`, `ingameclose` or
     `closeForAllPlayers` (inflated zones searched with the alpha0022
     `zone_assets` reader), so there is nothing to open by name that would
     self-release either.
* If the user wants the mid-round case closed regardless, the next step is
  the bounded version of lever 1 (rate >= 4 Hz for the window to matter, and
  a hard cap per pause episode). Reported as an option, not done.

### 7.6 Addresses added this pass (MEASURED)

| Address | Identity |
|---|---|
| `0x00493300..0x0049362C` | `CL_KeyEvent`; ESC in play -> `0x083DA993(local, [local+0x15369EE] ? 1 : 2)` at `0x00493405/0x00493417`; with the catcher set -> `UI_KeyEvent(local, 0x1B, down)` at `0x00493462` |
| `0x083DA993` | Themida'd in-game (pause) menu toggle; 46 `.text` callers |
| `0x015369EE[local]` | "in-game pause UI initialised" byte: set at `0x0044B707`, cleared at `0x004787E5` / `0x00499584` |
| `0x0046C8B1..0x0046C8CB` | per-frame retry of the pending script menu at `0x016EC420` |
| `0x00467D80` | `q` handler: slot <= 31, `cgs.scriptMenus[slot]` empty -> error string `0xC44918`; refused open -> pending slot |
| `0x005F5030..0x005F504A` | `Menus_OpenByName` refusal: focused legacy menu and `uiMenu` not 6/7 -> return 0 |
| `0x005F5061`, `0x005F509B`, `0x005F50BF`, `0x005F50C6` | legacy open tail: `uiMenu = 6`, catcher, `Menus_CloseAll`, `Menus_FindByName` (+ `Menus_Activate 0x006014D0` if found) |
| `0x005F5160` | `H`: `!anyFullscreen && uiMenu == 2` -> `0x005F4F20`; then `Scaleform_CloseMenu(2)` if `uiMenu == 2` or (`uiMenu == 0` and `Dvar("2611")`) |
| `"2611"` | is `ui_opensummary` (the `s`-handler demo-playback refusal string at `0xC44BD0` names it) |
| `0x00468A00` | `s` handler: `cg_objectiveText` -> `cgs+0xBE514`, `cg_objectiveIcon` -> `+0xBE914`, `hud_drawHud` -> `+0xBF090`, `g_scriptMainMenu` -> `+0xBEA14`, `cg_unlockFlagSet` -> `0x00468900`, `cg_vo_prefix` -> `0x0046E060`, **anything else -> `0x00625330(name, value, 0)` generic set-by-name** - the "seven-entry whitelist" in `pause_menu.md` 5.5 is not exclusive |
| `0x006B76D0` | "Scaleform owns input" = `[0x028A668C]->+0xC && uiMenu == 7` |
| `0x005EAC30` | `!Dvar("978") && uiMenu == 7` -> arms `0x081C6290` |
| `0x005F5430` / `0x006080E0` | write `"2711"` = 1 (error popup up) / 0 (error cleared) |
| `0x00601715..0x00601843` | legacy click/key router; when no menu keeps flags `0x4004` -> `UI_SetActiveMenu(local, 0)` (`cl_paused = 0` if it was 1) |

### 7.7 2026-09-29 retest and menu-asset boundary

The user retested Zombies and still needs two Esc presses to resume. The
`spawnPlayer()` and intermission cleanup above cannot address a mid-round Esc:
the first Esc produces no server command or pause-state transition that lets
the dedicated server distinguish a closed Scaleform screen from a still-open
one. Do not mark this fixed on the strength of the GSC cleanup.

Read-only inspection of the cached, inflated 1.1.1.13 `common_mp.ff` confirms
the client menu representation. `ui_mp/sf_pausemenu_minimap.menu` is asset 1569,
type 25, only 48 serialized bytes. Its one menu pointer is a block-3 stream
reference (`0x311e8a0d`), not an inline menu to edit. The actual menu is nested
in `ui_mp/ingame.txt` (asset 1567, type 25, 514740 bytes, 61 menus). Its
`sf_pausemenu_minimap` menuDef begins at blob offset `0x42647`, followed by its
name at `0x427d7`; the serialized static flags at menuDef `+0x44` are zero and
the dynamic flags at `+0x48` are 4. The menu declares 15 items. This matches
the previously traced focused-menu open path.

The local unsigned-fastfile writers support rawfiles, stringtables, and
localize entries. They do not serialize C1 MenuList/menuDef/itemDef dependency
graphs or relocate stream references into a newly packed zone. Copying the
48-byte alias alone would leave its original block-3 reference unresolved in
the new zone. Copying `ingame.txt` wholesale would carry references to earlier
assets and require verified relocation and menu-pool override behavior. A
minimal replacement menu would drop its 15 items and has no C1 validation.
No menu patch was written or installed. The fix remains a client-side menu
close-path repair or a correctly serialized and C1-tested menu override.
