# -*- coding: utf-8 -*-
import sys,os,json
sys.stdout.reconfigure(encoding="utf-8")
for f in ["CodolStateReader.cs","CodolRangeEquipment.cs"]:
    s=open("_extracted/reference/"+f,encoding="utf-8",errors="replace").read()
    print("="*20,f,len(s))
    print(s[:2200])
    print()
for f in ["gamestate-constants.json","composite-gamestate-candidate.json","player-candidate-format.json","spawn-candidate-format.json","udp-summary.json","association-status.json"]:
    try:
        d=json.load(open("_extracted/reference/"+f,encoding="utf-8"))
        print("--",f,":",json.dumps(d,ensure_ascii=False)[:500])
    except Exception as e: print("--",f,"ERR",e)
