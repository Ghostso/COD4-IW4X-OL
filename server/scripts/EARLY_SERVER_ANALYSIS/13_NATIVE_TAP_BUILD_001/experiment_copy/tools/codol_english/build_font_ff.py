#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
build_font_ff.py -- build codol_english_font.ff, a patch-folder zone that gives
C1's Scaleform menus a Latin font for English while every Chinese glyph stays.

    python tools/codol_english/build_font_ff.py                       # Saira Condensed (OFL)
    python tools/codol_english/build_font_ff.py --style agency        # the shipped Agency FB glyphs
    python tools/codol_english/build_font_ff.py --regular R.ttf --bold B.ttf
    python tools/codol_english/build_font_ff.py --latin-only -o out/codol_font_poc.ff
    python tools/codol_english/build_font_ff.py --inspect out/codol_english_font.ff

How C1 picks a menu font (docs/CODOL_ENGLISH_UI.md, "Font"): every text field
in codo/codologin/codohud/codoingame.gfx names an alias, and 0x006B50B0 loads
the rawfile scaleform/fonts_ingame.gfx into a GFx FontLib and maps
    $font_2 -> FZLanTingHei-R-GBK      $font_3 -> FZZongYi-M05S
    $font_4 -> Agency FB               $font_5 -> Agency FB (bold)
    $IMECandidateListFont -> FZLanTingHei-R-GBK

This tool takes the shipped library (patch_code_post_gfx_mp's copy, the one
C1 links), replaces the glyphs U+0020..U+007E of the two Chinese fonts with
Latin glyphs scaled to the Chinese font's own cap height, and keeps the font
names, metrics and every other glyph.  English text (which build_ff.py keeps
to printable ASCII) is then drawn in the Latin design; Chinese text, player
names and anything left untranslated still find their glyphs in the same font.

The result goes into a zone as the rawfile scaleform/fonts_ingame.gfx.  In
the patch folder it loads ahead of code_post_gfx, and C1 keeps the first
rawfile it links under a name, so the library C1 opens is this one.  Without
the file (or with +set codol_patchdir 0) nothing changes.

Size: the full library is about 7.4 MB compressed, far above the 256 KiB
that fits in C1's first read chunk.  C1 decrypts only that first chunk of an
unsigned zone (0x004B5B7D, over the z_stream input 0x017C68B4 after the
header is consumed) and inflates every later chunk as it is (0x004B69E0: no
decrypt when the zone is unsigned).  This builder therefore encrypts the
first 0x40000-0x115 body bytes and writes the rest in plain; --inspect reads
a file back the same way.  Kernel33's patch folder must accept files larger
than 0x40000 (see docs/CODOL_ENGLISH_UI.md for the one-line loader change).
--latin-only keeps only ASCII in the two fonts, and --subset N keeps ASCII
plus the N Chinese characters used most in C1's own localize text, so the
file fits in 256 KiB and loads with the 256 KiB loader: test builds, not for
players, because the other Chinese characters have no glyphs.
"""
from __future__ import annotations

import argparse
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_ff as bf          # noqa: E402  container constants, RSA key, AES-CTR
import gfx_font as gf          # noqa: E402

FONTLIB = "scaleform/fonts_ingame.gfx"
FONT_DIR = os.path.join(HERE, "fonts")
DEFAULT_OUT = os.path.join(HERE, "out", "codol_english_font.ff")
LATIN = list(range(0x20, 0x7F))            # everything an English localize value may contain
ENCRYPTED = bf.READ_CHUNK - bf.BODY_OFF    # body bytes inside C1's first read chunk

# Chinese font -> which donor weight replaces its Latin glyphs
TARGETS = {"FZLanTingHei-R-GBK": "regular",   # $font_2, body text, IME list
           "FZZongYi-M05S": "bold"}           # $font_3, most buttons, titles and labels
STYLES = {
    # SIL OFL 1.1, files and licence in tools/codol_english/fonts/
    "saira": ("SairaCondensed-Medium.ttf", "SairaCondensed-SemiBold.ttf"),
    # the Agency FB glyphs already inside the shipped library ($font_4 / $font_5)
    "agency": (("Agency FB", 0), ("Agency FB", 1)),
}


def stock_library():
    """Bytes of the fonts_ingame.gfx C1 links: patch_code_post_gfx_mp loads before code_post_gfx_mp."""
    alpha = os.environ.get("CODOL_ALPHA0022", os.path.join(os.path.dirname(bf.DEFAULT_EXE), "CODOL",
                                                           "1.1.1.13_server", "alpha0022"))
    for p in (alpha, os.path.join(alpha, "zones")):
        if p not in sys.path:
            sys.path.insert(0, p)
    import zone_assets as za
    for zn in ("patch_code_post_gfx_mp", "code_post_gfx_mp"):
        z = za.open_zone(zn)
        for a in z.by_type(bf.T_RAWFILE):
            name, data = za.decode_rawfile(a.blob)
            if name == FONTLIB:
                return zn, data
    raise SystemExit("%s not found in the code_post_gfx zones" % FONTLIB)


def donors(args, fonts):
    if args.regular or args.bold:
        if not (args.regular and args.bold):
            raise SystemExit("--regular and --bold go together")
        return gf.TTFDonor(args.regular), gf.TTFDonor(args.bold), "custom"
    reg, bold = STYLES[args.style]
    if args.style == "agency":
        by = {(f.display_name, f.flags & 1): f for f in fonts}
        return gf.GFxDonor(by[reg]), gf.GFxDonor(by[bold]), args.style
    return (gf.TTFDonor(os.path.join(FONT_DIR, reg)), gf.TTFDonor(os.path.join(FONT_DIR, bold)),
            args.style)


def common_cjk(n):
    """The n characters >= U+2E80 used most in C1's Chinese localize values (dump_c1_localize.py)."""
    if not n:
        return set()
    import collections
    import json
    with open(bf.DEFAULT_C1DUMP) as f:
        dump = json.load(f)
    count = collections.Counter()
    for ents in dump.values():
        for e in ents:
            if e[3]:
                count.update(ch for ch in bytes.fromhex(e[3]).decode("gbk", "replace") if ord(ch) >= 0x2E80)
    return {ord(ch) for ch, _k in count.most_common(n)}


def build_library(stock, args, log=print):
    head, tags = gf.read_movie(stock)
    fonts = [gf.Font3.parse(b) for c, b, _l in tags if c == gf.T_DEFINEFONT3]
    reg, bold, style = donors(args, fonts)
    out = []
    for code, body, long_form in tags:
        if code == gf.T_DEFINEFONT3:
            f = gf.Font3.parse(body)
            weight = TARGETS.get(f.display_name)
            if weight:
                scale, n = gf.graft(f, reg if weight == "regular" else bold, LATIN,
                                    cap_ratio=args.cap, track=args.track)
                if args.latin_only or args.subset:
                    f.keep_only(set(LATIN) | common_cjk(args.subset))
                body = f.build()
                log("  %-20s %d Latin glyphs from the %s %s donor (scale %.3f), %d glyphs in all"
                    % (f.display_name, n, style, weight, scale, len(f.codes)))
        out.append((code, body, long_form))
    lib = gf.write_movie(head, out)
    # read back: every font parses, the grafted glyphs decode
    _h, back = gf.read_movie(lib)
    for code, body, _l in back:
        if code == gf.T_DEFINEFONT3:
            f = gf.Font3.parse(body)
            if f.build() != body:
                raise AssertionError("%s does not rebuild byte-exactly" % f.display_name)
            for c in LATIN:
                i = f.index(c)
                if i is not None:
                    gf.decode_shape(f.shapes[i])
    return lib


# --- zone and container -----------------------------------------------------------------------
def pack_rawfile_z(name, data):
    """RawFile {name, compressedLen, len, buffer}, zlib body, no terminator (as the shipped
    patch_code_post_gfx_mp stores fonts_ingame.gfx)."""
    z = zlib.compress(data, 9)
    return struct.pack("<IiiI", bf.PTR_INLINE, len(z), len(data), bf.PTR_INLINE) + name.encode() + b"\0" + z


def build_zone(zone_name, assets):
    assets = [(bf.T_RAWFILE, bf.pack_rawfile(zone_name))] + assets
    body = bytearray(struct.pack("<IIII", 0, 0, len(assets), bf.PTR_INLINE))
    table_at = len(body)
    body += b"\0" * (16 * len(assets))
    first = len(body)
    for i, (t, blob) in enumerate(assets):
        struct.pack_into("<IIII", body, table_at + 16 * i, t, len(body), bf.PTR_INLINE, len(blob))
        body += blob
    blocks = [0] * 8
    blocks[0] = bf.BLOCK0
    blocks[3] = (len(body) - first) + 16 * len(assets) + bf.BLOCK_MARGIN   # rawfiles stream to block 3
    return struct.pack("<II8I", len(body), 0, *blocks) + bytes(body)


def wrap(zone, exe):
    """IWffu100; only the body bytes in C1's first read chunk are encrypted."""
    from Crypto.Cipher import PKCS1_OAEP
    from Crypto.Hash import SHA256
    import datetime
    key, iv = os.urandom(24), os.urandom(16)
    blob = PKCS1_OAEP.new(bf.rsa_key(exe).public_key(), hashAlgo=SHA256).encrypt(key + iv)
    hi, lo = bf.filetime(datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None))
    head = bf.MAGIC_PLAIN + struct.pack("<IBII", bf.ZONE_VERSION, bf.HEADER_FLAG, hi, lo)
    body = zlib.compress(zone, 9)
    return head + blob + bf.ctr(key, iv, body[:ENCRYPTED]) + body[ENCRYPTED:]


def unwrap(data, exe):
    """Read a file the way C1 does: decrypt the first chunk's body bytes, inflate the rest as is."""
    from Crypto.Cipher import PKCS1_OAEP
    from Crypto.Hash import SHA256
    if data[:8] != bf.MAGIC_PLAIN or struct.unpack_from("<I", data, 8)[0] != bf.ZONE_VERSION:
        raise ValueError("not an IWffu100 version 0x14E file")
    mat = PKCS1_OAEP.new(bf.rsa_key(exe), hashAlgo=SHA256).decrypt(data[0x15:bf.BODY_OFF])
    body = data[bf.BODY_OFF:]
    return zlib.decompress(bf.ctr(mat[:24], mat[24:40], body[:ENCRYPTED]) + body[ENCRYPTED:])


def rawfiles(zone):
    out = {}
    for t, b in bf.parse_zone(zone):
        if t != bf.T_RAWFILE:
            continue
        _np, clen, ulen, _bp = struct.unpack_from("<IiiI", b, 0)
        e = b.index(b"\0", 16)
        name, data = b[16:e].decode(), b[e + 1:]
        out[name] = zlib.decompress(data[:clen]) if clen else data[:ulen]
    return out


# --- preview ----------------------------------------------------------------------------------
SAMPLES = ["MULTIPLAYER   Create a Class   Barracks   Store",
           "Team Deathmatch - Level 42 - 1,250 XP   [ESC] Back",
           u"开始游戏 Start Game  玩家 Player_01"]


def preview(stock, lib, path, px=26):
    from PIL import Image, ImageDraw
    def fonts(movie):
        return {gf.Font3.parse(b).display_name + (" Bold" if gf.Font3.parse(b).flags & 1 else ""):
                gf.Font3.parse(b) for c, b, _l in gf.read_movie(movie)[1] if c == gf.T_DEFINEFONT3}
    a, b = fonts(stock), fonts(lib)
    rows = []
    for alias, name in (("$font_3", "FZZongYi-M05S"), ("$font_2", "FZLanTingHei-R-GBK")):
        for tag, fs in (("stock", a), ("English", b)):
            rows.append(("%s %s (%s)" % (alias, tag, name), [gf.render(fs[name], s, px) for s in SAMPLES]))
    width = 360 + max(im.width for _l, ims in rows for im in ims)
    height = 10 + sum(sum(im.height for im in ims) + 10 for _l, ims in rows)
    out = Image.new("RGB", (width, height), (20, 24, 28))
    d = ImageDraw.Draw(out)
    y = 5
    for label, ims in rows:
        d.text((8, y + 8), label, fill=(255, 200, 80))
        for im in ims:
            out.paste((235, 235, 235), (360, y), im)
            y += im.height
        y += 10
    out.save(path)
    return path


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build the English Scaleform font zone for C1.")
    ap.add_argument("-o", "--out", default=DEFAULT_OUT)
    ap.add_argument("--zone", default=None, help="zone name (default: the output file name)")
    ap.add_argument("--exe", default=bf.DEFAULT_EXE, help="C1.exe, for the zone key")
    ap.add_argument("--style", choices=sorted(STYLES), default="saira")
    ap.add_argument("--regular", help="TTF/OTF for FZLanTingHei's Latin ($font_2)")
    ap.add_argument("--bold", help="TTF/OTF for FZZongYi's Latin ($font_3)")
    ap.add_argument("--cap", type=float, default=1.0, help="cap height relative to the Chinese font's")
    ap.add_argument("--track", type=float, default=0.0, help="extra spacing per glyph, em/1000")
    ap.add_argument("--latin-only", action="store_true",
                    help="drop the Chinese glyphs so the zone fits the 256 KiB loader (test only)")
    ap.add_argument("--subset", type=int, default=0, metavar="N",
                    help="like --latin-only, but keep the N most used Chinese characters too (test only)")
    ap.add_argument("--library-out", help="also write the rebuilt fonts_ingame.gfx here")
    ap.add_argument("--preview", help="write a PNG comparing stock and new Latin glyphs")
    ap.add_argument("--inspect", metavar="FF", help="read a built file back and summarise it")
    args = ap.parse_args(argv)

    if args.inspect:
        with open(args.inspect, "rb") as f:
            data = f.read()
        zone = unwrap(data, args.exe)
        rf = rawfiles(zone)
        print("%s: %d bytes, zone image %d bytes, rawfiles %s" % (
            args.inspect, len(data), len(zone), {k: len(v) for k, v in rf.items()}))
        if FONTLIB in rf:
            for c, b, _l in gf.read_movie(rf[FONTLIB])[1]:
                if c == gf.T_DEFINEFONT3:
                    f = gf.Font3.parse(b)
                    print("   %-20s flags %#04x  %5d glyphs" % (f.display_name, f.flags, len(f.codes)))
        return

    zone_name = args.zone or os.path.splitext(os.path.basename(args.out))[0]
    src, stock = stock_library()
    print("stock %s from %s: %d bytes" % (FONTLIB, src, len(stock)))
    lib = build_library(stock, args)
    if args.library_out:
        with open(args.library_out, "wb") as f:
            f.write(lib)
    zone = build_zone(zone_name, [(bf.T_RAWFILE, pack_rawfile_z(FONTLIB, lib))])
    print(bf.check_with_alpha0022(zone, args.exe))
    ff = wrap(zone, args.exe)
    back = unwrap(ff, args.exe)
    if back != zone or rawfiles(back).get(FONTLIB) != lib:
        raise AssertionError("container does not round-trip")
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "wb") as f:
        f.write(ff)
    print("wrote %s: zone '%s', library %d bytes, file %d bytes%s" % (
        args.out, zone_name, len(lib), len(ff),
        "" if len(ff) <= bf.READ_CHUNK else
        " (over 0x40000: needs the patch folder's large-zone support)"))
    if args.preview:
        print("preview:", preview(stock, lib, args.preview))


if __name__ == "__main__":
    main()
