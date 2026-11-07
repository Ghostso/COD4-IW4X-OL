import sys, importlib.util, hashlib, hmac, json, glob
spec=importlib.util.spec_from_file_location("lp", r"CODOLServer\lobby_server\lobby_plain_probe.py")
lp=importlib.util.module_from_spec(spec); sys.modules["lp"]=lp; spec.loader.exec_module(lp)
PAD = bytes.fromhex("3b3b77c902a4ee89e602398862ff1190ad42dcff040d2188")

runs=[("E57A5C_20261001_220416_a2","b74faff5c1d503a13545d5372efe8851639555e7"),
      ("E57A5C_20261001_221440_a2","9b961571f9ca42f52560ed1303404784b20c3581"),
      ("E57A5C_20261001_222340_a2","72922299c7dbea3fc2afb30172d4c474e02c8e23")]

for name,txh in runs:
    d=f"CODOLServer\\logs\\{name}\\plain.jsonl"
    if not glob.os.path.exists(d): continue
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
    tx=bytes.fromhex(txh)
    f=frames[0]
    hkey=hashlib.sha1(f).digest()          # step1
    print(f"=== {name}")
    print(f"  sha1(frame)      = {hkey.hex()}")
    print(f"  tx20 (observed)  = {tx.hex()}")
    print(f"  match sha1?      = {hkey==tx}")
    # maybe tx20 = HMAC_SHA1(hkey, X)[:20] with X containing the pad
    for label, data in (("PAD alone", PAD),
                        ("PAD^0", PAD),
                        ("zeros24", bytes(24))):
        m=hmac.new(hkey, data, hashlib.sha1).digest()
        if m==tx: print(f"  ★ MATCH via HMAC(hkey, {label})")
    # maybe tx20 = hkey xor pad
    x=bytes(hkey[i]^PAD[i] for i in range(20))
    print(f"  hkey xor PAD[0:20] = {x.hex()}  match={x==tx}")
