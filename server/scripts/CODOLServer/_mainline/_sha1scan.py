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
f=frames[0]
print("frame len", len(f), "seq", int.from_bytes(f[6:10],"little"))
# candidate key derivations: sha1 over every plausible slice, then codec
cands={}
body=f[26:-8]
for start in range(0, 30):
    for ln in (16, 20, 32, 40, 64, len(body)-start):
        if ln<=0 or start+ln>len(f): continue
        h=hashlib.sha1(f[start:start+ln]).digest()
        cands[f"sha1(f[{start}:{start+ln}])"]=h
        cands[f"codec02a0(sha1(f[{start}:{start+ln}]))[4:20]"]=lp.codec_02a0(h)[4:20]
        cands[f"codec0420(sha1(f[{start}:{start+ln}]))[4:20]"]=lp.codec_0420(h)[4:20]
usable=body[:len(body)//16*16]
hits=[]
for name,k in cands.items():
    if len(k)!=16: continue
    pt=AES.new(k,AES.MODE_CBC,f[10:26]).decrypt(usable)
    if b"CODOL" in pt or pt[:4]==b"\x54\x01\x00\x00" or pt[:1] in (b"\x87",b"\x89"):
        hits.append((name,pt[:20].hex()))
print("candidates:", len(cands), "hits:", len(hits))
for h in hits[:10]: print("  HIT", h)
