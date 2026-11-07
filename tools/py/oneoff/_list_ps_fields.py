with open(r"_e1_regression\ol-mod-olfinal\src\game_server\server_mp\sv_snapshot_mp.cpp", "r", encoding="utf-8") as f:
    text = f.read()

pos = text.find("writePlayerState(")
end = text.find("void SvSnapshotBuilder::writeServerEntities", pos)
if end == -1: end = pos + 35000
body = text[pos:end]

import re
# Find writePlayerStateFieldIndex
matches = re.findall(r"writePlayerStateFieldIndex\s*\(\s*[^,]+,\s*([^,]+),", body)
print(f"Total fields written: {len(matches)}")
for i, m in enumerate(matches):
    print(f"  #{i+1:02d}: {m.strip()}")
