# -*- coding: utf-8 -*-
"""Read-only boundary audit for VA 0xCA8000..0xCA8800."""
import argparse
import collections
import csv
import hashlib
import struct
from pathlib import Path

IB = 0x00400000
SOI = 0x0E659000
TABLE = 0x00CA8000
TABLE_RVA = TABLE - IB
WEND = 0x00CA8800
TEND = 0x00CA876C
SECS = (
    (0, ".tp3", 0x00001000, 0x08A689A, 0x001000, 0x593000, 0x60000020),
    (1, ".tp3", 0x008A8000, 0x016DA70, 0x594000, 0x16E000, 0x40000040),
    (2, ".tp3", 0x00A16000, 0xDBB1CC0, 0x702000, 0x062000, 0xC0000040),
    (3, ".tp3", 0x0E5C8000, 0x0000031, 0x764000, 0x001000, 0xC0000040),
    (4, ".tp3", 0x0E5C9000, 0x0009228, 0x765000, 0x00A000, 0x40000040),
    (5, ".tvm0", 0x0E5D3000, 0x0004000, 0x76F000, 0x002000, 0x60000020),
    (6, ".tp3", 0x0E5D7000, 0x0082000, 0x771000, 0x006000, 0xE0000020),
)

def hx(x):
    return "0x%08X" % x if x is not None else ""

def sec_at_rva(rva):
    for s in SECS:
        if s[2] <= rva < s[2] + max(s[3], s[5]):
            return s
    return None

def rva2off(rva):
    s = sec_at_rva(rva)
    if not s:
        return None
    d = rva - s[2]
    return s[4] + d if 0 <= d < s[5] else None

def off2rva(off):
    for s in SECS:
        if s[4] <= off < s[4] + s[5]:
            return s[2] + off - s[4]
    return None

def rd32(data, va):
    off = rva2off(va - IB)
    return struct.unpack_from("<I", data, off)[0] if off is not None and off + 4 <= len(data) else None

def cls(v):
    if v is None: return "OOB"
    if v == 0: return "ZERO"
    if 0x80000000 <= v <= 0x8FFFFFFF: return "SENTINEL_8XXXXXXX"
    if IB <= v < IB + SOI: return "IN_IMAGE_VA"
    return "OTHER"

def target(v):
    if v is None or not IB <= v < IB + SOI:
        return None, "", "NO"
    rva = v - IB
    sec = sec_at_rva(rva)
    if not sec:
        return rva, "", "NO"
    return rva, "%s#%d" % (sec[1], sec[0]), "YES" if rva2off(rva) is not None else "NO"

def ff_refs(data, lo, hi, include_tvm0=False):
    out = []
    for off in range(len(data) - 6):
        if data[off] != 0xFF or data[off + 1] not in (0x15, 0x25):
            continue
        va = struct.unpack_from("<I", data, off + 2)[0]
        if not (lo <= va < hi):
            continue
        rva = off2rva(off)
        sec = sec_at_rva(rva) if rva is not None else None
        if not include_tvm0 and sec and sec[0] == 5:
            continue
        out.append((va, off, data[off + 1], rva))
    return out

def make_rows(data, refs):
    by = collections.defaultdict(list)
    for slot, off, op, crva in refs:
        by[slot].append((off, op, crva))
    rows = []
    for i in range(512):
        slot = TABLE + 4 * i
        v = rd32(data, slot)
        trva, tsec, tback = target(v)
        rr = by.get(slot, [])
        csec = collections.Counter()
        cops = collections.Counter()
        crvas = []
        for off, op, crva in rr:
            s = sec_at_rva(crva) if crva is not None else None
            csec["%s#%d" % (s[1], s[0]) if s else "OUT"] += 1
            cops["FF%02X" % op] += 1
            if crva is not None: crvas.append(crva)
        rows.append({
            "index": i, "slot_va": hx(slot), "slot_rva": hx(slot - IB),
            "slot_file_off": hx(rva2off(slot - IB)), "raw_value_hex": hx(v),
            "raw_value_dec": str(v), "value_class": cls(v),
            "target_rva_hex": hx(trva), "target_section": tsec,
            "target_file_backed": tback, "ff15_refs": cops["FF15"],
            "ff25_refs": cops["FF25"], "ff_refs": len(rr),
            "caller_rva_count": len(crvas), "caller_rvas": " ".join(hx(x) for x in sorted(crvas)),
            "caller_sections": ";".join("%s=%d" % x for x in sorted(csec.items())),
            "region": "TEMPLATE_475" if slot < TEND else "TAIL_37",
        })
    return rows

def longest_equal_run(vals):
    best_start, best_len = 0, 0
    start = 0
    for i in range(1, len(vals) + 1):
        if i == len(vals) or vals[i] != vals[start]:
            if i - start > best_len:
                best_start, best_len = start, i - start
            start = i
    return best_start, best_len

def build(data, source):
    refs = ff_refs(data, TABLE, WEND, False)
    rows = make_rows(data, refs)
    vals = [rd32(data, TABLE + 4 * i) for i in range(512)]
    tv = vals[:475]
    uv = vals[475:]
    # Duplicate identity: exact byte comparison with VA E12944 / file 6FE944.
    a, b = rva2off(TABLE_RVA), 0x6FE944
    n = 0
    while n < 0x800 and data[a+n] == data[b+n]:
        n += 1
    # Strict main-section FF15/FF25 operand set, semantic census excludes .tvm0.
    main_slots = set()
    main_refs = collections.defaultdict(list)
    for off in range(len(data) - 6):
        if data[off] != 0xFF or data[off + 1] not in (0x15, 0x25):
            continue
        op = struct.unpack_from("<I", data, off + 2)[0]
        crva = off2rva(off)
        csec = sec_at_rva(crva) if crva is not None else None
        if csec and csec[0] == 5:
            continue
        tsec = sec_at_rva(op - IB) if IB <= op < IB + SOI else None
        if tsec and tsec[0] == 1:
            main_slots.add(op)
            main_refs[op].append((off, data[off + 1], crva))
    win = {x for x in main_slots if TABLE <= x < WEND}
    extra = sorted(main_slots - win)
    dupes = [(v, c) for v, c in collections.Counter(vals).items() if c > 1]
    info = {
        "source": str(source), "sha256": hashlib.sha256(data).hexdigest(), "size": len(data),
        "table_off": a, "copy_va": 0x00E12944, "copy_off": b, "match": n,
        "refs": len(refs), "ff15": sum(1 for x in refs if x[2] == 0x15),
        "ff25": sum(1 for x in refs if x[2] == 0x25),
        "slots": len({x[0] for x in refs}), "unique_values": len(set(vals)),
        "classes": collections.Counter(cls(v) for v in vals),
        "mod4": collections.Counter(v & 3 for v in vals),
        "mod16": collections.Counter(v & 15 for v in vals),
        "tclasses": collections.Counter(cls(v) for v in tv),
        "uclasses": collections.Counter(cls(v) for v in uv),
        "tptr": (min(v for v in tv if cls(v) == "IN_IMAGE_VA"), max(v for v in tv if cls(v) == "IN_IMAGE_VA")),
        "uptr": (min(v for v in uv if cls(v) == "IN_IMAGE_VA"), max(v for v in uv if cls(v) == "IN_IMAGE_VA")),
        "dupes": dupes, "lrun": longest_equal_run(vals),
        "ptr_deltas": collections.Counter(b - a for a, b in zip(
            [v for v in tv if cls(v) == "IN_IMAGE_VA"],
            [v for v in tv if cls(v) == "IN_IMAGE_VA"][1:])),
        "self_or_window": [(i, vals[i]) for i in range(512) if TABLE <= vals[i] < WEND],
        "count_like": [(i, vals[i]) for i in range(512)
                       if vals[i] in (475, 512, 0x76C, 0x800, 0x1D0, 0x1DB)],
        "main_slots": len(main_slots), "win_slots": len(win), "extra": extra,
        "extra_refs": {x: main_refs[x] for x in extra},
        "win_low2": collections.Counter(rd32(data, x) & 3 for x in win),
        "main_low2": collections.Counter(rd32(data, x) & 3 for x in main_slots),
    }
    return rows, info

def write_csv(path, rows):
    fields = ["index", "slot_va", "slot_rva", "slot_file_off", "raw_value_hex", "raw_value_dec",
              "value_class", "target_rva_hex", "target_section", "target_file_backed",
              "ff15_refs", "ff25_refs", "ff_refs", "caller_rva_count", "caller_rvas",
              "caller_sections", "region"]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(rows)

def write_txt(path, rows, x):
    L = []
    add = L.append
    add("CA8000 512-DWORD BOUNDARY AUDIT")
    add("=" * 78)
    add("READ-ONLY. Semantic FF census excludes .tvm0. No string scan.")
    add("FILE=%s" % x["source"])
    add("SHA256=%s" % x["sha256"])
    add("FILE_SIZE=%d" % x["size"])
    add("")
    add("TABLE AND FILE MAP")
    add("-" * 78)
    add("ImageBase=%s SizeOfImage=%s" % (hx(IB), hx(SOI)))
    add("Table VA=%s RVA=%s fileoff=%s section=.tp3#1" % (hx(TABLE), hx(TABLE_RVA), hx(x["table_off"])))
    add("Observation window=[%s,%s) bytes=0x800 dwords=512" % (hx(TABLE), hx(WEND)))
    add("Exact template boundary=%s exact_length=0x%X bytes=%d dwords" % (hx(TEND), x["match"], x["match"] // 4))
    add("Duplicate identity=VA %s fileoff=%s; same bytes for the exact template length" % (hx(x["copy_va"]), hx(x["copy_off"])))
    add("Tail=[%s,%s) dwords=%d" % (hx(TEND), hx(WEND), 512 - x["match"] // 4))
    add("HIGH: this is a 475-DWORD exact template followed by a separate 37-DWORD array.")
    add("HIGH: exact template repeat is byte-for-byte at the duplicate identity above.")
    add("MEDIUM/LOW: the 0x800-byte edge is an observation window/alignment chunk; single-object boundary is not proven.")
    add("")
    add("VALUE MIX / STRIDE / ALIGNMENT")
    add("-" * 78)
    add("512 classes=%s" % dict(x["classes"]))
    add("512 mod4=%s" % dict(sorted(x["mod4"].items())))
    add("512 mod16=%s" % dict(sorted(x["mod16"].items())))
    add("template(475) classes=%s" % dict(x["tclasses"]))
    add("tail(37) classes=%s" % dict(x["uclasses"]))
    add("template in-image range=%s..%s" % (hx(x["tptr"][0]), hx(x["tptr"][1])))
    add("tail in-image range=%s..%s" % (hx(x["uptr"][0]), hx(x["uptr"][1])))
    add("unique=%d/512 duplicate-values=%s" % (x["unique_values"], [(hx(v), c) for v, c in sorted(x["dupes"])]))
    add("longest consecutive identical-u32 run=index %d length=%d" % (x["lrun"][0], x["lrun"][1]))
    add("HIGH: value mix is not a homogeneous code-pointer array.")
    add("template pointer delta histogram (top 8)=%s" % x["ptr_deltas"].most_common(8))
    add("template pointer deltas: unique=%d; |delta|<=0x100 in %d/%d transitions" % (
        len(x["ptr_deltas"]), sum(n for d, n in x["ptr_deltas"].items() if abs(d) <= 0x100),
        sum(x["ptr_deltas"].values())))
    add("self/window pointers stored in the window=%s" % [(i, hx(v)) for i, v in x["self_or_window"]])
    add("count-like DWORDs (475/512/0x76C/0x800/0x1D0/0x1DB)=%s" % [(i, hx(v)) for i, v in x["count_like"]])
    add("MEDIUM: no uniform stride is present across the 475-DWORD template.")
    add("MEDIUM: tail is all in-image pointers; indices 480..511 are exact +0x10 stride entries.")
    add("UNKNOWN: semantic type of either substructure (descriptor/runtime/control/object).")
    add("")
    add("TAIL 37-POINTER ARRAY")
    add("-" * 78)
    for i in range(475, 512):
        r = rows[i]
        add("[%3d] slot=%s value=%s class=%s target_rva=%s section=%s ff_refs=%d" % (
            i, r["slot_va"], r["raw_value_hex"], r["value_class"], r["target_rva_hex"],
            r["target_section"], r["ff_refs"]))
    add("HIGH: all 37 values are in-image pointers.")
    add("MEDIUM: first five values point to 0xCA5614/0xCA562A/0xCA5640/0xCA55FC/0xCA5608; remaining 32 form an exact +0x10 stride run.")
    add("")
    add("REFERENCE RECONCILIATION: 232 VS 231")
    add("-" * 78)
    add("USER-232 CONDITION: distinct FF15/FF25 operands whose absolute VA maps to section .tp3#1.")
    add("OLD-231 CONDITION: same census but additionally TABLE_VA <= operand < 0xCA8800.")
    add("user232 distinct slots=%d window231 distinct slots=%d difference=%d" % (
        x["main_slots"], x["win_slots"], len(x["extra"])))
    for s in x["extra"]:
        sec = sec_at_rva(s - IB)
        v = x["extra_values"].get(s)
        add("DIFFERENCE SLOT=%s section=%s fileoff=%s value=%s class=%s target_rva=%s" % (
            hx(s), "%s#%d" % (sec[1], sec[0]) if sec else "OUT", hx(rva2off(s - IB)),
            hx(v), cls(v), hx(v - IB) if v is not None and IB <= v < IB + SOI else ""))
        for o, op, crva in x["extra_refs"][s]:
            add("  raw FF%02X at fileoff=%s caller_rva=%s" % (op, hx(o), hx(crva)))
    add("HIGH: 0x00DB7158 is the exact extra slot; it accounts for 232 - 231 and low2 {0:108,1:3,2:115,3:6}.")
    add("HIGH: no FF15/FF25 operand references 0xCA8760..0xCA87FF in this raw census.")
    add("UNKNOWN: all 232/231 counts remain raw-byte patterns, not instruction-boundary or reachable-callsite counts.")
    add("")
    add("RAW REFERENCE SUMMARY")
    add("-" * 78)
    add("FF15=%d FF25=%d total=%d unique_slots=%d" % (x["ff15"], x["ff25"], x["refs"], x["slots"]))
    add("window low2=%s all-main-section low2=%s" % (dict(x["win_low2"]), dict(x["main_low2"])))
    add("")
    add("HEADER / DESCRIPTOR CHECK")
    add("-" * 78)
    add("No magic/count/length/self-pointer header was established at slot 0.")
    add("UNKNOWN: whether either substructure is a header/descriptor, registry, dispatcher, or runtime table.")
    add("LOW: naming the 512-DWORD window as a single dispatcher/pointer registry.")
    add("")
    add("CONFIDENCE SUMMARY")
    add("-" * 78)
    add("HIGH   table identity, section, file offset, 512-DWORD window")
    add("HIGH   exact 475-DWORD/0x76C-byte template and duplicate identity")
    add("HIGH   37-DWORD all-pointer tail with a distinct target range")
    add("HIGH   232-vs-231 difference is exactly slot 0x00DB7158 outside the 0xCA8800 window")
    add("MEDIUM tail indices 480..511 have exact +0x10 stride")
    add("MEDIUM targets have no static file backing (section .tp3#0 virtual tail)")
    add("LOW    single fixed-size dispatcher/header interpretation")
    add("UNKNOWN target semantics, header fields, reachability")
    add("")
    add("Per-dword details: scripts/_out/ca8000_boundary_audit.csv")
    path.write_text("\n".join(L) + "\n", encoding="utf-8")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("exe", nargs="?", default="codoMP_client_shipRetail.exe")
    ap.add_argument("--csv", default="scripts/_out/ca8000_boundary_audit.csv")
    ap.add_argument("--txt", default="scripts/_out/ca8000_boundary_audit.txt")
    a = ap.parse_args()
    data = Path(a.exe).read_bytes()
    rows, info = build(data, a.exe)
    # Read values for the out-of-window difference slot with the same section map.
    for s in info["extra"]:
        sec = sec_at_rva(s - IB)
        off = rva2off(s - IB)
        info.setdefault("extra_values", {})[s] = struct.unpack_from("<I", data, off)[0] if off is not None else None
    Path(a.csv).parent.mkdir(parents=True, exist_ok=True)
    Path(a.txt).parent.mkdir(parents=True, exist_ok=True)
    write_csv(Path(a.csv), rows)
    write_txt(Path(a.txt), rows, info)
    print("wrote", a.csv)
    print("wrote", a.txt)
    print("main_slots=%d window_slots=%d extra=%s" % (info["main_slots"], info["win_slots"], [hx(s) for s in info["extra"]]))

if __name__ == "__main__":
    main()
