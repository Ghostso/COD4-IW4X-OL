import re

with open(r"_e1_regression\ol-mod-olfinal\src\game_server\EngineBindings.cpp", "r", encoding="utf-8", errors="ignore") as f:
    text = f.read()

# find EngineBindings::bind
pos = text.find("EngineBindings::bind")
if pos != -1:
    print(text[pos:pos+2500])
else:
    print("Not found EngineBindings::bind directly, searching 'bind('...")
    for m in re.finditer(r"(bool\s+EngineBindings::\w+)", text):
        print(m.group(1))
