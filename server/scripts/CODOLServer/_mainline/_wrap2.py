p = r"run_codol_001\capture_elevated_network.ps1"
s = open(p, encoding="utf-8").read()

old = "    [string]$HandshakeP608KeyFile = '',"
new = old + "\n    [string]$AcReadyFlag = '',"
assert old in s
s = s.replace(old, new, 1)

# forward at both -HandshakeP608KeyFile sites
old2 = "    -HandshakeP608KeyFile $HandshakeP608KeyFile `"
new2 = "    -HandshakeP608KeyFile $HandshakeP608KeyFile `\n    -AcReadyFlag $AcReadyFlag `"
cnt = s.count(old2)
s = s.replace(old2, new2)
print("forward sites patched:", cnt)

open(p, "w", encoding="utf-8").write(s)
