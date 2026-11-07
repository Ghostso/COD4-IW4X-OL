from pathlib import Path
p=Path("scripts/_tmp_candidate_audit.py")
s=p.read_text(encoding="utf-8")
s=s.replace("for fn in seen:\n st=int(fn,16); f=off(st);", "for fn in seen:\n st=int(fn,16)\n if st == 0x36490: continue\n f=off(st);")
p.write_text(s,encoding="utf-8")
print("patched")
