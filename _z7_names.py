import re
def names(p):
    d = open(p,"rb").read()
    # extract ASCII runs >= 6 chars (method/field names live as plain strings in #Strings)
    return set(m.group().decode() for m in re.finditer(rb"[A-Za-z_][A-Za-z0-9_]{5,60}", d))
a = names(r"backups\FROZEN_20261002_222802\A_observer_out\AboProbe.dll")
b = names(r"restore_iips_contract_001\observer2\uut3\AboProbe.dll")
print("50176 names: %d   90624 names: %d" % (len(a), len(b)))
only_a = sorted(a - b)
only_b = sorted(b - a)
print("\n=== only in 50176 (%d) ===" % len(only_a))
for x in only_a[:60]: print("  ", x)
print("\n=== only in 90624 (%d) ===" % len(only_b))
for x in only_b[:60]: print("  ", x)
