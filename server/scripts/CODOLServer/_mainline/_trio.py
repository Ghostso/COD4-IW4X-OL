import sys, importlib.util, hashlib, hmac, json
spec=importlib.util.spec_from_file_location("lp", r"CODOLServer\lobby_server\lobby_plain_probe.py")
lp=importlib.util.module_from_spec(spec); sys.modules["lp"]=lp; spec.loader.exec_module(lp)
PAD24 = bytes.fromhex("3b3b77c902a4ee89e602398862ff1190ad42dcff040d2188")
D9    = bytes.fromhex("9025f3521589e308369c7bebdc39bd9f75e0be424671dd00")
TX    = bytes.fromhex("00ff6c168581503fe2dafb2e04682f426ad704cf")
RX    = bytes.fromhex("efd33a88b232318b33d03c5471274d8b28673118")
mat24 = bytes(D9[i] ^ PAD24[i] for i in range(24))
print("mat24 = transform(D9) =", mat24.hex())
print("TX60C =", TX.hex())
print("RX620 =", RX.hex())
print()
d=r"CODOLServer\logs\E57A5C_20261002_001315_a3\plain.jsonl"
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
f=frames[0]; target=f[-8:]
print("frame0 tag =", target.hex())
print()
# which candidate reproduces the tag?
cands={}
cands["codec0420(TX)"]=lp.codec_0420(TX)
cands["codec02a0(TX)"]=lp.codec_02a0(TX)
cands["HMAC(sha1(frame),mat24)"]=hmac.new(hashlib.sha1(f).digest(), mat24, hashlib.sha1).digest()
cands["HMAC(mat24,sha1(frame))"]=hmac.new(mat24, hashlib.sha1(f).digest(), hashlib.sha1).digest()
for label,key in cands.items():
    tag=hmac.new(key, f[:-8], hashlib.sha1).digest()[:8]
    print(f"  {label:28s} tag={tag.hex()} match={tag==target}")
