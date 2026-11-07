p = r"restore_iips_contract_001\observer2\AboProbe.cs"
s = open(p, encoding="utf-8").read()
old = '                    string preG = Hex(proc, 0x00BA3A18, 6);'
new = '''                    // 0xBA3A2A  74 39  je 0xBA3A65
                    // The lone exit between the provider call (0xBA3A05) and
                    // the 4-byte read (0xBA3A45).  Reachability probe showed
                    // control reaches 0xBA3A18 but never 0xBA3AA3, so this is
                    // the guard that diverts it.  (An earlier attempt to patch
                    // this was reverted after a "startup crash" that later
                    // proved to be stray-probe port contention, not the patch.)
                    string preH = Hex(proc, 0x00BA3A2A, 2);
''' + old
assert old in s; s = s.replace(old, new, 1)

old2 = '''                        bool okG = preG == "898d70fcffff" && WriteRemoteBytes('''
new2 = '''                        bool okH = preH == "7439" && WriteRemoteBytes(
                            proc, 0x00BA3A2A, new byte[] { 0x90, 0x90 });
''' + old2
assert old2 in s; s = s.replace(old2, new2, 1)

old3 = '                        Ev("PATCH_REACH",'
new3 = '''                        Ev("PATCH_PROVFAIL", "H=" + preH + "->" +
                           Hex(proc, 0x00BA3A2A, 2) + " okH=" + okH,
                           "t=" + t.ToString("F2"), "", "");
''' + old3
assert old3 in s; s = s.replace(old3, new3, 1)
open(p,"w",encoding="utf-8").write(s)
print("0xBA3A2A patched in")
