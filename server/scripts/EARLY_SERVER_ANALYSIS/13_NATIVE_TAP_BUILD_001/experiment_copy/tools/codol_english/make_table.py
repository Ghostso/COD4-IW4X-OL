#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
make_table.py -- (re)build codol_english.tsv, the English text for every C1
localize name, from the English sources on disk.

    python tools/codol_english/make_table.py [-o tools/codol_english/codol_english.tsv]

Per C1 name (dump_c1_localize.py, run automatically when missing), first match wins:
  1. the C1 value is already plain ASCII -> left out (nothing to translate);
  2. an official English string with the same name: Warfare2 (IW4 dev) .str
     files, IW4 English zones (sources/iw4_loc.json), the iw4x localize.csv
     dumps, Warfare2 zones (sources/w2_loc.json), T5 English zones
     (sources/t5_loc.json) -- unless its %s/&&N tokens disagree with the
     Chinese text, in which case a translation of the Chinese is preferred;
  3. a translation of the Chinese text (sources/translations.json by_text),
     then by name (by_key);
  4. another name whose Chinese text is identical and already has English.
Values are reduced to printable ASCII (C1 reads GBK).

Output: KEY<TAB>text, one per line, with \n \t \\ escaped.  Names left in
Chinese go to missing.tsv beside the output.

The first pass of this table (2026-09-28) was made with scratch scripts that
also read live menu dumps; sources/live_dump_menu.tsv is that dump (name ->
the Chinese text C1 showed) and settles names whose zone value is only a
heuristically resolved reference.

sources/native_localize.tsv, when present, does the same for every mounted
zone: it is the server's `codol_dumplocalize` output (fs_homepath/
codol_localize.tsv), written by the native zone loader, which resolves the
de-duplicated name references exactly.  The Python zone reader only guesses
those, and in localized_common_gametype_mp its guesses paired most announcer
subtitle names (SUBTITLE_*_1MC_*) with another line's text, so players read
"Counter-UAV standing by" while the announcer said the AC-130 was ready.  Its
first line for a name is what C1 shows; it matched every one of the 9,747
names in live_dump_menu.tsv.  Only SUBTITLE_* names are taken from it: the
rest are settled by the live dump or are labels already fitted to their boxes.
Several translations in translations.json were made from the misattributed
text, so the announcer lines are also pinned in sources/manual.tsv.
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import os
import re
import subprocess
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "sources")
DEFAULT_OUT = os.path.join(HERE, "codol_english.tsv")
DEFAULT_C1DUMP = os.path.join(os.environ.get("TEMP", "."), "codol_english", "c1_localize.json")
W2 = r"D:\CoD\CODOL Builds\Warfare2Client"
IW4X_DUMPS = r"D:\CoD\iw4x_development\userraw\dump\*\localizedstrings\localize.csv"

CJK = re.compile(r"[\u3000-\u9fff\uff00-\uffef\ufffd]")
TOK = re.compile(r"&&\d|%[sdif]|\[\{[^}]*\}\]")
FIX = {"Huanito": "Juanito", "Aldran": "Oderan", "Odelan": "Oderan"}


def J(name):
    with open(os.path.join(SRC, name), encoding="utf-8") as f:
        return json.load(f)


def parse_str(path):
    out, ref = {}, None
    with open(path, "rb") as f:
        for line in f.read().split(b"\n"):
            m = re.match(rb'\s*REFERENCE\s+(\S+)', line)
            if m:
                ref = m.group(1).decode()
                continue
            m = re.match(rb'\s*LANG_ENGLISH\s+"(.*)"\s*\r?$', line)
            if m and ref:
                try:
                    out[ref.upper()] = m.group(1).decode("utf-8")
                except UnicodeDecodeError:
                    out[ref.upper()] = m.group(1).decode("latin-1")
                ref = None
    return out


def official_sources():
    w2s = {}
    for p in (glob.glob(os.path.join(W2, r"GameData\ShipFiles\english\localizedstrings\*.str")) +
              glob.glob(os.path.join(W2, r"GameData\ShipFiles\localizedstrings\*.str")) +
              glob.glob(os.path.join(W2, r"DevData\raw\localizedstrings\*.str"))):
        pref = os.path.basename(p)[:-4].upper()
        for k, v in parse_str(p).items():
            w2s.setdefault(pref + "_" + k, v)
    iw4csv = {}
    for p in glob.glob(IW4X_DUMPS):
        with open(p, "rb") as f:
            for line in f.read().split(b"\n"):
                m = re.match(rb'([A-Za-z0-9_]+),"(.*)"\r?$', line)
                if not m:
                    continue
                try:
                    iw4csv.setdefault(m.group(1).decode().upper(), m.group(2).decode("utf-8"))
                except UnicodeDecodeError:
                    continue
    up = lambda d: {k.upper(): v for k, v in d.items()}
    w2z = up(J("w2_loc.json"))                 # {NAME: English}
    return [("w2str", w2s), ("iw4zone", up(J("iw4_loc.json"))), ("iw4csv", iw4csv),
            ("w2zone", w2z), ("t5zone", up(J("t5_loc.json")))]


def ascii_only(s):
    for a, b in FIX.items():
        s = s.replace(a, b)
    for a, b in (("\u2019", "'"), ("\u2018", "'"), ("\u201c", '"'), ("\u201d", '"'), ("\u2014", "--"),
                 ("\u2013", "-"), ("\u2026", "..."), ("\u00a0", " "), ("\u2122", "(TM)"),
                 ("\u00ae", "(R)"), ("\u00a9", "(C)")):
        s = s.replace(a, b)
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()


def esc(s):
    return s.replace("\\", "\\\\").replace("\t", "\\t").replace("\r", "\\r").replace("\n", "\\n")


def unesc(b):
    out, i = bytearray(), 0
    while i < len(b):
        c = b[i]
        if c == 0x5C and i + 1 < len(b):
            out += {0x6E: b"\n", 0x74: b"\t", 0x72: b"\r"}.get(b[i + 1], bytes([b[i + 1]]))
            i += 2
        else:
            out.append(c)
            i += 1
    return bytes(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build codol_english.tsv")
    ap.add_argument("-o", "--out", default=DEFAULT_OUT)
    ap.add_argument("--c1", default=DEFAULT_C1DUMP)
    args = ap.parse_args(argv)

    if not os.path.exists(args.c1):
        subprocess.check_call([sys.executable, os.path.join(HERE, "dump_c1_localize.py"), "-o", args.c1])
    with open(args.c1) as f:
        c1 = json.load(f)
    c1keys, approx = collections.OrderedDict(), set()
    names = set(e[1].upper() for ents in c1.values() for e in ents)
    for zn, ents in c1.items():
        for _i, name, ap_, val in ents:
            if name.startswith("<"):
                continue
            v = bytes.fromhex(val) if val else None
            # A value that is itself another localize NAME is a mis-resolved de-dup reference
            # (about 1,900 of them), not ASCII text: treat it as unknown.
            if v is not None and re.match(rb"^[A-Z0-9_]+$", v) and v.decode().upper() in names:
                v, ap_ = None, "~"
            c1keys.setdefault(name.upper(), []).append((zn, v))
            if ap_ == "~":
                approx.add(name.upper())

    live = {}
    with open(os.path.join(SRC, "live_dump_menu.tsv"), "rb") as f:
        for line in f.read().split(b"\n"):
            if b"\t" in line:
                k, v = line.split(b"\t", 1)
                live.setdefault(k.decode("latin-1").upper(), unesc(v.rstrip(b"\r")))

    native = os.path.join(SRC, "native_localize.tsv")
    if os.path.exists(native):
        with open(native, "rb") as f:
            for line in f.read().split(b"\n"):
                if b"\t" in line:
                    k, v = line.split(b"\t", 1)
                    k = k.decode("latin-1").upper()
                    # Subtitles only: every other name is settled by the live
                    # menu dump or is a label already fitted to its box.
                    if not k.startswith("SUBTITLE_"):
                        continue
                    live.setdefault(k, unesc(v.rstrip(b"\r")))
                    approx.discard(k)

    tr = J("translations.json")
    by_text, by_key = tr["by_text"], {k.upper(): v for k, v in tr["by_key"].items()}
    sources = official_sources()

    def official(k):
        for name, d in sources:
            if k in d and not CJK.search(d[k]):
                return d[k], name
        return None, None

    def decide(k, zhb):
        if zhb is not None and all(c < 0x80 for c in zhb):
            return None, "ascii"
        zhs = zhb.decode("gbk", "replace") if zhb is not None else None
        en, s = official(k)
        if en is not None and zhs is not None and sorted(TOK.findall(zhs)) != sorted(TOK.findall(en)):
            if zhs in by_text:
                return by_text[zhs], "translated(token)"
        if en is not None:
            return en, s
        if zhs is not None and zhs in by_text:
            return by_text[zhs], "translated"
        if k in by_key and (zhs is None or k not in approx):
            return by_key[k], "translated(key)"
        return None, "none"

    first = lambda lst: next((v for _z, v in lst if v is not None), None)
    same_text = {}
    for k, zh in list(live.items()) + [(k, first(l)) for k, l in c1keys.items() if k not in approx]:
        if zh is None:
            continue
        en, s = decide(k, zh)
        if en is not None and s != "ascii":
            same_text.setdefault(zh, en)

    final, src, missing = {}, collections.Counter(), {}
    todo = [(k, v, "live") for k, v in live.items()]
    todo += [(k, first(l), "static") for k, l in c1keys.items() if k not in live and k not in approx]
    for k, zh, where in todo:
        en, s = decide(k, zh)
        if en is None and s == "none" and zh is not None and zh in same_text:
            en, s = same_text[zh], "same-text"
        src["%s:%s" % (where, s)] += 1
        if en is not None:
            final[k] = ascii_only(en)
        elif s == "none" and zh is not None:
            missing[k] = zh.decode("gbk", "replace")

    manual = os.path.join(SRC, "manual.tsv")    # hand corrections win over every source
    if os.path.exists(manual):
        with open(manual, encoding="utf-8") as f:
            for line in f:
                if line.startswith("#") or "\t" not in line:
                    continue
                k, v = line.rstrip("\r\n").split("\t", 1)
                if k.upper() in c1keys or k.upper() in live:
                    final[k.upper()] = v
                    missing.pop(k.upper(), None)
                    src["manual"] += 1
    with open(args.out, "w", encoding="ascii", newline="\n") as f:
        f.write("# Call of Duty Online 1.1.1.13 English localize text: KEY<TAB>text, \\n \\t \\\\ escaped.\n")
        f.write("# Built by tools/codol_english/make_table.py (official IW4/W2/T5 English where the name exists,\n")
        f.write("# translations of the Chinese text otherwise).  Consumed by build_ff.py.\n")
        for k in sorted(final):
            f.write("%s\t%s\n" % (k, esc(final[k])))
    miss = os.path.join(os.path.dirname(os.path.abspath(args.out)), "missing.tsv")
    with open(miss, "w", encoding="utf-8", newline="\n") as f:
        f.write("# C1 localize names with no English yet: KEY<TAB>Chinese text\n")
        for k in sorted(missing):
            f.write("%s\t%s\n" % (k, esc(missing[k])))
    print("english", len(final), dict(sorted(src.items())))
    print("wrote", args.out, "and", miss, "(%d untranslated)" % len(missing))


if __name__ == "__main__":
    main()
