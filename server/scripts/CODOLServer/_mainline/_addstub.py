p = r"restore_iips_contract_001\observer2\AboProbe.cs"
s = open(p, encoding="utf-8").read()

old = '                    string preA = Hex(proc, 0x00BA3A5F, 2);'
new = old + '''
                    // Redirect the dispatch byte into the lobby object so the
                    // observer can read it.  Both instructions are exactly
                    // 6 bytes, so no jump/trampoline is needed:
                    //   0xBA3AA3  88 95 77FCFFFF  mov [ebp-0x389], dl
                    //          -> 88 97 D4060000  mov [edi+0x6D4], dl
                    //   0xBA3AE0  8A 8D 77FCFFFF  mov cl, [ebp-0x389]
                    //          -> 8A 8F D4060000  mov cl, [edi+0x6D4]
                    // edi = connection object; +0x6D4 is sampled below.
                    string preB = Hex(proc, 0x00BA3AA3, 6);
                    string preC = Hex(proc, 0x00BA3AE0, 6);'''
assert old in s; s = s.replace(old, new, 1)

old2 = '''                        bool okA = preA == "7704" && WriteRemoteBytes(
                            proc, 0x00BA3A5F, new byte[] { 0x90, 0x90 });'''
new2 = old2 + '''
                        bool okB = preB == "889577fcffff" && WriteRemoteBytes(
                            proc, 0x00BA3AA3,
                            new byte[] { 0x88, 0x97, 0xD4, 0x06, 0x00, 0x00 });
                        bool okC = preC == "8a8d77fcffff" && WriteRemoteBytes(
                            proc, 0x00BA3AE0,
                            new byte[] { 0x8A, 0x8F, 0xD4, 0x06, 0x00, 0x00 });'''
assert old2 in s; s = s.replace(old2, new2, 1)

old3 = '                        Ev("PATCH_JA",'
new3 = '''                        Ev("PATCH_DISPATCH_STUB",
                           "B=" + preB + "->" + Hex(proc, 0x00BA3AA3, 6) +
                           " okB=" + okB,
                           "C=" + preC + "->" + Hex(proc, 0x00BA3AE0, 6) +
                           " okC=" + okC,
                           "t=" + t.ToString("F2"), "");
''' + old3
assert old3 in s; s = s.replace(old3, new3, 1)

open(p, "w", encoding="utf-8").write(s)
print("dispatch stub added")
