import struct
import os
import hashlib
import json
import math
from collections import Counter


def main():
    p = os.path.join(
        r"D:\BaiduNetdiskDownload\使命召唤OL",
        "run_codol_001", "sandbox_ifs1_20260923",
        "codoMP_client_shipRetail.exe")
    d = open(p, "rb").read()
    out = {}
    out["path"] = os.path.abspath(p)
    out["size"] = len(d)
    out["sha256"] = hashlib.sha256(d).hexdigest().upper()
    pe = struct.unpack_from("<I", d, 0x3C)[0]
    out["pe_off"] = hex(pe)
    out["machine"] = hex(struct.unpack_from("<H", d, pe + 4)[0])
    nsec = struct.unpack_from("<H", d, pe + 6)[0]
    optsz = struct.unpack_from("<H", d, pe + 20)[0]
    opt = pe + 24
    out["magic"] = hex(struct.unpack_from("<H", d, opt)[0])
    out["imagebase"] = hex(struct.unpack_from("<I", d, opt + 28)[0])
    out["entry_rva"] = hex(struct.unpack_from("<I", d, opt + 16)[0])
    out["entry_va"] = hex(struct.unpack_from("<I", d, opt + 28)[0] +
                          struct.unpack_from("<I", d, opt + 16)[0])
    secs = []
    off = opt + optsz
    for i in range(nsec):
        s = d[off + i * 40: off + (i + 1) * 40]
        name = s[:8].rstrip(b"\x00").decode("latin1")
        vsize, vaddr, rsize, raddr = struct.unpack_from("<IIII", s, 8)
        chars = struct.unpack_from("<I", s, 36)[0]
        body = d[raddr:raddr + rsize]
        ent = 0.0
        if body:
            c = Counter(body)
            n = len(body)
            for v in c.values():
                pr = v / n
                ent -= pr * math.log2(pr)
        secs.append({
            "name": name,
            "va": hex(vaddr),
            "vsize": hex(vsize),
            "raw": hex(raddr),
            "rsize": hex(rsize),
            "chars": hex(chars),
            "entropy": round(ent, 4),
            "first32": body[:32].hex(),
        })
    out["sections"] = secs
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
