"""Offline census of the zm/coop map-node link rule (codol_bot_nav.c).

Drives the alpha0022 Python collision oracle (pmove.World: brushes + terrain,
the THIRD stack of memory `three-trace-stacks-disagree`) over the map's own
node_pathnode set (obj/zm-mapents/<map>-mapents.txt) and reports, per
rejection reason, why the T5 Path_CanLinkNodes port rejects a pair.  It is
an oracle for WHY, not a substitute for the native cm walk: the native
server prints the same histogram at load (CoDOL waypoint graph: ... reject
histogram).

usage: python tools/codol_path_link_census.py <map> [--sample N] [--height H]
       [--lift L] [--arrive A] [--drop D] [--mask HEX] [--nodes-only]
"""
import os, sys, re, math, time, random, argparse, collections
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ALPHA = r"D:\CoD\CODOL Builds\Call of Duty Online 1.1.1.13\CODOL\1.1.1.13_server\alpha0022"
sys.path.insert(0, ALPHA)
os.chdir(ALPHA)
import pmove  # noqa: E402

def load_nodes(mapname):
    path = os.path.join(ROOT, "obj", "zm-mapents", mapname + "-mapents.txt")
    text = open(path, encoding="utf-8", errors="replace").read()
    out = []
    for block in re.findall(r"\{(.*?)\}", text, re.S):
        kv = dict(re.findall(r'"([^"]+)"\s+"([^"]*)"', block))
        cls = kv.get("classname", "")
        if not cls.startswith("node_"):
            continue
        if int(kv.get("spawnflags", "0") or 0) & 1:
            continue
        o = [float(v) for v in kv["origin"].split()]
        out.append((cls, o, kv))
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("map")
    ap.add_argument("--sample", type=int, default=60)
    ap.add_argument("--height", type=float, default=72.0)
    ap.add_argument("--lift", type=float, default=18.0)
    ap.add_argument("--arrive", type=float, default=18.0)
    ap.add_argument("--drop", type=float, default=32.0)
    ap.add_argument("--step", type=float, default=8.0)
    ap.add_argument("--mask", type=lambda s: int(s, 16), default=0x2820011)
    ap.add_argument("--nodes-only", action="store_true")
    ap.add_argument("--point", action="store_true", help="floor census with a point trace")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--dropfloor", action="store_true", help="T5 node_droptofloor before linking")
    a = ap.parse_args()
    t0 = time.time()
    w = pmove.World(a.map)
    print("World(%s) built in %.1fs terrain=%s err=%s" % (a.map, time.time() - t0, w.terrain is not None, getattr(w, "terrain_error", None)))
    nodes = load_nodes(a.map)
    print("%d node_* records" % len(nodes))
    mins = (-15.5, -15.5, 0.0); maxs = (15.5, 15.5, a.height)
    if a.dropfloor:
        # T5 node_droptofloor: origin+1 down 256, box actorMins..(30 tall), mask 0x820011,
        # then a stationary actor-box probe at the landing.
        bad_solid = bad_float = bad_land = 0; dropped = collections.Counter(); kept = []
        t0 = time.time()
        for cls, o, kv in nodes:
            s = (o[0], o[1], o[2] + 1.0); e = (o[0], o[1], o[2] - 255.0)
            tr = w.trace(s, e, (-15, -15, 0), (15, 15, 30), 0x820011)
            if tr.startsolid or tr.allsolid: bad_solid += 1; continue
            if tr.fraction >= 1.0: bad_float += 1; continue
            z = s[2] + (e[2] - s[2]) * tr.fraction
            tr = w.trace((o[0], o[1], z), (o[0], o[1], z), (-15, -15, 0), (15, 15, 48), 0x820011)
            if tr.startsolid or tr.allsolid: bad_land += 1; continue
            dropped[int(round(o[2] - z))] += 1
            kept.append((cls, [o[0], o[1], z], kv))
        print("droptofloor (%.1fs): %d kept, %d in solid, %d floating, %d landing in solid; drop histogram %s" % (
            time.time() - t0, len(kept), bad_solid, bad_float, bad_land, sorted(dropped.items())))
        nodes = kept
    # 1. floor census: where is the floor relative to each node origin?
    rel = collections.Counter(); solid = 0; nofloor = 0; contents = collections.Counter(); sfl = collections.Counter()
    t0 = time.time()
    for cls, o, kv in nodes:
        s = (o[0], o[1], o[2] + a.lift); e = (o[0], o[1], o[2] - 128.0)
        tr = w.trace(s, e, (0,0,0) if a.point else mins, (0,0,0) if a.point else maxs, a.mask)
        if tr.startsolid:
            solid += 1; continue
        if tr.fraction >= 1.0:
            nofloor += 1; continue
        fz = s[2] + (e[2] - s[2]) * tr.fraction
        rel[int(round(o[2] - fz))] += 1
        contents[hex(int(getattr(tr, "contents", 0)))] += 1
        sfl[hex(int(getattr(tr, "surface_flags", 0)))] += 1
    print("floor census (%.1fs): start-in-solid %d, no floor within 128 below %d" % (time.time() - t0, solid, nofloor))
    print("  node z minus floor z, histogram:", sorted(rel.items()))
    print("  hit contents:", contents.most_common(8))
    print("  hit surface flags:", sfl.most_common(8))
    if a.nodes_only:
        return
    # 2. walk census on a sample of nodes, every candidate within 256/128.
    random.seed(a.seed)
    idx = list(range(len(nodes)))
    if a.sample and a.sample < len(idx):
        idx = random.sample(idx, a.sample)
    hist = collections.Counter(); hits = collections.Counter(); links = 0; pairs = 0; isolated = 0; all_links = []
    t0 = time.time()
    for i in idx:
        ci, fo, _ = nodes[i]
        out = 0
        for j, (cj, to, _) in enumerate(nodes):
            if i == j: continue
            dx = to[0] - fo[0]; dy = to[1] - fo[1]; dz = to[2] - fo[2]
            if abs(dz) > 128.0: continue
            if dx*dx + dy*dy > 65536.0: continue
            pairs += 1
            reason = walk(w, fo, to, mins, maxs, a, hits)
            hist[reason] += 1
            if reason == "link":
                links += 1; out += 1; all_links.append((i, j))
        # T5 Path_IsNegotiationLink: begin -> its targeted end, unconditionally.
        if ci == "node_negotiation_begin":
            for j, (cj, to, kvj) in enumerate(nodes):
                if cj == "node_negotiation_end" and kvj.get("targetname") == nodes[i][2].get("target"):
                    all_links.append((i, j)); links += 1; out += 1
        if not out: isolated += 1
    print("walk census (%.1fs): %d sampled nodes, %d candidate pairs, %d links, %d sampled nodes isolated" % (time.time() - t0, len(idx), pairs, links, isolated))
    for k, v in hist.most_common():
        print("  %-28s %d" % (k, v))
    print("  forward-hit contents/sflags:", hits.most_common(10))
    if a.sample:
        return
    # 3. component census over the full directed graph (undirected union), and
    #    whether each zombie_spawner (target -> node targetname) and
    #    exterior_goal (nearest node) sits on the main component.
    parent = list(range(len(nodes)))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i
    for x, y in all_links:
        parent[find(x)] = find(y)
    comp = collections.Counter(find(i) for i in range(len(nodes)))
    main, main_size = comp.most_common(1)[0]
    print("components: %d, main %d nodes, %d off it; sizes %s" % (len(comp), main_size, len(nodes) - main_size, sorted(comp.values(), reverse=True)[:12]))
    by_tn = {}
    for k, (cls, o, kv) in enumerate(nodes):
        if "targetname" in kv: by_tn[kv["targetname"]] = k
    text = open(os.path.join(ROOT, "obj", "zm-mapents", a.map + "-mapents.txt"), encoding="utf-8", errors="replace").read()
    sp = sp_off = go = go_off = 0
    for block in re.findall(r"\{(.*?)\}", text, re.S):
        kv = dict(re.findall(r'"([^"]+)"\s+"([^"]*)"', block))
        if kv.get("classname") != "script_struct": continue
        is_sp = kv.get("script_noteworthy") == "zombie_spawner"; is_go = kv.get("targetname") == "exterior_goal"
        if not (is_sp or is_go): continue
        node = by_tn.get(kv.get("target"))
        if node is None:
            o = [float(v) for v in kv["origin"].split()]
            node = min(range(len(nodes)), key=lambda k: (nodes[k][1][0]-o[0])**2 + (nodes[k][1][1]-o[1])**2 + (nodes[k][1][2]-o[2])**2)
        off = find(node) != main
        if is_sp: sp += 1; sp_off += off
        else: go += 1; go_off += off
        if off: print("  OFF MAIN: %s at %s -> node %d (%s)" % ("zombie_spawner" if is_sp else "exterior_goal", kv.get("origin"), node, nodes[node][1]))
    print("zombie_spawner %d (%d off main), exterior_goal %d (%d off main)" % (sp, sp_off, go, go_off))

def walk(w, fo, to, mins, maxs, a, hits):
    dx = to[0] - fo[0]; dy = to[1] - fo[1]; ln = math.hypot(dx, dy)
    if ln < 1.0: return "coincident"
    dx /= ln; dy /= ln
    pos = list(fo); steps = 0
    while steps < 96:
        rx = to[0] - pos[0]; ry = to[1] - pos[1]; remain = math.hypot(rx, ry)
        if remain <= 4.0: break
        adv = min(remain, a.step)
        s = (pos[0], pos[1], pos[2] + a.lift)
        e = (s[0] + dx*adv, s[1] + dy*adv, s[2])
        tr = w.trace(s, e, mins, maxs, a.mask)
        if tr.startsolid or tr.allsolid:
            return "forward startsolid (step %d)" % (0 if steps == 0 else 1)
        if tr.fraction < 1.0:
            hits[(hex(int(getattr(tr, "contents", 0))), hex(int(getattr(tr, "surface_flags", 0))))] += 1
            return "forward hit"
        d = (e[0], e[1], e[2] - a.lift - a.drop)
        tr = w.trace(e, d, mins, maxs, a.mask)
        if tr.startsolid or tr.allsolid: return "down startsolid"
        if tr.fraction >= 1.0: return "no floor within drop"
        pos = [e[0], e[1], e[2] + (d[2] - e[2]) * tr.fraction]
        steps += 1
    if steps >= 96: return "step budget"
    if abs(pos[2] - to[2]) > a.arrive: return "arrival dz > %g" % a.arrive
    return "link"

if __name__ == "__main__":
    main()
