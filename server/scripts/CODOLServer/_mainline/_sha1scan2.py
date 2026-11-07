import sys, importlib.util, json, glob, hashlib
from Crypto.Cipher import AES
spec=importlib.util.spec_from_file_location("lp", r"CODOLServer\lobby_server\lobby_plain_probe.py")
lp=importlib.util.module_from_spec(spec); sys.modules["lp"]=lp; spec.loader.exec_module(lp)
d=sorted(glob.glob(r"CODOLServer\logs\E57A5C_20261001_2204*_a*\plain.jsonl"))[-1]
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
f=frames[0]; body=f[26:-8]; usable=body[:len(body)//16*16]
def strict(pt):
    return (b"CODOL" in pt) or (b"UserWarning" in pt) or (b"ComError" in pt) or (pt[:4]==b"\x54\x01\x00\x00")
mk=[("sha1",lambda b: hashlib.sha1(b).digest()),
    ("sha256",lambda b: hashlib.sha256(b).digest()),
    ("md5",lambda b: hashlib.md5(b).digest())]
sls=[slice(0,16), slice(4,20)]
best=[]
for hn,hf in mk:
    for start in range(0, 40):
        for ln in (16,20,24,32,40,48,64,80,96):
            if start+ln>len(f): continue
            h=hf(f[start:start+ln])
            if len(h)<20: continue
            for cn,cf in (("c02a0",lp.codec_02a0),("c0420",lp.codec_0420)):
                for sl in sls:
                    k=cf(h)[sl]
                    if len(k)!=16: continue
                    pt=AES.new(k,AES.MODE_CBC,f[10:26]).decrypt(usable)
                    if strict(pt):
                        best.append((f"{hn}(f[{start}:{start+ln}]) {cn}[{sl.start}:{sl.stop}]", pt[:32].hex()))
print("strict hits:", len(best))
for b in best[:12]: print("  ", b)
