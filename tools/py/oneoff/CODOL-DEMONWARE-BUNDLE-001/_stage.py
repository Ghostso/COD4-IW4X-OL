# -*- coding: utf-8 -*-
import os, shutil, hashlib, json

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
STAGE = os.path.join(ROOT, "CODOL-DEMONWARE-EVIDENCE-BUNDLE-20261012")
if os.path.isdir(STAGE): shutil.rmtree(STAGE)
os.makedirs(STAGE)

def copy_rel(src_rel, dst_rel=None, max_mb=8):
    src = os.path.join(ROOT, src_rel.replace("/", os.sep))
    if not os.path.isfile(src): return False
    if os.path.getsize(src) > max_mb*1024*1024: return False
    dst = os.path.join(STAGE, (dst_rel or src_rel).replace("/", os.sep))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst); return True

def copy_tree_reports(src_rel, dst_rel, exts=(".md",".txt",".csv",".json"), skip_dirs=("_tools","__pycache__","_work")):
    src = os.path.join(ROOT, src_rel.replace("/", os.sep))
    n=0
    for dp, dn, fn in os.walk(src):
        dn[:] = [d for d in dn if d not in skip_dirs]
        for f in fn:
            if os.path.splitext(f)[1].lower() not in exts: continue
            p = os.path.join(dp, f)
            if os.path.getsize(p) > 8*1024*1024: continue
            rel = os.path.relpath(p, src)
            d = os.path.join(STAGE, dst_rel, rel)
            os.makedirs(os.path.dirname(d), exist_ok=True)
            shutil.copy2(p, d); n+=1
    return n

manifest = []
# 1) consolidated register
shutil.copy2(os.path.join(ROOT,"CODOL-DEMONWARE-BUNDLE-001","00_CONSOLIDATED_QUESTION_REGISTER.md"),
             os.path.join(STAGE,"00_CONSOLIDATED_QUESTION_REGISTER.md"))
shutil.copy2(os.path.join(ROOT,"XVAL-02_IMAGE_INTEGRITY_AND_REGISTER_AUDIT","XVAL02_QUESTION_REGISTER_MIGRATION.csv"),
             os.path.join(STAGE,"00_REGISTER_SOURCE_XVAL02_QUESTION_REGISTER_MIGRATION.csv"))

# 2) E26 / E27 / PEER / KEYFLOW reports + SHA256SUMS
for src, dst in [
    ("E26_SERVER_HANDSHAKE_PEER_CROSSWALK_001", "02_E26_SERVER_HANDSHAKE_PEER_CROSSWALK_001"),
    ("E27_DEMONWARE_SERVER_PEER_DISCOVERY_001", "03_E27_DEMONWARE_SERVER_PEER_DISCOVERY_001"),
    ("CLIENT-DEMONWARE-PEER-REUSE-AUDIT-001",   "04_CLIENT-DEMONWARE-PEER-REUSE-AUDIT-001"),
    ("CLIENT-DEMONWARE-CODEC-KEYFLOW-001",      "05_CLIENT-DEMONWARE-CODEC-KEYFLOW-001"),
]:
    cnt = copy_tree_reports(src, dst)
    print(dst, "->", cnt, "files")

# 3) supporting summaries
SUP = {
 "06_SUMMARY_INDEX/01_LAUNCH_AND_BOOTSTRAP": [
   ("CODOLLauncher/CODOL_LAUNCHER_V1.md",),
   ("CODOL_BOOTSTRAP_REPORT_2026-09-16.md",),
   ("RESTORE_LOCALRM_001/RESTORE_LOCALRM_001_FINAL.md",),
   ("RESTORE_ENGINE_BRIDGE_002/RESTORE_ENGINE_BRIDGE_002_FINAL.md",),
   ("restore003/RESTORE_ENGINE_BRIDGE_003_DECISION.md",),
   ("RESTORE001_DECISION.md",),("RESTORE002_DECISION.md",),
   ("RESTORE003_DECISION.md",),("RESTORE005_DECISION.md",),
 ],
 "06_SUMMARY_INDEX/02_LOBBY_REPRODUCTION": [
   ("DEV-REPRO/REPRODUCTION-BASELINE-LOBBY-001.md",),
   ("CODOLServer/LOBBY_0X85_SEND_PATH_20260930.md",),
 ],
 "06_SUMMARY_INDEX/03_CONFIGSTRING_GAMESTATE": [
   ("E08_CONFIGSTRING_BODY_001/07_E08_VERDICT.md",),
   ("E09_CONFIGSTRING_BLOCKERS_001/07_E09_VERDICT.md",),
   ("E10_CONFIGSTRING_DISPATCH_001/07_E10_VERDICT.md",),
   ("E11_GAMESTATE_SUBFRAME_001/07_E11_VERDICT.md",),
   ("E12_REALTIME_GAMESTATE_CONSUMER_001/07_E12_VERDICT.md",),
   ("E13_RECV_RINGBUFFER_TRACE_001/07_E13_VERDICT.md",),
   ("E14_CROSS_PROJECT_PROTOCOL_AND_NETWORK_001/10_E14_VERDICT.md",),
   ("14_SERVER_KNOWLEDGE_ATLAS_001/07_GAMESTATE_CONFIGSTRING_SNAPSHOT.md",),
 ],
 "06_SUMMARY_INDEX/04_SERVER_PACKET_RECV_SEND": [
   ("E25_HANDSHAKE_RESPONSE_SEND_PATH_001/E25_DOWNSTREAM_QUEUE_SEND_CLOSURE.md",),
   ("E13_RECV_RINGBUFFER_TRACE_001/01_RECV_FUNCTION_IO_INVENTORY.md",),
   ("CODOL_2697_SERVER_STATIC_ANALYSIS_20261011/04_PROTOCOL_PATHS.md",),
 ],
}
for d, items in SUP.items():
    for (rel,) in items:
        if copy_rel(rel, d+"/"+os.path.basename(rel)):
            print("  +", rel)
        else:
            print("  ! skip", rel)

# DEV-BOOKING booking/lobby specs
n = copy_tree_reports("DEV-BOOKING", "06_SUMMARY_INDEX/02_LOBBY_REPRODUCTION/DEV-BOOKING-SPECS", exts=(".md",))
print("DEV-BOOKING specs ->", n)

print("STAGE ready")
