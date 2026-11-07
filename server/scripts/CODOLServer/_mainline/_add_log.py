p = r"restore_iips_contract_001\observer2\AboProbe.cs"
s = open(p, encoding="utf-8").read()
old = '''                        string post7 = Hex(proc, 0x00BA35E9, 2);'''
new = '''                        string post7 = Hex(proc, 0x00BA35E9, 2);
                        // Own event: Ev() only keeps 4 fields, so the arm
                        // patch status would otherwise be truncated away.
                        Ev("PATCH_ARM", "pre7=" + pre7 + " post7=" + post7,
                           "ok7=" + ok7, "t=" + t.ToString("F2"), "");'''
assert old in s
s = s.replace(old, new, 1)
open(p, "w", encoding="utf-8").write(s)
print("patched")
