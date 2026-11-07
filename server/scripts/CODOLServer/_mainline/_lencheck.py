import json
# verify from the client's own frame
d=r"CODOLServer\logs\E57A5C_20261002_002957_a1\plain.jsonl"
fr=None
for line in open(d,encoding="utf-8"):
    try: ev=json.loads(line)
    except Exception: continue
    if ev.get("event")=="hold_recv" and ev.get("len")==386:
        fr=bytes.fromhex(ev["hex"]); break
print("client frame total len =", len(fr))
print("length field           =", int.from_bytes(fr[:4],"little"))
print("=> field + 4 == total ?", int.from_bytes(fr[:4],"little")+4 == len(fr))
print()
print("client frame layout:")
print("  [0:4]   len field =", int.from_bytes(fr[:4],"little"))
print("  [4]     type      =", hex(fr[4]))
print("  [5]     opcode    =", hex(fr[5]))
print("  [6:10]  seq       =", int.from_bytes(fr[6:10],"little"))
print("  [10:26] IV/block  =", fr[10:26].hex())
print("  [26:-8] payload   =", len(fr)-8-26, "bytes")
print("  [-8:]   tag       =", fr[-8:].hex())
