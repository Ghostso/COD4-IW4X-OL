# -*- coding: utf-8 -*-
"""clipmap_scan.py -- locate cbrush_t / cplane_s / CollisionAabbTree arrays in a zone.

cbrush_t (IW4X AssertSize 36):
  +0  u16 numsides          6..64
  +2  u16 glassPieceIndex   0
  +4  u32 sides             cleared (0xFFFFFFFF)
  +8  u32 baseAdjacentSide  cleared (0xFFFFFFFF)
  +12 u16 axialMaterialNum[2][3]   each < numMaterials
  +24 u8  firstAdjacentSideOffsets[2][3]
  +30 u8  edgeCount[2][3]

cplane_s (20): normal[3] unit, dist, type, pad[3]

CollisionAabbTree (32): mid[3], u16 materialIndex, u16 childCount, half[3], i32 childIndex

Usage: python -X utf8 tools\clipmap_scan.py <zone.bin>
"""
import struct, sys, math

def plane_ok(d, o):
    nx, ny, nz, dist = struct.unpack_from("<4f", d, o)
    l2 = nx*nx + ny*ny + nz*nz
    return math.isfinite(l2) and abs(l2 - 1.0) < 0.02 and abs(dist) < 200000.0

def scan_planes(d, minrun=3):
    N = len(d); runs = []; o = 0
    while o < N - 20:
        if plane_ok(d, o):
            s = o; e = o + 20
            while e < N - 20 and plane_ok(d, e):
                e += 20
            n = (e - s) // 20
            if n >= minrun:
                runs.append((s, n))
            o = e
        else:
            o += 4
    return runs

def brush_ok(d, o, maxmat):
    if o + 36 > len(d):
        return False
    ns, glass = struct.unpack_from("<2H", d, o)
    if not (4 <= ns <= 64) or glass != 0:
        return False
    p1, p2 = struct.unpack_from("<2I", d, o + 4)
    if p1 != 0xFFFFFFFF or p2 != 0xFFFFFFFF:
        return False
    am = struct.unpack_from("<6H", d, o + 12)
    if any(x >= maxmat for x in am):
        return False
    ec = d[o + 30:o + 36]
    if any(x > 64 for x in ec):
        return False
    return True

def scan_brushes(d, maxmat=64):
    N = len(d); hits = []
    for o in range(0, N - 36, 4):
        if brush_ok(d, o, maxmat):
            hits.append(o)
    chains = []; i = 0
    while i < len(hits):
        s = hits[i]; j = i
        while j + 1 < len(hits) and hits[j+1] - hits[j] == 36:
            j += 1
        if j - i + 1 >= 3:
            chains.append((s, j - i + 1))
        i = j + 1
    return hits, chains

def main(path):
    d = open(path, "rb").read()
    print("zone size %d (%#x)" % (len(d), len(d)))

    runs = scan_planes(d, 3)
    runs.sort(key=lambda r: -r[1])
    print("\ncplane runs (>=3):")
    for s, n in runs[:20]:
        nz = sum(1 for i in range(n) if abs(struct.unpack_from("<4f", d, s + i*20)[2]) > 1e-6)
        print("  %#010x  %3d planes  (%d non-horizontal)" % (s, n, nz))

    hits, chains = scan_brushes(d, 64)
    print("\ncbrush_t candidates: %d, chains>=3: %d" % (len(hits), len(chains)))
    for s, n in chains[:20]:
        print("  %#010x  %d brushes  (%d bytes)" % (s, n, n*36))

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else r"D:\BaiduNetdiskDownload\使命召唤OL\_map_extract\coop_train_zone.bin")
