# "The server dies on every post-match map rotation" - 2026-09-16

## Verdict: it is not a crash. It is a clean `quit`.

Three preserved reproductions
(`bin/home/main/qconsole.mapchange-crash-2032.log`,
`qconsole.mapchange-crash-2:2.log`, `qconsole.mapchange-crash-repro3.log`)
are identical, and none of them is a fault.

### What prints the last line

The trailing `---------------------------` (27 dashes) is `src/sv_main.c:3073`,
the **final statement of `SV_Shutdown()`**. Everything above it in the "crash
tail" is `SV_Shutdown`'s own teardown, in source order:

| log text | producer |
|---|---|
| `----- Server Shutdown -----` / `With the reason: EXE_SERVERQUIT` | `SV_Shutdown` entry |
| `t "<name> EXE_SERVERQUIT" PB`, `-- Unacknowledged Server Commands --` | `SV_FinalMessage` |
| `==== ShutdownGame (1) ====`, `SV_FreeClientScriptId` + `SV_FreeClientScriptPers` per slot | `SV_ShutdownGameProgs` |
| `Player <name>, N dropped: EXE_DISCONNECTED`, `SV_FreeClientScriptId`, `Going to CS_FREE` | `SV_DisconnectAllClients` |
| `bdDTLS: saved N association(s)` | `CODOL_NetworkReset` |
| `match report ... (reason mapchange)` | `SV_ClearServer` |
| `---------------------------` | `SV_Shutdown` exit |

`SV_Shutdown("EXE_SERVERQUIT")` has exactly one caller: `Com_Quit_f`
(`src/common.c`). And `Com_Quit_f` prints `quitting...` - which **is present**
in all three logs, a few lines above the "crash" (2032: line 17932; repro3:
line 20879).

There is no asymmetry between a "surviving" and a "fatal" map change in
repro3: it contains one shutdown, not two. `SV_FreeClientScriptId` appearing
without `SV_FreeClientScriptPers` in the second half is correct - `ShutdownGame`
already released `pers` for every slot before `SV_DisconnectAllClients` ran.

The log ends at the banner because `Com_Quit_f` calls `Com_CloseLogFiles()`
immediately after `SV_Shutdown` returns. That is the expected end of a clean
quit, not a truncation.

The match also had not ended: in every reproduction the bots are mid-round
(command time ~190-215 s) and no intermission/`ExitLevel` ran. `map_rotate`,
`vstr nextmap` and `ExitLevel` appear nowhere in any of the three logs.

## Why nothing was written to disk

Two separate defects, both fixed here.

1. **There was no top-level fault handler at all.** `SetUnhandledExceptionFilter`,
   a vectored handler and `SetErrorMode` appeared nowhere in the tree; only
   `Com_Error -> Sys_Error` ever wrote `sys_error.txt`. A real access violation
   would therefore have killed the dedicated server with *no* console line, no
   file and no dialog. (That is not what happened here, but it was one bad
   pointer away from being unknowable.)
2. **Two shutdown paths leave no trace in `qconsole.log`:**
   * A command typed at the Win32 server console echoed through `Sys_Print`
     (`src/sys_main.c:352`), which only feeds `CON_Print` - the GUI window. It
     never reached `Com_PrintLogfile`, so `]quit` is invisible in the log file.
   * The console window's **quit button** (`win_syscon.c`, `QUIT_ID`) calls
     `Cbuf_AddText("quit\n")` with no echo of any kind and no confirmation.

   A third path is silent for a different reason: anything arriving over rcon,
   Source rcon, the webadmin or the GSC `execex()` builtin runs inside
   `Com_BeginRedirect`, and with `logrcon 0` `Com_PrintMessage` sends that
   output **only** to the rcon reply. Verified live: an rcon `status` produced
   no log output at all. *This rules rcon out for these three reproductions* -
   the whole `SV_Shutdown` spew did reach the log, so the quit was not
   redirected.

By elimination the quit came from the server console window (typed command or
quit button), i.e. from the desktop, not from the game, the lobby or the map
change.

## Changes

| file | change |
|---|---|
| `src/win32/sys_win32_crash.c` (new) | `SetUnhandledExceptionFilter` + `signal()` + `atexit` reporter. Writes `bin/codol_crash.txt`: exception name/code, faulting address as `<module>+0xRVA`, access type, full x86 register set, EBP frame chain and a return-address stack scan. Uses raw `VirtualQuery`/`WriteFile` so it survives a corrupted heap. Also exports `Sys_CaptureBacktrace()` / `Sys_SymbolizeAddress()`. |
| `src/win32/sys_win32.c` | installs it as the first statement of `WinMain`; logs the `Com_Quit_f` in `Sys_EventLoopThread`. |
| `src/sys_main.c` | `Sys_Exit` marks the exit as announced so the `atexit` hook only fires on an unannounced `exit()`. |
| `src/common.c` | new `Com_LogLifecycleEvent()`: one `MSG_NORDPRINT` line naming the invoker, power, client and the caller chain - it bypasses the rcon redirect, so it always lands in `qconsole.log`. Called from `Com_Quit_f`. Console command echo now goes through `Com_PrintMessage` instead of `Sys_Print`, so `]quit` reaches the log file. |
| `src/cmd.c` | `Cmd_ExecuteString` logs `quit`, `killserver`, `map`, `map_rotate`, `map_restart`, `fast_restart`. That is the single choke point every dispatcher funnels through. |
| `src/win32/win_syscon.c` | quit button: accept only a real `BN_CLICKED` carrying the button's own HWND in `lParam` (rejections are logged with the raw message), confirm with a modal while a map is loaded, and log the click. |
| `tools/codol_crash_symbolize.py` | resolves `<module>+0xRVA` to `symbol+offset` using the exe's own symbol table (the mingw link keeps it; no `.map` needed). |
| `bin/START-CRASH-TEST.cmd` | isolated instance: own exe, own `CODOL_HOME`, udp/17799. |

## Verified live (isolated instance, udp/17799)

* `rcon crash` (the pre-existing `Com_Crash_f`, `*(int*)0 = ...`) produced a
  complete `bin/codol_crash.txt` naming `codol_dedrun_crash.exe+0x8638`, which
  `i686-w64-mingw32-nm` resolves to `Com_Crash_f` (`00408638 t Com_Crash_f`,
  default image base 0x400000). The frame chain read
  `Cbuf_Execute <- SVC_RemoteCommand <- SV_ConnectionlessPacket <-
  SV_PacketEvent <- NET_Event <- NET_Sleep <- SV_Frame`. Symbolize against the
  **exact** exe that produced the report; RVAs move on every relink.
* `CoDOL lifecycle:` lines appear for an rcon `map`, an rcon `map_rotate`, an
  rcon `quit`, `Com_Quit_f` itself and a console-window quit-button event,
  each with its caller chain, and they survive the rcon redirect.
* The console echo now reaches the log file (`]status` in `qconsole.log`).

## Build

```
make -j8 OS=Windows_NT CC=i686-w64-mingw32-gcc CPP=i686-w64-mingw32-g++ \
     AR=i686-w64-mingw32-ar OBJ_DIR=obj/crash-win32 \
     TARGETNAME=codol_dedrun_crash bin/codol_dedrun_crash.exe
```
