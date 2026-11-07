import re

with open(r"_e1_regression\ol-mod-olfinal\src\game_server\EngineBindings.hpp", "r", encoding="utf-8", errors="ignore") as f:
    text = f.read()

# search for Rva constants
matches = re.findall(r"(constexpr\s+.*?Rva\s*=\s*0x[0-9a-fA-F]+;)", text)
for m in matches[:50]:
    print(m)
print(f"Total Rva constants found: {len(matches)}")
