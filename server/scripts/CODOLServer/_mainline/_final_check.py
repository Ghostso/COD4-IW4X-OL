import sys, importlib.util, json, glob, hmac, hashlib
from Crypto.Cipher import AES
spec=importlib.util.spec_from_file_location("lp", r"CODOLServer\lobby_server\lobby_plain_probe.py")
lp=importlib.util.module_from_spec(spec); sys.modules["lp"]=lp; spec.loader.exec_module(lp)

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
    tx=bytes.fromhex(txh); K=lp.codec_0420(tx)
    K_aes=K[4:20]
    print(f"=== {name}")
    for fi,f in enumerate(frames[:2]):
        ct=f[26:-8]; usable=ct[:len(ct)//16*16]
        pt=AES.new(K_aes, AES.MODE_CBC, f[10:26]).decrypt(usable)
        tag_ok = hmac.new(K, f[:-8], hashlib.sha1).digest()[:8] == f[-8:]
        txt=''.join(chr(b) if 32<=b<127 else '.' for b in pt[:32])
        print(f"  frame{fi} seq={int.from_bytes(f[6:10],'little')} tag_ok={tag_ok} pt={txt}")
