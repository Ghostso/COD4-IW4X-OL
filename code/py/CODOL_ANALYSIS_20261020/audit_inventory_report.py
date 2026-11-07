#!/usr/bin/env python3
import csv, json
from collections import Counter, defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"CODOL_ANALYSIS_20261020"
CSV=OUT/"AUDIT_FILE_INVENTORY.csv"
def label(rel, original):
    if rel.startswith("DEV-BOOKING/_lineage021/iw4x-rawfiles/"):
        return "iw4x-assets-second-round"
    if rel.startswith("CODOL-BATTLE-SERVER-IMPLEMENTATION-FOUNDATION-047/"):
        return "codol-server-foundation-047"
    if rel.startswith("CODOL-BATTLE-SERVER-"):
        return "codol-battle-server-audit-evidence"
    return original
def main():
    rows=list(csv.DictReader(CSV.open(encoding="utf-8",newline="")))
    for r in rows: r["object_label_corrected"]=label(r["path"],r["object_label"])
    groups=defaultdict(lambda:[0,0,set()])
    for r in rows:
        g=groups[r["path"].split("/",1)[0]]; g[0]+=1; g[1]+=int(r["size"]); g[2].add(r["sha256"])
    summary={"rows":len(rows),"bytes":sum(int(r["size"]) for r in rows),"unique_hashes":len({r["sha256"] for r in rows}),"empty_hashes":sum(not r["sha256"] for r in rows),"iw4x_paths":sum(r["path"].startswith("DEV-BOOKING/_lineage021/iw4x-rawfiles/") for r in rows),"iw4x_bytes":sum(int(r["size"]) for r in rows if r["path"].startswith("DEV-BOOKING/_lineage021/iw4x-rawfiles/")),"top_dirs":[{"name":k,"files":v[0],"bytes":v[1],"unique":len(v[2])} for k,v in sorted(groups.items(),key=lambda kv:kv[1][1],reverse=True)],"labels":[{"label":k,"files":v} for k,v in Counter(r["object_label_corrected"] for r in rows).most_common()],"extensions":[{"extension":k,"files":v} for k,v in Counter(r["extension"] for r in rows).most_common(80)]}
    (OUT/"AUDIT_FIRST_ROUND_REPORT.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    with (OUT/"AUDIT_FIRST_ROUND_CLASSIFIED.csv").open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print(json.dumps({k:summary[k] for k in ["rows","bytes","unique_hashes","empty_hashes","iw4x_paths","iw4x_bytes"]},ensure_ascii=False,indent=2))
if __name__=="__main__": main()
