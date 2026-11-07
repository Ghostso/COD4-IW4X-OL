import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = "AboProbe.cs"
s = open(p, encoding="utf-8", errors="replace").read()
old = """                    if (lobReqB0.HasValue && lobReqB0.Value != 0)
                    {
                        lobRd1c = ReadU32(process, lobReqB0.Value + 0x1c);
                        lobRd24 = ReadU32(process, lobReqB0.Value + 0x24);
                        lobRd10 = ReadU32(process, lobReqB0.Value + 0x10);
                        lobRd0c = ReadU32(process, lobReqB0.Value + 0x0c);
                    }"""
new = """                    if (lobReqB0.HasValue && lobReqB0.Value != 0)
                    {
                        lobRd1c = ReadU32(process, lobReqB0.Value + 0x1c);
                        lobRd24 = ReadU32(process, lobReqB0.Value + 0x24);
                        lobRd10 = ReadU32(process, lobReqB0.Value + 0x10);
                        lobRd0c = ReadU32(process, lobReqB0.Value + 0x0c);
                        lobRd08 = ReadU32(process, lobReqB0.Value + 0x08);
                        lobRd14 = ReadU32(process, lobReqB0.Value + 0x14);
                        lobRd20 = ReadU32(process, lobReqB0.Value + 0x20);
                        // full hex of the reader object + its buffer head: this
                        // is the authoritative record of how the opcode buffer
                        // gets filled, replacing earlier single-point guesses.
                        lobRdHex = Hex(process, lobReqB0.Value, 0x40);
                        if (lobRd1c.HasValue && lobRd1c.Value != 0)
                            lobRdBufHex = Hex(process, lobRd1c.Value, 0x40);
                    }"""
assert s.count(old) == 1
s = s.replace(old, new, 1)
old2 = "            uint? lobRd1c = null, lobRd24 = null, lobRd10 = null, lobRd0c = null;"
new2 = ("            uint? lobRd1c = null, lobRd24 = null, lobRd10 = null, lobRd0c = null;\n"
        "            uint? lobRd08 = null, lobRd14 = null, lobRd20 = null;\n"
        "            string lobRdHex = \"\", lobRdBufHex = \"\";")
assert s.count(old2) == 1
s = s.replace(old2, new2, 1)
s = s.replace("lobRd24,lobRd10,lobRd0c,dnsA,", "lobRd24,lobRd10,lobRd0c,lobRd08,lobRd14,lobRd20,lobRdHex,lobRdBufHex,dnsA,", 1)
s = s.replace("V(lobRd0c),", "V(lobRd0c), V(lobRd08), V(lobRd14), V(lobRd20),\n                lobRdHex, lobRdBufHex,", 1)
open(p, "w", encoding="utf-8").write(s)
print("patched")
