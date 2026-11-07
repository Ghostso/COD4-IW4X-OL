from pathlib import Path
p=Path("scripts/_tmp_candidate_audit.py")
s=p.read_text(encoding="utf-8")
s=s.replace('print("\\n%s kind=%s refs=%s context=%s"%(fn,next(r["candidate_kind"] for r in rows if r["candidate_func"]==fn)," ".join(r["ref_rva"] for r in rows if r["candidate_func"]==fn),D[max(0,f-8):f+24].hex()))', 'print("\\n%s kind=%s refs=%s"%(fn,next(r["candidate_kind"] for r in rows if r["candidate_func"]==fn)," ".join(r["ref_rva"] for r in rows if r["candidate_func"]==fn)))')
s=s.replace("D[max(0,f-64):off(ref)+16]", "D[max(0,f-64):off(ref)+16]")
p.write_text(s,encoding="utf-8")
print("patched")
