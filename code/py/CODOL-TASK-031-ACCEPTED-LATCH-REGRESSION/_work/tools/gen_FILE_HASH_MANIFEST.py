import os, hashlib, time
ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
OUT  = os.path.join(ROOT, "CODOL-TASK-031-ACCEPTED-LATCH-REGRESSION")
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for c in iter(lambda: f.read(1<<20), b''): h.update(c)
    return h.hexdigest()
rows=[]
rows.append("id\trole\tpath\tsize_bytes\tsha256\tpe_arch\ttimestamp_or_image_size\tversion_association\tevidence_grade\tnotes")
def add(i, role, rel, arch, ts, ver, grade, notes):
    p = rel if os.path.isabs(rel) else os.path.join(ROOT, rel)
    if not os.path.exists(p): rows.append("\t".join([i,role,p,"MISSING","MISSING",arch,ts,ver,"MISSING",notes])); return
    if os.path.isdir(p):
        files=sum(len(fs) for _,_,fs in os.walk(p)); size=sum(os.path.getsize(os.path.join(r,f)) for r,_,fs in os.walk(p) for f in fs)
        rows.append("\t".join([i,role,p,str(size),"DIRECTORY(%d files)"%files,arch,ts,ver,grade,notes])); return
    rows.append("\t".join([i,role,p,str(os.path.getsize(p)),sha(p),arch,ts,ver,grade,notes]))
add("T-01","target client EXE (original)", r"COD OL\codoMP_client_shipRetail.exe","PE32/x86","SizeOfImage 0x0E659000","3.19.26.22 / build 1649370","CONFIRMED","COFF TimeDateStamp = 0x6096930A (2021-05-08T13:32:58Z); size/hash match 009 V-01")
add("T-02","target main engine DLL (original)", r"COD OL\codoMP_client_shipRetailBase.dll","PE32/x86","SizeOfImage 0x3991000","target instance main module","CONFIRMED","hash matches 009 V-02")
add("T-03","DLL redirect variant (.exe.local)", r"COD OL\codoMP_client_shipRetail.exe.local\codoMP_client_shipRetailBase.dll","PE32/x86","SizeOfImage 0x3991000","same build; 6-byte diff vs T-02","CONFIRMED","offset 0x27D80C..0x27D811: T-02='ff 15 f4 22 b0 10', T-03='b8 01 00 00 00 90'")
add("T-04","DLL redirect variant (2nd copy)", r"COD OL\codoMP_client_shipRetailBase.dll.local\codoMP_client_shipRetailBase.dll","PE32/x86","SizeOfImage 0x3991000","identical to T-03","CONFIRMED","")
add("T-05","runtime unpacked image", r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin","PE32/x86 image","SizeOfImage 0x0E659000","target EXE unpacked mapping","CONFIRMED","ALL static RVAs verified here; SHA-256 newly computed (009 left NOT_COMPUTED)")
add("T-06","sandbox client EXE (executed)", r"run_codol_001\sandbox_datafix_20260929\codoMP_client_shipRetail.exe","PE32/x86","SizeOfImage 0x0E659000","3.19.26.22 / build 1649370","CONFIRMED","identical to T-01; this is the binary that ran in the failed session")
add("T-07","sandbox engine DLL (executed)", r"run_codol_001\sandbox_datafix_20260929\codoMP_client_shipRetailBase.dll","PE32/x86","SizeOfImage 0x3991000","target instance main module","CONFIRMED","identical to T-02")
add("T-08","system hosts (CURRENT, after event)", r"C:\Windows\System32\drivers\etc\hosts","text","915 bytes","local platform config","CONFIRMED","37756f9b... ; NOT the pre-run state (937 B / 07642387...). No codol/QQ lines. See integrity/HOSTS_INTEGRITY_EVENT.md")
add("T-09","hosts snapshot used for restore", r"CODOLServer\_mainline\_hosts_snap\hosts.original","text","915 bytes","canonical console template","CONFIRMED","source of post-event restore; same hash as T-08")
add("T-10","canonical successful sandbox (NOT executed this round)", r"run_codol_001\sandbox_ifs1_20260923","PE32/x86","-","3.19.26.22 / build 1649370","CONFIRMED","This is the sandbox named by the fixed chain (HANDOFF_20260927). THIS ROUND RAN sandbox_datafix_20260929 INSTEAD.")
add("T-11","canonical auth service script", r"CODOLServer\lobby_server\lobby_probe_server.py","python","-","fixed chain service @127.0.0.1:8443","CONFIRMED","fixed chain uses this, NOT fake_auth_tls.py")
add("T-12","canonical lobby socket service script", r"CODOLServer\lobby_server\lobby_socket_server.py","python","-","fixed chain service @127.0.0.2:8444","CONFIRMED","fixed chain uses this, NOT lobby_server.py")
add("T-13","hosts snapshot/restore tool", r"CODOLServer\_mainline\_z7_hosts.py","python","-","official snapshot/apply/restore tool","CONFIRMED","NOT used during this round - that omission is the root cause of INT-031-01")
add("T-14","reference protocol source (same build)", r"_e1_regression\ol-mod-olfinal","source","-","build 1649370 (TimeDateStamp 0x6096930A)","REFERENCE","REFERENCE ONLY; every RVA re-derived from image_best.bin")
rows.append("#")
rows.append("# --- TASK-031 lab / evidence / integrity artifacts ---")
for sub,tag in ((r"CODOL-TASK-031-ACCEPTED-LATCH-REGRESSION\evidence","EVD"),
                (r"CODOL-TASK-031-ACCEPTED-LATCH-REGRESSION\integrity","INT"),
                (r"CODOL-TASK-031-ACCEPTED-LATCH-REGRESSION\_work\lab","LAB")):
    d=os.path.join(ROOT,sub); n=0
    if not os.path.isdir(d): continue
    for fn in sorted(os.listdir(d)):
        fp=os.path.join(d,fn)
        if os.path.isfile(fp):
            n+=1
            rows.append("\t".join(["%s-%02d"%(tag,n),"task031 artifact",fp,str(os.path.getsize(fp)),sha(fp),"-","-","TASK-031","CONFIRMED",os.path.relpath(fp,OUT)]))
    for dp,_,fs in os.walk(d):
        rel=os.path.relpath(dp,d)
        if rel=="." : continue
        for fn in sorted(fs):
            fp=os.path.join(dp,fn)
            rows.append("\t".join(["%s-sub"%tag,"task031 artifact",fp,str(os.path.getsize(fp)),sha(fp),"-","-","TASK-031","CONFIRMED",os.path.relpath(fp,OUT)]))
rows.append("#")
rows.append("# manifest generated: %s (Asia/Shanghai)" % time.strftime("%Y-%m-%dT%H:%M:%S%z"))
rows.append("# host: %s\\%s" % (os.environ.get("COMPUTERNAME","?"), os.environ.get("USERNAME","?")))
open(os.path.join(OUT,"FILE_HASH_MANIFEST.tsv"),"w",encoding="utf-8").write("\n".join(rows)+"\n")
print("lines:",len(rows))
for r in rows[:16]: print(r[:200])
