with open(r"_e1_regression\ol-mod-olfinal\src\game_server\EngineBindings.cpp", "r", encoding="utf-8") as f:
    text = f.read()

import re
matches = re.findall(r"(constexpr\s+std::array<std::uint8_t,\s*\d+>\s+SV\w+Prefix\s*\{[^}]+\};)", text)
for m in matches:
    print(m)
