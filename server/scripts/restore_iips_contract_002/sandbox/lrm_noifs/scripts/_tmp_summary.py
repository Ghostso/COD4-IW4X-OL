import csv, collections
from pathlib import Path
rows=list(csv.DictReader(open(r"scripts\_out\high_reuse_slot_final_refs.csv",encoding="utf-8")))
for slot in ["0x00CA8114","0x00CA8194","0x00CA812C","0x00CA819C","0x00CA8164"]:
 rs=[r for r in rows if r["slot_va"].lower()==slot.lower()]
 print("SLOT",slot,"n",len(rs),"cfg",sum(r["cfg_instruction_start"]=="YES" for r in rs),"linear",sum(r["boundary_status"]=="LINEAR_CANDIDATE_ONLY" for r in rs))
 print("cfg refs:",[(r["ref_rva"],r["cfg_roots"]) for r in rs if r["cfg_instruction_start"]=="YES"])
