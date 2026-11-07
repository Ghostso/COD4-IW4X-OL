import sys, importlib.util, hashlib, hmac, json
spec=importlib.util.spec_from_file_location("lp", r"CODOLServer\lobby_server\lobby_plain_probe.py")
lp=importlib.util.module_from_spec(spec); sys.modules["lp"]=lp; spec.loader.exec_module(lp)
PAD24 = bytes.fromhex("3b3b77c902a4ee89e602398862ff1190ad42dcff040d2188")
D9    = bytes.fromhex("9025f3521589e308369c7bebdc39bd9f75e0be424671dd00")
mat24 = bytes(D9[i] ^ PAD24[i] for i in range(24))

d=r"CODOLServer\logs\E57A5C_20261002_000214_a1\plain.jsonl"
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
print("frame0 len", len(f), "tag", f[-8:].hex())
variants = {
 "sha1(frame)": hashlib.sha1(f).digest(),
 "HMAC(sha1(frame),mat24)": hmac.new(hashlib.sha1(f).digest(), mat24, hashlib.sha1).digest(),
 "HMAC(mat24, sha1(frame))": hmac.new(mat24, hashlib.sha1(f).digest(), hashlib.sha1).digest(),
 "mat24": mat24,
 "sha1(mat24)": hashlib.sha1(mat24).digest(),
 "D9": D9,
}
for label,key in variants.items():
    tag=hmac.new(key, f[:-8], hashlib.sha1).digest()[:8]
    print(f"  {label:28s} tag={tag.hex()} match={tag==f[-8:]}")
# also try derived forms through codec
for label,k in variants.items():
    if len(k)>=20:
        for cn,cf in (("c02a0",lp.codec_02a0),("c0420",lp.codec_0420)):
            for sl,s in (("all20",cf(k)),("[4:20]",cf(k)[4:20])):
                tag=hmac.new(s, f[:-8], hashlib.sha1).digest()[:8]
                if tag==f[-8:]:
                    print(f"  ★ MATCH {label} -> {cn}{sl}")
