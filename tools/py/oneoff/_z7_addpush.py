p = r"CODOLServer\lobby3074\lsg_server.py"
src = open(p, encoding="utf-8").read()
# After self.armed = True, add push_config call
old = "            self.armed = True"
new = "            self.armed = True\n            self.push_config(c)"
src = src.replace(old, new, 1)
open(p, "w", encoding="utf-8", newline="").write(src)
print("patched")
