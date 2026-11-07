import os

root = os.path.dirname(os.path.abspath("run_combat_pipeline.py"))

# 1. Patch codol_crypto.py
crypto_path = os.path.join(root, "REF_LOBBY_KIT", "codol_crypto.py")
with open(crypto_path, "r", encoding="utf-8") as f:
    c = f.read()
target = "pl_val = 1 if firing_range else (playlist if playlist is not None else 1)"
replacement = "pl_val = playlist if playlist is not None else (1 if firing_range else 1)"
assert target in c, "target not found in codol_crypto.py"
c = c.replace(target, replacement, 1)
with open(crypto_path, "w", encoding="utf-8") as f:
    f.write(c)
print("Patched codol_crypto.py")

# 2. Patch lobby_server.py
lobby_path = os.path.join(root, "REF_LOBBY_KIT", "lobby_server.py")
with open(lobby_path, "r", encoding="utf-8") as f:
    c2 = f.read()
target2 = "objs = [cc.build_mission_session_object(\n                firing_range=True, playlist=1,\n                address67=True)]"
replacement2 = "objs = [cc.build_mission_session_object(\n                firing_range=True, playlist=(_pl or 1),\n                address67=True)]"
assert target2 in c2, "target2 not found in lobby_server.py"
c2 = c2.replace(target2, replacement2, 1)
with open(lobby_path, "w", encoding="utf-8") as f:
    f.write(c2)
print("Patched lobby_server.py")
