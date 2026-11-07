import re

with open(r"_e1_regression\ol-mod-olfinal\src\game_server\EngineBindings.cpp", "r", encoding="utf-8", errors="ignore") as f:
    text = f.read()

# search for prefix arrays
matches = re.findall(r"(constexpr\s+std::array<std::uint8_t,\s*\d+>\s+\w+Prefix\s*\{[^}]+\};)", text)
for m in matches[:15]:
    print(m)
