import sys, importlib.util, hashlib, hmac
spec=importlib.util.spec_from_file_location("lp", r"CODOLServer\lobby_server\lobby_plain_probe.py")
lp=importlib.util.module_from_spec(spec); sys.modules["lp"]=lp; spec.loader.exec_module(lp)

CONST24 = bytes.fromhex("ad42f59088a421e63bc9890239ff02dc110477ffee88620d")
PERM    = [0x08,0x12,0x09,0x0E,0x05,0x14, 0x0A,0x07,0x0B,0x0C,0x15,0x16,
           0x0D,0x10,0x03,0x00,0x01,0x0F, 0x13,0x11,0x17,0x06,0x04]

def transform(src):
    return bytes(src[i] ^ CONST24[PERM[i]] for i in range(len(src)))

# --- report the inverse map (CONST24 permuted) for inspection ---
perm_const = bytes(CONST24[PERM[i]] for i in range(24))
print("permuted CONST24 (the actual XOR pad):")
print("  ", perm_const.hex())
runs=[("E57A5C_20261001_220416_a2","b74faff5c1d503a13545d5372efe8851639555e7"),
      ("E57A5C_20261001_221440_a2","9b961571f9ca42f52560ed1303404784b20c3581"),
      ("E57A5C_20261001_222340_a2","72922299c7dbea3fc2afb30172d4c474e02c8e23")]
print()
print("check: is tx20 == HMAC_SHA1(SHA1(frame), PAD xor X)[:20] for some X?")
print("     (invert: X = PAD xor (unknown) -- cannot solve without X)")
print()
for name,txh in runs:
    tx=bytes.fromhex(txh)
    print(f"{name}")
    print(f"  tx20        = {tx.hex()}")
    print(f"  codec0420   = {lp.codec_0420(tx).hex()}")
