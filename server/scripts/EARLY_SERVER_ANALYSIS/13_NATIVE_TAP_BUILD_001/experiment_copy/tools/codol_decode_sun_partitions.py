"""Decode guarded C1 sun partition captures; no process access or input.

AB98B0 writes view; AB9790 writes projection then calls 61A1D0 for
view*projection at+80 and61A630 for inverse at+C0. Optional point must be
an independently established world point, not an inferred wall hit.
"""
import argparse,json,struct,math
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument("capture",type=Path)
p.add_argument("--point",nargs=3,type=float)
a=p.parse_args();raw=a.capture.read_bytes()
r=json.loads(raw.decode("utf-16" if raw.startswith(b"\xff\xfe") else "utf-8-sig"))
if not r.get("frontendPointerStillCurrent") or int(r.get("frontendPointer","0"),16)<65536:
    raise SystemExit("Capture lacks stable valid frontend pointer")
b=bytes.fromhex(r["projectionInputs"]["sunOutput41c50Hex"])
point=a.point or r["viewOrigin"]
out={"commandTime":r["commandTime"],"point":point,"pointKind":"supplied world point" if a.point else "camera, NOT wall", "partitions":[]}
for i in range(2):
    m=[struct.unpack_from("<16f",b,0x70+i*0x160+j*0x40) for j in range(4)]
    if not all(math.isfinite(v) for matrix in m for v in matrix):raise SystemExit("Nonfinite matrix")
    view,projection,combined,inverse=m
    product=[sum(view[4*j+k]*projection[4*k+h] for k in range(4)) for j in range(4) for h in range(4)]
    clip=[sum((point+[1])[k]*combined[4*k+h] for k in range(4)) for h in range(4)]
    out["partitions"].append(dict(index=i,view=view,projection=projection,combined=combined,inverse=inverse,
        productMaximumDifference=max(abs(x-y) for x,y in zip(product,combined)),
        xyWorldSpan=[2/abs(projection[j]) for j in (0,5)],clip=clip))
print(json.dumps(out,indent=2))
