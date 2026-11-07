p = r"restore_iips_contract_001\observer2\AboProbe.cs"
s = open(p, encoding="utf-8").read()
old = '''                        // DISABLED: 0xBA3A90 turned out to be on a path that
                        // startup also uses; rewriting it made the process exit
                        // with 0xFFFFFFFF at ~12 s (iipsinit stage), before any
                        // 0x85 exchange.  Kept read-only for observation.
                        bool ok9 = false;'''
new = '''                        // 0xBA3710 (the 0x85 handler) has exactly ONE caller
                        // (0xBA46C2, itself only reached for opcode 0x85) and no
                        // jump-table reference, so patching inside it cannot
                        // affect other paths.  The earlier "12 s startup crash"
                        // happened because the patch landed at t=4.47 s, while
                        // the .tp3 section is still packed; the write hit
                        // placeholder bytes.  Gate on the real instruction
                        // sequence instead of a single byte.
                        bool ok9 = false;
                        if (pre9 == "53" &&
                            Hex(proc, 0x00BA3A8D, 4) == "52505153" &&
                            Hex(proc, 0x00BA3A96, 3) == "83c418")
                        {
                            ok9 = WriteRemoteBytes(
                                proc, 0x00BA3A90, new byte[] { 0x56 });
                        }'''
assert old in s
s = s.replace(old, new, 1)
open(p, "w", encoding="utf-8").write(s)
print("re-enabled with stronger gating")
