#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
codol_stringtable_dump.py -- decode CoDOL 1.1.1.13 type-37 (stringtable) zone
assets back into CSV.

    python tools/codol_stringtable_dump.py --list code_post_gfx_mp
    python tools/codol_stringtable_dump.py code_post_gfx_mp mp/allchallengestable.csv
    python tools/codol_stringtable_dump.py --out DIR code_post_gfx_mp "mp/co*.csv"

Why this exists.  The CSVs under `bin/home/codol_rawfiles/mp/` are the IW4
exports; they are NOT what C1 mounts.  CoDOL ships its own tables inside the
fastfiles -- `mp/allchallengestable.csv` is 602 x 39 against IW4's ~450 x 24,
and carries the numeric challenge ID that C1 0x48bf60 looks up and that indexes
`challenges[]` in mp/playersecuredata.def.  Weapon levelling lives in
`mp/coweaponprimaryranktable.csv` / `mp/coweaponsecondaryranktable.csv`, which
have no IW4 equivalent at all.  Only the mounted tables are evidence for CoDOL
behaviour.

Asset layout, MEASURED on code_post_gfx_mp:

    +0x00  u32 namePtr      (0xFFFFFFFF: the name follows the fixed part)
    +0x04  u32 columnCount
    +0x08  u32 rowCount
    +0x0C  u32 valuesPtr    (0xFFFFFFFF: the cells follow the name)
    +0x10       char name[] NUL-terminated
                struct { u32 stringPtr; u32 hash; } cells[rowCount*columnCount]
                char strings[]  -- the cells' inline strings, in cell order

A cell's `stringPtr` is 0xFFFFFFFF when its string is inline (the next unread
one in the trailing region), 0 for an empty cell, and otherwise a block-3
back-reference to a string written earlier in the zone stream.  Those
references are the majority (22464 of 23478 cells in allchallengestable) and
their block-3 offsets cannot be mapped back to file offsets without simulating
the loader -- see the COULD NOT DETERMINE note in alpha0022/zone_assets.py.

We do not need to.  Every cell carries its string's hash, and the hash function
is MEASURED exactly (1014/1014 inline cells of mp/allchallengestable.csv):

    h = 0; for each byte c: h = (tolower(c) + 31*h) & 0xFFFFFFFF

So a de-duplicated cell is resolved from its hash against a pool built the way
alpha0022's `marketplace_catalogue.load_tables()` builds it -- exactly, with no
heuristic:

  * the empty string (hash 0),
  * every *inline* cell of every stringtable in the zone.  A cell is
    de-duplicated only because that same string was written inline earlier in
    the stream, so the zone's inline cells are the pre-image of nearly every
    back-reference,
  * the decimal spellings of 0 .. `--int-pool` (default 2,000,000), which cover
    the numeric cells whose first occurrence was in a non-stringtable asset.

`--deep` adds a last-resort scan of every NUL-run in the zone and every suffix
of one, for hashes the pool still misses.  Those hits are heuristic: a 32-bit
hash collides freely against binary noise read as text, so a scan hit is marked
`~text` and a hash with more than one candidate is written `<hash:XXXXXXXX?a|b>`.
Both count as unresolved in the per-table summary; nothing is silently guessed.

Reuses the measured fastfile reader in the alpha0022 Python server
(zone_assets.py).  Point CODOL_ALPHA0022 at that directory if it is not at the
default path below.
"""
from __future__ import print_function

import argparse
import csv
import fnmatch
import os
import struct
import sys

DEFAULT_ALPHA = (r"D:\CoD\CODOL Builds\Call of Duty Online 1.1.1.13"
                 r"\CODOL\1.1.1.13_server\alpha0022")

sys.path.insert(0, os.environ.get("CODOL_ALPHA0022", DEFAULT_ALPHA))
import zone_assets as za  # noqa: E402

MASK = 0xFFFFFFFF
PTR_INLINE = 0xFFFFFFFF
HEADER = 0x10


def _lower(c):
    return c + 0x20 if 0x41 <= c <= 0x5A else c


def st_hash(data):
    """C1's stringtable cell hash.  MEASURED; see the module docstring."""
    if isinstance(data, str):
        data = data.encode("latin-1")
    h = 0
    for c in bytearray(data):
        h = (_lower(c) + 31 * h) & MASK
    return h


class CellPool(object):
    """hash -> cell text.

    `exact` holds pre-images we actually decoded or constructed; `scan` holds
    optional heuristic hits from raw zone bytes and is only consulted when
    `exact` misses.
    """

    MAX_RUN = 512        # longer runs are binary noise, not names

    def __init__(self):
        self.exact = {0: ""}
        self.scan = {}

    def learn(self, text, h=None):
        if isinstance(text, bytes):
            text = text.decode("latin-1")
        self.exact.setdefault(st_hash(text) if h is None else h, text)

    def learn_integers(self, upto):
        """Numeric cells whose first occurrence was a non-stringtable asset."""
        setdefault = self.exact.setdefault
        for i in range(upto + 1):
            s = str(i)
            setdefault(st_hash(s), s)
        for i in range(1, 1000):
            s = "-%d" % i
            setdefault(st_hash(s), s)

    def learn_zone_scan(self, data):
        """Last resort.  Suffix hashes accumulate from the right in O(len):
               H(i) = tolower(c[i]) * 31**(L-1-i) + H(i+1)
        Candidates are ranked -- 2 a whole printable NUL-run, 1 a printable
        suffix of one, 0 anything with a control byte -- and only the best rank
        survives.  Two distinct top-rank candidates ("200" and "0n0" both hash
        to 0xC1B2) are kept as an ambiguity, never picked between."""
        pow31 = [1]
        for _ in range(self.MAX_RUN):
            pow31.append((pow31[-1] * 31) & MASK)
        add = self._add_scan
        for run in data.split(b"\0"):
            n = len(run)
            if n == 0 or n > self.MAX_RUN:
                continue
            body = bytearray(run)
            h = 0
            clean = True
            for i in range(n - 1, -1, -1):
                c = body[i]
                if c < 0x20 or c == 0x7F:
                    clean = False
                h = (h + _lower(c) * pow31[n - 1 - i]) & MASK
                add(h, run[i:], (2 if i == 0 else 1) if clean else 0)

    def _add_scan(self, h, s, rank):
        cur = self.scan.get(h)
        if cur is None:
            self.scan[h] = (rank, s)
            return
        crank, cs = cur
        if rank > crank:
            self.scan[h] = (rank, s)
        elif rank == crank and cs != s:
            if isinstance(cs, frozenset):
                self.scan[h] = (rank, frozenset(cs | set([s])))
            else:
                self.scan[h] = (rank, frozenset([cs, s]))

    def get(self, h):
        """-> (text, exact).  Misses and ambiguities stay visible in the cell."""
        v = self.exact.get(h)
        if v is not None:
            return v, True
        v = self.scan.get(h)
        if v is None:
            return "<hash:%08x?>" % h, False
        _, s = v
        if isinstance(s, frozenset):
            return ("<hash:%08x?%s>"
                    % (h, "|".join(x.decode("latin-1") for x in sorted(s)[:4])),
                    False)
        return "~" + s.decode("latin-1"), False


def learn_inline_cells(zone, pool):
    """Seed `pool` with every inline stringtable cell in the zone."""
    learned = 0
    for a in zone.by_type(za.T_STRINGTABLE):
        blob = a.blob
        try:
            name_ptr, cols, rows, values_ptr = struct.unpack_from("<4I", blob, 0)
            if name_ptr != PTR_INLINE or values_ptr != PTR_INLINE or not (cols and rows):
                continue
            cursor = blob.index(b"\0", HEADER) + 1
            cell_at = cursor
            cursor += cols * rows * 8
            for i in range(cols * rows):
                p, h = struct.unpack_from("<2I", blob, cell_at + i * 8)
                if p != PTR_INLINE:
                    continue
                e = blob.index(b"\0", cursor)
                pool.learn(blob[cursor:e], h)
                cursor = e + 1
                learned += 1
        except Exception:
            continue
    return learned


def decode_stringtable(blob, pool=None):
    """-> (name, rows, stats).  `rows` is a list of lists of str."""
    if len(blob) < HEADER:
        raise ValueError("stringtable asset is only %d bytes" % len(blob))
    name_ptr, cols, rows, values_ptr = struct.unpack_from("<4I", blob, 0)
    if name_ptr != PTR_INLINE:
        raise ValueError("name is a back-reference (%#010x); this dumper only "
                         "handles inline names" % name_ptr)
    end = blob.index(b"\0", HEADER)
    name = blob[HEADER:end].decode("latin-1")
    cursor = end + 1
    stats = {"inline": 0, "ref": 0, "null": 0, "unresolved": 0}
    if cols == 0 or rows == 0:
        return name, [], stats
    ncell = cols * rows
    cell_at = cursor
    need = cell_at + ncell * 8
    if values_ptr != PTR_INLINE or need > len(blob):
        raise ValueError("%s: %d x %d cells do not fit in %d bytes (valuesPtr "
                         "%#010x)" % (name, rows, cols, len(blob), values_ptr))
    cursor = need
    out = []
    for r in range(rows):
        row = []
        for c in range(cols):
            p, h = struct.unpack_from("<2I", blob, cell_at + (r * cols + c) * 8)
            if p == PTR_INLINE:
                e = blob.index(b"\0", cursor)
                row.append(blob[cursor:e].decode("latin-1"))
                cursor = e + 1
                stats["inline"] += 1
            elif p == 0:
                row.append("")
                stats["null"] += 1
            else:
                stats["ref"] += 1
                if pool is None:
                    row.append("<ref:%08x>" % p)
                    stats["unresolved"] += 1
                else:
                    text, exact = pool.get(h)
                    row.append(text)
                    if not exact:
                        stats["unresolved"] += 1
        out.append(row)
    if cursor != len(blob):
        stats["trailing"] = len(blob) - cursor
    return name, out, stats


def _safe(name):
    return name.replace("/", "_").replace("\\", "_")


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("zone", help="fastfile name, e.g. code_post_gfx_mp")
    ap.add_argument("tables", nargs="*",
                    help="asset names or glob patterns; default: every table")
    ap.add_argument("--list", action="store_true",
                    help="list the zone's stringtables and their shape")
    ap.add_argument("--out", metavar="DIR",
                    help="write <DIR>/<name>.csv instead of stdout")
    ap.add_argument("--no-resolve", action="store_true",
                    help="leave de-duplicated cells as <ref:...> (fast)")
    ap.add_argument("--int-pool", type=int, default=2000000, metavar="N",
                    help="pool the decimal spellings of 0..N (default 2000000)")
    ap.add_argument("--deep", action="store_true",
                    help="last-resort raw-byte scan for hashes the exact pool "
                         "misses; its hits are marked '~' and stay unresolved")
    args = ap.parse_args(argv)

    z = za.open_zone(args.zone)
    assets = z.by_type(za.T_STRINGTABLE)
    if args.list:
        print("%s: %d stringtables" % (z.name, len(assets)))
        for a in assets:
            try:
                ncols, nrows = struct.unpack_from("<2I", a.blob, 4)
            except Exception:
                continue
            print("  %-46s %5d x %-3d  %9d bytes"
                  % (a.name, nrows, ncols, a.size))
        return 0

    wanted = []
    for a in assets:
        if not a.name:
            continue
        if not args.tables:
            wanted.append(a)
            continue
        low = a.name.lower()
        for pat in args.tables:
            p = pat.lower()
            if low == p or fnmatch.fnmatch(low, p) or fnmatch.fnmatch(low, "mp/" + p):
                wanted.append(a)
                break
    if not wanted:
        sys.stderr.write("no stringtable matched; try --list\n")
        return 1

    pool = None
    if not args.no_resolve:
        pool = CellPool()
        n = learn_inline_cells(z, pool)
        pool.learn_integers(args.int_pool)
        if args.deep:
            pool.learn_zone_scan(z.data)
        sys.stderr.write("cell pool: %d exact (%d inline cells from %s%s)\n"
                         % (len(pool.exact), n, z.name,
                            ", + deep scan" if args.deep else ""))
    if args.out and not os.path.isdir(args.out):
        os.makedirs(args.out)
    rc = 0
    for a in wanted:
        try:
            name, rows, stats = decode_stringtable(a.blob, pool)
        except Exception as exc:
            sys.stderr.write("%s: %s\n" % (a.name, exc))
            rc = 1
            continue
        ncols = len(rows[0]) if rows else 0
        if args.out:
            path = os.path.join(args.out, _safe(name or a.name))
            with open(path, "w", newline="", encoding="utf-8") as f:
                csv.writer(f, lineterminator="\n").writerows(rows)
            where = path
        else:
            w = csv.writer(sys.stdout, lineterminator="\n")
            w.writerows(rows)
            where = "-"
        sys.stderr.write("%-46s %5d x %-3d -> %s  (%d inline, %d ref, %d empty,"
                         " %d unresolved)\n"
                         % (name, len(rows), ncols, where, stats["inline"],
                            stats["ref"], stats["null"], stats["unresolved"]))
    return rc


if __name__ == "__main__":
    sys.exit(main())
