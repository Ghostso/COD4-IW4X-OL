p=r"COD OL\codoMP_client_shipRetail.exe"
d=open(p,"rb").read()
va=0x81A76A8; o=va-0x714000
print("file off 0x%X"%o)
if 0<=o<len(d):
    e=d.find(b"\x00",o); print("  ASCII:", repr(d[o:e].decode("latin1","replace")))
    print("  raw:", d[o:o+96])
