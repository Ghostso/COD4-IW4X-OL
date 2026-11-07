p = r"restore_iips_contract_001\observer2\AboProbe.cs"
s = open(p, encoding="utf-8").read()

# static field
old_f = "        static string liveTxKeyFile = null;"
new_f = old_f + "\n        static string acReadyFlag = null;\n        static uint lastAcForFlag = 0;"
assert old_f in s
s = s.replace(old_f, new_f, 1)

# bind from args
old_b = "            liveTxKeyFile = handshakeTxFile;"
new_b = old_b + '''
            acReadyFlag = Arg(args, "--ac-ready-flag", null);'''
assert old_b in s
s = s.replace(old_b, new_b, 1)

# emit in the CODEC_KEYS block: ac == 0x17E (382) transition writes the flag
anchor = '                Ev("CONN_D9",'
assert anchor in s
indent = " " * (len(anchor) - len(anchor.lstrip()))
inject = (
    indent + "// The 0x85 frame buffer is refilled per frame: [obj+0xAC] goes\n"
    + indent + "// 0 -> 382 -> 0.  Publishing a flag on the 0->382 edge lets the\n"
    + indent + "// probe send only while a frame is actually pending; otherwise the\n"
    + indent + "// reader at 0xBA3A91 has a zero length and reads garbage.\n"
    + indent + "if (!string.IsNullOrEmpty(acReadyFlag))\n"
    + indent + "{\n"
    + indent + "    uint acNow = ReadU32(process, keyObj + 0xAC) ?? 0;\n"
    + indent + "    if (acNow != lastAcForFlag)\n"
    + indent + "    {\n"
    + indent + "        lastAcForFlag = acNow;\n"
    + indent + "        if (acNow != 0)\n"
    + indent + "        {\n"
    + indent + "            try { File.WriteAllText(acReadyFlag,\n"
    + indent + "                  acNow.ToString() + \"\\n\"); } catch (Exception) { }\n"
    + indent + "            Ev(\"AC_READY\", \"ac=\" + acNow,\n"
    + indent + "               \"t=\" + t.ToString(\"F3\"), \"\", \"\");\n"
    + indent + "        }\n"
    + indent + "    }\n"
    + indent + "}\n"
)
s = s.replace(anchor, inject + anchor, 1)
open(p, "w", encoding="utf-8").write(s)
print("patched")
