import json, glob, os
from Crypto.Cipher import AES
KP=[b"CODOL-LOCAL", b"UserWarning", b"ComError"]
def frames_of(p):
    buf=bytearray()
    for line in open(p,encoding="utf-8",errors="replace"):
        try: ev=json.loads(line)
        except Exception: continue
        if ev.get("event")=="hold_recv" and ev.get("len",0)>10:
            buf += bytes.fromhex(ev["hex"])
    buf=bytes(buf); off=0; out=[]
    while off+10<=len(buf):
        fl=int.from_bytes(buf[off:off+4],"little")
        if fl<10 or off+4+fl>len(buf): break
        if buf[off+5]==0x85: out.append(buf[off:off+4+fl])
        off+=4+fl
    return out
res=[]
for p in sorted(glob.glob(r"CODOLServer\logs\*\plain.jsonl")):
    try: fr=frames_of(p)
    except Exception: continue
    if not fr: continue
    f=fr[0]
    if len(f)<40: continue
    ct=f[26:-8]; usable=ct[:len(ct)//16*16]
    for kn,k in (("zero",bytes(16)),):
        pt=AES.new(k,AES.MODE_CBC,f[10:26]).decrypt(usable)
        if any(x in pt for x in KP):
            res.append((os.path.basename(os.path.dirname(p)), pt[:24].hex()))
print("zero-key-decodable runs:", len(res))
for r in res: print("  ", r[0], r[1])
