import sys, importlib.util, json, glob, hmac, hashlib
spec=importlib.util.spec_from_file_location("lp", r"CODOLServer\lobby_server\lobby_plain_probe.py")
lp=importlib.util.module_from_spec(spec); sys.modules["lp"]=lp; spec.loader.exec_module(lp)

CONST24 = bytes.fromhex("ad42f59088a421e63bc9890239ff02dc110477ffee88620d")
PERM    = [0x08,0x12,0x09,0x0E,0x05,0x14, 0x0A,0x07,0x0B,0x0C,0x15,0x16,
           0x0D,0x10,0x03,0x00,0x01,0x0F, 0x13,0x11,0x17,0x06,0x04]

def transform(src: bytes) -> bytes:
    return bytes(src[i] ^ CONST24[PERM[i]] for i in range(24))

runs=[("E57A5C_20261001_220416_a2","b74faff5c1d503a13545d5372efe8851639555e7"),
      ("E57A5C_20261001_221440_a2","9b961571f9ca42f52560ed1303404784b20c3581")]
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
    print(f"=== {name}")
    for fi,f in enumerate(frames[:2]):
        # step 1: hkey = sha1(frame)
        hkey = hashlib.sha1(f).digest()
        # step 2..4 need conn+0xD9 (unknown) -> test whether
        # derived == codec_0420(tx) for ANY plausible mat24
        tag_ok = hmac.new(lp.codec_0420(tx), f[:-8], hashlib.sha1).digest()[:8] == f[-8:]
        print(f"  frame{fi} len={len(f)} tag_ok(using codec_0420(tx20))={tag_ok}")
    print("  note: hkey20(SHA1 of frame) =", hashlib.sha1(frames[0]).hexdigest()[:16], "...")
