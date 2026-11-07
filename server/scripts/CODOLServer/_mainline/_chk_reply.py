import json
from Crypto.Cipher import AES
d=r"CODOLServer\logs\E57A5C_20261001_210604_a2\plain.jsonl"
key=bytes(16)
for line in open(d,encoding="utf-8"):
    try: ev=json.loads(line)
    except Exception: continue
    if ev.get("event")=="reply_85_cbc":
        raw=bytes.fromhex(ev["hex"])  # only first 64 bytes logged
        print("seq",ev.get("seq"),"logged_len",len(raw),"total",ev.get("len"))
        print("  head",raw[:26].hex())
