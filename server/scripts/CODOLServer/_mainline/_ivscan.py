import sys, importlib.util, json, glob, itertools
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
src=bytes.fromhex("266a380d05cb3e730b1bb00eca691820cebc9a0f")
d2=lp.codec_02a0(src); d4=lp.codec_0420(src)
keys={"zero":bytes(16),"p608":d2[4:20],"p608_0":d2[:16],"p604":d4[4:20],"p604_0":d4[:16],
      "src620_0":src[:16],"src620_4":src[4:20]}
f=frames[0]
ivs={"frame[10:26]":f[10:26],"zero":bytes(16),"src620_0":src[:16],"src620_4":src[4:20],
     "d2_0":d2[:16],"d2_4":d2[4:20]}
ct=f[26:-8]; usable=ct[:len(ct)//16*16]
hits=0
for kn,k in keys.items():
    for ivn,iv in ivs.items():
        pt=AES.new(k,AES.MODE_CBC,iv).decrypt(usable)
        score=sum(1 for b in pt[:64] if 32<=b<127)
        if score>40 or b"CODOL" in pt or pt[:4]==b"\x54\x01\x00\x00":
            print(f"HIT key={kn:10s} iv={ivn:12s} score={score} pt={pt[:32].hex()}")
            hits+=1
print("hits:",hits)
