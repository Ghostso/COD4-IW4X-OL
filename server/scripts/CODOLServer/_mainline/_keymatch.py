import sys, importlib.util
spec=importlib.util.spec_from_file_location("lp", r"CODOLServer\lobby_server\lobby_plain_probe.py")
lp=importlib.util.module_from_spec(spec); sys.modules["lp"]=lp; spec.loader.exec_module(lp)
src620=bytes.fromhex("bac753082cab680bb05ef0d48f1993addd7ddd1d")
src60C=None
print("codec_02A0(src620)      =", lp.codec_02a0(src620).hex())
print("codec_02A0(src620)[:16] =", lp.codec_02a0(src620)[:16].hex())
for k in ["d889860b22803e7ea8b38f595d6dfc2a","52cc481cff54873ffdb10b1eed6e80f5","faec571026d000d1c41cf5e9b398e11c"]:
    print(k, "== codec_02A0(src620)[:16]?", k==lp.codec_02a0(src620)[:16].hex())
    print(k, "== codec_0420(src620)[:16]?", k==lp.codec_0420(src620)[:16].hex())
