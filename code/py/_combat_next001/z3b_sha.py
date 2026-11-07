# -*- coding: utf-8 -*-
import hashlib, os
BASE = r'D:\BaiduNetdiskDownload\使命召唤OL'
COPY = os.path.join(BASE, 'REF_LOBBY_KIT_CAP009')
FILES = ["COMBAT_V0_1_NEXT_010_CAPTURE.md", "COMBAT_V0_1_NEXT_010_FIELD_ANALYSIS.md"]
out = ["# COMBAT-V0.1-NEXT-010 \u4ea4\u4ed8\u7269 SHA-256", "",
       "\u751f\u6210\u65b9\u5f0f: \u9010\u6587\u4ef6\u8bfb\u5b57\u8282\u8ba1\u7b97 SHA-256\u3002", "",
       "| \u6587\u4ef6 | \u5b57\u8282\u6570 | SHA-256 |", "|---|---|---|"]
for f in FILES:
    b = open(os.path.join(BASE, f), "rb").read()
    out.append("| `%s` | %d | `%s` |" % (f, len(b), hashlib.sha256(b).hexdigest()))
out += ["", "## \u72b6\u6001", "",
        "| \u9879 | \u503c |", "|---|---|",
        "| \u72ec\u7acb\u526f\u672c | `REF_LOBBY_KIT_CAP009` |",
        "| \u63d2\u6869 | \u5df2\u5b9e\u65bd\uff0c\u9759\u6001\u81ea\u68c0\u5168\u901a\u8fc7 |",
        "| \u91c7\u96c6 | \u6682\u505c\uff0c\u5f85\u7528\u6237\u786e\u8ba4 |",
        "| A/B \u5b57\u6bb5\u6620\u5c04 | \u672a\u95ed\u5408 |"]
out += ["", "## \u4fee\u6539\u524d\u540e\u54c8\u5e0c\uff08\u539f\u76ee\u5f55\u672a\u52a8\uff09", "",
        "| \u6587\u4ef6 | \u5b57\u8282\u6570 | SHA-256 |", "|---|---|---|"]
for f in ["REF_LOBBY_KIT/lobby_server.py", "REF_LOBBY_KIT_CAP009/lobby_server.py",
          "REF_LOBBY_KIT/codol_crypto.py", "REF_LOBBY_KIT/lobby_srv.log",
          "GOLDEN-LOBBY-001/REF_LOBBY_KIT/lobby_server.py"]:
    p = os.path.join(BASE, f)
    if os.path.exists(p):
        b = open(p, "rb").read()
        out.append("| `%s` | %d | `%s` |" % (f, len(b), hashlib.sha256(b).hexdigest()))
    else:
        out.append("| `%s` | - | (not found) |" % f)
out += ["", "## \u672c\u6b21\u65b0\u589e\u811a\u672c", "",
        "| \u811a\u672c | \u5b57\u8282\u6570 | SHA-256 | \u4f5c\u7528 |", "|---|---|---|---|"]
for f, d in [("apply_capture_patch.py", "\u951a\u5b9a\u63d2\u6869\u5668\uff08\u5e42\u7b49\uff09"),
             ("test_capture_hooks.py", "\u91c7\u96c6\u94a9\u5b50\u5355\u5143\u6d4b\u8bd5")]:
    p = os.path.join(BASE, "_combat_next001", f)
    if os.path.exists(p):
        b = open(p, "rb").read()
        out.append("| `_combat_next001/%s` | %d | `%s` | %s |" % (f, len(b), hashlib.sha256(b).hexdigest(), d))
out += ["", "## \u590d\u6838\u65b9\u6cd5", "", "```powershell", 'cd "' + BASE + '"',
        "Get-ChildItem COMBAT_V0_1_NEXT_010_*.md | Get-FileHash -Algorithm SHA256 | Format-Table Hash,Path -AutoSize",
        "cd _combat_next001",
        "python -X utf8 test_capture_hooks.py \"..\\REF_LOBBY_KIT_CAP009\"   # \u94a9\u5b50\u81ea\u68c0",
        "```"]
open(os.path.join(BASE, "COMBAT_V0_1_NEXT_010_SHA256.txt"), "w",
     encoding="utf-8", newline="\r\n").write("\n".join(out) + "\n")
print("manifest written")
