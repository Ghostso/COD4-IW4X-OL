p = r"restore_iips_contract_001\observer2\AboProbe.cs"
s = open(p, encoding="utf-8").read()
old = '                    string preE = Hex(proc, 0x00BA3A70, 2);'
new = '''                    // Reachability probe: 0xBA3A18 is the first fixed point
                    // after the provider call.  Replace it (6 bytes, equal
                    // length) with `inc byte [edi+0x5E0]` so obj+0x5E0 counts
                    // how many times control reaches this stage.
                    //   89 8D 70FCFFFF  mov [ebp-0x390], ecx
                    //   -> FE 87 E0050000  inc byte [edi+0x5E0]
                    string preG = Hex(proc, 0x00BA3A18, 6);
''' + old
assert old in s; s = s.replace(old, new, 1)

old2 = '''                        bool okE = preE == "743b" && WriteRemoteBytes('''
new2 = '''                        bool okG = preG == "898d70fcffff" && WriteRemoteBytes(
                            proc, 0x00BA3A18,
                            new byte[] { 0xFE, 0x87, 0xE0, 0x05, 0x00, 0x00 });
''' + old2
assert old2 in s; s = s.replace(old2, new2, 1)

old3 = '                        Ev("PATCH_GUARDS",'
new3 = '''                        Ev("PATCH_REACH", "G=" + preG + "->" +
                           Hex(proc, 0x00BA3A18, 6) + " okG=" + okG,
                           "t=" + t.ToString("F2"), "", "");
''' + old3
assert old3 in s; s = s.replace(old3, new3, 1)
open(p,"w",encoding="utf-8").write(s)
print("reachability probe added")
