p = r"restore_iips_contract_001\observer2\AboProbe.cs"
src = open(p, encoding="utf-8").read()

old = """                                    File.WriteAllText(secretsFile, sb.ToString());
                                    secretsWritten = true;
                                    Ev("SECRETS_WRITTEN",
                                       "sub=0x" + rp2.Value.ToString("X8"),
                                       "challenge=" + ch,
                                       "aes_out=" + aout,
                                       "file=" + secretsFile);"""

new = """                                    File.WriteAllText(secretsFile, sb.ToString());
                                    secretsWritten = true;
                                    // Also export [req+0x648] 32B for the 0x89
                                    // reply's 32B session field (memcmp check
                                    // at 0xBA1171).  Same pattern as echo.txt.
                                    string f648 = Hex(proc, rp2.Value + 0x648, 32);
                                    string f648Path = secretsFile.Replace(
                                        "secrets.txt", "field648.txt");
                                    File.WriteAllText(f648Path, f648 + "\\n");
                                    Ev("SECRETS_WRITTEN",
                                       "sub=0x" + rp2.Value.ToString("X8"),
                                       "challenge=" + ch,
                                       "aes_out=" + aout,
                                       "f648=" + f648);"""

src = src.replace(old, new)
open(p, "w", encoding="utf-8", newline="").write(src)
print("patched")
