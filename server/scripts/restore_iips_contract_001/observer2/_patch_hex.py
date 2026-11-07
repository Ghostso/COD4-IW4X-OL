import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = "AboProbe.cs"
s = open(p, encoding="utf-8", errors="replace").read()
Q = chr(34)

old = "            if (lobbySingleton.HasValue && lobbySingleton.Value != 0)\n            {\n                lobConn4f4 = ReadU32(process, lobbySingleton.Value + 0x4f4);"
new = (
    "            string tplAHex = Hex(process, 0x0E3ECA10, 0x88);\n"
    "            string tplBHex = Hex(process, 0x0E3EC988, 0x88);\n"
    "            string dnsBHex = dnsB.HasValue && dnsB.Value != 0 ?\n"
    "                Hex(process, dnsB.Value, 0x88) : " + Q + Q + ";\n"
    "            string lobReqHex = " + Q + Q + ";\n" + old
)
print("count old", s.count(old))
assert s.count(old) == 1
s = s.replace(old, new, 1)

old2 = "                        lobReqStr = ReadStringAt(process, lobConn4f4.Value + 0x8, 64);\n                    }"
new2 = old2 + "\n                    lobReqHex = Hex(process, lobConn4f4.Value + 0x8, 0x88);"
print("count old2", s.count(old2))
assert s.count(old2) == 1
s = s.replace(old2, new2, 1)

k1 = "tplBPtr,tplBStr,uA50,"
print("hdr", s.count(k1))
assert s.count(k1) == 1
s = s.replace(k1, "tplBPtr,tplBStr,tplAHex,tplBHex,dnsBHex,lobReqHex,uA50,", 1)

k2 = "V(tplBLen), V(tplBCap), V(tplBPtr), tplBStr, V(uA50),"
print("val", s.count(k2))
assert s.count(k2) == 1
s = s.replace(k2, "V(tplBLen), V(tplBCap), V(tplBPtr), tplBStr,\n                tplAHex, tplBHex, dnsBHex, lobReqHex, V(uA50),", 1)

open(p, "w", encoding="utf-8").write(s)
print("ok")
