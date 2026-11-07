import sys, importlib.util, json, glob
from Crypto.Cipher import AES
spec=importlib.util.spec_from_file_location("lp", r"CODOLServer\lobby_server\lobby_plain_probe.py")
lp=importlib.util.module_from_spec(spec); sys.modules["lp"]=lp; spec.loader.exec_module(lp)
d=glob.glob(r"CODOLServer\logs\E57A5C_20261001_2204*_a*\plain.jsonl")
d=sorted(d)[-1]
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
print("log:", d, "frames:", [len(f) for f in frames])
src620=bytes.fromhex("266a380d05cb3e730b1bb00eca691820cebc9a0f")
keys={
 "zero": bytes(16),
 "p608.key(observed)": bytes.fromhex("f1e9d07399c57ea4edc304d44eacbb38"),
 "codec_02A0(src620)[4:20]": lp.codec_02a0(src620)[4:20],
 "p604.key(observed)": bytes.fromhex("f4b64c15d3b12331335b8fd848896b2d"),
}
for i,f in enumerate(frames[:2]):
    ct=f[26:-8]; usable=ct[:len(ct)//16*16]
    print(f"-- frame{i} len={len(f)} seq={int.from_bytes(f[6:10],'little')}")
    for name,k in keys.items():
        pt=AES.new(k,AES.MODE_CBC,f[10:26]).decrypt(usable)
        good = (b"CODOL" in pt) or (b"UserWarning" in pt) or (b"ComError" in pt)
        print(f"   {name:28s} {pt[:20].hex()} {'<== PLAINTEXT' if good else ''}")
