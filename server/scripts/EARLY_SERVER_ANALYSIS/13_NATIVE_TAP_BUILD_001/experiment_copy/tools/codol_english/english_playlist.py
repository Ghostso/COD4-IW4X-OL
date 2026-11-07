#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
english_playlist.py -- make an English copy of the lobby's playlist file.

    python tools/codol_english/english_playlist.py [SRC] [-o OUT]

Playlist and game-mode names and descriptions (the matchmaking list, the
left-panel description, and the mode name on the scoreboard such as
"团队竞技 - Killhouse") are not localize entries.  They come from the
playlist file the lobby serves: C1 logs
    LiveStorage_FetchFile: filename[mp_playlists_shipRetail_cb2.info]
    Playlist was 30274 bytes
and the lobby (alpha0022 dw-capture.py) serves resources/mp_playlists_shipRetail_cb2.info.
Every entry carries both languages:
    name english "Team Deathmatch"
    name chinese "团队竞技"
    description english "..."
    description chinese "..."
and C1 uses the line for its own language, chinese.  This tool rewrites each
`name chinese` / `description chinese` line with the text of the preceding
`name english` / `description english` line of the same block (ASCII, so the
GBK file stays valid).  Everything else is copied byte for byte.

The lobby would serve the result instead of the stock file -- for everyone,
or per player if the lobby chooses the file by account.  This tool only
writes OUT; it never touches the lobby.
"""
import argparse
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SRC = (r"D:\CoD\CODOL Builds\Call of Duty Online 1.1.1.13\CODOL\1.1.1.13_server"
               r"\alpha0022\resources\mp_playlists_shipRetail_cb2.info")
DEFAULT_OUT = os.path.join(HERE, "out", "mp_playlists_shipRetail_cb2.english.info")
LINE = re.compile(rb'^(\s*)(name|description)(\s+)(english|chinese)(\s+)"(.*)"(.*)$')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", nargs="?", default=DEFAULT_SRC)
    ap.add_argument("-o", "--out", default=DEFAULT_OUT)
    a = ap.parse_args()
    data = open(a.src, "rb").read()
    lines = data.split(b"\n")
    english = {}
    changed = kept = 0
    for i, raw in enumerate(lines):
        cr = raw.endswith(b"\r")
        line = raw[:-1] if cr else raw
        if re.match(rb"^\s*(playlist|gametype)\b", line):
            english = {}
        m = LINE.match(line)
        if not m:
            continue
        ind, kind, s1, lang, s2, text, tail = m.groups()
        if lang == b"english":
            english[kind] = text
        elif kind in english and all(c < 0x80 for c in english[kind]):
            if text != english[kind]:
                changed += 1
            lines[i] = ind + kind + s1 + b"chinese" + s2 + b'"' + english[kind] + b'"' + tail + (b"\r" if cr else b"")
        else:
            kept += 1
    out = b"\n".join(lines)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    open(a.out, "wb").write(out)
    print("wrote %s: %d chinese lines now English, %d left (no English line), %d -> %d bytes"
          % (a.out, changed, kept, len(data), len(out)))


if __name__ == "__main__":
    main()
