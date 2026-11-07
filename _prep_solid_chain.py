# -*- coding: utf-8 -*-
import os, shutil

# 1. Disable firingrange-battle.enabled so C# server does not spawn
flag = r"REF_LOBBY_KIT\firingrange-battle.enabled"
flag_bak = r"REF_LOBBY_KIT\firingrange-battle.enabled.bak"
if os.path.exists(flag):
    if os.path.exists(flag_bak):
        os.remove(flag_bak)
    os.rename(flag, flag_bak)
    print(f"Renamed {flag} -> {flag_bak}")

# 2. Update launch_game_for_user_test.py to pass --no-battle
launch_script = "launch_game_for_user_test.py"
with open(launch_script, "r", encoding="utf-8") as f:
    text = f.read()

if "--no-battle" not in text:
    old_line = '"--secs", "1800", "--out", "n10_interactive_test.txt", "--force"'
    new_line = '"--secs", "1800", "--out", "n10_interactive_test.txt", "--force", "--no-battle"'
    assert old_line in text, "old_line not found in launch_game_for_user_test.py"
    text = text.replace(old_line, new_line, 1)
    with open(launch_script, "w", encoding="utf-8") as f:
        f.write(text)
    print("Added --no-battle to launch_game_for_user_test.py")
else:
    print("--no-battle already present in launch_game_for_user_test.py")