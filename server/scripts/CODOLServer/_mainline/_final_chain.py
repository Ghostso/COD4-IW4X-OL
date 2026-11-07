import sys, importlib.util, hashlib, hmac, json, glob
spec=importlib.util.spec_from_file_location("lp", r"CODOLServer\lobby_server\lobby_plain_probe.py")
lp=importlib.util.module_from_spec(spec); sys.modules["lp"]=lp; spec.loader.exec_module(lp)
PAD24 = bytes.fromhex("3b3b77c902a4ee89e602398862ff1190ad42dcff040d2188")
D9    = bytes.fromhex("9025f3521589e308369c7bebdc39bd9f75e0be424671dd00")

mat24 = bytes(D9[i] ^ PAD24[i] for i in range(24))
print("conn+D9 (24B)  =", D9.hex())
print("transform(D9)  =", mat24.hex())
print()

run="E57A5C_20261002_000222"
d=fr"CODOLServer\logs\{run}\plain.jsonl"
import os
if os.path.exists(d):
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
    print("frames:", [(len(f), int.from_bytes(f[6:10],'little')) for f in frames])
    if frames:
        f=frames[0]
        for label,key in (("sha1(frame)", hashlib.sha1(f).digest()),
                          ("HMAC(sha1(frame),mat24)", hmac.new(hashlib.sha1(f).digest(), mat24, hashlib.sha1).digest())):
            tag=hmac.new(key, f[:-8], hashlib.sha1).digest()[:8]
            print(f"  {label:26s} -> tag {tag.hex()}  match={tag==f[-8:]}")
else:
    print("run dir missing:", d)
