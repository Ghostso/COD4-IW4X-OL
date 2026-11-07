import difflib

with open(r"CODOL-Combat-Server-v0.1\src\Codol\MotionSnapshot.cs", "r", encoding="utf-8") as f:
    cur = f.readlines()
with open(r"CODOL-Combat-Server-v0.1\src\Codol\MotionSnapshot.cs.bak_before_movefix_20261016", "r", encoding="utf-8") as f:
    bak = f.readlines()

diff = list(difflib.unified_diff(bak, cur, fromfile="bak", tofile="cur", n=3))
for line in diff[:80]:
    print(line, end="")
if len(diff) > 80:
    print(f"\n... ({len(diff) - 80} more lines)")
