with open(r"_e1_regression\ol-mod-olfinal\src\game_server\EngineBindings.cpp", "r", encoding="utf-8", errors="ignore") as f:
    text = f.read()

pos = text.find("EngineBindings::bind()")
if pos != -1:
    print(text[pos+1000:pos+3500])
