import sys, importlib.util
spec=importlib.util.spec_from_file_location("lp", r"CODOLServer\lobby_server\lobby_plain_probe.py")
lp=importlib.util.module_from_spec(spec); sys.modules["lp"]=lp; spec.loader.exec_module(lp)
rx = bytes.fromhex("54d4dfcdcd6e47dbe520199f96c479e40eb1ea4f")
frame_len=382
key20 = lp.codec_02a0(rx)
inner = lp.build_inner_87()
inner_len = frame_len - 2 - 4 - 16 - 8
print("inner_len (plaintext size) =", inner_len)
pt = inner + b"\x00"*(inner_len-len(inner))
print("plaintext len              =", len(pt))
from Crypto.Cipher import AES
iv = bytes(16)
ct = AES.new(key20[4:20], AES.MODE_CBC, iv).encrypt(pt)
print("ciphertext len             =", len(ct))
body = (1).to_bytes(4,"little") + iv + ct
print("body len (v1+iv+ct)        =", len(body))
fw = (frame_len).to_bytes(4,"little") + bytes([0x00,0x85]) + body
print("frame-without-tag len      =", len(fw))
print("+ tag8                     =", len(fw)+8)
print("length field               =", frame_len)
print("field + 4 == total ?       =", frame_len+4 == len(fw)+8)
