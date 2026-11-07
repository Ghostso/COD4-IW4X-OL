with open(r"_e1_regression\ol-mod-olfinal\src\game_server\EngineBindings.cpp", "r", encoding="utf-8") as f:
    text = f.read()

pos = text.find("nativeEntityPrefixFailure =")
if pos != -1:
    print(text[pos:pos+1500])
