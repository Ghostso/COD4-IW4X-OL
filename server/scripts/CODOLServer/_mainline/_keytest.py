import json, sys
sys.path.insert(0, r"CODOLServer\lobby_server")
from Crypto.Cipher import AES
import importlib.util
spec=importlib.util.spec_from_file_location("lp", r"CODOLServer\lobby_server\lobby_plain_probe.py")
lp=importlib.util.module_from_spec(spec); sys.modules["lp"]=lp; spec.loader.exec_module(lp)

rx20=bytes.fromhex("1589a669a13d78c9129e1f185f7a441cbbd3fc70")
tx20=bytes.fromhex("f9eaa26d28802afe0a16318927d96dc873ae4125")
print("codec_02A0(rx20) =", lp.codec_02a0(rx20).hex())
print("codec_0420(tx20) =", lp.codec_0420(tx20).hex())

d=r"CODOLServer\logs\E57A5C_20261001_212007_a1\plain.jsonl"
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

# Try every plausible key/IV combination against the client's real seq=1 frame.
f=frames[0]
ct=f[26:-8]; usable=ct[:len(ct)//16*16]
for kname,key in [("codec_02A0(rx20)[:16]", lp.codec_02a0(rx20)[:16]),
                  ("codec_0420(tx20)[:16]", lp.codec_0420(tx20)[:16]),
                  ("rx20[:16]", rx20[:16]), ("zero", bytes(16))]:
    for ivname,iv in [("frame[10:26]", f[10:26]), ("zero", bytes(16))]:
        try:
            pt=AES.new(key,AES.MODE_CBC,iv).decrypt(usable)
        except Exception as e:
            continue
        if pt[:1]==b"\x87" or pt[:1]==b"\x89" or b"CODOL" in pt:
            print("HIT-CLIENT", kname, ivname, pt[:24].hex())
        if pt[:4]==b"\x54\x01\x00\x00":
            print("HIT-LEN", kname, ivname, pt[:24].hex())
