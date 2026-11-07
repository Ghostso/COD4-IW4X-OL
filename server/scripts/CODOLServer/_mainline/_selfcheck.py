import sys, importlib.util, json, glob, hmac, hashlib
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
print("frames:", [(len(f), int.from_bytes(f[6:10],'little')) for f in frames])
# Candidate 20-byte material locations inside a client->server 0x85 frame
for i,f in enumerate(frames[:2]):
    tag=f[-8:]
    print(f"--- frame{i} seq={int.from_bytes(f[6:10],'little')} tag={tag.hex()}")
    found=False
    for start in range(0, min(len(f)-20, 80)):
        M=f[start:start+20]
        for cname,cf in (("c02a0",lp.codec_02a0),("c0420",lp.codec_0420)):
            K=cf(M)
            for msglen in (len(f)-8, len(f)-4, len(f)):
                calc=hmac.new(K, f[:msglen], hashlib.sha1).digest()[:8]
                if calc==tag:
                    print(f"   ★ MATCH material=f[{start}:{start+20}] {cname} msglen={msglen}")
                    found=True
    if not found: print("   no match with simple windows")
