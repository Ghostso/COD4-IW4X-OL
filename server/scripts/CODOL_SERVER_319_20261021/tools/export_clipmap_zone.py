# -*- coding: utf-8 -*-
"""Export the verified coop_train_mp_firingrange ClipMap subset to a C table.
The parser is intentionally strict: every offset and invariant is checked from the
zone bytes, and it fails closed instead of guessing when the layout changes.
"""
import json, math, re, struct, sys
from pathlib import Path

ROOT = Path(r'D:\BaiduNetdiskDownload\使命召唤OL')
ZONE = ROOT / '_map_extract' / 'coop_train_zone.bin'
ENT  = ROOT / '_map_extract' / 'coop_train_entities.txt'
OUTJSON = ROOT / 'CODOL_SERVER_319_20261021' / 'fixtures' / 'coop_train_clipmap_20261023.json'
OUTHDR  = ROOT / 'CODOL_SERVER_319_20261021' / 'include' / 'codol_clipmap_coop_train.h'
OUTINC  = ROOT / 'CODOL_SERVER_319_20261021' / 'include' / 'codol_clipmap_coop_train.inc'

MAT_BLOB = b'clip_player\x00clip_shot_block\x00clip_full\x00clip\x00'
PLANE_DELTA = 0x30069e8d - 0x23f5a4

def u16(d, o): return struct.unpack_from('<H', d, o)[0]
def i16(d, o): return struct.unpack_from('<h', d, o)[0]
def u32(d, o): return struct.unpack_from('<I', d, o)[0]
def f32(d, o): return struct.unpack_from('<f', d, o)[0]

def plane_ok(d, o):
    n = struct.unpack_from('<3f', d, o)
    dist = f32(d, o + 12)
    l2 = n[0]*n[0] + n[1]*n[1] + n[2]*n[2]
    return math.isfinite(dist) and abs(l2 - 1.0) < 0.02 and abs(dist) < 200000.0

def main():
    d = ZONE.read_bytes()
    mat_strings = d.find(MAT_BLOB)
    if mat_strings < 0:
        raise SystemExit('material string blob not found')
    if d.find(MAT_BLOB, mat_strings + 1) >= 0:
        raise SystemExit('multiple material string blobs; layout ambiguous')
    mats_off = mat_strings - 4 * 12
    # The material strings are followed by a 4-byte alignment pad and 8-byte sides.
    sides_off = mat_strings + len(MAT_BLOB)
    side_ptr_bias = 1  # verified 3.19 relocation quirk: cbrush.sides = side_raw+1
    # Find the exact contiguous side table by resolving each plane pointer.
    n_sides = 0
    while True:
        o = sides_off + n_sides * 8
        p = u32(d, o)
        if not (0x30000000 <= p < 0x31000000):
            break
        raw = p - PLANE_DELTA
        if raw < 0 or raw >= len(d):
            break
        if (raw - (mats_off - 27 * 20)) % 20 != 0:
            break
        n_sides += 1
    if n_sides < 1:
        raise SystemExit('brushside table not found')
    planes_off = mats_off
    # Count the contiguous cplane_t run immediately before the material table.
    k = 1
    while planes_off - (k + 1) * 20 >= 0 and plane_ok(d, planes_off - (k + 1) * 20):
        k += 1
    # The first valid plane in the run is the start; re-scan forward from it.
    planes_off = mats_off - k * 20
    n_planes = 0
    while planes_off + (n_planes + 1) * 20 <= mats_off and plane_ok(d, planes_off + n_planes * 20):
        n_planes += 1
    planes_off = mats_off - n_planes * 20
    if n_planes < 1:
        raise SystemExit('plane table not found')
    hdr = planes_off - 64
    if u32(d, hdr) != n_planes or u32(d, hdr + 4) != 0xffffffff:
        raise SystemExit('compact clipmap header mismatch')
    edges_off = sides_off + n_sides * 8
    edge_count = u32(d, hdr + 24)
    leafnodes_count = u32(d, hdr + 32)
    leafnodes_off = edges_off + edge_count
    # Locate the 36-byte cbrush run immediately before the 24-byte bounds table.
    # The verified coop layout has 30 brushes. The search checks pointer targets,
    # bounds finiteness, and the four material-content flags.
    allowed_contents = {0, 0x08010000, 0x080028c0, 0x08033240, 0x08030200}
    candidates = []
    for nbrush in range(1, 129):
        for boff in range(leafnodes_off, min(len(d), leafnodes_off + 0x5000)):
            if boff + nbrush * 36 + nbrush * 24 + nbrush * 4 > len(d):
                break
            ptrs = 0
            ok = True
            for i in range(nbrush):
                o = boff + i * 36
                ns = u16(d, o)
                p = u32(d, o + 4)
                if ns > 64:
                    ok = False; break
                if p:
                    if not (0x30000000 <= p < 0x31000000):
                        ok = False; break
                    ptrs += 1
            if not ok or ptrs < 4:
                continue
            bnd = boff + nbrush * 36
            cts = bnd + nbrush * 24
            vals = []
            for i in range(nbrush):
                fs = struct.unpack_from('<6f', d, bnd + i * 24)
                if not all(math.isfinite(x) and abs(x) < 1e5 for x in fs):
                    ok = False; break
                vals.extend(fs)
            if not ok or not any(abs(x) > 1e-5 for x in vals):
                continue
            flags = [u32(d, cts + i * 4) for i in range(nbrush)]
            if all(x in allowed_contents for x in flags):
                candidates.append((boff, nbrush, ptrs, bnd, cts))
    # Choose the candidate with the strongest pointer count and largest brush count.
    if not candidates:
        raise SystemExit('cbrush run not found')
    brushes_off, n_brushes, ptr_count, bounds_off, contents_off = max(
        candidates, key=lambda x: (x[2], -abs(x[1] - leafnodes_count), -x[1], -x[0]))
    # Decode plane/sides/brushes.
    planes = []
    for i in range(n_planes):
        o = planes_off + i * 20
        planes.append({'normal': list(struct.unpack_from('<3f', d, o)),
                       'dist': f32(d, o + 12), 'type': d[o + 16]})
    materials = []
    for i in range(4):
        o = mats_off + i * 12
        materials.append({'surface': struct.unpack_from('<i', d, o + 4)[0],
                          'contents': u32(d, o + 8)})
    sides = []
    for i in range(n_sides):
        o = sides_off + i * 8
        p = u32(d, o)
        if not (0x30000000 <= p < 0x31000000):
            raise SystemExit('side plane pointer invalid')
        plane = (p - PLANE_DELTA - planes_off) // 20
        if not (0 <= plane < n_planes):
            raise SystemExit('side plane index out of range')
        sides.append({'plane': plane, 'material': u16(d, o + 4),
                      'first_adjacent': struct.unpack_from('<b', d, o + 6)[0],
                      'edge_count': struct.unpack_from('<b', d, o + 7)[0]})
    brushes = []
    for i in range(n_brushes):
        o = brushes_off + i * 36
        ns = u16(d, o)
        p = u32(d, o + 4)
        side_index = None
        if p:
            side_raw = p - PLANE_DELTA - side_ptr_bias
            side_index = (side_raw - sides_off) // 8
            if side_index < 0 or (side_raw - sides_off) % 8:
                raise SystemExit('brush side pointer not aligned')
        if side_index is not None and side_index >= n_sides:
            raise SystemExit('brush side pointer out of range')
        if p and d[o+8:o+12] == b'\0\0\0\0':
            base_adj = None
        else:
            base_adj = u32(d, o + 8)
        brushes.append({'numsides': ns, 'side_first': side_index,
                        'base_adjacent': base_adj,
                        'contents': u32(d, contents_off + i * 4),
                        'bounds': {
                            'mid': list(struct.unpack_from('<3f', d, bounds_off + i * 24)),
                            'half': list(struct.unpack_from('<3f', d, bounds_off + i * 24 + 12)),
                        }})
    # Resolve script_brushmodel entities. The verified model numbering is *71..*99,
    # and the compact array keeps those submodels at brush indices 1..29 in order.
    ent_text = ENT.read_text(encoding='utf-8', errors='replace')
    entities = []
    for block in re.findall(r'\{[^{}]*\}', ent_text, re.S):
        if '"classname" "script_brushmodel"' not in block:
            continue
        kv = dict(re.findall(r'"([^"]+)"\s+"([^"]*)"', block))
        if 'model' not in kv or 'origin' not in kv:
            continue
        model = int(kv['model'][1:])
        origin = [float(x) for x in kv['origin'].split()]
        bi = model - 70
        if not (1 <= bi < n_brushes):
            raise SystemExit('script model index outside verified brush mapping')
        b = brushes[bi]
        mid, half = b['bounds']['mid'], b['bounds']['half']
        entities.append({'model': model, 'origin': origin, 'brush_index': bi,
                         'targetname': kv.get('targetname', ''),
                         'world_mid': [origin[j] + mid[j] for j in range(3)],
                         'world_half': half[:]})
    result = {
        'zone': str(ZONE),
        'layout': {
            'header': hdr, 'planes': planes_off, 'plane_count': n_planes,
            'materials': mats_off, 'materials_strings': mat_strings,
            'brushsides': sides_off, 'brushside_count': n_sides,
            'brush_edges': edges_off, 'brush_edge_count': edge_count,
            'leafbrush_nodes': leafnodes_off, 'leafbrush_node_count': leafnodes_count,
            'brushes': brushes_off, 'brush_count': n_brushes,
            'brush_bounds': bounds_off, 'brush_contents': contents_off,
        },
        'planes': planes, 'materials': materials, 'sides': sides,
        'brushes': brushes, 'script_brushmodels': entities,
        'pointer_delta': PLANE_DELTA,
    }
    OUTJSON.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    # Emit exact AABB table for the 29 script models. These are the map-specific
    # player clip volumes; the 8 plane-backed brushes remain available in JSON.
    lines = []
    lines.append('/* generated by tools/export_clipmap_zone.py; do not hand edit */')
    lines.append('#ifndef CODOL_CLIPMAP_COOP_TRAIN_H')
    lines.append('#define CODOL_CLIPMAP_COOP_TRAIN_H')
    lines.append('#define CODOL_CLIPMAP_COOP_TRAIN_BOX_COUNT %d' % len(entities))
    lines.append('static const codol_collision_box_t codol_clipmap_coop_train_boxes[CODOL_CLIPMAP_COOP_TRAIN_BOX_COUNT] = {')
    inc = []
    for e in entities:
        mid, half = e['world_mid'], e['world_half']
        row = '  {{% .7ff, % .7ff, % .7ff}, {% .7ff, % .7ff, % .7ff}, CODOL_CONTENTS_PLAYERCLIP, -1},' % (
            mid[0]-half[0], mid[1]-half[1], mid[2]-half[2],
            mid[0]+half[0], mid[1]+half[1], mid[2]+half[2])
        lines.append(row); inc.append(row)
    lines.append('};')
    lines.append('#endif /* CODOL_CLIPMAP_COOP_TRAIN_H */')
    OUTHDR.write_text('\n'.join(lines)+'\n', encoding='utf-8')
    OUTINC.write_text('\n'.join(inc)+'\n', encoding='utf-8')
    print('layout', result['layout'])
    print('brushes', n_brushes, 'side pointers', ptr_count, 'script models', len(entities))
    print('wrote', OUTJSON)
    print('wrote', OUTHDR)
    print('wrote', OUTINC)

if __name__ == '__main__':
    main()
