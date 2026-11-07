#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
gfx_font.py -- read and rewrite the fonts inside a Scaleform (GFx) font
library such as C1's scaleform/fonts_ingame.gfx.

C1's menus never embed a font.  Every text field names an alias ($font_2 ..
$font_5); the font map C1 builds at 0x006B50B0 sends each alias to a font
in fonts_ingame.gfx (docs/CODOL_ENGLISH_UI.md, "Font").  That movie is an
uncompressed SWF ("GFX" signature) whose fonts are DefineFont3 tags: 20480
units per em, y pointing down, glyph outlines as SWF SHAPE records with
quadratic curves, which is also what TrueType uses.

This module:
  * walks the tags of a GFX/SWF movie and writes a movie back with some tags
    replaced (the header's file length is recomputed);
  * parses and rebuilds DefineFont3 byte-exactly (checked on all four fonts of
    the shipped library);
  * decodes and encodes glyph SHAPE records;
  * converts TrueType glyphs (fontTools) into SHAPE records, scaled to a
    target cap height, with contours reversed to the direction the shipped
    fonts use;
  * renders a string with a DefineFont3 font to a PIL image, for previews.
"""
from __future__ import annotations

import struct
import zlib

EM = 20480                       # DefineFont3 units per em
T_END, T_DEFINEFONT3 = 0, 75


# --- bit streams ------------------------------------------------------------------------------
class BitReader:
    def __init__(self, data, pos):
        self.d, self.p = data, pos * 8

    def ub(self, n):
        v = 0
        for _ in range(n):
            v = (v << 1) | ((self.d[self.p >> 3] >> (7 - (self.p & 7))) & 1)
            self.p += 1
        return v

    def sb(self, n):
        if n == 0:
            return 0
        v = self.ub(n)
        return v - (1 << n) if v & (1 << (n - 1)) else v

    def align(self):
        self.p = (self.p + 7) & ~7

    @property
    def byte(self):
        return self.p >> 3


class BitWriter:
    def __init__(self):
        self.out, self.acc, self.n = bytearray(), 0, 0

    def ub(self, n, v):
        for i in range(n - 1, -1, -1):
            self.acc = (self.acc << 1) | ((v >> i) & 1)
            self.n += 1
            if self.n == 8:
                self.out.append(self.acc)
                self.acc = self.n = 0

    def sb(self, n, v):
        self.ub(n, v & ((1 << n) - 1))

    def getvalue(self):
        if self.n:
            self.out.append(self.acc << (8 - self.n))
            self.acc = self.n = 0
        return bytes(self.out)


def sbits(*vals):
    n = 1
    for v in vals:
        while not -(1 << (n - 1)) <= v < (1 << (n - 1)):
            n += 1
    return n


def read_rect(data, pos):
    r = BitReader(data, pos)
    nb = r.ub(5)
    v = [r.sb(nb) for _ in range(4)]
    r.align()
    return v, r.byte


def write_rect(xmin, xmax, ymin, ymax):
    w = BitWriter()
    nb = sbits(xmin, xmax, ymin, ymax)
    w.ub(5, nb)
    for v in (xmin, xmax, ymin, ymax):
        w.sb(nb, v)
    return w.getvalue()


# --- movie ------------------------------------------------------------------------------------
def read_movie(data):
    """-> (header_bytes_without_length, [(code, body, long_form)]).  Accepts GFX/FWS and CFX/CWS."""
    sig = data[:3]
    if sig in (b"CFX", b"CWS"):
        data = data[:8] + zlib.decompress(data[8:])
        sig = b"GFX" if sig == b"CFX" else b"FWS"
    if sig not in (b"GFX", b"FWS"):
        raise ValueError("not a GFX/SWF movie: %r" % data[:4])
    _rect, p = read_rect(data, 8)
    p += 4                                              # frame rate, frame count
    head = bytes(data[:4]) + bytes(data[8:p])           # signature+version, rect, rate, count
    out = []
    while p < len(data):
        h = struct.unpack_from("<H", data, p)[0]
        p += 2
        code, ln = h >> 6, h & 0x3F
        long_form = ln == 0x3F
        if long_form:
            ln = struct.unpack_from("<I", data, p)[0]
            p += 4
        out.append((code, bytes(data[p:p + ln]), long_form))
        p += ln
        if code == T_END:
            break
    return head, out


def write_movie(head, tags):
    body = bytearray()
    for code, b, long_form in tags:
        if long_form or len(b) >= 0x3F:
            body += struct.pack("<HI", (code << 6) | 0x3F, len(b))
        else:
            body += struct.pack("<H", (code << 6) | len(b))
        body += b
    total = 8 + len(head) - 4 + len(body)
    return head[:4] + struct.pack("<I", total) + head[4:] + bytes(body)


# --- glyph shapes -----------------------------------------------------------------------------
def decode_shape(b):
    """SHAPE -> list of contours [('M',x,y), ('L',x,y) | ('Q',cx,cy,x,y) ...], absolute."""
    r = BitReader(b, 0)
    nf, nl = r.ub(4), r.ub(4)
    x = y = 0
    out, cur = [], None
    while True:
        if r.ub(1) == 0:
            flags = r.ub(5)
            if flags == 0:
                break
            if flags & 0x10:
                raise ValueError("glyph shape declares new styles")
            if flags & 0x01:
                n = r.ub(5)
                x, y = r.sb(n), r.sb(n)
                cur = [("M", x, y)]
                out.append(cur)
            if flags & 0x02:
                r.ub(nf)
            if flags & 0x04:
                r.ub(nf)
            if flags & 0x08:
                r.ub(nl)
        else:
            straight, n = r.ub(1), r.ub(4) + 2
            if straight:
                if r.ub(1):
                    dx, dy = r.sb(n), r.sb(n)
                elif r.ub(1):
                    dx, dy = 0, r.sb(n)
                else:
                    dx, dy = r.sb(n), 0
                x, y = x + dx, y + dy
                cur.append(("L", x, y))
            else:
                cdx, cdy, adx, ady = r.sb(n), r.sb(n), r.sb(n), r.sb(n)
                cx, cy = x + cdx, y + cdy
                x, y = cx + adx, cy + ady
                cur.append(("Q", cx, cy, x, y))
    return out


def encode_shape(contours):
    """Contours (integer, absolute) -> SHAPE with one fill style used as FillStyle0, the way
    the shipped fonts are written (first style change record: FillStyle0=1 + MoveTo)."""
    w = BitWriter()
    w.ub(4, 1)
    w.ub(4, 0)
    first = True
    x = y = 0
    for c in contours:
        _, mx, my = c[0]
        n = sbits(mx, my)
        w.ub(6, 0b000011 if first else 0b000001)       # TypeFlag 0, [FillStyle0], MoveTo
        w.ub(5, n)
        w.sb(n, mx)
        w.sb(n, my)
        if first:
            w.ub(1, 1)
            first = False
        x, y = mx, my
        for e in c[1:]:
            if e[0] == "L":
                dx, dy = e[1] - x, e[2] - y
                if dx == 0 and dy == 0:
                    continue
                n = max(2, sbits(dx, dy))
                w.ub(2, 0b11)
                w.ub(4, n - 2)
                if dx and dy:
                    w.ub(1, 1)
                    w.sb(n, dx)
                    w.sb(n, dy)
                elif dx == 0:
                    w.ub(2, 0b01)
                    w.sb(n, dy)
                else:
                    w.ub(2, 0b00)
                    w.sb(n, dx)
                x, y = e[1], e[2]
            else:
                d = (e[1] - x, e[2] - y, e[3] - e[1], e[4] - e[2])
                if not any(d):
                    continue
                n = max(2, sbits(*d))
                w.ub(2, 0b10)
                w.ub(4, n - 2)
                for v in d:
                    w.sb(n, v)
                x, y = e[3], e[4]
    w.ub(6, 0)
    return w.getvalue()


def transform(contours, sx, sy=None, dx=0, dy=0):
    sy = sx if sy is None else sy
    def P(px, py):
        return int(round(px * sx + dx)), int(round(py * sy + dy))
    out = []
    for c in contours:
        n = []
        for e in c:
            if e[0] == "Q":
                n.append(("Q",) + P(e[1], e[2]) + P(e[3], e[4]))
            else:
                n.append((e[0],) + P(e[1], e[2]))
        out.append(n)
    return out


def reverse_contour(c):
    pts, segs = [(c[0][1], c[0][2])], []
    for e in c[1:]:
        segs.append(e)
        pts.append(e[-2:])
    out = [("M",) + tuple(pts[-1])]
    for i in range(len(segs) - 1, -1, -1):
        e, start = segs[i], pts[i]
        out.append(("L",) + tuple(start) if e[0] == "L" else ("Q", e[1], e[2]) + tuple(start))
    return out


def cap_height(shape):
    ys = [e[-1] for c in decode_shape(shape) for e in c]
    return -min(ys) if ys else 0


# --- DefineFont3 ------------------------------------------------------------------------------
class Font3(object):
    """DefineFont3 with wide codes and layout (every font C1 ships)."""

    @classmethod
    def parse(cls, body):
        f = cls()
        d = body
        f.fid, f.flags, f.lang, nl = struct.unpack_from("<HBBB", d, 0)
        p = 5
        f.name = bytes(d[p:p + nl])
        p += nl
        ng = struct.unpack_from("<H", d, p)[0]
        p += 2
        if not f.flags & 0x04 or not f.flags & 0x80:
            raise ValueError("only DefineFont3 with wide codes and layout is supported")
        base = p
        offs = struct.unpack_from("<%d%s" % (ng + 1, "I" if f.flags & 0x08 else "H"), d, p)
        f.shapes = [bytes(d[base + offs[i]:base + offs[i + 1]]) for i in range(ng)]
        p = base + offs[ng]
        f.codes = list(struct.unpack_from("<%dH" % ng, d, p))
        p += 2 * ng
        f.ascent, f.descent, f.leading = struct.unpack_from("<hhh", d, p)
        p += 6
        f.adv = list(struct.unpack_from("<%dh" % ng, d, p))
        p += 2 * ng
        f.bounds = []
        for _ in range(ng):
            r, p = read_rect(d, p)
            f.bounds.append(r)
        nk = struct.unpack_from("<H", d, p)[0]
        p += 2
        f.kern = [struct.unpack_from("<HHh", d, p + 6 * i) for i in range(nk)]
        p += 6 * nk
        f.tail = bytes(d[p:])
        return f

    @property
    def display_name(self):
        return self.name.rstrip(b"\0").decode("latin-1")

    def index(self, code):
        try:
            return self.codes.index(code)
        except ValueError:
            return None

    def set_glyph(self, code, shape, adv, bounds=(0, 0, 0, 0)):
        i = self.index(code)
        if i is None:
            self.codes.append(code)
            self.shapes.append(shape)
            self.adv.append(adv)
            self.bounds.append(list(bounds))
        else:
            self.shapes[i], self.adv[i], self.bounds[i] = shape, adv, list(bounds)

    def keep_only(self, codes):
        keep = [i for i, c in enumerate(self.codes) if c in codes]
        self.codes = [self.codes[i] for i in keep]
        self.shapes = [self.shapes[i] for i in keep]
        self.adv = [self.adv[i] for i in keep]
        self.bounds = [self.bounds[i] for i in keep]
        self.kern = [k for k in self.kern if k[0] in codes and k[1] in codes]

    def build(self):
        order = sorted(range(len(self.codes)), key=lambda i: self.codes[i])   # CodeTable ascending
        ng = len(order)
        shapes = [self.shapes[i] for i in order]
        size = sum(len(s) for s in shapes)
        wide = 2 * (ng + 1) + size > 0xFFFF
        flags = (self.flags & ~0x08) | (0x08 if wide else 0) | 0x84
        out = bytearray(struct.pack("<HBBB", self.fid, flags, self.lang, len(self.name)))
        out += self.name + struct.pack("<H", ng)
        o = (4 if wide else 2) * (ng + 1)
        offs = []
        for s in shapes:
            offs.append(o)
            o += len(s)
        offs.append(o)
        out += struct.pack("<%d%s" % (ng + 1, "I" if wide else "H"), *offs)
        for s in shapes:
            out += s
        out += struct.pack("<%dH" % ng, *[self.codes[i] for i in order])
        out += struct.pack("<hhh", self.ascent, self.descent, self.leading)
        out += struct.pack("<%dh" % ng, *[self.adv[i] for i in order])
        for i in order:
            out += write_rect(*self.bounds[i])
        out += struct.pack("<H", len(self.kern))
        for k in self.kern:
            out += struct.pack("<HHh", *k)
        return bytes(out + self.tail)


# --- glyph donors -----------------------------------------------------------------------------
class TTFDonor(object):
    """Glyphs from a TrueType/OpenType file (fontTools).  CFF cubics are split into quadratics."""

    def __init__(self, path, variation=None):
        from fontTools.ttLib import TTFont
        self.path = path
        self.font = TTFont(path)
        if variation:
            from fontTools.varLib.instancer import instantiateVariableFont
            self.font = instantiateVariableFont(self.font, variation)
        self.upm = self.font["head"].unitsPerEm
        self.cmap = self.font.getBestCmap()
        self.gs = self.font.getGlyphSet()
        self.hmtx = self.font["hmtx"]

    def has(self, code):
        return code in self.cmap

    def outline(self, code):
        """-> (contours in font units, y up, SWF direction), advance in font units."""
        from fontTools.pens.basePen import BasePen

        class Pen(BasePen):
            def __init__(pen, gs):
                BasePen.__init__(pen, gs)
                pen.cs, pen.cur = [], None

            def _moveTo(pen, p):
                pen.cur = [("M", p[0], p[1])]
                pen.cs.append(pen.cur)

            def _lineTo(pen, p):
                pen.cur.append(("L", p[0], p[1]))

            def _qCurveToOne(pen, c, p):
                pen.cur.append(("Q", c[0], c[1], p[0], p[1]))

            def _curveToOne(pen, c1, c2, p):
                p0 = pen._getCurrentPoint()
                q1 = (p0[0] + 0.75 * (c1[0] - p0[0]), p0[1] + 0.75 * (c1[1] - p0[1]))
                q2 = (p[0] + 0.75 * (c2[0] - p[0]), p[1] + 0.75 * (c2[1] - p[1]))
                m = ((q1[0] + q2[0]) / 2, (q1[1] + q2[1]) / 2)
                pen._qCurveToOne(q1, m)
                pen._qCurveToOne(q2, p)

            def _closePath(pen):
                c = pen.cur
                if c and tuple(c[-1][-2:]) != (c[0][1], c[0][2]):
                    c.append(("L", c[0][1], c[0][2]))

            _endPath = _closePath

        gn = self.cmap[code]
        pen = Pen(self.gs)
        self.gs[gn].draw(pen)
        # y up -> y down flips the winding; reverse to keep the shipped fonts' direction
        cs = [reverse_contour(c) for c in pen.cs if len(c) > 1]
        return cs, self.hmtx[gn][0], self.upm

    def cap_units(self):
        cs, _adv, upm = self.outline(ord("H"))
        return max(e[-1] for c in cs for e in c) * EM / upm


class GFxDonor(object):
    """Glyphs from a DefineFont3 already in the library (e.g. the shipped Agency FB)."""

    def __init__(self, font):
        self.f = font
        self.map = {c: i for i, c in enumerate(font.codes)}

    def has(self, code):
        return code in self.map

    def outline(self, code):
        i = self.map[code]
        cs = [[(e[0],) + tuple(v if k % 2 == 0 else -v for k, v in enumerate(e[1:])) for e in c]
              for c in decode_shape(self.f.shapes[i])]            # y down -> y up, same winding rule
        return cs, self.f.adv[i], EM

    def cap_units(self):
        return cap_height(self.f.shapes[self.map[ord("H")]])


def graft(target, donor, codes, cap_ratio=1.0, track=0):
    """Replace target's glyphs for `codes` with donor's, scaled so the donor's cap height is
    cap_ratio * target's own 'H' cap height.  Advances scale with the outline; `track` adds
    extra spacing per glyph in em/1000.  Returns the scale used."""
    tcap = cap_height(target.shapes[target.index(ord("H"))])
    scale = tcap * cap_ratio / donor.cap_units()                   # font units -> EM units
    n = 0
    for code in codes:
        if not donor.has(code):
            continue
        cs, adv, upm = donor.outline(code)
        s = scale * EM / upm if upm != EM else scale
        cs = transform(cs, s, -s)                                   # y up -> SWF y down
        target.set_glyph(code, encode_shape(cs), int(round(adv * s + track * EM / 1000.0)))
        n += 1
    return scale, n


# --- preview ----------------------------------------------------------------------------------
def render(font, text, px, ss=4):
    """Anti-aliased greyscale PIL image of `text` in `font` at `px` pixels per em (even-odd fill)."""
    from PIL import Image, ImageChops, ImageDraw
    cm = {c: i for i, c in enumerate(font.codes)}
    sc = px * ss / float(EM)
    asc = font.ascent * sc
    h = int((font.ascent + font.descent) * sc) + 2 * ss
    w = int(sum(font.adv[cm[ord(ch)]] for ch in text if ord(ch) in cm) * sc) + 4 * ss
    img = Image.new("1", (max(w, 4), max(h, 4)), 0)
    x0 = 2 * ss
    for ch in text:
        i = cm.get(ord(ch))
        if i is None:
            continue
        for c in decode_shape(font.shapes[i]):
            pts, x, y = [], 0, 0
            for e in c:
                if e[0] == "Q":
                    for k in range(1, 7):
                        t = k / 6.0
                        pts.append(((1 - t) ** 2 * x + 2 * (1 - t) * t * e[1] + t * t * e[3],
                                    (1 - t) ** 2 * y + 2 * (1 - t) * t * e[2] + t * t * e[4]))
                    x, y = e[3], e[4]
                else:
                    x, y = e[1], e[2]
                    pts.append((x, y))
            if len(pts) > 2:
                t = Image.new("1", img.size, 0)
                ImageDraw.Draw(t).polygon([(x0 + a * sc, asc + b * sc + ss) for a, b in pts], fill=1)
                img = ImageChops.logical_xor(img, t)
        x0 += font.adv[i] * sc
    img = img.convert("L")
    return img.resize((img.width // ss, img.height // ss), Image.LANCZOS)
