import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = "AboProbe.cs"
s = open(p, encoding="utf-8", errors="replace").read()

anchor = "static string outDir, tag, mode;"
if "lastCodecKey" not in s:
    assert s.count(anchor) == 1
    s = s.replace(anchor, anchor + "\n        static string lastCodecKey = null;", 1)

needle = "            uint? objAD8 = null, objADC = null;"
block = (
"            // Snapshot the reader on every codec-state change, not only on the\n"
"            // 20 ms CSV tick: the C8=2 -> fail window is ~30 ms and was never\n"
"            // captured by polling.  This records raw bytes for offline analysis.\n"
"            if (lobReqC8.HasValue && lobConn4f4.HasValue && lobReqB0.HasValue)\n"
"            {\n"
"                string codecKey = V(lobReqC8) + \"/\" + V(lobReq9c) + \"/\" +\n"
"                    V(lobReqA8) + \"/\" + V(lobReq5e8);\n"
"                if (codecKey != lastCodecKey)\n"
"                {\n"
"                    lastCodecKey = codecKey;\n"
"                    Ev(\"CODEC_TRANSITION\",\n"
"                       \"req=\" + lobConn4f4.Value.ToString(\"X8\"),\n"
"                       \"c8=\" + V(lobReqC8) + \" s9c=\" + V(lobReq9c) +\n"
"                       \" a8=\" + V(lobReqA8) + \" b0=\" + V(lobReqB0) +\n"
"                       \" b4=\" + V(lobReqB4) + \" rd24=\" + V(lobRd24),\n"
"                       \"buf=\" + lobRdBufHex,\n"
"                       \"rd=\" + lobRdHex);\n"
"                }\n"
"            }\n"
"            uint? objAD8 = null, objADC = null;"
)
assert s.count(needle) == 1
s = s.replace(needle, block, 1)
open(p, "w", encoding="utf-8").write(s)
print("patched ok")
