import sys, importlib.util, json
from Crypto.Cipher import AES
spec=importlib.util.spec_from_file_location("lp", r"CODOLServer\lobby_server\lobby_plain_probe.py")
lp=importlib.util.module_from_spec(spec); sys.modules["lp"]=lp; spec.loader.exec_module(lp)

d=r"CODOLServer\logs\E57A5C_20261002_010817_a3\plain.jsonl"
rx = bytes.fromhex("496fc8b9ed4b932f2c8f1e26b58bfc9f60659e68")
key20 = lp.codec_02a0(rx)
aes_key = key20[4:20]
print("rx620     =", rx.hex())
print("key20     =", key20.hex())
print("aes_key   =", aes_key.hex())
print()
for line in open(d,encoding="utf-8"):
    try: ev=json.loads(line)
    except Exception: continue
    if ev.get("event")=="reply_85_cbc" and ev.get("seq")==1:
        # only the first 64 bytes are logged; reconstruct what we sent
        print("logged head:", ev["hex"][:140])
        break
print()
# reconstruct the two frames we sent
for name,inner in (("87",lp.build_inner_87()), ("89",lp.build_inner_89())):
    frame_len=382
    inner_len=frame_len-2-4-16-8
    pt=inner+b"\x00"*(inner_len-len(inner))
    iv=bytes(16)
    ct=AES.new(aes_key,AES.MODE_CBC,iv).encrypt(pt)
    body=(1).to_bytes(4,"little")+iv+ct
    fw=(frame_len).to_bytes(4,"little")+bytes([0,0x85])+body
    tag=lp.sign_0x85(fw,key20)
    full=fw+tag
    # what the client sees after CBC-decrypt with ITS key
    pt2=AES.new(aes_key,AES.MODE_CBC,full[10:26]).decrypt(full[26:-8])
    print(f"inner={name}: frame_len={len(full)} first_plaintext_byte=0x{pt2[0]:02x}  head={pt2[:8].hex()}")
