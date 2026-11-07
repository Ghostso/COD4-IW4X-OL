# -*- coding: utf-8 -*-
"""S2-C: byte/section-level diff between original and modified iips.dll."""
import sys, os, struct, json, hashlib
import pefile


def sec_map(pe):
    out = []
    for s in pe.sections:
        out.append({
            "name": s.Name.rstrip(b"\x00").decode("latin1"),
            "rva": s.VirtualAddress,
            "vsize": s.Misc_VirtualSize,
            "raw": s.PointerToRawData,
            "rawsize": s.SizeOfRawData,
        })
    out.sort(key=lambda x: (x["raw"] if x["raw"] else 1 << 32, x["rva"]))
    return out


def main():
    a_path, b_path = sys.argv[1], sys.argv[2]
    out_path = sys.argv[3] if len(sys.argv) > 3 else None
    A = open(a_path, "rb").read()
    B = open(b_path, "rb").read()
    peA = pefile.PE(a_path, fast_load=True)
    peB = pefile.PE(b_path, fast_load=True)

    rep = {
        "a": {"path": a_path, "size": len(A), "sections": sec_map(peA),
              "sha256": hashlib.sha256(A).hexdigest().upper(),
              "imagebase": hex(peA.OPTIONAL_HEADER.ImageBase),
              "ep_rva": hex(peA.OPTIONAL_HEADER.AddressOfEntryPoint),
              "timestamp": peA.FILE_HEADER.TimeDateStamp},
        "b": {"path": b_path, "size": len(B), "sections": sec_map(peB),
              "sha256": hashlib.sha256(B).hexdigest().upper(),
              "imagebase": hex(peB.OPTIONAL_HEADER.ImageBase),
              "ep_rva": hex(peB.OPTIONAL_HEADER.AddressOfEntryPoint),
              "timestamp": peB.FILE_HEADER.TimeDateStamp},
    }
    rep["size_delta"] = len(B) - len(A)
    rep["same_length"] = len(A) == len(B)

    # section table diff
    sa = {s["name"]: s for s in rep["a"]["sections"]}
    sb = {s["name"]: s for s in rep["b"]["sections"]}
    sdiff = []
    for n in sorted(set(sa) | set(sb)):
        x, y = sa.get(n), sb.get(n)
        if x != y:
            sdiff.append({"name": n, "a": x, "b": y})
    rep["section_diffs"] = sdiff

    # byte diff (only if same length, else compare common prefix)
    n = min(len(A), len(B))
    diffs = []
    run = None
    for i in range(n):
        if A[i] != B[i]:
            if run is None:
                run = [i, i]
            else:
                run[1] = i
        else:
            if run is not None:
                diffs.append(tuple(run))
                run = None
    if run is not None:
        diffs.append(tuple(run))
    rep["diff_region_count"] = len(diffs)
    rep["diff_byte_total"] = sum(e - s + 1 for s, e in diffs)

    # classify each run into a section
    def sec_of(off):
        for s in rep["b"]["sections"]:
            if s["raw"] and s["raw"] <= off < s["raw"] + s["rawsize"]:
                return s["name"]
        return "?"

    det = []
    for s, e in diffs[:4000]:
        det.append({
            "off": hex(s), "len": e - s + 1,
            "a_va": hex(off_to_va(peA, s)) if off_to_va(peA, s) is not None else None,
            "b_sec": sec_of(s),
            "a_head": A[s:s + 32].hex(),
            "b_head": B[s:s + 32].hex(),
        })
    rep["diff_runs"] = det

    # if sizes differ, show tail
    if len(A) != len(B):
        rep["extra_tail_a"] = A[n:n + 64].hex()
        rep["extra_tail_b"] = B[n:n + 64].hex()

    txt = json.dumps(rep, indent=1, ensure_ascii=False)
    if out_path:
        open(out_path, "w", encoding="utf-8").write(txt)
    print(json.dumps({k: v for k, v in rep.items() if k != "diff_runs"}, indent=1, ensure_ascii=False))
    print("diff_runs(first 60):")
    print(json.dumps(rep["diff_runs"][:60], indent=1, ensure_ascii=False))


def off_to_va(pe, off):
    for s in pe.sections:
        if s.PointerToRawData <= off < s.PointerToRawData + s.SizeOfRawData:
            return pe.OPTIONAL_HEADER.ImageBase + (off - s.PointerToRawData + s.VirtualAddress)
    return None


if __name__ == "__main__":
    main()
