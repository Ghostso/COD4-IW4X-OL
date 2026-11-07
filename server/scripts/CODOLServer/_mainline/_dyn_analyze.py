import json
p=r"CODOLServer\_mainline\_dyn_game_out3\state.jsonl"
recs=[]
for line in open(p,encoding="utf-8"):
    try: recs.append(json.loads(line))
    except: pass
data=[r for r in recs if "t" in r]
print("采样点=%d  时长=%.1fs"%(len(data), data[-1]["t"] if data else 0))
print()
print("=== dwLobby_state 变化点 ===")
prev=None
for r in data:
    v=r.get("dwLobby_state")
    if v!=prev:
        print("  t=%7.2f  state=%s  prev=%s  chk_arg=%s  u5CC=%s  uA50=%s  flag_61f=%s"%(r["t"],v,r.get("state_prev"),r.get("chk_arg"),r.get("u5CC"),r.get("uA50"),r.get("flag_61f")))
        prev=v
print()
print("=== chk_arg(0xE4EA3C) 变化点 ===")
prev=None
for r in data:
    v=r.get("chk_arg")
    if v!=prev:
        print("  t=%7.2f  chk_arg=%s (0x%X)"%(r["t"],v,v if v else 0)); prev=v
print()
print("=== code_7EF210 是否变化 ===")
s=set(r.get("code_7EF210") for r in data)
for x in s: print("   ",x)
print()
print("=== 非零字段统计 ===")
import collections
for k in ("dwLobby_state","chk_arg","u5CC","u8AC","uA50","flag_dc2","flag_61f","ptr_874"):
    vals=[r.get(k) for r in data]
    nz=[v for v in vals if v]
    print("  %-14s 非零采样=%d/%d  取值集合=%s"%(k,len(nz),len(vals),sorted(set(vals))[:8]))
