# -*- coding: utf-8 -*-
"""The plain probe's --*-aes-key-file wants a bare hex blob (16 or 20 bytes),
not the key=value secrets.txt.  Emit aes_out as aes_out.hex."""
import os, time, threading, sys

SRC = r"D:\z7tmp\secrets.txt"
DST = r"D:\z7tmp\aes_out.hex"
DST20 = r"D:\z7tmp\hmac_out.hex"

T0420_TABLE = bytes([0x41,0x13,0x09,0xAE,0x3F,0xA3,0xBC,0xF3,0x18,0x72,
                     0xEA,0xBC,0x09,0x32,0x11,0xCC,0x12,0x42,0x54,0xF4])
T0420_IDX = bytes([0x07,0x11,0x0E,0x10,0x09,0x13,0x0D,0x00,0x02,0x03,
                   0x04,0x08,0x01,0x0A,0x0B,0x05,0x12,0x06,0x0C,0x0F])

def codec_0420(src):
    return bytes(T0420_TABLE[T0420_IDX[i]] ^ src[i] for i in range(20))

print("watching", SRC, "->", DST, DST20, flush=True)
last = None
t0 = time.time()
while time.time() - t0 < 200:
    try:
        txt = open(SRC, encoding="utf-8").read()
    except OSError:
        time.sleep(0.02); continue
    if txt == last:
        time.sleep(0.02); continue
    last = txt
    d = {}
    for line in txt.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            d[k.strip()] = v.strip()
    if "aes_out" in d and len(d["aes_out"]) == 32:
        open(DST, "w", encoding="ascii").write(d["aes_out"] + "\n")
        print("wrote aes_out.hex", d["aes_out"], flush=True)
    if "blob" in d and len(d["blob"]) >= 40:
        ho = codec_0420(bytes.fromhex(d["blob"][:40]))
        open(DST20, "w", encoding="ascii").write(ho.hex() + "\n")
        print("wrote hmac_out.hex", ho.hex(), flush=True)
    if "aes_out" in d and "blob" in d:
        break
print("done", flush=True)
