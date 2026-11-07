import re

with open(r"_e1_regression\ol-mod-olfinal\src\game_server\server_mp\sv_snapshot_mp.cpp", "r", encoding="utf-8") as f:
    text = f.read()

pos = text.find("void SvSnapshotBuilder::writePlayerState")
if pos == -1:
    pos = text.find("writePlayerState(")

print("writePlayerState found at:", pos)
body = text[pos:pos+15000]

# Find all field writes
matches = re.findall(r"writePlayerStateFieldIndex\s*\(\s*message\s*,\s*([^,]+),\s*lastFieldIndex\s*\);", body)
print(f"Total fields written in pass 1: {len(matches)}")
for i, m in enumerate(matches):
    print(f"  #{i+1:02d}: {m.strip()}")

# Also find second pass
pos2 = body.find("PlayerStateSecondPassFields")
if pos2 != -1:
    print("\nSecond pass fields:")
    print(body[pos2:pos2+800])
