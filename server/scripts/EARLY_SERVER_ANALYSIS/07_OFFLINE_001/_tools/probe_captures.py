import json, glob, collections, os
d = r"D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Server\lobby\captures"
files = sorted(glob.glob(os.path.join(d,"wiretap-*.jsonl")))
total=0; kinds=collections.Counter(); layers=collections.Counter(); payload_carry=0
for f in files:
    n=0
    for line in open(f, encoding="utf-8"):
        line=line.strip()
        if not line: continue
        n+=1
        try: e=json.loads(line)
        except Exception: continue
        kinds[e.get("kind")]+=1
        layers[e.get("layer")]+=1
        # heuristic: any field whose name suggests raw bytes and has >8 hex-ish chars
        s=json.dumps(e)
        if any(k in s for k in ('"payload"','"hex"','"bytes"','"raw"')): payload_carry+=1
    print(os.path.basename(f), n)
    total+=n
print("TOTAL EVENTS:", total)
print("KINDS:", dict(kinds))
print("LAYERS:", dict(layers))
print("events w/ payload-ish key:", payload_carry)
