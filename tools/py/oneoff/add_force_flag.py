with open("launch_game_for_user_test.py", "r", encoding="utf-8") as f:
    content = f.read()

old_cmd = """        sys.executable, "-X", "utf8", RUN_ALL,
        "--secs", "1800", "--out", "n10_interactive_test.txt"
    ]"""

new_cmd = """        sys.executable, "-X", "utf8", RUN_ALL,
        "--secs", "1800", "--out", "n10_interactive_test.txt", "--force"
    ]"""

if old_cmd in content:
    content = content.replace(old_cmd, new_cmd, 1)
    with open("launch_game_for_user_test.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("Added --force to launch_game_for_user_test.py!")
else:
    print("--force already present or command differs.")
