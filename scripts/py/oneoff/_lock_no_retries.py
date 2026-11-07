# -*- coding: utf-8 -*-
launch_script = "launch_game_for_user_test.py"
with open(launch_script, "r", encoding="utf-8") as f:
    text = f.read()

# Hard restriction: NO RETRIES! Single attempt only, no auto-relaunch loop
if '"--retries", "5"' in text:
    text = text.replace('"--retries", "5", ', '')
    print("Removed --retries 5 from launch_game_for_user_test.py")

with open(launch_script, "w", encoding="utf-8") as f:
    f.write(text)

print("Updated launch_game_for_user_test.py to single-shot execution only.")