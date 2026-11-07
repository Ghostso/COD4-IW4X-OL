"""CODOL zone-to-IFS mapping (READ-ONLY).

Maps every zone name the engine requests (per static analysis) to:
  - its .ifs container on disk (SHA-256 + size)
  - whether it exists in sandbox main\\
  - confidence level (verified/pattern/candidate)

Uses:  arch_zone_requests.csv  +  CODOLServer/_mainline/ifs_zone_audit.py
No game run, no memory write, no file modification.
"""
import hashlib
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
GAMEDIR = os.path.join(ROOT, "COD OL")
IFSDIR = os.path.join(GAMEDIR, "IIPS", "IIPSDownload")
MAIN = os.path.join(ROOT, "run_codol_001", "sandbox_ifs1_20260923", "main")
AUDIT = os.path.join(ROOT, "CODOLServer", "_mainline", "ifs_zone_audit.py")


def load_zone_requests():
    """Read arch_zone_requests.csv, return zone-shaped names with confidence."""
    path = os.path.join(ROOT, "arch_zone_requests.csv")
    out = {}
    with open(path, "r", encoding="utf-8") as f:
        header = next(f).rstrip("\n").split("|")
        has_conf = len(header) >= 8
        for line in f:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            parts = line.split("|")
            if len(parts) < 7:
                continue
            if has_conf:
                name, sva, iva, kind, func, member, zl, conf = parts[:8]
            else:
                name, sva, iva, kind, func, member, zl = parts[:7]
                # infer confidence from func address
                fva = int(func, 16)
                if fva in {0x4FCC00, 0x4FCCA0, 0x4FCD50, 0x49E410}:
                    conf = "verified"
                elif fva in {0x49E600, 0x4FE830}:
                    conf = "pattern"
                else:
                    conf = "candidate"
            if zl == "zone":
                out[name] = (conf, int(func, 16))
    return out


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main(argv=None):
    # 1) load requested zones with confidence
    req = load_zone_requests()
    if not req:
        print("run _zone_enum.py enq first")
        return 2

    # 2) existing main\ files
    have = set()
    if os.path.isdir(MAIN):
        for n in os.listdir(MAIN):
            if n.lower().endswith(".ff"):
                have.add(n[:-3].lower())

    # 3) scan known .ifs containers (base + marketplace; others are DLC)
    known_ifs = [
        "ff_init_common_gfx_V109.ifs",
        "ff_init_common_marketplace_V95.ifs",
    ]
    print("scanning known .ifs containers...")
    container_of = {}    # zone_name -> {path, size, sha256, meta}
    for n in known_ifs:
        p = os.path.join(IFSDIR, n)
        if not os.path.isfile(p):
            print("  missing: %s" % n)
            continue
        try:
            res = subprocess.run(
                [sys.executable, "-X", "utf8", AUDIT, p, MAIN, "--json"],
                capture_output=True, text=True, timeout=15, check=True)
            rpt = json.loads(res.stdout)
            for z in rpt["zones"]:
                if z["name"]:
                    key = z["name"].lower()
                    if key.endswith(".ff"):
                        key = key[:-3]
                    container_of[key] = {
                        "container": n,
                        "container_sha256": z["sha256"].upper(),
                        "container_size": z["size"],
                        "meta": z["metadata"],
                    }
            print("  %s: %d zones" % (n, rpt["zone_count"]))
        except Exception as e:
            print("  skip %s: %s" % (n, e))

    # 4) produce mapping
    rows = []
    for name, (conf, fva) in sorted(req.items()):
        in_main = name in have
        cinfo = container_of.get(name)
        rows.append({
            "zone": name,
            "confidence": conf,
            "in_main": in_main,
            "func_va": "0x%08X" % fva,
            "container": cinfo["container"] if cinfo else None,
            "container_sha256": cinfo["container_sha256"] if cinfo else None,
            "container_size": cinfo["container_size"] if cinfo else None,
            "meta": cinfo["meta"] if cinfo else None,
        })

    out = os.path.join(ROOT, "arch_zone_ifs_map.csv")
    with open(out, "w", encoding="utf-8", newline="") as f:
        f.write("zone|confidence|in_main|func_va|container|container_sha256|container_size|meta\n")
        for r in rows:
            f.write("%s|%s|%s|%s|%s|%s|%s|%s\n" %
                    (r["zone"], r["confidence"], r["in_main"], r["func_va"],
                     r["container"] or "", r["container_sha256"] or "",
                     r["container_size"] or "", r["meta"] or ""))

    print("wrote %s (%d rows)" % (out, len(rows)))

    # summary
    missing = [r for r in rows if not r["in_main"]]
    print("\n=== MISSING from main\\ (%d) ===" % len(missing))
    for r in missing:
        c = r["container"] or "???"
        print("  %-42s  conf=%-9s  in_ifs=%-45s  size=%-10s" %
              (r["zone"], r["confidence"], c, r["container_size"]))

    present = [r for r in rows if r["in_main"]]
    print("\n=== PRESENT in main\\ (%d) ===" % len(present))
    for r in present:
        c = r["container"] or "???"
        print("  %-42s  conf=%-9s  in_ifs=%-45s  size=%-10s" %
              (r["zone"], r["confidence"], c, r["container_size"]))

    not_in_any = [r for r in rows if r["container"] is None]
    if not_in_any:
        print("\n=== NOT FOUND IN ANY .ifs (%d) ===" % len(not_in_any))
        for r in not_in_any:
            print("  %s" % r["zone"])

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))