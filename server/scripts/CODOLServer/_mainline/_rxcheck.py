import sys, importlib.util
spec=importlib.util.spec_from_file_location("lp", r"CODOLServer\lobby_server\lobby_plain_probe.py")
lp=importlib.util.module_from_spec(spec); sys.modules["lp"]=lp; spec.loader.exec_module(lp)
RX = bytes.fromhex("efd33a88b232318b33d03c5471274d8b28673118")
d20 = lp.codec_02a0(RX)
print("codec_02A0(rx620)      =", d20.hex())
print("[4:20]                 =", d20[4:20].hex())
print("[0:16]                 =", d20[:16].hex())
print()
# compare against the p608 keys actually observed in that same run
obs = ["f2b861a3bcce011e74891a1770893b16",
       "52cc481cff54873ffdb10b1eed6e80f5",
       "80925cc11e4774f2f71c91a4b03a1451"]
for o in obs:
    print(f"  observed p608 {o}  ==[4:20]? {o==d20[4:20].hex()}   ==[0:16]? {o==d20[:16].hex()}")
