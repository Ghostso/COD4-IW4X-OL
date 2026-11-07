p = r"restore_iips_contract_001\observer2\AboProbe.cs"
lines = open(p, encoding="utf-8").read().split("\n")
idx = None
for i, ln in enumerate(lines):
    if 'Ev("CONN_D9",' in ln:
        idx = i
        break
assert idx is not None, "anchor not found"
# indentation of the anchor line
indent = " " * (len(lines[idx]) - len(lines[idx].lstrip()))
insert = [
    indent + "// Continuously refresh rx.txt / tx.txt for the whole lobby",
    indent + "// window.  Writing them once at the 5E8->3 transition handed the",
    indent + "// probe a stale key: measured, that snapshot's value appeared only",
    indent + "// ~10 times in a whole run while the client used a different",
    indent + "// p608+0x14 for 99.9% of it, so every reply was rejected.",
    indent + "if (!string.IsNullOrEmpty(liveRxKeyFile))",
    indent + "{",
    indent + "    string curRx = Hex(process, keyObj + 0x620, 20);",
    indent + "    if (curRx != lastRxRaw)",
    indent + "    {",
    indent + "        lastRxRaw = curRx;",
    indent + "        try { File.WriteAllText(liveRxKeyFile, curRx + \"\\n\"); }",
    indent + "        catch (Exception) { }",
    indent + "    }",
    indent + "}",
    indent + "if (!string.IsNullOrEmpty(liveTxKeyFile))",
    indent + "{",
    indent + "    string curTx = Hex(process, keyObj + 0x60C, 20);",
    indent + "    if (curTx != lastTxRaw)",
    indent + "    {",
    indent + "        lastTxRaw = curTx;",
    indent + "        try { File.WriteAllText(liveTxKeyFile, curTx + \"\\n\"); }",
    indent + "        catch (Exception) { }",
    indent + "    }",
    indent + "}",
]
lines[idx:idx] = insert
open(p, "w", encoding="utf-8").write("\n".join(lines))
print("inserted at line", idx+1)
