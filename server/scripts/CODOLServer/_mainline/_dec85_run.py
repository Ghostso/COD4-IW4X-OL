import json, sys
from Crypto.Cipher import AES
log = r"CODOLServer\logs\E57A5C_20261001_204530_a1\plain.jsonl"
buf_all = bytearray()
frames=[]
for line in open(log, encoding="utf-8", errors="replace"):
    try: ev=json.loads(line)
    except Exception: continue
    if ev.get("event")=="hold_recv" and ev.get("len",0)>10:
        buf_all += bytes.fromhex(ev["hex"])
buf=bytes(buf_all)
off=0
while off+10 <= len(buf):
    flen=int.from_bytes(buf[off:off+4],"little")
    if flen<10 or off+4+flen>len(buf): break
    fr=buf[off:off+4+flen]
    if fr[5]==0x85:
        frames.append(fr)
    off += 4+flen
print("parsed frames:", [len(f) for f in frames], "trailing", len(buf)-off)
key=bytes(16)
for i,fr in enumerate(frames):
    seq=int.from_bytes(fr[6:10],"little")
    iv=fr[10:26]; ct=fr[26:-8]
    usable=ct[:len(ct)//16*16]
    pt=AES.new(key,AES.MODE_CBC,iv).decrypt(usable)
    print("="*70)
    print(f"frame{i} seq={seq} len={len(fr)} ct={len(ct)} mod16={len(ct)%16}")
    print("pt_hex", pt[:160].hex())
    txt=''.join(chr(b) if 32<=b<127 else ('.' if b else '_') for b in pt[:200])
    print("pt_txt", txt)
