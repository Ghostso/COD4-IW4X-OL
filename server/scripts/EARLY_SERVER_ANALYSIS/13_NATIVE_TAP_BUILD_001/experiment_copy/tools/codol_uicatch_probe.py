r"""Sample C1's UI key-catcher / menu stack / cursor predicate out of the live client.

    python tools/codol_uicatch_probe.py --pid <C1 PID>                    # one shot
    python tools/codol_uicatch_probe.py --pid <C1 PID> --watch --out ui.jsonl

Read-only (PROCESS_VM_READ).  Nothing here writes to the client.

WHY THIS EXISTS
---------------
"Sometimes a cursor draws on the screen as if cl_paused is enabled."  In C1 the
cursor and cl_paused are two faces of the same state: a legacy (non-Scaleform)
UI menu is active.  Everything below was read out of C1.exe 1.1.1.13,
ImageBase 0x400000.

  Server command 'q' (openMenu / openMenuNoMouse)
      0x00469816 -> 0x00467D80
        showCursor = (Cmd_Argc() <= 2 || !*Cmd_Argv(2))   0x00467E00..0x00467E2F
        Menus_OpenByName(name, showCursor)                0x00467E34 -> 0x005F4FB0
  Server command 'u' openPopupMenu 0x00467EE0, 'v' closePopupMenu 0x00467FC0,
                  'r' closeMenu    0x00468060, 'H' closeInGameMenu 0x005F5160.

  0x005F4FB0 first offers the name to the Scaleform front end (0x006B7940),
  which only knows these eight menus:
      changeclass, team_marinesopfor, changeclass_marines, changeclass_opfor,
      changeteam, respawnpopupmenurevive, mp_eog_summary, coop_eog_summary
  Every other name falls through to the legacy menu stack, which at 0x005F509B
  executes, unconditionally and for the no-mouse variant too:

      keyCatchers = (keyCatchers & 1) | 0x10          ; KEYCATCH_UI

  UI_SetActiveMenu (0x005F3490) pairs that same write with
  Dvar_SetIntByName("cl_paused", 1) at 0x005F34DC, and UI_KeyEvent (0x005F3760)
  clears both again at 0x005F38AC/0x005F38E9 once no menu is left visible --
  which is why the server log sees the client ship userinfo "\cl_paused\1"
  during a match.

  The cursor is drawn by UI_Refresh (0x005ECDB0).  Its full predicate, read at
  0x005ECE96..0x005ECEF7, is

      mouseInWindow (0x02832FC4, set by UI_MouseEvent 0x005F3900)
   && !Dvar("978")                                  (0x005EAC30)
   && (keyCatchers & 0x10)                          (0x005ECEB0)
   && (anyVisibleFullScreenMenu || Dvar("2711"))    (0x005ECEC0 -> 0x00606FB0)
   && menuMode (0x0283464C) not in {3, 5}

  so KEYCATCH_UI is necessary but not sufficient; this probe reports every term.

Menu tables:
  0x02832FE0  menuDef* array of every loaded menu, count at 0x028339E0
              (0x005F9219/0x005F920B)
  menu+0x000  name
  menu+0x048 + 4*localClient  per-client flags; visible == (f & 4) && (f & 2)
              (0x00606E00, 0x005F504B)
  menu+0x0A8  fullScreen      (0x00606FD8)
  0x02832FA8  the open-menu context: +0x000 localClientNum,
              +0xA3C menu*[] , +0xA7C count
  0x016EC420  per-local-client pending script menu, stride 72:
              +0x00 name[0x40], +0x40 slot, +0x44 showCursor  (0x00467E8E)

Dvars (value at +0xC):
  [0x02572034] cl_paused      [0x02574638] "2711"    [0x025745F8] "1871"
"""
import argparse
import ctypes
import json
import sys
import time

KEY_CATCHERS = 0x016FC2E0
KEY_CATCH_EDGE = 0x016FC2E4
MENU_MODE = 0x0283464C
MENU_CONTEXT = 0x02832FA8
MENU_LIST = 0xA3C
MENU_COUNT = 0xA7C
MENU_FLAGS = 0x48
MENU_FULLSCREEN = 0xA8
ALL_MENUS = 0x02832FE0
ALL_MENU_COUNT = 0x028339E0
MOUSE_IN_WINDOW = 0x02832FC4
CURSOR_X = 0x02832FB8
CURSOR_Y = 0x02832FBC
PENDING_MENU = 0x016EC420
PENDING_STRIDE = 72
DVAR_CL_PAUSED = 0x02572034
DVAR_2711 = 0x02574638
DVAR_1871 = 0x025745F8
DVAR_VALUE = 0xC

KEYCATCH_CONSOLE = 0x01
KEYCATCH_UI = 0x10

# 0x006B7940: the only menus C1 routes to Scaleform instead of the legacy stack.
SCALEFORM_MENUS = (
    "changeclass", "team_marinesopfor", "changeclass_marines", "changeclass_opfor",
    "changeteam", "respawnpopupmenurevive", "mp_eog_summary", "coop_eog_summary",
)


class Reader(object):
    """PROCESS_VM_READ only; never writes to the client."""

    def __init__(self, pid):
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self.kernel.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
        self.kernel.OpenProcess.restype = ctypes.c_void_p
        self.kernel.ReadProcessMemory.argtypes = [
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
            ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
        self.handle = self.kernel.OpenProcess(0x10, False, pid)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())

    def read(self, address, size):
        if not address:
            return None
        buffer = ctypes.create_string_buffer(size)
        got = ctypes.c_size_t()
        if not self.kernel.ReadProcessMemory(self.handle, ctypes.c_void_p(address), buffer,
                                             size, ctypes.byref(got)) or got.value != size:
            return None
        return buffer.raw

    def word(self, address):
        raw = self.read(address, 4)
        return None if raw is None else int.from_bytes(raw, "little", signed=True)

    def uword(self, address):
        raw = self.read(address, 4)
        return None if raw is None else int.from_bytes(raw, "little")

    def real(self, address):
        raw = self.read(address, 4)
        return None if raw is None else ctypes.c_float.from_buffer_copy(raw).value

    def text(self, address, limit=64):
        raw = self.read(address, limit)
        if raw is None:
            return None
        raw = raw.split(b"\0")[0]
        if not raw or any(c < 32 or c > 126 for c in raw):
            return None
        return raw.decode("latin-1")


def dvar_value(reader, dvar_global):
    """dvar_t: +0x0 name, +0x8 type (0 = bool, 5 = int), +0xC value union."""
    pointer = reader.uword(dvar_global)
    if not pointer:
        return None
    kind = reader.read(pointer + 8, 1)
    if kind is not None and kind[0] == 0:
        raw = reader.read(pointer + DVAR_VALUE, 1)
        return None if raw is None else raw[0]
    return reader.word(pointer + DVAR_VALUE)


def open_menus(reader, local):
    """The open-menu context at 0x02832FA8, oldest first (mirror of 0x00606E00)."""
    count = reader.word(MENU_CONTEXT + MENU_COUNT)
    if count is None or not 0 <= count < 64:
        return count, []
    entries = []
    for index in range(count):
        menu = reader.uword(MENU_CONTEXT + MENU_LIST + 4 * index)
        if not menu:
            entries.append({"index": index, "menu": 0})
            continue
        flags = reader.uword(menu + MENU_FLAGS + 4 * local)
        entries.append({
            "index": index,
            "name": reader.text(reader.uword(menu) or 0),
            "flags": flags,
            "visible": bool(flags is not None and (flags & 4) and (flags & 2)),
            "fullScreen": reader.word(menu + MENU_FULLSCREEN),
        })
    return count, entries


def loaded_menus(reader, local, only=None):
    """Every menuDef C1 has loaded (0x02832FE0 / 0x028339E0)."""
    count = reader.word(ALL_MENU_COUNT)
    if count is None or not 0 <= count < 1024:
        return count, []
    rows = []
    for index in range(count):
        menu = reader.uword(ALL_MENUS + 4 * index)
        if not menu:
            continue
        name = reader.text(reader.uword(menu) or 0)
        if only is not None and name not in only:
            continue
        flags = reader.uword(menu + MENU_FLAGS + 4 * local)
        rows.append({
            "name": name,
            "flags": flags,
            "visible": bool(flags is not None and (flags & 4) and (flags & 2)),
            "fullScreen": reader.word(menu + MENU_FULLSCREEN),
            "scaleform": name in SCALEFORM_MENUS,
        })
    return count, rows


def sample(reader, dump_all=False):
    local = reader.word(MENU_CONTEXT) or 0
    if not 0 <= local < 4:
        local = 0
    catchers = reader.uword(KEY_CATCHERS)
    count, entries = open_menus(reader, local)
    mode = reader.word(MENU_MODE)
    full_screen = any(e.get("visible") and e.get("fullScreen") for e in entries)
    dvar_2711 = dvar_value(reader, DVAR_2711)
    in_window = reader.word(MOUSE_IN_WINDOW)
    ui = bool(catchers is not None and catchers & KEYCATCH_UI)
    loaded_count, loaded = loaded_menus(reader, local, None if dump_all else ())

    pending = None
    base = PENDING_MENU + PENDING_STRIDE * local
    name = reader.text(base, 0x40)
    if name:
        pending = {"name": name, "slot": reader.word(base + 0x40),
                   "showCursor": reader.uword(base + 0x44)}

    hud = hud_gates(reader)
    return {
        "wall": round(time.time(), 3),
        "hud": hud,
        "keyCatchers": catchers,
        "ui": ui,
        "console": bool(catchers is not None and catchers & KEYCATCH_CONSOLE),
        "keyCatchEdge": (reader.read(KEY_CATCH_EDGE, 1) or b"\xff")[0],
        "menuMode": mode,
        "localClient": local,
        "openCount": count,
        "open": entries,
        "topVisible": next((e.get("name") for e in reversed(entries) if e.get("visible")), None),
        "anyFullScreenVisible": full_screen,
        "loadedMenuCount": loaded_count,
        "loadedMenus": loaded,
        "pending": pending,
        "mouseInWindow": in_window,
        "cursor": [reader.real(CURSOR_X), reader.real(CURSOR_Y)],
        "cl_paused": dvar_value(reader, DVAR_CL_PAUSED),
        "dvar2711": dvar_2711,
        "dvar1871": dvar_value(reader, DVAR_1871),
        # UI_Refresh 0x005ECE96..0x005ECEF7, minus the Dvar("978") suppressor
        # which C1 looks up by name and this probe cannot resolve without it.
        "cursorWouldDraw": bool(in_window and ui and (full_screen or dvar_2711)
                                and mode not in (3, 5)),
    }


def hud_gates(reader):
    """CG_ShouldDrawHUD 0x00453A10 inputs plus the killcam latch.

    cg is the obfuscated per-client pointer 0x016D3B58[0x06C3D2AC] ^ 0x490B400C
    (same decode as codol_splash_probe.py).  drawHud cg+0xBF090 is written by
    the 's hud_drawHud' handler 0x00468A64; dvar "952" (default 1) makes the
    HUD ignore KEYCATCH_UI; inKillcam cg+0xC8B60.
    """
    index = reader.uword(0x06C3D2AC)
    if index is None or index > 1024:
        return None
    pointer = reader.uword(0x016D3B58 + index * 4)
    if pointer is None:
        return None
    cg = pointer ^ 0x490B400C
    dvar = reader.uword(0x016F8064)
    return {
        "commandTime": reader.uword(cg),
        "drawHud": reader.uword(cg + 0xBF090),
        "dvar952": (reader.read(dvar + 12, 1) or b"\xff")[0] if dvar else None,
        "inKillcam": reader.uword(cg + 0xC8B60),
    }


def digest(row):
    hud = row.get("hud") or {}
    return (row["keyCatchers"], row["menuMode"], row["cl_paused"], row["dvar1871"],
            (row["pending"] or {}).get("name"), hud.get("drawHud"), hud.get("dvar952"),
            hud.get("inKillcam"),
            row["dvar2711"], row["mouseInWindow"], row["cursorWouldDraw"],
            tuple((e.get("name"), e.get("flags")) for e in row["open"]))


def line(row):
    names = ",".join("%s%s" % (e.get("name"),
                               "*" if e.get("visible") else "")
                     for e in row["open"]) or "-"
    return ("kc=0x%-3x ui=%d mode=%-3s cl_paused=%-4s 2711=%-4s 1871=%-4s inWin=%-4s "
            "fsMenu=%d draw=%d open=[%s] pending=%s hud=%s" % (
                row["keyCatchers"] or 0, row["ui"], row["menuMode"], row["cl_paused"],
                row["dvar2711"], row["dvar1871"], row["mouseInWindow"],
                row["anyFullScreenVisible"], row["cursorWouldDraw"], names,
                (row["pending"] or {}).get("name", "-"),
                "-" if not row.get("hud") else "draw%s/952:%s/kc%s" % (
                    row["hud"]["drawHud"], row["hud"]["dvar952"], row["hud"]["inKillcam"])))


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pid", type=int, required=True, help="C1.exe process id")
    parser.add_argument("--watch", action="store_true", help="log every state change")
    parser.add_argument("--seconds", type=float, default=0.0, help="stop after N seconds")
    parser.add_argument("--hz", type=float, default=50.0)
    parser.add_argument("--out", help="JSONL of every change")
    parser.add_argument("--menus", action="store_true",
                        help="one shot: also dump every loaded menuDef")
    arguments = parser.parse_args()

    reader = Reader(arguments.pid)
    if not arguments.watch:
        row = sample(reader, dump_all=arguments.menus)
        print(line(row))
        if arguments.menus:
            print("loaded menus: %s" % row["loadedMenuCount"])
            for menu in row["loadedMenus"]:
                print("  %-32s flags=0x%-5x fullScreen=%-3s scaleform=%d visible=%d" % (
                    menu["name"], menu["flags"] or 0, menu["fullScreen"],
                    menu["scaleform"], menu["visible"]))
        else:
            print(json.dumps(row, indent=2))
        return 0

    stream = open(arguments.out, "w", encoding="utf-8") if arguments.out else None
    started = time.time()
    period = 1.0 / max(arguments.hz, 1.0)
    previous = None
    try:
        while True:
            row = sample(reader)
            if row["keyCatchers"] is not None:
                current = digest(row)
                if current != previous:
                    previous = current
                    stamp = time.strftime("%H:%M:%S", time.localtime(row["wall"]))
                    print("%s.%03d %s" % (stamp, int(row["wall"] % 1 * 1000), line(row)),
                          flush=True)
                    if stream:
                        stream.write(json.dumps(row) + "\n")
                        stream.flush()
            if arguments.seconds and time.time() - started >= arguments.seconds:
                break
            time.sleep(period)
    except KeyboardInterrupt:
        pass
    finally:
        if stream:
            stream.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
