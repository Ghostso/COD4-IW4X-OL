# -*- coding: utf-8 -*-
"""Enumerate every network-API call site in the target DLL via the fixed
.idata2 IAT, and every LoadLibrary/GetProcAddress dynamic-resolution site.
Read-only."""
import sys, os, json, struct, re, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dll_common as C
import pefile

# ---- 1. resolve all .idata2 slots to names/ordinals ----
imp = pefile.PE(data=C._b, fast_load=False)
slots = {}   # slot_rva -> (kind, name)
for entry in imp.DIRECTORY_ENTRY_IMPORT:
    dll = entry.dll.decode('latin1')
    for im in entry.imports:
        nm = (im.name.decode('latin1') if im.name else "ord_%d" % im.ordinal)
        if im.address is not None:
            slots[im.address - C.IB] = (dll, nm, 'NAME' if im.name else 'ORDINAL', im.ordinal)
print("total import slots:", len(slots))

# ---- 2. every FF15 call site, map slot -> api ----
ff = C.scan_ff15()
def slot_of(ins):
    m = re.search(r"\[(0x[0-9a-f]+)\]", ins.op_str)
    return (int(m.group(1),16)-C.IB) if m else None

rows = []
for ins in ff:
    sr = slot_of(ins)
    if sr is None: continue
    dll, nm, kind, ordinal = slots.get(sr, ("?", "?", "?", None))
    rows.append((ins.address-C.IB, sr, dll, nm, kind, ordinal))
print("FF15 call sites:", len(rows))

# ---- 3. classify by section/owner ----
# regions identified in prior tasks: libcurl ~0x42xxxx/0x43xxxx, OpenSSL ~0x2Dxxxx,
# ping cluster ~0x235xxx, libcef-ish, etc. We'll just record raw and section.
out = ["RVA\tSLOT_RVA\tDLL\tAPI\tKIND\tORDINAL\tSECTION"]
for rva, sr, dll, nm, kind, ordinal in sorted(rows):
    out.append("%08x\t%08x\t%s\t%s\t%s\t%s\t%s" % (
        rva, sr, dll, nm, kind, (ordinal if ordinal is not None else ""), C.sec_of_rva(rva)))
open(os.path.join(C.EV,"all_ff15_import_calls.tsv"),"w",encoding="utf-8",newline="").write("\n".join(out)+"\n")

# ---- 4. network-related subset ----
NET_DLLS = {"WS2_32.dll","WSOCK32.dll","ws2_32.dll","wsock32.dll"}
netrows = [r for r in rows if r[2] in NET_DLLS]
print("network-API call sites:", len(netrows))
cnt = collections.Counter(r[3] for r in netrows)
for k,v in cnt.most_common():
    print("   %-28s %d" % (k, v))

json.dump({"ff15_total":len(rows),"net_total":len(netrows),
           "net_api_counts":dict(cnt)},
          open(os.path.join(C.EV,"network_api_counts.json"),"w"), indent=2)
print("wrote all_ff15_import_calls.tsv + network_api_counts.json")
