with open("CODOL-Combat-Server-v0.1/src/Engine/ServerHost.cs", "r", encoding="utf-8") as f:
    content = f.read()

old_code = """            string[] cands = new string[]
            {
                "map_assets",
                Path.Combine("..", "..", "..", "_map_extract"),
                "_map_extract",
                Path.Combine("config", "map_assets")
            };"""

new_code = """            string[] cands = new string[]
            {
                "map_assets",
                Path.Combine("..", "_map_extract"),
                Path.Combine("..", "..", "..", "_map_extract"),
                "_map_extract",
                Path.Combine("config", "map_assets")
            };"""

assert old_code in content, "old_code not found in ServerHost.cs"
content = content.replace(old_code, new_code, 1)

with open("CODOL-Combat-Server-v0.1/src/Engine/ServerHost.cs", "w", encoding="utf-8") as f:
    f.write(content)

print("ServerHost.cs updated successfully!")
