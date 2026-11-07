p = "CODOL_SERVER_319_20261021/docs/SESSION_20261022_CLIENT_ARCH_AND_LOBBY_CHAIN.md"
s = open(p, encoding="utf-8", errors="replace").read()
print("chars", len(s))
for l in s.splitlines():
    if l.startswith("## ") or l.startswith("# Appendix"):
        print(l)
