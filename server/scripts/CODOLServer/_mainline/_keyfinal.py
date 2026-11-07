import sys, importlib.util, json
from Crypto.Cipher import AES
spec=importlib.util.spec_from_file_location("lp", r"CODOLServer\lobby_server\lobby_plain_probe.py")
lp=importlib.util.module_from_spec(spec); sys.modules["lp"]=lp; spec.loader.exec_module(lp)
src620=bytes.fromhex("bac753082cab680bb05ef0d48f1993addd7ddd1d")
d20=lp.codec_02a0(src620)
print("codec_02A0(src620) =", d20.hex())
print("[4:20]            =", d20[4:20].hex())
print("observed p608.key = d889860b22803e7ea8b38f595d6dfc2a")
print("MATCH:", d20[4:20].hex()=="d889860b22803e7ea8b38f595d6dfc2a")

# cross-check against the client's own frame using its OWN derived key
d=r"CODOLServer\logs\E57A5C_20261001_213930_a1\plain.jsonl"
import os
if not os.path.exists(d):
    import glob
    cands=glob.glob(r"CODOLServer\logs\E57A5C_20261001_2139*_a*\plain.jsonl")
    print("cands", cands)
    if cands: d=cands[-1]
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
print("frames:", [len(f) for f in frames])
for i,f in enumerate(frames[:2]):
    ct=f[26:-8]; usable=ct[:len(ct)//16*16]
    for name,k in [("zero",bytes(16)), ("codec_02A0(src620)[4:20]", d20[4:20]), ("codec_02A0(src620)[:16]", d20[:16])]:
        pt=AES.new(k,AES.MODE_CBC,f[10:26]).decrypt(usable)
        ok = b"CODOL" in pt or b"Warning" in pt or pt[:1] in (b"\x87",b"\x89")
        print(f"  frame{i} {name:28s} pt={pt[:16].hex()} {'<-- PLAUSIBLE' if ok else ''}")
