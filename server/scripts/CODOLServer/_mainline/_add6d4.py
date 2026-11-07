p = r"restore_iips_contract_001\observer2\AboProbe.cs"
s = open(p, encoding="utf-8").read()
# add 6d4 to the FRAMEBUF event (which already dumps a0/a4/a8/ac)
old = '''    + indent + "           \\"at_a4=\\" + (a4 != 0 ? Hex(process, a4, 0x20) : \\"-\\"));\\n"'''
if old not in s:
    # fall back: locate the FRAMEBUF Ev() and extend its field list
    old2 = '''+ indent + "           "a8=0x" + a8.ToString("X8") + " ac=" + ac,'''
    print("using alt anchor:", old2 in s)
    new2 = '''+ indent + "           "a8=0x" + a8.ToString("X8") + " ac=" + ac +
    indent + " d4=" + V(ReadU32(process, keyObj + 0x6D4)),'''
    s = s.replace(old2, new2, 1)
else:
    new = old + ''' + '%s' % '' + indent + "d4 handled separately"
    print("unexpected")
open(p,"w",encoding="utf-8").write(s)
print("patched")
