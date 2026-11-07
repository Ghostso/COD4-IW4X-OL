p = r"restore_iips_contract_001\observer2\AboProbe.cs"
s = open(p, encoding="utf-8").read()

# 1) add pre7 read right after pre6
old_pre6 = 'string pre6 = Hex(proc, 0x00BA3644, 2);'
new_pre6 = old_pre6 + '''
                    // 0xBA35E9  74 D6   je 0xBA35C1   (0x87 arm failure exit)
                    // 0xBA35E2 calls 0xBA3010, which then calls 0xBA2A60 with a
                    // stale stack argument for its length parameter (see the
                    // manual, 5.27.51).  That call always fails, so 644 never
                    // becomes 1 and every 0x89 reply is reset.  NOPing this
                    // jump lets the arm succeed unconditionally:
                    //   0xBA35EB  mov [esi+0x644], 1
                    string pre7 = Hex(proc, 0x00BA35E9, 2);'''
assert old_pre6 in s
s = s.replace(old_pre6, new_pre6, 1)

# 2) add the write
old_ok6 = '''                        bool ok6 = pre6 == "74d4" && WriteRemoteBytes(
                            proc, 0x00BA3644, new byte[] { 0x90, 0x90 });'''
new_ok6 = old_ok6 + '''
                        bool ok7 = pre7 == "74d6" && WriteRemoteBytes(
                            proc, 0x00BA35E9, new byte[] { 0x90, 0x90 });'''
assert old_ok6 in s
s = s.replace(old_ok6, new_ok6, 1)

# 3) add post7
old_post6 = 'string post6 = Hex(proc, 0x00BA3644, 2);'
new_post6 = old_post6 + '\n                        string post7 = Hex(proc, 0x00BA35E9, 2);'
assert old_post6 in s
s = s.replace(old_post6, new_post6, 1)

# 4) include in applied
old_ap = 'ok1 && ok2 && ok3 && ok4 && ok5 && ok6 &&'
new_ap = 'ok1 && ok2 && ok3 && ok4 && ok5 && ok6 && ok7 &&'
assert old_ap in s
s = s.replace(old_ap, new_ap, 1)

old_cmp = 'post5 == "eb16" && post6 == "9090";'
new_cmp = 'post5 == "eb16" && post6 == "9090" && post7 == "9090";'
assert old_cmp in s
s = s.replace(old_cmp, new_cmp, 1)

open(p, "w", encoding="utf-8").write(s)
print("patched")
