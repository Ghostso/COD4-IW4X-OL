p = r"run_codol_001\elevated_ifs1_observer.ps1"
s = open(p, encoding="utf-8").read()

old = "    [string]$HandshakeP608KeyFile = '',"
new = old + "\n    [string]$AcReadyFlag = '',"
assert old in s
s = s.replace(old, new, 1)

old2 = """if ($HandshakeP608KeyFile) {
    $argString += ' --handshake-p608-key-file "' + $HandshakeP608KeyFile + '"'"""
new2 = """if ($AcReadyFlag) {
    $argString += ' --ac-ready-flag "' + $AcReadyFlag + '"'
}
""" + old2
assert old2 in s
s = s.replace(old2, new2, 1)

open(p, "w", encoding="utf-8").write(s)
print("wrapper patched")
