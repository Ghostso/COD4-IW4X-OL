p = r"restore_iips_contract_001\observer2\AboProbe.cs"
s = open(p, encoding="utf-8").read()
old = '''                        bool ok9 = pre9 == "53" && WriteRemoteBytes(
                            proc, 0x00BA3A90, new byte[] { 0x56 });'''
new = '''                        // DISABLED: 0xBA3A90 turned out to be on a path that
                        // startup also uses; rewriting it made the process exit
                        // with 0xFFFFFFFF at ~12 s (iipsinit stage), before any
                        // 0x85 exchange.  Kept read-only for observation.
                        bool ok9 = false;'''
assert old in s
s = s.replace(old, new, 1)
open(p, "w", encoding="utf-8").write(s)
print("reverted (write disabled, read kept)")
