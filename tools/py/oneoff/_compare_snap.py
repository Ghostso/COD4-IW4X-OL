with open(r"CODOL-Combat-Server-v0.1\src\Codol\MotionSnapshot.cs.bak_before_movefix_20261016", "r", encoding="utf-8") as f:
    text_old = f.read()

pos = text_old.find("BuildVerifiedMotionSnapshot")
if pos != -1:
    print(text_old[pos:pos+1800])
