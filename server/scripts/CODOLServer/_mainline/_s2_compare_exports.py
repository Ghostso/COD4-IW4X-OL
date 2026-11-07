# -*- coding: utf-8 -*-
"""S2-B: compare PE exports between the baseline and working iips.dll."""
import sys, json, hashlib
import pefile


def get_exports(path):
    pe = pefile.PE(path, fast_load=True)
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_EXPORT']])
    out = []
    ex = getattr(pe, "DIRECTORY_ENTRY_EXPORT", None)
    if not ex:
        return out
    for s in ex.symbols:
        name = s.name.decode("latin1") if s.name else None
        out.append({"ordinal": s.ordinal, "rva": s.address, "name": name})
    return out


def main():
    a_path, b_path = sys.argv[1], sys.argv[2]
    out_path = sys.argv[3] if len(sys.argv) > 3 else None
    a = get_exports(a_path)
    b = get_exports(b_path)
    rep = {
        "a": {"path": a_path, "count": len(a), "exports": a},
        "b": {"path": b_path, "count": len(b), "exports": b},
    }
    # compare by ordinal (export table identity) and by name
    da = {x["ordinal"]: x for x in a}
    db = {x["ordinal"]: x for x in b}
    ord_diff = []
    for k in sorted(set(da) | set(db)):
        if da.get(k) != db.get(k):
            ord_diff.append({"ordinal": k, "a": da.get(k), "b": db.get(k)})
    rep["ordinal_diffs"] = ord_diff
    rep["ordinal_diff_count"] = len(ord_diff)

    # name-level mapping
    na = {x["name"]: x for x in a if x["name"]}
    nb = {x["name"]: x for x in b if x["name"]}
    name_diff = []
    for k in sorted(set(na) | set(nb)):
        if na.get(k) != nb.get(k):
            name_diff.append({"name": k, "a": na.get(k), "b": nb.get(k)})
    rep["name_diffs"] = name_diff
    rep["name_diff_count"] = len(name_diff)

    txt = json.dumps(rep, indent=1, ensure_ascii=False)
    if out_path:
        open(out_path, "w", encoding="utf-8").write(txt)
    print(json.dumps({k: v for k, v in rep.items() if k not in ("a", "b")}, indent=1, ensure_ascii=False))
    return rep


if __name__ == "__main__":
    main()
