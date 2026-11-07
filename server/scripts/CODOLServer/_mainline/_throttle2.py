p = r"restore_iips_contract_001\observer2\AboProbe.cs"
s = open(p, encoding="utf-8").read()
old = '                        Ev("P604_VTABLE",'
new = '''                        bool emitVt4 = (t - lastVtable4Emit) >= 0.5;
                        if (emitVt4) lastVtable4Emit = t;
                        if (emitVt4) Ev("P604_VTABLE",'''
assert old in s
s = s.replace(old, new, 1)

old2 = "        static double lastVtableEmit = -1.0;"
new2 = old2 + "\n        static double lastVtable4Emit = -1.0;"
assert old2 in s
s = s.replace(old2, new2, 1)

# LOBBY_P608_KEY_ERROR was firing 1400+ times; keep it but note it is a write
open(p,"w",encoding="utf-8").write(s)
print("p604 throttled")
