import os
o=r"COD OL\IIPS\TPFUI\IIPSRes\back\边玩边下\边玩边下底.png"
print("原始 边玩边下底.png:")
print("  exists", os.path.isfile(o))
if os.path.isfile(o):
    d=open(o,"rb").read()
    print("  size", len(d))
    print("  head", d[:32].hex())
    print("  tail", d[-16:].hex())
