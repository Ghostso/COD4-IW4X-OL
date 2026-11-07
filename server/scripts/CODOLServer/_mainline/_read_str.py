import glob, os
# 先在 dump 里读
p=r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(p,"rb").read(); base=0x400000
va=0x81A76A8; o=va-base
print("dump 内 0x%08X (off 0x%X):"% (va,o))
if 0<=o<len(d):
    e=d.find(b"\x00",o); print("   ASCII:", repr(d[o:e].decode("latin1","replace")))
    e2=d.find(b"\x00\x00",o); print("   raw:", d[o:o+80])
else:
    print("   越界")
