with open(r"_e1_regression\ol-mod-olfinal\xmake.lua", "r", encoding="utf-8") as f:
    text = f.read()

for t in ["ol_room_owner", "ol_game_server", "ol_dedicated_control_tests"]:
    pos = text.find(t)
    if pos != -1:
        start = text.rfind("target(", 0, pos)
        end = text.find("\ntarget(", pos)
        if end == -1: end = pos + 400
        print(f"=== Target {t} ===")
        print(text[start:end])
