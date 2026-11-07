#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
build_ff.py -- build codol_english.ff, the English localize fastfile that
Kernel33.dll loads ahead of C1's Chinese zones (docs/CODOL_ENGLISH_UI.md).

    python tools/codol_english/build_ff.py                 # -> tools/codol_english/out/codol_english.ff
    python tools/codol_english/build_ff.py -o X.ff --table T.tsv
    python tools/codol_english/build_ff.py --inspect X.ff  # decrypt a built file and summarise it

Input: codol_english.tsv (KEY<TAB>text; a line that does not start with an
upper-case KEY<TAB> continues the previous value after a newline, because the
first-pass table wrote multi-line values unescaped), and the C1 localize dump
from dump_c1_localize.py (run automatically when missing).

What goes in:
  * only names that some shipped C1 zone defines, spelled as C1 spells them:
    the localize pool holds 12000 entries (.rdata 0x00CD4D68, type 27) and an
    English-only name would take a slot C1 never needed;
  * only printable ASCII: C1 decodes strings as GBK, so a byte >= 0x80 would
    be read as half of a Chinese character;
  * only values whose printf conversions (%s %d ...) and &&N placeholders are
    the same multiset as the Chinese value the game would otherwise show -- a
    string with an extra %s is a crash when code formats it.  Where they
    differ the name is left out and C1 keeps its Chinese text.

Container: IWffu100 (unsigned): 21-byte header, RSA-OAEP(SHA-256) wrapped
AES-192 key and IV, then AES-CTR(zlib(zone)).  C1 decrypts an IWffu100 file in
ONE ctr_encrypt pass over the bytes of the first 256 KiB read chunk (stream
init 0x004B5AC0 -> 0x004B5B7D; chunk size 0x40000 at 0x004B67A5), so the file
must fit in one chunk.  build_ff refuses a bigger one.

Zone image: the CODOL layout measured by alpha0022's ffwriter/codol_ff.py
(0x28-byte header {size, externalSize, blockSize[8]}, XAssetList, 16-byte
asset directory {type, offset, ptr, size}, then the asset blobs back to back).
LocalizeEntry blob, MEASURED on the shipped localized zones:
    u32 valuePtr = 0xFFFFFFFF, u32 namePtr = 0xFFFFFFFF, value\0, name\0
"""
from __future__ import annotations

import argparse
import collections
import datetime
import hashlib
import json
import os
import re
import struct
import subprocess
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_TABLE = os.path.join(HERE, "codol_english.tsv")
DEFAULT_OUT = os.path.join(HERE, "out", "codol_english.ff")
DEFAULT_C1DUMP = os.path.join(os.environ.get("TEMP", "."), "codol_english", "c1_localize.json")
DEFAULT_EXE = os.environ.get("CODOL_EXE", r"D:\CoD\CODOL Builds\Call of Duty Online 1.1.1.13\C1.exe")

# --- measured constants (see the docstring and alpha0022 ffwriter/codol_ff.py) ---------------
MAGIC_PLAIN = b"IWffu100"
ZONE_VERSION = 0x14E            # cmp eax, 0x14E @ 0x004B5E3B
HEADER_FLAG = 1
RSA_BLOB_LEN = 0x100
BODY_OFF = 0x15 + RSA_BLOB_LEN
READ_CHUNK = 0x40000            # DB file reader chunk, 0x004B67A5 / 0x004B68CC
ASSET_BASE = 0x28
PTR_INLINE = 0xFFFFFFFF
T_LOCALIZE = 27
T_RAWFILE = 36
BLOCK0 = 0x20                   # every shipped localize/rawfile-only zone declares 0x20
BLOCK_MARGIN = 0x10000          # over-provisioning is free (DB_AllocXBlocks never checks it)
POOL_LOCALIZE = 12000           # .rdata 0x00CD4D68[27]
KEY_OFF, KEY_LEN = 0x83C248, 1191   # DER RSA key inside C1.exe (alpha0022 zone_assets.py)
KEY_SHA = "3a2f7891ac98f1fdf6a9a221c5586725157df270d6831e0ff82c383cd262cbb5"

# Zones whose names get English, by --scope.  The localize pool holds 12000 entries and
# vanilla C1 already peaks near 11100 on a zombies map (base 9747 names + ~1340 map-level
# entries).  English for a name that only a map-level zone defines is a permanent extra entry
# (the Chinese one is still loaded, parked behind it), so only the MP common/gametype/map
# zones are added by default: +~520 entries, worst case ~11600.  "all" adds coop and zombies
# names too (+~2140) and overflows the pool on those maps.
BASE_ZONES = ("patch_localized_code_post_gfx_mp", "localized_code_post_gfx_mp")
MP_ZONES = BASE_ZONES + ("patch_localized_common_mp", "localized_common_mp",
                         "patch_localized_common_gametype_mp", "localized_common_gametype_mp",
                         "patch_mp_killhouse_sh", "mp_killhouse_sh")
SCOPES = {"base": BASE_ZONES, "mp": MP_ZONES, "all": None}

KEY_LINE = re.compile(r"^([A-Z0-9_]+)\t(.*)$")
FMT = re.compile(r"%%|%[-+ #0]*\d*(?:\.\d+)?[sdifuxXcgeEpl]|&&\d+")


# --- table ------------------------------------------------------------------------------------
def unescape(s):
    if "\\" not in s:
        return s
    res, i = [], 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            n = s[i + 1]
            res.append({"n": "\n", "t": "\t", "r": "\r", "\\": "\\"}.get(n, "\\" + n))
            i += 2
        else:
            res.append(c)
            i += 1
    return "".join(res)


def read_table(path):
    """KEY -> English text.  Continuation lines (no KEY<TAB>) extend the previous value."""
    out = collections.OrderedDict()
    last = None
    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.rstrip("\r\n")
            if line.startswith("#"):
                last = None
                continue
            m = KEY_LINE.match(line)
            if m:
                last = m.group(1)
                out[last] = unescape(m.group(2))
            elif last is not None:
                out[last] += "\n" + unescape(line)
    return out


# --- C1 reference -----------------------------------------------------------------------------
def zone_rank(zn):
    """The order C1 meets localize names in: patch_X before X, code zones first."""
    order = ["patch_localized_code_post_gfx_mp", "localized_code_post_gfx_mp",
             "patch_localized_common_mp", "localized_common_mp"]
    return (order.index(zn) if zn in order else len(order), zn)


DEFAULT_LIVE = os.path.join(HERE, "sources", "live_dump_menu.tsv")
DEFAULT_NATIVE = os.path.join(HERE, "sources", "native_localize.tsv")
KEYLIKE = re.compile(rb"^[A-Z0-9_]+$")


def read_native(path):
    """NAME_UPPER -> (C1 spelling, GBK text) for the SUBTITLE_* names of the
    server's codol_dumplocalize output (see make_table.py).  The native zone
    loader resolves the name references the zone dump only guesses: most of
    the announcer subtitle names the zone dump places carry another line's
    text (and 283 are missing from it).  The first line for a name is the one
    C1 shows."""
    native = {}
    if not path or not os.path.exists(path):
        return native
    with open(path, "rb") as f:
        for line in f.read().split(b"\n"):
            if b"\t" not in line:
                continue
            k, v = line.split(b"\t", 1)
            name = k.decode("latin-1")
            if name.upper().startswith("SUBTITLE_"):
                native.setdefault(name.upper(), (name, unescape_bytes(v.rstrip(b"\r"))))
    return native


def read_live(path):
    """NAME_UPPER -> the exact GBK text a running C1 held (first-pass dump, escaped)."""
    live = {}
    if not path or not os.path.exists(path):
        return live
    with open(path, "rb") as f:
        for line in f.read().split(b"\n"):
            if b"\t" not in line:
                continue
            k, v = line.rstrip(b"\r").split(b"\t", 1)
            live.setdefault(k.decode("latin-1").upper(), unescape_bytes(v))
    return live


def unescape_bytes(b):
    out, i = bytearray(), 0
    while i < len(b):
        if b[i] == 0x5C and i + 1 < len(b):
            out += {0x6E: b"\n", 0x74: b"\t", 0x72: b"\r"}.get(b[i + 1], bytes([b[i + 1]]))
            i += 2
        else:
            out.append(b[i])
            i += 1
    return bytes(out)


def load_c1(path, live_path=DEFAULT_LIVE, native_path=DEFAULT_NATIVE):
    """-> {NAME_UPPER: (C1 spelling, [(zone, gbk bytes or None, approx)])}

    The zone dump's values are partly de-duplicated references that RefResolver
    places heuristically, and about 1,900 of them land on the wrong string (a
    value that is itself another localize NAME, e.g. MPUI_SCOREBOARD_SCORE ->
    "EXE_BAD_CHALLENGE").  Such a value looks like ASCII and hid the name from
    translation.  The live dump holds the exact text for all 9,747 base names;
    it wins, and a remaining key-like value is treated as unknown.
    """
    if not os.path.exists(path):
        subprocess.check_call([sys.executable, os.path.join(HERE, "dump_c1_localize.py"), "-o", path])
    with open(path) as f:
        d = json.load(f)
    live = read_live(live_path)
    names = set(e[1].upper() for l in d.values() for e in l)
    out = collections.OrderedDict()
    for zn in sorted(d, key=zone_rank):
        for _i, name, approx, val in d[zn]:
            if name.startswith("<"):
                continue
            v = bytes.fromhex(val) if val is not None else None
            ap = approx == "~"
            if name.upper() in live:
                v, ap = live[name.upper()], False
            elif v is not None and KEYLIKE.match(v) and v.decode().upper() in names:
                v, ap = None, True
            out.setdefault(name.upper(), (name, []))[1].append((zn, v, ap))
    # Subtitle names take the native dump's text.  Names the zone dump never
    # placed (283 announcer subtitles) are NOT added: every English name is a
    # permanent localize pool entry, and +502 more would pass the 12000-entry
    # pool on a zombies map (see POOL_LOCALIZE).  They stay Chinese as before.
    for key, (_name, value) in read_native(native_path).items():
        if key in out:
            out[key] = (out[key][0], [(z, value, False) for z, _v, _ap in out[key][1]])
    return out


def fmt_tokens(s):
    if isinstance(s, bytes):
        s = s.decode("latin-1")
    return sorted(FMT.findall(s))


def select(table, c1, stats, missing, zones=None):
    """-> [(C1 name, value bytes)] in C1 order; only names some zone in ``zones`` defines."""
    chosen = []
    for key, (name, vals) in c1.items():
        live = next((v for _z, v, ap in vals if v is not None and not ap), None)
        approx = live is None
        if live is None:
            live = next((v for _z, v, _ap in vals if v is not None), None)
        en = table.get(key)
        if live is not None and all(c < 0x80 for c in live):
            stats["already ASCII in C1 (left alone)"] += 1
            continue
        if zones is not None and not any(z in zones for z, _v, _ap in vals):
            stats["outside --scope (left Chinese)"] += 1
            missing[name] = (vals[0][0], live)
            continue
        if en is None or not en.strip():
            stats["no English text"] += 1
            missing[name] = (vals[0][0], live)
            continue
        if any((ord(ch) < 0x20 and ch not in "\n\t") or ord(ch) > 0x7E for ch in en):
            stats["dropped: not printable ASCII"] += 1
            missing[name] = (vals[0][0], live)
            continue
        want = fmt_tokens(live) if live is not None else []
        got = fmt_tokens(en)
        if got != want and not (approx and not got):
            stats["dropped: format tokens differ"] += 1
            missing[name] = (vals[0][0], live)
            continue
        chosen.append((name, en.encode("ascii")))
        stats["English"] += 1
    return chosen


# --- zone image -------------------------------------------------------------------------------
def pack_localize(name, value):
    return struct.pack("<II", PTR_INLINE, PTR_INLINE) + value + b"\0" + name.encode("ascii") + b"\0"


def pack_rawfile(name, data=b""):
    # CODOL RawFile {name, compressedLen, len, buffer}; an uncompressed buffer is streamed with a NUL
    return struct.pack("<IiiI", PTR_INLINE, 0, len(data), PTR_INLINE) + name.encode() + b"\0" + data + b"\0"


def build_zone(zone_name, entries):
    assets = [(T_RAWFILE, pack_rawfile(zone_name))]    # the zone marker every shipped zone carries
    assets += [(T_LOCALIZE, pack_localize(n, v)) for n, v in entries]
    body = bytearray(struct.pack("<IIII", 0, 0, len(assets), PTR_INLINE))
    table_at = len(body)
    body += b"\0" * (16 * len(assets))
    first = len(body)
    for i, (t, blob) in enumerate(assets):
        struct.pack_into("<IIII", body, table_at + 16 * i, t, len(body), PTR_INLINE, len(blob))
        body += blob
    blocks = [0] * 8
    blocks[0] = BLOCK0
    blocks[3] = (len(body) - first) + 16 * len(assets) + BLOCK_MARGIN
    return struct.pack("<II8I", len(body), 0, *blocks) + bytes(body)


def parse_zone(zone):
    """Minimal reader, the inverse of build_zone -> [(type, blob)]."""
    size = struct.unpack_from("<I", zone, 0)[0]
    if size != len(zone) - ASSET_BASE:
        raise ValueError("zone size field %#x != %#x" % (size, len(zone) - ASSET_BASE))
    sc, _sp, n, ap = struct.unpack_from("<4I", zone, ASSET_BASE)
    if sc != 0 or ap != PTR_INLINE:
        raise ValueError("unexpected XAssetList")
    p = ASSET_BASE + 16
    return [(t, zone[ASSET_BASE + off:ASSET_BASE + off + sz])
            for t, off, _ptr, sz in (struct.unpack_from("<4I", zone, p + 16 * i) for i in range(n))]


# --- container --------------------------------------------------------------------------------
def rsa_key(exe):
    from Crypto.PublicKey import RSA
    with open(exe, "rb") as f:
        f.seek(KEY_OFF)
        der = f.read(KEY_LEN)
    if hashlib.sha256(der).hexdigest() != KEY_SHA:
        raise SystemExit("%s: the zone key at %#x is not the 1.1.1.13 one" % (exe, KEY_OFF))
    return RSA.import_key(der)


def ctr(key, iv, data):
    """AES-CTR as LibTomCrypt runs it here: E(IV) first, counter incremented little-endian."""
    from Crypto.Cipher import AES
    from Crypto.Util import Counter
    c = Counter.new(128, initial_value=int.from_bytes(iv, "little"), little_endian=True)
    return AES.new(key, AES.MODE_CTR, counter=c).encrypt(data)


def filetime(when):
    delta = when - datetime.datetime(1601, 1, 1)
    v = (delta.days * 86400 + delta.seconds) * 10000000 + delta.microseconds * 10
    return (v >> 32) & 0xFFFFFFFF, v & 0xFFFFFFFF


def wrap(zone, exe):
    from Crypto.Cipher import PKCS1_OAEP
    from Crypto.Hash import SHA256
    key, iv = os.urandom(24), os.urandom(16)
    blob = PKCS1_OAEP.new(rsa_key(exe).public_key(), hashAlgo=SHA256).encrypt(key + iv)
    if len(blob) != RSA_BLOB_LEN:
        raise AssertionError("RSA blob is %d bytes" % len(blob))
    hi, lo = filetime(datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None))
    head = MAGIC_PLAIN + struct.pack("<IBII", ZONE_VERSION, HEADER_FLAG, hi, lo)
    return head + blob + ctr(key, iv, zlib.compress(zone, 9))


def unwrap(data, exe):
    from Crypto.Cipher import PKCS1_OAEP
    from Crypto.Hash import SHA256
    if data[:8] != MAGIC_PLAIN:
        raise ValueError("not an IWffu100 file")
    ver = struct.unpack_from("<I", data, 8)[0]
    if ver != ZONE_VERSION:
        raise ValueError("version %#x" % ver)
    mat = PKCS1_OAEP.new(rsa_key(exe), hashAlgo=SHA256).decrypt(data[0x15:BODY_OFF])
    return zlib.decompress(ctr(mat[:24], mat[24:40], data[BODY_OFF:]))


def check_with_alpha0022(zone, exe):
    """Parse the image with alpha0022's zone_assets.Zone, an independent reader, if present."""
    alpha = os.environ.get("CODOL_ALPHA0022", os.path.join(os.path.dirname(exe), "CODOL",
                                                           "1.1.1.13_server", "alpha0022"))
    for p in (alpha, os.path.join(alpha, "zones")):
        if p not in sys.path:
            sys.path.insert(0, p)
    try:
        import zone_assets as za
    except ImportError:
        return "alpha0022 zone_assets.py not found; independent check skipped"
    z = za.Zone(zone, "<english>")
    end = z.asset_table_offset + 16 * len(z.assets)
    for a in z.assets:
        if a.offset + ASSET_BASE != end:
            raise AssertionError("asset %d does not tile" % a.index)
        end += a.size
    if end != len(zone):
        raise AssertionError("assets end at %#x, zone is %#x" % (end, len(zone)))
    return "alpha0022 zone_assets.Zone reads it: %d assets, tiling exact" % len(z.assets)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build the English localize fastfile for C1.")
    ap.add_argument("-o", "--out", default=DEFAULT_OUT)
    ap.add_argument("--table", default=DEFAULT_TABLE)
    ap.add_argument("--c1", default=DEFAULT_C1DUMP, help="dump_c1_localize.py output")
    ap.add_argument("--zone", default=None, help="zone name (default: the output file name)")
    ap.add_argument("--exe", default=DEFAULT_EXE, help="C1.exe, for the zone key")
    ap.add_argument("--scope", choices=sorted(SCOPES), default="mp",
                    help="which zones' names get English (default mp; see SCOPES)")
    ap.add_argument("--missing", default=None, help="write the untranslated C1 names here (TSV)")
    ap.add_argument("--inspect", metavar="FF", help="decrypt a built file and summarise it")
    args = ap.parse_args(argv)

    if args.inspect:
        with open(args.inspect, "rb") as f:
            zone = unwrap(f.read(), args.exe)
        assets = parse_zone(zone)
        print("%s: zone image %d bytes, %d assets %s" % (
            args.inspect, len(zone), len(assets), dict(collections.Counter(t for t, _ in assets))))
        for t, b in assets[:5]:
            print("   type %d  %r" % (t, b[8:100] if t == T_LOCALIZE else b[16:60]))
        return

    zone_name = args.zone or os.path.splitext(os.path.basename(args.out))[0]
    table = read_table(args.table)
    c1 = load_c1(args.c1)
    stats, missing = collections.Counter(), collections.OrderedDict()
    entries = select(table, c1, stats, missing, SCOPES[args.scope])
    if len(entries) >= POOL_LOCALIZE:
        raise SystemExit("%d entries would not fit the localize pool" % len(entries))
    zone = build_zone(zone_name, entries)
    if [b for _t, b in parse_zone(zone)[1:]] != [pack_localize(n, v) for n, v in entries]:
        raise AssertionError("zone does not read back")
    print(check_with_alpha0022(zone, args.exe))
    ff = wrap(zone, args.exe)
    if len(ff) > READ_CHUNK:
        raise SystemExit("%s would be %d bytes; C1 decrypts only the first %d bytes of an IWffu100 "
                         "file" % (args.out, len(ff), READ_CHUNK))
    if unwrap(ff, args.exe) != zone:
        raise AssertionError("container does not round-trip")
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "wb") as f:
        f.write(ff)
    if args.missing:
        with open(args.missing, "w", encoding="utf-8", newline="\n") as f:
            f.write("# C1 localize names left in Chinese: NAME<TAB>first zone<TAB>Chinese text\n")
            for n, (z, v) in missing.items():
                zh = v.decode("gbk", "replace") if v is not None else ""
                f.write("%s\t%s\t%s\n" % (n, z, zh.replace("\n", "\\n")))
    print("table %s: %d keys; C1 localize names: %d" % (os.path.basename(args.table), len(table), len(c1)))
    for k in sorted(stats):
        print("  %-36s %6d" % (k, stats[k]))
    print("wrote %s: zone '%s', %d localize entries, image %d bytes, file %d bytes (limit %d)"
          % (args.out, zone_name, len(entries), len(zone), len(ff), READ_CHUNK))


if __name__ == "__main__":
    main()
