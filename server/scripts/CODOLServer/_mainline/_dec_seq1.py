import sys, importlib.util
from Crypto.Cipher import AES
spec=importlib.util.spec_from_file_location("lp", r"CODOLServer\lobby_server\lobby_plain_probe.py")
lp=importlib.util.module_from_spec(spec); sys.modules["lp"]=lp; spec.loader.exec_module(lp)
raw = bytes.fromhex("7e010000ab85010000002005856fdd82c4741b81f170bab95ba6efc6caeb3ac5ff53a5c8a83a9b6fe931fbfaf268a45cfb68111c6c948e910252d76c577baaafd78c966a80d59cb5a0b71625b44bb84277470bac8b9444fbc935dacf704f963d6653b6201acb1ba8135026e5b36978e47ae5fe419aece7ddaf672ee7c7d0b2a52af9fcff75e712905141a28c135cc57457e9e57d561ed32b9f3ad00f52f98a44de54bccfc42e4466ed7d5541cc36311c9ef2011cb1d58b9febe6520adedcb32107167836aa5bc1c18a1070b7c71dacb2aca9c5f04650d30e7124188f971393ef075da8c041a566c9fbb10c0a44d404e8e42957feec3afb5b24acaf60058db8c147ed620ac3d21bc2b47c4c82cec0460d8f7c8a2b8da6d191636ca6380abca2806fd9067493dcefd3ba538ddf25311e83517939ed4d160ba860507e04d0538436245614f2f5f2400d6a5b2003f300051fc83de3390fa11de6f6f5aa40dfc8d875e957a64eb6a7648ef0e69ee3a2069461010b98ccd05479cea7be32838894f246917e") if False else None
# read the actual frame from the log instead
import json
d=r"CODOLServer\logs\E57A5C_20261002_002957_a1\plain.jsonl"
fr=None
for line in open(d,encoding="utf-8"):
    try: ev=json.loads(line)
    except Exception: continue
    if ev.get("event")=="hold_recv" and ev.get("len")==386:
        fr=bytes.fromhex(ev["hex"]); break
rx=bytes.fromhex("54d4dfcdcd6e47dbe520199f96c479e40eb1ea4f")
tx=bytes.fromhex("cc2f4de16711e0e6c1ae555f882c1afc35e2d835")
print("frame len", len(fr), "seq", int.from_bytes(fr[6:10],"little"))
ct=fr[26:-8]; usable=ct[:len(ct)//16*16]
print()
print("try zero-key (was the case when --force-p608-zero-key was on):")
pt=AES.new(bytes(16), AES.MODE_CBC, fr[10:26]).decrypt(usable)
print("  ", pt[:64].hex())
print("  ", ''.join(chr(b) if 32<=b<127 else '.' for b in pt[:64]))
print()
for name,k in (("codec02a0(rx)[4:20]", lp.codec_02a0(rx)[4:20]),
               ("codec0420(tx)[4:20]", lp.codec_0420(tx)[4:20]),
               ("p604 style codec0420(tx)[:16]", lp.codec_0420(tx)[:16])):
    pt=AES.new(k, AES.MODE_CBC, fr[10:26]).decrypt(usable)
    print(f"{name}: {pt[:48].hex()}")
    print("   ", ''.join(chr(b) if 32<=b<127 else '.' for b in pt[:48]))
