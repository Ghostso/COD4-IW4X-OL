import os
root = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL-TASK-031-ACCEPTED-LATCH-REGRESSION"
rows=[]
rows.append(["phase","phase_name","single_variable","control_state","status","executed",
  "blocking_precondition","result_latch_0_to_1","mmstart_constructed","mmstart_sent",
  "battle_connect","judgement","evidence"])
rows.append(["0","baseline reproduction","NONE (no modification)",
  "kit accepted = b'mmbook accepted'+NUL ; A/B = original","INVALID_PRECONDITION","YES (ran, but session invalid)",
  "client never entered the lobby (stopped at '100' popup); rc=-1 (0xFFFFFFFF) at t=8.0s",
  "INVALID_PRECONDITION","INVALID_PRECONDITION","INVALID_PRECONDITION","INVALID_PRECONDITION",
  "INVALID_PRECONDITION","BASELINE_REPRODUCTION.md ; evidence/LAUNCH_CHAIN_DIFF.tsv ; evidence/P0_*"])
rows.append(["1","A/B pairing alignment","A/B echo values ([matching+0x3A048/0x3A04C])",
  "accepted format/length/timing/channel FIXED to phase-0 form","NOT_RUN","NO",
  "phase 0 is INVALID_PRECONDITION; there is no valid baseline to hold form constant against",
  "NOT_APPLICABLE","NOT_APPLICABLE","NOT_APPLICABLE","NOT_APPLICABLE",
  "NOT_RUN (blocked by invalid phase-0 precondition)","EXPERIMENT_MATRIX.tsv"])
rows.append(["2","accepted byte format","accepted inner bytes (variants A/B/C)",
  "A/B pairing + send channel + timing FIXED","NOT_RUN (STATIC/OFFLINE ONLY)","NO",
  "no lobby business session; client never reached matchmaking. Also channel/caller UNLOCATED",
  "NOT_APPLICABLE","NOT_APPLICABLE","NOT_APPLICABLE","NOT_APPLICABLE",
  "OFFLINE_DETERMINED (codec)，DYNAMIC NOT_RUN","ACCEPTED_BYTE_VARIANTS.tsv ; LATCH_AND_MMSTART_TRACE.md"])
rows.append(["3","combined interaction check","phase1 x phase2 combination",
  "requires phase1 and phase2 valid results","BLOCKED","NO",
  "phase 1 and phase 2 both NOT_RUN; phase 0 precondition invalid",
  "NOT_APPLICABLE","NOT_APPLICABLE","NOT_APPLICABLE","NOT_APPLICABLE",
  "BLOCKED (prerequisite phases not done)","EXPERIMENT_MATRIX.tsv"])
with open(os.path.join(root,"EXPERIMENT_MATRIX.tsv"),"w",encoding="utf-8") as f:
    for r in rows: f.write("\t".join(r)+"\n")
print("\n".join("\t".join(r) for r in rows))
