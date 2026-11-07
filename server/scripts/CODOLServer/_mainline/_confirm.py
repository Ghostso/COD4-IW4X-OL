import sys, importlib.util
spec=importlib.util.spec_from_file_location("lp", r"CODOLServer\lobby_server\lobby_plain_probe.py")
lp=importlib.util.module_from_spec(spec); sys.modules["lp"]=lp; spec.loader.exec_module(lp)
RX = bytes.fromhex("efd33a88b232318b33d03c5471274d8b28673118")   # TRIO rx620, t=38.553
d20 = lp.codec_02a0(RX)
print("rx620 (TRIO, t=38.553) =", RX.hex())
print("codec_02A0(rx620)      =", d20.hex())
print("  [4:20]               =", d20[4:20].hex())
print()
print("p608 observed at t=38.587..38.600 (same frame batch) = 4610df8ba10ef2fe568d517fa877102f")
print("MATCH [4:20]:", d20[4:20].hex() == "4610df8ba10ef2fe568d517fa877102f")
print()
# also verify the tx side for the same batch
TX = bytes.fromhex("00ff6c168581503fe2dafb2e04682f426ad704cf")
d42 = lp.codec_0420(TX)
print("tx60C (TRIO)           =", TX.hex())
print("codec_0420(tx60C)      =", d42.hex())
print("  [4:20]               =", d42[4:20].hex())
