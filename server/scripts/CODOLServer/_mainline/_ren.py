p = r"restore_iips_contract_001\observer2\AboProbe.cs"
s = open(p, encoding="utf-8").read()
# the new one is the one reading 0xBA3A90; rename it to pre9
s = s.replace('string pre8 = Hex(proc, 0x00BA3A90, 1);',
              'string pre9 = Hex(proc, 0x00BA3A90, 1);')
s = s.replace('bool ok8 = pre8 == "53" && WriteRemoteBytes(\n                            proc, 0x00BA3A90, new byte[] { 0x56 });',
              'bool ok9 = pre9 == "53" && WriteRemoteBytes(\n                            proc, 0x00BA3A90, new byte[] { 0x56 });')
s = s.replace('string post8 = Hex(proc, 0x00BA3A90, 1);',
              'string post9 = Hex(proc, 0x00BA3A90, 1);')
s = s.replace('Ev("PATCH_SRCBASE", "pre8=" + pre8 + " post8=" + post8, "ok8=" + ok8,',
              'Ev("PATCH_SRCBASE", "pre9=" + pre9 + " post9=" + post9, "ok9=" + ok9,')
open(p, "w", encoding="utf-8").write(s)
print("renamed")
