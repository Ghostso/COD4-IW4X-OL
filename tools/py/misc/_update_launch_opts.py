# -*- coding: utf-8 -*-
launch_script = "launch_game_for_user_test.py"
with open(launch_script, "r", encoding="utf-8") as f:
    text = f.read()

# Make sure --no-battle is removed and --retries 5 --no-certs are added
old_opts = '"--secs", "1800", "--out", "n10_interactive_test.txt", "--force", "--no-battle"'
new_opts = '"--secs", "1800", "--out", "n10_interactive_test.txt", "--force", "--retries", "5", "--no-certs"'

if old_opts in text:
    text = text.replace(old_opts, new_opts, 1)
    print("Replaced --no-battle with --retries 5 --no-certs")
elif new_opts not in text:
    old_base = '"--secs", "1800", "--out", "n10_interactive_test.txt", "--force"'
    text = text.replace(old_base, new_opts, 1)
    print("Added --retries 5 --no-certs")
else:
    print("Options already set to --retries 5 --no-certs")

with open(launch_script, "w", encoding="utf-8") as f:
    f.write(text)

print("Updated launch_game_for_user_test.py successfully!")