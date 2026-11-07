#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
codol_zone_assets.py -- dump a browsable asset listing of every CoDOL 1.1.1.13
fastfile the client mounts, into docs/zone_assets/.

    python tools/codol_zone_assets.py                 # all zones -> docs/zone_assets
    python tools/codol_zone_assets.py common_mp mp_rust   # a subset (indexes/README
                                                          # are still rebuilt from
                                                          # every <zone>.txt present)
    python tools/codol_zone_assets.py --out DIR       # elsewhere

Reuses the measured fastfile reader in the alpha0022 Python server
(zone_assets.py: RSA/AES/zlib container, XAssetList directory).  Locate it
with CODOL_ALPHA0022=<dir> when it is not at the default path below.  Inflated
zones are cached by that module (CODOL_ZONE_CACHE, default %TEMP%/codol_zones).

Naming.  Every asset struct starts with its name pointer (localize: value then
name; image: name pointer at +32).  0xFFFFFFFF means the NUL-terminated name
follows the fixed part of the struct, whose size per type is in HEADER below
(measured on the shipped zones; 4/28/30/41/... agree with the IW4OL native
loader's dependency_asset_name()).  Anything else is a de-duplicated reference
into runtime block 3 (see zone_assets.py, C1.exe 0x004B6FD9): the same string
was written earlier in the stream -- e.g. every xmodel of common_gametype_mp
is named by a cell of the mp/cocharitems/*.csv stringtables, sound aliases by
the sound fields of the weapon that first used them, the four world assets of
a map by the com_map name.  We do not simulate the loader (the IW4OL native
loader in src/codol/assets/codol_load_blocks.c does, and is the authority);
RefResolver below recovers the file offset from the block-3 offset with the
run/chain heuristic described in its docstring, and flags every name it is
not sure about with '~' in column 3.  Anything it cannot place at all is
written as <unresolved:...>.
"""
from __future__ import annotations

import argparse
import collections
import os
import re
import struct
import sys
import time

DEFAULT_ALPHA = (r"D:\CoD\CODOL Builds\Call of Duty Online 1.1.1.13\CODOL"
                 r"\1.1.1.13_server\alpha0022")
sys.path.insert(0, os.environ.get("CODOL_ALPHA0022", DEFAULT_ALPHA))
import zone_assets as za  # noqa: E402

try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, ".."))
DEFAULT_OUT = os.path.join(REPO, "docs", "zone_assets")

PTR_INLINE = 0xFFFFFFFF

# Byte offset of the inline name after the name pointer (MEASURED, see header).
HEADER = {
    0: 68, 1: 72, 2: 88, 3: 48, 4: 360, 5: 96, 9: 204, 11: 12, 12: 136, 13: 48,
    15: None, 16: 16, 18: 84, 20: 116, 21: None, 22: 16, 24: 24, 25: 12, 26: 400,
    28: 0xBFC, 30: 32, 31: 8, 36: 16, 37: 16, 38: 24, 39: 12, 40: 112, 41: 788,
    42: 36, 43: 12,
}
T_IMAGE, T_LOCALIZE, T_RAWFILE = 10, 27, 36

# Alphabet prior per type: (name_sig() OR-mask, number of inline names it was
# learned from) over every inline-named asset of the 90 shipped zones
# (MEASURED 2026-09-16; e.g. sound aliases and xanims never use '/', '.' or
# upper case).  Merged with the zone's own inline names before filtering.
TYPE_SIG_PRIOR = {
    0: (0x00, 1), 1: (0x00, 2), 2: (0x00, 11554), 3: (0x00, 155), 4: (0xE0, 2258),
    5: (0x43, 4767), 9: (0xA0, 4552), 10: (0x60, 592), 11: (0x80, 14124),
    13: (0x03, 85), 16: (0x03, 19), 22: (0x00, 2), 24: (0x09, 11), 25: (0x03, 53),
    26: (0x00, 22), 27: (0x08, 14304), 28: (0x20, 905), 30: (0x01, 2872),
    36: (0x43, 851), 37: (0x03, 518), 38: (0x28, 37), 39: (0x03, 8), 40: (0x00, 3),
    41: (0x80, 30), 42: (0x03, 9), 43: (0x80, 276),
}

# Merged indexes asked for by name; every other type also gets ALL_<type>.txt.
INDEX_TYPES = ("xanim", "xmodel", "fx", "material", "sound", "weapon",
               "rawfile", "vehicle", "stringtable", "localize")

_STR_START = re.compile(rb"(?<![\x20-\x7e])[\x20-\x7e]+\x00")
_NAMELIKE = re.compile(rb"^[A-Za-z0-9_$~][A-Za-z0-9_/\\.\- ]*$")


def cstr(b, off):
    e = b.find(b"\0", off)
    if e < 0 or off >= len(b):
        return None
    return b[off:e].decode("latin-1")


SIG_SLASH, SIG_DOT, SIG_BSLASH, SIG_UPPER, SIG_SPACE, SIG_DIGIT1, SIG_PUNCT, SIG_SHORT = \
    1, 2, 4, 8, 16, 32, 64, 128


def name_sig(s):
    """Character-class signature of a name (bytes): which classes it uses.
    A ref of type T may only resolve to names whose classes are a subset of
    the classes seen in T's inline names (learned per zone)."""
    v = 0
    if b"/" in s:
        v |= SIG_SLASH
    if b"." in s:
        v |= SIG_DOT
    if b"\\" in s:
        v |= SIG_BSLASH
    if any(0x41 <= c <= 0x5A for c in s):
        v |= SIG_UPPER
    if b" " in s:
        v |= SIG_SPACE
    if s[:1].isdigit():
        v |= SIG_DIGIT1
    if any(not (0x30 <= c <= 0x39 or 0x41 <= c <= 0x5A or 0x61 <= c <= 0x7A or c in b"_/.\\ ")
           for c in s):
        v |= SIG_PUNCT
    if len(s) <= 3:
        v |= SIG_SHORT
    return v


# --------------------------------------------------------------------------
# de-duplicated name resolution
# --------------------------------------------------------------------------

class RefResolver(object):
    """Maps de-duplicated block-3 name references back to file offsets.

    Block 3 is bump-allocated in stream order, so along the refs sorted by
    block-3 offset X the delta (file offset - X) is nearly piecewise constant:
    strings written back to back share it, except that a 4-byte pointer
    allocated after a string is 4-aligned in block 3 and not in the file, so
    the delta may drop by 0..3 per string (PAD); between blobs it only grows
    (data that went to other blocks), give or take a little padding (EPS).

      1. candidate targets = STRONG string starts: name-like, >= 3 chars, and
         preceded by NUL / a 0xFFFFFFFF or 0xFFFFFFFE pointer marker, or
         >= 6 chars containing '_', '/' or '.' (inline names after a struct);
      2. stage 1: every delta path explaining >= MIN_L1 consecutive refs is a
         run; the chain of non-overlapping runs with (almost) non-decreasing
         delta and the largest total length wins (Fenwick-tree DP).  A ref of
         a map-world type whose candidate equals the com_map name is an
         anchor run;
      3. stage 2: refs outside the chain search only between the neighbouring
         chain deltas; runs of >= 2 are chained the same way, the rest take
         the candidate nearest the previous delta (ALL printable runs as a
         last resort).

    Exact: stage-1 runs, anchors, stage-2 runs of >= 3 (or of 2 with a small
    candidate set) and unique candidates; everything else is flagged '~'.
    """
    PAD = 3            # delta may drop this much per consecutive string
    EPS = 4096         # allowed net drop between runs along the chain
    MIN_L1 = 4
    SLACK = 64         # widening of the stage-2 search window
    KMAX2 = 48         # max per-step drop in stage 2 (PAD per skipped string)
    MAX_C = 400000

    def __init__(self, data, anchors=None):
        self.data = data
        self.anchors = anchors or {}
        allpos, strong = [], []
        for m in _STR_START.finditer(data):
            p = m.start()
            allpos.append(p)
            s = m.group(0)[:-1]
            if len(s) >= 3 and _NAMELIKE.match(s):
                prev = data[p - 4:p] if p >= 4 else b""
                if (p == 0 or data[p - 1] == 0
                        or prev in (b"\xff\xff\xff\xff", b"\xfe\xff\xff\xff")
                        or (len(s) >= 6 and (b"_" in s or b"/" in s or b"." in s))):
                    strong.append(p)
            # a block-3 pointer (0x3xxxxxxx) right before a name leaves its
            # printable top byte ('0'..'?') glued to the run: also offer the
            # start just after such bytes
            for k in range(1, 4):
                if len(s) - k >= 5 and 0x30 <= s[k - 1] <= 0x3F and s[k:k + 1].isalpha() \
                        and _NAMELIKE.match(s[k:]):
                    strong.append(p + k)
                    break
        self.all = np.array(allpos, dtype=np.int64)
        self.strong = np.array(sorted(set(strong)), dtype=np.int64)
        # character-class signature of every strong candidate, so a ref can
        # be restricted to the alphabet its asset type's inline names use
        self.sig = np.array([name_sig(self.name_at(int(p))) for p in self.strong],
                            dtype=np.uint8)
        self._arr_cache = {}

    def arr_for(self, mask):
        """Strong starts whose signature fits `mask` (allowed classes)."""
        a = self._arr_cache.get(mask)
        if a is None:
            a = self.strong[(self.sig & ~np.uint8(mask)) == 0]
            self._arr_cache[mask] = a
        return a

    @staticmethod
    def _hits(arr, pos):
        i = np.searchsorted(arr, pos)
        i = np.minimum(i, len(arr) - 1)
        return arr[i] == pos

    @staticmethod
    def _cands(arr, X, F, lo=0, hi=None):
        if hi is not None:
            F = min(F, X + hi)
        a = np.searchsorted(arr, X + max(lo, 0), side="right")
        b = np.searchsorted(arr, F, side="right")
        return arr[a:b] - X

    def name_at(self, pos):
        e = self.data.find(b"\0", pos)
        return self.data[pos:e]

    def name_score(self, pos):
        s = self.name_at(pos)
        if not _NAMELIKE.match(s):
            return -1
        if len(s) > 5 and 0x30 <= s[0] <= 0x3F and s[1:2].isalpha():
            return len(s) - 10      # probably a pointer's top byte glued on
        return len(s)

    def _choose(self, X, S, near):
        """Nearest name-like candidate to `near`; longest name on ties."""
        if len(S) == 1:
            return int(S[0])
        scored = [(d, self.name_score(X + d)) for d in S.tolist()]
        good = [t for t in scored if t[1] > 0] or scored
        if near is None:
            return int(max(good, key=lambda t: (t[1], -t[0]))[0])
        return int(min(good, key=lambda t: (abs(t[0] - near), -t[1]))[0])

    def _step(self, arr, Xp, X, F, surv, kmax):
        """Advance surviving deltas from the ref at Xp to the ref at X: keep
        those with a hit (in arr, the next ref's candidate array) at
        X + d - k, k in 0..kmax (smallest k wins).  A drop k > PAD is only
        allowed when enough strings lie between the two targets to have
        padded that much (PAD per string)."""
        best = np.full(len(surv), -1, dtype=np.int64)
        prev_end = np.searchsorted(self.strong, Xp + surv, side="right")
        for k in range(kmax, -1, -1):
            pos = X + surv - k
            h = self._hits(arr, pos) & (pos <= F) & (pos > X)
            if k > self.PAD and h.any():
                between = np.searchsorted(self.strong, pos) - prev_end
                h &= k <= self.PAD * (1 + between)
            best[h] = surv[h] - k
        m = best >= 0
        return m, best[m]

    def _runs(self, arrs, Xs, Fs, idx, cand, min_len, kmax):
        """idx: ref indices to consider (consecutive in the ref order);
        arrs[i] = candidate array of ref i; cand(i) -> candidate deltas.
        -> [(start_pos_in_idx, L, path, w)], weight L**2 so one long run
        beats a chain of chance fragments."""
        runs, covered = [], set()
        n = len(idx)
        for a in range(n - 1):
            C = cand(idx[a])
            if len(C) == 0:
                continue
            if len(C) > self.MAX_C:
                C = C[:self.MAX_C]
            paths = C.reshape(-1, 1)
            surv = C
            L = 1
            while len(surv):
                b = a + L
                if b >= n or idx[b] != idx[a] + L:      # must stay consecutive
                    m = np.zeros(len(surv), dtype=bool); nd = surv[:0]
                else:
                    m, nd = self._step(arrs[idx[b]], Xs[idx[b - 1]], Xs[idx[b]], Fs[idx[b]],
                                       surv, kmax)
                ended = paths[~m]
                if L >= min_len:
                    for row in ended.tolist():
                        if (a, row[0]) in covered:
                            continue
                        runs.append((a, L, row, L * L))
                        for j, dj in enumerate(row):
                            covered.add((a + j, dj))
                paths = np.column_stack([paths[m], nd]) if m.any() else paths[:0]
                surv = nd
                L += 1
        return runs

    def _chain(self, runs):
        """Max-weight non-overlapping runs whose delta drops by at most EPS
        from one run's end to the next run's start."""
        if not runs:
            return []
        runs = sorted(runs, key=lambda r: (r[0], r[0] + r[1]))
        ends = np.array(sorted({r[2][-1] for r in runs}), dtype=np.int64)
        m = len(ends)
        tree_w = [0.0] * (m + 1)
        tree_i = [-1] * (m + 1)

        def update(r, w, k):
            r += 1
            while r <= m:
                if w > tree_w[r]:
                    tree_w[r], tree_i[r] = w, k
                r += r & -r

        def query(r):
            r += 1
            bw, bi = 0.0, -1
            while r > 0:
                if tree_w[r] > bw:
                    bw, bi = tree_w[r], tree_i[r]
                r -= r & -r
            return bw, bi

        best = [0.0] * len(runs)
        back = [-1] * len(runs)
        by_end = sorted(range(len(runs)), key=lambda k: runs[k][0] + runs[k][1])
        e = 0
        for k, (s, L, path, w) in enumerate(runs):
            while e < len(by_end) and runs[by_end[e]][0] + runs[by_end[e]][1] <= s:
                q = by_end[e]
                update(int(np.searchsorted(ends, runs[q][2][-1])), best[q], q)
                e += 1
            r = int(np.searchsorted(ends, path[0] + self.EPS, side="right")) - 1
            bw, bi = query(r) if r >= 0 else (0.0, -1)
            best[k], back[k] = bw + w, bi
        k = int(np.argmax(best))
        chosen = []
        while k >= 0:
            chosen.append(runs[k])
            k = back[k]
        return chosen[::-1]

    def resolve(self, refs):
        """refs: [(key, X, F, mask)] -> {key: (file_offset or None, exact)};
        mask = allowed name_sig() classes for that asset's type."""
        groups = collections.OrderedDict()
        for key, X, F, mask in refs:
            g = groups.setdefault(X, [F, [], 0])
            g[0] = min(g[0], F)
            g[1].append(key)
            g[2] |= mask
        Xs = [int(x) for x in sorted(groups)]
        Fs = [groups[x][0] for x in Xs]
        keys = [groups[x][1] for x in Xs]
        arrs = [self.arr_for(groups[x][2]) for x in Xs]
        n = len(Xs)
        d = [None] * n
        exact = [False] * n
        # ---- stage 1: long runs over the full windows + anchors
        idx = list(range(n))
        runs = self._runs(arrs, Xs, Fs, idx, lambda i: self._cands(arrs[i], Xs[i], Fs[i]),
                          self.MIN_L1, self.PAD)
        for i in range(n):
            want = None
            for k in keys[i]:
                want = self.anchors.get(k, want)
            if want is None:
                continue
            for dl in self._cands(self.strong, Xs[i], Fs[i]).tolist():
                if self.name_at(Xs[i] + dl) == want:
                    runs.append((i, 1, [dl], 100))
                    break
        for s, L, path, w in self._chain(runs):
            for j in range(L):
                d[s + j], exact[s + j] = path[j], True
        # ---- stage 2: bounded search in the gaps
        i = 0
        while i < n:
            if d[i] is not None:
                i += 1
                continue
            j = i
            while j < n and d[j] is None:
                j += 1
            prev = d[i - 1] if i > 0 else None
            nxt = d[j] if j < n else None
            lo = 0 if prev is None else prev - self.EPS
            hi = None if nxt is None else nxt + self.SLACK
            gap = list(range(i, j))
            cands = {g: self._cands(arrs[g], Xs[g], Fs[g], lo, hi) for g in gap}
            runs = self._runs(arrs, Xs, Fs, gap, lambda g: cands[g], 2, self.KMAX2)
            for s, L, path, w in self._chain(runs):
                small = len(cands[gap[s]]) <= 20
                for k in range(L):
                    d[gap[s] + k], exact[gap[s] + k] = path[k], (L >= 3 or small)
            near = prev
            for g in gap:
                if d[g] is not None:
                    near = d[g]
                    continue
                C = cands[g]
                if len(C) == 0:
                    C = self._cands(self.all, Xs[g], Fs[g], lo, hi)
                    if len(C) == 0:
                        C = self._cands(self.all, Xs[g], Fs[g])
                    if len(C):
                        d[g] = self._choose(Xs[g], C, near if near is not None else nxt)
                        exact[g] = False
                else:
                    d[g] = self._choose(Xs[g], C, near if near is not None else nxt)
                    exact[g] = len(C) == 1
                if d[g] is not None:
                    near = d[g]
            i = j
        out = {}
        for i in range(n):
            fo = None if d[i] is None else Xs[i] + d[i]
            for key in keys[i]:
                out[key] = (fo, exact[i])
        return out


# --------------------------------------------------------------------------
# per-zone listing
# --------------------------------------------------------------------------

def list_zone(zone):
    """-> [(type_name, name, flag)] for every directory asset; flag '' exact,
    '~' approximate (ambiguous de-dup), '!' unresolved/unnamed."""
    d = zone.data
    rows = [None] * len(zone.assets)
    refs = []
    for a in zone.assets:
        b = a.blob
        t = a.type
        if len(b) < 8:
            rows[a.index] = (a.type_name, "<empty>", "!")
            continue
        if t == T_LOCALIZE:
            vp, npr = struct.unpack_from("<II", b, 0)
            pos = 8
            if vp == PTR_INLINE:
                v = cstr(b, pos)
                pos += (len(v.encode("latin-1")) + 1) if v is not None else 0
            if npr == PTR_INLINE:
                rows[a.index] = (a.type_name, cstr(b, pos) or "<empty>", "")
            elif npr == 0:
                rows[a.index] = (a.type_name, "<null>", "!")
            else:
                refs.append((a.index, (npr - 1) & 0x0FFFFFFF, a.offset + za.ASSET_BASE))
            continue
        name_ptr_off = 32 if t == T_IMAGE else 0
        p0 = struct.unpack_from("<I", b, name_ptr_off)[0]
        if p0 == PTR_INLINE:
            hdr = 36 if t == T_IMAGE else HEADER.get(t)
            if hdr is None:
                rows[a.index] = (a.type_name, "<inline-name, unknown header>", "!")
            else:
                s = cstr(b, hdr)
                rows[a.index] = (a.type_name, s if s is not None else "<empty>",
                                 "" if s else "!")
        elif p0 == 0:
            rows[a.index] = (a.type_name, "<null>", "!")
        elif p0 == 0xFFFFFFFE:
            rows[a.index] = (a.type_name, "<asset-ref>", "!")
        else:
            if ((p0 - 1) >> 28) != 3:
                rows[a.index] = (a.type_name, "<ptr:%#010x>" % p0, "!")
            else:
                refs.append((a.index, (p0 - 1) & 0x0FFFFFFF, a.offset + za.ASSET_BASE))
    if refs:
        if np is None:
            raise SystemExit("numpy is required to resolve de-duplicated names")
        # the four per-map world assets carry the com_map's name
        anchors = {}
        com = [r for r in rows if r is not None and r[0] == "com_map" and r[2] == ""]
        if com:
            want = com[0][1].encode("latin-1")
            for idx, X, F in refs:
                if zone.assets[idx].type in (15, 18, 20, 21):
                    anchors[idx] = want
        # per-type alphabet learned from this zone's inline names (plus the
        # global prior below when a type has too few of them here)
        sigs = collections.defaultdict(lambda: [0, 0])
        for a in zone.assets:
            r = rows[a.index]
            if r is not None and r[2] == "" and not r[1].startswith("<"):
                sigs[a.type][0] |= name_sig(r[1].encode("latin-1"))
                sigs[a.type][1] += 1
        for t, (m, c) in TYPE_SIG_PRIOR.items():
            sigs[t][0] |= m
            sigs[t][1] += c
        def mask_for(t):
            m, c = sigs.get(t, (0, 0))
            return m if c >= 5 else 0xFF
        refs = [(idx, X, F, mask_for(zone.assets[idx].type)) for idx, X, F in refs]
        res = RefResolver(d, anchors).resolve(refs)
        for idx, X, F, _ in refs:
            a = zone.assets[idx]
            fo, exact = res.get(idx, (None, False))
            if fo is None:
                rows[idx] = (a.type_name, "<unresolved:b3+%#x>" % X, "!")
            else:
                rows[idx] = (a.type_name, cstr(d, fo) or "<empty>", "" if exact else "~")
    return rows


def write_zone(out_dir, zone_name, rows):
    path = os.path.join(out_dir, zone_name + ".txt")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for tn, name, flag in sorted(rows, key=lambda r: (r[0], r[1].lower(), r[1])):
            f.write("%s\t%s%s\n" % (tn, name, ("\t" + flag) if flag else ""))
    return path


def read_zone_file(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 2:
                rows.append((parts[0], parts[1], parts[2] if len(parts) > 2 else ""))
    return rows


# --------------------------------------------------------------------------
# indexes + README
# --------------------------------------------------------------------------

def classify(zone):
    if zone.startswith(("patch_", "localized_")):
        base = zone.split("_", 1)[1]
        if base.startswith("localized_"):
            base = base.split("_", 1)[1]
    else:
        base = zone
    if base.startswith("common_gametype_"):
        return "gametype"
    if base.startswith(("mp_", "zm_", "coop_")) and base not in ("mp_playlists",):
        return "map-load" if base.endswith("_load") else "map"
    return "startup"


def build_indexes(out_dir, per_zone, decode_failures):
    by_type = collections.defaultdict(list)   # type -> [(name, zone, flag)]
    counts = collections.OrderedDict()        # zone -> Counter(type)
    for zone in sorted(per_zone):
        c = collections.Counter()
        for tn, name, flag in per_zone[zone]:
            by_type[tn].append((name, zone, flag))
            c[tn] += 1
        counts[zone] = c
    # remove stale ALL_ files then write fresh
    for fn in os.listdir(out_dir):
        if fn.startswith("ALL_") and fn.endswith(".txt"):
            os.remove(os.path.join(out_dir, fn))
    for tn, rows in by_type.items():
        with open(os.path.join(out_dir, "ALL_%s.txt" % tn), "w",
                  encoding="utf-8", newline="\n") as f:
            for name, zone, flag in sorted(rows, key=lambda r: (r[0].lower(), r[0], r[1])):
                f.write("%s\t%s%s\n" % (name, zone, ("\t" + flag) if flag else ""))
    with open(os.path.join(out_dir, "ALL_animtree.txt"), "w", encoding="utf-8",
              newline="\n") as f:
        for name, zone, flag in sorted(by_type.get("rawfile", ()),
                                       key=lambda r: (r[0].lower(), r[1])):
            if name.lower().endswith(".atr"):
                f.write("%s\t%s\n" % (name, zone))
    all_types = sorted(set(by_type), key=lambda t: za.type_index(t) if t in za.ASSET_TYPES else 999)
    with open(os.path.join(out_dir, "COUNTS.tsv"), "w", encoding="utf-8", newline="\n") as f:
        f.write("zone\tclass\ttotal\t" + "\t".join(all_types) + "\n")
        for zone, c in counts.items():
            f.write("%s\t%s\t%d\t" % (zone, classify(zone), sum(c.values()))
                    + "\t".join(str(c.get(t, 0)) for t in all_types) + "\n")
    write_readme(out_dir, counts, by_type, all_types, decode_failures)


def write_readme(out_dir, counts, by_type, all_types, decode_failures):
    total_flags = collections.Counter()
    for rows in by_type.values():
        for _, _, flag in rows:
            total_flags[flag] += 1
    main_cols = ["xanim", "xmodel", "material", "techset", "image", "sound",
                 "fx", "weapon", "weaponattach", "vehicle", "rawfile",
                 "stringtable", "localize", "menufile", "menu"]
    main_cols = [c for c in main_cols if c in all_types]
    other = [t for t in all_types if t not in main_cols]
    L = []
    L.append("# CoDOL 1.1.1.13 zone asset listing\n")
    L.append("Generated by `tools/codol_zone_assets.py` from the fastfiles in "
             "`client_shipRetail/chinese/` (the only zone directory the client "
             "mounts; the `ff00xx.ff` files at the game root are PE executables, "
             "not zones).  Regenerate with:\n")
    L.append("```\npython tools/codol_zone_assets.py            # all zones\n"
             "python tools/codol_zone_assets.py mp_rust    # one zone, then rebuild indexes\n```\n")
    L.append("Needs numpy and the alpha0022 Python server dir (env `CODOL_ALPHA0022`, "
             "default `D:\\CoD\\CODOL Builds\\...\\alpha0022`) for its measured "
             "fastfile reader `zone_assets.py`.  First run inflates every zone "
             "(~4 min); the inflated copies are cached under `%TEMP%\\codol_zones`.\n")
    L.append("## Files\n")
    L.append("* `<zone>.txt` -- every asset in that zone's directory, `type<TAB>name`, "
             "sorted by type then name.  An optional third column flags `~` = name "
             "recovered from a de-duplicated reference without a corroborating run "
             "(usually right, not proven -- see 'Name location' below) and `!` = "
             "unresolved/unnamed (placeholder in the name column).\n"
             "* `ALL_<type>.txt` -- merged per-type index, `name<TAB>zone[<TAB>flag]`, "
             "one line per (name, zone) pair; a name in several zones appears once per zone.\n"
             "* `ALL_animtree.txt` -- rawfiles ending in `.atr`.\n"
             "* `COUNTS.tsv` -- full per-type-per-zone matrix (every type).\n")
    L.append("Names are the exact bytes in the zone (latin-1); GSC/native code must "
             "match them case-insensitively with `/` and `\\` equivalent, which is what "
             "the engine does.\n")
    L.append("## Asset type numbering\n")
    L.append("Type ids are the 32-bit `type` field of each 16-byte directory entry in the "
             "inflated zone (`XAssetList` at +0x28).  The names are the IW4 enum; ids 36 "
             "(rawfile) and 37 (stringtable) are proven by struct decode and by "
             "`BG_TryLoadAnimList` in C1.exe, the rest are confirmed by content "
             "(xanim names at 2, xmodel at 4, material at 5, techset at 9, image at 10, "
             "sound aliases at 11, the five per-map world assets at 15/16/18/20/21, "
             "localize at 27, weapon at 28, fx at 30, leaderboarddef 38, "
             "structureddatadef 39, tracer 40, vehicle 41, addon_map_ents 42, "
             "weaponattach 43).\n")
    L.append("| id | type | id | type | id | type | id | type |\n|---|---|---|---|---|---|---|---|")
    T = za.ASSET_TYPES
    for r in range(0, len(T), 4):
        cells = []
        for k in range(r, r + 4):
            cells.append("%d | %s" % (k, T[k]) if k < len(T) else " | ")
        L.append("| " + " | ".join(cells) + " |")
    L.append("")
    L.append("Name location per type: the struct's first field is the name pointer "
             "(localize: value pointer then name pointer; image: name pointer at +32).  "
             "`0xFFFFFFFF` = inline name after the fixed struct, whose size is: "
             + ", ".join("%s=%d" % (za.type_name(t), h) for t, h in sorted(HEADER.items()) if h is not None)
             + ", image=36.  Any other value is a de-duplicated block-3 reference "
             "(C1.exe 0x004B6FD9) to a string written earlier in the zone (xmodels of "
             "common_gametype_mp are named by cells of mp/cocharitems/*.csv, sound "
             "aliases by the sound fields of the first weapon using them, the world "
             "assets of a map by its com_map name).  The tool does not replay the "
             "loader's block allocation; it recovers the file offset of the referenced "
             "string from the fact that block 3 is bump-allocated in stream order "
             "(file offset - block-3 offset is nearly constant for strings written "
             "back to back and only grows between blobs), fitting runs of consecutive "
             "references and keeping the maximum-weight monotone chain of runs, with "
             "candidates restricted to the character classes the type's inline names "
             "use.  Names from a run of >= 3 references, from a unique candidate or "
             "from the com_map anchor are unflagged; the rest carry `~`.  The IW4OL "
             "native loader (src/codol/assets/codol_load_blocks.c) is the authority "
             "when a `~` name matters.\n")
    L.append("Not covered: assets that only live *inside* another asset (e.g. XModels "
             "inlined in a GfxWorld or a weapon's attachments) have no directory entry "
             "and are not listed; the IW4OL native loader's alias catalogue "
             "(`codol_load_blocks.c`) is the authority for those.\n")
    L.append("## Zones\n")
    L.append("Mount groups (from the server's mount order, which mirrors the client): "
             "**startup** = code_pre_gfx_mp, code_post_gfx_default_mp, code_post_gfx_mp, "
             "common_mp, ui_mp, ui_viewer_mp, mp_playlists, development_mp and their "
             "`patch_`/`localized_`/`patch_localized_` companions; **gametype** = "
             "common_gametype_{mp,zm,coop} (+localized/patch), mounted per match type; "
             "**map** = `<map>_load` (load-screen), `<map>`, `patch_<map>` per map.  "
             "Every `.ff` in the directory is listed below.\n")
    L.append("Name-resolution totals over all zones: %d exact, %d approximate (`~`), "
             "%d unresolved/unnamed (`!`).\n"
             % (total_flags[""], total_flags["~"], total_flags["!"]))
    L.append("| zone | class | total | " + " | ".join(main_cols) + " | other |")
    L.append("|" + "---|" * (len(main_cols) + 4))
    for zone, c in counts.items():
        oth = sum(c.get(t, 0) for t in other)
        L.append("| %s | %s | %d | " % (zone, classify(zone), sum(c.values()))
                 + " | ".join(str(c.get(t, 0)) for t in main_cols) + " | %d |" % oth)
    L.append("")
    L.append("`other` = " + ", ".join(other) + " (see COUNTS.tsv).\n")
    L.append("## Per-type totals (distinct names across all zones)\n")
    L.append("| type | entries | distinct names |\n|---|---|---|")
    for t in all_types:
        rows = by_type[t]
        L.append("| %s | %d | %d |" % (t, len(rows), len({r[0].lower() for r in rows})))
    L.append("")
    L.append("## Zones or files that could not be decoded\n")
    if decode_failures:
        for name, why in decode_failures:
            L.append("* `%s` -- %s" % (name, why))
    else:
        L.append("* none")
    L.append("")
    with open(os.path.join(out_dir, "README.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L))


# --------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("zones", nargs="*", help="zone names (default: every .ff in the client zone dir)")
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--extra", action="append", default=[],
                    help="extra .ff path to try (listed in README on failure)")
    args = ap.parse_args(argv)
    os.makedirs(args.out, exist_ok=True)
    ffdir = za.ff_dir()
    zones = args.zones or sorted(f[:-3] for f in os.listdir(ffdir) if f.lower().endswith(".ff"))
    failures = []
    t0 = time.time()
    for zn in zones:
        t1 = time.time()
        try:
            zone = za.open_zone(zn)
            rows = list_zone(zone)
        except Exception as e:  # noqa: BLE001
            failures.append((zn, "%s: %s" % (type(e).__name__, e)))
            print("FAIL %s: %s" % (zn, e), file=sys.stderr)
            continue
        write_zone(args.out, zn, rows)
        fl = collections.Counter(r[2] for r in rows)
        print("%-45s %6d assets  ~%d !%d  %.1fs" % (zn, len(rows), fl["~"], fl["!"], time.time() - t1))
    for extra in args.extra:
        try:
            zone = za.open_zone(extra)
            rows = list_zone(zone)
            write_zone(args.out, zone.name, rows)
        except Exception as e:  # noqa: BLE001
            failures.append((extra, "%s: %s" % (type(e).__name__, e)))
    # root-level "ff" files that are not zones
    root = za.game_root()
    for fn in sorted(os.listdir(root)):
        if fn.lower().startswith("ff") and fn.lower().split(".")[-1] in ("ff", "ff2"):
            with open(os.path.join(root, fn), "rb") as f:
                magic = f.read(8)
            failures.append((fn, "not a fastfile (magic %r%s)" % (
                magic[:4], "; a PE executable" if magic[:2] == b"MZ" else "")))
    per_zone = {}
    for fn in os.listdir(args.out):
        if fn.endswith(".txt") and not fn.startswith("ALL_"):
            per_zone[fn[:-4]] = read_zone_file(os.path.join(args.out, fn))
    build_indexes(args.out, per_zone, failures)
    print("done: %d zones, %d failures, %.0fs -> %s" % (len(per_zone), len(failures),
                                                        time.time() - t0, args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
