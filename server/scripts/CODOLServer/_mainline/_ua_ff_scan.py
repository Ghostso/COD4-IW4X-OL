import zlib, re, struct
d=open("ui_mp.ff","rb").read()
print("size", len(d), "head", d[:16].hex(), repr(d[:16]))
# 1) 找 GFx/SWF 头
for magic in [b"GFX", b"CFX", b"FWS", b"CWS", b"ZWS", b"<GFX", b"gfx"]:
    idx=[]; i=0
    while True:
        j=d.find(magic,i)
        if j<0: break
        idx.append(j); i=j+1
        if len(idx)>6: break
    print("magic %-6r -> %s" % (magic, [hex(x) for x in idx]))
# 2) 找 zlib 头
z=[]; i=0
while True:
    j=d.find(b"\x78\x9c",i)
    if j<0: break
    z.append(j); i=j+2
    if len(z)>8: break
print("zlib 78 9c count(sample):", len(z), [hex(x) for x in z[:8]])
print("=== 前 0x120 字节 hex ===")
print(d[:0x120].hex())
