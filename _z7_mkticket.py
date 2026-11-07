# -*- coding: utf-8 -*-
"""Build 128-byte tickets (tag DE AD BD EF) whose standard base64
contains neither '+' nor '/'.  Deterministic search on a seed byte."""
import base64

def build(seed):
    body = bytearray([0xDE, 0xAD, 0xBD, 0xEF])
    for i in range(124):
        body.append((seed + i * 13 + (i >> 3)) & 0xFF)
    return bytes(body)

def ok(b64):
    return "+" not in b64 and "/" not in b64

def make():
    for seed in range(256):
        t = build(seed)
        b = base64.b64encode(t).decode()
        if ok(b) and len(t) == 128:
            return t, b
    return None, None

t, b = make()
if t is None:
    # relax: also try varying both seed and stride
    for seed in range(256):
        for stride in (3, 5, 7, 11, 17, 29):
            body = bytearray([0xDE,0xAD,0xBD,0xEF])
            for i in range(124):
                body.append((seed + i*stride) & 0xFF)
            t = bytes(body)
            b = base64.b64encode(t).decode()
            if ok(b):
                break
        if ok(b): break

print("has +:", "+" in b, " has /:", "/" in b)
print("b64len:", len(b), "declen:", len(base64.b64decode(b)))
print("first4:", base64.b64decode(b)[:4].hex())
print("b64:", b)

# write into mklobby_response-compatible form
import re
p = r"CODOLServer\lobby_server\mklobby_response.py"
src = open(p, encoding="utf-8").read()
new_ct = 'CT_SAFE = %r' % b
new_st = 'ST_SAFE = %r' % b
open(r"D:\z7tmp\tickets.py","w",encoding="utf-8").write(
    "CT_SAFE = %r\nST_SAFE = %r\n" % (b, b))
print("written D:/z7tmp/tickets.py")
