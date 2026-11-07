import sys, importlib.util, json
from Crypto.Cipher import AES
spec=importlib.util.spec_from_file_location("lp", r"CODOLServer\lobby_server\lobby_plain_probe.py")
lp=importlib.util.module_from_spec(spec); sys.modules["lp"]=lp; spec.loader.exec_module(lp)

# rebuild exactly what the probe sent, using the same batch's rx20
rx = bytes.fromhex("54d4dfcdcd6e47dbe520199f96c479e40eb1ea4f")
frame_len=382
key20 = lp.codec_02a0(rx)
key16 = key20[4:20]
print("key20 =", key20.hex())
print("key16 =", key16.hex())
print()
inner = lp.build_inner_87()
print("inner(87) =", inner.hex())
inner_len = frame_len - 2 - 4 - 16 - 8
pt = inner + b"\x00"*(inner_len-len(inner))
print("plaintext len", len(pt), "(expect", inner_len, ")")
print("plaintext head:", pt[:32].hex())
print()
# The client decrypts frame[26:-8]; verify our own construction is self-consistent
iv = bytes(range(16))
ct = AES.new(key16, AES.MODE_CBC, iv).encrypt(pt)
body = (1).to_bytes(4,"little") + iv + ct
fw = (frame_len).to_bytes(4,"little") + bytes([0x00,0x85]) + body
print("frame_len field =", int.from_bytes(fw[:4],"little"), " (should be 382)")
print("total frame len =", len(fw), " (then +8 tag =", len(fw)+8, ")")
tag = lp.sign_0x85(fw, key20)
full = fw + tag
print("full len =", len(full))
print()
# now: what the CLIENT does is decrypt full[26:-8] with p608 key and IV full[10:26]
test_pt = AES.new(key16, AES.MODE_CBC, full[10:26]).decrypt(full[26:-8])
print("client-side decrypt of our frame ->", test_pt[:24].hex())
print("first byte =", hex(test_pt[0]), " (0x87 required for arm)")
