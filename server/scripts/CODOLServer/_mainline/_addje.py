p = r"restore_iips_contract_001\observer2\AboProbe.cs"
s = open(p, encoding="utf-8").read()

old = '                    string preB = Hex(proc, 0x00BA3AA3, 6);'
new = '''                    // 0xBA3A4F  74 14  je 0xBA3A65  (taken when the 4-byte read
                    // at 0xBA3A45 failed).  The stub below proved al=0 there,
                    // so cl ends up 0 via 0xBA3AAD.  NOP it to force al=1 and
                    // let the handler continue to the inner-byte read.
                    string preD = Hex(proc, 0x00BA3A4F, 2);
''' + old
assert old in s; s = s.replace(old, new, 1)

old2 = '''                        bool okB = preB == "889577fcffff" && WriteRemoteBytes('''
new2 = '''                        bool okD = preD == "7414" && WriteRemoteBytes(
                            proc, 0x00BA3A4F, new byte[] { 0x90, 0x90 });
''' + old2
assert old2 in s; s = s.replace(old2, new2, 1)

old3 = '                        Ev("PATCH_DISPATCH_STUB",'
new3 = '''                        Ev("PATCH_READFAIL", "preD=" + preD + " postD=" +
                           Hex(proc, 0x00BA3A4F, 2), "okD=" + okD,
                           "t=" + t.ToString("F2"), "");
''' + old3
assert old3 in s; s = s.replace(old3, new3, 1)
open(p,"w",encoding="utf-8").write(s)
print("je patch added")
