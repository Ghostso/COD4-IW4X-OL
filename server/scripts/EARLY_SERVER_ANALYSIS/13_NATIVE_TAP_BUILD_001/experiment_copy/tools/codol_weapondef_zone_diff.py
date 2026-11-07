#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""codol_weapondef_zone_diff.py -- offline WeaponDef / weaponattach evidence.

Every CoDOL type-28 (weapon) asset carries the runtime WeaponDef verbatim in
blob[0:0xBFC], with the internal name at +0xBFC (the 0xBFC is BG_BuildCustom-
WeaponDef's own ``rep movsd`` copy size, C1 0x004216C4).  Type-43
(weaponattach) assets carry {offset,type,value} override records that C1 applies
to that copy.  This script reads both straight out of the shipped fastfiles, so
a claim about "what the client's bg_weaponDefs holds" can be checked without a
running C1.

Usage:

    python tools/codol_weapondef_zone_diff.py def cheytac_mp [zone ...]
        Print the pmove/sway fields of every definition of that weapon in each
        zone, so the zones can be diffed against each other and against a live
        read.  Default zones: common_gametype_mp patch_common_gametype_mp
        ui_viewer_mp.

    python tools/codol_weapondef_zone_diff.py dump cheytac_mp [--from ZONE] \
            [--start 0x600] [--end 0x760]
        Hex/float window of the serialized definition.

    python tools/codol_weapondef_zone_diff.py attach 0x670,0x674 [zone ...]
        Every weaponattach override that writes those WeaponDef offsets.

    python tools/codol_weapondef_zone_diff.py compose "*a 11 11 69 20 ..." \
            [--base cheytac_mp]
        Resolve the composed name the way the server does (mp/coWeapon-
        AttachmentTable.csv + mp/coMarketplaceItems.csv), then print every
        override each resolved attachment applies, marking the ones that land
        on a pmove field.

    python tools/codol_weapondef_zone_diff.py table mp/coWeaponAttachmentTable.csv

Needs the alpha0022 fastfile reader (zone_assets.py); point CODOL_ALPHA0022 at
its directory if it is not at the default path.
"""
from __future__ import annotations

import argparse
import os
import struct
import sys

DEFAULT_ALPHA = (r"D:\CoD\CODOL Builds\Call of Duty Online 1.1.1.13\CODOL"
                 r"\1.1.1.13_server\alpha0022")
sys.path.insert(0, os.environ.get("CODOL_ALPHA0022", DEFAULT_ALPHA))
import zone_assets as za  # noqa: E402

WEAPON_ZONES = ("common_gametype_mp", "patch_common_gametype_mp", "ui_viewer_mp")
DEF_SIZE = 0xBFC

# Offsets this server's pmove / sway / breath code consumes, with the C1 reader
# that proves the role.  'f' float, 'I' dword, 'B' byte.
FIELDS = [
    (0x670, "f", "moveSpeedScale      (PM_CmdScale 0x41023f, bob 0x413734)"),
    (0x674, "f", "adsMoveSpeedScale   (PM_CmdScale 0x410266, bob 0x413749)"),
    (0x678, "f", "sprintDurationScale (BG_GetMaxSprintTime 0x40e9e6)"),
    (0x694, "I", "overlayReticle      (BG_CanHoldBreath 0x421f00, sway select)"),
    (0x6ec, "f", "adsSwayMaxAngle"),
    (0x6f0, "f", "hipSwayMaxAngle"),
    (0x6f4, "f", "adsSwaySpeed"),
    (0x6f8, "f", "hipSwaySpeed"),
    (0x6fc, "f", "swayCrouchScale"),
    (0x700, "f", "swayProneScale"),
    (0x704, "f", "(+0x704 -- NOT a sway field)"),
    (0x708, "f", "(+0x708 -- NOT a sway field)"),
    (0x714, "f", "adsSteadySwayDelay  (BG_GetAdsSteadySwayAngle 0x422e20)"),
    (0x718, "f", "adsSteadySwayRamp   (BG_GetAdsSteadySwayAngle 0x422e20)"),
    (0xbc3, "B", "crosshairColourGate"),
    (0xbc8, "B", "aimDownSight"),
]

PMOVE_OFFSETS = {0x670: "moveSpeedScale", 0x674: "adsMoveSpeedScale",
                 0x678: "sprintDurationScale", 0x694: "overlayReticle"}


# ---------------------------------------------------------------- primitives
def u32(b, off):
    return struct.unpack_from("<I", b, off)[0]


def f32(b, off):
    return struct.unpack_from("<f", b, off)[0]


def weapon_name(blob):
    if len(blob) <= DEF_SIZE:
        return None
    end = blob.find(b"\0", DEF_SIZE)
    if end < 0:
        return None
    return blob[DEF_SIZE:end].decode("latin1")


def weapon_defs(zone, want=None):
    """-> [(Asset, blob, internal name)] for every complete type-28 asset."""
    out = []
    for asset in zone.by_type(28):
        blob = asset.blob
        name = weapon_name(blob)
        if name is None:
            continue
        if want is not None and name.lower() != want.lower():
            continue
        out.append((asset, blob, name))
    return out


def read_attachment(blob):
    """C1 0x4c3d00 / codol_asset_registry.c:946.  -> (name, [(off,type,value,text)])."""
    if len(blob) < 12:
        return None
    ref, count, ptr = struct.unpack_from("<3I", blob, 0)
    pos = 12
    if ref == 0xFFFFFFFF:
        end = blob.find(b"\0", pos)
        if end < 0:
            return None
        name = blob[pos:end].decode("latin1")
        pos = end + 1
    else:
        name = "<ref %08x>" % ref
    if not ptr or count > 0xFFFF or pos + 12 * count > len(blob):
        return name, []
    records, pos = pos, pos + 12 * count
    entries = []
    for i in range(count):
        off, typ, val = struct.unpack_from("<3I", blob, records + 12 * i)
        text = None
        if (typ < 16 or typ == 39) and val:
            end = blob.find(b"\0", pos)
            if end < 0:
                return name, entries
            text = blob[pos:end].decode("latin1")
            pos = end + 1
        entries.append((off, typ, val, text))
    return name, entries


def read_stringtable(blob):
    """codol_stringtable.c CODOL_ReadStringTable.  -> (name, cols, rows, cells)."""
    if len(blob) < 17 or u32(blob, 0) != 0xFFFFFFFF:
        return None
    cols, rows = u32(blob, 4), u32(blob, 8)
    pos = 16
    end = blob.find(b"\0", pos)
    if end < 0:
        return None
    name = blob[pos:end].decode("latin1")
    pos = end + 1
    count = cols * rows
    if count > (len(blob) - pos) // 8:
        return None
    records, pos = pos, pos + 8 * count
    cells = []
    for i in range(count):
        ref = u32(blob, records + 8 * i)
        if ref == 0xFFFFFFFF:
            end = blob.find(b"\0", pos)
            if end < 0:
                return None
            cells.append(blob[pos:end].decode("latin1"))
            pos = end + 1
        else:
            cells.append("")
    return name, cols, rows, cells


def norm(name):
    return name.lower().replace("\\", "/")


def find_table(name, zones):
    """Newest zone first, last asset first -- CODOL_LoadEngineStringTable."""
    for spec in zones:
        try:
            zone = za.open_zone(spec)
        except IOError:
            continue
        for asset in reversed(zone.by_type(37)):
            table = read_stringtable(asset.blob)
            if table and norm(table[0]) == norm(name):
                return spec, table
    return None, None


def open_zones(specs):
    zones = []
    for spec in specs:
        try:
            zones.append((spec, za.open_zone(spec)))
        except Exception as exc:                            # noqa: BLE001
            print("%-28s ERROR %s" % (spec, exc))
    return zones


# ------------------------------------------------------------------ commands
def field_line(blob):
    out = []
    for off, fmt, _label in FIELDS:
        if off + 4 > len(blob):
            out.append("%03x=?" % off)
        elif fmt == "f":
            out.append("%03x=%g" % (off, f32(blob, off)))
        elif fmt == "I":
            out.append("%03x=%u" % (off, u32(blob, off)))
        else:
            out.append("%03x=%u" % (off, blob[off]))
    return " ".join(out)


def cmd_def(args):
    zones = args.zone or list(WEAPON_ZONES)
    rows = []
    for spec, zone in open_zones(zones):
        hits = weapon_defs(zone, args.weapon)
        if not hits:
            print("%-28s (no %s)" % (spec, args.weapon))
            continue
        for asset, blob, name in hits:
            line = field_line(blob)
            rows.append(line)
            print("%-28s idx=%-5d size=%-6d %s" % (spec, asset.index, asset.size, line))
    if rows:
        print("")
        print("all zones identical: %s" % ("YES" if len(set(rows)) == 1 else "NO"))
    for off, fmt, label in FIELDS:
        print("    +0x%03x %s" % (off, label))


def cmd_dump(args):
    spec = args.frm or WEAPON_ZONES[0]
    zone = za.open_zone(spec)
    hits = weapon_defs(zone, args.weapon)
    if not hits:
        print("%s: no %s" % (spec, args.weapon))
        return 1
    blob = hits[0][1]
    for off in range(args.start, min(args.end, len(blob) - 15), 16):
        vals = struct.unpack_from("<4f", blob, off)
        ints = struct.unpack_from("<4I", blob, off)
        print("%03x  %-44s %s" % (off, " ".join("%-10.4g" % v for v in vals),
                                  " ".join("%08x" % v for v in ints)))
    return 0


def cmd_attach(args):
    targets = set(int(x, 0) for x in args.offsets.split(","))
    zones = args.zone or list(WEAPON_ZONES)
    total = 0
    for spec, zone in open_zones(zones):
        hits = 0
        for asset in zone.by_type(43):
            parsed = read_attachment(asset.blob)
            if not parsed:
                continue
            name, entries = parsed
            for off, typ, val, text in entries:
                if off in targets:
                    print("%-26s %-32s +0x%03x type %2d %-24r %s"
                          % (spec, name, off, typ, text,
                             PMOVE_OFFSETS.get(off, "")))
                    hits += 1
        print("%-26s %d weaponattach assets, %d hits" % (spec, len(zone.by_type(43)), hits))
        total += hits
    print("total %d" % total)


def cmd_table(args):
    spec, table = find_table(args.name, args.zone or list(WEAPON_ZONES))
    if not table:
        print("no stringtable %s" % args.name)
        return 1
    name, cols, rows, cells = table
    print("### %s from %s: %d cols x %d rows" % (name, spec, cols, rows))
    for r in range(rows):
        print(" | ".join(cells[r * cols:(r + 1) * cols]))
    return 0


def attachment_item_name(index, market_table):
    """codol_weapon_compose.c CODOL_ComposedAttachmentItem / C1 0x41fa2e: the
    item index is the 1-based ordinal of the "wat" rows of
    mp/coMarketplaceItems.csv (0 id, 1 name, 2 type, 3 group)."""
    if not index:
        return None
    _n, cols, rows, cells = market_table
    ordinal = 0
    for r in range(rows):
        row = cells[r * cols:(r + 1) * cols]
        if len(row) < 4 or row[2] != "wat":
            continue
        ordinal += 1
        if ordinal == index:
            return row[1] or None
    return None


def attachment_asset(base, item, attach_table):
    """Last nonempty row for (base, item) -- C1 0x41fc96 overwrite order."""
    _n, cols, rows, cells = attach_table
    for r in range(rows - 1, -1, -1):
        row = cells[r * cols:(r + 1) * cols]
        if len(row) < 3 or row[0] != base or row[1] != item:
            continue
        if row[2]:
            return row[2]
    return None


def cmd_compose(args):
    zones = args.zone or list(WEAPON_ZONES)
    spec, attach_table = find_table("mp/coWeaponAttachmentTable.csv", zones)
    if not attach_table:
        print("mp/coWeaponAttachmentTable.csv not found in %s" % (zones,))
        return 1
    market_spec, market_table = find_table("mp/coMarketplaceItems.csv", zones)
    if not market_table:
        print("mp/coMarketplaceItems.csv not found in %s" % (zones,))
        return 1
    print("attachment table from %s, marketplace from %s" % (spec, market_spec))
    tokens = args.name.split()
    if not tokens or tokens[0] != "*a":
        print("not a composed '*a <base> <flag> [<item> <variant>]*' name")
        return 1
    base = args.base
    items = [int(t) for t in tokens[3::2]]
    print("composed %r -> base %s, items %s" % (args.name, base, items))
    assets = {}
    for item in items:
        name = attachment_item_name(item, market_table)
        asset = attachment_asset(base, name, attach_table) if name else None
        print("  item %-4d %-28s -> %s" % (item, name, asset or "(no row for this weapon)"))
        if asset:
            assets[item] = asset
    blobs = {}
    for spec, zone in open_zones(zones):
        for asset in zone.by_type(43):
            parsed = read_attachment(asset.blob)
            if parsed and parsed[0] not in blobs:
                blobs[parsed[0]] = (spec, parsed[1])
    touched = []
    for item, asset in assets.items():
        found = blobs.get(asset)
        if not found:
            print("  %-28s NOT MOUNTED" % asset)
            continue
        zone_spec, entries = found
        print("  %-28s (%s, %d overrides)" % (asset, zone_spec, len(entries)))
        for off, typ, val, text in entries:
            mark = PMOVE_OFFSETS.get(off)
            if mark:
                touched.append((asset, off, mark, text))
            print("      +0x%03x type %2d value %-12u %-28r %s"
                  % (off, typ, val, text, mark or ""))
    print("")
    if touched:
        print("PMOVE FIELDS OVERRIDDEN BY THIS COMPOSED WEAPON:")
        for asset, off, mark, text in touched:
            print("  %s +0x%03x %s %r" % (asset, off, mark, text))
    else:
        print("no attachment on this composed weapon touches a pmove field;")
        print("the base weapon's own +0x670/+0x674 are what both sides use.")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")

    p = sub.add_parser("def")
    p.add_argument("weapon")
    p.add_argument("zone", nargs="*")
    p.set_defaults(func=cmd_def)

    p = sub.add_parser("dump")
    p.add_argument("weapon")
    p.add_argument("--from", dest="frm")
    p.add_argument("--start", type=lambda s: int(s, 0), default=0x600)
    p.add_argument("--end", type=lambda s: int(s, 0), default=0x760)
    p.set_defaults(func=cmd_dump)

    p = sub.add_parser("attach")
    p.add_argument("offsets")
    p.add_argument("zone", nargs="*")
    p.set_defaults(func=cmd_attach)

    p = sub.add_parser("table")
    p.add_argument("name")
    p.add_argument("zone", nargs="*")
    p.set_defaults(func=cmd_table)

    p = sub.add_parser("compose")
    p.add_argument("name")
    p.add_argument("--base", default="cheytac_mp")
    p.add_argument("zone", nargs="*")
    p.set_defaults(func=cmd_compose)

    args = ap.parse_args(argv)
    if not getattr(args, "func", None):
        ap.print_help()
        return 2
    return args.func(args) or 0


if __name__ == "__main__":
    sys.exit(main())
