import sys, importlib.util, json, glob, hmac, hashlib
spec=importlib.util.spec_from_file_location("lp", r"CODOLServer\lobby_server\lobby_plain_probe.py")
lp=importlib.util.module_from_spec(spec); sys.modules["lp"]=lp; spec.loader.exec_module(lp)

runs=[("E57A5C_20261001_220416_a2","b74faff5c1d503a13545d5372efe8851639555e7","266a380d05cb3e730b1bb00eca691820cebc9a0f"),
      ("E57A5C_20261001_221440_a2","9b961571f9ca42f52560ed1303404784b20c3581","34280e6ae6a753868e5bee2680bbb4db64c1366f"),
      ("E57A5C_20261001_222340_a2","72922299c7dbea3fc2afb30172d4c474e02c8e23","6c37a985269ce5d2c3ddc21c89ad9f5ac90f8445")]
for name,txh,rxh in runs:
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
    tx=bytes.fromhex(txh); rx=bytes.fromhex(rxh)
    keys={}
    for kn,k20 in (("tx",tx),("rx",rx)):
        for cn,cf in (("c02a0",lp.codec_02a0),("c0420",lp.codec_0420)):
            d20=cf(k20)
            keys[f"{kn}/{cn}[0:16]"]=d20[:16]
            keys[f"{kn}/{cn}[4:20]"]=d20[4:20]
            keys[f"{kn}/{cn}]raw20"]=d20
    print(f"=== {name}  frames={len(frames)}  keys={len(keys)}")
    hit=0
    for fi,f in enumerate(frames[:2]):
        tag=f[-8:]
        for kn,key in keys.items():
            for msglen in range(len(f)-16, len(f)+1):
                if msglen<=0: continue
                calc=hmac.new(key, f[:msglen], hashlib.sha1).digest()[:8]
                if calc==tag:
                    print(f"   ★ frame{fi} seq={int.from_bytes(f[6:10],'little')} {kn} msglen={msglen}")
                    hit+=1
    if not hit: print("   (no match)")
