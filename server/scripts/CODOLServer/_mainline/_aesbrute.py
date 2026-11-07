import sys, importlib.util, json, glob, hashlib
from Crypto.Cipher import AES
spec=importlib.util.spec_from_file_location("lp", r"CODOLServer\lobby_server\lobby_plain_probe.py")
lp=importlib.util.module_from_spec(spec); sys.modules["lp"]=lp; spec.loader.exec_module(lp)

d=sorted(glob.glob(r"CODOLServer\logs\E57A5C_20261001_2204*_a*\plain.jsonl"))[0]
buf=bytearray()
for line in open(d,encoding="utf-8"):
    try: ev=json.loads(line)
    except Exception: continue
    if ev.get("event")=="hold_recv" and ev.get("len",0)>10:
        buf += bytes.fromhex(ev["hex"])
buf=bytes(buf); off=0; frames=[]
while off+10<=len(buf):
    fl=int.from_bytes(buf[off:off+4],"little")
    if fl<10 or off+4+fl>len(buf): break
    if buf[off+5]==0x85: frames.append(buf[off:off+4+fl])
    off+=4+fl
f=frames[0]
ct=f[26:-8]; usable=ct[:len(ct)//16*16]
KP=b"CODOL-LOCAL-0001"

# sources available in the frame itself
sources={}
for start in range(0, 40):
    for ln in (16,20,32):
        if start+ln<=len(f):
            sources[f"f[{start}:{start+ln}]"]=f[start:start+ln]
sources["f[10:26](iv)"]=f[10:26]
sources["f[6:10](seq)+iv"]=f[6:10]+f[10:26]

def variants(b):
    out={}
    for cn,cf in (("c02a0",lp.codec_02a0),("c0420",lp.codec_0420)):
        try: d20=cf(b)
        except Exception: continue
        out[cn+"[0:16]"]=d20[:16]
        out[cn+"[4:20]"]=d20[4:20]
        out[cn+"[0:20]"]=d20
        out[cn+"[2:18]"]=d20[2:18]
    for hn,hf in (("sha1",hashlib.sha1),("md5",hashlib.md5),("sha256",hashlib.sha256)):
        h=hf(b).digest()
        out[hn+"[0:16]"]=h[:16]
    out["raw[0:16]"]=b[:16]
    out["raw[4:20]"]=b[4:20]
    return out

ivs={"frame[10:26]":f[10:26],"zero":bytes(16)}
hits=0; tried=0
for sname,src in sources.items():
    for vname,key in variants(src).items():
        if len(key)!=16: continue
        for iname,iv in ivs.items():
            tried+=1
            pt=AES.new(key,AES.MODE_CBC,iv).decrypt(usable)
            if KP in pt:
                print(f"★★★ HIT src={sname} key={vname} iv={iname}")
                print("     pt =", pt[:48].hex())
                hits+=1
print("tried", tried, "hits", hits)
