# -*- coding: utf-8 -*-
import os
IMG = r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d = open(IMG, "rb").read()
needles = [b"SessionStart", b"sessionstart", b"Session Start", b"session_start",
           b"gamestate", b"Gamestate", b"CCS", b"netchan", b"usercmd", b"UserCmd",
           b"snapshot", b"Snapshot", b"servercmd", b"ServerCommand", b"dedicated",
           b"capture", b"Capture", b"28960", b"entitlement", b"Entitlement",
           b"roster", b"Roster", b"XUID", b"xuid", b"MM_RESERVE", b"startArena",
           b"sv_", b"dvar", b"verifySignatures", b"EXE_GAMEISENDING", b"EXE_MATCHENDED",
           b"EXE_KEYCHANGE", b"EXE_GAME", b"clc_", b"svc_"]
for n in needles:
    c = d.count(n)
    idx = d.find(n)
    ctx = ""
    if idx >= 0:
        s = d[max(0, idx-30):idx+70]
        ctx = "".join(chr(b) if 32 <= b < 127 else "." for b in s)
    print("%-20s count=%-5d %s" % (n.decode(errors="replace"), c, ctx))
