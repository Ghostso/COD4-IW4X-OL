import re
def names(p):
    d = open(p,"rb").read()
    return set(m.group().decode() for m in re.finditer(rb"[A-Za-z_][A-Za-z0-9_]{5,60}", d))
a = names(r"backups\FROZEN_20261002_222802\A_observer_out\AboProbe.dll")
b = names(r"restore_iips_contract_001\observer2\uut3\AboProbe.dll")
ob = sorted(b - a)
print("=== 90624 独有（%d 项），过滤掉哈希串 ===" % len(ob))
for x in ob:
    if re.fullmatch(r"[0-9A-F]{40,}", x): continue
    print("  ", x)
