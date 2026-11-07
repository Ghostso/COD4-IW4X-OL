import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = "AboProbe.cs"
s = open(p, encoding="utf-8", errors="replace").read()

old = """            uint? lobReq644 = null, lobReq5e8 = null, lobReqC4 = null;
            uint? lobReqLen = null, lobReqCap = null, lobReqStrPtr = null;
            string lobReqStr = "";"""
new = """            uint? lobReq644 = null, lobReq5e8 = null, lobReqC4 = null;
            uint? lobReqLen = null, lobReqCap = null, lobReqStrPtr = null;
            string lobReqStr = "";
            // RX/TX machinery of the lobby frame codec (0xBA20A0 and friends).
            uint? lobReqA8 = null, lobReqB0 = null, lobReqB4 = null;
            uint? lobReqB8 = null, lobReqBC = null;
            uint? lobRd1c = null, lobRd24 = null, lobRd10 = null, lobRd0c = null;"""
assert s.count(old) == 1
s = s.replace(old, new, 1)

old2 = """                    lobReqLen = ReadU32(process, lobConn4f4.Value + 0x18);"""
new2 = """                    lobReqA8 = ReadU32(process, lobConn4f4.Value + 0xa8);
                    lobReqB0 = ReadU32(process, lobConn4f4.Value + 0xb0);
                    lobReqB4 = ReadU32(process, lobConn4f4.Value + 0xb4);
                    lobReqB8 = ReadU32(process, lobConn4f4.Value + 0xb8);
                    lobReqBC = ReadU32(process, lobConn4f4.Value + 0xbc);
                    if (lobReqB0.HasValue && lobReqB0.Value != 0)
                    {
                        lobRd1c = ReadU32(process, lobReqB0.Value + 0x1c);
                        lobRd24 = ReadU32(process, lobReqB0.Value + 0x24);
                        lobRd10 = ReadU32(process, lobReqB0.Value + 0x10);
                        lobRd0c = ReadU32(process, lobReqB0.Value + 0x0c);
                    }
                    lobReqLen = ReadU32(process, lobConn4f4.Value + 0x18);"""
assert s.count(old2) == 1
s = s.replace(old2, new2, 1)

old3 = "lobReqStr,dnsA,dnsB,"
new3 = "lobReqStr,lobReqA8,lobReqB0,lobReqB4,lobReqB8,lobReqBC,lobRd1c,lobRd24,lobRd10,lobRd0c,dnsA,dnsB,"
assert s.count(old3) == 1
s = s.replace(old3, new3, 1)

old4 = "V(lobReqLen), V(lobReqCap), V(lobReqStrPtr), lobReqStr,"
new4 = ("V(lobReqLen), V(lobReqCap), V(lobReqStrPtr), lobReqStr,\n"
        "                V(lobReqA8), V(lobReqB0), V(lobReqB4), V(lobReqB8),\n"
        "                V(lobReqBC), V(lobRd1c), V(lobRd24), V(lobRd10),\n"
        "                V(lobRd0c),")
assert s.count(old4) == 1
s = s.replace(old4, new4, 1)

open(p, "w", encoding="utf-8").write(s)
print("ok")
