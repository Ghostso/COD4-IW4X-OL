# -*- coding: utf-8 -*-
"""clipmap_locate.py -- locate & validate CODOL clipMap regions in an unpacked zone.

Verified anchors (coop_train_mp_firingrange, all offsets recomputed from bytes):
  entity text   : ASCII "{ ... }" block (worldspawn .. last "}")
  TriggerModel  : N x {contents=0x28000001, hullCount u16, firstHull u16}, 8B each
  TriggerHull   : M x {Bounds(mid3,half3) 24B, contents=0x28000001, slabCount u16, firstSlab u16}, 32B
  TriggerSlab   : K x {dir3(unit), midPoint, halfSize}, 20B each; K == sum(hull.slabCount)
  planes        : run of cplane_s {n3 unit, dist, type u8, pad3}, 20B stride
  material names: "clip_player\\0clip_shot_block\\0clip_full\\0clip\\0"
  plane-ptr tbl : P x {u32 in 0x30000000.., u32 0}, stride-20 deltas -> P == len(planes)

Self-checks raise on any inconsistency. Usage:
  python -X utf8 tools\\clipmap_locate.py ..\\_map_extract\\coop_train_zone.bin
"""
import struct, sys, math, re

def parse_triggers(d, off):
    models=[]; o=off
    while len(models)<64:
        contents,hc,fh = struct.unpack_from("<IHH", d, o)
        if contents!=0x28000001: break
        models.append(dict(hullCount=hc, firstHull=fh)); o+=8
    # hulls follow; their contents lives at +24
    hulls=[]; ho=o
    while True:
        mx,my,mz,hx,hy,hz = struct.unpack_from("<6f", d, ho)
        contents,sc,fs = struct.unpack_from("<IHH", d, ho+24)
        if contents!=0x28000001: break
        hulls.append(dict(mid=(mx,my,mz), half=(hx,hy,hz), slabCount=sc, firstSlab=fs)); ho+=32
    slabs=[]; so=ho
    for i in range(sum(h["slabCount"] for h in hulls)):
        dx,dy,dz,mid,half = struct.unpack_from("<5f", d, so)
        l2=dx*dx+dy*dy+dz*dz
        if abs(l2-1.0)>0.01: raise SystemExit("slab %d dir not unit (%g)"%(i,l2))
        slabs.append(dict(dir=(dx,dy,dz), mid=mid, half=half)); so+=20
    # validate hull refs
    for i,m in enumerate(models):
        if m["firstHull"]+m["hullCount"]>len(hulls):
            raise SystemExit("model %d hull range over hulls"%i)
    # validate slab refs
    for i,h in enumerate(hulls):
        if h["firstSlab"]+h["slabCount"]>len(slabs):
            raise SystemExit("hull %d slab range over slabs"%i)
    return dict(models=models, hulls=hulls, slabs=slabs, end=so)

def parse_planes(d, off):
    planes=[]; o=off
    while True:
        nx,ny,nz,dist = struct.unpack_from("<4f", d, o)
        l2=nx*nx+ny*ny+nz*nz
        if not (math.isfinite(l2) and abs(l2-1.0)<0.02 and abs(dist)<200000): break
        planes.append(dict(n=(nx,ny,nz), dist=dist, type=d[o+16])); o+=20
    return planes, o

def main(path):
    d=open(path,"rb").read()
    # entity text
    i=d.find(b'"classname" "worldspawn"');  assert i>0
    es=d.rfind(b'{',0,i)
    # find end: last "}\n" before binary
    ee=None; depth=0; j=es
    while j < es+200000:
        c=d[j:j+1]
        if c==b'{': depth+=1
        elif c==b'}':
            depth-=1
            if depth==0:
                k=j+1
                while d[k:k+1] in (b'\n',b'\r',b' '): k+=1
                if d[k:k+1]!=b'{': ee=k; break
        j+=1
    ent=d[es:ee]
    bm=[int(x) for x in re.findall(rb'"model" "\*([0-9]+)"', ent)]
    trig_once=len(re.findall(rb'"classname" "trigger_once"', ent))
    trig_mult=len(re.findall(rb'"classname" "trigger_multiple"', ent))
    print("entity text %#x..%#x (%d B); brushmodels=%d max=%d; triggers=%d+%d" % (
        es,ee,ee-es,len(bm),max(bm),trig_once,trig_mult))

    # triggers
    t=(ee+3)&~3; base=None
    for o in range(t, t+64, 4):
        if struct.unpack_from("<I",d,o)[0]==0x28000001: base=o; break
    trig=parse_triggers(d, base)
    print("triggers: models=%d (expect %d) hulls=%d slabs=%d end=%#x" % (
        len(trig["models"]), trig_once+trig_mult, len(trig["hulls"]), len(trig["slabs"]), trig["end"]))
    assert len(trig["models"]) in (trig_once+trig_mult, 2*(trig_once+trig_mult))

    # planes after trigger slabs
    o=trig["end"]; planes=None; planes_off=None
    for cand in range(o, o+0x100, 4):
        ps,e2=parse_planes(d,cand)
        if len(ps)>=8: planes,planes_off=ps,cand; break
    print("planes: %d @ %#x..%#x" % (len(planes), planes_off, planes_off+len(planes)*20))

    # materials + ptr table
    mn=d.find(b"clip_player\x00clip_shot_block\x00clip_full\x00clip\x00", planes_off)
    assert mn>0
    o=mn+len(b"clip_player\x00clip_shot_block\x00clip_full\x00clip\x00")
    n=0
    while True:
        lo,hi=struct.unpack_from("<II", d, o)
        if hi!=0 or not (0x30000000<=lo<0x31000000): break
        n+=1; o+=8
    print("materials: 4 @ %#x; brushside plane-ptr table: %d entries" % (mn, n))
    assert n==len(planes), "plane count %d != ptr entries %d" % (len(planes), n)
    print("SELF-CHECK OK")

if __name__=="__main__":
    main(sys.argv[1] if len(sys.argv)>1 else r"D:\BaiduNetdiskDownload\使命召唤OL\_map_extract\coop_train_zone.bin")



