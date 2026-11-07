p = r"restore_iips_contract_001\observer2\AboProbe.cs"
s = open(p, encoding="utf-8").read()
old = '                    string preD = Hex(proc, 0x00BA3A4F, 2);'
new = old + '''
                    // Two more guards sit between 0xBA3A4F and the inner-byte
                    // read; both jump to 0xBA3AAD (xor cl,cl):
                    //   0xBA3A70  74 3B  je 0xBA3AAD
                    //   0xBA3A9B  74 10  je 0xBA3AAD
                    string preE = Hex(proc, 0x00BA3A70, 2);
                    string preF = Hex(proc, 0x00BA3A9B, 2);'''
assert old in s; s = s.replace(old, new, 1)

old2 = '''                        bool okD = preD == "7414" && WriteRemoteBytes(
                            proc, 0x00BA3A4F, new byte[] { 0x90, 0x90 });'''
new2 = old2 + '''
                        bool okE = preE == "743b" && WriteRemoteBytes(
                            proc, 0x00BA3A70, new byte[] { 0x90, 0x90 });
                        bool okF = preF == "7410" && WriteRemoteBytes(
                            proc, 0x00BA3A9B, new byte[] { 0x90, 0x90 });'''
assert old2 in s; s = s.replace(old2, new2, 1)

old3 = '                        Ev("PATCH_READFAIL",'
new3 = '''                        Ev("PATCH_GUARDS", "E=" + preE + "->" +
                           Hex(proc, 0x00BA3A70, 2) + " okE=" + okE,
                           "F=" + preF + "->" + Hex(proc, 0x00BA3A9B, 2) +
                           " okF=" + okF,
                           "t=" + t.ToString("F2"), "");
''' + old3
assert old3 in s; s = s.replace(old3, new3, 1)
open(p,"w",encoding="utf-8").write(s)
print("guards patched")
