# -*- coding: utf-8 -*-
"""b08: BFS caller tree up from the game decoder to see if it reaches a socket cluster."""
import sys, os, struct
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import _c046 as C
def callers(t):
    return [a for a,_ in C.e8_callers(t)]
seen=set(); frontier=[0x673040]; depth={0x673040:0}
sockregion=range(0x865000,0x866000)
while frontier:
    nxt=[]
    for f in frontier:
        for c in callers(f):
            if c not in seen:
                seen.add(c); depth[c]=depth[f]+1; nxt.append(c)
    frontier=nxt
    if len(seen)>4000: break
print("reachable upstream funcs:",len(seen))
# report funcs that are in the game socket cluster
hits=sorted([c for c in seen if 0x865000<=c<0x866000])
print("upstream funcs inside 0x865000-0x866000:", [hex(x) for x in hits])
# print max depth
md=max(depth.values()); print("max depth",md)
# top-level (no callers) among them
tops=[c for c in seen if not callers(c)]
print("top-level reachable:", [hex(x) for x in tops][:80])
