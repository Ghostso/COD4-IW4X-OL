import sys, importlib.util, json
from Crypto.Cipher import AES
spec=importlib.util.spec_from_file_location("lp", r"CODOLServer\lobby_server\lobby_plain_probe.py")
lp=importlib.util.module_from_spec(spec); sys.modules["lp"]=lp; spec.loader.exec_module(lp)
d="CODOLServer\\logs\\E57A5C_20261001_220416_a2\\plain.jsonl"
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
# runtime p604/p608 keys observed in the same session family
for nm,k in [("p604(220424)=f4b64c15d3b12331335b8fd848896b2d", bytes.fromhex("f4b64c15d3b12331335b8fd848896b2d")),
             ("p604(222348)=20a486e5ed681b74f0114c19...", None),
             ("p608(220424)@38.764=f1e9d07399c57ea4edc304d44eacbb38", bytes.fromhex("f1e9d07399c57ea4edc304d44eacbb38")),
             ("p608(221448)@39.466=1285bd861c85208ca711a82f...", None)]:
    if k is None: continue
    ct=f[26:-8]
    pt=AES.new(k, AES.MODE_CBC, f[10:26]).decrypt(ct[:len(ct)//16*16])
    txt=''.join(chr(b) if 32<=b<127 else '.' for b in pt[:40])
    print(f"{nm}\n   pt={pt[:24].hex()}  {txt}")
