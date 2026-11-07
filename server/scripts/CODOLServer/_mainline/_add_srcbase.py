p = r"restore_iips_contract_001\observer2\AboProbe.cs"
s = open(p, encoding="utf-8").read()

old = 'string pre7 = Hex(proc, 0x00BA35E9, 2);'
new = old + '''
                    // 0xBA3A90  53   push ebx   -> 56   push esi
                    // The 0x85 frame reader 0xB783C0 takes its SOURCE BASE in
                    // arg1.  Two of the three calls in this handler pass esi
                    // (function arg1); only 0xBA3A91 - the one that produces
                    // the inner dispatch byte cl - passes ebx (function arg3),
                    // i.e. a different buffer (observed: b0 != b4).  As a
                    // result cl is never 0x87, the arm never runs and
                    // [obj+0x644] stays 0.  Making this call use esi like the
                    // others is a 1-byte change.
                    string pre8 = Hex(proc, 0x00BA3A90, 1);'''
assert old in s
s = s.replace(old, new, 1)

old2 = '''                        bool ok7 = pre7 == "74d6" && WriteRemoteBytes(
                            proc, 0x00BA35E9, new byte[] { 0x90, 0x90 });'''
new2 = old2 + '''
                        bool ok8 = pre8 == "53" && WriteRemoteBytes(
                            proc, 0x00BA3A90, new byte[] { 0x56 });'''
assert old2 in s
s = s.replace(old2, new2, 1)

old3 = 'string post7 = Hex(proc, 0x00BA35E9, 2);'
new3 = old3 + '\n                        string post8 = Hex(proc, 0x00BA3A90, 1);'
assert old3 in s
s = s.replace(old3, new3, 1)

old4 = 'Ev("PATCH_ARM", "pre7=" + pre7 + " post7=" + post7,'
new4 = 'Ev("PATCH_SRCBASE", "pre8=" + pre8 + " post8=" + post8, "ok8=" + ok8, "t=" + t.ToString("F2"), "");\n                        Ev("PATCH_ARM", "pre7=" + pre7 + " post7=" + post7,'
assert old4 in s
s = s.replace(old4, new4, 1)

open(p, "w", encoding="utf-8").write(s)
print("patched")
