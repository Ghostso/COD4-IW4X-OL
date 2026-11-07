#!/usr/bin/env python3
"""s137: B12 (V=04/06/08 second layer) + B13 (the x4 scale unit).
Pure static: corpus only.
"""
import json, struct, collections, sys

CORPUS = r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\corpus\corpus.json"
recs = json.load(open(CORPUS, "r", encoding="utf-8"))
if isinstance(recs, dict):
    recs = recs.get("records") or recs.get("data") or list(recs.values())

FIXED = {0x01: 1, 0x03: 1, 0x06: 2, 0x07: 4, 0x08: 4, 0x09: 8, 0x0a: 8}

def blobs(payload):
    out = []; i = 0; n = len(payload)
    while i < n:
        t = payload[i]; i += 1
        if t == 0x00: continue
        if t == 0x10:
            j = payload.find(b"\x00", i)
            if j < 0: break
            i = j + 1; continue
        if t in FIXED: i += FIXED[t]; continue
        if t in (0x13, 0x6b, 0x6c):
            if i >= n or payload[i] != 0x08: break
            i += 1
            if i + 4 > n: break
            ln = struct.unpack_from("<I", payload, i)[0]; i += 4
            data = payload[i:i+ln]; i += ln
            if t in (0x6b, 0x6c): i += 4
            if t == 0x13: out.append(data)
            continue
        break
    return out

def gather(svc, task):
    inner = []
    for r in recs:
        if r.get("svc") == svc and r.get("task") == task:
            for d in blobs(bytes.fromhex(r["payload"])):
                if len(d) >= 4 and struct.unpack_from("<I", d, 0)[0] == len(d) - 4:
                    inner.append(d[4:])
    return inner

def u16(x, o):
    return struct.unpack_from("<H", x, o)[0] if o + 2 <= len(x) else None
def u32(x, o):
    return struct.unpack_from("<I", x, o)[0] if o + 4 <= len(x) else None

def main():
    for (svc, task) in [(11, 4), (6, 14)]:
        inner = gather(svc, task)
        fam = [x for x in inner if x and x[0] == 0x02]
        rd = [x for x in inner if x and x[0] == 0x18]
        print("### svc/task %d/%d : blobs=%d fam02=%d ready18=%d" % (svc, task, len(inner), len(fam), len(rd)))
        print("   byte0 dist:", collections.Counter(x[0] for x in inner).most_common(8))
        print("   byte1 dist:", collections.Counter(x[1] for x in fam if len(x) > 1).most_common())
        for V in (2, 4, 6, 8):
            xs = [x for x in fam if len(x) > 1 and x[1] == V]
            if not xs: continue
            print("  ===== V=0x%02X n=%d distinct=%d =====" % (V, len(xs), len(set(xs))))
            # candidate formula hit rates over ALL samples (not distinct)
            cnt = collections.Counter()
            for x in xs:
                L = len(x); B = L - 10
                A = u32(x, 4); C = u16(x, 8); D5 = u16(x, 5)
                if A == B << 10: cnt["u32==B<<10"] += 1
                if D5 == B * 4: cnt["u16@5==B*4"] += 1
                if A >> 10 == B: cnt["u32>>10==B"] += 1
                if C % 2048 == 0: cnt["u16@8 %2048==0"] += 1
                if A % 1024 == 0: cnt["u32 %1024==0"] += 1
                if C == (A >> 10) << 11: cnt["u16@8==(A>>10)<<11"] += 1
            print("   formula hits:", dict(cnt))
            # raw header bytes 2..10 for distinct
            print("   raw hdr [2:10] + B + u32 + u16@8 + u16@5:")
            for x in sorted(set(xs), key=lambda t: (len(t), t)):
                L = len(x); B = L - 10
                print("     %3d %s | B=%-3d u32=0x%08X u16@8=%-6d u16@5=%-5d u32>>10=%-4d u16@8>>11=%d" % (
                    L, x[2:10].hex(), B, u32(x,4), u16(x,8), u16(x,5), u32(x,4)>>10, u16(x,8)>>11))

if __name__ == "__main__":
    main()
