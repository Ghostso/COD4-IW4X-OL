# -*- coding: utf-8 -*-
path = "launch_game_for_user_test.py"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

# Completely remove bring_window_to_foreground so it NEVER touches desktop focus or locks user input
old_thread = "t_fg = threading.Thread(target=bring_window_to_foreground, daemon=True)\n    t_fg.start()"
new_thread = "# [DISABLED] Never grab foreground or lock desktop input queue\n    # t_fg = threading.Thread(target=bring_window_to_foreground, daemon=True)\n    # t_fg.start()"

assert old_thread in text, "old_thread not found"
text = text.replace(old_thread, new_thread, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(text)

print("Successfully disabled bring_window_to_foreground! Desktop input queue will NEVER be locked.")